"""Atomic GitHub publication and full readback of prepared result files.

Standard library only. This module never trains, reads EEG, creates credentials,
or selects files: the caller supplies an explicit prepared payload mapping.
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import time
import urllib.error
import urllib.parse
import urllib.request


class UploadError(RuntimeError):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def git_blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


class GitResultPublisher:
    """Publish all supplied paths in one non-forced commit, then GET every blob.

    An injected requester has signature ``(method, API_path, body=None) -> dict``.
    ``publish`` returns a receipt even when individual post-commit GETs fail;
    callers must inspect ``failed_objects`` before reporting success.
    """

    def __init__(self, token, repository, branch, requester=None, sleep=time.sleep):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ValueError("Expected owner/repository")
        if not branch or any(ord(c) < 32 for c in branch):
            raise ValueError("Expected a nonempty Git branch")
        self._token = token
        self.repository, self.branch = repository, branch
        self._root = "/repos/" + repository
        self._ref = "heads/" + urllib.parse.quote(branch, safe="/")
        self._requester = requester or self._http
        self._sleep = sleep

    def _http(self, method, path, body=None):
        headers = {"Authorization": "Bearer " + self._token,
                   "Accept": "application/vnd.github+json",
                   "User-Agent": "paper2-existing-result-export",
                   "X-GitHub-Api-Version": "2022-11-28"}
        data = None if body is None else json.dumps(body, allow_nan=False).encode()
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request("https://api.github.com" + path,
                                         headers=headers, data=data, method=method)
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)

    def _request(self, method, path, body=None):
        for attempt in range(3):
            status = None
            delay = attempt + 1
            try:
                result = self._requester(method, path, body)
                if not isinstance(result, dict):
                    raise UploadError("Invalid GitHub JSON response")
                return result
            except urllib.error.HTTPError as error:
                status = error.code
                headers = error.headers or {}
                retry_after = headers.get("Retry-After")
                rate_limited = status == 403 and (
                    retry_after is not None or headers.get("X-RateLimit-Remaining") == "0")
                if status not in (408, 429, 500, 502, 503, 504) and not rate_limited:
                    raise UploadError("GitHub HTTP " + str(status), status) from None
                if rate_limited and retry_after is not None:
                    try:
                        delay = min(30, max(1, float(retry_after)))
                    except (TypeError, ValueError):
                        pass
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
                pass
            except (ValueError, UnicodeError):
                raise UploadError("Invalid GitHub JSON response") from None
            if attempt == 2:
                raise UploadError("GitHub network request failed after three attempts", status)
            print(json.dumps({"event": "github_network_retry", "operation": method,
                              "attempt": attempt + 2, "http_status": status,
                              "delay_seconds": delay}), flush=True)
            self._sleep(delay)
        raise AssertionError("unreachable")

    def _head(self, paths):
        ref = self._request("GET", self._root + "/git/ref/" + self._ref)
        commit = ref["object"]["sha"]
        tree = self._request("GET", self._root + "/git/commits/" + commit)["tree"]["sha"]
        listing = self._request("GET", self._root + "/git/trees/" + tree + "?recursive=1")
        existing = {row["path"]: row["sha"] for row in listing.get("tree", [])
                    if row.get("type") == "blob"}
        if listing.get("truncated"):
            # Query only requested paths if the repository tree is too large.
            for path in paths:
                try:
                    row = self._request("GET", self._root + "/contents/" +
                                        urllib.parse.quote(path, safe="/") + "?ref=" + commit)
                    existing[path] = row["sha"]
                except UploadError as error:
                    if error.status != 404:
                        raise
                    existing.pop(path, None)
        return commit, tree, existing

    @staticmethod
    def _payloads(files):
        result = {}
        for path, local in sorted(files.items()):
            parsed = PurePosixPath(path)
            if (not path or parsed.is_absolute() or "\\" in path
                    or any(p in ("", ".", "..") for p in path.split("/"))):
                raise ValueError("Unsafe repository result path")
            data = Path(local).read_bytes()
            result[path] = {"data": data, "bytes": len(data),
                            "sha256": hashlib.sha256(data).hexdigest(),
                            "git_blob_sha1": git_blob_sha(data)}
        if not result:
            raise ValueError("No prepared result files supplied")
        return result

    def _verify(self, commit, payloads, status):
        objects, failures = [], []
        for path, value in payloads.items():
            row = {"path": path, **{k: value[k] for k in ("bytes", "sha256", "git_blob_sha1")},
                   "full_get_verified": False}
            try:
                result = self._request("GET", self._root + "/git/blobs/" + value["git_blob_sha1"])
                if result.get("encoding") != "base64":
                    raise UploadError("GitHub blob GET was not base64")
                encoded = "".join(result.get("content", "").split())
                data = base64.b64decode(encoded, validate=True)
                if (len(data) != value["bytes"] or result.get("size") != len(data)
                        or result.get("sha") != value["git_blob_sha1"]
                        or git_blob_sha(data) != value["git_blob_sha1"]
                        or hashlib.sha256(data).hexdigest() != value["sha256"]):
                    raise UploadError("GitHub full blob GET length/SHA mismatch")
                row["full_get_verified"] = True
            except (UploadError, ValueError, TypeError) as error:
                row.update(error_type=type(error).__name__, http_status=getattr(error, "status", None))
                failures.append(path)
            objects.append(row)
            print(json.dumps({"event": "github_full_get", "path": path,
                              "verified": row["full_get_verified"]}), flush=True)
        return {"status": "verification_failed" if failures else status,
                "repository": self.repository, "branch": self.branch, "commit": commit,
                "objects": objects, "object_count": len(objects),
                "total_bytes": sum(v["bytes"] for v in objects),
                "verified_objects": sum(v["full_get_verified"] for v in objects),
                "failed_objects": failures, "force_push_used": False}

    def publish(self, files, message):
        payloads = self._payloads(files)
        uploaded = set()
        for attempt in range(3):
            parent, tree, existing = self._head(payloads)
            changed = [p for p, v in payloads.items() if existing.get(p) != v["git_blob_sha1"]]
            if not changed:
                return self._verify(parent, payloads, "already_uploaded")
            for path in changed:
                value = payloads[path]
                sha = value["git_blob_sha1"]
                if sha not in uploaded:
                    result = self._request("POST", self._root + "/git/blobs", {
                        "encoding": "base64", "content": base64.b64encode(value["data"]).decode()})
                    if result.get("sha") != sha:
                        raise UploadError("GitHub created a blob with an unexpected SHA")
                    uploaded.add(sha)
                print(json.dumps({"event": "github_blob_ready", "path": path,
                                  "bytes": value["bytes"]}), flush=True)
            entries = [{"path": p, "mode": "100644", "type": "blob",
                        "sha": payloads[p]["git_blob_sha1"]} for p in changed]
            result = self._request("POST", self._root + "/git/trees", {"base_tree": tree, "tree": entries})
            result = self._request("POST", self._root + "/git/commits", {
                "message": message, "tree": result["sha"], "parents": [parent]})
            commit = result["sha"]
            try:
                self._request("PATCH", self._root + "/git/refs/" + self._ref,
                              {"sha": commit, "force": False})
                return self._verify(commit, payloads, "uploaded")
            except UploadError as error:
                if error.status not in (409, 422) or attempt == 2:
                    raise
                print(json.dumps({"event": "github_branch_advanced", "rebase_attempt": attempt + 2}), flush=True)
                self._sleep(attempt + 1)
        raise AssertionError("unreachable")
