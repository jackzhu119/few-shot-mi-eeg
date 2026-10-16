"""synthetic=true; software_validation_only for the portable statistics replay."""

import copy
import csv
import importlib.util
import io
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "postreview_statistics",
    Path(__file__).parents[1] / "scripts/analyze_kumar_postreview_statistics_20261016.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def synthetic_inputs():
    definition = {
        "schema_version": 1, "analysis_status": "review_triggered_exploratory",
        "synthetic": True, "software_validation_only": True,
        "participant_order": "lexicographic", "signflip_atol_BA": 1e-12,
        "signflip_rtol": 0, "tail": "absolute_mean_inclusive", "holm_family_size": 4,
        "original_bootstrap_draws": 10000, "original_bootstrap_seed": 42, "contrasts": [],
    }
    rows = []
    for name, subset, left, right, subjects in MODULE.CONTRASTS:
        definition["contrasts"].append({
            "contrast_id": name, "cohort": "remaining12", "subset": subset,
            "left_method": left, "right_method": right, "n": len(subjects),
            "participants": list(subjects),
            "saved_ci95_low_BA_unchanged": "0.010000000000000009",
            "saved_ci95_high_BA_unchanged": "0.23000000000000001",
        })
        for subject in subjects:
            index = MODULE.REMAINING12.index(subject)
            endpoints = {
                "source_only": .4 + .005 * index,
                "frozen_csp_lda_recalibration": .45 + .004 * index,
                "refit_csp_lda": .49 + .008 * index,
            }
            difference = endpoints[left] - endpoints[right]
            rows.append({
                "contrast_id": name, "subject": subject, "subset": subset,
                "left_method": left, "right_method": right,
                "left_endpoint_BA": repr(endpoints[left]),
                "right_endpoint_BA": repr(endpoints[right]),
                "paired_difference_BA_original_decimal": repr(difference),
                "paired_difference_pp": repr(100 * difference),
                "source": "same_saved_participant_endpoints",
            })
    return rows, definition


def write_inputs(path, rows, definition):
    path.mkdir()
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=MODULE.FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    data = stream.getvalue().encode()
    definition = copy.deepcopy(definition)
    definition["participant_csv_sha256"] = MODULE.sha256(data)
    (path / MODULE.CSV_NAME).write_bytes(data)
    (path / MODULE.DEFINITION_NAME).write_text(json.dumps(definition))


@pytest.mark.parametrize("case", ["duplicate", "missing", "extra", "order", "method",
                                  "subject", "subset", "difference", "nan", "infinity",
                                  "bounds", "units", "shared_endpoint"])
def test_strict_identity_and_numerical_validation(case):
    rows, definition = synthetic_inputs()
    if case == "duplicate":
        rows[1] = rows[0].copy()
    elif case == "missing":
        rows.pop()
    elif case == "extra":
        rows.append(rows[0].copy())
    elif case == "order":
        rows[0], rows[1] = rows[1], rows[0]
    elif case in ("method", "subject", "subset"):
        field = {"method": "left_method", "subject": "subject", "subset": "subset"}[case]
        rows[0][field] = "unexpected"
    elif case == "difference":
        rows[0]["paired_difference_BA_original_decimal"] = ".9"
    elif case in ("nan", "infinity", "bounds"):
        rows[0]["left_endpoint_BA"] = {"nan": "nan", "infinity": "inf", "bounds": "1.2"}[case]
    elif case == "units":
        rows[0]["paired_difference_pp"] = ".00001"
    else:
        # Keep this row's subtraction valid while violating the same method endpoint elsewhere.
        rows[12]["left_endpoint_BA"] = ".8"
        difference = .8 - float(rows[12]["right_endpoint_BA"])
        rows[12]["paired_difference_BA_original_decimal"] = repr(difference)
        rows[12]["paired_difference_pp"] = repr(100 * difference)
    with pytest.raises(ValueError):
        MODULE.validate_inputs(rows, definition)


@pytest.mark.parametrize("field,value", [
    ("signflip_atol_BA", 1e-6), ("holm_family_size", 3),
    ("participant_order", "numeric"), ("analysis_status", "confirmatory"),
])
def test_fixed_definitions_cannot_drift(field, value):
    rows, definition = synthetic_inputs()
    definition[field] = value
    with pytest.raises(ValueError):
        MODULE.validate_inputs(rows, definition)


