"""Private all-provider/runtime identity, with version-only fake executables."""
import copy
import hashlib
import os
import sys

import pytest

from testing.h_eval import runtime_manifest as runtime_owner
from testing.h_eval.runtime_execution import begin
from testing.h_eval.runtime_manifest import (
    REQUIRED_COMMANDS,
    REQUIRED_GROUPS,
    capture_complete,
    expire,
    manifest_digest,
    resolve_executable,
    revalidate,
    seal,
    verify_complete,
)


@pytest.fixture
def manifest(tmp_path):
    executable = tmp_path / "runtime"
    executable.write_text("#!" + sys.executable + "\nimport sys\nassert sys.argv[1:] == ['--version']\nprint('fixture 1')\n")
    executable.chmod(0o700)
    source = tmp_path / "source"; source.write_text("fixture\n")
    providers = {p: (executable, ["--version"]) for p in ("codex", "claude", "antigravity")}
    commands = {name: (executable, ["--version"]) for name in REQUIRED_COMMANDS}
    return capture_complete(providers=providers, commands=commands,
                            groups={g: [source] for g in REQUIRED_GROUPS}, routes={"fixture": "test-only"},
                            absent_settings=[tmp_path / "absent"])


def test_all_runtime_versions_rechecked(manifest):
    assert verify_complete(manifest, probe_versions=True) == manifest


@pytest.mark.parametrize("change", ["provider", "command", "group", "source", "version", "absent", "alias", "executable_mode"])
def test_runtime_manifest_fails_closed(manifest, tmp_path, change):
    value = copy.deepcopy(manifest)
    if change == "provider": value["providers"].remove("codex")
    elif change == "command": value["commands"] = []
    elif change == "group": value["groups"]["projection_inputs"] = []
    elif change == "source": (tmp_path / "source").write_text("changed")
    elif change == "version": value["runtimes"]["codex"]["version_stdout"] = "other"
    elif change == "absent": (tmp_path / "absent").write_text("new settings")
    elif change == "executable_mode": (tmp_path / "runtime").chmod(0o600)
    elif change == "alias":
        old = tmp_path / "source"; new = tmp_path / "other"
        old.rename(new); old.symlink_to(new)
    with pytest.raises(ValueError): verify_complete(value, probe_versions=change != "executable_mode")


def test_manifest_seal_revalidate_expire_and_recapture(manifest, tmp_path):
    captured_digest = manifest_digest(manifest)
    sealed = seal(manifest)
    assert sealed["lifecycle"]["state"] == "sealed"
    assert sealed["lifecycle"]["sealed_sha256"] == captured_digest
    assert revalidate(sealed) == sealed

    (tmp_path / "source").write_text("drift\n")
    with pytest.raises(ValueError, match="drift"):
        revalidate(sealed)

    expired = expire(sealed)
    assert expired["lifecycle"]["state"] == "expired"
    with pytest.raises(ValueError, match="sealed"):
        revalidate(expired)


def test_manifest_records_physical_identity_and_cache_tree(tmp_path):
    executable = tmp_path / "runtime"
    executable.write_text("#!" + sys.executable + "\nimport sys\nassert sys.argv[1:] == ['--version']\nprint('fixture 2')\n")
    executable.chmod(0o750)
    source = tmp_path / "source"; source.write_text("fixture\n")
    cache = tmp_path / "cache"; cache.mkdir(); (cache / "module.txt").write_text("cached\n")
    (cache / ".bin").mkdir(); (cache / ".bin" / "module").symlink_to(cache / "module.txt")
    providers = {p: (executable, ["--version"]) for p in ("codex", "claude", "antigravity")}
    commands = {name: (executable, ["--version"]) for name in REQUIRED_COMMANDS}
    value = capture_complete(
        providers=providers,
        commands=commands,
        groups={group: [cache if group == "cache_inputs" else source] for group in REQUIRED_GROUPS},
        routes={"fixture": "test-only"},
        absent_settings=[tmp_path / "absent"],
        environment={"home": str(tmp_path), "temp_root": str(tmp_path)},
    )
    identity = value["files"][str(executable)]
    assert identity["physical_path"] == str(executable)
    assert identity["device"] == executable.stat().st_dev
    assert identity["inode"] == executable.stat().st_ino
    assert identity["mode"] == 0o750
    assert identity["bytes"] == executable.stat().st_size
    assert identity["sha256"] == hashlib.sha256(executable.read_bytes()).hexdigest()
    assert value["files"][str(cache)]["kind"] == "directory"
    assert any(entry["kind"] == "symlink" for entry in value["files"][str(cache)]["entries"])
    assert value["environment"]["cache_paths"] == [str(cache)]
    assert resolve_executable(seal(value), "python") == str(executable)


