"""Real tracked-source and subprocess suppression approval contracts."""

import json
import subprocess
import sys

import pytest

from tools.ci import scanner_suppressions as owner


def git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def repository(tmp_path):
    git(tmp_path, "init", "-q")
    source = tmp_path / "app.py"
    source.write_text("from sample import (\n    first,\n)  # noqa: E402\n")
    git(tmp_path, "add", "app.py")
    row = owner.scan_suppressions(root=tmp_path)[0]
    record = row | {"disposition": "accepted", "review": "fixture-independent-review",
                    "reason": "Fixture bootstrap import", "owner": "app.py", "expiry": "2099-12-31"}
    known = tmp_path / "known.json"
    known.write_text(json.dumps({"suppressions": [record]}))
    return tmp_path, source, known


def run(repo, known):
    return subprocess.run([sys.executable, str(owner.ROOT / "tools/ci/scanner_suppressions.py"),
                           "--root", str(repo), "--known", str(known)],
                          cwd=repo, capture_output=True, text=True)


@pytest.mark.parametrize("change,exit_code", [
    ("none", 0), ("movement", 0), ("multiline-context", 1),
    ("rule", 1), ("duplicate", 1), ("missing-review", 1),
    ("expired", 1), ("missing-source", 2), ("corrupt", 2),
])
def test_subprocess_source_and_review_contract(repository, change, exit_code):
    repo, source, known = repository
    if change == "movement":
        source.write_text("# harmless inserted header\n\n" + source.read_text())
    elif change == "multiline-context":
        source.write_text(source.read_text().replace("first", "second"))
    elif change == "rule":
        source.write_text(source.read_text().replace("E402", "E402, F401"))
    elif change == "duplicate":
        source.write_text(source.read_text() * 2)
    elif change == "missing-source":
        source.unlink()
    elif change == "corrupt":
        known.write_text("{")
    elif change in {"missing-review", "expired"}:
        doc = json.loads(known.read_text())
        if change == "expired":
            doc["suppressions"][0]["expiry"] = "2000-01-01"
        else:
            del doc["suppressions"][0]["review"]
        known.write_text(json.dumps(doc))
    result = run(repo, known)
    assert result.returncode == exit_code, result.stdout + result.stderr
    doc = json.loads(result.stdout)
    if exit_code != 2:
        assert doc["schema"] == owner.SCHEMA_V2
        assert doc["blocking"] == bool(exit_code)
        if change == "movement":
            assert doc["unchanged"][0]["line"] == 5
    else:
        assert doc["classification"] == "tool-failure"
