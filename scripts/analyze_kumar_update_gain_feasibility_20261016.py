"""Exploratory update-gain feasibility from legal source/support summaries only.

Inputs contain 18 participants x five target sessions at full support (19/20).
The four feature columns are whitelisted; query BA enters training only for the
training participants, and enters evaluation only after actions are selected.
No EEG, model weights, trial-level query data, search or decoder fitting is used.
Real-data execution requires the separately frozen follow-up protocol.
"""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import platform
import subprocess

import numpy as np
import sklearn
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

DEV = tuple(f"sub-{i}" for i in (1, 4, 7, 10, 13, 16))
PRIMARY = tuple(f"sub-{i}" for i in range(1, 19) if f"sub-{i}" not in DEV)
SESSIONS = tuple(f"ses-{i}" for i in range(1, 6))
ACTIONS = ("frozen", "lda_only", "full_refit")
FEATURES = (
    "frozen_source_BA_all_support",
    "source40_to_support_trace_normalized_cov_frobenius",
    "support_cv_lda_gain",
    "support_cv_full_gain",
)
ALPHA = 10.0
BOOTSTRAP_DRAWS = 10000
SEED = 42
FEATURE_CONSISTENCY_ATOL = 1e-12
EXPECTED_KEYS = {(s, t) for s in DEV + PRIMARY for t in SESSIONS}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def ids_sha256(values):
    return sha256(json.dumps(values, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def finite(value, name):
    try:
        result = float(value)
    except (ValueError, TypeError) as error:
        raise ValueError(f"Invalid number: {name}") from error
    require(math.isfinite(result), f"Nonfinite number: {name}")
    return result


def integer(value, name):
    result = finite(value, name)
    require(result.is_integer(), f"Noninteger: {name}")
    return int(result)


def boolean(value, name):
    require(value in (True, False, "True", "False", "true", "false", "1", "0"),
            f"Invalid boolean: {name}")
    return value in (True, "True", "true", "1")


def unique_json(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read_csv(data):
    reader = csv.DictReader(io.StringIO(data.decode("utf-8"), newline=""))
    fields = reader.fieldnames
    require(fields and len(fields) == len(set(fields)), "Missing/duplicate CSV columns")
    rows = list(reader)
    require(all(None not in r and None not in r.values() for r in rows), "Malformed CSV row")
    return rows


def identities(rows, name):
    keys = [(r.get("subject"), r.get("session")) for r in rows]
    require(len(keys) == len(set(keys)), f"Duplicate {name} identity")
    require(set(keys) == EXPECTED_KEYS, f"Missing/extra {name} participant/session identity")
    return dict(zip(keys, rows, strict=True))


def bounded(value, name, low=0, high=1):
    result = finite(value, name)
    require(low <= result <= high, f"Out-of-range {name}")
    return result


def validate_inputs(feature_rows, outcome_rows, provenance, synthetic=False):
    """Fail closed on identities, feature missingness and source/support fit leakage.

    Source/support IDs are producer-supplied legal provenance; chronological
    order is checked against that supplied order, not independently against EEG.
    Query identity hashes are pairing metadata, never model inputs.
    """
    features = identities(feature_rows, "feature")
    outcomes = identities(outcome_rows, "outcome")
    require(provenance.get("schema_version") == 1, "Unsupported provenance schema")
    require(provenance.get("synthetic") is synthetic, "Synthetic provenance mismatch")
    require(provenance.get("software_validation_only") is synthetic,
            "Software-only provenance mismatch")
    require(provenance.get("support_order") == "chronological", "Support order not chronological")
    audit = identities(provenance.get("rows", []), "provenance")
    source_ids_by_subject = {}
    source_ba_by_subject = {}
    trial_owners = {}
    support_owners = {}
    clean_features, clean_outcomes = [], {}
    for key in sorted(EXPECTED_KEYS):
        f, o, p = features[key], outcomes[key], audit[key]
        cohort = "development6" if key[0] in DEV else "remaining12"
        require(f.get("cohort") == o.get("cohort") == cohort, "Cohort identity mismatch")
        n = integer(f["n_support"], "support count")
        require(n in (19, 20) and integer(o["n_support"], "outcome support count") == n,
                "Only full support of 19/20 is allowed")
        left = integer(f["support_left"], "support left")
        right = integer(f["support_right"], "support right")
        require(0 < left <= 10 and 0 < right <= 10 and left + right == n,
                "Invalid support classes")
        arrays = {}
        for field in ("source_trial_ids", "support_trial_ids", "support_train_half_trial_ids",
                      "support_holdout_trial_ids", "lda_fit_trial_ids", "full_refit_fit_trial_ids"):
            values = p.get(field)
            require(isinstance(values, list) and all(isinstance(x, str) and x for x in values),
                    f"Missing/invalid source/support provenance: {field}")
            require(len(values) == len(set(values)), f"Duplicate trial ID: {field}")
            arrays[field] = values
        source, support = arrays["source_trial_ids"], arrays["support_trial_ids"]
        prefix, holdout = arrays["support_train_half_trial_ids"], arrays["support_holdout_trial_ids"]
        require(len(source) == 40 and len(support) == n, "Source/support provenance count mismatch")
        require(f.get("source_trial_ids_sha256") == ids_sha256(source)
                and f.get("support_trial_ids_sha256") == ids_sha256(support),
                "Source/support identity hash mismatch")
        require(not set(source) & set(support), "Source/support leakage")
        for trial in source + support:
            require(trial not in trial_owners or trial_owners[trial] == key[0],
                    "Trial identity shared across participants")
            trial_owners[trial] = key[0]
        for trial in support:
            require(trial not in support_owners, "Support trial identity shared across sessions")
            support_owners[trial] = key
        require(prefix == support[:n // 2] and holdout == support[n // 2:],
                "Support chronological half split mismatch")
        for field in ("lda_fit_trial_ids", "full_refit_fit_trial_ids"):
            require(arrays[field] == source + prefix, f"Incorrect fit IDs: {field}")
            require(not set(arrays[field]) & set(holdout), f"Holdout entered fit: {field}")
        if key[0] in source_ids_by_subject:
            require(source == source_ids_by_subject[key[0]], "Source IDs change across sessions")
        source_ids_by_subject[key[0]] = source
        require(integer(f["support_train_half_n"], "prefix count") == len(prefix)
                and integer(f["support_holdout_n"], "holdout count") == len(holdout),
                "Half-split count mismatch")
        hl = integer(f["support_holdout_left"], "holdout left")
        hr = integer(f["support_holdout_right"], "holdout right")
        require(hl >= 0 and hr >= 0 and hl + hr == len(holdout), "Invalid holdout classes")
        defined = boolean(f["holdout_defined"], "holdout_defined")
        fallback = boolean(f["holdout_fallback_frozen"], "holdout fallback")
        missing_class = hl == 0 or hr == 0
        require(not missing_class or (not defined and fallback), "Missing holdout class not flagged")
        require(defined or fallback, "Undefined holdout must fall back to frozen")
        gains = [0.0, 0.0]
        if defined:
            require(not missing_class, "Single-class holdout BA is not defined")
            bas = [bounded(f[f"holdout_BA_{a}"], f"holdout BA {a}") for a in ACTIONS]
            gains = [bas[1] - bas[0], bas[2] - bas[0]]
            if fallback:
                require(bas[0] == bas[1] == bas[2], "Fallback holdout BA must equal frozen")
        else:
            require(bool(f.get("holdout_missing_reason")), "Missing holdout reason required")
            require(all(f.get(f"holdout_BA_{a}") in ("", None) for a in ACTIONS),
                    "Undefined holdout BA must be missing")
        for name, recomputed in zip(FEATURES[2:], gains, strict=True):
            supplied = bounded(f[name], name, -1, 1)
            require(math.isclose(supplied, recomputed, rel_tol=0,
                                 abs_tol=FEATURE_CONSISTENCY_ATOL),
                    f"Support-CV feature inconsistent with holdout BA: {name}")
        x = [bounded(f[FEATURES[0]], FEATURES[0]),
             bounded(f[FEATURES[1]], FEATURES[1], 0, math.sqrt(2) + 1e-12), *gains]
        clean_features.append({"subject": key[0], "session": key[1], "cohort": cohort,
                               "n_support": n,
                               "source_trial_ids_sha256": f["source_trial_ids_sha256"],
                               "support_trial_ids_sha256": f["support_trial_ids_sha256"],
                               "support_train_half_n": len(prefix),
                               "support_holdout_n": len(holdout),
                               "holdout_missing_reason": f.get("holdout_missing_reason", ""),
                               "x": x, "holdout_fallback_frozen": fallback,
                               "feature_missing_holdout_class": missing_class})
        query_hash = o.get("query_trial_ids_sha256", "")
        require(len(query_hash) == 64 and all(c in "0123456789abcdef" for c in query_hash),
                "Missing/invalid query identity hash")
        require(integer(o["n_query"], "query count") > 0, "Invalid query count")
        source_ba = bounded(o["frozen_source_query_BA"], "source query BA")
        if key[0] in source_ba_by_subject:
            require(source_ba == source_ba_by_subject[key[0]], "Source query BA changes by session")
        source_ba_by_subject[key[0]] = source_ba
        clean_outcomes[key] = {"ba": [bounded(o[f"BA_{a}"], f"query BA {a}") for a in ACTIONS],
                               "frozen_source_query_BA": source_ba,
                               "query_trial_ids_sha256": query_hash,
                               "n_query": integer(o["n_query"], "query count")}
    return clean_features, clean_outcomes


def choose(gain_lda, gain_full):
    """Exact ties prefer frozen, then LDA, then full; no fitted risk threshold."""
    return int(np.argmax([0.0, gain_lda, gain_full]))


def fit_fold(train_features, train_targets, evaluation_features):
    """Evaluation outcomes cannot enter this interface or scaler.fit/Ridge.fit."""
    train_subjects = sorted({r["subject"] for r in train_features})
    eval_subjects = sorted({r["subject"] for r in evaluation_features})
    require(not set(train_subjects) & set(eval_subjects), "Participant train/evaluation overlap")
    x = np.asarray([r["x"] for r in train_features], dtype=float)
    y = np.asarray(train_targets, dtype=float)
    require(x.shape == (len(train_features), 4) and y.shape == (len(train_features), 2),
            "Training matrix shape mismatch")
    require(np.isfinite(x).all() and np.isfinite(y).all(), "Nonfinite training matrix")
    scaler = StandardScaler().fit(x)
    model = Ridge(alpha=ALPHA).fit(scaler.transform(x), y)
    predictions = model.predict(scaler.transform(np.asarray([r["x"] for r in evaluation_features])))
    threshold = float(np.median(x[:, 1]))
    audit = {"train_participants": train_subjects, "evaluation_participants": eval_subjects,
             "train_rows": [f"{r['subject']}/{r['session']}" for r in train_features],
             "scaler_mean": scaler.mean_.tolist(), "scaler_scale": scaler.scale_.tolist(),
             "ridge_alpha": ALPHA, "ridge_coef": model.coef_.tolist(),
             "ridge_intercept": model.intercept_.tolist(), "drift_threshold": threshold}
    return predictions, threshold, audit


def build_decisions(features, outcomes):
    """Fit on other development participants, then all six for remaining12."""
    decisions, audits = [], []
    folds = [(f"dev_lopo_{s}", [p for p in DEV if p != s], [s]) for s in DEV]
    folds.append(("remaining12_train_development6", list(DEV), list(PRIMARY)))
    for fold, train_subjects, eval_subjects in folds:
        train = [r for r in features if r["subject"] in train_subjects]
        evaluation = [r for r in features if r["subject"] in eval_subjects]
        targets = [[outcomes[(r["subject"], r["session"])]["ba"][j]
                    - outcomes[(r["subject"], r["session"])]["ba"][0] for j in (1, 2)]
                   for r in train]
        predictions, threshold, audit = fit_fold(train, targets, evaluation)
        audits.append({"fold": fold, **audit})
        for r, pred in zip(evaluation, predictions, strict=True):
            cv = 0 if r["holdout_fallback_frozen"] else choose(r["x"][2], r["x"][3])
            decisions.append({**r, "fold": fold, "predicted_lda_gain": float(pred[0]),
                              "predicted_full_gain": float(pred[1]),
                              "predicted_full_minus_lda_gain": float(pred[1] - pred[0]),
                              "ridge": choose(*pred),
                              "support_cv": cv,
                              "drift_median": 2 if r["x"][1] >= threshold else 0})
    return decisions, audits


def evaluate_decisions(decisions, outcomes):
    """Score fixed actions and exact frequency-matched random mixture expectations."""
    rows = []
    for fold in sorted({r["fold"] for r in decisions}):
        selected = [r for r in decisions if r["fold"] == fold]
        probabilities = np.bincount([r["ridge"] for r in selected], minlength=3) / len(selected)
        for d in selected:
            o = outcomes[(d["subject"], d["session"])]
            bas = np.asarray(o["ba"])
            policies = {"always_frozen": 0, "always_lda_only": 1, "always_full_refit": 2,
                        "ridge": d["ridge"], "support_cv": d["support_cv"],
                        "drift_median": d["drift_median"], "matched_random_expectation": None}
            for policy, action in policies.items():
                probs = probabilities if action is None else np.eye(3)[action]
                ba = float(probs @ bas)
                gains = bas - bas[0]
                rows.append({"subject": d["subject"], "session": d["session"],
                             "cohort": d["cohort"], "fold": fold, "policy": policy,
                             "action": "expected_mixture" if action is None else ACTIONS[action],
                             "BA": ba, "gain_vs_frozen_BA": ba - bas[0],
                             "gain_vs_lda_only_BA": ba - bas[1],
                             "gain_vs_full_refit_BA": ba - bas[2],
                             "downside_frequency": float(probs @ (gains < 0)),
                             "downside_magnitude_BA": float(probs @ np.maximum(-gains, 0)),
                             "rate_frozen": float(probs[0]), "rate_lda_only": float(probs[1]),
                             "rate_full_refit": float(probs[2]),
                             "frozen_source_to_target_decline_BA": o["frozen_source_query_BA"]
                             - bas[0],
                             "predicted_lda_minus_frozen_BA": d["predicted_lda_gain"],
                             "actual_lda_minus_frozen_BA": float(bas[1] - bas[0]),
                             "predicted_full_minus_frozen_BA": d["predicted_full_gain"],
                             "actual_full_minus_frozen_BA": float(bas[2] - bas[0]),
                             "predicted_full_minus_lda_BA": d["predicted_full_minus_lda_gain"],
                             "actual_full_minus_lda_BA": float(bas[2] - bas[1]),
                             "lda_gain_sign_agrees": bool(np.sign(d["predicted_lda_gain"])
                                                          == np.sign(bas[1] - bas[0])),
                             "full_gain_sign_agrees": bool(np.sign(d["predicted_full_gain"])
                                                           == np.sign(bas[2] - bas[0])),
                             "full_minus_lda_sign_agrees": bool(
                                 np.sign(d["predicted_full_minus_lda_gain"])
                                 == np.sign(bas[2] - bas[1])),
                             "query_trial_ids_sha256": o["query_trial_ids_sha256"],
                             "n_query": o["n_query"]})
    return rows


METRICS = ("BA", "gain_vs_frozen_BA", "gain_vs_lda_only_BA", "gain_vs_full_refit_BA",
           "downside_frequency", "downside_magnitude_BA", "rate_frozen", "rate_lda_only",
           "rate_full_refit", "frozen_source_to_target_decline_BA")


def summarize(rows):
    """Equal-session participant endpoints; bootstrap whole participants only."""
    participant_rows, summaries = [], []
    for cohort, subjects in (("development6", DEV), ("remaining12", PRIMARY)):
        draws = np.random.default_rng(SEED).integers(len(subjects),
                                                   size=(BOOTSTRAP_DRAWS, len(subjects)))
        for policy in sorted({r["policy"] for r in rows}):
            endpoints = []
            for subject in subjects:
                sessions = [r for r in rows if r["subject"] == subject and r["policy"] == policy]
                require({r["session"] for r in sessions} == set(SESSIONS),
                        "Missing participant evaluation session")
                metrics = {m: float(np.mean([r[m] for r in sessions])) for m in METRICS}
                participant_rows.append({"subject": subject, "cohort": cohort, "policy": policy,
                                         "n_sessions": len(sessions), **metrics})
                endpoints.append([metrics[m] for m in METRICS])
            values = np.asarray(endpoints)
            ci = np.quantile(values[draws].mean(axis=1), [.025, .975], axis=0)
            for j, metric in enumerate(METRICS):
                summaries.append({"cohort": cohort, "policy": policy, "metric": metric,
                                  "n_participants": len(subjects),
                                  "mean": float(values[:, j].mean()),
                                  "ci95_low": float(ci[0, j]), "ci95_high": float(ci[1, j])})
    return participant_rows, summaries


def risk_sign_diagnostics(decisions, outcomes):
    """Descriptive sign diagnostics; sessions do not become independent people."""
    result = []
    for cohort in ("development6", "remaining12"):
        selected = [r for r in decisions if r["cohort"] == cohort]
        contrasts = (("lda_minus_frozen", 1, 0, "predicted_lda_gain"),
                     ("full_minus_frozen", 2, 0, "predicted_full_gain"),
                     ("full_minus_lda", 2, 1, "predicted_full_minus_lda_gain"))
        for contrast, action, reference, column in contrasts:
            pred = np.asarray([r[column] for r in selected]) < 0
            actual = np.asarray([outcomes[(r["subject"], r["session"])]["ba"][action]
                                 - outcomes[(r["subject"], r["session"])]["ba"][reference]
                                 for r in selected]) < 0
            result.append({"cohort": cohort, "contrast": contrast,
                           "n_participants": len({r["subject"] for r in selected}),
                           "n_sessions_descriptive": len(selected),
                           "predicted_negative_actual_decline": int(sum(pred & actual)),
                           "predicted_negative_no_decline": int(sum(pred & ~actual)),
                           "predicted_nonnegative_actual_decline": int(sum(~pred & actual)),
                           "predicted_nonnegative_no_decline": int(sum(~pred & ~actual))})
    return result


def csv_bytes(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def render_report(summary, synthetic):
    lines = ["# Exploratory update-gain feasibility", "",
             f"synthetic={str(synthetic).lower()}; software_validation_only={str(synthetic).lower()}",
             "", "All 18 participants were previously exposed. Development leave-one-participant-out "
             "and remaining12 evaluation after training on six development participants are "
             "exploratory; this is not independent confirmation or a validated gate.", "",
             "Four source/support features, training-fold StandardScaler and two-target Ridge "
             "(alpha=10) are fixed. Ties prefer frozen, LDA, full. Missing holdout classes set "
             "both CV gains to zero and force the support-CV selector to frozen. Drift uses "
             "the training-participant session median, without query tuning.", "",
             "| Cohort | Policy | Mean BA (%) | Gain vs frozen (pp; participant 95% CI) | "
             "Decline frequency (%) | Mean downside (pp) | Update rate (%) |",
             "|---|---|---:|---:|---:|---:|---:|"]
    index = {(r["cohort"], r["policy"], r["metric"]): r for r in summary}
    for cohort in ("development6", "remaining12"):
        for policy in sorted({r["policy"] for r in summary}):
            def metric(name):
                return index[(cohort, policy, name)]
            gain = metric("gain_vs_frozen_BA")
            lines.append(f"| {cohort} | {policy} | {100 * metric('BA')['mean']:.2f} | "
                         f"{100 * gain['mean']:.2f} "
                         f"[{100 * gain['ci95_low']:.2f}, {100 * gain['ci95_high']:.2f}] | "
                         f"{100 * metric('downside_frequency')['mean']:.2f} | "
                         f"{100 * metric('downside_magnitude_BA')['mean']:.2f} | "
                         f"{100 * (1 - metric('rate_frozen')['mean']):.2f} |")
    lines += ["", "Participant endpoints average the five sessions equally. All confidence intervals "
              "resample whole participants (10,000 draws, seed 42). Downside magnitude is "
              "max(frozen BA minus selected BA, 0), including zero for non-declining sessions. "
              "The random control is an exact action-mixture expectation within each development "
              "LOPO fold or the remaining12 group; its downside is the expectation of action-wise "
              "loss, rather than the loss of its mean BA.", "",
              "The complete CSV summary includes paired differences against each always-action "
              "baseline, action rates and participant intervals. Predicted-negative-gain versus "
              "actual-decline counts are descriptive session diagnostics, with participants "
              "retained as the independent unit. Frozen source-query to target-query decline is "
              "an explanatory outcome only. No external validation or novelty claim follows.", "",
              "Source/support fit disjointness is verified from upstream legal trial-ID provenance. "
              "Chronological order is an upstream assertion. Query-set hashes are pairing metadata, "
              "and no query trial records, EEG or decoder weights are loaded."]
    return "\n".join(lines) + "\n"


def run(features_path, outcomes_path, provenance_path, output, synthetic=False):
    started_utc = datetime.now(timezone.utc).isoformat()
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"Output must be a fresh directory: {output}")
    paths = {"features": Path(features_path), "outcomes": Path(outcomes_path),
             "provenance": Path(provenance_path)}
    require(paths["features"].suffix == paths["outcomes"].suffix == ".csv"
            and paths["provenance"].suffix == ".json", "Only summary CSV/JSON inputs are allowed")
    data = {name: path.read_bytes() for name, path in paths.items()}
    features, outcomes = validate_inputs(read_csv(data["features"]), read_csv(data["outcomes"]),
                                        json.loads(data["provenance"], object_pairs_hook=unique_json),
                                        synthetic=synthetic)
    with threadpool_limits(limits=1):
        decisions, audits = build_decisions(features, outcomes)
    evaluation = evaluate_decisions(decisions, outcomes)
    participants, summary = summarize(evaluation)
    flat_decisions = [{k: v for k, v in row.items() if k != "x"} |
                      dict(zip(FEATURES, row["x"], strict=True)) for row in decisions]
    tables = {"session_decisions.csv": flat_decisions,
              "session_policy_evaluation.csv": evaluation,
              "participant_policy_endpoints.csv": participants,
              "participant_bootstrap_summary.csv": summary,
              "risk_sign_diagnostics.csv": risk_sign_diagnostics(decisions, outcomes)}
    outputs = {name: csv_bytes([dict(row, synthetic=synthetic, software_validation_only=synthetic)
                               for row in rows]) for name, rows in tables.items()}
    outputs["model_fit_audit.json"] = (json.dumps(
        {"synthetic": synthetic, "software_validation_only": synthetic, "folds": audits},
        indent=2, allow_nan=False) + "\n").encode()
    outputs["REPORT.md"] = render_report(summary, synthetic).encode()
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=Path(__file__).parents[1],
                                         text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "unavailable"
    receipt = {"analysis_status": "posthoc_exploratory_all18_previously_exposed",
               "synthetic": synthetic, "software_validation_only": synthetic,
               "features": list(FEATURES), "alpha": ALPHA, "bootstrap_draws": BOOTSTRAP_DRAWS,
               "feature_consistency_atol": FEATURE_CONSISTENCY_ATOL,
               "feature_consistency_rtol": 0,
               "seed": SEED, "tie_order": list(ACTIONS), "source_commit": commit,
               "script_sha256": sha256(Path(__file__).read_bytes()),
               "input_sha256": {k: sha256(v) for k, v in data.items()},
               "output_sha256": {k: sha256(v) for k, v in outputs.items()},
               "versions": {"python": platform.python_version(), "numpy": np.__version__,
                            "scikit_learn": sklearn.__version__},
               "n_feature_rows": len(features), "n_participants": len(DEV + PRIMARY),
               "independent_statistical_unit": "participant",
               "confidence_intervals": "Pointwise exploratory 95% percentile; no new p-value family",
               "numerical_threads": 1,
               "random_control": "Exact expected mixture; action frequencies match Ridge within "
                                 "each development LOPO fold or the remaining12 evaluation group",
               "downside_magnitude": "Mean max(frozen BA minus policy BA,0) over all sessions; "
                                     "for random, expectation over actions before aggregation",
               "source_decline": "Frozen source-query BA minus target-query BA; outcome only",
               "provenance_limit": "Source/support disjointness and half-split fits checked on "
                                   "provided trial IDs; chronology supplied by upstream producer",
               "no_eeg_weights_query_trial_access": True,
               "no_hyperparameter_search_or_external_validation": True}
    # All input validation and computation finish before creating any output.
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in outputs.items():
        with (output / name).open("xb") as handle:
            handle.write(raw)
    receipt["started_utc"] = started_utc
    receipt["finished_utc"] = datetime.now(timezone.utc).isoformat()
    with (output / "execution_receipt.json").open("x", encoding="utf-8") as handle:
        json.dump(receipt, handle, indent=2, allow_nan=False)
        handle.write("\n")
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("features", "outcomes", "provenance", "output"):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--synthetic", action="store_true",
                        help="Software tests only; must match provenance flags")
    args = parser.parse_args(argv)
    try:
        run(args.features, args.outcomes, args.provenance, args.output, args.synthetic)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f"error: {error}\n")


if __name__ == "__main__":
    main()
