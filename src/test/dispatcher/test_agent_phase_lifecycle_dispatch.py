from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import re
import subprocess
import time
from types import SimpleNamespace
import zipfile

import pytest

from agent_phase import lifecycle_dispatch as lifecycle_dispatch_module
from agent_phase import gitstate as gitstate_module
from agent_phase.dispatch import DispatchError, Dispatcher
from agent_phase.provider import Result
from agent_phase.request import PhaseRequest

from test_agent_phase_dispatch import ROOT, git, repository


__all__ = ["repository"]
REQUEST = PhaseRequest("implementation_testing", "codex_only", "Implement it.")


def terminal_payload(
    prompt: bytes,
    subject: str | None = "Apply lifecycle change",
    body: str = "task-scoped verification passed",
    path_dispositions: list[dict[str, str]] | None = None,
) -> bytes:
    text = prompt.decode()
    nonce = re.search(r"<<<AGENT-PHASE-RESULT ([0-9a-f]{32})>>>", text)
    stage = re.search(r"^stage: ([a-z_]+)$", text, re.MULTILINE)
    assert nonce is not None and stage is not None
    payload = json.dumps({
        "version": 1,
        "stage": stage.group(1),
        "outcome": "completed",
        "body": body,
        "commit_message": (
            None if subject is None else {"subject": subject, "body": ""}
        ),
        **({"path_dispositions": path_dispositions} if path_dispositions is not None else {}),
    })
    token = nonce.group(1)
    return (
        f"<<<AGENT-PHASE-RESULT {token}>>>\n{payload}\n"
        f"<<<END-AGENT-PHASE-RESULT {token}>>>\n"
    ).encode()


def review_payload(prompt: bytes, outcome: str = "reviewed_with_no_findings") -> bytes:
    text = prompt.decode()
    nonce = re.search(r"<<<AGENT-REVIEW-RESULT ([0-9a-f]{32})>>>", text)
    stage = re.search(r"^stage: ([a-z_]+)$", text, re.MULTILINE)
    assert nonce is not None and stage is not None
    payload = json.dumps({
        "version": 1,
        "stage": stage.group(1),
        "outcome": outcome,
        "body": "review body",
    })
    token = nonce.group(1)
    return (
        f"<<<AGENT-REVIEW-RESULT {token}>>>\n{payload}\n"
        f"<<<END-AGENT-REVIEW-RESULT {token}>>>\n"
    ).encode()


class LifecycleRunner:
    def __init__(
        self, mutate=None, fail_stage: str | None = None,
        subject: str | None = "Apply lifecycle change",
        review_outcome: str = "reviewed_with_no_findings",
        path_dispositions: list[dict[str, str]] | None = None,
    ) -> None:
        self.calls: list[dict[str, object]] = []
        self.mutate = mutate
        self.fail_stage = fail_stage
        self.subject = subject
        self.review_outcome = review_outcome
        self.path_dispositions = path_dispositions

    def __call__(self, argv, prompt, cwd, max_output, on_output=None):
        stage_match = re.search(rb"^stage: ([a-z_]+)$", prompt, re.MULTILINE)
        assert stage_match is not None
        stage = stage_match.group(1).decode()
        self.calls.append({"stage": stage, "argv": list(argv), "prompt": prompt})
        if self.mutate is not None:
            self.mutate(stage, cwd)
        if b"<<<AGENT-PHASE-RESULT " in prompt:
            stdout = terminal_payload(prompt, self.subject, path_dispositions=self.path_dispositions)
        elif b"<<<AGENT-REVIEW-RESULT " in prompt:
            stdout = review_payload(prompt, self.review_outcome)
        else:
            stdout = f"{stage} output".encode()
        now = time.time()
        failed = stage == self.fail_stage
        return Result(1 if failed else 0, stdout, b"failed" if failed else b"", False, now, now)


