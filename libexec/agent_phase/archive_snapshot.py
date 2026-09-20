"""Bounded, no-follow snapshots of dispatcher evidence, excluding owned runtimes."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat

from .runtime_exclusion import disposable_runtime


MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 128 * 1024 * 1024
MAX_ENTRIES = 20_000
MAX_DEPTH = 32
MAX_PATH_BYTES = 1024
MANIFEST = "TRANSPORT-MANIFEST.json"
CORE = ("request.json", "resolved.json", "state.json", "result.json")


class ArchiveError(RuntimeError):
    """An archive failure with bounded, run-relative diagnostics."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = "".join(c if c.isprintable() else "?" for c in detail)[:1200]
        super().__init__(f"{code}: {self.detail}")


def exclusion(relative: Path) -> str | None:
    parts = relative.parts
    runtime = disposable_runtime(relative)
    if runtime:
        return runtime
    if any(p == "__MACOSX" or p == ".DS_Store" or p.startswith("._") for p in parts):
        return "macOS metadata; descendants not observed"
    if relative.suffix.lower() == ".zip":
        return "nested transport; descendants not observed"
    return None


def identity(info: os.stat_result) -> tuple[int, ...]:
    # Directory membership is compared by the bounded selected-path inventory.
    # Cache/metadata changes under excluded names must not invalidate evidence.
    if stat.S_ISDIR(info.st_mode):
        return (info.st_dev, info.st_ino, info.st_mode)
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def open_directory(path, *, dir_fd=None) -> int:
    return os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=dir_fd)


