"""H evidence identity and acquisition checks; no effective skill-use claim."""
import base64
import hashlib
import json
import subprocess
from pathlib import Path

import pytest
from test_agent_phase_acquisition import binary as acquisition_binary, command
from agent_phase.acquisition_records import records

# Expose the imported fixture under the name requested by these tests.
binary = acquisition_binary

ROOT = Path(__file__).resolve().parents[3]
PRIMARY = ('go-language-profile', 'go-test-profile', 'pytest-test-profile',
           'markdown-language-profile', 'sqlite-database-profile')

# The v0.13.1 Vite 8.2.4 fixture/profile correction supersedes exactly one
# historical frozen input. The seal keeps its original whole-body hash; the
# current skill is held to the maintained 8.2.4 contract instead.
VITE_SKILL = 'skills/vite-build-profile/SKILL.md'
VITE_HISTORICAL_SHA256 = 'c455c78206ef7dd759379d3889d9d55e888ea3700a55dfcb9b48e036e7c91482'
VITE_CURRENT = {
    'body_sha256': 'c09181f32e1bea94fddd998210f843f3573ef5bdffcb575588cc7d6b6b8759e3',
    'body_only_sha256': '8f7133a1a6f928580b215bed2610a282e43a171942d2ae0fcf1c119d1592933e',
    'content_identity': '92e4e639348fc859ac840afad297617e99262db9ff1ea6a8529b365bedebde5b',
}
VITE_VERSION = '8.2.4'
VITE_RESOLVED = 'https://registry.npmjs.org/vite/-/vite-8.2.4.tgz'
VITE_INTEGRITY = ('sha512-lfauXnrf2x0p+UoA+wXh0dgFWnUjCyG6Js95KBkgaCwUU9k0DAHI4W6Q0WCx'
                  '+h+5g+Alce1y4Zi2QjjK0UvGBw==')
VITE_CATALOG = 'skills/catalog_generated.json'
VITE_METADATA = 'src/agentic_praxis_grimoire/resources/skill-metadata.json'
VITE_PACKAGE = 'src/test/fixtures/apg124-toolchain/vite/package.json'
VITE_LOCK = 'src/test/fixtures/apg124-toolchain/vite/package-lock.json'
VITE_CONTRACT = (VITE_SKILL, VITE_CATALOG, VITE_METADATA, VITE_PACKAGE, VITE_LOCK)


def encoded(v):
    return (json.dumps(v, indent=2, sort_keys=True) + '\n').encode()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def frozen_input(name):
    # APG166A intentionally changes measurement/launch implementation. The
    # historical seal stays immutable; only its frozen acceptance inputs
    # remain current. APG166A's readiness inventory owns current code checks.
    frozen = (name.startswith('testing/fixtures/context-eval/') and name.endswith('.json'))
    frozen = frozen or (name.startswith('skills/') and name.endswith('/SKILL.md'))
    frozen = frozen or name == 'docs/governance/skill-maturity-ledger.json'
    return frozen


def verify_current_vite(current):
    """Hold the superseding Vite skill to its maintained 8.2.4 contract."""
    source = current(VITE_SKILL)
    assert sha256(source) == VITE_CURRENT['body_sha256'], 'current Vite skill bytes'
    body = source[source.index(b'\n---\n', 4)+5:]
    assert sha256(body) == VITE_CURRENT['body_only_sha256'], 'current Vite skill body'
    catalog = json.loads(current(VITE_CATALOG))
    descriptor = next(x for x in catalog['skills'] if x['id'] == 'vite-build-profile')
    for key, value in VITE_CURRENT.items():
        assert descriptor[key] == value, f'current Vite catalog {key}'
    metadata = json.loads(current(VITE_METADATA))
    entry = next(x for x in metadata['skills'] if x['name'] == 'vite-build-profile')
    assert entry['path'] == VITE_SKILL, 'current Vite metadata path'
    assert entry['source_sha256'] == VITE_CURRENT['body_sha256'], 'current Vite metadata source'
    package = json.loads(current(VITE_PACKAGE))
    assert package['dependencies'] == {'vite': VITE_VERSION}, 'current Vite fixture dependency'
    lock = json.loads(current(VITE_LOCK))
    assert lock['packages']['']['dependencies'] == {'vite': VITE_VERSION}, 'current Vite lock root'
    locked = lock['packages']['node_modules/vite']
    assert (locked['version'], locked['resolved'], locked['integrity']) == (
        VITE_VERSION, VITE_RESOLVED, VITE_INTEGRITY), 'current Vite lock record'


