"""Adverse manager-receipt cases across real sealed Git candidates."""
import json
from pathlib import Path

import pytest

from agent_phase import gitstate, ownership_cli
from agent_phase.finalization_proof import RecoveryError
from agent_phase.finalization_recovery import recover
from test_agent_phase_disposition_flow import PHASE_ID, REQUEST, make_dispatcher, repository as _repository, git
from test_agent_phase_path_dispositions import OwnershipRunner, track

repository = _repository


def source_with_challenges(repository, tmp_path, count=1, dirty=False):
    if dirty:
        (repository / 'README.md').write_text('original operator dirt\n')
        names = ['README.md']
    else:
        names = [f'deleted-{i}.txt' for i in range(count)]
        for name in names:
            track(repository, name, symlink=False)

    def terminal(cwd, prompt):
        for name in names:
            if dirty:
                (cwd / name).write_text('exact phase overwrite\n')
            else:
                (cwd / name).unlink()
        (cwd / 'product.txt').write_text('exact product\n')

    runner = OwnershipRunner(hooks={4: terminal})
    state = make_dispatcher(repository, tmp_path / 'runs', runner).dispatch(
        PHASE_ID, REQUEST, finalization_policy='checkpoint')
    assert state['semantic_outcome'] == 'completed'
    assert state['finalization_outcome'] == 'blocked'
    assert len(runner.calls) == 5
    return Path(state['run_directory']), state


def resolution(repository, source, state, output, decision='phase_owned', index=0):
    record = ownership_cli.create(source, repository,
        state['ownership_challenges']['records'][index]['challenge_id'], decision,
        'Manager accepts this exact path and sealed candidate')
    ownership_cli._write_create_only(output, record)
    return output


def finalize(source, repository, receipts):
    return recover(source, repository, policy='commit-local',
                   authorize_policy_upgrade=True, ownership_resolutions=receipts)


def test_twice_resumed_challenge_retains_exact_archived_origin(repository, tmp_path):
    target = track(repository, 'deleted.txt', symlink=False)
    state = make_dispatcher(repository, tmp_path / 'source', OwnershipRunner(
        hooks={2: lambda cwd, prompt: target.unlink()})).dispatch(
            PHASE_ID, REQUEST, finalization_policy='checkpoint')
    original = state['ownership_challenges']['records'][0]
    for index in range(2):
        runner = OwnershipRunner()
        state = make_dispatcher(repository, tmp_path / f'resume-{index}', runner).resume(
            PHASE_ID, REQUEST, Path(state['run_directory']), 'closeout',
            finalization_policy='checkpoint')
        assert state['ownership_challenges']['records'] == [original]
        assert original['challenge_id'].encode() in runner.calls[0]['prompt']
        assert state['finalization_outcome'] == 'blocked'
    source = Path(state['run_directory'])
    output = resolution(repository, source, state, tmp_path / 'resumed-resolution.json')
    assert finalize(source, repository, [output])['finalization']['outcome'] == 'completed'


def test_resolution_rejects_inconsistent_manager_identity_and_redirected_git(repository, tmp_path, monkeypatch):
    source, state = source_with_challenges(repository, tmp_path)
    cid = state['ownership_challenges']['records'][0]['challenge_id']
    receipt = ownership_cli.create(source, repository, cid, 'phase_owned', 'exact grant')
    receipt['manager_authority']['controller_generation'] = {'different': True}
    receipt['sha256'] = ownership_cli.digest(ownership_cli._record_without_digest(receipt))
    with pytest.raises(ownership_cli.OwnershipResolutionError):
        ownership_cli.validate_receipt(receipt)
    monkeypatch.setenv('GIT_INDEX_FILE', str(tmp_path / 'redirected-index'))
    with pytest.raises(RecoveryError, match='RECOVERY_ENVIRONMENT_INVALID'):
        ownership_cli.create(source, repository, cid, 'phase_owned', 'exact grant')


