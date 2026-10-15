"""Check authored reporting artifacts against saved evidence; no scientific execution."""

import csv
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

ROOT = Path("/workspace/few-shot-mi-eeg")
LOG = ROOT / "research_logs/kumar_manuscript_completion_20261015/run01"
OUT = ROOT / "manuscript/review_package_20261015"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    draft = ROOT / "manuscript/kumar_longitudinal_decoding_working_draft_20261015.md"
    text = draft.read_text()
    original = subprocess.check_output(
        ["git", "show", f"HEAD:{draft.relative_to(ROOT)}"], cwd=ROOT, text=True
    )
    assert (
        original.split("## Results\n", 1)[1].split("## Discussion\n", 1)[0]
        == text.split("## Results\n", 1)[1].split("## Discussion\n", 1)[0]
    )
    assert [x for x in original.splitlines() if x.startswith("|")] == [
        x for x in text.splitlines() if x.startswith("|")
    ]
    summary = (
        ROOT
        / "research_logs/kumar_frozen_query_comparison_20261015/run01/cohort_method_endpoint_summary.csv"
    )
    rows = list(csv.DictReader(summary.open()))
    for row in rows:
        cell = f"{float(row['mean_BA']) * 100:.2f} [{float(row['descriptive_ci95_low']) * 100:.2f}, {float(row['descriptive_ci95_high']) * 100:.2f}]"
        assert cell in text, cell
    bibliography = ROOT / "manuscript/kumar_references_20261015.bib"
    verified = json.loads(
        (
            ROOT
            / "research_logs/kumar_manuscript_references_20261015/run01/reference_verification.json"
        ).read_text()
    )
    assert sha(bibliography) == verified["bibliography_sha256"]
    keys = set(re.findall(r"@[a-z]+\{([^,]+)", bibliography.read_text()))
    citations = set(re.findall(r"(?<![\w])@([a-z][a-z0-9]+)", text))
    assert citations <= keys and len(keys) == 10
    local_links = []
    for source in [
        draft,
        ROOT / "manuscript/kumar_supplementary_methods_20261015.md",
        ROOT / "manuscript/kumar_author_review_checklist_20261015.md",
    ]:
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", source.read_text()):
            if not target.startswith(("http://", "https://", "#", "mailto:")):
                path = (source.parent / target.split("#")[0]).resolve()
                assert path.exists(), target
                local_links.append(str(path))
    protected = json.loads((LOG / "preservation_before.json").read_text())["protected_paths"]
    for item in protected:
        assert sha(ROOT / item["path"]) == item["sha256"], item["path"]
    outputs = []
    for name in ["manuscript", "supplement", "author_checklist"]:
        pdf = OUT / f"{name}.pdf"
        docx = OUT / f"{name}.docx"
        plain = subprocess.check_output(["pdftotext", str(pdf), "-"], text=True)
        (LOG / f"{name}_PDF_text.txt").write_text(plain)
        assert len(plain.strip()) > 500 and "\ufffd" not in plain
        with ZipFile(docx) as z:
            document = ET.fromstring(z.read("word/document.xml"))
            word_text = "".join(document.itertext())
            media = [x for x in z.namelist() if x.startswith("word/media/")]
        if name == "manuscript":
            for value in ["51.58", "57.94", "59.89", "65.36", "7.42", "2.49", "12.48"]:
                assert value in plain and value in word_text, value
            assert len(media) == 3
            assert all(key not in plain for key in ["@lawhern2018", "@nemar177", "@kumar2024"])
            assert "pgae076" in plain and "pgae137" in plain
        outputs.append(
            {
                "name": name,
                "pdf_bytes": pdf.stat().st_size,
                "pdf_sha256": sha(pdf),
                "docx_bytes": docx.stat().st_size,
                "docx_sha256": sha(docx),
                "docx_embedded_media": len(media),
                "pdfinfo": subprocess.check_output(["pdfinfo", str(pdf)], text=True),
            }
        )
    report = {
        "status": "passed_saved_evidence_text_reference_preservation_and_export_content_checks",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "script_sha256": sha(Path(__file__)),
        "base_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "main_results_and_original_three_tables_unchanged": True,
        "cohort_method_endpoint_rows_checked": len(rows),
        "verified_bibliography_entries": len(keys),
        "used_citation_keys": sorted(citations),
        "local_links_checked": len(local_links),
        "protected_files_byte_unchanged": len(protected),
        "exports": outputs,
        "raw_EEG_decodes_model_forwards_or_fits": 0,
        "native_Word_rendering_performed": False,
        "rendered_PDF_visual_check": "separate actual page-image inspection required",
        "limits": [
            "Reference metadata verification does not imply original full-text review.",
            "DOCX XML/media and content checked; native Word layout was not rendered.",
            "Author-specific declarations remain limited to actual supplied/source-supported facts.",
        ],
    }
    (LOG / "package_content_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "exports"}, indent=2))


if __name__ == "__main__":
    main()
