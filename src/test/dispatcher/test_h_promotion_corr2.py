"""Visible CORR2 tasks and exact later-result correctness contracts."""
import json
from pathlib import Path
import shutil
import sys

import pytest

from testing.h_eval import promotion_fixture_specs as fixtures
from testing.h_eval import promotion_oracles as oracle

ROOT = Path(__file__).resolve().parents[3]
CASES = {case['case_id']: case for row in json.loads(
    (ROOT / 'testing/h_eval/promotion-preregistration.json').read_text())['skills']
    for case in row['cases']}
TEST_CASES = [key for key in CASES if '/positive/' in key and
              key.startswith(('go-test-profile/', 'pytest-test-profile/'))]


def executables():
    go = shutil.which('go')
    assert go, 'Go is required for this focused qualification'
    return {'go': go, 'python3': sys.executable}


@pytest.mark.parametrize('case_id', TEST_CASES)
def test_visible_start_correct_deficient_and_vacuous_completion(case_id):
    spec = fixtures.ORACLES[case_id]
    starting = CASES[case_id]['subject_files']
    # Every tested implementation/API is already visible, byte for byte.
    implementation = oracle._implementation_files(spec, spec.good_files)
    for name, text in implementation.items():
        if name in {'go.mod', 'pytest.ini', 'conftest.py', 'files.go'}:
            continue
        assert name in starting
        # Parser argument spelling is immaterial; the API is visible.
        if name != 'parse.go':
            assert starting[name] == text
        else:
            assert 'func Parse(' in starting[name]
    complete = {**starting, **spec.good_files}
    good = oracle.evaluate_model_output(case_id, complete, executables())
    assert good['status'] == 'pass', good
    authored = good['model_authored_tests']
    assert authored['good']['status'] == 'pass'
    assert authored['bad']['status'] == 'fail'
    deficient = oracle.evaluate_model_output(case_id, starting, executables())
    assert deficient['status'] == 'fail', deficient
    assert 'undefined:' not in json.dumps(deficient)
    assert 'ModuleNotFoundError' not in json.dumps(deficient)
    assert 'ImportError' not in json.dumps(deficient)
    vacuous = dict(implementation)
    if case_id.startswith('go-'):
        package = {'lifecycle': 'parsing', 'false-pass': 'harness', 'parallel-isolation': 'files'}[case_id.rsplit('/', 1)[1]]
        vacuous['empty_test.go'] = f'package {package}\nimport "testing"\nfunc TestEmpty(t *testing.T) {{}}\n'
    else:
        vacuous['check_empty.py' if case_id.endswith('collection') else 'test_empty.py'] = 'def test_empty():\n    assert True\n'
    rejected = oracle.evaluate_model_output(case_id, vacuous, executables())
    assert rejected['status'] == 'fail'
    assert rejected['model_authored_tests']['vacuous'] is True
    assert good['hidden_oracle']['hidden_oracle_sha256'] == deficient['hidden_oracle']['hidden_oracle_sha256']


@pytest.mark.parametrize('case_id', TEST_CASES)
def test_hidden_overlay_never_overwrites_visible_paths(case_id):
    spec = fixtures.ORACLES[case_id]
    visible = CASES[case_id]['subject_files']
    assert set(visible).isdisjoint(oracle._hidden_overlay(spec, visible))


@pytest.mark.parametrize('case_id', [key for key in CASES if '/non-trigger/' in key])
def test_neighbor_task_result_not_domain_membership(case_id):
    spec = fixtures.ORACLES[case_id]
    case = CASES[case_id]
    assert case['subject_files'] == spec.bad_files
    assert oracle.evaluate_model_output(case_id, case['subject_files'], {})['status'] == 'fail'
    assert oracle.evaluate_model_output(case_id, spec.good_files, {})['status'] == 'pass'
    assert case['non_trigger_contract']['provider_free_claim'] == 'structure-only'
    for name in spec.good_files:
        unchanged = dict(spec.good_files)
        unchanged[name] = spec.bad_files[name]
        assert oracle.evaluate_model_output(case_id, unchanged, {})['status'] == 'fail'
    unrelated = {**spec.good_files, 'extra.txt': 'unrequested edit'}
    assert oracle.evaluate_model_output(case_id, unrelated, {})['status'] == 'fail'


def test_both_frontmatter_inputs_are_visible_and_each_is_graded():
    case = CASES['markdown-language-profile/non-trigger/frontmatter']
    assert 'YAML' in case['prompt'] and 'JSON' in case['prompt']
    assert set(case['subject_files']) == {'x.md', 'json.md'}