def test_legacy_exclusion_without_ledger_keeps_exact_finalize_rules(repository, tmp_path, monkeypatch):
    from agent_phase import ownership_challenge
    target = track(repository, 'legacy.txt', symlink=False)
    # Produce the retained pre-challenge shape through the existing legacy
    # path-disposition implementation, including its sealed source archive.
    with monkeypatch.context() as legacy:
        legacy.setattr(ownership_challenge, 'observe', lambda *a, **k: None)
        legacy.setattr(ownership_challenge, 'prompt', lambda *a, **k: '')
        state = make_dispatcher(repository, tmp_path / 'source', OwnershipRunner(
            hooks={2: lambda cwd, prompt: target.unlink()},
            dispositions=[{'path': 'legacy.txt', 'disposition': 'exclude_unrelated'}],
        )).dispatch(PHASE_ID, REQUEST, finalization_policy='checkpoint')
    assert state.get('ownership_challenges') is None
    runner = OwnershipRunner()
    replay = make_dispatcher(repository, tmp_path / 'resume', runner).resume(
        PHASE_ID, REQUEST, Path(state['run_directory']), 'finalize',
        finalization_policy='commit-local')
    assert replay['repository_finalized']
    assert not runner.calls
    assert git(repository, 'show', 'HEAD:legacy.txt') == 'entry bytes'
    assert not target.exists()


@pytest.mark.parametrize('decision', ['phase_owned', 'exclude_unrelated'])
def test_terminal_manager_resolution_is_idempotent_and_preserves_worktree(repository, tmp_path, decision):
    source, state = source_with_challenges(repository, tmp_path)
    receipt = resolution(repository, source, state, tmp_path / 'resolution.json', decision)
    first = finalize(source, repository, [receipt])
    assert first['finalization']['outcome'] == 'completed'
    report = Path(first['receipt_path']).with_suffix('.md').read_text()
    assert 'Semantic outcome: completed' in report
    assert 'resolved_by_manager: 1' in report
    assert 'deleted-0.txt' in report
    assert 'not automatically restored' in report
    assert not (repository / 'deleted-0.txt').exists()
    if decision == 'exclude_unrelated':
        assert git(repository, 'show', 'HEAD:deleted-0.txt') == 'entry bytes'
    else:
        assert git(repository, 'ls-tree', 'HEAD', '--', 'deleted-0.txt') == ''
    head = git(repository, 'rev-parse', 'HEAD')
    second = finalize(source, repository, [receipt])
    assert second['finalization']['outcome'] in ('materialized', 'reused')
    assert not second['git_mutation_performed']
    assert git(repository, 'rev-parse', 'HEAD') == head
    assert json.loads((source / 'state.json').read_text())['finalization_outcome'] == 'blocked'


@pytest.mark.parametrize('kind', ['duplicate', 'contradictory', 'second_open', 'candidate_drift', 'cross_run'])
def test_manager_receipts_refuse_non_exact_or_incomplete_authority(repository, tmp_path, kind):
    source, state = source_with_challenges(repository, tmp_path, count=2 if kind == 'second_open' else 1)
    first = resolution(repository, source, state, tmp_path / 'first.json')
    receipts = [first]
    if kind == 'duplicate':
        receipts.append(first)
    elif kind == 'contradictory':
        receipts.append(resolution(repository, source, state, tmp_path / 'second.json', 'exclude_unrelated'))
    elif kind == 'candidate_drift':
        (repository / 'product.txt').write_text('different candidate\n')
    elif kind == 'cross_run':
        (repository / 'deleted-0.txt').write_text('entry bytes\n')
        runner = OwnershipRunner(hooks={4: lambda cwd, prompt: (cwd / 'deleted-0.txt').unlink()})
        other = make_dispatcher(repository, tmp_path / 'other', runner).dispatch(
            PHASE_ID, REQUEST, finalization_policy='checkpoint')
        source = Path(other['run_directory'])
    head = git(repository, 'rev-parse', 'HEAD')
    index = gitstate.index_identity(repository)
    with pytest.raises(RecoveryError):
        finalize(source, repository, receipts)
    assert git(repository, 'rev-parse', 'HEAD') == head
    assert gitstate.index_identity(repository) == index


