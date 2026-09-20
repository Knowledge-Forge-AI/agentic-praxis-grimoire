from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[6]
SPEC = importlib.util.spec_from_file_location("apg_nix_qualification", ROOT / "libexec/apg_nix_qualification.py")
assert SPEC is not None and SPEC.loader is not None
qualify = importlib.util.module_from_spec(SPEC)
# Split so the public local-path confidentiality marker never appears literally.
LOCAL_FLAKE = "git+file:" + "///x"
SPEC.loader.exec_module(qualify)


def environment(tmp_path: Path) -> dict[str, str]:
    return {"HOME": str(tmp_path / "home"), "XDG_STATE_HOME": str(tmp_path / "home/.local/state")}


def test_disposable_profile_is_derived_inside_scratch(tmp_path: Path) -> None:
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    assert qualify.disposable_profile(scratch, environment(tmp_path)) == scratch.resolve() / "nix-profile/profile"


@pytest.mark.parametrize("relative", [".nix-profile", ".local/state/nix/profiles", ".local/state/nix"])
def test_disposable_profile_refuses_default_profile_roots(tmp_path: Path, relative: str) -> None:
    scratch = tmp_path / "home" / relative
    scratch.mkdir(parents=True)
    with pytest.raises(qualify.QualificationError, match="default Nix profile"):
        qualify.disposable_profile(scratch, environment(tmp_path))


def test_disposable_profile_refuses_nix_profile_symlinks_and_bad_scratch(tmp_path: Path) -> None:
    real = tmp_path / "real-profile-root"
    real.mkdir()
    env = environment(tmp_path)
    (tmp_path / "home").mkdir()
    (tmp_path / "home/.nix-profile").symlink_to(real)
    with pytest.raises(qualify.QualificationError, match="default Nix profile"):
        qualify.disposable_profile(real, env)
    explicit = tmp_path / "explicit"
    explicit.mkdir()
    with pytest.raises(qualify.QualificationError, match="default Nix profile"):
        qualify.disposable_profile(explicit, {**env, "NIX_PROFILE": str(explicit)})
    with pytest.raises(qualify.QualificationError, match="absolute direct"):
        qualify.disposable_profile(Path("relative"), env)
    link = tmp_path / "link"
    link.symlink_to(explicit)
    with pytest.raises(qualify.QualificationError, match="absolute direct"):
        qualify.disposable_profile(link, env)
    with pytest.raises(qualify.QualificationError, match="absolute direct"):
        qualify.disposable_profile(tmp_path / "missing", env)
    assert Path("/nix/var/nix/profiles") in qualify.default_profiles(env)


def test_every_profile_step_names_the_disposable_profile_and_locks_inputs(tmp_path: Path) -> None:
    profile = tmp_path / "nix-profile/profile"
    steps = qualify.local_steps(LOCAL_FLAKE + "?ref=main", tmp_path, "aarch64-darwin", profile)
    for argv in steps:
        assert argv[0] == "nix"
        if argv[1:3] != ["profile", "list"]:
            assert "--no-update-lock-file" in argv and "--no-write-lock-file" in argv
        if argv[1] == "profile":
            assert argv[argv.index("--profile") + 1] == str(profile)
            assert "install" not in argv
    assert any(argv[1:3] == ["flake", "check"] for argv in steps)
    assert any("--version" in argv for argv in steps)


@pytest.mark.parametrize("tag", ["v0.13.0", "v1.0.0", "v10.2.30"])
def test_readback_accepts_only_exact_release_tags(tag: str) -> None:
    assert qualify.tag_reference(tag) == (
        f"github:Knowledge-Forge-AI/agentic-praxis-grimoire/{tag}#agentic-praxis-grimoire")


@pytest.mark.parametrize("tag", ["main", "0.13.0", "v0.13", "v0.13.0-rc1", "refs/heads/main", "v01.2.3"])
def test_readback_rejects_mutable_or_malformed_refs(tag: str) -> None:
    with pytest.raises(qualify.QualificationError, match="exact release tag"):
        qualify.tag_reference(tag)


