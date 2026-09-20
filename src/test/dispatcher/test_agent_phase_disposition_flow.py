from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
from typing import Any, Callable
import zipfile

import pytest

from agent_phase import candidate as candidate_module
from agent_phase.dispatch import DispatchError, Dispatcher
from agent_phase import gitstate as gitstate_module
from agent_phase.provider import Result
from agent_phase.request import PhaseRequest
from agent_phase import stage_delta as stage_delta_module


PHASE_ID = "DISPOSITION-TEST"
REQUEST = PhaseRequest("implementation_testing", "normal", "Implement disposition flow task.")


def write_fake_evidence(argv: list[str], exit_code: int) -> None:
    if "--evidence-prefix" not in argv:
        return
    prefix = Path(argv[argv.index("--evidence-prefix") + 1])
    path = prefix.with_name(f"{prefix.name}.antigravity-terminal-result.json")
    empty = {
        "text": "", "utf8_bytes": 0,
        "sha256": hashlib.sha256(b"").hexdigest(),
        "truncated": False, "source": None,
    }
    path.write_text(json.dumps({
        "schema": "antigravity-terminal-evidence-v2", "version": 2,
        "profile": argv[1], "model": argv[1],
        "reviewer": "--reviewer" in argv, "plan_mode": "--reviewer" in argv,
        "wrapper_exit_code": exit_code,
        "provider_record_observed": False,
        "terminal_result_observed": False,
        "terminal_record_kind": "no_terminal_event",
        "protocol_evidence_outcome": "no_terminal_event",
        "oversized_record_classification": None,
        "completion_fence_observed": exit_code == 0,
        "raw_result_artifact": None,
        "raw_result_absent_reason": "fake completion fence",
        "raw_result_bytes": 0, "raw_result_sha256": None,
        "normalized_status": "success" if exit_code == 0 else "error",
        "raw_status": None, "child_started": True,
        "child_exit_code": exit_code, "protocol_error": None,
        "reason_fields": {key: dict(empty) for key in (
            "error", "message", "reason", "cancel_reason", "cancellation_reason",
            "finish_reason", "termination_reason", "code", "error_code",
        )},
        "identifier_fields": {key: dict(empty) for key in (
            "conversation_id", "request_id", "session_id", "operation_id",
            "run_id", "turn_id",
        )},
        "preferred_reason": None,
    }) + "\n", encoding="utf-8")
    path.chmod(0o600)


def git(cwd: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments], cwd=cwd, capture_output=True, text=True, check=True
    )
    return completed.stdout.strip()


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "user.name", "Test")
    (root / "README.md").write_text("# Initial Repo\n")
    git(root, "add", "README.md")
    git(root, "commit", "-q", "-m", "initial commit")
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
    git(root, "remote", "add", "origin", str(remote))
    git(root, "push", "-q", "--set-upstream", "origin", "HEAD")
    return root


def closeout_payload(
    prompt: bytes,
    outcome: str = "completed",
    subject: str = "AGENTCENTRAL-DISPOSITION-FLOW1: Completed disposition phase",
    body: str = "All qualification tests passed: pytest -q passed with 100% green.",
) -> bytes:
    text = prompt.decode("utf-8")
    begin = re.search(r"<<<AGENT-PHASE-RESULT ([0-9a-f]{32})>>>", text)
    assert begin is not None, "closeout prompt did not carry a result nonce"
    nonce = begin.group(1)
    payload = {
        "version": 1,
        "stage": "closeout",
        "outcome": outcome,
        "body": body,
        "commit_message": {"subject": subject, "body": ""},
    }
    return (
        f"<<<AGENT-PHASE-RESULT {nonce}>>>\n"
        f"{json.dumps(payload)}\n"
        f"<<<END-AGENT-PHASE-RESULT {nonce}>>>\n"
    ).encode("utf-8")


def review_payload(
    prompt: bytes,
    stage: str,
    outcome: str = "reviewed_with_findings",
    body: str = "Advisory findings: consider updating documentation and tests.",
) -> bytes:
    match = re.search(rb"<<<AGENT-REVIEW-RESULT ([0-9a-f]{32})>>>", prompt)
    assert match is not None, "review prompt did not carry a review nonce"
    nonce = match.group(1).decode("ascii")
    payload = {"version": 1, "stage": stage, "outcome": outcome, "body": body}
    return (
        f"<<<AGENT-REVIEW-RESULT {nonce}>>>\n{json.dumps(payload)}\n"
        f"<<<END-AGENT-REVIEW-RESULT {nonce}>>>\n"
    ).encode("utf-8")


class DispositionFakeRunner:
    """Simulates provider stages with programmatic hooks to manipulate the worktree and index."""

    def __init__(
        self,
        hooks: dict[int, Callable[[Path, bytes], None]] | None = None,
        review_outcomes: dict[int, str] | None = None,
        closeout_subject: str = "AGENTCENTRAL-DISPOSITION-FLOW1: Completed disposition phase",
    ) -> None:
        self.calls: list[dict[str, Any]] = []
        self.hooks = hooks or {}
        self.review_outcomes = review_outcomes or {}
        self.closeout_subject = closeout_subject

    def __call__(self, argv: list[str], prompt: bytes, cwd: Path, max_output: int, on_output=None) -> Result:
        index = len(self.calls)
        self.calls.append({"argv": argv, "prompt": prompt, "cwd": cwd})

        if index in self.hooks:
            self.hooks[index](cwd, prompt)

        stage_match = re.search(rb"^stage: ([a-z_]+)$", prompt, re.MULTILINE)
        stage_name = stage_match.group(1).decode("ascii") if stage_match else ""

        if b"<<<AGENT-PHASE-RESULT " in prompt:
            stdout = closeout_payload(prompt, subject=self.closeout_subject)
        elif b"<<<AGENT-REVIEW-RESULT " in prompt:
            review_stage = stage_name or ("plan_review" if index == 1 else "final_review")
            outcome = self.review_outcomes.get(index, "reviewed_with_findings")
            stdout = review_payload(prompt, review_stage, outcome=outcome)
        elif stage_name == "plan" or index == 0:
            stdout = b"Plan: Implement new disposition flow with stage deltas."
        elif stage_name == "work" or index == 2:
            stdout = b"Produced: Added feature and unit tests with advisory review incorporated."
        else:
            stdout = f"stage-{index} stdout".encode("utf-8")

        started = time.time()
        exit_code = 0
        write_fake_evidence(list(argv), exit_code)
        return Result(
            exit_code=exit_code,
            stdout=stdout,
            stderr=b"",
            truncated=False,
            started=started,
            ended=started,
        )


