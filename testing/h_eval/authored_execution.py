"""Candidate-configured pytest observation, distinct from hidden grading."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from . import hidden_execution

STABLE_FUNCTION = "test_value_normalizes_mixed_input"
COLLECTION_CASE = "pytest-test-profile/positive/collection"


def prepare(spec, files):
    """Observe the selected pytest arguments without any collection overrides."""
    report = "apg-authored-execution.json"
    while any(report == n or n.startswith(report + "/") or report.startswith(n + "/") for n in files):
        report = "apg-" + report
    driver = str(Path(hidden_execution.__file__).resolve())
    return replace(spec, command=(spec.command[0], driver, report, *spec.command[3:]),
                   attestation_report=report)


def attest(receipt, selected_command, files):
    raw = receipt.get("hidden_execution_artifact", "").encode()
    observed, identities, errors, version = {}, {}, [], "unavailable"
    try:
        if len(raw) > hidden_execution.MAX_REPORT_BYTES:
            raise ValueError("authored artifact exceeds bound")
        events, version = hidden_execution._pytest_events(raw)
        identities = json.loads(raw)["function_identities"]
        if not isinstance(identities, dict):
            raise ValueError("invalid function identities")
        if not version.strip():
            raise ValueError("empty runner version")
        for node, state in events:
            observed.setdefault(node, []).append(state)
    except (ValueError, KeyError, TypeError, UnicodeError) as error:
        errors.append(str(error))
    stable = [node for node in observed if identities.get(node) == STABLE_FUNCTION]
    if len(stable) != 1:
        errors.append("expected exactly one stable function node")
    for node in stable:
        states = observed[node]
        if states not in (["collected", "started", "setup:passed", "call:passed", "teardown:passed"],
                          ["collected", "started", "setup:passed", "call:failed", "teardown:passed"]):
            errors.append("stable node did not execute exactly once to a terminal outcome")
    return {"schema": "apg.authored-pytest-execution/v1", "runner_version": version,
            "command_owner": "candidate-configured-authored-run", "selected_command": list(selected_command),
            "observer_command": receipt["command"], "hidden_collection_overrides": False,
            "candidate_configuration_digests": hidden_execution.identities(files),
            "execution_artifact_sha256": hashlib.sha256(raw).hexdigest(),
            "observed_statuses": observed, "function_identities": identities, "stable_function": STABLE_FUNCTION,
            "stable_nodes": stable, "execution_complete": not errors, "fail_reasons": errors}


def discriminates(good, bad):
    left, right = (r["authored_execution"] for r in (good, bad))
    nodes = left["stable_nodes"]
    return (left["execution_complete"] and right["execution_complete"]
            and nodes == right["stable_nodes"]
            and "call:passed" in left["observed_statuses"][nodes[0]]
            and "call:failed" in right["observed_statuses"][nodes[0]])
