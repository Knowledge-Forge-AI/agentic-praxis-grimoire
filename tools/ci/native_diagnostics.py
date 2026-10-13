"""Bounded, sanitized command-failure evidence for hosted native lanes."""
from __future__ import annotations

import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

OUTPUT_LIMIT = 16 * 1024
SECRET_NAME = re.compile(r"token|secret|password|credential|private|[-_]key", re.I)
ANSI = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")
GO_FAILURE = re.compile(r"--- FAIL|^FAIL(?:\s|$)|panic:|^# |\S+\.go:\d+:|\[build failed\]")


def _clean_text(value: str | bytes | None) -> str:
    text = value.decode("utf-8", errors="replace") if isinstance(value, bytes) else (value or "")
    text = ANSI.sub("", text)
    return "".join(c for c in text if c in "\n\t" or (ord(c) >= 32 and not 127 <= ord(c) <= 159))


def sanitize(value: str | bytes | None, environment: Mapping[str, str] | None = None) -> str:
    """Redact before bounding; never emit an environment inventory."""
    environment = os.environ if environment is None else environment
    text = _clean_text(value)
    secrets = [_clean_text(v) for k, v in environment.items() if SECRET_NAME.search(k) and len(v) >= 4]
    for secret in sorted(secrets, key=len, reverse=True):
        if secret:
            text = text.replace(secret, "<redacted>")
    text = re.sub(r"\b(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]+", "<redacted>", text)
    text = re.sub(r"(?i)(\bauthorization\s*[:=]\s*)(?:(?:basic|bearer|token)\s+)?[^\s,;]+",
                  r"\1<redacted>", text)
    text = re.sub(r"(?i)(\bbearer\s+)[^\s,;]+", r"\1<redacted>", text)
    for key in ("GITHUB_WORKSPACE", "RUNNER_TEMP", "HOME"):
        path = environment.get(key, "")
        if len(path) >= 4:
            text = text.replace(path, f"<{key}>")
    text = re.sub(r"/(?:Users|home)/[^/\s]+", "/<user>", text)
    # Child text must not become an Actions workflow command when printed.
    return re.sub(r"(?m)^(\s*)::", r"\1: :", text)


def bounded(value: str, *, tail: bool = False, limit: int = OUTPUT_LIMIT) -> tuple[str, bool]:
    encoded = value.encode("utf-8")
    truncated = len(encoded) > limit
    kept = encoded[-limit:] if tail else encoded[:limit]
    return kept.decode("utf-8", errors="ignore"), truncated


def _command(args: list[str], environment: Mapping[str, str]) -> str:
    parts = [Path(args[0]).name]
    redact_next = False
    for arg in args[1:]:
        parts.append("<redacted>" if redact_next else arg)
        redact_next = bool(arg.startswith("-") and SECRET_NAME.search(arg) and "=" not in arg)
        if arg.startswith("-") and SECRET_NAME.search(arg) and "=" in arg:
            parts[-1] = arg.split("=", 1)[0] + "=<redacted>"
    return bounded(sanitize(" ".join(parts), environment), limit=2048)[0]


def command_diagnostics(args: list[str], returncode: int | None, stdout: str | bytes | None,
                        stderr: str | bytes | None, environment: Mapping[str, str]) -> dict[str, Any]:
    stdout_text, stderr_text = sanitize(stdout, environment), sanitize(stderr, environment)
    stdout_tail, stdout_truncated = bounded(stdout_text, tail=True)
    stderr_tail, stderr_truncated = bounded(stderr_text, tail=True)
    extract, extract_truncated = bounded("\n".join(
        line for line in (stdout_text + "\n" + stderr_text).splitlines() if GO_FAILURE.search(line)))
    return {"command": _command(args, environment), "returncode": returncode,
            "timed_out": returncode is None, "stdout_tail": stdout_tail, "stderr_tail": stderr_tail,
            "stdout_truncated": stdout_truncated, "stderr_truncated": stderr_truncated,
            "failure_extract": extract, "failure_extract_truncated": extract_truncated}


def command_message(details: dict[str, Any]) -> str:
    status = "timeout" if details["timed_out"] else str(details["returncode"])
    return (f"{details['command']} failed ({status})\n"
            f"stdout tail:\n{details['stdout_tail']}\nstderr tail:\n{details['stderr_tail']}\n"
            f"failure extract:\n{details['failure_extract']}")


def failure_record(error: Exception, lane: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    if details is None:
        message, truncated = bounded(sanitize(str(error)))
        details = {"message": message, "message_truncated": truncated}
    return {"schema": "apgr.native-lane-failure/v1", "status": "failed", "lane": lane,
            "exception_type": type(error).__name__, **details}
