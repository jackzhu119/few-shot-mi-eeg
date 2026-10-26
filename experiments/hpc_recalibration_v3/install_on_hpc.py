"""Install the bundled V3 code beside the completed V2 project, then submit once."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile


def atomic_file(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def install(archive, base_project, destination):
    base_project, destination = Path(base_project).resolve(), Path(destination).resolve()
    base_config_path = base_project / "configs/kumar_dev_hpc_gpu1_24cpu.json"
    if not base_config_path.is_file():
        raise FileNotFoundError(
            "Existing completed V2 configuration is missing: " + str(base_config_path)
        )
    base = json.loads(base_config_path.read_text())
    for key in ("data_root", "project_dir", "output_root"):
        value = Path(base[key]).expanduser()
        base[key] = str(
            value if value.is_absolute() else (base_config_path.parent / value).resolve()
        )
    with zipfile.ZipFile(archive) as package:
        manifest = json.loads(package.read("BUNDLE_MANIFEST.json"))
        written = 0
        for row in manifest["files"]:
            name = row["path"]
            if Path(name).is_absolute() or ".." in Path(name).parts:
                raise ValueError("Invalid bundled path")
            body = package.read("payload/" + name)
            if len(body) != row["bytes"] or hashlib.sha256(body).hexdigest() != row["sha256"]:
                raise ValueError("Bundled code integrity failure")
            path = destination / name
            if not path.is_file() or path.read_bytes() != body:
                atomic_file(path, body)
                written += 1
        science = json.loads(package.read("assets/science.json"))
        original = json.loads(package.read("assets/v2_tasks.json"))
        original_tasks = original["tasks"] if isinstance(original, dict) else original
        checkpoints = json.loads(package.read("assets/v2_source_checkpoints.json"))
    sys.path.insert(0, str(destination))
    from hpc_recalibration_v3.configuration import generate

    config, tasks = generate(base, original_tasks, checkpoints, destination, science)
    config_path = destination / "configs/discovery.json"
    tasks_path = destination / "configs/tasks.json"
    if config_path.is_file():
        old = json.loads(config_path.read_text())
        if old["science"] != config["science"]:
            raise ValueError(
                "A different scientific version already occupies this project; keep its checkpoints and use a new directory"
            )
        # Preserve explicit local runtime resource changes, not stale science.
        config = old
    else:
        atomic_file(config_path, (json.dumps(config, indent=2) + "\n").encode())
    if tasks_path.is_file() and json.loads(tasks_path.read_text()) != tasks:
        raise ValueError(
            "Existing task identities differ; retain their outputs and use a new version"
        )
    if not tasks_path.is_file():
        atomic_file(tasks_path, (json.dumps(tasks, indent=2) + "\n").encode())
    atomic_file(
        destination / "PACKAGE_MANIFEST.json", (json.dumps(manifest, indent=2) + "\n").encode()
    )
    print(
        json.dumps(
            {
                "event": "v3_installed",
                "project_dir": str(destination),
                "updated_code_files": written,
                "tasks": len(tasks),
                "new_pooled_source_fits": 3,
                "old_v2_source_refits": 0,
                "input_data_reused_from": base["data_root"],
                "resources": "3 jobs; 1GPU/16CPU/64G each",
            }
        ),
        flush=True,
    )
    return config_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-project", default="/public/home/zhuziyuan/projects/paper2-recalibration-v2"
    )
    parser.add_argument(
        "--project-dir", default="/public/home/zhuziyuan/projects/paper2-recalibration-v3"
    )
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reauthorize", action="store_true")
    args = parser.parse_args()
    config = install(Path(sys.argv[0]), args.base_project, args.project_dir)
    if args.prepare_only:
        return 0
    command = [
        sys.executable,
        "-u",
        str(Path(args.project_dir) / "bootstrap.py"),
        "submit",
        "--config",
        str(config),
    ]
    if args.dry_run:
        command.append("--dry-run")
    if args.reauthorize:
        command.append("--reauthorize")
    return subprocess.call(command)


if __name__ == "__main__":
    raise SystemExit(main())
