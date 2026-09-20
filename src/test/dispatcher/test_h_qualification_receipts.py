"""Receipt completeness, exclusive reruns, and causal predicate refusal."""
import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest
from testing.h_eval import qualification_receipts as qr
from testing.h_eval.run_focused_test_batches import summarize, reconcile
from testing.h_eval.run_sqlite_writer_wal_causal_proof import compare, oracle_receipt


def test_real_pytest_outcomes_include_setup_errors_and_xfails(tmp_path):
    test = tmp_path / 'test_outcomes.py'
    test.write_text('''import pytest
@pytest.fixture
def broken():
    raise RuntimeError('setup fails')
def test_ok(): pass
def test_failure(): assert False
def test_error(broken): pass
@pytest.mark.skip(reason='example')
def test_skip(): pass
@pytest.mark.xfail(reason='example')
def test_xfail(): assert False
@pytest.mark.xfail(reason='example')
def test_xpass(): pass
@pytest.fixture
def bad_teardown():
    yield
    raise RuntimeError('teardown fails')
def test_pass_then_error(bad_teardown): pass
def test_fail_then_error(bad_teardown): assert False
''')
    import os
    env = dict(os.environ, APG_PYTEST_RECEIPT=str(tmp_path / 'events.json'), PYTHONDONTWRITEBYTECODE='1')
    result = subprocess.run([sys.executable, '-m', 'pytest', '-p', 'no:cacheprovider', '-p',
                             'testing.h_eval.pytest_receipt_plugin', '-q', str(test)],
                            env=env, cwd=qr.ROOT, capture_output=True)
    cases, counts, complete = summarize(json.loads((tmp_path / 'events.json').read_text()), result.returncode)
    assert complete
    assert counts == dict(collected=8, passed=2, failed=2, errors=3, skipped=1, xfailed=1, xpassed=1, incomplete=0)
    assert len(cases) == 8


def test_real_pytest_reasonless_xfail_and_xpass_are_not_skips(tmp_path):
    test = tmp_path / 'test_reasonless.py'
    test.write_text('''import pytest
def test_pass(): pass
def test_fail(): assert False
@pytest.mark.skip
def test_plain_skip(): pass
@pytest.mark.xfail
def test_reasonless_xfail(): assert False
@pytest.mark.xfail
def test_reasonless_xpass(): pass
@pytest.mark.xfail(strict=True)
def test_reasonless_strict_xpass(): pass
@pytest.fixture
def broken():
    raise RuntimeError('setup fails')
def test_setup_error(broken): pass
@pytest.fixture
def bad_teardown():
    yield
    raise RuntimeError('teardown fails')
def test_teardown_error(bad_teardown): pass
''')
    import os
    events_path = tmp_path / 'events.json'
    env = dict(os.environ, APG_PYTEST_RECEIPT=str(events_path), PYTHONDONTWRITEBYTECODE='1')
    result = subprocess.run([sys.executable, '-m', 'pytest', '-p', 'no:cacheprovider', '-p',
                             'testing.h_eval.pytest_receipt_plugin', '-q', str(test)],
                            env=env, cwd=qr.ROOT, capture_output=True)
    events = json.loads(events_path.read_text())
    # Reasonless markers are recorded as '' rather than dropped to None.
    wasxfail = {r['nodeid'].rsplit('::', 1)[1]: r['wasxfail'] for r in events['reports'] if r['when'] == 'call'}
    assert wasxfail['test_reasonless_xfail'] == '' and wasxfail['test_reasonless_xpass'] == ''
    cases, counts, complete = summarize(events, result.returncode)
    assert result.returncode == 1 and complete
    outcomes = {c['nodeid'].rsplit('::', 1)[1]: c['outcome'] for c in cases}
    assert outcomes == {'test_pass': 'passed', 'test_fail': 'failed', 'test_plain_skip': 'skipped',
                        'test_reasonless_xfail': 'xfailed', 'test_reasonless_xpass': 'xpassed',
                        'test_reasonless_strict_xpass': 'xpassed', 'test_setup_error': 'errors',
                        'test_teardown_error': 'errors'}
    assert counts == dict(collected=8, passed=2, failed=1, errors=2, skipped=1, xfailed=1, xpassed=2, incomplete=0)


