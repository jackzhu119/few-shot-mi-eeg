#!/usr/bin/env python3
"""Build or install this project's explicit, dependency-free offline code bundle.

Run build on the development host. Run install on login1, never a GPU job.
Installation verifies each archive once, uses same-directory atomic files, and
preserves existing outputs and all differing files. A lightweight stat receipt
makes unchanged repeated installation/resumption cheap.
"""

from __future__ import annotations

import argparse
import fcntl
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile
import tempfile
import time


CODE_TOP = "paper2-recalibration-v2"
INPUT_TOP = "kumar_cue5s_v1"
PROJECT_FILES = (
    "README.md", "NOTICE.md", "launch.sh", "job.sh", "bootstrap.py", "build_offline.py",
    "install_offline.sh", "configs/kumar_dev.json", "configs/tasks_kumar_dev.json",
    "configs/input_manifest.json", "configs/input_archive_receipt.json",
)
MODULE_FILES = tuple("hpc_recalibration/" + name for name in (
    "__init__.py", "checkpoint.py", "training.py", "classical.py", "data.py", "preflight.py",
    "slurm.py", "github_sync.py", "summarize.py",
))
REPOSITORY_FILES = {
    "LICENSES/MIT.txt": "LICENSE",
    "LICENSING.md": "LICENSING.md",
    "LICENSES/CC-BY-4.0.txt": "LICENSES/CC-BY-4.0.txt",
    "LICENSES/paper2-hpc-v2-scope-20261023.md": "LICENSES/paper2-hpc-v2-scope-20261023.md",
    "docs/paper2_hpc_v2_literature_and_scientific_design_20261023.md":
        "docs/paper2_hpc_v2_literature_and_scientific_design_20261023.md",
    "docs/paper2_hpc_v2_literature_and_scientific_design_20261023.json":
        "docs/paper2_hpc_v2_literature_and_scientific_design_20261023.json",
}


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode("utf-8")


