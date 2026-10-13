"""Provider-free qualification of ordinary V1 dispatch and V2 route execution with custom APGR-home."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
import tomllib

import pytest

# Sibling helpers below are imported after this path insertion.
DISPATCHER_DIR = Path(__file__).resolve().parent
if str(DISPATCHER_DIR) not in sys.path:
    sys.path.insert(0, str(DISPATCHER_DIR))

from agent_phase.bundle import publish_bundle
from agent_phase.dispatch import DispatchError, Dispatcher
from agent_phase.provider import Result, run as production_run
from agent_phase.request import PhaseRequest, parse_request_v2
from agent_phase.resolution_v2 import resolve_v2
from agent_phase.roster import load_roster
from agent_phase.v2_dispatch import V2DispatchError, dispatch_v2
from test_agent_phase_antigravity import repository


ROOT = Path(__file__).resolve().parents[3]


def _make_custom_home_bundle(
    tmp_path: Path,
    *,
    worker_modes: list[str] | None = None,
    custom_alias_claude: str = "home-custom-claude",
    custom_alias_codex: str = "home-custom-codex",
    custom_alias_gemini: str = "home-custom-gemini",
) -> Path:
    """Publish a valid isolated APGR-home bundle whose aliases, models, and worker settings differ from source."""
    source = tmp_path / "dispatcher-source"
    shutil.copytree(ROOT / "common/dispatcher", source)

    # 1. Custom parent and worker models/efforts
    models_path = source / "models.toml"
    models = models_path.read_text(encoding="utf-8")
    old_claude = (
        '[providers.claude.opus-high-review]\n'
        'model = "claude-opus-5-5"\n'
        'effort = "high"\n'
        'role = "opus"'
    )
    new_claude = (
        '[providers.claude.opus-high-review]\n'
        'model = "claude-fable-5-1"\n'
        'effort = "medium"\n'
        'role = "opus"'
    )
    old_luna = (
        '[providers.codex.luna-worker]\n'
        'model = "gpt-6-luna"\n'
        'effort = "max"'
    )
    new_luna = (
        '[providers.codex.luna-worker]\n'
        'model = "gpt-6-luna-next"\n'
        'effort = "xhigh"'
    )
    assert models.count(old_claude) == 1
    assert models.count(old_luna) == 1
    models = models.replace(old_claude, new_claude, 1)
    models = models.replace(old_luna, new_luna, 1)
    models = models.replace(
        'model = "gpt-6.1-sol"\neffort = "xhigh"',
        'model = "gpt-7-astra"\neffort = "high"',
    )
    models_path.write_text(models, encoding="utf-8")

    # 2. Worker settings fixed 4+4
    workers_path = source / "workers.toml"
    workers = workers_path.read_text(encoding="utf-8").replace('profile = "gemini-3.8-flash-high"', 'profile = "gemini-3.8-flash-medium"')
    if worker_modes is not None:
        modes_repr = json.dumps(worker_modes)
        workers = re.sub(
            r'mode_requirements\s*=\s*\[[^\]]*\]',
            f'mode_requirements = {modes_repr}',
            workers,
        )
    workers_path.write_text(workers, encoding="utf-8")

    # 3. Custom distinct valid endpoint aliases
    endpoints_path = source / "endpoints.toml"
    endpoints_text = endpoints_path.read_text(encoding="utf-8")
    endpoints_text += (
        f'\n[endpoints.{custom_alias_claude}]\n'
        'provider = "claude"\n'
        'profile = "opus-high-review"\n'
        f'\n[endpoints.{custom_alias_codex}]\n'
        'provider = "codex"\n'
        'profile = "implementation-testing"\n'
        f'\n[endpoints.{custom_alias_gemini}]\n'
        'provider = "antigravity"\n'
        'profile = "gemini-3.8-flash-high"\n'
    )
    endpoints_path.write_text(endpoints_text, encoding="utf-8")

    # 4. Capabilities for custom aliases
    caps_path = source / "capabilities.toml"
    caps_text = 'schema = "agent-phase-capabilities-v1"\ngeneration = 9\n'
    caps_text += (
        f'\n[endpoints.{custom_alias_claude}]\n'
        'provider = "claude"\n'
        'profile = "opus-high-review"\n'
        'capabilities = ["read", "reasoning", "subagent_workers"]\n'
        'posture = "read_only"\n'
        f'\n[endpoints.{custom_alias_codex}]\n'
        'provider = "codex"\n'
        'profile = "implementation-testing"\n'
        'capabilities = ["read", "mutation", "execution", "reasoning", "subagent_workers"]\n'
        'posture = "mutating"\n'
        f'\n[endpoints.{custom_alias_gemini}]\n'
        'provider = "antigravity"\n'
        'profile = "gemini-3.8-flash-high"\n'
        'capabilities = []\n'
        'posture = "read_only"\n'
    )
    caps_path.write_text(caps_text, encoding="utf-8")

    # 5. Routes mapped to custom aliases
    routes_path = source / "routes.toml"
    routes_text = routes_path.read_text(encoding="utf-8")

    # gemini_sub: custom claude reviews/plan, custom codex work/closeout
    old_gemini_sub = (
        '[routes.implementation_testing.gemini_sub]\n'
        'plan = "claude-opus-high-plan"\n'
        'plan_review = "claude-opus-high-review"\n'
        'work = "codex-implementation-testing"\n'
        'final_review = "claude-opus-high-review"\n'
        'closeout = "codex-implementation-testing"'
    )
    new_gemini_sub = (
        '[routes.implementation_testing.gemini_sub]\n'
        f'plan = "{custom_alias_claude}"\n'
        f'plan_review = "{custom_alias_claude}"\n'
        f'work = "{custom_alias_codex}"\n'
        f'final_review = "{custom_alias_claude}"\n'
        f'closeout = "{custom_alias_codex}"'
    )
    assert routes_text.count(old_gemini_sub) == 1
    routes_text = routes_text.replace(old_gemini_sub, new_gemini_sub, 1)

    # claude_only: all slots to custom claude
    old_claude_only = (
        '[routes.implementation_testing.claude_only]\n'
        'plan = "claude-opus-high-plan"\n'
        'plan_review = "claude-opus-high-review"\n'
        'work = "claude-only-implementation-primary"\n'
        'final_review = "claude-opus-high-review"\n'
        'closeout = "claude-only-implementation-primary"'
    )
    new_claude_only = (
        '[routes.implementation_testing.claude_only]\n'
        f'plan = "{custom_alias_claude}"\n'
        f'plan_review = "{custom_alias_claude}"\n'
        f'work = "{custom_alias_claude}"\n'
        f'final_review = "{custom_alias_claude}"\n'
        f'closeout = "{custom_alias_claude}"'
    )
    assert routes_text.count(old_claude_only) == 1
    routes_text = routes_text.replace(old_claude_only, new_claude_only, 1)

    # normal: plan custom gemini, work custom codex, review custom claude
    old_normal = (
        '[routes.implementation_testing.normal]\n'
        'plan = "codex-architecture-docs-primary"\n'
        'plan_review = "claude-normal-plan-review"\n'
        'work = "antigravity-gemini-high"\n'
        'final_review = "claude-normal-final-review"\n'
        'closeout = "codex-implementation-testing"'
    )
    new_normal = (
        '[routes.implementation_testing.normal]\n'
        f'plan = "{custom_alias_gemini}"\n'
        f'plan_review = "{custom_alias_claude}"\n'
        f'work = "{custom_alias_codex}"\n'
        f'final_review = "{custom_alias_claude}"\n'
        f'closeout = "{custom_alias_codex}"'
    )
    assert routes_text.count(old_normal) == 1
    routes_text = routes_text.replace(old_normal, new_normal, 1)

    routes_path.write_text(routes_text, encoding="utf-8")

    # Publish bundle to isolated APGR home
    home = tmp_path / "apgr-home"
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.toml").write_text(
        "[dispatcher.bundle]\nrequired = true\n", encoding="utf-8"
    )
    publish_bundle(source, home / "dispatcher")
    return home


def _fake_codex_bin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    bin_dir = tmp_path / "fake-codex-bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    fake_codex = bin_dir / "codex"
    fixture = (
        r"""#!""" + sys.executable + r"""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tomllib

