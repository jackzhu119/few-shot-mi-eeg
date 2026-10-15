"""Synthetic metadata-only scope tests; never open EEG, event TSV or weights."""

import copy
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

import prepare_kumar_frozen_query_inputs as module
import prepare_kumar_frozen_query_checkpoints as checkpoints


@pytest.fixture
def synthetic_metadata():
    config = {
        "subjects": ["sub-1"], "development_subjects": ["sub-1"], "final_test_subjects": [],
        "split": {"source_session": "ses-0", "source_train_runs": ["run-0", "run-1"],
                  "source_validation_runs": ["run-2"], "source_query_runs": ["run-3"],
                  "target_sessions": [f"ses-{i}" for i in range(1, 6)],
                  "target_support_runs": ["run-0"], "target_query_runs": "all_remaining_runs"},
    }
    paths = {"dataset_description.json"}
    trials = []
    for session in range(6):
        paths.add(f"sub-1/ses-{session}/sub-1_ses-{session}_scans.tsv")
        for run in range(4 if session in {0, 1} else 3):
            prefix = f"sub-1/ses-{session}/eeg/sub-1_ses-{session}_task-imagery_run-{run}"
            paths.update(prefix + "_" + suffix for suffix in module.SUFFIXES)
            role = (["source_train", "source_train", "source_validation", "source_query"][run]
                    if session == 0 else "target_support" if run == 0 else "target_query")
            trials.append({"trial_id": f"sub-1/ses-{session}/run-{run}/row-1", "subject": "sub-1",
                           "source_file": prefix + "_eeg.edf", "role": role, "included": True,
                           "synthetic": True, "software_validation_only": True})
    official, historical, receipts = [], [], []
    for path in sorted(paths):
        body = ("synthetic_metadata_only:" + path).encode()
        sha = hashlib.sha256(body).hexdigest()
        official.append({"path": path, "size": len(body), "checksum_algorithm": "sha256",
                         "checksum": sha, "url": "https://example.invalid/" + path})
        old = {"relative_path": path, "bytes": len(body), "sha256": sha, "key": "synthetic/" + path}
        historical.append(old)
        receipts.append({**old, "verification": "full_get_sha256_verified", "readback_bytes": len(body),
                         "selected_for_full_readback": True})
    hashes = {e["relative_path"]: e["sha256"] for e in historical}
    for trial in trials:
        trial["raw_file_sha256"] = hashes[trial["source_file"]]
    return SimpleNamespace(config=config, split={"trials": trials}, official=official,
                           historical=historical, receipts=receipts)


def select(fixture):
    return module.select_scope(fixture.config, fixture.split, fixture.official,
                               fixture.historical, fixture.receipts)


def test_exact_whole_run_queries_exclude_all_fit_and_support_files(synthetic_metadata):
    fixture = synthetic_metadata
    files, query = select(fixture)
    assert len(files) == 67  # 12 query runs * 5 files + 6 scans + description.
    edfs = [e for e in files if e["relative_path"].endswith(".edf")]
    assert len(edfs) == 12
    assert sum(e["role"] == "source_query" for e in edfs) == 1
    assert sum(e["role"] == "target_query" for e in edfs) == 11
    assert all("run-0_" not in e["relative_path"] for e in files)
    assert all(e["role"] not in {"source_train", "source_validation", "target_support"} for e in files)
    assert [t["trial_id"] for t in query] == [t["trial_id"] for t in fixture.split["trials"]
                                               if t["role"] in module.QUERY_ROLES]


def test_partial_rows_retained_and_metadata_order_not_sorted_by_labels(synthetic_metadata):
    fixture = synthetic_metadata
    rows = fixture.split["trials"]
    rows[-1]["included"] = False
    for row in rows:
        row["label"] = object()  # Selector must never inspect or serialize labels.
    _, query = select(fixture)
    assert query[-1] is rows[-1] and not query[-1]["included"]
    assert len(query) == 12


@pytest.mark.parametrize("kind", ["official", "historical", "receipts"])
def test_duplicate_input_identity_rejected(synthetic_metadata, kind):
    entries = getattr(synthetic_metadata, kind)
    entries.append(copy.deepcopy(entries[0]))
    with pytest.raises(ValueError, match="Duplicate metadata"):
        select(synthetic_metadata)


