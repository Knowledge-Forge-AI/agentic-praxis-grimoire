"""Redundant metadata dispositions require retained observation and Git proof."""

import json
from pathlib import Path

import pytest

from agent_phase.dispatch import DispatchError
from test_agent_phase_path_dispositions import OwnershipRunner, track
from test_agent_phase_disposition_flow import PHASE_ID, REQUEST, git, make_dispatcher, repository as _repository

repository = _repository


METADATA = '.serena/cache/language/symbols.pkl'


def add_product_and_metadata(cwd, prompt):
    (cwd / 'product.txt').write_text('accepted\n')
    path = cwd / METADATA
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'opaque metadata')


@pytest.mark.parametrize('disposition', [None, 'exclude_environment', 'exclude_unrelated'])
@pytest.mark.parametrize('policy', ['checkpoint', 'commit-local', 'publish'])
def test_metadata_publication_neutral(repository, tmp_path, disposition, policy):
    supplied = None if disposition is None else [{'path': METADATA, 'disposition': disposition}]
    state = make_dispatcher(repository, tmp_path, OwnershipRunner(
        hooks={2: add_product_and_metadata}, dispositions=supplied,
    )).dispatch(PHASE_ID, REQUEST, finalization_policy=policy)
    assert state['complete']
    assert state['publication_candidate']['tree'] == state['raw_terminal_candidate']['tree']
    assert METADATA not in state['candidate_manifest']['paths']
    assert METADATA not in state['phase_owned_paths']
    assert state['path_dispositions'] == []
    assert state['excluded_paths'] == []
    noops = state.get('path_disposition_noops', [])
    assert len(noops) == int(disposition is not None)
    if noops:
        assert noops[0]['path'] == METADATA
        assert noops[0]['disposition'] == disposition
        assert noops[0]['observation']['stage'] == 'work'
    output = json.loads(Path(state['run_directory'], 'result.json').read_text())
    assert output['path_disposition_noops'] == noops
    terminal = json.loads(Path(state['run_directory'], '05-closeout.result.json').read_text())
    assert terminal.get('path_dispositions') == supplied
    if policy == 'publish':
        assert state['push']['succeeded']
        assert git(repository, 'rev-parse', 'HEAD') == git(
            repository, 'ls-remote', 'origin', state['push']['remote_ref'],
        ).split()[0]
        assert git(repository, 'ls-tree', 'HEAD', '--', METADATA) == ''
        return

    def no_provider(*args, **kwargs):
        pytest.fail('finalize-only must not invoke providers')

    replay = make_dispatcher(repository, tmp_path / 'replay', no_provider).resume(
        PHASE_ID, REQUEST, Path(state['run_directory']), 'finalize',
        finalization_policy='commit-local',
    )
    assert replay['complete'] and replay['commit']
    assert replay['path_disposition_noops'] == noops
    assert git(repository, 'ls-tree', 'HEAD', '--', METADATA) == ''
    assert (repository / METADATA).read_bytes() == b'opaque metadata'


@pytest.mark.parametrize('path,disposition,tracked', [
    ('.serena/not-observed', 'exclude_environment', False),
    ('.serena/not-observed', 'exclude_unrelated', False),
    ('.serena/not-observed', 'phase_owned', False),
    (METADATA, 'phase_owned', False),
    ('.serena/tracked.json', 'exclude_environment', True),
    ('arbitrary-missing', 'exclude_environment', False),
])
def test_missing_dispositions_remain_invalid(repository, tmp_path, path, disposition, tracked):
    if tracked:
        track(repository, path, False)
    head = git(repository, 'rev-parse', 'HEAD')
    with pytest.raises(DispatchError, match='PATH_DISPOSITION_INVALID'):
        make_dispatcher(repository, tmp_path, OwnershipRunner(
            hooks={2: add_product_and_metadata},
            dispositions=[{'path': path, 'disposition': disposition}],
        )).dispatch(PHASE_ID, REQUEST, finalization_policy='commit-local')
    assert git(repository, 'rev-parse', 'HEAD') == head


