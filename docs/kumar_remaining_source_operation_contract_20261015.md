# Remaining 36 source fits: fixed deployment handoff

The user explicitly requests immediate completion of the existing 36 EEGNet
source fits on the existing dot-operated Pod, without waiting for CSP writing.
This revision removes only the existing financial execution prerequisites and
enables the same exact253 HTTPS restoration manifest. It does not replace the
scientific runner, expand the task list, change training parameters or refit the
accepted18. Codex prepares code/data/evidence; dot alone deploys and operates Pod.

Historical monetary observations/unknowns remain in the contract and the prior
fixed commit 9f7bc102dec264e10688765636596c336e69becc. Their execution role is
explicitly `superseded-by-user`: no cost, rate, balance or billing recheck is
required. No amount is filled in or newly asserted. No new allocation is allowed.

## Fixed identities and scope

- Runner SHA256: `9e54f1107956cae6f98228e787838cf973b8889fa98a85b7ce889cf3a2847dfc`.
- Contract SHA256: `f1a5b94aa89f6f2d9f694f7c270e48ef2624afc06be3a08e328f500224491bd9`.
- HTTPS manifest SHA256: `b654533a6e4fee780fab11d7a9a44ec418ef327f2422f2a2570d49cfa1b47b9f`.
- Original253 source manifest: `research_logs/kumar_checkpoint_reuse_preparation_20261015/proposed_remaining_source_inputs.json`,
  SHA256 `312b5bd38995aac5fd7748b64cdf5c0446b5e33fe05e3970c61b5dd73e026682`.
- Scientific config SHA256 remains `14c291ca9762cb676a5f61608ab7b895435fdb957b7396056093c8310435856d`;
  split SHA256 remains `ac6e9f2cdd66b3c26814cfc04edf5f8e08eb592ca523c7ab029a2fa56ffd0b28`.
- Accepted18 ledger remains `1ee1868b97e6ff7ea2e42327fe64337cafbb0f8ee6aff19cc24fba5265f9aaa9`.

Exactly sub-2/3/5/6/8/9/11/12/14/15/17/18, each seed20261012/20261013/20261014,
in that order. The contract contains all36 original job IDs/output/result keys.
Only source ses-0 runs0/1 TRAIN and run2 source validation: 40/20 trials per fit.
No query adapter, query signal/labels, later-session signal or accepted18 fit is
permitted. Future scans.tsv metadata remains solely for frozen acquisition-order
identity verification. Scientific config, numerical threads and replay1e-7 stay fixed.

The bounded queue is unchanged: two serial fits per chunk, shared global GPU
lock across both fits and packaging, fit1800s, chunk3600s, whole-run<=10800s,
TERM30s reserve, zero automatic training retries, 5GiB free disk plus100663296B
chunk reserve, at most two trained/unexported models. All checks, runtime startup,
packaging and actual receipt waits consume the same absolute execution window.
Partial completion is preserved if the window expires; it never rolls forward.

## Source bytes and transport

The exact253 local originals were fully rehashed:253/253,196740994bytes,
36EDF+217metadata, zero mismatch. Private transport archive:
`source-inputs-253.tar.gz`,114244136bytes,
SHA256 `fc9f1b26f79df27e6fd5ab06264a092dbe289af38b309aa0f8bf03eed8968155`.
It contains253 regular `data/<original-relative-path>` members and the unchanged
`source_manifest.json` (254members total). The whole tar was reopened and each
member fully length/SHA verified. Detailed receipt:
`research_logs/kumar_remaining36_deployment_20261015/input_transfer_package.json`.

Local archive:
`/workspace/private_model_receipts/remaining36-deployment-20261015/source-inputs-253.tar.gz`.
Private R2 key:
`few-shot-mi-eeg/research-evidence/task-aware-kumar/20261015/remaining36-source-transfer-run01/source-inputs-253.tar.gz`.
Use the existing supported authenticated Jupyter file transfer for the downloaded
package; do not copy R2 credentials or create signed capability URLs. The input
package contains no credentials, existing model weights or query files. It is
not a Git artifact and is not a claim of completed Pod deployment.

The existing official HTTPS fetcher is also a complete deployment route if the
archive is not present on dot's filesystem. The manifest now has
`execution_enabled=true`; all253 file entries are byte-equivalent at entry level.
It reuses any complete local files only after full SHA/official checksum checks,
otherwise performs one bounded official request per file. No new downloader exists.

On the clean fixed checkout in the existing Pod, preserve all old claims/state.
Use the final commit returned with this delivery as `PAPER2_FIXED_COMMIT` and
verify `git rev-parse HEAD` equals it; do not reset a dirty checkout. Reuse the
existing `/workspace/.venvs/paper2-gpu` runtime; its exact91package checks remain.
Then restore/verify the253files with the existing entrypoint:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 CUBLAS_WORKSPACE_CONFIG=:4096:8 \
PYTHONPATH=src:scripts /workspace/.venvs/paper2-gpu/bin/python -B \
  scripts/fetch_kumar_remaining_source_https.py \
  --data-root /workspace/paper2-data/kumar \
  --receipt /workspace/paper2-results/https-remaining-source-download-run01.json \
  --execute