@pytest.mark.parametrize("kind", ["official", "historical", "receipts"])
def test_missing_trusted_metadata_rejected(synthetic_metadata, kind):
    getattr(synthetic_metadata, kind).pop(0)  # dataset_description.json
    with pytest.raises(ValueError, match="Missing official or prior"):
        select(synthetic_metadata)


@pytest.mark.parametrize("field,value", [("sha256", "unknown"), ("bytes", 1), ("key", "wrong")])
def test_conflicting_historical_identity_rejected(synthetic_metadata, field, value):
    synthetic_metadata.historical[0][field] = value
    with pytest.raises(ValueError, match="SHA256|Conflicting"):
        select(synthetic_metadata)


@pytest.mark.parametrize("field,value", [
    ("verification", "unknown"), ("readback_bytes", 0), ("selected_for_full_readback", False),
])
def test_invalid_historical_provenance_rejected(synthetic_metadata, field, value):
    synthetic_metadata.receipts[0][field] = value
    with pytest.raises(ValueError, match="historical source-byte"):
        select(synthetic_metadata)


def test_historical_head_is_retained_as_identity_never_claimed_full_get(synthetic_metadata):
    receipt = synthetic_metadata.receipts[0]
    receipt.update(verification="head_length_and_sha256_metadata_verified",
                   status="uploaded_head_verified", uploaded_bytes=receipt["bytes"],
                   selected_for_full_readback=False, readback_bytes=0)
    files, _ = select(synthetic_metadata)
    assert files[0]["historical_R2_full_GET_verified"] is False
    assert files[0]["historical_R2_verification"] == "head_length_and_sha256_metadata_verified"


def test_changed_query_run_role_rejected(synthetic_metadata):
    synthetic_metadata.split["trials"][3]["role"] = "source_train"
    with pytest.raises(ValueError, match="Incomplete query"):
        select(synthetic_metadata)


def test_support_contamination_rejected(synthetic_metadata):
    synthetic_metadata.split["trials"][4]["role"] = "target_query"
    with pytest.raises(ValueError, match="Incomplete query"):
        select(synthetic_metadata)


def test_mixed_role_same_run_rejected(synthetic_metadata):
    trial = copy.deepcopy(synthetic_metadata.split["trials"][3])
    trial.update(trial_id=trial["trial_id"] + "-extra", role="source_train")
    synthetic_metadata.split["trials"].append(trial)
    with pytest.raises(ValueError, match="Mixed or changed"):
        select(synthetic_metadata)


