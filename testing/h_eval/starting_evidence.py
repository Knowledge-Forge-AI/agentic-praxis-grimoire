"""Exact durable starting-pytest readback; no generalized evidence admission."""
from pathlib import Path

from . import authored_execution, hidden_execution


def _command(receipt, spec, runtime):
    command = receipt["command"]
    if (not isinstance(command, list) or not command or not Path(command[0]).is_absolute()
            or command[1:] != list(spec.command[1:]) or not receipt.get("runtime_version")):
        raise ValueError("starting command identity/runtime missing or changed")
    if runtime is not None:
        from .promotion_oracles import _manifest_runtime_name
        bound = runtime["runtimes"][_manifest_runtime_name(runtime, spec.command[0])]
        if (command[0] != runtime["files"][bound["executable"]]["physical_path"]
                or receipt["runtime_version"] != bound["version_stdout"]):
            raise ValueError("starting runtime binding changed")
    if receipt["status"] != ("pass" if receipt["returncode"] == 0 else "fail"):
        raise ValueError("starting command status changed")
    return command


def verify(record, case, runtime=None):
    """Recompute raw-artifact attestation against source and preregistered bytes."""
    from . import promotion_oracles as oracle
    spec = oracle.spec_for(case["case_id"])
    files = case["subject_files"]
    if (record["case_id"] != case["case_id"] or record["oracle_id"] != spec.oracle_id
            or record["hidden_oracle_sha256"] != spec.hidden_oracle_sha256):
        raise ValueError("starting subject oracle binding changed")
    overlay = oracle._hidden_overlay(spec, files)
    run_spec, kind, expected = hidden_execution.prepare(spec, overlay, files)
    hidden = record["hidden_oracle"]
    command = _command(hidden, run_spec, runtime)
    raw = hidden["hidden_execution_artifact"].encode()
    attestation = hidden_execution.attest(kind, expected, raw, hidden["returncode"], command, overlay, files)
    attestation["runtime_version"] = attestation["runner_version"]
    if hidden["execution_attestation"] != attestation or not attestation["qualifying"]:
        raise ValueError("starting hidden execution artifact/attestation invalid")
    custody = oracle._grading_custody(files, {**files, **overlay}, {}, overlay)
    if hidden["grading_custody"] != custody:
        raise ValueError("starting subject identity changed")
    authored = record["model_authored_tests"]
    for variant in ("good", "bad"):
        source = spec.good_files if variant == "good" else spec.bad_files
        substitutions = {name: source[name] for name in spec.implementation_paths}
        graded = {**files, **substitutions}
        receipt = authored[variant]
        observed_spec = (authored_execution.prepare(spec, graded)
                         if spec.case_id == authored_execution.COLLECTION_CASE else spec)
        _command(receipt, observed_spec, runtime)
        if receipt["grading_custody"] != oracle._grading_custody(files, graded, substitutions, {}):
            raise ValueError("starting authored custody changed")
        if spec.case_id == authored_execution.COLLECTION_CASE:
            recomputed = authored_execution.attest(
                {**receipt, "hidden_execution_artifact": receipt["authored_execution_artifact"]}, spec.command, graded)
            if receipt["authored_execution"] != recomputed:
                raise ValueError("starting authored execution changed")
    passed = authored["good"]["returncode"] == 0 and authored["bad"]["returncode"] != 0
    if spec.case_id == authored_execution.COLLECTION_CASE:
        passed = passed and authored_execution.discriminates(authored["good"], authored["bad"])
    status = "pass" if passed else "fail"
    if (authored["status"] != status or record["status"] != status
            or record["starting_failure_required"] != (not passed)
            or record["starting_subject"] != ("source-oracle-complete" if passed else "genuinely-incomplete-or-failing")):
        raise ValueError("starting subject classification changed")
    return attestation


def verify_all(evidence, cases, runtime=None):
    """All three current starting pytest implementations satisfy hidden tests.

    Their genuine deficiencies are candidate collection or vacuous authored
    discrimination. Missing hidden evidence must never masquerade as rejection.
    """
    expected = {c["case_id"]: c for c in cases if c["case_id"].startswith("pytest-test-profile/positive/")}
    rows = [r for r in evidence["starting_subjects"] if r["case_id"] in expected]
    if len(rows) != len(expected) or {r["case_id"] for r in rows} != set(expected):
        raise ValueError("starting pytest coverage missing or duplicated")
    try:
        return [verify(row, expected[row["case_id"]], runtime) for row in rows]
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError("malformed starting pytest evidence") from error
