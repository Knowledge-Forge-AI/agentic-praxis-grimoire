"""Substantive task oracles for the frozen APG159A context corpus.

The provider result is deliberately only a terminal receipt here.  A zero
provider exit status, a plausible answer, or a context delivery observation
cannot establish task correctness.  Command scenarios therefore run the
frozen command and inspect the resulting subject; review scenarios validate a
small, preregistered finding contract and independently validate the APGR
mechanism evidence supplied by the arm owner.

This module has no provider or model dependency.  ``exercise_oracle`` uses
repository-local temporary GOOD/BAD fixtures and the real frozen commands
where a command is part of the frozen oracle.  Those fixtures are deliberately
outside the model-visible subject corpus.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import subprocess
import tempfile
from typing import Any, Callable, Mapping


SCHEMA = "apg.h-task-oracle/v1"
FIXTURE_SCHEMA = "apg.h-oracle-fixture-exercise/v1"
_MAX_FILES = 20_000
_MAX_BYTES = 128 << 20
_EPHEMERAL_PARTS = frozenset({".git", "__pycache__", ".pytest_cache", "node_modules", "build"})


# These values are copied from the frozen scenario JSON.  Keeping the exact
# object here makes oracle binding fail closed if a caller supplies a scenario
# with a changed quality-oracle contract.
_FROZEN_QUALITY_ORACLES: dict[str, dict[str, Any]] = {
    "scenario-01": {
        "assertions": "health check endpoint returns 200 and passes test assertions; zero unexpected repo mutations",
        "command": "go test ./pkg/handler/...",
        "expected_exit_code": 0,
    },
    "scenario-02": {
        "assertions": "plan review disposition is recorded and pytest suite passes cleanly",
        "command": "pytest tests/",
        "expected_exit_code": 0,
    },
    "scenario-03": {
        "assertions": "zero inapplicable language/database skills selected; reviewer produces structured critique; zero worktree/index/HEAD drift",
    },
    "scenario-04": {
        "assertions": "RTK instructions slice delivered in prompt; bash syntax passes; zero git authority drift",
        "command": "bash -n scripts/build.sh",
        "expected_exit_code": 0,
    },
    "scenario-05": {
        "assertions": "static dispatch succeeds cleanly; all canonical skills loaded via global root; no attempted destructive per-run projection",
    },
    "scenario-06": {
        "assertions": "server SQLite query handler passes integration tests cleanly",
        "command": "go test ./cmd/server/...",
        "expected_exit_code": 0,
    },
    "scenario-07": {
        "assertions": "planner rejects adaptive context plan due to mandatory doctrine overflow and falls back to qualified static transport with doctrine intact; zero silent doctrine truncation; no pre-launch dispatch abort",
    },
    "scenario-08": {
        "assertions": "both project: and apgr: skills are retained under explicit namespaces; zero silent shadowing; project skill ranked ahead of canonical",
    },
    "scenario-09": {
        "assertions": "canonical apgr: skill is suppressed; project: skill is delivered; replacement provenance is explicitly recorded in plan",
    },
    "scenario-10": {
        "assertions": "go-cmp integration test compiles and passes; acquired body SHA-256 matches canonical exactly; zero repo mutations outside tests/",
        "command": "go test ./tests/...",
        "expected_exit_code": 0,
    },
    "scenario-11": {
        "assertions": "reviewer receives full body in MCP result payload without shell access; review findings reference test profile standards; zero git authority drift",
    },
    "scenario-12": {
        "assertions": "reviewer recovers skill body from pre-materialized snapshot using view_file without shell access; critique is delivered; zero git authority drift",
    },
    "scenario-13": {
        "assertions": "dispatcher detects disabled/unavailable MCP before launch; cleanly chooses static context mode; zero attempted broken JSON-RPC connections",
    },
    "scenario-14": {
        "assertions": "in-band MCP acquisition delivers skill body to reviewer without repository writes; worktree, index, and HEAD remain strictly unchanged",
    },
    "scenario-15": {
        "assertions": "component builds cleanly; operator claude settings remain unmutated; zero global discovery pollution",
        "command": "npm run build --prefix frontend",
        "expected_exit_code": 0,
    },
}

_COMMAND_SCENARIOS = frozenset(
    scenario_id
    for scenario_id, oracle in _FROZEN_QUALITY_ORACLES.items()
    if "command" in oracle
)
_READ_ONLY_SCENARIOS = frozenset({"scenario-03", "scenario-07", "scenario-11", "scenario-12", "scenario-13", "scenario-14"})
_AUTHORITY_EVIDENCE_REQUIRED = frozenset(
    {"scenario-03", "scenario-04", "scenario-07", "scenario-10", "scenario-11", "scenario-12", "scenario-13", "scenario-14", "scenario-15"}
)
_CANONICAL_BODY_SHA = {
    "scenario-10": "daf781fb67e2bbd491bfbc4238d575d1bce78cd5b99f417ab4a33c27ed8180aa",
    "scenario-11": "b675e94daabf185896bba5cf740891215e74741b1088ba2fa74cb9d5576c6e61",
    "scenario-12": "a2a1090422ddd0aa38610f7beedad1d6af6d50f7c6c553fc6f1f5aabfb04935f",
}

# These are the source-owned read-only tool scopes for the two scenarios whose
# substantive contract mentions the absence of shell authority.  The event
# trace is still checked for unexpected shell channels, but an empty event
# trace cannot itself prove that a shell was not granted.
_READ_ONLY_TOOL_SCOPES = {
    "scenario-11": frozenset({"view_file", "skill_search", "skill_acquire", "context_explain"}),
    "scenario-12": frozenset({"view_file"}),
}

_REVIEW_REQUIRED_PATHS = {
    "scenario-03": frozenset({"README.md", "docs/architecture.md"}),
    "scenario-11": frozenset({"pkg/api/client.go"}),
    "scenario-12": frozenset({"pkg/service/service.go"}),
    "scenario-14": frozenset({"pkg/data/models.go"}),
}

# These semantic facts are source-owned oracle data, derived from the frozen
# subjects above.  They are deliberately separate from the response contract:
# the model receives only the answer-neutral envelope instructions, while the
# oracle retains the objective fact kind it must check.  Matching binds each
# response to frozen source bytes before evaluating the fact; summary and
# category prose never participates in acceptance.
_REVIEW_FACTS: dict[str, tuple[dict[str, Any], ...]] = {
    "scenario-03": (
        {
            "path": "README.md",
            "kind": "absent_link_target",
        },
        {
            "path": "docs/architecture.md",
            "kind": "adjacent_heading_lines",
        },
    ),
    "scenario-11": (
        {
            "path": "pkg/api/client.go",
            "kind": "nil_pair_return",
        },
    ),
    "scenario-12": (
        {
            "path": "pkg/service/service.go",
            "kind": "constant_return",
        },
    ),
    "scenario-14": (
        {
            "path": "pkg/data/models.go",
            "kind": "field_declarations",
        },
    ),
}

_REVIEW_FACT_BY_PATH = {
    (scenario_id, fact["path"]): fact
    for scenario_id, facts in _REVIEW_FACTS.items()
    for fact in facts
}


class _Incomplete(Exception):
    """Evidence is absent or malformed, so the arm cannot be qualified."""


RECEIPT_SCHEMA = "apg.h-arm-evidence/v1"
_RECEIPT_FILES = (
    "subject-before.json",
    "subject-after.json",
    "git-before.json",
    "git-after.json",
    "provider-import.json",
    "provider-terminal.json",
    "context-plan.json",
    "transport.json",
    "source-seal.json",
    "route.json",
    "activity.json",
    "authority.json",
    "acquisition-receipts.jsonl",
    "runtime.json",
    "review-response.json",
    "provider.stdout",
    "provider.stderr",
)
_REVIEW_SCENARIOS = frozenset({"scenario-03", "scenario-11", "scenario-12", "scenario-14"})


def _receipt_bytes(path: Path) -> bytes:
    try:
        info = path.lstat()
    except OSError as exc:
        raise _Incomplete(f"receipt file is unavailable: {path.name}") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise _Incomplete(f"receipt file is not a regular file: {path.name}")
    # Run-owned evidence is private.  Group-read custody is allowed for a
    # dispatcher-owned handoff, but world-readable evidence is not.
    if stat.S_IMODE(info.st_mode) & 0o007:
        raise _Incomplete(f"receipt file is not private: {path.name}")
    try:
        value = path.read_bytes()
    except OSError as exc:
        raise _Incomplete(f"receipt file cannot be read: {path.name}") from exc
    if len(value) > _MAX_BYTES:
        raise _Incomplete("receipt file exceeds oracle bounds")
    return value


def _receipt_json(root: Path, name: str) -> tuple[Any, bytes]:
    data = _receipt_bytes(root / name)
    try:
        return json.loads(data.decode("utf-8")), data
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _Incomplete(f"receipt JSON is malformed: {name}") from exc


def _digest(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _receipt_snapshot(value: Any, name: str) -> Mapping[str, Any]:
    if isinstance(value, Mapping) and isinstance(value.get("files"), Mapping):
        value = value["files"]
    if not isinstance(value, Mapping) or not value:
        raise _Incomplete(f"receipt snapshot is missing: {name}")
    for path, identity in value.items():
        if not isinstance(path, str) or not path or Path(path).is_absolute() or "\\" in path:
            raise _Incomplete(f"receipt snapshot path is unsafe: {name}")
        if not isinstance(identity, Mapping):
            raise _Incomplete(f"receipt snapshot identity is malformed: {name}")
        if not _digest(identity.get("sha256")):
            raise _Incomplete(f"receipt snapshot digest is malformed: {name}")
        if type(identity.get("bytes")) is not int or identity["bytes"] < 0:
            raise _Incomplete(f"receipt snapshot byte count is malformed: {name}")
    return value


def _receipt_bundle(
    value: Any,
    *,
    scenario_id: str,
    subject: Path,
    before: Mapping[str, Any],
    expected_mode: str | None = None,
) -> dict[str, Any]:
    """Load one immutable execution-owned evidence bundle.

    The caller supplies only the physical bundle root.  All substantive facts
    are read from fixed files and bound to the root's identity manifest; a
    free-form arm dictionary cannot satisfy this contract.
    """
    if not isinstance(value, (str, os.PathLike)):
        raise _Incomplete("execution-owned receipt root is required")
    root = _physical_root(value)
    identity, _ = _receipt_json(root, "identity.json")
    if not isinstance(identity, Mapping) or identity.get("schema") != RECEIPT_SCHEMA:
        raise _Incomplete("execution-owned receipt identity is invalid")
    if identity.get("scenario_id") != scenario_id:
        raise _Incomplete("execution receipt scenario identity mismatch")
    if expected_mode is not None and identity.get("mode") != expected_mode:
        raise _Incomplete("execution receipt mode identity mismatch")
    if identity.get("owner") != "h-execution-package":
        raise _Incomplete("execution receipt owner identity is absent")
    subject_identity = identity.get("subject")
    if not isinstance(subject_identity, Mapping) or subject_identity.get("path") != str(subject):
        raise _Incomplete("execution receipt subject identity mismatch")
    files = identity.get("files")
    if not isinstance(files, Mapping) or set(files) != set(_RECEIPT_FILES):
        raise _Incomplete("execution receipt file inventory is incomplete")
    raw_files: dict[str, bytes] = {}
    for name in _RECEIPT_FILES:
        data = _receipt_bytes(root / name)
        record = files.get(name)
        if (not isinstance(record, Mapping) or type(record.get("bytes")) is not int
                or record["bytes"] != len(data)
                or not isinstance(record.get("sha256"), str)
                or record["sha256"] != _sha256(data)):
            raise _Incomplete(f"execution receipt file identity mismatch: {name}")
        raw_files[name] = data
    loaded: dict[str, Any] = {}
    for name in _RECEIPT_FILES:
        if name.endswith(".json"):
            try:
                loaded[name] = json.loads(raw_files[name].decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise _Incomplete(f"execution receipt JSON is malformed: {name}") from exc
    acquisitions: list[Mapping[str, Any]] = []
    for line in raw_files["acquisition-receipts.jsonl"].splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _Incomplete("acquisition receipt stream is malformed") from exc
        if not isinstance(item, Mapping):
            raise _Incomplete("acquisition receipt is not an object")
        acquisitions.append(item)
    loaded["acquisition-receipts.jsonl"] = acquisitions
    snapshots = {
        "before": _receipt_snapshot(loaded["subject-before.json"], "subject-before.json"),
        "after": _receipt_snapshot(loaded["subject-after.json"], "subject-after.json"),
    }
    expected_before = _before_snapshot(before)
    if dict(snapshots["before"]) != dict(expected_before):
        raise _Incomplete("execution receipt before snapshot differs from arm admission")
    actual_after = _snapshot(subject)
    if dict(snapshots["after"]) != actual_after:
        raise _Incomplete("execution receipt after snapshot differs from subject")
    git_before = loaded["git-before.json"]
    git_after = loaded["git-after.json"]
    provider_import = loaded["provider-import.json"]
    provider_terminal = loaded["provider-terminal.json"]
    context = loaded["context-plan.json"]
    delivery = loaded["transport.json"]
    source_seal = loaded["source-seal.json"]
    route = loaded["route.json"]
    activity = loaded["activity.json"]
    runtime = loaded["runtime.json"]
    review = loaded["review-response.json"]
    for name, item in (("git-before", git_before), ("git-after", git_after),
                       ("provider-import", provider_import),
                       ("provider-terminal", provider_terminal),
                       ("context", context), ("transport", delivery),
                       ("source-seal", source_seal), ("route", route),
                       ("activity", activity), ("runtime", runtime),
                       ("review", review)):
        if not isinstance(item, Mapping):
            raise _Incomplete(f"execution receipt section is malformed: {name}")
        if item.get("scenario_id") not in (None, scenario_id):
            raise _Incomplete(f"execution receipt section scenario mismatch: {name}")
    if not git_before or not git_after:
        raise _Incomplete("Git authority receipts are incomplete")
    authority = {
        "available": True,
        "git_before": git_before,
        "git_after": git_after,
        "git_unchanged": git_before == git_after,
        "unchanged": dict(snapshots["before"]) == actual_after,
        "subject_before": snapshots["before"],
        "subject_after": snapshots["after"],
        "permitted": activity.get("permitted"),
    }
    # The execution package stores the native APGR records verbatim.  A
    # caller-supplied wrapper (or a flattened ``selected_skills`` claim) is
    # deliberately not an admissible substitute for these records.
    if context.get("schema") != "apg.invocation-context/v1":
        raise _Incomplete("native invocation context receipt is required")
    if delivery.get("schema") != "apg.controlled-transmissions/v1" or delivery.get("coverage") != "complete":
        raise _Incomplete("native controlled-transmission receipt is incomplete")
    scope = {key: context.get(key) for key in ("run_id", "binding_id", "attempt_id")}
    if any(not isinstance(value, str) or not value for value in scope.values()):
        raise _Incomplete("native invocation context scope is incomplete")
    prospective = context.get("prospective_plan")
    if prospective is not None:
        if not isinstance(prospective, Mapping) or prospective.get("schema_version") != "apg.context-plan/v1":
            raise _Incomplete("native prospective context plan is malformed")
        for key, expected in scope.items():
            if prospective.get(key) != expected:
                raise _Incomplete("native prospective plan scope differs from context")
    instruction_plan = context.get("instruction_plan")
    context_transport = context.get("transport")
    if not isinstance(instruction_plan, Mapping) or instruction_plan.get("schema") != "apg.instruction-plan/v1":
        raise _Incomplete("native instruction plan is absent")
    if not isinstance(context_transport, Mapping) or not isinstance(context_transport.get("stdin"), Mapping):
        raise _Incomplete("native context transport identity is absent")
    stdin_identity = context_transport["stdin"]
    if (type(stdin_identity.get("bytes")) is not int or stdin_identity["bytes"] < 0
            or not _digest(stdin_identity.get("sha256"))):
        raise _Incomplete("native stdin identity is malformed")
    runner_stdin = instruction_plan.get("runner_stdin")
    if not isinstance(runner_stdin, Mapping) or runner_stdin != stdin_identity:
        raise _Incomplete("native runner stdin identity differs from context transport")
    plan_reference = delivery.get("plan")
    if not isinstance(plan_reference, Mapping) or plan_reference.get("schema") != "apg.context-reference/v1":
        raise _Incomplete("native transport plan reference is absent")
    context_raw = raw_files["context-plan.json"]
    if (plan_reference.get("bytes") != len(context_raw)
            or plan_reference.get("sha256") != _sha256(context_raw)):
        raise _Incomplete("native transport plan reference does not bind context bytes")
    events = delivery.get("events")
    if not isinstance(events, list) or not events:
        raise _Incomplete("native controlled-transmission events are absent")
    event_ids: set[str] = set()
    for event in events:
        if not isinstance(event, Mapping) or event.get("schema") != "apg.acquisition-event/v1":
            raise _Incomplete("native transmission event is malformed")
        if any(event.get(key) != expected for key, expected in scope.items()):
            raise _Incomplete("native transmission event scope differs from context")
        event_id = event.get("event_id")
        if not _digest(event_id) or event_id in event_ids:
            raise _Incomplete("native transmission event identity is malformed")
        event_ids.add(event_id)
        if type(event.get("controlled_bytes")) is not int or event["controlled_bytes"] < 0:
            raise _Incomplete("native transmission byte identity is malformed")
        if not _digest(event.get("payload_sha256")):
            raise _Incomplete("native transmission payload identity is malformed")
    prompts = [event for event in events if event.get("channel") == "prompt" and event.get("phase") == "initial"]
    if len(prompts) != 1:
        raise _Incomplete("native initial prompt delivery is not bound to runner stdin")
    prompt = prompts[0]
    direct_prompt = prompt.get("payload_sha256") == stdin_identity.get("sha256") and prompt.get("controlled_bytes") == stdin_identity.get("bytes")
    transformed_prompt = prompt.get("input_view") == {"sha256": stdin_identity.get("sha256"), "bytes": stdin_identity.get("bytes")}
    if not (direct_prompt or transformed_prompt):
        raise _Incomplete("native initial prompt delivery is not bound to runner stdin")
    if provider_import.get("schema") != "apg.h-provider-import/v1":
        raise _Incomplete("provider import receipt schema is invalid")
    if not isinstance(provider_terminal.get("exit_code"), int):
        raise _Incomplete("provider terminal exit identity is absent")
    stdout_identity = {"bytes": len(raw_files["provider.stdout"]),
                       "sha256": _sha256(raw_files["provider.stdout"])}
    stderr_identity = {"bytes": len(raw_files["provider.stderr"]),
                       "sha256": _sha256(raw_files["provider.stderr"])}
    if provider_import.get("raw") != stdout_identity:
        raise _Incomplete("provider import does not bind retained stdout")
    if provider_terminal.get("stdout") != stdout_identity or provider_terminal.get("stderr") != stderr_identity:
        raise _Incomplete("provider terminal does not bind retained streams")
    # A source-seal section is always an owned receipt.  In particular, a
    # missing/``null`` schema must not be promoted to an accepted seal by the
    # oracle.  The fixture owner uses the explicit not-applicable schema when
    # it deliberately has no source-readiness authority.
    if source_seal.get("schema") not in {"apg.h-readiness-seal/v1", "apg.h-source-seal/v1", "apg.h-not-applicable/v1"}:
        raise _Incomplete("source seal receipt schema is invalid")
    if not route.get("provider") or not route.get("profile") or not route.get("binding_id"):
        raise _Incomplete("provider route receipt is incomplete")
    if route.get("binding_id") != context.get("binding_id"):
        raise _Incomplete("provider route binding differs from native context")
    if runtime.get("schema") not in {"apg.h-runtime-inputs/v2", "apg.h-runtime-observation/v1"}:
        raise _Incomplete("runtime receipt schema is invalid")
    if review.get("schema") not in {"apg.h-review-response/v1", "apg.h-evaluation-response/v1", "apg.h-not-applicable/v1"}:
        raise _Incomplete("review receipt schema is invalid")
    # Acquisition rows are canonical native event files, not model-authored
    # summaries.  Validate their file identity and event scope here so the
    # substantive oracle can safely derive facts from them.
    for row in acquisitions:
        event = row.get("event")
        path = row.get("path")
        if not isinstance(event, Mapping) or event.get("schema") != "apg.acquisition-event/v1":
            raise _Incomplete("native acquisition event is malformed")
        if any(event.get(key) != expected for key, expected in scope.items()):
            raise _Incomplete("native acquisition event scope differs from context")
        if not isinstance(path, str) or not path.startswith("acquisitions/") or Path(path).is_absolute() or "\\" in path:
            raise _Incomplete("native acquisition receipt path is unsafe")
        name = Path(path).name
        if (not name.startswith("event-") or not name.endswith(".jsonl")
                or name[6:-6] != event.get("event_id")):
            raise _Incomplete("native acquisition receipt path does not bind event identity")
        if type(row.get("bytes")) is not int or row["bytes"] < 0 or not _digest(row.get("sha256")):
            raise _Incomplete("native acquisition receipt identity is malformed")
        if event.get("event_id") not in event_ids:
            # A retained acquisition may be observed before a final transport
            # trace (for example recovery), but it still needs a native event
            # identity.  Do not silently accept arbitrary IDs.
            if not _digest(event.get("event_id")):
                raise _Incomplete("native acquisition event identity is malformed")
    if activity.get("schema") != "apg.h-execution-activity/v1":
        raise _Incomplete("execution activity receipt schema is invalid")
    for key in ("attempts", "retries", "restarts", "revision_observation", "restart_observation"):
        if key not in activity:
            raise _Incomplete(f"execution activity receipt lacks {key}")
    if activity.get("attempts") != ["one"] or activity.get("retries") != 0 or activity.get("restarts") != 0:
        raise _Incomplete("execution retry/restart evidence is not single-use")
    if scenario_id == "scenario-12":
        recovery_receipt = activity.get("recovery_receipt")
        if (not isinstance(recovery_receipt, Mapping)
                or recovery_receipt.get("schema") != "apg.h-recovery-receipt/v1"
                or recovery_receipt.get("status") != "complete"):
            raise _Incomplete("Scenario 12 retained recovery receipt is incomplete")
    return {
        "root": root,
        "identity": identity,
        "before": snapshots["before"],
        "after": snapshots["after"],
        "authority": authority,
        "context": context,
        "delivery": delivery,
        "context_raw": context_raw,
        "context_reference": plan_reference,
        "events": events,
        "acquisitions": acquisitions,
        "runtime": runtime,
        "route": route,
        "activity": activity,
        "provider_import": provider_import,
        "provider_terminal": provider_terminal,
        "source_seal": source_seal,
        "review": review,
    }


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str) + "\n").encode("utf-8")


def _evidence(kind: str, value: Any) -> dict[str, Any]:
    data = value if isinstance(value, bytes) else _canonical(value)
    return {"kind": str(kind), "sha256": _sha256(data), "bytes": len(data)}


def _receipt(oracle: Mapping[str, Any], status: str, facts: list[tuple[str, Any]]) -> dict[str, Any]:
    if status not in {"pass", "fail", "unavailable"}:
        raise ValueError("invalid task-oracle status")
    evidence = [_evidence(kind, value) for kind, value in facts]
    if not evidence:
        evidence = [_evidence("oracle-decision", {"status": status})]
    return {"schema": SCHEMA, "oracle": deepcopy(dict(oracle)), "status": status, "evidence": evidence}


def _physical_root(value: Any) -> Path:
    if isinstance(value, (str, os.PathLike)):
        root = Path(value)
    else:
        raise _Incomplete("subject root is required")
    if not root.is_absolute():
        root = root.absolute()
    try:
        root.stat()
    except OSError as exc:
        raise _Incomplete("subject root is unavailable") from exc
    # A physical subject root is required.  Ancestor aliases such as the
    # macOS /var -> /private/var compatibility path are harmless; only the
    # subject entry itself may not be a symlink.
    if root.is_symlink():
        raise _Incomplete("subject root must be physical")
    if not root.is_dir():
        raise _Incomplete("subject root must be a directory")
    return root


def _snapshot(root: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    total = 0
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in _EPHEMERAL_PARTS for part in relative.parts):
            continue
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise _Incomplete("subject symlink is not admissible")
        if stat.S_ISDIR(info.st_mode):
            continue
        if not stat.S_ISREG(info.st_mode):
            raise _Incomplete("subject contains a nonregular file")
        data = path.read_bytes()
        total += len(data)
        if len(result) >= _MAX_FILES or total > _MAX_BYTES:
            raise _Incomplete("subject exceeds oracle bounds")
        result[str(relative)] = {"bytes": len(data), "sha256": _sha256(data), "mode": stat.S_IMODE(info.st_mode)}
    return result


def _before_snapshot(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise _Incomplete("before authority snapshot is required")
    if isinstance(value.get("files"), Mapping):
        value = value["files"]
    if not value:
        raise _Incomplete("empty before authority snapshot")
    return value


def _allowed(path: str, scopes: list[str]) -> bool:
    for scope in scopes:
        if not isinstance(scope, str):
            continue
        scope = scope.strip("/")
        if scope and (path == scope or path.startswith(scope + "/")):
            return True
    return False


def _mutation_facts(root: Path, before: Any, scopes: list[str]) -> tuple[bool, dict[str, Any]]:
    before_map = _before_snapshot(before)
    after = _snapshot(root)
    paths = set(before_map) | set(after)
    changed = sorted(path for path in paths if before_map.get(path) != after.get(path))
    unexpected = [path for path in changed if not _allowed(path, scopes)]
    return not unexpected, {"changed": changed, "unexpected": unexpected, "allowed_scopes": scopes}


def _authority(arm_evidence: Mapping[str, Any]) -> Mapping[str, Any] | None:
    if isinstance(arm_evidence, Mapping) and any(key in arm_evidence for key in ("git_before", "git_after", "git_unchanged", "unchanged")):
        return arm_evidence
    direct = arm_evidence.get("authority")
    if isinstance(direct, Mapping):
        return direct
    direct = arm_evidence.get("git_authority")
    if isinstance(direct, Mapping):
        return direct
    return None


def _authority_check(scenario_id: str, arm_evidence: Mapping[str, Any]) -> tuple[bool, dict[str, Any]]:
    authority = _authority(arm_evidence)
    if scenario_id in _AUTHORITY_EVIDENCE_REQUIRED and authority is None:
        raise _Incomplete("authority identity is absent")
    if authority is None:
        return True, {"authority_present": False}
    if authority.get("available") is False:
        return False, {"authority_present": True, "available": False}
    if scenario_id in _AUTHORITY_EVIDENCE_REQUIRED:
        required = ("git_before", "git_after", "git_unchanged")
        if any(key not in authority for key in required):
            raise _Incomplete("complete before/after Git authority identity is absent")
        if authority.get("git_unchanged") is not True:
            return False, {"authority_present": True, "git_unchanged": authority.get("git_unchanged")}
        if authority.get("git_before") != authority.get("git_after"):
            return False, {"authority_present": True, "git_unchanged": False}
        if authority.get("unchanged") is not True:
            return False, {"authority_present": True, "unchanged": authority.get("unchanged")}
    drift_keys = (
        "head_drift_observed",
        "index_drift_observed",
        "worktree_drift_observed",
        "subject_drift_observed",
        "target_repository_head_changed",
        "target_repository_index_changed",
        "target_repository_worktree_changed",
    )
    drift = [key for key in drift_keys if authority.get(key) is True]
    if authority.get("unchanged") is False or authority.get("immutability_fence_preserved") is False:
        drift.append("unchanged")
    for before_key, after_key in (("before", "after"), ("head_before", "head_after"), ("index_before", "index_after"), ("worktree_before", "worktree_after")):
        if before_key in authority and after_key in authority and authority[before_key] != authority[after_key]:
            drift.append(before_key)
    return not drift, {"authority_present": True, "drift": drift}


def _native_context(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or value.get("schema") != "apg.invocation-context/v1":
        raise _Incomplete("native invocation context is required")
    return value


def _plan(context: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return the source-owned prospective plan from one native context record.

    The native context record is the only accepted container.  In particular,
    this function intentionally does not search descendants for convenient
    keys: doing so would turn a model-authored assertion into mechanism
    evidence.
    """
    context = _native_context(context)
    plan = context.get("prospective_plan")
    if not isinstance(plan, Mapping) or plan.get("schema_version") != "apg.context-plan/v1":
        raise _Incomplete("native prospective context plan is absent")
    for key in ("run_id", "binding_id", "attempt_id"):
        if plan.get(key) != context.get(key):
            raise _Incomplete("native prospective plan scope differs from context")
    if not isinstance(plan.get("reasons"), list) or not all(isinstance(item, str) and item for item in plan["reasons"]):
        raise _Incomplete("native prospective plan reasons are malformed")
    if type(plan.get("budget_passed")) is not bool or type(plan.get("required_satisfied")) is not bool:
        raise _Incomplete("native prospective plan qualification is incomplete")
    return plan


