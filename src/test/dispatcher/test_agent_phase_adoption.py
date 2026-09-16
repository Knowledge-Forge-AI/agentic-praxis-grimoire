"""Explicit new-phase adoption across disposable real Git boundaries."""

import json
from pathlib import Path

import pytest

from agent_phase import adoption, archive, archive_verify, gitstate
from agent_phase.dispatch import DispatchError
from agent_phase.request import PhaseRequest
from test_agent_phase_disposition_flow import make_dispatcher, repository as _repository, git, PHASE_ID, REQUEST
from test_agent_phase_path_dispositions import OwnershipRunner

repository = _repository


NEW_PHASE = "CONTINUATION"
NEW_REQUEST = PhaseRequest("implementation_testing", "normal", "NEW substantive task")


def sealed(repository, tmp_path, names=("adopted.txt",), dispositions=None):
    def work(cwd, prompt):
        for name in names:
            (cwd / name).parent.mkdir(parents=True, exist_ok=True)
            (cwd / name).write_text("sealed candidate\n")
    state = make_dispatcher(repository, tmp_path / "source", OwnershipRunner(
        hooks={2: work}, dispositions=dispositions)).dispatch(
            PHASE_ID, REQUEST, finalization_policy="checkpoint")
    return Path(state["run_directory"])


def receipt(repository, tmp_path, source, paths=None):
    record = adoption.create(source, repository, NEW_PHASE, NEW_REQUEST,
                             reason="Accept reviewed candidate objects", paths=paths)
    path = tmp_path / "adoption.json"
    path.write_bytes(adoption.encoded(record))
    return path, record


def continue_phase(repository, tmp_path, path, runner=None, policy="commit-local"):
    return make_dispatcher(repository, tmp_path / "new", runner or OwnershipRunner(
        hooks={2: lambda cwd, prompt: (cwd / "new.txt").write_text("new work\n")})).dispatch(
            NEW_PHASE, NEW_REQUEST, finalization_policy=policy, continue_from=path)


def test_provider_free_creation_and_nonmutating_dry_run(repository, tmp_path):
    source = sealed(repository, tmp_path)
    before = {p.name: p.read_bytes() for p in source.iterdir() if p.is_file()}
    boundary = gitstate.capture_entry(repository)
    path, record = receipt(repository, tmp_path, source)
    runner = OwnershipRunner()
    state = make_dispatcher(repository, tmp_path / "dry", runner).dry_run(
        NEW_PHASE, NEW_REQUEST, continue_from=path)
    assert record["provider_invocations"] == 0 and runner.calls == []
    assert state["run_id"] == record["continuation_run_id"]
    assert not (tmp_path / "dry").exists()
    assert gitstate.capture_entry(repository) == boundary
    assert before == {p.name: p.read_bytes() for p in source.iterdir() if p.is_file()}


def test_uncommitted_adoption_preserves_unrelated_dirt_and_fresh_semantics(repository, tmp_path):
    source = sealed(repository, tmp_path)
    (repository / "operator.txt").write_text("operator dirt\n")
    path, record = receipt(repository, tmp_path, source)
    runner = OwnershipRunner(hooks={2: lambda cwd, prompt: (cwd / "new.txt").write_text("new\n")})
    state = continue_phase(repository, tmp_path, path, runner)
    assert state["complete"] and state["commit_verified"]
    assert state["phase_owned_paths"] == ["adopted.txt", "new.txt"]
    assert {x["path"] for x in state["phase_delta"]} == {"adopted.txt", "new.txt"}
    assert (repository / "operator.txt").read_text() == "operator dirt\n"
    assert git(repository, "ls-tree", "HEAD", "--", "operator.txt") == ""
    assert len(runner.calls) == 5 and state["provider_invocations_inherited"] == 0
    assert state["run_id"] == record["continuation_run_id"]
    assert state["adoption"] == record
    assert b"NEW substantive task" in runner.calls[0]["prompt"]
    assert b"Dispatcher-owned adoption provenance" in runner.calls[0]["prompt"]
    assert b"Implement disposition flow task." not in runner.calls[0]["prompt"]
    assert json.loads((Path(state["run_directory"]) / "result.json").read_text())["adoption"] == record


