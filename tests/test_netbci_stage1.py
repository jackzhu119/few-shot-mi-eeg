"""Run-level uncertainty, equal-count sampling and bounded-download regression."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from fetch_netbci_original_metadata import BoundedRanges
from run_netbci_stage1 import balanced_indices, run_ci


def test_conditional_interval_resamples_whole_runs():
    y=np.array(['rest','right_hand']*5)
    prediction=y.copy()
    prediction[6:]=np.where(y[6:]=='rest','right_hand','rest')
    groups=np.array(['good']*6+['bad']*4)
    ci=run_ci(y,prediction,groups,repetitions=200,seed=10)
    assert ci==[0.0,1.0]
    assert run_ci(y,y,np.array(['only']*10)) is None


def test_equal_class_run_matching_does_not_silently_drop_a_run():
    trials=[{'session':s,'run':r,'label':label}
            for s in ['01','02'] for r in ['01','02']
            for label in ['rest','right_hand'] for _ in range(4)]
    selected=balanced_indices(trials,['01','02'],['rest','right_hand'],3,42)
    assert all(len(x)==12 and len(set(x))==12 for x in selected.values())
    repeated=balanced_indices(trials,['01','02'],['rest','right_hand'],3,42)
    assert all(np.array_equal(selected[s],repeated[s]) for s in selected)
    eligible=np.ones(len(trials),dtype=bool)
    eligible[:2]=False
    with pytest.raises(ValueError,match='Insufficient'):
        balanced_indices(trials,['01','02'],['rest','right_hand'],3,42,eligible)


def test_server_ignoring_range_never_reads_full_body(monkeypatch):
    class Response:
        status=200
        headers={}
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,*args):raise AssertionError('Forbidden full body read')
    monkeypatch.setattr('urllib.request.urlopen',lambda *a,**k:Response())
    with pytest.raises(OSError,match='full body was not read'):
        BoundedRanges('https://example.test/archive',10_000).read(1)


def test_range_budget_checked_before_network(monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('Network must not be called')
    monkeypatch.setattr('urllib.request.urlopen',forbidden)
    with pytest.raises(ValueError,match='budget exceeded'):
        BoundedRanges('https://example.test/archive',10_000,budget=100).read(1)
