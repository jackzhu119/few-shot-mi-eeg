"""Plot recorded development participant means; no fitting or score selection."""
from pathlib import Path
import hashlib
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

root = Path(__file__).resolve().parent
source = root / "measurement_receipt.json"
result = json.loads(source.read_text())
candidates = ["standardized44", "pca4", "motor6"]
fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), constrained_layout=True)
for ax, endpoint, scale, chance, ylabel in [
    (axes[0], "source_twofold_balanced_accuracy", 100, 50, "Source run probe BA (%)"),
    (axes[1], "mean_five_support_split_half_vector_cosine", 1, 0,
     "Mean support split-half cosine")
]:
    for i, candidate in enumerate(candidates):
        summary = result["participant_summaries"][candidate][endpoint]
        values = np.array([row["value"] for row in summary["participant_values"]]) * scale
        ax.scatter(i + np.linspace(-.12, .12, 6), values, s=24,
                   color="#537A9E", alpha=.8, label="Six participant means" if i == 0 else None)
        mean = summary["mean"] * scale
        lo, hi = np.asarray(summary["interval95"]) * scale
        ax.errorbar(i, mean, yerr=[[mean-lo], [hi-mean]], color="#172F48",
                    fmt="D", capsize=5, markersize=5, linewidth=1.6,
                    label="Mean and participant 95% CI" if i == 0 else None)
    ax.axhline(chance, color="#94623D", linestyle="--", linewidth=1)
    ax.set_xticks(range(3), ["All 44", "Source PCA4", "C3/Cz/C4 six"])
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=.15)
    ax.spines[["top", "right"]].set_visible(False)
axes[0].set_ylim(0, 100)
axes[1].set_ylim(-1, 1)
axes[0].legend(fontsize=7, loc="upper left")
fig.suptitle("Exploratory task-measurement diagnosis: six development IDs", fontsize=12)
for suffix in ["png", "svg", "pdf"]:
    fig.savefig(root / f"development_measurement.{suffix}", dpi=180)
plt.close(fig)
receipt = {"input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
           "executed_plot_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "participants": 6, "fit_operations": 0,
           "outputs": [{"path": str(root / f"development_measurement.{suffix}"),
                        "sha256": hashlib.sha256((root / f"development_measurement.{suffix}").read_bytes()).hexdigest()}
                       for suffix in ["png", "svg", "pdf"]]}
(root / "plot_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
