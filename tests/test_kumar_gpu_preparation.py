"""Data scope and atomic full-hash restore guards, without network."""
import hashlib
import importlib.util
import io
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('restore_kumar', ROOT / 'scripts/restore_kumar_r2.py')
restore = importlib.util.module_from_spec(spec)
spec.loader.exec_module(restore)


def test_development_scope_has_only_42_frozen_edfs():
    entries = restore.select('development-csp')
    edfs = [e['relative_path'] for e in entries if e['relative_path'].endswith('.edf')]
    assert len(edfs) == 42
    assert all('/ses-0/' in p and ('_run-0_' in p or '_run-1_' in p)
               or '/ses-0/' not in p and '_run-0_' in p for p in edfs)
    assert sum(e['bytes'] for e in entries) == 211043998


def test_hash_conflict_never_promotes_download(tmp_path):
    class Body(io.BytesIO):
        def iter_chunks(self, chunk_size):
            yield self.read()

    class Client:
        def get_object(self, **kwargs):
            return {'Body': Body(b'bad')}

    entry = dict(relative_path='x.edf', key='fixed/x', bytes=3,
                 sha256=hashlib.sha256(b'yes').hexdigest())
    with pytest.raises(ValueError, match='hash mismatch'):
        restore.restore(Client(), 'test', [entry], tmp_path)
    assert not (tmp_path / 'x.edf').exists()
    assert (tmp_path / 'x.edf.partial').exists()
