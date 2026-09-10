"""APG-owned pytest, xdist, mirror, and exact coverage runner."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path, PurePosixPath
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Callable, NoReturn, Sequence


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
EXPECTED_TYPESCRIPT_VERSION = "Version 7.0.2"
EXPECTED_JAVASCRIPT_ENGINE = "v22.22.2|darwin/arm64|12.4.254.21-node.39"
EXPECTED_JAVASCRIPT_ENGINE_SHA256 = (
    "b7fff29202c2d59eeff28c53588d2832323b45cb2e854ba29bea47ade37d8359"
)
EXPECTED_JAVASCRIPT_ENGINE_ROOT = Path("/nix/store")
EXPECTED_JAVASCRIPT_ENGINE_UID = 0
NODE_PROFILE_RUNTIME_TEST_PATHS = frozenset(
    {
        "src/test/int/python/agentic-praxis-grimoire/skills/nodejs-runtime-profile/SKILL.int.test.py",
    }
)
NODE_PROFILE_RUNTIME_CONTRACTS = {
    "primary": (
        "APG_NODEJS_PRIMARY_NODE",
        "v22.22.2|darwin/arm64|12.4.254.21-node.39|1.51.0",
        "b7fff29202c2d59eeff28c53588d2832323b45cb2e854ba29bea47ade37d8359",
    ),
    "secondary": (
        "APG_NODEJS_SECONDARY_NODE",
        "v24.19.0|darwin/arm64|13.6.233.17-node.51|1.52.1",
        "27db838bb204ef7c21df2931f5656e4c8fb32e6e947f363a402b49714d32b5b1",
    ),
}
NODE_PROFILE_ENVIRONMENT_KEYS = frozenset(
    {"NO_COLOR", "PNPM_HOME", "TEMP", "TMP", "TMPDIR", "npm_config_cache"}
)
_NODE_SCRATCH_RESULT = {
    "contentPreserved": True,
    "durabilityProven": False,
    "fileUrlProtocol": "file:",
    "missingCode": "ENOENT",
    "permissionPolicyProven": False,
    "roundTripEqual": True,
    "separator": "/",
}
NODE_PROFILE_OUTPUT_CONTRACTS = {
    "primary-commonjs-namespace": (0, "json-exact", "empty", ["alpha", "beta", "default"]),
    "secondary-commonjs-namespace": (0, "json-exact", "empty", ["alpha", "beta", "default", "module.exports"]),
    "primary-default-type-flag": (0, "json-exact", "empty", {"defaultType": True}),
    "secondary-default-type-flag": (0, "json-exact", "empty", {"defaultType": False}),
    "primary-explicit-commonjs-refusal": (1, "empty", "discard", None),
    "secondary-explicit-commonjs-refusal": (1, "empty", "discard", None),
    "primary-no-manifest-detection": (0, "json-exact", "empty", {"mapping": "module-only"}),
    "secondary-no-manifest-detection": (0, "json-exact", "empty", {"mapping": "module-only"}),
    "primary-owned-scratch": (0, "json-exact", "empty", _NODE_SCRATCH_RESULT),
    "secondary-owned-scratch": (0, "json-exact", "empty", _NODE_SCRATCH_RESULT),
    "primary-scratch-symlink-refusal": (0, "json-exact", "empty", {"refused": True}),
    "secondary-scratch-symlink-refusal": (0, "json-exact", "empty", {"refused": True}),
    "primary-typescript-erasable": (0, "json-exact", "empty", {"label": "erasable"}),
    "secondary-typescript-erasable": (0, "json-exact", "empty", {"label": "erasable"}),
    "primary-typescript-nonerasable": (1, "empty", "discard", None),
    "secondary-typescript-nonerasable": (1, "empty", "discard", None),
    "redaction-negative": (0, "json-exact", "empty", {"secret": "expected-safe-value"}),
}
TYPESCRIPT_COMPILER_TEST_PATHS = frozenset(
    {
        "src/test/int/python/agentic-praxis-grimoire/skills/typescript-language-profile/SKILL.int.test.py",
        "src/test/unit/python/agentic-praxis-grimoire/src/test/support/apg_typescript_fixture_contract.unit.test.py",
    }
)
JAVASCRIPT_ENGINE_TEST_PATHS = frozenset(
    {
        "src/test/int/python/agentic-praxis-grimoire/skills/javascript-language-profile/SKILL.int.test.py",
    }
)
THRESHOLDS = {
    "unit": (80, 80),
    "integration": (80, 80),
    "combined": (85, 85),
}


class ToolError(Exception):
    """A bounded invocation, inventory, test, or coverage failure."""


class InvocationError(ToolError):
    """A bounded invocation or prerequisite configuration failure."""


class JavascriptQualificationError(InvocationError):
    """A bounded JavaScript qualification failure with no captured streams."""


class NodeProfileQualificationError(InvocationError):
    """A bounded Node-profile qualification failure with no captured streams."""


class HarnessError(ToolError):
    """A bounded test harness or worker infrastructure failure."""


class NodeProfileCleanupError(HarnessError):
    """A bounded Node-profile cleanup failure with no raw path or stream data."""


class GateShortfallError(ToolError):
    """A bounded coverage gate shortfall where tests passed but thresholds were not met."""


class PolicyCheckError(ToolError):
    """A bounded repository policy verification failure."""


class TestAssertionError(ToolError):
    """A test assertion failure during pytest execution."""


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
class PublicTestSelection:
    """Exact public Python files and node deselections for one release version."""

    version: str
    files: dict[str, tuple[str, ...]]
    deselections: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class JavascriptEngineBinding:
    """Exact executable facts observed around one JavaScript invocation."""

    path: Path
    file_identity: tuple[int, int, int, int, int, int, int]
    executable_sha256: str
    public_identity: str


@dataclass(frozen=True)
class JavascriptOutputContract:
    """One closed contract for a maintained JavaScript engine observation."""

    expected_return_code: int
    stdout_policy: str
    stderr_policy: str
    expected_result: object = None


@dataclass(frozen=True)
class JavascriptObservation:
    """Redacted validated JavaScript facts with no reachable captured streams."""

    return_code: int
    output_contract_id: str
    result: object
    stdout_empty: bool
    stderr_empty: bool
    engine_public_identity: str
    engine_sha256: str


@dataclass(frozen=True)
class NodeProfileRuntimeBinding:
    """Exact executable facts observed around one Node-profile invocation."""

    role: str
    path: Path
    file_identity: tuple[int, int, int, int, int, int, int]
    executable_sha256: str
    public_identity: str


@dataclass(frozen=True)
class NodeProfileInvocation:
    """One parent-owned private scratch topology for one Node invocation."""

    contract_id: str
    root: Path
    temporary: Path
    npm_cache: Path
    pnpm_home: Path
    work: Path
    filesystem_case: Path

    @property
    def environment(self) -> dict[str, str]:
        """Return the exact synthetic child environment for this invocation."""
        temporary = os.fspath(self.temporary)
        return {
            "NO_COLOR": "1",
            "PNPM_HOME": os.fspath(self.pnpm_home),
            "TEMP": temporary,
            "TMP": temporary,
            "TMPDIR": temporary,
            "npm_config_cache": os.fspath(self.npm_cache),
        }


@dataclass(frozen=True)
class NodeProfileObservation:
    """Redacted validated Node-profile facts with no captured streams."""

    role: str
    output_contract_id: str
    result: object
    runtime_public_identity: str
    runtime_sha256: str


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


JAVASCRIPT_OUTPUT_CONTRACTS = {
    "script-module-strictness": JavascriptOutputContract(
        0, "json-exact", "empty",
        {"sloppy": True, "strict": True, "moduleThis": True},
    ),
    "script-goal-strictness": JavascriptOutputContract(
        0, "json-exact", "empty",
        {
            "sloppy": {"error": None, "result": 1},
            "strict": {"error": "ReferenceError"},
        },
    ),
    "scope-declarations": JavascriptOutputContract(
        0, "json-exact", "empty",
        {
            "tdzError": "ReferenceError",
            "varBefore": "undefined",
            "fnBefore": "function",
            "perIteration": {"fromLet": [0, 1, 2], "fromVar": [3, 3, 3]},
        },
    ),
    "functions-boundaries": JavascriptOutputContract(
        0, "json-exact", "empty",
        {
            "binding": {"called": "holder", "arrow": "lexical"},
            "defaults": {"first": 1, "second": 2},
            "spread": {
                "head": 1,
                "tail": [2, 3],
                "widened": [1, 2, 3],
                "called": [1, 2, 3],
                "copied": {"head": 1, "own": "included"},
                "captured": 1,
            },
            "abrupt": "TypeError",
            "trace": ["first", "throw"],
        },
    ),
    "optional-chain": JavascriptOutputContract(
        0, "json-exact", "empty",
        {
            "result": {
                "conjunction": False,
                "disjunction": "r",
                "coalesced": "r",
                "grouped": "TypeError",
                "optionalCall": 6,
            },
            "trace": ["or-right", "coalesce-right", "optional-argument"],
        },
    ),
    "objects-classes": JavascriptOutputContract(
        0, "json-exact", "empty",
        {
            "chain": {"ownKind": True, "ownShared": False, "shared": "from-base"},
            "fixed": {
                "assign": {"threw": "TypeError"},
                "remove": {"threw": "TypeError"},
                "value": "original",
            },
            "setter": {"observed": 7, "ownsValue": False},
            "nonWritable": {"threw": "TypeError", "value": "base", "owns": False},
            "trace": ["base-constructor", "derived-field", "derived-after-super"],
            "field": "derived-field",
            "staticTrace": ["static-field", "static-block"],
            "secret": "derived-private",
            "brand": True,
        },
    ),
    "equality": JavascriptOutputContract(
        0, "json-exact", "empty",
        {
            "nanStrict": False,
            "nanSame": True,
            "zeroSame": False,
            "set": 2,
            "bigintError": "TypeError",
        },
    ),
    "coercion": JavascriptOutputContract(
        0, "json-exact", "empty",
        {
            "trace": ["number", "string", "default"],
            "result": {"number": 42, "string": "forty-two", "loose": True},
        },
    ),
    "iterator-close": JavascriptOutputContract(
        0, "json-exact", "empty",
        {
            "a": ["next:1", "next:2", "return"],
            "b": ["next:1"],
            "body": "TypeError:body",
            "missingTrace": ["next:1", "next:2"],
            "missing": {"first": 1, "second": 2},
            "noncall": "TypeError",
            "nonobject": "TypeError",
        },
    ),
    "finally-completion": JavascriptOutputContract(
        0, "json-exact", "empty",
        {
            "throwing": "from-finally",
            "returning": "from-finally",
            "normal": {
                "name": "TypeError",
                "message": "preserved",
                "trace": ["finally"],
            },
        },
    ),
    "promise-async": JavascriptOutputContract(
        0, "json-exact", "empty",
        {
            "promiseTrace": ["synchronous", "after-call", "then-1", "then-2"],
            "awaitTrace": ["before-await", "after-await"],
            "rejected": {"caught": "async-origin"},
        },
    ),
    "module-live-bindings": JavascriptOutputContract(
        0, "json-exact", "empty",
        {
            "live": {"before": 0, "after": 1},
            "namespace": {
                "label": "counter",
                "count": 1,
                "keys": ["count", "increment", "label"],
                "tag": "[object Module]",
            },
            "write": {"threw": "TypeError"},
        },
    ),
    "module-cycle": JavascriptOutputContract(0, "json-exact", "empty", "ReferenceError"),
    "top-level-await": JavascriptOutputContract(0, "json-exact", "empty", 1),
    "dynamic-import-failure": JavascriptOutputContract(0, "json-exact", "empty", "Error"),
    "module-strictness": JavascriptOutputContract(
        0, "json-exact", "empty",
        {"topLevelThisIsUndefined": True, "strict": {"threw": "ReferenceError"}},
    ),
    "module-goal-evidence": JavascriptOutputContract(
        0, "json-exact", "empty", 'nearest package.json "type" field'
    ),
    "checked-javascript": JavascriptOutputContract(
        0, "json-exact", "empty", {"total": 6, "count": 3}
    ),
    "cli-core": JavascriptOutputContract(
        0, "json-exact", "empty",
        {
            "first": {
                "total": 5,
                "operandCount": 2,
                "verbose": True,
                "messages": ["operands:2"],
                "status": "computed",
            },
            "stable": True,
        },
    ),
    "commonjs-boundary-syntax": JavascriptOutputContract(0, "empty", "empty"),
    "cli-commonjs-adapter-syntax": JavascriptOutputContract(0, "empty", "empty"),
}


def fail(message: str) -> NoReturn:
    raise ToolError(message)


def fail_invocation(message: str) -> NoReturn:
    raise InvocationError(message)


def fail_harness(message: str) -> NoReturn:
    raise HarnessError(message)


def fail_policy(message: str) -> NoReturn:
    raise PolicyCheckError(message)


def _unique_object(pairs: Sequence[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key: {key}")
        result[key] = value
    return result


def _relative_path(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        fail_invocation(f"inventory {field} must be a nonempty string")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) != value:
        fail_invocation(f"inventory {field} is not a normalized relative path: {value}")
    return value


def load_inventory(root: Path) -> Inventory:
    """Load the strict inventory without accepting unknown or duplicate data."""
    try:
        raw = (root / INVENTORY_PATH).read_text(encoding="utf-8")
        value = json.loads(raw, object_pairs_hook=_unique_object)
    except (OSError, UnicodeError, ValueError) as error:
        fail_invocation(f"test inventory is unreadable or malformed: {error}")
    if not isinstance(value, dict) or set(value) != {
        "coverage_sources",
        "excluded_python_launchers",
        "schema_version",
        "tests",
    }:
        fail_invocation("test inventory has unknown or missing top-level fields")
    if value["schema_version"] != 2:
        fail_invocation("test inventory schema_version must be 2")

    coverage_sources: dict[str, tuple[str, ...]] = {}
    source_entries = value["coverage_sources"]
    if not isinstance(source_entries, list) or not source_entries:
        fail_invocation("test inventory coverage_sources must be a nonempty array")
    for entry in source_entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "rationale", "suites"}:
            fail_invocation("coverage source entry has unknown or missing fields")
        path = _relative_path(entry["path"], "source path")
        rationale = entry["rationale"]
        if not isinstance(rationale, str) or not rationale.strip():
            fail_invocation(f"coverage source rationale is invalid: {path}")
        suites = entry["suites"]
        if (
            not isinstance(suites, list)
            or suites != ["unit", "integration", "combined"]
        ):
            fail_invocation(f"coverage source suites are invalid: {path}")
        if path in coverage_sources:
            fail_invocation(f"duplicate coverage source: {path}")
        coverage_sources[path] = tuple(suites)

    excluded_launchers: dict[str, str] = {}
    launcher_entries = value["excluded_python_launchers"]
    if not isinstance(launcher_entries, list):
        fail_invocation("excluded_python_launchers must be an array")
    for entry in launcher_entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "reason"}:
            fail_invocation("launcher entry has unknown or missing fields")
        path = _relative_path(entry["path"], "launcher path")
        reason = entry["reason"]
        if not isinstance(reason, str) or not reason.strip():
            fail_invocation(f"launcher exclusion lacks a rationale: {path}")
        if path in excluded_launchers:
            fail_invocation(f"duplicate launcher exclusion: {path}")
        excluded_launchers[path] = reason

    tests: dict[str, tuple[str, str]] = {}
    test_entries = value["tests"]
    if not isinstance(test_entries, list) or not test_entries:
        fail_invocation("test inventory tests must be a nonempty array")
    for entry in test_entries:
        if not isinstance(entry, dict) or set(entry) != {"owner", "path", "suite"}:
            fail_invocation("test entry has unknown or missing fields")
        path = _relative_path(entry["path"], "test path")
        owner = _relative_path(entry["owner"], "production owner")
        suite = entry["suite"]
        if suite not in {"unit", "integration"}:
            fail_invocation(f"test suite is invalid: {path}")
        if path in tests:
            fail_invocation(f"duplicate mirrored test: {path}")
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
        for source_root in (root / "libexec", root / "src/agentic_praxis_grimoire")
        for path in source_root.rglob("*.py")
        if "__pycache__" not in path.parts
    }
    declared_sources = set(inventory.coverage_sources)
    if actual_sources != declared_sources:
        missing = sorted(actual_sources - declared_sources)
        stale = sorted(declared_sources - actual_sources)
        fail_policy(f"coverage source inventory differs: missing={missing}; stale={stale}")
    actual_launchers = set()
    for path in (root / "bin").iterdir():
        if path.is_file() and path.read_bytes().startswith(b"#!/usr/bin/env python3\n"):
            actual_launchers.add(path.relative_to(root).as_posix())
    if actual_launchers != set(inventory.excluded_launchers):
        fail_policy("Python launcher exclusions differ from the executable inventory")

    actual_tests = {
        path.relative_to(root).as_posix()
        for base in (root / UNIT_ROOT, root / INTEGRATION_ROOT)
        for path in base.rglob("*.test.py")
    }
    if actual_tests != set(inventory.tests):
        missing = sorted(actual_tests - set(inventory.tests))
        stale = sorted(set(inventory.tests) - actual_tests)
        fail_policy(f"mirrored test inventory differs: missing={missing}; stale={stale}")
    legacy = sorted(
        path.relative_to(root).as_posix()
        for base in (root / "src/test/unit/python", root / "src/test/int/python")
        for path in base.glob("*.py")
    )
    if legacy:
        fail_policy(f"stale legacy Python test path remains: {legacy}")
    for path, (owner, suite) in inventory.tests.items():
        if not (root / owner).is_file():
            fail_policy(f"mirrored test production owner is missing: {owner}")
        expected = _expected_test_path(owner, suite)
        if path != expected:
            fail_policy(f"mirrored test path disagrees with owner: {path}; expected {expected}")


def _read_public_version_file(root: Path, expected: str) -> None:
    """Require the current public projection's version authority to match exactly."""
    path = root / "src/agentic_praxis_grimoire/VERSION"
    if path.is_symlink() or not path.is_file():
        fail_invocation("public validation source VERSION must be a regular file")
    try:
        lines = path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeError) as error:
        fail_invocation(f"public validation source VERSION is unreadable: {error}")
    if lines != [expected]:
        observed = lines[0] if len(lines) == 1 else "<malformed>"
        fail_invocation(
            "public validation source VERSION does not match --public-version "
            f"{expected} (observed {observed})"
        )


