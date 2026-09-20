"""One provider-free H mechanical transaction on the operator host.

The helper validates the host layout, seals a runtime with three explicitly
simulated version-only providers, runs exactly one complete provider-free
transaction through ``run_final_b8_transaction.run_transaction``, then reads
the retained evidence back.  It never starts, probes or retries a real
provider and never runs a second transaction.  Every count in the result is
read from maintained receipts; a failed run records the actual counts.

This is not an H holdout observation, a live grant or manager acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import stat
import sys
import traceback
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

RESULT_SCHEMA = "apg166v-h-mechanical-host/v1"
RESULT_NAME = "host-mechanical-result.json"
FAKE_PROVIDERS = ("claude", "codex", "antigravity")
EXPECTED_CHECKS = {
    "scenario_records": 15, "equal_initial_trees": 15, "unchanged_subject_pairs": 15,
    "promotion_fixture_pairs": 25, "provider_invocations": 0, "sentinels": 0,
    "package_seal_valid": True, "readback_valid": True,
}
GO_CANCELLATION = "go-language-profile/positive/cancellation"
OMISSIONS = [
    "runtime HOME build and module caches (Go build cache, tool telemetry) are left in place, not collected",
    "no provider credential home or operator session is created, read or collected",
    "the external cache input directory is identity-bound by the runtime manifest, not copied",
]


# Frozen subject go.sum files whose modules the offline Go oracles need.  The
# reviewed cache list must name each module's exact ``cache/download/.../@v``
# directory; its zip and go.mod must match these h1 values before any start.
GO_SUM_SOURCES = ("testing/fixtures/context-eval/subjects/scenario-10/go.sum",)
MAX_MODULE_ZIP_BYTES = 256 << 20
DIAGNOSTICS = "diagnostics"
DIAGNOSTIC_SUFFIXES = (".json", ".jsonl", ".md", ".toml", ".txt", ".bin", "stdout", "stderr", "stdin")
DIAGNOSTIC_EXCLUDED = frozenset({"home", "tmp", "cache", "gomod", "node_modules", ".git", "fake-providers"})
MAX_DIAGNOSTIC_FILE_BYTES = 16 << 20
MAX_DIAGNOSTIC_BYTES = 128 << 20


class Refused(Exception):
    """Host prerequisites are not met; no transaction starts."""


def _go_escape(value: str) -> str:
    return "".join("!" + c.lower() if "A" <= c <= "Z" else c for c in value)


def _h1(entries: list[tuple[str, bytes]]) -> str:
    """Go dirhash Hash1 over (name, bytes) pairs."""
    import base64
    summary = "".join(f"{_sha256(data)}  {name}\n" for name, data in sorted(entries))
    return "h1:" + base64.b64encode(hashlib.sha256(summary.encode()).digest()).decode()


def _zip_h1(path: Path) -> str:
    import zipfile
    with zipfile.ZipFile(path) as archive:
        members = [item for item in archive.infolist() if not item.is_dir()]
        if sum(item.file_size for item in members) > MAX_MODULE_ZIP_BYTES:
            raise Refused(f"Go module zip exceeds bound: {path}")
        return _h1([(item.filename, archive.read(item)) for item in members])


def go_module_inputs(repo: Path, caches: list[str]) -> list[dict[str, Any]]:
    """Verify every frozen go.sum module against an exactly listed cache input.

    This is read-only and runs no ``go`` process: the module files are hashed
    with Go's h1 algorithm and compared with the frozen go.sum.  A missing or
    mismatched input refuses before any transaction; nothing is downloaded.
    """
    listed = {Path(item) for item in caches}
    verified = []
    for relative in GO_SUM_SOURCES:
        sums: dict[tuple[str, str], str] = {}
        for line in (repo / relative).read_text().splitlines():
            module, version, digest = line.split()
            sums[(module, version)] = digest
        for (module, version), digest in sorted(sums.items()):
            if version.endswith("/go.mod"):
                continue
            mod_digest = sums.get((module, version + "/go.mod"))
            suffix = f"/cache/download/{_go_escape(module)}/@v"
            matches = [path for path in listed if str(path).endswith(suffix)]
            if len(matches) != 1:
                raise Refused(f"reviewed cache list must name exactly one Go module input for {module}@{version}")
            directory = matches[0]
            zip_path = directory / f"{_go_escape(version)}.zip"
            mod_path = directory / f"{_go_escape(version)}.mod"
            if any(path.is_symlink() or not path.is_file() for path in (zip_path, mod_path)):
                raise Refused(f"Go module input files are unavailable: {module}@{version}")
            observed = {"zip": _zip_h1(zip_path), "mod": _h1([("go.mod", mod_path.read_bytes())])}
            if observed != {"zip": digest, "mod": mod_digest}:
                raise Refused(f"Go module input does not match frozen go.sum: {module}@{version}")
            verified.append({"module": module, "version": version, "directory": str(directory),
                             "go_sum": relative, "h1": observed,
                             "files": [_file_identity(zip_path), _file_identity(mod_path)]})
    return verified


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_identity(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": _sha256(data),
            "mode": oct(stat.S_IMODE(path.stat().st_mode))}


def _write_json(path: Path, value: Any) -> None:
    data = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def _inside(child: Path, parent: Path) -> bool:
    return child == parent or child.is_relative_to(parent)


def _loopback() -> dict[str, bool]:
    observed = {}
    for family, address in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
        try:
            with socket.socket(family, socket.SOCK_STREAM) as probe:
                probe.bind((address, 0))
                probe.listen(1)
            observed[address] = True
        except OSError:
            observed[address] = False
    return observed


def _commands(repo: Path) -> dict[str, tuple[Path, list[str]]]:
    from . import runtime_manifest as rm
    commands = {}
    for name in sorted(rm.REQUIRED_COMMANDS):
        if name == "apgr":
            selected = repo / "bin/apgr"
        else:
            found = shutil.which("python3" if name == "python" else name)
            selected = Path(found) if found else None
        if selected is None or not selected.is_file() or not os.access(selected, os.X_OK):
            raise Refused(f"required local command unavailable: {name}")
        commands[name] = (selected.resolve(), ["version"] if name == "go" else ["--version"])
    return commands


def preflight(repo: Path, runtime_root: Path, output: Path, cache_inputs: Path) -> dict[str, Any]:
    """Refuse before any transaction when the host layout is not usable."""
    for label, value in (("--repo", repo), ("--runtime-root", runtime_root), ("--output", output)):
        if not value.is_absolute():
            raise Refused(f"{label} must be absolute")
    if repo.resolve() != repo or not (repo / "testing/h_eval").is_dir():
        raise Refused("--repo must be the physical source checkout")
    if runtime_root.exists() or runtime_root.is_symlink():
        raise Refused("--runtime-root must not exist")
    parent = runtime_root.parent
    if not parent.is_dir() or parent.resolve() != parent:
        raise Refused("--runtime-root parent must be an existing physical directory")
    info = parent.lstat()
    if info.st_uid != os.getuid() or info.st_mode & 0o022:
        raise Refused("--runtime-root parent must be an exclusive operator-owned directory")
    if _inside(runtime_root, repo) or _inside(repo, runtime_root):
        raise Refused("runtime root and source tree must not contain each other")
    if not output.is_dir() or output.resolve() != output:
        raise Refused("--output must be an existing physical directory")
    if (output / RESULT_NAME).exists():
        raise Refused("host mechanical result already exists; no second transaction")
    try:
        caches = json.loads(cache_inputs.read_bytes())
    except (OSError, ValueError) as error:
        raise Refused("reviewed host cache input list is unavailable") from error
    if (not isinstance(caches, list) or not caches
            or any(not isinstance(item, str) or not Path(item).is_absolute() or not Path(item).is_dir()
                   or _inside(Path(item), repo) for item in caches)):
        raise Refused("cache inputs must be existing absolute local directories outside source")
    try:
        modules = go_module_inputs(repo, caches)
    except Refused:
        raise
    except Exception as error:  # noqa: BLE001 - unreadable/corrupt input refuses before any start
        raise Refused(f"Go module input verification failed: {type(error).__name__}: {error}") from error
    commands = _commands(repo)
    from . import promotion_oracles
    tokens = set(promotion_oracles.required_executable_tokens())
    missing = sorted(token for token in tokens if token not in commands and not shutil.which(token))
    if missing:
        raise Refused(f"promotion oracle executables unavailable: {missing}")
    loopback = _loopback()
    if not loopback["127.0.0.1"]:
        raise Refused("host IPv4 loopback bind is unavailable")
    return {"commands": {name: str(path) for name, (path, _args) in commands.items()},
            "caches": caches, "go_module_inputs": modules, "loopback": loopback,
            "oracle_tokens": sorted(tokens)}


def _fake_provider(directory: Path, name: str) -> Path:
    path = directory / f"fake-{name}"
    path.write_text(
        f"#!{sys.executable}\n"
        "import sys\n"
        "if sys.argv[1:] != ['--version']:\n"
        f"    sys.stderr.write('simulated {name} accepts only --version; provider start refused\\n')\n"
        "    raise SystemExit(97)\n"
        f"print('APG166V-H-COMPLETE1 simulated {name} version-only fixture; not a provider')\n"
    )
    path.chmod(0o700)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o700 or not os.access(path, os.X_OK):
        raise Refused(f"simulated {name} executable permissions are invalid")
    return path


def build_runtime(repo: Path, runtime_root: Path, caches: list[str]) -> dict[str, Any]:
    """Seal a runtime whose providers are three separate version-only fakes."""
    from . import runtime_manifest as rm
    runtime_root.mkdir(mode=0o700)
    for name in ("home", "tmp", "qualification", "fake-providers"):
        (runtime_root / name).mkdir(mode=0o700)
    fakes = {name: _fake_provider(runtime_root / "fake-providers", name) for name in FAKE_PROVIDERS}
    commands = _commands(repo)
    bindings = json.loads((repo / "testing/h_eval/scenario-bindings.json").read_bytes())
    sources = sorted({s for row in bindings["scenarios"] for s in row["routes"]["static"]["identity_sources"]})
    context = runtime_root / "instrumented-context.json"
    context.write_text(json.dumps({
        "execution": "instrumented", "operator_auth": "untouched; no provider probes",
        "settings": "isolated fixture context; not live settings qualification"}, indent=2) + "\n")
    groups = {
        "route_sources": [repo / s for s in sources],
        "operator_settings": [context],
        "catalog_inputs": [repo / "skills/catalog_generated.json"],
        "projection_inputs": [repo / p for p in ("codex/AGENTS.md", "claude/CLAUDE.md", "antigravity/GEMINI.md")],
        "apgr_generation": [repo / "bin/apgr", repo / "src/agentic_praxis_grimoire/VERSION"],
        "toolchain_inputs": [path for path, _args in commands.values()],
        "cache_inputs": [Path(item) for item in caches],
        "environment_inputs": [context],
    }
    value = rm.capture_and_seal(
        providers={name: (path, ["--version"]) for name, path in fakes.items()},
        commands=commands, groups=groups,
        routes={row["scenario_id"]: row["routes"] for row in bindings["scenarios"]},
        absent_settings=[runtime_root / "home/absent-settings"],
        environment={"home": str(runtime_root / "home"), "temp_root": str(runtime_root / "tmp"),
                     "values": {"CGO_ENABLED": "1"}},
    )
    manifest = runtime_root / "runtime-manifest.json"
    _write_json(manifest, value)
    for name, path in fakes.items():
        if rm.resolve_executable(value, name) != str(path):
            raise Refused(f"sealed runtime does not bind simulated {name}")
    return {"manifest_path": str(manifest), "manifest_sha256": rm.manifest_digest(value),
            "fakes": {name: _file_identity(path) for name, path in fakes.items()}}


def _source_identity(repo: Path) -> str:
    from .readiness import make_seal, source_identity
    return source_identity(make_seal(repo)["files"])


def _build_inputs(repo: Path) -> dict[str, Any]:
    from .readiness import make_seal
    files = make_seal(repo)["files"]
    go = {name: digest for name, digest in files.items() if name.endswith(".go") or name in ("go.mod", "go.sum")}
    return {
        "apgr_launcher": _file_identity(repo / "bin/apgr"),
        "version": _file_identity(repo / "src/agentic_praxis_grimoire/VERSION"),
        "go_source_sha256": _sha256(json.dumps(go, sort_keys=True).encode()),
        "go_source_files": len(go),
        "binary": ("none: bin/apgr is a Python source launcher and the Go bridge runs from the "
                   "source checkout with the sealed toolchain; no prebuilt APGR binary is rebuilt or aliased"),
    }


def _counts(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    summary = summary or {}
    fixtures = summary.get("promotion_oracle_fixtures") or {}
    guard = summary.get("provider_guard") or {}
    return {
        "scenario_records": summary.get("complete_records"),
        "equal_initial_trees": summary.get("initial_trees_equal"),
        "unchanged_subject_pairs": summary.get("subject_pairs_unchanged"),
        "promotion_fixture_pairs": fixtures.get("fixture_pairs"),
        "provider_invocations": summary.get("provider_invocations"),
        "sentinels": guard.get("sentinels_observed"),
    }


def readback(repo: Path, transaction: Path, output: Path) -> dict[str, Any]:
    """Provider-free readback of the retained transaction; never re-runs it."""
    from . import provider_free_readiness, readiness
    evidence: dict[str, Any] = {"package_seal_valid": False, "readback_valid": False, "errors": []}
    summary = provider_free_readiness.read_dry_run(transaction)
    evidence["summary"] = summary
    retained = json.loads((transaction.parent / "seal.json").read_bytes())
    package = provider_free_readiness.make_package_seal(repo, transaction)
    evidence["package_seal_valid"] = package == retained and package["provider_free_mechanical_candidate"] is True
    if package != retained:
        evidence["errors"].append("recomputed package seal differs from retained seal.json")
    seal = readiness.make_ready1_seal(repo, {"transaction_directory": str(transaction)})
    readiness.verify_seal(repo, seal)
    _write_json(output / "readiness-seal.json", seal)
    _write_json(output / "package-seal.json", package)
    receipts = (summary.get("promotion_oracle_fixtures") or {}).get("receipts", [])
    cancellation = {r.get("fixture"): r.get("status") for r in receipts if r.get("case_id") == GO_CANCELLATION}
    evidence["go_cancellation"] = cancellation
    if cancellation != {"pass": "pass", "fail": "fail"}:
        evidence["errors"].append("known-GOOD/BAD Go cancellation fixture receipts are incomplete")
    evidence["readback_valid"] = not evidence["errors"]
    evidence["readiness_seal"] = _file_identity(output / "readiness-seal.json")
    evidence["package_seal"] = _file_identity(output / "package-seal.json")
    return evidence


def _diagnostic_selected(relative: Path) -> bool:
    return relative.name.endswith(DIAGNOSTIC_SUFFIXES)


def collect_diagnostics(runtime_root: Path, attempt: Path | None, output: Path) -> dict[str, Any]:
    """Copy retained diagnostic text into ``<output>/diagnostics`` on any outcome.

    The transaction runtime stays in place for readback.  Only selected text
    receipts under the attempt directory plus the runtime manifest are copied;
    HOME/tmp/build/module caches, subjects' dependency trees, fake providers and
    symlinks are omitted with a recorded reason.  Collection problems are
    returned as issues and never change the transaction status.
    """
    target = output / DIAGNOSTICS
    target.mkdir(mode=0o700)
    files: dict[str, Any] = {}
    omissions: list[dict[str, str]] = []
    issues: list[str] = []
    total = 0
    sources: list[tuple[Path, Path]] = []
    manifest = runtime_root / "runtime-manifest.json"
    if manifest.is_file() and not manifest.is_symlink():
        sources.append((manifest, Path("runtime-manifest.json")))
    if attempt is None or not attempt.is_dir():
        issues.append("no qualification attempt directory was created")
    else:
        for directory, names, filenames in os.walk(attempt):
            base = Path(directory)
            for name in sorted(names):
                if name in DIAGNOSTIC_EXCLUDED or (base / name).is_symlink():
                    omissions.append({"path": str(base / name), "reason": "non-diagnostic directory or symlink excluded"})
            names[:] = sorted(name for name in names
                              if name not in DIAGNOSTIC_EXCLUDED and not (base / name).is_symlink())
            for name in sorted(filenames):
                path = base / name
                relative = Path("qualification") / path.relative_to(attempt)
                if path.is_symlink():
                    omissions.append({"path": str(path), "reason": "symlink excluded"})
                elif not _diagnostic_selected(relative):
                    omissions.append({"path": str(path), "reason": "not a selected diagnostic text file"})
                else:
                    sources.append((path, relative))
    for path, relative in sources:
        try:
            size = path.stat().st_size
            if size > MAX_DIAGNOSTIC_FILE_BYTES or total + size > MAX_DIAGNOSTIC_BYTES:
                omissions.append({"path": str(path), "reason": f"size bound exceeded ({size} bytes)"})
                continue
            data = path.read_bytes()
            destination = target / relative
            destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
            total += len(data)
            files[str(relative)] = {"source": str(path), "bytes": len(data), "sha256": _sha256(data),
                                    "mode": oct(stat.S_IMODE(path.stat().st_mode))}
        except OSError as error:
            issues.append(f"{relative}: {type(error).__name__}: {error}")
    collection = {"schema": "apg166v-h-mechanical-diagnostics/v1", "runtime_root": str(runtime_root),
                  "attempt_directory": str(attempt) if attempt else None, "selected_count": len(files),
                  "selected_bytes": total, "files": files, "omissions": omissions, "issues": issues}
    _write_json(target / "COLLECTION.json", collection)
    return {"collection": str(target / "COLLECTION.json"), "selected_count": len(files),
            "selected_bytes": total, "omission_count": len(omissions), "issues": issues}


def _write_diagnostic_index(output: Path, result: Mapping[str, Any]) -> None:
    """Point at diagnostic text outside the standard retained subtree."""
    pointers = {"result": str(output / RESULT_NAME)}
    for key in ("traceback",):
        if result.get(key):
            pointers[key] = result[key]
    diagnostics = result.get("diagnostics") or {}
    if diagnostics.get("collection"):
        pointers["collection"] = diagnostics["collection"]
    pointers["transaction_directory_in_place"] = result.get("transaction_directory")
    pointers["runtime_manifest_in_place"] = (result.get("runtime") or {}).get("manifest_path")
    _write_json(output / "DIAGNOSTIC-INDEX.json", {
        "schema": "apg166v-h-mechanical-diagnostic-index/v1", "pointers": pointers,
        "collection_issues": result.get("collection_issues", []),
        "note": "files omitted by the size bound remain at their recorded source path in place"})


def _collect(result: dict[str, Any], runtime_root: Path, output: Path) -> None:
    """Retain diagnostics once after the single transaction; never alters status."""
    attempts = sorted((runtime_root / "qualification").glob("final-b8-*"))
    try:
        result["diagnostics"] = collect_diagnostics(runtime_root, attempts[-1] if attempts else None, output)
        result["collection_issues"] = list(result["diagnostics"]["issues"])
    except Exception as error:  # noqa: BLE001 - a collection issue is not a test result
        result["collection_issues"] = [f"diagnostic collection failed: {type(error).__name__}: {error}"]
    try:
        _write_diagnostic_index(output, result)
    except Exception as error:  # noqa: BLE001
        result["collection_issues"].append(f"diagnostic index failed: {type(error).__name__}: {error}")


def run(repo: Path, runtime_root: Path, output: Path, *, cache_inputs: Path,
        transaction: Callable[..., Mapping[str, Any]] | None = None) -> tuple[int, dict[str, Any]]:
    """Run one complete transaction and write ``host-mechanical-result.json``."""
    result: dict[str, Any] = {
        "schema": RESULT_SCHEMA, "status": "refused", "live_provider_starts": 0,
        "source_unchanged": False, "transactions_started": 0, "retries": 0,
        "checks": {key: None for key in EXPECTED_CHECKS}, "collection_omissions": OMISSIONS,
        "transaction_directory": None, "not_h_observation": True, "manager_acceptance": "pending",
    }
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["GIT_OPTIONAL_LOCKS"] = "0"
    try:
        host = preflight(repo, runtime_root, output, cache_inputs)
    except Refused as error:
        result["refusal"] = str(error)
        if output.is_dir() and not (output / RESULT_NAME).exists():
            _write_json(output / RESULT_NAME, result)
        return 2, result
    result["host"] = host
    result["cache_inputs"] = _file_identity(cache_inputs)
    before = _source_identity(repo)
    result["source"] = {"source_identity": before, "build_inputs": _build_inputs(repo)}
    try:
        result["runtime"] = build_runtime(repo, runtime_root, host["caches"])
    except (Refused, OSError, ValueError) as error:
        result["refusal"] = f"runtime preparation failed: {error}"
        _write_json(output / RESULT_NAME, result)
        return 2, result
    if transaction is None:
        from .run_final_b8_transaction import run_transaction as transaction
    result["status"] = "failed"
    outcome: Mapping[str, Any] | None = None
    try:
        result["transactions_started"] = 1
        outcome = transaction(runtime_root / "qualification", Path(result["runtime"]["manifest_path"]), root=repo)
    except BaseException as error:  # noqa: BLE001 - retain every failure; never retry
        trace = output / "host-mechanical-traceback.txt"
        trace.write_text("".join(traceback.format_exception(error)))
        result["failure"] = f"{type(error).__name__}: {error}"
        result["traceback"] = str(trace)
        attempts = sorted((runtime_root / "qualification").glob("final-b8-*"))
        if attempts:
            result["transaction_directory"] = str(attempts[-1] / "transaction")
            summary_path = attempts[-1] / "transaction" / "dry-run.json"
            if summary_path.is_file():
                result["checks"].update(_counts(json.loads(summary_path.read_bytes())))
        if isinstance(error, (KeyboardInterrupt, SystemExit)):
            _collect(result, runtime_root, output)
            _write_json(output / RESULT_NAME, result)
            raise
    if outcome is not None:
        target = Path(outcome["transaction"])
        result["transaction_directory"] = str(target)
        result["transaction_accepted"] = bool(outcome.get("accepted"))
        result["supporting"] = {"summary": str(target.parent / "summary.json"),
                                "seal": str(target.parent / "seal.json"),
                                "runtime_input": str(target.parent / "runtime-input.json")}
        result["checks"].update(_counts(outcome.get("summary")))
        try:
            evidence = readback(repo, target, output)
        except (OSError, KeyError, TypeError, ValueError) as error:
            result["readback_failure"] = f"{type(error).__name__}: {error}"
            result["checks"]["package_seal_valid"] = False
            result["checks"]["readback_valid"] = False
        else:
            result["checks"].update(_counts(evidence.pop("summary")))
            result["checks"]["package_seal_valid"] = evidence["package_seal_valid"]
            result["checks"]["readback_valid"] = evidence["readback_valid"]
            result["readback"] = evidence
    after = _source_identity(repo)
    result["source"]["source_identity_after"] = after
    result["source_unchanged"] = before == after
    if (outcome is not None and result.get("transaction_accepted") and result["source_unchanged"]
            and result["checks"] == EXPECTED_CHECKS):
        result["status"] = "passed"
    _collect(result, runtime_root, output)
    _write_json(output / RESULT_NAME, result)
    return (0 if result["status"] == "passed" else 1), result


def main(argv: list[str] | None = None, *, cache_inputs: Path) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    code, result = run(args.repo, args.runtime_root, args.output, cache_inputs=cache_inputs)
    print(json.dumps({"status": result["status"], "result": str(args.output / RESULT_NAME)}))
    return code


__all__ = ["EXPECTED_CHECKS", "RESULT_SCHEMA", "Refused", "build_runtime", "main",
           "preflight", "readback", "run"]
