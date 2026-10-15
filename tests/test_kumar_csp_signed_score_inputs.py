"""Synthetic metadata/opaque-byte guards; never deserialize actual EEG or models."""
from __future__ import annotations

import ast
import copy
import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "csp_input_checker", Path(__file__).parents[1] / "scripts/check_kumar_csp_signed_score_inputs.py")
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def identity(path, relative):
    return {"path": relative, "bytes": path.stat().st_size, "sha256": checker.digest(path)}


@pytest.fixture
def prepared(tmp_path):
    binding = copy.deepcopy(json.loads(checker.BINDING.read_text()))
    epochs = tmp_path / binding["defaults"]["epochs_root"]
    baseline = tmp_path / binding["defaults"]["baseline_root"]
    required, raw, participants, remote = [], {}, [], []
    for position, subject in enumerate(checker.SUBJECTS):
        metadata = []
        for session, runs, role in [(0, [0, 1], "source_train")] + [
                (value, [0], "target_support") for value in range(1, 6)]:
            for run in runs:
                count = 19 if position in (0, 1, 3, 5) and session == 1 else 20
                source_file = f"{subject}/ses-{session}/eeg/{subject}_ses-{session}_task-imagery_run-{run}_eeg.edf"
                raw[source_file] = {"path": source_file, "sha256": "e" * 64}
                for number in range(1, count + 1):
                    metadata.append({"subject": subject, "cohort": "development", "role": role,
                                     "session": f"ses-{session}", "run": f"run-{run}",
                                     "source_row": number,
                                     "trial_id": f"{subject}/ses-{session}/run-{run}/row-{number}",
                                     "label": "left_hand" if number <= count // 2 else "right_hand",
                                     "source_file": source_file, "raw_file_sha256": "e" * 64})
        folder = epochs / subject
        write(folder / "included_trial_metadata.json", metadata)
        (folder / "restricted_epochs.npz").write_bytes(b"SYNTHETIC OPAQUE BYTES, NEVER NPZ-DECODED")
        role_counts = {"source_train": 40, "target_support": len(metadata) - 40}
        write(folder / "subject_receipt.json", {
            "subject": subject, "cohort": "development", "status": "passed", "synthetic": False,
            "metadata_sha256": checker.digest(folder / "included_trial_metadata.json"),
            "epochs_sha256": checker.digest(folder / "restricted_epochs.npz"),
            "trial_count": len(metadata), "role_counts": role_counts, "query_windows_read": 0,
            "validation_windows_read": 0, "final_cohort_access": False})
        participants.append({"subject": subject, "role_counts": role_counts,
                             "trial_count": len(metadata), "source_file_count": 7})
        for kind, root, names in (("epochs", epochs, checker.EPOCH_NAMES),
                                  ("baseline", baseline, checker.BASELINE_NAMES)):
            for name in sorted(names):
                path = root / subject / name
                if kind == "baseline":
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(b"SYNTHETIC OPAQUE MODEL/RECEIPT BYTES")
                row = identity(path, f"{subject}/{name}")
                row["root"] = kind
                required.append(row)
                if kind == "baseline":
                    remote.append({"relative_path": row["path"], "sha256": row["sha256"],
                                   "bytes": row["bytes"], "readback_bytes": row["bytes"],
                                   "verification": "full_get_sha256_verified",
                                   "head_http_status": 200, "get_http_status": 200})
    for relative in checker.SOURCE_BINDINGS:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"SYNTHETIC PINNED SOURCE BINDING")
    write(tmp_path / binding["baseline_R2_receipt_path"],
          {"status": "completed", "readback_mode": "all", "files": remote})
    binding["required_files"] = required
    binding["participants"] = participants
    binding["source_EDF_identities_metadata_only"] = [raw[key] for key in sorted(raw)]
    path = tmp_path / "binding.json"

    def seal():
        for row in binding["source_bindings"]:
            row.update(identity(tmp_path / row["path"], row["path"]))
        for row in binding["required_files"]:
            root = epochs if row["root"] == "epochs" else baseline
            candidate = root / row["path"]
            if candidate.is_file():
                row.update(identity(candidate, row["path"]))
        write(path, binding)
        return checker.digest(path)

    def run(*, refresh=True, **kwargs):
        expected = seal() if refresh else checker.digest(path)
        return checker.check_inputs(path, repo_root=tmp_path, expected_binding_sha256=expected,
                                    **kwargs)

    seal()
    return tmp_path, binding, epochs, baseline, seal, run


