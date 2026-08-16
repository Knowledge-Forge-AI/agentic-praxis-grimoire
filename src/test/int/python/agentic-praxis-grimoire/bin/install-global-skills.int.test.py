"""Integration contracts for the multi-repository global-skill installer."""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat

from src.test.install_global_skills_cases import (
    add_skill,
    read_state,
    run_command,
    tree_snapshot,
)


def environment(home: Path, **values: str) -> dict[str, str]:
    return {"HOME": str(home), **values}


def test_help_missing_and_invalid_agent_are_bounded() -> None:
    help_result = run_command("--help")
    assert help_result.returncode == 0
    assert "install-global-skills AGENT" in help_result.stdout
    missing = run_command()
    invalid = run_command("other")
    assert missing.returncode == invalid.returncode == 2
    assert "usage:" in missing.stderr.lower()
    assert "invalid choice" in invalid.stderr


def test_codex_default_installs_default_apg_and_ignores_codex_home(
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    apg = tmp_path / "local" / "agentic-praxis-grimoire"
    skill = add_skill(apg, "nested/apg-skill")
    result = run_command(
        "codex",
        environment=environment(
            home,
            LOCAL_PROJ_INSTALL=str(apg.parent),
            CODEX_HOME=str(tmp_path / "legacy"),
        ),
    )
    root = home / ".agents" / "skills"
    assert result.returncode == 0, result.stderr
    assert (root / "apg-skill").resolve() == skill
    assert not (tmp_path / "legacy").exists()
    assert "detected automatically" in result.stdout


def test_claude_config_and_exact_override_destinations(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    skill = add_skill(repository, "skill")
    home = tmp_path / "home"
    configured = tmp_path / "claude configuration"
    result = run_command(
        "claude",
        repository,
        environment=environment(home, CLAUDE_CONFIG_DIR=str(configured)),
    )
    assert result.returncode == 0, result.stderr
    assert (configured / "skills" / "skill").resolve() == skill
    assert "top-level skills directory" in result.stdout

    override = tmp_path / "exact skills"
    second = run_command(
        "codex",
        repository,
        "--skills-root",
        override,
        environment=environment(home),
    )
    assert second.returncode == 0, second.stderr
    assert (override / "skill").resolve() == skill


def test_two_sources_form_one_state_and_preserve_source_bytes(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first repository"
    second = tmp_path / "second repository"
    alpha = add_skill(first, "nested/alpha")
    beta = add_skill(second, "βeta")
    before = (tree_snapshot(first), tree_snapshot(second))
    root = tmp_path / "skills"
    result = run_command(
        "codex", first, second, "--skills-root", root, environment={}
    )
    assert result.returncode == 0, result.stderr
    assert (root / "alpha").resolve() == alpha
    assert (root / "βeta").resolve() == beta
    installed = read_state(root)
    assert len(installed["sources"]) == 2
    assert set(installed["links"]) == {"alpha", "βeta"}
    assert before == (tree_snapshot(first), tree_snapshot(second))


def test_include_apg_and_duplicate_names_fail_before_mutation(
    tmp_path: Path,
) -> None:
    apg = tmp_path / "apg"
    explicit = tmp_path / "explicit"
    add_skill(apg, "apg")
    add_skill(explicit, "other")
    root = tmp_path / "combined"
    included = run_command(
        "claude",
        explicit,
        "--include-apg",
        "--apg-root",
        apg,
        "--skills-root",
        root,
        environment={},
    )
    assert included.returncode == 0, included.stderr
    assert {"apg", "other"} <= {entry.name for entry in root.iterdir()}

    duplicate = tmp_path / "duplicate"
    add_skill(duplicate, "nested/OTHER")
    collision_root = tmp_path / "collision"
    collision = run_command(
        "codex",
        explicit,
        duplicate,
        "--skills-root",
        collision_root,
        environment={},
    )
    assert collision.returncode == 2
    assert "Duplicate global skill" in collision.stderr
    assert not collision_root.exists()


def test_source_destination_overlap_is_refused_before_mutation(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    add_skill(repository, "skill")
    destination = repository / "generated" / "skills"
    result = run_command(
        "codex",
        repository,
        "--skills-root",
        destination,
        environment={},
    )

    assert result.returncode == 2
    assert "overlap" in result.stderr.lower()
    assert not destination.exists()


def test_rerun_add_remove_and_omit_source_update_one_owned_set(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    alpha = add_skill(first, "alpha")
    beta = add_skill(second, "beta")
    root = tmp_path / "skills"
    assert run_command(
        "codex", first, second, "--skills-root", root, environment={}
    ).returncode == 0
    repeated = run_command(
        "codex", first, second, "--skills-root", root, environment={}
    )
    assert repeated.returncode == 0
    assert "unchanged: 2" in repeated.stdout

    (alpha / "SKILL.md").unlink()
    gamma = add_skill(first, "gamma")
    updated = run_command(
        "codex", first, "--skills-root", root, environment={}
    )
    assert updated.returncode == 0, updated.stderr
    assert not (root / "alpha").exists()
    assert not (root / "beta").exists()
    assert (root / "gamma").resolve() == gamma
    assert beta.exists()


def test_check_dry_run_and_json_are_read_only_and_deterministic(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    add_skill(repository, "alpha")
    root = tmp_path / "skills"
    dry = run_command(
        "codex",
        repository,
        "--skills-root",
        root,
        "--dry-run",
        "--format",
        "json",
        environment={},
    )
    assert dry.returncode == 0
    assert not root.exists()
    assert dry.stdout == run_command(
        "codex",
        repository,
        "--skills-root",
        root,
        "--dry-run",
        "--format",
        "json",
        environment={},
    ).stdout
    assert json.loads(dry.stdout)["mode"] == "dry-run"

    assert run_command(
        "codex", repository, "--skills-root", root, environment={}
    ).returncode == 0
    before = tree_snapshot(root)
    assert run_command(
        "codex", repository, "--skills-root", root, "--check", environment={}
    ).returncode == 0
    add_skill(repository, "beta")
    drift = run_command(
        "codex", repository, "--skills-root", root, "--check", environment={}
    )
    assert drift.returncode == 1
    assert tree_snapshot(root) == before


def test_unmanaged_and_other_owner_entries_are_preserved_and_refused(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    source = add_skill(repository, "skill")
    root = tmp_path / "skills"
    root.mkdir()
    unmanaged = root / "unmanaged"
    unmanaged.write_text("keep\n", encoding="utf-8")
    (root / "skill").symlink_to(source)
    result = run_command(
        "codex", repository, "--skills-root", root, environment={}
    )
    assert result.returncode == 2
    assert "unmanaged" in result.stderr.lower()
    assert unmanaged.read_text(encoding="utf-8") == "keep\n"
    assert (root / "skill").resolve() == source

    (root / "skill").unlink()
    (root / ".flatten-skill-symlinks-state.json").write_text(
        "{}\n", encoding="utf-8"
    )
    reserved = run_command(
        "codex", repository, "--skills-root", root, environment={}
    )
    assert reserved.returncode == 2
    assert (root / ".flatten-skill-symlinks-state.json").exists()


def test_changed_owned_target_and_wrong_agent_state_fail_closed(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    add_skill(repository, "skill")
    root = tmp_path / "skills"
    assert run_command(
        "codex", repository, "--skills-root", root, environment={}
    ).returncode == 0
    replacement = tmp_path / "replacement"
    replacement.mkdir()
    (root / "skill").unlink()
    (root / "skill").symlink_to(replacement)
    changed = run_command(
        "codex", repository, "--skills-root", root, environment={}
    )
    assert changed.returncode == 2
    assert (root / "skill").resolve() == replacement
    assert run_command(
        "claude", repository, "--skills-root", root, environment={}
    ).returncode == 2


def test_uninstall_removes_exact_owned_state_only(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    add_skill(repository, "skill")
    root = tmp_path / "parent" / "skills"
    assert run_command(
        "codex", repository, "--skills-root", root, environment={}
    ).returncode == 0
    unrelated = root / "manual"
    unrelated.write_text("preserve\n", encoding="utf-8")
    result = run_command(
        "codex", "--skills-root", root, "--uninstall", environment={}
    )
    assert result.returncode == 0, result.stderr
    assert unrelated.read_text(encoding="utf-8") == "preserve\n"
    assert not (root / "skill").exists()
    assert not (root / ".install-global-skills-state.json").exists()


def test_spaces_unicode_lock_and_state_permissions(tmp_path: Path) -> None:
    repository = tmp_path / "répo source"
    skill = add_skill(repository, "nested/δelta")
    root = tmp_path / "skill target"
    root.mkdir()
    (root / ".install-global-skills.lock").mkdir(mode=0o700)
    blocked = run_command(
        "codex", repository, "--skills-root", root, environment={}
    )
    assert blocked.returncode == 2
    assert not (root / "δelta").exists()
    (root / ".install-global-skills.lock").rmdir()
    installed = run_command(
        "codex", repository, "--skills-root", root, environment={}
    )
    assert installed.returncode == 0, installed.stderr
    assert (root / "δelta").resolve() == skill
    metadata = (root / ".install-global-skills-state.json").stat()
    assert stat.S_IMODE(metadata.st_mode) == 0o600
    assert metadata.st_nlink == 1


def test_control_bearing_environment_and_cli_paths_fail_before_output(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    add_skill(repository, "skill")
    safe_home = tmp_path / "home"
    cases = (
        (
            ("codex",),
            environment(Path("/tmp/unsafe\nhome")),
            "/tmp/unsafe\nhome",
        ),
        (
            ("claude", repository),
            environment(
                safe_home,
                CLAUDE_CONFIG_DIR="/tmp/unsafe\rconfiguration",
            ),
            "/tmp/unsafe\rconfiguration",
        ),
        (
            ("codex",),
            environment(
                safe_home,
                LOCAL_PROJ_INSTALL="/tmp/unsafe\tlocal",
            ),
            "/tmp/unsafe\tlocal",
        ),
        (
            (
                "codex",
                repository,
                "--skills-root",
                "/tmp/unsafe\x7fskills",
            ),
            environment(safe_home),
            "/tmp/unsafe\x7fskills",
        ),
        (
            ("codex", "--apg-root", "/tmp/unsafe\napg"),
            environment(safe_home),
            "/tmp/unsafe\napg",
        ),
        (
            ("codex", "/tmp/unsafe\trepository"),
            environment(safe_home),
            "/tmp/unsafe\trepository",
        ),
    )
    for arguments, selected_environment, unsafe in cases:
        result = run_command(
            *arguments, environment=selected_environment
        )
        assert result.returncode == 2
        assert unsafe not in result.stderr
        assert "control" in result.stderr
