"""D1 repair through real wrapper/production transport and disposable fakes only."""
import json
import os
from pathlib import Path
import subprocess

import pytest

from testing.h_eval import d1_auth, d1_qualification as d1, readiness

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def installed(tmp_path, monkeypatch):
    home = tmp_path / "operator"
    home.mkdir()
    (home / ".fake-authenticated").touch()
    config = home / ".claude"
    config.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config))
    for name in ("USER", "LOGNAME", "SECURITYSESSIONID"):
        monkeypatch.setenv(name, "disposable-identity")
    for name in ("ANTHROPIC_API_KEY", "APGR_WORKER_FACADE", "AGENT_CENTRAL_HOME", "UNRELATED_VARIABLE"):
        monkeypatch.setenv(name, "must-not-be-forwarded")
    binary = d1.create_fake_claude_executable(tmp_path / "provider", repo_root=ROOT)
    original = binary.read_text()
    monkeypatch.setenv("PATH", str(binary.parent) + os.pathsep + "/usr/bin:/bin")
    python = binary.parent / "python3"
    monkeypatch.setattr(d1, "_launching_python", lambda: str(python))

    def configure(scenario="success", transform=None):
        script = original.replace('cfg.get("scenario", "success")', repr(scenario))
        binary.write_text(transform(script) if transform else script)
        evidence = tmp_path / "custody" / "attempt"
        state = d1.capture_git_state(ROOT)
        authority = {
            "schema": d1.LIVE_AUTHORITY_SCHEMA, "probe_id": d1.PROBE_ID,
            "authority_id": "fake-repair-test", "attempt_id": "fake-repair-test",
            "accepted_commit": state["head"], "accepted_tree": state["tree"],
            "source_identity": readiness.source_identity(readiness.make_seal(ROOT)["files"]),
            "descriptor_sha256": d1._sha256((ROOT / d1.DESCRIPTOR_RELATIVE_PATH).read_bytes()),
            "custody_root": str(evidence.parent), "evidence_root": str(evidence),
            "max_starts": 1, "replay_prohibited": True,
        }
        return evidence, authority

    return home, binary, configure


def test_supported_auth_context_and_real_native_argv(installed):
    home, _, configure = installed
    # Populated operator configuration must not add instruction/RTK guidance.
    settings = home / ".claude" / "settings.json"
    settings.write_text('{"permissions":{"deny":["Skill(agent-worker)"]}}')
    (home / ".claude" / "CLAUDE.md").write_text("Unrelated operator instruction")
    apgr = home / ".apgr"
    apgr.mkdir(parents=True)
    (apgr / "config.toml").write_text('[integrations.rtk]\nenabled = true\nexecutable = "/no/such/rtk"\n')
    evidence, authority = configure()
    before = settings.read_bytes()
    record = d1.run_live_d1(ROOT, evidence, authority)
    assert record["d1_status"] == "qualified"  # A fake production-transport result only.
    assert settings.read_bytes() == before
    assert not (evidence / "home").exists()
    assert record["pre_provider"]["settings"]["sources"]["isolation"]["isolated_home"] is False
    native = json.loads((evidence / d1.NATIVE_LAUNCH_FACTS_ARTIFACT).read_bytes())["launch_facts"]
    argv = native["argv"]
    assert argv[argv.index("--tools") + 1] == "Read"
    assert "--safe-mode" in argv and "--no-session-persistence" in argv
    assert "--append-system-prompt" not in argv
    child = json.loads((evidence / "child-startup-evidence.json").read_bytes())
    assert child["environ"]["HOME"] == str(home)
    assert "must-not-be-forwarded" not in json.dumps(child["environ"])
    assert record["surface_contract"]["tools"] == ["Read"]
    assert record["executable_evidence"]["preflight"]["auth_status"]["status"] == "authenticated"
    assert d1.readback_d1_record(evidence, ROOT)["d1_status"] == "qualified"
    ledger = next((evidence.parent / "consumed-attempts").glob("*.json"))
    consumed = ledger.read_bytes()
    with pytest.raises(d1.D1AttemptError):
        d1.run_live_d1(ROOT, evidence, authority)
    assert ledger.read_bytes() == consumed
    auth_path = evidence / "auth-context.json"
    auth = json.loads(auth_path.read_bytes())
    auth["values"]["ANTHROPIC_API_KEY"] = "forbidden"
    auth_path.chmod(0o600)
    auth_path.write_text(json.dumps(auth))
    record["pre_provider"]["auth_context_sha256"] = d1._sha256(auth_path.read_bytes())
    record["record_digest"] = d1.compute_record_digest(record)
    record_path = evidence / "d1-record.json"
    record_path.chmod(0o600)
    record_path.write_text(json.dumps(record))
    with pytest.raises(d1.D1ReadbackError, match="authentication context"):
        d1.readback_d1_record(evidence, ROOT, allow_failed=True)