class NarrativeLifecycleRunner(LifecycleRunner):
    def __init__(self, body: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.body = body

    def __call__(self, argv, prompt, cwd, max_output, on_output=None):
        result = super().__call__(argv, prompt, cwd, max_output, on_output)
        if b"<<<AGENT-PHASE-RESULT " in prompt:
            return result._replace(stdout=terminal_payload(prompt, self.subject, self.body))
        return result


class LightweightInlineRepairRunner:
    def __init__(self) -> None:
        self.calls: list[bytes] = []

    def __call__(self, argv, prompt, cwd, max_output, on_output=None):
        self.calls.append(prompt)
        now = time.time()
        if prompt.startswith(b"Formatting-only terminal result repair."):
            stdout = terminal_payload(prompt.replace(b"terminal_stage:", b"stage:"))
        else:
            stdout = b"Completed solo work without the required result fence."
        return Result(0, stdout, b"", False, now, now)


def test_lightweight_resume_inline_repair_does_not_inflate_semantic_count(
    repository: Path, tmp_path: Path
) -> None:
    source_dispatcher = Dispatcher(
        ROOT,
        repository,
        run_root=tmp_path / "source",
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=LifecycleRunner(fail_stage="solo"),
    )
    with pytest.raises(DispatchError):
        source_dispatcher.dispatch(
            "LIFECYCLE", REQUEST, "solo", "checkpoint"
        )
    source = only_run(tmp_path / "source")
    runner = LightweightInlineRepairRunner()

    state = dispatcher(repository, tmp_path, runner).resume(
        "LIFECYCLE",
        REQUEST,
        source,
        "solo",
        lifecycle="solo",
        finalization_policy="checkpoint",
    )

    assert len(runner.calls) == 2
    assert state["provider_invocations_inherited"] == 0
    assert state["provider_invocations_performed"] == 1
    assert state["auxiliary_provider_invocations_performed"] == 1
    assert state["provider_invocations_effective"] == 1
    assert state["terminal_result_validated"] is True


@pytest.mark.parametrize(
    ("lifecycle", "terminal"),
    [
        ("standard", "closeout"),
        ("solo", "solo"),
        ("plan-reviewed", "produce_close"),
        ("work-reviewed", "revise_close"),
    ],
)
def test_dispatcher_terminal_contract_is_last_for_every_lifecycle(
    repository: Path, tmp_path: Path, lifecycle: str, terminal: str
) -> None:
    request = PhaseRequest(
        "implementation_testing",
        "codex_only",
        "bounded task\nEnd exactly with:\n<<<CUSTOM-TERMINAL-MARKER>>>",
    )
    runner = LifecycleRunner()

    dispatcher(repository, tmp_path, runner).dispatch(
        f"TERMINAL-{lifecycle}",
        request,
        lifecycle=lifecycle,
        finalization_policy="checkpoint",
    )

    prompt = next(call["prompt"] for call in runner.calls if call["stage"] == terminal)
    end = re.search(rb"<<<END-AGENT-PHASE-RESULT [0-9a-f]{32}>>>", prompt)
    assert end is not None
    assert prompt.rstrip().endswith(end.group(0))
    assert prompt.index(b"<<<CUSTOM-TERMINAL-MARKER>>>") < prompt.index(
        b"Earlier task and prior material"
    )


def test_terminal_narrative_fields_require_explicit_labels() -> None:
    body = (
        "Disposition: amend\n"
        "Rationale: accepted the review finding and corrected the implementation.\n"
        "Qualification evidence:\n"
        "python3 -m pytest -q tests/test_agent_phase_lifecycle_dispatch.py passed\n"
        "Unresolved concerns: external CI remains pending.\n"
    )
    assert lifecycle_dispatch_module.terminal_narrative_fields(body) == {
        "closer_disposition": "amend",
        "closer_rationale": (
            "accepted the review finding and corrected the implementation."
        ),
        "qualification_evidence": (
            "python3 -m pytest -q tests/test_agent_phase_lifecycle_dispatch.py passed"
        ),
        "unresolved_concerns": "external CI remains pending.",
    }
    assert lifecycle_dispatch_module.terminal_narrative_fields(
        "Completed after running the requested checks."
    ) == {
        "closer_disposition": None,
        "closer_rationale": None,
        "qualification_evidence": None,
        "unresolved_concerns": None,
    }


def test_terminal_narrative_is_handed_off_without_fabricated_fields(
    repository: Path, tmp_path: Path
) -> None:
    state = dispatcher(
        repository,
        tmp_path,
        NarrativeLifecycleRunner("Completed after running the requested checks."),
    ).dispatch("NARRATIVE", REQUEST, "solo", "checkpoint")

    assert state["closer_narrative"] == (
        "Completed after running the requested checks."
    )
    for key in (
        "closer_disposition",
        "closer_rationale",
        "qualification_evidence",
        "unresolved_concerns",
    ):
        assert state[key] is None
    run = Path(state["run_directory"])
    result = json.loads((run / "result.json").read_text())
    human = (run / "result.md").read_text()
    assert result["closer_narrative"] == state["closer_narrative"]
    assert result["closer_disposition"] is None
    assert result["qualification_evidence"] is None
    assert "closer disposition: **not explicitly reported**" in human
    assert "qualification evidence: not explicitly reported" in human
    assert "unresolved concerns: not explicitly reported" in human


def test_terminal_narrative_fields_and_producer_evidence_are_retained(
    repository: Path, tmp_path: Path
) -> None:
    body = (
        "Disposition: accept\n"
        "Rationale: the reviewed product is coherent.\n"
        "Qualification evidence: focused tests passed.\n"
        "Unresolved concerns: full CI is pending externally."
    )
    runner = NarrativeLifecycleRunner(body)
    state = dispatcher(
        repository,
        tmp_path,
        runner,
    ).dispatch("NARRATIVE", REQUEST, "work-reviewed", "checkpoint")

    assert state["closer_disposition"] == "accept"
    assert state["closer_rationale"] == "the reviewed product is coherent."
    assert state["qualification_evidence"] == "focused tests passed."
    assert state["unresolved_concerns"] == "full CI is pending externally."
    assert state["producer_evidence"]["stage"] == "produce"
    assert state["producer_evidence"]["forwarded_to"] == "revise_close"
    result = json.loads(
        Path(state["run_directory"]).joinpath("result.json").read_text()
    )
    assert result["closer_report"] == {
        "closer_disposition": "accept",
        "closer_rationale": "the reviewed product is coherent.",
        "qualification_evidence": "focused tests passed.",
        "unresolved_concerns": "full CI is pending externally.",
    }
    assert result["producer_evidence"] == state["producer_evidence"]
    terminal_prompt = next(
        call["prompt"] for call in runner.calls if call["stage"] == "revise_close"
    )
    assert b"produce output" in terminal_prompt


def test_require_unchanged_records_stage_name_for_unchanged_boundary(
    repository: Path,
) -> None:
    entry = gitstate_module.capture_entry(repository)
    state = {
        "entry": entry.as_dict(),
        "_previous_operational_metadata": {},
    }
    lifecycle_dispatch_module.require_unchanged(
        SimpleNamespace(cwd=repository),
        state,
        {"tree": entry.tree},
        "plan_review",
        entry.index_identity,
    )

    stage = state["stage_delta_ledger"]["stages"]["plan_review"]
    assert stage["stage"] == "plan_review"
    assert stage["before_tree"] == entry.tree
    assert stage["after_tree"] == entry.tree


def test_require_unchanged_normalizes_staged_metadata_before_capture(
    repository: Path,
) -> None:
    entry = gitstate_module.capture_entry(repository)
    metadata = repository / ".pytest_cache" / "index-only.txt"
    metadata.parent.mkdir(exist_ok=True)
    metadata.write_text("provider metadata\n", encoding="utf-8")
    git(repository, "add", os.fspath(metadata.relative_to(repository)))
    state = {
        "entry": entry.as_dict(),
        "_previous_operational_metadata": {},
    }

    lifecycle_dispatch_module.require_unchanged(
        SimpleNamespace(cwd=repository),
        state,
        {"tree": entry.tree},
        "plan_review",
        entry.index_identity,
    )

    assert metadata.is_file()
    assert "index-only.txt" not in subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=repository,
        capture_output=True,
        check=True,
        text=True,
    ).stdout
    stage = state["stage_delta_ledger"]["stages"]["plan_review"]
    assert stage["after_tree"] == entry.tree
    assert ".pytest_cache/index-only.txt" in stage["operational_metadata_paths"]


