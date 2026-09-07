"""Unit tests for APG's pytest, coverage, and mirror-policy runner."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import inspect
import json
import os
from pathlib import Path
import shutil
import stat
import sys

import pytest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import apg_test  # noqa: E402


def write_inventory(root: Path, value: object) -> None:
    path = root / apg_test.INVENTORY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def minimal_inventory() -> dict[str, object]:
    return {
        "schema_version": 2,
        "coverage_sources": [
            {
                "path": "libexec/tool.py",
                "rationale": "unit policy owner",
                "suites": ["unit", "integration", "combined"],
            }
        ],
        "excluded_python_launchers": [
            {"path": "bin/tool", "reason": "thin import and exit adapter"}
        ],
        "tests": [
            {
                "owner": "libexec/tool.py",
                "path": (
                    "src/test/unit/python/agentic-praxis-grimoire/"
                    "libexec/tool.unit.test.py"
                ),
                "suite": "unit",
            }
        ],
    }


def materialize_inventory_tree(root: Path) -> None:
    value = minimal_inventory()
    for relative in (
        "libexec/tool.py",
        "src/test/unit/python/agentic-praxis-grimoire/libexec/tool.unit.test.py",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("value = 1\n", encoding="utf-8")
    launcher = root / "bin/tool"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    write_inventory(root, value)


def test_exact_threshold_arithmetic_does_not_use_display_rounding() -> None:
    apg_test.enforce_threshold(apg_test.CoverageCounts(4, 5, 8, 10), 80, 80)
    with pytest.raises(apg_test.ToolError, match="statement coverage"):
        apg_test.enforce_threshold(apg_test.CoverageCounts(799, 1000, 8, 10), 80, 80)
    with pytest.raises(apg_test.ToolError, match="branch coverage"):
        apg_test.enforce_threshold(apg_test.CoverageCounts(8, 10, 799, 1000), 80, 80)


def test_coverage_counts_require_exact_sources_and_measurable_branches() -> None:
    report = {
        "files": {
            "libexec/a.py": {
                "summary": {
                    "covered_lines": 8,
                    "num_statements": 10,
                    "covered_branches": 4,
                    "num_branches": 5,
                }
            }
        }
    }
    assert apg_test.coverage_counts(report, ["libexec/a.py"]) == apg_test.CoverageCounts(
        8, 10, 4, 5
    )
    with pytest.raises(apg_test.ToolError, match="omits required source"):
        apg_test.coverage_counts(report, ["libexec/missing.py"])
    with pytest.raises(apg_test.ToolError, match="zero statements or branches"):
        apg_test.coverage_counts(
            {"files": {"libexec/a.py": {"summary": {
                "covered_lines": 1, "num_statements": 1,
                "covered_branches": 0, "num_branches": 0,
            }}}},
            ["libexec/a.py"],
        )


@pytest.mark.parametrize(
    "field,value,message",
    [
        ("covered_lines", True, "malformed"),
        ("covered_lines", 8.0, "malformed"),
        ("covered_lines", "8", "malformed"),
        ("covered_lines", -1, "impossible"),
        ("covered_lines", 11, "impossible"),
        ("num_statements", -1, "impossible"),
        ("covered_branches", -1, "impossible"),
        ("covered_branches", 6, "impossible"),
        ("num_branches", -1, "impossible"),
    ],
)
def test_coverage_counts_reject_malformed_and_impossible_values(
    field: str, value: object, message: str
) -> None:
    summary: dict[str, object] = {
        "covered_lines": 8,
        "num_statements": 10,
        "covered_branches": 4,
        "num_branches": 5,
    }
    summary[field] = value
    with pytest.raises(apg_test.ToolError, match=message):
        apg_test.coverage_counts(
            {"files": {"libexec/a.py": {"summary": summary}}},
            ["libexec/a.py"],
        )


def test_coverage_report_rejects_missing_and_foreign_sources() -> None:
    apg_test.validate_coverage_report(
        {"files": {"libexec/a.py": {}}}, {"libexec/a.py"}
    )
    with pytest.raises(apg_test.ToolError, match="missing=.*b.py"):
        apg_test.validate_coverage_report(
            {"files": {"libexec/a.py": {}}},
            {"libexec/a.py", "libexec/b.py"},
        )
    with pytest.raises(apg_test.ToolError, match="foreign=.*outside.py"):
        apg_test.validate_coverage_report(
            {"files": {"libexec/a.py": {}, "outside.py": {}}},
            {"libexec/a.py"},
        )


def test_strict_inventory_rejects_duplicate_and_unknown_data(tmp_path: Path) -> None:
    write_inventory(tmp_path, minimal_inventory())
    loaded = apg_test.load_inventory(tmp_path)
    assert loaded.tests

    inventory_path = tmp_path / apg_test.INVENTORY_PATH
    inventory_path.write_text('{"schema_version":2,"schema_version":2}', encoding="utf-8")
    with pytest.raises(apg_test.ToolError, match="duplicate key"):
        apg_test.load_inventory(tmp_path)

    value = minimal_inventory()
    value["unexpected"] = True
    write_inventory(tmp_path, value)
    with pytest.raises(apg_test.ToolError, match="top-level fields"):
        apg_test.load_inventory(tmp_path)


def test_inventory_rejects_invalid_source_launcher_and_test_entries(tmp_path: Path) -> None:
    cases: list[tuple[dict[str, object], str]] = []

    value = minimal_inventory()
    value["schema_version"] = 1
    cases.append((value, "schema_version"))

    value = minimal_inventory()
    value["coverage_sources"] = []
    cases.append((value, "nonempty array"))

    value = minimal_inventory()
    value["coverage_sources"][0]["suites"] = ["unknown"]
    cases.append((value, "suites are invalid"))

    value = minimal_inventory()
    value["coverage_sources"].append(value["coverage_sources"][0].copy())
    cases.append((value, "duplicate coverage source"))

    value = minimal_inventory()
    value["excluded_python_launchers"][0]["reason"] = ""
    cases.append((value, "lacks a rationale"))

    value = minimal_inventory()
    value["tests"][0]["suite"] = "system"
    cases.append((value, "test suite is invalid"))

    value = minimal_inventory()
    value["tests"].append(value["tests"][0].copy())
    cases.append((value, "duplicate mirrored test"))

    value = minimal_inventory()
    value["coverage_sources"][0]["extra"] = True
    cases.append((value, "source entry"))

    value = minimal_inventory()
    value["excluded_python_launchers"] = "invalid"
    cases.append((value, "must be an array"))

    value = minimal_inventory()
    value["excluded_python_launchers"][0]["extra"] = True
    cases.append((value, "launcher entry"))

    value = minimal_inventory()
    value["tests"] = []
    cases.append((value, "nonempty array"))

    value = minimal_inventory()
    value["tests"][0]["extra"] = True
    cases.append((value, "test entry"))

    for candidate, message in cases:
        write_inventory(tmp_path, candidate)
        with pytest.raises(apg_test.ToolError, match=message):
            apg_test.load_inventory(tmp_path)


def test_inventory_detects_missing_stale_wrong_mirror_and_legacy_tests(
    tmp_path: Path,
) -> None:
    materialize_inventory_tree(tmp_path)
    inventory = apg_test.load_inventory(tmp_path)
    apg_test.validate_inventory(tmp_path, inventory)

    (tmp_path / "libexec/extra.py").write_text("value = 2\n", encoding="utf-8")
    with pytest.raises(apg_test.PolicyCheckError, match="coverage source inventory differs"):
        apg_test.validate_inventory(tmp_path, inventory)
    (tmp_path / "libexec/extra.py").unlink()

    value = minimal_inventory()
    value["tests"][0]["path"] = (
        "src/test/unit/python/agentic-praxis-grimoire/libexec/wrong.unit.test.py"
    )
    wrong = tmp_path / value["tests"][0]["path"]
    wrong.write_text("value = 1\n", encoding="utf-8")
    original = tmp_path / minimal_inventory()["tests"][0]["path"]
    original.unlink()
    write_inventory(tmp_path, value)
    with pytest.raises(apg_test.PolicyCheckError, match="disagrees with owner"):
        apg_test.validate_inventory(tmp_path, apg_test.load_inventory(tmp_path))

    legacy = tmp_path / "src/test/unit/python/legacy.test.py"
    legacy.write_text("value = 1\n", encoding="utf-8")
    with pytest.raises(apg_test.PolicyCheckError, match="stale legacy"):
        apg_test.validate_inventory(tmp_path, apg_test.load_inventory(tmp_path))


def test_dependency_versions_are_exact(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(apg_test.metadata, "version", lambda name: apg_test.EXPECTED_VERSIONS[name])
    assert apg_test.dependency_versions() == apg_test.EXPECTED_VERSIONS
    monkeypatch.setattr(apg_test.metadata, "version", lambda _name: "0")
    with pytest.raises(apg_test.ToolError, match="version mismatch"):
        apg_test.dependency_versions()


def test_typescript_compiler_prerequisite_is_missing_wrong_or_exact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    monkeypatch.delenv("APG_TYPESCRIPT_TSC", raising=False)
    with pytest.raises(apg_test.ToolError, match="APG_TYPESCRIPT_TSC"):
        apg_test.validate_typescript_compiler(root)

    compiler = tmp_path / "tooling" / "tsc"
    compiler.parent.mkdir()
    compiler.write_text("#!/bin/sh\nprintf 'Version 6.0.3\\n'\n", encoding="utf-8")
    compiler.chmod(0o755)
    monkeypatch.setenv("APG_TYPESCRIPT_TSC", str(compiler))
    with pytest.raises(apg_test.ToolError, match="expected Version 7.0.2"):
        apg_test.validate_typescript_compiler(root)

    compiler.write_text("#!/bin/sh\nprintf 'Version 7.0.2\\n'\n", encoding="utf-8")
    assert apg_test.validate_typescript_compiler(root) == "Version 7.0.2"

    checkout_compiler = root / "tsc"
    checkout_compiler.write_bytes(compiler.read_bytes())
    checkout_compiler.chmod(0o755)
    monkeypatch.setenv("APG_TYPESCRIPT_TSC", str(checkout_compiler))
    with pytest.raises(apg_test.ToolError, match="outside the repository"):
        apg_test.validate_typescript_compiler(root)

    compiler_link = tmp_path / "linked-tsc"
    compiler_link.symlink_to(compiler)
    monkeypatch.setenv("APG_TYPESCRIPT_TSC", str(compiler_link))
    with pytest.raises(apg_test.ToolError, match="regular executable"):
        apg_test.validate_typescript_compiler(root)
    monkeypatch.setattr(
        apg_test.metadata,
        "version",
        lambda _name: (_ for _ in ()).throw(apg_test.metadata.PackageNotFoundError()),
    )
    with pytest.raises(apg_test.ToolError, match="not installed"):
        apg_test.dependency_versions()


def test_typescript_prerequisite_follows_validated_test_ownership() -> None:
    historical = apg_test.Inventory({}, {}, {})
    assert not apg_test.requires_typescript_compiler(historical)
    current = apg_test.Inventory(
        {},
        {},
        {
            next(iter(apg_test.TYPESCRIPT_COMPILER_TEST_PATHS)): (
                "skills/typescript-language-profile/SKILL.md",
                "integration",
            )
        },
    )
    assert apg_test.requires_typescript_compiler(current)


def test_javascript_engine_prerequisite_is_missing_unsafe_wrong_or_exact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    monkeypatch.delenv("APG_JAVASCRIPT_NODE", raising=False)
    with pytest.raises(apg_test.ToolError, match="APG_JAVASCRIPT_NODE"):
        apg_test.validate_javascript_engine(root)

    engine = tmp_path / "tooling" / "node"
    engine.parent.mkdir()
    engine.write_text(
        "#!/bin/sh\nprintf 'v20.0.0|darwin/arm64|0\\n'\n", encoding="utf-8"
    )
    engine.chmod(0o755)
    monkeypatch.setattr(apg_test, "EXPECTED_JAVASCRIPT_ENGINE_ROOT", tmp_path)
    monkeypatch.setattr(apg_test, "EXPECTED_JAVASCRIPT_ENGINE_UID", os.getuid())
    monkeypatch.setattr(
        apg_test,
        "EXPECTED_JAVASCRIPT_ENGINE_SHA256",
        hashlib.sha256(engine.read_bytes()).hexdigest(),
    )
    monkeypatch.setenv("APG_JAVASCRIPT_NODE", str(engine))
    with pytest.raises(apg_test.ToolError, match="identity mismatch"):
        apg_test.validate_javascript_engine(root)

    engine.write_text(
        "#!/bin/sh\nprintf 'v22.22.2|darwin/arm64|12.4.254.21-node.39\\n'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        apg_test,
        "EXPECTED_JAVASCRIPT_ENGINE_SHA256",
        hashlib.sha256(engine.read_bytes()).hexdigest(),
    )
    assert apg_test.validate_javascript_engine(root) == apg_test.EXPECTED_JAVASCRIPT_ENGINE

    monkeypatch.setattr(apg_test, "EXPECTED_JAVASCRIPT_ENGINE_SHA256", "0" * 64)
    with pytest.raises(apg_test.ToolError, match="digest mismatch"):
        apg_test.validate_javascript_engine(root)

    linked = tmp_path / "linked-node"
    linked.symlink_to(engine)
    monkeypatch.setenv("APG_JAVASCRIPT_NODE", str(linked))
    with pytest.raises(apg_test.ToolError, match="regular executable"):
        apg_test.validate_javascript_engine(root)

    linked_parent = tmp_path / "linked-parent"
    linked_parent.symlink_to(engine.parent, target_is_directory=True)
    monkeypatch.setenv("APG_JAVASCRIPT_NODE", str(linked_parent / engine.name))
    with pytest.raises(apg_test.ToolError, match="symlinked path components"):
        apg_test.validate_javascript_engine(root)

    checkout_engine = root / "node"
    checkout_engine.write_bytes(engine.read_bytes())
    checkout_engine.chmod(0o755)
    monkeypatch.setenv("APG_JAVASCRIPT_NODE", str(checkout_engine))
    with pytest.raises(apg_test.ToolError, match="outside the repository"):
        apg_test.validate_javascript_engine(root)


def test_javascript_engine_replacement_during_validation_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    engine = tmp_path / "node"
    engine.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    engine.chmod(0o755)
    monkeypatch.setattr(apg_test, "EXPECTED_JAVASCRIPT_ENGINE_ROOT", tmp_path)
    monkeypatch.setattr(apg_test, "EXPECTED_JAVASCRIPT_ENGINE_UID", os.getuid())
    monkeypatch.setattr(
        apg_test,
        "EXPECTED_JAVASCRIPT_ENGINE_SHA256",
        hashlib.sha256(engine.read_bytes()).hexdigest(),
    )
    monkeypatch.setenv("APG_JAVASCRIPT_NODE", str(engine))

    def replace_engine(*args: object, **kwargs: object) -> apg_test.subprocess.CompletedProcess[str]:
        engine.write_text("#!/bin/sh\nprintf changed\n", encoding="utf-8")
        engine.chmod(0o755)
        return apg_test.subprocess.CompletedProcess(
            args[0], 0, apg_test.EXPECTED_JAVASCRIPT_ENGINE + "\n"
        )

    monkeypatch.setattr(apg_test, "_run_javascript_process", replace_engine)
    with pytest.raises(apg_test.ToolError, match="changed during validation"):
        apg_test.validate_javascript_engine(root)


def test_javascript_engine_rejects_relative_directory_nonexecutable_root_and_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    engine = tmp_path / "tooling" / "node"
    engine.parent.mkdir()
    engine.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    engine.chmod(0o755)
    monkeypatch.setenv("APG_JAVASCRIPT_NODE", "relative/node")
    with pytest.raises(apg_test.ToolError, match="absolute regular executable"):
        apg_test.validate_javascript_engine(root)
    monkeypatch.setenv("APG_JAVASCRIPT_NODE", str(engine.parent))
    with pytest.raises(apg_test.ToolError, match="absolute regular executable"):
        apg_test.validate_javascript_engine(root)
    engine.chmod(0o644)
    monkeypatch.setenv("APG_JAVASCRIPT_NODE", str(engine))
    with pytest.raises(apg_test.ToolError, match="absolute regular executable"):
        apg_test.validate_javascript_engine(root)
    engine.chmod(0o755)
    monkeypatch.setattr(apg_test, "EXPECTED_JAVASCRIPT_ENGINE_ROOT", tmp_path / "approved")
    with pytest.raises(apg_test.ToolError, match="immutable Nix-store engine"):
        apg_test.validate_javascript_engine(root)
    monkeypatch.setattr(apg_test, "EXPECTED_JAVASCRIPT_ENGINE_ROOT", tmp_path)
    monkeypatch.setattr(apg_test, "EXPECTED_JAVASCRIPT_ENGINE_UID", os.getuid() + 1)
    with pytest.raises(apg_test.ToolError, match="owned by root"):
        apg_test.validate_javascript_engine(root)


def test_javascript_prerequisite_follows_validated_test_ownership() -> None:
    historical = apg_test.Inventory({}, {}, {})
    assert not apg_test.requires_javascript_engine(historical)
    current = apg_test.Inventory(
        {},
        {},
        {
            next(iter(apg_test.JAVASCRIPT_ENGINE_TEST_PATHS)): (
                "skills/javascript-language-profile/SKILL.md",
                "integration",
            )
        },
    )
    assert apg_test.requires_javascript_engine(current)


def test_node_profile_prerequisite_follows_validated_test_ownership() -> None:
    historical = apg_test.Inventory({}, {}, {})
    assert not apg_test.requires_node_profile_runtimes(historical)
    current = apg_test.Inventory(
        {}, {}, {
            next(iter(apg_test.NODE_PROFILE_RUNTIME_TEST_PATHS)): (
                "skills/nodejs-runtime-profile/SKILL.md", "integration"
            )
        }
    )
    assert apg_test.requires_node_profile_runtimes(current)


def test_node_profile_prerequisites_are_exact_direct_distinct_and_external(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    primary = tmp_path / "primary-node"
    secondary = tmp_path / "secondary-node"
    primary_identity = "v22.22.2|darwin/arm64|12.4.254.21-node.39|1.51.0"
    secondary_identity = "v24.19.0|darwin/arm64|13.6.233.17-node.51|1.52.1"
    for executable, identity in ((primary, primary_identity), (secondary, secondary_identity)):
        probe = json.dumps({"identity": identity, "execArgv": [], "nodeOptions": False})
        executable.write_text(f"#!/bin/sh\nprintf '%s\\n' '{probe}'\n", encoding="utf-8")
        executable.chmod(0o755)
    contracts = {
        "primary": ("APG_NODEJS_PRIMARY_NODE", primary_identity, hashlib.sha256(primary.read_bytes()).hexdigest()),
        "secondary": ("APG_NODEJS_SECONDARY_NODE", secondary_identity, hashlib.sha256(secondary.read_bytes()).hexdigest()),
    }
    monkeypatch.setattr(apg_test, "NODE_PROFILE_RUNTIME_CONTRACTS", contracts)
    monkeypatch.setenv("APG_NODEJS_OWNED_SCRATCH_ROOT", str(tmp_path))
    monkeypatch.setenv("NODE_OPTIONS", "--trace-warnings")
    monkeypatch.setenv("APG_NODEJS_PRIMARY_NODE", str(primary))
    monkeypatch.setenv("APG_NODEJS_SECONDARY_NODE", str(secondary))
    assert apg_test.validate_node_profile_runtimes(root) == (primary_identity, secondary_identity)

    monkeypatch.delenv("APG_NODEJS_SECONDARY_NODE")
    with pytest.raises(apg_test.ToolError, match="APG_NODEJS_SECONDARY_NODE"):
        apg_test.validate_node_profile_runtimes(root)
    monkeypatch.setenv("APG_NODEJS_SECONDARY_NODE", str(primary))
    monkeypatch.setattr(
        apg_test,
        "NODE_PROFILE_RUNTIME_CONTRACTS",
        {**contracts, "secondary": ("APG_NODEJS_SECONDARY_NODE", primary_identity, contracts["primary"][2])},
    )
    with pytest.raises(apg_test.ToolError, match="remain distinct"):
        apg_test.validate_node_profile_runtimes(root)
    linked = tmp_path / "linked-node"
    linked.symlink_to(secondary)
    monkeypatch.setenv("APG_NODEJS_SECONDARY_NODE", str(linked))
    monkeypatch.setattr(apg_test, "NODE_PROFILE_RUNTIME_CONTRACTS", contracts)
    with pytest.raises(apg_test.ToolError, match="direct regular executable"):
        apg_test.validate_node_profile_runtimes(root)
    checkout_node = root / "node"
    checkout_node.write_bytes(secondary.read_bytes())
    checkout_node.chmod(0o755)
    monkeypatch.setenv("APG_NODEJS_SECONDARY_NODE", str(checkout_node))
    with pytest.raises(apg_test.ToolError, match="outside the repository"):
        apg_test.validate_node_profile_runtimes(root)


def test_node_profile_invocation_topology_is_unique_closed_private_and_cleaned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repository"
    owned = tmp_path / "owned"
    root.mkdir()
    owned.mkdir()
    monkeypatch.setenv("APG_NODEJS_OWNED_SCRATCH_ROOT", os.fspath(owned))
    roots = []
    for _ in range(2):
        with apg_test.node_profile_invocation(root, "primary-owned-scratch") as invocation:
            roots.append(invocation.root)
            assert invocation.root.parent == owned
            assert invocation.environment == {
                "NO_COLOR": "1",
                "PNPM_HOME": os.fspath(invocation.pnpm_home),
                "TEMP": os.fspath(invocation.temporary),
                "TMP": os.fspath(invocation.temporary),
                "TMPDIR": os.fspath(invocation.temporary),
                "npm_config_cache": os.fspath(invocation.npm_cache),
            }
            assert all(
                stat.S_IMODE(path.lstat().st_mode) == 0o700
                for path in (
                    invocation.root,
                    invocation.temporary,
                    invocation.npm_cache,
                    invocation.pnpm_home,
                    invocation.work,
                    invocation.filesystem_case,
                )
            )
        assert not roots[-1].exists()
    assert roots[0] != roots[1]
    monkeypatch.delenv("APG_NODEJS_OWNED_SCRATCH_ROOT")
    with pytest.raises(apg_test.ToolError, match="scratch owner is unavailable"):
        apg_test._node_profile_owned_scratch(root)


def test_node_profile_invocation_rejects_symlink_escape_and_repository_ancestry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repository"
    owned = tmp_path / "owned"
    root.mkdir()
    owned.mkdir()
    monkeypatch.setenv("APG_NODEJS_OWNED_SCRATCH_ROOT", os.fspath(owned))
    with apg_test.node_profile_invocation(root, "primary-scratch-symlink-refusal") as invocation:
        outside = tmp_path / "outside"
        outside.mkdir()
        forged = apg_test.NodeProfileInvocation(
            invocation.contract_id,
            invocation.root,
            invocation.temporary,
            invocation.npm_cache,
            invocation.pnpm_home,
            invocation.work,
            outside,
        )
        with pytest.raises(apg_test.ToolError, match="topology is not exact"):
            apg_test._validate_node_profile_invocation(root, forged)
        invocation.filesystem_case.rmdir()
        invocation.filesystem_case.symlink_to(outside, target_is_directory=True)
        with pytest.raises(apg_test.ToolError, match="fs-case directory violates"):
            apg_test._validate_node_profile_invocation(root, invocation)
    linked_owner = tmp_path / "linked-owner"
    linked_owner.symlink_to(owned, target_is_directory=True)
    monkeypatch.setenv("APG_NODEJS_OWNED_SCRATCH_ROOT", os.fspath(linked_owner))
    with pytest.raises(apg_test.ToolError, match="separate external"):
        apg_test._node_profile_owned_scratch(root)
    nested_owner = root / "nested-owner"
    nested_owner.mkdir()
    monkeypatch.setenv("APG_NODEJS_OWNED_SCRATCH_ROOT", os.fspath(nested_owner))
    with pytest.raises(apg_test.ToolError, match="separate external"):
        apg_test._node_profile_owned_scratch(root)
    parent_owner = tmp_path.parent
    monkeypatch.setenv("APG_NODEJS_OWNED_SCRATCH_ROOT", os.fspath(parent_owner))
    with pytest.raises(apg_test.ToolError, match="separate external"):
        apg_test._node_profile_owned_scratch(root)


def test_node_profile_topology_rejects_relative_lexical_ancestor_missing_and_mode_gaps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repository"
    owned = tmp_path / "owned"
    root.mkdir()
    owned.mkdir()

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APG_NODEJS_OWNED_SCRATCH_ROOT", "owned")
    with pytest.raises(apg_test.ToolError, match="separate external"):
        apg_test._node_profile_owned_scratch(root)

    lexical = owned / "child" / ".."
    (owned / "child").mkdir()
    monkeypatch.setenv("APG_NODEJS_OWNED_SCRATCH_ROOT", os.fspath(lexical))
    with pytest.raises(apg_test.ToolError, match="separate external"):
        apg_test._node_profile_owned_scratch(root)

    real_parent = tmp_path / "real-parent"
    real_parent.mkdir()
    linked_parent = tmp_path / "linked-parent"
    linked_parent.symlink_to(real_parent, target_is_directory=True)
    linked_owned = linked_parent / "owned"
    (real_parent / "owned").mkdir()
    monkeypatch.setenv("APG_NODEJS_OWNED_SCRATCH_ROOT", os.fspath(linked_owned))
    with pytest.raises(apg_test.ToolError, match="separate external"):
        apg_test._node_profile_owned_scratch(root)

    monkeypatch.setenv("APG_NODEJS_OWNED_SCRATCH_ROOT", os.fspath(owned))
    with apg_test.node_profile_invocation(root, "primary-owned-scratch") as invocation:
        invocation.filesystem_case.rmdir()
        with pytest.raises(apg_test.ToolError, match="fs-case directory is unavailable"):
            apg_test._validate_node_profile_invocation(root, invocation)
        invocation.filesystem_case.mkdir(mode=0o750)
        with pytest.raises(apg_test.ToolError, match="fs-case directory violates"):
            apg_test._validate_node_profile_invocation(root, invocation)


def test_node_profile_cleanup_attempts_all_and_reports_retained_artifact_truthfully(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repository"
    owned = tmp_path / "owned"
    root.mkdir()
    owned.mkdir()
    monkeypatch.setenv("APG_NODEJS_OWNED_SCRATCH_ROOT", os.fspath(owned))
    attempted = []
    retained_root = None

    def actions(invocation: apg_test.NodeProfileInvocation):
        def fail_first() -> None:
            attempted.append("first")
            raise OSError("synthetic")

        def run_later() -> None:
            attempted.append("later")

        return (("first", fail_first), ("later", run_later))

    monkeypatch.setattr(apg_test, "_node_profile_cleanup_actions", actions)
    with pytest.raises(apg_test.NodeProfileCleanupError) as captured:
        with apg_test.node_profile_invocation(root, "primary-owned-scratch") as invocation:
            retained_root = invocation.root
    assert attempted == ["first", "later"]
    assert retained_root is not None and retained_root.exists()
    assert "retained-artifact" in str(captured.value)
    assert os.fspath(retained_root) not in str(captured.value)
    shutil.rmtree(retained_root)


def test_node_profile_partial_rmtree_failure_is_truthful_and_retained(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repository"
    owned = tmp_path / "owned"
    root.mkdir()
    owned.mkdir()
    monkeypatch.setenv("APG_NODEJS_OWNED_SCRATCH_ROOT", os.fspath(owned))
    real_rmtree = shutil.rmtree
    retained_root = None

    def partial_rmtree(path: Path) -> None:
        (Path(path) / "tmp").rmdir()
        raise OSError("synthetic partial removal")

    monkeypatch.setattr(apg_test.shutil, "rmtree", partial_rmtree)
    with pytest.raises(apg_test.NodeProfileCleanupError) as captured:
        with apg_test.node_profile_invocation(root, "primary-owned-scratch") as invocation:
            retained_root = invocation.root
    assert retained_root is not None and retained_root.exists()
    assert "remove-root,retained-artifact" in str(captured.value)
    assert os.fspath(retained_root) not in str(captured.value)
    real_rmtree(retained_root)


def test_node_profile_setup_failure_cleans_before_bounded_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repository"
    owned = tmp_path / "owned"
    root.mkdir()
    owned.mkdir()
    monkeypatch.setenv("APG_NODEJS_OWNED_SCRATCH_ROOT", os.fspath(owned))
    monkeypatch.setattr(
        apg_test,
        "_validate_node_profile_invocation",
        lambda *_args: (_ for _ in ()).throw(apg_test.ToolError("synthetic")),
    )
    with pytest.raises(apg_test.NodeProfileQualificationError, match="setup failed"):
        with apg_test.node_profile_invocation(root, "primary-owned-scratch"):
            pytest.fail("setup failure must prevent yield")
    assert list(owned.iterdir()) == []


def test_node_profile_cleanup_absence_verification_failure_is_bounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class UnobservableRoot:
        def lstat(self):
            raise OSError("synthetic verification failure")

    invocation = apg_test.NodeProfileInvocation(
        "primary-owned-scratch",
        UnobservableRoot(),
        tmp_path / "tmp",
        tmp_path / "npm-cache",
        tmp_path / "pnpm-home",
        tmp_path / "work",
        tmp_path / "fs-case",
    )
    monkeypatch.setattr(apg_test, "_node_profile_cleanup_actions", lambda _invocation: ())
    assert apg_test._cleanup_node_profile_invocation(invocation) == "absence-verification"


def test_node_profile_retired_containment_machinery_cannot_reappear() -> None:
    source = (REPOSITORY_ROOT / "libexec/apg_test.py").read_text(encoding="utf-8")
    for retired in (
        "UF_IMMUTABLE",
        "os.chflags",
        "_pinned_node_profile_directories",
        "_sealed_node_profile_executable",
        "protected_directories",
        "node-runtime-",
    ):
        assert retired not in source
    current_claims = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            REPOSITORY_ROOT / "docs/specs/nodejs-runtime-profile.md",
            REPOSITORY_ROOT / "src/test/fixtures/apg80-nodejs-runtime-cli/README.md",
        )
    )
    for overclaim in (
        "pins the exact scratch root",
        "continuously bound",
    ):
        assert overclaim not in current_claims
    assert "not continuous identity" in current_claims
    assert "not a security boundary" in current_claims
    parameters = inspect.signature(apg_test.invoke_node_profile_runtime).parameters
    assert not {"cwd", "environment", "protected_directories"} & set(parameters)
    assert "invocation" in parameters


def test_node_profile_scratch_postflight_failure_still_observes_runtime_afterward(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repository"
    owned = tmp_path / "owned"
    outside = tmp_path / "outside"
    root.mkdir()
    owned.mkdir()
    outside.mkdir()
    monkeypatch.setenv("APG_NODEJS_OWNED_SCRATCH_ROOT", os.fspath(owned))
    binding = apg_test.NodeProfileRuntimeBinding(
        "primary", tmp_path / "node", (1, 2, 3, 4, 5, 6, 7), "a" * 64, "synthetic"
    )
    observations = []

    def observe(_root: Path, role: str) -> apg_test.NodeProfileRuntimeBinding:
        observations.append(role)
        return binding

    monkeypatch.setattr(apg_test, "_node_profile_runtime_binding", observe)
    contract = "primary-scratch-symlink-refusal"
    with apg_test.node_profile_invocation(root, contract) as invocation:
        def replace_case(*_args: object, **_kwargs: object):
            invocation.filesystem_case.rmdir()
            invocation.filesystem_case.symlink_to(outside, target_is_directory=True)
            return {"refused": True}, None

        monkeypatch.setattr(apg_test, "_execute_node_profile_contract", replace_case)
        with pytest.raises(
            apg_test.NodeProfileQualificationError, match="scratch postflight contract failed"
        ):
            apg_test.invoke_node_profile_runtime(
                root,
                "primary",
                ["--eval", "must-not-run"],
                invocation=invocation,
                output_contract_id=contract,
                expected_result={"refused": True},
            )
    assert observations == ["primary", "primary"]
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize("drift", ["path-identity", "metadata", "digest", "public-identity"])
def test_node_profile_low_level_runtime_post_probe_rejects_every_drift(
    drift: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    executable = tmp_path / "node"
    original = b"#!/bin/sh\nexit 0\n"
    executable.write_bytes(original)
    executable.chmod(0o755)
    expected_identity = "v-test|darwin/arm64|v8|uv"
    monkeypatch.setenv("APG_NODEJS_PRIMARY_NODE", os.fspath(executable))
    monkeypatch.setitem(
        apg_test.NODE_PROFILE_RUNTIME_CONTRACTS,
        "primary",
        ("APG_NODEJS_PRIMARY_NODE", expected_identity, hashlib.sha256(original).hexdigest()),
    )

    def probe(arguments: list[str], **_kwargs: object):
        public_identity = expected_identity
        if drift == "path-identity":
            moved = tmp_path / "node-original"
            executable.rename(moved)
            executable.write_bytes(original)
            executable.chmod(0o755)
        elif drift == "metadata":
            executable.chmod(0o700)
        elif drift == "digest":
            executable.write_bytes(b"#!/bin/sh\nexit 1\n")
            executable.chmod(0o755)
        else:
            public_identity = "wrong-public-identity"
        output = json.dumps(
            {"identity": public_identity, "execArgv": [], "nodeOptions": False}
        )
        return apg_test.subprocess.CompletedProcess(arguments, 0, output, "")

    monkeypatch.setattr(apg_test, "_run_javascript_process", probe)
    with pytest.raises(apg_test.NodeProfileQualificationError, match="runtime-binding"):
        apg_test._node_profile_runtime_binding(root, "primary")


def test_node_profile_cross_invocation_binding_drift_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contract = "redaction-negative"
    invocation = apg_test.NodeProfileInvocation(
        contract,
        tmp_path / "invocation",
        tmp_path / "invocation/tmp",
        tmp_path / "invocation/npm-cache",
        tmp_path / "invocation/pnpm-home",
        tmp_path / "invocation/work",
        tmp_path / "invocation/fs-case",
    )
    before = apg_test.NodeProfileRuntimeBinding(
        "primary", tmp_path / "node", (1, 2, 3, 4, 5, 6, 7), "a" * 64, "identity"
    )
    after = apg_test.NodeProfileRuntimeBinding(
        "primary", tmp_path / "node", (1, 9, 3, 4, 5, 6, 7), "a" * 64, "identity"
    )
    observations = iter((before, after))
    monkeypatch.setattr(apg_test, "_validate_node_profile_invocation", lambda *_args: None)
    monkeypatch.setattr(apg_test, "_node_profile_runtime_binding", lambda *_args: next(observations))
    monkeypatch.setattr(
        apg_test,
        "_execute_node_profile_contract",
        lambda *_args, **_kwargs: ({"secret": "expected-safe-value"}, None),
    )
    with pytest.raises(apg_test.NodeProfileQualificationError, match="binding changed"):
        apg_test.invoke_node_profile_runtime(
            tmp_path / "repository",
            "primary",
            ["--eval", "safe"],
            invocation=invocation,
            output_contract_id=contract,
            expected_result={"secret": "expected-safe-value"},
        )


def test_node_profile_invocation_rejects_unknown_output_contract() -> None:
    with pytest.raises(apg_test.ToolError, match="output contract is unknown"):
        with apg_test.node_profile_invocation(Path("/not-reached"), "unknown-contract"):
            pass


@pytest.mark.parametrize(
    "actual",
    [
        {"field": "same", "extra": True},
        {},
        {"field": 1},
        {"field": "different"},
    ],
)
def test_node_profile_closed_output_rejects_extra_missing_wrong_type_and_value(
    actual: object, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert not apg_test._exact_json_matches(actual, {"field": "same"})


def test_every_node_profile_structured_field_has_closed_mutation_negatives() -> None:
    def paths(value: object, prefix: tuple[object, ...] = ()):
        if isinstance(value, dict):
            for key, item in value.items():
                current = (*prefix, key)
                yield current
                yield from paths(item, current)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                current = (*prefix, index)
                yield current
                yield from paths(item, current)

    def at(value: object, path: tuple[object, ...]):
        for part in path:
            value = value[part]
        return value

    def replace(value: object, path: tuple[object, ...], replacement: object):
        changed = deepcopy(value)
        parent = at(changed, path[:-1]) if path[:-1] else changed
        parent[path[-1]] = replacement
        return changed

    for _, stdout_policy, _, expected in apg_test.NODE_PROFILE_OUTPUT_CONTRACTS.values():
        if stdout_policy != "json-exact":
            continue
        for path in paths(expected):
            original = at(expected, path)
            wrong_type = [] if not isinstance(original, list) else {}
            assert not apg_test._exact_json_matches(
                replace(expected, path, wrong_type), expected
            )
            if isinstance(original, bool):
                wrong_value = not original
            elif isinstance(original, int):
                wrong_value = original + 1
            elif isinstance(original, str):
                wrong_value = original + "-wrong"
            elif isinstance(original, list):
                wrong_value = [*original, "unexpected"]
            elif isinstance(original, dict):
                wrong_value = {**original, "unexpected": True}
            else:
                wrong_value = "not-null"
            assert not apg_test._exact_json_matches(
                replace(expected, path, wrong_value), expected
            )
            parent = at(deepcopy(expected), path[:-1]) if path[:-1] else None
            if isinstance(parent, (dict, list)):
                missing = deepcopy(expected)
                del at(missing, path[:-1])[path[-1]]
                assert not apg_test._exact_json_matches(missing, expected)
        if isinstance(expected, dict):
            extra = {**expected, "unexpected": True}
            assert not apg_test._exact_json_matches(extra, expected)


def test_javascript_semantic_invocation_returns_one_exact_pre_post_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    engine = tmp_path / "node"
    engine.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = -p ]; then printf 'v22.22.2|darwin/arm64|12.4.254.21-node.39\\n'; "
        "else printf '1\\n'; fi\n",
        encoding="utf-8",
    )
    engine.chmod(0o755)
    monkeypatch.setattr(apg_test, "EXPECTED_JAVASCRIPT_ENGINE_ROOT", tmp_path)
    monkeypatch.setattr(apg_test, "EXPECTED_JAVASCRIPT_ENGINE_UID", os.getuid())
    monkeypatch.setattr(
        apg_test,
        "EXPECTED_JAVASCRIPT_ENGINE_SHA256",
        hashlib.sha256(engine.read_bytes()).hexdigest(),
    )
    monkeypatch.setenv("APG_JAVASCRIPT_NODE", str(engine))
    observation = apg_test.invoke_javascript_engine(
        root,
        ["--input-type=module", "--eval", "ignored"],
        cwd=root,
        output_contract_id="top-level-await",
    )
    assert observation.engine_public_identity == apg_test.EXPECTED_JAVASCRIPT_ENGINE
    assert observation.result == 1
    assert not hasattr(observation, "stdout")
    assert not hasattr(observation, "stderr")
    assert not hasattr(observation, "completed")


def test_javascript_invocation_rejects_path_change_before_or_after(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    engine = tmp_path / "node"
    engine.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    engine.chmod(0o755)
    identity = (1, 2, 0o100755, os.getuid(), os.getgid(), len(engine.read_bytes()), 1)
    binding = apg_test.JavascriptEngineBinding(
        engine, identity, hashlib.sha256(engine.read_bytes()).hexdigest(),
        apg_test.EXPECTED_JAVASCRIPT_ENGINE,
    )
    monkeypatch.setenv("APG_JAVASCRIPT_NODE", str(tmp_path / "different"))
    monkeypatch.setattr(apg_test, "_javascript_engine_binding", lambda _root: binding)
    with pytest.raises(apg_test.ToolError, match="changed before invocation"):
        apg_test.invoke_javascript_engine(
            root,
            ["--eval", "ignored"],
            cwd=root,
            output_contract_id="top-level-await",
        )


def test_javascript_invocation_rejects_environment_content_or_metadata_change_after_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    engine = tmp_path / "node"
    original = b"#!/bin/sh\nexit 0\n"
    engine.write_bytes(original)
    engine.chmod(0o755)
    monkeypatch.setattr(apg_test, "EXPECTED_JAVASCRIPT_ENGINE_ROOT", tmp_path)
    monkeypatch.setattr(apg_test, "EXPECTED_JAVASCRIPT_ENGINE_UID", os.getuid())
    monkeypatch.setattr(
        apg_test, "EXPECTED_JAVASCRIPT_ENGINE_SHA256", hashlib.sha256(original).hexdigest()
    )
    monkeypatch.setenv("APG_JAVASCRIPT_NODE", str(engine))
    calls = 0
    def path_changing_run(args: list[str], **_kwargs: object) -> apg_test.subprocess.CompletedProcess[str]:
        nonlocal calls
        calls += 1
        if calls == 1:
            return apg_test.subprocess.CompletedProcess(args, 0, apg_test.EXPECTED_JAVASCRIPT_ENGINE + "\n", "")
        monkeypatch.setenv("APG_JAVASCRIPT_NODE", str(tmp_path / "reopened"))
        return apg_test.subprocess.CompletedProcess(args, 0, "1\n", "")
    monkeypatch.setattr(apg_test, "_run_javascript_process", path_changing_run)
    with pytest.raises(apg_test.ToolError, match="path changed after invocation"):
        apg_test.invoke_javascript_engine(
            root, ["--eval", "ignored"], cwd=root, output_contract_id="top-level-await"
        )

    monkeypatch.setenv("APG_JAVASCRIPT_NODE", str(engine))
    calls = 0
    def content_changing_run(args: list[str], **_kwargs: object) -> apg_test.subprocess.CompletedProcess[str]:
        nonlocal calls
        calls += 1
        if calls == 1:
            return apg_test.subprocess.CompletedProcess(args, 0, apg_test.EXPECTED_JAVASCRIPT_ENGINE + "\n", "")
        engine.write_text("#!/bin/sh\nprintf changed\n", encoding="utf-8")
        engine.chmod(0o755)
        return apg_test.subprocess.CompletedProcess(args, 0, "1\n", "")
    monkeypatch.setattr(apg_test, "_run_javascript_process", content_changing_run)
    with pytest.raises(apg_test.ToolError, match="digest mismatch|changed across invocation"):
        apg_test.invoke_javascript_engine(
            root, ["--eval", "ignored"], cwd=root, output_contract_id="top-level-await"
        )

    engine.write_bytes(original)
    engine.chmod(0o755)
    monkeypatch.setenv("APG_JAVASCRIPT_NODE", str(engine))
    calls = 0
    def metadata_changing_run(args: list[str], **_kwargs: object) -> apg_test.subprocess.CompletedProcess[str]:
        nonlocal calls
        calls += 1
        if calls in (1, 3):
            return apg_test.subprocess.CompletedProcess(args, 0, apg_test.EXPECTED_JAVASCRIPT_ENGINE + "\n", "")
        engine.chmod(0o700)
        return apg_test.subprocess.CompletedProcess(args, 0, "1\n", "")
    monkeypatch.setattr(apg_test, "_run_javascript_process", metadata_changing_run)
    with pytest.raises(apg_test.ToolError, match="changed across invocation"):
        apg_test.invoke_javascript_engine(
            root, ["--eval", "ignored"], cwd=root, output_contract_id="top-level-await"
        )


def test_javascript_invocation_rejects_actual_resolved_path_replacement_after_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    selected = tmp_path / "selected"
    selected.mkdir()
    engine = selected / "node"
    engine.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    engine.chmod(0o755)
    replacement = tmp_path / "replacement"
    replacement.mkdir()
    replacement_engine = replacement / "node"
    replacement_engine.write_bytes(engine.read_bytes())
    replacement_engine.chmod(0o755)
    monkeypatch.setattr(apg_test, "EXPECTED_JAVASCRIPT_ENGINE_ROOT", tmp_path)
    monkeypatch.setattr(apg_test, "EXPECTED_JAVASCRIPT_ENGINE_UID", os.getuid())
    monkeypatch.setattr(
        apg_test,
        "EXPECTED_JAVASCRIPT_ENGINE_SHA256",
        hashlib.sha256(engine.read_bytes()).hexdigest(),
    )
    monkeypatch.setenv("APG_JAVASCRIPT_NODE", str(engine))
    calls = 0

    def replacing_run(
        args: list[str], **_kwargs: object
    ) -> apg_test.subprocess.CompletedProcess[str]:
        nonlocal calls
        calls += 1
        if calls == 1:
            return apg_test.subprocess.CompletedProcess(
                args, 0, apg_test.EXPECTED_JAVASCRIPT_ENGINE + "\n", ""
            )
        moved = tmp_path / "selected-before-replacement"
        selected.rename(moved)
        selected.symlink_to(replacement, target_is_directory=True)
        return apg_test.subprocess.CompletedProcess(args, 0, "1\n", "")

    monkeypatch.setattr(apg_test, "_run_javascript_process", replacing_run)
    with pytest.raises(apg_test.ToolError, match="direct resolved executable path"):
        apg_test.invoke_javascript_engine(
            root, ["--eval", "ignored"], cwd=root, output_contract_id="top-level-await"
        )


def test_javascript_failures_do_not_reflect_external_output() -> None:
    sentinel = "APG79B-NONSECRET-STREAM-SENTINEL"
    for return_code, stdout, stderr, message in (
        (7, sentinel, sentinel, "unexpected status"),
        (0, "not-json-" + sentinel, "", "invalid structured output"),
        (0, "1\n", sentinel, "unexpected stderr"),
        (0, sentinel, "", "unexpected stdout"),
    ):
        contract = "top-level-await" if message != "unexpected stdout" else "commonjs-boundary-syntax"
        with pytest.raises(apg_test.JavascriptQualificationError, match=message) as captured:
            apg_test._validate_javascript_output(contract, return_code, stdout, stderr)
        assert sentinel not in str(captured.value)


def test_javascript_timeout_and_oserror_are_bounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    binding = apg_test.JavascriptEngineBinding(
        tmp_path / "node",
        (1, 2, 3, os.getuid(), os.getgid(), 4, 5),
        "0" * 64,
        apg_test.EXPECTED_JAVASCRIPT_ENGINE,
    )
    monkeypatch.setenv("APG_JAVASCRIPT_NODE", str(binding.path))
    monkeypatch.setattr(apg_test, "_javascript_engine_binding", lambda _root: binding)
    for error in (
        apg_test.subprocess.TimeoutExpired(["node"], 1, output="private", stderr="private"),
        OSError("private path and output"),
    ):
        def raising(*_args: object, selected: BaseException = error, **_kwargs: object) -> object:
            raise selected

        monkeypatch.setattr(apg_test, "_run_javascript_process", raising)
        with pytest.raises(apg_test.JavascriptQualificationError) as captured:
            apg_test.invoke_javascript_engine(
                tmp_path,
                ["--eval", "ignored"],
                cwd=tmp_path,
                output_contract_id="top-level-await",
            )
        assert "private" not in str(captured.value)


def test_every_javascript_output_contract_field_has_rejecting_mutations() -> None:
    def encoded(value: object) -> str:
        return json.dumps(value, separators=(",", ":")) + "\n"

    def at(value: object, path: tuple[object, ...]) -> object:
        current = value
        for part in path:
            current = current[part]
        return current

    def replace(value: object, path: tuple[object, ...], replacement: object) -> object:
        changed = deepcopy(value)
        parent = at(changed, path[:-1])
        parent[path[-1]] = replacement
        return changed

    def paths(value: object, prefix: tuple[object, ...] = ()):
        if isinstance(value, dict):
            for key, child in value.items():
                path = (*prefix, key)
                yield path
                yield from paths(child, path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                path = (*prefix, index)
                yield path
                yield from paths(child, path)

    for contract_id, contract in apg_test.JAVASCRIPT_OUTPUT_CONTRACTS.items():
        if contract.stdout_policy == "empty":
            assert apg_test._validate_javascript_output(contract_id, 0, "", "") is None
            for return_code, stdout, stderr in ((1, "", ""), (0, "x", ""), (0, "", "x")):
                with pytest.raises(apg_test.JavascriptQualificationError):
                    apg_test._validate_javascript_output(contract_id, return_code, stdout, stderr)
            continue
        expected = contract.expected_result
        assert apg_test._validate_javascript_output(contract_id, 0, encoded(expected), "") == expected
        with pytest.raises(apg_test.JavascriptQualificationError):
            apg_test._validate_javascript_output(contract_id, 0, "not-json", "")
        with pytest.raises(apg_test.JavascriptQualificationError):
            apg_test._validate_javascript_output(contract_id, 0, encoded([expected]), "")
        for path in paths(expected):
            original = at(expected, path)
            wrong_type = 0 if isinstance(original, str) else "wrong-type"
            with pytest.raises(apg_test.JavascriptQualificationError):
                apg_test._validate_javascript_output(
                    contract_id, 0, encoded(replace(expected, path, wrong_type)), ""
                )
            if isinstance(original, bool):
                wrong_value = not original
            elif isinstance(original, int):
                wrong_value = original + 1
            elif isinstance(original, str):
                wrong_value = original + "-wrong"
            elif isinstance(original, list):
                wrong_value = [*original, "unexpected"]
            elif isinstance(original, dict):
                wrong_value = {**original, "unexpected": True}
            else:
                wrong_value = "not-null"
            with pytest.raises(apg_test.JavascriptQualificationError):
                apg_test._validate_javascript_output(
                    contract_id, 0, encoded(replace(expected, path, wrong_value)), ""
                )
            parent = at(deepcopy(expected), path[:-1])
            if isinstance(parent, (dict, list)):
                missing = deepcopy(expected)
                del at(missing, path[:-1])[path[-1]]
                with pytest.raises(apg_test.JavascriptQualificationError):
                    apg_test._validate_javascript_output(contract_id, 0, encoded(missing), "")
        for path in ((), *tuple(path for path in paths(expected) if isinstance(at(expected, path), dict))):
            target = expected if not path else at(expected, path)
            if isinstance(target, dict):
                changed = deepcopy(expected)
                at(changed, path)["unexpected"] = True
                with pytest.raises(apg_test.JavascriptQualificationError):
                    apg_test._validate_javascript_output(contract_id, 0, encoded(changed), "")


def test_actual_pytest_rendering_cannot_disclose_raw_engine_streams(tmp_path: Path) -> None:
    sentinel = "APG79B-NONSECRET-STREAM-SENTINEL"
    test_path = tmp_path / "test_rendered_failure.py"
    test_path.write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(REPOSITORY_ROOT / 'libexec')!r})\n"
        "import apg_test\n"
        f"SENTINEL = {sentinel!r}\n"
        "def test_rendered_failure():\n"
        "    try:\n"
        "        apg_test._validate_javascript_output('top-level-await', 0, SENTINEL, '')\n"
        "    except apg_test.JavascriptQualificationError as error:\n"
        "        observed = error\n"
        "    assert observed is None\n",
        encoding="utf-8",
    )

    class Capture:
        rendered = ""

        def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
            if report.failed:
                self.rendered += report.longreprtext

    capture = Capture()
    result = pytest.main(["-p", "no:terminal", str(test_path)], plugins=[capture])
    assert result == pytest.ExitCode.TESTS_FAILED
    assert sentinel not in capture.rendered
    assert "JavascriptQualificationError" in capture.rendered


def test_node_profile_pytest_showlocals_cannot_disclose_raw_streams(tmp_path: Path) -> None:
    sentinel = "APG81-NONSECRET-STREAM-SENTINEL"
    encoded = sentinel.encode("utf-8").hex()
    test_path = tmp_path / "test_node_rendered_failure.py"
    test_path.write_text(
        "import json, pathlib, subprocess, sys\n"
        f"sys.path.insert(0, {str(REPOSITORY_ROOT / 'libexec')!r})\n"
        "import apg_test\n"
        "binding=apg_test.NodeProfileRuntimeBinding('primary',pathlib.Path('/external/node'),(1,2,3,4,5,6,7),'a'*64,'synthetic')\n"
        "invocation=apg_test.NodeProfileInvocation('redaction-negative',pathlib.Path('/scratch/i'),pathlib.Path('/scratch/i/tmp'),pathlib.Path('/scratch/i/npm-cache'),pathlib.Path('/scratch/i/pnpm-home'),pathlib.Path('/scratch/i/work'),pathlib.Path('/scratch/i/fs-case'))\n"
        "def test_rendered_failure(monkeypatch):\n"
        "    monkeypatch.setattr(apg_test,'_node_profile_runtime_binding',lambda root,role: binding)\n"
        "    monkeypatch.setattr(apg_test,'_validate_node_profile_invocation',lambda root,invocation: None)\n"
        f"    monkeypatch.setattr(apg_test,'_run_javascript_process',lambda args,**kwargs: subprocess.CompletedProcess(args,0,json.dumps({{'secret':bytes.fromhex('{encoded}').decode()}})+'\\n',''))\n"
        "    apg_test.invoke_node_profile_runtime(pathlib.Path('/repo'),'primary',['--eval','safe'],invocation=invocation,output_contract_id='redaction-negative',expected_result={'secret':'expected-safe-value'})\n",
        encoding="utf-8",
    )

    class Capture:
        rendered = ""

        def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
            if report.failed:
                self.rendered += report.longreprtext

    capture = Capture()
    result = pytest.main(
        ["-q", "-l", str(test_path)], plugins=[capture]
    )
    assert result == pytest.ExitCode.TESTS_FAILED
    assert sentinel not in capture.rendered
    assert "/scratch/i" not in capture.rendered
    assert "NodeProfileQualificationError" in capture.rendered


def test_node_profile_cleanup_pytest_showlocals_cannot_disclose_raw_paths(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "APG81-private-repository-sentinel"
    owned = tmp_path / "APG81-private-scratch-sentinel"
    repository.mkdir()
    owned.mkdir()
    test_path = tmp_path / "test_node_cleanup_rendered_failure.py"
    test_path.write_text(
        "import os, pathlib, sys\n"
        f"sys.path.insert(0, {str(REPOSITORY_ROOT / 'libexec')!r})\n"
        "import apg_test\n"
        f"REPOSITORY=pathlib.Path({os.fspath(repository)!r})\n"
        f"OWNED=pathlib.Path({os.fspath(owned)!r})\n"
        "os.environ['APG_NODEJS_OWNED_SCRATCH_ROOT']=str(OWNED)\n"
        "def test_rendered_cleanup_failure(monkeypatch):\n"
        "    def partial(path):\n"
        "        (pathlib.Path(path)/'tmp').rmdir()\n"
        "        raise OSError('synthetic')\n"
        "    monkeypatch.setattr(apg_test.shutil,'rmtree',partial)\n"
        "    with apg_test.node_profile_invocation(REPOSITORY,'primary-owned-scratch'):\n"
        "        pass\n",
        encoding="utf-8",
    )

    class Capture:
        rendered = ""

        def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
            if report.failed:
                self.rendered += report.longreprtext

    capture = Capture()
    result = pytest.main(["-q", "-l", str(test_path)], plugins=[capture])
    assert result == pytest.ExitCode.TESTS_FAILED
    assert os.fspath(repository) not in capture.rendered
    assert os.fspath(owned) not in capture.rendered
    assert "NodeProfileCleanupError" in capture.rendered


def test_node_profile_early_pytest_showlocals_failures_cannot_disclose_raw_paths(
    tmp_path: Path,
) -> None:
    scratch_sentinel = tmp_path / "APG81-private-invalid-scratch-sentinel"
    runtime_sentinel = tmp_path / "APG81-private-runtime-sentinel"
    argument_sentinel = "APG81-private-argument-sentinel"
    argument_hex = argument_sentinel.encode("utf-8").hex()
    test_path = tmp_path / "test_node_early_rendered_failures.py"
    test_path.write_text(
        "import os, pathlib, sys\n"
        f"sys.path.insert(0, {str(REPOSITORY_ROOT / 'libexec')!r})\n"
        "import apg_test\n"
        f"SCRATCH=pathlib.Path({os.fspath(scratch_sentinel)!r})\n"
        f"RUNTIME=pathlib.Path({os.fspath(runtime_sentinel)!r})\n"
        "REPOSITORY=SCRATCH.parent/'repository'\n"
        "INVOCATION=apg_test.NodeProfileInvocation('redaction-negative',SCRATCH,SCRATCH/'tmp',SCRATCH/'npm-cache',SCRATCH/'pnpm-home',SCRATCH/'work',SCRATCH/'fs-case')\n"
        "BINDING=apg_test.NodeProfileRuntimeBinding('primary',RUNTIME,(1,2,3,4,5,6,7),'a'*64,'identity')\n"
        "def test_invalid_scratch_owner(monkeypatch):\n"
        "    monkeypatch.setenv('APG_NODEJS_OWNED_SCRATCH_ROOT',str(SCRATCH))\n"
        "    with apg_test.node_profile_invocation(REPOSITORY,'primary-owned-scratch'):\n"
        "        pass\n"
        "def test_duplicate_runtime_paths(monkeypatch):\n"
        "    monkeypatch.setattr(apg_test,'_node_profile_runtime_binding',lambda *args:BINDING)\n"
        "    apg_test.validate_node_profile_runtimes(REPOSITORY)\n"
        "def test_invoke_runtime_preflight_failure(monkeypatch):\n"
        "    monkeypatch.setattr(apg_test,'_validate_node_profile_invocation',lambda *args:None)\n"
        "    monkeypatch.setattr(apg_test,'_node_profile_runtime_binding',lambda *args:(_ for _ in ()).throw(apg_test.ToolError('synthetic runtime failure')))\n"
        f"    apg_test.invoke_node_profile_runtime(REPOSITORY,'primary',[bytes.fromhex('{argument_hex}').decode()],invocation=INVOCATION,output_contract_id='redaction-negative',expected_result={{'secret':'expected-safe-value'}})\n",
        encoding="utf-8",
    )

    class Capture:
        rendered = ""

        def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
            if report.failed:
                self.rendered += report.longreprtext

    capture = Capture()
    result = pytest.main(["-q", "-l", str(test_path)], plugins=[capture])
    assert result == pytest.ExitCode.TESTS_FAILED
    assert os.fspath(scratch_sentinel) not in capture.rendered
    assert os.fspath(runtime_sentinel) not in capture.rendered
    assert argument_sentinel not in capture.rendered
    assert "NodeProfileQualificationError" in capture.rendered


@pytest.mark.parametrize("value", ["", "/absolute", "../escape", "a/../b", "a//b"])
def test_inventory_paths_must_be_normalized_relative(value: str) -> None:
    with pytest.raises(apg_test.ToolError, match="normalized relative path|nonempty"):
        apg_test._relative_path(value, "test")


def test_artifact_directory_is_fresh_and_rejects_unsafe_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APG_TEST_ARTIFACT_ROOT", os.fspath(tmp_path))
    first = apg_test._artifact_directory(REPOSITORY_ROOT)
    second = apg_test._artifact_directory(REPOSITORY_ROOT)
    assert first.path != second.path
    apg_test._cleanup_artifacts(first)
    apg_test._cleanup_artifacts(second)
    monkeypatch.setenv("APG_TEST_ARTIFACT_ROOT", "relative")
    with pytest.raises(apg_test.InvocationError, match="absolute real directory"):
        apg_test._artifact_directory(REPOSITORY_ROOT)


def test_pytest_execution_rejects_failure_missing_and_parallel_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(apg_test, "validate_worker_manifest", lambda *_args: None)
    monkeypatch.setattr(apg_test, "validate_child_manifest", lambda *_args: None)
    monkeypatch.setattr(apg_test, "_coverage_contexts", lambda _path: set())
    class Result:
        returncode = 0

    def successful(*_args: object, **kwargs: object) -> Result:
        environment = kwargs["env"]
        data = Path(environment["COVERAGE_FILE"])
        data.write_bytes(b"coverage")
        data.with_suffix(".json").write_text('{"files": {}}', encoding="utf-8")
        assert environment["PATH"].split(os.pathsep)[0] == os.fspath(Path(sys.executable).parent)
        assert environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"
        return Result()
    monkeypatch.setattr(apg_test.subprocess, "run", successful)
    data, report = apg_test._run_pytest(REPOSITORY_ROOT, "unit", 2, tmp_path)
    assert data.is_file() and report == {"files": {}}

    class Failed:
        returncode = 5

    monkeypatch.setattr(apg_test.subprocess, "run", lambda *_args, **_kwargs: Failed())
    failure = tmp_path / "failure"
    failure.mkdir()
    with pytest.raises(apg_test.ToolError, match="status 5"):
        apg_test._run_pytest(REPOSITORY_ROOT, "unit", 2, failure)

    incomplete = tmp_path / "incomplete"
    incomplete.mkdir()
    monkeypatch.setattr(apg_test.subprocess, "run", lambda *_args, **_kwargs: Result())
    with pytest.raises(apg_test.ToolError, match="output is incomplete"):
        apg_test._run_pytest(REPOSITORY_ROOT, "unit", 2, incomplete)
    parallel = tmp_path / "parallel"
    parallel.mkdir()

    def leaves_parallel(*_args: object, **kwargs: object) -> Result:
        data = Path(kwargs["env"]["COVERAGE_FILE"])
        data.write_bytes(b"coverage")
        data.with_suffix(".json").write_text('{"files": {}}', encoding="utf-8")
        data.with_name(data.name + ".worker").write_bytes(b"stale")
        return Result()

    monkeypatch.setattr(apg_test.subprocess, "run", leaves_parallel)
    with pytest.raises(apg_test.ToolError, match="unexpected data"):
        apg_test._run_pytest(REPOSITORY_ROOT, "unit", 2, parallel)

    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (foreign / "foreign.coverage").write_bytes(b"foreign")
    with pytest.raises(apg_test.ToolError, match="contains unexpected data"):
        apg_test._run_pytest(REPOSITORY_ROOT, "unit", 2, foreign)


def test_pytest_execution_rejects_malformed_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(apg_test, "validate_worker_manifest", lambda *_args: None)
    monkeypatch.setattr(apg_test, "validate_child_manifest", lambda *_args: None)
    monkeypatch.setattr(apg_test, "_coverage_contexts", lambda _path: set())
    class Result:
        returncode = 0

    def malformed(*_args: object, **kwargs: object) -> Result:
        data = Path(kwargs["env"]["COVERAGE_FILE"])
        data.write_bytes(b"coverage")
        data.with_suffix(".json").write_text("{", encoding="utf-8")
        return Result()

    monkeypatch.setattr(apg_test.subprocess, "run", malformed)
    with pytest.raises(apg_test.ToolError, match="JSON is unreadable"):
        apg_test._run_pytest(REPOSITORY_ROOT, "unit", 2, tmp_path)


def test_pytest_command_disables_worker_restart_and_uses_selected_root(tmp_path: Path) -> None:
    command = apg_test._pytest_command(
        tmp_path,
        "integration",
        8,
        tmp_path / "data",
        tmp_path / "report.json",
        "run-id",
    )
    assert command[command.index("-n") + 1] == "8"
    assert "--max-worker-restart=0" in command
    assert "xdist.plugin" in command
    assert "pytest_cov.plugin" in command
    assert command[-1].endswith("src/test/int/python/agentic-praxis-grimoire")


def test_mirror_path_mapping_handles_markdown_and_extensionless_owners() -> None:
    assert apg_test._expected_test_path("skills/example/SKILL.md", "unit").endswith(
        "skills/example/SKILL.unit.test.py"
    )
    assert apg_test._expected_test_path("bin/example", "integration").endswith(
        "bin/example.int.test.py"
    )


def test_run_enforces_each_suite_then_combined_union(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inventory = apg_test.Inventory(
        {"libexec/tool.py": ("unit", "integration", "combined")}, {}, {}
    )
    monkeypatch.setattr(apg_test, "load_inventory", lambda _root: inventory)
    monkeypatch.setattr(apg_test, "validate_inventory", lambda _root, _inventory: None)
    monkeypatch.setattr(apg_test, "dependency_versions", lambda: {})
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir()
    metadata = artifact_root.stat()
    ownership = apg_test.ArtifactDirectory(
        artifact_root, metadata.st_dev, metadata.st_ino
    )
    monkeypatch.setattr(apg_test, "_artifact_directory", lambda _root: ownership)
    report = {"files": {"libexec/tool.py": {"summary": {
        "covered_lines": 9, "num_statements": 10,
        "covered_branches": 9, "num_branches": 10,
    }}}}
    calls: list[str] = []

    def run_suite(
        _root: Path, suite: str, workers: int, _artifacts: Path, **_kwargs: object
    ):
        calls.append(f"{suite}:{workers}")
        return artifact_root / suite / f"{suite}.coverage", report

    monkeypatch.setattr(apg_test, "_run_pytest", run_suite)
    monkeypatch.setattr(apg_test, "_combine_coverage", lambda *_args: report)
    apg_test.run("combined", 8, tmp_path)
    assert calls == ["unit:8", "integration:8"]
    with pytest.raises(apg_test.ToolError, match="workers"):
        apg_test.run("unit", 0, tmp_path)


def test_combined_reports_both_components_and_union_after_a_component_gate_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inventory = apg_test.Inventory(
        {"libexec/tool.py": ("unit", "integration", "combined")}, {}, {}
    )
    monkeypatch.setattr(apg_test, "load_inventory", lambda _root: inventory)
    monkeypatch.setattr(apg_test, "validate_inventory", lambda _root, _inventory: None)
    monkeypatch.setattr(apg_test, "dependency_versions", lambda: {})
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir()
    metadata = artifact_root.stat()
    ownership = apg_test.ArtifactDirectory(
        artifact_root, metadata.st_dev, metadata.st_ino
    )
    monkeypatch.setattr(apg_test, "_artifact_directory", lambda _root: ownership)
    calls: list[str] = []

    def report(covered: int) -> dict[str, object]:
        return {"files": {"libexec/tool.py": {"summary": {
            "covered_lines": covered, "num_statements": 10,
            "covered_branches": covered, "num_branches": 10,
        }}}}

    def run_suite(
        _root: Path, suite: str, _workers: int, _artifacts: Path, **_kwargs: object
    ):
        calls.append(suite)
        return artifact_root / suite / f"{suite}.coverage", report(
            5 if suite == "unit" else 9
        )

    monkeypatch.setattr(apg_test, "_run_pytest", run_suite)
    def malformed_union(*_args: object) -> dict[str, object]:
        calls.append("combined")
        raise apg_test.ToolError("union malformed")

    monkeypatch.setattr(apg_test, "_combine_coverage", malformed_union)

    with pytest.raises(
        apg_test.ToolError,
        match="unit.*statement coverage.*combined.*union malformed",
    ):
        apg_test.run("combined", 8, tmp_path)
    assert calls == ["unit", "integration", "combined"]


def test_combined_component_failure_artifacts_are_isolated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inventory = apg_test.Inventory(
        {"libexec/tool.py": ("unit", "integration", "combined")}, {}, {}
    )
    monkeypatch.setattr(apg_test, "load_inventory", lambda _root: inventory)
    monkeypatch.setattr(apg_test, "validate_inventory", lambda _root, _inventory: None)
    monkeypatch.setattr(apg_test, "dependency_versions", lambda: {})
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir()
    metadata = artifact_root.stat()
    ownership = apg_test.ArtifactDirectory(
        artifact_root, metadata.st_dev, metadata.st_ino
    )
    monkeypatch.setattr(apg_test, "_artifact_directory", lambda _root: ownership)
    calls: list[str] = []

    def fail_component(
        _root: Path,
        suite: str,
        _workers: int,
        component_artifacts: Path,
        **_kwargs: object,
    ) -> tuple[Path, dict[str, object]]:
        calls.append(suite)
        assert component_artifacts == artifact_root / suite
        assert not any(component_artifacts.iterdir())
        (component_artifacts / f"{suite}-failure-evidence").write_text(
            "retained\n", encoding="utf-8"
        )
        raise apg_test.ToolError(f"{suite} failed")

    monkeypatch.setattr(apg_test, "_run_pytest", fail_component)
    with pytest.raises(
        apg_test.ToolError,
        match="unit: unit failed; integration: integration failed",
    ):
        apg_test.run("combined", 2, tmp_path, keep_artifacts_on_failure=True)
    assert calls == ["unit", "integration"]
    assert (artifact_root / "unit/unit-failure-evidence").is_file()
    assert (artifact_root / "integration/integration-failure-evidence").is_file()


def test_worker_manifest_requires_exact_workers_collections_results_and_clean_down(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "workers.jsonl"
    node_ids = ["root/test_example.py::test_one"]
    events = []
    for worker in ("gw0", "gw1"):
        events.extend(
            [
                {"event": "worker-start", "run_id": "run", "suite": "unit", "worker": worker},
                {"event": "collection", "run_id": "run", "suite": "unit", "worker": worker, "node_ids": node_ids},
                {"event": "worker-complete", "run_id": "run", "suite": "unit", "worker": worker, "exitstatus": 0},
                {"event": "node-down", "run_id": "run", "suite": "unit", "worker": worker, "error": False, "exitstatus": 0},
            ]
        )
    events.append(
        {"event": "test-result", "run_id": "run", "suite": "unit", "nodeid": node_ids[0], "outcome": "passed"}
    )
    events.append(
        {"event": "controller-complete", "run_id": "run", "suite": "unit", "exitstatus": 0}
    )
    manifest.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")
    apg_test.validate_worker_manifest(manifest, "run", "unit", 2, "root")

    events.pop(-2)
    manifest.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")
    with pytest.raises(apg_test.ToolError, match="terminal result"):
        apg_test.validate_worker_manifest(manifest, "run", "unit", 2, "root")


def test_required_child_manifest_needs_completion_and_coverage_context(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "children.jsonl"
    context = "apg-child:run:child"
    events = [
        {"event": "child-start", "run_id": "run", "suite": "unit", "process_id": "child", "context": context},
        {"event": "child-complete", "run_id": "run", "suite": "unit", "process_id": "child", "context": context},
    ]
    manifest.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")
    apg_test.validate_child_manifest(manifest, "run", "unit", {context})
    with pytest.raises(apg_test.ToolError, match="coverage contribution"):
        apg_test.validate_child_manifest(manifest, "run", "unit", set())
    with pytest.raises(apg_test.ToolError, match="child coverage contribution differs"):
        apg_test.validate_child_manifest(
            manifest,
            "run",
            "unit",
            {context, "apg-child:foreign:stale"},
        )

    manifest.write_text("", encoding="utf-8")
    with pytest.raises(apg_test.ToolError, match="child coverage contribution differs"):
        apg_test.validate_child_manifest(
            manifest,
            "run",
            "unit",
            {"apg-child:foreign:stale"},
        )


def test_main_maps_combined_name_and_returns_bounded_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[tuple[str, int]] = []

    def successful(
        suite: str, workers: int, _root: Path, **_kwargs: object
    ) -> None:
        observed.append((suite, workers))

    monkeypatch.setattr(apg_test, "run", successful)
    assert apg_test.main(["unit-integration"]) == 0
    assert observed == [("combined", 8)]

    def failing(*_args: object, **_kwargs: object) -> None:
        raise apg_test.ToolError("bounded")

    monkeypatch.setattr(apg_test, "run", failing)
    assert apg_test.main(["unit"]) == 1


def test_resolve_source_commit_returns_head_commit_hash_or_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    commit = apg_test.resolve_source_commit(REPOSITORY_ROOT)
    assert len(commit) == 40
    assert all(c in "0123456789abcdef" for c in commit.lower())

    class DummyProcess:
        returncode = 1
        stdout = ""
        stderr = "fatal: not a git repository"

    monkeypatch.setattr(apg_test.subprocess, "run", lambda *args, **kwargs: DummyProcess())
    with pytest.raises(apg_test.ToolError, match="resolve source commit"):
        apg_test.resolve_source_commit(tmp_path)

    class MalformedProcess:
        returncode = 0
        stdout = "short\n"
        stderr = ""

    monkeypatch.setattr(apg_test.subprocess, "run", lambda *args, **kwargs: MalformedProcess())
    with pytest.raises(apg_test.ToolError, match="invalid commit hash"):
        apg_test.resolve_source_commit(tmp_path)


def test_write_summary_creates_mode_private_payload(tmp_path: Path) -> None:
    summary_file = tmp_path / "subdir" / "summary.json"
    apg_test.write_summary(
        summary_file,
        suite="policy",
        test_status="pass",
        gate_status="pass",
        source_commit="a" * 40,
    )
    assert summary_file.is_file()
    assert oct(stat.S_IMODE(summary_file.stat().st_mode)) == "0o600"
    payload = json.loads(summary_file.read_text(encoding="utf-8"))
    assert payload == {
        "version": 1,
        "subproject": "apg",
        "suite": "policy",
        "test_status": "pass",
        "gate_status": "pass",
        "source_commit": "a" * 40,
    }


def test_run_policy_executes_validators_and_fails_on_defect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class GoodSkillResult:
        passed = True

    class GoodRecordResult:
        passed = True

    monkeypatch.setattr(apg_test, "load_inventory", lambda _root: None)
    monkeypatch.setattr(apg_test, "validate_inventory", lambda _root, _inv: None)
    monkeypatch.setattr(apg_test, "dependency_versions", lambda: None)
    monkeypatch.setattr("apg_skill_library_check.check_library", lambda _root: GoodSkillResult())
    monkeypatch.setattr("apg_skill_library_check._embedded_corpus_failure", lambda _root: None)
    monkeypatch.setattr("apg_record_identity.check_records", lambda _root: GoodRecordResult())

    apg_test.run_policy(REPOSITORY_ROOT)

    class BadSkillResult:
        passed = False

    monkeypatch.setattr("apg_skill_library_check.check_library", lambda _root: BadSkillResult())
    with pytest.raises(apg_test.ToolError, match="skill library policy check failed"):
        apg_test.run_policy(REPOSITORY_ROOT)

    monkeypatch.setattr("apg_skill_library_check.check_library", lambda _root: GoodSkillResult())
    monkeypatch.setattr("apg_skill_library_check._embedded_corpus_failure", lambda _root: "drift")
    with pytest.raises(apg_test.ToolError, match="corpus identity check failed"):
        apg_test.run_policy(REPOSITORY_ROOT)

    class BadRecordResult:
        passed = False

    monkeypatch.setattr("apg_skill_library_check._embedded_corpus_failure", lambda _root: None)
    monkeypatch.setattr("apg_record_identity.check_records", lambda _root: BadRecordResult())
    with pytest.raises(apg_test.ToolError, match="record identity policy check failed"):
        apg_test.run_policy(REPOSITORY_ROOT)


def test_main_policy_and_summary_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    summary_path = tmp_path / "ci" / "summary.json"
    called = []

    def mock_policy(_root: Path) -> None:
        called.append("policy")

    monkeypatch.setattr(apg_test, "run_policy", mock_policy)
    monkeypatch.setattr(apg_test, "resolve_source_commit", lambda _root: "c" * 40)

    exit_code = apg_test.main(["policy", "--summary-file", str(summary_path)])
    assert exit_code == 0
    assert called == ["policy"]
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["test_status"] == "pass"
    assert payload["suite"] == "policy"
    assert payload["source_commit"] == "c" * 40

    def failing_run(*args: object, **kwargs: object) -> None:
        raise apg_test.ToolError("failure injected")

    fail_summary = tmp_path / "ci" / "fail-summary.json"
    monkeypatch.setattr(apg_test, "run", failing_run)
    exit_code = apg_test.main(["unit", "--summary-file", str(fail_summary)])
    assert exit_code == 1
    fail_payload = json.loads(fail_summary.read_text(encoding="utf-8"))
    assert fail_payload["test_status"] == "fail"
    assert fail_payload["gate_status"] == "fail"
    assert fail_payload["suite"] == "unit"

    gate_summary = tmp_path / "ci" / "gate-summary.json"

    def gate_fail_run(*args: object, **kwargs: object) -> None:
        raise apg_test.GateShortfallError("coverage fell below gate")

    monkeypatch.setattr(apg_test, "run", gate_fail_run)
    exit_code = apg_test.main(["unit", "--summary-file", str(gate_summary)])
    assert exit_code == 1
    gate_payload = json.loads(gate_summary.read_text(encoding="utf-8"))
    assert gate_payload["test_status"] == "pass"
    assert gate_payload["gate_status"] == "fail"

    inv_summary = tmp_path / "ci" / "inv-summary.json"

    def inv_fail_run(*args: object, **kwargs: object) -> None:
        raise apg_test.InvocationError("bad workers")

    monkeypatch.setattr(apg_test, "run", inv_fail_run)
    exit_code = apg_test.main(["unit", "--summary-file", str(inv_summary)])
    assert exit_code == 1
    inv_payload = json.loads(inv_summary.read_text(encoding="utf-8"))
    assert inv_payload["test_status"] == "error"
    assert inv_payload["gate_status"] == "error"

    interrupt_summary = tmp_path / "ci" / "interrupt-summary.json"

    def interrupt_run(*args: object, **kwargs: object) -> None:
        raise KeyboardInterrupt()

    monkeypatch.setattr(apg_test, "run", interrupt_run)
    exit_code = apg_test.main(["unit", "--summary-file", str(interrupt_summary)])
    assert exit_code == 130
    int_payload = json.loads(interrupt_summary.read_text(encoding="utf-8"))
    assert int_payload["test_status"] == "error"
    assert int_payload["gate_status"] == "error"


def test_main_argparse_error_writes_summary_when_requested(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(apg_test, "resolve_source_commit", lambda _root: "d" * 40)
    summary_path = tmp_path / "ci" / "cli-error.json"
    with pytest.raises(SystemExit) as exc_info:
        apg_test.main(["invalid-role", "--summary-file", str(summary_path)])
    assert exc_info.value.code != 0
    assert summary_path.is_file()
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["suite"] == "unknown"
    assert payload["test_status"] == "error"
    assert payload["gate_status"] == "error"
    assert payload["source_commit"] == "d" * 40


def test_main_omits_summary_when_commit_cannot_be_resolved(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def broken_commit(_root: Path) -> str:
        raise apg_test.ToolError("git unavailable")

    monkeypatch.setattr(apg_test, "resolve_source_commit", broken_commit)
    monkeypatch.setattr(apg_test, "run", lambda *args, **kwargs: None)
    summary_path = tmp_path / "ci" / "no-commit.json"
    exit_code = apg_test.main(["unit", "--summary-file", str(summary_path)])
    assert exit_code == 1
    assert not summary_path.exists()


def test_parser_accepts_policy_and_summary_file() -> None:
    parser = apg_test.parser()
    args = parser.parse_args(["policy", "--summary-file", "reports/summary.json"])
    assert args.suite == "policy"
    assert args.summary_file == Path("reports/summary.json")


def test_main_harness_policy_and_assertion_error_summary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(apg_test, "resolve_source_commit", lambda _root: "e" * 40)

    # HarnessError -> test_status: "error", gate_status: "error"
    harness_summary = tmp_path / "ci" / "harness-summary.json"
    def harness_fail_run(*args: object, **kwargs: object) -> None:
        raise apg_test.HarnessError("worker crashed or manifest invalid")
    monkeypatch.setattr(apg_test, "run", harness_fail_run)
    exit_code = apg_test.main(["unit", "--summary-file", str(harness_summary)])
    assert exit_code == 1
    harness_payload = json.loads(harness_summary.read_text(encoding="utf-8"))
    assert harness_payload["test_status"] == "error"
    assert harness_payload["gate_status"] == "error"

    # PolicyCheckError -> test_status: "fail", gate_status: "fail"
    policy_summary = tmp_path / "ci" / "policy-fail-summary.json"
    def policy_fail_run(*args: object, **kwargs: object) -> None:
        raise apg_test.PolicyCheckError("corpus mismatch")
    monkeypatch.setattr(apg_test, "run_policy", policy_fail_run)
    exit_code = apg_test.main(["policy", "--summary-file", str(policy_summary)])
    assert exit_code == 1
    policy_payload = json.loads(policy_summary.read_text(encoding="utf-8"))
    assert policy_payload["test_status"] == "fail"
    assert policy_payload["gate_status"] == "fail"

    # TestAssertionError -> test_status: "fail", gate_status: "fail"
    assert_summary = tmp_path / "ci" / "assert-fail-summary.json"
    def assert_fail_run(*args: object, **kwargs: object) -> None:
        raise apg_test.TestAssertionError("test failed")
    monkeypatch.setattr(apg_test, "run", assert_fail_run)
    exit_code = apg_test.main(["unit", "--summary-file", str(assert_summary)])
    assert exit_code == 1
    assert_payload = json.loads(assert_summary.read_text(encoding="utf-8"))
    assert assert_payload["test_status"] == "fail"
    assert assert_payload["gate_status"] == "fail"


def test_main_summary_write_failure_preserves_exit_code_and_emits_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(apg_test, "resolve_source_commit", lambda _root: "f" * 40)
    summary_path = tmp_path / "ci" / "summary.json"

    def disk_full(*args: object, **kwargs: object) -> None:
        raise OSError("No space left on device")

    monkeypatch.setattr(apg_test, "write_summary", disk_full)

    # 1. Successful test run with failed summary write -> exits 1
    monkeypatch.setattr(apg_test, "run", lambda *args, **kwargs: None)
    exit_code = apg_test.main(["unit", "--summary-file", str(summary_path)])
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "failed to write summary file" in captured.err

    # 2. Failing test run (GateShortfallError) with failed summary write -> exits 1
    monkeypatch.setattr(
        apg_test, "run", lambda *args, **kwargs: (_ for _ in ()).throw(apg_test.GateShortfallError("coverage fail"))
    )
    exit_code = apg_test.main(["unit", "--summary-file", str(summary_path)])
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "failed to write summary file" in captured.err


def test_main_stale_summary_invalidation_and_safety(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    summary_path = tmp_path / "ci" / "stale-summary.json"

    # Pre-populate valid APGR v1 summary
    apg_test.write_summary(
        summary_path,
        suite="unit",
        test_status="pass",
        gate_status="pass",
        source_commit="1" * 40,
    )
    assert summary_path.is_file()

    # Commit cannot be resolved at runtime -> stale summary must be removed
    monkeypatch.setattr(
        apg_test,
        "resolve_source_commit",
        lambda _root: (_ for _ in ()).throw(apg_test.ToolError("no git")),
    )
    monkeypatch.setattr(apg_test, "run", lambda *args, **kwargs: None)
    exit_code = apg_test.main(["unit", "--summary-file", str(summary_path)])
    assert exit_code == 1
    assert not summary_path.exists()

    # Safety: Foreign file should NOT be unlinked by invalidate()
    foreign_path = tmp_path / "ci" / "foreign.json"
    foreign_path.write_text('{"subproject": "other", "version": 1}', encoding="utf-8")
    dest_foreign = apg_test.admit_summary_destination(REPOSITORY_ROOT, foreign_path)
    with pytest.raises(apg_test.InvocationError, match="not a recognized APGR receipt"):
        dest_foreign.invalidate()
    assert foreign_path.is_file()

    # Corrupt or non-json file should also NOT be unlinked
    corrupt_path = tmp_path / "ci" / "corrupt.txt"
    corrupt_path.write_text("not json", encoding="utf-8")
    dest_corrupt = apg_test.admit_summary_destination(REPOSITORY_ROOT, corrupt_path)
    with pytest.raises(apg_test.InvocationError, match="not a recognized APGR receipt"):
        dest_corrupt.invalidate()
    assert corrupt_path.is_file()


def test_summary_path_confinement(
    tmp_path: Path,
) -> None:
    fake_repo = tmp_path / "repo"
    fake_repo.mkdir()
    fake_git = fake_repo / ".git"
    fake_git.mkdir()
    fake_docs = fake_repo / "docs"
    fake_docs.mkdir()

    # Path inside .git/
    with pytest.raises(apg_test.InvocationError, match="summary file cannot target Git metadata"):
        apg_test.admit_summary_destination(fake_repo, fake_git / "summary.json")

    # Path inside repo that is not gitignored
    with pytest.raises(apg_test.InvocationError, match="summary file inside repository must be gitignored"):
        apg_test.admit_summary_destination(fake_repo, fake_docs / "forbidden-summary.json")

    # Path outside repo is allowed
    outside = tmp_path / "outside" / "summary.json"
    dest_outside = apg_test.admit_summary_destination(fake_repo, outside)
    assert dest_outside.resolved_target == outside.resolve()


def test_summary_git_head_drift_detection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # First call at entry returns c1, subsequent call at exit returns c2
    commits = iter(["a" * 40, "b" * 40])
    monkeypatch.setattr(apg_test, "resolve_source_commit", lambda _root: next(commits))
    monkeypatch.setattr(apg_test, "run", lambda *args, **kwargs: None)

    summary_path = tmp_path / "ci" / "drift-summary.json"
    # Pre-populate a summary to verify it gets invalidated
    apg_test.write_summary(
        summary_path,
        suite="unit",
        test_status="pass",
        gate_status="pass",
        source_commit="a" * 40,
    )
    assert summary_path.is_file()

    exit_code = apg_test.main(["unit", "--summary-file", str(summary_path)])
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "git HEAD drifted during execution" in captured.err
    assert not summary_path.exists()


def test_pytest_exit_code_mappings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StubProcess:
        def __init__(self, code: int):
            self.returncode = code

    # Code 1 -> TestAssertionError (requires worker manifest validation)
    art1 = tmp_path / "artifacts1"
    art1.mkdir()
    monkeypatch.setattr(apg_test, "validate_worker_manifest", lambda *_args: None)
    monkeypatch.setattr(apg_test.subprocess, "run", lambda *_args, **_kwargs: StubProcess(1))
    with pytest.raises(apg_test.TestAssertionError, match="status 1"):
        apg_test._run_pytest(REPOSITORY_ROOT, "unit", 2, art1)

    # For codes 2, 3, 4, 5, validate_worker_manifest must NOT be called
    def fail_if_manifest_called(*_args, **_kwargs):
        raise AssertionError("validate_worker_manifest was unexpectedly called")

    monkeypatch.setattr(apg_test, "validate_worker_manifest", fail_if_manifest_called)

    # Code 2 -> KeyboardInterrupt
    art2 = tmp_path / "artifacts2"
    art2.mkdir()
    monkeypatch.setattr(apg_test.subprocess, "run", lambda *_args, **_kwargs: StubProcess(2))
    with pytest.raises(KeyboardInterrupt):
        apg_test._run_pytest(REPOSITORY_ROOT, "unit", 2, art2)

    # Code 3 -> HarnessError
    art3 = tmp_path / "artifacts3"
    art3.mkdir()
    monkeypatch.setattr(apg_test.subprocess, "run", lambda *_args, **_kwargs: StubProcess(3))
    with pytest.raises(apg_test.HarnessError, match="status 3"):
        apg_test._run_pytest(REPOSITORY_ROOT, "unit", 2, art3)

    # Code 4 -> InvocationError
    art4 = tmp_path / "artifacts4"
    art4.mkdir()
    monkeypatch.setattr(apg_test.subprocess, "run", lambda *_args, **_kwargs: StubProcess(4))
    with pytest.raises(apg_test.InvocationError, match="status 4"):
        apg_test._run_pytest(REPOSITORY_ROOT, "unit", 2, art4)

    # Code 5 -> InvocationError
    art5 = tmp_path / "artifacts5"
    art5.mkdir()
    monkeypatch.setattr(apg_test.subprocess, "run", lambda *_args, **_kwargs: StubProcess(5))
    with pytest.raises(apg_test.InvocationError, match="collected no tests"):
        apg_test._run_pytest(REPOSITORY_ROOT, "unit", 2, art5)


def test_javascript_engine_prerequisite_failure_raises_invocation_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("APG_JAVASCRIPT_NODE", raising=False)
    with pytest.raises(apg_test.InvocationError, match="JavaScript test prerequisite is unavailable"):
        apg_test._javascript_engine_binding(tmp_path)


def test_node_profile_cleanup_error_inherits_harness_error() -> None:
    assert issubclass(apg_test.NodeProfileCleanupError, apg_test.HarnessError)


def test_entry_time_summary_invalidation_unlinks_stale_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stale_summary = tmp_path / "ci" / "stale-summary.json"
    apg_test.write_summary(
        stale_summary,
        suite="policy",
        test_status="pass",
        gate_status="pass",
        source_commit="d" * 40,
    )
    assert stale_summary.is_file()

    monkeypatch.setattr(apg_test, "resolve_source_commit", lambda _root: "d" * 40)
    # Simulate an early abort or unhandled exception during run
    def bomb(*_args, **_kwargs):
        raise RuntimeError("simulated sudden crash")

    monkeypatch.setattr(apg_test, "run_policy", bomb)
    with pytest.raises(RuntimeError, match="simulated sudden crash"):
        apg_test.main(["policy", "--summary-file", str(stale_summary)])

    # Stale summary must have been invalidated at entry before run_policy crashed
    assert not stale_summary.exists()


def test_admit_summary_destination_refuses_tracked_and_git_metadata_and_preserves_bytes(
    tmp_path: Path,
) -> None:
    # 1. Tracked valid receipt inside repository cannot be admitted
    sample_receipt = REPOSITORY_ROOT / "testing" / "fixtures" / "jaca_ci" / "sample-summary-pass.json"
    assert sample_receipt.is_file()
    sha_before = hashlib.sha256(sample_receipt.read_bytes()).hexdigest()
    with pytest.raises(apg_test.InvocationError, match="cannot target tracked file"):
        apg_test.admit_summary_destination(REPOSITORY_ROOT, sample_receipt)
    assert hashlib.sha256(sample_receipt.read_bytes()).hexdigest() == sha_before

    # 2. Tracked non-receipt code file cannot be admitted
    code_file = REPOSITORY_ROOT / "libexec" / "apg_test.py"
    code_sha = hashlib.sha256(code_file.read_bytes()).hexdigest()
    with pytest.raises(apg_test.InvocationError, match="cannot target tracked file"):
        apg_test.admit_summary_destination(REPOSITORY_ROOT, code_file)
    assert hashlib.sha256(code_file.read_bytes()).hexdigest() == code_sha

    # 3. Receipt-shaped file inside .git cannot be admitted
    fake_repo = tmp_path / "repo"
    fake_repo.mkdir()
    fake_git = fake_repo / ".git"
    fake_git.mkdir()
    git_receipt = fake_git / "receipt.json"
    git_receipt.write_text(json.dumps({
        "version": 1, "subproject": "apg", "suite": "policy",
        "test_status": "pass", "gate_status": "pass", "source_commit": "e" * 40,
    }), encoding="utf-8")
    git_receipt_sha = hashlib.sha256(git_receipt.read_bytes()).hexdigest()
    with pytest.raises(apg_test.InvocationError, match="cannot target Git metadata"):
        apg_test.admit_summary_destination(fake_repo, git_receipt)
    assert git_receipt.is_file()
    assert hashlib.sha256(git_receipt.read_bytes()).hexdigest() == git_receipt_sha

    # 4. Output symlink targeting protected content cannot be admitted
    symlink_target = tmp_path / "link-to-tracked.json"
    symlink_target.symlink_to(sample_receipt)
    with pytest.raises(apg_test.InvocationError, match="cannot target a symlink"):
        apg_test.admit_summary_destination(REPOSITORY_ROOT, symlink_target)
    assert symlink_target.is_symlink()
    assert hashlib.sha256(sample_receipt.read_bytes()).hexdigest() == sha_before


def test_destination_invalidate_preserves_foreign_and_corrupt_files(
    tmp_path: Path,
) -> None:
    # Foreign non-receipt JSON file at admitted path raises InvocationError and is preserved
    foreign_file = tmp_path / "foreign.json"
    foreign_file.write_text('{"notes": "unrelated data"}', encoding="utf-8")
    dest = apg_test.admit_summary_destination(REPOSITORY_ROOT, foreign_file)
    with pytest.raises(apg_test.InvocationError, match="not a recognized APGR receipt"):
        dest.invalidate()
    assert foreign_file.is_file()
    assert foreign_file.read_text(encoding="utf-8") == '{"notes": "unrelated data"}'

    # Foreign text file is preserved
    text_file = tmp_path / "notes.txt"
    text_file.write_text("plain text", encoding="utf-8")
    dest_text = apg_test.admit_summary_destination(REPOSITORY_ROOT, text_file)
    with pytest.raises(apg_test.InvocationError, match="not a recognized APGR receipt"):
        dest_text.invalidate()
    assert text_file.is_file()


def test_destination_invalidate_permission_error_raises_invocation_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stale_summary = tmp_path / "stale.json"
    apg_test.write_summary(
        stale_summary,
        suite="policy",
        test_status="pass",
        gate_status="pass",
        source_commit="f" * 40,
    )
    dest = apg_test.admit_summary_destination(REPOSITORY_ROOT, stale_summary)
    def fail_unlink(*_args, **_kwargs):
        raise PermissionError("read-only filesystem")
    monkeypatch.setattr(Path, "unlink", fail_unlink)
    with pytest.raises(apg_test.InvocationError, match="failed to invalidate stale summary"):
        dest.invalidate()


def test_early_flag_scanning_ignores_flags_as_filenames() -> None:
    suite, summary_file = apg_test._scan_early_args(["policy", "--summary-file", "--workers", "8"])
    assert suite == "policy"
    assert summary_file is None

    suite, summary_file = apg_test._scan_early_args(["unit", "--summary-file=--workers", "8"])
    assert suite == "unit"
    assert summary_file is None

    suite, summary_file = apg_test._scan_early_args(["integration", "--summary-file", "valid.json"])
    assert suite == "integration"
    assert summary_file == Path("valid.json")


def test_combined_coverage_harness_error_dominance_and_outcomes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # 1. Union _combine_coverage raises HarnessError -> reports error/error, not fail/fail
    mock_cr = apg_test.ComponentResult(tmp_path / "fake.cov", {}, apg_test.CoverageCounts(100, 100, 50, 50))
    mock_inv = apg_test.Inventory(coverage_sources={}, excluded_launchers={}, tests={})
    monkeypatch.setattr(apg_test, "load_inventory", lambda _root: mock_inv)
    monkeypatch.setattr(apg_test, "validate_inventory", lambda _r, _i: None)
    monkeypatch.setattr(apg_test, "dependency_versions", lambda: None)
    monkeypatch.setattr(apg_test, "requires_typescript_compiler", lambda _i: False)
    monkeypatch.setattr(apg_test, "requires_javascript_engine", lambda _i: False)
    monkeypatch.setattr(apg_test, "requires_node_profile_runtimes", lambda _i: False)
    monkeypatch.setattr(apg_test, "_run_pytest", lambda *_args, **_kwargs: (tmp_path / "fake.cov", {}))
    monkeypatch.setattr(apg_test, "validate_coverage_report", lambda *_args: None)
    monkeypatch.setattr(apg_test, "coverage_counts", lambda *_args: apg_test.CoverageCounts(100, 100, 50, 50))
    monkeypatch.setattr(apg_test, "enforce_threshold", lambda *_args: None)
    monkeypatch.setattr(apg_test, "resolve_source_commit", lambda _r: "a" * 40)

    summary_file = tmp_path / "ci" / "merge-harness-error.json"

    monkeypatch.setattr(
        apg_test,
        "_combine_coverage",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(apg_test.HarnessError("merge failed")),
    )
    exit_code = apg_test.main(["unit-integration", "--summary-file", str(summary_file)])
    assert exit_code == 1
    payload = json.loads(summary_file.read_text(encoding="utf-8"))
    assert payload["test_status"] == "error"
    assert payload["gate_status"] == "error"
    assert payload["suite"] == "combined"

    # 2. Simultaneous component GateShortfallError and union HarnessError: HarnessError dominates!
    summary_dom = tmp_path / "ci" / "dom-summary.json"
    component_count = 0
    def shortfall_then_pass(*args, **kwargs):
        nonlocal component_count
        component_count += 1
        if component_count == 1:
            raise apg_test.GateShortfallError("unit coverage shortfall")

    monkeypatch.setattr(apg_test, "enforce_threshold", shortfall_then_pass)
    exit_code = apg_test.main(["unit-integration", "--summary-file", str(summary_dom)])
    assert exit_code == 1
    dom_payload = json.loads(summary_dom.read_text(encoding="utf-8"))
    assert dom_payload["test_status"] == "error"
    assert dom_payload["gate_status"] == "error"


def test_main_help_leaves_existing_summary_untouched(
    tmp_path: Path,
) -> None:
    existing_receipt = tmp_path / "existing-summary.json"
    apg_test.write_summary(
        existing_receipt,
        suite="policy",
        test_status="pass",
        gate_status="pass",
        source_commit="b" * 40,
    )
    content_before = existing_receipt.read_bytes()
    with pytest.raises(SystemExit) as exc:
        apg_test.main(["--help", "--summary-file", str(existing_receipt)])
    assert exc.value.code == 0
    assert existing_receipt.read_bytes() == content_before


def test_summary_destination_and_admission_branches(tmp_path: Path) -> None:
    # 1. Target does not exist -> invalidate() returns None
    nonexistent = tmp_path / "does_not_exist.json"
    dest_nonexistent = apg_test.admit_summary_destination(REPOSITORY_ROOT, nonexistent)
    dest_nonexistent.invalidate()

    # 2. Target is directory -> invalidate() raises InvocationError
    target_dir = tmp_path / "dir_target"
    target_dir.mkdir()
    dest_dir = apg_test.SummaryDestination(target_dir, target_dir.resolve(), REPOSITORY_ROOT)
    with pytest.raises(apg_test.InvocationError, match="cannot target a directory"):
        dest_dir.invalidate()

    # 3. Target is a symlink to an APGR receipt -> admitted fails, and direct invalidate() guards against unlinking symlink
    backing_receipt = tmp_path / "backing.json"
    apg_test.write_summary(
        backing_receipt,
        suite="policy",
        test_status="pass",
        gate_status="pass",
        source_commit="1" * 40,
    )
    symlink_receipt = tmp_path / "symlink_receipt.json"
    symlink_receipt.symlink_to(backing_receipt)
    with pytest.raises(apg_test.InvocationError, match="cannot target a symlink"):
        apg_test.admit_summary_destination(REPOSITORY_ROOT, symlink_receipt)
    dest_symlink = apg_test.SummaryDestination(symlink_receipt, symlink_receipt.resolve(), REPOSITORY_ROOT)
    with pytest.raises(apg_test.InvocationError, match="cannot target a symlink"):
        dest_symlink.invalidate()
    assert symlink_receipt.is_symlink()
    assert backing_receipt.is_file()

    # 4. _is_apgr_receipt branches:
    # 4a. Oversized
    big_file = tmp_path / "big.json"
    big_file.write_bytes(b"x" * (1024 * 1024 + 1))
    assert not apg_test._is_apgr_receipt(big_file)

    # 4b. Not a dict
    arr_file = tmp_path / "arr.json"
    arr_file.write_text("[1, 2, 3]", encoding="utf-8")
    assert not apg_test._is_apgr_receipt(arr_file)

    # 4c. Version != 1
    v_file = tmp_path / "v.json"
    v_file.write_text(json.dumps({
        "version": 2, "subproject": "apg", "suite": "policy",
        "test_status": "pass", "gate_status": "pass", "source_commit": "1" * 40,
    }), encoding="utf-8")
    assert not apg_test._is_apgr_receipt(v_file)

    # 4d. Subproject != "apg"
    sub_file = tmp_path / "sub.json"
    sub_file.write_text(json.dumps({
        "version": 1, "subproject": "other", "suite": "policy",
        "test_status": "pass", "gate_status": "pass", "source_commit": "1" * 40,
    }), encoding="utf-8")
    assert not apg_test._is_apgr_receipt(sub_file)

    # 4e. Invalid suite
    suite_file = tmp_path / "suite.json"
    suite_file.write_text(json.dumps({
        "version": 1, "subproject": "apg", "suite": "bad_suite",
        "test_status": "pass", "gate_status": "pass", "source_commit": "1" * 40,
    }), encoding="utf-8")
    assert not apg_test._is_apgr_receipt(suite_file)

    # 4f. Invalid test_status
    ts_file = tmp_path / "ts.json"
    ts_file.write_text(json.dumps({
        "version": 1, "subproject": "apg", "suite": "policy",
        "test_status": "invalid", "gate_status": "pass", "source_commit": "1" * 40,
    }), encoding="utf-8")
    assert not apg_test._is_apgr_receipt(ts_file)

    # 4g. Invalid gate_status
    gs_file = tmp_path / "gs.json"
    gs_file.write_text(json.dumps({
        "version": 1, "subproject": "apg", "suite": "policy",
        "test_status": "pass", "gate_status": "invalid", "source_commit": "1" * 40,
    }), encoding="utf-8")
    assert not apg_test._is_apgr_receipt(gs_file)

    # 4h. Invalid commit (wrong length / non-hex)
    com_file = tmp_path / "com.json"
    com_file.write_text(json.dumps({
        "version": 1, "subproject": "apg", "suite": "policy",
        "test_status": "pass", "gate_status": "pass", "source_commit": "not_40_hex",
    }), encoding="utf-8")
    assert not apg_test._is_apgr_receipt(com_file)

    nonhex_file = tmp_path / "nonhex.json"
    nonhex_file.write_text(json.dumps({
        "version": 1, "subproject": "apg", "suite": "policy",
        "test_status": "pass", "gate_status": "pass", "source_commit": "z" * 40,
    }), encoding="utf-8")
    assert not apg_test._is_apgr_receipt(nonhex_file)

    # 5. admit_summary_destination branches:
    # 5a. target is directory
    with pytest.raises(apg_test.InvocationError, match="cannot target a directory"):
        apg_test.admit_summary_destination(REPOSITORY_ROOT, target_dir)

    # 5b. target is repository root
    with pytest.raises(apg_test.InvocationError, match="cannot target repository root"):
        apg_test.admit_summary_destination(REPOSITORY_ROOT, REPOSITORY_ROOT)

    # 5c. raw target has .git
    with pytest.raises(apg_test.InvocationError, match="cannot target Git metadata"):
        apg_test.admit_summary_destination(REPOSITORY_ROOT, Path(".git") / "test.json")

    # 5d. resolved target inside git metadata
    with pytest.raises(apg_test.InvocationError, match="cannot target Git metadata"):
        apg_test.admit_summary_destination(REPOSITORY_ROOT, REPOSITORY_ROOT / ".git" / "test.json")


def test_main_summary_file_equals_syntax_and_write_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # 1. --summary-file=path syntax
    eq_summary = tmp_path / "eq-summary.json"
    exit_code = apg_test.main(["policy", f"--summary-file={eq_summary}"])
    assert exit_code == 0
    assert eq_summary.is_file()

    # 2. --summary-file= with empty value attempts directory target and exits 1
    exit_code_empty = apg_test.main(["policy", "--summary-file="])
    assert exit_code_empty == 1

    # 3. _write_admitted disk failure
    dest_write_fail = tmp_path / "write-fail.json"
    def bomb_write(*args, **kwargs):
        raise OSError("write failed")
    monkeypatch.setattr(apg_test, "write_summary", bomb_write)
    exit_code_fail = apg_test.main(["policy", "--summary-file", str(dest_write_fail)])
    assert exit_code_fail == 1
    assert "failed to write summary file" in capsys.readouterr().err


def test_keyboard_interrupt_with_invalidation_failure_exits_130(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    summary_path = tmp_path / "ci" / "summary.json"
    apg_test.write_summary(
        summary_path,
        suite="policy",
        test_status="pass",
        gate_status="pass",
        source_commit="0" * 40,
    )
    monkeypatch.setattr(apg_test, "run_policy", lambda _root: (_ for _ in ()).throw(KeyboardInterrupt()))
    commits = iter(["0" * 40, "1" * 40])
    monkeypatch.setattr(apg_test, "resolve_source_commit", lambda _r: next(commits))
    original_invalidate = apg_test.SummaryDestination.invalidate
    call_count = 0
    def failing_invalidate(self):
        nonlocal call_count
        call_count += 1
        if call_count > 1:
            raise apg_test.InvocationError("disk read-only on unlinking")
        original_invalidate(self)
    monkeypatch.setattr(apg_test.SummaryDestination, "invalidate", failing_invalidate)

    exit_code = apg_test.main(["policy", "--summary-file", str(summary_path)])
    assert exit_code == 130
    captured = capsys.readouterr()
    assert "interrupted" in captured.err
    assert "git HEAD drifted during execution" in captured.err
    assert "disk read-only on unlinking" in captured.err


def test_admit_summary_destination_inverse_alias_and_dual_boundary(
    tmp_path: Path,
) -> None:
    # 1. Inverse alias: in-repository tracked symlink pointing to an outside receipt
    repo = tmp_path / "disposable-repo"
    repo.mkdir()
    apg_test.subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    apg_test.subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    apg_test.subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)

    outside_receipt = tmp_path / "outside-receipt.json"
    apg_test.write_summary(
        outside_receipt,
        suite="policy",
        test_status="pass",
        gate_status="pass",
        source_commit="3" * 40,
    )
    outside_sha = hashlib.sha256(outside_receipt.read_bytes()).hexdigest()

    tracked_link = repo / "tracked-link.json"
    tracked_link.symlink_to(outside_receipt)
    apg_test.subprocess.run(["git", "add", "tracked-link.json"], cwd=repo, check=True)
    apg_test.subprocess.run(["git", "commit", "-m", "add tracked link"], cwd=repo, check=True, capture_output=True)

    # Admission must refuse the in-repo tracked symlink
    with pytest.raises(apg_test.InvocationError, match="cannot target a symlink"):
        apg_test.admit_summary_destination(repo, tracked_link)
    # Refusal preserves link, outside receipt, and git index
    assert tracked_link.is_symlink()
    assert hashlib.sha256(outside_receipt.read_bytes()).hexdigest() == outside_sha
    ls_check = apg_test.subprocess.run(["git", "ls-files", "--error-unmatch", "tracked-link.json"], cwd=repo, capture_output=True)
    assert ls_check.returncode == 0
    status_check = apg_test.subprocess.run(["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True)
    assert status_check.stdout.strip() == ""

    # 2. Positive test: ordinary fresh gitignored destination under repository is admitted and written
    (repo / ".gitignore").write_text(".test-reports/\n")
    report_dest = repo / ".test-reports" / "apg" / "policy" / "summary.json"
    report_dest.parent.mkdir(parents=True, exist_ok=True)
    dest_ignored = apg_test.admit_summary_destination(repo, report_dest)
    dest_ignored.invalidate()
    dest_ignored.write(
        suite="policy",
        test_status="pass",
        gate_status="pass",
        source_commit="3" * 40,
    )
    assert report_dest.is_file()
    assert apg_test._is_apgr_receipt(report_dest)

    # 3. Positive test: ordinary fresh outside scratch destination is admitted and written
    outside_scratch = tmp_path / "fresh-scratch.json"
    dest_scratch = apg_test.admit_summary_destination(repo, outside_scratch)
    dest_scratch.invalidate()
    dest_scratch.write(
        suite="policy",
        test_status="pass",
        gate_status="pass",
        source_commit="3" * 40,
    )
    assert outside_scratch.is_file()
    assert apg_test._is_apgr_receipt(outside_scratch)

    # 4. Fail-closed git tracking probe: timeout raises InvocationError
    from unittest.mock import patch
    def fail_timeout(*args, **kwargs):
        raise apg_test.subprocess.TimeoutExpired(cmd=["git", "ls-files"], timeout=5)

    with patch.object(apg_test.subprocess, "run", side_effect=fail_timeout):
        with pytest.raises(apg_test.InvocationError, match="timed out"):
            apg_test.admit_summary_destination(repo, report_dest)
