"""Real local subprocess checks of a copied Slurm script; no GPU/EEG execution."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1] / "experiments/hpc_recalibration_v2"
spec = importlib.util.spec_from_file_location("spool_submit", ROOT / "single_pool/submit.py")
submit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(submit)


@pytest.fixture
def deployment(tmp_path):
    runtime = tmp_path / "shared runtime"
    runtime.mkdir()
    script = runtime / "job.sh"
    script.write_bytes((ROOT / "single_pool/job.sh").read_bytes())
    controller = runtime / "controller.py"
    controller.write_text(
        "import json,os,sys\nfrom pathlib import Path\n"
        "Path(os.environ['START_MARKER']).write_text('synthetic-only')\n"
        "print(json.dumps({'synthetic':True,'software_validation_only':True,'argv':sys.argv[1:]}),flush=True)\n")
    spool = tmp_path / "slurmd/job771415"
    spool.mkdir(parents=True)
    copied = spool / "slurm_script"
    copied.write_bytes(script.read_bytes())
    marker = tmp_path / "controller-started"
    env = os.environ.copy()
    env.update(SLURM_JOB_ID="771415", START_MARKER=str(marker))
    env.pop("PAPER2_POOL_RUNTIME", None)
    return runtime, copied, marker, env


def test_actual_copied_slurm_script_uses_explicit_shared_runtime(deployment):
    runtime, copied, marker, env = deployment
    env["PAPER2_POOL_RUNTIME"] = str(runtime)
    result = subprocess.run(["bash", str(copied), "synthetic.json", sys.executable, "0,1"],
                            env=env, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert marker.read_text() == "synthetic-only"
    assert "pool_runtime directory=" + str(runtime) in result.stdout
    assert "pool_exit code=0" in result.stdout
    row = next(json.loads(line) for line in result.stdout.splitlines() if line.startswith("{"))
    assert row["synthetic"] and row["software_validation_only"]
    assert row["argv"] == ["--config", "synthetic.json", "--indices", "0,1"]


def test_missing_slurm_runtime_binding_stops_before_child_launch(deployment):
    _runtime, copied, marker, env = deployment
    result = subprocess.run(["bash", str(copied), "synthetic.json", sys.executable, "0,1"],
                            env=env, capture_output=True, text=True, timeout=10)
    assert result.returncode == 2
    assert "pool_runtime_missing" in result.stderr
    assert "pool_controller pid=" not in result.stdout
    assert not marker.exists()


def test_relative_runtime_binding_is_not_used(deployment):
    _runtime, copied, marker, env = deployment
    env["PAPER2_POOL_RUNTIME"] = "."
    result = subprocess.run(["bash", str(copied), "synthetic.json", sys.executable],
                            env=env, capture_output=True, text=True, timeout=10)
    assert result.returncode == 2
    assert "pool_runtime_invalid" in result.stderr
    assert not marker.exists()


def test_submit_exports_fixed_runtime_without_changing_batch_argument_layout(tmp_path):
    config = {"project_dir": str(tmp_path), "output_root": str(tmp_path / "output"),
              "_config_path": str(tmp_path / "config.json"), "python": sys.executable,
              "slurm": {"partition": "hpc_gpu1", "pool_workers": 2,
                        "cpus_per_task": 12, "mem": "64G", "gres": "gpu:1"}}
    command = submit._pool_command(config, [0, 1], "synthetic-spool-check")
    assert "--export=ALL,PAPER2_POOL_RUNTIME=" + str((ROOT / "single_pool").resolve()) in command
    assert command[-4:] == [str((ROOT / "single_pool/job.sh").resolve()), config["_config_path"],
                            sys.executable, "0,1"]
    assert all(value in command for value in ("--nodes=1", "--gres=gpu:2", "--cpus-per-task=24", "--mem=128G"))
    assert not any(value.startswith("--array") for value in command)
