"""Nix host qualification helper as a real process.

``prepare-source`` runs against a real disposable Git repository. The ``nix``
executable is a stand-in on PATH that records each argv and answers or fails
as instructed: real Nix evaluation, builds and profiles are outside this
contract and are exercised by the flake checks and the attended host run.
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
HELPER = ROOT / "libexec/apg_nix_qualification.py"
REV = "1" * 40

FAKE_NIX = r'''
import json, os, sys
log = os.environ["FAKE_NIX_LOG"]
with open(log, "a") as handle:
    handle.write(json.dumps(sys.argv[1:]) + "\n")
fault = json.loads(os.environ.get("FAKE_NIX_FAULT", "{}"))
arguments = sys.argv[1:]
if fault.get("fail") == arguments[:2]:
    print("stand-in nix refusal", file=sys.stderr)
    raise SystemExit(1)
package = os.environ.get("FAKE_NIX_PACKAGE")
if arguments[:2] == ["flake", "metadata"]:
    print(json.dumps(fault.get("metadata", {"locked": {"rev": "%s", "narHash": "sha256-x"}})))
elif arguments[:1] == ["eval"]:
    attribute = arguments[-1]
    print(attribute.rsplit("#", 1)[1].replace("packages.", "drv:"), end="")
elif arguments[:1] == ["build"] and package:
    os.symlink(package, arguments[arguments.index("--out-link") + 1])
elif arguments[:1] == ["run"]:
    print(fault.get("version", "apgr 0.13.0"))
elif arguments[:2] == ["profile", "add"] and package:
    os.symlink(package, arguments[arguments.index("--profile") + 1])
elif arguments[:2] == ["profile", "list"]:
    print(json.dumps({"elements": {"agentic-praxis-grimoire": {"active": True}}}))
elif arguments[:2] == ["profile", "remove"] and not fault.get("keep_profile"):
    os.unlink(arguments[arguments.index("--profile") + 1])
''' % REV


def _standin_package(root: Path) -> Path:
    """Reuse the installed-command stand-ins owned by the smoke integration test."""
    spec = importlib.util.spec_from_file_location(
        "apg_nix_smoke_int_standins", Path(__file__).with_name("apg_nix_smoke.int.test.py"))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._package(root)


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(["git", "-C", os.fspath(repository), *arguments], check=True,
                          capture_output=True, text=True).stdout


def _helper(*arguments: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-B", os.fspath(HELPER), *arguments], cwd=ROOT,
                          env={**os.environ, **(env or {})}, stdin=subprocess.DEVNULL,
                          capture_output=True, text=True, check=False)


@pytest.fixture
def fake_nix(tmp_path: Path) -> dict[str, str]:
    bin_dir = tmp_path / "fake-bin"
    bin_dir.mkdir()
    nix = bin_dir / "nix"
    nix.write_text(f"#!{sys.executable}\n{FAKE_NIX}")
    nix.chmod(0o700)
    return {"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}", "FAKE_NIX_LOG": os.fspath(tmp_path / "nix.log"),
            "HOME": os.fspath(tmp_path / "home"), "XDG_STATE_HOME": os.fspath(tmp_path / "home/.state")}


def _calls(environment: dict[str, str]) -> list[list[str]]:
    log = Path(environment["FAKE_NIX_LOG"])
    return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []


def _checkout(path: Path) -> Path:
    path.mkdir()
    _git(path, "init", "-q", "-b", "main")
    for name, text in {"flake.nix": "{}\n", "libexec/tool.py": "x = 1\n", "private/evidence.md": "private\n",
                       "deleted.txt": "gone\n", ".gitignore": "ignored.txt\n"}.items():
        (path / name).parent.mkdir(parents=True, exist_ok=True)
        (path / name).write_text(text)
    _git(path, "add", ".")
    _git(path, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture")
    (path / "deleted.txt").unlink()
    (path / "untracked.md").write_text("eligible working file\n")
    (path / "ignored.txt").write_text("operator-local\n")
    (path / ".scratch").mkdir()
    (path / ".scratch/state.json").write_text("{}\n")
    return path


def test_prepare_source_commits_only_eligible_working_files_without_touching_the_checkout(tmp_path: Path) -> None:
    checkout = _checkout(tmp_path / "checkout")
    before = (_git(checkout, "rev-parse", "HEAD"), (checkout / ".git/index").read_bytes(),
              _git(checkout, "status", "--porcelain=v1", "--untracked-files=all"))
    bare = tmp_path / "qualification.git"
    first = _helper("prepare-source", "--checkout", os.fspath(checkout), "--bare", os.fspath(bare))
    assert first.returncode == 0, first.stderr
    flake = json.loads(first.stdout)["flake"]
    commit = _git(bare, "rev-parse", "refs/heads/main").strip()
    assert flake == f"git+file://{bare}?ref=main&rev={commit}"
    assert _git(bare, "ls-tree", "-r", "--name-only", commit).split() == [
        ".gitignore", "flake.nix", "libexec/tool.py", "untracked.md"]
    assert (_git(checkout, "rev-parse", "HEAD"), (checkout / ".git/index").read_bytes(),
            _git(checkout, "status", "--porcelain=v1", "--untracked-files=all")) == before
    (checkout / "untracked.md").write_text("changed\n")
    second = _helper("prepare-source", "--checkout", os.fspath(checkout), "--bare", os.fspath(bare))
    assert json.loads(second.stdout)["flake"] != flake and second.returncode == 0
    (checkout / "claude").mkdir()
    (checkout / "claude/settings.json").write_text("{}\n")
    refused = _helper("prepare-source", "--checkout", os.fspath(checkout), "--bare", os.fspath(bare))
    assert (refused.returncode, refused.stderr) == (
        1, "apg-qualify-nix: operator settings would enter the qualification source\n")


def test_eval_foreign_evaluates_only_the_non_native_systems(fake_nix: dict[str, str]) -> None:
    completed = _helper("eval-foreign", "--flake", "git+https://example.invalid/apgr-source.git", "--native", "aarch64-darwin", env=fake_nix)
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        system: {"name": f"drv:{system}.default.name", "drv_path": f"drv:{system}.default.drvPath",
                 "evidence": "evaluation_and_instantiation"}
        for system in ("aarch64-linux", "x86_64-linux")}
    assert all(call[:3] == ["eval", "--no-update-lock-file", "--no-write-lock-file"] for call in _calls(fake_nix))


def test_local_failure_reports_the_step_and_removes_the_disposable_profile(tmp_path: Path,
                                                                           fake_nix: dict[str, str]) -> None:
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    fault = {**fake_nix, "FAKE_NIX_FAULT": json.dumps({"fail": ["profile", "add"]})}
    completed = _helper("local", "--flake", "git+https://example.invalid/apgr-source.git", "--scratch", os.fspath(scratch),
                        "--system", "aarch64-darwin", env=fault)
    assert completed.returncode == 1
    assert completed.stderr == "apg-qualify-nix: nix profile add failed: stand-in nix refusal\n"
    profile = os.fspath(scratch.resolve() / "nix-profile/profile")
    calls = _calls(fake_nix)
    assert [call[:2] for call in calls] == [["flake", "check"], ["build", "--no-update-lock-file"],
                                            ["run", "--no-update-lock-file"], ["profile", "add"]]
    assert calls[-1][:3] == ["profile", "add", "--profile"] and calls[-1][3] == profile
    assert not (scratch / "nix-profile").exists()


def test_local_refuses_scratch_inside_a_default_profile_root_before_any_nix_call(tmp_path: Path,
                                                                                fake_nix: dict[str, str]) -> None:
    scratch = Path(fake_nix["HOME"]) / ".nix-profile/inside"
    scratch.mkdir(parents=True)
    completed = _helper("local", "--flake", "git+https://example.invalid/apgr-source.git", "--scratch", os.fspath(scratch),
                        "--system", "x86_64-linux", env=fake_nix)
    assert completed.returncode == 1
    assert completed.stderr.startswith("apg-qualify-nix: scratch overlaps a default Nix profile root: ")
    assert _calls(fake_nix) == []


@pytest.mark.parametrize("arguments, fault, diagnostic", [
    (("--tag", "0.13.0", "--expect-rev", REV), {}, "readback requires an exact release tag such as v0.13.0"),
    (("--tag", "v0.13.0", "--expect-rev", "HEAD"), {}, "--expect-rev must be a 40-character lowercase commit"),
    (("--tag", "v0.13.0", "--expect-rev", "2" * 40), {}, f"tag v0.13.0 resolves to {REV}, expected {'2' * 40}"),
    (("--tag", "v0.13.0", "--expect-rev", REV), {"metadata": {"unlocked": {}}},
     "flake metadata for v0.13.0 is malformed"),
    (("--tag", "v0.13.0", "--expect-rev", REV), {"metadata": {"locked": {"rev": REV, "narHash": "md5-x"}}},
     "flake metadata for v0.13.0 has no sha256 narHash"),
])
def test_readback_binds_the_tag_to_one_expected_revision_before_qualifying(
        tmp_path: Path, fake_nix: dict[str, str], arguments, fault, diagnostic) -> None:
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    completed = _helper("readback", *arguments, "--scratch", os.fspath(scratch), "--system", "aarch64-darwin",
                        env={**fake_nix, "FAKE_NIX_FAULT": json.dumps(fault)})
    assert (completed.returncode, completed.stderr) == (1, f"apg-qualify-nix: {diagnostic}\n")
    calls = _calls(fake_nix)
    assert all(call[:2] == ["flake", "metadata"] for call in calls)
    if calls:
        assert calls == [["flake", "metadata", "--json", "--refresh",
                          "github:Knowledge-Forge-AI/agentic-praxis-grimoire/v0.13.0"]]
    assert list(scratch.iterdir()) == []


def _qualified(tmp_path: Path, fake_nix: dict[str, str], *arguments: str, **fault: object):
    package = _standin_package(tmp_path / "package")
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    env = {**fake_nix, "FAKE_NIX_PACKAGE": os.fspath(package), "FAKE_NIX_FAULT": json.dumps(fault)}
    return _helper(*arguments, "--scratch", os.fspath(scratch), "--system", "aarch64-darwin", env=env), scratch


def test_local_qualifies_store_and_disposable_profile_through_the_real_smoke(tmp_path: Path,
                                                                            fake_nix: dict[str, str]) -> None:
    completed, scratch = _qualified(tmp_path, fake_nix, "local", "--flake", "git+https://example.invalid/apgr-source.git")
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    profile = scratch.resolve() / "nix-profile/profile"
    assert result["profile"] == os.fspath(profile) and result["profile_removed"] is True
    assert result["profile_elements"] == ["agentic-praxis-grimoire"]
    assert [step["argv"][:2] for step in result["steps"]] == [
        ["nix", "flake"], ["nix", "build"], ["nix", "run"], ["nix", "profile"], ["nix", "profile"]]
    for label in ("store_smoke", "profile_smoke"):
        assert result[label]["controller_generation"]["reason"] == "installed_immutable_runtime"
    assert _calls(fake_nix)[-1] == ["profile", "remove", "--profile", os.fspath(profile), "--all"]
    assert not profile.parent.exists()


def test_readback_qualifies_only_the_resolved_revision(tmp_path: Path, fake_nix: dict[str, str]) -> None:
    completed, _ = _qualified(tmp_path, fake_nix, "readback", "--tag", "v0.13.0", "--expect-rev", REV)
    assert completed.returncode == 0, completed.stderr
    readback = json.loads(completed.stdout)["readback"]
    assert readback == {"tag": "v0.13.0", "expected_rev": REV, "locked_rev": REV, "nar_hash": "sha256-x",
                        "pinned_flake": f"github:Knowledge-Forge-AI/agentic-praxis-grimoire/{REV}",
                        "version": "0.13.0", "system": "aarch64-darwin", "evidence": "native-execution"}
    pinned = f"github:Knowledge-Forge-AI/agentic-praxis-grimoire/{REV}"
    assert all(pinned in " ".join(call) for call in _calls(fake_nix)[1:-2])


@pytest.mark.parametrize("fault, diagnostic", [
    ({"version": "apgr 0.12.9"}, "tagged apgr reported 'apgr 0.12.9', expected apgr 0.13.0"),
])
def test_readback_refuses_a_tagged_runtime_reporting_another_version(tmp_path: Path, fake_nix: dict[str, str],
                                                                     fault: dict, diagnostic: str) -> None:
    completed, scratch = _qualified(tmp_path, fake_nix, "readback", "--tag", "v0.13.0", "--expect-rev", REV,
                                    **fault)
    assert (completed.returncode, completed.stderr) == (1, f"apg-qualify-nix: {diagnostic}\n")
    assert not (scratch / "nix-profile").exists()