@pytest.mark.parametrize('field', ['proof_class', 'observation', 'disposition'])
def test_retained_noop_tampering_rejected(repository, tmp_path, field):
    from agent_phase.path_disposition import validate_evidence
    from agent_phase.result import ResultError
    state = make_dispatcher(repository, tmp_path, OwnershipRunner(
        hooks={2: add_product_and_metadata},
        dispositions=[{'path': METADATA, 'disposition': 'exclude_environment'}],
    )).dispatch(PHASE_ID, REQUEST, finalization_policy='checkpoint')
    evidence = json.loads(json.dumps(state['path_ownership']))
    evidence['path_disposition_noops'][0][field] = 'tampered'
    with pytest.raises(ResultError, match='PATH_DISPOSITION_INVALID'):
        validate_evidence(repository, evidence, state)
    state['stage_delta_ledger']['stages']['work']['operational_metadata_paths'] = []
    with pytest.raises(ResultError, match='PATH_DISPOSITION_INVALID'):
        validate_evidence(repository, state['path_ownership'], state)


def test_noop_cannot_override_inherited_claim(repository, tmp_path):
    state = make_dispatcher(repository, tmp_path, OwnershipRunner(
        hooks={2: add_product_and_metadata},
        dispositions=[{'path': METADATA, 'disposition': 'exclude_environment'}],
    )).dispatch(PHASE_ID, REQUEST, finalization_policy='checkpoint')
    with pytest.raises(DispatchError, match='PATH_DISPOSITION_INVALID'):
        make_dispatcher(repository, tmp_path / 'resume', OwnershipRunner(
            dispositions=[{'path': METADATA, 'disposition': 'phase_owned'}],
        )).resume(PHASE_ID, REQUEST, Path(state['run_directory']), 'closeout',
                  finalization_policy='commit-local')


def test_prompt_separates_metadata_from_git_targets(repository, tmp_path):
    from agent_phase.envelope import TERMINAL_RESULT_CONTRACT
    from agent_phase.stage_delta import format_stage_deltas_summary
    state = make_dispatcher(repository, tmp_path, OwnershipRunner(
        hooks={2: add_product_and_metadata},
    )).dispatch(PHASE_ID, REQUEST, finalization_policy='checkpoint')
    summary = format_stage_deltas_summary(state)
    eligible, informational = summary.split('Operational metadata observations', 1)
    assert 'Git/product cumulative delta' in eligible
    assert '`product.txt`' in eligible
    assert METADATA not in eligible
    assert METADATA in informational
    assert 'informational only; not disposition targets' in informational
    assert 'Do not emit path_dispositions for paths the dispatcher classifies as operational_metadata.' in TERMINAL_RESULT_CONTRACT


@pytest.mark.parametrize('case', ['base_object', 'raw_object', 'deletion', 'entry_dirt', 'ancestor_blob', 'alias'])
def test_observation_alone_cannot_grant_noop(repository, case):
    from agent_phase import gitstate
    from agent_phase.path_disposition import apply
    from agent_phase.result import ResultError
    path = METADATA
    if case in ('base_object', 'deletion'):
        target = track(repository, path, False)
    if case == 'ancestor_blob':
        track(repository, '.serena', False)
    entry = gitstate.capture_entry(repository)
    if case == 'raw_object':
        track(repository, path, False)
    if case == 'deletion':
        target.unlink()
    if case == 'alias':
        (repository / '.serena').symlink_to(repository / 'elsewhere')
    raw = gitstate.capture_entry(repository).tree
    state = {'entry': entry.as_dict(), 'stage_delta_ledger': {'stages': {
        'work': {'stage': 'work', 'before_tree': entry.tree, 'after_tree': raw,
                 'operational_metadata_paths': [path]},
    }}}
    if case == 'entry_dirt':
        state['entry']['dirty'] = [path]
    if case in ('deletion', 'raw_object'):
        # A path in the cumulative Git delta is an ordinary disposition target,
        # even if a stale classification view calls it metadata.
        publication, excluded, ambiguous = apply(state, entry, raw, [
            {'path': path, 'disposition': 'exclude_environment'},
        ])
        assert not state['path_disposition_noops']
        assert excluded == {path}
        assert publication == entry.tree
    else:
        with pytest.raises(ResultError, match='PATH_DISPOSITION_INVALID'):
            apply(state, entry, raw, [{'path': path, 'disposition': 'exclude_environment'}])


