"""Independent file/TSV coverage and representative numeric replay; no training.

Usage: python .../independent_milimb_liu_crosscheck.py milimbeeg|liu2024
No production downloader/auditor helper is imported. Original bytes are read only.
"""

import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import mne
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
NAME = sys.argv[1]
assert NAME in {"milimbeeg", "liu2024"}
OUT = ROOT / "research_logs/public_data_expansion_20261010" / (NAME + "_ingestion")
PLAN = json.loads((OUT / "ingestion_plan.json").read_text())
DATA = ROOT / "data/public_eeg" / NAME / PLAN["nemar_id"] / PLAN["version"]
AUDIT = OUT / "signal_audit_run01"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    selection_path = ROOT / PLAN["selection_manifest_path"]
    assert sha(selection_path) == PLAN["selection_manifest_sha256"]
    selection = json.loads(selection_path.read_text())
    assert {e["path"] for e in selection} == {str(p.relative_to(DATA)) for p in DATA.rglob("*") if p.is_file()}
    for entry in selection:
        path = DATA / entry["path"]
        assert path.stat().st_size == entry["size"]
        digest = hashlib.sha256() if entry["checksum_algorithm"] == "sha256" else hashlib.sha1()
        if entry["checksum_algorithm"] == "git":
            digest.update(f"blob {entry['size']}\0".encode())
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1048576), b""):
                digest.update(block)
        assert digest.hexdigest() == entry["checksum"]
    sfreq = 125 if NAME == "milimbeeg" else 500
    suffix = ".edf" if NAME == "milimbeeg" else ".bdf"
    runs = [json.loads(p.read_text()) for p in (AUDIT / "runs").glob("*.json")]
    assert len(runs) == PLAN["signal_file_count"] and all(r["status"] == "passed" for r in runs)
    run_map = {r["source_file"]: r for r in runs}
    assert len(run_map) == len(runs)
    events = json.loads((AUDIT / "source_events.json").read_text())
    event_map = {(e["source_file"], e["source_row"]): e for e in events}
    assert len(event_map) == len(events)
    seen = set()
    label_counts, duration_counts, kind_counts = Counter(), Counter(), Counter()
    per_subject = defaultdict(Counter)
    for entry in selection:
        if not entry["path"].endswith("_events.tsv"):
            continue
        signal_path = entry["path"].removesuffix("_events.tsv") + "_eeg" + suffix
        with (DATA / entry["path"]).open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream, delimiter="\t"))
        for i, row in enumerate(rows, 1):
            key = signal_path, i
            e = event_map[key]
            assert e["label"] == row["trial_type"] and e["stored_value"] == int(row["value"])
            assert e["onset_seconds"] == float(row["onset"])
            assert e["duration_seconds"] == float(row["duration"])
            assert e["start_sample"] == int(row["sample"])
            assert e["duration_samples_as_stored"] == round(float(row["duration"]) * sfreq)
            assert e["stop_sample_exclusive"] <= run_map[signal_path]["n_times"]
            boundary = row["trial_type"] == "EDGE boundary"
            kind = "concatenation_boundary" if boundary else "positive_duration_task"
            assert e["source_event_kind"] == kind
            assert (float(row["duration"]) == 0) == boundary
            assert e["analysis_eligibility"] == "unselected;no_model_window_policy"
            label_counts[row["trial_type"]] += 1
            duration_counts[str(float(row["duration"]))] += 1
            kind_counts[kind] += 1
            per_subject[e["subject"]][row["trial_type"]] += 1
            seen.add(key)
    assert seen == set(event_map)
    groups = {}
    for field in ["whole_signal_numeric_sha256", "central4KiB_numeric_sha256"]:
        by_hash = defaultdict(list)
        for run in runs:
            by_hash[run[field]].append(run["source_file"])
        groups[field] = sorted(sorted(paths) for paths in by_hash.values() if len(paths) > 1)
    replay = []
    for signal_path in [min(run_map), max(run_map)]:
        reader = mne.io.read_raw_edf if suffix == ".edf" else mne.io.read_raw_bdf
        raw = reader(DATA / signal_path, preload=False, verbose="ERROR")
        try:
            whole = hashlib.sha256()
            for start in range(0, int(raw.n_times), 16384):
                values = raw.get_data(start=start, stop=min(start + 16384, int(raw.n_times)))
                assert np.isfinite(values).all()
                whole.update(np.asarray(values, dtype="<f8").tobytes(order="C"))
            start = max(0, int(raw.n_times) // 2 - 128)
            values = raw.get_data(picks=[0, 1], start=start, stop=start + 256)
            center = hashlib.sha256(np.asarray(values, dtype="<f8").tobytes(order="C")).hexdigest()
            assert whole.hexdigest() == run_map[signal_path]["whole_signal_numeric_sha256"]
            assert center == run_map[signal_path]["central4KiB_numeric_sha256"]
            replay.append({"source_file": signal_path, "full_numeric_replay_exact": True,
                           "full_numeric_sha256": whole.hexdigest(), "central4KiB_sha256": center})
        finally:
            raw.close()
    aggregate = json.loads((AUDIT / "aggregate.json").read_text())
    assert aggregate["complete"] and not aggregate["representative_only"]
    assert aggregate["source_event_count"] == len(events)
    assert aggregate["source_label_counts"] == label_counts
    assert aggregate["source_duration_counts"] == duration_counts
    assert aggregate["source_event_kind_counts"] == kind_counts
    assert len(per_subject) == aggregate["source_identity_count"] == PLAN["published_resource_ids"]
    for field, values in groups.items():
        assert sorted(sorted(g) for g in aggregate["exact_numeric_duplicate_groups"][field]) == values
    result = {"status": "passed", "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
              "dataset": PLAN["dataset_id"], "version": PLAN["version"], "production_helpers_imported": False,
              "script_sha256": sha(Path(__file__)), "source_files_official_checksum_recalculated": len(selection),
              "selected_bytes": sum(e["size"] for e in selection), "signal_file_count": len(runs),
              "published_resource_ids": len(per_subject), "source_rows_one_to_one_verified": len(events),
              "source_label_counts": dict(label_counts), "source_duration_counts": dict(duration_counts),
              "source_event_kind_counts": dict(kind_counts), "exact_numeric_duplicate_groups": groups,
              "representative_numeric_replays": replay, "aggregate_sha256": sha(AUDIT / "aggregate.json"),
              "source_events_sha256": sha(AUDIT / "source_events.json"),
              "nonstandard_subject_class_counts": {s: dict(c) for s, c in per_subject.items()
                  if NAME == "milimbeeg" and c != {"EDGE boundary": 61, "clh": 5, "crh": 5,
                                                    "dlf": 5, "drf": 5, "plf": 5, "prf": 5, "rest": 31}},
              "scope": "independent resource validation only; no biological cross-resource identity or model/retention evidence"}
    with (OUT / "independent_source_crosscheck.json").open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