def dispatcher(repository: Path, tmp_path: Path, runner: LifecycleRunner) -> Dispatcher:
    return Dispatcher(
        ROOT,
        repository,
        run_root=tmp_path / "runs",
        codex_executable="/fake/codex",
        scanner_executable=None,
        resolve_scanner=False,
        runner=runner,
    )


def head(repository: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repository, check=True,
        capture_output=True, text=True,
    ).stdout.strip()


def remote_head(repository: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "origin/master"], cwd=repository, check=True,
        capture_output=True, text=True,
    ).stdout.strip()


def published_remote_head(repository: Path) -> str:
    return subprocess.run(
        ["git", "ls-remote", "origin", "refs/heads/master"], cwd=repository,
        check=True, capture_output=True, text=True,
    ).stdout.split()[0]


def only_run(run_root: Path) -> Path:
    states = list(run_root.rglob("state.json"))
    assert len(states) == 1
    return states[0].parent


def test_solo_checkpoint_is_one_invocation_and_never_mutates_git_metadata(
    repository: Path, tmp_path: Path
) -> None:
    before = head(repository)
    index_before = (repository / ".git/index").read_bytes()

    def mutate(stage: str, cwd: Path) -> None:
        assert stage == "solo"
        (cwd / "solo.txt").write_text("solo\n")

    runner = LifecycleRunner(mutate)
    state = dispatcher(repository, tmp_path, runner).dispatch(
        "LIFECYCLE", REQUEST, "solo", "checkpoint"
    )

    assert [call["stage"] for call in runner.calls] == ["solo"]
    assert state["expected_review_count"] == 0
    assert state["effective_checkpoints"] == []
    assert state["provider_invocations_effective"] == 1
    assert state["terminal_result_stage"] == "solo"
    assert state["manager_disposition_required"] is True
    assert state["completion_kind"] == "checkpoint_ready"
    assert state["push"]["status"] == "not_attempted_by_policy"
    assert state["commit"] is None and head(repository) == before
    assert (repository / ".git/index").read_bytes() == index_before
    assert (repository / "solo.txt").read_text() == "solo\n"


def test_checkpoint_allows_nonempty_delta_without_commit_message(
    repository: Path, tmp_path: Path
) -> None:
    def mutate(stage: str, cwd: Path) -> None:
        (cwd / "solo.txt").write_text("solo\n")

    state = dispatcher(
        repository, tmp_path, LifecycleRunner(mutate, subject=None)
    ).dispatch("LIFECYCLE", REQUEST, "solo", "checkpoint")

    assert state["complete"] is True
    assert state["proposed_commit_message"] is None
    assert state["manager_disposition_required"] is True


def test_solo_commit_local_commits_without_remote_contact(
    repository: Path, tmp_path: Path
) -> None:
    before_remote = remote_head(repository)

    def mutate(stage: str, cwd: Path) -> None:
        (cwd / "solo.txt").write_text("solo\n")

    state = dispatcher(repository, tmp_path, LifecycleRunner(mutate)).dispatch(
        "LIFECYCLE", REQUEST, "solo", "commit-local"
    )

    assert state["commit"] is not None
    assert state["push"]["status"] == "not_attempted_by_policy"
    assert remote_head(repository) == before_remote
    assert subprocess.run(
        ["git", "status", "--porcelain"], cwd=repository, check=True,
        capture_output=True, text=True,
    ).stdout == ""


