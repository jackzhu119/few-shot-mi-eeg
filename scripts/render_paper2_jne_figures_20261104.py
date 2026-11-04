"""Apply JNE figure typography to the recorded Paper2 results without refitting."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import textwrap
import xml.etree.ElementTree as ET

import fitz
from matplotlib.text import Text
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = ROOT / "scripts/render_paper2_alignment_integrated_20261104.py"
SPEC = importlib.util.spec_from_file_location("recorded_paper2_figures", BASE_PATH)
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)
ORIGINAL_PANEL = BASE.panel
WIDTH_MM = 150


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def panel(ax, letter, title):
    title = "\n".join(textwrap.wrap(title, width=29, break_long_words=False))
    ORIGINAL_PANEL(ax, "(" + letter.lower() + ")", title)


def export(fig, stem, rows, output):
    """Keep 8pt text while changing physical width, with explicit canvas checks."""
    fig.set_size_inches(WIDTH_MM / 25.4, fig.get_figheight(), forward=True)
    if stem == "Fig1_workflow":
        workflow_wraps = {
            "Source TRAIN\nFixed earlier-session labels":
                "Source TRAIN\nFixed earlier-session\nlabels",
            "EA-CSP\nSeparate source/support whitening;\nrefit CSP + LDA":
                "EA-CSP\nSeparate source/support\nwhitening; refit CSP + LDA",
        }
        for text in fig.findobj(Text):
            if text.get_text() in workflow_wraps:
                text.set_text(workflow_wraps[text.get_text()])
    fig.canvas.draw()
    sizes = [obj.get_fontsize() for obj in fig.findobj(Text) if obj.get_text().strip()]
    if sizes and min(sizes) < 8:
        raise ValueError(f"{stem}: font below 8 pt")
    renderer = fig.canvas.get_renderer()
    outside_ticks = set()
    for ax in fig.axes:
        for axis, limits in [(ax.xaxis, ax.get_xlim()), (ax.yaxis, ax.get_ylim())]:
            low, high = sorted(limits)
            for tick in axis.get_major_ticks() + axis.get_minor_ticks():
                if not low - 1e-10 <= tick.get_loc() <= high + 1e-10:
                    outside_ticks.update((tick.label1, tick.label2))
    clipped = []
    for text in fig.findobj(Text):
        if text in outside_ticks or not text.get_visible() or not text.get_text().strip():
            continue
        bounds = text.get_window_extent(renderer)
        if (bounds.x0 < -1 or bounds.y0 < -1 or bounds.x1 > fig.bbox.x1 + 1
                or bounds.y1 > fig.bbox.y1 + 1):
            clipped.append(text.get_text())
    if clipped:
        raise ValueError(f"Text outside figure canvas in {stem}: {clipped}")
    if stem == "Fig1_workflow":
        ax = fig.axes[0]
        for patch in ax.patches:
            if not isinstance(patch, BASE.Rectangle):
                continue
            center = (patch.get_x() + patch.get_width() / 2,
                      patch.get_y() + patch.get_height() / 2)
            matching = [text for text in ax.texts if text.get_position() == center]
            if len(matching) != 1:
                raise ValueError("Workflow box does not have exactly one label")
            label, box = matching[0].get_window_extent(renderer), patch.get_window_extent(renderer)
            if (label.x0 < box.x0 + 1 or label.x1 > box.x1 - 1
                    or label.y0 < box.y0 + 1 or label.y1 > box.y1 - 1):
                raise ValueError("Workflow label exceeds its box: " + matching[0].get_text())
    for extension in ("pdf", "svg", "png"):
        options = {"dpi": 600, "facecolor": "white"}
        if extension == "pdf":
            options["metadata"] = {"Creator": "Python / Matplotlib", "CreationDate": None, "ModDate": None}
        elif extension == "svg":
            options["metadata"] = {"Creator": "Python / Matplotlib", "Date": None}
        fig.savefig(output / (stem + "." + extension), **options)
    with Image.open(output / (stem + ".png")) as image:
        image.convert("RGB").save(output / (stem + ".tiff"), compression="tiff_lzw", dpi=(600, 600))
    with (output / (stem + ".csv")).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=BASE.FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    BASE.plt.close(fig)
    with fitz.open(output / (stem + ".pdf")) as document:
        raster_count = sum(len(page.get_images()) for page in document)
    svg = ET.parse(output / (stem + ".svg"))
    svg_images = sum(node.tag.endswith("}image") for node in svg.iter())
    with Image.open(output / (stem + ".tiff")) as image:
        raster = {"pixels": list(image.size), "mode": image.mode,
                  "dpi": [float(x) for x in image.info["dpi"]],
                  "compression": image.info["compression"],
                  "bits_per_sample": list(image.tag_v2[258])}
    if raster_count or svg_images or raster["mode"] != "RGB" or raster["bits_per_sample"] != [8, 8, 8]:
        raise ValueError("JNE publication-format check failed: " + stem)
    return {"stem": stem, "width_mm": WIDTH_MM, "minimum_font_pt": min(sizes),
            "PDF_raster_image_count": raster_count, "SVG_image_element_count": svg_images,
            "visible_text_within_canvas": True, "panel_style": "(a), (b), (c), (d)",
            "tiff": raster, "plot_rows": len(rows),
            "outputs": [{"file": stem + "." + ext,
                         "bytes": (output / (stem + "." + ext)).stat().st_size,
                         "sha256": digest(output / (stem + "." + ext))}
                        for ext in ("pdf", "svg", "tiff", "png", "csv")]}


def main():
    BASE.panel = panel
    BASE.export = export
    if "--output" not in sys.argv:
        sys.argv.extend(["--output", str(ROOT / "manuscript/jne_alignment_20261104/figures")])
    BASE.main()
    output = Path(sys.argv[sys.argv.index("--output") + 1])
    manifest_path = output / "FIGURE_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["renderer"] = {"path": str(Path(__file__).relative_to(ROOT)), "sha256": digest(__file__)}
    manifest["base_renderer"] = {"path": str(BASE_PATH.relative_to(ROOT)), "sha256": digest(BASE_PATH)}
    manifest["journal"] = "Journal of Neural Engineering"
    manifest["presentation_only_adaptation"] = True
    manifest["panel_data_ids"] = "Original A-D identifiers retained in source CSVs; display labels are lowercase parenthesized"
    manifest["layout_adjustments"] = [
        "150 mm physical canvas width with 8 pt minimum text",
        "Panel titles wrapped at word boundaries",
        "Workflow source and EA node labels rewrapped without changing words",
    ]
    original = ROOT / "manuscript/bmt_alignment_integrated_20261104/figures"
    comparisons = []
    for path in sorted(output.glob("*.csv")):
        previous = original / path.name
        identical = previous.is_file() and path.read_bytes() == previous.read_bytes()
        comparisons.append({"file": path.name, "sha256": digest(path),
                            "original_path": str(previous.relative_to(ROOT)),
                            "byte_identical": identical})
    if not all(row["byte_identical"] for row in comparisons):
        raise ValueError("JNE figure source CSV differs from the frozen original")
    manifest["source_csv_invariance"] = comparisons
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
