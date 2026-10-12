#!/usr/bin/env python3
"""Verify original public Leeuwis sidecars and resource-ID joins, without inference."""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import numpy as np

from fetch_nemar_subset import write_immutable

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG = REPO_ROOT / "research_logs/public_data_expansion_20261010/leeuwis_ingestion"
SOURCE = REPO_ROOT / (
    "research_logs/public_data_expansion_20261010/large_training_metadata/"
    "leeuwis2021_upstream_adapter.py")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def main() -> None:
    receipt = json.loads((LOG / "original_non_eeg_sidecars_download_receipt.json").read_text())
    root = REPO_ROOT / receipt["raw_root"]
    require(receipt["complete"] and len(receipt["files"]) == 4, "Four source sidecars required")
    for entry in receipt["files"]:
        data = (root / entry["path"]).read_bytes()
        require(len(data) == entry["official_size"] and hashlib.sha1(data).hexdigest()
                == entry["official_checksum"] and hashlib.sha256(data).hexdigest()
                == entry["actual_sha256"], "Original official sidecar checksum mismatch")
    official_data = (LOG / "original_dataverse_dataset_metadata.json").read_bytes()
    require(hashlib.sha256(official_data).hexdigest() == receipt["official_metadata_sha256"],
            "Original official metadata snapshot changed")
    official = json.loads(official_data)["data"]["latestVersion"]
    require(official["versionNumber"] == 1 and official["versionMinorNumber"] == 0,
            "Original DataverseNL v1.0 required")
    files = {entry["dataFile"]["id"]: entry["dataFile"] for entry in official["files"]}
    tree = ast.parse(SOURCE.read_text())
    ids = next(ast.literal_eval(node.value) for node in tree.body
               if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name)
                  and target.id == "_FILE_IDS" for target in node.targets))
    mapping = []
    for index, (original_id, file_ids) in enumerate(ids.items(), 1):
        require(all(str(original_id) in files[fid]["filename"] for fid in file_ids),
                "Upstream original IDs inconsistent with official source filenames")
        mapping.append({"nemar_subject": f"sub-{index}", "original_subject_id": original_id,
                        "original_run_files": [{"datafile_id": fid,
                                                "filename": files[fid]["filename"],
                                                "official_checksum": files[fid]["checksum"]}
                                               for fid in file_ids]})
    questionnaires = read_csv(root / "Questionnaires.csv")
    curves = read_csv(root / "BCI_OnlineClassificationErrors.csv")
    questionnaire_ids = {int(row["ppnr"]) for row in questionnaires}
    curve_ids = {int(re.fullmatch(r"Subject (\d+)", row["subject"])[1]) for row in curves}
    resource_ids = set(ids)
    require(len(questionnaires) == len(mapping) == 55 and questionnaire_ids == resource_ids,
            "Original questionnaire IDs do not exactly match55 mapped EEG resource IDs")
    keys = Counter((row["subject"], row["run"], row["lr"]) for row in curves)
    require(len(keys) == len(curves) == 480 and all(count == 1 for count in keys.values()),
            "Duplicate or missing online curve identities")
    require({row["run"] for row in curves} == {"Calibration", "Run1", "Run2", "Run3"}
            and {row["lr"] for row in curves} == {"L", "R"}, "Unexpected curve run/hand labels")
    values = np.array([[float(value) for key, value in row.items()
                        if key not in {"subject", "run", "lr"}] for row in curves])
    require(values.shape == (480, 2000) and np.isfinite(values).all()
            and 0 <= values.min() <= values.max() <= 100, "Invalid online error percentages")
    ages = np.array([float(row["Age"]) for row in questionnaires])
    require(np.isfinite(ages).all(), "Nonfinite original age")
    result = {
        "dataset": "Leeuwis2021 original DataverseNL v1.0 sidecars",
        "source_acceptance_complete": True, "source_sidecar_file_count": 4,
        "source_sidecar_bytes": receipt["bytes"], "nemar_original_id_mapping": mapping,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "upstream_source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "official_metadata_sha256": receipt["official_metadata_sha256"],
        "questionnaire_row_count": 55, "questionnaire_resource_ID_set_matches": True,
        "original_age_range": [float(ages.min()), float(ages.max())],
        "original_gender_counts": dict(Counter(row["Gender"] for row in questionnaires)),
        "online_curve_rows": len(curves), "online_curve_original_subject_count": len(curve_ids),
        "online_curve_timepoints_per_row": 2000, "online_curve_numeric_values": int(values.size),
        "online_curve_all_finite": True,
        "online_curve_min_max_percent": [float(values.min()), float(values.max())],
        "online_curve_unique_subject_run_hand_keys": len(keys),
        "extra_original_ids_without_selected_EEG": sorted(curve_ids - resource_ids),
        "selected_EEG_ids_missing_online_curves": sorted(resource_ids - curve_ids),
        "selected_EEG_matching_curve_rows": sum(int(row["subject"].split()[1]) in resource_ids
                                                 for row in curves),
        "curve_definition": "Source readme: average online classification error across20 "
        "trials per subject/run/hand;2000 points across8seconds at250Hz; cue at3seconds.",
        "curves_are_trial_outcomes": False, "original_numeric_EEG_read": False,
        "run_identity_limit": "Original subject40 feedback EEG filenames irregular. No "
        "original signal/marker validation or per-trial join performed. Calibration and "
        "feedback curves are not newly acquired EEG subjects.",
        "scope_limit": "One visit; no causal learning, unassisted retention or algorithm "
        "efficacy inference. Original questionnaire individual age/gender can be joined by "
        "the explicit source-ID map; mirror age20.71 is only the published group mean.",
    }
    write_immutable(LOG / "original_non_eeg_sidecars_audit_run01.json", result)
    print(json.dumps({key: result[key] for key in ["source_acceptance_complete",
                                                  "extra_original_ids_without_selected_EEG",
                                                  "selected_EEG_matching_curve_rows"]}))


if __name__ == "__main__":
    main()
