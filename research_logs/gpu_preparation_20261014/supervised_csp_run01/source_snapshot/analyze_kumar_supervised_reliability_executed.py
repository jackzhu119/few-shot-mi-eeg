"""Development-only supervised CSP reliability. No query, policy or threshold search."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import mne
import numpy as np
from sklearn.metrics import balanced_accuracy_score

from analyze_kumar_lowdim_reliability import (
    array_digest,
    participant_bootstrap,
    support_phase_alignment_control,
)
from learning_preserving_bci.datasets.kumar import load_subject
from learning_preserving_bci.decoders.csp_lda import make_csp_lda
from learning_preserving_bci.utils.reproducibility import collect_provenance
from restore_kumar_r2 import PROTOCOL, ROOT, SPLIT, digest

CONFIG = ROOT / 'configs/kumar_supervised_reliability_20261014.json'


def analyze(subject, seed, permutations):
    metadata, x, y = subject.metadata, subject.X, subject.y
    if any(t['role'] not in {'source_train', 'target_support'} for t in metadata):
        raise ValueError('Disallowed input role')
    source = np.array([i for i, t in enumerate(metadata) if t['role'] == 'source_train'])
    rng = np.random.default_rng(seed)
    folds = []
    for run in ('run-0', 'run-1'):
        train = np.array([i for i in source if metadata[i]['run'] == run])
        test = np.array([i for i in source if metadata[i]['run'] != run])
        model = make_csp_lda(4).fit(x[train], y[train])
        prediction = model.predict(x[test])
        null = []
        for _ in range(permutations):
            shuffled = rng.permutation(y[train])
            control = make_csp_lda(4).fit(x[train], shuffled)
            null.append(float(balanced_accuracy_score(y[test], control.predict(x[test]))))
        folds.append(dict(train_ids=[metadata[i]['trial_id'] for i in train],
                          holdout_ids=[metadata[i]['trial_id'] for i in test],
                          labels=y[test].tolist(), predictions=prediction.tolist(),
                          balanced_accuracy=float(balanced_accuracy_score(y[test], prediction)),
                          negative_control_balanced_accuracy=null))
    model = make_csp_lda(4).fit(x[source], y[source])
    csp = model.named_steps['csp']
    features = csp.transform(x)
    state_hash = array_digest(csp.filters_)
    support = []
    for session in [f'ses-{i}' for i in range(1, 6)]:
        idx = np.array([i for i, t in enumerate(metadata)
                        if t['role'] == 'target_support' and t['session'] == session])
        support.append(dict(session=session, n=len(idx),
                            trial_ids=[metadata[i]['trial_id'] for i in idx],
                            **support_phase_alignment_control(features[source], y[source],
                                                              features[idx], y[idx])))
    if state_hash != array_digest(csp.filters_):
        raise RuntimeError('Support changed supervised source representation')
    return dict(folds=folds, support=support, csp_filter_sha256=state_hash,
                source_fit_ids=[metadata[i]['trial_id'] for i in source],
                source_twofold_balanced_accuracy=float(np.mean([f['balanced_accuracy'] for f in folds])),
                input_numeric_sha256=array_digest(x), input_count=len(x),
                source_count=len(source), verified_source_files=subject.provenance['verified_source_files'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(CONFIG.read_text())
    protocol = json.loads(PROTOCOL.read_text())
    if config['development_subjects'] != protocol['development_subjects']:
        raise ValueError('Development cohort changed')
    if config['allowed_roles'] != ['source_train', 'target_support'] or config['csp_components'] != 4:
        raise ValueError('Unreviewed diagnostic configuration')
    args.output.mkdir(parents=True, exist_ok=False)
    frozen = dict(config_sha256=digest(CONFIG), protocol_sha256=digest(PROTOCOL),
                  split_sha256=digest(SPLIT), script_sha256=digest(__file__),
                  adapter_sha256=digest(ROOT / 'src/learning_preserving_bci/datasets/kumar.py'))
    (args.output / 'before_fit_freeze.json').write_text(json.dumps(frozen, indent=2))
    mne.set_log_level('ERROR')
    results = {}
    for name in config['development_subjects']:
        subject = load_subject(args.data_root, name, protocol, split_manifest=SPLIT,
                               allowed_roles=set(config['allowed_roles']))
        results[name] = analyze(subject, config['seed'], config['negative_control_replicates'])
        (args.output / f'{name}.json').write_text(json.dumps(results[name], indent=2, allow_nan=False))
    ba = {s: r['source_twofold_balanced_accuracy'] for s, r in results.items()}
    cosine = {s: float(np.mean([v['observed']['support_split_half_direction_cosine']
                                for v in r['support']])) for s, r in results.items()}
    summary = dict(status='completed_exploratory_diagnostic', synthetic=False,
                   source_ba=participant_bootstrap(ba, config['seed'], config['bootstrap_replicates']),
                   support_half_cosine=participant_bootstrap(cosine, config['seed'], config['bootstrap_replicates']),
                   query_rows_loaded=0, final_subjects_loaded=0, threshold_search=False,
                   gate_implemented=False, input_count=sum(r['input_count'] for r in results.values()),
                   source_count=sum(r['source_count'] for r in results.values()),
                   freeze=frozen, provenance=collect_provenance(config['seed'], ROOT))
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False))
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
