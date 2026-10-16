#!/usr/bin/env python3
"""Independently check actual exported bytes and every saved heatmap cell."""

import csv
import hashlib
import io
import json
import math
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = ROOT / "manuscript/figures/plos_submission_20261016"
checks = 0


def require(condition, message):
    global checks
    checks += 1
    if not condition:
        raise ValueError(message)


def csv_rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def image_change(old, new, name):
    require(old.size == new.size, f"same image geometry: {name}")
    box = ImageChops.difference(old.convert("RGB"), new.convert("RGB")).getbbox()
    if name.startswith("Fig1"):
        require(box is not None, "Fig1 revised legend changes actual pixels")
        require(box[1] >= math.floor(new.height * 0.85), "Fig1 changes only bottom legend region")
    else:
        require(box is None, f"unchanged actual image pixels: {name}")
    return list(box) if box else None


def revision_checks(receipt):
    old_out = ROOT / "manuscript/figures/plos_submission_20261015"
    old_log = ROOT / "research_logs/kumar_submission_figures_20261015/run01"
    old_receipt = json.loads((old_log / "figure_generation_receipt.json").read_text())
    baseline = json.loads((HERE / "prior_artifact_baseline.json").read_text())
    require(len(baseline["files"]) == 55, "55 pre-revision protected files")
    for item in baseline["files"]:
        data = (ROOT / item["path"]).read_bytes()
        require(len(data) == item["bytes"], f"prior byte length preserved: {item['path']}")
        require(hashlib.sha256(data).hexdigest() == item["sha256"], f"prior SHA preserved: {item['path']}")
    old_script = (ROOT / "scripts/render_kumar_submission_figures_20261015.py").read_text()
    new_script = (ROOT / "scripts/render_kumar_submission_figures_20261016.py").read_text()
    expected_script = old_script.replace(
        'OUT = ROOT / "manuscript/figures/plos_submission_20261015"',
        'OUT = ROOT / "manuscript/figures/plos_submission_20261016"',
    ).replace(
        'LOG = ROOT / "research_logs/kumar_submission_figures_20261015/run01"',
        'LOG = ROOT / "research_logs/kumar_submission_figures_20261016/run01"',
    ).replace('label="Participant"', 'label="Participant (method color)"')
    require(new_script == expected_script, "renderer changes exactly two output paths and Fig1 legend")
    require('values, cmap="RdBu_r", vmin=-limit, vmax=limit' in new_script, "Fig4 unchanged RdBu_r direction")
    require(receipt["source_files"] == old_receipt["source_files"], "same exact scientific sources")
    require(receipt["figures"] == old_receipt["figures"], "all numerical figure evidence unchanged")
    require(receipt["actual_font"] == old_receipt["actual_font"], "same actual font file and limits")
    require(receipt["runtime"] == old_receipt["runtime"], "same installed runtime")
    expected_geometry = json.loads(json.dumps(old_receipt["actual_export_checks"]))
    for figure in expected_geometry:
        for artist in figure["text_artists"]:
            if artist["text"] == "Participant":
                artist["text"] = "Participant (method color)"
    require(receipt["actual_export_checks"] == expected_geometry, "same recorded geometry and 8–12 pt text except legend wording")
    require(receipt["scope"] == old_receipt["scope"], "same saved-table-only scientific scope")
    require((OUT / "CAPTIONS.md").read_bytes() == (old_out / "CAPTIONS.md").read_bytes(), "caption bytes unchanged")
    stems = (
        "Fig1_target_query_participants",
        "Fig2_cpu_primary_paired_changes",
        "Fig3_csp_signed_support_halves",
        "Fig4_longitudinal_paired_changes",
    )
    participants = csv_rows(ROOT / "research_logs/kumar_frozen_query_comparison_20261015/run01/per_participant_endpoints.csv")
    endpoints = {(r["subject"], r["method"]): r for r in participants}
    summaries = {
        (r["cohort"], r["method"], r["endpoint"]): r
        for r in csv_rows(ROOT / "research_logs/kumar_frozen_query_comparison_20261015/run01/cohort_method_endpoint_summary.csv")
    }
    for row in csv_rows(OUT / f"{stems[0]}_source_data.csv"):
        if row["record_type"] == "participant":
            saved = endpoints[(row["subject"], row["method"])]
            require(math.isclose(float(row["BA"]), float(saved["target_five_session_mean_BA"]), abs_tol=1e-14), "Fig1 participant saved BA")
            require(row["cohort"] == saved["cohort"], "Fig1 participant cohort")
        else:
            saved = summaries[(row["cohort"], row["method"], "target_five_session_mean_BA")]
            for plotted, source in (("BA", "mean_BA"), ("ci95_low", "descriptive_ci95_low"), ("ci95_high", "descriptive_ci95_high")):
                require(math.isclose(float(row[plotted]), float(saved[source]), abs_tol=1e-14), f"Fig1 saved summary {plotted}")
    comparison = json.loads((ROOT / "research_logs/kumar_frozen_query_comparison_20261015/run01/comparison_receipt.json").read_text())
    primary = [r for r in comparison["preserved_original_CPU_primary_contrast"] if r["original_primary_cohort"]]
    require(len(primary) == 1 and primary[0]["cohort"] == "remaining12", "Fig2 original primary cohort")
    primary = primary[0]
    pairs = dict(zip(primary["subjects"], primary["participant_differences"], strict=True))
    for row in csv_rows(OUT / f"{stems[1]}_source_data.csv"):
        if row["record_type"] == "participant":
            require(math.isclose(float(row["difference_pp"]), 100 * pairs[row["subject"]], abs_tol=1e-12), "Fig2 saved participant paired change")
        else:
            for plotted, value in (("difference_pp", primary["mean_difference"]), ("ci95_low_pp", primary["ci95"][0]), ("ci95_high_pp", primary["ci95"][1])):
                require(math.isclose(float(row[plotted]), 100 * value, abs_tol=1e-12), f"Fig2 original saved {plotted}")
    audit = json.loads((ROOT / "research_logs/kumar_csp_signed_score_execution_20261015/run02/independent_numerical_audit_run01.json").read_text())
    halves = {
        (f"sub-{subject['subject']}", session["session"]): session["half_LDA_signed_contrasts_source_sd"]
        for subject in audit["subjects"] for session in subject["support_sessions"]
    }
    signs = {"both_positive": 0, "both_negative": 0, "opposite_signs": 0}
    for row in csv_rows(OUT / f"{stems[2]}_source_data.csv"):
        first, second = halves[(row["subject"], row["session"])]
        require(float(row["first_half_margin_source_sd"]) == first, "Fig3 first saved half")
        require(float(row["second_half_margin_source_sd"]) == second, "Fig3 second saved half")
        kind = "both_positive" if first > 0 and second > 0 else "both_negative" if first < 0 and second < 0 else "opposite_signs"
        require(row["sign_pattern"] == kind, "Fig3 saved signed pattern")
        signs[kind] += 1
    require(signs == {"both_positive": 19, "both_negative": 2, "opposite_signs": 9}, "Fig3 all 30 sign patterns")
    format_checks = []
    for stem in stems:
        csv_name = f"{stem}_source_data.csv"
        require((OUT / csv_name).read_bytes() == (old_out / csv_name).read_bytes(), f"source CSV byte equality: {stem}")
        for extension in ("png", "tif", "svg", "pdf"):
            path, old = OUT / f"{stem}.{extension}", old_out / f"{stem}.{extension}"
            require(path.is_file() and path.stat().st_size > 0, f"actual format exists: {path.name}")
            same = path.read_bytes() == old.read_bytes()
            require(same == (stem != stems[0]), f"only Fig1 changes exported bytes: {path.name}")
        with Image.open(OUT / f"{stem}.png") as png, Image.open(old_out / f"{stem}.png") as old_png:
            require(png.format == "PNG" and png.n_frames == 1, "single actual PNG")
            require(all(abs(float(x) - 600) < 0.01 for x in png.info["dpi"]), "actual PNG 600 dpi")
            if "A" in png.getbands():
                require(png.getchannel("A").getextrema() == (255, 255), "fully opaque PNG alpha")
            png_box = image_change(old_png, png, stem)
            pixels = png.size
        svg = ET.parse(OUT / f"{stem}.svg").getroot()
        width, height = float(svg.attrib["width"].removesuffix("pt")), float(svg.attrib["height"].removesuffix("pt"))
        require(abs(width - pixels[0] / 600 * 72) < 0.001 and abs(height - pixels[1] / 600 * 72) < 0.001, "actual SVG physical dimensions")
        font_sizes = []
        for group in svg.iter():
            if group.get("id", "").startswith("text_"):
                for element in group.iter():
                    match = re.search(r"scale\(([\d.]+) -[\d.]+\)", element.get("transform", ""))
                    if match:
                        font_sizes.append(100 * float(match.group(1)))
        require(bool(font_sizes) and all(8 <= size <= 12 for size in font_sizes), "actual SVG font sizes 8–12 pt")
        require("LiberationSans" in (OUT / f"{stem}.svg").read_text(), "actual SVG font glyph outlines")
        pdf_info = subprocess.run(["pdfinfo", str(OUT / f"{stem}.pdf")], capture_output=True, text=True, check=True).stdout
        require(re.search(r"Pages:\s+1\b", pdf_info) is not None, "actual single-page PDF")
        page_size = re.search(r"Page size:\s+([\d.]+) x ([\d.]+) pts", pdf_info)
        require(page_size is not None and abs(float(page_size[1]) - width) < 0.001 and abs(float(page_size[2]) - height) < 0.001, "actual PDF physical dimensions")
        pdf_fonts = subprocess.run(["pdffonts", str(OUT / f"{stem}.pdf")], capture_output=True, text=True, check=True).stdout
        font_lines = [line for line in pdf_fonts.splitlines()[2:] if line.strip()]
        require(bool(font_lines), "actual PDF font records")
        for line in font_lines:
            embedded = re.search(r"\s(yes|no)\s+(yes|no)\s+(yes|no)\s+\d+\s+\d+\s*$", line)
            require("LiberationSans" in line and embedded is not None and embedded[1] == "yes", "all actual PDF fonts embedded Liberation Sans")
        old_text = subprocess.run(["pdftotext", "-layout", str(old_out / f"{stem}.pdf"), "-"], capture_output=True, text=True, check=True).stdout
        new_text = subprocess.run(["pdftotext", "-layout", str(OUT / f"{stem}.pdf"), "-"], capture_output=True, text=True, check=True).stdout
        if stem == stems[0]:
            old_text = old_text.replace("Participant", "Participant (method color)")
        require(old_text.split() == new_text.split(), "actual PDF text changes only intended legend")
        pdf_pixels = []
        for directory in (old_out, OUT):
            process = subprocess.run(["pdftoppm", "-singlefile", "-r", "72", "-png", str(directory / f"{stem}.pdf")], capture_output=True, check=True)
            with Image.open(io.BytesIO(process.stdout)) as raster:
                pdf_pixels.append(raster.convert("RGB"))
        pdf_box = image_change(pdf_pixels[0], pdf_pixels[1], stem)
        format_checks.append({"figure": stem, "all_four_formats_verified": True, "source_CSV_byte_identical": True, "all_four_format_bytes_identical_to_old": stem != stems[0], "PNG_changed_pixel_box": png_box, "PDF_72dpi_changed_pixel_box": pdf_box, "SVG_font_size_range_pt": [min(font_sizes), max(font_sizes)]})
    return {"prior_protected_files_verified": len(baseline["files"]), "four_format_and_revision_checks": format_checks, "renderer_diff": "Only two output paths and Participant -> Participant (method color)", "Fig4_palette": "unchanged RdBu_r", "Fig4_shared_symmetric_limits_pp": receipt["figures"][stems[3]]["shared_symmetric_color_limits_pp"], "Fig4_maximum_absolute_change_pp": receipt["figures"][stems[3]]["observed_max_absolute_change_pp"], "validator_derivation": {"copied_from": str((old_log / "validate_submission_figures.py").relative_to(ROOT)), "source_sha256": hashlib.sha256((old_log / "validate_submission_figures.py").read_bytes()).hexdigest()}, "validation_runtime": {"python": sys.version.split()[0], "Pillow": Image.__version__}}


