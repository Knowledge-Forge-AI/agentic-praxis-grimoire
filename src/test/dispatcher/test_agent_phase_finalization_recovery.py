"""Recovery uses real Git objects and never executes a provider."""

import json
import os
from pathlib import Path
import subprocess

import pytest

from agent_phase import gitstate
from agent_phase.finalization_proof import RecoveryError
from agent_phase.finalization_recovery import recover, main
from test_agent_phase_resume import repository as _repository, dispatcher, Runner, PHASE, REQUEST, git

repository = _repository


def source_run(repository, tmp_path, policy="checkpoint"):
    state = dispatcher(repository, tmp_path / "runs", Runner(mutate_at=2)).dispatch(
        PHASE, REQUEST, finalization_policy=policy)
    return Path(state["run_directory"])


def snapshot(source):
    return {str(p.relative_to(source)): p.read_bytes() for p in source.rglob("*") if p.is_file()}


def manual_commit(repository, extra=False):
    git(repository, "add", "phase.txt")
    if extra:
        (repository / "unrelated.txt").write_text("unrelated\n")
        git(repository, "add", "unrelated.txt")
    git(repository, "commit", "-qm", "operator materialization")


@pytest.mark.parametrize("extra", [False, True])
def test_materialized_objects_receipt_is_new_and_never_publishes(repository, tmp_path, monkeypatch, extra):
    source = source_run(repository, tmp_path)
    before = snapshot(source)
    manual_commit(repository, extra)
    head = git(repository, "rev-parse", "HEAD")
    index = gitstate.index_identity(repository)
    monkeypatch.setattr("agent_phase.finalization.finalize_repository", lambda *a, **k: pytest.fail("republished"))
    receipt = recover(source, repository)
    assert receipt["finalization"]["outcome"] == "materialized"
    assert receipt["phase_owned_paths"] == ["phase.txt"]
    assert receipt["unrelated_committed_paths_not_adopted"] == (["unrelated.txt"] if extra else [])
    assert not receipt["git_mutation_performed"] and not receipt["publication_attempted"]
    assert receipt["provider_invocations"] == 0
    assert snapshot(source) == before
    assert Path(receipt["receipt_path"]).is_file()
    again = recover(source, repository)
    assert again["finalization"]["outcome"] == "materialized"
    assert git(repository, "rev-parse", "HEAD") == head
    assert gitstate.index_identity(repository) == index


def test_finalized_dry_run_no_mutation(repository, tmp_path, monkeypatch):
    source = source_run(repository, tmp_path, "commit-local")
    before = snapshot(source.parent)
    boundary = gitstate.capture_entry(repository)
    monkeypatch.setattr("agent_phase.finalization.finalize_repository", lambda *a, **k: pytest.fail("finalized"))
    receipt = recover(source, repository, dry_run=True)
    assert receipt["action"] == "verify_existing"
    assert receipt["provider_invocations"] == 0
    assert snapshot(source.parent) == before
    assert gitstate.capture_entry(repository) == boundary


def test_checkpoint_finalization_preserves_unrelated_dirt(repository, tmp_path):
    source = source_run(repository, tmp_path)
    before = snapshot(source)
    (repository / "operator.txt").write_text("preserve me\n")
    receipt = recover(source, repository, policy="commit-local", authorize_policy_upgrade=True)
    assert receipt["finalization"]["outcome"] == "completed"
    assert receipt["git_mutation_performed"]
    assert (repository / "operator.txt").read_text() == "preserve me\n"
    assert git(repository, "ls-tree", "HEAD", "--", "operator.txt") == ""
    assert snapshot(source) == before
    again = recover(source, repository, policy="commit-local", authorize_policy_upgrade=True)
    assert again["finalization"]["outcome"] == "materialized"
    assert not again["git_mutation_performed"]


def test_owned_object_difference_refuses(repository, tmp_path):
    source = source_run(repository, tmp_path)
    (repository / "phase.txt").write_text("different\n")
    manual_commit(repository)
    with pytest.raises(RecoveryError, match="RECOVERY_CANDIDATE_CONFLICT"):
        recover(source, repository)