def load_public_test_selection(
    root: Path, inventory: Inventory, version: str
) -> PublicTestSelection:
    """Load one clean public projection and close its canonical Python selection."""
    import apg_public_release as public_release

    if not isinstance(version, str):
        raise InvocationError("public validation version must be a string")
    try:
        public_release.validate_version(version)
    except (public_release.InvocationError, public_release.ToolError) as error:
        fail_invocation(f"public validation version is invalid: {error}")
    private_path = root / "private"
    if private_path.exists() or private_path.is_symlink():
        fail_invocation("public validation source contains a private directory")
    _read_public_version_file(root, version)

    try:
        repository = public_release.resolve_repository(root, "public validation source")
        committed_version = public_release.committed_bytes(
            repository, "src/agentic_praxis_grimoire/VERSION"
        ).decode("ascii").splitlines()
        if committed_version != [version]:
            fail_invocation(
                "public validation source committed VERSION does not match "
                f"--public-version {version}"
            )
        public_release.validate_public_release_surface(repository, version)
        policy = public_release.load_policy(
            repository,
            expected_surfaces=public_release.audited_policy_surfaces(version),
        )
        deselections = public_release.resolve_public_validation_deselections(
            version, policy
        )
    except (OSError, UnicodeError, public_release.InvocationError, public_release.ToolError) as error:
        fail_invocation(f"public validation source rejected: {error}")

    policy_tests = policy.get("required_test_entrypoints")
    if (
        not isinstance(policy_tests, (list, tuple))
        or any(not isinstance(path, str) for path in policy_tests)
        or len(set(policy_tests)) != len(policy_tests)
    ):
        fail_invocation("public validation policy test entrypoints are malformed")

    audited_python = tuple(path for path in policy_tests if path.endswith(".py"))
    try:
        selected_python = public_release.public_python_selection(
            repository, version, audited_python
        )
    except (public_release.InvocationError, public_release.ToolError) as error:
        fail_invocation(f"public validation test selection rejected: {error}")
    if (
        not isinstance(selected_python, (list, tuple))
        or any(not isinstance(path, str) for path in selected_python)
        or len(set(selected_python)) != len(selected_python)
        or not set(audited_python).issubset(selected_python)
    ):
        fail_invocation("public validation Python test selection is malformed")

    selected: dict[str, list[str]] = {"unit": [], "integration": []}
    roots = (
        (UNIT_ROOT.as_posix() + "/", "unit"),
        (INTEGRATION_ROOT.as_posix() + "/", "integration"),
    )
    for path in selected_python:
        matching_suites = [suite for prefix, suite in roots if path.startswith(prefix)]
        if len(matching_suites) != 1:
            fail_invocation(
                "public validation policy contains a Python test outside the "
                f"canonical suites: {path}"
            )
        suite = matching_suites[0]
        declared = inventory.tests.get(path)
        if declared is None:
            fail_invocation(f"public validation test is missing from inventory: {path}")
        if declared[1] != suite:
            fail_invocation(
                f"public validation test suite disagrees with inventory: {path}"
            )
        selected[suite].append(path)

    if any(not paths for paths in selected.values()):
        fail_invocation("public validation policy omits a canonical Python test suite")

    selected_paths = {path for paths in selected.values() for path in paths}
    if not isinstance(deselections, (list, tuple)):
        fail_invocation("public validation deselections are malformed")
    if any(not isinstance(node, str) for node in deselections):
        fail_invocation("public validation deselections are malformed")
    if tuple(deselections) != tuple(sorted(set(deselections))):
        fail_invocation("public validation deselections are malformed")
    deselected_by_suite: dict[str, list[str]] = {"unit": [], "integration": []}
    for node_id in deselections:
        if not isinstance(node_id, str):
            fail_invocation("public validation deselections are malformed")
        node_file, separator, node_name = node_id.partition("::")
        if not separator or not node_name or node_file not in selected_paths:
            fail_invocation(
                "public validation deselection is outside the exact audited "
                f"Python selection: {node_id}"
            )
        suite = inventory.tests[node_file][1]
        deselected_by_suite[suite].append(node_id)

    return PublicTestSelection(
        version=version,
        files={suite: tuple(sorted(paths)) for suite, paths in selected.items()},
        deselections={
            suite: tuple(sorted(paths))
            for suite, paths in deselected_by_suite.items()
        },
    )


def dependency_versions() -> dict[str, str]:
    """Require the exact reviewed test stack."""
    versions: dict[str, str] = {}
    for distribution, expected in EXPECTED_VERSIONS.items():
        try:
            actual = metadata.version(distribution)
        except metadata.PackageNotFoundError:
            fail_invocation(f"required test dependency is not installed: {distribution}=={expected}")
        if actual != expected:
            fail_invocation(
                f"test dependency version mismatch: {distribution}=={actual}; "
                f"expected {expected}"
            )
        versions[distribution] = actual
    return versions


