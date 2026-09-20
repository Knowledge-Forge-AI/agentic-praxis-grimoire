"""Outbox projection engine for Request V2 dispatch invocations.

Projects operator-facing symlinks and atomic locator metadata into the
standard APGR outbox topology:
  <outbox_root>/<project>/<phase-id>/
    <phase-id>-dispatch--<timestamp>        -> canonical run directory
    <phase-id>-dispatch--<timestamp>.zip    -> canonical archive
    <phase-id>-dispatch--<timestamp>.locator.json (atomic regular file)

Canonical machine authority remains strictly under <APGR_HOME>/state/.
Outbox symlinks are navigation only and must never become resume authority.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import sys
from typing import Any, Mapping

from .run import RunPathError, safe_component

# Ensure src is accessible for config resolution if needed
_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

try:
    from agentic_praxis_grimoire.config import (
        DEFAULT_OUTBOX_RELATIVE,
        default_outbox_root,
        resolve_outbox_root as _resolve_config_outbox_root,
    )
except ImportError:
    DEFAULT_OUTBOX_RELATIVE = Path("Documents") / "agent" / "outbox"

    def default_outbox_root(*, home: str | os.PathLike[str] | None = None) -> Path:
        base = Path.home() if home is None else Path(home).expanduser().resolve()
        return base / DEFAULT_OUTBOX_RELATIVE

    def _resolve_config_outbox_root(
        explicit: str | os.PathLike[str] | None = None,
        *,
        home: str | os.PathLike[str] | None = None,
        **kwargs: Any,
    ) -> Path:
        if explicit is not None:
            return Path(explicit).expanduser().resolve()
        return default_outbox_root(home=home)


def resolve_outbox_root(
    explicit: str | os.PathLike[str] | None = None,
    *,
    project_root: str | os.PathLike[str] | None = None,
    apgr_home: str | os.PathLike[str] | None = None,
    home: str | os.PathLike[str] | None = None,
    **kwargs: Any,
) -> Path:
    if explicit is not None:
        return Path(explicit).expanduser().resolve()
    resolved = _resolve_config_outbox_root(
        explicit=None,
        project_root=project_root,
        apgr_home=apgr_home,
        home=home,
        **kwargs,
    )
    def_root = default_outbox_root(home=home).expanduser().resolve()
    if resolved == def_root:
        env_root = os.environ.get("AGENT_PHASE_RUN_ROOT")
        if env_root:
            return Path(env_root).expanduser().resolve()
    return resolved.expanduser().resolve()


LOCATOR_SCHEMA = "agent-phase-dispatch-locator-v1"
LOCATOR_VERSION = 1


def validate_no_symlink_parents(path: Path, boundary: Path) -> None:
    """Ensure no directory component between boundary and path (inclusive) is a symlink."""
    boundary = boundary.resolve()
    curr = path
    while True:
        try:
            st = curr.lstat()
            if stat.S_ISLNK(st.st_mode):
                raise RunPathError(f"hostile symlink detected in parent chain: {curr}")
        except FileNotFoundError:
            pass
        if curr == boundary or curr == curr.parent or not curr.is_relative_to(boundary):
            break
        curr = curr.parent


def build_locator_payload(
    *,
    project: str,
    phase_id: str,
    run_id: str,
    request_digest: str,
    canonical_run_path: Path,
    database_path: Path,
    archive_path: Path | None,
    archive_sha256: str | None,
    projection_paths: Mapping[str, str],
    semantic_status: str,
    finalization_policy: str,
    finalization_status: str,
    commit: Mapping[str, Any] | None = None,
    tree: str | None = None,
    publication_status: str | None = None,
    remote_readback: Mapping[str, Any] | None = None,
    archive_status: str | None = None,
) -> dict[str, Any]:
    """Construct an agent-phase-dispatch-locator-v1 dictionary."""
    payload: dict[str, Any] = {
        "schema": LOCATOR_SCHEMA,
        "version": LOCATOR_VERSION,
        "project": project,
        "phase_id": phase_id,
        "run_id": run_id,
        "request_digest": request_digest,
        "canonical_run_path": str(canonical_run_path.resolve()),
        "database_path": str(database_path.resolve()),
        "archive_path": str(archive_path.resolve()) if archive_path else None,
        "archive_sha256": archive_sha256,
        "projection_paths": dict(projection_paths),
        "semantic_status": semantic_status,
        "finalization_policy": finalization_policy,
        "finalization_status": finalization_status,
        "commit": dict(commit) if commit else None,
        "tree": tree,
        "publication_status": publication_status,
        "remote_readback": dict(remote_readback) if remote_readback else None,
    }
    if archive_status is not None:
        payload["archive_status"] = archive_status
    return payload


def project_v2_run(
    *,
    outbox_root: Path,
    project: str,
    phase_id: str,
    run_id: str,
    leaf: str,
    canonical_run_dir: Path,
    canonical_archive_path: Path | None,
    archive_sha256: str | None,
    database_path: Path,
    request_digest: str,
    semantic_status: str,
    finalization_policy: str,
    finalization_status: str,
    commit: Mapping[str, Any] | None = None,
    tree: str | None = None,
    publication_status: str | None = None,
    remote_readback: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Safely project canonical V2 state into operator outbox contract."""
    # 1. Component validation
    safe_project = safe_component(project, "project")
    safe_phase = safe_component(phase_id, "phase id")

    # 2. Canonical target verification
    if not canonical_run_dir.is_dir():
        raise RunPathError(f"canonical run directory does not exist: {canonical_run_dir}")
    if canonical_run_dir.is_symlink():
        raise RunPathError(f"canonical run directory must not be a symlink: {canonical_run_dir}")

    state_root = database_path.parent.resolve()
    runs_root = state_root / "runs"
    try:
        resolved_canonical_run = canonical_run_dir.resolve(strict=True)
    except OSError as err:
        raise RunPathError(f"cannot resolve canonical run directory: {err}") from err

    if not resolved_canonical_run.is_relative_to(runs_root):
        raise RunPathError(f"canonical run directory {resolved_canonical_run} is not inside state runs root {runs_root}")

    resolved_archive: Path | None = None
    if canonical_archive_path is not None:
        if not canonical_archive_path.is_file():
            raise RunPathError(f"canonical archive does not exist: {canonical_archive_path}")
        if canonical_archive_path.is_symlink():
            raise RunPathError(f"canonical archive must not be a symlink: {canonical_archive_path}")
        resolved_archive = canonical_archive_path.resolve(strict=True)
        if not resolved_archive.is_relative_to(runs_root):
            raise RunPathError(f"canonical archive {resolved_archive} is not inside state runs root {runs_root}")

    # 3. Topology & Parent validation
    outbox_root = outbox_root.expanduser().resolve()
    phase_dir = outbox_root / safe_project / safe_phase

    validate_no_symlink_parents(phase_dir, outbox_root)

    os.makedirs(phase_dir, mode=0o700, exist_ok=True)
    try:
        os.chmod(phase_dir, 0o700)
    except OSError:
        pass

    validate_no_symlink_parents(phase_dir, outbox_root)

    # 4. Collision refusal (no-clobber)
    leaf_link = phase_dir / leaf
    zip_link = phase_dir / f"{leaf}.zip"
    locator_file = phase_dir / f"{leaf}.locator.json"

    if leaf_link.is_symlink() or leaf_link.exists():
        raise RunPathError(f"projection target already exists: {leaf_link}")
    if zip_link.is_symlink() or zip_link.exists():
        raise RunPathError(f"projection target archive link already exists: {zip_link}")
    if locator_file.is_symlink() or locator_file.exists():
        raise RunPathError(f"projection locator already exists: {locator_file}")

    projection_paths = {
        "run_directory": str(leaf_link),
        "archive": str(zip_link),
        "locator": str(locator_file),
    }

    # 5. Atomic locator write & symlink creation
    locator_payload = build_locator_payload(
        project=safe_project,
        phase_id=safe_phase,
        run_id=run_id,
        request_digest=request_digest,
        canonical_run_path=resolved_canonical_run,
        database_path=database_path.resolve(),
        archive_path=resolved_archive,
        archive_sha256=archive_sha256,
        projection_paths=projection_paths,
        semantic_status=semantic_status,
        finalization_policy=finalization_policy,
        finalization_status=finalization_status,
        commit=commit,
        tree=tree,
        publication_status=publication_status,
        remote_readback=remote_readback,
    )

    tmp_locator = phase_dir / f".{leaf}.locator.json.tmp"
    try:
        tmp_locator.write_text(json.dumps(locator_payload, indent=2) + "\n", encoding="utf-8")
        fd = os.open(tmp_locator, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(tmp_locator, locator_file)
    except Exception as exc:
        if tmp_locator.exists():
            try:
                tmp_locator.unlink()
            except OSError:
                pass
        raise RunPathError(f"failed to write projection locator: {exc}") from exc

    try:
        os.symlink(resolved_canonical_run, leaf_link)
        if resolved_archive is not None:
            os.symlink(resolved_archive, zip_link)
    except Exception as exc:
        if leaf_link.is_symlink():
            leaf_link.unlink()
        if zip_link.is_symlink():
            zip_link.unlink()
        if locator_file.exists():
            locator_file.unlink()
        raise RunPathError(f"failed to create projection symlinks: {exc}") from exc

    return locator_payload
