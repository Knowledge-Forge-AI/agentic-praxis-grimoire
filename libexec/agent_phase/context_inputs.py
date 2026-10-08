"""Structured context-planning inputs for the adaptive branch only.

Facts and explicit skill requests come from four closed sources with a fixed
precedence per fact kind: task (dispatch command line) > project config > home
config > repository manifests. Manifest facts are read from a small fixed set
of top-level regular files; nothing is executed and task prose is never
interpreted. Unknown or contradictory values stay visible in the returned
record and are not sent to the planner.

Static dispatch never resolves inputs; configuration owners import only the
pure closed validator.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import os
from pathlib import Path
import re
import stat
from typing import Any, Iterable, Mapping

SCHEMA = "apg.context-inputs/v1"
FACT_KINDS = ("language", "runtime", "test_framework", "repository_characteristic", "capability")
STAGES = ("plan", "review", "work")
SKILL_ID = re.compile(r"^(apgr|project|user):[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
FACT_VALUE = re.compile(r"^[a-z0-9][a-z0-9._+-]{0,63}\Z")
MAX_SKILLS = 64
MAX_FACT_VALUES = 32
MAX_MANIFEST_BYTES = 256 * 1024
CONTEXT_KEYS = frozenset({"mode", "max_initial_context_bytes", "max_initial_context_characters",
                          "manifest_facts", "skills", "facts", "instructions"})
INSTRUCTION_MODES = ("projected", "static")

# Presence-only rows plus one bounded parse (pyproject.toml). Order is stable.
MANIFESTS = (
    ("go.mod", (("language", "go"), ("test_framework", "go-native"))),
    ("pyproject.toml", (("language", "python"),)),
    ("pytest.ini", (("test_framework", "pytest"),)),
    ("setup.py", (("language", "python"),)),
    ("setup.cfg", (("language", "python"),)),
    ("requirements.txt", (("language", "python"),)),
    ("package.json", (("runtime", "nodejs"), ("language", "javascript"))),
    ("tsconfig.json", (("language", "typescript"),)),
    ("Gemfile", (("language", "ruby"),)),
    ("flake.nix", (("language", "nix"),)),
    ("default.nix", (("language", "nix"),)),
    ("Dockerfile", (("repository_characteristic", "dockerfile"),)),
    ("Vagrantfile", (("repository_characteristic", "vagrantfile"),)),
    ("Cargo.toml", (("language", "rust"),)),
)

TASK_INPUTS: ContextVar = ContextVar("apgr_context_task_inputs", default=None)


class InputError(ValueError):
    """A task-supplied fact or request is outside the closed vocabulary."""


def validate_context_table(context: Mapping[str, Any], error: type[Exception]) -> None:
    """Closed validation of the additive dispatcher.context input keys.

    Both configuration owners call an identical copy of these rules; the
    parity test in the dispatcher suite binds them together.
    """
    if "manifest_facts" in context and type(context["manifest_facts"]) is not bool:
        raise error("dispatcher.context.manifest_facts must be a boolean")
    if "instructions" in context and context["instructions"] not in INSTRUCTION_MODES:
        raise error("dispatcher.context.instructions must be projected or static")
    if "skills" in context:
        skills = context["skills"]
        if not isinstance(skills, list) or len(skills) > MAX_SKILLS:
            raise error(f"dispatcher.context.skills must be a list of at most {MAX_SKILLS} entries")
        seen = set()
        for item in skills:
            entry = normalize_request(item, error)
            if entry["id"] in seen:
                raise error(f"duplicate dispatcher.context.skills entry: {entry['id']}")
            seen.add(entry["id"])
    if "facts" in context:
        facts = context["facts"]
        if not isinstance(facts, dict):
            raise error("dispatcher.context.facts must be a table")
        for kind, values in facts.items():
            if kind == "work_class":
                raise error("dispatcher.context.facts.work_class is dispatcher-owned")
            if kind not in FACT_KINDS:
                raise error(f"unsupported dispatcher.context.facts kind: {kind}")
            if (not isinstance(values, list) or len(values) > MAX_FACT_VALUES
                    or any(not isinstance(v, str) or not FACT_VALUE.match(v) for v in values)
                    or len(set(values)) != len(values)):
                raise error(f"dispatcher.context.facts.{kind} must be a list of distinct "
                            "lowercase fact values")


def normalize_request(item: Any, error: type[Exception] = InputError) -> dict[str, Any]:
    if isinstance(item, str):
        item = {"id": item}
    if not isinstance(item, dict) or set(item) - {"id", "required", "stages"} or "id" not in item:
        raise error("skill request must be an ID or a table with id, required and stages")
    if not isinstance(item["id"], str) or not SKILL_ID.match(item["id"]):
        raise error(f"invalid qualified skill ID: {item['id']!r}")
    if "required" in item and type(item["required"]) is not bool:
        raise error("skill request required must be a boolean")
    stages = item.get("stages", list(STAGES))
    if (not isinstance(stages, list) or not stages or len(set(stages)) != len(stages)
            or any(s not in STAGES for s in stages)):
        raise error("skill request stages must be a non-empty subset of plan, review and work")
    return {"id": item["id"], "required": item.get("required", False), "stages": sorted(stages)}


def parse_task_fact(text: str) -> tuple[str, str]:
    kind, separator, value = text.partition("=")
    if not separator or kind not in FACT_KINDS or not FACT_VALUE.match(value):
        raise InputError(f"--context-fact must be KIND=VALUE with KIND in {', '.join(FACT_KINDS)}")
    return kind, value


def scoped_task_inputs(facts: Iterable[tuple[str, str]] = (), skills: Iterable[str] = ()):
    """Validate eagerly, then bind dispatch-command inputs to one fresh dispatch.

    The values are recorded in each attempt's context-plan ``inputs`` section;
    they are never persisted as configuration and are not carried by resume.
    """
    facts, skills = list(facts), list(skills)
    for kind, value in facts:
        parse_task_fact(f"{kind}={value}")
    requests = [normalize_request(s) for s in skills]
    if len({r["id"] for r in requests}) != len(requests):
        raise InputError("duplicate --context-skill")
    return _bound({"facts": facts, "skills": requests} if (facts or requests) else None)


@contextmanager
def _bound(value):
    token = TASK_INPUTS.set(value)
    try:
        yield value
    finally:
        TASK_INPUTS.reset(token)


def _read_bounded(path: Path) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("not a regular file")
        if info.st_size > MAX_MANIFEST_BYTES:
            raise OverflowError("oversized")
        data = stream.read(MAX_MANIFEST_BYTES + 1)
    if len(data) > MAX_MANIFEST_BYTES:
        raise OverflowError("oversized")
    return data


def manifest_facts(work_tree: Path | str | None) -> tuple[list[tuple[str, str, str]], list[dict[str, Any]]]:
    """Return (kind, value, file) facts and per-file statuses for present files."""
    facts: list[tuple[str, str, str]] = []
    files: list[dict[str, Any]] = []
    if work_tree is None:
        return facts, [{"file": None, "status": "unknown", "reason": "no_working_tree"}]
    root = Path(work_tree)
    for name, produced in MANIFESTS:
        path = root / name
        try:
            info = path.lstat()
        except FileNotFoundError:
            continue
        except OSError as error:
            files.append({"file": name, "status": "unknown", "reason": type(error).__name__})
            continue
        if stat.S_ISLNK(info.st_mode):
            files.append({"file": name, "status": "unknown", "reason": "symlink_ignored"})
            continue
        if not stat.S_ISREG(info.st_mode):
            files.append({"file": name, "status": "unknown", "reason": "not_regular_file"})
            continue
        rows = list(produced)
        if name == "pyproject.toml":
            try:
                import tomllib
                document = tomllib.loads(_read_bounded(path).decode("utf-8"))
            except OverflowError:
                files.append({"file": name, "status": "unknown", "reason": "oversized"})
                continue
            except (OSError, ValueError, UnicodeError) as error:
                files.append({"file": name, "status": "unknown",
                              "reason": "unparseable" if not isinstance(error, OSError) else "unreadable"})
                continue
            tool = document.get("tool") if isinstance(document.get("tool"), dict) else {}
            pytest_table = tool.get("pytest") if isinstance(tool.get("pytest"), dict) else {}
            if isinstance(pytest_table.get("ini_options"), dict):
                rows.append(("test_framework", "pytest"))
        files.append({"file": name, "status": "read", "facts": [f"{k}={v}" for k, v in rows]})
        facts.extend((kind, value, name) for kind, value in rows)
    return facts, files


def _declared(provenance: list[Mapping[str, Any]], source: str) -> Mapping[str, Any]:
    for row in provenance:
        if row.get("source") == source:
            context = row.get("context")
            return context if isinstance(context, Mapping) else {}
    return {}


def resolve(capture: Mapping[str, Any], *, postures: Iterable[str],
            work_tree: Path | str | None) -> tuple[list[dict[str, str]], list[dict[str, Any]], dict[str, Any]]:
    """Resolve planner facts/requests plus an explanation record."""
    postures = sorted(set(postures))
    provenance = list(capture.get("provenance") or [])
    home, project = _declared(provenance, "home"), _declared(provenance, "project")
    task = TASK_INPUTS.get() or {}
    task_facts: dict[str, list[str]] = {}
    for kind, value in task.get("facts", []):
        task_facts.setdefault(kind, [])
        if value not in task_facts[kind]:
            task_facts[kind].append(value)
    declared = [("task", task_facts), ("project", project.get("facts") or {}),
                ("home", home.get("facts") or {})]
    manifest_enabled = capture.get("settings", {}).get("manifest_facts", True) is not False
    manifest, files = manifest_facts(work_tree) if manifest_enabled else ([], [])
    rows: list[dict[str, Any]] = []
    planner_facts: list[dict[str, str]] = []
    for kind in FACT_KINDS:
        winner = next(((source, table[kind]) for source, table in declared if kind in table), None)
        manifest_values = [(v, f) for k, v, f in manifest if k == kind]
        if winner is not None:
            source, values = winner
            for value in values:
                rows.append({"kind": kind, "value": value, "source": source, "status": "supplied"})
                planner_facts.append({"kind": kind, "value": value})
            for other, other_values in declared:
                if other == source or kind not in other_values:
                    continue
                for value in other_values[kind]:
                    if value not in values:
                        rows.append({"kind": kind, "value": value, "source": other, "status": "overridden"})
            for value, name in manifest_values:
                rows.append({"kind": kind, "value": value, "source": f"manifest:{name}",
                             "status": "supplied" if value in values else "conflicting"})
        else:
            seen = set()
            for value, name in manifest_values:
                rows.append({"kind": kind, "value": value, "source": f"manifest:{name}", "status": "supplied"})
                if value not in seen:
                    seen.add(value)
                    planner_facts.append({"kind": kind, "value": value})
    # Explicit requests: the nearest declaring config list replaces lower lists
    # (per-key capture semantics); task requests are unioned and win attributes.
    configured_source, configured = next(
        ((s, c["skills"]) for s, c in (("project", project), ("home", home)) if "skills" in c), (None, []))
    requests: dict[str, dict[str, Any]] = {}
    for item in configured:
        entry = normalize_request(item)
        requests[entry["id"]] = {**entry, "source": configured_source}
    for entry in task.get("skills", []):
        requests[entry["id"]] = {**entry, "source": "task"}
    request_rows, planner_requests = [], []
    for identifier in sorted(requests):
        entry = requests[identifier]
        applies = bool(set(entry["stages"]) & set(postures))
        request_rows.append({**entry, "applies": applies,
                             "status": "supplied" if applies else "not_applicable"})
        if applies:
            planner_requests.append({"id": identifier, "required": entry["required"]})
    record = {"schema": SCHEMA, "postures": postures,
              "task_source": "dispatch_command" if task else None,
              "task_inputs_note": "command-line inputs apply to fresh dispatches only; resumes use configuration",
              "manifest": {"enabled": manifest_enabled, "files": files,
                           "boundary": "top-level regular files; presence plus bounded pyproject.toml parse; nothing executed"},
              "facts": rows, "requests": request_rows}
    return planner_facts, planner_requests, record
