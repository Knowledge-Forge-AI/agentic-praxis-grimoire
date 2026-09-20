"""Shared ordinary adaptive route: support check, Claude projection, late acquisition.

Both V1 (dispatch.py) and V2 (v2_turns.py) call ``ordinary_projection``. The
only supported pilot seam is the maintained Claude wrapper launched with its
ordinary argv ``[.../claude-profile, PROFILE, (--read-only), -p]``. Every other
provider or argv shape keeps the unchanged static transport with an explicit
``route_unsupported:<code>`` reason while the planner still records what an
adaptive route would have selected.

Selected optional skill bodies travel inside the planned stdin payload after
the byte-identical mandatory prompt. Deferred embedded ``apgr:`` skills stay
reachable through the existing APGR MCP acquisition server, which the wrapper
composes beside the worker facade; budget-deferred requests are additionally
prepared as exact run-owned recovery files. Nothing here imports
``testing.h_eval`` or grants shell, write or directory authority.
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any

SUPPORT_SCHEMA = "apg.context-route/v1"
SEAM = "claude-profile"
MAX_ALLOWED = 128
MAX_RECOVERY = 16
COMPACT_VIEW = "compact ordinary acquisition view; the complete record is the run's context-plan file"


class ContextFallback(Exception):
    """A prelaunch optional failure with a stable static-fallback reason."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(detail or reason)
        self.fallback_reason = reason


def postures_v1(stage: str, role: str) -> list[str]:
    if role == "reviewer" or stage in ("plan_review", "final_review", "work_review"):
        return ["review"]
    if stage == "plan":
        return ["plan"]
    return ["work"]


def instruction_classes_v1(stage: str, role: str) -> list[str]:
    """V1 role class for the instruction projection; V2 derives the union from its role flags."""
    if role == "reviewer" or stage in ("plan_review", "final_review", "work_review"):
        return ["review_verification"]
    if stage == "plan":
        return ["planning"]
    if stage == "closeout":
        return ["closeout"]
    return ["implementation"]


def route_support(provider: str | None, profile: str | None, argv: list[str]) -> dict[str, Any]:
    """Classify the exact launch seam; never infers provider-native behavior."""
    support = {"schema": SUPPORT_SCHEMA, "seam": SEAM, "provider": provider, "profile": profile,
               "supported": False, "code": None}
    if provider != "claude":
        return {**support, "code": "provider_not_in_pilot"}
    if not argv or Path(argv[0]).name != "claude-profile":
        return {**support, "code": "launcher_not_claude_profile"}
    if not (argv[1:] == [profile, "-p"] or argv[1:] == [profile, "--read-only", "-p"]):
        return {**support, "code": "argv_shape"}
    try:
        from claude_vc_profile import PROFILE_CONTRACTS
    except Exception:  # optional classification only
        return {**support, "code": "launcher_contract_unavailable"}
    contract = PROFILE_CONTRACTS.get(profile)
    if contract is None:
        return {**support, "code": "profile_unknown"}
    if contract.isolated_settings:
        return {**support, "code": "isolated_settings_profile"}
    return {**support, "supported": True,
            "read_only": "--read-only" in argv or contract.permission_mode == "plan"}


def ordinary_projection(*, provider, profile, argv, prefix, classes=None):
    """Return ``(projection | None, support)`` for the shared V1/V2 seam.

    ``classes`` are the attempt's instruction role classes; the projection is
    consulted only after the skill plan is effectively adaptive.
    """
    support = route_support(provider, profile, list(argv))
    if not support["supported"]:
        return None, support
    try:
        binary = persistent_binary()
    except Exception as error:  # a source-only checkout remains static
        return None, {**support, "preflight": "acquisition_binary_unavailable",
                      "preflight_detail": type(error).__name__}
    instructions = InstructionInputs(argv[0], classes, ambient_tools=not support["read_only"])
    return ClaudeProjection(binary, prefix, instructions), {**support, "preflight": "available", "binary": str(binary)}


class InstructionInputs:
    """Selection inputs for the run-owned standing-instruction projection."""

    def __init__(self, launcher: str, classes, *, ambient_tools: bool) -> None:
        self.launcher = launcher
        self.classes = list(classes) if classes is not None else None
        self.ambient_tools = ambient_tools

    def prepare(self, record, run_dir, prefix):
        from .claude_instruction_handoff import launcher_root, prepare
        from .instruction_projection import ProjectionError
        try:
            root = launcher_root(self.launcher)
        except OSError as error:
            raise ProjectionError("instruction_source_unavailable", type(error).__name__) from error
        return prepare(record, Path(run_dir).resolve(), prefix, root=root, classes=self.classes,
                       ambient_tools=self.ambient_tools,
                       derived_from={"classes": "dispatcher stage/role binding",
                                     "ambient_tools": "not read_only in the route support classification"})