@pytest.mark.parametrize('row,expected', [
    (dict(outcome='skipped', wasxfail='', strict_xpass=False), 'xfailed'),
    (dict(outcome='passed', wasxfail='', strict_xpass=False), 'xpassed'),
    (dict(outcome='skipped', wasxfail=None, strict_xpass=False), 'skipped'),
    (dict(outcome='passed', wasxfail=None, strict_xpass=False), 'passed'),
    (dict(outcome='failed', wasxfail=None, strict_xpass=False), 'failed'),
    (dict(outcome='failed', wasxfail=None, strict_xpass=True), 'xpassed'),
    (dict(outcome='skipped', wasxfail='reason', strict_xpass=False), 'xfailed'),
], ids=['reasonless-xfail', 'reasonless-xpass', 'skip', 'pass', 'fail', 'strict-xpass', 'reasoned-xfail'])
def test_summary_classifies_xfail_marker_by_presence(row, expected):
    node = 't.py::x'
    reports = [dict(nodeid=node, when='setup', outcome='passed', wasxfail=None, strict_xpass=False),
               dict(row, nodeid=node, when='call'),
               dict(nodeid=node, when='teardown', outcome='passed', wasxfail=None, strict_xpass=False)]
    exit_code = 1 if expected == 'failed' or row['strict_xpass'] else 0
    cases, counts, complete = summarize({'collected_nodeids': [node], 'reports': reports,
                                         'collection_errors': [], 'exit_code': exit_code}, exit_code)
    assert complete
    assert cases == [{'nodeid': node, 'outcome': expected}]
    assert counts[expected] == 1


def test_receipt_missing_outcome_fails_closed():
    cases, counts, complete = summarize({'collected_nodeids': ['test_x'], 'reports': [],
                                        'collection_errors': [], 'exit_code': 0}, 0)
    assert counts['incomplete'] == 1
    assert not complete


def test_attempts_and_artifacts_are_exclusive(tmp_path):
    first, second = qr.new_attempt(tmp_path, 'suite'), qr.new_attempt(tmp_path, 'suite')
    assert first != second
    qr.write_json(first / 'receipt.json', {'a': 1})
    with pytest.raises(FileExistsError):
        qr.write_json(first / 'receipt.json', {'a': 2})
    assert json.loads((first / 'receipt.json').read_text()) == {'a': 1}


def test_reconciliation_derives_unique_nodes(tmp_path):
    common = dict(suite_id='a', attempt_id='a-1', source_identity={'candidate_sha256': 'x'},
                  passed=True, included_in_canonical_unique_aggregate=True)
    selected = [dict(common, test_cases=[{'nodeid': 'one'}]),
                dict(common, suite_id='b', attempt_id='b-1', test_cases=[{'nodeid': 'one'}, {'nodeid': 'two'}])]
    result = reconcile(selected, tmp_path)
    assert result['canonical_focused_case_count'] == 2
    assert result['unique_nodeids'] == ['one', 'two']
    # Two passing suites on one candidate are still a partial run.
    assert result['all_selected_passed'] and result['same_candidate']
    assert not result['required_suite_coverage']
    assert not result['covering_qualification']


def _selected(passed=True, candidate='x', suites=None, drop=()):
    from testing.h_eval.run_focused_test_batches import FOCUSED, SEPARATE
    names = [s for s in (suites or FOCUSED + SEPARATE) if s not in drop]
    return [dict(suite_id=s, attempt_id=s + '-1', source_identity={'candidate_sha256': candidate},
                 passed=passed if s == 'agent_phase_provider_stream' else True,
                 included_in_canonical_unique_aggregate=s in FOCUSED,
                 test_cases=[{'nodeid': s + '::t'}]) for s in names]


