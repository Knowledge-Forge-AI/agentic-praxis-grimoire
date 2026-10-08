#!/usr/bin/env python3
"""Compare alias and physical paths using the preregistered SQLite oracle."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / 'libexec'))
from testing.h_eval import promotion_oracles as po
from testing.h_eval import qualification_receipts as receipts


def oracle_receipt() -> dict:
    prereg = json.loads((REPO_ROOT / 'testing/h_eval/promotion-preregistration.json').read_bytes())['oracle_source']
    files = {name: {'sha256': receipts.digest((REPO_ROOT / name).read_bytes()),
                    'bytes': (REPO_ROOT / name).stat().st_size} for name in po.SOURCE_PATHS}
    combined = po.source_sha256(REPO_ROOT)
    return {'source_paths': list(po.SOURCE_PATHS), 'files': files, 'sha256': combined,
            'preregistration': prereg,
            'oracle_sha256_matches_preregistration': combined == prereg['sha256'] and list(po.SOURCE_PATHS) == prereg['paths']}


def inventory(directory: Path) -> dict:
    """Complete physical fixture inventory; symlinks are recorded, never followed."""
    physical = directory.resolve()
    entries = {}
    for dirpath, dirnames, filenames in os.walk(physical, followlinks=False):
        for name in sorted(dirnames + filenames):
            path = Path(dirpath) / name
            relative = str(path.relative_to(physical))
            if path.is_symlink():
                entries[relative] = {'type': 'symlink', 'target': os.readlink(path)}
            elif path.is_dir():
                entries[relative] = {'type': 'directory'}
            else:
                data = path.read_bytes()
                entries[relative] = {'type': 'file', 'sha256': receipts.digest(data), 'bytes': len(data)}
    return entries


def vector(label: str, cwd: Path, env: dict, out: Path, spec) -> dict:
    argv = [sys.executable, *spec.command[1:]]
    executable = Path(sys.executable).resolve()
    before = {name: {'sha256': receipts.digest((cwd / name).read_bytes()), 'bytes': (cwd / name).stat().st_size}
              for name in spec.good_files}
    inventory_before = inventory(cwd)
    run = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, timeout=30)
    inventory_after = inventory(cwd)
    for name, data in [('stdout', run.stdout), ('stderr', run.stderr)]:
        with (out / (label + '.' + name)).open('xb') as stream:
            stream.write(data)
    record = {'command': argv, 'cwd': str(cwd), 'physical_cwd': str(cwd.resolve()),
              'environment': env, 'fixture_files': before, 'oracle': oracle_receipt(),
              'fixture_inventory_before': inventory_before, 'fixture_inventory_after': inventory_after,
              'executable': str(executable), 'executable_sha256': receipts.digest(executable.read_bytes()),
              'version': subprocess.check_output([sys.executable, '--version'], env=env, text=True).strip(),
              'exit_code': run.returncode, 'failure_observed': b'AssertionError' in run.stderr,
              'stdout_sha256': receipts.digest(run.stdout), 'stderr_sha256': receipts.digest(run.stderr)}
    receipts.write_json(out / (label + '.json'), record)
    return record


def compare(baseline: dict, canonical: dict) -> dict:
    constant = ('executable', 'executable_sha256', 'version', 'fixture_files', 'oracle', 'command')
    predicates = {key + '_same': baseline[key] == canonical[key] for key in constant}
    env = lambda r: {k: v for k, v in r['environment'].items() if k not in ('TMPDIR', 'PWD')}
    predicates['environment_same_except_declared_paths'] = env(baseline) == env(canonical)
    predicates['oracle_preregistration_match'] = all(r['oracle']['oracle_sha256_matches_preregistration'] for r in (baseline, canonical))
    # Both vectors share one physical fixture: baseline must leave no residue
    # and the canonicalized vector must start from the baseline's initial state.
    predicates['baseline_left_no_fixture_residue'] = baseline['fixture_inventory_before'] == baseline['fixture_inventory_after']
    predicates['canonical_started_from_baseline_initial_state'] = canonical['fixture_inventory_before'] == baseline['fixture_inventory_before']
    predicates['canonical_left_no_fixture_residue'] = canonical['fixture_inventory_before'] == canonical['fixture_inventory_after']
    controlled = all(predicates.values())
    paths = (baseline['cwd'] != baseline['physical_cwd'] and canonical['cwd'] == canonical['physical_cwd']
             and baseline['physical_cwd'] == canonical['physical_cwd']
             and all(r['environment']['PWD'] == r['cwd'] and r['environment']['TMPDIR'] == r['cwd'] for r in (baseline, canonical)))
    predicates.update(baseline_path_uncanonicalized=baseline['cwd'] != baseline['physical_cwd'],
                      canonicalized_path_physical=canonical['cwd'] == canonical['physical_cwd'],
                      baseline_failure_observed=baseline['exit_code'] != 0 and baseline['failure_observed'],
                      canonical_success_observed=canonical['exit_code'] == 0 and not canonical['failure_observed'])
    passed = controlled and paths and all(predicates.values())
    return {'schema': 'apg.h-causal-proof-comparison/v2', 'predicates': predicates,
            'controlled_factors_equal': controlled, 'only_declared_path_variable_changed': controlled and paths,
            'causal_proof_passed': passed,
            'conclusion': 'Observed path canonicalization explains this controlled fixture result.' if passed else 'Causal conclusion not established.'}


def run_proof(out: Path) -> dict:
    spec = po.spec_for('sqlite-database-profile/positive/writer-wal')
    physical = out / 'fixture'
    physical.mkdir(mode=0o700)
    alias = out / 'alias'
    alias.symlink_to(physical, target_is_directory=True)
    for name, content in spec.good_files.items():
        (physical / name).write_text(content, encoding='utf-8')
    base = {'PATH': '/usr/bin:/bin', 'HOME': str(out), 'LANG': 'C', 'LC_ALL': 'C',
            'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1'}
    vector('baseline', alias, dict(base, TMPDIR=str(alias), PWD=str(alias)), out, spec)
    vector('canonicalized', physical, dict(base, TMPDIR=str(physical), PWD=str(physical)), out, spec)
    # Derive comparison from retained artifacts, not intended run values.
    baseline = json.loads((out / 'baseline.json').read_bytes())
    canonical = json.loads((out / 'canonicalized.json').read_bytes())
    comparison = compare(baseline, canonical)
    receipts.write_json(out / 'fixture-oracle-digest-receipt.json', baseline['oracle'])
    receipts.write_json(out / 'comparison.json', comparison)
    return comparison


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--qualification-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    out = args.output_dir.resolve() if args.output_dir else receipts.new_attempt(args.qualification_dir.resolve(), 'sqlite-proof')
    if args.output_dir:
        out.mkdir(mode=0o700)
    result = run_proof(out)
    print(json.dumps(result, indent=2))
    return 0 if result['causal_proof_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
