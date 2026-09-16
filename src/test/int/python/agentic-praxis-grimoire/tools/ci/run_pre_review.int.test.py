"""Integration tests for end-to-end pre-review static analysis execution."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from tools.ci.pre_review_records import Check
from tools.ci.run_pre_review import execute_all, main


def test_execute_all_clean_run(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "evidence"
    c1 = Check("check-echo-1", ("echo", "success-1"))
    c2 = Check("check-echo-2", ("echo", "success-2"))
    selected = (c1, c2)

    results = execute_all(selected, evidence_dir)
    assert len(results) == 2
    assert all(r.status == "passed" for r in results)
    assert all(r.classification == "passed" for r in results)

    # Check that log files were created
    assert (evidence_dir / "check-echo-1.log").is_file()
    assert (evidence_dir / "check-echo-2.log").is_file()


def test_execute_all_segregates_tool_failure_from_policy_finding(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "evidence"
    # c1: policy finding (exit 1 on ruff)
    c1 = Check("ruff", (sys.executable, "-c", "import sys; sys.exit(1)"), python_owned=True)
    # c2: tool failure (exit 127 command not found)
    c2 = Check("missing-tool", ("nonexistent_command_xyz_123",))

    results = execute_all((c1, c2), evidence_dir)
    assert len(results) == 2

    res_policy = next(r for r in results if r.name == "ruff")
    assert res_policy.status == "failed"
    assert res_policy.classification == "policy-finding"

    res_tool = next(r for r in results if r.name == "missing-tool")
    assert res_tool.status == "failed"
    assert res_tool.classification == "tool-failure"


def test_main_cli_execution_with_single_check(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "evidence"
    code = main(["--evidence-dir", str(evidence_dir), "--check", "ci-topology"])
    assert code == 0
    assert (evidence_dir / "manifest.json").is_file()
    assert (evidence_dir / "results.json").is_file()

    results_doc = json.loads((evidence_dir / "results.json").read_text(encoding="utf-8"))
    assert results_doc.get("schema") == "apg-pre-review-result-v1"
    assert len(results_doc["results"]) == 1
    assert results_doc["results"][0]["name"] == "ci-topology"
    assert results_doc["results"][0]["status"] == "passed"


def test_malformed_tool_result_does_not_prevent_later_independent_check(tmp_path: Path) -> None:
    malformed = Check("retained-python-ratchets", (sys.executable, "-c", "print(123)"), policy="retained-python-ratchets")
    later = Check("later-check", (sys.executable, "-c", "print(\"still ran\")"))
    results = execute_all((malformed, later), tmp_path / "evidence", scratch_dir=tmp_path / "scratch")
    assert [(item.name, item.classification) for item in results] == [
        ("retained-python-ratchets", "tool-failure"),
        ("later-check", "passed"),
    ]
    assert "still ran" in (tmp_path / "evidence/later-check.log").read_text()


def test_tool_caches_are_bound_to_disposable_scratch(tmp_path: Path) -> None:
    check = Check("cache-observer", (sys.executable, "-c", "import json,os; print(json.dumps({key:os.environ[key] for key in (\"RUFF_CACHE_DIR\",\"MYPY_CACHE_DIR\",\"PYTHONPYCACHEPREFIX\")}))"))
    scratch = tmp_path / "scratch"
    result = execute_all((check,), tmp_path / "evidence", scratch_dir=scratch)
    assert result[0].status == "passed"
    log = (tmp_path / "evidence/cache-observer.log").read_text()
    assert '"RUFF_CACHE_DIR": "<private-path>/ruff-cache"' in log
    assert '"MYPY_CACHE_DIR": "<private-path>/mypy-cache"' in log
    assert '"PYTHONPYCACHEPREFIX": "<private-path>/pycache"' in log
