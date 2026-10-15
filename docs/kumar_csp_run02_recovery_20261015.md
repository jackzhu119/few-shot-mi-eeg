# Single corrected CPU recovery: run02

This delivery prepares run02; it does not start it. Dot approved the procfs repair
at `ad5be8e51e98eebd99ac994a249136e349d2f582` and one bounded recovery, subject
to checking this identity patch. The launcher changes exactly DIAGNOSTIC, OUTPUT
and STATE. All its functions, process monitoring, numerical threads, scientific
consumer and frozen inputs remain byte-equivalent to the reviewed implementation.

- Launcher SHA256: `215ec7ec6cb199f2d70c485969583f9b09cfc8346ed7f316448bc92bfdadbf56`.
- Contract SHA256: `0ec85048e51e1f9d3e7cc0e553544db975ab4b792b3e534a3924c6faaef65157`.
- Consumer SHA256: `ebc866734add9769c7b881332cb9362badaa0f6bf401bc2c6dfa717b645960f3`.
- Recovery binding SHA256: `06ac6ea6f700b3f7e551ff1943f728166349f2a90e1aa4517094730a8d25c306`.
- Original window: 2026-10-15 05:27:00–07:27:00 UTC, epoch 1792042020–1792049220.
  Startup, preflight and receipt work consume that same window; the existing
  launcher reserves up to 30 seconds for TERM cleanup. Never start a new 7200 s timer.
- Sampling stays 0.25 s; maximum sampled tree RSS 2 GiB; cgroup and host
  headroom each 1 GiB; initial effective availability 3 GiB. Zero automatic retries.

Run01 remains a failed attempt with real Python launch, empty recorded consumer
log and no saved scientific results. An empty log does not establish zero Python
execution. Its claim, authorization, failure receipts and private R2 objects are
not rewritten or reused. Its original R2 receipt is 17205 bytes,
SHA256 `b5524eeb9aa945535766dcfdba9dab224cb79b6910182694241adbe2d1f48a29`,
covering 20 objects / 40972 bytes / zero full-GET failures.

## External authorization and invocation

After dot checks the final commit, create a **new external** authorization file
at `/workspace/private_model_receipts/csp-cpu-operation-run02-20261015/actual_external_authorization.json`
using `research_logs/kumar_csp_run02_identity_20261015/external_authorization.template.json`.
Replace only its template status with
`parent_reviewed_csp_signed_score_cpu_execution_authorized` and `reviewed_commit`
with the final 40-character reviewed commit. Reobserve the actual hostname,
boot_id and pid1_start_ticks and require exact equality to the binding. Preserve
the stated decision provenance, recovery_of, original absolute window and all
false permissions. Publish exclusively and compute its complete UTF-8 SHA256.
Do not use the template as actual authorization, reuse run01 authorization, or
create the run02 STATE directory while preparing the authorization.

No balance, bill, currency amount or new spending gate is introduced. The legacy
`cost_authorization` key is kept solely to retain compatibility with the already
reviewed launcher and points to the unchanged historical existing-CPU allocation
receipt. Financial blocking requirements are explicitly `superseded-by-user`;
this does not authorize new allocation, GPU, query, accepted18 refitting or 36 fits.

Use the following **complete** command after dispatch. Set the three positional
arguments to the reviewed commit, external authorization path and its actual
SHA256. The linkage gate below is part of the reviewed command, not a new
native launcher feature. It is tested directly from this fenced block. Do not
bypass it by invoking the launcher alone. It reads only metadata and byte hashes,
then invokes the existing guarded launcher exactly once; the launcher repeats
its existing 42-input/runtime/resource/duplicate checks before any consumer.

