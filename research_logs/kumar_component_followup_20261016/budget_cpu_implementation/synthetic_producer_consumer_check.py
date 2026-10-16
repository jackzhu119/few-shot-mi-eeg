"""Always-synthetic 18x5 producer/CSV/selector interface check; never real EEG."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[3]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


class FourPowerFeatures:
    """Fixed synthetic features for a schema check, not a scientific CSP fit."""

    def fit_transform(self, X, y):
        return self.transform(X)

    def transform(self, X):
        return np.log(np.square(X[:, :4]).mean(axis=2))


def factory(**kwargs):
    return SimpleNamespace(named_steps={
        "csp": FourPowerFeatures(),
        "lda": LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto"),
    })


def fixture(subject, development, seed):
    rng = np.random.default_rng(seed)
    tensors, labels, trials = [], [], []
    groups = [("ses-0", "run-0", "source_train", 20),
              ("ses-0", "run-1", "source_train", 20)]
    for number in range(1, 6):
        n = 19 if number == 2 else 20
        groups.extend([(f"ses-{number}", "run-0", "target_support", n),
                       (f"ses-{number}", "run-1", "target_query", 8)])
    for session, run, role, count in groups:
        for row in range(1, count + 1):
            if role == "target_support":
                # A one-class first4 remains; the full run obeys 9/10 or10/10.
                label = 1 if 5 <= row <= 14 else 0
                if subject == "sub-1" and session == "ses-5":
                    label = int(row > 10)  # Explicit undefined holdout case.
            else:
                label = row % 2
            X = rng.normal(size=(22, 96))
            X[label] *= 3
            X -= X.mean(axis=0, keepdims=True)
            tensors.append(X)
            labels.append(label)
            trials.append({"subject": subject, "session": session, "run": run,
                           "role": role, "source_row": row, "start_sample": row * 100,
                           "acquisition_time_utc": "2020-01-01T00:00:00+00:00",
                           "trial_id": f"{subject}/{session}/{run}/row-{row}",
                           "cohort": "development" if development else "final_test",
                           "synthetic": True, "software_validation_only": True})
    order = rng.permutation(len(trials))
    X, y = np.asarray(tensors)[order], np.asarray(labels)[order]
    trials = [trials[index] for index in order]
    saved = []
    for index, trial in enumerate(trials):
        if trial["role"] != "target_query":
            continue
        for method, predicted in (("source_only", 0),
                                  ("frozen_csp_lda_recalibration", 1 - int(y[index])),
                                  ("refit_csp_lda", int(y[index]))):
            saved.append({"subject": subject, "session": trial["session"], "run": trial["run"],
                          "method": method, "trial_id": trial["trial_id"], "label": int(y[index]),
                          "prediction": predicted, "synthetic": True,
                          "software_validation_only": True})
    for row in range(1, 21):
        saved.append({"subject": subject, "session": "ses-0", "run": "run-3",
                      "method": "source_only", "trial_id": f"{subject}/ses-0/run-3/row-{row}",
                      "label": row % 2, "prediction": row % 2, "synthetic": True,
                      "software_validation_only": True})
    return X, y, trials, saved


def run(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    budget = module("synthetic_budget_producer", ROOT / "scripts/run_kumar_component_budget_cpu_20261016.py")
    consumer = module("synthetic_gain_consumer", ROOT / "scripts/analyze_kumar_update_gain_feasibility_20261016.py")
    helpers = module("synthetic_budget_fixture", ROOT / "tests/test_kumar_component_budget_cpu_20261016.py")
    features, outcomes, provenance_rows = [], [], []
    with threadpool_limits(limits=1):
        for index, subject in enumerate(consumer.DEV + consumer.PRIMARY):
            X, y, trials, saved = fixture(subject, subject in consumer.DEV, 20261016 + index)
            result = budget.run_budget_subject(
                X, y, trials, helpers.synthetic_source_arrays(), saved,
                {"budgets": [4, 8, 12, 16, "full"], "seed": 42, "synthetic": True},
                model_factory=factory)
            features.extend(result["features"])
            outcomes.extend(result["outcomes"])
            provenance_rows.extend(result["provenance"]["rows"])
    paths = {"features": output / "synthetic_full_support_features.csv",
             "outcomes": output / "synthetic_full_support_outcomes.csv",
             "provenance": output / "synthetic_source_support_trial_provenance.json"}
    budget.write_csv(paths["features"], features)
    budget.write_csv(paths["outcomes"], outcomes)
    budget.write_json(paths["provenance"], {"schema_version": 1, "synthetic": True,
                      "software_validation_only": True, "support_order": "chronological",
                      "rows": provenance_rows})
    consumer.run(paths["features"], paths["outcomes"], paths["provenance"],
                 output / "synthetic_consumer_output", synthetic=True)
    assert len(features) == len(outcomes) == len(provenance_rows) == 90
    undefined = [row for row in features if not row["holdout_defined"]]
    assert len(undefined) == 1
    assert all(row["support_cv_lda_gain"] == row["support_cv_full_gain"] == 0 for row in undefined)
    receipt = {"status": "passed_synthetic_producer_csv_consumer_contract",
               "synthetic": True, "software_validation_only": True,
               "real_EEG_or_historical_model_files_read": 0,
               "scientific_results_claimed": False, "participants": 18, "sessions": 5,
               "feature_rows": 90, "outcome_rows": 90, "provenance_rows": 90,
               "undefined_holdout_rows": len(undefined), "numerical_threads": 1,
               "model_factory": "fixed synthetic four-power features plus real shrinkage LDA",
               "producer_sha256": budget.sha256_file(ROOT / "scripts/run_kumar_component_budget_cpu_20261016.py"),
               "consumer_sha256": budget.sha256_file(ROOT / "scripts/analyze_kumar_update_gain_feasibility_20261016.py"),
               "input_sha256": {name: budget.sha256_file(path) for name, path in paths.items()}}
    budget.write_json(output / "synthetic_integration_receipt.json", receipt)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    run(parser.parse_args().output)