if "--version" in sys.argv:
    print("codex 1.0.0")
    sys.exit(0)

if os.environ.get("APGR_WORKER_LEAF") == "1":
    assert "APGR_PARENT_ID" not in os.environ
    assert "APGR_WORKER_FACADE" not in os.environ
    assert "agents.enabled=false" in sys.argv
    assert 'model="gpt-6-luna-next"' in sys.argv
    assert 'model_reasoning_effort="xhigh"' in sys.argv
    assert sys.argv[sys.argv.index("--sandbox") + 1] == "read-only"
    workers_path = Path(os.environ["APGR_DISPATCH_WORKERS"])
    assert workers_path.is_file()
    assert hashlib.sha256(workers_path.read_bytes()).hexdigest() == os.environ["APGR_DISPATCH_WORKERS_SHA256"]
    workers = tomllib.loads(workers_path.read_text(encoding="utf-8"))
    assert workers["selections"]["triple_pool_4x4x4"]["luna_worker"]["profile"] == "luna-worker"
    sys.stdin.read()
    print(json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "fixture child"}}), flush=True)
    sys.exit(0)

# Parent execution fallback
prompt = sys.stdin.read()
m = re.search(r"<<<AGENT-PHASE-RESULT ([0-9a-f]{32})>>>", prompt)
if m:
    token = m.group(1)
    payload = json.dumps({
        "version": 1,
        "stage": "solo",
        "outcome": "completed",
        "body": "codex parent done",
        "commit_message": {"subject": "Codex change", "body": ""},
    })
    print(f"<<<AGENT-PHASE-RESULT {token}>>>\n{payload}\n<<<END-AGENT-PHASE-RESULT {token}>>>")
