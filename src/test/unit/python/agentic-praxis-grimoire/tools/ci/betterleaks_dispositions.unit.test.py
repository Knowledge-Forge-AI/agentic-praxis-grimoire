"""Exact nonsecret identities, multiplicity and malformed approval refusal."""

import json

import pytest

from tools.ci.betterleaks_dispositions import SCHEMA, load_records, reconcile, source_identity


def fixture_record(tmp_path):
    source = tmp_path / "fixture.py"
    source.write_text("# redaction fixture\nvalue = 'synthetic-input'\nassert value\n")
    observation = {"File": "fixture.py", "RuleID": "synthetic-rule", "StartLine": 2, "EndLine": 2}
    record = source_identity(tmp_path, observation) | {
        "reason": "Synthetic fixture tests redaction.", "owner": "fixture.py",
        "review": "test-only-review", "disposition": "reviewed_nonsecret",
    }
    return source, observation, record


def test_exact_match_retains_raw_count_and_duplicate_blocks(tmp_path):
    _, observation, record = fixture_record(tmp_path)
    assert reconcile(tmp_path, [observation], [record]) == {
        "observations": 1, "reviewed_nonsecret": 1, "unresolved": 0, "unmatched_dispositions": 0,
    }
    result = reconcile(tmp_path, [observation, observation], [record])
    assert result["observations"] == 2
    assert result["reviewed_nonsecret"] == result["unresolved"] == 1


@pytest.mark.parametrize("change", ["context", "match", "rule"])
def test_altered_context_match_or_rule_does_not_inherit(tmp_path, change):
    source, observation, record = fixture_record(tmp_path)
    if change == "rule":
        observation["RuleID"] = "other-rule"
    else:
        source.write_text(source.read_text().replace(
            "redaction fixture" if change == "context" else "synthetic-input", "changed"
        ))
    result = reconcile(tmp_path, [observation], [record])
    assert result["unresolved"] == result["unmatched_dispositions"] == 1


def test_missing_observation_requires_investigation(tmp_path):
    _, _, record = fixture_record(tmp_path)
    assert reconcile(tmp_path, [], [record])["unmatched_dispositions"] == 1


def test_function_scope_cannot_change_outside_nearby_lines(tmp_path):
    source = tmp_path / "fixture.py"
    body = "def redaction_test():\n" + "    # padding\n" * 5 + "    value = 'synthetic-input'\n"
    source.write_text(body)
    observation = {"File":"fixture.py", "RuleID":"synthetic-rule", "StartLine":7, "EndLine":7}
    original = source_identity(tmp_path, observation)
    source.write_text(body.replace("redaction_test", "different_owner"))
    changed = source_identity(tmp_path, observation)
    assert original["match_sha256"] == changed["match_sha256"]
    assert original["context_sha256"] != changed["context_sha256"]
    source.write_text("\n" + body)
    assert source_identity(tmp_path, observation | {"StartLine":8, "EndLine":8}) == original


@pytest.mark.parametrize("change", ["duplicate", "reason", "review", "digest", "schema", "unknown", "json-key"])
def test_bad_inventory_refused(tmp_path, change):
    _, _, record = fixture_record(tmp_path)
    document = {"schema": SCHEMA, "records": [record]}
    if change == "duplicate":
        document["records"].append(record)
    elif change in {"reason", "review"}:
        record[change] = " "
    elif change == "digest":
        record["match_sha256"] = "bad"
    elif change == "schema":
        document["schema"] = "unknown"
    elif change == "unknown":
        record["allow_all"] = True
    policy = tmp_path / "policy.json"
    policy.write_text(json.dumps(document) if change != "json-key" else '{"schema":1,"schema":2}')
    with pytest.raises(ValueError):
        load_records(policy)


@pytest.mark.parametrize("path", ["", ".", "../fixture.py", "/fixture.py", "./fixture.py", "missing.py"])
def test_unbound_source_refused(tmp_path, path):
    _, observation, _ = fixture_record(tmp_path)
    observation["File"] = path
    with pytest.raises((OSError, ValueError)):
        source_identity(tmp_path, observation)


def test_symlink_source_refused(tmp_path):
    source, observation, _ = fixture_record(tmp_path)
    link = tmp_path / "link.py"
    link.symlink_to(source)
    observation["File"] = link.name
    with pytest.raises(ValueError, match="symlink"):
        source_identity(tmp_path, observation)
