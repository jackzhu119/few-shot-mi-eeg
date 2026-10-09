"""Exercise MNE/MOABB with its synthetic provider without EEG downloads."""

from __future__ import annotations

import json

import mne
import numpy as np
from moabb.datasets import FakeDataset
from moabb.paradigms import MotorImagery


def main() -> None:
    mne.set_log_level("ERROR")
    fixture = FakeDataset(
        event_list=("left_hand", "right_hand"),
        n_subjects=1,
        n_sessions=2,
        n_runs=1,
        n_events=10,
        duration=20,
        seed=42,
        channels=("C3", "Cz", "C4"),
    )
    X, y, metadata = MotorImagery(n_classes=2, fmin=8, fmax=30).get_data(
        dataset=fixture,
        subjects=[1],
    )
    assert X.ndim == 3 and X.shape[1] == 3
    assert len(X) == len(y) == len(metadata) > 0
    assert np.isfinite(X).all() and len(set(y)) == 2
    assert metadata.subject.nunique() == 1 and metadata.session.nunique() == 2
    print(
        json.dumps(
            {
                "status": "MNE_MOABB_synthetic_provider_passed",
                "shape": list(X.shape),
                "labels": sorted(set(y)),
                "sessions": sorted(metadata.session.unique()),
                "synthetic": True,
                "public_eeg_downloaded": False,
            }
        )
    )


if __name__ == "__main__":
    main()
