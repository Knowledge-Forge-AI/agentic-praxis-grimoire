"""Durable run artifacts, outside any target repository."""

from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any, Callable


RUN_ROOT_ENVIRONMENT = "AGENT_PHASE_RUN_ROOT"
TELEMETRY_FILE = "malskanner-shadow.jsonl"
LABEL_FILE = "malskanner-shadow.labels.jsonl"

REQUEST_SUFFIX = ".request.json"
JSON_SUFFIX = ".json"
# `fullmatch` against this is the whole validation. `$` would accept a trailing
# newline, and a newline in a component would reach the stage envelope's
# `run_id:` line as extra dispatcher-looking text.
COMPONENT_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")

RUN_LAYOUT_SCHEMA_V2 = "agent-phase-run-layout-v2"
RUN_LAYOUT_KIND_V2 = "project-phase-dispatch"
# General leaf syntax patterns for pattern validation and test support.
# Production topology validation uses phase_id-bound expressions with re.fullmatch.
V1_LEAF_PATTERN = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]*--\d{8}T\d{12}Z\Z")
V2_LEAF_PATTERN = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]*-dispatch--\d{8}T\d{12}Z\Z")


class RunPathError(ValueError):
    """A run artifact path component is not a safe single path component."""

    def __init__(self, detail: str, code: str = "UNSAFE_RUN_PATH_COMPONENT") -> None:
        super().__init__(detail)
        self.code = code


def default_root() -> Path:
    override = os.environ.get(RUN_ROOT_ENVIRONMENT)
    if override:
        return Path(override)
    home = Path(os.environ.get("HOME", "~")).expanduser()
    return home / "Documents/agent/outbox"


def v2_leaf(phase_id: str, timestamp: str) -> str:
    return f"{phase_id}-dispatch--{timestamp}"


def v2_run_id(project: str, phase_id: str, leaf: str) -> str:
    return f"{project}/{phase_id}/{leaf}"


def layout_record_v2(run_id: str, leaf: str) -> dict[str, str]:
    return {
        "schema": RUN_LAYOUT_SCHEMA_V2,
        "kind": RUN_LAYOUT_KIND_V2,
        "run_id": run_id,
        "leaf": leaf,
    }


def safe_component(
    value: str, kind: str, *, reported_value: str | None = None
) -> str:
    """Validate one path component. Never rewrites; refuses instead."""
    if not COMPONENT_PATTERN.fullmatch(value):
        invalid_value = value if reported_value is None else reported_value
        raise RunPathError(
            f"{kind} is not a safe path component: {invalid_value!r}; it must match "
            f"{COMPONENT_PATTERN.pattern} (ASCII letters, digits, dot, dash, "
            f"underscore; no separator, no leading dot)"
        )
    return value


def project_name(repository_root: Path) -> str:
    """Derive the visible project namespace from the repository basename."""
    project = repository_root.name.lstrip(".")
    return safe_component(
        project, "project", reported_value=repository_root.name
    )


def phase_id_from_request(path: Path) -> str:
    """Derive the phase id from the request filename, never from prompt prose.

    Only the two known suffixes are removed. `Path.stem` would drop whatever
    followed the last dot, so `RELEASE-2.0.request.json` would silently become
    the phase `RELEASE-2` — a rewrite, in a change whose rule is that an
    unusable name is refused rather than repaired.
    """
    name = path.name
    for suffix in (REQUEST_SUFFIX, JSON_SUFFIX):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    return safe_component(name, "phase id")


def run_timestamp() -> str:
    """UTC to the microsecond, so repeat attempts need no random suffix."""
    now = datetime.datetime.now(datetime.timezone.utc)
    return now.strftime("%Y%m%dT%H%M%S%f") + "Z"


def worker_parent_prefix(run_id: str) -> str:
    """Transport-safe namespace for one run; retain the full logical ID elsewhere.

    Run components are bounded by the filesystem, not the worker transport's
    128-character limit. Hash the complete namespaced ID rather than rewriting
    punctuation or truncating names. Historical ledgers keep their old keys.
    """
    return "dispatch-" + hashlib.sha256(run_id.encode("utf-8")).hexdigest() + "--"


