"""Independent no-fit loss replay and mutation guard, using CPU synthetic tensors."""

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from replay_kumar_first_fit import independent_eval  # noqa: E402


def fixture_model(mutate=False):
    class Fixed(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.register_buffer("marker", torch.zeros(1))

        def forward(self, x):
            if mutate:
                self.marker.add_(1)
            return x[:, :, 0]

    return SimpleNamespace(
        model_=Fixed(),
        device="cpu",
        channel_mean_=np.zeros((1, 2, 1), dtype=np.float32),
        channel_scale_=np.ones((1, 2, 1), dtype=np.float32),
        classes_=np.array([0, 1], dtype=np.int64),
    )


def test_independent_logsumexp_matches_analytic_without_fitting():
    x = np.tile(np.array([[[0.0], [1.0]]], dtype=np.float32), (20, 1, 1))
    y = np.ones(20, dtype=np.int64)
    model = fixture_model()
    logits, losses, loss = independent_eval(model, x, y, 16)
    assert logits.shape == (20, 2)
    np.testing.assert_allclose(losses, np.log1p(np.exp(-1)), rtol=0, atol=1e-15)
    assert abs(loss - losses.mean()) < 1e-7
    assert not model.model_.training
    assert all(p.grad is None for p in model.model_.parameters())


def test_mutated_state_blocks_replay():
    with pytest.raises(ValueError, match="state changed"):
        independent_eval(
            fixture_model(mutate=True),
            np.zeros((20, 2, 1), dtype=np.float32),
            np.zeros(20, dtype=np.int64),
            16,
        )
