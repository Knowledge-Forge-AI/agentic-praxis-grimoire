"""Command-line adapters for the three Python agent-report entry points."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import signal
import sys
from functools import partial
from typing import Callable, Sequence

from .diff import collect_diff_report
from .git_adapter import GitAdapter, GitError
from .operational import (
    build_operational_record,
    load_operational_source,
    validate_related_git_report_id,
)
from .rendering import build_record
from .safety import (
    Destination,
    MAX_SOURCE_BYTES,
    ReportError,
    UsageError,
    private_temporary_directory,
    read_validated_source,
    source_value_is_absolute,
    testing_pause,
    validate_metadata,
    validate_source_path,
    validate_status_doc,
    validate_ticket,
)
from .show import collect_show_report, validate_commit_input


SHOW_USAGE = """Usage: git-show-report <ticket-id> <commit-hash> <status-doc-path-from-repo-root> <result> <final-gate>

Append one complete version-2 Git commit report to the current APGR phase outbox:
  ~/Documents/agent/outbox/<repo-name>/<ticket-id>/<ticket-id>.git.show.report.txt

Environment:
  APGR_OUTBOX_ROOT      Override the canonical outbox root directory.
  GIT_SHOW_REPORT_ROOT  Retain the legacy omnibus destination and append semantics.
"""

DIFF_USAGE = """Usage: git-diff-report <phase-id> <result> <final-gate> [--status-doc <repository-relative-path>]

Append one complete version-1 uncommitted Git snapshot report to the current APGR phase outbox:
  ~/Documents/agent/outbox/<repo-name>/<phase-id>/<phase-id>.git.diff.report.txt

Environment:
  APGR_OUTBOX_ROOT      Override the canonical outbox root directory.
  GIT_SHOW_REPORT_ROOT  Retain the legacy omnibus destination and append semantics.
"""

OPERATIONAL_USAGE = """Usage: append-operational-report <ticket-id> <operational-report-path> <result> <final-gate> [options]

Append one complete operational-report record to the current APGR phase outbox:
  ~/Documents/agent/outbox/<repo-name>/<ticket-id>/<ticket-id>.ops.report.txt
  (or inside the current Git show/diff primary when one exists)

Options:
  --related-commit <commit>
  --related-git-report-id <GIT-SHOW-REPORT-id|GIT-DIFF-REPORT-id>
  -h, --help

Environment:
  APGR_OUTBOX_ROOT      Override the canonical outbox root directory.
  GIT_SHOW_REPORT_ROOT  Retain the legacy omnibus destination and append semantics.
