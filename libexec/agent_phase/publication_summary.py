"""Separate disposition-eligible Git paths from historical stage observations."""

from pathlib import Path
from typing import Any

from . import gitstate


def cumulative_lines(state: dict[str, Any], limit: int) -> list[str]:
    """Read the cumulative Git delta at the last retained stage boundary."""
    heading = 'Git/product cumulative delta — eligible for publication/path-disposition decisions'
    entry = state.get('entry') or {}
    stages = (state.get('stage_delta_ledger') or {}).get('stages', {})
    last = state.get('_last_closed_stage')
    record = stages.get(last, {})
    base = (state.get('path_ownership') or {}).get('entry_tree') or (
        state.get('resume') or {}).get('source_entry_tree') or entry.get('tree')
    raw = record.get('after_tree') or (state.get('path_ownership') or {}).get('raw_tree')
    if not raw:
        for stage in reversed(state.get('stages_completed', [])):
            raw = stages.get(stage, {}).get('after_tree')
            if raw:
                break
    if not entry.get('root') or not base or not raw:
        return [heading, 'Cumulative Git binding unavailable; stage observations alone do not grant ownership.']
    try:
        changes = gitstate.phase_delta(Path(entry['root']), base, raw)
    except (gitstate.GitStateError, OSError):
        return [heading, 'Cumulative Git binding unavailable; stage observations alone do not grant ownership.']
    lines = [heading, *[f'- {change.status}: `{change.path}`' for change in changes[:limit]]]
    if not changes:
        lines.append('No cumulative Git changes.')
    if len(changes) > limit:
        lines.append(f'{len(changes) - limit} cumulative Git paths omitted for prompt capacity.')
    return lines
