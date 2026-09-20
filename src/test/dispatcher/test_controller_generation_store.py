"""Tests for controller generation storage, materialization, and process identity."""

from __future__ import annotations

import os
import stat
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import pytest

# Ensure libexec is in Python path
if str(Path(__file__).resolve().parents[3] / "libexec") not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "libexec"))

from controller_generation_process import (
    _process_identity_linux,
    current_process_identity,
    process_identity,
    verify_process_identity,
)
from controller_generation_store import (
    SCHEMA_GENERATION,
    GenerationLimitError,
    GenerationSecurityError,
    GenerationValidationError,
    StoreLockTimeoutError,
    StoreSecurityError,
    _safe_remove_tree,
    canonical_root_sha256,
    coordinate,
    materialize,
    resolve_controller_dir,
    validate_generation,
)


@pytest.fixture
def scratch_dir(tmp_path: Path):
    """Create an isolated direct directory beneath the test-owned temp root."""
    child = tmp_path.resolve() / "generation-store"
    child.mkdir(mode=0o700)
    try:
        yield child
    finally:
        _safe_remove_tree(child)


def _init_git_repo(path: Path) -> Path:
    """Initialize a clean disposable git repository at path."""
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "tester@example.invalid"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test Runner"], cwd=path, check=True)
    return path


