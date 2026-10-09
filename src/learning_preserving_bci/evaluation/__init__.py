"""Subject-aware offline evaluation and subject-level statistical inference."""

from .fixed_decoder import evaluate_fixed_decoder
from .splits import TrialSplit, leave_one_subject_out, within_subject_session_split
from .statistics import bootstrap_subject_mean, paired_subject_statistics

__all__ = [
    "TrialSplit",
    "leave_one_subject_out",
    "within_subject_session_split",
    "evaluate_fixed_decoder",
    "bootstrap_subject_mean",
    "paired_subject_statistics",
]
