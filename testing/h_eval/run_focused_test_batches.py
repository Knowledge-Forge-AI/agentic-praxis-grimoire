#!/usr/bin/env python3
"""Run provider-free batches with exact node outcomes and immutable attempts."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
from testing.h_eval import qualification_receipts as receipts

FOCUSED = ('h_d1_seam', 'h_claude_reads', 'h_delivery', 'h_arm_evidence_qual6',
           'h_promotion_qual6', 'h_provider_free_guard', 'h_provider_free_readiness')
SEPARATE = ('h_runtime_complete', 'agent_phase_provider_stream', 'h_qualification_receipts')


def _terminal_outcome(row: dict) -> str:
    # An xfail marker without a reason records wasxfail == ''; only None means
    # the report carried no xfail marker.
    if row['strict_xpass']:
        return 'xpassed'
    if row['wasxfail'] is not None:
        return 'xfailed' if row['outcome'] == 'skipped' else 'xpassed'
    return row['outcome']


def summarize(events: dict, exit_code: int) -> tuple[list, dict, bool]:
    nodes = events['collected_nodeids']
    cases = []
    for node in nodes:
        rows = [r for r in events['reports'] if r['nodeid'] == node]
        errors = [r for r in rows if r['when'] != 'call' and r['outcome'] == 'failed']
        terminal = [r for r in rows if r['when'] == 'call' or r['outcome'] == 'skipped']
        outcome = 'errors' if errors else 'incomplete'
        if not errors and len(terminal) == 1:
            outcome = _terminal_outcome(terminal[0])
        cases.append({'nodeid': node, 'outcome': outcome})
    # Pytest counts phase outcomes: a failed call and failed teardown are both
    # observable, so their sum may exceed collected node IDs.
    counts = {key: 0 for key in ('passed', 'failed', 'skipped', 'xfailed', 'xpassed', 'errors', 'incomplete')}
    for row in events['reports']:
        if row['when'] != 'call' and row['outcome'] == 'failed':
            counts['errors'] += 1
        elif row['when'] == 'call' or row['outcome'] == 'skipped':
            counts[_terminal_outcome(row)] += 1
    counts['incomplete'] = sum(c['outcome'] == 'incomplete' for c in cases)
    counts['errors'] += len(events['collection_errors']) + len(events.get('internal_errors', []))
    counts['collected'] = len(nodes)
    complete = (len(nodes) == len(set(nodes)) and counts['incomplete'] == 0
                and events['exit_code'] == exit_code
                and {r['nodeid'] for r in events['reports']} <= set(nodes)
                and all(sum(r['nodeid'] == node and r['when'] == phase for r in events['reports']) == 1
                        for node in nodes for phase in ('setup', 'teardown')))
    if exit_code == 0:
        complete = complete and not (counts['failed'] or counts['errors']) and bool(nodes)
        complete = complete and not any(r['strict_xpass'] for r in events['reports'])
    elif exit_code == 1:
        complete = complete and bool(counts['failed'] or counts['errors'] or any(r['strict_xpass'] for r in events['reports']))
    elif exit_code == 3:
        complete = complete and bool(events.get('internal_errors'))
    return cases, counts, complete


def run_batch(name: str, parent: Path) -> dict:
    attempt = receipts.new_attempt(parent, name)
    target = f'src/test/dispatcher/test_{name}.py'
    env = dict(os.environ)
    env['PYTHONPATH'] = os.pathsep.join([str(REPO_ROOT), str(REPO_ROOT / 'libexec'), str(REPO_ROOT / 'src'), str(REPO_ROOT / 'src/test/dispatcher'), env.get('PYTHONPATH', '')])
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['APG_PYTEST_RECEIPT'] = str(attempt / 'pytest-events.json')
    argv = [sys.executable, '-m', 'pytest', '-p', 'no:cacheprovider', '-p',
            'testing.h_eval.pytest_receipt_plugin', '-q', '--tb=short', target]
    command = receipts.run_command(argv, attempt, env=env)
    events = json.loads((attempt / 'pytest-events.json').read_bytes())
    cases, counts, complete = summarize(events, command['exit_code'])
    value = {'schema': 'apg.test-batch-receipt/v2', 'attempt_id': attempt.name,
             'suite_id': name, 'target_paths': [target],
             'overlap_group': 'focused' if name in FOCUSED else 'separate-regression',
             'included_in_canonical_unique_aggregate': name in FOCUSED,
             'command_receipt': 'command.json', 'command_sha256': receipts.digest((attempt / 'command.json').read_bytes()),
             'events_sha256': receipts.digest((attempt / 'pytest-events.json').read_bytes()),
             'source_identity': command['source_identity'], 'count_basis': 'pytest phase outcomes; totals can exceed collected nodes', 'summary': counts, 'test_cases': cases,
             'receipt_complete': complete, 'passed': complete and command['exit_code'] == 0 and command['source_unchanged']}
    receipts.write_json(attempt / 'batch.json', value)
    print(f'{name}: {counts}; pass={value["passed"]}', flush=True)
    return value


def reconcile(selected: list[dict], parent: Path) -> dict:
    included = [r for r in selected if r['included_in_canonical_unique_aggregate']]
    nodes = sorted({c['nodeid'] for r in included for c in r['test_cases']})
    attempts = {r['suite_id']: {'selected': r['attempt_id'],
                'superseded': sorted(p.parent.name for p in parent.glob(r['suite_id'] + '-*/batch.json')
                                     if p.parent.name != r['attempt_id'])} for r in selected}
    value = {'schema': 'apg.focused-test-reconciliation/v2', 'selected_attempts': attempts,
             'canonical_focused_case_count': len(nodes), 'unique_nodeids': nodes,
             'all_selected_passed': bool(selected) and all(r['passed'] for r in selected),
             'required_suite_coverage': sorted(r['suite_id'] for r in selected) == sorted(FOCUSED + SEPARATE),
             'same_candidate': len({r['source_identity']['candidate_sha256'] for r in selected}) == 1}
    # Only one invocation that selects every required suite, on one candidate,
    # with every selected attempt passing can claim covering qualification.
    value['covering_qualification'] = (value['all_selected_passed'] and value['same_candidate']
                                       and value['required_suite_coverage'])
    value['historical_statement'] = (
        f'188 was a historical unreconciled aggregate; this reconciliation derives {len(nodes)} unique focused '
        'node IDs from its selected receipts. Any prior-to-current count relation requires node_set_delta.')
    return value


def _node_ids(label: str, value) -> list:
    ids = value.get('unique_nodeids') if isinstance(value, dict) else None
    if not isinstance(ids, list) or not all(isinstance(node, str) for node in ids):
        raise ValueError(f'{label} reconciliation has no unique_nodeids list')
    return ids


def node_set_delta(prior: dict, current: dict) -> dict:
    """Compare two reconciliations' focused node IDs as exact sets."""
    before, after = _node_ids('prior', prior), _node_ids('current', current)
    old, new = set(before), set(after)
    added, removed, unchanged = sorted(new - old), sorted(old - new), sorted(old & new)
    consistent = {label: len(ids) == len(set(ids)) and ids == sorted(ids)
                  and value.get('canonical_focused_case_count') == len(ids)
                  for label, ids, value in (('prior', before, prior), ('current', after, current))}
    holds = (old - set(removed)) | set(added) == new and len(new) == len(old) - len(removed) + len(added)
    return {'schema': 'apg.focused-node-set-delta/v1',
            'prior_count': len(old), 'current_count': len(new),
            'added': added, 'removed': removed, 'unchanged': unchanged,
            'added_count': len(added), 'removed_count': len(removed), 'unchanged_count': len(unchanged),
            'set_equation': 'current = (prior - removed) | added',
            'count_equation': f'{len(old)} - {len(removed)} + {len(added)} = {len(new)}',
            'pure_addition': not removed,
            'inputs_consistent': consistent,
            'valid': holds and all(consistent.values())}


