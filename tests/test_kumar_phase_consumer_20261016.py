"""Synthetic consumer lifecycle tests; no original EEG, source NPZ or science fit."""
from __future__ import annotations

import copy
import csv
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]


def load_script(name, filename):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """All file content, source state, raw objects and fitted state are synthetic."""
    phase = load_script("synthetic_phase_consumer", "run_kumar_phase_window_cpu_20261016.py")
    common = load_script("synthetic_common_helpers", "run_kumar_component_budget_cpu_20261016.py")
    monkeypatch.setattr(phase, "ROOT", tmp_path)
    monkeypatch.setattr(common, "ROOT", tmp_path)
    main = ModuleType("__main__")
    main.__file__ = str(tmp_path / "scripts/run_kumar_component_budget_cpu_20261016.py")
    for name in ("sha256_file", "read_json", "write_json", "write_csv", "save_model_state",
                 "verify_subject_inputs_after"):
        setattr(main, name, getattr(common, name))
    main.git_head = lambda: "synthetic-software-test-commit"
    main.verify_pins = lambda pins: None
    main.verify_input_text_pins = lambda config, old: None
    monkeypatch.setitem(sys.modules, "__main__", main)

    def dump(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def csv_dump(path, rows):
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    from learning_preserving_bci.datasets.kumar import CHANNEL_NAMES, numeric_hash

    zeros = {count: np.zeros((22, count), dtype=np.float64) for count in (1024, 2560)}
    processed = {count: np.zeros((22, count // 4), dtype=np.float32) for count in (1024, 2560)}
    raw_hash = numeric_hash(zeros[2560])
    processed_hash = numeric_hash(processed[2560], dtype="<f4")
    monkeypatch.setattr(phase, "preprocess_window", lambda array, window: processed[array.shape[1]].copy())
    data = tmp_path / "data"
    baseline = tmp_path / "historical"
    entries, trials, mappings, saved, raw_reads, loads, fits = [], [], [], [], [], [], []
    outputs = {}
    subjects = [f"synthetic-{index}" for index in range(1, 19)]

    def add_data(relative, payload):
        path = data / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        digest = common.sha256_file(path)
        entries.append({"path": relative, "size": len(payload), "checksum_algorithm": "sha256", "checksum": digest})
        return digest

    add_data("dataset_description.json", json.dumps({"Version": "1.0.5", "DatasetType": "derivative", "License": "CC-BY-4.0", "synthetic": True}).encode())
    for subject in subjects:
        relative = f"{subject}/synthetic_eeg.edf"
        digest = add_data(relative, b"synthetic software test; never opened as real EEG")
        prefix = relative.removesuffix("_eeg.edf")
        for suffix in ("_eeg.json", "_events.json", "_events.tsv", "_channels.tsv"):
            add_data(prefix + suffix, b"synthetic metadata")
        for session in ("ses-0", *phase.SESSIONS):
            add_data(f"{subject}/{session}/{subject}_{session}_scans.tsv", b"synthetic scan metadata")
        dump(tmp_path / "prior/runs" / (relative.replace("/", "__") + ".json"), {"n_times": 2_000_000, "status": "passed", "synthetic": True})
        for name in ("source_before.npz", "source_after.npz", "participant_receipt.json", "fit_access_audit.json"):
            path = baseline / subject / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"synthetic never-loaded historical state placeholder")
            outputs[f"{subject}/{name}"] = common.sha256_file(path)
        # Exactly 400 rows. Unused validation/source-query identities deliberately
        # dominate this synthetic fixture to make forbidden-role access visible.
        for index in range(400):
            if index < 40:
                role, session = "source_train", "ses-0"
            elif index < 210:
                role, session = "source_validation", "ses-0"
            elif index < 380:
                role, session = "source_query", "ses-0"
            else:
                session = f"ses-{(index - 380) // 4 + 1}"
                role = "target_support" if (index - 380) % 4 < 2 else "target_query"
            label = "left_hand" if index % 2 == 0 else "right_hand"
            cue = index * 4096
            trial_id = f"{subject}/{session}/{role}/{index}"
            trials.append({"trial_id": trial_id, "subject": subject, "cohort": "synthetic",
                           "session": session, "run": "synthetic-run", "label": label, "role": role,
                           "included": True, "sample_count": 2560, "start_sample": cue, "source_file": relative,
                           "raw_file_sha256": digest, "raw_window_numeric_sha256": raw_hash,
                           "processed_window_numeric_sha256": processed_hash})
            mappings.append({"trial_id": trial_id, "subject": subject, "session": session,
                             "run": "synthetic-run", "class": label, "cue_mapping_exact": True,
                             "phase_mapping_success": True, "cue_sample_0based": cue,
                             "task_start_sample_0based": cue + 768, "task_end_sample_0based": cue + 2304,
                             "sample_rate": 512, "task_start_code": 7691 + (index % 2) * 10,
                             "task_end_code": 7692 + (index % 2) * 10, "recording_n_samples": 2_000_000})
            if role == "target_query":
                saved.append({"trial_id": trial_id, "subject": subject, "session": session,
                              "method": "source_only", "synthetic": False, "label": index % 2, "prediction": 0})
    csv_dump(tmp_path / "predictions.csv", saved)
    outputs["query_predictions.csv"] = common.sha256_file(tmp_path / "predictions.csv")
    dump(baseline / "execution_receipt.json", {"outputs": outputs, "synthetic": True})
    dump(tmp_path / "old.json", {"source_manifest": "source_manifest.json", "prior_signal_audit": "prior"})
    dump(tmp_path / "source_manifest.json", entries)
    dump(tmp_path / "split.json", {"trials": trials, "synthetic": True})
    dump(tmp_path / "claim.json", {"deadline_epoch": phase.time.time() + 600, "synthetic": True})
    csv_dump(tmp_path / "mapping.csv", mappings)
    (tmp_path / "protocol.md").write_text("synthetic software validation only", encoding="utf-8")
    monkeypatch.setattr(phase, "PROTOCOL_SHA256", common.sha256_file(tmp_path / "protocol.md"))
    config = {"analysis_mode": "phase_window", "phase_settings": copy.deepcopy(phase.PHASE_SETTINGS),
              "phase_mapping": "mapping.csv", "phase_mapping_sha256": common.sha256_file(tmp_path / "mapping.csv"),
              "input_text_pins": {"mapping.csv": common.sha256_file(tmp_path / "mapping.csv")},
              "old_config": "old.json", "data_root": "data", "subjects": subjects, "source_code_pins": {},
              "baseline_execution_receipt_sha256": common.sha256_file(baseline / "execution_receipt.json")}
    dump(tmp_path / "config.json", config)
    dump(tmp_path / "authorization.json", {"synthetic": True, "software_validation_only": True})
    args = SimpleNamespace(protocol=tmp_path / "protocol.md", split_manifest=tmp_path / "split.json",
                           baseline_root=baseline, saved_predictions=tmp_path / "predictions.csv",
                           output=tmp_path / "output", claim=tmp_path / "claim.json",
                           config=tmp_path / "config.json", authorization=tmp_path / "authorization.json")

    def load_source(root, subject):
        loads.append(subject)
        return {"synthetic_state": np.asarray([1.0])}

    main.load_verified_source_model = load_source
    main.verify_historical_fit_scope = lambda root, subject, rows: {"synthetic": True, "rows": len(rows)}

    class SyntheticRaw:
        first_samp = 0
        info = {"sfreq": 512}
        ch_names = list(CHANNEL_NAMES)
        n_times = 2_000_000
        _orig_units = dict.fromkeys(CHANNEL_NAMES, "µV")

        def get_channel_types(self):
            return ["eeg"] * 22

        def get_data(self, *, start, stop):
            raw_reads.append((self.subject, start, stop))
            return zeros[stop - start].copy()

        def close(self):
            pass

    def open_raw(path, **kwargs):
        raw = SyntheticRaw()
        raw.subject = Path(path).parent.name
        return raw

    import mne
    monkeypatch.setattr(mne.io, "read_raw_edf", open_raw)

    def evaluate(**kwargs):
        # No estimator is built. A synthetic finite checkpoint exercises the real
        # persistence/hash callback in the thin consumer, not scientific fitting.
        subject = kwargs["subject"]
        fits.append(subject)
        context = {"kind": "fit_attempt", "subject": subject, "window": "task2s", "session": "ses-0", "method": "source_only"}
        kwargs["emit"](context)
        kwargs["model_sink"]({"synthetic_state": np.asarray([2.0])}, context)
        metrics, predictions = [], []
        for session in phase.SESSIONS:
            query = [row for row in kwargs["selected"] if row["role"] == "target_query" and row["session"] == session]
            for window in phase.WINDOWS:
                for method in phase.METHODS:
                    metrics.append({"subject": subject, "cohort": "synthetic", "session": session,
                                    "window": window, "method": method, "balanced_accuracy": 0.5 if query else None,
                                    "n_unknown_query_phase": 0, "synthetic": True})
                    predictions.extend({"trial_id": row["trial_id"], "subject": subject, "session": session,
                                        "window": window, "method": method, "label": row["label"], "prediction": 0,
                                        "synthetic": True} for row in query)
        return {"metrics": metrics, "predictions": predictions, "fit_access_audit": [],
                "original_cue_state_sha256_before": "synthetic", "original_cue_state_sha256_after": "synthetic"}

    monkeypatch.setattr(phase, "evaluate_participant", evaluate)
    return SimpleNamespace(phase=phase, common=common, main=main, config=config, args=args,
                           root=tmp_path, trials=trials, mappings=mappings, saved=saved, fits=fits,
                           loads=loads, raw_reads=raw_reads, dump=dump, csv_dump=csv_dump)


def test_canonical_guard_rejects_an_unrelated_main_script(sandbox, monkeypatch):
    monkeypatch.setattr(sandbox.main, "__file__", str(sandbox.root / "unrelated.py"))
    with pytest.raises(ValueError, match="canonical"):
        sandbox.phase.execute_bound_inputs(sandbox.args, sandbox.config)
    assert not sandbox.args.output.exists() and sandbox.fits == []


@pytest.mark.parametrize("change,message", [
    ("mode", "settings"), ("settings", "settings"), ("protocol", "protocol"),
    ("mapping_bytes", "pinned"), ("mapping_pin", "pinned"), ("mapping_unsafe", "pinned"),
])
def test_unfrozen_identity_stops_before_signal_or_state_access(sandbox, change, message):
    config = copy.deepcopy(sandbox.config)
    if change == "mode":
        config["analysis_mode"] = "unfrozen"
    elif change == "settings":
        config["phase_settings"]["window_seconds"] = 3.0
    elif change == "protocol":
        sandbox.args.protocol.write_text("mutated synthetic protocol")
    elif change == "mapping_bytes":
        with (sandbox.root / "mapping.csv").open("a") as handle:
            handle.write("\n")
    elif change == "mapping_pin":
        config["input_text_pins"]["mapping.csv"] = "unfrozen"
    else:
        config["phase_mapping"] = "../mapping.csv"
    with pytest.raises(ValueError, match=message):
        sandbox.phase.execute_bound_inputs(sandbox.args, config)
    assert sandbox.loads == sandbox.raw_reads == sandbox.fits == []
    assert not sandbox.args.output.exists()


def test_complete_synthetic_lifecycle_preserves_all_540_cells_and_hashes(sandbox):
    sandbox.phase.execute_bound_inputs(sandbox.args, sandbox.config)
    output = sandbox.args.output
    receipt = json.loads((output / "execution_receipt.json").read_text())
    assert receipt["rows"] == 540 and receipt["query_or_validation_fitted"] is False
    assert receipt["EEGNet_models_loaded_or_refitted"] is False
    assert len(sandbox.fits) == len(sandbox.loads) == 18
    with (output / "metrics.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 540
    assert len({(row["subject"], row["session"], row["window"], row["method"]) for row in rows}) == 540
    manifest = json.loads((output / "input_before_after_manifest.json").read_text())
    assert manifest["before_after_equal"] is True
    assert len(manifest["historical_source_inputs"]) == 18 * 4
    for path, expected in {**manifest["dataset_inputs"], **manifest["historical_source_inputs"]}.items():
        assert sandbox.common.sha256_file(path) == expected
    forbidden_cues = {row["start_sample"] for row in sandbox.trials if row["role"] in {"source_validation", "source_query"}}
    assert len(sandbox.raw_reads) == 18 * 60 * 2
    assert all(start not in forbidden_cues and start - 768 not in forbidden_cues
               for _, start, _ in sandbox.raw_reads)
    assert not (output / "consumer_exception_receipt.json").exists()


@pytest.mark.parametrize("failure", ["checkpoint_write", "checkpoint_hash"])
def test_checkpoint_failures_stop_before_another_fit_or_participant(sandbox, monkeypatch, failure):
    if failure == "checkpoint_write":
        def fail(*args, **kwargs):
            raise OSError("synthetic checkpoint storage failure")
        monkeypatch.setattr(sandbox.main, "save_model_state", fail)
        expected = OSError
    else:
        original = sandbox.common.sha256_file
        def fail(path):
            if "private_models" in Path(path).parts:
                raise ValueError("synthetic checkpoint hash integrity failure")
            return original(path)
        # The real checkpoint helper resolves its hash in this helper module.
        monkeypatch.setattr(sandbox.common, "sha256_file", fail)
        expected = ValueError
    with pytest.raises(expected, match="synthetic checkpoint"):
        sandbox.phase.execute_bound_inputs(sandbox.args, sandbox.config)
    assert sandbox.fits == sandbox.loads == ["synthetic-1"]
    receipt = json.loads((sandbox.args.output / "consumer_exception_receipt.json").read_text())
    assert receipt["subject"] == "synthetic-1" and receipt["scientific_retry"] is False
    assert receipt["partial_and_claim_preserved"] is True
    assert (sandbox.args.output / "synthetic-1/partial_evidence.jsonl").is_file()
    assert not (sandbox.args.output / "synthetic-2").exists()
    assert not (sandbox.args.output / "execution_receipt.json").exists()
    if failure == "checkpoint_hash":
        assert len(list((sandbox.args.output / "synthetic-1/private_models").rglob("*.npz"))) == 1


def test_post_input_mutation_fails_before_next_participant(sandbox, monkeypatch):
    original = sandbox.main.verify_subject_inputs_after
    def mutate(root, subject, data_root, provenance):
        path = Path(root) / subject / "source_before.npz"
        path.write_bytes(b"synthetic mutation")
        return original(root, subject, data_root, provenance)
    monkeypatch.setattr(sandbox.main, "verify_subject_inputs_after", mutate)
    with pytest.raises(ValueError, match="Historical source input changed"):
        sandbox.phase.execute_bound_inputs(sandbox.args, sandbox.config)
    assert sandbox.fits == ["synthetic-1"]
    assert not (sandbox.args.output / "synthetic-2").exists()


def test_final_shared_input_mutation_prevents_completed_receipt(sandbox, monkeypatch):
    def mutate(pins):
        with (sandbox.root / "mapping.csv").open("a") as handle:
            handle.write("\n")
    monkeypatch.setattr(sandbox.main, "verify_pins", mutate)
    with pytest.raises(ValueError, match="mapping changed"):
        sandbox.phase.execute_bound_inputs(sandbox.args, sandbox.config)
    assert len(sandbox.fits) == 18
    assert not (sandbox.args.output / "execution_receipt.json").exists()
    assert (sandbox.args.output / "consumer_exception_receipt.json").is_file()


def test_all_missing_target_queries_retain_540_null_cells_not_empty_table_failure(sandbox):
    for row in sandbox.mappings:
        if "/target_query/" in row["trial_id"]:
            row["phase_mapping_success"] = False
    sandbox.csv_dump(sandbox.root / "mapping.csv", sandbox.mappings)
    digest = sandbox.common.sha256_file(sandbox.root / "mapping.csv")
    sandbox.config["phase_mapping_sha256"] = digest
    sandbox.config["input_text_pins"]["mapping.csv"] = digest
    sandbox.phase.execute_bound_inputs(sandbox.args, sandbox.config)
    with (sandbox.args.output / "metrics.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 540 and all(row["balanced_accuracy"] == "" for row in rows)
    empty = json.loads((sandbox.args.output / "query_predictions_empty.json").read_text())
    assert empty["rows"] == 0 and empty["all_540_cells_retained_in_metrics"] is True
    contrasts = json.loads((sandbox.args.output / "paired_contrasts.json").read_text())
    assert all(row["n_participants"] == 0 and row["mean_difference_ba"] is None for row in contrasts)
    assert (sandbox.args.output / "execution_receipt.json").is_file()


@pytest.mark.parametrize("kind", ["duplicate_trial", "wrong_phase_class", "saved_prediction_sha"])
def test_frozen_metadata_identity_failure_stops_before_real_input_access(sandbox, kind):
    if kind == "duplicate_trial":
        sandbox.trials[-1]["trial_id"] = sandbox.trials[-2]["trial_id"]
        sandbox.dump(sandbox.args.split_manifest, {"trials": sandbox.trials})
    elif kind == "wrong_phase_class":
        sandbox.mappings[0]["class"] = "right_hand"
        sandbox.csv_dump(sandbox.root / "mapping.csv", sandbox.mappings)
        digest = sandbox.common.sha256_file(sandbox.root / "mapping.csv")
        sandbox.config["phase_mapping_sha256"] = digest
        sandbox.config["input_text_pins"]["mapping.csv"] = digest
    else:
        with sandbox.args.saved_predictions.open("a") as handle:
            handle.write("\n")
    with pytest.raises(ValueError):
        sandbox.phase.execute_bound_inputs(sandbox.args, sandbox.config)
    assert sandbox.loads == sandbox.raw_reads == sandbox.fits == []
    assert not sandbox.args.output.exists()


@pytest.mark.parametrize("field", ["raw_file_sha256", "raw_window_numeric_sha256", "processed_window_numeric_sha256"])
def test_frozen_source_byte_or_numeric_digest_mismatch_prevents_first_fit(sandbox, field):
    sandbox.trials[0][field] = "not-a-matching-synthetic-hash"
    sandbox.dump(sandbox.args.split_manifest, {"trials": sandbox.trials})
    with pytest.raises(ValueError, match="SHA"):
        sandbox.phase.execute_bound_inputs(sandbox.args, sandbox.config)
    assert sandbox.fits == [] and sandbox.loads == ["synthetic-1"]
    receipt = json.loads((sandbox.args.output / "consumer_exception_receipt.json").read_text())
    assert receipt["exception"] == "ValueError" and receipt["scientific_retry"] is False
    assert not (sandbox.args.output / "synthetic-2").exists()


def test_preexpired_claim_retains_failure_without_read_or_fit(sandbox):
    sandbox.dump(sandbox.args.claim, {"deadline_epoch": sandbox.phase.time.time() + 29, "synthetic": True})
    with pytest.raises(TimeoutError, match="cleanup reserve"):
        sandbox.phase.execute_bound_inputs(sandbox.args, sandbox.config)
    assert sandbox.loads == sandbox.raw_reads == sandbox.fits == []
    assert sandbox.args.claim.exists()
    assert (sandbox.args.output / "consumer_exception_receipt.json").is_file()
