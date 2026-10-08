"""Provider-free qualification of the ordinary APGR-home launch path."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import tomllib

import pytest

from agent_phase.bundle import publish_bundle
from agent_phase.bundle_io import BundleNotFoundError
from agent_phase.dispatch import Dispatcher
from agent_phase.envelope import RenderedPrompt
from agent_phase.gitstate import capture_entry
from agent_phase.routing import Endpoint, RoutingError, describe
from agent_phase.run import RunDirectory, stage_parent_id
from agent_phase.runtime_models import ModelAuthorityConflict, selection
from agent_phase.worker_capability import resolve_worker_capability
from agent_phase.provider import Result
from apgr_workers.ledger import ParentLedger
from test_agent_phase_antigravity import repository


ROOT = Path(__file__).resolve().parents[3]


def _home_bundle(tmp_path: Path) -> Path:
    """Publish a valid home bundle whose selected values differ from source."""
    source = tmp_path / "dispatcher-source"
    shutil.copytree(ROOT / "common/dispatcher", source)
    models_path = source / "models.toml"
    models = models_path.read_text(encoding="utf-8")
    old_claude = '[providers.claude.opus-high-review]\nmodel = "claude-opus-5-5"\neffort = "high"\nrole = "opus"'
    new_claude = '[providers.claude.opus-high-review]\nmodel = "claude-fable-5-1"\neffort = "medium"\nrole = "opus"'
    old_luna = '[providers.codex.luna-worker]\nmodel = "gpt-6-luna"\neffort = "max"'
    new_luna = '[providers.codex.luna-worker]\nmodel = "gpt-6-luna-next"\neffort = "xhigh"'
    assert models.count(old_claude) == 1
    assert models.count(old_luna) == 1
    models = models.replace(old_claude, new_claude, 1)
    models = models.replace(old_luna, new_luna, 1)
    models = models.replace('model = "gpt-6.1-sol"\neffort = "xhigh"', 'model = "gpt-7-astra"\neffort = "high"')
    models_path.write_text(models, encoding="utf-8")

    home = tmp_path / "apgr-home"
    home.mkdir()
    (home / "config.toml").write_text(
        "[dispatcher.bundle]\nrequired = true\n", encoding="utf-8"
    )
    publish_bundle(source, home / "dispatcher")
    return home


CODEX_FIXTURE = r'''
import hashlib
import json
import os
from pathlib import Path
import sys
import tomllib

assert os.environ.get("APGR_WORKER_LEAF") == "1"
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
'''


@pytest.fixture(autouse=True)
def _fake_codex(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bin_dir = tmp_path / "fake-bin"
    bin_dir.mkdir()
    executable = bin_dir / "codex"
    executable.write_text("#!" + sys.executable + "\n" + CODEX_FIXTURE, encoding="utf-8")
    executable.chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])


def test_home_bundle_reaches_real_stage_and_external_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A home selection reaches the parent seam and the actual child argv."""
    home = _home_bundle(tmp_path)
    repo = repository.__wrapped__(tmp_path)
    directory = RunDirectory(tmp_path / "runs", "home-path", "APG166SR1")
    observed: dict[str, object] = {}

    def runner(argv, prompt, cwd, max_output, on_output=None):
        del prompt, cwd, max_output, on_output
        observed["argv"] = list(argv)
        assert argv[1:] == ["opus-high-review", "--read-only", "-p"]
        assert Path(os.environ["APGR_HOME"]).resolve() == home.resolve()
        assert os.environ["APGR_MODEL_AUTHORITY"] == "captured-bundle"
        model_path = Path(os.environ["APGR_DISPATCH_MODELS"])
        worker_path = Path(os.environ["APGR_DISPATCH_WORKERS"])
        models = tomllib.loads(model_path.read_text(encoding="utf-8"))
        selected_parent = models["providers"]["claude"]["opus-high-review"]
        assert selected_parent["model"] == "claude-fable-5-1"
        assert selected_parent["effort"] == "medium"
        assert hashlib.sha256(model_path.read_bytes()).hexdigest() == os.environ["APGR_DISPATCH_MODELS_SHA256"]
        assert hashlib.sha256(worker_path.read_bytes()).hexdigest() == os.environ["APGR_DISPATCH_WORKERS_SHA256"]
        from claude_vc_profile import resolve_profile

        resolved = resolve_profile(ROOT / "claude", "opus-high-review")
        assert resolved.resolved_model_id == "claude-fable-5-1"
        assert resolved.source_profile["effort"] == "medium"
        assert os.environ.get("APGR_WORKER_FACADE") == "1"
        child = subprocess.run(
            [str(ROOT / "bin/agent-worker"), "job", "launch", "--key", "home-child",
             "--worker-kind", "luna", "--task", "Inspect selected child",
             "--task-authority", "read_only", "--acceptance-criteria", "Return fixture observation"],
            capture_output=True, text=True, timeout=30, check=False,
        )
        assert child.returncode == 0, {"stdout": child.stdout, "stderr": child.stderr}
        launch = json.loads(child.stdout)
        wait = subprocess.run(
            [str(ROOT / "bin/agent-worker"), "job", "wait", "--job-id", launch["job_id"],
             "--timeout", "20"],
            capture_output=True, text=True, timeout=30, check=False,
        )
        assert wait.returncode == 0, wait.stderr
        result = json.loads(wait.stdout)
        assert result["status"] == "completed", result
        assert result["cleanup_proven"] is True, result
        observed["child"] = result
        now = time.time()
        return Result(0, b"fake Claude parent", b"", False, now, now)

    dispatcher = Dispatcher(
        ROOT, repo, run_root=tmp_path / "dispatcher-runs", resolve_scanner=False,
        runner=runner, apgr_home=home,
    )
    # Load the home authority before introducing the ambient legacy marker. The
    # launch itself must then replace that marker with its captured selection.
    assert dispatcher.roster.bundle.bundle_dir == home / "dispatcher"
    monkeypatch.setenv("APGR_MODEL_AUTHORITY", "source-defaults")
    dispatcher._bind_stage_accounting(
        {"execution_mode": "gemini_sub", "controller_generation": {"commit": "a" * 40}},
        directory, entry=capture_entry(repo),
    )
    data = b"Inspect the selected APGR-home worker.\n"
    result, meta = dispatcher._stage(
        directory, 1, "work", "01-work", "reviewer",
        Endpoint("claude", "opus-high-review"),
        RenderedPrompt(data, [{"kind": "task_prompt", "start": 0, "end": len(data)}]),
        None, read_only=True,
    )
    assert result.ok, result.stderr.decode()
    assert meta["worker_capability"]["allowed"] is True
    assert meta["worker_drain"]["uncertain_cleanup"] is False
    assert observed["child"]["status"] == "completed"
    status = ParentLedger(
        stage_parent_id(directory.run_id, "work", 1), directory.path / "workers"
    ).get_status()
    assert status["status"] == "closed"
    assert status["policy"]["policy_selection"] == "triple_pool_4x4x4"
    assert status["external_counts"] == {"gemini": 0, "luna": 0, "sonnet": 0}
    assert status["worker_capability"]["luna_worker"]["model"] == "gpt-6-luna-next"
    assert status["worker_capability"]["luna_worker"]["effort"] == "xhigh"


