"""Provider-free qualification of the complete fifteen-scenario package.

The dry-run materializes both subject arms, builds provider argv and context
plans, resolves importers and substantive oracles, and records every missing
piece explicitly. It never calls a model provider and never writes an
aggregate result.
"""
from __future__ import annotations

import hashlib
import importlib
import inspect
import json
import os
import shlex
import shutil
import tempfile
from collections.abc import Callable, Mapping
from contextvars import ContextVar
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from agent_phase import context_adapter, provider
from agent_phase.transmission import direct_bytes

from . import execution, importers
from .evaluate import encoded, load
from .preregistration import verify_bindings

SCHEMA = "apg.h-dry-run/v1"
MODES = ("static", "adaptive")

ACTIVE_RUNTIME = ContextVar("h_provider_free_runtime", default=None)


def _write_new(path: Path, value: Any) -> None:
    if path.parent.resolve() != path.parent or path.exists() or path.is_symlink():
        raise ValueError("dry-run artifact destination must be new and physical")
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        child = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        with os.fdopen(child, "wb") as stream:
            stream.write(encoded(value))
            stream.flush()
            os.fsync(stream.fileno())
        os.fsync(fd)
    finally:
        os.close(fd)


def _invoke(target: Callable[..., Any], values: Mapping[str, Any]) -> Any:
    try:
        signature = inspect.signature(target)
    except (TypeError, ValueError):
        return target(*[values[k] for k in ("scenario", "destination", "mode") if k in values])
    names = set(signature.parameters)
    kwargs = {name: value for name, value in values.items() if name in names}
    try:
        signature.bind(**kwargs)
    except TypeError:
        positional = [values[k] for k in ("scenario", "destination", "mode") if k in values]
        signature.bind(*positional)
        return target(*positional)
    return target(**kwargs)


def _subject_target(factory: Any) -> Callable[..., Any] | None:
    for name in ("materialize_subject", "materialize", "build_subject", "subject_files"):
        target = getattr(factory, name, None)
        if callable(target):
            return target
    if callable(factory):
        return factory
    return None


def _copy_files(destination: Path, files: Mapping[str, bytes | str]) -> None:
    execution._materialize(destination, files)


def _normalize_subject(value: Any, destination: Path) -> dict[str, Any]:
    if isinstance(value, Mapping) and isinstance(value.get("files"), list):
        if not destination.is_dir():
            raise ValueError("subject factory inventory has no materialized root")
        return {"files": execution.snapshot_tree(destination), "factory": dict(value)}
    if isinstance(value, Mapping) and isinstance(value.get("files"), Mapping):
        files = value["files"]
        if destination.exists() and not execution.snapshot_tree(destination):
            _copy_files(destination, files)
        elif not destination.exists():
            destination.mkdir(mode=0o700)
            _copy_files(destination, files)
        return {"files": execution.snapshot_tree(destination), "factory": dict(value)}
    if isinstance(value, Mapping) and all(isinstance(key, str) for key in value):
        if not destination.exists():
            destination.mkdir(mode=0o700)
        _copy_files(destination, value)
        return {"files": execution.snapshot_tree(destination), "factory": {"files": dict(value)}}
    if isinstance(value, (str, Path)) or value is None:
        if value is not None and Path(value).resolve() != destination.resolve():
            source = Path(value)
            if not source.is_dir():
                raise ValueError("subject factory returned a non-directory")
            for name in execution.snapshot_tree(source):
                target = destination / name
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                target.write_bytes(direct_bytes(source / name, utf8=False))
        if not destination.is_dir():
            raise ValueError("subject factory did not materialize a directory")
        return {"files": execution.snapshot_tree(destination), "factory": {"path": str(destination)}}
    if hasattr(value, "files"):
        return _normalize_subject({"files": value.files}, destination)
    raise ValueError("unsupported subject factory result")


def materialize_subject(factory: Any, *, root: Path, scenario: Mapping[str, Any], destination: Path, mode: str) -> dict[str, Any]:
    target = _subject_target(factory)
    if target is None:
        raise ValueError("subject factory is unavailable")
    value = _invoke(target, {
        "root": root,
        "repository_root": root,
        "scenario": scenario,
        "scenario_id": scenario["scenario_id"],
        "corpus_root": root / "testing/fixtures/context-eval",
        "destination": destination,
        "output": destination,
        "mode": mode,
        "arm": mode,
    })
    return _normalize_subject(value, destination)


def _load_subject_factory(factory: Any) -> Any:
    if factory is not None:
        return factory
    return importlib.import_module("testing.h_eval.subjects")


def _load_oracle_owner(owner: Any) -> Any:
    if owner is not None:
        return owner
    return importlib.import_module("testing.h_eval.oracles")


def _oracle_target(owner: Any, scenario: Mapping[str, Any]) -> Any:
    for name in ("oracle_for", "get_oracle", "resolve_oracle"):
        target = getattr(owner, name, None)
        if callable(target):
            return _invoke(target, {"scenario": scenario})
    if callable(owner):
        return _invoke(owner, {"scenario": scenario})
    return getattr(owner, scenario["scenario_id"].replace("-", "_"), None)


