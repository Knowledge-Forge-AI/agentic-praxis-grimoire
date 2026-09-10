"""APG123 Maintained Browser UI Harness and Prerequisite Contract.

Manages synthetic local Chromium/Firefox/WebKit execution using exact Playwright 1.62.1.
Enforces fail-closed validation of runtime, Node binary identity, package root,
scratch ownership, network isolation, and deterministic positive/negative scenario receipts.

Explicit Disclaimer:
Evidence confirms browser DOM, rendering, and accessibility node characteristics;
makes NO screen reader audio or assistive technology conformance claim.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple
import uuid

# Explicit Disclaimers
BROWSER_CORROBORATION_DISCLAIMER: str = (
    "Evidence confirms browser DOM, rendering, and accessibility node characteristics; "
    "makes NO screen reader audio or assistive technology conformance claim."
)

# Identity Constants
EXPECTED_NODE_VERSION: str = "v22.22.2|darwin/arm64|12.4.254.21-node.39|1.51.0"
EXPECTED_NODE_SHA256: str = "b7fff29202c2d59eeff28c53588d2832323b45cb2e854ba29bea47ade37d8359"
EXPECTED_PLAYWRIGHT_VERSION: str = "1.62.1"

# Authority Constants
APG123_BROWSER_UI_AUTHORITY: str = "APG123-BROWSER-UI-QUALIFIED-RECEIPT"
APG125_BROWSER_RUNTIME_AUTHORITY: str = "APG125-BROWSER-RUNTIME-QUALIFIED-RECEIPT"
APG125_BROWSER_MIXED_AUTHORITY: str = "APG125-BROWSER-MIXED-QUALIFIED-RECEIPT"
FAMILY_TABLE_SCHEMA_VERSION: str = "1.0.0"
FAMILY_TABLE_AUTHORITY: str = "APG129-BROWSER-FAMILY-TABLE"

# Supported Engines & Groups
SUPPORTED_BROWSERS: Tuple[str, ...] = ("chromium", "firefox", "webkit")
SCENARIO_GROUPS: Tuple[str, ...] = (
    "all",
    "playwright",
    "accessibility",
    "svg",
    "browser_runtime",
    "browser-runtime",
    "apg123",
)

# Scenario Register Partitions
PLAYWRIGHT_SCENARIOS: Tuple[str, ...] = (
    "PW01", "PW02", "PW03", "PW04", "PW05",
    "PW06", "PW07", "PW08", "PW09", "PW10",
)
ACCESSIBILITY_SCENARIOS: Tuple[str, ...] = (
    "AX01", "AX02", "AX03", "AX04", "AX05", "AX06",
    "AX07", "AX08", "AX09", "AX10", "AX11",
)
SVG_SCENARIOS: Tuple[str, ...] = ("SVG01", "SVG02", "SVG03")
APG123_SCENARIOS: Tuple[str, ...] = PLAYWRIGHT_SCENARIOS + ACCESSIBILITY_SCENARIOS + SVG_SCENARIOS
BROWSER_RUNTIME_SCENARIOS: Tuple[str, ...] = (
    "BR01", "BR02", "BR03", "BR04", "BR05", "BR06", "BR07",
    "BR08", "BR09", "BR10", "BR11", "BR12", "BR13", "BR14",
)
ALL_SCENARIOS: Tuple[str, ...] = APG123_SCENARIOS + BROWSER_RUNTIME_SCENARIOS


class BrowserHarnessError(Exception):
    """Base error for APG123 browser UI harness failures."""

    def __init__(
        self,
        message: str,
        *,
        failure_evidence: Optional[Dict[str, Any]] = None,
        retained_path: Optional[Path] = None,
        original_class: Optional[str] = None,
        original_message: Optional[str] = None,
        bounded_cause: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.failure_evidence = failure_evidence
        self.retained_path = retained_path
        self.original_class = original_class
        self.original_message = original_message
        self.bounded_cause = bounded_cause


class BrowserHarnessPrerequisiteError(BrowserHarnessError):
    """Raised when environment or runtime prerequisites fail closed."""


class BrowserHarnessExecutionError(BrowserHarnessError):
    """Raised when harness execution or child process fails."""


class BrowserHarnessValidationError(BrowserHarnessError):
    """Raised when receipt data or scenario assertions are invalid."""


@dataclass(frozen=True)
class BrowserHarnessConfig:
    """Validated configuration for APG123 browser harness."""
    repo_root: Path
    scratch_root: Path
    node_executable: Path
    node_identity: str
    package_root: Path
    package_version: str
    browsers_path: Path


@dataclass
class BrowserHarnessReceipt:
    """Sanitized evaluation receipt from browser harness execution."""
    raw: Dict[str, Any]
    browsers: Dict[str, str] = field(default_factory=dict)
    summary: Dict[str, int] = field(default_factory=dict)
    scenarios: List[Dict[str, Any]] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)
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

    def get_scenario(self, scenario_id: str, browser: str) -> Optional[Dict[str, Any]]:
        for sc in self.scenarios:
            if sc.get("scenario_id") == scenario_id and sc.get("browser") == browser:
                return sc
        return None


def validate_scratch_root(scratch_path: Path, repo_root: Path, *, private: bool = False) -> Path:
    """Validate that scratch path is an absolute, non-symlink, external direct directory."""
    if not scratch_path.is_absolute():
        raise BrowserHarnessPrerequisiteError(f"Scratch path must be absolute: {scratch_path}")
    if scratch_path.is_symlink():
        raise BrowserHarnessPrerequisiteError(f"Scratch path must not be a symlink: {scratch_path}")
    try:
        resolved = scratch_path.resolve(strict=True)
        repo_resolved = repo_root.resolve(strict=True)
        info = scratch_path.lstat()
    except OSError as err:
        raise BrowserHarnessPrerequisiteError(f"Scratch root could not be resolved: {type(err).__name__}") from err

    if not resolved.is_dir():
        raise BrowserHarnessPrerequisiteError(f"Scratch path must be an existing directory: {scratch_path}")
    if resolved == repo_resolved or repo_resolved in resolved.parents or resolved in repo_resolved.parents:
        raise BrowserHarnessPrerequisiteError("Scratch root must be strictly outside the repository checkout")
    if private:
        import stat
        if hasattr(os, "getuid") and info.st_uid != os.getuid():
            raise BrowserHarnessPrerequisiteError(f"Scratch root must be caller-owned: {scratch_path}")
        if (stat.S_IMODE(info.st_mode) & 0o777) != 0o700:
            raise BrowserHarnessPrerequisiteError(f"Scratch root must be mode 0700, got: 0{stat.S_IMODE(info.st_mode):o}")
    return resolved


def validate_node_executable(node_path: Path, repo_root: Path) -> str:
    """Validate Node executable existence, digest, and runtime identity string."""
    if not node_path.is_absolute():
        raise BrowserHarnessPrerequisiteError(f"Node path must be absolute: {node_path}")
    if node_path.is_symlink():
        raise BrowserHarnessPrerequisiteError(f"Node path must not be a symlink: {node_path}")
    if not node_path.is_file() or not os.access(node_path, os.X_OK):
        raise BrowserHarnessPrerequisiteError(f"Node path must be an executable file: {node_path}")

    try:
        resolved = node_path.resolve(strict=True)
        repo_resolved = repo_root.resolve(strict=True)
    except OSError as err:
        raise BrowserHarnessPrerequisiteError(f"Node executable could not be resolved: {type(err).__name__}") from err

    if resolved == repo_resolved or repo_resolved in resolved.parents:
        raise BrowserHarnessPrerequisiteError("Node executable must be outside repository checkout")

    try:
        with resolved.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
    except OSError as err:
        raise BrowserHarnessPrerequisiteError(f"Failed to read Node binary digest: {type(err).__name__}") from err

    if digest != EXPECTED_NODE_SHA256:
        raise BrowserHarnessPrerequisiteError(
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
        raise BrowserHarnessPrerequisiteError(f"Failed to query Node identity: {err}") from err

    if identity != EXPECTED_NODE_VERSION:
        raise BrowserHarnessPrerequisiteError(
            f"Node runtime identity mismatch: expected {EXPECTED_NODE_VERSION}, got {identity}"
        )
    return identity


def validate_playwright_package(package_root: Path, repo_root: Path) -> str:
    """Validate that package_root contains exact Playwright 1.62.1 node_modules."""
    if not package_root.is_absolute():
        raise BrowserHarnessPrerequisiteError(f"Package root must be absolute: {package_root}")
    if not package_root.is_dir():
        raise BrowserHarnessPrerequisiteError(f"Package root must be an existing directory: {package_root}")

    try:
        resolved = package_root.resolve(strict=True)
        repo_resolved = repo_root.resolve(strict=True)
    except OSError as err:
        raise BrowserHarnessPrerequisiteError(f"Package root could not be resolved: {type(err).__name__}") from err

    if resolved == repo_resolved or repo_resolved in resolved.parents:
        raise BrowserHarnessPrerequisiteError("Package root must be outside repository checkout")

    pw_test_json = resolved / "node_modules" / "@playwright" / "test" / "package.json"
    pw_json = resolved / "node_modules" / "playwright" / "package.json"

    if not pw_test_json.is_file() or not pw_json.is_file():
        raise BrowserHarnessPrerequisiteError(f"Playwright packages not found in {resolved / 'node_modules'}")

    try:
        test_meta = json.loads(pw_test_json.read_text(encoding="utf-8"))
        pw_meta = json.loads(pw_json.read_text(encoding="utf-8"))
    except Exception as err:
        raise BrowserHarnessPrerequisiteError(f"Failed to read package manifest: {err}") from err

    v1 = test_meta.get("version")
    v2 = pw_meta.get("version")
    if v1 != EXPECTED_PLAYWRIGHT_VERSION or v2 != EXPECTED_PLAYWRIGHT_VERSION:
        raise BrowserHarnessPrerequisiteError(
            f"Playwright version mismatch: expected {EXPECTED_PLAYWRIGHT_VERSION}, got {v1} / {v2}"
        )
    return v1


def validate_browser_cache(browsers_path: Path) -> Dict[str, Path]:
    """Validate that browser cache directory contains chromium, firefox, and webkit builds."""
    if not browsers_path.is_dir():
        raise BrowserHarnessPrerequisiteError(f"Browser cache directory does not exist: {browsers_path}")

    found: Dict[str, Path] = {}
    for entry in browsers_path.iterdir():
        if not entry.is_dir():
            continue
        name = entry.name.lower()
        if name.startswith("chromium-") and "chromium" not in found:
            found["chromium"] = entry
        elif name.startswith("firefox-") and "firefox" not in found:
            found["firefox"] = entry
        elif name.startswith("webkit-") and "webkit" not in found:
            found["webkit"] = entry

    missing = set(SUPPORTED_BROWSERS) - set(found.keys())
    if missing:
        raise BrowserHarnessPrerequisiteError(
            f"Missing browser binaries in cache {browsers_path}: {sorted(missing)}"
        )
    return found


def observe_browser_harness_config(
    repo_root: Path,
    scratch_path: Optional[Path] = None,
    node_path: Optional[Path] = None,
    package_root: Optional[Path] = None,
    browsers_path: Optional[Path] = None,
) -> BrowserHarnessConfig:
    """Construct and validate BrowserHarnessConfig using parent prerequisite and explicit env only."""
    repo_root = repo_root.resolve(strict=True)

    if scratch_path is None:
        raw_scratch = os.environ.get("APG_PLAYWRIGHT_OWNED_SCRATCH_ROOT")
        if not raw_scratch:
            raise BrowserHarnessPrerequisiteError("set APG_PLAYWRIGHT_OWNED_SCRATCH_ROOT to an external direct directory")
        scratch_path = Path(raw_scratch)
    validated_scratch = validate_scratch_root(scratch_path, repo_root, private=True)

    if node_path is None:
        raw_node = os.environ.get("APG_JAVASCRIPT_NODE")
        if not raw_node:
            raise BrowserHarnessPrerequisiteError("set APG_JAVASCRIPT_NODE to the qualified Node executable")
        node_path = Path(raw_node)
    node_identity = validate_node_executable(node_path, repo_root)

    if package_root is None:
        raw_pkg = os.environ.get("APG_PLAYWRIGHT_PACKAGE_ROOT")
        if not raw_pkg:
            raise BrowserHarnessPrerequisiteError("set APG_PLAYWRIGHT_PACKAGE_ROOT to the Playwright package directory")
        package_root = Path(raw_pkg)
    pkg_version = validate_playwright_package(package_root, repo_root)

    if browsers_path is None:
        raw_browsers = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
        if not raw_browsers:
            raise BrowserHarnessPrerequisiteError("set PLAYWRIGHT_BROWSERS_PATH to the browser cache directory")
        browsers_path = Path(raw_browsers)
    validate_browser_cache(browsers_path)

    libexec_dir = str(repo_root / "libexec")
    if libexec_dir not in sys.path:
        sys.path.insert(0, libexec_dir)
    try:
        import apg_test  # noqa: E402
        import apg_playwright_runtime  # noqa: E402
        apg_test.validate_javascript_engine(repo_root)
        apg_playwright_runtime.validate(repo_root)
    except Exception as err:
        raise BrowserHarnessPrerequisiteError(f"Authoritative prerequisite validation failed: {err}") from err

    return BrowserHarnessConfig(
        repo_root=repo_root,
        scratch_root=validated_scratch,
        node_executable=node_path,
        node_identity=node_identity,
        package_root=package_root,
        package_version=pkg_version,
        browsers_path=browsers_path,
    )


def load_scenarios_register(fixtures_dir: Path) -> Dict[str, Any]:
    """Load and validate scenarios.json register file."""
    scenarios_file = fixtures_dir / "scenarios.json"
    if not scenarios_file.is_file():
        raise BrowserHarnessValidationError(f"scenarios.json not found in {fixtures_dir}")
    try:
        data = json.loads(scenarios_file.read_text(encoding="utf-8"))
    except Exception as err:
        raise BrowserHarnessValidationError(f"Invalid scenarios.json: {err}") from err

    scenario_ids = [s.get("id") for s in data.get("scenarios", [])]
    if len(scenario_ids) != len(ALL_SCENARIOS) or set(scenario_ids) != set(ALL_SCENARIOS):
        raise BrowserHarnessValidationError(
            f"Scenario register mismatch: expected {len(ALL_SCENARIOS)} scenarios, found {len(scenario_ids)}"
        )
    return data


def load_family_table(fixtures_dir: Path, table_filename: str = "family_table.json") -> Dict[str, Any]:
    """Load and validate family_table.json table file."""
    table_file = fixtures_dir / table_filename
    if not table_file.is_file():
        raise BrowserHarnessValidationError(f"{table_filename} not found in {fixtures_dir}")
    try:
        data = json.loads(table_file.read_text(encoding="utf-8"))
    except Exception as err:
        raise BrowserHarnessValidationError(f"Invalid {table_filename}: {err}") from err

    validate_family_table(data)
    return data


def validate_family_table(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate family table structure, schema version, uniqueness, and lack of ambiguity."""
    if not isinstance(data, dict):
        raise BrowserHarnessValidationError("Family table must be a dictionary")

    schema_version = data.get("schema_version")
    if schema_version != FAMILY_TABLE_SCHEMA_VERSION:
        raise BrowserHarnessValidationError(f"Unsupported family table schema_version: {schema_version}")

    authority = data.get("authority")
    if not authority or not isinstance(authority, str):
        raise BrowserHarnessValidationError("Family table missing valid authority")

    families = data.get("families")
    if not isinstance(families, list):
        raise BrowserHarnessValidationError("Family table families must be a list")

    seen_families: Set[str] = set()
    family_map: Dict[str, Dict[str, Any]] = {}
    group_to_family: Dict[str, str] = {}

    for fam in families:
        if not isinstance(fam, dict):
            raise BrowserHarnessValidationError("Family table family row must be a dictionary")
        f_id = fam.get("id")
        if not f_id or not isinstance(f_id, str):
            raise BrowserHarnessValidationError("Family table family row missing valid identifier")
        if f_id in seen_families:
            raise BrowserHarnessValidationError(f"Duplicate family registration in family table: {f_id}")
        seen_families.add(f_id)

        auth = fam.get("authority")
        if not auth or not isinstance(auth, str):
            raise BrowserHarnessValidationError(f"Family table missing valid authority for family: {f_id}")
        family_map[f_id] = fam

        fam_groups = fam.get("groups")
        if not isinstance(fam_groups, list):
            raise BrowserHarnessValidationError("Family groups must be a list")
        if isinstance(fam_groups, list):
            for grp in fam_groups:
                if not isinstance(grp, str) or not grp:
                    raise BrowserHarnessValidationError(f"Invalid group name in family {f_id}: {grp}")
                if grp in group_to_family:
                    raise BrowserHarnessValidationError(f"Duplicate or ambiguous group registration in family table: {grp}")
                group_to_family[grp] = f_id

    supported_mixes = data.get("supported_mixes", [])
    if "supported_mixes" in data:
        if not isinstance(supported_mixes, list):
            raise BrowserHarnessValidationError("Family table supported_mixes must be a list")
        seen_mix_sets: Set[FrozenSet[str]] = set()
        for mix in supported_mixes:
            if not isinstance(mix, dict):
                raise BrowserHarnessValidationError("Invalid supported_mixes row type: must be a dictionary")
            mix_auth = mix.get("authority")
            if not mix_auth or not isinstance(mix_auth, str):
                raise BrowserHarnessValidationError("supported_mixes row missing valid authority")
            mix_families = mix.get("families")
            if not isinstance(mix_families, list) or len(mix_families) == 0:
                raise BrowserHarnessValidationError("supported_mixes row families must be a non-empty list")
            mix_family_seen = set()
            for mf in mix_families:
                if not isinstance(mf, str) or not mf:
                    raise BrowserHarnessValidationError(f"supported_mixes contains invalid family identifier: {mf}")
                if mf not in seen_families:
                    raise BrowserHarnessValidationError(f"supported_mixes references unknown family: {mf}")
                if mf in mix_family_seen:
                    raise BrowserHarnessValidationError(f"Duplicate family in supported_mixes row: {mf}")
                mix_family_seen.add(mf)

            if len(mix_family_seen) == 1:
                single_fam = next(iter(mix_family_seen))
                raise BrowserHarnessValidationError(
                    f"Ambiguous family registration: singleton mix for family '{single_fam}' registered in supported_mixes"
                )

            mix_set = frozenset(mix_family_seen)
            if mix_set in seen_mix_sets:
                raise BrowserHarnessValidationError(f"Duplicate mix registration in family table: {sorted(mix_set)}")
            seen_mix_sets.add(mix_set)

    entries = data.get("entries")
    if not isinstance(entries, list):
        raise BrowserHarnessValidationError("Family table entries must be a list")

    seen_ids: Set[str] = set()

    for entry in entries:
        if not isinstance(entry, dict):
            raise BrowserHarnessValidationError("Invalid family table entry")
        sc_id = entry.get("id")
        grp = entry.get("group")
        fam = entry.get("family")

        if not sc_id or not isinstance(sc_id, str):
            raise BrowserHarnessValidationError("Family table entry missing valid id")
        if sc_id in seen_ids:
            raise BrowserHarnessValidationError(f"Duplicate scenario ID in family table: {sc_id}")
        seen_ids.add(sc_id)

        if not fam or fam not in seen_families:
            raise BrowserHarnessValidationError(f"Unknown family in family table for scenario {sc_id}: {fam}")
        if not grp or grp not in group_to_family:
            raise BrowserHarnessValidationError(f"Unknown group in family table for scenario {sc_id}: {grp}")
        if group_to_family[grp] != fam:
            raise BrowserHarnessValidationError(
                f"Mismatched group-to-family mapping for scenario {sc_id}: group '{grp}' belongs to family '{group_to_family[grp]}', not '{fam}'"
            )

    aliases = data.get("aliases")
    if not isinstance(aliases, dict):
        raise BrowserHarnessValidationError("Family table missing aliases definition")

    for alias_name, alias_ids in aliases.items():
        if not isinstance(alias_ids, list):
            raise BrowserHarnessValidationError(f"Alias {alias_name} in family table must be a list")
        alias_seen: Set[str] = set()
        for a_id in alias_ids:
            if a_id not in seen_ids:
                raise BrowserHarnessValidationError(f"Alias {alias_name} references unknown scenario ID: {a_id}")
            if a_id in alias_seen:
                raise BrowserHarnessValidationError(f"Duplicate scenario ID in alias {alias_name}: {a_id}")
            alias_seen.add(a_id)

    return data


