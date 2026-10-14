import importlib.util
from pathlib import Path

import numpy as np
import pytest

spec = importlib.util.spec_from_file_location(
    "support_reliability", Path(__file__).parents[1] /
    "scripts/analyze_kumar_support_reliability.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_reversed_direction_and_conditional_interval():
    labels = np.repeat([0, 1], 10)
    source = np.column_stack([labels * 2 - 1, np.zeros(20)])
    result = module.measure(source, labels, -source, labels)
    assert result["source_support_direction_cosine"] == -1
    assert result["support_split_half_direction_cosine"] == 1
    assert result["conditional_bootstrap_cosine_interval"] == [-1, -1]


def test_zero_direction_retained_and_insufficient_class_rejected():
    labels = np.repeat([0, 1], 10)
    zero = np.zeros((20, 2))
    result = module.measure(zero, labels, zero, labels)
    assert result["source_support_direction_cosine"] is None
    assert result["bootstrap_nonzero_directions"] == 0
    with pytest.raises(ValueError, match="Insufficient"):
        module.measure(zero, labels, zero[:12], labels[:12])
