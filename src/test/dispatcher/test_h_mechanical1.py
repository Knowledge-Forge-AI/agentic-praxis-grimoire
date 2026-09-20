"""APG166V-H-MECHANICAL1 cause-specific regressions.

Each test reproduces one established cause from the retained COMPLETE1 host
transaction with local, non-network inputs:

* scenario-10: a Go oracle command under ``GOPROXY=off`` could not resolve a
  module that was only present in a manifest-bound cache input;
* scenario-15: the fixture ``.bin/tsc`` launcher ``require()``-d a bound
  ``tsc`` that is a bash wrapper on nix hosts;
* the current D1 descriptor refresh changes four digests and its model.

No provider, network, or H transaction is started.
"""
from __future__ import annotations

import base64
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from testing.h_eval import oracles
from testing.h_eval.oracle_commands import ManifestRunner
from testing.h_eval.runtime_manifest import REQUIRED_COMMANDS, REQUIRED_GROUPS, capture_complete, seal

ROOT = Path(__file__).resolve().parents[3]
MODULE = "example.com/fixture/Answer"
ESCAPED = "example.com/fixture/!answer"
VERSION = "v1.0.0"


def _h1(entries):
    summary = "".join(f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in sorted(entries))
    return "h1:" + base64.b64encode(hashlib.sha256(summary.encode()).digest()).decode()


def _tool(directory: Path) -> Path:
    tool = directory / "fake-tool"
    tool.write_text(f"#!{sys.executable}\nprint('fake-tool 0.0-test')\n")
    tool.chmod(0o700)
    return tool


def _runtime(tmp_path: Path, *, real: dict[str, tuple[Path, list[str]]], cache_inputs: list[Path]) -> dict:
    tool = _tool(tmp_path)
    readme = ROOT / "README.md"
    home = tmp_path / "runtime-home"
    home.mkdir()
    groups = {group: [readme] for group in REQUIRED_GROUPS}
    groups["cache_inputs"] = cache_inputs
    commands = {name: real.get(name, (tool, ["--version"])) for name in REQUIRED_COMMANDS}
    return seal(capture_complete(
        providers={name: (tool, ["--version"]) for name in ("codex", "claude", "antigravity")},
        commands=commands, groups=groups, routes={"fixture": "mechanical1"},
        absent_settings=[home / "absent"],
        environment={"home": str(home), "temp_root": str(home), "values": {"CGO_ENABLED": "0"}},
    ))


def _go() -> Path:
    found = shutil.which("go")
    if found is None:
        pytest.skip("local Go toolchain unavailable")
    return Path(found).resolve()


def _module_cache(tmp_path: Path) -> tuple[Path, str]:
    """A minimal Go module-cache download directory plus its go.sum text."""
    download = tmp_path / "modcache" / "cache" / "download" / ESCAPED / "@v"
    download.mkdir(parents=True)
    gomod = f"module {MODULE}\n\ngo 1.25\n".encode()
    source = b"package answer\n\nfunc Value() int { return 42 }\n"
    prefix = f"{MODULE}@{VERSION}/"
    with zipfile.ZipFile(download / f"{VERSION}.zip", "w") as archive:
        archive.writestr(prefix + "go.mod", gomod)
        archive.writestr(prefix + "answer.go", source)
    (download / f"{VERSION}.mod").write_bytes(gomod)
    (download / f"{VERSION}.lock").write_bytes(b"")
    go_sum = (f"{MODULE} {VERSION} {_h1([(prefix + 'go.mod', gomod), (prefix + 'answer.go', source)])}\n"
              f"{MODULE} {VERSION}/go.mod {_h1([('go.mod', gomod)])}\n")
    return download, go_sum


def _go_subject(tmp_path: Path, go_sum: str | None) -> Path:
    subject = tmp_path / "subject"
    (subject / "tests").mkdir(parents=True)
    if go_sum is None:
        (subject / "go.mod").write_text("module fixture/use\n\ngo 1.25\n")
        (subject / "tests/use_test.go").write_text(
            "package tests\nimport \"testing\"\nfunc TestLocal(t *testing.T) {}\n")
        return subject
    (subject / "go.mod").write_text(f"module fixture/use\n\ngo 1.25\n\nrequire {MODULE} {VERSION}\n")
    (subject / "go.sum").write_text(go_sum)
    (subject / "tests/use_test.go").write_text(
        "package tests\nimport (\"testing\"; answer \"" + MODULE + "\")\n"
        "func TestAnswer(t *testing.T) { if answer.Value() != 42 { t.Fatal(\"wrong\") } }\n")
    return subject