def test_exact_selected_scope_and_opaque_blobs_verified_without_writes(prepared):
    root, _, _, _, seal, run = prepared
    seal()
    before = {str(path): checker.digest(path) for path in root.rglob("*") if path.is_file()}
    result = run(refresh=False)
    after = {str(path): checker.digest(path) for path in root.rglob("*") if path.is_file()}
    assert before == after
    assert result["status"] == "metadata_verified_execution_closed"
    assert result["artifact_count"] == 42
    assert result["source_train_rows"] == 240 and result["target_support_rows"] == 596
    assert result["numerical_arrays_deserialized"] is False
    assert result["new_fits"] == result["query_rows_loaded"] == 0
    assert result["execution_authorized"] is False


def test_unapproved_binary_tamper_rejected_before_metadata(prepared):
    _, _, epochs, _, _, run = prepared
    (epochs / "sub-1/restricted_epochs.npz").write_bytes(b"TAMPERED")
    with pytest.raises(ValueError, match="Pinned bytes/SHA256 mismatch"):
        run(refresh=False)


@pytest.mark.parametrize("change", ["query", "final", "support_run", "duplicate", "source_class", "raw_path"])
def test_forbidden_metadata_fails_even_with_self_consistent_internal_receipts(prepared, change):
    _, binding, epochs, _, _, run = prepared
    path = epochs / "sub-1/included_trial_metadata.json"
    rows = json.loads(path.read_text())
    if change == "query":
        rows[0]["role"] = "target_query"
    elif change == "final":
        rows[0]["cohort"] = "final_test"
    elif change == "support_run":
        rows[40]["run"] = "run-2"
        rows[40]["trial_id"] = "sub-1/ses-1/run-2/row-1"
    elif change == "duplicate":
        rows[1] = copy.deepcopy(rows[0])
    elif change == "source_class":
        rows[0]["label"] = "right_hand"
    else:
        rows[0]["source_file"] = "sub-1/ses-0/eeg/sub-1_ses-0_task-imagery_run-2_eeg.edf"
    write(path, rows)
    receipt_path = epochs / "sub-1/subject_receipt.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["metadata_sha256"] = checker.digest(path)
    write(receipt_path, receipt)
    assert binding["execution_authorized"] is False
    with pytest.raises(ValueError):
        run()


@pytest.mark.parametrize("change", ["scope", "duplicate_file", "path_escape", "missing_dependency"])
def test_changed_proposal_scope_and_binding_structure_rejected(prepared, change):
    _, binding, _, _, _, run = prepared
    if change == "scope":
        binding["scope"]["query_rows"] = 1
    elif change == "duplicate_file":
        binding["required_files"][-1] = copy.deepcopy(binding["required_files"][0])
    elif change == "path_escape":
        binding["defaults"]["epochs_root"] = "../outside"
    else:
        binding["source_bindings"].pop()
    with pytest.raises(ValueError):
        run()


@pytest.mark.parametrize("field,value", [("verification", "head_only"), ("get_http_status", 503),
                                         ("readback_bytes", 0), ("sha256", "0" * 64)])
def test_source40_full_get_chain_cannot_be_substituted_by_existence(prepared, field, value):
    root, binding, _, _, _, run = prepared
    path = root / binding["baseline_R2_receipt_path"]
    value_rows = json.loads(path.read_text())
    value_rows["files"][0][field] = value
    write(path, value_rows)
    with pytest.raises(ValueError, match="SOURCE40 R2 bytes/SHA proof mismatch"):
        run()


def test_relocated_pinned_inputs_allowed_without_root_traversal(prepared):
    _, _, epochs, baseline, _, run = prepared
    result = run(epochs_root=epochs, baseline_root=baseline)
    assert result["artifact_count"] == 42


def test_cli_checker_has_no_numerical_model_or_process_execution_imports():
    tree = ast.parse(Path(checker.__file__).read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module.split(".")[0])
    assert imported <= {"__future__", "argparse", "hashlib", "json", "collections", "pathlib"}
