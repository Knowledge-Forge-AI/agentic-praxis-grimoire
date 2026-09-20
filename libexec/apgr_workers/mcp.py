"""Small on-demand MCP facade for an already registered worker parent.

The process owns only the JSON-RPC transport.  Parent registration, policy
resolution, and worker launch remain in the existing ledger and adapter.  The
fixed context is supplied by the Claude launcher and checked against the live
ledger before every operation; no request can choose a parent or executable.
"""

from __future__ import annotations

import json
import math
import re
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    _LIBEXEC = str(Path(__file__).resolve().parents[1])
    if _LIBEXEC not in sys.path:
        sys.path.insert(0, _LIBEXEC)
    from apgr_workers.adapter import (
        cancel_worker_job,
        launch_worker_job,
        wait_worker_job,
    )
    from apgr_workers.facade_context import WorkerFacadeContext, load_server_context
else:
    from .adapter import cancel_worker_job, launch_worker_job, wait_worker_job
    from .facade_context import WorkerFacadeContext, load_server_context


PROTOCOL_VERSION = "2025-06-18"
SERVER_NAME = "agent_worker"
SERVER_VERSION = "1"
DEFAULT_WAIT_SECONDS = 5.0
MAX_WAIT_SECONDS = 30.0
MAX_TASK_CHARS = 16_384
MAX_ACCEPTANCE_CHARS = 8_192
MAX_SCOPE_ITEMS = 64
MAX_SCOPE_ITEM_CHARS = 512
MAX_RESULT_BYTES = 128 * 1024
MAX_LINE_BYTES = 1 * 1024 * 1024
_READ_ONLY_DELEGATION_DESCRIPTION = (
    "Submit one bounded leaf worker task. A read-only task is authorized "
    "read-only inspection; facade ledger and outbox writes are launcher-owned "
    "orchestration bookkeeping and do not grant product mutation. No plan-file "
    "workflow is needed for a read-only task. Stay within the current permission "
    "mode and explicitly exposed tools. The worker cannot create another worker."
)
_MUTATION_CAPABLE_DELEGATION_DESCRIPTION = (
    "Submit one bounded leaf worker task. A mutation-capable task is authorized "
    "mutation strictly within its caller-declared mutation_scope paths, which must "
    "be disjoint from other active worker scopes. Outbox writes and ledger entries "
    "are launcher-owned bookkeeping. Stay within the current permission mode and "
    "explicitly exposed tools. The worker cannot create another worker."
)

_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_AUTHORITIES = frozenset({"read_only", "mutation_capable"})
_TOOL_ARGUMENT_KEYS = {
    "submit": frozenset(
        {"task", "key", "task_authority", "mutation_scope", "acceptance_criteria",
         "worker_kind", "task_id", "previous_job_id", "recovery_decision", "recovery_reason"}
    ),
    "status": frozenset({"job_id"}),
    "result": frozenset({"job_id"}),
    "wait": frozenset({"job_id", "timeout"}),
    "cancel": frozenset({"job_id"}),
    "abandon": frozenset({"job_id", "reason"}),
    "pause_pool": frozenset({"worker_kind", "reason", "evidence"}),
    "outcome": frozenset({"job_id", "outcome", "evidence"}),
}


class MCPRequestError(ValueError):
    """A malformed JSON-RPC request or tool input."""


def _bounded_string(value: Any, name: str, maximum: int, *, required: bool = True) -> str | None:
    if not isinstance(value, str):
        if value is None and not required:
            return None
        raise MCPRequestError(f"{name} must be text")
    if required and not value.strip():
        raise MCPRequestError(f"{name} must not be empty")
    if len(value) > maximum:
        raise MCPRequestError(f"{name} exceeds the {maximum}-character limit")
    return value


