"""Provider-free operational observation commands.

``summarize`` reads selected run directories (or the optional index),
``index`` imports/rebuilds the optional SQLite index, ``feedback`` appends
explicitly attributed feedback, ``explain`` shows one run's context
decisions from its own records (no index required), and ``list`` discovers
runs and their recorded state without knowing run paths. None of them invokes
a provider, planner, Go bridge or dispatcher, and none writes into run
directories.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from agent_phase import observations
from agent_phase.config_routing import ConfigError, resolve_global_home


def _selection_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("runs", nargs="*", type=Path, help="explicit run directories")
    parser.add_argument("--outbox-root", type=Path, default=None)
    parser.add_argument("--project", default=None, help="outbox project directory name")
    parser.add_argument("--phase", default=None, help="restrict to one phase directory")
    parser.add_argument("--v2", action="store_true",
                        help="include canonical V2 runs under <APGR_HOME>/state/runs")
    parser.add_argument("--latest", type=int, default=20,
                        help=f"newest runs per selector (1..{observations.MAX_RUNS})")
    parser.add_argument("--apgr-home", type=Path, default=None)


def _home(parsed: argparse.Namespace) -> Path:
    return resolve_global_home(parsed.apgr_home)


def _collect(parsed: argparse.Namespace, warnings: list[str]) -> list[dict]:
    paths = observations.select_runs(
        run_dirs=parsed.runs, outbox_root=parsed.outbox_root, project=parsed.project,
        phase=parsed.phase, apgr_home=_home(parsed) if parsed.v2 else None,
        v2_home=parsed.v2, latest=parsed.latest)
    if not paths:
        raise observations.ObservationError(
            "no runs selected; pass run directories, --outbox-root/--project, or --v2")
    runs = []
    for path in paths:
        try:
            runs.append(observations.collect_run(path))
        except observations.ObservationError as error:
            warnings.append(f"{path.name}: {error}")
        except (TypeError, AttributeError, ValueError, KeyError) as error:
            # Analytics only: one structurally malformed run is skipped, not fatal.
            warnings.append(f"{path.name}: malformed run records skipped ({type(error).__name__})")
    return runs


def summarize_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="agent-phase observations summarize", allow_abbrev=False)
    _selection_arguments(parser)
    parser.add_argument("--from-index", action="store_true", help="read the optional index instead of run directories")
    parser.add_argument("--index", type=Path, default=None)
    parser.add_argument("--run-id", action="append", default=None, dest="run_ids",
                        help="with --from-index, restrict to this run id (repeatable)")
    parser.add_argument("--no-feedback", action="store_true")
    parser.add_argument("--json", action="store_true")
    parsed = parser.parse_args(argv)
    if parsed.from_index and (parsed.runs or parsed.outbox_root or parsed.project or parsed.phase or parsed.v2):
        parser.exit(2, f"{parser.prog}: --from-index selects with --run-id only; "
                       "run-directory and outbox selectors apply to direct summaries\n")
    if parsed.run_ids and not parsed.from_index:
        parser.exit(2, f"{parser.prog}: --run-id requires --from-index\n")
    warnings: list[str] = []
    try:
        home = _home(parsed)
        if parsed.from_index:
            runs = observations.runs_from_index(
                parsed.index or observations.storage_root(home) / "index.sqlite3",
                set(parsed.run_ids) if parsed.run_ids else None)
        else:
            runs = _collect(parsed, warnings)
        feedback = [] if parsed.no_feedback else observations.read_feedback(
            observations.storage_root(home) / "feedback.jsonl", {r["run_id"] for r in runs}, warnings)
    except (observations.ObservationError, ConfigError, OSError) as error:
        parser.exit(2, f"{parser.prog}: {error}\n")
    summary = observations.summarize(runs, feedback)
    summary["warnings"].extend(warnings)
    sys.stdout.write(json.dumps(summary, indent=2, sort_keys=True) + "\n" if parsed.json
                     else observations.render_text(summary))
    return 0


def index_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="agent-phase observations index", allow_abbrev=False)
    _selection_arguments(parser)
    parser.add_argument("--index", type=Path, default=None)
    parser.add_argument("--rebuild", action="store_true", help="write a fresh index and replace it atomically")
    parsed = parser.parse_args(argv)
    warnings: list[str] = []
    try:
        path = parsed.index or observations.storage_root(_home(parsed)) / "index.sqlite3"
        counts = observations.import_runs(path, _collect(parsed, warnings), rebuild=parsed.rebuild)
    except (observations.ObservationError, ConfigError, OSError) as error:
        sys.stderr.write(f"{parser.prog}: {error}\n")
        return 1
    sys.stdout.write(json.dumps({"index": path.name, **counts, "warnings": warnings}, sort_keys=True) + "\n")
    return 0


def feedback_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="agent-phase observations feedback", allow_abbrev=False)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--attempt-id", default=None)
    parser.add_argument("--label", required=True, choices=observations.FEEDBACK_LABELS)
    parser.add_argument("--source", required=True, choices=observations.FEEDBACK_SOURCES)
    parser.add_argument("--skill", default=None, help="qualified skill id the feedback concerns")
    parser.add_argument("--note", default=None)
    parser.add_argument("--apgr-home", type=Path, default=None)
    parsed = parser.parse_args(argv)
    try:
        record = observations.append_feedback(
            observations.storage_root(_home(parsed)) / "feedback.jsonl",
            run_id=parsed.run_id, attempt_id=parsed.attempt_id, label=parsed.label,
            source=parsed.source, skill=parsed.skill, note=parsed.note)
    except (observations.ObservationError, ConfigError, OSError) as error:
        parser.exit(2, f"{parser.prog}: {error}\n")
    sys.stdout.write(json.dumps(record, sort_keys=True) + "\n")
    return 0


def _leaf_path(parsed: argparse.Namespace, home: Path) -> Path:
    """Resolve ``--leaf`` inside the named known layout; never an arbitrary path."""
    from agent_phase.observations_discovery import HISTORICAL_LEAF, verified_projection
    from agent_phase.run import RunPathError, default_root, safe_component
    try:
        for value, kind in ((parsed.leaf, "leaf"), (parsed.project, "project"), (parsed.phase, "phase")):
            if value is not None:
                safe_component(value, kind)
    except RunPathError as error:
        raise observations.ObservationError(str(error)) from error
    runs = home / "state" / "runs"
    if parsed.v2:
        parents, leaf = [runs], runs / parsed.leaf
    else:
        pattern = observations._LEAF if parsed.phase else HISTORICAL_LEAF
        if not pattern.fullmatch(parsed.leaf):
            raise observations.ObservationError("--leaf does not name a run leaf of the selected layout")
        project_dir = (parsed.outbox_root or default_root(home, project_root=Path.cwd())) / parsed.project
        parents = [project_dir, project_dir / parsed.phase] if parsed.phase else [project_dir]
        leaf = parents[-1] / parsed.leaf
    if any(path.is_symlink() for path in parents):
        raise observations.ObservationError("--leaf layout directories must not be symlinks")
    if leaf.is_symlink():
        # Only a verified V2 projection (phase layout) is read, at its target, as in ``list``.
        target = None if parsed.v2 or not parsed.phase else verified_projection(leaf, runs)
        if target is None:
            raise observations.ObservationError("--leaf names a symlink that is not a verified V2 projection")
        return target
    return leaf


def _explain_selection(parsed: argparse.Namespace, home: Path) -> list[Path]:
    if parsed.leaf:
        return observations.select_runs(run_dirs=[_leaf_path(parsed, home)])
    if parsed.run:
        return observations.select_runs(run_dirs=[parsed.run])
    if parsed.project:
        outbox = parsed.outbox_root
        if outbox is None:
            from agent_phase.run import default_root
            outbox = default_root(home, project_root=Path.cwd())
        return observations.select_runs(outbox_root=outbox, project=parsed.project, phase=parsed.phase, latest=1)
    return observations.select_runs(apgr_home=home, v2_home=True, latest=1)


def explain_main(argv: list[str]) -> int:
    from agent_phase import observations_explain as explain
    parser = argparse.ArgumentParser(prog="agent-phase observations explain", allow_abbrev=False)
    parser.add_argument("run", nargs="?", type=Path, help="explicit run directory")
    parser.add_argument("--project", default=None, help="newest run of this outbox project directory")
    parser.add_argument("--outbox-root", type=Path, default=None,
                        help="with --project; defaults to the resolved dispatcher outbox root")
    parser.add_argument("--phase", default=None, help="with --project, restrict to one phase directory")
    parser.add_argument("--v2", action="store_true", help="newest canonical V2 run under <APGR_HOME>/state/runs")
    parser.add_argument("--leaf", default=None,
                        help="with --project (and --phase) or --v2: exactly this listed run leaf or V2 run id")
    parser.add_argument("--attempt", default=None, help="attempt prefix or attempt id")
    parser.add_argument("--stage", default=None, help="binding/stage id")
    parser.add_argument("--no-feedback", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--apgr-home", type=Path, default=None)
    parsed = parser.parse_args(argv)
    if sum(bool(x) for x in (parsed.run, parsed.project, parsed.v2)) != 1:
        parser.exit(2, f"{parser.prog}: select exactly one of RUN_DIR, --project or --v2\n")
    if (parsed.outbox_root or parsed.phase) and not parsed.project:
        parser.exit(2, f"{parser.prog}: --outbox-root and --phase require --project\n")
    if parsed.leaf and parsed.run:
        parser.exit(2, f"{parser.prog}: --leaf requires --project or --v2\n")
    warnings: list[str] = []
    try:
        home = _home(parsed)
        paths = _explain_selection(parsed, home)
        if not paths:
            raise observations.ObservationError("no run found for the selector")
        value = explain.explain_run(paths[0], attempt=parsed.attempt, stage=parsed.stage)
        if not parsed.no_feedback:
            explain.attach_feedback(value, observations.read_feedback(
                observations.storage_root(home) / "feedback.jsonl", {value["run"]["run_id"]}, warnings))
    except (observations.ObservationError, ConfigError, OSError) as error:
        parser.exit(2, f"{parser.prog}: {error}\n")
    value["warnings"].extend(warnings)
    sys.stdout.write(json.dumps(value, indent=2, sort_keys=True) + "\n" if parsed.json
                     else explain.render_explanation(value))
    return 0


def list_main(argv: list[str]) -> int:
    from agent_phase import observations_list
    from agent_phase.run import RunPathError, default_root, safe_component
    parser = argparse.ArgumentParser(
        prog="agent-phase observations list", allow_abbrev=False,
        description="List dispatch runs and their recorded state, newest first (read-only; not live health).")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--project", default=None, help="outbox project directory name")
    scope.add_argument("--all-projects", action="store_true", help="every project under the outbox root (bounded)")
    parser.add_argument("--phase", default=None, help="restrict to one phase id")
    parser.add_argument("--outbox-root", type=Path, default=None,
                        help="defaults to the resolved dispatcher outbox root")
    parser.add_argument("--v2", action="store_true", help="include canonical V2 runs under <APGR_HOME>/state/runs")
    parser.add_argument("--latest", type=int, default=observations_list.DEFAULT_LATEST,
                        help=f"newest runs across the whole selection (1..{observations.MAX_RUNS})")
    parser.add_argument("--no-feedback", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--apgr-home", type=Path, default=None)
    parsed = parser.parse_args(argv)
    if not (parsed.project or parsed.all_projects or parsed.v2):
        parser.exit(2, f"{parser.prog}: select --project, --all-projects or --v2\n")
    if parsed.outbox_root is not None and not (parsed.project or parsed.all_projects):
        parser.exit(2, f"{parser.prog}: --outbox-root requires --project or --all-projects\n")
    if parsed.outbox_root is not None and not parsed.outbox_root.is_dir():
        parser.exit(2, f"{parser.prog}: --outbox-root is not a directory\n")
    try:
        for value, kind in ((parsed.project, "project"), (parsed.phase, "phase")):
            if value is not None:
                safe_component(value, kind)
        home = _home(parsed)
        outbox = None
        if parsed.project or parsed.all_projects:
            outbox = parsed.outbox_root or default_root(home, project_root=Path.cwd())
        value = observations_list.list_runs(
            outbox_root=outbox, project=parsed.project, phase=parsed.phase, apgr_home=home, v2=parsed.v2,
            latest=parsed.latest, feedback=not parsed.no_feedback,
            explicit_outbox=parsed.outbox_root is not None, explicit_home=parsed.apgr_home is not None)
    except (observations.ObservationError, ConfigError, RunPathError, OSError) as error:
        parser.exit(2, f"{parser.prog}: {error}\n")
    sys.stdout.write(json.dumps(value, indent=2, sort_keys=True) + "\n" if parsed.json
                     else observations_list.render_list(value))
    return 0


COMMANDS = {"summarize": summarize_main, "index": index_main, "feedback": feedback_main,
            "explain": explain_main, "list": list_main}


def main(argv: list[str] | None = None) -> int:
    values = list(sys.argv[1:] if argv is None else argv)
    if not values or values[0] not in COMMANDS:
        sys.stderr.write(f"observations: command must be one of {sorted(COMMANDS)}\n")
        return 2
    return COMMANDS[values[0]](values[1:])


if __name__ == "__main__":
    raise SystemExit(main())
