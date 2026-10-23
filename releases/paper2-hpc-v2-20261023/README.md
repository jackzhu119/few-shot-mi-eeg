# School HPC V2 offline delivery

Source commit: `71e79fb6f70346ac2fc307c0b93dc23af101e2c7`.

Download the code tar and installer here. The separate 125,283,270-byte EEG input
tar is deliberately outside Git; it is supplied through this chat/workspace at
`/workspace/paper2_hpc_v2_delivery/paper2-hpc-v2-kumar-dev-inputs.tar.gz`.
Its complete SHA is recorded in SHA256SUMS.txt and the public input manifest.
The new R2 upload returned HTTP401 and is not claimed as a backup.

Upload all three files to `/public/home/zhuziyuan/incoming/`, then on login1 run:

```bash
bash /public/home/zhuziyuan/incoming/install_offline.sh
```

Enter the GitHub token only at the hidden school-terminal prompt.
The same experiment resumes with:

```bash
bash /public/home/zhuziyuan/projects/paper2-recalibration-v2/launch.sh
```

[Complete instructions](../../experiments/hpc_recalibration_v2/README.md).
[Validation and limitations](../../research_logs/paper2_hpc_v2_20261023/REPORT.md).

Real A100 execution has not occurred in this delivery. The first allocated GPU
worker performs the minimal forward/backward/save/resume check and then trains.
