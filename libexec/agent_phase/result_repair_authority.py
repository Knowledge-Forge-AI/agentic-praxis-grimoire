"""Structured operator authority for explicit result-repair finalization."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import stat

from . import finalization as finalization_module
from . import result as result_module


MAX_COMMIT_BODY_FILE_BYTES = 64 * 1024


@dataclass(frozen=True)
class OperatorCommitAuthority:
    message: result_module.CommitMessage
    body_source: str

    def as_record(self) -> dict[str, object]:
        return {
            "schema": "agent-phase-result-repair-commit-authority-v1",
            "origin": "structured_operator_authority",
            "subject": self.message.subject,
            "body": self.message.body,
            "body_source": self.body_source,
        }

    def prompt_json(self) -> str:
        return json.dumps(
            {
                "subject": self.message.subject,
                "body": self.message.body,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )


def _fail(code: str, detail: str) -> finalization_module.FinalizationError:
    return finalization_module.FinalizationError(code, detail)


def _identity(info: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_nlink,
        info.st_size,
        info.st_mtime_ns,
    )


def _read_body_file(path: Path) -> str:
    try:
        before = os.lstat(path)
    except FileNotFoundError as error:
        raise _fail(
            "RESULT_REPAIR_COMMIT_BODY_MISSING",
            "operator commit-message body file is missing",
        ) from error
    except OSError as error:
        raise _fail(
            "RESULT_REPAIR_COMMIT_BODY_UNREADABLE",
            "operator commit-message body file cannot be inspected",
        ) from error
    if stat.S_ISLNK(before.st_mode):
        raise _fail(
            "RESULT_REPAIR_COMMIT_BODY_SYMLINK",
            "operator commit-message body file must not be a symbolic link",
        )
    if not stat.S_ISREG(before.st_mode):
        raise _fail(
            "RESULT_REPAIR_COMMIT_BODY_TYPE",
            "operator commit-message body file must be a regular file",
        )
    if before.st_size > MAX_COMMIT_BODY_FILE_BYTES:
        raise _fail(
            "RESULT_REPAIR_COMMIT_BODY_OVERSIZED",
            "operator commit-message body file exceeds the bounded size",
        )
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise _fail(
            "RESULT_REPAIR_COMMIT_BODY_UNREADABLE",
            "operator commit-message body file cannot be opened",
        ) from error
    try:
        opened = os.fstat(descriptor)
        if _identity(opened) != _identity(before) or not stat.S_ISREG(opened.st_mode):
            raise _fail(
                "RESULT_REPAIR_COMMIT_BODY_REPLACED",
                "operator commit-message body file changed while opening",
            )
        chunks: list[bytes] = []
        remaining = MAX_COMMIT_BODY_FILE_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(64 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if len(data) > MAX_COMMIT_BODY_FILE_BYTES:
            raise _fail(
                "RESULT_REPAIR_COMMIT_BODY_OVERSIZED",
                "operator commit-message body file exceeds the bounded size",
            )
        after = os.fstat(descriptor)
        try:
            named_after = os.lstat(path)
        except OSError as error:
            raise _fail(
                "RESULT_REPAIR_COMMIT_BODY_REPLACED",
                "operator commit-message body file disappeared while reading",
            ) from error
        if (
            _identity(after) != _identity(before)
            or _identity(named_after) != _identity(before)
            or len(data) != before.st_size
        ):
            raise _fail(
                "RESULT_REPAIR_COMMIT_BODY_REPLACED",
                "operator commit-message body file changed while reading",
            )
    finally:
        os.close(descriptor)
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise _fail(
            "RESULT_REPAIR_COMMIT_BODY_UTF8",
            "operator commit-message body file is not valid UTF-8",
        ) from error


def load(
    subject: str | None, body_file: Path | None
) -> OperatorCommitAuthority | None:
    if subject is None and body_file is None:
        return None
    if subject is None:
        raise _fail(
            "RESULT_REPAIR_COMMIT_SUBJECT_REQUIRED",
            "operator commit-message body file requires an explicit subject",
        )
    body = "" if body_file is None else _read_body_file(body_file)
    try:
        message = result_module.validate_commit_message(subject, body)
    except result_module.ResultError as error:
        raise _fail(error.code, error.detail) from error
    return OperatorCommitAuthority(
        message=message,
        body_source="empty" if body_file is None else "bounded_body_file",
    )


def require_match(
    authority: OperatorCommitAuthority | None,
    parsed: result_module.CommitMessage | None,
) -> None:
    if authority is None:
        return
    if parsed != authority.message:
        raise _fail(
            "RESULT_REPAIR_COMMIT_MESSAGE_MISMATCH",
            "formatter commit_message did not exactly match structured operator authority",
        )
