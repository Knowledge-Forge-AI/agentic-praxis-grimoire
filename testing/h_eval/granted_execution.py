"""Thin granted callers for live H pairs and promotion cases.

These callers add no orchestration authority of their own.  Every provider
start is admitted and consumed by ``live_admission`` first; scenario arms use
the existing ``execution.construct_arm`` owner, and promotion cases reuse its
runtime, git, provider-runner and importer seams.  Nothing here retries,
resumes, selects an alternate identity or writes a maturity ledger.
"""
from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable, Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

from agent_phase import provider
from agent_phase.transmission import direct_bytes

from . import dry_run, execution, importers, live_admission
from .evaluate import load

PAIR_SCHEMA = "apg.h-granted-pair/v1"
CASE_SCHEMA = "apg.h-promotion-case-result/v1"
CASE_INTEGRITY_SCHEMA = "apg.h-promotion-case-integrity/v1"
PROMOTION_ENDPOINT = ("codex", "implementation-testing")
_RESULT = "result.json"
_INTEGRITY = "integrity.json"
_DELIVERY_ROOT = ".agents/skills"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _new_directory(path: Path) -> Path:
    path = Path(path)
    if not path.is_absolute() or path.parent.resolve() != path.parent:
        raise ValueError("granted output parent must be physical")
    path.mkdir(mode=0o700)
    return path


def _failed_arm_explanation(arm_dir: Path) -> dict[str, Any]:
    """Keep the primary failed-arm explanation beside a strict readback refusal.

    The integrity-checked diagnostic reader never qualifies the arm; its
    failure is recorded rather than allowed to replace the refusal.
    """
    try:
        diagnostic = execution.read_arm_diagnostic(arm_dir)
    except Exception as error:  # noqa: BLE001 - the strict refusal stays primary
        return {"status": "unavailable", "error": f"{type(error).__name__}: {error}"}
    outcome = diagnostic["outcome"]
    return {
        "status": "retained",
        "schema": diagnostic["schema"],
        "qualification": diagnostic["qualification"],
        "failure": outcome["failure"],
        "failure_detail": outcome["failure_detail"],
        "provider_invocations": outcome["provider_invocations"],
        "provider_terminal": outcome["provider_terminal"],
        "raw_streams": diagnostic["raw_streams"],
        "postrun_checks": diagnostic["postrun_checks"],
        "runtime_post_run": diagnostic["runtime_post_run"],
        "missing_evidence": diagnostic["missing_evidence"],
        "current_runtime": diagnostic["current_runtime"],
    }


def run_granted_pair(
    *,
    pair_dir: str | Path,
    source_root: str | Path,
    scenario_id: str,
    live_authorization: Mapping[str, Any],
    runtime_inputs: Mapping[str, Any],
    liveness_policy: Any = None,
) -> dict[str, Any]:
    """Run static then adaptive once each, reading every arm back immediately.

    The adaptive arm is not started when the static arm was refused, did not
    complete, or cannot be read back; its unit remains visibly unconsumed.
    """
    source_root = Path(source_root)
    pair_dir = _new_directory(Path(pair_dir))
    record: dict[str, Any] = {
        "schema": PAIR_SCHEMA, "scenario_id": scenario_id, "arms": {},
        "retries": 0, "replay_authorized": False, "stopped": None,
    }
    for mode in ("static", "adaptive"):
        arm_dir = pair_dir / mode
        try:
            execution.construct_arm(
                arm_dir=arm_dir, source_root=source_root, scenario_id=scenario_id, mode=mode,
                execution="live", runtime_inputs=runtime_inputs,
                live_authorization=live_authorization, liveness_policy=liveness_policy,
            )
        except (OSError, TypeError, ValueError) as error:
            record["arms"][mode] = {"status": "refused", "error": f"{type(error).__name__}: {error}",
                                    "arm_exists": arm_dir.exists()}
            record["stopped"] = f"{mode} arm refused before a provider start"
            break
        try:
            readback = execution.read_arm_result(arm_dir)
        except (OSError, TypeError, ValueError) as error:
            record["arms"][mode] = {"status": "readback-invalid", "error": f"{type(error).__name__}: {error}",
                                    "diagnostic": _failed_arm_explanation(arm_dir)}
            record["stopped"] = f"{mode} arm readback is missing or invalid"
            break
        record["arms"][mode] = {
            "status": readback.get("status"),
            "failure": readback.get("failure"),
            # Additive bounded step/reason; absent (None) for historical arms.
            "failure_detail": deepcopy(readback.get("failure_detail")),
            "postrun_checks": deepcopy(readback.get("postrun_checks")),
            "provider_invocations": readback.get("provider_invocations"),
            "live_admission": deepcopy(readback.get("live_admission")),
            "subject_factory": deepcopy((readback.get("construction") or {}).get("subject_factory")),
        }
        if readback.get("status") != "complete":
            record["stopped"] = f"{mode} arm did not complete; no automatic continuation"
            break
    static, adaptive = record["arms"].get("static"), record["arms"].get("adaptive")
    if static and adaptive and static.get("live_admission") and adaptive.get("live_admission"):
        left, right = static["live_admission"], adaptive["live_admission"]
        record["same_source"] = (left["source_identity"] == right["source_identity"]
                                 and left["decision_sha256"] == right["decision_sha256"]
                                 and static["subject_factory"] == adaptive["subject_factory"])
        if not record["same_source"]:
            record["stopped"] = "paired arms do not share source, decision and subject factory"
    execution._write_json(pair_dir / "pair.json", record)
    return record