def test_solo_publish_preserves_default_commit_and_push_behavior(
    repository: Path, tmp_path: Path
) -> None:
    def mutate(stage: str, cwd: Path) -> None:
        (cwd / "solo.txt").write_text("solo\n")

    state = dispatcher(repository, tmp_path, LifecycleRunner(mutate)).dispatch(
        "LIFECYCLE", REQUEST, "solo", "publish"
    )

    assert state["commit"] is not None
    assert state["push"]["succeeded"] is True
    assert state["completion_kind"] == "published"


@pytest.mark.parametrize("policy", ["checkpoint", "commit-local"])
def test_non_publish_policies_do_not_resolve_or_contact_remote(
    repository: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    policy: str,
) -> None:
    monkeypatch.setattr(
        gitstate_module, "push_target",
        lambda *args: pytest.fail("remote target resolved"),
    )
    monkeypatch.setattr(
        gitstate_module, "remote_head",
        lambda *args: pytest.fail("remote contacted"),
    )

    state = dispatcher(repository, tmp_path, LifecycleRunner()).dispatch(
        "LIFECYCLE", REQUEST, "solo", policy
    )

    assert state["push"]["attempted"] is False


def test_plan_reviewed_has_one_plan_review_and_terminal_producer(
    repository: Path, tmp_path: Path
) -> None:
    def mutate(stage: str, cwd: Path) -> None:
        if stage == "produce_close":
            (cwd / "change.txt").write_text("done\n")

    runner = LifecycleRunner(mutate)
    state = dispatcher(repository, tmp_path, runner).dispatch(
        "LIFECYCLE", REQUEST, "plan-reviewed", "checkpoint"
    )

    assert [call["stage"] for call in runner.calls] == [
        "plan", "plan_review", "produce_close",
    ]
    assert state["effective_checkpoints"] == ["post_planning"]
    assert state["terminal_result_stage"] == "produce_close"
    assert state["final_candidate_reviewed"] is False
    assert state["proposal_binding"] == state["plan_candidate"]
    assert state["plan_proposal_binding"] == state["plan_candidate"]
    result = json.loads(
        Path(state["run_directory"]).joinpath("result.json").read_text()
    )
    assert result["proposal_binding"] == state["plan_candidate"]
    assert result["plan_proposal_binding"] == state["plan_candidate"]
    terminal_prompt = runner.calls[2]["prompt"].decode()
    assert "Plan proposal binding (dispatcher-owned exact bytes)" in terminal_prompt
    assert "Planner proposal — exact bound bytes, to be dispositioned" in terminal_prompt
    assert "authoritative exact material" not in terminal_prompt
    assert "Independent plan review findings" in terminal_prompt
    assert "--reviewer" not in runner.calls[2]["argv"]


@pytest.mark.parametrize("read_only_stage", ["plan", "plan_review"])
def test_plan_reviewed_read_only_stages_are_byte_fenced(
    repository: Path, tmp_path: Path, read_only_stage: str
) -> None:
    def mutate(stage: str, cwd: Path) -> None:
        if stage == read_only_stage:
            (cwd / "forbidden.txt").write_text("mutation\n")

    runner = LifecycleRunner(mutate)
    if read_only_stage == "plan_review":
        with pytest.raises(DispatchError) as caught:
            dispatcher(repository, tmp_path, runner).dispatch(
                "LIFECYCLE", REQUEST, "plan-reviewed", "checkpoint"
            )
        assert caught.value.code == "READ_ONLY_STAGE_MUTATED_CANDIDATE"
        state = json.loads((only_run(tmp_path / "runs") / "state.json").read_bytes())
        assert runner.calls[-1]["stage"] == "plan_review"
    else:
        state = dispatcher(repository, tmp_path, runner).dispatch(
            "LIFECYCLE", REQUEST, "plan-reviewed", "checkpoint"
        )
    ledger = state.get("stage_delta_ledger", {})
    entry = ledger.get("stages", {}).get(read_only_stage)
    assert entry is not None
    assert "forbidden.txt" in entry["product_paths"]


@pytest.mark.parametrize(
    ("lifecycle", "read_only_stage"),
    [
        ("standard", "plan_review"),
        ("standard", "final_review"),
        ("plan-reviewed", "plan"),
        ("plan-reviewed", "plan_review"),
        ("work-reviewed", "work_review"),
    ],
)
def test_review_index_product_changes_block_without_materializing_blobs(
    repository: Path, tmp_path: Path, lifecycle: str, read_only_stage: str
) -> None:
    def mutate(stage: str, cwd: Path) -> None:
        if stage != read_only_stage:
            return
        blob = subprocess.run(
            ["git", "hash-object", "-w", "--stdin"], cwd=cwd,
            input=b"index only\n", capture_output=True, check=True,
        ).stdout.decode().strip()
        git(cwd, "update-index", "--add", "--cacheinfo", f"100644,{blob},index-only.txt")

    if read_only_stage == "plan":
        state = dispatcher(repository, tmp_path, LifecycleRunner(mutate)).dispatch(
            "LIFECYCLE", REQUEST, lifecycle, "checkpoint"
        )
    else:
        with pytest.raises(DispatchError) as caught:
            dispatcher(repository, tmp_path, LifecycleRunner(mutate)).dispatch(
                "LIFECYCLE", REQUEST, lifecycle, "checkpoint"
            )
        assert caught.value.code == "READ_ONLY_STAGE_MUTATED_INDEX"
        state = json.loads((only_run(tmp_path / "runs") / "state.json").read_bytes())
    normalizations = state.get("index_normalizations", [])
    assert any(n["stage"] == read_only_stage for n in normalizations)
    assert not (repository / "index-only.txt").exists()


