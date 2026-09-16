"""Tests for closed directory token resolution and profile security validation."""

from __future__ import annotations

import os
import stat
from typing import Any, cast
from pathlib import Path

import claude_model_catalog as catalog
import claude_vc_profile as launcher
import pytest
from claude_profile_directories import (
    APGR_HOME_ENVIRONMENT,
    APGR_SCRATCH_OVERRIDE_ENVIRONMENT,
    HOST_DIRECTORY_TOKENS,
    SCRATCH_DIRECTORY_TOKENS,
    SUPPORTED_DIRECTORY_TOKENS,
    ProfileDirectoryError,
    resolve_profile_directories,
    resolve_scratch,
    resolve_user_home,
    validate_directory_tokens,
)


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    env: dict[str, str] = {}
    monkeypatch.delenv(APGR_HOME_ENVIRONMENT, raising=False)
    monkeypatch.delenv(APGR_SCRATCH_OVERRIDE_ENVIRONMENT, raising=False)
    return env


@pytest.fixture
def secure_home(tmp_path: Path) -> Path:
    home = (tmp_path.resolve() / "user_home")
    home.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(home, 0o700)
    return home


@pytest.fixture
def secure_scratch(tmp_path: Path) -> Path:
    scratch = (tmp_path.resolve() / "agent_scratch")
    scratch.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(scratch, 0o700)
    return scratch


# --- Group 1: Token validation tests ---


def test_supported_tokens_contract() -> None:
    assert SUPPORTED_DIRECTORY_TOKENS == frozenset({"user-home", "scratch"})
    assert SCRATCH_DIRECTORY_TOKENS == ["scratch"]
    assert HOST_DIRECTORY_TOKENS == ["user-home", "scratch"]


@pytest.mark.parametrize(
    "bad_tokens",
    [
        ["unknown-token"],
        [""],
        ["user-home", "scratch", "unknown"],
        ["relative/path"],
        ["user-home", "user-home"],
        ["scratch", "scratch"],
    ],
)
def test_validate_directory_tokens_malformed(bad_tokens: list[str]) -> None:
    with pytest.raises(ProfileDirectoryError):
        validate_directory_tokens(bad_tokens)


@pytest.mark.parametrize(
    "bad_type",
    [
        "user-home",
        {"user-home": "scratch"},
        123,
        None,
    ],
)
def test_validate_directory_tokens_non_sequence(bad_type: object) -> None:
    with pytest.raises(ProfileDirectoryError):
        validate_directory_tokens(cast(Any, bad_type))


def test_validate_directory_tokens_valid() -> None:
    validate_directory_tokens([])
    validate_directory_tokens(["scratch"])
    validate_directory_tokens(["user-home", "scratch"])


# --- Group 2: User Home resolution & security validation ---


def test_resolve_user_home_success(secure_home: Path) -> None:
    resolved = resolve_user_home(home=secure_home)
    assert resolved == secure_home
    assert resolved.is_absolute()
    assert resolved.is_dir()


def test_resolve_user_home_via_environment(secure_home: Path) -> None:
    env = {"HOME": str(secure_home)}
    resolved = resolve_user_home(environment=env)
    assert resolved == secure_home


def test_resolve_user_home_relative_path() -> None:
    with pytest.raises(ProfileDirectoryError, match="must be absolute"):
        resolve_user_home(home="relative/home")


def test_resolve_user_home_not_exists(tmp_path: Path) -> None:
    missing = tmp_path.resolve() / "missing_home"
    with pytest.raises(ProfileDirectoryError, match="does not exist"):
        resolve_user_home(home=missing)


def test_resolve_user_home_is_file(tmp_path: Path) -> None:
    file_path = tmp_path.resolve() / "home_file"
    file_path.touch()
    with pytest.raises(ProfileDirectoryError, match="not a directory"):
        resolve_user_home(home=file_path)


def test_resolve_user_home_symlink(secure_home: Path, tmp_path: Path) -> None:
    link = tmp_path.resolve() / "home_symlink"
    link.symlink_to(secure_home)
    with pytest.raises(ProfileDirectoryError, match="symlink"):
        resolve_user_home(home=link)


