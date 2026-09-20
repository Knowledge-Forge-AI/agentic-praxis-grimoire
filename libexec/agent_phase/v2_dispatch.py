"""Dispatcher runtime engine for Request V2 invocations.

Integrates SQLite persistence, turn-by-turn pre-launch route selection,
multi-turn semantic role execution, operational finalization, outbox
projection, and complete terminal artifact sealing.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any
import zipfile

from . import candidate, gitstate as gitstate_module, finalization as finalization_module
from .capabilities import load_capabilities
from .display import Display
from .dynamic_router import (
    NoRouteAvailableError,
    OperationalObservation,
)
from .finalization import FinalizationError
from .lifecycle import (
    FINALIZATION_CHECKPOINT,
    FINALIZATION_COMMIT_LOCAL,
    FINALIZATION_PUBLISH,
    LIFECYCLE_STANDARD,
    get_lifecycle,
    validate_finalization,
)
from .outbox_projection import (
    build_locator_payload,
    project_v2_run,
    resolve_outbox_root,
)
from .persistence import (
    get_run,
    open_dispatcher_db,
    record_actor_bindings,
    record_artifact,
    record_configuration_provenance,
    record_operational_observation,
    record_resume_relation,
    record_run,
    record_semantic_responsibility,
    resolve_dispatcher_db_path,
    update_run_status,
)
from .probes import collect_operational_observations
from .publication import PublicationError
from .request import PhaseRequestV2
from .roster import load_roster
from .run import (
    RunPathError,
    phase_id_from_request,
    project_name,
    run_timestamp,
    safe_component,
    v2_leaf,
)
from .semantic_roles import (
    ActorBindingPolicy,
    create_default_binding_policy,
)
from .v2_turns import PreLaunchFailureError, execute_v2_turns


class V2DispatchError(RuntimeError):
    """Raised when Request V2 dispatch fails."""


class _RunDirectoryAdapter:
    def __init__(self, path: Path) -> None:
        self.path = path

    def write_bytes(self, name: str, data: bytes) -> Path:
        target = self.path / name
        temporary = self.path / f".{name}.tmp"
        with open(temporary, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        return target

    def write_text(self, name: str, text: str) -> Path:
        return self.write_bytes(name, text.encode("utf-8"))

    def write_json(self, name: str, payload: Any) -> Path:
        return self.write_bytes(name, (json.dumps(payload, indent=2) + "\n").encode("utf-8"))


def run_id_for_v2(phase_type: str) -> str:
    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    rand_hex = os.urandom(4).hex()
    return f"apgr-run-v2-{phase_type}-{timestamp}-{rand_hex}"


def dispatch_v2(
    repository_root: Path,
    work_tree: Path,
    request: PhaseRequestV2,
    raw_request: bytes,
    *,
    execution_mode: str = "dynamic",
    provenance: Mapping[str, Any] | None = None,
    provenance_chain: Sequence[Mapping[str, Any]] | None = None,
    apgr_home: Path | None = None,
    outbox_root: Path | str | None = None,
    lifecycle: str = LIFECYCLE_STANDARD,
    finalization_policy: str = FINALIZATION_PUBLISH,
    dry_run: bool = False,
    display: Display | None = None,
    operational_observations: Sequence[OperationalObservation] = (),
    injected_observations: Sequence[OperationalObservation] | None = None,
    runner: Callable[..., Any] | None = None,
    attempt_number: int = 1,
    run_id: str | None = None,
    resume_from_run_id: str | None = None,
    binding_policy: ActorBindingPolicy | None = None,
    request_path: Path | None = None,
    phase_id: str | None = None,
    continue_from: str | None = None,
    entry_adoption: str | None = None,
    native_git_authority: str | None = None,
    now: float | None = None,
) -> dict[str, Any]:
    """Execute or dry-run a Request V2 single-phase dispatch with SQLite persistence."""
    candidate.require_worktree(work_tree)
    spec = get_lifecycle(lifecycle)
    valid_finalization_policy = validate_finalization(finalization_policy)
    load_roster(repository_root)
    caps_catalog = load_capabilities(repository_root)
    policy = binding_policy or create_default_binding_policy()

    repo_root = gitstate_module.repository_root(work_tree)
    project = project_name(repo_root)
    if phase_id is not None:
        effective_phase_id = safe_component(phase_id, "phase id")
    elif request_path is not None:
        effective_phase_id = phase_id_from_request(Path(request_path))
    else:
        effective_phase_id = safe_component(request.phase_type, "phase id")

    entry = gitstate_module.capture_entry(work_tree)
    entry_adoption_record: dict[str, Any] | None = None
    if entry_adoption:
        from . import entry_adoption as entry_adoption_module
        adopt_text = Path(entry_adoption).read_text(encoding="utf-8")
        adopt_data = json.loads(adopt_text)
        entry_adoption_record = entry_adoption_module.validate_strict_entry(
            work_tree, adopt_data, phase_id=effective_phase_id, request=request
        )

    effective_outbox_root = resolve_outbox_root(
        explicit=outbox_root,
        project_root=repo_root,
        apgr_home=apgr_home,
    )

    req_digest = hashlib.sha256(raw_request).hexdigest()
    actual_run_id = run_id or run_id_for_v2(request.phase_type)
    db_path = resolve_dispatcher_db_path(apgr_home)
    runs_dir = db_path.parent / "runs"
    runs_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        os.chmod(runs_dir, 0o700)
    except OSError:
        pass
    run_dir = runs_dir / actual_run_id
    run_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        os.chmod(run_dir, 0o700)
    except OSError:
        pass

    # Persist request copy as a run-owned file
    request_file = run_dir / "request.json"
    request_file.write_bytes(raw_request)

    conn = open_dispatcher_db(db_path)
    try:
        # Check if run exists already (for recovery/resume of same run)
        existing_run = get_run(conn, actual_run_id)
        if existing_run is None:
            # 1. Persist Run
            record_run(
                conn,
                run_id=actual_run_id,
                project=project,
                phase_id=effective_phase_id,
                schema_version=1,
                request_schema=request.schema,
                request_digest=req_digest,
                workflow_version="v0.12",
                lifecycle=spec.name,
                execution_mode=execution_mode,
                status="running" if runner else ("dry_run" if dry_run else "staged"),
                run_directory=str(run_dir),
            )

            # 2. Persist Configuration Provenance Chain
            chain = list(provenance_chain or [])
            if not chain and provenance:
                chain = [dict(provenance)]
            record_configuration_provenance(conn, actual_run_id, chain)

            # 3. Persist Actor Bindings
            record_actor_bindings(conn, actual_run_id, [b.as_dict() for b in policy.bindings])

            # 4. Persist Canonical Semantic Responsibilities
            for binding in policy.bindings:
                for role in binding.roles:
                    record_semantic_responsibility(
                        conn,
                        id=f"sem-{actual_run_id}-{role}",
                        run_id=actual_run_id,
                        responsibility_name=role,
                        binding_id=binding.binding_id,
                        status="pending",
                    )

            # 5. Persist Request Artifact
            record_artifact(
                conn,
                artifact_id=f"art-{actual_run_id}-request",
                run_id=actual_run_id,
                artifact_name="request.json",
                relative_path="request.json",
                size_bytes=len(raw_request),
                sha256=req_digest,
                content_type="application/json",
            )

        # Record resume relation if this run resumes/retries a prior run
        if resume_from_run_id is not None:
            record_resume_relation(
                conn,
                run_id=actual_run_id,
                prior_run_id=resume_from_run_id,
                resumed_from_stage="auto",
                relation_type="retry",
            )

        # Collect operational observations using precedence (injected > durable > probes)
        injected = tuple(injected_observations or operational_observations)
        ref_now = time.time() if now is None else float(now)
        effective_observations = collect_operational_observations(
            conn=conn,
            now=ref_now,
            providers=("codex", "claude", "antigravity"),
            injected=injected,
        )

        for obs in effective_observations:
            record_operational_observation(
                conn,
                observation_id=obs.observation_id,
                producer=obs.producer,
                observation_type=obs.observation_type,
                provider=obs.provider,
                profile=obs.profile,
                timestamp=obs.timestamp,
                expires_at=obs.expires_at,
                state_value=obs.state_value,
                digest=obs.digest,
                detail=obs.detail,
            )

        # Execute semantic turns
        try:
            turn_result = execute_v2_turns(
                conn,
                actual_run_id,
                run_dir,
                repository_root,
                work_tree,
                request,
                execution_mode,
                policy,
                caps_catalog,
                effective_observations,
                runner,
                display,
                dry_run,
                spec,
                valid_finalization_policy,
                attempt_number=attempt_number,
                injected_observations=injected,
                now=ref_now,
            )
        except NoRouteAvailableError as exc:
            update_run_status(conn, actual_run_id, "failed", outcome="no_route", semantic_outcome="no_route")
            return {
                "schema": "agent-phase-result-v2",
                "run_id": actual_run_id,
                "project": project,
                "phase_id": effective_phase_id,
                "status": "no_route",
                "outcome": "no_route",
                "request_schema": request.schema,
                "phase_type": request.phase_type,
                "execution_mode": execution_mode,
                "lifecycle": spec.name,
                "finalization_policy": valid_finalization_policy,
                "detail": str(exc),
                "run_directory": str(run_dir),
                "db_path": str(db_path),
            }
        except PreLaunchFailureError as exc:
            update_run_status(conn, actual_run_id, "failed", outcome="failed_pre_launch", semantic_outcome="failed_pre_launch")
            raise V2DispatchError(f"Turn execution failed: {exc}") from exc
        except KeyboardInterrupt:
            update_run_status(conn, actual_run_id, "failed", outcome="operator_interrupted", semantic_outcome="operator_interrupted")
            raise
        except Exception as exc:
            timestamp_str = run_timestamp()
            leaf = v2_leaf(effective_phase_id, timestamp_str)
            projection_dir = effective_outbox_root / project / effective_phase_id
            target_projection_paths = {
                "run_directory": str(projection_dir / leaf),
                "archive": str(projection_dir / f"{leaf}.zip"),
                "locator": str(projection_dir / f"{leaf}.locator.json"),
            }
            fail_res = {
                "schema": "agent-phase-result-v2",
                "run_id": actual_run_id,
                "project": project,
                "phase_id": effective_phase_id,
                "status": "failed",
                "semantic_status": "failed",
                "finalization_policy": valid_finalization_policy,
                "finalization_status": "failed",
                "request_schema": request.schema,
                "phase_type": request.phase_type,
                "execution_mode": execution_mode,
                "lifecycle": spec.name,
                "commit": None,
                "tree": None,
                "publication_status": None,
                "remote_readback": None,
                "archive_path": None,
                "archive_sha256": None,
                "archive_status": "pending_sealing",
                "run_directory": str(run_dir),
                "db_path": str(db_path),
                "projection_paths": target_projection_paths,
                "error": str(exc),
            }
            try:
                (run_dir / "result.json").write_text(json.dumps(fail_res, indent=2) + "\n", encoding="utf-8")
                in_archive_loc = build_locator_payload(
                    project=project,
                    phase_id=effective_phase_id,
                    run_id=actual_run_id,
                    request_digest=req_digest,
                    canonical_run_path=run_dir,
                    database_path=db_path,
                    archive_path=None,
                    archive_sha256=None,
                    projection_paths=target_projection_paths,
                    semantic_status="failed",
                    finalization_policy=valid_finalization_policy,
                    finalization_status="failed",
                    commit=None,
                    tree=None,
                    publication_status=None,
                    remote_readback=None,
                    archive_status="pending_sealing",
                )
                (run_dir / "locator.json").write_text(json.dumps(in_archive_loc, indent=2) + "\n", encoding="utf-8")
                archive_path = run_dir.parent / f"{actual_run_id}.zip"
                if not archive_path.exists():
                    fd = os.open(archive_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                    os.close(fd)
                    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                        for root_dir, _, files in os.walk(run_dir):
                            for file in files:
                                p = Path(root_dir) / file
                                zf.write(p, arcname=str(p.relative_to(run_dir)))
                archive_sha256 = hashlib.sha256(archive_path.read_bytes()).hexdigest()
                update_run_status(
                    conn,
                    actual_run_id,
                    "failed",
                    outcome="failed",
                    semantic_outcome="failed",
                    finalization_outcome="failed",
                    archive_path=str(archive_path),
                    archive_sha256=archive_sha256,
                )
                fail_res["archive_path"] = str(archive_path)
                fail_res["archive_sha256"] = archive_sha256
                fail_res.pop("archive_status", None)
                (run_dir / "result.json").write_text(json.dumps(fail_res, indent=2) + "\n", encoding="utf-8")
                project_v2_run(
                    outbox_root=effective_outbox_root,
                    project=project,
                    phase_id=effective_phase_id,
                    run_id=actual_run_id,
                    leaf=leaf,
                    canonical_run_dir=run_dir,
                    canonical_archive_path=archive_path,
                    archive_sha256=archive_sha256,
                    database_path=db_path,
                    request_digest=req_digest,
                    semantic_status="failed",
                    finalization_policy=valid_finalization_policy,
                    finalization_status="failed",
                    commit=None,
                    tree=None,
                    publication_status=None,
                    remote_readback=None,
                )
            except Exception:
                update_run_status(conn, actual_run_id, "failed", outcome="failed", semantic_outcome="failed")
            raise V2DispatchError(f"Turn execution failed: {exc}") from exc
        except BaseException:
            update_run_status(conn, actual_run_id, "failed", outcome="failed", semantic_outcome="failed")
            raise

        commit_info: dict[str, Any] | None = None
        tree_info: str | None = turn_result.get("final_tree")
        publication_status: str | None = None
        remote_readback: dict[str, Any] | None = None

        repair_evidence = turn_result.get("result_repair")
        auxiliary_performed = 1 if repair_evidence else 0
        total_effective_turns = spec.expected_provider_invocations + auxiliary_performed

        if runner is not None:
            parsed_closeout = turn_result.get("closeout_stage_result")
            if parsed_closeout is None or not parsed_closeout.completed:
                semantic_status = "failed"
                finalization_status = "failed"
                overall_status = "failed"
            else:
                semantic_status = "completed"
                effective_display = display or Display(None, enabled=False)
                native_transition = None
                if native_git_authority:
                    from . import native_git as native_git_module
                    auth_text = Path(native_git_authority).read_text(encoding="utf-8")
                    auth_dict = json.loads(auth_text)
                    native_transition = native_git_module.validate_authority(
                        work_tree, auth_dict, phase_id=effective_phase_id, request=request
                    )

                fin_state: dict[str, Any] = {
                    "lifecycle": spec.name,
                    "finalization_policy": valid_finalization_policy,
                    "effective_stages": {name: "performed" for name in spec.stage_names},
                    "effective_checkpoints": list(spec.checkpoints),
                    "effective_review_count": len(spec.checkpoints),
                    "provider_invocations_inherited": 0,
                    "provider_invocations_performed": spec.expected_provider_invocations,
                    "provider_invocations_effective": spec.expected_provider_invocations,
                    "auxiliary_provider_invocations": auxiliary_performed,
                    "auxiliary_provider_invocations_performed": auxiliary_performed,
                    "total_effective_provider_turns": total_effective_turns,
                    "result_repair": repair_evidence,
                    "terminal_candidate": {"tree": turn_result["final_tree"]},
                    "closeout_candidate": {"tree": turn_result["final_tree"]},
                    "native_git_transition": native_transition,
                    "path_dispositions": [d._asdict() for d in parsed_closeout.path_dispositions] if parsed_closeout else [],
                    "phase_owned_paths": [],
                    "stage_deltas": {},
                    "ownership_challenges": None,
                    "entry": entry.as_dict(),
                }
                if entry_adoption_record is not None:
                    fin_state["entry_adoption"] = entry_adoption_record
                    fin_state["phase_owned_paths"] = sorted(set(entry_adoption_record.get("adopted_paths", [])))
                    if "candidate_manifest" in entry_adoption_record:
                        fin_state["candidate_manifest"] = entry_adoption_record["candidate_manifest"]
                try:
                    finalization_module.finalize_repository(
                        fin_state,
                        entry,
                        parsed_closeout,
                        effective_display,
                        resumed=False,
                        directory=_RunDirectoryAdapter(run_dir),
                        expected_index=entry.index_identity,
                    )
                    commit_info = fin_state.get("commit")
                    tree_info = fin_state.get("final_tree", turn_result["final_tree"])
                    push_rec = fin_state.get("push", {})

                    fin_outcome = fin_state.get("finalization_outcome")
                    repo_finalized = fin_state.get("repository_finalized", False)
                    comp_kind = fin_state.get("completion_kind")

                    if valid_finalization_policy == FINALIZATION_CHECKPOINT:
                        if fin_outcome == "completed" and comp_kind == "checkpoint_ready":
                            finalization_status = "checkpointed"
                            overall_status = "completed"
                        else:
                            finalization_status = "failed"
                            overall_status = "failed"
                    elif valid_finalization_policy == FINALIZATION_COMMIT_LOCAL:
                        if repo_finalized and fin_outcome in ("completed", "reused"):
                            finalization_status = "completed"
                            overall_status = "completed"
                        else:
                            finalization_status = "failed"
                            overall_status = "failed"
                    elif valid_finalization_policy == FINALIZATION_PUBLISH:
                        publication_status = push_rec.get("status")
                        remote_readback = push_rec
                        if repo_finalized and (push_rec.get("status") == "succeeded" or comp_kind == "finalized_empty_delta"):
                            finalization_status = "completed"
                            overall_status = "completed"
                        else:
                            finalization_status = "failed"
                            overall_status = "failed"
                    else:
                        finalization_status = "completed"
                        overall_status = "completed"
                except (FinalizationError, PublicationError, gitstate_module.GitStateError):
                    finalization_status = "failed"
                    overall_status = "failed"
                    push_rec = fin_state.get("push", {})
                    publication_status = push_rec.get("status", "failed")
                    remote_readback = push_rec
        elif dry_run:
            semantic_status = "dry_run"
            finalization_status = "not_attempted"
            overall_status = "dry_run"
        else:
            semantic_status = "staged_pre_launch"
            finalization_status = "not_attempted"
            overall_status = "staged_pre_launch"

        # Construct projection metadata and paths
        timestamp_str = run_timestamp()
        leaf = v2_leaf(effective_phase_id, timestamp_str)
        projection_dir = effective_outbox_root / project / effective_phase_id
        target_projection_paths = {
            "run_directory": str(projection_dir / leaf),
            "archive": str(projection_dir / f"{leaf}.zip"),
            "locator": str(projection_dir / f"{leaf}.locator.json"),
        }

        first_binding = policy.bindings[0].binding_id
        first_route = turn_result["prior_resolutions"].get(first_binding)
        selected_route_dict = first_route.as_dict() if first_route else {}

        # 1. In-archive result.json (archive digests null / pending_sealing)
        in_archive_result = {
            "schema": "agent-phase-result-v2",
            "run_id": actual_run_id,
            "project": project,
            "phase_id": effective_phase_id,
            "status": overall_status,
            "semantic_status": semantic_status,
            "finalization_policy": valid_finalization_policy,
            "finalization_status": finalization_status,
            "request_schema": request.schema,
            "phase_type": request.phase_type,
            "execution_mode": execution_mode,
            "lifecycle": spec.name,
            "commit": commit_info,
            "tree": tree_info,
            "publication_status": publication_status,
            "remote_readback": remote_readback,
            "archive_path": None,
            "archive_sha256": None,
            "archive_status": "pending_sealing",
            "initial_binding": first_binding,
            "selected_route": selected_route_dict,
            "all_routes": {k: v.as_dict() for k, v in turn_result["prior_resolutions"].items()},
            "auxiliary_provider_invocations": auxiliary_performed,
            "auxiliary_provider_invocations_performed": auxiliary_performed,
            "total_effective_provider_turns": total_effective_turns,
            "result_repair": repair_evidence,
            "run_directory": str(run_dir),
            "db_path": str(db_path),
            "projection_paths": target_projection_paths,
        }
        res_json_bytes = (json.dumps(in_archive_result, indent=2) + "\n").encode("utf-8")
        (run_dir / "result.json").write_bytes(res_json_bytes)

        # 2. In-archive result.md
        res_md_text = (
            f"# Phase Execution Result: {effective_phase_id}\n\n"
            f"- **Run ID**: `{actual_run_id}`\n"
            f"- **Project**: `{project}`\n"
            f"- **Overall Status**: `{overall_status}`\n"
            f"- **Semantic Status**: `{semantic_status}`\n"
            f"- **Finalization Policy**: `{valid_finalization_policy}`\n"
            f"- **Finalization Status**: `{finalization_status}`\n"
            f"- **Lifecycle**: `{spec.name}`\n"
            f"- **Execution Mode**: `{execution_mode}`\n\n"
            f"## Git & Publication Summary\n\n"
            f"- **Candidate Tree**: `{tree_info or 'none'}`\n"
            f"- **Commit**: `{commit_info.get('sha') if commit_info else 'none'}` "
            f"({commit_info.get('subject') if commit_info else 'none'})\n"
            f"- **Publication Status**: `{publication_status or 'none'}`\n\n"
            f"## Turns & Routes Executed\n\n"
        )
        for b_id, r in turn_result["prior_resolutions"].items():
            res_md_text += f"- **{b_id}**: `{r.provider}/{r.profile}` via `{r.endpoint_alias}`\n"
        if repair_evidence:
            res_md_text += (
                f"\n## Result Repair Evidence\n\n"
                f"- **Operation**: `{repair_evidence.get('operation')}`\n"
                f"- **Source Attempt**: `{repair_evidence.get('source_attempt_id')}`\n"
                f"- **Source Result Blocker**: `{repair_evidence.get('source_result_blocker')}`\n"
                f"- **Repair Provider / Profile**: `{repair_evidence.get('repair_provider')}/{repair_evidence.get('repair_profile')}`\n"
                f"- **Strict Parse Outcome**: `{repair_evidence.get('strict_parse_outcome')}`\n"
                f"- **Isolated Working Directory**: `{repair_evidence.get('isolated_working_directory')}`\n"
                f"- **Candidate Tree Unchanged**: `{repair_evidence.get('candidate_tree_identical')}`\n"
                f"- **Side Effects Free**: `{repair_evidence.get('no_side_effect_truth')}`\n"
            )
        res_md_bytes = res_md_text.encode("utf-8")
        (run_dir / "result.md").write_bytes(res_md_bytes)

        # 3. In-archive locator.json copy
        in_archive_locator = build_locator_payload(
            project=project,
            phase_id=effective_phase_id,
            run_id=actual_run_id,
            request_digest=req_digest,
            canonical_run_path=run_dir,
            database_path=db_path,
            archive_path=None,
            archive_sha256=None,
            projection_paths=target_projection_paths,
            semantic_status=semantic_status,
            finalization_policy=valid_finalization_policy,
            finalization_status=finalization_status,
            commit=commit_info,
            tree=tree_info,
            publication_status=publication_status,
            remote_readback=remote_readback,
            archive_status="pending_sealing",
        )
        loc_json_bytes = (json.dumps(in_archive_locator, indent=2) + "\n").encode("utf-8")
        (run_dir / "locator.json").write_bytes(loc_json_bytes)

        # Record run-owned artifacts in DB
        if runner is not None:
            att_suffix = f"-att{attempt_number}" if attempt_number > 1 else ""
            for art_name, art_bytes, art_type in (
                ("result.json", res_json_bytes, "application/json"),
                ("result.md", res_md_bytes, "text/markdown"),
                ("locator.json", loc_json_bytes, "application/json"),
            ):
                record_artifact(
                    conn,
                    artifact_id=f"art-{actual_run_id}{att_suffix}-{art_name.replace('.', '-')}",
                    run_id=actual_run_id,
                    artifact_name=art_name,
                    relative_path=art_name,
                    size_bytes=len(art_bytes),
                    sha256=hashlib.sha256(art_bytes).hexdigest(),
                    content_type=art_type,
                )

        # Finalize and seal archive
        archive_path: Path | None = None
        archive_sha256: str | None = None

        if runner is not None:
            archive_path = run_dir.parent / f"{actual_run_id}.zip"
            if archive_path.exists() or archive_path.is_symlink():
                raise RunPathError(f"canonical archive already exists: {archive_path}")
            fd = os.open(archive_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for root_dir, _, files in os.walk(run_dir):
                    for file in files:
                        p = Path(root_dir) / file
                        zf.write(p, arcname=str(p.relative_to(run_dir)))
            archive_sha256 = hashlib.sha256(archive_path.read_bytes()).hexdigest()
            update_run_status(
                conn,
                actual_run_id,
                overall_status,
                outcome=overall_status,
                semantic_outcome=semantic_status,
                finalization_outcome=finalization_status,
                archive_path=str(archive_path),
                archive_sha256=archive_sha256,
            )
        elif dry_run:
            update_run_status(conn, actual_run_id, "dry_run", outcome="dry_run", semantic_outcome="dry_run")
        else:
            update_run_status(conn, actual_run_id, "staged", outcome="staged", semantic_outcome="staged")

        # Execute outbox projection
        locator_payload: dict[str, Any] | None = None
        projection_error: str | None = None
        if runner is not None and archive_path is not None:
            try:
                locator_payload = project_v2_run(
                    outbox_root=effective_outbox_root,
                    project=project,
                    phase_id=effective_phase_id,
                    run_id=actual_run_id,
                    leaf=leaf,
                    canonical_run_dir=run_dir,
                    canonical_archive_path=archive_path,
                    archive_sha256=archive_sha256,
                    database_path=db_path,
                    request_digest=req_digest,
                    semantic_status=semantic_status,
                    finalization_policy=valid_finalization_policy,
                    finalization_status=finalization_status,
                    commit=commit_info,
                    tree=tree_info,
                    publication_status=publication_status,
                    remote_readback=remote_readback,
                )
            except Exception as proj_err:
                projection_error = str(proj_err)

        result_payload = dict(in_archive_result)
        result_payload.pop("archive_status", None)
        if archive_path is not None:
            result_payload["archive_path"] = str(archive_path)
            result_payload["archive_sha256"] = archive_sha256
        if locator_payload is not None:
            result_payload["projection_paths"] = locator_payload["projection_paths"]
        elif projection_error is not None:
            result_payload["projection_error"] = projection_error
            result_payload["projection_status"] = "failed"

        # Update canonical on-disk result.json and locator.json with post-sealing archive truth
        if archive_path is not None:
            canonical_res_bytes = (json.dumps(result_payload, indent=2) + "\n").encode("utf-8")
            tmp_res = run_dir / ".result.json.tmp"
            tmp_res.write_bytes(canonical_res_bytes)
            os.replace(tmp_res, run_dir / "result.json")
            if locator_payload is not None:
                canonical_loc_bytes = (json.dumps(locator_payload, indent=2) + "\n").encode("utf-8")
                tmp_loc = run_dir / ".locator.json.tmp"
                tmp_loc.write_bytes(canonical_loc_bytes)
                os.replace(tmp_loc, run_dir / "locator.json")

        return result_payload
    finally:
        conn.close()