def _identifier(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER_RE.fullmatch(value):
        raise MCPRequestError(f"{name} is not a safe identifier")
    return value


def _arguments(params: Any) -> dict[str, Any]:
    if not isinstance(params, Mapping):
        raise MCPRequestError("tools/call params must be an object")
    value = params.get("arguments", {})
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise MCPRequestError("tool arguments must be an object")
    return dict(value)


def _project_job(job: Mapping[str, Any]) -> dict[str, Any]:
    """Return bounded worker evidence without exposing process internals."""
    projected: dict[str, Any] = {}
    for key in (
        "job_id",
        "status",
        "task_authority",
        "error",
        "cleanup_proven",
        "created_at",
        "updated_at",
        "worker_kind",
        "task_id",
        "previous_job_id",
        "attempt_number",
        "recovery_decision",
        "recovery_reason",
        "abandonment",
        "task_file",
        "task_outcome",
        "task_outcome_evidence",
        "provider_status",
        "cleanup_status",
        "cancellation_decision",
    ):
        if key in job:
            projected[key] = job[key]
    result = job.get("result")
    if isinstance(result, Mapping):
        projected["result"] = dict(result)
    created = job.get("created_at")
    projected["age_seconds"] = max(0.0, time.time() - created) if isinstance(created, (int, float)) else None
    projected["last_meaningful_progress"] = None
    projected["last_tool_state"] = None
    projected["partial_output"] = None
    task_file = job.get("task_file")
    job_id = job.get("job_id")
    if isinstance(task_file, str) and isinstance(job_id, str):
        path = Path(task_file).parent / f"{job_id}.stdout.md"
        try:
            stat = path.stat()
            projected["partial_output"] = {"path": str(path), "bytes": stat.st_size,
                                            "last_output_at": stat.st_mtime,
                                            "meaningful_progress": "unknown"}
        except OSError:
            pass
    return projected


def _bounded_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Keep one MCP response bounded even when provider output is very large."""
    candidate = dict(payload)
    encoded = json.dumps(candidate, ensure_ascii=False, separators=(",", ":"))
    if len(encoded.encode("utf-8")) <= MAX_RESULT_BYTES:
        return candidate
    result = candidate.get("result")
    if isinstance(result, Mapping):
        reduced = dict(result)
        for key in ("response", "text", "output", "raw_response"):
            value = reduced.get(key)
            if isinstance(value, str):
                reduced[key] = value[:16_384] + "\n[facade result truncated]"
        candidate["result"] = reduced
    encoded = json.dumps(candidate, ensure_ascii=False, separators=(",", ":"))
    if len(encoded.encode("utf-8")) <= MAX_RESULT_BYTES:
        return candidate
    return {
        "job_id": candidate.get("job_id"),
        "status": candidate.get("status"),
        "error": "worker result exceeded the MCP response limit",
        "result_truncated": True,
    }


class WorkerMCPServer:
    """Handle the small fixed tool surface for one parent lifetime."""

    def __init__(self, context: WorkerFacadeContext) -> None:
        self.context = context

    def _ensure_context(self) -> dict[str, Any]:
        return self.context.assert_current()

    def _allowed_worker_kinds(self) -> list[str]:
        try:
            status = self.context.ledger.get_status()
            allowed = status.get("allowed_worker_kinds")
            if not isinstance(allowed, list):
                cap = status.get("worker_capability")
                if isinstance(cap, Mapping):
                    allowed = cap.get("allowed_worker_kinds")
            if isinstance(allowed, list):
                return [str(k) for k in allowed if k in ("gemini", "luna", "sonnet")]
        except Exception:
            pass
        return []

    def _pausable_pool_kinds(self) -> list[str]:
        kinds = self._allowed_worker_kinds()
        cap = self.context.ledger.get_status().get("worker_capability") or {}
        if (cap.get("sonnet_worker", {}).get("transport") == "claude_native"
                and "sonnet" not in cap.get("excluded_worker_kinds", [])):
            kinds = [*kinds, "sonnet"]
        return kinds

    def _tool_specs(self) -> list[dict[str, Any]]:
        submit_read_only = self.context.task_authority == "read_only"
        submit_description = (
            _READ_ONLY_DELEGATION_DESCRIPTION
            if submit_read_only
            else _MUTATION_CAPABLE_DELEGATION_DESCRIPTION
        )
        allowed_kinds = self._allowed_worker_kinds()
        specs = [
            {
                "name": "submit",
                "description": submit_description,
                # Read-only product authority still starts a process and writes
                # orchestration state. Permission comes from exact launcher rules.
                "annotations": {"readOnlyHint": False},
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string", "minLength": 1, "maxLength": MAX_TASK_CHARS},
                        "key": {"type": "string", "pattern": _IDENTIFIER_RE.pattern},
                        "worker_kind": {"type": "string", "enum": allowed_kinds},
                        "task_id": {"type": "string", "pattern": _IDENTIFIER_RE.pattern},
                        "previous_job_id": {"type": "string", "pattern": _IDENTIFIER_RE.pattern},
                        "recovery_decision": {"type": "string", "enum": ["adopt", "amend", "reject", "continue"]},
                        "recovery_reason": {"type": "string", "maxLength": MAX_ACCEPTANCE_CHARS},
                        "task_authority": {
                            "type": "string",
                            "enum": ["read_only", "mutation_capable"],
                        },
                        "mutation_scope": {
                            "type": "array",
                            "maxItems": MAX_SCOPE_ITEMS,
                            "items": {"type": "string", "minLength": 1, "maxLength": MAX_SCOPE_ITEM_CHARS},
                        },
                        "acceptance_criteria": {
                            "type": "string",
                            "maxLength": MAX_ACCEPTANCE_CHARS,
                        },
                    },
                    "required": ["task"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "status",
                "description": "Read the status of one submitted worker job.",
                "annotations": {"readOnlyHint": True},
                "inputSchema": self._job_schema(),
            },
            {
                "name": "result",
                "description": "Read terminal evidence or current status for one worker job.",
                "annotations": {"readOnlyHint": True},
                "inputSchema": self._job_schema(),
            },
            {
                "name": "wait",
                "description": (
                    "Wait for one worker job for a bounded interval; a timeout "
                    "returns still-running status and is not worker failure."
                ),
                "annotations": {"readOnlyHint": True},
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "job_id": {"type": "string", "pattern": _IDENTIFIER_RE.pattern},
                        "timeout": {"type": "number", "minimum": 0, "maximum": MAX_WAIT_SECONDS},
                    },
                    "required": ["job_id"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "outcome",
                "description": "Record the parent's task disposition with evidence. This changes owned bookkeeping only; it does not assert provider termination or release custody.",
                "annotations": {"readOnlyHint": False},
                "inputSchema": {"type": "object", "properties": {
                    "job_id": {"type": "string", "pattern": _IDENTIFIER_RE.pattern},
                    "outcome": {"type": "string", "enum": ["partial", "accepted", "rejected", "failed", "cancelled"]},
                    "evidence": {"type": "string", "minLength": 1, "maxLength": MAX_ACCEPTANCE_CHARS}},
                    "required": ["job_id", "outcome", "evidence"], "additionalProperties": False},
            },
            {
                "name": "pause_pool",
                "description": "Pause new admissions to an allowed pool for this parent. In-flight jobs retain custody. No timer or automatic quota retry is started.",
                "annotations": {"readOnlyHint": False},
                "inputSchema": {"type": "object", "properties": {
                    "worker_kind": {"type": "string", "enum": self._pausable_pool_kinds()},
                    "reason": {"type": "string", "minLength": 1, "maxLength": MAX_ACCEPTANCE_CHARS},
                    "evidence": {"type": "string", "minLength": 1, "maxLength": MAX_ACCEPTANCE_CHARS}},
                    "required": ["worker_kind", "reason", "evidence"], "additionalProperties": False},
            },
            {
                "name": "abandon",
                "description": "Record a deliberate stop decision, cancel the exact job, and retain partial work. Cleanup must be proven before a replacement writer starts.",
                "annotations": {"readOnlyHint": False},
                "inputSchema": {"type": "object", "properties": {
                    "job_id": {"type": "string", "pattern": _IDENTIFIER_RE.pattern},
                    "reason": {"type": "string", "minLength": 1, "maxLength": MAX_ACCEPTANCE_CHARS}},
                    "required": ["job_id", "reason"], "additionalProperties": False},
            },
            {
                "name": "cancel",
                "description": "Request cancellation of one worker job and return cleanup evidence.",
                "annotations": {"readOnlyHint": False},
                "inputSchema": self._job_schema(),
            },
        ]
        return [spec for spec in specs if (spec["name"] != "submit" or allowed_kinds)
                and (spec["name"] != "pause_pool" or self._pausable_pool_kinds())]

    @staticmethod
    def _job_schema() -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "pattern": _IDENTIFIER_RE.pattern},
            },
            "required": ["job_id"],
            "additionalProperties": False,
        }

    def _job(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        self._ensure_context()
        job_id = _identifier(arguments.get("job_id"), "job_id")
        return _bounded_payload(_project_job(self.context.ledger.get_job(job_id)))

    def _submit(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        self._ensure_context()
        task = _bounded_string(arguments.get("task"), "task", MAX_TASK_CHARS)
        assert task is not None
        requested_authority = arguments.get("task_authority", self.context.task_authority)
        if requested_authority not in _AUTHORITIES:
            raise MCPRequestError("task_authority must be read_only or mutation_capable")
        if self.context.task_authority == "read_only" and requested_authority != "read_only":
            raise MCPRequestError("a read-only parent cannot submit a mutating task")

        raw_scope = arguments.get("mutation_scope", [])
        if raw_scope is None:
            raw_scope = []
        if not isinstance(raw_scope, list) or len(raw_scope) > MAX_SCOPE_ITEMS:
            raise MCPRequestError("mutation_scope must be a bounded list")
        scope: list[str] = []
        for item in raw_scope:
            value = _bounded_string(item, "mutation_scope item", MAX_SCOPE_ITEM_CHARS)
            assert value is not None
            scope.append(value)
        if requested_authority == "read_only" and scope:
            raise MCPRequestError("read-only tasks cannot include mutation_scope")

        key = arguments.get("key")
        if key is not None:
            key = _identifier(key, "key")
        acceptance = _bounded_string(
            arguments.get("acceptance_criteria"),
            "acceptance_criteria",
            MAX_ACCEPTANCE_CHARS,
            required=False,
        )
        allowed_kinds = self._allowed_worker_kinds()
        worker_kind = arguments.get("worker_kind")
        if worker_kind is None:
            worker_kind = "gemini" if "gemini" in allowed_kinds else (allowed_kinds[0] if allowed_kinds else "gemini")
        elif worker_kind not in allowed_kinds:
            raise MCPRequestError(f"worker_kind {worker_kind!r} is not allowed")
        result = launch_worker_job(
            parent_id=self.context.parent_id,
            task=task,
            idempotency_key=key,
            task_authority=requested_authority,
            mutation_scope=scope,
            acceptance_criteria=acceptance,
            state_dir=self.context.state_dir,
            worker_kind=worker_kind,
            **{key: (_identifier(arguments[key], key) if key in {"task_id", "previous_job_id"}
                      else _bounded_string(arguments[key], key, MAX_ACCEPTANCE_CHARS))
               for key in ("task_id", "previous_job_id", "recovery_decision", "recovery_reason")
               if key in arguments},
        )
        return _bounded_payload(_project_job(result))

    def _wait(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        self._ensure_context()
        job_id = _identifier(arguments.get("job_id"), "job_id")
        timeout = arguments.get("timeout", DEFAULT_WAIT_SECONDS)
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
            raise MCPRequestError("timeout must be a finite number")
        if not math.isfinite(float(timeout)) or timeout < 0 or timeout > MAX_WAIT_SECONDS:
            raise MCPRequestError(f"timeout must be between 0 and {MAX_WAIT_SECONDS} seconds")
        try:
            observation = wait_worker_job(
                parent_id=self.context.parent_id,
                job_id=job_id,
                timeout_seconds=float(timeout),
                state_dir=self.context.state_dir,
            )
            # ``wait_worker_job`` returns the terminal result payload for the
            # CLI.  MCP must project the containing ledger job so the provider
            # response remains available under ``result`` together with
            # cleanup evidence.
            projected = _project_job(self.context.ledger.get_job(job_id))
            if observation.get("timed_out"):
                projected.update(timed_out=True, decision_required=True)
            return _bounded_payload(projected)
        except TimeoutError:
            current = _project_job(self.context.ledger.get_job(job_id))
            current["timed_out"] = True
            return _bounded_payload(current)

    def _cancel(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        self._ensure_context()
        job_id = _identifier(arguments.get("job_id"), "job_id")
        cancel_worker_job(
            self.context.parent_id,
            job_id,
            state_dir=self.context.state_dir,
        )
        return _bounded_payload(_project_job(self.context.ledger.get_job(job_id)))

    def _call_tool(self, name: Any, arguments: Mapping[str, Any]) -> dict[str, Any]:
        allowed = _TOOL_ARGUMENT_KEYS.get(name)
        if allowed is None:
            raise MCPRequestError(f"unknown worker tool: {name}")
        unknown = sorted(set(arguments) - allowed)
        if unknown:
            raise MCPRequestError(
                f"unknown arguments for {name}: {', '.join(str(item) for item in unknown)}"
            )
        if name == "submit":
            return self._submit(arguments)
        if name == "status":
            return self._job(arguments)
        if name == "result":
            return self._job(arguments)
        if name == "wait":
            return self._wait(arguments)
        if name == "cancel":
            return self._cancel(arguments)
        if name == "abandon":
            self._ensure_context()
            self.context.ledger.record_abandonment(
                _identifier(arguments.get("job_id"), "job_id"),
                _bounded_string(arguments.get("reason"), "reason", MAX_ACCEPTANCE_CHARS))
            return self._cancel(arguments)
        if name == "pause_pool":
            self._ensure_context()
            worker_kind = arguments.get("worker_kind")
            if worker_kind not in self._pausable_pool_kinds():
                raise MCPRequestError(f"worker_kind {worker_kind!r} is not allowed")
            return self.context.ledger.pause_pool(
                worker_kind,
                _bounded_string(arguments.get("reason"), "reason", MAX_ACCEPTANCE_CHARS),
                _bounded_string(arguments.get("evidence"), "evidence", MAX_ACCEPTANCE_CHARS))
        if name == "outcome":
            self._ensure_context()
            outcome = arguments.get("outcome")
            if outcome not in {"partial", "accepted", "rejected", "failed", "cancelled"}:
                raise MCPRequestError("invalid task outcome")
            return _project_job(self.context.ledger.record_task_outcome(
                _identifier(arguments.get("job_id"), "job_id"), outcome,
                _bounded_string(arguments.get("evidence"), "evidence", MAX_ACCEPTANCE_CHARS)))
        raise MCPRequestError(f"unknown worker tool: {name}")

    @staticmethod
    def _tool_content(payload: Mapping[str, Any], *, is_error: bool = False) -> dict[str, Any]:
        value = _bounded_payload(payload)
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(value, ensure_ascii=False, sort_keys=True),
                }
            ],
            "isError": is_error,
        }

    def handle(self, request: Mapping[str, Any]) -> dict[str, Any] | None:
        method = request.get("method")
        request_id = request.get("id")
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                },
            }
        if isinstance(method, str) and method.startswith("notifications/"):
            return None
        try:
            if method == "ping":
                result: Any = {}
            elif method == "tools/list":
                self._ensure_context()
                result = {"tools": self._tool_specs()}
            elif method == "tools/call":
                params = request.get("params")
                if not isinstance(params, Mapping):
                    raise MCPRequestError("tools/call params must be an object")
                name = params.get("name")
                arguments = _arguments(params)
                try:
                    result = self._tool_content(self._call_tool(name, arguments))
                except Exception as error:  # noqa: BLE001 - keep one tool failure from killing the transport
                    result = self._tool_content(
                        {
                            "status": "error",
                            "error_type": type(error).__name__,
                            "error": str(error),
                        },
                        is_error=True,
                    )
            else:
                raise MCPRequestError(f"method not found: {method}")
        except MCPRequestError as error:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32602, "message": str(error)},
            }
        except Exception as error:  # noqa: BLE001 - convert ledger failures to JSON-RPC errors
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32000, "message": str(error)},
            }
        return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _write_response(response: Mapping[str, Any]) -> None:
    sys.stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def main() -> int:
    try:
        context = load_server_context()
    except Exception as error:  # noqa: BLE001 - invalid optional context is a local startup result
        print(f"agent-worker-mcp: unavailable ({type(error).__name__})", file=sys.stderr, flush=True)
        return 2
    server = WorkerMCPServer(context)
    for line in sys.stdin:
        if len(line.encode("utf-8", "replace")) > MAX_LINE_BYTES:
            _write_response({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32600, "message": "request exceeds the size limit"},
            })
            continue
        try:
            request = json.loads(line)
            if not isinstance(request, Mapping) or request.get("jsonrpc") != "2.0":
                raise MCPRequestError("request must be a JSON-RPC 2.0 object")
            response = server.handle(request)
        except (UnicodeDecodeError, json.JSONDecodeError, MCPRequestError) as error:
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32600, "message": str(error)},
            }
        if response is not None and "id" in response:
            _write_response(response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