def persistent_binary() -> Path:
    import importlib.util
    import sys
    source = Path(__file__).resolve().parents[2] / "src/agentic_praxis_grimoire/go_bridge.py"
    name = "_apgr_context_route_bridge_" + hashlib.sha256(str(source).encode()).hexdigest()
    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None or spec.loader is None:
        raise ImportError("maintained Go bridge unavailable")
    module = importlib.util.module_from_spec(spec)
    previous = sys.modules.get(name)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        if previous is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous
    return module.persistent_executable()


class ClaudeProjection:
    """Ordinary Claude projection: argv unchanged, stdin equals the planned payload."""

    def __init__(self, binary: Path, prefix: str, instructions: InstructionInputs | None = None) -> None:
        self.binary = Path(binary)
        self.prefix = prefix
        self.acquisition = None
        self.instructions = instructions

    def qualification(self) -> dict[str, Any]:
        return {"selective_projection": True, "independent_recovery": True,
                "evidence": "ordinary claude-profile seam: planned payload on runner stdin; "
                            "deferred embedded skills via run-owned APGR MCP plus exact recovery files"}

    def project(self, plan, argv, prompt):
        payload = plan["payload"].encode("utf-8")
        if not payload.startswith(prompt):
            raise ContextFallback("optional_plan_failed", "planned payload lost the mandatory prefix")
        allowed, recovery = acquirable(plan)
        self.acquisition = OrdinaryAcquisition(self.binary, self.prefix, allowed, recovery) if allowed else None
        return list(argv), payload