ROOT = Path(__file__).resolve().parents[3]


def make_dispatcher(
    repository: Path,
    tmp_path: Path,
    runner: Any,
) -> Dispatcher:
    return Dispatcher(
        root=ROOT,
        cwd=repository,
        run_root=tmp_path / "runs",
        codex_executable="/fake/codex",
        claude_launcher="/fake/claude-profile",
        scanner_executable=None,
        resolve_scanner=False,
        runner=runner,
    )


# ==============================================================================
# Unit Tests
# ==============================================================================


def test_stage_delta_classification_and_attribution(repository: Path) -> None:
    """Verify that product changes and operational metadata are correctly classified."""
    # 1. Add product file and metadata files
    (repository / "src").mkdir()
    (repository / "src" / "main.py").write_text("print('hello')\n")
    (repository / ".serena").mkdir(parents=True)
    (repository / ".serena" / "memory.json").write_text("{}\n")
    (repository / ".scratch").mkdir(parents=True)
    (repository / ".scratch" / "temp.log").write_text("debug log\n")

    state: dict[str, Any] = {}
    entry_tree = gitstate_module.current_head(repository)
    after_candidate = candidate_module.tree_identity(repository)

    deltas = stage_delta_module.capture_stage_boundary(
        repository,
        state,
        stage="plan",
        before_tree=entry_tree,
        after_tree=after_candidate["tree"],
    )

    classifications = {d["path"]: d["classification"] for d in deltas}
    assert classifications["src/main.py"] == "product"
    assert classifications[".serena/memory.json"] == "operational_metadata"
    assert classifications[".scratch/temp.log"] == "operational_metadata"

    ledger = state["stage_delta_ledger"]
    stage_info = ledger["stages"]["plan"]
    assert "src/main.py" in stage_info["product_paths"]
    assert ".serena/memory.json" in stage_info["operational_metadata_paths"]


def test_tracked_metadata_looking_paths_remain_product(repository: Path) -> None:
    """Tracked files under metadata-like directories must be classified as product."""
    metadata_dir = repository / ".serena"
    metadata_dir.mkdir()
    tracked_file = metadata_dir / "tracked_config.json"
    tracked_file.write_text("{\"active\": true}\n")
    git(repository, "add", ".serena/tracked_config.json")
    git(repository, "commit", "-m", "Tracked config")

    before_tree = str(candidate_module.tree_identity(repository)["tree"])

    # Modify the tracked file
    tracked_file.write_text("{\"active\": false}\n")
    # Also add an untracked metadata file
    (metadata_dir / "untracked_cache.bin").write_bytes(b"\x00\x01\x02")

    after_tree = str(candidate_module.tree_identity(repository)["tree"])
    state: dict[str, Any] = {}
    deltas = stage_delta_module.capture_stage_boundary(
        repository,
        state,
        stage="work",
        before_tree=before_tree,
        after_tree=after_tree,
    )

    classifications = {d["path"]: d["classification"] for d in deltas}
    assert classifications[".serena/tracked_config.json"] == "product"
    assert classifications[".serena/untracked_cache.bin"] == "operational_metadata"


def test_bounded_handling_of_ignored_and_large_metadata_roots(repository: Path) -> None:
    """Scanning operational metadata must respect file count and depth bounds."""
    scratch = repository / ".scratch"
    scratch.mkdir()
    # Create files exceeding typical scan batching
    for i in range(120):
        (scratch / f"file_{i:03d}.tmp").write_text(f"data {i}\n")

    metadata = stage_delta_module.scan_operational_metadata(repository)
    # Metadata scan is bounded by max_files (50 files per root)
    assert len(metadata) == 50
    for path in metadata:
        assert path.startswith(".scratch/")


def test_producer_prompt_receives_separate_disposition_inputs(repository: Path, tmp_path: Path) -> None:
    """Verify the producer prompt receives the five explicit disposition options and distinct inputs."""
    prompts: list[str] = []

    def hook(index: int, prompt: bytes) -> None:
        if index == 2:  # work / produce stage
            prompts.append(prompt.decode("utf-8"))

    runner = DispositionFakeRunner(hooks={2: lambda cwd, p: hook(2, p)})
    dispatcher = make_dispatcher(repository, tmp_path, runner)
    dispatcher.dispatch(PHASE_ID, REQUEST, finalization_policy="checkpoint")

    assert len(prompts) == 1
    work_prompt = prompts[0]
    assert "The producer must explicitly choose one proposal disposition: accept, amend," in work_prompt
    assert "reject, defer, or supersede" in work_prompt
    assert "Planner proposal binding (dispatcher-owned exact identity)" in work_prompt
    assert "Planner proposal — exact bound bytes, to be dispositioned" in work_prompt
    assert "Independent plan-review findings" in work_prompt
    assert "Stage changes observed before production" in work_prompt


def test_closer_prompt_receives_separate_disposition_inputs(repository: Path, tmp_path: Path) -> None:
    """Verify closer prompt receives producer narrative, review findings, and stage deltas."""
    prompts: list[str] = []

    def hook(index: int, prompt: bytes) -> None:
        if index == 4:  # closeout stage
            prompts.append(prompt.decode("utf-8"))

    runner = DispositionFakeRunner(hooks={4: lambda cwd, p: hook(4, p)})
    dispatcher = make_dispatcher(repository, tmp_path, runner)
    dispatcher.dispatch(PHASE_ID, REQUEST, finalization_policy="checkpoint")

    assert len(prompts) == 1
    closeout_prompt = prompts[0]
    assert "The terminal producer/revisor is the final in-run dispositioner and may accept, amend," in closeout_prompt
    assert "reject, defer, or supersede" in closeout_prompt
    assert "Producer candidate binding (dispatcher-owned exact identity)" in closeout_prompt
    assert "Current exact worktree product (dispatcher-owned binding)" in closeout_prompt
    assert "Independent work-review findings" in closeout_prompt
    assert "Prior stage-delta summary (dispatcher-owned evidence)" in closeout_prompt


