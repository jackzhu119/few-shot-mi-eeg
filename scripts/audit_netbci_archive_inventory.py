"""Bounded metadata-only inventory of pinned original archives; no signal members."""
import argparse
import csv
import hashlib
import json
import re
import zipfile
from pathlib import Path

from fetch_netbci_original_metadata import BoundedRanges

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    api = ROOT / 'research_logs/netbci2026_sources/original_dataverse/dataset_api.json'
    version = json.loads(api.read_text())['data']['latestVersion']
    assert (version['versionNumber'], version['versionMinorNumber']) == (2, 2)
    receipts = []
    for file_id in (744565, 744564):
        info = next(x['dataFile'] for x in version['files'] if x['dataFile']['id'] == file_id)
        url = f'https://entrepot.recherche.data.gouv.fr/api/access/datafile/{file_id}'
        stream = BoundedRanges(url, info['filesize'], budget=4_000_000)
        selected = []
        with zipfile.ZipFile(stream) as archive:
            entries = archive.infolist()
            with (args.output / f'{file_id}_inventory.tsv').open('w', newline='') as f:
                writer = csv.writer(f, delimiter='\t')
                writer.writerow(['member', 'bytes', 'compressed_bytes', 'encrypted', 'crc32'])
                writer.writerows((x.filename, x.file_size, x.compress_size, bool(x.flag_bits & 1),
                                  f'{x.CRC:08x}') for x in entries)
            for x in entries:
                # Inspect only small textual behavioral/global metadata. Never raw signals or MAT.
                relevant = (re.search(r'performance|feedback|score|behav|log|participants|scans|sessions|readme',
                                      x.filename, re.I) is not None)
                subject_ok = not re.search(r'sub-\d+', x.filename) or 'sub-01/' in x.filename
                if (relevant and subject_ok and x.file_size <= 100_000 and x.compress_size <= 100_000
                        and Path(x.filename).suffix.lower() in {'.tsv', '.csv', '.txt', '.json', '.md'}
                        and not x.flag_bits & 1):
                    data = archive.read(x)
                    target = args.output / 'text_metadata' / str(file_id) / x.filename
                    if '..' in Path(x.filename).parts or Path(x.filename).is_absolute():
                        raise ValueError('Unsafe archive member')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
                    selected.append({'member': x.filename, 'size': len(data),
                                     'sha256': hashlib.sha256(data).hexdigest(), 'crc_verified': True})
        receipts.append({'file_id': file_id, 'filename': info['filename'], 'url': url,
                         'archive_size': info['filesize'], 'whole_archive_checksum_verified': False,
                         'entries': len(entries), 'http_bytes_read': stream.bytes_received,
                         'range_requests': stream.requests, 'selected_text_members': selected,
                         'signal_members_read': 0})
    (args.output / 'receipt.json').write_text(json.dumps({'version': '2.2', 'archives': receipts}, indent=2)+'\n')
    print(json.dumps(receipts, indent=2))


if __name__ == '__main__':
    main()