def acquirable(plan: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Deferred embedded skills only; project/user bodies are not retained by the plan."""
    overridden = {o.get("requested") for o in (plan.get("catalog") or {}).get("overrides") or []}
    budget, other = [], []
    for decision in plan.get("decisions") or []:
        identifier = decision.get("selected_id")
        if (decision.get("status") != "deferred" or decision.get("requested_id") != identifier
                or not isinstance(identifier, str) or not identifier.startswith("apgr:")
                or identifier in overridden):
            continue
        (budget if decision.get("reason") == "required_closure_exceeds_budget" else other).append(identifier)
    allowed = list(dict.fromkeys([*budget, *other]))[:MAX_ALLOWED]
    return allowed, [i for i in budget if i in allowed][:MAX_RECOVERY]


def compact_plan(record: dict[str, Any]) -> dict[str, Any]:
    plan = record.get("prospective_plan") or {}
    return {"schema": record["schema"], "run_id": record["run_id"], "binding_id": record["binding_id"],
            "attempt_id": record["attempt_id"], "view": COMPACT_VIEW,
            "requested_mode": record["requested_mode"], "effective_mode": record["effective_mode"],
            "reason": record["reason"], "content_identity": record.get("content_identity"),
            "catalog_fingerprint": record.get("catalog_fingerprint"), "rule_version": record.get("rule_version"),
            "decisions": [{k: d.get(k) for k in ("requested_id", "selected_id", "status", "reason", "required")}
                          for d in plan.get("decisions") or []],
            "mandatory_cost": plan.get("mandatory_cost"), "payload_cost": plan.get("payload_cost")}


class OrdinaryAcquisition:
    """Run-owned MCP authority plus wrapper handoff for one ordinary attempt."""

    def __init__(self, binary: Path, prefix: str, allowed: list[str], recovery: list[str]) -> None:
        self.binary = Path(binary)
        self.prefix = prefix
        self.allowed = list(allowed)
        self.recovery_ids = list(recovery)

    def _suffix(self, record) -> str:
        # The prefix separates semantic and review-retry attempts of one stage.
        return hashlib.sha256(json.dumps([record["run_id"], record["binding_id"], record["attempt_id"],
                                          record.get("attempt_number"), self.prefix]).encode()).hexdigest()

    def prepare(self, record, run_dir, argv):
        from .acquisition_launch import PROTOCOL, MAX_MESSAGE, _capture, _json, _new, _verify_recovery
        from .claude_context_acquisition import OPTION, representable
        run_dir = Path(run_dir)
        if any(a.split("=", 1)[0] == OPTION for a in argv):
            raise ContextFallback("acquisition_prelaunch_failed", "duplicate context acquisition option")
        authority = {"run_dir": str(run_dir), "run_id": record["run_id"], "binding_id": record["binding_id"],
                     "attempt_id": record["attempt_id"], "consumer": "claude",
                     "catalog": {"schema_version": "apg.skill-catalog/v1", "snapshots": [], "overrides": []},
                     "allowed_ids": self.allowed}
        suffix = self._suffix(record)
        try:
            initial = _new(run_dir, "acquisition-prelaunch-" + suffix + ".json", {**authority, "preparation": True})
            recovery = []
            for candidate in self.recovery_ids:
                result = _capture([str(self.binary), "skills", "acquire", candidate, "--prepare-only", "--config", initial])
                if result.returncode or len(result.stdout) > MAX_MESSAGE:
                    raise ValueError("recovery preparation failed")
                selected = _json(result.stdout)
                _verify_recovery(run_dir, selected)
                body = base64.b64decode(selected["selection"]["snapshot"]["body"], validate=True)
                path = run_dir / (selected["materialized_path"] + "/SKILL.md")
                recovery.append({"id": candidate, "path": selected["materialized_path"] + "/SKILL.md",
                                 "absolute_path": str(path), "bytes": len(body),
                                 "sha256": hashlib.sha256(body).hexdigest(),
                                 "content_identity": selected["selection"]["content_identity"]})
            self._probe(initial)
        except ContextFallback:
            raise
        except Exception as error:
            raise ContextFallback("acquisition_prelaunch_failed", type(error).__name__) from error
        if any(not representable(row["absolute_path"]) for row in recovery):
            raise ContextFallback("recovery_path_unrepresentable")
        self.pending = (run_dir, "acquisition-server-" + suffix + ".json", authority)
        self.handoff = run_dir / ("context-acquisition-" + suffix + ".json")
        details = {"seam": SEAM, "protocol": PROTOCOL, "config": str(run_dir / self.pending[1]),
                   "allowed_ids": list(self.allowed), "recovery": recovery,
                   "context_handoff": str(self.handoff), "tools_exposed": "mcp__apgr__skill_search,mcp__apgr__skill_acquire,mcp__apgr__context_explain",
                   "boundary": "embedded apgr: skills only; project/user bodies are not retained by the plan",
                   "status": "prelaunch_available", "model_observed": None, "replay_authorized": False}
        return [*argv, OPTION, str(self.handoff)], details

    def notice(self, record) -> str:
        rows = record["acquisition"]["recovery"]
        text = ("\nAPGR context: optional skills above were selected for this attempt. Other embedded APGR "
                "skills are available on request through mcp__apgr__skill_search and mcp__apgr__skill_acquire. "
                "If that server fails, preserve this attempt; do not replay it or seek shell authority.\n")
        if rows:
            text += "Budget-deferred skill copies readable with the native Read tool:\n"
            text += "".join(f"{row['id']}: {row['absolute_path']}\n" for row in rows)
        return text

    def _probe(self, config: str) -> None:
        from .acquisition_launch import PROTOCOL, MAX_MESSAGE, _capture, _json
        probe = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": PROTOCOL, "capabilities": {}, "clientInfo": {"name": "apgr-prelaunch", "version": "1"}}}
        result = _capture([str(self.binary), "mcp", "serve", "--config", config], (json.dumps(probe) + "\n").encode())
        if result.returncode or len(result.stdout) > MAX_MESSAGE:
            raise ValueError("MCP prelaunch failed")
        response = _json(result.stdout)
        if (response.get("jsonrpc") != "2.0" or response.get("id") != 1
                or response.get("result", {}).get("protocolVersion") != PROTOCOL
                or response["result"].get("capabilities") != {"tools": {}, "resources": {}}):
            raise ValueError("MCP protocol mismatch")

    def finalize(self, record):
        from .acquisition_launch import _new
        from .claude_context_acquisition import create
        run_dir, name, authority = self.pending
        compact = compact_plan(record)
        raw = json.dumps(compact, sort_keys=True).encode()
        if len(raw) > 700 * 1024:
            raise ContextFallback("acquisition_config_failed", "compact plan exceeds server bound")
        config = _new(run_dir, name, {**authority, "context_plan": compact})
        self._probe(config)
        create(self.handoff, record, config=Path(config), binary=self.binary,
               server=[str(self.binary), "mcp", "serve", "--config", config])
