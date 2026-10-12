"""Verify closed saved inputs and executed notebook exports; never read EEG or fit."""
from __future__ import annotations

import base64
import hashlib
import importlib.metadata
import json
import platform
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

import nbformat

ROOT = Path(__file__).resolve().parents[3]
AUDIT = ROOT / "research_logs/netbci_cohort_all19_20261010"
VALIDATION = AUDIT / "notebook_validation_run03"
FINAL = Path(__file__).resolve().parent


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def record(path):
    return {"path": str(path.relative_to(ROOT)), "sha256": sha(path), "bytes": path.stat().st_size}


def read(path):
    return json.loads(path.read_text())


class ImageCounter(HTMLParser):
    def __init__(self):
        super().__init__()
        self.embedded_pngs = 0

    def handle_starttag(self, tag, attrs):
        if tag == "img" and dict(attrs).get("src", "").startswith("data:image/png;base64,"):
            self.embedded_pngs += 1


notebook_path = ROOT / "notebooks/netbci2026_all19_20261011.ipynb"
html_path = notebook_path.with_suffix(".html")
builder = ROOT / "scripts/build_netbci_all19_notebook.py"
notebook = nbformat.read(notebook_path, as_version=4)
nbformat.validate(notebook)
assert notebook.metadata.builder_sha256 == sha(builder)
assert notebook.metadata.validation_run == VALIDATION.name
code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
assert len(notebook.cells) == 16 and len(code_cells) == 12
assert [cell.execution_count for cell in code_cells] == list(range(1, 13))
assert not [output for cell in code_cells for output in cell.outputs if output.output_type == "error"]

embedded = []
for cell_index, cell in enumerate(notebook.cells):
    for output in cell.get("outputs", []):
        if "image/png" in output.get("data", {}):
            path = VALIDATION / f"embedded_native_figure_{len(embedded) + 1:02d}.png"
            assert path.read_bytes() == base64.b64decode(output.data["image/png"]), "Saved embedded image changed."
            embedded.append({"cell_index": cell_index, **record(path)})
assert len(embedded) == 7
exports_path = VALIDATION / "native_figure_export_index.json"
exports = read(exports_path)
assert [row["figure_number"] for row in exports] == list(range(1, 8))
for figure in exports:
    assert len(figure["artifacts"]) == 3
    assert {Path(item["path"]).suffix for item in figure["artifacts"]} == {".png", ".svg", ".pdf"}
    for item in figure["artifacts"]:
        assert record(ROOT / item["path"]) == item

input_artifacts = []
for directory_name, receipt_name in [
    ("summary_run01", "summary_receipt.json"),
    ("independence_sensitivity_run01", "sensitivity_receipt.json"),
]:
    directory = AUDIT / directory_name
    receipt = read(directory / receipt_name)
    assert receipt["synthetic"] is False
    input_artifacts.append(record(directory / receipt_name))
    for name, checksum in receipt["output_sha256"].items():
        path = directory / name
        assert sha(path) == checksum
        input_artifacts.append(record(path))

compact_path = AUDIT / "numeric_signal_identity_summary_v2.json"
compact = read(compact_path)
ledger = Path(compact["full_ledger_file"])
assert sha(ledger) == compact["full_ledger_sha256"]
assert compact["cross_subject_affected_identities"] == ["sub-1", "sub-6", "sub-7", "sub-15", "sub-17"]
assert len(compact["identities_without_detected_cross_subject_exact_signal_copies"]) == 14
for path in [compact_path, ledger, (ROOT / compact["official_manifest_file"]).resolve(),
             ROOT / "configs/netbci_cohort_all19_20261010.json"]:
    input_artifacts.append(record(path))
assert sha((ROOT / compact["official_manifest_file"]).resolve()) == compact["official_manifest_sha256"]

for directory_name, receipt_name in [
    ("summary_run01", "summary_receipt.json"),
    ("independence_sensitivity_run01", "sensitivity_receipt.json"),
]:
    old = ROOT / "research_logs/netbci_cohort_resume_20261010" / directory_name
    for name, checksum in read(old / receipt_name)["output_sha256"].items():
        assert sha(old / name) == checksum

parser = ImageCounter()
html = html_path.read_text()
parser.feed(html)
assert parser.embedded_pngs == 7
assert "Verified 19 published identities; 14 retained identities." in html
assert "Published online score change (pp)" in html
assert "unitless" in html and "BrainVision" in html

