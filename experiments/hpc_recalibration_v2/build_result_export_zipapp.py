"""Build the single-file saved-result uploader from explicit original sources."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile


def build(destination, source_commit=None):
    root = Path(__file__).resolve().parents[2]
    source = Path(__file__).resolve().parent
    source_commit = source_commit or subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root).decode().strip()
    contents = {name: (source / filename).read_bytes() for name, filename in (
        ('__main__.py', 'export_saved_results.py'), ('github_result_upload.py', 'github_result_upload.py'),
        ('result_history_export.py', 'result_history_export.py'))}
    contents.update({
        'assets/SOURCE_DATA_ATTRIBUTION.txt': (root / 'releases/paper2-hpc-v2-20261023/DATA_ATTRIBUTION.txt').read_bytes(),
        'assets/LICENSES/MIT.txt': (root / 'LICENSES/MIT.txt').read_bytes(),
        'assets/LICENSES/CC-BY-4.0.txt': (root / 'LICENSES/CC-BY-4.0.txt').read_bytes(),
    })
    manifest = {'source_commit': source_commit, 'scope': 'saved result export only; no training or inference',
                'files': [{'path': name, 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}
                          for name, body in sorted(contents.items())]}
    contents['assets/UPLOADER_BUILD.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as package:
        for name, body in sorted(contents.items()):
            info = zipfile.ZipInfo(name, date_time=(2000, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            package.writestr(info, body)
    return {'file': destination.name, 'bytes': destination.stat().st_size,
            'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(), 'source_commit': source_commit}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.output), indent=2))