def validate_family_table_and_register(family_table: Dict[str, Any], register: Dict[str, Any]) -> None:
    """Validate that family table and scenario register agree on all scenario IDs and groups."""
    validate_family_table(family_table)
    if not isinstance(register, dict) or not isinstance(register.get("scenarios"), list):
        raise BrowserHarnessValidationError("Invalid scenarios register")

    table_entries = {e["id"]: e for e in family_table["entries"]}
    register_scenarios = {}
    for s in register["scenarios"]:
        if not isinstance(s, dict) or not s.get("id"):
            raise BrowserHarnessValidationError("Invalid scenario record in register")
        if s["id"] in register_scenarios:
            raise BrowserHarnessValidationError(f"Duplicate scenario ID in register: {s['id']}")
        register_scenarios[s["id"]] = s

    if set(table_entries.keys()) != set(register_scenarios.keys()):
        raise BrowserHarnessValidationError(
            f"Family table and scenarios register disagree on scenario IDs: table has {len(table_entries)}, register has {len(register_scenarios)}"
        )

    for sc_id, entry in table_entries.items():
        reg_sc = register_scenarios[sc_id]
        if entry["group"] != reg_sc.get("group"):
            raise BrowserHarnessValidationError(
                f"Family table and scenarios register disagree on group for {sc_id}: table={entry['group']}, register={reg_sc.get('group')}"
            )


