# School HPC V2 direct GitHub download

Source commit: `71e79fb6f70346ac2fc307c0b93dc23af101e2c7`.

The code, installer and complete input data can now be downloaded directly from
this GitHub repository on the school's login1 terminal. No transfer through a
personal computer or R2 permission is needed. The author expressly requested
GitHub distribution on 23 October 2026. [Data attribution and original
CC BY 4.0 license](DATA_ATTRIBUTION.txt) accompany the data.

On login1 run this single line using the already confirmed Python interpreter.
It needs no curl/wget and preserves terminal input for the authorization prompt:

```bash
/public/home/zhuziyuan/.venvs/paper3-hpc-cu121-offline/bin/python -u -c 'import urllib.request; exec(compile(urllib.request.urlopen("https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/d7c49a9a0e25b359c389e2d2383d91fcde973f99/experiments/hpc_recalibration_v2/download_on_hpc.py", timeout=60).read(), "download_on_hpc.py", "exec"))'
```

The downloader resumes interrupted files, verifies four input parts, joins them
to the unchanged 125,283,270-byte archive, verifies the full SHA256 and invokes
the existing installer. Downloads go to `/public/home/zhuziyuan/incoming/`;
the project is installed under `/public/home/zhuziyuan/projects/paper2-recalibration-v2/`.
All payload URLs use fixed commits. The input [manifest](input_download_manifest.json)
pins data revision `b971e79dbf5bf8a1452634046b6e186fe298b6a9`.

Public downloading needs no GitHub token. Before the first training submission,
enter the token only at the existing hidden school-terminal prompt; it authorizes
progress reporting. To download/install without submitting, append `--no-launch`
to the Python command. The same download command resumes interrupted transfers.
The same experiment resumes with:

```bash
bash /public/home/zhuziyuan/projects/paper2-recalibration-v2/launch.sh
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