def test_checkpoint_refuses_terminal_index_only_mutation(
    repository: Path, tmp_path: Path
) -> None:
    def mutate(stage: str, cwd: Path) -> None:
        if stage == "solo":
            git(cwd, "update-index", "--chmod=+x", "file.txt")

    state = dispatcher(repository, tmp_path, LifecycleRunner(mutate)).dispatch(
        "LIFECYCLE", REQUEST, "solo", "checkpoint"
    )
    normalizations = state.get("index_normalizations", [])
    assert any(n["stage"] == "solo" for n in normalizations)


def test_blocked_deletion_archive_reconstructs_binary_and_untracked_candidate(
    repository: Path, tmp_path: Path
) -> None:
    binary = bytes(range(256)) + b"\x00\xffcandidate"

    def mutate(stage: str, cwd: Path) -> None:
        if stage == "solo":
            (cwd / "file.txt").unlink()
            (cwd / "binary.dat").write_bytes(binary)
            (cwd / "untracked.txt").write_text("untracked\n", encoding="utf-8")

    state = dispatcher(
        repository, tmp_path, LifecycleRunner(mutate, subject=None, path_dispositions=[
            {"path": "file.txt", "disposition": "phase_owned"},
        ])
    ).dispatch("LIFECYCLE", REQUEST, "solo", "checkpoint")
    run_directory = Path(state["run_directory"])
    assert state['semantic_outcome'] == 'completed'
    assert state['finalization_outcome'] == 'blocked'
    assert state['finalization']['repair_class'] == 'requires_manager_ownership'
    assert not state['commit']
    patch = run_directory / "ownership-raw-candidate.patch"
    manifest_path = run_directory / "ownership-candidate-evidence.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert patch.stat().st_size == manifest['raw']['bytes']
    assert hashlib.sha256(patch.read_bytes()).hexdigest() == manifest['raw']['sha256']
    assert manifest['raw']['reconstruction_verified'] is True
    assert manifest['raw']['tree'] == state['raw_terminal_candidate']['tree']
    assert gitstate_module.candidate_manifest(repository, manifest['raw']['base_head'],
        manifest['raw']['tree'])['paths']['binary.dat']['sha256'] == hashlib.sha256(binary).hexdigest()
    result = json.loads((run_directory / "result.json").read_text(encoding="utf-8"))
    assert result['ownership_candidate_evidence'] == state['ownership_candidate_evidence']

    reconstructed = tmp_path / "reconstructed"
    subprocess.run(
        ["git", "clone", "-q", str(repository), str(reconstructed)], check=True
    )
    subprocess.run(
        ["git", "apply", "--index", "--binary", str(patch)],
        cwd=reconstructed, check=True,
    )
    tree = subprocess.run(
        ["git", "write-tree"], cwd=reconstructed,
        capture_output=True, check=True, text=True,
    ).stdout.strip()
    assert tree == state["final_tree"]

    with zipfile.ZipFile(state["archive_path"]) as archive:
        names = {Path(name).name for name in archive.namelist()}
    assert {patch.name, manifest_path.name} <= names


def test_checkpoint_excludes_unrelated_entry_dirt(
    repository: Path, tmp_path: Path
) -> None:
    (repository / "operator-notes.txt").write_text(
        "operator dirt\n", encoding="utf-8"
    )

    def mutate(stage: str, cwd: Path) -> None:
        if stage == "solo":
            (cwd / "phase.txt").write_text("phase candidate\n", encoding="utf-8")

    state = dispatcher(
        repository, tmp_path, LifecycleRunner(mutate, subject=None)
    ).dispatch("LIFECYCLE", REQUEST, "solo", "checkpoint")
    manifest = json.loads(
        (Path(state["run_directory"]) / "checkpoint-candidate-manifest.json")
        .read_text(encoding="utf-8")
    )

    assert manifest["schema"] == "agent-phase-checkpoint-candidate-v2"
    assert set(manifest["paths"]) == {"phase.txt"}
    assert manifest["checkpoint_tree"] != manifest["observed_terminal_tree"]
    assert (repository / "operator-notes.txt").read_text() == "operator dirt\n"


