#!/usr/bin/env python3
"""Portable, exclusive final provider-free B8 transaction and package seal."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
for relative in ('', 'src', 'src/test/dispatcher', 'libexec'):
    sys.path.insert(0, str(REPO_ROOT / relative))
from testing.h_eval import dry_run, provider_free_readiness, runtime_manifest as rm
from testing.h_eval import qualification_receipts as receipts


def run_transaction(qualification_dir, previous_manifest, *, root=REPO_ROOT):
    """Run exactly one provider-free transaction and seal its package evidence."""
    out = receipts.new_attempt(Path(qualification_dir).resolve(), 'final-b8')
    manifest_path = Path(previous_manifest)
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    receipts.write_json(out / 'runtime-input.json', {'path': str(manifest_path.resolve()),
                        'sha256': receipts.digest(manifest_bytes), 'manifest_digest': rm.manifest_digest(manifest)})
    rm.verify(manifest, probe_versions=True)
    target = out / 'transaction'
    result = dry_run.dry_run_all(root, target, runtime_manifest=manifest)
    seal = provider_free_readiness.make_package_seal(root, target)
    receipts.write_json(out / 'seal.json', seal)
    receipts.write_json(out / 'summary.json', result)
    accepted = (seal['provider_free_mechanical_candidate'] and result['complete_records'] == 15
                and result['initial_trees_equal'] == 15 and result['subject_pairs_unchanged'] == 15
                and result['promotion_oracle_fixtures']['fixture_pairs'] == 25
                and result['provider_invocations'] == 0 and result['aggregate_written'] is False)
    return {'output': str(out), 'transaction': str(target), 'accepted': accepted,
            'gates': seal['gates'], 'seal': seal, 'summary': result}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--qualification-dir', type=Path, required=True)
    parser.add_argument('--previous-manifest', type=Path, required=True,
                        help='Retained runtime input; revalidated before use, never treated as source acceptance')
    args = parser.parse_args()
    outcome = run_transaction(args.qualification_dir, args.previous_manifest)
    print(json.dumps({'output': outcome['output'], 'accepted': outcome['accepted'], 'gates': outcome['gates']}))
    return 0 if outcome['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
