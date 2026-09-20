"""APG162C caller qualification; all provider launches are captured locally."""
from __future__ import annotations

import json
import os
from pathlib import Path
import time
import shutil

import pytest

from test_agent_phase_rtk import _REPO_ROOT, write_fake_evidence
from agent_phase.dispatch import Dispatcher
from agent_phase.envelope import Segment, render, SEGMENT_TASK_PROMPT
from agent_phase.provider import Result
from agent_phase.routing import Endpoint
from agent_phase.run import RunDirectory


def configure(root, executable=None, enabled=True):
    (root / '.apgr').mkdir(parents=True, exist_ok=True)
    (root / '.apgr/config.toml').write_text(
        '[integrations.rtk]\nenabled = ' + str(enabled).lower() + '\n'
        + (f'executable = "{executable}"\n' if executable else '')
        + 'providers.claude = "instructions"\n'
    )


@pytest.fixture
def targets(tmp_path, monkeypatch):
    binary = tmp_path / 'rtk'
    binary.write_text("#!/bin/sh\necho 'rtk 0.43.0'\n")
    binary.chmod(0o755)
    target = tmp_path / 'target'
    configure(target, binary)
    (target / '.git').mkdir()
    nested = target / 'nested/deep'
    nested.mkdir(parents=True)
    ambient = tmp_path / 'ambient'
    configure(ambient, enabled=False)
    (ambient / '.git').mkdir()
    empty = tmp_path / 'empty'
    empty.mkdir()
    controller = tmp_path / 'controller'
    configure(controller, enabled=False)
    # The selected controller now owns a coherent six-member roster bundle.
    shutil.copytree(_REPO_ROOT / "common/dispatcher", controller / "common/dispatcher")
    selected_home = tmp_path / 'selected-home'
    selected_home.mkdir()
    (selected_home / 'config.toml').write_text('[integrations.rtk]\nenabled = true\n')
    (selected_home / 'claude').mkdir()
    (selected_home / 'claude/settings.json').write_text('{}\n')
    ambient_home = tmp_path / 'ambient-home'
    ambient_home.mkdir()
    (ambient_home / 'config.toml').write_text('[integrations.rtk]\nenabled = false\n')
    monkeypatch.setenv('APGR_HOME', str(ambient_home))
    monkeypatch.delenv('APGR_TARGET_PROJECT_ROOT', raising=False)
    monkeypatch.delenv('APGR_TARGET_PROJECT_START', raising=False)
    monkeypatch.setenv('AGENT_CENTRAL_WORKER_WORKSPACE', str(ambient))
    monkeypatch.chdir(ambient)
    return target, nested, empty, ambient, controller, selected_home, binary


