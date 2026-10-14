# MIND public API verification — 2026-10-12 UTC

Official DOI: https://doi.org/10.57760/sciencedb.34326
Dataset ID: d0f67f38c5bc4416bdcce619f33e57da
Current release: V4 / schema.org version 4.0.0

- Fresh official landing GET: HTTP 200; `conditionsOfAccess=PUBLIC`.
- Fresh details GET `/api/sdb-dataset-service/dataset/details/{id}?version=V4&mode=front`: HTTP 200/code 20000, `canView=true`, `canGetZip=true`, `shareStatus=PUBLIC`.
- Current inventory POST `/api/gin-sdb-filetree/public/file/childrenFileListByPath`: `dataSetId`, `version=V4`, `path=/V4/MIND_BIDS`, `lastIndex=0`, `pageSize=200`. Recursive public directory listing completed without authentication. The token `public4` is not the current API version argument; earlier exploratory requests with that argument returned empty lists. No gate bypass attempted.
- Complete recursive manifest: 1772 files, 182 directories within MIND_BIDS, 99,091,202,929 bytes total. Sum equals official landing/details declared volume.
- Actual participants: public `participants.tsv` GET 200 includes exactly 30 unique sub-01…sub-30 rows; BIDS inventory also contains exactly those 30 participant directories. EEG has three BrainVision runs for every participant (90 `.eeg` files).
- BIDS EEG-only: 690 files, 31,972,818,960 bytes (29.777 GiB). All BIDS raw modalities: 34,405,546,200 bytes (32.043 GiB). Sourcedata: 57,655,025,224 bytes (53.695 GiB). One derivatives RAR: 7,030,594,363 bytes (6.548 GiB).
- Representative EEG signal HEAD: unauthenticated https://china.scidb.cn/download?fileId=… returned HTTP 200, content-type application/octet-stream, content-length 357,478,400 matching manifest, accept-ranges bytes. No signal body downloaded. Exact stable fileId endpoint and headers in `signal_HEAD_probe.json`; no signed credentials recorded.
- Public lightweight GETs: README, participants.tsv, dataset_description.json, first EEG run header/JSON/events TSV/events JSON all HTTP 200. These are saved as `sample_*` with corresponding HTTP probe JSON.
- Repository declared license is CC BY-NC 4.0. BIDS `dataset_description.json` declares CC BY 4.0, so a source-internal license conflict remains; apply the stricter repository CC BY-NC 4.0 until clarified. README details explicitly state 28 right-handed and 2 without clear hand preference, agreeing with participants.tsv handedness (28 R, 2 A), though README abstract simplifies this to all right-handed.
- Recommendation: technically public and downloadable, useful current MI source. Full EEG-only download exceeds a 5 GiB acquisition budget by roughly 6x, and full derivatives exceeds it too. No full EEG archive downloaded by this verification.

Raw evidence: fresh landing, details/version API responses, recursive inventory response pages + HTTP manifest, exact complete file manifests. `inspect_public_inventory.py` is the rerunnable metadata-only collection script; signal checks were HEAD only.
