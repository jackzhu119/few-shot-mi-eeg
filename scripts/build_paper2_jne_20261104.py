"""Export the fixed Paper2 results for JNE; document/packaging operations only."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor
import fitz

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "manuscript/jne_alignment_20261104"
OLD = ROOT / "manuscript/bmt_alignment_integrated_20261104"
AUDIT = ROOT / "research_logs/paper2_jne_20261104"
DOCS = ROOT / "docs/paper2_jne_20261104"
SCIENCE_COMMIT = "e5969e6ee6294206954b5a83c5258fdb2e143eda"
OLD_ARCHIVE_SHA = "d16aac10c7adbc467cfaa9ba83e08933e91456e8cad8df569d8293315835d94b"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def record(path):
    return {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size,
            "sha256": sha(path.read_bytes())}


def run(args):
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    if result.returncode or result.stderr.strip():
        raise RuntimeError("Document conversion failed or warned: " + result.stderr[-6000:])


def word_style(path):
    document = Document(path)
    for section in document.sections:
        section.page_width, section.page_height = Mm(210), Mm(297)
        margin = 20 if path.stem == "Cover_Letter" else 22
        section.top_margin = section.bottom_margin = Mm(margin)
        section.left_margin = section.right_margin = Mm(margin)
        footer = section.footer.paragraphs[0]
        footer.alignment = 1
        field = OxmlElement("w:fldSimple")
        field.set(qn("w:instr"), "PAGE")
        footer._p.append(field)
    for style in document.styles:
        if style.type == 1:
            style.font.name, style.font.size = "Times New Roman", Pt(12)
            style.font.color.rgb = RGBColor(0, 0, 0)
            style.paragraph_format.line_spacing = 1.15
            style.paragraph_format.space_after = Pt(6)
    for name, size in (("Title", 18), ("Heading 1", 16), ("Heading 2", 14)):
        if name in document.styles:
            document.styles[name].font.size = Pt(size)
    for table in document.tables:
        table.autofit = True
        for row_index, row in enumerate(table.rows):
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.line_spacing = 1.05
                    for span in paragraph.runs:
                        span.font.name, span.font.size = "Times New Roman", Pt(12)
                        if row_index == 0:
                            span.bold = True
                    for shading in cell._tc.findall(".//" + qn("w:shd")):
                        shading.getparent().remove(shading)
    for paragraph in document.paragraphs:
        if re.match(r"(?:Table|Figure)\s+(?:S?\d+)\.", paragraph.text):
            paragraph.paragraph_format.keep_with_next = True
    document.core_properties.author = "Ziyuan Zhu; Sihao Liu; Haoyang Yu"
    document.save(path)
    text = " ".join(p.text for p in document.paragraphs)
    text += " " + " ".join(c.text for t in document.tables for row in t.rows for c in row.cells)
    return {"tables": len(document.tables), "embedded_figures": len(document.inline_shapes),
            "complete_word_count_including_tables_references": len(text.split()),
            "editable_math_objects": len(document.element.findall(
                ".//{http://schemas.openxmlformats.org/officeDocument/2006/math}oMath")),
            "body_font_pt": 12, "table_font_pt": 12, "line_spacing": 1.15}


def source_check():
    main = (OUT / "MAIN.md").read_text()
    previous = (OLD / "MAIN.md").read_text()
    cleanup = json.loads((AUDIT / "narrative_cleanup_20261104.json").read_text())
    pairs = cleanup["authorized_paragraph_rephrasings"]
    def canonical_editorial(text):
        mapping = {row[key]: f"[recorded editorial paragraph {i}]"
                   for i, row in enumerate(pairs)
                   for key in ("old_paragraph_sha256", "new_paragraph_sha256")}
        return "\n\n".join(mapping.get(sha(part.encode()), part) for part in text.split("\n\n"))
    def scientific(text):
        text = canonical_editorial(text)
        text = text.split("## Introduction\n", 1)[1].split("## Data and code availability\n", 1)[0]
        text = re.sub(r"### Computational checks and AI assistance\n.*?(?=### Statistical units)",
                      "", text, flags=re.S)
        for lower, upper in zip("abcd", "ABCD"):
            text = text.replace("(" + lower + ")", upper)
        return text
    if scientific(main) != scientific(previous):
        raise ValueError("Scientific manuscript changed beyond the recorded presentation/AI changes")
    table_index = json.loads((OUT / "SUPPLEMENT_TABLE_INDEX.json").read_text())
    def canonical_supplement(text):
        entries = table_index["tables"]
        if all(row["new_caption_paragraph"] in text for row in entries):
            for row in entries:
                placeholder = f"[caption slot {row['position']}]" if row["old_caption_paragraph"] else ""
                text = text.replace(row["new_caption_paragraph"], placeholder, 1)
            inverse = {new: old for old, new in table_index["old_to_new_labels"].items()}
            text = re.sub(r"\bTable (S\d+)\b", lambda match: "Table " + inverse.get(match[1], match[1]), text)
            for row in entries:
                if row["old_caption_paragraph"]:
                    text = text.replace(f"[caption slot {row['position']}]", row["old_caption_paragraph"])
        text = canonical_editorial(text)
        return "\n\n".join(part for part in text.split("\n\n") if part.strip())
    supplement = (OUT / "SUPPLEMENT.md").read_text()
    if canonical_supplement(supplement) != canonical_supplement((OLD / "SUPPLEMENT.md").read_text()):
        raise ValueError("Supplement changed beyond the exact recorded editorial paragraphs")
    tables = re.findall(r"(?m)^\|[^\n]*(?:\n\|[^\n]*)*", supplement)
    if len(tables) != 27 or any(sha(text.encode()) != row["table_rows_sha256"]
                                for text, row in zip(tables, table_index["tables"])):
        raise ValueError("Supplementary table values changed")
    if re.findall(r"(?m)^\*\*Table S(\d+)\.", supplement) != [str(i) for i in range(1, 28)]:
        raise ValueError("Supplementary table captions must run consecutively S1-S27")
    abstract = main.split("## Abstract\n", 1)[1].split("**Keywords:**", 1)[0].strip()
    labels = re.findall(r"\*\*(Objective|Approach|Main results|Significance):\*\*", abstract)
    if labels != ["Objective", "Approach", "Main results", "Significance"]:
        raise ValueError("Required JNE abstract labels missing or unordered")
    abstract_words = len(abstract.replace("**", "").split())
    if abstract_words > 300 or re.search(r"(?<!\w)@[A-Za-z]", abstract):
        raise ValueError("Abstract length or citation check failed")
    if "## Acknowledgements" not in main or "**AI disclosure.**" not in main:
        raise ValueError("IOP AI acknowledgement missing")
    (OUT / "ABSTRACT_FOR_SUBMISSION.txt").write_text(abstract.replace("**", "") + "\n")
    return {"science_source_commit": SCIENCE_COMMIT,
            "scientific_body_unchanged_excluding_recorded_editorial_rephrasings_AI_methods_and_panel_case": True,
            "supplement_unchanged_excluding_recorded_editorial_rephrasings_and_table_presentation": True,
            "supplementary_table_captions": list(range(1, 28)),
            "all_27_supplementary_table_blocks_byte_identical": True,
            "exact_editorial_paragraph_pairs": len(pairs), "abstract_headings": labels,
            "abstract_word_count": abstract_words}


def build_documents():
    checks = source_check()
    AUDIT.mkdir(parents=True, exist_ok=True)
    sources = OUT / "Sources"
    sources.mkdir(exist_ok=True)
    third = OUT / "Third_Party"
    third.mkdir(exist_ok=True)
    shutil.copyfile(OLD / "references.bib", OUT / "references.bib")
    for name in ("bmt_vancouver.csl", "README.md"):
        shutil.copyfile(OLD / "Third_Party" / name, third / name)
    (third / "JNE_USE.md").write_text(
        "# Citation style in this JNE review copy\n\n"
        "The historical locally adapted Vancouver CSL is retained for consistent numbered references. "
        "JNE permits consistent Vancouver references at initial submission; this is not an official IOP style. "
        "The original CSL credits and CC BY-SA 3.0 terms remain unchanged (see README.md).\n")
    (sources / "layout.tex").write_text(
        "\\usepackage{needspace}\n\\usepackage{xurl}\n\\usepackage{seqsplit}\n")
    metadata = {row["filename"]: row for row in csv.DictReader((OUT / "SUPPLEMENT_METADATA.csv").open())}
    bib = OUT / "references.bib"
    keys = set(re.findall(r"@\w+\s*\{\s*([^,]+),", bib.read_text()))
    documents = {}
    for filename, stem in (("MAIN.md", "JNE_Manuscript"),
                           ("SUPPLEMENT.md", "Supplementary_Methods"),
                           ("DECLARATIONS.md", "Declarations"),
                           ("COVER_LETTER.md", "Cover_Letter"),
                           ("RELATED_MANUSCRIPT_STATEMENT.md", "Related_Manuscript_Statement")):
        text = (OUT / filename).read_text()
        unresolved = set(re.findall(r"(?<!\w)@([A-Za-z0-9_:-]+)", text)) - keys
        if unresolved or re.search(r"\{\{[A-Za-z0-9_]+\}\}", text):
            raise ValueError("Unresolved reference or template field: " + str(unresolved))
        if filename == "SUPPLEMENT.md":
            row = metadata[stem + ".pdf"]
            text = text.split("\n", 1)[0] + "\n\n**Supplement title:** " + row["title"] + "\n\n**Description:** " + row["description"] + "\n" + text.split("\n", 1)[1]
        text = text.replace("{width=100%}", "{width=150mm}")
        word_source = sources / (stem + "_word.md")
        word_source.write_text(text)
        common = ["pandoc", str(word_source), "--from=markdown-implicit_figures+tex_math_single_backslash+autolink_bare_uris",
                  "--standalone", "--citeproc", "--bibliography", str(bib), "--csl", str(third / "bmt_vancouver.csl"),
                  "--resource-path", str(OUT), "--metadata", "lang=en-US"]
        run(common + ["-o", str(OUT / (stem + ".docx"))])
        word = word_style(OUT / (stem + ".docx"))
        table_space = 25 if filename == "MAIN.md" else 10
        text = re.sub(r"(?m)^(\*\*Table (?:S?\d+)\..*)$",
                      lambda m: f"\\Needspace{{{table_space}\\baselineskip}}\n\n" + m[1], text)
        if filename == "SUPPLEMENT.md":
            text = text.replace("## S 1. Analysis layers and statistical units",
                                "\\Needspace{20\\baselineskip}\n\n## S 1. Analysis layers and statistical units")
        def figure_space(match):
            path = OUT / match[2].replace(".png", ".pdf")
            with fitz.open(path) as figure:
                image_height = figure[0].rect.height * (150 / 25.4 * 72) / figure[0].rect.width
            caption_lines = math.ceil(len(match[3].split()) / 17) + 1
            reserve = min(700, image_height + caption_lines * 17 + 28)
            return f"\\Needspace{{{reserve:.1f}pt}}\n\n" + match[1] + "\n\n" + match[3]
        text = re.sub(r"(?m)^(!\[Figure[^\n]+\]\(([^\)]+)\)\{[^\n]+\})\n\n(\*\*Figure[^\n]+)",
                      figure_space, text)
        if filename == "MAIN.md":
            text = text.replace("## Supplementary material", "\\Needspace{9\\baselineskip}\n\n## Supplementary material")
        text = re.sub(r"(!\[[^\]]*\]\()([^\)]+)\.png(\))", lambda m: m[1] + m[2] + ".pdf" + m[3]
                      if (OUT / (m[2] + ".pdf")).is_file() else m[0], text)
        text = re.sub(r"`([A-Za-z0-9_./:;=+-]{24,})`", lambda m: r"\texttt{\seqsplit{" + m[1].replace("_", r"\_") + "}}", text)
        text = text.replace("software_validation_only=true", r"\seqsplit{software\_validation\_only=true}")
        pdf_source = sources / (stem + "_pdf.md")
        pdf_source.write_text(text)
        common[1] = str(pdf_source)
        run(common + ["--include-in-header", str(sources / "layout.tex"), "--pdf-engine=xelatex",
                      "-V", "mainfont=DejaVu Serif", "-V", "sansfont=DejaVu Sans", "-V", "monofont=DejaVu Sans Mono",
                      "-V", "geometry:margin=" + ("20mm" if filename == "COVER_LETTER.md" else "22mm"),
                      "-V", "fontsize=12pt", "-V",
                      "linestretch=" + ("1.15" if filename in {"MAIN.md", "SUPPLEMENT.md"} else "1.0"),
                      "-V", "colorlinks=true", "-V", "urlcolor=blue", "-o", str(OUT / (stem + ".pdf"))])
        with fitz.open(OUT / (stem + ".pdf")) as pdf:
            content = "\n".join(page.get_text() for page in pdf)
            if "[?]" in content or "\ufffd" in content or any(not page.get_text().strip() for page in pdf):
                raise ValueError("Unresolved/empty PDF: " + stem)
            documents[stem] = {"word": word, "pdf_pages": len(pdf),
                               "pdf_raster_images": sum(len(page.get_images()) for page in pdf)}
    if documents["JNE_Manuscript"]["word"]["embedded_figures"] != 5 or documents["JNE_Manuscript"]["word"]["tables"] != 2:
        raise ValueError("JNE initial main file requires the complete 5 figures and 2 tables")
    if documents["JNE_Manuscript"]["pdf_raster_images"]:
        raise ValueError("Main PDF figures must remain vector")
    if documents["JNE_Manuscript"]["word"]["complete_word_count_including_tables_references"] > 12000:
        raise ValueError("Manuscript exceeds the normal word guideline")
    checks.update(documents=documents, no_scientific_execution=True,
                  initial_submission="complete embedded-figure PDF", manuscript_font_pt=12,
                  review_pdf_page_count_is_not_typeset_page_count=True,
                  reference_style="historical consistent numbered Vancouver; not official IOP template",
                  historical_scientific_files_modified=False)
    (OUT / "JOURNAL_FORMAT_CHECKS.json").write_text(json.dumps(checks, indent=2) + "\n")


def package():
    original = OLD / "Supplementary_Data_and_Code.zip"
    if sha(original.read_bytes()) != OLD_ARCHIVE_SHA:
        raise ValueError("Frozen scientific archive changed")
    metadata = list(csv.DictReader((OUT / "SUPPLEMENT_METADATA.csv").open()))
    if any(len(x["title"]) > 30 or len(x["description"].split()) > 30 for x in metadata):
        raise ValueError("Supplement metadata exceeds IOP limits")
    selected = set()
    for directory in (DOCS, AUDIT, ROOT / "research_logs/paper2_jne_presubmission_20261104",
                      ROOT / "research_logs/paper2_jne_author_approval_20261104", OUT):
        selected.update(p for p in directory.rglob("*") if p.is_file() and p.suffix in {".md", ".json", ".csv", ".bib", ".csl", ".tex"}
                        and p.name not in {"PACKAGE_SHA256.json", "FILE_MANIFEST.json", "FINAL_VALIDATION.json", "GITHUB_FULL_GET_RECEIPT.json"})
    selected.update(ROOT.glob("scripts/*jne*20261104.py"))
    # The source archive already contains all scientific data/code and historical provenance.
    data = OUT / "Supplementary_Data_and_Code.zip"
    with zipfile.ZipFile(original) as old, zipfile.ZipFile(data, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as new:
        for entry in old.infolist():
            new.writestr(entry, old.read(entry.filename))
        row = metadata[1]
        readme = ("# " + row["title"] + "\n\n**Description:** " + row["description"] + "\n\n"
                  "JNE format revision of the fixed scientific results at " + SCIENCE_COMMIT + ". "
                  "All 1,392 historical archive entries are retained byte for byte, including their historical BMT paths. "
                  "Current JNE materials are under manuscript/jne_alignment_20261104. "
                  "See its REPRODUCTION.md for saved-result-only commands. No raw EEG, model weights or credentials are included.\n")
        new.writestr("README_JNE.md", readme)
        old_names = set(old.namelist())
        for path in sorted(selected):
            name = str(path.relative_to(ROOT))
            if name in old_names:
                raise ValueError("Attempt to overwrite historical scientific entry: " + name)
            new.write(path, name)
    with zipfile.ZipFile(original) as old, zipfile.ZipFile(data) as new:
        identical = all(old.read(name) == new.read(name) for name in old.namelist())
        if not identical or new.testzip():
            raise ValueError("Public scientific archive preservation failed")
        archive_check = {"historical_entries": len(old.namelist()), "new_total_entries": len(new.namelist()),
                         "all_historical_entries_byte_identical": identical, "original_archive_sha256": OLD_ARCHIVE_SHA}
    bundle = OUT / "JNE_Author_Review_Package.zip"
    bundle_files = [p for p in sorted(OUT.rglob("*")) if p.is_file()
                    and p.name not in {bundle.name, "PACKAGE_SHA256.json", "FILE_MANIFEST.json"}]
    file_manifest = {"scope": "Files inside the JNE author-review ZIP, excluding this manifest",
                     "files": [{"file": str(p.relative_to(OUT)), "bytes": p.stat().st_size,
                                "sha256": sha(p.read_bytes())} for p in bundle_files]}
    (OUT / "FILE_MANIFEST.json").write_text(json.dumps(file_manifest, indent=2) + "\n")
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(OUT.rglob("*")):
            if path.is_file() and path.name not in {bundle.name, "PACKAGE_SHA256.json"}:
                archive.write(path, str(path.relative_to(OUT)))
    uploads = [OUT / "JNE_Manuscript.pdf", OUT / "Supplementary_Methods.pdf", data]
    if any(p.stat().st_size > 50_000_000 for p in uploads[1:]) or sum(p.stat().st_size for p in uploads) > 150_000_000:
        raise ValueError("IOP submission file-size limits exceeded")
    author_status = json.loads((OUT / "SUBMISSION_STATUS.json").read_text())
    receipt = {"journal": "Journal of Neural Engineering", "status": author_status["status"],
               "author_approval": {"recorded": author_status["final_jne_files_author_approval_recorded"],
                                   "date": author_status.get("author_confirmation_date"),
                                   "approved_base_commit": author_status.get("author_approved_base_commit"),
                                   "authors_consent_to_submit": author_status.get("authors_consent_to_submit")},
               "submitted": False, "main_branch_merged": False, "new_fits_or_query_forwards": 0,
               "science_preservation": archive_check, "actual_supplement_files": metadata,
               "submission_file_bytes": sum(p.stat().st_size for p in uploads),
               "archives": [record(data), record(bundle)]}
    (OUT / "PACKAGE_SHA256.json").write_text(json.dumps(receipt, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-package", action="store_true")
    parser.add_argument("--package-only", action="store_true")
    args = parser.parse_args()
    if not args.package_only:
        build_documents()
    if not args.no_package:
        package()


if __name__ == "__main__":
    main()
