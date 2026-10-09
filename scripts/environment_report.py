"""Inspect the actual runtime without collecting environment/credential values."""

from __future__ import annotations

import argparse
from datetime import datetime
from importlib import import_module, metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
from zoneinfo import ZoneInfo


def environment_report() -> dict:
    packages = {}
    for name, module in (
        ("numpy", "numpy"),
        ("scipy", "scipy"),
        ("scikit-learn", "sklearn"),
        ("mne", "mne"),
        ("moabb", "moabb"),
        ("braindecode", "braindecode"),
        ("torch", "torch"),
        ("torchaudio", "torchaudio"),
        ("pytest", "pytest"),
    ):
        try:
            version = metadata.version(name)
            import_module(module)
            packages[name] = {"version": version, "import_verified": True}
        except Exception as error:
            packages[name] = {"import_verified": False, "failure_type": type(error).__name__}
    import torch

    memory = {}
    if Path("/proc/meminfo").is_file():
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, value = line.split(":", 1)
            if key in {"MemTotal", "MemAvailable"}:
                memory[key + "_bytes"] = int(value.strip().split()[0]) * 1024
    disk = shutil.disk_usage(Path.cwd())
    identity = {}
    for key in ("user.name", "user.email"):
        operation = subprocess.run(["git", "config", "--get", key], capture_output=True, text=True)
        identity[key] = (
            "configured" if operation.returncode == 0 and operation.stdout.strip() else "missing"
        )
    return {
        "observed_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "platform": platform.platform(),
        "os_release": platform.freedesktop_os_release(),
        "architecture": platform.machine(),
        "python": platform.python_version(),
        "python_executable": os.sys.executable,
        "cpu_count": os.cpu_count(),
        "cpu_affinity_count": len(os.sched_getaffinity(0))
        if hasattr(os, "sched_getaffinity")
        else None,
        "memory": memory,
        "disk": {"total_bytes": disk.total, "free_bytes": disk.free},
        "packages": packages,
        "gpu": {
            "torch_cuda_available": torch.cuda.is_available(),
            "torch_cuda_build": torch.version.cuda,
            "device_count": torch.cuda.device_count(),
            "nvidia_smi_present": shutil.which("nvidia-smi") is not None,
            "nvidia_device_nodes": sorted(str(p) for p in Path("/dev").glob("nvidia*")),
            "validated_device": "cpu",
        },
        "git_identity": identity,
        "paid_compute_created": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = environment_report()
    encoded = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    if not all(p["import_verified"] for p in report["packages"].values()):
        raise SystemExit("One or more required full-environment imports failed")


if __name__ == "__main__":
    main()
