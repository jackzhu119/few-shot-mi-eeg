#!/bin/bash
# Run this FILE on login1 after uploading the two archives to incoming/.
# Bash 4.2; no downloads, dependency installation, hard links or directory fsync.
set -eu
python=${HPC_V2_PYTHON:-/public/home/zhuziyuan/.venvs/paper3-hpc-cu121-offline/bin/python}
incoming=${HPC_V2_INCOMING:-/public/home/zhuziyuan/incoming}
code=${HPC_V2_CODE_ARCHIVE:-$incoming/paper2-hpc-v2-code.tar.gz}
inputs=${HPC_V2_INPUTS_ARCHIVE:-$incoming/paper2-hpc-v2-kumar-dev-inputs.tar.gz}
project=${HPC_V2_PROJECT_DIR:-/public/home/zhuziyuan/projects/paper2-recalibration-v2}
if [ ! -x "$python" ]; then
    printf '%s\n' "Existing Python was not found: $python" >&2
    exit 2
fi
exec "$python" -u -c '
import hashlib, json, pathlib, sys, tarfile
archive_path, inputs, project = sys.argv[1:4]
top = "paper2-recalibration-v2"
with tarfile.open(archive_path, "r:*") as archive:
    names = set()
    for item in archive.getmembers():
        path = pathlib.PurePosixPath(item.name)
        if (path.is_absolute() or ".." in path.parts or "\\" in item.name
                or not path.parts or path.parts[0] != top
                or not (item.isfile() or item.isdir()) or item.name in names):
            raise SystemExit("Unsafe or duplicate code archive member; nothing installed.")
        names.add(item.name)
    manifest = json.load(archive.extractfile(top + "/PACKAGE_MANIFEST.json"))
    record = next(row for row in manifest["files"] if row["path"] == "build_offline.py")
    source = archive.extractfile(top + "/build_offline.py").read()
    if len(source) != record["bytes"] or hashlib.sha256(source).hexdigest() != record["sha256"]:
        raise SystemExit("Installer payload failed SHA256; nothing installed.")
sys.argv = ["build_offline.py", "install", "--code-archive", archive_path,
            "--inputs-archive", inputs, "--project-dir", project] + sys.argv[4:]
exec(compile(source, top + "/build_offline.py", "exec"),
     {"__name__": "__main__", "__file__": str(pathlib.Path(project) / "build_offline.py")})
' "$code" "$inputs" "$project" "$@"
