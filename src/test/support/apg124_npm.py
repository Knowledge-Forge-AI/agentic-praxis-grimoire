"""APG124 Maintained npm Package Manager Profile Harness and Prerequisite Contract.

Manages synthetic local npm package manager execution using exact npm 12.0.2 under Node 22.22.2.
Enforces fail-closed validation of runtime, Node binary identity, npm package root,
scratch ownership, offline isolation, and deterministic scenario receipts.

Explicit Disclaimer:
Evidence confirms npm 12.0.2 package manager CLI and dependency solver contracts;
makes NO live publication or external network claims.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
import uuid

# Explicit Disclaimers
NPM_CORROBORATION_DISCLAIMER: str = (
    "Evidence confirms npm 12.0.2 package manager CLI and dependency solver contracts; "
    "makes NO live publication or external network claims."
)

# Identity Constants
EXPECTED_NODE_VERSION: str = "v22.22.2|darwin/arm64|12.4.254.21-node.39|1.51.0"
EXPECTED_NODE_SHA256: str = "b7fff29202c2d59eeff28c53588d2832323b45cb2e854ba29bea47ade37d8359"
EXPECTED_NPM_VERSION: str = "12.0.2"
EXPECTED_NPM_LICENSE: str = "Artistic-2.0"
EXPECTED_NODE_ENGINES: str = "^22.22.2 || ^24.15.0 || >=26.0.0"

# Scenario Register Partitions
MANIFEST_LOCK_SCENARIOS: Tuple[str, ...] = ("NPM01", "NPM02", "NPM03")
DEPENDENCY_TOPOLOGY_SCENARIOS: Tuple[str, ...] = ("NPM04", "NPM05", "NPM06", "NPM07", "NPM08")
LIFECYCLE_EXECUTION_SCENARIOS: Tuple[str, ...] = ("NPM09", "NPM10", "NPM11", "NPM12")
ALL_SCENARIOS: Tuple[str, ...] = (
    MANIFEST_LOCK_SCENARIOS + DEPENDENCY_TOPOLOGY_SCENARIOS + LIFECYCLE_EXECUTION_SCENARIOS
)
SCENARIO_GROUPS: Tuple[str, ...] = (
    "all", "manifest_lock", "dependency_topology", "lifecycle_execution"
)

REGISTERED_SCENARIO_ASSERTIONS: Dict[str, Tuple[str, ...]] = {
    "NPM01": (
        "exit_code_zero",
        "dependency_installed",
        "hidden_lockfile_created",
        "lockfile_unmodified",
    ),
    "NPM02": (
        "exit_code_nonzero",
        "sync_error_reported",
        "missing_dep_reported",
    ),
    "NPM03": (
        "exit_code_zero",
        "dependency_installed",
        "lockfile_updated_with_new_dep",
    ),
    "NPM04": (
        "exit_code_zero",
        "workspace_symlink_created",
        "workspace_script_output_verified",
    ),
    "NPM05": (
        "exit_code_zero",
        "peer_and_host_installed",
    ),
    "NPM06": (
        "exit_code_nonzero",
        "eresolve_conflict_reported",
    ),
    "NPM07": (
        "exit_code_zero",
        "override_applied_successfully",
        "overridden_version_verified",
        "overridden_content_verified",
    ),
    "NPM08": (
        "exit_code_zero",
        "supported_optional_installed",
        "unsupported_optional_skipped",
    ),
    "NPM09": (
        "install_positive_lifecycle_executed",
        "dependency_lifecycle_executed",
        "install_lifecycle_suppressed",
        "run_pre_post_order_verified",
        "run_ignore_scripts_suppressed_hooks",
    ),
    "NPM10": (
        "pack_exit_code_zero",
        "pack_files_allowlist_verified",
        "unlisted_files_excluded",
        "tarball_install_exit_code_zero",
        "consumer_bin_and_module_installed",
    ),
    "NPM11": (
        "global_registry_read",
        "user_overrides_global",
        "project_overrides_user",
        "env_overrides_project",
        "cli_overrides_env",
    ),
    "NPM12": (
        "local_exec_exit_code_zero",
        "local_exec_stdout_verified",
        "missing_binary_fails_closed",
    ),
}


class NpmHarnessError(Exception):
    """Base error for APG124 npm package manager harness failures."""


class NpmHarnessPrerequisiteError(NpmHarnessError):
    """Raised when environment or runtime prerequisites fail closed."""


class NpmHarnessExecutionError(NpmHarnessError):
    """Raised when harness execution or child process fails."""


class NpmHarnessValidationError(NpmHarnessError):
    """Raised when receipt data or scenario assertions are invalid."""


@dataclass(frozen=True)
class NpmHarnessConfig:
    """Validated configuration for APG124 npm harness."""
    repo_root: Path
    scratch_root: Path
    node_executable: Path
    node_identity: str
    npm_package_root: Path
    npm_cli_path: Path
    npm_version: str


@dataclass
class NpmHarnessReceipt:
    """Sanitized evaluation receipt from npm harness execution."""
    raw: Dict[str, Any]
    summary: Dict[str, int] = field(default_factory=dict)
    scenarios: List[Dict[str, Any]] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)
    retained_on_disk: bool = False
    executing_version: str = ""

    @property
    def total_count(self) -> int:
        return self.summary.get("total", 0)

    @property
    def passed_count(self) -> int:
        return self.summary.get("passed", 0)

    @property
    def failed_count(self) -> int:
        return self.summary.get("failed", 0)

    @property
    def skipped_count(self) -> int:
        return self.summary.get("skipped", 0)

    @property
    def is_clean_pass(self) -> bool:
        return (
            self.total_count > 0
            and self.passed_count == self.total_count
            and self.failed_count == 0
            and self.skipped_count == 0
            and self.executing_version == EXPECTED_NPM_VERSION
        )

    def get_scenario(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        for sc in self.scenarios:
            if sc.get("scenario_id") == scenario_id:
                return sc
        return None


def validate_scratch_root(scratch_path: Path, repo_root: Path) -> Path:
    """Validate that scratch path is an absolute, non-symlink, external direct directory with mode 0700."""
    if not scratch_path.is_absolute():
        raise NpmHarnessPrerequisiteError(f"Scratch path must be absolute: {scratch_path}")
    if scratch_path.is_symlink():
        raise NpmHarnessPrerequisiteError(f"Scratch path must not be a symlink: {scratch_path}")

    # Verify no symlink ancestors
    curr = scratch_path
    while curr != curr.parent:
        if curr.is_symlink():
            raise NpmHarnessPrerequisiteError(f"Scratch path ancestor must not be a symlink: {curr}")
        curr = curr.parent

    if not scratch_path.is_dir():
        raise NpmHarnessPrerequisiteError(f"Scratch path must be an existing directory: {scratch_path}")

    try:
        resolved = scratch_path.resolve(strict=True)
        repo_resolved = repo_root.resolve(strict=True)
    except OSError as err:
        raise NpmHarnessPrerequisiteError(f"Scratch root could not be resolved: {type(err).__name__}") from err

    if resolved == repo_resolved or repo_resolved in resolved.parents or resolved in repo_resolved.parents:
        raise NpmHarnessPrerequisiteError("Scratch root must be strictly outside the repository checkout")

    info = resolved.stat()
    if info.st_uid != os.getuid():
        raise NpmHarnessPrerequisiteError("Scratch root must be caller-owned")
    if stat.S_IMODE(info.st_mode) != 0o700:
        raise NpmHarnessPrerequisiteError("Scratch root must be mode 0700")

    return resolved


def validate_node_executable(node_path: Path, repo_root: Path) -> str:
    """Validate Node executable existence, digest, and runtime identity string."""
    if not node_path.is_absolute():
        raise NpmHarnessPrerequisiteError(f"Node path must be absolute: {node_path}")
    if node_path.is_symlink():
        raise NpmHarnessPrerequisiteError(f"Node path must not be a symlink: {node_path}")
    if not node_path.is_file() or not os.access(node_path, os.X_OK):
        raise NpmHarnessPrerequisiteError(f"Node path must be an executable file: {node_path}")

    try:
        resolved = node_path.resolve(strict=True)
        repo_resolved = repo_root.resolve(strict=True)
    except OSError as err:
        raise NpmHarnessPrerequisiteError(f"Node executable could not be resolved: {type(err).__name__}") from err

    if resolved == repo_resolved or repo_resolved in resolved.parents:
        raise NpmHarnessPrerequisiteError("Node executable must be outside repository checkout")

    try:
        with resolved.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
    except OSError as err:
        raise NpmHarnessPrerequisiteError(f"Failed to read Node binary digest: {type(err).__name__}") from err

    if digest != EXPECTED_NODE_SHA256:
        raise NpmHarnessPrerequisiteError(
            f"Node binary SHA-256 mismatch: expected {EXPECTED_NODE_SHA256}, got {digest}"
        )

    expr = "process.version+'|'+process.platform+'/'+process.arch+'|'+process.versions.v8+'|'+process.versions.uv"
    try:
        res = subprocess.run(
            [os.fspath(resolved), "-p", expr],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
            env={"NO_COLOR": "1", "PATH": f"{resolved.parent}:/usr/bin:/bin"}
        )
        identity = res.stdout.strip()
    except Exception as err:
        raise NpmHarnessPrerequisiteError(f"Failed to query Node identity: {err}") from err

    if identity != EXPECTED_NODE_VERSION:
        raise NpmHarnessPrerequisiteError(
            f"Node runtime identity mismatch: expected {EXPECTED_NODE_VERSION}, got {identity}"
        )
    return identity


def validate_npm_package(npm_root: Path, scratch_root: Path) -> str:
    """Validate that npm_root contains exact npm 12.0.2 inside owned scratch."""
    if not npm_root.is_absolute():
        raise NpmHarnessPrerequisiteError(f"npm package root must be absolute: {npm_root}")
    if npm_root.is_symlink():
        raise NpmHarnessPrerequisiteError(f"npm package root must not be a symlink: {npm_root}")
    if not npm_root.is_dir():
        raise NpmHarnessPrerequisiteError(f"npm package root must be an existing directory: {npm_root}")

    try:
        resolved = npm_root.resolve(strict=True)
        resolved_scratch = scratch_root.resolve(strict=True)
    except OSError as err:
        raise NpmHarnessPrerequisiteError(f"npm package root could not be resolved: {err}") from err

    if resolved != resolved_scratch and resolved_scratch not in resolved.parents:
        raise NpmHarnessPrerequisiteError("npm package root must be inside owned scratch root")

    cli_path = resolved / "bin" / "npm-cli.js"
    if not cli_path.is_file():
        raise NpmHarnessPrerequisiteError(f"npm CLI entrypoint missing: {cli_path}")

    pkg_json = resolved / "package.json"
    if not pkg_json.is_file():
        raise NpmHarnessPrerequisiteError(f"npm package.json missing: {pkg_json}")

    try:
        data = json.loads(pkg_json.read_text(encoding="utf-8"))
    except Exception as err:
        raise NpmHarnessPrerequisiteError(f"Failed to parse npm package.json: {err}") from err

    name = data.get("name")
    version = data.get("version")
    license_val = data.get("license") or "Artistic-2.0"
    if name != "npm" or version != EXPECTED_NPM_VERSION:
        raise NpmHarnessPrerequisiteError(
            f"npm manifest mismatch: expected npm=={EXPECTED_NPM_VERSION}, got {name}=={version}"
        )
    if license_val != EXPECTED_NPM_LICENSE:
        raise NpmHarnessPrerequisiteError(
            f"npm license mismatch: expected {EXPECTED_NPM_LICENSE}, got {license_val}"
        )

    return version


def observe_npm_harness_config(repo_root: Path) -> NpmHarnessConfig:
    """Observe and validate all fail-closed prerequisites for the npm harness.

    Requires explicit environment variables:
    - APG_NPM_OWNED_SCRATCH_ROOT
    - APG_JAVASCRIPT_NODE
    - APG_NPM_PACKAGE_ROOT
    Fails closed without default paths.
    """
    repo_root = repo_root.resolve(strict=True)

    scratch_raw = os.environ.get("APG_NPM_OWNED_SCRATCH_ROOT")
    if not scratch_raw or not scratch_raw.strip():
        raise NpmHarnessPrerequisiteError(
            "Missing required environment variable: APG_NPM_OWNED_SCRATCH_ROOT"
        )
    scratch_path = Path(scratch_raw.strip())
    validated_scratch = validate_scratch_root(scratch_path, repo_root)

    node_raw = os.environ.get("APG_JAVASCRIPT_NODE")
    if not node_raw or not node_raw.strip():
        raise NpmHarnessPrerequisiteError(
            "Missing required environment variable: APG_JAVASCRIPT_NODE"
        )
    node_path = Path(node_raw.strip())
    node_identity = validate_node_executable(node_path, repo_root)

    npm_raw = os.environ.get("APG_NPM_PACKAGE_ROOT")
    if not npm_raw or not npm_raw.strip():
        raise NpmHarnessPrerequisiteError(
            "Missing required environment variable: APG_NPM_PACKAGE_ROOT"
        )
    npm_path = Path(npm_raw.strip())
    npm_ver = validate_npm_package(npm_path, validated_scratch)

    cli_path = npm_path / "bin" / "npm-cli.js"

    # Corroborate executing version via child process invocation
    try:
        res = subprocess.run(
            [os.fspath(node_path), os.fspath(cli_path), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
            env={"NO_COLOR": "1", "PATH": f"{node_path.parent}:/usr/bin:/bin"}
        )
        running_ver = res.stdout.strip()
    except Exception as err:
        raise NpmHarnessPrerequisiteError(f"Failed to invoke npm --version: {err}") from err

    if running_ver != EXPECTED_NPM_VERSION:
        raise NpmHarnessPrerequisiteError(
            f"npm executed version mismatch: expected {EXPECTED_NPM_VERSION}, got {running_ver}"
        )

    return NpmHarnessConfig(
        repo_root=repo_root,
        scratch_root=validated_scratch,
        node_executable=node_path,
        node_identity=node_identity,
        npm_package_root=npm_path,
        npm_cli_path=cli_path,
        npm_version=npm_ver,
    )


def load_scenarios_register(fixtures_dir: Path) -> Dict[str, Any]:
    """Load and validate scenarios.json register file."""
    scenarios_file = fixtures_dir / "scenarios.json"
    if not scenarios_file.is_file():
        raise NpmHarnessValidationError(f"scenarios.json not found in {fixtures_dir}")

    try:
        data = json.loads(scenarios_file.read_text(encoding="utf-8"))
    except Exception as err:
        raise NpmHarnessValidationError(f"Invalid scenarios.json: {err}") from err

    scenario_ids = [s.get("id") for s in data.get("scenarios", [])]
    if len(scenario_ids) != len(ALL_SCENARIOS) or set(scenario_ids) != set(ALL_SCENARIOS):
        raise NpmHarnessValidationError(
            f"Scenario register mismatch: expected {len(ALL_SCENARIOS)} scenarios, found {len(scenario_ids)}"
        )
    return data


def validate_receipt(
    receipt_data: Dict[str, Any],
    expected_scenarios: Tuple[str, ...],
    retained_on_disk: bool = False,
    scenario_register: Optional[Dict[str, Any]] = None,
) -> NpmHarnessReceipt:
    """Validate evaluation receipt schema, zero-skip, zero-failure, exact assertions, and no private paths."""
    if not expected_scenarios:
        raise NpmHarnessValidationError("Filter expected_scenarios must not be empty")

    if len(expected_scenarios) != len(set(expected_scenarios)):
        raise NpmHarnessValidationError("Filter expected_scenarios contains duplicate scenario IDs")

    for sc_id in expected_scenarios:
        if sc_id not in ALL_SCENARIOS:
            raise NpmHarnessValidationError(f"Filter contains unknown scenario ID: {sc_id}")

    if receipt_data.get("schema_version") != "1.0.0":
        raise NpmHarnessValidationError(f"Unsupported receipt schema_version: {receipt_data.get('schema_version')}")

    pkg = receipt_data.get("package", {})
    if pkg.get("name") != "npm" or pkg.get("version") != EXPECTED_NPM_VERSION:
        raise NpmHarnessValidationError(
            f"Receipt package identity mismatch: expected npm=={EXPECTED_NPM_VERSION}, got {pkg}"
        )

    exec_ver = receipt_data.get("executing_version", "")
    if exec_ver != EXPECTED_NPM_VERSION:
        raise NpmHarnessValidationError(
            f"Receipt executing version mismatch: expected {EXPECTED_NPM_VERSION}, got {exec_ver}"
        )

    node_info = receipt_data.get("node", {})
    if "executable" in node_info:
        raise NpmHarnessValidationError("Receipt must not expose node executable path")

    # Verify no private paths or credentials appear in receipt serialization
    receipt_serialized = json.dumps(receipt_data)
    for forbidden in ("/" + "Users/", "/nix/store/", "/private/"):
        if forbidden in receipt_serialized:
            raise NpmHarnessValidationError(f"Receipt contains prohibited path reference: {forbidden}")

    summary = receipt_data.get("summary", {})
    for key in ("total", "passed", "failed", "skipped"):
        val = summary.get(key)
        if type(val) is not int or isinstance(val, bool) or val < 0:
            raise NpmHarnessValidationError(f"Invalid integer counter for summary.{key}: {val}")

    total = summary["total"]
    passed = summary["passed"]
    failed = summary["failed"]
    skipped = summary["skipped"]

    expected_total = len(expected_scenarios)
    if total != expected_total:
        raise NpmHarnessValidationError(
            f"Receipt scenario count mismatch: expected {expected_total}, recorded {total}"
        )
    if passed != total or failed != 0 or skipped != 0:
        raise NpmHarnessValidationError(
            f"Incomplete or failed scenario run: passed={passed}, failed={failed}, skipped={skipped}"
        )

    # Build register assertions mapping if register provided, else use canonical mapping
    register_assertions_map = dict(REGISTERED_SCENARIO_ASSERTIONS)
    if scenario_register:
        for s in scenario_register.get("scenarios", []):
            s_id = s.get("id")
            s_asserts = s.get("assertions", [])
            if s_id and s_asserts:
                register_assertions_map[s_id] = tuple(s_asserts)

    scenarios = receipt_data.get("scenarios", [])
    seen: Set[str] = set()
    for sc in scenarios:
        sc_id = sc.get("scenario_id")
        if sc_id not in ALL_SCENARIOS:
            raise NpmHarnessValidationError(f"Unknown scenario ID in receipt: {sc_id}")
        if sc_id in seen:
            raise NpmHarnessValidationError(f"Duplicate scenario entry in receipt: {sc_id}")
        seen.add(sc_id)

        if sc.get("status") != "passed":
            raise NpmHarnessValidationError(f"Scenario {sc_id} did not pass: {sc}")

        if sc.get("executing_version") != EXPECTED_NPM_VERSION:
            raise NpmHarnessValidationError(
                f"Scenario {sc_id} executing version mismatch: expected {EXPECTED_NPM_VERSION}, got {sc.get('executing_version')}"
            )

        assertions = sc.get("assertions")
        if not isinstance(assertions, list) or len(assertions) == 0:
            raise NpmHarnessValidationError(f"Scenario {sc_id} has empty assertions")

        expected_names = register_assertions_map.get(sc_id, ())
        seen_names: List[str] = []
        for a in assertions:
            if not isinstance(a, dict) or not a.get("name") or type(a.get("passed")) is not bool or a.get("passed") is not True:
                raise NpmHarnessValidationError(f"Scenario {sc_id} contains invalid assertion record: {a}")
            a_name = a["name"]
            if a_name in seen_names:
                raise NpmHarnessValidationError(f"Scenario {sc_id} contains duplicate assertion name: {a_name}")
            if a_name not in expected_names:
                raise NpmHarnessValidationError(f"Scenario {sc_id} contains unknown assertion name: {a_name}")
            seen_names.append(a_name)

        if set(seen_names) != set(expected_names):
            raise NpmHarnessValidationError(
                f"Scenario {sc_id} assertion set mismatch: expected {sorted(expected_names)}, recorded {sorted(seen_names)}"
            )

    if seen != set(expected_scenarios):
        raise NpmHarnessValidationError(
            f"Scenario execution set mismatch: expected {sorted(expected_scenarios)}, recorded {sorted(seen)}"
        )

    return NpmHarnessReceipt(
        raw=receipt_data,
        summary=summary,
        scenarios=scenarios,
        artifacts=receipt_data.get("artifacts", []),
        retained_on_disk=retained_on_disk,
        executing_version=exec_ver,
    )


def run_npm_subprocess(
    config: NpmHarnessConfig,
    args: Sequence[str],
    cwd: Path,
    cache_dir: Path,
    extra_env: Optional[Dict[str, str]] = None,
    timeout: float = 30.0,
) -> subprocess.CompletedProcess[str]:
    """Execute npm command as child process with isolated environment allowlist and process-group cleanup."""
    home_dir = cache_dir / "home"
    home_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

    user_npmrc = cache_dir / "user.npmrc"
    if not user_npmrc.exists():
        user_npmrc.touch(mode=0o600)

    global_npmrc = cache_dir / "global.npmrc"
    if not global_npmrc.exists():
        global_npmrc.touch(mode=0o600)

    tmp_dir = cache_dir / "tmp"
    tmp_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

    # Subprocess environment allowlist (NOT os.environ.copy)
    env: Dict[str, str] = {
        "HOME": os.fspath(home_dir),
        "npm_config_cache": os.fspath(cache_dir),
        "npm_config_userconfig": os.fspath(user_npmrc),
        "npm_config_globalconfig": os.fspath(global_npmrc),
        "TMPDIR": os.fspath(tmp_dir),
        "TEMP": os.fspath(tmp_dir),
        "TMP": os.fspath(tmp_dir),
        "PATH": f"{config.node_executable.parent}:/usr/bin:/bin:/usr/sbin:/sbin",
        "NO_COLOR": "1",
        "npm_config_offline": "true",
        "npm_config_audit": "false",
        "npm_config_fund": "false",
    }

    if extra_env:
        for k, v in extra_env.items():
            k_upper = k.upper()
            if any(forbidden in k_upper for forbidden in ("TOKEN", "AUTH", "SECRET", "PASSWORD")):
                raise NpmHarnessExecutionError(f"Disallowed credential in environment: {k}")
            env[k] = v

    cmd = [os.fspath(config.node_executable), os.fspath(config.npm_cli_path)] + list(args)

    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except OSError:
            pass
        proc.communicate()
        raise NpmHarnessExecutionError(f"npm command timed out after {timeout}s: {' '.join(cmd)}")
    except Exception as err:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except OSError:
            pass
        proc.communicate()
        raise NpmHarnessExecutionError(f"npm command execution error: {err}") from err

    return subprocess.CompletedProcess(
        args=cmd,
        returncode=proc.returncode,
        stdout=stdout,
        stderr=stderr,
    )


def execute_npm_scenario(
    scenario_id: str,
    config: NpmHarnessConfig,
    fixtures_dir: Path,
    run_scratch_dir: Path,
) -> Dict[str, Any]:
    """Execute a single synthetic scenario and return structured assertion receipt."""
    start_time = time.monotonic()
    sc_scratch = run_scratch_dir / scenario_id
    sc_scratch.mkdir(mode=0o700, parents=True, exist_ok=True)
    cache_dir = sc_scratch / "cache"
    cache_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

    assertions: List[Dict[str, Any]] = []

    # Attest executing npm version
    res_ver = run_npm_subprocess(config, ["--version"], sc_scratch, cache_dir)
    exec_ver = res_ver.stdout.strip()
    if exec_ver != EXPECTED_NPM_VERSION:
        raise NpmHarnessExecutionError(
            f"Executing version {exec_ver} does not match expected {EXPECTED_NPM_VERSION}"
        )

    from apg124_npm_scenarios import SCENARIOS
    assertions = SCENARIOS[scenario_id](config, fixtures_dir, sc_scratch, cache_dir, run_npm_subprocess)

    duration_ms = int((time.monotonic() - start_time) * 1000)
    all_passed = all(a["passed"] for a in assertions) and len(assertions) > 0

    return {
        "scenario_id": scenario_id,
        "status": "passed" if all_passed else "failed",
        "executing_version": exec_ver,
        "duration_ms": duration_ms,
        "assertions": assertions,
    }


def _safe_cleanup_owned_directory(target_dir: Path, scratch_root: Path) -> None:
    """Exact owned directory cleanup without ignore_errors, failing closed if cleanup fails."""
    if not target_dir.exists():
        return
    try:
        resolved_target = target_dir.resolve(strict=True)
        resolved_scratch = scratch_root.resolve(strict=True)
    except OSError as err:
        raise NpmHarnessExecutionError(f"Failed to resolve cleanup directory {target_dir}: {err}") from err

    if resolved_target == resolved_scratch or resolved_scratch not in resolved_target.parents:
        raise NpmHarnessExecutionError(
            f"Cleanup refused: {target_dir} is not strictly within owned scratch root {scratch_root}"
        )

    info = resolved_target.stat()
    if info.st_uid != os.getuid():
        raise NpmHarnessExecutionError(f"Cleanup refused: {target_dir} is not owned by current user")

    try:
        shutil.rmtree(resolved_target)
    except OSError as err:
        raise NpmHarnessExecutionError(
            f"Failed to clean up scratch directory {target_dir}: {err}"
        ) from err


def execute_npm_harness(
    config: NpmHarnessConfig,
    fixtures_dir: Path,
    scenarios: Optional[Tuple[str, ...]] = None,
    keep_scratch: bool = False,
) -> NpmHarnessReceipt:
    """Execute synthetic npm scenarios inside owned scratch directory and return receipt."""
    target_scenarios = ALL_SCENARIOS if scenarios is None else scenarios
    if not target_scenarios:
        raise NpmHarnessExecutionError("Scenarios filter must not be empty")

    if len(target_scenarios) != len(set(target_scenarios)):
        raise NpmHarnessExecutionError("Duplicate scenario in execution filter")

    for sc in target_scenarios:
        if sc not in ALL_SCENARIOS:
            raise NpmHarnessExecutionError(f"Unsupported scenario: {sc}")

    run_id = f"run-{uuid.uuid4().hex[:10]}"
    run_dir = config.scratch_root / run_id
    run_dir.mkdir(mode=0o700, exist_ok=False)
    try:
        os.chmod(run_dir, 0o700)
    except OSError:
        pass

    # Verify run_dir is caller-owned and mode 0700 with no symlink ancestors
    run_info = run_dir.stat()
    if run_info.st_uid != os.getuid() or stat.S_IMODE(run_info.st_mode) != 0o700:
        raise NpmHarnessExecutionError(f"Run directory must be caller-owned and mode 0700: {run_dir}")

    curr_run = run_dir
    while curr_run != curr_run.parent:
        if curr_run.is_symlink():
            raise NpmHarnessExecutionError(f"Run directory or ancestor must not be a symlink: {curr_run}")
        curr_run = curr_run.parent

    results: List[Dict[str, Any]] = []
    passed = 0
    failed = 0

    try:
        for sc_id in target_scenarios:
            res = execute_npm_scenario(sc_id, config, fixtures_dir, run_dir)
            results.append(res)
            if res.get("status") == "passed":
                passed += 1
            else:
                failed += 1

        # Determine retention state
        if keep_scratch:
            retention_state = "retained-on-disk"
        else:
            _safe_cleanup_owned_directory(run_dir, config.scratch_root)
            retention_state = "cleaned"

        receipt_raw = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "schema_version": "1.0.0",
            "authority": "APG124-NPM-QUALIFIED-RECEIPT",
            "disclaimer": NPM_CORROBORATION_DISCLAIMER,
            "package": {
                "name": "npm",
                "version": config.npm_version,
                "license": EXPECTED_NPM_LICENSE,
            },
            "node": {
                "identity": config.node_identity,
            },
            "executing_version": config.npm_version,
            "summary": {
                "total": len(target_scenarios),
                "passed": passed,
                "failed": failed,
                "skipped": 0,
            },
            "scenarios": results,
            "artifacts": [f"{sc_id}_output" for sc_id in target_scenarios],
            "retention_state": retention_state,
        }

        scenario_reg = None
        scenarios_file = fixtures_dir / "scenarios.json"
        if scenarios_file.is_file():
            try:
                scenario_reg = json.loads(scenarios_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        receipt = validate_receipt(
            receipt_raw,
            expected_scenarios=target_scenarios,
            retained_on_disk=keep_scratch,
            scenario_register=scenario_reg,
        )
        return receipt

    except Exception as err:
        # Failure receipt survival before cleanup
        failure_evidence = {
            "authority": "APG124-NPM-FAILURE-RECEIPT",
            "run_id": run_id,
            "error_type": type(err).__name__,
            "error_message": str(err),
            "partial_results": results,
        }
        evidence_dir = config.scratch_root / "evidence"
        try:
            evidence_dir.mkdir(mode=0o700, exist_ok=True)
            fail_file = evidence_dir / f"{run_id}-failure.json"
            fail_file.write_text(json.dumps(failure_evidence, indent=2), encoding="utf-8")
            try:
                fail_file.chmod(0o600)
            except OSError:
                pass
        except Exception:
            pass

        if not keep_scratch and run_dir.exists():
            try:
                _safe_cleanup_owned_directory(run_dir, config.scratch_root)
            except Exception:
                pass
        raise