r2_root = ROOT / "research_logs/public_data_expansion_20261010/r2"
storage_references = []
for name in ["netbci_numeric_identity_v2_20261011_run01.json",
             "netbci_all19_analysis_results_20261011_run01.json"]:
    path = r2_root / name
    receipt = read(path)
    assert receipt["status"] == "completed" and receipt["totals"]["failed_files"] == 0
    assert all(item["verification"] == "full_get_sha256_verified" for item in receipt["files"])
    if name.startswith("netbci_numeric"):
        entry = next(item for item in receipt["files"] if item["relative_path"] == ledger.name)
        assert entry["sha256"] == sha(ledger)
    storage_references.append({**record(path), "status": receipt["status"], "totals": receipt["totals"]})

artifacts = [builder, notebook_path, html_path,
             ROOT / "docs/netbci_all19_results_20261011.md",
             ROOT / "manuscript/all19_addendum_20261011.md",
             VALIDATION / "execution.log", exports_path, Path(__file__)]
now = datetime.now(timezone.utc)
result = {
    "status": "executed_notebook_and_all_seven_native_figures_verified",
    "synthetic": False,
    "checked_at_utc": now.isoformat(),
    "checked_date_asia_shanghai": now.astimezone(ZoneInfo("Asia/Shanghai")).date().isoformat(),
    "scope": "Saved real-data table and identity-ledger hashes, notebook execution, native figures and report references. No EEG array read or model fitting.",
    "execution": {
        "command": "MNE_DONTWRITE_HOME=true XDG_CACHE_HOME=/workspace/.cache MPLCONFIGDIR=/workspace/.cache/matplotlib OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 /workspace/.venvs/few-shot-mi-eeg/bin/python scripts/build_netbci_all19_notebook.py --execute --write-reports --validation-run notebook_validation_run03",
        "exit_code": 0, "kernel": "bci-netbci-local", "cells": 16, "code_cells": 12,
        "execution_counts": list(range(1, 13)), "error_outputs": 0,
        "native_png_outputs": 7, "nbformat_schema_passed": True,
    },
    "visual_review": {
        "method": "view_image each actual final run03 exported PNG",
        "all_seven_reviewed": True, "status": "passed",
        "checks": [
            "14 retained-ID trajectories and available-ID means; all 19-ID failure and source-copy matrices remain inspectable",
            "score and BA level percent, paired changes pp, spectral dB and geometric unitless distances remain distinct",
            "all-ID EEG bootstrap is labeled arithmetic; dynamic 14-ID restriction is labeled post-observation exploratory",
            "duplicate matrix flags sub-1/sub-17 all four sessions, sub-6/sub-15 session01 and sub-7 sessions01-03",
            "all-six-run matching 14/14 and fixed-QC matching 9/14 shown without relaxing cells",
            "geometry figure has its own ID and available-ID-mean legend; association point IDs are separately positioned",
            "reference and QC variants retain separate symbols and labels, actual n and coarse-QC limitations",
            "axes, annotations, legends, titles and footers legible; no clipping observed",
        ],
        "full_page_browser_render_reviewed": False,
    },
    "html_structure": {"exporter": "nbconvert HTMLExporter lab",
        "embedded_png_img_tag_count": parser.embedded_pngs,
        "source_limits_units_and_dynamic_scope_present": True,
        "browser_visual_status": "not_reviewed"},
    "artifact_sha256": [record(path) for path in artifacts],
    "embedded_figure_artifacts": embedded,
    "standalone_figure_exports": exports,
    "input_artifacts": input_artifacts,
    "ten_identity_summary_outputs_still_match_original_receipt": True,
    "ten_identity_sensitivity_outputs_still_match_original_receipt": True,
    "storage_receipt_references_checked": storage_references,
    "this_notebook_and_report_upload_status": "not asserted here; final source checkpoint has separate receipt",
    "prior_attempts": [
        {"run": "notebook_validation_run01", "exit_code": 1,
         "failure": "Cell2 provenance path display used a relative official-manifest path without resolve; checksum passed; no figures/reports/final notebook were written.",
         "preserved_log": "research_logs/netbci_cohort_all19_20261010/notebook_validation_run01/execution.log",
         "preserved_builder": "research_logs/netbci_cohort_all19_20261010/notebook_validation_run01/failed_builder/build_netbci_all19_notebook.py"},
        {"run": "notebook_validation_run02", "exit_code": 0,
         "status": "executed outputs preserved before visualization corrections",
         "issue": "Nearby association ID annotations overlap; exported geometry needs its own ID legend and dimensionless units.",
         "preserved_artifacts": "research_logs/netbci_cohort_all19_20261010/notebook_validation_run02/superseded_plot_labels"},
    ],
    "scientific_boundaries": [
        "19 published identities are not established biological independent participants",
        "full original BrainVision continuous EEG not compared; correct assignment and duplicate cause unknown",
        "14-ID exact-copy exclusion is source-driven, post-observation and not external confirmation",
        "no model refitting, altered presets, synthetic trial outcomes, causal human learning or skill-retention claim",
    ],
    "versions": {"python": platform.python_version(), **{package: importlib.metadata.version(package)
        for package in ["numpy", "pandas", "matplotlib", "nbformat", "nbclient", "nbconvert", "ipykernel"]}},
}
target = FINAL / "notebook_validation_receipt.json"
assert not target.exists(), "Preserve previous validation receipts."
result["final_validation_directory"] = str(FINAL.relative_to(ROOT))
result["final_validation_attempts"] = [{"attempt": 1, "exit_code": 1, "category": "validator assertion wording; no notebook or scientific failure", "reason": "The title exists within embedded PNG, while HTML text reports 14 retained identities.", "preserved_script": record(FINAL / "verify_final_artifacts_attempt01.py"), "preserved_log": record(FINAL / "validation_attempt01.log")}, {"attempt": 2, "exit_code": 0, "category": "saved-artifact validation only"}]
result["validation_only_execution"] = {"notebook_reexecuted": False, "scientific_models_refit": False,
    "raw_EEG_arrays_read": False, "preserved_run03_embedded_pngs_byte_match_notebook": True}
