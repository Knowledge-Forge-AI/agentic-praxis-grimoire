"""Suppression inventory requires exact, unexpired review decisions and lexical active discovery."""

from __future__ import annotations

from datetime import date, timedelta
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

from tools.ci import scanner_suppressions as owner


def test_pending_and_expired_suppression_decisions_block(tmp_path, monkeypatch):
    row = {"path": "module.py", "line": 5, "kind": "noqa", "rule": "F401", "context": "import os"}
    policy = tmp_path / "known.json"
    monkeypatch.setattr(owner, "KNOWN_SUPPRESSIONS_FILE", policy)
    monkeypatch.setattr(owner, "scan_suppressions", lambda *args, **kwargs: [row])
    policy.write_text(json.dumps({"suppressions": [row]}))
    assert owner.build_inventory()["blocking"]
    reviewed = dict(
        row,
        disposition="accepted",
        review="fixture-review",
        reason="specific adapter import contract",
        owner="maintainer",
        expiry=(date.today() + timedelta(days=1)).isoformat(),
    )
    policy.write_text(json.dumps({"suppressions": [reviewed]}))
    assert not owner.build_inventory()["blocking"]
    reviewed["expiry"] = "2020-01-01"
    policy.write_text(json.dumps({"suppressions": [reviewed]}))
    assert owner.build_inventory()["blocking"]


def test_missing_inventory_and_automatic_update_are_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(owner, "KNOWN_SUPPRESSIONS_FILE", tmp_path / "missing.json")
    monkeypatch.setattr(owner, "scan_suppressions", lambda *args, **kwargs: [])
    assert owner.main([]) == 2
    with pytest.raises(SystemExit):
        owner.main(["--update-baseline"])


def test_second_occurrence_is_a_new_suppression(tmp_path, monkeypatch):
    row = {
        "path": "module.py",
        "line": 5,
        "kind": "noqa",
        "rule": "F401",
        "context": "import os",
        "disposition": "accepted",
        "review": "fixture-review",
        "reason": "contract",
        "owner": "maintainer",
        "expiry": (date.today() + timedelta(days=1)).isoformat(),
    }
    policy = tmp_path / "known.json"
    policy.write_text(json.dumps({"suppressions": [row]}))
    monkeypatch.setattr(owner, "KNOWN_SUPPRESSIONS_FILE", policy)
    curr1 = dict(row)
    curr2 = dict(row, line=8)
    monkeypatch.setattr(owner, "scan_suppressions", lambda *args, **kwargs: [curr1, curr2])
    inv = owner.build_inventory()
    assert inv["added"] == [curr2]
    assert len(inv["unchanged"]) == 1


def test_workflow_suppressions_are_included(tmp_path, monkeypatch):
    workflow = tmp_path / ".github/workflows/check.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("# zizmor:ignore[unpinned-uses]\n- uses: actions/checkout@v4\n")
    monkeypatch.setattr(owner, "ROOT", tmp_path)
    monkeypatch.setattr(
        owner.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(stdout=".github/workflows/check.yml\n"),
    )
    assert owner.scan_suppressions() == [
        {
            "path": ".github/workflows/check.yml",
            "line": 1,
            "kind": "zizmor_ignore",
            "rule": "unpinned-uses",
            "context": "- uses: actions/checkout@v4",
        }
    ]


def test_broadened_suppression_is_visible_and_blocking(tmp_path, monkeypatch):
    row = {
        "path": "module.py",
        "line": 5,
        "kind": "noqa",
        "rule": "F401",
        "context": "import os",
        "disposition": "accepted",
        "review": "fixture-review",
        "reason": "contract",
        "owner": "maintainer",
        "expiry": (date.today() + timedelta(days=1)).isoformat(),
    }
    policy = tmp_path / "known.json"
    policy.write_text(json.dumps({"suppressions": [row]}))
    monkeypatch.setattr(owner, "KNOWN_SUPPRESSIONS_FILE", policy)
    for rule in ("F401,F841", "*"):
        changed = dict(row, rule=owner.normalize_rule(rule))
        monkeypatch.setattr(owner, "scan_suppressions", lambda *args, c=changed, **kwargs: [c])
        result = owner.build_inventory()
        assert result["blocking"]
        assert result["broadened"] == [{"previous": row, "current": changed}]


def test_unreadable_tracked_input_is_tool_failure(tmp_path, monkeypatch, capsys):
    source = tmp_path / "module.py"
    source.write_text("pass\n")
    monkeypatch.setattr(owner, "ROOT", tmp_path)
    monkeypatch.setattr(owner.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout="module.py\n"))
    original = Path.read_text

    def read(path, *args, **kwargs):
        if path == source:
            raise OSError("fixture read failure")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read)
    assert owner.main([]) == 2
    assert json.loads(capsys.readouterr().out)["classification"] == "tool-failure"