def test_advisory_review_findings_and_unreviewable(repository: Path, tmp_path: Path) -> None:
    """An 'unreviewable' adversarial review must be advisory and advance to completion."""
    runner = DispositionFakeRunner(review_outcomes={1: "unreviewable", 3: "unreviewable"})
    dispatcher = make_dispatcher(repository, tmp_path, runner)
    state = dispatcher.dispatch(PHASE_ID, REQUEST, finalization_policy="checkpoint")

    assert state["complete"] is True
    assert state["outcome"] == "completed"
    assert state["review_outcomes"] == {
        "plan_review": "unreviewable",
        "final_review": "unreviewable",
    }
    assert len(runner.calls) == 5


def test_recoverable_index_normalization(repository: Path) -> None:
    """A stage that stages files into the git index is safely normalized without losing worktree content."""
    entry_index = gitstate_module.index_identity(repository)

    # Provider stages a file in the real git index
    (repository / "staged_product.py").write_text("def run(): pass\n")
    git(repository, "add", "staged_product.py")
    assert gitstate_module.index_identity(repository) != entry_index
    (repository / "staged_product.py").write_text("def run(): return 42\n")

    state: dict[str, Any] = {}
    record = stage_delta_module.normalize_index_if_needed(
        repository, entry_index, state, stage_name="work"
    )

    assert record is not None
    assert record["restored_clean"] is True
    assert "staged_product.py" in record["staged_paths"]
    # The file must remain in the worktree
    assert (repository / "staged_product.py").read_text() == "def run(): return 42\n"
    # The index must be restored to clean state
    assert gitstate_module.index_identity(repository) == entry_index
    assert len(state["index_normalizations"]) == 1


def test_genuinely_ambiguous_git_state_blocks(repository: Path, tmp_path: Path) -> None:
    """Unmerged git conflicts or submodules must stop execution safely."""
    def create_conflict(cwd: Path, prompt: bytes) -> None:
        (cwd / "conflict.txt").write_text("conflict\n")
        h = subprocess.run(
            ["git", "hash-object", "-w", "conflict.txt"],
            cwd=cwd, capture_output=True, check=True
        ).stdout.decode().strip()
        subprocess.run(
            ["git", "update-index", "--index-info"],
            input=f"100644 {h} 1\tconflict.txt\n100644 {h} 2\tconflict.txt\n100644 {h} 3\tconflict.txt\n".encode(),
            cwd=cwd, check=True
        )

    runner = DispositionFakeRunner(hooks={1: create_conflict})
    dispatcher = make_dispatcher(repository, tmp_path, runner)

    with pytest.raises((DispatchError, gitstate_module.GitStateError)) as caught:
        dispatcher.dispatch(PHASE_ID, REQUEST, finalization_policy="checkpoint")

    assert caught.value.code == "READ_ONLY_STAGE_MUTATED_INDEX"
    assert git(repository, "ls-files", "--unmerged")
    assert (repository / "conflict.txt").read_text() == "conflict\n"
    source = next((tmp_path / "runs").rglob("state.json"))
    state = json.loads(source.read_bytes())
    invalidation = state["review_binding_invalidations"]["plan_review"]
    assert invalidation["candidate_observation_unavailable"] is True
    assert invalidation["paths_complete"] is False
    assert "unmerged paths" in invalidation["index_normalization_reason"]


# ==============================================================================
# Full End-to-End Lifecycle Tests
# ==============================================================================


