"""Workflow parsing preserves on and refuses ambiguous mappings."""
import pytest
from tools.ci.workflow_model import parse_yaml_or_json, WorkflowParseError


def test_on_is_a_string_key() -> None:
    assert parse_yaml_or_json('{"on":{"pull_request":{}}}') == {"on": {"pull_request": {}}}


@pytest.mark.parametrize("value", ['{"on":{},"on":{}}', '[]', 'on: push', '{"jobs":{"a":{},"a":{}}}'])
def test_ambiguous_or_unsupported_input_refused(value: str) -> None:
    with pytest.raises(WorkflowParseError):
        parse_yaml_or_json(value)
