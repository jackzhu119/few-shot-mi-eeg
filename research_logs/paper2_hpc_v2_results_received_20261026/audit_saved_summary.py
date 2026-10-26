"""Reconcile saved exported histories and summaries without weights/EEG/inference."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('packet_directory', type=Path)
args = parser.parse_args()
root = args.packet_directory.resolve()
source = root / 'source_code'
sys.path.insert(0, str(source))
from hpc_recalibration.preflight import load_config
from hpc_recalibration.summarize import summarize
config = load_config(source / 'configs/kumar_dev_hpc_gpu1_24cpu.json')
config['output_root'] = str(root / 'results')
config['project_dir'] = str(source)
config['tasks_file'] = str(source / 'configs/tasks_kumar_dev.json')
with tempfile.TemporaryDirectory(prefix='saved-summary-check-') as temporary:
    target = Path(temporary)
    repeated = summarize(config, destination=target)
    original = json.loads((root / 'analysis/summary.json').read_text())
    for value in (repeated, original):
        value.pop('created_at', None)
    assert repeated == original, 'Summary values differ'
    csvs = []
    for path in sorted((root / 'analysis').glob('*.csv')):
        assert path.read_bytes() == (target / path.name).read_bytes(), path.name
        csvs.append({'file': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'byte_identical': True})
counts = collections.Counter()
epochs = steps = 0
sources = []
for path in sorted((root / 'training_records').rglob('checkpoint.pt.json')):
    state = json.loads(path.read_text())
    role = 'source' if '/source/' in path.as_posix() else 'adaptation'
    assert state['complete'] is True and state['epoch'] == (100 if role == 'source' else 20), path
    assert len(state['history']) == state['epoch'], path
    assert [h['epoch'] for h in state['history']] == list(range(1, state['epoch']+1)), path
    counts[role] += 1
    epochs += state['epoch']
    steps += state['step']
    if role == 'source':
        candidates = [h for h in state['history'] if 'validation_loss' in h]
        best = min(candidates, key=lambda h: h['validation_loss'])
        assert state['best_epoch'] == best['epoch'] and state['best_loss'] == best['validation_loss'], path
        sources.append({'file': path.relative_to(root).as_posix(), 'best_epoch': state['best_epoch'], 'best_validation_loss': state['best_loss']})
assert counts == {'source':18, 'adaptation':1350}, counts
classical = list((root / 'training_records').rglob('*.npz.json'))
assert len(classical) == 1206, len(classical)
receipt = {'scope':'Saved predictions/metadata/statistics only; no model binary, training, inference, EEG or host operation',
           'summary_values_identical_except_created_at':True,'csv_checks':csvs,
           'current_checkpoint_metadata_counts':dict(counts),'classical_model_metadata_count':len(classical),
           'current_completed_epochs':epochs,'current_completed_optimizer_steps':steps,
           'source_validation_epoch_selections':sources,'failed_checks':[],
           'note':'Recorded model state immutability and training claims are metadata evidence; not independent checkpoint replay.'}
(root.parent / 'independent_summary_audit.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k not in ('csv_checks','source_validation_epoch_selections')},indent=2))
