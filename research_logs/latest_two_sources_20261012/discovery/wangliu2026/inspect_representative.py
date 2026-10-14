"""Inspect official SET/FDT members with member CRC; do not run author code."""
import collections
import hashlib
import json
import sys
import zipfile
import zlib
from pathlib import Path

import mne
import numpy as np
import scipy.io

from audit_source import ROOT, RemoteZip, digest, save_json

source = json.loads((ROOT / "figshare_fixed_v11.json").read_bytes())
f = next(f for f in source["files"] if f["name"] == "sourcedata.zip")
remote = RemoteZip(f["download_url"], f["size"])
name = "sub-01/pre/sub-01_B_pre_01_original.set"
receipts = []
try:
    with zipfile.ZipFile(remote) as z:
        for member in (name, name.replace(".set", ".fdt")):
            info = z.getinfo(member)
            p = ROOT / "representative" / member
            if p.exists() and p.stat().st_size == info.file_size:
                b = p.read_bytes()
                assert zlib.crc32(b) == info.CRC
            else:
                b = z.read(member)  # zipfile validates member CRC on complete read
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b)
            receipts.append({"member": member, "path": str(p.relative_to(ROOT)), "bytes": len(b), "central_directory_crc32": f"{info.CRC:08x}", "member_crc32_verified": True, "whole_archive_md5_verified": False, **digest(b)})
    mat = scipy.io.loadmat(ROOT / "representative" / name, simplify_cells=True, uint16_codec="latin1")
    eeg = mat["EEG"] if "EEG" in mat else mat
    events = eeg.get("event", [])
    if isinstance(events, dict): events = [events]
    channels = eeg.get("chanlocs", [])
    if isinstance(channels, dict): channels = [channels]
    report = {"member": name, "mat_variables": list(mat), "eeg_keys": list(eeg), "nbchan": int(eeg["nbchan"]), "srate": float(eeg["srate"]), "pnts": int(eeg["pnts"]), "trials": int(eeg["trials"]), "xmin": float(eeg["xmin"]), "xmax": float(eeg["xmax"]), "data_reference": str(eeg["data"]), "reference_field": str(eeg.get("ref")), "channel_names": [str(x.get("labels")) for x in channels], "events": [{k: (v.item() if isinstance(v,np.generic) else v) for k,v in x.items() if k in ("type", "latency", "duration", "urevent")} for x in events], "event_type_counts": dict(collections.Counter(str(x.get("type")) for x in events))}
    report["mat_uint16_codec"] = "latin1"
    report["default_mat_reader_issue"] = "scipy default loadmat failed with buffer is too small for requested array; latin1 reads all variables"
    raw = mne.io.read_raw_eeglab(ROOT / "representative" / name, preload=False, uint16_codec="latin1", verbose="ERROR")
    chunk = raw.get_data(start=0, stop=min(1000,raw.n_times))
    report.update({"mne_version": mne.__version__, "mne_read": {"sfreq": raw.info["sfreq"], "channels": len(raw.ch_names), "n_times": int(raw.n_times), "channel_types": dict(collections.Counter(raw.get_channel_types())), "loaded_first_samples": int(chunk.shape[1]), "finite_all_first_samples": bool(np.isfinite(chunk).all()), "sample_min_volts": float(chunk.min()), "sample_max_volts": float(chunk.max()), "annotation_count": len(raw.annotations), "annotation_counts": dict(collections.Counter(raw.annotations.description)), "first_annotations": [{"onset_seconds":float(a["onset"]),"duration_seconds":float(a["duration"]),"description":str(a["description"])} for a in list(raw.annotations)[:6]]}})
    save_json("representative_audit.json", report)
    print(json.dumps({k:v for k,v in report.items() if k not in ("events","channel_names","eeg_keys")}))
finally:
    save_json("representative_member_receipts.json", receipts)
    previous = json.loads((ROOT / "representative_range_receipts.json").read_bytes()) if (ROOT / "representative_range_receipts.json").exists() else []
    save_json("representative_range_receipts.json", previous + remote.receipts)

# Independent directory coverage checks do not imply signal identity independence.
entries = json.loads((ROOT / "source_zip_entries.json").read_bytes())
counts, phase_ids, subjects = collections.Counter(), collections.defaultdict(set), {}
for e in entries:
    if not e["name"].endswith(".set"): continue
    subject, phase, filename = e["name"].split("/")
    group = filename.split("_")[1]
    counts[phase] += 1
    phase_ids[phase].add(subject)
    subjects.setdefault(subject, {"group_code":group,"phases":{}})["phases"].setdefault(phase,[]).append(filename)
follow_missing = sorted(phase_ids["pre"] - phase_ids["follow"])
coverage = {"subjects": subjects, "subject_count": len(subjects), "group_subject_counts": dict(collections.Counter(x["group_code"] for x in subjects.values())), "set_count_by_phase": dict(counts), "subject_count_by_phase": {k:len(v) for k,v in phase_ids.items()}, "missing_followup_ids": follow_missing, "all_present_subject_phases_have_four_runs": all(len(r)==4 for s in subjects.values() for r in s["phases"].values()), "every_set_has_matching_fdt": all(e["name"].replace(".set",".fdt") in {i["name"] for i in entries} for e in entries if e["name"].endswith(".set"))}
save_json("source_coverage_audit.json", coverage)
