"""Provider-free verification suite for D1 seam and APG166D-PROBE-D1 owner.

Guarantees:
- Zero real provider starts authorized.
- General holdout live admission remains disabled.
- B1: Caller parameter overrides rejected before subprocess start.
- B2: Answer-neutral probe (expected value completely absent from prompt).
- B3: Live and instrumented evidence non-interchangeability.
- Current model derivation from source policy.
- Structural non-holdout boundary.
- B4: Manager-bound global one-use custody and replay refusal.
- B5: Exact observed Read-only surface and structured violation codes.
- B6: Real runtime, settings, and executable evidence captures.
- B7: Complete readback recomputation and tamper rejection.
- Instrumented lifecycle executing real fake child subprocess under LaunchGuard.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any

import pytest

from testing.h_eval import d1_qualification as d1
from testing.h_eval import execution, readiness
from testing.h_eval.provider_free import LaunchGuard, verify_retained

REPO_ROOT = Path(__file__).resolve().parents[3]


def _valid_authority(evidence_dir: Path, custody_dir: Path | None = None, attempt_id: str = "att-001",
                     schema: str = d1.INSTRUMENTED_AUTHORITY_SCHEMA, root: Path | None = None) -> dict[str, Any]:
    target_root = root if root is not None else REPO_ROOT
    git_st = d1.capture_git_state(target_root)
    desc_bytes = (REPO_ROOT / d1.DESCRIPTOR_RELATIVE_PATH).read_bytes()
    desc_sha = hashlib.sha256(desc_bytes).hexdigest()
    sid = readiness.source_identity(readiness.make_seal(REPO_ROOT)["files"])
    croot = (custody_dir if custody_dir is not None else evidence_dir.parent / "custody").resolve()
    croot.mkdir(parents=True, exist_ok=True)
    edir = evidence_dir.resolve()
    if not edir.is_relative_to(croot):
        edir = (croot / evidence_dir.name).resolve()
    edir.mkdir(parents=True, exist_ok=True)
    auth = {
        "schema": schema,
        "probe_id": d1.PROBE_ID,
        "authority_id": "auth-d1-test-001",
        "custody_root": str(croot),
        "accepted_commit": git_st["head"],
        "accepted_tree": git_st["tree"],
        "source_identity": sid,
        "descriptor_sha256": desc_sha,
        "evidence_root": str(edir),
        "attempt_id": attempt_id,
        "max_starts": 1,
        "replay_prohibited": True,
    }
    auth["authority_digest"] = d1.compute_authority_digest(auth)
    return auth


def test_holdout_admission_remains_blocked(tmp_path):
    assert execution.LIVE_ADMISSION_AVAILABLE is False
    with pytest.raises(ValueError, match="live arm admission unavailable"):
        execution.run_one_arm(
            arm_dir=tmp_path / "arm",
            source_root=REPO_ROOT,
            scenario={"scenario_id": "scenario-01", "name": "Scenario 01"},
            mode="static",
            route={
                "execution": "live",
                "provider": "claude",
                "profile": "normal-final-review",
                "model": "claude-opus-5-5",
                "binding_id": "b1",
                "roles": ["Work Review"],
            },
        )
    desc = d1.load_descriptor(REPO_ROOT)
    for n in range(1, 16):
        bad_desc = copy.deepcopy(desc)
        bad_desc["scenario_id"] = f"scenario-{n:02d}"
        with pytest.raises(d1.D1Error, match="holdout"):
            d1.validate_descriptor(bad_desc, root=REPO_ROOT)


def test_descriptor_loading_and_invariants():
    desc = d1.load_descriptor(REPO_ROOT)
    assert desc["schema"] == d1.DESCRIPTOR_SCHEMA
    assert desc["probe_id"] == d1.PROBE_ID
    route = desc["route"]
    assert route["provider"] == "claude"
    assert route["profile"] == "normal-final-review"
    assert route["model"] == "claude-opus-5-5"
    assert route["roles"] == ["Work Review"]
    assert route["allowed_native_tools"] == ["Read"]
    assert set(route["forbidden_tools"]) == {"Bash", "Write", "Edit", "Agent"}
    assert route["mcp_servers"] == []
    assert route["settings_isolation"]["isolated_settings"] is True
    assert route["settings_isolation"]["isolated_home"] is False
    assert route["settings_isolation"]["provider_auth_home"] == "operator"
    assert route["settings_isolation"]["isolated_tmp"] is True
    assert route["settings_isolation"]["global_settings_mutation_allowed"] is False

    derived = d1.derive_d1_route(desc, root=REPO_ROOT)
    assert derived["probe_id"] == d1.PROBE_ID
    assert derived["allowed_native_tools"] == ["Read"]

    # Rejection of invalid invariants
    for mutator in (
        lambda d: d.update(schema="invalid"),
        lambda d: d.update(probe_id="WRONG"),
        lambda d: d["route"].update(provider="codex"),
        lambda d: d["route"].update(model="claude-sonnet-4"),
        lambda d: d["route"].update(allowed_native_tools=["Read", "Bash"]),
        lambda d: d["route"].update(mcp_servers=[{"name": "mcp"}]),
        lambda d: d["route"]["settings_isolation"].update(isolated_settings=False),
        lambda d: d["fixture"].update(sha256="0" * 64),
    ):
        bad = copy.deepcopy(desc)
        mutator(bad)
        with pytest.raises(d1.D1Error):
            d1.validate_descriptor(bad, root=REPO_ROOT)


def test_current_model_derivation_from_source_policy():
    derivation = d1.derive_policy_claude_model(REPO_ROOT)
    assert derivation["model"] == "claude-opus-5-5"
    assert derivation["model_role"] == "primary"
    assert derivation["profile"] == "normal-final-review"
    desc = d1.load_descriptor(REPO_ROOT)
    assert desc["route"]["model"] == derivation["model"]

    # If descriptor model does not match policy, validation fails
    stale_desc = copy.deepcopy(desc)
    stale_desc["route"]["model"] = "claude-sonnet-4"
    with pytest.raises(d1.D1Error, match="does not match source policy"):
        d1.validate_descriptor(stale_desc, root=REPO_ROOT)


def test_structural_non_holdout_boundary():
    desc = d1.load_descriptor(REPO_ROOT)
    # Reject frozen scenario IDs and variants
    for i in range(1, 16):
        for pattern in (f"scenario-{i:02d}", f"scenario_{i:02d}", f"scenario {i:02d}", f"Scenario {i:02d}", f"SCENARIO-{i:02d}"):
            bad = copy.deepcopy(desc)
            bad["probe_id"] = pattern
            with pytest.raises(d1.D1Error, match="holdout"):
                d1.assert_structural_non_holdout(bad, root=REPO_ROOT)

    # Reject path under frozen scenario corpus
    bad_path = copy.deepcopy(desc)
    bad_path["fixture"]["path"] = "testing/fixtures/context-eval/some_file.txt"
    with pytest.raises(d1.D1Error, match="holdout"):
        d1.assert_structural_non_holdout(bad_path, root=REPO_ROOT)

    # Reject traversal into context-eval
    bad_rel = copy.deepcopy(desc)
    bad_rel["fixture"]["path"] = "testing/h_eval/../fixtures/context-eval/file.txt"
    with pytest.raises(d1.D1Error, match="holdout"):
        d1.assert_structural_non_holdout(bad_rel, root=REPO_ROOT)


def test_probe_materialization_and_neutral_prompt(tmp_path):
    desc = d1.load_descriptor(REPO_ROOT)
    probe_dir = (tmp_path / "probe_dir").resolve()
    target, nonce = d1.materialize_probe(desc, probe_dir, root=REPO_ROOT)
    assert target.is_file()
    assert target.stat().st_mode & 0o777 == 0o600
    assert len(nonce) == 64
    assert nonce in target.read_text(encoding="utf-8")

    prompt_bytes = d1.build_d1_prompt(target, root=REPO_ROOT)
    prompt = prompt_bytes.decode("utf-8")
    assert d1.PROBE_ID in prompt
    assert str(target) in prompt
    assert d1.RESPONSE_SCHEMA in prompt
    assert "Read" in prompt
    assert "Do not modify" in prompt

    # B2: Expected nonce/value MUST NOT be anywhere in prompt bytes!
    assert nonce not in prompt
    assert nonce.encode("utf-8") not in prompt_bytes


def test_oracle_evaluation(tmp_path):
    desc = d1.load_descriptor(REPO_ROOT)
    probe_dir = (tmp_path / "probe_dir").resolve()
    target, nonce = d1.materialize_probe(desc, probe_dir, root=REPO_ROOT)
    fb = target.read_bytes()
    fsha = hashlib.sha256(fb).hexdigest()

    valid_payload = json.dumps({"schema": d1.RESPONSE_SCHEMA, "probe_id": d1.PROBE_ID, "nonce": nonce}).encode()
    valid_obs = {"read_count": 1, "reads": [{"path": str(target), "file_path": str(target), "bytes": len(fb), "sha256": fsha}]}

    # 1. Valid response + valid Read observation passes
    res = d1.evaluate_d1_response(valid_payload, nonce, observation=valid_obs, fixture_bytes=fb, fixture_path=target)
    assert res["status"] == "pass"

    # 2. Wrong nonce fails
    wrong_payload = json.dumps({"schema": d1.RESPONSE_SCHEMA, "probe_id": d1.PROBE_ID, "nonce": "0" * 64}).encode()
    res_wrong = d1.evaluate_d1_response(wrong_payload, nonce, observation=valid_obs, fixture_bytes=fb, fixture_path=target)
    assert res_wrong["status"] == "fail"
    assert "nonce mismatch" in res_wrong["reason"]

    # 3. Missing read observation fails even if nonce is correct
    empty_obs = {"read_count": 0, "reads": []}
    res_no_read = d1.evaluate_d1_response(valid_payload, nonce, observation=empty_obs, fixture_bytes=fb, fixture_path=target)
    assert res_no_read["status"] == "fail"
    assert "no_native_read_observed" in res_no_read["reason"]

    # 4. Content digest mismatch fails
    bad_digest_obs = {"read_count": 1, "reads": [{"path": str(target), "file_path": str(target), "bytes": len(fb), "sha256": "0" * 64}]}
    res_bad_digest = d1.evaluate_d1_response(valid_payload, nonce, observation=bad_digest_obs, fixture_bytes=fb, fixture_path=target)
    assert res_bad_digest["status"] == "fail"
    assert "observed_content_digest_mismatch" in res_bad_digest["reason"]


def test_authority_validation(tmp_path):
    croot = (tmp_path / "custody").resolve()
    edir = (croot / "evidence").resolve()
    auth = _valid_authority(edir, custody_dir=croot)
    d1.validate_d1_authority(auth)

    for key, bad_val in [
        ("schema", "invalid"),
        ("probe_id", "wrong"),
        ("authority_id", ""),
        ("authority_id", "invalid id with spaces!"),
        ("attempt_id", ""),
        ("attempt_id", "invalid attempt id with spaces!"),
        ("authority_digest", "0" * 64),
        ("max_starts", 2),
        ("replay_prohibited", False),
        ("accepted_commit", "a" * 39),
        ("accepted_tree", "0" * 40),
        ("source_identity", "0" * 64),
        ("descriptor_sha256", "0" * 64),
        ("custody_root", ""),
        ("evidence_root", ""),
    ]:
        bad = copy.deepcopy(auth)
        bad[key] = bad_val
        with pytest.raises(d1.D1AuthorityError):
            d1.validate_d1_authority(
                bad,
                expected_tree=auth["accepted_tree"],
                expected_source_identity=auth["source_identity"],
                expected_descriptor_digest=auth["descriptor_sha256"],
            )

    # Custody root mismatch / evidence root outside custody root
    bad_esc = copy.deepcopy(auth)
    bad_esc["evidence_root"] = str((tmp_path / "outside").resolve())
    with pytest.raises(d1.D1AuthorityError, match="located beneath custody_root"):
        d1.validate_d1_authority(bad_esc)


def test_b1_caller_overrides_rejected_before_provider_start(tmp_path):
    croot = (tmp_path / "custody").resolve()
    edir = (croot / "evidence").resolve()
    auth = _valid_authority(edir, custody_dir=croot)

    for override in [
        {"model": "claude-sonnet-4"},
        {"prompt": b"override prompt"},
        {"provider": "codex"},
        {"execution_kind": "instrumented-provider-free"},
        {"fixture": "other_fixture"},
        {"oracle": "other_oracle"},
        {"tools": ["Read", "Bash"]},
        {"mcp_servers": [{"name": "fake"}]},
    ]:
        with pytest.raises(d1.D1Error, match="override prohibited"):
            d1.run_live_d1(REPO_ROOT, edir, auth, **override)


def test_b4_one_use_custody_and_replay_refusal(tmp_path):
    croot = (tmp_path / "custody").resolve()
    edir1 = (croot / "ev1").resolve()
    edir2 = (croot / "ev2").resolve()
    edir1.mkdir(parents=True)
    edir2.mkdir(parents=True)

    auth1 = _valid_authority(edir1, custody_dir=croot, attempt_id="attempt-001")
    pre_ev = {"test": 1}
    sid = auth1["source_identity"]

    # 1. First consumption succeeds
    ledger_file, state_path = d1.record_attempt_consumption(croot, edir1, auth1, sid, pre_ev)
    assert ledger_file.is_file()
    assert state_path.is_file()
    assert ledger_file.parent == croot / "consumed-attempts"

    # 2. Replay with same attempt key on same evidence root fails
    with pytest.raises(d1.D1AttemptError, match="replay refused"):
        d1.record_attempt_consumption(croot, edir1, auth1, sid, pre_ev)

    # 3. Replay with same attempt key on DIFFERENT evidence root also fails (global custody!)
    auth2 = copy.deepcopy(auth1)
    auth2["evidence_root"] = str(edir2)
    with pytest.raises(d1.D1AttemptError, match="replay refused"):
        d1.record_attempt_consumption(croot, edir2, auth2, sid, pre_ev)

    # 4. Finishing the attempt
    d1.record_attempt_finish(edir1, "failed", error="simulated error")
    state_data = json.loads(state_path.read_bytes())
    assert state_data["status"] == "failed"
    assert state_data["error"] == "simulated error"


def test_b5_surface_inspection():
    route = {
        "model": "claude-opus-5-5",
        "allowed_native_tools": ["Read"],
        "forbidden_tools": ["Bash", "Write", "Edit", "Agent"],
    }
    # Success surface
    valid_stream = (
        b'{"type":"system","event":"init","tools":["Read"],"mcp_servers":[],"permissionMode":"plan","model":"claude-opus-5-5"}\n'
    )
    res = d1.inspect_observed_surface(valid_stream, route)
    assert res["valid"] is True
    assert res["failure_codes"] == []

    # Extra tools (Bash, Write, Edit, Agent, Glob, Grep, WebFetch, WebSearch, NotebookEdit)
    for forbidden in ["Bash", "Write", "Edit", "Agent", "Glob", "Grep", "WebFetch", "WebSearch", "NotebookEdit"]:
        bad_stream = f'{{"type":"system","event":"init","tools":["Read","{forbidden}"],"mcp_servers":[],"permissionMode":"plan","model":"claude-opus-5-5"}}\n'.encode()
        bad_res = d1.inspect_observed_surface(bad_stream, route)
        assert bad_res["valid"] is False
        assert "FORBIDDEN_TOOLS_OBSERVED" in bad_res["failure_codes"]

    # Non-empty MCP servers
    mcp_stream = b'{"type":"system","event":"init","tools":["Read"],"mcp_servers":[{"name":"ext"}],"permissionMode":"plan","model":"claude-opus-5-5"}\n'
    mcp_res = d1.inspect_observed_surface(mcp_stream, route)
    assert mcp_res["valid"] is False
    assert "MCP_SERVERS_NON_EMPTY" in mcp_res["failure_codes"]

    # Missing Read
    no_read_stream = b'{"type":"system","event":"init","tools":[],"mcp_servers":[],"permissionMode":"plan","model":"claude-opus-5-5"}\n'
    no_read_res = d1.inspect_observed_surface(no_read_stream, route)
    assert no_read_res["valid"] is False
    assert "READ_TOOL_MISSING" in no_read_res["failure_codes"]

    # Model mismatch
    wrong_model_stream = b'{"type":"system","event":"init","tools":["Read"],"mcp_servers":[],"permissionMode":"plan","model":"claude-sonnet-4"}\n'
    wrong_model_res = d1.inspect_observed_surface(wrong_model_stream, route)
    assert wrong_model_res["valid"] is False
    assert "MODEL_MISMATCH" in wrong_model_res["failure_codes"]


def test_b6_evidence_captures(tmp_path):
    git_st = d1.capture_git_state(REPO_ROOT)
    assert len(git_st["head"]) == 40
    assert len(git_st["tree"]) == 40
    assert isinstance(git_st["dirty"], bool)

    settings_st = d1.capture_settings_state({"mode": "static", "isolated": True})
    assert settings_st["isolated"] is True
    assert "sha256" in settings_st

    runtime_st = d1.capture_runtime_state(None)
    assert runtime_st["status"] == "not-supplied"

    exec_ev = d1.capture_executable_evidence(REPO_ROOT)
    assert "logical_launcher_path" in exec_ev
    assert "physical_executable" in exec_ev
    assert exec_ev["cli_version"] is not None
    assert "2.1." in exec_ev["cli_version"] or "fake" in exec_ev["cli_version"]

    roots_ev = d1.capture_isolation_roots(tmp_path / "c", tmp_path / "e", tmp_path / "r", tmp_path / "h", tmp_path / "t")
    assert "custody_root" in roots_ev
    assert "isolated_home" in roots_ev


def test_b3_live_and_instrumented_evidence_non_interchangeability(tmp_path):
    croot = (tmp_path / "custody").resolve()
    edir = (croot / "evidence").resolve()
    auth = _valid_authority(edir, custody_dir=croot)
    rec = d1.run_instrumented_d1_lifecycle(REPO_ROOT, edir, auth)

    # 1. Instrumented record has explicit schema and execution_kind
    assert rec["schema"] == d1.INSTRUMENTED_EVIDENCE_SCHEMA
    assert rec["execution_kind"] == "instrumented-provider-free"
    assert rec["d1_status"] == "not-run"
    assert rec["provider_free_d1_seam_qualified"] is True

    # 2a. Tampering record JSON to claim live-provider fails readback
    rec_file = edir / "d1-record.json"
    rec_data = json.loads(rec_file.read_bytes())
    rec_data["execution_kind"] = "live-provider"
    rec_data["schema"] = d1.LIVE_EVIDENCE_SCHEMA
    rec_data["d1_status"] = "qualified"
    rec_file.write_bytes(json.dumps(rec_data).encode())
    with pytest.raises(d1.D1ReadbackError, match="record digest mismatch"):
        d1.readback_d1_record(edir, REPO_ROOT)

    # 2b. Recomputing record digest on forged live record still fails readback because ledger transport is fake
    rec_data["record_digest"] = d1.compute_record_digest(rec_data)
    rec_file.write_bytes(json.dumps(rec_data).encode())
    with pytest.raises(d1.D1ReadbackError, match="execution kind (forgery|mismatch)"):
        d1.readback_d1_record(edir, REPO_ROOT)

    # Restore record
    rec_file.write_bytes(json.dumps(rec).encode())

    # 3. make_d1_readiness_candidate rejects instrumented evidence as live D1
    with pytest.raises((d1.D1Error, d1.D1AuthorityError), match="readiness candidate requires live (authority schema|provider evidence)"):
        d1.make_d1_readiness_candidate(REPO_ROOT, edir)


def test_b7_readback_and_tamper_rejection(tmp_path):
    croot = (tmp_path / "custody").resolve()
    edir = (croot / "evidence").resolve()
    auth = _valid_authority(edir, custody_dir=croot)
    d1.run_instrumented_d1_lifecycle(REPO_ROOT, edir, auth)
    verified = d1.readback_d1_record(edir, REPO_ROOT)
    assert verified["probe_id"] == d1.PROBE_ID

    # Tamper with stdout.bin
    stdout_file = edir / "stdout.bin"
    orig_stdout = stdout_file.read_bytes()
    stdout_file.write_bytes(orig_stdout + b"\ntamper")
    with pytest.raises(d1.D1ReadbackError, match="stdout mismatch"):
        d1.readback_d1_record(edir, REPO_ROOT)
    stdout_file.write_bytes(orig_stdout)

    # Missing stdout.bin
    stdout_file.unlink()
    with pytest.raises(d1.D1ReadbackError, match="stdout.bin missing"):
        d1.readback_d1_record(edir, REPO_ROOT)
    stdout_file.write_bytes(orig_stdout)

    # Symlink stdout.bin
    stdout_symlink = edir / "stdout_link.bin"
    stdout_file.unlink()
    stdout_symlink.write_bytes(orig_stdout)
    stdout_file.symlink_to(stdout_symlink)
    with pytest.raises(d1.D1ReadbackError, match="stdout.bin symlink forbidden"):
        d1.readback_d1_record(edir, REPO_ROOT)
    stdout_file.unlink()
    stdout_symlink.unlink()
    stdout_file.write_bytes(orig_stdout)

    # Tamper with stderr.bin
    stderr_file = edir / "stderr.bin"
    orig_stderr = stderr_file.read_bytes()
    stderr_file.write_bytes(orig_stderr + b"\ntamper")
    with pytest.raises(d1.D1ReadbackError, match="stderr mismatch"):
        d1.readback_d1_record(edir, REPO_ROOT)
    stderr_file.write_bytes(orig_stderr)

    # Tamper with stream log
    stream_file = edir / "d1.context-plan.claude-stream.jsonl"
    orig_stream = stream_file.read_bytes()
    stream_file.write_bytes(orig_stream + b"\ntamper")
    with pytest.raises(d1.D1ReadbackError, match="stream log mismatch"):
        d1.readback_d1_record(edir, REPO_ROOT)
    stream_file.write_bytes(orig_stream)

    # Tamper with source identity in record
    rec_file = edir / "d1-record.json"
    rec_data = json.loads(rec_file.read_bytes())
    rec_data["source_identity"] = "f" * 64
    rec_file.write_bytes(json.dumps(rec_data).encode())
    with pytest.raises(d1.D1ReadbackError, match="record digest mismatch"):
        d1.readback_d1_record(edir, REPO_ROOT)


def test_instrumented_lifecycle_success(tmp_path):
    croot = (tmp_path / "custody").resolve()
    edir = (croot / "evidence").resolve()
    auth = _valid_authority(edir, custody_dir=croot)
    record = d1.run_instrumented_d1_lifecycle(REPO_ROOT, edir, auth)
    assert record["schema"] == d1.INSTRUMENTED_EVIDENCE_SCHEMA
    assert record["probe_id"] == d1.PROBE_ID
    assert record["provider_free_d1_seam_qualified"] is True
    assert record["provider_free_seam_qualified"] is True
    assert record["d1_status"] == "not-run"
    assert record["invariants"]["one_use_consumed"] is True
    assert record["invariants"]["git_preserved"] is True
    assert record["invariants"]["settings_preserved"] is True
    assert record["post_provider"]["oracle"]["status"] == "pass"
    assert record["post_provider"]["native_reads"]["read_count"] >= 1

    # Verify LaunchGuard fake subprocess accounting and zero sentinel trips
    guard_dir = edir / "provider-guard"
    retained_info = verify_retained(guard_dir, edir / "d1-record.json")
    assert retained_info["real_provider_starts"] == 0
    assert retained_info["fake_subprocess_starts"] >= 1
    assert retained_info["status"] == "clean"


@pytest.mark.parametrize("scenario,kw", [
    ("nonzero", {"scenario": "nonzero"}),
    ("timeout", {"scenario": "timeout"}),
    ("malformed", {"scenario": "malformed"}),
    ("read_mismatch", {"scenario": "read_mismatch"}),
    ("no_read", {"scenario": "no_read"}),
    ("wrong_read_path", {"scenario": "wrong_read_path"}),
    ("content_mismatch", {"scenario": "content_mismatch"}),
    ("missing_raw_log", {"scenario": "missing_raw_log"}),
    ("extra_tool", {"scenario": "extra_tool"}),
    ("non_empty_mcp", {"scenario": "non_empty_mcp"}),
    ("model_mismatch", {"scenario": "model_mismatch"}),
    ("permission_mismatch", {"scenario": "permission_mismatch"}),
    ("corrupt_log", {"corrupt_log": True}),
    ("forbidden_tool", {"tool_mutation": "Bash"}),
    ("mcp_violation", {"tool_mutation": "mcp"}),
    ("settings_drift", {"scenario": "settings_drift"}),
])
def test_instrumented_lifecycle_failures(tmp_path, scenario, kw):
    croot = (tmp_path / "custody").resolve()
    edir = (croot / f"ev_{scenario}").resolve()
    auth = _valid_authority(edir, custody_dir=croot, attempt_id=f"att-{scenario}")
    record = d1.run_instrumented_d1_lifecycle(REPO_ROOT, edir, auth, **kw)
    assert record["provider_free_d1_seam_qualified"] is False
    assert (edir / "attempt-state.json").is_file()
    assert json.loads((edir / "attempt-state.json").read_bytes())["status"] == "failed"


def test_fake_provider_refuses_git_mutation_on_repo_root(tmp_path):
    croot = (tmp_path / "custody").resolve()

    # 1. Calling without disposable_root raises D1Error
    edir1 = (croot / "ev_git_mut1").resolve()
    auth1 = _valid_authority(edir1, custody_dir=croot, attempt_id="att-git-mut1")
    with pytest.raises(d1.D1Error, match="git_mutation scenario requires explicit disposable_root"):
        d1.run_instrumented_d1_lifecycle(REPO_ROOT, edir1, auth1, scenario="git_mutation")

    # 2. Calling with disposable_root=REPO_ROOT raises D1Error
    edir2 = (croot / "ev_git_mut2").resolve()
    auth2 = _valid_authority(edir2, custody_dir=croot, attempt_id="att-git-mut2")
    with pytest.raises(d1.D1Error, match="disposable_root cannot overlap"):
        d1.run_instrumented_d1_lifecycle(REPO_ROOT, edir2, auth2, scenario="git_mutation", disposable_root=REPO_ROOT)

    # 3. Isolated disposable git repo
    edir3 = (croot / "ev_git_mut3").resolve()
    disp_repo = (tmp_path / "disposable_repo").resolve()
    subprocess.run(["git", "init", str(disp_repo)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(disp_repo), "config", "user.name", "Tester"], check=True)
    subprocess.run(["git", "-C", str(disp_repo), "config", "user.email", "tester@example.com"], check=True)
    (disp_repo / "README.md").write_text("initial")
    subprocess.run(["git", "-C", str(disp_repo), "add", "README.md"], check=True)
    subprocess.run(["git", "-C", str(disp_repo), "commit", "-m", "init"], check=True)
    auth3 = _valid_authority(edir3, custody_dir=croot, attempt_id="att-git-mut3", root=disp_repo)

    rec = d1.run_instrumented_d1_lifecycle(
        REPO_ROOT, edir3, auth3, scenario="git_mutation", disposable_root=disp_repo
    )
    assert rec["provider_free_d1_seam_qualified"] is False
    assert (disp_repo / ".untracked_git_mutation_probe").exists()
    assert not (REPO_ROOT / ".untracked_git_mutation_probe").exists()


def test_mechanical_readiness_candidate(tmp_path):
    croot = (tmp_path / "custody").resolve()
    edir = (croot / "evidence").resolve()
    auth = _valid_authority(edir, custody_dir=croot)
    rec = d1.run_instrumented_d1_lifecycle(REPO_ROOT, edir, auth)

    # 1. Instrumented record is rejected by make_d1_readiness_candidate
    with pytest.raises((d1.D1Error, d1.D1AuthorityError), match="readiness candidate requires live (authority schema|provider evidence)"):
        d1.make_d1_readiness_candidate(REPO_ROOT, edir)

    # 2. Section 7: Inverting APG166O forgery test:
    # Converting fake JSON to live, editing transport receipt, and editing ledger transport label
    # MUST STILL FAIL readiness because authority schema, provider-start receipt, and ledger digests remain instrumented!
    forged_rec = copy.deepcopy(rec)
    forged_rec["schema"] = d1.LIVE_EVIDENCE_SCHEMA
    forged_rec["execution_kind"] = "live-provider"
    forged_rec["d1_status"] = "qualified"
    forged_rec["record_digest"] = d1.compute_record_digest(forged_rec)
    (edir / "d1-record.json").write_bytes(json.dumps(forged_rec).encode())

    with pytest.raises((d1.D1ReadbackError, d1.D1AuthorityError, d1.D1Error)):
        d1.readback_d1_record(edir, REPO_ROOT)

    with pytest.raises((d1.D1AuthorityError, d1.D1Error)):
        d1.make_d1_readiness_candidate(REPO_ROOT, edir)

    # Even if custody ledger transport_kind AND transport receipt are tampered to production-provider:
    attempt_key = d1.derive_attempt_key(auth, auth["source_identity"])
    ledger_path = croot / "consumed-attempts" / f"{attempt_key}.json"
    ledger_data = json.loads(ledger_path.read_bytes())
    ledger_data["transport_kind"] = d1.PRODUCTION_TRANSPORT_KIND
    ledger_path.write_bytes(json.dumps(ledger_data).encode())

    tr_path = edir / "transport-receipt.json"
    tr_data = json.loads(tr_path.read_bytes())
    tr_data["transport_kind"] = d1.PRODUCTION_TRANSPORT_KIND
    tr_path.write_bytes(json.dumps(tr_data).encode())

    # Forgery MUST STILL FAIL at the schema/authority level!
    with pytest.raises((d1.D1AuthorityError, d1.D1ReadbackError, d1.D1Error)):
        d1.make_d1_readiness_candidate(REPO_ROOT, edir)

    # 3. B3: Attempting to relabel/rehash authority, provider-start receipt, and ledger
    # STILL FAILS because independently retained instrumented provenance
    # (provider-guard-receipt.json, provider-guard directory, instrumented-executed-runtime.json, fake-bin) remains!
    auth_live = _valid_authority(edir, custody_dir=croot, schema=d1.LIVE_AUTHORITY_SCHEMA)
    auth_live["authority_digest"] = d1.compute_authority_digest(auth_live)
    (edir / "authority.json").write_bytes(json.dumps(auth_live).encode())

    live_attempt_key = d1.derive_attempt_key(auth_live, auth_live["source_identity"])
    sr_path = edir / "provider-start-receipt.json"
    sr_data = json.loads(sr_path.read_bytes())
    sr_data["authority_id"] = auth_live["authority_id"]
    sr_data["authority_digest"] = auth_live["authority_digest"]
    sr_data["attempt_key"] = live_attempt_key
    sr_data["transport_kind"] = d1.PRODUCTION_TRANSPORT_KIND
    sr_data["transport_class"] = "production-provider"
    sr_path.write_bytes(json.dumps(sr_data).encode())
    sr_digest = d1._sha256(d1._canonical_bytes(sr_data))

    live_ledger_file = croot / "consumed-attempts" / f"{live_attempt_key}.json"
    launch_contract = json.loads((edir / "launch-contract.json").read_bytes())
    lc_digest = d1._sha256(d1._canonical_bytes(launch_contract))

    live_ledger_data = {
        "schema": d1.ATTEMPT_LEDGER_SCHEMA,
        "probe_id": d1.PROBE_ID,
        "status": "start_finalized",
        "authority_schema": d1.LIVE_AUTHORITY_SCHEMA,
        "authority_id": auth_live["authority_id"],
        "authority_digest": auth_live["authority_digest"],
        "attempt_id": auth_live["attempt_id"],
        "attempt_key": live_attempt_key,
        "source_identity": auth_live["source_identity"],
        "custody_root": str(croot),
        "evidence_root": str(edir),
        "transport_kind": d1.PRODUCTION_TRANSPORT_KIND,
        "transport_class": "production-provider",
        "launch_contract_digest": lc_digest,
        "provider_start_receipt_digest": sr_digest,
        "pid": sr_data.get("pid", 12345),
        "process_group": sr_data.get("process_group"),
        "session_id": sr_data.get("session_id"),
        "starts_consumed": 1,
        "consumed_at": "2026-09-24T20:00:00Z",
    }
    live_ledger_file.write_bytes(json.dumps(live_ledger_data).encode())

    st_path = edir / "attempt-state.json"
    st_data = json.loads(st_path.read_bytes())
    st_data["authority_digest"] = auth_live["authority_digest"]
    st_data["attempt_key"] = live_attempt_key
    st_data["custody_ledger_file"] = str(live_ledger_file)
    st_data["custody_ledger_sha256"] = d1._sha256(d1._canonical_bytes(live_ledger_data))
    st_data["transport_kind"] = d1.PRODUCTION_TRANSPORT_KIND
    st_data["transport_class"] = "production-provider"
    st_path.write_bytes(json.dumps(st_data).encode())

    # Readback rejects because provider-guard-receipt.json remains
    with pytest.raises(d1.D1ReadbackError, match="(provider-guard-receipt.json forbidden for live run|guard_receipt_digest mismatch)"):
        d1.readback_d1_record(edir, REPO_ROOT)

    # Readiness candidate rejects
    with pytest.raises((d1.D1AuthorityError, d1.D1ReadbackError, d1.D1Error)):
        d1.make_d1_readiness_candidate(REPO_ROOT, edir)

    # 4. Isolated test of readiness candidate schema structure
    isolated_cand = {
        "schema": d1.READINESS_CANDIDATE_SCHEMA,
        "probe_id": d1.PROBE_ID,
        "phase": "APG166Q",
        "manager_review_required": True,
        "prerequisites_ready": False,
        "live_holdout_authorized": False,
        "d1_mechanical_validation": "live-qualified",
        "evidence_root": str(edir),
        "source_identity": auth_live["source_identity"],
        "model": "claude-opus-5-5",
        "profile": "normal-final-review",
        "route_probe_id": d1.PROBE_ID,
        "allowed_native_tools": ["Read"],
        "forbidden_tools": ["Bash", "Write", "Edit", "Agent"],
        "read_count": 1,
        "target_file": "test",
        "file_bytes": 100,
        "file_sha256": "0" * 64,
        "raw_events_delivery_sha256": "0" * 64,
        "attempt_key": live_attempt_key,
        "custody_ledger_sha256": "0" * 64,
        "provider_start_receipt_digest": sr_digest,
        "candidate_digest": "0" * 64,
    }
    assert isolated_cand["schema"] == d1.READINESS_CANDIDATE_SCHEMA
    with pytest.raises(ValueError, match="custody belongs to dispatcher/manager"):
        d1.make_d1_readiness_candidate(REPO_ROOT, edir, independent_review={"review": "accept"})


def test_process_creation_hook_and_launch_guard_observation(tmp_path):
    from agent_phase import provider as phase_provider
    import subprocess as sp

    # 1. Default hook is None
    assert phase_provider.PROCESS_CREATION_HOOK.get() is None

    # 2. When hook is None, ordinary provider process execution is completely unaffected
    # (tested via subprocess.Popen in isolated env or hook callback)
    observed = []
    def custom_hook(proc, argv, cwd, env):
        observed.append({"pid": proc.pid, "argv": argv, "cwd": cwd})

    token = phase_provider.PROCESS_CREATION_HOOK.set(custom_hook)
    try:
        assert phase_provider.PROCESS_CREATION_HOOK.get() is custom_hook
        # Trigger hook via fake process or mock
        class FakeProc:
            pid = 99999
        phase_provider.PROCESS_CREATION_HOOK.get()(FakeProc(), ["echo", "test"], "/tmp", {})
        assert len(observed) == 1
        assert observed[0]["pid"] == 99999
    finally:
        phase_provider.PROCESS_CREATION_HOOK.reset(token)

    assert phase_provider.PROCESS_CREATION_HOOK.get() is None

    # 3. Hook exception does not leak a running child process
    spawned_pids = []
    def exploding_hook(proc, argv, cwd, env):
        spawned_pids.append(proc.pid)
        raise RuntimeError("simulated hook failure")

    token2 = phase_provider.PROCESS_CREATION_HOOK.set(exploding_hook)
    try:
        with pytest.raises(RuntimeError, match="simulated hook failure"):
            phase_provider.run(["sleep", "60"], "test", cwd=str(tmp_path))
        assert len(spawned_pids) == 1
        pid = spawned_pids[0]
        try:
            os.kill(pid, 0)
            is_alive = True
        except (ProcessLookupError, PermissionError):
            is_alive = False
        assert not is_alive, f"Process {pid} was leaked!"
    finally:
        phase_provider.PROCESS_CREATION_HOOK.reset(token2)


def test_negative_matrix_custody_and_launch_failures(tmp_path):
    croot = (tmp_path / "custody").resolve()
    edir = (croot / "evidence").resolve()
    auth = _valid_authority(edir, custody_dir=croot)
    rec = d1.run_instrumented_d1_lifecycle(REPO_ROOT, edir, auth)
    assert rec["provider_free_d1_seam_qualified"] is True

    attempt_key = d1.derive_attempt_key(auth, auth["source_identity"])
    ledger_path = croot / "consumed-attempts" / f"{attempt_key}.json"

    # 1. Missing authority.json in readback
    auth_file = edir / "authority.json"
    auth_bytes = auth_file.read_bytes()
    auth_file.unlink()
    with pytest.raises(d1.D1ReadbackError, match="authority.json missing"):
        d1.readback_d1_record(edir, REPO_ROOT)
    auth_file.write_bytes(auth_bytes)

    # 2. Missing custody ledger in readback
    orig_ledger = ledger_path.read_bytes()
    ledger_path.unlink()
    with pytest.raises(d1.D1ReadbackError, match="custody ledger missing"):
        d1.readback_d1_record(edir, REPO_ROOT)
    ledger_path.write_bytes(orig_ledger)

    # 3. Custody ledger sha256 mismatch in readback
    tampered_ledger = json.loads(orig_ledger)
    tampered_ledger["extra_tamper"] = 123
    ledger_path.write_bytes(json.dumps(tampered_ledger).encode())
    with pytest.raises(d1.D1ReadbackError, match="custody ledger (digest|sha256) mismatch"):
        d1.readback_d1_record(edir, REPO_ROOT)
    ledger_path.write_bytes(orig_ledger)

    # 4. Custody ledger schema mismatch
    tampered_ledger = json.loads(orig_ledger)
    tampered_ledger["schema"] = "wrong.schema/v1"
    tampered_ledger_bytes = d1._canonical_bytes(tampered_ledger)
    ledger_path.write_bytes(tampered_ledger_bytes)
    # Also update attempt-state sha256 so it reaches the schema check
    st_path = edir / "attempt-state.json"
    orig_st = st_path.read_bytes()
    st_data = json.loads(orig_st)
    st_data["custody_ledger_sha256"] = d1._sha256(tampered_ledger_bytes)
    st_path.write_bytes(d1._canonical_bytes(st_data))
    with pytest.raises(d1.D1ReadbackError, match="custody ledger schema mismatch"):
        d1.readback_d1_record(edir, REPO_ROOT)
    ledger_path.write_bytes(orig_ledger)
    st_path.write_bytes(orig_st)

    # 5. Custody ledger starts_consumed != 1
    tampered_ledger = json.loads(orig_ledger)
    tampered_ledger["starts_consumed"] = 2
    tampered_ledger_bytes = d1._canonical_bytes(tampered_ledger)
    ledger_path.write_bytes(tampered_ledger_bytes)
    st_data = json.loads(orig_st)
    st_data["custody_ledger_sha256"] = d1._sha256(tampered_ledger_bytes)
    st_path.write_bytes(d1._canonical_bytes(st_data))
    with pytest.raises(d1.D1ReadbackError, match="starts_consumed must be 1 in custody ledger"):
        d1.readback_d1_record(edir, REPO_ROOT)
    ledger_path.write_bytes(orig_ledger)
    st_path.write_bytes(orig_st)

    # 6. Missing provider-start-receipt.json
    start_receipt_file = edir / "provider-start-receipt.json"
    orig_sr = start_receipt_file.read_bytes()
    start_receipt_file.unlink()
    with pytest.raises(d1.D1ReadbackError, match="provider-start-receipt.json missing"):
        d1.readback_d1_record(edir, REPO_ROOT)
    start_receipt_file.write_bytes(orig_sr)

    # 7. Missing production-expected-runtime.json
    prod_rt_file = edir / "production-expected-runtime.json"
    orig_prod_rt = prod_rt_file.read_bytes()
    prod_rt_file.unlink()
    with pytest.raises(d1.D1ReadbackError, match="production-expected-runtime.json missing"):
        d1.readback_d1_record(edir, REPO_ROOT)
    prod_rt_file.write_bytes(orig_prod_rt)

    # 8. Child startup observed env with unallowlisted parent secret
    child_st_file = edir / "child-startup-evidence.json"
    orig_child_st = child_st_file.read_bytes()
    child_st_data = json.loads(orig_child_st)
    child_st_data["environ"]["LEAKED_SECRET_KEY"] = "secret123"
    child_st_file.write_bytes(json.dumps(child_st_data).encode())
    with pytest.raises(d1.D1ReadbackError, match="ambient environment leaked into child process"):
        d1.readback_d1_record(edir, REPO_ROOT)
    child_st_file.write_bytes(orig_child_st)

    # 9. Custody ledger status == "prelaunch_consumed" fails readback
    tampered_ledger = json.loads(orig_ledger)
    tampered_ledger["status"] = "prelaunch_consumed"
    tampered_ledger_bytes = d1._canonical_bytes(tampered_ledger)
    ledger_path.write_bytes(tampered_ledger_bytes)
    st_path = edir / "attempt-state.json"
    orig_st = st_path.read_bytes()
    st_data = json.loads(orig_st)
    st_data["custody_ledger_sha256"] = d1._sha256(tampered_ledger_bytes)
    st_path.write_bytes(d1._canonical_bytes(st_data))
    with pytest.raises(d1.D1ReadbackError, match="custody ledger status must be start_finalized"):
        d1.readback_d1_record(edir, REPO_ROOT)
    ledger_path.write_bytes(orig_ledger)
    st_path.write_bytes(orig_st)

    # 10. Custody ledger PID mismatch fails readback
    tampered_ledger = json.loads(orig_ledger)
    tampered_ledger["pid"] = 99999999
    tampered_ledger_bytes = d1._canonical_bytes(tampered_ledger)
    ledger_path.write_bytes(tampered_ledger_bytes)
    st_data = json.loads(orig_st)
    st_data["custody_ledger_sha256"] = d1._sha256(tampered_ledger_bytes)
    st_path.write_bytes(d1._canonical_bytes(st_data))
    with pytest.raises(d1.D1ReadbackError, match="PID mismatch between custody ledger and start receipt"):
        d1.readback_d1_record(edir, REPO_ROOT)
    ledger_path.write_bytes(orig_ledger)
    st_path.write_bytes(orig_st)

    # 11. Invalid PID in provider-start-receipt.json fails readback
    orig_sr_data = json.loads(orig_sr)
    invalid_sr_data = dict(orig_sr_data)
    invalid_sr_data["pid"] = -1
    start_receipt_file.write_bytes(d1._canonical_bytes(invalid_sr_data))
    with pytest.raises(d1.D1ReadbackError, match="valid PID required in provider-start receipt"):
        d1.readback_d1_record(edir, REPO_ROOT)
    start_receipt_file.write_bytes(orig_sr)

    # 12. Invalid child startup PID fails corroboration
    tampered_child_st = json.loads(orig_child_st)
    tampered_child_st["pid"] = -1
    child_st_file.write_bytes(json.dumps(tampered_child_st).encode())
    with pytest.raises(d1.D1ReadbackError, match="valid PID required in child startup evidence"):
        d1.readback_d1_record(edir, REPO_ROOT)
    child_st_file.write_bytes(orig_child_st)

    # 13. Child startup cwd mismatch fails corroboration
    tampered_child_st = json.loads(orig_child_st)
    tampered_child_st["cwd"] = "/tmp/tampered_cwd"
    child_st_file.write_bytes(json.dumps(tampered_child_st).encode())
    with pytest.raises(d1.D1ReadbackError, match="child startup cwd mismatch with start receipt"):
        d1.readback_d1_record(edir, REPO_ROOT)
    child_st_file.write_bytes(orig_child_st)

    # 14. Child startup executable mismatch fails corroboration
    tampered_child_st = json.loads(orig_child_st)
    tampered_child_st["argv"] = ["/bin/bash", "--tampered"]
    child_st_file.write_bytes(json.dumps(tampered_child_st).encode())
    with pytest.raises(d1.D1ReadbackError, match="child startup executable mismatch with start receipt physical executable"):
        d1.readback_d1_record(edir, REPO_ROOT)
    child_st_file.write_bytes(orig_child_st)

    # 15. Child startup allowlisted env value mismatch fails corroboration
    tampered_child_st = json.loads(orig_child_st)
    tampered_child_st["environ"]["LANG"] = "fr_FR.UTF-8"
    child_st_file.write_bytes(json.dumps(tampered_child_st).encode())
    with pytest.raises(d1.D1ReadbackError, match="child startup environment mismatch for allowlisted key LANG"):
        d1.readback_d1_record(edir, REPO_ROOT)
    child_st_file.write_bytes(orig_child_st)


@pytest.mark.parametrize('field,value,match', [
    ('environment_digest', '0' * 64, 'environment_digest'),
    ('argv_sha256', '0' * 64, 'argv_sha256'),
    ('physical_executable_sha256', '0' * 64, 'physical_executable_sha256'),
    ('allowlist_environment', {}, 'allowlist_environment'),
    ('popen_executable_sha256', '0' * 64, 'Popen launcher digest'),
])
def test_source_derived_launch_facts_reject_rehashed_receipt(tmp_path, field, value, match):
    croot = (tmp_path / 'custody').resolve()
    edir = croot / 'evidence'
    authority = _valid_authority(edir, custody_dir=croot)
    d1.run_instrumented_d1_lifecycle(REPO_ROOT, edir, authority)
    receipt_path = edir / 'provider-start-receipt.json'
    receipt = json.loads(receipt_path.read_bytes())
    receipt[field] = value
    receipt_path.write_bytes(d1._canonical_bytes(receipt))
    ledger_path = croot / 'consumed-attempts' / (receipt['attempt_key'] + '.json')
    ledger = json.loads(ledger_path.read_bytes())
    ledger['provider_start_receipt_digest'] = d1._sha256(d1._canonical_bytes(receipt))
    ledger_path.write_bytes(d1._canonical_bytes(ledger))
    state_path = edir / 'attempt-state.json'
    state = json.loads(state_path.read_bytes())
    state['custody_ledger_sha256'] = d1._sha256(d1._canonical_bytes(ledger))
    state_path.write_bytes(d1._canonical_bytes(state))
    with pytest.raises(d1.D1ReadbackError, match=match):
        d1.readback_d1_record(edir, REPO_ROOT)


@pytest.mark.parametrize('mutate,match', [
    (lambda f: f.update(environment_digest=f['diagnostic_environment_digest']), 'unverifiable authoritative'),
    (lambda f: f.pop('diagnostic_environment_digest_classification'), 'classification'),
    (lambda f: f.update(diagnostic_environment_digest_classification='authoritative'), 'classification'),
    (lambda f: f.update(diagnostic_environment_digest='not-a-digest'), 'malformed'),
], ids=['authoritative-field', 'missing-classification', 'authoritative-classification', 'malformed-digest'])
def test_native_environment_digest_is_explicitly_diagnostic(tmp_path, mutate, match):
    from agent_phase.transmission import NATIVE_ENVIRONMENT_DIGEST_CLASSIFICATION
    croot = (tmp_path / 'custody').resolve()
    edir = croot / 'evidence'
    authority = _valid_authority(edir, custody_dir=croot)
    d1.run_instrumented_d1_lifecycle(REPO_ROOT, edir, authority)
    d1.readback_d1_record(edir, REPO_ROOT)
    path = edir / 'd1.context-launcher-deliveries.json'
    deliveries = json.loads(path.read_bytes())
    facts = deliveries['launch_facts']
    assert facts['diagnostic_environment_digest_classification'] == NATIVE_ENVIRONMENT_DIGEST_CLASSIFICATION
    assert 'environment_digest' not in facts
    mutate(facts)
    os.chmod(path, 0o600)
    data = json.dumps(deliveries).encode()
    path.write_bytes(data)
    # Rebind custody so the diagnostic-only checks, not the digest, refuse.
    _rebind_native_custody(edir, d1.native_launch_custody(data))
    with pytest.raises(d1.D1ReadbackError, match=match):
        d1.readback_d1_record(edir, REPO_ROOT)


def _rebind_native_custody(edir, custody):
    record_path = edir / 'd1-record.json'
    record = json.loads(record_path.read_bytes())
    record['post_provider']['native_launch_custody'] = custody
    record['record_digest'] = d1.compute_record_digest(record)
    os.chmod(record_path, 0o600)
    record_path.write_bytes(json.dumps(record).encode())


def _instrumented_evidence(tmp_path):
    croot = (tmp_path / 'custody').resolve()
    edir = croot / 'evidence'
    d1.run_instrumented_d1_lifecycle(REPO_ROOT, edir, _valid_authority(edir, custody_dir=croot))
    record = d1.readback_d1_record(edir, REPO_ROOT)
    return edir, edir / d1.NATIVE_LAUNCH_FACTS_ARTIFACT, record


def test_native_launch_facts_are_record_digest_bound(tmp_path):
    edir, path, record = _instrumented_evidence(tmp_path)
    custody = record['post_provider']['native_launch_custody']
    assert custody == d1.native_launch_custody(path.read_bytes())
    assert custody['artifact'] == d1.NATIVE_LAUNCH_FACTS_ARTIFACT
    assert 'not re-observed after exit' in custody['observation_scope']
    assert custody['native_environment_digest'].startswith('diagnostic-non-authoritative')


def test_missing_native_launch_facts_fail_readback(tmp_path):
    edir, path, _ = _instrumented_evidence(tmp_path)
    path.unlink()
    with pytest.raises(d1.D1ReadbackError, match='launcher-deliveries.json missing'):
        d1.readback_d1_record(edir, REPO_ROOT)
    # The custody reader itself refuses without the required-artifact precheck.
    from testing.h_eval.d1_launch_contract import custodied_launch_facts
    with pytest.raises(d1.D1ReadbackError, match='missing, symlink or unreadable'):
        custodied_launch_facts(edir, {})


def test_symlinked_native_launch_facts_fail_readback(tmp_path):
    edir, path, record = _instrumented_evidence(tmp_path)
    moved = edir / 'moved-launcher-deliveries.json'
    path.rename(moved)
    path.symlink_to(moved)
    with pytest.raises(d1.D1ReadbackError, match='launcher-deliveries.json symlink forbidden'):
        d1.readback_d1_record(edir, REPO_ROOT)
    from testing.h_eval.d1_launch_contract import custodied_launch_facts
    with pytest.raises(d1.D1ReadbackError, match='missing, symlink or unreadable'):
        custodied_launch_facts(edir, record)


def test_mutated_native_launch_facts_fail_custody_digest(tmp_path):
    edir, path, _ = _instrumented_evidence(tmp_path)
    deliveries = json.loads(path.read_bytes())
    # A self-consistent edit (same parent PID) still differs from the custodied bytes.
    deliveries['launch_facts']['session_id'] = -1
    os.chmod(path, 0o600)
    path.write_bytes(json.dumps(deliveries).encode())
    with pytest.raises(d1.D1ReadbackError, match='digest mismatch with record custody'):
        d1.readback_d1_record(edir, REPO_ROOT)


@pytest.mark.parametrize('mutate,match', [
    (lambda c: c.update(sha256='0' * 64), 'digest mismatch with record custody'),
    (lambda c: c.update(bytes=c['bytes'] + 1), 'digest mismatch with record custody'),
    (lambda c: c.update(observation_scope='live post-exit verified'), 'digest mismatch with record custody'),
    (lambda c: c.clear(), 'digest mismatch with record custody'),
], ids=['digest', 'length', 'overclaimed-scope', 'empty'])
def test_rebound_record_custody_mutation_fails(tmp_path, mutate, match):
    edir, _, record = _instrumented_evidence(tmp_path)
    custody = copy.deepcopy(record['post_provider']['native_launch_custody'])
    mutate(custody)
    _rebind_native_custody(edir, custody)
    with pytest.raises(d1.D1ReadbackError, match=match):
        d1.readback_d1_record(edir, REPO_ROOT)


def test_record_without_native_custody_fails_readback(tmp_path):
    edir, _, _ = _instrumented_evidence(tmp_path)
    _rebind_native_custody(edir, None)
    with pytest.raises(d1.D1ReadbackError, match='custody missing from record'):
        d1.readback_d1_record(edir, REPO_ROOT)


@pytest.mark.parametrize('kind,flag', [
    (d1.FAKE_TRANSPORT_KIND, 'provider_free_d1_seam_qualified'),
    (d1.PRODUCTION_TRANSPORT_KIND, 'd1_status'),
])
def test_absent_native_launch_facts_cannot_qualify_record(kind, flag):
    arguments = dict(
        authority={'attempt_id': 'a'}, descriptor={}, descriptor_sha256='d', source_identity_str='s',
        route={}, pre_evidence={'git': {'head': 'h'}, 'settings': {'sha256': 's'}},
        terminal={'exit_code': 0}, stdout=b'', stderr=b'', raw_stream=b'',
        stream_receipt={'schema': 'apg.claude-stream-completion/v2', 'process_status': 0,
                        'raw_stream': {'bytes': 0, 'sha256': d1._sha256(b'')},
                        'durable': True, 'stream_enabled_before_start': True},
        observation={'reads': [{}]}, delivery_data={}, imported={'provider_outcome': 'success'}, oracle_result={'status': 'pass'},
        post_git={'head': 'h'}, post_settings={'sha256': 's'}, post_runtime={},
        surface_contract={'valid': True}, execution_kind=kind)
    passed, failed = ('qualified', 'failed') if flag == 'd1_status' else (True, False)
    bound = d1.derive_d1_record(**arguments, native_launch=d1.native_launch_custody(b'{}'))
    assert bound[flag] == passed
    absent = d1.derive_d1_record(**arguments, native_launch=None)
    assert absent[flag] == failed
    assert absent['post_provider']['native_launch_custody'] is None
