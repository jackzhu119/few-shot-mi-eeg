#!/usr/bin/env python3
"""Read final DOCX XML/PDF listings without modifying any document."""

import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LOG = Path(__file__).resolve().parent
DIRECTORY = ROOT / "manuscript/plos_one_submission_20261015"
NAMES = (
    "manuscript_for_review",
    "manuscript_for_submission",
    "S1_Text",
    "S2_Text",
    "author_worksheet",
    "cover_letter_draft",
)
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
W = "{" + NS["w"] + "}"
REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
OFFICE = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
checks = 0


def require(condition, message):
    global checks
    checks += 1
    if not condition:
        raise ValueError(message)


def record(path):
    data = path.read_bytes()
    return {
        "path": str(path.relative_to(ROOT)),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def normalize(text):
    return re.sub(r"\s+", " ", text).strip()


def markdown_tables(text):
    tables, current = [], []
    for line in text.splitlines():
        if line.startswith("|"):
            if not re.fullmatch(r"[\s|:\-]+", line):
                current.append([normalize(x) for x in line.strip("|").split("|")])
        elif current:
            tables.append(current)
            current = []
    if current:
        tables.append(current)
    return tables


def main():
    expected_tables = markdown_tables(
        (ROOT / "manuscript/kumar_longitudinal_decoding_working_draft_20261015.md").read_text()
    )
    require(len(expected_tables) == 3, "original three complete tables")
    expected_images = {
        hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (ROOT / "manuscript/figures/plos_submission_20261015").glob("Fig*.png")
    }
    require(len(expected_images) == 4, "four exact original figure PNG hashes")
    files_before = [
        record(DIRECTORY / f"{name}.{extension}") for name in NAMES for extension in ("pdf", "docx")
    ]
    results = []
    for name in NAMES:
        docx = DIRECTORY / f"{name}.docx"
        with zipfile.ZipFile(docx) as archive:
            root = ET.fromstring(archive.read("word/document.xml"))
            styles = ET.fromstring(archive.read("word/styles.xml"))
            relationships = ET.fromstring(archive.read("word/_rels/document.xml.rels"))
            media = [
                entry
                for entry in archive.namelist()
                if entry.startswith("word/media/") and not entry.endswith("/")
            ]
            tables = root.findall(".//w:tbl", NS)
            extracted = []
            for table in tables:
                rows = []
                for row in table.findall("./w:tr", NS):
                    rows.append(
                        [
                            normalize("".join(x.text or "" for x in cell.findall(".//w:t", NS)))
                            for cell in row.findall("./w:tc", NS)
                        ]
                    )
                extracted.append(rows)
            lines = root.findall(".//w:lnNumType", NS)
            simple_page_fields = []
            for part in archive.namelist():
                if part.startswith("word/") and part.endswith(".xml"):
                    part_root = ET.fromstring(archive.read(part))
                    simple_page_fields.extend(
                        {"part": part, "instruction": field.get(W + "instr")}
                        for field in part_root.findall(".//w:fldSimple", NS)
                        if field.get(W + "instr", "").strip().upper() == "PAGE"
                    )
            if name in ("manuscript_for_review", "manuscript_for_submission"):
                require(len(tables) == 4, f"{name}: four editable XML tables")
                for index in range(3):
                    require(
                        extracted[index] == expected_tables[index],
                        f"{name}: original table {index + 1} exact cells",
                    )
                require(
                    len(lines) == 1
                    and lines[0].get(W + "restart") == "continuous"
                    and lines[0].get(W + "countBy") == "1",
                    f"{name}: continuous line numbers",
                )
                for style_name in ("Normal", "BodyText", "FirstParagraph", "Compact"):
                    style = styles.find(f'.//w:style[@w:styleId="{style_name}"]', NS)
                    spacing = style.find("./w:pPr/w:spacing", NS)
                    require(
                        spacing is not None
                        and spacing.get(W + "line") == "480"
                        and spacing.get(W + "lineRule") == "auto",
                        f"{name}: double-line style {style_name}",
                    )
                footer_references = root.findall(".//w:footerReference", NS)
                require(len(footer_references) == 1, f"{name}: actual footer reference")
                identifier = footer_references[0].get(OFFICE + "id")
                matches = [
                    node
                    for node in relationships.findall(REL + "Relationship")
                    if node.get("Id") == identifier
                ]
                require(
                    len(matches) == 1 and matches[0].get("Type", "").endswith("/footer"),
                    f"{name}: footer relationship bound",
                )
                require(bool(simple_page_fields), f"{name}: live PAGE field")
                if name == "manuscript_for_review":
                    require(len(media) == 4, "review DOCX four images")
                    require(
                        {hashlib.sha256(archive.read(entry)).hexdigest() for entry in media}
                        == expected_images,
                        "review DOCX exact image source bytes",
                    )
                else:
                    require(len(media) == 0, "submission DOCX image-free")
            image_list = subprocess.run(
                ["pdfimages", "-list", str(DIRECTORY / f"{name}.pdf")],
                capture_output=True,
                text=True,
                check=True,
            ).stdout
            image_rows = [line.split() for line in image_list.splitlines()[2:] if line.strip()]
            raster_images = [row for row in image_rows if row[2] == "image"]
            soft_masks = [row for row in image_rows if row[2] == "smask"]
            if name == "manuscript_for_review":
                require(len(raster_images) == 4, "review PDF four actual raster images")
            elif name == "manuscript_for_submission":
                require(len(image_rows) == 0, "submission PDF image-free")
            results.append(
                {
                    "name": name,
                    "docx_images": len(media),
                    "docx_tables": len(tables),
                    "continuous_line_number_attributes": [x.attrib for x in lines],
                    "PAGE_fields": simple_page_fields,
                    "PDF_visible_image_count": len(raster_images),
                    "PDF_transparency_soft_mask_count": len(soft_masks),
                    "PDF_image_listing": image_list,
                    "original_three_tables_cell_identical": name.startswith("manuscript_for_"),
                }
            )
    files_after = [
        record(DIRECTORY / f"{name}.{extension}") for name in NAMES for extension in ("pdf", "docx")
    ]
    require(files_before == files_after, "all twelve source document bytes unchanged by inspection")
    result = {
        "status": "final_document_structure_checks_passed",
        "checks": checks,
        "failures": [],
        "documents": results,
        "source_files": files_after,
        "no_source_document_modified": True,
        "scope": "Actual PDF image listings and DOCX ZIP/XML only; no native Word rendering or Word pagination claim. PDF visual QA recorded separately. Figures in review PDF have soft masks from PNGs; separately uploaded TIFFs are flattened RGB/no-alpha.",
    }
    with (LOG / "final_document_structure_QA.json").open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print(json.dumps({"status": result["status"], "checks": checks, "failures": []}))


if __name__ == "__main__":
    main()
