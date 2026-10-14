"""Validate the frozen development queue plan; cannot execute a fit."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check():
    p = json.loads((ROOT / "configs/kumar_development_queue_plan_20261014.json").read_text())
    assert not p["execution_enabled"] and not p["query_access"]
    assert not p["formal_non_development_gate"]
    config_path = ROOT / p["training_config"]
    assert hashlib.sha256(config_path.read_bytes()).hexdigest() == p["training_config_sha256"]
    c = json.loads(config_path.read_text())
    assert p["development_subjects"] == c["development_subjects"]
    assert p["seeds"] == c["seeds"]
    assert {(j["subject"], j["seed"]) for j in p["jobs"]} == {
        (s, seed) for s in c["development_subjects"] for seed in c["seeds"]
    }
    assert len(p["jobs"]) == len({j["job_id"] for j in p["jobs"]}) == 18
    reused = [j for j in p["jobs"] if j["action"] == "reuse_completed_never_refit"]
    assert [(j["subject"], j["seed"]) for j in reused] == [("sub-1", 20261012)]
    assert sum(j["action"] == "planned_not_authorized_to_execute" for j in p["jobs"]) == 17
    split_sha = hashlib.sha256((ROOT / c["split_manifest"]).read_bytes()).hexdigest()
    for job in p["jobs"]:
        identity = {
            k: job[k] for k in ("subject", "seed", "training_config_sha256", "split_sha256")
        }
        assert identity["training_config_sha256"] == p["training_config_sha256"]
        assert identity["split_sha256"] == split_sha
        assert (
            job["job_id"]
            == hashlib.sha256(
                json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
        )
    manifest = ROOT / p["data_manifest"]
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == p["data_manifest_sha256"]
    data = json.loads(manifest.read_text())["files"]
    edf = [f["relative_path"] for f in data if f["relative_path"].endswith(".edf")]
    assert len(data) == 127 and sum(f["bytes"] for f in data) == 98743492
    assert len(edf) == 18
    for s in c["development_subjects"]:
        assert sorted(f for f in edf if f.startswith(s + "/")) == [
            f"{s}/ses-0/eeg/{s}_ses-0_task-imagery_run-{i}_eeg.edf" for i in range(3)
        ]
    print(
        json.dumps(
            dict(
                status="plan_valid_execution_closed",
                jobs=18,
                reused=1,
                new_fits_max=17,
                query_access=False,
                data_files=127,
                data_bytes=98743492,
            )
        )
    )


if __name__ == "__main__":
    check()