def _read_reconciliation(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'reconciliation must be a regular non-symlink file: {path}')
    return json.loads(path.read_bytes())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--qualification-dir', type=Path)
    parser.add_argument('--suite', choices=FOCUSED + SEPARATE, action='append')
    parser.add_argument('--compare', nargs=2, type=Path, metavar=('PRIOR', 'CURRENT'),
                        help='print the exact node-set delta between two reconciliation.json files')
    args = parser.parse_args()
    if args.compare:
        if args.suite:
            parser.error('--compare runs no suites')
        delta = node_set_delta(*(_read_reconciliation(path) for path in args.compare))
        if args.qualification_dir:
            out = receipts.new_attempt(args.qualification_dir.resolve(), 'node-set-delta')
            receipts.write_json(out / 'node-set-delta.json',
                                dict(delta, inputs={label: {'path': str(path), 'sha256': receipts.digest(path.read_bytes())}
                                                    for label, path in zip(('prior', 'current'), args.compare)}))
        print(json.dumps({key: delta[key] for key in ('prior_count', 'current_count', 'added_count',
                          'removed_count', 'unchanged_count', 'count_equation', 'valid')}, sort_keys=True))
        return 0 if delta['valid'] else 1
    if not args.qualification_dir:
        parser.error('--qualification-dir is required')
    parent = args.qualification_dir.resolve() / 'test-batch-receipts'
    selected = [run_batch(name, parent) for name in (args.suite or FOCUSED + SEPARATE)]
    value = reconcile(selected, parent)
    out = receipts.new_attempt(args.qualification_dir.resolve(), 'reconciliation')
    receipts.write_json(out / 'reconciliation.json', value)
    return 0 if value['covering_qualification'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