def test_inherited_noop_cannot_exclude_new_git_object(repository):
    from agent_phase import gitstate
    from agent_phase.path_disposition import apply
    from agent_phase.result import ResultError
    entry = gitstate.capture_entry(repository)
    state = {'entry': entry.as_dict(), 'stage_delta_ledger': {'stages': {
        'work': {'stage': 'work', 'before_tree': entry.tree, 'after_tree': entry.tree,
                 'operational_metadata_paths': [METADATA]},
    }}}
    apply(state, entry, entry.tree, [{'path': METADATA, 'disposition': 'exclude_environment'}])
    track(repository, METADATA, False)
    raw = gitstate.capture_entry(repository).tree
    with pytest.raises(ResultError, match='PATH_DISPOSITION_INVALID'):
        apply(state, entry, raw, [])


def test_resuming_metadata_introducing_terminal_retains_proof(repository, tmp_path):
    state = make_dispatcher(repository, tmp_path, OwnershipRunner(
        hooks={2: lambda cwd, prompt: (cwd / 'product.txt').write_text('accepted\n'),
               4: add_product_and_metadata},
        dispositions=[{'path': METADATA, 'disposition': 'exclude_environment'}],
    )).dispatch(PHASE_ID, REQUEST, finalization_policy='checkpoint')
    replay = make_dispatcher(repository, tmp_path / 'replay', OwnershipRunner()).resume(
        PHASE_ID, REQUEST, Path(state['run_directory']), 'closeout',
        finalization_policy='checkpoint',
    )
    assert replay['complete']
    assert replay['path_disposition_noops'] == state['path_disposition_noops']
    assert len(replay['stage_delta_ledger']['retained_metadata_observations']) == 1
    final = make_dispatcher(repository, tmp_path / 'final', OwnershipRunner()).resume(
        PHASE_ID, REQUEST, Path(replay['run_directory']), 'finalize',
        finalization_policy='commit-local',
    )
    assert final['complete'] and final['commit']
    assert final['path_disposition_noops'] == state['path_disposition_noops']


@pytest.mark.parametrize('lifecycle,stage', [('solo', 'solo'), ('work-reviewed', 'produce')])
def test_metadata_noop_is_lifecycle_independent(repository, tmp_path, lifecycle, stage):
    from test_agent_phase_lifecycle_dispatch import LifecycleRunner, dispatcher, REQUEST as request
    runner = LifecycleRunner(
        mutate=lambda current, cwd: add_product_and_metadata(cwd, b'') if current == stage else None,
        path_dispositions=[{'path': METADATA, 'disposition': 'exclude_environment'}],
    )
    state = dispatcher(repository, tmp_path, runner).dispatch(
        PHASE_ID, request, lifecycle, 'checkpoint',
    )
    assert state['complete']
    assert state['path_disposition_noops'][0]['observation']['stage'] == stage
    assert METADATA not in state['candidate_manifest']['paths']


def test_formatter_can_repeat_but_cannot_mint_noops():
    from agent_phase import finalization, result, result_repair
    state = {'path_ownership': {'dispositions': [], 'path_disposition_noops': [
        {'path': METADATA, 'disposition': 'exclude_environment'},
    ]}}
    parsed = result.StageResult(1, 'closeout', 'completed', 'done', None,
        path_dispositions=({'path': METADATA, 'disposition': 'exclude_environment'},))
    result_repair._require_inherited_dispositions(state, parsed)
    with pytest.raises(finalization.FinalizationError, match='PATH_DISPOSITION_INVALID'):
        result_repair._require_inherited_dispositions({}, parsed)