def test_directory_symlink_binds_link_target_and_target_tree(manifest, tmp_path):
    target = tmp_path / "sdk"; target.mkdir()
    payload = target / "include.h"; payload.write_text("#define FIXTURE 1\n")
    link = tmp_path / "usr-include"; link.symlink_to(target, target_is_directory=True)
    value = copy.deepcopy(manifest)
    value["files"][str(link)] = runtime_owner._input(link)
    value["groups"]["cache_inputs"] = [str(link)]
    value["environment"]["cache_paths"] = [str(target)]

    identity = value["files"][str(link)]
    assert identity["kind"] == "directory"
    assert identity["link_target"] == str(target)
    assert identity["target_kind"] == "directory"
    assert identity["physical_path"] == str(target)
    assert identity["device"] == target.stat().st_dev
    assert identity["inode"] == target.stat().st_ino
    assert any(entry["relative_path"] == "include.h" for entry in identity["entries"])
    assert verify_complete(value) == value

    alternate = tmp_path / "sdk-alternate"; alternate.mkdir()
    (alternate / "include.h").write_text("#define FIXTURE 1\n")
    link.unlink(); link.symlink_to(alternate, target_is_directory=True)
    with pytest.raises(ValueError, match="drift"):
        verify_complete(value)

    link.unlink(); link.symlink_to(target, target_is_directory=True)
    payload.write_text("#define FIXTURE 2\n")
    with pytest.raises(ValueError, match="drift"):
        verify_complete(value)
    payload.write_text("#define FIXTURE 1\n")
    (target / "new.h").write_text("new\n")
    with pytest.raises(ValueError, match="drift"):
        verify_complete(value)


def test_directory_symlink_old_v2_identity_without_link_fields_remains_readable(manifest, tmp_path):
    target = tmp_path / "sdk"; target.mkdir(); (target / "lib.h").write_text("header\n")
    link = tmp_path / "usr-include"; link.symlink_to(target, target_is_directory=True)
    value = copy.deepcopy(manifest)
    value["files"][str(link)] = runtime_owner._input(link)
    value["groups"]["cache_inputs"] = [str(link)]
    value["environment"]["cache_paths"] = [str(target)]
    legacy = copy.deepcopy(value)
    legacy["files"][str(link)].pop("link_target")
    legacy["files"][str(link)].pop("target_kind")
    assert verify_complete(legacy) == legacy


def test_directory_symlink_cycle_is_rejected(tmp_path):
    root = tmp_path / "root"; root.mkdir()
    (root / "loop").symlink_to(root, target_is_directory=True)
    with pytest.raises(ValueError, match="cycle"):
        runtime_owner._input(root)


@pytest.mark.parametrize("budget_name", ["MAX_DIRECTORY_ENTRIES", "MAX_INPUT_BYTES"])
def test_directory_symlink_target_shares_parent_budget(tmp_path, monkeypatch, budget_name):
    root = tmp_path / "root"; root.mkdir()
    target = tmp_path / "target"; target.mkdir()
    (root / "root.txt").write_text("aa")
    (target / "target.txt").write_text("bb")
    (root / "target-link").symlink_to(target, target_is_directory=True)
    if budget_name == "MAX_DIRECTORY_ENTRIES":
        monkeypatch.setattr(runtime_owner, budget_name, 2)
    else:
        monkeypatch.setattr(runtime_owner, budget_name, 3)
    with pytest.raises(ValueError, match="exceeds bound"):
        runtime_owner._input(root)


def test_version_capture_is_separate_from_task_invocation(tmp_path):
    sentinel = tmp_path / "task-sentinel"
    executable = tmp_path / "version-only"
    executable.write_text(
        "#!" + sys.executable + "\n"
        "from pathlib import Path\n"
        "import sys\n"
        f"sentinel = Path({str(sentinel)!r})\n"
        "if sys.argv[1:] != ['--version']:\n"
        "    sentinel.write_text('task')\n"
        "    raise SystemExit(73)\n"
        "print('version-only')\n"
    )
    executable.chmod(0o700)
    source = tmp_path / "source"; source.write_text("fixture\n")
    providers = {p: (executable, ["--version"]) for p in ("codex", "claude", "antigravity")}
    commands = {name: (executable, ["--version"]) for name in REQUIRED_COMMANDS}
    value = capture_complete(
        providers=providers,
        commands=commands,
        groups={group: [source] for group in REQUIRED_GROUPS},
        routes={"fixture": "test-only"},
        absent_settings=[tmp_path / "absent"],
        environment={"home": str(tmp_path), "temp_root": str(tmp_path)},
    )
    assert not sentinel.exists()
    tx = begin(seal(value), work_dir=tmp_path, home=tmp_path)
    assert tx.run("python", ["--version"], cwd=tmp_path, temp_root=tmp_path).stdout == b"version-only\n"
    with pytest.raises(ValueError, match="provider task invocation"):
        tx.run("claude", ["--task"], cwd=tmp_path, temp_root=tmp_path)
    with pytest.raises(ValueError, match="bounded version owner"):
        tx.run("claude", ["--version"], cwd=tmp_path, temp_root=tmp_path)
    assert not sentinel.exists()
    tx.close()


