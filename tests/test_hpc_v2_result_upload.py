"""No real GitHub writes or credentials: an in-memory Git service is used."""
import base64
import importlib.util
from pathlib import Path
import urllib.error

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "hpc_result_upload", ROOT / "experiments/hpc_recalibration_v2/github_result_upload.py")
upload = importlib.util.module_from_spec(spec)
spec.loader.exec_module(upload)


def http_error(status):
    return urllib.error.HTTPError("https://api.github.com/mock", status,
                                   "synthetic_secret_must_not_be_logged", {}, None)


class GitService:
    def __init__(self):
        self.root = "/repos/example/results"
        keep = b"other existing progress\n"
        self.keep_sha = upload.git_blob_sha(keep)
        self.blobs = {self.keep_sha: keep}
        self.trees = {"t0": {"training_status/other/STATUS.json": self.keep_sha}}
        self.commits = {"c0": {"tree": "t0", "parents": []}}
        self.head = "c0"
        self.calls = []
        self.conflict_once = False
        self.corrupt_blob = None
        self.truncated = False

    def __call__(self, method, path, body=None):
        self.calls.append((method, path, body))
        path = path.removeprefix(self.root)
        if method == "GET" and path.startswith("/git/ref/"):
            return {"object": {"sha": self.head}}
        if method == "GET" and path.startswith("/git/commits/"):
            return {"tree": {"sha": self.commits[path.rsplit("/", 1)[-1]]["tree"]}}
        if method == "GET" and path.startswith("/git/trees/"):
            tree = self.trees[path.split("/git/trees/", 1)[1].split("?", 1)[0]]
            return {"truncated": self.truncated,
                    "tree": [{"path": p, "type": "blob", "sha": sha} for p, sha in tree.items()]}
        if method == "GET" and path.startswith("/contents/"):
            name, ref = path.removeprefix("/contents/").split("?ref=")
            tree = self.trees[self.commits[ref]["tree"]]
            if name not in tree:
                raise http_error(404)
            return {"sha": tree[name]}
        if method == "POST" and path == "/git/blobs":
            data = base64.b64decode(body["content"])
            sha = upload.git_blob_sha(data)
            self.blobs[sha] = data
            return {"sha": sha}
        if method == "POST" and path == "/git/trees":
            tree = self.trees[body["base_tree"]].copy()
            tree.update({row["path"]: row["sha"] for row in body["tree"]})
            sha = "t" + str(len(self.trees))
            self.trees[sha] = tree
            return {"sha": sha}
        if method == "POST" and path == "/git/commits":
            sha = "c" + str(len(self.commits))
            self.commits[sha] = {"tree": body["tree"], "parents": body["parents"]}
            return {"sha": sha}
        if method == "PATCH":
            assert body["force"] is False
            if self.conflict_once:
                self.conflict_once = False
                tree = self.trees[self.commits[self.head]["tree"]].copy()
                tree["training_status/other/new-progress.json"] = self.keep_sha
                self.trees["external-tree"] = tree
                self.commits["external-commit"] = {"tree": "external-tree", "parents": [self.head]}
                self.head = "external-commit"
                raise http_error(422)
            if self.commits[body["sha"]]["parents"] != [self.head]:
                raise http_error(422)
            self.head = body["sha"]
            return {"object": {"sha": self.head}}
        if method == "GET" and path.startswith("/git/blobs/"):
            sha = path.rsplit("/", 1)[-1]
            data = self.blobs[sha]
            content = b"incorrect" if sha == self.corrupt_blob else data
            return {"sha": sha, "size": len(data), "encoding": "base64",
                    "content": base64.b64encode(content).decode() + "\n"}
        raise AssertionError((method, path))


@pytest.fixture
def files(tmp_path):
    result = {}
    for name, data in [("manifest.json", b'{"synthetic":true}\n'), ("packet.part000", b"saved-predictions\x00\x01")]:
        path = tmp_path / name
        path.write_bytes(data)
        result["research_logs/paper2/export/" + name] = path
    return result


def publisher(service, sleep=lambda _: None):
    return upload.GitResultPublisher("synthetic-not-a-token", "example/results",
                                     "research/paper2", requester=service, sleep=sleep)


def test_one_atomic_nonforced_commit_and_full_get(files):
    service = GitService()
    result = publisher(service).publish(files, "Publish prepared paper2 results")
    assert result["status"] == "uploaded"
    assert result["verified_objects"] == result["object_count"] == 2
    assert result["failed_objects"] == [] and result["force_push_used"] is False
    assert result["total_bytes"] == sum(path.stat().st_size for path in files.values())
    patches = [r for r in service.calls if r[0] == "PATCH"]
    assert len(patches) == 1 and not patches[0][2]["force"]
    tree = service.trees[service.commits[service.head]["tree"]]
    assert tree["training_status/other/STATUS.json"] == service.keep_sha
    assert set(files) <= set(tree)
    assert all(row["full_get_verified"] for row in result["objects"])


def test_repeat_is_idempotent_but_still_full_get_verifies(files):
    service = GitService()
    client = publisher(service)
    first = client.publish(files, "Publish")
    service.calls.clear()
    second = client.publish(files, "Publish")
    assert second["status"] == "already_uploaded" and second["commit"] == first["commit"]
    assert second["verified_objects"] == 2
    assert not any(method in ("POST", "PATCH") for method, _, _ in service.calls)


