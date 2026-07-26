"""APG-owned pytest, xdist, mirror, and exact coverage runner."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from importlib import metadata
import json
import os
from pathlib import Path, PurePosixPath
import secrets
import shutil
import subprocess
import sys
import tempfile
from typing import NoReturn, Sequence


COMMAND = "apg-test"
INVENTORY_PATH = Path("testing/apg-test-inventory.json")
UNIT_ROOT = Path("src/test/unit/python/agentic-praxis-grimoire")
INTEGRATION_ROOT = Path("src/test/int/python/agentic-praxis-grimoire")
EXPECTED_VERSIONS = {
    "coverage": "7.15.2",
    "pytest": "9.1.1",
    "pytest-cov": "7.1.0",
    "pytest-xdist": "3.8.0",
}
THRESHOLDS = {
    "unit": (80, 80),
    "integration": (80, 80),
    "combined": (85, 85),
}


class ToolError(Exception):
    """A bounded invocation, inventory, test, or coverage failure."""


@dataclass(frozen=True)
class CoverageCounts:
    """Exact aggregate statement and branch counts."""

    statements_covered: int
    statements_total: int
    branches_covered: int
    branches_total: int


@dataclass(frozen=True)
class Inventory:
    """Validated source, launcher, and mirrored-test ownership."""

    coverage_sources: dict[str, tuple[str, ...]]
    excluded_launchers: dict[str, str]
    tests: dict[str, tuple[str, str]]


@dataclass(frozen=True)
class ComponentResult:
    """One test component with valid completeness and coverage data."""

    data_file: Path
    report: dict[str, object]
    counts: CoverageCounts


@dataclass(frozen=True)
class ArtifactDirectory:
    """One invocation-owned artifact directory and its creation identity."""

    path: Path
    device: int
    inode: int


def fail(message: str) -> NoReturn:
    raise ToolError(message)


def _unique_object(pairs: Sequence[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key: {key}")
        result[key] = value
    return result


def _relative_path(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        fail(f"inventory {field} must be a nonempty string")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) != value:
        fail(f"inventory {field} is not a normalized relative path: {value}")
    return value


def load_inventory(root: Path) -> Inventory:
    """Load the strict inventory without accepting unknown or duplicate data."""
    try:
        raw = (root / INVENTORY_PATH).read_text(encoding="utf-8")
        value = json.loads(raw, object_pairs_hook=_unique_object)
    except (OSError, UnicodeError, ValueError) as error:
        fail(f"test inventory is unreadable or malformed: {error}")
    if not isinstance(value, dict) or set(value) != {
        "coverage_sources",
        "excluded_python_launchers",
        "schema_version",
        "tests",
    }:
        fail("test inventory has unknown or missing top-level fields")
    if value["schema_version"] != 1:
        fail("test inventory schema_version must be 1")

    coverage_sources: dict[str, tuple[str, ...]] = {}
    source_entries = value["coverage_sources"]
    if not isinstance(source_entries, list) or not source_entries:
        fail("test inventory coverage_sources must be a nonempty array")
    for entry in source_entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "rationale", "suites"}:
            fail("coverage source entry has unknown or missing fields")
        path = _relative_path(entry["path"], "source path")
        rationale = entry["rationale"]
        if not isinstance(rationale, str) or not rationale.strip():
            fail(f"coverage source rationale is invalid: {path}")
        suites = entry["suites"]
        if (
            not isinstance(suites, list)
            or suites != ["unit", "integration", "combined"]
        ):
            fail(f"coverage source suites are invalid: {path}")
        if path in coverage_sources:
            fail(f"duplicate coverage source: {path}")
        coverage_sources[path] = tuple(suites)

    excluded_launchers: dict[str, str] = {}
    launcher_entries = value["excluded_python_launchers"]
    if not isinstance(launcher_entries, list):
        fail("excluded_python_launchers must be an array")
    for entry in launcher_entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "reason"}:
            fail("launcher entry has unknown or missing fields")
        path = _relative_path(entry["path"], "launcher path")
        reason = entry["reason"]
        if not isinstance(reason, str) or not reason.strip():
            fail(f"launcher exclusion lacks a rationale: {path}")
        if path in excluded_launchers:
            fail(f"duplicate launcher exclusion: {path}")
        excluded_launchers[path] = reason

    tests: dict[str, tuple[str, str]] = {}
    test_entries = value["tests"]
    if not isinstance(test_entries, list) or not test_entries:
        fail("test inventory tests must be a nonempty array")
    for entry in test_entries:
        if not isinstance(entry, dict) or set(entry) != {"owner", "path", "suite"}:
            fail("test entry has unknown or missing fields")
        path = _relative_path(entry["path"], "test path")
        owner = _relative_path(entry["owner"], "production owner")
        suite = entry["suite"]
        if suite not in {"unit", "integration"}:
            fail(f"test suite is invalid: {path}")
        if path in tests:
            fail(f"duplicate mirrored test: {path}")
        tests[path] = (owner, suite)
    return Inventory(coverage_sources, excluded_launchers, tests)


def _expected_test_path(owner: str, suite: str) -> str:
    mirror = UNIT_ROOT if suite == "unit" else INTEGRATION_ROOT
    source = PurePosixPath(owner)
    name = source.name
    for suffix in (".py", ".md"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    kind = "unit" if suite == "unit" else "int"
    return str(PurePosixPath(mirror.as_posix()) / source.parent / f"{name}.{kind}.test.py")


def validate_inventory(root: Path, inventory: Inventory) -> None:
    """Reject stale, omitted, duplicate, or incorrectly mirrored ownership."""
    actual_sources = {
        path.relative_to(root).as_posix()
        for path in (root / "libexec").rglob("*.py")
        if "__pycache__" not in path.parts
    }
    declared_sources = set(inventory.coverage_sources)
    if actual_sources != declared_sources:
        missing = sorted(actual_sources - declared_sources)
        stale = sorted(declared_sources - actual_sources)
        fail(f"coverage source inventory differs: missing={missing}; stale={stale}")
    actual_launchers = set()
    for path in (root / "bin").iterdir():
        if path.is_file() and path.read_bytes().startswith(b"#!/usr/bin/env python3\n"):
            actual_launchers.add(path.relative_to(root).as_posix())
    if actual_launchers != set(inventory.excluded_launchers):
        fail("Python launcher exclusions differ from the executable inventory")

    actual_tests = {
        path.relative_to(root).as_posix()
        for base in (root / UNIT_ROOT, root / INTEGRATION_ROOT)
        for path in base.rglob("*.test.py")
    }
    if actual_tests != set(inventory.tests):
        missing = sorted(actual_tests - set(inventory.tests))
        stale = sorted(set(inventory.tests) - actual_tests)
        fail(f"mirrored test inventory differs: missing={missing}; stale={stale}")
    legacy = sorted(
        path.relative_to(root).as_posix()
        for base in (root / "src/test/unit/python", root / "src/test/int/python")
        for path in base.glob("*.py")
    )
    if legacy:
        fail(f"stale legacy Python test path remains: {legacy}")
    for path, (owner, suite) in inventory.tests.items():
        if not (root / owner).is_file():
            fail(f"mirrored test production owner is missing: {owner}")
        expected = _expected_test_path(owner, suite)
        if path != expected:
            fail(f"mirrored test path disagrees with owner: {path}; expected {expected}")


def dependency_versions() -> dict[str, str]:
    """Require the exact reviewed test stack."""
    versions: dict[str, str] = {}
    for distribution, expected in EXPECTED_VERSIONS.items():
        try:
            actual = metadata.version(distribution)
        except metadata.PackageNotFoundError:
            fail(f"required test dependency is not installed: {distribution}=={expected}")
        if actual != expected:
            fail(
                f"test dependency version mismatch: {distribution}=={actual}; "
                f"expected {expected}"
            )
        versions[distribution] = actual
    return versions


def record_worker_coverage_sentinel() -> None:
    """Provide one maintained-source event for an xdist worker context."""

    return None


def coverage_counts(report: dict[str, object], paths: Sequence[str]) -> CoverageCounts:
    """Aggregate exact counts for a reviewed source set."""
    files = report.get("files")
    if not isinstance(files, dict):
        fail("coverage JSON has no files object")
    statement_covered = statement_total = branch_covered = branch_total = 0
    for path in paths:
        entry = files.get(path)
        if not isinstance(entry, dict) or not isinstance(entry.get("summary"), dict):
            fail(f"coverage data omits required source: {path}")
        summary = entry["summary"]
        try:
            counts = tuple(
                summary[field]
                for field in (
                    "covered_lines",
                    "num_statements",
                    "covered_branches",
                    "num_branches",
                )
            )
        except KeyError:
            fail(f"coverage counts are malformed for source: {path}")
        if any(not isinstance(count, int) or isinstance(count, bool) for count in counts):
            fail(f"coverage counts are malformed for source: {path}")
        covered_lines, num_statements, covered_branches, num_branches = counts
        if (
            covered_lines < 0
            or num_statements < 0
            or covered_lines > num_statements
            or covered_branches < 0
            or num_branches < 0
            or covered_branches > num_branches
        ):
            fail(f"coverage counts are impossible for source: {path}")
        statement_covered += covered_lines
        statement_total += num_statements
        branch_covered += covered_branches
        branch_total += num_branches
    if statement_total <= 0 or branch_total <= 0:
        fail("coverage source target has zero statements or branches")
    return CoverageCounts(
        statement_covered,
        statement_total,
        branch_covered,
        branch_total,
    )


def validate_coverage_report(report: dict[str, object], declared: set[str]) -> None:
    """Reject missing, foreign, or non-file coverage measurements."""
    files = report.get("files")
    if not isinstance(files, dict):
        fail("coverage JSON has no files object")
    measured = set(files)
    if measured != declared:
        missing = sorted(declared - measured)
        foreign = sorted(measured - declared)
        fail(f"coverage source set differs: missing={missing}; foreign={foreign}")


def enforce_threshold(counts: CoverageCounts, statement: int, branch: int) -> None:
    """Enforce exact integer ratios without display rounding."""
    if counts.statements_covered * 100 < statement * counts.statements_total:
        fail(
            "statement coverage gate failed: "
            f"{counts.statements_covered}/{counts.statements_total} < {statement}%"
        )
    if counts.branches_covered * 100 < branch * counts.branches_total:
        fail(
            "branch coverage gate failed: "
            f"{counts.branches_covered}/{counts.branches_total} < {branch}%"
        )


def _artifact_directory(root: Path) -> ArtifactDirectory:
    configured = os.environ.get("APG_TEST_ARTIFACT_ROOT")
    if configured:
        parent = Path(configured)
        if not parent.is_absolute() or not parent.is_dir() or parent.is_symlink():
            fail("APG_TEST_ARTIFACT_ROOT must be an absolute real directory")
    else:
        parent = Path(tempfile.gettempdir())
    artifact = Path(tempfile.mkdtemp(prefix="apg-test-", dir=parent))
    artifact.chmod(0o700)
    metadata = artifact.stat()
    return ArtifactDirectory(artifact, metadata.st_dev, metadata.st_ino)


def _cleanup_artifacts(ownership: ArtifactDirectory) -> None:
    """Remove only a private invocation-owned artifact directory."""
    path = ownership.path
    if not path.name.startswith("apg-test-") or path.is_symlink() or not path.is_dir():
        return
    status = path.stat()
    if (status.st_dev, status.st_ino) != (ownership.device, ownership.inode):
        fail("artifact directory identity changed before cleanup")
    if hasattr(os, "getuid"):
        if status.st_uid != os.getuid() or status.st_mode & 0o077:
            fail("artifact directory ownership or mode changed before cleanup")
    shutil.rmtree(path)


def _read_manifest(path: Path, run_id: str, suite: str) -> list[dict[str, object]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        fail(f"run manifest is unreadable: {path.name}: {error}")
    events: list[dict[str, object]] = []
    for line in lines:
        try:
            event = json.loads(line, object_pairs_hook=_unique_object)
        except (ValueError, json.JSONDecodeError) as error:
            fail(f"run manifest is malformed: {path.name}: {error}")
        if not isinstance(event, dict):
            fail(f"run manifest event is not an object: {path.name}")
        if event.get("run_id") != run_id or event.get("suite") != suite:
            fail(f"run manifest contains foreign or stale evidence: {path.name}")
        events.append(event)
    return events


def validate_worker_manifest(
    path: Path,
    run_id: str,
    suite: str,
    workers: int,
    selected_root: str,
    measured_contexts: set[str] | None = None,
) -> None:
    """Require exact worker, collection, terminal-result, and node-down evidence."""
    events = _read_manifest(path, run_id, suite)
    expected_workers = {f"gw{index}" for index in range(workers)}
    by_kind: dict[str, list[dict[str, object]]] = {}
    for event in events:
        kind = event.get("event")
        if kind not in {
            "worker-start",
            "collection",
            "worker-complete",
            "node-down",
            "test-result",
            "controller-complete",
        }:
            fail("worker manifest contains an unexpected event")
        by_kind.setdefault(str(kind), []).append(event)
    collections: list[tuple[str, ...]] = []
    for kind in ("worker-start", "collection", "worker-complete", "node-down"):
        members = by_kind.get(kind, [])
        observed = [event.get("worker") for event in members]
        if len(observed) != workers or set(observed) != expected_workers:
            fail(f"worker manifest {kind} set is incomplete or duplicated")
        if kind == "collection":
            for event in members:
                node_ids = event.get("node_ids")
                if (
                    not isinstance(node_ids, list)
                    or not node_ids
                    or any(not isinstance(nodeid, str) for nodeid in node_ids)
                    or len(set(node_ids)) != len(node_ids)
                ):
                    fail("worker collection evidence is malformed or empty")
                collections.append(tuple(node_ids))
        elif kind == "worker-complete":
            if any(event.get("exitstatus") != 0 for event in members):
                fail("worker completion evidence reports failure")
        elif kind == "node-down":
            if any(
                event.get("error") is not False or event.get("exitstatus") != 0
                for event in members
            ):
                fail("worker node-down evidence reports a crash or incomplete exit")
    if any(collection != collections[0] for collection in collections[1:]):
        fail("xdist workers did not collect identical node IDs")
    selected = set(collections[0])
    prefix = selected_root.rstrip("/") + "/"
    if any(
        (nodeid.partition("::")[0] != selected_root)
        and not nodeid.partition("::")[0].startswith(prefix)
        for nodeid in selected
    ):
        fail("worker collection contains a node outside the selected root")
    result_events = by_kind.get("test-result", [])
    result_nodes = [event.get("nodeid") for event in result_events]
    if len(result_nodes) != len(selected) or set(result_nodes) != selected:
        fail("every selected node must have exactly one terminal result")
    if any(event.get("outcome") not in {"passed", "failed", "skipped"} for event in result_events):
        fail("worker manifest terminal result is malformed")
    controller = by_kind.get("controller-complete", [])
    if len(controller) != 1 or controller[0].get("exitstatus") != 0:
        fail("controller completion evidence reports failure")
    if measured_contexts is not None:
        expected_contexts = {
            f"apg-worker:{run_id}:{worker}" for worker in expected_workers
        }
        observed_contexts = {
            context
            for context in measured_contexts
            if context.startswith("apg-worker:")
        }
        if observed_contexts != expected_contexts:
            missing = sorted(expected_contexts - measured_contexts)
            foreign = sorted(observed_contexts - expected_contexts)
            fail(
                "worker coverage contribution differs: "
                f"missing={missing}; foreign={foreign}"
            )


def validate_child_manifest(
    path: Path, run_id: str, suite: str, measured_contexts: set[str]
) -> None:
    """Require every registered Python child to finish and contribute coverage."""
    events = _read_manifest(path, run_id, suite)
    grouped: dict[str, list[dict[str, object]]] = {}
    for event in events:
        if event.get("event") not in {"child-start", "child-complete"}:
            fail("child manifest contains an unexpected event")
        process_id = event.get("process_id")
        context = event.get("context")
        if not isinstance(process_id, str) or not process_id or not isinstance(context, str):
            fail("child manifest event is malformed")
        grouped.setdefault(process_id, []).append(event)
    for process_id, process_events in grouped.items():
        kinds = [event["event"] for event in process_events]
        contexts = {event["context"] for event in process_events}
        if kinds.count("child-start") != 1 or kinds.count("child-complete") != 1:
            fail(f"required Python child did not start and complete exactly once: {process_id}")
        expected_context = f"apg-child:{run_id}:{process_id}"
        if contexts != {expected_context}:
            fail(f"required Python child has no observable coverage contribution: {process_id}")
    expected_contexts = {
        f"apg-child:{run_id}:{process_id}" for process_id in grouped
    }
    observed_contexts = {
        context
        for context in measured_contexts
        if context.startswith("apg-child:")
    }
    if observed_contexts != expected_contexts:
        missing = sorted(expected_contexts - observed_contexts)
        foreign = sorted(observed_contexts - expected_contexts)
        if missing:
            process_ids = [context.rsplit(":", 1)[1] for context in missing]
            fail(
                "required Python child has no observable coverage contribution: "
                + ", ".join(process_ids)
            )
        fail(
            "child coverage contribution differs: "
            f"missing={missing}; foreign={foreign}"
        )


def _coverage_contexts(data_file: Path) -> set[str]:
    from coverage import CoverageData

    data = CoverageData(basename=str(data_file))
    try:
        data.read()
        return set(data.measured_contexts())
    except Exception as error:
        fail(f"coverage contexts are unreadable: {data_file.name}: {error}")
    finally:
        data.close(force=True)


def _component_artifacts(artifacts: Path, suite: str) -> set[Path]:
    return {
        artifacts / f"{suite}.coverage",
        artifacts / f"{suite}.json",
        artifacts / f"{suite}.workers.jsonl",
        artifacts / f"{suite}.children.jsonl",
    }


def _pytest_command(
    root: Path,
    suite: str,
    workers: int,
    data_file: Path,
    json_file: Path,
    run_id: str,
) -> list[str]:
    selected = UNIT_ROOT if suite == "unit" else INTEGRATION_ROOT
    return [
        sys.executable,
        "-m",
        "pytest",
        "-p",
        "xdist.plugin",
        "-p",
        "pytest_cov.plugin",
        "-n",
        str(workers),
        "--testrunuid",
        run_id,
        "--max-worker-restart=0",
        "--dist=load",
        "-p",
        "src.test.apg_pytest_plugin",
        "--cov=libexec",
        "--cov-branch",
        f"--cov-config={root / '.coveragerc'}",
        f"--cov-report=json:{json_file}",
        "--cov-report=",
        str(root / selected),
    ]


def _run_pytest(
    root: Path,
    suite: str,
    workers: int,
    artifacts: Path,
    *,
    run_id: str | None = None,
    failure_mode: str | None = None,
) -> tuple[Path, dict[str, object]]:
    run_id = run_id or secrets.token_hex(16)
    data_file = artifacts / f"{suite}.coverage"
    json_file = artifacts / f"{suite}.json"
    worker_manifest = artifacts / f"{suite}.workers.jsonl"
    child_manifest = artifacts / f"{suite}.children.jsonl"
    existing = set(artifacts.iterdir())
    if existing:
        fail(f"{suite} coverage artifact directory contains unexpected data")
    for manifest in (worker_manifest, child_manifest):
        descriptor = os.open(manifest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(descriptor)
    environment = os.environ.copy()
    environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    executable_dir = str(Path(sys.executable).parent)
    environment["PATH"] = executable_dir + os.pathsep + environment.get("PATH", "")
    environment["COVERAGE_FILE"] = str(data_file)
    environment["APG_TEST_RUN_ID"] = run_id
    environment["APG_TEST_SUITE"] = suite
    environment["APG_TEST_SELECTED_ROOT"] = (
        UNIT_ROOT if suite == "unit" else INTEGRATION_ROOT
    ).as_posix()
    environment["APG_TEST_WORKER_MANIFEST"] = str(worker_manifest)
    environment["APG_TEST_CHILD_MANIFEST"] = str(child_manifest)
    environment["APG_TEST_ARTIFACT_DIRECTORY"] = str(artifacts)
    environment["APG_TEST_REQUIRED_ENTRYPOINTS"] = json.dumps(
        sorted(path.name for path in (root / "bin").iterdir() if path.is_file())
    )
    environment["APG_TEST_REQUIRED_MODULE_BASENAMES"] = json.dumps(
        sorted({path.name for path in (root / "libexec").rglob("*.py")})
    )
    environment["APG_TEST_CANONICAL_LIBEXEC"] = str((root / "libexec").resolve())
    bootstrap = str(root / "src/test/apg_coverage_bootstrap")
    environment["PYTHONPATH"] = bootstrap + os.pathsep + environment.get("PYTHONPATH", "")
    if failure_mode:
        environment["APG_TEST_FAILURE_MODE"] = failure_mode
    else:
        environment.pop("APG_TEST_FAILURE_MODE", None)
    result = subprocess.run(
        _pytest_command(root, suite, workers, data_file, json_file, run_id),
        cwd=root,
        env=environment,
        check=False,
    )
    if result.returncode != 0:
        validate_worker_manifest(
            worker_manifest,
            run_id,
            suite,
            workers,
            (UNIT_ROOT if suite == "unit" else INTEGRATION_ROOT).as_posix(),
        )
        fail(f"{suite} pytest run failed with status {result.returncode}")
    if not data_file.is_file() or not json_file.is_file():
        fail(f"{suite} coverage output is incomplete")
    measured_contexts = _coverage_contexts(data_file)
    validate_worker_manifest(
        worker_manifest,
        run_id,
        suite,
        workers,
        (UNIT_ROOT if suite == "unit" else INTEGRATION_ROOT).as_posix(),
        measured_contexts,
    )
    validate_child_manifest(
        child_manifest, run_id, suite, measured_contexts
    )
    expected = _component_artifacts(artifacts, suite)
    if set(artifacts.iterdir()) != expected:
        fail(f"{suite} coverage left unexpected data")
    try:
        report = json.loads(json_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        fail(f"{suite} coverage JSON is unreadable: {error}")
    if not isinstance(report, dict):
        fail(f"{suite} coverage JSON is not an object")
    return data_file, report


def _combine_coverage(root: Path, data_files: Sequence[Path], output: Path) -> dict[str, object]:
    from coverage import Coverage, CoverageData

    combined = CoverageData(basename=str(output))
    try:
        for path in data_files:
            data = CoverageData(basename=str(path))
            try:
                data.read()
                combined.update(data)
            except Exception as error:
                fail(f"coverage data could not be combined: {path.name}: {error}")
            finally:
                data.close(force=True)
        combined.write()
    finally:
        combined.close(force=True)
    json_file = output.with_suffix(".json")
    coverage = Coverage(data_file=str(output), config_file=str(root / ".coveragerc"))
    coverage.load()
    loaded_data = coverage.get_data()
    try:
        coverage.json_report(outfile=str(json_file))
    finally:
        coverage.get_data().close(force=True)
        loaded_data.close(force=True)
    try:
        value = json.loads(json_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        fail(f"combined coverage JSON is unreadable: {error}")
    if not isinstance(value, dict):
        fail("combined coverage JSON is not an object")
    return value


def run(
    suite: str,
    workers: int,
    root: Path,
    *,
    keep_artifacts_on_failure: bool = False,
    failure_mode: str | None = None,
) -> None:
    """Validate inventory, run selected suites, and enforce exact gates."""
    if workers < 1 or workers > 64:
        fail("workers must be between 1 and 64")
    inventory = load_inventory(root)
    validate_inventory(root, inventory)
    dependency_versions()
    artifact_ownership = _artifact_directory(root)
    artifacts = artifact_ownership.path
    completed = False
    try:
        selected = ("unit", "integration") if suite == "combined" else (suite,)
        results: dict[str, ComponentResult] = {}
        errors: list[str] = []
        invocation_id = secrets.token_hex(16)
        for selected_suite in selected:
            try:
                component_artifacts = artifacts / selected_suite
                component_artifacts.mkdir(mode=0o700)
                data_file, report = _run_pytest(
                    root,
                    selected_suite,
                    workers,
                    component_artifacts,
                    run_id=f"{invocation_id}-{selected_suite}",
                    failure_mode=failure_mode,
                )
                validate_coverage_report(report, set(inventory.coverage_sources))
                paths = sorted(
                    path
                    for path, suites in inventory.coverage_sources.items()
                    if selected_suite in suites
                )
                counts = coverage_counts(report, paths)
                results[selected_suite] = ComponentResult(data_file, report, counts)
                try:
                    enforce_threshold(counts, *THRESHOLDS[selected_suite])
                except ToolError as error:
                    errors.append(f"{selected_suite}: {error}")
                else:
                    print(
                        f"PASS {selected_suite}: statements "
                        f"{counts.statements_covered}/{counts.statements_total}; branches "
                        f"{counts.branches_covered}/{counts.branches_total}"
                    )
            except ToolError as error:
                errors.append(f"{selected_suite}: {error}")
        if suite == "combined" and set(results) == {"unit", "integration"}:
            try:
                report = _combine_coverage(
                    root,
                    [results[name].data_file for name in ("unit", "integration")],
                    artifacts / "combined.coverage",
                )
                validate_coverage_report(report, set(inventory.coverage_sources))
                paths = sorted(inventory.coverage_sources)
                counts = coverage_counts(report, paths)
                enforce_threshold(counts, *THRESHOLDS["combined"])
            except ToolError as error:
                errors.append(f"combined: {error}")
            else:
                print(
                    "PASS combined union: statements "
                    f"{counts.statements_covered}/{counts.statements_total}; branches "
                    f"{counts.branches_covered}/{counts.branches_total}"
                )
        if errors:
            fail("; ".join(errors))
        completed = True
    finally:
        if not completed and keep_artifacts_on_failure:
            print(f"{COMMAND}: retained failure artifacts: {artifacts}", file=sys.stderr)
        else:
            _cleanup_artifacts(artifact_ownership)


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        prog=COMMAND,
        description="Run APG pytest suites with xdist and exact coverage gates.",
    )
    value.add_argument("suite", choices=("unit", "integration", "unit-integration"))
    value.add_argument("--workers", type=int, default=8)
    value.add_argument("--keep-artifacts-on-failure", action="store_true")
    value.add_argument(
        "--verify-failure-mode",
        choices=("worker-crash", "missing-child"),
    )
    return value


def main(arguments: Sequence[str] | None = None) -> int:
    args = parser().parse_args(arguments)
    suite = "combined" if args.suite == "unit-integration" else args.suite
    root = Path(__file__).resolve(strict=True).parent.parent
    try:
        run(
            suite,
            args.workers,
            root,
            keep_artifacts_on_failure=args.keep_artifacts_on_failure,
            failure_mode=args.verify_failure_mode,
        )
    except ToolError as error:
        print(f"{COMMAND}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
