"""Source-owned promotion oracle execution and retained evidence."""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
from typing import Any, Callable, Mapping, Sequence

from . import promotion_fixture_specs, hidden_execution, authored_execution
from . import runtime_execution, runtime_manifest


SCHEMA = "apg.h-promotion-oracle/v1"
SOURCE_PATH = "testing/h_eval/promotion_oracles.py"
FIXTURE_SOURCE_PATH = "testing/h_eval/promotion_fixture_specs.py"
SOURCE_PATHS = (SOURCE_PATH, FIXTURE_SOURCE_PATH, "testing/h_eval/hidden_execution.py",
                "testing/h_eval/lifecycle_hidden.py", "testing/h_eval/authored_execution.py",
                "testing/h_eval/starting_evidence.py")
MAX_STREAM_BYTES = 1_000_000
COMMAND_TIMEOUT_SECONDS = 30
MAX_INVENTORY_BYTES = 16_000_000

PromotionOracleError = promotion_fixture_specs.PromotionOracleError
FixtureSpec = promotion_fixture_specs.FixtureSpec
_ORACLES = promotion_fixture_specs.ORACLES
_source_check = promotion_fixture_specs.source_check

# BAD model-result snapshots for test-profile cases retain the source-owned
# GOOD implementation and substitute authored tests that are vacuous or fail
# to distinguish the known-bad implementation.  This keeps fixture-pair
# qualification about the test oracle rather than a broken production copy.
_BAD_AUTHORED_TESTS: dict[str, dict[str, str]] = {
    "go-test-profile/positive/lifecycle": {
        "parse_test.go": 'package parsing\nimport "testing"\nfunc TestParserSmoke(*testing.T) {}\n',
    },
    "go-test-profile/positive/false-pass": {
        "harness_test.go": 'package harness\nimport "testing"\nfunc TestHarnessSmoke(*testing.T) {}\n',
    },
    "go-test-profile/positive/parallel-isolation": {
        "files_test.go": 'package files\nimport "testing"\nfunc TestIsolationSmoke(*testing.T) {}\n',
    },
    "pytest-test-profile/positive/collection": {
        "check_values.py": "def test_collected():\n    assert True\n",
    },
    "pytest-test-profile/positive/fixture-lifecycle": {
        "test_output.py": "def test_fixture_exists(output):\n    assert output is not None\n",
    },
    "pytest-test-profile/positive/worker-isolation": {
        "test_counter.py": "def test_worker_smoke():\n    assert True\n",
    },
}


def qualification_files(spec: FixtureSpec, variant: str) -> Mapping[str, str]:
    if variant != "bad" or spec.case_id not in _BAD_AUTHORED_TESTS:
        return spec.good_files if variant == "good" else spec.bad_files
    files = dict(_implementation_files(spec, spec.good_files))
    files.update(_BAD_AUTHORED_TESTS[spec.case_id])
    return files

def spec_for(case_id: str) -> FixtureSpec:
    try:
        return _ORACLES[case_id]
    except KeyError as exc:
        raise PromotionOracleError(f"no source-owned oracle for {case_id}") from exc


def case_ids() -> tuple[str, ...]:
    return tuple(sorted(_ORACLES))


def required_executable_tokens() -> tuple[str, ...]:
    """Return command tokens that the sealed runtime must bind."""
    return tuple(sorted({spec.command[0] for spec in _ORACLES.values() if spec.command}))


def executable_paths_for_value(value: Mapping[str, Any]) -> dict[str, str]:
    """Resolve the small diagnostic executable map from a sealed manifest."""
    if isinstance(value, Mapping) and isinstance(value.get("runtimes"), Mapping):
        result: dict[str, str] = {}
        files = value.get("files")
        if not isinstance(files, Mapping):
            raise PromotionOracleError("sealed runtime manifest lacks file table")
        for token in required_executable_tokens():
            name = _manifest_runtime_name(value, token)
            record = value["runtimes"].get(name)
            if not isinstance(record, Mapping):
                raise PromotionOracleError(f"sealed runtime manifest lacks runtime: {token}")
            executable_name = record.get("executable")
            file_record = files.get(executable_name)
            if not isinstance(file_record, Mapping) or file_record.get("kind") != "file":
                raise PromotionOracleError(f"sealed runtime executable is unbound: {token}")
            result[token] = str(file_record["physical_path"])
        return result
    return {str(key): str(path) for key, path in value.items()}


def source_sha256(root: str | Path | None = None) -> str:
    """Hash both the execution owner and its source-owned fixture registry."""
    digest = hashlib.sha256()
    base = Path(root) if root is not None else Path(__file__).parents[2]
    paths = (base / name for name in SOURCE_PATHS)
    for path in paths:
        digest.update(path.read_bytes())
    return digest.hexdigest()


def registry_inventory() -> tuple[dict[str, str], ...]:
    """Return the exact source-owned registry inventory.

    The preregistration is the expected inventory.  This function exposes the
    independently derived implementation side so callers can compare both
    sides without accidentally validating a registry against itself.
    """
    return tuple({
        "case_id": case_id,
        "skill_id": spec.skill_id,
        "kind": spec.kind,
        "oracle_id": spec.oracle_id,
        "hidden_oracle_sha256": spec.hidden_oracle_sha256,
        "fixture_kind": spec.fixture_kind,
        "fixture_contract": spec.check_name,
    } for case_id, spec in sorted(_ORACLES.items()))


