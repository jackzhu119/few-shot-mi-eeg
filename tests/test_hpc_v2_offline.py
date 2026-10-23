"""Offline packaging/install tests; no network, Slurm submission or real EEG."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile

import pytest


SOURCE = Path(__file__).resolve().parents[1] / "experiments" / "hpc_recalibration_v2"
SPEC = importlib.util.spec_from_file_location("paper2_offline_builder", SOURCE / "build_offline.py")
offline = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(offline)


def make_tar(path, members):
    with tarfile.open(path, "w:gz") as archive:
        for name, body, kind in members:
            info = tarfile.TarInfo(name)
            info.mode = 0o644
            info.type = kind
            if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
                info.linkname = "../../escaped"
            if kind == tarfile.REGTYPE:
                info.size = len(body)
                archive.addfile(info, io.BytesIO(body))
            else:
                archive.addfile(info)


@pytest.fixture
def bundles(tmp_path, monkeypatch):
    source = tmp_path / "source"
    repository = tmp_path / "repository"
    source.mkdir()
    repository.mkdir()
    for name in offline.PROJECT_FILES + offline.MODULE_FILES:
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if name in ("build_offline.py", "install_offline.sh"):
            path.write_bytes((SOURCE / name).read_bytes())
        else:
            path.write_text("software-validation-only\n")
    for name in offline.REPOSITORY_FILES:
        path = repository / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("software-validation-only license or methods\n")
    (source / "secret-token.txt").write_text("must-not-be-packed")
    (source / "outputs").mkdir()
    (source / "outputs" / "model.pt").write_bytes(b"must-not-be-packed")
    monkeypatch.setattr(offline.subprocess, "check_output", lambda *a, **kw: "test-base-commit\n")
    code = tmp_path / "paper2-hpc-v2-code.tar.gz"
    data = b"synthetic-only-payload"
    manifest = {"schema_version": 1, "files": [
        {"path": "subject/train.npz", "bytes": len(data),
         "sha256": hashlib.sha256(data).hexdigest()}]}
    (source / "configs/input_manifest.json").write_text(json.dumps(manifest))
    offline.build_bundle(source, repository, code)
    inputs = tmp_path / "paper2-hpc-v2-kumar-dev-inputs.tar.gz"
    make_tar(inputs, [(offline.INPUT_TOP + "/subject/train.npz", data, tarfile.REGTYPE),
                      (offline.INPUT_TOP + "/input_manifest.json",
                       json.dumps(manifest).encode(), tarfile.REGTYPE)])
    return {"code": code, "inputs": inputs, "project": tmp_path / "installed",
            "source": source, "repository": repository}


def test_allowlisted_bundle_excludes_secret_outputs_and_roundtrips(bundles):
    with tarfile.open(bundles["code"]) as archive:
        names = archive.getnames()
        assert not any("secret" in n or "outputs" in n for n in names)
        assert all(n.startswith(offline.CODE_TOP + "/") for n in names)
        manifest = json.load(archive.extractfile(offline.CODE_TOP + "/PACKAGE_MANIFEST.json"))
        assert manifest["base_git_commit"] == "test-base-commit"
    record = offline.inspect_archive(bundles["code"], offline.CODE_TOP, "PACKAGE_MANIFEST.json")
    assert len(record["files"]) == len(manifest["files"]) + 1


def test_install_idempotent_cache_avoids_full_rescan_and_preserves_outputs(bundles, monkeypatch):
    first = offline.install_bundles(bundles["code"], bundles["inputs"], bundles["project"])
    assert first["status"] == "installed"
    data = bundles["project"] / "data" / offline.INPUT_TOP / "subject/train.npz"
    assert data.read_bytes() == b"synthetic-only-payload"
    outputs = bundles["project"] / "outputs"
    outputs.mkdir()
    (outputs / "checkpoint.pt").write_bytes(b"existing-training-result")
    monkeypatch.setattr(offline, "inspect_archive", lambda *a: pytest.fail("must reuse installation cache"))
    second = offline.install_bundles(bundles["code"], bundles["inputs"], bundles["project"])
    assert second["status"] == "already_installed"
    assert second["full_archive_rescan"] is False
    assert (outputs / "checkpoint.pt").read_bytes() == b"existing-training-result"


def test_existing_different_source_is_not_overwritten(bundles):
    bundles["project"].mkdir()
    existing = bundles["project"] / "README.md"
    existing.write_text("user's existing edited README")
    with pytest.raises(ValueError, match="Existing file differs"):
        offline.install_bundles(bundles["code"], bundles["inputs"], bundles["project"])
    assert existing.read_text() == "user's existing edited README"
    assert not (bundles["project"] / "bootstrap.py").exists()


def test_manifest_hash_failure_writes_no_project_payload(bundles):
    wrong = {"files": [{"path": "x.npz", "bytes": 3, "sha256": "0" * 64}]}
    make_tar(bundles["inputs"], [(offline.INPUT_TOP + "/x.npz", b"bad", tarfile.REGTYPE),
                                 (offline.INPUT_TOP + "/input_manifest.json",
                                  json.dumps(wrong).encode(), tarfile.REGTYPE)])
    with pytest.raises(ValueError, match="length/SHA256"):
        offline.install_bundles(bundles["code"], bundles["inputs"], bundles["project"])
    assert not bundles["project"].exists()


def test_self_consistent_wrong_input_archive_is_rejected(bundles):
    body = b"other-dataset"
    wrong = {"files": [{"path": "x.npz", "bytes": len(body),
                        "sha256": hashlib.sha256(body).hexdigest()}]}
    make_tar(bundles["inputs"], [(offline.INPUT_TOP + "/x.npz", body, tarfile.REGTYPE),
                                 (offline.INPUT_TOP + "/input_manifest.json",
                                  json.dumps(wrong).encode(), tarfile.REGTYPE)])
    with pytest.raises(ValueError, match="frozen input manifest"):
        offline.install_bundles(bundles["code"], bundles["inputs"], bundles["project"])
    assert not bundles["project"].exists()


@pytest.mark.parametrize("name,kind", [
    ("../outside", tarfile.REGTYPE),
    ("/absolute", tarfile.REGTYPE),
    (offline.CODE_TOP + "/../../outside", tarfile.REGTYPE),
    (offline.CODE_TOP + "/link", tarfile.SYMTYPE),
    (offline.CODE_TOP + "/link", tarfile.LNKTYPE),
])
def test_archive_path_and_link_rejection(tmp_path, name, kind):
    archive = tmp_path / "unsafe.tar.gz"
    make_tar(archive, [(name, b"bad", kind)])
    with pytest.raises(ValueError):
        offline.inspect_archive(archive, offline.CODE_TOP, "PACKAGE_MANIFEST.json")
    assert not (tmp_path / "outside").exists()


def test_existing_data_symlink_cannot_escape_project(bundles, tmp_path):
    project = bundles["project"]
    project.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (project / "data").symlink_to(elsewhere, target_is_directory=True)
    with pytest.raises(ValueError, match="symbolic link"):
        offline.install_bundles(bundles["code"], bundles["inputs"], project)
    assert not list(elsewhere.iterdir())


def test_single_shell_file_installs_without_launch_or_network(bundles, monkeypatch):
    # Restore the actual subprocess API that the build fixture mocked.
    monkeypatch.undo()
    environment = os.environ.copy()
    environment.update({"HPC_V2_PYTHON": sys.executable,
                        "HPC_V2_CODE_ARCHIVE": str(bundles["code"]),
                        "HPC_V2_INPUTS_ARCHIVE": str(bundles["inputs"]),
                        "HPC_V2_PROJECT_DIR": str(bundles["project"])})
    result = subprocess.run(["bash", str(SOURCE / "install_offline.sh"), "--no-launch"],
                            env=environment, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "installed"
    assert (bundles["project"] / ".offline_install.json").exists()
    assert not (bundles["project"] / "outputs").exists()


def test_changed_installed_file_invalidates_stat_cache(bundles):
    offline.install_bundles(bundles["code"], bundles["inputs"], bundles["project"])
    altered = bundles["project"] / "bootstrap.py"
    altered.write_text("local edited version must be preserved")
    with pytest.raises(ValueError, match="Existing file differs"):
        offline.install_bundles(bundles["code"], bundles["inputs"], bundles["project"])
    assert altered.read_text() == "local edited version must be preserved"