def test_required_home_bundle_missing_fails_before_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "missing-home"
    home.mkdir()
    (home / "config.toml").write_text(
        "[dispatcher.bundle]\nrequired = true\n", encoding="utf-8"
    )
    repo = repository.__wrapped__(tmp_path)
    sentinel = tmp_path / "provider-started"

    def runner(*args, **kwargs):
        del args, kwargs
        sentinel.write_text("invoked", encoding="utf-8")
        raise AssertionError("provider started before required home validation")

    dispatcher = Dispatcher(
        ROOT, repo, run_root=tmp_path / "dispatcher-runs", resolve_scanner=False,
        runner=runner, apgr_home=home,
    )
    directory = RunDirectory(tmp_path / "runs", "missing-home", "APG166SR1")
    data = b"This provider must not start.\n"
    with pytest.raises(RoutingError) as raised:
        dispatcher._stage(
            directory, 1, "work", "01-work", "primary",
            Endpoint("claude", "implementation-primary"),
            RenderedPrompt(data, [{"kind": "task_prompt", "start": 0, "end": len(data)}]),
            None, read_only=False,
        )
    assert "required" in str(raised.value)
    cause = raised.value
    causes = []
    while cause is not None:
        causes.append(cause)
        cause = cause.__cause__
    assert any(isinstance(item, BundleNotFoundError) for item in causes)
    assert not sentinel.exists()


def test_ambient_source_defaults_cannot_bypass_home_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = _home_bundle(tmp_path)
    monkeypatch.setenv("APGR_HOME", str(home))
    monkeypatch.setenv("APGR_MODEL_AUTHORITY", "source-defaults")
    endpoint = Endpoint("codex", "implementation-testing")

    with pytest.raises(ModelAuthorityConflict):
        selection(ROOT, endpoint.provider, endpoint.profile)
    with pytest.raises(ModelAuthorityConflict):
        describe(ROOT, "primary", endpoint)
    with pytest.raises(ModelAuthorityConflict):
        resolve_worker_capability(ROOT, endpoint.provider, endpoint.profile, "gemini_sub")
    from claude_vc_profile import resolve_profile

    with pytest.raises(ModelAuthorityConflict):
        resolve_profile(ROOT / "claude", "opus-high-review")


def test_home_bundle_reaches_real_codex_stage_native_binding(tmp_path, monkeypatch):
    home = _home_bundle(tmp_path)
    repo = repository.__wrapped__(tmp_path)
    directory = RunDirectory(tmp_path / "runs", "native-home-path", "APG166SR1")
    calls = []

    def runner(argv, prompt, cwd, max_output, on_output=None):
        calls.append(list(argv))
        assert argv.count('model="gpt-7-astra"') == 1
        assert 'model_reasoning_effort="high"' in argv
        assert 'agents.default_subagent_model="gpt-6-luna-next"' in argv
        assert 'agents.default_subagent_reasoning_effort="xhigh"' in argv
        assert os.environ["APGR_MODEL_AUTHORITY"] == "captured-bundle"
        now = time.time()
        return Result(0, b"fake Codex parent", b"", False, now, now)

    dispatcher = Dispatcher(ROOT, repo, run_root=tmp_path / "dispatch", resolve_scanner=False, runner=runner, apgr_home=home)
    assert dispatcher.roster.bundle.bundle_dir == home / "dispatcher"
    monkeypatch.setenv("APGR_MODEL_AUTHORITY", "source-defaults")
    dispatcher._bind_stage_accounting({"execution_mode": "gemini_sub", "controller_generation": {"commit": "a" * 40}}, directory, entry=capture_entry(repo))
    data = b"Fake provider native launch qualification."
    result, meta = dispatcher._stage(directory, 1, "work", "01-work", "worker", Endpoint("codex", "implementation-testing"), RenderedPrompt(data, [{"kind": "task_prompt", "start": 0, "end": len(data)}]), None, read_only=True)
    assert result.ok
    assert len(calls) == 1
    assert meta["worker_drain"]["status"] == "closed"
