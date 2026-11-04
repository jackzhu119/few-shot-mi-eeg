"""Rebuild P1/P2 tables in a fresh directory, using saved predictions only."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
AUDIT = Path("research_logs/paper2_alignment_integrated_20261104")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    commands = []

    def run(command, label, cwd=ROOT):
        result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
        (output / (label + ".stdout")).write_text(result.stdout)
        (output / (label + ".stderr")).write_text(result.stderr)
        commands.append({"argv": command, "exit_code": result.returncode})
        if result.returncode:
            raise RuntimeError(label + " failed: " + result.stderr[-2000:])

    p1 = output / "analysis"
    run([sys.executable, str(ROOT / "scripts/analyze_paper2_alignment_integrated_20261104.py"),
         "--root", str(ROOT), "--output", str(p1), "--plan-commit",
         "13dd7646c4ce37db40504154388e76b4c6ca6595"], "p1")
    run([sys.executable, str(ROOT / "scripts/check_paper2_alignment_integrated_20261104.py"),
         "--root", str(ROOT), "--analysis", str(p1), "--output", str(output / "independent")], "p1_check")
    miniature = output / "receipt_tree"
    relative = AUDIT / "mechanisms"
    shutil.copytree(ROOT / relative, miniature / relative)
    phase = Path("research_logs/paper2_structure_revision_20261029/component_replay/input/phase/metrics.csv.gz")
    (miniature / phase).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / phase, miniature / phase)
    run([sys.executable, str(miniature / relative / "summarize_mechanisms.py")], "p2", miniature)
    comparisons = []
    for expected_dir, rebuilt_dir in ((ROOT / AUDIT / "analysis", p1),
                                      (ROOT / relative, miniature / relative)):
        for original in sorted(expected_dir.glob("*.csv")):
            rebuilt = rebuilt_dir / original.name
            before, after = original.read_bytes(), rebuilt.read_bytes()
            if before != after:
                raise ValueError("Rebuilt table differs: " + str(original.relative_to(ROOT)))
            comparisons.append({"source": str(original.relative_to(ROOT)), "bytes": len(before),
                                "sha256": hashlib.sha256(before).hexdigest(), "byte_identical": True})
    receipt = {"status": "passed", "new_fit_count": 0, "new_query_forward_count": 0,
               "EEG_or_private_models_loaded": False, "commands": commands,
               "CSV_comparisons": comparisons}
    (output / "REPRODUCTION_CHECK.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": "passed", "tables": len(comparisons), "output": str(output)}))


if __name__ == "__main__":
    main()
