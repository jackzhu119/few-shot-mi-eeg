"""Publish saved V3 results only, with resumable packets and full GitHub readback.

No model or EEG is loaded. Scientific acceptance remains a separate operation.
"""
from __future__ import annotations

import datetime as dt
import fcntl
import hashlib
import json
from pathlib import Path
import re
import tempfile

from export_saved_results import atomic_bytes, atomic_json, copy_public, digest, make_packet, stamp
from github_result_upload import GitResultPublisher

VERSION = "paper2-v3-saved-results-20261026"
PREDICTION_KEYS = {"probabilities", "labels", "classes", "trial_id", "run_id"}
TEXT_SUFFIXES = {".out", ".err", ".log", ".txt", ".md", ".csv"}


def emit(event, **values):
    print(json.dumps({"event": event, **values}), flush=True)


def _tasks(config):
    value = config.get("tasks")
    if value is None:
        value = json.loads(Path(config["tasks_file"]).read_text())
    tasks = value["tasks"] if isinstance(value, dict) else value
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("A declared V3 task list is required")
    names = [t["task_id"] for t in tasks]
    if len(set(names)) != len(names) or any(not re.fullmatch(r"[A-Za-z0-9_.-]+", name)
                                         or name in (".", "..") for name in names):
        raise ValueError("Invalid declared task identity")
    return tasks


def _inventory(config):
    project, output = Path(config["project_dir"]).resolve(), Path(config["output_root"]).resolve()
    tasks = _tasks(config)
    entries, issues = [], []
    completed = []
    paths = set()
    for task in tasks:
        folder = output / "tasks" / task["task_id"]
        marker = folder / "complete.json"
        try:
            value = json.loads(marker.read_text())
            done = (value.get("task_id") == task["task_id"] and value.get("status") == "completed"
                    and bool(value.get("identity") or value.get("task_identity")))
        except FileNotFoundError:
            done = False
        except (ValueError, UnicodeError):
            done = False
        if done:
            completed.append(task["task_id"])
        else:
            issues.append({"path": "results/tasks/" + task["task_id"] + "/complete.json",
                           "error_type": "task_not_complete_or_marker_invalid"})
        paths.update(p for p in folder.rglob("*") if p.is_file())
    paths.update(p for p in output.iterdir() if p.is_file()
                 and p.suffix in TEXT_SUFFIXES | {".json"})
    for name in ("logs", "analysis", "summary", "model_diagnostics"):
        paths.update(p for p in (output / name).rglob("*") if p.is_file())
    # Avoid monitor/publication self-references that would change each packet
    # every time its own export receipt is updated.
    for p in (output / ".runtime").glob("*.json"):
        if not p.name.startswith(("monitor", "publish", "export", "github", "last_upload", "last_publish")):
            paths.add(p)
    for path in sorted(paths):
        if path.is_symlink() or not path.resolve().is_relative_to(output):
            raise ValueError("Result symlink is not followed: " + str(path))
        kind = ("predictions" if path.name == "predictions.npz" else "json" if path.suffix == ".json"
                else "text" if path.suffix in TEXT_SUFFIXES else "model" if path.suffix in (".pt", ".npz")
                else "excluded")
        entries.append({"path": str(path), "target": "results/" + path.relative_to(output).as_posix(),
                        "kind": kind, "stat": stamp(path)})
    sources = set(project.glob("*.py")) | set(project.glob("*.sh"))
    for name in ("configs", "hpc_recalibration", "hpc_recalibration_v3", "LICENSES"):
        sources.update(p for p in (project / name).rglob("*") if p.is_file()
                       and p.suffix in (".py", ".sh", ".json", ".md", ".txt"))
    sources.update(project / name for name in
                   ("LICENSE", "NOTICE.md", "DATA_ATTRIBUTION.txt", "PACKAGE_MANIFEST.json"))
    actual_config = Path(config["_config_path"]).resolve()
    sources.add(actual_config)
    for path in sorted(sources):
        if not path.is_file():
            continue
        if path.is_symlink():
            raise ValueError("Source symlink is not followed")
        relative = (path.relative_to(project).as_posix() if path.is_relative_to(project)
                    else "actual_configuration.json" if path == actual_config else None)
        if relative is None:
            raise ValueError("Unexpected source provenance path")
        entries.append({"path": str(path), "target": "source_code/" + relative,
                        "kind": "json" if path.suffix == ".json" else "text", "stat": stamp(path)})
    return tasks, completed, entries, issues


def _model_inventory(entry, destination):
    key = hashlib.sha256(json.dumps(entry, sort_keys=True).encode()).hexdigest()
    cache = destination / "model_hash_cache" / (key + ".json")
    if cache.is_file():
        return json.loads(cache.read_text())
    path = Path(entry["path"])
    if stamp(path) != entry["stat"]:
        raise RuntimeError("Saved model changed during export")
    result = {"path": entry["target"], "bytes": entry["stat"]["bytes"],
              "sha256": digest(path), "reason": "model_binary_retained_locally"}
    if stamp(path) != entry["stat"]:
        raise RuntimeError("Saved model changed while hashing")
    atomic_json(cache, result)
    return result


def _packet_metadata(destination, packet):
    status = packet["export_status"]
    text = ("# Saved V3 results\n\nPacket `" + packet["packet_id"] + "`; status `" + status + "`.\n\n"
            "Only saved V3 result JSON, five-key prediction NPZ, logs, analysis and source provenance are included. "
            "Model binaries, EEG inputs, token files and optimizer tensors remain local. No Torch checkpoint load, fit or forward occurred.\n\n"
            "Join archive parts in packet_manifest.json order; verify combined archive bytes/SHA256, then verify every extracted payload against paper2_results/MANIFEST.json. "
            "Tasks marked complete are not thereby independently audited or accepted.\n")
    atomic_bytes(destination / "README.md", text.encode())
    atomic_json(destination / "packet_manifest.json", {k:v for k,v in packet.items() if k!="upload_files"})


