"""Exercise the real single-file installer with a synthetic existing project."""

from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "v3_bundle_builder", ROOT / "experiments/hpc_recalibration_v3/build_bundle.py"
)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def test_deterministic_bundle_has_only_code_metadata_and_licenses(tmp_path):
    first = builder.build(tmp_path / "first.pyz", source_commit="synthetic-software-validation")
    second = builder.build(tmp_path / "second.pyz", source_commit="synthetic-software-validation")
    assert first["sha256"] == second["sha256"]
    with zipfile.ZipFile(tmp_path / "first.pyz") as z:
        names = z.namelist()
        assert not any(n.endswith((".pt", ".npz")) for n in names)
        manifest = json.loads(z.read("BUNDLE_MANIFEST.json"))
        for row in manifest["files"]:
            body = z.read("payload/" + row["path"])
            assert len(body) == row["bytes"] and hashlib.sha256(body).hexdigest() == row["sha256"]
        assert "payload/hpc_recalibration_v3/summarize.py" in names
        assert "payload/hpc_recalibration/checkpoint.py" in names
        assert "payload/github_result_upload.py" in names


def test_actual_zipapp_install_reuses_project_and_status_without_gpu_or_scheduler(tmp_path):
    bundle = tmp_path / "test-only.pyz"
    builder.build(bundle, source_commit="synthetic-software-validation")
    base = tmp_path / "v2"
    (base / "configs").mkdir(parents=True)
    data = base / "data"
    data.mkdir()
    original = {
        "project_dir": str(base),
        "data_root": str(data),
        "output_root": str(base / "outputs"),
        "python": sys.executable,
    }
    (base / "configs/kumar_dev_hpc_gpu1_24cpu.json").write_text(json.dumps(original))
    destination = tmp_path / "v3"
    command = [
        sys.executable,
        "-u",
        str(bundle),
        "--base-project",
        str(base),
        "--project-dir",
        str(destination),
        "--prepare-only",
    ]
    first = subprocess.run(command, text=True, capture_output=True, timeout=30)
    assert first.returncode == 0, first.stdout + first.stderr
    assert '"tasks": 126' in first.stdout
    # A persistent result sentinel cannot be erased by a repeated installation.
    sentinel = destination / "outputs/existing-checkpoint-sentinel"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_bytes(b"synthetic saved result")
    repeat = subprocess.run(command, text=True, capture_output=True, timeout=30)
    assert repeat.returncode == 0 and '"updated_code_files": 0' in repeat.stdout
    assert sentinel.read_bytes() == b"synthetic saved result"
    status = subprocess.run(
        [sys.executable, "-u", str(destination / "bootstrap.py"), "status"],
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert status.returncode == 0, status.stdout + status.stderr
    assert '"completed_tasks": 0' in status.stdout and '"total_tasks": 126' in status.stdout
    imports = subprocess.run(
        [
            sys.executable,
            "-c",
            "import hpc_recalibration_v3.geometry,hpc_recalibration_v3.neural,hpc_recalibration_v3.simulation,hpc_recalibration_v3.summarize,hpc_recalibration_v3.publish_results",
        ],
        cwd=destination,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert imports.returncode == 0, imports.stderr
