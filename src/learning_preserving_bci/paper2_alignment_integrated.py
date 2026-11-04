"""Descriptive reanalysis of saved binary EEG predictions, without model execution.

All rates are fractions internally. Nonlinear weak-class metrics are calculated
at the original endpoint before repeated endpoints are averaged within people.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import sys

import numpy as np


METHODS = ("frozen", "lda_only", "full_csp", "ea_csp")
KUMAR_METHODS = dict(zip(("source_only", "frozen_csp_lda_recalibration",
                         "refit_csp_lda", "ea_csp_lda"), METHODS))
BUDGETS = ("4", "8", "12", "16", "full")
DEVELOPMENT = tuple(f"sub-{i}" for i in (1, 4, 7, 10, 13, 16))
ALL_KUMAR = tuple(f"sub-{i}" for i in range(1, 19))
PRIMARY = tuple(p for p in ALL_KUMAR if p not in DEVELOPMENT)
CONTRASTS = (("lda_minus_frozen", "frozen", "lda_only"),
             ("full_minus_frozen", "frozen", "full_csp"),
             ("full_minus_lda", "lda_only", "full_csp"),
             ("ea_minus_full", "full_csp", "ea_csp"),
             ("ea_minus_frozen", "frozen", "ea_csp"))
METRICS = ("ba", "weak_recall", "recall_gap", "recall_left", "recall_right")
TOLERANCE = 1e-12
SEED = 20261104
RESAMPLES = 10000


def require(condition, message):
    if not condition:
        raise ValueError(message)


def numeric_order(value):
    return tuple(int(x) if x.isdigit() else x for x in re.split(r"(\d+)", value))


def binary_metrics(truth, prediction):
    """Score one original endpoint; undefined recalls remain None, never zero."""
    y = np.asarray(truth)
    p = np.asarray(prediction)
    require(y.ndim == p.ndim == 1 and y.shape == p.shape, "Prediction shape mismatch")
    require(set(y.tolist()) <= {0, 1} and set(p.tolist()) <= {0, 1}, "Nonbinary outcome")
    counts = [int(np.sum(y == c)) for c in (0, 1)]
    correct = [int(np.sum((y == c) & (p == c))) for c in (0, 1)]
    recalls = [correct[c] / counts[c] if counts[c] else None for c in (0, 1)]
    complete = all(n > 0 for n in counts)
    ba = sum(recalls) / 2 if complete else None
    weak = min(recalls) if complete else None
    gap = abs(recalls[0] - recalls[1]) if complete else None
    if complete:
        require(abs(weak - (ba - gap / 2)) <= TOLERANCE, "Weak-class identity failed")
    return {"n_query": len(y), "n_left": counts[0], "n_right": counts[1],
            "correct_left": correct[0], "correct_right": correct[1],
            "recall_left": recalls[0], "recall_right": recalls[1],
            "ba": ba, "weak_recall": weak, "recall_gap": gap,
            "prediction_left": int(np.sum(p == 0)), "prediction_right": int(np.sum(p == 1)),
            "status": "ok" if complete else "undefined_missing_class"}


def paired_transition(truth, reference, new):
    """Class-balanced C/I/D fractions with full query-class denominators."""
    a = binary_metrics(truth, reference)
    b = binary_metrics(truth, new)
    if a["status"] != "ok":
        return {"corrected": None, "introduced": None, "disagreement": None,
                **{"delta_" + key: None for key in METRICS}, "status": a["status"]}
    y, ref, pred = np.asarray(truth), np.asarray(reference), np.asarray(new)
    weights = np.asarray([1 / (2 * (a["n_left"] if c == 0 else a["n_right"])) for c in y])
    corrected = float(np.sum(weights[(ref != y) & (pred == y)]))
    introduced = float(np.sum(weights[(ref == y) & (pred != y)]))
    disagreement = float(np.sum(weights[ref != pred]))
    delta = {"delta_" + key: b[key] - a[key] for key in METRICS}
    require(abs(corrected - introduced - delta["delta_ba"]) <= TOLERANCE,
            "Corrected-minus-introduced identity failed")
    require(abs(disagreement - corrected - introduced) <= TOLERANCE,
            "Binary disagreement identity failed")
    return {"corrected": corrected, "introduced": introduced,
            "disagreement": disagreement, **delta, "status": "ok"}


def pair_predictions(reference, new):
    """One-to-one strict identity/order/label join; never a many-to-many join."""
    def identities(rows):
        ids = [r["trial_id"] for r in rows]
        require(len(ids) == len(set(ids)), "Duplicate trial identity")
        return ids
    require(identities(reference) == identities(new), "Query identity/order mismatch")
    require([r["label"] for r in reference] == [r["label"] for r in new],
            "Query label mismatch")
    return ([int(r["label"]) for r in reference],
            [int(r["prediction"]) for r in reference],
            [int(r["prediction"]) for r in new])


def signed(value, tolerance=TOLERANCE):
    return "positive" if value > tolerance else "negative" if value < -tolerance else "zero"


def paired_summary(values):
    """One fixed descriptive participant bootstrap, preserving paired differences."""
    x = np.asarray(values, dtype=np.float64)
    require(x.ndim == 1 and np.isfinite(x).all(), "Invalid participant values")
    if len(x) == 0:
        return {"n": 0, "mean": None, "ci_low": None, "ci_high": None,
                "median": None, "minimum": None, "maximum": None,
                "positive": 0, "zero": 0, "negative": 0,
                "leave_one_out_min": None, "leave_one_out_max": None,
                "status": "undefined_no_eligible_participant"}
    draws = np.random.default_rng(SEED).integers(0, len(x), (RESAMPLES, len(x)))
    low, high = np.quantile(x[draws].mean(axis=1), [0.025, 0.975], method="linear")
    counts = Counter(signed(v) for v in x)
    leave = (x.sum() - x) / (len(x) - 1) if len(x) > 1 else None
    return {"n": len(x), "mean": float(x.mean()), "ci_low": float(low), "ci_high": float(high),
            "median": float(np.median(x)), "minimum": float(x.min()), "maximum": float(x.max()),
            "positive": counts["positive"], "zero": counts["zero"], "negative": counts["negative"],
            "leave_one_out_min": float(leave.min()) if leave is not None else None,
            "leave_one_out_max": float(leave.max()) if leave is not None else None,
            "status": "ok" if len(x) > 1 else "single_participant_degenerate_interval"}


def read_csv(path):
    body = Path(path).read_bytes()
    if str(path).endswith(".gz"):
        body = gzip.decompress(body)
    return list(csv.DictReader(io.StringIO(body.decode(), newline="")))


def source_manifest(paths, root):
    return [{"path": str(p.relative_to(root)), "bytes": p.stat().st_size,
             "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in sorted(set(paths))]


def load_inputs(root):
    """Load only saved labels/decisions and frozen identity metadata, not EEG."""
    root = Path(root)
    budget_dir = root / "research_logs/paper2_structure_revision_20261029/component_replay/input/budget"
    paths = [budget_dir / "query_predictions.csv.gz", budget_dir / "session_metrics.csv.gz",
             root / "research_logs/kumar_cross_session_20261012/protocol/split_manifest.json",
             root / "research_logs/kumar_submission_qc_20261015/run01/query_identity_qc_ledger.csv"]
    frozen_rows = json.loads(paths[2].read_text())["trials"]
    frozen = {r["trial_id"]: r for r in frozen_rows}
    require(len(frozen) == len(frozen_rows), "Duplicate frozen trial")
    qc_rows = read_csv(paths[3])
    qc = {r["trial_id"]: r for r in qc_rows}
    require(len(qc) == len(qc_rows), "Duplicate QC ledger trial")
    records, raw_metrics = [], {}
    for row in read_csv(paths[1]):
        key = row["subject"], row["session"], row["budget"], KUMAR_METHODS[row["method"]]
        require(key not in raw_metrics, "Duplicate historical metric cell")
        raw_metrics[key] = row
    for row in read_csv(paths[0]):
        require(row["synthetic"] == row["software_validation_only"] == "False", "Synthetic outcome")
        meta = frozen[row["trial_id"]]
        require(meta["included"] and meta["role"] == "target_query", "Nonquery prediction")
        require(all(meta[k] == row[k] for k in ("subject", "session", "run")), "Trial metadata mismatch")
        require(int(row["label"]) == (0 if meta["label"] == "left_hand" else 1), "Frozen label mismatch")
        flag = qc[row["trial_id"]]
        require(flag["included"] == "True" and flag["role"] == "target_query"
                and all(flag[k] == row[k] for k in ("subject", "session", "run")), "QC identity mismatch")
        require(flag["label"] == meta["label"], "QC label mismatch")
        require((flag["qc_peak_to_peak_over_250uv"] == "True")
                == bool(meta["qc_peak_to_peak_over_250uv"]), "QC flag mismatch")
        require(bool(meta["qc_peak_to_peak_over_250uv"])
                == (float(flag["raw_peak_to_peak_max_volts"]) > 0.00025), "QC rule mismatch")
        require(row["subject"] in ALL_KUMAR and row["session"] in {f"ses-{i}" for i in range(1, 6)},
                "Unfrozen participant/session")
        require(row["budget"] in BUDGETS, "Unfrozen support budget")
        require(row["cohort"] == ("development6" if row["subject"] in DEVELOPMENT else "remaining12"),
                "Cohort identity mismatch")
        records.append({"dataset": "Kumar2024", "participant": row["subject"], "session": row["session"],
                        "run": row["run"], "budget": row["budget"], "k": int(row["k"]),
                        "method": KUMAR_METHODS[row["method"]], "trial_id": row["trial_id"],
                        "label": int(row["label"]), "prediction": int(row["prediction"]),
                        "qc_flagged": bool(meta["qc_peak_to_peak_over_250uv"]),
                        "fallback": row["fallback"] == "True"})
    bnci = root / "research_logs/paper2_external_validation_20261027"
    bnci_metrics = {}
    for participant in range(1, 10):
        identity = bnci / f"trial_identity/bnci001-sub-{participant:02d}/manifest.json"
        paths.append(identity)
        m = json.loads(identity.read_text())
        require(m["metadata"]["query_used_for_fitting"] is False
                and m["metadata"]["whole_run_role_disjoint"] is True, "BNCI role metadata")
        trial_meta = {r["trial_id"]: r for r in m["trials"]}
        require(len(trial_meta) == len(m["trials"]), "Duplicate BNCI frozen trial")
        for method in METHODS:
            p = bnci / f"saved_predictions/bnci001-sub-{participant:02d}/E__n20__{method}.json"
            paths.append(p)
            saved = json.loads(p.read_text())
            require(saved["query_used_for_fitting"] is False and saved["synthetic"] is False,
                    "BNCI inference/empirical identity")
            require(saved["dataset"] == "BNCI2014-001" and saved["method"] == method
                    and saved["session"] == "E" and int(saved["participant"]) == participant,
                    "BNCI result identity")
            require(saved["budget_requested"] == saved["n_support_available"] == 20
                    and saved["n_support_actual"] == (0 if method == "frozen" else 20),
                    "BNCI budget mismatch")
            require(len(saved["trial_ids"]) == len(saved["y"]) == len(saved["prediction"]) == 120,
                    "BNCI saved arrays mismatch")
            expected_ids = [r["trial_id"] for r in m["trials"] if r["included"] and r["role"] == "query"]
            require(expected_ids == saved["trial_ids"], "BNCI whole-run query order")
            bnci_metrics[(f"sub-{participant:02d}", method)] = saved["metrics"]["balanced_accuracy"]
            for tid, y, prediction in zip(saved["trial_ids"], saved["y"], saved["prediction"]):
                meta = trial_meta[tid]
                require(meta["included"] and meta["role"] == "query" and meta["label"] == y,
                        "BNCI query label/role mismatch")
                records.append({"dataset": "BNCI2014-001", "participant": f"sub-{participant:02d}",
                                "session": "E", "run": f"run-{meta['run']}", "budget": "full", "k": 20,
                                "method": method, "trial_id": tid, "label": int(y),
                                "prediction": int(prediction), "qc_flagged": None, "fallback": False})
    return records, raw_metrics, bnci_metrics, paths


def group_records(records):
    groups = defaultdict(list)
    for r in records:
        key = tuple(r[k] for k in ("dataset", "participant", "session", "budget", "method"))
        groups[key].append(r)
    signatures = {}
    for key, group in groups.items():
        pair_predictions(group, group)
        sig_key = key[:3]
        signature = [(r["trial_id"], r["label"], r["run"]) for r in group]
        require(sig_key not in signatures or signatures[sig_key] == signature,
                "Method/budget query identities, order or labels differ")
        signatures[sig_key] = signature
        binary_metrics([r["label"] for r in group], [r["prediction"] for r in group])
    return groups


def endpoint_tables(groups, subset="all_query"):
    metrics, transitions = [], []
    for key in sorted(groups, key=lambda x: tuple(numeric_order(s) for s in x)):
        dataset, participant, session, budget, method = key
        group = groups[key]
        if subset == "unflagged_query":
            group = [r for r in group if not r["qc_flagged"]]
        context = dict(dataset=dataset, participant=participant, session=session,
                       budget=budget, method=method, subset=subset)
        metrics.append({**context, "support_count": groups[key][0]["k"],
                        "labels_used": 0 if method == "frozen" else groups[key][0]["k"],
                        "fallback": any(r["fallback"] for r in groups[key]),
                        **binary_metrics([r["label"] for r in group], [r["prediction"] for r in group])})
    bases = {key[:-1] for key in groups}
    for base in sorted(bases, key=lambda x: tuple(numeric_order(s) for s in x)):
        dataset, participant, session, budget = base
        require(all(base + (m,) in groups for m in METHODS), "Incomplete four-method endpoint")
        for contrast, ref, new in CONTRASTS:
            a, b = groups[base + (ref,)], groups[base + (new,)]
            if subset == "unflagged_query":
                a, b = [r for r in a if not r["qc_flagged"]], [r for r in b if not r["qc_flagged"]]
            y, pa, pb = pair_predictions(a, b)
            metrics_a = binary_metrics(y, pa)
            transitions.append(dict(dataset=dataset, participant=participant, session=session,
                                    budget=budget, subset=subset, contrast=contrast,
                                    n_query=len(y), n_left=metrics_a["n_left"], n_right=metrics_a["n_right"],
                                    **paired_transition(y, pa, pb)))
    return metrics, transitions


def participant_tables(metrics, transitions):
    outputs = []
    for rows, keys, fields in [(metrics, ("dataset", "participant", "budget", "method", "subset"), METRICS),
                               (transitions, ("dataset", "participant", "budget", "contrast", "subset"),
                                tuple("delta_" + x for x in METRICS) + ("corrected", "introduced", "disagreement"))]:
        grouped = defaultdict(list)
        for r in rows:
            grouped[tuple(r[k] for k in keys)].append(r)
        table = []
        for key in sorted(grouped, key=lambda x: tuple(numeric_order(s) for s in x)):
            cells = grouped[key]
            expected = 5 if key[0] == "Kumar2024" else 1
            require(len(cells) == expected and len({r["session"] for r in cells}) == expected,
                    "Missing or repeated original endpoint")
            complete = all(r["status"] == "ok" for r in cells)
            result = {**dict(zip(keys, key)), "n_endpoints_expected": expected,
                      "n_endpoints_defined": sum(r["status"] == "ok" for r in cells),
                      "n_query_total": sum(r["n_query"] for r in cells),
                      "status": "ok" if complete else "undefined_incomplete_participant"}
            result.update({f: float(np.mean([r[f] for r in cells])) if complete else None for f in fields})
            if "contrast" in result:
                result.update({"endpoint_" + sign + "_fraction":
                               sum(signed(r["delta_ba"]) == sign for r in cells) / expected if complete else None
                               for sign in ("positive", "zero", "negative")})
            table.append(result)
        outputs.append(table)
    return outputs


def cohorts(dataset):
    if dataset == "Kumar2024":
        return {"development6": DEVELOPMENT, "remaining12": PRIMARY, "all18_descriptive": ALL_KUMAR}
    return {"external9": tuple(f"sub-{i:02d}" for i in range(1, 10))}


def summarize_participants(participants, contrasts):
    mean_rows, effect_rows, joint_rows = [], [], []
    for table, method_key, fields, target in [
            (participants, "method", METRICS, mean_rows),
            (contrasts, "contrast", tuple("delta_" + x for x in METRICS)
             + ("corrected", "introduced", "disagreement", "endpoint_positive_fraction",
                "endpoint_zero_fraction", "endpoint_negative_fraction"), effect_rows)]:
        groups = defaultdict(list)
        for row in table:
            groups[(row["dataset"], row["budget"], row[method_key], row["subset"])].append(row)
        for group_key, rows in sorted(groups.items()):
            dataset, budget, method, subset = group_key
            lookup = {r["participant"]: r for r in rows}
            for cohort, ids in cohorts(dataset).items():
                require(set(ids) <= set(lookup), "Cohort endpoint missing")
                valid = [p for p in ids if lookup[p]["status"] == "ok"]
                common = dict(dataset=dataset, cohort=cohort, budget=budget, subset=subset,
                              **{method_key: method}, n_expected=len(ids),
                              participants=json.dumps(valid, separators=(",", ":")))
                for field in fields:
                    target.append({**common, "metric": field,
                                   **paired_summary([lookup[p][field] for p in valid])})
                if method_key == "contrast":
                    for ba_sign in ("positive", "zero", "negative"):
                        for w_sign in ("positive", "zero", "negative"):
                            members = [p for p in valid if signed(lookup[p]["delta_ba"]) == ba_sign
                                       and signed(lookup[p]["delta_weak_recall"]) == w_sign]
                            joint_rows.append({**common, "ba_sign": ba_sign, "weak_recall_sign": w_sign,
                                               "count": len(members), "n_defined": len(valid),
                                               "fraction": len(members) / len(valid) if valid else None,
                                               "members": json.dumps(members, separators=(",", ":"))})
    return mean_rows, effect_rows, joint_rows


def qc_same_eligible(participants, contrasts):
    """Compare all/restricted queries on the same complete participant identities."""
    out = []
    for table, identity, fields in [(participants, "method", METRICS),
                                    (contrasts, "contrast", tuple("delta_" + x for x in METRICS))]:
        groups = defaultdict(dict)
        for row in table:
            if row["dataset"] == "Kumar2024" and row["budget"] == "full":
                groups[row[identity]][(row["participant"], row["subset"])] = row
        for name, lookup in sorted(groups.items()):
            for cohort, expected in cohorts("Kumar2024").items():
                eligible = [p for p in expected if lookup[p, "unflagged_query"]["status"] == "ok"]
                for field in fields:
                    a = [lookup[p, "all_query"][field] for p in eligible]
                    b = [lookup[p, "unflagged_query"][field] for p in eligible]
                    context = dict(dataset="Kumar2024", cohort=cohort, budget="full", **{identity: name},
                                   metric=field, n_expected=len(expected), n_eligible=len(eligible),
                                   eligible_participants=json.dumps(eligible, separators=(",", ":")))
                    for scope, values in [("all_query_same_eligible", a), ("unflagged_query", b),
                                          ("paired_unflagged_minus_all", [y - x for x, y in zip(a, b)])]:
                        out.append({**context, "scope": scope, **paired_summary(values)})
    return out


def run_tables(records):
    """Describe runs without substituting them for independent participants."""
    groups = defaultdict(list)
    for r in records:
        if r["budget"] == "full":
            groups[(r["dataset"], r["participant"], r["session"], r["run"], r["method"])].append(r)
    metrics, contrasts = [], []
    for key, group in sorted(groups.items()):
        metrics.append({**dict(zip(("dataset", "participant", "session", "run", "method"), key)),
                        **binary_metrics([r["label"] for r in group], [r["prediction"] for r in group])})
    for base in sorted({k[:-1] for k in groups}):
        for name, ref, new in CONTRASTS:
            a, b = groups[base + (ref,)], groups[base + (new,)]
            y, pa, pb = pair_predictions(a, b)
            counts = Counter(y)
            contrasts.append({**dict(zip(("dataset", "participant", "session", "run"), base)),
                              "contrast": name, "n_query": len(y), "n_left": counts[0],
                              "n_right": counts[1], **paired_transition(y, pa, pb)})
    person_groups = defaultdict(list)
    for row in contrasts:
        person_groups[(row["dataset"], row["participant"], row["contrast"])].append(row)
    people = []
    for key, rows in sorted(person_groups.items()):
        valid = [r for r in rows if r["status"] == "ok"]
        people.append({**dict(zip(("dataset", "participant", "contrast"), key)),
                       "runs_total": len(rows), "runs_defined": len(valid),
                       "runs_undefined": len(rows) - len(valid),
                       **{sign + "_fraction": sum(signed(r["delta_ba"]) == sign for r in valid) / len(valid)
                          if valid else None for sign in ("positive", "zero", "negative")}})
    cohort_rows = []
    for dataset in sorted({r["dataset"] for r in people}):
        for name, _, _ in CONTRASTS:
            lookup = {r["participant"]: r for r in people if r["dataset"] == dataset and r["contrast"] == name}
            for cohort, expected in cohorts(dataset).items():
                valid = [p for p in expected if lookup[p]["runs_defined"] > 0]
                for sign in ("positive", "zero", "negative"):
                    cohort_rows.append(dict(dataset=dataset, cohort=cohort, contrast=name,
                                            run_effect_sign=sign, n_expected=len(expected),
                                            participants=json.dumps(valid, separators=(",", ":")),
                                            weighting="run fraction within participant; participants equal",
                                            **paired_summary([lookup[p][sign + "_fraction"] for p in valid])))
    return metrics, contrasts, people, cohort_rows


def write_table(path, rows):
    require(bool(rows), f"Empty result table: {path}")
    fieldnames = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("x", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def execute(root, output, plan_commit):
    """Recompute descriptive endpoints from saved decisions exactly once per output."""
    root, output = Path(root), Path(output)
    require(not output.exists(), "Output already exists; preserve the completed reanalysis")
    records, historical_kumar, historical_bnci, paths = load_inputs(root)
    inputs = source_manifest(paths, root)
    groups = group_records(records)
    require(len(groups) == 18 * 5 * 5 * 4 + 9 * 4, "Saved endpoint grid changed")
    metrics, transitions = endpoint_tables(groups)
    max_error = 0.0
    for row in metrics:
        if row["dataset"] == "Kumar2024":
            old = historical_kumar[(row["participant"], row["session"], row["budget"], row["method"])]
            expected = float(old["balanced_accuracy"])
            require(row["support_count"] == int(old["k"]) and row["n_query"] == int(old["n_query"]),
                    "Saved support/query counts changed")
            expected_hash = old["query_trial_ids_sha256"]
            key = tuple(row[k] for k in ("dataset", "participant", "session", "budget", "method"))
            ids = [r["trial_id"] for r in groups[key]]
            require(hashlib.sha256(json.dumps(ids, separators=(",", ":")).encode()).hexdigest()
                    == expected_hash, "Saved query hash changed")
        else:
            expected = historical_bnci[row["participant"], row["method"]]
        error = abs(row["ba"] - expected)
        max_error = max(error, max_error)
        require(error <= 5e-15, "Historical BA differs from saved decisions")
    qc_groups = {k: g for k, g in groups.items() if k[0] == "Kumar2024" and k[3] == "full"}
    qc_metrics, qc_transitions = endpoint_tables(qc_groups, "unflagged_query")
    metrics += qc_metrics
    transitions += qc_transitions
    participants, participant_contrasts = participant_tables(metrics, transitions)
    means, effects, joint = summarize_participants(participants, participant_contrasts)
    qc = qc_same_eligible(participants, participant_contrasts)
    # Run-level profiles are diagnostics; they never replace the original endpoint weights.
    run_metrics, run_contrasts, run_people, run_cohorts = run_tables(records)
    require(source_manifest(paths, root) == inputs, "An input changed during reanalysis")
    output.mkdir(parents=True)
    for name, rows in {"endpoint_metrics.csv": metrics, "endpoint_transitions.csv": transitions,
                       "participant_metrics.csv": participants, "participant_contrasts.csv": participant_contrasts,
                       "cohort_method_metrics.csv": means, "cohort_contrasts.csv": effects,
                       "joint_benefit_distribution.csv": joint,
                       "qc_same_eligible_comparisons.csv": qc, "query_run_metrics.csv": run_metrics,
                       "query_run_contrasts.csv": run_contrasts,
                       "participant_run_effect_distribution.csv": run_people,
                       "cohort_run_effect_distribution.csv": run_cohorts}.items():
        write_table(output / name, rows)
    report = {"analysis": "saved-prediction descriptive reanalysis; no new fit or query forward",
              "plan_commit": plan_commit, "input_files": inputs, "saved_prediction_rows": len(records),
              "original_endpoint_groups": len(groups), "maximum_historical_BA_error": max_error,
              "bootstrap": {"replicates": RESAMPLES, "seed": SEED, "quantile_method": "linear",
                            "unit": "participant", "order": "numeric participant identifier",
                            "identity": "new descriptive intervals; historical intervals unchanged"},
              "sign_tolerance": TOLERANCE, "units": "fractions; multiply rate differences by 100 for pp",
              "label_mapping": {"0": "left_hand", "1": "right_hand"},
              "cohort_membership": {"development6": DEVELOPMENT, "remaining12": PRIMARY,
                                    "all18_descriptive": ALL_KUMAR},
              "probability_metrics": {"status": "unavailable", "reason": "Both selected prediction exports contain hard labels, not probabilities or logits; none inferred."},
              "new_fit_count": 0, "query_forward_count": 0, "EEG_loaded": False,
              "historical_files_modified": False, "new_p_values_or_comparison_family": False,
              "software": {"python": sys.version, "numpy": np.__version__},
              "run_diagnostic_rows": len(run_contrasts),
              "input_immutable_check": "passed", "identity_and_binary_metric_checks": "passed"}
    (output / "INPUT_MANIFEST.json").write_text(json.dumps(inputs, indent=2) + "\n")
    (output / "ANALYSIS_REPORT.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
