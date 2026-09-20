"""Closed proof for exclusion of already observed, unpublished metadata."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from . import candidate, gitstate, metadata_policy
from .result import ResultError


PROOF_CLASS = 'observed-untracked-operational-metadata-v1'


def _overlaps(path: str, other: str) -> bool:
    return path == other or path.startswith(other + '/') or other.startswith(path + '/')


def _binding(record: dict[str, Any]) -> dict[str, Any]:
    return {key: record.get(key) for key in (
        'stage', 'before_tree', 'after_tree', 'operational_metadata_paths',
    )}


def _digest(binding: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(binding, sort_keys=True,
        separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()


def retain_observation(state: dict[str, Any], stage: str, record: dict[str, Any]) -> None:
    """Keep only no-op-bound classification evidence when a stage is recaptured."""
    noops = (state.get('path_ownership') or {}).get('path_disposition_noops', [])
    binding = _binding(record)
    if any(item['observation']['stage'] == stage and
           item['observation']['binding_sha256'] == _digest(binding) for item in noops):
        ledger = state['stage_delta_ledger']
        retained = ledger.setdefault('retained_metadata_observations', [])
        active = {item['observation']['binding_sha256'] for item in noops}
        retained[:] = [item for item in retained if _digest(item) in active]
        if binding not in retained:
            retained.append(binding)


def _observation(state: dict[str, Any], path: str, expected: Any = None) -> dict[str, Any]:
    from .path_disposition import MAX_ENTRIES
    from .stage_delta import MAX_STAGE_INLINE_DELTAS

    ledger = state.get('stage_delta_ledger') or {}
    stages = ledger.get('stages', {})
    retained = ledger.get('retained_metadata_observations', [])
    if not isinstance(stages, dict) or not isinstance(retained, list) or len(retained) > MAX_ENTRIES:
        raise ResultError('PATH_DISPOSITION_INVALID', 'invalid retained metadata classification view')
    records = [*stages.values(), *retained]
    for record in records:
        # This separately bounded classification view is dispatcher-produced,
        # even when the mixed inline delta prefix is full of product changes.
        if not isinstance(record, dict):
            continue
        paths = record.get('operational_metadata_paths', [])
        if not isinstance(paths, list) or len(paths) > MAX_STAGE_INLINE_DELTAS or any(not isinstance(p, str) for p in paths):
            raise ResultError('PATH_DISPOSITION_INVALID', 'invalid retained metadata path view')
        if path not in paths:
            continue
        binding = _binding(record)
        digest = _digest(binding)
        observation = {'stage': record.get('stage'), 'classification': 'operational_metadata',
                       'binding_sha256': digest}
        if expected is None or observation == expected:
            return observation
    raise ResultError('PATH_DISPOSITION_INVALID', 'no retained metadata observation for disposition')


def inherit_observations(state: dict[str, Any], source: dict[str, Any]) -> None:
    """Carry only bindings required by inherited no-ops into a repair run."""
    noops = (source.get('path_ownership') or {}).get('path_disposition_noops', [])
    ledger = source.get('stage_delta_ledger') or {}
    records = [*(ledger.get('stages') or {}).values(),
               *ledger.get('retained_metadata_observations', [])]
    bindings = []
    for item in noops:
        observation = _observation(source, item['path'], item['observation'])
        for record in records:
            binding = _binding(record)
            if (binding['stage'] == observation['stage']
                    and _digest(binding) == observation['binding_sha256']):
                if binding not in bindings:
                    bindings.append(binding)
                break
    if bindings:
        state.setdefault('stage_delta_ledger', {})['retained_metadata_observations'] = bindings


def prove(root: Path, state: dict[str, Any], base: str, raw: str,
          item: dict[str, str], expected: Any = None) -> dict[str, Any]:
    """Use retained classification and Git objects, never metadata contents."""
    path = item['path']
    if metadata_policy.classify_path(path, False) != 'operational_metadata':
        raise ResultError('PATH_DISPOSITION_INVALID', 'disposition does not name an observed cumulative delta')
    if item['disposition'] not in ('exclude_environment', 'exclude_unrelated'):
        raise ResultError('PATH_DISPOSITION_INVALID', 'disposition is not a redundant metadata exclusion')
    observation = _observation(state, path, expected)
    dirty = (state.get('entry') or {}).get('dirty', [])
    delta = gitstate.phase_delta(root, base, raw)
    if any(_overlaps(path, p) for p in [*dirty, *(c.path for c in delta)]):
        raise ResultError('PATH_DISPOSITION_INVALID', 'metadata exclusion overlaps ownership or entry dirt')
    for tree in (base, raw):
        # Exact object and all ancestor objects are inspected. A tree at the
        # named path or a blob/symlink ancestor cannot acquire no-op authority.
        parts = path.split('/')
        for length in range(1, len(parts) + 1):
            prefix = '/'.join(parts[:length])
            record = candidate._git(root, ['ls-tree', '-z', tree, '--',
                gitstate.literal_pathspec(prefix)], preserve_output=True)
            if record and (length == len(parts) or record.split(' ', 2)[1] != 'tree'):
                raise ResultError('PATH_DISPOSITION_INVALID', 'metadata disposition names or traverses a Git object')
    return {**item, 'proof_class': PROOF_CLASS, 'observation': observation}


def validate(root: Path, state: dict[str, Any], evidence: dict[str, Any]) -> None:
    """Re-derive every retained no-op; summaries cannot mint missing-path authority."""
    from .path_disposition import MAX_ENTRIES, validate_dispositions

    noops = evidence.get('path_disposition_noops', [])
    if not isinstance(noops, list) or len(noops) > MAX_ENTRIES or any(not isinstance(n, dict) for n in noops):
        raise ResultError('PATH_DISPOSITION_INVALID', 'invalid metadata no-op evidence')
    supplied = [{'path': n.get('path'), 'disposition': n.get('disposition')} for n in noops]
    validate_dispositions([*evidence['dispositions'], *supplied])
    for item, retained in zip(supplied, noops):
        if prove(root, state, evidence['entry_tree'], evidence['raw_tree'], item, retained.get('observation')) != retained:
            raise ResultError('PATH_DISPOSITION_INVALID', 'metadata no-op proof differs from retained observation')