result["source_receipt_input_hash_checks"] = []
for directory_name, receipt_name in [("summary_run01", "summary_receipt.json"),
        ("independence_sensitivity_run01", "sensitivity_receipt.json")]:
    receipt = read(AUDIT / directory_name / receipt_name)
    checked = []
    for name, item in receipt["input_sha256"].items():
        path = Path(item["path"])
        assert sha(path) == item["sha256"], f"Source artifact changed: {name}"
        checked.append({"name": name, **record(path)})
    result["source_receipt_input_hash_checks"].append({"directory": directory_name,
        "verified_count": len(checked), "all_inputs_match_receipt": True, "artifacts": checked})
result["independent_evidence_references"] = [record(AUDIT / name) for name in [
    "independent_methods_closeout_run01.json", "independent_sensitivity_review_run01.json",
    "independent_first10_replay_comparison_20261011.json"]]
result["visual_review"]["method"] = "view_image each of seven actual run03 exported PNGs, seven saved notebook embedded PNGs, and seven PDF page-1 pdftoppm rasterizations"
result["visual_review"]["reviewed_image_count"] = 21
result["visual_review"]["svg_visual_reviewed"] = False
result["visual_review"]["svg_validation_scope"] = "All seven SVG XML trees parse, root/viewBox present, and indexed SHA/size match; browser SVG rendering was not reviewed."
result["visual_review"]["per_figure"] = read(FINAL / "visual_observations.json")
result["pdf_preview_artifacts"] = [record(FINAL / f"pdf_preview_{n:02d}.png") for n in range(1, 8)]
import xml.etree.ElementTree as ET
for n in range(1, 8):
    path = VALIDATION / "exports" / f"native_figure_{n:02d}.svg"
    tree = ET.parse(path)
    assert tree.getroot().tag.endswith("svg") and "viewBox" in tree.getroot().attrib
    pdf = VALIDATION / "exports" / f"native_figure_{n:02d}.pdf"
    assert pdf.read_bytes().startswith(b"%PDF-")
result["reviewed_counts_and_units"] = {"published_identities": 19, "retained_identities": 14,
    "biological_independence_verified": False, "source_events": 14431, "eligible_events": 14429,
    "partial_source_events_excluded": 2, "affected_copy_identities": [1, 6, 7, 15, 17],
    "all_six_matching_available": "14/14", "restricted_qc_matching_available": "9/14",
    "original_qc_matching_available": "14/19", "restricted_qc_unavailable_identities": [8, 11, 13, 14, 19],
    "constant_prediction_rows": 21, "constant_prediction_identities": 10, "qc_shortage_failures": 5,
    "scientific_failure_logs": 26, "run_qc_flag_records_retained": 456,
    "levels": "percent", "behavior_and_BA_changes": "percentage points (pp)",
    "spectral_task_contrast": "dB", "AIRM_and_PCA_geometry": "unitless"}
result["validation_skill"] = "data-analytics:validate-data; bounded final authoring QA, existing independent calculations reused"
result["parallel_readonly_claim_review"] = {"status": "passed", "method": "Independent subagent compared report/manuscript/notebook text with saved tables",
    "material_inconsistencies_found": 0, "files_changed": False, "model_or_notebook_execution": False}
result["artifact_sha256"].extend([record(FINAL / "visual_observations.json"), record(VALIDATION / "verify_artifacts.py")])
target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
print(json.dumps({"status": result["status"], "native_figures": 7, "exports": 21,
                  "input_artifacts": len(input_artifacts), "receipt": str(target)}, ensure_ascii=False))