def test_manager_entry_dirt_grant_is_exact_and_exclusion_is_unsupported(repository, tmp_path):
    source, state = source_with_challenges(repository, tmp_path, dirty=True)
    cid = state['ownership_challenges']['records'][0]['challenge_id']
    with pytest.raises(ownership_cli.OwnershipResolutionError):
        ownership_cli.create(source, repository, cid, 'exclude_unrelated', 'decline')
    with pytest.raises(RecoveryError):
        finalize(source, repository, [])
    path = resolution(repository, source, state, tmp_path / 'grant.json')
    result = finalize(source, repository, [path])
    assert result['finalization']['outcome'] == 'completed'
    assert git(repository, 'show', 'HEAD:README.md') == 'exact phase overwrite'
    assert (repository / 'README.md').read_text() == 'exact phase overwrite\n'
    assert state['ownership_candidate_evidence']['entry']['reconstruction_verified']


def test_resolution_creation_has_no_provider_tests_or_git_writes(repository, tmp_path, monkeypatch):
    source, state = source_with_challenges(repository, tmp_path)
    before = gitstate.index_identity(repository), git(repository, 'rev-parse', 'HEAD')
    monkeypatch.setattr('agent_phase.provider.run', lambda *a, **k: pytest.fail('provider called'))
    monkeypatch.setattr(gitstate, 'capture_entry', lambda *a, **k: pytest.fail('live candidate captured'))
    original = gitstate._run

    def read_only(root, arguments, *args, **kwargs):
        assert arguments[0] not in {'add', 'commit', 'write-tree', 'update-index', 'update-ref', 'push', 'hash-object'}
        return original(root, arguments, *args, **kwargs)

    monkeypatch.setattr(gitstate, '_run', read_only)
    output = resolution(repository, source, state, tmp_path / 'private.json')
    assert output.stat().st_mode & 0o777 == 0o600
    with pytest.raises(ownership_cli.OwnershipResolutionError):
        ownership_cli._write_create_only(output, ownership_cli.read(output))
    assert before == (gitstate.index_identity(repository), git(repository, 'rev-parse', 'HEAD'))


def test_open_terminal_challenge_cannot_resume_into_git_or_adoption(repository, tmp_path):
    from agent_phase import adoption
    from agent_phase.dispatch import DispatchError
    from agent_phase.resume_validation import ResumeError
    source, state = source_with_challenges(repository, tmp_path)
    runner = OwnershipRunner()
    with pytest.raises((DispatchError, ResumeError)) as refusal:
        make_dispatcher(repository, tmp_path / 'resume', runner).resume(
            PHASE_ID, REQUEST, source, 'finalize', finalization_policy='checkpoint')
    assert refusal.value.code == 'OWNERSHIP_CHALLENGE_OPEN'
    assert runner.calls == []
    with pytest.raises(RecoveryError):
        adoption.create(source, repository, 'NEXT-PHASE', REQUEST, reason='adopt')


def test_formatter_cannot_introduce_challenge_resolution():
    from agent_phase.result import StageResult
    from agent_phase.result_repair import _require_inherited_dispositions
    from agent_phase.finalization import FinalizationError
    parsed = StageResult(1, 'closeout', 'completed', '', None,
        ownership_resolutions=({'challenge_id': 'ownch1-' + 'a' * 64, 'decision': 'phase_owned'},))
    with pytest.raises(FinalizationError, match='OWNERSHIP_CHALLENGE_INVALID'):
        _require_inherited_dispositions({}, parsed)


@pytest.mark.parametrize('field', [
    '"ownership_resolutions":[],"ownership_resolutions":[]',
    '"ownership_resolutions":[{"challenge_id":"ownch1-' + 'a' * 64 + '","decision":"phase_owned","decision":"exclude_unrelated"}]',
])
def test_duplicate_resolution_keys_are_authority_errors_not_formatter_requests(field):
    from agent_phase import result
    token = 'a' * 32
    begin, end = result.markers(token)
    payload = '{"version":1,"stage":"closeout","outcome":"completed","body":"","commit_message":null,' + field + '}'
    with pytest.raises(result.ResultError) as refusal:
        result.parse((begin + '\n' + payload + '\n' + end).encode(), 'closeout', token)
    assert refusal.value.code == 'OWNERSHIP_PROVIDER_RESOLUTION_INVALID'