def verify_frozen_inputs(seal, *, current, committed):
    """Check frozen seal inputs against the working tree and HEAD.

    Exactly one path, VITE_SKILL, is exempt from both equalities. It must keep
    its historical seal entry and must satisfy the current Vite contract.
    """
    assert seal['files'].get(VITE_SKILL) == VITE_HISTORICAL_SHA256, 'historical Vite seal entry'
    for name, sha in seal['files'].items():
        if not frozen_input(name) or name == VITE_SKILL:
            continue
        assert sha256(current(name)) == sha, f'working tree differs from seal: {name}'
        assert sha256(committed(name)) == sha, f'HEAD differs from seal: {name}'
    verify_current_vite(current)


def verify_seal_digest(raw, seal):
    assert raw['seal_sha256'] == sha256(encoded(seal)), 'raw seal digest'


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
    verify_frozen_inputs(
        seal,
        current=lambda name: (ROOT / name).read_bytes(),
        committed=lambda name: subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=ROOT),
    )
    raw = json.loads((ROOT / 'docs/evaluations/apg166/raw.json').read_bytes())
    verify_seal_digest(raw, seal)


OTHER_SKILL = 'skills/other-profile/SKILL.md'
CONTEXT_EVAL = 'testing/fixtures/context-eval/fixture.json'
LEDGER = 'docs/governance/skill-maturity-ledger.json'
LOOKALIKES = ('skills/vite-build-profile-x/SKILL.md', 'skills/chatgpt/vite-build-profile/SKILL.md')


def synthetic_inputs():
    """In-memory seal and readers; nothing tracked, retained or committed changes."""
    current = {name: (ROOT / name).read_bytes() for name in VITE_CONTRACT}
    for name in (OTHER_SKILL, CONTEXT_EVAL, LEDGER, *LOOKALIKES):
        current[name] = f'frozen {name}\n'.encode()
    committed = dict(current)
    # HEAD may still hold the superseded Vite body; it is intentionally unchecked.
    committed[VITE_SKILL] = b'superseded historical Vite body\n'
    files = {name: sha256(current[name]) for name in (OTHER_SKILL, CONTEXT_EVAL, LEDGER, *LOOKALIKES)}
    files[VITE_SKILL] = VITE_HISTORICAL_SHA256
    # Non-frozen entries stay unchecked, as before.
    files['skills/catalog_generated.json'] = '0' * 64
    return {'files': files}, current, committed


def run_synthetic(seal, current, committed):
    verify_frozen_inputs(seal, current=current.__getitem__, committed=committed.__getitem__)


def test_synthetic_frozen_inputs_pass_unmodified():
    run_synthetic(*synthetic_inputs())


@pytest.mark.parametrize('mutation', ['missing', 'wrong'])
def test_historical_vite_seal_entry_is_required(mutation):
    seal, current, committed = synthetic_inputs()
    if mutation == 'missing':
        del seal['files'][VITE_SKILL]
    else:
        seal['files'][VITE_SKILL] = VITE_CURRENT['body_sha256']
    with pytest.raises(AssertionError, match='historical Vite seal entry'):
        run_synthetic(seal, current, committed)


def test_current_vite_skill_bytes_are_required():
    seal, current, committed = synthetic_inputs()
    current[VITE_SKILL] = current[VITE_SKILL] + b'\n'
    with pytest.raises(AssertionError, match='current Vite skill bytes'):
        run_synthetic(seal, current, committed)