def _fact(plan: Mapping[str, Any], key: str, default: Any = None) -> Any:
    """Read only a direct native-plan field; never recurse into claims."""
    if not isinstance(plan, Mapping):
        raise _Incomplete("native plan is malformed")
    return plan[key] if key in plan else default


def _decisions(plan: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    decisions = plan.get("decisions")
    if not isinstance(decisions, list):
        raise _Incomplete("native plan decisions are absent")
    result: list[Mapping[str, Any]] = []
    for decision in decisions:
        if not isinstance(decision, Mapping):
            raise _Incomplete("native plan decision is malformed")
        for key in ("requested_id", "selected_id", "status", "reason", "required"):
            if key not in decision:
                raise _Incomplete(f"native plan decision lacks {key}")
        if not all(isinstance(decision[key], str) and decision[key] for key in ("requested_id", "status", "reason")):
            raise _Incomplete("native plan decision identity is malformed")
        if decision["selected_id"] is not None and (not isinstance(decision["selected_id"], str) or not decision["selected_id"]):
            raise _Incomplete("native plan selected identity is malformed")
        if type(decision["required"]) is not bool:
            raise _Incomplete("native plan required flag is malformed")
        result.append(decision)
    return result


def _selected(plan: Mapping[str, Any]) -> list[str]:
    """Derive selected IDs from native snapshots and decision rows."""
    snapshots = plan.get("selected_snapshots")
    if not isinstance(snapshots, list):
        raise _Incomplete("native selected snapshots are absent")
    ids: list[str] = []
    for snapshot in snapshots:
        if not isinstance(snapshot, Mapping) or not isinstance(snapshot.get("qualified_id"), str) or not snapshot["qualified_id"]:
            raise _Incomplete("native selected snapshot identity is malformed")
        if snapshot["qualified_id"] in ids:
            raise _Incomplete("native selected snapshot identity is duplicated")
        ids.append(snapshot["qualified_id"])
    selected_decisions = [decision.get("selected_id") for decision in _decisions(plan)
                          if decision.get("status") == "selected" and decision.get("selected_id")]
    if sorted(selected_decisions) != sorted(ids) or len(selected_decisions) != len(ids):
        raise _Incomplete("native selected snapshots differ from selected decisions")
    return ids


def _mechanism_facts(bundle: Mapping[str, Any]) -> tuple[Mapping[str, Any], list[str], dict[str, Any]]:
    context = _native_context(bundle.get("context"))
    plan = _plan(context)
    selected = _selected(plan)
    events = bundle.get("events")
    if not isinstance(events, list):
        raise _Incomplete("native transport events are absent")
    return context, selected, {
        "requested_mode": context.get("requested_mode"),
        "effective_mode": context.get("effective_mode"),
        "reason": context.get("reason"),
        "plan_effective_mode": plan.get("effective_mode"),
        "plan_reasons": list(plan.get("reasons", [])),
        "selected": selected,
        "budget_passed": plan.get("budget_passed"),
        "required_satisfied": plan.get("required_satisfied"),
        "event_count": len(events),
        "channels": sorted({event.get("channel") for event in events if isinstance(event, Mapping)}),
    }


def _static_delivery_check(scenario_id: str, bundle: Mapping[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Qualify a static arm from native delivery and source custody facts.

    Static preparation deliberately has no prospective planner result.  The
    static arm therefore proves the native transport, source configuration and
    instruction components it actually retained; adaptive selection,
    fallback, acquisition and recovery claims remain owned by the adaptive
    path and are never synthesized here.
    """
    if not isinstance(bundle, Mapping):
        raise _Incomplete("static delivery bundle is absent")
    context = _native_context(bundle.get("context"))
    route = bundle.get("route")
    if not isinstance(route, Mapping):
        raise _Incomplete("static delivery route is absent")
    source = route.get("source_identity")
    if not isinstance(source, Mapping) or source.get("schema") != "apg.h-source-binding/v1":
        raise _Incomplete("static source binding is absent")
    if source.get("owner") != "testing.h_eval.preregistration":
        raise _Incomplete("static source binding owner is invalid")
    if source.get("scenario_id") not in (None, scenario_id):
        raise _Incomplete("static source binding scenario differs")
    if source.get("bindings_path") != "testing/h_eval/scenario-bindings.json" or not _digest(source.get("route_sha256")):
        raise _Incomplete("static source binding identity is incomplete")
    identity_sources = source.get("identity_sources")
    source_hashes = source.get("source_sha256")
    bindings_path = "testing/h_eval/scenario-bindings.json"
    if (not isinstance(identity_sources, list) or not identity_sources
            or any(not isinstance(item, str) or not item for item in identity_sources)
            or not isinstance(source_hashes, Mapping)):
        raise _Incomplete("static source configuration identity is incomplete")
    source_paths = [item for item in identity_sources if item != bindings_path]
    if (not _digest(source.get("bindings_sha256")) or not source_paths
            or any(not _digest(source_hashes.get(item)) for item in source_paths)):
        raise _Incomplete("static source configuration identity is incomplete")
    configuration = context.get("configuration")
    if (not isinstance(configuration, list) or any(not isinstance(item, str) or not item for item in configuration)
            or len(set(configuration)) != len(configuration)):
        raise _Incomplete("native static configuration is malformed")
    configuration_matches = configuration == identity_sources

    if context.get("requested_mode") != "static" or context.get("effective_mode") != "static":
        return False, {"status": "not_static", "requested_mode": context.get("requested_mode"),
                       "effective_mode": context.get("effective_mode")}
    if context.get("planned") is not False or context.get("prospective_plan") is not None:
        return False, {"status": "adaptive_claim_in_static_arm", "planned": context.get("planned"),
                       "prospective_plan": context.get("prospective_plan") is not None}
    role_binding = route.get("role_binding")
    if not isinstance(role_binding, Mapping):
        raise _Incomplete("static source role binding is absent")
    if (role_binding.get("binding_id") != route.get("binding_id")
            or role_binding.get("binding_id") != context.get("binding_id")
            or not isinstance(role_binding.get("roles"), list)
            or role_binding.get("roles") != context.get("roles")):
        raise _Incomplete("static role binding differs from native context")
    allowed_tools = role_binding.get("allowed_tools")
    if (not isinstance(allowed_tools, list) or not allowed_tools
            or any(not isinstance(item, str) or not item for item in allowed_tools)
            or len(set(allowed_tools)) != len(allowed_tools)):
        raise _Incomplete("static role tool scope is malformed")

    instruction_plan = context.get("instruction_plan")
    components = instruction_plan.get("components") if isinstance(instruction_plan, Mapping) else None
    if (not isinstance(instruction_plan, Mapping)
            or instruction_plan.get("schema") != "apg.instruction-plan/v1"
            or not isinstance(components, list) or not components):
        raise _Incomplete("native static instruction custody is absent")
    component_ids: list[str] = []
    for component in components:
        if not isinstance(component, Mapping) or not isinstance(component.get("id"), str) or not component["id"]:
            raise _Incomplete("native static instruction component is malformed")
        if component["id"] in component_ids:
            raise _Incomplete("native static instruction component is duplicated")
        component_ids.append(component["id"])
        if any(key in component for key in ("authority_preserved", "selected_skills", "dispatch_success", "task_oracle", "coverage")):
            raise _Incomplete("native static instruction component contains a claimed result")
        if component["id"] == "evaluation-response-contract":
            if (component.get("schema") != "apg.h-evaluation-contract-identity/v1"
                    or component.get("required") is not True):
                raise _Incomplete("native static response-contract identity is malformed")
        elif not isinstance(component.get("source_path"), str) or not component["source_path"]:
            raise _Incomplete("native static instruction source path is absent")
        if type(component.get("bytes")) is not int or component["bytes"] <= 0 or not _digest(component.get("sha256")):
            raise _Incomplete("native static instruction source identity is malformed")
    standing = next((component for component in components if component.get("id") == "provider-standing"), None)
    if not isinstance(standing, Mapping):
        return False, {"status": "provider_standing_component_missing", "components": component_ids}

    contract_ok = True
    contract_identity: dict[str, Any] | None = None
    if scenario_id in _REVIEW_SCENARIOS:
        from . import response_contract
        contract_bytes = ("\n\nEvaluation scenario: " + scenario_id + "\n"
                          + response_contract.instructions()).encode("utf-8")
        contract_identity = {"schema": "apg.h-evaluation-contract-identity/v1",
                             "bytes": len(contract_bytes), "sha256": _sha256(contract_bytes), "required": True}
        contract = next((component for component in components
                         if component.get("id") == "evaluation-response-contract"), None)
        contract_ok = (isinstance(contract, Mapping)
                       and {key: contract.get(key) for key in contract_identity} == contract_identity)

    events = bundle.get("events")
    if not isinstance(events, list):
        raise _Incomplete("native static delivery events are absent")
    initial_prompts = [event for event in events if isinstance(event, Mapping)
                       and event.get("schema") == "apg.acquisition-event/v1"
                       and event.get("channel") == "prompt" and event.get("phase") == "initial"]
    if len(initial_prompts) != 1:
        return False, {"status": "initial_prompt_delivery_missing", "initial_prompt_events": len(initial_prompts)}
    late_mechanism_events = [event for event in events if isinstance(event, Mapping)
                             and event.get("phase") == "late"
                             and event.get("channel") in {"mcp", "mcp_result", "tool_result", "recovery_read"}]
    acquisition_rows = bundle.get("acquisitions")
    if not isinstance(acquisition_rows, list):
        raise _Incomplete("native static acquisition receipt list is absent")
    late_mechanism_events.extend(
        row.get("event") for row in acquisition_rows
        if isinstance(row, Mapping) and isinstance(row.get("event"), Mapping)
        and row["event"].get("phase") == "late"
        and row["event"].get("channel") in {"mcp", "mcp_result", "tool_result", "recovery_read"}
    )
    facts = {
        "status": "static_delivery_observed" if configuration_matches and contract_ok and not late_mechanism_events else "static_delivery_rejected",
        "requested_mode": context.get("requested_mode"),
        "effective_mode": context.get("effective_mode"),
        "planned": context.get("planned"),
        "prospective_plan_present": context.get("prospective_plan") is not None,
        "configuration": list(configuration),
        "configuration_matches_source": configuration_matches,
        "source_identity_sources": list(identity_sources),
        "instruction_components": component_ids,
        "initial_prompt_events": len(initial_prompts),
        "evaluation_contract": contract_identity,
        "evaluation_contract_matches": contract_ok,
        "late_mechanism_events": len(late_mechanism_events),
    }
    return configuration_matches and contract_ok and not late_mechanism_events, facts


def _acquisition_check(scenario_id: str, arm_evidence: Mapping[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Qualify a native acquisition event against the native selection plan."""
    if not isinstance(arm_evidence, Mapping) or not isinstance(arm_evidence.get("context"), Mapping):
        raise _Incomplete("native acquisition bundle is required")
    context = _native_context(arm_evidence["context"])
    if scenario_id == "scenario-10" and context.get("requested_mode") == "static":
        static_ok, static_facts = _static_delivery_check(scenario_id, arm_evidence)
        static_facts["acquisition_required"] = False
        static_facts["late_mcp_required"] = False
        return static_ok, static_facts
    plan = _plan(context)
    selected = _selected(plan)
    decisions = _decisions(plan)
    rows = arm_evidence.get("acquisitions")
    if not isinstance(rows, list):
        raise _Incomplete("retained native acquisition rows are absent")
    source_candidates: list[tuple[Mapping[str, Any], Mapping[str, Any]]] = []
    delivery_candidates: list[tuple[Mapping[str, Any], Mapping[str, Any]]] = []
    selected_decisions = {decision.get("selected_id"): decision for decision in decisions
                          if decision.get("status") == "selected" and decision.get("selected_id") in selected}
    for row in rows:
        if not isinstance(row, Mapping):
            raise _Incomplete("native acquisition row is malformed")
        event = row.get("event")
        if not isinstance(event, Mapping) or event.get("schema") != "apg.acquisition-event/v1":
            raise _Incomplete("native acquisition event is malformed")
        # Preparation and materialization events retain the source identity;
        # response events retain the actual APGR transport.  Neither one is
        # sufficient on its own for a delivered-body oracle.
        if event.get("kind") in {"preparation_response", "recovery_candidate"}:
            continue
        candidate_id = event.get("selected") or event.get("requested")
        if candidate_id not in selected_decisions:
            continue
        decision = selected_decisions[candidate_id]
        content_identity = event.get("content_identity")
        valid_identities = {decision.get("content_identity")}
        whole_source = decision.get("whole_source")
        body_only = decision.get("body_only")
        if isinstance(whole_source, Mapping):
            valid_identities.add(whole_source.get("sha256"))
        if isinstance(body_only, Mapping):
            valid_identities.add(body_only.get("sha256"))
        is_source = event.get("kind") in {"materialized", "available"}
        if is_source:
            if content_identity not in valid_identities:
                continue
            source_candidates.append((event, decision))
            continue
        if event.get("channel") not in {"mcp", "mcp_result", "tool_result", "recovery_read"} and event.get("kind") != "response_delivered":
            continue
        # The native response frame carries the frame digest, not the skill
        # body digest.  Its relation to the body is established by the
        # source-owned materialization row above.
        delivery_candidates.append((event, decision))
    if not source_candidates or not delivery_candidates:
        return False, {"status": "missing_native_source_or_delivery", "selected": selected,
                       "source_events": len(source_candidates), "delivery_events": len(delivery_candidates)}
    event, decision = delivery_candidates[-1]
    source_event, _ = source_candidates[-1]
    body_only = decision.get("body_only")
    body_sha = body_only.get("sha256") if isinstance(body_only, Mapping) else None
    if scenario_id in _CANONICAL_BODY_SHA and body_sha != _CANONICAL_BODY_SHA[scenario_id]:
        return False, {"status": "canonical_body_mismatch", "selected": decision.get("selected_id"), "body_sha256": body_sha}
    return True, {
        "status": "native_delivery_observed",
        "selected": decision.get("selected_id"),
        "event_id": event.get("event_id"),
        "source_event_id": source_event.get("event_id"),
        "channel": event.get("channel"),
        "kind": event.get("kind"),
        "content_identity": source_event.get("content_identity"),
        "payload_sha256": event.get("payload_sha256"),
        "controlled_bytes": event.get("controlled_bytes"),
    }


def _normalized_source(value: str) -> str:
    """Normalize only line endings and trailing whitespace for source spans."""
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in value.split("\n")).strip("\n")


def _review_source_files(scenario_id: str) -> Mapping[str, bytes]:
    """Load the immutable source-owned bytes used by review facts."""
    try:
        from . import subjects
        return subjects.subject_files(scenario_id)
    except (OSError, UnicodeError, ValueError):
        return {}


def _source_span(finding: Mapping[str, Any], source: bytes) -> tuple[int, int, list[str]] | None:
    """Return a validated one-based span and its exact source lines."""
    span = finding.get("span")
    if not isinstance(span, Mapping) or set(span) != {"start", "end"}:
        return None
    start, end = span.get("start"), span.get("end")
    if (type(start) is not int or type(end) is not int or start < 1
            or end < start):
        return None
    try:
        text = source.decode("utf-8")
    except UnicodeDecodeError:
        return None
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if end > len(lines):
        return None
    snippet = finding.get("snippet")
    if not isinstance(snippet, str):
        return None
    actual = "\n".join(lines[start - 1:end])
    if _normalized_source(snippet) != _normalized_source(actual):
        return None
    return start, end, lines[start - 1:end]


def _return_expression(line: str, *, nil_pair: bool) -> str | None:
    """Extract the one source-owned return expression from a reviewed line."""
    pattern = (r"\breturn\s+nil\s*,\s*nil\b" if nil_pair
               else r'\breturn\s+"[^"\\]*(?:\\.[^"\\]*)*"')
    matches = re.findall(pattern, line)
    return matches[0] if len(matches) == 1 else None


def _optional_evidence_matches(
    evidence: Mapping[str, Any],
    expected: Mapping[str, Any],
    *,
    allowed: frozenset[str],
) -> bool:
    """Validate optional objective fields without making them mandatory."""
    optional = {"link_target", "return_expression", "declaration"}
    if any(key in evidence and key not in allowed for key in optional):
        return False
    for key in allowed:
        if key not in evidence:
            continue
        observed = evidence[key]
        wanted = expected.get(key)
        if key == "declaration":
            if not isinstance(observed, Mapping) or observed != wanted:
                return False
        elif not isinstance(observed, str) or not isinstance(wanted, str):
            return False
        elif _normalized_source(observed) != _normalized_source(wanted):
            return False
    return True


def _generic_evidence_matches(
    finding: Mapping[str, Any],
    evidence: Mapping[str, Any],
    source_files: Mapping[str, bytes],
) -> bool:
    """Bind any finding to source bytes before applying a scenario fact."""
    if not isinstance(finding, Mapping) or not isinstance(evidence, Mapping):
        return False
    path = finding.get("path")
    source_path = evidence.get("source_path")
    if not isinstance(path, str) or source_path != path:
        return False
    source = source_files.get(path)
    span = _source_span(evidence, source) if isinstance(source, bytes) else None
    if span is None:
        return False
    snippet = _normalized_source("\n".join(span[2]))
    link_target = evidence.get("link_target")
    if link_target is not None:
        if not isinstance(link_target, str):
            return False
        links = [match.group(1) for line in span[2]
                 for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", line)]
        if link_target not in links:
            return False
    return_expression = evidence.get("return_expression")
    if return_expression is not None:
        if (not isinstance(return_expression, str)
                or _normalized_source(return_expression) not in snippet):
            return False
    declaration = evidence.get("declaration")
    if declaration is not None:
        if (not isinstance(declaration, Mapping) or not declaration
                or any(not isinstance(key, str) or not isinstance(value, str)
                       for key, value in declaration.items())):
            return False
        normalized_lines = {" ".join(line.split()) for line in span[2]}
        if any(f"{key} {value}" not in normalized_lines
               for key, value in declaration.items()):
            return False
    return True


def _return_evidence_matches(
    evidence: Mapping[str, Any],
    source: bytes,
    *,
    nil_pair: bool,
) -> bool:
    span = _source_span(evidence, source)
    if span is None or span[0] != span[1]:
        return False
    observed = _return_expression(span[2][0], nil_pair=nil_pair)
    if observed is None:
        return False
    return _optional_evidence_matches(
        evidence,
        {"return_expression": observed},
        allowed=frozenset({"return_expression"}),
    )


def _review_evidence_matches(
    scenario_id: str,
    finding: Mapping[str, Any],
    evidence: Mapping[str, Any],
    source_files: Mapping[str, bytes],
) -> bool:
    """Check one objective evidence item against frozen source bytes."""
    fact = _REVIEW_FACT_BY_PATH.get((scenario_id, finding.get("path")))
    if fact is None or not isinstance(evidence, Mapping):
        return False
    path = fact["path"]
    source = source_files.get(path)
    if not isinstance(source, bytes) or evidence.get("source_path") != path:
        return False
    kind = fact.get("kind")
    if kind == "absent_link_target":
        span = _source_span(evidence, source)
        if span is None or span[0] != span[1]:
            return False
        match = re.fullmatch(r".*\[[^\]]+\]\(([^)]+)\).*", span[2][0].strip())
        if match is None:
            return False
        target = match.group(1)
        if not _optional_evidence_matches(
            evidence,
            {"link_target": target},
            allowed=frozenset({"link_target"}),
        ):
            return False
        target_path, separator, _fragment = target.partition("#")
        if not separator or not target_path:
            target_path = target
        if (not target_path or target_path.startswith(("/", "\\"))
                or ".." in Path(target_path).parts):
            return False
        return target_path not in source_files
    if kind == "adjacent_heading_lines":
        span = _source_span(evidence, source)
        if span is None or len(span[2]) != 2:
            return False
        try:
            lines = source.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n").split("\n")
        except UnicodeDecodeError:
            return False
        if lines and lines[-1] == "":
            lines.pop()
        heading_indexes = [index for index, line in enumerate(lines) if line.startswith("#")]
        if not heading_indexes:
            return False
        heading = heading_indexes[0]
        return (span[0] == heading + 1 and span[1] == heading + 2
                and lines[heading].strip() == span[2][0].strip()
                and lines[heading + 1].strip() != ""
                and _optional_evidence_matches(
                    evidence, {}, allowed=frozenset()))
    if kind == "nil_pair_return":
        return _return_evidence_matches(evidence, source, nil_pair=True)
    if kind == "constant_return":
        return _return_evidence_matches(evidence, source, nil_pair=False)
    if kind == "field_declarations":
        span = _source_span(evidence, source)
        if span is None:
            return False
        try:
            text = source.decode("utf-8")
        except UnicodeDecodeError:
            return False
        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        fields: dict[str, str] = {}
        field_indexes: dict[str, int] = {}
        for index, line in enumerate(lines):
            match = re.fullmatch(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s+([A-Za-z_][A-Za-z0-9_]*(?:\[\])?)\s*", line)
            if match:
                fields[match.group(1)] = match.group(2)
                field_indexes[match.group(1)] = index
        expected = {name: fields.get(name) for name in ("ID", "Name")}
        if any(value is None for value in expected.values()):
            return False
        first = min(field_indexes["ID"], field_indexes["Name"])
        last = max(field_indexes["ID"], field_indexes["Name"])
        return (span[0] == first + 1 and span[1] == last + 1
                and _optional_evidence_matches(
                    evidence, {"declaration": expected},
                    allowed=frozenset({"declaration"})))
    return False


def _review_fact_matches(
    scenario_id: str,
    finding: Mapping[str, Any],
    source_files: Mapping[str, bytes] | None = None,
) -> bool:
    """Check every objective evidence item against the source-owned fact."""
    if not isinstance(finding, Mapping):
        return False
    source_files = source_files if source_files is not None else _review_source_files(scenario_id)
    evidence = finding.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        return False
    return all(
        _review_evidence_matches(scenario_id, finding, item, source_files)
        for item in evidence
    )


def _review_check(scenario_id: str, arm_evidence: Mapping[str, Any], provider_result: Mapping[str, Any]) -> tuple[bool, dict[str, Any]]:
    # Only a validated response-contract envelope may supply findings.  The
    # previous fallback to ``structured_findings`` accepted a model-authored
    # claim object and made the oracle recursive.
    review = arm_evidence.get("review_response")
    if not isinstance(review, Mapping) and isinstance(provider_result, Mapping):
        review = provider_result.get("review_response")
    if not isinstance(review, Mapping):
        raise _Incomplete("structured review response is absent")
    try:
        from . import response_contract
        review = response_contract.validate(review, scenario_id=scenario_id)
    except (ImportError, response_contract.ResponseContractError) as exc:
        raise _Incomplete("structured review response is malformed") from exc
    findings: list[Any] = review["findings"]
    normalized_paths: set[str] = set()
    for finding in findings:
        normalized_paths.add(finding["path"])
    required = _REVIEW_REQUIRED_PATHS.get(scenario_id, frozenset())
    source_files = _review_source_files(scenario_id)
    generic_evidence = [
        {
            "path": finding["path"],
            "matches": all(
                _generic_evidence_matches(finding, evidence, source_files)
                for evidence in finding["evidence"]
            ),
        }
        for finding in findings
    ]
    generic_ok = all(item["matches"] for item in generic_evidence)
    if not required:
        return bool(findings) and generic_ok, {
            "finding_count": len(findings),
            "generic_evidence": generic_evidence,
        }
    findings_by_path: dict[str, list[Mapping[str, Any]]] = {}
    for finding in findings:
        findings_by_path.setdefault(finding["path"], []).append(finding)
    # Every supplied objective evidence item for every required-path finding
    # must bind to the same frozen fact.  This keeps an extra forged item or
    # duplicate finding from rescuing a response that contains wrong evidence.
    observed_facts: dict[str, bool] = {}
    for path in required:
        candidates = findings_by_path.get(path, [])
        observed_facts[path] = bool(candidates) and all(
            _review_evidence_matches(scenario_id, candidate, evidence, source_files)
            for candidate in candidates
            for evidence in candidate.get("evidence", [])
        )
    facts_ok = all(observed_facts.get(path) is True for path in required)
    return required <= normalized_paths and facts_ok and generic_ok, {
        "finding_count": len(findings),
        "required_paths": sorted(required),
        "observed_paths": sorted(normalized_paths),
        "generic_evidence": generic_evidence,
        "semantic_facts": [{"path": path, "matches": value}
                           for path, value in sorted(observed_facts.items())],
        "response": {
            "schema": review["schema"],
            "scenario_id": review["scenario_id"],
        },
    }


def _provider_check(provider_result: Any, *, scenario_id: str | None = None) -> tuple[bool, dict[str, Any]]:
    if not isinstance(provider_result, Mapping):
        raise _Incomplete("provider import receipt is absent")
    if provider_result.get("schema") != "apg.h-provider-import/v1":
        raise _Incomplete("provider import receipt schema is invalid")
    raw = provider_result.get("raw")
    if (not isinstance(raw, Mapping) or type(raw.get("bytes")) is not int
            or raw["bytes"] < 0 or not isinstance(raw.get("sha256"), str)
            or len(raw["sha256"]) != 64):
        raise _Incomplete("provider raw identity is incomplete")
    route = provider_result.get("route")
    if not isinstance(route, Mapping) or route.get("provider") not in {"codex", "claude", "antigravity"}:
        raise _Incomplete("provider route identity is absent")
    terminal = provider_result.get("terminal")
    if not isinstance(terminal, Mapping) or not isinstance(terminal.get("exit_code"), int):
        raise _Incomplete("provider terminal receipt is absent")
    if terminal["exit_code"] != 0:
        return False, {"provider_terminal": "nonzero"}
    if provider_result.get("parse_status") in {"empty", "malformed"}:
        raise _Incomplete("malformed provider terminal receipt")
    if scenario_id in _REVIEW_SCENARIOS:
        if provider_result.get("review_response_status") != "accepted" or not isinstance(provider_result.get("review_response"), Mapping):
            raise _Incomplete("structured review response is missing or malformed")
    return True, {
        "provider": route.get("provider"),
        "provider_terminal": "observed",
        "raw": {"bytes": raw["bytes"], "sha256": raw["sha256"]},
    }


def _read_text(root: Path, relative: str) -> str | None:
    path = root / relative
    try:
        if path.is_symlink() or not path.is_file():
            return None
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


def _has_tokens(text: str | None, *tokens: str) -> bool:
    if text is None:
        return False
    lowered = text.lower()
    return all(token.lower() in lowered for token in tokens)


def _not_placeholder(*texts: str | None) -> bool:
    combined = "\n".join(text or "" for text in texts).lower()
    return not any(token in combined for token in ("placeholder", "provider task owns", "todo", r"\tskip", "t.skip"))


def _subject_contract(scenario_id: str, root: Path) -> bool:
    if scenario_id == "scenario-01":
        source = _read_text(root, "pkg/handler/health.go")
        tests = _read_text(root, "pkg/handler/health_test.go")
        return (_has_tokens(source, "net/http", "json")
                and ("StatusOK" in (source or "") or "WriteHeader(200" in (source or ""))
                and _has_tokens(tests, "httptest", "200", "json")
                and _not_placeholder(source, tests))
    if scenario_id == "scenario-02":
        plan = _read_text(root, "docs/plan-disposition.md")
        tests = _read_text(root, "tests/test_app.py")
        return bool(plan and len(plan.strip()) > 20 and _has_tokens(plan, "F-1", "F-2")
                    and tests and tests.count("assert") >= 2 and _not_placeholder(plan, tests))
    if scenario_id == "scenario-04":
        script = _read_text(root, "scripts/build.sh")
        return (_has_tokens(script, "cflags")
                and any(token in (script or "").lower() for token in ("incremental", "-mmd", "-mf", "-mp"))
                and _not_placeholder(script))
    if scenario_id == "scenario-06":
        source = _read_text(root, "cmd/server/main.go")
        tests = _read_text(root, "cmd/server/main_test.go")
        return (_has_tokens(source, "querystore", "python3", "query_sqlite")
                and _has_tokens(tests, "httptest", "json")
                and _not_placeholder(source, tests))
    if scenario_id == "scenario-10":
        tests = _read_text(root, "tests/integration_test.go")
        return _has_tokens(tests, "go-cmp", "cmp.") and _not_placeholder(tests)
    if scenario_id == "scenario-15":
        component = _read_text(root, "frontend/src/App.tsx")
        if not (_has_tokens(component, "export default", "<") and ">" in (component or "") and "return null" not in (component or "").lower() and _not_placeholder(component)):
            return False
        package = _read_text(root, "frontend/package.json")
        if not _has_tokens(package, "react", "typescript"):
            return False
        return True
    raise _Incomplete(f"unknown command oracle {scenario_id}")


def _bound_executable(runtime: Mapping[str, Any], name: str) -> str:
    runtimes = runtime.get("runtimes")
    if not isinstance(runtimes, Mapping):
        raise _Incomplete("runtime command inventory is absent")
    record = runtimes.get(name)
    if not isinstance(record, Mapping):
        raise _Incomplete(f"runtime command is not bound: {name}")
    executable = record.get("executable")
    if not isinstance(executable, str) or not executable.startswith("/"):
        raise _Incomplete("runtime executable path is not physical")
    files = runtime.get("files")
    identity = files.get(executable) if isinstance(files, Mapping) else None
    if not isinstance(identity, Mapping):
        raise _Incomplete(f"runtime executable identity is absent: {name}")
    # v2 keys retain the declared path while the identity binds the resolved
    # physical executable.  Execute that physical path so a mutable symlink
    # or ambient PATH cannot change the command boundary after sealing.
    physical = identity.get("physical_path", executable)
    if not isinstance(physical, str) or not physical.startswith("/"):
        raise _Incomplete("runtime executable physical path is absent")
    path = Path(physical)
    if path.is_symlink() or not path.is_file() or not os.access(path, os.X_OK):
        raise _Incomplete(f"runtime executable is unavailable: {name}")
    data = path.read_bytes()
    if identity.get("bytes") != len(data) or identity.get("sha256") != _sha256(data):
        raise _Incomplete(f"runtime executable drifted: {name}")
    return str(path)


def _run_command(
    command_runner: Callable[..., Any] | None,
    argv: list[str],
    cwd: Path,
    runtime: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    from .oracle_commands import ManifestRunner
    if type(command_runner) is not ManifestRunner:
        raise _Incomplete("repository-owned manifest command runner required")
    try:
        raw = command_runner.run(argv, cwd=cwd)
        observed_argv = [_bound_executable(runtime, argv[0]), *argv[1:]]
    except (OSError, subprocess.SubprocessError, TypeError, ValueError) as exc:
        raise _Incomplete("frozen command could not be executed") from exc
    if isinstance(raw, Mapping):
        code = raw.get("exit_code", raw.get("returncode"))
        stdout = raw.get("stdout", b"")
        stderr = raw.get("stderr", b"")
    else:
        code = getattr(raw, "exit_code", getattr(raw, "returncode", None))
        stdout = getattr(raw, "stdout", b"")
        stderr = getattr(raw, "stderr", b"")
    if not isinstance(code, int):
        raise _Incomplete("command runner did not return an exit code")
    if isinstance(stdout, str):
        stdout = stdout.encode()
    if isinstance(stderr, str):
        stderr = stderr.encode()
    if not isinstance(stdout, bytes) or not isinstance(stderr, bytes):
        raise _Incomplete("command runner output is not bytes")
    truncated = bool(getattr(raw, "truncated", False))
    stderr_truncated = bool(getattr(raw, "stderr_truncated", False))
    if isinstance(raw, Mapping):
        truncated = bool(raw.get("truncated", truncated))
        stderr_truncated = bool(raw.get("stderr_truncated", stderr_truncated))
    if truncated or stderr_truncated:
        raise _Incomplete("command output is truncated")
    return {
        "exit_code": code,
        "stdout": stdout,
        "stderr": stderr,
        "truncated": truncated,
        "stderr_truncated": stderr_truncated,
    }, {
        "synthetic": False,
        "argv": observed_argv,
        "retained_command": {"path": str(command_runner.directory / "command.json"),
                             "sha256": _sha256((command_runner.directory / "command.json").read_bytes())},
        "environment": {key: value for key, value in runtime.get("environment", {}).items()}
        if isinstance(runtime.get("environment"), Mapping) else {},
    }


def _instruction_delivery_check(bundle: Mapping[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Bind Scenario 04 to native instruction and transmission receipts."""
    if not isinstance(bundle, Mapping):
        raise _Incomplete("native instruction delivery bundle is absent")
    context = _native_context(bundle.get("context"))
    instruction_plan = context.get("instruction_plan")
    if not isinstance(instruction_plan, Mapping):
        raise _Incomplete("native instruction plan is absent")
    components = instruction_plan.get("components")
    if not isinstance(components, list):
        raise _Incomplete("native instruction components are absent")
    component = next((item for item in components
                      if isinstance(item, Mapping) and item.get("kind") == "standing-and-rtk"), None)
    if component is None:
        return False, {"component": "standing-and-rtk", "status": "absent"}
    for key in ("source_path", "source_sha256", "rendered_sha256", "rtk_slice_sha256"):
        identity = component.get(key)
        if not isinstance(identity, str) or not identity or (key.endswith("sha256") and len(identity) != 64):
            raise _Incomplete("native RTK component identity is malformed")
    for key in ("source_bytes", "rendered_bytes", "rtk_slice_bytes"):
        if type(component.get(key)) is not int or component[key] <= 0:
            raise _Incomplete("native RTK component byte identity is malformed")
    events = bundle.get("events")
    if not isinstance(events, list):
        raise _Incomplete("native instruction delivery events are absent")
    delivered = [event for event in events if isinstance(event, Mapping)
                 and event.get("schema") == "apg.acquisition-event/v1"
                 and event.get("channel") == "instructions" and event.get("phase") == "initial"]
    if len(delivered) != 1:
        return False, {"component": "standing-and-rtk", "status": "missing_native_delivery", "events": len(delivered)}
    event = delivered[0]
    argv = context.get("transport", {}).get("argv", [])
    candidates = [argument for argument in argv if isinstance(argument, str)
                  and argument.startswith("developer_instructions=")
                  and _sha256(argument.encode()) == event.get("payload_sha256")
                  and len(argument.encode()) == event.get("controlled_bytes")]
    if len(candidates) != 1:
        return False, {"component": "standing-and-rtk", "status": "identity_mismatch", "event_id": event.get("event_id")}
    try:
        rendered = json.loads(candidates[0].split("=", 1)[1])
    except (ValueError, TypeError):
        return False, {"component": "standing-and-rtk", "status": "malformed_instruction_argument"}
    header = f"Source standing instructions ({component['source_path']}; sha256={component['rendered_sha256']}):\n"
    if not isinstance(rendered, str) or not rendered.startswith(header):
        return False, {"component": "standing-and-rtk", "status": "source_header_mismatch"}
    body = rendered[len(header):].encode()
    from agent_source_guidance import render_rtk_slice
    slice_data = render_rtk_slice("codex", "instructions", "rtk").encode()
    if (len(body) != component["rendered_bytes"] or _sha256(body) != component["rendered_sha256"]
            or len(slice_data) != component["rtk_slice_bytes"]
            or _sha256(slice_data) != component["rtk_slice_sha256"]
            or not body.endswith(slice_data.strip() + b"\n")):
        return False, {"component": "standing-and-rtk", "status": "rendered_guidance_mismatch"}
    return True, {"component": "standing-and-rtk", "source_path": component["source_path"],
                  "source_sha256": component["source_sha256"],
                  "rendered_sha256": component["rendered_sha256"],
                  "rtk_slice_sha256": component["rtk_slice_sha256"],
                  "rtk_slice_bytes": component["rtk_slice_bytes"],
                  "event_id": event["event_id"], "channel": event["channel"]}


def _file_identity(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise _Incomplete(f"{name} identity is absent")
    for key in ("path", "device", "inode", "mode", "bytes", "sha256"):
        if key not in value:
            raise _Incomplete(f"{name} identity lacks {key}")
    if not isinstance(value["path"], str) or not value["path"] or type(value["device"]) is not int or type(value["inode"]) is not int or type(value["mode"]) is not int or type(value["bytes"]) is not int or value["bytes"] < 0 or not _digest(value["sha256"]):
        raise _Incomplete(f"{name} identity is malformed")
    return value


def _settings_isolation_check(activity: Mapping[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Require typed operator-setting and discovery receipts owned by the arm."""
    if not isinstance(activity, Mapping):
        raise _Incomplete("execution activity receipt is absent")
    settings = activity.get("settings_receipt")
    discovery = activity.get("discovery_receipt")
    if not isinstance(settings, Mapping) or settings.get("schema") != "apg.h-settings-observation/v1":
        raise _Incomplete("operator settings observation receipt is absent")
    if not isinstance(discovery, Mapping) or discovery.get("schema") != "apg.h-discovery-observation/v1":
        raise _Incomplete("discovery observation receipt is absent")
    settings_before = _file_identity(settings.get("before"), "settings before")
    settings_after = _file_identity(settings.get("after"), "settings after")
    run_root = _file_identity(discovery.get("run_root"), "discovery run root")
    global_before = _file_identity(discovery.get("global_before"), "global before")
    global_after = _file_identity(discovery.get("global_after"), "global after")
    settings_equal = settings_before == settings_after
    global_equal = global_before == global_after
    scoped = discovery.get("scoped_to_run") is True
    return settings_equal and global_equal and scoped, {
        "settings_equal": settings_equal,
        "global_equal": global_equal,
        "scoped_to_run": scoped,
        "run_root": {"path": run_root["path"], "bytes": run_root["bytes"], "sha256": run_root["sha256"]},
    }


def _read_only_scope_check(scenario_id: str, bundle: Mapping[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Bind read-only authority to the retained route and native argv.

    A lack of shell events is only a transport observation.  The authority
    claim comes from the source-owned frozen role binding, whose profile source
    and route digest are retained beside the arm, and from the actual argv
    recorded by the native invocation-context record.
    """
    expected_tools = _READ_ONLY_TOOL_SCOPES.get(scenario_id)
    if expected_tools is None:
        raise _Incomplete(f"read-only scope is not defined for {scenario_id}")
    if not isinstance(bundle, Mapping):
        raise _Incomplete("read-only scope bundle is absent")
    route = bundle.get("route")
    context = bundle.get("context")
    if not isinstance(route, Mapping) or not isinstance(context, Mapping):
        raise _Incomplete("read-only scope route or context is absent")
    source = route.get("source_identity")
    if not isinstance(source, Mapping) or source.get("schema") != "apg.h-source-binding/v1":
        raise _Incomplete("source-owned route binding is absent")
    if source.get("owner") != "testing.h_eval.preregistration":
        raise _Incomplete("source-owned route binding owner is invalid")
    if source.get("scenario_id") not in (None, scenario_id):
        raise _Incomplete("source-owned route binding scenario differs")
    if not isinstance(source.get("bindings_path"), str) or source["bindings_path"] != "testing/h_eval/scenario-bindings.json":
        raise _Incomplete("source-owned route binding path is invalid")
    if not _digest(source.get("route_sha256")):
        raise _Incomplete("source-owned route binding digest is absent")
    identity_sources = source.get("identity_sources")
    source_hashes = source.get("source_sha256")
    if (not isinstance(identity_sources, list) or not identity_sources
            or any(not isinstance(item, str) or not item for item in identity_sources)
            or not isinstance(source_hashes, Mapping)):
        raise _Incomplete("source-owned profile identity is incomplete")
    profile_sources = [item for item in identity_sources if "profiles" in Path(item).parts]
    if not profile_sources or any(not _digest(source_hashes.get(item)) for item in profile_sources):
        raise _Incomplete("source-owned profile identity is absent")

    role_binding = route.get("role_binding")
    if not isinstance(role_binding, Mapping):
        raise _Incomplete("source-owned role binding is absent")
    binding_id = role_binding.get("binding_id")
    if not isinstance(binding_id, str) or not binding_id:
        raise _Incomplete("source-owned role binding identity is absent")
    if binding_id != route.get("binding_id") or binding_id != context.get("binding_id"):
        raise _Incomplete("read-only route binding differs from native context")
    roles = role_binding.get("roles")
    if (not isinstance(roles, list) or not roles
            or any(not isinstance(role, str) or not role for role in roles)):
        raise _Incomplete("source-owned role binding roles are malformed")
    allowed_tools = role_binding.get("allowed_tools")
    if (not isinstance(allowed_tools, list) or not allowed_tools
            or any(not isinstance(tool, str) or not tool for tool in allowed_tools)
            or len(set(allowed_tools)) != len(allowed_tools)):
        raise _Incomplete("source-owned read-only tool scope is malformed")
    normalized_tools = frozenset(tool.casefold() for tool in allowed_tools)
    forbidden_tools = sorted(normalized_tools & {"bash", "shell", "run_command", "write", "edit"})
    scope_matches = normalized_tools == frozenset(tool.casefold() for tool in expected_tools)

    profile_contract = route.get("profile_contract")
    profile_contract_matches = True
    if profile_contract is not None:
        if not isinstance(profile_contract, Mapping) or profile_contract.get("schema") != "apg.h-profile-tool-scope/v1":
            raise _Incomplete("retained profile tool-scope contract is malformed")
        contract_tools = profile_contract.get("allowed_tools")
        if (not isinstance(contract_tools, list)
                or frozenset(str(tool).casefold() for tool in contract_tools) != normalized_tools
                or profile_contract.get("profile") != route.get("profile")
                or not _digest(profile_contract.get("source_sha256"))):
            raise _Incomplete("retained profile tool-scope contract differs")
        profile_contract_matches = True

    transport = context.get("transport")
    argv = transport.get("argv") if isinstance(transport, Mapping) else None
    if (not isinstance(argv, list) or any(not isinstance(arg, str) or not arg for arg in argv)):
        raise _Incomplete("native provider argv is absent")
    read_only_count = argv.count("--read-only")
    argv_read_only = read_only_count == 1
    facts = {
        "scenario_id": scenario_id,
        "binding_id": binding_id,
        "profile": route.get("profile"),
        "profile_source": profile_sources,
        "allowed_tools": sorted(allowed_tools),
        "forbidden_tools": forbidden_tools,
        "expected_tools": sorted(expected_tools),
        "scope_matches": scope_matches,
        "profile_contract_matches": profile_contract_matches,
        "argv_sha256": _sha256(_canonical(argv)),
        "read_only_flag_count": read_only_count,
        "argv_read_only": argv_read_only,
    }
    return scope_matches and not forbidden_tools and profile_contract_matches and argv_read_only, facts


def _static_assertion_evaluate(
    oracle: "TaskOracle",
    before: Any,
    provider_result: Mapping[str, Any],
    bundle: Mapping[str, Any],
) -> tuple[str, list[tuple[str, Any]]]:
    """Evaluate static arms from retained delivery facts only.

    Static arms are the comparator transport.  They do not contain the
    adaptive planner's prospective plan, so their oracle must not demand
    adaptive selection, fallback, acquisition, or recovery facts.  Review
    scenarios still use the same structured response contract as adaptive
    arms, and all arms retain provider terminal and authority receipts.
    """
    provider_ok, provider_facts = _provider_check(provider_result, scenario_id=oracle.scenario_id)
    authority_ok, authority_facts = _authority_check(oracle.scenario_id, bundle["authority"])
    static_ok, static_facts = _static_delivery_check(oracle.scenario_id, bundle)
    facts: list[tuple[str, Any]] = [
        ("provider-terminal", provider_facts),
        ("authority", authority_facts),
        ("static-delivery", static_facts),
    ]
    ok = provider_ok and authority_ok and static_ok
    sid = oracle.scenario_id
    if sid in _REVIEW_SCENARIOS:
        review_ok, review_facts = _review_check(sid, {"review_response": bundle["review"]}, provider_result)
        ok = ok and review_ok
        facts.append(("review-contract", review_facts))
    if sid in {"scenario-11", "scenario-12"}:
        scope_ok, scope_facts = _read_only_scope_check(sid, bundle)
        channels = {event.get("channel") for event in bundle["events"] if isinstance(event, Mapping)}
        ok = ok and scope_ok and not (channels & {"shell", "bash"})
        facts.append(("read-only-scope", scope_facts))
    return ("pass" if ok else "fail"), facts


def _command_evaluate(oracle: "TaskOracle", root: Path, before: Any, arm_evidence: Mapping[str, Any], provider_result: Mapping[str, Any], command_runner: Callable[..., Any] | None, bundle: Mapping[str, Any]) -> tuple[str, list[tuple[str, Any]]]:
    provider_ok, provider_facts = _provider_check(provider_result, scenario_id=oracle.scenario_id)
    command = oracle.expected["command"]
    argv = shlex.split(command)
    if not argv:
        raise _Incomplete("frozen command is empty")
    runtime = bundle["runtime"]
    if command_runner is None:
        from .oracle_commands import ManifestRunner
        command_runner = ManifestRunner(runtime, root, Path(arm_evidence["receipt_root"]).parent / "oracle-command")
    command_result, runner_facts = _run_command(command_runner, argv, root, runtime)
    exit_ok = command_result["exit_code"] == oracle.expected["expected_exit_code"]
    scopes = list(oracle.scenario.get("task_input", {}).get("mutation_scope", [])) if isinstance(oracle.scenario, Mapping) else []
    mutation_ok, mutation_facts = _mutation_facts(root, before, scopes)
    subject_ok = _subject_contract(oracle.scenario_id, root)
    authority_ok, authority_facts = _authority_check(oracle.scenario_id, bundle["authority"])
    supplemental_ok = True
    facts: list[tuple[str, Any]] = [
        ("provider-terminal", provider_facts),
        ("frozen-command", {"command": command, "argv": argv, **runner_facts, "complete": True}),
        ("runtime-identity", runtime),
        ("command-stdout", command_result["stdout"]),
        ("command-stderr", command_result["stderr"]),
        ("command-exit", {"observed": command_result["exit_code"], "expected": oracle.expected["expected_exit_code"], "match": exit_ok}),
        ("subject-contract", {"satisfied": subject_ok}),
        ("authority", authority_facts),
        ("mutation-boundary", mutation_facts),
    ]
    if oracle.scenario_id == "scenario-04":
        supplemental_ok, delivery_facts = _instruction_delivery_check(bundle)
        facts.append(("instruction-delivery", delivery_facts))
    elif oracle.scenario_id == "scenario-10":
        supplemental_ok, acquisition_facts = _acquisition_check(oracle.scenario_id, bundle)
        facts.append(("acquisition", acquisition_facts))
    elif oracle.scenario_id == "scenario-15":
        supplemental_ok, settings_facts = _settings_isolation_check(bundle["activity"])
        facts.append(("settings-isolation", settings_facts))
    ok = provider_ok and exit_ok and mutation_ok and subject_ok and authority_ok and supplemental_ok
    return ("pass" if ok else "fail"), facts


def _assertion_evaluate(oracle: "TaskOracle", root: Path, before: Any, arm_evidence: Mapping[str, Any], provider_result: Mapping[str, Any], bundle: Mapping[str, Any]) -> tuple[str, list[tuple[str, Any]]]:
    context = _native_context(bundle.get("context"))
    if context.get("requested_mode") == "static":
        return _static_assertion_evaluate(oracle, before, provider_result, bundle)
    provider_ok, provider_facts = _provider_check(provider_result, scenario_id=oracle.scenario_id)
    authority_ok, authority_facts = _authority_check(oracle.scenario_id, bundle["authority"])
    context, selected, mechanism_facts = _mechanism_facts(bundle)
    plan = _plan(context)
    decisions = _decisions(plan)
    facts: list[tuple[str, Any]] = [("provider-terminal", provider_facts), ("authority", authority_facts), ("context-plan", mechanism_facts)]
    ok = provider_ok and authority_ok
    sid = oracle.scenario_id
    if sid == "scenario-03":
        review_ok, review_facts = _review_check(sid, {"review_response": bundle["review"]}, provider_result)
        reasons = " ".join([str(context.get("reason", "")), *plan.get("reasons", [])]).lower()
        ok = ok and context.get("requested_mode") == "adaptive" and context.get("planned") is True and context.get("effective_mode") == "static" and plan.get("effective_mode") == "static" and selected == ["apgr:markdown-language-profile"] and ("fallback" in reasons or "overflow" in reasons) and review_ok
        ok = ok and not any(skill in selected for skill in ("apgr:go-language-profile", "apgr:pytest-test-profile", "apgr:javascript-language-profile", "apgr:dockerfile-profile", "apgr:sqlite-database-profile"))
        facts.append(("review-contract", review_facts))
    elif sid == "scenario-05":
        qualification = plan.get("qualification")
        selected_decisions = [decision for decision in decisions if decision.get("required")]
        ok = ok and context.get("requested_mode") == "adaptive" and context.get("effective_mode") == "static" and plan.get("effective_mode") == "static" and plan.get("required_satisfied") is True and bool(selected_decisions) and all(decision.get("status") == "selected" and str(decision.get("selected_id", "")).startswith("apgr:") for decision in selected_decisions) and isinstance(qualification, Mapping) and qualification.get("selective_projection") is False
    elif sid == "scenario-07":
        reasons = " ".join(plan.get("reasons", [])).lower()
        ok = ok and context.get("requested_mode") == "adaptive" and context.get("planned") is True and context.get("effective_mode") == "static" and plan.get("effective_mode") == "static" and "mandatory" in reasons and "overflow" in reasons and plan.get("budget_passed") is False and plan.get("required_satisfied") is True
    elif sid == "scenario-08":
        qualification = plan.get("qualification")
        ok = ok and context.get("requested_mode") == "adaptive" and context.get("effective_mode") == "adaptive" and plan.get("effective_mode") == "adaptive" and selected == ["project:go-language-profile", "apgr:go-language-profile"] and all(decision.get("status") == "selected" for decision in decisions if decision.get("selected_id") in selected) and isinstance(qualification, Mapping) and qualification.get("selective_projection") is True and qualification.get("independent_recovery") is True
    elif sid == "scenario-09":
        overrides = plan.get("catalog", {}).get("overrides") if isinstance(plan.get("catalog"), Mapping) else None
        replacement = [decision for decision in decisions if decision.get("requested_id") == "apgr:go-language-profile"]
        qualification = plan.get("qualification")
        ok = ok and context.get("requested_mode") == "adaptive" and context.get("effective_mode") == "adaptive" and plan.get("effective_mode") == "adaptive" and selected == ["project:go-language-profile"] and len(replacement) == 1 and replacement[0].get("selected_id") == "project:go-language-profile" and isinstance(overrides, list) and any(isinstance(item, Mapping) and item.get("requested_id") == "apgr:go-language-profile" and item.get("selected_id") == "project:go-language-profile" for item in overrides) and isinstance(qualification, Mapping) and qualification.get("selective_projection") is True and qualification.get("independent_recovery") is True
    elif sid == "scenario-11":
        acquisition_ok, acquisition_facts = _acquisition_check(sid, bundle)
        scope_ok, scope_facts = _read_only_scope_check(sid, bundle)
        review_ok, review_facts = _review_check(sid, {"review_response": bundle["review"]}, provider_result)
        channels = {event.get("channel") for event in bundle["events"] if isinstance(event, Mapping)}
        ok = ok and context.get("effective_mode") == "adaptive" and acquisition_ok and scope_ok and not (channels & {"shell", "bash"}) and review_ok
        facts.extend((("acquisition", acquisition_facts), ("read-only-scope", scope_facts), ("review-contract", review_facts)))
    elif sid == "scenario-12":
        review_ok, review_facts = _review_check(sid, {"review_response": bundle["review"]}, provider_result)
        scope_ok, scope_facts = _read_only_scope_check(sid, bundle)
        acquisition = context.get("acquisition")
        recovery = acquisition.get("recovery") if isinstance(acquisition, Mapping) else None
        recovery_events = [row.get("event") for row in bundle["acquisitions"] if isinstance(row, Mapping) and isinstance(row.get("event"), Mapping) and row["event"].get("kind") == "recovery_read_observed"]
        recovery_ok = isinstance(acquisition, Mapping) and acquisition.get("status") == "prelaunch_available" and acquisition.get("replay_authorized") is False and isinstance(recovery, list) and len(recovery) == 1 and len(recovery_events) == 1
        if recovery_ok:
            expected = recovery[0]
            observed = recovery_events[0]
            recovery_ok = (isinstance(expected, Mapping) and observed.get("phase") == "late" and observed.get("is_repeat_delivery") is False and observed.get("payload_sha256") == expected.get("sha256") and observed.get("controlled_bytes") == expected.get("bytes") and observed.get("provenance") == expected.get("path"))
        channels = {event.get("channel") for event in bundle["events"] if isinstance(event, Mapping)}
        ok = ok and recovery_ok and scope_ok and not (channels & {"shell", "bash"}) and bundle["activity"].get("attempts") == ["one"] and bundle["activity"].get("retries") == 0 and bundle["activity"].get("restarts") == 0 and review_ok
        facts.extend((("read-only-scope", scope_facts), ("review-contract", review_facts)))
    elif sid == "scenario-13":
        reasons = " ".join([str(context.get("reason", "")), *plan.get("reasons", [])]).lower()
        channels = {event.get("channel") for event in bundle["events"] if isinstance(event, Mapping)}
        ok = ok and context.get("requested_mode") == "adaptive" and context.get("planned") is True and context.get("effective_mode") == "static" and plan.get("required_satisfied") is True and ("unavailable" in reasons or "fallback" in reasons) and "mcp" not in channels and not bundle["acquisitions"]
    elif sid == "scenario-14":
        acquisition_ok, acquisition_facts = _acquisition_check(sid, bundle)
        ok = ok and context.get("effective_mode") == "adaptive" and acquisition_ok and authority_ok
        facts.append(("acquisition", acquisition_facts))
        review_ok, review_facts = _review_check(sid, {"review_response": bundle["review"]}, provider_result)
        ok = ok and review_ok
        facts.append(("review-contract", review_facts))
    else:
        raise _Incomplete(f"unknown assertion oracle {sid}")
    return ("pass" if ok else "fail"), facts


class TaskOracle:
    """One frozen scenario's substantive oracle owner."""

    def __init__(self, scenario_id: str, expected: Mapping[str, Any], scenario: Mapping[str, Any] | None = None) -> None:
        self.scenario_id = scenario_id
        self.expected = deepcopy(dict(expected))
        self.scenario = deepcopy(dict(scenario or {"scenario_id": scenario_id, "task_input": {}}))

    def evaluate(
        self,
        scenario_id: str,
        subject: str | os.PathLike[str],
        *,
        before: Mapping[str, Any],
        arm_evidence: Mapping[str, Any],
        provider_result: Mapping[str, Any],
        command_runner: Callable[..., Any] | None = None,
    ) -> dict[str, Any]:
        """Evaluate one completed provider arm without inferring from prose."""
        if scenario_id != self.scenario_id:
            raise ValueError("oracle/scenario identity mismatch")
        if not isinstance(arm_evidence, Mapping):
            raise ValueError("arm evidence must be a mapping")
        root = _physical_root(subject)
        try:
            bundle_root = arm_evidence.get("receipt_root")
            bundle = _receipt_bundle(
                bundle_root,
                scenario_id=self.scenario_id,
                subject=root,
                before=before,
                expected_mode=arm_evidence.get("mode"),
            )
            # The imported result is retained twice by the execution package:
            # once as the direct call input and once as provider-import.json.
            # Requiring equality closes the caller-injection seam.
            if bundle["provider_import"] != provider_result:
                raise _Incomplete("provider import receipt differs from retained bundle")
            if self.scenario_id in _COMMAND_SCENARIOS:
                status, facts = _command_evaluate(self, root, before, arm_evidence, provider_result, command_runner, bundle)
            else:
                status, facts = _assertion_evaluate(self, root, before, arm_evidence, provider_result, bundle)
        except _Incomplete as exc:
            return _receipt(self.expected, "unavailable", [("incomplete", {"reason": str(exc), "scenario_id": self.scenario_id})])
        return _receipt(self.expected, status, facts)

    def __call__(self, scenario_id: str, subject: str | os.PathLike[str], **kwargs: Any) -> dict[str, Any]:
        return self.evaluate(scenario_id, subject, **kwargs)


def oracle_for(scenario: Mapping[str, Any] | str) -> TaskOracle:
    """Bind an oracle only to one of the exact frozen quality contracts."""
    if isinstance(scenario, str):
        scenario_id = scenario
        source: Mapping[str, Any] = {"scenario_id": scenario_id, "task_input": {}}
    elif isinstance(scenario, Mapping):
        scenario_id = scenario.get("scenario_id")
        source = scenario
    else:
        raise TypeError("scenario must be a mapping or scenario id")
    if not isinstance(scenario_id, str) or scenario_id not in _FROZEN_QUALITY_ORACLES:
        raise ValueError("unknown frozen scenario")
    if isinstance(source, Mapping) and "expected_outcome" in source:
        supplied = source.get("expected_outcome", {}).get("quality_oracle")
        if supplied != _FROZEN_QUALITY_ORACLES[scenario_id]:
            raise ValueError("frozen quality oracle contract changed")
    return TaskOracle(scenario_id, _FROZEN_QUALITY_ORACLES[scenario_id], source)


get_oracle = oracle_for
resolve_oracle = oracle_for


def _write_fixture(root: Path, files: Mapping[str, str | bytes]) -> None:
    for name, value in files.items():
        path = root / name
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        data = value.encode() if isinstance(value, str) else value
        path.write_bytes(data)


def _fixture_sqlite_bytes() -> bytes:
    import sqlite3
    with tempfile.TemporaryDirectory(prefix="oracle-sqlite-") as temporary:
        path = Path(temporary) / "db.sqlite"
        with sqlite3.connect(path) as database:
            database.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
            database.execute("INSERT INTO users(name) VALUES ('oracle-user')")
        return path.read_bytes()


def _command_fixture(scenario_id: str, good: bool) -> dict[str, str | bytes]:
    if scenario_id == "scenario-01":
        if not good:
            return {"go.mod": "module fixture/health\n\ngo 1.25\n", "pkg/handler/health.go": "package handler\n\nimport \"net/http\"\nfunc Health(http.ResponseWriter, *http.Request) {}\n", "pkg/handler/health_test.go": "package handler\nimport \"testing\"\nfunc TestHealthTODO(t *testing.T) { t.Skip(\"placeholder\") }\n"}
        return {"go.mod": "module fixture/health\n\ngo 1.25\n", "pkg/handler/health.go": "package handler\n\nimport (\n \"encoding/json\"\n \"net/http\"\n)\nfunc Health(w http.ResponseWriter, _ *http.Request) { w.Header().Set(\"Content-Type\", \"application/json\"); w.WriteHeader(http.StatusOK); _ = json.NewEncoder(w).Encode(map[string]string{\"status\":\"ok\"}) }\n", "pkg/handler/health_test.go": "package handler\nimport (\"net/http/httptest\"; \"testing\")\nfunc TestHealth(t *testing.T) { r := httptest.NewRecorder(); Health(r, httptest.NewRequest(\"GET\", \"/health\", nil)); if r.Code != 200 { t.Fatalf(\"status=%d\", r.Code) }; if r.Body.Len() == 0 { t.Fatal(\"json body missing\") } }\n"}
    if scenario_id == "scenario-02":
        tests = "from src.app import total\n\ndef test_existing_total():\n    assert total([1, 2]) == 3\n\ndef test_empty_input_regression():\n    assert total([]) == 0\n"
        if not good:
            tests = "from src.app import total\n\ndef test_provider_task_placeholder():\n    pass\n"
        return {"pyproject.toml": "[project]\nname=\"fixture\"\n", "src/__init__.py": "", "src/app.py": "def total(values):\n    return sum(values)\n", "tests/test_app.py": tests, "docs/plan-disposition.md": "# Plan disposition\n\nF-1 accepted: add empty-input regression. F-2 accepted: retain total API and test boundary.\n"}
    if scenario_id == "scenario-04":
        script = "#!/usr/bin/env bash\nset -eu\nmkdir -p build\n: \"${INCREMENTAL:=1}\"\ncc ${CFLAGS:-} -MMD -MP -MF build/app.d -o build/app src/main.c\n"
        if not good:
            script = "#!/usr/bin/env bash\nset -eu\ncc ${CFLAGS:-} -o build/app src/main.c\n"
        return {"scripts/build.sh": script, "src/main.c": "int main(void) { return 0; }\n"}
    if scenario_id == "scenario-06":
        source = "package main\n\nimport (\n \"encoding/json\"\n \"net/http\"\n \"os/exec\"\n)\nfunc queryStore(path string) ([]string, error) { output, err := exec.Command(\"python3\", \"../../tools/query_sqlite.py\", path).Output(); if err != nil { return nil, err }; var names []string; if err := json.Unmarshal(output, &names); err != nil { return nil, err }; return names, nil }\nfunc handler(w http.ResponseWriter, _ *http.Request) { names, err := queryStore(\"../../schema/db.sqlite\"); if err != nil { http.Error(w, err.Error(), 500); return }; w.Header().Set(\"Content-Type\", \"application/json\"); _ = json.NewEncoder(w).Encode(names) }\n"
        tests = "package main\nimport (\"encoding/json\"; \"net/http/httptest\"; \"testing\")\nfunc TestServerQuery(t *testing.T) { r := httptest.NewRecorder(); handler(r, httptest.NewRequest(\"GET\", \"/users\", nil)); if r.Code != 200 { t.Fatalf(\"status=%d\", r.Code) }; var names []string; if err := json.Unmarshal(r.Body.Bytes(), &names); err != nil { t.Fatal(err) } }\n"
        if not good:
            tests = "package main\nimport \"testing\"\nfunc TestServerTaskPlaceholder(t *testing.T) { t.Skip(\"placeholder\") }\n"
            source = "package main\nimport \"net/http\"\nfunc handler(http.ResponseWriter, *http.Request) {}\n"
        return {"go.mod": "module fixture/server\n\ngo 1.25\n", "cmd/server/main.go": source, "cmd/server/main_test.go": tests, "schema/db.sqlite": _fixture_sqlite_bytes(), "tools/query_sqlite.py": "import json, sqlite3, sys\nwith sqlite3.connect(sys.argv[1]) as db:\n    print(json.dumps([row[0] for row in db.execute('SELECT name FROM users ORDER BY id')]))\n"}
    if scenario_id == "scenario-10":
        if not good:
            return {"go.mod": "module fixture/cmp\n\ngo 1.25\n", "tests/integration_test.go": "package tests\nimport \"testing\"\nfunc TestPlaceholder(t *testing.T) { t.Skip(\"placeholder\") }\n"}
        return {"go.mod": "module fixture/cmp\n\ngo 1.25\n\nrequire github.com/google/go-cmp v0.7.0\n", "go.sum": (Path(__file__).parents[1] / "fixtures/context-eval/subjects/scenario-10/go.sum").read_text(), "tests/integration_test.go": "package tests\nimport (\"testing\"; \"github.com/google/go-cmp/cmp\")\nfunc TestIntegration(t *testing.T) { if diff := cmp.Diff([]int{1, 2}, []int{1, 2}); diff != \"\" { t.Fatal(diff) }; if cmp.Diff([]int{1}, []int{2}) == \"\" { t.Fatal(\"different input accepted\") } }\n"}
    if scenario_id == "scenario-15":
        component = "export default function App() { return <main data-testid=\"app\">ready</main>; }\n"
        if not good:
            component = "export default function App() { return null; }\n"
        return {"frontend/package.json": '{"private":true,"dependencies":{"react":"^19.0.0","typescript":"^5.5.0"},"scripts":{"build":"tsc --noEmit"}}\n', "frontend/tsconfig.json": '{"compilerOptions":{"target":"ES2022","moduleResolution":"node","jsx":"react-jsx","strict":true,"noEmit":true},"include":["src/**/*.tsx"]}\n', "frontend/src/App.tsx": component}
    raise ValueError(f"unknown command fixture {scenario_id}")


def _assertion_fixture(scenario_id: str) -> dict[str, str]:
    files = {
        "scenario-03": {"README.md": "# Review fixture\n", "docs/architecture.md": "# Architecture\n"},
        "scenario-05": {"main.go": "package main\n", "go.mod": "module fixture\n"},
        "scenario-07": {"src/main.rs": "fn main() {}\n"},
        "scenario-08": {"main.go": "package main\n", ".apgr/skills/go-language-profile/SKILL.md": "fixture\n"},
        "scenario-09": {"main.go": "package main\n", ".apgr/skills/go-language-profile/SKILL.md": "fixture\n", ".apgr/config.toml": "[skills.overrides]\n"},
        "scenario-11": {"pkg/api/client.go": "package api\n"},
        "scenario-12": {"pkg/service/service.go": "package service\n"},
        "scenario-13": {"pkg/auth/auth.go": "package auth\n"},
        "scenario-14": {"pkg/data/models.go": "package data\n"},
    }
    try:
        return files[scenario_id]
    except KeyError as exc:
        raise ValueError(f"unknown assertion fixture {scenario_id}") from exc


def _fixture_prompt(scenario_id: str, good: bool) -> bytes:
    return f"source-owned fixture prompt {scenario_id} {'good' if good else 'bad'}\n".encode()


def _fixture_identity(data: bytes) -> dict[str, Any]:
    return {"bytes": len(data), "characters": len(data.decode("utf-8")), "sha256": _sha256(data)}


def _fixture_decision(requested: str, selected: str | None, *, body_sha: str, status: str = "selected") -> dict[str, Any]:
    body = {"bytes": 128, "sha256": body_sha}
    return {"requested_id": requested, "selected_id": selected, "status": status,
            "reason": "source-owned fixture decision", "required": True,
            "content_identity": body_sha, "whole_source": dict(body), "body_only": dict(body)}


def _fixture_plan(scenario_id: str, good: bool) -> dict[str, Any]:
    requested_mode = "adaptive"
    effective_mode = "static"
    reasons = ["fixture_static"]
    selected_ids: list[str] = []
    decisions: list[dict[str, Any]] = []
    qualification = {"selective_projection": False, "independent_recovery": False,
                     "evidence": "source-owned fixture mechanism evidence"}
    overrides: list[dict[str, Any]] = []
    canonical = _CANONICAL_BODY_SHA
    if scenario_id == "scenario-03":
        selected_ids = ["apgr:markdown-language-profile"]
        decisions = [_fixture_decision(selected_ids[0], selected_ids[0], body_sha="3" * 64)]
        reasons = ["mandatory_overflow_fallback"] if good else ["qualified_projection"]
    elif scenario_id == "scenario-05":
        selected_ids = ["apgr:go-language-profile", "apgr:go-test-profile", "apgr:pytest-test-profile", "apgr:markdown-language-profile", "apgr:sqlite-database-profile"]
        decisions = [_fixture_decision(item, item, body_sha=_sha256(item.encode())) for item in selected_ids]
        reasons = ["global_skill_path_isolation_unqualified_fallback"]
    elif scenario_id == "scenario-07":
        selected_ids = ["apgr:go-language-profile"]
        decisions = [_fixture_decision(selected_ids[0], selected_ids[0], body_sha="7" * 64)]
        reasons = ["mandatory_overflow_fallback"] if good else ["qualified_projection"]
    elif scenario_id == "scenario-08":
        requested_mode = effective_mode = "adaptive"
        selected_ids = ["project:go-language-profile", "apgr:go-language-profile"]
        decisions = [_fixture_decision(item, item, body_sha="8" * 64) for item in selected_ids]
        reasons = ["qualified_projection"]
        qualification.update(selective_projection=True, independent_recovery=True)
    elif scenario_id == "scenario-09":
        requested_mode = effective_mode = "adaptive"
        selected_ids = ["project:go-language-profile"] if good else ["apgr:go-language-profile"]
        decisions = [_fixture_decision("apgr:go-language-profile", selected_ids[0], body_sha="9" * 64)]
        overrides = [{"requested_id": "apgr:go-language-profile", "selected_id": "project:go-language-profile", "reason": "explicit project replacement"}] if good else []
        reasons = ["qualified_projection"]
        qualification.update(selective_projection=True, independent_recovery=True)
    elif scenario_id == "scenario-10":
        requested_mode = effective_mode = "adaptive"
        selected_ids = ["apgr:go-test-profile"]
        decisions = [_fixture_decision(selected_ids[0], selected_ids[0], body_sha=canonical[scenario_id] if good else "0" * 64)]
        reasons = ["qualified_projection"]
        qualification.update(selective_projection=True, independent_recovery=True)
    elif scenario_id == "scenario-11":
        requested_mode = effective_mode = "adaptive"
        selected_ids = ["apgr:go-test-profile"]
        decisions = [_fixture_decision(selected_ids[0], selected_ids[0], body_sha=canonical[scenario_id] if good else "0" * 64)]
        reasons = ["qualified_projection"]
        qualification.update(selective_projection=True, independent_recovery=True)
    elif scenario_id == "scenario-12":
        requested_mode = effective_mode = "adaptive"
        selected_ids = ["apgr:go-language-profile"]
        decisions = [_fixture_decision(selected_ids[0], selected_ids[0], body_sha=canonical[scenario_id])]
        reasons = ["qualified_projection"]
        qualification.update(selective_projection=True, independent_recovery=True)
    elif scenario_id == "scenario-13":
        selected_ids = ["apgr:go-language-profile"]
        decisions = [_fixture_decision(selected_ids[0], selected_ids[0], body_sha="d" * 64)]
        reasons = ["mcp_adapter_unavailable_at_prelaunch_fallback"]
    elif scenario_id == "scenario-14":
        requested_mode = effective_mode = "adaptive"
        selected_ids = ["apgr:sqlite-database-profile"]
        decisions = [_fixture_decision(selected_ids[0], selected_ids[0], body_sha="e" * 64)]
        reasons = ["qualified_projection"]
        qualification.update(selective_projection=True, independent_recovery=True)
    else:
        raise ValueError(f"unknown assertion fixture {scenario_id}")
    if not good:
        if scenario_id == "scenario-13":
            reasons = ["qualified_projection"]
        if scenario_id in {"scenario-05", "scenario-07"}:
            qualification["selective_projection"] = True
        if scenario_id == "scenario-08":
            selected_ids = ["project:go-language-profile"]
            decisions = [_fixture_decision(selected_ids[0], selected_ids[0], body_sha="8" * 64)]
        if scenario_id == "scenario-09":
            decisions = [_fixture_decision("apgr:go-language-profile", "apgr:go-language-profile", body_sha="9" * 64)]
    snapshots = [{"qualified_id": item, "body": "", "bytes": 128, "sha256": decision["body_only"]["sha256"]}
                 for item, decision in zip(selected_ids, [item for item in decisions if item.get("status") == "selected"])]
    return {
        "schema_version": "apg.context-plan/v1", "run_id": f"fixture-{scenario_id}-{int(good)}",
        "binding_id": "fixture-binding", "attempt_id": "one", "roles": ["Work Review"],
        "requested_mode": requested_mode, "effective_mode": effective_mode,
        "reasons": reasons, "catalog": {"schema_version": "apg.skill-catalog/v1", "overrides": overrides},
        "decisions": decisions, "selected_snapshots": snapshots, "budget": {"max_initial_context_bytes": 1 << 20},
        "qualification": qualification, "budget_passed": scenario_id != "scenario-07",
        "required_satisfied": good or scenario_id not in {"scenario-05"}, "mandatory_cost": 128,
        "payload_cost": 128, "payload": "source-owned fixture payload", "tokens": None,
        "provider_native_overhead": None,
    }


def _fixture_evidence(scenario_id: str, good: bool) -> dict[str, Any]:
    prompt = _fixture_prompt(scenario_id, good)
    prompt_identity = _fixture_identity(prompt)
    fixture_argv = ["fixture-claude-profile", "fixture-review", "--read-only", "-p"]
    fixture_configuration = ["testing/h_eval/scenario-bindings.json", "claude/profiles/normal-final-review.json"]
    standing = b"source-owned fixture standing instructions\n"
    instruction_components: list[dict[str, Any]] = [{
        "id": "provider-standing",
        "source_path": "fixture/CLAUDE.md",
        "bytes": len(standing),
        "sha256": _sha256(standing),
    }]
    if scenario_id in _REVIEW_SCENARIOS:
        from . import response_contract
        contract_bytes = ("\n\nEvaluation scenario: " + scenario_id + "\n"
                          + response_contract.instructions()).encode("utf-8")
        instruction_components.append({
            "id": "evaluation-response-contract",
            "schema": "apg.h-evaluation-contract-identity/v1",
            "bytes": len(contract_bytes),
            "sha256": _sha256(contract_bytes),
            "required": True,
        })
    authority = {"available": True, "unchanged": True}
    requested = "adaptive" if scenario_id not in {"scenario-01", "scenario-02", "scenario-04", "scenario-06", "scenario-15"} else "static"
    context: dict[str, Any] = {
        "schema": "apg.invocation-context/v1", "run_id": f"fixture-{scenario_id}-{int(good)}",
        "binding_id": "fixture-binding", "attempt_id": "one", "attempt_number": 1,
        "roles": ["Work Review"], "requested_mode": requested, "effective_mode": "static",
        "reason": "static_requested", "configuration": fixture_configuration, "planned": requested == "adaptive",
        "materialized": False, "model_observed": None, "catalog_fingerprint": None,
        "rule_version": None, "content_identity": None,
        "transport": {"argv": fixture_argv, "argv_json": _fixture_identity(_canonical(fixture_argv)), "stdin": prompt_identity,
                      "native_discovery_count": None, "delivered_body_count": None},
        "instruction_plan": {"schema": "apg.instruction-plan/v1", "components": instruction_components,
                             "runner_stdin": prompt_identity, "model_observed": None},
        "attempted_request": None, "prospective_plan": None,
    }
    if scenario_id == "scenario-04":
        from agent_source_guidance import render_rtk_slice
        slice_data = render_rtk_slice("codex", "instructions", "rtk").encode()
        source_body = b"Source-owned standing authority.\n"
        body = source_body.rstrip() + b"\n\n" + slice_data.strip() + b"\n"
        source_path = "fixture/AGENTS.md"
        rendered = f"Source standing instructions ({source_path}; sha256={_sha256(body)}):\n" + body.decode()
        context["transport"]["argv"].extend(["-c", "developer_instructions=" + json.dumps(rendered, ensure_ascii=False)])
        context["transport"]["argv_json"] = _fixture_identity(_canonical(context["transport"]["argv"]))
        context["instruction_plan"]["components"] = [{
            "kind": "standing-and-rtk", "source_path": source_path,
            "source_sha256": _sha256(source_body), "rendered_sha256": _sha256(body),
            "source_bytes": len(source_body), "source_characters": len(source_body),
            "rendered_bytes": len(body), "rendered_characters": len(body),
            "rtk_slice_sha256": _sha256(slice_data), "rtk_slice_bytes": len(slice_data),
            "boundary": "component view, overlaps transport; do not add twice",
        }]
    elif scenario_id not in _COMMAND_SCENARIOS or scenario_id == "scenario-10":
        plan = _fixture_plan(scenario_id, good)
        context["effective_mode"] = plan["effective_mode"]
        context["reason"] = ",".join(plan["reasons"])
        context["prospective_plan"] = plan
    if scenario_id == "scenario-12":
        recovery_sha = _CANONICAL_BODY_SHA[scenario_id]
        context["acquisition"] = {
            "status": "prelaunch_available", "replay_authorized": False,
            "recovery": [{"id": "apgr:go-language-profile", "path": "acquisitions/skills/fixture/apgr:go-language-profile/SKILL.md", "bytes": 128, "sha256": recovery_sha, "content_identity": recovery_sha}],
        }
    activity: dict[str, Any] = {
        "schema": "apg.h-execution-activity/v1", "attempts": ["one"], "retries": 0, "restarts": 0,
        "provider_invocations": 0, "revision_observation": [], "restart_observation": [], "permitted": True,
    }
    if scenario_id == "scenario-15":
        settings = {"path": "fixture/operator-settings.json", "device": 1, "inode": 1, "mode": 0o600, "bytes": 1, "sha256": "1" * 64}
        run_root = {"path": "fixture/run", "device": 1, "inode": 2, "mode": 0o700, "bytes": 1, "sha256": "2" * 64}
        global_id = {"path": "fixture/discovery", "device": 1, "inode": 3, "mode": 0o700, "bytes": 1, "sha256": "3" * 64}
        after_settings = dict(settings)
        after_global = dict(global_id)
        if not good:
            after_settings["sha256"] = "0" * 64
            after_global["sha256"] = "0" * 64
        activity["settings_receipt"] = {"schema": "apg.h-settings-observation/v1", "before": settings, "after": after_settings}
        activity["discovery_receipt"] = {"schema": "apg.h-discovery-observation/v1", "run_root": run_root, "global_before": global_id, "global_after": after_global, "scoped_to_run": True}
    if scenario_id == "scenario-12":
        activity["recovery_receipt"] = {"schema": "apg.h-recovery-receipt/v1", "status": "complete", "provider_observed": None, "model_observed": None}
    return {"authority": authority, "context": context, "activity": activity, "prompt": prompt}


def _write_private(path: Path, value: Any, *, raw: bool = False) -> bytes:
    data = value if raw else _canonical(value)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_bytes(data)
    path.chmod(0o600)
    return data


def _fixture_review_response(scenario_id: str, good: bool) -> dict[str, Any]:
    required = sorted(_REVIEW_REQUIRED_PATHS.get(scenario_id, frozenset()))

    def evidence_for(path: str) -> dict[str, Any]:
        source = _review_source_files(scenario_id).get(path)
        if not isinstance(source, bytes):
            raise _Incomplete(f"review fixture source is unavailable: {path}")
        text = source.decode("utf-8")
        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        if path == "README.md":
            index, match = next(
                (index, re.search(r"\[[^\]]+\]\(([^)]+)\)", line))
                for index, line in enumerate(lines)
                if re.search(r"\[[^\]]+\]\(([^)]+)\)", line)
            )
            return {
                "source_path": path,
                "span": {"start": index + 1, "end": index + 1},
                "snippet": lines[index],
                "link_target": match.group(1),
            }
        if path == "docs/architecture.md":
            index = next(index for index, line in enumerate(lines) if line.startswith("#"))
            return {
                "source_path": path,
                "span": {"start": index + 1, "end": index + 2},
                "snippet": "\n".join(lines[index:index + 2]),
            }
        if path in {"pkg/api/client.go", "pkg/service/service.go"}:
            index = next(index for index, line in enumerate(lines) if re.search(r"\breturn\s+", line))
            return_expression = _return_expression(lines[index], nil_pair=path.endswith("client.go"))
            if return_expression is None:
                raise _Incomplete(f"review fixture return expression is unavailable: {path}")
            return {
                "source_path": path,
                "span": {"start": index + 1, "end": index + 1},
                "snippet": lines[index],
                "return_expression": return_expression,
            }
        if path == "pkg/data/models.go":
            fields: dict[str, str] = {}
            indexes: dict[str, int] = {}
            for index, line in enumerate(lines):
                match = re.fullmatch(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s+([A-Za-z_][A-Za-z0-9_]*(?:\[\])?)\s*", line)
                if match:
                    fields[match.group(1)] = match.group(2)
                    indexes[match.group(1)] = index
            first = min(indexes["ID"], indexes["Name"])
            last = max(indexes["ID"], indexes["Name"])
            return {
                "source_path": path,
                "span": {"start": first + 1, "end": last + 1},
                "snippet": "\n".join(lines[first:last + 1]),
                "declaration": {"ID": fields["ID"], "Name": fields["Name"]},
            }
        raise _Incomplete(f"review fixture path is unknown: {path}")

    findings = [
        {
            "path": path,
            "category": "source-observation",
            "summary": f"Reviewed source evidence for {path}.",
            "evidence": [evidence_for(path)],
        }
        for path in required
    ]
    if not good and findings:
        findings = findings[1:]
    return {
        "schema": "apg.h-evaluation-response/v1",
        "scenario_id": scenario_id,
        "summary": "Source-owned structured review fixture.",
        "findings": findings,
        "limitations": [],
    }


def _fixture_acquisition_events(scenario_id: str, good: bool, context: Mapping[str, Any]) -> list[dict[str, Any]]:
    if scenario_id not in {"scenario-10", "scenario-11", "scenario-12", "scenario-14"}:
        return []
    if scenario_id == "scenario-12":
        recovery = context["acquisition"]["recovery"][0]
        event = {"schema": "apg.acquisition-event/v1", "run_id": context["run_id"], "binding_id": context["binding_id"], "attempt_id": context["attempt_id"], "kind": "recovery_read_observed", "channel": "recovery_read", "phase": "late", "is_repeat_delivery": not good, "controlled_bytes": recovery["bytes"], "payload_sha256": recovery["sha256"], "provenance": recovery["path"], "observation_kind": "witnessed_recovery_read", "model_observed": None, "provider_observed": None}
        event["event_id"] = _sha256(_canonical(event))
        return [event]
    else:
        plan = context["prospective_plan"]
        decision = next(item for item in plan["decisions"] if item.get("status") == "selected")
        selected = decision["selected_id"]
        body_sha = decision["body_only"]["sha256"]
        if not good:
            body_sha = "0" * 64
        source = {"schema": "apg.acquisition-event/v1", "run_id": context["run_id"], "binding_id": context["binding_id"], "attempt_id": context["attempt_id"], "kind": "materialized", "channel": "preparation", "phase": "late", "selected": selected, "requested": decision["requested_id"], "content_identity": decision["content_identity"], "controlled_bytes": 0, "provenance": "source-owned fixture materialization", "observation_kind": "complete_channel_write", "model_observed": None, "provider_observed": None}
        source["event_id"] = _sha256(_canonical(source))
        event = {"schema": "apg.acquisition-event/v1", "run_id": context["run_id"], "binding_id": context["binding_id"], "attempt_id": context["attempt_id"], "kind": "response_delivered", "channel": "mcp", "phase": "late", "selected": selected, "requested": decision["requested_id"], "controlled_bytes": 128, "payload_sha256": body_sha, "provenance": "source-owned fixture acquisition", "observation_kind": "complete_channel_write", "model_observed": None, "provider_observed": None}
        event["event_id"] = _sha256(_canonical(event))
        return [source, event]


def _validate_fixture_runtime(value: Mapping[str, Any]) -> Mapping[str, Any]:
    """Validate the sealed runtime owner without probing provider binaries."""
    if not isinstance(value, Mapping) or value.get("schema") != "apg.h-runtime-inputs/v2":
        raise _Incomplete("sealed v2 runtime manifest required for oracle fixtures")
    try:
        from . import runtime_manifest
        runtime_manifest.verify(value, probe_versions=False)
    except (ImportError, OSError, TypeError, ValueError) as exc:
        raise _Incomplete("fixture runtime manifest is not valid") from exc
    lifecycle = value.get("lifecycle")
    if not isinstance(lifecycle, Mapping) or lifecycle.get("state") != "sealed":
        raise _Incomplete("sealed v2 runtime manifest required for oracle fixtures")
    return value


def _copy_bound_node_modules(runtime: Mapping[str, Any], subject: Path) -> None:
    """Materialize only manifest-bound offline TypeScript dependencies.

    Scenario 15's source-owned fixture is outside the model subject.  Its
    dependency tree is copied from a cache directory already inventoried by
    the sealed runtime manifest; no package manager or network resolution is
    allowed during fixture qualification.
    """
    groups = runtime.get("groups")
    files = runtime.get("files")
    if not isinstance(groups, Mapping) or not isinstance(files, Mapping):
        raise _Incomplete("runtime cache inventory is absent")
    candidates: list[Path] = []
    for declared in groups.get("cache_inputs", []):
        identity = files.get(declared)
        if isinstance(identity, Mapping) and isinstance(identity.get("physical_path"), str):
            base = Path(identity["physical_path"])
            candidates.extend((base, base / "node_modules"))
    source = next((candidate for candidate in candidates
                   if (candidate / "typescript" / "bin" / "tsc").is_file()
                   and (candidate / "react").is_dir()
                   and (candidate / "@types" / "react").is_dir()
                   and (candidate / "csstype").is_dir()), None)
    if source is None:
        raise _Incomplete("manifest-bound TypeScript dependency cache is unavailable")
    target = subject / "frontend" / "node_modules"
    target.mkdir(mode=0o700, parents=True, exist_ok=True)
    for package in ("typescript", "react", "@types/react", "csstype"):
        source_package = source / package
        target_package = target / package
        if target_package.exists():
            raise _Incomplete("fixture dependency destination already exists")
        if any(path.is_symlink() for path in source_package.rglob("*")):
            raise _Incomplete("fixture dependency package contains a symlink")
        shutil.copytree(source_package, target_package)
    binaries = target / ".bin"
    binaries.mkdir(mode=0o700)
    # Execute the manifest-bound compiler itself rather than require() it: on
    # nix hosts the bound ``tsc`` is a bash wrapper that execs Node, not a
    # JavaScript entry (APG166V-H-COMPLETE1 scenario-15).
    bash = _bound_executable(runtime, "bash")
    tsc = _bound_executable(runtime, "tsc")
    if any(character.isspace() for character in bash):
        raise _Incomplete("bound bash executable cannot form a direct fixture launcher")
    launcher = binaries / "tsc"
    launcher.write_text(f"#!{bash}\nexec {shlex.quote(tsc)} \"$@\"\n")
    launcher.chmod(0o700)


def _fixture_command_runner(runtime: Mapping[str, Any], subject: Path, fixture_root: Path):
    from .oracle_commands import ManifestRunner
    return ManifestRunner(runtime, subject, fixture_root / "command"), lambda: None

def _fixture_bundle(
    bundle_root: Path,
    *,
    subject: Path,
    before: Mapping[str, Any],
    scenario_id: str,
    good: bool,
    provider_result: Mapping[str, Any],
    evidence: Mapping[str, Any],
    provider_raw: bytes,
    runtime: Mapping[str, Any],
) -> Path:
    """Write a complete execution-owned bundle for one isolated fixture."""
    mode = "fixture"
    if scenario_id == "scenario-11":
        allowed_tools = ["view_file", "skill_search", "skill_acquire", "context_explain"]
    elif scenario_id == "scenario-12":
        allowed_tools = ["view_file"]
    else:
        allowed_tools = ["view_file"]
    profile_source = "claude/profiles/normal-final-review.json"
    route = {
        "schema": "apg.h-route/v1",
        "scenario_id": scenario_id,
        "provider": "claude",
        "profile": "fixture-review",
        "model": "fixture-model",
        "binding_id": "fixture-binding",
        "roles": ["Work Review"],
        "execution": "instrumented",
        "argv": list(evidence["context"]["transport"]["argv"]),
        "role_binding": {
            "binding_id": "fixture-binding",
            "roles": ["Work Review"],
            "allowed_tools": allowed_tools,
        },
        "source_identity": {
            "schema": "apg.h-source-binding/v1",
            "owner": "testing.h_eval.preregistration",
            "scenario_id": scenario_id,
            "mode": evidence["context"]["requested_mode"],
            "bindings_path": "testing/h_eval/scenario-bindings.json",
            "bindings_sha256": "a" * 64,
            "route_sha256": "b" * 64,
            "source_sha256": {profile_source: "c" * 64},
            "identity_sources": ["testing/h_eval/scenario-bindings.json", profile_source],
        },
        "profile_contract": {
            "schema": "apg.h-profile-tool-scope/v1",
            "owner": "testing.h_eval.preregistration",
            "profile": "fixture-review",
            "allowed_tools": allowed_tools,
            "source_path": profile_source,
            "source_sha256": "c" * 64,
        },
    }
    context = deepcopy(dict(evidence["context"]))
    authority = {
        "schema": "apg.h-authority/v1", "scenario_id": scenario_id,
        "mode": mode, "binding_id": route["binding_id"],
        "unchanged": True, "permitted": True,
    }
    git = {"schema": "apg.h-git-authority/v1", "scenario_id": scenario_id,
           "head": "fixture-head", "index": "fixture-index", "worktree": "fixture-worktree"}
    activity = deepcopy(dict(evidence["activity"]))
    review = _fixture_review_response(scenario_id, good) if scenario_id in _REVIEW_SCENARIOS else {"schema": "apg.h-not-applicable/v1", "scenario_id": scenario_id}
    prompt = bytes(evidence["prompt"])
    prompt_identity = _fixture_identity(prompt)
    context["transport"]["stdin"] = prompt_identity
    context["instruction_plan"]["runner_stdin"] = prompt_identity
    events: list[dict[str, Any]] = []

    def event(payload: bytes, *, channel: str, provenance: str, kind: str = "initial_delivered", phase: str = "initial") -> dict[str, Any]:
        item: dict[str, Any] = {
            "schema": "apg.acquisition-event/v1", "run_id": context["run_id"],
            "binding_id": context["binding_id"], "attempt_id": context["attempt_id"],
            "kind": kind, "channel": channel, "phase": phase,
            "controlled_bytes": len(payload), "payload_sha256": _sha256(payload),
            "provenance": provenance, "observation_kind": "complete_pipe_write",
            "model_observed": None, "provider_observed": None,
        }
        item["event_id"] = _sha256(_canonical(item))
        return item

    events.append(event(prompt, channel="prompt", provenance="rendered-runner-stdin"))
    if scenario_id == "scenario-04":
        payload = context["transport"]["argv"][-1].encode()
        events.append(event(payload, channel="instructions", provenance="provider-argv"))
    acquisition_events = _fixture_acquisition_events(scenario_id, good, context)
    context_bytes = _write_private(bundle_root / "context-plan.json", context)
    transport = {
        "schema": "apg.controlled-transmissions/v1",
        "plan": {"schema": "apg.context-reference/v1", "path": "context-plan.json",
                 "sha256": _sha256(context_bytes), "bytes": len(context_bytes)},
        "boundary": "source-owned fixture transport",
        "events": events, "diagnostics": [], "coverage": "complete", "model_observed": None,
    }
    files: dict[str, bytes] = {"context-plan.json": context_bytes}
    payloads: dict[str, Any] = {
        "subject-before.json": dict(before),
        "subject-after.json": dict(before),
        "git-before.json": git,
        "git-after.json": git,
        "provider-import.json": provider_result,
        "provider-terminal.json": {"schema": "apg.h-provider-terminal/v1", "scenario_id": scenario_id,
                                    "exit_code": 0, "truncated": False, "stderr_truncated": False},
        "transport.json": transport,
        "source-seal.json": {"schema": "apg.h-not-applicable/v1", "scenario_id": scenario_id},
        "route.json": route,
        "activity.json": activity,
        "authority.json": {"schema": "apg.h-authority-receipt/v1",
                           "status": "test-only", "before": dict(before),
                           "after": dict(before), "replay_authorized": False},
        "runtime.json": runtime,
        "review-response.json": review,
    }
    for name, value in payloads.items():
        files[name] = _write_private(bundle_root / name, value)
    acquisition_rows = []
    for item in acquisition_events:
        data = _canonical(item)
        acquisition_rows.append({"event": item, "path": f"acquisitions/event-{item['event_id']}.jsonl",
                                 "bytes": len(data), "sha256": _sha256(data)})
    acquisition_bytes = b"".join(_canonical(item) for item in acquisition_rows)
    files["acquisition-receipts.jsonl"] = _write_private(
        bundle_root / "acquisition-receipts.jsonl", acquisition_bytes, raw=True
    )
    stdout = provider_raw
    stderr = b""
    files["provider.stdout"] = _write_private(bundle_root / "provider.stdout", stdout, raw=True)
    files["provider.stderr"] = _write_private(bundle_root / "provider.stderr", stderr, raw=True)
    terminal = payloads["provider-terminal.json"]
    terminal["stdout"] = {"bytes": len(stdout), "sha256": _sha256(stdout)}
    terminal["stderr"] = {"bytes": 0, "sha256": _sha256(stderr)}
    files["provider-terminal.json"] = _write_private(bundle_root / "provider-terminal.json", terminal)
    identity = {
        "schema": RECEIPT_SCHEMA,
        "owner": "h-execution-package",
        "scenario_id": scenario_id,
        "mode": mode,
        "binding_id": route["binding_id"],
        "subject": {"path": str(subject)},
        "files": {name: {"bytes": len(data), "sha256": _sha256(data)} for name, data in files.items()},
    }
    _write_private(bundle_root / "identity.json", identity)
    return bundle_root


def exercise_oracle(
    root: str | os.PathLike[str],
    scenario: Mapping[str, Any] | str,
    oracle: TaskOracle | None = None,
    *,
    runtime_manifest: Mapping[str, Any] | None = None,
    fixture_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Exercise one oracle with retained GOOD/BAD fixtures and no providers.

    Command-backed fixtures execute through the sealed manifest transaction;
    they never use ambient ``PATH`` or a synthetic exit-code callback.  The
    optional fixture root is retained for review and is required to be an
    empty external directory supplied by the caller.
    """
    bound = oracle or oracle_for(scenario)
    if isinstance(scenario, Mapping):
        scenario_id = scenario.get("scenario_id")
    else:
        scenario_id = scenario
    if scenario_id != bound.scenario_id:
        raise ValueError("fixture/oracle scenario identity mismatch")
    destination = _physical_root(root)
    records: dict[str, Any] = {}
    try:
        runtime = _validate_fixture_runtime(runtime_manifest or {})
    except _Incomplete as error:
        return {
            "schema": FIXTURE_SCHEMA,
            "scenario_id": scenario_id,
            "provider_invocations": 0,
            "status": "incomplete",
            "good": False,
            "bad": False,
            "reason": str(error),
            "records": {},
        }

    temporary = None
    if fixture_root is None:
        scratch = os.environ.get("APG_H_QUALIFICATION_TMP")
        if not scratch:
            raise ValueError("external oracle qualification scratch required")
        scratch_root = _physical_root(scratch)
        if scratch_root.resolve().is_relative_to(destination.resolve()):
            raise ValueError("oracle qualification scratch must be external to source")
        temporary = tempfile.TemporaryDirectory(prefix=f"oracle-{scenario_id}-", dir=str(scratch_root))
        fixture_base = Path(temporary.name)
    else:
        fixture_base = Path(fixture_root)
        if not fixture_base.is_absolute():
            raise ValueError("oracle fixture root must be absolute")
        if fixture_base.exists():
            if fixture_base.is_symlink() or not fixture_base.is_dir() or any(fixture_base.iterdir()):
                raise ValueError("oracle fixture root must be a new empty physical directory")
        else:
            fixture_base.mkdir(mode=0o700, parents=True)
        fixture_base = _physical_root(fixture_base)
        if fixture_base.resolve().is_relative_to(destination.resolve()):
            raise ValueError("oracle fixture root must be external to source")

    try:
        for label, good in (("good", True), ("bad", False)):
            arm_root = fixture_base / label
            subject = arm_root / "subject"
            subject.mkdir(mode=0o700, parents=True)
            if scenario_id in _COMMAND_SCENARIOS:
                _write_fixture(subject, _command_fixture(scenario_id, good))
                if scenario_id == "scenario-15":
                    _copy_bound_node_modules(runtime, subject)
            else:
                _write_fixture(subject, _assertion_fixture(scenario_id))
            before = _snapshot(subject)
            evidence = _fixture_evidence(scenario_id, good)
            review = _fixture_review_response(scenario_id, good)
            importers = __import__("testing.h_eval.importers", fromlist=["import_claude"])
            wire_result: Any = "fixture"
            if scenario_id in _REVIEW_SCENARIOS:
                wire_result = review
            raw = (json.dumps({"type": "result", "subtype": "success",
                               "session_id": f"fixture-{label}",
                               "model": "fixture-model", "result": wire_result},
                              sort_keys=True) + "\n").encode("utf-8")
            route = {"provider": "claude", "profile": "fixture-review",
                     "model": "fixture-model", "binding_id": "fixture-binding",
                     "roles": ["Work Review"], "execution": "instrumented",
                     "scenario_id": scenario_id}
            provider_result = importers.import_claude(raw, route, terminal={"exit_code": 0})
            bundle = arm_root / "oracle-input"
            bundle.mkdir(mode=0o700)
            _fixture_bundle(bundle, subject=subject, before=before,
                            scenario_id=scenario_id, good=good,
                            provider_result=provider_result, evidence=evidence,
                            provider_raw=raw, runtime=runtime)
            command_runner = cleanup = None
            try:
                if scenario_id in _COMMAND_SCENARIOS:
                    command_runner, cleanup = _fixture_command_runner(runtime, subject, arm_root)
                receipt = bound.evaluate(
                    scenario_id,
                    subject,
                    before=before,
                    arm_evidence={"receipt_root": str(bundle), "mode": "fixture"},
                    provider_result=provider_result,
                    command_runner=command_runner,
                )
            finally:
                if cleanup is not None:
                    cleanup()
            records[label] = {"status": receipt["status"], "receipt": receipt}
        try:
            from . import runtime_manifest as runtime_owner
            runtime_owner.verify(runtime, probe_versions=False)
        except (ImportError, OSError, TypeError, ValueError) as error:
            return {
                "schema": FIXTURE_SCHEMA,
                "scenario_id": scenario_id,
                "provider_invocations": 0,
                "status": "incomplete",
                "good": False,
                "bad": False,
                "reason": f"runtime revalidation failed: {error}",
                "records": records,
            }
    finally:
        if temporary is not None:
            temporary.cleanup()
    return {
        "schema": FIXTURE_SCHEMA,
        "scenario_id": scenario_id,
        "provider_invocations": 0,
        "status": "complete" if records.get("good", {}).get("status") == "pass" and records.get("bad", {}).get("status") == "fail" else "incomplete",
        "good": records.get("good", {}).get("status") == "pass",
        "bad": records.get("bad", {}).get("status") == "fail",
        "records": records,
    }


__all__ = ["SCHEMA", "TaskOracle", "exercise_oracle", "get_oracle", "oracle_for", "resolve_oracle"]
