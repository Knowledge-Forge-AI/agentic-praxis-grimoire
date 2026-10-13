"""Regression tests ensuring zero overly-permissive chmod operations in test fixtures.

Verifies the elimination of 13 CodeQL py/overly-permissive-file physical chmod
calls across dispatcher test suites via AST analysis and confirms fail-closed
security validation using synthetic stat/lstat metadata.
"""

from __future__ import annotations

import ast
import os
import stat
from pathlib import Path

import pytest
from claude_profile_directories import (
    APGR_SCRATCH_OVERRIDE_ENVIRONMENT,
    ProfileDirectoryError,
    resolve_scratch,
    resolve_user_home,
)
from controller_generation_store import (
    GenerationValidationError,
    StoreSecurityError,
    coordinate,
    validate_generation,
)
from test_controller_generation_store import (
    _init_git_repo,
    _setup_test_generation,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DISPATCHER_TEST_DIR = REPO_ROOT / "src" / "test" / "dispatcher"

TARGET_FILES = {
    "entry_adoption_boundary": DISPATCHER_TEST_DIR
    / "test_agent_phase_entry_adoption_boundary.py",
    "run_layout": DISPATCHER_TEST_DIR / "test_agent_phase_run_layout.py",
    "claude_profile_directories": DISPATCHER_TEST_DIR
    / "test_claude_profile_directories.py",
    "controller_generation_store": DISPATCHER_TEST_DIR
    / "test_controller_generation_store.py",
}


def _extract_chmod_calls(tree: ast.AST) -> list[tuple[int, int | None]]:
    """Return list of (line_number, mode_int) for all chmod calls in an AST."""
    results: list[tuple[int, int | None]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_chmod = False
        mode_val: int | None = None
        if isinstance(func, ast.Name) and func.id == "chmod" or isinstance(func, ast.Attribute) and func.attr == "chmod":
            is_chmod = True

        if not is_chmod:
            continue

        # Check keyword arguments first
        for kw in node.keywords:
            if (
                kw.arg == "mode"
                and isinstance(kw.value, ast.Constant)
                and isinstance(kw.value.value, int)
            ):
                mode_val = kw.value.value

        # Check positional arguments if not found
        if mode_val is None and node.args:
            is_os_call = isinstance(func, ast.Attribute) and isinstance(
                func.value, ast.Name
            ) and func.value.id == "os"
            idx = 1 if is_os_call else 0
            if (
                len(node.args) > idx
                and isinstance(node.args[idx], ast.Constant)
                and isinstance(node.args[idx].value, int)
            ):
                mode_val = node.args[idx].value

        results.append((node.lineno, mode_val))
    return results


def test_entry_adoption_boundary_has_no_physical_chmod() -> None:
    """Verify entry adoption boundary contains zero physical chmod calls."""
    path = TARGET_FILES["entry_adoption_boundary"]
    assert path.is_file(), f"Missing target file: {path}"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    calls = _extract_chmod_calls(tree)
    assert len(calls) == 0, f"Expected 0 chmod calls in {path.name}, found: {calls}"


def test_run_layout_has_no_permissive_chmod() -> None:
    """Verify run_layout does not physically chmod to 0o755 at line 980."""
    path = TARGET_FILES["run_layout"]
    assert path.is_file(), f"Missing target file: {path}"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    calls = _extract_chmod_calls(tree)
    for lineno, mode in calls:
        assert mode != 0o755, f"Found overly permissive 0o755 at {path.name}:{lineno}"


def test_claude_profile_directories_parent_permissions_use_synthetic_metadata() -> None:
    """Verify tests for unacceptable permissions do not physically chmod to 0o777 or 0o775."""
    path = TARGET_FILES["claude_profile_directories"]
    assert path.is_file(), f"Missing target file: {path}"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    target_functions = {
        "test_unacceptable_parent_permissions_rejected_for_user_home",
        "test_unacceptable_parent_permissions_rejected_for_scratch",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in target_functions:
            fn_calls = _extract_chmod_calls(node)
            assert (
                len(fn_calls) == 0
            ), f"Function {node.name} must use synthetic stat, but contains chmod: {fn_calls}"


def test_controller_generation_store_has_no_permissive_chmod() -> None:
    """Verify controller generation store fixtures only use safe private permissions (0o700)."""
    path = TARGET_FILES["controller_generation_store"]
    assert path.is_file(), f"Missing target file: {path}"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    calls = _extract_chmod_calls(tree)
    for lineno, mode in calls:
        if mode is not None:
            assert mode not in (
                0o755,
                0o775,
                0o777,
                0o644,
                0o666,
            ), f"Found overly permissive mode {oct(mode)} at {path.name}:{lineno}"
            assert (
                mode & 0o077
            ) == 0, f"Expected private mode without group/other bits, found {oct(mode)} at {path.name}:{lineno}"


def test_claude_profile_user_home_rejects_synthetic_permissive_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Functional check: resolve_user_home fails closed against synthetic 0o777 parent."""
    home = tmp_path / "user_home"
    home.mkdir(mode=0o700, parents=True, exist_ok=True)
    real_lstat = Path.lstat

    def fake_lstat(path: Path) -> os.stat_result:
        res = real_lstat(path)
        if path == home:
            return os.stat_result((stat.S_IFDIR | 0o777, *res[1:]))
        return res

    monkeypatch.setattr(Path, "lstat", fake_lstat)
    with pytest.raises(ProfileDirectoryError, match="unsafe permissions"):
        resolve_user_home(environment={}, home=home)


def test_claude_profile_scratch_rejects_synthetic_permissive_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Functional check: resolve_scratch fails closed against synthetic 0o777 scratch."""
    home = tmp_path / "user_home"
    home.mkdir(mode=0o700, parents=True, exist_ok=True)
    scratch = home / "scratch"
    scratch.mkdir(mode=0o700, parents=True, exist_ok=True)
    real_lstat = Path.lstat

    def fake_lstat(path: Path) -> os.stat_result:
        res = real_lstat(path)
        if path == scratch:
            return os.stat_result((stat.S_IFDIR | 0o777, *res[1:]))
        return res

    monkeypatch.setattr(Path, "lstat", fake_lstat)
    with pytest.raises(ProfileDirectoryError, match="unsafe permissions"):
        resolve_scratch(
            environment={APGR_SCRATCH_OVERRIDE_ENVIRONMENT: str(scratch)},
            home=home,
        )


def test_controller_store_rejects_synthetic_permissive_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Functional check: coordinate fails closed against synthetic 0o777 store directory."""
    repo = _init_git_repo(tmp_path / "repo")
    store_dir = tmp_path / "store"
    store_dir.mkdir(mode=0o700, parents=True)
    real_lstat = Path.lstat

    monkeypatch.setattr(
        Path,
        "lstat",
        lambda p: (
            os.stat_result((stat.S_IFDIR | 0o777, *real_lstat(p)[1:]))
            if p == store_dir
            else real_lstat(p)
        ),
    )

    with pytest.raises(StoreSecurityError, match="group/world writable"), coordinate(repo, store=store_dir):
        pass


def test_validate_generation_detects_synthetic_tampered_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Functional check: validate_generation detects tampered file mode via synthetic lstat."""
    _, ctrl_dir, record = _setup_test_generation(tmp_path)
    gen_root = Path(record["generation_root"])
    target = gen_root / "libexec" / "helper.py"

    real_lstat = Path.lstat
    monkeypatch.setattr(
        Path,
        "lstat",
        lambda p: (
            os.stat_result((stat.S_IFREG | 0o777, *real_lstat(p)[1:]))
            if p == target
            else real_lstat(p)
        ),
    )

    with pytest.raises(GenerationValidationError, match="Mode mismatch"):
        validate_generation(record, ctrl_dir)


# APG166ZM: hosted CodeQL py/overly-permissive-file results in the bundle
# publisher and the H custody fixtures.  Every explicit chmod/open/mkdir mode
# there is a literal without group or other bits; a computed mode or a
# Path.chmod indirection would hide the same permission from the query.
CODEQL_PERMISSION_FILES = (
    REPO_ROOT / "libexec" / "agent_phase" / "bundle_io.py",
    DISPATCHER_TEST_DIR / "h_live_fixtures.py",
    DISPATCHER_TEST_DIR / "test_h_live_admission.py",
    DISPATCHER_TEST_DIR / "test_h_replacement_admission.py",
)


def _explicit_modes(tree: ast.AST) -> list[tuple[int, str, ast.expr]]:
    modes = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, (ast.Attribute, ast.Name)):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else func.id
        os_call = isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "os"
        index = {"chmod": 1 if os_call else 0, "mkdir": 1 if os_call else 0, "open": 2}.get(name)
        if index is None or (name == "open" and not os_call):
            continue
        mode = next((keyword.value for keyword in node.keywords if keyword.arg == "mode"), None)
        if mode is None and len(node.args) > index:
            mode = node.args[index]
        if mode is not None or name == "chmod":
            modes.append((node.lineno, name, mode))
    return modes


@pytest.mark.parametrize("path", CODEQL_PERMISSION_FILES, ids=lambda path: path.name)
def test_codeql_permission_files_use_only_literal_owner_private_modes(path: Path) -> None:
    modes = _explicit_modes(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
    for lineno, name, mode in modes:
        assert isinstance(mode, ast.Constant) and type(mode.value) is int, (
            f"{path.name}:{lineno} {name} mode must be an integer literal")
        assert mode.value & 0o077 == 0, f"{path.name}:{lineno} {name} grants {oct(mode.value)}"
    if path.name == "bundle_io.py":
        assert {(name, mode.value) for _, name, mode in modes} == {("mkdir", 0o700), ("open", 0o600)}


def test_explicit_mode_scan_detects_group_and_computed_modes() -> None:
    source = ("import os\nos.chmod(p, 0o620)\nPath(p).chmod(MODE)\n"
              "os.open(p, flags, 0o644)\nq.mkdir(mode=0o755)\nos.open(p, flags)\n")
    found = [(name, getattr(mode, "value", None)) for _, name, mode in _explicit_modes(ast.parse(source))]
    assert found == [("chmod", 0o620), ("chmod", None), ("open", 0o644), ("mkdir", 0o755)]
