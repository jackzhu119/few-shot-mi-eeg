"""Replay four review-triggered exploratory tests from saved participant endpoints.

Requires two small portable text inputs and an explicit fresh output directory.
No fitting, query evaluation, bootstrap recalculation, or scientific rule selection.
"""

import argparse
import csv
from fractions import Fraction
import hashlib
import io
import itertools
import json
import math
from pathlib import Path
import platform

import numpy as np

ATOL_BA = 1e-12
CSV_NAME = "participant_inputs.csv"
DEFINITION_NAME = "statistics_definition.json"
FIELDS = [
    "contrast_id", "subject", "subset", "left_method", "right_method",
    "left_endpoint_BA", "right_endpoint_BA", "paired_difference_BA_original_decimal",
    "paired_difference_pp", "source",
]
REMAINING12 = tuple(sorted(
    f"sub-{i}" for i in range(1, 19) if i not in (1, 4, 7, 10, 13, 16)
))
ELIGIBLE10 = tuple(s for s in REMAINING12 if s not in ("sub-12", "sub-8"))
CONTRASTS = (
    ("remaining12_full_minus_frozen", "all_included", "refit_csp_lda", "source_only",
     REMAINING12),
    ("remaining12_full_minus_lda_only", "all_included", "refit_csp_lda",
     "frozen_csp_lda_recalibration", REMAINING12),
    ("remaining12_lda_only_minus_frozen", "all_included", "frozen_csp_lda_recalibration",
     "source_only", REMAINING12),
    ("eligible10_unflagged_full_minus_frozen", "unflagged", "refit_csp_lda", "source_only",
     ELIGIBLE10),
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def unique_json(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def finite(value, name):
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid numerical {name}") from error
    require(math.isfinite(number), f"Nonfinite {name}")
    return number


def validate_inputs(rows, definition):
    """Require the fixed identities, endpoint pairing, numerical rules and old CIs."""
    require(definition.get("schema_version") == 1, "Unsupported definition schema")
    require(definition.get("analysis_status") == "review_triggered_exploratory",
            "Exploratory status must be retained")
    require(definition.get("participant_order") == "lexicographic", "Participant order changed")
    require(definition.get("signflip_atol_BA") == ATOL_BA
            and definition.get("signflip_rtol") == 0
            and definition.get("tail") == "absolute_mean_inclusive",
            "Fixed sign-flip tail/tolerance changed")
    require(definition.get("holm_family_size") == 4, "Fixed Holm family changed")
    require(definition.get("original_bootstrap_draws") == 10000
            and definition.get("original_bootstrap_seed") == 42,
            "Original bootstrap identity changed")
    specs = definition.get("contrasts")
    require(isinstance(specs, list) and len(specs) == 4, "Exactly four contrasts required")
    expected_keys = []
    for spec, (name, subset, left, right, subjects) in zip(specs, CONTRASTS, strict=True):
        require(spec.get("contrast_id") == name and spec.get("subset") == subset
                and spec.get("left_method") == left and spec.get("right_method") == right
                and spec.get("cohort") == "remaining12", "Fixed contrast identity changed")
        require(spec.get("n") == len(subjects)
                and spec.get("participants") == list(subjects), "Participant identity/order changed")
        for field in ("saved_ci95_low_BA_unchanged", "saved_ci95_high_BA_unchanged"):
            require(isinstance(spec.get(field), str), "Original CI must remain a decimal string")
        low = finite(spec["saved_ci95_low_BA_unchanged"], "CI lower limit")
        high = finite(spec["saved_ci95_high_BA_unchanged"], "CI upper limit")
        require(-1 <= low <= high <= 1, "Invalid original CI limits")
        expected_keys.extend((name, s, subset, left, right) for s in subjects)
    actual_keys = [(r.get("contrast_id"), r.get("subject"), r.get("subset"),
                    r.get("left_method"), r.get("right_method")) for r in rows]
    require(len(actual_keys) == len(set(actual_keys)), "Duplicate participant contrast row")
    require(actual_keys == expected_keys, "Missing/extra participant or row identity/order mismatch")
    endpoint_values = {}
    for row in rows:
        left = finite(row["left_endpoint_BA"], "left endpoint")
        right = finite(row["right_endpoint_BA"], "right endpoint")
        difference = finite(row["paired_difference_BA_original_decimal"], "paired difference")
        pp = finite(row["paired_difference_pp"], "paired difference pp")
        require(0 <= left <= 1 and 0 <= right <= 1, "Endpoint outside balanced-accuracy range")
        require(math.isclose(difference, left - right, rel_tol=0, abs_tol=5e-15),
                "Paired difference does not match saved endpoints")
        require(math.isclose(pp, difference * 100, rel_tol=0, abs_tol=5e-13),
                "Difference percentage-point units mismatch")
        require(row["source"] in ("saved_paired_contrast", "same_saved_participant_endpoints"),
                "Unexpected endpoint provenance")
        for method, value in ((row["left_method"], left), (row["right_method"], right)):
            key = (row["subject"], row["subset"], method)
            require(key not in endpoint_values or endpoint_values[key] == value,
                    "Shared participant endpoint differs across contrasts")
            endpoint_values[key] = value


def sign_flip(tokens):
    """Full 2**n enumeration; fixed inclusive tolerance, plus strict-decimal diagnostic."""
    values = [finite(x, "paired difference") for x in tokens]
    require(bool(values), "Empty difference vector")
    n = len(values)
    observed = abs(math.fsum(values) / n)
    fractions = [Fraction(x) for x in tokens]
    exact_observed = abs(sum(fractions))
    count = strict_count = fraction_count = ties = 0
    for signs in itertools.product((-1, 1), repeat=n):
        statistic = abs(math.fsum(s * x for s, x in zip(signs, values, strict=True)) / n)
        count += statistic >= observed - ATOL_BA
        strict_count += statistic >= observed
        ties += abs(statistic - observed) <= ATOL_BA
        fraction_count += abs(sum(s * x for s, x in zip(signs, fractions, strict=True))) \
            >= exact_observed
    return {
        "signflip_statistic_abs_mean_BA": observed,
        "signflip_tail_numerator": count,
        "signflip_denominator": 2**n,
        "signflip_p_two_sided": count / 2**n,
        "signflip_ties_within_atol": ties,
        "signflip_atol_BA": ATOL_BA,
        "signflip_rtol": 0,
        "signflip_float_strict_tail_numerator": strict_count,
        "signflip_exact_fraction_tail_numerator": fraction_count,
        "signflip_fraction_agrees": count == fraction_count,
    }


def holm_adjust(values):
    require(len(values) == 4 and all(0 <= p <= 1 for p in values), "Invalid fixed-family p values")
    order = sorted(range(4), key=lambda i: values[i])
    adjusted = [0.] * 4
    previous = 0.
    for rank, index in enumerate(order):
        previous = min(1., max(previous, (4 - rank) * values[index]))
        adjusted[index] = previous
    return adjusted


def summarize(rows, definition):
    validate_inputs(rows, definition)
    result = []
    for spec in definition["contrasts"]:
        selected = [r for r in rows if r["contrast_id"] == spec["contrast_id"]]
        tokens = [r["paired_difference_BA_original_decimal"] for r in selected]
        values = np.asarray([float(x) for x in tokens], dtype=np.float64)
        mean = float(values.mean())
        sd = float(values.std(ddof=1))
        result.append({
            "contrast_id": spec["contrast_id"], "cohort": spec["cohort"],
            "subset": spec["subset"], "n": len(values),
            "participants": ";".join(spec["participants"]),
            "mean_difference_BA": mean, "mean_difference_pp": 100 * mean,
            "saved_ci95_low_BA_unchanged": spec["saved_ci95_low_BA_unchanged"],
            "saved_ci95_high_BA_unchanged": spec["saved_ci95_high_BA_unchanged"],
            "cohen_dz": mean / sd if sd else "undefined_zero_sample_sd",
            "positive": int(sum(values > 0)), "zero": int(sum(values == 0)),
            "negative": int(sum(values < 0)), **sign_flip(tokens),
        })
    for row, adjusted in zip(result, holm_adjust([r["signflip_p_two_sided"] for r in result]),
                             strict=True):
        row["signflip_holm_adjusted_p_family4"] = adjusted
        row["interpretation"] = "Review-triggered exploratory; no confirmatory claim"
    return result


def run(inputs, output):
    inputs, output = Path(inputs), Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Output must be a fresh directory: {output}")
    csv_bytes = (inputs / CSV_NAME).read_bytes()
    definition_bytes = (inputs / DEFINITION_NAME).read_bytes()
    definition = json.loads(definition_bytes, object_pairs_hook=unique_json)
    require(isinstance(definition, dict), "Definition must be a JSON object")
    require(definition.get("participant_csv_sha256") == sha256(csv_bytes),
            "Participant CSV SHA256 mismatch")
    reader = csv.DictReader(io.StringIO(csv_bytes.decode("utf-8"), newline=""))
    require(reader.fieldnames == FIELDS, "Participant CSV schema mismatch")
    rows = list(reader)
    require(all(set(r) == set(FIELDS) and None not in r.values() for r in rows),
            "Malformed participant CSV row")
    results = summarize(rows, definition)
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(results[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(results)
    result_bytes = stream.getvalue().encode("utf-8")
    receipt = {
        "analysis_status": "review_triggered_exploratory",
        "synthetic": bool(definition.get("synthetic", False)),
        "software_validation_only": bool(definition.get("synthetic", False)),
        "python": platform.python_version(), "numpy": np.__version__,
        "input_sha256": {CSV_NAME: sha256(csv_bytes), DEFINITION_NAME: sha256(definition_bytes)},
        "statistics_results_csv_sha256": sha256(result_bytes),
        "participant_rows": len(rows), "fixed_comparisons": len(results),
        "original_ci_strings_retained": True,
        "no_training_query_evaluation_or_bootstrap_recalculation": True,
        "null_assumption": "Independent participant differences with a sign-symmetric null; "
                           "not a randomized allocation study",
        "multiplicity": "Holm across exactly four fixed sign-flip comparisons",
    }
    # Validation/computation completes before the first output mutation.
    output.mkdir(parents=True, exist_ok=False)
    with (output / "statistics_results.csv").open("xb") as handle:
        handle.write(result_bytes)
    with (output / "execution_receipt.json").open("x", encoding="utf-8") as handle:
        json.dump(receipt, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", required=True, type=Path,
                        help="Directory containing participant_inputs.csv and statistics_definition.json")
    parser.add_argument("--output", required=True, type=Path, help="New output directory; must not exist")
    args = parser.parse_args(argv)
    try:
        run(args.inputs, args.output)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f"error: {error}\n")


if __name__ == "__main__":
    main()
