"""Production selection with disposable fakes; never live qualification evidence."""
import json
import os
from pathlib import Path
import shlex
import shutil
import sys

import pytest

from testing.h_eval import d1_qualification as d1
from testing.h_eval import readiness

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_LAUNCHING_PYTHON = d1._launching_python


def executable(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(0o700)
    return path


@pytest.fixture
def installed(tmp_path, monkeypatch):
    home = tmp_path / "operator-home"
    home.mkdir()
    (home / ".fake-authenticated").touch()
    (tmp_path / ".fake-authenticated").touch()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    python = executable(tmp_path / "python" / "python3",
                        "#!/bin/sh\nexec " + shlex.quote(sys.executable) + ' "$@"\n')
    generated = d1.create_fake_claude_executable(tmp_path / "generator", repo_root=REPO_ROOT)
    # Copy only the provider script, never the instrumented python3 shim.
    claude = executable(tmp_path / "provider" / "claude",
                        generated.read_text().replace('cfg.get("scenario", "success")',
                                                      'cfg.get("scenario", "no_read")'))
    lookup = tmp_path / "operator-bin" / "claude"
    lookup.parent.mkdir()
    lookup.symlink_to(claude)
    sentinel = tmp_path / "shadow-used"
    shadow = executable(tmp_path / "system" / "python3",
                        f"#!/bin/sh\ntouch {shlex.quote(str(sentinel))}\necho '[3,9,0]'\n")
    monkeypatch.setenv("PATH", os.pathsep.join([str(shadow.parent), str(lookup.parent), "/usr/bin", "/bin"]))
    monkeypatch.setattr(d1, "_launching_python", lambda: str(python))
    monkeypatch.setattr(d1, "D1_SYSTEM_PATH", (str(shadow.parent), "/usr/bin", "/bin"))
    return python, claude, shadow, sentinel


def live_test_authority(tmp_path):
    custody = tmp_path / "custody"
    evidence = custody / "evidence"
    evidence.mkdir(parents=True)
    state = d1.capture_git_state(REPO_ROOT)
    return evidence, {
        "schema": d1.LIVE_AUTHORITY_SCHEMA, "probe_id": d1.PROBE_ID,
        "authority_id": "disposable-fake-test", "attempt_id": "disposable-fake-test",
        "accepted_commit": state["head"], "accepted_tree": state["tree"],
        "source_identity": readiness.source_identity(readiness.make_seal(REPO_ROOT)["files"]),
        "descriptor_sha256": d1._sha256((REPO_ROOT / d1.DESCRIPTOR_RELATIVE_PATH).read_bytes()),
        "custody_root": str(custody), "evidence_root": str(evidence),
        "max_starts": 1, "replay_prohibited": True,
    }


def test_legacy_shadow_and_missing_provider_repaired(installed, tmp_path):
    python, claude, shadow, sentinel = installed
    legacy = os.pathsep.join([str(shadow.parent), str(python.parent)])
    assert shutil.which("python3", path=legacy) == str(shadow)
    assert shutil.which("claude", path=legacy) is None
    selection = d1.select_d1_production_executables()
    env = d1.build_d1_launch_environment(home_dir=tmp_path, tmp_dir=tmp_path, executable_selection=selection)
    assert shutil.which("python3", path=env["PATH"]) == str(python)
    assert shutil.which("claude", path=env["PATH"]) == str(claude)
    assert d1.preflight_d1_production_executables(REPO_ROOT, selection, env)["claude_version"] == d1.D1_CLAUDE_CLI_VERSION
    assert not sentinel.exists()


@pytest.mark.parametrize("failure", ["missing-provider", "missing-python-alias", "old-python", "0.0.0", "2.1.259", "2.1.282", "missing-node"])
def test_refusal_preserves_grant_and_retry(installed, tmp_path, failure):
    python, claude, _, sentinel = installed
    evidence, authority = live_test_authority(tmp_path)
    original_python, original_claude = python.read_text(), claude.read_text()
    if failure == "missing-provider":
        claude.unlink()
    elif failure == "missing-python-alias":
        python.unlink()
    elif failure == "old-python":
        python.write_text("#!/bin/sh\necho '[3,9,0]'\n")
    elif failure in {"0.0.0", "2.1.259", "2.1.282"}:
        claude.write_text(original_claude.replace(d1.D1_CLAUDE_CLI_VERSION, failure))
    else:
        claude.write_text("#!/usr/bin/env missing-d1-node\n")
    with pytest.raises(d1.D1Error, match="must match" if failure in {"2.1.259", "2.1.282"} else None):
        d1.run_live_d1(REPO_ROOT, evidence, authority)
    assert not list(evidence.iterdir())
    assert not (evidence.parent / "consumed-attempts").exists()
    assert not sentinel.exists()
    executable(python, original_python)
    executable(claude, original_claude)
    # Same authority, no cleanup/reset: controlled fake returns an explicit failed record.
    record = d1.run_live_d1(REPO_ROOT, evidence, authority)
    assert record["d1_status"] == "failed"
    assert d1.readback_d1_record(evidence, REPO_ROOT, allow_failed=True)["d1_status"] == "failed"


def test_production_wrapper_evidence_readback_and_one_shot(installed, tmp_path):
    python, claude, _, sentinel = installed
    evidence, authority = live_test_authority(tmp_path)
    record = d1.run_live_d1(REPO_ROOT, evidence, authority)
    assert record["d1_status"] == "failed"  # Deliberate no-Read fake, not a qualification.
    facts = record["executable_evidence"]
    selection = facts["executable_selection"]
    assert selection["executables"]["claude"]["lookup"] != str(claude)
    receipt = json.loads((evidence / "provider-start-receipt.json").read_bytes())
    child = json.loads((evidence / "child-startup-evidence.json").read_bytes())
    native = json.loads((evidence / d1.NATIVE_LAUNCH_FACTS_ARTIFACT).read_bytes())["launch_facts"]
    assert native["argv"][0] == str(claude)
    assert receipt["allowlist_environment"]["PATH"] == child["environ"]["PATH"] == d1.d1_production_path(selection)
    assert facts["production_executable"] == facts["physical_executable"] == str(claude)
    manifest = json.loads((evidence / "runtime-manifest.json").read_bytes())
    assert manifest["runtimes"]["python"]["executable"] == str(python)
    assert not sentinel.exists()
    d1.readback_d1_record(evidence, REPO_ROOT, allow_failed=True)
    with pytest.raises(d1.D1Error):
        d1.run_live_d1(REPO_ROOT, evidence, authority)
    selection["executables"]["python3"]["sha256"] = "0" * 64
    record["record_digest"] = d1.compute_record_digest(record)
    path = evidence / "d1-record.json"
    path.chmod(0o600)
    path.write_bytes(d1._canonical_bytes(record))
    with pytest.raises(d1.D1ReadbackError, match="selection"):
        d1.readback_d1_record(evidence, REPO_ROOT, allow_failed=True)


def test_default_python_and_no_unbound_environment(installed, monkeypatch, tmp_path):
    monkeypatch.setattr(d1, "_launching_python", DEFAULT_LAUNCHING_PYTHON)
    selection = d1.select_d1_production_executables()
    assert selection["executables"]["python3"]["physical"] == str(Path(sys.executable).resolve())
    with pytest.raises(d1.D1Error, match="selection"):
        d1.build_d1_launch_environment(home_dir=tmp_path, tmp_dir=tmp_path)


@pytest.mark.parametrize("env_option", ["", "-S "])
def test_provider_env_interpreter_is_bound_only_when_needed(installed, tmp_path, monkeypatch, env_option):
    _, claude, _, sentinel = installed
    interpreter = executable(tmp_path / "script-runtime" / "d1-test-runtime",
                             "#!/bin/sh\nexec " + shlex.quote(sys.executable) + ' "$@"\n')
    claude.write_text("#!/usr/bin/env " + env_option + "d1-test-runtime\n" + claude.read_text().split("\n", 1)[1])
    monkeypatch.setenv("PATH", os.environ["PATH"] + os.pathsep + str(interpreter.parent))
    selection = d1.select_d1_production_executables()
    assert selection["executables"]["d1-test-runtime"]["physical"] == str(interpreter)
    env = d1.build_d1_launch_environment(home_dir=tmp_path, tmp_dir=tmp_path, executable_selection=selection)
    assert d1.preflight_d1_production_executables(REPO_ROOT, selection, env)["claude_version"] == d1.D1_CLAUDE_CLI_VERSION
    assert not sentinel.exists()


def test_selected_version_uses_closed_operator_context(installed, tmp_path):
    _, claude, _, sentinel = installed
    script = claude.read_text()
    banner = repr(d1.D1_CLAUDE_CLI_VERSION + " (Claude Code)")
    assert script.count(banner) == 1
    claude.write_text(script.replace(banner, banner + ' if "HOME" in os.environ else "2.1.259"'))
    selection = d1.select_d1_production_executables()
    env = d1.build_d1_launch_environment(home_dir=tmp_path, tmp_dir=tmp_path, executable_selection=selection)
    preflight = d1.preflight_d1_production_executables(REPO_ROOT, selection, env)
    assert preflight["claude_version"] == "2.1.281"
    assert preflight["doctor_claude_version"] == "2.1.259"
    assert preflight["auth_status"]["status"] == "authenticated"
    assert not sentinel.exists()


@pytest.mark.parametrize("reported", ["2.1.281-beta.1", "unrelated 2.1.281 output", "2.1.281 (fake-provider-free seam)"])
def test_nonstable_or_ambiguous_version_refuses_before_consumption(installed, tmp_path, reported):
    _, claude, _, _ = installed
    script = claude.read_text()
    banner = repr(d1.D1_CLAUDE_CLI_VERSION + " (Claude Code)")
    claude.write_text(script.replace(banner, repr(reported)))
    evidence, authority = live_test_authority(tmp_path)
    with pytest.raises(d1.D1Error, match="must match"):
        d1.run_live_d1(REPO_ROOT, evidence, authority)
    assert not list(evidence.iterdir())
    assert not (evidence.parent / "consumed-attempts").exists()