@pytest.mark.parametrize('failure', ['ValueError("invalid")', 'RuntimeError("refused")', 'False'])
def test_transfer_allows_visible_failure_styles(failure):
    case_id = 'sqlite-database-profile/positive/transactions'
    files = dict(fixtures.ORACLES[case_id].good_files)
    action = 'return False' if failure == 'False' else 'raise ' + failure
    files['transfer.py'] = files['transfer.py'].replace('raise ValueError("invalid transfer")', action).replace('raise ValueError("insufficient funds")', action)
    result = oracle.evaluate_model_output(case_id, files, executables())
    assert result['status'] == 'pass', result


def test_transfer_rejects_unobservable_failure_and_partial_changes():
    case_id = 'sqlite-database-profile/positive/transactions'
    files = dict(fixtures.ORACLES[case_id].good_files)
    files['transfer.py'] = files['transfer.py'].replace('raise ValueError("insufficient funds")', 'return None')
    assert oracle.evaluate_model_output(case_id, files, executables())['status'] == 'fail'
    assert oracle.evaluate_model_output(case_id, fixtures.ORACLES[case_id].bad_files, executables())['status'] == 'fail'


def test_requested_migration_rejects_noop_and_disabled_foreign_keys():
    case_id = 'sqlite-database-profile/positive/rebuild-integrity'
    assert 'children_parent_idx' in CASES[case_id]['subject_files']['README.md']
    assert oracle.evaluate_model_output(case_id, fixtures.ORACLES[case_id].good_files, executables())['status'] == 'pass'
    for code in ['def migrate(connection):\n    pass\n',
                 'def migrate(connection):\n    connection.commit()\n    connection.execute("PRAGMA foreign_keys=OFF")\n    connection.execute("CREATE INDEX IF NOT EXISTS children_parent_idx ON children(parent_id)")\n']:
        assert oracle.evaluate_model_output(case_id, {'migrate.py': code}, executables())['status'] == 'fail'


@pytest.mark.parametrize('heading,fragment', [('# Installation', 'installation'),
    ('## Installation', 'installation'), ('### Installation', 'installation'),
    ('### Install: the CLI!', 'install-the-cli'), ('## A-b guide ###', 'a-b-guide')])
def test_markdown_heading_fragments(heading, fragment):
    spec = fixtures.ORACLES['markdown-language-profile/positive/links']
    files = {'README.md': f'[Setup](setup.md#{fragment})\n', 'setup.md': heading+'\n'}
    assert fixtures.source_check(spec, files)
    files['README.md'] = '[Setup](setup.md#wrong)\n'
    assert not fixtures.source_check(spec, files)


@pytest.mark.parametrize('variant', ['good', 'refuse', 'corrupt'])
def test_copy_existing_destination_policy(variant):
    case_id = 'go-language-profile/positive/api-resources'
    files = dict(fixtures.ORACLES[case_id].good_files)
    if variant == 'refuse':
        files['copy.go'] = files['copy.go'].replace('os.Create(dst)', 'os.OpenFile(dst, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)')
    elif variant == 'corrupt':
        files['copy.go'] = files['copy.go'].replace('os.Create(dst)', 'os.OpenFile(dst, os.O_WRONLY|os.O_CREATE, 0600)')
    assert oracle.evaluate_model_output(case_id, files, executables())['status'] == ('fail' if variant == 'corrupt' else 'pass')


def test_writer_rejects_wait_beyond_visible_bound():
    files = {'exercise.py': 'import sqlite3\ndef open_database(path):\n    return sqlite3.connect(path, timeout=6.2)\n'}
    result = oracle.evaluate_model_output('sqlite-database-profile/positive/writer-wal', files, executables())
    assert result['status'] == 'fail'
    assert 'not less than 6.0' in result['hidden_oracle']['stderr']


@pytest.mark.parametrize('case_id', ['go-language-profile/positive/cancellation',
                                    'go-language-profile/positive/concurrency'])
def test_ordered_cancellation_and_concurrency_fixtures(case_id):
    spec = fixtures.ORACLES[case_id]
    assert 'time.Sleep' not in '\n'.join(spec.hidden_oracle_files.values())
    result = oracle.evaluate_model_output(case_id, spec.good_files, executables())
    assert result['status'] == 'pass', result
    assert oracle.evaluate_model_output(case_id, spec.bad_files, executables())['status'] == 'fail'


def test_transfer_rejects_false_success_signal():
    case_id = 'sqlite-database-profile/positive/transactions'
    files = dict(fixtures.ORACLES[case_id].good_files)
    files['transfer.py'] += '    return False\n'
    assert oracle.evaluate_model_output(case_id, files, executables())['status'] == 'fail'
