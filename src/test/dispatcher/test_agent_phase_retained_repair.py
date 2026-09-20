"""Readback of real in-run repair artifacts, without replaying the formatter."""
import json

import pytest

from agent_phase.lifecycle import get_lifecycle, LIFECYCLE_STANDARD
from agent_phase.resume import _terminal_result
from agent_phase.resume_validation import ResumeError
from agent_phase import result as result_module
from test_agent_phase_closeout import FormattingRepairRunner, PHASE_ID, REQUEST
from test_agent_phase_dispatch import make_dispatcher, repository

__all__ = ['repository']


@pytest.mark.parametrize('repair_kind', ['in-run', 'post-hoc'])
@pytest.mark.parametrize('damage', [None, 'stdout', 'prompt', 'normalized', 'transport', 'outcome'])
def test_read_recorded_repair(repository, tmp_path, damage, repair_kind):
    if repair_kind == 'in-run':
        runner = FormattingRepairRunner(repository)
        dispatcher = make_dispatcher(repository, tmp_path, runner)
        state = dispatcher.dispatch(PHASE_ID, REQUEST, finalization_policy='checkpoint')
        source, = [p.parent for p in (tmp_path / 'runs').rglob('state.json')]
    else:
        from pathlib import Path
        from test_agent_phase_result_repair import make_source, repair, RepairRunner
        malformed = make_source(repository, tmp_path)
        runner = RepairRunner()
        state = repair(repository, tmp_path, malformed, runner)
        source = Path(state['run_directory'])
    assert state['complete'] is True
    lifecycle = get_lifecycle(LIFECYCLE_STANDARD)
    original = (source / '05-closeout.stdout.md').read_bytes()
    assert state['result_repair']['strict_parse_outcome'] == (
        'parsed' if repair_kind == 'in-run' else 'parsed_completed'
    )
    calls = len(runner.calls)
    before = {p.name: p.read_bytes() for p in source.iterdir() if p.is_file()}
    if damage == 'stdout':
        (source / 'result-repair.stdout.md').write_bytes(b'not a valid response')
    elif damage == 'prompt':
        (source / 'result-repair.prompt.md').write_bytes(b'wrong original response')
    elif damage == 'normalized':
        path = source / 'result-repair.result.json'
        value = json.loads(path.read_text())
        value['body'] = 'changed'
        path.write_text(json.dumps(value))
    elif damage == 'transport':
        state['result_repair_transport']['validated'] = False
    elif damage == 'outcome':
        state['semantic_outcome'] = 'blocked'
    if damage:
        with pytest.raises(ResumeError, match='RESUME_ARTIFACT_MISMATCH'):
            _terminal_result(source, state, tuple(state['stages_completed']), lifecycle)
    else:
        parsed = _terminal_result(source, state, tuple(state['stages_completed']), lifecycle)
        assert parsed.completed
        assert parsed.as_dict() == json.loads((source / state['terminal_result_artifact']).read_text())
        assert before == {p.name: p.read_bytes() for p in source.iterdir() if p.is_file()}
        # Removing the receipt restores strict original-response behavior.
        assert _terminal_result(source, {**state, 'result_repair': None},
                                tuple(state['stages_completed']), lifecycle) is None
    assert (source / '05-closeout.stdout.md').read_bytes() == original
    assert len(runner.calls) == calls
