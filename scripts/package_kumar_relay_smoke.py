"""Package existing synthetic CUDA checkpoint for parent-mediated backup validation.

No training, network, credentials, or claim of completed R2 backup.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import tarfile
from pathlib import Path

REQUIRED = ['software_validation.json', 'synthetic_weights.json', 'synthetic_weights.pt']


def package(source, output):
    if output.exists():
        raise FileExistsError('Preserve prior archive')
    data = {}
    for name in REQUIRED:
        path = source/name
        if path.is_symlink() or not path.is_file():
            raise ValueError('Required synthetic evidence file missing or symlinked')
        data[name] = path.read_bytes()
    software = json.loads(data['software_validation.json'])
    weights = json.loads(data['synthetic_weights.json'])
    for record in (software, weights):
        if record.get('synthetic') is not True or record.get('software_validation_only') is not True:
            raise ValueError('This packer only accepts synthetic software evidence')
    sha = hashlib.sha256(data['synthetic_weights.pt']).hexdigest()
    if weights['checkpoint_sha256'] != sha or software['checks'][0]['checkpoint_sha256'] != sha:
        raise ValueError('Synthetic checkpoint hash mismatch')
    if sum(map(len,data.values())) > 256*1024**2:
        raise ValueError('Evidence bundle too large')
    manifest = {'kind':'synthetic_checkpoint_relay_smoke','synthetic':True,
                'software_validation_only':True,'status':'packaged_awaiting_parent_and_R2_verification',
                'files':[{'path':n,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in data.items()]}
    data['manifest.json'] = (json.dumps(manifest,indent=2)+'\n').encode()
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('xb') as stream, tarfile.open(fileobj=stream,mode='w') as tar:
        for name, content in data.items():
            info=tarfile.TarInfo(name)
            info.size=len(content)
            info.mode=0o600
            info.mtime=0
            tar.addfile(info,io.BytesIO(content))
    digest=hashlib.sha256(output.read_bytes()).hexdigest()
    return {'status':'packaged_backup_pending','archive':str(output),'bytes':output.stat().st_size,
            'sha256':digest,'files':3,'real_training_executed':False,'R2_backup_verified':False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(package(a.source,a.output)))


if __name__=='__main__':
    main()
