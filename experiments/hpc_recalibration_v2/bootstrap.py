#!/usr/bin/env python3
"""Observable entry point; normal -u launch and optional -I -S are supported."""
import argparse
import json
import os
from pathlib import Path
import sys
import sysconfig
import traceback


def configure_imports():
    # In Python <=3.13, -S can leave sys.prefix at the base interpreter even for
    # a venv. Inspect the invoked executable path without resolving its symlink.
    if sys.flags.no_site:
        env_root = Path(sys.executable).absolute().parent.parent
        if (env_root / "pyvenv.cfg").is_file():
            sys.prefix = str(env_root)
            sys.exec_prefix = str(env_root)
            ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
            locations = [env_root / "lib" / ver / "site-packages",
                         env_root / "lib64" / ver / "site-packages"]
        else:
            locations = [Path(sysconfig.get_path(key)) for key in ("purelib", "platlib")]
        for location in locations:
            if location.is_dir() and str(location) not in sys.path:
                sys.path.append(str(location))
    sys.path.insert(0, str(Path(__file__).resolve().parent))


configure_imports()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "submit", "worker", "gpu-smoke", "summarize"])
    parser.add_argument("--config", required=True)
    parser.add_argument("--index", type=int)
    parser.add_argument("--refresh-preflight", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(json.dumps({"event": "python_start", "pid": os.getpid(),
                      "python": sys.version.split()[0], "command": args.command}), flush=True)
    from hpc_recalibration import preflight
    config = preflight.load_config(args.config)
    if args.command == "summarize":
        from hpc_recalibration.summarize import summarize
        result = summarize(config)
        print(json.dumps({key: result[key] for key in (
            "tasks_expected", "tasks_complete", "cells_expected", "cells_with_defined_ba")}), flush=True)
        return 0
    if args.command == "prepare":
        print(json.dumps(preflight.prepare_once(config, refresh=args.refresh_preflight), indent=2))
        return 0
    if args.command == "submit":
        from hpc_recalibration.slurm import submit
        print(json.dumps(submit(config, refresh_preflight=args.refresh_preflight,
                                dry_run=args.dry_run), indent=2))
        return 0
    if args.command == "gpu-smoke":
        print(json.dumps(preflight.gpu_smoke_once(config), indent=2))
        return 0
    tasks = preflight.load_tasks(config)
    if args.index is None or not 0 <= args.index < len(tasks):
        raise ValueError("worker requires a valid --index into the prepared task list")
    task = tasks[args.index]
    # Runtime controls are separate from scientific identity and checkpoint schema.
    for key, value in config.get("runtime", {}).items():
        config.setdefault(key, value)
    preflight.lightweight_ready(config)
    if task.get("family", "eegnet") == "eegnet":
        preflight.gpu_smoke_once(config)
        from hpc_recalibration.training import run_task
    elif task["family"] == "classical":
        from hpc_recalibration.classical import run_task
    else:
        raise ValueError("unsupported task family")
    return int(run_task(task, config) or 0)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
