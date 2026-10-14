"""Replay the public MIND V4 metadata census; never requests EEG signal files."""
from __future__ import annotations
import argparse, collections, concurrent.futures, csv, datetime, hashlib, io, json, platform, re, subprocess, sys
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent
DEST = ROOT / 'census_metadata'
BASE = '/V4/MIND_BIDS/'
DIRECTION_CODES = {'mi_l2r':'4', 'mi_t2b':'5', 'mi_ul2lr':'6', 'mi_ur2ll':'7'}
CENSUS_SUFFIXES = ('_events.json', '_events.tsv', '_eeg.json', '_channels.tsv')

def utcnow():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def normalized_md5(value):
    if not value:
        return None
    if not re.fullmatch(r'[0-9a-fA-F]{1,32}', value):
        raise ValueError('Invalid inventory MD5')
    return value.lower().zfill(32)

def eligible(record):
    path = record['path']
    return not record['dir'] and (path[len(BASE):] in ('.bidsignore', 'README.md', 'dataset_description.json', 'participants.json', 'participants.tsv', 'LICENSE', 'LICENSE.txt', 'CHANGES') or (re.fullmatch(r'/V4/MIND_BIDS/sub-\d{2}/eeg/[^/]+', path) and path.endswith(CENSUS_SUFFIXES)))

def download_one(record):
    assert eligible(record), 'Only selected lightweight metadata may be requested'
    relative = record['path'].removeprefix(BASE)
    target = DEST / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    expected = int(record['size'])
    url = 'https://china.scidb.cn/download?fileId=' + record['id']
    expected_hash = normalized_md5(record.get('md5', ''))
    result = {'official_record':record, 'official_file_id':record['id'], 'version':record['version'], 'official_md5_exact':record.get('md5', ''), 'official_md5_normalized':expected_hash, 'official_bytes':expected, 'download_endpoint':url, 'local_relative_path':relative}
    if target.exists():
        content = target.read_bytes()
        if len(content) == expected and hashlib.md5(content).hexdigest() == expected_hash:
            result.update({'checked_at_utc':utcnow(), 'http_status':None, 'reused_verified_local_bytes':True, 'actual_bytes':len(content), 'actual_md5':hashlib.md5(content).hexdigest(), 'actual_sha256':hashlib.sha256(content).hexdigest(), 'size_verified':True, 'md5_verified':True})
            return result
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=30, allow_redirects=False, stream=True)
            result.update({'checked_at_utc':utcnow(), 'http_status':response.status_code, 'headers':{key:value for key,value in response.headers.items() if key.lower() not in ('set-cookie', 'location')}, 'redirect_followed':False})
            if response.status_code != 200:
                response.close()
                raise RuntimeError(f'Public download returned HTTP {response.status_code}')
            # Read at most declared metadata bytes + 1, preserving the original bytes.
            content = response.raw.read(expected + 1)
            response.close()
            actual_md5 = hashlib.md5(content).hexdigest()
            result.update({'actual_bytes':len(content), 'actual_md5':actual_md5, 'actual_sha256':hashlib.sha256(content).hexdigest(), 'size_verified':len(content)==expected, 'md5_verified':actual_md5==expected_hash, 'reused_verified_local_bytes':False})
            if len(content) != expected or (expected_hash and actual_md5 != expected_hash):
                raise RuntimeError('Metadata length or MD5 does not match official inventory')
            target.write_bytes(content)
            return result
        except (requests.RequestException, RuntimeError) as error:
            result['last_error'] = str(error).split('?')[0]
            if attempt == 2:
                result['failed'] = True
                return result
    raise AssertionError('unreachable')

def load_tsv(path):
    return list(csv.DictReader(io.StringIO(path.read_text(encoding='utf-8-sig')), delimiter='\t'))

