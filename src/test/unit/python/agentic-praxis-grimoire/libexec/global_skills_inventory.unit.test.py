"""Unit contracts for global-skill source and destination inventory."""

from __future__ import annotations

import os
from pathlib import Path
import sys

import pytest

from src.test.apg_test_support import repository_root
from src.test.install_global_skills_cases import add_skill


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import global_skills_inventory as inventory  # noqa: E402
import install_global_skills as command  # noqa: E402


def test_cli_has_closed_agent_and_exclusive_modes() -> None:
    assert command.parse_args(["codex"]).agent == "codex"
    assert command.parse_args(["claude"]).agent == "claude"
    with pytest.raises(SystemExit):
        command.parse_args(["other"])
    with pytest.raises(command.InstallError, match="combined"):
        command.resolve_request(
            command.parse_args(["codex", "--check", "--dry-run"]), {}
        )


def test_codex_default_ignores_codex_home_and_override_is_exact(
    tmp_path: Path,
) -> None:
    environment = {
        "HOME": str(tmp_path / "home"),
        "CODEX_HOME": str(tmp_path / "legacy"),
    }
    assert inventory.destination_for("codex", None, environment) == (
        tmp_path / "home" / ".agents" / "skills"
    )
    override = tmp_path / "exact"
    assert inventory.destination_for("codex", override, {}) == override


def test_claude_default_uses_config_then_home(tmp_path: Path) -> None:
    home = tmp_path / "home"
    configured = tmp_path / "configuration"
    assert inventory.destination_for(
        "claude", None, {"HOME": str(home)}
    ) == home / ".claude" / "skills"
    assert inventory.destination_for(
        "claude",
        None,
        {"HOME": str(home), "CLAUDE_CONFIG_DIR": str(configured)},
    ) == configured / "skills"
    with pytest.raises(inventory.InventoryError, match="HOME"):
        inventory.destination_for("claude", None, {})


def test_apg_default_explicit_and_include_source_semantics(
    tmp_path: Path,
) -> None:
    apg = tmp_path / "installed" / "agentic-praxis-grimoire"
    explicit = tmp_path / "explicit"
    add_skill(apg, "apg")
    add_skill(explicit, "other")
    environment = {"HOME": str(tmp_path / "home"), "LOCAL_PROJ_INSTALL": str(apg.parent)}

    assert inventory.source_values((), False, None, environment) == (apg,)
    assert inventory.source_values((explicit,), False, None, environment) == (
        explicit,
    )
    assert inventory.source_values((explicit,), True, None, environment) == (
        explicit,
        apg,
    )
    with pytest.raises(inventory.InventoryError, match="requires"):
        inventory.source_values((), True, None, environment)


