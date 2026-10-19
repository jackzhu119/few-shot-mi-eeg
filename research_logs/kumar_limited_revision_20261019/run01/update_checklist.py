"""Update only the existing checklist answers from the fixed submission version."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import fitz

BASE = "19a5909fd76d96be9316559602010932ccec81a8"
REL = "manuscript/plos_one_innovation_20261017/Human_Participants_Checklist.pdf"
ORIGINAL_SHA = "000de16bb9203f35a43ec5f8bcb24c90dbb60f5bf27779faa0a38ffab2aa3650"
ANSWER = (
    "Secondary analysis of public Kumar2024 EEG (NEMAR nm000177/v1.0.5), exempt "
    "from additional ethical review under Article 32(1) of China's 2023 Measures "
    "for Ethical Review of Life Science and Medical Research Involving Human "
    "Participants. The analysis used lawfully obtained public data, caused no "
    "harm, and involved no sensitive personal information or commercial interests. "
    "Original data collection: University of Texas at Austin protocol 2020-03-0073 "
    "and written informed consent."
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--line-range", required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    evidence = args.evidence_dir.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    original = subprocess.check_output(["git", "show", f"{BASE}:{REL}"], cwd=root)
    assert hashlib.sha256(original).hexdigest() == ORIGINAL_SHA
    document = fitz.open(stream=original, filetype="pdf")
    changed = []
    for page in document:
        for widget in page.widgets():
            if widget.field_name == "all countries where data collection took place":
                words = ANSWER.split()
                lines: list[str] = []
                line = ""
                for word in words:
                    candidate = (line + " " + word).strip()
                    if fitz.get_text_length(candidate, fontname="helv", fontsize=9.3) > widget.rect.width - 5:
                        lines.append(line)
                        line = word
                    else:
                        line = candidate
                lines.append(line)
                assert len(lines) * 9.3 * 1.15 < widget.rect.height
                widget.field_value = "\n".join(lines)
                widget.update()
                changed.append({"field": widget.field_name, "value": widget.field_value})
            elif widget.field_name == "Please state the line numbers in the Methods where this is reported 1_2":
                assert fitz.get_text_length(args.line_range, fontname="helv", fontsize=11) < widget.rect.width
                widget.field_value = args.line_range
                widget.update()
                changed.append({"field": widget.field_name, "value": widget.field_value})
    assert len(changed) == 2
    staged = evidence / "Human_Participants_Checklist.pdf"
    document.save(staged, garbage=4, deflate=True)
    document.close()
    checked = fitz.open(staged)
    fields = {w.field_name: w.field_value for p in checked for w in p.widgets()}
    assert len(fields) == 9
    assert fields["NA"] == "X" and fields["Uploaded"] == ""
    assert fields["Completed"] == "X"  # Existing Q2 N/A mark: names differ from the visible labels.
    assert fields["Please state the line numbers in the Methods where this is reported 2_2"] == "X"
    assert fields["Completed_2"] == ""
    text = "\n".join(p.get_text() for p in checked)
    assert "research administration" not in text and "confirmed exemption" not in text
    assert "Article 32(1)" in text and "2020-03-0073" in text
    for index, page in enumerate(checked, start=1):
        page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).save(evidence / f"checklist_page{index}.png")
    (root / REL).write_bytes(staged.read_bytes())
    receipt = {
        "baseline_commit": BASE,
        "original_sha256": ORIGINAL_SHA,
        "final_sha256": hashlib.sha256(staged.read_bytes()).hexdigest(),
        "final_bytes": staged.stat().st_size,
        "changed_fields": changed,
        "original_widget_count_preserved": len(fields),
        "all_other_field_values_preserved": True,
        "Q1": "N/A approval document; regulatory exemption explanation",
        "Q2": "N/A prospective recruitment",
        "Q3": f"Completed; actual final manuscript lines {args.line_range}",
        "visual_review": "pending inspection of the two newly rendered checklist pages",
    }
    (evidence / "checklist_update_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