def test_complete_standard_lifecycle_disposition_flow_9_steps(
    repository: Path, tmp_path: Path
) -> None:
    """Proves the canonical 9-step sequence of the disposition pipeline:
    1. Planner writes a proposal and creates operational metadata.
    2. Plan adversary emits findings and modifies a product doc file.
    3. Producer dispositions both, produces source and tests.
    4. Work adversary emits findings and modifies another product file.
    5. Revisor/closer dispositions work and review, qualifies, and closes.
    6. Phase completes without deadlock.
    7. Operational metadata remains in worktree but is absent from the commit.
    8. Product paths selected by closer are finalized exactly.
    9. Archive and result expose every stage artifact and delta.
    """
    def stage_hook(index: int, cwd: Path, prompt: bytes) -> None:
        if index == 0:
            # Step 1: Planner writes proposal and creates operational metadata
            (cwd / ".serena").mkdir(parents=True, exist_ok=True)
            (cwd / ".serena" / "project_index.json").write_text("{\"symbols\": 42}\n")
            (cwd / ".scratch").mkdir(parents=True, exist_ok=True)
            (cwd / ".scratch" / "scratchpad.txt").write_text("planning thoughts\n")

        elif index == 1:
            # Step 2: Plan review emits advisory findings and retains tool metadata.
            (cwd / ".serena" / "plan-review.json").write_text("{}\n")

        elif index == 2:
            # Step 3: Producer sees both, dispositions them, produces source and tests
            # Creates architecture.md and produces feature.py + test_feature.py.
            (cwd / "docs").mkdir()
            (cwd / "README.md").write_text("# Updated Repo with Feature Docs\n")
            (cwd / "docs" / "architecture.md").write_text("# Final Architecture (dispositioned by producer)\n")
            src = cwd / "src"
            src.mkdir(parents=True, exist_ok=True)
            (src / "feature.py").write_text("def execute_feature():\n    return 'success'\n")
            tests = cwd / "tests"
            tests.mkdir(parents=True, exist_ok=True)
            (tests / "test_feature.py").write_text("def test_ok(): assert True\n")
            # Also creates pytest cache
            (cwd / ".pytest_cache").mkdir(parents=True, exist_ok=True)
            (cwd / ".pytest_cache" / "cache.json").write_text("{}\n")

        elif index == 3:
            # Step 4: Work review emits findings and creates tool metadata.
            (cwd / ".claude" / ".cc-writes").mkdir(parents=True, exist_ok=True)
            (cwd / ".claude" / ".cc-writes" / "audit.json").write_text("{\"verified\": true}\n")

        elif index == 4:
            # Step 5: Closer accepts/amends, runs qualification, and closes
            (cwd / "docs" / "architecture.md").write_text(
                "# Final Architecture (dispositioned by producer & finalized by closer)\n"
            )

    runner = DispositionFakeRunner(
        hooks={i: lambda cwd, p, i=i: stage_hook(i, cwd, p) for i in range(5)},
        closeout_subject="AGENTCENTRAL-DISPOSITION-FLOW1: Completed full 9-step flow",
    )
    dispatcher = make_dispatcher(repository, tmp_path, runner)

    # Step 6: The phase completes rather than deadlocking
    state = dispatcher.dispatch(PHASE_ID, REQUEST, finalization_policy="publish")

    assert state["complete"] is True
    assert state["outcome"] == "completed"
    assert len(runner.calls) == 5
    assert state["closeout_delta"]["paths"] == ["docs/architecture.md"]
    assert state["authorized_revisor_revisions"]["paths"] == ["docs/architecture.md"]
    assert state["final_candidate_reviewed"] is False

    # Step 7: Operational metadata remains present in worktree but is ABSENT from the commit
    assert (repository / ".serena" / "project_index.json").is_file()
    assert (repository / ".scratch" / "scratchpad.txt").is_file()
    assert (repository / ".pytest_cache" / "cache.json").is_file()
    assert (repository / ".claude" / ".cc-writes" / "audit.json").is_file()

    commit_files = git(repository, "show", "--name-only", "--pretty=format:", "HEAD").splitlines()
    committed_paths = [f.strip() for f in commit_files if f.strip()]

    for path in committed_paths:
        assert not path.startswith(".serena/"), f"Unexpected metadata in commit: {path}"
        assert not path.startswith(".scratch/"), f"Unexpected metadata in commit: {path}"
        assert not path.startswith(".pytest_cache/"), f"Unexpected metadata in commit: {path}"
        assert not path.startswith(".claude/"), f"Unexpected metadata in commit: {path}"

    # Step 8: Product paths selected by the closer are finalized exactly
    expected_committed = {
        "docs/architecture.md",
        "src/feature.py",
        "tests/test_feature.py",
        "README.md",
    }
    assert set(committed_paths) == expected_committed

    # Step 9: The archive/result exposes every stage artifact and stage delta to the prompter
    run_dir = Path(state["run_directory"])
    result_json_path = run_dir / "result.json"
    result_md_path = run_dir / "result.md"

    assert result_json_path.is_file()
    assert result_md_path.is_file()

    result_data = json.loads(result_json_path.read_text(encoding="utf-8"))
    assert "stage_delta_ledger" in result_data
    assert "closer_disposition" in result_data
    assert "operational_metadata_paths" in result_data

    ledger = result_data["stage_delta_ledger"]
    stages_recorded = ledger["stages"]
    assert "plan" in stages_recorded
    assert "plan_review" in stages_recorded
    assert "work" in stages_recorded
    assert "final_review" in stages_recorded
    assert "closeout" in stages_recorded

    assert ".serena/project_index.json" in stages_recorded["plan"]["operational_metadata_paths"]
    assert stages_recorded["plan_review"]["product_paths"] == []
    assert "src/feature.py" in stages_recorded["work"]["product_paths"]
    assert stages_recorded["final_review"]["product_paths"] == []

    # Verify result.md structure has the 7 canonical human-facing sections
    result_md_text = result_md_path.read_text(encoding="utf-8")
    assert "## Phase and publication outcome" in result_md_text
    assert "## Closer disposition and rationale" in result_md_text
    assert "## Changed product paths and retained metadata paths" in result_md_text
    assert "## Qualification performed and its outcomes" in result_md_text
    assert "## Review outcomes and unresolved concerns" in result_md_text
    assert "## Manager attention items" in result_md_text
    assert "## Supporting identities and mechanical evidence" in result_md_text

    # Every product status line in the human report must agree with the
    # machine ledger for the same stage.  Derive the expected category counts
    # from result.json so this fails if Markdown falls back to all product
    # paths for a filtered category.
    stage_sections = {
        match.group(1): match.group(0)
        for match in re.finditer(
            r"#### Stage `([^`]+)`.*?(?=\n#### Stage `|\Z)",
            result_md_text,
            re.DOTALL,
        )
    }
    status_categories = {
        "additions": ("added", "A"),
        "modifications": (
            "modified", "M", "renamed", "R", "type_changed", "T"
        ),
        "deletions": ("deleted", "D"),
    }
    for stage_name, stage_info in stages_recorded.items():
        section = stage_sections[stage_name]
        status_counts = stage_info.get("classification_status_counts", {})
        product_counts = status_counts.get("product", {})
        assert isinstance(product_counts, dict)
        for category, statuses in status_categories.items():
            expected = sum(product_counts.get(status, 0) for status in statuses)
            match = re.search(
                rf"^- product {category} \((\d+)", section, re.MULTILINE
            )
            assert (match is not None) is (expected > 0), (
                stage_name,
                category,
                expected,
            )
            if match is not None:
                assert int(match.group(1)) == expected

    # Verify archive contains result artifacts
    archive_path = Path(state["archive_path"])
    assert archive_path.is_file()
    with zipfile.ZipFile(archive_path) as arc:
        names = arc.namelist()
        assert any(n.endswith("result.json") for n in names)
        assert any(n.endswith("result.md") for n in names)


