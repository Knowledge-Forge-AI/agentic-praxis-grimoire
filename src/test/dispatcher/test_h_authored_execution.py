"""CORR5 candidate collection owns stable-check execution."""
import pytest

from testing.h_eval import authored_execution
from test_h_hidden_execution import CASE, subject
from test_h_promotion_corr3 import custody, grade


def test_relocated_stable_check_has_distinct_authored_good_bad_evidence():
    files = subject()
    result = grade(CASE, files)
    assert result['status'] == 'pass'
    authored = result['model_authored_tests']
    for variant, outcome in [('good', 'passed'), ('bad', 'failed')]:
        receipt = authored[variant]
        evidence = receipt['authored_execution']
        assert receipt['authored_execution_artifact']
        assert 'hidden_execution_artifact' not in receipt
        assert evidence['command_owner'] == 'candidate-configured-authored-run'
        assert evidence['hidden_collection_overrides'] is False
        assert evidence['selected_command'] == ['python3', '-m', 'pytest', '-q']
        assert '-c' not in receipt['command'] and '-o' not in receipt['command']
        assert evidence['stable_nodes'] == ['submitted_values.py::test_value_normalizes_mixed_input']
        assert evidence['observed_statuses'][evidence['stable_nodes'][0]] == [
            'collected', 'started', 'setup:passed', 'call:' + outcome, 'teardown:passed']
        assert evidence['execution_complete']
    custody(result, files, ('values.py',))


def test_uncollected_stable_source_and_collected_renamed_replacement_fails():
    files = subject()
    files['legacy.py'] = files['submitted_values.py']
    files['submitted_values.py'] = files['submitted_values.py'].replace(
        authored_execution.STABLE_FUNCTION, 'test_value_renamed')
    result = grade(CASE, files)
    assert result['hidden_oracle']['visible_check_name_preserved']
    assert result['hidden_oracle']['execution_attestation']['qualifying']
    assert result['model_authored_tests']['good']['status'] == 'pass'
    assert result['model_authored_tests']['bad']['status'] == 'fail'
    assert result['model_authored_tests']['status'] == result['status'] == 'fail'


@pytest.mark.parametrize('action', ['deselect', 'drop', 'skip', 'xfail', 'xpass', 'duplicate', 'second-file'])
def test_stable_node_suppression_or_ambiguity_fails(action):
    files = subject()
    actions = {
        'deselect': 'items.remove(node); config.hook.pytest_deselected(items=[node])',
        'drop': 'items.remove(node)',
        'skip': 'node.add_marker(pytest.mark.skip(reason="candidate"))',
        'xfail': 'node.add_marker(pytest.mark.xfail(run=False, reason="candidate"))',
        'xpass': 'node.add_marker(pytest.mark.xfail(reason="candidate"))',
        'duplicate': 'items.append(node)',
    }
    if action == 'second-file':
        files['submitted_other.py'] = files['submitted_values.py']
    else:
        files['conftest.py'] = ('import pytest\ndef pytest_collection_modifyitems(config, items):\n'
            '    for node in list(items):\n'
            '        if node.nodeid.startswith("submitted_values.py::test_value_normalizes_mixed_input"):\n'
            '            ' + actions[action] + '\n')
    result = grade(CASE, files)
    assert result['hidden_oracle']['execution_attestation']['qualifying']
    assert result['model_authored_tests']['status'] == result['status'] == 'fail'
    assert not result['model_authored_tests']['good']['authored_execution']['execution_complete']