def test_empty_checkpoint_scope_does_not_import_unrelated_entry_dirt(
    repository: Path, tmp_path: Path
) -> None:
    (repository / "operator-notes.txt").write_text(
        "operator dirt\n", encoding="utf-8"
    )

    state = dispatcher(
        repository, tmp_path, LifecycleRunner(subject=None)
    ).dispatch("LIFECYCLE", REQUEST, "solo", "checkpoint")
    run_directory = Path(state["run_directory"])
    patch = (run_directory / "checkpoint-candidate.patch").read_bytes()
    manifest = json.loads(
        (run_directory / "checkpoint-candidate-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    head_tree = subprocess.run(
        ["git", "rev-parse", "HEAD^{tree}"], cwd=repository,
        capture_output=True, check=True, text=True,
    ).stdout.strip()

    assert patch == b""
    assert manifest["paths"] == {}
    assert manifest["checkpoint_tree"] == head_tree
    assert manifest["checkpoint_tree"] != manifest["observed_terminal_tree"]
    assert b"operator-notes.txt" not in patch


def test_checkpoint_treats_phase_paths_as_literal_git_pathspecs(
    repository: Path, tmp_path: Path
) -> None:
    (repository / "star1.txt").write_text("operator dirt\n", encoding="utf-8")

    def mutate(stage: str, cwd: Path) -> None:
        if stage == "solo":
            (cwd / "star[1].txt").write_text("phase candidate\n", encoding="utf-8")

    state = dispatcher(
        repository, tmp_path, LifecycleRunner(mutate, subject=None)
    ).dispatch("LIFECYCLE", REQUEST, "solo", "checkpoint")
    run_directory = Path(state["run_directory"])
    patch = (run_directory / "checkpoint-candidate.patch").read_bytes()
    manifest = json.loads(
        (run_directory / "checkpoint-candidate-manifest.json").read_text(
            encoding="utf-8"
        )
    )

    assert set(manifest["paths"]) == {"star[1].txt"}
    assert b"star1.txt" not in patch
    assert b"operator dirt" not in patch


def test_work_reviewed_binds_review_and_records_unreviewed_revision_delta(
    repository: Path, tmp_path: Path
) -> None:
    def mutate(stage: str, cwd: Path) -> None:
        if stage == "produce":
            (cwd / "change.txt").write_text("produced\n")
        elif stage == "revise_close":
            (cwd / "change.txt").write_text("revised\n")

    runner = LifecycleRunner(mutate)
    state = dispatcher(repository, tmp_path, runner).dispatch(
        "LIFECYCLE", REQUEST, "work-reviewed", "checkpoint"
    )

    assert [call["stage"] for call in runner.calls] == [
        "produce", "work_review", "revise_close",
    ]
    assert state["effective_checkpoints"] == ["post_work"]
    assert state["post_review_revision_delta"]["paths"] == ["change.txt"]
    assert state["final_candidate_reviewed"] is False
    assert state["producer_binding"] == state["produced_candidate"]
    assert state["work_product_binding"] == state["produced_candidate"]
    assert state["revisor_input"]["original_scope"]["kind"] == "task_prompt"
    assert state["revisor_input"]["producer_binding"] == state["produced_candidate"]
    assert state["revisor_input"]["current_worktree_product"] == state[
        "closer_entry_candidate"
    ]
    assert state["revisor_input"]["producer_narrative"]["optional"] is True
    assert state["revisor_input"]["work_review"]["outcome"] == (
        "reviewed_with_no_findings"
    )
    assert [artifact["stage"] for artifact in state["review_artifacts"]] == [
        "work_review"
    ]
    revision = state["authorized_revisor_revisions"]
    assert revision["authorized"] is True
    assert revision["paths"] == ["change.txt"]
    assert state["stage_delta_ledger"]["stages"]["work_review"]["product_paths"] == []
    assert revision["terminal_bytes_verified"] is True
    assert revision["independent_review_after_revision"] is False
    assert state["post_revisor_review"]["automatic"] is False
    review_prompt = runner.calls[1]["prompt"].decode()
    assert state["produced_candidate"]["tree"] in review_prompt
    terminal_prompt = runner.calls[2]["prompt"].decode()
    assert "Producer binding (dispatcher-owned exact product)" in terminal_prompt
    assert "Current worktree product (dispatcher-owned exact binding)" in terminal_prompt
    assert "Independent work review findings" in terminal_prompt
    assert "Producer narrative (optional whole artifact)" in terminal_prompt
    assert "There is no second independent review after your revision" in terminal_prompt
    result = json.loads(
        Path(state["run_directory"]).joinpath("result.json").read_text()
    )
    assert result["schema"] == "agent-phase-result-v4"
    assert result["review_artifact_names"] == ["02-work-review.result.json"]
    assert result["review_artifact_outcomes"] == {
        "work_review": "reviewed_with_no_findings",
    }
    assert result["producer_binding"] == state["produced_candidate"]
    assert result["work_product_binding"] == state["produced_candidate"]
    assert result["revisor_binding"] == state["revise_close_candidate"]
    assert result["authorized_revisor_revisions"]["paths"] == ["change.txt"]
    human = Path(state["run_directory"]).joinpath("result.md").read_text()
    assert "`02-work-review.result.json`: reviewed_with_no_findings" in human
    assert "authorized revisor revisions: 1 path(s)" in human
    assert "automatic post-revisor independent review: none" in human


def test_work_reviewed_advisory_findings_are_forwarded_without_hidden_review(
    repository: Path, tmp_path: Path
) -> None:
    def mutate(stage: str, cwd: Path) -> None:
        if stage == "produce":
            (cwd / "change.txt").write_text("produced\n")

    runner = LifecycleRunner(
        mutate, review_outcome="reviewed_with_findings"
    )
    state = dispatcher(repository, tmp_path, runner).dispatch(
        "ADVISORY", REQUEST, "work-reviewed", "checkpoint"
    )

    assert [call["stage"] for call in runner.calls] == [
        "produce", "work_review", "revise_close",
    ]
    assert state["review_artifact_outcomes"] == {
        "work_review": "reviewed_with_findings",
    }
    assert state["revisor_input"]["work_review"]["outcome"] == (
        "reviewed_with_findings"
    )
    terminal_prompt = runner.calls[2]["prompt"]
    assert b"review body" in terminal_prompt
    assert b"Independent work review findings" in terminal_prompt
    assert state["post_revisor_review"]["performed"] is False


def test_work_reviewed_reviewer_mutation_blocks(
    repository: Path, tmp_path: Path
) -> None:
    def mutate(stage: str, cwd: Path) -> None:
        if stage == "produce":
            (cwd / "change.txt").write_text("produced\n")
        elif stage == "work_review":
            (cwd / "reviewer.txt").write_text("forbidden\n")

    with pytest.raises(DispatchError) as caught:
        dispatcher(repository, tmp_path, LifecycleRunner(mutate)).dispatch(
            "LIFECYCLE", REQUEST, "work-reviewed", "checkpoint"
        )
    assert caught.value.code == "READ_ONLY_STAGE_MUTATED_CANDIDATE"
    state = json.loads((only_run(tmp_path / "runs") / "state.json").read_bytes())
    ledger = state.get("stage_delta_ledger", {})
    entry = ledger.get("stages", {}).get("work_review")
    assert entry is not None
    assert "reviewer.txt" in entry["product_paths"]


def test_checkpoint_to_commit_local_invokes_zero_providers(
    repository: Path, tmp_path: Path
) -> None:
    def mutate(stage: str, cwd: Path) -> None:
        (cwd / "solo.txt").write_text("solo\n")

    source_root = tmp_path / "source"
    source_dispatcher = Dispatcher(
        ROOT, repository, run_root=source_root, codex_executable="/fake/codex",
        scanner_executable=None, resolve_scanner=False,
        runner=LifecycleRunner(mutate),
    )
    source_dispatcher.dispatch("LIFECYCLE", REQUEST, "solo", "checkpoint")
    source = only_run(source_root)
    runner = LifecycleRunner()
    state = dispatcher(repository, tmp_path, runner).resume(
        "LIFECYCLE", REQUEST, source, "finalize",
        finalization_policy="commit-local",
    )

    assert runner.calls == []
    assert state["provider_invocations_performed"] == 0
    assert state["commit"] is not None
    assert state["push"]["status"] == "not_attempted_by_policy"


def test_commit_local_to_publish_reuses_commit_without_providers(
    repository: Path, tmp_path: Path
) -> None:
    def mutate(stage: str, cwd: Path) -> None:
        (cwd / "solo.txt").write_text("solo\n")

    source_root = tmp_path / "source"
    source_dispatcher = Dispatcher(
        ROOT, repository, run_root=source_root, codex_executable="/fake/codex",
        scanner_executable=None, resolve_scanner=False,
        runner=LifecycleRunner(mutate),
    )
    local = source_dispatcher.dispatch(
        "LIFECYCLE", REQUEST, "solo", "commit-local"
    )
    source = only_run(source_root)
    runner = LifecycleRunner()
    state = dispatcher(repository, tmp_path, runner).resume(
        "LIFECYCLE", REQUEST, source, "finalize",
        finalization_policy="publish",
    )

    assert runner.calls == []
    assert state["commit"]["sha"] == local["commit"]["sha"]
    assert state["push"]["succeeded"] is True
    assert published_remote_head(repository) == local["commit"]["sha"]


def test_commit_local_to_publish_records_accepted_unpushed_ancestor(
    repository: Path, tmp_path: Path
) -> None:
    (repository / "ancestor.txt").write_text("accepted ancestor\n")
    git(repository, "add", "ancestor.txt")
    git(repository, "commit", "-q", "-m", "Add accepted ancestor")

    def mutate(stage: str, cwd: Path) -> None:
        (cwd / "solo.txt").write_text("solo\n")

    source_root = tmp_path / "source"
    source_dispatcher = Dispatcher(
        ROOT, repository, run_root=source_root, codex_executable="/fake/codex",
        scanner_executable=None, resolve_scanner=False,
        runner=LifecycleRunner(mutate),
    )
    local = source_dispatcher.dispatch(
        "LIFECYCLE", REQUEST, "solo", "commit-local"
    )
    state = dispatcher(repository, tmp_path, LifecycleRunner()).resume(
        "LIFECYCLE", REQUEST, only_run(source_root), "finalize",
        finalization_policy="publish",
    )

    assert state["push"]["preexisting_unpushed_commit_count"] == 1
    assert published_remote_head(repository) == local["commit"]["sha"]


@pytest.mark.parametrize(
    ("lifecycle", "failed_stage", "resume_stage", "remaining", "checkpoint"),
    [
        ("solo", "solo", "solo", ["solo"], []),
        (
            "plan-reviewed", "plan_review", "plan-review",
            ["plan_review", "produce_close"], ["post_planning"],
        ),
        (
            "work-reviewed", "work_review", "work-review",
            ["work_review", "revise_close"], ["post_work"],
        ),
    ],
)
def test_lightweight_resume_runs_exact_remaining_suffix(
    repository: Path,
    tmp_path: Path,
    lifecycle: str,
    failed_stage: str,
    resume_stage: str,
    remaining: list[str],
    checkpoint: list[str],
) -> None:
    def mutate(stage: str, cwd: Path) -> None:
        if stage in ("solo", "produce", "produce_close", "revise_close"):
            (cwd / "change.txt").write_text(f"{stage}\n")

    source_root = tmp_path / "source"
    source_dispatcher = Dispatcher(
        ROOT, repository, run_root=source_root, codex_executable="/fake/codex",
        scanner_executable=None, resolve_scanner=False,
        runner=LifecycleRunner(mutate, fail_stage=failed_stage),
    )
    with pytest.raises(DispatchError):
        source_dispatcher.dispatch(
            "LIFECYCLE", REQUEST, lifecycle, "checkpoint"
        )
    source = only_run(source_root)
    runner = LifecycleRunner(mutate)

    state = dispatcher(repository, tmp_path, runner).resume(
        "LIFECYCLE", REQUEST, source, resume_stage,
        lifecycle=lifecycle, finalization_policy="checkpoint",
    )

    assert [call["stage"] for call in runner.calls] == remaining
    assert state["provider_invocations_performed"] == len(remaining)
    assert state["effective_checkpoints"] == checkpoint
    if lifecycle == "work-reviewed":
        assert [item["stage"] for item in state["review_artifacts"]] == [
            "work_review"
        ]
        assert state["review_artifact_outcomes"] == {
            "work_review": "reviewed_with_no_findings",
        }
        assert state["revisor_input"]["producer_binding"] == state[
            "producer_binding"
        ]
        assert state["revisor_input"]["current_worktree_product"] == state[
            "work_product_binding"
        ]
        assert state["authorized_revisor_revisions"]["terminal_bytes_verified"]
        assert state["post_revisor_review"]["performed"] is False


def test_resume_rejects_lifecycle_change_before_creating_run(
    repository: Path, tmp_path: Path
) -> None:
    source_root = tmp_path / "source"
    source_dispatcher = Dispatcher(
        ROOT, repository, run_root=source_root, codex_executable="/fake/codex",
        scanner_executable=None, resolve_scanner=False,
        runner=LifecycleRunner(fail_stage="solo"),
    )
    with pytest.raises(DispatchError):
        source_dispatcher.dispatch(
            "LIFECYCLE", REQUEST, "solo", "checkpoint"
        )

    with pytest.raises(DispatchError) as caught:
        dispatcher(repository, tmp_path, LifecycleRunner()).resume(
            "LIFECYCLE", REQUEST, only_run(source_root), "auto",
            lifecycle="standard",
        )

    assert caught.value.code == "RESUME_LIFECYCLE_MISMATCH"
    assert not (tmp_path / "runs").exists()


def test_result_and_dry_run_use_lifecycle_specific_truth(
    repository: Path, tmp_path: Path
) -> None:
    state = dispatcher(repository, tmp_path, LifecycleRunner()).dispatch(
        "LIFECYCLE", REQUEST, "solo", "checkpoint"
    )
    run = Path(state["run_directory"])
    result = json.loads((run / "result.json").read_text())
    human = (run / "result.md").read_text()

    assert result["schema"] == "agent-phase-result-v4"
    assert result["expected_stages"] == ["solo"]
    assert result["review_count"] == result["review_count_required"] == 0
    assert result["review_artifacts"] == []
    assert result["reviews"] == []
    assert result["proposal_binding"] is None
    assert result["producer_binding"] == result["candidates"]["terminal"]
    assert result["authorized_revisor_revisions"] is None
    assert result["post_revisor_review"]["automatic"] is False
    assert "reviews: 0 of 0" in human
    assert "review artifact outcomes: none" in human
    assert "automatic post-revisor independent review: none" in human
    assert "stages completed: 1 of 1" in human

    dry_root = tmp_path / "dry"
    dry = Dispatcher(
        ROOT, repository, run_root=dry_root, codex_executable="/fake/codex",
        scanner_executable=None, resolve_scanner=False,
        runner=LifecycleRunner(),
    ).dry_run("DRY", REQUEST, "work-reviewed", "checkpoint")
    assert dry["stages_rendered"] == ["produce"]
    assert dry["stages_not_rendered"] == ["work_review", "revise_close"]
    assert Path(dry["run_directory"]).joinpath("01-produce.prompt.md").is_file()
    revise_capacity = dry["terminal_prompt_preflight"]["stages"]["revise_close"]
    assert revise_capacity["mandatory_sources"] == [
        "original_scope",
        "producer_binding",
        "current_worktree_product",
        "work_review_findings",
        "terminal_result_contract",
    ]
    assert revise_capacity["optional_sources"] == ["producer_narrative"]
    assert revise_capacity["omission_scope"] == "whole_optional_artifact_only"


def test_finalize_only_rejects_policy_downgrade_before_new_archive(
    repository: Path, tmp_path: Path
) -> None:
    source_root = tmp_path / "source"
    source_dispatcher = Dispatcher(
        ROOT, repository, run_root=source_root, codex_executable="/fake/codex",
        scanner_executable=None, resolve_scanner=False,
        runner=LifecycleRunner(),
    )
    source_dispatcher.dispatch(
        "LIFECYCLE", REQUEST, "solo", "commit-local"
    )
    target_root = tmp_path / "target"
    target = Dispatcher(
        ROOT, repository, run_root=target_root, codex_executable="/fake/codex",
        scanner_executable=None, resolve_scanner=False,
        runner=LifecycleRunner(),
    )

    with pytest.raises(DispatchError) as caught:
        target.resume(
            "LIFECYCLE", REQUEST, only_run(source_root), "finalize",
            finalization_policy="checkpoint",
        )

    assert caught.value.code == "FINALIZATION_TRANSITION_INVALID"
    assert not target_root.exists()
