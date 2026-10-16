"""synthetic=true; software_validation_only for the four-feature CSV selector."""

import copy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

SPEC = importlib.util.spec_from_file_location(
    "gain_feasibility",
    Path(__file__).parents[1] / "scripts/analyze_kumar_update_gain_feasibility_20261016.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def synthetic_inputs():
    """Arbitrary BA summaries exercise software; no EEG or scientific fit outcomes."""
    features, outcomes, provenance_rows = [], [], []
    for si, subject in enumerate(MODULE.DEV + MODULE.PRIMARY):
        source = [f"{subject}/source/{i}" for i in range(40)]
        cohort = "development6" if subject in MODULE.DEV else "remaining12"
        for ti, session in enumerate(MODULE.SESSIONS):
            n = 19 if (si + ti) % 3 == 0 else 20
            support = [f"{subject}/{session}/support/{i}" for i in range(n)]
            prefix, holdout = support[:n // 2], support[n // 2:]
            features.append({"subject": subject, "session": session, "cohort": cohort,
                             "source_trial_ids_sha256": MODULE.ids_sha256(source),
                             "support_trial_ids_sha256": MODULE.ids_sha256(support),
                             "n_support": n, "support_left": n // 2,
                             "support_right": n - n // 2,
                             "frozen_source_BA_all_support": .45 + .02 * (si % 5),
                             "source40_to_support_trace_normalized_cov_frobenius":
                             .05 * (1 + ti + si % 4),
                             "support_train_half_n": len(prefix),
                             "support_holdout_n": len(holdout),
                             "support_holdout_left": len(holdout) // 2,
                             "support_holdout_right": len(holdout) - len(holdout) // 2,
                             "holdout_BA_frozen": .5,
                             "holdout_BA_lda_only": .48 + .01 * ti,
                             "holdout_BA_full_refit": .47 + .02 * (si % 4),
                             "support_cv_lda_gain": .48 + .01 * ti - .5,
                             "support_cv_full_gain": .47 + .02 * (si % 4) - .5,
                             "holdout_defined": True, "holdout_fallback_frozen": False,
                             "holdout_missing_reason": ""})
            base = .46 + .01 * ti
            outcomes.append({"subject": subject, "session": session, "cohort": cohort,
                             "n_support": n, "n_query": 60, "query_trial_ids_sha256": "a" * 64,
                             "BA_frozen": base, "BA_lda_only": base - .03 + .01 * (si % 5),
                             "BA_full_refit": base - .02 + .02 * ti,
                             "frozen_source_query_BA": .6 + .005 * si})
            provenance_rows.append({"subject": subject, "session": session,
                                    "source_trial_ids": source,
                                    "support_trial_ids": support,
                                    "support_train_half_trial_ids": prefix,
                                    "support_holdout_trial_ids": holdout,
                                    "lda_fit_trial_ids": source + prefix,
                                    "full_refit_fit_trial_ids": source + prefix})
    return features, outcomes, {"schema_version": 1, "synthetic": True,
                                  "software_validation_only": True,
                                  "support_order": "chronological", "rows": provenance_rows}


def clean_inputs():
    return MODULE.validate_inputs(*synthetic_inputs(), synthetic=True)


def write_inputs(path):
    path.mkdir()
    f, o, p = synthetic_inputs()
    paths = [path / "features.csv", path / "outcomes.csv", path / "provenance.json"]
    paths[0].write_bytes(MODULE.csv_bytes(f))
    paths[1].write_bytes(MODULE.csv_bytes(o))
    paths[2].write_text(json.dumps(p))
    return paths


@pytest.mark.parametrize("case", ["duplicate_feature", "missing_feature", "duplicate_outcome",
                                  "missing_outcome", "wrong_cohort", "bad_budget", "nan_feature",
                                  "nan_outcome", "invalid_query_hash", "source_ba_changes",
                                  "noninteger_count", "missing_provenance"])
def test_bad_csv_identities_missingness_and_bounds_fail(case):
    f, o, p = synthetic_inputs()
    if case == "duplicate_feature":
        f.append(f[0].copy())
    elif case == "missing_feature":
        f.pop()
    elif case == "duplicate_outcome":
        o.append(o[0].copy())
    elif case == "missing_outcome":
        o.pop()
    elif case == "wrong_cohort":
        f[0]["cohort"] = "remaining12"
    elif case == "bad_budget":
        f[0]["n_support"] = 16
    elif case == "nan_feature":
        f[0][MODULE.FEATURES[1]] = "nan"
    elif case == "nan_outcome":
        o[0]["BA_full_refit"] = "inf"
    elif case == "invalid_query_hash":
        o[0]["query_trial_ids_sha256"] = "missing"
    elif case == "source_ba_changes":
        o[1]["frozen_source_query_BA"] = .3
    elif case == "noninteger_count":
        f[0]["support_train_half_n"] = 9.5
    else:
        p["rows"].pop()
    with pytest.raises(ValueError):
        MODULE.validate_inputs(f, o, p, synthetic=True)


@pytest.mark.parametrize("case,message", [
    ("source_support_overlap", "Source/support leakage"),
    ("holdout_in_fit", "Incorrect fit IDs"), ("wrong_half", "half split"),
    ("future_fit", "Incorrect fit IDs"), ("duplicate_trial", "Duplicate trial"),
    ("cross_participant", "shared across participants"),
    ("cross_session", "shared across sessions"), ("synthetic_unmarked", "Synthetic provenance"),
])
def test_source_support_fit_and_participant_isolation(case, message):
    f, o, p = synthetic_inputs()
    r = p["rows"][0]
    if case == "source_support_overlap":
        r["source_trial_ids"][0] = r["support_trial_ids"][0]
    elif case == "holdout_in_fit":
        r["lda_fit_trial_ids"][-1] = r["support_holdout_trial_ids"][0]
    elif case == "wrong_half":
        r["support_train_half_trial_ids"] = r["support_train_half_trial_ids"][::-1]
    elif case == "future_fit":
        r["full_refit_fit_trial_ids"].append("sub-1/future/trial")
    elif case == "duplicate_trial":
        r["source_trial_ids"][1] = r["source_trial_ids"][0]
    elif case == "cross_participant":
        # Preserve the other participant's within-row fit identity while copying a source ID.
        other = p["rows"][5]
        old = other["source_trial_ids"][0]
        for field in ("source_trial_ids", "lda_fit_trial_ids", "full_refit_fit_trial_ids"):
            other[field] = [r["source_trial_ids"][0] if x == old else x for x in other[field]]
    elif case == "cross_session":
        other = p["rows"][1]
        old = other["support_trial_ids"][0]
        for field in ("support_trial_ids", "support_train_half_trial_ids", "lda_fit_trial_ids",
                      "full_refit_fit_trial_ids"):
            other[field] = [r["support_trial_ids"][0] if x == old else x for x in other[field]]
    else:
        p["synthetic"] = False
    # Preserve valid hashes so these tests exercise fit/isolation checks themselves.
    for feature, prov in zip(f, p["rows"], strict=True):
        feature["source_trial_ids_sha256"] = MODULE.ids_sha256(prov["source_trial_ids"])
        feature["support_trial_ids_sha256"] = MODULE.ids_sha256(prov["support_trial_ids"])
    with pytest.raises(ValueError, match=message):
        MODULE.validate_inputs(f, o, p, synthetic=True)


def test_missing_holdout_class_has_zero_gains_and_cv_frozen():
    f, o, p = synthetic_inputs()
    f[0].update({"support_holdout_left": 0, "support_holdout_right": f[0]["support_holdout_n"],
                 "holdout_defined": False, "holdout_fallback_frozen": True,
                 "support_cv_lda_gain": 0, "support_cv_full_gain": 0,
                 "holdout_missing_reason": "missing_holdout_class",
                 **{f"holdout_BA_{a}": "" for a in MODULE.ACTIONS}})
    features, outcomes = MODULE.validate_inputs(f, o, p, synthetic=True)
    row = next(r for r in features if (r["subject"], r["session"]) == ("sub-1", "ses-1"))
    assert row["x"][2:] == [0, 0]
    assert row["feature_missing_holdout_class"] is True
    decisions, _ = MODULE.build_decisions(features, outcomes)
    assert next(r["support_cv"] for r in decisions
                if (r["subject"], r["session"]) == ("sub-1", "ses-1")) == 0
    f[0]["holdout_fallback_frozen"] = False
    with pytest.raises(ValueError, match="flagged"):
        MODULE.validate_inputs(f, o, p, synthetic=True)


def test_evaluation_query_changes_never_change_own_predictions_or_fits():
    features, outcomes = clean_inputs()
    original, original_audit = MODULE.build_decisions(features, outcomes)
    changed = copy.deepcopy(outcomes)
    for (subject, _), outcome in changed.items():
        if subject in MODULE.PRIMARY:
            outcome["ba"] = [.1, .9, .2]
            outcome["frozen_source_query_BA"] = .123
    revised, revised_audit = MODULE.build_decisions(features, changed)
    assert original == revised and original_audit == revised_audit
    for key, outcome in changed.items():
        if key[0] == MODULE.DEV[0]:
            outcome["ba"] = [.8, .1, .9]
    revised, revised_audit = MODULE.build_decisions(features, changed)
    def own(rows):
        return [r for r in rows if r["subject"] == MODULE.DEV[0]]
    assert own(original) == own(revised)
    assert original_audit[0] == revised_audit[0]


def test_train_only_scaler_threshold_and_exact_ties():
    features, outcomes = clean_inputs()
    train = [r for r in features if r["subject"] in MODULE.DEV[1:]]
    evaluation = [r for r in features if r["subject"] == MODULE.DEV[0]]
    targets = [[outcomes[(r["subject"], r["session"])]["ba"][a]
                - outcomes[(r["subject"], r["session"])]["ba"][0] for a in (1, 2)] for r in train]
    _, threshold, audit = MODULE.fit_fold(train, targets, evaluation)
    changed = copy.deepcopy(evaluation)
    for row in changed:
        row["x"] = [1000] * 4
    _, changed_threshold, changed_audit = MODULE.fit_fold(train, targets, changed)
    assert threshold == changed_threshold and audit == changed_audit
    np.testing.assert_allclose(audit["scaler_mean"], np.mean([r["x"] for r in train], axis=0))
    assert threshold == np.median([r["x"][1] for r in train])
    assert MODULE.choose(0, 0) == MODULE.choose(-1, -1) == 0
    assert MODULE.choose(.1, .1) == 1
    assert MODULE.choose(.1, .2) == 2
    with pytest.raises(ValueError, match="overlap"):
        MODULE.fit_fold(train, targets, train[:1])


def test_exact_random_expectation_and_participant_statistics():
    features, outcomes = clean_inputs()
    decisions, _ = MODULE.build_decisions(features, outcomes)
    for i, row in enumerate(decisions):
        row["ridge"] = i % 3  # Explicit synthetic action pattern, not a model result.
    evaluated = MODULE.evaluate_decisions(decisions, outcomes)
    for fold in {r["fold"] for r in decisions}:
        selected = [r for r in decisions if r["fold"] == fold]
        rates = np.bincount([r["ridge"] for r in selected], minlength=3) / len(selected)
        for row in evaluated:
            if row["fold"] != fold or row["policy"] != "matched_random_expectation":
                continue
            ba = np.array(outcomes[(row["subject"], row["session"])]["ba"])
            np.testing.assert_allclose(row["BA"], rates @ ba)
            np.testing.assert_allclose(row["downside_frequency"], rates @ (ba < ba[0]))
            np.testing.assert_allclose(row["downside_magnitude_BA"],
                                       rates @ np.maximum(ba[0] - ba, 0))
    participants, summary = MODULE.summarize(evaluated)
    assert len(participants) == 18 * 7
    assert {r["n_participants"] for r in summary} == {6, 12}
    assert all(r["ci95_low"] - 1e-12 <= r["mean"] <= r["ci95_high"] + 1e-12 for r in summary)
    assert all(r["mean"] == 0 for r in summary if r["policy"] == "always_frozen"
               and r["metric"] == "gain_vs_frozen_BA")
    sign_rows = MODULE.risk_sign_diagnostics(decisions, outcomes)
    assert len(sign_rows) == 6
    assert {r["contrast"] for r in sign_rows} == {
        "lda_minus_frozen", "full_minus_frozen", "full_minus_lda"}
    for row in sign_rows:
        assert sum(v for k, v in row.items() if k.startswith("predicted_")) \
            == row["n_sessions_descriptive"]


def test_synthetic_end_to_end_is_reproducible_marked_and_preserves_outputs(tmp_path):
    inputs = write_inputs(tmp_path / "inputs")
    output, replay = tmp_path / "output", tmp_path / "replay"
    receipt = MODULE.run(*inputs, output, synthetic=True)
    MODULE.run(*inputs, replay, synthetic=True)
    assert receipt["synthetic"] is receipt["software_validation_only"] is True
    assert receipt["n_feature_rows"] == 90
    for path in output.iterdir():
        if path.name == "execution_receipt.json":
            first_receipt = json.loads(path.read_text())
            replay_receipt = json.loads((replay / path.name).read_text())
            for item in (first_receipt, replay_receipt):
                started = datetime.fromisoformat(item.pop("started_utc"))
                finished = datetime.fromisoformat(item.pop("finished_utc"))
                assert started.tzinfo == finished.tzinfo == timezone.utc
                assert started <= finished
            assert first_receipt == replay_receipt
        else:
            assert path.read_bytes() == (replay / path.name).read_bytes()
        if path.suffix == ".csv":
            rows = MODULE.read_csv(path.read_bytes())
            assert all(r["synthetic"] == r["software_validation_only"] == "True" for r in rows)
    with pytest.raises(FileExistsError):
        MODULE.run(*inputs, output, synthetic=True)


def test_validation_precedes_output_creation_and_cli_missing_args(tmp_path, capsys):
    inputs = write_inputs(tmp_path / "inputs")
    inputs[1].write_bytes(inputs[1].read_bytes().replace(b"BA_frozen", b"BA_unknown"))
    output = tmp_path / "uncreated"
    with pytest.raises(KeyError):
        MODULE.run(*inputs, output, synthetic=True)
    assert not output.exists()
    with pytest.raises(SystemExit) as error:
        MODULE.main([])
    assert error.value.code == 2
    assert "usage:" in capsys.readouterr().err


def test_duplicate_headers_json_keys_and_short_rows_are_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        MODULE.read_csv(b"subject,subject\nsub-1,sub-1\n")
    with pytest.raises(ValueError, match="Malformed"):
        MODULE.read_csv(b"subject,session\nsub-1\n")
    with pytest.raises(ValueError, match="Duplicate JSON"):
        json.loads('{"schema_version":1,"schema_version":1}', object_pairs_hook=MODULE.unique_json)


@pytest.mark.parametrize("field", MODULE.FEATURES[2:])
def test_explicit_cv_gain_must_match_holdout_ba_without_silent_repair(field):
    features, outcomes, provenance = synthetic_inputs()
    features[0][field] += 5e-13
    MODULE.validate_inputs(features, outcomes, provenance, synthetic=True)
    features[0][field] += 2e-12
    with pytest.raises(ValueError, match="inconsistent with holdout BA"):
        MODULE.validate_inputs(features, outcomes, provenance, synthetic=True)
    features, outcomes, provenance = synthetic_inputs()
    features[0].pop(field)
    with pytest.raises(KeyError):
        MODULE.validate_inputs(features, outcomes, provenance, synthetic=True)


def test_missing_class_requires_explicit_zero_gain_columns():
    features, outcomes, provenance = synthetic_inputs()
    features[0].update({"support_holdout_left": 0,
                        "support_holdout_right": features[0]["support_holdout_n"],
                        "holdout_defined": False, "holdout_fallback_frozen": True,
                        "holdout_missing_reason": "missing_holdout_class",
                        "support_cv_lda_gain": 0, "support_cv_full_gain": .01,
                        **{f"holdout_BA_{a}": "" for a in MODULE.ACTIONS}})
    with pytest.raises(ValueError, match="inconsistent with holdout BA"):
        MODULE.validate_inputs(features, outcomes, provenance, synthetic=True)