def resolve_scenario_family_authority(family_table: Dict[str, Any], target_scenarios: Tuple[str, ...]) -> str:
    """Resolve qualified receipt authority for a set of target scenarios using the validated family table."""
    if not target_scenarios:
        raise BrowserHarnessValidationError("Target scenarios must not be empty")

    seen = set()
    selected_families = set()
    entry_map = {e["id"]: e for e in family_table.get("entries", [])}

    for sc_id in target_scenarios:
        if sc_id in seen:
            raise BrowserHarnessValidationError(f"Duplicate scenario ID in selection: {sc_id}")
        seen.add(sc_id)

        entry = entry_map.get(sc_id)
        if not entry:
            raise BrowserHarnessValidationError(f"Unknown scenario ID in selection: {sc_id}")
        selected_families.add(entry["family"])

    families_raw = family_table.get("families", [])
    family_map = {}
    if isinstance(families_raw, list):
        for f in families_raw:
            f_id = f.get("id") or f.get("family") or f.get("name")
            if f_id:
                family_map[f_id] = f
    elif isinstance(families_raw, dict):
        family_map = families_raw

    if len(selected_families) == 1:
        fam = next(iter(selected_families))
        fam_entry = family_map.get(fam)
        if not fam_entry or not fam_entry.get("authority"):
            raise BrowserHarnessValidationError(f"Unknown family or missing authority for: {fam}")
        return fam_entry["authority"]

    supported_mixes = family_table.get("supported_mixes") or []
    for mix in supported_mixes:
        mix_fams = set(mix.get("families", []))
        if mix_fams == selected_families:
            mix_auth = mix.get("authority")
            if not mix_auth:
                raise BrowserHarnessValidationError(f"Missing authority for supported mix: {sorted(mix_fams)}")
            return mix_auth

    raise BrowserHarnessValidationError(f"Unsupported scenario family mix: {sorted(selected_families)}")


