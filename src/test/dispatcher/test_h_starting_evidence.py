"""CORR5 real starting pytest subprocess/capture/cleanup and durable readback."""
import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from testing.h_eval import hidden_execution, preregistration, promotion_oracles as oracle, starting_evidence
from test_h_promotion_corr3 import CASES, ROOT

PYTEST_CASES = [c for c in CASES.values() if c['case_id'].startswith('pytest-test-profile/positive/')]


def durable_starting(tmp_path, monkeypatch):
    """Replace sealed-runtime admission only; run actual commands and cleanup."""
    manifest = {'runtimes': {'python3': {'version_stdout': sys.version}, 'pytest': {}},
                'files': {sys.executable: {'physical_path': sys.executable}}}
    manifest['runtimes']['python3']['executable'] = sys.executable

    class Transaction:
        def resolve(self, _name):
            return sys.executable

        def revalidate(self):
            return manifest

        def close(self):
            return manifest

        def run(self, name, arguments, *, cwd, temp_root, **kwargs):
            assert name == 'python3'
            return subprocess.run([sys.executable, *arguments], cwd=cwd,
                                  env=oracle._closed_environment(cwd, Path(sys.executable), 'python'),
                                  capture_output=True, **kwargs)

    monkeypatch.setattr(oracle, '_verify_complete_runtime', lambda _: None)
    monkeypatch.setattr(oracle.runtime_execution, 'begin', lambda *a, **k: Transaction())
    monkeypatch.setattr(oracle, 'case_ids', lambda: ())  # Only the changed starting boundary.
    inventory = preregistration.expected_oracle_inventory(preregistration.verify_promotions(ROOT))
    result = oracle.qualify_all(manifest, tmp_path / 'durable', expected_inventory=inventory,
                               starting_subject_cases=PYTEST_CASES)
    return result, manifest


def test_starting_capture_precedes_cleanup_and_survives_in_retained_evidence(tmp_path, monkeypatch):
    result, manifest = durable_starting(tmp_path, monkeypatch)
    retained = json.loads((tmp_path / 'durable/qualification.json').read_text())
    assert retained == result
    assert not list((tmp_path / 'durable/starting-evaluation').rglob('*.py'))
    assert not list((tmp_path / 'durable/starting-evaluation').rglob('apg*execution.json'))
    assert not [p for p in (tmp_path / 'durable/starting-evaluation').rglob('*')
                if p.is_dir() and p.name.isdigit()]
    assert not (tmp_path / 'durable/tmp').exists()
    attestations = starting_evidence.verify_all(retained, PYTEST_CASES, manifest)
    assert len(attestations) == 3
    for row, attestation in zip(retained['starting_subjects'], attestations):
        assert row['status'] == 'fail' and row['starting_failure_required']
        assert row['hidden_oracle']['status'] == 'pass'
        assert row['model_authored_tests']['status'] == 'fail'
        assert attestation['qualifying'] and attestation['runner_version'] == pytest.__version__
        assert attestation['runtime_version'] == pytest.__version__
        assert attestation['expected_identities']
        assert all(attestation['observed_statuses'][n] == [
            'collected', 'started', 'setup:passed', 'call:passed', 'teardown:passed']
            for n in attestation['expected_identities'])


def test_absent_capture_cannot_qualify_starting_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(hidden_execution, 'capture', lambda *args: None)
    with pytest.raises(ValueError, match='status changed|artifact/attestation invalid'):
        durable_starting(tmp_path, monkeypatch)
    assert not (tmp_path / 'durable/qualification.json').exists()
    assert not list((tmp_path / 'durable/starting-evaluation').rglob('*.py'))


@pytest.mark.parametrize('mutation', ['missing', 'malformed', 'oversized', 'tampered', 'expected',
    'copied-status', 'classification', 'subject', 'command', 'runtime', 'authored-status'])
def test_retained_starting_evidence_recomputes_not_copied_status(tmp_path, monkeypatch, mutation):
    result, manifest = durable_starting(tmp_path, monkeypatch)
    value = copy.deepcopy(result)
    row = value['starting_subjects'][0]
    hidden = row['hidden_oracle']
    if mutation == 'missing':
        del hidden['hidden_execution_artifact']
    elif mutation in {'malformed', 'oversized', 'copied-status'}:
        hidden['hidden_execution_artifact'] = ('x' * (hidden_execution.MAX_REPORT_BYTES + 1)
                                               if mutation == 'oversized' else '{}')
        hidden['execution_attestation']['qualifying'] = True
    elif mutation == 'tampered':
        hidden['hidden_execution_artifact'] = hidden['hidden_execution_artifact'].replace('call:passed', 'call:skipped')
    elif mutation == 'expected':
        hidden['execution_attestation']['expected_identities'] = ['forged']
    elif mutation == 'classification':
        row['status'] = 'pass'
    elif mutation == 'subject':
        hidden['grading_custody']['candidate_before']['values.py'] = '0' * 64
    elif mutation == 'command':
        hidden['command'].append('-k=none')
    elif mutation == 'runtime':
        hidden['runtime_version'] = 'forged'
    else:
        row['model_authored_tests']['status'] = 'pass'
    with pytest.raises(ValueError):
        starting_evidence.verify_all(value, PYTEST_CASES, manifest)


@pytest.mark.parametrize('mutation', ['artifact', 'missing', 'copied-status'])
def test_dry_run_readback_rejects_invalid_starting_artifact_even_with_refreshed_inventory(tmp_path, monkeypatch, mutation):
    from testing.h_eval import provider_free_readiness as readiness
    from testing.h_eval.provider_free import LaunchGuard
    evidence, manifest = durable_starting(tmp_path, monkeypatch)
    directory = tmp_path / 'readback'
    directory.mkdir(mode=0o700)
    with LaunchGuard(directory / 'provider-guard') as guard:
        receipt = guard.assert_clean()
    rows = [{'scenario_id': f'scenario-{n:02d}'} for n in range(1, 16)]
    for row in rows:
        target = directory / 'records' / row['scenario_id']
        target.mkdir(parents=True)
        (target / 'dry-run.json').write_text(json.dumps(row))
    result = {'records': rows, 'provider_guard': receipt, 'aggregate_written': False,
              'promotion_oracle_fixtures': evidence}
    (directory / 'promotion-oracle-fixtures').mkdir()
    (directory / 'runtime-manifest.json').write_text(json.dumps(manifest))

    def retain():
        (directory / 'dry-run.json').write_text(json.dumps(result))
        (directory / 'promotion-oracle-fixtures/qualification.json').write_text(json.dumps(evidence))
        (directory / 'integrity.json').unlink(missing_ok=True)
        readiness.retain_integrity(directory)

    retain()
    assert readiness.read_dry_run(directory) == result
    hidden = evidence['starting_subjects'][0]['hidden_oracle']
    if mutation == 'missing':
        del hidden['hidden_execution_artifact']
    else:
        hidden['hidden_execution_artifact'] = '{}'
        if mutation == 'copied-status':
            hidden['execution_attestation']['qualifying'] = True
    retain()
    with pytest.raises(ValueError, match='starting'):
        readiness.read_dry_run(directory)