print(json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "codex parent"}}), flush=True)
"""
    )
    fake_codex.write_text(fixture, encoding="utf-8")
    fake_codex.chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])
    return fake_codex


def _fake_claude_bin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    bin_dir = tmp_path / "fake-claude-bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    fake_claude = bin_dir / "claude"
    fixture = (
        r"""#!""" + sys.executable + r"""
import json
import os
from pathlib import Path
import re
import sys

if "--version" in sys.argv:
    print("claude 2.1.250")
    sys.exit(0)

log_path = os.environ.get("FAKE_CLAUDE_LOG")
if log_path:
    record = {
        "argv": [a for a in sys.argv if not a.startswith("#")],
        "env": {k: os.environ[k] for k in ("APGR_MODEL_AUTHORITY", "APGR_WORKER_FACADE", "APGR_DISPATCH_MODELS_SHA256", "APGR_DISPATCH_WORKERS_SHA256") if k in os.environ},
    }
    Path(log_path).write_text(json.dumps(record, indent=2), encoding="utf-8")

prompt = sys.stdin.read()
m_phase = re.search(r"<<<AGENT-PHASE-RESULT ([0-9a-f]{32})>>>", prompt)
if m_phase:
    token = m_phase.group(1)
    payload = json.dumps({
        "version": 1,
        "stage": "solo",
        "outcome": "completed",
        "body": "claude parent completed",
        "commit_message": {"subject": "Claude solo change", "body": ""},
    })
    print(f"<<<AGENT-PHASE-RESULT {token}>>>\n{payload}\n<<<END-AGENT-PHASE-RESULT {token}>>>")

m_rev = re.search(r"<<<AGENT-REVIEW-RESULT ([0-9a-f]{32})>>>", prompt)
if m_rev:
    token = m_rev.group(1)
    payload = json.dumps({
        "version": 1,
        "stage": "review",
        "outcome": "reviewed_with_no_findings",
        "body": "Approved by claude review",
    })
    print(f"<<<AGENT-REVIEW-RESULT {token}>>>\n{payload}\n<<<END-AGENT-REVIEW-RESULT {token}>>>")

print(json.dumps({"type": "result", "subtype": "success", "result": "done"}))
"""
    )
    fake_claude.write_text(fixture, encoding="utf-8")
    fake_claude.chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])
    return fake_claude


def _fake_agy_bin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    bin_dir = tmp_path / "fake-agy-bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    fake_agy = bin_dir / "agy"
    fake_agy.write_text(
        r"""#!""" + sys.executable + r"""
