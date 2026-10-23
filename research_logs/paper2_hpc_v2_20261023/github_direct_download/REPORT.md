# Direct school-server download from GitHub

The author explicitly requested GitHub-hosted inputs on 23 October 2026 so that
login1 can download them without a personal-computer transfer. This replaces
the earlier local-only delivery instruction for this input package. The original
125,283,270-byte archive and every scientific configuration remain unchanged.

## Published inputs and download entry

Data revision: `b971e79dbf5bf8a1452634046b6e186fe298b6a9`.
`releases/paper2-hpc-v2-20261023/input_download_manifest.json` lists four input
parts, each no larger than32MiB. Their sum is125,283,270 bytes. Joining them
restores archive SHA256
`b6f211bbf2ed512fbf30d178d59c67181396c98d0ec122812519ee95a9aa3e0a`.
The code and installer remain pinned to
`cddb6aa2b73a169e5386ff981d93fd6f6bf43f28` and retain their prior SHA values.

`experiments/hpc_recalibration_v2/download_on_hpc.py` uses only the existing
Python standard library. It downloads directly to the school's persistent
`/public/home/zhuziyuan/incoming`, supports HTTP Range continuation, verifies
each part and the whole archive, then invokes the existing installer. Completed
files use the prior successful SHA receipt and unchanged file stats. Network
attempts are bounded at three; file-system failures propagate. No scientific
attempt is automatically retried. Public downloads require no token or R2
permission. Before training submission the existing hidden GitHub-token
authorization remains in effect.

## Observed validation

- The public fixed-version manifest was anonymously retrieved from GitHub.
- A real Range request returned HTTP206 with the correct Content-Range and
  matching bytes. It was not treated as a full-file verification.
- The actual downloader fetched code, installer and all four input parts from
  public GitHub. Part000 resumed from a real1MiB GitHub download. Every part
  matched its declared size and SHA256; the joined125,283,270-byte tar matched
  the unchanged original SHA256.
- The same process installed and verified120 files locally with `--no-launch`.
  No Slurm submission, new fit, query inference or school-host access occurred.
- Repeating the command took0.332s, downloaded no data again and reused the
  installation without a full archive rescan.
- Thirteen targeted download tests passed in0.05s; Ruff and whitespace checks
  passed. Tests cover Range continuation, servers ignoring Range, invalid Range,
  integrity failures, preservation of differing files, bounded network failures,
  assembly, stat-cache reuse and immediate propagation of fsync failure.

`actual_download_install_receipt.json` contains the actual part hashes, final
archive hash, installation count and repeat-run stdout. This evidence is from
the current Codex CPU environment; it does not claim that the internal school
network or its A100 was accessed.

## Distribution and failed route

An attempted Release attachment upload returned HTTP401 at uploads.github.com,
although the Release metadata API succeeded. No Release asset was uploaded.
The working route uses ordinary versioned repository files split below the
single-file limit. The Release page points to these files and instructions.
`release_upload_failure.json` retains the failed route; it is not a download
receipt. The earlier R2HTTP401 record is also preserved. Neither failed route
is required for the working GitHub downloads.

The package-publication audit verified93 archive members and the expected
78NPZ schemas without model weights, credential files or chat content.
Original public acquisition times and coded IDs remain; the audit makes no
universal anonymity or exhaustive secret-detection assertion. Source five-author
credit, dataset/paper DOIs, CC BY4.0 and preprocessing changes are recorded in
the release's DATA_ATTRIBUTION.txt. Original source ownership is unchanged.
