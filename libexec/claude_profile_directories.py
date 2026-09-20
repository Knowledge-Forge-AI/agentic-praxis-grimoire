"""Closed directory token resolution and security validation for Claude profiles."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import os
from pathlib import Path
import stat


TOKEN_USER_HOME = "user-home"
TOKEN_SCRATCH = "scratch"
SUPPORTED_DIRECTORY_TOKENS = frozenset({TOKEN_USER_HOME, TOKEN_SCRATCH})

SCRATCH_DIRECTORY_TOKENS = [TOKEN_SCRATCH]
HOST_DIRECTORY_TOKENS = [TOKEN_USER_HOME, TOKEN_SCRATCH]

APGR_HOME_ENVIRONMENT = "APGR_HOME"
APGR_SCRATCH_OVERRIDE_ENVIRONMENT = "APGR_AGENT_SCRATCH_ROOT"


class ProfileError(RuntimeError):
    """A profile or launcher argument violates the profile contract."""


class ProfileDirectoryError(ProfileError):
    """A directory token or filesystem directory violates security policy."""


def validate_directory_tokens(tokens: Sequence[str]) -> None:
    """Ensure tokens belong to the closed set without malformed or duplicate entries."""
    if not isinstance(tokens, (list, tuple)):
        raise ProfileDirectoryError(
            f"additional directories must be a list or tuple of tokens, got {type(tokens).__name__}"
        )
    seen: set[str] = set()
    for token in tokens:
        if not isinstance(token, str) or not token:
            raise ProfileDirectoryError(f"malformed directory token: {token!r}")
        if token not in SUPPORTED_DIRECTORY_TOKENS:
            raise ProfileDirectoryError(f"unsupported directory token: {token!r}")
        if token in seen:
            raise ProfileDirectoryError(f"duplicate directory token: {token!r}")
        seen.add(token)


def validate_directory_security(
    path: Path,
    *,
    label: str,
    writable: bool = False,
) -> Path:
    """Validate direct non-symlink directory, ancestors, ownership, and mode."""
    if not path.is_absolute():
        raise ProfileDirectoryError(f"{label} path must be absolute: {path}")
    if ".." in path.parts:
        raise ProfileDirectoryError(f"{label} path must be direct: {path}")

    if not path.exists():
        raise ProfileDirectoryError(f"{label} directory does not exist: {path}")

    if not path.is_dir():
        raise ProfileDirectoryError(f"{label} path is not a directory: {path}")

    # Symlink check on the target and all ancestors
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ProfileDirectoryError(
                f"{label} path or ancestor is a symlink: {part}"
            )

    current_uid = os.getuid()

    # Ancestor ownership and mode check
    for part in path.parents:
        if not part.exists():
            continue
        st = part.lstat()
        if st.st_uid not in {0, current_uid}:
            raise ProfileDirectoryError(
                f"{label} ancestor has untrusted owner (uid {st.st_uid} != {current_uid}): {part}"
            )
        if (
            stat.S_ISDIR(st.st_mode)
            and (st.st_mode & 0o022)
            and not (st.st_mode & stat.S_ISVTX)
        ):
            raise ProfileDirectoryError(
                f"{label} ancestor is group or world writable without sticky bit: {part}"
            )

    # Target directory ownership check
    info = path.lstat()
    if info.st_uid != current_uid:
        raise ProfileDirectoryError(
            f"{label} directory must be owned by current user (uid {current_uid}, got {info.st_uid}): {path}"
        )

    # Target directory mode check: must not be group-writable or world-writable
    if (info.st_mode & 0o022) != 0:
        mode_str = oct(stat.S_IMODE(info.st_mode))
        raise ProfileDirectoryError(
            f"{label} directory has unsafe permissions (group/world writable): {path} (mode {mode_str})"
        )

    if not (info.st_mode & 0o100) or not os.access(path, os.X_OK):
        raise ProfileDirectoryError(f"{label} directory is not accessible: {path}")
    if writable:
        if not (info.st_mode & 0o200) or not os.access(path, os.W_OK):
            raise ProfileDirectoryError(f"{label} directory is not writable: {path}")

    return path


def _create_owned_child(parent: Path, name: str) -> Path:
    """Create only an APGR-owned child through a validated parent descriptor."""
    validate_directory_security(parent, label="APGR scratch parent", writable=True)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        fd = os.open(parent, flags)
        try:
            observed = parent.lstat()
            opened = os.fstat(fd)
            if (opened.st_dev, opened.st_ino) != (observed.st_dev, observed.st_ino):
                raise ProfileDirectoryError("APGR scratch parent changed before creation")
            try:
                os.mkdir(name, mode=0o700, dir_fd=fd)
            except FileExistsError:
                pass  # Never chmod or replace an existing operator-owned entry.
            child = validate_directory_security(
                parent / name, label="default scratch", writable=True,
            )
            observed = parent.lstat()
            if (opened.st_dev, opened.st_ino) != (observed.st_dev, observed.st_ino):
                raise ProfileDirectoryError("APGR scratch parent changed during creation")
            return child
        finally:
            os.close(fd)
    except OSError as error:
        raise ProfileDirectoryError("cannot create bounded APGR scratch directory") from error


def resolve_apgr_home(
    *,
    environment: Mapping[str, str] | None = None,
    home: Path | str | None = None,
) -> Path:
    """Resolve APGR home directory from environment override or default ~/.apgr."""
    env = os.environ if environment is None else environment
    configured = env.get(APGR_HOME_ENVIRONMENT)
    if configured is not None:
        if not configured.strip():
            raise ProfileDirectoryError(f"{APGR_HOME_ENVIRONMENT} must not be empty")
        p = Path(configured)
        if not p.is_absolute():
            raise ProfileDirectoryError(
                f"{APGR_HOME_ENVIRONMENT} must be an absolute path: {configured}"
            )
        return p

    if home is not None:
        user_home = Path(home)
    elif "HOME" in env:
        user_home = Path(env["HOME"])
    else:
        user_home = Path.home()

    if not user_home.is_absolute():
        raise ProfileDirectoryError(
            f"user home must be an absolute path: {user_home}"
        )
    return user_home / ".apgr"


def resolve_user_home(
    *,
    environment: Mapping[str, str] | None = None,
    home: Path | str | None = None,
) -> Path:
    """Resolve and validate the current user home directory."""
    env = os.environ if environment is None else environment
    if home is not None:
        user_home = Path(home)
    elif "HOME" in env:
        user_home = Path(env["HOME"])
    else:
        user_home = Path.home()

    return validate_directory_security(
        user_home, label="user-home", writable=False
    )


def resolve_scratch(
    *,
    environment: Mapping[str, str] | None = None,
    home: Path | str | None = None,
) -> Path:
    """Resolve and validate scratch directory with override support."""
    env = os.environ if environment is None else environment
    override = env.get(APGR_SCRATCH_OVERRIDE_ENVIRONMENT)
    if override is not None:
        if not override.strip():
            raise ProfileDirectoryError(
                f"{APGR_SCRATCH_OVERRIDE_ENVIRONMENT} must not be empty"
            )
        scratch_path = Path(override)
        if not scratch_path.is_absolute():
            raise ProfileDirectoryError(
                f"{APGR_SCRATCH_OVERRIDE_ENVIRONMENT} must be an absolute path: {override}"
            )
        if not scratch_path.exists():
            raise ProfileDirectoryError(
                f"scratch override directory does not exist: {scratch_path}"
            )
        return validate_directory_security(
            scratch_path, label="scratch override", writable=True
        )

    apgr_home = resolve_apgr_home(environment=env, home=home)
    scratch_path = apgr_home / "scratch"
    if not apgr_home.exists() and APGR_HOME_ENVIRONMENT not in env:
        _create_owned_child(apgr_home.parent, ".apgr")
    validate_directory_security(apgr_home, label="APGR home")
    if not scratch_path.exists():
        _create_owned_child(apgr_home, "scratch")
    return validate_directory_security(
        scratch_path, label="default scratch", writable=True
    )


def resolve_directory_token(
    token: str,
    *,
    environment: Mapping[str, str] | None = None,
    home: Path | str | None = None,
) -> Path:
    """Resolve a single closed token to a validated direct filesystem path."""
    if token == TOKEN_USER_HOME:
        return resolve_user_home(environment=environment, home=home)
    if token == TOKEN_SCRATCH:
        return resolve_scratch(environment=environment, home=home)
    raise ProfileDirectoryError(f"unsupported directory token: {token!r}")


def resolve_profile_directories(
    tokens: Sequence[str],
    *,
    environment: Mapping[str, str] | None = None,
    home: Path | str | None = None,
) -> list[Path]:
    """Validate closed tokens and resolve each to a secure filesystem path."""
    validate_directory_tokens(tokens)
    return [
        resolve_directory_token(token, environment=environment, home=home)
        for token in tokens
    ]