import sys, json
print(json.dumps({"status": "completed"}))
""",
        encoding="utf-8",
    )
    fake_agy.chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])
    return fake_agy


# ---------------------------------------------------------------------------
# Test 1: V1 Dispatch with Custom Home Codex Native Worker
# ---------------------------------------------------------------------------


def test_v1_dispatch_custom_home_codex_native_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """V1 Dispatcher.dispatch executes custom home route with native Astra worker binding."""
    home = _make_custom_home_bundle(tmp_path)
    _fake_codex_bin(tmp_path, monkeypatch)
    repo = repository.__wrapped__(tmp_path)
    observed: dict[str, object] = {}

    def runner(argv, prompt, cwd, max_output, on_output=None):
        del cwd, max_output, on_output
        observed["argv"] = list(argv)
        # Scoped exactly-once model assertion to native-worker path
        assert argv.count('model="gpt-7-astra"') == 1
        assert 'model_reasoning_effort="high"' in argv
        assert 'agents.default_subagent_model="gpt-6-luna-next"' in argv
        assert 'agents.default_subagent_reasoning_effort="xhigh"' in argv
        assert os.environ.get("APGR_MODEL_AUTHORITY") == "captured-bundle"

        model_path = Path(os.environ["APGR_DISPATCH_MODELS"])
        worker_path = Path(os.environ["APGR_DISPATCH_WORKERS"])
        assert hashlib.sha256(model_path.read_bytes()).hexdigest() == os.environ["APGR_DISPATCH_MODELS_SHA256"]
        assert hashlib.sha256(worker_path.read_bytes()).hexdigest() == os.environ["APGR_DISPATCH_WORKERS_SHA256"]
        assert model_path.read_bytes() == (home / "dispatcher/models.toml").read_bytes()
        assert worker_path.read_bytes() == (home / "dispatcher/workers.toml").read_bytes()
        assert tomllib.loads(worker_path.read_text())["selections"]["triple_pool_4x4x4"]["gemini_worker"]["profile"] == "gemini-3.8-flash-medium"

        m = re.search(r"<<<AGENT-PHASE-RESULT ([0-9a-f]{32})>>>", prompt.decode())
        assert m is not None
        token = m.group(1)
        payload = json.dumps({
            "version": 1,
            "stage": "solo",
            "outcome": "completed",
            "body": "codex native done",
            "commit_message": {"subject": "Codex native worker commit", "body": ""},
        })
        stdout = f"<<<AGENT-PHASE-RESULT {token}>>>\n{payload}\n<<<END-AGENT-PHASE-RESULT {token}>>>\n".encode()
        now = time.time()
        return Result(0, stdout, b"", False, now, now)

    req = PhaseRequest("implementation_testing", "gemini_sub", "Implement feature with Codex native.")
    dispatcher = Dispatcher(
        ROOT,
        repo,
        run_root=tmp_path / "dispatcher-runs",
        resolve_scanner=False,
        runner=runner,
        apgr_home=home,
    )
    state = dispatcher.dispatch("V1-NATIVE-WORKER", req, lifecycle="solo", finalization_policy="checkpoint")
    assert state["outcome"] == "completed"
    assert "argv" in observed
    resolved = json.loads(next((tmp_path / "dispatcher-runs").rglob("resolved.json")).read_text())
    assert resolved["effective_stage_routes"]["solo"]["endpoint_alias"] == "home-custom-codex"


# ---------------------------------------------------------------------------
# Test 2: V1 Dispatch with Claude Real Launcher and Fake Claude PATH
# ---------------------------------------------------------------------------


def test_v1_dispatch_custom_home_claude_real_launcher(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """V1 Dispatcher.dispatch executes custom home route exercising real claude-profile launcher."""
    home = _make_custom_home_bundle(tmp_path)
    _fake_claude_bin(tmp_path, monkeypatch)
    repo = repository.__wrapped__(tmp_path)

    log_path = tmp_path / "claude_recorded_argv.json"
    monkeypatch.setenv("FAKE_CLAUDE_LOG", str(log_path))

    req = PhaseRequest("implementation_testing", "claude_only", "Implement feature with Claude launcher.")
    dispatcher = Dispatcher(
        ROOT,
        repo,
        run_root=tmp_path / "dispatcher-runs",
        claude_launcher=str(ROOT / "bin/claude-profile"),
        resolve_scanner=False,
        runner=production_run,
        apgr_home=home,
    )
    state = dispatcher.dispatch("V1-CLAUDE", req, lifecycle="solo", finalization_policy="checkpoint")
    assert state["outcome"] == "completed"

    assert log_path.exists(), "real claude-profile launcher did not execute fake claude"
    record = json.loads(log_path.read_text(encoding="utf-8"))
    claude_argv = record["argv"]

    # Verify custom parent model and effort from captured bundle
    assert "--model" in claude_argv
    assert claude_argv[claude_argv.index("--model") + 1] == "claude-fable-5-1"
    assert "--effort" in claude_argv
    assert claude_argv[claude_argv.index("--effort") + 1] == "medium"


# ---------------------------------------------------------------------------
# Test 3: Non-worker V1 applies captured selection once, including generation leases
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("generation_bound", [False, True])
def test_v1_dispatch_non_worker_applies_model_selection_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, generation_bound: bool
) -> None:
    """Captured selection occurs once after any pinned generation profile values."""
    from agent_phase.runtime_models import selection
    from controller_generation import LEASE_ENV, codex_profile_arguments

    home = _make_custom_home_bundle(tmp_path)
    repo = repository.__wrapped__(tmp_path)
    observed_argv: list[str] = []
    if generation_bound:
        lease = tmp_path / "generation.json"
        lease.write_text(json.dumps({"generation": {"generation_root": str(ROOT)}}))
        lease.chmod(0o600)
        monkeypatch.setenv(LEASE_ENV, str(lease))
    else:
        monkeypatch.delenv(LEASE_ENV, raising=False)

    def runner(argv, prompt, cwd, max_output, on_output=None):
        del cwd, max_output, on_output
        observed_argv.extend(argv)
        m = re.search(r"<<<AGENT-PHASE-RESULT ([0-9a-f]{32})>>>", prompt.decode())
        token = m.group(1) if m else "0" * 32
        payload = json.dumps({
            "version": 1,
            "stage": "solo",
            "outcome": "completed",
            "body": "non-worker done",
            "commit_message": {"subject": "Non-worker commit", "body": ""},
        })
        stdout = f"<<<AGENT-PHASE-RESULT {token}>>>\n{payload}\n<<<END-AGENT-PHASE-RESULT {token}>>>\n".encode()
        now = time.time()
        return Result(0, stdout, b"", False, now, now)

    # codex_only is non-worker; build_argv owns the one captured selection.
    req = PhaseRequest("implementation_testing", "codex_only", "Non-worker dispatch.")
    dispatcher = Dispatcher(
        ROOT,
        repo,
        run_root=tmp_path / "dispatcher-runs",
        codex_executable="/fake/bin/codex",
        resolve_scanner=False,
        runner=runner,
        apgr_home=home,
    )
    state = dispatcher.dispatch("V1-NON-WORKER", req, lifecycle="solo", finalization_policy="checkpoint")
    assert state["outcome"] == "completed"
    selected = selection(ROOT, "codex", "implementation-testing", bundle=dispatcher.roster.bundle)
    profile = codex_profile_arguments(ROOT, "implementation-testing")
    expected_overrides = [value for value in profile if value.startswith(("model=", "model_reasoning_effort="))]
    expected_overrides.extend([
        "model=" + json.dumps(selected["model"]),
        "model_reasoning_effort=" + json.dumps(selected["effort"]),
    ])
    assert [value for value in observed_argv if value.startswith(("model=", "model_reasoning_effort="))] == expected_overrides
    assert observed_argv.count('model="gpt-7-astra"') == 1
    assert observed_argv.count("model_reasoning_effort=" + json.dumps(selected["effort"])) == 1


# ---------------------------------------------------------------------------
# Test 4: V2 Dispatch Static Route Codex Native Worker (Exposes Missing apply_selection)
# ---------------------------------------------------------------------------


def test_v2_dispatch_static_route_codex_native_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """V2 static dispatch reaches runner; exposes bound_workers missing apply_selection for codex_parent."""
    home = _make_custom_home_bundle(tmp_path)
    _fake_codex_bin(tmp_path, monkeypatch)
    repo = repository.__wrapped__(tmp_path)

    captured_work_argv: list[str] = []

    def runner(*, run_id, binding, route, run_dir, argv=None, nonce=None, **kwargs):
        del run_id, route, run_dir, kwargs
        if binding.binding_id == "binding_work":
            captured_work_argv.extend(argv or [])
            (repo / "work.txt").write_text("work done\n", encoding="utf-8")
            return b"work completed"
        if binding.binding_id in ("binding_closeout", "binding_closeout_agent") and nonce:
            from agent_phase import result as result_module
            begin, end = result_module.markers(nonce)
            payload = {
                "version": 1,
                "stage": "closeout",
                "outcome": "completed",
                "body": "Closeout complete.",
                "commit_message": None,
            }
            return f"{begin}\n{json.dumps(payload)}\n{end}\n".encode("utf-8")
        return None

    raw_req = json.dumps({
        "schema": "agent-phase-request-v2",
        "phase_type": "implementation_testing",
        "prompt": "Test V2 static dispatch with native worker",
    }).encode("utf-8")
    req = parse_request_v2(raw_req)

    res = dispatch_v2(
        ROOT,
        repo,
        req,
        raw_req,
        execution_mode="gemini_sub",
        apgr_home=home,
        runner=runner,
        finalization_policy="checkpoint",
    )
    assert res["status"] == "completed"
    assert len(captured_work_argv) > 0
    assert 'model_reasoning_effort="high"' in captured_work_argv
    assert 'agents.default_subagent_model="gpt-6-luna-next"' in captured_work_argv
    assert 'agents.default_subagent_reasoning_effort="xhigh"' in captured_work_argv

    # Selected parent settings must survive native worker binding.
    has_custom_model = any('model="gpt-7-astra"' in a for a in captured_work_argv)
    assert has_custom_model, (
        "V2 native worker launch must retain selected parent model; "
        f"model='gpt-7-astra' not found in argv: {captured_work_argv}"
    )
    assert sum(1 for a in captured_work_argv if 'model="gpt-7-astra"' in a) == 1


# ---------------------------------------------------------------------------
# Test 5: V2 Dispatch Dynamic Route Custom Home
# ---------------------------------------------------------------------------


def test_v2_dispatch_dynamic_route_custom_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """V2 dynamic dispatch resolves capabilities from custom home bundle and completes launch."""
    home = _make_custom_home_bundle(tmp_path)
    _fake_codex_bin(tmp_path, monkeypatch)
    _fake_claude_bin(tmp_path, monkeypatch)
    _fake_agy_bin(tmp_path, monkeypatch)
    repo = repository.__wrapped__(tmp_path)

    invoked_bindings: list[str] = []

    def runner(*, run_id, binding, route, run_dir, argv=None, nonce=None, **kwargs):
        del run_id, run_dir, kwargs
        assert route.endpoint_alias.startswith("home-custom-")
        if route.provider == "codex":
            assert 'model="gpt-7-astra"' in argv
            assert 'model_reasoning_effort="high"' in argv
            assert 'agents.default_subagent_model="gpt-6-luna-next"' in argv
        assert Path(os.environ["APGR_DISPATCH_MODELS"]).read_bytes() == (home / "dispatcher/models.toml").read_bytes()
        invoked_bindings.append(binding.binding_id)
        if binding.is_mutating:
            (repo / f"{binding.binding_id}.txt").write_text("done\n", encoding="utf-8")
        if binding.binding_id in ("binding_closeout", "binding_closeout_agent") and nonce:
            from agent_phase import result as result_module
            begin, end = result_module.markers(nonce)
            payload = {
                "version": 1,
                "stage": "closeout",
                "outcome": "completed",
                "body": "Closeout complete.",
                "commit_message": None,
            }
            return f"{begin}\n{json.dumps(payload)}\n{end}\n".encode("utf-8")
        return None

    raw_req = json.dumps({
        "schema": "agent-phase-request-v2",
        "phase_type": "implementation_testing",
        "prompt": "Test V2 dynamic dispatch",
    }).encode("utf-8")
    req = parse_request_v2(raw_req)

    res = dispatch_v2(
        ROOT,
        repo,
        req,
        raw_req,
        execution_mode="dynamic",
        apgr_home=home,
        runner=runner,
        finalization_policy="checkpoint",
    )
    assert res["status"] == "completed"
    assert invoked_bindings == [
        "binding_plan",
        "binding_plan_review",
        "binding_work",
        "binding_work_review",
        "binding_closeout",
    ]


# ---------------------------------------------------------------------------
# Test 6: Capture roster, republish home, assert no mixed capability/model state
# ---------------------------------------------------------------------------


def test_capture_roster_republish_home_no_mixed_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Capturing roster snapshot then republishing home must not mix capabilities/models.

    Exposes defect: resolution_v2 root path misses passing roster=snap to load_capabilities.
    """
    home = _make_custom_home_bundle(
        tmp_path,
        custom_alias_claude="captured-claude-alias",
    )
    snap1 = load_roster(ROOT, apgr_home=home)
    assert "captured-claude-alias" in snap1.capabilities_catalog
    original_caps = set(snap1.capabilities_catalog["captured-claude-alias"].capabilities)

    # Republish home with a completely different bundle (removing captured-claude-alias)
    _make_custom_home_bundle(
        tmp_path / "repub-scratch",
        custom_alias_claude="republished-claude-alias",
    )
    replacement = tmp_path / "repub-scratch/dispatcher-source/models.toml"
    replacement.write_text(replacement.read_text().replace("gpt-7-astra", "gpt-8-astra").replace("gpt-6-luna-next", "gpt-6-luna-other"))
    publish_bundle(
        tmp_path / "repub-scratch/dispatcher-source",
        home / "dispatcher",
    )

    raw_req = json.dumps({
        "schema": "agent-phase-request-v2",
        "phase_type": "implementation_testing",
        "prompt": "Test resolution with captured roster against republished home",
    }).encode("utf-8")
    req = parse_request_v2(raw_req)

    # 1. Resolve using captured roster snapshot
    resolved = resolve_v2(
        req,
        ROOT,
        execution_mode="gemini_sub",
        apgr_home=home,
        roster=snap1,
    )
    plan_res = resolved["route_resolutions"]["binding_plan"]
    assert plan_res["endpoint_alias"] == "captured-claude-alias"

    # Resolution must use captured capabilities after the on-disk bundle is republished.
    resolved_caps = set(plan_res.get("capabilities", []))
    assert resolved_caps == original_caps, (
        f"V2 resolution must retain captured roster capabilities; "
        f"resolved capabilities {resolved_caps} differ from captured roster capabilities {original_caps}"
    )

    # 2. Launch using captured roster snapshot: must bind captured endpoints, not republished ones
    _fake_claude_bin(tmp_path, monkeypatch)
    _fake_codex_bin(tmp_path, monkeypatch)
    repo = repository.__wrapped__(tmp_path)
    captured_bindings: list[tuple[str, str]] = []

    def runner(*, run_id, binding, route, run_dir, argv=None, nonce=None, **kwargs):
        del run_id, run_dir, kwargs
        assert hashlib.sha256(Path(os.environ["APGR_DISPATCH_MODELS"]).read_bytes()).hexdigest() == snap1.bundle.members["models.toml"].sha256
        assert hashlib.sha256(Path(os.environ["APGR_DISPATCH_WORKERS"]).read_bytes()).hexdigest() == snap1.bundle.members["workers.toml"].sha256
        if route.provider == "codex":
            assert 'model="gpt-7-astra"' in argv
            assert 'agents.default_subagent_model="gpt-6-luna-next"' in argv
        captured_bindings.append((binding.binding_id, route.endpoint_alias))
        if binding.is_mutating:
            (repo / f"{binding.binding_id}.txt").write_text("done\n", encoding="utf-8")
        if binding.binding_id in ("binding_closeout", "binding_closeout_agent") and nonce:
            from agent_phase import result as result_module
            begin, end = result_module.markers(nonce)
            payload = {
                "version": 1,
                "stage": "closeout",
                "outcome": "completed",
                "body": "Closeout complete.",
                "commit_message": None,
            }
            return f"{begin}\n{json.dumps(payload)}\n{end}\n".encode("utf-8")
        return None

    res = dispatch_v2(
        ROOT,
        repo,
        req,
        raw_req,
        execution_mode="gemini_sub",
        apgr_home=home,
        roster=snap1,
        runner=runner,
        finalization_policy="checkpoint",
    )
    assert res["status"] == "completed"
    claude_bindings = [alias for bid, alias in captured_bindings if "plan" in bid or "review" in bid]
    assert len(claude_bindings) == 3
    assert all(alias == "captured-claude-alias" for alias in claude_bindings)
    assert not any("republished" in alias for _, alias in captured_bindings)


