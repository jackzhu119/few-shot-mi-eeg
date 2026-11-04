"""Export the approved saved Paper2 data as standalone CSV/XLSX files.

This is a format conversion. It neither loads EEG/models nor recomputes metrics.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from dataclasses import dataclass
import datetime as dt
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import zipfile

import openpyxl
import xlsxwriter

ROOT = Path(__file__).resolve().parents[1]
PIN = "407e6ce0a17339d5808a7acc14e9745b9dceffbd"
ARCHIVE_PATH = "manuscript/jne_alignment_20261104/Supplementary_Data_and_Code.zip"
ARCHIVE_SHA = "e06c756aa183fc32714d938a2cdd21ca065e5b9d43abf5642e7a4bf1839788ad"
JNE = "manuscript/jne_alignment_20261104/"
ANALYSIS = "research_logs/paper2_alignment_integrated_20261104/analysis/"
MECHANISMS = "research_logs/paper2_alignment_integrated_20261104/mechanisms/"
ORIGINAL_INPUT = "research_logs/paper2_structure_revision_20261029/component_replay/input/"
BNCI = "research_logs/paper2_external_validation_20261027/saved_predictions/"
RAW = f"https://raw.githubusercontent.com/jackzhu119/few-shot-mi-eeg/{PIN}/"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical_json(value):
    # JSON floating point numbers retain their parsed IEEE values; strings and
    # CSV decimal text are never coerced. Original byte hashes remain in INDEX.
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=True)


def csv_rows(data):
    rows = list(csv.reader(io.StringIO(data.decode("utf-8-sig"), newline="")))
    if not rows or not rows[0]:
        raise ValueError("Empty source CSV")
    width = len(rows[0])
    if any(len(row) != width for row in rows[1:]):
        raise ValueError("Ragged source CSV")
    return rows[0], rows[1:]


@dataclass
class Table:
    table_id: str
    title: str
    source_path: str
    source_sha256: str
    kind: str
    headers: list[str]
    rows: list[list[str]]
    block_sha256: str | None = None

    @property
    def sheet(self):
        name = self.table_id + "_" + re.sub(r"[^A-Za-z0-9_]", "_", self.title)
        return name[:31]

    def manifest(self):
        return {"table_id": self.table_id, "sheet": self.sheet, "title": self.title,
                "source_path": self.source_path, "source_sha256": self.source_sha256,
                "source_url": RAW + self.source_path, "kind": self.kind,
                "headers": self.headers, "data_rows": len(self.rows),
                "columns": len(self.headers), "table_block_sha256": self.block_sha256}


def manuscript_tables(archive, path, prefix, expected):
    data = archive.read(path)
    text = data.decode("utf-8")
    found = list(re.finditer(r"(?m)^\|[^\n]*(?:\n\|[^\n]*)*", text))
    if len(found) != expected:
        raise ValueError("Unexpected number of manuscript tables: " + path)
    tables = []
    for number, match in enumerate(found, 1):
        rows = [[cell.strip() for cell in line.strip().strip("|").split("|")]
                for line in match[0].splitlines()]
        if len(rows) < 2 or not all(re.fullmatch(r":?-{2,}:?", x) for x in rows[1]):
            raise ValueError("Unrecognized Markdown table delimiter")
        headers, values = rows[0], rows[2:]
        if any(len(row) != len(headers) for row in values):
            raise ValueError("Ragged manuscript table")
        table_id = f"{prefix}{number:02d}"
        title = ("Main_Table_" if prefix == "M" else "Supplement_Table_") + str(number)
        tables.append(Table(table_id, title, path, digest(data), "manuscript_table",
                            headers, values, digest(match[0].encode("utf-8"))))
    return tables


def collect_tables(archive):
    tables = manuscript_tables(archive, JNE + "MAIN.md", "M", 2)
    tables += manuscript_tables(archive, JNE + "SUPPLEMENT.md", "S", 27)
    names = archive.namelist()
    groups = [("A", sorted(n for n in names if n.startswith(ANALYSIS) and n.endswith(".csv") and "/" not in n[len(ANALYSIS):])),
              ("C", sorted(n for n in names if n.startswith(MECHANISMS) and n.endswith(".csv") and "/" not in n[len(MECHANISMS):])),
              ("F", sorted(n for n in names if n.startswith(JNE + "figures/") and n.endswith(".csv"))
               + sorted(n for n in names if n.startswith(JNE + "supplementary_figures/") and n.endswith(".csv")))]
    if [len(paths) for _, paths in groups] != [12, 5, 10]:
        raise ValueError("Fixed result/figure source count changed")
    for prefix, paths in groups:
        for number, path in enumerate(paths, 1):
            data = archive.read(path)
            header, values = csv_rows(data)
            tables.append(Table(f"{prefix}{number:02d}", Path(path).stem, path,
                                digest(data), "figure_csv" if prefix == "F" else "statistical_csv",
                                header, values))
    if len(tables) != 56 or len({t.sheet for t in tables}) != 56:
        raise ValueError("Table/sheet identity mismatch")
    return tables


def export_result_csv(tables, output):
    path = output / "Supplementary_Results.csv"
    cells = 0
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["table_id", "row", "column", "field", "value"])
        for table in tables:
            for row_index, row in enumerate(table.rows, 1):
                for column, value in enumerate(row, 1):
                    writer.writerow([table.table_id, row_index, column, table.headers[column - 1], value])
                    cells += 1
    # Independent parser reconstructs every coordinate, including empty fields.
    expected = {(t.table_id, r, c): (t.headers[c - 1], value)
                for t in tables for r, row in enumerate(t.rows, 1)
                for c, value in enumerate(row, 1)}
    with path.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            key = (row["table_id"], int(row["row"]), int(row["column"]))
            if expected.pop(key, None) != (row["field"], row["value"]):
                raise ValueError("Result CSV field differs from its source")
    if expected:
        raise ValueError("Result CSV has missing fields")
    return cells


def export_workbook(tables, output):
    path = output / "Supplementary_Results.xlsx"
    workbook = xlsxwriter.Workbook(path, {"constant_memory": True, "strings_to_formulas": False,
                                          "strings_to_urls": False, "strings_to_numbers": False})
    workbook.set_properties({"title": "Results and figure data", "author": "Ziyuan Zhu; Sihao Liu; Haoyang Yu",
                             "comments": "Saved-data format conversion; no new analysis or fitting."})
    header = workbook.add_format({"bold": True, "bg_color": "#E6EDF3", "border": 1, "text_wrap": True})
    text = workbook.add_format({"num_format": "@", "valign": "top"})
    note = workbook.add_format({"text_wrap": True, "valign": "top"})
    readme = workbook.add_worksheet("README")
    description = "Article tables, participant and session summaries, figure data, and source identifiers copied from fixed saved results."
    notes = [
        ["Short title", "Results and figure data"], ["Description", description],
        ["Fixed source commit", PIN],
        ["Content", "2 main tables; 27 supplementary tables; 17 statistical CSVs; 10 figure-source CSVs."],
        ["Precision", "Every source field is stored as text. No decimal rounding, formula execution or automatic numeric conversion."],
        ["Using numeric fields", "Convert selected text fields explicitly for computation; the original full-precision CSVs remain linked in INDEX."],
        ["Empty/missing values", "Empty fields, NA/status text and undefined entries retain their source representation."],
        ["Statistical unit", "Participants remain the independent units. Sessions, seeds and repeated predictions are nested observations."],
        ["Manuscript tables", "Display-precision cells retain their Markdown text markers; full-precision statistical rows are separate sheets."],
        ["Saved predictions", "The separate Budget/Phase prediction CSVs and Saved_Records CSV preserve the selected CSP/LDA saved outputs."],
        ["Scope", "This workbook does not embed all EEGNet/synthetic raw outputs or all original files. Fixed code and provenance remain in GitHub."],
        ["Original archive", f"{ARCHIVE_PATH}; SHA256 {ARCHIVE_SHA}"],
        ["No new execution", "No EEG, weights, model fitting, query forward or new statistical calculation was used."],
        ["Terms", "Project derived data follow LICENSING.md; original EEG and third-party materials retain their terms."],
    ]
    readme.set_column(0, 0, 24)
    readme.set_column(1, 1, 120)
    for row_index, row in enumerate(notes):
        for col, value in enumerate(row):
            readme.write_string(row_index, col, value, header if col == 0 else note)
        readme.set_row(row_index, 44)
    index = workbook.add_worksheet("INDEX")
    index_headers = ["table_id", "sheet", "title", "kind", "source_path", "source_sha256", "rows", "columns", "original_source_url"]
    index.write_row(0, 0, index_headers, header)
    for row_index, table in enumerate(tables, 1):
        values = [table.table_id, table.sheet, table.title, table.kind, table.source_path,
                  table.source_sha256, str(len(table.rows)), str(len(table.headers)), RAW + table.source_path]
        for col, value in enumerate(values):
            index.write_string(row_index, col, value, text)
    index.freeze_panes(1, 0)
    index.autofilter(0, 0, len(tables), len(index_headers) - 1)
    index.set_column(0, 3, 25)
    index.set_column(4, 5, 50)
    index.set_column(6, 7, 12)
    index.set_column(8, 8, 70)
    for table in tables:
        sheet = workbook.add_worksheet(table.sheet)
        sheet.freeze_panes(1, 0)
        for col, value in enumerate(table.headers):
            if len(value) > 32767 or sheet.write_string(0, col, value, header):
                raise ValueError("Workbook header exceeds supported string bounds")
        for row_index, row in enumerate(table.rows, 1):
            for col, value in enumerate(row):
                if len(value) > 32767 or sheet.write_string(row_index, col, value, text):
                    raise ValueError("Workbook string would truncate")
        for col, label in enumerate(table.headers):
            preview = [len(row[col]) for row in table.rows[:200]]
            width = min(48, max(12, len(label) + 2, max(preview, default=0) + 2))
            sheet.set_column(col, col, width)
        if table.rows:
            sheet.autofilter(0, 0, len(table.rows), len(table.headers) - 1)
    workbook.close()
    loaded = openpyxl.load_workbook(path, read_only=True, data_only=False)
    if len(loaded.sheetnames) != 58:
        raise ValueError("Workbook sheet count differs")
    checked = 0
    for table in tables:
        actual = list(loaded[table.sheet].iter_rows(values_only=True))
        expected = [table.headers] + table.rows
        if len(actual) != len(expected):
            raise ValueError("Workbook row count differs")
        for before, after in zip(expected, actual):
            if tuple(before) != tuple("" if x is None else x for x in after):
                raise ValueError("Workbook source text changed: " + table.table_id)
            checked += len(before)
    loaded.close()
    return checked


def export_predictions_and_records(archive, output):
    sources, expected_records = [], []
    copied = []
    for kind, expected_rows in [("budget", 78600), ("phase", 11460)]:
        source = ORIGINAL_INPUT + kind + "/query_predictions.csv.gz"
        compressed = archive.read(source)
        data = gzip.decompress(compressed)
        header, rows = csv_rows(data)
        if len(rows) != expected_rows:
            raise ValueError("Prediction source count changed: " + kind)
        destination = output / ("Supplementary_" + kind.title() + "_Predictions.csv")
        destination.write_bytes(data)
        if destination.read_bytes() != data:
            raise ValueError("Decompressed prediction bytes differ")
        entry = {"source_id": kind + "_predictions", "path": source, "source_url": RAW + source,
                 "source_bytes": len(compressed), "source_sha256": digest(compressed),
                 "decompressed_bytes": len(data), "decompressed_sha256": digest(data),
                 "headers": header, "rows": len(rows), "output_file": destination.name}
        sources.append(entry)
        copied.append(entry)
    manifest = json.loads(archive.read(ANALYSIS + "INPUT_MANIFEST.json"))
    external = sorted(row["path"] for row in manifest if row["path"].startswith(BNCI) and row["path"].endswith(".json"))
    cells = sorted(n for n in archive.namelist() if n.startswith(MECHANISMS + "run01/cells/") and n.endswith(".json"))
    if len(external) != 36 or len(cells) != 576:
        raise ValueError("Fixed JSON record population differs")
    statuses, vector_counts = Counter(), Counter()
    for number, source in enumerate(external + cells, 1):
        data = archive.read(source)
        value = json.loads(data)
        if source.startswith(BNCI):
            count = len(value["y"])
            if count != 120 or len(value["prediction"]) != count or len(value["trial_ids"]) != count:
                raise ValueError("External prediction vector lengths differ")
            vector_counts["external"] += count
        else:
            statuses[value["status"]] += 1
            if value["status"] == "complete":
                count = len(value["label"])
                if len(value["prediction"]) != count or len(value["p_right"]) != count or len(value["context"]["query_ids"]) != count:
                    raise ValueError("Sensitivity prediction vector lengths differ")
                family = "new_phase" if value["context"]["dataset"] == "kumar_phase" else "matched"
                vector_counts[family] += count
        source_id = f"J{number:03d}"
        sources.append({"source_id": source_id, "path": source, "source_url": RAW + source,
                        "source_bytes": len(data), "source_sha256": digest(data),
                        "record_type": "json_document", "rows": 1,
                        "canonical_json_sha256": digest(canonical_json(value).encode("utf-8"))})
        expected_records.append([source_id, source, "json_document", "1", canonical_json(value)])
    for number, suffix in enumerate(["budget/session_metrics.csv.gz", "phase/metrics.csv.gz"], 1):
        source = ORIGINAL_INPUT + suffix
        compressed = archive.read(source)
        data = gzip.decompress(compressed)
        headers, rows = csv_rows(data)
        if len(headers) != len(set(headers)) or len(rows) != (1800 if number == 1 else 540):
            raise ValueError("Metric CSV identity/shape changed")
        source_id = f"T{number:02d}"
        sources.append({"source_id": source_id, "path": source, "source_url": RAW + source,
                        "source_bytes": len(compressed), "source_sha256": digest(compressed),
                        "decompressed_bytes": len(data), "decompressed_sha256": digest(data),
                        "record_type": "csv_metric_row", "rows": len(rows), "headers": headers})
        for row_index, row in enumerate(rows, 1):
            expected_records.append([source_id, source, "csv_metric_row", str(row_index),
                                     canonical_json(dict(zip(headers, row)))])
    if statuses != {"complete": 544, "undefined_query_missing_class": 32}:
        raise ValueError("Undefined/complete cell population changed")
    if vector_counts != {"external": 4320, "matched": 20040, "new_phase": 3820}:
        raise ValueError("Contained prediction lengths changed")
    path = output / "Supplementary_Saved_Records.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["source_id", "source_path", "record_type", "source_row", "record_json"])
        writer.writerows(expected_records)
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.reader(stream)
        next(reader)
        actual = list(reader)
    if actual != expected_records or len(actual) != 2952:
        raise ValueError("Saved-record CSV roundtrip differs")
    for row in actual:
        if canonical_json(json.loads(row[4])) != row[4]:
            raise ValueError("Canonical JSON roundtrip differs")
    return {"sources": sources, "raw_prediction_CSVs": copied,
            "saved_record_CSV_rows": len(actual), "JSON_documents": len(external) + len(cells),
            "cell_status_counts": dict(statuses), "contained_JSON_prediction_values": dict(vector_counts),
            "total_selected_classical_prediction_values": 78600 + 11460 + sum(vector_counts.values()),
            "scope_note": "CSP/LDA predictions and sensitivity records. Not all EEGNet, geometric or synthetic raw outputs; no new predictions."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    if args.archive:
        raw_archive = args.archive.read_bytes()
    elif (ROOT / ARCHIVE_PATH).is_file():
        raw_archive = (ROOT / ARCHIVE_PATH).read_bytes()
    else:
        raw_archive = subprocess.check_output(["git", "show", PIN + ":" + ARCHIVE_PATH], cwd=ROOT)
    if digest(raw_archive) != ARCHIVE_SHA:
        raise ValueError("Fixed source archive SHA256 differs")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(raw_archive)) as archive:
        if len(archive.namelist()) != 1471:
            raise ValueError("Fixed archive member count differs")
        tables = collect_tables(archive)
        result_cells = export_result_csv(tables, output)
        workbook_cells = export_workbook(tables, output)
        records = export_predictions_and_records(archive, output)
    index = {"source_commit": PIN, "source_archive": {"path": ARCHIVE_PATH, "bytes": len(raw_archive), "sha256": ARCHIVE_SHA},
             "table_schema": "table_id,row,column,field,value; all source values remain text; row/column are 1-based data coordinates",
             "table_sources": [table.manifest() for table in tables], "saved_record_sources": records["sources"],
             "CSV_text_precision": "Original CSV field strings are preserved exactly, including empty fields and all decimal digits.",
             "Markdown_cells": "Leading/trailing table syntax spacing trimmed; cell text/Markdown markers retained; original table-block SHA256 supplied.",
             "JSON_scope": "Objects and nested values are canonicalized. Formatting bytes may change; original source bytes/SHA256 remain pinned.",
             "XLSX_scope": "Optional human-readable copy of the same 56 table sources; every field stored as text. No raw prediction rows embedded here."}
    (output / "INPUT_INDEX.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n")
    files = []
    for path in sorted(output.glob("Supplementary_*")):
        if path.is_file():
            if path.stat().st_size > 50_000_000:
                raise ValueError("Direct file exceeds 50 MB: " + path.name)
            files.append({"file": path.name, "bytes": path.stat().st_size, "sha256": digest(path.read_bytes())})
    receipt = {"status": "passed", "validated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
               "source_commit": PIN, "input_archive_sha256": ARCHIVE_SHA,
               "source_table_count": len(tables), "long_result_data_cells_roundtripped": result_cells,
               "workbook_cells_including_headers_roundtripped": workbook_cells, "workbook_sheets": 58,
               "numeric_or_formula_auto_conversion": False, "original_decimal_text_retained": True,
               "decimal_text_scope": "Original CSV/table field strings and XLSX text cells; JSON numbers retain parsed IEEE values and canonical JSON semantics.",
               "empty_fields_retained": True, "all_primary_files_below_50MB": True,
               "new_fit_count": 0, "new_query_forward_count": 0, "EEG_or_model_loaded": False,
               "saved_records": {key: value for key, value in records.items() if key not in {"sources", "raw_prediction_CSVs"}},
               "raw_prediction_CSV_roundtrip": records["raw_prediction_CSVs"], "outputs": files}
    (output / "DATA_EXPORT_VALIDATION.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
