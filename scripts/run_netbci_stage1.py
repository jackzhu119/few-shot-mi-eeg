"""Auditable one-subject longitudinal features and small frozen CPU baselines."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pickle
import time
from dataclasses import asdict
from pathlib import Path

import mne
import numpy as np
import torch
from scipy.linalg import helmert
from scipy.signal import butter, sosfiltfilt, welch
from sklearn.metrics import balanced_accuracy_score, confusion_matrix
from sklearn.preprocessing import StandardScaler

from learning_preserving_bci.datasets.netbci import file_sha256, load_netbci_bundle
from learning_preserving_bci.decoders.csp_lda import make_csp_lda
from learning_preserving_bci.decoders.eegnet import EEGNetClassifier
from learning_preserving_bci.neural_geometry import covariance_distance, fit_pca, subspace_distance
from learning_preserving_bci.utils.reproducibility import collect_provenance
from prepare_netbci_analysis import prepare

ROOT = Path(__file__).resolve().parents[1]


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False)+'\n')


def write_table(path, rows):
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, list(rows[0]), delimiter='\t')
        w.writeheader()
        w.writerows(rows)


def run_ci(y, prediction, runs, *, seed=42, repetitions=2000):
    """Conditional run-cluster percentile interval; never a participant CI."""
    y, prediction, runs = map(np.asarray, (y, prediction, runs))
    groups = np.unique(runs)
    if len(groups) < 2:
        return None
    rng = np.random.default_rng(seed)
    indices = {g: np.flatnonzero(runs == g) for g in groups}
    scores = []
    for _ in range(repetitions):
        idx = np.concatenate([indices[g] for g in rng.choice(groups, len(groups), replace=True)])
        if len(np.unique(y[idx])) == 2:
            scores.append(balanced_accuracy_score(y[idx], prediction[idx]))
    return np.quantile(scores, [0.025, 0.975]).tolist()


def model_digest(model):
    if isinstance(model, EEGNetClassifier):
        h = hashlib.sha256()
        for name, tensor in sorted(model.model_.state_dict().items()):
            h.update(name.encode())
            h.update(tensor.detach().cpu().numpy().tobytes())
        h.update(model.channel_mean_.tobytes())
        h.update(model.channel_scale_.tobytes())
        return h.hexdigest()
    return hashlib.sha256(pickle.dumps(model)).hexdigest()


def balanced_indices(trials, sessions, labels, per_class_run, seed, eligible=None):
    rng = np.random.default_rng(seed)
    chosen = {}
    for session in sessions:
        groups = sorted({t['run'] for t in trials if t['session'] == session})
        idx = []
        for run in groups:
            for label in labels:
                pool = [i for i, t in enumerate(trials) if t['session'] == session
                        and t['run'] == run and t['label'] == label
                        and (eligible is None or eligible[i])]
                if len(pool) < per_class_run:
                    raise ValueError('Insufficient class/run-matched trials')
                idx.extend(rng.choice(pool, per_class_run, replace=False).tolist())
        chosen[session] = np.asarray(idx)
    return chosen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT / 'configs/netbci_stage1.json')
    parser.add_argument('--bundle', type=Path, default=ROOT / 'data/netbci2026/derived_v1.0.0/sub-1')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    config = json.loads(args.config.read_text())
    torch.set_num_threads(config['threads'])
    mne.set_log_level('ERROR')
    subset = load_netbci_bundle(args.bundle)
    trials = [asdict(t) for t in subset.trials]
    plan = json.loads((ROOT / config['partition_config']).read_text())
    partitions = prepare(plan, trials)
    id_index = {t['trial_id']: i for i, t in enumerate(trials)}
    roles = {role: np.array([id_index[t] for t in p['trial_ids']])
             for role, p in partitions['partitions'].items()}
    # Metadata-only source mapping; same row confirmed by the independent event audit.
    original_root = ROOT / 'data/netbci2026/original_v2.2_metadata'
    behavior = json.loads((ROOT / 'research_logs/netbci_stage1_20261010/behavior_audit.json').read_text())
    by_run = {(r['session'], r['run']): r for r in behavior['runs']}
    events = []
    for t in trials:
        stem = f"sub-01_ses-{t['session']}_task-MotorImageryRest_run-{t['run']}"
        path = original_root / f"sub-01/ses-{t['session']}/eeg/{stem}_events.tsv"
        with path.open(encoding='utf-8-sig') as f:
            old = list(csv.DictReader(f, delimiter='\t'))[t['tsv_row']-1]
        run = by_run[t['session'], t['run']]
        events.append(dict(t, original_subject='sub-01', original_events_file=str(path.relative_to(ROOT)),
                           original_events_sha256=file_sha256(path), original_onset_s=old['onset'],
                           original_sample=old['sample'], original_value=old['value'],
                           original_duration_s=old['duration'],
                           original_sfreq_hz=run['original_sampling_frequency_hz'],
                           acquisition_date_status='anonymized_unresolved_actual_date',
                           trial_behavior_outcome='unresolved'))
    write_table(args.output / 'event_inventory.tsv', events)
    write_table(args.output / 'run_inventory.tsv', subset.run_table())
    X, y = subset.dataset.X, subset.dataset.y
    sfreq = subset.dataset.sfreq
    names = list(subset.dataset.channel_names)
    sessions = plan['session_order']
    # No baseline available: no ERD/ERS claim. Welch of stored task windows only.
    car = X - X.mean(axis=1, keepdims=True)
    cut = round(config['edge_crop_seconds'] * sfreq)
    raw_window = X[..., cut:-cut]
    car_window = car[..., cut:-cut]
    freq, psd = welch(car_window, fs=sfreq, window='hann', nperseg=config['welch_segment_samples'],
                      noverlap=config['welch_overlap_samples'], detrend='constant', scaling='density')
    _, raw_psd = welch(raw_window, fs=sfreq, window='hann', nperseg=config['welch_segment_samples'],
                       noverlap=config['welch_overlap_samples'], detrend='constant', scaling='density')
    bands = []
    for low, high in (config['mu_hz'], config['beta_hz']):
        mask = (freq >= low) & (freq <= high)
        bands.append(np.trapezoid(psd[..., mask], freq[mask], axis=-1))
    features = np.log10(np.maximum(np.concatenate(bands, axis=1), np.finfo(float).tiny))
    train = roles['reference_train']
    final_train = np.r_[train, roles['reference_validation']]
    # Source-only QC rule: flag rather than silently remove or reconstruct trials.
    peak_uv = np.ptp(X, axis=-1).max(axis=1) * 1e6
    log_peak = np.log10(np.maximum(peak_uv, 1e-12))
    median = np.median(log_peak[train])
    mad = 1.4826*np.median(np.abs(log_peak[train]-median))
    threshold = median + config['artifact_log_peak_MAD_multiplier']*max(mad, 1e-12)
    flat = (X.std(axis=-1)*1e6 < 0.1).any(axis=1)
    flagged = (log_peak > threshold) | flat
    trial_features = []
    roi = [names.index(c) for c in ('C3', 'Cz', 'C4')]
    for i, t in enumerate(trials):
        trial_features.append(dict(t, peak_to_peak_max_uv=float(peak_uv[i]), qc_flag=bool(flagged[i]),
                                   mu_ROI_V2=float(bands[0][i, roi].mean()),
                                   beta_ROI_V2=float(bands[1][i, roi].mean())))
    write_table(args.output / 'trial_features.tsv', trial_features)
    sos = butter(4, config['decoder_band_hz'], fs=sfreq, btype='bandpass', output='sos')
    filtered = sosfiltfilt(sos, car, axis=-1)[..., cut:-cut].copy()
    # Fixed analytical CAR coordinate basis, not learned from test data.
    basis = helmert(len(names), full=False)
    covariance = []
    for epoch in filtered:
        z = basis @ epoch
        z -= z.mean(axis=1, keepdims=True)
        cov = z @ z.T / (z.shape[1]-1)
        cov /= np.trace(cov)
        alpha = config['covariance_trace_shrinkage']
        covariance.append((1-alpha)*cov + alpha*np.eye(len(basis))/len(basis))
    covariance = np.asarray(covariance)
    scaler = StandardScaler().fit(features[final_train])
    standardized = scaler.transform(features)
    pca = fit_pca(standardized[final_train], config['pca_components'])
    projected = pca.transform(standardized)
    reference_cov = covariance[final_train].mean(axis=0)
    spectral = []
    for session in sessions:
        for label in np.unique(y):
            idx = np.array([i for i, t in enumerate(trials) if t['session']==session and t['label']==label])
            mean_psd = psd[idx][:, roi].mean(axis=(0, 1))
            orig_psd = raw_psd[idx][:, roi].mean(axis=(0, 1))
            for j, f in enumerate(freq):
                spectral.append({'session': session, 'label': label, 'frequency_hz': float(f),
                                 'CAR_ROI_PSD_V2_per_Hz': float(mean_psd[j]),
                                 'source_reference_ROI_PSD_V2_per_Hz': float(orig_psd[j])})
    write_table(args.output / 'spectra.tsv', spectral)
    run_rows = []
    for session in sessions:
        for run in sorted({t['run'] for t in trials if t['session']==session}):
            idx = np.array([i for i,t in enumerate(trials) if (t['session'],t['run'])==(session,run)])
            run_rows.append({'session':session, 'run':run, 'n':len(idx), 'qc_flagged':int(flagged[idx].sum()),
                             'mu_ROI_V2':float(bands[0][idx][:,roi].mean()),
                             'beta_ROI_V2':float(bands[1][idx][:,roi].mean()),
                             'AIRM_to_source_fit':covariance_distance(reference_cov,covariance[idx].mean(axis=0),regularization=0),
                             'PCA_mean_distance_to_source':float(np.linalg.norm(projected[idx].mean(axis=0)-projected[final_train].mean(axis=0)))})
    write_table(args.output/'run_features.tsv',run_rows)
    matched_rows = []
    for repetition in range(config['matched_repetitions']):
        chosen = balanced_indices(trials,sessions,np.unique(y),config['matched_trials_per_class_per_run'],
                                  config['seed']+repetition)
        # Session-specific PCA is solely descriptive; never enters a decoder or feature selection.
        source_idx = chosen[sessions[0]]
        source_cov = covariance[source_idx].mean(axis=0)
        source_space = fit_pca(standardized[source_idx],config['pca_components']).components_
        for session, idx in chosen.items():
            target_space = fit_pca(standardized[idx],config['pca_components']).components_
            groups = sorted({trials[i]['run'] for i in idx})
            within = []
            for a, ra in enumerate(groups):
                ca = covariance[[i for i in idx if trials[i]['run']==ra]].mean(axis=0)
                for rb in groups[a+1:]:
                    cb = covariance[[i for i in idx if trials[i]['run']==rb]].mean(axis=0)
                    within.append(covariance_distance(ca,cb,regularization=0))
            matched_rows.append({'repetition':repetition,'session':session,'n_matched':len(idx),
                                 'AIRM_to_session01':covariance_distance(source_cov,covariance[idx].mean(axis=0),regularization=0),
                                 'within_session_run_AIRM_mean':float(np.mean(within)),
                                 'PCA_subspace_distance':subspace_distance(source_space,target_space),
                                 'mu_ROI_V2':float(bands[0][idx][:,roi].mean()),
                                 'beta_ROI_V2':float(bands[1][idx][:,roi].mean())})
    write_table(args.output/'matched_geometry.tsv',matched_rows)
    evaluation = []
    predictions = []
    failures = []
    decoder_input = np.einsum('kc,nct->nkt',basis,filtered)
    for family in ('CSP_LDA','EEGNet_CPU_3epochs'):
        try:
            def factory():
                if family=='CSP_LDA':
                    return make_csp_lda(4)
                return EEGNetClassifier(len(basis),2,filtered.shape[-1],sfreq,
                                        epochs=config['eegnet_epochs'],batch_size=config['eegnet_batch_size'],
                                        learning_rate=config['eegnet_learning_rate'],seed=config['seed'])
            development = factory().fit(decoder_input[train],y[train])
            val = roles['reference_validation']
            val_score = float(balanced_accuracy_score(y[val],development.predict(decoder_input[val])))
            model = factory().fit(decoder_input[final_train],y[final_train])
            before = model_digest(model)
            for session in sessions:
                role = 'reference_query' if session==sessions[0] else 'target_query'
                idx = np.array([i for i in roles[role] if trials[i]['session']==session])
                pred = model.predict(decoder_input[idx])
                replay = model.predict(decoder_input[idx])
                assert np.array_equal(pred,replay), 'Prediction replay differs'
                runs = np.array([trials[i]['run'] for i in idx])
                clean = ~flagged[idx]
                clean_score = (float(balanced_accuracy_score(y[idx][clean],pred[clean]))
                               if len(np.unique(y[idx][clean]))==2 else None)
                evaluation.append({'decoder':family,'subject':'sub-1','session':session,'n_test':len(idx),
                                   'n_runs':len(np.unique(runs)), 'balanced_accuracy':float(balanced_accuracy_score(y[idx],pred)),
                                   'conditional_run_bootstrap_CI95':run_ci(y[idx],pred,runs,seed=config['seed'],repetitions=config['bootstrap_run_repetitions']),
                                   'confusion_matrix_rest_right_hand':confusion_matrix(y[idx],pred,labels=['rest','right_hand']).tolist(),
                                   'n_qc_flagged_query':int((~clean).sum()), 'qc_unflagged_BA':clean_score,
                                   'source_validation_BA':val_score, 'train_n':len(final_train),
                                   'participant_n':1,'CI_scope':'conditional run resampling; not participant/generalization CI'})
                predictions.extend({'decoder':family,'trial_id':trials[i]['trial_id'],'session':session,
                                    'run':trials[i]['run'],'true_label':str(y[i]),'prediction':str(p)}
                                   for i,p in zip(idx,pred,strict=True))
            after = model_digest(model)
            assert before==after,'Frozen parameters changed on query'
            model_info = {'family':family,'parameter_sha256_before_and_after':before,
                          'query_state_unchanged':True,'prediction_replay_exact':True,
                          'source_train_trial_ids':[trials[i]['trial_id'] for i in final_train],
                          'development_train_n':len(train),'source_validation_n':len(val),
                          'parameters_predefined_no_target_selection':True}
            if family.startswith('EEGNet'):
                torch.save(model.model_.state_dict(),args.output/'eegnet_weights.pt')
                model_info['loss_history']=model.loss_history_
                np.savez(args.output/'eegnet_normalization.npz',mean=model.channel_mean_,scale=model.channel_scale_)
            else:
                # Own locally fitted sklearn object; never deserialize untrusted artifacts.
                (args.output/'csp_lda.pkl').write_bytes(pickle.dumps(model))
            write_json(args.output/f'{family}_model_audit.json',model_info)
        except Exception as error:
            failures.append({'family':family,'type':type(error).__name__,'message':str(error)})
    write_json(args.output/'decoder_results.json',evaluation)
    if predictions:
        write_table(args.output/'predictions.tsv',predictions)
    write_json(args.output/'failures.json',failures)
    write_json(args.output/'partitions.json',partitions)
    np.savez(args.output/'reference_geometry.npz',pca_components=pca.components_,
             scaler_mean=scaler.mean_,scaler_scale=scaler.scale_,helmert=basis,reference_covariance=reference_cov)
    write_json(args.output/'analysis_receipt.json',{
        'status':'completed_exploratory' if not failures else 'completed_with_failures',
        'synthetic':False,'participants':1,'trials':len(trials),'shape':list(X.shape),
        'config':config,'config_sha256':file_sha256(args.config),'script_sha256':file_sha256(Path(__file__)),
        'bundle_sha256':file_sha256(args.bundle/'epochs.npz'),
        'metadata_sha256':file_sha256(args.bundle/'metadata.json'),
        'provenance':collect_provenance(config['seed'],ROOT),
        'duration_seconds':time.monotonic()-start,'qc_source_fit_train_n':len(train),
        'qc_log10_peak_uv_threshold':float(threshold),'qc_flagged_total':int(flagged.sum()),
        'QC_scope':'source-fit screening only; not expert artifact-free certification',
        'fixed_preprocessing':'CAR74, deterministic Helmert73, per-epoch zero-phase8-30Hz, crop0.5s each edge',
        'geometry_window':'[0.5,4.5)s stored task window; no prestimulus ERD',
        'target_transforms_fitted':False,'target_descriptive_PCA_only':True,
        'limitations':['one participant','unverified behavior run order/denominator',
                       'anonymized scan dates','no causal human learning or retention inference'],
        'outputs':{p.name:file_sha256(p) for p in args.output.iterdir() if p.is_file()}})
    print(json.dumps({'output':str(args.output),'decoder_results':evaluation,'failures':failures},indent=2))


if __name__=='__main__':
    main()
