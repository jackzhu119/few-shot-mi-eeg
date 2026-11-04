"""Create standalone JNE upload files from approved saved data; no model runs."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

import fitz

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "manuscript/jne_alignment_20261104"
UPLOAD = OUT / "UPLOAD_FILES"
AUDIT = ROOT / "research_logs/paper2_jne_direct_upload_20261104"
PIN = "407e6ce0a17339d5808a7acc14e9745b9dceffbd"
REPO = "https://github.com/jackzhu119/few-shot-mi-eeg"
RAW = "https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/" + PIN + "/"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command):
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if result.returncode or result.stderr.strip():
        raise RuntimeError("Direct export failed or warned: " + result.stderr[-5000:])


def legacy_module():
    spec = importlib.util.spec_from_file_location("approved_document_builder", ROOT / "scripts/build_paper2_jne_20261104.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def attach_csv_metadata(source, target, metadata):
    """Two rectangular metadata records, followed by the exact original CSV bytes."""
    original = source.read_bytes()
    first = next(csv.reader(io.StringIO(original.decode("utf-8"), newline="")))
    if len(first) < 2:
        raise ValueError("CSV requires at least two fields for its metadata records")
    if len(metadata["title"]) > 30 or len(metadata["description"].split()) > 30:
        raise ValueError("Supplement title/description is too long")
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["#title", metadata["title"]] + [""] * (len(first) - 2))
    writer.writerow(["#description", metadata["description"]] + [""] * (len(first) - 2))
    prefix = buffer.getvalue().encode("utf-8")
    target.write_bytes(prefix + original)
    delivered = target.read_bytes()
    if delivered[len(prefix):] != original:
        raise ValueError("CSV data section changed while adding title/description")
    with target.open(encoding="utf-8", newline="") as stream:
        reader = csv.reader(stream)
        title, description = next(reader), next(reader)
        if title[:2] != ["#title", metadata["title"]] or description[:2] != ["#description", metadata["description"]]:
            raise ValueError("Internal supplementary metadata differs")
    return {"file": target.name, "bytes": target.stat().st_size, "sha256": digest(target),
            "metadata_records_before_header": 2, "data_section_offset_bytes": len(prefix),
            "data_section_bytes": len(original), "data_section_sha256": digest(source),
            "data_section_byte_identical_to_verified_export": True}


def build_guide(index, data_receipt, copies, helper):
    metadata = {row["filename"]: row for row in csv.DictReader((OUT / "SUPPLEMENT_METADATA.csv").open())}
    desc = metadata["Supplementary_Code_and_Reproduction.pdf"]["description"]
    lines = ["# Code and reproduction", "", "**Description:** " + desc, "",
             "## Data delivery and fixed scientific version", "",
             "This supplement accompanies the author-approved JNE article. The present delivery converts saved data to standalone CSV files; it creates no model, query prediction or new statistical estimate. Scientific definitions, participant units, exclusions, numerical values and the author approval are retained.", "",
             "The fixed scientific/code/input snapshot is [the approved repository version](" + REPO + "/tree/" + PIN + "), commit `" + PIN + "`. Original machine-readable files and the complete earlier data/code archive remain available there. That historical archive has 1,471 members; these direct-upload files are a documented selection and lossless conversion, rather than a claim that every historical file is embedded.", "",
             "The source recordings remain at NEMAR nm000177/v1.0.5 and the original BNCI2014-001 source, with its verified NEMAR nm000139/v1.0.3 mirror. No raw EEG, model weights or credentials are supplied in these CSV files.", "",
             "## Read the standalone CSV files", "",
             "Each CSV contains two initial metadata records: #title and #description. The third record is the actual data header. Skip the first two records when reading data. Their removal recovers the exact verified CSV data section, including original decimal strings and empty fields. The two prediction data sections are byte-identical to their decompressed frozen source files.", "",
             "```python", "import csv", "import json", "", "with open(", "    'Supplementary_Results.csv',", "    encoding='utf-8', newline=''", ") as f:",
             "    next(f)  # title metadata record", "    next(f)  # description metadata record", "    result_cells = list(csv.DictReader(f))", "",
             "# pandas: pd.read_csv(path, skiprows=2,", "#                     dtype=str, keep_default_na=False)",
             "# Saved_Records.record_json is parsed with json.loads; no eval is used.", "```", "",
             "CSV field strings retain their source precision. Spreadsheet software can coerce long decimals when importing or saving CSV; the optional public XLSX copy stores all fields as text. Keep the supplied CSV files unchanged for numerical reproduction.", "",
             "### Result tables", "",
             "Supplementary_Results.csv uses the fields table_id, row, column, field and value. Row and column are one-based data coordinates. It contains 238,401 cells from 56 sources: two main tables, 27 supplementary tables, 17 full-precision statistical CSVs and ten figure-source CSVs. Manuscript tables keep their display precision and text markers; the separate statistical-source rows preserve the original full decimal strings. The INDEX below maps every table ID to its original file.", "",
             "### Saved predictions and records", "",
             "Supplementary_Budget_Predictions.csv contains 78,600 saved chronological-budget prediction rows. Supplementary_Phase_Predictions.csv contains 11,460 saved cue/task-window prediction rows. Original trial IDs, labels, methods, budgets and eligibility representations are retained.", "",
             "Supplementary_Saved_Records.csv has 2,952 records. Its columns are source_id, source_path, record_type, source_row and record_json. The 612 JSON documents comprise 36 original BNCI prediction files and 576 sensitivity cells; the latter retain 544 completed and 32 undefined cells. The remaining 2,340 records are the 1,800 budget-session and 540 phase-metric rows. JSON objects are serialized canonically; original formatting bytes can differ, while parsed values and nested arrays are retained. Original source-file checksums are in the public input index.", "",
             "These files collectively contain 118,240 repeated, method-specific CSP/LDA prediction values, including 4,320 original BNCI, 20,040 matched-control and 3,820 new phase values inside JSON vectors. These are not unique participants or independent trials. The complete historical neural, geometric and synthetic raw exports retain their original public packet locations; their saved summaries and figure data are included in the result tables, rather than relabeled as new trial predictions.", "",
             "## Fixed code and saved-result reconstruction", "",
             "Use the recorded science dependencies: Python 3.11.16, NumPy 2.2.6, SciPy 1.15.3, scikit-learn 1.7.2 and MNE 1.10.2. Formatting uses a separate document/plot interpreter. No environment or model retraining is needed to inspect the supplied files.", "",
             "From a checkout of the fixed scientific snapshot, the previously validated saved-result command is:", "",
             "```bash", "p=scripts/reproduce_paper2_alignment_saved_results_20261104.py", "python \"$p\" --output /tmp/jne-reproduction-new", "```", "",
             "Use an unused output directory. That command rebuilds 17 result CSVs from saved predictions/cell records and checks them against the saved tables. It loads no EEG or checkpoint and performs no model fit or query forward. Its actual earlier reproduction receipts remain in the fixed scientific repository; the present format conversion does not claim to repeat all experiments.", "",
             "Relevant fixed source files:", "",
             "- [Saved-result reproduction entry](" + RAW + "scripts/reproduce_paper2_alignment_saved_results_20261104.py)",
             "- [Saved-prediction analysis](" + RAW + "scripts/analyze_paper2_alignment_integrated_20261104.py)",
             "- [Independent numerical check](" + RAW + "scripts/check_paper2_alignment_integrated_20261104.py)",
             "- [Source/data lineage](" + RAW + "research_logs/paper2_alignment_integrated_20261104/data_lineage.json)",
             "- [Input manifests and saved result tables](" + REPO + "/tree/" + PIN + "/research_logs/paper2_alignment_integrated_20261104)", "",
             "Historical V2 raw results: [fixed public packet](" + REPO + "/tree/" + PIN + "/training_status/paper2-recalibration-v2/result_exports/f1689db3941ae31757442698). Historical V3 raw results: [fixed public packet](" + REPO + "/tree/500831c086d9e1d1e8412cf8ebca5fb6a288db76/training_status/paper2-discovery-v3/result_exports/83cbdfdcfa541b3ab3addfc3). Trial QC and all-event phase mapping retain their original paths in the fixed source snapshot.", "",
             "## Direct CSV checksums", "",
             "Checksums below refer to the complete upload CSV, including its two metadata records. Full output/source mappings, headers and source hashes are supplied as INPUT_INDEX.json in the public repository next to the direct-upload validation records.", ""]
    for row in copies:
        lines.extend(["**" + row["file"] + "**", "",
                      f"Bytes: {row['bytes']}; data records begin after two metadata records. SHA256: `{row['sha256']}`.", ""])
    lines.extend(["## Result-source index", "",
                  "M01–M02 identify the main tables; S01–S27 the supplementary tables; A01–A12 and C01–C05 the statistical CSVs; F01–F10 the figure-data tables. Source headers occur in the CSV field column, and full source paths, dimensions and byte hashes are in INPUT_INDEX.json.", ""])
    for table in index["table_sources"]:
        lines.extend([f"**{table['table_id']}: {table['title']}** — {table['data_rows']} data rows, {table['columns']} columns.", "",
                      "Original source: [" + Path(table["source_path"]).name + "](" + table["source_url"] + "). SHA256: `" + table["source_sha256"] + "`.", ""])
    lines.extend(["## Licenses and scope", "",
                  "Original project code follows MIT. Original derived data and manuscript/figure content follow CC BY 4.0 within LICENSING.md. Original EEG and third-party components keep their own terms; the citation style retains its separate CC BY-SA attribution. These files do not relicense original recordings or third-party software. Participant-level statistical units, previously exposed analysis scopes, undefined endpoints and negative/null results remain as reported.", ""])
    source = OUT / "Supplementary_Code_and_Reproduction.md"
    source.write_text("\n".join(lines))
    common = ["pandoc", str(source), "--from=markdown-implicit_figures+autolink_bare_uris", "--standalone",
              "--metadata", "lang=en-US"]
    run(common + ["-o", str(OUT / "Supplementary_Code_and_Reproduction.docx")])
    helper.word_style(OUT / "Supplementary_Code_and_Reproduction.docx")
    text = source.read_text()
    text = re.sub(r"`([A-Za-z0-9_./:;=+-]{24,})`", lambda m: r"\texttt{\seqsplit{" + m[1].replace("_", r"\_") + "}}", text)
    pdf_source = OUT / "Sources/Supplementary_Code_and_Reproduction_pdf.md"
    pdf_source.write_text(text)
    common[1] = str(pdf_source)
    run(common + ["--pdf-engine=xelatex", "--include-in-header", str(OUT / "Sources/layout.tex"),
                  "-V", "mainfont=DejaVu Serif", "-V", "monofont=DejaVu Sans Mono", "-V", "fontsize=12pt",
                  "-V", "geometry:margin=22mm", "-V", "linestretch=1.1", "-o", str(OUT / "Supplementary_Code_and_Reproduction.pdf")])
    with fitz.open(OUT / "Supplementary_Code_and_Reproduction.pdf") as document:
        if any(not page.get_text().strip() for page in document):
            raise ValueError("Empty page in code/reproduction guide")
    if data_receipt["source_table_count"] != 56 or not data_receipt["status"] == "passed":
        raise ValueError("Data export receipt failed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--documents-already-built", action="store_true")
    parser.add_argument("--data-staging", type=Path)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    helper = legacy_module()
    if not args.documents_already_built:
        helper.build_documents()
    if args.data_staging:
        staging = args.data_staging
    else:
        staging = Path(tempfile.mkdtemp(prefix="paper2-jne-direct-data-"))
        command = [sys.executable, str(ROOT / "scripts/export_paper2_jne_direct_data_20261104.py"), "--output", str(staging)]
        if args.archive:
            command.extend(["--archive", str(args.archive)])
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError("Saved-data export failed: " + result.stderr[-3000:])
    AUDIT.mkdir(parents=True, exist_ok=True)
    UPLOAD.mkdir(exist_ok=True)
    index = json.loads((staging / "INPUT_INDEX.json").read_text())
    receipt = json.loads((staging / "DATA_EXPORT_VALIDATION.json").read_text())
    for name in ("INPUT_INDEX.json", "DATA_EXPORT_VALIDATION.json"):
        shutil.copyfile(staging / name, AUDIT / name)
    expected = {row["file"]: row for row in receipt["outputs"]}
    metadata = {row["filename"]: row for row in csv.DictReader((OUT / "SUPPLEMENT_METADATA.csv").open())}
    copies = []
    for name in ("Supplementary_Results.csv", "Supplementary_Budget_Predictions.csv",
                 "Supplementary_Phase_Predictions.csv", "Supplementary_Saved_Records.csv"):
        source = staging / name
        if digest(source) != expected[name]["sha256"]:
            raise ValueError("Verified export bytes changed: " + name)
        copies.append(attach_csv_metadata(source, UPLOAD / name, metadata[name]))
    readable = OUT / "READABLE_COPY"
    readable.mkdir(exist_ok=True)
    shutil.copyfile(staging / "Supplementary_Results.xlsx", readable / "Supplementary_Results.xlsx")
    build_guide(index, receipt, copies, helper)
    for name in ("JNE_Manuscript.pdf", "Supplementary_Methods.pdf", "Supplementary_Code_and_Reproduction.pdf"):
        shutil.copyfile(OUT / name, UPLOAD / name)
    editor = OUT / "EDITOR_FILES"
    editor.mkdir(exist_ok=True)
    for name in ("Cover_Letter.pdf", "Declarations.pdf", "Related_Manuscript_Statement.pdf"):
        shutil.copyfile(OUT / name, editor / name)
    ordered = ["JNE_Manuscript.pdf"] + list(metadata)
    if len(ordered) != 7 or any(not (UPLOAD / name).is_file() for name in ordered):
        raise ValueError("Expected seven individual upload files")
    files = [{"file": name, "bytes": (UPLOAD / name).stat().st_size,
              "sha256": digest(UPLOAD / name), "designation": "Complete Document for Review (PDF Only)" if i == 0 else "Supplementary Data Files (incl. Multimedia)"}
             for i, name in enumerate(ordered)]
    if any(row["bytes"] > 50_000_000 for row in files[1:]) or sum(row["bytes"] for row in files) > 150_000_000:
        raise ValueError("Direct upload size exceeds IOP guidance")
    if any(path.suffix.lower() == ".zip" for path in UPLOAD.iterdir()):
        raise ValueError("An archive remains in the direct upload folder")
    status = json.loads((OUT / "SUBMISSION_STATUS.json").read_text())
    manifest = {"status": "passed", "delivery": "Seven standalone PDF/CSV files; no archive upload",
                "fixed_source_commit": PIN, "author_approval_retained": status["final_jne_files_author_approval_recorded"],
                "csv_metadata_wrapping": copies, "files": files, "total_upload_bytes": sum(row["bytes"] for row in files),
                "optional_workbook": {"path": "READABLE_COPY/Supplementary_Results.xlsx", "bytes": (readable / "Supplementary_Results.xlsx").stat().st_size,
                                      "sha256": digest(readable / "Supplementary_Results.xlsx"), "required_for_upload": False},
                "new_fits": 0, "query_forwards": 0, "journal_submission": False, "main_merge": False}
    (OUT / "DIRECT_UPLOAD_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (OUT / "PACKAGE_SHA256.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (AUDIT / "DIRECT_UPLOAD_VALIDATION.json").write_text(json.dumps(manifest, indent=2) + "\n")
    all_files = [p for p in sorted(OUT.rglob("*")) if p.is_file() and p.name != "FILE_MANIFEST.json"]
    (OUT / "FILE_MANIFEST.json").write_text(json.dumps({"delivery": "Standalone files", "files": [
        {"file": str(p.relative_to(OUT)), "bytes": p.stat().st_size, "sha256": digest(p)} for p in all_files]}, indent=2) + "\n")
    print(json.dumps({"status": "passed", "upload_files": files, "total_bytes": manifest["total_upload_bytes"]}, indent=2))


if __name__ == "__main__":
    main()
