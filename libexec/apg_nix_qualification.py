"""Host qualification of the first-party APGR Nix flake.

Every ``nix profile`` call receives an explicit disposable profile derived
from a scratch directory; the operator's default profile is never a target.
The helper never runs garbage collection, activation or publication.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Callable, Sequence


PUBLIC_FLAKE = "github:Knowledge-Forge-AI/agentic-praxis-grimoire"
TAG = re.compile(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
SYSTEM_TARGETS = {"aarch64-darwin": "darwin/arm64", "x86_64-linux": "linux/amd64",
                  "aarch64-linux": "linux/arm64"}
LOCKED = ("--no-update-lock-file", "--no-write-lock-file")
SCRATCH_IDENTITY = {"GIT_AUTHOR_NAME": "APGR Nix qualification", "GIT_COMMITTER_NAME": "APGR Nix qualification",
                    "GIT_AUTHOR_EMAIL": "nix-qualification@example.invalid",
                    "GIT_COMMITTER_EMAIL": "nix-qualification@example.invalid",
                    "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z", "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z"}
Runner = Callable[[Sequence[str]], str]


class QualificationError(RuntimeError):
    """A qualification precondition or step failed."""


def default_profiles(environment: dict[str, str] | None = None) -> tuple[Path, ...]:
    values = os.environ if environment is None else environment
    home = Path(values.get("HOME", str(Path.home())))
    state = Path(values.get("XDG_STATE_HOME", str(home / ".local/state")))
    roots = [home / ".nix-profile", state / "nix", Path("/nix/var/nix/profiles")]
    if values.get("NIX_PROFILE"):
        roots.append(Path(values["NIX_PROFILE"]))
    return tuple(roots)


def disposable_profile(scratch: Path, environment: dict[str, str] | None = None) -> Path:
    """Derive the only profile this helper may mutate, refusing default roots."""

    if not scratch.is_absolute() or not scratch.is_dir() or scratch.is_symlink():
        raise QualificationError("--scratch must be an existing absolute direct directory")
    resolved = scratch.resolve(strict=True)
    for root in default_profiles(environment):
        for candidate in {root, root.resolve()} if root.exists() else {root}:
            if resolved == candidate or candidate in resolved.parents or resolved in candidate.parents:
                raise QualificationError(f"scratch overlaps a default Nix profile root: {candidate}")
    return resolved / "nix-profile" / "profile"


def tag_reference(tag: str, attribute: str = "agentic-praxis-grimoire") -> str:
    if not TAG.fullmatch(tag):
        raise QualificationError("readback requires an exact release tag such as v0.13.0")
    return f"{PUBLIC_FLAKE}/{tag}#{attribute}"


def _run(argv: Sequence[str]) -> str:
    completed = subprocess.run(list(argv), capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        tail = " | ".join((completed.stderr or completed.stdout).strip().splitlines()[-6:])
        raise QualificationError(f"{argv[0]} {' '.join(argv[1:3])} failed: {tail}")
    return completed.stdout


def prepare_source(checkout: Path, bare: Path, runner: Runner = _run) -> str:
    """Commit the checkout's eligible working files into a scratch bare repository.

    The product index and HEAD are untouched: a scratch GIT_DIR and index read
    the checkout work tree. ``private/`` never enters, and ignored or
    info-excluded operator files such as ``claude/settings.json`` are refused.
    """

    names = [name for name in runner(["git", "-C", str(checkout), "ls-files", "-co",
                                      "--exclude-standard", "-z"]).split("\0") if name]
    eligible = sorted(name for name in set(names)
                      if not name.startswith(("private/", ".scratch/")) and (checkout / name).exists())
    if any(Path(name).name in {"settings.json", "settings.local.json"} for name in eligible):
        raise QualificationError("operator settings would enter the qualification source")
    if not (bare / "HEAD").is_file():
        runner(["git", "init", "-q", "--bare", "-b", "main", str(bare)])
    index = bare / "qualification.index"
    index.unlink(missing_ok=True)
    prefix = ["env", f"GIT_DIR={bare}", f"GIT_INDEX_FILE={index}", f"GIT_WORK_TREE={checkout}",
              *(f"{key}={value}" for key, value in SCRATCH_IDENTITY.items()), "git"]
    for start in range(0, len(eligible), 200):
        runner([*prefix, "add", "-f", "--", *eligible[start:start + 200]])
    tree = runner([*prefix, "write-tree"]).strip()
    commit = runner([*prefix, "commit-tree", tree, "-m", "APGR Nix qualification source"]).strip()
    runner(["git", f"--git-dir={bare}", "update-ref", "refs/heads/main", commit])
    return f"git+file://{bare}?ref=main&rev={commit}"


def local_steps(flake: str, scratch: Path, system: str, profile: Path) -> list[list[str]]:
    """Return the exact local qualification argv sequence (no execution)."""

    package = f"{flake}#packages.{system}.default"
    return [
        ["nix", "flake", "check", *LOCKED, "-L", flake],
        ["nix", "build", *LOCKED, "--out-link", str(scratch / "result"), package],
        ["nix", "run", *LOCKED, f"{flake}#apps.{system}.apgr", "--", "--version"],
        ["nix", "profile", "add", "--profile", str(profile), *LOCKED, package],
        ["nix", "profile", "list", "--profile", str(profile), "--json"],
    ]


def qualify_local(flake: str, scratch: Path, system: str, runner: Runner = _run) -> dict:
    if system not in SYSTEM_TARGETS:
        raise QualificationError(f"unsupported system: {system}")
    profile = disposable_profile(scratch)
    if os.path.lexists(profile):
        raise QualificationError("disposable profile already exists; choose a fresh scratch directory")
    profile.parent.mkdir(mode=0o700)
    smoke = Path(__file__).resolve().parent / "apg_nix_smoke.py"
    result: dict = {"flake": flake, "system": system, "profile": str(profile), "steps": []}
    try:
        for argv in local_steps(flake, scratch, system, profile):
            output = runner(argv)
            result["steps"].append({"argv": argv, "stdout_tail": output.strip()[-400:]})
        package = (scratch / "result").resolve(strict=True)
        installed = json.loads(output or "{}")  # complete `nix profile list --json`
        result["profile_elements"] = sorted(installed.get("elements", {}))
        for label, bin_dir in (("store", package / "bin"), ("profile", profile / "bin")):
            output = runner([sys.executable, "-B", str(smoke), "--package", str(package),
                             "--bin-dir", str(bin_dir), "--target", SYSTEM_TARGETS[system]])
            result[f"{label}_smoke"] = json.loads(output)
    finally:
        try:
            if os.path.lexists(profile):
                runner(["nix", "profile", "remove", "--profile", str(profile), "--all"])
        finally:
            shutil.rmtree(profile.parent, ignore_errors=True)
        result["profile_removed"] = not profile.parent.exists()
    return result


def eval_foreign(flake: str, native: str, runner: Runner = _run) -> dict:
    """Evaluate and instantiate the non-native systems; nothing is built or run."""

    results = {}
    for system in sorted(set(SYSTEM_TARGETS) - {native}):
        attribute = f"{flake}#packages.{system}.default"
        name = runner(["nix", "eval", *LOCKED, "--raw", f"{attribute}.name"]).strip()
        derivation = runner(["nix", "eval", *LOCKED, "--raw", f"{attribute}.drvPath"]).strip()
        results[system] = {"name": name, "drv_path": derivation, "evidence": "evaluation_and_instantiation"}
    return results


def readback(tag: str, scratch: Path, system: str, expected_rev: str, runner: Runner = _run) -> dict:
    """Read back one published tag: resolve it once, then qualify only that revision.

    ``--refresh`` bypasses the tarball TTL so a cached tag resolution cannot
    satisfy the comparison. Every later step uses the resolved commit, never
    the mutable tag name.
    """

    if not re.fullmatch(r"[0-9a-f]{40}", expected_rev or ""):
        raise QualificationError("--expect-rev must be a 40-character lowercase commit")
    reference = tag_reference(tag).split("#", 1)[0]
    try:
        locked = json.loads(runner(["nix", "flake", "metadata", "--json", "--refresh", reference]))["locked"]
        rev, nar_hash = locked["rev"], locked["narHash"]
    except (KeyError, TypeError, ValueError) as error:
        raise QualificationError(f"flake metadata for {tag} is malformed") from error
    if rev != expected_rev:
        raise QualificationError(f"tag {tag} resolves to {rev}, expected {expected_rev}")
    if not isinstance(nar_hash, str) or not nar_hash.startswith("sha256-"):
        raise QualificationError(f"flake metadata for {tag} has no sha256 narHash")
    pinned = f"{PUBLIC_FLAKE}/{rev}"
    result = qualify_local(pinned, scratch, system, runner)
    version = tag[1:]
    reported = result["steps"][2]["stdout_tail"]
    if reported != f"apgr {version}":
        raise QualificationError(f"tagged apgr reported {reported!r}, expected apgr {version}")
    for label in ("store_smoke", "profile_smoke"):
        if result[label].get("controller_generation", {}).get("reason") != "installed_immutable_runtime":
            raise QualificationError(f"{label} did not record installed_immutable_runtime provenance")
    if result.get("profile_removed") is not True:
        raise QualificationError("the disposable readback profile was not removed")
    result["readback"] = {"tag": tag, "expected_rev": expected_rev, "locked_rev": rev, "nar_hash": nar_hash,
                          "pinned_flake": pinned, "version": version, "system": system,
                          "evidence": "native-execution"}
    return result


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="apg-qualify-nix")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare-source", help="commit eligible checkout files to a scratch bare repo")
    prepare.add_argument("--checkout", required=True, type=Path)
    prepare.add_argument("--bare", required=True, type=Path)
    local = commands.add_parser("local", help="check, build, run and disposable-profile readback")
    local.add_argument("--flake", required=True)
    local.add_argument("--scratch", required=True, type=Path)
    local.add_argument("--system", required=True, choices=sorted(SYSTEM_TARGETS))
    foreign = commands.add_parser("eval-foreign", help="evaluate non-native systems")
    foreign.add_argument("--flake", required=True)
    foreign.add_argument("--native", required=True, choices=sorted(SYSTEM_TARGETS))
    tagged = commands.add_parser("readback", help="post-publication readback of an exact release tag")
    tagged.add_argument("--tag", required=True)
    tagged.add_argument("--scratch", required=True, type=Path)
    tagged.add_argument("--system", required=True, choices=sorted(SYSTEM_TARGETS))
    tagged.add_argument("--expect-rev", required=True, help="merged release commit the tag must resolve to")
    parsed = parser.parse_args(arguments)
    try:
        if parsed.command == "prepare-source":
            result: object = {"flake": prepare_source(parsed.checkout.resolve(strict=True), parsed.bare.absolute())}
        elif parsed.command == "local":
            result = qualify_local(parsed.flake, parsed.scratch, parsed.system)
        elif parsed.command == "eval-foreign":
            result = eval_foreign(parsed.flake, parsed.native)
        else:
            result = readback(parsed.tag, parsed.scratch, parsed.system, parsed.expect_rev)
    except (OSError, ValueError, QualificationError) as error:
        print(f"apg-qualify-nix: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
