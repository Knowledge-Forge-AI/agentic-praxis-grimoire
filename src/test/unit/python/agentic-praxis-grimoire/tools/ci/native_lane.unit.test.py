"""Native CI adapter contracts with every external command replaced."""
from __future__ import annotations

import json
import signal
import subprocess

import pytest

from tools.ci import native_lane as lane
from tools.ci import native_seal as seals


@pytest.fixture(autouse=True)
def no_external_commands(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        raise AssertionError("unreplaced external process in source-only fixture")
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    for key in ("GOOS", "GOARCH", "GITHUB_WORKSPACE", "GITHUB_OUTPUT", "GITHUB_TOKEN", "GH_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    for key, value in {"SOURCE_COMMIT": "a" * 40, "SOURCE_TREE": "b" * 40,
                       "PR_HEAD_SHA": "c" * 40, "PR_BASE_SHA": "d" * 40,
                       "COMMIT_SHA": "a" * 40, "ACTUAL_REPO": lane.EXPECTED_REPO,
                       "ACTUAL_REPO_ID": lane.EXPECTED_REPO_ID, "BASE_REF": "main",
                       "HEAD_REF": "staging", "HEAD_REPO": lane.EXPECTED_REPO,
                       "RUNNER_OS": "Linux", "RUNNER_ARCH": "X64", "ImageOS": "ubuntu24",
                       "ImageVersion": "fixture", "RUNNER_TEMP": str(tmp_path)}.items():
        monkeypatch.setenv(key, value)


@pytest.fixture
def command_child(monkeypatch):
    """Replace process creation; exercise the adapter's real timeout cleanup."""
    class Child:
        pid = 4242

        def __init__(self, result, timeouts):
            self.returncode = result.returncode
            self.result = result
            self.timeouts = list(timeouts)
            self.deadlines = []

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def communicate(self, *, timeout):
            self.deadlines.append(timeout)
            if self.timeouts:
                raise self.timeouts.pop(0)
            return self.result.stdout, self.result.stderr

    def install(result, *timeouts):
        child = Child(result, timeouts)
        def start(args, **kwargs):
            assert kwargs["start_new_session"] is True
            assert kwargs["stdout"] == kwargs["stderr"] == subprocess.PIPE
            return child
        monkeypatch.setattr(subprocess, "Popen", start)
        return child
    return install


def git_fixture(args, cwd=None):
    if args[0] == "status":
        return ""
    if args[0] == "rev-parse":
        return "a" * 40 + "\n" + "b" * 40
    if args[0] == "show":
        return "d" * 40 + " " + "c" * 40
    raise AssertionError(args)


def test_guard_binds_merge_commit_distinct_from_pr_head(monkeypatch, tmp_path):
    monkeypatch.setattr(lane, "_git_run", git_fixture)
    result = lane.run_guard(tmp_path / "guard")
    assert result["source_commit"] == "a" * 40
    assert result["pr_head_sha"] == "c" * 40
    assert json.loads((tmp_path / "guard/identity.json").read_text())["source_tree"] == "b" * 40


@pytest.mark.parametrize("change", ["parents", "dirty", "commit", "fork", "missing"])
def test_guard_refuses_identity_drift(monkeypatch, tmp_path, change):
    def changed(args, cwd=None):
        if change == "parents" and args[0] == "show":
            return "e" * 40 + " " + "c" * 40
        if change == "dirty" and args[0] == "status":
            return "M unexpected"
        return git_fixture(args)
    monkeypatch.setattr(lane, "_git_run", changed)
    if change == "commit":
        monkeypatch.setenv("COMMIT_SHA", "f" * 40)
    elif change == "fork":
        monkeypatch.setenv("HEAD_REPO", "fork/repo")
    elif change == "missing":
        monkeypatch.delenv("HEAD_REPO")
    with pytest.raises(lane.LaneError):
        lane.run_guard(tmp_path / "guard")


def test_runner_environment_cannot_override_actual_host(monkeypatch):
    monkeypatch.setattr(lane.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(lane.platform, "machine", lambda: "arm64")
    with pytest.raises(lane.LaneError, match="host system/architecture"):
        lane._verify_native_host(seals.CANONICAL_TARGETS["native-linux-x64"])


def test_even_matching_cross_target_override_is_forbidden(monkeypatch):
    monkeypatch.setattr(lane.platform, "system", lambda: "Linux")
    monkeypatch.setattr(lane.platform, "machine", lambda: "x86_64")
    monkeypatch.setenv("GOOS", "linux")
    with pytest.raises(lane.LaneError, match="override forbidden"):
        lane._verify_native_host(seals.CANONICAL_TARGETS["native-linux-x64"])


@pytest.mark.parametrize("name", list(seals.CANONICAL_TARGETS))
def test_native_qualification_runs_race_and_real_nix_adapter(monkeypatch, tmp_path, name):
    import apg_go_build
    import apg_go_buildinfo
    import apg_nix_qualification as nix
    spec = seals.CANONICAL_TARGETS[name]
    monkeypatch.setattr(lane.platform, "system", lambda: "Darwin" if spec["system"] == "darwin" else "Linux")
    monkeypatch.setattr(lane.platform, "machine", lambda: spec["arch"])
    monkeypatch.setenv("RUNNER_OS", "macOS" if spec["system"] == "darwin" else "Linux")
    monkeypatch.setenv("RUNNER_ARCH", "ARM64" if spec["arch"] == "arm64" else "X64")
    monkeypatch.setattr(lane, "_git_run", git_fixture)
    monkeypatch.setattr(lane.shutil, "which", lambda _: "/fixture/go")
    synthetic = apg_go_buildinfo.make_synthetic_binary(target=spec["target"])
    _, mod = apg_go_buildinfo.extract_raw_build_info(synthetic)
    recorded = "binary: go1.26.9\n" + mod
    compiler = tmp_path / "compiler"
    compiler.write_text("go1.26.9\n" + recorded)
    calls = []
    def run(args, **kwargs):
        calls.append(args)
        if args[:2] == ["/fixture/go", "version"]:
            stdout = recorded if "-m" in args else f"go version go1.26.9 {spec['target']}\n"
        elif args[0] == "nix":
            stdout = str(compiler)
        elif "--version" in args:
            stdout = "apgr 0.13.1\n"
        elif "build-info" in args:
            stdout = json.dumps({"version": "0.13.1", "target": spec["target"], "corpus_fingerprint_verified": True})
        else:
            stdout = "passed\n"
        return subprocess.CompletedProcess(args, 0, stdout, "")
    monkeypatch.setattr(lane, "_run", run)
    def build(root, target, output, **kwargs):
        assert kwargs == {"require_native": True}
        output.write_bytes(synthetic)
        output.with_name("apgr.binary-manifest.json").write_text("{}\n")
    monkeypatch.setattr(apg_go_build, "build", build)
    nix_calls = []
    def qualify(flake, scratch, system):
        nix_calls.append((flake, system))
        return {"profile_removed": True, "store_smoke": {"controller_generation": {"reason": "installed_immutable_runtime"}},
                "profile_smoke": {"controller_generation": {"reason": "installed_immutable_runtime"}}}
    monkeypatch.setattr(nix, "qualify_local", qualify)
    monkeypatch.setattr(nix, "eval_foreign", lambda *args: {})
    result = lane.run_qualify(name, tmp_path / "out")
    assert any(args[1:] == ["test", "-race", "-count=1", "./..."] for args in calls)
    assert any(args[1:] == ["test", "-count=1", "./..."] for args in calls)
    assert any(args[1:] == ["vet", "./..."] for args in calls)
    assert nix_calls[0][0].endswith("rev=" + "a" * 40)
    assert result["evidence"] == "native-execution"
    assert seals.verify_lane_seal(tmp_path / "out" / spec["slug"] / "lane-seal.json")["target"] == spec["target"]


def test_child_failure_cannot_emit_success(command_child):
    command_child(subprocess.CompletedProcess([], 1, "", "failure"))
    with pytest.raises(lane.LaneError, match="failed"):
        lane._run(["go", "test", "./..."])


def test_binary_target_smoke_fails_on_wrong_packaged_architecture(monkeypatch, tmp_path):
    values = iter(["apgr 0.13.1\n", json.dumps({"version": "0.13.1", "target": "linux/arm64", "corpus_fingerprint_verified": True})])
    monkeypatch.setattr(lane, "_run", lambda *a, **k: subprocess.CompletedProcess([], 0, next(values), ""))
    with pytest.raises(lane.LaneError, match="build-info"):
        lane._binary_smoke(tmp_path / "binary", "linux/amd64", tmp_path)


@pytest.mark.parametrize("name", list(seals.CANONICAL_TARGETS))
def test_consumer_installs_exact_sealed_archives_offline(monkeypatch, tmp_path, name):
    from tools.ci import native_artifacts
    spec = seals.CANONICAL_TARGETS[name]
    bundle = tmp_path / "bundle"
    py = bundle / "python"
    py.mkdir(parents=True)
    for item in seals.CANONICAL_TARGETS.values():
        (py / f"agentic_praxis_grimoire-0.13.1-py3-none-{item['python_tag']}.whl").write_bytes(b"fixture")
    binding = {"artifact_id": "1", "artifact_digest": "sha256:" + "e" * 64, "seal_sha256": "f" * 64}
    monkeypatch.setenv("NATIVE_BUNDLE_JSON", json.dumps(binding))
    monkeypatch.setattr(lane, "_identity", lambda: ("a" * 40, "b" * 40))
    monkeypatch.setattr(lane, "_verify_native_host", lambda _: {})
    artifact_calls = []
    monkeypatch.setattr(native_artifacts, "verify_downloaded_artifact", lambda *a, **k: artifact_calls.append(a))
    seal = {"bundle_seal_sha256": "f" * 64, "source_commit": "a" * 40, "source_tree": "b" * 40}
    seal_checks = []
    monkeypatch.setattr(lane, "verify_bundle_seal", lambda *a: (seal_checks.append(a) or seal))
    commands = []
    def run(args, **kwargs):
        commands.append(args)
        if kwargs.get("allow_failure"):
            return subprocess.CompletedProcess(args, 1, "", "not a supported wheel on this platform")
        if args == ["node", "--version"]:
            out = "v22.22.2\n"
        elif "--version" in args:
            out = "apgr 0.13.1\n"
        elif "build-info" in args:
            out = json.dumps({"version": "0.13.1", "target": spec["target"], "corpus_fingerprint_verified": True})
        else:
            out = "passed"
        return subprocess.CompletedProcess(args, 0, out, "")
    monkeypatch.setattr(lane, "_run", run)
    result = lane.run_consumer(name, bundle, tmp_path / "consumer")
    assert artifact_calls == []  # The separate workflow verifier owns token-bearing API access.
    assert len(seal_checks) == 2
    assert result["checks"]["foreign_wheel_rejected"] == "passed"
    npm = next(command for command in commands if command[:2] == ["npm", "install"])
    assert {"--offline", "--ignore-scripts", "--no-audit", "--no-fund", "--package-lock=false"} <= set(npm)
    assert npm[-1].endswith(f"knowledge-forge-ai-apgr-{spec['npm_slug']}-0.13.1.tgz")
    assert sum("report" in command and "verify" in command for command in commands) == 2


@pytest.mark.parametrize("key", ["GITHUB_TOKEN", "GH_TOKEN"])
def test_consumer_refuses_a_token_in_packaged_execution(monkeypatch, tmp_path, key):
    monkeypatch.setenv(key, "fixture-token")
    with pytest.raises(lane.LaneError, match="must not inherit"):
        lane.run_consumer("native-linux-x64", tmp_path / "bundle", tmp_path / "out")


def test_failed_command_keeps_stdout_cause_and_status(command_child):
    output = "--- FAIL: TestDarwin (0.01s)\n    native_test.go:42: actual cause\nFAIL\tfixture/package\n"
    command_child(subprocess.CompletedProcess([], 7, output, ""))
    with pytest.raises(lane.LaneError, match="actual cause") as caught:
        lane._run(["/fixture/go", "test", "-count=1", "./..."])
    assert caught.value.diagnostics["returncode"] == 7
    assert caught.value.diagnostics["stderr_tail"] == ""


def test_large_command_failure_is_bounded_and_retains_early_cause(command_child):
    output = "--- FAIL: TestEarly (0.01s)\n    early_test.go:9: early cause\n" + "noise\n" * 200000
    command_child(subprocess.CompletedProcess([], 1, output, "é" * 20000))
    with pytest.raises(lane.LaneError) as caught:
        lane._run(["go", "test"])
    diagnostics = caught.value.diagnostics
    assert "early cause" in str(caught.value)
    for field in ("stdout_tail", "stderr_tail", "failure_extract"):
        assert len(diagnostics[field].encode()) <= 16384
    assert diagnostics["stdout_truncated"] and diagnostics["stderr_truncated"]
    assert len(str(caught.value).encode()) < 55000


def test_timeout_decodes_and_bounds_partial_bytes(monkeypatch, command_child):
    partial = subprocess.CompletedProcess([], -9, b"partial stdout\xff", b"partial stderr")
    child = command_child(partial, subprocess.TimeoutExpired([], 2700, output=partial.stdout, stderr=partial.stderr))
    killed = []
    monkeypatch.setattr(lane.os, "killpg", lambda *args: killed.append(args))
    with pytest.raises(lane.LaneError, match="partial stdout") as caught:
        lane._run(["go", "test"])
    assert caught.value.diagnostics["timed_out"] is True
    assert caught.value.diagnostics["returncode"] is None
    assert "partial stderr" in str(caught.value)
    assert child.deadlines == [2700, 5]
    assert killed == [(child.pid, signal.SIGKILL)]


def test_qualify_failure_artifact_is_sanitized_and_cannot_emit_success(monkeypatch, tmp_path, capsys, command_child):
    monkeypatch.setenv("FIXTURE_SECRET", "environment-secret-value")
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "github-output"))
    output = "--- FAIL: TestDarwin\n cause environment-secret-value Bearer bearer-secret-value ghp_fixture123\x00\n"
    command_child(subprocess.CompletedProcess([], 1, output, ""))
    monkeypatch.setattr(lane, "run_qualify", lambda *a: lane._run(["go", "test", "--token", "argument-secret-value"]))
    diagnostics = tmp_path / "diagnostics"
    assert lane.main(["qualify", "--lane", "native-darwin-arm64", "--output", str(tmp_path / "out"),
                      "--diagnostics", str(diagnostics)]) == 1
    artifact = diagnostics / "native-darwin-arm64-failure.json"
    content = artifact.read_text()
    logged = capsys.readouterr().err
    for secret in ("environment-secret-value", "bearer-secret-value", "ghp_fixture123", "argument-secret-value"):
        assert secret not in content and secret not in logged
    result = json.loads(content)
    assert result["schema"] == "apgr.native-lane-failure/v1"
    assert result["status"] == "failed" and result["lane"] == "native-darwin-arm64"
    assert "\x00" not in logged and "TestDarwin" in logged
    assert not list(tmp_path.rglob("lane-seal.json"))
    assert not (tmp_path / "github-output").exists()


