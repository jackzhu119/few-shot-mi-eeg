"""Freeze explicit closed research files before immutable R2 transfer."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def freeze(selection: Path, manifest_output: Path) -> dict:
    specification_bytes = selection.read_bytes()
    specification = json.loads(specification_bytes)
    repository = Path(specification["repository"]).resolve(strict=True)
    destination = Path(specification["destination"])
    if destination.exists() or manifest_output.exists():
        raise FileExistsError("Preserve prior snapshots and choose a new destination")
    destination.mkdir(parents=True)
    entries = []
    for relative in sorted(set(specification["paths"])):
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or str(path) != relative:
            raise ValueError("Canonical repository-relative source paths required")
        source = repository / path
        if source.resolve(strict=True) != source or not source.is_file():
            raise ValueError("Only reviewed regular files without symlinks may be frozen")
        content = source.read_bytes()
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        if source.read_bytes() != content or target.read_bytes() != content:
            raise ValueError(f"Source or staged bytes changed during snapshot: {relative}")
        entries.append({"original_repository_path": relative,
                        "relative_snapshot_path": relative,
                        "bytes": len(content), "sha256": sha256(content)})
    if selection.read_bytes() != specification_bytes:
        raise ValueError("Selection changed during snapshot")
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repository,
                            check=True, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=repository,
                           check=True, capture_output=True, text=True).stdout != ""
    manifest = {
        "schema_version": 1,
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": specification["scope"],
        "repository": str(repository),
        "source_git_commit": commit,
        "contains_uncommitted_research_evidence": dirty,
        "selection_sha256": sha256(specification_bytes),
        "snapshot_complete": True,
        "all_source_and_staged_bytes_unchanged_during_copy": True,
        "source_qualification_distinct_from_R2_transfer": True,
        "scientific_acceptance_preserved_without_reinterpretation": True,
        "credential_values_logged": False,
        "source_files": len(entries),
        "source_bytes": sum(entry["bytes"] for entry in entries),
        "files": entries,
    }
    content = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    (destination / "snapshot_manifest.json").write_bytes(content)
    manifest_output.parent.mkdir(parents=True, exist_ok=True)
    manifest_output.write_bytes(content)
    return {"destination": str(destination), "snapshot_manifest_sha256": sha256(content),
            "planned_files": len(entries) + 1,
            "planned_bytes": manifest["source_bytes"] + len(content)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--manifest-output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(freeze(args.selection, args.manifest_output)))


if __name__ == "__main__":
    main()