def _promotion_case(root: Path, case_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    from .preregistration import verify_promotions
    for skill in verify_promotions(root)["skills"]:
        for case in skill["cases"]:
            if case["case_id"] == case_id:
                return skill, case
    raise ValueError(f"promotion case is not preregistered: {case_id}")


def _verified_route(root: Path, case: Mapping[str, Any]) -> dict[str, Any]:
    route = case.get("route")
    if (not isinstance(route, Mapping) or (route.get("provider"), route.get("profile")) != PROMOTION_ENDPOINT
            or route.get("role") != "Producer"):
        raise ValueError("promotion case route is not the preregistered Codex producer route")
    source = root / str(route.get("model_source"))
    if source.resolve() != source or _sha256(source.read_bytes()) != route.get("model_source_sha256"):
        raise ValueError("promotion case model source changed")
    return dict(route)


def _delivered_skill(root: Path, skill: Mapping[str, Any]) -> tuple[str, bytes]:
    path = root / skill["source_path"]
    data = direct_bytes(path, utf8=False, max_bytes=execution.MAX_BYTES)
    if _sha256(data) != skill["whole_sha256"]:
        raise ValueError("preregistered skill body changed")
    return f"{_DELIVERY_ROOT}/{skill['skill_id']}/SKILL.md", data


def _guidance_argv(root: Path, argv: list[str]) -> list[str]:
    """Add frozen source guidance without operator skill-disable policy."""
    from agent_source_guidance import source_guidance
    guidance = source_guidance(
        root / "codex", [], workers=False, instruction_file="AGENTS.md",
        provider="codex", provider_mode="instructions", executable="rtk",
    )
    if guidance.prompt:
        argv[-1:-1] = ["-c", "developer_instructions=" + json.dumps(guidance.prompt, ensure_ascii=False)]
    if any(part.startswith("skills.config") for part in argv):
        raise ValueError("promotion delivery cannot be disabled by skill configuration")
    return argv


def _graded_copy(subject: Path, graded: Path) -> dict[str, dict[str, Any]]:
    """Copy model output bytes, excluding git metadata and the delivered skill."""
    graded.mkdir(mode=0o700)
    inventory = {}
    for name, item in execution.snapshot_tree(subject).items():
        if name == _DELIVERY_ROOT or name.startswith(_DELIVERY_ROOT + "/"):
            continue
        target = graded / name
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        execution._write_bytes(target, direct_bytes(subject / name, utf8=False, max_bytes=execution.MAX_BYTES))
        os.chmod(target, item["mode"], follow_symlinks=False)
        inventory[name] = item
    return inventory


def _persist_case(case_dir: Path, result: dict[str, Any]) -> dict[str, Any]:
    execution._write_json(case_dir / _RESULT, result)
    files = execution.snapshot_tree(case_dir)
    execution._write_json(case_dir / _INTEGRITY, {
        "schema": CASE_INTEGRITY_SCHEMA,
        "files": files,
        "directories": execution.snapshot_dirs(case_dir),
        "result_sha256": files[_RESULT]["sha256"],
    })
    return result


def run_promotion_case(
    *,
    case_dir: str | Path,
    source_root: str | Path,
    case_id: str,
    live_authorization: Mapping[str, Any],
    runtime_inputs: Mapping[str, Any],
    liveness_policy: Any = None,
    _runner_factory: Callable[[Mapping[str, str]], Callable[..., Any]] | None = None,
) -> dict[str, Any]:
    """Run one preregistered promotion case with at most one provider start.

    ``_runner_factory`` is a test seam that replaces only the manifest-bound
    provider runner; admission, consumption, subject, delivery, grading and
    retention remain the maintained path.
    """
    from . import runtime_manifest
    from . import promotion_oracles

    source_root, case_dir = Path(source_root), Path(case_dir)
    if source_root.resolve() != source_root or case_dir.parent.resolve() != case_dir.parent:
        raise ValueError("promotion case and source roots must be physical")
    if case_dir.exists() or case_dir.is_symlink():
        raise ValueError("promotion case directory already exists; replay refused")
    live_admission.check_shape(live_authorization)
    skill, case = _promotion_case(source_root, case_id)
    route = _verified_route(source_root, case)
    delivery_path, delivery_bytes = _delivered_skill(source_root, skill)
    admission = live_admission.admit(
        source_root, live_authorization, live_admission.promotion_unit(case_id),
        runtime_inputs=runtime_inputs,
    )
    runtime_manifest.verify(runtime_inputs, probe_versions=True)
    global_root = execution._global_discovery_candidate(runtime_inputs, "codex")
    if global_root.exists() or global_root.is_symlink():
        raise ValueError("operator global Codex skill discovery must be absent for promotion cases")
    codex = runtime_manifest.resolve_executable(runtime_inputs, "codex")
    receipt = live_admission.consume(admission)

    _new_directory(case_dir)
    run, subject = case_dir / "run", case_dir / "subject"
    run.mkdir(mode=0o700)
    subject.mkdir(mode=0o700)
    result: dict[str, Any] = {
        "schema": CASE_SCHEMA, "case_id": case_id, "skill_id": skill["skill_id"],
        "kind": case["kind"], "case_sha256": case["case_sha256"], "route": route,
        "status": "incomplete", "provider_invocations": 0, "retries": 0, "restarts": 0,
        "replay_authorized": False, "live_admission": deepcopy(receipt),
        "attribution_status": "pending-independent-review",
        "promotion_authorized": False, "maturity_ledger_written": False,
        "oracle_is_not_promotion": True,
    }
    transaction = token = None
    owned = closed = False
    returned = None
    try:
        transaction, token, owned = execution._acquire_runtime_transaction(runtime_inputs, work_dir=run)
        execution._materialize(subject, {**case["subject_files"], delivery_path: delivery_bytes})
        git, git_environment, git_source = execution._prepare_subject_repository(
            subject, None, runtime_inputs=runtime_inputs,
        )
        before = execution.snapshot_tree(subject)
        git_before = execution._git_authority(subject, git, environment=git_environment,
                                               environment_source=git_source)
        result["subject_before"] = before
        result["git_authority_before"] = git_before
        result["delivery"] = {
            "schema": "apg.h-promotion-delivery/v1",
            "mechanism": "repository-scoped Codex skill directory in the case subject",
            "path": delivery_path,
            "bytes": len(delivery_bytes),
            "sha256": _sha256(delivery_bytes),
            "preregistered_whole_sha256": skill["whole_sha256"],
            "global_discovery_root": str(global_root),
            "global_discovery_absent": True,
            "use_evidence": "delivery only; guidance use requires later independent attribution review",
        }
        argv = provider.build_argv(
            provider.Endpoint(*PROMOTION_ENDPOINT), "producer", source_root,
            codex_executable=codex, read_only=False, pin_profile=True,
        )
        argv = _guidance_argv(source_root, argv)
        prompt = str(case["prompt"]).encode()
        environment = execution._manifest_environment(runtime_inputs, cwd=subject)
        runner = (_runner_factory or execution._bound_provider_runner)(environment)
        execution._write_json(run / "started.json", {
            "attempt_id": "one", "replay_authorized": False, "argv": argv,
            "prompt_sha256": _sha256(prompt), "environment_keys": sorted(environment),
        })
        result["provider_invocations"] = 1
        returned = execution._normalize_returned(runner(argv, prompt, subject, liveness_policy=liveness_policy))
        terminal = execution._terminal(returned)
        execution._write_bytes(run / "provider.stdout", returned.stdout)
        execution._write_bytes(run / "provider.stderr", returned.stderr)
        result["provider_terminal"] = terminal
        checked = transaction.revalidate(probe_versions=True)
        result["runtime_revalidation"] = {
            "status": "valid", "post_run": "valid",
            "manifest_sha256": runtime_manifest.manifest_digest(checked),
            "transaction": "owned" if owned else "borrowed",
        }
        if owned:
            transaction.close(probe_versions=True)
            dry_run.ACTIVE_RUNTIME.reset(token)
        closed = True
        live_admission.verify_current(admission, source_root, runtime_inputs)
        imported = importers.importer_for("codex")(returned.stdout, {**route, "execution": "live"},
                                                   terminal=terminal)
        result["provider_import"] = dict(imported)
        after = execution.snapshot_tree(subject)
        delivered_after = after.get(delivery_path)
        result["delivery"]["unchanged_after_run"] = (
            delivered_after is not None and delivered_after["sha256"] == _sha256(delivery_bytes))
        result["delivery"]["global_discovery_absent_after_run"] = not (global_root.exists() or global_root.is_symlink())
        result["subject_after"] = after
        result["changed_paths"] = sorted(n for n in before.keys() | after.keys() if before.get(n) != after.get(n))
        result["git_authority_after"] = execution._git_authority(
            subject, git, environment=git_environment, environment_source=git_source)
        result["transcript"] = {"stdout": terminal["stdout"], "stderr": terminal["stderr"]}
        if terminal["exit_code"] != 0 or terminal["truncated"]:
            raise ValueError("provider transport did not complete")
        graded = case_dir / "graded"
        result["graded_inventory"] = _graded_copy(subject, graded)
        paths = promotion_oracles.executable_paths_for_value(runtime_inputs)
        oracle = promotion_oracles.evaluate_subject_directory(case_id, graded, paths)
        result["oracle"] = oracle
        result["status"] = "complete"
    except BaseException as error:
        result["failure"] = f"{type(error).__name__}: {error}"
        if transaction is not None and not closed:
            try:
                if owned:
                    transaction.close(probe_versions=True)
            except (OSError, TypeError, ValueError):
                pass
            finally:
                if owned and token is not None:
                    dry_run.ACTIVE_RUNTIME.reset(token)
        if returned is not None and "provider_terminal" not in result:
            try:
                result["provider_terminal"] = execution._terminal(returned)
            except (TypeError, ValueError):
                pass
        _persist_case(case_dir, result)
        if isinstance(error, (KeyboardInterrupt, SystemExit)):
            raise
        return result
    return _persist_case(case_dir, result)


def read_case_result(case_dir: str | Path) -> dict[str, Any]:
    """Read one retained promotion case without starting or retrying a provider."""
    case_dir = Path(case_dir)
    if case_dir.resolve() != case_dir or not case_dir.is_dir():
        raise ValueError("promotion case directory must be physical")
    integrity = load(case_dir / _INTEGRITY)
    result = load(case_dir / _RESULT)
    if (integrity.get("schema") != CASE_INTEGRITY_SCHEMA
            or integrity.get("result_sha256") != _sha256((case_dir / _RESULT).read_bytes())):
        raise ValueError("promotion case result identity changed")
    actual = execution.snapshot_tree(case_dir)
    actual.pop(_INTEGRITY, None)
    if actual != integrity.get("files") or execution.snapshot_dirs(case_dir) != integrity.get("directories"):
        raise ValueError("promotion case evidence changed or lost")
    if result.get("schema") != CASE_SCHEMA:
        raise ValueError("promotion case result schema is invalid")
    live_admission.verify_receipt(result.get("live_admission"),
                                  unit=live_admission.promotion_unit(result.get("case_id", "")))
    if (result.get("promotion_authorized") is not False or result.get("maturity_ledger_written") is not False
            or result.get("attribution_status") != "pending-independent-review"):
        raise ValueError("promotion case result claims promotion authority")
    if type(result.get("provider_invocations")) is not int or result["provider_invocations"] not in (0, 1):
        raise ValueError("promotion case invocation accounting is invalid")
    if result.get("retries") != 0 or result.get("restarts") != 0:
        raise ValueError("promotion case retry accounting is invalid")
    return result


__all__ = ["read_case_result", "run_granted_pair", "run_promotion_case"]