def test_companion_closer_cannot_revert_invalidated_review(repository: Path, tmp_path: Path) -> None:
    """Observed review drift stops before a closer can conceal the changed bytes."""
    def review(cwd: Path, prompt: bytes) -> None:
        (cwd / "rogue_edit.txt").write_text("observed during review\n")
    def closeout(cwd: Path, prompt: bytes) -> None:
        pytest.fail("closer must not run after review drift")
    runner = DispositionFakeRunner(hooks={3: review, 4: closeout})
    with pytest.raises(DispatchError) as caught:
        make_dispatcher(repository, tmp_path, runner).dispatch(PHASE_ID, REQUEST, finalization_policy="publish")
    assert caught.value.code == "READ_ONLY_STAGE_MUTATED_CANDIDATE"
    assert (repository / "rogue_edit.txt").read_text() == "observed during review\n"
    source = next((tmp_path / "runs").rglob("state.json"))
    state = json.loads(source.read_bytes())
    assert "closeout" not in state["stages_invoked"]
    assert state["finalization_outcome"] == "not_attempted"


def test_companion_recoverable_staging_pollution(
    repository: Path, tmp_path: Path
) -> None:
    """Staging pollution introduced mid-phase is normalized and dispatch finishes cleanly."""
    def stage_hook(index: int, cwd: Path, prompt: bytes) -> None:
        if index == 1:  # plan review contaminates git index
            (cwd / ".serena").mkdir()
            (cwd / ".serena/cache").write_text("content\n")
            git(cwd, "add", ".serena/cache")

    runner = DispositionFakeRunner(hooks={1: lambda c, p: stage_hook(1, c, p)})
    dispatcher = make_dispatcher(repository, tmp_path, runner)
    state = dispatcher.dispatch(PHASE_ID, REQUEST, finalization_policy="checkpoint")

    assert state["complete"] is True
    assert len(state.get("index_normalizations", [])) >= 1
    assert state["index_normalizations"][0]["stage"] == "plan_review"


def test_companion_interruption_resume_retains_ledger(
    repository: Path, tmp_path: Path
) -> None:
    """Interrupted runs preserve prior stage deltas and resumed runs retain them."""
    class FailingRunner(DispositionFakeRunner):
        def __call__(self, argv, prompt, cwd, max_output, on_output=None):
            index = len(self.calls)
            if index == 1:
                # Plan review records informational tool metadata
                (cwd / ".serena").mkdir()
                (cwd / ".serena/review_note.md").write_text("note\n")
            if index == 2:
                # Fail at work stage
                self.calls.append({"argv": argv, "prompt": prompt, "cwd": cwd})
                write_fake_evidence(list(argv), 1)
                return Result(1, b"", b"provider crashed", False, time.time(), time.time())
            return super().__call__(argv, prompt, cwd, max_output, on_output)

    runner = FailingRunner()
    dispatcher = make_dispatcher(repository, tmp_path / "source", runner)
    with pytest.raises(DispatchError):
        dispatcher.dispatch(PHASE_ID, REQUEST)

    source_dir = next(
        path for path in (tmp_path / "source" / "runs").rglob(f"*{PHASE_ID}*") if path.is_dir() and (path / "state.json").exists()
    )

    def resumed_work(cwd: Path, prompt: bytes) -> None:
        (cwd / "resumed.py").write_text("new resumed stage bytes\n")
    resume_runner = DispositionFakeRunner(hooks={0: resumed_work})
    resume_dispatcher = make_dispatcher(repository, tmp_path / "resumed", resume_runner)
    resumed = resume_dispatcher.resume(PHASE_ID, REQUEST, source_dir, finalization_policy="checkpoint")

    assert resumed["outcome"] == "completed"
    assert "stage_delta_ledger" in resumed
    # Check that stage delta from plan_review was carried forward
    ledger = resumed["stage_delta_ledger"]
    assert "plan_review" in ledger["stages"]
    assert ".serena/review_note.md" in ledger["stages"]["plan_review"]["operational_metadata_paths"]

    assert ledger["stages"]["work"]["product_paths"] == ["resumed.py"]


def test_companion_pre_existing_operator_dirt_preserved(
    repository: Path, tmp_path: Path
) -> None:
    """Operator dirty worktree files before phase start must remain untouched."""
    operator_file = repository / "operator_wip.txt"
    operator_file.write_text("wip work not for this phase\n")

    runner = DispositionFakeRunner()
    dispatcher = make_dispatcher(repository, tmp_path, runner)
    state = dispatcher.dispatch(PHASE_ID, REQUEST, finalization_policy="publish")

    assert state["complete"] is True
    # Operator file must still exist with unchanged content
    assert operator_file.read_text() == "wip work not for this phase\n"
    # Operator file must NOT be in the phase commit
    commit_files = git(repository, "show", "--name-only", "--pretty=format:", "HEAD").splitlines()
    assert "operator_wip.txt" not in commit_files


def test_staged_rename_and_intent_to_add_preserve_current_bytes(repository: Path) -> None:
    entry_index = gitstate_module.index_identity(repository)
    git(repository, "mv", "README.md", "Updated.md")
    (repository / "Updated.md").write_text("later unstaged edit\n")
    (repository / "intent.py").write_text("intent content\n")
    git(repository, "add", "-N", "intent.py")
    record = stage_delta_module.normalize_index_if_needed(
        repository, entry_index, {}, stage_name="work"
    )
    assert record["stage"] == "work"
    assert {c["path"]: c["status"] for c in record["staged_changes"]} == {
        "README.md": "D", "Updated.md": "A", "intent.py": "intent_to_add"
    }
    assert (repository / "Updated.md").read_text() == "later unstaged edit\n"
    assert (repository / "intent.py").read_text() == "intent content\n"
    assert not (repository / "README.md").exists()
    assert gitstate_module.index_identity(repository) == entry_index


def test_implicit_candidate_capture_and_tracking_are_honest(repository: Path) -> None:
    before = candidate_module.tree_identity(repository)
    (repository / "new.py").write_text("new product\n")
    state = {}
    first = stage_delta_module.capture_stage_boundary(repository, state, stage="plan", before_tree=before)
    added = next(d for d in first if d["path"] == "new.py")
    assert added["tracked_before"] is False
    assert added["tracked_after"] is True
    boundary = candidate_module.tree_identity(repository)
    assert stage_delta_module.capture_stage_boundary(repository, state, stage="plan_review", before_tree=boundary) == []
    (repository / "new.py").write_text("later product\n")
    later = stage_delta_module.capture_stage_boundary(repository, state, stage="work", before_tree=boundary)
    assert later[0]["introduced_by_stage"] == "work"
    assert later[0]["tracked_before"] is True


