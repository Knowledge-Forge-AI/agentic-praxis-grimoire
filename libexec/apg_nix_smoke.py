"""Provider-free smoke of one installed APGR Nix output, outside any checkout.

The smoke runs the installed commands from an empty working directory with an
isolated HOME and APGR_HOME.  Fake provider executables record any launch; a
real provider is never started.  It is used by the flake checks and by the
host qualification helper against a disposable profile.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


RUNTIME_SUBPATH = "share/agentic-praxis-grimoire/runtime"
MODULE = "github.com/Knowledge-Forge-AI/agentic-praxis-grimoire"
PROVIDERS = ("agy", "claude", "codex", "gemini")
ENVIRONMENT_ALLOWLIST = ("LANG", "LC_ALL", "LC_CTYPE", "TERM", "USER", "LOGNAME", "NIX_STORE")


class SmokeError(RuntimeError):
    """One installed-output expectation failed."""


def _run(command: list[str], *, env: dict[str, str], cwd: Path, label: str) -> str:
    completed = subprocess.run(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                               capture_output=True, text=True, timeout=300, check=False)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip().splitlines()[-5:]
        raise SmokeError(f"{label} failed ({completed.returncode}): " + " | ".join(detail))
    return completed.stdout


def _environment(base: Path, bin_dir: Path) -> dict[str, str]:
    sentinels = base / "provider-sentinels"
    sentinels.mkdir()
    for name in PROVIDERS:
        command = sentinels / name
        command.write_text('#!/bin/sh\nprintf invoked >> "$APGR_SMOKE_PROVIDER_MARKER"\nexit 97\n')
        command.chmod(0o700)
    # Allowlisted, never inherited: ambient APGR/agent variables (home, outbox,
    # lease, Go override) would otherwise redirect writes or binaries.
    env = {key: os.environ[key] for key in ENVIRONMENT_ALLOWLIST if key in os.environ}
    env.update({"HOME": str(base / "home"), "APGR_HOME": str(base / "apgr-home"),
                "APGR_OUTBOX_ROOT": str(base / "outbox"), "TMPDIR": str(base),
                "APGR_SMOKE_PROVIDER_MARKER": str(base / "provider-invoked"),
                "PATH": os.pathsep.join((str(sentinels), str(bin_dir), os.environ.get("PATH", "")))})
    (base / "home").mkdir()
    return env


def _identity(runtime: Path, bin_dir: Path, env: dict[str, str], cwd: Path, target: str) -> None:
    version = (runtime / "src/agentic_praxis_grimoire/VERSION").read_text(encoding="ascii").strip()
    corpus = hashlib.sha256(
        (runtime / "src/agentic_praxis_grimoire/resources/skill-metadata.json").read_bytes()
    ).hexdigest()
    reported = _run([str(bin_dir / "apgr"), "--version"], env=env, cwd=cwd, label="apgr --version")
    if reported != f"apgr {version}\n":
        raise SmokeError(f"apgr --version reported {reported.strip()!r}, expected {version}")
    info = json.loads(_run([str(bin_dir / "apgr"), "build-info"], env=env, cwd=cwd, label="build-info"))
    expected = {"version": version, "module_path": MODULE, "target": target,
                "corpus_fingerprint": corpus, "corpus_fingerprint_verified": True}
    for key, value in expected.items():
        if info.get(key) != value:
            raise SmokeError(f"build-info {key} is {info.get(key)!r}, expected {value!r}")
    listed = _run([str(bin_dir / "apgr"), "skills", "list"], env=env, cwd=cwd, label="skills list")
    if "implementing-with-test-discipline" not in listed:
        raise SmokeError("portable Go skills list omitted a canonical skill")


def _dispatcher(runtime: Path, bin_dir: Path, env: dict[str, str], base: Path) -> dict:
    empty = base / "empty"
    empty.mkdir()
    home = env["APGR_HOME"]
    _run([str(bin_dir / "agent-phase-dispatch"), "--help"], env=env, cwd=empty, label="dispatch --help")
    shown = json.loads(_run([str(bin_dir / "apgr-dispatcher-bundle"), "show", "--json"],
                            env=env, cwd=empty, label="bundle show"))
    if not str(shown.get("bundle_dir", "")).startswith(str(runtime)):
        raise SmokeError("dispatcher bundle was not resolved from the installed runtime")
    _run([str(bin_dir / "apgr-dispatcher-bundle"), "project", "--apgr-home", home],
         env=env, cwd=empty, label="bundle project")
    _run([str(bin_dir / "apgr-dispatcher-bundle"), "verify", "--apgr-home", home],
         env=env, cwd=empty, label="bundle verify")
    request = base / "SMOKE.json"
    request.write_text(json.dumps({"schema": "agent-phase-request-v1", "prompt": "Provider-free Nix smoke",
                                   "phase_type": "implementation_testing", "execution_mode": "codex_only"}))
    flags = ["--lifecycle", "work-reviewed", "--finalization", "checkpoint"]
    _run([str(bin_dir / "agent-phase-resolve"), str(request), *flags], env=env, cwd=empty, label="resolve")
    candidate = base / "candidate"
    candidate.mkdir()
    for arguments in (["init", "-q", "-b", "main"], ["config", "user.name", "Nix Smoke"],
                      ["config", "user.email", "nix-smoke@example.invalid"]):
        _run(["git", "-C", str(candidate), *arguments], env=env, cwd=empty, label="git fixture")
    (candidate / "file.txt").write_text("fixture\n")
    _run(["git", "-C", str(candidate), "add", "file.txt"], env=env, cwd=empty, label="git fixture")
    _run(["git", "-C", str(candidate), "commit", "-qm", "fixture"], env=env, cwd=empty, label="git fixture")
    _run([str(bin_dir / "agent-phase-dispatch"), str(request), "--dry-run", *flags],
         env=env, cwd=candidate, label="dry-run dispatch")
    states = sorted(base.rglob("state.json"))
    if len(states) != 1:
        raise SmokeError(f"dry-run dispatch produced {len(states)} run states, expected 1")
    generation = json.loads(states[0].read_text()).get("controller_generation", {})
    marker = json.loads((runtime / "apgr-installed-runtime.json").read_text())
    if (generation.get("reason") != "installed_immutable_runtime" or generation.get("commit") is not None
            or generation.get("runtime_digest") != marker["runtime_digest"]
            or generation.get("controller_root") != str(runtime)):
        raise SmokeError("dry-run dispatch did not record installed runtime provenance")
    if any(path.name == "generations" for path in base.rglob("*")):
        raise SmokeError("installed dispatch materialized a controller generation")
    if (base / "provider-invoked").exists():
        raise SmokeError("a provider executable was launched")
    return generation


def smoke(package: Path, bin_dir: Path, target: str) -> dict:
    runtime = package / RUNTIME_SUBPATH
    with tempfile.TemporaryDirectory(prefix="apgr-nix-smoke-") as temporary:
        base = Path(temporary).resolve()
        env = _environment(base, bin_dir)
        empty = base / "cwd"
        empty.mkdir()
        _identity(runtime, bin_dir, env, empty, target)
        generation = _dispatcher(runtime, bin_dir, env, base)
    return {"package": str(package), "target": target, "controller_generation": generation}


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="apg_nix_smoke")
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--bin-dir", type=Path, help="installed command directory; defaults to <package>/bin")
    parser.add_argument("--target", required=True, choices=("darwin/arm64", "linux/amd64", "linux/arm64"))
    parsed = parser.parse_args(arguments)
    package = parsed.package.resolve(strict=True)
    bin_dir = (parsed.bin_dir or package / "bin").absolute()
    try:
        result = smoke(package, bin_dir, parsed.target)
    except (OSError, ValueError, SmokeError, subprocess.SubprocessError) as error:
        print(f"apg_nix_smoke: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