@pytest.mark.parametrize("error", [KeyError("fixture key"), TypeError("fixture type"), RuntimeError("fixture runtime")])
def test_unexpected_qualify_errors_are_recorded_and_fail(monkeypatch, tmp_path, error):
    def fail(*args):
        raise error
    monkeypatch.setattr(lane, "run_qualify", fail)
    assert lane.main(["qualify", "--lane", "native-linux-x64", "--output", str(tmp_path / "out"),
                      "--diagnostics", str(tmp_path / "diagnostics")]) == 1
    result = json.loads((tmp_path / "diagnostics/native-linux-x64-failure.json").read_text())
    assert result["exception_type"] == type(error).__name__
    assert result["status"] == "failed"


@pytest.mark.parametrize("location", ["same", "child", "parent", "checkout", "outside-temp"])
def test_diagnostics_path_refused_before_qualification(monkeypatch, tmp_path, location):
    output = tmp_path / "out"
    paths = {"same": output, "child": output / "diagnostics", "parent": tmp_path,
             "checkout": tmp_path / "checkout/diagnostics", "outside-temp": tmp_path.parent / "outside-diagnostics"}
    monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path / "checkout"))
    monkeypatch.setattr(lane, "run_qualify", lambda *a: pytest.fail("qualification started before validation"))
    assert lane.main(["qualify", "--lane", "native-linux-x64", "--output", str(output),
                      "--diagnostics", str(paths[location])]) == 1
    assert not list(tmp_path.rglob("*-failure.json"))


