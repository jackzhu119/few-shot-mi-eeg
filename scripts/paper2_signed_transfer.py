"""Short-lived object-scoped transfer capabilities; no long-lived credential export.

Prepare on the already authorized Codex host, securely transfer the private JSON
file to RunPod, then receive/backup there. Never print or commit capability URLs.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import tarfile
import urllib.error
import urllib.request
from pathlib import Path

from restore_kumar_r2 import ROOT, digest, select
from sync_research_r2 import build_client, safe_key_prefix


def request(url, *, method='GET', data=None, headers=None):
    try:
        return urllib.request.urlopen(urllib.request.Request(url, data=data, method=method,
                                                             headers=headers or {}), timeout=120)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f'Signed transfer HTTP {error.code}; URL redacted') from None
    except Exception:
        raise RuntimeError('Signed transfer failed; URL redacted') from None


def prepare(path, *, scope=None, key=None):
    path = path.resolve()
    if path.is_relative_to(ROOT) or path.exists():
        raise ValueError('Capability file must be new and outside repository')
    client, bucket, _ = build_client()
    client.head_bucket(Bucket=bucket)
    if scope:
        entries = select(scope)
        for e in entries:
            e['url'] = client.generate_presigned_url('get_object', Params={'Bucket':bucket, 'Key':e['key']}, ExpiresIn=3600)
        payload = dict(mode='data', scope=scope, entries=entries)
    else:
        safe_key_prefix(key)
        params = dict(Bucket=bucket, Key=key)
        payload = dict(mode='backup', key=key,
                       put=client.generate_presigned_url('put_object', Params={**params, 'IfNoneMatch':'*'}, ExpiresIn=3600),
                       get=client.generate_presigned_url('get_object', Params=params, ExpiresIn=3600))
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(payload, stream)
    print('Private one-hour capability file created; securely transfer, never commit or print contents.')


def receive(path, root):
    payload = json.loads(path.read_text())
    entries = select(payload['scope'])
    supplied = payload['entries']
    if [{k:v for k,v in e.items() if k != 'url'} for e in supplied] != entries:
        raise ValueError('Capability manifest differs from frozen R2 mapping')
    root.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(root).free < sum(e['bytes'] for e in entries) + 5*1024**3:
        raise RuntimeError('Need data size plus 5 GiB reserve')
    for entry in supplied:
        target = root / entry['relative_path']
        if not target.resolve().is_relative_to(root.resolve()):
            raise ValueError('Unsafe destination')
        if target.exists():
            if digest(target) != entry['sha256']:
                raise ValueError('Existing content conflict')
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.name + '.partial')
        with request(entry['url']) as response, temp.open('wb') as stream:
            shutil.copyfileobj(response, stream)
        if temp.stat().st_size != entry['bytes'] or digest(temp) != entry['sha256']:
            raise ValueError('Full GET hash mismatch')
        temp.replace(target)
    print('All selected source bytes SHA256 verified; capability URLs omitted.')


def backup(path, source):
    payload = json.loads(path.read_text())
    if payload['mode'] != 'backup' or path.resolve().is_relative_to(source.resolve()):
        raise ValueError('Invalid backup capability or unsafe source placement')
    # Existing audited collector rejects credential names, keys and symlinks.
    from sync_research_r2 import safe_source_files
    files = safe_source_files(source)
    archive = source.parent / (source.name + '.tar')
    with tarfile.open(archive, 'w') as tar:
        for item in files:
            tar.add(item, arcname=item.relative_to(source).as_posix(), recursive=False)
    expected = digest(archive)
    # Bounded model/log bundle only: prevent a mistaken raw dataset upload.
    if archive.stat().st_size > 256*1024**2:
        raise ValueError('Model/log bundle exceeds 256 MiB review boundary')
    try:
        with request(payload['put'], method='PUT', data=archive.read_bytes(),
                     headers={'If-None-Match':'*'}) as response:
            response.read()
    except RuntimeError as error:
        if 'HTTP 412' not in str(error):
            raise
        # Prior PUT may already have succeeded. Verify remote bytes before retrying.
    remote = archive.with_suffix('.readback')
    with request(payload['get']) as response, remote.open('wb') as stream:
        shutil.copyfileobj(response, stream)
    if digest(remote) != expected or remote.stat().st_size != archive.stat().st_size:
        raise ValueError('Backup readback mismatch; preserve local files, do not shut down')
    receipt = archive.with_suffix('.backup.json')
    receipt.write_text(json.dumps(dict(status='full_get_sha256_verified', key=payload['key'],
                                      sha256=expected, bytes=archive.stat().st_size,
                                      files={str(f.relative_to(source)):digest(f) for f in files}), indent=2))
    remote.unlink()
    print(json.dumps(dict(status='full_get_sha256_verified', receipt=str(receipt))))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['prepare-data', 'prepare-backup', 'receive', 'backup'])
    p.add_argument('--capability', type=Path, required=True)
    p.add_argument('--scope', choices=['development-csp', 'development-eegnet'])
    p.add_argument('--key')
    p.add_argument('--directory', type=Path)
    a = p.parse_args()
    if a.action == 'prepare-data':
        if not a.scope:
            p.error('--scope required')
        prepare(a.capability, scope=a.scope)
    elif a.action == 'prepare-backup':
        if not a.key:
            p.error('--key required')
        prepare(a.capability, key=a.key)
    else:
        if a.directory is None:
            p.error('--directory required')
        (receive if a.action == 'receive' else backup)(a.capability, a.directory)


if __name__ == '__main__':
    main()