def test_owner_cli_requires_exact_run_and_external_create_only_output(repository, tmp_path, monkeypatch, capsys):
    with pytest.raises(SystemExit):
        ownership_cli.main(['resolve'])
    source, state = source_with_challenges(repository, tmp_path)
    monkeypatch.chdir(repository)
    output = tmp_path / 'cli-resolution.json'
    argv = ['resolve', '--run', str(source), '--challenge',
            state['ownership_challenges']['records'][0]['challenge_id'],
            '--decision', 'phase_owned', '--reason', 'Exact manager decision', '--output']
    assert ownership_cli.main([*argv, str(repository / 'forbidden.json')]) == 2
    assert not (repository / 'forbidden.json').exists()
    assert ownership_cli.main([*argv, str(source / 'forbidden.json')]) == 2
    assert not (source / 'forbidden.json').exists()
    assert ownership_cli.main([*argv, str(output)]) == 0
    before = output.read_bytes()
    assert ownership_cli.main([*argv, str(output)]) == 2
    assert output.read_bytes() == before
    capsys.readouterr()


def test_completed_materialization_can_carry_manager_resolution_into_adoption(repository, tmp_path):
    from agent_phase import adoption
    source, state = source_with_challenges(repository, tmp_path)
    grant = resolution(repository, source, state, tmp_path / 'grant.json')
    assert finalize(source, repository, [grant])['finalization']['outcome'] == 'completed'
    materialized = finalize(source, repository, [grant])
    record = adoption.create(source, repository, 'OWNCHALLENGE-NEXT', REQUEST,
        reason='Continue from already materialized candidate',
        materialization_receipt=Path(materialized['receipt_path']))
    adoption.validate_retained(repository, record)
    assert record['source_candidate_manifest']['paths']['deleted-0.txt']['present'] is False
    output = tmp_path / 'adoption.json'
    output.write_bytes(adoption.encoded(record))
    output.chmod(0o600)
    runner = OwnershipRunner(hooks={2: lambda cwd, prompt: (cwd / 'next.txt').write_text('next phase\n')})
    continued = make_dispatcher(repository, tmp_path / 'continued', runner).dispatch(
        'OWNCHALLENGE-NEXT', REQUEST, finalization_policy='checkpoint', continue_from=output)
    assert continued['semantic_outcome'] == 'completed'
    assert continued['ownership_challenges']['records'] == []


@pytest.mark.parametrize('lifecycle,terminal,count', [
    ('solo', 'solo', 1), ('plan-reviewed', 'produce_close', 3),
    ('work-reviewed', 'revise_close', 3),
])
def test_terminal_deletion_never_requests_an_extra_turn_across_lifecycles(repository, tmp_path, lifecycle, terminal, count):
    from test_agent_phase_lifecycle_dispatch import LifecycleRunner, dispatcher, REQUEST as request

    def mutate(stage, root):
        if stage == terminal:
            (root / 'README.md').unlink()

    runner = LifecycleRunner(mutate=mutate, path_dispositions=[{'path': 'README.md', 'disposition': 'phase_owned'}])
    state = dispatcher(repository, tmp_path, runner).dispatch(
        'OWNCHALLENGE-LIFECYCLE', request, lifecycle=lifecycle, finalization_policy='checkpoint')
    assert state['semantic_outcome'] == 'completed'
    assert state['finalization_outcome'] == 'blocked'
    assert state['finalization']['repair_class'] == 'requires_manager_ownership'
    assert len(runner.calls) == count
    assert state['ownership_challenges']['records'][0]['boundary'] == 'post_terminal'
    assert state['commit'] is None
