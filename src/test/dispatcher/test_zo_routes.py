"""Fresh source roster routes preserve endpoints, authority and worker availability."""
import json
from pathlib import Path
import tomllib

import pytest

from agent_phase.bundle import load_bundle
from agent_phase.request import EXECUTION_MODES, PHASE_TYPES, PhaseRequest
from agent_phase.routing import resolve
from agent_phase.runtime_models import apply_selection, captured, selection
from agent_phase.roster import Endpoint

ROOT = Path(__file__).resolve().parents[3]
SLOTS = ("plan", "plan_review", "work", "final_review", "closeout")

@pytest.mark.parametrize("phase", PHASE_TYPES)
def test_standard_gemini_sub_route(phase):
    bundle = load_bundle(repo_root=ROOT)
    with captured(bundle):
        result = resolve(PhaseRequest(phase, "gemini_sub", "bounded route proof"), ROOT,
                         "standard", "checkpoint")
        expected = [("claude-opus-5-5", "high"), ("claude-opus-5-5", "high"),
                    ("gpt-6.1-sol", "xhigh"), ("claude-opus-5-5", "high"),
                    ("gpt-6.1-sol", "xhigh")]
        assert [(result["stages"][s]["intelligence"]["model"],
                 result["stages"][s]["intelligence"]["effort"]) for s in SLOTS] == expected
        for stage in result["stages"].values():
            cap = stage["worker_capability"]
            assert cap["allowed"] and cap["policy_selection"] == "triple_pool_4x4x4"
            assert [cap["limits"]["max_" + k] for k in ("gemini", "luna", "sonnet")] == [4, 4, 4]
            assert cap["sonnet_worker"]["model"] == "claude-sonnet-5-5"
            assert cap["sonnet_worker"]["effort"] == "high"
            assert cap["sonnet_worker"]["transport"] == (
                "claude_native" if stage["provider"] == "claude" else "claude_external")

@pytest.mark.parametrize("phase", PHASE_TYPES)
@pytest.mark.parametrize("mode", [m for m in EXECUTION_MODES if m != "dynamic"])
def test_all_static_codex_slots_use_sol(phase, mode):
    bundle = load_bundle(repo_root=ROOT)
    with captured(bundle):
        result = resolve(PhaseRequest(phase, mode, "bounded static route proof"), ROOT,
                         "standard", "checkpoint")
        for stage in result["stages"].values():
            if stage["provider"] == "codex":
                assert stage["intelligence"]["model"] == "gpt-6.1-sol"
                assert stage["intelligence"]["effort"] == "xhigh"
            cap = stage.get("worker_capability")
            if mode in {"normal", "conserve_claude", "codex_only"}:
                assert not cap or not cap.get("allowed")
            if mode in {"gemini_opus", "gemini_fable"} and cap:
                assert "sonnet_worker" not in cap


def test_profile_readback_and_codex_argv(tmp_path):
    from apgr_workers.native_launch import prepare_native_binding, apply_native_binding
    from apgr_workers.policy import resolve_worker_capability
    bundle = load_bundle(repo_root=ROOT)
    with captured(bundle):
        for profile, spec in bundle.models_catalog["providers"]["codex"].items():
            if spec["role"] != "parent":
                continue
            source = tomllib.loads((ROOT / "codex/profiles" / (profile + ".config.toml")).read_text())
            selected = selection(ROOT, "codex", profile)
            assert (source["model"], source["model_reasoning_effort"]) == (selected["model"], selected["effort"])
            binding = prepare_native_binding(ROOT, parent_id="compile-" + profile,
                parent_profile=profile, workspace=tmp_path / "workspace",
                state_dir=tmp_path / "state", task_authority="read_only",
                capability=resolve_worker_capability(ROOT, "codex", profile, "gemini_sub"))
            assert (binding.parent_model, binding.parent_effort) == ("gpt-6.1-sol", "xhigh")
            assert (binding.native_model, binding.native_effort) == ("gpt-6-luna", "max")
            argv = apply_selection(apply_native_binding(["codex", "exec", "-"], binding), Endpoint("codex", profile), ROOT)
            assert argv.count('model="gpt-6.1-sol"') == 1
            assert argv.count('model_reasoning_effort="xhigh"') == 1
        luna = selection(ROOT, "codex", "luna-worker")
        assert (luna["model"], luna["effort"]) == ("gpt-6-luna", "max")


@pytest.mark.parametrize("phase", PHASE_TYPES)
@pytest.mark.parametrize("mode", [m for m in EXECUTION_MODES if m != "dynamic"])
def test_dispatcher_dry_run_current_routes(tmp_path, phase, mode):
    from agent_phase.dispatch import Dispatcher
    from test_agent_phase_antigravity import repository
    workspace = repository.__wrapped__(tmp_path)
    dispatcher = Dispatcher(ROOT, workspace, resolve_scanner=False,
                            apgr_home=tmp_path / "home", run_root=tmp_path / "outbox")
    result = dispatcher.dry_run("APG166ZO-ROUTE", PhaseRequest(phase, mode, "route proof"),
                                "standard", "checkpoint")
    assert result["provider_invocations"] == 0
    resolved = json.loads((Path(result["run_directory"]) / "resolved.json").read_text())
    for stage in resolved["stages"].values():
        if stage["provider"] == "codex":
            assert (stage["intelligence"]["model"], stage["intelligence"]["effort"]) == ("gpt-6.1-sol", "xhigh")