def test_version_probe_writes_only_private_home_and_tmp(tmp_path):
    installation = tmp_path / "installed"; installation.mkdir()
    executable = installation / "provider"
    executable.write_text(
        "#!" + sys.executable + "\nimport os,sys,json\nfrom pathlib import Path\n"
        "assert sys.argv[1:] == ['--version']\n"
        "home, tmp = Path(os.environ['HOME']), Path(os.environ['TMPDIR'])\n"
        "assert home.parent == tmp.parent == Path.cwd()\n"
        "assert home != Path(sys.argv[0]).parent\n"
        "assert os.environ['TMP'] == os.environ['TEMP'] == str(tmp)\n"
        "(home/'state').write_text('version-state')\n"
        "(tmp/'state').write_text('temporary-state')\n"
        "print(json.dumps({'home':str(home),'tmp':str(tmp)}))\n")
    executable.chmod(0o700)
    receipt = runtime_owner._version_observation(executable, ["--version"],
                                               env={"HOME": str(installation), "TMPDIR": str(installation)})
    import json
    from pathlib import Path
    observed = json.loads(receipt["version_stdout"])
    assert not Path(observed["home"]).exists()
    assert not Path(observed["tmp"]).exists()
    assert sorted(p.name for p in installation.iterdir()) == ["provider"]


def test_network_receipt_does_not_claim_os_confinement(manifest):
    assert manifest["environment"]["network"] == "configured_offline_not_os_enforced"
    assert manifest["environment"]["network_disabled"] is False
    value = copy.deepcopy(manifest)
    value["environment"].update(network="disabled", network_disabled=True)
    with pytest.raises(ValueError, match="OS network confinement"):
        verify_complete(value)


def test_oracle_command_receipt_states_configured_offline_limit(manifest, tmp_path):
    import json
    from testing.h_eval.oracle_commands import ManifestRunner
    destination = tmp_path / "oracle-command"
    result = ManifestRunner(seal(manifest), tmp_path, destination).run(
        ["apgr", "--version"], cwd=tmp_path)
    assert result.returncode == 0
    receipt = json.loads((destination / "command.json").read_bytes())
    assert receipt["network_policy"] == "configured_offline_not_os_enforced"
    assert {path.name for path in destination.iterdir()} == {"command.json", "stdout", "stderr"}


def test_manifest_bound_environment_has_no_ambient_path_or_network(monkeypatch, manifest, tmp_path):
    sealed = seal(manifest)
    monkeypatch.setenv("PATH", "/ambient/path")
    tx = begin(sealed, work_dir=tmp_path, home=tmp_path)
    values = tx.environment(cwd=tmp_path, temp_root=tmp_path)
    assert values["PATH"] != "/ambient/path"
    assert values["PATH"] == __import__("os").pathsep.join(sealed["environment"]["path_dirs"])
    assert values["GOPROXY"] == "off"
    assert values["GOSUMDB"] == "off"
    assert values["npm_config_offline"] == "true"
    assert values["PYTHONNOUSERSITE"] == "1"
    tx.close()


@pytest.mark.parametrize("key", ["HOME", "LD_PRELOAD", "LD_LIBRARY_PATH", "UNBOUND_ENV"])
def test_manifest_environment_rejects_unowned_overrides(manifest, tmp_path, key):
    tx = begin(seal(manifest), work_dir=tmp_path, home=tmp_path)
    with pytest.raises(ValueError, match="owner-approved|boundary"):
        tx.environment(cwd=tmp_path, temp_root=tmp_path, extra={key: str(tmp_path)})
    tx.close()


