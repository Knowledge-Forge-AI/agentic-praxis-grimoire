"""Real Git capture-to-commit regressions for adopted tracked ignored product."""

from pathlib import Path
import subprocess

import pytest

from agent_phase import gitstate, ownership_cli
from agent_phase.finalization_recovery import recover
from test_agent_phase_path_dispositions import OwnershipRunner
from test_agent_phase_disposition_flow import PHASE_ID, REQUEST, git, make_dispatcher, repository as _repository

repository = _repository


FIXTURE = "src/test/fixtures/bulk/email_export/node_modules/ignored.js"


def track_ignored(root: Path) -> Path:
    (root / ".gitignore").write_text("node_modules/\n")
    fixture = root / FIXTURE
    fixture.parent.mkdir(parents=True)
    fixture.write_text("baseline fixture\n")
    git(root, "add", ".gitignore")
    git(root, "add", "-f", "--", f":(top,literal){FIXTURE}")
    git(root, "commit", "-qm", "Track intentional fixture")
    return fixture


@pytest.mark.parametrize("operation", ["modify", "delete"])
def test_exact_commit_of_tracked_ignored_preserves_operator_index(
    repository: Path, operation: str,
) -> None:
    fixture = track_ignored(repository)
    operator = repository / "operator.txt"
    operator.write_text("operator staged\n")
    git(repository, "add", "operator.txt")
    operator.write_text("operator unstaged\n")
    staged = git(repository, "ls-files", "--stage", "--", "operator.txt")
    branch = git(repository, "symbolic-ref", "HEAD")
    before = git(repository, "rev-parse", "HEAD")
    (repository / "new-product.txt").write_text("new accepted product\n")
    if operation == "modify":
        fixture.write_text("accepted fixture\n")
        fixture.chmod(0o755)
    else:
        fixture.unlink()

    commit = gitstate.commit(repository, [FIXTURE, "new-product.txt"], "Accept fixture\n")

    assert git(repository, "rev-parse", f"{commit}^") == before
    assert set(git(repository, "diff-tree", "-r", "--no-commit-id", "--name-only", commit).splitlines()) == {FIXTURE, "new-product.txt"}
    assert git(repository, "show", f"{commit}:new-product.txt") == "new accepted product"
    assert git(repository, "ls-files", "--stage", "--", "operator.txt") == staged
    assert operator.read_text() == "operator unstaged\n"
    assert git(repository, "symbolic-ref", "HEAD") == branch
    if operation == "modify":
        assert git(repository, "show", f"{commit}:{FIXTURE}") == "accepted fixture"
        assert git(repository, "ls-tree", commit, "--", FIXTURE).startswith("100755 ")
        assert fixture.read_text() == "accepted fixture\n"
        assert fixture.stat().st_mode & 0o111
    else:
        assert git(repository, "ls-tree", commit, "--", FIXTURE) == ""
        assert not fixture.exists()


