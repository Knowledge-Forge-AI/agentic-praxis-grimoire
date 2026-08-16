"""Unit contracts for APGR home, identifier, and reserved-path primitives."""

from __future__ import annotations

from pathlib import Path
import stat
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src"))

from agentic_praxis_grimoire import paths


def test_global_home_precedence_is_cli_then_environment_then_default(
    tmp_path: Path,
) -> None:
    home = tmp_path / "operator-home"
    environment = {"APGR_HOME": str(tmp_path / "environment")}
    assert paths.resolve_global_home(home=home, environment={}) == home / ".apgr"
    assert (
        paths.resolve_global_home(environment=environment, home=home)
        == tmp_path / "environment"
    )
    assert (
        paths.resolve_global_home(
            cli_home=tmp_path / "explicit",
            environment=environment,
            home=home,
        )
        == tmp_path / "explicit"
    )


@pytest.mark.parametrize(
    "value",
    ["", ".", "..", "a/b", r"a\\b", "a/../b", "a\x00b", " leading"],
)
def test_path_identifiers_reject_traversal_separators_and_ambiguous_values(
    value: str,
) -> None:
    with pytest.raises(paths.PathContractError):
        paths.validate_identifier(value, "phase")


def test_phase_path_is_bounded_and_private_home_can_be_created(tmp_path: Path) -> None:
    home = paths.ensure_global_home(tmp_path / "home")
    assert stat.S_IMODE(home.stat().st_mode) == 0o700
    phase = paths.outbox_phase_path(tmp_path / "outbox", "project", "APG82")
    assert phase == tmp_path / "outbox" / "project" / "APG82"
    with pytest.raises(paths.PathContractError):
        paths.outbox_phase_path(tmp_path / "outbox", "project", "../APG82")


def test_reserved_adapter_root_and_descendants_are_refused(tmp_path: Path) -> None:
    home = tmp_path / "home"
    reserved = paths.reserved_adapter_path(home)
    assert reserved == home / "agentic-praxis-grimoire-nd"
    for candidate in (reserved, reserved / "state", reserved / "nested" / "file"):
        with pytest.raises(paths.PathContractError, match="reserved"):
            paths.reject_reserved_adapter_path(candidate, home)

    allowed = tmp_path / "other"
    assert paths.reject_reserved_adapter_path(allowed, home) == allowed


def test_global_home_and_project_paths_reject_relative_inputs(tmp_path: Path) -> None:
    with pytest.raises(paths.PathContractError, match="absolute"):
        paths.resolve_global_home("relative")
    with pytest.raises(paths.PathContractError, match="absolute"):
        paths.outbox_phase_path("relative", "project", "APG82")
    with pytest.raises(paths.PathContractError, match="absolute"):
        paths.project_config_path("relative")
    project = tmp_path / "project"
    assert paths.project_config_path(project) == project / ".apgr" / "config.toml"
    assert paths.global_config_path(tmp_path / "home").name == "config.toml"


def test_global_home_refuses_symlink_and_non_directory(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(paths.PathContractError, match="ordinary directory"):
        paths.ensure_global_home(link)
    file_path = tmp_path / "file"
    file_path.write_text("file", encoding="utf-8")
    with pytest.raises(paths.PathContractError, match="ordinary directory"):
        paths.ensure_global_home(file_path)


def test_project_discovery_absence_file_start_and_required_failure(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    assert paths.discover_project_root(missing) is None
    plain = tmp_path / "plain"
    plain.mkdir()
    source = plain / "source.py"
    source.write_text("", encoding="utf-8")
    assert paths.discover_project_root(source) == paths.discover_project_root(plain)
    with pytest.raises(paths.PathContractError, match="Git worktree"):
        paths.require_project_root(Path("/"))
    with pytest.raises(paths.PathContractError, match="existing directory"):
        paths.discover_project_root(explicit=missing)


def test_identifier_accepts_boundary_and_rejects_oversize() -> None:
    value = "a" + "b" * 127
    assert paths.validate_identifier(value) == value
    assert paths.validate_project_phase("project", "APG82") == ("project", "APG82")
    with pytest.raises(paths.PathContractError):
        paths.validate_identifier(value + "c")
