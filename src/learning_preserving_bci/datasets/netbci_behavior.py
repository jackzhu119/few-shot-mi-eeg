"""NETBCI published percentages at their verified participant/session grain.

Vector positions are preserved, but never assigned EEG run or trial identities.
The unweighted mean of published run percentages is not a pooled hit rate.
"""
from __future__ import annotations

import ast
import csv
from pathlib import Path

import numpy as np


def read_behavior_sessions(path: str | Path, session_columns: dict[str, str],
                           expected_vector_length: int) -> tuple[list[dict], list[dict]]:
    """Validate explicit source fields; return session and source-position tables."""
    sessions, positions, subjects = [], [], set()
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        for source_row, row in enumerate(csv.DictReader(stream, delimiter="\t"), start=1):
            subject = row["participant_id"]
            if not subject or subject in subjects:
                raise ValueError("Missing or duplicate participant_id")
            subjects.add(subject)
            previous = baseline = None
            for session, column in session_columns.items():
                literal = row[column]
                try:
                    vector = ast.literal_eval(literal)
                except (ValueError, SyntaxError) as exc:
                    raise ValueError(f"Invalid score literal: {subject}/{column}") from exc
                if (not isinstance(vector, list) or len(vector) != expected_vector_length
                        or any(isinstance(x, bool) or not isinstance(x, (int, float))
                               for x in vector)):
                    raise ValueError("Scores must be an explicitly complete numeric list")
                values = np.asarray(vector, dtype=float)
                if not np.isfinite(values).all() or ((values < 0) | (values > 100)).any():
                    raise ValueError("Published percentages must be finite and within 0–100")
                mean = float(values.mean())
                if baseline is None:
                    baseline = mean
                sessions.append({
                    "original_subject": subject, "session": session,
                    "source_row": source_row, "source_column": column,
                    "source_literal": literal, "n_reported_run_scores": len(values),
                    "mean_run_hit_percent": mean, "median_run_hit_percent": float(np.median(values)),
                    "sd_between_reported_run_percent": float(values.std(ddof=1)),
                    "min_run_hit_percent": float(values.min()),
                    "max_run_hit_percent": float(values.max()),
                    "delta_from_first_session_pp": mean - baseline,
                    "delta_from_previous_session_pp": "unavailable" if previous is None else mean-previous,
                    "EEG_run_order": "unresolved", "score_denominator": "unresolved",
                    "trial_outcome": "unresolved",
                    "online_feature_source_literal": row.get(f"ChannelFreq-Features-session{int(session)}", "unavailable"),
                    "anxiety_source_literal": row.get(f"STAI_YA-session{int(session)}", "unavailable"),
                })
                for position, score in enumerate(values, start=1):
                    positions.append({
                        "original_subject": subject, "session": session,
                        "source_row": source_row, "source_column": column,
                        "source_vector_position": position, "published_hit_percent": float(score),
                        "EEG_run": "unresolved", "EEG_trial": "unresolved",
                        "score_denominator": "unresolved",
                    })
                previous = mean
    if not sessions:
        raise ValueError("Empty participant table")
    return sessions, positions


def join_verified_sessions(behavior: list[dict], eeg: list[dict],
                           subject_map: dict[str, str]) -> list[dict]:
    """One-to-one session join; reject run/trial broadcasting or incomplete keys."""
    behavior_index = {}
    for row in behavior:
        key = row["original_subject"], row["session"]
        if key in behavior_index:
            raise ValueError("Duplicate behavior session key; do not broadcast run scores")
        behavior_index[key] = row
    result, seen = [], set()
    for row in eeg:
        if "trial_id" in row or "run" in row:
            raise ValueError("Session behavior must not be broadcast onto EEG runs/trials")
        key = row["subject"], row["session"]
        if key in seen:
            raise ValueError("Duplicate EEG session key")
        seen.add(key)
        if row["subject"] not in subject_map:
            raise ValueError("Subject identity needs an explicitly verified mapping")
        source_key = subject_map[row["subject"]], row["session"]
        if source_key not in behavior_index:
            raise ValueError("EEG session has no matching source behavior field")
        result.append({**behavior_index[source_key], **row,
                       "join_grain": "verified_participant_session_only"})
    return result