def test_manifest_environment_allows_run_owned_caches_and_subject_pythonpath(manifest, tmp_path):
    base = tmp_path / "base"; base.mkdir()
    subject = tmp_path / "subject"; subject.mkdir()
    go_cache = tmp_path / "go-cache"; go_cache.mkdir()
    npm_cache = tmp_path / "npm-cache"; npm_cache.mkdir()
    value = copy.deepcopy(manifest)
    value["environment"]["set"]["PYTHONPATH"] = str(base)
    tx = begin(seal(value), work_dir=tmp_path, home=tmp_path)
    values = tx.environment(
        cwd=subject,
        temp_root=tmp_path,
        extra={"GOCACHE": str(go_cache), "npm_config_cache": str(npm_cache), "PYTHONPATH": str(subject)},
    )
    assert values["GOCACHE"] == str(go_cache)
    assert values["npm_config_cache"] == str(npm_cache)
    assert values["PYTHONPATH"] == os.pathsep.join((str(base), str(subject)))
    with pytest.raises(ValueError, match="run-owned"):
        tx.environment(cwd=subject, temp_root=tmp_path, extra={"GOCACHE": str(tmp_path.parent)})
    with pytest.raises(ValueError, match="subject PYTHONPATH"):
        tx.environment(cwd=subject, temp_root=tmp_path, extra={"PYTHONPATH": str(tmp_path.parent)})
    tx.close()


def test_manifest_transaction_runs_bound_command_with_complete_stdin(tmp_path):
    executable = tmp_path / "runtime"
    executable.write_text(
        "#!" + sys.executable + "\n"
        "import sys\n"
        "if sys.argv[1:] == ['--version']:\n"
        "    print('runner 1')\n"
        "else:\n"
        "    sys.stdout.buffer.write(b'argv=' + ' '.join(sys.argv[1:]).encode() + b'\\n')\n"
        "    sys.stdout.buffer.write(sys.stdin.buffer.read())\n"
    )
    executable.chmod(0o700)
    source = tmp_path / "source"; source.write_text("fixture\n")
    providers = {p: (executable, ["--version"]) for p in ("codex", "claude", "antigravity")}
    commands = {name: (executable, ["--version"]) for name in REQUIRED_COMMANDS}
    value = capture_complete(
        providers=providers,
        commands=commands,
        groups={group: [source] for group in REQUIRED_GROUPS},
        routes={"fixture": "test-only"},
        absent_settings=[tmp_path / "absent"],
        environment={"home": str(tmp_path), "temp_root": str(tmp_path)},
    )
    tx = begin(seal(value), work_dir=tmp_path, home=tmp_path)
    result = tx.run("apgr", ["skills", "plan", "--stdin"], stdin=b"complete-plan\n", cwd=tmp_path,
                    temp_root=tmp_path)
    assert result.returncode == 0
    assert result.stdout == b"argv=skills plan --stdin\ncomplete-plan\n"
    assert result.stderr == b""
    tx.close()


def test_transaction_revalidates_only_at_explicit_boundaries(manifest, tmp_path, monkeypatch):
    calls = []
    original = runtime_owner.revalidate

    def counted(value, *, probe_versions=False):
        calls.append(probe_versions)
        return original(value, probe_versions=probe_versions)

    monkeypatch.setattr(runtime_owner, "revalidate", counted)
    tx = begin(seal(manifest), work_dir=tmp_path, home=tmp_path)
    assert len(calls) == 1  # begin
    tx.resolve("apgr")
    tx.environment(cwd=tmp_path, temp_root=tmp_path)
    assert len(calls) == 1  # in-memory consumers do not rescan inventories
    tx.run("apgr", ["--version"], cwd=tmp_path, temp_root=tmp_path)
    assert len(calls) == 3  # one before and one after the command
    tx.close()
    assert len(calls) == 4  # explicit post-transaction close


def test_failed_close_cannot_leave_reusable_transaction(manifest, tmp_path):
    tx = begin(seal(manifest), work_dir=tmp_path, home=tmp_path)
    (tmp_path / "source").write_text("drift")
    with pytest.raises(ValueError, match="drift"):
        tx.close()
    with pytest.raises(ValueError, match="not active"):
        tx.resolve("python")



def test_version_probe_disables_telemetry_in_its_private_config(tmp_path):
    import sys
    from testing.h_eval import runtime_manifest
    script = tmp_path / "version-tool"
    script.write_text("#!" + sys.executable + "\n" + "\n".join([
        "import os,pathlib",
        "home=pathlib.Path(os.environ['HOME'])",
        "config=pathlib.Path(os.environ['XDG_CONFIG_HOME'])",
        "assert config.is_relative_to(home)",
        "assert os.environ['APPDATA']==str(config)",
        "for directory in (config/'go/telemetry',home/'Library/Application Support/go/telemetry'):",
        "    assert (directory/'mode').read_text().strip()=='off'",
        "print('private-version 1')",
    ]) + "\n")
    script.chmod(0o700)
    observation = runtime_manifest._version_observation(script, ["--version"], env={
        "XDG_CONFIG_HOME": str(tmp_path / "operator-config"),
        "APPDATA": str(tmp_path / "operator-config"),
    })
    assert observation["version_stdout"] == "private-version 1"
    assert not (tmp_path / "operator-config").exists()