def exercise_oracle(owner: Any, oracle: Any, *, root: Path, scenario: Mapping[str, Any],
                    runtime_manifest=None, fixture_root=None) -> dict[str, Any]:
    target = getattr(owner, "exercise_oracle", None)
    if not callable(target):
        target = getattr(oracle, "exercise", None)
    if not callable(target):
        return {"status": "incomplete", "reason": "oracle good/bad fixture exercise owner unavailable"}
    value = _invoke(target, {"root": root, "scenario": scenario, "oracle": oracle,
                             "runtime_manifest": runtime_manifest, "fixture_root": fixture_root})
    if isinstance(value, Mapping):
        if value.get("good") is True and value.get("bad") is True:
            return {"status": "complete", "good": True, "bad": True, "evidence": dict(value)}
        return {"status": "incomplete", "reason": "oracle fixture exercise did not prove good and bad cases", "evidence": dict(value)}
    return {"status": "incomplete", "reason": "oracle fixture exercise returned no positive and negative proof"}


def _runtime_executable(manifest: Mapping[str, Any] | None, name: str) -> str | None:
    if not isinstance(manifest, Mapping) or manifest.get("schema") != "apg.h-runtime-inputs/v2":
        return None
    record = manifest.get("runtimes", {}).get(name)
    if not isinstance(record, Mapping):
        return None
    entry = manifest.get("files", {}).get(record.get("executable"))
    if not isinstance(entry, Mapping):
        return None
    physical = entry.get("physical_path")
    return str(physical) if isinstance(physical, str) else None


def _provider_binding(manifest: Mapping[str, Any] | None, provider_name: str) -> dict[str, Any]:
    physical = _runtime_executable(manifest, provider_name)
    if physical is None:
        return {"status": "unavailable", "reason": "provider runtime is not bound in the complete manifest"}
    return {"status": "resolved", "runtime": provider_name, "physical_path": physical}


class _ProviderFreeProjection:
    """Repository-owned projection seam for provider-free plan mechanics.

    It preserves the native planner payload and argv authority, while its
    qualification is explicitly limited to plumbing.  It cannot establish
    native provider discovery or live selective-projection qualification.
    """

    def __init__(self, *, run_dir: Path, scenario_id: str, source_root: Path) -> None:
        self.run_dir = run_dir
        self.scenario_id = scenario_id
        self.source_root = source_root
        self.run_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.settings_path = self.run_dir / "provider-free-settings.json"
        if not self.settings_path.exists():
            self.settings_path.write_text(json.dumps({
                "schema": "apg.h-provider-free-projection/v1",
                "scenario_id": scenario_id,
                "qualification": "plumbing-only",
            }, sort_keys=True) + "\n")

    def qualification(self) -> dict[str, Any]:
        return {
            "selective_projection": True,
            "independent_recovery": True,
            "evidence": "provider-free context transport mechanics only",
        }

    def project(self, plan: Mapping[str, Any], argv: list[str], prompt: bytes) -> tuple[list[str], bytes]:
        payload = plan.get("payload")
        if not isinstance(payload, str) or prompt not in payload.encode():
            raise ValueError("provider-free projection changed the mandatory task payload")
        if self.scenario_id == "scenario-15":
            from .projection_qualification import materialize
            materialize(self.source_root, self.run_dir / "selected", plan)
        return list(argv), payload.encode()