@pytest.mark.parametrize('case', ['root', 'nested', 'explicit-empty', 'explicit-other', 'no-project', 'home-ancestor', 'isolated-start'])
@pytest.mark.parametrize('provider', ['codex', 'antigravity', 'claude'])
def test_v1_project_authority_at_runner(tmp_path, monkeypatch, targets, case, provider):
    target, nested, empty, ambient, controller, selected_home, binary = targets
    unconfigured = tmp_path / 'home-like' / 'repo'
    (unconfigured / '.git').mkdir(parents=True)
    configure(unconfigured.parent, enabled=False)
    if case in ('home-ancestor', 'isolated-start'):
        (selected_home / 'config.toml').write_text(
            f'[integrations.rtk]\nenabled = true\nexecutable = "{binary}"\n'
            'providers.claude = "instructions"\n'
        )
    cwd, explicit, active = {
        'home-ancestor': (unconfigured, None, True),
        'isolated-start': (target, None, True),
        'root': (target, None, True),
        'nested': (nested, None, True),
        'explicit-empty': (nested, empty, False),
        'explicit-other': (ambient, target, True),
        'no-project': (empty, None, False),
    }[case]
    # Source guidance remains implementation-owned; its config must not become
    # target authority. The supplied controller fixture has contradictory config.
    for name in ('codex', 'antigravity', 'claude'):
        (controller / name).symlink_to(_REPO_ROOT / name, target_is_directory=True)
    # A nested parent may already carry target context; the scoped launch must
    # override it and restore it without borrowing worker-facility fields.
    monkeypatch.setenv('APGR_TARGET_PROJECT_ROOT', str(ambient))
    monkeypatch.setenv('APGR_TARGET_PROJECT_START', str(ambient))
    captured = []
    def runner(argv, prompt, execution_cwd, max_bytes, on_output=None):
        from test_agent_phase_result_repair import write_antigravity_evidence
        write_antigravity_evidence(list(argv), response_bytes=b'ok')
        captured.append((list(argv), prompt, execution_cwd,
                         os.environ.get('APGR_TARGET_PROJECT_ROOT'),
                         os.environ.get('APGR_HOME')))
        assert os.environ['AGENT_CENTRAL_WORKER_WORKSPACE'] == str(ambient)
        assert os.environ['APGR_TARGET_PROJECT_START'] == str(cwd)
        if provider == 'claude':
            # Cross the real adapter boundary using the exact scoped environment.
            import claude_vc_profile as launcher
            monkeypatch.chdir(execution_cwd)
            launcher.launch(_REPO_ROOT / 'claude', 'normal-sysadmin-plan-review', ['--print', 'task'])
        return Result(0, b'ok', b'', False, time.time(), time.time())
    execs = []
    if provider == 'claude':
        import claude_vc_profile as launcher
        import claude_model_catalog as catalog
        monkeypatch.setenv('AGENT_CENTRAL_MANAGED_PARENT', '1')
        monkeypatch.delenv(launcher.WORKER_FACADE_MARKER, raising=False)
        monkeypatch.setattr(launcher.shutil, 'which', lambda name: '/fake/claude')
        monkeypatch.setattr(catalog, 'probe_claude_version', lambda executable: ('2.1.999', 'available'))
        monkeypatch.setattr(launcher.os, 'execve', lambda exe, argv, env: execs.append((argv, env)))
    dispatcher = Dispatcher(controller, cwd, project_root=explicit, apgr_home=selected_home,
                            run_root=tmp_path / 'runs', resolve_scanner=False,
                            codex_executable='/fake/codex', claude_launcher='/fake/claude',
                            antigravity_launcher='/fake/antigravity', runner=runner)
    result, _ = dispatcher._stage(
        directory=RunDirectory(tmp_path / 'runs', 'authority', 'work-reviewed'),
        index=1, stage='produce', prefix='produce', role='primary',
        endpoint=Endpoint(provider, 'gemini-3.8-flash-high' if provider == 'antigravity' else 'normal-sysadmin-plan-review' if provider == 'claude' else 'implementation-testing'),
        rendered=render([Segment(SEGMENT_TASK_PROMPT, 'task')]), binding=None,
        worker_capability={'allowed': False},
        working_directory=ambient if case == 'isolated-start' else None,
    )
    assert result.exit_code == 0
    assert len(captured) == 1
    argv, prompt, actual_cwd, project_env, home_env = captured[0]
    assert actual_cwd == (ambient if case == 'isolated-start' else cwd)
    assert project_env == (str(explicit) if explicit is not None else None)
    assert os.environ['APGR_TARGET_PROJECT_ROOT'] == str(ambient)
    assert os.environ['APGR_TARGET_PROJECT_START'] == str(ambient)
    assert home_env == str(selected_home)
    assert os.environ['APGR_HOME'] == str(tmp_path / 'ambient-home')
    assert os.environ['AGENT_CENTRAL_WORKER_WORKSPACE'] == str(ambient)
    if provider == 'claude':
        assert len(execs) == 1
        argv, env = execs[0]
        assert env['APGR_HOME'] == str(selected_home)
        assert '--setting-sources' in argv
        delivered = '\n'.join(argv)
    else:
        delivered = '\n'.join(argv) if provider == 'codex' else prompt.decode()
    assert ('RTK shell-output efficiency' in delivered) is active
    assert (str(binary) in delivered) is active


