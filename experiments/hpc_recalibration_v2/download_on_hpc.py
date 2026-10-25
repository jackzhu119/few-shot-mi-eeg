#!/usr/bin/env python3
"""Download pinned public artifacts directly on login1, then run the installer.

Standard library only. HTTP retries apply to downloads, never to training.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import http.client
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request


RAW = "https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/"
DATA_COMMIT = "b971e79dbf5bf8a1452634046b6e186fe298b6a9"
CODE_COMMIT = "cddb6aa2b73a169e5386ff981d93fd6f6bf43f28"
RELEASE = "releases/paper2-hpc-v2-20261023/"
MANIFEST_URL = RAW + DATA_COMMIT + "/" + RELEASE + "input_download_manifest.json"
MANIFEST_CONTENT_SHA256 = "57be5ea4637ff5a7dc42869c2504ab231004a967628d1ec41b7b06ca18139310"
ARTIFACTS = (
    {"file": "paper2-hpc-v2-code.tar.gz", "bytes": 86282,
     "sha256": "dd6fa2f293943d8b574655bc6f74c5b5d73b6559f5853d709515240c19fdc8ce"},
    {"file": "install_offline.sh", "bytes": 2049,
     "sha256": "3476346c1c71c92b91517aafdb08803a06a85b09de06f7c9562f6012f4fac508"},
)
RUNTIME_COMMIT = "57571a93a020e4c4c75ccbdcbbd51350b8393239"
RUNTIME_ARTIFACTS = ({'file': 'submit.py', 'bytes': 12506, 'sha256': '663b32225cc4c97c4d3bad136214780d9c5b4e8b11841b30bc237d7a74fd274c'}, {'file': 'controller.py', 'bytes': 12566, 'sha256': '0ceb49a52db626cc3674a2b96e56cc2caa0fb2ce8570df9e5672e7ae433eb884'}, {'file': 'job.sh', 'bytes': 2695, 'sha256': '08fe7596b00ef68183293b783c8244b77ebae215b37d8226b29bdd21484f503c'}, {'file': 'switch.py', 'bytes': 15705, 'sha256': '7d1d3f56134d81643fd4b2a8444111ce22e777b1974e07cbb5d6cba64ec6846a'})


class DownloadError(RuntimeError):
    pass


class _RetryableNetwork(Exception):
    pass


def _https(url):
    if urllib.parse.urlsplit(url).scheme != "https":
        raise DownloadError("Only verified HTTPS download URLs are accepted")
    return url


def to_official_candidates(url):
    """Keep the pinned canonical URL; API raw media is a separate official host."""
    _https(url)
    parsed = urllib.parse.urlsplit(url)
    parts = parsed.path.lstrip("/").split("/", 3)
    if (parsed.hostname == "raw.githubusercontent.com" and len(parts) == 4
            and not parsed.query and not parsed.fragment):
        owner, repository, ref, path = parts
        api = ("https://api.github.com/repos/" + owner + "/" + repository
               + "/contents/" + path + "?ref=" + urllib.parse.quote(ref, safe=""))
        return (api, url)
    return (url,)


def _timeout():
    try:
        seconds = float(os.environ.get("PAPER2_DOWNLOAD_TIMEOUT_SECONDS", "30"))
    except ValueError:
        raise DownloadError("PAPER2_DOWNLOAD_TIMEOUT_SECONDS must be positive") from None
    if not 0 < seconds < float("inf"):
        raise DownloadError("PAPER2_DOWNLOAD_TIMEOUT_SECONDS must be positive")
    return seconds


def _headers(url, offset=0):
    headers = {"User-Agent": "paper2-hpc-direct-download", "Accept-Encoding": "identity"}
    if urllib.parse.urlsplit(url).hostname == "api.github.com":
        headers["Accept"] = "application/vnd.github.raw+json"
    if offset:
        headers["Range"] = "bytes=" + str(offset) + "-"
    return headers


def _network_call(call, url):
    """Classify network operations only; storage calls never pass through here."""
    try:
        return call()
    except urllib.error.HTTPError as error:
        api = urllib.parse.urlsplit(url).hostname == "api.github.com"
        if error.code in (408, 429, 500, 502, 503, 504) or (api and error.code in (401, 403)):
            raise _RetryableNetwork("HTTP " + str(error.code)) from None
        raise DownloadError("Download HTTP " + str(error.code) + "; fixed source unavailable; no file overwritten") from None
    except ssl.SSLCertVerificationError:
        raise DownloadError("TLS certificate verification failed; configure the trusted system/campus CA bundle") from None
    except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.IncompleteRead) as error:
        if isinstance(getattr(error, "reason", None), ssl.SSLCertVerificationError):
            raise DownloadError("TLS certificate verification failed; configure the trusted system/campus CA bundle") from None
        raise _RetryableNetwork(type(error).__name__) from None


def _connecting(url, filename, attempt, offset):
    print(json.dumps({"file": filename, "status": "connecting",
                      "host": urllib.parse.urlsplit(url).hostname,
                      "attempt": attempt + 1, "offset_bytes": offset}), flush=True)


def _sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _stamp(path):
    stat = Path(path).stat()
    return {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns,
            "inode": stat.st_ino, "device": stat.st_dev}


def _atomic_json(path, value):
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _receipt(path):
    return path.with_name("." + path.name + ".download.json")


def verified_existing(path, spec):
    """Stat-only reuse after a successful original SHA check."""
    if not path.exists():
        return False
    expected = {"bytes": int(spec["bytes"]), "sha256": spec["sha256"]}
    receipt = _receipt(path)
    if receipt.is_file():
        try:
            old = json.loads(receipt.read_text())
            if old.get("expected") == expected and old.get("stat") == _stamp(path):
                return True
        except (OSError, ValueError):
            pass
    if path.stat().st_size != expected["bytes"] or _sha(path) != expected["sha256"]:
        raise DownloadError("Existing file differs; preserved without overwrite: " + path.name)
    _atomic_json(receipt, {"expected": expected, "stat": _stamp(path)})
    return True


def _publish(partial, destination, spec):
    if partial.stat().st_size != int(spec["bytes"]) or _sha(partial) != spec["sha256"]:
        raise DownloadError("Length/SHA256 mismatch; partial retained: " + destination.name)
    os.replace(partial, destination)
    _atomic_json(_receipt(destination), {
        "expected": {"bytes": int(spec["bytes"]), "sha256": spec["sha256"]},
        "stat": _stamp(destination)})


def download(url, destination, spec, *, opener=None, sleep=time.sleep):
    """Three bounded network attempts; retain resumable .part and old finals."""
    opener = opener or urllib.request.urlopen
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if verified_existing(destination, spec):
        print(json.dumps({"file": destination.name, "status": "already_verified"}), flush=True)
        return
    _https(url)
    partial = destination.with_name(destination.name + ".part")
    expected = int(spec["bytes"])
    candidates = to_official_candidates(url)
    # Raw supports Range; the Contents API returns the full file with HTTP200.
    if partial.exists() and partial.stat().st_size and len(candidates) > 1:
        candidates = tuple(reversed(candidates))
    timeout = _timeout()
    for attempt in range(3):
        offset = partial.stat().st_size if partial.exists() else 0
        if offset > expected:
            raise DownloadError("Oversized partial retained: " + destination.name)
        if offset == expected:
            _publish(partial, destination, spec)
            return
        current = candidates[attempt % len(candidates)]
        _connecting(current, destination.name, attempt, offset)
        try:
            request = urllib.request.Request(current, headers=_headers(current, offset))
            with _network_call(lambda: opener(request, timeout=timeout), current) as response:
                _https(response.geturl())
                status = response.status
                if status not in (200, 206):
                    raise DownloadError("Unexpected download HTTP status: " + str(status))
                if status == 206:
                    content_range = response.headers.get("Content-Range", "")
                    try:
                        unit, interval = content_range.split(" ", 1)
                        span, total = interval.split("/")
                        start, end = (int(s) for s in span.split("-"))
                        valid = unit == "bytes" and start == offset and int(total) == expected and start <= end < expected
                    except ValueError:
                        valid = False
                    if not valid:
                        raise DownloadError("Incorrect HTTP Range response; partial retained")
                else:
                    # A server that ignores Range returned the full object.
                    offset = 0
                mode = "ab" if offset else "wb"
                processed = offset
                next_report = processed + 8 * 1024 * 1024
                print(json.dumps({"file": destination.name, "status": "downloading",
                                  "resumed_bytes": offset, "attempt": attempt + 1}), flush=True)
                with partial.open(mode) as stream:
                    while True:
                        block = _network_call(lambda: response.read(1024 * 1024), current)
                        if not block:
                            break
                        if processed + len(block) > expected:
                            raise DownloadError("Download exceeds declared bytes; partial retained")
                        stream.write(block)
                        processed += len(block)
                        if processed >= next_report:
                            print(json.dumps({"file": destination.name, "bytes": processed,
                                              "total_bytes": expected}), flush=True)
                            next_report = processed + 8 * 1024 * 1024
                    stream.flush()
                    os.fsync(stream.fileno())
                if processed < expected:
                    raise _RetryableNetwork("Incomplete response")
            _publish(partial, destination, spec)
            print(json.dumps({"file": destination.name, "status": "sha256_verified",
                              "bytes": expected}), flush=True)
            return
        except _RetryableNetwork as error:
            print(json.dumps({"file": destination.name, "status": "connection_failed",
                              "host": urllib.parse.urlsplit(current).hostname,
                              "attempt": attempt + 1, "reason": str(error)}), flush=True)
        if attempt < 2:
            sleep(2 ** attempt)
    raise DownloadError("Network download failed after three attempts; rerun the same command to resume")


def read_manifest(url, *, opener=None, sleep=time.sleep):
    opener = opener or urllib.request.urlopen
    candidates = to_official_candidates(url)
    timeout = _timeout()
    for attempt in range(3):
        current = candidates[attempt % len(candidates)]
        _connecting(current, "input_manifest", attempt, 0)
        try:
            request = urllib.request.Request(current, headers=_headers(current))
            with _network_call(lambda: opener(request, timeout=timeout), current) as response:
                _https(response.geturl())
                payload = _network_call(lambda: response.read(1024 * 1024), current)
                value = json.loads(payload)
            if value.get("schema_version") != 1 or not value.get("input", {}).get("parts"):
                raise DownloadError("Unrecognized input download manifest")
            return value
        except _RetryableNetwork as error:
            print(json.dumps({"file": "input_manifest", "status": "connection_failed",
                              "host": urllib.parse.urlsplit(current).hostname,
                              "attempt": attempt + 1, "reason": str(error)}), flush=True)
            if attempt == 2:
                raise DownloadError("Could not download input manifest; rerun the same command") from None
            sleep(2 ** attempt)


def assemble(parts, destination, spec):
    if verified_existing(destination, spec):
        return
    partial = destination.with_name(destination.name + ".assembling")
    with partial.open("wb") as outgoing:
        for source in parts:
            with source.open("rb") as incoming:
                shutil.copyfileobj(incoming, outgoing, 1024 * 1024)
        outgoing.flush()
        os.fsync(outgoing.fileno())
    _publish(partial, destination, spec)
    print(json.dumps({"file": destination.name, "status": "assembled_sha256_verified",
                      "bytes": int(spec["bytes"])}), flush=True)


def prepare(incoming, manifest_url=MANIFEST_URL, *, opener=None):
    incoming = Path(incoming)
    incoming.mkdir(parents=True, exist_ok=True)
    for spec in ARTIFACTS:
        download(RAW + CODE_COMMIT + "/" + RELEASE + spec["file"],
                 incoming / spec["file"], spec, opener=opener)
    cache = incoming / ".paper2-input-manifest.json"
    manifest = None
    if manifest_url == MANIFEST_URL and cache.is_file():
        cached = json.loads(cache.read_bytes())
        digest = hashlib.sha256(json.dumps(cached, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if digest == MANIFEST_CONTENT_SHA256:
            manifest = cached
    if manifest is None:
        manifest = read_manifest(manifest_url, opener=opener)
        if manifest_url == MANIFEST_URL:
            digest = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            if digest != MANIFEST_CONTENT_SHA256:
                raise DownloadError("Frozen input manifest SHA256 mismatch")
            _atomic_json(cache, manifest)
    spec = manifest["input"]
    if Path(spec["file"]).name != spec["file"]:
        raise DownloadError("Invalid input archive filename")
    final = incoming / spec["file"]
    if verified_existing(final, spec):
        return final
    parts = []
    for part in spec["parts"]:
        relative = PurePosixPath(part["file"])
        if relative.is_absolute() or ".." in relative.parts or "\\" in part["file"]:
            raise DownloadError("Invalid part filename")
        path = incoming / relative
        download(urllib.parse.urljoin(manifest_url, part["file"]), path, part, opener=opener)
        parts.append(path)
    assemble(parts, final, spec)
    return final


def prepare_profile(project_dir, token_file=None) -> Path:
    """Apply resource/credential-path choices without changing scientific files."""
    project = Path(project_dir).expanduser().resolve()
    original = project / "configs" / "kumar_dev.json"
    original_bytes = original.read_bytes()
    config = json.loads(original_bytes)
    slurm = config.setdefault("slurm", {})
    resource_changes = {"partition": "hpc_gpu1", "gres": "gpu:1", "exclude": "",
                        "cpus_per_task": 12, "mem": "64G", "array_parallel": 2,
                        "submission_mode": "single_pool", "pool_workers": 2}
    before = {key: slurm.get(key) for key in resource_changes}
    slurm.update(resource_changes)
    credential_path = None
    if token_file is not None:
        candidate = Path(token_file).expanduser().resolve()
        if candidate.is_file():
            credential_path = str(candidate)
            config.setdefault("git_sync", {})["token_file"] = credential_path
    destination = original.with_name("kumar_dev_hpc_gpu1_24cpu.json")
    if not destination.is_file() or json.loads(destination.read_bytes()) != config:
        _atomic_json(destination, config)
    payload = destination.read_bytes()
    provenance = {"schema_version": 1, "profile": "school_hpc_gpu1",
                  "base_config": str(original),
                  "base_sha256": hashlib.sha256(original_bytes).hexdigest(),
                  "effective_config": str(destination),
                  "effective_sha256": hashlib.sha256(payload).hexdigest(),
                  "slurm_before": before, "slurm_after": resource_changes,
                  "token_file": credential_path, "token_value_read_or_recorded": False,
                  "scientific_configuration_changed": False,
                  "gpu_model_inferred_from_partition_screenshot": False}
    receipt = destination.with_suffix(".provenance.json")
    if not receipt.is_file() or json.loads(receipt.read_bytes()) != provenance:
        _atomic_json(receipt, provenance)
    return destination


def install_runtime_bundle(project_dir, incoming, *, opener=None):
    """Install immutable extra runtime files; leave the sealed code pack intact."""
    if not RUNTIME_ARTIFACTS or RUNTIME_COMMIT == "PENDING":
        raise DownloadError("Single-job runtime is not versioned")
    project = Path(project_dir).expanduser().resolve()
    destination = project / ".hpc_runtime" / RUNTIME_COMMIT
    staged = []
    for spec in RUNTIME_ARTIFACTS:
        cached = Path(incoming) / "runtime" / (spec["sha256"] + "-" + spec["file"])
        url = RAW + RUNTIME_COMMIT + "/experiments/hpc_recalibration_v2/single_pool/" + spec["file"]
        download(url, cached, spec, opener=opener)
        staged.append((spec, cached))
    destination.mkdir(parents=True, exist_ok=True)
    for spec, cached in staged:
        target = destination / spec["file"]
        if target.exists():
            if target.stat().st_size != spec["bytes"] or _sha(target) != spec["sha256"]:
                raise DownloadError("Installed versioned runtime differs: " + target.name)
            continue
        fd, temporary = tempfile.mkstemp(prefix="." + target.name + ".", dir=destination)
        try:
            with os.fdopen(fd, "wb") as outgoing, cached.open("rb") as source:
                shutil.copyfileobj(source, outgoing)
                outgoing.flush()
                os.fsync(outgoing.fileno())
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    _atomic_json(destination / "runtime_manifest.json", {
        "source_commit": RUNTIME_COMMIT, "artifacts": list(RUNTIME_ARTIFACTS),
        "original_code_package_modified": False, "scientific_configuration_changed": False})
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--incoming", default="/public/home/zhuziyuan/incoming")
    parser.add_argument("--project-dir", default="/public/home/zhuziyuan/projects/paper2-recalibration-v2")
    parser.add_argument("--manifest-url", default=MANIFEST_URL)
    parser.add_argument("--token-file", default=os.environ.get("PAPER2_GITHUB_TOKEN_FILE"))
    parser.add_argument("--switch-job", help="Move this project's existing job; preserve checkpoints and require manual GitHub authorization")
    parser.add_argument("--download-only", action="store_true")
    parser.add_argument("--no-launch", action="store_true")
    args = parser.parse_args()
    incoming = Path(args.incoming).expanduser().resolve()
    incoming.mkdir(parents=True, exist_ok=True)
    with (incoming / ".paper2-direct-download.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        prepare(incoming, args.manifest_url)
    if not args.download_only:
        env = os.environ.copy()
        env.update(HPC_V2_INCOMING=str(incoming), HPC_V2_PROJECT_DIR=args.project_dir,
                   HPC_V2_PYTHON=sys.executable)
        # Installation is kept separate so the old packaged default cannot
        # submit to the original partition before this resource profile applies.
        code = subprocess.call(["bash", str(incoming / "install_offline.sh"), "--no-launch"], env=env)
        if code:
            return code
        profile = prepare_profile(args.project_dir, args.token_file)
        runtime = install_runtime_bundle(args.project_dir, incoming)
        print(json.dumps({"status": "runtime_profile_ready", "config": str(profile),
                          "partition": "hpc_gpu1", "gpus_per_task": 1,
                          "cpu_per_task": 12, "memory_per_task": "64G",
                          "submission_mode": "single_pool", "slurm_jobs": 1,
                          "pool_workers": 2, "total_cpus": 24, "total_memory": "128G",
                          "runtime": str(runtime)}), flush=True)
        if not args.no_launch:
            command = [sys.executable, "-u", str(runtime / "switch.py"), "--config", str(profile)]
            if args.switch_job:
                command.extend(["--job-id", args.switch_job])
            return subprocess.call(command, env=env)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DownloadError as error:
        print(str(error), file=sys.stderr, flush=True)
        raise SystemExit(1)
