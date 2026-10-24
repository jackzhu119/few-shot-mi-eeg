import hashlib
import importlib.util
import io
import json
from pathlib import Path
import urllib.parse

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "runtime_upgrade", ROOT / "experiments/hpc_recalibration_v2/download_on_hpc.py")
download = importlib.util.module_from_spec(spec)
spec.loader.exec_module(download)


class Response(io.BytesIO):
    status = 200
    headers = {}

    def geturl(self):
        return "https://api.github.com/"


@pytest.fixture
def bundle(monkeypatch):
    bodies = {"submit.py": b"# submit runtime\n", "controller.py": b"# controller\n", "job.sh": b"#!/bin/bash\n"}
    rows = tuple({"file": name, "bytes": len(value), "sha256": hashlib.sha256(value).hexdigest()}
                 for name, value in bodies.items())
    monkeypatch.setattr(download, "RUNTIME_COMMIT", "a" * 40)
    monkeypatch.setattr(download, "RUNTIME_ARTIFACTS", rows)
    return bodies


def test_runtime_installs_extra_files_without_touching_original_package(tmp_path, bundle):
    project = tmp_path / "project"
    project.mkdir()
    original = project / "bootstrap.py"
    original.write_bytes(b"# original sealed code\n")
    checkpoint = project / "outputs/model/checkpoint.pt"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_bytes(b"existing checkpoint retained")
    before = original.read_bytes(), checkpoint.read_bytes()

    def opener(request, **kwargs):
        name = urllib.parse.urlsplit(request.full_url).path.rsplit("/", 1)[-1]
        assert urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query)["ref"] == ["a" * 40]
        return Response(bundle[name])

    path = download.install_runtime_bundle(project, tmp_path / "incoming", opener=opener)
    assert path == project / ".hpc_runtime" / ("a" * 40)
    assert (original.read_bytes(), checkpoint.read_bytes()) == before
    for name, value in bundle.items():
        assert (path / name).read_bytes() == value
    manifest = json.loads((path / "runtime_manifest.json").read_bytes())
    assert not manifest["original_code_package_modified"]
    assert not manifest["scientific_configuration_changed"]
    assert download.install_runtime_bundle(
        project, tmp_path / "incoming", opener=lambda *a, **k: pytest.fail("cached runtime fetched again")) == path


def test_wrong_remote_runtime_is_not_installed(tmp_path, bundle):
    with pytest.raises(download.DownloadError, match="SHA256"):
        download.install_runtime_bundle(tmp_path / "project", tmp_path / "incoming",
                                        opener=lambda *a, **k: Response(b"x" * len(bundle["submit.py"])))
    assert not (tmp_path / "project/.hpc_runtime").exists()


def test_versioned_runtime_conflict_does_not_overwrite_local_evidence(tmp_path, bundle):
    project = tmp_path / "project"
    directory = project / ".hpc_runtime" / ("a" * 40)
    directory.mkdir(parents=True)
    existing = directory / "submit.py"
    existing.write_bytes(b"preserve unexpected local source")

    def opener(request, **kwargs):
        name = urllib.parse.urlsplit(request.full_url).path.rsplit("/", 1)[-1]
        return Response(bundle[name])

    with pytest.raises(download.DownloadError, match="versioned runtime differs"):
        download.install_runtime_bundle(project, tmp_path / "incoming", opener=opener)
    assert existing.read_bytes() == b"preserve unexpected local source"