def test_strings_vs_directives_python(tmp_path, monkeypatch):
    src = tmp_path / "test_strings.py"
    src.write_text(
        '"""Docstring containing # noqa: E402 and # type: ignore."""\n'
        's = "literal with # noqa: F401"\n'
        'msg = f"# nosemgrep: some-rule inside fstring"\n'
        'import os  # noqa: F401\n'
    )
    monkeypatch.setattr(owner, "ROOT", tmp_path)
    monkeypatch.setattr(owner.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout="test_strings.py\n"))
    supps = owner.scan_suppressions()
    # Only line 4 active comment is found; strings on lines 1, 2, 3 are ignored
    assert len(supps) == 1
    assert supps[0]["line"] == 4
    assert supps[0]["kind"] == "noqa"
    assert supps[0]["rule"] == "F401"
    assert supps[0]["context"].startswith("sha256:")


def test_strings_vs_directives_go(tmp_path, monkeypatch):
    src = tmp_path / "test.go"
    src.write_text(
        'package main\n'
        'func main() {\n'
        '    s := "// nolint:errcheck inside string"\n'
        '    raw := `// nolint:govet inside raw`\n'
        '    fmt.Println(s, raw) // nolint:errcheck\n'
        '}\n'
    )
    monkeypatch.setattr(owner, "ROOT", tmp_path)
    monkeypatch.setattr(owner.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout="test.go\n"))
    supps = owner.scan_suppressions()
    assert len(supps) == 1
    assert supps[0]["line"] == 5
    assert supps[0]["kind"] == "nolint_go"
    assert supps[0]["rule"] == "errcheck"
    assert supps[0]["context"] == "fmt.Println(s, raw)"


def test_strings_vs_directives_yaml(tmp_path, monkeypatch):
    src = tmp_path / "check.yml"
    src.write_text(
        'name: "CI with # actionlint-disable inside string"\n'
        'description: \'# zizmor:ignore[unpinned] in single quotes\'\n'
        'run: echo "hello" # actionlint-disable-line\n'
    )
    monkeypatch.setattr(owner, "ROOT", tmp_path)
    monkeypatch.setattr(owner.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout="check.yml\n"))
    supps = owner.scan_suppressions()
    assert len(supps) == 1
    assert supps[0]["line"] == 3
    assert supps[0]["kind"] == "actionlint_disable"
    assert supps[0]["context"] == 'run: echo "hello"'


def test_shebang_script_tokenization(tmp_path, monkeypatch):
    src = tmp_path / "bin" / "tool"
    src.parent.mkdir(parents=True)
    src.write_text(
        '#!/usr/bin/env python3\n'
        '"""Docstring # noqa: E402."""\n'
        'msg = "# noqa: E501 in string"\n'
        'from lib import helper  # noqa: E402\n'
    )
    monkeypatch.setattr(owner, "ROOT", tmp_path)
    monkeypatch.setattr(owner.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout="bin/tool\n"))
    supps = owner.scan_suppressions()
    assert len(supps) == 1
    assert supps[0]["line"] == 4
    assert supps[0]["kind"] == "noqa"
    assert supps[0]["rule"] == "E402"
    assert supps[0]["context"].startswith("sha256:")


def test_executable_fixtures_are_not_exempt(tmp_path, monkeypatch):
    fixture = tmp_path / "src" / "test" / "fixtures" / "sample.py"
    fixture.parent.mkdir(parents=True)
    fixture.write_text("import sys  # noqa: F401\n")
    rel_path = "src/test/fixtures/sample.py"
    monkeypatch.setattr(owner, "ROOT", tmp_path)
    monkeypatch.setattr(owner.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout=f"{rel_path}\n"))
    supps = owner.scan_suppressions()
    assert len(supps) == 1
    assert supps[0]["path"] == rel_path
    assert supps[0]["kind"] == "noqa"
    assert supps[0]["rule"] == "F401"


def test_movement_with_unchanged_context_stays_unchanged(tmp_path, monkeypatch):
    known_entry = {
        "path": "module.py",
        "line": 5,
        "kind": "noqa",
        "rule": "F401",
        "context": "import os",
        "disposition": "accepted",
        "review": "fixture-review",
        "reason": "contract requirement",
        "owner": "maintainer",
        "expiry": "2026-12-31",
    }
    policy = tmp_path / "known.json"
    policy.write_text(json.dumps({"suppressions": [known_entry]}))
    monkeypatch.setattr(owner, "KNOWN_SUPPRESSIONS_FILE", policy)

    # Line moved from 5 to 55, but context is identical
    moved_entry = dict(known_entry, line=55)
    monkeypatch.setattr(owner, "scan_suppressions", lambda *args, **kwargs: [moved_entry])

    inv = owner.build_inventory()
    assert not inv["blocking"]
    assert inv["added"] == []
    assert inv["removed"] == []
    assert len(inv["unchanged"]) == 1
    assert inv["unchanged"][0]["line"] == 55