@pytest.mark.parametrize("policy", ["checkpoint", "commit-local"])
def test_without_adoption_editing_prior_dirty_path_requires_manager(repository, tmp_path, policy):
    sealed(repository, tmp_path)
    head = git(repository, "rev-parse", "HEAD")
    state = make_dispatcher(repository, tmp_path / "new", OwnershipRunner(
        hooks={2: lambda cwd, prompt: (cwd / "adopted.txt").write_text("changed\n")})).dispatch(
            NEW_PHASE, NEW_REQUEST, finalization_policy=policy)
    assert git(repository, "rev-parse", "HEAD") == head
    assert state["commit"] is None
    assert state["entry_dirt_overlap"] == ["adopted.txt"]


def test_subset_does_not_adopt_other_source_path(repository, tmp_path):
    source = sealed(repository, tmp_path, ("adopted.txt", "unselected.txt"))
    path, record = receipt(repository, tmp_path, source, ["adopted.txt"])
    state = continue_phase(repository, tmp_path, path)
    assert record["unselected_source_paths"] == ["unselected.txt"]
    assert state["phase_owned_paths"] == ["adopted.txt", "new.txt"]
    assert git(repository, "ls-tree", "HEAD", "--", "unselected.txt") == ""
    assert (repository / "unselected.txt").read_text() == "sealed candidate\n"


@pytest.mark.parametrize("change", ["receipt", "object", "branch", "index", "operation", "source"])
def test_stale_or_tampered_authority_stops_before_provider(repository, tmp_path, change):
    source = sealed(repository, tmp_path)
    path, record = receipt(repository, tmp_path, source)
    if change == "receipt":
        record["reason"] = "tampered"
        path.write_text(json.dumps(record))
    elif change == "object":
        (repository / "adopted.txt").write_text("operator replacement\n")
    elif change == "branch":
        git(repository, "switch", "-qc", "other")
    elif change == "index":
        (repository / "staged.txt").write_text("staged operator\n")
        git(repository, "add", "staged.txt")
    elif change == "operation":
        (repository / ".git/MERGE_HEAD").write_text(git(repository, "rev-parse", "HEAD") + "\n")
    else:
        (source / "state.json").write_text("{}")
    runner = OwnershipRunner()
    expected = {
        "receipt": "adoption checksum differs",
        "object": "repository changed since adoption creation",
        "branch": "repository changed since adoption creation",
        "index": "repository changed since adoption creation",
        "operation": "repository has active Git operation state",
        "source": "source archive",
    }[change]
    with pytest.raises(adoption.AdoptionError, match=expected):
        continue_phase(repository, tmp_path, path, runner)
    assert runner.calls == []


@pytest.mark.parametrize("extra", [False, True])
def test_materialized_candidate_is_provenance_without_republication(repository, tmp_path, extra):
    from agent_phase.finalization_recovery import recover
    source = sealed(repository, tmp_path)
    git(repository, "add", "adopted.txt")
    if extra:
        (repository / "unrelated.txt").write_text("unrelated commit\n")
        git(repository, "add", "unrelated.txt")
    git(repository, "commit", "-qm", "manual materialization")
    recognized = recover(source, repository)
    path, record = receipt(repository, tmp_path, source)
    state = continue_phase(repository, tmp_path, path)
    assert recognized["finalization"]["outcome"] == "materialized"
    assert record["materialization"]["action"] == "recognize_materialization"
    assert state["phase_delta"] == [{"path": "new.txt", "status": "A"}]
    assert "unrelated.txt" not in state["candidate_manifest"]["paths"]


def test_materialization_with_one_different_object_refuses(repository, tmp_path):
    source = sealed(repository, tmp_path)
    (repository / "adopted.txt").write_text("different\n")
    git(repository, "add", "adopted.txt")
    git(repository, "commit", "-qm", "different candidate")
    with pytest.raises(RuntimeError, match="CANDIDATE_CONFLICT"):
        receipt(repository, tmp_path, source)


@pytest.mark.parametrize("claim", [False, True])
def test_provider_cannot_expand_selection_to_unselected_dirt(repository, tmp_path, claim):
    source = sealed(repository, tmp_path, ("adopted.txt", "unselected.txt"))
    path, _ = receipt(repository, tmp_path, source, ["adopted.txt"])
    runner = OwnershipRunner(
        hooks={2: lambda cwd, prompt: (cwd / "unselected.txt").write_text("changed\n")} if not claim else {},
        dispositions=[{"path": "unselected.txt", "disposition": "phase_owned"}] if claim else [])
    head = git(repository, "rev-parse", "HEAD")
    expected = ("provider disposition overlaps unadopted authority" if claim
                else "phase change overlaps an unadopted object boundary")
    error_type = DispatchError if claim else adoption.AdoptionError
    with pytest.raises(error_type, match=expected) as refusal:
        continue_phase(repository, tmp_path, path, runner)
    assert refusal.value.code == ("PATH_DISPOSITION_INVALID" if claim else "ADOPTION_INVALID")
    assert git(repository, "rev-parse", "HEAD") == head