@pytest.mark.parametrize("operation", ["modify", "delete"])
@pytest.mark.parametrize("review_outcome", ["reviewed_with_findings", "unreviewable"])
def test_advisory_closer_amendment_commits_ignored_product_and_reuses_commit(
    repository: Path, tmp_path: Path, operation: str, review_outcome: str,
) -> None:
    fixture = track_ignored(repository)
    operator = repository / "operator.txt"
    operator.write_text("independent operator work\n")
    operator.chmod(0o755)
    sibling = fixture.with_name("untracked.js")
    sibling.write_text("ignored sibling stays local\n")
    sibling_oid = git(repository, "hash-object", str(sibling))
    branch = git(repository, "symbolic-ref", "HEAD")
    upstream = git(repository, "rev-parse", "--symbolic-full-name", "@{upstream}")
    remote = git(repository, "rev-parse", "@{upstream}")
    before = git(repository, "rev-parse", "HEAD")
    count = int(git(repository, "rev-list", "--count", "HEAD"))

    def produce(cwd: Path, prompt: bytes) -> None:
        fixture.write_text("producer candidate\n")
        (cwd / "new-product.txt").write_text("reviewed new product\n")

    def amend_and_verify(cwd: Path, prompt: bytes) -> None:
        assert fixture.read_text() == "producer candidate\n"
        if operation == "modify":
            fixture.write_text("closer verified bytes\n")
            fixture.chmod(0o755)
            assert fixture.read_bytes() == b"closer verified bytes\n"
        else:
            fixture.unlink()
            assert not fixture.exists()
        (cwd / ".serena").mkdir(exist_ok=True)
        (cwd / ".serena" / "index.json").write_text("local metadata\n")

    runner = OwnershipRunner(
        hooks={2: produce, 4: amend_and_verify},
        review_outcomes={1: review_outcome, 3: review_outcome},
        dispositions=([{"path": FIXTURE, "disposition": "phase_owned"}]
                      if operation == "delete" else None),
    )
    dispatcher = make_dispatcher(repository, tmp_path, runner)
    state = dispatcher.dispatch(PHASE_ID, REQUEST, finalization_policy="commit-local")

    assert state["complete"] is True
    assert state["outcome"] == "completed"
    assert len(runner.calls) == 5
    assert state["final_candidate_reviewed"] is False
    assert state["closeout_delta"]["paths"] == [FIXTURE]
    assert state["authorized_revisor_revisions"]["terminal_bytes_verified"] is True
    assert state["authorized_revisor_revisions"]["independent_review_after_revision"] is False
    assert state["pre_final_candidate"] == state["closer_entry_candidate"]
    assert state["closeout_candidate"]["tree"] != state["pre_final_candidate"]["tree"]
    if operation == 'delete':
        assert state['semantic_outcome'] == 'completed'
        assert state['finalization']['repair_class'] == 'requires_manager_ownership'
        assert state['commit'] is None
        assert git(repository, 'rev-parse', 'HEAD') == before
        source = Path(state['run_directory'])
        challenge = state['ownership_challenges']['records'][0]
        assert challenge['boundary'] == 'post_terminal'
        resolution = tmp_path / 'ownership.json'
        ownership_cli._write_create_only(resolution, ownership_cli.create(
            source, repository, challenge['challenge_id'], 'phase_owned',
            'Manager accepts exact tracked ignored deletion'))
        recovered = recover(source, repository, ownership_resolutions=[resolution])
        assert recovered['provider_invocations'] == recovered['product_test_invocations'] == 0
        commit = recovered['finalization']['commit']['sha']
    else:
        commit = state["commit"]["sha"]
    assert git(repository, "rev-parse", f"{commit}^") == before
    assert int(git(repository, "rev-list", "--count", "HEAD")) == count + 1
    assert set(git(repository, "diff-tree", "-r", "--no-commit-id", "--name-only", commit).splitlines()) == {FIXTURE, "new-product.txt"}
    assert git(repository, "show", f"{commit}:new-product.txt") == "reviewed new product"
    assert state["push"]["attempted"] is False
    assert git(repository, "rev-parse", "@{upstream}") == remote
    assert git(repository, "symbolic-ref", "HEAD") == branch
    assert git(repository, "rev-parse", "--symbolic-full-name", "@{upstream}") == upstream
    assert operator.read_text() == "independent operator work\n"
    assert operator.stat().st_mode & 0o111
    assert (repository / ".serena" / "index.json").read_text() == "local metadata\n"
    assert sibling.read_text() == "ignored sibling stays local\n"
    assert subprocess.run(["git", "cat-file", "-e", sibling_oid], cwd=repository,
                          capture_output=True).returncode != 0
    if operation == "modify":
        assert fixture.read_text() == "closer verified bytes\n"
        assert git(repository, "ls-tree", commit, "--", FIXTURE).startswith("100755 ")
    else:
        assert not fixture.exists()

    def no_provider(*args, **kwargs):
        pytest.fail("finalize replay must not launch a provider")

    if operation == 'delete':
        replay = recover(source, repository, ownership_resolutions=[resolution])
        assert replay['finalization']['outcome'] == 'materialized'
        assert replay['finalization']['commit'] == commit
        assert not replay['git_mutation_performed']
        assert replay['provider_invocations'] == replay['product_test_invocations'] == 0
    else:
        replay = make_dispatcher(repository, tmp_path / "replay", no_provider).resume(
            PHASE_ID, REQUEST, Path(state["run_directory"]), "finalize",
            finalization_policy="commit-local",
        )
        assert replay["complete"] is True
        assert replay["commit"]["sha"] == commit
        assert replay["commit_reused"] is True
        assert replay["push"]["attempted"] is False
    assert int(git(repository, "rev-list", "--count", "HEAD")) == count + 1
    assert git(repository, "diff", "HEAD", "--", FIXTURE) == ""
