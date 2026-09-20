"""Provider-free ownership receipts and exact finalization recovery."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from agent_phase import ownership_cli
from agent_phase.finalization_proof import RecoveryError
from agent_phase.finalization_recovery import recover
from test_agent_phase_disposition_flow import PHASE_ID, REQUEST, make_dispatcher, repository as _repository
from test_agent_phase_path_dispositions import OwnershipRunner, track

repository = _repository


def _challenge_run(repository, tmp_path):
    target = track(repository, "ordinary.txt", symlink=False)
    state = make_dispatcher(
        repository,
        tmp_path / "runs",
        OwnershipRunner(
            hooks={2: lambda cwd, prompt: (
                target.unlink(),
                (cwd / "product.txt").write_text("product\n"),
            )}
        ),
    ).dispatch(PHASE_ID, REQUEST, finalization_policy="checkpoint")
    return target, Path(state["run_directory"]), state


def _receipt(repository, source, decision):
    state = json.loads((source / "state.json").read_text())
    challenge_id = state["ownership_challenges"]["records"][0]["challenge_id"]
    return ownership_cli.create(
        source,
        repository,
        challenge_id,
        decision,
        "manager reviewed the exact terminal candidate",
    ), challenge_id


@pytest.mark.parametrize("decision", ["phase_owned", "exclude_unrelated"])
def test_manager_receipt_binds_exact_challenge_and_recovers(repository, tmp_path, decision):
    target, source, state = _challenge_run(repository, tmp_path)
    before_source = {
        str(path.relative_to(source)): path.read_bytes()
        for path in source.rglob("*")
        if path.is_file()
    }
    output = tmp_path / f"ownership-{decision}.json"
    receipt, challenge_id = _receipt(repository, source, decision)
    ownership_cli._write_create_only(output, receipt)

    assert receipt["challenge_id"] == challenge_id
    assert receipt["provider_invocations"] == 0
    assert receipt["product_test_invocations"] == 0
    assert receipt["git_mutation_performed"] is False
    assert output.stat().st_mode & 0o077 == 0
    assert ownership_cli.read(output) == receipt
    assert {
        str(path.relative_to(source)): path.read_bytes()
        for path in source.rglob("*")
        if path.is_file()
    } == before_source

    recovered = recover(
        source,
        repository,
        policy="commit-local",
        authorize_policy_upgrade=True,
        ownership_resolutions=[output],
    )
    assert recovered["finalization"]["outcome"] == "completed"
    assert recovered["ownership_resolutions"][0]["challenge_id"] == challenge_id
    assert recovered["provider_invocations"] == 0
    assert not target.exists()
    if decision == "phase_owned":
        assert subprocess.run(
            ["git", "cat-file", "-e", "HEAD:ordinary.txt"],
            cwd=repository,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode != 0
        assert repository.joinpath("product.txt").read_text() == "product\n"
    else:
        assert subprocess.check_output(
            ["git", "show", "HEAD:ordinary.txt"], cwd=repository, text=True
        ) == "entry bytes\n"
        # Excluding a deletion restores only the private publication tree; the
        # operator-visible worktree deletion remains untouched.
        assert not (repository / "ordinary.txt").exists()


def test_tampered_manager_receipt_refuses_without_provider_or_git(repository, tmp_path):
    target, source, _state = _challenge_run(repository, tmp_path)
    output = tmp_path / "ownership.json"
    receipt, _challenge_id = _receipt(repository, source, "phase_owned")
    ownership_cli._write_create_only(output, receipt)
    tampered = {**receipt, "decision": "exclude_unrelated"}
    output.write_text(json.dumps(tampered, sort_keys=True) + "\n")
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repository, text=True
    ).strip()

    with pytest.raises(RecoveryError, match="OWNERSHIP_RESOLUTION_INVALID"):
        recover(
            source,
            repository,
            policy="commit-local",
            authorize_policy_upgrade=True,
            ownership_resolutions=[output],
        )
    assert subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repository, text=True
    ).strip() == head
    assert target is not None
