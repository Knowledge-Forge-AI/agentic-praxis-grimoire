"""Failed disposition writes retain blocked evidence and propagate failure."""
import hashlib
import json
from pathlib import Path
import time

import pytest

from agent_phase import worker_canary as canary
from agent_phase.canary_budget import CanaryBudget, CanaryBudgetError, DEFAULT_PHASE
from agent_phase.dispatch import Dispatcher
from agent_phase.provider import Result
from test_apg166zu_qualifier_correction import isolated_budgets, observe_preflight
import test_apg166zt_qualifier_repair as qualifier_repair

canary_stage_environment = qualifier_repair.canary_stage_environment

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('persistent', [True, False])
def test_disposition_failure_propagates_with_blocked_receipt(
    tmp_path, monkeypatch, canary_stage_environment, persistent,
):
    home, _ = canary_stage_environment
    order, errors = [], []
    budgets = isolated_budgets(tmp_path, monkeypatch, order)
    observe_preflight(monkeypatch, order)
    now = time.time()
    cleanup = {key: True for key in ('cleanup_proven', 'outer_group_absent',
                                    'nested_groups_absent', 'verified_absence', 'reaped')}
    cleanup['failure_reasons'] = []
    monkeypatch.setattr(Dispatcher, '_stage', lambda *args, **kwargs:
                        (Result(0, b'', b'', True, now, now, cleanup=cleanup),
                         {'worker_drain': {'uncertain_cleanup': False}}))
    monkeypatch.setattr(canary, 'qualify', lambda record:
                        {'passed': True, 'status': 'passed', 'reasons': []})
    original = CanaryBudget.record_disposition
    calls = []

    def record(self, case, attempt, *, status, **kwargs):
        calls.append(status)
        if persistent or status == 'passed':
            error = CanaryBudgetError('recording ' + status + ' failed')
            errors.append(error)
            raise error
        return original(self, case, attempt, status=status, **kwargs)

    monkeypatch.setattr(CanaryBudget, 'record_disposition', record)
    output = tmp_path / 'case'
    with pytest.raises(CanaryBudgetError) as raised:
        canary.run_case(ROOT, home, output, 'claude-gemini',
                        runner=lambda *args, **kwargs: pytest.fail('unexpected provider launch'))
    assert calls == ['passed', 'blocked']
    assert raised.value is errors[-1]
    receipt = (output / 'canary.json').read_bytes()
    data = json.loads(receipt)
    assert data['status'] == 'blocked'
    assert data['error_type'] == 'CanaryBudgetError'
    assert data['cleanup_proven'] is False
    assert 'recording passed failed' in data['diagnostic']
    attempts = budgets[DEFAULT_PHASE].get_case('claude-gemini')['attempts']
    assert len(attempts) == 1
    attempt = attempts[0]
    assert attempt['status'] == ('reserved' if persistent else 'blocked')
    assert attempt['status'] != 'passed'
    if persistent:
        assert raised.value.__context__ is errors[0]
    else:
        assert attempt['details']['receipt_sha256'] == hashlib.sha256(receipt).hexdigest()
        assert attempt['details']['receipt'] == str(output / 'canary.json')
