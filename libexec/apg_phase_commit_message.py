"""Deterministic validation for APG formal-phase commit messages."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Sequence


COMMAND_NAME = "apg-check-phase-commit-message"
PHASE = re.compile(r"APG(?:-TEST[0-9]+|[0-9]+[A-Z]?)\Z")
OBJECT_ID = re.compile(rb"[0-9a-f]{40}(?:[0-9a-f]{24})?\n?\Z")
HEADINGS = ("Scope:", "Result:", "Verification:", "Not run:")
EXIT_COMPLIANT = 0
EXIT_NONCOMPLIANT = 1
EXIT_USAGE = 2
EXIT_REPOSITORY = 3
GIT_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class Diagnostic:
    """One content-free commit-message diagnostic."""

    code: str
    invariant: str
    message: str
    action: str

    def json_value(self) -> dict[str, str]:
        return {
            "action": self.action,
            "code": self.code,
            "invariant": self.invariant,
            "message": self.message,
        }


@dataclass(frozen=True)
class ValidationResult:
    """Complete validation result for one expected phase."""

    phase: str
    diagnostics: tuple[Diagnostic, ...]

    @property
    def passed(self) -> bool:
        return not self.diagnostics


class RepositoryFailure(Exception):
    """A bounded source or Git failure safe to render without raw details."""

    def __init__(self, diagnostic: Diagnostic) -> None:
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic


def phase_argument(value: str) -> str:
    """Require the canonical spelling of an APG semantic phase ID."""

    if PHASE.fullmatch(value) is None:
        raise argparse.ArgumentTypeError(
            "phase must use canonical APG<number>[suffix] or APG-TEST<number> form"
        )
    return value


def revision_argument(value: str) -> str:
    """Reject empty, unbounded, or control-bearing revision operands."""

    if not value or len(value) > 1024:
        raise argparse.ArgumentTypeError("revision must contain 1 to 1024 characters")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise argparse.ArgumentTypeError("revision must not contain control characters")
    return value


def _diagnostic(
    code: str,
    invariant: str,
    message: str,
    action: str,
) -> Diagnostic:
    return Diagnostic(code, invariant, message, action)


def _decode_message(message: bytes) -> tuple[str | None, list[Diagnostic]]:
    try:
        text = message.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return None, [
            _diagnostic(
                "APGCM001",
                "utf8-message",
                "the commit message is not valid UTF-8",
                "write the formal-phase message as deterministic UTF-8 text",
            )
        ]
    if any(
        (ord(character) < 32 and character != "\n") or ord(character) == 127
        for character in text
    ):
        return None, [
            _diagnostic(
                "APGCM002",
                "safe-control-characters",
                "the commit message contains a disallowed control character",
                "retain line feeds and remove other control characters",
            )
        ]
    return text, []


def _validate_subject(
    phase: str,
    lines: list[str],
    diagnostics: list[Diagnostic],
) -> None:
    if not lines or not lines[0]:
        diagnostics.append(
            _diagnostic(
                "APGCM003",
                "nonempty-message",
                "the commit message is empty",
                "add the required subject and four-section body",
            )
        )
        return
    prefix = f"{phase}: "
    if not lines[0].startswith(prefix):
        diagnostics.append(
            _diagnostic(
                "APGCM004",
                "canonical-phase-subject",
                "the subject does not begin with the expected canonical phase ID",
                "begin the subject with the supplied phase followed by colon-space",
            )
        )
        return
    if not lines[0][len(prefix) :].strip():
        diagnostics.append(
            _diagnostic(
                "APGCM005",
                "nonempty-subject-result",
                "the subject has no nonempty result",
                "add a concise imperative result after the phase prefix",
            )
        )


def _validate_sections(lines: list[str], diagnostics: list[Diagnostic]) -> None:
    if len(lines) < 3 or lines[1] != "" or lines[2] == "":
        diagnostics.append(
            _diagnostic(
                "APGCM006",
                "subject-body-separator",
                "the subject and body are not separated by exactly one blank line",
                "place one blank line between the subject and Scope heading",
            )
        )

    positions: list[int] = []
    cardinality_passed = True
    for heading in HEADINGS:
        matches = [index for index, line in enumerate(lines) if line == heading]
        if len(matches) != 1:
            cardinality_passed = False
            diagnostics.append(
                _diagnostic(
                    "APGCM007",
                    "section-cardinality",
                    f"the {heading[:-1]} section heading occurs {len(matches)} times",
                    "include each required section heading exactly once",
                )
            )
        else:
            positions.append(matches[0])
    if not cardinality_passed:
        return

    if positions != sorted(positions) or positions[0] != 2:
        diagnostics.append(
            _diagnostic(
                "APGCM008",
                "section-order",
                "the four section headings are not in the required order",
                "order Scope, Result, Verification, and Not run after the separator",
            )
        )
        return

    for index, heading in enumerate(HEADINGS):
        start = positions[index] + 1
        end = positions[index + 1] if index + 1 < len(positions) else len(lines)
        content = [line for line in lines[start:end] if line]
        if not content:
            diagnostics.append(
                _diagnostic(
                    "APGCM009",
                    "nonempty-section",
                    f"the {heading[:-1]} section has no nonempty entry",
                    "add at least one nonempty list entry to the section",
                )
            )
            continue
        if any(not line.startswith("- ") or not line[2:].strip() for line in content):
            diagnostics.append(
                _diagnostic(
                    "APGCM010",
                    "section-entry-form",
                    f"the {heading[:-1]} section contains a malformed entry",
                    "use one or more nonempty entries beginning with dash-space",
                )
            )


def validate_message(phase: str, message: bytes) -> ValidationResult:
    """Validate raw message bytes against the APG formal-phase contract."""

    text, diagnostics = _decode_message(message)
    if text is None:
        return ValidationResult(phase, tuple(diagnostics))
    normalized = text.rstrip("\n")
    lines = normalized.split("\n") if normalized else []
    _validate_subject(phase, lines, diagnostics)
    _validate_sections(lines, diagnostics)
    return ValidationResult(phase, tuple(diagnostics))


def render_json(result: ValidationResult, source: str) -> str:
    """Render one deterministic schema-versioned JSON result."""

    return json.dumps(
        {
            "diagnostics": [item.json_value() for item in result.diagnostics],
            "phase": result.phase,
            "schema_version": 1,
            "source": source,
            "status": "pass" if result.passed else "fail",
        },
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"


def render_text(result: ValidationResult, source: str) -> str:
    """Render one deterministic human-readable validation result."""

    if result.passed:
        return f"PASS APG phase commit message: {result.phase} ({source})\n"
    lines = [
        f"{item.code} {item.invariant}: {item.message}; action: {item.action}"
        for item in result.diagnostics
    ]
    noun = "diagnostic" if len(lines) == 1 else "diagnostics"
    lines.append(
        f"FAIL APG phase commit message: {result.phase} ({source}); "
        f"{len(result.diagnostics)} {noun}"
    )
    return "\n".join(lines) + "\n"


def _repository_error_json(phase: str, source: str, item: Diagnostic) -> str:
    return json.dumps(
        {
            "diagnostics": [item.json_value()],
            "phase": phase,
            "schema_version": 1,
            "source": source,
            "status": "error",
        },
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"


def _repository_error_text(phase: str, source: str, item: Diagnostic) -> str:
    return (
        f"ERROR APG phase commit message: {phase} ({source}); "
        f"{item.code} {item.invariant}: {item.message}; action: {item.action}\n"
    )


def _read_message_file(path: Path) -> bytes:
    try:
        if not path.is_file() or path.is_symlink():
            raise OSError("unsafe message source")
        return path.read_bytes()
    except OSError as error:
        raise RepositoryFailure(
            _diagnostic(
                "APGCMR002",
                "message-file-source",
                "the message file is unreadable or is not a regular file",
                "supply a readable regular non-symlink message file",
            )
        ) from error


def _git_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_PAGER": "cat",
            "LC_ALL": "C",
            "LANG": "C",
        }
    )
    return environment


def _run_git(arguments: Sequence[str]) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            ["git", "--no-pager", *arguments],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_git_environment(),
            shell=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RepositoryFailure(
            _diagnostic(
                "APGCMR001",
                "git-commit-source",
                "Git could not supply a commit message from the current repository",
                "run inside the intended repository with a resolvable commit revision",
            )
        ) from error


def _read_commit_message(revision: str) -> bytes:
    resolved = _run_git(
        ("rev-parse", "--verify", "--quiet", "--end-of-options", f"{revision}^{{commit}}")
    )
    if resolved.returncode != 0 or OBJECT_ID.fullmatch(resolved.stdout) is None:
        raise RepositoryFailure(
            _diagnostic(
                "APGCMR001",
                "git-commit-source",
                "the revision does not resolve to a commit in the current repository",
                "supply a commit revision from the intended repository",
            )
        )
    object_id = resolved.stdout.strip().decode("ascii")
    commit = _run_git(("cat-file", "commit", object_id))
    if commit.returncode != 0 or b"\n\n" not in commit.stdout:
        raise RepositoryFailure(
            _diagnostic(
                "APGCMR001",
                "git-commit-source",
                "Git did not return a complete commit object",
                "verify repository integrity and supply a valid commit revision",
            )
        )
    return commit.stdout.split(b"\n\n", 1)[1]


def build_parser() -> argparse.ArgumentParser:
    """Build the bounded public command surface."""

    parser = argparse.ArgumentParser(
        prog=COMMAND_NAME,
        description=(
            "Validate one APG formal-phase commit message before or after commit."
        ),
    )
    parser.add_argument("--phase", required=True, type=phase_argument, metavar="PHASE-ID")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--message-file", type=Path, metavar="PATH")
    source.add_argument("--commit", type=revision_argument, metavar="REVISION")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="deterministic output format (default: text)",
    )
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    """Run the checker and return its documented exit class."""

    options = build_parser().parse_args(arguments)
    source = "message-file" if options.message_file is not None else "commit"
    try:
        message = (
            _read_message_file(options.message_file)
            if options.message_file is not None
            else _read_commit_message(options.commit)
        )
    except RepositoryFailure as error:
        output = (
            _repository_error_json(options.phase, source, error.diagnostic)
            if options.format == "json"
            else _repository_error_text(options.phase, source, error.diagnostic)
        )
        sys.stdout.write(output)
        return EXIT_REPOSITORY
    result = validate_message(options.phase, message)
    output = (
        render_json(result, source)
        if options.format == "json"
        else render_text(result, source)
    )
    sys.stdout.write(output)
    return EXIT_COMPLIANT if result.passed else EXIT_NONCOMPLIANT


if __name__ == "__main__":
    raise SystemExit(main())