def _safe_subject_files(files: Mapping[str, str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for name, content in files.items():
        relative = Path(name)
        if (relative.is_absolute() or "\\" in name or any(part in {"", ".", ".."} for part in relative.parts)
                or not isinstance(content, str)):
            raise PromotionOracleError(f"unsafe model subject path {name}")
        result[name] = content
    return result


def _hidden_overlay(spec: FixtureSpec, subject_files: Mapping[str, str] | None = None) -> dict[str, str]:
    """Add only non-conflicting oracle files; never supply candidate support."""
    overlay: dict[str, str] = {}
    occupied = set(subject_files or {}) | set(spec.good_files) | set(spec.bad_files)
    for name, content in spec.hidden_oracle_files.items():
        if spec.command and spec.command[0] == "go":
            prefix = "apg_oracle_"
            namespace = "TestAPGOracle"
            while any(namespace in text for text in (subject_files or {}).values()):
                namespace += "Oracle"
            content = re.sub(r"\bTest(\w+)\b", lambda match: namespace + match[1], content)
        elif name.startswith("check_"):
            prefix = "check_apg_oracle_"
        elif name.startswith("test_"):
            prefix = "test_apg_oracle_"
        else:
            prefix = "apg_oracle_"
        target = prefix + Path(name).name
        while any(target == path or target.startswith(path + "/") or path.startswith(target + "/")
                  for path in occupied):
            target = prefix + target
        overlay[target] = content
        occupied.add(target)
    return overlay


def _authored_test_files(spec: FixtureSpec, files: Mapping[str, str]) -> dict[str, str]:
    if not spec.command:
        return {}
    if spec.command[0] == "go":
        return {name: content for name, content in files.items() if name.endswith("_test.go")}
    return {name: content for name, content in files.items()
            if name.startswith(("test_", "check_")) or name.endswith("_test.py")}


def _implementation_files(spec: FixtureSpec, files: Mapping[str, str]) -> dict[str, str]:
    authored = set(_authored_test_files(spec, files))
    return {name: content for name, content in files.items() if name not in authored}


def _write_files(root: Path, files: Mapping[str, str]) -> None:
    for name, content in files.items():
        relative = Path(name)
        path = root / relative
        if relative.is_absolute() or ".." in relative.parts or "\\" in name:
            raise PromotionOracleError(f"unsafe fixture path {name}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="")
        path.chmod(0o600)


def _write_private_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)
    path.chmod(0o600)


def _write_private_json(path: Path, value: Mapping[str, Any]) -> None:
    _write_private_bytes(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def _private_directory(path: str | Path, *, create: bool = False) -> Path:
    value = Path(path)
    if not value.is_absolute() or value.resolve() != value or value.is_symlink():
        raise PromotionOracleError("oracle fixture root must be an absolute physical directory")
    if create:
        value.mkdir(parents=True, exist_ok=False, mode=0o700)
    if not value.is_dir() or value.is_symlink():
        raise PromotionOracleError("oracle fixture root is unavailable")
    if stat.S_IMODE(value.stat().st_mode) & 0o077:
        raise PromotionOracleError("oracle fixture root must be private")
    return value


def _new_fixture_root(path: str | Path) -> Path:
    value = Path(path)
    if value.exists() or value.is_symlink():
        raise PromotionOracleError("oracle fixture root must be a new private directory")
    return _private_directory(value, create=True)


def _fixture_inventory(root: Path) -> list[dict[str, Any]]:
    """Capture the complete subject tree without following symlinks."""
    entries: list[dict[str, Any]] = []
    total = 0
    for candidate in sorted(root.rglob("*")):
        relative = candidate.relative_to(root)
        info = candidate.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise PromotionOracleError(f"fixture subject contains symlink: {relative}")
        if stat.S_ISDIR(info.st_mode):
            entries.append({"path": str(relative), "kind": "directory",
                            "mode": stat.S_IMODE(info.st_mode)})
            continue
        if not stat.S_ISREG(info.st_mode):
            raise PromotionOracleError(f"fixture subject contains unsupported entry: {relative}")
        raw = candidate.read_bytes()
        total += len(raw)
        if total > MAX_INVENTORY_BYTES:
            raise PromotionOracleError("fixture subject inventory exceeds bound")
        entries.append({"path": str(relative), "kind": "file", "mode": stat.S_IMODE(info.st_mode),
                        "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    return entries


def _manifest_runtime_name(manifest: Mapping[str, Any], token: str) -> str:
    runtimes = manifest.get("runtimes")
    if not isinstance(runtimes, Mapping):
        raise PromotionOracleError("sealed runtime manifest lacks runtime table")
    if token in runtimes:
        return token
    aliases = {"python3": ("python",), "python": ("python3",),
               "cc": ("clang", "gcc"), "clang": ("cc", "gcc"), "gcc": ("cc", "clang")}
    for alias in aliases.get(token, ()):
        if alias in runtimes:
            return alias
    raise PromotionOracleError(f"sealed runtime manifest lacks required runtime: {token}")


def _verify_complete_runtime(manifest: Mapping[str, Any]) -> None:
    if not isinstance(manifest, Mapping) or manifest.get("schema") != runtime_manifest.COMPLETE_SCHEMA:
        raise PromotionOracleError("complete sealed runtime manifest required")
    lifecycle = manifest.get("lifecycle")
    if not isinstance(lifecycle, Mapping) or lifecycle.get("state") != "sealed":
        raise PromotionOracleError("sealed runtime manifest required")
    for token in required_executable_tokens():
        _manifest_runtime_name(manifest, token)
    # Race fixtures must not silently fall back to a host compiler.  The
    # manifest must explicitly bind both the C compiler alias and cgo policy.
    _manifest_runtime_name(manifest, "cc")
    environment = manifest.get("environment", {})
    values = environment.get("set", {}) if isinstance(environment, Mapping) else {}
    if values.get("CGO_ENABLED") != "1":
        raise PromotionOracleError("sealed runtime manifest must bind CGO_ENABLED=1 for race fixtures")
    # The Python module and SQLite runtime are manifest-owned requirements even
    # though their task command is invoked through the bound Python executable.
    _manifest_runtime_name(manifest, "pytest")
    _manifest_runtime_name(manifest, "sqlite3")


def _runtime_requirements(manifest: Mapping[str, Any], spec: FixtureSpec) -> dict[str, str]:
    names: dict[str, str] = {}
    for requirement in spec.runtime_requirements:
        if requirement.endswith("-module"):
            module = requirement.removesuffix("-module")
            names[requirement] = _manifest_runtime_name(manifest, module)
        else:
            names[requirement] = _manifest_runtime_name(manifest, requirement)
    return names


def _closed_environment(work: Path, executable: Path, kind: str) -> dict[str, str]:
    real_work = work.resolve()
    environment = {
        "PATH": str(executable.parent),
        "HOME": str(real_work / ".home"),
        "TMPDIR": str(real_work / ".tmp"),
        "LANG": "C",
        "LC_ALL": "C",
        "PYTHONNOUSERSITE": "1",
        "PYTHONPATH": "",
        "NO_PROXY": "*",
        "http_proxy": "",
        "https_proxy": "",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
    }
    if kind == "go":
        environment.update({"GOTOOLCHAIN": "local", "GOPROXY": "off", "GOSUMDB": "off", "GONOSUMDB": "*"})
    (real_work / ".home").mkdir()
    (real_work / ".tmp").mkdir()
    return environment


def _command_receipt_from_completed(spec: FixtureSpec, completed: subprocess.CompletedProcess[bytes],
                                    command: Sequence[str], expected: str | None,
                                    root_marker: str | None = None) -> dict[str, object]:
    if len(completed.stdout) > MAX_STREAM_BYTES or len(completed.stderr) > MAX_STREAM_BYTES:
        raise PromotionOracleError(f"fixture output exceeds bound for {spec.case_id}")
    status = "pass" if completed.returncode == 0 else "fail"
    if expected is not None and status != expected:
        raise PromotionOracleError(f"{spec.case_id} {expected} fixture returned {completed.returncode}")
    marker = root_marker or ""
    stdout = completed.stdout.decode("utf-8", "replace").replace(marker, "<fixture-root>")
    stderr = completed.stderr.decode("utf-8", "replace").replace(marker, "<fixture-root>")
    return {"case_id": spec.case_id, "fixture": expected or "subject", "status": status,
            "oracle_id": spec.oracle_id, "hidden_oracle_sha256": spec.hidden_oracle_sha256,
            "qualification_scope": "source-owned-hidden-oracle",
            "returncode": completed.returncode, "stdout_bytes": len(completed.stdout),
            "stderr_bytes": len(completed.stderr),
            "stdout_sha256": hashlib.sha256(completed.stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(completed.stderr).hexdigest(),
            "stdout": stdout, "stderr": stderr, "command": list(command),
            "runtime_version": getattr(completed, "apg_runner_version", None),
            "network": "configured_offline_not_os_enforced"}


def _command_receipt(spec: FixtureSpec, files: Mapping[str, str], executable_paths: Mapping[str, str],
                     expected: str | None,
                     runner: Callable[[FixtureSpec, Mapping[str, str]], tuple[subprocess.CompletedProcess[bytes], Sequence[str], str | None]] | None = None) -> dict[str, object]:
    if not spec.command:
        raise PromotionOracleError(f"command missing for {spec.case_id}")
    command_name = spec.command[0]
    if runner is not None:
        completed, command, marker = runner(spec, files)
        receipt = _command_receipt_from_completed(spec, completed, command, expected, marker)
        if spec.attestation_report:
            receipt["hidden_execution_artifact"] = getattr(completed, "apg_hidden_report", b"").decode("utf-8", "replace")
        return receipt
    executable_value = executable_paths.get(command_name)
    if not executable_value:
        raise PromotionOracleError(f"manifest executable missing: {command_name}")
    executable = Path(executable_value)
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise PromotionOracleError(f"manifest executable unavailable: {command_name}")
    command = [str(executable), *spec.command[1:]]
    with tempfile.TemporaryDirectory(prefix="apg-promotion-oracle-") as temporary:
        work = Path(temporary).resolve()
        _write_files(work, files)
        environment = _closed_environment(work, executable, command_name if command_name == "go" else "python")
        version = None
        if command_name == "go" and "-json" in spec.command:
            probe = subprocess.run([str(executable), "version"], cwd=work, env=environment,
                                   capture_output=True, timeout=COMMAND_TIMEOUT_SECONDS, check=True)
            version = probe.stdout.decode("utf-8", "replace").strip()
        completed = subprocess.run(command, cwd=work, env=environment, capture_output=True,
                                   timeout=COMMAND_TIMEOUT_SECONDS, check=False)
        completed.apg_runner_version = version
        hidden_execution.capture(spec, completed, work)
        receipt = _command_receipt_from_completed(spec, completed, command, expected, str(work))
        if spec.attestation_report:
            receipt["hidden_execution_artifact"] = getattr(completed, "apg_hidden_report", b"").decode("utf-8", "replace")
        return receipt


def _source_receipt(spec: FixtureSpec, files: Mapping[str, str], expected: str) -> dict[str, object]:
    observed = _source_check(spec, files)
    status = "pass" if observed else "fail"
    if status != expected:
        raise PromotionOracleError(f"{spec.case_id} {expected} source fixture did not match")
    return {"case_id": spec.case_id, "fixture": expected, "status": status,
            "oracle_id": spec.oracle_id, "hidden_oracle_sha256": spec.hidden_oracle_sha256,
            "qualification_scope": "structural-only; semantic-non-use-not-evaluated"
            if spec.kind == "non-trigger" else "source-owned-structural-oracle",
            "facts_sha256": [hashlib.sha256(fact.encode()).hexdigest() for fact in spec.hidden_facts],
            "check": spec.check_name, "network": "configured_offline_not_os_enforced"}


def _case_directory(root: Path, case_id: str, variant: str) -> tuple[Path, Path, Path]:
    parts = case_id.split("/")
    if variant not in {"good", "bad"} or any(part in {"", ".", ".."} for part in parts):
        raise PromotionOracleError(f"unsafe fixture identity {case_id}/{variant}")
    directory = root / "fixtures" / Path(*parts) / variant
    subject = directory / "subject"
    evidence = directory / "evidence"
    subject.mkdir(parents=True, exist_ok=False, mode=0o700)
    evidence.mkdir(mode=0o700)
    return directory, subject, evidence


def _normalised_output(raw: bytes, root: Path) -> str:
    return raw.decode("utf-8", "replace").replace(str(root), "<fixture-root>")


def _durable_source_receipt(spec: FixtureSpec, files: Mapping[str, str], variant: str,
                            expected: str, root: Path) -> dict[str, object]:
    directory, subject, evidence = _case_directory(root, spec.case_id, variant)
    _write_files(subject, files)
    before = _fixture_inventory(subject)
    _write_private_json(evidence / "before-inventory.json", {"entries": before})
    observed = _source_check(spec, files)
    status = "pass" if observed else "fail"
    after = _fixture_inventory(subject)
    _write_private_json(evidence / "after-inventory.json", {"entries": after})
    receipt = {
        "schema": SCHEMA,
        "case_id": spec.case_id,
        "fixture": expected,
        "status": status,
        "oracle_id": spec.oracle_id,
        "hidden_oracle_sha256": spec.hidden_oracle_sha256,
        "qualification_scope": "structural-only; semantic-non-use-not-evaluated"
        if spec.kind == "non-trigger" else "source-owned-structural-oracle",
        "returncode": None,
        "stdout_bytes": 0,
        "stderr_bytes": 0,
        "stdout_sha256": hashlib.sha256(b"").hexdigest(),
        "stderr_sha256": hashlib.sha256(b"").hexdigest(),
        "stdout": "",
        "stderr": "",
        "command": None,
        "check": spec.check_name,
        "facts_sha256": [hashlib.sha256(fact.encode()).hexdigest() for fact in spec.hidden_facts],
        "subject_inventory_before": str((evidence / "before-inventory.json").relative_to(root)),
        "subject_inventory_after": str((evidence / "after-inventory.json").relative_to(root)),
        "subject_before_entries": len(before),
        "subject_after_entries": len(after),
        "network": "configured_offline_not_os_enforced",
        "evidence_root": str(directory.relative_to(root)),
    }
    _write_private_json(evidence / "receipt.json", receipt)
    if status != expected:
        raise PromotionOracleError(f"{spec.case_id} {expected} source fixture did not match")
    return receipt


def _durable_command_receipt(spec: FixtureSpec, files: Mapping[str, str], variant: str,
                             expected: str, root: Path, transaction: runtime_execution.RuntimeTransaction,
                             manifest: Mapping[str, Any]) -> dict[str, object]:
    if not spec.command:
        raise PromotionOracleError(f"command missing for {spec.case_id}")
    directory, subject, evidence = _case_directory(root, spec.case_id, variant)
    _write_files(subject, files)
    before = _fixture_inventory(subject)
    _write_private_json(evidence / "before-inventory.json", {"entries": before})
    runtime_names = _runtime_requirements(manifest, spec)
    runtime_name = runtime_names[spec.command[0]]
    executable = transaction.resolve(runtime_name)
    command = [executable, *spec.command[1:]]
    evaluation_root = directory / "oracle-evaluation"
    evaluation_root.mkdir(mode=0o700)
    evaluation_counter = 0
    observations: list[tuple[subprocess.CompletedProcess[bytes], Sequence[str], str | None]] = []

    def transaction_runner(run_spec: FixtureSpec, run_files: Mapping[str, str]):
        nonlocal evaluation_counter
        evaluation_counter += 1
        evaluation_dir = evaluation_root / str(evaluation_counter)
        evaluation_dir.mkdir(mode=0o700)
        _write_files(evaluation_dir, run_files)
        run_names = _runtime_requirements(manifest, run_spec)
        run_runtime = run_names[run_spec.command[0]]
        run_executable = transaction.resolve(run_runtime)
        run_command = [run_executable, *run_spec.command[1:]]
        try:
            completed = transaction.run(run_runtime, run_spec.command[1:], cwd=evaluation_dir,
                                        temp_root=root / "tmp", timeout=COMMAND_TIMEOUT_SECONDS, check=False)
            hidden_execution.capture(run_spec, completed, evaluation_dir)
            completed.apg_runner_version = manifest["runtimes"][run_runtime].get("version_stdout")
            observations.append((completed, run_command, str(evaluation_dir)))
            return completed, run_command, str(evaluation_dir)
        finally:
            shutil.rmtree(evaluation_dir)

    try:
        model_evaluation = evaluate_model_output(
            spec.case_id, files, {}, runner=transaction_runner
        )
    except Exception as error:
        after = _fixture_inventory(subject)
        _write_private_json(evidence / "after-inventory.json", {"entries": after})
        _write_private_json(evidence / "failure.json", {
            "schema": SCHEMA, "case_id": spec.case_id, "fixture": expected,
            "error_type": type(error).__name__, "error": str(error),
            "subject_inventory_before": str((evidence / "before-inventory.json").relative_to(root)),
            "subject_inventory_after": str((evidence / "after-inventory.json").relative_to(root)),
        })
        raise
    if model_evaluation.get("status") != expected:
        raise PromotionOracleError(
            f"{spec.case_id} {expected} source-owned model-output oracle returned "
            f"{model_evaluation.get('status')}"
        )
    if not observations:
        raise PromotionOracleError(f"{spec.case_id} hidden-oracle runner produced no observation")
    after = _fixture_inventory(subject)
    if before != after:
        raise PromotionOracleError(f"{spec.case_id} retained subject changed during oracle evaluation")
    completed, observed_command, observed_marker = observations[0]
    stdout_raw = completed.stdout
    stderr_raw = completed.stderr
    if len(stdout_raw) > MAX_STREAM_BYTES or len(stderr_raw) > MAX_STREAM_BYTES:
        raise PromotionOracleError(f"fixture output exceeds bound for {spec.case_id}")
    stdout_path = evidence / "stdout.bin"
    stderr_path = evidence / "stderr.bin"
    _write_private_bytes(stdout_path, stdout_raw)
    _write_private_bytes(stderr_path, stderr_raw)
    observation_receipts = [
        _command_receipt_from_completed(spec, observed, command_value, None, marker)
        for observed, command_value, marker in observations
    ]
    status = str(model_evaluation.get("status"))
    receipt = {
        "schema": SCHEMA,
        "case_id": spec.case_id,
        "fixture": expected,
        "status": status,
        "oracle_id": spec.oracle_id,
        "hidden_oracle_sha256": spec.hidden_oracle_sha256,
        "qualification_scope": "source-owned-hidden-oracle",
        "returncode": completed.returncode,
        "stdout_bytes": len(stdout_raw),
        "stderr_bytes": len(stderr_raw),
        "stdout_sha256": hashlib.sha256(stdout_raw).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr_raw).hexdigest(),
        "stdout": _normalised_output(stdout_raw, root),
        "stderr": _normalised_output(stderr_raw, root),
        "stdout_path": str(stdout_path.relative_to(root)),
        "stderr_path": str(stderr_path.relative_to(root)),
        "command_token": spec.command[0],
        "runtime_name": runtime_name,
        "command": list(observed_command),
        "cwd": str(evaluation_root.relative_to(root)),
        "subject_inventory_before": str((evidence / "before-inventory.json").relative_to(root)),
        "subject_inventory_after": str((evidence / "after-inventory.json").relative_to(root)),
        "subject_before_entries": len(before),
        "subject_after_entries": len(after),
        "network": "configured_offline_not_os_enforced",
        "evidence_root": str(directory.relative_to(root)),
        "subject_inventory_sha256": _subject_inventory_digest(before),
        "subject_path": str(subject.relative_to(root)),
        "runner_observation_count": len(observation_receipts),
        "runner_observations": observation_receipts,
        "execution_owner": "source-owned-hidden-oracle-runner",
        "model_evaluation": model_evaluation,
    }
    _write_private_json(evidence / "after-inventory.json", {"entries": after})
    _write_private_json(evidence / "receipt.json", receipt)
    return receipt


def _subject_metadata(spec: FixtureSpec, *, scope: str) -> dict[str, object]:
    return {
        "case_id": spec.case_id,
        "oracle_id": spec.oracle_id,
        "hidden_oracle_sha256": spec.hidden_oracle_sha256,
        "qualification_scope": scope,
    }


def _subject_inventory_digest(entries: Sequence[Mapping[str, object]]) -> str:
    raw = (json.dumps(list(entries), sort_keys=True, separators=(",", ":")) + "\n").encode()
    return hashlib.sha256(raw).hexdigest()


def _read_subject_directory(path: str | Path) -> tuple[dict[str, str], list[dict[str, Any]], list[dict[str, Any]]]:
    """Read a retained result tree while proving its bytes stay unchanged."""
    root = _private_directory(path)
    before = _fixture_inventory(root)
    files: dict[str, str] = {}
    for candidate in sorted(root.rglob("*")):
        if candidate.is_dir():
            continue
        relative = candidate.relative_to(root)
        try:
            files[str(relative)] = candidate.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise PromotionOracleError(f"retained subject is not UTF-8 text: {relative}") from exc
    after = _fixture_inventory(root)
    if before != after:
        raise PromotionOracleError("retained subject changed during oracle read")
    return files, before, after


def _run_subject_with_hidden_oracle(spec: FixtureSpec, files: Mapping[str, str],
                                    executable_paths: Mapping[str, str],
                                    runner: Callable[[FixtureSpec, Mapping[str, str]], tuple[subprocess.CompletedProcess[bytes], Sequence[str], str | None]] | None = None) -> dict[str, object]:
    """Apply the source-owned oracle to an unmodified model subject.

    The retained subject is copied into a fresh temporary directory by
    ``_command_receipt``.  Hidden tests are added under reserved names in that
    copy, so neither the model result nor the source registry is rewritten.
    """
    if spec.fixture_kind != "command":
        observed = _source_check(spec, files)
        result = _subject_metadata(
            spec,
            scope=("structural-only; semantic-non-use-not-evaluated"
                   if spec.kind == "non-trigger" else "source-owned-structural-oracle"),
        )
        result.update({"status": "pass" if observed else "fail", "fixture": "subject",
                       "check": spec.check_name})
        return result
    candidate = dict(files)
    overlay = _hidden_overlay(spec, files)
    candidate.update(overlay)
    run_spec, kind, expected = hidden_execution.prepare(spec, overlay, files)
    receipt = _command_receipt(run_spec, candidate, executable_paths, None, runner)
    if kind:
        raw = (receipt.get("hidden_execution_artifact", "") if kind == "pytest" else receipt["stdout"]).encode()
        attestation = hidden_execution.attest(kind, expected, raw, receipt["returncode"],
                                              receipt["command"], overlay, files)
        attestation["runtime_version"] = (receipt["runtime_version"] if kind == "go"
                                           else attestation["runner_version"])
        receipt["execution_attestation"] = attestation
        if not attestation["qualifying"]:
            receipt["status"] = "fail"
    if spec.case_id == "pytest-test-profile/positive/collection":
        receipt["visible_check_name_preserved"] = hidden_execution.collection_check_present(files)
        if not receipt["visible_check_name_preserved"]:
            receipt["status"] = "fail"
    receipt["fixture"] = "subject"
    receipt["subject_file_count"] = len(files)
    receipt["grading_custody"] = _grading_custody(files, candidate, {}, overlay)
    return receipt


def evaluate_subject(case_id: str, subject_files: Mapping[str, str],
                     executable_paths: Mapping[str, str], *,
                     runner: Callable[[FixtureSpec, Mapping[str, str]], tuple[subprocess.CompletedProcess[bytes], Sequence[str], str | None]] | None = None) -> dict[str, object]:
    """Evaluate one later model-visible subject using the source oracle.

    This is the explicit result API used by provider-free qualification and by
    later evidence import.  It returns a failing result for an incomplete
    starting subject; it does not turn that expected failure into an exception.
    """
    spec = spec_for(case_id)
    return _run_subject_with_hidden_oracle(spec, _safe_subject_files(subject_files), executable_paths, runner)


def evaluate_subject_directory(case_id: str, subject_root: str | Path,
                               executable_paths: Mapping[str, str]) -> dict[str, object]:
    """Grade exact retained result files and bind an unchanged inventory."""
    files, before, after = _read_subject_directory(subject_root)
    result = evaluate_model_output(case_id, files, executable_paths)
    final = _fixture_inventory(_private_directory(subject_root))
    if before != final:
        raise PromotionOracleError("retained subject changed during oracle evaluation")
    result.update({
        "subject_root": str(Path(subject_root)),
        "subject_inventory_before": before,
        "subject_inventory_after": final,
        "subject_inventory_sha256": _subject_inventory_digest(before),
        "subject_readback_unchanged": before == after == final,
    })
    return result


evaluate_model_output_directory = evaluate_subject_directory


def _grading_custody(candidate, graded, substitutions, overlay):
    """Retain identities of submitted bytes and every permitted grading delta."""
    def identities(files):
        return {name: hashlib.sha256(content.encode("utf-8")).hexdigest()
                for name, content in sorted(files.items())}
    controlled = {name: content for name, content in candidate.items() if name not in substitutions}
    preserved = all(graded.get(name) == content for name, content in controlled.items())
    if not preserved or set(graded) - set(candidate) - set(substitutions) - set(overlay):
        raise PromotionOracleError("candidate custody changed during grading")
    return {"candidate_before": identities(candidate),
            "candidate_controlled": identities(controlled),
            "graded_files": identities(graded),
            "implementation_substitutions": identities(substitutions),
            "hidden_nonconflicting_overlay": identities(overlay),
            "candidate_configuration_restored": False,
            "candidate_controlled_preserved": preserved}


def _evaluate_authored_tests(spec: FixtureSpec, subject_files: Mapping[str, str],
                             executable_paths: Mapping[str, str], *,
                             runner: Callable[[FixtureSpec, Mapping[str, str]], tuple[subprocess.CompletedProcess[bytes], Sequence[str], str | None]] | None = None) -> dict[str, object]:
    authored = _authored_test_files(spec, subject_files)
    result: dict[str, object] = _subject_metadata(spec, scope="source-owned-known-good-bad-implementations")
    # Collection configuration, not a filename heuristic, decides which tests run.
    result["conventional_test_file_count"] = len(authored)
    receipts: dict[str, object] = {}
    for variant in ("good", "bad"):
        source = spec.good_files if variant == "good" else spec.bad_files
        implementation = {name: source[name] for name in spec.implementation_paths}
        files = {**subject_files, **implementation}
        run_spec = authored_execution.prepare(spec, files) if spec.case_id == authored_execution.COLLECTION_CASE else spec
        receipt = _command_receipt(run_spec, files, executable_paths, None, runner)
        if spec.case_id == authored_execution.COLLECTION_CASE:
            receipt["authored_execution"] = authored_execution.attest(receipt, spec.command, files)
            receipt["authored_execution_artifact"] = receipt.pop("hidden_execution_artifact", "")
        receipt["grading_custody"] = _grading_custody(subject_files, files, implementation, {})
        receipts[variant] = receipt
    good = receipts["good"]
    bad = receipts["bad"]
    good_pass = isinstance(good, Mapping) and good.get("status") == "pass"
    bad_fail = isinstance(bad, Mapping) and bad.get("status") == "fail"
    stable = (authored_execution.discriminates(good, bad)
              if spec.case_id == authored_execution.COLLECTION_CASE else True)
    # A test set that passes against both implementations is vacuous for the
    # promotion decision.  A set that cannot run against the known-good
    # implementation is also incomplete, even if the bad run happens to fail.
    result.update({"status": "pass" if good_pass and bad_fail and stable else "fail",
                   "good": good, "bad": bad,
                   "vacuous": bool(good_pass and not bad_fail)})
    return result


def evaluate_model_output(case_id: str, subject_files: Mapping[str, str],
                          executable_paths: Mapping[str, str], *,
                          runner: Callable[[FixtureSpec, Mapping[str, str]], tuple[subprocess.CompletedProcess[bytes], Sequence[str], str | None]] | None = None) -> dict[str, object]:
    """Evaluate a retained later-model result without mutating that result.

    Test-profile tasks receive an additional source-owned known-good/known-bad
    implementation check for the model-authored tests.  Other command tasks
    use the hidden source-owned tests directly.  The returned status is a
    qualification observation, so an incomplete starting subject is reported
    as ``fail`` rather than being silently treated as a passing fixture.
    """
    spec = spec_for(case_id)
    files = _safe_subject_files(subject_files)
    hidden = _run_subject_with_hidden_oracle(spec, files, executable_paths, runner)
    result: dict[str, object] = _subject_metadata(
        spec,
        scope=("source-owned-known-good-bad-implementations"
        if spec.kind == "positive" and spec.skill_id in {"go-test-profile", "pytest-test-profile"}
               else hidden.get("qualification_scope", "source-owned-hidden-oracle")),
    )
    result["hidden_oracle"] = hidden
    if spec.kind == "positive" and spec.skill_id in {"go-test-profile", "pytest-test-profile"}:
        authored = _evaluate_authored_tests(spec, files, executable_paths, runner=runner)
        result["model_authored_tests"] = authored
        result["status"] = ("pass" if hidden.get("status") == "pass"
                             and authored.get("status") == "pass" else "fail")
    else:
        result["status"] = hidden.get("status", "fail")
    return result


def qualify_starting_subject(case_id: str, subject_files: Mapping[str, str],
                             executable_paths: Mapping[str, str], *,
                             runner: Callable[[FixtureSpec, Mapping[str, str]], tuple[subprocess.CompletedProcess[bytes], Sequence[str], str | None]] | None = None) -> dict[str, object]:
    """Classify the visible starting subject under its source-owned oracle."""
    result = evaluate_model_output(case_id, subject_files, executable_paths, runner=runner)
    if result.get("status") == "pass":
        # A source contract may already be satisfied by the visible
        # implementation (the writer case intentionally permits bounded
        # fail-fast contention).  Preserve that fact instead of inventing a
        # hidden technique requirement; later evidence still needs its own
        # task/result and guidance-use records.
        result["starting_subject"] = "source-oracle-complete"
        result["starting_failure_required"] = False
    else:
        result["starting_subject"] = "genuinely-incomplete-or-failing"
        result["starting_failure_required"] = True
    return result


def _qualify_fixture_variant(case_id: str, variant: str,
                             executable_paths: Mapping[str, str], *,
                             runner: Callable[[FixtureSpec, Mapping[str, str]], tuple[subprocess.CompletedProcess[bytes], Sequence[str], str | None]] | None = None) -> dict[str, object]:
    spec = spec_for(case_id)
    if variant not in {"good", "bad"}:
        raise PromotionOracleError(f"unknown fixture variant {variant}")
    files = qualification_files(spec, variant)
    result = evaluate_model_output(case_id, files, executable_paths, runner=runner)
    expected = "pass" if variant == "good" else "fail"
    if result.get("status") != expected:
        raise PromotionOracleError(
            f"{case_id} {variant} source-owned model-output oracle returned {result.get('status')}"
        )
    result.update({"fixture": expected, "fixture_variant": variant, "status": expected,
                   "network": "configured_offline_not_os_enforced"})
    return result


def run_fixture(case_id: str, variant: str, executable_paths: Mapping[str, str]) -> dict[str, object]:
    spec = spec_for(case_id)
    if variant not in ("good", "bad"):
        raise PromotionOracleError(f"unknown fixture variant {variant}")
    return _qualify_fixture_variant(case_id, variant, executable_paths)


def qualify_all_diagnostic(executable_paths: Mapping[str, str], *,
                           expected_inventory: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Run explicit-path fixtures for local diagnostics only.

    This compatibility path deliberately does not establish complete
    qualification: it has no sealed manifest transaction or durable evidence
    root.  APG166E qualification must call :func:`qualify_all` instead.
    """
    validate_registry(expected_inventory)
    receipts: list[dict[str, object]] = []
    for case_id in case_ids():
        receipts.append(run_fixture(case_id, "good", executable_paths))
        receipts.append(run_fixture(case_id, "bad", executable_paths))
    return {"schema": SCHEMA, "source_path": SOURCE_PATH, "source_sha256": source_sha256(),
            "qualification_mode": "diagnostic", "complete_qualification": False,
            "cases": len(case_ids()), "fixture_pairs": len(receipts) // 2,
            "receipts": receipts}


def qualify_all(sealed_runtime_manifest: Mapping[str, Any], fixture_root: str | Path, *,
                expected_inventory: Sequence[Mapping[str, object]] | None = None,
                starting_subject_cases: Sequence[Mapping[str, object]] | None = None) -> dict[str, object]:
    """Run all fixtures inside one sealed, durable runtime transaction."""
    _verify_complete_runtime(sealed_runtime_manifest)
    if expected_inventory is None:
        raise PromotionOracleError("preregistration inventory required")
    validate_registry(expected_inventory)
    root = _private_directory(fixture_root, create=not Path(fixture_root).exists())
    if any(root.iterdir()):
        raise PromotionOracleError("oracle fixture root must be empty before qualification")
    work = root / "transaction-work"
    home = root / "home"
    temporary = root / "tmp"
    for directory in (work, home, temporary, root / "fixtures"):
        directory.mkdir(mode=0o700)
    temporary_identity = temporary.stat()
    transaction = runtime_execution.begin(sealed_runtime_manifest, work_dir=work, home=home)
    receipts: list[dict[str, object]] = []
    starting_records: list[dict[str, object]] = []
    closed = False
    try:
        # begin() performs the pre-transaction revalidation.  Keep a digest in
        # the durable result without copying private manifest contents.
        before_digest = runtime_manifest.manifest_digest(transaction.revalidate())
        if starting_subject_cases is not None:
            starting_root = root / "starting-evaluation"
            starting_root.mkdir(mode=0o700)
            starting_counters: dict[str, int] = {}

            def starting_runner(run_spec: FixtureSpec, run_files: Mapping[str, str]):
                case_root = starting_root / Path(*run_spec.case_id.split("/"))
                counter = starting_counters.get(run_spec.case_id, 0) + 1
                starting_counters[run_spec.case_id] = counter
                evaluation_dir = case_root / str(counter)
                evaluation_dir.mkdir(parents=True, mode=0o700)
                _write_files(evaluation_dir, run_files)
                run_names = _runtime_requirements(sealed_runtime_manifest, run_spec)
                run_runtime = run_names[run_spec.command[0]]
                run_executable = transaction.resolve(run_runtime)
                run_command = [run_executable, *run_spec.command[1:]]
                try:
                    completed = transaction.run(
                        run_runtime, run_spec.command[1:], cwd=evaluation_dir,
                        temp_root=root / "tmp", timeout=COMMAND_TIMEOUT_SECONDS, check=False,
                    )
                    hidden_execution.capture(run_spec, completed, evaluation_dir)
                    completed.apg_runner_version = sealed_runtime_manifest["runtimes"][run_runtime].get("version_stdout")
                    return completed, run_command, str(evaluation_dir)
                finally:
                    shutil.rmtree(evaluation_dir)

            for entry in starting_subject_cases:
                if not isinstance(entry, Mapping):
                    raise PromotionOracleError("starting subject entry must be a mapping")
                case_id = entry.get("case_id")
                subject_files = entry.get("subject_files")
                if not isinstance(case_id, str) or not isinstance(subject_files, Mapping):
                    raise PromotionOracleError("starting subject entry is malformed")
                record = qualify_starting_subject(
                    case_id, subject_files, {}, runner=starting_runner
                )
                record["starting_runtime_scope"] = "sealed-runtime-transaction"
                starting_records.append(record)
        for case_id in case_ids():
            spec = spec_for(case_id)
            files = qualification_files(spec, "good")
            receipts.append(
                _durable_command_receipt(spec, files, "good", "pass", root, transaction, sealed_runtime_manifest)
                if spec.fixture_kind == "command"
                else _durable_source_receipt(spec, files, "good", "pass", root)
            )
            files = qualification_files(spec, "bad")
            receipts.append(
                _durable_command_receipt(spec, files, "bad", "fail", root, transaction, sealed_runtime_manifest)
                if spec.fixture_kind == "command"
                else _durable_source_receipt(spec, files, "bad", "fail", root)
            )
        checked_after = transaction.close()
        closed = True
        after_digest = runtime_manifest.manifest_digest(checked_after)
    except Exception:
        if not closed:
            try:
                transaction.close()
            except Exception:
                pass
        raise
    observed = temporary.lstat()
    if not stat.S_ISDIR(observed.st_mode) or (observed.st_dev, observed.st_ino) != (temporary_identity.st_dev, temporary_identity.st_ino):
        raise PromotionOracleError("oracle temporary root identity changed")
    # Pytest creates current-run symlinks in this exclusively owned scratch.
    # Keep receipts and subjects, but remove transient runner storage before seal.
    shutil.rmtree(temporary)
    transaction_receipt = {
        "status": "closed",
        "before_revalidated": True,
        "after_revalidated": True,
        "manifest_sha256": before_digest,
        "after_manifest_sha256": after_digest,
    }
    _write_private_json(root / "transaction.json", transaction_receipt)
    result = {"schema": SCHEMA, "source_path": SOURCE_PATH, "source_sha256": source_sha256(),
              "qualification_mode": "complete", "complete_qualification": True,
              "fixture_root": str(root), "runtime_transaction": transaction_receipt,
              "cases": len(case_ids()), "fixture_pairs": len(receipts) // 2,
              "receipts": receipts, "starting_subjects": starting_records,
              "starting_subject_count": len(starting_records)}
    # Keep the aggregate beside the per-fixture receipts.  Raw streams remain
    # in their own files and are referenced by each retained receipt.
    if starting_subject_cases is not None:
        from .starting_evidence import verify_all
        verify_all(result, starting_subject_cases, sealed_runtime_manifest)
    _write_private_json(root / "qualification.json", result)
    return result


def validate_registry(expected_inventory: Sequence[Mapping[str, object]]) -> None:
    """Compare the implementation registry to preregistration metadata.

    The caller must pass inventory parsed from the preregistration file.  A
    registry-derived list is rejected so a self-comparison cannot establish
    coverage.  Case digests are checked by the preregistration owner because
    the implementation registry has no authority over prompt/subject bytes.
    """
    if isinstance(expected_inventory, (str, bytes)):
        raise PromotionOracleError("preregistration inventory required; case IDs are not sufficient")
    if any(not isinstance(item, Mapping) for item in expected_inventory):
        raise PromotionOracleError("preregistration inventory entries must be mappings")
    expected = [dict(item) for item in expected_inventory]
    actual = [dict(item) for item in registry_inventory()]
    required = {"case_id", "skill_id", "kind", "oracle_id", "hidden_oracle_sha256",
                "fixture_kind", "fixture_contract"}
    if any(not isinstance(item.get("case_sha256"), str)
           or len(item["case_sha256"]) != 64
           or any(char not in "0123456789abcdef" for char in item["case_sha256"])
           for item in expected):
        raise PromotionOracleError("stale case digest in preregistration inventory")
    expected_ids = [item.get("case_id") for item in expected]
    actual_ids = [item.get("case_id") for item in actual]
    if len(expected_ids) != len(set(expected_ids)):
        raise PromotionOracleError("duplicate case ID in preregistration inventory")
    if len(actual_ids) != len(set(actual_ids)):
        raise PromotionOracleError("duplicate case ID in implementation registry")
    missing = sorted(set(expected_ids) - set(actual_ids))
    extra = sorted(set(actual_ids) - set(expected_ids))
    if missing or extra:
        raise PromotionOracleError(f"fixture inventory mismatch missing={missing} extra={extra}")
    expected_by_id = {item["case_id"]: item for item in expected}
    actual_by_id = {item["case_id"]: item for item in actual}
    for case_id in sorted(expected_by_id):
        left = expected_by_id[case_id]
        right = actual_by_id[case_id]
        for field in sorted(required - {"case_id"}):
            if left.get(field) != right.get(field):
                family = ("skill" if field == "skill_id" else
                          "kind" if field == "kind" else
                          "oracle identity" if field in {"oracle_id", "hidden_oracle_sha256"}
                          else "fixture contract")
                raise PromotionOracleError(f"{family} mismatch for {case_id}: {field}")
        if "case_sha256" in left and (len(left["case_sha256"]) != 64
                                       or any(char not in "0123456789abcdef" for char in left["case_sha256"].lower())):
            raise PromotionOracleError(f"stale case digest for {case_id}")
    for case_id in sorted(actual_by_id):
        spec = spec_for(case_id)
        if not spec.good_files or not spec.bad_files or not spec.hidden_facts:
            raise PromotionOracleError(f"incomplete fixture pair for {case_id}")
        if spec.fixture_kind == "command" and not spec.command:
            raise PromotionOracleError(f"command fixture lacks command for {case_id}")
        if spec.kind == "non-trigger" and spec.fixture_kind != "source_fact":
            raise PromotionOracleError(f"non-trigger fixture must be source fact for {case_id}")