# ---------------------------------------------------------------------------
# Test 7: Missing Required Workers Blocks Runner in V1
# ---------------------------------------------------------------------------


def test_missing_required_workers_blocks_runner_v1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """V1 dispatch fails closed before runner when required workers are missing/unsupported."""
    home = _make_custom_home_bundle(tmp_path)
    # Keep disposable Git setup usable while making required Codex unavailable.
    git = shutil.which("git")
    fake_bin = tmp_path / "missing-worker-bin"
    fake_bin.mkdir()
    (fake_bin / "git").symlink_to(git)
    monkeypatch.setenv("PATH", str(fake_bin))
    repo = repository.__wrapped__(tmp_path)
    runner_called = False

    def runner(*args, **kwargs):
        nonlocal runner_called
        runner_called = True
        raise AssertionError("runner should not be invoked when workers are unavailable")

    req = PhaseRequest("implementation_testing", "gemini_sub", "Should fail before runner.")
    dispatcher = Dispatcher(
        ROOT,
        repo,
        run_root=tmp_path / "dispatcher-runs",
        codex_executable="/unavailable/codex",
        resolve_scanner=False,
        runner=runner,
        apgr_home=home,
    )
    with pytest.raises(DispatchError) as raised:
        dispatcher.dispatch("BLOCKED-V1", req, lifecycle="solo", finalization_policy="checkpoint")

    assert raised.value.code == "worker_unavailable"
    assert not runner_called, "runner was invoked despite missing required workers in V1"


