#!/usr/bin/env python3
"""Independently check actual exported bytes and every saved heatmap cell."""

import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = ROOT / "manuscript/figures/plos_submission_20261015"
checks = 0


def require(condition, message):
    global checks
    checks += 1
    if not condition:
        raise ValueError(message)


def csv_rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main():
    receipt = json.loads((HERE / "figure_generation_receipt.json").read_text())
    for item in receipt["source_files"] + receipt["outputs"] + [receipt["script"]]:
        data = (ROOT / item["path"]).read_bytes()
        require(len(data) == item["bytes"], f"byte length: {item['path']}")
        require(hashlib.sha256(data).hexdigest() == item["sha256"], f"SHA: {item['path']}")
    source = csv_rows(
        ROOT / "research_logs/kumar_frozen_query_comparison_20261015/run01/per_subject_session.csv"
    )
    mapping = {(r["subject"], r["method"], r["session"]): r for r in source}
    require(len(source) == len(mapping) == 432, "complete saved source")
    heatmap = csv_rows(OUT / "Fig4_longitudinal_paired_changes_source_data.csv")
    identities = [(r["contrast"], r["subject"], r["session"]) for r in heatmap]
    require(len(heatmap) == len(set(identities)) == 180, "180 unique heatmap cells")
    expected_subjects = [
        f"sub-{n}" for n in (1, 4, 7, 10, 13, 16, 2, 3, 5, 6, 8, 9, 11, 12, 14, 15, 17, 18)
    ]
    for contrast, reference in (
        ("full_refit_minus_frozen", "source_only"),
        ("full_refit_minus_LDA_only", "frozen_csp_lda_recalibration"),
    ):
        rows = [r for r in heatmap if r["contrast"] == contrast]
        expected = [
            (subject, f"ses-{session}") for subject in expected_subjects for session in range(1, 6)
        ]
        require(
            [(r["subject"], r["session"]) for r in rows] == expected,
            "identity order: no effect sorting",
        )
        for row in rows:
            full = mapping[(row["subject"], "refit_csp_lda", row["session"])]
            comparison = mapping[(row["subject"], reference, row["session"])]
            require(
                int(full["n_unique_query_trials"])
                == int(comparison["n_unique_query_trials"])
                == int(row["n_unique_query_trials"]),
                "same saved query counts",
            )
            require(
                float(full["balanced_accuracy"]) == float(row["full_refit_BA"]),
                "exact full saved value",
            )
            require(
                float(comparison["balanced_accuracy"]) == float(row["comparator_BA"]),
                "exact comparator saved value",
            )
            expected_gain = 100 * (
                float(full["balanced_accuracy"]) - float(comparison["balanced_accuracy"])
            )
            require(
                math.isclose(expected_gain, float(row["difference_pp"]), rel_tol=0, abs_tol=1e-12),
                "cell difference",
            )
    fonts = []
    tiffs = []
    for tiff in sorted(OUT.glob("*.tif")):
        with Image.open(tiff) as image:
            dpi = [float(x) for x in image.info["dpi"]]
            require(dpi == [600.0, 600.0], "actual TIFF DPI")
            require(image.mode == "RGB", "RGB/noalpha")
            require(image.info["compression"] == "tiff_lzw", "LZW")
            require(image.n_frames == 1, "flattened single image")
            require(6.68 <= image.width / dpi[0] * 2.54 <= 19.05001, "width")
            require(image.height / dpi[1] * 2.54 <= 22.23, "height")
            require(tiff.stat().st_size < 10_000_000, "10MB")
            with Image.open(tiff.with_suffix(".png")) as png:
                require(image.size == png.size, "PNG/TIFF pixel dimensions")
                require(
                    image.tobytes() == png.convert("RGB").tobytes(), "TIFF exact RGB PNG pixels"
                )
            tiffs.append(
                {
                    "name": tiff.name,
                    "bytes": tiff.stat().st_size,
                    "pixels": list(image.size),
                    "dpi": dpi,
                }
            )
        process = subprocess.run(
            ["pdffonts", str(tiff.with_suffix(".pdf"))], capture_output=True, text=True, check=True
        )
        require("LiberationSans" in process.stdout, "actual embedded font")
        require(" yes " in process.stdout, "embedded font reported")
        fonts.append({"figure": tiff.stem, "pdffonts": process.stdout})
    require(len(tiffs) == 4, "four TIFF exports")
    require(
        len(csv_rows(OUT / "Fig1_target_query_participants_source_data.csv")) == 80,
        "72 participant +8 cohort points",
    )
    require(
        len(csv_rows(OUT / "Fig2_cpu_primary_paired_changes_source_data.csv")) == 13,
        "12 participants +1 original mean",
    )
    require(
        len(csv_rows(OUT / "Fig3_csp_signed_support_halves_source_data.csv")) == 30,
        "30 support sessions /60 halves",
    )
    require(receipt["source_bytes_unchanged_after_render"] is True, "source preservation")
    result = {
        "status": "independent_export_and_saved_cell_validation_passed",
        "checks": checks,
        "failures": [],
        "actual_tiffs": tiffs,
        "actual_embedded_PDF_fonts": fonts,
        "font_limit": "Liberation Sans is actual installed family; strict Arial/Times compliance not claimed",
        "scientific_execution": "none; saved-table and image byte checks only",
    }
    with (HERE / "independent_export_validation.json").open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print(json.dumps({"status": result["status"], "checks": checks, "failures": []}))


if __name__ == "__main__":
    main()
