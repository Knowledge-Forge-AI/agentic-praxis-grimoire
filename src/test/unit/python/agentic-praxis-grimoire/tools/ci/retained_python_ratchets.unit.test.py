"""Ratchet inventory changes and checker failures cannot pass as presence checks."""
import json
from pathlib import Path
import subprocess
from tools.ci.retained_python_ratchets import evaluate_ratchets


def fixture(root: Path) -> Path:
    owner = root / "src/agentic_praxis_grimoire/__init__.py"
    owner.parent.mkdir(parents=True)
    owner.write_text("")
    baseline = root / "baseline.json"
    baseline.write_text(json.dumps({"schema": "apg-retained-python-ratchets-v1",
        "paths": [str(owner.relative_to(root))], "quality": {"ruff_f": 0, "mypy": 0}}))
    return baseline


def test_independent_findings_are_not_waived(tmp_path: Path) -> None:
    baseline = fixture(tmp_path)
    calls = []
    def run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 1, "findings", "")
    report, code = evaluate_ratchets(baseline, root=tmp_path, runner=run)
    assert code == 1 and len(calls) == 2
    assert set(report["checks"]) == {"ruff_f", "mypy"}


def test_missing_tool_is_not_a_policy_finding(tmp_path: Path) -> None:
    baseline = fixture(tmp_path)
    def run(*args, **kwargs):
        return subprocess.CompletedProcess(args, 1, "", "No module named mypy")
    assert evaluate_ratchets(baseline, root=tmp_path, runner=run)[1] == 2


def test_owner_addition_and_baseline_inflation_refused(tmp_path: Path) -> None:
    baseline = fixture(tmp_path)
    (tmp_path / "src/agentic_praxis_grimoire/new.py").write_text("")
    assert evaluate_ratchets(baseline, root=tmp_path)[1] == 1
    doc = json.loads(baseline.read_text())
    doc["quality"]["mypy"] = 7
    baseline.write_text(json.dumps(doc))
    assert evaluate_ratchets(baseline, root=tmp_path)[1] == 2