def test_conflict_rebuilds_on_new_head_without_reuploading_blobs(files):
    service = GitService()
    service.conflict_once = True
    result = publisher(service).publish(files, "Publish")
    assert result["verified_objects"] == 2
    assert service.commits[result["commit"]]["parents"] == ["external-commit"]
    tree = service.trees[service.commits[service.head]["tree"]]
    assert "training_status/other/new-progress.json" in tree and set(files) <= set(tree)
    assert sum(method == "POST" and path.endswith("/git/blobs") for method, path, _ in service.calls) == 2
    assert sum(method == "PATCH" for method, _, _ in service.calls) == 2


def test_network_retry_and_sanitized_permission_error(files, capsys):
    service = GitService()
    attempts = [0]
    waits = []

    def transient(method, path, body=None):
        attempts[0] += 1
        if attempts[0] <= 2:
            raise http_error(503)
        return service(method, path, body)

    client = upload.GitResultPublisher("synthetic_secret_must_not_be_logged", "example/results",
                                      "research/paper2", requester=transient, sleep=waits.append)
    assert client.publish(files, "Publish")["verified_objects"] == 2
    assert waits == [1, 2]
    assert "synthetic_secret_must_not_be_logged" not in capsys.readouterr().out

    def forbidden(*args):
        raise http_error(403)

    client = upload.GitResultPublisher("synthetic_secret_must_not_be_logged", "example/results",
                                      "research/paper2", requester=forbidden)
    with pytest.raises(upload.UploadError) as error:
        client.publish(files, "Publish")
    assert error.value.status == 403 and "synthetic_secret_must_not_be_logged" not in str(error.value)


def test_full_get_failure_is_recorded_and_other_objects_still_verified(files):
    service = GitService()
    service.corrupt_blob = upload.git_blob_sha(next(iter(files.values())).read_bytes())
    result = publisher(service).publish(files, "Publish")
    assert result["status"] == "verification_failed"
    assert result["verified_objects"] == 1
    assert result["failed_objects"] == [next(iter(files))]
    assert len(result["objects"]) == 2
    service.corrupt_blob = None
    assert publisher(service).publish(files, "Publish")["verified_objects"] == 2


def test_truncated_tree_uses_fixed_commit_metadata_for_idempotence(files):
    service = GitService()
    publisher(service).publish(files, "Publish")
    service.calls.clear()
    service.truncated = True
    result = publisher(service).publish(files, "Publish")
    assert result["status"] == "already_uploaded"
    assert sum("/contents/" in path for _, path, _ in service.calls) == 2
    assert not any(method == "POST" for method, _, _ in service.calls)


@pytest.mark.parametrize("bad", ["../secret", "/absolute", "a/../b", "a\\b", "a//b"])
def test_unsafe_paths_fail_before_any_network(tmp_path, bad):
    local = tmp_path / "payload"
    local.write_bytes(b"synthetic")
    service = GitService()
    with pytest.raises(ValueError, match="Unsafe repository"):
        publisher(service).publish({bad: local}, "Publish")
    assert service.calls == []


def test_exhausted_network_attempts_are_bounded_and_do_not_publish(files):
    calls = []
    waits = []
    def network_failure(method, path, body=None):
        calls.append(method)
        raise TimeoutError("synthetic_secret_must_not_be_logged")
    client = upload.GitResultPublisher("synthetic", "example/results", "research/paper2",
                                      requester=network_failure, sleep=waits.append)
    with pytest.raises(upload.UploadError, match="after three attempts"):
        client.publish(files, "Publish")
    assert calls == ["GET"] * 3 and waits == [1, 2]


def test_permission_403_does_not_pause_or_retry(files, capsys):
    calls, waits = [], []

    def forbidden(method, path, body=None):
        calls.append(method)
        raise http_error(403)

    client = upload.GitResultPublisher("synthetic_secret_must_not_be_logged", "example/results",
                                      "research/paper2", requester=forbidden, sleep=waits.append)
    with pytest.raises(upload.UploadError) as error:
        client.publish(files, "Publish")
    assert calls == ["GET"] and waits == []
    assert error.value.status == 403
    assert "synthetic_secret_must_not_be_logged" not in str(error.value) + capsys.readouterr().out


def test_rate_limit_403_retries_with_capped_delay_and_sanitized_events(files, capsys):
    service = GitService()
    attempts, waits = [0], []

    def limited(method, path, body=None):
        attempts[0] += 1
        if attempts[0] <= 2:
            headers = {"Retry-After": "999"} if attempts[0] == 1 else {"X-RateLimit-Remaining": "0"}
            raise urllib.error.HTTPError("https://api.github.com/mock", 403,
                                         "synthetic_secret_must_not_be_logged", headers, None)
        return service(method, path, body)

    client = upload.GitResultPublisher("synthetic_secret_must_not_be_logged", "example/results",
                                      "research/paper2", requester=limited, sleep=waits.append)
    assert client.publish(files, "Publish")["verified_objects"] == 2
    assert waits == [30, 2] and all(value <= 30 for value in waits)
    output = capsys.readouterr().out
    assert '"http_status": 403' in output and '"delay_seconds": 30' in output
    assert "synthetic_secret_must_not_be_logged" not in output
