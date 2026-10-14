"""One frozen 25-file official HTTPS restoration; never train or expand scope."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import time
from pathlib import Path

import requests

from fetch_nemar_subset import (
    digest_file,
    official_response,
    safe_destination,
    sanitized_error,
    validate_entry,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'configs/kumar_first_fit_https_20261014.json'


def load_plan():
    raw = CONFIG.read_bytes()
    if hashlib.sha256(raw).hexdigest() != CONFIG.with_suffix('.sha256').read_text().strip():
        raise ValueError('Frozen HTTPS manifest hash mismatch')
    plan = json.loads(raw)
    if (len(plan['files']) != 25 or sum(e['size'] for e in plan['files']) != 16425499
            or plan['subject'] != 'sub-1' or plan['seed'] != 20261012):
        raise ValueError('Unreviewed scope')
    original_raw = (ROOT / 'research_logs/public_data_expansion_20261010/kumar2024_nm000177_v1.0.5_selection_manifest.json').read_bytes()
    if hashlib.sha256(original_raw).hexdigest() != plan['original_selection_sha256']:
        raise ValueError('Original selection manifest identity changed')
    original = json.loads(original_raw)
    original = {e['path']: e for e in original}
    for entry in plan['files']:
        validate_entry(entry, plan['official_prefix'])
        if {k:v for k,v in entry.items() if k != 'expected_sha256'} != original[entry['path']]:
            raise ValueError('Official source identity changed')
    return plan


def verify(path, entry):
    official, sha, size = digest_file(path, entry)
    if (size, official, sha) != (entry['size'], entry['checksum'], entry['expected_sha256']):
        raise ValueError('Size/official checksum/historical SHA256 mismatch')
    return sha


def fetch_one(root, entry, deadline, session_factory=requests.Session):
    target = safe_destination(root, entry['path'])
    if target.exists():
        verify(target, entry)
        return {'path':entry['path'], 'status':'reused_sha256_verified', 'sha256':entry['expected_sha256']}
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + '.partial')
    if partial.exists():
        raise FileExistsError('Preserved partial exists; inspect before a new attempt')
    with session_factory() as session, official_response(session, entry) as response:
        if response.status_code != 200:
            raise ValueError(f'Official HTTPS status {response.status_code}')
        length = response.headers.get('Content-Length')
        if length is not None and int(length) != entry['size']:
            raise ValueError('Content-Length mismatch')
        count = 0
        with partial.open('xb') as stream:
            for block in response.iter_content(chunk_size=128*1024):
                if time.monotonic() >= deadline:
                    raise TimeoutError('Operation deadline reached; partial preserved')
                count += len(block)
                if count > entry['size']:
                    raise ValueError('Response exceeds frozen byte count')
                stream.write(block)
            stream.flush()
            os.fsync(stream.fileno())
    verify(partial, entry)
    os.link(partial, target)  # Exclusive destination: cannot replace an existing file.
    partial.unlink()
    return {'path':entry['path'], 'status':'downloaded_sha256_verified', 'sha256':entry['expected_sha256']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    plan = load_plan()
    print(json.dumps({'files':25,'bytes':16425499,'edf':3,'execute':args.execute}))
    if not args.execute:
        return
    if args.receipt.exists():
        raise FileExistsError('Preserve existing receipt; choose a new attempt receipt')
    args.data_root.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(args.data_root).free < 16425499 + 5*1024**3:
        raise RuntimeError('Require data size plus 5 GiB reserve')
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    result = {'status':'started','config_sha256':hashlib.sha256(CONFIG.read_bytes()).hexdigest(),
              'records':[], 'real_training_executed':False, 'maximum_attempts_per_file':1}
    deadline = time.monotonic()+600
    try:
        for signal in (False, True):
            for entry in plan['files']:
                if entry['path'].endswith('.edf') != signal:
                    continue
                result['current_path'] = entry['path']
                if time.monotonic() >= deadline:
                    raise TimeoutError('Operation deadline reached')
                result['records'].append(fetch_one(args.data_root, entry, deadline))
                args.receipt.write_text(json.dumps(result, indent=2)+'\n')
            if not signal:
                description = json.loads((args.data_root/'dataset_description.json').read_text())
                if description.get('License') != 'CC-BY-4.0' or description.get('Version') != '1.0.5':
                    raise ValueError('License/version metadata gate failed')
        result['status'] = 'all_25_full_sha256_verified'
    except Exception as error:
        result.update(status='failed_preserved_inputs', error=sanitized_error(error))
        raise SystemExit('Download failed; see sanitized receipt. Files preserved.') from None
    finally:
        args.receipt.write_text(json.dumps(result,indent=2)+'\n')


if __name__ == '__main__':
    main()
