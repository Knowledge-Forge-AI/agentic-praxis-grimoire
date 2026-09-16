"""Stage orchestration for dispatcher-owned lifecycle specifications.

Each stage is a fresh process with explicitly rebuilt context. Provider session
continuity is never relied upon.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

from . import archive as archive_module
from . import antigravity_evidence as antigravity_evidence_module
from . import candidate as candidate_module
from . import capacity as capacity_module
from . import display as display_module
from . import dry_run as dry_run_module
from . import envelope as envelope_module
from . import failure_boundary as failure_boundary_module
from . import finalization as finalization_module
from . import gitstate as gitstate_module
from . import lifecycle_dispatch as lifecycle_dispatch_module
from .lifecycle import (
    FINALIZATION_PUBLISH,
    LIFECYCLE_STANDARD,
    get_lifecycle,
    validate_finalization,
)
from .publication import record as push_record
from . import prompt_policy as prompt_policy_module
from . import provider as provider_module
from . import result as result_module
from . import review_result as review_result_module
from . import result_artifacts as result_artifacts_module
from . import resume as resume_module
from . import adoption as adoption_module
from . import resume_dispatch as resume_dispatch_module
from . import run as run_module
from . import scanner as scanner_module
from . import stage_delta as stage_delta_module
from .request import PhaseRequest, WORKER_CAPABLE_MODES
from .routing import (
    Endpoint,
    PROVIDER_ANTIGRAVITY,
    PROVIDER_CODEX,
    antigravity_intelligence,
    load_validated_roster,
    resolve,
    route,
)
from .transport import (
    PromptLimitError,
    ensure_prompt_fits,
)
from .worker_capability import resolve_worker_capability
from .worker_custody import WorkerCustody

RESULT_SCHEMA = result_artifacts_module.RESULT_SCHEMA


class DispatchError(RuntimeError):
    """A run could not proceed without violating a dispatcher invariant.

    `code` is the recorded blocking reason. It is set for every path that can
    leave a phase incomplete, so `result.json` never has to describe a failure in
    prose the dispatcher cannot itself classify.
    """

    def __init__(self, message: str, code: str = "DISPATCH_FAILED") -> None:
        super().__init__(message)
        self.code = code


class Dispatcher:
    """Owns routing, stage transitions, artifacts, and shadow telemetry.

    Provider and scanner executables are constructor parameters. Provider
    executables default to lazy resolution from PATH on first use; tests inject
    fakes by construction; there is deliberately no environment variable or
    CLI flag that redirects them in production.
    """

    def __init__(
        self,
        root: Path,
        cwd: Path,
        run_root: Path | None = None,
        codex_executable: str | None = None,
        claude_launcher: str | None = None,
        antigravity_launcher: str | None = None,
        scanner_executable: str | None = None,
        scanner_version: str | None = None,
        resolve_scanner: bool = True,
        runner: Callable[..., provider_module.Result] = provider_module.run,
        display: display_module.Display | None = None,
    ) -> None:
        self.root = root
        self.cwd = cwd
        self.run_root = run_root or run_module.default_root()
        self.codex_executable = codex_executable
        self.claude_launcher = claude_launcher
        self.antigravity_launcher = antigravity_launcher
        self.runner = runner
        # A disabled display is a complete display: every call is a no-op, so no
        # code path below has to ask whether an observer is attached.
        self.display = display or display_module.Display(None, enabled=False)
        if scanner_executable is None and resolve_scanner:
            scanner_executable = scanner_module.resolve_scanner()
        self.scanner_executable = scanner_executable
        if scanner_version is None and scanner_executable is not None:
            scanner_version = scanner_module.scanner_version(scanner_executable)
        self.scanner_version = scanner_version
        self.invocations: list[dict[str, Any]] = []
        self.provider_evidence: list[dict[str, Any]] = []
        self.telemetry_failures: list[dict[str, Any]] = []
        self.scan_rows: list[dict[str, Any]] = []
        self.prompt_policy_segments: list[dict[str, Any]] = []
        self.stage_output_limits: dict[str, int] = {}
        self._active_stage: str | None = None
        self._stage_accounting_state: dict[str, Any] | None = None
        self._stage_accounting_directory: run_module.RunDirectory | None = None
        self._entry_state: gitstate_module.EntryState | None = None
        self._adoption: dict[str, Any] | None = None
        self._native_git_authority: dict[str, Any] | None = None
        self._entry_adoption: dict[str, Any] | None = None
        self.lifecycle = get_lifecycle(LIFECYCLE_STANDARD)
        self.finalization_policy = FINALIZATION_PUBLISH

    def _bind_stage_accounting(
        self,
        state: dict[str, Any],
        directory: run_module.RunDirectory,
        entry: gitstate_module.EntryState | None = None,
    ) -> None:
        self._stage_accounting_state = state
        self._stage_accounting_directory = directory
        self._entry_state = entry

    def _record_stage_accounting(self, field: str, stage: str) -> None:
        state = self._stage_accounting_state
        directory = self._stage_accounting_directory
        if state is None or directory is None:
            return
        stages = state.setdefault(field, [])
        if stage not in stages:
            stages.append(stage)
        state["shadow"] = self._shadow_state()
        directory.write_json("state.json", state)

    def _record_stage_transport(
        self, stage: str, status: str, **facts: Any
    ) -> None:
        state = self._stage_accounting_state
        if state is None:
            return
        state.setdefault("stage_transport_outcomes", {})[stage] = {
            "stage": stage,
            "status": status,
            **facts,
        }

    # -- prompt assembly ---------------------------------------------------

    def _header(self, stage: str, request: PhaseRequest, run_id: str) -> str:
        return envelope_module.stage_header(
            stage,
            run_id,
            request.phase_type,
            request.execution_mode,
            self.lifecycle.name,
            self.lifecycle.checkpoints,
            self.finalization_policy,
        ) + adoption_module.prompt_context(getattr(self, "_adoption", None))

    def plan_prompt(
        self, request: PhaseRequest, run_id: str, task_prompt: str | None = None
    ) -> envelope_module.RenderedPrompt:
        return envelope_module.render(
            [
                envelope_module.Segment(
                    envelope_module.SEGMENT_ENVELOPE,
                    self._header(envelope_module.STAGE_PLAN, request, run_id)
                    + "\n"
                    + envelope_module.PLAN_ENVELOPE
                    + "\n\n"
                    + envelope_module.PROVIDER_NOTE
                    + "\n\n"
                    + envelope_module.TASK_PROMPT_HEADER,
                ),
                envelope_module.Segment(
                    envelope_module.SEGMENT_TASK_PROMPT,
                    request.prompt if task_prompt is None else task_prompt,
                ),
            ]
        )

    def review_prompt(
        self,
        stage: str,
        request: PhaseRequest,
        run_id: str,
        binding: dict[str, Any],
        material: str | bytes,
        task_prompt: str,
        review_contract: str,
    ) -> envelope_module.RenderedPrompt:
        task_header = (
            self._header(stage, request, run_id)
            + "\n"
            + envelope_module.REVIEWER_ENVELOPE
            + "\n\n"
            + review_contract
            + "\n\n"
            + envelope_module.GIT_IDENTITY_POLICY
            + "\n\n"
            + envelope_module.TASK_PROMPT_HEADER
        )
        material_header = (
            "Candidate binding:\n"
            + "\n".join(f"  {key}: {value}" for key, value in sorted(binding.items()))
            + "\n\n"
            + envelope_module.REVIEWER_INDEPENDENCE
            + "\n\n"
            + envelope_module.PRIOR_MATERIAL_HEADER
        )
        return envelope_module.render(
            [
                envelope_module.Segment(
                    envelope_module.SEGMENT_ENVELOPE, task_header
                ),
                envelope_module.Segment(
                    envelope_module.SEGMENT_TASK_PROMPT, task_prompt
                ),
                envelope_module.Segment(
                    envelope_module.SEGMENT_ENVELOPE, material_header
                ),
                envelope_module.Segment(
                    envelope_module.SEGMENT_PRIOR_MATERIAL, material
                ),
            ]
        )

    def continuation_prompt(
        self,
        stage: str,
        request: PhaseRequest,
        run_id: str,
        directive: str,
        prior: list[tuple[str, str | bytes]],
        include_task_prompt: bool,
        contract: str | None = None,
        task_prompt: str | None = None,
    ) -> envelope_module.RenderedPrompt:
        header = (
            self._header(stage, request, run_id)
            + "\n"
            + directive
            + "\n\n"
            + envelope_module.PROVIDER_NOTE
        )
        segments = [envelope_module.Segment(envelope_module.SEGMENT_ENVELOPE, header)]
        if include_task_prompt:
            segments.append(
                envelope_module.Segment(
                    envelope_module.SEGMENT_ENVELOPE,
                    "\n" + envelope_module.TASK_PROMPT_HEADER,
                )
            )
            segments.append(
                envelope_module.Segment(
                    envelope_module.SEGMENT_TASK_PROMPT,
                    request.prompt if task_prompt is None else task_prompt,
                )
            )
        segments.append(
            envelope_module.Segment(
                envelope_module.SEGMENT_ENVELOPE,
                "\n" + envelope_module.PRIOR_MATERIAL_HEADER,
            )
        )
        for title, body in prior:
            if isinstance(body, bytes):
                payload: str | bytes = (
                    f"\n## {title}\n\n".encode("utf-8") + body
                )
            else:
                payload = f"\n## {title}\n\n{body}"
            segments.append(
                envelope_module.Segment(
                    envelope_module.SEGMENT_PRIOR_MATERIAL,
                    payload,
                )
            )
        if contract is not None:
            # Keep the nonce-bound contract at the absolute prompt end. Do not
            # place any task, prior material, or contextual headers after this
            # segment: the provider's exact ending must be unambiguous.
            segments.append(
                envelope_module.Segment(
                    envelope_module.SEGMENT_ENVELOPE,
                    "\n" + envelope_module.TERMINAL_CONTRACT_PRECEDER
                    + "\n" + contract,
                )
            )
        return envelope_module.render(segments)

    def closeout_prompt(
        self,
        request: PhaseRequest,
        run_id: str,
        task_prompt: str,
        producer_binding: dict[str, Any],
        current_product: dict[str, Any],
        producer_narrative: str | bytes,
        findings: str,
        begin: str,
        end: str,
        *,
        stage_delta_summary: str | None = None,
        qualification_evidence: str | None = None,
    ) -> envelope_module.RenderedPrompt:
        prior_segments: list[tuple[str, str | bytes]] = [
            (
                "Producer candidate binding (dispatcher-owned exact identity)",
                json.dumps(producer_binding, sort_keys=True, separators=(",", ":")),
            ),
            (
                "Current exact worktree product (dispatcher-owned binding)",
                json.dumps(current_product, sort_keys=True, separators=(",", ":")),
            ),
            ("Producer summary/output (optional whole artifact)", producer_narrative),
            ("Independent work-review findings", findings),
        ]
        if stage_delta_summary:
            prior_segments.append(
                ("Prior stage-delta summary (dispatcher-owned evidence)", stage_delta_summary)
            )
        if qualification_evidence:
            prior_segments.append(
                ("Qualification evidence available in the run", qualification_evidence)
            )
        return self.continuation_prompt(
            envelope_module.STAGE_CLOSEOUT,
            request,
            run_id,
            envelope_module.CLOSEOUT_ENVELOPE,
            prior_segments,
            include_task_prompt=True,
            contract=envelope_module.CLOSEOUT_RESULT_CONTRACT.format(
                begin=begin, end=end
            ),
            task_prompt=task_prompt,
        )

    def _sanitize(
        self,
        directory: run_module.RunDirectory,
        state: dict[str, Any],
        source: str,
        text: str,
    ) -> str:
        sanitized = prompt_policy_module.sanitize(text)
        self.prompt_policy_segments.append(sanitized.evidence(source))
        total = sum(
            int(segment["removal_count"])
            for segment in self.prompt_policy_segments
        )
        summary = {
            "policy_version": prompt_policy_module.POLICY_VERSION,
            "sanitized": total > 0,
            "total_removal_count": total,
            "evidence_artifact": "prompt-policy.json",
        }
        state["prompt_policy"] = summary
        directory.write_json(
            "prompt-policy.json",
            {
                "schema": "agent-phase-prompt-policy-v1",
                **summary,
                "segments": list(self.prompt_policy_segments),
            },
        )
        directory.write_json("state.json", state)
        return sanitized.text

    # -- execution ---------------------------------------------------------

    def _scan(
        self,
        directory: run_module.RunDirectory,
        prefix: str,
        boundary: str,
        rendered: envelope_module.RenderedPrompt,
    ) -> dict[str, Any]:
        row = scanner_module.scan(
            rendered.data,
            boundary,
            directory.run_id,
            rendered.segments,
            f"{prefix}.prompt.md",
            executable=self.scanner_executable,
            version=self.scanner_version,
        )
        # Shadow telemetry must never be able to end a run. A failure to persist
        # it is recorded and stepped over, exactly like an UNAVAILABLE verdict.
        try:
            scanner_module.append_row(directory.telemetry_path, row)
            directory.write_json(f"{prefix}.scan.json", row)
        except OSError as error:
            self.telemetry_failures.append({"prefix": prefix, "error": str(error)})
        self.scan_rows.append(row)
        return row

    def _shadow_state(self) -> dict[str, Any]:
        """Report what the scans actually did, not what was expected of them."""
        statuses = sorted({str(row["status"]) for row in self.scan_rows})
        scanned = [
            row for row in self.scan_rows
            if row["status"] == scanner_module.STATUS_SCANNED
        ]
        return {
            "scanner_available": self.scanner_executable is not None,
            "scan_statuses": statuses,
            "scans_attempted": len(self.scan_rows),
            "scans_completed": len(scanned),
            "telemetry_failures": list(self.telemetry_failures),
            "shadow_qualification_complete": (
                bool(self.scan_rows)
                and len(scanned) == len(self.scan_rows)
                and not self.telemetry_failures
            ),
        }

    def _stage(
        self,
        directory: run_module.RunDirectory,
        index: int,
        stage: str,
        prefix: str,
        role: str,
        endpoint: Endpoint,
        rendered: envelope_module.RenderedPrompt,
        binding: dict[str, Any] | None,
        *,
        read_only: bool | None = None,
        working_directory: Path | None = None,
        invocation_kind: str = "semantic",
        display_stage_count: int | None = None,
        on_provider_invoke: Callable[[], None] | None = None,
        worker_capability: dict[str, Any] | None = None,
    ) -> tuple[provider_module.Result, dict[str, Any]]:
        self._active_stage = stage
        from . import ownership_challenge
        challenge_state = self._stage_accounting_state
        if (challenge_state is not None and invocation_kind == "semantic"
                and stage == self.lifecycle.terminal_result_stage):
            # Separate dispatcher provenance precedes all task/provider prose.
            context = ownership_challenge.prompt(self.cwd, challenge_state, stage)
            rendered = envelope_module.render([
                envelope_module.Segment(envelope_module.SEGMENT_ENVELOPE, context),
                *[envelope_module.Segment(segment["kind"], rendered.data[segment["start"]:segment["end"]])
                  for segment in rendered.segments],
            ])
        from . import review_binding
        if (self._stage_accounting_state is not None
                and invocation_kind in ("semantic", "auxiliary_review_retry")
                and review_binding.is_review(self._stage_accounting_state, stage)):
            if invocation_kind == "semantic":
                review_binding.bind(self.cwd, self._stage_accounting_state, stage, binding)
            else:
                review_binding.verify(self.cwd, self._stage_accounting_state, stage)
        if role == "reviewer" and invocation_kind == "semantic":
            self._review_attempt_context = {
                "index": index, "endpoint": endpoint, "rendered": rendered,
                "binding": binding, "read_only": read_only,
                "candidate": candidate_module.tree_identity(self.cwd),
                "index_identity": gitstate_module.index_identity(self.cwd),
            }
        parent_id = run_module.stage_parent_id(directory.run_id, stage, index)
        worker_cap = worker_capability
        original_rendered = rendered
        if worker_cap is None and self._stage_accounting_state is not None:
            exec_mode = self._stage_accounting_state.get("execution_mode")
            if exec_mode in WORKER_CAPABLE_MODES and invocation_kind in ("semantic", "auxiliary_review_retry"):
                worker_cap = resolve_worker_capability(
                    self.root, endpoint.provider, endpoint.profile, exec_mode
                )
        effective_read_only = role == "reviewer" if read_only is None else read_only
        # Astra's native Luna pool is runtime-owned.  For the selected fixed
        # policy, bind its launch-local cap and worker facade before rendering
        # the prompt or registering the parent ledger.  Binding is optional at
        # the dispatcher boundary: a stale/missing launcher yields a durable
        # diagnostic and the ordinary provider task continues without workers.
        native_binding = None
        argv: list[str] | None = None
        native_astra = bool(
            worker_cap
            and worker_cap.get("allowed")
            and endpoint.provider == PROVIDER_CODEX
            and worker_cap.get("parent_family") == "codex_astra"
            and worker_cap.get("policy_selection") == "dual_pool_4x4"
        )
        if native_astra:
            try:
                from agent_workers.native_launch import (
                    apply_native_binding,
                    capability_with_native_binding,
                    prepare_native_binding,
                )

                if self.codex_executable is None:
                    self.codex_executable = provider_module.resolve_codex_executable()
                native_workspace = self.cwd if working_directory is None else working_directory
                native_authority = "read_only" if effective_read_only else "mutation_capable"
                native_state_dir = directory.path / "workers"
                base_argv = provider_module.build_argv(
                    endpoint,
                    role,
                    self.root,
                    self.codex_executable,
                    self.claude_launcher,
                    self.antigravity_launcher,
                    read_only=read_only,
                    evidence_prefix=None,
                    pin_profile=False,
                )
                native_binding = prepare_native_binding(
                    self.root,
                    parent_id=parent_id,
                    parent_profile=endpoint.profile,
                    workspace=native_workspace,
                    state_dir=native_state_dir,
                    task_authority=native_authority,
                    lifecycle_generation=f"{directory.run_id}:{stage}:{index}",
                    capability=worker_cap,
                )
                argv = apply_native_binding(base_argv, native_binding)
                worker_cap = capability_with_native_binding(
                    worker_cap, native_binding, argv
                )
            except Exception as error:  # optional launch binding boundary
                detail = str(error).replace("\n", " ").strip()[:240]
                worker_cap = {
                    **worker_cap,
                    "allowed": False,
                    "available": False,
                    "reason": (
                        "Astra native launch binding unavailable"
                        + (f" ({type(error).__name__}: {detail})" if detail else "")
                    ),
                }
        if worker_cap and worker_cap.get("allowed") and endpoint.provider == "claude":
            worker_cap = {**worker_cap, "interface": "stdio-mcp"}
        worker_guidance = ""
        if worker_cap and worker_cap.get("allowed") and endpoint.provider == PROVIDER_ANTIGRAVITY:
            from agent_source_guidance import source_guidance
            worker_guidance, _ = source_guidance(
                self.root / "antigravity", [], workers=True, instruction_file="GEMINI.md"
            )
        if worker_cap is not None:
            rendered = envelope_module.render([
                envelope_module.Segment(
                    envelope_module.SEGMENT_ENVELOPE,
                    worker_guidance + "\n" + envelope_module.worker_envelope(worker_cap, str(self.root / "bin/agent-worker")),
                ),
                *[
                    envelope_module.Segment(
                        segment["kind"],
                        rendered.data[segment["start"]:segment["end"]],
                    )
                    for segment in rendered.segments
                ],
            ])
        boundary: stage_delta_module.StageBoundary | None = None
        if self._stage_accounting_state is not None and invocation_kind in ("semantic", "auxiliary_review_retry"):
            boundary = stage_delta_module.open_stage_boundary(
                self.cwd if working_directory is None else working_directory,
                stage,
                self._stage_accounting_state,
                entry=self._entry_state,
                directory=directory,
            )
        try:
            ensure_prompt_fits(stage, endpoint, rendered)
        except PromptLimitError as error:
            if boundary is not None:
                boundary.close(ok=False, error=error)
            if invocation_kind == "semantic":
                self._record_stage_transport(
                    stage, "prompt_rejected_before_invocation"
                )
            raise DispatchError(str(error), "PROVIDER_PROMPT_LIMIT") from error
        directory.write_bytes(f"{prefix}.prompt.md", rendered.data)
        # Shadow only: nothing below reads the verdict.
        self._scan(directory, prefix, stage, rendered)
        if argv is None and endpoint.provider == PROVIDER_CODEX and self.codex_executable is None:
            try:
                self.codex_executable = provider_module.resolve_codex_executable()
            except provider_module.ProviderError as error:
                if boundary is not None:
                    boundary.close(ok=False, error=error)
                if invocation_kind == "semantic":
                    self._record_stage_transport(
                        stage, "provider_unavailable_before_invocation"
                    )
                raise
        if argv is None:
            argv = provider_module.build_argv(
                endpoint,
                role,
                self.root,
                self.codex_executable,
                self.claude_launcher,
                self.antigravity_launcher,
                read_only=read_only,
                evidence_prefix=(
                    directory.path / prefix
                    if endpoint.provider == PROVIDER_ANTIGRAVITY
                    else None
                ),
            )
            if endpoint.provider == PROVIDER_CODEX and invocation_kind in ("semantic", "auxiliary_review_retry"):
                # Profiles/auth remain provider-home owned. Fresh ordinary
                # stages receive this implementation's guidance, just as native
                # worker parents do in apply_native_binding. Do not add it twice
                # or change the detached result formatter's inspection contract.
                from agent_source_guidance import codex_guidance_overrides

                additions = []
                for override in codex_guidance_overrides(self.root, workers=False):
                    additions.extend(("-c", override))
                argv = argv[:-1] + additions + argv[-1:]
        self.display.stage_started(
            index,
            stage,
            role,
            endpoint,
            self.lifecycle.expected_provider_invocations
            if display_stage_count is None else display_stage_count,
        )
        parent_ledger = None
        prior_parent_id = os.environ.get("AGENT_CENTRAL_PARENT_ID")
        prior_worker_state = os.environ.get("AGENT_CENTRAL_WORKER_STATE_DIR")
        prior_facade = os.environ.get("AGENT_CENTRAL_WORKER_FACADE")
        custody = WorkerCustody(None, directory, prefix, self._stage_accounting_state)
        drain_summary: dict[str, Any] | None = None
        try:
            if worker_cap and worker_cap.get("allowed"):
                candidate_ledger = None
                try:
                    # The ledger is optional too.  Keep its import inside the same
                    # fallback boundary as registration so a missing or stale
                    # worker package cannot stop the parent provider invocation.
                    from agent_workers.ledger import ParentLedger

                    parent_family = worker_cap["parent_family"]
                    effective_read_only = role == "reviewer" if read_only is None else read_only
                    task_authority = "read_only" if effective_read_only else "mutation_capable"
                    worker_state_dir = directory.path / "workers"
                    candidate_ledger = ParentLedger(parent_id, worker_state_dir)
                    custody.adopt_if_present(candidate_ledger)
                    registered = candidate_ledger.register(
                        parent_family=parent_family,
                        task_authority=task_authority,
                        workspace=str(self.cwd if working_directory is None else working_directory),
                        policy_path=self.root / worker_cap["policy_source"],
                        worker_capability={
                            **worker_cap,
                            "policy_source": str((self.root / worker_cap["policy_source"]).resolve()),
                            "source_root": str(self.root),
                            "lifecycle_generation": f"{directory.run_id}:{stage}:{index}",
                            "execution_mode": (self._stage_accounting_state or {}).get("execution_mode"),
                            "parent_provider": endpoint.provider,
                            "parent_profile": endpoint.profile,
                            "parent_run_id": directory.run_id,
                            "parent_stage": stage,
                            "controller_generation": (self._stage_accounting_state or {}).get("controller_generation"),
                        },
                    )
                    parent_ledger = candidate_ledger
                    custody.ledger = candidate_ledger
                    if registered["policy"]["policy_sha256"] != worker_cap["policy_sha256"]:
                        raise ValueError("worker policy changed after resolution")
                    os.environ["AGENT_CENTRAL_PARENT_ID"] = parent_id
                    os.environ["AGENT_CENTRAL_WORKER_STATE_DIR"] = str(worker_state_dir)
                except BaseException as error:
                    if candidate_ledger is not None:
                        custody.adopt_if_present(candidate_ledger)
                    if not isinstance(error, Exception):
                        # A registration may have committed before an
                        # interruption was delivered. Preserve custody before
                        # propagating so a later resume cannot mistake the
                        # unpersisted state for a worker-free stage.
                        custody.arm()
                        raise
                    worker_cap = {
                        **worker_cap,
                        "allowed": False,
                        "available": False,
                        "reason": f"parent registration unavailable ({type(error).__name__})",
                    }
                    rendered = envelope_module.render([
                        envelope_module.Segment(
                            envelope_module.SEGMENT_ENVELOPE,
                            envelope_module.worker_envelope(worker_cap, str(self.root / "bin/agent-worker")),
                        ),
                        *[
                            envelope_module.Segment(
                                segment["kind"],
                                original_rendered.data[segment["start"]:segment["end"]],
                            )
                            for segment in original_rendered.segments
                        ],
                    ])
                    ensure_prompt_fits(stage, endpoint, rendered)
                    directory.write_bytes(f"{prefix}.prompt.md", rendered.data)
            # Registration is the admission boundary. Arm and persist the
            # marker before any provider code can launch a worker; a hard
            # parent exit therefore leaves resume/capture fenced on disk.
            custody.arm()
            if parent_ledger is not None and worker_cap.get("allowed") and endpoint.provider == "claude":
                os.environ["AGENT_CENTRAL_WORKER_FACADE"] = "1"
            else:
                os.environ.pop("AGENT_CENTRAL_WORKER_FACADE", None)
            if on_provider_invoke is not None:
                try:
                    on_provider_invoke()
                except BaseException as error:
                    if boundary is not None:
                        custody.close_boundary(boundary, ok=False, error=error)
                    if invocation_kind == "semantic":
                        self._record_stage_transport(
                            stage, "boundary_rejected_before_invocation"
                        )
                    raise
            if invocation_kind == "semantic":
                self._record_stage_accounting("stages_invoked", stage)
                self._record_stage_transport(stage, "invoking")
            # The runner seam's stable contract is this five-argument positional form.
            # Advisory stall notices are an extra keyword the real provider accepts,
            # so they are wired only for the production runner; injected test runners
            # keep the established signature. The dispatcher still never selects a
            # liveness policy -- that stays entirely source-owned in the provider.
            notice_kwargs: dict[str, Any] = {}
            if self.runner is provider_module.run:
                notice_kwargs["on_notice"] = self.display.stage_notice
            result = self.runner(
                argv,
                rendered.data,
                self.cwd if working_directory is None else working_directory,
                provider_module.MAX_STAGE_OUTPUT_BYTES,
                self.display.stage_output,
                **notice_kwargs,
            )
        except provider_module.ProviderLivenessExpired as expired:
            policy = {
                "inactivity_seconds": expired.policy.inactivity_seconds,
                "outer_ceiling_seconds": expired.policy.outer_ceiling_seconds,
            }
            liveness = {
                "code": "PROVIDER_LIVENESS_EXPIRED",
                "reason": expired.reason,
                "policy": policy,
                "elapsed_seconds": expired.elapsed_seconds,
                "silent_seconds": expired.silent_seconds,
                "last_activity_monotonic": expired.last_activity_monotonic,
                "last_activity_stream": expired.last_activity_stream,
                # Additive stall evidence: which recognized progress kind was
                # last seen, how stale it was, and the closed per-kind counts.
                "last_activity_kind": expired.last_activity_kind,
                "last_activity_age_seconds": expired.last_activity_age_seconds,
                "activity_counts": expired.activity_counts,
                "termination": expired.termination,
                "cleanup": expired.cleanup,
            }
            if invocation_kind == "semantic":
                self._record_stage_transport(
                    stage,
                    "liveness_expired",
                    exit_code=None,
                    truncated=expired.truncated,
                    stderr_truncated=expired.stderr_truncated,
                    liveness=liveness,
                )
            # The supervisor has already completed bounded process-group
            # teardown. Retain every captured byte and the policy/activity
            # evidence before the outer failure boundary takes custody of a
            # mutating stage's candidate.
            directory.write_bytes(f"{prefix}.stdout.md", expired.stdout)
            directory.write_bytes(f"{prefix}.stderr.log", expired.stderr)
            expired_meta = {
                "stage": stage,
                "role": role,
                "provider": endpoint.provider,
                "profile": endpoint.profile,
                "argv": list(argv),
                "prompt_sha256": run_module.digest(rendered.data),
                "prompt_bytes": len(rendered.data),
                "stdout_sha256": run_module.digest(expired.stdout),
                "stdout_bytes": len(expired.stdout),
                "stderr_sha256": run_module.digest(expired.stderr),
                "stderr_bytes": len(expired.stderr),
                "exit_code": None,
                "truncated": expired.truncated,
                "stderr_truncated": expired.stderr_truncated,
                "interrupted": False,
                "liveness_expired": True,
                "liveness": liveness,
                "candidate": binding,
            }
            if invocation_kind != "semantic":
                expired_meta["invocation_kind"] = invocation_kind
            directory.write_json(f"{prefix}.meta.json", expired_meta)
            invocation = {
                "stage": stage,
                "role": role,
                "provider": endpoint.provider,
                "profile": endpoint.profile,
                "argv": list(argv),
                "exit_code": None,
                "blocking_reason": "PROVIDER_LIVENESS_EXPIRED",
            }
            if invocation_kind != "semantic":
                invocation["invocation_kind"] = invocation_kind
            self.invocations.append(invocation)
            self.display.stage_failed(
                stage,
                f"provider liveness expired ({expired.reason}); "
                f"silent={expired.silent_seconds:.3f}s",
            )
            if boundary is not None:
                custody.close_boundary(boundary, ok=False, error=expired)
            raise DispatchError(
                f"stage {stage} provider liveness expired: {expired}",
                "PROVIDER_LIVENESS_EXPIRED",
            ) from expired
        except provider_module.ProviderCleanupFailed as failed:
            cleanup = failed.cleanup
            termination = failed.termination
            if invocation_kind == "semantic":
                self._record_stage_transport(
                    stage,
                    "cleanup_failed",
                    exit_code=failed.exit_code,
                    truncated=failed.truncated,
                    stderr_truncated=failed.stderr_truncated,
                    cleanup=cleanup,
                    termination=termination,
                )
            # Cleanup failure is transport evidence, not a successful provider
            # result. Preserve the exact bytes captured at the cleanup boundary
            # so the outer failure boundary can still account for a mutating
            # stage and archive the incomplete run.
            directory.write_bytes(f"{prefix}.stdout.md", failed.stdout)
            directory.write_bytes(f"{prefix}.stderr.log", failed.stderr)
            cleanup_meta = {
                "stage": stage,
                "role": role,
                "provider": endpoint.provider,
                "profile": endpoint.profile,
                "argv": list(argv),
                "prompt_sha256": run_module.digest(rendered.data),
                "prompt_bytes": len(rendered.data),
                "stdout_sha256": run_module.digest(failed.stdout),
                "stdout_bytes": len(failed.stdout),
                "stderr_sha256": run_module.digest(failed.stderr),
                "stderr_bytes": len(failed.stderr),
                "exit_code": failed.exit_code,
                "truncated": failed.truncated,
                "stderr_truncated": failed.stderr_truncated,
                "interrupted": False,
                "cleanup_failed": True,
                "cleanup": cleanup,
                "termination": termination,
                "candidate": binding,
            }
            if invocation_kind != "semantic":
                cleanup_meta["invocation_kind"] = invocation_kind
            directory.write_json(f"{prefix}.meta.json", cleanup_meta)
            invocation = {
                "stage": stage,
                "role": role,
                "provider": endpoint.provider,
                "profile": endpoint.profile,
                "argv": list(argv),
                "exit_code": failed.exit_code,
                "blocking_reason": "PROVIDER_CLEANUP_FAILED",
            }
            if invocation_kind != "semantic":
                invocation["invocation_kind"] = invocation_kind
            self.invocations.append(invocation)
            self.display.stage_failed(stage, "provider cleanup could not be proven")
            if boundary is not None:
                custody.close_boundary(boundary, ok=False, error=failed, exit_code=failed.exit_code)
            raise DispatchError(
                f"stage {stage} provider cleanup failed", "PROVIDER_CLEANUP_FAILED"
            ) from failed
        except provider_module.ProviderInterrupted as interrupted:
            if invocation_kind == "semantic":
                self._record_stage_transport(
                    stage,
                    "interrupted",
                    exit_code=None,
                    truncated=interrupted.truncated,
                    stderr_truncated=interrupted.stderr_truncated,
                    **(
                        {
                            "cleanup": interrupted.cleanup,
                            "termination": interrupted.termination,
                        }
                        if interrupted.cleanup
                        else {}
                    ),
                )
            # The provider is already terminated. Persist what it produced
            # before the interrupt rather than discarding a long stage's output.
            directory.write_bytes(f"{prefix}.stdout.md", interrupted.stdout)
            directory.write_bytes(f"{prefix}.stderr.log", interrupted.stderr)
            # A stage record too, so a reader is not left with four metas and no
            # account of the fifth. `exit_code` stays null rather than borrowing
            # a signal number the dispatcher did not observe.
            interrupted_meta = {
                "stage": stage,
                "role": role,
                "provider": endpoint.provider,
                "profile": endpoint.profile,
                "argv": list(argv),
                "prompt_sha256": run_module.digest(rendered.data),
                "prompt_bytes": len(rendered.data),
                "stdout_sha256": run_module.digest(interrupted.stdout),
                "stdout_bytes": len(interrupted.stdout),
                "stderr_sha256": run_module.digest(interrupted.stderr),
                "stderr_bytes": len(interrupted.stderr),
                "exit_code": None,
                "truncated": interrupted.truncated,
                "stderr_truncated": interrupted.stderr_truncated,
                "interrupted": True,
                "candidate": binding,
            }
            if interrupted.cleanup:
                interrupted_meta["cleanup"] = interrupted.cleanup
                interrupted_meta["termination"] = interrupted.termination
            if invocation_kind != "semantic":
                interrupted_meta["invocation_kind"] = invocation_kind
            directory.write_json(f"{prefix}.meta.json", interrupted_meta)
            invocation = {
                "stage": stage, "role": role, "provider": endpoint.provider,
                "profile": endpoint.profile, "argv": list(argv),
                "exit_code": None,
            }
            if invocation_kind != "semantic":
                invocation["invocation_kind"] = invocation_kind
            self.invocations.append(invocation)
            self.display.stage_failed(stage, "interrupted by operator")
            if boundary is not None:
                custody.close_boundary(boundary, ok=False, error=interrupted)
            raise DispatchError(
                f"stage {stage} interrupted by operator", "OPERATOR_INTERRUPTED"
            ) from interrupted
        except BaseException as error:
            if boundary is not None:
                custody.close_boundary(boundary,
                    ok=False,
                    error=error,
                    exit_code=getattr(error, "returncode", None),
                )
            if invocation_kind == "semantic":
                self._record_stage_transport(
                    stage,
                    "failed",
                    exit_code=getattr(error, "returncode", None),
                )
            invocation = {
                "stage": stage, "role": role, "provider": endpoint.provider,
                "profile": endpoint.profile, "argv": list(argv),
                "exit_code": getattr(error, "returncode", None),
            }
            if invocation_kind != "semantic":
                invocation["invocation_kind"] = invocation_kind
            self.invocations.append(invocation)
            raise
        finally:
            try:
                drain_summary = custody.drain()
            finally:
                if prior_facade is not None:
                    os.environ["AGENT_CENTRAL_WORKER_FACADE"] = prior_facade
                else:
                    os.environ.pop("AGENT_CENTRAL_WORKER_FACADE", None)
                if parent_ledger is not None:
                    if prior_parent_id is not None:
                        os.environ["AGENT_CENTRAL_PARENT_ID"] = prior_parent_id
                    else:
                        os.environ.pop("AGENT_CENTRAL_PARENT_ID", None)
                    if prior_worker_state is not None:
                        os.environ["AGENT_CENTRAL_WORKER_STATE_DIR"] = prior_worker_state
                    else:
                        os.environ.pop("AGENT_CENTRAL_WORKER_STATE_DIR", None)
        if invocation_kind == "semantic":
            self._record_stage_transport(
                stage,
                (
                    "overflowed"
                    if result.truncated
                    else "completed" if result.ok else "failed"
                ),
                exit_code=result.exit_code,
                truncated=result.truncated,
                stderr_truncated=result.stderr_truncated,
                **(
                    {"cleanup": result.cleanup}
                    if result.cleanup is not None
                    else {}
                ),
            )
        invocation = {
            "stage": stage, "role": role, "provider": endpoint.provider,
            "profile": endpoint.profile, "argv": list(argv),
            "exit_code": result.exit_code,
        }
        if invocation_kind != "semantic":
            invocation["invocation_kind"] = invocation_kind
        self.invocations.append(invocation)
        directory.write_bytes(f"{prefix}.stdout.md", result.stdout)
        directory.write_bytes(f"{prefix}.stderr.log", result.stderr)
        meta = run_module.stage_meta(
            stage, role, endpoint.provider, endpoint.profile, argv,
            rendered.data, result, binding,
        )
        if drain_summary is not None:
            meta["worker_drain"] = drain_summary
        if invocation_kind != "semantic":
            meta["invocation_kind"] = invocation_kind
        if endpoint.provider == PROVIDER_ANTIGRAVITY:
            try:
                evidence = antigravity_evidence_module.validate(
                    directory.path,
                    prefix,
                    endpoint.profile,
                    antigravity_intelligence(self.root, endpoint.profile)["model"],
                    role == "reviewer" if read_only is None else read_only,
                    result.exit_code,
                )
            except antigravity_evidence_module.EvidenceError as error:
                if boundary is not None:
                    custody.close_boundary(boundary, ok=False, error=error)
                evidence = {
                    "validation": "invalid",
                    "detail": str(error),
                    "original_wrapper_exit_code": result.exit_code,
                }
                meta["antigravity_evidence"] = evidence
                directory.write_json(f"{prefix}.meta.json", meta)
                self.provider_evidence.append({"stage": stage, **evidence})
                raise DispatchError(
                    f"stage {stage} Antigravity evidence invalid: {error}",
                    "PROVIDER_EVIDENCE_INVALID",
                ) from error
            meta["antigravity_evidence"] = evidence
            self.provider_evidence.append({"stage": stage, **evidence})
        if worker_cap is not None:
            meta["worker_capability"] = worker_cap
        directory.write_json(f"{prefix}.meta.json", meta)
        if drain_summary and drain_summary.get("uncertain_cleanup"):
            has_candidate = False
            candidate_observed = False
            if boundary is not None:
                try:
                    after_tree = candidate_module.tree_identity(self.cwd)["tree"]
                    before_tree = (
                        boundary.before_tree.get("tree")
                        if isinstance(boundary.before_tree, dict)
                        else boundary.before_tree
                    )
                    has_candidate = (after_tree != before_tree)
                    candidate_observed = True
                except Exception:
                    pass
            result_emitted = bool(
                result and result.stdout and result.stdout.strip()
            )
            if not result_emitted and not has_candidate and (candidate_observed or boundary is None):
                raw_survivors = drain_summary.get("orphaned_pids", []) or drain_summary.get("known_survivors", [])
                known_survivors = [s for s in raw_survivors if isinstance(s, int)][:128] if isinstance(raw_survivors, list) else []
                cleanup_info = {
                    "certainty": "uncertain",
                    "known_survivors": known_survivors,
                    "candidate_emitted": False,
                    "result_emitted": False,
                }
                meta["worker_cleanup"] = cleanup_info
                meta["resume_safety"] = "fresh_run_required"
                directory.write_json(f"{prefix}.meta.json", meta)
                if self._stage_accounting_state is not None:
                    self._stage_accounting_state["worker_cleanup"] = cleanup_info
                    self._stage_accounting_state["resume_safety"] = "fresh_run_required"
                    self._stage_accounting_state["blocking_reason"] = {
                        "code": "WORKER_TERMINATED_BEFORE_RESULT",
                        "detail": (
                            "worker terminated before result with uncertain cleanup; "
                            "fresh dispatch required after custody resolution"
                        ),
                    }
                if invocation_kind == "semantic":
                    self._record_stage_transport(stage, "worker_terminated_before_result")
                self.invocations[-1]["blocking_reason"] = "WORKER_TERMINATED_BEFORE_RESULT"
                self.display.stage_failed(
                    stage,
                    "worker terminated before result; uncertain cleanup requires fresh run",
                )
                if boundary is not None:
                    custody.close_boundary(boundary, ok=False)
                raise DispatchError(
                    f"stage {stage} worker terminated before result: uncertain cleanup requires fresh run",
                    "WORKER_TERMINATED_BEFORE_RESULT",
                )
            if invocation_kind == "semantic":
                self._record_stage_transport(stage, "worker_cleanup_failed")
            self.invocations[-1]["blocking_reason"] = "WORKER_CLEANUP_FAILED"
            self.display.stage_failed(stage, "stage worker cleanup could not be proven")
            if boundary is not None:
                custody.close_boundary(boundary, ok=False)
            raise DispatchError(
                f"stage {stage} worker cleanup failed: uncertain processes remain",
                "WORKER_CLEANUP_FAILED",
            )
        self.display.stage_finished(
            stage, result.exit_code, result.ended - result.started
        )
        if not result.ok:
            if boundary is not None:
                custody.close_boundary(boundary, ok=False, exit_code=result.exit_code)
            # A hard stdout overflow is an output-limit failure. An ordinary
            # nonzero exit remains a transport failure. Diagnostic stderr
            # truncation alone never reaches this branch, and elapsed time is
            # not a failure mode.
            detail = (
                f"exit={result.exit_code} truncated={result.truncated} "
                f"stderr_truncated={result.stderr_truncated}"
            )
            if endpoint.provider == PROVIDER_ANTIGRAVITY:
                reason = meta.get("antigravity_evidence", {}).get("provider_reason")
                reason_field = meta.get("antigravity_evidence", {}).get(
                    "provider_reason_field"
                )
                if reason:
                    detail += f" reason[{reason_field}]={str(reason)[:1000]}"
            self.display.stage_failed(stage, detail)
            code = (
                "PROVIDER_OUTPUT_LIMIT"
                if result.truncated
                else "PROVIDER_TRANSPORT_FAILED"
            )
            raise DispatchError(
                f"stage {stage} failed: {detail}", code
            )

        # Check native Git commit reconciliation before boundary close
        auth = (
            self._stage_accounting_state.get("native_git_authority")
            if isinstance(self._stage_accounting_state, dict)
            else None
        )
        is_auth_stage = bool(boundary is not None and auth and auth.get("authorized_stage") == stage)

        reported_obj = None
        if result.stdout:
            try:
                parsed_res = json.loads(result.stdout.decode("utf-8", "replace"))
                if isinstance(parsed_res, dict):
                    reported_obj = parsed_res
            except Exception:
                pass

        if is_auth_stage:
            post_stage_head = gitstate_module.current_head(self.cwd)
            entry_record = (
                self._stage_accounting_state.get("entry", {})
                if isinstance(self._stage_accounting_state, dict)
                else {}
            )
            expected_entry_head = (
                entry_record.get("head") if isinstance(entry_record, dict) else None
            )
            if post_stage_head != expected_entry_head:
                from . import native_git as native_git_module
                try:
                    transition = native_git_module.reconcile_native_transition(
                        self.cwd,
                        self._stage_accounting_state,
                        stage,
                        auth,
                        post_stage_head,
                        reported_result=reported_obj,
                    )
                    self._stage_accounting_state["native_git_transition"] = transition
                    self._stage_accounting_state.setdefault(
                        "stage_git_commit_delta", []
                    ).extend(transition.get("commit_chain", []))
                except native_git_module.NativeGitError as error:
                    if boundary is not None:
                        custody.close_boundary(boundary, ok=False, error=error)
                    self.invocations[-1]["blocking_reason"] = error.code
                    self.display.stage_failed(
                        stage, f"native git transition rejected: {error}"
                    )
                    raise DispatchError(str(error), error.code) from error
            elif reported_obj and (
                reported_obj.get("git_disposition", {}).get("commit")
                or reported_obj.get("commit")
            ):
                if boundary is not None:
                    custody.close_boundary(boundary, ok=False)
                raise DispatchError(
                    "claimed native commit missing: HEAD did not advance",
                    "NATIVE_COMMIT_MISSING",
                )
        else:
            if reported_obj and "git_disposition" in reported_obj:
                if boundary is not None:
                    custody.close_boundary(boundary, ok=False)
                raise DispatchError(
                    "unauthorized provider claimed native git commit",
                    "NATIVE_COMMIT_UNAUTHORIZED",
                )

        if boundary is not None:
            try:
                custody.close_boundary(boundary, ok=True, exit_code=result.exit_code)
            except gitstate_module.GitStateError as error:
                raise DispatchError(str(error), error.code) from error
        if invocation_kind == "semantic":
            self._record_stage_accounting("stage_transports_completed", stage)
        self._active_stage = None
        if (challenge_state is not None and self._entry_state is not None
                and invocation_kind == "semantic" and not read_only
                and stage in self.lifecycle.stage_names
                and self.lifecycle.stage(stage).is_mutating):
            try:
                ownership_challenge.observe(self.cwd, challenge_state, self._entry_state,
                    candidate_module.tree_identity(self.cwd)["tree"], stage,
                    "post_terminal" if stage == self.lifecycle.terminal_result_stage else "post_producer")
            except result_module.ResultError as error:
                raise DispatchError(str(error), error.code) from error
        return result, meta

    # -- result artifact ---------------------------------------------------

    def _update_invocation_accounting(self, state: dict[str, Any]) -> None:
        semantic_performed = sum(
            1 for record in self.invocations
            if record.get("invocation_kind", "semantic") == "semantic"
        )
        auxiliary_performed = sum(
            1 for record in self.invocations
            if record.get("invocation_kind") in ("auxiliary", "auxiliary_result_repair", "auxiliary_review_retry")
        )
        inherited_semantic = state.get("semantic_provider_invocations_inherited")
        if inherited_semantic is None:
            inherited_semantic = state.get("provider_invocations_inherited", 0)
        state["provider_invocations"] = len(self.invocations)
        state["semantic_provider_invocations_inherited"] = inherited_semantic
        state["semantic_provider_invocations_performed"] = semantic_performed
        state["auxiliary_provider_invocations"] = auxiliary_performed
        state["auxiliary_provider_invocations_performed"] = auxiliary_performed
        state["provider_invocations_inherited"] = inherited_semantic
        state["provider_invocations_performed"] = semantic_performed
        state["provider_invocations_effective"] = inherited_semantic + semantic_performed
        state["total_effective_provider_turns"] = (
            state["provider_invocations_effective"] + auxiliary_performed
            + state.get("auxiliary_provider_invocations_inherited", 0)
        )

    def _write_result(
        self, directory: run_module.RunDirectory, state: dict[str, Any]
    ) -> None:
        state["provider_evidence"] = list(self.provider_evidence)
        result_artifacts_module.write(directory, state, self.invocations)

    def _finalize(
        self,
        directory: run_module.RunDirectory,
        state: dict[str, Any],
        *,
        write_result: bool = True,
    ) -> archive_module.ArchiveError | None:
        """Write final artifacts, then seal exactly those bytes into the ZIP."""
        from . import outcomes
        outcomes.finish(state)
        self._update_invocation_accounting(state)
        state["provider_evidence"] = list(self.provider_evidence)
        state["shadow"] = self._shadow_state()
        state["archive_path"] = str(directory.archive_path)

        def write_artifacts() -> None:
            try:
                if write_result:
                    # Result preparation validates and aligns run-relative pointers;
                    # serialize the same validated fields into the resumable state.
                    self._write_result(directory, state)
            finally:
                directory.write_json("state.json", state)

        def finished():
            return self.display.finished(state, directory.path)
        return archive_module.finalize(directory, state, write_artifacts, finished)

    def dispatch(
        self,
        phase_id: str,
        request: PhaseRequest,
        lifecycle: str = LIFECYCLE_STANDARD,
        finalization_policy: str = FINALIZATION_PUBLISH,
        *, continue_from: Path | None = None,
        native_git_authority: Path | None = None,
        entry_adoption: Path | None = None,
    ) -> dict[str, Any]:
        options = [x for x in (continue_from, native_git_authority, entry_adoption) if x is not None]
        if len(options) > 1:
            raise DispatchError(
                "continue_from, native_git_authority, and entry_adoption are mutually exclusive",
                "MUTUALLY_EXCLUSIVE_OPTIONS",
            )
        self.lifecycle = get_lifecycle(lifecycle)
        self.finalization_policy = validate_finalization(finalization_policy)
        if continue_from is not None:
            adoption_module.proof.require_standard_environment()
        # A phase that could never bind a pre-final candidate must fail now, not
        # after four provider invocations have already been spent.
        candidate_module.require_worktree(self.cwd)
        repo_root = gitstate_module.repository_root(self.cwd).resolve()
        # Identity is validated before any state capture, so an unusable project
        # or phase name costs nothing and cannot reach a provider.
        project = run_module.project_name(repo_root)
        run_module.safe_component(phase_id, "phase id")
        # Entry state is captured before the first invocation so the phase delta
        # can later be separated from operator dirt that was already here. An
        # unsupported entry (staged index, unborn HEAD, submodule, unmerged path)
        # refuses here, with zero mutations and zero provider invocations spent.
        self._adoption = (adoption_module.prepare(continue_from,
            repo_root, phase_id, request)
            if continue_from is not None else None)

        self._native_git_authority = None
        if native_git_authority is not None:
            from . import native_git as native_git_module
            try:
                raw_text = Path(native_git_authority).read_text(encoding="utf-8")
                raw_auth = json.loads(raw_text)
                self._native_git_authority = native_git_module.validate_authority(
                    repo_root, raw_auth, phase_id=phase_id, request=request
                )
            except (native_git_module.NativeGitError, json.JSONDecodeError, OSError, ValueError) as error:
                code = getattr(error, "code", "NATIVE_GIT_AUTHORITY_INVALID")
                raise DispatchError(str(error), code) from error

        self._entry_adoption = None
        if entry_adoption is not None:
            from . import entry_adoption as entry_adoption_module
            try:
                raw_text = Path(entry_adoption).read_text(encoding="utf-8")
                raw_adopt = json.loads(raw_text)
                self._entry_adoption = entry_adoption_module.validate_strict_entry(
                    repo_root, raw_adopt, phase_id=phase_id, request=request
                )
            except (entry_adoption_module.EntryAdoptionError, json.JSONDecodeError, OSError, ValueError) as error:
                code = getattr(error, "code", "ENTRY_ADOPTION_INVALID")
                raise DispatchError(str(error), code) from error

        entry = gitstate_module.capture_entry(self.cwd)
        self.invocations = []
        self.provider_evidence = []
        self.telemetry_failures = []
        self.scan_rows = []
        self.prompt_policy_segments = []
        roster = load_validated_roster(self.root)
        resolved = resolve(
            request,
            self.root,
            self.lifecycle.name,
            self.finalization_policy,
            roster=roster,
        )
        endpoints = route(
            request, self.lifecycle, root=self.root, roster=roster
        )

        self.display.run_started(
            project, phase_id, request.phase_type, request.execution_mode,
            endpoints,
            lifecycle=self.lifecycle.name,
            finalization_policy=self.finalization_policy,
            review_count=self.lifecycle.expected_review_count,
        )
        directory = run_module.RunDirectory(self.run_root, project, phase_id,
            timestamp=self._adoption["timestamp"] if self._adoption else None)
        state_effective_routes = {
            k: {**v, "route_selecting_run_id": directory.run_id} if isinstance(v, dict) and v.get("route_selecting_run_id") is None else dict(v)
            for k, v in resolved.get("effective_stage_routes", {}).items()
        } if isinstance(resolved.get("effective_stage_routes"), dict) else resolved.get("effective_stage_routes")
        state: dict[str, Any] = {
            "run_layout": dict(directory.run_layout),
            "run_id": directory.run_id,
            "project": project,
            "phase_id": phase_id,
            "run_directory": str(directory.path),
            "dry_run": False,
            "phase_type": request.phase_type,
            "execution_mode": request.execution_mode,
            "lifecycle": self.lifecycle.name,
            "finalization_policy": self.finalization_policy,
            "effective_stage_routes": state_effective_routes,
            "route_transition": resolved.get("route_transition"),
            "expected_stages": list(self.lifecycle.stage_names),
            "expected_provider_invocations": (
                self.lifecycle.expected_provider_invocations
            ),
            "expected_review_count": self.lifecycle.expected_review_count,
            "terminal_result_stage": self.lifecycle.terminal_result_stage,
            "cwd": str(self.cwd),
            "checkpoints_completed": [],
            "stage_accounting_schema": (
                result_artifacts_module.STAGE_ACCOUNTING_SCHEMA
            ),
            "stages_invoked": [],
            "stage_transports_completed": [],
            "terminal_result_validated": False,
            "stages_completed": [],
            "entry": entry.as_dict(),
            "entry_dirt_identities": entry.dirty,
            "_previous_operational_metadata": stage_delta_module.scan_operational_metadata(entry.root),
            "final_head": entry.head,
            "phase_delta": [],
            "phase_owned_paths": [],
            "revision_paths": [],
            "terminal_transport": None,
            "finalization_attempted": False,
            "finalization_outcome": "not_attempted",
            "pre_final_candidate": None,
            "closeout_candidate": None,
            "terminal_candidate": None,
            "commit": None,
            "push": push_record(),
            "archive_path": str(directory.archive_path),
            "archive": archive_module.record(directory.archive_path),
            "prompt_policy": {
                "policy_version": prompt_policy_module.POLICY_VERSION,
                "sanitized": False,
                "total_removal_count": 0,
                "evidence_artifact": "prompt-policy.json",
            },
            "provider_outcomes": {},
            "review_outcomes": {},
            "outcome": None,
            "semantic_outcome": None,
            "blocking_reason": None,
            "complete": False,
            "manager_disposition_required": False,
            "shadow": self._shadow_state(),
            "entry_repository_identity": {
                "root": str(entry.root),
                "device": entry.root.stat().st_dev,
                "inode": entry.root.stat().st_ino,
                "context": ".",
            },
            "entry_worktree_dirt": entry.dirty,
            "entry_worktree_delta": list(entry.dirty.keys()) if isinstance(entry.dirty, dict) else list(entry.dirty),
            "entry_baseline": {
                "head": entry.head,
                "tree": entry.tree,
                "index": entry.index_identity,
                "dirty": entry.dirty,
            },
            "candidate_baseline": (
                {
                    "tree": self._entry_adoption["candidate_tree"],
                    "paths": list(self._entry_adoption["adopted_paths"]),
                    "manifest": self._entry_adoption["candidate_manifest"],
                }
                if self._entry_adoption is not None
                else None
            ),
            "adopted_candidate_identity": (
                self._entry_adoption["candidate_manifest"]
                if self._entry_adoption is not None
                else (self._adoption["candidate_manifest"] if self._adoption is not None else None)
            ),
            "stage_filesystem_delta": [],
            "stage_git_commit_delta": [],
            "external_evidence_delta": [],
            "publication_delta": [],
        }
        def checkpoint(name: str) -> None:
            state["checkpoints_completed"].append(name)

        def done(stage: str) -> None:
            if stage not in state["stages_completed"]:
                state["stages_completed"].append(stage)
            state["shadow"] = self._shadow_state()
            directory.write_json("state.json", state)

        try:
            if self._adoption is not None:
                state["adoption"] = self._adoption
                state["phase_owned_paths"] = sorted(adoption_module.paths(state))
                directory.write_json("adoption.json", self._adoption)
                adoption_module.prepare(continue_from, entry.root, phase_id, request)
            if self._native_git_authority is not None:
                state["native_git_authority"] = self._native_git_authority
                state["phase_owned_paths"] = sorted(set(self._native_git_authority["authorized_paths"]))
                directory.write_json("native-git-authority.json", self._native_git_authority)
            if self._entry_adoption is not None:
                state["entry_adoption"] = self._entry_adoption
                state["phase_owned_paths"] = sorted(set(self._entry_adoption["adopted_paths"]))
                state["candidate_manifest"] = self._entry_adoption["candidate_manifest"]
                directory.write_json("entry-adoption.json", self._entry_adoption)
            self._bind_stage_accounting(state, directory, entry=entry)
            self.display.artifacts(directory.path)
            self.display.scanner(
                self.scanner_executable is not None, self.scanner_version
            )
            directory.write_json("request.json", request.as_dict())
            directory.write_json("resolved.json", resolved)
            directory.write_json("entry-evidence.json", {
                **entry.as_dict(), "dirty": entry.dirty,
            })
            directory.write_json("state.json", state)
            return self._run_stages(
                request, directory, state, entry, endpoints, checkpoint, done
            )
        except BaseException as error:
            if state.pop("_finalized", False):
                raise
            # Every incomplete path lands here, so no run can end without a
            # recorded reason and a persisted artifact set. Mid-run failures that
            # are not DispatchError (a candidate that cannot be built, an
            # unreadable dirty path, a failed artifact write) must be recorded
            # too, or their absence reads as ambiguity rather than failure.
            state["complete"] = False
            state["outcome"] = "blocked"
            if state.get("semantic_outcome") is None:
                state["semantic_outcome"] = "blocked"
            if state.get("finalization_outcome") is None or state.get("finalization_outcome") == "not_attempted":
                if state.get("finalization_attempted"):
                    state["finalization_outcome"] = "blocked"
                else:
                    state["finalization_outcome"] = "not_attempted"
            if state["blocking_reason"] is None:
                state["blocking_reason"] = {
                    "code": getattr(error, "code", type(error).__name__),
                    "detail": str(error),
                }
            state["shadow"] = self._shadow_state()
            state["provider_invocations"] = len(self.invocations)
            try:
                failure_boundary_module.capture_mutating_boundary(
                    self, state, entry, self.lifecycle
                )
            except failure_boundary_module.FailureBoundaryError as capture_error:
                state["failure_candidate_capture"] = {
                    "status": "failed",
                    "code": capture_error.code,
                    "detail": capture_error.detail,
                }
                if capture_error.code == "ENTRY_DIRT_OVERLAP":
                    if state.get("blocking_reason") is None:
                        state["blocking_reason"] = {
                            "code": capture_error.code,
                            "detail": capture_error.detail,
                        }
            # The artifact write is best-effort: if the run is failing *because*
            # the run directory is unwritable, re-raising that instead of the
            # original cause would hide why the phase actually stopped.
            try:
                self._finalize(directory, state)
            except OSError:
                # Even when final state/result writes are the failing boundary,
                # honor the best-effort package-on-exit contract for whatever
                # durable run artifacts exist without displacing the primary
                # exception.
                try:
                    archive_module.create(directory)
                except archive_module.ArchiveError:
                    pass
                self.display.finished(state, directory.path)
            raise

    def resume(
        self,
        phase_id: str,
        request: PhaseRequest,
        source: Path,
        from_stage: str = "auto",
        *,
        lifecycle: str | None = None,
        finalization_policy: str | None = None,
        dry_run: bool = False,
        result_repair_commit_subject: str | None = None,
        result_repair_commit_body_file: Path | None = None,
    ) -> dict[str, Any]:
        """Create a new run that inherits one validated semantic prefix."""
        try:
            return resume_dispatch_module.start(
                self,
                phase_id,
                request,
                source,
                from_stage,
                lifecycle=lifecycle,
                finalization_policy=finalization_policy,
                dry_run=dry_run,
                result_repair_commit_subject=result_repair_commit_subject,
                result_repair_commit_body_file=result_repair_commit_body_file,
            )
        except (
            resume_module.ResumeError,
            finalization_module.FinalizationError,
            archive_module.ArchiveError,
        ) as error:
            raise DispatchError(
                getattr(error, "detail", str(error)),
                getattr(error, "code", type(error).__name__),
            ) from error

    def _terminal_contract(self, stage: str, begin: str, end: str) -> str:
        return lifecycle_dispatch_module.terminal_contract(stage, begin, end)

    def _complete_terminal(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return lifecycle_dispatch_module.complete_terminal(self, *args, **kwargs)

    def _run_solo(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return lifecycle_dispatch_module.run_solo(self, *args, **kwargs)

    def _run_plan_reviewed(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return lifecycle_dispatch_module.run_plan_reviewed(self, *args, **kwargs)

    def _run_work_reviewed(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return lifecycle_dispatch_module.run_work_reviewed(self, *args, **kwargs)

    def _run_stages(
        self,
        request: PhaseRequest,
        directory: run_module.RunDirectory,
        state: dict[str, Any],
        entry: gitstate_module.EntryState,
        endpoints: dict[str, Endpoint],
        checkpoint: Callable[[str], None],
        done: Callable[[str], None],
    ) -> dict[str, Any]:
        runners = {
            "standard": self._run_standard,
            "solo": self._run_solo,
            "plan-reviewed": self._run_plan_reviewed,
            "work-reviewed": self._run_work_reviewed,
        }
        return runners[self.lifecycle.name](
            request, directory, state, entry, endpoints, checkpoint, done
        )

    def _run_standard(
        self,
        request: PhaseRequest,
        directory: run_module.RunDirectory,
        state: dict[str, Any],
        entry: gitstate_module.EntryState,
        endpoints: dict[str, Endpoint],
        checkpoint: Callable[[str], None],
        done: Callable[[str], None],
    ) -> dict[str, Any]:
        plan_stage, plan_review_stage, work_stage, final_review_stage, closeout_stage = (
            self.lifecycle.stages
        )
        # A. planning
        task_prompt = self._sanitize(
            directory, state, "request.prompt", request.prompt
        )
        plan = self.plan_prompt(request, directory.run_id, task_prompt)
        try:
            capacity, self.stage_output_limits = (
                capacity_module.preflight_lifecycle_capacity(
                    self, request, directory.run_id, task_prompt, endpoints
                )
            )
            state["terminal_prompt_preflight"] = capacity
            ensure_prompt_fits(
                envelope_module.STAGE_PLAN,
                endpoints[envelope_module.STAGE_PLAN],
                plan,
            )
        except PromptLimitError as error:
            raise DispatchError(str(error), "PROVIDER_PROMPT_LIMIT") from error
        plan_before_tree = candidate_module.tree_identity(self.cwd)
        plan_before_index = gitstate_module.index_identity(self.cwd)
        plan_result, _ = self._stage(
            directory, 1, plan_stage.name, plan_stage.prefix, plan_stage.role,
            endpoints[envelope_module.STAGE_PLAN], plan, None,
            read_only=plan_stage.process_read_only,
        )
        stage_delta_module.normalize_index_if_needed(
            self.cwd, entry, plan_stage.name, state
        )
        plan_after_tree = candidate_module.tree_identity(self.cwd)
        plan_after_index = gitstate_module.index_identity(self.cwd)
        # Compatibility fallback for callers that substitute _stage. The common
        # StageBoundary owns normal attribution; an existing record is not recaptured.
        stage_delta_module.capture_stage_boundary(
            self.cwd,
            plan_stage.name,
            plan_before_tree,
            plan_before_index,
            plan_after_tree,
            plan_after_index,
            state,
        )
        plan_endpoint = endpoints[plan_stage.name]
        plan_material = lifecycle_dispatch_module.materialize_plan(
            directory,
            plan_result.stdout,
            plan_endpoint.provider,
            plan_endpoint.profile,
        )
        plan_binding = plan_material.binding
        state["plan_candidate"] = plan_binding
        state["proposal_binding"] = plan_binding
        state["plan_proposal_binding"] = plan_binding
        state["planner_proposal"] = {
            "binding": plan_binding,
            "artifact_name": "plan-material.md",
            "exact_bytes": True,
            "implementation_authority": False,
        }
        done(envelope_module.STAGE_PLAN)

        # B. plan review
        plan_review_before_tree = candidate_module.tree_identity(self.cwd)
        plan_review_before_index = gitstate_module.index_identity(self.cwd)
        plan_review_nonce = review_result_module.new_nonce()
        plan_review = self.review_prompt(
            envelope_module.STAGE_PLAN_REVIEW, request, directory.run_id,
            plan_binding, plan_material.data,
            task_prompt,
            review_result_module.contract(
                plan_review_stage.name, plan_review_nonce
            ),
        )
        plan_review_result, _ = self._stage(
            directory, 2, plan_review_stage.name, plan_review_stage.prefix,
            plan_review_stage.role, endpoints[envelope_module.STAGE_PLAN_REVIEW], plan_review,
            plan_binding,
            read_only=plan_review_stage.process_read_only,
        )
        stage_delta_module.normalize_index_if_needed(
            self.cwd, entry, plan_review_stage.name, state
        )
        plan_review_after_tree = candidate_module.tree_identity(self.cwd)
        plan_review_after_index = gitstate_module.index_identity(self.cwd)
        # Compatibility fallback for callers that substitute _stage. The common
        # StageBoundary owns normal attribution; an existing record is not recaptured.
        stage_delta_module.capture_stage_boundary(
            self.cwd,
            plan_review_stage.name,
            plan_review_before_tree,
            plan_review_before_index,
            plan_review_after_tree,
            plan_review_after_index,
            state,
        )
        parsed_plan_review = lifecycle_dispatch_module.complete_review(
            self, directory, state, plan_review_stage, plan_review_result,
            plan_review_nonce,
        )
        done(envelope_module.STAGE_PLAN_REVIEW)

        # C. work
        forwarded_plan_review = self._sanitize(
            directory,
            state,
            "plan_review.stdout.forwarded_to_work",
            parsed_plan_review.body,
        )
        current_product_at_work = candidate_module.tree_identity(self.cwd)
        stage_deltas_before_work = stage_delta_module.format_stage_deltas_summary(state)
        plan_review_finding_text = (
            f"Outcome: {parsed_plan_review.outcome} (advisory)\n\n"
            f"{forwarded_plan_review}"
        )
        work = self.continuation_prompt(
            envelope_module.STAGE_WORK, request, directory.run_id,
            envelope_module.WORK_ENVELOPE,
            [
                (
                    "Planner proposal binding (dispatcher-owned exact identity)",
                    json.dumps(plan_binding, sort_keys=True, separators=(",", ":")),
                ),
                (
                    "Planner proposal — exact bound bytes, to be dispositioned",
                    plan_material.data,
                ),
                ("Independent plan-review findings", plan_review_finding_text),
                (
                    "Current exact worktree product (dispatcher-owned binding)",
                    json.dumps(current_product_at_work, sort_keys=True, separators=(",", ":")),
                ),
                (
                    "Stage changes observed before production",
                    stage_deltas_before_work,
                ),
            ],
            include_task_prompt=True,
            task_prompt=task_prompt,
        )
        work_before_tree = current_product_at_work
        work_before_index = gitstate_module.index_identity(self.cwd)
        work_result, _ = self._stage(
            directory, 3, work_stage.name, work_stage.prefix, work_stage.role,
            endpoints[envelope_module.STAGE_WORK], work, None
        )
        stage_delta_module.normalize_index_if_needed(
            self.cwd, entry, work_stage.name, state
        )
        pre_final = candidate_module.tree_identity(self.cwd)
        work_after_index = gitstate_module.index_identity(self.cwd)
        # Compatibility fallback for callers that substitute _stage. The common
        # StageBoundary owns normal attribution; an existing record is not recaptured.
        stage_delta_module.capture_stage_boundary(
            self.cwd,
            work_stage.name,
            work_before_tree,
            work_before_index,
            pre_final,
            work_after_index,
            state,
        )
        state["pre_final_candidate"] = pre_final
        state["producer_binding"] = pre_final
        state["work_product_binding"] = pre_final
        state["producer_candidate"] = pre_final
        lifecycle_dispatch_module.record_producer_evidence(
            state,
            work_stage.name,
            work_result.stdout,
            closeout_stage.name,
            artifact_name=f"{work_stage.prefix}.stdout.md",
        )
        done(envelope_module.STAGE_WORK)

        # D. final review
        final_review_before_tree = candidate_module.tree_identity(self.cwd)
        final_review_before_index = gitstate_module.index_identity(self.cwd)
        final_review_nonce = review_result_module.new_nonce()
        final_review, prompt_decision = capacity_module.fit_optional_narrative(
            final_review_stage.name,
            endpoints[envelope_module.STAGE_FINAL_REVIEW],
            lambda material: self.review_prompt(
                envelope_module.STAGE_FINAL_REVIEW, request, directory.run_id,
                pre_final, material, task_prompt,
                review_result_module.contract(
                    final_review_stage.name, final_review_nonce
                ),
            ),
            work_result.stdout,
            source_stage=work_stage.name,
            artifact_basename=f"{work_stage.prefix}.stdout.md",
            artifact_bytes=work_result.stdout,
            mandatory_sources=(
                "original_scope",
                "producer_binding",
                "work_review_contract",
            ),
        )
        state.setdefault("prompt_capacity_decisions", []).append(prompt_decision)
        final_review_result, _ = self._stage(
            directory, 4, final_review_stage.name, final_review_stage.prefix,
            final_review_stage.role, endpoints[envelope_module.STAGE_FINAL_REVIEW], final_review,
            pre_final,
            read_only=final_review_stage.process_read_only,
        )
        stage_delta_module.normalize_index_if_needed(
            self.cwd, entry, final_review_stage.name, state
        )
        final_review_after_tree = candidate_module.tree_identity(self.cwd)
        final_review_after_index = gitstate_module.index_identity(self.cwd)
        # Compatibility fallback for callers that substitute _stage. The common
        # StageBoundary owns normal attribution; an existing record is not recaptured.
        stage_delta_module.capture_stage_boundary(
            self.cwd,
            final_review_stage.name,
            final_review_before_tree,
            final_review_before_index,
            final_review_after_tree,
            final_review_after_index,
            state,
        )
        parsed_final_review = lifecycle_dispatch_module.complete_review(
            self, directory, state, final_review_stage, final_review_result,
            final_review_nonce,
        )
        done(envelope_module.STAGE_FINAL_REVIEW)

        # E. closeout
        nonce = result_module.new_nonce()
        begin, end = result_module.markers(nonce)
        forwarded_final_review = self._sanitize(
            directory,
            state,
            "final_review.stdout.forwarded_to_closeout",
            parsed_final_review.body,
        )
        closeout_endpoint = endpoints[envelope_module.STAGE_CLOSEOUT]
        closer_entry_candidate = candidate_module.tree_identity(self.cwd)
        current_product = closer_entry_candidate
        state["closer_entry_candidate"] = closer_entry_candidate
        state["revisor_entry_candidate"] = closer_entry_candidate
        prior_stage_deltas = stage_delta_module.format_stage_deltas_summary(state)
        qualification_evidence = state.get("qualification_evidence")
        if not isinstance(qualification_evidence, str) or not qualification_evidence.strip():
            qualification_evidence = (
                "No separate dispatcher qualification record is available before closeout. "
                "The producer artifact is forwarded separately; report only task-scoped "
                "checks actually performed or an explicit verification limitation."
            )
        work_review_finding_text = (
            f"Outcome: {parsed_final_review.outcome} (advisory)\n\n"
            f"{forwarded_final_review}"
        )
        state["revisor_input"] = {
            "original_scope": {
                "kind": "task_prompt",
                "bytes": len(task_prompt.encode("utf-8")),
                "sha256": run_module.digest(task_prompt.encode("utf-8")),
            },
            "producer_binding": pre_final,
            "current_worktree_product": current_product,
            "producer_narrative": {
                "optional": True,
                "stage": work_stage.name,
                "artifact_basename": f"{work_stage.prefix}.stdout.md",
            },
            "work_review": {
                "artifact_name": f"{final_review_stage.prefix}.result.json",
                "stage": final_review_stage.name,
                "semantic_role": "work_review",
                "outcome": parsed_final_review.outcome,
            },
        }
        forwarded_work = self._sanitize(
            directory,
            state,
            "work.stdout.forwarded_to_closeout",
            work_result.stdout.decode("utf-8", "replace"),
        )
        try:
            closeout, prompt_decision = capacity_module.fit_optional_narrative(
                closeout_stage.name,
                closeout_endpoint,
                lambda material: self.closeout_prompt(
                    request,
                    directory.run_id,
                    task_prompt,
                    pre_final,
                    current_product,
                    material,
                    work_review_finding_text,
                    begin,
                    end,
                    stage_delta_summary=prior_stage_deltas,
                    qualification_evidence=qualification_evidence,
                ),
                forwarded_work,
                source_stage=work_stage.name,
                artifact_basename=f"{work_stage.prefix}.stdout.md",
                artifact_bytes=work_result.stdout,
                mandatory_sources=(
                    "original_scope",
                    "producer_binding",
                    "current_worktree_product",
                    "work_review_findings",
                    "stage_delta_summary",
                    "qualification_evidence",
                    "terminal_result_contract",
                ),
            )
        except PromptLimitError as error:
            raise DispatchError(str(error), "PROVIDER_PROMPT_LIMIT") from error
        state.setdefault("prompt_capacity_decisions", []).append(prompt_decision)
        closeout_before_tree = current_product
        closeout_before_index = gitstate_module.index_identity(self.cwd)
        closeout_result, _ = self._stage(
            directory, 5, closeout_stage.name, closeout_stage.prefix,
            closeout_stage.role, closeout_endpoint, closeout, pre_final,
        )
        stage_delta_module.normalize_index_if_needed(
            self.cwd, entry, closeout_stage.name, state
        )
        # Closeout legitimately mutates the worktree: it applies accepted
        # corrections. Re-derive the identity so the record never
        # implies the pre-final review covered these bytes.
        closeout_candidate = candidate_module.tree_identity(self.cwd)
        closeout_after_index = gitstate_module.index_identity(self.cwd)
        # Compatibility fallback for callers that substitute _stage. The common
        # StageBoundary owns normal attribution; an existing record is not recaptured.
        stage_delta_module.capture_stage_boundary(
            self.cwd,
            closeout_stage.name,
            closeout_before_tree,
            closeout_before_index,
            closeout_candidate,
            closeout_after_index,
            state,
        )
        state["closeout_candidate"] = closeout_candidate
        state["revisor_binding"] = closeout_candidate
        state["revisor_candidate"] = closeout_candidate
        state["terminal_candidate"] = closeout_candidate
        closer_mutated = closeout_candidate["tree"] != closer_entry_candidate["tree"]
        adversary_mutated = closer_entry_candidate["tree"] != pre_final["tree"]
        state["closeout_delta"] = {
            "changed": closer_mutated,
            "paths": candidate_module.tree_delta(
                self.cwd, str(closer_entry_candidate["tree"]), str(closeout_candidate["tree"])
            ),
            "note": (
                "Paths listed here changed during the closeout stage (after the pre_final review) "
                "and were therefore not covered by it."
            ),
        }
        state["cumulative_closeout_delta"] = {
            "changed": closeout_candidate["tree"] != pre_final["tree"],
            "paths": candidate_module.tree_delta(
                self.cwd, str(pre_final["tree"]), str(closeout_candidate["tree"])
            ),
            "note": (
                "Paths listed here changed after the pre_final review and were "
                "therefore not covered by it."
            ),
        }
        lifecycle_dispatch_module.record_revisor_revision(
            self,
            state,
            closer_entry_candidate,
            closeout_candidate,
            closeout_stage,
            final_review_stage.name,
        )
        state["final_candidate_reviewed"] = (
            (not adversary_mutated)
            and (not closer_mutated)
            and (closeout_candidate["tree"] == pre_final["tree"])
        )
        return self._complete_terminal(
            directory,
            state,
            entry,
            closeout_stage,
            closeout_result,
            nonce,
            endpoint=closeout_endpoint,
        )

    def dry_run(
        self,
        phase_id: str,
        request: PhaseRequest,
        lifecycle: str = LIFECYCLE_STANDARD,
        finalization_policy: str = FINALIZATION_PUBLISH,
        *, continue_from: Path | None = None,
        native_git_authority: Path | None = None,
        entry_adoption: Path | None = None,
    ) -> dict[str, Any]:
        options = [x for x in (continue_from, native_git_authority, entry_adoption) if x is not None]
        if len(options) > 1:
            raise DispatchError(
                "continue_from, native_git_authority, and entry_adoption are mutually exclusive",
                "MUTUALLY_EXCLUSIVE_OPTIONS",
            )
        repo_root = gitstate_module.repository_root(self.cwd).resolve()
        if continue_from is not None:
            adoption_module.proof.require_standard_environment()
            record = adoption_module.prepare(continue_from,
                repo_root, phase_id, request)
            return {"outcome": "dry_run", "dry_run": True,
                    "run_id": record["continuation_run_id"], "adoption": record,
                    "provider_invocations": 0, "provider_invocations_inherited": 0,
                    "resolved": resolve(request, self.root, lifecycle, finalization_policy)}
        if native_git_authority is not None:
            from . import native_git as native_git_module
            try:
                raw_text = Path(native_git_authority).read_text(encoding="utf-8")
                raw_auth = json.loads(raw_text)
                record = native_git_module.validate_authority(
                    repo_root, raw_auth, phase_id=phase_id, request=request
                )
            except (native_git_module.NativeGitError, json.JSONDecodeError, OSError, ValueError) as error:
                code = getattr(error, "code", "NATIVE_GIT_AUTHORITY_INVALID")
                raise DispatchError(str(error), code) from error
            return {
                "outcome": "dry_run",
                "dry_run": True,
                "phase_id": phase_id,
                "native_git_authority": record,
                "provider_invocations": 0,
                "provider_invocations_inherited": 0,
                "resolved": resolve(request, self.root, lifecycle, finalization_policy),
            }
        if entry_adoption is not None:
            from . import entry_adoption as entry_adoption_module
            try:
                raw_text = Path(entry_adoption).read_text(encoding="utf-8")
                raw_adopt = json.loads(raw_text)
                record = entry_adoption_module.validate_strict_entry(
                    repo_root, raw_adopt, phase_id=phase_id, request=request
                )
            except (entry_adoption_module.EntryAdoptionError, json.JSONDecodeError, OSError, ValueError) as error:
                code = getattr(error, "code", "ENTRY_ADOPTION_INVALID")
                raise DispatchError(str(error), code) from error
            return {
                "outcome": "dry_run",
                "dry_run": True,
                "phase_id": phase_id,
                "entry_adoption": record,
                "provider_invocations": 0,
                "provider_invocations_inherited": 0,
                "resolved": resolve(request, self.root, lifecycle, finalization_policy),
            }
        self._adoption = None
        self._native_git_authority = None
        self._entry_adoption = None
        return dry_run_module.run(
            self, phase_id, request, lifecycle, finalization_policy
        )
