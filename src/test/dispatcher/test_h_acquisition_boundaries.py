"""APG166D launch admission regressions; no provider is invoked."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from agent_phase.acquisition_launch import AcquisitionLaunch
from agent_phase.claude_read_observer import capture_recovery, digest, observe
from test_h_claude_reads import case, encoded, SCOPE
from test_h_wrapper_handoff import binary, prepared_launch, environment
from agent_phase.claude_acquisition_handoff import OPTION, consume


def test_internal_route_requires_observation_before_consumption(binary, tmp_path):
    argv, prompt, prepared = prepared_launch(binary, tmp_path)
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake = bindir / "claude"
    fake.write_text("#!" + sys.executable + "\nraise SystemExit(97)\n")
    fake.chmod(0o700)
    env = {**os.environ, **environment(argv, prepared), "PATH": str(bindir) + os.pathsep + os.environ["PATH"]}
    env.pop("AGENT_CENTRAL_WORKER_FACADE", None)
    env.pop("APGR_WORKER_FACADE", None)
    result = subprocess.run(argv, input=prompt, capture_output=True, env=env, timeout=30)
    assert result.returncode != 0
    assert b"requires --live-log" in result.stderr
    assert not Path(argv[argv.index(OPTION) + 1] + ".consumed").exists()


FORBIDDEN = ["--tools", "--allowed-tools", "--allowedTools", "--disallowed-tools",
             "--disallowedTools", "--mcp-config", "--strict-mcp-config", "--settings",
             "--managed-settings", "--setting-sources", "--add-dir", "--model",
             "--fallback-model", "--effort", "--permission-mode", "--permission-prompt-tool",
             "--permission-prompts", "--dangerously-skip-permissions",
             "--allow-dangerously-skip-permissions"]


@pytest.mark.parametrize("extra", [["--"], ["--apgr-acquisition-handoff", "x"],
                                  ["--print"], ["task text"],
                                  *[[flag, "x"] for flag in FORBIDDEN]])
def test_prepare_refuses_before_any_authority_write(tmp_path, monkeypatch, extra):
    from agent_phase import acquisition_launch
    monkeypatch.setattr(acquisition_launch, "_new", lambda *a, **k: pytest.fail("authority created before argv admission"))
    launch = AcquisitionLaunch(binary=Path("/usr/bin/true").resolve(), catalog={},
                               candidates=["apgr:go-language-profile"],
                               seam="claude-profile-readonly", native_read_authorized=True)
    with pytest.raises(ValueError):
        launch.prepare(dict(run_id="r", binding_id="b", attempt_id="a"), tmp_path,
                       ["/wrapper/claude-profile", "normal-final-review", "--read-only", "-p", *extra])
    assert list(tmp_path.iterdir()) == []


def test_unchanged_requires_captured_authority(case):
    use, result, terminal = copy.deepcopy(case[1])
    use["message"]["content"][0]["id"] = "again"
    result["message"]["content"][0]["tool_use_id"] = "again"
    result["tool_use_result"] = {"type": "file_unchanged", "file": {
        "filePath": use["message"]["content"][0]["input"]["file_path"]}}
    raw = encoded([*case[1][:2], use, result, terminal])
    with pytest.raises(ValueError, match="captured"):
        observe(raw, expected_sha256=digest(raw), captured={}, scope=SCOPE)


@pytest.mark.parametrize("extra", [[flag, "x"] for flag in FORBIDDEN] +
                         [[flag + "=x"] for flag in FORBIDDEN] + [["--no-tools"], ["--agent", "x"]])
def test_full_wrapper_refuses_override_before_native(binary, tmp_path, extra):
    from testing.h_eval import claude_reads
    argv, prompt, prepared = prepared_launch(binary, tmp_path)
    argv = claude_reads.prepare(prepared, argv)
    bindir = tmp_path / "bin"; bindir.mkdir()
    marker = tmp_path / "native-invoked"
    fake = bindir / "claude"
    fake.write_text("#!" + sys.executable + "\nfrom pathlib import Path\nPath(" + repr(str(marker)) + ").touch()\n")
    fake.chmod(0o700)
    env = {**os.environ, **environment(argv, prepared), "PATH": str(bindir) + os.pathsep + os.environ["PATH"]}
    env.pop("AGENT_CENTRAL_WORKER_FACADE", None)
    env.pop("APGR_WORKER_FACADE", None)
    result = subprocess.run([*argv, *extra], input=prompt, capture_output=True, env=env, timeout=15)
    assert result.returncode != 0
    assert not marker.exists()
    assert not Path(argv[argv.index(OPTION) + 1] + ".consumed").exists()


@pytest.mark.parametrize("change", ["missing", "run_id", "binding_id", "attempt_id", "digest", "facade"])
def test_full_wrapper_refuses_scope_and_facade(binary, tmp_path, change):
    from agent_phase.transmission import SCOPE_ENV
    from testing.h_eval import claude_reads
    argv, prompt, prepared = prepared_launch(binary, tmp_path)
    argv = claude_reads.prepare(prepared, argv)
    env = {**os.environ, **environment(argv, prepared)}
    env.pop("AGENT_CENTRAL_WORKER_FACADE", None)
    env.pop("APGR_WORKER_FACADE", None)
    scope = json.loads(env[SCOPE_ENV])
    if change == "missing": env.pop(SCOPE_ENV)
    elif change == "facade": env["APGR_WORKER_FACADE"] = "1"
    else:
        if change == "digest": scope["handoff"]["sha256"] = "0" * 64
        else: scope["record"][change] = "wrong"
        env[SCOPE_ENV] = json.dumps(scope)
    # No native binary can be resolved if admission regresses.
    env["PATH"] = str(tmp_path)
    result = subprocess.run([sys.executable, str(Path('libexec/claude_vc_profile.py').resolve()),
                             str(Path.cwd() / "claude"), argv[1], *argv[2:]],
                            input=prompt, capture_output=True, env=env, timeout=15)
    assert result.returncode != 0
    assert b"claude executable not found" not in result.stderr
    assert (b"internal acquisition handoff" in result.stderr if change != "facade"
            else b"cannot compose with worker facade" in result.stderr)
    assert not Path(argv[argv.index(OPTION) + 1] + ".consumed").exists()


@pytest.mark.parametrize("change", ["config", "server", "handoff", "recovery", "root", "binary", "marker", "marker_inode", "scope"])
def test_postrun_custody_rejects_drift(binary, tmp_path, change):
    from agent_phase.claude_acquisition_custody import capture_prepared, verify_after
    local = tmp_path / "apgr"; local.write_bytes(Path(binary).read_bytes()); local.chmod(0o700)
    argv, _, prepared = prepared_launch(local, tmp_path)
    path = Path(argv[argv.index(OPTION) + 1])
    before = capture_prepared(prepared)
    handoff = consume(path, environment(argv, prepared))
    if change == "scope": prepared["record"]["attempt_id"] = "wrong"
    elif change == "root":
        root = Path(handoff["recovery_authority"]["path"])
        root.rename(root.with_name("saved")); root.mkdir()
    else:
        selected = {"config": Path(handoff["config"]["path"]),
                    "server": Path(prepared["record"]["acquisition"]["config"]),
                    "handoff": path, "binary": local,
                    "recovery": path.parent / prepared["record"]["acquisition"]["recovery"][0]["path"],
                    "marker": Path(str(path) + ".consumed"),
                    "marker_inode": Path(str(path) + ".consumed")}[change]
        data = selected.read_bytes()
        if change == "marker_inode":
            selected.rename(selected.with_suffix(".saved")); selected.write_bytes(data); selected.chmod(0o600)
        else: selected.write_bytes(data + b" ")
    with pytest.raises((ValueError, OSError)):
        verify_after(prepared, before)
    retained = json.loads(Path(str(path) + ".custody-after.json").read_bytes())
    assert retained["status"] == "invalid"
    assert set(retained["observed"]["files"]) == set(before["files"])


def test_failed_premodel_attempt_is_consumed_and_fresh_attempt_is_independent(binary, tmp_path):
    from testing.h_eval import claude_reads
    first = tmp_path / "first"; first.mkdir()
    argv, _, prepared = prepared_launch(binary, first)
    argv = claude_reads.prepare(prepared, argv)
    path = argv[argv.index(OPTION) + 1]
    env = {**os.environ, **environment(argv, prepared), "PATH": str(first)}
    env.pop("AGENT_CENTRAL_WORKER_FACADE", None)
    env.pop("APGR_WORKER_FACADE", None)
    failed = subprocess.run([sys.executable, str(Path('libexec/claude_vc_profile.py').resolve()),
                             str(Path.cwd() / "claude"), argv[1], *argv[2:]],
                            input=b"", capture_output=True, env=env, timeout=15)
    assert failed.returncode != 0 and b"claude executable not found" in failed.stderr
    with pytest.raises(FileExistsError): consume(path, environment(argv, prepared))
    second = tmp_path / "second"; second.mkdir()
    argv2, _, prepared2 = prepared_launch(binary, second, dict(run_id="fresh-run", binding_id="fresh-binding", attempt_id="fresh-attempt"))
    assert argv2[argv2.index(OPTION) + 1] != path
    consume(argv2[argv2.index(OPTION) + 1], environment(argv2, prepared2))


def test_print_alias_normalized_without_authority_side_effect():
    from agent_phase.claude_acquisition_argv import prepare_argv
    assert prepare_argv(["claude-profile", "normal-final-review", "--read-only", "--print"])[-1] == "-p"
