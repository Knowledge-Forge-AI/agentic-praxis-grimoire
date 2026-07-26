"""Run-scoped pytest/xdist accounting for the APG test runner."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest

from libexec.apg_test import record_worker_coverage_sentinel


_RESULTS: dict[str, str] = {}
_CONTEXT_WORKERS: set[str] = set()


def _settings() -> tuple[str, str, Path]:
    return (
        os.environ["APG_TEST_RUN_ID"],
        os.environ["APG_TEST_SUITE"],
        Path(os.environ["APG_TEST_WORKER_MANIFEST"]),
    )


def _append(event: dict[str, object]) -> None:
    run_id, suite, path = _settings()
    payload = {"run_id": run_id, "suite": suite, **event}
    line = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.write(descriptor, line)
    finally:
        os.close(descriptor)


def _worker_id(config: pytest.Config) -> str | None:
    worker_input = getattr(config, "workerinput", None)
    return worker_input.get("workerid") if worker_input is not None else None


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "unit: APG isolated unit contract")
    config.addinivalue_line("markers", "integration: APG real-boundary contract")
    worker = _worker_id(config)
    if worker is not None:
        _append({"event": "worker-start", "worker": worker})


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    suite = os.environ["APG_TEST_SUITE"]
    selected_root = os.environ["APG_TEST_SELECTED_ROOT"].rstrip("/")
    opposite = "integration" if suite == "unit" else "unit"
    seen: set[str] = set()
    for item in items:
        path = item.nodeid.partition("::")[0]
        if path != selected_root and not path.startswith(selected_root + "/"):
            raise pytest.UsageError(f"collected node outside {suite} root: {item.nodeid}")
        if item.nodeid in seen:
            raise pytest.UsageError(f"duplicate collected node: {item.nodeid}")
        seen.add(item.nodeid)
        if item.get_closest_marker(opposite) is not None:
            raise pytest.UsageError(f"collected node has wrong suite marker: {item.nodeid}")
        item.add_marker(suite)


@pytest.hookimpl(optionalhook=True)
def pytest_xdist_node_collection_finished(node: Any, ids: list[str]) -> None:
    _append(
        {
            "event": "collection",
            "worker": node.gateway.id,
            "node_ids": list(ids),
        }
    )


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    if _worker_id(report.config) is not None if hasattr(report, "config") else False:
        return
    if report.when == "setup" and report.outcome in {"failed", "skipped"}:
        _RESULTS[report.nodeid] = report.outcome
    elif report.when == "call":
        _RESULTS[report.nodeid] = report.outcome
    elif report.when == "teardown" and report.outcome == "failed":
        _RESULTS[report.nodeid] = report.outcome


@pytest.hookimpl(optionalhook=True)
def pytest_testnodedown(node: Any, error: object | None) -> None:
    output = getattr(node, "workeroutput", {})
    _append(
        {
            "event": "node-down",
            "worker": node.gateway.id,
            "error": error is not None,
            "exitstatus": output.get("exitstatus"),
        }
    )


def pytest_sessionstart(session: pytest.Session) -> None:
    if _worker_id(session.config) is not None:
        return
    if os.environ.get("APG_TEST_FAILURE_MODE") != "missing-child":
        return
    environment = os.environ.copy()
    environment["APG_TEST_REQUIRED_CHILD_ID"] = "injected-missing-child"
    environment["APG_TEST_DISABLE_CHILD_COVERAGE"] = "1"
    environment.pop("COVERAGE_PROCESS_CONFIG", None)
    subprocess.run([sys.executable, "-c", "pass"], env=environment, check=True)


def pytest_runtest_setup(item: pytest.Item) -> None:
    worker = _worker_id(item.config)
    if worker is not None and worker not in _CONTEXT_WORKERS:
        from coverage import Coverage

        coverage = Coverage.current()
        if coverage is None:
            raise pytest.UsageError("worker coverage accounting is unavailable")
        run_id, _suite, _path = _settings()
        coverage.switch_context(f"apg-worker:{run_id}:{worker}")
        record_worker_coverage_sentinel()
        _CONTEXT_WORKERS.add(worker)
    if worker != "gw0" or os.environ.get("APG_TEST_FAILURE_MODE") != "worker-crash":
        return
    marker = Path(os.environ["APG_TEST_ARTIFACT_DIRECTORY"]) / "worker-crash-triggered"
    try:
        descriptor = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return
    os.close(descriptor)
    os._exit(86)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    worker = _worker_id(session.config)
    if worker is not None:
        _append(
            {
                "event": "worker-complete",
                "worker": worker,
                "exitstatus": int(exitstatus),
            }
        )
        return
    for nodeid, outcome in sorted(_RESULTS.items()):
        _append(
            {
                "event": "test-result",
                "nodeid": nodeid,
                "outcome": outcome,
            }
        )
    _append({"event": "controller-complete", "exitstatus": int(exitstatus)})