def test_context_changed_fails(tmp_path, monkeypatch):
    known_entry = {
        "path": "module.py",
        "line": 5,
        "kind": "noqa",
        "rule": "F401",
        "context": "import os",
        "disposition": "accepted",
        "review": "fixture-review",
        "reason": "contract requirement",
        "owner": "maintainer",
        "expiry": "2026-12-31",
    }
    policy = tmp_path / "known.json"
    policy.write_text(json.dumps({"suppressions": [known_entry]}))
    monkeypatch.setattr(owner, "KNOWN_SUPPRESSIONS_FILE", policy)

    # Context changed from "import os" to "import sys"
    changed_entry = dict(known_entry, context="import sys")
    monkeypatch.setattr(owner, "scan_suppressions", lambda *args, **kwargs: [changed_entry])

    inv = owner.build_inventory()
    assert inv["blocking"]
    assert inv["context_changed"] == [{"previous": known_entry, "current": changed_entry}]


def test_rule_normalization_exact_match(tmp_path, monkeypatch):
    known_entry = {
        "path": "module.py",
        "line": 5,
        "kind": "noqa",
        "rule": "E402, F401",
        "context": "import os",
        "disposition": "accepted",
        "review": "fixture-review",
        "reason": "contract requirement",
        "owner": "maintainer",
        "expiry": "2026-12-31",
    }
    policy = tmp_path / "known.json"
    policy.write_text(json.dumps({"suppressions": [known_entry]}))
    monkeypatch.setattr(owner, "KNOWN_SUPPRESSIONS_FILE", policy)

    # Current has reversed rule order and extra whitespace: "F401,  E402"
    current_entry = dict(known_entry, rule=owner.normalize_rule("F401,  E402"))
    monkeypatch.setattr(owner, "scan_suppressions", lambda *args, **kwargs: [current_entry])

    inv = owner.build_inventory()
    assert not inv["blocking"]
    assert len(inv["unchanged"]) == 1
    assert inv["broadened"] == []


def test_duplicate_occurrences_full_multiplicity(tmp_path, monkeypatch):
    entry1 = {
        "path": "module.py",
        "line": 5,
        "kind": "noqa",
        "rule": "F401",
        "context": "import os",
        "disposition": "accepted",
        "review": "fixture-review",
        "reason": "first import",
        "owner": "maintainer",
        "expiry": "2026-12-31",
    }
    entry2 = dict(entry1, line=10, reason="second import")
    policy = tmp_path / "known.json"
    policy.write_text(json.dumps({"suppressions": [entry1, entry2]}))
    monkeypatch.setattr(owner, "KNOWN_SUPPRESSIONS_FILE", policy)

    # Current has 2 identical occurrences
    c1 = dict(entry1)
    c2 = dict(entry2)
    monkeypatch.setattr(owner, "scan_suppressions", lambda *args, **kwargs: [c1, c2])

    inv = owner.build_inventory()
    assert not inv["blocking"]
    assert len(inv["unchanged"]) == 2

    # Current adds a 3rd identical occurrence
    c3 = dict(entry1, line=15)
    monkeypatch.setattr(owner, "scan_suppressions", lambda *args, **kwargs: [c1, c2, c3])
    inv3 = owner.build_inventory()
    assert inv3["blocking"]
    assert len(inv3["unchanged"]) == 2
    assert inv3["added"] == [c3]


def test_wildcard_approvals_rejected(tmp_path, monkeypatch):
    wildcard_entry = {
        "path": "module.py",
        "line": 5,
        "kind": "noqa",
        "rule": "*",
        "context": "import os",
        "disposition": "accepted",
        "review": "fixture-review",
        "reason": "blanket suppression",
        "owner": "maintainer",
        "expiry": "2026-12-31",
    }
    policy = tmp_path / "known.json"
    policy.write_text(json.dumps({"suppressions": [wildcard_entry]}))
    monkeypatch.setattr(owner, "KNOWN_SUPPRESSIONS_FILE", policy)
    monkeypatch.setattr(owner, "scan_suppressions", lambda *args, **kwargs: [dict(wildcard_entry)])

    inv = owner.build_inventory()
    assert inv["blocking"]
    assert len(inv["unapproved_or_expired"]) == 1