def test_resolve_user_home_symlink_ancestor(secure_home: Path, tmp_path: Path) -> None:
    link_parent = tmp_path.resolve() / "ancestor_link"
    real_parent = tmp_path.resolve() / "ancestor_real"
    real_parent.mkdir(mode=0o700, exist_ok=True)
    child = real_parent / "child_home"
    child.mkdir(mode=0o700, exist_ok=True)
    link_parent.symlink_to(real_parent)

    path_via_link = link_parent / "child_home"
    with pytest.raises(ProfileDirectoryError, match="symlink"):
        resolve_user_home(home=path_via_link)


def test_resolve_user_home_unsafe_owner(
    secure_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    orig_lstat = Path.lstat

    def fake_lstat(path_obj: Path) -> os.stat_result:
        real_stat = orig_lstat(path_obj)
        if path_obj == secure_home:
            return os.stat_result(
                (
                    real_stat.st_mode,
                    real_stat.st_ino,
                    real_stat.st_dev,
                    real_stat.st_nlink,
                    99999,
                    real_stat.st_gid,
                    real_stat.st_size,
                    real_stat.st_atime,
                    real_stat.st_mtime,
                    real_stat.st_ctime,
                )
            )
        return real_stat

    monkeypatch.setattr(Path, "lstat", fake_lstat)
    with pytest.raises(ProfileDirectoryError, match="owned by current user"):
        resolve_user_home(home=secure_home)


def test_resolve_user_home_unsafe_ancestor_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path.resolve() / "home"
    home.mkdir(mode=0o700, exist_ok=True)

    orig_lstat = Path.lstat

    def fake_lstat(path_obj: Path) -> os.stat_result:
        real_stat = orig_lstat(path_obj)
        if path_obj == tmp_path.resolve():
            return os.stat_result(
                (
                    real_stat.st_mode,
                    real_stat.st_ino,
                    real_stat.st_dev,
                    real_stat.st_nlink,
                    99999,  # untrusted ancestor owner
                    real_stat.st_gid,
                    real_stat.st_size,
                    real_stat.st_atime,
                    real_stat.st_mtime,
                    real_stat.st_ctime,
                )
            )
        return real_stat

    monkeypatch.setattr(Path, "lstat", fake_lstat)
    with pytest.raises(ProfileDirectoryError, match="untrusted owner"):
        resolve_user_home(home=home)


def test_resolve_user_home_unsafe_mode_world_writable(
    secure_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    orig_lstat = Path.lstat
    monkeypatch.setattr(
        Path,
        "lstat",
        lambda p: (
            os.stat_result((stat.S_IFDIR | 0o777, *orig_lstat(p)[1:]))
            if p == secure_home
            else orig_lstat(p)
        ),
    )
    with pytest.raises(ProfileDirectoryError, match="unsafe permissions"):
        resolve_user_home(home=secure_home)


def test_resolve_user_home_unsafe_mode_group_writable(
    secure_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    orig_lstat = Path.lstat
    monkeypatch.setattr(
        Path,
        "lstat",
        lambda p: (
            os.stat_result((stat.S_IFDIR | 0o775, *orig_lstat(p)[1:]))
            if p == secure_home
            else orig_lstat(p)
        ),
    )
    with pytest.raises(ProfileDirectoryError, match="unsafe permissions"):
        resolve_user_home(home=secure_home)


def test_resolve_user_home_unsafe_ancestor_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent = tmp_path.resolve() / "bad_mode_parent"
    parent.mkdir(mode=0o700, exist_ok=True)
    child = parent / "home"
    child.mkdir(mode=0o700, exist_ok=True)

    orig_lstat = Path.lstat

    def fake_lstat(path_obj: Path) -> os.stat_result:
        real_stat = orig_lstat(path_obj)
        if path_obj == parent:
            # Group and world writable directory without sticky bit
            fake_mode = stat.S_IFDIR | 0o777
            return os.stat_result(
                (
                    fake_mode,
                    real_stat.st_ino,
                    real_stat.st_dev,
                    real_stat.st_nlink,
                    os.getuid(),
                    real_stat.st_gid,
                    real_stat.st_size,
                    real_stat.st_atime,
                    real_stat.st_mtime,
                    real_stat.st_ctime,
                )
            )
        return real_stat

    monkeypatch.setattr(Path, "lstat", fake_lstat)
    with pytest.raises(ProfileDirectoryError, match="group or world writable"):
        resolve_user_home(home=child)


# --- Group 3: Scratch override (APGR_AGENT_SCRATCH_ROOT) ---


def test_scratch_override_success(secure_scratch: Path) -> None:
    env = {APGR_SCRATCH_OVERRIDE_ENVIRONMENT: str(secure_scratch)}
    resolved = resolve_scratch(environment=env)
    assert resolved == secure_scratch
    assert resolved.is_absolute()
    assert resolved.is_dir()


def test_scratch_override_empty() -> None:
    env = {APGR_SCRATCH_OVERRIDE_ENVIRONMENT: "   "}
    with pytest.raises(ProfileDirectoryError, match="must not be empty"):
        resolve_scratch(environment=env)


def test_scratch_override_relative() -> None:
    env = {APGR_SCRATCH_OVERRIDE_ENVIRONMENT: "relative/scratch"}
    with pytest.raises(ProfileDirectoryError, match="must be an absolute path"):
        resolve_scratch(environment=env)


def test_scratch_override_missing_never_created(tmp_path: Path) -> None:
    missing = tmp_path.resolve() / "missing_override_scratch"
    env = {APGR_SCRATCH_OVERRIDE_ENVIRONMENT: str(missing)}
    with pytest.raises(ProfileDirectoryError, match="does not exist"):
        resolve_scratch(environment=env)
    assert not missing.exists(), "Arbitrary override path must NEVER be created"


def test_scratch_override_is_file(tmp_path: Path) -> None:
    target_file = tmp_path.resolve() / "scratch_is_file"
    target_file.touch()
    env = {APGR_SCRATCH_OVERRIDE_ENVIRONMENT: str(target_file)}
    with pytest.raises(ProfileDirectoryError, match="not a directory"):
        resolve_scratch(environment=env)


def test_scratch_override_symlink(secure_scratch: Path, tmp_path: Path) -> None:
    link = tmp_path.resolve() / "scratch_link"
    link.symlink_to(secure_scratch)
    env = {APGR_SCRATCH_OVERRIDE_ENVIRONMENT: str(link)}
    with pytest.raises(ProfileDirectoryError, match="symlink"):
        resolve_scratch(environment=env)


def test_scratch_override_symlink_ancestor(tmp_path: Path) -> None:
    real_parent = tmp_path.resolve() / "scratch_ancestor_real"
    real_parent.mkdir(mode=0o700, exist_ok=True)
    link_parent = tmp_path.resolve() / "scratch_ancestor_link"
    link_parent.symlink_to(real_parent)
    child = real_parent / "target_scratch"
    child.mkdir(mode=0o700, exist_ok=True)

    path_via_link = link_parent / "target_scratch"
    env = {APGR_SCRATCH_OVERRIDE_ENVIRONMENT: str(path_via_link)}
    with pytest.raises(ProfileDirectoryError, match="symlink"):
        resolve_scratch(environment=env)


def test_scratch_override_unsafe_owner(
    secure_scratch: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    orig_lstat = Path.lstat

    def fake_lstat(path_obj: Path) -> os.stat_result:
        real_stat = orig_lstat(path_obj)
        if path_obj == secure_scratch:
            return os.stat_result(
                (
                    real_stat.st_mode,
                    real_stat.st_ino,
                    real_stat.st_dev,
                    real_stat.st_nlink,
                    99999,
                    real_stat.st_gid,
                    real_stat.st_size,
                    real_stat.st_atime,
                    real_stat.st_mtime,
                    real_stat.st_ctime,
                )
            )
        return real_stat

    monkeypatch.setattr(Path, "lstat", fake_lstat)
    env = {APGR_SCRATCH_OVERRIDE_ENVIRONMENT: str(secure_scratch)}
    with pytest.raises(ProfileDirectoryError, match="owned by current user"):
        resolve_scratch(environment=env)


def test_scratch_override_unsafe_mode(
    secure_scratch: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    orig_lstat = Path.lstat
    monkeypatch.setattr(
        Path,
        "lstat",
        lambda p: (
            os.stat_result((stat.S_IFDIR | 0o777, *orig_lstat(p)[1:]))
            if p == secure_scratch
            else orig_lstat(p)
        ),
    )
    env = {APGR_SCRATCH_OVERRIDE_ENVIRONMENT: str(secure_scratch)}
    with pytest.raises(ProfileDirectoryError, match="unsafe permissions"):
        resolve_scratch(environment=env)


def test_scratch_override_not_writable(secure_scratch: Path) -> None:
    os.chmod(secure_scratch, 0o500)
    try:
        env = {APGR_SCRATCH_OVERRIDE_ENVIRONMENT: str(secure_scratch)}
        with pytest.raises(ProfileDirectoryError, match="not writable"):
            resolve_scratch(environment=env)
    finally:
        os.chmod(secure_scratch, 0o700)


# --- Group 4: Default scratch creation & resolution (APGR_HOME/scratch) ---


def test_default_scratch_creation_restrictive(tmp_path: Path) -> None:
    apgr_home = tmp_path.resolve() / "fake_apgr_home"
    apgr_home.mkdir(mode=0o700)
    env = {APGR_HOME_ENVIRONMENT: str(apgr_home)}
    scratch = apgr_home / "scratch"
    assert not scratch.exists()

    resolved = resolve_scratch(environment=env)
    assert resolved == scratch
    assert scratch.is_dir()
    info = scratch.stat()
    assert stat.S_IMODE(info.st_mode) == 0o700
    assert info.st_uid == os.getuid()


def test_standalone_default_creates_only_owned_children(secure_home: Path) -> None:
    scratch = resolve_scratch(environment={}, home=secure_home)
    assert scratch == secure_home / ".apgr" / "scratch"
    assert sorted(p.name for p in secure_home.iterdir()) == [".apgr"]
    assert sorted(p.name for p in scratch.parent.iterdir()) == ["scratch"]
    assert stat.S_IMODE(scratch.stat().st_mode) == 0o700
    assert stat.S_IMODE(scratch.parent.stat().st_mode) == 0o700


def test_missing_configured_home_is_never_created(tmp_path: Path) -> None:
    parent = tmp_path.resolve() / "operator-parent"
    with pytest.raises(ProfileDirectoryError, match="does not exist"):
        resolve_scratch(environment={APGR_HOME_ENVIRONMENT: str(parent / "apgr")})
    assert not parent.exists()


def test_default_never_repairs_existing_unsafe_directory(secure_home: Path) -> None:
    scratch = secure_home / ".apgr" / "scratch"
    scratch.mkdir(parents=True, mode=0o777)
    scratch.chmod(0o777)
    with pytest.raises(ProfileDirectoryError, match="unsafe permissions"):
        resolve_scratch(environment={}, home=secure_home)
    assert stat.S_IMODE(scratch.stat().st_mode) == 0o777


@pytest.mark.parametrize("value", ["", " ", "relative", "${HOME}/scratch", "~/scratch"])
def test_configured_home_does_not_expand_shell_syntax(value: str) -> None:
    with pytest.raises(ProfileDirectoryError):
        resolve_scratch(environment={APGR_HOME_ENVIRONMENT: value})


def test_scratch_refuses_parent_traversal(secure_scratch: Path) -> None:
    with pytest.raises(ProfileDirectoryError, match="direct"):
        resolve_scratch(environment={
            APGR_SCRATCH_OVERRIDE_ENVIRONMENT: str(secure_scratch / ".." / secure_scratch.name),
        })


def test_scratch_requires_search_permission(secure_scratch: Path) -> None:
    secure_scratch.chmod(0o600)
    try:
        with pytest.raises(ProfileDirectoryError, match="accessible"):
            resolve_scratch(environment={APGR_SCRATCH_OVERRIDE_ENVIRONMENT: str(secure_scratch)})
    finally:
        secure_scratch.chmod(0o700)


def test_default_scratch_existing_validated(tmp_path: Path) -> None:
    apgr_home = tmp_path.resolve() / "existing_apgr_home"
    scratch = apgr_home / "scratch"
    scratch.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(scratch, 0o700)

    env = {APGR_HOME_ENVIRONMENT: str(apgr_home)}
    resolved = resolve_scratch(environment=env)
    assert resolved == scratch


def test_default_scratch_relative_apgr_home() -> None:
    env = {APGR_HOME_ENVIRONMENT: "relative/apgr"}
    with pytest.raises(ProfileDirectoryError, match="must be an absolute path"):
        resolve_scratch(environment=env)


def test_default_scratch_unsafe_ancestor_symlink(tmp_path: Path) -> None:
    real_parent = tmp_path.resolve() / "apgr_real_parent"
    real_parent.mkdir(mode=0o700, exist_ok=True)
    link_parent = tmp_path.resolve() / "apgr_link_parent"
    link_parent.symlink_to(real_parent)

    (real_parent / "apgr_home").mkdir(mode=0o700)
    apgr_home = link_parent / "apgr_home"
    env = {APGR_HOME_ENVIRONMENT: str(apgr_home)}
    with pytest.raises(ProfileDirectoryError, match="symlink"):
        resolve_scratch(environment=env)


# --- Group 5: Multi-token profile directories resolution ---


def test_resolve_profile_directories_empty() -> None:
    assert resolve_profile_directories([]) == []


def test_resolve_profile_directories_scratch_only(
    secure_scratch: Path,
) -> None:
    env = {APGR_SCRATCH_OVERRIDE_ENVIRONMENT: str(secure_scratch)}
    resolved = resolve_profile_directories(["scratch"], environment=env)
    assert resolved == [secure_scratch]


def test_resolve_profile_directories_user_home_and_scratch(
    secure_home: Path, secure_scratch: Path
) -> None:
    env = {APGR_SCRATCH_OVERRIDE_ENVIRONMENT: str(secure_scratch)}
    resolved = resolve_profile_directories(
        ["user-home", "scratch"], environment=env, home=secure_home
    )
    assert resolved == [secure_home, secure_scratch]


def test_resolve_profile_directories_unsupported_token() -> None:
    with pytest.raises(ProfileDirectoryError, match="unsupported directory token"):
        resolve_profile_directories(["user-home", "bogus"])


# --- Group 6: Profile contracts and JSON profile files ---


def test_profile_contracts_tokens_aligned() -> None:
    expected_tokens = {
        "architecture-docs-primary": ["scratch"],
        "fable-architecture-docs-primary": ["scratch"],
        "normal-sysadmin-plan-review": ["user-home", "scratch"],
        "sysadmin-opus-review": ["user-home", "scratch"],
        "sysadmin-primary": ["user-home", "scratch"],
        "sysadmin-review": ["user-home", "scratch"],
    }
    for name, tokens in expected_tokens.items():
        contract = launcher.PROFILE_CONTRACTS[name]
        assert contract.additional_directories == tokens


def test_load_all_claude_profiles_succeeds() -> None:
    claude_root = Path(__file__).resolve().parents[3] / "claude"
    for profile_name in launcher.SUPPORTED_PROFILES:
        loaded = launcher.load_profile(claude_root, profile_name)
        assert isinstance(loaded, dict)
        contract = launcher.PROFILE_CONTRACTS[profile_name]
        if contract.additional_directories is not None:
            assert loaded["additionalDirectories"] == contract.additional_directories
        else:
            assert "additionalDirectories" not in loaded


def test_profile_json_files_have_no_forbidden_strings() -> None:
    claude_root = Path(__file__).resolve().parents[3] / "claude"
    profiles_dir = claude_root / "profiles"
    for json_file in profiles_dir.glob("*.json"):
        content = json_file.read_text(encoding="utf-8")
        # Forbidden substring checks without literal forbidden tokens
        users_forbidden = "/" + "Users" + "/"
        file_forbidden = "file" + ":///"
        assert users_forbidden not in content, f"Found forbidden substring in {json_file}"
        assert file_forbidden not in content, f"Found forbidden substring in {json_file}"


# --- Group 7: Claude launch() argv and error behavior ---


@pytest.mark.parametrize("profile_name", [
    "architecture-docs-primary", "fable-architecture-docs-primary",
    "normal-sysadmin-plan-review", "sysadmin-primary", "sysadmin-review",
    "sysadmin-opus-review",
])
def test_launch_argv_includes_resolved_add_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, profile_name: str,
) -> None:
    home = tmp_path.resolve() / "test_home"
    home.mkdir(mode=0o700, exist_ok=True)
    scratch = tmp_path.resolve() / "test_scratch"
    scratch.mkdir(mode=0o700, exist_ok=True)

    root = Path(__file__).resolve().parents[3]
    claude_root = root / "claude"

    fake_settings = tmp_path.resolve() / "settings.json"
    fake_settings.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(launcher, "canonical_settings_path", lambda root: fake_settings)

    monkeypatch.setattr(launcher.shutil, "which", lambda name: "/fixture/claude")
    monkeypatch.setattr(
        catalog, "probe_claude_version", lambda executable: ("2.1.999", "available")
    )
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv(APGR_SCRATCH_OVERRIDE_ENVIRONMENT, str(scratch))

    calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(launcher.os, "execve", lambda *args: calls.append(args))

    monkeypatch.delenv(launcher.WORKER_FACADE_MARKER, raising=False)
    launcher.launch(claude_root, profile_name, ["--print", "hello"])
    assert len(calls) == 1
    argv = calls[0][1]
    assert isinstance(argv, list)
    contract = launcher.PROFILE_CONTRACTS[profile_name]
    add_dirs = [argv[i + 1] for i, arg in enumerate(argv) if arg == "--add-dir"]
    assert add_dirs == ([str(home), str(scratch)] if contract.isolated_settings else [str(scratch)])
    assert argv[argv.index("--effort") + 1] == "high"
    assert argv[argv.index("--permission-mode") + 1] == contract.permission_mode
    assert argv[argv.index("--model") + 1] == launcher.resolve_profile(claude_root, profile_name).resolved_model_id
    if contract.isolated_settings:
        assert argv[argv.index("--settings") + 1] == str(fake_settings)
        assert argv[argv.index("--setting-sources") + 1] == ""
    if contract.permission_mode == "plan":
        assert "--strict-mcp-config" in argv
        assert "--no-chrome" in argv


def test_launch_fails_on_missing_scratch_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = tmp_path.resolve() / "nonexistent_override"
    root = Path(__file__).resolve().parents[3]
    claude_root = root / "claude"

    monkeypatch.setattr(launcher.shutil, "which", lambda name: "/fixture/claude")
    monkeypatch.setattr(
        catalog, "probe_claude_version", lambda executable: ("2.1.999", "available")
    )
    monkeypatch.setenv(APGR_SCRATCH_OVERRIDE_ENVIRONMENT, str(missing))

    with pytest.raises(launcher.ProfileError, match="does not exist"):
        launcher.launch(claude_root, "architecture-docs-primary", ["--print", "test"])
    assert not missing.exists()


def test_launch_fails_on_symlink_scratch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_scratch = tmp_path.resolve() / "real_scratch"
    real_scratch.mkdir(mode=0o700, exist_ok=True)
    symlink_scratch = tmp_path.resolve() / "symlink_scratch"
    symlink_scratch.symlink_to(real_scratch)

    root = Path(__file__).resolve().parents[3]
    claude_root = root / "claude"

    monkeypatch.setattr(launcher.shutil, "which", lambda name: "/fixture/claude")
    monkeypatch.setattr(
        catalog, "probe_claude_version", lambda executable: ("2.1.999", "available")
    )
    monkeypatch.setenv(APGR_SCRATCH_OVERRIDE_ENVIRONMENT, str(symlink_scratch))

    with pytest.raises(launcher.ProfileError, match="symlink"):
        launcher.launch(claude_root, "architecture-docs-primary", ["--print", "test"])


def test_launch_rejects_add_dir_command_line_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = Path(__file__).resolve().parents[3]
    claude_root = root / "claude"

    with pytest.raises(launcher.ProfileError, match="cannot be overridden: --add-dir"):
        launcher.launch(
            claude_root, "sysadmin-primary", ["--add-dir", "/custom", "--print", "test"]
        )