class Snapshot:
    """All selected bytes are required; exceeding a limit fails without truncation."""

    def __init__(self, source: Path, required=CORE) -> None:
        self.source = source
        self.files: dict[str, bytes] = {}
        self.directories: list[str] = []
        self.observed: dict[str, tuple[int, ...]] = {}
        self.excluded: list[dict[str, str]] = []
        self.total = 0
        self.entries = 0
        self.required = tuple(required)
        self.source_issues: list[dict[str, str]] = []
        self.source_issue_omissions = 0
        self.verification: list[dict[str, object]] = []
        self._scan(False)
        missing = [name for name in self.required if name not in self.files]
        if missing:
            raise ArchiveError("RUN_ARCHIVE_MISSING_REQUIRED", ", ".join(missing))
        self._validate_core()

    def _validate_core(self) -> None:
        for name in self.required:
            try:
                record = json.loads(self.files[name])
                if not isinstance(record, dict):
                    raise ValueError("not an object")
            except ValueError as error:
                raise ArchiveError("RUN_ARCHIVE_FAILED", f"invalid core JSON: {name}") from error
            # An unperformed terminal stage has no terminal result. Preserve
            # that source observation without inventing a required artifact.
            issues = record.get("artifact_reference_issues") or []
            if not isinstance(issues, list):
                raise ArchiveError("RUN_ARCHIVE_FAILED", f"invalid source observations: {name}")
            self.source_issue_omissions += max(0, len(issues) - 256)
            for issue in issues[:256]:
                if isinstance(issue, dict):
                    observed = {key: str(issue.get(key, ""))[:200]
                                for key in ("pointer", "reason")}
                    if observed not in self.source_issues:
                        self.source_issues.append(observed)
            references = record.get("artifact_references") or {}
            if not isinstance(references, dict):
                raise ArchiveError("RUN_ARCHIVE_FAILED", f"invalid artifact references: {name}")
            for group in references.values():
                for item in group if isinstance(group, list) else [group]:
                    if isinstance(item, dict) and isinstance(item.get("name"), str):
                        self._require_file(item["name"])
            for key, binding in record.items():
                if key.endswith("_binding") and isinstance(binding, dict):
                    path = binding.get("relative_path")
                    if isinstance(path, str):
                        data = self._require_file(path)
                        if (binding.get("bytes") is not None
                                and (type(binding["bytes"]) is not int
                                     or binding["bytes"] != len(data))):
                            raise ArchiveError("RUN_ARCHIVE_INTEGRITY", f"binding length mismatch: {path}")
                        if (binding.get("sha256") is not None
                                and hashlib.sha256(data).hexdigest() != binding["sha256"]):
                            raise ArchiveError("RUN_ARCHIVE_INTEGRITY", f"binding digest mismatch: {path}")

    def _require_file(self, name: str) -> bytes:
        if name not in self.files:
            # Do not echo an untrusted pointer which could be an absolute path.
            raise ArchiveError("RUN_ARCHIVE_MISSING_REQUIRED", "referenced evidence is absent from selection")
        return self.files[name]

    def _scan(self, verify: bool) -> None:
        try:
            descriptor = open_directory(self.source)
            try:
                seen: dict[str, tuple[int, ...]] = {}
                seen["."] = identity(os.fstat(descriptor))
                self._walk(descriptor, Path(), seen, verify)
                if verify:
                    membership = sorted(set(seen) ^ set(self.observed))
                    if membership:
                        self._changed("membership_changed", membership[0])
                    for key, current in seen.items():
                        previous = self.observed[key]
                        if current[2] != previous[2]:
                            self._changed("mode_or_type_changed", key)
                        if key not in self.files and current != previous:
                            self._changed("mode_or_type_changed", key)
                        if key in self.files and current != previous:
                            self.verification.append({
                                "category": "metadata_only_changed", "path": key,
                                "same_content_replacement": current[:2] != previous[:2],
                            })
                if not verify:
                    self.observed = seen
            finally:
                os.close(descriptor)
        except OSError as error:
            raise ArchiveError("RUN_ARCHIVE_FAILED", "cannot read run root (OS error)") from error

    def _names(self, descriptor: int, relative: Path) -> list[str]:
        names = []
        with os.scandir(descriptor) as entries:
            for entry in entries:
                self.entries += 1
                if self.entries > MAX_ENTRIES:
                    raise ArchiveError("RUN_ARCHIVE_LIMIT", f"entry limit {MAX_ENTRIES} at {relative}")
                names.append(entry.name)
        return sorted(names, key=lambda name: (name not in CORE, name))

    def _walk(self, descriptor: int, relative: Path, seen: dict, verify: bool) -> None:
        for name in self._names(descriptor, relative):
            child = relative / name
            key = child.as_posix()
            if len(child.parts) > MAX_DEPTH or len(os.fsencode(key)) > MAX_PATH_BYTES:
                raise ArchiveError("RUN_ARCHIVE_LIMIT", f"path/depth limit at {key}")
            reason = exclusion(child)
            if reason:
                if not verify:
                    self.excluded.append({"path": key, "reason": reason})
                continue
            if key == MANIFEST:
                raise ArchiveError("RUN_ARCHIVE_COLLISION", f"reserved generated artifact: {key}")
            try:
                info = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
                seen[key] = identity(info)
                if verify and key not in self.observed:
                    self._changed("membership_changed", key)
                if verify and key in self.observed and info.st_mode != self.observed[key][2]:
                    self._changed("mode_or_type_changed", key)
                self._node(descriptor, child, info, seen, verify)
            except OSError as error:
                if verify and isinstance(error, FileNotFoundError):
                    self._changed("membership_changed", key)
                raise ArchiveError("RUN_ARCHIVE_FAILED", f"cannot read artifact: {key} (OS error)") from error

    def _node(self, descriptor: int, child: Path, info, seen: dict, verify: bool) -> None:
        key = child.as_posix()
        if stat.S_ISDIR(info.st_mode):
            nested = open_directory(child.name, dir_fd=descriptor)
            try:
                if identity(os.fstat(nested)) != identity(info):
                    raise ArchiveError("RUN_ARCHIVE_CHANGED", f"directory changed: {key}")
                if not verify:
                    self.directories.append(key)
                self._walk(nested, child, seen, verify)
            finally:
                os.close(nested)
        elif stat.S_ISREG(info.st_mode):
            data = self._read(descriptor, child, info)
            if verify:
                if key in self.files and (
                    len(data) != len(self.files[key])
                    or hashlib.sha256(data).digest() != hashlib.sha256(self.files[key]).digest()
                ):
                    self._changed("content_changed", key)
            else:
                self.files[key] = data
        else:
            raise ArchiveError("RUN_ARCHIVE_FAILED", f"unsupported run artifact node: {key}")

    def _read(self, descriptor: int, child: Path, info) -> bytes:
        key = child.as_posix()
        if info.st_size > MAX_FILE_BYTES or self.total + info.st_size > MAX_TOTAL_BYTES:
            raise ArchiveError(
                "RUN_ARCHIVE_LIMIT",
                f"required evidence byte limit at {key}; file={info.st_size}/{MAX_FILE_BYTES}, "
                f"selected={self.total}, total_limit={MAX_TOTAL_BYTES}; retain full local run",
            )
        fd = os.open(child.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)
        with os.fdopen(fd, "rb") as handle:
            opened = os.fstat(handle.fileno())
            if opened.st_mode != info.st_mode:
                self._changed("mode_or_type_changed", key)
            if opened.st_size != info.st_size:
                self._changed("content_changed", key)
            data = handle.read(info.st_size + 1)
            final = os.fstat(handle.fileno())
            if final.st_mode != info.st_mode:
                self._changed("mode_or_type_changed", key)
            if len(data) != info.st_size or final.st_size != info.st_size:
                self._changed("content_changed", key)
        self.total += len(data)
        return data

    def _changed(self, category: str, key: str) -> None:
        diagnostic = {"category": category, "path": key}
        self.verification.append(diagnostic)
        error = ArchiveError("RUN_ARCHIVE_CHANGED", f"{category}: {key}")
        error.verification = list(self.verification)
        raise error

    def verify_unchanged(self) -> list[dict[str, object]]:
        self.entries = 0
        selected_total = self.total
        self.total = 0
        self.verification = []
        try:
            self._scan(True)
        finally:
            self.total = selected_total
        return list(self.verification)

    def manifest(self, purpose: str) -> dict:
        return {
            "schema": "agent-phase-transport-v1", "purpose": purpose,
            "review_only": True, "resume_authority": "full original local run",
            "source_leaf": self.source.name,
            "source_records": "byte-identical source attempt; transport status is separate",
            "included": [{"path": name, "bytes": len(data),
                          "sha256": hashlib.sha256(data).hexdigest(),
                          "mode": self.observed[name][2]}
                         for name, data in sorted(self.files.items())],
            "excluded": self.excluded, "directories": self.directories,
            "selected_count": len(self.files), "selected_bytes": self.total,
            "limits": {"file_bytes": MAX_FILE_BYTES, "total_bytes": MAX_TOTAL_BYTES,
                       "entries": MAX_ENTRIES, "depth": MAX_DEPTH, "path_bytes": MAX_PATH_BYTES},
            "size_count_omissions": [], "missing_required": [],
            "source_artifact_observations": self.source_issues,
            "source_issue_records_not_inspected": self.source_issue_omissions,
            "required": list(self.required),
            "observation_limitations": [
                "Excluded descendants are not enumerated, counted, read or hashed.",
                "Directory names do not sanitize content; selected evidence must already be safe to share.",
                "Content verification allows same-mode, same-byte regular-file replacement; it is not a filesystem transaction or hostile-writer confinement.",
            ],
        }


def encoded(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8")


def load_record(source: Path, name: str) -> dict:
    """Read one bounded core record through a no-follow directory descriptor."""
    try:
        root = open_directory(source)
        try:
            info = os.stat(name, dir_fd=root, follow_symlinks=False)
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_FILE_BYTES:
                raise ArchiveError("RUN_ARCHIVE_FAILED", f"invalid core record: {name}")
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root)
            with os.fdopen(fd, "rb") as handle:
                raw = handle.read(info.st_size + 1)
                if len(raw) != info.st_size or identity(os.fstat(handle.fileno())) != identity(info):
                    raise ArchiveError("RUN_ARCHIVE_CHANGED", f"core record changed: {name}")
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError("not an object")
            return value
        finally:
            os.close(root)
    except FileNotFoundError as error:
        raise ArchiveError("RUN_ARCHIVE_MISSING_REQUIRED", f"missing core record: {name}") from error
    except (OSError, ValueError) as error:
        raise ArchiveError("RUN_ARCHIVE_FAILED", f"cannot read core record: {name}") from error


def dry_run_required(source: Path) -> tuple[str, ...]:
    state = load_record(source, "state.json")
    return CORE[:-1] if state.get("dry_run") is True else CORE