def stage_parent_id(run_id: str, stage: str, index: int) -> str:
    """Bind the dispatcher-owned stage name and invocation to its run namespace."""
    return f"{worker_parent_prefix(run_id)}{stage}--{index}"


def validate_run_topology(
    source: Path,
    state: dict[str, Any],
    result: dict[str, Any] | None = None,
    *,
    error_fn: Callable[[str, str], Exception] | None = None,
) -> None:
    """Validate source run directory topology, layout provenance, and identity.

    Supports exact historical V1 (<root>/<project>/<phase>--<timestamp>) and
    V2 (<root>/<project>/<phase>/<phase>-dispatch--<timestamp>).
    Rejects mixed, forged, malformed, or ambiguous configurations.
    """
    def fail(code: str, detail: str) -> None:
        if error_fn is not None:
            raise error_fn(code, detail)
        raise RunPathError(f"{code}: {detail}", code)

    project = state.get("project")
    phase_id = state.get("phase_id")
    if not isinstance(project, str) or not isinstance(phase_id, str):
        fail("RESUME_SOURCE_INVALID", "source project or phase identity is invalid")
    try:
        safe_component(project, "project")
        safe_component(phase_id, "phase id")
    except RunPathError as error:
        fail("RESUME_SOURCE_INVALID", str(error))

    recorded_directory = state.get("run_directory")
    if not isinstance(recorded_directory, str):
        fail("RESUME_SOURCE_INVALID", "source run directory identity is invalid")
    if Path(recorded_directory).resolve() != source:
        fail("RESUME_SOURCE_INVALID", "source run directory identity does not match source path")

    # Note: callers using require_source pass a strictly resolved path where
    # is_symlink() is False, but these checks protect direct callers against symlinks.
    if source.is_symlink():
        fail("RESUME_SOURCE_INVALID", "source run must not be a symlink")
    if source.parent.is_symlink():
        fail("RESUME_SOURCE_INVALID", "source parent directory must not be a symlink")

    layout = state.get("run_layout")
    if layout is None:
        # Historical V1 run
        if source.parent.name != project:
            fail(
                "RESUME_SOURCE_INVALID",
                "source project, phase, run ID, and directory topology disagree",
            )
        expected_run_id = f"{project}/{source.name}"
        if state.get("run_id") != expected_run_id:
            fail(
                "RESUME_SOURCE_INVALID",
                "source project, phase, run ID, and directory topology disagree",
            )
        if re.fullmatch(re.escape(phase_id) + r"--\d{8}T\d{12}Z", source.name) is None:
            fail(
                "RESUME_SOURCE_INVALID",
                "source project, phase, run ID, and directory topology disagree",
            )
        if result is not None:
            if result.get("run_layout") is not None:
                fail(
                    "RESUME_ARTIFACT_MISMATCH",
                    "source result and state disagree on run_layout",
                )
            for key in ("project", "phase_id", "run_id", "run_directory"):
                if result.get(key) != state.get(key):
                    fail(
                        "RESUME_ARTIFACT_MISMATCH",
                        f"source result and state disagree on {key}",
                    )
    else:
        # V2 layout
        if not isinstance(layout, dict):
            fail("RESUME_SOURCE_INVALID", "source run_layout must be an object")
        if layout.get("schema") != RUN_LAYOUT_SCHEMA_V2:
            fail(
                "RESUME_SOURCE_INVALID",
                f"unsupported run_layout schema: {layout.get('schema')!r}",
            )
        if layout.get("kind") != RUN_LAYOUT_KIND_V2:
            fail(
                "RESUME_SOURCE_INVALID",
                f"unsupported run_layout kind: {layout.get('kind')!r}",
            )
        if source.parent.parent.is_symlink():
            fail("RESUME_SOURCE_INVALID", "source grandparent directory must not be a symlink")
        if source.parent.name != phase_id:
            fail(
                "RESUME_SOURCE_INVALID",
                f"V2 source parent directory {source.parent.name!r} does not match phase id {phase_id!r}",
            )
        if source.parent.parent.name != project:
            fail(
                "RESUME_SOURCE_INVALID",
                f"V2 source grandparent directory {source.parent.parent.name!r} does not match project {project!r}",
            )
        if re.fullmatch(re.escape(phase_id) + r"-dispatch--\d{8}T\d{12}Z", source.name) is None:
            fail(
                "RESUME_SOURCE_INVALID",
                "V2 source leaf does not match expected phase-dispatch timestamp pattern",
            )
        expected_run_id = f"{project}/{phase_id}/{source.name}"
        if state.get("run_id") != expected_run_id:
            fail(
                "RESUME_SOURCE_INVALID",
                f"V2 run_id {state.get('run_id')!r} does not match expected {expected_run_id!r}",
            )
        if layout.get("run_id") != expected_run_id:
            fail(
                "RESUME_SOURCE_INVALID",
                f"run_layout run_id {layout.get('run_id')!r} does not match expected {expected_run_id!r}",
            )
        if layout.get("leaf") != source.name:
            fail(
                "RESUME_SOURCE_INVALID",
                f"run_layout leaf {layout.get('leaf')!r} does not match source name {source.name!r}",
            )
        if result is not None:
            if result.get("run_layout") != state.get("run_layout"):
                fail(
                    "RESUME_ARTIFACT_MISMATCH",
                    "source result and state disagree on run_layout",
                )
            for key in ("project", "phase_id", "run_id", "run_directory"):
                if result.get(key) != state.get(key):
                    fail(
                        "RESUME_ARTIFACT_MISMATCH",
                        f"source result and state disagree on {key}",
                    )