@pytest.mark.parametrize('kwargs,field', [
    (dict(), None),
    (dict(passed=False), 'all_selected_passed'),
    (dict(drop=('agent_phase_provider_stream',)), 'required_suite_coverage'),
    (dict(drop=('h_d1_seam',)), 'required_suite_coverage'),
], ids=['covering', 'failed-provider-stream', 'partial-separate', 'partial-focused'])
def test_covering_qualification_requires_pass_candidate_and_coverage(tmp_path, kwargs, field):
    result = reconcile(_selected(**kwargs), tmp_path)
    if field is None:
        assert result['covering_qualification']
    else:
        assert not result[field]
        assert not result['covering_qualification']


def test_mixed_candidates_and_duplicate_suites_do_not_cover(tmp_path):
    mixed = _selected()
    mixed[0]['source_identity'] = {'candidate_sha256': 'other'}
    assert not reconcile(mixed, tmp_path)['covering_qualification']
    duplicated = _selected() + _selected()[:1]
    assert not reconcile(duplicated, tmp_path)['required_suite_coverage']


@pytest.mark.parametrize('field', ['all_selected_passed', 'same_candidate', 'required_suite_coverage'])
def test_main_exit_requires_every_covering_condition(tmp_path, monkeypatch, field):
    from testing.h_eval import run_focused_test_batches as batches
    value = {'all_selected_passed': True, 'same_candidate': True, 'required_suite_coverage': True}
    value[field] = False
    monkeypatch.setattr(batches, 'run_batch', lambda name, parent: {'suite_id': name})
    monkeypatch.setattr(batches, 'reconcile', lambda selected, parent: dict(
        value, covering_qualification=all(value.values())))
    monkeypatch.setattr(sys, 'argv', ['run', '--qualification-dir', str(tmp_path)])
    assert batches.main() == 1
    value[field] = True
    monkeypatch.setattr(sys, 'argv', ['run', '--qualification-dir', str(tmp_path / 'second')])
    assert batches.main() == 0


def _reconciliation(nodes):
    return {'unique_nodeids': sorted(nodes), 'canonical_focused_case_count': len(nodes)}


def test_node_set_delta_reports_exact_additions():
    from testing.h_eval.run_focused_test_batches import node_set_delta
    prior = _reconciliation([f'n{i:03}' for i in range(184)])
    current = _reconciliation([f'n{i:03}' for i in range(188)])
    delta = node_set_delta(prior, current)
    assert delta['valid'] and delta['pure_addition']
    assert (delta['prior_count'], delta['current_count']) == (184, 188)
    assert delta['added'] == ['n184', 'n185', 'n186', 'n187'] and delta['removed'] == []
    assert delta['unchanged_count'] == 184
    assert delta['count_equation'] == '184 - 0 + 4 = 188'


def test_node_set_delta_exposes_replacement_hidden_by_count():
    from testing.h_eval.run_focused_test_batches import node_set_delta
    # A +4 count difference can hide removals; the set delta shows them.
    prior = _reconciliation(['a', 'b', 'c'])
    current = _reconciliation(['a', 'd', 'e', 'f', 'g', 'h', 'i'])
    delta = node_set_delta(prior, current)
    assert delta['current_count'] - delta['prior_count'] == 4
    assert delta['removed'] == ['b', 'c'] and delta['added_count'] == 6
    assert not delta['pure_addition']
    assert delta['count_equation'] == '3 - 2 + 6 = 7'


@pytest.mark.parametrize('mutate', [
    lambda v: v.update(canonical_focused_case_count=v['canonical_focused_case_count'] + 1),
    lambda v: v.update(unique_nodeids=v['unique_nodeids'] + v['unique_nodeids'][:1]),
    lambda v: v.update(unique_nodeids=list(reversed(v['unique_nodeids']))),
], ids=['count-mismatch', 'duplicate', 'unsorted'])
def test_node_set_delta_refuses_inconsistent_inputs(mutate):
    from testing.h_eval.run_focused_test_batches import node_set_delta
    current = _reconciliation(['a', 'b', 'c'])
    mutate(current)
    delta = node_set_delta(_reconciliation(['a', 'b']), current)
    assert not delta['inputs_consistent']['current']
    assert not delta['valid']


