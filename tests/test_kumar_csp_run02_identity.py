"""Test the exact handoff identity gate; never invoke a scientific consumer."""
import ast
import copy
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
BASELINE = "ad5be8e51e98eebd99ac994a249136e349d2f582"
LAUNCHER = "scripts/run_kumar_csp_signed_score_operation.py"
LOG = "research_logs/kumar_csp_run02_identity_20261015"
SPEC = importlib.util.spec_from_file_location("run02_metadata_test", ROOT / LAUNCHER)
operation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(operation)
HANDOFF = (ROOT / "docs/kumar_csp_run02_recovery_20261015.md").read_text()
GATE_SOURCE = HANDOFF.split("<<'PY'\n", 1)[1].split("\nPY\n", 1)[0]
GATE = {"__name__": "synthetic_identity_gate_test"}
exec(compile(GATE_SOURCE, "reviewed_recovery_handoff", "exec"), GATE)


@pytest.fixture
def recovery(tmp_path):
    binding = operation.read(ROOT / LOG / "recovery_binding.json")
    files = {GATE["BINDING"], LAUNCHER, "scripts/analyze_kumar_csp_signed_score_v1.py",
             "configs/kumar_csp_signed_score_operation_20261015.json"}
    files.update(binding["recovery_of"][key] for key in
                 ("launcher_receipt", "claim", "R2_full_get_receipt"))
    for relative in files:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / relative).read_bytes())
    auth = operation.read(ROOT / LOG / "external_authorization.template.json")
    auth.update(status="parent_reviewed_csp_signed_score_cpu_execution_authorized",
                reviewed_commit="a" * 40, synthetic=True, software_validation_only=True)
    return tmp_path, binding, auth


def check(root, auth, now=None):
    return GATE["recovery_gate"](operation, root, auth,
                                 now=1792045620 if now is None else now)


def test_launcher_changes_exactly_three_identity_literals():
    old = subprocess.check_output(["git", "show", f"{BASELINE}:{LAUNCHER}"], cwd=ROOT, text=True)
    expected = old.replace('DIAGNOSTIC = "kumar-csp-signed-score-development-run01-20261015"',
                           'DIAGNOSTIC = "kumar-csp-signed-score-development-run02-20261015"')
    expected = expected.replace('OUTPUT = "results/kumar_csp_signed_score_20261015/run01"',
                                'OUTPUT = "results/kumar_csp_signed_score_20261015/run02"')
    expected = expected.replace('STATE = "research_logs/kumar_next_source_operations_20261015/csp_signed_score_operation_run01"',
                                'STATE = "research_logs/kumar_next_source_operations_20261015/csp_signed_score_operation_run02"')
    assert (ROOT / LAUNCHER).read_text() == expected
    before = [ast.dump(n) for n in ast.parse(old).body if isinstance(n, ast.FunctionDef)]
    after = [ast.dump(n) for n in ast.parse(expected).body if isinstance(n, ast.FunctionDef)]
    assert before == after


def test_contract_changes_only_identity_command_output_and_self_pin():
    relative = "configs/kumar_csp_signed_score_operation_20261015.json"
    old = json.loads(subprocess.check_output(["git", "show", f"{BASELINE}:{relative}"], cwd=ROOT))
    new = operation.read(ROOT / relative)
    expected = copy.deepcopy(old)
    expected.update(diagnostic_id=operation.DIAGNOSTIC, output=operation.OUTPUT,
                    state_directory=operation.STATE)
    expected["command"][-1] = operation.OUTPUT
    expected["frozen_files"][LAUNCHER] = operation.sha(ROOT / LAUNCHER)
    assert new == expected
    operation.validate_contract(new)


def test_exact_documented_gate_passes_read_only_with_original_claim_present(recovery):
    root, binding, auth = recovery
    before = {p: operation.sha(p) for p in root.rglob("*") if p.is_file()}
    assert check(root, auth) == binding
    assert {p: operation.sha(p) for p in root.rglob("*") if p.is_file()} == before
    assert not (root / operation.STATE).exists()
    assert not (root / operation.OUTPUT).exists()


@pytest.mark.parametrize("key", ["launcher_receipt", "claim", "R2_full_get_receipt"])
def test_modified_original_evidence_rejected(recovery, key):
    root, binding, auth = recovery
    (root / binding["recovery_of"][key]).write_text("SYNTHETIC MODIFICATION")
    with pytest.raises(ValueError, match="Run01 evidence changed"):
        check(root, auth)


@pytest.mark.parametrize("change,pattern", [
    ("link", "must link"), ("deadline", "Original window"),
    ("host", "Recovery host"), ("run01", "Run02 identity"),
    ("template", "Exact CPU-only"), ("contract", "Exact CPU-only"),
])
def test_wrong_authorization_identity_refused(recovery, change, pattern):
    root, _, auth = recovery
    if change == "link":
        auth["recovery_of"]["launcher_receipt_sha256"] = "0" * 64
    elif change == "deadline":
        auth["deadline_unix"] += 3600
        auth["approved_wall_seconds"] += 3600
    elif change == "host":
        auth["container_identity"]["boot_id"] = "different-host"
    elif change == "run01":
        auth["diagnostic_id"] = "kumar-csp-signed-score-development-run01-20261015"
    elif change == "template":
        auth["status"] = "TEMPLATE_ONLY_NOT_AN_EXECUTION_AUTHORIZATION"
    else:
        auth["operation_contract_sha256"] = "0" * 64
    with pytest.raises(ValueError, match=pattern):
        check(root, auth)
    assert not (root / operation.STATE).exists()


@pytest.mark.parametrize("relative", [operation.OUTPUT, operation.STATE])
@pytest.mark.parametrize("kind", ["directory", "dangling_symlink"])
def test_existing_run02_identity_stops_without_cleanup(recovery, relative, kind):
    root, _, auth = recovery
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if kind == "directory":
        path.mkdir()
    else:
        path.symlink_to("absent-preserved-target")
    with pytest.raises(ValueError, match="Run02 already"):
        check(root, auth)
    assert path.exists() or path.is_symlink()


def test_original_deadline_cleanup_margin_cannot_be_renewed(recovery):
    root, binding, auth = recovery
    with pytest.raises(ValueError, match="absolute authorization window"):
        check(root, auth, now=binding["deadline_unix"] - 30)
