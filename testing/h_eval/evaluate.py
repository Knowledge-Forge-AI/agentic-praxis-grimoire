"""APG166 sealed, provider-free evidence harness and strict paired aggregator.

This module never starts a provider. The repository has no qualified live H
binding. Prospective planner bytes are separate from delivered context totals.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess

SCHEMA = 'apg.h-evaluation/v1'
PRIMARY = ('go-language-profile', 'go-test-profile', 'pytest-test-profile',
           'markdown-language-profile', 'sqlite-database-profile')
CORPUS = 'testing/fixtures/context-eval'
BOUNDARY = 'apgr-controlled-channel-write/v1'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + '\n').encode()


def load(path):
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ValueError('duplicate JSON key')
            result[k] = v
        return result
    return json.loads(path.read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def scenarios(root):
    rows = [load(p) for p in sorted((root / CORPUS).glob('scenario-*.json'))]
    if [r['scenario_id'] for r in rows] != [f'scenario-{n:02}' for n in range(1, 16)]:
        raise ValueError('all 15 scenarios required')
    for n, row in enumerate(rows, 1):
        if row['subset'] != ('calibration' if n <= 5 else 'acceptance'):
            raise ValueError('subset changed')
        if 'quality_oracle' not in row['expected_outcome']:
            raise ValueError('quality oracle missing')
    return rows


def unavailable(reason):
    return {'source': 'unavailable', 'value': None, 'reason': reason}


def make_seal(root, binary):
    """Capture inputs before any H holdout observations; caller writes exclusively."""
    rows = scenarios(root)
    paths = set()
    for pattern in ('skills/**/*.go', 'skills/**/SKILL.md', 'skills/**/*.json',
                    'internal/acquisition/*.go', 'internal/cli/*.go',
                    'libexec/agent_phase/*context*.py', 'libexec/agent_phase/acquisition*.py',
                    'src/agentic_praxis_grimoire/acquisition.py',
                    'src/test/dispatcher/test_h_*.py',
                    'src/test/dispatcher/test_agent_phase_acquisition.py',
                    'testing/h_eval/*.py', 'testing/h_eval/*.json',
                    CORPUS + '/*.json', CORPUS + '/measure_f.py'):
        paths.update(p for p in root.glob(pattern) if p.is_file())
    paths.update(root / p for p in ('docs/governance/skill-maturity-ledger.json',
                                   'docs/governance/language-profile-known-debt.json'))
    paths.update(root / p for p in ('codex/AGENTS.md', 'claude/CLAUDE.md', 'antigravity/GEMINI.md'))
    routes = {}
    for row in rows:
        binding = {'provider': row['provider'], 'binding': row['role_binding'],
                   'model_route': unavailable('no qualified live paired harness'),
                   'provider_binding': unavailable('native selective projection unqualified')}
        routes[row['scenario_id']] = {arm: {**binding, 'requested_context_mode': arm,
                                           'execution': 'not_invoked'} for arm in ('static', 'adaptive')}
    return {'schema_version': 'apg.h-seal/v1', 'phase': 'APG166',
            'rule_version': 'apg.context-packing/v1', 'boundary': BOUNDARY,
            'files': {str(p.relative_to(root)): digest(p.read_bytes()) for p in sorted(paths)},
            'binary_sha256': digest(binary.read_bytes()), 'routes': routes,
            'policy': 'No holdout tuning. Planner/model/transport observations remain separate.'}


def verify_seal(root, binary, seal):
    if seal['schema_version'] != 'apg.h-seal/v1' or digest(binary.read_bytes()) != seal['binary_sha256']:
        raise ValueError('seal binary mismatch')
    # Recompute the complete inventory as well as bytes: newly added owners count.
    current = make_seal(root, binary)
    if current != seal:
        raise ValueError('sealed inputs changed; invalidate the entire acceptance set')


def synthetic_catalog(row, subject):
    catalog = {'schema_version': 'apg.skill-catalog/v1'}
    project = row.get('catalog_sources', {}).get('project')
    if not project:
        return catalog, None
    raw = project['synthetic_body'].encode()
    body = raw[raw.index(b'\n---\n', 4) + 5:]
    if (len(raw), digest(raw), len(body), digest(body)) != (
            project['whole_bytes'], project['whole_sha256'], project['body_bytes'], project['body_sha256']):
        raise ValueError('synthetic fixture identity mismatch')
    relative = Path(project['canonical_path'])
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('unsafe synthetic path')
    target = subject / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(raw)
    config = row['repository_evidence'].get('configuration_facts', {}).get('project_config')
    if config:
        (subject / '.apgr/config.toml').write_text(config)
    catalog['snapshots'] = [{'qualified_id': project['id'], 'path': str(relative),
                             'body': base64.b64encode(raw).decode(), 'support': {}}]
    catalog['overrides'] = [{'requested': k, 'selected': v, 'config_path': '.apgr/config.toml',
                             'config_sha256': digest(config.encode())}
                            for k, v in sorted(row.get('overrides', {}).items())]
    return catalog, {'source': 'synthetic', 'whole_bytes': len(raw), 'whole_sha256': digest(raw),
                     'body_bytes': len(body), 'body_sha256': digest(body)}


def native(binary, args, request):
    result = subprocess.run([str(binary), *args], input=encoded(request),
                            capture_output=True, timeout=30, check=True)
    return json.loads(result.stdout)


def planner_observation(root, binary, row, catalog):
    """Use repository facts, not expected selections, to probe unchanged policy."""
    provider_file = {'codex': 'codex/AGENTS.md', 'claude': 'claude/CLAUDE.md',
                     'antigravity': 'antigravity/GEMINI.md'}[row['provider']]
    standing = (root / provider_file).read_bytes()
    # This is explicitly a synthetic envelope, never an initial-delivery total.
    task = '\n<fixture-task>\n' + json.dumps(row['task_input'], sort_keys=True) + '\n</fixture-task>\n'
    roles = '\n<fixture-roles>\n' + json.dumps(row['role_binding'], sort_keys=True) + '\n</fixture-roles>\n'
    facts = [{'kind': 'language', 'value': row['repository_evidence']['primary_language']}]
    request = {'schema_version': 'apg.context-plan/v1', 'run_id': 'h-mechanism',
               'binding_id': row['role_binding']['binding_id'], 'attempt_id': 'one',
               'roles': row['role_binding']['roles'], 'consumer': 'go_library',
               'requested_mode': 'adaptive', 'catalog': catalog, 'facts': facts,
               'mandatory': [{'id': 'standing', 'kind': 'standing', 'text': standing.decode(),
                              'source_path': provider_file, 'source_sha256': digest(standing)},
                             {'id': 'task', 'kind': 'synthetic-fixture-envelope', 'text': task},
                             {'id': 'roles', 'kind': 'synthetic-fixture-envelope', 'text': roles}],
               'budget': {'max_initial_context_bytes': row.get('budget', {}).get('max_initial_controlled_bytes')},
               'qualification': {}}
    plan = native(binary, ['skills', 'plan', '--stdin'], request)
    repeated = native(binary, ['skills', 'plan', '--stdin'], request)
    if plan != repeated:
        raise ValueError('non-reproducible plan')
    return {'source': 'measured', 'scope': 'prospective planner only; synthetic task/role envelope',
            'request_sha256': digest(encoded(request)),
            'components': [{'id': c['id'], 'source': 'synthetic' if c['kind'] == 'synthetic-fixture-envelope' else 'measured',
                            'bytes': len(c['text'].encode()), 'sha256': digest(c['text'].encode())} for c in request['mandatory']],
            'facts': facts, 'effective_mode': plan['effective_mode'], 'reasons': plan['reasons'],
            'rule_version': plan['rule_version'], 'content_identity': plan['content_identity'],
            'mandatory_cost': plan['mandatory_cost'], 'payload_cost': plan['payload_cost'],
            'selected': [s['qualified_id'] for s in plan['selected_snapshots']], 'reproducible': True}


def collect(root, binary, seal, subjects):
    verify_seal(root, binary, seal)
    subjects.mkdir(exist_ok=False)
    rows = []
    for scenario in scenarios(root):
        sid = scenario['scenario_id']
        subject = subjects / sid
        subject.mkdir()
        catalog, synthetic = synthetic_catalog(scenario, subject)
        reason = 'No repository-owned qualified live paired provider harness; subject task output unavailable'
        arms = {}
        for arm in ('static', 'adaptive'):
            arms[arm] = {'route': seal['routes'][sid][arm],
                         'initial': unavailable(reason), 'cumulative': unavailable(reason),
                         'deliveries': [], 'coverage': unavailable('no live channel trace'),
                         'task_outcome': unavailable(reason), 'quality_oracle': scenario['expected_outcome']['quality_oracle'],
                         'retries': unavailable(reason), 'producer_revisions': unavailable(reason),
                         'missing_guidance_findings': unavailable(reason),
                         'restart_required_incidents': unavailable(reason),
                         'authority': unavailable(reason), 'exact_recovery': unavailable(reason),
                         'late_acquisitions': unavailable(reason), 'provider_native_bytes': unavailable(reason),
                         'tokens': unavailable('no direct provider token counter')}
        rows.append({'scenario_id': sid, 'subset': scenario['subset'], 'synthetic_inputs': bool(scenario.get('synthetic_inputs')),
                     'synthetic_materialization': synthetic, 'arms': arms,
                     'mechanism': planner_observation(root, binary, scenario, catalog)})
    verify_seal(root, binary, seal)
    return {'schema_version': SCHEMA, 'seal_sha256': digest(encoded(seal)), 'boundary': BOUNDARY,
            'scenario15': 'contingent/unavailable', 'rows': rows}


def delivered_totals(deliveries):
    """Count one observation per transmission; repeat transmissions have new IDs.

    A single transmission may have multiple accounting views with the same ID.
    Conflicting views are invalid rather than chosen silently. Materialization
    and preflight records are never supplied as provider transmissions.
    """
    seen = {}
    for event in deliveries:
        if set(event) != {'id', 'phase', 'bytes', 'sha256', 'channel', 'source'}:
            raise ValueError('invalid delivery shape')
        if event['source'] != 'measured' or event['phase'] not in ('initial', 'late'):
            raise ValueError('unmeasured delivery')
        if type(event['bytes']) is not int or event['bytes'] < 0 or not event['id']:
            raise ValueError('invalid delivery bytes or identity')
        if len(event['sha256']) != 64 or any(c not in '0123456789abcdef' for c in event['sha256']):
            raise ValueError('invalid payload digest')
        if event['channel'] not in ('prompt', 'instructions', 'mcp_configuration', 'mcp', 'cli', 'recovery_read'):
            raise ValueError('invalid delivery channel')
        if event['id'] in seen and seen[event['id']] != event:
            raise ValueError('conflicting delivery views')
        seen[event['id']] = event
    return (sum(e['bytes'] for e in seen.values() if e['phase'] == 'initial'),
            sum(e['bytes'] for e in seen.values()))


def p95(values):
    if not values or not all(math.isfinite(v) for v in values):
        raise ValueError('finite nonempty observations required')
    return sorted(values)[math.ceil(.95 * len(values)) - 1]


def measured_pair(row):
    a, s = row['arms']['adaptive'], row['arms']['static']
    routes = [{k: v for k, v in arm['route'].items() if k != 'requested_context_mode'} for arm in (a, s)]
    if routes[0] != routes[1]:
        raise ValueError('paired route mismatch')
    values = []
    for arm in (a, s):
        if any(arm[k]['source'] != 'measured' for k in ('initial', 'cumulative', 'coverage')):
            return None
        if arm['coverage']['value'] != 'complete':
            return None
        if (arm['route']['model_route'].get('source') != 'measured' or not arm['route']['model_route'].get('value')
                or arm['route']['execution'] != 'live'):
            raise ValueError('live route evidence required')
        if any(type(arm[k]['value']) is not int or arm[k]['value'] < 0 for k in ('initial', 'cumulative')):
            raise ValueError('invalid measured total')
        totals = delivered_totals(arm['deliveries'])
        if totals != (arm['initial']['value'], arm['cumulative']['value']):
            raise ValueError('delivery totals mismatch')
        values.append(totals)
    (ai, ac), (si, sc) = values
    if si <= 0 or sc <= 0:
        raise ValueError('strictly positive static denominators required')
    return 1 - ai / si, ac / sc - 1


def aggregate(raw, metrics):
    if raw['schema_version'] != SCHEMA or raw['boundary'] != BOUNDARY:
        raise ValueError('unsupported results boundary')
    expected = metrics['cohorts']['calibration_cohort'] + metrics['cohorts']['acceptance_cohort']
    rows = raw['rows']
    if len(rows) != len(expected) or {r['scenario_id'] for r in rows} != set(expected):
        raise ValueError('missing or duplicate scenario')
    by_id = {r['scenario_id']: r for r in rows}
    for row in rows:
        if set(row['arms']) != {'static', 'adaptive'}:
            raise ValueError('missing pair member')
        if row['synthetic_inputs'] != (row['scenario_id'] in ('scenario-08', 'scenario-09')):
            raise ValueError('synthetic cohort changed')
    eligible = list(metrics['cohorts']['savings_eligible_cohort'])
    contingent = raw['scenario15'] == 'contingent/unavailable'
    if contingent:
        eligible.remove('scenario-15')
    elif raw['scenario15'] != 'qualified':
        raise ValueError('invalid Scenario 15 disposition')
    else:
        for arm in by_id['scenario-15']['arms'].values():
            proof = arm.get('selective_discovery', {})
            if proof.get('source') != 'measured' or proof.get('value') != 'qualified-no-leakage-settings-unchanged':
                raise ValueError('Scenario 15 live contingency evidence required')
    output = {}
    for name, cohort in (('full_applicable', eligible), ('non_synthetic', [s for s in eligible if s not in ('scenario-08', 'scenario-09')])):
        observations, missing = [], []
        for sid in cohort:
            value = measured_pair(by_id[sid])
            if value is None:
                missing.append(sid)
            else:
                observations.append(value)
        savings = statistics.median(v[0] for v in observations) if observations else None
        growth = p95([v[1] for v in observations]) if observations else None
        output[name] = {'expected_n': len(cohort), 'measured_n': len(observations), 'missing': missing,
                        'median_savings': savings, 'nearest_rank_p95_growth': growth,
                        'small_sample': 'p95 is the maximum for n <= 6; not a population guarantee',
                        'pass': not missing and bool(observations) and savings >= .20 and growth <= .10}
    acceptance = [by_id[s] for s in metrics['cohorts']['acceptance_cohort']]
    quality = all(a['task_outcome'].get('source') == 'measured' and a['task_outcome'].get('value') == 'pass'
                  and a['authority'].get('source') == 'measured' and a['authority'].get('value') == 'preserved'
                  for r in acceptance for a in r['arms'].values())
    recovery = all(a['exact_recovery'].get('source') == 'measured' and a['exact_recovery'].get('value') is True
                   for s in ('scenario-10', 'scenario-11', 'scenario-12', 'scenario-14') for a in by_id[s]['arms'].values())
    return {'schema_version': 'apg.h-aggregate/v1', 'raw_sha256': digest(encoded(raw)),
            **output, 'scenario15': raw['scenario15'], 'quality_and_authority_pass': quality,
            'exact_recovery_pass': recovery,
            'benefit_gate_pass': not contingent and quality and recovery and all(r['pass'] for r in output.values()),
            'qualified_promotions': 0, 'default_recommendation': 'retain_static',
            'maturity_gate': 'not_met; independent skill evidence and dispatcher review required'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('seal', 'collect', 'aggregate'))
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--binary', type=Path)
    parser.add_argument('--seal', type=Path)
    parser.add_argument('--raw', type=Path)
    parser.add_argument('--subjects', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.action == 'seal':
        result = make_seal(root, args.binary.resolve())
    elif args.action == 'collect':
        result = collect(root, args.binary.resolve(), load(args.seal), args.subjects)
    else:
        result = aggregate(load(args.raw), load(root / CORPUS / 'context-eval-metrics-and-oracles.json'))
    with args.output.open('xb') as stream:
        stream.write(encoded(result))


if __name__ == '__main__':
    main()