@pytest.mark.parametrize("policy", ["checkpoint", "commit-local"])
@pytest.mark.parametrize("claim", [False, True])
def test_new_deletion_of_adopted_path_requires_current_phase_disposition(repository, tmp_path, claim, policy):
    source = sealed(repository, tmp_path)
    git(repository, "add", "adopted.txt")
    git(repository, "commit", "-qm", "materialize")
    path, _ = receipt(repository, tmp_path, source)
    runner = OwnershipRunner(hooks={2: lambda cwd, prompt: (cwd / "adopted.txt").unlink()},
        challenge_decision="phase_owned" if claim else None)
    head = git(repository, "rev-parse", "HEAD")
    state = continue_phase(repository, tmp_path, path, runner, policy)
    if claim:
        assert state["phase_delta"] == [{"path": "adopted.txt", "status": "D"}]
        assert "path_ownership_required" not in state.get("manager_attention_reasons", [])
    else:
        assert git(repository, "rev-parse", "HEAD") == head
        assert state["commit"] is None
        assert "adopted.txt" not in state["candidate_manifest"]["paths"]
        assert "adopted.txt" not in state["phase_owned_paths"]
        assert "path_ownership_required" in state["manager_attention_reasons"]


def test_continued_checkpoint_can_resume_exactly_and_recover_provider_free(repository, tmp_path):
    from agent_phase.finalization_recovery import recover
    source = sealed(repository, tmp_path)
    path, _ = receipt(repository, tmp_path, source)
    state = continue_phase(repository, tmp_path, path, policy="checkpoint")
    continued = Path(state["run_directory"])
    dry = make_dispatcher(repository, tmp_path / "resume", OwnershipRunner()).resume(
        NEW_PHASE, NEW_REQUEST, continued, "finalize", dry_run=True)
    assert dry["provider_invocations_performed"] == 0
    recovered = recover(continued, repository)
    assert recovered["phase_owned_paths"] == ["adopted.txt", "new.txt"]


def test_symlink_swap_after_receipt_invalidates_entry(repository, tmp_path):
    source = sealed(repository, tmp_path, ("dir/item.txt",))
    path, _ = receipt(repository, tmp_path, source)
    (repository / "dir/item.txt").unlink()
    (repository / "dir").rmdir()
    target = tmp_path / "outside"
    target.mkdir()
    (target / "item.txt").write_text("sealed candidate\n")
    (repository / "dir").symlink_to(target, target_is_directory=True)
    with pytest.raises(adoption.AdoptionError, match="repository changed since adoption creation"):
        continue_phase(repository, tmp_path, path)


def test_symlink_ancestor_at_creation_refuses_alias(repository, tmp_path):
    source = sealed(repository, tmp_path, ("dir/item.txt",))
    git(repository, "add", "dir/item.txt")
    git(repository, "commit", "-qm", "materialize candidate")
    (repository / "dir/item.txt").unlink()
    (repository / "dir").rmdir()
    target = tmp_path / "outside"
    target.mkdir()
    (target / "item.txt").write_text("sealed candidate\n")
    (repository / "dir").symlink_to(target, target_is_directory=True)
    with pytest.raises(adoption.AdoptionError, match="adopted path traverses a symlink alias"):
        receipt(repository, tmp_path, source)
    assert not (tmp_path / "adoption.json").exists()


def test_selected_prefix_overlap_refuses_at_creation(repository, tmp_path):
    source = sealed(repository, tmp_path, ("dir/item.txt",))
    with pytest.raises(adoption.AdoptionError, match="selected paths have overlapping object boundaries"):
        receipt(repository, tmp_path, source, ["dir", "dir/item.txt"])


