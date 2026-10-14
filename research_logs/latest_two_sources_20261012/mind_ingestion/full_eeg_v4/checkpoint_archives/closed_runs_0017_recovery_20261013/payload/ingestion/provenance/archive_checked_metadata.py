"""Freeze all already officially-checked small MIND source files in immutable R2."""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "scripts"))
from fetch_mind2026_r2 import immutable_json, load_json, now, safe_error_code, upload_source
from sync_research_r2 import build_client

log = Path("research_logs/latest_two_sources_20261012/mind_ingestion/full_eeg_v4")
cache = Path("data/public_eeg/mind2026/MIND_BIDS")
sources = [load_json(p) for p in (log / "source_receipts").rglob("*.json")]
sources = sorted((s for s in sources if not s["relative_path"].endswith(".eeg")),
                 key=lambda s: s["relative_path"])
assert len(sources) == 605
assert all(s["official_size_and_md5_pass"] for s in sources)
try:
    client, bucket, sdk = build_client()
    receipts = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for result in pool.map(lambda s: upload_source(client, bucket, cache, log, s), sources):
            receipts.append(result)
            if len(receipts) % 100 == 0 or len(receipts) == len(sources):
                print(json.dumps({"checked_metadata_full_get_closed": len(receipts),
                                  "planned_metadata": len(sources)}), flush=True)
    immutable_json(log / "checked_metadata_r2_closed.json",
                   {"closed_at_utc": now(), "files": receipts, "boto3_version": sdk,
                    "status": "completed", "full_get_sha256_verified_files": len(receipts),
                    "credential_values_logged": False})
except Exception as error:
    failure = {"failed_at_utc": now(), "error_type": type(error).__name__,
               "error_code": safe_error_code(error), "credential_values_logged": False}
    print(json.dumps(failure), flush=True)
    raise SystemExit(1)
