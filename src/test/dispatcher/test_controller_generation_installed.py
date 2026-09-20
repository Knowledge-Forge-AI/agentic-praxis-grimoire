"""Installed immutable runtimes run in place with truthful, lease-free provenance."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys

import pytest

import controller_generation as generation
import controller_generation_bootstrap as bootstrap
from agent_phase import bundle_io

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "libexec"))
import apg_nix_distribution as distribution  # noqa: E402


def _set_writable(root: Path, writable: bool) -> None:
    for path in (root, *root.rglob("*")):
        if path.is_symlink():
            continue
        mode = path.stat().st_mode
        if path.is_dir():
            path.chmod(0o755 if writable else 0o555)
        else:
            path.chmod((mode | 0o200) if writable else (mode & ~0o222))


@pytest.fixture
def frozen(tmp_path):
    frozen_roots = []

    def freeze(root: Path) -> Path:
        _set_writable(root, False)
        frozen_roots.append(root)
        return root

    yield freeze
    for root in frozen_roots:
        _set_writable(root, True)


STORE_HASH = "0123456789abcdfghijklmnpqrsvwxyz"  # 32 nix-base32 characters


@pytest.fixture(autouse=True)
def nix_store(tmp_path, monkeypatch):
    """A fake store directory; macOS temporary paths are resolved to be canonical."""
    store = (tmp_path / "nix-store").resolve()
    store.mkdir()
    monkeypatch.setattr(generation, "NIX_STORE_DIR", store)
    return store


def runtime_tree(base: Path, *, marker: dict | None = None, digest: bool = True) -> Path:
    """Create ``<base>/runtime``; pass a store object as ``base`` to be installable."""
    root = base / "runtime"
    (root / "src/agentic_praxis_grimoire").mkdir(parents=True)
    root = root.resolve()
    (root / "src/agentic_praxis_grimoire/VERSION").write_text("9.8.7\n")
    value = {"schema": "apgr.installed-runtime/v1", "distribution": "nix", "runtime_root": str(root),
             "runtime_digest": distribution.runtime_digest(root) if digest else "a" * 64,
             "version": "9.8.7"}
    value.update(marker or {})
    (root / generation.INSTALLED_MARKER).write_text(json.dumps(value))
    return root


def store_runtime(nix_store: Path, frozen, name: str = "apgr", **options) -> Path:
    obj = nix_store / f"{STORE_HASH}-{name}"
    root = runtime_tree(obj, **options)
    frozen(obj)
    return root


def test_read_only_store_object_self_naming_tree_is_installed(nix_store, frozen):
    marker = generation.installed_runtime(store_runtime(nix_store, frozen))
    assert marker is not None and marker["version"] == "9.8.7"


@pytest.mark.parametrize("change", [
    {"version": "9.8.8"}, {"runtime_root": "/elsewhere"}, {"schema": "other"},
    {"runtime_digest": "z" * 64}, {"extra": True}, {"distribution": "homebrew"},
])
def test_marker_contract_mismatch_is_not_installed(nix_store, frozen, change):
    assert generation.installed_runtime(store_runtime(nix_store, frozen, marker=change)) is None


def test_writable_tree_git_ancestor_and_symlink_marker_are_not_installed(nix_store, frozen):
    writable = runtime_tree(nix_store / f"{STORE_HASH}-writable")
    assert generation.installed_runtime(writable) is None

    in_git = nix_store / f"{STORE_HASH}-repo"
    (in_git / ".git").mkdir(parents=True)
    assert generation.installed_runtime(store_runtime(nix_store, frozen, "repo")) is None

    obj = nix_store / f"{STORE_HASH}-linked"
    linked = runtime_tree(obj)
    target = nix_store / "marker.json"
    (linked / generation.INSTALLED_MARKER).rename(target)
    (linked / generation.INSTALLED_MARKER).symlink_to(target)
    frozen(obj)
    assert generation.installed_runtime(linked) is None
    assert generation.installed_runtime(nix_store / "missing") is None


def test_store_binding_rejects_non_store_alias_and_malformed_objects(tmp_path, nix_store, frozen):
    outside = runtime_tree(tmp_path / "outside")
    frozen(tmp_path / "outside")
    assert generation.installed_runtime(outside) is None
    inside = store_runtime(nix_store, frozen)
    alias = tmp_path / "alias"
    alias.symlink_to(inside)
    assert generation.installed_runtime(alias) is None
    for name in ("e" * 32 + "-apgr", "0" * 31 + "-apgr", STORE_HASH, STORE_HASH + "-"):
        obj = nix_store / name
        root = runtime_tree(obj)
        frozen(obj)
        assert generation.nix_store_object(root) is None, name
        assert generation.installed_runtime(root) is None, name
    writable_object = nix_store / f"{STORE_HASH}-writable-object"
    root = frozen(runtime_tree(writable_object))  # runtime frozen, store object writable
    assert generation.installed_runtime(root) is None


def test_marker_outside_the_store_is_refused_not_treated_as_checkout(tmp_path, frozen, monkeypatch):
    root = runtime_tree(tmp_path / "copy")
    frozen(tmp_path / "copy")
    monkeypatch.setattr(sys, "argv", ["agent-phase-dispatch", "dispatch", "REQUEST.json"])
    monkeypatch.setattr(bootstrap, "coordinate", lambda *_a, **_k: pytest.fail("checkout path used"))
    with pytest.raises(RuntimeError, match="not a recognized write-protected Nix store runtime"):
        bootstrap.enter(root)


def test_checkout_without_marker_keeps_the_generation_path(tmp_path, monkeypatch):
    class Reached(Exception):
        pass

    def reached(*_args, **_kwargs):
        raise Reached

    assert not (ROOT / generation.INSTALLED_MARKER).exists()
    monkeypatch.setattr(sys, "argv", ["agent-phase-dispatch", "dispatch", "REQUEST.json"])
    monkeypatch.delenv(generation.LEASE_ENV, raising=False)
    monkeypatch.setattr(bootstrap, "_resume_commit", lambda *_a, **_k: None)
    monkeypatch.setattr(bootstrap, "coordinate", reached)
    with pytest.raises(Reached):
        bootstrap.enter(tmp_path)


def test_installed_entry_verifies_the_recorded_digest(nix_store, frozen, monkeypatch):
    root = store_runtime(nix_store, frozen, digest=False)
    monkeypatch.setattr(sys, "argv", ["agent-phase-dispatch", "dispatch", "REQUEST.json"])
    monkeypatch.setattr(generation, "_development", None)
    with pytest.raises(RuntimeError, match="recorded runtime_digest"):
        bootstrap.enter(root)
    assert generation._development is None


def test_enter_records_installed_provenance_without_git_or_store(tmp_path, nix_store, frozen, monkeypatch):
    root = store_runtime(nix_store, frozen)
    monkeypatch.setattr(sys, "argv", ["agent-phase-dispatch", "dispatch", "REQUEST.json"])
    monkeypatch.setenv(generation.LEASE_ENV, str(tmp_path / "inherited-lease.json"))
    monkeypatch.setenv("PYTHONPATH", "/ambient")
    monkeypatch.setattr(generation, "_development", None)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("installed runtime must not probe Git or open a generation store")

    monkeypatch.setattr(bootstrap.subprocess, "run", forbidden)
    monkeypatch.setattr(bootstrap, "coordinate", forbidden)
    monkeypatch.setattr(bootstrap, "materialize", forbidden)
    bootstrap.enter(root)
    record = generation.provenance("run-1")
    assert record["reason"] == "installed_immutable_runtime"
    assert record["commit"] is None and record["tree"] is None
    assert record["safety_established"] is False and record["generation_root"] is None
    assert record["controller_root"] == str(root) and record["runtime_version"] == "9.8.7"
    assert record["run_id"] == "run-1"
    assert generation.LEASE_ENV not in os.environ and "PYTHONPATH" not in os.environ
    assert os.environ["PYTHONDONTWRITEBYTECODE"] == "1"


def test_installed_runtime_refuses_generation_pinned_resume(tmp_path, nix_store, frozen, monkeypatch):
    root = store_runtime(nix_store, frozen)
    prior = tmp_path / "prior"
    prior.mkdir()
    (prior / "state.json").write_text(json.dumps({"controller_generation": {"safety_established": True}}))
    monkeypatch.setattr(sys, "argv", ["agent-phase-dispatch", "dispatch", "REQUEST.json", "--resume", str(prior)])
    with pytest.raises(RuntimeError, match="generation-pinned"):
        bootstrap.enter(root)
    (prior / "state.json").write_text(json.dumps({"controller_generation": {
        "safety_established": False, "reason": "installed_immutable_runtime"}}))
    monkeypatch.setattr(generation, "_development", None)
    bootstrap.enter(root)
    assert generation.provenance()["reason"] == "installed_immutable_runtime"


def test_resume_scans_every_prior_argument(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    for path, safe in ((first, False), (second, True)):
        path.mkdir()
        (path / "state.json").write_text(json.dumps({"controller_generation": {"safety_established": safe}}))
    found = bootstrap._prior_generations(["--resume", str(first), f"--run={second}"])
    assert [item["safety_established"] for item in found] == [False, True]
    (first / "state.json").write_text(json.dumps({"controller_generation": "corrupted"}))
    (second / "state.json").write_text("[]")
    assert bootstrap._prior_generations(["--resume", str(first), "--run", str(second)]) == [{}, {}]


def test_bundle_immutable_policy_is_limited_to_installed_source_defaults(tmp_path, monkeypatch):
    assert bundle_io.installed_source_defaults(ROOT / "common/dispatcher") is False
    assert bundle_io.installed_source_defaults(tmp_path) is False
    member = tmp_path / "models.toml"
    member.write_text("x = 1\n")
    os.link(member, tmp_path / "alias.toml")
    with pytest.raises(bundle_io.BundleError, match="multiple hard links"):
        bundle_io.validate_regular_file(Path("models.toml"), member.lstat())
    bundle_io.validate_regular_file(Path("models.toml"), member.lstat(), immutable=True)

    # A foreign owner is accepted only for a trusted immutable owner without write bits.
    monkeypatch.setattr(bundle_io.os, "geteuid", lambda: os.getuid() + 1)
    monkeypatch.setattr(bundle_io, "TRUSTED_IMMUTABLE_OWNERS", (os.getuid(),))
    with pytest.raises(bundle_io.BundleError, match="not owned"):
        bundle_io.validate_regular_file(Path("models.toml"), member.lstat(), immutable=True)
    member.chmod(0o444)
    bundle_io.validate_regular_file(Path("models.toml"), member.lstat(), immutable=True)
    (tmp_path / "alias.toml").unlink()
    with pytest.raises(bundle_io.BundleError, match="not owned"):
        bundle_io.validate_regular_file(Path("models.toml"), member.lstat())
    monkeypatch.setattr(bundle_io, "TRUSTED_IMMUTABLE_OWNERS", (0,))
    with pytest.raises(bundle_io.BundleError, match="not owned"):
        bundle_io.validate_regular_file(Path("models.toml"), member.lstat(), immutable=True)


# Linux Nix build sandbox: the builder is uid 1000 in a one-uid user namespace,
# so the unmapped host-root owner of /nix/store reports the overflow uid.
SANDBOX_PROC = {"/proc/sys/kernel/overflowuid": "65534\n",
                "/proc/self/uid_map": "      1000      30001          1\n"}


def _sandbox_member(tmp_path, monkeypatch, *, proc=SANDBOX_PROC, system="Linux", uid=65534, mode=0o444):
    def read(path):
        if path not in proc:
            raise FileNotFoundError(path)
        return proc[path]

    monkeypatch.setattr(bundle_io.platform, "system", lambda: system)
    monkeypatch.setattr(bundle_io, "_read_proc", read)
    monkeypatch.setattr(bundle_io.os, "geteuid", lambda: 1000)
    member = tmp_path / "models.toml"
    member.write_text("x = 1\n")
    fields = list(member.lstat())
    fields[stat.ST_MODE], fields[stat.ST_UID] = stat.S_IFREG | mode, uid
    return os.stat_result(fields)


def test_immutable_store_member_owned_by_unmapped_sandbox_owner_is_accepted(tmp_path, monkeypatch):
    value = _sandbox_member(tmp_path, monkeypatch)
    bundle_io.validate_regular_file(Path("models.toml"), value, immutable=True)


@pytest.mark.parametrize("case", [
    "identity-map", "uid-range-map", "owner-writable", "group-writable", "not-immutable",
    "foreign-uid", "darwin", "proc-unreadable", "uid-map-malformed", "uid-map-empty", "overflow-differs",
    "uid-map-late-row-maps-overflow",
])
def test_unmapped_owner_exception_is_refused_outside_the_sandboxed_immutable_store(tmp_path, monkeypatch, case):
    proc, options, immutable = dict(SANDBOX_PROC), {}, True
    if case == "identity-map":
        proc["/proc/self/uid_map"] = "         0          0 4294967295\n"
    elif case == "uid-range-map":  # auto-allocate-uids: 65534 is a real namespace account
        proc["/proc/self/uid_map"] = "         0     872415232      65536\n"
    elif case == "owner-writable":
        options["mode"] = 0o644
    elif case == "group-writable":
        options["mode"] = 0o464
    elif case == "not-immutable":
        immutable = False
    elif case == "foreign-uid":
        options["uid"] = 1234
    elif case == "darwin":
        options["system"] = "Darwin"
    elif case == "proc-unreadable":
        proc = {}
    elif case == "uid-map-malformed":
        proc["/proc/self/uid_map"] = "1000 30001\n"
    elif case == "uid-map-empty":
        proc["/proc/self/uid_map"] = "\n"
    elif case == "overflow-differs":
        proc["/proc/sys/kernel/overflowuid"] = "65533\n"
    elif case == "uid-map-late-row-maps-overflow":  # the kernel allows 340 rows; read them all
        rows = "".join(f"{100000 + 10 * index:>10} {200000 + 10 * index:>10} {1:>10}\n" for index in range(339))
        proc["/proc/self/uid_map"] = rows + f"{65534:>10} {300000:>10} {1:>10}\n"
    value = _sandbox_member(tmp_path, monkeypatch, proc=proc, **options)
    with pytest.raises(bundle_io.BundleError, match=r"not owned by effective account \(uid \d+ != 1000\)"):
        bundle_io.validate_regular_file(Path("models.toml"), value, immutable=immutable)


def test_proc_records_are_read_whole_or_refused(tmp_path):
    record = tmp_path / "uid_map"
    record.write_text("x" * (bundle_io._PROC_RECORD_LIMIT - 1) + "\n")
    assert len(bundle_io._read_proc(str(record))) == bundle_io._PROC_RECORD_LIMIT
    record.write_text("x" * bundle_io._PROC_RECORD_LIMIT + "\n")
    with pytest.raises(ValueError, match="exceeds its bounded size"):
        bundle_io._read_proc(str(record))


def test_unmapped_owner_reads_this_host_namespace_without_admitting_it():
    # On Darwin the predicate is closed; in an initial Linux namespace every uid is mapped.
    assert bundle_io._unmapped_owner(65534) is False
    assert bundle_io._unmapped_owner(os.getuid()) is False


def _copy_runtime(target: Path) -> Path:
    data = distribution.load_distribution(ROOT)
    names = subprocess.check_output(["git", "-C", str(ROOT), "ls-files", "-z", "--", *data["runtime"]],
                                    text=True).split("\0")
    for name in filter(None, names):
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, destination)
    return target.resolve()


def test_copied_read_only_runtime_outside_the_store_is_refused(tmp_path, frozen):
    """A copy with a valid marker is not an installed runtime; the real-store
    dry-run is qualified by the flake ``installed-smoke`` check."""
    runtime = _copy_runtime(tmp_path / "install" / "runtime")
    (runtime / generation.INSTALLED_MARKER).write_bytes(distribution.render_marker(runtime))
    frozen(tmp_path / "install")
    base = tmp_path / "isolated"
    candidate = base / "candidate"
    candidate.mkdir(parents=True)
    env = {"PATH": os.environ["PATH"], "HOME": str(base / "home"), "APGR_HOME": str(base / "apgr-home"),
           "APGR_OUTBOX_ROOT": str(base / "outbox"), "TMPDIR": str(base)}
    (base / "home").mkdir()
    for arguments in (["init", "-q", "-b", "main"], ["config", "user.name", "Fixture"],
                      ["config", "user.email", "fixture@example.invalid"]):
        subprocess.run(["git", "-C", str(candidate), *arguments], check=True, env=env)
    (candidate / "file.txt").write_text("fixture\n")
    subprocess.run(["git", "-C", str(candidate), "add", "."], check=True, env=env)
    subprocess.run(["git", "-C", str(candidate), "commit", "-qm", "base"], check=True, env=env)
    request = base / "SMOKE.json"
    request.write_text(json.dumps({"schema": "agent-phase-request-v1", "phase_type": "implementation_testing",
                                   "execution_mode": "codex_only", "prompt": "Provider-free fixture"}))
    before = sorted(p.relative_to(runtime).as_posix() for p in runtime.rglob("*"))
    result = subprocess.run([str(runtime / "bin/agent-phase-dispatch"), str(request), "--dry-run",
                             "--lifecycle", "work-reviewed", "--finalization", "checkpoint"],
                            cwd=candidate, env=env, capture_output=True, text=True, timeout=120)
    assert result.returncode != 0
    # The launcher reports only the error class; the in-process test pins the text.
    assert "generation binding failed (RuntimeError)" in result.stderr
    assert not list((base / "outbox").rglob("state.json"))
    assert not any(path.name == "generations" for path in base.rglob("*"))
    assert sorted(p.relative_to(runtime).as_posix() for p in runtime.rglob("*")) == before