def test_diagnostic_write_failure_keeps_original_cause_and_exit(monkeypatch, tmp_path, capsys):
    def fail(*args):
        raise lane.LaneError("original cause")
    monkeypatch.setattr(lane, "run_qualify", fail)
    diagnostics = tmp_path / "diagnostics"
    diagnostics.write_text("blocked directory")
    assert lane.main(["qualify", "--lane", "native-linux-x64", "--output", str(tmp_path / "out"),
                      "--diagnostics", str(diagnostics)]) == 1
    logged = capsys.readouterr().err
    assert "original cause" in logged and "diagnostics write failed" in logged


def test_success_does_not_create_failure_artifact(monkeypatch, tmp_path):
    monkeypatch.setattr(lane, "run_qualify", lambda *a: {})
    assert lane.main(["qualify", "--lane", "native-linux-x64", "--output", str(tmp_path / "out"),
                      "--diagnostics", str(tmp_path / "diagnostics")]) == 0
    assert not (tmp_path / "diagnostics").exists()


def test_redaction_precedes_bounds_and_neutralizes_log_commands(monkeypatch, command_child):
    monkeypatch.setenv("FIXTURE_API_KEY", "abcdef-secret")
    monkeypatch.setenv("GITHUB_WORKSPACE", "/fixture/private-checkout")
    output = ("::warning::child text\nAuthorization: Basic basic-secret\n"
              "github_pat_pat-secret\n/fixture/private-checkout/cause.go\n"
              "abcdef-\x1b[31msecret\x1b[0m\n" + "x" * 16380 + "abcdef-secret")
    stderr = "::warning::child text\nAuthorization: Basic basic-secret\ngithub_pat_patsecret123\n"
    command_child(subprocess.CompletedProcess([], 1, output, stderr))
    with pytest.raises(lane.LaneError) as caught:
        lane._run(["go", "--api-key=argument-secret"])
    message = str(caught.value)
    for secret in ("abcdef-secret", "basic-secret", "patsecret123", "argument-secret", "/fixture/private-checkout"):
        assert secret not in json.dumps(caught.value.diagnostics) and secret not in message
    assert "::warning::" not in message