def requires_typescript_compiler(inventory: Inventory) -> bool:
    """Return whether the validated inventory owns compiler-backed tests."""
    return bool(TYPESCRIPT_COMPILER_TEST_PATHS & set(inventory.tests))


def validate_typescript_compiler(root: Path) -> str:
    """Require the exact externally provisioned compiler used by maintained tests."""
    raw = os.environ.get("APG_TYPESCRIPT_TSC")
    if not raw:
        fail_invocation(
            "TypeScript test prerequisite is unavailable: set APG_TYPESCRIPT_TSC "
            "to an absolute executable typescript@7.0.2 tsc installed outside "
            "the repository checkout"
        )
    executable = Path(raw)
    if (
        not executable.is_absolute()
        or executable.is_symlink()
        or not executable.is_file()
        or not os.access(executable, os.X_OK)
    ):
        fail_invocation(
            "APG_TYPESCRIPT_TSC must name an absolute regular executable "
            "typescript@7.0.2 tsc outside the repository checkout"
        )
    try:
        resolved_executable = executable.resolve(strict=True)
        resolved_root = root.resolve(strict=True)
    except OSError as error:
        fail_invocation(f"TypeScript compiler prerequisite path could not be resolved: {error}")
    if resolved_executable == resolved_root or resolved_root in resolved_executable.parents:
        fail_invocation("APG_TYPESCRIPT_TSC must be installed outside the repository checkout")
    try:
        completed = subprocess.run(
            [str(executable), "--version"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=10,
            env={**os.environ, "NO_COLOR": "1"},
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        fail_invocation(f"TypeScript compiler prerequisite could not be executed: {error}")
    version = completed.stdout.strip()
    if completed.returncode != 0 or version != EXPECTED_TYPESCRIPT_VERSION:
        fail_invocation(
            "TypeScript compiler version mismatch: "
            f"observed {version or '<no version>'}; expected {EXPECTED_TYPESCRIPT_VERSION}"
        )
    return version


def requires_javascript_engine(inventory: Inventory) -> bool:
    """Return whether the validated inventory owns engine-backed JavaScript tests."""
    return bool(JAVASCRIPT_ENGINE_TEST_PATHS & set(inventory.tests))


def requires_node_profile_runtimes(inventory: Inventory) -> bool:
    """Return whether the inventory owns exact two-runtime Node tests."""
    return bool(NODE_PROFILE_RUNTIME_TEST_PATHS & set(inventory.tests))


def _observe_node_profile_owned_scratch(root: Path) -> Path:
    """Observe the assignment owner behind a path-free public wrapper."""
    raw = os.environ.get("APG_NODEJS_OWNED_SCRATCH_ROOT")
    if not raw:
        fail("Node-profile scratch owner is unavailable: set APG_NODEJS_OWNED_SCRATCH_ROOT")
    scratch = Path(raw)
    try:
        resolved = scratch.resolve(strict=True)
        repository = root.resolve(strict=True)
    except OSError as error:
        fail(f"Node-profile scratch owner could not be resolved: {type(error).__name__}")
    if (
        not scratch.is_absolute()
        or scratch.is_symlink()
        or not scratch.is_dir()
        or resolved != scratch
        or resolved == repository
        or repository in resolved.parents
        or resolved in repository.parents
    ):
        fail("APG_NODEJS_OWNED_SCRATCH_ROOT must be a separate external direct directory")
    return resolved


def _node_profile_owned_scratch(root: Path) -> Path:
    """Require the explicit owner without retaining its path on failure."""
    try:
        return _observe_node_profile_owned_scratch(root)
    except ToolError as error:
        safe_kind = str(error)
        root = None
        error = None
        _raise_node_profile_qualification(safe_kind, "scratch-owner")


def _validate_node_profile_directory(path: Path, owner: Path, label: str) -> None:
    """Require one existing private direct path beneath the invocation owner."""
    try:
        resolved = path.resolve(strict=True)
        metadata = path.lstat()
    except OSError as error:
        fail(f"Node-profile {label} directory is unavailable: {type(error).__name__}")
    if (
        not path.is_absolute()
        or path.is_symlink()
        or not path.is_dir()
        or resolved != path
        or not resolved.is_relative_to(owner)
        or stat.S_IMODE(metadata.st_mode) & 0o077
    ):
        fail(f"Node-profile {label} directory violates its exact private owner")


def _validate_node_profile_invocation(root: Path, invocation: NodeProfileInvocation) -> None:
    """Revalidate one exact direct-child topology at ordinary preflight."""
    owned = _node_profile_owned_scratch(root)
    if invocation.root.parent != owned:
        fail("Node-profile invocation root is not a direct child of its exact owner")
    _validate_node_profile_directory(invocation.root, owned, "invocation-root")
    expected = {
        invocation.temporary: "tmp",
        invocation.npm_cache: "npm-cache",
        invocation.pnpm_home: "pnpm-home",
        invocation.work: "work",
        invocation.filesystem_case: "fs-case",
    }
    if set(expected) != {
        invocation.root / "tmp",
        invocation.root / "npm-cache",
        invocation.root / "pnpm-home",
        invocation.root / "work",
        invocation.root / "fs-case",
    }:
        fail("Node-profile invocation topology is not exact")
    for path, label in expected.items():
        if path.parent != invocation.root:
            fail("Node-profile invocation child is not direct")
        _validate_node_profile_directory(path, invocation.root, label)
    environment = invocation.environment
    if set(environment) != NODE_PROFILE_ENVIRONMENT_KEYS or environment["NO_COLOR"] != "1":
        fail("Node-profile child environment is not the exact closed allowlist")
    if environment != {
        "NO_COLOR": "1",
        "PNPM_HOME": os.fspath(invocation.pnpm_home),
        "TEMP": os.fspath(invocation.temporary),
        "TMP": os.fspath(invocation.temporary),
        "TMPDIR": os.fspath(invocation.temporary),
        "npm_config_cache": os.fspath(invocation.npm_cache),
    }:
        fail("Node-profile child environment disagrees with its exact topology")


def _node_profile_cleanup_actions(
    invocation: NodeProfileInvocation,
) -> tuple[tuple[str, Callable[[], None]], ...]:
    """Return the complete ordered cleanup plan for fault-injection tests."""
    return (("remove-root", lambda: shutil.rmtree(invocation.root)),)


def _cleanup_node_profile_invocation(invocation: NodeProfileInvocation) -> str | None:
    """Attempt every owned cleanup action and return only a bounded failure."""
    failures: list[str] = []
    actions = _node_profile_cleanup_actions(invocation)
    for action_id, action in actions:
        try:
            action()
        except Exception:
            failures.append(action_id)
    try:
        invocation.root.lstat()
    except FileNotFoundError:
        pass
    except OSError:
        failures.append("absence-verification")
    else:
        failures.append("retained-artifact")
    action = None
    actions = ()
    return ",".join(dict.fromkeys(failures)) or None


def _raise_node_profile_cleanup(contract_id: str, detail: str) -> NoReturn:
    """Raise one path-free cleanup failure from a path-free frame."""
    raise NodeProfileCleanupError(
        f"Node-profile cleanup failed: {contract_id}; {detail}"
    ) from None


def _raise_node_profile_qualification(kind: str, contract_id: str) -> NoReturn:
    """Raise one path-free qualification failure from a path-free frame."""
    raise NodeProfileQualificationError(
        f"Node-profile {kind}: {contract_id}"
    ) from None


@contextmanager
def node_profile_invocation(root: Path, contract_id: str):
    """Create and completely clean one exact parent-owned invocation topology."""
    if contract_id not in NODE_PROFILE_OUTPUT_CONTRACTS:
        root = None
        contract_id = ""
        _raise_node_profile_qualification("output contract is unknown", "unknown-contract")
    try:
        owned = _node_profile_owned_scratch(root)
        invocation_root = Path(tempfile.mkdtemp(prefix="node-profile-", dir=owned))
    except (OSError, ToolError) as error:
        safe_kind = f"invocation root creation failed ({type(error).__name__})"
        root = None
        contract_id = ""
        owned = None
        error = None
        _raise_node_profile_qualification(safe_kind, "scratch-root")
    invocation = NodeProfileInvocation(
        contract_id,
        invocation_root,
        invocation_root / "tmp",
        invocation_root / "npm-cache",
        invocation_root / "pnpm-home",
        invocation_root / "work",
        invocation_root / "fs-case",
    )
    try:
        invocation_root.chmod(0o700)
        for child in (
            invocation.temporary,
            invocation.npm_cache,
            invocation.pnpm_home,
            invocation.work,
            invocation.filesystem_case,
        ):
            child.mkdir(mode=0o700)
        _validate_node_profile_invocation(root, invocation)
    except Exception as error:
        setup_error = f"setup failed ({type(error).__name__})"
    else:
        setup_error = None
    if setup_error is not None:
        cleanup_error = _cleanup_node_profile_invocation(invocation)
        safe_contract_id = contract_id
        child = None
        invocation = None
        invocation_root = None
        owned = None
        root = None
        contract_id = ""
        if cleanup_error is not None:
            _raise_node_profile_cleanup(safe_contract_id, cleanup_error)
        _raise_node_profile_qualification(setup_error, safe_contract_id)
    try:
        yield invocation
    finally:
        cleanup_error = _cleanup_node_profile_invocation(invocation)
        safe_contract_id = contract_id
        child = None
        invocation = None
        invocation_root = None
        owned = None
        root = None
        contract_id = ""
        if cleanup_error is not None:
            _raise_node_profile_cleanup(safe_contract_id, cleanup_error)


def _probe_node_profile_runtime_identity(
    executable: Path,
    role: str,
    expected_identity: str,
    *,
    environment: dict[str, str],
    timeout: int = 10,
) -> tuple[str | None, str | None]:
    """Execute the Node-profile runtime probe consuming process exceptions and raw streams."""
    identity_expression = (
        "JSON.stringify({identity:process.version+'|'+process.platform+'/'+process.arch+'|'"
        "+process.versions.v8+'|'+process.versions.uv,execArgv:process.execArgv.slice(0,-2),"
        "nodeOptions:Object.hasOwn(process.env,'NODE_OPTIONS')})"
    )
    try:
        try:
            completed = _run_javascript_process(
                [os.fspath(executable), "-p", identity_expression],
                cwd=None,
                timeout=timeout,
                environment=environment,
            )
        except (OSError, subprocess.TimeoutExpired, UnicodeError) as error:
            error_name = (
                "TimeoutExpired"
                if isinstance(error, subprocess.TimeoutExpired)
                else "UnicodeError"
                if isinstance(error, UnicodeError)
                else "OSError"
            )
            error = None
            return None, f"Node-profile {role} prerequisite could not be executed: {error_name}"

        return_code = completed.returncode
        stderr = completed.stderr
        raw_stdout = completed.stdout
        completed = None

        if return_code != 0 or stderr != "":
            raw_stdout = ""
            stderr = ""
            return None, f"Node-profile {role} prerequisite changed or has the wrong identity"

        try:
            public_probe = json.loads(raw_stdout)
        except (ToolError, TypeError, ValueError, json.JSONDecodeError, RecursionError):
            public_probe = None
        raw_stdout = ""
        stderr = ""

        if not isinstance(public_probe, dict):
            public_probe = None
            return None, f"Node-profile {role} prerequisite changed or has the wrong identity"

        public_identity = public_probe.get("identity")
        exec_argv = public_probe.get("execArgv")
        node_options = public_probe.get("nodeOptions")
        public_probe = None

        if (
            public_identity != expected_identity
            or exec_argv != []
            or node_options is not False
        ):
            public_identity = None
            exec_argv = None
            node_options = None
            return None, f"Node-profile {role} prerequisite changed or has the wrong identity"

        return public_identity, None
    except KeyboardInterrupt:
        return None, "interrupted"


def _observe_node_profile_runtime_binding(
    root: Path, role: str
) -> NodeProfileRuntimeBinding:
    """Observe one runtime; its public wrapper removes unsafe failure frames."""
    contract = NODE_PROFILE_RUNTIME_CONTRACTS.get(role)
    if contract is None:
        fail("unknown Node-profile runtime role")
    environment_name, expected_identity, expected_sha256 = contract
    raw = os.environ.get(environment_name)
    if not raw:
        fail(f"Node-profile prerequisite is unavailable: set {environment_name}")
    executable = Path(raw)
    if (
        not executable.is_absolute()
        or executable.is_symlink()
        or not executable.is_file()
        or not os.access(executable, os.X_OK)
    ):
        fail(f"{environment_name} must name an absolute direct regular executable")
    try:
        resolved = executable.resolve(strict=True)
        repository = root.resolve(strict=True)
        before = executable.lstat()
    except OSError as error:
        fail(f"Node-profile {role} prerequisite identity could not be read: {type(error).__name__}")
    if resolved != executable:
        fail(f"{environment_name} must contain no symlinked path component")
    if resolved == repository or repository in resolved.parents:
        fail(f"{environment_name} must be outside the repository checkout")
    identity = (
        before.st_dev, before.st_ino, before.st_mode, before.st_uid,
        before.st_gid, before.st_size, before.st_mtime_ns,
    )
    try:
        with resolved.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
    except OSError as error:
        fail(f"Node-profile {role} prerequisite content could not be read: {type(error).__name__}")
    if digest != expected_sha256:
        fail(f"Node-profile {role} executable digest mismatch")
    identity_environment = {"NO_COLOR": "1"}
    public_identity, probe_error = _probe_node_profile_runtime_identity(
        resolved,
        role,
        expected_identity,
        environment=identity_environment,
        timeout=10,
    )
    if probe_error == "interrupted":
        raise KeyboardInterrupt()
    if probe_error is not None and probe_error.startswith(
        f"Node-profile {role} prerequisite could not be executed:"
    ):
        fail(probe_error)
    try:
        after = executable.lstat()
        after_resolved = executable.resolve(strict=True)
        with resolved.open("rb") as stream:
            after_digest = hashlib.file_digest(stream, "sha256").hexdigest()
    except OSError as error:
        fail(f"Node-profile {role} prerequisite changed during validation: {type(error).__name__}")
    after_identity = (
        after.st_dev, after.st_ino, after.st_mode, after.st_uid,
        after.st_gid, after.st_size, after.st_mtime_ns,
    )
    if (
        after_identity != identity
        or after_resolved != resolved
        or after_digest != digest
        or probe_error is not None
        or public_identity != expected_identity
        or identity_environment != {"NO_COLOR": "1"}
        or os.environ.get(environment_name) != raw
    ):
        public_identity = None
        probe_error = None
        fail(f"Node-profile {role} prerequisite changed or has the wrong identity")
    return NodeProfileRuntimeBinding(role, resolved, identity, digest, expected_identity)


def _node_profile_runtime_binding(root: Path, role: str) -> NodeProfileRuntimeBinding:
    """Resolve one exact runtime and expose only a bounded failure frame."""
    if role not in NODE_PROFILE_RUNTIME_CONTRACTS:
        root = None
        role = ""
        _raise_node_profile_qualification("runtime role is unknown", "runtime-binding")
    error_kind: str | None = None
    try:
        return _observe_node_profile_runtime_binding(root, role)
    except ToolError as error:
        error_kind = str(error)
        root = None
        role = ""
        error = None
    if error_kind is not None:
        safe_kind = error_kind
        error_kind = None
        _raise_node_profile_qualification(safe_kind, "runtime-binding")


def validate_node_profile_runtimes(root: Path) -> tuple[str, str]:
    """Validate both exact maintained Node-profile runtime roles."""
    error_kind: str | None = None
    try:
        bindings = tuple(
            _node_profile_runtime_binding(root, role) for role in ("primary", "secondary")
        )
    except ToolError as error:
        error_kind = str(error)
        root = None
        error = None
    if error_kind is not None:
        safe_kind = error_kind
        error_kind = None
        _raise_node_profile_qualification(safe_kind, "runtime-roles")
    if bindings[0].path == bindings[1].path or bindings[0].executable_sha256 == bindings[1].executable_sha256:
        bindings = ()
        root = None
        _raise_node_profile_qualification(
            "primary and secondary runtime roles must remain distinct", "runtime-roles"
        )
    return tuple(binding.public_identity for binding in bindings)


def invoke_node_profile_runtime(
    root: Path,
    role: str,
    arguments: Sequence[str],
    *,
    invocation: NodeProfileInvocation,
    output_contract_id: str,
    expected_result: object,
    expected_return_code: int = 0,
    stdout_policy: str = "json-exact",
    stderr_policy: str = "empty",
    timeout: int = 20,
) -> NodeProfileObservation:
    """Execute one exact runtime and return only a closed redacted observation."""
    contract = NODE_PROFILE_OUTPUT_CONTRACTS.get(output_contract_id)
    early_error = None
    if contract is None:
        early_error = "output contract is unknown"
    supplied_contract = (
        expected_return_code, stdout_policy, stderr_policy, expected_result
    )
    if early_error is None and supplied_contract != contract:
        early_error = "invocation disagrees with its closed output contract"
    if early_error is None and invocation.contract_id != output_contract_id:
        early_error = "invocation disagrees with its scratch contract"
    if early_error is not None:
        safe_error_kind = early_error
        safe_contract_id = (
            output_contract_id if output_contract_id in NODE_PROFILE_OUTPUT_CONTRACTS
            else "unknown-contract"
        )
        root = None
        role = ""
        arguments = ()
        invocation = None
        output_contract_id = ""
        expected_result = None
        contract = None
        supplied_contract = None
        _raise_node_profile_qualification(safe_error_kind, safe_contract_id)
    before = None
    try:
        _validate_node_profile_invocation(root, invocation)
    except ToolError as error:
        error_kind = str(error)
        before = None
        result = None
    else:
        try:
            before = _node_profile_runtime_binding(root, role)
        except ToolError:
            error_kind = "runtime preflight contract failed"
            result = None
        else:
            result, error_kind = _execute_node_profile_contract(
                before.path,
                arguments,
                cwd=invocation.work,
                environment=invocation.environment,
                timeout=timeout,
                expected_return_code=expected_return_code,
                stdout_policy=stdout_policy,
                stderr_policy=stderr_policy,
                expected_result=expected_result,
            )
    postflight_error = None
    if before is not None:
        try:
            _validate_node_profile_invocation(root, invocation)
        except ToolError:
            postflight_error = "scratch postflight contract failed"
    # Drop caller-supplied and captured-data-adjacent references before any
    # bounded error is raised. Traceback-local rendering must remain safe.
    arguments = ()
    expected_result = None
    after = None
    if before is not None:
        try:
            after = _node_profile_runtime_binding(root, role)
        except ToolError:
            error_kind = "runtime postflight contract failed"
        if after is not None and after != before:
            error_kind = "runtime binding changed across invocation"
    if postflight_error is not None:
        error_kind = postflight_error
    if error_kind is not None:
        safe_error_kind = error_kind
        safe_contract_id = output_contract_id
        root = None
        role = ""
        arguments = ()
        invocation = None
        output_contract_id = ""
        expected_result = None
        contract = None
        supplied_contract = None
        before = None
        after = None
        result = None
        _raise_node_profile_qualification(safe_error_kind, safe_contract_id)
    return NodeProfileObservation(
        role, output_contract_id, result, before.public_identity, before.executable_sha256
    )


def _exact_json_matches(actual: object, expected: object) -> bool:
    """Compare one closed JSON value without raising through raw values."""
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(actual) == set(expected) and all(
            _exact_json_matches(actual[key], value) for key, value in expected.items()
        )
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(
            _exact_json_matches(item, value) for item, value in zip(actual, expected)
        )
    return actual == expected


def _execute_node_profile_contract(
    executable: Path,
    arguments: Sequence[str],
    *,
    cwd: Path,
    environment: dict[str, str],
    timeout: int,
    expected_return_code: int,
    stdout_policy: str,
    stderr_policy: str,
    expected_result: object,
) -> tuple[object, str | None]:
    """Capture and consume raw process data without propagating its frames."""
    try:
        completed = _run_javascript_process(
            [os.fspath(executable), *arguments],
            cwd=cwd,
            timeout=timeout,
            environment=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return None, f"invocation failed ({type(error).__name__})"
    if completed.returncode != expected_return_code:
        return None, "status contract failed"
    if stderr_policy not in {"empty", "discard"}:
        return None, "stderr policy is invalid"
    if stderr_policy == "empty" and completed.stderr != "":
        return None, "stderr contract failed"
    if stdout_policy == "empty":
        if completed.stdout != "" or expected_result is not None:
            return None, "output contract failed"
        return None, None
    if stdout_policy != "json-exact":
        return None, "stdout policy is invalid"
    try:
        actual = json.loads(completed.stdout, object_pairs_hook=_unique_object)
    except (ToolError, TypeError, ValueError, json.JSONDecodeError):
        return None, "output contract failed"
    if not _exact_json_matches(actual, expected_result):
        return None, "output contract failed"
    return actual, None


def validate_javascript_engine(root: Path) -> str:
    """Require the exact external engine used for bounded observations."""
    return _javascript_engine_binding(root).public_identity


def _run_javascript_process(
    arguments: Sequence[str],
    *,
    cwd: Path | None,
    timeout: int,
    environment: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    """Own the sole JavaScript qualification process-spawn site."""
    return subprocess.run(
        list(arguments),
        check=False,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        env=environment,
    )


def _javascript_error(kind: str, output_contract_id: str) -> NoReturn:
    raise JavascriptQualificationError(
        f"JavaScript qualification {kind}: output contract {output_contract_id}"
    )


def _check_exact_json(
    actual: object,
    expected: object,
    context: str,
) -> str | None:
    if type(actual) is not type(expected):
        return f"result type mismatch at {context}"
    if isinstance(expected, dict):
        if set(actual) != set(expected):
            return f"result fields mismatch at {context}"
        for key, value in expected.items():
            mismatch = _check_exact_json(actual[key], value, f"{context}.{key}")
            if mismatch is not None:
                return mismatch
        return None
    if isinstance(expected, list):
        if len(actual) != len(expected):
            return f"result length mismatch at {context}"
        for index, value in enumerate(expected):
            mismatch = _check_exact_json(actual[index], value, f"{context}[{index}]")
            if mismatch is not None:
                return mismatch
        return None
    if actual != expected:
        return f"result value mismatch at {context}"
    return None


def _consume_javascript_stream_output(
    output_contract_id: str,
    return_code: int,
    stdout: str,
    stderr: str,
) -> tuple[object, str | None]:
    """Parse and validate streams within a narrow frame without retaining raw data."""
    contract = JAVASCRIPT_OUTPUT_CONTRACTS.get(output_contract_id)
    if contract is None:
        return None, "selected an unknown contract"
    if return_code != contract.expected_return_code:
        return None, "returned an unexpected status"
    if contract.stderr_policy == "empty" and stderr != "":
        return None, "returned unexpected stderr"
    if contract.stdout_policy == "empty":
        if stdout != "":
            return None, "returned unexpected stdout"
        return None, None
    if contract.stdout_policy != "json-exact":
        return None, "selected an invalid stdout policy"
    try:
        parsed = json.loads(stdout, object_pairs_hook=_unique_object)
    except (ToolError, TypeError, ValueError, RecursionError):
        return None, "returned invalid structured output"
    mismatch = _check_exact_json(parsed, contract.expected_result, "result")
    if mismatch is not None:
        parsed = None
        return None, mismatch
    return deepcopy(contract.expected_result), None


def _validate_javascript_output(
    output_contract_id: str,
    return_code: int,
    stdout: str,
    stderr: str,
) -> object:
    """Validate captured streams locally and return only a closed result."""
    result, error_kind = _consume_javascript_stream_output(
        output_contract_id, return_code, stdout, stderr
    )
    stdout = ""
    stderr = ""
    if error_kind is not None:
        safe_kind = error_kind
        safe_contract_id = output_contract_id
        output_contract_id = ""
        error_kind = None
        _javascript_error(safe_kind, safe_contract_id)
    return result


def _probe_javascript_engine_identity(
    executable: Path,
    environment: dict[str, str],
    timeout: int = 10,
) -> tuple[str | None, str | None]:
    """Execute the identity probe in a narrow frame consuming process exceptions and raw streams."""
    try:
        try:
            completed = _run_javascript_process(
                [
                    os.fspath(executable),
                    "-p",
                    "process.version+'|'+process.platform+'/'+process.arch+'|'+process.versions.v8",
                ],
                cwd=None,
                timeout=timeout,
                environment=environment,
            )
        except (OSError, subprocess.TimeoutExpired, UnicodeError) as error:
            error_name = ("TimeoutExpired" if isinstance(error, subprocess.TimeoutExpired)
                          else "UnicodeError" if isinstance(error, UnicodeError) else "OSError")
            error = None
            return None, f"JavaScript engine prerequisite could not be executed: {error_name}"

        return_code = completed.returncode
        stderr = completed.stderr
        raw_identity = completed.stdout.strip()
        completed = None

        if (
            return_code != 0
            or stderr != ""
            or raw_identity != EXPECTED_JAVASCRIPT_ENGINE
        ):
            raw_identity = ""
            stderr = ""
            return None, (
                "JavaScript engine identity mismatch; expected "
                f"{EXPECTED_JAVASCRIPT_ENGINE}"
            )
        return EXPECTED_JAVASCRIPT_ENGINE, None
    except KeyboardInterrupt:
        return None, "interrupted"


def _execute_javascript_contract(
    executable: Path,
    arguments: Sequence[str],
    *,
    cwd: Path,
    timeout: int,
    environment: dict[str, str],
    output_contract_id: str,
) -> tuple[object, bool, bool, int, str | None]:
    """Capture and consume raw process data returning only public-safe values or diagnostic descriptor."""
    try:
        contract = JAVASCRIPT_OUTPUT_CONTRACTS.get(output_contract_id)
        if contract is None:
            return None, False, False, 0, "selected an unknown contract"
        try:
            completed = _run_javascript_process(
                [os.fspath(executable), *arguments],
                cwd=cwd,
                timeout=timeout,
                environment=environment,
            )
        except (OSError, subprocess.TimeoutExpired, UnicodeError) as error:
            error_name = ("TimeoutExpired" if isinstance(error, subprocess.TimeoutExpired)
                          else "UnicodeError" if isinstance(error, UnicodeError) else "OSError")
            error = None
            return None, False, False, 0, f"subprocess could not be executed ({error_name})"

        return_code = completed.returncode
        stdout_empty = completed.stdout == ""
        stderr_empty = completed.stderr == ""

        result, error_kind = _consume_javascript_stream_output(
            output_contract_id, return_code, completed.stdout, completed.stderr
        )
        completed = None
        if error_kind is not None:
            return None, stdout_empty, stderr_empty, return_code, error_kind
        return result, stdout_empty, stderr_empty, return_code, None
    except KeyboardInterrupt:
        return None, False, False, 0, "interrupted"


def _javascript_engine_binding(root: Path) -> JavascriptEngineBinding:
    """Resolve and validate one direct engine path without returning a loose path."""
    raw = os.environ.get("APG_JAVASCRIPT_NODE")
    if not raw:
        fail_invocation(
            "JavaScript test prerequisite is unavailable: set APG_JAVASCRIPT_NODE "
            "to the absolute regular Node v22.22.2 executable outside the repository"
        )
    executable = Path(raw)
    if (
        not executable.is_absolute()
        or executable.is_symlink()
        or not executable.is_file()
        or not os.access(executable, os.X_OK)
    ):
        fail_invocation(
            "APG_JAVASCRIPT_NODE must name an absolute regular executable "
            "Node v22.22.2 outside the repository checkout"
        )
    try:
        resolved_executable = executable.resolve(strict=True)
        resolved_root = root.resolve(strict=True)
    except OSError as error:
        fail_invocation(f"JavaScript engine prerequisite path could not be resolved: {error}")
    if resolved_executable == resolved_root or resolved_root in resolved_executable.parents:
        fail_invocation("APG_JAVASCRIPT_NODE must be installed outside the repository checkout")
    if resolved_executable != executable:
        fail_invocation(
            "APG_JAVASCRIPT_NODE must name a direct resolved executable path "
            "without symlinked path components"
        )
    if EXPECTED_JAVASCRIPT_ENGINE_ROOT not in resolved_executable.parents:
        fail_invocation("APG_JAVASCRIPT_NODE must name the approved immutable Nix-store engine")
    try:
        before = resolved_executable.lstat()
    except OSError as error:
        fail_invocation(f"JavaScript engine prerequisite identity could not be read: {error}")
    before_identity: tuple[int, int, int, int, int, int, int] = (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_uid,
        before.st_gid,
        before.st_size,
        before.st_mtime_ns,
    )
    if before.st_uid != EXPECTED_JAVASCRIPT_ENGINE_UID:
        fail_invocation("APG_JAVASCRIPT_NODE must be owned by root")
    try:
        with resolved_executable.open("rb") as stream:
            executable_sha256 = hashlib.file_digest(stream, "sha256").hexdigest()
    except OSError as error:
        fail_invocation(f"JavaScript engine prerequisite content could not be read: {error}")
    if executable_sha256 != EXPECTED_JAVASCRIPT_ENGINE_SHA256:
        fail_invocation("JavaScript engine executable digest mismatch")
    identity, probe_error = _probe_javascript_engine_identity(
        resolved_executable,
        environment={**os.environ, "NO_COLOR": "1"},
        timeout=10,
    )
    if probe_error == "interrupted":
        raise KeyboardInterrupt()
    try:
        after = resolved_executable.lstat()
        after_identity = (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_uid,
            after.st_gid,
            after.st_size,
            after.st_mtime_ns,
        )
        after_resolved = resolved_executable.resolve(strict=True)
    except OSError as error:
        fail_invocation(f"JavaScript engine prerequisite changed during validation: {error}")
    if after_identity != before_identity or after_resolved != resolved_executable:
        fail_invocation("JavaScript engine prerequisite changed during validation")
    try:
        with resolved_executable.open("rb") as stream:
            after_sha256 = hashlib.file_digest(stream, "sha256").hexdigest()
    except OSError as error:
        fail_invocation(f"JavaScript engine prerequisite changed during validation: {error}")
    if after_sha256 != EXPECTED_JAVASCRIPT_ENGINE_SHA256:
        fail_invocation("JavaScript engine prerequisite changed during validation")
    if probe_error is not None:
        fail_invocation(probe_error)
    if os.environ.get("APG_JAVASCRIPT_NODE") != raw:
        fail_invocation("JavaScript engine environment binding changed during validation")
    return JavascriptEngineBinding(
        path=resolved_executable,
        file_identity=before_identity,
        executable_sha256=executable_sha256,
        public_identity=identity,
    )


def invoke_javascript_engine(
    root: Path,
    arguments: Sequence[str],
    *,
    cwd: Path,
    timeout: int = 20,
    environment: dict[str, str] | None = None,
    output_contract_id: str,
) -> JavascriptObservation:
    """Run one semantic or syntax subprocess through one pre/post exact binding."""
    before = _javascript_engine_binding(root)
    if os.environ.get("APG_JAVASCRIPT_NODE") != os.fspath(before.path):
        fail_invocation("JavaScript engine path changed before invocation")
    env = environment if environment is not None else {**os.environ, "NO_COLOR": "1"}
    result, stdout_empty, stderr_empty, return_code, error_kind = (
        _execute_javascript_contract(
            before.path,
            arguments,
            cwd=cwd,
            timeout=timeout,
            environment=env,
            output_contract_id=output_contract_id,
        )
    )
    if error_kind == "interrupted":
        raise KeyboardInterrupt()
    if os.environ.get("APG_JAVASCRIPT_NODE") != os.fspath(before.path):
        fail_invocation("JavaScript engine path changed after invocation")
    after = _javascript_engine_binding(root)
    if after != before:
        fail_invocation("JavaScript engine binding changed across invocation")

    # Drop intermediate and caller-supplied references before any possible error
    arguments = ()
    environment = None
    env = None
    cwd = None
    root = None

    if error_kind is not None:
        safe_kind = error_kind
        safe_contract_id = output_contract_id
        output_contract_id = ""
        before = None
        after = None
        result = None
        error_kind = None
        _javascript_error(safe_kind, safe_contract_id)

    return JavascriptObservation(
        return_code=return_code,
        output_contract_id=output_contract_id,
        result=result,
        stdout_empty=stdout_empty,
        stderr_empty=stderr_empty,
        engine_public_identity=before.public_identity,
        engine_sha256=before.executable_sha256,
    )


def record_worker_coverage_sentinel() -> None:
    """Provide one maintained-source event for an xdist worker context."""

    return None


def coverage_counts(report: dict[str, object], paths: Sequence[str]) -> CoverageCounts:
    """Aggregate exact counts for a reviewed source set."""
    files = report.get("files")
    if not isinstance(files, dict):
        fail_harness("coverage JSON has no files object")
    statement_covered = statement_total = branch_covered = branch_total = 0
    for path in paths:
        entry = files.get(path)
        if not isinstance(entry, dict) or not isinstance(entry.get("summary"), dict):
            fail_harness(f"coverage data omits required source: {path}")
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
            fail_harness(f"coverage counts are malformed for source: {path}")
        if any(not isinstance(count, int) or isinstance(count, bool) for count in counts):
            fail_harness(f"coverage counts are malformed for source: {path}")
        covered_lines, num_statements, covered_branches, num_branches = counts
        if (
            covered_lines < 0
            or num_statements < 0
            or covered_lines > num_statements
            or covered_branches < 0
            or num_branches < 0
            or covered_branches > num_branches
        ):
            fail_harness(f"coverage counts are impossible for source: {path}")
        statement_covered += covered_lines
        statement_total += num_statements
        branch_covered += covered_branches
        branch_total += num_branches
    if statement_total <= 0 or branch_total <= 0:
        fail_harness("coverage source target has zero statements or branches")
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
        fail_harness("coverage JSON has no files object")
    measured = set(files)
    if measured != declared:
        missing = sorted(declared - measured)
        foreign = sorted(measured - declared)
        fail_harness(f"coverage source set differs: missing={missing}; foreign={foreign}")


def enforce_threshold(counts: CoverageCounts, statement: int, branch: int) -> None:
    """Enforce exact integer ratios without display rounding."""
    if counts.statements_covered * 100 < statement * counts.statements_total:
        raise GateShortfallError(
            "statement coverage gate failed: "
            f"{counts.statements_covered}/{counts.statements_total} < {statement}%"
        )
    if counts.branches_covered * 100 < branch * counts.branches_total:
        raise GateShortfallError(
            "branch coverage gate failed: "
            f"{counts.branches_covered}/{counts.branches_total} < {branch}%"
        )


def _artifact_directory(root: Path) -> ArtifactDirectory:
    configured = os.environ.get("APG_TEST_ARTIFACT_ROOT")
    if configured:
        parent = Path(configured)
        if not parent.is_absolute() or not parent.is_dir() or parent.is_symlink():
            fail_invocation("APG_TEST_ARTIFACT_ROOT must be an absolute real directory")
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
        fail_harness("artifact directory identity changed before cleanup")
    if hasattr(os, "getuid"):
        if status.st_uid != os.getuid() or status.st_mode & 0o077:
            fail_harness("artifact directory ownership or mode changed before cleanup")
    shutil.rmtree(path)


def _read_manifest(path: Path, run_id: str, suite: str) -> list[dict[str, object]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        fail_harness(f"run manifest is unreadable: {path.name}: {error}")
    events: list[dict[str, object]] = []
    for line in lines:
        try:
            event = json.loads(line, object_pairs_hook=_unique_object)
        except (ValueError, json.JSONDecodeError) as error:
            fail_harness(f"run manifest is malformed: {path.name}: {error}")
        if not isinstance(event, dict):
            fail_harness(f"run manifest event is not an object: {path.name}")
        if event.get("run_id") != run_id or event.get("suite") != suite:
            fail_harness(f"run manifest contains foreign or stale evidence: {path.name}")
        events.append(event)
    return events


def validate_test_selection(selected_files: Sequence[str], selected_root: str) -> tuple[str, ...]:
    """Require a nonempty, unique inventory selection in the repository path form."""
    if not isinstance(selected_files, (list, tuple)) or not selected_files:
        fail_harness("test file selection is missing or malformed")
    prefix = selected_root.rstrip("/") + "/"
    for path in selected_files:
        if (
            not isinstance(path, str)
            or not path.startswith(prefix)
            or "\\" in path
            or ":" in path
            or "\x00" in path
            or PurePosixPath(path).is_absolute()
            or PurePosixPath(path).as_posix() != path
            or ".." in PurePosixPath(path).parts
        ):
            fail_harness("test file selection contains a noncanonical or foreign path")
    if len(set(selected_files)) != len(selected_files):
        fail_harness("test file selection contains duplicate files")
    return tuple(selected_files)


def _validate_node_ids(
    node_ids: object,
    selected_root: str,
    selected_files: Sequence[str],
    *,
    allow_empty: bool,
    require_all_files: bool,
) -> tuple[str, ...]:
    """Validate node syntax and membership against one selected file inventory."""
    expected = set(validate_test_selection(selected_files, selected_root))
    if (
        not isinstance(node_ids, (list, tuple))
        or (not allow_empty and not node_ids)
        or any(not isinstance(nodeid, str) for nodeid in node_ids)
        or len(set(node_ids)) != len(node_ids)
    ):
        fail_harness("worker collection evidence is malformed, duplicated or empty")
    files: set[str] = set()
    for nodeid in node_ids:
        path, separator, suffix = nodeid.partition("::")
        if not separator or not suffix:
            fail_harness("worker collection node ID is malformed")
        validate_test_selection([path], selected_root)
        files.add(path)
    if not files.issubset(expected):
        fail_harness(
            "worker collection contains files outside the selected inventory: "
            f"foreign={sorted(files - expected)}"
        )
    if require_all_files and files != expected:
        fail_harness(
            "worker collection differs from inventory: "
            f"missing={sorted(expected - files)}; foreign={sorted(files - expected)}"
        )
    return tuple(node_ids)


def validate_collection(
    node_ids: Sequence[str], selected_root: str, selected_files: Sequence[str]
) -> tuple[str, ...]:
    """Close one worker's node collection against its exact inventory file set."""
    return _validate_node_ids(
        node_ids,
        selected_root,
        selected_files,
        allow_empty=False,
        require_all_files=True,
    )


def validate_worker_manifest(
    path: Path,
    run_id: str,
    suite: str,
    workers: int,
    selected_root: str,
    selected_files: Sequence[str],
    measured_contexts: set[str] | None = None,
    deselections: Sequence[str] = (),
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
            fail_harness("worker manifest contains an unexpected event")
        by_kind.setdefault(str(kind), []).append(event)
    collection_records: list[tuple[tuple[str, ...], tuple[str, ...] | None, tuple[str, ...] | None]] = []
    for kind in ("worker-start", "collection", "worker-complete", "node-down"):
        members = by_kind.get(kind, [])
        observed = [event.get("worker") for event in members]
        if len(observed) != workers or set(observed) != expected_workers:
            fail_harness(f"worker manifest {kind} set is incomplete or duplicated")
        if kind == "collection":
            for event in members:
                raw = validate_collection(
                    event.get("node_ids"), selected_root, selected_files
                )
                has_remaining = "remaining_node_ids" in event
                has_deselected = "deselected_node_ids" in event
                if has_remaining != has_deselected:
                    fail_harness(
                        "worker collection evidence must include both raw and "
                        "post-deselection node IDs"
                    )
                if has_remaining:
                    remaining = _validate_node_ids(
                        event.get("remaining_node_ids"),
                        selected_root,
                        selected_files,
                        allow_empty=True,
                        require_all_files=False,
                    )
                    observed_deselected = _validate_node_ids(
                        event.get("deselected_node_ids"),
                        selected_root,
                        selected_files,
                        allow_empty=True,
                        require_all_files=False,
                    )
                    raw_set = set(raw)
                    remaining_set = set(remaining)
                    observed_set = set(observed_deselected)
                    if (
                        remaining_set & observed_set
                        or remaining_set | observed_set != raw_set
                    ):
                        fail_harness(
                            "worker collection raw and post-deselection node IDs "
                            "do not form an exact partition"
                        )
                    collection_records.append((raw, remaining, observed_deselected))
                else:
                    collection_records.append((raw, None, None))
        elif kind == "worker-complete":
            if any(event.get("exitstatus") != 0 for event in members):
                fail_harness("worker completion evidence reports failure")
        elif kind == "node-down":
            if any(
                event.get("error") is not False or event.get("exitstatus") != 0
                for event in members
            ):
                fail_harness("worker node-down evidence reports a crash or incomplete exit")
    if not collection_records:
        fail_harness("worker collection evidence is missing")
    raw_collections = [record[0] for record in collection_records]
    formats = {record[1] is not None for record in collection_records}
    if len(formats) != 1:
        fail_harness("worker collection evidence mixes legacy and enriched formats")
    if any(collection != raw_collections[0] for collection in raw_collections[1:]):
        fail_harness("xdist workers did not collect identical node IDs")
    if (
        not isinstance(deselections, (list, tuple))
        or any(not isinstance(nodeid, str) for nodeid in deselections)
        or len(set(deselections)) != len(deselections)
    ):
        fail_harness("worker manifest deselection set is malformed")
    approved_deselections = tuple(deselections)
    approved_set = set(approved_deselections)
    enriched = next(iter(formats))
    if enriched:
        remaining_collections = [record[1] for record in collection_records]
        observed_deselections = [record[2] for record in collection_records]
        if any(
            remaining != remaining_collections[0]
            for remaining in remaining_collections[1:]
        ) or any(
            observed != observed_deselections[0]
            for observed in observed_deselections[1:]
        ):
            fail_harness("xdist workers disagreed about post-deselection node IDs")
        actual_deselected = set(observed_deselections[0] or ())
        if actual_deselected != approved_set:
            fail_harness("worker manifest deselection set differs from collection")
        selected = set(remaining_collections[0] or ())
    else:
        selected = set(raw_collections[0])
        if not approved_set.issubset(selected):
            fail_harness("worker manifest deselection set differs from collection")
        selected -= approved_set
    result_events = by_kind.get("test-result", [])
    result_nodes = [event.get("nodeid") for event in result_events]
    expected_results = selected
    if len(result_nodes) != len(expected_results) or set(result_nodes) != expected_results:
        fail_harness("every selected node must have exactly one terminal result")
    if any(event.get("outcome") not in {"passed", "failed", "skipped"} for event in result_events):
        fail_harness("worker manifest terminal result is malformed")
    controller = by_kind.get("controller-complete", [])
    if len(controller) != 1 or controller[0].get("exitstatus") != 0:
        fail_harness("controller completion evidence reports failure")
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
            fail_harness(
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
            fail_harness("child manifest contains an unexpected event")
        process_id = event.get("process_id")
        context = event.get("context")
        if not isinstance(process_id, str) or not process_id or not isinstance(context, str):
            fail_harness("child manifest event is malformed")
        grouped.setdefault(process_id, []).append(event)
    for process_id, process_events in grouped.items():
        kinds = [event["event"] for event in process_events]
        contexts = {event["context"] for event in process_events}
        if kinds.count("child-start") != 1 or kinds.count("child-complete") != 1:
            fail_harness(f"required Python child did not start and complete exactly once: {process_id}")
        expected_context = f"apg-child:{run_id}:{process_id}"
        if contexts != {expected_context}:
            fail_harness(f"required Python child has no observable coverage contribution: {process_id}")
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
            fail_harness(
                "required Python child has no observable coverage contribution: "
                + ", ".join(process_ids)
            )
        fail_harness(
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
        fail_harness(f"coverage contexts are unreadable: {data_file.name}: {error}")
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
    selected_files: Sequence[str],
    deselections: Sequence[str] = (),
) -> list[str]:
    selected = UNIT_ROOT if suite == "unit" else INTEGRATION_ROOT
    paths = validate_test_selection(selected_files, selected.as_posix())
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
        "--cov=src/agentic_praxis_grimoire",
        "--cov-branch",
        f"--cov-config={root / '.coveragerc'}",
        f"--cov-report=json:{json_file}",
        "--cov-report=",
        *(
            argument
            for node_id in deselections
            for argument in ("--deselect", node_id)
        ),
        *(str(root / path) for path in paths),
    ]


def _run_pytest(
    root: Path,
    suite: str,
    workers: int,
    artifacts: Path,
    selected_files: Sequence[str],
    *,
    run_id: str | None = None,
    failure_mode: str | None = None,
    deselections: Sequence[str] = (),
) -> tuple[Path, dict[str, object]]:
    run_id = run_id or secrets.token_hex(16)
    selected_files = validate_test_selection(
        selected_files, (UNIT_ROOT if suite == "unit" else INTEGRATION_ROOT).as_posix()
    )
    data_file = artifacts / f"{suite}.coverage"
    json_file = artifacts / f"{suite}.json"
    worker_manifest = artifacts / f"{suite}.workers.jsonl"
    child_manifest = artifacts / f"{suite}.children.jsonl"
    existing = set(artifacts.iterdir())
    if existing:
        fail_harness(f"{suite} coverage artifact directory contains unexpected data")
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
    environment["APG_TEST_SELECTED_FILES"] = json.dumps(selected_files)
    environment["APG_TEST_WORKER_MANIFEST"] = str(worker_manifest)
    environment["APG_TEST_CHILD_MANIFEST"] = str(child_manifest)
    environment["APG_TEST_ARTIFACT_DIRECTORY"] = str(artifacts)
    environment["APG_TEST_REQUIRED_ENTRYPOINTS"] = json.dumps(
        sorted(path.name for path in (root / "bin").iterdir() if path.is_file())
    )
    environment["APG_TEST_REQUIRED_MODULE_BASENAMES"] = json.dumps(
        sorted(
            {
                path.name
                for source_root in (
                    root / "libexec",
                    root / "src/agentic_praxis_grimoire",
                )
                for path in source_root.rglob("*.py")
            }
        )
    )
    environment["APG_TEST_CANONICAL_LIBEXEC"] = str((root / "libexec").resolve())
    environment["APG_TEST_CANONICAL_PACKAGE"] = str(
        (root / "src/agentic_praxis_grimoire").resolve()
    )
    bootstrap = str(root / "src/test/apg_coverage_bootstrap")
    package_root = str(root / "src")
    inherited_pythonpath = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = os.pathsep.join(
        part for part in (bootstrap, package_root, inherited_pythonpath) if part
    )
    if failure_mode:
        environment["APG_TEST_FAILURE_MODE"] = failure_mode
    else:
        environment.pop("APG_TEST_FAILURE_MODE", None)
    result = subprocess.run(
        _pytest_command(
            root,
            suite,
            workers,
            data_file,
            json_file,
            run_id,
            selected_files,
            deselections,
        ),
        cwd=root,
        env=environment,
        check=False,
    )
    if result.returncode != 0:
        if result.returncode == 2:
            raise KeyboardInterrupt()
        if result.returncode == 4:
            raise InvocationError(f"{suite} pytest commandline usage error with status 4")
        if result.returncode == 5:
            raise InvocationError(f"{suite} pytest collected no tests (status 5)")
        if result.returncode == 3:
            raise HarnessError(f"{suite} pytest internal failure with status 3")
        validate_worker_manifest(
            worker_manifest,
            run_id,
            suite,
            workers,
            (UNIT_ROOT if suite == "unit" else INTEGRATION_ROOT).as_posix(),
            selected_files,
            None,
            deselections,
        )
        if result.returncode == 1:
            raise TestAssertionError(f"{suite} pytest run failed with status 1")
        raise HarnessError(f"{suite} pytest run failed with status {result.returncode}")
    if not data_file.is_file() or not json_file.is_file():
        raise HarnessError(f"{suite} coverage output is incomplete")
    measured_contexts = _coverage_contexts(data_file)
    validate_worker_manifest(
        worker_manifest,
        run_id,
        suite,
        workers,
        (UNIT_ROOT if suite == "unit" else INTEGRATION_ROOT).as_posix(),
        selected_files,
        measured_contexts,
        deselections,
    )
    validate_child_manifest(
        child_manifest, run_id, suite, measured_contexts
    )
    expected = _component_artifacts(artifacts, suite)
    if set(artifacts.iterdir()) != expected:
        fail_harness(f"{suite} coverage left unexpected data")
    try:
        report = json.loads(json_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        fail_harness(f"{suite} coverage JSON is unreadable: {error}")
    if not isinstance(report, dict):
        fail_harness(f"{suite} coverage JSON is not an object")
    return data_file, report


def _combine_coverage(root: Path, data_files: Sequence[Path], output: Path) -> dict[str, object]:
    """Combine coverage data files into an aggregate report without cross-test leakage."""
    from coverage import Coverage
    from coverage.data import CoverageData

    combined = CoverageData(basename=str(output))
    try:
        for path in data_files:
            data = CoverageData(basename=str(path))
            try:
                data.read()
                combined.update(data)
            except Exception as error:
                fail_harness(f"coverage data could not be combined: {path.name}: {error}")
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
        fail_harness(f"combined coverage JSON is unreadable: {error}")
    if not isinstance(value, dict):
        fail_harness("combined coverage JSON is not an object")
    return value


def _export_coverage_artifacts(
    artifacts: Path,
    export_dir: Path,
    selected: Sequence[str],
    suite: str,
) -> None:
    export_dir.mkdir(parents=True, exist_ok=True)
    for comp in selected:
        comp_dir = artifacts / comp
        dest_comp = export_dir / comp
        dest_comp.mkdir(parents=True, exist_ok=True)
        for name in (f"{comp}.json", f"{comp}.workers.jsonl", f"{comp}.children.jsonl"):
            src_file = comp_dir / name
            if src_file.exists():
                shutil.copy2(src_file, dest_comp / name)
    if suite == "combined":
        combined_file = artifacts / "combined.json"
        if combined_file.exists():
            shutil.copy2(combined_file, export_dir / "combined.json")


def run(
    suite: str,
    workers: int,
    root: Path,
    *,
    keep_artifacts_on_failure: bool = False,
    failure_mode: str | None = None,
    public_version: str | None = None,
    export_coverage: Path | None = None,
) -> None:
    """Validate inventory, run selected suites, and enforce exact gates."""
    if workers < 1 or workers > 64:
        raise InvocationError("workers must be between 1 and 64")
    if public_version is not None and suite == "policy":
        raise InvocationError("--public-version applies only to test suites")
    inventory = load_inventory(root)
    validate_inventory(root, inventory)
    public_selection = (
        load_public_test_selection(root, inventory, public_version)
        if public_version is not None
        else None
    )
    effective_inventory = inventory
    if public_selection is not None:
        selected_paths = {path for paths in public_selection.files.values() for path in paths}
        effective_inventory = Inventory(
            inventory.coverage_sources,
            inventory.excluded_launchers,
            {path: inventory.tests[path] for path in selected_paths},
        )
    dependency_versions()
    if requires_typescript_compiler(effective_inventory):
        validate_typescript_compiler(root)
    if requires_javascript_engine(effective_inventory):
        validate_javascript_engine(root)
    if requires_node_profile_runtimes(effective_inventory):
        validate_node_profile_runtimes(root)
    from apg_playwright_runtime import TEST_PATHS, PlaywrightPrerequisiteError, validate
    if TEST_PATHS & set(effective_inventory.tests):
        validate_javascript_engine(root)
        try:
            validate(root)
        except PlaywrightPrerequisiteError as error:
            fail_invocation(str(error))
    artifact_ownership = _artifact_directory(root)
    artifacts = artifact_ownership.path
    completed = False
    try:
        selected = ("unit", "integration") if suite == "combined" else (suite,)
        results: dict[str, ComponentResult] = {}
        errors: list[str] = []
        has_invocation_error = False
        has_harness_error = False
        has_assertion_error = False
        has_gate_error = False
        def _record_error(prefix: str, err: Exception) -> None:
            nonlocal has_invocation_error, has_harness_error, has_assertion_error, has_gate_error
            errors.append(f"{prefix}: {err}")
            if isinstance(err, InvocationError):
                has_invocation_error = True
            elif isinstance(err, GateShortfallError):
                has_gate_error = True
            elif isinstance(err, (PolicyCheckError, TestAssertionError)):
                has_assertion_error = True
            else:
                has_harness_error = True

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
                    selected_files=(
                        public_selection.files[selected_suite]
                        if public_selection is not None
                        else tuple(sorted(
                            path for path, (_owner, owner_suite) in inventory.tests.items()
                            if owner_suite == selected_suite
                        ))
                    ),
                    run_id=f"{invocation_id}-{selected_suite}",
                    failure_mode=failure_mode,
                    deselections=(
                        public_selection.deselections[selected_suite]
                        if public_selection is not None
                        else ()
                    ),
                )
                validate_coverage_report(report, set(inventory.coverage_sources))
                paths = sorted(
                    path
                    for path, suites in inventory.coverage_sources.items()
                    if selected_suite in suites
                )
                counts = coverage_counts(report, paths)
                results[selected_suite] = ComponentResult(data_file, report, counts)
                enforce_threshold(counts, *THRESHOLDS[selected_suite])
                print(
                    f"PASS {selected_suite}: statements "
                    f"{counts.statements_covered}/{counts.statements_total}; branches "
                    f"{counts.branches_covered}/{counts.branches_total}"
                )
            except (InvocationError, HarnessError, PolicyCheckError, TestAssertionError, GateShortfallError, ToolError) as error:
                _record_error(selected_suite, error)
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
            except (InvocationError, HarnessError, PolicyCheckError, TestAssertionError, GateShortfallError, ToolError) as error:
                _record_error("combined", error)
            else:
                print(
                    "PASS combined union: statements "
                    f"{counts.statements_covered}/{counts.statements_total}; branches "
                    f"{counts.branches_covered}/{counts.branches_total}"
                )
        if errors:
            if has_invocation_error:
                raise InvocationError("; ".join(errors))
            if has_harness_error:
                raise HarnessError("; ".join(errors))
            if has_assertion_error:
                raise TestAssertionError("; ".join(errors))
            if has_gate_error:
                raise GateShortfallError("; ".join(errors))
            raise ToolError("; ".join(errors))
        completed = True
    finally:
        if export_coverage is not None:
            _export_coverage_artifacts(artifacts, export_coverage, selected, suite)
        if not completed and keep_artifacts_on_failure:
            print(f"{COMMAND}: retained failure artifacts: {artifacts}", file=sys.stderr)
        else:
            try:
                _cleanup_artifacts(artifact_ownership)
            except Exception as cleanup_error:
                if not completed or errors:
                    print(
                        f"{COMMAND}: artifact directory cleanup warning: {cleanup_error}",
                        file=sys.stderr,
                    )
                else:
                    raise


def resolve_source_commit(root: Path) -> str:
    """Resolve the Git commit object ID of HEAD at execution time for the repository root."""
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        fail(f"resolve source commit: {error}")
    if completed.returncode != 0:
        fail(f"resolve source commit: {completed.stderr.strip() or 'git command failed'}")
    commit = completed.stdout.strip()
    if len(commit) != 40 or not all(c in "0123456789abcdefABCDEF" for c in commit):
        fail(f"resolve source commit: invalid commit hash {commit}")
    return commit


def write_summary(
    path: Path,
    *,
    suite: str,
    test_status: str,
    gate_status: str,
    source_commit: str,
) -> None:
    """Atomically write mode-private JACA CI qualification summary JSON."""
    payload = {
        "version": 1,
        "subproject": "apg",
        "suite": suite,
        "test_status": test_status,
        "gate_status": gate_status,
        "source_commit": source_commit,
    }
    content = (json.dumps(payload, indent=2) + "\n").encode("utf-8")
    resolved_path = path.resolve()
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = resolved_path.with_name(f".{resolved_path.name}.tmp.{secrets.token_hex(8)}")
    try:
        descriptor = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with open(descriptor, "wb", closefd=True) as stream:
                stream.write(content)
        except BaseException:
            try:
                os.close(descriptor)
            except OSError:
                pass
            raise
        tmp_path.replace(resolved_path)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


@dataclass(frozen=True)
class SummaryDestination:
    """Admitted destination for JACA CI qualification summary JSON."""

    target: Path
    resolved_target: Path
    root: Path

    def invalidate(self) -> None:
        """Safely invalidate existing APGR receipt at this admitted path.

        If target exists and is a recognized 6-field APGR receipt, unlink it.
        If target exists and is NOT a recognized APGR receipt, raise InvocationError
        to preserve foreign files.
        If unlinking fails, raise InvocationError.
        """
        if not self.target.exists() and not self.target.is_symlink():
            return
        if self.target.is_symlink():
            raise InvocationError(f"summary file cannot target a symlink: {self.target}")
        if self.target.is_dir() or self.resolved_target.is_dir():
            raise InvocationError(f"summary file cannot target a directory: {self.target}")
        if not _is_apgr_receipt(self.target):
            raise InvocationError(
                f"summary file exists and is not a recognized APGR receipt: {self.target}"
            )
        try:
            self.target.unlink()
        except OSError as error:
            raise InvocationError(f"failed to invalidate stale summary file: {error}") from error

    def write(
        self,
        *,
        suite: str,
        test_status: str,
        gate_status: str,
        source_commit: str,
    ) -> None:
        """Atomically write mode-private (0o600) summary JSON."""
        write_summary(
            self.target,
            suite=suite,
            test_status=test_status,
            gate_status=gate_status,
            source_commit=source_commit,
        )


def _is_apgr_receipt(path: Path) -> bool:
    """Verify that path points to a strict 6-field APGR qualification receipt."""
    try:
        resolved = path.resolve()
        if not resolved.is_file():
            return False
        content = resolved.read_bytes()
        if len(content) > 1024 * 1024:
            return False
        data = json.loads(content.decode("utf-8"))
        if not isinstance(data, dict):
            return False
        expected_keys = {"version", "subproject", "suite", "test_status", "gate_status", "source_commit"}
        commit = data.get("source_commit")
        return (
            set(data.keys()) == expected_keys
            and data.get("version") == 1
            and data.get("subproject") == "apg"
            and data.get("suite") in ("policy", "unit", "integration", "combined", "unknown")
            and data.get("test_status") in ("pass", "fail", "error")
            and data.get("gate_status") in ("pass", "fail", "error")
            and isinstance(commit, str)
            and len(commit) == 40
            and all(c in "0123456789abcdefABCDEF" for c in commit)
        )
    except (OSError, UnicodeError, ValueError):
        return False


def _git_metadata_paths(root: Path) -> set[Path]:
    """Resolve actual Git metadata directory paths for root, supporting linked worktrees."""
    paths: set[Path] = set()
    for flag in ("--git-dir", "--git-common-dir"):
        try:
            completed = subprocess.run(
                ["git", "rev-parse", flag],
                cwd=root,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=5,
            )
            if completed.returncode == 0 and completed.stdout.strip():
                git_path = Path(completed.stdout.strip())
                if not git_path.is_absolute():
                    git_path = (root / git_path).resolve()
                else:
                    git_path = git_path.resolve()
                paths.add(git_path)
        except (OSError, subprocess.TimeoutExpired):
            pass
    return paths


def admit_summary_destination(root: Path, target: Path) -> SummaryDestination:
    """Verify target summary path is safe from overwriting repo code or Git authority."""
    if ".git" in target.parts or target.name == ".git":
        raise InvocationError(f"summary file cannot target Git metadata: {target}")

    if target.is_symlink():
        raise InvocationError(f"summary file cannot target a symlink: {target}")

    resolved_root = root.resolve(strict=True)
    norm_root = Path(os.path.normpath(str(root)))

    raw_target = target if target.is_absolute() else (Path.cwd() / target)
    lexical_target = Path(os.path.normpath(str(raw_target)))
    addressed_in_parent = lexical_target.parent.resolve() / lexical_target.name

    if addressed_in_parent.is_symlink():
        raise InvocationError(f"summary file cannot target a symlink: {target}")

    resolved_target = target.resolve()

    for path_rep in (lexical_target, addressed_in_parent, resolved_target):
        if ".git" in path_rep.parts or path_rep.name == ".git":
            raise InvocationError(f"summary file cannot target Git metadata: {target}")

    for git_meta in _git_metadata_paths(resolved_root):
        for path_rep in (lexical_target, addressed_in_parent, resolved_target):
            if path_rep == git_meta or git_meta in path_rep.parents:
                raise InvocationError(f"summary file cannot target Git metadata: {target}")

    if resolved_root in (resolved_target, lexical_target, addressed_in_parent) or lexical_target == norm_root:
        raise InvocationError(f"summary file cannot target repository root: {target}")

    if any(p.is_dir() for p in (target, lexical_target, addressed_in_parent) if p.exists()) or (resolved_target.exists() and resolved_target.is_dir()):
        raise InvocationError(f"summary file cannot target a directory: {target}")

    in_repo_rels: list[Path] = []
    for candidate_path in (resolved_target, addressed_in_parent, lexical_target):
        for root_cand in (resolved_root, norm_root):
            if root_cand in candidate_path.parents:
                rel = candidate_path.relative_to(root_cand)
                if rel not in in_repo_rels:
                    in_repo_rels.append(rel)

    for rel in in_repo_rels:
        try:
            tracked_proc = subprocess.run(
                ["git", "ls-files", "--error-unmatch", str(rel)],
                cwd=resolved_root,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
            if tracked_proc.returncode == 0:
                raise InvocationError(
                    f"summary file inside repository cannot target tracked file: {target}"
                )
        except subprocess.TimeoutExpired as error:
            raise InvocationError(
                f"git ls-files timed out probing summary destination: {target}"
            ) from error
        except OSError as error:
            raise InvocationError(
                f"failed to probe git tracking status: {error}"
            ) from error

        try:
            ignored_proc = subprocess.run(
                ["git", "check-ignore", "-q", str(rel)],
                cwd=resolved_root,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
            is_ignored = (ignored_proc.returncode == 0)
        except (OSError, subprocess.TimeoutExpired):
            is_ignored = False

        if not is_ignored:
            raise InvocationError(
                f"summary file inside repository must be gitignored: {target}"
            )

    return SummaryDestination(target, resolved_target, resolved_root)


def admit_export_destination(root: Path, target: Path) -> Path:
    """Verify target coverage export directory is safe from Git metadata and repository root."""
    if ".git" in target.parts or target.name == ".git":
        raise InvocationError(f"export directory cannot target Git metadata: {target}")
    if target.is_symlink():
        raise InvocationError(f"export directory cannot target a symlink: {target}")
    resolved_root = root.resolve(strict=True)
    raw_target = target if target.is_absolute() else (Path.cwd() / target)
    resolved_target = raw_target.resolve()
    if resolved_target == resolved_root:
        raise InvocationError(f"export directory cannot target repository root: {target}")
    for git_meta in _git_metadata_paths(resolved_root):
        if resolved_target == git_meta or git_meta in resolved_target.parents:
            raise InvocationError(f"export directory cannot target Git metadata: {target}")
    return resolved_target


def _scan_early_args(raw_args: Sequence[str]) -> tuple[str, Path | None]:
    """Scan raw CLI arguments early for suite and summary-file path without raising."""
    summary_file_early: Path | None = None
    suite_early: str = "unknown"
    idx = 0
    while idx < len(raw_args):
        token = raw_args[idx]
        if token in ("unit", "integration", "unit-integration", "policy"):
            suite_early = "combined" if token == "unit-integration" else token
        elif token == "--summary-file":
            if idx + 1 < len(raw_args) and not raw_args[idx + 1].startswith("-"):
                summary_file_early = Path(raw_args[idx + 1])
                idx += 1
            else:
                summary_file_early = None
        elif token.startswith("--summary-file="):
            val = token.split("=", 1)[1]
            if val and not val.startswith("-"):
                summary_file_early = Path(val)
            else:
                summary_file_early = None
        idx += 1
    return suite_early, summary_file_early


def run_policy(root: Path) -> None:
    """Execute inventory, skill, record identity and roadmap-governance policy."""
    inventory = load_inventory(root)
    validate_inventory(root, inventory)
    dependency_versions()

    import apg_skill_library_check
    import apg_record_identity
    import apg_roadmap_closure

    skill_result = apg_skill_library_check.check_library(root)
    if not skill_result.passed:
        raise PolicyCheckError("skill library policy check failed")
    corpus_failure = apg_skill_library_check._embedded_corpus_failure(root)
    if corpus_failure is not None:
        raise PolicyCheckError(f"skill library corpus identity check failed: {corpus_failure}")

    record_result = apg_record_identity.check_records(root)
    if not record_result.passed:
        raise PolicyCheckError("record identity policy check failed")

    closure_result = apg_roadmap_closure.check_roadmap_closure(root)
    if not closure_result["passed"]:
        raise PolicyCheckError("roadmap closure policy check failed")

    print("PASS policy: inventory, skill-library, record-identity, and roadmap-closure checks passed")


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        prog=COMMAND,
        description="Run APG pytest suites with xdist and exact coverage gates.",
    )
    value.add_argument(
        "suite",
        choices=("unit", "integration", "unit-integration", "policy"),
    )
    value.add_argument("--workers", type=int, default=8)
    value.add_argument("--keep-artifacts-on-failure", action="store_true")
    value.add_argument(
        "--verify-failure-mode",
        choices=("worker-crash", "missing-child"),
    )
    value.add_argument(
        "--summary-file",
        type=Path,
        default=None,
        help="write machine-readable JACA CI qualification summary JSON",
    )
    value.add_argument(
        "--public-version",
        default=None,
        help="run the exact clean public projection for this release version",
    )
    value.add_argument(
        "--export-coverage",
        type=Path,
        default=None,
        help="export retained coverage JSON artifacts to target directory",
    )
    return value


def main(arguments: Sequence[str] | None = None) -> int:
    raw_args = list(sys.argv[1:] if arguments is None else arguments)
    suite_early, summary_file_early = _scan_early_args(raw_args)

    root = Path(__file__).resolve(strict=True).parent.parent
    try:
        entry_commit = resolve_source_commit(root)
    except ToolError:
        entry_commit = None

    try:
        args = parser().parse_args(arguments)
    except SystemExit as exc:
        if exc.code != 0 and summary_file_early is not None:
            try:
                early_dest = admit_summary_destination(root, summary_file_early)
                early_dest.invalidate()
                if entry_commit is not None:
                    early_dest.write(
                        suite=suite_early,
                        test_status="error",
                        gate_status="error",
                        source_commit=entry_commit,
                    )
            except InvocationError:
                pass
        raise

    suite = "combined" if args.suite == "unit-integration" else args.suite
    destination: SummaryDestination | None = None
    if args.summary_file is not None:
        try:
            destination = admit_summary_destination(root, args.summary_file)
            destination.invalidate()
        except InvocationError as error:
            print(f"{COMMAND}: {error}", file=sys.stderr)
            return 1

    export_dir: Path | None = None
    if args.export_coverage is not None:
        try:
            export_dir = admit_export_destination(root, args.export_coverage)
        except InvocationError as error:
            print(f"{COMMAND}: {error}", file=sys.stderr)
            return 1

    def _write_admitted(test_status: str, gate_status: str) -> bool:
        if destination is None:
            return True

        def _safe_invalidate() -> None:
            try:
                destination.invalidate()
            except InvocationError as error:
                print(f"{COMMAND}: {error}", file=sys.stderr)

        if entry_commit is None:
            print(f"{COMMAND}: resolve source commit: git unavailable", file=sys.stderr)
            _safe_invalidate()
            return False
        try:
            exit_commit = resolve_source_commit(root)
        except ToolError as error:
            print(f"{COMMAND}: {error}", file=sys.stderr)
            _safe_invalidate()
            return False
        if exit_commit != entry_commit:
            print(
                f"{COMMAND}: git HEAD drifted during execution (entry {entry_commit} != exit {exit_commit})",
                file=sys.stderr,
            )
            _safe_invalidate()
            return False
        try:
            destination.write(
                suite=suite,
                test_status=test_status,
                gate_status=gate_status,
                source_commit=exit_commit,
            )
            return True
        except Exception as error:
            print(
                f"{COMMAND}: failed to write summary file {destination.target}: {error}",
                file=sys.stderr,
            )
            _safe_invalidate()
            return False

    try:
        if args.public_version is not None and suite == "policy":
            raise InvocationError("--public-version applies only to test suites")
        if suite == "policy":
            run_policy(root)
        else:
            run_kwargs: dict[str, object] = {
                "keep_artifacts_on_failure": args.keep_artifacts_on_failure,
                "failure_mode": args.verify_failure_mode,
                "public_version": args.public_version,
            }
            if export_dir is not None:
                run_kwargs["export_coverage"] = export_dir
            run(suite, args.workers, root, **run_kwargs)
        if not _write_admitted("pass", "pass"):
            return 1
        return 0
    except GateShortfallError as error:
        _write_admitted("pass", "fail")
        print(f"{COMMAND}: {error}", file=sys.stderr)
        return 1
    except InvocationError as error:
        _write_admitted("error", "error")
        print(f"{COMMAND}: {error}", file=sys.stderr)
        return 1
    except HarnessError as error:
        _write_admitted("error", "error")
        print(f"{COMMAND}: {error}", file=sys.stderr)
        return 1
    except (PolicyCheckError, TestAssertionError, ToolError) as error:
        _write_admitted("fail", "fail")
        print(f"{COMMAND}: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        _write_admitted("error", "error")
        print(f"{COMMAND}: interrupted", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