@pytest.mark.parametrize('case', ['nested', 'explicit-empty', 'explicit-other', 'no-project', 'home-ancestor'])
def test_claude_direct_start_discovery(tmp_path, monkeypatch, targets, case):
    import claude_vc_profile as launcher
    import claude_model_catalog as catalog
    target, nested, empty, ambient, controller, selected_home, binary = targets
    unconfigured = tmp_path / 'home-like' / 'repo'
    (unconfigured / '.git').mkdir(parents=True)
    configure(unconfigured.parent, enabled=False)
    if case == 'home-ancestor':
        (selected_home / 'config.toml').write_text(
            f'[integrations.rtk]\nenabled = true\nexecutable = "{binary}"\n'
            'providers.claude = "instructions"\n'
        )
    cwd, explicit, active = {
        'home-ancestor': (unconfigured, None, True),
        'nested': (nested, None, True), 'explicit-empty': (nested, empty, False),
        'explicit-other': (ambient, target, True), 'no-project': (empty, None, False),
    }[case]
    monkeypatch.chdir(cwd)
    monkeypatch.setenv('APGR_HOME', str(selected_home))
    if explicit is None:
        monkeypatch.delenv('APGR_TARGET_PROJECT_ROOT', raising=False)
    else:
        monkeypatch.setenv('APGR_TARGET_PROJECT_ROOT', str(explicit))
    monkeypatch.setenv('AGENT_CENTRAL_MANAGED_PARENT', '1')
    monkeypatch.delenv(launcher.WORKER_FACADE_MARKER, raising=False)
    monkeypatch.setattr(launcher.shutil, 'which', lambda name: '/fake/claude')
    monkeypatch.setattr(catalog, 'probe_claude_version', lambda executable: ('2.1.999', 'available'))
    calls = []
    monkeypatch.setattr(launcher.os, 'execve', lambda exe, argv, env: calls.append(argv))
    launcher.launch(_REPO_ROOT / 'claude', 'normal-sysadmin-plan-review', ['--print', 'task'])
    assert len(calls) == 1
    assert ('RTK shell-output efficiency' in '\n'.join(calls[0])) is active


@pytest.mark.parametrize('consumer', ['v1', 'v2', 'claude'])
def test_real_consumer_fallback_serializes(tmp_path, monkeypatch, consumer):
    import agentic_praxis_grimoire.rtk as rtk
    import agent_source_guidance as guidance
    def broken(**kwargs):
        raise RuntimeError('injected RTK resolution failure')
    monkeypatch.setattr(rtk, 'resolve_rtk_configuration', broken)
    observed = []
    if consumer == 'v1':
        observed.append(Dispatcher(_REPO_ROOT, tmp_path, run_root=tmp_path / 'runs',
                                  resolve_scanner=False)._ensure_rtk_resolution())
    elif consumer == 'v2':
        from agent_phase import v2_dispatch
        from agent_phase.request import parse_request_v2
        from test_agent_phase_v2_full_execution import _init_repo
        target = _init_repo(tmp_path / 'target')
        real_turns = v2_dispatch.execute_v2_turns
        def capture(*args, **kwargs):
            observed.append(kwargs['rtk_resolution'])
            return real_turns(*args, **kwargs)
        monkeypatch.setattr(v2_dispatch, 'execute_v2_turns', capture)
        raw = json.dumps({'schema': 'agent-phase-request-v2', 'phase_type': 'implementation_testing',
                          'prompt': 'task'}).encode()
        # First runner call terminates after resolution capture, with no provider.
        def runner(**kwargs):
            raise RuntimeError('fixture stop after resolution')
        try:
            v2_dispatch.dispatch_v2(_REPO_ROOT, target, parse_request_v2(raw), raw,
                                    execution_mode='gemini_sub', apgr_home=tmp_path / 'home',
                                    outbox_root=tmp_path / 'outbox', runner=runner)
        except RuntimeError:
            pass
    else:
        selected_home = tmp_path / 'home'
        (selected_home / 'claude').mkdir(parents=True)
        (selected_home / 'claude/settings.json').write_text('{}\n')
        monkeypatch.setenv('APGR_HOME', str(selected_home))
        import claude_vc_profile as launcher
        import claude_model_catalog as catalog
        real_guidance = guidance.source_guidance
        def capture(*args, **kwargs):
            observed.append(kwargs['rtk'])
            return real_guidance(*args, **kwargs)
        monkeypatch.setattr(guidance, 'source_guidance', capture)
        monkeypatch.setenv('AGENT_CENTRAL_MANAGED_PARENT', '1')
        monkeypatch.delenv(launcher.WORKER_FACADE_MARKER, raising=False)
        monkeypatch.setattr(launcher.shutil, 'which', lambda name: '/fake/claude')
        monkeypatch.setattr(catalog, 'probe_claude_version', lambda executable: ('2.1.999', 'available'))
        monkeypatch.setattr(launcher.os, 'execve', lambda *args: None)
        launcher.launch(_REPO_ROOT / 'claude', 'normal-sysadmin-plan-review', ['--print', 'task'])
    assert len(observed) == 1
    value = json.loads(json.dumps(observed[0].as_dict()))
    assert value['status'] == 'unavailable'
    assert 'injected RTK resolution failure' in value['diagnostics'][0]
