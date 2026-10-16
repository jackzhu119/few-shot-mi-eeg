"""Check final PDF/DOCX structures without rendering native Word or changing exports."""

import argparse
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

ROOT = Path("/workspace/few-shot-mi-eeg")
HERE = Path(__file__).resolve().parent
OUT = ROOT / "manuscript/plos_one_submission_20261016"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W, "m": "http://schemas.openxmlformats.org/officeDocument/2006/math"}
XHTML = "{http://www.w3.org/1999/xhtml}"
K = "{" + W + "}"
STEMS = (
    "manuscript_for_submission",
    "manuscript_for_review",
    "S1_Text",
    "S2_Text",
    "author_worksheet",
    "cover_letter_draft",
)
checks = []


def check(condition, description):
    checks.append({"description": description, "passed": bool(condition)})


def record(path):
    data = path.read_bytes()
    return {
        "path": str(path.relative_to(ROOT)),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def run(command):
    return subprocess.run(command, capture_output=True, text=True, check=True).stdout


def normalized(value):
    return re.sub(r"\s+", " ", value.replace("`", "")).strip()


def markdown_tables(text):
    lines = text.splitlines()
    result = []
    for index, line in enumerate(lines):
        if (
            line.startswith("| ")
            and index + 1 < len(lines)
            and re.match(r"^\|\s*[-:]+\s*\|", lines[index + 1])
        ):
            rows = []
            cursor = index
            while cursor < len(lines) and lines[cursor].startswith("| "):
                if cursor != index + 1:
                    rows.append(
                        [normalized(x) for x in lines[cursor].strip().strip("|").split("|")]
                    )
                cursor += 1
            result.append(rows)
    return result


def paragraph_text(paragraph):
    return "".join(t.text or "" for t in paragraph.findall(".//w:t", NS))


def docx_check(path, expected_main_tables):
    with ZipFile(path) as archive:
        document = ET.fromstring(archive.read("word/document.xml"))
        style_root = ET.fromstring(archive.read("word/styles.xml"))
        styles = {x.get(K + "styleId"): x for x in style_root.findall("w:style", NS)}

        def inherited_line(style_id, seen=None):
            seen = set() if seen is None else seen
            if style_id in seen:
                return None
            seen.add(style_id)
            style = styles.get(style_id)
            if style is None:
                return None
            spacing = style.find("w:pPr/w:spacing", NS)
            if spacing is not None and spacing.get(K + "line"):
                return spacing.get(K + "line")
            base = style.find("w:basedOn", NS)
            return inherited_line(base.get(K + "val"), seen) if base is not None else None

        paragraphs = document.findall(".//w:p", NS)
        text_paragraphs = [paragraph_text(p) for p in paragraphs]
        table_nodes = document.findall(".//w:tbl", NS)
        tables = [
            [
                [normalized(paragraph_text(cell)) for cell in row.findall("w:tc", NS)]
                for row in table.findall("w:tr", NS)
            ]
            for table in table_nodes
        ]
        image_members = [x for x in archive.namelist() if x.startswith("word/media/")]
        drawing_count = len(document.findall(".//w:drawing", NS))
        lines = [
            {key.split("}")[-1]: value for key, value in node.attrib.items()}
            for node in document.findall(".//w:lnNumType", NS)
        ]
        sections = document.findall(".//w:sectPr", NS)
        page_fields = []
        for name in archive.namelist():
            if name.startswith("word/") and "footer" in name and name.endswith(".xml"):
                footer = ET.fromstring(archive.read(name))
                page_fields.extend(x.get(K + "instr") for x in footer.findall(".//w:fldSimple", NS))
        check("PAGE" in page_fields, f"{path.name}: actual PAGE footer field")
        check(
            all(section.find("w:footerReference", NS) is not None for section in sections),
            f"{path.name}: footer linked in each section",
        )
        numbered = path.stem in STEMS[:4]
        check(
            (len(lines) == len(sections) and all(x.get("restart") == "continuous" for x in lines))
            if numbered
            else not lines,
            f"{path.name}: expected continuous line-numbering metadata",
        )
        spacing_histogram = Counter()
        for paragraph in paragraphs:
            if not paragraph_text(paragraph).strip():
                continue
            style = paragraph.find("w:pPr/w:pStyle", NS)
            style_id = style.get(K + "val") if style is not None else "Normal"
            direct = paragraph.find("w:pPr/w:spacing", NS)
            line = (
                direct.get(K + "line")
                if direct is not None and direct.get(K + "line")
                else inherited_line(style_id)
            )
            spacing_histogram[(style_id, line)] += 1
        expected_line = "480" if numbered else "264"
        check(
            all(line == expected_line for _, line in spacing_histogram),
            f"{path.name}: effective paragraph spacing {expected_line}/240 lines",
        )
        bibliography = [
            paragraph_text(p)
            for p in paragraphs
            if (style := p.find("w:pPr/w:pStyle", NS)) is not None
            and style.get(K + "val") == "Bibliography"
        ]
        if path.stem.startswith("manuscript_"):
            check(len(tables) == 5, f"{path.name}: five native editable tables")
            check(tables == expected_main_tables, f"{path.name}: every main-table cell matches source")
            expected_images = 4 if path.stem.endswith("review") else 0
            check(
                len(image_members) == drawing_count == expected_images,
                f"{path.name}: expected {expected_images} embedded figures",
            )
            check(len(bibliography) == 16, f"{path.name}: sixteen bibliography paragraphs")
            for index in range(1, 6):
                check(
                    sum(p.startswith(f"Table {index}.") for p in text_paragraphs) == 1,
                    f"{path.name}: Table {index} caption occurs once",
                )
            for index in range(1, 5):
                check(
                    sum(p.startswith(f"Fig {index}.") for p in text_paragraphs) == 1,
                    f"{path.name}: Fig {index} caption occurs once",
                )
        else:
            check(not image_members and drawing_count == 0, f"{path.name}: no embedded figures")
        if path.stem == "S1_Text":
            check(
                any(p.startswith("S11. Post-review exploratory paired sign-flip checks") for p in text_paragraphs),
                f"{path.name}: new S11 present",
            )
            check(document.find(".//m:oMath", NS) is not None, f"{path.name}: native equation elements present")
        return {
            **record(path),
            "native_tables": len(tables),
            "table_cells": tables,
            "image_members": len(image_members),
            "drawing_elements": drawing_count,
            "bibliography_paragraphs": len(bibliography),
            "section_line_numbers": lines,
            "PAGE_footer_fields": page_fields,
            "effective_spacing_histogram": {
                f"{style}:{line}": count for (style, line), count in spacing_histogram.items()
            },
            "native_Word_layout_rendered": False,
        }


def pdf_check(path):
    info = run(["pdfinfo", str(path)])
    text = run(["pdftotext", "-layout", str(path), "-"])
    root = ET.fromstring(run(["pdftotext", "-bbox-layout", str(path), "-"]))
    pages = root.findall(".//" + XHTML + "page")
    overflow = []
    empty = []
    sparse = []
    page_topics = {}
    for number, page in enumerate(pages, 1):
        width, height = float(page.get("width")), float(page.get("height"))
        words = page.findall(".//" + XHTML + "word")
        joined = " ".join("".join(word.itertext()) for word in words)
        for word in words:
            a = word.attrib
            if (
                float(a["xMin"]) < -0.25
                or float(a["yMin"]) < -0.25
                or float(a["xMax"]) > width + 0.25
                or float(a["yMax"]) > height + 0.25
            ):
                overflow.append({"page": number, "text": word.text, "box": a})
        if not joined.strip():
            empty.append(number)
        if len(words) < 30:
            sparse.append({"page": number, "word_count": len(words), "text": joined})
        for term in ("Table 5.", "S11.", "References", "Supporting information captions"):
            if term in joined:
                page_topics.setdefault(term, []).append(number)
    check(len(pages) == int(re.search(r"^Pages:\s+(\d+)", info, re.M)[1]), f"{path.name}: actual page count agrees")
    check(not overflow, f"{path.name}: no word crosses physical PDF boundary")
    check(not empty, f"{path.name}: no empty-text pages")
    check(not sparse, f"{path.name}: no nearly empty page under 30 words")
    check("[@" not in text and "??" not in text, f"{path.name}: no unresolved citation markers")
    fonts = run(["pdffonts", str(path)])
    check("LiberationSerif" in fonts, f"{path.name}: actual installed PDF body font recorded")
    if path.stem.startswith("manuscript_"):
        refs = text.split("References", 1)[1].split("Supporting information captions", 1)[0]
        reference_ids = [int(x) for x in re.findall(r"^\s*\d+\s+(\d+)\.\s+", refs, re.M)]
        check(reference_ids == list(range(1, 17)), f"{path.name}: all sixteen numbered references")
        for prefix, maximum in (("Table", 5), ("Fig", 4)):
            for index in range(1, maximum + 1):
                count = len(re.findall(r"^\s*(?:\d+\s+)?" + prefix + r"\s+" + str(index) + r"\.", text, re.M))
                check(count == 1, f"{path.name}: {prefix} {index} caption occurs once")
        for value in ("0.01953", "0.05859", "0.01025", "0.04102", "0.26123", "0.07617", "0.15234"):
            check(value in text, f"{path.name}: Table 5 value {value} present")
    if path.stem == "S1_Text":
        for value in ("S11.", "0.01953125", "0.05859375", "0.041015625", "0.15234375", "0.807128"):
            check(value in text, f"{path.name}: new statistical section value {value} present")
    if path.stem == "author_worksheet":
        check("确认按上述限定范围激活" in text, f"{path.name}: exact approved Chinese reply survives export")
        check("NotoSerifCJK" in fonts, f"{path.name}: actual CJK fallback embedded")
    return {
        **record(path),
        "pages": len(pages),
        "physical_overflow": overflow,
        "empty_text_pages": empty,
        "sparse_pages_under_30_words": sparse,
        "key_section_pages": page_topics,
        "actual_embedded_fonts": fonts,
        "pdfinfo": info,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-name", required=True)
    args = parser.parse_args()
    destination = HERE / args.report_name
    if destination.parent != HERE or destination.exists():
        raise ValueError("Require a fresh report filename within the QA directory")
    source = ROOT / "manuscript/kumar_plos_one_submission_draft_20261016.md"
    expected = markdown_tables(source.read_text())
    check(len(expected) == 5, "source contains five tables")
    docx = [docx_check(OUT / f"{stem}.docx", expected) for stem in STEMS]
    pdfs = [pdf_check(OUT / f"{stem}.pdf") for stem in STEMS]
    failures = [item for item in checks if not item["passed"]]
    result = {
        "status": "passed" if not failures else "issues_found",
        "script": record(Path(__file__).resolve()),
        "current_source": record(source),
        "checks": len(checks),
        "failures": failures,
        "docx": docx,
        "PDF": pdfs,
        "check_details": checks,
        "visual_QA_recorded_separately": True,
        "native_Word_layout_rendered": False,
        "native_Word_pagination_claimed": False,
        "scientific_execution": "none; ZIP XML, PDF text/metadata and exported-document checks only",
    }
    with destination.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(json.dumps({"status": result["status"], "checks": len(checks), "failures": failures}))


if __name__ == "__main__":
    main()