def test_auth_refusal_does_not_consume_then_same_authority_runs(installed):
    home, _, configure = installed
    evidence, authority = configure()
    marker = home / ".fake-authenticated"
    marker.unlink()
    with pytest.raises(d1.D1Error, match="unauthenticated"):
        d1.run_live_d1(ROOT, evidence, authority)
    assert not evidence.exists()
    assert not (evidence.parent / "consumed-attempts").exists()
    marker.touch()
    assert d1.run_live_d1(ROOT, evidence, authority)["d1_status"] == "qualified"


def test_exact_observed_version_reaches_startup(installed):
    _, binary, configure = installed
    assert d1.D1_CLAUDE_CLI_VERSION == "2.1.281"
    evidence, authority = configure()
    assert subprocess.check_output([str(binary), "--version"], text=True).split()[0] == "2.1.281"
    record = d1.run_live_d1(ROOT, evidence, authority)
    assert record["d1_status"] == "qualified"
    assert record["executable_evidence"]["preflight"]["claude_version"] == "2.1.281"
    events = [json.loads(line) for line in (evidence / "stdout.bin").read_bytes().splitlines()]
    assert events[0]["claude_code_version"] == "2.1.281"


def test_startup_version_drift_is_consumed_and_inspectable(installed, monkeypatch):
    _, binary, configure = installed
    collect = d1.claude_reads.collect
    errors = []

    def observed_collect(*args, **kwargs):
        try:
            return collect(*args, **kwargs)
        except ValueError as error:
            errors.append(str(error))
            raise

    monkeypatch.setattr(d1.claude_reads, "collect", observed_collect)

    def startup_only(script):
        old = '"claude_code_version": ' + repr(d1.D1_CLAUDE_CLI_VERSION)
        assert script.count(old) == 2
        return script.replace(old, '"claude_code_version": "2.1.259"')

    evidence, authority = configure(transform=startup_only)
    assert subprocess.check_output([str(binary), "--version"], text=True).split()[0] == "2.1.281"
    record = d1.run_live_d1(ROOT, evidence, authority)
    assert record["executable_evidence"]["preflight"]["claude_version"] == "2.1.281"
    assert record["d1_status"] == "failed"
    assert errors == ["runtime differs from qualified native Read binding"]
    assert record["post_provider"]["failure_reasons"] == [
        "NO_NATIVE_READ",
        "ORACLE_FAILED:no_native_read_observed",
    ]
    assert list((evidence.parent / "consumed-attempts").glob("*.json"))
    # Existing readback cannot reconstruct the rejected qualified observation.
    # Preserve this diagnostic limit without changing accepted readback behavior.
    with pytest.raises(d1.D1ReadbackError, match="native reads count recomputation mismatch"):
        d1.readback_d1_record(evidence, ROOT, allow_failed=True)


@pytest.mark.parametrize("replacement,reason", [("{}", "indeterminate"), ("HELP_UNSUPPORTED", "unsupported")])
def test_unverifiable_status_refuses_before_consumption(installed, replacement, reason):
    _, _, configure = installed
    def transform(script):
        if replacement == "HELP_UNSUPPORTED":
            return script.replace("auth status --json --safe-mode --no-session-persistence", "unsupported")
        return script.replace('json.dumps({"loggedIn": marker.is_file(), "authMethod": "claude.ai"})', repr(replacement))
    evidence, authority = configure(transform=transform)
    with pytest.raises(d1.D1Error, match=reason):
        d1.run_live_d1(ROOT, evidence, authority)
    assert not evidence.exists()


@pytest.mark.parametrize("scenario,exit_code", [("auth_error", 1), ("nonzero", 7)])
def test_complete_provider_failure_remains_inspectable_and_consumed(installed, scenario, exit_code):
    _, _, configure = installed
    evidence, authority = configure(scenario)
    record = d1.run_live_d1(ROOT, evidence, authority)
    post = record["post_provider"]
    assert record["d1_status"] == "failed"
    assert post["capture"]["status"] == "complete"
    assert post["terminal"]["exit_code"] == exit_code
    assert post["importer"]["provider_terminal_status"] == "success"
    assert post["provider_outcome"] == "error"
    assert "ORACLE_FAILED:no_native_read_observed" in post["failure_reasons"]
    assert post["importer"]["provider_error"]["assistant_errors"] == ["authentication_failed"]
    assert b"live logging failed" not in (evidence / "stderr.bin").read_bytes()
    assert d1.readback_d1_record(evidence, ROOT, allow_failed=True)["d1_status"] == "failed"
    with pytest.raises(d1.D1ReadbackError, match="PROVIDER_ERROR"):
        d1.readback_d1_record(evidence, ROOT)
    ledger = next((evidence.parent / "consumed-attempts").glob("*.json"))
    before = ledger.read_bytes()
    with pytest.raises(d1.D1AttemptError):
        d1.run_live_d1(ROOT, evidence, authority)
    assert ledger.read_bytes() == before


