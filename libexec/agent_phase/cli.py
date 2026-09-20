#!/usr/bin/env python3
"""Command-line entry points for the phase dispatcher."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


_LIBEXEC_DIR = str(Path(__file__).resolve().parents[1])
if _LIBEXEC_DIR not in sys.path:
    sys.path.insert(0, _LIBEXEC_DIR)

if __name__ == "__main__":
    from controller_generation_bootstrap import enter
    try:
        enter(Path(__file__).resolve().parents[2])
    except (OSError, ValueError, RuntimeError) as error:
        sys.exit(f"agent-phase-dispatch: generation binding failed ({type(error).__name__})")

from agent_phase.candidate import CandidateError  # noqa: E402
from agent_phase.dispatch import DispatchError, Dispatcher  # noqa: E402
from agent_phase.display import Display  # noqa: E402
from agent_phase.lifecycle import (  # noqa: E402
    FINALIZATION_POLICIES,
    FINALIZATION_PUBLISH,
    LIFECYCLE_NAMES,
    LIFECYCLE_STANDARD,
    LifecycleError,
)
from agent_phase.provider import ProviderError, run as provider_run  # noqa: E402
from agent_phase.request import (  # noqa: E402
    RequestError,
    parse_request,
    parse_request_v2,
)
from agent_phase.resolution_v2 import resolve_v2  # noqa: E402
from agent_phase.v2_dispatch import V2DispatchError, dispatch_v2  # noqa: E402
from agent_phase.routing import RoutingError, resolve  # noqa: E402
from agent_phase.dynamic_router import (  # noqa: E402
    NoRouteAvailableError,
    RoutingResolutionError,
)
from agent_phase.persistence import PersistenceError  # noqa: E402
from agent_phase.capabilities import CapabilityError  # noqa: E402
from agent_phase import run as run_module  # noqa: E402
from agent_phase import resume_validation as resume_validation_module  # noqa: E402
from agent_phase import scanner as scanner_module  # noqa: E402
from agent_phase.adoption import AdoptionError  # noqa: E402
from agent_phase.finalization_proof import RecoveryError  # noqa: E402
from agent_phase.native_git import NativeGitError  # noqa: E402
from agent_phase.entry_adoption import EntryAdoptionError  # noqa: E402
from agent_phase.config_routing import (  # noqa: E402
    ConfigError,
    ROUTING_MODES,
    resolve_execution_mode,
)


ERRORS = (
    RequestError, RoutingError, LifecycleError, CandidateError, DispatchError, ProviderError,
    run_module.RunPathError, resume_validation_module.ResumeError,
    scanner_module.ScannerError, AdoptionError, RecoveryError,
    NativeGitError, EntryAdoptionError, ConfigError,
    NoRouteAvailableError, RoutingResolutionError, PersistenceError,
    CapabilityError, V2DispatchError, OSError,
)


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def emit(payload: object) -> None:
    json.dump(payload, sys.stdout, sort_keys=True, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def resolve_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agent-phase-resolve", allow_abbrev=False)
    parser.add_argument("request", type=Path)
    parser.add_argument("--execution-mode", choices=ROUTING_MODES)
    parser.add_argument("--apgr-home", type=Path)
    parser.add_argument("--lifecycle", choices=LIFECYCLE_NAMES, default=LIFECYCLE_STANDARD)
    parser.add_argument(
        "--finalization", choices=FINALIZATION_POLICIES, default=FINALIZATION_PUBLISH
    )
    parsed = parser.parse_args(argv)
    try:
        raw = parsed.request.read_bytes()
        try:
            peek = json.loads(raw.decode("utf-8", errors="replace"))
        except Exception:
            peek = {}
        is_v2 = isinstance(peek, dict) and peek.get("schema") == "agent-phase-request-v2"
        if not is_v2 and parsed.execution_mode is not None:
            parser.error("--execution-mode cannot be specified for Request V1; Request V1 embedded execution_mode is authoritative")
        if is_v2:
            req_v2 = parse_request_v2(raw)
            mode_res = resolve_execution_mode(
                explicit=parsed.execution_mode,
                apgr_home=parsed.apgr_home,
            )
            emit(resolve_v2(
                req_v2,
                repository_root(),
                execution_mode=mode_res.execution_mode,
                configuration_provenance=mode_res.winner.as_dict(),
                lifecycle=parsed.lifecycle,
                finalization_policy=parsed.finalization,
            ))
        else:
            request = parse_request(raw)
            emit(resolve(
                request, repository_root(), parsed.lifecycle, parsed.finalization
            ))
    except ERRORS as error:
        parser.exit(2, f"agent-phase-resolve: {error}\n")
    return 0


def dispatch_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agent-phase-dispatch", allow_abbrev=False)
    parser.add_argument("request", type=Path)
    parser.add_argument("--execution-mode", choices=ROUTING_MODES)
    parser.add_argument("--apgr-home", type=Path)
    parser.add_argument("--outbox-root", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", type=Path, metavar="PRIOR_RUN")
    parser.add_argument("--continue-from", type=Path, metavar="ADOPTION_JSON")
    parser.add_argument(
        "--native-git-authority", type=Path, metavar="AUTHORITY_JSON"
    )
    parser.add_argument(
        "--entry-adoption", type=Path, metavar="ENTRY_ADOPTION_JSON"
    )
    parser.add_argument("--from-stage")
    parser.add_argument("--lifecycle", choices=LIFECYCLE_NAMES)
    parser.add_argument("--finalization", choices=FINALIZATION_POLICIES)
    parser.add_argument("--result-repair-commit-subject")
    parser.add_argument(
        "--result-repair-commit-body-file", type=Path, metavar="PATH"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="suppress the live progress display on stderr; artifacts and the "
             "machine-readable result on stdout are unaffected",
    )
    parsed = parser.parse_args(argv)
    if parsed.continue_from is not None and parsed.resume is not None:
        parser.error("--continue-from and --resume are distinct operations")
    if parsed.entry_adoption is not None and parsed.resume is not None:
        parser.error("--entry-adoption and --resume are distinct operations")
    if parsed.native_git_authority is not None and parsed.resume is not None:
        parser.error("--native-git-authority and --resume are distinct operations")
    if parsed.continue_from is not None and parsed.entry_adoption is not None:
        parser.error("--continue-from and --entry-adoption are distinct operations")
    if parsed.from_stage is not None and parsed.resume is None:
        parser.error("--from-stage requires --resume")
    commit_authority_requested = (
        parsed.result_repair_commit_subject is not None
        or parsed.result_repair_commit_body_file is not None
    )
    if commit_authority_requested and (
        parsed.resume is None
        or parsed.from_stage != "result-repair"
        or parsed.finalization not in ("commit-local", "publish")
    ):
        parser.error(
            "result-repair commit-message options require --resume, "
            "--from-stage result-repair, and --finalization commit-local|publish"
        )
    if (
        parsed.result_repair_commit_body_file is not None
        and parsed.result_repair_commit_subject is None
    ):
        parser.error(
            "--result-repair-commit-body-file requires "
            "--result-repair-commit-subject"
        )
    # Live human output goes to stderr so stdout stays a clean JSON channel.
    display = Display(sys.stderr, enabled=not parsed.quiet)
    try:
        raw = parsed.request.read_bytes()
        try:
            peek = json.loads(raw.decode("utf-8", errors="replace"))
        except Exception:
            peek = {}
        is_v2 = isinstance(peek, dict) and peek.get("schema") == "agent-phase-request-v2"
        if not is_v2 and parsed.execution_mode is not None:
            parser.error("--execution-mode cannot be specified for Request V1; Request V1 embedded execution_mode is authoritative")
        if not is_v2 and parsed.outbox_root is not None:
            parser.error("--outbox-root cannot be specified for Request V1; Request V1 outbox is determined by run configuration")
        if is_v2:
            if parsed.resume is not None:
                resume_target = Path(parsed.resume)
                if resume_target.is_symlink():
                    parser.error("source run must not be a symlink")
            if parsed.continue_from is not None:
                continue_target = Path(parsed.continue_from)
                if continue_target.is_symlink():
                    parser.error("continue_from must not be a symlink")
            req_v2 = parse_request_v2(raw)
            mode_res = resolve_execution_mode(
                explicit=parsed.execution_mode,
                apgr_home=parsed.apgr_home,
            )
            runner = None if parsed.dry_run else provider_run
            result = dispatch_v2(
                repository_root(),
                Path.cwd(),
                req_v2,
                raw,
                execution_mode=mode_res.execution_mode,
                provenance=mode_res.winner.as_dict(),
                provenance_chain=[p.as_dict() for p in mode_res.provenance_chain],
                apgr_home=parsed.apgr_home,
                outbox_root=parsed.outbox_root,
                lifecycle=parsed.lifecycle or LIFECYCLE_STANDARD,
                finalization_policy=parsed.finalization or FINALIZATION_PUBLISH,
                dry_run=parsed.dry_run,
                display=display,
                runner=runner,
                resume_from_run_id=parsed.resume,
                request_path=parsed.request,
                continue_from=parsed.continue_from,
                entry_adoption=parsed.entry_adoption,
                native_git_authority=parsed.native_git_authority,
            )
            emit(result)
            return 0

        phase_id = (
            resume_validation_module.phase_id_for_resume(
                parsed.resume, parsed.request
            )
            if parsed.resume is not None
            else run_module.phase_id_from_request(parsed.request)
        )
        request = parse_request(raw)
        dispatcher = Dispatcher(repository_root(), Path.cwd(), display=display)
        if parsed.resume is not None:
            state = dispatcher.resume(
                phase_id, request, parsed.resume, parsed.from_stage or "auto",
                lifecycle=parsed.lifecycle,
                finalization_policy=parsed.finalization,
                dry_run=parsed.dry_run,
                result_repair_commit_subject=(
                    parsed.result_repair_commit_subject
                ),
                result_repair_commit_body_file=(
                    parsed.result_repair_commit_body_file
                ),
            )
        else:
            lifecycle = parsed.lifecycle or LIFECYCLE_STANDARD
            finalization = parsed.finalization or FINALIZATION_PUBLISH
            dispatch_kwargs = {}
            if parsed.continue_from is not None:
                dispatch_kwargs["continue_from"] = parsed.continue_from
            if parsed.native_git_authority is not None:
                dispatch_kwargs["native_git_authority"] = parsed.native_git_authority
            if parsed.entry_adoption is not None:
                dispatch_kwargs["entry_adoption"] = parsed.entry_adoption
            state = (
                dispatcher.dry_run(
                    phase_id, request, lifecycle, finalization,
                    **dispatch_kwargs,
                )
                if parsed.dry_run
                else dispatcher.dispatch(
                    phase_id, request, lifecycle, finalization,
                    **dispatch_kwargs,
                )
            )
        emit(state)
    except DispatchError as error:
        # An interrupt reaching the dispatcher between stages and one reaching it
        # inside a stage are the same event to the operator, so they exit alike.
        code = 130 if error.code == "OPERATOR_INTERRUPTED" else 2
        parser.exit(code, f"agent-phase-dispatch: {error}\n")
    except ERRORS as error:
        parser.exit(2, f"agent-phase-dispatch: {error}\n")
    except KeyboardInterrupt:
        parser.exit(130, "agent-phase-dispatch: interrupted\n")
    finally:
        display.close()
    return 0


def scan_summary_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agent-phase-scan-summary", allow_abbrev=False)
    parser.add_argument("--run-root", type=Path, default=None)
    parsed = parser.parse_args(argv)
    root = parsed.run_root or run_module.default_root()
    try:
        emit(
            scanner_module.summarize(
                root / run_module.TELEMETRY_FILE, root / run_module.LABEL_FILE
            )
        )
    except ERRORS as error:
        parser.exit(2, f"agent-phase-scan-summary: {error}\n")
    return 0


def scan_label_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agent-phase-scan-label", allow_abbrev=False)
    parser.add_argument("--scan-id", required=True)
    parser.add_argument("--label", required=True, choices=scanner_module.LABELS)
    parser.add_argument("--note", default=None)
    parser.add_argument("--run-root", type=Path, default=None)
    parsed = parser.parse_args(argv)
    root = parsed.run_root or run_module.default_root()
    try:
        emit(
            scanner_module.append_label(
                root / run_module.LABEL_FILE, parsed.scan_id, parsed.label, parsed.note
            )
        )
    except ERRORS as error:
        parser.exit(2, f"agent-phase-scan-label: {error}\n")
    return 0


MAINS = {
    "resolve": resolve_main,
    "dispatch": dispatch_main,
    "scan-summary": scan_summary_main,
    "scan-label": scan_label_main,
}


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "adopt":
        from agent_phase.adoption_cli import main as adopt_main
        return adopt_main(sys.argv[2:])
    if len(sys.argv) > 1 and sys.argv[1] == "adopt-entry":
        from agent_phase.entry_adoption_cli import main as adopt_entry_main
        return adopt_entry_main(sys.argv[2:])
    if len(sys.argv) > 1 and sys.argv[1] == "native-git":
        from agent_phase.native_git_cli import main as native_git_main
        return native_git_main(sys.argv[2:])
    if len(sys.argv) > 1 and sys.argv[1] == "finalize":
        from agent_phase.finalization_recovery import main as finalize_main
        return finalize_main(sys.argv[2:])
    if len(sys.argv) < 2 or sys.argv[1] not in MAINS:
        sys.stderr.write(f"agent-phase: entry point must be one of {sorted(MAINS)}\n")
        return 2
    return MAINS[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    raise SystemExit(main())
