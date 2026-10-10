"""Event-relative PSD without a prestimulus baseline; does not estimate ERD."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy.signal import spectrogram

from learning_preserving_bci.datasets.netbci import file_sha256, load_netbci_bundle

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    bundle=load_netbci_bundle(ROOT/'data/netbci2026/derived_v1.0.0/sub-1')
    X=bundle.dataset.X
    roi=[list(bundle.dataset.channel_names).index(c) for c in ['C3','Cz','C4']]
    car=X-X.mean(axis=1,keepdims=True)
    freq,times,density=spectrogram(car[:,roi,:],fs=bundle.dataset.sfreq,window='hann',nperseg=250,
                                  noverlap=125,detrend='constant',scaling='density',mode='psd',axis=-1)
    mask=(freq>=4)&(freq<=40)
    rows=[]
    for session in ['01','02','03','04']:
        for label in np.unique(bundle.dataset.y):
            idx=[i for i,t in enumerate(bundle.trials) if t.session==session and t.label==label]
            mean=density[idx].mean(axis=(0,1))
            for fi in np.flatnonzero(mask):
                for ti,t in enumerate(times):
                    rows.append({'session':session,'label':str(label),'n_trials':len(idx),
                                 'time_after_stored_target_marker_s':float(t),'frequency_hz':float(freq[fi]),
                                 'ROI_PSD_V2_per_Hz':float(mean[fi,ti])})
    out=args.output/'event_relative_psd.tsv'
    with out.open('w',newline='') as f:
        w=csv.DictWriter(f,list(rows[0]),delimiter='\t')
        w.writeheader()
        w.writerows(rows)
    (args.output/'receipt.json').write_text(json.dumps({
        'status':'event_relative_spectra_not_ERD_ERS','ROI':['C3','Cz','C4'],'reference':'CAR74',
        'window_seconds':1,'step_seconds':0.5,'time_anchor':'stored task marker; no separate verified feedback onset',
        'prestimulus_baseline':'unresolved','units':'V^2/Hz','script_sha256':file_sha256(Path(__file__)),
        'output_sha256':file_sha256(out),'bundle_sha256':file_sha256(ROOT/'data/netbci2026/derived_v1.0.0/sub-1/epochs.npz')},indent=2)+'\n')


if __name__=='__main__':
    main()