def test_metadata_observation_is_bounded_and_does_not_follow_external_ancestor(repository: Path, tmp_path: Path) -> None:
    external = tmp_path / "external"
    (external / ".cc-writes").mkdir(parents=True)
    (external / ".cc-writes" / "private").write_text("not observed")
    (repository / ".claude").symlink_to(external, target_is_directory=True)
    scratch = repository / ".scratch"
    scratch.mkdir()
    for i in range(100):
        sub = scratch / str(i)
        sub.mkdir()
        (sub / "data").write_text("data")
    observation = {}
    found = stage_delta_module.scan_operational_metadata(repository, observation=observation)
    assert len(found) <= 50
    assert not any(p.startswith(".claude/") for p in found)
    assert set(observation["omitted_roots"]) == {".scratch", ".claude/.cc-writes"}
    state = {}
    tree = candidate_module.tree_identity(repository)
    stage_delta_module.capture_stage_boundary(repository, state, stage="plan", before_tree=tree, after_tree=tree)
    summary = state["stage_delta_ledger"]["stages"]["plan"]
    assert summary["observation_completeness"] == "truncated"
    assert summary["observation_limitations"]["classification"] == "external_or_unobserved"


def test_preexisting_metadata_is_not_attributed_to_planner(repository: Path, tmp_path: Path) -> None:
    (repository / ".serena").mkdir()
    (repository / ".serena" / "preexisting").write_text("retained")
    state = make_dispatcher(repository, tmp_path, DispositionFakeRunner()).dispatch(
        PHASE_ID, REQUEST, finalization_policy="checkpoint"
    )
    assert not any(d["path"] == ".serena/preexisting" for d in state["stage_delta_ledger"]["deltas"])


def test_standard_lifecycle_through_fake_provider_processes(repository: Path, tmp_path: Path) -> None:
    """Real provider subprocess transport, repository changes and qualification."""
    import sys
    from agent_phase import provider

    script = tmp_path / "fake_provider.py"
    script.write_text(r'''import json, re, subprocess, sys
from pathlib import Path
prompt = sys.stdin.read()
stage = re.search(r"^stage: ([a-z_]+)$", prompt, re.M).group(1)
if stage == "plan":
    Path(".serena").mkdir()
    Path(".serena/cache").write_text("local metadata")
    print("Proposal: return 42 and protect it with a test.")
elif stage == "work":
    assert "Proposal: return 42" in prompt
    assert "Advisory: retain the rationale" in prompt
    assert ".serena/cache" in prompt and ".serena/plan-review.md" in prompt
    assert Path(".serena/plan-review.md").read_text() == "adversary rationale"
    Path("plan-review.md").write_text("accepted rationale")
    Path("work-review.md").write_text("redundant producer note")
    Path("feature.py").write_text("def answer(): return 42\n")
    Path("test_feature.py").write_text("from feature import answer\nassert answer() == 42\n")
    print("Disposition: amend proposal using the adversary rationale; qualification awaits closer.")
elif stage == "closeout":
    assert "amend proposal" in prompt and "Advisory: retain the rationale" in prompt
    for path in (".serena/cache", "plan-review.md", "feature.py", "work-review.md"):
        assert path in prompt and Path(path).exists()
    Path("work-review.md").unlink()
    subprocess.run([sys.executable, "test_feature.py"], check=True)
    nonce = re.search(r"<<<AGENT-PHASE-RESULT ([0-9a-f]{32})>>>", prompt).group(1)
    body = {"version": 1, "stage": stage, "outcome": "completed",
            "body": "Amend: retain plan rationale, reject redundant work-review file. Ran python test_feature.py: passed. No unresolved concerns.",
            "commit_message": {"subject": "Implement tested answer", "body": ""}}
    print(f"<<<AGENT-PHASE-RESULT {nonce}>>>\n" + json.dumps(body) + f"\n<<<END-AGENT-PHASE-RESULT {nonce}>>>")
else:
    name = ".serena/plan-review.md" if stage == "plan_review" else ".serena/work-review.md"
    Path(name).write_text("adversary rationale")
    nonce = re.search(r"<<<AGENT-REVIEW-RESULT ([0-9a-f]{32})>>>", prompt).group(1)
    body = {"version": 1, "stage": stage, "outcome": "reviewed_with_findings", "body": "Advisory: retain the rationale"}
    print(f"<<<AGENT-REVIEW-RESULT {nonce}>>>\n" + json.dumps(body) + f"\n<<<END-AGENT-REVIEW-RESULT {nonce}>>>")
''')
    calls = []
    def process_runner(argv, prompt, cwd, max_output, on_output=None):
        calls.append(argv)
        result = provider.run([sys.executable, str(script)], prompt, cwd, max_output, on_output)
        write_fake_evidence(list(argv), result.exit_code)
        return result

    state = make_dispatcher(repository, tmp_path, process_runner).dispatch(
        PHASE_ID, REQUEST, finalization_policy="commit-local"
    )
    assert state["complete"] and len(calls) == 5
    assert set(git(repository, "show", "--name-only", "--pretty=format:", "HEAD").splitlines()) == {
        "feature.py", "test_feature.py", "plan-review.md"
    }
    assert (repository / ".serena/cache").read_text() == "local metadata"
    assert not (repository / "work-review.md").exists()
    ledger = state["stage_delta_ledger"]
    assert set(ledger["stages"]) == {"plan", "plan_review", "work", "final_review", "closeout"}
    assert any(d["path"] == "work-review.md" and d["status"] == "deleted" for d in ledger["deltas"])
    with zipfile.ZipFile(state["archive_path"]) as archive:
        names = archive.namelist()
        for fragment in ("plan", "plan-review", "work", "final-review", "closeout"):
            assert any(fragment in name for name in names)