def summarize(records, downloaded):
    participants = load_tsv(DEST/'participants.tsv')
    subject_ids = [row['participant_id'] for row in participants]
    run_rows = []
    anomaly_rows = []
    aggregate = collections.Counter()
    per_subject = {}
    for subject in subject_ids:
        runs = sorted((DEST/subject/'eeg').glob('*_events.tsv'))
        subject_counts = collections.Counter()
        for path in runs:
            rows = load_tsv(path)
            run_match = re.search(r'_run-(\d+)_',path.name)
            run_id = run_match.group(1) if run_match else None
            eeg_json_path = path.with_name(path.name.replace('_events.tsv','_eeg.json'))
            events_json = json.loads(path.with_suffix('.json').read_text())
            eeg_json = json.loads(eeg_json_path.read_text())
            channels = load_tsv(path.with_name(path.name.replace('_events.tsv','_channels.tsv')))
            expected_codes = {kind:code for kind,code in DIRECTION_CODES.items()}
            previous_onset = None
            monotonic = True
            nonfinite = []
            intervals = []
            last_mi_onset = None
            mi_events = []
            cues = []
            flags = []
            for index,row in enumerate(rows):
                onset = float(row['onset']); duration = float(row['duration'])
                if previous_onset is not None and onset < previous_onset:
                    monotonic=False
                previous_onset=onset
                if onset < 0 or duration < 0:
                    flags.append({'issue':'negative_onset_or_duration','row_0based':index,'row':row})
                kind = row['trial_type']
                if kind in expected_codes:
                    mi_events.append({'row_0based':index,'onset':onset,'duration':duration,'trial_type':kind,'value':row['value']})
                    if row['value'] != expected_codes[kind]:
                        flags.append({'issue':'direction_event_code_mismatch','row_0based':index,'row':row})
                    if duration != 10.0:
                        flags.append({'issue':'mi_duration_not_10_seconds','row_0based':index,'row':row})
                    if last_mi_onset is not None:
                        intervals.append(onset-last_mi_onset)
                    last_mi_onset=onset
                elif kind == 'mi_start':
                    cues.append({'row_0based':index,'onset':onset,'duration':duration,'value':row['value']})
                elif kind not in ('rest_open','rest_closed'):
                    flags.append({'issue':'unknown_trial_type','row_0based':index,'row':row})
            if not monotonic:
                flags.append({'issue':'nonmonotonic_event_onsets'})
            counts = collections.Counter(row['trial_type'] for row in mi_events)
            aggregate.update(counts);subject_counts.update(counts)
            # The two 20-trial blocks are within the same public continuous run.
            halves = []
            for half_index in range(2):
                items = mi_events[half_index*20:(half_index+1)*20]
                half_counts = collections.Counter(item['trial_type'] for item in items)
                cue = cues[half_index] if len(cues)>half_index else None
                halves.append({'half_1based':half_index+1, 'n_mi_trials':len(items), 'direction_counts':dict(half_counts), 'direction_sequence':[item['trial_type'] for item in items], 'first_mi_onset_seconds':items[0]['onset'] if items else None, 'last_mi_onset_seconds':items[-1]['onset'] if items else None, 'mi_start_cue':cue, 'cue_to_first_mi_seconds':items[0]['onset']-cue['onset'] if items and cue else None, 'within_half_intervals_seconds':[items[i+1]['onset']-items[i]['onset'] for i in range(len(items)-1)]})
            if len(mi_events)!=40:
                flags.append({'issue':'mi_trial_count_not_40','actual':len(mi_events)})
            if counts!=collections.Counter({kind:10 for kind in DIRECTION_CODES}):
                flags.append({'issue':'per_run_four_direction_counts_not_10_each','actual':dict(counts)})
            if len(cues)!=2:
                flags.append({'issue':'mi_start_cue_count_not_2','actual':len(cues)})
            if set(halves[0]['direction_counts']) != {'mi_l2r','mi_t2b'} or set(halves[1]['direction_counts']) != {'mi_ul2lr','mi_ur2ll'}:
                flags.append({'issue':'half_direction_pair_differs_from_readme'})
            within = [value for half in halves for value in half['within_half_intervals_seconds']]
            unusual = [{'half_1based':half['half_1based'],'between_mi_trials_0based':index,'interval_seconds':value} for half in halves for index,value in enumerate(half['within_half_intervals_seconds']) if not 26.8 <= value <= 27.2]
            if unusual:
                flags.append({'issue':'within_half_interval_outside_26_8_to_27_2_seconds','details':unusual,'threshold_is_census_screen_only':True})
            entry = {'subject_id':subject,'run_id':run_id,'event_file':str(path.relative_to(DEST)),'events_total':len(rows),'trial_type_counts':dict(collections.Counter(row['trial_type'] for row in rows)),'mi_trials':len(mi_events),'mi_direction_counts':dict(counts),'mi_duration_counts':dict(collections.Counter(str(row['duration']) for row in mi_events)),'onsets_monotonic_nondecreasing':monotonic,'first_event_onset_seconds':float(rows[0]['onset']) if rows else None,'last_event_end_seconds':max(float(row['onset'])+float(row['duration']) for row in rows) if rows else None,'halves':halves,'between_half_last_to_first_mi_onset_seconds':halves[1]['first_mi_onset_seconds']-halves[0]['last_mi_onset_seconds'] if all(half['n_mi_trials'] for half in halves) else None,'sampling_frequency':eeg_json.get('SamplingFrequency'),'eeg_channel_count':eeg_json.get('EEGChannelCount'),'channels_tsv_count':len(channels),'channels_type_counts':dict(collections.Counter(row.get('type') for row in channels)),'channels_status_counts':dict(collections.Counter(row.get('status') for row in channels)),'raw_eeg_json':eeg_json,'raw_events_json':events_json,'flags':flags}
            run_rows.append(entry)
            anomaly_rows.extend({'subject_id':subject,'run_id':run_id,**flag} for flag in flags)
        per_subject[subject]={'n_runs':len(runs),'mi_direction_counts':dict(subject_counts),'mi_trials':sum(subject_counts.values())}
    summary={'checked_at_utc':utcnow(),'dataset_id':'d0f67f38c5bc4416bdcce619f33e57da','version':'V4','selection':'root metadata plus all EEG run events.json/events.tsv/eeg.json/channels.tsv; no signal bodies','metadata_file_count':len(downloaded),'downloaded_metadata_bytes':sum(row.get('actual_bytes',0) for row in downloaded),'all_metadata_md5_and_size_verified':all(row.get('size_verified') and row.get('md5_verified') for row in downloaded),'participant_count':len(participants),'unique_participant_count':len(set(subject_ids)),'participant_ids':subject_ids,'raw_participant_rows':participants,'handedness_counts':dict(collections.Counter(row['handedness'] for row in participants)),'run_count':len(run_rows),'runs_per_subject':per_subject,'all_subjects_have_three_runs':all(row['n_runs']==3 for row in per_subject.values()),'total_mi_trials':sum(aggregate.values()),'mi_direction_counts':dict(aggregate),'all_mi_duration_10_seconds':all(set(row['mi_duration_counts'])=={'10.0'} for row in run_rows),'all_onsets_monotonic_nondecreasing':all(row['onsets_monotonic_nondecreasing'] for row in run_rows),'sampling_frequency_counts':dict(collections.Counter(str(row['sampling_frequency']) for row in run_rows)),'eeg_channel_count_counts':dict(collections.Counter(str(row['eeg_channel_count']) for row in run_rows)),'flag_count':len(anomaly_rows),'flags':anomaly_rows,'source_level_limitations':['Published onset/duration/event codes were inspected; no claim of true EEG-fNIRS temporal alignment is made.','Fixed direction pairs occupy different within-run halves; direction and half/time position are confounded.','Manual event corrections and original vendor markers require separate provenance review; this census preserves published metadata rather than relabeling.','Repository license is CC BY-NC 4.0; BIDS dataset_description states CC BY 4.0. Both allow noncommercial research; this does not reconcile the license declarations.'],'root_required_files_present':{name:any(row['path']==BASE+name for row in records) for name in ['README.md','LICENSE','LICENSE.txt','dataset_description.json','participants.json','participants.tsv','CHANGES']},'signal_bodies_downloaded':0}
    (ROOT/'census_runs.json').write_text(json.dumps(run_rows,ensure_ascii=False,indent=2))
    (ROOT/'census_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    with (ROOT/'census_runs.tsv').open('w') as stream:
        writer=csv.DictWriter(stream,fieldnames=['subject_id','run_id','mi_trials','mi_direction_counts','events_total','sampling_frequency','eeg_channel_count','channels_tsv_count','onsets_monotonic_nondecreasing','flags'],delimiter='\t');writer.writeheader()
        for row in run_rows:
            writer.writerow({key:json.dumps(row[key]) if isinstance(row[key],(dict,list)) else row[key] for key in writer.fieldnames})
    return summary

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--summarize-only',action='store_true');args=parser.parse_args()
    inventory=json.loads((ROOT/'inventory_manifest.json').read_text())
    selected=[row for row in inventory['records'] if eligible(row)]
    if args.summarize_only:
        downloaded=json.loads((ROOT/'census_download_manifest.json').read_text())['files']
    else:
        DEST.mkdir(exist_ok=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
            downloaded=list(executor.map(download_one, selected))
        failed=[row for row in downloaded if row.get('failed')]
        manifest={'checked_at_utc':utcnow(),'version':'V4','source_inventory_sha256':hashlib.sha256((ROOT/'inventory_manifest.json').read_bytes()).hexdigest(),'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),'python':sys.version,'requests_version':requests.__version__,'seed':None,'selection_count':len(selected),'selection_official_bytes':sum(row['size'] for row in selected),'files':downloaded,'failed_count':len(failed),'signal_bodies_downloaded':0}
        (ROOT/'census_download_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
        print('Downloaded metadata',len(downloaded),'failures',len(failed),flush=True)
        if failed:
            print(json.dumps([{'path':row['official_record']['path'],'error':row.get('last_error')} for row in failed],indent=2));sys.exit(1)
    summary=summarize(inventory['records'],downloaded)
    print(json.dumps({key:summary[key] for key in ['metadata_file_count','downloaded_metadata_bytes','all_metadata_md5_and_size_verified','participant_count','run_count','total_mi_trials','mi_direction_counts','all_onsets_monotonic_nondecreasing','flag_count']},indent=2),flush=True)

if __name__=='__main__':
    main()