def _frozen_plan_inputs(root: Path, scenario: Mapping[str, Any], route: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Bind provider doctrine, scenario facts, overrides, and budget bytes."""
    instructions = scenario.get("mandatory_instructions") or {}
    provider_file = instructions.get("provider_file")
    if not isinstance(provider_file, str) or Path(provider_file).is_absolute() or ".." in Path(provider_file).parts:
        raise ValueError("frozen provider instruction source unavailable")
    standing_path = root / provider_file
    standing = direct_bytes(standing_path, utf8=False)
    declared = instructions.get("provider_instruction_bytes")
    if type(declared) is not int:
        raise ValueError("frozen provider instruction measurement unavailable")
    components = [{
        "id": "provider-standing",
        "kind": "standing",
        "text": standing.decode("utf-8"),
        "source_path": provider_file,
        "source_sha256": hashlib.sha256(standing).hexdigest(),
    }]
    records = [{
        "id": "provider-standing",
        "source_path": provider_file,
        "bytes": len(standing),
        "historical_apg159a_bytes": declared,
        "sha256": hashlib.sha256(standing).hexdigest(),
        "declared_doctrine_bytes": instructions.get("mandatory_doctrine_bytes"),
    }]
    evidence = scenario.get("repository_evidence") or {}
    facts: list[dict[str, Any]] = []
    if isinstance(evidence.get("primary_language"), str):
        facts.append({"kind": "language", "value": evidence["primary_language"]})
    for relative in evidence.get("files", []):
        if not isinstance(relative, str) or Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise ValueError("unsafe frozen repository fact")
        # The clean subject owns these files; the exact subject-relative bytes
        # are verified by the subject factory before planning.  Keep only the
        # frozen path fact in the planner request here.
        facts.append({"kind": "repository_file", "value": relative})
    project = (scenario.get("catalog_sources") or {}).get("project")
    if isinstance(project, Mapping):
        facts.append({"kind": "synthetic_project_skill", "value": str(project.get("id", ""))})
    facts.append({"kind": "role_binding", "value": route["role_binding"]["binding_id"]})
    budget = scenario.get("budget") or {}
    settings: dict[str, Any] = {}
    if type(budget.get("max_initial_controlled_bytes")) is int:
        settings["max_initial_context_bytes"] = budget["max_initial_controlled_bytes"]
    if type(budget.get("max_initial_controlled_characters")) is int:
        settings["max_initial_context_characters"] = budget["max_initial_controlled_characters"]
    override_records = []
    config = (evidence.get("configuration_facts") or {}).get("project_config")
    for requested, selected in sorted((scenario.get("overrides") or {}).items()):
        if not isinstance(config, str):
            raise TypeError("project override configuration bytes unavailable")
        override_records.append({
            "requested": requested,
            "selected": selected,
            "config_path": ".apgr/config.toml",
            "config_sha256": hashlib.sha256(config.encode()).hexdigest(),
        })
    return components, records, {"facts": facts, "settings": settings,
                                 "overrides": override_records}


def _native_frozen_planner(request: Mapping[str, Any], capture: Mapping[str, Any],
                           *, mandatory: list[dict[str, Any]], facts: list[dict[str, Any]],
                           overrides: list[Mapping[str, Any]]) -> dict[str, Any]:
    enriched = json.loads(json.dumps(request))
    # Keep the frozen task envelope first: the projection seam requires the
    # planned payload to retain the exact caller prompt prefix.
    enriched["mandatory"] = [*enriched.get("mandatory", []), *mandatory]
    enriched["facts"] = [*facts]
    enriched["catalog"]["overrides"] = [dict(value) for value in overrides]
    from agent_phase.context_adapter import native_plan
    transaction = ACTIVE_RUNTIME.get()
    if transaction is not None:
        arguments = ["skills", "plan", "--stdin", "--apgr-home", capture["apgr_home"]]
        if capture.get("project_root"):
            arguments.extend(["--project-root", capture["project_root"]])
        result = transaction.run("apgr", arguments, stdin=context_adapter.canonical(enriched),
                                 cwd=Path(capture["apgr_home"]))
        if result.returncode or len(result.stdout) > context_adapter.MAX_PLAN_BYTES:
            raise ValueError("manifest-bound native context planner failed")
        return json.loads(result.stdout)
    return native_plan(enriched, capture)


def _verify_frozen_subject_inputs(root: Path, scenario: Mapping[str, Any], subject_root: Path) -> None:
    """Bind synthetic catalog/config inputs before the native planner runs."""
    evidence = scenario.get("repository_evidence") or {}
    for relative in evidence.get("files", []):
        path = subject_root / relative
        if path.resolve() != path or not path.is_file() or path.is_symlink():
            raise ValueError(f"frozen subject input missing: {relative}")
    project = (scenario.get("catalog_sources") or {}).get("project")
    if isinstance(project, Mapping):
        relative = Path(str(project["canonical_path"]))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("unsafe synthetic project skill path")
        raw = direct_bytes(subject_root / relative, utf8=False)
        if len(raw) != project.get("whole_bytes") or hashlib.sha256(raw).hexdigest() != project.get("whole_sha256"):
            raise ValueError("synthetic project skill identity changed")
        marker = b"\n---\n"
        if marker not in raw[4:]:
            raise ValueError("synthetic project skill front matter missing")
        body = raw[raw.index(marker, 4) + len(marker):]
        if len(body) != project.get("body_bytes") or hashlib.sha256(body).hexdigest() != project.get("body_sha256"):
            raise ValueError("synthetic project skill body identity changed")
    config = (evidence.get("configuration_facts") or {}).get("project_config")
    if config is not None:
        config_path = subject_root / ".apgr/config.toml"
        if config_path.resolve() != config_path or not config_path.is_file() or config_path.read_text() != config:
            raise ValueError("frozen project configuration identity changed")
    for source in (scenario.get("skill_sources") or {}).values():
        relative = Path(str(source["canonical_path"]))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("unsafe canonical skill path")
        raw = direct_bytes(root / relative, utf8=False)
        if source.get("source_kind") == "planned_not_in_canonical_corpus":
            # APG159A explicitly delegated later RTK authoring/measurement;
            # its absent numerical fields are not frozen zero-byte claims.
            continue
        if len(raw) != source.get("whole_bytes"):
            raise ValueError("canonical skill whole identity changed")
        marker = b"\n---\n"
        if marker not in raw[4:]:
            raise ValueError("canonical skill front matter missing")
        body = raw[raw.index(marker, 4) + len(marker):]
        if len(body) != source.get("body_bytes") or hashlib.sha256(body).hexdigest() != source.get("body_sha256"):
            raise ValueError("canonical skill body identity changed")


def _route_argv(root: Path, route: Mapping[str, Any], scenario: Mapping[str, Any], mode: str,
                runtime_manifest: Mapping[str, Any] | None = None) -> list[str]:
    from .provider_free import ACTIVE_GUARD
    guard = ACTIVE_GUARD.get()
    endpoint = provider.Endpoint(route["provider"], route["profile"])
    read_only = scenario["task_input"]["task_authority"] == "read_only"
    paths = {
        "codex_executable": "/__apg_provider_free_unbound__/codex",
        "claude_launcher": "/__apg_provider_free_unbound__/claude",
        "antigravity_launcher": "/__apg_provider_free_unbound__/antigravity",
    }
    if guard is not None:
        key = {"codex": "codex_executable", "claude": "claude_launcher",
               "antigravity": "antigravity_launcher"}[route["provider"]]
        paths[key] = guard.executable(route["provider"], route["profile"])
    return provider.build_argv(endpoint, "reviewer" if read_only else "producer", root,
                               read_only=read_only, pin_profile=False, **paths)


def build_context_plan(root: Path, scenario: Mapping[str, Any], route: Mapping[str, Any], mode: str,
                       destination: Path, runtime_manifest: Mapping[str, Any] | None = None) -> dict[str, Any]:
    destination.mkdir(mode=0o700, parents=True, exist_ok=True)
    from .execution_evidence import contract_identity, task_prompt
    prompt = task_prompt(scenario)
    subject_root = destination.parent / "subject"
    mandatory, instruction_records, plan_inputs = _frozen_plan_inputs(root, scenario, route)
    response = contract_identity(scenario)
    if response["required"]:
        instruction_records.append({"id": "evaluation-response-contract", **response})
    settings = {"mode": mode, **plan_inputs["settings"]}
    capture = {
        "settings": settings,
        "provenance": list(route.get("identity_sources", [])),
        "overrides": [dict(value) for value in plan_inputs["overrides"]],
        "apgr_home": str(destination),
        "project_root": str(subject_root),
    }
    argv = _route_argv(root, route, scenario, mode, runtime_manifest)
    projection = None
    if mode == "adaptive" and scenario["scenario_id"] not in {"scenario-05", "scenario-07", "scenario-13"}:
        projection = _ProviderFreeProjection(run_dir=destination / "projection",
                                              scenario_id=scenario["scenario_id"], source_root=root)
        capture["provenance"].append(str(projection.settings_path))
        if scenario["scenario_id"] == "scenario-15":
            argv.extend(["--settings", str(projection.run_dir / "selected/isolated-claude-settings.json"),
                         "--setting-sources", "", "--add-dir", str(projection.run_dir / "selected")])

    def planner(request: Mapping[str, Any], supplied: Mapping[str, Any]) -> dict[str, Any]:
        return _native_frozen_planner(
            request, supplied, mandatory=mandatory,
            facts=plan_inputs["facts"], overrides=plan_inputs["overrides"],
        )

    argv, payload, prepared = context_adapter.prepare(
        capture=capture,
        run_dir=destination,
        prefix="dry",
        run_id=mode,
        binding_id=route["role_binding"]["binding_id"],
        attempt_id="one",
        roles=route["role_binding"]["roles"],
        consumer=route["provider"],
        argv=argv,
        prompt=prompt,
        # The maintained native Go planner is the source of catalog,
        # selection, and content identities.  A dry-run must not substitute a
        # synthetic planner merely to make the record look complete.
        planner=planner if mode == "adaptive" else None,
        projection=projection,
        instruction_records=instruction_records,
    )
    if not prepared.get("reference") or prepared.get("record") is None:
        raise ValueError("context plan was not retained")
    record = prepared["record"]
    fallback_contract = (
        scenario["scenario_id"] in {"scenario-05", "scenario-07", "scenario-13"}
        and mode == "adaptive"
        and record["effective_mode"] == "static"
        and record.get("planned") is True
        and not record.get("acquisition")
    )
    return {
        "status": "complete" if mode == "static" or record["effective_mode"] == "adaptive" or fallback_contract else "incomplete",
        "reason": record.get("reason"),
        "effective_mode": record["effective_mode"],
        "planner": "native" if mode == "adaptive" else "none",
        "argv": argv,
        "payload": {"bytes": len(payload), "sha256": __import__("hashlib").sha256(payload).hexdigest()},
        "response_contract": response,
        "reference": prepared["reference"],
        "record": record,
        "qualification": "provider-free-plumbing-only" if projection is not None else "frozen-fallback-contract",
    }


def _command_binding(scenario: Mapping[str, Any], runtime_manifest: Mapping[str, Any] | None) -> dict[str, Any]:
    oracle = scenario["expected_outcome"]["quality_oracle"]
    command = oracle.get("command") if isinstance(oracle, Mapping) else None
    if not command:
        return {"status": "not_applicable", "command": None}
    parts = shlex.split(command)
    executable = parts[0] if parts else ""
    if runtime_manifest is None:
        return {"status": "unavailable", "command": command, "executable": executable,
                "reason": "complete runtime manifest required"}
    if runtime_manifest.get("schema") != "apg.h-runtime-inputs/v2":
        return {"status": "unavailable", "command": command, "executable": executable,
                "reason": "v2 runtime manifest required"}
    physical = _runtime_executable(runtime_manifest, executable)
    if physical is None:
        return {"status": "unavailable", "command": command, "executable": executable,
                "reason": "frozen command is not bound in runtime manifest"}
    return {"status": "resolved", "command": command, "executable": executable,
            "physical_path": physical,
            "version_stdout": runtime_manifest["runtimes"][executable]["version_stdout"]}


def _exercise_midturn_recovery(root: Path, scenario: Mapping[str, Any],
                               route: Mapping[str, Any], destination: Path) -> dict[str, Any]:
    """Run the frozen failure/recovery shape with a provider-local fake actor."""
    source = root / scenario["withheld_skill"]["canonical_path"]
    if not source.is_file() or source.is_symlink():
        return {"status": "incomplete", "reason": "withheld recovery source unavailable", "provider_invocations": 0}
    try:
        run_dir = destination / "midturn-recovery"
        run_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
        payload = scenario["task_input"]["instruction"].encode()
        source_bytes = direct_bytes(source, utf8=False)
        source_sha = hashlib.sha256(source_bytes).hexdigest()

        class Acquisition:
            def prepare(self, record, run, argv):
                recovery = Path(run) / "recovery" / "SKILL.md"
                recovery.parent.mkdir(mode=0o700)
                recovery.write_bytes(source_bytes)
                recovery.chmod(0o600)
                return argv, {
                    "status": "prelaunch_available",
                    "replay_authorized": False,
                    "recovery": [{
                        "id": scenario["withheld_skill"]["id"],
                        "path": "recovery/SKILL.md",
                        "sha256": source_sha,
                        "bytes": len(source_bytes),
                    }],
                }

            def finalize(self, record):
                return None

        class Projection:
            acquisition = Acquisition()

            def qualification(self):
                return {
                    "selective_projection": True,
                    "independent_recovery": True,
                    "evidence": "provider-free mid-turn fixture",
                }

            def project(self, plan, argv, prompt):
                return argv, plan["payload"].encode()

        capture = {
            "settings": {"mode": "adaptive"},
            "provenance": [],
            "overrides": [],
            "apgr_home": str(run_dir),
            "project_root": str(destination),
        }
        argv = ["fake-claude-profile", "normal-final-review", "--read-only", "-p"]
        argv, prepared_payload, prepared = context_adapter.prepare(
            capture=capture,
            run_dir=run_dir,
            prefix="attempt",
            run_id="adaptive",
            binding_id=route["role_binding"]["binding_id"],
            attempt_id="one",
            roles=route["role_binding"]["roles"],
            consumer="claude",
            argv=argv,
            prompt=payload,
            planner=lambda request, _capture: {
                "effective_mode": "adaptive",
                "reasons": ["provider-free-midturn"],
                "payload": request["mandatory"][0]["text"],
                "catalog_fingerprint": "provider-free",
                "rule_version": "provider-free",
                "content_identity": "provider-free",
            },
            projection=Projection(),
        )
        if prepared["record"]["effective_mode"] != "adaptive":
            raise ValueError("adaptive recovery plan did not remain adaptive")
        seen = {}

        def fake_provider():
            transport = context_adapter.ACTIVE_TRANSPORT.get()
            if transport is None:
                raise ValueError("controlled transport was not selected")
            transport.process_started(argv)
            transport.wrote_stdin(prepared_payload)
            recovery = prepared["record"]["acquisition"]["recovery"][0]
            path = run_dir / recovery["path"]
            observed = direct_bytes(path, utf8=False)
            if hashlib.sha256(observed).hexdigest() != recovery["sha256"] or observed != source_bytes:
                raise ValueError("recovery snapshot identity changed")
            seen.update({
                "recovered": True,
                "path": recovery["path"],
                "sha256": hashlib.sha256(observed).hexdigest(),
                "allowed_tools": ["view_file"],
                "replay_authorized": False,
            })
            return SimpleNamespace(exit_code=0, stdout=b"fake-recovery-complete", stderr=b"", truncated=False)

        context_adapter.invoke(prepared, fake_provider)
        trace = load(run_dir / "attempt.context-deliveries.json")
        if trace.get("coverage") != "complete" or not seen.get("recovered"):
            raise ValueError("mid-turn recovery transport evidence incomplete")
        return {
            "status": "complete",
            "provider_invocations": 0,
            "fake_provider_invocations": 1,
            "recovered": True,
            "recovery_sha256": seen["sha256"],
            "bash_tool_granted": False,
            "replay_authorized": False,
        }
    except Exception as error:  # noqa: BLE001 - retain failed qualification evidence
        return {"status": "incomplete", "provider_invocations": 0,
                "reason": f"{type(error).__name__}: {error}"}


def _exercise_prelaunch_fallback(root: Path, scenario: Mapping[str, Any],
                                route: Mapping[str, Any], destination: Path) -> dict[str, Any]:
    """Prove adaptive preparation falls back before any MCP/provider launch."""
    try:
        run_dir = destination / "prelaunch-fallback"
        run_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
        prompt = scenario["task_input"]["instruction"].encode()
        _, _, prepared = context_adapter.prepare(
            capture={
                "settings": {"mode": "adaptive"},
                "provenance": [],
                "overrides": [],
                "apgr_home": str(run_dir),
                "project_root": str(destination),
            },
            run_dir=run_dir,
            prefix="fallback",
            run_id="adaptive",
            binding_id=route["role_binding"]["binding_id"],
            attempt_id="one",
            roles=route["role_binding"]["roles"],
            consumer="claude",
            argv=["fake-claude-profile", "normal-final-review", "--read-only", "-p"],
            prompt=prompt,
            # Exercise the maintained planner's no-projection fallback.  The
            # provider-free check must not manufacture a plan identity.
            planner=(lambda request, supplied: _native_frozen_planner(
                request, supplied, mandatory=[], facts=[], overrides=[])) if ACTIVE_RUNTIME.get() else None,
            projection=None,
        )
        record = prepared["record"]
        if record["effective_mode"] != "static" or not record.get("planned"):
            raise ValueError("MCP-unavailable adaptive request did not choose static fallback")
        if (run_dir / "acquisitions").exists() or record.get("acquisition"):
            raise ValueError("fallback created an MCP acquisition")
        return {
            "status": "complete",
            "provider_invocations": 0,
            "mcp_invocations": 0,
            "effective_mode": "static",
            "fallback_reason": record["reason"],
        }
    except Exception as error:  # noqa: BLE001 - retain failed qualification evidence
        return {"status": "incomplete", "provider_invocations": 0,
                "reason": f"{type(error).__name__}: {error}"}


def _exercise_projection(root: Path, scenario: Mapping[str, Any],
                         route: Mapping[str, Any], destination: Path) -> dict[str, Any]:
    """Preflight Scenario 15 without inventing a projection qualification.

    The native planner is exercised against an isolated run-owned settings
    path.  The repository currently has no source-owned selective projection
    adapter, so the record remains incomplete even though the provider and
    model are never invoked.
    """
    try:
        run_dir = destination / "isolated-projection"
        plan = build_context_plan(root, scenario, route, "adaptive", run_dir / "plan")
        settings = run_dir / "plan" / "projection" / "provider-free-settings.json"
        if plan["status"] != "complete" or plan["effective_mode"] != "adaptive" or not settings.is_file():
            raise ValueError("provider-free selective projection plan incomplete")
        from .projection_qualification import verify
        selected = settings.parent / "selected"
        projection_receipt = load(selected / "projection-receipt.json")
        projection_custody = verify(selected, projection_receipt)
        return {
            "status": "complete",
            "provider_invocations": 0,
            "effective_mode": plan["effective_mode"],
            "qualification": "provider-free-plumbing-only",
            "plan_reference": plan["reference"],
            "settings_sha256": hashlib.sha256(settings.read_bytes()).hexdigest(),
            "projection_custody": projection_custody,
            "projected_skills_dir": str(settings.parent),
            "live_qualification": "contingent/unavailable",
        }
    except Exception as error:  # noqa: BLE001 - retain failed qualification evidence
        return {"status": "incomplete", "provider_invocations": 0,
                "reason": f"{type(error).__name__}: {error}",
                "live_qualification": "contingent/unavailable"}


def _scenario_special(root: Path, scenario: Mapping[str, Any], route: Mapping[str, Any],
                      destination: Path) -> dict[str, Any]:
    sid = scenario["scenario_id"]
    result: dict[str, Any] = {}
    if sid == "scenario-12":
        result["midturn_recovery"] = _exercise_midturn_recovery(root, scenario, route, destination)
        transaction = ACTIVE_RUNTIME.get()
        if transaction is None:
            result["recovery_subtree"] = {"status": "incomplete", "reason": "sealed runtime required"}
        else:
            from .recovery_qualification import qualify_recovery
            try:
                result["recovery_subtree"] = qualify_recovery(
                    root, destination / "recovery-subtree", apgr_executable=transaction.resolve("apgr"),
                    environment=transaction.environment(cwd=destination))
            except (ValueError, OSError) as error:
                result["recovery_subtree"] = {"status": "incomplete", "reason": str(error)}
    if sid == "scenario-13":
        result["prelaunch_fallback"] = _exercise_prelaunch_fallback(root, scenario, route, destination)
    if sid == "scenario-15":
        result["selective_projection"] = _exercise_projection(root, scenario, route, destination)
    return result


def _dry_run_all(
    root: str | Path,
    output: str | Path | None = None,
    *,
    subject_factory: Any = None,
    oracle_owner: Any = None,
    runtime_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the complete provider-free package preflight for all 15 scenarios."""
    root = Path(root)
    bindings = verify_bindings(root)
    subject_factory = _load_subject_factory(subject_factory)
    oracle_owner = _load_oracle_owner(oracle_owner)
    output_path = Path(output) if output is not None else None
    if output_path is not None:
        if output_path.resolve() != output_path or output_path.exists():
            raise ValueError("dry-run output must be a new physical directory")
        output_path.mkdir(mode=0o700)
    scratch = Path(tempfile.mkdtemp(prefix="apg166e-dry-run-")) if output_path is None else None
    runtime_status: dict[str, Any]
    if runtime_manifest is None:
        runtime_status = {"status": "unavailable", "reason": "complete v2 runtime manifest required"}
    else:
        try:
            from . import runtime_manifest as runtime_owner
            runtime_owner.verify(runtime_manifest, probe_versions=False)
            runtime_status = {"status": "resolved", "schema": runtime_manifest.get("schema")}
        except Exception as error:  # noqa: BLE001 - retain failed qualification evidence
            runtime_status = {"status": "unavailable", "reason": f"{type(error).__name__}: {error}"}
    records: list[dict[str, Any]] = []
    total_invocations = 0
    for row in bindings["scenarios"]:
        scenario = load(root / row["scenario_path"])
        scenario_dir = (output_path / row["scenario_id"]) if output_path is not None else None
        if scenario_dir is not None:
            scenario_dir.mkdir(mode=0o700)
        record: dict[str, Any] = {
            "schema": SCHEMA,
            "phase": "APG166E",
            "scenario_id": row["scenario_id"],
            "provider_invocations": 0,
            "status": "complete",
            "blockers": [],
            "subjects": {},
            "subject_directories": {},
            "routes": {},
            "context_plans": {},
            "importer": {},
            "oracle": {},
            "command": _command_binding(scenario, runtime_manifest),
            "special": {},
        }
        record["runtime"] = dict(runtime_status)
        if runtime_status["status"] != "resolved":
            record["status"] = "incomplete"
            record["blockers"].append("complete runtime manifest unavailable")
        for mode in MODES:
            try:
                target = (scenario_dir / mode) if scenario_dir is not None else scratch / row["scenario_id"] / mode
                target.mkdir(mode=0o700, parents=True, exist_ok=True)
                subject = target / "subject"
                record["subjects"][mode] = materialize_subject(subject_factory, root=root, scenario=scenario, destination=subject, mode=mode)
                record["subject_directories"][mode] = sorted(
                    str(path.relative_to(subject)) for path in subject.rglob("*") if path.is_dir())
                route = row["routes"][mode]
                provider_runtime = _provider_binding(runtime_manifest, route["provider"])
                record["routes"][mode] = {
                    "provider": route["provider"],
                    "profile": route["profile"],
                    "model": route["model"],
                    "argv": _route_argv(root, route, scenario, mode, runtime_manifest),
                    "provider_invocations": 0,
                    "runtime": provider_runtime,
                }
                if provider_runtime["status"] != "resolved":
                    record["status"] = "incomplete"
                    record["blockers"].append(f"{mode}: provider runtime unavailable")
                _verify_frozen_subject_inputs(root, scenario, subject)
                record["context_plans"][mode] = build_context_plan(
                    root, scenario, route, mode, target / "plan", runtime_manifest
                )
                if record["context_plans"][mode]["status"] != "complete":
                    record["status"] = "incomplete"
                    record["blockers"].append(
                        f"{mode}: native context plan incomplete ({record['context_plans'][mode].get('reason')})"
                    )
            except Exception as error:  # noqa: BLE001 - retain failed qualification evidence
                record["status"] = "incomplete"
                record["blockers"].append(f"{mode}: {type(error).__name__}: {error}")
        pair = record["subjects"]
        record["initial_trees_equal"] = (
            set(pair) == set(MODES) and pair["static"]["files"] == pair["adaptive"]["files"]
            and record["subject_directories"].get("static") == record["subject_directories"].get("adaptive")
        )
        if not record["initial_trees_equal"]:
            record["status"] = "incomplete"
            record["blockers"].append("static/adaptive initial subjects differ or are unavailable")
        special_root = (scenario_dir / "special") if scenario_dir is not None else scratch / row["scenario_id"] / "special"
        special_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        record["special"] = _scenario_special(root, scenario, row["routes"]["adaptive"], special_root)
        try:
            record["importer"] = importers.qualify_importer(
                row["routes"]["static"]["provider"], row["scenario_id"])
            if record["importer"]["status"] != "complete":
                record["status"] = "incomplete"
                record["blockers"].append("provider importer contract incomplete")
        except Exception as error:  # noqa: BLE001 - retain failed qualification evidence
            record["status"] = "incomplete"
            record["importer"] = {"status": "unavailable", "reason": str(error)}
            record["blockers"].append("provider importer unavailable")
        try:
            oracle = _oracle_target(oracle_owner, scenario)
            record["oracle"] = {
                "status": "resolved" if oracle is not None else "unavailable",
                "fixture_exercise": exercise_oracle(oracle_owner, oracle, root=root, scenario=scenario,
                    runtime_manifest=runtime_manifest, fixture_root=special_root.parent / "oracle-fixtures") if oracle is not None else {"status": "incomplete", "reason": "oracle owner returned no oracle"},
            }
            if record["oracle"]["status"] != "resolved" or record["oracle"]["fixture_exercise"]["status"] != "complete":
                record["status"] = "incomplete"
                record["blockers"].append("substantive oracle fixture exercise incomplete")
        except Exception as error:  # noqa: BLE001 - retain failed qualification evidence
            record["status"] = "incomplete"
            record["oracle"] = {"status": "unavailable", "reason": str(error)}
            record["blockers"].append("substantive oracle unavailable")
        record["command"] = _command_binding(scenario, runtime_manifest)
        if record["command"]["status"] == "unavailable":
            record["status"] = "incomplete"
            record["blockers"].append("frozen oracle command unavailable")
        for name, special in record["special"].items():
            if special.get("status") != "complete":
                record["status"] = "incomplete"
                record["blockers"].append(f"{name} plumbing incomplete")
        # Planning and oracle-fixture qualification must never mutate either
        # model-visible subject, even for a later writable task.
        record["subject_authority"] = {}
        for mode in MODES:
            target = (scenario_dir / mode) if scenario_dir is not None else scratch / row["scenario_id"] / mode
            try:
                unchanged = (execution.snapshot_tree(target / "subject") == pair[mode]["files"]
                    and sorted(str(path.relative_to(target / "subject"))
                        for path in (target / "subject").rglob("*") if path.is_dir())
                    == record["subject_directories"][mode])
            except (OSError, ValueError, KeyError):
                unchanged = False
            record["subject_authority"][mode] = {"unchanged": unchanged}
            if not unchanged:
                record["status"] = "incomplete"
                record["blockers"].append(f"{mode}: dry-run subject authority changed or unavailable")
        from .provider_free import ACTIVE_GUARD
        record["provider_guard"] = ACTIVE_GUARD.get().assert_clean()
        total_invocations += record["provider_invocations"]
        records.append(record)
        if scenario_dir is not None:
            _write_new(scenario_dir / "dry-run.json", record)
    result = {
        "schema": SCHEMA,
        "phase": "APG166E",
        "records": records,
        "scenario_count": len(records),
        "complete_records": sum(row["status"] == "complete" for row in records),
        "initial_trees_equal": sum(row["initial_trees_equal"] for row in records),
        "subject_pairs_unchanged": sum(all(row["subject_authority"][mode]["unchanged"]
                                          for mode in MODES) for row in records),
        "provider_invocations": total_invocations,
        "all_subjects_complete": len(records) == 15 and all(
            row["subjects"].keys() == set(MODES) and all(row["subjects"][mode].get("files") for mode in MODES)
            for row in records
        ),
        "runtime": runtime_status,
        "aggregate_written": False,
    }
    if scratch is not None:
        shutil.rmtree(scratch, ignore_errors=True)
    return result


def dry_run_all(root, output=None, *, subject_factory=None, oracle_owner=None,
                runtime_manifest=None):
    """Retain tripwire custody even when a provider-free transaction fails."""
    from .provider_free import LaunchGuard
    if runtime_manifest is not None and (subject_factory is not None or oracle_owner is not None):
        raise ValueError("qualified dry-run requires repository-owned subjects and oracles")
    if output is None:
        raise ValueError("durable private output required for provider-free qualification")
    output = Path(output)
    if output.resolve() != output or output.exists() or output.is_symlink():
        raise ValueError("dry-run output must be a new physical directory")
    # Keep failed launch evidence beside the immutable scenario records. The
    # nested records owner must never clean the guard after an exception.
    output.mkdir(mode=0o700)
    with LaunchGuard(output / "provider-guard") as guard:
        for row in verify_bindings(Path(root))["scenarios"]:
            for route in row["routes"].values():
                guard.executable(route["provider"], route["profile"])
        from .provider_free_readiness import retain_integrity
        from .readiness import make_seal, source_identity
        source = source_identity(make_seal(root)["files"])
        transaction = None
        if runtime_manifest is not None:
            from .runtime_execution import begin
            transaction = begin(runtime_manifest, work_dir=output)
            _write_new(output / "runtime-manifest.json", runtime_manifest)
        token = ACTIVE_RUNTIME.set(transaction)
        try:
            result = _dry_run_all(root, output / "records", subject_factory=subject_factory,
                                  oracle_owner=oracle_owner, runtime_manifest=runtime_manifest)
            if transaction is not None:
                from .preregistration import qualify_promotion_oracles
                result["promotion_oracle_fixtures"] = qualify_promotion_oracles(
                    root, runtime_manifest, output / "promotion-oracle-fixtures")
                guard.assert_clean()
                transaction.close(probe_versions=True)
        finally:
            ACTIVE_RUNTIME.reset(token)
            if transaction is not None and transaction._active:
                transaction.close()
        if source_identity(make_seal(root)["files"]) != source:
            raise ValueError("provider-free source changed during qualification")
        result["source_identity"] = source
        result["runtime_transaction"] = {"status": "valid" if transaction is not None else "unavailable"}
        if transaction is not None:
            from .runtime_manifest import manifest_digest
            result["runtime_transaction"].update(
                manifest_sha256=manifest_digest(runtime_manifest), before="valid", after="valid",
                lifetime="one provider-free qualification transaction",
                later_transaction="revalidate and recapture on any mutable input drift")
        result["provider_guard"] = guard.assert_clean()
        _write_new(output / "dry-run.json", result)
        retain_integrity(output)
    return result


provider_free_dry_run = dry_run_all
run_all = dry_run_all


__all__ = [
    "SCHEMA",
    "build_context_plan",
    "dry_run_all",
    "exercise_oracle",
    "materialize_subject",
    "provider_free_dry_run",
    "run_all",
]
