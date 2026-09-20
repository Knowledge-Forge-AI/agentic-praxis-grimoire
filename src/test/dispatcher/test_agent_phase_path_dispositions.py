"""Publication ownership exercised through real disposable Git lifecycles."""

import json
import re
from pathlib import Path

import pytest

from agent_phase import result
from test_agent_phase_disposition_flow import DispositionFakeRunner, PHASE_ID, REQUEST, git, make_dispatcher, repository as _repository

repository = _repository


class OwnershipRunner(DispositionFakeRunner):
    def __init__(self, *args, dispositions=None, narrative=None,
                 challenge_decision=None, ownership_resolutions=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.dispositions = dispositions
        self.narrative = narrative
        self.challenge_decision = challenge_decision
        self.ownership_resolutions = ownership_resolutions

    def __call__(self, *args, **kwargs):
        response = super().__call__(*args, **kwargs)
        prompt = args[1] if len(args) > 1 else kwargs['prompt']
        if b'<<<AGENT-PHASE-RESULT ' in response.stdout and (
            self.dispositions is not None or self.narrative is not None
            or self.challenge_decision is not None
            or self.ownership_resolutions is not None
        ):
            lines = response.stdout.splitlines()
            payload = json.loads(lines[1])
            if self.dispositions is not None:
                payload['path_dispositions'] = self.dispositions
            if self.narrative is not None:
                payload['body'] = self.narrative
            if self.ownership_resolutions is not None:
                resolutions = self.ownership_resolutions
                if callable(resolutions):
                    resolutions = resolutions(prompt)
                payload['ownership_resolutions'] = resolutions
            elif self.challenge_decision is not None:
                challenge_ids = [
                    match.decode('ascii')
                    for match in re.findall(
                        rb'"challenge_id"\s*:\s*"(ownch1-[0-9a-f]{64})"',
                        prompt,
                    )
                ]
                payload['ownership_resolutions'] = [
                    {'challenge_id': challenge_id, 'decision': self.challenge_decision}
                    for challenge_id in challenge_ids
                ]
            lines[1] = json.dumps(payload).encode()
            response = response._replace(stdout=b'\n'.join(lines) + b'\n')
        return response


def track(root, path, symlink=True):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    if symlink:
        target.symlink_to('.agents/skills')
    else:
        target.write_text('entry bytes\n')
    git(root, 'add', '--', path)
    git(root, 'commit', '-qm', 'Track entry object')
    return target


@pytest.mark.parametrize('path,symlink', [('.claude/skills', True), ('arbitrary/link', True), ('regular.txt', False)])
@pytest.mark.parametrize('disposition', ['exclude_environment', 'exclude_unrelated', 'phase_owned', None])
def test_deletion_ownership(repository, tmp_path, path, symlink, disposition):
    target = track(repository, path, symlink)
    before = git(repository, 'rev-parse', 'HEAD')

    def change(cwd, prompt):
        target.unlink()
        (cwd / 'product.txt').write_text('accepted\n')

    runner = OwnershipRunner(hooks={2: change}, dispositions=(
        None if disposition is None else [{'path': path, 'disposition': disposition}]
    ), narrative='The deletion is a sandbox artifact and must not be published.')
    state = make_dispatcher(repository, tmp_path, runner).dispatch(
        PHASE_ID, REQUEST, finalization_policy='commit-local',
    )
    # A raw path claim cannot resolve a dispatcher-created deletion challenge.
    # The challenge must be resolved by its exact ID in the terminal result or
    # by the provider-free manager lane.
    assert state['manager_disposition_required'] is True
    assert state['commit'] is None
    assert git(repository, 'rev-parse', 'HEAD') == before
    assert 'path_ownership_required' in state['manager_attention_reasons']
    assert len(state['ownership_challenges']['records']) == 1
    assert state['ownership_challenges']['records'][0]['path'] == path
    assert state['ownership_challenges']['records'][0]['reason'] == 'unclaimed_tracked_deletion'
    assert state['ownership_challenges']['events'][-1]['kind'] == 'shown'
    assert path not in state['candidate_manifest']['paths']
    assert not target.exists() and not target.is_symlink()
    output = json.loads(Path(state['run_directory'], 'result.json').read_text())
    assert output['mechanical_phase_delta'] == state['mechanical_phase_delta']
    report = Path(state['run_directory'], 'result.md').read_text()
    assert 'raw terminal observation' in report and 'publication candidate' in report
    assert 'mechanical delta (observed, not necessarily published)' in report
    assert 'excluded from publication: 0 path(s)' in report
    assert path in report


@pytest.mark.parametrize('disposition', ['exclude_environment', 'phase_owned'])
@pytest.mark.parametrize('policy', ['checkpoint', 'commit-local'])
def test_finalize_replay_preserves_ownership(repository, tmp_path, disposition, policy):
    path = '.claude/skills'
    target = track(repository, path)
    (repository / 'operator.txt').write_text('unstaged operator\n')
    index = git(repository, 'ls-files', '--stage', '--', 'operator.txt')

    def change(cwd, prompt):
        target.unlink()
        (cwd / 'product.txt').write_text('accepted\n')

    supplied_disposition = (
        'exclude_unrelated' if disposition == 'exclude_environment' else disposition
    )
    state = make_dispatcher(repository, tmp_path, OwnershipRunner(
        hooks={2: change}, dispositions=[{'path': path, 'disposition': supplied_disposition}],
        challenge_decision=(
            'phase_owned' if disposition == 'phase_owned' else 'exclude_unrelated'
        ),
    )).dispatch(PHASE_ID, REQUEST, finalization_policy=policy)
    if policy == 'checkpoint' and disposition == 'exclude_environment':
        manifest = json.loads(Path(state['run_directory'], 'checkpoint-candidate-manifest.json').read_text())
        assert path not in manifest['paths']
        assert git(repository, 'ls-tree', manifest['publication_tree'], '--', path).startswith('120000 ')
        assert manifest['observed_terminal_tree'] != manifest['publication_tree']

    def no_provider(*args, **kwargs):
        pytest.fail('finalize-only must not invoke a provider')

    replay = make_dispatcher(repository, tmp_path / 'replay', no_provider).resume(
        PHASE_ID, REQUEST, Path(state['run_directory']), 'finalize',
        finalization_policy='commit-local',
    )
    assert replay['complete'] is True
    assert replay['path_dispositions'] == state['path_dispositions']
    assert replay['excluded_paths'] == state['excluded_paths']
    assert replay['commit']
    if policy == 'commit-local':
        assert replay['commit']['sha'] == state['commit']['sha']
        assert replay['commit_reused'] is True
    assert git(repository, 'ls-files', '--stage', '--', 'operator.txt') == index
    assert (repository / 'operator.txt').read_text() == 'unstaged operator\n'
    assert git(repository, 'ls-tree', 'HEAD', '--', 'operator.txt') == ''
    assert bool(git(repository, 'ls-tree', 'HEAD', '--', path)) == (disposition != 'phase_owned')


@pytest.mark.parametrize('value', [
    None, {}, [{'path': '/absolute', 'disposition': 'phase_owned'}],
    *[[{'path': path, 'disposition': 'phase_owned'}] for path in
      ('../escape', 'a/../b', '', './a', 'a//b', 'a/', 'a/./b', 'C:/outside', 'a\x00b')],
    [{'path': 'a', 'disposition': 'unknown'}],
    [{'path': 'a', 'disposition': 'phase_owned', 'extra': True}],
    [{'path': 'a', 'disposition': 'phase_owned'}] * 2,
    [{'path': 'a', 'disposition': 'phase_owned'}, {'path': 'a', 'disposition': 'exclude_environment'}],
    [{'path': str(i), 'disposition': 'phase_owned'} for i in range(1025)],
    [{'path': 'x' * 131073, 'disposition': 'phase_owned'}],
])
def test_invalid_contract(value):
    from agent_phase.path_disposition import validate_dispositions
    with pytest.raises(result.ResultError, match='PATH_DISPOSITION_INVALID'):
        validate_dispositions(value)


def test_unobserved_disposition_fails_before_commit(repository, tmp_path):
    from agent_phase.dispatch import DispatchError
    before = git(repository, 'rev-parse', 'HEAD')
    with pytest.raises(DispatchError, match='PATH_DISPOSITION_INVALID'):
        make_dispatcher(repository, tmp_path, OwnershipRunner(dispositions=[
            {'path': 'README.md', 'disposition': 'phase_owned'},
        ])).dispatch(PHASE_ID, REQUEST, finalization_policy='commit-local')
    assert git(repository, 'rev-parse', 'HEAD') == before


def test_staged_operator_dirt_is_rejected_unchanged(repository, tmp_path):
    from agent_phase import gitstate
    (repository / 'operator.txt').write_text('staged\n')
    git(repository, 'add', 'operator.txt')
    (repository / 'operator.txt').write_text('unstaged\n')
    before = gitstate.index_identity(repository)
    head = git(repository, 'rev-parse', 'HEAD')
    runner = OwnershipRunner()
    with pytest.raises(gitstate.GitStateError, match='ENTRY_STAGED_CHANGES'):
        make_dispatcher(repository, tmp_path, runner).dispatch(PHASE_ID, REQUEST)
    assert runner.calls == []
    assert gitstate.index_identity(repository) == before
    assert git(repository, 'rev-parse', 'HEAD') == head
    assert (repository / 'operator.txt').read_text() == 'unstaged\n'


def test_exclusion_without_product_leaves_local_deletion(repository, tmp_path):
    target = track(repository, 'ordinary.txt', False)
    head = git(repository, 'rev-parse', 'HEAD')
    state = make_dispatcher(repository, tmp_path, OwnershipRunner(
        hooks={2: lambda cwd, prompt: target.unlink()},
        dispositions=[{'path': 'ordinary.txt', 'disposition': 'exclude_unrelated'}],
        challenge_decision='exclude_unrelated',
    )).dispatch(PHASE_ID, REQUEST, finalization_policy='commit-local')
    assert state['completion_kind'] == 'finalized_empty_delta'
    assert state['candidate_manifest']['paths'] == {}
    assert not target.exists()
    assert git(repository, 'rev-parse', 'HEAD') == head


def test_inherited_exclusion_conflict_stops_before_provider(repository, tmp_path):
    from agent_phase.dispatch import DispatchError
    target = track(repository, 'ordinary.txt', False)
    state = make_dispatcher(repository, tmp_path, OwnershipRunner(
        hooks={2: lambda cwd, prompt: target.unlink()},
        dispositions=[{'path': 'ordinary.txt', 'disposition': 'exclude_environment'}],
        challenge_decision='exclude_unrelated',
    )).dispatch(PHASE_ID, REQUEST, finalization_policy='checkpoint')
    target.write_text('new operator bytes\n')
    runner = OwnershipRunner()
    with pytest.raises(DispatchError) as caught:
        make_dispatcher(repository, tmp_path / 'resume', runner).resume(
            PHASE_ID, REQUEST, Path(state['run_directory']), 'finalize',
            finalization_policy='commit-local',
        )
    assert caught.value.code == 'RESUME_CANDIDATE_CONFLICT'
    assert runner.calls == []
    assert target.read_text() == 'new operator bytes\n'


def test_exclusion_cannot_displace_present_descendant(repository, tmp_path):
    target = track(repository, 'ordinary', False)
    head = git(repository, 'rev-parse', 'HEAD')
    def change(cwd, prompt):
        target.unlink()
        target.mkdir()
        (target / 'conflicting.txt').write_text('keep these bytes\n')
    state = make_dispatcher(repository, tmp_path, OwnershipRunner(
        hooks={2: change},
        dispositions=[{'path': 'ordinary', 'disposition': 'exclude_environment'}],
    )).dispatch(PHASE_ID, REQUEST, finalization_policy='commit-local')
    assert state['manager_disposition_required'] is True
    assert state['commit'] is None
    assert state['ownership_challenges']['records'][0]['path'] == 'ordinary'
    assert git(repository, 'rev-parse', 'HEAD') == head
    assert (target / 'conflicting.txt').read_text() == 'keep these bytes\n'


def test_resumed_terminal_inherits_exclusion_without_reclaiming(repository, tmp_path):
    target = track(repository, 'ordinary.txt', False)
    state = make_dispatcher(repository, tmp_path, OwnershipRunner(
        hooks={2: lambda cwd, prompt: target.unlink()},
        dispositions=[{'path': 'ordinary.txt', 'disposition': 'exclude_unrelated'}],
        challenge_decision='exclude_unrelated',
    )).dispatch(PHASE_ID, REQUEST, finalization_policy='checkpoint')
    runner = OwnershipRunner(hooks={0: lambda cwd, prompt: (cwd / 'new.txt').write_text('new\n')})
    replay = make_dispatcher(repository, tmp_path / 'resume', runner).resume(
        PHASE_ID, REQUEST, Path(state['run_directory']), 'closeout',
        finalization_policy='commit-local',
    )
    assert len(runner.calls) == 1
    assert replay['commit']
    assert replay['excluded_paths'] == ['ordinary.txt']
    assert 'ordinary.txt' not in replay['inherited_candidate_manifest']['paths']
    assert 'ordinary.txt' not in replay['candidate_manifest']['paths']
    assert git(repository, 'show', 'HEAD:ordinary.txt') == 'entry bytes'
    assert not target.exists()


@pytest.mark.parametrize('dispositions', [
    [{'path': '/outside', 'disposition': 'phase_owned'}],
    [{'path': 'ordinary.txt', 'disposition': 'phase_owned'}] * 2,
    [{'path': 'ordinary.txt', 'disposition': 'exclude_environment'},
     {'path': 'ordinary.txt', 'disposition': 'phase_owned'}],
])
def test_invalid_ownership_never_invokes_formatter(repository, tmp_path, dispositions):
    from agent_phase.dispatch import DispatchError
    target = track(repository, 'ordinary.txt', False)
    head = git(repository, 'rev-parse', 'HEAD')
    runner = OwnershipRunner(hooks={2: lambda cwd, prompt: target.unlink()}, dispositions=dispositions)
    with pytest.raises(DispatchError) as caught:
        make_dispatcher(repository, tmp_path, runner).dispatch(PHASE_ID, REQUEST)
    assert caught.value.code == 'PATH_DISPOSITION_INVALID'
    assert len(runner.calls) == 5
    assert git(repository, 'rev-parse', 'HEAD') == head
    state = json.loads(next((tmp_path / 'runs').rglob('state.json')).read_text())
    assert state['manager_disposition_required'] is True
    assert 'ordinary.txt' not in state['candidate_manifest']['paths']


def test_invalid_enclosing_result_cannot_drop_exclusion(repository, tmp_path):
    from agent_phase.dispatch import DispatchError
    class InvalidEnvelope(OwnershipRunner):
        def __call__(self, *args, **kwargs):
            response = super().__call__(*args, **kwargs)
            if b'<<<AGENT-PHASE-RESULT ' in response.stdout:
                lines = response.stdout.splitlines()
                payload = json.loads(lines[1])
                payload['version'] = 2
                lines[1] = json.dumps(payload).encode()
                response = response._replace(stdout=b'\n'.join(lines))
            return response
    target = track(repository, 'ordinary.txt', False)
    head = git(repository, 'rev-parse', 'HEAD')
    runner = InvalidEnvelope(
        hooks={2: lambda cwd, prompt: target.write_text('unrelated changed bytes\n')},
        dispositions=[{'path': 'ordinary.txt', 'disposition': 'exclude_unrelated'}],
    )
    with pytest.raises(DispatchError) as caught:
        make_dispatcher(repository, tmp_path, runner).dispatch(PHASE_ID, REQUEST)
    assert caught.value.code == 'RESULT_VERSION'
    assert len(runner.calls) == 5
    assert git(repository, 'rev-parse', 'HEAD') == head


def test_nonrestorable_exclusion_records_manager_attention(repository, tmp_path):
    from agent_phase import finalization, gitstate
    from agent_phase.display import Display
    target = track(repository, 'ordinary.txt', False)
    state = make_dispatcher(repository, tmp_path, OwnershipRunner(
        hooks={2: lambda cwd, prompt: (target.unlink(), (cwd / 'product.txt').write_text('product\n'))},
        dispositions=[{'path': 'ordinary.txt', 'disposition': 'exclude_environment'}],
        challenge_decision='exclude_unrelated',
    )).dispatch(PHASE_ID, REQUEST, finalization_policy='checkpoint')
    # A concurrent commit changes the object that an exclusion would preserve.
    # Keep the exact raw terminal worktree observation for finalization.
    target.write_text('concurrent committed bytes\n')
    git(repository, 'add', '--', 'ordinary.txt')
    git(repository, 'commit', '-qm', 'Change excluded object')
    target.unlink()
    state['finalization_policy'] = 'commit-local'
    state['manager_disposition_required'] = False
    recorded = state['entry']
    entry = gitstate.EntryState(repository, recorded['head'], recorded['branch'],
                                recorded['tree'], {}, recorded['index'])
    parsed = result.StageResult(1, 'closeout', 'completed', 'done',
        result.CommitMessage('Preserve product', ''),
        ({'path': 'ordinary.txt', 'disposition': 'exclude_environment'},))
    before = git(repository, 'rev-parse', 'HEAD')
    with pytest.raises(finalization.FinalizationError, match='PATH_DISPOSITION_INVALID'):
        finalization.finalize_repository(
            state, entry, parsed, Display(None, enabled=False), resumed=False,
            expected_index=gitstate.index_identity(repository),
        )
    assert state['manager_disposition_required'] is True
    assert 'path_ownership_invalid' in state['manager_attention_reasons']
    assert git(repository, 'rev-parse', 'HEAD') == before
    assert not target.exists()
