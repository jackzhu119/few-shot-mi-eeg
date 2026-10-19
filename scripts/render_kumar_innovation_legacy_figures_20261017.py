#!/usr/bin/env python3
"""Re-export the four existing figures with verified Arial, preserving their data.

The original renderer and scientific sources remain unchanged. Font binaries
are supplied locally with --font-dir and are never copied to the repository.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "scripts/render_kumar_submission_figures_20261016.py"
OUT = ROOT / "manuscript/figures/plos_innovation_20261017"
LOG = ROOT / "research_logs/kumar_plos_innovation_20261017/legacy_figure_export"


def record(path: Path) -> dict:
    return {
        "path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font-dir", type=Path, required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("kumar_original_figure_renderer", ORIGINAL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OUT, module.LOG = OUT, LOG
    OUT.mkdir(parents=True, exist_ok=True)
    LOG.mkdir(parents=True, exist_ok=True)
    for stem in module.STEMS:
        for suffix in (".png", ".tif", ".svg", ".pdf", "_source_data.csv"):
            module.require(not (OUT / (stem + suffix)).exists(), "preserve existing exports")

    font_paths = sorted(args.font_dir.resolve().glob("[Aa]rial*.TTF"))
    module.require(len(font_paths) == 4, "provide all four unmodified Arial font styles")
    for path in font_paths:
        module.font_manager.fontManager.addfont(str(path))
    module.matplotlib.rcParams.update({
        "font.family": "Arial", "font.size": 9, "axes.labelsize": 9,
        "axes.titlesize": 10, "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
        "legend.fontsize": 8, "svg.hashsalt": "kumar-plos-innovation-20261017",
        "pdf.fonttype": 42, "ps.fonttype": 42, "figure.facecolor": "white",
        "axes.facecolor": "white", "savefig.facecolor": "white",
    })
    actual_fonts = []
    original_save = module.save_figure

    def checked_save(fig, stem):
        if stem == module.STEMS[3]:
            cohort_labels = [artist for artist in fig.findobj(module.matplotlib.text.Text)
                             if artist.get_text() == "Remaining (n = 12)"]
            module.require(len(cohort_labels) == 1, "Figure 4 primary-cohort label")
            cohort_labels[0].set_text("Primary cohort (n = 12)")
        fig.canvas.draw()
        fonts = {}
        for artist in fig.findobj(module.matplotlib.text.Text):
            if not artist.get_visible() or not artist.get_text().strip():
                continue
            path = Path(module.font_manager.findfont(
                artist.get_fontproperties(), fallback_to_default=False,
            )).resolve()
            family = module.font_manager.FontProperties(fname=path).get_name()
            module.require(family == "Arial", f"unexpected font for {artist.get_text()!r}")
            module.require(path in font_paths, "font must be from the verified local package")
            fonts[str(path)] = {**record(path), "family": family}
        actual_fonts.append({"figure": stem, "fonts": list(fonts.values())})
        original_save(fig, stem)
        # Materialize the reading PNG from the verified RGB TIFF. Writing a
        # complete in-memory buffer avoids a truncated first PNG observed with
        # the runtime's direct file-handle export; no pixels are recalculated.
        with module.Image.open(OUT / f"{stem}.tif") as verified_image:
            buffer = io.BytesIO()
            verified_image.save(buffer, format="PNG", dpi=(module.DPI, module.DPI))
        (OUT / f"{stem}.png").write_bytes(buffer.getvalue())

    module.save_figure = checked_save
    started = datetime.now(timezone.utc).isoformat()
    clock = time.monotonic()
    paths = [module.COMPARISON / name for name in (
        "per_participant_endpoints.csv", "cohort_method_endpoint_summary.csv",
        "comparison_receipt.json", "per_subject_session.csv",
    )] + [module.CSP]
    source_bytes = {path: path.read_bytes() for path in paths}
    parsed = [list(csv.DictReader(io.StringIO(source_bytes[paths[i]].decode())))
              for i in (0, 1, 3)]
    participants = {(row["subject"], row["method"]): row for row in parsed[0]}
    summaries = {(row["cohort"], row["method"], row["endpoint"]): row for row in parsed[1]}
    module.require(len(participants) == len(parsed[0]) == 72, "participant rows")
    module.require(len(summaries) == len(parsed[1]) == 24, "summary rows")
    evidence = {
        module.STEMS[0]: module.figure1(participants, summaries),
        module.STEMS[1]: module.figure2(json.loads(source_bytes[paths[2]]), participants),
        module.STEMS[2]: module.figure3(json.loads(source_bytes[module.CSP])),
        module.STEMS[3]: module.figure4(parsed[2], participants),
    }
    exact_data_comparisons = []
    for stem in module.STEMS:
        old = ROOT / "manuscript/figures/plos_submission_20261016" / f"{stem}_source_data.csv"
        new = OUT / old.name
        identical = old.read_bytes() == new.read_bytes()
        module.require(identical, f"scientific source-data export changed: {stem}")
        exact_data_comparisons.append({"figure": stem, "byte_identical_to_original": identical,
                                       "sha256": record(new)["sha256"]})
    module.contact_sheet()
    module.require(all(path.read_bytes() == data for path, data in source_bytes.items()),
                   "scientific inputs changed during export")
    receipt = {
        "schema_version": 1, "status": "completed_four_existing_figures_with_exact_Arial",
        "started_at_utc": started, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": time.monotonic() - clock,
        "script": record(Path(__file__).resolve()), "original_renderer": record(ORIGINAL),
        "runtime": {"python": platform.python_version(), "numpy": module.np.__version__,
                    "matplotlib": module.matplotlib.__version__, "pillow": module.Image.__version__},
        "sources": [record(path) for path in paths],
        "scientific_sources_unchanged": True, "scientific_export_comparisons": exact_data_comparisons,
        "actual_fonts": actual_fonts, "font_size_range_pt": [8, 12],
        "strict_Arial_font_family_verified": True,
        "font_source": "https://sourceforge.net/projects/corefonts/files/the%20fonts/final/arial32.exe/download",
        "font_package_sha256": "85297a4d146e9c87ac6f74822734bdee5f4b2a722d7eaa584b7f2cbf76f478f6",
        "font_license": "Core Fonts for the Web EULA; local use; no font binaries redistributed",
        "font_license_url": "https://corefonts.sourceforge.net/eula.htm",
        "font_binaries_in_release": False, "outputs": [record(path) for path in module.FILES],
        "figure_checks": module.GEOMETRY, "scientific_summaries": evidence,
        "new_model_fits": 0, "new_predictions": 0,
        "visual_qa": "pending inspection of all four final figure images",
    }
    receipt_path = LOG / "figure_generation_receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"figures": 4, "output": str(OUT), "receipt": str(receipt_path)}, indent=2))


if __name__ == "__main__":
    main()