def test_resumed_closer_sees_cumulative_product_paths(repository, tmp_path):
    state = make_dispatcher(repository, tmp_path, OwnershipRunner(
        hooks={2: add_product_and_metadata},
    )).dispatch(PHASE_ID, REQUEST, finalization_policy='checkpoint')
    prompts = []
    replay = make_dispatcher(repository, tmp_path / 'replay', OwnershipRunner(
        hooks={0: lambda cwd, prompt: prompts.append(prompt)},
    )).resume(PHASE_ID, REQUEST, Path(state['run_directory']), 'closeout',
              finalization_policy='checkpoint')
    assert replay['complete']
    assert prompts
    prompt = prompts[0].decode() if isinstance(prompts[0], bytes) else prompts[0]
    eligible = prompt.split('Git/product cumulative delta', 1)[1].split(
        'Operational metadata observations', 1)[0]
    assert '`product.txt`' in eligible
    assert 'binding unavailable' not in eligible


def test_metadata_volume_preserves_historical_product_summary(repository, tmp_path):
    from agent_phase.stage_delta import format_stage_deltas_summary
    state = make_dispatcher(repository, tmp_path, OwnershipRunner(
        hooks={2: add_product_and_metadata},
    )).dispatch(PHASE_ID, REQUEST, finalization_policy='checkpoint')
    state['stage_delta_ledger']['deltas'] = [
        {'stage': 'work', 'path': f'.serena/{i}', 'status': 'added',
         'classification': 'operational_metadata'} for i in range(200)
    ] + [{'stage': 'work', 'path': 'historical-product.txt', 'status': 'deleted',
          'classification': 'product'}]
    summary = format_stage_deltas_summary(state)
    assert '190 metadata observations omitted' in summary
    assert 'Historical stage observations' in summary
    assert '`historical-product.txt`' in summary


@pytest.mark.parametrize('failure', ['tree', 'root'])
def test_unavailable_git_summary_is_informational(repository, failure):
    from agent_phase import gitstate
    from agent_phase.publication_summary import cumulative_lines
    tree = gitstate.capture_entry(repository).tree
    state = {'entry': {'root': str(repository), 'tree': tree},
             'path_ownership': {'raw_tree': tree}}
    if failure == 'tree':
        state['path_ownership']['raw_tree'] = '0' * 40
    else:
        track(repository, 'second-tree.txt', False)
        state['path_ownership']['raw_tree'] = gitstate.capture_entry(repository).tree
        state['entry']['root'] = str(repository / 'missing')
    assert 'binding unavailable' in '\n'.join(cumulative_lines(state, 40))


def test_repair_inherits_only_required_classification_bindings(repository, tmp_path):
    from types import SimpleNamespace
    from agent_phase import result_repair
    from agent_phase.path_disposition import validate_evidence
    state = make_dispatcher(repository, tmp_path, OwnershipRunner(
        hooks={2: add_product_and_metadata},
        dispositions=[{'path': METADATA, 'disposition': 'exclude_environment'}],
    )).dispatch(PHASE_ID, REQUEST, finalization_policy='checkpoint')
    repair = {}
    result_repair._seed_source_boundary(repair, SimpleNamespace(
        source_state=state, terminal_candidate=state['terminal_candidate'],
        candidate_manifest=state['candidate_manifest'],
        source_entry=SimpleNamespace(root=repository, tree=state['entry']['tree']),
    ))
    ledger = repair['stage_delta_ledger']
    assert set(ledger) == {'retained_metadata_observations'}
    assert len(ledger['retained_metadata_observations']) == 1
    assert set(ledger['retained_metadata_observations'][0]) == {
        'stage', 'before_tree', 'after_tree', 'operational_metadata_paths'}
    repair['entry'] = state['entry']
    validate_evidence(repository, repair['path_ownership'], repair)
    ledger['retained_metadata_observations'][0]['operational_metadata_paths'] = []
    from agent_phase.result import ResultError
    with pytest.raises(ResultError, match='PATH_DISPOSITION_INVALID'):
        validate_evidence(repository, repair['path_ownership'], repair)


def test_missing_product_disposition_reports_cumulative_delta(repository):
    from agent_phase import gitstate
    from agent_phase.path_disposition import apply
    from agent_phase.result import ResultError
    entry = gitstate.capture_entry(repository)
    with pytest.raises(ResultError, match='does not name an observed cumulative delta'):
        apply({'entry': entry.as_dict()}, entry, entry.tree,
              [{'path': 'misspelled-product', 'disposition': 'exclude_environment'}])