```bash
cd /workspace/few-shot-mi-eeg
/workspace/.venvs/few-shot-mi-eeg/bin/python -B - "$REVIEWED_COMMIT" "$RUN02_AUTHORIZATION" "$RUN02_AUTHORIZATION_SHA256" <<'PY'
import importlib.util
import runpy
import subprocess
import sys
from pathlib import Path

BINDING = "research_logs/kumar_csp_run02_identity_20261015/recovery_binding.json"
BINDING_SHA = "06ac6ea6f700b3f7e551ff1943f728166349f2a90e1aa4517094730a8d25c306"


def recovery_gate(operation, root, auth, *, now=None):
    require = operation.require
    require(operation.sha(root / BINDING) == BINDING_SHA, "Recovery binding changed")
    binding = operation.read(root / BINDING)
    prior = binding["recovery_of"]
    for path_key, hash_key in (("launcher_receipt", "launcher_receipt_sha256"),
                               ("claim", "claim_sha256"),
                               ("R2_full_get_receipt", "R2_full_get_receipt_sha256")):
        require(operation.sha(root / prior[path_key]) == prior[hash_key], "Run01 evidence changed")
    failed = operation.read(root / prior["launcher_receipt"])
    require(failed["status"] == "launcher_failed_preserved"
            and failed["diagnostic_id"] == prior["diagnostic_id"]
            and failed["authorization_sha256"] == prior["authorization_sha256"], "Run01 failure identity changed")
    require(auth.get("recovery_of") == prior and auth.get("recovery_binding_sha256") == BINDING_SHA,
            "Actual authorization must link the original failed attempt")
    require(operation.container_identity() == binding["container_identity"] == failed["container_identity"]
            == auth.get("container_identity"), "Recovery host changed")
    require(all(auth.get(key) == binding[key] for key in
                ("not_before_unix", "deadline_unix", "approved_wall_seconds"))
            and auth["deadline_unix"] == failed["absolute_deadline_unix"], "Original window changed")
    require(operation.DIAGNOSTIC == binding["diagnostic_id"] == auth.get("diagnostic_id")
            and operation.OUTPUT == binding["output"] and operation.STATE == binding["state_directory"],
            "Run02 identity changed")
    require(operation.sha(root / "scripts/run_kumar_csp_signed_score_operation.py") == binding["launcher_sha256"]
            and operation.sha(root / "scripts/analyze_kumar_csp_signed_score_v1.py") == binding["scientific_consumer_sha256"],
            "Frozen entrypoint changed")
    require(operation.sha(root / "configs/kumar_csp_signed_score_operation_20261015.json")
            == binding["operation_contract_sha256"], "Run02 contract changed")
    require(not any((root / name).exists() or (root / name).is_symlink()
                    for name in (operation.OUTPUT, operation.STATE)), "Run02 already has output/state; stop")
    operation.authorization_check(auth, binding["operation_contract_sha256"], auth["reviewed_commit"], now=now)
    return binding


if __name__ == "__main__":
    root = Path("/workspace/few-shot-mi-eeg")
    commit, authorization, authorization_sha = sys.argv[1:]
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip() == commit
    assert not subprocess.check_output(["git", "diff", "HEAD", "--name-only"], cwd=root, text=True).strip()
    path = root / "scripts/run_kumar_csp_signed_score_operation.py"
    spec = importlib.util.spec_from_file_location("run02_identity_gate", path)
    operation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(operation)
    operation.require(operation.sha(authorization) == authorization_sha, "Actual authorization SHA changed")
    auth = operation.read(authorization)
    operation.require(auth.get("reviewed_commit") == commit, "Authorization commit differs")
    binding = recovery_gate(operation, root, auth)
    sys.argv = [str(path), "--execute", "--expected-commit", commit,
                "--reviewed-contract-sha256", binding["operation_contract_sha256"],
                "--authorization", authorization, "--authorization-sha256", authorization_sha]
    runpy.run_path(str(path), run_name="__main__")
PY
```

Any failure stops this command; preserve the new authorization and any actual
run02 claim/partial/exception receipt. Do not repeat it, clean claims, slide the
deadline or change hosts. Once dispatched, report the real PID/start/log and
monitor to actual exit; audit and back up all raw run02 evidence with full R2
GET/SHA verification. A successful exit is still pending scientific audit, not
acceptance. No run02 execution or scientific result is claimed by this delivery.
