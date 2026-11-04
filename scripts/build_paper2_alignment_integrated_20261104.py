"""Build the isolated EA extension from completed analyses; never fits a model."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

from docx import Document
from docx.shared import RGBColor
import fitz

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "manuscript/bmt_alignment_integrated_20261104"
AUDIT = ROOT / "research_logs/paper2_alignment_integrated_20261104"
DOCS = ROOT / "docs/paper2_alignment_integrated_20261104"
SPEC = importlib.util.spec_from_file_location(
    "existing_document_helpers", ROOT / "scripts/build_paper2_discovery_revision_20261027.py"
)
HELPER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPER)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command):
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError("Document export failed: " + result.stderr[-6000:])
    return result.stderr


def style_word(path):
    info = HELPER.format_word(path)
    document = Document(path)
    for name in ("Title", "Subtitle", "Heading 1", "Heading 2", "Heading 3", "Heading 4"):
        if name in document.styles:
            document.styles[name].font.color.rgb = RGBColor(0, 0, 0)
            document.styles[name].font.name = "Times New Roman"
    for paragraph in document.paragraphs:
        if re.match(r"(?:Table|Figure)\s+(?:S?\d+)\.", paragraph.text):
            paragraph.paragraph_format.keep_with_next = True
    document.core_properties.author = "Ziyuan Zhu; Sihao Liu; Haoyang Yu"
    document.save(path)
    info["editable_math_objects"] = len(document.element.findall(
        ".//{http://schemas.openxmlformats.org/officeDocument/2006/math}oMath"
    ))
    return info


def fill_templates():
    tokens_path = OUT / "MANUSCRIPT_TOKENS.json"
    tokens = json.loads(tokens_path.read_text()) if tokens_path.exists() else {}
    for name in ("MAIN", "SUPPLEMENT"):
        text = (OUT / (name + ".template.md")).read_text()
        needed = set(re.findall(r"\{\{([A-Z0-9_]+)\}\}", text))
        missing = needed - tokens.keys()
        if missing:
            raise ValueError("Unresolved manuscript evidence fields: " + str(sorted(missing)))
        for key in needed:
            text = text.replace("{{" + key + "}}", tokens[key])
        if re.search(r"\{\{[A-Za-z0-9_]+\}\}", text):
            raise ValueError("Unresolved template marker in " + name)
        (OUT / (name + ".md")).write_text(text)


def declaration_word():
    text = (OUT / "Ethical_and_Legal_Declarations.md").read_text()
    parts = re.split(r"^## (.+)\n", text, flags=re.M)
    fields = {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}
    document = Document()
    document.add_heading("Ethical and legal declarations", 0)
    document.add_paragraph("Biomedical Engineering / Biomedizinische Technik — integrated extension for author review")
    document.add_paragraph((OUT / "MAIN.md").read_text().splitlines()[0][2:])
    document.add_paragraph("Ziyuan Zhu; Sihao Liu; Haoyang Yu")
    table = document.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    table.rows[0].cells[0].text = "STATEMENT"
    table.rows[0].cells[1].text = "TEXT"
    for key in ("Acknowledgments", "Research ethics", "Informed consent", "Author contributions",
                "Use of large language models, AI and machine learning tools", "Conflict of interest",
                "Research funding", "Data availability", "Software availability"):
        cells = table.add_row().cells
        cells[0].text, cells[1].text = key, fields[key].replace("**", "")
    path = OUT / "Ethical_and_Legal_Declarations.docx"
    document.save(path)
    return style_word(path)


def build_documents():
    fill_templates()
    third_party = OUT / "Third_Party"
    third_party.mkdir(exist_ok=True)
    for path in (ROOT / "manuscript/bmt_component_revision_20261029/Third_Party").glob("*"):
        if path.is_file():
            shutil.copyfile(path, third_party / path.name)
    bib = OUT / "references.bib"
    csl = third_party / "bmt_vancouver.csl"
    HELPER.CSL = csl
    main = (OUT / "MAIN.md").read_text()
    used = set(re.findall(r"(?<!\w)@([A-Za-z0-9_:-]+)", main))
    keys = set(re.findall(r"@\w+\s*\{\s*([^,]+),", bib.read_text()))
    checks = HELPER.journal_checks(main, used, bib)
    status = json.loads((OUT / "SUBMISSION_STATUS.json").read_text())
    declarations = (OUT / "Ethical_and_Legal_Declarations.md").read_text()
    checks.update({"status": status, "AI_disclosure_retained": "Codex" in declarations and "ChatGPT" in declarations,
                   "AI_disclosure_location": "separate Ethical and Legal Declarations",
                   "build_does_not_fit_or_infer": True})
    abstract = main.split("## Abstract\n", 1)[1].split("**Keywords:**", 1)[0].strip()
    (OUT / "ABSTRACT_FOR_SUBMISSION.txt").write_text(re.sub(r"\*\*", "", abstract) + "\n")
    sources = OUT / "Sources"
    sources.mkdir(exist_ok=True)
    (sources / "layout.tex").write_text(
        "\\usepackage{needspace}\n\\usepackage{xurl}\n\\usepackage{seqsplit}\n"
    )
    documents, warnings = {}, {}
    for filename, stem in (("MAIN.md", "BMT_Manuscript_Reading"),
                           ("SUPPLEMENT.md", "Supplementary_Methods"),
                           ("Ethical_and_Legal_Declarations.md", "Ethical_and_Legal_Declarations")):
        text = (OUT / filename).read_text()
        unresolved = set(re.findall(r"(?<!\w)@([A-Za-z0-9_:-]+)", text)) - keys
        if unresolved:
            raise ValueError("Unresolved references: " + str(unresolved))
        common = ["pandoc", str(OUT / filename), "--from=markdown-implicit_figures+tex_math_single_backslash+autolink_bare_uris",
                  "--standalone", "--citeproc", "--bibliography", str(bib), "--csl", str(csl),
                  "--resource-path", str(OUT), "--metadata", "lang=en-US"]
        if filename == "Ethical_and_Legal_Declarations.md":
            word_info = declaration_word()
        else:
            warnings[stem + "_word"] = run(common + ["-o", str(OUT / (stem + ".docx"))])
            word_info = style_word(OUT / (stem + ".docx"))
        text = re.sub(r"(?m)^(\*\*Table (?:S?\d+)\..*)$",
                      lambda m: "\\Needspace{12\\baselineskip}\n\n" + m[1], text)
        text = re.sub(r"(?m)^(!\[Figure[^\n]+)$",
                      lambda m: "\\Needspace{44\\baselineskip}\n\n" + m[1], text)
        text = re.sub(r"(!\[[^\]]*\]\()([^\)]+)\.png(\))",
                      lambda m: m[1] + m[2] + ".pdf" + m[3]
                      if (OUT / (m[2] + ".pdf")).is_file() else m[0], text)
        # Break long audit identifiers in PDF without changing their values or
        # the copyable identifiers in the editable manuscript sources.
        text = re.sub(r"`([A-Za-z0-9_./:;=+-]{24,})`",
                      lambda m: r"\texttt{\seqsplit{" + m[1].replace("_", r"\_") + "}}", text)
        text = text.replace("software_validation_only=true", r"\seqsplit{software\_validation\_only=true}")
        pdf_source = sources / (stem + ".md")
        pdf_source.write_text(text)
        pdf_common = list(common)
        pdf_common[1] = str(pdf_source)
        warnings[stem + "_pdf"] = run(pdf_common + [
            "--include-in-header", str(sources / "layout.tex"), "--pdf-engine=xelatex",
            "-V", "mainfont=DejaVu Serif", "-V", "sansfont=DejaVu Sans",
            "-V", "monofont=DejaVu Sans Mono", "-V", "geometry:margin=22mm",
            "-V", "fontsize=11pt", "-V", "colorlinks=true", "-V", "urlcolor=blue",
            "-o", str(OUT / (stem + ".pdf"))])
        with fitz.open(OUT / (stem + ".pdf")) as pdf:
            all_text = "\n".join(page.get_text() for page in pdf)
            if "[?]" in all_text or "\ufffd" in all_text or any(not page.get_text().strip() for page in pdf):
                raise ValueError("Broken/empty exported PDF: " + stem)
            documents[stem] = {"word": word_info, "pdf_pages": len(pdf),
                               "raster_image_objects": sum(len(page.get_images()) for page in pdf)}
    submission = sources / "BMT_Manuscript_For_Submission.md"
    submission.write_text(HELPER.submission_source(main))
    run(["pandoc", str(submission), "--from=markdown-implicit_figures+tex_math_single_backslash+autolink_bare_uris",
         "--standalone", "--citeproc", "--bibliography", str(bib), "--csl", str(csl),
         "--resource-path", str(OUT), "--metadata", "lang=en-US", "-o",
         str(OUT / "BMT_Manuscript_Submission.docx")])
    word = OUT / "BMT_Manuscript_Submission.docx"
    documents["BMT_Manuscript_Submission"] = style_word(word)
    if documents["BMT_Manuscript_Submission"]["tables"] != 2 or documents["BMT_Manuscript_Submission"]["inline_figures"]:
        raise ValueError("Submission Word must contain two editable tables and separate figures")
    document = Document(word)
    text = " ".join(p.text for p in document.paragraphs)
    text += " " + " ".join(c.text for t in document.tables for row in t.rows for c in row.cells)
    checks["exported_complete_word_count"] = len(text.split())
    if checks["exported_complete_word_count"] > 6000:
        raise ValueError("Exported complete manuscript exceeds 6000 words")
    if any(v.strip() for v in warnings.values()):
        raise ValueError("Document exporter warnings: " + str(warnings))
    checks.update(documents=documents, warnings=warnings)
    (OUT / "JOURNAL_FORMAT_CHECKS.json").write_text(json.dumps(checks, indent=2) + "\n")


def package():
    """Package reproducible public results, excluding private arrays and source bodies."""
    paths = set()
    for directory in (AUDIT, DOCS):
        paths.update(p for p in directory.rglob("*") if p.is_file()
                     and "/source_audit/paper1/files/" not in str(p)
                     and p.name not in {"PUBLIC_ZIP_REPRODUCTION.json", "FINAL_DELIVERY_CHECKS.json",
                                        "PUBLIC_GITHUB_FULL_GET_RECEIPT.json"}
                     and p.suffix in {".md", ".json", ".csv", ".yaml", ".txt", ".gz", ".py", ".log", ".jsonl"})
    for pattern in ("scripts/*alignment*20261104.py", "scripts/verify_saved_alignment_metrics_20261104.py",
                    "tests/test*alignment*.py"):
        paths.update(ROOT.glob(pattern))
    paths.update([ROOT / "src/learning_preserving_bci/__init__.py",
                  ROOT / "src/learning_preserving_bci/paper2_alignment_integrated.py",
                  ROOT / "src/learning_preserving_bci/alignment_mechanism.py",
                  ROOT / "scripts/build_paper2_discovery_revision_20261027.py",
                  ROOT / "LICENSE", ROOT / "LICENSING.md"])
    manifest_path = AUDIT / "analysis/INPUT_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text())
    entries = manifest if isinstance(manifest, list) else manifest.get("inputs", manifest.get("files", []))
    for entry in entries:
        rel = entry.get("path", "")
        path = ROOT / rel
        if path.is_file() and not Path(rel).is_absolute() and path.suffix in {".json", ".csv", ".gz"}:
            paths.add(path)
    # Include native phase metadata and the original code dependencies, while
    # leaving private prepared signal arrays outside the public package.
    native_inputs = json.loads((AUDIT / "input_audit/INPUT_MANIFEST.json").read_text())
    for entry in native_inputs.get("files", []):
        rel = entry.get("path", "")
        path = ROOT / rel
        if not Path(rel).is_absolute() and path.is_file() and path.suffix in {".json", ".csv", ".gz", ".py"}:
            paths.add(path)
    paths.update((OUT / "figures").glob("*.csv"))
    paths.update((OUT / "figures").glob("*.json"))
    for entry in json.loads((OUT / "figures/FIGURE_MANIFEST.json").read_text())["source_files"]:
        path = ROOT / entry["path"]
        if path.is_file() and path.suffix in {".json", ".csv"}:
            paths.add(path)
    for name in ("MAIN.md", "MAIN.template.md", "SUPPLEMENT.md", "SUPPLEMENT.template.md",
                 "MANUSCRIPT_TOKENS.json", "references.bib", "reproduction.md",
                 "Ethical_and_Legal_Declarations.md", "SUBMISSION_STATUS.json"):
        paths.add(OUT / name)
    for directory in (OUT / "Third_Party", OUT / "supplementary_figures"):
        paths.update(p for p in directory.glob("*") if p.is_file())
    data = OUT / "Supplementary_Data_and_Code.zip"
    with zipfile.ZipFile(data, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(paths):
            archive.write(path, str(path.relative_to(ROOT)))
    if data.stat().st_size > 10_000_000:
        raise ValueError("Public supplement exceeds 10 MB")
    bundle = OUT / "Integrated_Revision_Review_Package.zip"
    selected = [p for p in OUT.rglob("*") if p.is_file() and p.name not in {bundle.name, "PACKAGE_SHA256.json"}]
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(selected):
            archive.write(path, str(path.relative_to(OUT)))
    receipt = {"status": "isolated_extension_for_author_review", "submission_performed": False,
               "new_author_approval_inherited": False, "private_EEG_or_weights_included": False,
               "archives": [{"file": p.name, "bytes": p.stat().st_size, "sha256": digest(p)}
                            for p in (data, bundle)]}
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
    print(json.dumps({"output": str(OUT), "documents_built": not args.package_only,
                      "packaged": not args.no_package}))


if __name__ == "__main__":
    main()
