#!/usr/bin/env python3
"""Read-only byte/metadata preflight for the frozen CSP signed-score proposal.

Standard library only. No numerical array, model, EEG, optimizer, or diagnostic
module is imported. A pass establishes input identity, never execution consent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
BINDING = ROOT / "configs/kumar_csp_signed_score_input_binding_20261015.json"
EXPECTED_BINDING_SHA256 = "af65b5f0ce7850b010dc83965e799d3f26601b70fb6bc19607e59d1af3738712"
SUBJECTS = [f"sub-{value}" for value in (1, 4, 7, 10, 13, 16)]
EPOCH_NAMES = {"included_trial_metadata.json", "restricted_epochs.npz", "subject_receipt.json"}
BASELINE_NAMES = {"source_before.npz", "source_after.npz", "participant_receipt.json",
                  "fit_access_audit.json"}
SOURCE_BINDINGS = {
    "configs/kumar_csp_reliability_20261014.json",
    "configs/kumar_cross_session_20261012.json",
    "docs/kumar_csp_reliability_plan_20261014.md",
    "docs/kumar_csp_reliability_methods_review_20261014.md",
    "scripts/analyze_kumar_csp_signed_score_v1.py",
    "scripts/analyze_kumar_lowdim_reliability.py",
    "scripts/run_kumar_baselines.py",
    "src/learning_preserving_bci/decoders/csp_lda.py",
    "research_logs/kumar_cross_session_20261012/csp_reliability_freeze_run01_20261014/freeze_receipt.json",
    "research_logs/kumar_cross_session_20261012/csp_development_epochs_run01_20261014/preparation_receipt.json",
    "research_logs/kumar_cross_session_20261012/csp_implementation_review_run01_20261014/preparation_static_review_receipt.json",
    "research_logs/recovery_20261014/kumar_results_R2_run01.json",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def contained(root: Path, relative: str) -> Path:
    path = PurePosixPath(relative)
    require(not path.is_absolute() and bool(path.parts) and
            all(part not in (".", "..") for part in path.parts), "Unsafe relative input path")
    candidate = root / relative
    require(not candidate.is_symlink() and candidate.resolve().is_relative_to(root.resolve()),
            "Input escapes its pinned root")
    return candidate


def verify_file(path: Path, row: dict) -> None:
    require(path.is_file(), f"Missing pinned file: {path}")
    require(path.stat().st_size == row["bytes"] and digest(path) == row["sha256"],
            f"Pinned bytes/SHA256 mismatch: {path}")


def check_inputs(binding_path: Path = BINDING, *, repo_root: Path = ROOT,
                 epochs_root: Path | None = None, baseline_root: Path | None = None,
                 expected_binding_sha256: str = EXPECTED_BINDING_SHA256) -> dict:
    """The injectable roots/digest support synthetic software fixtures only."""
    require(digest(binding_path) == expected_binding_sha256, "Input binding SHA256 mismatch")
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    require(binding.get("schema_version") == 1 and binding.get("execution_authorized") is False,
            "Input binding must retain closed execution authority")
    scope = binding["scope"]
    expected_scope = {
        "development_subjects": SUBJECTS, "allowed_roles": ["source_train", "target_support"],
        "source_rows": 240, "support_rows": 596, "trial_count": 836, "source_file_count": 42,
        "source_train_session": "ses-0", "source_train_runs": ["run-0", "run-1"],
        "support_sessions": [f"ses-{value}" for value in range(1, 6)], "support_run": "run-0",
        "validation_rows": 0, "query_rows": 0, "final_subjects": 0,
        "new_source_train20_pipeline_attempts": 240, "new_primary_SOURCE40_decoder_fits": 0,
        "existing_SOURCE40_models_reused": 6, "bootstrap_seed": 42,
        "bootstrap_replicates": 10000,
    }
    require(scope == expected_scope, "Changed frozen diagnostic scope")
    source_rows = binding["source_bindings"]
    require(len(source_rows) == 12 and {row["path"] for row in source_rows} == SOURCE_BINDINGS,
            "Missing or duplicate scientific/dependency bindings")
    for row in source_rows:
        verify_file(contained(repo_root, row["path"]), row)
    roots = {
        "epochs": epochs_root or contained(repo_root, binding["defaults"]["epochs_root"]),
        "baseline": baseline_root or contained(repo_root, binding["defaults"]["baseline_root"]),
    }
    expected = {(kind, f"{subject}/{name}") for subject in SUBJECTS
                for kind, names in (("epochs", EPOCH_NAMES), ("baseline", BASELINE_NAMES))
                for name in names}
    rows = binding["required_files"]
    require(len(rows) == 42 and {(row["root"], row["path"]) for row in rows} == expected,
            "Restricted artifact set differs from 18 prepared plus 24 SOURCE40 files")
    by_identity = {(row["root"], row["path"]): row for row in rows}
    for row in rows:
        verify_file(contained(roots[row["root"]], row["path"]), row)
    r2 = json.loads(contained(repo_root, binding["baseline_R2_receipt_path"]).read_text())
    require(r2.get("status") == "completed" and r2.get("readback_mode") == "all",
            "Historical SOURCE40 backup is not full-GET closed")
    by_remote = {}
    for row in r2["files"]:
        by_remote.setdefault(row["relative_path"], []).append(row)
    raw_files, totals, participants = {}, Counter(), []
    for subject in SUBJECTS:
        folder = roots["epochs"] / subject
        metadata = json.loads((folder / "included_trial_metadata.json").read_text())
        prepared = json.loads((folder / "subject_receipt.json").read_text())
        ids = [row["trial_id"] for row in metadata]
        require(len(ids) == len(set(ids)), "Duplicate selected trial identity")
        role_counts = Counter()
        for row in metadata:
            require(row["subject"] == subject and row["cohort"] == "development" and
                    row["role"] in scope["allowed_roles"], "Forbidden selected cohort/role")
            require(row["label"] in ("left_hand", "right_hand"), "Changed selected label")
            require(row["trial_id"] ==
                    f"{subject}/{row['session']}/{row['run']}/row-{row['source_row']}",
                    "Trial identity field mismatch")
            require(type(row["source_row"]) is int and 1 <= row["source_row"] <= 20,
                    "Invalid source row")
            source = row["role"] == "source_train"
            require((source and row["session"] == "ses-0" and row["run"] in ("run-0", "run-1"))
                    or (not source and row["session"] in scope["support_sessions"] and
                        row["run"] == "run-0"), "Forbidden source/support run")
            path = f"{subject}/{row['session']}/eeg/{subject}_{row['session']}_task-imagery_{row['run']}_eeg.edf"
            require(row["source_file"] == path, "Unexpected selected EDF identity")
            identity = {"path": path, "sha256": row["raw_file_sha256"]}
            require(path not in raw_files or raw_files[path] == identity,
                    "Conflicting selected EDF identity")
            raw_files[path] = identity
            role_counts[row["role"]] += 1
        for session, run in [("ses-0", "run-0"), ("ses-0", "run-1")] + [
                (value, "run-0") for value in scope["support_sessions"]]:
            selected = [row for row in metadata if row["session"] == session and row["run"] == run]
            counts = sorted(Counter(row["label"] for row in selected).values())
            require((len(selected), counts) in ((19, [9, 10]), (20, [10, 10])) and
                    (session != "ses-0" or (len(selected) == 20 and
                     {row["source_row"] for row in selected} == set(range(1, 21)))),
                    "Source/current-support class budget mismatch")
        for name, field in (("included_trial_metadata.json", "metadata_sha256"),
                            ("restricted_epochs.npz", "epochs_sha256")):
            require(prepared[field] == by_identity[("epochs", f"{subject}/{name}")]["sha256"],
                    "Preparation receipt breaks pinned file chain")
        require(prepared.get("status") == "passed" and prepared.get("synthetic") is False and
                prepared["subject"] == subject and prepared["cohort"] == "development" and
                prepared["trial_count"] == len(metadata) and prepared["role_counts"] == role_counts and
                prepared["query_windows_read"] == 0 and prepared["validation_windows_read"] == 0 and
                prepared["final_cohort_access"] is False, "Preparation receipt scope mismatch")
        for name in BASELINE_NAMES:
            relative = f"{subject}/{name}"
            remote_rows = by_remote.get(relative, [])
            require(len(remote_rows) == 1, "Missing or duplicate SOURCE40 R2 identity")
            remote, pinned = remote_rows[0], by_identity[("baseline", relative)]
            require(remote.get("verification") == "full_get_sha256_verified" and
                    remote.get("head_http_status") == remote.get("get_http_status") == 200 and
                    remote.get("readback_bytes") == remote["bytes"] == pinned["bytes"] and
                    remote["sha256"] == pinned["sha256"], "SOURCE40 R2 bytes/SHA proof mismatch")
        totals.update(role_counts)
        participants.append({"subject": subject, "role_counts": dict(sorted(role_counts.items())),
                             "trial_count": len(metadata), "source_file_count": 7})
    require(participants == binding["participants"] and totals == {
        "source_train": 240, "target_support": 596}, "Changed aggregate selected scope")
    require([raw_files[key] for key in sorted(raw_files)] == binding["source_EDF_identities_metadata_only"]
            and len(raw_files) == 42, "Changed 42-EDF provenance identities")
    return {"status": "metadata_verified_execution_closed", "binding_sha256": expected_binding_sha256,
            "artifact_count": 42, "prepared_artifacts": 18, "existing_SOURCE40_artifacts": 24,
            "scientific_dependency_bindings": 12, "source_train_rows": 240,
            "target_support_rows": 596, "source_EDF_metadata_identities": 42,
            "participants": participants, "numerical_arrays_deserialized": False,
            "new_fits": 0, "query_rows_loaded": 0, "execution_authorized": False,
            "proof_scope": "byte hashes and metadata, not independent numerical replay or scientific completion"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs-root", type=Path)
    parser.add_argument("--baseline-root", type=Path)
    args = parser.parse_args()
    print(json.dumps(check_inputs(epochs_root=args.epochs_root, baseline_root=args.baseline_root),
                     indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
