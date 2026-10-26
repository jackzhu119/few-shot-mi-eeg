"""Build a deterministic offline zipapp; never bundle EEG, weights or secrets."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile


def build(destination, source_commit=None):
    here = Path(__file__).resolve().parent
    root = here.parents[1]
    v2 = root / "experiments/hpc_recalibration_v2"
    source_commit = (
        source_commit
        or subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root).decode().strip()
    )
    content = {"bootstrap.py": (here / "bootstrap.py").read_bytes()}
    for name in (
        "__init__.py",
        "configuration.py",
        "runtime.py",
        "job.sh",
        "geometry.py",
        "neural.py",
        "workers.py",
        "monitor.py",
        "simulation.py",
        "summarize.py",
        "publish_results.py",
    ):
        content["hpc_recalibration_v3/" + name] = (here / name).read_bytes()
    for path in (v2 / "hpc_recalibration").glob("*.py"):
        content["hpc_recalibration/" + path.name] = path.read_bytes()
    for name in ("export_saved_results.py", "github_result_upload.py", "result_history_export.py"):
        content[name] = (v2 / name).read_bytes()
    for name in ("MIT.txt", "CC-BY-4.0.txt"):
        content["LICENSES/" + name] = (root / "LICENSES" / name).read_bytes()
    content["DATA_ATTRIBUTION.txt"] = (
        root / "releases/paper2-hpc-v2-20261023/DATA_ATTRIBUTION.txt"
    ).read_bytes()
    content["LICENSE"] = (root / "LICENSE").read_bytes()
    content["NOTICE.md"] = (
        b"Original V3 code: project MIT scope; derived reports: CC BY4.0 scope. Original EEG rights retained. This bundle contains no EEG or model weights.\n"
    )
    manifest = {
        "source_commit": source_commit,
        "scientific_version": "kumar-discovery-v3.0.0",
        "scope": "offline code only;3GPU jobs; original data and18V2sources reused locally",
        "files": [
            {"path": name, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
            for name, body in sorted(content.items())
        ],
    }
    entries = {"payload/" + name: body for name, body in content.items()}
    entries["__main__.py"] = (here / "install_on_hpc.py").read_bytes()
    entries["BUNDLE_MANIFEST.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    entries["assets/science.json"] = (here / "science.json").read_bytes()
    entries["assets/v2_tasks.json"] = (v2 / "configs/tasks_kumar_dev.json").read_bytes()
    entries["assets/v2_source_checkpoints.json"] = (
        here / "v2_source_checkpoints.json"
    ).read_bytes()
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, body in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(2000, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, body)
    return {
        "file": destination.name,
        "bytes": destination.stat().st_size,
        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "source_commit": source_commit,
        "science_sha256": hashlib.sha256(entries["assets/science.json"]).hexdigest(),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.output), indent=2))