def test_candidate_does_not_hash_untracked_metadata(repository: Path) -> None:
    cache = repository / ".scratch" / "unique-cache"
    cache.parent.mkdir()
    cache.write_bytes(b"unique operational cache contents not for git objects")
    blob = git(repository, "hash-object", str(cache))
    candidate_module.tree_identity(repository)
    assert subprocess.run(["git", "cat-file", "-e", blob], cwd=repository, capture_output=True).returncode != 0
    assert cache.read_bytes() == b"unique operational cache contents not for git objects"


def test_resume_boundary_normalizes_staged_metadata_before_candidate_capture(repository: Path) -> None:
    from types import SimpleNamespace
    from agent_phase import lifecycle_dispatch

    entry = gitstate_module.capture_entry(repository)
    before = candidate_module.tree_identity(repository)
    cache = repository / ".serena" / "new-cache"
    cache.parent.mkdir()
    cache.write_text("provider cache")
    git(repository, "add", "-f", ".serena/new-cache")
    state = {"entry": entry.as_dict()}
    lifecycle_dispatch.require_unchanged(
        SimpleNamespace(cwd=repository), state, before, "plan_review", entry.index_identity
    )
    assert state["index_normalizations"][0]["stage"] == "plan_review"
    boundary = state["stage_delta_ledger"]["stages"]["plan_review"]
    assert boundary["after_tree"] == before["tree"]
    assert boundary["product_paths"] == []
    assert boundary["operational_metadata_paths"] == [".serena/new-cache"]
    assert cache.read_text() == "provider cache"


def test_restored_tracked_product_keeps_tracking_evidence(repository: Path) -> None:
    (repository / "README.md").unlink()
    before = candidate_module.tree_identity(repository)
    (repository / "README.md").write_text("restored tracked product")
    deltas = stage_delta_module.capture_stage_boundary(repository, {}, stage="closeout", before_tree=before)
    assert deltas[0]["status"] == "added"
    assert deltas[0]["tracked_before"] is False
    assert deltas[0]["tracked_after"] is True


@pytest.mark.parametrize("restore", [False, True])
def test_provider_branch_switch_with_other_upstream(repository: Path, tmp_path: Path, restore: bool) -> None:
    entry_branch = git(repository, "branch", "--show-current")
    head = git(repository, "rev-parse", "HEAD")
    remote_before = git(repository, "ls-remote", "origin")

    def switch(cwd: Path, prompt: bytes) -> None:
        git(cwd, "checkout", "-b", "other-branch")
        git(cwd, "config", "branch.other-branch.remote", "origin")
        git(cwd, "config", "branch.other-branch.merge", "refs/heads/other-upstream")
        assert git(cwd, "rev-parse", "HEAD") == head
        (cwd / "feature.py").write_text("product\n")

    def close(cwd: Path, prompt: bytes) -> None:
        if restore:
            git(cwd, "checkout", entry_branch)

    runner = DispositionFakeRunner(hooks={2: switch, 4: close})
    dispatcher = make_dispatcher(repository, tmp_path, runner)
    if restore:
        state = dispatcher.dispatch(PHASE_ID, REQUEST, finalization_policy="commit-local")
        assert state["repository_finalized"] is True
        assert git(repository, "branch", "--show-current") == entry_branch
        assert git(repository, "rev-parse", "HEAD") != head
    else:
        with pytest.raises(DispatchError) as caught:
            dispatcher.dispatch(PHASE_ID, REQUEST, finalization_policy="publish")
        assert caught.value.code == "GIT_AUTHORITY_BRANCH_MISMATCH"
        state = json.loads(next((tmp_path / "runs").rglob("state.json")).read_text())
        assert state["manager_disposition_required"] is True
        assert set(state["candidate_manifest"]["paths"]) == {"feature.py"}
        assert state["commit"] is None
        assert git(repository, "rev-parse", "HEAD") == head
    assert git(repository, "ls-remote", "origin") == remote_before
    assert state["stage_delta_ledger"]["stages"]["work"]["git_authority_paths"]
    assert len(runner.calls) == 5
    result_md = Path(state["run_directory"], "result.md").read_text()
    assert "other-branch" in result_md


def test_active_operation_preserves_candidate_and_stage_event(repository: Path, tmp_path: Path) -> None:
    head = git(repository, "rev-parse", "HEAD")
    def hook(cwd: Path, prompt: bytes) -> None:
        (cwd / "feature.py").write_text("preserve me\n")
        (cwd / ".git" / "MERGE_HEAD").write_text(head + "\n")
    runner = DispositionFakeRunner(hooks={2: hook})
    with pytest.raises((DispatchError, gitstate_module.GitStateError)) as caught:
        make_dispatcher(repository, tmp_path, runner).dispatch(PHASE_ID, REQUEST)
    assert caught.value.code == "ENTRY_ACTIVE_GIT_OPERATION"
    state = json.loads(next((tmp_path / "runs").rglob("state.json")).read_text())
    assert state["failure_candidate"]["tree"]
    assert "active_git_operation" in state["manager_attention_reasons"]
    assert "feature.py" in state["failure_candidate"]["candidate_paths"]
    assert state["stage_delta_ledger"]["stages"]["work"]["git_authority_paths"]
    assert git(repository, "rev-parse", "HEAD") == head


def test_failed_stage_only_entry_dirt_keeps_manager_attention(repository: Path, tmp_path: Path) -> None:
    from agent_phase import failure_boundary, lifecycle
    from types import SimpleNamespace
    (repository / "README.md").write_text("operator bytes\n")
    entry = gitstate_module.capture_entry(repository)
    (repository / "README.md").write_text("failed provider bytes\n")
    state = {"stages_invoked": ["work"]}
    failure_boundary.capture_mutating_boundary(
        SimpleNamespace(_active_stage="work"), state, entry,
        lifecycle.get_lifecycle("standard"), "work",
    )
    assert state["phase_owned_paths"] == []
    assert state["manager_disposition_required"] is True
    assert "entry_dirt_overlap" in state["manager_attention_reasons"]
    assert state["failure_candidate"]["candidate_paths"] == ["README.md"]