def test_go_oracle_command_resolves_manifest_bound_module_offline(tmp_path):
    download, go_sum = _module_cache(tmp_path)
    runtime = _runtime(tmp_path, real={"go": (_go(), ["version"])}, cache_inputs=[download])
    subject = _go_subject(tmp_path, go_sum)
    destination = tmp_path / "command"
    result = ManifestRunner(runtime, subject, destination).run(["go", "test", "./tests/..."], cwd=subject)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert b"module lookup disabled" not in result.stderr
    receipt = json.loads((destination / "command.json").read_bytes())
    seeded = {item["name"]: item for item in receipt["go_module_inputs"]}
    assert set(seeded) == {f"{VERSION}.mod", f"{VERSION}.zip"}
    for name, item in seeded.items():
        data = (download / name).read_bytes()
        assert item["module"] == MODULE and item["version"] == VERSION
        assert item["bytes"] == len(data) and item["sha256"] == hashlib.sha256(data).hexdigest()
        assert item["source"] == str(download / name)
    # Read-only extracted module directories are removed with the run-owned cache.
    assert {path.name for path in destination.iterdir()} == {"command.json", "stdout", "stderr"}
    assert (download / f"{VERSION}.zip").is_file()


def test_go_oracle_command_without_bound_module_still_fails_honestly(tmp_path):
    _download, go_sum = _module_cache(tmp_path)
    runtime = _runtime(tmp_path, real={"go": (_go(), ["version"])}, cache_inputs=[ROOT / "README.md"])
    subject = _go_subject(tmp_path, go_sum)
    destination = tmp_path / "command"
    result = ManifestRunner(runtime, subject, destination).run(["go", "test", "./tests/..."], cwd=subject)
    assert result.returncode != 0
    assert b"module lookup disabled by GOPROXY=off" in result.stderr
    assert "go_module_inputs" not in json.loads((destination / "command.json").read_bytes())


def test_go_oracle_command_without_go_sum_seeds_nothing(tmp_path):
    download, _go_sum = _module_cache(tmp_path)
    runtime = _runtime(tmp_path, real={"go": (_go(), ["version"])}, cache_inputs=[download])
    subject = _go_subject(tmp_path, None)
    destination = tmp_path / "command"
    result = ManifestRunner(runtime, subject, destination).run(["go", "test", "./tests/..."], cwd=subject)
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert "go_module_inputs" not in json.loads((destination / "command.json").read_bytes())


def test_go_module_seed_refuses_bound_input_that_differs_from_inventory(tmp_path, monkeypatch):
    from testing.h_eval import oracle_commands
    download, go_sum = _module_cache(tmp_path)
    runtime = _runtime(tmp_path, real={"go": (_go(), ["version"])}, cache_inputs=[download])
    subject = _go_subject(tmp_path, go_sum)
    entries = runtime["files"][str(download)]["entries"]
    tampered = json.loads(json.dumps(runtime))
    for entry in tampered["files"][str(download)]["entries"]:
        if entry.get("relative_path") == f"{VERSION}.zip":
            entry["sha256"] = "0" * 64
    assert entries != tampered["files"][str(download)]["entries"]
    modules = tmp_path / "gomod"
    modules.mkdir()
    with pytest.raises(ValueError, match="differs from the sealed inventory"):
        oracle_commands.seed_go_modules(tampered, subject, modules)


def _tsc_cache(tmp_path: Path) -> Path:
    cache = tmp_path / "node-cache" / "node_modules"
    for package in ("typescript/bin", "react", "@types/react", "csstype"):
        (cache / package).mkdir(parents=True)
    (cache / "typescript/bin/tsc").write_text("#!/usr/bin/env node\n")
    for package in ("react", "@types/react", "csstype"):
        (cache / package / "package.json").write_text("{}\n")
    return cache


def _wrapper_tsc(tmp_path: Path, bash: Path, node: Path) -> Path:
    """A nix-style bash wrapper that execs Node on the real compiler entry."""
    entry = tmp_path / "compiler" / "tsc.js"
    entry.parent.mkdir()
    entry.write_text(
        "const args = process.argv.slice(2);\n"
        "if (args[0] === '--version') { console.log('Version 0.0-test'); process.exit(0); }\n"
        "console.log('compiled ' + JSON.stringify(args));\n"
        "process.exit(args.includes('--fail') ? 2 : 0);\n")
    wrapper = tmp_path / "compiler" / "tsc"
    wrapper.write_text(f"#! {bash} -e\nexec \"{node}\"  {entry} \"$@\" \n")
    wrapper.chmod(0o755)
    return wrapper


