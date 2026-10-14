"""Resume only identified transport failures; every controller itself stops safely."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "scripts"))
from fetch_mind2026_r2 import atomic_json, immutable_json, load_json, now

log = Path("research_logs/latest_two_sources_20261012/mind_ingestion/full_eeg_v4")
command = [sys.executable, "scripts/fetch_mind2026_r2.py", "--manifest",
           "research_logs/latest_two_sources_20261012/discovery/mind/all_files_manifest.tsv",
           "--cache", "data/public_eeg/mind2026/MIND_BIDS", "--log", str(log),
           "--representative", "research_logs/latest_two_sources_20261012/representative/mind",
           "--representative-gate",
           "research_logs/latest_two_sources_20261012/mind_ingestion/representative_gate_v3/audit.json",
           "--execute"]
transient = {"ChunkedEncodingError", "ReadTimeout", "ConnectionError", "ReadTimeoutError",
             "ConnectTimeoutError", "EndpointConnectionError"}
allowed = {"status", "files", "eeg_signals", "bytes", "completed_runs", "total_runs", "run",
           "seconds_this_run", "source_bytes", "full_get_verified", "cache_evicted",
           "failed_at_utc", "error_type", "error_code", "credential_values_logged",
           "exception_message_logged", "partial_or_signal_deleted", "runs", "events"}
errors = {}
attempt = 0
while True:
    attempt += 1
    child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             text=True, bufsize=1)
    atomic_json(log / "supervisor_status.json", {"updated_at_utc": now(), "status": "controller_running",
                                                "supervisor_pid": os.getpid(), "controller_pid": child.pid,
                                                "attempt": attempt, "credential_values_logged": False})
    for line in child.stdout:
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            print(json.dumps({k: v for k, v in value.items() if k in allowed}), flush=True)
    child.stdout.close()
    code = child.wait()
    state = load_json(log / "state.json")
    if code == 0 and state.get("status") == "completed":
        atomic_json(log / "supervisor_status.json", {"updated_at_utc": now(), "status": "completed",
                                                    "attempts": attempt, "credential_values_logged": False})
        raise SystemExit(0)
    error_type = state.get("error_type", "")
    run = state.get("current_run", "unknown")
    errors[run] = errors.get(run, 0) + 1
    retry = (code == 1 and state.get("status") == "failed_preserved_cache"
             and error_type in transient and errors[run] <= 8)
    record = {"recorded_at_utc": now(), "run": run, "controller_exit_code": code,
              "error_type": error_type, "retry": retry, "failures_for_run": errors[run],
              "source_checksum_or_R2_key_mismatch_retried": False,
              "source_or_partial_bytes_deleted": False, "credential_values_logged": False}
    immutable_json(log / "supervisor_journal" / f"{time.time_ns()}.json", record)
    print(json.dumps(record), flush=True)
    if not retry:
        atomic_json(log / "supervisor_status.json", {"updated_at_utc": now(), "status": "stopped_preserved_cache",
                                                    "attempts": attempt, "error_type": error_type,
                                                    "credential_values_logged": False})
        raise SystemExit(1)
    time.sleep(min(30, 5 * errors[run]))