def validate_receipt(
    receipt_data: Dict[str, Any],
    expected_browsers: Tuple[str, ...],
    expected_scenarios: Tuple[str, ...],
    retained_on_disk: bool = False,
    fixtures_dir: Optional[Path] = None,
) -> BrowserHarnessReceipt:
    """Validate evaluation receipt schema, zero-skip, zero-failure, and scenario completeness."""
    if not expected_browsers or not expected_scenarios:
        raise BrowserHarnessValidationError("Filter expected_browsers and expected_scenarios must not be empty")

    if receipt_data.get("schema_version") != "1.0.0":
        raise BrowserHarnessValidationError(f"Unsupported receipt schema_version: {receipt_data.get('schema_version')}")

    authority = receipt_data.get("authority")
    if not authority or not isinstance(authority, str):
        raise BrowserHarnessValidationError("Receipt missing authority")

    base_dir = fixtures_dir or (Path(__file__).parents[1] / "fixtures/apg123-browser-ui")
    family_table = load_family_table(base_dir)
    register = load_scenarios_register(base_dir)

    # Validate table and register agreement inside validate_receipt
    validate_family_table_and_register(family_table, register)

    expected_authority = resolve_scenario_family_authority(family_table, expected_scenarios)

    if authority != expected_authority:
        raise BrowserHarnessValidationError(
            f"Receipt authority mismatch: expected {expected_authority}, got {authority}"
        )

    pkg = receipt_data.get("package", {})
    if pkg.get("name") != "@playwright/test" or pkg.get("version") != EXPECTED_PLAYWRIGHT_VERSION:
        raise BrowserHarnessValidationError(
            f"Receipt package identity mismatch: expected @playwright/test=={EXPECTED_PLAYWRIGHT_VERSION}, got {pkg}"
        )

    # Validate runtime hashes if runtime metadata is present
    runtime = receipt_data.get("runtime")
    if runtime is not None:
        if not isinstance(runtime, dict):
            raise BrowserHarnessValidationError("Receipt runtime metadata must be a dictionary")
        file_map = {
            "runner_sha256": base_dir / "runner.mjs",
            "register_sha256": base_dir / "scenarios.json",
            "table_sha256": base_dir / "family_table.json",
        }
        for h_key in ("runner_sha256", "register_sha256", "table_sha256"):
            h_val = runtime.get(h_key)
            if h_val is not None:
                if not isinstance(h_val, str) or len(h_val) != 64 or not all(c in "0123456789abcdefABCDEF" for c in h_val):
                    raise BrowserHarnessValidationError(f"Invalid digest format for runtime.{h_key}: {h_val}")
                target_file = file_map[h_key]
                if target_file.is_file():
                    expected_hash = hashlib.sha256(target_file.read_bytes()).hexdigest()
                    if h_val.lower() != expected_hash.lower():
                        raise BrowserHarnessValidationError(
                            f"Receipt runtime.{h_key} digest mismatch: expected {expected_hash}, got {h_val}"
                        )

    # Validate table metadata if present
    table_meta = receipt_data.get("table")
    if table_meta is not None:
        if not isinstance(table_meta, dict):
            raise BrowserHarnessValidationError("Receipt table metadata must be a dictionary")
        t_sha = table_meta.get("sha256")
        if t_sha is not None:
            if not isinstance(t_sha, str) or len(t_sha) != 64 or not all(c in "0123456789abcdefABCDEF" for c in t_sha):
                raise BrowserHarnessValidationError(f"Invalid digest format for table.sha256: {t_sha}")
            target_table = base_dir / "family_table.json"
            if target_table.is_file():
                expected_tbl_hash = hashlib.sha256(target_table.read_bytes()).hexdigest()
                if t_sha.lower() != expected_tbl_hash.lower():
                    raise BrowserHarnessValidationError(
                        f"Receipt table.sha256 digest mismatch: expected {expected_tbl_hash}, got {t_sha}"
                    )

    summary = receipt_data.get("summary", {})
    for key in ("total", "passed", "failed", "skipped"):
        val = summary.get(key)
        if type(val) is not int or isinstance(val, bool) or val < 0:
            raise BrowserHarnessValidationError(f"Invalid integer counter for summary.{key}: {val}")

    total = summary["total"]
    passed = summary["passed"]
    failed = summary["failed"]
    skipped = summary["skipped"]

    expected_total = len(expected_browsers) * len(expected_scenarios)
    if total != expected_total:
        raise BrowserHarnessValidationError(
            f"Receipt scenario count mismatch: expected {expected_total}, recorded {total}"
        )
    if passed != total or failed != 0 or skipped != 0:
        raise BrowserHarnessValidationError(
            f"Incomplete or failed scenario run: passed={passed}, failed={failed}, skipped={skipped}"
        )

    browsers = receipt_data.get("browsers", {})
    for b in expected_browsers:
        if b not in browsers or not isinstance(browsers[b], str) or not browsers[b]:
            raise BrowserHarnessValidationError(f"Receipt missing version string for browser: {b}")

    table_entry_map = {e["id"]: e for e in family_table["entries"]}
    register_scenario_map = {s["id"]: s for s in register["scenarios"]}
    scenarios = receipt_data.get("scenarios", [])
    seen: Set[Tuple[str, str]] = set()
    for sc in scenarios:
        sc_id = sc.get("scenario_id")
        grp = sc.get("group")
        b = sc.get("browser")

        if sc_id not in table_entry_map:
            raise BrowserHarnessValidationError(f"Unknown scenario ID in receipt: {sc_id}")
        if sc_id not in register_scenario_map:
            raise BrowserHarnessValidationError(f"Receipt scenario {sc_id} missing from scenarios register")

        expected_group = table_entry_map[sc_id]["group"]
        if not grp or grp != expected_group:
            raise BrowserHarnessValidationError(
                f"Scenario {sc_id} recorded group mismatch: expected {expected_group}, got {grp}"
            )
        if grp != register_scenario_map[sc_id].get("group"):
            raise BrowserHarnessValidationError(
                f"Scenario {sc_id} recorded group disagrees with register: expected {register_scenario_map[sc_id].get('group')}, got {grp}"
            )

        if (sc_id, b) in seen:
            raise BrowserHarnessValidationError(f"Duplicate scenario entry in receipt: ({sc_id}, {b})")
        seen.add((sc_id, b))

        if sc.get("status") != "passed":
            raise BrowserHarnessValidationError(f"Scenario {sc_id} did not pass: {sc}")

        assertions = sc.get("assertions")
        if not isinstance(assertions, list) or len(assertions) == 0:
            raise BrowserHarnessValidationError(f"Scenario {sc_id} has empty assertions")
        for a in assertions:
            if not isinstance(a, dict) or not a.get("name") or type(a.get("passed")) is not bool or a.get("passed") is not True:
                raise BrowserHarnessValidationError(f"Scenario {sc_id} contains invalid assertion record: {a}")

    expected_set = {(sc_id, b) for b in expected_browsers for sc_id in expected_scenarios}
    if seen != expected_set:
        raise BrowserHarnessValidationError(
            f"Scenario execution set mismatch: expected {sorted(expected_set)}, recorded {sorted(seen)}"
        )
    predicates = {row["id"]: row["assertions"] for row in register["scenarios"]}
    for scenario in scenarios:
        names = [assertion["name"] for assertion in scenario["assertions"]]
        if len(names) != len(set(names)) or set(names) != set(predicates[scenario["scenario_id"]]):
            raise BrowserHarnessValidationError("Scenario assertion set differs from maintained predicates")

    return BrowserHarnessReceipt(
        raw=receipt_data,
        browsers=browsers,
        summary=summary,
        scenarios=scenarios,
        artifacts=receipt_data.get("artifacts", []),
        retained_on_disk=retained_on_disk,
    )


