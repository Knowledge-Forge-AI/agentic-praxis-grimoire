"""Structured publication ownership; Git observations alone do not own deletions."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any

from . import candidate, gitstate, metadata_noop
from .result import ResultError


MAX_ENTRIES = 1024
MAX_ENCODED_BYTES = 128 * 1024
DISPOSITIONS = frozenset({'phase_owned', 'exclude_environment', 'exclude_unrelated'})
SCHEMA = 'agent-phase-path-ownership-v1'


def validate_dispositions(value: Any) -> list[dict[str, str]]:
    """Validate the closed, bounded wire field before using any of its entries."""
    def invalid(detail: str) -> None:
        raise ResultError('PATH_DISPOSITION_INVALID', detail)

    if not isinstance(value, list) or len(value) > MAX_ENTRIES:
        invalid('path_dispositions must be an array of at most 1024 entries')
    try:
        encoded = json.dumps(value, ensure_ascii=False).encode('utf-8')
    except (TypeError, ValueError, UnicodeError):
        invalid('path dispositions are not UTF-8 JSON')
    if len(encoded) > MAX_ENCODED_BYTES:
        invalid('path dispositions exceed 131072 encoded bytes')
    seen = set()
    for item in value:
        if not isinstance(item, dict) or set(item) != {'path', 'disposition'}:
            invalid('each disposition must contain exactly path and disposition')
        path = item['path']
        if (not isinstance(path, str) or not path
                or any(part in ('', '.', '..') for part in path.split('/'))
                or any(ord(c) < 32 or ord(c) == 127 for c in path)
                or '\\' in path or (len(path) > 1 and path[1] == ':')):
            invalid('disposition path must be canonical literal repository-relative UTF-8')
        if path in seen:
            invalid('duplicate or contradictory path disposition')
        seen.add(path)
        if not isinstance(item['disposition'], str) or item['disposition'] not in DISPOSITIONS:
            invalid('unknown path disposition')
    return [dict(item) for item in value]


def normalize(root: Path, base: str, raw: str, dispositions: list[dict[str, str]]) -> str:
    """Restore excluded entry objects only in a private index, never the worktree."""
    excluded = [item['path'] for item in dispositions if item['disposition'] != 'phase_owned']
    if not excluded:
        return raw
    with tempfile.TemporaryDirectory(prefix='agent-phase-publication-') as scratch:
        environment = os.environ.copy()
        environment['GIT_INDEX_FILE'] = os.fspath(Path(scratch) / 'index')
        candidate._git(root, ['read-tree', raw], environment)
        for path in excluded:
            literal = gitstate.literal_pathspec(path)
            record = candidate._git(root, ['ls-tree', '-z', base, '--', literal], preserve_output=True)
            candidate._git(root, ['update-index', '--force-remove', '--', path], environment)
            if record:
                metadata, name = record.rstrip('\0').split('\t', 1)
                mode, kind, oid = metadata.split(' ')
                if name != path or kind != 'blob' or mode not in ('100644', '100755', '120000'):
                    raise ResultError('PATH_DISPOSITION_INVALID', 'excluded entry object cannot be restored')
                candidate._git(root, ['update-index', '--add', '--cacheinfo', mode, oid, path], environment)
        publication = candidate._git(root, ['write-tree'], environment)
    changed = {c.path for c in gitstate.phase_delta(root, raw, publication)}
    if not changed <= set(excluded):
        raise ResultError('PATH_DISPOSITION_INVALID', 'exclusion conflicts with another candidate object')
    return publication


def validate_evidence(root: Path, evidence: Any, state: dict[str, Any] | None = None) -> dict[str, Any]:
    """Recompute retained ownership evidence from immutable Git objects on resume."""
    fields = {
        'schema', 'entry_tree', 'raw_tree', 'publication_tree', 'dispositions',
    }
    if not isinstance(evidence, dict) or set(evidence) not in (fields, fields | {'path_disposition_noops'}) or evidence['schema'] != SCHEMA:
        raise ResultError('PATH_DISPOSITION_INVALID', 'invalid retained ownership evidence')
    dispositions = validate_dispositions(evidence['dispositions'])
    for key in ('entry_tree', 'raw_tree', 'publication_tree'):
        oid = evidence[key]
        if not isinstance(oid, str) or len(oid) != 40 or any(c not in '0123456789abcdef' for c in oid):
            raise ResultError('PATH_DISPOSITION_INVALID', 'invalid ownership tree identity')
    observed = {c.path for c in gitstate.phase_delta(root, evidence['entry_tree'], evidence['raw_tree'])}
    if any(item['path'] not in observed for item in dispositions):
        raise ResultError('PATH_DISPOSITION_INVALID', 'disposition does not name an observed cumulative delta')
    metadata_noop.validate(root, state or {}, evidence)
    if normalize(root, evidence['entry_tree'], evidence['raw_tree'], dispositions) != evidence['publication_tree']:
        raise ResultError('PATH_DISPOSITION_INVALID', 'publication tree disagrees with ownership evidence')
    return evidence


def apply(state: dict[str, Any], entry: Any, raw: str, supplied: Any) -> tuple[str, set[str], list[str]]:
    """Resolve ownership and return publication tree, exclusions and ambiguities."""
    dispositions = validate_dispositions(list(supplied))
    from . import adoption
    try:
        adoption.guard_boundary(state, entry.root, raw, dispositions)
    except adoption.AdoptionError as error:
        raise ResultError('PATH_DISPOSITION_INVALID', str(error)) from error
    native_transition = state.get("native_git_transition")
    if isinstance(native_transition, dict):
        native_paths = set(native_transition.get("changed_paths") or [])
        native_auth = state.get("native_git_authority") or {}
        allowed = set(native_auth.get("authorized_paths") or native_auth.get("paths") or [])
        if allowed and (native_paths - allowed):
            raise ResultError(
                "PATH_DISPOSITION_INVALID",
                f"native commit modified paths outside authority: {sorted(native_paths - allowed)}",
            )
    inherited = state.get('path_ownership')
    inherited_noops = {}
    base = (state.get('resume') or {}).get('source_entry_tree', entry.tree)
    if inherited is None and state.get('entry_adoption'):
        base = state['entry_adoption']['base_tree']
    if inherited is not None:
        validate_evidence(entry.root, inherited, state)
        inherited_noops = {item['path']: item['observation'] for item in inherited.get('path_disposition_noops', [])}
        base = inherited['entry_tree']
        excluded_before = [item['path'] for item in inherited['dispositions'] if item['disposition'] != 'phase_owned']
        if excluded_before:
            expected = gitstate.candidate_manifest(entry.root, base, inherited['raw_tree'], paths=excluded_before)
            if gitstate.candidate_manifest_conflicts(entry.root, raw, expected):
                raise ResultError('PATH_DISPOSITION_INVALID', 'inherited excluded observation changed')
        previous = {item['path']: item['disposition'] for item in [
            *inherited['dispositions'], *inherited.get('path_disposition_noops', []),
        ]}
        for item in dispositions:
            if item['path'] in previous and previous[item['path']] != item['disposition']:
                raise ResultError('PATH_DISPOSITION_INVALID', 'inherited disposition cannot be contradicted')
        previous.update({item['path']: item['disposition'] for item in dispositions})
        dispositions = validate_dispositions([
            {'path': path, 'disposition': disposition} for path, disposition in sorted(previous.items())
        ])
    observed = gitstate.phase_delta(entry.root, base, raw)
    observed_paths = {change.path for change in observed}
    noops = []
    eligible = []
    for item in dispositions:
        # A leaf symlink is a valid object; traversal through one is an alias.
        parent = (entry.root / item['path']).parent
        while parent != entry.root:
            if parent.is_symlink():
                raise ResultError('PATH_DISPOSITION_INVALID', 'disposition traverses a worktree alias')
            parent = parent.parent
        if item['path'] not in observed_paths or item['path'] in inherited_noops:
            noops.append(metadata_noop.prove(entry.root, state, base, raw, item, inherited_noops.get(item['path'])))
        else:
            eligible.append(item)
    dispositions = eligible
    claims = {item['path']: item['disposition'] for item in dispositions}
    from . import ownership_challenge as challenges
    if state.get('ownership_challenges') is not None:
        challenges.validate(entry.root, state)
        open_paths = {r['path'] for r in challenges.open_records(state)}
        resolved = challenges.decisions(state)
        # Free-form path dispositions cannot bypass either open observations
        # or exact ID-based decisions. Preserve metadata no-op handling above.
        dispositions = [item for item in dispositions if item['path'] not in open_paths | set(resolved)]
        for path, decision in resolved.items():
            dispositions.append({'path': path, 'disposition': decision})
        claims = {item['path']: item['disposition'] for item in dispositions}
    excluded = {path for path, disposition in claims.items() if disposition != 'phase_owned'}
    if state.get('entry_adoption'):
        unadopted_in_raw = set(state['entry_adoption'].get('unadopted_dirty_paths', [])) & observed_paths
        excluded.update(unadopted_in_raw)
        for u_path in sorted(unadopted_in_raw):
            if not any(d['path'] == u_path for d in dispositions):
                dispositions.append({'path': u_path, 'disposition': 'exclude_unrelated'})
    ambiguous = (sorted(open_paths) if state.get('ownership_challenges') is not None else
                 sorted(change.path for change in observed if change.status == 'D' and change.path not in claims))
    publication = normalize(entry.root, base, raw, dispositions)
    state['path_ownership'] = {
        'schema': SCHEMA, 'entry_tree': base, 'raw_tree': raw,
        'publication_tree': publication, 'dispositions': dispositions,
        'path_disposition_noops': noops,
    }
    state['path_dispositions'] = dispositions
    state['path_disposition_noops'] = noops
    state['excluded_paths'] = sorted(excluded)
    state['mechanical_phase_delta'] = [change._asdict() for change in observed]
    state['raw_terminal_candidate'] = {'kind': 'git_tree', 'tree': raw}
    state['publication_candidate'] = {'kind': 'git_tree', 'tree': publication}
    return publication, excluded, ambiguous
