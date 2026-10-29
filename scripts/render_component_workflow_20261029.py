"""Draw the four frozen decoder actions as an auditable vector workflow.

This independent review figure uses rectangles, arrows and editable text only.
It does not load EEG, models or saved predictions and performs no fitting or
inference. Dataset-specific estimators remain defined by the manuscript Methods.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, Rectangle
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
WIDTH_MM = 170
HEIGHT_MM = 126
FONT_PT = 8.0
STEM = "Decoder_component_workflow"
COL_X = (4.0, 44.0, 88.0, 129.0)
COL_W = (35.0, 39.0, 36.0, 37.0)
HEADERS = ("Fitting inputs", "Spatial representation", "Decision rule", "Later query inference")

CAPTION = (
    "Four decoder actions under the recorded source and current-session support "
    "partitions. Frozen CSP/LDA is fitted to source training alone. LDA-only keeps "
    "the source CSP fixed and refits LDA on the source/support union. Full refitting "
    "refits both CSP and LDA on that same union. EA estimates separate arithmetic "
    "covariance references from source training and current support, aligns each "
    "domain and fits CSP/LDA on the aligned union. Its later query is transformed "
    "using the already fixed support-derived target reference. Query signals and "
    "labels do not estimate references or parameters or select a method. Source "
    "training contains 40 labels in Kumar2024 and 96 in BNCI2014-001; current "
    "support contains 19 or 20 and 20 labels, respectively. The three updating "
    "pipelines share source/support identities within each dataset; frozen uses "
    "zero target labels. Dataset-specific preprocessing, coordinates and covariance "
    "estimators are specified in the Methods. This diagram depicts existing "
    "operations and introduces no new algorithm or experiment."
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def definition() -> tuple[list[dict], list[dict]]:
    rows = (
        (
            "frozen", "Frozen CSP/LDA", 99.0, 13.0,
            (
                "Source training only",
                "Fit CSP\non source training",
                "Fit LDA\non source training",
                "Apply fixed source\nCSP + LDA",
            ),
        ),
        (
            "lda_only", "LDA-only recalibration", 76.0, 13.0,
            (
                "Source for CSP;\nsource + current\nsupport for LDA",
                "Keep source CSP fixed",
                "Refit LDA on the\nsource/support union",
                "Apply source CSP\nand updated LDA",
            ),
        ),
        (
            "full", "Full CSP/LDA refitting", 53.0, 13.0,
            (
                "Source + current\nsupport",
                "Refit CSP on the\nsource/support union",
                "Refit LDA on the\nsource/support union",
                "Apply updated\nCSP + LDA",
            ),
        ),
        (
            "ea", "EA-CSP", 22.0, 21.0,
            (
                "Source + current\nsupport",
                "Separate references:\nRₛ from source;\nRₜ from current support.\nAlign each domain.",
                "Fit CSP + LDA on the\naligned source/\nsupport union",
                "Apply support-derived\n$R_t^{-1/2}$ to query;\nthen fitted CSP + LDA",
            ),
        ),
    )
    nodes: list[dict] = []
    edges: list[dict] = []
    for method_id, method, y, height, labels in rows:
        for column, label in enumerate(labels):
            nodes.append({
                "node_id": f"{method_id}_{column}",
                "method_id": method_id,
                "method_name": method,
                "stage": HEADERS[column],
                "text": label,
                "x_mm": COL_X[column],
                "y_mm": y,
                "width_mm": COL_W[column],
                "height_mm": height,
                "font_pt": FONT_PT,
            })
        for column in range(3):
            edges.append({
                "edge_id": f"{method_id}_{column}_{column + 1}",
                "source_node_id": f"{method_id}_{column}",
                "target_node_id": f"{method_id}_{column + 1}",
                "meaning": "fixed fitting/update stage to next stage; not query-based fitting",
                "start_x_mm": COL_X[column] + COL_W[column] + 0.3,
                "start_y_mm": y + height / 2,
                "end_x_mm": COL_X[column + 1] - 0.3,
                "end_y_mm": y + height / 2,
            })
    return nodes, edges


def render(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": FONT_PT,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "axes.linewidth": 0.6,
        "savefig.facecolor": "white",
        "figure.facecolor": "white",
    })
    nodes, edges = definition()
    fig = plt.figure(figsize=(WIDTH_MM / 25.4, HEIGHT_MM / 25.4))
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set(xlim=(0, WIDTH_MM), ylim=(0, HEIGHT_MM))
    ax.set_axis_off()

    for x, width, label in zip(COL_X, COL_W, HEADERS):
        ax.text(x + width / 2, 121.0, label, ha="center", va="center", fontsize=8.1)
    for node in nodes:
        x, y, width, height = (node[k] for k in ("x_mm", "y_mm", "width_mm", "height_mm"))
        ax.add_patch(Rectangle((x, y), width, height, facecolor="white",
                               edgecolor="black", linewidth=0.65))
        ax.text(x + width / 2, y + height / 2, node["text"], ha="center", va="center",
                fontsize=node["font_pt"], linespacing=1.35)
        if node["node_id"].endswith("_0"):
            ax.text(x, y + height + 2.8, node["method_name"], ha="left", va="center",
                    fontsize=8.5, fontweight="bold")
    for edge in edges:
        ax.add_patch(FancyArrowPatch(
            (edge["start_x_mm"], edge["start_y_mm"]),
            (edge["end_x_mm"], edge["end_y_mm"]),
            arrowstyle="-|>", mutation_scale=6.4, linewidth=0.65,
            facecolor="black", edgecolor="black", shrinkA=0, shrinkB=0,
        ))

    notes = (
        "Source labels: Kumar 40; BNCI 96. Current support labels: Kumar 19/20; BNCI 20.",
        "Frozen uses zero target labels; the three updates share source/support identities.",
        "Query is used for inference, not reference estimation, parameter fitting or selection.",
        "Dataset-specific preprocessing and covariance estimators are defined in Methods.",
    )
    for i, note in enumerate(notes):
        ax.text(4.0, 16.6 - i * 3.8, note, fontsize=7.6, ha="left", va="center")

    # Assert actual renderer bounds, so font changes cannot silently clip a box.
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for text in ax.texts:
        bbox = text.get_window_extent(renderer)
        outer = ax.get_window_extent(renderer)
        if bbox.x0 < outer.x0 or bbox.x1 > outer.x1 or bbox.y0 < outer.y0 or bbox.y1 > outer.y1:
            raise ValueError(f"Workflow text exceeds the canvas: {text.get_text()!r}")
    for node in nodes:
        text = next(t for t in ax.texts if t.get_text() == node["text"] and
                    abs(t.get_position()[1] - node["y_mm"] - node["height_mm"] / 2) < 1e-7)
        corners = ax.transData.transform(((node["x_mm"], node["y_mm"]),
                                          (node["x_mm"] + node["width_mm"],
                                           node["y_mm"] + node["height_mm"])))
        bbox = text.get_window_extent(renderer)
        if bbox.x0 < corners[0, 0] or bbox.x1 > corners[1, 0] or \
                bbox.y0 < corners[0, 1] or bbox.y1 > corners[1, 1]:
            raise ValueError(f"Text exceeds workflow node {node['node_id']}")

    for suffix, options in (
        ("pdf", {"metadata": {"Title": "Recorded decoder component workflow",
                               "Subject": "Existing source/support/query information access"}}),
        ("svg", {}),
        ("tiff", {"dpi": 600, "pil_kwargs": {"compression": "tiff_lzw"}}),
        ("png", {"dpi": 600}),
    ):
        fig.savefig(output / f"{STEM}.{suffix}", **options)
    with Image.open(output / f"{STEM}.tiff") as raster:
        rgb = raster.convert("RGB")
    rgb.save(output / f"{STEM}.tiff", compression="tiff_lzw", dpi=(600, 600))
    plt.close(fig)
    write_csv(output / f"{STEM}_nodes.csv", nodes)
    write_csv(output / f"{STEM}_edges.csv", edges)
    (output / f"{STEM}_caption.txt").write_text(CAPTION + "\n", encoding="utf-8")

    tiff = Image.open(output / f"{STEM}.tiff")
    svg = (output / f"{STEM}.svg").read_text(encoding="utf-8")
    if tiff.info.get("compression") != "tiff_lzw" or "<text" not in svg:
        raise ValueError("Required TIFF LZW compression or editable SVG text was not produced")
    paths = sorted(f for f in output.glob(f"{STEM}*")
                   if f.name != f"{STEM}_manifest.json")
    methods = ROOT / "manuscript/bmt_component_revision_20261029/MAIN.md"
    manifest = {
        "artifact": "Independent review workflow; no manuscript insertion or figure renumbering",
        "scientific_scope": "Existing methods only; no EEG, model, predictions, fit or inference loaded",
        "width_mm": WIDTH_MM,
        "height_mm": HEIGHT_MM,
        "minimum_font_pt": 7.6,
        "node_font_pt": FONT_PT,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "vector_primitives_only": True,
        "SVG_editable_text": True,
        "PDF_fonttype": 42,
        "font_file": font_manager.findfont("DejaVu Sans"),
        "tiff": {"pixels": list(tiff.size), "mode": tiff.mode,
                 "dpi": [float(v) for v in tiff.info["dpi"]],
                 "compression": tiff.info["compression"]},
        "software": {"python": platform.python_version(), "matplotlib": matplotlib.__version__},
        "source_script": {"path": str(Path(__file__).relative_to(ROOT)),
                          "sha256": sha256(Path(__file__))},
        "Methods_source": {"path": str(methods.relative_to(ROOT)), "sha256": sha256(methods)},
        "scientific_information": {
            "Kumar_source_labels": 40, "BNCI_source_labels": 96,
            "Kumar_target_support_labels": [19, 20], "BNCI_target_support_labels": 20,
            "query_fitting_reference_or_selection": False,
            "updating_methods_share_source_and_support": True,
            "frozen_target_labels": 0,
            "EA_query_transform": "Fixed inverse square root of current-support reference",
        },
        "outputs": [{"path": f.name, "bytes": f.stat().st_size, "sha256": sha256(f)}
                    for f in paths],
    }
    (output / f"{STEM}_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "manuscript/bmt_component_revision_20261029/workflow")
    args = parser.parse_args()
    manifest = render(args.output)
    print(json.dumps({"output": str(args.output), "node_count": manifest["node_count"],
                      "edge_count": manifest["edge_count"], "tiff": manifest["tiff"]}))


if __name__ == "__main__":
    main()