@pytest.mark.parametrize('key', sorted(VITE_CURRENT))
def test_current_vite_catalog_descriptor_is_required(key):
    seal, current, committed = synthetic_inputs()
    catalog = json.loads(current[VITE_CATALOG])
    descriptor = next(x for x in catalog['skills'] if x['id'] == 'vite-build-profile')
    descriptor[key] = '0' * 64
    current[VITE_CATALOG] = json.dumps(catalog).encode()
    with pytest.raises(AssertionError, match=f'current Vite catalog {key}'):
        run_synthetic(seal, current, committed)


def test_current_vite_metadata_source_is_required():
    seal, current, committed = synthetic_inputs()
    metadata = json.loads(current[VITE_METADATA])
    entry = next(x for x in metadata['skills'] if x['name'] == 'vite-build-profile')
    entry['source_sha256'] = VITE_HISTORICAL_SHA256
    current[VITE_METADATA] = json.dumps(metadata).encode()
    with pytest.raises(AssertionError, match='current Vite metadata source'):
        run_synthetic(seal, current, committed)


def test_current_vite_fixture_and_lock_are_required():
    seal, current, committed = synthetic_inputs()
    package = json.loads(current[VITE_PACKAGE])
    package['dependencies']['vite'] = '8.2.2'
    stale = dict(current, **{VITE_PACKAGE: json.dumps(package).encode()})
    with pytest.raises(AssertionError, match='current Vite fixture dependency'):
        run_synthetic(seal, stale, committed)

    lock = json.loads(current[VITE_LOCK])
    lock['packages']['node_modules/vite']['version'] = '8.2.2'
    stale = dict(current, **{VITE_LOCK: json.dumps(lock).encode()})
    with pytest.raises(AssertionError, match='current Vite lock record'):
        run_synthetic(seal, stale, committed)


@pytest.mark.parametrize('name', [OTHER_SKILL, CONTEXT_EVAL, LEDGER])
def test_non_vite_working_tree_mismatch_fails(name):
    seal, current, committed = synthetic_inputs()
    current[name] = b'changed\n'
    with pytest.raises(AssertionError, match=f'working tree differs from seal: {name}'):
        run_synthetic(seal, current, committed)


@pytest.mark.parametrize('name', [OTHER_SKILL, CONTEXT_EVAL, LEDGER])
def test_non_vite_head_mismatch_fails(name):
    seal, current, committed = synthetic_inputs()
    committed[name] = b'changed\n'
    with pytest.raises(AssertionError, match=f'HEAD differs from seal: {name}'):
        run_synthetic(seal, current, committed)


@pytest.mark.parametrize('name', LOOKALIKES)
@pytest.mark.parametrize('reader', ['current', 'committed'])
def test_similarly_named_skill_receives_no_exception(name, reader):
    seal, current, committed = synthetic_inputs()
    (current if reader == 'current' else committed)[name] = b'changed\n'
    where = 'working tree' if reader == 'current' else 'HEAD'
    with pytest.raises(AssertionError, match=f'{where} differs from seal: {name}'):
        run_synthetic(seal, current, committed)


def test_raw_seal_digest_refuses_tampered_seal():
    seal = json.loads((ROOT / 'docs/evaluations/apg166/seal.json').read_bytes())
    raw = json.loads((ROOT / 'docs/evaluations/apg166/raw.json').read_bytes())
    tampered = json.loads(json.dumps(seal))
    tampered['files'][VITE_SKILL] = VITE_CURRENT['body_sha256']
    with pytest.raises(AssertionError, match='raw seal digest'):
        verify_seal_digest(raw, tampered)


def test_aggregate_recomputes_and_unavailable_is_not_zero():
    import importlib.util
    spec = importlib.util.spec_from_file_location('h', ROOT / 'testing/h_eval/evaluate.py')
    h = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(h)
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
