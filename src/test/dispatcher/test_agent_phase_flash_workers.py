"""Gemini parent access through the real Antigravity and shared CLI transports."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

import pytest

from agent_phase.dispatch import Dispatcher
from agent_phase.envelope import RenderedPrompt
from agent_phase.gitstate import capture_entry
from agent_phase.lifecycle import LIFECYCLES
from agent_phase.routing import Endpoint
from agent_phase.run import RunDirectory, stage_parent_id
pytest.importorskip("agent_workers", reason="agent_workers subsystem retained in Agent-Central")
from agent_workers.ledger import ParentLedger
from test_agent_worker_capture_order import repository

ROOT = Path(__file__).resolve().parents[3]

AGY = r'''
import json, os, subprocess, sys, time
from pathlib import Path
if '--version' in sys.argv:
    print('agy fixture'); raise SystemExit(0)
assert sys.argv[sys.argv.index('--model') + 1] == 'gemini-3.8-flash-high'
assert os.environ['HOME'] == os.environ['FLASH_EXPECTED_HOME']
if os.environ.get('AGENT_CENTRAL_WORKER_LEAF') == '1':
    assert 'AGENT_CENTRAL_PARENT_ID' not in os.environ
    assert 'AGENT_CENTRAL_WORKER_FACADE' not in os.environ
    if os.environ.get('FLASH_CHILD_OUTCOME') == 'cancelled':
        time.sleep(60)
    if os.environ.get('FLASH_CHILD_OUTCOME') == 'failed':
        print(json.dumps({'type':'result','status':'ERROR','error':'fixture failure'}), flush=True)
        raise SystemExit(7)
    response = 'Gemini leaf inspected'
else:
    source = Path(os.environ['FLASH_SOURCE'])
    prompt = sys.argv[sys.argv.index('-p') + 1]
    assert str(source / 'bin/agent-worker') in prompt
    assert 'Both pools use external leaf processes' in prompt
    assert 'Capacity is a ceiling' in prompt
    assert 'AGENT_CENTRAL_WORKER_FACADE' not in os.environ
    def cli(*args):
        result = subprocess.run([str(source / 'bin/agent-worker'), *args], capture_output=True, text=True, timeout=30)
        assert result.returncode == 0 or args[:2] in (('job','wait'), ('job','cancel')), result.stderr
        return json.loads(result.stdout)
    status = cli('parent', 'status')
    cap = status['worker_capability']
    assert cap['execution_mode'] in ('gemini_flash_sub', 'gemini_flash_opus_sub')
    assert cap['parent_provider'] == 'antigravity'
    assert cap['parent_profile'] == 'gemini-3.8-flash-high'
    assert cap['parent_family'] == 'gemini_flash'
    assert cap['native_worker']['enabled'] is False
    assert status['task_authority'] == os.environ['FLASH_AUTHORITY']
    jobs = []
    for kind in ('gemini', 'luna'):
        job = cli('job', 'launch', '--key', kind, '--worker-kind', kind,
                  '--task', 'Inspect fixture ' + kind, '--task-authority', 'read_only',
                  '--acceptance-criteria', 'Return fixture observation')
        outcome = os.environ.get('FLASH_CHILD_OUTCOME', 'completed')
        if outcome == 'cancelled':
            waiting = cli('job', 'wait', '--job-id', job['job_id'], '--timeout', '1')
            assert waiting['timed_out'] is True, waiting
            assert cli('parent', 'status')['external_counts'][kind] == 1
            cli('job', 'cancel', '--job-id', job['job_id'])
        result = cli('job', 'wait', '--job-id', job['job_id'], '--timeout', '20')
        assert result['status'] == outcome, result
        assert result['cleanup_proven'] is True, result
        jobs.append(result['job_id'])
    status = cli('parent', 'status')
    assert status['external_counts'] == {'gemini': 0, 'luna': 0}
    response = json.dumps({'jobs': jobs, 'family': cap['parent_family']})
print(json.dumps({'type':'agent_response', 'text_delta':response}), flush=True)
print(json.dumps({'type':'result', 'status':'SUCCESS', 'result':response}), flush=True)
'''

CODEX = r'''
import json, os, sys, time
assert os.environ['HOME'] == os.environ['FLASH_EXPECTED_HOME']
assert os.environ.get('AGENT_CENTRAL_WORKER_LEAF') == '1'
assert 'AGENT_CENTRAL_PARENT_ID' not in os.environ
assert 'AGENT_CENTRAL_WORKER_FACADE' not in os.environ
assert 'agents.enabled=false' in sys.argv
assert 'model="gpt-5.6-luna"' in sys.argv
assert 'model_reasoning_effort="max"' in sys.argv
assert sys.argv[sys.argv.index('--sandbox') + 1] == 'read-only'
sys.stdin.read()
if os.environ.get('FLASH_CHILD_OUTCOME') == 'cancelled':
    time.sleep(60)
if os.environ.get('FLASH_CHILD_OUTCOME') == 'failed':
    raise SystemExit(7)
print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'Luna leaf inspected'}}))
'''


@pytest.fixture
def flash_binaries(tmp_path, monkeypatch):
    binaries = tmp_path / 'bin'
    binaries.mkdir()
    for name, content in (('agy', AGY), ('codex', CODEX)):
        path = binaries / name
        path.write_text('#!' + sys.executable + '\n' + content)
        path.chmod(0o755)
    monkeypatch.setenv('PATH', str(binaries) + os.pathsep + os.environ['PATH'])
    monkeypatch.setenv('FLASH_SOURCE', str(ROOT))
    monkeypatch.setenv('FLASH_EXPECTED_HOME', os.environ['HOME'])
    monkeypatch.setenv('PYTHONDONTWRITEBYTECODE', '1')


@pytest.mark.parametrize('mode', ['gemini_flash_sub', 'gemini_flash_opus_sub'])
@pytest.mark.parametrize('read_only', [False, True])
@pytest.mark.parametrize('outcome', ['completed', 'failed', 'cancelled'])
def test_real_gemini_parent_cli_launches_both_external_leaves(tmp_path, monkeypatch, flash_binaries, mode, read_only, outcome):
    repo = repository(tmp_path / 'repo')
    directory = RunDirectory(tmp_path / 'runs', 'flash-fixture', 'PARENT')
    dispatcher = Dispatcher(ROOT, repo, resolve_scanner=False)
    state = {'execution_mode': mode, 'controller_generation': {'commit': 'a' * 40}}
    dispatcher._bind_stage_accounting(state, directory, entry=capture_entry(repo))
    monkeypatch.setenv('FLASH_AUTHORITY', 'read_only' if read_only else 'mutation_capable')
    monkeypatch.setenv('FLASH_CHILD_OUTCOME', outcome)
    data = b'Inspect fixture using bounded workers.\n'
    result, meta = dispatcher._stage(
        directory, 1, 'work', '01-work', 'reviewer' if read_only else 'primary',
        Endpoint('antigravity', 'gemini-3.8-flash-high'),
        RenderedPrompt(data, [{'kind': 'task_prompt', 'start': 0, 'end': len(data)}]),
        None, read_only=read_only,
    )
    assert result.ok, result.stderr.decode()
    assert meta['worker_capability']['interface'] == 'cli'
    assert meta['worker_drain']['uncertain_cleanup'] is False
    ledger = ParentLedger(stage_parent_id(directory.run_id, 'work', 1), directory.path / 'workers')
    status = ledger.get_status()
    assert status['status'] == 'closed'
    assert status['external_counts'] == {'gemini': 0, 'luna': 0}
    cap = status['worker_capability']
    assert cap['parent_run_id'] == directory.run_id
    assert cap['parent_stage'] == 'work'
    assert cap['controller_generation'] == state['controller_generation']
    jobs = json.loads(ledger.data_path.read_text())['gemini_jobs']
    assert {job['worker_kind'] for job in jobs.values()} == {'gemini', 'luna'}


@pytest.mark.parametrize('life', LIFECYCLES.values(), ids=lambda life: life.name)
def test_lifecycle_roles_keep_read_only_worker_authority(tmp_path, monkeypatch, life):
    """Role semantics, rather than provider identity, own child authority."""
    from agent_phase.provider import Result
    import time

    repo = repository(tmp_path / 'repo')
    directory = RunDirectory(tmp_path / 'runs', 'flash-roles', life.name)
    observed = []

    def runner(argv, prompt, cwd, max_output, on_output=None):
        from test_agent_phase_antigravity import write_fake_evidence
        write_fake_evidence(list(argv), 0)
        ledger = ParentLedger(os.environ['AGENT_CENTRAL_PARENT_ID'], Path(os.environ['AGENT_CENTRAL_WORKER_STATE_DIR']))
        observed.append(ledger.get_status()['task_authority'])
        now = time.time()
        return Result(0, b'fixture', b'', False, now, now)

    dispatcher = Dispatcher(ROOT, repo, runner=runner, resolve_scanner=False)
    dispatcher._bind_stage_accounting({'execution_mode': 'gemini_flash_sub'}, directory, entry=capture_entry(repo))
    for index, stage in enumerate(life.stages, 1):
        data = b'Inspect fixture'
        result, meta = dispatcher._stage(directory, index, stage.name, stage.prefix, stage.role,
            Endpoint('antigravity', 'gemini-3.8-flash-high'),
            RenderedPrompt(data, [{'kind':'task_prompt', 'start':0, 'end':len(data)}]),
            None, read_only=stage.process_read_only)
        assert result.ok and meta['worker_drain']['uncertain_cleanup'] is False
    assert observed == ['read_only' if stage.process_read_only else 'mutation_capable' for stage in life.stages]
