"""One source-only development fit, followed by mandatory full-GET R2 backup.

Parent coordinates GPU use. This entry point never reads query or final subjects.
A partial local output is preserved on failure; complete fits are restored, not refit.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import torch

from learning_preserving_bci.datasets.kumar import load_subject
from learning_preserving_bci.utils.reproducibility import collect_provenance
from restore_kumar_r2 import PROTOCOL, ROOT, SPLIT, digest
from sync_research_r2 import build_client
from train_kumar_eegnet import (
    SourceOnlyEEGNet,
    load_checkpoint,
    save_checkpoint,
    source_arrays,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    backup_options = parser.add_mutually_exclusive_group(required=True)
    backup_options.add_argument('--backup-prefix')
    backup_options.add_argument('--backup-capability', type=Path)
    parser.add_argument('--subject', choices=['sub-1', 'sub-4', 'sub-7', 'sub-10', 'sub-13', 'sub-16'], required=True)
    parser.add_argument('--seed', type=int, choices=[20261012, 20261013, 20261014], required=True)
    args = parser.parse_args()
    config_path = ROOT / 'configs/kumar_eegnet_gpu_development_20261014.json'
    config = json.loads(config_path.read_text())
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable; no CPU fallback')
    if args.backup_capability:
        payload = json.loads(args.backup_capability.read_text())
        if payload.get('mode') != 'backup':
            raise ValueError('Wrong backup capability')
    else:
        client, bucket, _ = build_client()
        client.head_bucket(Bucket=bucket)  # Prove existing off-machine destination before fitting.
    torch.set_num_threads(config['threads'])
    output = args.output.resolve()
    done = output / 'completed.json'
    if done.exists():
        record = json.loads(done.read_text())
        if (record['subject'], record['seed'], record['config_sha256']) != (
                args.subject, args.seed, digest(config_path)):
            raise ValueError('Existing fit belongs to a different job')
        load_checkpoint(output / 'weights.pt', expected_sha256=record['checkpoint_sha256'])
    else:
        output.mkdir(parents=True, exist_ok=False)
        started = time.monotonic()
        subject = load_subject(args.data_root, args.subject, PROTOCOL, split_manifest=SPLIT,
                               allowed_roles={'source_train', 'source_validation'})
        source = source_arrays(subject)
        model = SourceOnlyEEGNet(config, args.seed).fit_source(*source)
        saved = save_checkpoint(model, output / 'weights.pt', synthetic=False,
                                software_validation_only=False)
        restored = load_checkpoint(output / 'weights.pt', expected_sha256=saved['checkpoint_sha256'])
        import numpy as np
        if not np.array_equal(model.predict_proba(source[2]), restored.predict_proba(source[2])):
            raise RuntimeError('Development validation checkpoint replay failed')
        record = dict(subject=args.subject, seed=args.seed, config_sha256=digest(config_path),
                      checkpoint_sha256=saved['checkpoint_sha256'], synthetic=False,
                      query_rows_loaded=0, formal_query_evaluation=False,
                      source_train_count=len(source[0]), source_validation_count=len(source[2]),
                      selected_epoch=model.selected_epoch_, runtime_seconds=time.monotonic()-started,
                      peak_cuda_memory_bytes=torch.cuda.max_memory_allocated(),
                      provenance=collect_provenance(args.seed, ROOT),
                      script_sha256=digest(__file__), split_sha256=digest(SPLIT),
                      verified_source_files=subject.provenance['verified_source_files'])
        done.write_text(json.dumps(record, indent=2, allow_nan=False))
    if args.backup_capability:
        from paper2_signed_transfer import backup
        backup(args.backup_capability, output)
        return
    receipt = output.parent / (output.name + f'-backup-{time.time_ns()}.json')
    subprocess.run([sys.executable, str(ROOT / 'scripts/sync_research_r2.py'),
                    '--source', str(output), '--key-prefix', args.backup_prefix,
                    '--receipt', str(receipt), '--execute', '--readback-mode', 'all',
                    '--workers', '1'], check=True)
    backed = json.loads(receipt.read_text())
    if backed['totals']['failed_files'] or backed['totals']['full_get_sha256_verified_files'] != backed['totals']['planned_files']:
        raise RuntimeError('Incomplete off-machine backup; do not shut down')
    print(json.dumps(dict(status='source_fit_and_full_get_backup_complete', receipt=str(receipt))))


if __name__ == '__main__':
    main()
