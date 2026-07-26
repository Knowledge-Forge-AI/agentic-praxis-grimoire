"""Unit tests for APG's pytest, coverage, and mirror-policy runner."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys

import pytest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import apg_test  # noqa: E402


def write_inventory(root: Path, value: object) -> None:
    path = root / apg_test.INVENTORY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def minimal_inventory() -> dict[str, object]:
    return {
        "schema_version": 1,
        "coverage_sources": [
            {
                "path": "libexec/tool.py",
                "rationale": "unit policy owner",
                "suites": ["unit", "integration", "combined"],
            }
        ],
        "excluded_python_launchers": [
            {"path": "bin/tool", "reason": "thin import and exit adapter"}
        ],
        "tests": [
            {
                "owner": "libexec/tool.py",
                "path": (
                    "src/test/unit/python/agentic-praxis-grimoire/"
                    "libexec/tool.unit.test.py"
                ),
                "suite": "unit",
            }
        ],
    }


def materialize_inventory_tree(root: Path) -> None:
    value = minimal_inventory()
    for relative in (
        "libexec/tool.py",
        "src/test/unit/python/agentic-praxis-grimoire/libexec/tool.unit.test.py",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("value = 1\n", encoding="utf-8")
    launcher = root / "bin/tool"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    write_inventory(root, value)


def test_exact_threshold_arithmetic_does_not_use_display_rounding() -> None:
    apg_test.enforce_threshold(apg_test.CoverageCounts(4, 5, 8, 10), 80, 80)
    with pytest.raises(apg_test.ToolError, match="statement coverage"):
        apg_test.enforce_threshold(apg_test.CoverageCounts(799, 1000, 8, 10), 80, 80)
    with pytest.raises(apg_test.ToolError, match="branch coverage"):
        apg_test.enforce_threshold(apg_test.CoverageCounts(8, 10, 799, 1000), 80, 80)


def test_coverage_counts_require_exact_sources_and_measurable_branches() -> None:
    report = {
        "files": {
            "libexec/a.py": {
                "summary": {
                    "covered_lines": 8,
                    "num_statements": 10,
                    "covered_branches": 4,
                    "num_branches": 5,
                }
            }
        }
    }
    assert apg_test.coverage_counts(report, ["libexec/a.py"]) == apg_test.CoverageCounts(
        8, 10, 4, 5
    )
    with pytest.raises(apg_test.ToolError, match="omits required source"):
        apg_test.coverage_counts(report, ["libexec/missing.py"])
    with pytest.raises(apg_test.ToolError, match="zero statements or branches"):
        apg_test.coverage_counts(
            {"files": {"libexec/a.py": {"summary": {
                "covered_lines": 1, "num_statements": 1,
                "covered_branches": 0, "num_branches": 0,
            }}}},
            ["libexec/a.py"],
        )


@pytest.mark.parametrize(
    "field,value,message",
    [
        ("covered_lines", True, "malformed"),
        ("covered_lines", 8.0, "malformed"),
        ("covered_lines", "8", "malformed"),
        ("covered_lines", -1, "impossible"),
        ("covered_lines", 11, "impossible"),
        ("num_statements", -1, "impossible"),
        ("covered_branches", -1, "impossible"),
        ("covered_branches", 6, "impossible"),
        ("num_branches", -1, "impossible"),
    ],
)
def test_coverage_counts_reject_malformed_and_impossible_values(
    field: str, value: object, message: str
) -> None:
    summary: dict[str, object] = {
        "covered_lines": 8,
        "num_statements": 10,
        "covered_branches": 4,
        "num_branches": 5,
    }
    summary[field] = value
    with pytest.raises(apg_test.ToolError, match=message):
        apg_test.coverage_counts(
            {"files": {"libexec/a.py": {"summary": summary}}},
            ["libexec/a.py"],
        )


def test_coverage_report_rejects_missing_and_foreign_sources() -> None:
    apg_test.validate_coverage_report(
        {"files": {"libexec/a.py": {}}}, {"libexec/a.py"}
    )
    with pytest.raises(apg_test.ToolError, match="missing=.*b.py"):
        apg_test.validate_coverage_report(
            {"files": {"libexec/a.py": {}}},
            {"libexec/a.py", "libexec/b.py"},
        )
    with pytest.raises(apg_test.ToolError, match="foreign=.*outside.py"):
        apg_test.validate_coverage_report(
            {"files": {"libexec/a.py": {}, "outside.py": {}}},
            {"libexec/a.py"},
        )


def test_strict_inventory_rejects_duplicate_and_unknown_data(tmp_path: Path) -> None:
    write_inventory(tmp_path, minimal_inventory())
    loaded = apg_test.load_inventory(tmp_path)
    assert loaded.tests

    inventory_path = tmp_path / apg_test.INVENTORY_PATH
    inventory_path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
    with pytest.raises(apg_test.ToolError, match="duplicate key"):
        apg_test.load_inventory(tmp_path)

    value = minimal_inventory()
    value["unexpected"] = True
    write_inventory(tmp_path, value)
    with pytest.raises(apg_test.ToolError, match="top-level fields"):
        apg_test.load_inventory(tmp_path)


def test_inventory_rejects_invalid_source_launcher_and_test_entries(tmp_path: Path) -> None:
    cases: list[tuple[dict[str, object], str]] = []

    value = minimal_inventory()
    value["schema_version"] = 2
    cases.append((value, "schema_version"))

    value = minimal_inventory()
    value["coverage_sources"] = []
    cases.append((value, "nonempty array"))

    value = minimal_inventory()
    value["coverage_sources"][0]["suites"] = ["unknown"]
    cases.append((value, "suites are invalid"))

    value = minimal_inventory()
    value["coverage_sources"].append(value["coverage_sources"][0].copy())
    cases.append((value, "duplicate coverage source"))

    value = minimal_inventory()
    value["excluded_python_launchers"][0]["reason"] = ""
    cases.append((value, "lacks a rationale"))

    value = minimal_inventory()
    value["tests"][0]["suite"] = "system"
    cases.append((value, "test suite is invalid"))

    value = minimal_inventory()
    value["tests"].append(value["tests"][0].copy())
    cases.append((value, "duplicate mirrored test"))

    value = minimal_inventory()
    value["coverage_sources"][0]["extra"] = True
    cases.append((value, "source entry"))

    value = minimal_inventory()
    value["excluded_python_launchers"] = "invalid"
    cases.append((value, "must be an array"))

    value = minimal_inventory()
    value["excluded_python_launchers"][0]["extra"] = True
    cases.append((value, "launcher entry"))

    value = minimal_inventory()
    value["tests"] = []
    cases.append((value, "nonempty array"))

    value = minimal_inventory()
    value["tests"][0]["extra"] = True
    cases.append((value, "test entry"))

    for candidate, message in cases:
        write_inventory(tmp_path, candidate)
        with pytest.raises(apg_test.ToolError, match=message):
            apg_test.load_inventory(tmp_path)


def test_inventory_detects_missing_stale_wrong_mirror_and_legacy_tests(
    tmp_path: Path,
) -> None:
    materialize_inventory_tree(tmp_path)
    inventory = apg_test.load_inventory(tmp_path)
    apg_test.validate_inventory(tmp_path, inventory)

    (tmp_path / "libexec/extra.py").write_text("value = 2\n", encoding="utf-8")
    with pytest.raises(apg_test.ToolError, match="coverage source inventory differs"):
        apg_test.validate_inventory(tmp_path, inventory)
    (tmp_path / "libexec/extra.py").unlink()

    value = minimal_inventory()
    value["tests"][0]["path"] = (
        "src/test/unit/python/agentic-praxis-grimoire/libexec/wrong.unit.test.py"
    )
    wrong = tmp_path / value["tests"][0]["path"]
    wrong.write_text("value = 1\n", encoding="utf-8")
    original = tmp_path / minimal_inventory()["tests"][0]["path"]
    original.unlink()
    write_inventory(tmp_path, value)
    with pytest.raises(apg_test.ToolError, match="disagrees with owner"):
        apg_test.validate_inventory(tmp_path, apg_test.load_inventory(tmp_path))

    legacy = tmp_path / "src/test/unit/python/legacy.test.py"
    legacy.write_text("value = 1\n", encoding="utf-8")
    with pytest.raises(apg_test.ToolError, match="stale legacy"):
        apg_test.validate_inventory(tmp_path, apg_test.load_inventory(tmp_path))


def test_dependency_versions_are_exact(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(apg_test.metadata, "version", lambda name: apg_test.EXPECTED_VERSIONS[name])
    assert apg_test.dependency_versions() == apg_test.EXPECTED_VERSIONS
    monkeypatch.setattr(apg_test.metadata, "version", lambda _name: "0")
    with pytest.raises(apg_test.ToolError, match="version mismatch"):
        apg_test.dependency_versions()
    monkeypatch.setattr(
        apg_test.metadata,
        "version",
        lambda _name: (_ for _ in ()).throw(apg_test.metadata.PackageNotFoundError()),
    )
    with pytest.raises(apg_test.ToolError, match="not installed"):
        apg_test.dependency_versions()


@pytest.mark.parametrize("value", ["", "/absolute", "../escape", "a/../b", "a//b"])
def test_inventory_paths_must_be_normalized_relative(value: str) -> None:
    with pytest.raises(apg_test.ToolError, match="normalized relative path|nonempty"):
        apg_test._relative_path(value, "test")


def test_artifact_directory_is_fresh_and_rejects_unsafe_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APG_TEST_ARTIFACT_ROOT", os.fspath(tmp_path))
    first = apg_test._artifact_directory(REPOSITORY_ROOT)
    second = apg_test._artifact_directory(REPOSITORY_ROOT)
    assert first.path != second.path
    apg_test._cleanup_artifacts(first)
    apg_test._cleanup_artifacts(second)
    monkeypatch.setenv("APG_TEST_ARTIFACT_ROOT", "relative")
    with pytest.raises(apg_test.ToolError, match="absolute real directory"):
        apg_test._artifact_directory(REPOSITORY_ROOT)


def test_pytest_execution_rejects_failure_missing_and_parallel_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(apg_test, "validate_worker_manifest", lambda *_args: None)
    monkeypatch.setattr(apg_test, "validate_child_manifest", lambda *_args: None)
    monkeypatch.setattr(apg_test, "_coverage_contexts", lambda _path: set())
    class Result:
        returncode = 0

    def successful(*_args: object, **kwargs: object) -> Result:
        environment = kwargs["env"]
        data = Path(environment["COVERAGE_FILE"])
        data.write_bytes(b"coverage")
        data.with_suffix(".json").write_text('{"files": {}}', encoding="utf-8")
        assert environment["PATH"].split(os.pathsep)[0] == os.fspath(Path(sys.executable).parent)
        assert environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"
        return Result()
    monkeypatch.setattr(apg_test.subprocess, "run", successful)
    data, report = apg_test._run_pytest(REPOSITORY_ROOT, "unit", 2, tmp_path)
    assert data.is_file() and report == {"files": {}}

    class Failed:
        returncode = 5

    monkeypatch.setattr(apg_test.subprocess, "run", lambda *_args, **_kwargs: Failed())
    failure = tmp_path / "failure"
    failure.mkdir()
    with pytest.raises(apg_test.ToolError, match="status 5"):
        apg_test._run_pytest(REPOSITORY_ROOT, "unit", 2, failure)

    incomplete = tmp_path / "incomplete"
    incomplete.mkdir()
    monkeypatch.setattr(apg_test.subprocess, "run", lambda *_args, **_kwargs: Result())
    with pytest.raises(apg_test.ToolError, match="output is incomplete"):
        apg_test._run_pytest(REPOSITORY_ROOT, "unit", 2, incomplete)
    parallel = tmp_path / "parallel"
    parallel.mkdir()

    def leaves_parallel(*_args: object, **kwargs: object) -> Result:
        data = Path(kwargs["env"]["COVERAGE_FILE"])
        data.write_bytes(b"coverage")
        data.with_suffix(".json").write_text('{"files": {}}', encoding="utf-8")
        data.with_name(data.name + ".worker").write_bytes(b"stale")
        return Result()

    monkeypatch.setattr(apg_test.subprocess, "run", leaves_parallel)
    with pytest.raises(apg_test.ToolError, match="unexpected data"):
        apg_test._run_pytest(REPOSITORY_ROOT, "unit", 2, parallel)

    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (foreign / "foreign.coverage").write_bytes(b"foreign")
    with pytest.raises(apg_test.ToolError, match="contains unexpected data"):
        apg_test._run_pytest(REPOSITORY_ROOT, "unit", 2, foreign)


def test_pytest_execution_rejects_malformed_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(apg_test, "validate_worker_manifest", lambda *_args: None)
    monkeypatch.setattr(apg_test, "validate_child_manifest", lambda *_args: None)
    monkeypatch.setattr(apg_test, "_coverage_contexts", lambda _path: set())
    class Result:
        returncode = 0

    def malformed(*_args: object, **kwargs: object) -> Result:
        data = Path(kwargs["env"]["COVERAGE_FILE"])
        data.write_bytes(b"coverage")
        data.with_suffix(".json").write_text("{", encoding="utf-8")
        return Result()

    monkeypatch.setattr(apg_test.subprocess, "run", malformed)
    with pytest.raises(apg_test.ToolError, match="JSON is unreadable"):
        apg_test._run_pytest(REPOSITORY_ROOT, "unit", 2, tmp_path)


def test_pytest_command_disables_worker_restart_and_uses_selected_root(tmp_path: Path) -> None:
    command = apg_test._pytest_command(
        tmp_path,
        "integration",
        8,
        tmp_path / "data",
        tmp_path / "report.json",
        "run-id",
    )
    assert command[command.index("-n") + 1] == "8"
    assert "--max-worker-restart=0" in command
    assert "xdist.plugin" in command
    assert "pytest_cov.plugin" in command
    assert command[-1].endswith("src/test/int/python/agentic-praxis-grimoire")


def test_mirror_path_mapping_handles_markdown_and_extensionless_owners() -> None:
    assert apg_test._expected_test_path("skills/example/SKILL.md", "unit").endswith(
        "skills/example/SKILL.unit.test.py"
    )
    assert apg_test._expected_test_path("bin/example", "integration").endswith(
        "bin/example.int.test.py"
    )


def test_run_enforces_each_suite_then_combined_union(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inventory = apg_test.Inventory(
        {"libexec/tool.py": ("unit", "integration", "combined")}, {}, {}
    )
    monkeypatch.setattr(apg_test, "load_inventory", lambda _root: inventory)
    monkeypatch.setattr(apg_test, "validate_inventory", lambda _root, _inventory: None)
    monkeypatch.setattr(apg_test, "dependency_versions", lambda: {})
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir()
    metadata = artifact_root.stat()
    ownership = apg_test.ArtifactDirectory(
        artifact_root, metadata.st_dev, metadata.st_ino
    )
    monkeypatch.setattr(apg_test, "_artifact_directory", lambda _root: ownership)
    report = {"files": {"libexec/tool.py": {"summary": {
        "covered_lines": 9, "num_statements": 10,
        "covered_branches": 9, "num_branches": 10,
    }}}}
    calls: list[str] = []

    def run_suite(
        _root: Path, suite: str, workers: int, _artifacts: Path, **_kwargs: object
    ):
        calls.append(f"{suite}:{workers}")
        return artifact_root / suite / f"{suite}.coverage", report

    monkeypatch.setattr(apg_test, "_run_pytest", run_suite)
    monkeypatch.setattr(apg_test, "_combine_coverage", lambda *_args: report)
    apg_test.run("combined", 8, tmp_path)
    assert calls == ["unit:8", "integration:8"]
    with pytest.raises(apg_test.ToolError, match="workers"):
        apg_test.run("unit", 0, tmp_path)


def test_combined_reports_both_components_and_union_after_a_component_gate_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inventory = apg_test.Inventory(
        {"libexec/tool.py": ("unit", "integration", "combined")}, {}, {}
    )
    monkeypatch.setattr(apg_test, "load_inventory", lambda _root: inventory)
    monkeypatch.setattr(apg_test, "validate_inventory", lambda _root, _inventory: None)
    monkeypatch.setattr(apg_test, "dependency_versions", lambda: {})
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir()
    metadata = artifact_root.stat()
    ownership = apg_test.ArtifactDirectory(
        artifact_root, metadata.st_dev, metadata.st_ino
    )
    monkeypatch.setattr(apg_test, "_artifact_directory", lambda _root: ownership)
    calls: list[str] = []

    def report(covered: int) -> dict[str, object]:
        return {"files": {"libexec/tool.py": {"summary": {
            "covered_lines": covered, "num_statements": 10,
            "covered_branches": covered, "num_branches": 10,
        }}}}

    def run_suite(
        _root: Path, suite: str, _workers: int, _artifacts: Path, **_kwargs: object
    ):
        calls.append(suite)
        return artifact_root / suite / f"{suite}.coverage", report(
            5 if suite == "unit" else 9
        )

    monkeypatch.setattr(apg_test, "_run_pytest", run_suite)
    def malformed_union(*_args: object) -> dict[str, object]:
        calls.append("combined")
        raise apg_test.ToolError("union malformed")

    monkeypatch.setattr(apg_test, "_combine_coverage", malformed_union)

    with pytest.raises(
        apg_test.ToolError,
        match="unit.*statement coverage.*combined.*union malformed",
    ):
        apg_test.run("combined", 8, tmp_path)
    assert calls == ["unit", "integration", "combined"]


def test_combined_component_failure_artifacts_are_isolated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inventory = apg_test.Inventory(
        {"libexec/tool.py": ("unit", "integration", "combined")}, {}, {}
    )
    monkeypatch.setattr(apg_test, "load_inventory", lambda _root: inventory)
    monkeypatch.setattr(apg_test, "validate_inventory", lambda _root, _inventory: None)
    monkeypatch.setattr(apg_test, "dependency_versions", lambda: {})
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir()
    metadata = artifact_root.stat()
    ownership = apg_test.ArtifactDirectory(
        artifact_root, metadata.st_dev, metadata.st_ino
    )
    monkeypatch.setattr(apg_test, "_artifact_directory", lambda _root: ownership)
    calls: list[str] = []

    def fail_component(
        _root: Path,
        suite: str,
        _workers: int,
        component_artifacts: Path,
        **_kwargs: object,
    ) -> tuple[Path, dict[str, object]]:
        calls.append(suite)
        assert component_artifacts == artifact_root / suite
        assert not any(component_artifacts.iterdir())
        (component_artifacts / f"{suite}-failure-evidence").write_text(
            "retained\n", encoding="utf-8"
        )
        raise apg_test.ToolError(f"{suite} failed")

    monkeypatch.setattr(apg_test, "_run_pytest", fail_component)
    with pytest.raises(
        apg_test.ToolError,
        match="unit: unit failed; integration: integration failed",
    ):
        apg_test.run("combined", 2, tmp_path, keep_artifacts_on_failure=True)
    assert calls == ["unit", "integration"]
    assert (artifact_root / "unit/unit-failure-evidence").is_file()
    assert (artifact_root / "integration/integration-failure-evidence").is_file()


def test_worker_manifest_requires_exact_workers_collections_results_and_clean_down(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "workers.jsonl"
    node_ids = ["root/test_example.py::test_one"]
    events = []
    for worker in ("gw0", "gw1"):
        events.extend(
            [
                {"event": "worker-start", "run_id": "run", "suite": "unit", "worker": worker},
                {"event": "collection", "run_id": "run", "suite": "unit", "worker": worker, "node_ids": node_ids},
                {"event": "worker-complete", "run_id": "run", "suite": "unit", "worker": worker, "exitstatus": 0},
                {"event": "node-down", "run_id": "run", "suite": "unit", "worker": worker, "error": False, "exitstatus": 0},
            ]
        )
    events.append(
        {"event": "test-result", "run_id": "run", "suite": "unit", "nodeid": node_ids[0], "outcome": "passed"}
    )
    events.append(
        {"event": "controller-complete", "run_id": "run", "suite": "unit", "exitstatus": 0}
    )
    manifest.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")
    apg_test.validate_worker_manifest(manifest, "run", "unit", 2, "root")

    events.pop(-2)
    manifest.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")
    with pytest.raises(apg_test.ToolError, match="terminal result"):
        apg_test.validate_worker_manifest(manifest, "run", "unit", 2, "root")


def test_required_child_manifest_needs_completion_and_coverage_context(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "children.jsonl"
    context = "apg-child:run:child"
    events = [
        {"event": "child-start", "run_id": "run", "suite": "unit", "process_id": "child", "context": context},
        {"event": "child-complete", "run_id": "run", "suite": "unit", "process_id": "child", "context": context},
    ]
    manifest.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")
    apg_test.validate_child_manifest(manifest, "run", "unit", {context})
    with pytest.raises(apg_test.ToolError, match="coverage contribution"):
        apg_test.validate_child_manifest(manifest, "run", "unit", set())
    with pytest.raises(apg_test.ToolError, match="child coverage contribution differs"):
        apg_test.validate_child_manifest(
            manifest,
            "run",
            "unit",
            {context, "apg-child:foreign:stale"},
        )

    manifest.write_text("", encoding="utf-8")
    with pytest.raises(apg_test.ToolError, match="child coverage contribution differs"):
        apg_test.validate_child_manifest(
            manifest,
            "run",
            "unit",
            {"apg-child:foreign:stale"},
        )


def test_main_maps_combined_name_and_returns_bounded_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[tuple[str, int]] = []

    def successful(
        suite: str, workers: int, _root: Path, **_kwargs: object
    ) -> None:
        observed.append((suite, workers))

    monkeypatch.setattr(apg_test, "run", successful)
    assert apg_test.main(["unit-integration"]) == 0
    assert observed == [("combined", 8)]

    def failing(*_args: object, **_kwargs: object) -> None:
        raise apg_test.ToolError("bounded")

    monkeypatch.setattr(apg_test, "run", failing)
    assert apg_test.main(["unit"]) == 1
