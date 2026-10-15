"""Validate a documentary snapshot using saved metadata and file hashes only."""

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/workspace/few-shot-mi-eeg")
LOG = ROOT / "research_logs/kumar_project_status_sync_20261015/run01"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    checks = []

    def require(name, passed):
        checks.append({"check": name, "passed": bool(passed)})

    inventory = json.loads((LOG / "pending_originals_inventory.json").read_text())
    git_files = []
    private_files = []
    for item in inventory["files"]:
        path = ROOT / item["path"]
        require("original_length:" + item["path"], path.stat().st_size == item["bytes"])
        require("original_sha256:" + item["path"], sha(path) == item["sha256"])
        if item["git_candidate"]:
            require("json_candidate_only:" + item["path"], path.suffix == ".json")
            json.loads(path.read_text())
            git_files.append(item["path"])
        else:
            require(
                "private_array_ignored:" + item["path"],
                subprocess.run(
                    ["git", "check-ignore", "-q", "--", item["path"]], cwd=ROOT, check=False
                ).returncode
                == 0,
            )
            private_files.append(item["path"])
    git_files.extend(
        ["scripts/analyze_kumar_csp_reliability.py", "tests/test_kumar_csp_reliability.py"]
    )
    require("fourteen_json_plus_two_source_test", len(git_files) == 16)
    require("six_private_arrays", len(private_files) == 6)
    require(
        "no_query_or_validation_in_preparation",
        inventory["metadata_scope"]["query_trial_count"]
        == inventory["metadata_scope"]["validation_trial_count"]
        == 0,
    )
    protected = json.loads((LOG / "preservation_before.json").read_text())["protected_files"]
    for item in protected:
        path = ROOT / item["path"]
        require(
            "protected:" + item["path"],
            path.stat().st_size == item["bytes"] and sha(path) == item["sha256"],
        )
    docs = [
        "CURRENT_PROJECT_STATUS.md",
        "README.md",
        "manuscript/README.md",
        str((LOG / "README.md").relative_to(ROOT)),
    ]
    links = 0
    for name in docs:
        path = ROOT / name
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text()):
            if target.startswith(("https://", "http://", "#", "mailto:")):
                continue
            links += 1
            require(
                "link:" + name + ":" + target,
                (path.parent / target.split("#")[0]).resolve().exists(),
            )
    handoff = (ROOT / "NEXT_STAGE_HANDOFF.md").read_text()
    require(
        "current_handoff_banner_before_history",
        handoff.index("最新有效状态") < handoff.index("05:58:40"),
    )
    require("current_handoff_resolves_status", (ROOT / "CURRENT_PROJECT_STATUS.md").exists())
    ledger_path = (
        ROOT / "research_logs/kumar_remaining36_acceptance_20261015/run01/accepted_jobs_all54.json"
    )
    ledger = json.loads(ledger_path.read_text())
    require(
        "accepted54_identity_count",
        len(ledger["accepted_jobs"]) == 54
        and len({j["job_id"] for j in ledger["accepted_jobs"]}) == 54,
    )
    require(
        "accepted54_hash_unchanged",
        sha(ledger_path) == "013668c8d1b1c5d6061f3701d495cf7770743a1c6fda8678f5db7ffd50992670",
    )
    query = json.loads(
        (
            ROOT
            / "research_logs/kumar_frozen_query_acceptance_20261015/run01/accepted_evaluation.json"
        ).read_text()
    )
    require(
        "separate_query54_acceptance",
        query["query_evaluation_accepted_count"] == 54
        and query["source_accepted_count_unchanged"] == 54
        and not query["new_execution_released"],
    )
    receipt_paths = [
        "research_logs/kumar_manuscript_completion_20261015/run01/r2_full_get_receipt.json",
        "research_logs/kumar_author_confirmation_20261015/run01/r2_full_get_receipt.json",
    ]
    receipt_expected = [
        (131, 9622032, "240804c950587cfdabd408a2235b0971f88c8a6aa0c1e3df94928ddd9ce2ce37"),
        (111, 9233753, "d4ecca0afafdfbc9405c14302fdea1e85500f73006564f99777bee9fa4f97d18"),
    ]
    for name, (count, size, digest) in zip(receipt_paths, receipt_expected):
        path = ROOT / name
        receipt = json.loads(path.read_text())
        require(
            "receipt:" + name,
            sha(path) == digest
            and receipt["status"] == "completed"
            and receipt["totals"]["full_get_sha256_verified_files"] == count
            and receipt["totals"]["readback_bytes"] == size
            and receipt["totals"]["failed_files"] == 0,
        )
    candidate_paths = [ROOT / p for p in git_files + docs] + [ROOT / "NEXT_STAGE_HANDOFF.md"]
    patterns = [
        r"AKIA[0-9A-Z]{16}",
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        r"(?i)X-Amz-Signature=[0-9a-f]{32,}",
        r"(?i)(?:aws_secret_access_key|api_key|access_token)\s*[:=]\s*[\"\x27][A-Za-z0-9/+=._-]{20,}",
    ]
    findings = []
    for path in candidate_paths:
        text = path.read_text()
        for i, pattern in enumerate(patterns):
            if re.search(pattern, text):
                findings.append({"path": str(path.relative_to(ROOT)), "pattern_index": i})
    require("no_literal_credential_or_signed_url_pattern_in_candidates", not findings)
    status = "passed" if all(x["passed"] for x in checks) else "failed"
    result = {
        "status": status,
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "script_sha256": sha(Path(__file__)),
        "checks": len(checks),
        "failed_checks": [x for x in checks if not x["passed"]],
        "protected_files_unchanged": len(protected),
        "current_links_checked": links,
        "original_archival_Git_candidates": git_files,
        "private_arrays_excluded_from_Git": private_files,
        "literal_credential_scan_findings": findings,
        "raw_EEG_array_decodes_model_forwards_or_fits": 0,
        "Pod_or_submission_actions": 0,
        "limits": [
            "Pattern scan does not claim a universal secret detector.",
            "All archived source bytes remain historical; synthetic tests do not repair their known broad-except defect.",
        ],
        "checks_detail": checks,
    }
    (LOG / "status_validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: v
                for k, v in result.items()
                if k
                not in [
                    "checks_detail",
                    "original_archival_Git_candidates",
                    "private_arrays_excluded_from_Git",
                ]
            },
            indent=2,
        )
    )
    if status != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
