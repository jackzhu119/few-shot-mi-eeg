"""A zero-write source rate limit cannot authorize retrying integrity failures."""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("mind_supervisor_policy", ROOT / "scripts/supervise_mind_recovery.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_identified_current_zero_write_429_allows_transport_retry():
    assert module.is_known_rate_limit("ValueError", {"reason": "source_http_range_response_mismatch", "http_status": 429, "received_bytes": 0})


@pytest.mark.parametrize("error,evidence", [
    ("ValueError", {}),
    ("ValueError", {"reason": "source_checksum_mismatch", "http_status": 429, "received_bytes": 0}),
    ("ValueError", {"reason": "source_http_range_response_mismatch", "http_status": 206, "received_bytes": 0}),
    ("ValueError", {"reason": "source_http_range_response_mismatch", "http_status": 429, "received_bytes": 1}),
    ("ClientError", {"reason": "source_http_range_response_mismatch", "http_status": 429, "received_bytes": 0}),
    ("ValueError", None),
])
def test_unidentified_mapping_digest_written_body_or_R2_error_stops(error, evidence):
    assert not module.is_known_rate_limit(error, evidence)