def test_directory_occupying_adopted_object_refuses_at_creation(repository, tmp_path):
    (repository / "anchor.txt").write_text("retained tracked object\n")
    git(repository, "add", "anchor.txt")
    git(repository, "commit", "-qm", "retain nonempty repository")
    state = make_dispatcher(repository, tmp_path / "source", OwnershipRunner(
        hooks={2: lambda cwd, prompt: (cwd / "README.md").unlink()},
        challenge_decision="phase_owned")).dispatch(
            PHASE_ID, REQUEST, finalization_policy="checkpoint")
    source = Path(state["run_directory"])
    git(repository, "add", "README.md")
    git(repository, "commit", "-qm", "materialize owned deletion")
    # Git does not record an empty directory at an absent object boundary.
    (repository / "README.md").mkdir()
    with pytest.raises(adoption.AdoptionError, match="adopted object is occupied by a directory"):
        receipt(repository, tmp_path, source)


@pytest.mark.parametrize("dry_run", [False, True])
@pytest.mark.parametrize("forge_source", [False, True])
def test_rechecksummed_scope_expansion_cannot_adopt_unrelated_dirt(
        repository, tmp_path, dry_run, forge_source):
    source = sealed(repository, tmp_path)
    (repository / "operator.txt").write_text("operator-owned bytes\n")
    path, record = receipt(repository, tmp_path, source)
    record["adopted_paths"].append("operator.txt")
    record["excluded_unrelated_paths"].remove("operator.txt")
    # Bind real operator bytes and recompute every affected receipt checksum.
    # Even a forged source-manifest copy must agree with immutable source evidence.
    record["candidate_manifest"] = gitstate.candidate_manifest(repository,
        record["source_entry"]["tree"], record["observed_entry"]["tree"],
        paths=record["adopted_paths"])
    if forge_source:
        record["source_candidate_manifest"] = record["candidate_manifest"]
        record["source_candidate_manifest_sha256"] = adoption.digest(record["source_candidate_manifest"])
    record["sha256"] = adoption.digest({k: v for k, v in record.items() if k != "sha256"})
    path.write_bytes(adoption.encoded(record))
    boundary = gitstate.capture_entry(repository)
    runner = OwnershipRunner()
    expected = "source candidate binding changed" if forge_source else "adoption objects disagree with source candidate"
    with pytest.raises(adoption.AdoptionError, match=expected):
        dispatcher = make_dispatcher(repository, tmp_path / "new", runner)
        operation = dispatcher.dry_run if dry_run else dispatcher.dispatch
        operation(NEW_PHASE, NEW_REQUEST, continue_from=path)
    assert runner.calls == []
    assert gitstate.capture_entry(repository) == boundary


@pytest.mark.parametrize("case", ["missing_run", "parent_directory", "manifest", "missing_object"])
def test_invalid_source_cannot_create_authority(repository, tmp_path, case):
    source = sealed(repository, tmp_path)
    if case == "missing_run":
        source = tmp_path / "missing"
    elif case == "parent_directory":
        source = source.parent
    elif case == "manifest":
        state_path = source / "state.json"
        state = json.loads(state_path.read_text())
        state["candidate_manifest"]["paths"]["adopted.txt"]["sha256"] = "0" * 64
        state_path.write_text(json.dumps(state))
    else:
        oid = git(repository, "hash-object", "adopted.txt")
        (repository / ".git/objects" / oid[:2] / oid[2:]).unlink()
    error_type = gitstate.GitStateError if case == "missing_object" else archive_verify.VerificationError
    expected = "CANDIDATE_MANIFEST_TREE_UNREADABLE" if case == "missing_object" else "source archive"
    with pytest.raises(error_type, match=expected):
        receipt(repository, tmp_path, source)
    assert not (tmp_path / "adoption.json").exists()


def test_materialization_receipt_reference_is_verified(repository, tmp_path):
    from agent_phase.finalization_recovery import recover
    source = sealed(repository, tmp_path)
    git(repository, "add", "adopted.txt")
    git(repository, "commit", "-qm", "manual materialization")
    recognized = recover(source, repository)
    reference = Path(recognized["receipt_path"])
    record = adoption.create(source, repository, NEW_PHASE, NEW_REQUEST,
        reason="Accept materialized candidate", materialization_receipt=reference)
    assert record["materialization_receipt"]["record"] == recognized
    recognized["candidate_manifest"]["paths"] = {}
    reference.write_text(json.dumps(recognized))
    with pytest.raises(adoption.AdoptionError, match="materialization receipt"):
        adoption.create(source, repository, NEW_PHASE, NEW_REQUEST,
            reason="Accept materialized candidate", materialization_receipt=reference)


