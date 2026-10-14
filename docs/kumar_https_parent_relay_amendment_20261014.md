# Operational amendment: fixed public HTTPS input and private parent relay

This changes transport only. The scientific protocol, source version, 22 channels,
preprocessing, source run partition, subject sub-1, seed 20261012, optimizer,
selection rule and overall three-seed plan are unchanged. No real fit is executed
by this preparation. Preserve historical R2/SSH failures and previous outputs.

The old phrase "already-local" refers to the frozen NEMAR nm000177/v1.0.5 byte
identities; the identical selected bytes may now be restored on the existing Pod
from explicit official HTTPS URLs. No fresh cohort or changed source release.

## Frozen first-fit download

`configs/kumar_first_fit_https_20261014.json` and its detached SHA256 contain exactly
25 files / 16,425,499 bytes: four root metadata files; six sub-1 session scans;
source session run-0/1/2 EDFs and four sidecars per run. Only three EDFs. No query
EDF or target EEG. The original selection checksum and each official URL/checksum
remain pinned; every object additionally matches the historical R2 SHA256.

All 22 metadata files must pass full official checksum and historical SHA256,
then dataset version/license (1.0.5, CC-BY-4.0) pass before any EDF request.
The bounded downloader uses one request at a time, one attempt per file, existing
TLS/proxy settings, known official redirects only and 20/60-second connect/read
timeouts. A 600-second internal deadline plus a 660-second process deadline bounds
execution. Existing wrong files and failed `.partial` files are preserved and
cause failure; verified files are reused. No complete 2705-file download plan runs.

After checking out the new delivery commit on the existing Pod (parent operation):

```bash
cd /workspace/paper2-90f674f # actual checkout in received server acceptance evidence
export PYTHONPATH="$PWD/src:$PWD/scripts"
timeout --signal=TERM --kill-after=10s 660s \
 /workspace/.venvs/paper2-gpu/bin/python scripts/fetch_kumar_first_fit_https.py \
 --data-root /workspace/paper2-data/kumar \
 --receipt /workspace/paper2-results/https-first-fit-download-run01.json --execute
```

Omitting `--execute` is a no-network plan check. A new attempt requires a new
receipt path and explicit investigation of any preserved partial/conflict. Do not
change hashes or relax checks to make a download succeed. The script does not
train and does not fetch query data. Keep the data private/off Git despite CC BY.

## Private relay: actual acceptance and remaining gate

Parent supplied Library installation evidence archive ID
`libfile_4d84c9ced408819184bb5d35678b89d6`, 14,247 bytes, SHA256
`d000a45b9db03eca32ea124bd533ce234a5028c5471410ac9efdca2586ff0a1c`.
This task materialized the private file using authorized Library tools, verified
its complete bytes and all 15 manifest member sizes/hashes, then uploaded the
unchanged archive to the existing R2 destination and completely GET-verified it.
The receipt is `research_logs/https_first_fit_20261014/library_to_r2_receipt.json`.
The shared installation package is cross-project operational evidence, not a
scientific result reused as independent novelty in either paper.

The included paper2 CUDA synthetic receipt records torch 2.8.0+cu128, available
CUDA, same-seed replay and safe checkpoint replay. It is actual received software
evidence, not a real EEG fit. It supersedes older "server installation pending"
status only for installation/synthetic checks, not real training or billing.
The archive explicitly excludes binary model weights, so a checkpoint-bearing
relay roundtrip is still required. `ready_for_first_fit=false` remains in the new
relay contract. The existing direct-R2 training runner is not weakened or bypassed.

Parent can package the ALREADY COMPLETED synthetic model (no repeated fit):

```bash
PYTHONPATH="$PWD/src:$PWD/scripts" /workspace/.venvs/paper2-gpu/bin/python \
 scripts/package_kumar_relay_smoke.py \
 --source /workspace/paper2-results/cuda-synthetic-run01 \
 --output /workspace/paper2-results/cuda-synthetic-relay-run01.tar
```

The packer includes exactly `software_validation.json`, `synthetic_weights.json`,
`synthetic_weights.pt` and a member hash manifest. It verifies the weights SHA256
against both receipts, refuses overwrites/symlinks/non-synthetic input, and outputs
only archive size/hash and pending state. No credentials, environment files or
raw EEG are included. A local CPU synthetic package exercise is software testing
of the packer only; it is NOT the required Pod-to-Library checkpoint acceptance.

Parent downloads this archive via authenticated Jupyter, privately places it in
Library, and sends this task its Library ID, exact byte count and SHA256 (no secret
URL). This task repeats private materialization, archive/member/checkpoint hash
verification, existing-authorization R2 upload and full GET comparison. A checksum
mismatch, missing weight or Library/R2 failure leaves the gate closed and all
local Pod evidence retained. No further training or shutdown follows a failure.

## First real fit and completion contract

After checkpoint-bearing relay passes, version the exact one-fit entry point and
contract; do not merely remove the old runner's R2 preflight. The parent-mediated
entry point must enforce sub-1/seed20261012, one fit, process lock and bounded
runtime. Its local terminal state is `fit_finished_backup_pending`, not completed.
Keep source TRAIN/validation exclusive, all scientific settings and frozen hashes.

Package weights plus bound JSON, loss history, input hashes/download receipt,
code/config/version identity and stdout/stderr. Parent sends the package over the
same accepted route; Codex produces a durable R2 full-GET receipt binding the exact
archive SHA256, object key and member manifest. Parent verifies and acknowledges
that receipt before the run can be marked complete. The Pod is retained until
backup is verified and both papers' dependencies are clear. Parent alone controls
platform stop and checks the resulting platform state. Process exit is not backup
completion or billing stop. No R2 master key or signed capability is transferred.
