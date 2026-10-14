"""No-network checks for frozen transfer scope and preservation on failure."""
import hashlib
import importlib.util
import sys
import time
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('first_fit_https',ROOT/'scripts/fetch_kumar_first_fit_https.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_scope_matches_frozen_first_fit_only():
    plan=module.load_plan()
    edfs=[e for e in plan['files'] if e['path'].endswith('.edf')]
    assert len(edfs)==3
    assert all(e['path'].startswith('sub-1/ses-0/') for e in edfs)
    assert [e['path'].split('_run-')[1].split('_')[0] for e in edfs]==['0','1','2']


def entry():
    sha=hashlib.sha256(b'yes').hexdigest()
    return dict(path='a.edf',size=3,checksum_algorithm='sha256',checksum=sha,expected_sha256=sha)


def test_existing_mismatch_is_preserved(tmp_path):
    (tmp_path/'a.edf').write_bytes(b'bad')
    with pytest.raises(ValueError,match='mismatch'):
        module.fetch_one(tmp_path,entry(),time.monotonic()+60)
    assert (tmp_path/'a.edf').read_bytes()==b'bad'


def test_download_hash_failure_preserves_partial(tmp_path,monkeypatch):
    class Response:
        status_code=200
        headers={'Content-Length':'3'}
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def iter_content(self,**kwargs): yield b'bad'
    monkeypatch.setattr(module,'official_response',lambda *args:Response())
    with pytest.raises(ValueError,match='mismatch'):
        module.fetch_one(tmp_path,entry(),time.monotonic()+60)
    assert not (tmp_path/'a.edf').exists()
    assert (tmp_path/'a.edf.partial').read_bytes()==b'bad'
    with pytest.raises(FileExistsError,match='partial'):
        module.fetch_one(tmp_path,entry(),time.monotonic()+60)


def test_relay_packer_rejects_missing_or_wrong_checkpoint(tmp_path):
    import json
    import package_kumar_relay_smoke as packer
    source=tmp_path/'source'
    source.mkdir()
    common={'synthetic':True,'software_validation_only':True,'checkpoint_sha256':'0'*64}
    (source/'software_validation.json').write_text(json.dumps({**common,'checks':[common]}))
    (source/'synthetic_weights.json').write_text(json.dumps(common))
    (source/'synthetic_weights.pt').write_bytes(b'test-only-not-model')
    with pytest.raises(ValueError,match='hash mismatch'):
        packer.package(source,tmp_path/'output.tar')
    assert not (tmp_path/'output.tar').exists()
