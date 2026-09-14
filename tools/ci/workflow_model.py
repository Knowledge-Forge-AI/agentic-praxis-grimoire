"""Read APGR JSON-formatted workflow owners without YAML ambiguity."""
from __future__ import annotations
import json
from typing import Any

class WorkflowParseError(ValueError):
    """The owned workflow is not a strict JSON mapping."""

def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise WorkflowParseError(f"duplicate mapping key: {key}")
        result[key] = value
    return result

def parse_yaml_or_json(text: str) -> dict[str, Any]:
    """Read the JSON subset of YAML used by the shipped .yml owners.

    The compatibility name does not imply a general YAML parser. Unsupported
    YAML, duplicate keys and non-mapping roots fail before topology checks.
    """
    try:
        result = json.loads(text, object_pairs_hook=_unique_pairs)
    except (ValueError, TypeError) as error:
        raise WorkflowParseError("workflow must be a strict JSON mapping") from error
    if not isinstance(result, dict):
        raise WorkflowParseError("workflow root must be a mapping")
    return result
