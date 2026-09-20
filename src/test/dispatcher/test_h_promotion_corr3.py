"""CORR3 candidate custody and transaction-neutral oracle contracts."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

import pytest

from testing.h_eval import promotion_oracles as oracle

ROOT = Path(__file__).resolve().parents[3]
CASES = {c['case_id']: c for row in json.loads(
    (ROOT / 'testing/h_eval/promotion-preregistration.json').read_text())['skills'] for c in row['cases']}


def grade(case_id, files):
    return oracle.evaluate_model_output(case_id, files, {'python3': sys.executable, 'go': shutil.which('go')})


def custody(result, files, implementation):
    authored = result['model_authored_tests']
    for variant in ('good', 'bad'):
        record = authored[variant]['grading_custody']
        assert set(record['implementation_substitutions']) == set(implementation)
        assert record['candidate_configuration_restored'] is False
        assert record['candidate_controlled_preserved'] is True
        for name, content in files.items():
            digest = hashlib.sha256(content.encode()).hexdigest()
            assert record['candidate_before'][name] == digest
            if name not in implementation:
                assert record['graded_files'][name] == digest
        assert record['hidden_nonconflicting_overlay'] == {}
    assert authored['good']['grading_custody']['candidate_controlled'] == authored['bad']['grading_custody']['candidate_controlled']


@pytest.mark.parametrize('vacuous', [False, True])
def test_external_go_tests_keep_visible_module_identity(vacuous):
    case_id = 'go-test-profile/positive/lifecycle'
    files = dict(CASES[case_id]['subject_files'])
    module = files['go.mod'].split()[1]
    files['parse_test.go'] = ('package parsing_test\nimport ("testing"; p "' + module + '")\n'
        'func TestVisibleAPI(t *testing.T) { v, err := p.Parse("12"); if err != nil || v != 12 { t.Fatal(v, err) }; '
        + ('' if vacuous else 'if _, err := p.Parse("bad"); err == nil { t.Fatal("accepted malformed") }; ') + '}\n')
    result = grade(case_id, files)
    assert result['status'] == ('fail' if vacuous else 'pass'), result
    assert result['model_authored_tests']['good']['status'] == 'pass'
    assert result['model_authored_tests']['bad']['status'] == ('pass' if vacuous else 'fail')
    custody(result, files, ('parse.go',))


def test_deleted_conftest_is_never_restored():
    case_id = 'pytest-test-profile/positive/fixture-lifecycle'
    files = dict(oracle.spec_for(case_id).good_files)
    del files['conftest.py']
    result = grade(case_id, files)
    assert result['status'] == 'fail'
    assert result['model_authored_tests']['good']['status'] == 'fail'
    for receipt in (result['hidden_oracle'], *[result['model_authored_tests'][v] for v in ('good', 'bad')]):
        assert 'conftest.py' not in receipt['grading_custody']['graded_files']
        assert receipt['grading_custody']['candidate_configuration_restored'] is False
    custody(result, files, ('output_support.py',))


@pytest.mark.parametrize('vacuous', [False, True])
def test_custom_pytest_collection_and_support_are_active(vacuous):
    case_id = 'pytest-test-profile/positive/collection'
    files = dict(oracle.spec_for(case_id).good_files)
    del files['check_values.py']
    files['pytest.ini'] = '[pytest]\npython_files = submitted_*.py\npython_functions = test_value_*\n'
    files['support.py'] = "EXPECTED = ['alpha']\n"
    files['conftest.py'] = 'import pytest\n@pytest.fixture\ndef expected():\n    from support import EXPECTED\n    return EXPECTED\n'
    files['submitted_values.py'] = ('from values import normalize\ndef test_value_normalizes_mixed_input(expected):\n'
        + ('    assert True\n' if vacuous else "    assert normalize([' Alpha ']) == expected\n"))
    result = grade(case_id, files)
    assert result['status'] == ('fail' if vacuous else 'pass'), result
    assert result['model_authored_tests']['good']['status'] == 'pass'
    assert result['model_authored_tests']['bad']['status'] == ('pass' if vacuous else 'fail')
    custody(result, files, ('values.py',))


def test_hidden_overlay_never_shadows_candidate_names():
    case_id = 'pytest-test-profile/positive/fixture-lifecycle'
    spec = oracle.spec_for(case_id)
    files = dict(spec.good_files)
    files['test_apg_oracle_test_output.py'] = '# candidate support\n'
    files['pyproject.toml'] = '[tool.example]\nactive = true\n'
    files['tox.ini'] = '[example]\nactive = yes\n'
    overlay = oracle._hidden_overlay(spec, files)
    assert set(overlay).isdisjoint(files)
    assert 'conftest.py' not in overlay
    result = grade(case_id, files)
    assert result['status'] == 'pass', result
    custody(result, files, ('output_support.py',))
    hidden = result['hidden_oracle']['grading_custody']
    assert set(hidden['hidden_nonconflicting_overlay']) == set(overlay)


def test_explicit_begin_transfer_commits_and_rolls_back():
    case_id = 'sqlite-database-profile/positive/transactions'
    files = dict(oracle.spec_for(case_id).good_files)
    code = files['transfer.py'].replace('    with connection:', '    connection.execute("BEGIN")\n    try:')
    files['transfer.py'] = code + '        connection.commit()\n    except Exception:\n        connection.rollback()\n        raise\n'
    result = grade(case_id, files)
    assert result['status'] == 'pass', result


@pytest.mark.parametrize('failure', ['raise RuntimeError("migration refused") from error', 'return False'])
@pytest.mark.parametrize('corrupt', [False, True])
def test_explicit_immediate_migration_failure_signals_and_recovery(failure, corrupt):
    case_id = 'sqlite-database-profile/positive/rebuild-integrity'
    files = {'migrate.py': 'def migrate(connection):\n    connection.execute("BEGIN IMMEDIATE")\n    try:\n'
        '        connection.execute("CREATE INDEX IF NOT EXISTS children_parent_idx ON children(parent_id)")\n'
        '        connection.commit()\n    except Exception as error:\n        connection.rollback()\n'
        + ('        connection.execute("DELETE FROM children")\n        connection.commit()\n' if corrupt else '')
        + '        ' + failure + '\n'}
    result = grade(case_id, files)
    assert result['status'] == ('fail' if corrupt else 'pass'), result


def test_missing_source_cannot_truncate_existing_destination():
    case_id = 'go-language-profile/positive/api-resources'
    files = dict(oracle.spec_for(case_id).good_files)
    # This broken completion only damages the destination on a missing source.
    files['copy.go'] = files['copy.go'].replace('if err != nil { return err }; defer input.Close()',
        'if err != nil { os.WriteFile(dst, nil, 0600); return err }; defer input.Close()')
    result = grade(case_id, files)
    assert result['status'] == 'fail'
    assert 'missing source changed destination' in result['hidden_oracle']['stdout']


@pytest.mark.parametrize('format_code,expected', [('%w', 'pass'), ('%v', 'fail')])
def test_fetch_visible_error_identity_contract(format_code, expected):
    case_id = 'go-language-profile/positive/cancellation'
    for text in (CASES[case_id]['prompt'], CASES[case_id]['subject_files']['README.md']):
        assert 'errors.Is(err, context.Canceled)' in text
        assert 'errors.Is(err, context.DeadlineExceeded)' in text
    files = dict(oracle.spec_for(case_id).good_files)
    files['fetch.go'] = files['fetch.go'].replace('return nil, err', 'return nil, fmt.Errorf("fetch: ' + format_code + '", err)')
    assert grade(case_id, files)['status'] == expected
