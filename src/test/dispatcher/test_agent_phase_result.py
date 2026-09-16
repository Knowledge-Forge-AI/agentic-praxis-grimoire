"""Tests for dispatcher result artifacts, stage attribution, and ledger truth."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from agent_phase import candidate as candidate_module
from agent_phase import gitstate as gitstate_module
from agent_phase import result_artifacts as result_artifacts_module
from agent_phase import stage_delta as stage_delta_module
from agent_phase import failure_boundary as failure_boundary_module
from agent_phase import finalization as finalization_module
from agent_phase.result import CommitMessage, StageResult


def git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        check=False,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"git {args} failed: {completed.stderr}")
    return completed.stdout.strip()


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.name", "Tester")
    git(repo, "config", "user.email", "tester@example.com")
    git(repo, "config", "commit.gpgsign", "false")
    (repo / "README.md").write_text("# Test Repository\n")
    git(repo, "add", "README.md")
    git(repo, "commit", "-m", "Initial commit")
    return repo


class DummyDirectory:
    def __init__(self, path: Path, run_id: str = "test-run-1") -> None:
        self.path = path
        self.run_id = run_id
        self.written_files: dict[str, Any] = {}

    def write_json(self, name: str, data: Any) -> None:
        self.written_files[name] = data
        (self.path / name).write_text(json.dumps(data, indent=2))

    def write_text(self, name: str, text: str) -> None:
        self.written_files[name] = text
        (self.path / name).write_text(text)

    def write_bytes(self, name: str, data: bytes) -> None:
        self.written_files[name] = data
        (self.path / name).write_bytes(data)


def test_monotonic_manager_attention_accumulates_and_persists() -> None:
    state: dict[str, Any] = {}
    failure_boundary_module.record_manager_attention(
        state,
        reason="entry_dirt_overlap",
        detail="operator dirt overlapped",
        paths=["dirty.txt"],
        candidate_tree="tree123",
    )
    assert state["manager_disposition_required"] is True
    assert state["manager_attention_reasons"] == ["entry_dirt_overlap"]
    assert state["manager_disposition"]["reason"] == "entry_dirt_overlap"

    # Subsequent record appends reason without wiping out earlier attention
    failure_boundary_module.record_manager_attention(
        state,
        reason="git_authority_branch_mismatch",
        detail="branch changed",
        paths=["other.txt"],
        candidate_tree="tree456",
    )
    assert state["manager_disposition_required"] is True
    assert state["manager_attention_reasons"] == [
        "entry_dirt_overlap",
        "git_authority_branch_mismatch",
    ]


def test_product_deletions_participate_in_candidate(repository: Path) -> None:
    before = candidate_module.tree_identity(repository)
    (repository / "README.md").unlink()
    state: dict[str, Any] = {}
    deltas = stage_delta_module.capture_stage_boundary(
        repository, state, stage="work", before_tree=before
    )
    del_delta = next(d for d in deltas if d["path"] == "README.md")
    assert del_delta["status"] == "deleted"
    assert del_delta["classification"] == "product"
    assert del_delta["included_in_product_candidate"] is True


def test_stage_delta_ledger_inline_bounds_and_overflow(repository: Path, tmp_path: Path) -> None:
    directory = DummyDirectory(tmp_path / "run")
    directory.path.mkdir(parents=True)
    state: dict[str, Any] = {}
    deltas = [
        {
            "stage": "work",
            "path": f"file_{i}.txt",
            "status": "added",
            "classification": "product",
        }
        for i in range(300)
    ]
    stage_delta_module._record_deltas_to_ledger(
        state,
        "work",
        "before_sha",
        "after_sha",
        {},
        {},
        deltas,
        {},
        directory=directory,
    )
    ledger = state["stage_delta_ledger"]
    stage_info = ledger["stages"]["work"]
    # Stage inline deltas bounded to MAX_STAGE_INLINE_DELTAS (256)
    assert len(stage_info["deltas"]) == 256
    assert stage_info["observation_completeness"] == "truncated"
    assert stage_info["overflow"]["omitted_inline_count"] == 44
    assert (directory.path / "work.deltas.jsonl").exists()

    # Prompt summary bounds
    summary = stage_delta_module.format_stage_deltas_summary(state)
    assert "additional deltas omitted for prompt capacity" in summary


def test_git_authority_branch_mismatch_blocks_auto_publication(repository: Path) -> None:
    entry = gitstate_module.capture_entry(repository)
    git(repository, "checkout", "-b", "other-branch")
    state = {
        "lifecycle": "standard",
        "effective_stages": {"plan": {}, "plan_review": {}, "work": {}, "final_review": {}, "closeout": {}},
        "effective_checkpoints": ["post_planning", "pre_final"],
        "provider_invocations_performed": 5,
        "expected_stages": ["plan", "plan_review", "work", "final_review", "closeout"],
        "expected_provider_invocations": 5,
        "expected_review_count": 2,
    }
    parsed = StageResult(
        version=1,
        stage="closeout",
        outcome="completed",
        body="closeout complete",
        commit_message=CommitMessage("test subject", "test body"),
    )

    class DummyDisplay:
        def git_delta(self, *args: Any) -> None: pass
        def git_committing(self, *args: Any) -> None: pass
        def git_committed(self, *args: Any) -> None: pass

    with pytest.raises(finalization_module.FinalizationError) as exc:
        finalization_module.finalize_repository(
            state, entry, parsed, DummyDisplay(), resumed=False
        )
    assert exc.value.code == "GIT_AUTHORITY_BRANCH_MISMATCH"
    assert state["manager_disposition_required"] is True
    assert "git_authority_branch_mismatch" in state["manager_attention_reasons"]
    assert state["repository_finalized"] is False
    assert state["push"]["status"] == "not_attempted_branch_mismatch"


def test_result_md_stage_execution_story_and_plan_material_name(tmp_path: Path) -> None:
    directory = DummyDirectory(tmp_path / "run")
    directory.path.mkdir(parents=True)
    (directory.path / "plan-material.md").write_text("# Plan Material\n")
    (directory.path / "02-plan-review.result.json").write_text("{}\n")
    (directory.path / "03-work.stdout.md").write_text("producer evidence\n")
    (directory.path / "04-final-review.result.json").write_text("{}\n")
    (directory.path / "05-closeout.result.json").write_text("{}\n")
    (directory.path / "final_review.deltas.jsonl").write_text(
        '{"path":"overflow.py","status":"added"}\n'
    )

    state = {
        "run_id": "test-run",
        "project": "agent-central",
        "phase_id": "phase-1",
        "run_directory": str(directory.path),
        "outcome": "completed",
        "complete": True,
        "phase_type": "implementation_testing",
        "execution_mode": "normal",
        "lifecycle": "standard",
        "finalization_policy": "publish",
        "cwd": str(tmp_path),
        "stages_invoked": ["plan", "plan_review", "work", "final_review", "closeout"],
        "stages_completed": ["plan", "plan_review", "work", "final_review", "closeout"],
        "stage_transports_completed": ["plan", "plan_review", "work", "final_review", "closeout"],
        "planner_proposal": {
            "binding": {"schema": "plan-material-v1"},
            "artifact_name": "plan.material.bin",
            "exact_bytes": True,
            "implementation_authority": False,
        },
        "proposal_binding": {
            "schema": "plan-material-v1",
            "relative_path": "plan-material.md",
        },
        "producer_evidence": {
            "stage": "work",
            "artifact_name": "03-work.stdout.md",
            "outcome": "completed",
        },
        "revisor_input": {
            "producer_narrative": {
                "stage": "work",
                "artifact_basename": "03-work.stdout.md",
            },
            "work_review": {
                "stage": "final_review",
                "artifact_name": "04-final-review.result.json",
            },
        },
        "review_artifacts": [
            {
                "stage": "plan_review",
                "checkpoint": "post_planning",
                "name": "02-plan-review.result.json",
                "outcome": "accept",
            },
            {
                "stage": "final_review",
                "checkpoint": "pre_final",
                "name": "04-final-review.result.json",
                "outcome": "amend",
            },
        ],
        "review_outcomes": {
            "plan_review": "accept",
            "final_review": "amend",
        },
        "closer_disposition": "accept",
        "closer_rationale": "all findings accepted and addressed",
        "qualification_evidence": "focused dispatcher tests passed",
        "unresolved_concerns": "one deferred advisory",
        "manager_disposition_required": True,
        "manager_attention_reasons": [
            "entry_dirt_overlap",
            "git_authority_branch_mismatch",
        ],
        "closeout_delta": {"changed": True, "paths": ["pkg/mod.py"]},
        "cumulative_closeout_delta": {
            "changed": True,
            "paths": ["pkg/mod.py", "old.py"],
        },
        "final_candidate_reviewed": False,
        "terminal_result_stage": "closeout",
        "stage_delta_capture_error": {
            "code": "LEDGER_WRITE_FAILED",
            "detail": "bounded evidence retained",
        },
        "index_normalization_error": None,
        "failure_boundary_error": {
            "code": "FAILURE_LEDGER_WRITE_FAILED",
            "detail": "primary failure retained",
        },
        "stage_delta_ledger": {
            "schema": "agent-phase-stage-delta-v1",
            "deltas": [],
            "stages": {
                "plan": {
                    "stage": "plan",
                    "role": "planner",
                    "deltas": [],
                    "observation_completeness": "bounded",
                },
                "plan_review": {
                    "stage": "plan_review",
                    "role": "reviewer",
                    "deltas": [],
                    "observation_completeness": "bounded",
                },
                "work": {
                    "stage": "work",
                    "role": "producer",
                    "deltas": [
                        {"path": "pkg/mod.py", "status": "added", "classification": "product"},
                        {"path": "old.py", "status": "deleted", "classification": "product"},
                    ],
                    "product_paths": ["pkg/mod.py", "old.py"],
                    "total_deltas_count": 2,
                    "inline_deltas_count": 2,
                    "omitted_deltas_count": 0,
                    "observation_completeness": "bounded",
                    "before_git_authority": {
                        "branch": "main",
                        "head": "same-head",
                        "active_operations": [],
                    },
                    "after_git_authority": {
                        "branch": "main",
                        "head": "same-head",
                        "active_operations": [],
                    },
                },
                "final_review": {
                    "stage": "final_review",
                    "role": "reviewer",
                    "deltas": [
                        {"path": "pkg/mod.py", "status": "modified", "classification": "product"},
                    ],
                    "product_paths": ["pkg/mod.py"],
                    "total_deltas_count": 12,
                    "inline_deltas_count": 1,
                    "omitted_deltas_count": 11,
                    "observation_completeness": "truncated",
                    "overflow": {"name": "final_review.deltas.jsonl", "bytes": 48},
                    "observation_limitations": {
                        "classification": "bounded_scan",
                        "omitted_stage_deltas_count": 11,
                        "metadata_scan": {"omitted_roots": [".claude", ".scratch"]},
                    },
                },
                "closeout": {
                    "stage": "closeout",
                    "role": "closer",
                    "deltas": [
                        {
                            "path": "branch",
                            "status": "changed",
                            "classification": "git_authority",
                            "authority_event": {
                                "kind": "branch_change",
                                "before": "other-branch",
                                "after": "main",
                            },
                        },
                    ],
                    "before_git_authority": {
                        "branch": "other-branch",
                        "head": "same-head",
                        "active_operations": [],
                    },
                    "after_git_authority": {
                        "branch": "main",
                        "head": "same-head",
                        "active_operations": [],
                    },
                    "git_authority_paths": ["branch"],
                    "observation_completeness": "bounded",
                }
            },
        },
        "index_normalizations": [
            {
                "stage": "work",
                "safety": "normalized",
                "staged_changes": [{"path": "intent.txt", "status": "added"}],
                "intent_to_add_paths": ["intent.txt"],
                "reason": "provider-created index change normalized",
            },
        ],
    }
    invocations = [
        {"stage": "plan", "role": "planner", "provider": "codex", "profile": "default", "exit_code": 0},
        {"stage": "plan_review", "role": "reviewer", "provider": "codex", "profile": "default", "exit_code": 0},
        {"stage": "work", "role": "producer", "provider": "antigravity", "profile": "default", "exit_code": 0},
        {"stage": "final_review", "role": "reviewer", "provider": "codex", "profile": "default", "exit_code": 0},
        {"stage": "closeout", "role": "closer", "provider": "codex", "profile": "default", "exit_code": 0},
    ]
    result_artifacts_module.write(directory, state, invocations)

    result_json = json.loads((directory.path / "result.json").read_text())
    assert result_json["planner_proposal"]["artifact_name"] == "plan-material.md"
    assert result_json["producer_evidence"]["artifact_name"] == "03-work.stdout.md"
    assert result_json["terminal_result_artifact"] == "05-closeout.result.json"
    assert result_json["review_artifact_names"] == [
        "02-plan-review.result.json",
        "04-final-review.result.json",
    ]
    assert state["planner_proposal"] == result_json["planner_proposal"]
    assert state["producer_evidence"] == result_json["producer_evidence"]
    assert state["revisor_input"] == result_json["revisor_input"]

    references = result_json["artifact_references"]
    expected_references = {
        "plan_material": "plan-material.md",
        "producer_evidence": "03-work.stdout.md",
        "producer_narrative": "03-work.stdout.md",
        "terminal_result": "05-closeout.result.json",
        "dispatcher_result": "result.json",
    }
    for group, expected_name in expected_references.items():
        assert references[group]["name"] == expected_name
        assert not Path(expected_name).is_absolute()
        assert (directory.path / expected_name).is_file()
    assert {
        item["name"] for item in references["review_artifacts"]
    } == {"02-plan-review.result.json", "04-final-review.result.json"}
    for review in references["review_artifacts"]:
        assert not Path(review["name"]).is_absolute()
        assert (directory.path / review["name"]).is_file()

    result_md = (directory.path / "result.md").read_text()
    assert "## Stage execution story" in result_md
    assert "### Stages invoked" in result_md
    assert "### Stage changes and observations" in result_md
    assert "product additions" in result_md
    assert "product deletions" in result_md
    assert "Stage `final_review` (role: `reviewer`; disposition: `work reviewer`)" in result_md
    assert "observation limitations: bounded_scan; omitted metadata roots: .claude, .scratch" in result_md
    assert "overflow artifact: `final_review.deltas.jsonl`" in result_md
    assert "intent-to-add: `intent.txt`" in result_md
    assert "other-branch" in result_md
    assert "### Review outcomes (advisory)" in result_md
    assert "`plan_review` role=`plan reviewer`: **accept**" in result_md
    assert "### Boundary persistence observations" in result_md
    assert "stage_delta_capture_error" in result_md
    assert "### Closer disposition and revision delta" in result_md
    assert "all findings accepted and addressed" in result_md
    assert "focused dispatcher tests passed" in result_md
    assert "one deferred advisory" in result_md
    assert "entry_dirt_overlap" in result_md
    assert "### Artifact handoff" in result_md
    for expected_name in (
        "plan-material.md",
        "03-work.stdout.md",
        "02-plan-review.result.json",
        "04-final-review.result.json",
        "05-closeout.result.json",
        "result.json",
    ):
        assert f"`{expected_name}`" in result_md


def test_invalid_artifact_pointers_preserve_failure_handoff(tmp_path: Path) -> None:
    directory = DummyDirectory(tmp_path / "run")
    directory.path.mkdir(parents=True)

    state = {
        "run_id": "failed-run",
        "project": "agent-central",
        "phase_id": "phase-1",
        "run_directory": str(directory.path),
        "outcome": "blocked",
        "complete": False,
        "phase_type": "implementation_testing",
        "execution_mode": "normal",
        "lifecycle": "standard",
        "finalization_policy": "publish",
        "cwd": str(tmp_path),
        "blocking_reason": {
            "code": "PROVIDER_TRANSPORT_FAILED",
            "detail": "provider exited after changing the candidate",
        },
        "planner_proposal": {
            "artifact_name": "/private/secret/plan.md",
            "exact_bytes": True,
        },
        "producer_evidence": {
            "stage": "work",
            "artifact_name": "../outside.stdout.md",
        },
        "review_artifacts": [
            {
                "stage": "final_review",
                "name": "missing-review.result.json",
                "outcome": "unreviewable",
            },
        ],
        "terminal_result_stage": "closeout",
    }

    result_artifacts_module.write(directory, state, [])
    result_json = json.loads((directory.path / "result.json").read_text())
    assert result_json["blocking_reason"]["code"] == "PROVIDER_TRANSPORT_FAILED"
    assert result_json["planner_proposal"]["artifact_name"] is None
    assert result_json["producer_evidence"]["artifact_name"] is None
    assert result_json["review_artifacts"][0]["name"] is None
    assert result_json["artifact_references"]["dispatcher_result"]["name"] == "result.json"
    assert all(
        not isinstance(reference, dict)
        or reference.get("name") not in {"/private/secret/plan.md", "../outside.stdout.md"}
        for reference in result_json["artifact_references"].get("review_artifacts", [])
    )
    issue_pairs = {
        (item["pointer"], item["reason"])
        for item in result_json["artifact_reference_issues"]
    }
    assert ("planner_proposal.artifact_name", "unsafe_name") in issue_pairs
    assert ("producer_evidence.artifact_name", "unsafe_name") in issue_pairs
    assert ("review_artifacts[0].name", "missing_or_unusable") in issue_pairs
    assert ("terminal_result.artifact_name", "missing_or_unusable") in issue_pairs

    result_md = (directory.path / "result.md").read_text()
    assert "unavailable artifact pointers" in result_md
    assert "PROVIDER_TRANSPORT_FAILED" in result_md


def test_r2_fixture_three_modifications_zero_additions_zero_deletions(tmp_path: Path) -> None:
    directory = DummyDirectory(tmp_path / "run")
    directory.path.mkdir(parents=True)
    state = {
        "run_id": "r2-run",
        "project": "agent-central",
        "phase_id": "phase-1",
        "run_directory": str(directory.path),
        "outcome": "completed",
        "complete": True,
        "phase_type": "implementation_testing",
        "execution_mode": "normal",
        "lifecycle": "standard",
        "finalization_policy": "publish",
        "cwd": str(tmp_path),
        "stage_delta_ledger": {
            "schema": "agent-phase-stage-delta-v1",
            "stages": {
                "work": {
                    "stage": "work",
                    "role": "producer",
                    "product_paths": ["src/a.py", "src/b.py", "src/c.py"],
                    "classification_counts": {"product": 3},
                    "classification_status_counts": {"product": {"modified": 3}},
                    "deltas": [
                        {"path": "src/a.py", "classification": "product", "status": "modified"},
                        {"path": "src/b.py", "classification": "product", "status": "modified"},
                        {"path": "src/c.py", "classification": "product", "status": "modified"},
                    ],
                }
            }
        },
    }
    invocations = [
        {"stage": "work", "role": "producer", "provider": "antigravity", "profile": "default", "exit_code": 0}
    ]
    result_artifacts_module.write(directory, state, invocations)
    result_md = (directory.path / "result.md").read_text()
    assert "- product modifications (3): `src/a.py`, `src/b.py`, `src/c.py`" in result_md
    assert "product additions" not in result_md
    assert "product deletions" not in result_md


def test_mixed_status_stage_renders_exact_categories(tmp_path: Path) -> None:
    directory = DummyDirectory(tmp_path / "run")
    directory.path.mkdir(parents=True)
    state = {
        "run_id": "mixed-run",
        "project": "agent-central",
        "phase_id": "phase-1",
        "run_directory": str(directory.path),
        "outcome": "completed",
        "complete": True,
        "phase_type": "implementation_testing",
        "execution_mode": "normal",
        "lifecycle": "standard",
        "finalization_policy": "publish",
        "cwd": str(tmp_path),
        "stage_delta_ledger": {
            "schema": "agent-phase-stage-delta-v1",
            "stages": {
                "work": {
                    "stage": "work",
                    "role": "producer",
                    "product_paths": ["add.py", "mod.py", "del.py", "mode.py"],
                    "classification_counts": {"product": 4},
                    "classification_status_counts": {
                        "product": {"added": 1, "modified": 1, "deleted": 1, "type_changed": 1}
                    },
                    "deltas": [
                        {"path": "add.py", "classification": "product", "status": "added"},
                        {"path": "mod.py", "classification": "product", "status": "modified"},
                        {"path": "del.py", "classification": "product", "status": "deleted"},
                        {"path": "mode.py", "classification": "product", "status": "type_changed"},
                    ],
                }
            }
        },
    }
    invocations = [
        {"stage": "work", "role": "producer", "provider": "antigravity", "profile": "default", "exit_code": 0}
    ]
    result_artifacts_module.write(directory, state, invocations)
    result_md = (directory.path / "result.md").read_text()
    assert "- product additions (1): `add.py`" in result_md
    assert "- product modifications (2): `mod.py`, `mode.py`" in result_md
    assert "- product deletions (1): `del.py`" in result_md


def test_filtered_fallback_rejection() -> None:
    info = {
        "product_paths": ["m1.py", "m2.py"],
        "deltas": [
            {"path": "m1.py", "classification": "product", "status": "modified"},
            {"path": "m2.py", "classification": "product", "status": "modified"},
        ],
    }
    assert result_artifacts_module._paths_for(info, "product", ("added", "A")) == []
    assert result_artifacts_module._paths_for(info, "product", ("deleted", "D")) == []
    assert result_artifacts_module._paths_for(info, "product", ("modified", "M")) == ["m1.py", "m2.py"]
    info_no_deltas = {"product_paths": ["fallback.py"]}
    assert result_artifacts_module._paths_for(info_no_deltas, "product") == ["fallback.py"]


def test_detailed_records_omitted_by_bounds_reports_total_and_omitted_counts(tmp_path: Path) -> None:
    directory = DummyDirectory(tmp_path / "run")
    directory.path.mkdir(parents=True)
    paths = [f"file_{i:03d}.py" for i in range(300)]
    inline_paths = paths[:256]
    deltas = [{"path": p, "classification": "product", "status": "added"} for p in inline_paths]
    state = {
        "run_id": "bounded-run",
        "project": "agent-central",
        "phase_id": "phase-1",
        "run_directory": str(directory.path),
        "outcome": "completed",
        "complete": True,
        "phase_type": "implementation_testing",
        "execution_mode": "normal",
        "lifecycle": "standard",
        "finalization_policy": "publish",
        "cwd": str(tmp_path),
        "stage_delta_ledger": {
            "schema": "agent-phase-stage-delta-v1",
            "observation_completeness": "truncated",
            "stages": {
                "work": {
                    "stage": "work",
                    "role": "producer",
                    "product_paths": inline_paths,
                    "product_paths_total_count": 300,
                    "product_paths_omitted_count": 44,
                    "classification_counts": {"product": 300},
                    "classification_status_counts": {"product": {"added": 300}},
                    "observation_completeness": "truncated",
                    "omitted_deltas_count": 44,
                    "deltas": deltas,
                }
            }
        },
    }
    invocations = [
        {"stage": "work", "role": "producer", "provider": "antigravity", "profile": "default", "exit_code": 0}
    ]
    result_artifacts_module.write(directory, state, invocations)
    result_md = (directory.path / "result.md").read_text()
    assert "product additions (300; 256 inline, 44 omitted)" in result_md


def test_convenience_views_bounded_to_max_stage_inline_deltas() -> None:
    deltas = (
        [{"path": f"prod_{i}.py", "classification": "product", "status": "modified"} for i in range(300)]
        + [{"path": f".serena/meta_{i}.json", "classification": "operational_metadata", "status": "added"} for i in range(300)]
        + [{"path": f"git_auth_{i}", "classification": "git_authority", "status": "modified"} for i in range(300)]
    )
    state: dict[str, Any] = {}
    stage_delta_module._record_deltas_to_ledger(
        state,
        "work",
        "0" * 40,
        "1" * 40,
        None,
        None,
        deltas,
        {"status": "clean"},
    )
    record = state["stage_delta_ledger"]["stages"]["work"]
    assert len(record["product_paths"]) == stage_delta_module.MAX_STAGE_INLINE_DELTAS
    assert record["product_paths_total_count"] == 300
    assert record["product_paths_omitted_count"] == 44

    assert len(record["operational_metadata_paths"]) == stage_delta_module.MAX_STAGE_INLINE_DELTAS
    assert record["operational_metadata_paths_total_count"] == 300
    assert record["operational_metadata_paths_omitted_count"] == 44

    assert len(record["git_authority_paths"]) == stage_delta_module.MAX_STAGE_INLINE_DELTAS
    assert record["git_authority_paths_total_count"] == 300
    assert record["git_authority_paths_omitted_count"] == 44

    assert record["classification_status_counts"]["product"]["modified"] == 300
    assert record["classification_status_counts"]["operational_metadata"]["added"] == 300
    assert record["classification_status_counts"]["git_authority"]["modified"] == 300


def test_large_stage_finalization_independence(repository: Path) -> None:
    before_identity = candidate_module.tree_identity(repository)
    for i in range(300):
        (repository / f"large_{i:03d}.txt").write_text(f"content {i}\n")
    after_identity = candidate_module.tree_identity(repository)
    assert after_identity["tree"] != before_identity["tree"]
    delta = candidate_module.tree_delta(repository, str(before_identity["tree"]), str(after_identity["tree"]))
    assert len(delta) == 300


def test_large_staged_changes_normalization(repository: Path, tmp_path: Path) -> None:
    dummy_dir = DummyDirectory(tmp_path / "run")
    dummy_dir.path.mkdir(parents=True)
    for i in range(300):
        (repository / f"staged_{i:03d}.txt").write_text("initial\n")
    git(repository, "add", ".")
    git(repository, "commit", "-m", "commit 300 files")
    entry_index = gitstate_module.index_identity(repository)

    for i in range(300):
        (repository / f"staged_{i:03d}.txt").write_text("modified\n")
    git(repository, "add", ".")

    state: dict[str, Any] = {}
    norm = stage_delta_module.normalize_index_if_needed(
        repository, entry_index, state, stage_name="work", directory=dummy_dir
    )
    assert norm is not None
    assert norm["safety"] == "safe_restored"
    assert norm["restored_clean"] is True
    assert len(norm["staged_changes"]) == stage_delta_module.MAX_STAGE_INLINE_DELTAS
    assert norm["staged_changes_total_count"] == 300
    assert norm["staged_changes_omitted_count"] == 44
    assert len(norm["staged_paths"]) == stage_delta_module.MAX_STAGE_INLINE_DELTAS
    assert norm["staged_paths_total_count"] == 300
    assert norm["staged_paths_omitted_count"] == 44
    assert (dummy_dir.path / "work.index_normalizations.jsonl").is_file()
    lines = (dummy_dir.path / "work.index_normalizations.jsonl").read_text().strip().split("\n")
    assert len(lines) == 44

    diff_staged = git(repository, "diff", "--staged")
    assert diff_staged == ""
    assert (repository / "staged_000.txt").read_text() == "modified\n"


def test_large_intent_to_add_normalization(repository: Path, tmp_path: Path) -> None:
    dummy_dir = DummyDirectory(tmp_path / "run")
    dummy_dir.path.mkdir(parents=True)
    entry_index = gitstate_module.index_identity(repository)
    for i in range(300):
        (repository / f"intent_{i:03d}.txt").write_text(f"intent {i}\n")
    git(repository, "add", "-N", ".")

    state: dict[str, Any] = {}
    norm = stage_delta_module.normalize_index_if_needed(
        repository, entry_index, state, stage_name="work", directory=dummy_dir
    )
    assert norm is not None
    assert norm["safety"] == "safe_restored"
    assert norm["restored_clean"] is True
    assert len(norm["intent_to_add_paths"]) == stage_delta_module.MAX_STAGE_INLINE_DELTAS
    assert norm["intent_to_add_paths_total_count"] == 300
    assert norm["intent_to_add_paths_omitted_count"] == 44
    for i in range(300):
        assert (repository / f"intent_{i:03d}.txt").is_file()
    status = git(repository, "status", "--porcelain=v2")
    assert "1 .A" not in status


def test_unmerged_path_detected_as_unsafe_after_many_staged_paths(repository: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    entry_index = "clean-entry-index"
    monkeypatch.setattr(gitstate_module, "index_identity", lambda repo: "dirty-index")
    mock_changes = [
        {"path": f"staged_{i:03d}.txt", "status": "modified", "type": "tracked"}
        for i in range(300)
    ] + [{"path": "conflict.txt", "status": "unmerged", "type": "unmerged"}]
    monkeypatch.setattr(stage_delta_module, "inspect_index_changes", lambda root, **kw: mock_changes)

    state: dict[str, Any] = {}
    with pytest.raises(gitstate_module.GitStateError) as caught:
        stage_delta_module.normalize_index_if_needed(
            repository, entry_index, state, stage_name="work"
        )
    assert caught.value.code == "ENTRY_UNMERGED"
    assert len(state["index_normalizations"]) == 1
    norm = state["index_normalizations"][0]
    assert norm["safety"] == "unsafe"
    assert norm["unmerged_paths"] == ["conflict.txt"]


def test_interstage_metadata_modification_unattributed_to_next_stage(repository: Path) -> None:
    state: dict[str, Any] = {}
    b1 = stage_delta_module.StageBoundary(repository, "plan", state=state)
    b1.close()

    serena_dir = repository / ".serena"
    serena_dir.mkdir(parents=True, exist_ok=True)
    (serena_dir / "interstage.json").write_text("{\"gap\": true}\n")

    b2 = stage_delta_module.StageBoundary(repository, "work", state=state)
    assert "interstage_observations" in state
    assert any(".serena/interstage.json" in p for obs in state.get("interstage_observations", []) for p in obs.get("paths", []))

    (serena_dir / "work.json").write_text("{\"stage\": \"work\"}\n")
    b2.close()

    work_deltas = state["stage_delta_ledger"]["stages"]["work"]["deltas"]
    work_paths = {d["path"] for d in work_deltas}
    assert ".serena/work.json" in work_paths
    assert ".serena/interstage.json" not in work_paths


def test_stage_entry_exact_metadata_baseline(repository: Path) -> None:
    state: dict[str, Any] = {}
    serena_dir = repository / ".serena"
    serena_dir.mkdir(parents=True, exist_ok=True)
    target = serena_dir / "test.json"
    target.write_text("initial\n")

    boundary = stage_delta_module.StageBoundary(repository, "work", state=state)
    target.write_text("modified by provider\n")
    boundary.close()

    work_deltas = state["stage_delta_ledger"]["stages"]["work"]["deltas"]
    assert any(d["path"] == ".serena/test.json" and d["status"] == "modified" for d in work_deltas)


def test_stage_with_only_index_normalization_never_reports_no_changes_observed(tmp_path: Path) -> None:
    directory = DummyDirectory(tmp_path / "run")
    directory.path.mkdir(parents=True)
    state = {
        "run_id": "norm-only-run",
        "project": "agent-central",
        "phase_id": "phase-1",
        "run_directory": str(directory.path),
        "outcome": "completed",
        "complete": True,
        "phase_type": "implementation_testing",
        "execution_mode": "normal",
        "lifecycle": "standard",
        "finalization_policy": "publish",
        "cwd": str(tmp_path),
        "stage_delta_ledger": {
            "schema": "agent-phase-stage-delta-v1",
            "stages": {
                "work": {
                    "stage": "work",
                    "role": "producer",
                    "product_paths": [],
                    "classification_counts": {},
                    "deltas": [],
                    "index_normalizations": [
                        {
                            "stage": "work",
                            "safety": "normalized",
                            "staged_paths": ["staged.txt"],
                            "reason": "provider staged file",
                        }
                    ],
                }
            }
        },
        "index_normalizations": [
            {
                "stage": "work",
                "safety": "normalized",
                "staged_paths": ["staged.txt"],
                "reason": "provider staged file",
            }
        ],
    }
    invocations = [
        {"stage": "work", "role": "producer", "provider": "antigravity", "profile": "default", "exit_code": 0}
    ]
    result_artifacts_module.write(directory, state, invocations)
    result_md = (directory.path / "result.md").read_text()
    work_section = result_md.split("Stage `work`")[1].split("###")[0]
    assert "No changes observed." not in work_section
    assert "No product or metadata path delta observed; index anomaly recorded." in work_section
    assert "index normalization/anomaly: `normalized`" in result_md


def test_truncated_cross_stage_history_wording(tmp_path: Path) -> None:
    directory = DummyDirectory(tmp_path / "run")
    directory.path.mkdir(parents=True)
    state = {
        "run_id": "truncated-history-run",
        "project": "agent-central",
        "phase_id": "phase-1",
        "run_directory": str(directory.path),
        "outcome": "completed",
        "complete": True,
        "phase_type": "implementation_testing",
        "execution_mode": "normal",
        "lifecycle": "standard",
        "finalization_policy": "publish",
        "cwd": str(tmp_path),
        "stage_delta_ledger": {
            "schema": "agent-phase-stage-delta-v1",
            "observation_completeness": "truncated",
            "omitted_deltas_count": 10,
            "stages": {
                "work": {
                    "stage": "work",
                    "role": "producer",
                    "product_paths": ["a.py"],
                    "observation_completeness": "truncated",
                    "omitted_deltas_count": 10,
                    "deltas": [{"path": "a.py", "classification": "product", "status": "modified"}],
                }
            }
        },
    }
    invocations = [
        {"stage": "work", "role": "producer", "provider": "antigravity", "profile": "default", "exit_code": 0}
    ]
    result_artifacts_module.write(directory, state, invocations)
    result_md = (directory.path / "result.md").read_text()
    assert "- Cross-stage reversions or supersessions: none detected in bounded inline evidence." in result_md
    assert "- No cross-stage path reversions or supersessions detected." not in result_md


def test_artifact_reference_validation_covers_index_normalizations(tmp_path: Path) -> None:
    directory = DummyDirectory(tmp_path / "run")
    directory.path.mkdir(parents=True)
    valid_file = directory.path / "work.index_normalizations.jsonl"
    valid_file.write_text("{}\n")

    issues: list[dict[str, str]] = []
    norms = [
        {
            "stage": "work",
            "overflow_artifact": {"name": "work.index_normalizations.jsonl"},
        },
        {
            "stage": "plan",
            "overflow_artifact": {"name": "/etc/passwd"},
        },
        {
            "stage": "closeout",
            "overflow_artifact": {"name": "missing.jsonl"},
        },
    ]
    validated = result_artifacts_module._validated_index_normalizations(directory, norms, issues=issues)
    assert validated[0]["overflow_artifact"]["name"] == "work.index_normalizations.jsonl"
    assert validated[1]["overflow_artifact"]["name"] is None
    assert validated[2]["overflow_artifact"]["name"] is None

    issue_map = {(i["pointer"], i["reason"]) for i in issues}
    assert ("index_normalizations[1].overflow_artifact", "unsafe_name") in issue_map
    assert ("index_normalizations[2].overflow_artifact", "missing_or_unusable") in issue_map


def _closeout_state(tmp_path: Path, **extra: Any) -> dict[str, Any]:
    return {"run_id": "closeout-evidence", "project": "test", "phase_id": "test",
            "cwd": str(tmp_path), "run_directory": str(tmp_path), "outcome": "completed", "complete": True,
            "lifecycle": "standard", "phase_type": "implementation_testing",
            "execution_mode": "normal", "finalization_policy": "publish", **extra}


def test_top_metadata_and_interstage_handoffs_are_bounded(tmp_path: Path) -> None:
    paths = [f".scratch/{i:04d}" for i in range(1500)]
    state = _closeout_state(tmp_path, stage_delta_ledger={"stages": {"work": {
        "operational_metadata_paths": paths[:256],
        "operational_metadata_paths_total_count": 1500,
        "classification_counts": {"operational_metadata": 1500},
        "deltas": [],
    }}}, interstage_observations=[{
        "preceding_stage": "work", "following_stage": "final_review",
        "paths": [".scratch/gap"], "paths_total_count": 1,
    }])
    directory = DummyDirectory(tmp_path)
    result_artifacts_module.write(directory, state, [])
    result = json.loads((tmp_path / "result.json").read_text())
    assert len(result["operational_metadata_paths"]) == 256
    assert result["operational_metadata_paths_total_count"] == 1500
    assert result["operational_metadata_paths_inline_count"] == 256
    assert result["operational_metadata_paths_omitted_count"] == 1244
    assert result["interstage_observations"][0]["paths"] == [".scratch/gap"]
    md = (tmp_path / "result.md").read_text()
    assert "1490 paths omitted/unavailable in Markdown" in md
    assert "between `work` and `final_review`: total=1, inline=1, omitted=0; unattributed to providers" in md
    assert paths[20] not in md


def test_unknown_status_and_malformed_inherited_counts_remain_reportable(tmp_path: Path) -> None:
    state = _closeout_state(tmp_path, stage_delta_ledger={"stages": {
        "work": {"classification_status_counts": {"product": {"modified": 3, "unknown": 2, "added": None}},
                 "deltas": [{"path": "m", "classification": "product", "status": "modified"},
                            {"path": "u", "classification": "product", "status": "unknown"}],
                 "operational_metadata_paths_total_count": "bad", "omitted_deltas_count": None},
        "closeout": {"overflow": "bad", "classification_status_counts": None},
    }}, index_normalizations=[{"stage": "work", "staged_paths": ["m"],
        "staged_paths_total_count": None, "staged_changes_total_count": "bad",
        "intent_to_add_paths_total_count": "bad", "unmerged_paths_total_count": None}])
    result_artifacts_module.write(DummyDirectory(tmp_path), state, [])
    md = (tmp_path / "result.md").read_text()
    assert "product modifications (3; 1 inline, 2 omitted)" in md
    assert "product other/unclassified status (2; 1 shown, 1 paths omitted/unavailable): `u`" in md


@pytest.mark.parametrize("ledger", [False, True])
def test_alias_overflow_validation_preserves_single_true_issue(tmp_path: Path, ledger: bool) -> None:
    overflow = {"name": "missing.jsonl"}
    record = {"overflow": overflow, "overflow_artifact": overflow}
    issues: list[dict[str, str]] = []
    if ledger:
        result = result_artifacts_module._validated_stage_ledger(
            DummyDirectory(tmp_path), {"stages": {"work": record}}, issues=issues)["stages"]["work"]
    else:
        result = result_artifacts_module._validated_index_normalizations(
            DummyDirectory(tmp_path), [record], issues=issues)[0]
    assert result["overflow"]["name"] is None
    assert result["overflow_artifact"]["name"] is None
    assert len(issues) == 1
    assert issues[0]["reason"] == "missing_or_unusable"


def test_counts_without_any_inline_status_never_fabricate_categories(tmp_path: Path) -> None:
    state = _closeout_state(tmp_path, stage_delta_ledger={"stages": {"work": {
        "classification_counts": {"product": 300}, "product_paths_total_count": 300,
        "product_paths": [], "deltas": [], "omitted_deltas_count": 300,
    }}})
    result_artifacts_module.write(DummyDirectory(tmp_path), state, [])
    md = (tmp_path / "result.md").read_text()
    assert "product paths (300; 0 inline, 300 omitted; status unavailable in inline evidence)" in md
    assert "product additions" not in md
    assert "product modifications" not in md
    assert "product deletions" not in md


def test_stage_latest_index_alias_has_validated_pointer(tmp_path: Path) -> None:
    record = {"overflow": {"name": "missing.jsonl"}}
    issues: list[dict[str, str]] = []
    ledger = result_artifacts_module._validated_stage_ledger(DummyDirectory(tmp_path), {
        "stages": {"work": {"index_normalizations": [record], "index_normalization": record}}
    }, issues=issues)
    info = ledger["stages"]["work"]
    assert info["index_normalization"]["overflow"]["name"] is None
    assert len(issues) == 1


def test_invalid_status_totals_cannot_suppress_known_inline_paths(tmp_path: Path) -> None:
    state = _closeout_state(tmp_path, stage_delta_ledger={"stages": {"work": {
        "classification_status_counts": {"product": {"added": None, "modified": "bad", "deleted": -1}},
        "deltas": [{"path": status, "classification": "product", "status": status}
                   for status in ("added", "modified", "deleted")],
    }}})
    result_artifacts_module.write(DummyDirectory(tmp_path), state, [])
    md = (tmp_path / "result.md").read_text()
    assert "product additions (1): `added`" in md
    assert "product modifications (1): `modified`" in md
    assert "product deletions (1): `deleted`" in md
