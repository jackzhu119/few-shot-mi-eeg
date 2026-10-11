#!/usr/bin/env python3
"""Confirm duplicate derivative content against cached official source manifests."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LOG = REPO / "research_logs/netbci_cohort_resume_20261010"
DATA = REPO / "data/netbci2026/nm000305/v1.0.0"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    output = LOG / "numeric_signal_identity_official_manifest_confirmation.json"
    assert not output.exists(), "Preserve earlier evidence"
    numeric_path = LOG / "numeric_signal_identity.json"
    numeric = json.loads(numeric_path.read_text())
    manifest_path = REPO / "research_logs/netbci2026_sources/manifest.json"
    official = {row["path"]: row for row in json.loads(manifest_path.read_text())}
    per_subject = {}
    subject_manifest_evidence = []
    for subject in numeric["subject_order"]:
        path = REPO / "research_logs/netbci_cohort_20261010/downloads" / subject / "download_manifest.json"
        per_subject[subject] = {row["path"]: row for row in json.loads(path.read_text())}
        subject_manifest_evidence.append({"subject": subject,
                                          "manifest_file": str(path.relative_to(REPO)),
                                          "manifest_sha256": sha(path)})
    verified = []
    for run in numeric["continuous_runs"]:
        entry = official[run["source_file"]]
        subject_entry = per_subject[run["subject"]][run["source_file"]]
        file = DATA / run["source_file"]
        assert entry["checksum_algorithm"] == subject_entry["checksum_algorithm"] == "sha256"
        assert entry["size"] == subject_entry["size"] == file.stat().st_size
        actual_sha = sha(file)
        assert actual_sha == entry["checksum"] == subject_entry["checksum"] == run["source_edf_sha256"]
        verified.append({
            "identity": f"{run['subject']}/ses-{run['session']}/run-{run['run']}",
            "subject": run["subject"], "session": run["session"], "run": run["run"],
            "source_file": run["source_file"], "actual_edf_bytes": file.stat().st_size,
            "actual_edf_sha256": actual_sha,
            "official_manifest_checksum_algorithm": entry["checksum_algorithm"],
            "official_manifest_checksum": entry["checksum"],
            "official_manifest_bytes": entry["size"],
            "per_subject_manifest_checksum": subject_entry["checksum"],
            "per_subject_manifest_bytes": subject_entry["size"],
            "official_bytes_url": entry.get("bytes_url"), "official_object_url": entry.get("url"),
            "official_manifest_match": True, "per_subject_manifest_match": True,
            "original_header": run["original_header"],
        })
    by_identity = {row["identity"]: row for row in verified}
    groups = []
    for group in numeric["continuous_duplicate_groups"]:
        members = [by_identity[identity] for identity in group["members"]]
        file_hashes = {row["actual_edf_sha256"] for row in members}
        declared_hashes = {row["official_manifest_checksum"] for row in members}
        assert file_hashes == declared_hashes
        file_subgroups = [
            {"actual_and_official_edf_sha256": digest,
             "members": [row["identity"] for row in members if row["actual_edf_sha256"] == digest],
             "member_count": sum(row["actual_edf_sha256"] == digest for row in members)}
            for digest in sorted(file_hashes)
        ]
        groups.append({
            "numeric_sha256": group["numeric_sha256"], "member_count": len(members),
            "distinct_whole_edf_sha256": len(file_hashes),
            "distinct_official_edf_checksum": len(declared_hashes),
            "official_object_url_count": len({row["official_object_url"] for row in members}),
            "exact_whole_file_subgroups": file_subgroups,
            "distinct_original_header_paths": len({row["original_header"]["original_header_file"] for row in members}),
            "distinct_verified_original_header_sha256": len({row["original_header"]["actual_original_header_sha256"] for row in members}),
            "members": members,
        })
    result = {
        "status": "all_240_edfs_match_cached_official_and_per_subject_manifests",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(), "synthetic": False,
        "numeric_audit_file": str(numeric_path.relative_to(REPO)),
        "numeric_audit_sha256": sha(numeric_path),
        "script_file": str(Path(__file__).relative_to(REPO)), "script_sha256": sha(Path(__file__)),
        "official_manifest_file": str(manifest_path.relative_to(REPO)),
        "official_manifest_sha256": sha(manifest_path),
        "official_manifest_subject_manifests": subject_manifest_evidence,
        "summary": {"actual_edf_rehashed": len(verified), "official_manifest_matches": len(verified),
                    "per_subject_manifest_matches": len(verified),
                    "duplicate_numeric_groups": len(groups),
                    "duplicate_edf_members": sum(group["member_count"] for group in groups),
                    "numeric_groups_with_repeated_official_edf_checksums": sum(
                        any(subgroup["member_count"] > 1 for subgroup in group["exact_whole_file_subgroups"])
                        for group in groups),
                    "numeric_groups_with_single_whole_file_checksum": sum(
                        group["distinct_whole_edf_sha256"] == 1 for group in groups)},
        "interpretation": "All local EDFs match the cached official declarations. For each of the six numeric duplicate groups, sub-7 ses01/02/03 share identical whole-file EDF hashes that are also explicitly repeated in the official manifest. sub-1 ses04 has the same returned numeric signal but a distinct whole-file hash, illustrating why numeric identity must be assessed separately from metadata/file identity. The observed derivative repetition is not explained by a local recovery file failing the pinned official checksum.",
        "limitations": [
            "This verification uses cached, previously fetched official manifests; no fresh upstream data were downloaded.",
            "Official manifest agreement does not identify the source or timing of the repetition.",
            "Distinct verified original BrainVision header paths/hashes and filename references do not establish distinct or identical original EEG sample contents.",
            "Original BrainVision signal and marker sequences are not compared.",
        ],
        "duplicate_groups": groups, "all_run_verifications": verified,
    }
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"output": str(output), "summary": result["summary"]}, sort_keys=True))


if __name__ == "__main__":
    main()
