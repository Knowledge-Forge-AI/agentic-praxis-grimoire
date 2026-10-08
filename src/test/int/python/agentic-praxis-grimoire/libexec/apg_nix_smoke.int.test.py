"""The installed-output smoke as a real process against stand-in commands.

The commands under test are stand-ins for one installed APGR output: small
executables that honor the installed command contract and can be told to
break it. The smoke itself, its isolated environment, the provider sentinels
and every child process are real. A real Nix store output is qualified by the
flake checks, not here.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
SMOKE = ROOT / "libexec/apg_nix_smoke.py"
RUNTIME = "share/agentic-praxis-grimoire/runtime"
DIGEST = "a" * 64

# One stand-in serves every installed command; ``argv[0]`` selects the role.
COMMAND = r'''
import json, os, subprocess, sys
from pathlib import Path
package = Path(__file__).resolve().parents[1]
runtime = package / "share/agentic-praxis-grimoire/runtime"
fault = json.loads((package / "fault.json").read_text())
name, arguments = Path(sys.argv[0]).name, sys.argv[1:]
(package / ("environment-" + name)).write_text(json.dumps(dict(os.environ)))
if fault.get("fail") == name:
    print("stand-in failure", file=sys.stderr)
    raise SystemExit(3)
if name == "apgr":
    if arguments == ["--version"]:
        print("apgr " + fault.get("version", (runtime / "src/agentic_praxis_grimoire/VERSION").read_text().strip()))
    elif arguments == ["build-info"]:
        corpus = (runtime / "src/agentic_praxis_grimoire/resources/skill-metadata.json").read_bytes()
        import hashlib
        info = {"version": (runtime / "src/agentic_praxis_grimoire/VERSION").read_text().strip(),
                "module_path": "github.com/Knowledge-Forge-AI/agentic-praxis-grimoire", "target": "darwin/arm64",
                "corpus_fingerprint": hashlib.sha256(corpus).hexdigest(), "corpus_fingerprint_verified": True}
        info.update(fault.get("build_info", {}))
        print(json.dumps(info))
    elif arguments == ["skills", "list"]:
        print(fault.get("skills", "implementing-with-test-discipline\n"))
elif name == "apgr-dispatcher-bundle" and arguments[:1] == ["show"]:
    print(json.dumps({"bundle_dir": fault.get("bundle_dir", str(runtime / "common/dispatcher"))}))
elif name == "agent-phase-dispatch" and "--dry-run" in arguments:
    if fault.get("provider"):
        subprocess.run(["codex"], check=False)
    marker = json.loads((runtime / "apgr-installed-runtime.json").read_text())
    generation = {"reason": "installed_immutable_runtime", "commit": None,
                  "runtime_digest": marker["runtime_digest"], "controller_root": str(runtime)}
    generation.update(fault.get("generation", {}))
    for index in range(fault.get("states", 1)):
        run = Path(os.environ["APGR_OUTBOX_ROOT"], f"run-{index}")
        run.mkdir(parents=True)
        (run / "state.json").write_text(json.dumps({"controller_generation": generation}))
    if fault.get("generations"):
        Path(os.environ["APGR_HOME"], "generations").mkdir(parents=True)
'''
COMMANDS = ("agent-phase-dispatch", "agent-phase-resolve", "apgr", "apgr-dispatcher-bundle")


def _package(root: Path, **fault: object) -> Path:
    runtime = root / RUNTIME
    (runtime / "src/agentic_praxis_grimoire/resources").mkdir(parents=True)
    (runtime / "src/agentic_praxis_grimoire/VERSION").write_text("0.13.0\n")
    (runtime / "src/agentic_praxis_grimoire/resources/skill-metadata.json").write_text('{"skills": []}\n')
    (runtime / "common/dispatcher").mkdir(parents=True)
    (runtime / "apgr-installed-runtime.json").write_text(json.dumps({"runtime_digest": DIGEST}))
    (root / "fault.json").write_text(json.dumps(fault))
    (root / "bin").mkdir()
    for name in COMMANDS:
        command = root / "bin" / name
        command.write_text(f"#!{sys.executable}\n{COMMAND}")
        command.chmod(0o700)
    return root


def _smoke(package: Path, *extra: str, environment: dict[str, str] | None = None):
    env = {**os.environ, **(environment or {})}
    return subprocess.run([sys.executable, "-B", os.fspath(SMOKE), "--package", os.fspath(package),
                           "--target", "darwin/arm64", *extra], cwd=package, env=env,
                          stdin=subprocess.DEVNULL, capture_output=True, text=True, check=False)


def test_installed_contract_passes_and_children_get_only_the_isolated_environment(tmp_path: Path) -> None:
    package = _package(tmp_path / "package")
    ambient = {"APGR_HOME": "/operator/apgr", "APGR_OUTBOX_ROOT": "/operator/outbox",
               "APGR_GENERATION_LEASE": "/operator/lease.json", "PYTHONPATH": "/ambient", "LANG": "C.UTF-8"}
    completed = _smoke(package, environment=ambient)
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result == {"package": str(package.resolve()), "target": "darwin/arm64", "controller_generation": {
        "reason": "installed_immutable_runtime", "commit": None, "runtime_digest": DIGEST,
        "controller_root": str(package.resolve() / RUNTIME)}}
    for name in COMMANDS:
        child = json.loads((package / f"environment-{name}").read_text())
        assert not {"APGR_GENERATION_LEASE", "PYTHONPATH"} & set(child)
        assert child["LANG"] == "C.UTF-8"
        assert {child[key] for key in ("APGR_HOME", "APGR_OUTBOX_ROOT")}.isdisjoint(ambient.values())
        assert Path(child["HOME"]).parent == Path(child["TMPDIR"])
        assert child["PATH"].split(os.pathsep)[1] == os.fspath(package.resolve() / "bin")
    explicit = _smoke(package, "--bin-dir", os.fspath(package / "bin"))
    assert json.loads(explicit.stdout) == result


@pytest.mark.parametrize("fault, diagnostic", [
    ({"version": "9.9.9"}, "apgr --version reported 'apgr 9.9.9', expected 0.13.0"),
    ({"build_info": {"target": "linux/amd64"}}, "build-info target is 'linux/amd64', expected 'darwin/arm64'"),
    ({"build_info": {"corpus_fingerprint_verified": False}}, "build-info corpus_fingerprint_verified is False, expected True"),
    ({"skills": "other-skill\n"}, "portable Go skills list omitted a canonical skill"),
    ({"fail": "agent-phase-resolve"}, "resolve failed (3): stand-in failure"),
    ({"bundle_dir": "/elsewhere/common/dispatcher"}, "dispatcher bundle was not resolved from the installed runtime"),
    ({"states": 2}, "dry-run dispatch produced 2 run states, expected 1"),
    ({"states": 0}, "dry-run dispatch produced 0 run states, expected 1"),
    ({"generation": {"reason": "source_development_worktree"}}, "dry-run dispatch did not record installed runtime provenance"),
    ({"generation": {"commit": "b" * 40}}, "dry-run dispatch did not record installed runtime provenance"),
    ({"generation": {"runtime_digest": "c" * 64}}, "dry-run dispatch did not record installed runtime provenance"),
    ({"generations": True}, "installed dispatch materialized a controller generation"),
    ({"provider": True}, "a provider executable was launched"),
])
def test_each_installed_contract_break_fails_the_smoke(tmp_path: Path, fault: dict, diagnostic: str) -> None:
    completed = _smoke(_package(tmp_path / "package", **fault))
    assert completed.returncode == 1
    assert completed.stdout == ""
    assert completed.stderr == f"apg_nix_smoke: {diagnostic}\n"


def test_smoke_leaves_no_temporary_state_and_never_reads_ambient_apgr_paths(tmp_path: Path) -> None:
    package = _package(tmp_path / "package")
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    completed = _smoke(package, environment={"TMPDIR": os.fspath(scratch), "APGR_HOME": os.fspath(tmp_path / "x")})
    assert completed.returncode == 0, completed.stderr
    assert list(scratch.iterdir()) == []
    assert not (tmp_path / "x").exists()
