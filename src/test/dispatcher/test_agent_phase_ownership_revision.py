"""Independent review corrections: authority, revision arguments and readback."""
import json
from copy import deepcopy

import pytest

from agent_phase import candidate, gitstate, outcomes, ownership_challenge as challenges
from agent_phase import ownership_cli, result
from test_agent_phase_disposition_flow import repository as _repository
from test_agent_phase_path_dispositions import track

repository = _repository


@pytest.fixture
def deletion(repository):
    target = track(repository, "deleted.txt", symlink=False)
    entry = gitstate.capture_entry(repository)
    target.unlink()
    raw = candidate.tree_identity(repository)["tree"]
    state = {"run_id": "revision", "project": "fixture", "phase_id": "revision",
             "lifecycle": "standard"}
    challenges.observe(repository, state, entry, raw, "work", "post_producer")
    return state


@pytest.mark.parametrize("field", ["entry_tree", "raw_tree", "base_head"])
@pytest.mark.parametrize("value", ["--output=sentinel", "HEAD", "a" * 39, "A" * 40, None])
def test_record_rejects_non_object_revision_before_git(repository, deletion, monkeypatch, field, value):
    record = deepcopy(deletion["ownership_challenges"]["records"][0])
    record[field] = value
    record["challenge_id"] = "ownch1-" + challenges.digest(
        {key: item for key, item in record.items() if key != "challenge_id"})
    def forbidden(*args, **kwargs):
        pytest.fail("invalid revision reached Git")
    monkeypatch.setattr(gitstate, "_run", forbidden)
    with pytest.raises(result.ResultError, match="OWNERSHIP_CHALLENGE_INVALID"):
        challenges.validate_record(repository, record)


@pytest.mark.parametrize("kind", ["superseded", "resolved_by_provider", "resolved_by_manager"])
def test_event_revision_options_never_reach_git(repository, deletion, monkeypatch, kind):
    record = deletion["ownership_challenges"]["records"][0]
    cid = record["challenge_id"]
    if kind == "resolved_by_provider":
        challenges.prompt(repository, deletion, "closeout")
    event = {"challenge_id": cid, "kind": kind, "raw_tree": "--output=sentinel"}
    if kind != "superseded":
        event["decision"] = "phase_owned"
        event.update({"stage": "closeout"} if kind == "resolved_by_provider"
                     else {"receipt_digest": "a" * 64})
    deletion["ownership_challenges"]["events"].append(event)
    original = gitstate._run
    def guarded(root, arguments, *args, **kwargs):
        assert not any(arg.startswith("--output=") for arg in arguments)
        return original(root, arguments, *args, **kwargs)
    monkeypatch.setattr(gitstate, "_run", guarded)
    with pytest.raises(result.ResultError, match="OWNERSHIP_CHALLENGE_INVALID"):
        challenges.validate(repository, deletion)


@pytest.mark.parametrize("key", ["raw_terminal_candidate", "terminal_candidate", "closeout_candidate"])
def test_sealed_tree_rejects_revision_option(key):
    with pytest.raises(result.ResultError, match="OWNERSHIP_CHALLENGE_INVALID"):
        ownership_cli._state_raw_tree({key: {"tree": "--output=sentinel"}})


@pytest.mark.parametrize("stage", ["plan", "plan_review", "work", "produce", "work_review", "final_review"])
def test_nonterminal_result_refuses_even_empty_resolution_field(stage):
    nonce = "a" * 32
    begin, end = result.markers(nonce)
    payload = {"version": 1, "stage": stage, "outcome": "completed", "body": "",
               "commit_message": None, "ownership_resolutions": []}
    with pytest.raises(result.ResultError) as caught:
        result.parse((begin + "\n" + json.dumps(payload) + "\n" + end).encode(), stage, nonce)
    assert caught.value.code == "OWNERSHIP_PROVIDER_RESOLUTION_INVALID"
    assert outcomes.classify_failure(caught.value.code) == "requires_semantic_revision"
    assert outcomes.classify_failure("OWNERSHIP_CHALLENGE_INVALID") == "requires_repository_resolution"
    assert outcomes.classify_failure("OWNERSHIP_TYPE_CHANGE_UNSUPPORTED") == "requires_repository_resolution"


def test_git_facts_are_reused_only_inside_one_validation(repository, deletion, monkeypatch):
    challenges.prompt(repository, deletion, "closeout")
    record = deletion["ownership_challenges"]["records"][0]
    challenges.resolve_provider(repository, deletion, "closeout", record["raw_tree"],
        [{"challenge_id": record["challenge_id"], "decision": "phase_owned"}])
    original = gitstate.candidate_manifest
    calls = []
    def counted(*args, **kwargs):
        calls.append((args[1], tuple(kwargs["paths"])))
        return original(*args, **kwargs)
    monkeypatch.setattr(gitstate, "candidate_manifest", counted)
    challenges.validate(repository, deletion)
    assert len(calls) == len(set(calls)) == 3
    challenges.validate(repository, deletion)
    assert len(calls) == 6  # no retained cache can conceal later object corruption