```

If importing the package first, verify its exact full SHA and member manifest,
extract only its `data/` members into a new staging directory and merge solely
missing matching253paths without overwriting a differing existing file. The same
fetcher command then performs the full local recheck and publishes the real
`all_253_full_sha256_verified` receipt; it does not download when all files match.
Do not manufacture a Pod receipt from the Codex-side package verification.

## The one remaining deployment binding

There is one live deployment record still to create: dot binds this fixed code
and contract to the actual current Pod container and an actual absolute execution
window of at most10800seconds. This records the already requested operation; it
is not another scientific or financial decision. Codex has not observed the live
Pod identity and must not invent it. The following command is for dot on that Pod
only, after fixed checkout and input verification. It publishes a new external
authorization exclusively. Do not run it again for a pause/resume.

```bash
export PAPER2_CONTRACT_SHA256=f1a5b94aa89f6f2d9f694f7c270e48ef2624afc06be3a08e328f500224491bd9
export PAPER2_EXTERNAL_AUTHORIZATION=/workspace/paper2-results/remaining36-execution-authorization-run01.json
PYTHONPATH=src:scripts /workspace/.venvs/paper2-gpu/bin/python -B - "$PAPER2_FIXED_COMMIT" "$PAPER2_EXTERNAL_AUTHORIZATION" <<'AUTH'
import json
import subprocess
import sys
import time
from pathlib import Path
import run_kumar_remaining_source_batch as batch
commit, destination = sys.argv[1:]
contract = batch.read(batch.DEFAULT_CONTRACT)
batch.validate_contract(contract)
batch.require(subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip() == commit, "Fixed commit differs")
batch.require(not subprocess.check_output(["git", "status", "--porcelain"], text=True).strip(), "Preserve dirty checkout; stop")
batch.verify_source_inputs(contract)
batch.require(not Path(contract["state_root"]).exists(), "Existing queue state; do not recreate authorization")
for job in contract["remaining_jobs"]:
    output = Path(job["output"])
    batch.require(not output.exists() and not output.with_suffix(".tar").exists(), "Existing job output; stop")
start = int(time.time())
identity = batch.container_identity()
auth = {"schema_version": 1, "status": "parent_reviewed_remaining36_source_execution_authorized",
        "reviewed_commit": commit, "contract_sha256": batch.sha(batch.DEFAULT_CONTRACT),
        "approved_job_ids": [j["job_id"] for j in contract["remaining_jobs"]],
        "query_access": False, "accepted18_refitting_authorized": False,
        "financial_execution_preconditions": "superseded-by-user",
        "not_before_unix": start, "deadline_unix": start + 10800,
        "approved_wall_seconds": 10800, "authorized_container_identity": identity,
        "new_resource_allocation_authorized": False,
        "authorization_basis": "User requests completion of the fixed remaining36 on the existing dot-operated Pod; financial execution preconditions explicitly revoked. Dot publishes this actual host/window binding."}
batch.authorization_check(contract, auth["contract_sha256"], commit, auth)
batch.write_new(Path(destination), auth)
print(json.dumps({"authorization_sha256": batch.sha(Path(destination)), "container_identity": identity,
                  "not_before_unix": start, "deadline_unix": start + 10800}))
AUTH
```

Use the printed full authorization SHA as `PAPER2_AUTHORIZATION_SHA256`. Start the
existing queue once, preserving the original numeric environment:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
CUBLAS_WORKSPACE_CONFIG=:4096:8 PYTHONPATH=src:scripts \
/workspace/.venvs/paper2-gpu/bin/python -B scripts/run_kumar_remaining_source_batch.py \
  --execute --new-run \
  --expected-commit "$PAPER2_FIXED_COMMIT" \
  --reviewed-contract-sha256 "$PAPER2_CONTRACT_SHA256" \
  --authorization "$PAPER2_EXTERNAL_AUTHORIZATION" \
  --authorization-sha256 "$PAPER2_AUTHORIZATION_SHA256" --wait-seconds 600
```

Contract `execution_enabled=false` continues to describe the default metadata
mode; the actual external authorization is the explicit execution gate. The
historical scientific proposal/job action labels remain unchanged identities,
not a reason to retrain or expand their scope. No generic `formal_train` call.

## Real off-Pod boundaries and resumption

For each of18chunks, dot must fully download the original intent tar before
training, and the original results tar before the next chunk. On dot's off-Pod
filesystem, use the same fixed checkout's existing verifier:

```bash
PYTHONPATH=src:scripts python -B scripts/run_kumar_remaining_source_batch.py \
  --verify-export "$FULL_OFF_POD_ORIGINAL_TAR" \
  --receipt-output "$NEW_OFF_POD_RECEIPT_JSON" --attest-off-pod-possession
```

Return the real receipt using the supported authenticated Jupyter upload or
previously verified terminal route, compare full UTF-8 SHA and publish a new file
exclusively/atomically. The expected path is the current state's pending export
receipt path. No automatic R2 upload or internal browser API is claimed.

Exit76 means waiting for that receipt. Resume with the same exact command and
same authorization, replacing only `--new-run` with `--resume`. Never reissue the
authorization or deadline. Any failed/ambiguous claim, changed host, missing state,
storage failure or expired window stops; preserve originals and reconcile actual
off-Pod evidence. Do not clean claims or repeat a completed model. Exit75 with
`complete_exported` still means scientific audit/R2/acceptance are pending.
`trained`, `off_Pod_exported`, `independently_audited`, `R2_full_GET_verified` and
`accepted` remain distinct. The runner leaves the last three false.

Independent result audit continues to use `scripts/audit_kumar_remaining_source_bundle.py`
against each original tar and fixed253scope; full R2 GET and actual parent
confirmation follow. All original18 identities/weights/acceptances and CSP run01
failure/run02 results/R2 receipts remain unchanged. This delivery does not operate
Pod or claim that any of the remaining36 has already trained.