def test_excluded_source_objects_remain_protected(repository, tmp_path):
    source = sealed(repository, tmp_path, ("adopted.txt", "excluded.txt"),
        [{"path": "excluded.txt", "disposition": "exclude_unrelated"}])
    path, record = receipt(repository, tmp_path, source)
    assert record["inherited_excluded_paths"] == ["excluded.txt"]
    state = continue_phase(repository, tmp_path, path)
    assert state["phase_owned_paths"] == ["adopted.txt", "new.txt"]
    assert (repository / "excluded.txt").read_text() == "sealed candidate\n"
    assert git(repository, "ls-tree", "HEAD", "--", "excluded.txt") == ""


def test_continued_phase_may_modify_exact_adopted_uncommitted_object(repository, tmp_path):
    source = sealed(repository, tmp_path)
    path, _ = receipt(repository, tmp_path, source)
    runner = OwnershipRunner(hooks={2: lambda cwd, prompt: (cwd / "adopted.txt").write_text("new owned bytes\n")})
    state = continue_phase(repository, tmp_path, path, runner)
    assert state["commit_verified"]
    assert git(repository, "show", "HEAD:adopted.txt") == "new owned bytes"


def test_source_owned_deletion_is_adoptable_without_inheriting_semantic_stages(repository, tmp_path):
    def remove(cwd, prompt):
        (cwd / "README.md").unlink()
    state = make_dispatcher(repository, tmp_path / "source", OwnershipRunner(hooks={2: remove},
        challenge_decision="phase_owned")).dispatch(
            PHASE_ID, REQUEST, finalization_policy="checkpoint")
    path, record = receipt(repository, tmp_path, Path(state["run_directory"]))
    assert record["candidate_manifest"]["paths"]["README.md"]["present"] is False
    new = continue_phase(repository, tmp_path, path)
    assert new["commit_verified"]
    assert {x["path"] for x in new["phase_delta"]} == {"README.md", "new.txt"}


def test_cli_creation_is_provider_free_and_dispatch_names_receipt(repository, tmp_path, monkeypatch, capsys):
    from agent_phase import adoption_cli, cli
    source = sealed(repository, tmp_path)
    request = tmp_path / f"{NEW_PHASE}.request.json"
    request.write_text(json.dumps(NEW_REQUEST.as_dict()))
    output = tmp_path / "selected.json"
    monkeypatch.chdir(repository)
    monkeypatch.setattr("agent_phase.dispatch.Dispatcher._stage", lambda *a, **k: pytest.fail("provider called"))
    assert adoption_cli.main(["--run", str(source), "--request", str(request),
        "--reason", "Accept exact objects", "--output", str(output)]) == 0
    capsys.readouterr()
    assert cli.dispatch_main([str(request), "--continue-from", str(output), "--dry-run", "--quiet"]) == 0
    assert json.loads(capsys.readouterr().out)["provider_invocations"] == 0
    with pytest.raises(SystemExit):
        cli.dispatch_main([str(request), "--continue-from", str(output), "--resume", str(source)])


def test_new_request_mismatch_and_receipt_reuse_fail_closed(repository, tmp_path):
    source = sealed(repository, tmp_path)
    path, _ = receipt(repository, tmp_path, source)
    with pytest.raises(adoption.AdoptionError, match="adoption receipt is stale or differs from proven authority"):
        make_dispatcher(repository, tmp_path / "wrong", OwnershipRunner()).dry_run(
            NEW_PHASE, REQUEST, continue_from=path)
    continue_phase(repository, tmp_path, path, policy="checkpoint")
    with pytest.raises(adoption.AdoptionError, match="repository changed since adoption creation"):
        continue_phase(repository, tmp_path, path)


def test_new_selected_lifecycle_is_fresh_work_reviewed(repository, tmp_path):
    class WorkReviewedRunner(OwnershipRunner):
        def __call__(self, *args, **kwargs):
            response = super().__call__(*args, **kwargs)
            return response._replace(stdout=response.stdout.replace(b'"stage": "closeout"',
                                                                       b'"stage": "revise_close"'))
    source = sealed(repository, tmp_path)
    path, _ = receipt(repository, tmp_path, source)
    runner = WorkReviewedRunner(hooks={0: lambda cwd, prompt: (cwd / "new.txt").write_text("new\n")})
    state = make_dispatcher(repository, tmp_path / "new", runner).dispatch(
        NEW_PHASE, NEW_REQUEST, lifecycle="work-reviewed", finalization_policy="checkpoint",
        continue_from=path)
    assert len(runner.calls) == 3
    assert state["stages_completed"] == ["produce", "work_review", "revise_close"]
    assert state["provider_invocations_inherited"] == 0
    assert state["checkpoints_completed"] == ["post_work"]