def write_report(result):
    lines = [
        "# Independent revision figure validation",
        "",
        f"Status: **PASS**, {result['checks']} checks; no failures.",
        "",
        "The renderer differs from the preserved 2026-10-15 version only in its two new output paths and the Fig1 legend wording `Participant (method color)`. Colors are assigned per method column, so the wording describes the actual encoding.",
        "",
        "All four source-data CSVs are byte-identical to the old exports. All sixteen PNG/TIFF/SVG/PDF exports were checked. Fig2–4 are byte-identical in all four formats; Fig1 image changes are confined to the bottom legend region. Actual PDF text differs only by the intended legend phrase. Fig4 remains RdBu_r with shared ±60 pp limits; its maximum absolute saved change remains 55.00000000000001 pp.",
        "",
        "Saved Fig1 participant/summary values, Fig2 paired changes and original interval, Fig3 half margins and sign patterns, and all 180 Fig4 cells were independently matched to saved sources. Geometry is unchanged. TIFFs are single-frame RGB, 600 dpi, LZW, below 10 MB, and exactly match PNG RGB pixels. PNGs are opaque at 600 dpi; actual PDF dimensions and embedded Liberation Sans fonts and SVG dimensions and 8–12 pt glyph sizes pass. Strict Arial/Times compliance is not claimed.",
        "",
        f"All {result['prior_protected_files_verified']} protected pre-revision files retained their recorded byte lengths and SHA-256 hashes. This validation reads saved tables and exported images only; it performs no training, query inference, bootstrap, test, Pod operation, installation, or new environment work.",
        "",
        "Full checks and exact changed-pixel boxes are recorded in independent_revision_validation.json. Validator was copied from the old independent validator and extended in this new log directory.",
    ]
    with (HERE / "independent_revision_validation.md").open("x", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


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
    revision = revision_checks(receipt)
    result = {
        "status": "independent_revision_validation_passed",
        **revision,
        "checks": checks,
        "failures": [],
        "actual_tiffs": tiffs,
        "actual_embedded_PDF_fonts": fonts,
        "font_limit": "Liberation Sans is actual installed family; strict Arial/Times compliance not claimed",
        "scientific_execution": "none; saved-table and image byte checks only",
    }
    with (HERE / "independent_revision_validation.json").open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    write_report(result)
    print(json.dumps({"status": result["status"], "checks": checks, "failures": []}))


if __name__ == "__main__":
    main()
