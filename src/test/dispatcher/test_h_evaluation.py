"""Aggregation contract tests use synthetic observations, never H benefit data."""
import copy
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('h_evaluation', ROOT / 'testing/h_eval/evaluate.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
METRICS = h.load(ROOT / h.CORPUS / 'context-eval-metrics-and-oracles.json')


def measured(value):
    return {'source': 'measured', 'value': value}


def fixture():
    rows = []
    for n in range(1, 16):
        arms = {}
        for arm, size in (('static', 100), ('adaptive', 75)):
            route = {'provider': 'fixture', 'binding': 'same', 'model_route': measured('fixture'),
                     'execution': 'live', 'requested_context_mode': arm}
            arms[arm] = {'route': route, 'initial': measured(size), 'cumulative': measured(size),
                         'coverage': measured('complete'),
                         'deliveries': [{'id': 'one', 'phase': 'initial', 'bytes': size,
                                         'sha256': 'a' * 64, 'channel': 'prompt', 'source': 'measured'}],
                         'task_outcome': measured('pass'), 'authority': measured('preserved'),
                         'exact_recovery': measured(True),
                         'selective_discovery': measured('qualified-no-leakage-settings-unchanged')}
        rows.append({'scenario_id': f'scenario-{n:02}', 'synthetic_inputs': n in (8, 9), 'arms': arms})
    return {'schema_version': h.SCHEMA, 'boundary': h.BOUNDARY, 'scenario15': 'qualified', 'rows': rows}


def test_formula_dual_cohort():
    raw = fixture()
    result = h.aggregate(raw, METRICS)
    assert result['full_applicable']['expected_n'] == 6
    assert result['non_synthetic']['expected_n'] == 4
    assert result['full_applicable']['median_savings'] == .25
    assert result['full_applicable']['nearest_rank_p95_growth'] == -.25
    assert result['benefit_gate_pass']


@pytest.mark.parametrize('n', [1, 3, 4, 5, 6, 20, 21])
def test_nearest_rank(n):
    assert h.p95(list(range(n))) == __import__('math').ceil(.95 * n) - 1


def test_repeat_and_views():
    event = fixture()['rows'][0]['arms']['static']['deliveries'][0]
    assert h.delivered_totals([event, event]) == (100, 100)
    again = {**event, 'id': 'two', 'phase': 'late'}
    assert h.delivered_totals([event, again]) == (100, 200)
    with pytest.raises(ValueError, match='conflicting'):
        h.delivered_totals([event, {**event, 'bytes': 101}])


def test_missing_rejected_not_dropped():
    raw = fixture()
    raw['rows'][5]['arms']['adaptive']['initial'] = h.unavailable('not observed')
    result = h.aggregate(raw, METRICS)
    assert not result['benefit_gate_pass']
    assert result['full_applicable']['missing'] == ['scenario-06']
    del raw['rows'][5]['arms']['static']
    with pytest.raises(ValueError, match='missing pair'):
        h.aggregate(raw, METRICS)
    with pytest.raises(ValueError, match='missing or duplicate'):
        h.aggregate({**raw, 'rows': raw['rows'][:-1]}, METRICS)


def test_route_mismatch_and_invalid_denominator():
    raw = fixture()
    raw['rows'][5]['arms']['adaptive']['route']['binding'] = 'different'
    with pytest.raises(ValueError, match='route mismatch'):
        h.aggregate(raw, METRICS)
    raw = fixture()
    arm = raw['rows'][5]['arms']['static']
    arm['initial'] = arm['cumulative'] = measured(0)
    arm['deliveries'][0]['bytes'] = 0
    with pytest.raises(ValueError, match='positive'):
        h.aggregate(raw, METRICS)


def test_scenario15_contingency_is_not_full_evidence():
    raw = fixture()
    raw['scenario15'] = 'contingent/unavailable'
    result = h.aggregate(raw, METRICS)
    assert result['full_applicable']['expected_n'] == 5
    assert result['non_synthetic']['expected_n'] == 3
    assert result['full_applicable']['pass']
    assert not result['benefit_gate_pass']
    raw['scenario15'] = 'qualified'
    del raw['rows'][14]['arms']['adaptive']['selective_discovery']
    with pytest.raises(ValueError, match='contingency evidence'):
        h.aggregate(raw, METRICS)


def test_synthetic_improvement_cannot_hide_canonical_failure():
    raw = fixture()
    for index in (5, 9, 10, 14):
        arm = raw['rows'][index]['arms']['adaptive']
        arm['initial'] = arm['cumulative'] = measured(90)
        arm['deliveries'][0]['bytes'] = 90
    result = h.aggregate(raw, METRICS)
    assert not result['non_synthetic']['pass']
    assert not result['benefit_gate_pass']


def test_untagged_and_failed_quality_do_not_pass():
    raw = fixture()
    raw['rows'][6]['arms']['adaptive']['task_outcome'] = h.unavailable('no model')
    assert not h.aggregate(raw, METRICS)['benefit_gate_pass']
    raw = fixture()
    raw['rows'][9]['arms']['adaptive']['exact_recovery'] = measured(False)
    assert not h.aggregate(raw, METRICS)['benefit_gate_pass']
    raw = fixture()
    raw['rows'][5]['arms']['static']['deliveries'][0]['source'] = 'synthetic'
    with pytest.raises(ValueError, match='unmeasured'):
        h.aggregate(raw, METRICS)


def test_frozen_inputs_and_synthetic_materialization(tmp_path):
    rows = h.scenarios(ROOT)
    assert len(rows) == 15
    for index in (7, 8):
        subject = tmp_path / str(index)
        subject.mkdir()
        catalog, evidence = h.synthetic_catalog(rows[index], subject)
        assert evidence['whole_bytes'] == 690
        assert catalog['snapshots'][0]['qualified_id'] == 'project:go-language-profile'


def test_seal_rejects_drift_before_observation(tmp_path):
    binary = tmp_path / 'binary'
    binary.write_bytes(b'fixture binary identity only')
    seal = h.make_seal(ROOT, binary)
    h.verify_seal(ROOT, binary, seal)
    seal['files']['skills/context_plan.go'] = '0' * 64
    with pytest.raises(ValueError, match='sealed inputs changed'):
        h.verify_seal(ROOT, binary, seal)
    binary.write_bytes(b'changed')
    with pytest.raises(ValueError, match='binary mismatch'):
        h.verify_seal(ROOT, binary, seal)