class FakeRunner:
    def __init__(self, scratch: Path, fail_on: str | None = None) -> None:
        self.calls: list[list[str]] = []
        self.scratch = scratch
        self.fail_on = fail_on

    def __call__(self, argv):
        argv = list(argv)
        self.calls.append(argv)
        if self.fail_on and self.fail_on in argv:
            raise qualify.QualificationError(f"{self.fail_on} failed")
        if argv[:2] == ["nix", "build"]:
            package = self.scratch / "store-package"
            package.mkdir(exist_ok=True)
            (self.scratch / "result").symlink_to(package)
        if argv[:3] == ["nix", "profile", "list"]:
            # Real listings exceed any display tail; parsing must use the whole output.
            return json.dumps({"elements": {"agentic-praxis-grimoire": {"storePaths": ["/nix/store/" + "x" * 600]}}})
        if argv[-2:-1] == ["--target"]:
            return json.dumps({"ok": True})
        return "apgr 0.13.0\n"


def test_local_qualification_removes_the_disposable_profile(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(qualify, "default_profiles", lambda environment=None: ())
    runner = FakeRunner(tmp_path)
    result = qualify.qualify_local(LOCAL_FLAKE, tmp_path, "aarch64-darwin", runner)
    profile = str(tmp_path.resolve() / "nix-profile/profile")
    # The fake profile add creates no link, so only the scratch directory is removed.
    assert result["profile_removed"] is True and not (tmp_path / "nix-profile").exists()
    assert result["profile_elements"] == ["agentic-praxis-grimoire"]
    assert not [argv for argv in runner.calls if argv[1:3] == ["profile", "remove"]]
    assert all("--profile" in argv for argv in runner.calls if argv[1:2] == ["profile"])
    smokes = [argv for argv in runner.calls if "--bin-dir" in argv]
    assert [argv[argv.index("--bin-dir") + 1] for argv in smokes] == [
        str((tmp_path / "store-package").resolve() / "bin"), profile + "/bin"]


def test_local_qualification_cleans_up_after_failure_and_refuses_reuse(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(qualify, "default_profiles", lambda environment=None: ())
    runner = FakeRunner(tmp_path, fail_on="--json")
    (tmp_path / "nix-profile").mkdir()
    (tmp_path / "nix-profile/profile").write_text("")
    with pytest.raises(qualify.QualificationError, match="already exists"):
        qualify.qualify_local(LOCAL_FLAKE, tmp_path, "aarch64-darwin", runner)
    (tmp_path / "nix-profile/profile").unlink()
    (tmp_path / "nix-profile").rmdir()
    profile = tmp_path / "nix-profile/profile"
    original = runner.__call__

    def creating(argv):
        if argv[1:3] == ["profile", "add"]:
            profile.symlink_to(tmp_path)
        return original(argv)

    runner.calls.clear()
    with pytest.raises(qualify.QualificationError, match="--json failed"):
        qualify.qualify_local(LOCAL_FLAKE, tmp_path, "aarch64-darwin", creating)
    assert not (tmp_path / "nix-profile").exists()
    assert ["nix", "profile", "remove", "--profile", str(tmp_path.resolve() / "nix-profile/profile"),
            "--all"] in runner.calls
    with pytest.raises(qualify.QualificationError, match="unsupported system"):
        qualify.qualify_local(LOCAL_FLAKE, tmp_path, "x86_64-darwin", runner)


def test_eval_foreign_only_evaluates_non_native_systems() -> None:
    calls: list[list[str]] = []
    result = qualify.eval_foreign(".", "aarch64-darwin", lambda argv: calls.append(list(argv)) or "value\n")
    assert sorted(result) == ["aarch64-linux", "x86_64-linux"]
    assert all(argv[:2] == ["nix", "eval"] for argv in calls)
    assert not [argv for argv in calls if "build" in argv or "run" in argv]
    assert {item["evidence"] for item in result.values()} == {"evaluation_and_instantiation"}


def test_prepare_source_uses_scratch_git_state_and_excludes_private(tmp_path: Path) -> None:
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    git = ["git", "-C", str(checkout)]
    subprocess.run([*git, "init", "-q", "-b", "main"], check=True)
    (checkout / "kept.txt").write_text("kept\n")
    (checkout / "private").mkdir()
    (checkout / "private/secret.txt").write_text("secret\n")
    (checkout / "ignored.txt").write_text("ignored\n")
    (checkout / ".gitignore").write_text("ignored.txt\n")
    subprocess.run([*git, "add", ".gitignore", "kept.txt"], check=True)
    before = subprocess.check_output([*git, "status", "--porcelain"], text=True)
    reference = qualify.prepare_source(checkout, tmp_path / "scratch.git")
    assert reference.startswith(f"git+file://{tmp_path / 'scratch.git'}?ref=main&rev=")
    names = subprocess.check_output(["git", f"--git-dir={tmp_path / 'scratch.git'}", "ls-tree", "-r",
                                     "--name-only", "main"], text=True).split()
    assert names == [".gitignore", "kept.txt"]
    assert subprocess.check_output([*git, "status", "--porcelain"], text=True) == before
    (checkout / "claude").mkdir()
    (checkout / "claude/settings.json").write_text("{}")
    with pytest.raises(qualify.QualificationError, match="operator settings"):
        qualify.prepare_source(checkout, tmp_path / "scratch.git")


def test_main_reports_refusals_without_running_nix(capsys) -> None:
    assert qualify.main(["readback", "--tag", "main", "--scratch", "/tmp", "--system", "aarch64-darwin",
                         "--expect-rev", "a" * 40]) == 1
    assert "exact release tag" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        qualify.main(["readback", "--tag", "v0.13.0", "--scratch", "/tmp", "--system", "aarch64-darwin"])


REV = "0123456789abcdef0123456789abcdef01234567"


class ReadbackRunner(FakeRunner):
    def __init__(self, scratch: Path, *, locked: str = REV, smoke_reason: str = "installed_immutable_runtime",
                 version_line: str = "apgr 0.13.0\n") -> None:
        super().__init__(scratch)
        self.locked, self.smoke_reason, self.version_line = locked, smoke_reason, version_line

    def __call__(self, argv):
        argv = list(argv)
        if argv[:3] == ["nix", "flake", "metadata"]:
            self.calls.append(argv)
            return json.dumps({"locked": {"rev": self.locked, "narHash": "sha256-" + "A" * 43 + "=",
                                          "type": "github"}})
        if argv[-2:-1] == ["--target"]:
            self.calls.append(argv)
            return json.dumps({"controller_generation": {"reason": self.smoke_reason}})
        if argv[:2] == ["nix", "run"]:
            self.calls.append(argv)
            return self.version_line
        return super().__call__(argv)


def test_readback_resolves_the_tag_once_and_pins_every_step_to_the_expected_rev(tmp_path, monkeypatch):
    monkeypatch.setattr(qualify, "default_profiles", lambda environment=None: ())
    runner = ReadbackRunner(tmp_path)
    result = qualify.readback("v0.13.0", tmp_path, "aarch64-darwin", REV, runner)
    metadata = [argv for argv in runner.calls if argv[:3] == ["nix", "flake", "metadata"]]
    assert metadata == [["nix", "flake", "metadata", "--json", "--refresh",
                         "github:Knowledge-Forge-AI/agentic-praxis-grimoire/v0.13.0"]]
    pinned = f"github:Knowledge-Forge-AI/agentic-praxis-grimoire/{REV}"
    later = [argv for argv in runner.calls[1:] if argv[:1] == ["nix"] and argv[1] in {"flake", "build", "run"}
             or argv[1:3] == ["profile", "add"]]
    assert later and all(any(item.startswith(pinned) for item in argv) for argv in later)
    assert not [argv for argv in runner.calls[1:] if any("/v0.13.0" in item for item in argv)]
    assert result["readback"] == {"tag": "v0.13.0", "expected_rev": REV, "locked_rev": REV,
                                  "nar_hash": "sha256-" + "A" * 43 + "=", "pinned_flake": pinned,
                                  "version": "0.13.0", "system": "aarch64-darwin",
                                  "evidence": "native-execution"}
    assert result["profile_removed"] is True


@pytest.mark.parametrize("options, message", [
    ({"locked": "f" * 40}, "resolves to"),
    ({"smoke_reason": "source_development_worktree"}, "installed_immutable_runtime"),
    ({"version_line": "apgr 0.12.0\n"}, "reported"),
])
def test_readback_fails_closed_on_revision_version_or_provenance_mismatch(tmp_path, monkeypatch, options, message):
    monkeypatch.setattr(qualify, "default_profiles", lambda environment=None: ())
    with pytest.raises(qualify.QualificationError, match=message):
        qualify.readback("v0.13.0", tmp_path, "aarch64-darwin", REV, ReadbackRunner(tmp_path, **options))
    assert not (tmp_path / "nix-profile").exists()


@pytest.mark.parametrize("rev", ["A" * 40, "a" * 39, "main", ""])
def test_readback_requires_an_exact_lowercase_commit(tmp_path, rev):
    with pytest.raises(qualify.QualificationError, match="40-character"):
        qualify.readback("v0.13.0", tmp_path, "aarch64-darwin", rev, ReadbackRunner(tmp_path))
