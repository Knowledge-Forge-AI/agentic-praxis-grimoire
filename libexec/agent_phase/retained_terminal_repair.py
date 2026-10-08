"""Read a recorded, successful formatting repair without executing it.

Called only inside native retained-source validation; archive/source-manifest,
Git, ownership and lifecycle validation remain with their existing owners.
No current roster or installed provider is consulted for historical evidence.
"""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
from typing import Any


def _json(path: Path) -> dict[str, Any]:
    def pairs(items):
        value = {}
        for k, v in items:
            if k in value:
                raise ValueError(f'duplicate evidence key: {k}')
            value[k] = v
        return value
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'retained repair evidence missing or not a regular file: {path.name}')
    value = json.loads(path.read_bytes(), object_pairs_hook=pairs)
    if not isinstance(value, dict):
        raise ValueError(f'retained repair evidence is not an object: {path.name}')
    return value


def read_recorded_repair(source: Path, state: dict[str, Any], terminal: str,
                         nonce: str, original_stdout: bytes):
    """Return the same strict result accepted by an existing auxiliary repair.

    No repair record means the caller keeps its original strict parse behavior.
    A claimed successful repair must cross-bind its recorded bytes and result;
    neither a success Boolean nor a stand-alone normalized JSON is enough.
    """
    from . import result as result_module
    from . import result_repair as repair_module
    record = state.get('result_repair')
    if record is None:
        return None
    if not isinstance(record, dict):
        raise ValueError('retained result_repair record is not an object')
    parse_outcome = record.get('strict_parse_outcome')
    if parse_outcome not in ('parsed', 'parsed_completed'):
        if state.get('terminal_result_validated') and state.get('semantic_outcome') == 'completed':
            raise ValueError('completed semantics disagree with an unsuccessful recorded repair')
        return None
    if (record.get('operation') != 'result-repair'
            or record.get('one_shot') is not True
            or record.get('semantic_work_replayed') is not False
            or record.get('source_terminal_stage') != terminal
            or state.get('terminal_result_validated') is not True):
        raise ValueError('retained repair lacks the original formatting-only authority')
    prefix = 'result-repair'
    prompt = (source / f'{prefix}.prompt.md').read_bytes()
    output = (source / f'{prefix}.stdout.md').read_bytes()
    stderr = (source / f'{prefix}.stderr.log').read_bytes()
    meta = _json(source / f'{prefix}.meta.json')
    transport = state.get('result_repair_transport')
    if not isinstance(transport, dict):
        raise ValueError('retained repair transport record is missing')
    def digest(raw): return hashlib.sha256(raw).hexdigest()
    if (meta.get('stage') != 'result_repair'
            or meta.get('role') != 'auxiliary_formatter'
            or meta.get('invocation_kind') != 'auxiliary_result_repair'
            or meta.get('exit_code') != 0
            or meta.get('prompt_sha256') != digest(prompt)
            or meta.get('stdout_sha256') != digest(output)
            or meta.get('prompt_bytes') != len(prompt)
            or meta.get('stdout_bytes') != len(output)
            or meta.get('truncated') is not False
            or meta.get('stderr_truncated') is not False):
        raise ValueError('retained formatting repair metadata does not bind its exact streams')
    for key, expected in [('stage','result_repair'),('exit_code',0),('validated',True),
                          ('stdout_bytes',len(output)),('stderr_bytes',len(stderr)),
                          ('stdout_sha256',digest(output)),('stderr_sha256',digest(stderr)),
                          ('truncated',False),('stderr_truncated',False)]:
        if transport.get(key) != expected:
            raise ValueError(f'retained formatting repair transport mismatch: {key}')
    for key in ('provider','profile'):
        if not meta.get(key) or transport.get(key) != meta.get(key):
            raise ValueError(f'retained repair historical {key} metadata disagrees')
        if record.get('source_terminal_'+key) != meta.get(key):
            raise ValueError(f'retained repair differs from its original {key}')
    # The historical prompt and its metadata are the authority. Do not require
    # equality with today's formatter template, which may legitimately evolve.
    original_offset = prompt.find(original_stdout)
    repair_contract = prompt[original_offset + len(original_stdout):]
    repair_nonces = re.findall(
        rb'^terminal_stage: ' + re.escape(terminal.encode('ascii'))
        + rb'\nTerminal nonce: ([0-9a-f]{32})$', repair_contract, re.M,
    )
    if original_offset < 0 or len(repair_nonces) != 1:
        raise ValueError('retained repair prompt does not bind the original terminal output and nonce')
    repair_nonce = repair_nonces[0].decode('ascii')
    # In-run formatting reuses the terminal nonce. Post-hoc repair creates a
    # fresh nonce, bound by the already-verified formatter prompt and metadata.
    if parse_outcome == 'parsed' and repair_nonce != nonce:
        raise ValueError('in-run repair nonce differs from the original terminal nonce')
    parsed = result_module.parse(output, terminal, repair_nonce)
    if parse_outcome == 'parsed_completed' and not parsed.completed:
        raise ValueError('recorded completed repair did not produce a completed result')
    original_result_name = state.get('terminal_result_artifact')
    if not isinstance(original_result_name,str) or Path(original_result_name).name != original_result_name:
        raise ValueError('retained terminal artifact name is invalid')
    if (parsed.as_dict() != _json(source / f'{prefix}.result.json')
            or parsed.as_dict() != _json(source / original_result_name)):
        raise ValueError('strict repaired response disagrees with retained normalized terminal artifacts')
    if parsed.outcome != state.get('semantic_outcome'):
        raise ValueError('retained repaired outcome disagrees with semantic outcome')
    repair_module._require_inherited_dispositions(state, parsed)
    return parsed
