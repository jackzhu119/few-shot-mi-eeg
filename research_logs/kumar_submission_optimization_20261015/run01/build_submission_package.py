"""Build journal and illustrated-review documents from saved text/figures only."""

import hashlib
import json
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path("/workspace/few-shot-mi-eeg")
LOG = ROOT / "research_logs/kumar_submission_optimization_20261015/run01"
OUT = ROOT / "manuscript/plos_one_submission_20261015"
BIB = ROOT / "manuscript/kumar_plos_one_references_20261015.bib"
CSL = ROOT / "manuscript/review_package_author_confirmed_20261015/plos.csl"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/package/2006/relationships"
ODR = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
ET.register_namespace("w", W)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def q(name):
    return "{" + W + "}" + name


def child(parent, name):
    found = parent.find(q(name))
    return found if found is not None else ET.SubElement(parent, q(name))


def reference_docx():
    path = LOG / "plos_reference.docx"
    if path.exists():
        raise FileExistsError(path)
    result = subprocess.run(
        ["pandoc", "--print-default-data-file=reference.docx"], capture_output=True, check=True
    )
    with path.open("xb") as handle:
        handle.write(result.stdout)
    with ZipFile(path) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    styles = ET.fromstring(files["word/styles.xml"])
    defaults = child(styles, "docDefaults")
    rp = child(child(defaults, "rPrDefault"), "rPr")
    fonts = child(rp, "rFonts")
    for key in ["ascii", "hAnsi", "eastAsia", "cs"]:
        fonts.set(q(key), "Times New Roman")
    child(rp, "sz").set(q("val"), "24")
    for style in styles.findall(q("style")):
        if style.get(q("styleId")) in [
            "Normal",
            "BodyText",
            "FirstParagraph",
            "Compact",
            "Caption",
        ]:
            sp = child(child(style, "pPr"), "spacing")
            sp.set(q("line"), "480")
            sp.set(q("lineRule"), "auto")
            fonts = child(child(style, "rPr"), "rFonts")
            for key in ["ascii", "hAnsi", "cs"]:
                fonts.set(q(key), "Times New Roman")
            child(child(style, "rPr"), "sz").set(q("val"), "24")
    files["word/styles.xml"] = ET.tostring(styles, encoding="utf-8", xml_declaration=True)
    temp = path.with_suffix(".tmp.docx")
    with ZipFile(temp, "w", ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    temp.replace(path)
    return path


def patch_word(path, continuous_lines):
    with ZipFile(path) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    doc = ET.fromstring(files["word/document.xml"])
    rels = ET.fromstring(files["word/_rels/document.xml.rels"])
    types = ET.fromstring(files["[Content_Types].xml"])
    relid = "rIdPlosPageFooter"
    if any(x.get("Id") == relid for x in rels):
        raise ValueError("Footer relationship collision")
    ET.SubElement(
        rels,
        "{" + R + "}Relationship",
        {"Id": relid, "Type": ODR + "/footer", "Target": "plos_footer.xml"},
    )
    ET.SubElement(
        types,
        "{" + CT + "}Override",
        {
            "PartName": "/word/plos_footer.xml",
            "ContentType": "application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml",
        },
    )
    for sect in doc.findall(".//" + q("sectPr")):
        if continuous_lines:
            line = ET.Element(q("lnNumType"))
            for key, value in {
                "countBy": "1",
                "start": "1",
                "restart": "continuous",
                "distance": "180",
            }.items():
                line.set(q(key), value)
            after = {
                q(x)
                for x in [
                    "pgNumType",
                    "cols",
                    "formProt",
                    "vAlign",
                    "noEndnote",
                    "titlePg",
                    "textDirection",
                    "bidi",
                    "rtlGutter",
                    "docGrid",
                    "printerSettings",
                    "sectPrChange",
                ]
            }
            position = next(
                (i for i, element in enumerate(sect) if element.tag in after), len(sect)
            )
            sect.insert(position, line)
        for old in list(sect.findall(q("footerReference"))):
            sect.remove(old)
        reference = ET.Element(
            q("footerReference"), {q("type"): "default", "{" + ODR + "}id": relid}
        )
        sect.insert(sum(element.tag == q("headerReference") for element in sect), reference)
    if not continuous_lines:
        styles = ET.fromstring(files["word/styles.xml"])
        for style in styles.findall(q("style")):
            if style.get(q("styleId")) in [
                "Normal",
                "BodyText",
                "FirstParagraph",
                "Compact",
                "Caption",
            ]:
                spacing = child(child(style, "pPr"), "spacing")
                spacing.set(q("line"), "264")
                spacing.set(q("lineRule"), "auto")
                child(child(style, "rPr"), "sz").set(q("val"), "22")
        files["word/styles.xml"] = ET.tostring(styles, encoding="utf-8", xml_declaration=True)
    footer = ET.Element(q("ftr"))
    p = ET.SubElement(footer, q("p"))
    ET.SubElement(ET.SubElement(p, q("pPr")), q("jc"), {q("val"): "center"})
    field = ET.SubElement(p, q("fldSimple"), {q("instr"): "PAGE"})
    ET.SubElement(ET.SubElement(field, q("r")), q("t")).text = "1"
    files["word/plos_footer.xml"] = ET.tostring(footer, encoding="utf-8", xml_declaration=True)
    files["word/document.xml"] = ET.tostring(doc, encoding="utf-8", xml_declaration=True)
    files["word/_rels/document.xml.rels"] = ET.tostring(
        rels, encoding="utf-8", xml_declaration=True
    )
    files["[Content_Types].xml"] = ET.tostring(types, encoding="utf-8", xml_declaration=True)
    temp = path.with_suffix(".numbered.docx")
    with ZipFile(temp, "w", ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    temp.replace(path)


def export_source(source, kind, illustrated, article):
    text = source.read_text()
    title, text = text.split("\n", 1)
    title = title.lstrip("# ").strip()
    if not illustrated:
        text = re.sub(r"^!\[[^\]]*\]\([^\n]+\)(?:\{[^}]*\})?\s*$", "", text, flags=re.M)
    else:

        def image_link(match):
            path = (source.parent / match[2]).resolve()
            if not path.is_file():
                raise FileNotFoundError(path)
            return f"![{match[1]}]({path})" + (match[3] or "")

        text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)(\{[^}]*\})?", image_link, text)
    if article:
        pagebreak = (
            "\\newpage"
            if kind == "pdf"
            else '```{=openxml}\n<w:p><w:r><w:br w:type="page"/></w:r></w:p>\n```'
        )
        text = text.replace("## Abstract", pagebreak + "\n\n## Abstract", 1)
    if kind == "pdf":
        text = re.sub(
            r"`([a-f0-9]{40}|[a-f0-9]{64})`", lambda m: r"\texttt{\seqsplit{" + m[1] + "}}", text
        )
        text = re.sub(r"`([A-Za-z0-9_./:=-]{45,})`", lambda m: r"\path{" + m[1] + "}", text)
        text = text.replace("朱子元", r"\textcjk{朱子元}")
    return title, text