def _git_commit_all(path: Path, msg: str = "commit") -> str:
    """Stage and commit all changes in repository, returning commit SHA."""
    subprocess.run(["git", "add", "-A"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-qm", msg], cwd=path, check=True)
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path).decode().strip()


# ---------------------------------------------------------------------------
# Process Identity Tests
# ---------------------------------------------------------------------------

def test_process_identity_current() -> None:
    ident = current_process_identity()
    assert ident is not None
    assert isinstance(ident, str)
    assert verify_process_identity(os.getpid(), ident) is True

    if sys.platform == "darwin":
        parts = ident.split(":")
        assert len(parts) == 3
        pid_str, sec_str, usec_str = parts
        assert pid_str == str(os.getpid())
        assert int(sec_str) > 0
        assert int(usec_str) >= 0


def test_process_identity_invalid_and_dead_pid() -> None:
    assert process_identity(99_999_999) is None
    assert process_identity(-1) is None
    assert process_identity(0) is None
    assert process_identity(cast(Any, "invalid")) is None
    assert verify_process_identity(os.getpid(), "non-matching-ident") is False


def test_process_identity_linux_parser(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    boot_id_file = tmp_path / "boot_id"
    boot_id_file.write_text("fake-boot-uuid-12345\n", encoding="utf-8")

    stat_file = tmp_path / "stat"
    # Tricky process comm containing spaces and parens
    # 22nd field (1-based) is index 19 after the last paren
    # fields after ') ':
    # 1: S (state)
    # ...
    # 20: 543210 (starttime)
    rest_fields = ["S"] + [str(i) for i in range(4, 22)] + ["543210", "other"]
    stat_file.write_text(f"1234 (bash (subshell)) {' '.join(rest_fields)}\n", encoding="utf-8")

    monkeypatch.setattr(
        "controller_generation_process.Path",
        lambda p: (
            boot_id_file if "boot_id" in str(p)
            else stat_file if "stat" in str(p)
            else Path(p)
        ),
    )

    ident = _process_identity_linux(1234)
    assert ident == "1234:fake-boot-uuid-12345:543210"


# ---------------------------------------------------------------------------
# Coordination & Locking Tests
# ---------------------------------------------------------------------------

def test_coordinate_creates_store_and_lock(scratch_dir: Path) -> None:
    repo = _init_git_repo(scratch_dir / "repo")
    (repo / "bin").mkdir()
    (repo / "bin" / "agent-cmd").write_text("#!/bin/sh\nexit 0\n")
    os.chmod(repo / "bin" / "agent-cmd", 0o700)
    _git_commit_all(repo)

    store_base = scratch_dir / "custom_store"
    with coordinate(repo, store=store_base) as cdir:
        assert cdir == store_base
        assert cdir.is_dir()
        st = os.lstat(cdir)
        assert stat.S_IMODE(st.st_mode) == 0o700
        assert st.st_uid == os.getuid()

        lock_path = cdir / ".lock"
        assert lock_path.is_file()
        st_lock = os.lstat(lock_path)
        assert stat.S_IMODE(st_lock.st_mode) == 0o600
        assert st_lock.st_uid == os.getuid()


def test_coordinate_env_base_override(monkeypatch: pytest.MonkeyPatch, scratch_dir: Path) -> None:
    repo = _init_git_repo(scratch_dir / "repo")
    store_base = scratch_dir / "env_store_base"
    monkeypatch.delenv("APGR_GENERATION_STORE", raising=False)
    monkeypatch.setenv("AGENT_CENTRAL_GENERATION_STORE", str(store_base))

    with coordinate(repo) as cdir:
        expected_digest = canonical_root_sha256(repo)
        assert cdir == store_base / expected_digest
        assert cdir.is_dir()


def test_coordinate_apgr_generation_store_override_wins(monkeypatch: pytest.MonkeyPatch, scratch_dir: Path) -> None:
    repo = _init_git_repo(scratch_dir / "repo")
    store_base = scratch_dir / "apgr_store_base"
    legacy_base = scratch_dir / "legacy_store_base"
    monkeypatch.setenv("AGENT_CENTRAL_GENERATION_STORE", str(legacy_base))
    monkeypatch.setenv("APGR_GENERATION_STORE", str(store_base))

    with coordinate(repo) as cdir:
        expected_digest = canonical_root_sha256(repo)
        assert cdir == store_base / expected_digest
        assert cdir.is_dir()


def test_resolve_controller_dir_legacy_readback_rule(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path / "repo")
    digest = canonical_root_sha256(repo)

    fake_home = tmp_path / "home"
    fake_legacy_base = fake_home / ".local/state/agent-central/generations"
    fake_legacy_dir = fake_legacy_base / digest
    fake_legacy_dir.mkdir(parents=True, mode=0o700)

    monkeypatch.delenv("APGR_GENERATION_STORE", raising=False)
    monkeypatch.delenv("AGENT_CENTRAL_GENERATION_STORE", raising=False)
    monkeypatch.delenv("APGR_HOME", raising=False)
    monkeypatch.setenv("HOME", str(fake_home))

    # With default home (~/.apgr), legacy dir exists and target (~/.apgr/generations/<digest>) does not
    res = resolve_controller_dir(repo)
    assert res == fake_legacy_dir

    # When target exists, target wins
    target_dir = fake_home / ".apgr/generations" / digest
    target_dir.mkdir(parents=True, mode=0o700)
    assert resolve_controller_dir(repo) == target_dir

    # With explicitly relocated home (APGR_HOME), legacy is NEVER checked even if target does not exist
    relocated_home = tmp_path / "relocated_home"
    monkeypatch.setenv("APGR_HOME", str(relocated_home))
    relocated_target = relocated_home / "generations" / digest
    assert resolve_controller_dir(repo) == relocated_target


def test_coordinate_rejects_symlink_dir(scratch_dir: Path) -> None:
    repo = _init_git_repo(scratch_dir / "repo")
    target_dir = scratch_dir / "real_dir"
    target_dir.mkdir(mode=0o700)
    link_dir = scratch_dir / "link_store"
    link_dir.symlink_to(target_dir)

    with pytest.raises(StoreSecurityError, match="is a symlink"), coordinate(repo, store=link_dir):
        pass


def test_coordinate_rejects_group_world_writable_dir(
    scratch_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _init_git_repo(scratch_dir / "repo")
    store_dir = scratch_dir / "insecure_store"
    store_dir.mkdir(mode=0o700)
    orig_lstat = Path.lstat
    monkeypatch.setattr(
        Path,
        "lstat",
        lambda p: (
            os.stat_result((stat.S_IFDIR | 0o777, *orig_lstat(p)[1:]))
            if p == store_dir
            else orig_lstat(p)
        ),
    )

    with pytest.raises(StoreSecurityError, match="group/world writable"), coordinate(repo, store=store_dir):
        pass


def test_coordinate_rejects_symlink_lock_file(scratch_dir: Path) -> None:
    repo = _init_git_repo(scratch_dir / "repo")
    store_dir = scratch_dir / "store_with_bad_lock"
    store_dir.mkdir(mode=0o700)
    dummy_target = scratch_dir / "dummy"
    dummy_target.touch()
    (store_dir / ".lock").symlink_to(dummy_target)

    with pytest.raises(StoreSecurityError, match="symlink"), coordinate(repo, store=store_dir):
        pass


def test_coordinate_flock_concurrency_timeout(scratch_dir: Path) -> None:
    repo = _init_git_repo(scratch_dir / "repo")
    store_dir = scratch_dir / "lock_test_store"

    barrier_acquired = threading.Event()
    barrier_release = threading.Event()

    def lock_holder():
        with coordinate(repo, store=store_dir, timeout=5.0):
            barrier_acquired.set()
            barrier_release.wait(timeout=5.0)

    t = threading.Thread(target=lock_holder)
    t.start()
    assert barrier_acquired.wait(timeout=5.0)

    try:
        # Attempt to acquire while held, with a short timeout
        with pytest.raises(StoreLockTimeoutError, match="Timed out"), coordinate(repo, store=store_dir, timeout=0.2):
            pass
    finally:
        barrier_release.set()
        t.join(timeout=5.0)

    # After release, acquisition succeeds
    with coordinate(repo, store=store_dir, timeout=2.0) as cdir:
        assert cdir.is_dir()


# ---------------------------------------------------------------------------
# Materialization & Allowlist Tests
# ---------------------------------------------------------------------------

def test_materialize_git_objects_allowlist_and_schema(scratch_dir: Path) -> None:
    repo = _init_git_repo(scratch_dir / "repo")

    # Allowlisted files
    (repo / "bin").mkdir()
    (repo / "bin" / "agent-cmd").write_text("#!/bin/sh\necho cmd\n")
    os.chmod(repo / "bin" / "agent-cmd", 0o700)

    (repo / "libexec").mkdir()
    (repo / "libexec" / "worker.py").write_text("print('worker')\n")

    (repo / "codex").mkdir()
    (repo / "codex" / "AGENTS.md").write_text("# Codex Agents\n")

    (repo / "claude").mkdir()
    (repo / "claude" / "CLAUDE.md").write_text("# Claude Guidance\n")
    (repo / "claude" / "model-catalog-v1.json").write_text('{"models": []}\n')
    (repo / "claude" / "instruction-fragments-v1.json").write_text('{"fragments": []}\n')

    (repo / "antigravity" / "profiles").mkdir(parents=True)
    (repo / "antigravity" / "profiles" / "default.json").write_text('{"profile": "agy"}\n')

    (repo / "tools").mkdir()
    (repo / "tools" / "add_dispatcher_roster_operator_directions.py").write_text("#!/usr/bin/env python3\n")
    os.chmod(repo / "tools" / "add_dispatcher_roster_operator_directions.py", 0o700)

    # Non-allowlisted files
    (repo / "README.md").write_text("# Top Readme\n")
    (repo / "src").mkdir()
    (repo / "src" / "app.py").write_text("print('not allowlisted')\n")
    (repo / "tools" / "unwanted.py").write_text("print('unwanted')\n")

    commit = _git_commit_all(repo, "initial allowlist commit")
    ctrl_dir = scratch_dir / "ctrl"

    record = materialize(repo, ctrl_dir, commit)

    assert record["schema"] == SCHEMA_GENERATION
    assert record["commit"] == commit
    assert record["safety_established"] is True
    assert record["controller_root"] == str(repo.resolve())

    gen_root = Path(record["generation_root"])
    assert gen_root == (ctrl_dir / "objects" / commit).resolve()
    assert gen_root.is_dir()

    # Verify allowlisted files are present
    assert (gen_root / "bin" / "agent-cmd").is_file()
    assert (gen_root / "libexec" / "worker.py").is_file()
    assert (gen_root / "codex" / "AGENTS.md").is_file()
    assert (gen_root / "claude" / "CLAUDE.md").is_file()
    assert (gen_root / "claude" / "model-catalog-v1.json").is_file()
    assert (gen_root / "claude" / "instruction-fragments-v1.json").is_file()
    assert (gen_root / "antigravity" / "profiles" / "default.json").is_file()
    assert (gen_root / "tools" / "add_dispatcher_roster_operator_directions.py").is_file()

    # Verify non-allowlisted files are NOT present
    assert (gen_root / "README.md").exists()  # provider-free roster smoke checks it
    assert not (gen_root / "src").exists()
    assert not (gen_root / "tools" / "unwanted.py").exists()

    # Verify immutable read-only permissions
    # Executable: 0o500
    st_bin = os.lstat(gen_root / "bin" / "agent-cmd")
    assert stat.S_IMODE(st_bin.st_mode) == 0o500
    st_tool = os.lstat(gen_root / "tools" / "add_dispatcher_roster_operator_directions.py")
    assert stat.S_IMODE(st_tool.st_mode) == 0o500

    # Regular files: 0o400
    st_lib = os.lstat(gen_root / "libexec" / "worker.py")
    assert stat.S_IMODE(st_lib.st_mode) == 0o400

    # Directories: 0o500
    st_dir = os.lstat(gen_root / "bin")
    assert stat.S_IMODE(st_dir.st_mode) == 0o500
    st_gen = os.lstat(gen_root)
    assert stat.S_IMODE(st_gen.st_mode) == 0o500

    # Writing inside generation root is rejected by OS
    with pytest.raises(PermissionError):
        (gen_root / "bin" / "injected.txt").write_text("fail")

    # Metadata is outside payload
    manifest_path = ctrl_dir / "manifests" / f"{commit}.json"
    record_path = ctrl_dir / "records" / f"{commit}.json"
    assert manifest_path.is_file()
    assert record_path.is_file()
    assert not (gen_root / "manifests").exists()
    assert not (gen_root / "records").exists()


def test_materialize_rejects_git_symlink(scratch_dir: Path) -> None:
    repo = _init_git_repo(scratch_dir / "repo")
    (repo / "bin").mkdir()
    target = repo / "bin" / "target.sh"
    target.write_text("#!/bin/sh\nexit 0\n")
    symlink = repo / "bin" / "symlink.sh"
    symlink.symlink_to(target.name)
    _git_commit_all(repo)

    ctrl_dir = scratch_dir / "ctrl"
    with pytest.raises(GenerationSecurityError, match="Symlink"):
        materialize(repo, ctrl_dir)


def test_materialize_rejects_credentials(scratch_dir: Path) -> None:
    for bad_file in ("bin/.env", "libexec/secret.key", "libexec/id_rsa", "bin/api_token.txt"):
        repo = _init_git_repo(scratch_dir / f"repo-{uuid4().hex}")
        bad_path = repo / bad_file
        bad_path.parent.mkdir(parents=True, exist_ok=True)
        bad_path.write_text("secret-data\n")
        _git_commit_all(repo)

        ctrl_dir = scratch_dir / f"ctrl-{uuid4().hex}"
        with pytest.raises(GenerationSecurityError):
            materialize(repo, ctrl_dir)


def test_materialize_rejects_ambient_settings(scratch_dir: Path) -> None:
    for bad_file in ("libexec/settings.json", "bin/claude_desktop_config.json", "bin/config.toml"):
        repo = _init_git_repo(scratch_dir / f"repo-{uuid4().hex}")
        bad_path = repo / bad_file
        bad_path.parent.mkdir(parents=True, exist_ok=True)
        bad_path.write_text('{"ambient": true}\n')
        _git_commit_all(repo)

        ctrl_dir = scratch_dir / f"ctrl-{uuid4().hex}"
        with pytest.raises(GenerationSecurityError):
            materialize(repo, ctrl_dir)


def test_materialize_rejects_cache_files(scratch_dir: Path) -> None:
    for bad_file in ("libexec/__pycache__/mod.pyc", "bin/.DS_Store", "libexec/test.pyc"):
        repo = _init_git_repo(scratch_dir / f"repo-{uuid4().hex}")
        bad_path = repo / bad_file
        bad_path.parent.mkdir(parents=True, exist_ok=True)
        bad_path.write_bytes(b"cache-content")
        _git_commit_all(repo)

        ctrl_dir = scratch_dir / f"ctrl-{uuid4().hex}"
        with pytest.raises(GenerationSecurityError):
            materialize(repo, ctrl_dir)


def test_materialize_rejects_user_canon(scratch_dir: Path) -> None:
    repo = _init_git_repo(scratch_dir / "repo")
    bad_path = repo / "common" / "workers" / "user-canon" / "notes.txt"
    bad_path.parent.mkdir(parents=True, exist_ok=True)
    bad_path.write_text("private user canon notes\n")
    _git_commit_all(repo)

    ctrl_dir = scratch_dir / "ctrl"
    with pytest.raises(GenerationSecurityError, match="[Uu]ser canon"):
        materialize(repo, ctrl_dir)


def test_materialize_rejects_file_size_limit(monkeypatch: pytest.MonkeyPatch, scratch_dir: Path) -> None:
    repo = _init_git_repo(scratch_dir / "repo")
    (repo / "bin").mkdir()
    (repo / "bin" / "large.sh").write_text("large file content\n")
    _git_commit_all(repo)

    monkeypatch.setattr("controller_generation_store.MAX_SINGLE_FILE_BYTES", 5)
    ctrl_dir = scratch_dir / "ctrl"
    with pytest.raises(GenerationLimitError, match="exceeds limit"):
        materialize(repo, ctrl_dir)


# ---------------------------------------------------------------------------
# Validation & Tamper Resistance Tests
# ---------------------------------------------------------------------------

def _setup_test_generation(scratch_dir: Path) -> tuple[Path, Path, dict[str, Any]]:
    repo = _init_git_repo(scratch_dir / f"repo-{uuid4().hex}")
    (repo / "bin").mkdir()
    (repo / "bin" / "run.sh").write_text("#!/bin/sh\necho running\n")
    os.chmod(repo / "bin" / "run.sh", 0o700)

    (repo / "libexec").mkdir()
    (repo / "libexec" / "helper.py").write_text("HELPER = True\n")

    _git_commit_all(repo)
    ctrl_dir = scratch_dir / f"ctrl-{uuid4().hex}"
    record = materialize(repo, ctrl_dir)
    return repo, ctrl_dir, record


def test_validate_generation_success(scratch_dir: Path) -> None:
    _, ctrl_dir, record = _setup_test_generation(scratch_dir)
    assert validate_generation(record, ctrl_dir) is True


def test_validate_generation_detects_tampered_content(scratch_dir: Path) -> None:
    _, ctrl_dir, record = _setup_test_generation(scratch_dir)
    gen_root = Path(record["generation_root"])
    target = gen_root / "libexec" / "helper.py"

    # Exact-size tamper: original is "HELPER = True\n" (14 bytes)
    # Tampered is "HELPER = Fals\n" (14 bytes) -> triggers Content hash mismatch
    os.chmod(target.parent, 0o700)
    os.chmod(target, 0o600)
    target.write_text("HELPER = Fals\n")
    os.chmod(target, 0o400)
    os.chmod(target.parent, 0o500)

    with pytest.raises(GenerationValidationError, match="Content"):
        validate_generation(record, ctrl_dir)


def test_validate_generation_detects_tampered_size(scratch_dir: Path) -> None:
    _, ctrl_dir, record = _setup_test_generation(scratch_dir)
    gen_root = Path(record["generation_root"])
    target = gen_root / "libexec" / "helper.py"

    # Changed-size tamper
    os.chmod(target.parent, 0o700)
    os.chmod(target, 0o600)
    target.write_text("HELPER = True; EXTRA = True\n")
    os.chmod(target, 0o400)
    os.chmod(target.parent, 0o500)

    with pytest.raises(GenerationValidationError, match="Size mismatch"):
        validate_generation(record, ctrl_dir)


def test_validate_generation_detects_tampered_mode(
    scratch_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, ctrl_dir, record = _setup_test_generation(scratch_dir)
    gen_root = Path(record["generation_root"])
    target = gen_root / "libexec" / "helper.py"

    orig_lstat = Path.lstat
    monkeypatch.setattr(
        Path,
        "lstat",
        lambda p: (
            os.stat_result((stat.S_IFREG | 0o777, *orig_lstat(p)[1:]))
            if p == target
            else orig_lstat(p)
        ),
    )

    with pytest.raises(GenerationValidationError, match="Mode mismatch"):
        validate_generation(record, ctrl_dir)


def test_validate_generation_detects_added_file_bytecode_prevention(scratch_dir: Path) -> None:
    _, ctrl_dir, record = _setup_test_generation(scratch_dir)
    gen_root = Path(record["generation_root"])

    # Simulate bytecode or rogue injected file
    os.chmod(gen_root / "libexec", 0o700)
    injected = gen_root / "libexec" / "helper.pyc"
    injected.write_bytes(b"pyc bytecode")
    os.chmod(injected, 0o400)
    os.chmod(gen_root / "libexec", 0o500)

    with pytest.raises(GenerationValidationError, match="Unauthorized file"):
        validate_generation(record, ctrl_dir)


def test_validate_generation_detects_added_symlink(scratch_dir: Path) -> None:
    _, ctrl_dir, record = _setup_test_generation(scratch_dir)
    gen_root = Path(record["generation_root"])

    os.chmod(gen_root / "bin", 0o700)
    link = gen_root / "bin" / "bad_link"
    link.symlink_to(gen_root / "bin" / "run.sh")
    os.chmod(gen_root / "bin", 0o500)

    with pytest.raises(GenerationValidationError, match="Symlink"):
        validate_generation(record, ctrl_dir)


def test_validate_generation_detects_manifest_hash_tamper(scratch_dir: Path) -> None:
    _, ctrl_dir, record = _setup_test_generation(scratch_dir)
    manifest_path = ctrl_dir / "manifests" / f"{record['commit']}.json"

    os.chmod(manifest_path, 0o600)
    manifest_path.write_text('{"tampered": true}\n')
    os.chmod(manifest_path, 0o400)

    with pytest.raises(GenerationValidationError, match="Manifest hash mismatch"):
        validate_generation(record, ctrl_dir)


def test_validate_generation_detects_tree_binding_mismatch(scratch_dir: Path) -> None:
    _, ctrl_dir, record = _setup_test_generation(scratch_dir)
    tampered_record = dict(record)
    tampered_record["tree"] = "0" * 40

    with pytest.raises(GenerationValidationError, match="[Tt]ree mismatch"):
        validate_generation(tampered_record, ctrl_dir)


def test_generation_reuse_only_after_full_validation(scratch_dir: Path) -> None:
    repo, ctrl_dir, record1 = _setup_test_generation(scratch_dir)

    # Calling materialize again reuses validated generation without error
    record2 = materialize(repo, ctrl_dir, record1["commit"])
    assert record2["manifest_sha256"] == record1["manifest_sha256"]

    # Tamper with the generation root
    gen_root = Path(record1["generation_root"])
    target = gen_root / "bin" / "run.sh"
    os.chmod(target.parent, 0o700)
    os.chmod(target, 0o600)
    target.write_text("#!/bin/sh\necho tampered\n")
    os.chmod(target, 0o500)
    os.chmod(target.parent, 0o500)

    # Tampering blocks. Never replace bytes underneath another live lease.
    with pytest.raises(GenerationValidationError):
        materialize(repo, ctrl_dir, record1["commit"])
    assert "tampered" in target.read_text()


def test_materialize_and_validate_current_repo(scratch_dir: Path) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    ctrl_dir = scratch_dir / "real_repo_ctrl"
    with coordinate(repo_root, store=ctrl_dir) as cdir:
        record = materialize(repo_root, cdir)
        assert record["schema"] == SCHEMA_GENERATION
        assert record["safety_established"] is True
        assert validate_generation(record, cdir) is True


@pytest.mark.parametrize("platform,previous,observed,expected", [
    ("darwin", "42:100:5", "42:101:0", True),
    ("darwin", "42:100:5", "42:100:5", False),
    ("darwin", "42:101:0", "42:100:5", False),
    ("darwin", "42:100:1000000", "42:101:0", False),
    ("darwin", "41:100:5", "42:101:0", False),
    ("darwin", "invalid", "42:101:0", False),
    ("linux", "42:btime-100:5", "42:btime-100:6", True),
    ("linux", "42:btime-100:6", "42:btime-100:5", False),
    ("linux", "42:btime-100:6", "42:btime-101:1", True),
    ("linux", "42:btime-100:6", "42:btime-99:1", False),
    ("linux", "42:invalid:1", "42:btime-101:1", False),
    ("unknown", "42:100:5", "42:101:0", False),
])
def test_retirement_birth_order_is_conservative(monkeypatch, platform, previous, observed, expected):
    import controller_generation_process as processes
    monkeypatch.setattr(processes.sys, "platform", platform)
    assert processes.identity_supersedes(42, previous, observed) is expected


def test_controller_generation_bootstrap_active_precedence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from controller_generation_bootstrap import _active

    active_dir = tmp_path / "active"
    active_dir.mkdir()
    legacy_dir = tmp_path / "legacy"
    legacy_dir.mkdir()

    monkeypatch.setenv("AGENT_CENTRAL_ACTIVE_ROOT", str(legacy_dir))
    monkeypatch.setenv("APGR_ACTIVE_ROOT", str(active_dir))

    assert _active(active_dir) is True
    assert _active(legacy_dir) is False

    monkeypatch.delenv("APGR_ACTIVE_ROOT", raising=False)
    assert _active(legacy_dir) is True


def test_controller_generation_bootstrap_extract_apgr_home(tmp_path: Path) -> None:
    from controller_generation_bootstrap import _extract_apgr_home

    target = tmp_path / "valid_home"
    assert _extract_apgr_home(["dispatch", "--apgr-home", str(target)]) == target
    assert _extract_apgr_home(["dispatch", f"--apgr-home={target}"]) == target
    assert _extract_apgr_home(["dispatch", "--other", "flag"]) is None

    # Trailing flag fails closed
    with pytest.raises(ValueError, match="requires an argument"):
        _extract_apgr_home(["dispatch", "--apgr-home"])

    # Relative path fails
    with pytest.raises(ValueError, match="must be an absolute path"):
        _extract_apgr_home(["dispatch", "--apgr-home", "relative/path"])

    with pytest.raises(ValueError, match="must be an absolute path"):
        _extract_apgr_home(["dispatch", "--apgr-home=relative/path"])

    # Control characters fail
    with pytest.raises(ValueError, match="invalid or control characters"):
        _extract_apgr_home(["dispatch", "--apgr-home", "/path/with\ninvalid"])


def test_validate_generation_does_not_create_missing_directories(scratch_dir: Path) -> None:
    nonexistent = scratch_dir / "nonexistent_ctrl_dir"
    fake_record = {
        "schema": SCHEMA_GENERATION,
        "safety_established": True,
        "commit": "a" * 40,
        "generation_root": str(nonexistent / "objects" / ("a" * 40)),
        "controller_root": "/tmp/fake_root",
        "controller_id": "b" * 64,
        "tree": "c" * 40,
        "manifest_sha256": "d" * 64,
    }
    with pytest.raises(GenerationValidationError, match="generation store directory missing"):
        validate_generation(fake_record, nonexistent)
    # The nonexistent directory was not created by validate_generation
    assert not nonexistent.exists()


def test_legacy_readback_survives_new_store_coordination_and_bootstrap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import hashlib
    import json
    import os
    import sys
    from controller_generation_bootstrap import _resume_commit, enter, LEASE_ENV
    from controller_generation_store import coordinate, materialize, resolve_controller_dir

    repo = _init_git_repo(tmp_path / "ctrl_repo")
    (repo / "libexec").mkdir(parents=True, exist_ok=True)
    (repo / "libexec/controller_generation_bootstrap.py").write_text("# bootstrap stub\n", encoding="utf-8")
    (repo / "README.md").write_text("hello", encoding="utf-8")
    commit = _git_commit_all(repo, "initial")
    digest = canonical_root_sha256(repo)

    fake_home = tmp_path / "home"
    legacy_base = fake_home / ".local/state/agent-central/generations"
    legacy_dir = legacy_base / digest
    legacy_dir.mkdir(parents=True, mode=0o700)

    monkeypatch.delenv("APGR_GENERATION_STORE", raising=False)
    monkeypatch.delenv("AGENT_CENTRAL_GENERATION_STORE", raising=False)
    monkeypatch.delenv("APGR_HOME", raising=False)
    monkeypatch.setenv("HOME", str(fake_home))

    # Materialize generation into the legacy store
    legacy_record = materialize(repo, legacy_dir, commit=commit)
    assert (legacy_dir / "objects" / commit).is_dir()

    # Capture initial state of the legacy generation (files, digests, modes)
    def snapshot_dir(base: Path) -> dict[str, tuple[str, int]]:
        snap = {}
        for p in sorted(base.rglob("*")):
            rel = str(p.relative_to(base))
            if p.is_file():
                h = hashlib.sha256(p.read_bytes()).hexdigest()
            else:
                h = "DIR"
            snap[rel] = (h, p.stat().st_mode)
        return snap

    legacy_snapshot_before = snapshot_dir(legacy_dir)

    # Create a disposable prior run state.json referencing the legacy generation
    run_dir = tmp_path / "prior_run"
    run_dir.mkdir()
    state_file = run_dir / "state.json"
    state_file.write_text(json.dumps({
        "schema": "agent-phase-state-v1",
        "controller_generation": legacy_record,
    }), encoding="utf-8")

    # Before startup, new target store does not exist
    target_dir = fake_home / ".apgr/generations" / digest
    assert not target_dir.exists()
    assert resolve_controller_dir(repo, lookup_only=True) == legacy_dir

    # A newly created current-store directory (empty, before objects exist) must NOT mask legacy record
    target_dir.mkdir(parents=True, mode=0o700)
    assert target_dir.exists()
    assert not (target_dir / "objects").exists()
    assert resolve_controller_dir(repo, lookup_only=True) == legacy_dir
    found_commit_early = _resume_commit(["--resume", str(run_dir)], repo)
    assert found_commit_early == commit

    # Intercept os.execve in enter()
    execve_calls = []

    def mock_execve(executable: str, args: list[str], env: dict[str, str]) -> None:
        execve_calls.append((executable, args, env))

    monkeypatch.setattr(os, "execve", mock_execve)
    monkeypatch.setattr(sys, "argv", ["agent-phase-dispatch", "dispatch", "--resume", str(run_dir)])

    # Run the native startup sequence through enter()
    enter(repo)

    # 1. Verify bootstrap succeeded and invoked execve
    assert len(execve_calls) == 1
    _exec, _args, _env = execve_calls[0]
    lease_path = Path(_env[LEASE_ENV])
    # Coordination lease MUST be in the new store, not legacy store
    assert str(target_dir) in str(lease_path)
    assert str(legacy_dir) not in str(lease_path)

    # 2. Verify legacy bytes, modes, and directory membership are 100% unchanged
    legacy_snapshot_after = snapshot_dir(legacy_dir)
    assert legacy_snapshot_before == legacy_snapshot_after
    assert not (legacy_dir / "leases").exists()
    assert not (legacy_dir / ".lock").exists()

    # 3. Verify new writable coordination stayed isolated in the new selected store
    assert target_dir.is_dir()
    assert (target_dir / "leases").is_dir()
    assert (target_dir / "objects" / commit).is_dir()

    # 4. Verify relocated home does not search default legacy state
    relocated_home = tmp_path / "relocated_home"
    relocated_target = relocated_home / "generations" / digest
    monkeypatch.setenv("APGR_HOME", str(relocated_home))
    assert resolve_controller_dir(repo, lookup_only=True) == relocated_target


def test_generation_store_precedence_and_empty_suppression(
    monkeypatch: pytest.MonkeyPatch, scratch_dir: Path, tmp_path: Path
) -> None:
    repo = _init_git_repo(scratch_dir / "repo")
    digest = canonical_root_sha256(repo)

    explicit_store = scratch_dir / "explicit_store"
    apgr_base = scratch_dir / "apgr_base"
    legacy_base = scratch_dir / "legacy_base"
    fake_home = tmp_path / "fake_home"

    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.delenv("APGR_HOME", raising=False)

    # 1. Explicit store parameter wins over APGR_GENERATION_STORE and AGENT_CENTRAL_GENERATION_STORE
    monkeypatch.setenv("APGR_GENERATION_STORE", str(apgr_base))
    monkeypatch.setenv("AGENT_CENTRAL_GENERATION_STORE", str(legacy_base))
    assert resolve_controller_dir(repo, store=explicit_store) == explicit_store

    # 2. When store is None, APGR_GENERATION_STORE wins over AGENT_CENTRAL_GENERATION_STORE
    assert resolve_controller_dir(repo) == apgr_base / digest

    # 3. Present empty APGR_GENERATION_STORE suppresses legacy AGENT_CENTRAL_GENERATION_STORE and selects default
    monkeypatch.setenv("APGR_GENERATION_STORE", "")
    target_default = fake_home / ".apgr/generations" / digest
    assert resolve_controller_dir(repo, lookup_only=False) == target_default

    # Coordinate with present empty APGR_GENERATION_STORE writes to default store, not legacy
    with coordinate(repo) as cdir:
        assert cdir == target_default
        assert cdir.is_dir()
        assert not (legacy_base / digest).exists()

    # 4. When APGR_GENERATION_STORE key is absent, AGENT_CENTRAL_GENERATION_STORE is selected
    # and legacy alias writes are allowed via coordinate
    monkeypatch.delenv("APGR_GENERATION_STORE", raising=False)
    legacy_expected = legacy_base / digest
    assert resolve_controller_dir(repo, lookup_only=False) == legacy_expected

    with coordinate(repo) as cdir:
        assert cdir == legacy_expected
        assert cdir.is_dir()
        assert (cdir / ".lock").is_file()


def test_controller_generation_bootstrap_active_empty_suppresses_legacy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from controller_generation_bootstrap import _active

    legacy_dir = tmp_path / "legacy_active"
    legacy_dir.mkdir()

    monkeypatch.setenv("AGENT_CENTRAL_ACTIVE_ROOT", str(legacy_dir))
    monkeypatch.setenv("APGR_ACTIVE_ROOT", "")

    # Present empty APGR_ACTIVE_ROOT suppresses AGENT_CENTRAL_ACTIVE_ROOT
    assert _active(legacy_dir) is False

    # Default active root is selected instead
    default_root = Path.home() / ".local/nix-darwin/agentic-praxis-grimoire_dinas"
    assert _active(default_root) is True


def test_legacy_readback_existing_dir_precondition_and_lookup_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo = _init_git_repo(tmp_path / "repo")
    digest = canonical_root_sha256(repo)

    fake_home = tmp_path / "home"
    legacy_dir = fake_home / ".local/state/agent-central/generations" / digest
    target_dir = fake_home / ".apgr/generations" / digest

    monkeypatch.delenv("APGR_GENERATION_STORE", raising=False)
    monkeypatch.delenv("AGENT_CENTRAL_GENERATION_STORE", raising=False)
    monkeypatch.delenv("APGR_HOME", raising=False)
    monkeypatch.setenv("HOME", str(fake_home))

    # Precondition: legacy directory does not exist, so default returns target even for lookup_only
    assert not legacy_dir.exists()
    assert resolve_controller_dir(repo, lookup_only=True) == target_dir

    # When legacy directory exists, lookup_only selects legacy
    legacy_dir.mkdir(parents=True, mode=0o700)
    assert resolve_controller_dir(repo, lookup_only=True) == legacy_dir

    # But lookup_only=False (e.g. for coordinate/write) selects target
    assert resolve_controller_dir(repo, lookup_only=False) == target_dir

    # Coordinate creates lock only in target, never in legacy
    with coordinate(repo) as cdir:
        assert cdir == target_dir
        assert (target_dir / ".lock").is_file()
        assert not (legacy_dir / ".lock").exists()


def test_legacy_readback_commit_aware_and_no_merge_byte_mode_immutability(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import hashlib

    repo = _init_git_repo(tmp_path / "repo")
    (repo / "libexec").mkdir(parents=True, exist_ok=True)
    (repo / "libexec/controller_generation_bootstrap.py").write_text("# bootstrap\n", encoding="utf-8")
    (repo / "README.md").write_text("v1", encoding="utf-8")
    commit1 = _git_commit_all(repo, "commit1")
    digest = canonical_root_sha256(repo)

    fake_home = tmp_path / "home"
    legacy_dir = fake_home / ".local/state/agent-central/generations" / digest
    target_dir = fake_home / ".apgr/generations" / digest

    monkeypatch.delenv("APGR_GENERATION_STORE", raising=False)
    monkeypatch.delenv("AGENT_CENTRAL_GENERATION_STORE", raising=False)
    monkeypatch.delenv("APGR_HOME", raising=False)
    monkeypatch.setenv("HOME", str(fake_home))

    # Materialize commit1 into legacy store
    legacy_record1 = materialize(repo, legacy_dir, commit=commit1)
    assert (legacy_dir / "objects" / commit1).is_dir()

    # Capture initial snapshot of legacy directory (hashes and exact modes)
    def snapshot(base: Path) -> dict[str, tuple[str, int]]:
        result = {}
        for p in sorted(base.rglob("*")):
            rel = str(p.relative_to(base))
            if p.is_file():
                h = hashlib.sha256(p.read_bytes()).hexdigest()
            else:
                h = "DIR"
            result[rel] = (h, p.stat().st_mode)
        return result

    snap_before = snapshot(legacy_dir)

    # validate_generation succeeds via commit-aware resolution
    assert validate_generation(legacy_record1, legacy_dir) is True

    # Advance repository to commit2
    (repo / "README.md").write_text("v2", encoding="utf-8")
    commit2 = _git_commit_all(repo, "commit2")

    # Materialize commit2 into target store
    target_record2 = materialize(repo, target_dir, commit=commit2)
    assert (target_dir / "objects" / commit2).is_dir()

    # Verify commit-aware resolution:
    # commit1 resolves to legacy_dir (present in legacy, absent in target)
    assert resolve_controller_dir(repo, lookup_only=True, commit=commit1) == legacy_dir
    # commit2 resolves to target_dir (present in target)
    assert resolve_controller_dir(repo, lookup_only=True, commit=commit2) == target_dir

    # Track validate_generation commit-aware path
    assert validate_generation(legacy_record1, legacy_dir) is True
    assert validate_generation(target_record2, target_dir) is True

    # Verify NO merge occurred and legacy directory bytes and modes are 100% immutable
    snap_after = snapshot(legacy_dir)
    assert snap_before == snap_after

    # Verify isolation: commit2 is not in legacy, commit1 is not in target
    assert not (legacy_dir / "objects" / commit2).exists()
    assert not (target_dir / "objects" / commit1).exists()
    assert not (legacy_dir / ".lock").exists()
    assert not (legacy_dir / "leases").exists()