@pytest.mark.parametrize("field,value", [
    ("timestamp", "../../escape"), ("extra", "unknown field"),
    ("lineage_depth", 9), ("candidate_manifest", {}),
])
def test_recomputed_checksum_does_not_bypass_closed_schema(repository, tmp_path, field, value):
    source = sealed(repository, tmp_path)
    path, record = receipt(repository, tmp_path, source)
    record[field] = value
    record["sha256"] = adoption.digest({k: v for k, v in record.items() if k != "sha256"})
    path.write_bytes(adoption.encoded(record))
    expected = {
        "timestamp": "invalid continuation identity or lineage bound",
        "extra": "unsupported adoption schema",
        "lineage_depth": "invalid continuation identity or lineage bound",
        "candidate_manifest": "CANDIDATE_MANIFEST_INVALID",
    }[field]
    with pytest.raises(adoption.AdoptionError, match=expected):
        make_dispatcher(repository, tmp_path / "new", OwnershipRunner()).dry_run(
            NEW_PHASE, NEW_REQUEST, continue_from=path)


def test_resume_cannot_claim_unadopted_dirt_by_restoring_prior_bytes(repository, tmp_path):
    source = sealed(repository, tmp_path)
    (repository / "operator.txt").write_text("original operator dirt\n")
    path, _ = receipt(repository, tmp_path, source)
    def invalid_work(cwd, prompt):
        (cwd / "operator.txt").write_text("overlap\n")
        raise RuntimeError("injected provider failure after overlap")
    with pytest.raises(RuntimeError, match="injected provider failure after overlap"):
        continue_phase(repository, tmp_path, path, OwnershipRunner(hooks={2: invalid_work}))
    failed = next((tmp_path / "new/runs").rglob("state.json")).parent
    head = git(repository, "rev-parse", "HEAD")
    runner = OwnershipRunner(hooks={0: lambda cwd, prompt: (cwd / "operator.txt").write_text("original operator dirt\n")})
    with pytest.raises((ValueError, RuntimeError), match="candidate ownership includes an unadopted object boundary"):
        make_dispatcher(repository, tmp_path / "resume", runner).resume(
            NEW_PHASE, NEW_REQUEST, failed, "work", finalization_policy="commit-local")
    assert git(repository, "rev-parse", "HEAD") == head
    assert git(repository, "ls-tree", "HEAD", "--", "operator.txt") == ""


def test_dirty_prefix_collision_guard_uses_real_git_paths(repository, tmp_path):
    sealed(repository, tmp_path, ("dir/item.txt",))
    (repository / "dir/item.txt").unlink()
    (repository / "dir").rmdir()
    (repository / "dir").write_text("operator replacement boundary\n")
    dirty = gitstate.dirty_paths(repository)
    assert "dir" in dirty
    with pytest.raises(adoption.AdoptionError, match="entry dirt overlaps an adopted object boundary"):
        adoption.require_paths(repository, ["dir/item.txt"], dirty)


def test_consistently_resealed_manifest_still_must_match_git_objects(repository, tmp_path):
    from types import SimpleNamespace
    source = sealed(repository, tmp_path)
    state_path = source / "state.json"
    state = json.loads(state_path.read_text())
    state["candidate_manifest"]["paths"]["adopted.txt"]["sha256"] = "0" * 64
    state_path.write_text(json.dumps(state))
    # Rebuild only disposable test evidence, including transport manifest/receipt,
    # so the refusal proves Git object agreement rather than archive integrity.
    target = source.with_suffix(".zip")
    target.unlink()
    archive.receipt_path(target).unlink()
    archive.create(SimpleNamespace(path=source, archive_path=target,
        archive_temporary_path=source.with_suffix(".tmp.zip"), leaf=source.name))
    assert archive_verify.verify_source_archive(source)["verified_against_source_directory"] is True
    with pytest.raises(adoption.AdoptionError, match="sealed source objects disagree with candidate manifest"):
        receipt(repository, tmp_path, source)
    assert not (tmp_path / "adoption.json").exists()