"""


@dataclass(frozen=True, slots=True)
class OperationalArguments:
    phase: str
    source_value: str
    result: str
    final_gate: str
    related_commit_input: str
    related_git_report_id: str


class _UsageAlreadyRendered(Exception):
    """Signal exit 2 after a compatibility usage block was already written."""


def _destination(git_root: Path, phase: str, outbox_root: Path | None) -> Destination:
    """Construct a destination without changing the legacy call shape by default."""

    if outbox_root is None:
        return Destination(git_root, phase)
    return Destination(git_root, phase, outbox_root=outbox_root)


def git_show_main(
    arguments: Sequence[str] | None = None,
    *,
    outbox_root: Path | None = None,
) -> int:
    """Run the compatible Git-show CLI."""

    values = sys.argv[1:] if arguments is None else arguments
    return _run(
        "git-show-report",
        partial(_git_show, outbox_root=outbox_root),
        list(values),
    )


def git_diff_main(
    arguments: Sequence[str] | None = None,
    *,
    outbox_root: Path | None = None,
) -> int:
    """Run the uncommitted Git-diff CLI."""

    values = sys.argv[1:] if arguments is None else arguments
    return _run(
        "git-diff-report",
        partial(_git_diff, outbox_root=outbox_root),
        list(values),
    )


def append_operational_main(
    arguments: Sequence[str] | None = None,
    *,
    outbox_root: Path | None = None,
) -> int:
    """Run the operational append CLI."""

    values = sys.argv[1:] if arguments is None else arguments
    return _run(
        "append-operational-report",
        partial(_append_operational, outbox_root=outbox_root),
        list(values),
    )


def _run(command_name: str, command: Callable[[list[str]], int], arguments: list[str]) -> int:
    previous_umask = os.umask(0o077)
    deterministic_environment = {
        "LC_ALL": "C",
        "LANG": "C",
        "GIT_PAGER": "cat",
        "PAGER": "cat",
    }
    previous_environment = {
        name: os.environ.get(name) for name in deterministic_environment
    }
    os.environ.update(deterministic_environment)
    handled_signals = [signal.SIGTERM]
    if os.name != "nt" and hasattr(signal, "SIGHUP"):
        handled_signals.append(signal.SIGHUP)
    previous = {value: signal.getsignal(value) for value in handled_signals}

    def interrupted(_signum: int, _frame: object) -> None:
        raise InterruptedError

    for value in handled_signals:
        signal.signal(value, interrupted)
    try:
        return command(arguments)
    except _UsageAlreadyRendered:
        return 2
    except UsageError as error:
        print(f"{command_name}: {error}", file=sys.stderr)
        return 2
    except (ReportError, GitError) as error:
        print(f"{command_name}: {error}", file=sys.stderr)
        return 1
    except InterruptedError:
        print(f"{command_name}: interrupted", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print(f"{command_name}: interrupted", file=sys.stderr)
        return 130
    except OSError:
        print(f"{command_name}: filesystem operation failed", file=sys.stderr)
        return 1
    finally:
        for value, handler in previous.items():
            signal.signal(value, handler)
        for name, prior in previous_environment.items():
            if prior is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = prior
        os.umask(previous_umask)


def _git_show(arguments: list[str], *, outbox_root: Path | None = None) -> int:
    if arguments and arguments[0] in {"-h", "--help"}:
        sys.stdout.write(SHOW_USAGE)
        return 0
    if len(arguments) != 5:
        sys.stderr.write(SHOW_USAGE)
        return 2
    phase, commit_input, status_doc, result, final_gate = arguments
    validate_ticket(phase)
    for value in (status_doc, result, final_gate):
        validate_metadata(value)
    try:
        validate_commit_input(commit_input)
    except ValueError as error:
        raise UsageError(str(error)) from error
    git = GitAdapter.discover(Path.cwd())
    with private_temporary_directory("git-show-report"):
        show = collect_show_report(
            git,
            phase=phase,
            commit_input=commit_input,
            status_doc=status_doc,
            result=result,
            final_gate=final_gate,
        )
        destination = _destination(git.root, phase, outbox_root)
        destination.append(build_record(show.record))
    print(f"git-show-report: appended {show.commit} to {destination.path}")
    return 0


def _git_diff(arguments: list[str], *, outbox_root: Path | None = None) -> int:
    if arguments and arguments[0] in {"-h", "--help"}:
        sys.stdout.write(DIFF_USAGE)
        return 0
    if len(arguments) not in {3, 5}:
        sys.stderr.write(DIFF_USAGE)
        return 2
    phase, result, final_gate = arguments[:3]
    status_doc_value: str | None = None
    if len(arguments) == 5:
        if arguments[3] != "--status-doc" or not arguments[4]:
            sys.stderr.write(DIFF_USAGE)
            return 2
        status_doc_value = arguments[4]
    validate_ticket(phase)
    validate_metadata(result)
    validate_metadata(final_gate)
    status_doc = validate_status_doc(status_doc_value)
    git = GitAdapter.discover(Path.cwd())
    with private_temporary_directory("git-diff-report"):
        diff = collect_diff_report(
            git,
            phase=phase,
            result=result,
            final_gate=final_gate,
            status_doc=status_doc,
        )
        destination = _destination(git.root, phase, outbox_root)
        destination.append(build_record(diff.record))
    print(f"git-diff-report: appended {diff.record.record_id} to {destination.path}")
    return 0


def _append_operational(
    arguments: list[str], *, outbox_root: Path | None = None
) -> int:
    if arguments and arguments[0] in {"-h", "--help"}:
        sys.stdout.write(OPERATIONAL_USAGE)
        return 0
    if len(arguments) < 4:
        sys.stderr.write(OPERATIONAL_USAGE)
        return 2
    parsed = _parse_operational_arguments(arguments)
    _validate_operational_arguments(parsed)
    git = GitAdapter.discover(Path.cwd())
    related_commit = _resolve_related_commit(git, parsed.related_commit_input)
    related_id = parsed.related_git_report_id or "NONE"
    if related_commit != "NONE" and related_id != f"GIT-SHOW-REPORT-{related_commit}":
        raise UsageError("related commit and Git report id conflict")

    destination = _destination(git.root, parsed.phase, outbox_root)
    source_path = Path(parsed.source_value)
    metadata = validate_source_path(
        source_path,
        destination.path,
        source_value=parsed.source_value,
    )
    if metadata.st_size == 0:
        raise ReportError("source operational report is empty")
    if metadata.st_size > MAX_SOURCE_BYTES:
        raise ReportError("source operational report is oversized")
    with private_temporary_directory("append-operational-report"):
        testing_pause("source-validated")
        raw = read_validated_source(
            source_path,
            metadata,
            max_bytes=MAX_SOURCE_BYTES,
        )
        source = load_operational_source(source_path, raw)

        def build_for_existing(_existing: bytes, records):
            record = build_operational_record(
                source=source,
                project=destination.project,
                phase=parsed.phase,
                result=parsed.result,
                final_gate=parsed.final_gate,
                related_commit=related_commit,
                related_git_report_id=related_id,
                existing_records=records,
            )
            return build_record(record)

        destination.append(build_for_existing)
    record_id = f"OPERATIONAL-REPORT-{hashlib.sha256(source.raw).hexdigest()}"
    print(f"append-operational-report: appended {record_id} to {destination.path}")
    return 0


def _parse_operational_arguments(arguments: list[str]) -> OperationalArguments:
    phase, source_value, result, final_gate = arguments[:4]
    related_commit_input = ""
    related_git_report_id = ""
    remaining = list(arguments[4:])
    while remaining:
        option = remaining.pop(0)
        if option == "--related-commit":
            if related_commit_input or not remaining or not remaining[0]:
                sys.stderr.write(OPERATIONAL_USAGE)
                raise _UsageAlreadyRendered
            related_commit_input = remaining.pop(0)
        elif option == "--related-git-report-id":
            if related_git_report_id or not remaining or not remaining[0]:
                sys.stderr.write(OPERATIONAL_USAGE)
                raise _UsageAlreadyRendered
            related_git_report_id = remaining.pop(0)
        else:
            sys.stderr.write(OPERATIONAL_USAGE)
            raise _UsageAlreadyRendered
    return OperationalArguments(
        phase,
        source_value,
        result,
        final_gate,
        related_commit_input,
        related_git_report_id,
    )


def _validate_operational_arguments(arguments: OperationalArguments) -> None:
    validate_ticket(arguments.phase)
    validate_metadata(arguments.result)
    validate_metadata(arguments.final_gate)
    validate_metadata(arguments.source_value, "operational report path")
    if not source_value_is_absolute(arguments.source_value):
        raise UsageError("operational report path must be absolute")
    if (
        "//" in arguments.source_value
        or "/./" in arguments.source_value
        or "/../" in arguments.source_value
        or arguments.source_value.endswith("/.")
        or arguments.source_value.endswith("/..")
    ):
        raise UsageError("operational report path is not clean")
    if arguments.related_git_report_id:
        validate_related_git_report_id(arguments.related_git_report_id)
    if arguments.related_commit_input:
        try:
            validate_commit_input(arguments.related_commit_input)
        except ValueError as error:
            raise UsageError("related commit must be 7 to 64 hex characters") from error
    if arguments.related_commit_input and not arguments.related_git_report_id:
        raise UsageError("related commit requires a related Git-show report id")
    if arguments.related_commit_input and arguments.related_git_report_id.startswith(
        "GIT-DIFF-REPORT-"
    ):
        raise UsageError("a Git-diff relation cannot have a related commit")


def _resolve_related_commit(git: GitAdapter, commit_input: str) -> str:
    if not commit_input:
        return "NONE"
    completed = git.run(
        ["rev-parse", "--verify", f"{commit_input}^{{commit}}"],
        check=False,
    )
    if completed.returncode != 0:
        raise UsageError("related commit does not resolve")
    try:
        return completed.stdout.decode("ascii").strip().lower()
    except UnicodeDecodeError as error:
        raise UsageError("related commit does not resolve") from error
