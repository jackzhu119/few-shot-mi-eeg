"""Disjoint-session baseline audit using existing frozen predictions; no fits."""
import argparse
import csv
import json
from pathlib import Path

from sklearn.metrics import balanced_accuracy_score

from learning_preserving_bci.datasets.netbci import file_sha256

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Preserve old audit')
    config_path=ROOT/'configs/netbci_date_separated.json'
    config=json.loads(config_path.read_text())
    base=ROOT/'research_logs/netbci_stage1_20261010/run01'
    events=list(csv.DictReader((base/'event_inventory.tsv').open(),delimiter='\t'))
    predictions=list(csv.DictReader((base/'predictions.tsv').open(),delimiter='\t'))
    assignment={}
    for t in events:
        if t['session']==config['training_session']:
            role='source_training' if t['run'] in config['source_training_runs'] else 'within_date_reference_query'
        elif t['run'] in config['excluded_calibration_runs']:
            role='unused_calibration'
        elif t['session']==config['validation_session']:
            role='validation_date'
        elif t['session'] in config['test_sessions']:
            role='test_dates'
        else:
            raise ValueError('Unexpected session')
        assignment[t['trial_id']]=role
    assert len(assignment)==len(events)==717
    assert not ({config['training_session']} & {config['validation_session']})
    assert not ({config['training_session'],config['validation_session']} & set(config['test_sessions']))
    rows=[]
    for family in sorted({p['decoder'] for p in predictions}):
        model=json.loads((base/f'{family}_model_audit.json').read_text())
        train=set(model['source_train_trial_ids'])
        assert train=={key for key,role in assignment.items() if role=='source_training'}
        assert model['query_state_unchanged'] and model['parameters_predefined_no_target_selection']
        for session in [config['validation_session'],*config['test_sessions']]:
            ps=[p for p in predictions if p['decoder']==family and p['session']==session]
            assert not (train & {p['trial_id'] for p in ps})
            rows.append({'decoder':family,'session':session,
                         'role':'validation_date' if session==config['validation_session'] else 'test_date',
                         'n':len(ps),'BA':float(balanced_accuracy_score([p['true_label'] for p in ps],[p['prediction'] for p in ps]))})
    receipt={'status':config['status'],'configuration':config,'training_validation_test_sessions_disjoint':True,
             'counts':{role:sum(r==role for r in assignment.values()) for role in set(assignment.values())},
             'results':rows,'existing_model_train_IDs_match':True,'test_data_fitted_or_selected_parameters':False,
             'prior_pilot_results_seen':True,'confirmatory_unseen_test_claim':False,
             'source_predictions_sha256':file_sha256(base/'predictions.tsv'),
             'config_sha256':file_sha256(config_path),'script_sha256':file_sha256(Path(__file__))}
    args.output.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(rows,indent=2))


if __name__=='__main__':
    main()