def test_incompatible_history_refuses(repository, tmp_path):
    source = source_run(repository, tmp_path)
    branch = git(repository, "branch", "--show-current")
    tree = git(repository, "write-tree")
    unrelated = git(repository, "commit-tree", tree, "-m", "unrelated root")
    git(repository, "update-ref", f"refs/heads/{branch}", unrelated)
    with pytest.raises(RecoveryError, match="RECOVERY_ANCESTRY_MISMATCH"):
        recover(source, repository)


@pytest.mark.parametrize("case", ["branch", "index", "operation"])
def test_repository_ambiguity_refuses(repository, tmp_path, monkeypatch, capsys, case):
    source = source_run(repository, tmp_path)
    if case == "branch":
        git(repository, "switch", "-qc", "other")
    elif case == "index":
        git(repository, "add", "phase.txt")
    else:
        (repository / ".git" / "MERGE_HEAD").write_text(git(repository, "rev-parse", "HEAD") + "\n")
    monkeypatch.chdir(repository)
    assert main(["--run", str(source)]) == 2
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["finalization"]["repair_class"] == "requires_repository_resolution"
    assert receipt["provider_invocations"] == 0


def test_exact_run_required(capsys):
    with pytest.raises(SystemExit) as error:
        main([])
    assert error.value.code == 2


