"""Rebuild the existing submission containers without changing scientific data."""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import fitz
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "manuscript/plos_one_innovation_20261017"
LOG = Path(__file__).resolve().parent
BASE = "3a806d210cc8c4f25f5d24f9dca61059588616f5"
EXCLUSIONS = {
    "PACKAGE_MANIFEST.json",
    "PACKAGE_ZIP_CHECKSUM.json",
    "Paper2_PLOS_ONE_Innovation_20261017.zip",
    "PLOS_ONE_Submission_Files_20261017.zip",
    "PLOS_ONE_Submission_Files_20261017_CHECKSUM.json",
}


def identity(path: Path) -> dict:
    content = path.read_bytes()
    return {"path": path.relative_to(PACKAGE).as_posix(), "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest()}


def save_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def main() -> None:
    assert identity(PACKAGE / "S1_Data.zip")["sha256"] == (
        "c6b73502b977b7bd36e27c914bebd686d994596b99f06227131272f428aa3614"
    ), "The scientific data archive must remain byte-identical."
    now = datetime.now(timezone.utc).isoformat()
    mapping = json.loads((PACKAGE / "PLOS_ONE_Submission_Files_20261017_CHECKSUM.json").read_text())["member_source_mapping"]
    upload = PACKAGE / "PLOS_ONE_Submission_Files_20261017.zip"
    with zipfile.ZipFile(upload, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for member, source in mapping.items():
            archive.write(PACKAGE / source, member)
    upload_members = []
    with zipfile.ZipFile(upload) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist()) == len(set(archive.namelist())) == 13
        for member, source in mapping.items():
            content = archive.read(member)
            assert content == (PACKAGE / source).read_bytes()
            upload_members.append({"path": member, "bytes": len(content),
                                   "sha256": hashlib.sha256(content).hexdigest()})
    save_json(PACKAGE / "PLOS_ONE_Submission_Files_20261017_CHECKSUM.json", {
        "file": upload.name, **{k: v for k, v in identity(upload).items() if k != "path"},
        "updated_utc": now, "revision_baseline": BASE, "members": len(mapping),
        "crc_passed": True, "all_uncompressed_member_bytes_verified": True,
        "member_source_mapping": mapping, "members_sha256": upload_members,
        "archive_is_for_download_and_extraction": True,
        "upload_individual_files_to_journal": True,
        "ethics_statement": "Regulatory exemption under Article32(1); no institutional-confirmation claim.",
        "submission_system_ethics_text": "Ethics_Statement_20261019.md",
    })
    documents = []
    names = ["PLOS_ONE_Manuscript_Submission", "PLOS_ONE_Manuscript_Reading",
             "S1_Supplementary_Methods", "S2_Reproducibility", "Cover_Letter"]
    for name in names:
        pdf = PACKAGE / f"{name}.pdf"
        word = PACKAGE / f"{name}.docx"
        with fitz.open(pdf) as document:
            documents.append({"file": word.name, "pdf": pdf.name, "pages": len(document),
                              "docx_sha256": identity(word)["sha256"],
                              "pdf_sha256": identity(pdf)["sha256"],
                              "current_verification": ("Verification/Targeted_Check_20261019_run02/document_export_QA.json" if name.startswith("PLOS_ONE_Manuscript") else "Verification/Revision_20261019/document_export_QA.json")})
    figures = []
    for image in sorted((PACKAGE / "Figures").glob("*.tif")):
        with Image.open(image) as frame:
            figures.append({**identity(image), "pixels": list(frame.size), "mode": frame.mode,
                            "dpi": [float(value) for value in frame.info["dpi"]],
                            "compression": frame.info.get("compression")})
    files = [identity(p) for p in sorted(PACKAGE.rglob("*"))
             if p.is_file() and p.relative_to(PACKAGE).as_posix() not in EXCLUSIONS]
    manifest = {
        "schema_version": 2, "updated_utc": now, "base_commit": BASE,
        "revision_date": "2026-10-19", "submission_id": "PONE-D-26-52050",
        "title": "Spatial-filter refitting improves limited-label recalibration in longitudinal motor-imagery EEG",
        "revision_scope": "Targeted wording corrections after checking review claims; original interval signs, numerical results, ethics, references, figures and scientific data are unchanged.",
        "self_exclusions": sorted(EXCLUSIONS), "payload_files": len(files),
        "documents": documents, "figures": figures, "files": files,
        "scientific_data_archive_byte_identical_to_baseline": True,
        "current_verification_directory": "Verification/Targeted_Check_20261019_run02/",
        "historical_record_scope": "Each dated verification record certifies its recorded artifact hashes; this manifest identifies the current files. Unchanged supplements retain their applicable earlier receipts.",
        "journal_submission_performed_by_this_revision": False,
    }
    save_json(PACKAGE / "PACKAGE_MANIFEST.json", manifest)
    complete = PACKAGE / "Paper2_PLOS_ONE_Innovation_20261017.zip"
    with zipfile.ZipFile(complete, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for record in files:
            archive.write(PACKAGE / record["path"], record["path"])
        archive.write(PACKAGE / "PACKAGE_MANIFEST.json", "PACKAGE_MANIFEST.json")
    with zipfile.ZipFile(complete) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist()) == len(set(archive.namelist())) == len(files) + 1
        for record in files:
            assert archive.read(record["path"]) == (PACKAGE / record["path"]).read_bytes()
        assert archive.read("PACKAGE_MANIFEST.json") == (PACKAGE / "PACKAGE_MANIFEST.json").read_bytes()
    save_json(PACKAGE / "PACKAGE_ZIP_CHECKSUM.json", {
        "file": complete.name, **{k: v for k, v in identity(complete).items() if k != "path"},
        "updated_utc": now, "members": len(files) + 1, "crc_passed": True,
        "all_uncompressed_member_bytes_verified": True,
        "manifest_sha256": identity(PACKAGE / "PACKAGE_MANIFEST.json")["sha256"],
    })
    receipt = {"baseline_commit": BASE, "created_utc": now,
               "upload_archive": identity(upload), "upload_members": len(mapping),
               "complete_archive": identity(complete), "complete_members": len(files) + 1,
               "scientific_data_archive": identity(PACKAGE / "S1_Data.zip"),
               "all_members_match_current_files": True, "duplicate_members": 0,
               "crc_failures": 0, "hash_failures": 0,
               "fonts_or_raw_EEG_added": False, "journal_submission_performed": False}
    save_json(LOG / "archive_validation.json", receipt)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
