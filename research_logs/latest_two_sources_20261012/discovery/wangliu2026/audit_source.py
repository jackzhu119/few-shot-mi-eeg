"""Read-only fixed-version metadata and bounded HTTP Range source inspection.

Author code is never imported or executed. Receipts use canonical public URLs,
never temporary redirect URLs. Whole archive MD5 is explicitly unverified.
"""
from __future__ import annotations
import concurrent.futures
import datetime
import hashlib
import io
import json
from pathlib import Path
import requests
import time
import zipfile

ROOT = Path(__file__).resolve().parent
TIME = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()

def digest(b):
    return {"sha256": hashlib.sha256(b).hexdigest(), "md5": hashlib.md5(b).hexdigest()}

def save_json(name, x):
    (ROOT / name).write_text(json.dumps(x, indent=2, ensure_ascii=False) + "\n")

def get_small(url, name, size_cap=2_000_000):
    r = requests.get(url, timeout=60, stream=True)
    r.raise_for_status()
    b = bytearray()
    for part in r.iter_content(65536):
        b.extend(part)
        if len(b) > size_cap:
            raise ValueError("bounded GET exceeded size cap")
    p = ROOT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b)
    return {"canonical_url": url, "http_status": r.status_code, "bytes": len(b), "time_utc": TIME(), "path": str(p.relative_to(ROOT)), **digest(b)}

class RemoteZip(io.RawIOBase):
    def __init__(self, url, size):
        self.url, self.size, self.pos = url, size, 0
        self.receipts = []
    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos
    def seek(self, offset, whence=0):
        self.pos = offset if whence == 0 else (self.pos + offset if whence == 1 else self.size + offset)
        if not 0 <= self.pos <= self.size:
            raise ValueError("seek out of bounds")
        return self.pos
    def read(self, length=-1):
        length = min(length if length >= 0 else self.size - self.pos, self.size - self.pos)
        if not length: return b""
        if length > 32_000_000: raise ValueError("range exceeds 32MB audit cap")
        start, end = self.pos, self.pos + length - 1
        for attempt in range(3):
            r = requests.get(self.url, headers={"Range": f"bytes={start}-{end}", "Accept-Encoding": "identity"}, timeout=90, stream=True)
            if r.status_code not in (429, 500, 502, 503, 504):
                break
            self.receipts.append({"canonical_url": self.url, "time_utc": TIME(), "http_status": r.status_code, "start": start, "end_inclusive": end, "attempt": attempt + 1, "response_read": False})
            r.close()
            time.sleep(1)
        if r.status_code != 206:
            r.close()
            raise ValueError(f"Range status {r.status_code}; refusing whole-archive response")
        cr = r.headers.get("Content-Range")
        if cr != f"bytes {start}-{end}/{self.size}":
            r.close()
            raise ValueError(f"Unexpected Content-Range {cr!r}")
        b = bytearray()
        for part in r.iter_content(65536):
            b.extend(part)
            if len(b) > length:
                r.close(); raise ValueError("Range response too long")
        if len(b) != length: raise ValueError("Range response too short")
        self.pos += length
        self.receipts.append({"canonical_url": self.url, "time_utc": TIME(), "http_status": r.status_code, "start": start, "end_inclusive": end, "content_range": cr, "bytes": len(b), **digest(b)})
        return bytes(b)

def main():
    fixed = "https://api.figshare.com/v2/articles/30509165/versions/11"
    receipt = get_small(fixed, "figshare_fixed_v11.json")
    data = json.loads((ROOT / "figshare_fixed_v11.json").read_bytes())
    save_json("figshare_fixed_v11_receipt.json", receipt)
    files = [f for f in data["files"] if f["size"] < 1_000_000]
    def dl(f):
        x = get_small(f["download_url"], "metadata/" + f["name"])
        x.update({"figshare_file_id": f["id"], "official_size": f["size"], "official_md5": f["computed_md5"], "official_md5_verified": x["md5"] == f["computed_md5"], "official_size_verified": x["bytes"] == f["size"]})
        return x
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        receipts = list(ex.map(dl, files))
    save_json("small_file_receipts.json", receipts)
    assert all(x["official_md5_verified"] and x["official_size_verified"] for x in receipts)
    source = next(f for f in data["files"] if f["name"] == "sourcedata.zip")
    remote = RemoteZip(source["download_url"], source["size"])
    try:
        z = zipfile.ZipFile(remote)
        entries = [{"name": i.filename, "compressed_bytes": i.compress_size, "uncompressed_bytes": i.file_size, "crc32": f"{i.CRC:08x}", "compression": i.compress_type, "header_offset": i.header_offset, "is_directory": i.is_dir(), "flag_bits": i.flag_bits} for i in z.infolist()]
        save_json("source_zip_entries.json", entries)
        save_json("source_zip_summary.json", {"archive": source, "whole_archive_downloaded": False, "whole_archive_official_md5_verified": False, "entries": len(entries), "files": sum(not i["is_directory"] for i in entries), "compressed_member_bytes": sum(i["compressed_bytes"] for i in entries), "uncompressed_member_bytes": sum(i["uncompressed_bytes"] for i in entries), "zip64_parser": "Python zipfile (ZIP64 enabled)", "range_transfer_bytes": sum(x.get("bytes", 0) for x in remote.receipts)})
        print(json.dumps({"small_files": len(receipts), "small_bytes": sum(x["bytes"] for x in receipts), "entries": len(entries), "uncompressed_bytes": sum(i["uncompressed_bytes"] for i in entries), "extensions": sorted(set(Path(i["name"]).suffix for i in entries if not i["is_directory"]))}))
    finally:
        save_json("source_zip_range_receipts.json", remote.receipts)

if __name__ == "__main__": main()
