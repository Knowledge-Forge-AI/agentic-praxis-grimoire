#!/usr/bin/env python3
"""Native hosted guard, build qualification and packaged consumer smoke."""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "libexec"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.ci.native_diagnostics import bounded, command_diagnostics, command_message, failure_record, sanitize
from tools.ci.native_seal import (
    CANONICAL_TARGETS,
    IDENTITY_SCHEMA,
    REQUIRED_LANES,
    build_consumer_receipt,
    build_lane_seal,
    canonical_json,
    check_containment,
    verify_bundle_seal,
    write_github_output,
)

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_REPO = "Knowledge-Forge-AI/agentic-praxis-grimoire"
EXPECTED_REPO_ID = "1306002537"
RELEASE_GO_VERSION = "go1.26.9"
COMMAND_TIMEOUT_SECONDS = 45 * 60


class LaneError(ValueError):
    """A native precondition, child process or smoke check failed."""


class LaneCommandError(LaneError):
    """A child failure with sanitized, bounded stdout and stderr evidence."""

    def __init__(self, diagnostics: dict[str, Any]) -> None:
        self.diagnostics = diagnostics
        super().__init__(command_message(diagnostics))


def _run(args: list[str], *, cwd: Path = ROOT, allow_failure: bool = False) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ, GOTOOLCHAIN="local", PYTHONDONTWRITEBYTECODE="1")
    with subprocess.Popen(args, cwd=cwd, env=environment, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True, start_new_session=True) as child:
        try:
            stdout, stderr = child.communicate(timeout=COMMAND_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired as error:
            # Go test binaries share this new process group, so kill them too.
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass  # The whole group has already exited.
            partial_stdout: str | bytes | None
            partial_stderr: str | bytes | None
            try:
                partial_stdout, partial_stderr = child.communicate(timeout=5)
            except subprocess.TimeoutExpired as drain_error:
                # A descendant that escaped the group may still hold a pipe.
                partial_stdout, partial_stderr = drain_error.stdout, drain_error.stderr
            raise LaneCommandError(command_diagnostics(args, None, partial_stdout, partial_stderr, environment)) from error
        result = subprocess.CompletedProcess(args, child.returncode, stdout, stderr)
    if result.returncode and not allow_failure:
        raise LaneCommandError(command_diagnostics(args, result.returncode, result.stdout, result.stderr, environment))
    return result


def _git_run(args: list[str], cwd: Path = ROOT) -> str:
    return _run(["git", *args], cwd=cwd).stdout.strip()


def _required(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise LaneError(f"missing {name}")
    return value


def _identity() -> tuple[str, str]:
    commit, tree = _git_run(["rev-parse", "HEAD", "HEAD^{tree}"]).splitlines()
    if commit != _required("SOURCE_COMMIT") or tree != _required("SOURCE_TREE"):
        raise LaneError("source commit/tree differs from guard")
    if _git_run(["status", "--porcelain", "--untracked-files=all"]):
        raise LaneError("source checkout is dirty")
    return commit, tree


def run_guard(output_path: Path) -> dict[str, Any]:
    check_containment(output_path)
    for name, expected in (("ACTUAL_REPO", EXPECTED_REPO), ("ACTUAL_REPO_ID", EXPECTED_REPO_ID),
                           ("BASE_REF", "main"), ("HEAD_REF", "staging"), ("HEAD_REPO", EXPECTED_REPO)):
        if _required(name) != expected:
            raise LaneError(f"unexpected {name}")
    if _git_run(["status", "--porcelain", "--untracked-files=all"]):
        raise LaneError("git working tree is dirty")
    commit, tree = _git_run(["rev-parse", "HEAD", "HEAD^{tree}"]).splitlines()
    head, base = _required("PR_HEAD_SHA"), _required("PR_BASE_SHA")
    if not all(re.fullmatch(r"[0-9a-f]{40}", item) for item in (commit, tree, head, base)):
        raise LaneError("invalid source identity")
    if commit != _required("COMMIT_SHA"):
        raise LaneError("COMMIT_SHA mismatch")
    if _git_run(["show", "-s", "--format=%P", "HEAD"]).split() != [base, head]:
        raise LaneError("merge parents must equal exact PR base and staging head")
    data = {"schema_version": IDENTITY_SCHEMA, "source_commit": commit, "source_tree": tree,
            "repository": EXPECTED_REPO, "repository_id": EXPECTED_REPO_ID,
            "pr_head_sha": head, "pr_base_sha": base, "status": "passed"}
    dest = output_path if output_path.suffix == ".json" else output_path / "identity.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(canonical_json(data))
    write_github_output("source_commit", commit)
    write_github_output("source_tree", tree)
    return data


def _verify_native_host(spec: dict[str, str]) -> dict[str, str]:
    aliases = {"x86_64": "amd64", "x64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64"}
    actual_os, actual_arch = platform.system().lower(), aliases.get(platform.machine().lower())
    runner_os = _required("RUNNER_OS").lower().replace("macos", "darwin")
    runner_arch = aliases.get(_required("RUNNER_ARCH").lower())
    if actual_arch is None or (actual_os, actual_arch) != (spec["system"], spec["arch"]) or (runner_os, runner_arch) != (actual_os, actual_arch):
        raise LaneError("host system/architecture mismatch")
    if any(name in os.environ for name in ("GOOS", "GOARCH")):
        raise LaneError("GOOS/GOARCH override forbidden")
    return {"os": actual_os, "arch": actual_arch, "image": _required("ImageOS"),
            "image_version": _required("ImageVersion")}


def _binary_smoke(binary: Path, target: str, cwd: Path) -> None:
    version = (ROOT / "src/agentic_praxis_grimoire/VERSION").read_text().strip()
    if _run([str(binary), "--version"], cwd=cwd).stdout.strip() != f"apgr {version}":
        raise LaneError("binary version smoke mismatch")
    info = json.loads(_run([str(binary), "build-info"], cwd=cwd).stdout)
    if info.get("target") != target or info.get("version") != version or info.get("corpus_fingerprint_verified") is not True:
        raise LaneError("binary build-info smoke mismatch")
    _run([str(binary), "report", "verify", str(ROOT / "report/testdata/persisted/diff.report.txt")], cwd=cwd)


def run_qualify(lane: str, output_path: Path) -> dict[str, Any]:
    spec = CANONICAL_TARGETS[lane]
    _verify_native_host(spec)
    check_containment(output_path)
    commit, tree = _identity()
    output_path.mkdir(parents=True, exist_ok=True)
    target_dir = output_path / spec["slug"]
    target_dir.mkdir()
    with tempfile.TemporaryDirectory(prefix="native-work-", dir=output_path.parent) as temporary:
        work = Path(temporary)
        go = shutil.which("go")
        if not go or _run([go, "version"]).stdout.strip() != f"go version {RELEASE_GO_VERSION} {spec['target']}":
            raise LaneError("wrong native Go compiler")
        logs = []
        for flags in (["test", "-count=1", "./..."], ["vet", "./..."], ["test", "-race", "-count=1", "./..."]):
            result = _run([go, *flags])
            logs.append(" ".join(flags) + "\n" + result.stdout + result.stderr)
        import apg_go_build
        import apg_go_buildinfo
        for seed in ("a", "b"):
            build_dir = work / seed
            build_dir.mkdir()
            apg_go_build.build(ROOT, spec["target"], build_dir / "apgr", require_native=True)
        for name in ("apgr", "apgr.binary-manifest.json"):
            if (work / "a" / name).read_bytes() != (work / "b" / name).read_bytes():
                raise LaneError("dual build byte/manifest divergence")
            shutil.copy2(work / "a" / name, target_dir / name)
        recorded = _run([go, "version", "-m", str(target_dir / "apgr")]).stdout
        apg_go_buildinfo.validate(target_dir / "apgr", spec["target"], recorded)
        (target_dir / "go-version-m.txt").write_text(recorded)
        (target_dir / "go-tests.log").write_text("\n".join(logs))
        _binary_smoke(target_dir / "apgr", spec["target"], work)
        import apg_nix_qualification as nix
        system = {"darwin/arm64": "aarch64-darwin", "linux/amd64": "x86_64-linux", "linux/arm64": "aarch64-linux"}[spec["target"]]
        flake = f"git+file://{ROOT}?rev={commit}"
        nix_work = work / "nix"
        nix_work.mkdir()
        evidence = nix.qualify_local(flake, nix_work, system)
        for label in ("store_smoke", "profile_smoke"):
            if evidence.get(label, {}).get("controller_generation", {}).get("reason") != "installed_immutable_runtime":
                raise LaneError("Nix installed dispatcher smoke missing")
        if evidence.get("profile_removed") is not True:
            raise LaneError("Nix disposable profile cleanup failed")
        compiler_path = Path(_run(["nix", "build", *nix.LOCKED, "--no-link", "--print-out-paths",
                                  f"{flake}#checks.{system}.compiler-identity"]).stdout.strip())
        compiler_text = compiler_path.read_text()
        if not compiler_text.startswith(RELEASE_GO_VERSION + "\n"):
            raise LaneError("Nix real compiler identity evidence missing")
        (target_dir / "nix-compiler-identity.txt").write_text(compiler_text)
        evidence.update({"schema_version": "apgr.native-nix-evidence/v1", "status": "passed",
                         "evidence": "native-execution", "native_execution": True, "lane": lane, "target": spec["target"],
                         "compiler_version": RELEASE_GO_VERSION, "foreign_evaluation": nix.eval_foreign(flake, system)})
        (target_dir / "nix-evidence.json").write_bytes(canonical_json(evidence))
    seal = build_lane_seal(lane, spec["target"], spec["slug"], commit, tree, target_dir)
    write_github_output("seal_sha256", seal["seal_sha256"])
    _identity()
    return seal


def run_consumer(lane: str, bundle_dir: Path, output_path: Path) -> dict[str, Any]:
    if os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"):
        raise LaneError("packaged consumer execution must not inherit a GitHub token")
    spec = CANONICAL_TARGETS[lane]
    _verify_native_host(spec)
    check_containment(output_path)
    _identity()
    binding = json.loads(_required("NATIVE_BUNDLE_JSON"))
    # The preceding token-bearing verify-bundle step checks the archive identity.
    # Recheck its producer-bound internal seal before and after packaged execution.
    seal = verify_bundle_seal(bundle_dir, binding["seal_sha256"])
    if (seal["source_commit"], seal["source_tree"]) != (_required("SOURCE_COMMIT"), _required("SOURCE_TREE")):
        raise LaneError("consumer bundle source identity mismatch")
    version = (ROOT / "src/agentic_praxis_grimoire/VERSION").read_text().strip()
    wheels = sorted((bundle_dir / "python").glob("*.whl"))
    native = [p for p in wheels if p.name.endswith(f"-{spec['python_tag']}.whl")]
    foreign = [p for p in wheels if p not in native]
    if len(native) != 1 or len(foreign) != 2:
        raise LaneError("consumer wheel inventory mismatch")
    output_path.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="native-consumer-", dir=output_path.parent) as temporary:
        work = Path(temporary)
        venv = work / "python"
        _run([sys.executable, "-m", "venv", str(venv)], cwd=work)
        pip = [str(venv / "bin/python"), "-m", "pip", "install", "--no-index", "--no-deps"]
        _run([*pip, str(native[0])], cwd=work)
        _binary_smoke(venv / "bin/apgr", spec["target"], work)
        negative = _run([*pip, str(foreign[0])], cwd=work, allow_failure=True)
        if negative.returncode == 0 or "not a supported wheel on this platform" not in negative.stderr:
            raise LaneError("foreign wheel negative control did not refuse platform")
        if _run(["node", "--version"], cwd=work).stdout.strip() != "v22.22.2":
            raise LaneError("consumer Node identity mismatch")
        npm = work / "npm"
        npm.mkdir()
        (npm / "package.json").write_text('{"name":"apgr-ci-install","private":true}\n')
        _run(["npm", "install", "--prefix", str(npm), "--ignore-scripts", "--offline", "--no-audit",
              "--no-fund", "--package-lock=false", str(bundle_dir / "npm" / f"knowledge-forge-ai-apgr-{version}.tgz"),
              str(bundle_dir / "npm" / f"knowledge-forge-ai-apgr-{spec['npm_slug']}-{version}.tgz")], cwd=work)
        _binary_smoke(npm / "node_modules/.bin/apgr", spec["target"], work)
    verify_bundle_seal(bundle_dir, binding["seal_sha256"])
    _identity()
    return build_consumer_receipt(lane, spec["target"], seal["bundle_seal_sha256"], seal["source_commit"],
                                  seal["source_tree"], dict.fromkeys(("wheel_install_smoke", "foreign_wheel_rejected",
                                  "npm_install_smoke", "bundle_seal_verified"), "passed"), output_path)


def _diagnostics_directory(path: Path, output: Path) -> Path:
    check_containment(path, "diagnostics")
    resolved, lane_output = path.resolve(), output.resolve()
    if resolved.is_relative_to(lane_output) or lane_output.is_relative_to(resolved):
        raise LaneError("diagnostics and qualification output directories must be disjoint")
    return path


def _report_failure(error: Exception, args: argparse.Namespace, diagnostics: Path | None) -> None:
    message = str(error) if isinstance(error, LaneCommandError) else bounded(sanitize(str(error)))[0]
    print(f"native lane failed: {message}", file=sys.stderr)
    if diagnostics is not None:
        try:
            # Revalidate at the write boundary as well as before qualification.
            _diagnostics_directory(diagnostics, args.output)
            diagnostics.mkdir(parents=True, exist_ok=True)
            destination = diagnostics / f"{args.lane}-failure.json"
            check_containment(destination, "diagnostics file")
            if destination.is_symlink():
                raise LaneError("diagnostics file must not be a symlink")
            details = error.diagnostics if isinstance(error, LaneCommandError) else None
            destination.write_bytes(canonical_json(failure_record(error, args.lane, details)))
        except Exception as write_error:
            print(f"native lane diagnostics write failed: {bounded(sanitize(str(write_error)))[0]}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("guard", "qualify", "consumer"):
        command = commands.add_parser(name)
        command.add_argument("--output", required=True, type=Path)
        if name != "guard":
            command.add_argument("--lane", required=True, choices=REQUIRED_LANES)
        if name == "consumer":
            command.add_argument("--bundle", required=True, type=Path)
        if name == "qualify":
            command.add_argument("--diagnostics", type=Path)
    args = parser.parse_args(argv)
    diagnostics = None
    try:
        if args.command == "guard":
            run_guard(args.output)
        elif args.command == "qualify":
            if args.diagnostics is not None:
                diagnostics = _diagnostics_directory(args.diagnostics, args.output)
            run_qualify(args.lane, args.output)
        else:
            run_consumer(args.lane, args.bundle, args.output)
    except Exception as error:
        # This CLI boundary records unexpected adapter errors and remains nonzero.
        # KeyboardInterrupt/SystemExit and runner cancellation still propagate.
        _report_failure(error, args, diagnostics)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
