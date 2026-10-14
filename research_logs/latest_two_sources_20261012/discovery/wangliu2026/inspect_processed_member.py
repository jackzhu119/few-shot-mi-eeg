"""Read one published derivative to assess raw/processed metadata differences."""
import collections
import json
import zipfile
import zlib

import numpy as np
import scipy.io
import h5py

from audit_source import ROOT, RemoteZip, digest, save_json

metadata = json.loads((ROOT / "figshare_fixed_v11.json").read_bytes())
f = next(x for x in metadata["files"] if x["name"] == "processeddata.zip")
remote = RemoteZip(f["download_url"], f["size"])
name = "sub-01/pre/sub-01_B_pre_01_eeg.mat"
try:
    with zipfile.ZipFile(remote) as z:
        info = z.getinfo(name)
        p = ROOT / "representative_processed" / name
        if p.exists() and p.stat().st_size == info.file_size:
            b = p.read_bytes()
            assert zlib.crc32(b) == info.CRC
        else:
            b = z.read(name)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b)
    save_json("processed_member_receipt.json", {"member":name,"path":str(p.relative_to(ROOT)),"bytes":len(b),"crc32":f"{info.CRC:08x}","member_crc32_verified":True,"whole_archive_md5_verified":False,**digest(b)})
    with h5py.File(p) as h:
        eeg = h["EEG"]
        def val(d):
            a = d[...]
            if d.attrs.get("MATLAB_class") == b"char":
                return "".join(chr(int(x)) for x in a.ravel())
            if a.size == 1: return a.ravel()[0].item()
            return a.tolist()
        def values(d):
            return [val(h[r]) for r in d[...].ravel()]
        types = values(eeg["event/type"])
        latencies = values(eeg["event/latency"])
        durations = values(eeg["event/duration"])
        dat = eeg["data"][...]
        report = {"member":name,"format":"MATLAB v7.3 HDF5","reader":"h5py", "h5py_version":h5py.__version__,"mat_keys":list(h),"eeg_keys":list(eeg),"nbchan":int(val(eeg["nbchan"])),"srate":float(val(eeg["srate"])),"pnts":int(val(eeg["pnts"])),"trials":int(val(eeg["trials"])),"xmin":float(val(eeg["xmin"])),"xmax":float(val(eeg["xmax"])),"ref":val(eeg["ref"]),"channel_names":values(eeg["chanlocs/labels"]),"data_shape_hdf5":list(dat.shape),"data_dtype":str(dat.dtype),"data_finite_all":bool(np.isfinite(dat).all()),"event_type_counts":dict(collections.Counter(str(x) for x in types)),"first_events":[{"type":t,"latency":l,"duration":d} for t,l,d in list(zip(types,latencies,durations))[:6]],"author_history":val(eeg["history"]),"author_code_executed":False}
    save_json("processed_member_audit.json",report)
    print(json.dumps({k:v for k,v in report.items() if k not in ("author_history","eeg_keys","channel_names")}))
finally:
    previous = json.loads((ROOT / "processed_member_range_receipts.json").read_bytes()) if (ROOT / "processed_member_range_receipts.json").exists() else []
    save_json("processed_member_range_receipts.json",previous+remote.receipts)