@pytest.mark.parametrize(("arguments", "code"), [(["--noEmit"], 0), (["--noEmit", "--fail"], 2)])
def test_fixture_tsc_launcher_executes_bound_bash_wrapper(tmp_path, arguments, code):
    bash, node = shutil.which("bash"), shutil.which("node")
    if bash is None or node is None:
        pytest.skip("local bash/node unavailable")
    bash, node = Path(bash).resolve(), Path(node).resolve()
    wrapper = _wrapper_tsc(tmp_path, bash, node)
    runtime = _runtime(tmp_path, real={"bash": (bash, ["--version"]), "node": (node, ["--version"]),
                                       "tsc": (wrapper, ["--version"])},
                       cache_inputs=[_tsc_cache(tmp_path)])
    subject = tmp_path / "subject"
    (subject / "frontend").mkdir(parents=True)
    oracles._copy_bound_node_modules(runtime, subject)
    launcher = subject / "frontend/node_modules/.bin/tsc"
    completed = subprocess.run([str(launcher), *arguments], capture_output=True, check=False,
                               env={"PATH": "/nonexistent"})
    assert b"SyntaxError" not in completed.stderr, completed.stderr.decode(errors="replace")
    assert completed.returncode == code
    assert completed.stdout.decode().strip() == "compiled " + json.dumps(arguments, separators=(",", ":"))
    assert launcher.read_text().splitlines()[0] == f"#!{bash}"


def _front_end(monkeypatch):
    from agentic_praxis_grimoire import acquisition
    forwarded = []
    monkeypatch.setattr(acquisition.go_bridge, "run",
                        lambda argv, repository_root: forwarded.append((list(argv), repository_root)) or 0)
    return acquisition, forwarded


def test_python_front_end_forwards_prepare_only_verbatim_without_authority(monkeypatch, tmp_path):
    acquisition, forwarded = _front_end(monkeypatch)
    monkeypatch.setattr(acquisition, "capture_catalog",
                        lambda *args: pytest.fail("prepare-only must not capture a Python catalog"))
    run = tmp_path / "run"
    run.mkdir()
    arguments = ["apgr:go-language-profile", "--prepare-only", "--run-dir", str(run), "--run-id", "r",
                 "--binding-id", "b", "--attempt-id", "a", "--project-root", str(ROOT)]
    assert acquisition.run_channel("skills", "acquire", tuple(arguments), {}) == 0
    assert forwarded == [(["skills", "acquire", *arguments], None)]
    assert list(run.iterdir()) == []


def test_python_front_end_other_acquire_shapes_are_unchanged(monkeypatch, tmp_path):
    acquisition, forwarded = _front_end(monkeypatch)
    monkeypatch.setattr(acquisition, "capture_catalog",
                        lambda start, project, home: ({"schema_version": "apg.skill-catalog/v1"}, []))
    run = tmp_path / "run"
    run.mkdir()
    scope = ["--run-dir", str(run), "--run-id", "r", "--binding-id", "b", "--attempt-id", "a"]
    assert acquisition.run_channel("skills", "acquire", ["apgr:go-language-profile", *scope], {}) == 0
    (argv, root), = forwarded
    assert argv[:3] == ["skills", "acquire", "apgr:go-language-profile"] and argv[3] == "--config"
    assert Path(argv[4]).parent == run and Path(argv[4]).name.startswith("acquisition-authority-")
    assert root is None
    # --prepare-only is recognized only in the native position after the target.
    with pytest.raises(SystemExit):
        acquisition.run_channel("skills", "acquire", ["apgr:go-language-profile", *scope, "--prepare-only"], {})
    with pytest.raises(SystemExit):
        acquisition.run_channel("skills", "search", ["go", "--prepare-only", *scope], {})
    assert len(forwarded) == 1


D1_REFRESHED = ("claude/model-catalog-v1.json", "common/dispatcher/endpoints.toml", "common/dispatcher/routes.toml",
                "common/dispatcher/models.toml")
# Frozen prior descriptor digest with the four source pins and route model
# masked. Equality proves every other field is unchanged.
D1_MASKED_PRIOR_SHA256 = "64f90ecfc43befb17955904f8ac4a5e332cf06bd400f04781a3a308dc3046b5c"


def test_d1_descriptor_refresh_changes_only_declared_pins_and_model():
    descriptor = json.loads((ROOT / "testing/h_eval/d1-descriptor.json").read_bytes())
    for relative in D1_REFRESHED:
        live = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        assert descriptor["source_sha256"][relative] == live, relative
    masked = json.loads(json.dumps(descriptor))
    for relative in D1_REFRESHED:
        masked["source_sha256"][relative] = "<masked>"
    masked["route"]["model"] = "<masked>"
    canonical = json.dumps(masked, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(canonical).hexdigest() == D1_MASKED_PRIOR_SHA256
    assert descriptor["route"]["model"] == "claude-opus-5-5"
    assert descriptor["route"]["profile"] == "normal-final-review"
    assert descriptor["route"]["allowed_native_tools"] == ["Read"]