def _extract_diagnostic(
    stderr: str, receipt_file: Optional[Path] = None
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Extract (original_class, original_message, bounded_cause) from receipt file or stderr."""
    orig_class = None
    orig_msg = None
    b_cause = None

    if receipt_file and receipt_file.is_file() and not receipt_file.is_symlink():
        try:
            raw_receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
            if isinstance(raw_receipt, dict):
                for sc in raw_receipt.get("scenarios", []):
                    if isinstance(sc, dict) and sc.get("status") == "failed":
                        err_details = sc.get("error_details")
                        if isinstance(err_details, dict):
                            orig_class = err_details.get("class")
                            orig_msg = err_details.get("message")
                            raw_cause = err_details.get("cause")
                            if isinstance(raw_cause, dict):
                                b_cause = raw_cause.get("message") or raw_cause.get("class")
                            elif raw_cause:
                                b_cause = str(raw_cause)
                        elif sc.get("error"):
                            orig_msg = str(sc.get("error"))
                        if orig_class or orig_msg:
                            break
        except Exception:
            pass

    if not orig_class and stderr:
        for line in stderr.splitlines():
            if "Runner fatal error:" in line:
                try:
                    payload = json.loads(line.split("Runner fatal error:", 1)[1].strip())
                    if isinstance(payload, dict):
                        orig_class = payload.get("class")
                        if not orig_msg:
                            orig_msg = payload.get("message")
                        if not b_cause:
                            raw_c = payload.get("cause")
                            if isinstance(raw_c, dict):
                                b_cause = raw_c.get("message") or raw_c.get("class")
                            elif raw_c:
                                b_cause = str(raw_c)
                except Exception:
                    pass
            elif ":" in line and any(line.strip().startswith(prefix) for prefix in ("Error:", "AbortError:", "TimeoutError:", "TypeError:", "ValueError:")):
                parts = line.strip().split(":", 1)
                if not orig_class:
                    orig_class = parts[0].strip()
                if not orig_msg:
                    orig_msg = parts[1].strip()

    return orig_class, orig_msg, b_cause


def sanitize_evidence_text(text: Any, max_len: int = 2000) -> str:
    """Sanitize and bound diagnostic strings, redacting sensitive paths and credentials."""
    if text is None:
        return ""
    str_val = str(text)
    home = os.environ.get("HOME")
    if home:
        str_val = str_val.replace(home, "<HOME>")
    scratch_root = os.environ.get("APG_PLAYWRIGHT_OWNED_SCRATCH_ROOT")
    if scratch_root:
        str_val = str_val.replace(scratch_root, "<SCRATCH_ROOT>")

    # URL userinfo
    str_val = re.sub(r"([a-zA-Z][a-zA-Z0-9+.-]*://)([^/\s@]+)@", r"\1<REDACTED>@", str_val)
    # Bearer tokens
    str_val = re.sub(r"(?i)\b(bearer\s+)[A-Za-z0-9_\-\.=]+", r"\1<REDACTED>", str_val)
    # auth/token/password assignments (quoted)
    str_val = re.sub(
        r"(?i)\b([a-z0-9_-]*(?:auth(?!ority)(?:orization)?|token|password|passwd|secret|credential)[a-z0-9_-]*\s*[:=]\s*)([\"'])(?:(?=(\\?))\3.)*?\2",
        r"\1\2<REDACTED>\2",
        str_val,
    )
    # auth/token/password assignments (unquoted)
    str_val = re.sub(
        r"(?i)\b([a-z0-9_-]*(?:auth(?!ority)(?:orization)?|token|password|passwd|secret|credential)[a-z0-9_-]*\s*[:=]\s*)(?![\"'])[^\s,;&]+",
        r"\1<REDACTED>",
        str_val,
    )

    if len(str_val) > max_len:
        str_val = str_val[:max_len] + "...[truncated]"
    return str_val


SECRET_KEY_PATTERN = re.compile(
    r"(?i)^[a-z0-9_-]*(?:auth(?!ority)(?:orization)?|token|password|passwd|secret|credential|api[_-]?key)[a-z0-9_-]*$"
)


def sanitize_evidence_structure(data: Any, max_depth: int = 5, seen: Optional[Set[int]] = None) -> Any:
    """Recursively sanitize structured evidence, redacting credentials and bounding depth/cycles."""
    if seen is None:
        seen = set()
    if data is None or isinstance(data, (int, float, bool)):
        return data
    if isinstance(data, str):
        return sanitize_evidence_text(data)

    if max_depth <= 0:
        return "<DEPTH_EXCEEDED>"

    obj_id = id(data)
    if obj_id in seen:
        return "<CIRCULAR_REFERENCE>"
    seen.add(obj_id)

    try:
        if isinstance(data, dict):
            sanitized_dict: Dict[str, Any] = {}
            for k, v in data.items():
                str_k = str(k)
                sanitized_k = sanitize_evidence_text(str_k, max_len=200)
                if SECRET_KEY_PATTERN.search(str_k) and not str_k.lower().startswith("authority"):
                    if isinstance(v, (str, int, float)):
                        sanitized_dict[sanitized_k] = "<REDACTED>"
                    else:
                        sanitized_dict[sanitized_k] = sanitize_evidence_structure(v, max_depth=max_depth - 1, seen=seen)
                else:
                    sanitized_dict[sanitized_k] = sanitize_evidence_structure(v, max_depth=max_depth - 1, seen=seen)
            return sanitized_dict
        elif isinstance(data, (list, tuple)):
            return [sanitize_evidence_structure(item, max_depth=max_depth - 1, seen=seen) for item in data]
        else:
            return sanitize_evidence_text(str(data))
    finally:
        seen.remove(obj_id)


def retain_failure_evidence(
    config: BrowserHarnessConfig,
    run_id: str,
    receipt_file: Path,
    returncode: Optional[int],
    stdout: str,
    stderr: str,
    error_msg: str,
) -> Tuple[Dict[str, Any], Path]:
    """Retain sanitized failure evidence in external scratch before run directory cleanup."""
    scratch_real = config.scratch_root.resolve(strict=True)
    evidence_dir = config.scratch_root / "evidence"

    # Avoid evidence_dir symlink/chmod following outside scratch; fail closed on indirect dir
    if evidence_dir.is_symlink():
        raise BrowserHarnessExecutionError(f"Evidence directory must not be a symlink: {evidence_dir}")
    if evidence_dir.exists():
        if evidence_dir.is_symlink():
            raise BrowserHarnessExecutionError(f"Evidence directory must not be a symlink: {evidence_dir}")
        if not evidence_dir.is_dir():
            raise BrowserHarnessExecutionError(f"Evidence directory must be a directory: {evidence_dir}")
        ev_real = evidence_dir.resolve(strict=True)
        if ev_real != (scratch_real / "evidence"):
            raise BrowserHarnessExecutionError(
                f"Evidence directory must be a direct path in scratch: {evidence_dir} -> {ev_real}"
            )
    else:
        evidence_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        if evidence_dir.is_symlink():
            raise BrowserHarnessExecutionError(f"Evidence directory must not be a symlink: {evidence_dir}")

    try:
        os.chmod(evidence_dir, 0o700, follow_symlinks=False)
    except (OSError, NotImplementedError):
        try:
            os.chmod(evidence_dir, 0o700)
        except OSError:
            pass

    retained_file = evidence_dir / f"{run_id}-failure.json"
    if retained_file.is_symlink():
        raise BrowserHarnessExecutionError(f"Retained evidence target must not be a symlink: {retained_file}")

    failure_receipt = None
    failed_scenarios = []

    if receipt_file.is_file() and not receipt_file.is_symlink():
        try:
            raw_receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
            if isinstance(raw_receipt, dict):
                failure_receipt = raw_receipt
                for sc in raw_receipt.get("scenarios", []):
                    if isinstance(sc, dict) and sc.get("status") == "failed":
                        failed_scenarios.append(sc)
        except Exception:
            pass

    orig_class, orig_msg, b_cause = _extract_diagnostic(stderr, receipt_file)
    if not orig_class:
        orig_class = "BrowserHarnessExecutionError"

    evidence: Dict[str, Any] = {
        "run_id": run_id,
        "returncode": returncode,
        "error_class": orig_class,
        "error_message": sanitize_evidence_text(orig_msg or error_msg),
        "bounded_cause": sanitize_evidence_text(b_cause) if b_cause else None,
        "failed_scenarios": sanitize_evidence_structure(failed_scenarios),
        "receipt": sanitize_evidence_structure(failure_receipt),
        "stdout": sanitize_evidence_text(stdout),
        "stderr": sanitize_evidence_text(stderr),
        "retained_path": os.fspath(retained_file),
    }

    # Exclusive retained file creation mode 0600
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(retained_file, flags, 0o600)
    try:
        with open(fd, "w", encoding="utf-8", closefd=True) as stream:
            stream.write(json.dumps(evidence, indent=2))
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        raise

    return evidence, retained_file


def cleanup_retained_failure_evidence(scratch_root: Path, run_id: str) -> int:
    """Clean up retained failure evidence for an exact run_id from scratch directory."""
    if not run_id or not isinstance(run_id, str):
        raise BrowserHarnessPrerequisiteError("run_id must be a non-empty string for evidence cleanup")
    if "/" in run_id or "\\" in run_id or ".." in run_id:
        raise BrowserHarnessPrerequisiteError(f"Invalid run_id for evidence cleanup: {run_id}")

    evidence_dir = scratch_root / "evidence"
    if not evidence_dir.is_dir() or evidence_dir.is_symlink():
        return 0

    target = evidence_dir / f"{run_id}-failure.json"
    if target.is_symlink():
        raise BrowserHarnessPrerequisiteError(f"Retained evidence must not be a symlink: {target}")
    if target.is_file():
        target.unlink()
        try:
            evidence_dir.rmdir()
        except OSError:
            pass
        return 1
    return 0


def execute_browser_harness(
    config: BrowserHarnessConfig,
    fixtures_dir: Path,
    browsers: Tuple[str, ...] = SUPPORTED_BROWSERS,
    group: str = "all",
    scenario_filter: Optional[Tuple[str, ...]] = None,
    keep_scratch: bool = False,
) -> BrowserHarnessReceipt:
    """Execute synthetic browser UI scenarios inside owned scratch directory and return receipt."""
    if group not in SCENARIO_GROUPS:
        raise BrowserHarnessExecutionError(f"Unknown scenario group: {group}")
    for b in browsers:
        if b not in SUPPORTED_BROWSERS:
            raise BrowserHarnessExecutionError(f"Unsupported browser: {b}")

    # Load and validate family table and register BEFORE execution
    family_table = load_family_table(fixtures_dir)
    register = load_scenarios_register(fixtures_dir)
    validate_family_table_and_register(family_table, register)

    table_entry_map = {e["id"]: e for e in family_table["entries"]}

    if scenario_filter is not None:
        if not scenario_filter or len(set(scenario_filter)) != len(scenario_filter) or any(sc not in table_entry_map for sc in scenario_filter):
            raise BrowserHarnessExecutionError("Scenario filter must contain distinct known IDs")
        target_scenarios = scenario_filter
    elif group == "all":
        target_scenarios = tuple(family_table["aliases"]["all"])
    elif group in family_table.get("aliases", {}):
        target_scenarios = tuple(family_table["aliases"][group])
    else:
        raise BrowserHarnessExecutionError(f"Unknown scenario group: {group}")

    # Resolve authority ONCE BEFORE execution
    expected_authority = resolve_scenario_family_authority(family_table, target_scenarios)

    run_id = f"run-{uuid.uuid4().hex[:10]}"
    run_dir = config.scratch_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        run_dir.chmod(0o700)
    except OSError:
        pass
    receipt_file = run_dir / "receipt.json"

    try:
        for item in fixtures_dir.iterdir():
            if item.name.startswith("."):
                continue
            dest = run_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

        runner_file = run_dir / "runner.mjs"
        if not runner_file.is_file():
            raise BrowserHarnessExecutionError(f"Runner script not found in {run_dir}")

        target_node_modules = config.package_root / "node_modules"
        symlink_node_modules = run_dir / "node_modules"
        if not symlink_node_modules.exists():
            symlink_node_modules.symlink_to(target_node_modules)

        cmd = [
            os.fspath(config.node_executable),
            os.fspath(runner_file),
            "--browsers", ",".join(browsers),
            "--group", group,
            "--scratch", os.fspath(run_dir),
            "--receipt", os.fspath(receipt_file),
            "--table", os.fspath(run_dir / "family_table.json"),
            "--register", os.fspath(run_dir / "scenarios.json"),
        ]
        if scenario_filter:
            cmd.extend(["--scenarios", ",".join(scenario_filter)])

        env = os.environ.copy()
        env["PLAYWRIGHT_BROWSERS_PATH"] = os.fspath(config.browsers_path)
        env["APG_PLAYWRIGHT_PACKAGE_ROOT"] = os.fspath(config.package_root)
        env["NODE_PATH"] = os.fspath(config.package_root / "node_modules")
        env["APG_REPOSITORY_ROOT"] = os.fspath(config.repo_root)
        env["NO_COLOR"] = "1"

        # Manage child in isolated process group: bounded TERM then KILL cleanup on failure
        proc = subprocess.Popen(
            cmd,
            cwd=run_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            start_new_session=True,
        )

        try:
            stdout, stderr = proc.communicate(timeout=180)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except OSError:
                pass
            try:
                stdout, stderr = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except OSError:
                    pass
                stdout, stderr = proc.communicate()
            evidence = None
            retained_file = None
            try:
                evidence, retained_file = retain_failure_evidence(
                    config=config,
                    run_id=run_id,
                    receipt_file=receipt_file,
                    returncode=-1,
                    stdout=stdout,
                    stderr=stderr,
                    error_msg="Harness execution timed out after 180s",
                )
            except Exception:
                pass
            raise BrowserHarnessExecutionError(
                f"Harness execution timed out after 180s:\n{stdout}\n{stderr}",
                failure_evidence=evidence,
                retained_path=retained_file,
                original_class="TimeoutExpired",
                original_message="Harness execution timed out after 180s",
            )
        except Exception as err:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                pass
            evidence = None
            retained_file = None
            try:
                evidence, retained_file = retain_failure_evidence(
                    config=config,
                    run_id=run_id,
                    receipt_file=receipt_file,
                    returncode=-1,
                    stdout="",
                    stderr=str(err),
                    error_msg=f"Harness process execution failed: {err}",
                )
            except Exception:
                pass
            raise BrowserHarnessExecutionError(
                f"Harness process execution failed: {err}",
                failure_evidence=evidence,
                retained_path=retained_file,
                original_class=type(err).__name__,
                original_message=str(err),
            ) from err

        if proc.returncode != 0:
            evidence = None
            retained_file = None
            orig_class = None
            orig_msg = None
            b_cause = None
            try:
                evidence, retained_file = retain_failure_evidence(
                    config=config,
                    run_id=run_id,
                    receipt_file=receipt_file,
                    returncode=proc.returncode,
                    stdout=stdout,
                    stderr=stderr,
                    error_msg=f"Runner exited with code {proc.returncode}",
                )
                orig_class = evidence.get("error_class")
                orig_msg = evidence.get("error_message")
                b_cause = evidence.get("bounded_cause")
            except Exception:
                orig_class, orig_msg, b_cause = _extract_diagnostic(stderr, receipt_file)
            raise BrowserHarnessExecutionError(
                f"Runner exited with code {proc.returncode}:\nSTDOUT: {stdout}\nSTDERR: {stderr}",
                failure_evidence=evidence,
                retained_path=retained_file,
                original_class=orig_class or "BrowserHarnessExecutionError",
                original_message=orig_msg or f"Runner exited with code {proc.returncode}",
                bounded_cause=b_cause,
            )

        if not receipt_file.is_file():
            evidence = None
            retained_file = None
            try:
                evidence, retained_file = retain_failure_evidence(
                    config=config,
                    run_id=run_id,
                    receipt_file=receipt_file,
                    returncode=proc.returncode,
                    stdout=stdout,
                    stderr=stderr,
                    error_msg=f"Runner did not create receipt file at {receipt_file}",
                )
            except Exception:
                pass
            raise BrowserHarnessExecutionError(
                f"Runner did not create receipt file at {receipt_file}",
                failure_evidence=evidence,
                retained_path=retained_file,
            )

        receipt_data = json.loads(receipt_file.read_text(encoding="utf-8"))

        # Verify all reported artifacts exist on disk before any cleanup
        artifacts_dir = run_dir / "artifacts"
        for art_name in receipt_data.get("artifacts", []):
            art_path = artifacts_dir / art_name
            if not art_path.is_file() or art_path.stat().st_size == 0:
                evidence = None
                retained_file = None
                try:
                    evidence, retained_file = retain_failure_evidence(
                        config=config,
                        run_id=run_id,
                        receipt_file=receipt_file,
                        returncode=proc.returncode,
                        stdout=stdout,
                        stderr=stderr,
                        error_msg=f"Artifact {art_name} missing or empty on disk at {art_path}",
                    )
                except Exception:
                    pass
                raise BrowserHarnessValidationError(
                    f"Artifact {art_name} missing or empty on disk at {art_path}",
                    failure_evidence=evidence,
                    retained_path=retained_file,
                )

        try:
            return validate_receipt(receipt_data, browsers, target_scenarios, retained_on_disk=keep_scratch, fixtures_dir=fixtures_dir)
        except BrowserHarnessValidationError as val_err:
            try:
                evidence, retained_file = retain_failure_evidence(
                    config=config,
                    run_id=run_id,
                    receipt_file=receipt_file,
                    returncode=proc.returncode,
                    stdout=stdout,
                    stderr=stderr,
                    error_msg=str(val_err),
                )
                val_err.failure_evidence = evidence
                val_err.retained_path = retained_file
            except Exception:
                pass
            raise

    finally:
        if not keep_scratch and run_dir.is_dir():
            try:
                shutil.rmtree(run_dir)
            except Exception:
                if sys.exc_info()[0] is None:
                    raise
