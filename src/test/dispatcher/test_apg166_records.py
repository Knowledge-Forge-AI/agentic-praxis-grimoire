"""H evidence identity and acquisition checks; no effective skill-use claim."""
import base64
import hashlib
import json
import subprocess
from pathlib import Path

import pytest
from test_agent_phase_acquisition import binary, command
from agent_phase.acquisition_records import records

ROOT = Path(__file__).resolve().parents[3]
PRIMARY = ('go-language-profile', 'go-test-profile', 'pytest-test-profile',
           'markdown-language-profile', 'sqlite-database-profile')


def encoded(v):
    return (json.dumps(v, indent=2, sort_keys=True) + '\n').encode()


@pytest.mark.parametrize('skill', PRIMARY)
def test_primary_body_provenance_and_late_acquisition(binary, tmp_path, skill):
    record = json.loads((ROOT / f'docs/evaluations/apg166/promotions/{skill}.json').read_bytes())
    source = (ROOT / record['source_path']).read_bytes()
    assert hashlib.sha256(source).hexdigest() == record['whole_source']['sha256']
    body = source[source.index(b'\n---\n', 4)+5:]
    assert hashlib.sha256(body).hexdigest() == record['body_only']['sha256']
    assert not record['eligible_for_stable'] and record['independent_review'] is None
    ledger = json.loads((ROOT / 'docs/governance/skill-maturity-ledger.json').read_bytes())
    entry = next(x for x in ledger['skills'] if x['skill_id'] == skill)
    assert hashlib.sha256(encoded(entry)).hexdigest() == record['ledger_entry']['sha256']
    assert entry['current_maturity'] == 'provisional'
    assert set(record['evidence']) == set(entry['required_evidence_categories'])
    catalog = json.loads((ROOT / 'skills/catalog_generated.json').read_bytes())
    descriptor = next(x for x in catalog['skills'] if x['id'] == skill)
    assert hashlib.sha256(encoded(descriptor)).hexdigest() == record['descriptor']['sha256']
    result = subprocess.run(command(binary, tmp_path, 'skills', 'acquire', 'apgr:' + skill), capture_output=True, check=True, timeout=15)
    acquired = json.loads(result.stdout)
    assert base64.b64decode(acquired['selection']['snapshot']['body']) == source
    assert (tmp_path / acquired['materialized_path'] / 'SKILL.md').read_bytes() == source
    search = subprocess.run(command(binary, tmp_path, 'skills', 'search', skill), capture_output=True, check=True, timeout=15)
    delivered = [r['event'] for r in records(tmp_path, 'run') if r['event']['kind'] in ('channel_delivered', 'response_delivered')]
    assert sum(r['controlled_bytes'] for r in delivered) == len(result.stdout) + len(search.stdout)
    assert len(delivered) == 2


def test_historical_seal_preserves_frozen_inputs():
    seal = json.loads((ROOT / 'docs/evaluations/apg166/seal.json').read_bytes())
    for name, sha in seal['files'].items():
        # APG166A intentionally changes measurement/launch implementation. The
        # historical seal stays immutable; only its frozen acceptance inputs
        # remain current. APG166A's readiness inventory owns current code checks.
        frozen = (name.startswith('testing/fixtures/context-eval/') and name.endswith('.json'))
        frozen = frozen or (name.startswith('skills/') and name.endswith('/SKILL.md'))
        frozen = frozen or name == 'docs/governance/skill-maturity-ledger.json'
        if frozen:
            assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == sha
            committed = subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=ROOT)
            assert hashlib.sha256(committed).hexdigest() == sha
    raw = json.loads((ROOT / 'docs/evaluations/apg166/raw.json').read_bytes())
    assert raw['seal_sha256'] == hashlib.sha256(encoded(seal)).hexdigest()


def test_aggregate_recomputes_and_unavailable_is_not_zero():
    import importlib.util
    spec = importlib.util.spec_from_file_location('h', ROOT / 'testing/h_eval/evaluate.py')
    h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)
    directory = ROOT / 'docs/evaluations/apg166'
    raw = h.load(directory / 'raw.json')
    aggregate = h.aggregate(raw, h.load(ROOT / h.CORPUS / 'context-eval-metrics-and-oracles.json'))
    assert aggregate == h.load(directory / 'aggregate.json')
    assert aggregate['qualified_promotions'] == 0 and not aggregate['benefit_gate_pass']
    assert aggregate['full_applicable']['measured_n'] == 0
    assert aggregate['full_applicable']['median_savings'] is None
    assert aggregate['non_synthetic']['expected_n'] == 3


def test_raw_schema_required_shapes_and_unavailability():
    """Check the declared required/closed fields and missing-value contract.

    This is the H schema's exercised subset, not a general JSON Schema engine.
    """
    schema = json.loads((ROOT / 'testing/h_eval/results.schema.json').read_bytes())
    raw = json.loads((ROOT / 'docs/evaluations/apg166/raw.json').read_bytes())
    assert set(raw) == set(schema['properties'])
    assert len(raw['rows']) == schema['properties']['rows']['minItems'] == 15
    shape = schema['properties']['rows']['items']
    arms = schema['$defs']['arm']
    for row in raw['rows']:
        assert set(row) == set(shape['properties'])
        assert set(row['arms']) == {'static', 'adaptive'}
        for arm in row['arms'].values():
            assert set(arms['required']) <= set(arm) <= set(arms['properties'])
            for key in arms['required']:
                if key not in ('route', 'deliveries', 'quality_oracle'):
                    observation = arm[key]
                    assert observation['source'] == 'unavailable'
                    assert observation['value'] is None and observation['reason']
