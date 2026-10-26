#!/usr/bin/env python3
"""Observable entry for the separately versioned school discovery round."""

import argparse
import json
import os
from pathlib import Path
import sys
import sysconfig
import traceback

for variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[variable] = "1"
if sys.flags.no_site:
    env = Path(sys.executable).absolute().parent.parent
    if (env / "pyvenv.cfg").is_file():
        sys.prefix = sys.exec_prefix = str(env)
        locations = [
            env
            / "lib"
            / f"python{sys.version_info.major}.{sys.version_info.minor}"
            / "site-packages",
            env
            / "lib64"
            / f"python{sys.version_info.major}.{sys.version_info.minor}"
            / "site-packages",
        ]
    else:
        locations = [Path(sysconfig.get_path(k)) for k in ("purelib", "platlib")]
    sys.path.extend(str(p) for p in locations if p.is_dir())
sys.path.insert(0, str(Path(__file__).resolve().parent))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=["submit", "worker", "monitor", "status", "summarize", "publish"]
    )
    parser.add_argument(
        "--config", default=str(Path(__file__).resolve().parent / "configs/discovery.json")
    )
    parser.add_argument("--slot", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reauthorize", action="store_true")
    parser.add_argument("--lock-fd", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            {
                "event": "python_start",
                "command": args.command,
                "pid": os.getpid(),
                "python": sys.version.split()[0],
            }
        ),
        flush=True,
    )
    from hpc_recalibration_v3.configuration import load_config, prepare_inputs
    from hpc_recalibration_v3.runtime import load_tasks, submit, worker_slot

    config = load_config(args.config)
    if args.command == "submit":
        from hpc_recalibration_v3.monitor import authorize, start_monitor

        config["_reauthorize"] = args.reauthorize
        if args.reauthorize and not args.dry_run:
            authorize(config)
            config["_reauthorize"] = False
        print(
            json.dumps({"event": "input_cache", **prepare_inputs(config, load_tasks(config))}),
            flush=True,
        )
        result = submit(
            config, dry_run=args.dry_run, authorize=authorize, monitor_start=start_monitor
        )
        print(json.dumps(result, indent=2), flush=True)
        return 1 if result.get("submission_failures") else 0
    if args.command == "worker":
        print(
            json.dumps({"event": "input_cache", **prepare_inputs(config, load_tasks(config))}),
            flush=True,
        )
        from hpc_recalibration_v3.workers import run_task

        return worker_slot(config, args.slot, task_runner=run_task)
    if args.command == "monitor":
        from hpc_recalibration_v3.monitor import monitor

        return monitor(args.config, args.lock_fd, args.once)
    if args.command == "status":
        from hpc_recalibration_v3.monitor import snapshot

        print(json.dumps(snapshot(config), indent=2), flush=True)
        return 0
    if args.command == "summarize":
        from hpc_recalibration_v3.summarize import summarize

        print(json.dumps(summarize(config), indent=2), flush=True)
        return 0
    from hpc_recalibration_v3.publish_results import publish

    result = publish(config)
    print(json.dumps(result, indent=2), flush=True)
    return (
        0
        if result.get("status") == "uploaded_unreviewed" and not result.get("history_errors")
        else 1
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
