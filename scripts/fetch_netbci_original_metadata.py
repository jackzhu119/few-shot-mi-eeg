"""Fetch only sub-01 metadata from the public Dataverse v2.2 ZIP via ranges.

No signal members are accepted. HTTP 206, file size, and cumulative byte limits
are checked before reading; a server ignoring Range is never read in full.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_URL = "https://entrepot.recherche.data.gouv.fr/api/access/datafile/744565"


class BoundedRanges(io.RawIOBase):
    def __init__(self, url: str, size: int, *, budget: int = 8_000_000):
        self.url = url
        self.size = size
        self.budget = budget
        self.position = 0
        self.bytes_received = 0
        self.requests = 0
        self.cache: dict[tuple[int, int], bytes] = {}
        self.resolved_url = None
        self.resolved_at = 0.0

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=io.SEEK_SET):
        base = {io.SEEK_SET: 0, io.SEEK_CUR: self.position, io.SEEK_END: self.size}[whence]
        self.position = base + offset
        if self.position < 0:
            raise ValueError("Negative archive position")
        return self.position

    def read(self, length=-1):
        if length < 0:
            length = self.size - self.position
        length = min(length, self.size - self.position)
        if length <= 0:
            return b""
        start = self.position
        stop = start + length
        for (left, right), data in self.cache.items():
            if left <= start and stop <= right:
                self.position = stop
                return data[start - left : stop - left]
        # A small prefetch covers a metadata member's local header and payload.
        fetch_stop = min(self.size, start + max(length, 8192))
        expected = fetch_stop - start
        if expected + self.bytes_received > self.budget:
            raise ValueError("Archive metadata HTTP budget exceeded")
        request_url = self.resolved_url if time.monotonic() - self.resolved_at < 3600 else None
        request = urllib.request.Request(request_url or self.url,
                                         headers={"Range": f"bytes={start}-{fetch_stop - 1}"})
        with urllib.request.urlopen(request, timeout=45) as response:
            expected_range = f"bytes {start}-{fetch_stop - 1}/{self.size}"
            if response.status != 206 or response.headers.get("Content-Range") != expected_range:
                raise OSError("Server did not honor the exact HTTP range; full body was not read")
            data = response.read(expected + 1)
            if len(data) != expected:
                raise OSError("Incomplete or oversized HTTP range")
            # Keep the redirect only in memory; never save signed query strings.
            self.resolved_url = response.geturl()
            self.resolved_at = time.monotonic()
        self.requests += 1
        self.bytes_received += len(data)
        self.cache[(start, fetch_stop)] = data
        self.position = stop
        return data[:length]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path,
                        default=REPO_ROOT / "data/netbci2026/original_v2.2_metadata")
    parser.add_argument("--receipt", type=Path,
                        default=REPO_ROOT / "research_logs/netbci2026_original_metadata_receipt.json")
    args = parser.parse_args()
    if args.receipt.exists():
        raise FileExistsError("Choose a new receipt path to preserve the previous verification")
    api_path = REPO_ROOT / "research_logs/netbci2026_sources/original_dataverse/dataset_api.json"
    version = json.loads(api_path.read_text())["data"]["latestVersion"]
    if (version["versionNumber"], version["versionMinorNumber"]) != (2, 2):
        raise ValueError("Expected pinned Dataverse v2.2 metadata")
    archive_info = next(item["dataFile"] for item in version["files"]
                        if item["dataFile"]["id"] == 744565)
    remote = BoundedRanges(ARCHIVE_URL, archive_info["filesize"])
    allowed = re.compile(
        r"(?:^|/)sub-01/ses-(\d+)/eeg/"
        r"sub-01_ses-\1_task-MotorImageryRest_run-(\d+)_(?:eeg\.(?:vhdr|vmrk|json)|"
        r"events\.tsv|channels\.tsv)$"
    )
    records = []
    with zipfile.ZipFile(remote) as archive:
        members = [item for item in archive.infolist() if allowed.search(item.filename)]
        if not members:
            raise ValueError("No expected sub-01 motor-imagery EEG metadata found")
        for item in members:
            match = allowed.search(item.filename)
            relative = item.filename[item.filename.index("sub-01/") :]
            if item.flag_bits & 1:
                raise ValueError("Encrypted member; no password attempt is permitted")
            if item.file_size > 100_000 or item.compress_size > 100_000:
                raise ValueError("Metadata member exceeds the per-file size limit")
            data = archive.read(item)  # zipfile verifies member CRC-32.
            path = args.output_root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists() and path.read_bytes() != data:
                raise FileExistsError(f"Existing metadata differs: {relative}")
            path.write_bytes(data)
            records.append({"member": item.filename, "local_path": str(path.resolve()),
                            "relative_path": relative, "session": match.group(1),
                            "run": match.group(2), "size": len(data),
                            "compressed_size": item.compress_size,
                            "crc32": f"{item.CRC:08x}", "crc_verified": True,
                            "sha256": hashlib.sha256(data).hexdigest()})
        directory_entries = len(archive.infolist())
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt = {"doi": "10.57745/RBJRC7", "version": "2.2", "subject": "sub-01",
               "source_url": ARCHIVE_URL, "archive_size": remote.size,
               "official_archive_checksum": archive_info["checksum"],
               "full_archive_checksum_verified": False, "crc_verification_scope": "selected members",
               "directory_entries": directory_entries, "range_requests": remote.requests,
               "http_bytes_read": remote.bytes_received,
               "selected_metadata_bytes": sum(item["size"] for item in records),
               "signal_files_downloaded": 0, "members": records}
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({key: value for key, value in receipt.items() if key != "members"}, indent=2))


if __name__ == "__main__":
    main()