def test_five_tool_argv_is_not_hidden_by_fake(installed, monkeypatch):
    _, _, configure = installed
    original = d1.d1_outer_argv
    def broad(root):
        argv = original(root)
        index = argv.index("--read-only-tools")
        return argv[:index] + argv[index + 2:]
    monkeypatch.setattr(d1, "d1_outer_argv", broad)
    evidence, authority = configure()
    record = d1.run_live_d1(ROOT, evidence, authority)
    assert "FORBIDDEN_TOOLS_OBSERVED" in record["surface_contract"]["failure_codes"]
    assert set(record["surface_contract"]["tools"]) == {"Read", "Glob", "Grep", "WebFetch", "WebSearch"}
    assert record["d1_status"] == "failed"
    with pytest.raises(d1.D1ReadbackError):
        d1.readback_d1_record(evidence, ROOT)


def test_truncated_capture_is_not_complete(installed):
    _, _, configure = installed
    evidence, authority = configure(transform=lambda s: s.replace("sys.stdout.buffer.write(out_b)", "sys.stdout.buffer.write(out_b[:-8])"))
    record = d1.run_live_d1(ROOT, evidence, authority)
    assert record["post_provider"]["capture"]["status"] == "incomplete"
    assert not (evidence / "d1.context-plan.claude-stream.complete.json").exists()
    assert "CAPTURE_INCOMPLETE" in record["post_provider"]["failure_reasons"]
    assert any(reason.startswith("ORACLE_FAILED:") for reason in record["post_provider"]["failure_reasons"])
    assert d1.readback_d1_record(evidence, ROOT, allow_failed=True)["d1_status"] == "failed"


def test_valid_raw_receipt_with_truncated_runner_output_is_inspectable(installed, monkeypatch):
    _, _, configure = installed
    invoke = d1.context_adapter.invoke

    def truncated(*args, **kwargs):
        result = invoke(*args, **kwargs)
        # Exercise the real wrapper, then model the runner's independent output cap.
        return result._replace(stdout=result.stdout[:100], truncated=True)

    monkeypatch.setattr(d1.context_adapter, "invoke", truncated)
    evidence, authority = configure("auth_error")
    record = d1.run_live_d1(ROOT, evidence, authority)
    assert (evidence / "d1.context-plan.claude-stream.complete.json").is_file()
    assert record["post_provider"]["capture"]["status"] == "incomplete"
    assert "CAPTURE_INCOMPLETE" in record["post_provider"]["failure_reasons"]
    assert any(reason.startswith("ORACLE_FAILED:") for reason in record["post_provider"]["failure_reasons"])
    assert d1.readback_d1_record(evidence, ROOT, allow_failed=True)["d1_status"] == "failed"
    with pytest.raises(d1.D1ReadbackError):
        d1.readback_d1_record(evidence, ROOT)


def test_auth_context_revalidation_and_settings_symlink(tmp_path):
    home = tmp_path / "operator"
    home.mkdir()
    for values in ({"HOME": str(home), "ANTHROPIC_API_KEY": "secret"}, {"HOME": "relative"}):
        with pytest.raises(ValueError):
            d1_auth.validate_context(values)
    with pytest.raises(ValueError, match="overlaps"):
        d1_auth.validate_context({"HOME": str(home)}, forbidden_roots=(tmp_path,))
    settings = home / ".claude" / "settings.json"
    settings.parent.mkdir()
    target = home / "settings-target.json"
    target.write_text("{}")
    settings.symlink_to(target)
    snapshot = d1_auth.settings_snapshot({"HOME": str(home)})
    assert snapshot["status"] == "symlink" and snapshot["sha256"] == d1._sha256(b"{}")


def test_custom_startup_surfaces_fail_closed():
    init = {"skills": [], "plugins": [], "agents": ["custom"], "memory_paths": {"user": "/custom"}}
    assert d1_auth.surface_failures(init, {}) == ["AGENTS_MISMATCH", "MEMORY_PATHS_MISMATCH"]


def test_populated_auto_memory_refuses_before_consumption(installed):
    home, _, configure = installed
    evidence, authority = configure()
    memory = d1_auth.auto_memory_path({"HOME": str(home)}, evidence)
    memory.mkdir(parents=True)
    (memory / "MEMORY.md").write_text("Previous task memory")
    with pytest.raises(d1.D1Error, match="auto-memory path is not fresh"):
        d1.run_live_d1(ROOT, evidence, authority)
    assert not evidence.exists()
    assert not (evidence.parent / "consumed-attempts").exists()