def test_bad_dates_and_corrupt_inventories_fail_closed(tmp_path, monkeypatch):
    policy = tmp_path / "known.json"
    monkeypatch.setattr(owner, "KNOWN_SUPPRESSIONS_FILE", policy)
    monkeypatch.setattr(owner, "scan_suppressions", lambda *args, **kwargs: [])

    # Bad date format
    bad_date_entry = {
        "path": "module.py",
        "kind": "noqa",
        "rule": "F401",
        "expiry": "not-a-date",
    }
    policy.write_text(json.dumps({"suppressions": [bad_date_entry]}))
    assert owner.main([]) == 2

    # Duplicate identical inventory entries
    valid_entry = {
        "path": "module.py",
        "line": 5,
        "kind": "noqa",
        "rule": "F401",
        "disposition": "accepted",
        "review": "fixture-review",
        "owner": "maintainer",
        "reason": "contract",
        "expiry": "2026-12-31",
    }
    policy.write_text(json.dumps({"suppressions": [valid_entry, valid_entry]}))
    assert owner.main([]) == 2

    # Non-dictionary root
    policy.write_text(json.dumps(["not", "a", "dict"]))
    assert owner.main([]) == 2


def test_pre_final_review_status_fails_closed(tmp_path, monkeypatch):
    base = {
        "path": "module.py",
        "line": 5,
        "kind": "noqa",
        "rule": "F401",
        "context": "import os",
        "owner": "maintainer",
        "reason": "contract",
        "expiry": "2026-12-31",
    }
    policy = tmp_path / "known.json"
    monkeypatch.setattr(owner, "KNOWN_SUPPRESSIONS_FILE", policy)
    monkeypatch.setattr(owner, "scan_suppressions", lambda *args, **kwargs: [dict(base)])

    # Pending status
    pending = dict(base, disposition="pending")
    policy.write_text(json.dumps({"suppressions": [pending]}))
    assert owner.build_inventory()["blocking"]

    # Missing concrete owner
    no_owner = dict(base, disposition="accepted",
        review="fixture-review", owner="")
    policy.write_text(json.dumps({"suppressions": [no_owner]}))
    assert owner.build_inventory()["blocking"]

    # Missing reason
    no_reason = dict(base, disposition="accepted",
        review="fixture-review", reason="")
    policy.write_text(json.dumps({"suppressions": [no_reason]}))
    assert owner.build_inventory()["blocking"]


def test_accepted_label_cannot_replace_actual_review_reference():
    row = dict(path="app.py", line=1, kind="noqa", rule="E402", context="bound",
               owner="app.py", reason="bootstrap", disposition="accepted", expiry="2099-12-31")
    assert not owner.is_entry_approved(row)
    assert not owner.is_entry_approved(row | {"review": "pending"})
    assert not owner.is_entry_approved(row | {"review": "test-review", "rule": "E402,*"})
    assert owner.is_entry_approved(row | {"review": "test-review"})


def test_lexical_rule_set_cannot_drop_a_wildcard_tail():
    source = "import module  # noqa: E402,*\n"
    row = owner.scan_python_text(source, source.splitlines(), "app.py")[0]
    assert "*" in row["rule"]
    assert not owner.is_entry_approved(row | dict(owner="app.py", reason="fixture",
        review="fixture-review", disposition="accepted", expiry="2099-12-31"))


def test_context_binds_multiline_statement_and_enclosing_function():
    def scan(source):
        return owner.scan_python_text(source, source.splitlines(), "app.py")[0]["context"]
    original = "def first():\n    from source import (\n        one,\n    )  # noqa: E402\n"
    assert scan(original) == scan("\n\n" + original)
    assert scan(original) != scan(original.replace("one,", "two,"))
    assert scan(original) != scan(original.replace("def first", "def second"))


@pytest.mark.parametrize("document", [
    '{"suppressions": [], "suppressions": []}',
    '{"suppressions": [], "schema": "unknown"}',
    '{"suppressions": [], "allow_all": true}',
])
def test_malformed_inventory_cannot_pass_as_empty(tmp_path, monkeypatch, document):
    monkeypatch.setattr(owner, "scan_suppressions", lambda *args, **kwargs: [])
    path = tmp_path / "known.json"
    path.write_text(document)
    with pytest.raises(ValueError):
        owner.build_inventory(known_file=path)


def test_build_inventory_forwards_root_to_scan_suppressions(tmp_path, monkeypatch):
    observed_root = []

    def fake_scan(root=None):
        observed_root.append(root)
        return []

    policy = tmp_path / "known.json"
    policy.write_text(json.dumps({"suppressions": []}))
    monkeypatch.setattr(owner, "scan_suppressions", fake_scan)
    custom_root = tmp_path / "custom"
    custom_root.mkdir()
    owner.build_inventory(known_file=policy, root=custom_root)
    assert observed_root == [custom_root]