def main():
    OUT.mkdir(exist_ok=True)
    started = datetime.now(timezone.utc)
    env = dict(os.environ)
    env["SOURCE_DATE_EPOCH"] = str(int(started.timestamp()))
    reference = reference_docx()
    header = LOG / "plos_typesetting.tex"
    header.write_text(r"""\usepackage{xurl,seqsplit,fvextra,lineno}
\newfontfamily\cjknamefont{Noto Serif CJK SC}
\newcommand{\textcjk}[1]{{\cjknamefont #1}}
\emergencystretch=3em
\AtBeginDocument{\Urlmuskip=0mu plus 2mu}
\AtBeginDocument{\ifcsname Highlighting\endcsname\RecustomVerbatimEnvironment{Highlighting}{Verbatim}{commandchars=\\\{\},breaklines,breakanywhere,fontsize=\footnotesize}\fi}
""")
    sources = [
        (
            "manuscript_for_submission",
            "kumar_plos_one_submission_draft_20261015.md",
            False,
            True,
            True,
        ),
        ("manuscript_for_review", "kumar_plos_one_submission_draft_20261015.md", True, True, True),
        ("S1_Text", "kumar_plos_one_supporting_methods_20261015.md", False, False, True),
        ("S2_Text", "kumar_plos_one_audit_reproducibility_20261015.md", False, False, True),
        ("author_worksheet", "kumar_plos_one_author_worksheet_20261015.md", False, False, False),
        ("cover_letter_draft", "kumar_plos_one_cover_letter_20261015.md", False, False, False),
    ]
    inputs = {str(BIB.relative_to(ROOT)): sha(BIB), str(CSL.relative_to(ROOT)): sha(CSL)}
    commands = []
    outputs = []
    for name, filename, illustrated, article, numbered in sources:
        source = ROOT / "manuscript" / filename
        inputs[str(source.relative_to(ROOT))] = sha(source)
        for kind in ["pdf", "docx"]:
            title, body = export_source(source, kind, illustrated, article)
            render = LOG / f"{name}_{kind}_source.md"
            with render.open("x") as handle:
                handle.write(body)
            target = OUT / f"{name}.{kind}"
            if target.exists():
                raise FileExistsError(target)
            command = [
                "pandoc",
                str(render),
                "--from=markdown-implicit_figures",
                "--standalone",
                "--shift-heading-level-by=-1",
                "--citeproc",
                f"--bibliography={BIB}",
                f"--csl={CSL}",
                "--metadata",
                f"title={title}",
                "--metadata",
                "lang=en-US",
                "--metadata",
                "link-citations=true",
                "--output",
                str(target),
            ]
            if kind == "pdf":
                line_header = LOG / f"{name}_line_numbers.tex"
                line_header.write_text("\\AtBeginDocument{\\linenumbers}\n" if numbered else "")
                command += [
                    "--pdf-engine=xelatex",
                    f"--include-in-header={header}",
                    f"--include-in-header={line_header}",
                    "-V",
                    "papersize=a4",
                    "-V",
                    "geometry:margin=22mm",
                    "-V",
                    "mainfont=Liberation Serif",
                    "-V",
                    "sansfont=Liberation Sans",
                    "-V",
                    "monofont=DejaVu Sans Mono",
                    "-V",
                    "fontsize=12pt" if numbered else "fontsize=11pt",
                    "-V",
                    "linestretch=2" if numbered else "linestretch=1.1",
                    "-V",
                    "colorlinks=true",
                ]
            else:
                command.append(f"--reference-doc={reference}")
            begin = datetime.now(timezone.utc).isoformat()
            result = subprocess.run(
                command, cwd=ROOT, env=env, capture_output=True, text=True, check=False
            )
            (LOG / f"build_{name}_{kind}.stdout").write_text(result.stdout)
            (LOG / f"build_{name}_{kind}.stderr").write_text(result.stderr)
            commands.append(
                {
                    "command": command,
                    "started_at_utc": begin,
                    "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                    "returncode": result.returncode,
                }
            )
            (LOG / "build_commands.json").write_text(json.dumps(commands, indent=2) + "\n")
            if result.returncode:
                raise RuntimeError(f"Actual typesetting failure {target.name}; stderr retained")
            if kind == "docx":
                patch_word(target, numbered)
            outputs.append(
                {
                    "path": str(target.relative_to(ROOT)),
                    "bytes": target.stat().st_size,
                    "sha256": sha(target),
                    "illustrated": illustrated,
                    "continuous_line_numbering": numbered,
                    "PDF_font": "Liberation Serif (installed metric-compatible substitute)"
                    if kind == "pdf"
                    else None,
                    "Word_native_layout_rendered": False,
                }
            )
    assert all(sha(ROOT / name) == value for name, value in inputs.items())
    receipt = {
        "status": "rendered_pending_final_QA",
        "started_at_utc": started.isoformat(),
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "new_sources_not_in_base_commit": True,
        "SOURCE_DATE_EPOCH": env["SOURCE_DATE_EPOCH"],
        "script_sha256": sha(Path(__file__)),
        "inputs": inputs,
        "outputs": outputs,
        "fits_forwards_or_raw_EEG_decodes": 0,
        "journal_graphics_separate_from_submission_manuscript": True,
        "font_limit": "PDF and figure actual fonts are Liberation substitutions; exact Arial/Times production compliance not claimed",
        "Word_validation": "Structural/text/numbering checks later; native Word layout unavailable",
    }
    (LOG / "document_build_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": receipt["status"], "exports": len(outputs)}))


if __name__ == "__main__":
    main()