def test_split_sha_conflict_rejected(synthetic_metadata):
    synthetic_metadata.split["trials"][3]["raw_file_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="Split and archived"):
        select(synthetic_metadata)


def test_default_checker_and_exclusive_creation_are_metadata_only(tmp_path, monkeypatch, capsys):
    manifest = {"file_count": 67, "bytes": 123, "edf_count": 12,
                "execution_enabled": False, "synthetic": True, "software_validation_only": True}
    monkeypatch.setattr(module, "build_manifest", lambda: manifest)
    path = tmp_path / "manifest.json"
    module.main(["--output", str(path), "--write"])
    original = path.read_bytes()
    module.main(["--output", str(path)])
    assert path.read_bytes() == original
    assert '"raw_query_files_read": false' in capsys.readouterr().out
    with pytest.raises(FileExistsError):
        module.main(["--output", str(path), "--write"])
    assert list(tmp_path.iterdir()) == [path]


def test_real_preparation_reads_only_pinned_metadata_not_query_data(monkeypatch):
    original = Path.read_bytes
    paths = []

    def guarded(path):
        relative = path.relative_to(module.ROOT).as_posix()
        assert relative in module.PINS or relative.startswith(module.PRIOR + "/runs/")
        assert not relative.startswith("data/")
        paths.append(relative)
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", guarded)
    manifest = module.build_manifest()
    assert manifest["execution_enabled"] is False
    assert (manifest["file_count"], manifest["bytes"], manifest["edf_count"]) == (1189, 1043686331, 216)
    assert (len(manifest["ordered_query_trial_ids"]), len(manifest["included_query_trial_ids"])) == (4320, 4290)
    assert len(paths) == len(module.PINS) + 216
    assert len(manifest["dependencies"]) == len(paths)


@pytest.fixture
def synthetic_checkpoint_metadata():
    job = {"job_id": "a" * 64, "subject": "sub-1", "seed": 20261012,
           "result_key": "synthetic/sub-1-seed-20261012-run01.tar", "archive_sha256": "b" * 64,
           "receipt": "synthetic/receipt.json", "parent_acknowledgement": "synthetic/ack.json"}
    entry = {"key": job["result_key"], "sha256": job["archive_sha256"], "bytes": 143360,
             "verification": "full_get_sha256_verified", "selected_for_full_readback": True,
             "readback_bytes": 143360}
    receipt = {"status": "completed", "files": [entry]}
    ack = {"status": "parent_acknowledged", "receipt_sha256": "c" * 64}
    checkpoint = {**job, "checkpoint_sha256": "d" * 64,
                  "synthetic": True, "software_validation_only": True}
    return SimpleNamespace(job=job, plan=copy.deepcopy(job), receipt=receipt, ack=ack,
                           checkpoint=checkpoint)


def checkpoint_entry(fixture):
    return checkpoints.checked_entry(fixture.job, fixture.plan, fixture.receipt, "c" * 64,
                                     fixture.ack, fixture.checkpoint)


def test_checkpoint_archive_identity_uses_original_and_matching_full_get_length(synthetic_checkpoint_metadata):
    fixture = synthetic_checkpoint_metadata
    fixture.checkpoint["metadata_read_from_archive_sha256"] = "e" * 64  # Replay metadata source.
    result = checkpoint_entry(fixture)
    assert result["archive_sha256"] == "b" * 64
    assert result["archive_bytes"] == 143360
    assert result["checkpoint_sha256"] == "d" * 64
    assert result["filename"] == "sub-1-seed-20261012-run01.tar"


@pytest.mark.parametrize("failure", ["replay", "partial_get", "duplicate_key", "unacknowledged", "wrong_receipt", "wrong_checkpoint", "different_order"])
def test_checkpoint_metadata_rejects_identity_and_acceptance_conflicts(synthetic_checkpoint_metadata, failure):
    fixture = synthetic_checkpoint_metadata
    if failure == "replay":
        fixture.receipt["files"][0]["sha256"] = "e" * 64
    elif failure == "partial_get":
        fixture.receipt["files"][0]["readback_bytes"] -= 1
    elif failure == "duplicate_key":
        fixture.receipt["files"].append(copy.deepcopy(fixture.receipt["files"][0]))
    elif failure == "unacknowledged":
        fixture.ack["status"] = "pending"
    elif failure == "wrong_receipt":
        fixture.ack["receipt_sha256"] = "0" * 64
    elif failure == "wrong_checkpoint":
        fixture.checkpoint["job_id"] = "0" * 64
    else:
        fixture.plan["seed"] = 20261013
    with pytest.raises(ValueError):
        checkpoint_entry(fixture)


def test_accepted54_deployment_builder_only_reads_repository_json(monkeypatch):
    original = Path.read_bytes
    seen = []

    def guarded(path):
        relative = path.relative_to(checkpoints.ROOT).as_posix()
        assert relative.startswith(("research_logs/", "configs/")) and relative.endswith(".json")
        seen.append(relative)
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", guarded)
    manifest = checkpoints.build_manifest()
    assert manifest["model_count"] == len(manifest["models"]) == 54
    assert [m["accepted_position"] for m in manifest["models"]] == list(range(1, 55))
    assert manifest["execution_enabled"] is False and manifest["archives_read"] is False
    assert manifest["models"][0]["archive_sha256"] == "2a4d0dd291f1f93bc0560e39b99b2e76fbf6bcba0d3a363ceb522fb4afea0f62"
    assert manifest["models"][0]["archive_bytes"] == 143360
    assert manifest["models"][0]["archive_sha256"] != manifest["first_model_replay_archive_excluded_sha256"]
    assert len(seen) == len(manifest["dependencies"])