# ---------------------------------------------------------------------------
# Test 8: Missing Required Workers Blocks Runner in V2
# ---------------------------------------------------------------------------


def test_missing_required_workers_blocks_runner_v2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """V2 dispatch fails closed before runner when required workers are missing/unsupported."""
    import agent_phase.worker_capability as wc
    from agent_phase.persistence import open_dispatcher_db, resolve_dispatcher_db_path

    home = _make_custom_home_bundle(tmp_path)
    _fake_codex_bin(tmp_path, monkeypatch)
    repo = repository.__wrapped__(tmp_path)

    # 1. Static V2 route: worker binary unavailable fails pre-launch before runner
    original_check = wc.check_worker_binaries
    monkeypatch.setattr(wc, "check_worker_binaries", lambda root, provider: (False, "agent-worker unavailable"))
    runner_called = False

    def runner(*args, **kwargs):
        nonlocal runner_called
        runner_called = True
        raise AssertionError("runner should not be invoked when workers are unavailable in V2 static")

    raw_req = json.dumps({
        "schema": "agent-phase-request-v2",
        "phase_type": "implementation_testing",
        "prompt": "Should fail before runner in V2",
    }).encode("utf-8")
    req = parse_request_v2(raw_req)

    with pytest.raises(V2DispatchError) as exc_info:
        dispatch_v2(
            ROOT,
            repo,
            req,
            raw_req,
            execution_mode="gemini_sub",
            apgr_home=home,
            runner=runner,
            finalization_policy="checkpoint",
        )

    assert "worker_unavailable" in str(exc_info.value)
    assert not runner_called, "runner was invoked despite missing required workers in V2 static"

    db_path = resolve_dispatcher_db_path(apgr_home=home)
    conn = open_dispatcher_db(db_path)
    row = conn.execute("SELECT status, outcome FROM runs ORDER BY created_at DESC LIMIT 1").fetchone()
    assert row["status"] == "failed"
    assert row["outcome"] == "failed_pre_launch"
    conn.close()

    # 2. Dynamic V2 route: worker policy excluding dynamic mode rejects route before runner
    monkeypatch.setattr(wc, "check_worker_binaries", original_check)
    home_dyn = _make_custom_home_bundle(tmp_path / "dyn", worker_modes=["normal"])
    runner_dyn_called = False

    def runner_dyn(*args, **kwargs):
        nonlocal runner_dyn_called
        runner_dyn_called = True
        raise AssertionError("runner should not be invoked when workers are unavailable in dynamic")

    res_dyn = dispatch_v2(
        ROOT,
        repo,
        req,
        raw_req,
        execution_mode="dynamic",
        apgr_home=home_dyn,
        runner=runner_dyn,
        finalization_policy="checkpoint",
    )
    assert res_dyn["status"] == "no_route"
    assert res_dyn["outcome"] == "no_route"
    assert "worker_unavailable" in res_dyn["detail"]
    assert not runner_dyn_called, "runner was invoked despite missing required workers in V2 dynamic"