def _atomic_bytes(path: Path, content: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            os.fchmod(handle.fileno(), mode)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def build_bundle(source: Path, repository: Path, destination: Path) -> dict:
    """No recursive repo archive: only the named code/config/docs/license files."""
    source, repository, destination = source.resolve(), repository.resolve(), destination.resolve()
    files = {name: source / name for name in PROJECT_FILES + MODULE_FILES}
    files.update({target: repository / origin for origin, target in REPOSITORY_FILES.items()})
    missing = [name for name, path in files.items() if not path.is_file() or path.is_symlink()]
    if missing:
        raise ValueError("Offline package is incomplete: " + ", ".join(missing))
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repository,
                                     text=True).strip()
    rows = [{"path": name, "bytes": path.stat().st_size, "sha256": _sha(path)}
            for name, path in sorted(files.items())]
    manifest = {"schema_version": 1, "package": CODE_TOP, "base_git_commit": commit,
                "content_identity": "Exact per-file SHA256; current development files may be uncommitted.",
                "no_dependencies_or_credentials_included": True, "files": rows}
    payloads = {name: path.read_bytes() for name, path in files.items()}
    payloads["PACKAGE_MANIFEST.json"] = _json_bytes(manifest)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="." + destination.name + ".", dir=destination.parent)
    try:
        with os.fdopen(fd, "wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
                with tarfile.open(fileobj=compressed, mode="w") as archive:
                    for name, body in sorted(payloads.items()):
                        info = tarfile.TarInfo(CODE_TOP + "/" + name)
                        info.size = len(body)
                        info.mode = 0o755 if name.endswith(".sh") or name == "bootstrap.py" else 0o644
                        info.mtime = 0
                        archive.addfile(info, io.BytesIO(body))
            raw.flush()
            os.fsync(raw.fileno())
        os.replace(temporary, destination)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    receipt = {"archive": destination.name, "bytes": destination.stat().st_size,
               "sha256": _sha(destination), "payload_files": len(rows),
               "base_git_commit": commit}
    _atomic_bytes(destination.with_suffix(destination.suffix + ".sha256.json"), _json_bytes(receipt))
    return receipt


def _member_path(name: str, top: str) -> str:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name:
        raise ValueError("Archive contains an unsafe path.")
    if not path.parts or path.parts[0] != top:
        raise ValueError("Archive has an unexpected top-level directory.")
    return "/".join(path.parts[1:])


def inspect_archive(path: Path, top: str, manifest_name: str) -> dict:
    """Validate every original payload byte before installing either archive."""
    with tarfile.open(path, "r:*") as archive:
        regular = {}
        seen = set()
        for member in archive.getmembers():
            relative = _member_path(member.name, top)
            if relative in seen:
                raise ValueError("Archive contains duplicate paths.")
            seen.add(relative)
            if member.isdir():
                continue
            if not member.isfile() or not relative:
                raise ValueError("Archive contains a link or unsupported member type.")
            regular[relative] = member
        if manifest_name not in regular:
            raise ValueError("Archive manifest is missing.")
        manifest = json.load(archive.extractfile(regular[manifest_name]))
        expected = {}
        for row in manifest["files"]:
            name = row["path"]
            if _member_path(top + "/" + name, top) != name or not name:
                raise ValueError("Manifest contains an unsafe path.")
            if name in expected or name == manifest_name:
                raise ValueError("Manifest contains duplicate or recursive entries.")
            expected[name] = row
        if set(regular) != set(expected) | {manifest_name}:
            raise ValueError("Archive members differ from its complete manifest.")
        verified = []
        for name, member in regular.items():
            digest = hashlib.sha256()
            count = 0
            with archive.extractfile(member) as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
                    count += len(block)
            if name in expected:
                row = expected[name]
                if count != row["bytes"] or digest.hexdigest() != row["sha256"]:
                    raise ValueError("Archive length/SHA256 mismatch for " + name)
            verified.append({"path": name, "bytes": count, "sha256": digest.hexdigest(),
                             "mode": member.mode & 0o777})
        return {"archive": str(path.resolve()), "top": top, "files": verified}


def _destination(root: Path, name: str) -> Path:
    destination = root / name
    current = root
    for component in PurePosixPath(name).parts:
        current = current / component
        if current.is_symlink():
            raise ValueError("Installation cannot traverse an existing symbolic link.")
    if destination.exists() and not destination.is_file():
        raise ValueError("Installation target is not a regular file: " + str(destination))
    return destination


def _stamp(path: Path) -> dict:
    value = path.stat()
    return {"bytes": value.st_size, "mtime_ns": value.st_mtime_ns}


def _same_install(receipt: dict, archives: dict, project: Path) -> bool:
    try:
        if receipt.get("archive_stats") != {name: _stamp(path) for name, path in archives.items()}:
            return False
        for row in receipt["installed_files"]:
            path = _destination(project, row["path"])
            if _stamp(path) != row["stat"]:
                return False
        return True
    except (KeyError, OSError, ValueError):
        return False


def install_bundles(code_archive: Path, inputs_archive: Path, project: Path) -> dict:
    """Idempotent install; refuse differences, never delete or write output files."""
    code_archive, inputs_archive, project = code_archive.resolve(), inputs_archive.resolve(), project.resolve()
    project.parent.mkdir(parents=True, exist_ok=True)
    lock_path = project.parent / ("." + project.name + ".install.lock")
    lock_fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(lock_fd)
        raise RuntimeError("Another installation is already running for this project.") from None
    try:
        archives = {"code": code_archive, "inputs": inputs_archive}
        receipt_path = project / ".offline_install.json"
        if receipt_path.is_file():
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            if _same_install(receipt, archives, project):
                return {"status": "already_installed", "full_archive_rescan": False,
                        "project_dir": str(project), "installed_files": len(receipt["installed_files"])}
        code = inspect_archive(code_archive, CODE_TOP, "PACKAGE_MANIFEST.json")
        inputs = inspect_archive(inputs_archive, INPUT_TOP, "input_manifest.json")
        expected_inputs = next(row for row in code["files"]
                               if row["path"] == "configs/input_manifest.json")
        actual_inputs = next(row for row in inputs["files"] if row["path"] == "input_manifest.json")
        if expected_inputs["sha256"] != actual_inputs["sha256"]:
            raise ValueError("Input archive does not match the code package's frozen input manifest.")
        allowed = set(PROJECT_FILES + MODULE_FILES) | set(REPOSITORY_FILES.values()) | {"PACKAGE_MANIFEST.json"}
        if any(row["path"] not in allowed for row in code["files"]):
            raise ValueError("Code archive contains a file outside the explicit code/config/docs allowlist.")
        actions = []
        for archive, prefix in ((code, ""), (inputs, "data/" + INPUT_TOP + "/")):
            for row in archive["files"]:
                target = _destination(project, prefix + row["path"])
                if target.exists() and _sha(target) != row["sha256"]:
                    raise ValueError("Existing file differs; no files were overwritten: " + str(target)
                                     + ". Preserve outputs; install a changed code package in a new version directory.")
                actions.append((archive, row, target))
        project.mkdir(parents=True, exist_ok=True, mode=0o700)
        handles = {}
        try:
            for archive, row, target in actions:
                if target.exists():
                    continue
                source = archive["archive"]
                if source not in handles:
                    handles[source] = tarfile.open(source, "r:*")
                tar = handles[source]
                member = tar.getmember(archive["top"] + "/" + row["path"])
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                fd, temporary = tempfile.mkstemp(prefix="." + target.name + ".", dir=target.parent)
                try:
                    digest = hashlib.sha256()
                    count = 0
                    with tar.extractfile(member) as incoming, os.fdopen(fd, "wb") as outgoing:
                        os.fchmod(outgoing.fileno(), row["mode"] or 0o600)
                        for block in iter(lambda: incoming.read(1024 * 1024), b""):
                            outgoing.write(block)
                            digest.update(block)
                            count += len(block)
                        outgoing.flush()
                        os.fsync(outgoing.fileno())
                    if count != row["bytes"] or digest.hexdigest() != row["sha256"]:
                        raise ValueError("Archive changed during installation: " + row["path"])
                    os.replace(temporary, target)
                except BaseException:
                    try:
                        os.unlink(temporary)
                    except FileNotFoundError:
                        pass
                    raise
        finally:
            for handle in handles.values():
                handle.close()
        receipt = {"schema_version": 1, "installed_unix": time.time(),
                   "archive_stats": {name: _stamp(path) for name, path in archives.items()},
                   "archive_sha256": {name: _sha(path) for name, path in archives.items()},
                   "installed_files": [{"path": str(target.relative_to(project)),
                                        "sha256": row["sha256"], "stat": _stamp(target)}
                                       for _, row, target in actions]}
        _atomic_bytes(receipt_path, _json_bytes(receipt))
        return {"status": "installed", "full_archive_rescan": True, "project_dir": str(project),
                "installed_files": len(actions), "archive_sha256": receipt["archive_sha256"]}
    finally:
        os.close(lock_fd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    build.add_argument("--source", type=Path, default=Path(__file__).resolve().parent)
    build.add_argument("--repository", type=Path, default=Path(__file__).resolve().parents[2])
    build.add_argument("--output", type=Path, required=True)
    install = commands.add_parser("install")
    install.add_argument("--code-archive", type=Path, required=True)
    install.add_argument("--inputs-archive", type=Path, required=True)
    install.add_argument("--project-dir", type=Path, required=True)
    install.add_argument("--config", default="configs/kumar_dev.json")
    install.add_argument("--no-launch", action="store_true")
    args = parser.parse_args()
    if args.command == "build":
        print(json.dumps(build_bundle(args.source, args.repository, args.output)), flush=True)
        return 0
    result = install_bundles(args.code_archive, args.inputs_archive, args.project_dir)
    print(json.dumps(result), flush=True)
    if not args.no_launch:
        project = args.project_dir.resolve()
        config = Path(args.config)
        if not config.is_absolute():
            config = project / config
        environment = os.environ.copy()
        environment["HPC_V2_PYTHON"] = sys.executable
        os.execvpe("bash", ["bash", str(project / "launch.sh"), str(config)], environment)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
