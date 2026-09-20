"""Source readback and subprocess-to-aggregate nonsecret reconciliation."""

import hashlib
import json
import sys
from pathlib import Path

import pytest

from tools.ci.betterleaks_dispositions import SCHEMA, load_records, reconcile, source_identity
from tools.ci.pre_review_records import ROOT, Check
from tools.ci.run_pre_review import execute_all


def test_manager_dispositions_bind_all_four_current_source_contexts():
    records = load_records(ROOT / "tools/ci/betterleaks_dispositions.json")
    assert len(records) == 4
    observations = []
    for record in records:
        lines = (ROOT / record["path"]).read_bytes().splitlines(keepends=True)
        matches = [i for i, line in enumerate(lines, 1)
                   if hashlib.sha256(line).hexdigest() == record["match_sha256"]]
        assert len(matches) == 1
        observations.append({"File": record["path"], "RuleID": record["rule"],
                             "StartLine": matches[0], "EndLine": matches[0]})
    assert reconcile(ROOT, observations, records) == {
        "observations": 4, "reviewed_nonsecret": 4, "unresolved": 0, "unmatched_dispositions": 0,
    }


@pytest.mark.parametrize("case,classification", [
    ("exact", "passed"), ("duplicate", "policy-finding"),
    ("missing", "policy-finding"), ("changed", "policy-finding"),
    ("error", "tool-failure"), ("empty-error", "tool-failure"),
    ("malformed", "tool-failure"),
])
def test_subprocess_aggregate_reconciles_without_retaining_payload(tmp_path: Path, case, classification):
    source = tmp_path / "sample.py"
    source.write_text("# fixture\nvalue = 'sensitive-output-marker'\nassert value\n")
    observation = {"File": "sample.py", "RuleID": "fixture", "StartLine": 2, "EndLine": 2,
                   "Secret": "sensitive-output-marker"}
    record = source_identity(tmp_path, observation) | {
        "reason": "Synthetic aggregate fixture.", "owner": "sample.py",
        "review": "test-only-review", "disposition": "reviewed_nonsecret",
    }
    policy = tmp_path / "tools/ci/betterleaks_dispositions.json"
    policy.parent.mkdir(parents=True)
    policy.write_text(json.dumps({"schema": SCHEMA, "records": [record]}))
    observations = [observation] * (2 if case == "duplicate" else 1)
    code = 1
    if case in {"missing", "empty-error"}:
        observations = []
        code = 0 if case == "missing" else 1
    if case == "error":
        code = 2
    if case == "changed":
        source.write_text(source.read_text().replace("# fixture", "# changed context"))
    output = "null" if case == "malformed" else json.dumps(observations)
    command = (sys.executable, "-c", f"import sys; print({output!r}); sys.exit({code})")
    check = Check("betterleaks", command, cwd=tmp_path, policy="betterleaks")
    later = Check("later", (sys.executable, "-c", "print('continued')"), cwd=tmp_path)
    results = execute_all((check, later), tmp_path / "evidence", scratch_dir=tmp_path / "scratch")
    assert results[0].classification == classification
    assert results[1].status == "passed"
    # Command attestation includes fixture arguments, so only scanner output
    # retention (after the classification header) is claimed here.
    retained = (tmp_path / "evidence/betterleaks.log").read_text().split("classification=", 1)[1]
    assert "sensitive-output-marker" not in retained
