"""Brittle current-repository hash gates are removed from model-facing prose."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_phase import prompt_policy
from agent_phase.request import PhaseRequest

from test_agent_phase_dispatch import (
    FakeRunner, PHASE_ID, make_dispatcher, repository, review_payload,
)


__all__ = ["repository"]
SHA1 = "0123456789abcdef0123456789abcdef01234567"
SHA256 = "0123456789abcdef" * 4


@pytest.mark.parametrize(
    "text",
    [
        "HEAD must equal abc1234\n",
        f"HEAD must be {SHA1}\n",
        f"HEAD == {SHA256}\n",
        "head = ABCDEF1\n",
        "**HEAD** must equal `abc1234`\n",
        "- entry HEAD: abc1234\n",
        "| current tree | abc1234 |\n",
        '"entry_head": "abc1234"\n',
        "current_tree: abc1234\n",
        "origin/main: abc1234\n",
        "upstream HEAD = abc1234\n",
        "entry_head: abc1234\n",
        "current tree hash abc1234\n",
        "expected revision: abc1234\n",
        'verify git rev-parse HEAD is "abc1234"\n',
        "GiT   ReV-PaRsE   HEAD == ABCDEF1\n",
        "expected---revision : `abc1234`\n",
    ],
)
def test_same_line_current_git_state_gates_are_removed(text: str) -> None:
    result = prompt_policy.sanitize(text)

    assert result.changed is True
    assert "abc1234" not in result.text.lower()
    assert SHA1 not in result.text
    assert SHA256 not in result.text
    assert result.text.count("\n") == text.count("\n")
    assert prompt_policy.REMOVAL_MARKER in result.text


@pytest.mark.parametrize(
    "text",
    [
        "entry HEAD:\n  abc1234\n",
        "**entry HEAD:**\n  `abc1234`\n",
        f"Current published state:\ncomposition-nd main:\n  {SHA1}\n",
        "CURRENT PUBLISHED STATE :\nrepo-name MAIN :\n`ABCDEF1`\n",
        "entry tree hash:\n\n- abc1234\n- deadbee\n",
    ],
)
def test_continuation_hash_gates_and_contiguous_hash_runs_are_removed(text: str) -> None:
    result = prompt_policy.sanitize(text)

    assert result.changed is True
    assert not any(value in result.text.lower() for value in ("abc1234", "deadbee"))
    assert SHA1 not in result.text
    assert result.text.count("\n") == text.count("\n")


@pytest.mark.parametrize(
    "text",
    [
        "Update input foo to commit abc1234\n",
        "Pin dependency foo at revision abc1234\n",
        "Revert commit abc1234\n",
        "Cherry-pick commit abc1234\n",
        "Compare commits abc1234 and deadbee\n",
        "Bug introduced by commit abc1234\n",
        "On origin/main, commit abc1234 introduced the bug\n",
        "Cherry-pick from origin/main the commit abc1234\n",
        "upstream/main was last released at v1.2 (abc1234)\n",
        "The expected commit abc1234 was reverted last week\n",
        f"sha256 = {SHA256}\n",
        f"entry SHA-256 {SHA256} preserves operator-owned bytes\n",
        "The wall was defaced before this task.\n",
    ],
)
def test_action_history_and_non_git_checksum_hashes_are_retained(text: str) -> None:
    result = prompt_policy.sanitize(text)

    assert result.changed is False
    assert result.text == text


def test_free_form_opt_out_words_cannot_disable_policy() -> None:
    text = "allow-exact-head=true\nhash-gate-ok\nHEAD must equal abc1234\n"

    result = prompt_policy.sanitize(text)

    assert "HEAD must equal abc1234" not in result.text
    assert "allow-exact-head=true" in result.text


class PolicyRunner(FakeRunner):
    outputs = {
        0: b"Plan evidence\nentry HEAD: feedface\n",
        1: b"Review evidence\ncurrent tree = abc1234\n",
        2: b"Work evidence\norigin/main: deadbee\n",
        3: b"Final review\nupstream HEAD = cafe123\n",
    }

    def __call__(self, *args, **kwargs):
        index = len(self.calls)
        result = super().__call__(*args, **kwargs)
        if index in self.outputs:
            if index in (1, 3):
                return result._replace(stdout=review_payload(
                    args[1],
                    "plan_review" if index == 1 else "final_review",
                    "reviewed_with_findings",
                    self.outputs[index].decode("utf-8"),
                ))
            return result._replace(stdout=self.outputs[index])
        return result


def test_dispatch_sanitizes_only_model_facing_free_form_segments(
    repository: Path, tmp_path: Path
) -> None:
    request = PhaseRequest(
        "implementation_testing",
        "normal",
        "Task\nHEAD must equal abc1234\nUpdate input foo to commit deadbee\n",
    )
    runner = PolicyRunner()
    state = make_dispatcher(repository, tmp_path, runner).dispatch(PHASE_ID, request)
    run_directory = Path(state["run_directory"])

    plan_prompt = runner.calls[0]["prompt"].decode()
    plan_review_prompt = runner.calls[1]["prompt"].decode()
    work_prompt = runner.calls[2]["prompt"].decode()
    final_review_prompt = runner.calls[3]["prompt"].decode()
    closeout_prompt = runner.calls[4]["prompt"].decode()

    assert "HEAD must equal abc1234" not in plan_prompt
    assert "Update input foo to commit deadbee" in plan_prompt
    assert "entry HEAD: feedface" in plan_review_prompt
    # The run-owned plan is byte-bound material. Hash-like text inside it is
    # retained verbatim and classified as non-binding evidence by the envelope.
    assert "entry HEAD: feedface" in work_prompt
    assert "current tree = abc1234" not in work_prompt
    assert "origin/main: deadbee" in final_review_prompt
    assert "upstream HEAD = cafe123" not in closeout_prompt
    assert "non-binding evidence" in plan_review_prompt
    assert "Do not recreate a" in work_prompt

    for value in state["plan_candidate"].values():
        assert str(value) in plan_review_prompt
    for value in state["pre_final_candidate"].values():
        assert str(value) in final_review_prompt

    raw_request = json.loads((run_directory / "request.json").read_text())
    assert raw_request["prompt"] == request.prompt
    assert (run_directory / "01-plan.stdout.md").read_bytes() == PolicyRunner.outputs[0]
    assert (run_directory / "01-plan.prompt.md").read_bytes() == runner.calls[0]["prompt"]

    evidence = json.loads((run_directory / "prompt-policy.json").read_text())
    assert evidence["policy_version"] == prompt_policy.POLICY_VERSION
    assert evidence["sanitized"] is True
    assert evidence["total_removal_count"] == 4
    assert {segment["source"] for segment in evidence["segments"]} == {
        "request.prompt",
        "plan_review.stdout.forwarded_to_work",
        "work.stdout.forwarded_to_closeout",
        "final_review.stdout.forwarded_to_closeout",
    }
    assert all(segment["original_sha256"] for segment in evidence["segments"])
    assert all(segment["sanitized_sha256"] for segment in evidence["segments"])
    result = json.loads((run_directory / "result.json").read_text())
    assert result["prompt_policy"] == state["prompt_policy"]