def prepare_bundle(config):
    """Caller serializes preparation/publication; unchanged outputs reuse packet."""
    destination = Path(config["output_root"]).resolve() / "exports" / VERSION
    destination.mkdir(parents=True, exist_ok=True)
    tasks, completed, entries, issues = _inventory(config)
    fingerprint = hashlib.sha256(json.dumps({"version": VERSION, "entries": entries,
        "tasks": tasks, "completed": completed, "issues": issues}, sort_keys=True).encode()).hexdigest()
    cache = destination / "prepared_packet.json"
    if cache.is_file():
        prior = json.loads(cache.read_text())
        if prior["fingerprint"] == fingerprint:
            for row in prior["packet"]["parts"]:
                path = destination / row["file"]
                if path.stat().st_size != row["bytes"] or digest(path) != row["sha256"]:
                    raise RuntimeError("Prepared packet changed; retained for diagnosis")
            _packet_metadata(destination, prior["packet"])
            emit("prepared_packet_reused", packet_id=prior["packet"]["packet_id"])
            return prior["packet"]
    payload = Path(tempfile.mkdtemp(prefix="payload-", dir=destination))
    files, excluded = [], []
    for number, entry in enumerate(entries, 1):
        if entry["kind"] == "model":
            excluded.append(_model_inventory(entry, destination))
        elif entry["kind"] == "excluded":
            excluded.append({"path":entry["target"], "bytes":entry["stat"]["bytes"],
                             "reason":"nonpublic_binary_or_partial"})
        else:
            try:
                files.append(copy_public(entry, payload / entry["target"]))
            except (ValueError, UnicodeError) as error:
                issues.append({"path":entry["target"], "error_type":type(error).__name__,
                               "reason":"invalid_public_result_retained_locally"})
        if number % 50 == 0:
            emit("export_progress", processed=number, total=len(entries))
    status = "complete_exported_unreviewed" if not issues else "partial_exported_unreviewed"
    manifest = {"schema_version":1, "version":VERSION, "experiment_id":config["experiment_id"],
                "tasks":[t["task_id"] for t in tasks], "completed_tasks":completed,
                "files":files, "excluded":excluded, "history_errors":issues,
                "analysis_counts":{"tasks_expected":len(tasks), "tasks_complete":len(completed),
                                   "prediction_files":sum(e["kind"]=="predictions" for e in entries)},
                "export_status":status, "accepted":False, "independently_audited":False,
                "no_training_or_inference":True, "weights_and_eeg_uploaded":False,
                "scope":"Saved own-V3 outputs/source only; completion flags are not scientific acceptance",
                "source_data":"Original dataset rights retained; see source_code/DATA_ATTRIBUTION.txt when supplied"}
    packet = make_packet(payload, destination, manifest)
    # The reused packet builder has a V2-specific README; publish a truthful V3
    # description instead of inheriting its historical result-count assertions.
    packet.update(export_status=status, accepted=False, independently_audited=False)
    _packet_metadata(destination, packet)
    atomic_json(cache, {"fingerprint":fingerprint, "packet":packet})
    emit("packet_prepared", packet_id=packet["packet_id"], export_status=status,
         payload_files=len(files), errors=len(issues))
    return packet


def publish(config, *, publisher_factory=None, token_loader=None):
    """Publish immutable packet + full-GET receipt; errors never invoke science."""
    from hpc_recalibration.github_sync import _load_token, _settings
    destination = Path(config["output_root"]).resolve() / "exports" / VERSION
    destination.mkdir(parents=True, exist_ok=True)
    with (destination / "publish.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        packet = prepare_bundle(config)
        options = _settings(config)
        token = (token_loader or _load_token)(options["token_file"])
        publisher = (publisher_factory or GitResultPublisher)(token, options["repository"], options["branch"])
        prefix = options["status_prefix"] + "/result_exports/" + packet["packet_id"]
        objects = {prefix + "/" + name: destination / name for name in packet["upload_files"]}
        receipt = publisher.publish(objects, "Publish saved paper2 V3 result packet " + packet["packet_id"])
        name = "github_full_get_receipt_" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json"
        path = destination / name
        atomic_json(path, receipt)
        if receipt["failed_objects"]:
            emit("verification_failed", failed_objects=receipt["failed_objects"], local_receipt=str(path))
            return {"status":"verification_failed", "packet_id":packet["packet_id"],
                    "receipt":receipt, "local_receipt":str(path), "accepted":False}
        closing = publisher.publish({prefix + "/" + name:path}, "Record V3 packet full GitHub readback")
        atomic_json(destination / ("readback_" + name), closing)
        result = {"status":"verification_failed" if closing["failed_objects"] else "uploaded_unreviewed",
                  "packet_id":packet["packet_id"], "export_status":packet["export_status"],
                  "data_commit":receipt["commit"], "receipt_commit":closing["commit"],
                  "verified_objects":receipt["verified_objects"], "failed_objects":closing["failed_objects"],
                  "history_errors":packet["history_errors"], "accepted":False,
                  "url":"https://github.com/"+options["repository"]+"/tree/"+options["branch"]+"/"+prefix,
                  "local_directory":str(destination)}
        atomic_json(destination / "last_publication.json", result)
        emit("upload_complete" if result["status"]=="uploaded_unreviewed" else "verification_failed", **result)
        return result
