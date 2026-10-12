"""Recalculate fixed source coverage and replay two raw numeric hashes independently.

Run from the repository root after signal_audit_run02. No production ingress or
audit helper is imported, and no model or window eligibility is selected.
"""

import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import mne
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PLAN = ROOT / "research_logs/public_data_expansion_20261010/kumar2024_ingestion_plan.json"
DATA = ROOT / "data/public_eeg/kumar2024/nm000177/v1.0.5"
AUDIT = HERE / "signal_audit_run02"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    plan = json.loads(PLAN.read_text())
    selection_path = ROOT / plan["selection_manifest_path"]
    assert sha(selection_path) == plan["selection_manifest_sha256"]
    selection = json.loads(selection_path.read_text())
    source_paths = {row["path"] for row in selection}
    actual_paths = {str(p.relative_to(DATA)) for p in DATA.rglob("*") if p.is_file()}
    assert actual_paths == source_paths
    official_verified = 0
    for row in selection:
        path = DATA / row["path"]
        assert path.stat().st_size == row["size"]
        hasher = hashlib.sha256() if row["checksum_algorithm"] == "sha256" else hashlib.sha1()
        if row["checksum_algorithm"] == "git":
            hasher.update(f"blob {row['size']}\0".encode())
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                hasher.update(block)
        assert hasher.hexdigest() == row["checksum"]
        official_verified += 1
    run_records = [json.loads(p.read_text()) for p in sorted((AUDIT / "runs").glob("*.json"))]
    run_map = {r["source_file"]: r for r in run_records}
    assert len(run_map) == len(run_records) == 360
    assert all(r["status"] == "passed" for r in run_records)
    event_records = json.loads((AUDIT / "source_events.json").read_text())
    event_map = {(r["source_file"], r["source_row"]): r for r in event_records}
    assert len(event_map) == len(event_records) == 7200
    counts = Counter()
    sessions = defaultdict(Counter)
    durations = []
    seen = set()
    for entry in selection:
        if not entry["path"].endswith("_events.tsv"):
            continue
        source_file = entry["path"].removesuffix("_events.tsv") + "_eeg.edf"
        with (DATA / entry["path"]).open(newline="") as stream:
            rows = list(csv.DictReader(stream, delimiter="\t"))
        assert len(rows) == 20
        for i, row in enumerate(rows, start=1):
            key = (source_file, i)
            expected = event_map[key]
            onset, duration, sample = float(row["onset"]), float(row["duration"]), int(row["sample"])
            assert expected["label"] == row["trial_type"]
            assert expected["stored_value"] == int(row["value"])
            assert expected["onset_seconds"] == onset
            assert expected["duration_seconds"] == duration
            assert expected["start_sample"] == sample
            assert expected["sample_count"] == round(duration * 512)
            assert expected["stop_sample_exclusive"] <= run_map[source_file]["n_times"]
            assert expected["analysis_eligibility"] == "not_selected_no_model_window_policy_yet"
            seen.add(key)
            counts[row["trial_type"]] += 1
            sessions[(expected["subject"], expected["session"])][row["trial_type"]] += 1
            durations.append(duration)
    assert seen == set(event_map)
    assert counts == {"left_hand": 3600, "right_hand": 3600}
    assert len(sessions) == 108
    for (subject, session), class_counts in sessions.items():
        assert subject in {f"sub-{i}" for i in range(1, 19)}
        assert class_counts == {"left_hand": 40 if session in {"ses-0", "ses-1"} else 30,
                                "right_hand": 40 if session in {"ses-0", "ses-1"} else 30}
    whole_groups, center_groups = defaultdict(list), defaultdict(list)
    for record in run_records:
        whole_groups[record["whole_signal_numeric_sha256"]].append(record["source_file"])
        center_groups[record["central_4KiB_numeric_sha256"]].append(record["source_file"])
    whole_duplicates = [g for g in whole_groups.values() if len(g) > 1]
    center_duplicates = [g for g in center_groups.values() if len(g) > 1]
    replay = []
    for relative in [min(run_map), max(run_map)]:
        record = run_map[relative]
        raw = mne.io.read_raw_edf(DATA / relative, preload=False, verbose="ERROR")
        try:
            digest = hashlib.sha256()
            for start in range(0, int(raw.n_times), 16384):
                values = raw.get_data(start=start, stop=min(start + 16384, int(raw.n_times)))
                assert np.isfinite(values).all()
                digest.update(np.asarray(values, dtype="<f8").tobytes(order="C"))
            assert digest.hexdigest() == record["whole_signal_numeric_sha256"]
            start = max(0, int(raw.n_times) // 2 - 128)
            values = raw.get_data(picks=[0, 1], start=start, stop=start + 256)
            center_digest = hashlib.sha256(np.asarray(values, dtype="<f8").tobytes(order="C")).hexdigest()
            assert center_digest == record["central_4KiB_numeric_sha256"]
            replay.append({"source_file": relative, "whole_signal_numeric_sha256": digest.hexdigest(),
                           "central_4KiB_numeric_sha256": center_digest, "exact_replay": True})
        finally:
            raw.close()
    aggregate = json.loads((AUDIT / "aggregate.json").read_text())
    assert aggregate["source_events"] == len(event_records)
    assert aggregate["source_class_counts"] == counts
    assert aggregate["partial_source_event_count"] == sum(t < 5 for t in durations) == 44
    assert aggregate["duration_exactly5s_count"] == sum(t == 5 for t in durations) == 7156
    assert aggregate["whole_signal_exact_numeric_duplicate_groups"] == whole_duplicates
    assert aggregate["central4KiB_duplicate_groups"] == center_duplicates
    result = {"status": "passed", "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
              "script_sha256": sha(Path(__file__)), "production_helpers_imported": False,
              "all_source_files_independently_official_checksum_verified": official_verified,
              "selected_bytes": sum(e["size"] for e in selection), "EDF_count": len(run_records),
              "source_events": len(event_records), "class_counts": dict(counts),
              "subject_session_pairs": len(sessions), "partial_source_events": 44,
              "whole_signal_duplicate_groups": whole_duplicates, "central4KiB_duplicate_groups": center_duplicates,
              "representative_numeric_replays": replay, "aggregate_sha256": sha(AUDIT / "aggregate.json"),
              "source_events_sha256": sha(AUDIT / "source_events.json"),
              "limits": "No biological identity verification across resources; no model fitting or window selection"}
    destination = HERE / "independent_source_crosscheck.json"
    with destination.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