def test_expected_nonzero_consumer_control_retains_raw_result(command_child):
    result = subprocess.CompletedProcess(["pip"], 1, "negative control", "unsupported wheel")
    command_child(result)
    actual = lane._run(["pip"], allow_failure=True)
    assert (actual.args, actual.returncode, actual.stdout, actual.stderr) == (
        result.args, result.returncode, result.stdout, result.stderr)


def test_failure_diagnostics_cannot_follow_file_symlink(monkeypatch, tmp_path, capsys):
    def fail(*args):
        raise lane.LaneError("original cause")
    monkeypatch.setattr(lane, "run_qualify", fail)
    diagnostics = tmp_path / "diagnostics"
    diagnostics.mkdir()
    target = tmp_path / "out/protected"
    target.parent.mkdir()
    target.write_text("preserved")
    (diagnostics / "native-linux-x64-failure.json").symlink_to(target)
    assert lane.main(["qualify", "--lane", "native-linux-x64", "--output", str(target.parent),
                      "--diagnostics", str(diagnostics)]) == 1
    assert target.read_text() == "preserved"
    assert "diagnostics write failed" in capsys.readouterr().err


def test_timeout_after_group_exit_still_reports_partial_output(monkeypatch, command_child):
    partial = subprocess.CompletedProcess([], -9, "partial cause", "")
    command_child(partial, subprocess.TimeoutExpired([], 2700))
    def vanished(*args):
        raise ProcessLookupError
    monkeypatch.setattr(lane.os, "killpg", vanished)
    with pytest.raises(lane.LaneCommandError, match="partial cause") as caught:
        lane._run(["go", "test"])
    assert caught.value.diagnostics["timed_out"] is True


