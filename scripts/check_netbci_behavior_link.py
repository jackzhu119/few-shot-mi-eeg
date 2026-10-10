"""Reconcile one subject's original metadata, derivative events and run scores.

Read local metadata only. No signal download, training, invented trial outcomes,
or conversion of reported percentages into success counts is performed.
"""

from __future__ import annotations

import argparse
import ast
import configparser
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def read_tsv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def compatible_percentage(literal: str, denominator: int) -> bool:
    """Numerical compatibility only; never assert an actual score denominator."""
    places = len(literal.partition(".")[2])
    tolerance = 0.5 * 10 ** -places
    percentage = float(literal)
    return any(abs(100 * numerator / denominator - percentage) <= tolerance + 1e-9
               for numerator in range(denominator + 1))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=REPO_ROOT / "research_logs/netbci2026_behavior_link_audit.json")
    parser.add_argument("--table", type=Path,
                        default=REPO_ROOT / "research_logs/netbci2026_behavior_run_candidates.tsv")
    args = parser.parse_args()
    if args.output.exists() or args.table.exists():
        raise FileExistsError("Select new output paths to preserve previous checks")
    source_root = REPO_ROOT / "data/netbci2026/original_v2.2_metadata"
    source_receipt = json.loads((REPO_ROOT / "research_logs/netbci2026_original_metadata_receipt.json").read_text())
    for member in source_receipt["members"]:
        data = (source_root / member["relative_path"]).read_bytes()
        require(hashlib.sha256(data).hexdigest() == member["sha256"], "Original metadata checksum changed")
    derivative_root = REPO_ROOT / "data/netbci2026/nm000305/v1.0.0"
    derivative_sources = {item["path"]: item for item in json.loads((
        REPO_ROOT / "research_logs/netbci2026_sources/download_manifest.json").read_text())}
    derivative_audit = json.loads((REPO_ROOT / "research_logs/netbci2026_subject1_audit.json").read_text())
    subject = derivative_audit["summary"]["subject"]
    upstream = json.loads((REPO_ROOT / "research_logs/netbci2026_sources/snapshot/sourcedata/sourcedata_provenance.json").read_text())
    matches = [item for item in upstream["files"] if item["subject"] == subject.removeprefix("sub-")]
    original_subjects = {Path(item["file"]).parts[0] for item in matches}
    require(len(original_subjects) == 1, "Ambiguous upstream subject identity")
    original_subject = next(iter(original_subjects))
    review = json.loads((REPO_ROOT / "research_logs/netbci2026_sources/independent_review.json").read_text())
    source_event_ids = review["upstream_loader_observation"]["declared_events"]
    source_label = {str(code): name for name, code in source_event_ids.items()}
    original_rows = []
    for item in matches:
        header_path = source_root / item["file"]
        require(hashlib.sha256(header_path.read_bytes()).hexdigest() == item["sha256"],
                "Original header differs from NEMAR upstream provenance")
        match = re.search(r"_ses-([^_]+)_task-MotorImageryRest_run-([^_]+)_eeg.vhdr$", header_path.name)
        require(match is not None, "Unsupported original run identity")
        session, run = match.groups()
        prefix = header_path.name.removesuffix("_eeg.vhdr")
        events = read_tsv(header_path.parent / (prefix + "_events.tsv"))
        original_json = json.loads((header_path.parent / (prefix + "_eeg.json")).read_text())
        config = configparser.ConfigParser(interpolation=None)
        text = header_path.read_text()
        config.read_string(text[text.index("[Common Infos]"):])
        frequency = 1e6 / float(config["Common Infos"]["SamplingInterval"])
        require(frequency == original_json["SamplingFrequency"], "Original rate metadata mismatch")
        original_channels = [value.split(",")[0] for key, value in config["Channel Infos"].items()
                             if key.startswith("ch")]
        derivative_run = next(row for row in derivative_audit["runs"]
                              if row["session"] == session and row["run"] == run)
        require(original_channels == derivative_run["channel_names"], "Cross-version channel order mismatch")
        new_events_path = derivative_root / subject / f"ses-{session}/eeg" / (
            f"{subject}_ses-{session}_task-imagery_run-{run}_events.tsv")
        derivative_bytes = new_events_path.read_bytes()
        expected = derivative_sources[str(new_events_path.relative_to(derivative_root))]
        require(expected["checksum_algorithm"] == "git" and hashlib.sha1(
            b"blob " + str(len(derivative_bytes)).encode() + b"\0" + derivative_bytes
        ).hexdigest() == expected["checksum"], "Derivative events checksum changed")
        new_events = read_tsv(new_events_path)
        require(len(events) == len(new_events), "Cross-version event count mismatch")
        markers = []
        for line in (header_path.parent / (prefix + "_eeg.vmrk")).read_text().splitlines():
            if re.match(r"Mk\d+=Stimulus,", line):
                fields = line.partition("=")[2].split(",")
                code = re.fullmatch(r"S\s+(\d+)", fields[1])
                require(code is not None, "Unknown original stimulus marker")
                markers.append((int(fields[2]) - 1, code.group(1)))
        require(len(markers) == len(events), "Original marker/event count mismatch")
        for old, new, marker in zip(events, new_events, markers, strict=True):
            require(source_label[old["value"]] == new["trial_type"], "Cross-version task label mismatch")
            require(marker == (int(old["sample"]), old["value"]), "BrainVision marker/TSV mismatch")
            require(abs(float(old["onset"]) * frequency - int(old["sample"])) < 1e-6,
                    "Original seconds/sample convention unresolved")
            require(round(float(old["onset"]) * derivative_run["sampling_frequency_hz"])
                    == int(new["sample"]), "Resampled onset identity mismatch")
        original_rows.append({
            "subject": subject, "original_subject": original_subject, "session": session, "run": run,
            "eeg_trial_count": len(events), "class_counts": dict(Counter(row["trial_type"] for row in new_events)),
            "upstream_header_sha256_matches": True, "event_sequence_matches": True,
            "marker_sequence_matches": True, "original_sampling_frequency_hz": frequency,
            "derivative_sampling_frequency_hz": derivative_run["sampling_frequency_hz"],
            "onset_resampling_max_difference_s": max(abs(float(old["onset"]) - float(new["onset"]))
                                                     for old, new in zip(events, new_events)),
            "original_durations_s": sorted({float(row["duration"]) for row in events}),
            "derivative_durations_s": derivative_run["trial_durations_s"],
        })
    require(len(original_rows) == derivative_audit["summary"]["run_count"], "Unmatched derivative run")
    behavior_root = REPO_ROOT / "research_logs/netbci2026_sources/original_dataverse"
    behavior_path = behavior_root / "participants.tsv"
    behavior_receipt = json.loads((behavior_root / "behavior_receipt.json").read_text())
    require(hashlib.md5(behavior_path.read_bytes()).hexdigest() == behavior_receipt["official_checksum"]["value"],
            "Behavior source checksum changed")
    participants = [row for row in read_tsv(behavior_path) if row["participant_id"] == original_subject]
    require(len(participants) == 1, "Original behavioral subject row not unique")
    candidate_rows, literals = [], []
    for session in sorted({row["session"] for row in original_rows}):
        runs = sorted([row for row in original_rows if row["session"] == session], key=lambda row: row["run"])
        column = f"BCI-Performance-session{int(session)}"
        raw_scores = participants[0][column]
        scores = ast.literal_eval(raw_scores)
        score_literals = re.findall(r"\d+(?:\.\d+)?", raw_scores)
        require(isinstance(scores, list) and len(scores) == len(runs) == len(score_literals),
                "Behavior vector length mismatch")
        features = participants[0].get(f"ChannelFreq-Features-session{int(session)}")
        for position, (run, score, literal) in enumerate(zip(runs, scores, score_literals, strict=True), start=1):
            require(isinstance(score, (int, float)) and not isinstance(score, bool) and 0 <= score <= 100,
                    "Invalid reported behavior percentage")
            literals.append(literal)
            candidate_rows.append(dict(run, behavior_percent=float(score),
                                       behavior_vector_position=position, behavior_source_column=column,
                                       score_denominator=None, trial_level_outcomes_available=False,
                                       run_score_order_status="candidate: score vector has no explicit run IDs",
                                       percentage_compatible_with_eeg_count=compatible_percentage(literal, run["eeg_trial_count"]),
                                       online_channel_frequency_features=features))
    compatible_denominators = [n for n in range(1, 201)
                               if all(compatible_percentage(literal, n) for literal in literals)]
    receipt = {
        "status": "cross_version_EEG_run_identity_verified_behavior_run_order_conditional",
        "subject": subject, "original_subject": original_subject, "runs_verified": len(original_rows),
        "stored_trials": sum(row["eeg_trial_count"] for row in original_rows),
        "signals_compared_or_downloaded": False, "source_versions": {"nemar": "v1.0.0", "dataverse": "2.2"},
        "subject_session_run_identity_verified": True, "event_task_sequence_verified": True,
        "upstream_event_semantics": source_event_ids,
        "upstream_semantics_source": review["upstream_loader_observation"],
        "trial_count_difference_origin": "Already present in original released events/markers; not added by NEMAR conversion",
        "reason_for_original_trial_omission": "unknown: per-trial rejection logs not released in checked metadata",
        "published_behavior_rows": len(candidate_rows),
        "score_run_order_verified": False, "actual_score_denominator_verified": False,
        "runs_incompatible_with_EEG_trial_denominator": sum(not row["percentage_compatible_with_eeg_count"]
                                                           for row in candidate_rows),
        "denominator_numerical_diagnostic": {"tested_range": [1, 200],
                                             "compatible_common_denominators": compatible_denominators,
                                             "interpretation": "Compatibility is not proof; no denominator or hit count selected"},
        "runs": candidate_rows,
    }
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    columns = ["subject", "original_subject", "session", "run", "eeg_trial_count", "behavior_percent",
               "behavior_vector_position", "behavior_source_column", "score_denominator",
               "run_score_order_status", "percentage_compatible_with_eeg_count"]
    with args.table.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, columns, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(candidate_rows)
    print(json.dumps({key: value for key, value in receipt.items() if key != "runs"}, indent=2))


if __name__ == "__main__":
    main()
