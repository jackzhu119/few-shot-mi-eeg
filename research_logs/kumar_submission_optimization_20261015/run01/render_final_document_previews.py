#!/usr/bin/env python3
"""Render every final PDF page for actual visual inspection; no science."""

import concurrent.futures
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
LOG = Path(__file__).resolve().parent
SOURCE = ROOT / "manuscript/plos_one_submission_20261015"
DESTINATION = Path("/workspace/private_model_receipts/kumar-plos-final-preview-20261015")
DOCUMENTS = (
    ("manuscript_for_review", 27),
    ("manuscript_for_submission", 24),
    ("S1_Text", 21),
    ("S2_Text", 5),
    ("author_worksheet", 4),
    ("cover_letter_draft", 1),
)


def record(path):
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def render(document):
    name, expected = document
    source = SOURCE / f"{name}.pdf"
    output = DESTINATION / name
    output.mkdir()
    argv = ["pdftoppm", "-r", "57", "-png", str(source), str(output / "page")]
    process = subprocess.run(argv, capture_output=True, text=True, check=True)
    pages = sorted(
        output.glob("page-*.png"),
        key=lambda path: int(re.search(r"-(\d+)\.png$", path.name).group(1)),
    )
    if len(pages) != expected:
        raise ValueError(f"{name}: expected {expected} pages, got {len(pages)}")
    contacts = []
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    for start in range(0, len(pages), 9):
        selected = pages[start : start + 9]
        columns = min(3, len(selected))
        rows = (len(selected) + columns - 1) // columns
        contact = Image.new("RGB", (500 * columns, 710 * rows), "#E5E5E5")
        draw = ImageDraw.Draw(contact)
        for index, page in enumerate(selected):
            left, top = (index % columns) * 500, (index // columns) * 710
            draw.text(
                (left + 10, top + 3),
                f"{name} / page {start + index + 1}",
                fill="#111111",
                font=font,
            )
            with Image.open(page) as image:
                image = image.convert("RGB")
                image.thumbnail((480, 678))
                contact.paste(image, (left + (500 - image.width) // 2, top + 25))
        target = output / f"contact_pages_{start + 1:02d}_{start + len(selected):02d}.png"
        with target.open("xb") as handle:
            contact.save(handle, format="PNG")
        contacts.append(
            {**record(target), "page_numbers": list(range(start + 1, start + len(selected) + 1))}
        )
    return {
        "document": name,
        "source": record(source),
        "pages": len(pages),
        "render_argv": argv,
        "render_exit_code": process.returncode,
        "render_stderr": process.stderr,
        "page_images": [record(page) for page in pages],
        "contact_sheets": contacts,
    }


def main():
    started = datetime.now(timezone.utc).isoformat()
    DESTINATION.mkdir(parents=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(render, DOCUMENTS))
    if sum(item["pages"] for item in results) != 82:
        raise ValueError("all 82 pages required")
    receipt = {
        "status": "all_82_final_PDF_pages_rendered",
        "started_at_utc": started,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "dpi": 57,
        "maximum_concurrent_document_renders": 2,
        "private_preview_root": str(DESTINATION),
        "documents": results,
        "page_count": 82,
        "contact_sheet_count": sum(len(x["contact_sheets"]) for x in results),
        "scientific_execution": "none; PDF rendering only",
        "source_documents_modified": False,
    }
    with (LOG / "final_document_preview_manifest.json").open("x", encoding="utf-8") as handle:
        json.dump(receipt, handle, indent=2)
        handle.write("\n")
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "pages": receipt["page_count"],
                "contacts": receipt["contact_sheet_count"],
            }
        )
    )


if __name__ == "__main__":
    main()
