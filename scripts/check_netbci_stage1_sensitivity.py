"""Post-observation QC and equal-count sensitivity; no decoder tuning."""
import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
from scipy.linalg import helmert
from scipy.signal import butter, sosfiltfilt

from learning_preserving_bci.datasets.netbci import file_sha256, load_netbci_bundle
from learning_preserving_bci.neural_geometry import covariance_distance
from run_netbci_stage1 import balanced_indices, write_json, write_table

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    bundle = load_netbci_bundle(ROOT / 'data/netbci2026/derived_v1.0.0/sub-1')
    config = json.loads((args.run/'analysis_receipt.json').read_text())['config']
    trials = [asdict(t) for t in bundle.trials]
    with (args.run/'trial_features.tsv').open() as f:
        features = list(csv.DictReader(f, delimiter='\t'))
    assert [t['trial_id'] for t in features]==[t['trial_id'] for t in trials]
    eligible = np.array([t['qc_flag']=='False' for t in features])
    sessions = ['01','02','03','04']
    labels = np.unique(bundle.dataset.y)
    per_class = config['matched_trials_per_class_per_run']
    # Keep the same run numbers in all sessions, not cherry-pick a session-specific set.
    common_runs = [r for r in sorted({t['run'] for t in trials})
                   if all(sum(eligible[i] and t['session']==s and t['run']==r and t['label']==label
                              for i,t in enumerate(trials)) >= per_class
                          for s in sessions for label in labels)]
    if not common_runs:
        raise ValueError('No common run has enough unflagged trials; sensitivity unresolved')
    allowed = eligible & np.array([t['run'] in common_runs for t in trials])
    # Restrict table to common runs so matching does not demand excluded runs.
    select = np.flatnonzero(np.array([t['run'] in common_runs for t in trials]))
    selected_trials = [trials[i] for i in select]
    X = bundle.dataset.X
    car = X-X.mean(axis=1,keepdims=True)
    sos = butter(4,config['decoder_band_hz'],fs=bundle.dataset.sfreq,btype='bandpass',output='sos')
    cut = round(config['edge_crop_seconds']*bundle.dataset.sfreq)
    filtered = sosfiltfilt(sos,car,axis=-1)[...,cut:-cut]
    basis = helmert(X.shape[1],full=False)
    covs=[]
    for epoch in filtered:
        z=basis@epoch
        z-=z.mean(axis=1,keepdims=True)
        cov=z@z.T/(z.shape[1]-1)
        cov/=np.trace(cov)
        alpha=config['covariance_trace_shrinkage']
        covs.append((1-alpha)*cov+alpha*np.eye(len(basis))/len(basis))
    covs=np.array(covs)
    rows=[]
    for rep in range(config['matched_repetitions']):
        chosen=balanced_indices(selected_trials,sessions,labels,per_class,config['seed']+rep,
                                eligible=allowed[select])
        chosen={s:select[idx] for s,idx in chosen.items()}
        reference=covs[chosen['01']].mean(axis=0)
        for session,idx in chosen.items():
            rows.append({'repetition':rep,'session':session,'common_runs':','.join(common_runs),
                         'n_matched':len(idx),'AIRM_to_session01':covariance_distance(reference,covs[idx].mean(axis=0),regularization=0)})
    write_table(args.output/'qc_matched_geometry.tsv',rows)
    # Reference sensitivity of published task-window PSD, not refitting a predictive model.
    spectra=list(csv.DictReader((args.run/'spectra.tsv').open(),delimiter='\t'))
    power_rows=[]
    for session in sessions:
        for label in labels:
            selected=[r for r in spectra if r['session']==session and r['label']==label]
            freq=np.array([float(r['frequency_hz']) for r in selected])
            for name,(low,high) in [('mu',config['mu_hz']),('beta',config['beta_hz'])]:
                mask=(freq>=low)&(freq<=high)
                car_power=np.trapezoid([float(r['CAR_ROI_PSD_V2_per_Hz']) for r,m in zip(selected,mask,strict=True) if m],freq[mask])
                raw_power=np.trapezoid([float(r['source_reference_ROI_PSD_V2_per_Hz']) for r,m in zip(selected,mask,strict=True) if m],freq[mask])
                power_rows.append({'session':session,'label':str(label),'band':name,'CAR_V2':car_power,
                                   'source_reference_V2':raw_power,'CAR_to_source_reference_ratio':car_power/raw_power})
    write_table(args.output/'reference_bandpower_sensitivity.tsv',power_rows)
    # Reconcile runs without another model fit or any target-driven choices.
    first=args.run
    second=first.parent/'run02_replay'
    keys=['event_inventory.tsv','trial_features.tsv','run_features.tsv','matched_geometry.tsv',
          'predictions.tsv','decoder_results.json']
    exact={key:file_sha256(first/key)==file_sha256(second/key) for key in keys}
    assert all(exact.values()),'Independent complete rerun changed deterministic outputs'
    for family in ['CSP_LDA','EEGNet_CPU_3epochs']:
        a=json.loads((first/f'{family}_model_audit.json').read_text())
        b=json.loads((second/f'{family}_model_audit.json').read_text())
        assert a['parameter_sha256_before_and_after']==b['parameter_sha256_before_and_after']
    pred=list(csv.DictReader((first/'predictions.tsv').open(),delimiter='\t'))
    failure_cases=[]
    for family in ['CSP_LDA','EEGNet_CPU_3epochs']:
        for session in sessions:
            p=[r['prediction'] for r in pred if r['decoder']==family and r['session']==session]
            if len(set(p))==1:
                failure_cases.append({'decoder':family,'session':session,'failure':'constant prediction',
                                      'predicted_class':p[0],'CI_warning':'run-bootstrap interval degenerates; not certainty or evidence of chance mechanism'})
    write_json(args.output/'sensitivity_receipt.json',{
        'status':'exploratory_post_observation_sensitivity','common_run_ids':common_runs,
        'minimum_clean_trials_per_class_run':per_class,'QC_does_not_certify_artifact_free':True,
        'source_fitted_QC_used':True,'independent_rerun_output_hashes_equal':exact,
        'decoder_failure_cases':failure_cases,'no_decoder_refit_or_target_tuning':True,
        'script_sha256':file_sha256(Path(__file__))})
    print(json.dumps({'common_runs':common_runs,'replay_equal':exact,'decoder_failure_cases':failure_cases},indent=2))


if __name__=='__main__':
    main()
