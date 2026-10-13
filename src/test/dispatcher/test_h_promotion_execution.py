"""APG166V-H-COMPLETE1 single-start promotion-case runner.

The Codex provider is a local fake bound through the sealed runtime manifest
and the maintained provider runner.  No case can promote a skill or write the
maturity ledger; oracle outcomes are retained for later independent review.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from testing.h_eval import granted_execution, live_admission, promotion_oracles
from h_live_fixtures import ROOT, Authority, fake_provider, sealed_runtime, starts

CASE = "go-language-profile/positive/cancellation"
UNIT = f"promotion/{CASE}"
PROTECTED = ("docs/governance/skill-maturity-ledger.json", "testing/h_eval/promotion-preregistration.json",
             "skills/go-language-profile/SKILL.md")


def _digests():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in PROTECTED}


def _setup(tmp_path, monkeypatch, **provider_options):
    provider, counter = fake_provider(tmp_path / "fixture", **provider_options)
    runtime = sealed_runtime(provider, tmp_path / "home")
    authority = Authority(tmp_path, monkeypatch, runtime)
    return authority, runtime, counter


def _run(tmp_path, authorization, runtime, name="case"):
    return granted_execution.run_promotion_case(
        case_dir=tmp_path / name, source_root=ROOT, case_id=CASE,
        live_authorization=authorization, runtime_inputs=runtime,
    )


def test_case_starts_once_delivers_exact_skill_and_reads_back(tmp_path, monkeypatch):
    before = _digests()
    authority, runtime, counter = _setup(tmp_path, monkeypatch, write="fetch.go")
    authorization = authority.grant([UNIT])
    result = _run(tmp_path, authorization, runtime)
    assert starts(counter) == 1
    assert result["provider_invocations"] == 1 and result["retries"] == 0
    skill = (ROOT / "skills/go-language-profile/SKILL.md").read_bytes()
    delivered = tmp_path / "case/subject/.agents/skills/go-language-profile/SKILL.md"
    assert delivered.read_bytes() == skill
    assert result["delivery"]["sha256"] == hashlib.sha256(skill).hexdigest()
    assert result["delivery"]["unchanged_after_run"] is True
    assert result["delivery"]["global_discovery_absent_after_run"] is True
    assert "fetch.go" in result["changed_paths"]
    started = json.loads((tmp_path / "case/run/started.json").read_text())
    assert not any(part.startswith("skills.config") for part in started["argv"])
    assert result["promotion_authorized"] is False
    assert result["maturity_ledger_written"] is False
    assert result["attribution_status"] == "pending-independent-review"
    readback = granted_execution.read_case_result(tmp_path / "case")
    granted_execution.read_case_result(tmp_path / "case")
    assert readback["live_admission"]["unit_id"] == UNIT
    assert starts(counter) == 1
    assert _digests() == before


def test_same_case_cannot_start_again(tmp_path, monkeypatch):
    authority, runtime, counter = _setup(tmp_path, monkeypatch)
    authorization = authority.grant([UNIT])
    _run(tmp_path, authorization, runtime)
    with pytest.raises(live_admission.AdmissionError, match="already consumed"):
        _run(tmp_path, authorization, runtime, name="replay")
    other = authority.grant([UNIT], name="grant-b.json")
    with pytest.raises(live_admission.AdmissionError, match="another grant"):
        _run(tmp_path, other, runtime, name="alternate")
    assert not (tmp_path / "replay").exists() and not (tmp_path / "alternate").exists()
    assert starts(counter) == 1


def test_provider_error_is_retained_with_actual_count(tmp_path, monkeypatch):
    authority, runtime, counter = _setup(tmp_path, monkeypatch, exit_code=5)
    result = _run(tmp_path, authority.grant([UNIT]), runtime)
    assert starts(counter) == 1
    assert result["status"] == "incomplete"
    assert "provider transport did not complete" in result["failure"]
    assert result["provider_invocations"] == 1
    assert granted_execution.read_case_result(tmp_path / "case")["status"] == "incomplete"


def test_oracle_pass_never_promotes(tmp_path, monkeypatch):
    authority, runtime, counter = _setup(tmp_path, monkeypatch)
    monkeypatch.setattr(promotion_oracles, "evaluate_subject_directory",
                        lambda case_id, root, paths: {"status": "pass", "case_id": case_id, "double": True})
    result = _run(tmp_path, authority.grant([UNIT]), runtime)
    assert result["status"] == "complete"
    assert result["oracle"]["status"] == "pass"
    assert result["promotion_authorized"] is False and result["oracle_is_not_promotion"] is True
    assert result["maturity_ledger_written"] is False
    assert not (tmp_path / "case/graded/.agents").exists()


def test_forged_or_self_approved_case_results_are_refused(tmp_path, monkeypatch):
    authority, runtime, _counter = _setup(tmp_path, monkeypatch)
    _run(tmp_path, authority.grant([UNIT]), runtime)
    case = tmp_path / "case"
    original = json.loads((case / "result.json").read_text())
    (case / "result.json").chmod(0o600)
    (case / "result.json").write_text(json.dumps({**original, "oracle": {"status": "pass"}}, indent=2, sort_keys=True) + "\n")
    with pytest.raises(ValueError, match="identity changed"):
        granted_execution.read_case_result(case)
    for change, message in (({"promotion_authorized": True}, "promotion authority"),
                            ({"provider_invocations": 2}, "invocation"),
                            ({"live_admission": {**original["live_admission"], "ledger_sha256": "8" * 64}}, "changed")):
        (case / "integrity.json").chmod(0o600)
        (case / "integrity.json").unlink()
        (case / "result.json").unlink()
        granted_execution._persist_case(case, {**original, **change})
        with pytest.raises(ValueError, match=message):
            granted_execution.read_case_result(case)


def test_case_refused_without_grant_or_with_global_discovery(tmp_path, monkeypatch):
    authority, runtime, counter = _setup(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="admission unavailable"):
        _run(tmp_path, {"authorized": True}, runtime)
    (tmp_path / "home/.agents/skills").mkdir(parents=True)
    with pytest.raises(ValueError, match="global Codex skill discovery"):
        _run(tmp_path, authority.grant([UNIT]), runtime)
    assert not (tmp_path / "case").exists()
    assert not (authority.custody / live_admission.LEDGER).exists()
    assert starts(counter) == 0
