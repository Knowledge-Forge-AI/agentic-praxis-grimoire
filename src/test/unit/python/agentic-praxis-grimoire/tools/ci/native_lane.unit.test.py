"""Native CI adapter contracts with every external command replaced."""
from __future__ import annotations

import json
import subprocess

import pytest

from tools.ci import native_lane as lane
from tools.ci import native_seal as seals


@pytest.fixture(autouse=True)
def no_external_commands(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        raise AssertionError("unreplaced external process in source-only fixture")
    monkeypatch.setattr(subprocess, "run", forbidden)
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
            stdout = "apgr 0.13.0\n"
        elif "build-info" in args:
            stdout = json.dumps({"version": "0.13.0", "target": spec["target"], "corpus_fingerprint_verified": True})
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


def test_child_failure_cannot_emit_success(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 1, "", "failure"))
    with pytest.raises(lane.LaneError, match="failed"):
        lane._run(["go", "test", "./..."])


def test_binary_target_smoke_fails_on_wrong_packaged_architecture(monkeypatch, tmp_path):
    values = iter(["apgr 0.13.0\n", json.dumps({"version": "0.13.0", "target": "linux/arm64", "corpus_fingerprint_verified": True})])
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
        (py / f"agentic_praxis_grimoire-0.13.0-py3-none-{item['python_tag']}.whl").write_bytes(b"fixture")
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
            out = "apgr 0.13.0\n"
        elif "build-info" in args:
            out = json.dumps({"version": "0.13.0", "target": spec["target"], "corpus_fingerprint_verified": True})
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
    assert npm[-1].endswith(f"knowledge-forge-ai-apgr-{spec['npm_slug']}-0.13.0.tgz")
    assert sum("report" in command and "verify" in command for command in commands) == 2


@pytest.mark.parametrize("key", ["GITHUB_TOKEN", "GH_TOKEN"])
def test_consumer_refuses_a_token_in_packaged_execution(monkeypatch, tmp_path, key):
    monkeypatch.setenv(key, "fixture-token")
    with pytest.raises(lane.LaneError, match="must not inherit"):
        lane.run_consumer("native-linux-x64", tmp_path / "bundle", tmp_path / "out")
