"""Re-read actual downloaded PhysioNet sources; never import ingestion helpers.

Run after the source audit. This is a real-data verification companion rather
than a source of training epochs, behavioral scores or research conclusions.
"""

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import mne
import numpy as np
import wfdb


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--audit-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    audit = json.loads((args.audit_root / "signal_audit.json").read_text())
    assert manifest["version"] == "1.0.0"
    assert manifest["subject_count"] == 109 and manifest["edf_count"] == 327
    assert len(manifest["files"]) == 654
    assert manifest["total_bytes"] == 834146640
    assert len({r["path"] for r in manifest["files"]}) == 654
    assert audit["read_subject_count"] == 109 and audit["read_signal_count"] == 327
    assert audit["new_epochs_created"] is False and audit["failures"] == []
    assert audit["analysis_status"] == "source_audit_only" and not audit["synthetic"]
    records = {r["path"]: r for r in audit["files"]}
    with (args.audit_root / "source_annotations.tsv").open() as stream:
        annotation_rows = list(csv.DictReader(stream, delimiter="\t"))
    with (args.audit_root / "source_wfdb_annotations.tsv").open() as stream:
        wfdb_rows = list(csv.DictReader(stream, delimiter="\t"))
    annotations = defaultdict(list)
    for row in annotation_rows:
        annotations[row["source_file"]].append(row)
    source_wfdb = defaultdict(list)
    for row in wfdb_rows:
        source_wfdb[row["source_file"]].append(row)
    checks, labels, durations = [], Counter(), defaultdict(Counter)
    fixed_4s_count, sidecar_count = 0, 0
    signals = defaultdict(list)
    recomputed_flags = {}
    official_bytes = defaultdict(list)
    for entry in manifest["files"]:
        path = args.data_root / entry["path"]
        assert path.stat().st_size == entry["size"], entry["path"]
        assert file_hash(path) == entry["sha256"], entry["path"]
        if entry["type"] != "edf":
            continue
        row = records[entry["path"]]
        raw = mne.io.read_raw_edf(path, preload=True, verbose="ERROR")
        try:
            data = raw.get_data()
            assert np.isfinite(data).all(), entry["path"]
            content_hash = hashlib.sha256(np.asarray(
                data.T, dtype="<f8").tobytes(order="C")).hexdigest()
            assert content_hash == row["signal_content_sha256"], entry["path"]
            assert raw.ch_names == row["channel_order"]
            assert float(raw.info["sfreq"]) == row["sampling_rate_hz"]
            assert raw.n_times == row["n_samples"]
            assert raw._orig_units == row["original_units"]
            assert np.isclose(float(np.abs(data).max()), row["peak_absolute_V"],
                              rtol=1e-12, atol=1e-15)
            assert np.allclose(np.sqrt(np.mean(data ** 2, axis=1)), row["channel_rms_V"],
                               rtol=1e-12, atol=1e-15)
            source_rows = annotations[entry["path"]]
            assert len(source_rows) == len(raw.annotations)
            clock = float(raw.info["sfreq"])
            total_duration = raw.n_times / clock
            file_flags = set()
            if clock != 160.0:
                file_flags.add("sampling_rate_differs_from_advertised_160Hz")
            if len(raw.ch_names) != 64:
                file_flags.add("channel_count_differs_from_advertised_64")
            if set(raw._orig_units.values()) != {"µV"}:
                file_flags.add("original_unit_differs_from_microvolts")
            if not row["sidecar_annotation_agreement"]["all_nonzero_edf_annotations_match"]:
                file_flags.add("EDF_WFDB_annotation_disagreement_pending_source_resolution")
            previous_end = 0.0
            for index, (onset, duration, label) in enumerate(zip(
                    raw.annotations.onset, raw.annotations.duration,
                    raw.annotations.description, strict=True)):
                event = source_rows[index]
                assert int(event["source_annotation_index"]) == index
                assert event["subject"] == entry["subject"]
                assert int(event["run"]) == entry["run"]
                assert float(event["onset_seconds"]) == onset
                assert float(event["duration_seconds"]) == duration
                assert event["source_label"] == label
                labels[str(label)] += 1
                durations[str(label)][str(float(duration))] += 1
                event_flags = set()
                if not row["sidecar_annotation_agreement"]["all_nonzero_edf_annotations_match"]:
                    event_flags.add("EDF_WFDB_annotation_disagreement_pending_source_resolution")
                if str(label) not in {"T0", "T1", "T2"}:
                    event_flags.add("unknown_annotation_label")
                if onset < -1 / clock or onset + duration > total_duration + 1 / clock:
                    event_flags.add("annotation_outside_signal")
                if duration <= 0:
                    event_flags.add("nonpositive_annotation_duration")
                if onset < previous_end - 1 / clock:
                    event_flags.add("overlapping_annotations")
                previous_end = onset + duration
                assert event_flags == set(filter(None, event["flags"].split(";")))
                file_flags.update(event_flags)
                # The four-second census is distinct from actual epoch inclusion.
                available = (str(label) in {"T1", "T2"} and duration >= 4.0
                             and not event["flags"]
                             and onset + 4.0 <= total_duration + 0.5 / clock)
                assert event["complete_4s_window_available"] == str(bool(available))
                fixed_4s_count += available
            sidecar = wfdb.rdann(str(path), "event")
            assert sidecar.fs == clock
            source_onsets = raw.annotations.onset
            source_durations = raw.annotations.duration
            source_labels = raw.annotations.description
            difference = len(source_onsets) - len(sidecar.sample)
            agreement = row["sidecar_annotation_agreement"]
            strict_agrees = agreement["all_nonzero_edf_annotations_match"]
            if strict_agrees:
                assert difference in (0, 1)
            if strict_agrees and difference:
                assert source_onsets[0] == 0 and source_labels[0] == "T0"
            if not strict_agrees:
                assert entry["path"] not in audit["source_qualification"]["pass_eligible_files"]
            stored_sidecar = source_wfdb[entry["path"] + ".event"]
            assert len(stored_sidecar) == len(sidecar.sample)
            for i, (sample, note, symbol) in enumerate(zip(
                    sidecar.sample, sidecar.aux_note, sidecar.symbol, strict=True)):
                assert int(stored_sidecar[i]["sample"]) == sample
                assert stored_sidecar[i]["original_aux_note"] == note
                assert stored_sidecar[i]["symbol"] == symbol
                assert float(stored_sidecar[i]["sampling_rate_hz"]) == sidecar.fs
                if strict_agrees:
                    label, duration_text = note.split(" duration: ")
                    position = i + difference
                    assert symbol == '"' and label == source_labels[position]
                    assert abs(sample / clock - source_onsets[position]) <= 0.5 / clock
                    assert abs(float(duration_text) - source_durations[position]) <= 0.5 / clock
            if not strict_agrees:
                matched = set()
                unmatched_sidecar = []
                for i, (sample, note, symbol) in enumerate(zip(
                        sidecar.sample, sidecar.aux_note, sidecar.symbol, strict=True)):
                    label, duration_text = note.split(" duration: ")
                    matches = [index for index, (onset, duration, source_label) in enumerate(zip(
                        source_onsets, source_durations, source_labels, strict=True))
                        if index not in matched and source_label == label
                        and abs(sample / clock - onset) <= 0.5 / clock
                        and abs(float(duration_text) - duration) <= 0.5 / clock]
                    if len(matches) == 1:
                        matched.add(matches[0])
                    else:
                        unmatched_sidecar.append(i)
                absent = set(range(len(source_onsets))) - matched
                assert absent == {r["edf_annotation_index"]
                                  for r in agreement["unmatched_edf_annotations"]}
                assert unmatched_sidecar == [r["wfdb_annotation_index"]
                                            for r in agreement["unmatched_wfdb_annotations"]]
                assert agreement["source_streams_modified"] is False
            sidecar_count += len(sidecar.sample)
            recomputed_flags[entry["path"]] = file_flags
            signals[(content_hash, clock, tuple(raw.ch_names))].append(entry["path"])
            official_bytes[(entry["sha256"], clock, tuple(raw.ch_names))].append(entry["path"])
            checks.append({"path": entry["path"], "all_checks_passed": True,
                           "source_annotation_count": len(source_rows),
                           "content_sha256": content_hash})
        finally:
            raw.close()
    assert len(checks) == 327
    assert labels == audit["source_annotation_counts"]
    assert len(annotation_rows) == audit["source_annotation_count"]
    assert fixed_4s_count == audit["fixed_4s_hand_imagery_inventory"]["available_event_count"]
    assert sidecar_count == audit["sidecar_annotation_count"]
    assert len(wfdb_rows) == sidecar_count
    assert {k: dict(v) for k, v in durations.items()} == audit["source_duration_histograms_seconds"]
    duplicate_groups = []
    for method, groups in (("official_sha256", official_bytes),
                           ("signal_content_sha256", signals)):
        duplicate_groups.extend({"method": method, "files": files}
                                for files in groups.values() if len(files) > 1)
    assert duplicate_groups == audit["duplicate_signal_groups"]
    for group in duplicate_groups:
        for path in group["files"]:
            recomputed_flags[path].add("duplicate_complete_source_signal")
    for path, flags in recomputed_flags.items():
        assert sorted(flags) == records[path]["flags"]
    expected_eligible = sorted(r["path"] for r in audit["files"] if not r["flags"])
    assert expected_eligible == sorted(audit["source_qualification"]["pass_eligible_files"])
    assert len(expected_eligible) == audit["source_qualification"]["pass_eligible_file_count"]
    complete_three_run_subjects = sorted(subject for subject, count in Counter(
        r["subject"] for r in audit["files"] if r["path"] in expected_eligible).items() if count == 3)
    assert complete_three_run_subjects == audit["source_qualification"]["pass_eligible_all_three_run_subjects"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump({"verified_at_utc": datetime.now(timezone.utc).isoformat(),
                   "all_checks_passed": True, "synthetic": False,
                   "source_file_count": 654, "signal_file_count": 327,
                   "source_subject_count": 109, "source_bytes": manifest["total_bytes"],
                   "source_annotation_counts": dict(labels),
                   "source_annotation_count": len(annotation_rows),
                   "sidecar_annotation_count": sidecar_count,
                   "complete_4s_imagery_source_window_count": int(fixed_4s_count),
                   "duplicate_signal_groups": duplicate_groups,
                   "resource_audit_status": audit["resource_audit_status"],
                   "source_qualified_signal_count": len(expected_eligible),
                   "source_qualified_complete_three_run_subject_count": len(complete_three_run_subjects),
                   "manifest_file_sha256": file_hash(args.manifest),
                   "primary_audit_file_sha256": file_hash(args.audit_root / "signal_audit.json"),
                   "script_sha256": file_hash(Path(__file__)),
                   "method": "fresh whole-recording read and direct source recheck; no ingestion-helper imports",
                   "no_epochs_no_model_no_retention_claim": True,
                   "checks": checks}, stream, indent=2)
        stream.write("\n")
    print(f"Independent actual source validation passed: {args.output}", flush=True)


if __name__ == "__main__":
    main()