def test_timeout_drain_is_bounded_when_descendant_holds_pipe(monkeypatch, command_child):
    child = command_child(subprocess.CompletedProcess([], -9, "", ""),
                          subprocess.TimeoutExpired([], 2700),
                          subprocess.TimeoutExpired([], 5, output=b"escaped pipe cause"))
    monkeypatch.setattr(lane.os, "killpg", lambda *args: None)
    with pytest.raises(lane.LaneCommandError, match="escaped pipe cause"):
        lane._run(["go", "test"])
    assert child.deadlines == [2700, 5]


def test_early_compile_and_vet_causes_survive_output_tail(command_child):
    cause = "# fixture/package\nsource.go:13:7: undefined: missing\nsource.go:22: vet cause\nFAIL fixture/package [build failed]\n"
    command_child(subprocess.CompletedProcess([], 1, "", cause + "noise\n" * 10000))
    with pytest.raises(lane.LaneCommandError) as caught:
        lane._run(["go", "test"])
    assert cause.strip() == caught.value.diagnostics["failure_extract"]
    assert "undefined: missing" not in caught.value.diagnostics["stderr_tail"]


def test_command_timeout_leaves_budget_for_hosted_diagnostics():
    workflow = json.loads((lane.ROOT / ".github/workflows/native-qualification.yml").read_text())
    for name in seals.REQUIRED_LANES:
        assert lane.COMMAND_TIMEOUT_SECONDS <= 60 * 60
        assert lane.COMMAND_TIMEOUT_SECONDS + 30 * 60 < workflow["jobs"][name]["timeout-minutes"] * 60