def test_node_set_delta_refuses_missing_node_list():
    from testing.h_eval.run_focused_test_batches import node_set_delta
    with pytest.raises(ValueError, match='prior'):
        node_set_delta({'canonical_focused_case_count': 3}, _reconciliation(['a']))


def test_compare_cli_writes_input_bound_delta(tmp_path, monkeypatch, capsys):
    from testing.h_eval import run_focused_test_batches as batches
    prior, current = tmp_path / 'prior.json', tmp_path / 'current.json'
    prior.write_text(json.dumps(_reconciliation(['a'])))
    current.write_text(json.dumps(_reconciliation(['a', 'b'])))
    monkeypatch.setattr(sys, 'argv', ['run', '--compare', str(prior), str(current),
                                      '--qualification-dir', str(tmp_path / 'q')])
    assert batches.main() == 0
    [written] = (tmp_path / 'q').glob('node-set-delta-*/node-set-delta.json')
    value = json.loads(written.read_text())
    assert value['added'] == ['b']
    assert value['inputs']['prior']['sha256'] == qr.digest(prior.read_bytes())
    assert json.loads(capsys.readouterr().out)['count_equation'] == '1 - 0 + 1 = 2'
    link = tmp_path / 'link.json'
    link.symlink_to(prior)
    monkeypatch.setattr(sys, 'argv', ['run', '--compare', str(link), str(current)])
    with pytest.raises(ValueError, match='non-symlink'):
        batches.main()


def test_exact_preregistered_source_set():
    value = oracle_receipt()
    assert len(value['source_paths']) == 6
    assert value['oracle_sha256_matches_preregistration']
    assert set(value['files']) == set(value['source_paths'])


def vectors():
    inventory = {'f': {'type': 'file', 'sha256': 'h', 'bytes': 1}}
    common = dict(executable='python', executable_sha256='hash', version='v', fixture_files={'f': 'h'},
                  oracle={'oracle_sha256_matches_preregistration': True}, command=['python'],
                  fixture_inventory_before=inventory, fixture_inventory_after=dict(inventory))
    base = dict(common, cwd='/alias', physical_cwd='/physical', environment={'PWD': '/alias', 'TMPDIR': '/alias', 'LANG': 'C'}, exit_code=1, failure_observed=True)
    canon = dict(common, cwd='/physical', physical_cwd='/physical', environment={'PWD': '/physical', 'TMPDIR': '/physical', 'LANG': 'C'}, exit_code=0, failure_observed=False)
    return base, canon


@pytest.mark.parametrize('field,value', [('executable_sha256', 'other'), ('version', 'other'),
    ('fixture_files', {}), ('command', []), ('exit_code', 1), ('physical_cwd', '/other'),
    ('oracle', {'oracle_sha256_matches_preregistration': False})])
def test_causal_proof_refuses_changed_factors(field, value):
    baseline, canonical = vectors()
    assert compare(baseline, canonical)['causal_proof_passed']
    canonical[field] = value
    assert not compare(baseline, canonical)['causal_proof_passed']


@pytest.mark.parametrize('label,field', [('baseline', 'fixture_inventory_after'),
    ('canonical', 'fixture_inventory_before'), ('canonical', 'fixture_inventory_after')])
def test_causal_proof_refuses_fixture_residue(label, field):
    baseline, canonical = vectors()
    target = baseline if label == 'baseline' else canonical
    target[field] = dict(target[field], **{'events.db': {'type': 'file', 'sha256': 'r', 'bytes': 1}})
    result = compare(baseline, canonical)
    assert not result['controlled_factors_equal']
    assert not result['causal_proof_passed']


def test_fixture_inventory_records_complete_tree_without_following_links(tmp_path):
    from testing.h_eval.run_sqlite_writer_wal_causal_proof import inventory
    (tmp_path / 'a.py').write_text('x')
    (tmp_path / 'sub').mkdir()
    (tmp_path / 'sub' / 'residue.db').write_bytes(b'db')
    (tmp_path / 'link').symlink_to(tmp_path / 'sub', target_is_directory=True)
    value = inventory(tmp_path)
    assert set(value) == {'a.py', 'sub', 'sub/residue.db', 'link'}
    assert value['link']['type'] == 'symlink'
    assert value['sub/residue.db']['bytes'] == 2


