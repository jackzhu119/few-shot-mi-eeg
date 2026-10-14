"""Restore only frozen Kumar source files; full SHA256, atomic writes, no credentials logged."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from sync_research_r2 import build_client

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / 'research_logs/public_data_expansion_20261010/r2/kumar2024_raw_20261011_run01.json'
PROTOCOL = ROOT / 'configs/kumar_cross_session_20261012.json'
SPLIT = ROOT / 'research_logs/kumar_cross_session_20261012/protocol/split_manifest.json'


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def select(scope):
    protocol = json.loads(PROTOCOL.read_text())
    trials = json.loads(SPLIT.read_text())['trials']
    if scope == 'development-csp':
        subjects = set(protocol['development_subjects'])
        roles = {'source_train', 'target_support'}
    elif scope == 'development-eegnet':
        subjects = set(protocol['development_subjects'])
        roles = {'source_train', 'source_validation'}
    else:
        subjects = set(protocol['subjects'])
        roles = {'source_train', 'source_validation', 'source_query', 'target_support', 'target_query'}
    edfs = {t['source_file'] for t in trials if t['subject'] in subjects and t['role'] in roles}
    prefixes = {f.removesuffix('_eeg.edf') for f in edfs}
    files = []
    for entry in json.loads(RECEIPT.read_text())['files']:
        path = entry['relative_path']
        chosen = (path == 'dataset_description.json' or path in edfs
                  or (path.split('/')[0] in subjects and path.endswith('_scans.tsv'))
                  or any(path == prefix + suffix for prefix in prefixes
                         for suffix in ('_eeg.json', '_events.json', '_events.tsv', '_channels.tsv')))
        if chosen:
            files.append({k: entry[k] for k in ('relative_path', 'key', 'sha256', 'bytes')})
    if len([f for f in files if f['relative_path'].endswith('.edf')]) != len(edfs):
        raise ValueError('Incomplete frozen R2 mapping')
    return files


def restore(client, bucket, entries, root):
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    needed = sum(e['bytes'] for e in entries if not (root / e['relative_path']).exists())
    if shutil.disk_usage(root).free < needed + 5 * 1024**3:
        raise RuntimeError('Insufficient disk: retain 5 GiB reserve')
    for entry in entries:
        path = root / entry['relative_path']
        if not path.resolve().is_relative_to(root):
            raise ValueError('Unsafe restore path')
        if path.exists():
            if path.stat().st_size != entry['bytes'] or digest(path) != entry['sha256']:
                raise ValueError('Existing local content conflict; preserve and investigate')
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(path.name + '.partial')
        response = client.get_object(Bucket=bucket, Key=entry['key'])
        try:
            with temp.open('wb') as stream:
                for block in response['Body'].iter_chunks(chunk_size=1024**2):
                    stream.write(block)
        finally:
            response['Body'].close()
        if temp.stat().st_size != entry['bytes'] or digest(temp) != entry['sha256']:
            raise ValueError('Full GET content hash mismatch; no promotion')
        temp.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scope', choices=['development-csp', 'development-eegnet', 'formal'], required=True)
    parser.add_argument('--data-root', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.receipt.exists():
        raise FileExistsError('Receipt exists; use a new attempt receipt')
    entries = select(args.scope)
    result = dict(scope=args.scope, files=entries, bytes=sum(e['bytes'] for e in entries),
                  edf_count=sum(e['relative_path'].endswith('.edf') for e in entries),
                  source_receipt_sha256=digest(RECEIPT), split_sha256=digest(SPLIT),
                  status='plan_only', credential_values_logged=False)
    if args.execute:
        client, bucket, _ = build_client()
        client.head_bucket(Bucket=bucket)
        restore(client, bucket, entries, args.data_root)
        result['status'] = 'all_local_bytes_sha256_verified'
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'files'}))


if __name__ == '__main__':
    main()
