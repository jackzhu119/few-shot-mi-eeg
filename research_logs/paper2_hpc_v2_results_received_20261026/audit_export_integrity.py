"""Check the downloaded packet bytes and every original archived member; no execution."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('download_directory', type=Path)
args = parser.parse_args()
root = args.download_directory.resolve()
receipt = json.loads((root / 'github_full_get_receipt_20261026T020424582390Z.json').read_text())
index = json.loads((root / 'packet_manifest.json').read_text())
assert receipt['failed_objects'] == [] and receipt['object_count'] == 3
for row in receipt['objects']:
    body = (root / Path(row['path']).name).read_bytes()
    assert len(body) == row['bytes']
    assert hashlib.sha256(body).hexdigest() == row['sha256']
    assert hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body).hexdigest() == row['git_blob_sha1']
assert len(index['parts']) == 1
archive = root / index['parts'][0]['file']
assert archive.stat().st_size == index['archive_bytes']
assert hashlib.sha256(archive.read_bytes()).hexdigest() == index['archive_sha256']
with tarfile.open(archive, 'r:gz') as stream:
    members = stream.getmembers()
    names = [m.name for m in members]
    assert len(names) == len(set(names))
    manifest = json.load(stream.extractfile('paper2_results/MANIFEST.json'))
    expected = {'paper2_results/' + r['path']: r for r in manifest['files']}
    assert set(names) == set(expected) | {'paper2_results/MANIFEST.json'}
    for member in members:
        assert member.isfile() and not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
        body = stream.extractfile(member).read()
        if member.name in expected:
            row = expected[member.name]
            assert len(body) == row['bytes'] and hashlib.sha256(body).hexdigest() == row['sha256'], member.name
    assert len(manifest['files']) == index['payload_files'] == 8983
print(json.dumps({'verified_git_objects':3,'payload_files':8983,'failed_checks':[]}))
