#!/usr/bin/env python3
"""Seal existing saved-result outputs; never load EEG or execute a decoder.

Writes two new receipts exclusively. The release manifest deliberately does not
hash itself or claim that the reference base commit contains these new files.
"""

import hashlib
import json
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
LOG = Path(__file__).resolve().parent
PACKAGE = ROOT / "manuscript/plos_one_submission_20261015"
BASE = "370bc94b7af3c926adeb02c38e430a53e4a64135"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def record(path):
    data = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "bytes": len(data), "sha256": digest(data)}


def write_new(path, payload):
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def main():
    checks = []

    def require(condition, name, detail=None):
        checks.append({"id": name, "passed": bool(condition), "detail": detail})
        if not condition:
            raise ValueError(name)

    for path in (PACKAGE / "release_manifest.json", LOG / "final_package_validation.json"):
        if path.exists():
            raise FileExistsError(path)
    protected = json.loads((LOG / "preservation_before.json").read_text())["protected_files"]
    for entry in protected:
        observed = record(ROOT / entry["path"])
        require(observed == entry, "original_scientific_file_unchanged", entry["path"])

    main_path = ROOT / "manuscript/kumar_plos_one_submission_draft_20261015.md"
    main_text = main_path.read_text()
    old_path = "manuscript/kumar_longitudinal_decoding_working_draft_20261015.md"
    original = subprocess.check_output(["git", "show", f"{BASE}:{old_path}"], cwd=ROOT).decode()

    def tables(text):
        return re.findall(r"(?m)(?:^\|.*\n)+", text)

    require(len(tables(original)) == 3, "original_three_tables_identified")
    require(tables(main_text)[:3] == tables(original), "three_original_tables_exact_bytes")
    bibliography = (ROOT / "manuscript/kumar_plos_one_references_20261015.bib").read_text()
    used = set(re.findall(r"(?<![\w.])@([A-Za-z][A-Za-z0-9_-]+)", main_text))
    keys = set(re.findall(r"@\w+\s*\{\s*([^,]+),", bibliography))
    require(used <= keys and len(used) == 14, "fourteen_citation_keys_resolve", sorted(used))
    title = re.search(r"^# (.+)$", main_text, re.MULTILINE).group(1)
    abstract = main_text.split("## Abstract\n", 1)[1].split("\n## ", 1)[0]
    words = len(re.findall(r"\S+", abstract))
    require(len(title) <= 250, "title_character_limit", len(title))
    require(words <= 300 and not re.search(r"@\w+", abstract), "abstract_limit_no_citations", words)
    require(
        len(re.findall(r"^\*\*Fig [1-4]\. .*\*\*$", main_text, re.MULTILINE)) == 4,
        "four_closed_explicit_figure_captions",
    )

    structure = json.loads((LOG / "final_document_structure_QA.json").read_text())
    visual = json.loads((LOG / "final_document_visual_QA.json").read_text())
    require(
        not structure["failures"] and structure["checks"] == 32,
        "independent_document_structure_32_checks",
    )
    require(
        not visual["remaining_layout_defects_found"],
        "actual_page_visual_review_no_unresolved_defect",
    )
    # The structure review records exact current document hashes; do not replace
    # the earlier build receipt whose two review exports were later corrected.
    bound = {entry["path"]: entry for entry in structure["source_files"]}
    pdf_results = []
    for pdf in sorted(PACKAGE.glob("*.pdf")):
        require(
            record(pdf) == bound[pdf.relative_to(ROOT).as_posix()],
            "current_pdf_matches_independent_QA",
            pdf.name,
        )
        with tempfile.TemporaryDirectory(prefix="paper2-pdf-bbox-") as temp:
            bbox = Path(temp) / "bbox.html"
            subprocess.run(
                ["pdftotext", "-bbox", str(pdf), str(bbox)], check=True, capture_output=True
            )
            tree = ET.parse(bbox)
            ns = {"x": "http://www.w3.org/1999/xhtml"}
            pages = tree.findall(".//x:page", ns)
            outside = []
            for number, page in enumerate(pages, 1):
                width, height = float(page.attrib["width"]), float(page.attrib["height"])
                for word in page.findall(".//x:word", ns):
                    if (
                        float(word.attrib["xMin"]) < -0.1
                        or float(word.attrib["yMin"]) < -0.1
                        or float(word.attrib["xMax"]) > width + 0.1
                        or float(word.attrib["yMax"]) > height + 0.1
                    ):
                        outside.append(number)
            require(
                not outside,
                "current_pdf_no_outside_page_text",
                {"file": pdf.name, "pages": len(pages)},
            )
            if pdf.stem == "cover_letter_draft":
                require(len(pages) == 1, "cover_letter_one_page")
            pdf_results.append({"file": pdf.name, "pages": len(pages)})
    for docx in sorted(PACKAGE.glob("*.docx")):
        require(
            record(docx) == bound[docx.relative_to(ROOT).as_posix()],
            "current_docx_matches_independent_QA",
            docx.name,
        )

    data_manifest = json.loads((PACKAGE / "S1_Data_manifest.json").read_text())
    with zipfile.ZipFile(PACKAGE / "S1_Data.zip") as archive:
        require(
            len(archive.namelist()) == len(set(archive.namelist())) == 41,
            "minimal_data_41_unique_members",
        )
        require(archive.testzip() is None, "minimal_data_all_CRC")
        expected = {entry["path"]: entry for entry in data_manifest["members"]}
        require(set(expected) == set(archive.namelist()), "minimal_data_exact_member_set")
        for name, entry in expected.items():
            data = archive.read(name)
            require(
                len(data) == entry["bytes"] and digest(data) == entry["sha256"],
                "minimal_data_full_member_SHA256",
                name,
            )
            require(
                Path(name).suffix in {".md", ".json", ".csv", ".py"},
                "minimal_data_text_or_code_only",
                name,
            )

    for tif in sorted(PACKAGE.glob("Fig*.tif")):
        with Image.open(tif) as image:
            dpi = image.info["dpi"]
            width_cm = image.width / dpi[0] * 2.54
            height_cm = image.height / dpi[1] * 2.54
            require(
                image.mode == "RGB"
                and image.n_frames == 1
                and image.info["compression"] == "tiff_lzw"
                and min(dpi) >= 300
                and max(dpi) <= 600
                and 6.68 <= width_cm <= 19.051
                and height_cm <= 22.23
                and tif.stat().st_size < 10_000_000,
                "figure_production_geometry_RGB_LZW",
                tif.name,
            )

    checked_links = []
    for document in [
        ROOT / "CURRENT_PROJECT_STATUS.md",
        ROOT / "README.md",
        ROOT / "manuscript/README.md",
        ROOT / "docs/kumar_submission_revision_report_20261015.md",
        *PACKAGE.glob("*.md"),
    ]:
        for target in re.findall(r"\]\(([^)]+)\)", document.read_text()):
            target = target.strip("<>").split("#", 1)[0]
            if not target or re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target):
                continue
            target = target.split(" ", 1)[0]
            resolved = document.parent / target
            require(
                resolved.exists(),
                "relative_delivery_link_resolves",
                {"document": str(document.relative_to(ROOT)), "target": target},
            )
            checked_links.append(target)

    sources = {main_path, Path(__file__).resolve()}
    for pattern in (
        "manuscript/kumar_plos_one_*_20261015.md",
        "manuscript/kumar_plos_one_references_20261015.bib",
        "docs/kumar_submission*20261015.md",
        "docs/plos_one_submission_check_20261015.md",
        "scripts/analyze_kumar_saved_query_qc_20261015.py",
        "scripts/render_kumar_submission_figures_20261015.py",
        "scripts/summarize_kumar_saved_training_curves.py",
        "tests/test_kumar_saved*20261015.py",
        "tests/test_kumar_saved_training_review.py",
        "research_logs/kumar_submission_qc_20261015/run01/*.csv",
        "research_logs/kumar_submission_qc_20261015/run01/public_inputs/*",
        "research_logs/kumar_submission_qc_20261015/run01/POST_OBSERVATION_PROTOCOL.md",
        "research_logs/kumar_submission_training_review_20261015/run01/results/*.csv",
        "manuscript/figures/plos_submission_20261015/*.csv",
    ):
        sources.update(path for path in ROOT.glob(pattern) if path.is_file())
    artifacts = sorted(path for path in PACKAGE.iterdir() if path.is_file())
    source_records = [record(path) for path in sorted(sources)]
    artifact_records = [record(path) for path in artifacts]
    now = datetime.now(timezone.utc).isoformat()
    release = {
        "status": "local_author_review_package_not_submitted_or_publicly_released",
        "sealed_at_utc": now,
        "reference_base_commit": BASE,
        "version_binding": "These new file hashes are sealed by the final local Git commit reported in the handoff; the reference base does not contain the new code/results. No self-hash or future public identifier is invented.",
        "sources": source_records,
        "artifacts": artifact_records,
        "document_build_history": "Initial twelve exports are historical. review_caption_correction.json binds the two corrected review exports; final_document_structure_QA.json and final_document_visual_QA.json bind current outputs.",
        "public_sync": "blocked_by_MCP_write_approval_policy_and_shell_proxy_connectivity",
        "new_R2_full_GET_verified": False,
        "remaining_author_decisions": [
            "secondary_analysis_institutional_determination",
            "actual_license_and_public_allowlist_selection",
            "personal_final_review_and_actual_AI_check_statement",
        ],
        "production_qualifications": [
            "Liberation font substitutions, not exact Arial/Times compliance",
            "Word XML/text/media checked; native Word layout not rendered",
        ],
        "no_new_fit_query_forward_or_Pod_operation": True,
    }
    write_new(PACKAGE / "release_manifest.json", release)
    receipt = {
        "status": "passed_with_explicit_public_sync_and_author_production_limits",
        "completed_at_utc": now,
        "script": record(Path(__file__).resolve()),
        "protected_original_files": len(protected),
        "checks": len(checks),
        "failures": [],
        "details": checks,
        "current_PDF_pages": pdf_results,
        "release_manifest": record(PACKAGE / "release_manifest.json"),
        "independent_visual_QA": record(LOG / "final_document_visual_QA.json"),
        "independent_structure_QA": record(LOG / "final_document_structure_QA.json"),
        "no_scientific_execution": True,
        "native_Word_visual_rendering": False,
        "new_R2_or_GitHub_sync": False,
    }
    write_new(LOG / "final_package_validation.json", receipt)
    print(
        json.dumps(
            {
                "checks": len(checks),
                "protected_files": len(protected),
                "failures": 0,
                "release_manifest": receipt["release_manifest"],
            }
        )
    )


if __name__ == "__main__":
    main()