def test_source_cli_dry_run_never_invokes_provider(repository, tmp_path):
    source = source_run(repository, tmp_path, "commit-local")
    before = gitstate.capture_entry(repository)
    traps = tmp_path / "traps"
    traps.mkdir()
    marker = tmp_path / "provider-invoked"
    for name in ("codex", "claude", "agy", "gemini"):
        path = traps / name
        path.write_text('#!/bin/sh\ntouch "$PROVIDER_MARKER"\nexit 99\n')
        path.chmod(0o755)
    executable = Path(__file__).resolve().parents[3] / "bin/agent-phase-finalize"
    result = subprocess.run([str(executable), "--run", str(source), "--dry-run"],
        cwd=repository, env={**os.environ, "PATH": str(traps) + os.pathsep + os.environ["PATH"],
                             "PROVIDER_MARKER": str(marker)}, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["provider_invocations"] == 0
    assert not marker.exists()
    assert gitstate.capture_entry(repository) == before


def test_excluded_path_cannot_be_absorbed(repository, tmp_path):
    from test_agent_phase_path_dispositions import OwnershipRunner
    from test_agent_phase_disposition_flow import make_dispatcher, PHASE_ID, REQUEST as request
    def mutate(cwd, prompt):
        (cwd / "phase.txt").write_text("phase\n")
        (cwd / "base.txt").write_text("excluded edit\n")
    state = make_dispatcher(repository, tmp_path, OwnershipRunner(hooks={2: mutate},
        dispositions=[{"path": "base.txt", "disposition": "exclude_unrelated"}])).dispatch(
            PHASE_ID, request, finalization_policy="checkpoint")
    source = Path(state["run_directory"])
    git(repository, "add", "phase.txt", "base.txt")
    git(repository, "commit", "-qm", "absorbed exclusion")
    with pytest.raises(RecoveryError, match="RECOVERY_EXCLUSION_CONFLICT"):
        recover(source, repository)


def test_ambiguous_deletion_requires_manager(repository, tmp_path):
    from test_agent_phase_path_dispositions import OwnershipRunner
    from test_agent_phase_disposition_flow import make_dispatcher, PHASE_ID, REQUEST as request
    state = make_dispatcher(repository, tmp_path, OwnershipRunner(
        hooks={2: lambda cwd, prompt: (cwd / "base.txt").unlink()})).dispatch(
            PHASE_ID, request, finalization_policy="checkpoint")
    with pytest.raises(RecoveryError) as error:
        recover(Path(state["run_directory"]), repository, policy="commit-local", authorize_policy_upgrade=True)
    assert error.value.repair_class == "requires_manager_ownership"


def test_metadata_recovery_uses_retained_proof(repository, tmp_path):
    from test_agent_phase_metadata_noops import METADATA, add_product_and_metadata
    from test_agent_phase_path_dispositions import OwnershipRunner
    from test_agent_phase_disposition_flow import make_dispatcher, PHASE_ID, REQUEST as request
    state = make_dispatcher(repository, tmp_path, OwnershipRunner(hooks={2: add_product_and_metadata},
        dispositions=[{"path": METADATA, "disposition": "exclude_environment"}])).dispatch(
            PHASE_ID, request, finalization_policy="checkpoint")
    receipt = recover(Path(state["run_directory"]), repository, policy="commit-local", authorize_policy_upgrade=True)
    assert receipt["finalization"]["outcome"] == "completed"
    assert receipt["path_ownership"]["path_disposition_noops"]
    assert METADATA not in receipt["phase_owned_paths"]
    assert (repository / METADATA).read_bytes() == b"opaque metadata"


@pytest.mark.parametrize("materialized", [False, True])
def test_historical_redundant_metadata_failure_repairs_without_provider(repository, tmp_path, monkeypatch, materialized):
    from agent_phase import metadata_noop
    from agent_phase.dispatch import DispatchError
    from agent_phase.result import ResultError
    from test_agent_phase_metadata_noops import METADATA, add_product_and_metadata
    from test_agent_phase_path_dispositions import OwnershipRunner
    from test_agent_phase_disposition_flow import make_dispatcher, PHASE_ID, REQUEST as request
    runner = OwnershipRunner(hooks={2: add_product_and_metadata},
        dispositions=[{"path": METADATA, "disposition": "exclude_environment"}])
    with monkeypatch.context() as patch:
        def old_proof(*args, **kwargs):
            raise ResultError("PATH_DISPOSITION_INVALID", "historical no-op rejection")
        patch.setattr(metadata_noop, "prove", old_proof)
        with pytest.raises(DispatchError):
            make_dispatcher(repository, tmp_path, runner).dispatch(
                PHASE_ID, request, finalization_policy="commit-local")
    source = next((tmp_path / "runs").rglob("state.json"))
    before = snapshot(source.parent)
    if materialized:
        git(repository, "add", "product.txt")
        git(repository, "commit", "-qm", "operator materialization")
    receipt = recover(source.parent, repository)
    assert receipt["finalization"]["outcome"] == ("materialized" if materialized else "completed")
    assert receipt["repair"]["code"] == ("CANDIDATE_MATERIALIZATION_VERIFIED" if materialized
                                          else "METADATA_NORMALIZATION_VERIFIED")
    assert receipt["provider_invocations"] == 0
    assert snapshot(source.parent) == before


def test_recovery_refuses_execution_hooks(repository, tmp_path):
    source = source_run(repository, tmp_path)
    marker = repository / "hook-ran"
    hook = repository / ".git/hooks/pre-commit"
    hook.write_text("#!/bin/sh\ntouch hook-ran\n")
    hook.chmod(0o755)
    with pytest.raises(RecoveryError, match="RECOVERY_HOOK_POLICY"):
        recover(source, repository, policy="commit-local", authorize_policy_upgrade=True)
    assert not marker.exists()


def test_recovery_cannot_adopt_path_appearing_after_preflight(repository, tmp_path, monkeypatch):
    from agent_phase import finalization
    source = source_run(repository, tmp_path)
    head = git(repository, "rev-parse", "HEAD")
    real_finalize = finalization.finalize_repository
    def intervening_write(*args, **kwargs):
        (repository / "unowned-late.txt").write_text("operator\n")
        return real_finalize(*args, **kwargs)
    monkeypatch.setattr(finalization, "finalize_repository", intervening_write)
    receipt = recover(source, repository, policy="commit-local", authorize_policy_upgrade=True)
    assert receipt["finalization"]["outcome"] == "blocked"
    assert receipt["finalization"]["blocking_reason"]["code"] == "RESUME_CANDIDATE_CONFLICT"
    assert git(repository, "rev-parse", "HEAD") == head
    assert "unowned-late.txt" not in receipt["phase_owned_paths"]


@pytest.mark.parametrize("failed_name", ["receipt.json", "finalization-state.json"])
def test_receipt_delivery_failure_retains_local_commit_truth(repository, tmp_path, monkeypatch, failed_name):
    from agent_phase.finalization_recovery import ReceiptDirectory
    source = source_run(repository, tmp_path)
    real_write = ReceiptDirectory.write_json
    def failed_delivery(self, name, value):
        if name == failed_name:
            raise OSError("injected receipt delivery failure")
        return real_write(self, name, value)
    monkeypatch.setattr(ReceiptDirectory, "write_json", failed_delivery)
    receipt = recover(source, repository, policy="commit-local", authorize_policy_upgrade=True)
    assert receipt["finalization"]["outcome"] == "completed"
    assert receipt["finalization"]["local_commit"]["outcome"] == "completed"
    assert receipt["final_head"] == git(repository, "rev-parse", "HEAD")
    assert receipt["git_mutation_performed"]
    assert receipt["delivery"]["outcome"] == "blocked"


def test_receipt_is_not_generic_resume_adoption(repository, tmp_path):
    from agent_phase.dispatch import DispatchError
    source = source_run(repository, tmp_path)
    manual_commit(repository, extra=True)
    receipt = recover(source, repository)
    with pytest.raises(DispatchError):
        dispatcher(repository, tmp_path / "resume", lambda *a, **k: pytest.fail("provider called")).resume(
            PHASE, REQUEST, source, "finalize", finalization_policy="commit-local")
    with pytest.raises(DispatchError):
        dispatcher(repository, tmp_path / "receipt-resume", lambda *a, **k: pytest.fail("provider called")).resume(
            PHASE, REQUEST, Path(receipt["receipt_path"]).parent, "finalize")


@pytest.mark.parametrize("key", ["GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR",
    "GIT_NAMESPACE", "GIT_REPLACE_REF_BASE", "GIT_SHALLOW_FILE"])
def test_redirected_git_authority_refused_before_git(repository, tmp_path, monkeypatch, key):
    source = source_run(repository, tmp_path)
    before = snapshot(source.parent)
    monkeypatch.setenv(key, str(tmp_path / "redirected"))
    monkeypatch.setattr(gitstate, "repository_root", lambda *a: pytest.fail("Git before guard"))
    with pytest.raises(RecoveryError, match="RECOVERY_ENVIRONMENT_INVALID") as error:
        recover(source, repository)
    assert error.value.repair_class == "requires_repository_resolution"
    assert snapshot(source.parent) == before


def test_policy_upgrade_requires_separate_authority(repository, tmp_path):
    source = source_run(repository, tmp_path)
    before = snapshot(source.parent)
    boundary = gitstate.capture_entry(repository)
    with pytest.raises(RecoveryError, match="RECOVERY_POLICY_AUTHORITY_REQUIRED") as error:
        recover(source, repository, policy="publish")
    assert error.value.repair_class == "requires_manager_ownership"
    assert snapshot(source.parent) == before
    assert gitstate.capture_entry(repository) == boundary


def test_default_checkpoint_recovery_reconstructs_without_git_mutation(repository, tmp_path):
    source = source_run(repository, tmp_path)
    before = snapshot(source)
    boundary = gitstate.capture_entry(repository)
    for _ in range(2):
        receipt = recover(source, repository)
        assert receipt["finalization_policy"] == "checkpoint"
        assert receipt["finalization"]["outcome"] == "completed"
        assert not receipt["git_mutation_performed"] and not receipt["publication_attempted"]
        directory = Path(receipt["receipt_path"]).parent
        manifest = json.loads((directory / "checkpoint-candidate-manifest.json").read_text())
        assert manifest["reconstruction"]["verified"]
        assert set(manifest["paths"]) == {"phase.txt"}
        assert snapshot(source) == before
        assert gitstate.capture_entry(repository) == boundary


def test_fsmonitor_refused_before_capture(repository, tmp_path, monkeypatch):
    source = source_run(repository, tmp_path)
    git(repository, "config", "core.fsmonitor", "./monitor")
    monkeypatch.setattr(gitstate, "capture_entry", lambda *a: pytest.fail("capture before guard"))
    with pytest.raises(RecoveryError, match="RECOVERY_HOOK_POLICY"):
        recover(source, repository)