def test_full_enumeration_zero_multiplicity_and_near_ties():
    positive = MODULE.sign_flip(["1", "2", "3"])
    assert (positive["signflip_tail_numerator"], positive["signflip_denominator"]) == (2, 8)
    zero = MODULE.sign_flip(["0", "0", "0", "0"])
    assert (zero["signflip_tail_numerator"], zero["signflip_denominator"]) == (16, 16)
    assert MODULE.sign_flip(["1", "1", "0"])["signflip_tail_numerator"] == 4
    near = MODULE.sign_flip(["1", "1", "0.0000000000001"])
    assert near["signflip_tail_numerator"] == 4
    assert near["signflip_exact_fraction_tail_numerator"] == 2
    assert not near["signflip_fraction_agrees"]
    with pytest.raises(ValueError, match="Empty"):
        MODULE.sign_flip([])


def test_holm_mapping_monotonicity_ties_and_invalid_family():
    assert MODULE.holm_adjust([.04, .01, .03, .2]) == [.09, .04, .09, .2]
    assert MODULE.holm_adjust([.5] * 4) == [1.] * 4
    with pytest.raises(ValueError):
        MODULE.holm_adjust([.01] * 3)
    with pytest.raises(ValueError):
        MODULE.holm_adjust([.01, .02, .03, float("nan")])


def test_portable_fresh_replay_is_identical_and_preserves_ci_strings(tmp_path):
    rows, definition = synthetic_inputs()
    inputs = tmp_path / "portable_inputs"
    write_inputs(inputs, rows, definition)
    first, replay = tmp_path / "first", tmp_path / "replay"
    results = MODULE.run(inputs, first)
    MODULE.run(inputs, replay)
    assert len(results) == 4 and sum(r["n"] for r in results) == 46
    for name in ("statistics_results.csv", "execution_receipt.json"):
        assert (first / name).read_bytes() == (replay / name).read_bytes()
    assert all(r["saved_ci95_low_BA_unchanged"] == "0.010000000000000009" for r in results)
    assert json.loads((first / "execution_receipt.json").read_text())["synthetic"] is True
    with pytest.raises(FileExistsError, match="fresh"):
        MODULE.run(inputs, first)


def test_invalid_inputs_never_create_output(tmp_path):
    rows, definition = synthetic_inputs()
    rows.pop()
    inputs, output = tmp_path / "inputs", tmp_path / "uncreated"
    write_inputs(inputs, rows, definition)
    with pytest.raises(ValueError, match="Missing/extra"):
        MODULE.run(inputs, output)
    assert not output.exists()


def test_hash_and_duplicate_json_key_fail_before_output(tmp_path):
    rows, definition = synthetic_inputs()
    inputs, output = tmp_path / "inputs", tmp_path / "uncreated"
    write_inputs(inputs, rows, definition)
    csv_path = inputs / MODULE.CSV_NAME
    original = csv_path.read_bytes()
    csv_path.write_bytes(original + b"\n")
    with pytest.raises(ValueError, match="SHA256"):
        MODULE.run(inputs, output)
    assert not output.exists()
    csv_path.write_bytes(original)
    path = inputs / MODULE.DEFINITION_NAME
    path.write_text(path.read_text().replace('"schema_version": 1',
                                            '"schema_version": 1, "schema_version": 1'))
    with pytest.raises(ValueError, match="Duplicate JSON"):
        MODULE.run(inputs, output)
    assert not output.exists()


def test_existing_file_or_dangling_symlink_output_is_never_overwritten(tmp_path):
    output = tmp_path / "occupied"
    output.write_text("preserve original bytes")
    with pytest.raises(FileExistsError):
        MODULE.run(tmp_path / "absent_inputs", output)
    assert output.read_text() == "preserve original bytes"
    link = tmp_path / "dangling"
    link.symlink_to(tmp_path / "absent")
    with pytest.raises(FileExistsError):
        MODULE.run(tmp_path / "absent_inputs", link)
    assert link.is_symlink()


def test_no_arguments_print_usage_and_exit(capsys):
    with pytest.raises(SystemExit) as error:
        MODULE.main([])
    assert error.value.code == 2
    assert "usage:" in capsys.readouterr().err
