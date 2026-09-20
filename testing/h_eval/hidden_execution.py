"""Exact hidden execution evidence, separate from candidate-authored grading.

The runner controls are source-owned; candidate hooks remain part of the subject.
This is execution accounting, not a sandbox against arbitrary hostile code.
"""
from __future__ import annotations

import ast
from collections import Counter
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re

MAX_REPORT_BYTES = 1_000_000
SCHEMA = "apg.hidden-execution/v1"

# Invoked by the bound Python executable, never parsed out of candidate stdout.
PYTEST_DRIVER = '''import json, sys, pytest
class Observer:
    def __init__(self):
        self.events = []
        self.function_identities = {}
    def pytest_itemcollected(self, item):
        self.events.append([item.nodeid, "collected"])
        self.function_identities[item.nodeid] = getattr(item, "originalname", None)
    def pytest_deselected(self, items):
        self.events.extend([item.nodeid, "deselected"] for item in items)
    def pytest_runtest_logstart(self, nodeid, location):
        self.events.append([nodeid, "started"])
    def pytest_runtest_logreport(self, report):
        status = report.outcome
        if hasattr(report, "wasxfail"):
            status = "xpassed" if report.passed else "xfailed"
        self.events.append([report.nodeid, report.when + ":" + status])
observer = Observer()
result = pytest.main(sys.argv[2:], plugins=[observer])
with open(sys.argv[1], "x", encoding="utf-8") as stream:
    json.dump({"runner_version": pytest.__version__, "events": observer.events,
               "function_identities": observer.function_identities}, stream)
sys.exit(result)
'''


def identities(files):
    return {name: hashlib.sha256(raw.encode()).hexdigest() for name, raw in sorted(files.items())}


def prepare(spec, overlay, candidate):
    """Derive identities only from the source-owned, collision-renamed overlay."""
    if spec.command[0] == "go":
        expected = [name for raw in overlay.values()
                    for name in re.findall(r"\bfunc\s+(Test\w+)\s*\(", raw)]
        command = (*spec.command[:2], "-json", *spec.command[2:])
        return replace(spec, command=command), "go", expected
    if spec.command[1:3] != ("-m", "pytest"):
        return spec, None, []
    expected = []
    for path, raw in sorted(overlay.items()):
        for node in ast.parse(raw).body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                # Current source-owned fixtures have no parametrized/class tests.
                # Refuse unsupported identity expansion instead of count matching.
                if any("parametrize" in ast.unparse(d) for d in node.decorator_list):
                    raise ValueError("hidden parametrization needs exact expanded identities")
                expected.append(path + "::" + node.name)
    report = "apg-hidden-execution.json"
    while any(report == n or n.startswith(report + "/") or report.startswith(n + "/")
              for n in {*candidate, *overlay}):
        report = "apg-" + report
    command = (spec.command[0], "-c", PYTEST_DRIVER, report, "-q", "--rootdir=.",
               "-o", "addopts=", "-o", "python_files=*.py", "-o", "python_functions=test_*",
               *sorted(overlay))
    return replace(spec, command=command, attestation_report=report), "pytest", expected


def capture(spec, completed, root):
    """Read the run-owned artifact before the disposable evaluation is removed."""
    if not spec.attestation_report:
        return
    path = Path(root) / spec.attestation_report
    raw = b""
    if path.is_file() and not path.is_symlink() and path.stat().st_size <= MAX_REPORT_BYTES:
        raw = path.read_bytes()
    completed.apg_hidden_report = raw


def _pytest_events(raw):
    value = json.loads(raw)
    if (not isinstance(value, dict) or not isinstance(value.get("runner_version"), str)
            or not value["runner_version"].strip()):
        raise ValueError("missing pytest runner version")
    events = value["events"]
    if not isinstance(events, list) or any(
            not isinstance(e, list) or len(e) != 2 or not all(isinstance(x, str) for x in e)
            for e in events):
        raise ValueError("invalid pytest events")
    return events, value["runner_version"]


def _go_events(raw):
    events, packages = [], {}
    for line in raw.splitlines():
        event = json.loads(line)
        if not isinstance(event, dict):
            raise ValueError("invalid Go event")
        # Output is opaque candidate text, even when it contains JSON.
        name, action, package = event.get("Test"), event.get("Action"), event.get("Package")
        if name and action in {"run", "pass", "fail", "skip"}:
            if not isinstance(name, str) or not isinstance(package, str) or not package:
                raise ValueError("unbound Go test event")
            packages.setdefault(name, set()).add(package)
            events.append([name, {"run": "started", "pass": "passed",
                                  "fail": "failed", "skip": "skipped"}[action]])
    if any(len(p) != 1 for p in packages.values()):
        raise ValueError("ambiguous test identity across Go packages")
    return events, "go-test-json/v1"


def attest(kind, expected, raw, returncode, command, overlay, candidate):
    """Derive qualification from exact identities and phase outcomes, never counts."""
    events, version, errors = [], "unavailable", []
    try:
        if len(raw) > MAX_REPORT_BYTES:
            raise ValueError("execution artifact exceeds bound")
        events, version = _pytest_events(raw) if kind == "pytest" else _go_events(raw)
    except (ValueError, KeyError, TypeError, UnicodeError) as error:
        errors.append("invalid execution artifact: " + str(error))
    if not expected or len(expected) != len(set(expected)):
        errors.append("empty or duplicate expected identities")
    observed = {}
    required = (["collected", "started", "setup:passed", "call:passed", "teardown:passed"]
                if kind == "pytest" else ["started", "passed"])
    for name, state in events:
        observed.setdefault(name, []).append(state)
    for name in expected:
        states = observed.get(name, [])
        if Counter(states) != Counter(required) or states != required:
            errors.append(name + ": expected exactly " + ",".join(required)
                          + "; observed " + (",".join(states) or "not-collected/not-run"))
    if returncode != 0:
        errors.append("hidden command exited " + str(returncode))
    return {"schema": SCHEMA, "runner_kind": kind, "runner_version": version,
            "expected_identities": expected, "observed_statuses": observed,
            "missing_identities": sorted(set(expected) - set(observed)),
            "command_owner": "source-owned-hidden-run-only", "command": list(command),
            "hidden_overlay": identities(overlay), "candidate_configuration_digests": identities(candidate),
            "hidden_collection_overrides": kind == "pytest",
            "execution_artifact_sha256": hashlib.sha256(raw).hexdigest(),
            "qualifying": not errors, "fail_reasons": errors}


def collection_check_present(files):
    """Visible stable function identity, independent of file naming convention."""
    required = "test_value_normalizes_mixed_input"
    for name, raw in files.items():
        if not name.endswith(".py"):
            continue
        try:
            if any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == required
                   for n in ast.parse(raw).body):
                return True
        except SyntaxError:
            continue
    return False


if __name__ == "__main__":
    # Match python -m pytest's import root when used as an observer driver.
    import os
    import sys
    sys.path[0] = os.getcwd()
    exec(PYTEST_DRIVER)
