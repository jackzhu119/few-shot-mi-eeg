"""Check author facts, immutable reporting and updated exports without science."""

import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

ROOT = Path("/workspace/few-shot-mi-eeg")
LOG = ROOT / "research_logs/kumar_author_confirmation_20261015/run01"
OUT = ROOT / "manuscript/review_package_author_confirmed_20261015"
BASE = "027d48a213e03968a43c06c9a820a8b96754ecfc"
FIXED = "90e9d41ddc8f3e17316fdaf80331094fa7739520"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    checks = []

    def check(name, condition):
        checks.append({"check": name, "passed": bool(condition)})

    confirmation = json.loads((LOG / "author_confirmation.json").read_text())
    check("all_eight_answers", [a["number"] for a in confirmation["answers"]] == list(range(1, 9)))
    check(
        "exact_user_reply",
        confirmation["verbatim_reply"]
        == "1.已更改 2.全部由我个人独立完成没有其它作者 3.没有资助 4.无 5.尚无结论 6.无限制 7.plos one 8.无",
    )
    check(
        "institutional_determination_unresolved",
        not confirmation["answers"][4][
            "approval_exemption_waiver_or_no_review_determination_claimed"
        ],
    )
    check(
        "orcid_author_report_only",
        not confirmation["answers"][0]["independent_current_profile_verification"],
    )
    check(
        "no_license_or_all_private_release_authorization",
        not confirmation["answers"][5]["specific_software_license_granted"]
        and not confirmation["answers"][5]["public_release_of_all_private_artifacts_authorized"],
    )
    check(
        "no_scientific_or_submission_authorization",
        not confirmation["new_scientific_or_submission_authorization"],
    )
    path = "manuscript/kumar_longitudinal_decoding_working_draft_20261015.md"
    text = (ROOT / path).read_text()
    original = subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT, text=True)
    results = text.split("## Results\n", 1)[1].split("## Discussion\n", 1)[0]
    check(
        "original_results_byte_unchanged",
        results == original.split("## Results\n", 1)[1].split("## Discussion\n", 1)[0],
    )
    table_lines = [s for s in text.splitlines() if s.startswith("|")]
    check(
        "all_original_table_lines_unchanged",
        table_lines == [s for s in original.splitlines() if s.startswith("|")],
    )
    check(
        "AI_assistance_disclosed_as_more_than_language_polishing",
        all(
            s in text
            for s in [
                "AI-assisted preparation",
                "software and validation code",
                "reference checks",
                "These tools are not authors",
            ]
        ),
    )
    check(
        "pending_final_approval_not_fabricated",
        "the author’s final review and approval" in text and "outstanding" in text,
    )
    checklist = (ROOT / "manuscript/kumar_author_review_checklist_20261015.md").read_text()
    check("eight_current_answers_marked_recorded", checklist.count("- [x]") == 8)
    check(
        "unresolved_institutional_status_still_open",
        "- [ ] Obtain the institution" in checklist
        and "**Current answer: no conclusion yet.**" in checklist,
    )
    preservation = json.loads((LOG / "preservation_before.json").read_text())["protected_files"]
    for item in preservation:
        data = (ROOT / item["path"]).read_bytes()
        check("length:" + item["path"], len(data) == item["bytes"])
        check("sha256:" + item["path"], digest(data) == item["sha256"])
    export_info = []
    for name in ["manuscript", "supplement", "author_checklist"]:
        pdf = OUT / f"{name}.pdf"
        plain = subprocess.check_output(["pdftotext", str(pdf), "-"], text=True)
        with ZipFile(OUT / f"{name}.docx") as stream:
            word = "".join(ET.fromstring(stream.read("word/document.xml")).itertext())
        check(f"{name}_no_replacement_glyph", "\ufffd" not in plain)
        if name == "manuscript":
            for phrase in [
                "no specific funding",
                "no competing interests",
                "AI-assisted preparation",
                "no concurrent journal consideration",
                "no conclusion has yet been obtained",
            ]:
                check("pdf_declaration:" + phrase, phrase in " ".join(plain.split()))
                check("word_declaration:" + phrase, phrase in " ".join(word.split()))
        if name == "author_checklist":
            for phrase in [
                "Current answer: no conclusion yet.",
                "none declared",
                "No project software LICENSE",
            ]:
                check("checklist_pdf:" + phrase, phrase in " ".join(plain.split()))
                check("checklist_word:" + phrase, phrase in " ".join(word.split()))
        stderr = (LOG / f"build_{name}_pdf.stderr").read_text()
        check(f"{name}_no_typesetting_warnings", not stderr.strip())
        xml = subprocess.check_output(["pdftotext", "-bbox", str(pdf), "-"], text=True)
        tree = ET.fromstring(xml)
        pages = tree.findall(".//{*}page")
        words = 0
        invalid_boxes = []
        for page in pages:
            width, height = float(page.attrib["width"]), float(page.attrib["height"])
            for token in page.findall(".//{*}word"):
                words += 1
                box = {k: float(token.attrib[k]) for k in ["xMin", "xMax", "yMin", "yMax"]}
                if not (
                    0 <= box["xMin"] <= box["xMax"] <= width
                    and 0 <= box["yMin"] <= box["yMax"] <= height
                ):
                    invalid_boxes.append({"word": words, "box": box})
        check(f"{name}_all_word_boxes_within_pages", not invalid_boxes)
        for kind in ["pdf", "docx"]:
            p = OUT / f"{name}.{kind}"
            export_info.append(
                {
                    "path": str(p.relative_to(ROOT)),
                    "bytes": p.stat().st_size,
                    "sha256": digest(p.read_bytes()),
                }
            )
        export_info.append(
            {
                "document": name,
                "pdf_pages": len(pages),
                "word_bbox_checked": words,
                "native_Word_layout_rendered": False,
            }
        )
    for name in ["author_checklist", "supplement"]:
        for kind in ["pdf", "docx"]:
            source = (OUT / f"{name}_{kind}_source.md").read_text()
            check(
                f"{name}_{kind}_canonical_links_bound_to_author_commit",
                f"/blob/{FIXED}/manuscript/" in source,
            )
    report = {
        "status": "passed" if all(c["passed"] for c in checks) else "failed",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_commit": BASE,
        "factual_source_commit": FIXED,
        "script_sha256": digest(Path(__file__).read_bytes()),
        "checks": len(checks),
        "failed_checks": [c for c in checks if not c["passed"]],
        "protected_files_unchanged": len(preservation),
        "results_bytes": len(results.encode()),
        "results_sha256": digest(results.encode()),
        "original_table_lines": len(table_lines),
        "export_info": export_info,
        "raw_EEG_decodes_model_forwards_or_fits": 0,
        "submission_or_public_data_release": False,
        "checks_detail": checks,
    }
    (LOG / "author_update_validation.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    )
    print(
        json.dumps(
            {k: v for k, v in report.items() if k != "checks_detail"}, ensure_ascii=False, indent=2
        )
    )
    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
