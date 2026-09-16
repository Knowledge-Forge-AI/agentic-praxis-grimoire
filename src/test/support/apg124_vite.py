"""APG124 Maintained Vite 8.2.2 Toolchain Harness and Prerequisite Contract.

Manages synthetic local Vite 8.2.2 build and dev server execution with Rolldown 1.2.7.
Enforces fail-closed validation of runtime, Node binary identity, package root,
scratch ownership, loopback network isolation, and deterministic positive/negative
scenario receipts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple


# Provenance and Disclaimers
VITE_TOOLCHAIN_DISCLAIMER: str = (
    "Maintained executable Vite 8.2.2 toolchain scenarios; evidence verifies local "
    "build, serving, and configuration contracts without third-party framework or "
    "deployment claims."
)

# Identity Constants
EXPECTED_NODE_VERSION: str = "v22.22.2|darwin/arm64|12.4.254.21-node.39|1.51.0"
EXPECTED_NODE_SHA256: str = "b7fff29202c2d59eeff28c53588d2832323b45cb2e854ba29bea47ade37d8359"
EXPECTED_VITE_VERSION: str = "8.2.2"
EXPECTED_ROLLDOWN_VERSION: str = "1.2.7"

# Scenarios
ALL_SCENARIOS: Tuple[str, ...] = (
    "VITE01", "VITE02", "VITE03", "VITE04", "VITE05", "VITE06",
    "VITE07", "VITE08", "VITE09", "VITE10", "VITE11", "VITE12"
)


class ViteHarnessError(Exception):
    """Base error for APG124 Vite harness failures."""


class ViteHarnessPrerequisiteError(ViteHarnessError, ValueError):
    """Raised when environment or runtime prerequisites fail closed."""


class ViteHarnessExecutionError(ViteHarnessError):
    """Raised when harness execution or child process fails."""


class ViteHarnessValidationError(ViteHarnessError):
    """Raised when receipt data or scenario assertions are invalid."""


@dataclass(frozen=True)
class ViteHarnessConfig:
    """Validated configuration for APG124 Vite harness."""
    repo_root: Path
    scratch_root: Path
    node_executable: Path
    node_identity: str
    package_root: Path
    package_version: str
    rolldown_version: str


@dataclass
class ViteHarnessReceipt:
    """Sanitized evaluation receipt from Vite harness execution."""
    raw: Dict[str, Any]
    toolchain: Dict[str, str] = field(default_factory=dict)
    summary: Dict[str, int] = field(default_factory=dict)
    scenarios: List[Dict[str, Any]] = field(default_factory=list)
    retained_on_disk: bool = False

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
        )

    def get_scenario(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        for sc in self.scenarios:
            if sc.get("scenario_id") == scenario_id:
                return sc
        return None


def validate_scratch_root(scratch_path: Path, repo_root: Path, *, private: bool = True) -> Path:
    """Validate that scratch path is an absolute, non-symlink, external direct directory."""
    if not scratch_path.is_absolute():
        raise ViteHarnessPrerequisiteError(f"Scratch path must be absolute: {scratch_path}")
    if scratch_path.is_symlink():
        raise ViteHarnessPrerequisiteError(f"Scratch path must not be a symlink: {scratch_path}")
    try:
        resolved = scratch_path.resolve(strict=True)
        repo_resolved = repo_root.resolve(strict=True)
        info = scratch_path.lstat()
    except OSError as err:
        raise ViteHarnessPrerequisiteError(f"Scratch root could not be resolved: {type(err).__name__}") from err

    if not stat.S_ISDIR(info.st_mode):
        raise ViteHarnessPrerequisiteError(f"Scratch path must be an existing directory: {scratch_path}")
    if resolved == repo_resolved or repo_resolved in resolved.parents or resolved in repo_resolved.parents:
        raise ViteHarnessPrerequisiteError("Scratch root must be strictly outside the repository checkout")
    if private:
        if info.st_uid != os.getuid() or (stat.S_IMODE(info.st_mode) & 0o077):
            raise ViteHarnessPrerequisiteError(f"Scratch root {scratch_path} must be caller-owned and mode 0700")
    return resolved


def validate_node_executable(node_path: Path, repo_root: Path) -> str:
    """Validate Node executable existence, digest, and runtime identity string."""
    if not node_path.is_absolute():
        raise ViteHarnessPrerequisiteError(f"Node path must be absolute: {node_path}")
    if node_path.is_symlink():
        raise ViteHarnessPrerequisiteError(f"Node path must not be a symlink: {node_path}")
    if not node_path.is_file() or not os.access(node_path, os.X_OK):
        raise ViteHarnessPrerequisiteError(f"Node path must be an executable file: {node_path}")

    try:
        resolved = node_path.resolve(strict=True)
        repo_resolved = repo_root.resolve(strict=True)
    except OSError as err:
        raise ViteHarnessPrerequisiteError(f"Node executable could not be resolved: {type(err).__name__}") from err

    if resolved == repo_resolved or repo_resolved in resolved.parents:
        raise ViteHarnessPrerequisiteError("Node executable must be outside repository checkout")

    try:
        with resolved.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
    except OSError as err:
        raise ViteHarnessPrerequisiteError(f"Failed to read Node binary digest: {type(err).__name__}") from err

    if digest != EXPECTED_NODE_SHA256:
        raise ViteHarnessPrerequisiteError(
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
            env={"NO_COLOR": "1"}
        )
        identity = res.stdout.strip()
    except Exception as err:
        raise ViteHarnessPrerequisiteError(f"Failed to query Node identity: {err}") from err

    if identity != EXPECTED_NODE_VERSION:
        raise ViteHarnessPrerequisiteError(
            f"Node runtime identity mismatch: expected {EXPECTED_NODE_VERSION}, got {identity}"
        )
    return identity


def validate_vite_package(package_root: Path, scratch_root: Path, repo_root: Path) -> Dict[str, str]:
    """Validate that package_root contains exact Vite 8.2.2 and Rolldown 1.2.7 packages."""
    if not package_root.is_absolute():
        raise ViteHarnessPrerequisiteError(f"Package root must be absolute: {package_root}")
    if not package_root.is_dir():
        raise ViteHarnessPrerequisiteError(f"Package root must be an existing directory: {package_root}")

    try:
        resolved = package_root.resolve(strict=True)
        scratch_resolved = scratch_root.resolve(strict=True)
        repo_resolved = repo_root.resolve(strict=True)
    except OSError as err:
        raise ViteHarnessPrerequisiteError(f"Package root could not be resolved: {type(err).__name__}") from err

    if resolved == repo_resolved or repo_resolved in resolved.parents:
        raise ViteHarnessPrerequisiteError("Package root must be outside repository checkout")
    if scratch_resolved not in resolved.parents and resolved != scratch_resolved:
        raise ViteHarnessPrerequisiteError("Vite package root must be inside owned scratch")

    vite_pkg = resolved / "node_modules" / "vite" / "package.json"
    rolldown_pkg = resolved / "node_modules" / "rolldown" / "package.json"
    native_pkg = resolved / "node_modules" / "@rolldown" / "binding-darwin-arm64" / "package.json"

    if not vite_pkg.is_file() or not rolldown_pkg.is_file():
        raise ViteHarnessPrerequisiteError(f"Vite or Rolldown packages not found in {resolved / 'node_modules'}")

    try:
        v_meta = json.loads(vite_pkg.read_text(encoding="utf-8"))
        r_meta = json.loads(rolldown_pkg.read_text(encoding="utf-8"))
    except Exception as err:
        raise ViteHarnessPrerequisiteError(f"Failed to read package manifest: {err}") from err

    v_ver = v_meta.get("version")
    r_ver = r_meta.get("version")
    if v_ver != EXPECTED_VITE_VERSION:
        raise ViteHarnessPrerequisiteError(
            f"Vite version mismatch: expected {EXPECTED_VITE_VERSION}, got {v_ver}"
        )
    if r_ver != EXPECTED_ROLLDOWN_VERSION:
        raise ViteHarnessPrerequisiteError(
            f"Rolldown version mismatch: expected {EXPECTED_ROLLDOWN_VERSION}, got {r_ver}"
        )

    return {
        "vite_version": v_ver,
        "rolldown_version": r_ver,
        "native_binding_present": str(native_pkg.is_file()).lower()
    }


def validate_prerequisites(repo_root: Path) -> Dict[str, object]:
    """Fail closed before tests; mirrors apg_playwright_runtime.py validate contract."""
    scratch_raw = os.environ.get("APG_VITE_OWNED_SCRATCH_ROOT", "")
    if not scratch_raw:
        raise ViteHarnessPrerequisiteError("set APG_VITE_OWNED_SCRATCH_ROOT to an external direct directory")
    scratch_path = Path(scratch_raw)
    scratch_resolved = validate_scratch_root(scratch_path, repo_root, private=True)

    package_raw = os.environ.get("APG_VITE_PACKAGE_ROOT", "")
    if not package_raw:
        raise ViteHarnessPrerequisiteError("set APG_VITE_PACKAGE_ROOT to the Vite package root inside scratch")
    package_path = Path(package_raw)
    pkg_info = validate_vite_package(package_path, scratch_resolved, repo_root)

    node_raw = os.environ.get("APG_JAVASCRIPT_NODE", "")
    if not node_raw:
        raise ViteHarnessPrerequisiteError("set APG_JAVASCRIPT_NODE to the qualified Node executable")
    node_path = Path(node_raw)
    node_identity = validate_node_executable(node_path, repo_root)

    return {
        "package_version": pkg_info["vite_version"],
        "rolldown_version": pkg_info["rolldown_version"],
        "node_version": node_identity.split("|")[0],
        "execution_verified": False
    }


def observe_vite_harness_config(repo_root: Path) -> ViteHarnessConfig:
    """Observe and validate full runtime environment configuration."""
    scratch_raw = os.environ.get("APG_VITE_OWNED_SCRATCH_ROOT", "")
    if not scratch_raw:
        raise ViteHarnessPrerequisiteError("set APG_VITE_OWNED_SCRATCH_ROOT to an external direct directory")
    scratch_path = Path(scratch_raw)
    scratch_resolved = validate_scratch_root(scratch_path, repo_root, private=True)

    package_raw = os.environ.get("APG_VITE_PACKAGE_ROOT", "")
    if not package_raw:
        raise ViteHarnessPrerequisiteError("set APG_VITE_PACKAGE_ROOT to the Vite package root inside scratch")
    package_path = Path(package_raw)
    pkg_info = validate_vite_package(package_path, scratch_resolved, repo_root)

    node_raw = os.environ.get("APG_JAVASCRIPT_NODE", "")
    if not node_raw:
        raise ViteHarnessPrerequisiteError("set APG_JAVASCRIPT_NODE to the qualified Node executable")
    node_path = Path(node_raw)
    node_identity = validate_node_executable(node_path, repo_root)

    return ViteHarnessConfig(
        repo_root=repo_root.resolve(strict=True),
        scratch_root=scratch_resolved,
        node_executable=node_path.resolve(strict=True),
        node_identity=node_identity,
        package_root=package_path.resolve(strict=True),
        package_version=pkg_info["vite_version"],
        rolldown_version=pkg_info["rolldown_version"]
    )


def load_scenarios_register(fixtures_dir: Path) -> Dict[str, Any]:
    """Load scenarios.json register fixture from disk."""
    reg_path = fixtures_dir / "scenarios.json"
    if not reg_path.is_file():
        raise ViteHarnessValidationError(f"Scenarios register not found: {reg_path}")
    try:
        data = json.loads(reg_path.read_text(encoding="utf-8"))
    except Exception as err:
        raise ViteHarnessValidationError(f"Failed to parse scenarios register: {err}") from err

    if data.get("schema_version") != "1.0.0":
        raise ViteHarnessValidationError(f"Invalid scenarios schema version: {data.get('schema_version')}")
    if "scenarios" not in data or not isinstance(data["scenarios"], list):
        raise ViteHarnessValidationError("Register must contain 'scenarios' list")
    return data


def sanitize_diagnostic_text(text: Any, config: Optional[ViteHarnessConfig] = None, max_len: int = 2000) -> str:
    """Sanitize and bound diagnostic strings, redacting sensitive paths and limits."""
    if text is None:
        return ""
    str_val = str(text)
    home = os.environ.get("HOME")
    if home:
        str_val = str_val.replace(home, "<HOME>")
    if config:
        str_val = str_val.replace(os.fspath(config.scratch_root), "<SCRATCH_ROOT>")
        str_val = str_val.replace(os.fspath(config.repo_root), "<REPO_ROOT>")
    scratch_env = os.environ.get("APG_VITE_OWNED_SCRATCH_ROOT")
    if scratch_env:
        str_val = str_val.replace(scratch_env, "<SCRATCH_ROOT>")
    str_val = re.sub(r"/" + r"Users/[^\s:\"']+", "<REDACTED_USER_PATH>", str_val)
    str_val = re.sub(r"/nix/store/[^\s:\"']+", "<REDACTED_NIX_PATH>", str_val)
    if len(str_val) > max_len:
        str_val = str_val[:max_len] + "...[truncated]"
    return str_val


def validate_receipt(
    raw: Dict[str, Any],
    expected_scenarios: Optional[Sequence[str]] = None,
    fixtures_dir: Optional[Path] = None,
    register: Optional[Dict[str, Any]] = None
) -> ViteHarnessReceipt:
    """Validate raw receipt from runner execution against expected constraints."""
    if not isinstance(raw, dict):
        raise ViteHarnessValidationError("Raw receipt must be a JSON dictionary")

    if raw.get("schema_version") != "1.0.0":
        raise ViteHarnessValidationError(f"Invalid receipt schema version: {raw.get('schema_version')}")

    if "retained_on_disk" in raw and type(raw["retained_on_disk"]) is not bool:
        raise ViteHarnessValidationError("retained_on_disk must be a boolean")

    summary = raw.get("summary")
    if not isinstance(summary, dict):
        raise ViteHarnessValidationError("Receipt must contain a summary dictionary")

    for key in ("total", "passed", "failed", "skipped"):
        val = summary.get(key)
        if type(val) is not int or val < 0:
            raise ViteHarnessValidationError(f"Invalid integer counter for summary.{key}: {val}")

    total = summary["total"]
    passed = summary["passed"]
    failed = summary["failed"]
    skipped = summary["skipped"]

    if total == 0 or passed != total or failed != 0 or skipped != 0:
        raise ViteHarnessValidationError(
            f"Receipt indicates non-clean pass: total={total}, passed={passed}, failed={failed}, skipped={skipped}"
        )

    if expected_scenarios is not None and total != len(expected_scenarios):
        raise ViteHarnessValidationError(
            f"Receipt scenario count mismatch: expected {len(expected_scenarios)}, recorded {total}"
        )

    scenarios = raw.get("scenarios")
    if not isinstance(scenarios, list):
        raise ViteHarnessValidationError("Receipt must contain a scenarios list")

    if len(scenarios) != total:
        raise ViteHarnessValidationError("Mismatch between summary total and scenario count")

    if register is None and fixtures_dir is not None:
        register = load_scenarios_register(fixtures_dir)
    elif register is None:
        default_fixtures = Path(__file__).resolve().parent.parent / "fixtures" / "apg124-toolchain" / "vite"
        if default_fixtures.is_dir():
            register = load_scenarios_register(default_fixtures)

    predicates_map = {}
    if register and "scenarios" in register:
        predicates_map = {row["id"]: row["assertions"] for row in register["scenarios"]}

    seen_ids: Set[str] = set()
    for sc in scenarios:
        if not isinstance(sc, dict):
            raise ViteHarnessValidationError("Scenario item must be a dictionary")

        sc_id = sc.get("scenario_id")
        if sc_id not in ALL_SCENARIOS:
            raise ViteHarnessValidationError(f"Unknown scenario ID in receipt: {sc_id}")

        if sc_id in seen_ids:
            raise ViteHarnessValidationError(f"Duplicate scenario ID in receipt: {sc_id}")
        seen_ids.add(sc_id)

        if sc.get("status") != "passed":
            raise ViteHarnessValidationError(f"Scenario {sc_id} status is not passed: {sc.get('status')}")

        assertions = sc.get("assertions")
        if not isinstance(assertions, list) or len(assertions) == 0:
            raise ViteHarnessValidationError(f"Scenario {sc_id} has empty assertions list")

        assertion_names: List[str] = []
        for a in assertions:
            if not isinstance(a, dict):
                raise ViteHarnessValidationError(f"Scenario {sc_id} assertion record must be a dict: {a}")
            a_name = a.get("name")
            if not a_name or not isinstance(a_name, str):
                raise ViteHarnessValidationError(f"Scenario {sc_id} assertion missing name: {a}")
            passed_val = a.get("passed")
            if type(passed_val) is not bool or passed_val is not True:
                raise ViteHarnessValidationError(f"Scenario {sc_id} assertion failed or malformed bool: {a}")
            assertion_names.append(a_name)

        if len(assertion_names) != len(set(assertion_names)):
            raise ViteHarnessValidationError(f"Scenario {sc_id} contains duplicate assertions: {assertion_names}")

        if sc_id in predicates_map:
            expected_set = set(predicates_map[sc_id])
            if set(assertion_names) != expected_set:
                raise ViteHarnessValidationError(
                    f"Scenario {sc_id} assertion set differs from maintained register predicates: "
                    f"expected {sorted(expected_set)}, got {sorted(set(assertion_names))}"
                )

    if expected_scenarios is not None:
        missing = set(expected_scenarios) - seen_ids
        if missing:
            raise ViteHarnessValidationError(f"Missing required scenarios in receipt: {sorted(missing)}")

    identity = raw.get("toolchain", {})
    if identity.get("vite_version") != EXPECTED_VITE_VERSION or identity.get("node_version") != "v22.22.2" or identity.get("node_identity") != EXPECTED_NODE_VERSION:
        raise ViteHarnessValidationError("Receipt toolchain identity mismatch")
    if any(marker in json.dumps(raw) for marker in ("/" + "Users/", "/nix/store/", "/private/")):
        raise ViteHarnessValidationError("Receipt contains private paths")

    return ViteHarnessReceipt(
        raw=raw,
        toolchain=raw.get("toolchain", {}),
        summary=summary,
        scenarios=scenarios,
        retained_on_disk=raw.get("retained_on_disk", False)
    )


def execute_vite_harness(
    config: ViteHarnessConfig,
    fixtures_dir: Path,
    scenario_filter: Optional[Sequence[str]] = None
) -> ViteHarnessReceipt:
    """Execute runner.mjs and return validated receipt."""
    if scenario_filter is not None and (not scenario_filter or len(set(scenario_filter)) != len(scenario_filter) or any(s not in ALL_SCENARIOS for s in scenario_filter)):
        raise ViteHarnessExecutionError("Scenario filter must be nonempty, unique and known")
    fixtures_dir = fixtures_dir.resolve(strict=True)
    runner_path = (fixtures_dir / "runner.mjs").resolve(strict=True)
    if not runner_path.is_file():
        raise ViteHarnessExecutionError(f"Runner script not found: {runner_path}")

    cmd: List[str] = [
        os.fspath(config.node_executable),
        os.fspath(runner_path),
        "--scratch-root", os.fspath(config.scratch_root),
        "--package-root", os.fspath(config.package_root)
    ]
    if scenario_filter:
        cmd.extend(["--filter", ",".join(scenario_filter)])

    proc = subprocess.Popen(
        cmd,
        cwd=fixtures_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
        env={
            "HOME": os.fspath(config.scratch_root),
            "TMPDIR": os.fspath(config.scratch_root),
            "PATH": f"{config.node_executable.parent}:/usr/bin:/bin",
            "NO_COLOR": "1",
            "APG_VITE_OWNED_SCRATCH_ROOT": os.fspath(config.scratch_root),
            "APG_VITE_PACKAGE_ROOT": os.fspath(config.package_root)
        }
    )
    try:
        stdout, stderr = proc.communicate(timeout=60)
    except subprocess.TimeoutExpired as err:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except OSError:
            pass
        proc.communicate()
        raise ViteHarnessExecutionError("Vite harness execution timed out") from err
    except BaseException as err:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except OSError:
            pass
        proc.communicate()
        sanitized = sanitize_diagnostic_text(str(err), config)
        raise ViteHarnessExecutionError(f"Failed to execute Vite harness: {sanitized}") from err

    if proc.returncode != 0:
        sanitized_stderr = sanitize_diagnostic_text(stderr, config)
        sanitized_stdout = sanitize_diagnostic_text(stdout, config)
        raise ViteHarnessExecutionError(
            f"Vite harness exited with code {proc.returncode}:\n{sanitized_stderr}\n{sanitized_stdout}"
        )

    try:
        raw_receipt = json.loads(stdout)
    except json.JSONDecodeError as err:
        sanitized_out = sanitize_diagnostic_text(stdout, config)
        raise ViteHarnessExecutionError(
            f"Failed to parse runner JSON receipt:\n{sanitized_out}\nError: {err}"
        ) from err

    return validate_receipt(
        raw_receipt,
        expected_scenarios=scenario_filter or ALL_SCENARIOS,
        fixtures_dir=fixtures_dir
    )