def test_recursive_discovery_skips_metadata_and_source_symlinks(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    alpha = add_skill(repository, "nested/alpha")
    add_skill(repository, "node_modules/dependency")
    external = add_skill(tmp_path / "external", "linked")
    (repository / "skills" / "linked").symlink_to(external)
    records = inventory.discover_repository(repository)
    assert [(record.name, record.source) for record in records] == [
        ("alpha", alpha)
    ]


def test_collision_ledger_is_case_aware_and_case_insensitive(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    add_skill(first, "nested/Shared")
    add_skill(second, "other/shared")
    with pytest.raises(inventory.InventoryError, match="Duplicate global skill"):
        inventory.build_inventory((first, second), tmp_path / "destination")


def test_duplicate_nested_and_overlapping_roots_fail_before_inventory(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    add_skill(repository, "skill")
    with pytest.raises(inventory.InventoryError, match="duplicate"):
        inventory.build_inventory((repository, repository), tmp_path / "output")
    nested = repository / "nested-repository"
    add_skill(nested, "other")
    with pytest.raises(inventory.InventoryError, match="nested"):
        inventory.build_inventory((repository, nested), tmp_path / "output")
    with pytest.raises(inventory.InventoryError, match="overlap"):
        inventory.build_inventory((repository,), repository / "skills" / "output")


def test_inventory_is_deterministic_and_hashes_marker_bytes(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    add_skill(repository, "βeta", "# Beta\n")
    add_skill(repository, "alpha", "# Alpha\n")
    destination = tmp_path / "destination"
    first = inventory.build_inventory((repository,), destination)
    second = inventory.build_inventory((repository,), destination)
    assert first == second
    assert [skill.name for skill in first.skills] == ["alpha", "βeta"]
    assert all(len(skill.skill_sha256) == 64 for skill in first.skills)


def test_repository_root_symlink_and_unsafe_output_name_are_refused(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    add_skill(repository, "skill")
    linked = tmp_path / "linked"
    linked.symlink_to(repository, target_is_directory=True)
    with pytest.raises(inventory.InventoryError, match="symlink"):
        inventory.discover_repository(linked)
    with pytest.raises(inventory.InventoryError, match="safe path component"):
        inventory.validate_component("bad\nname", "skill name")


def test_root_resolution_rejects_unsafe_and_contradictory_inputs(
    tmp_path: Path,
) -> None:
    with pytest.raises(inventory.InventoryError, match="absolute"):
        inventory.destination_for("codex", Path("relative"), {})
    with pytest.raises(inventory.InventoryError, match="unsupported agent"):
        inventory.destination_for("other", None, {"HOME": str(tmp_path)})
    with pytest.raises(inventory.InventoryError, match="CLAUDE_CONFIG_DIR"):
        inventory.destination_for(
            "claude",
            None,
            {"HOME": str(tmp_path), "CLAUDE_CONFIG_DIR": "relative"},
        )
    with pytest.raises(inventory.InventoryError, match="LOCAL_PROJ_INSTALL"):
        inventory.apg_repository(
            None, {"HOME": str(tmp_path), "LOCAL_PROJ_INSTALL": "relative"}
        )
    with pytest.raises(inventory.InventoryError, match="requires --include-apg"):
        inventory.source_values(
            (tmp_path / "repository",),
            False,
            tmp_path / "apg",
            {"HOME": str(tmp_path)},
        )

    missing = tmp_path / "missing"
    with pytest.raises(inventory.InventoryError, match="unavailable"):
        inventory.resolve_repository(missing)
    regular = tmp_path / "regular"
    regular.write_text("not a repository", encoding="utf-8")
    with pytest.raises(inventory.InventoryError, match="not a directory"):
        inventory.resolve_repository(regular)
    repository = tmp_path / "repository"
    repository.mkdir()
    with pytest.raises(inventory.InventoryError, match="requires a skills"):
        inventory.resolve_repository(repository)
    skills = repository / "skills"
    skills.write_text("unsafe", encoding="utf-8")
    with pytest.raises(inventory.InventoryError, match="skills path is unsafe"):
        inventory.resolve_repository(repository)


def test_indirect_marker_is_not_discovered(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    skill = repository / "skills" / "skill"
    skill.mkdir(parents=True)
    target = tmp_path / "marker"
    target.write_text("# Indirect\n", encoding="utf-8")
    (skill / "SKILL.md").symlink_to(target)

    assert inventory.discover_repository(repository) == ()
    assert inventory.apg_repository(tmp_path / "exact-apg", {}) == (
        tmp_path / "exact-apg"
    )
    with pytest.raises(inventory.InventoryError, match="no direct regular"):
        inventory.build_inventory((repository,), tmp_path / "destination")


def test_all_path_inputs_reject_ascii_controls_without_echoing_values(
    tmp_path: Path,
) -> None:
    controls = ("\n", "\r", "\t", "\x7f")
    for control in controls:
        unsafe = f"/tmp/unsafe{control}path"
        checks = (
            lambda: inventory.destination_for(
                "codex", None, {"HOME": unsafe}
            ),
            lambda: inventory.destination_for(
                "claude",
                None,
                {"HOME": str(tmp_path), "CLAUDE_CONFIG_DIR": unsafe},
            ),
            lambda: inventory.apg_repository(
                None,
                {"HOME": str(tmp_path), "LOCAL_PROJ_INSTALL": unsafe},
            ),
            lambda: inventory.destination_for(
                "codex", Path(unsafe), {}
            ),
            lambda: inventory.apg_repository(Path(unsafe), {}),
            lambda: inventory.resolve_repository(Path(unsafe)),
        )
        for check in checks:
            with pytest.raises(inventory.InventoryError) as captured:
                check()
            assert unsafe not in str(captured.value)

    with pytest.raises(inventory.InventoryError, match="valid path"):
        inventory.destination_for("codex", Path("/tmp/nul\x00path"), {})


def test_path_inputs_preserve_spaces_unicode_and_interior_periods(
    tmp_path: Path,
) -> None:
    home = tmp_path / "home with space.β"
    repository = tmp_path / "repository with space.β"
    add_skill(repository, "skill")

    assert inventory.destination_for(
        "codex", None, {"HOME": str(home)}
    ) == home / ".agents" / "skills"
    assert inventory.apg_repository(repository, {}) == repository
    assert inventory.resolve_repository(repository).repository == repository
