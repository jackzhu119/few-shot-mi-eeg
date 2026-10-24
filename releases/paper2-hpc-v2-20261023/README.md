# School HPC V2 direct GitHub download

Source commit: `71e79fb6f70346ac2fc307c0b93dc23af101e2c7`.

The code, installer and complete input data can now be downloaded directly from
this GitHub repository on the school's login1 terminal. No transfer through a
personal computer or R2 permission is needed. The author expressly requested
GitHub distribution on 23 October 2026. [Data attribution and original
CC BY 4.0 license](DATA_ATTRIBUTION.txt) accompany the data.

Current operating profile: **hpc_gpu partition, one GPU/16 CPU/128G per task,
at most two tasks in parallel**. The screenshot named a partition, not a node
or GPU model; the runtime requests generic `gpu:1`. Old A100-model and gpu3
exclusion constraints are removed only in a companion operating config.

Run this one-line initialization on login1. It first saves the small local entry
without making a network request, then uses the official GitHub API with raw
as a fallback (three bounded attempts, progress printed before connecting).
The embedded public initializer source is [school_bootstrap.py](../../experiments/hpc_recalibration_v2/school_bootstrap.py);
its compression keeps a single pasted command compatible with the terminal.
The public command below contains no credential. Existing trusted CA material
and hostname/certificate validation remain enabled.

```bash
/public/home/zhuziyuan/.venvs/paper3-hpc-cu121-offline/bin/python -u -c 'import base64,json,zlib; p=json.loads(zlib.decompress(base64.b64decode("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"))); exec(compile(p["source"],"paper2_start.py","exec"),{"__name__":"__main__","BOOTSTRAP_SOURCE":p["source"].encode(),"BOOTSTRAP_TOKEN":p.get("token")})'
```

The downloader resumes interrupted files, verifies four input parts, joins them
to the unchanged 125,283,270-byte archive, verifies the full SHA256 and invokes
the existing installer. Downloads go to `/public/home/zhuziyuan/incoming/`;
the project is installed under `/public/home/zhuziyuan/projects/paper2-recalibration-v2/`.
All payload URLs use fixed commits. The verified input manifest is cached too,
so completed local inputs can resume without a network request. The input [manifest](input_download_manifest.json)
pins data revision `b971e79dbf5bf8a1452634046b6e186fe298b6a9`.

Public downloading needs no GitHub token. Before the first training submission,
enter the token only at the existing hidden school-terminal prompt; it authorizes
progress reporting. To download/install without submitting, append `--no-launch`
to the Python command. The same download command resumes interrupted transfers.
The same experiment resumes with:

```bash
/public/home/zhuziyuan/.venvs/paper3-hpc-cu121-offline/bin/python -u /public/home/zhuziyuan/paper2_start.py
```

[Complete instructions](../../experiments/hpc_recalibration_v2/README.md).
[Validation and limitations](../../research_logs/paper2_hpc_v2_20261023/REPORT.md).

GitHub's regular-file limit requires the input archive to be stored as four
files under `inputs/`, each at most32MiB. The program restores the exact original
archive SHA256 `b6f211bbf2ed512fbf30d178d59c67181396c98d0ec122812519ee95a9aa3e0a`.
It does not reprocess EEG or change any scientific configuration. R2's earlier
HTTP401 upload failure remains recorded and is independent of this download path.

Real A100 execution has not occurred in this delivery. The first allocated GPU
worker performs the minimal forward/backward/save/resume check and then trains.

## School Python certificate-path repair

If an earlier bootstrap failed with `CERTIFICATE_VERIFY_FAILED: unable to get
local issuer certificate`, use the complete command above again. It selects
existing system CA material before downloading the script. No package install,
Python upgrade, trust bypass or scientific restart is needed. Reuse this same
command after a new SSH login so the selected CA reaches authorization and the
monitor as well.

The error may also mean a campus HTTPS proxy CA is absent from the server trust
store. If verification still fails after selecting the system bundle, the missing
item is a trusted campus CA chain from the school administrator; this command
does not invent or download an unverified trust anchor.

## Runtime profile and authorization

The installer runs with `--no-launch` before any submission. The downloader then
writes `configs/kumar_dev_hpc_gpu.json` with hpc_gpu/gpu:1,16 CPUs,128G and
array concurrency2, and explicitly launches that file. The original sealed
`kumar_dev.json` is untouched; scientific identities and outputs are unchanged.
A provenance sidecar records only operating fields and file hashes.

An optional authorization supplied privately by the author is saved only to the
school account's `.config/paper2-hpc/github-token` with mode0600. Public source,
input archives and progress contain no token. The initializer source saved as
`paper2_start.py` also contains no token value. The companion config references
only the local token-file path; the existing real GitHub permission check remains
before the first submission. A user who has not configured that private file
gets the existing hidden-input authorization prompt.

The current delivery was verified by a complete125,283,270-byte API-first
download and local `--no-launch` installation, plus46 focused transport, local
entry and resource-profile tests. This does not claim access to the internal
school network or actual GPU execution. The old failed raw-host requests never
reached scientific training.
