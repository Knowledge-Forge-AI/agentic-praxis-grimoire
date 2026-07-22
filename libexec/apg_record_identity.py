"""Read-only mechanical validation for APG phase and record identity."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys
from typing import Sequence


COMMAND_NAME = "apg-check-record-identity"
PHASE_TEXT = r"APG(?:-TEST[0-9]+|[0-9]+[A-Z]?)"
PHASE = re.compile(rf"{PHASE_TEXT}\Z", re.IGNORECASE)
ADR_PATH = re.compile(
    r"docs/adr/[0-9]{4}/[0-9]{2}/(?P<sequence>[0-9]{4})-[^/]+\.md\Z"
)
EXIT_PATH = re.compile(
    rf"docs/status/[0-9]{{4}}/[0-9]{{2}}/[0-9]{{2}}/"
    rf"(?P<sequence>[0-9]{{5}})-(?P<phase>{PHASE_TEXT})-[^/]+-exit\.md\Z",
    re.IGNORECASE,
)
INDEX_ENTRY = re.compile(
    rf"^- \[`(?P<sequence>[0-9]{{5}}) — (?P<phase>{PHASE_TEXT})\b[^`]*`\]"
    rf"\((?P<target>[^)]+)\)$",
    re.IGNORECASE | re.MULTILINE,
)
HEADING = re.compile(
    rf"^# (?P<phase>{PHASE_TEXT})\b.*\bExit\b", re.IGNORECASE | re.MULTILINE
)
EXPLICIT_FIELD = re.compile(
    rf"^Phase ID: `(?P<phase>{PHASE_TEXT})`$", re.IGNORECASE | re.MULTILINE
)


@dataclass(frozen=True)
class Diagnostic:
    """One deterministic record-identity noncompliance diagnostic."""

    code: str
    path: str
    invariant: str
    message: str
    action: str

    def json_value(self) -> dict[str, str]:
        return {
            "action": self.action,
            "code": self.code,
            "invariant": self.invariant,
            "message": self.message,
            "path": self.path,
        }


@dataclass(frozen=True)
class ExitRecord:
    """One exit record and its path-derived identity."""

    path: Path
    relative: str
    sequence: int
    path_phase: str


@dataclass(frozen=True)
class CheckResult:
    """Complete identity result and independently computed next values."""

    diagnostics: tuple[Diagnostic, ...]
    adrs: int
    exits: int
    phase_ids: int
    next_adr: str
    next_exit: str

    @property
    def passed(self) -> bool:
        return not self.diagnostics


def canonical_phase(value: str) -> str:
    """Return the case-insensitive canonical spelling for one phase ID."""

    return value.upper()


def phase_argument(value: str) -> str:
    """Validate and canonicalize one phase ID supplied on the command line."""

    if PHASE.fullmatch(value) is None:
        raise argparse.ArgumentTypeError(
            "phase must match APG<number>[suffix] or APG-TEST<number>"
        )
    return canonical_phase(value)


def add_diagnostic(
    diagnostics: list[Diagnostic],
    code: str,
    path: str,
    invariant: str,
    message: str,
    action: str,
) -> None:
    diagnostics.append(Diagnostic(code, path, invariant, message, action))


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _record_files(root: Path, owner: str) -> tuple[Path, ...]:
    base = root / "docs" / owner
    if not base.is_dir() or base.is_symlink():
        return ()
    return tuple(
        sorted(
            path
            for path in base.rglob("*.md")
            if path.name != "README.md" and path.is_file() and not path.is_symlink()
        )
    )


def check_records(
    root: Path,
    *,
    expect_available: Sequence[str] = (),
    expect_allocated: Sequence[str] = (),
) -> CheckResult:
    """Validate the adopted phase and record identity invariants."""

    root = root.resolve(strict=True)
    if not root.is_dir():
        raise NotADirectoryError(root)
    diagnostics: list[Diagnostic] = []

    adr_directory = root / "docs" / "adr"
    adr_sequences: list[int] = []
    for path in _record_files(root, "adr"):
        relative = _relative(path, root)
        match = ADR_PATH.fullmatch(relative)
        if match is None:
            continue
        adr_sequences.append(int(match.group("sequence")))
    if not adr_directory.is_dir() or adr_directory.is_symlink() or not adr_sequences:
        add_diagnostic(
            diagnostics,
            "APGR001",
            "docs/adr",
            "adr-namespace-present",
            "ADR namespace is missing, unsafe, or contains no assigned records",
            "restore the regular ADR tree and its assigned records",
        )
    for sequence, count in sorted(Counter(adr_sequences).items()):
        if count > 1:
            add_diagnostic(
                diagnostics,
                "APGR002",
                "docs/adr",
                "unique-adr-sequence",
                f"ADR sequence {sequence:04d} is assigned {count} times",
                "assign a unique ADR sequence without comparing exit numbers",
            )

    exits: list[ExitRecord] = []
    for path in _record_files(root, "status"):
        relative = _relative(path, root)
        match = EXIT_PATH.fullmatch(relative)
        if match is None:
            add_diagnostic(
                diagnostics,
                "APGR004",
                relative,
                "exit-path-identity",
                "exit record path does not encode sequence, phase, and exit suffix",
                "rename the record to the adopted exit-record path form",
            )
            continue
        raw_path_phase = match.group("phase")
        if raw_path_phase != raw_path_phase.lower():
            add_diagnostic(
                diagnostics,
                "APGR015",
                relative,
                "lowercase-exit-path-phase",
                "exit path phase token is not lowercase",
                "use the lowercase filename form of the canonical phase ID",
            )
        exits.append(
            ExitRecord(
                path,
                relative,
                int(match.group("sequence")),
                canonical_phase(raw_path_phase),
            )
        )
    status_directory = root / "docs" / "status"
    if not status_directory.is_dir() or status_directory.is_symlink() or not exits:
        add_diagnostic(
            diagnostics,
            "APGR003",
            "docs/status",
            "exit-namespace-present",
            "exit namespace is missing, unsafe, or contains no assigned records",
            "restore the regular status tree and its assigned exit records",
        )

    for sequence, count in sorted(Counter(item.sequence for item in exits).items()):
        if count > 1:
            add_diagnostic(
                diagnostics,
                "APGR005",
                "docs/status",
                "unique-exit-sequence",
                f"exit sequence {sequence:05d} is assigned {count} times",
                "assign a unique exit sequence without comparing ADR numbers",
            )

    status_index = root / "docs" / "status" / "README.md"
    index_is_regular = status_index.is_file() and not status_index.is_symlink()
    if not index_is_regular:
        add_diagnostic(
            diagnostics,
            "APGR006",
            "docs/status/README.md",
            "status-index-present",
            "status index is missing or is not a regular file",
            "restore the regular status index",
        )
    index_text = status_index.read_text(encoding="utf-8") if index_is_regular else ""
    index_entries = tuple(INDEX_ENTRY.finditer(index_text))
    target_counts = Counter(match.group("target") for match in index_entries)
    records_by_path = {item.relative.removeprefix("docs/status/"): item for item in exits}

    for target, count in sorted(target_counts.items()):
        if count != 1:
            add_diagnostic(
                diagnostics,
                "APGR008",
                "docs/status/README.md",
                "exit-index-exactness",
                f"exit target {target!r} is indexed {count} times",
                "index each exit target exactly once",
            )
        if target not in records_by_path:
            add_diagnostic(
                diagnostics,
                "APGR006",
                "docs/status/README.md",
                "indexed-exit-exists",
                f"indexed exit target {target!r} does not exist",
                "restore the target or remove the stale index entry",
            )

    indexed_by_target = {match.group("target"): match for match in index_entries}
    allocated_phases: list[str] = []
    for record in exits:
        allocated_phases.append(record.path_phase)
        target = record.relative.removeprefix("docs/status/")
        match = indexed_by_target.get(target)
        if match is None:
            add_diagnostic(
                diagnostics,
                "APGR007",
                record.relative,
                "exit-index-coverage",
                "exit record is not indexed",
                "add exactly one status-index entry for this record",
            )
            continue

        text = record.path.read_text(encoding="utf-8")
        heading_match = HEADING.search(text)
        field_matches = tuple(EXPLICIT_FIELD.finditer(text))
        if record.sequence >= 29 and len(field_matches) != 1:
            add_diagnostic(
                diagnostics,
                "APGR009",
                record.relative,
                "explicit-phase-field",
                f"new exit record has {len(field_matches)} explicit Phase ID fields",
                "add exactly one Phase ID field agreeing with the record identity",
            )

        index_sequence = int(match.group("sequence"))
        identities = [
            record.path_phase,
            canonical_phase(match.group("phase")),
        ]
        if heading_match is not None:
            identities.append(canonical_phase(heading_match.group("phase")))
        if len(field_matches) == 1:
            identities.append(canonical_phase(field_matches[0].group("phase")))
        canonical_spellings = [match.group("phase")]
        if heading_match is not None:
            canonical_spellings.append(heading_match.group("phase"))
        canonical_spellings.extend(
            field_match.group("phase") for field_match in field_matches
        )
        if any(value != canonical_phase(value) for value in canonical_spellings):
            add_diagnostic(
                diagnostics,
                "APGR014",
                record.relative,
                "canonical-phase-spelling",
                "index, H1, or Phase ID field uses non-uppercase phase spelling",
                "use the canonical uppercase phase ID outside the lowercase path slug",
            )
        if (
            index_sequence != record.sequence
            or heading_match is None
            or len(set(identities)) != 1
        ):
            add_diagnostic(
                diagnostics,
                "APGR010",
                record.relative,
                "phase-identity-agreement",
                "path, index, H1, sequence, or explicit phase identity disagree",
                "make the path, index, H1, and Phase ID field agree",
            )

    for phase, count in sorted(Counter(allocated_phases).items()):
        if count > 1:
            add_diagnostic(
                diagnostics,
                "APGR011",
                "docs/status",
                "unique-canonical-phase",
                f"canonical phase ID {phase} is allocated {count} times",
                "give every exit record one case-insensitively unique phase ID",
            )

    allocated = set(allocated_phases)
    for phase in sorted(set(expect_allocated)):
        if phase not in allocated:
            add_diagnostic(
                diagnostics,
                "APGR012",
                "docs/status",
                "expected-phase-allocation",
                f"expected phase {phase} is not allocated",
                "allocate the phase or correct the expectation",
            )
    for phase in sorted(set(expect_available)):
        if phase in allocated:
            add_diagnostic(
                diagnostics,
                "APGR013",
                "docs/status",
                "expected-phase-availability",
                f"expected phase {phase} is already allocated",
                "choose an available phase or correct the expectation",
            )

    ordered = tuple(
        sorted(diagnostics, key=lambda item: (item.path, item.code, item.message))
    )
    return CheckResult(
        ordered,
        len(adr_sequences),
        len(exits),
        len(allocated),
        f"{max(adr_sequences, default=0) + 1:04d}",
        f"{max((item.sequence for item in exits), default=0) + 1:05d}",
    )


def _summary(result: CheckResult) -> dict[str, int | str]:
    return {
        "adrs": result.adrs,
        "exits": result.exits,
        "next_adr": result.next_adr,
        "next_exit": result.next_exit,
        "phase_ids": result.phase_ids,
    }


def render_json(result: CheckResult) -> str:
    """Render deterministic schema-versioned JSON."""

    return json.dumps(
        {
            "diagnostics": [item.json_value() for item in result.diagnostics],
            "schema_version": 1,
            "status": "pass" if result.passed else "fail",
            "summary": _summary(result),
        },
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"


def render_text(result: CheckResult) -> str:
    """Render deterministic human-readable output."""

    counts = (
        f"{result.adrs} ADRs, {result.exits} exits, {result.phase_ids} phase IDs; "
        f"next ADR {result.next_adr}; next exit {result.next_exit}"
    )
    if result.passed:
        return f"PASS APG record identity: {counts}\n"
    lines = [
        f"{item.path} {item.code} {item.invariant}: {item.message}; action: {item.action}"
        for item in result.diagnostics
    ]
    noun = "diagnostic" if len(lines) == 1 else "diagnostics"
    lines.append(f"FAIL APG record identity: {len(lines)} {noun}, {counts}")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    """Build the bounded public command surface."""

    parser = argparse.ArgumentParser(
        prog=COMMAND_NAME,
        description=(
            "Validate APG ADR, exit-record, and semantic phase identity without "
            "repair, Git, network access, or cross-namespace sequence comparison."
        ),
    )
    parser.add_argument(
        "--root",
        type=Path,
        help="APG-shaped repository root (default: repository containing command)",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="deterministic output format (default: text)",
    )
    parser.add_argument(
        "--expect-available",
        action="append",
        default=[],
        type=phase_argument,
        metavar="PHASE",
        help="require a canonical phase ID to remain unallocated; repeatable",
    )
    parser.add_argument(
        "--expect-allocated",
        action="append",
        default=[],
        type=phase_argument,
        metavar="PHASE",
        help="require a canonical phase ID to be allocated; repeatable",
    )
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    """Run the checker and return its documented exit status."""

    parser = build_parser()
    options = parser.parse_args(arguments)
    default_root = Path(__file__).resolve(strict=True).parent.parent
    try:
        result = check_records(
            options.root if options.root is not None else default_root,
            expect_available=options.expect_available,
            expect_allocated=options.expect_allocated,
        )
    except (FileNotFoundError, NotADirectoryError, OSError, UnicodeError) as error:
        parser.error(f"could not inspect repository root: {error}")
    output = render_json(result) if options.format == "json" else render_text(result)
    sys.stdout.write(output)
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
