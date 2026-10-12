"""Archive an exact pushed Git checkpoint without live worktree files."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tarfile
from datetime import datetime, timezone
from pathlib import Path


def git(repository: Path, *arguments: str) -> bytes:
    return subprocess.run(["git", *arguments], cwd=repository, check=True,
                          capture_output=True).stdout


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def archive(repository: Path, destination: Path, commit: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("An exact full Git commit is required")
    if git(repository, "rev-parse", "HEAD").decode().strip() != commit:
        raise ValueError("HEAD must equal the reviewed scientific checkpoint")
    remote_ref = "refs/remotes/origin/research/learning-preserving-bci"
    if git(repository, "rev-parse", remote_ref).decode().strip() != commit:
        raise ValueError("The selected research checkpoint must already be pushed")
    if destination.exists():
        raise FileExistsError("Preserve prior checkpoint snapshots")
    destination.mkdir(parents=True)
    short = commit[:7]
    source_archive = destination / f"research_source_{short}.tar.gz"
    history_bundle = destination / f"research_history_{short}.bundle"
    git(repository, "archive", "--format=tar.gz", "--prefix=few-shot-mi-eeg/",
        f"--output={source_archive}", commit)
    git(repository, "bundle", "create", str(history_bundle), "--all")
    git(repository, "bundle", "verify", str(history_bundle))
    bundle_heads = git(repository, "bundle", "list-heads", str(history_bundle)).decode()
    if f"{commit} refs/heads/research/learning-preserving-bci\n" not in bundle_heads:
        raise ValueError("Bundle does not advertise the selected research checkpoint")
    expected = {}
    for record in git(repository, "ls-tree", "-r", "-z", commit).split(b"\0"):
        if not record:
            continue
        metadata, path = record.split(b"\t", 1)
        mode, kind, object_id = metadata.decode().split()
        if kind != "blob":
            raise ValueError("Checkpoint contains a non-blob Git tree entry")
        expected[path.decode()] = {"mode": mode, "git_blob_sha1": object_id}
    tracked_files = []
    with tarfile.open(source_archive, "r:gz") as stream:
        if stream.pax_headers.get("comment") != commit:
            raise ValueError("Git archive commit header does not match checkpoint")
        for member in stream:
            if member.isdir():
                continue
            prefix = "few-shot-mi-eeg/"
            if not member.name.startswith(prefix):
                raise ValueError("Archive member has an unexpected prefix")
            relative = member.name[len(prefix):]
            entry = expected.pop(relative)
            if member.issym():
                content = member.linkname.encode()
                if entry["mode"] != "120000":
                    raise ValueError("Unexpected archive symlink mode")
            elif member.isfile():
                file_stream = stream.extractfile(member)
                if file_stream is None:
                    raise ValueError("Archive file has no content")
                content = file_stream.read()
            else:
                raise ValueError("Unsupported archive member type")
            git_blob = hashlib.sha1(
                f"blob {len(content)}\0".encode() + content, usedforsecurity=False
            ).hexdigest()
            if git_blob != entry["git_blob_sha1"]:
                raise ValueError("Archive bytes do not match the committed Git blob")
            tracked_files.append({"repository_path": relative, **entry,
                                  "bytes": len(content),
                                  "sha256": hashlib.sha256(content).hexdigest()})
    if expected:
        raise ValueError("Committed source files are missing from the archive")
    manifest = {
        "schema_version": 2,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint_git_commit": commit,
        "checkpoint_git_tree_sha1": git(repository, "rev-parse", f"{commit}^{{tree}}").decode().strip(),
        "scope": "Exact already-pushed committed research checkpoint; source archive and complete local Git-ref history bundle. Live worktree files, raw EEG arrays, ignored large ledgers and runtime credentials are excluded. Those scientific arrays/ledgers have separate immutable completed R2 receipts.",
        "archive_every_file_verified_against_committed_git_blob": True,
        "archive_commit_header_verified": True,
        "history_bundle_verification": "passed",
        "advertised_bundle_heads": [
            {"git_commit": line.split(" ", 1)[0], "ref": line.split(" ", 1)[1]}
            for line in bundle_heads.splitlines()
        ],
        "tracked_file_count": len(tracked_files),
        "tracked_file_bytes": sum(entry["bytes"] for entry in tracked_files),
        "files": [{"path": path.name, "bytes": path.stat().st_size,
                   "sha256": digest_file(path)}
                  for path in [source_archive, history_bundle]],
        "tracked_source_files": sorted(tracked_files, key=lambda item: item["repository_path"]),
        "credential_values_logged": False,
        "untracked_work_excluded": True,
    }
    manifest_path = destination / "CHECKPOINT_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return {"checkpoint_git_commit": commit, "tracked_files": len(tracked_files),
            "planned_files": 3,
            "planned_bytes": sum(path.stat().st_size for path in destination.iterdir()),
            "manifest_sha256": digest_file(manifest_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--commit", required=True)
    arguments = parser.parse_args()
    print(json.dumps(archive(arguments.repository.resolve(strict=True),
                             arguments.destination, arguments.commit)))


if __name__ == "__main__":
    main()
