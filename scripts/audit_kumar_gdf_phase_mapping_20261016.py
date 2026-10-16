"""Read bounded original GDF header/event ranges and map cues to frozen trials.

This is metadata work: no signal samples, predictions, estimators or checkpoints
are read. Range hashes certify the downloaded ranges, never the entire GDF.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import struct
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from urllib3.exceptions import HTTPError as Urllib3HTTPError

ROOT = Path(__file__).resolve().parents[1]
TYPE_BYTES = (0, 1, 1, 2, 2, 4, 4, 8, 8, 0, 0, 0, 0, 0, 0, 0, 4, 8)
CUES = {769: "left_hand", 770: "right_hand"}
STARTS = {7691: "left_hand", 7701: "right_hand"}
ENDS = {7692: "left_hand", 7693: "left_hand", 7702: "right_hand", 7703: "right_hand"}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def exclusive_json(path, data):
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def parse_fixed_header(payload):
    if len(payload) != 256 or payload[:8] != b"GDF 2.00":
        raise ValueError("Only the observed GDF 2.00 fixed header is supported")
    header_bytes = struct.unpack_from("<H", payload, 184)[0] * 256
    n_records = struct.unpack_from("<q", payload, 236)[0]
    numerator, denominator = struct.unpack_from("<II", payload, 244)
    n_channels = struct.unpack_from("<H", payload, 252)[0]
    if not (0 < n_channels <= 256 and header_bytes == 256 * (n_channels + 1)):
        raise ValueError("Unexpected GDF header layout")
    if n_records <= 0 or numerator <= 0 or denominator <= 0:
        raise ValueError("Invalid recording length")
    date_fixed = struct.unpack_from("<Q", payload, 168)[0]
    recording_start = (
        datetime(1, 1, 1, tzinfo=timezone.utc)
        + timedelta(days=date_fixed * 2**-32 - 367)
    ).isoformat()
    return {
        "version": "GDF 2.00",
        "header_bytes": header_bytes,
        "n_records": n_records,
        "record_seconds_numerator": numerator,
        "record_seconds_denominator": denominator,
        "n_channels": n_channels,
        "recording_start_utc": recording_start,
    }


def parse_variable_header(payload, fixed):
    n = fixed["n_channels"]
    if len(payload) != 256 * n:
        raise ValueError("Variable header length mismatch")
    names = [payload[16 * i : 16 * (i + 1)].decode("latin-1").strip() for i in range(n)]
    samples = struct.unpack_from("<" + "I" * n, payload, 216 * n)
    types = struct.unpack_from("<" + "I" * n, payload, 220 * n)
    if any(t >= len(TYPE_BYTES) or TYPE_BYTES[t] == 0 for t in types):
        raise ValueError("Unsupported GDF data type")
    if min(samples) <= 0 or len(set(samples)) != 1:
        raise ValueError("Mixed or invalid channel clocks require a separate review")
    per_record = sum(s * TYPE_BYTES[t] for s, t in zip(samples, types))
    sample_rate = (
        samples[0] * fixed["record_seconds_denominator"] / fixed["record_seconds_numerator"]
    )
    return {
        **fixed,
        "channel_names": names,
        "samples_per_record": list(samples),
        "data_types": list(types),
        "sample_rate": sample_rate,
        "n_samples": samples[0] * fixed["n_records"],
        "bytes_per_record": per_record,
        "event_table_offset": fixed["header_bytes"] + fixed["n_records"] * per_record,
    }


def parse_events(payload, metadata):
    if len(payload) < 8:
        raise ValueError("Truncated event header")
    mode = payload[0]
    count = int.from_bytes(payload[1:4], "little")
    event_rate = struct.unpack_from("<f", payload, 4)[0]
    if mode not in (1, 3) or count <= 0 or not math.isfinite(event_rate) or event_rate <= 0:
        raise ValueError("Unsupported event mode/count/clock")
    expected = 8 + count * (6 if mode == 1 else 12)
    if len(payload) != expected:
        raise ValueError("Event bytes do not exactly fill original file tail")
    if event_rate != metadata["sample_rate"]:
        raise ValueError("Distinct event/signal clocks require separate conversion review")
    positions = struct.unpack_from("<" + "I" * count, payload, 8)
    codes = struct.unpack_from("<" + "H" * count, payload, 8 + 4 * count)
    if any(p < 1 or p > metadata["n_samples"] for p in positions):
        raise ValueError("Event position outside recording")
    if list(positions) != sorted(positions):
        raise ValueError("Event positions not monotone")
    events = [
        {"event_row": i + 1, "original_pos_1based": p, "sample_0based": p - 1, "code": c}
        for i, (p, c) in enumerate(zip(positions, codes))
    ]
    return {"mode": mode, "count": count, "sample_rate": event_rate, "events": events}


def phase_rows(events, frozen_trials, metadata, is_online):
    """Pair phases only inside their actual cue-to-next-cue event bracket."""
    cue_indices = [i for i, event in enumerate(events) if event["code"] in CUES]
    if len(cue_indices) != len(frozen_trials):
        raise ValueError("Cue/trial count mismatch")
    result = []
    recording_triggers = [event for event in events if event["code"] == 32766]
    for trial, index, next_index in zip(
        frozen_trials, cue_indices, cue_indices[1:] + [len(events)]
    ):
        cue = events[index]
        if cue["sample_0based"] != trial["start_sample"] or CUES[cue["code"]] != trial["label"]:
            raise ValueError("Exact sample/class correspondence failed")
        between = events[index + 1 : next_index]
        starts = [event for event in between if event["code"] in STARTS]
        ends = [event for event in between if event["code"] in ENDS]
        issues = []
        if len(starts) != 1:
            issues.append("task_start_count_" + str(len(starts)))
        if len(ends) != 1:
            issues.append("task_end_count_" + str(len(ends)))
        start = starts[0] if len(starts) == 1 else None
        end = ends[0] if len(ends) == 1 else None
        preceding_rest_starts = [event for event in events[:index] if event["code"] == 1000]
        preceding_rest = preceding_rest_starts[-1] if preceding_rest_starts else None
        following_rest = next((event for event in between if event["code"] == 1000
                               and end and event["sample_0based"] > end["sample_0based"]), None)
        if start and STARTS[start["code"]] != trial["label"]:
            issues.append("task_start_class_disagrees")
        if end and ENDS[end["code"]] != trial["label"]:
            issues.append("task_end_class_disagrees")
        if start and end and not (cue["sample_0based"] < start["sample_0based"] < end["sample_0based"]):
            issues.append("phase_order_invalid")
        sf = metadata["sample_rate"]
        complete_phase = not issues and start is not None and end is not None
        active_samples = end["sample_0based"] - start["sample_0based"] if complete_phase else None
        window_start, window_stop = trial["start_sample"], trial["stop_sample_exclusive"]
        active_overlap = (
            max(0, min(window_stop, end["sample_0based"]) - max(window_start, start["sample_0based"]))
            if complete_phase
            else None
        )
        pre_task = min(window_stop, start["sample_0based"]) - window_start if complete_phase else None
        post_task = max(0, window_stop - end["sample_0based"]) if complete_phase else None
        result.append(
            {
                "trial_id": trial["trial_id"],
                "subject": trial["subject"],
                "session": trial["session"],
                "run": trial["run"],
                "source_row": trial["source_row"],
                "class": trial["label"],
                "source_file": trial["source_file"],
                "online": is_online,
                "cue_code": cue["code"],
                "cue_original_pos_1based": cue["original_pos_1based"],
                "cue_sample_0based": cue["sample_0based"],
                "task_start_code": start["code"] if start else None,
                "task_start_sample_0based": start["sample_0based"] if start else None,
                "task_end_code": end["code"] if end else None,
                "task_end_sample_0based": end["sample_0based"] if end else None,
                "preceding_trial_rest_1000_sample_0based": preceding_rest["sample_0based"] if preceding_rest else None,
                "following_trial_rest_1000_sample_0based": following_rest["sample_0based"] if following_rest else None,
                "first_recording_trigger_32766_sample_0based": recording_triggers[0]["sample_0based"] if recording_triggers else None,
                "last_recording_trigger_32766_sample_0based": recording_triggers[-1]["sample_0based"] if recording_triggers else None,
                "recording_trigger_32766_count": len(recording_triggers),
                "recording_stop_sample_exclusive": metadata["n_samples"],
                "task_end_literal_category": (
                    "online_cue_delivered_codebook_wording" if is_online and end and end["code"] in (7693, 7703)
                    else "online_timeout_or_incorrect_hit" if is_online and end
                    else "offline_trial_end" if end else "not_resolved"
                ),
                "sample_rate": sf,
                "cue_to_task_start_seconds": (start["sample_0based"] - cue["sample_0based"]) / sf if start else None,
                "task_active_seconds": active_samples / sf if active_samples is not None else None,
                "original_stored_window_samples": trial["sample_count"],
                "original_window_complete_5s": trial["sample_count"] == 2560,
                "original_window_pre_task_seconds": pre_task / sf if pre_task is not None else None,
                "original_window_active_seconds": active_overlap / sf if active_overlap is not None else None,
                "original_window_post_task_seconds": post_task / sf if post_task is not None else None,
                "original_window_overlaps_post_task": bool(post_task) if post_task is not None else None,
                "original_window_crosses_following_trial_rest_marker": bool(complete_phase and following_rest
                    and window_stop > following_rest["sample_0based"]),
                "task_duration_below_7s_online": bool(is_online and active_samples < 7 * sf) if active_samples is not None else None,
                "task_start_2s_eligible": bool(complete_phase and active_samples >= 2 * sf and start["sample_0based"] + 2 * sf <= metadata["n_samples"]),
                "variable_active_minimum1s_eligible": bool(complete_phase and active_samples >= sf),
                "recording_n_samples": metadata["n_samples"],
                "original_window_ends_at_recording_boundary": window_stop == metadata["n_samples"],
                "cue_mapping_exact": True,
                "phase_mapping_success": complete_phase,
                "ambiguity_or_exclusion": ";".join(issues),
            }
        )
    return result


class RangeReader:
    """No retries and no fallback to a full download if Range is ignored."""

    def __init__(self, output_dir, maximum_bytes, network_policy=None):
        self.output_dir = Path(output_dir)
        self.maximum_bytes = maximum_bytes
        self.total_bytes = 0
        self.lock = threading.Lock()
        self.policy = network_policy
        self.http_requests = 0
        self.acquired_body_bytes = 0
        self.deadline = time.monotonic() + network_policy["maximum_operation_seconds"] if network_policy else None

    def fetch(self, row, start, end, output, etag=None):
        amount = end - start + 1
        if start < 0 or end >= row["size"] or amount <= 0 or amount > 100_000:
            raise ValueError("Requested range exceeds metadata bound")
        with self.lock:
            if self.total_bytes + amount > self.maximum_bytes:
                raise ValueError("Global range-byte budget exceeded")
        headers = {"Range": f"bytes={start}-{end}", "Accept-Encoding": "identity"}
        if etag:
            headers["If-Match"] = etag
        identity = {
            "url": row["url"], "official_path": row["path"],
            "range_start": start, "range_end": end, "expected_total_bytes": row["size"],
            "official_whole_file_sha256_not_verified_by_ranges": row["checksum"],
        }
        maximum_attempts = self.policy["maximum_attempts_per_range"] if self.policy else 1
        for attempt in range(1, maximum_attempts + 1):
            if self.deadline is not None:
                remaining = self.deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("Bounded metadata acquisition deadline reached")
                timeout = (min(15, remaining / 2), min(45, remaining / 2))
            else:
                timeout = (15, 45)
            with self.lock:
                if self.total_bytes + amount > self.maximum_bytes:
                    raise ValueError("Global range-byte budget exceeded")
                self.total_bytes += amount
                self.http_requests += 1
            receipt = {**identity, "started_utc": utc_now(), "attempt": attempt,
                       "status": None, "content_range": None, "range_bytes_read": 0,
                       "range_sha256": None, "response_body_read": False}
            payload, transient, integrity_error = None, False, None
            try:
                with requests.get(row["url"], headers=headers, stream=True, timeout=timeout) as response:
                    receipt.update(status=response.status_code, content_range=response.headers.get("Content-Range"),
                                   content_length=response.headers.get("Content-Length"), etag=response.headers.get("ETag"))
                    if response.status_code != 206:
                        transient = bool(self.policy and response.status_code in self.policy["retryable_http_statuses"])
                        integrity_error = "Server did not honor exact bounded HTTP range"
                    elif receipt["content_range"] != f"bytes {start}-{end}/{row['size']}":
                        integrity_error = "HTTP206 Content-Range integrity failure"
                    elif receipt["content_length"] != str(amount):
                        integrity_error = "HTTP206 Content-Length integrity failure"
                    elif receipt["etag"] is None:
                        integrity_error = "Original object has no stable ETag"
                    elif etag is not None and receipt["etag"] != etag:
                        integrity_error = "Original object ETag changed between ranges"
                    else:
                        receipt.update(response_body_read_attempted=True, range_bytes_read=None)
                        payload = response.raw.read(amount + 1)
                        receipt.update(response_body_read=True, range_bytes_read=len(payload), range_sha256=sha256(payload))
                        if len(payload) != amount:
                            integrity_error = "Exact range body length mismatch"
            except (requests.exceptions.RequestException, Urllib3HTTPError) as error:
                receipt.update(transport_exception=type(error).__name__, transport_message=str(error))
                transient = bool(self.policy and self.policy["retry_transport_exceptions"])
                integrity_error = "Metadata HTTPS transport failure"
            retry = transient and attempt < maximum_attempts
            receipt.update(completed_utc=utc_now(), transient_retry_scheduled=retry,
                           retry_scope="public_metadata_transport_only" if self.policy else "none")
            exclusive_json(output.with_suffix(f".attempt{attempt:02d}.json"), receipt)
            if integrity_error is None:
                break
            if not retry:
                exclusive_json(output.with_suffix(".failure.json"), receipt)
                raise ValueError(integrity_error)
            delay = self.policy["backoff_seconds"][attempt - 1]
            if self.deadline is not None and time.monotonic() + delay >= self.deadline:
                raise TimeoutError("Metadata deadline cannot accommodate fixed transport backoff")
            time.sleep(delay)
        with output.open("xb") as handle:
            handle.write(payload)
        with self.lock:
            self.acquired_body_bytes += len(payload)
        receipt.update(range_bytes=len(payload), range_sha256=sha256(payload), completed_utc=utc_now())
        exclusive_json(output.with_suffix(".receipt.json"), receipt)
        return payload, receipt

    def run(self, index, row):
        directory = self.output_dir / f"gdf-{index:03d}"
        directory.mkdir(exist_ok=False)
        first, receipt = self.fetch(row, 0, 255, directory / "fixed_header.bin")
        fixed = parse_fixed_header(first)
        variable, _ = self.fetch(row, 256, fixed["header_bytes"] - 1,
                                 directory / "variable_header.bin", receipt["etag"])
        metadata = parse_variable_header(variable, fixed)
        event_start = metadata["event_table_offset"]
        if event_start <= fixed["header_bytes"] or row["size"] - event_start > 100_000:
            raise ValueError("Invalid event-table offset or oversized event tail")
        tail, _ = self.fetch(row, event_start, row["size"] - 1,
                            directory / "event_table.bin", receipt["etag"])
        event_table = parse_events(tail, metadata)
        decoded = {"index": index, "source": row, "metadata": metadata, "event_table": event_table}
        exclusive_json(directory / "decoded_metadata.json", decoded)
        return decoded


def validate_saved_run(directory, row, index):
    """Rehash actual saved ranges before reuse; incomplete runs are not passed."""
    expected = json.loads((directory / "decoded_metadata.json").read_bytes())
    if expected["source"] != row or expected["index"] != index:
        raise ValueError("Saved original-file identity changed")
    payloads, receipts, etags, total = {}, {}, set(), 0
    for name in ("fixed_header", "variable_header", "event_table"):
        payload = (directory / f"{name}.bin").read_bytes()
        receipt = json.loads((directory / f"{name}.receipt.json").read_bytes())
        start, end = receipt["range_start"], receipt["range_end"]
        if (receipt["status"] != 206 or receipt["url"] != row["url"]
                or receipt["official_path"] != row["path"]
                or receipt["expected_total_bytes"] != row["size"]
                or receipt["official_whole_file_sha256_not_verified_by_ranges"] != row["checksum"]
                or receipt["content_range"] != f"bytes {start}-{end}/{row['size']}"
                or receipt["range_bytes"] != len(payload) or len(payload) != end - start + 1
                or receipt["range_sha256"] != sha256(payload)):
            raise ValueError("Saved range receipt/body integrity failed")
        payloads[name] = payload
        receipts[name] = receipt
        etags.add(receipt["etag"])
        total += len(payload)
    if len(etags) != 1 or None in etags:
        raise ValueError("Saved ranges have no single stable object ETag")
    fixed = parse_fixed_header(payloads["fixed_header"])
    metadata = parse_variable_header(payloads["variable_header"], fixed)
    events = parse_events(payloads["event_table"], metadata)
    expected_spans = {
        "fixed_header": (0, 255), "variable_header": (256, fixed["header_bytes"] - 1),
        "event_table": (metadata["event_table_offset"], row["size"] - 1),
    }
    if any((receipts[name]["range_start"], receipts[name]["range_end"]) != span
           for name, span in expected_spans.items()):
        raise ValueError("Saved range boundaries disagree with parsed GDF layout")
    if metadata != expected["metadata"] or events != expected["event_table"]:
        raise ValueError("Reparsed saved ranges disagree with recorded decode")
    return expected, total


def run(args):
    args.private_output.mkdir(parents=True, exist_ok=False)
    args.output.mkdir(parents=True, exist_ok=False)
    source_events_path = ROOT / "research_logs/public_data_expansion_20261010/kumar_ingestion/signal_audit_run02/source_events.json"
    manifest_path = ROOT / "research_logs/public_data_expansion_20261010/longitudinal_receipts/nm000177_manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    source_events = json.loads(source_events_path.read_bytes())
    gdfs = [row for row in manifest if row["path"].endswith(".gdf") and row["path"].startswith(("sourcedata/Offline/", "sourcedata/Online/"))]
    if len(gdfs) != 360 or len(source_events) != 7200:
        raise ValueError("Frozen run inventory changed")
    groups = defaultdict(list)
    for trial in source_events:
        groups[trial["source_file"]].append(trial)
    lookup = defaultdict(list)
    for filename, trials in groups.items():
        fingerprint = tuple((trial["start_sample"], trial["label"]) for trial in trials)
        lookup[fingerprint].append(filename)
    if len(lookup) != 360 or any(len(matches) != 1 for matches in lookup.values()):
        raise ValueError("Derivative cue fingerprints are not unique")
    policy = json.loads(args.network_policy.read_bytes()) if args.network_policy else None
    if policy:
        if (policy["maximum_attempts_per_range"] != 3 or policy["maximum_operation_seconds"] != 600
                or policy["retryable_http_statuses"] != [502, 503, 504]
                or policy["backoff_seconds"] != [1, 3] or args.workers != 1
                or not policy["retry_transport_exceptions"] or policy["scientific_fit_retries"] != 0):
            raise ValueError("Unreviewed metadata-only transport policy")
        exclusive_json(args.private_output / "network_policy_binding.json", {
            "path": str(args.network_policy), "bytes": args.network_policy.stat().st_size,
            "sha256": sha256(args.network_policy.read_bytes()), "policy": policy,
        })
    reader = RangeReader(args.private_output, args.max_range_bytes, policy)
    decoded = []
    started = utc_now()
    saved_range_bytes = 0
    reuse_directories = args.offline_ranges or args.reuse_ranges
    completed_indices = set()
    range_sources = {}
    if reuse_directories:
        for index, row in enumerate(gdfs[:args.limit]):
            candidates = [directory / f"gdf-{index:03d}" for directory in reuse_directories
                          if (directory / f"gdf-{index:03d}" / "decoded_metadata.json").exists()]
            if not candidates:
                continue
            directory = candidates[0]
            item, amount = validate_saved_run(directory, row, index)
            for duplicate in candidates[1:]:
                other, _ = validate_saved_run(duplicate, row, index)
                if other != item:
                    raise ValueError("Conflicting independently saved run metadata")
            decoded.append(item)
            saved_range_bytes += amount
            completed_indices.add(index)
            range_sources[index] = str(directory)
        exclusive_json(args.private_output / "offline_reuse_receipt.json", {
            "created_utc": utc_now(), "source_directories": [str(path) for path in reuse_directories],
            "rehash_reparse_passed_run_count": len(decoded), "validated_saved_range_bytes": saved_range_bytes,
            "http_requests_during_reuse": 0, "missing_or_incomplete_runs_not_assumed_passed": len(gdfs) - len(decoded),
        })
    if not args.offline_ranges and args.workers == 1:
        # Deliberately submit no future requests after a failed sequential read.
        for index, row in enumerate(gdfs[:args.limit]):
            if index not in completed_indices:
                decoded.append(reader.run(index, row))
                print(json.dumps({"completed_runs": len(decoded), "utc": utc_now()}), flush=True)
    elif not args.offline_ranges:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {
                pool.submit(reader.run, i, row): i
                for i, row in enumerate(gdfs[:args.limit]) if i not in completed_indices
            }
            try:
                for future in as_completed(futures):
                    decoded.append(future.result())
                    if len(decoded) % 30 == 0:
                        print(json.dumps({"completed_runs": len(decoded), "utc": utc_now()}), flush=True)
            except BaseException as error:
                for future in futures:
                    future.cancel()
                exclusive_json(args.output / "exception_receipt.json", {
                    "started_utc": started, "failed_utc": utc_now(), "exception": type(error).__name__,
                    "message": str(error), "completed_runs": len(decoded), "automatic_retry": False,
                })
                raise
    rows, run_receipts, used = [], [], set()
    inputs = [source_events_path, manifest_path]
    data_root = ROOT / "data/public_eeg/kumar2024/nm000177/v1.0.5"
    for item in sorted(decoded, key=lambda value: value["index"]):
        events, metadata = item["event_table"]["events"], item["metadata"]
        cue_fingerprint = tuple((event["sample_0based"], CUES[event["code"]]) for event in events if event["code"] in CUES)
        matches = lookup.get(cue_fingerprint, [])
        if len(matches) != 1:
            raise ValueError(f"No unique exact 20-cue sample/class map: {item['source']['path']}")
        filename = matches[0]
        if filename in used:
            raise ValueError("Two original files map to one derivative run")
        used.add(filename)
        trials = groups[filename]
        previous_path = ROOT / "research_logs/public_data_expansion_20261010/kumar_ingestion/signal_audit_run02/runs" / (filename.replace("/", "__") + ".json")
        previous = json.loads(previous_path.read_bytes())
        inputs.append(previous_path)
        if previous["status"] != "passed" or metadata["sample_rate"] != previous["sfreq"] or metadata["n_samples"] != previous["n_times"]:
            raise ValueError("Signal clock or recording extent disagrees with frozen EDF audit")
        original_channel_names = metadata["channel_names"][:22]
        derivative_channel_names = previous["channel_names"]
        if ([name.casefold() for name in original_channel_names]
                != [name.casefold() for name in derivative_channel_names]):
            raise ValueError("Original and derivative channel order differ")
        subject, session = trials[0]["subject"], trials[0]["session"]
        scans_path = data_root / subject / session / f"{subject}_{session}_scans.tsv"
        inputs.append(scans_path)
        scans = list(csv.DictReader(io.StringIO(scans_path.read_text()), delimiter="\t"))
        scan = [scan for scan in scans if scan["filename"] == "/".join(filename.split("/")[2:])]
        if len(scan) != 1:
            raise ValueError("Missing unique derivative acquisition-time record")
        time_difference = abs((datetime.fromisoformat(metadata["recording_start_utc"]) - datetime.fromisoformat(scan[0]["acq_time"].replace("Z", "+00:00"))).total_seconds())
        if time_difference > 0.001:
            raise ValueError("Original/derivative acquisition clock differs by >1ms")
        phases = phase_rows(events, trials, metadata, "/Online/" in item["source"]["path"])
        for phase in phases:
            phase.update(original_gdf_path=item["source"]["path"], original_whole_gdf_sha256_not_verified=item["source"]["checksum"])
        rows.extend(phases)
        run_receipts.append({
            "original_gdf_path": item["source"]["path"], "derivative_edf_path": filename,
            "range_decoded_private_file": f"gdf-{item['index']:03d}/decoded_metadata.json",
            "range_evidence_location": range_sources.get(item["index"], str(args.private_output / f"gdf-{item['index']:03d}")),
            "unique_exact_cue_count": len(trials), "sample_rate": metadata["sample_rate"],
            "recording_n_samples": metadata["n_samples"], "acquisition_time_difference_seconds": time_difference,
            "channel_order_first22_case_insensitive_equal": True,
            "channel_order_first22_literal_equal": original_channel_names == derivative_channel_names,
            "original_first22_channel_names": original_channel_names,
            "derivative_channel_names": derivative_channel_names,
            "channel_comparison_rule": "casefold only, preserving all 22 positions; no permutation or electrode aliases",
            "all_cue_sample_positions_and_classes_equal": True,
            "event_code_counts": dict(Counter(event["code"] for event in events)),
            "phase_mapping_success_count": sum(row["phase_mapping_success"] for row in phases),
        })
    fieldnames = list(rows[0])
    with (args.output / "trial_event_mapping.csv").open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    exclusive_json(args.output / "run_correspondence.json", run_receipts)
    exclusive_json(args.output / "input_sha256_manifest.json", [
        {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha256(path.read_bytes())}
        for path in sorted(set(inputs))
    ])
    summary = {
        "started_utc": started, "completed_utc": utc_now(), "scientific_decoder_executed": False,
        "ranges_requested_bytes": reader.total_bytes, "gdf_count": len(decoded), "trial_count": len(rows),
        "validated_saved_range_bytes": saved_range_bytes,
        "original_gdf_inventory": len(gdfs), "missing_or_incomplete_gdfs": len(gdfs) - len(decoded),
        "coverage_complete": len(decoded) == len(gdfs),
        "actual_new_http_requests": reader.http_requests,
        "actual_new_range_body_bytes_acquired": reader.acquired_body_bytes,
        "network_policy_sha256": sha256(args.network_policy.read_bytes()) if args.network_policy else None,
        "cue_mapping_exact_count": sum(row["cue_mapping_exact"] for row in rows),
        "phase_mapping_success_count": sum(row["phase_mapping_success"] for row in rows),
        "entire_gdf_signal_bytes_downloaded": False, "whole_gdf_checksums_verified": False,
        "http_range_receipts_location": str(args.private_output),
        "scientific_fit_retries": 0,
        "transport_retry_policy_maximum_attempts_per_range": policy["maximum_attempts_per_range"] if policy else 1,
    }
    exclusive_json(args.output / "summary.json", summary)
    print(json.dumps(summary, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, choices=range(1, 361), default=360)
    parser.add_argument("--workers", type=int, choices=(1, 2, 3, 4), default=4)
    parser.add_argument("--max-range-bytes", type=int, default=4 * 1024 * 1024)
    parser.add_argument("--network-policy", type=Path, help="Explicit versioned bounded metadata-only transport policy")
    parser.add_argument("--offline-ranges", type=Path, nargs="+", help="Rehash/reparse completed saved runs only; make zero HTTP requests")
    parser.add_argument("--reuse-ranges", type=Path, nargs="+", help="Explicit new metadata acquisition: rehash/reparse completed saved runs, fetch only incomplete/missing runs")
    args = parser.parse_args()
    if args.offline_ranges and args.reuse_ranges:
        parser.error("Choose offline-only reuse or explicit missing-run acquisition")
    try:
        run(args)
    except BaseException as error:
        receipt_path = args.output / "exception_receipt.json"
        if args.output.is_dir() and not receipt_path.exists():
            exclusive_json(receipt_path, {
                "failed_utc": utc_now(), "exception": type(error).__name__, "message": str(error),
                "automatic_retry": False, "existing_partial_preserved": True,
            })
        raise


if __name__ == "__main__":
    main()