class RunDirectory:
    """One run's artifact set, at `<root>/<project>/<phase-id>/<phase-id>-dispatch--<timestamp>`.

    A collision fails rather than merges two artifact sets into one directory.
    """

    def __init__(
        self, root: Path, project: str, phase_id: str, timestamp: str | None = None
    ) -> None:
        self.root = root
        self.project = safe_component(project, "project")
        self.phase_id = safe_component(phase_id, "phase id")
        self.timestamp = timestamp or run_timestamp()
        self.leaf = v2_leaf(self.phase_id, self.timestamp)
        self.run_id = v2_run_id(self.project, self.phase_id, self.leaf)
        self.run_layout = layout_record_v2(self.run_id, self.leaf)
        self.project_dir = root / self.project
        self.phase_dir = self.project_dir / self.phase_id
        self.path = self.phase_dir / self.leaf
        self.archive_path = self.phase_dir / f"{self.leaf}.zip"
        self.archive_temporary_path = self.phase_dir / f".{self.leaf}.zip.tmp"
        path_created = False
        temporary_created = False
        archive_created = False

        def cleanup_probe() -> None:
            for candidate, created in (
                (self.archive_path, archive_created),
                (self.archive_temporary_path, temporary_created),
            ):
                if created:
                    try:
                        candidate.unlink()
                    except OSError:
                        pass
            if path_created:
                try:
                    self.path.rmdir()
                except OSError:
                    pass

        try:
            # Check existing project directory
            if os.path.islink(self.project_dir):
                raise RunPathError(
                    f"project path is a symlink: {self.project_dir}",
                    "RUN_PATH_CREATION_FAILED",
                )
            if self.project_dir.exists() and not self.project_dir.is_dir():
                raise RunPathError(
                    f"project path is not a directory: {self.project_dir}",
                    "RUN_PATH_CREATION_FAILED",
                )
            project_existed = self.project_dir.exists()
            if not project_existed:
                self.project_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
                try:
                    self.project_dir.chmod(0o700)
                except OSError:
                    pass

            # Check existing phase directory
            if os.path.islink(self.phase_dir):
                raise RunPathError(
                    f"phase path is a symlink: {self.phase_dir}",
                    "RUN_PATH_CREATION_FAILED",
                )
            if self.phase_dir.exists() and not self.phase_dir.is_dir():
                raise RunPathError(
                    f"phase path is not a directory: {self.phase_dir}",
                    "RUN_PATH_CREATION_FAILED",
                )
            phase_existed = self.phase_dir.exists()
            if not phase_existed:
                self.phase_dir.mkdir(mode=0o700, exist_ok=True)
                try:
                    self.phase_dir.chmod(0o700)
                except OSError:
                    pass

            # Probe receipt collision before creating run leaf
            from . import archive as archive_module
            normal_receipt = archive_module.receipt_path(self.archive_path)
            failure_receipt = archive_module.failure_receipt_path(self.archive_path)
            if os.path.lexists(normal_receipt):
                raise RunPathError(
                    f"run archive receipt already exists: {normal_receipt}",
                    "RUN_ARCHIVE_COLLISION",
                )
            if os.path.lexists(failure_receipt):
                raise RunPathError(
                    f"run archive failure receipt already exists: {failure_receipt}",
                    "RUN_ARCHIVE_COLLISION",
                )

            # Create run directory leaf
            self.path.mkdir(mode=0o700, exist_ok=False)
            path_created = True

            # Probe both ZIP names and the atomic no-clobber hard-link operation
            # before a provider runs. A run root without hard-link support is not
            # feasible for the required archive contract.
            descriptor = os.open(
                self.archive_temporary_path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
            os.close(descriptor)
            temporary_created = True
            os.link(self.archive_temporary_path, self.archive_path)
            archive_created = True
            self.archive_path.unlink()
            archive_created = False
            self.archive_temporary_path.unlink()
            temporary_created = False
        except FileExistsError as error:
            cleanup_probe()
            if not path_created and error.filename == os.fspath(self.path):
                # Preserve the established exact-run-directory collision API.
                raise
            raise RunPathError(
                f"run archive path already exists: {error.filename or self.archive_path}",
                "RUN_ARCHIVE_COLLISION",
            ) from error
        except OSError as error:
            cleanup_probe()
            raise RunPathError(
                f"run artifact path cannot be created: {error.filename or self.path}: {error}",
                "RUN_PATH_CREATION_FAILED",
            ) from error

    @property
    def telemetry_path(self) -> Path:
        return self.root / TELEMETRY_FILE

    @property
    def label_path(self) -> Path:
        return self.root / LABEL_FILE

    def write_bytes(self, name: str, data: bytes) -> Path:
        target = self.path / name
        temporary = self.path / f".{name}.tmp"
        with open(temporary, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        return target

    def write_text(self, name: str, text: str) -> Path:
        return self.write_bytes(name, text.encode("utf-8"))

    def write_json(self, name: str, payload: Any) -> Path:
        if name in {"state.json", "result.json", "resolved.json"} and isinstance(payload, dict):
            if name in {"state.json", "result.json"} and "run_layout" not in payload:
                payload["run_layout"] = dict(self.run_layout)
            from controller_generation import provenance, note_state
            generation = provenance(self.run_id)
            if generation is not None:
                payload["controller_generation"] = generation
            if name in {"state.json", "result.json"}:
                note_state(payload)
        return self.write_text(
            name, json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
        )


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stage_meta(
    stage: str,
    role: str,
    provider: str,
    profile: str,
    argv: list[str],
    prompt: bytes,
    result: Any,
    candidate: dict[str, Any] | None,
) -> dict[str, Any]:
    """Stage record. Carries no environment dump and no secret-bearing values."""
    return {
        "stage": stage,
        "role": role,
        "provider": provider,
        "profile": profile,
        "argv": list(argv),
        "prompt_sha256": digest(prompt),
        "prompt_bytes": len(prompt),
        "stdout_sha256": digest(result.stdout),
        "stdout_bytes": len(result.stdout),
        "exit_code": result.exit_code,
        "truncated": result.truncated,
        "stderr_truncated": result.stderr_truncated,
        "cleanup": getattr(result, "cleanup", None),
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(result.started)),
        "ended_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(result.ended)),
        "duration_seconds": round(result.ended - result.started, 3),
        "candidate": candidate,
    }
