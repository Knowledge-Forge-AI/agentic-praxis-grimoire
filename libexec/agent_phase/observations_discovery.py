"""Bounded, name-only discovery of dispatch run leaves for ``observations list``.

Only the known layouts are scanned: ``<outbox>/<project>/<phase>/<phase>-dispatch--<ts>``
(current V1 leaves and V2 projection symlinks), historical
``<outbox>/<project>/<phase>--<ts>`` leaves, and, when requested, canonical
``<APGR_HOME>/state/runs/<run-id>`` directories. Project and phase directories
must be real directories; symlinks and special files are counted and never
entered. A symlinked leaf becomes readable only as a verified V2 projection
into this APGR home's ``state/runs`` (its small locator is the only file read
here). Every scan shares one entry bound; hitting any bound marks the result
incomplete rather than silently newest.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import stat
from typing import Any, Mapping

from . import observations as obs

MAX_PROJECTS = 256
MAX_PHASE_DIRS = 4096
MAX_DISCOVERY_ENTRIES = 50_000
MAX_LOCATOR_BYTES = 64 * 1024
HISTORICAL_LEAF = re.compile(r"(.+)--(\d{8}T\d{12}Z)\Z")
_STAMP = re.compile(r"(\d{8}T\d{6})(\d*)Z\Z")
OLDEST = datetime.min.replace(tzinfo=timezone.utc)


def _stamp(text: str | None) -> datetime | None:
    match = _STAMP.fullmatch(text or "")
    if not match:
        return None
    try:
        moment = datetime.strptime(match[1], "%Y%m%dT%H%M%S")
    except ValueError:
        return None
    return moment.replace(microsecond=int(match[2][:6].ljust(6, "0")), tzinfo=timezone.utc)


def iso(moment: datetime | None) -> str | None:
    return moment.isoformat().replace("+00:00", "Z") if moment else None


def mtime(path: Path) -> datetime | None:
    try:
        return datetime.fromtimestamp(path.lstat().st_mtime, tz=timezone.utc)
    except OSError:
        return None


def _kind(entry: os.DirEntry) -> str:
    try:
        if entry.is_symlink():
            return "symlink"
        if entry.is_dir(follow_symlinks=False):
            return "dir"
        return "file" if entry.is_file(follow_symlinks=False) else "special"
    except OSError:
        return "unreadable"


class _Scan:
    """Name-only directory scanning under one shared entry bound."""

    def __init__(self) -> None:
        self.entries = 0
        self.truncated = False
        self.skipped = Counter({"symlink": 0, "special": 0, "unreadable": 0, "non_leaf": 0})
        self.warnings: list[str] = []

    def truncate(self, what: str) -> None:
        if not self.truncated:
            obs._warn(self.warnings, f"{what} bound reached; results are incomplete and not guaranteed newest "
                                     "(narrow with --project/--phase)")
        self.truncated = True

    def skip(self, kind: str) -> None:
        self.skipped[kind if kind in ("symlink", "special", "unreadable") else "non_leaf"] += 1

    def children(self, path: Path, label: str) -> list[tuple[str, str]]:
        found = []
        try:
            with os.scandir(path) as entries:
                for entry in entries:
                    if self.entries >= MAX_DISCOVERY_ENTRIES:
                        self.truncate("discovery entry")
                        break
                    self.entries += 1
                    found.append((entry.name, _kind(entry)))
        except OSError as error:
            self.skipped["unreadable"] += 1
            obs._warn(self.warnings, f"{label}: {type(error).__name__}")
        return sorted(found)


def _candidate(source: str, path: Path, *, project: str | None, phase: str | None, leaf: str,
               root: str, relative: str, started: datetime | None) -> dict[str, Any]:
    fallback = mtime(path) if started is None and source == "v2_canonical" else None
    return {"source": source, "path": path, "project": project, "phase_id": phase, "leaf": leaf,
            "root": root, "relative": relative, "started": started or fallback,
            "started_source": "leaf_name" if started else ("filesystem_mtime" if fallback else None),
            "records_reason": None, "result": None}


def _projection(link: Path, locator: Path, runs_root: Path | None) -> tuple[Path | None, str | None]:
    try:
        target = link.resolve(strict=True)
    except (OSError, RuntimeError):
        return None, "symlink_target_unresolvable"
    if runs_root is None or target.parent != runs_root:
        other = target.parent.name == "runs" and target.parent.parent.name == "state"
        return None, "symlink_target_other_apgr_home_runs" if other else "symlink_target_outside_apgr_home_runs"
    try:
        if not stat.S_ISDIR(target.lstat().st_mode):
            return None, "symlink_target_not_directory"
    except OSError:
        return None, "symlink_target_unresolvable"
    value = obs._read_json(locator, MAX_LOCATOR_BYTES, [], "locator")
    if not isinstance(value, Mapping):
        return None, "symlink_leaf_without_locator"
    if value.get("run_id") != target.name:
        return None, "locator_run_mismatch"
    return target, None


def _phase_candidates(scan: _Scan, root: Path, project: str, phase: str,
                      runs_root: Path | None) -> list[dict[str, Any]]:
    found = []
    phase_dir = root / project / phase
    for name, kind in scan.children(phase_dir, f"{project}/{phase}"):
        match = obs._LEAF.fullmatch(name)
        if not match or kind not in ("dir", "symlink"):
            scan.skip(kind if match else "non_leaf")
            continue
        candidate = _candidate("outbox_leaf", phase_dir / name, project=project, phase=phase, leaf=name,
                               root="outbox", relative=f"{project}/{phase}/{name}", started=_stamp(match[1]))
        if kind == "symlink":
            target, reason = _projection(phase_dir / name, phase_dir / f"{name}.locator.json", runs_root)
            if target is not None:
                candidate.update(source="v2_projection", path=target)
            else:
                candidate.update(source="symlink_leaf", records_reason=reason)
        found.append(candidate)
    return found


def _project_candidates(scan: _Scan, root: Path, project: str, phase: str | None,
                        runs_root: Path | None, phases: list[int]) -> list[dict[str, Any]]:
    found = []
    for name, kind in scan.children(root / project, project):
        historical = HISTORICAL_LEAF.fullmatch(name)
        if historical and not obs._LEAF.fullmatch(name):
            if kind != "dir":
                scan.skip(kind)
            elif phase is None or historical[1] == phase:
                found.append(_candidate("historical_leaf", root / project / name, project=project,
                                        phase=historical[1], leaf=name, root="outbox",
                                        relative=f"{project}/{name}", started=_stamp(historical[2])))
            continue
        if kind != "dir":
            scan.skip(kind)
        elif phase is None or name == phase:
            phases[0] += 1
            if phases[0] > MAX_PHASE_DIRS:
                scan.truncate("phase directory")
                break
            found.extend(_phase_candidates(scan, root, project, name, runs_root))
    return found


def _outbox_candidates(scan: _Scan, root: Path, project: str | None, phase: str | None,
                       runs_root: Path | None) -> list[dict[str, Any]]:
    if project is not None:
        try:
            info = (root / project).lstat()
        except OSError:
            return []
        if not stat.S_ISDIR(info.st_mode):
            scan.skip("symlink" if stat.S_ISLNK(info.st_mode) else "non_leaf")
            return []
        projects = [project]
    else:
        projects = []
        for name, kind in scan.children(root, "outbox root"):
            if kind != "dir":
                scan.skip(kind)
            elif len(projects) >= MAX_PROJECTS:
                scan.truncate("project")
                break
            else:
                projects.append(name)
    found, phases = [], [0]
    for name in projects:
        found.extend(_project_candidates(scan, root, name, phase, runs_root, phases))
    return found


def _v2_candidates(scan: _Scan, runs_root: Path) -> list[dict[str, Any]]:
    found = []
    for name, kind in scan.children(runs_root, "state/runs"):
        if kind != "dir":
            scan.skip(kind)
            continue
        match = obs.V2_RUN.fullmatch(name)
        found.append(_candidate("v2_canonical", runs_root / name, project=None, phase=None, leaf=name,
                                root="apgr_home", relative=f"state/runs/{name}",
                                started=_stamp(match[1]) if match else None))
    return found


def discover_runs(*, outbox_root: Path | None = None, project: str | None = None, phase: str | None = None,
                  apgr_home: Path | None = None, v2: bool = False) -> tuple[list[dict[str, Any]], _Scan]:
    """Name-only discovery (plus projection locators); ``project=None`` scans all projects."""
    scan = _Scan()
    runs = Path(apgr_home) / "state" / "runs" if apgr_home is not None else None
    runs_root = _runs_root(runs) if runs is not None else None
    if runs is not None and runs.is_symlink():
        obs._warn(scan.warnings, "state/runs is a symlink; canonical V2 runs and projections are not read")
    found = []
    if outbox_root is not None:
        found.extend(_outbox_candidates(scan, Path(outbox_root), project, phase, runs_root))
    if v2 and runs_root is not None:
        found.extend(_v2_candidates(scan, runs_root))
    return found, scan


def _runs_root(runs: Path) -> Path | None:
    """Resolved ``state/runs``; a symlinked ``state/runs`` is refused, as in ``explain --leaf``."""
    try:
        return runs.resolve() if runs.is_dir() and not runs.is_symlink() else None
    except OSError:
        return None


def verified_projection(link: Path, runs: Path) -> Path | None:
    """Resolved canonical run for a verified V2 projection symlink, else ``None``."""
    return _projection(link, link.with_name(f"{link.name}.locator.json"), _runs_root(runs))[0]
