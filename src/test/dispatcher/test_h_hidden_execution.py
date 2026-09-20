"""CORR4 exact hidden pytest execution and visible collection contracts."""
import json

import pytest

from testing.h_eval import hidden_execution as execution, preregistration
from testing.h_eval import promotion_oracles as oracle
from test_h_promotion_corr3 import ROOT, custody, grade

CASE = 'pytest-test-profile/positive/collection'


def subject():
    files = dict(oracle.spec_for(CASE).good_files)
    files['submitted_values.py'] = files.pop('check_values.py')
    files['pytest.ini'] = '[pytest]\npython_files = submitted_*.py\npython_functions = test_value_*\n'
    return files


def test_hidden_override_preserves_candidate_authored_collection():
    files = subject()
    result = grade(CASE, files)
    assert result['status'] == 'pass', result
    hidden = result['hidden_oracle']['execution_attestation']
    assert hidden['qualifying'] and hidden['hidden_collection_overrides']
    assert len(hidden['expected_identities']) == 2
    assert all(hidden['observed_statuses'][node] == [
        'collected', 'started', 'setup:passed', 'call:passed', 'teardown:passed']
        for node in hidden['expected_identities'])
    authored = result['model_authored_tests']
    assert '1 passed' in authored['good']['stdout']  # custom selection excludes the second check
    assert authored['bad']['status'] == 'fail'
    assert 'execution_attestation' not in authored['good']
    assert '-c' not in authored['good']['command']
    custody(result, files, ('values.py',))


@pytest.mark.parametrize('action', ['deselect', 'drop', 'skip', 'xfail', 'xpass', 'duplicate'])
def test_candidate_hooks_cannot_hide_expected_nodes(action):
    files = subject()
    actions = {
        'deselect': 'items.remove(node); config.hook.pytest_deselected(items=[node])',
        'drop': 'items.remove(node)',
        'skip': 'node.add_marker(pytest.mark.skip(reason="candidate"))',
        'xfail': 'node.add_marker(pytest.mark.xfail(run=False, reason="candidate"))',
        'xpass': 'node.add_marker(pytest.mark.xfail(reason="candidate"))',
        'duplicate': 'items.append(node)',
    }
    files['conftest.py'] = ('import pytest\ndef pytest_collection_modifyitems(config, items):\n'
        '    for node in list(items):\n'
        '        if "apg_oracle" in node.nodeid:\n'
        '            ' + actions[action] + '\n            break\n')
    result = grade(CASE, files)
    assert result['status'] == 'fail'
    attestation = result['hidden_oracle']['execution_attestation']
    assert not attestation['qualifying'] and attestation['fail_reasons']
    assert result['model_authored_tests']['status'] == 'pass'


def test_broken_implementation_cannot_pass_with_suppressive_config():
    files = subject()
    files['values.py'] = oracle.spec_for(CASE).bad_files['values.py']
    result = grade(CASE, files)
    assert result['status'] == 'fail'
    hidden = result['hidden_oracle']['execution_attestation']
    assert not hidden['qualifying']
    assert any('call:failed' in states for states in hidden['observed_statuses'].values())


@pytest.mark.parametrize('rename', [False, True])
def test_visible_check_function_identity_is_stable(rename):
    files = subject()
    if rename:
        files['submitted_values.py'] = files['submitted_values.py'].replace(
            'test_value_normalizes_mixed_input', 'test_value_renamed')
    result = grade(CASE, files)
    assert result['status'] == ('fail' if rename else 'pass')
    assert result['hidden_oracle']['visible_check_name_preserved'] is not rename
    assert result['model_authored_tests']['status'] == ('fail' if rename else 'pass')


def test_fixture_lifecycle_hidden_nodes_all_pass_without_xfail():
    case = 'pytest-test-profile/positive/fixture-lifecycle'
    result = grade(case, dict(oracle.spec_for(case).good_files))
    assert result['status'] == 'pass', result
    hidden = result['hidden_oracle']['execution_attestation']
    assert hidden['qualifying']
    assert all('xfailed' not in s for states in hidden['observed_statuses'].values() for s in states)


@pytest.mark.parametrize('reporting', ['logging', 'properties'])
def test_lifecycle_accepts_candidate_junit_metadata(reporting):
    case = 'pytest-test-profile/positive/fixture-lifecycle'
    files = dict(oracle.spec_for(case).good_files)
    if reporting == 'logging':
        files['pytest.ini'] = '[pytest]\njunit_logging = all\n'
    else:
        files['conftest.py'] += ('\ndef pytest_collection_modifyitems(items):\n'
            '    for item in items:\n        item.user_properties.append(("candidate", "metadata"))\n')
    result = grade(case, files)
    assert result['status'] == 'pass', result
    assert result['hidden_oracle']['execution_attestation']['qualifying']
    custody(result, files, ('output_support.py',))


def test_lifecycle_axis_is_exact_and_material_in_preregistration():
    value = json.loads((ROOT / 'testing/h_eval/promotion-preregistration.json').read_text())
    case = next(c for r in value['skills'] for c in r['cases']
                if c['case_id'] == 'pytest-test-profile/positive/fixture-lifecycle')
    preregistration._verify_case_oracle(case, 'pytest-test-profile')
    assert case['oracle']['decision_axis'] == 'failure-path observation and state-isolation test design'
    assert 'session-root ownership' not in json.dumps(case)
    case['oracle']['decision_axis'] = 'session-root ownership'
    with pytest.raises(ValueError, match='test-design decision axis'):
        preregistration._verify_case_oracle(case, 'pytest-test-profile')


@pytest.mark.parametrize('states', [[], ['collected'], ['collected', 'started', 'call:passed'],
    ['collected', 'started', 'setup:passed', 'call:passed', 'teardown:failed']])
def test_partial_pytest_artifacts_fail_closed(states):
    raw = json.dumps({'runner_version': 'test', 'events': [['test_hidden.py::test_x', s] for s in states]}).encode()
    result = execution.attest('pytest', ['test_hidden.py::test_x'], raw, 0, [], {}, {})
    assert not result['qualifying']