HOST_PORTABLE_HELPERS = ('run_focused_test_batches.py', 'run_sqlite_writer_wal_causal_proof.py',
                         'run_final_b8_transaction.py', 'qualification_receipts.py',
                         'pytest_receipt_plugin.py', 'd1_launch_contract.py',
                         'live_admission.py', 'granted_execution.py', 'host_mechanical.py',
                         'prelaunch.py')
# Current R1/R2 surfaces: the readiness record, handoff, exit record and roadmap.
CURRENT_APG166E_SURFACES = ('docs/evaluations/apg166e-provider-free-readiness.md',
                            'docs/evaluations/apg166e/handoff.json',
                            'docs/status/2026/09/23/00227-apg166e-v0130-h-qual6-exit.md',
                            'docs/v0-13-roadmap.md')


@pytest.mark.parametrize('relative', [f'testing/h_eval/{name}' for name in HOST_PORTABLE_HELPERS]
                         + list(CURRENT_APG166E_SURFACES))
def test_helpers_and_current_surfaces_have_no_host_or_launch_literals(relative):
    text = (qr.ROOT / relative).read_text()
    assert '/' + 'Users' + '/' not in text  # split: public confidentiality marker
    assert 'launch-2026' not in text


@pytest.mark.parametrize('instrumented', [False, True])
@pytest.mark.parametrize('field', ['environment_digest', 'allowlist_environment'])
def test_both_authority_paths_verify_source_environment_without_launch(tmp_path, instrumented, field):
    from testing.h_eval import d1_launch_contract as launch, d1_qualification as d1
    plan = {'requested_mode': 'static', 'run_id': 'd1-test', 'binding_id': d1.ALLOWED_BINDING_ID, 'attempt_id': 'one'}
    edir = tmp_path / 'run'
    edir.mkdir()
    (edir / 'd1.context-plan.json').write_text(json.dumps(plan))
    roots = {'isolated_home': {'path': str(tmp_path / 'home')}, 'isolated_tmp': {'path': str(tmp_path / 'tmp')}}
    roots['custody_root'] = {'path': str(tmp_path / 'custody')}
    for value in roots.values():
        Path(value['path']).mkdir()
    operator_home = tmp_path / 'operator-home'
    operator_home.mkdir()
    from testing.h_eval.d1_auth import AUTH_SCHEMA
    auth_path = edir / 'auth-context.json'
    auth_path.write_text(json.dumps({'schema': AUTH_SCHEMA, 'values': {
        'HOME': roots['isolated_home']['path'] if instrumented else str(operator_home)}}))
    argv = [str(qr.ROOT / 'bin/claude-profile'), 'normal-final-review', '--read-only', '-p']
    provider = tmp_path / 'claude'
    provider.write_text('#!/bin/sh\necho 2.1.259\n')
    provider.chmod(0o700)
    selection = d1.select_d1_production_executables(search_path=str(tmp_path)) if not instrumented else None
    expected, effective = launch._expected_environment(edir, roots, instrumented, argv, selection, repo=qr.ROOT)
    receipt = {'environment_digest': d1._sha256(d1._canonical_bytes(effective)), 'allowlist_environment': expected}
    receipt[field] = 'wrong' if field == 'environment_digest' else {}
    authority = {'schema': d1.INSTRUMENTED_AUTHORITY_SCHEMA if instrumented else d1.LIVE_AUTHORITY_SCHEMA}
    with pytest.raises(d1.D1ReadbackError, match=field):
        launch.verify_launch_facts(qr.ROOT, edir, authority, roots, receipt,
                                  {'executable_evidence': {'executable_selection': selection},
                                   'pre_provider': {'auth_context_sha256': d1._sha256(auth_path.read_bytes())}}, argv)