@pytest.mark.parametrize("interrupted", [False, True])
def test_failed_provider_product_metadata_and_index_survive(repository: Path, tmp_path: Path, interrupted: bool) -> None:
    class Failed(DispositionFakeRunner):
        def __call__(self, argv, prompt, cwd, max_output, on_output=None):
            if len(self.calls) != 2:
                return super().__call__(argv, prompt, cwd, max_output, on_output)
            self.calls.append({"argv": argv, "prompt": prompt, "cwd": cwd})
            (cwd / "failed.py").write_text("preserved\n")
            (cwd / ".scratch").mkdir()
            (cwd / ".scratch" / "failed-log").write_text("metadata\n")
            git(cwd, "add", "-N", "failed.py")
            if interrupted:
                raise KeyboardInterrupt("injected interruption")
            write_fake_evidence(list(argv), 7)
            return Result(7, b"", b"failure", False, time.time(), time.time())
    before_index = gitstate_module.index_identity(repository)
    with pytest.raises((DispatchError, KeyboardInterrupt)):
        make_dispatcher(repository, tmp_path, Failed()).dispatch(PHASE_ID, REQUEST)
    state = json.loads(next((tmp_path / "runs").rglob("state.json")).read_text())
    assert state["blocking_reason"]["code"] == ("KeyboardInterrupt" if interrupted else "PROVIDER_TRANSPORT_FAILED")
    assert state["failure_candidate"]["stage"] == "work"
    assert state["failure_candidate"]["candidate_paths"] == ["failed.py"]
    stage = state["stage_delta_ledger"]["stages"]["work"]
    assert stage["product_paths"] == ["failed.py"]
    assert stage["operational_metadata_paths"] == [".scratch/failed-log"]
    assert state["index_normalizations"][0]["intent_to_add_paths"] == ["failed.py"]
    assert gitstate_module.index_identity(repository) == before_index
    assert (repository / "failed.py").read_text() == "preserved\n"


def test_large_real_delta_finalizes_complete_paths(repository: Path, tmp_path: Path) -> None:
    inline_limit = stage_delta_module.MAX_STAGE_INLINE_DELTAS
    count = inline_limit + 44
    omitted = count - inline_limit
    paths = {f"file-{i:04}.txt" for i in range(count)}
    def hook(cwd: Path, prompt: bytes) -> None:
        for name in sorted(paths):
            (cwd / name).write_text(name + "\n")
    state = make_dispatcher(repository, tmp_path, DispositionFakeRunner(hooks={2: hook})).dispatch(
        PHASE_ID, REQUEST, finalization_policy="commit-local"
    )
    summary = state["stage_delta_ledger"]["stages"]["work"]
    assert summary["observation_completeness"] == "truncated"
    assert summary["omitted_deltas_count"] == omitted
    assert summary["product_paths_total_count"] == count
    assert summary["product_paths_inline_count"] == inline_limit
    assert summary["product_paths_omitted_count"] == omitted
    assert set(state["candidate_manifest"]["paths"]) == paths
    assert set(git(repository, "show", "--name-only", "--pretty=format:", "HEAD").splitlines()) == paths

    run = Path(state["run_directory"])
    result_json = json.loads((run / "result.json").read_text(encoding="utf-8"))
    result_summary = result_json["stage_delta_ledger"]["stages"]["work"]
    assert len(result_summary["product_paths"]) == inline_limit
    assert result_summary["product_paths_total_count"] == count
    assert result_summary["product_paths_omitted_count"] == omitted
    assert set(result_json["candidate_manifest"]["paths"]) == paths
    result_md = (run / "result.md").read_text(encoding="utf-8")
    assert (
        f"product additions ({count}; "
        f"{inline_limit} inline, {omitted} omitted)"
        in result_md
    )


def test_closer_cannot_accept_unreviewed_product_drift(repository: Path, tmp_path: Path) -> None:
    def review(cwd: Path, prompt: bytes) -> None:
        (cwd / "README.md").write_text("concurrent bytes\n")
    with pytest.raises(DispatchError) as caught:
        make_dispatcher(repository, tmp_path, DispositionFakeRunner(hooks={3: review})).dispatch(
            PHASE_ID, REQUEST, finalization_policy="checkpoint"
        )
    assert caught.value.code == "READ_ONLY_STAGE_MUTATED_CANDIDATE"
    source = next((tmp_path / "runs").rglob("state.json"))
    state = json.loads(source.read_bytes())
    assert state["stage_delta_ledger"]["stages"]["final_review"]["product_paths"] == ["README.md"]
    assert not state.get("authorized_revisor_revisions")
    assert "pre_final" not in state["checkpoints_completed"]


def test_ledger_error_cannot_replace_primary_provider_failure(repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original = stage_delta_module._record_deltas_to_ledger
    def persist(state, stage_name, *args, **kwargs):
        if stage_name == "work":
            raise OSError("injected ledger persistence failure")
        return original(state, stage_name, *args, **kwargs)
    monkeypatch.setattr(stage_delta_module, "_record_deltas_to_ledger", persist)
    def fail(cwd: Path, prompt: bytes) -> None:
        (cwd / "preserved.py").write_text("provider bytes\n")
        raise RuntimeError("injected primary provider failure")
    with pytest.raises(RuntimeError, match="injected primary provider failure"):
        make_dispatcher(repository, tmp_path, DispositionFakeRunner(hooks={2: fail})).dispatch(PHASE_ID, REQUEST)
    directory = next((tmp_path / "runs").rglob("state.json")).parent
    state = json.loads((directory / "state.json").read_text())
    result = json.loads((directory / "result.json").read_text())
    assert state["blocking_reason"]["code"] == "RuntimeError"
    assert state["stage_delta_capture_error"]["code"] == "OSError"
    assert state["failure_candidate"]["candidate_paths"] == ["preserved.py"]
    assert result["blocking_reason"] == state["blocking_reason"]
    assert result["stage_delta_capture_error"] == state["stage_delta_capture_error"]
