"""One immutable provider arm for the APG166E execution package.

The historical paired owner remains the two-arm mechanism owner. F9 needs a
smaller admission unit: one clean subject, one context preparation, one
provider invocation, and one retained result. This module owns that unit and
deliberately has no retry or resume path.
"""
from __future__ import annotations

import ast
import errno
import hashlib
import inspect
import json
import os
import shutil
import stat
import subprocess
import traceback
from collections.abc import Callable, Mapping
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from agent_phase import context_adapter, provider
from agent_phase.acquisition_records import delivery_entries, records
from agent_phase.transmission import direct_bytes

from . import importers
from .evaluate import delivered_totals, load

SCHEMA = "apg.h-arm-result/v1"
CONSTRUCTION_SCHEMA = "apg.h-arm-construction/v1"
# Source-default live admission is never available.  A live arm is admitted
# only by live_admission.admit() from an external manager decision and grant;
# this constant is not consulted by that path and must never become a grant.
LIVE_ADMISSION_AVAILABLE = False
MAX_FILES = 20_000
MAX_BYTES = 128 << 20
_INTEGRITY = "integrity.json"
_RESULT = "result.json"


def _encoded(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_bytes(path: Path, data: bytes) -> None:
    if path.parent.resolve() != path.parent:
        raise ValueError("arm artifact parent must be physical")
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        child = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        with os.fdopen(child, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_json(path: Path, value: Any) -> None:
    _write_bytes(path, _encoded(value))


def snapshot_tree(root: Path) -> dict[str, dict[str, Any]]:
    """Capture a bounded path/mode/content inventory without following links."""
    root = Path(root)
    if root.resolve() != root:
        raise ValueError("subject root must be physical")
    result: dict[str, dict[str, Any]] = {}
    total = 0
    for path in sorted(root.rglob("*")):
        # Git metadata is captured separately as authority evidence.  Keeping
        # it out of the model subject inventory prevents provider-generated
        # object files and index churn from changing the frozen task tree.
        if ".git" in path.relative_to(root).parts:
            continue
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise ValueError("subject symlink refused")
        if stat.S_ISDIR(info.st_mode):
            continue
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("subject nonregular file refused")
        data = direct_bytes(path, utf8=False, max_bytes=MAX_BYTES)
        total += len(data)
        if len(result) >= MAX_FILES or total > MAX_BYTES:
            raise ValueError("subject snapshot exceeds bound")
        result[str(path.relative_to(root))] = {
            "bytes": len(data),
            "sha256": _sha256(data),
            "mode": stat.S_IMODE(info.st_mode),
        }
    return result


def snapshot_dirs(root: Path) -> dict[str, dict[str, Any]]:
    """Capture physical directory topology separately from file inventory."""
    root = Path(root)
    if root.resolve() != root or not root.is_dir():
        raise ValueError("directory root must be physical")
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if ".git" in relative.parts:
            continue
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise ValueError("directory symlink refused")
        if not stat.S_ISDIR(info.st_mode):
            continue
        result[str(relative)] = {"mode": stat.S_IMODE(info.st_mode)}
    return result


def _isolated_git_environment(git: str) -> dict[str, str]:
    """Return the explicit test-only environment used without a manifest.

    This path is retained for the small instrumented arm fixtures.  It is
    deliberately independent of ``os.environ`` so a developer's git config,
    hooks, locale, or shell PATH cannot become arm evidence.
    """
    parent = str(Path(git).parent)
    return {
        "PATH": parent,
        "HOME": parent,
        "TMPDIR": parent,
        "TMP": parent,
        "TEMP": parent,
        "LC_ALL": "C",
        "LANG": "C",
        "TZ": "UTC",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0",
    }


def _manifest_environment(runtime_inputs: Mapping[str, Any], *, cwd: Path) -> dict[str, str]:
    """Build one manifest-derived process environment for the arm boundary."""
    from . import dry_run, runtime_execution, runtime_manifest

    # A direct arm may own a bounded runtime transaction, while a provider-free
    # dry-run may lend its already active transaction.  Reuse that owner so
    # git/context/provider boundaries share one sealed environment and one
    # post-run revalidation instead of creating an ambient one-shot transaction.
    active = dry_run.ACTIVE_RUNTIME.get()
    if active is not None:
        requested = runtime_manifest.manifest_digest(runtime_inputs)
        bound = runtime_manifest.manifest_digest(active.manifest)
        if requested != bound:
            raise ValueError("runtime transaction manifest differs from arm inputs")
        environment = active.environment(cwd=cwd)
    else:
        environment = runtime_execution.build_environment(runtime_inputs, cwd=cwd)
    # These values are fixed H authority policy.  They do not come from the
    # operator shell and ensure every git invocation ignores global/system
    # configuration even when the manifest was captured before this owner ran.
    environment = dict(environment)
    environment.update({
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0",
    })
    return environment


def _acquire_runtime_transaction(
    runtime_inputs: Mapping[str, Any], *, work_dir: Path,
) -> tuple[Any, Any, bool]:
    """Bind one sealed runtime transaction to an arm's execution context.

    The outer provider-free transaction may already own the context.  A direct
    arm borrows only an exact manifest match; otherwise it creates and later
    closes its own bounded transaction.  The context token is returned solely
    for an owned transaction so callers cannot accidentally reset a parent.
    """
    from . import dry_run, runtime_execution, runtime_manifest

    expected = runtime_manifest.manifest_digest(runtime_inputs)
    active = dry_run.ACTIVE_RUNTIME.get()
    if active is not None:
        try:
            bound = runtime_manifest.manifest_digest(active.manifest)
            active.revalidate()
        except (AttributeError, TypeError, ValueError) as error:
            raise ValueError("active runtime transaction is unavailable") from error
        if bound != expected:
            raise ValueError("active runtime transaction does not match arm manifest")
        return active, None, False
    transaction = runtime_execution.begin(runtime_inputs, work_dir=work_dir)
    token = dry_run.ACTIVE_RUNTIME.set(transaction)
    return transaction, token, True


def _git_environment_identity(environment: Mapping[str, str], *, source: str) -> dict[str, Any]:
    if any(not isinstance(key, str) or not isinstance(value, str)
           for key, value in environment.items()):
        raise ValueError("git environment must contain strings")
    return {
        "schema": "apg.h-git-environment/v1",
        "source": source,
        "keys": sorted(environment),
        "sha256": _sha256(_encoded(dict(environment))),
    }


def _git_run(
    git: str,
    subject: Path,
    args: list[str],
    *,
    environment: Mapping[str, str],
    allow_failure: bool = False,
) -> bytes:
    if any(not isinstance(key, str) or not isinstance(value, str)
           for key, value in environment.items()):
        raise ValueError("git environment must contain strings")
    command = [git, "-c", "core.hooksPath=/dev/null", *args]
    completed = subprocess.run(
        command,
        cwd=subject,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
        env=dict(environment),
    )
    if completed.returncode != 0 and not allow_failure:
        raise ValueError(f"git authority command failed: {args[0]}")
    return completed.stdout


def _prepare_subject_repository(
    subject: Path,
    executable_paths: Mapping[str, str] | None,
    *,
    runtime_inputs: Mapping[str, Any] | None = None,
) -> tuple[str, dict[str, str], str]:
    """Create the isolated repository required by real Codex routes.

    The repository is arm-owned and hidden from the subject file inventory.  A
    deterministic initial commit gives before/after authority a real HEAD and
    index to bind, while the provider still sees the exact clean fixture tree.
    """
    configured = (executable_paths or {}).get("git_executable")
    if runtime_inputs is not None:
        from . import runtime_manifest

        expected = runtime_manifest.resolve_executable(runtime_inputs, "git")
        if configured is not None and Path(configured).resolve() != Path(expected).resolve():
            raise ValueError("git executable is not the sealed runtime executable")
        git = expected
        environment = _manifest_environment(runtime_inputs, cwd=subject)
        source = "runtime-manifest"
    else:
        git = configured or shutil.which("git")
        environment = None
        source = "test-only-isolated"
    if not git:
        raise ValueError("git executable required for provider subject authority")
    git = str(Path(git).resolve())
    if environment is None:
        environment = _isolated_git_environment(git)
    _git_run(git, subject, ["-c", "init.defaultBranch=main", "init", "--quiet"], environment=environment)
    _git_run(git, subject, ["config", "user.name", "APGR execution"], environment=environment)
    _git_run(git, subject, ["config", "user.email", "apgr-execution@invalid"], environment=environment)
    _git_run(git, subject, ["add", "--all"], environment=environment)
    _git_run(git, subject, ["commit", "--quiet", "--allow-empty", "-m", "initial frozen subject"], environment=environment)
    return git, environment, source


def _git_authority(
    subject: Path,
    git: str,
    *,
    environment: Mapping[str, str] | None = None,
    environment_source: str = "test-only-isolated",
) -> dict[str, Any]:
    """Capture HEAD, index, and worktree identities independently."""
    environment = dict(environment or _isolated_git_environment(git))
    environment_identity = _git_environment_identity(environment, source=environment_source)
    git_dir = subject / ".git"
    if git_dir.is_symlink() or not git_dir.is_dir():
        raise ValueError("subject git directory is not physical")
    head_bytes = _git_run(git, subject, ["rev-parse", "--verify", "HEAD"], environment=environment)
    head = head_bytes.decode("ascii", errors="strict").strip()
    index = git_dir / "index"
    if index.is_symlink() or not index.is_file():
        raise ValueError("subject git index is unavailable")
    index_bytes = direct_bytes(index, utf8=False, max_bytes=MAX_BYTES)
    status = _git_run(git, subject, ["status", "--porcelain=v1", "--untracked-files=all"], environment=environment)
    listing = _git_run(git, subject, ["ls-files", "--stage"], environment=environment)
    diff = _git_run(git, subject, ["diff", "--no-ext-diff", "--binary"], environment=environment)
    return {
        "available": True,
        "executable": git,
        "environment": environment_identity,
        "head": head,
        "index": {"bytes": len(index_bytes), "sha256": _sha256(index_bytes)},
        "worktree": {
            "status_bytes": len(status),
            "status_sha256": _sha256(status),
            "listing_sha256": _sha256(listing),
            "diff_bytes": len(diff),
            "diff_sha256": _sha256(diff),
        },
    }


def _source_launcher(source_root: Path, relative: str) -> tuple[str, dict[str, Any]]:
    """Bind one repository-owned provider wrapper and its byte identity."""
    path = source_root / relative
    if (path.resolve() != path or path.is_symlink() or not path.is_file()
            or not os.access(path, os.X_OK)):
        raise ValueError(f"source provider launcher is unavailable: {relative}")
    data = direct_bytes(path, utf8=False, max_bytes=MAX_BYTES)
    return str(path), {
        "path": str(path),
        "bytes": len(data),
        "sha256": _sha256(data),
    }


def _live_provider_bindings(
    source_root: Path,
    runtime_inputs: Mapping[str, Any],
) -> tuple[dict[str, str], dict[str, Any]]:
    """Resolve live wrappers and real binaries without launching a provider.

    ``provider.build_argv`` consumes the repository wrappers for Claude and
    Antigravity.  The manifest-bound provider binaries are retained alongside
    those wrappers as separate runtime identities for the wrapper environment;
    they are never substituted into the wrapper argv slot.
    """
    from . import runtime_manifest

    checked = runtime_manifest.verify_complete(runtime_inputs, probe_versions=False)
    claude_launcher, claude_identity = _source_launcher(source_root, provider.CLAUDE_LAUNCHER)
    antigravity_launcher, antigravity_identity = _source_launcher(source_root, provider.ANTIGRAVITY_LAUNCHER)
    paths = {
        "git_executable": runtime_manifest.resolve_executable(checked, "git"),
        "codex_executable": runtime_manifest.resolve_executable(checked, "codex"),
        "claude_launcher": claude_launcher,
        "antigravity_launcher": antigravity_launcher,
    }
    provider_identities: dict[str, Any] = {}
    for name in ("codex", "claude", "antigravity"):
        record = checked["runtimes"].get(name)
        if not isinstance(record, Mapping) or record.get("executable") is None:
            provider_identities[name] = {"status": "unavailable"}
            continue
        executable = runtime_manifest.resolve_executable(checked, name)
        paths[f"{name}_executable"] = executable
        provider_identities[name] = {
            "status": "bound",
            "path": executable,
            "identity": runtime_manifest.file_identity(executable),
        }
    bindings = {
        "schema": "apg.h-provider-runtime-bindings/v1",
        "manifest_sha256": runtime_manifest.manifest_digest(checked),
        "launchers": {
            "claude": claude_identity,
            "antigravity": antigravity_identity,
        },
        "provider_executables": provider_identities,
        "environment": {
            "source": "runtime-manifest",
            "manifest_sha256": runtime_manifest.manifest_digest(checked),
        },
    }
    return paths, bindings


def _bound_provider_runner(environment: Mapping[str, str]) -> Callable[..., Any]:
    """Close the manifest environment over the real provider runner."""
    bound = dict(environment)

    def run_bound(*args: Any, **kwargs: Any) -> Any:
        if "environment" in kwargs:
            raise ValueError("live provider environment is source-bound")
        return provider.run(*args, environment=bound, **kwargs)

    return run_bound


def _route(route: Mapping[str, Any], mode: str, execution: str | None) -> dict[str, Any]:
    if not isinstance(route, Mapping):
        raise ValueError("arm route must be an object")
    if route.get("requested_mode", mode) != mode:
        raise ValueError("route mode does not match arm")
    selected = dict(route)
    binding = selected.get("role_binding")
    if isinstance(binding, Mapping):
        selected.setdefault("binding_id", binding.get("binding_id"))
        selected.setdefault("roles", binding.get("roles"))
    selected.setdefault("execution", execution or "instrumented")
    if selected.get("provider") not in importers.PROVIDERS:
        raise ValueError("unsupported provider")
    required = ("provider", "profile", "model", "binding_id", "roles", "execution")
    if any(not selected.get(key) for key in required):
        raise ValueError("incomplete arm route")
    if selected["execution"] not in ("instrumented", "live"):
        raise ValueError("unsupported execution mode")
    if not isinstance(selected["roles"], list) or not selected["roles"]:
        raise ValueError("route roles required")
    optional = (
        "requested_mode", "scenario_id", "source_identity", "subject_factory_identity",
        "construction_identity", "route_identity", "source_sha256", "identity_sources",
        "role_binding",
    )
    return {key: selected[key] for key in (*required, *optional) if key in selected}


_CONSTRUCTION_TOKEN = object()


def _frozen_inputs(source_root: Path, scenario_id: str, mode: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Load one scenario and route from the source-owned frozen bindings."""
    from .preregistration import verify_bindings

    if mode not in ("static", "adaptive"):
        raise ValueError("frozen arm mode is invalid")
    bindings = verify_bindings(source_root)
    try:
        row = next(item for item in bindings["scenarios"] if item["scenario_id"] == scenario_id)
    except StopIteration as error:
        raise ValueError("unknown frozen scenario") from error
    scenario_path = source_root / row["scenario_path"]
    scenario = load(scenario_path)
    if scenario.get("scenario_id") != scenario_id:
        raise ValueError("frozen scenario identity is invalid")
    route = deepcopy(dict(row["routes"][mode]))
    source_identity = {
        "schema": "apg.h-source-binding/v1",
        "owner": "testing.h_eval.preregistration",
        "scenario_id": scenario_id,
        "mode": mode,
        "bindings_path": "testing/h_eval/scenario-bindings.json",
        "bindings_sha256": _sha256((source_root / "testing/h_eval/scenario-bindings.json").read_bytes()),
        "scenario_path": row["scenario_path"],
        "scenario_sha256": row["scenario_sha256"],
        "route_sha256": _sha256(_encoded(route)),
        "source_sha256": deepcopy(dict(route.get("source_sha256", {}))),
        "identity_sources": list(route.get("identity_sources", [])),
    }
    route["scenario_id"] = scenario_id
    route["source_identity"] = source_identity
    return scenario, row, route, source_identity


def _frozen_subject(source_root: Path, scenario_id: str) -> tuple[dict[str, bytes], dict[str, int], dict[str, Any]]:
    """Read subject bytes and mode identities from the source-owned factory."""
    from . import subjects

    corpus = source_root / "testing/fixtures/context-eval"
    subjects.verify_manifest(corpus_root=corpus)
    manifest = subjects.load_manifest(corpus_root=corpus)
    entry = manifest["scenarios"].get(scenario_id)
    if not isinstance(entry, Mapping):
        raise ValueError("frozen subject factory entry is unavailable")
    files = subjects.subject_files(scenario_id, corpus_root=corpus)
    declared = {item["path"]: item for item in entry.get("files", []) if isinstance(item, Mapping)}
    if set(files) != set(declared):
        raise ValueError("subject factory files differ from frozen manifest")
    modes = {name: int(item["mode"]) for name, item in declared.items()}
    factory_identity = {
        "schema": "apg.h-subject-factory-identity/v1",
        "owner": "testing.h_eval.subjects",
        "manifest_path": "testing/fixtures/context-eval/subjects/manifest.json",
        "manifest_sha256": _sha256((corpus / "subjects/manifest.json").read_bytes()),
        "scenario_id": scenario_id,
        "scenario_sha256": entry.get("scenario_sha256"),
        "tree_sha256": entry.get("tree_sha256"),
        "files": deepcopy(dict(declared)),
    }
    return files, modes, factory_identity


def _oracle_identity(scenario: Mapping[str, Any], source_identity: Mapping[str, Any]) -> dict[str, Any]:
    expected = scenario.get("expected_outcome", {}).get("quality_oracle")
    return {
        "schema": "apg.h-oracle-owner/v1",
        "owner": "testing.h_eval.oracles",
        "factory": "oracle_for",
        "scenario_id": scenario.get("scenario_id"),
        "quality_oracle_sha256": _sha256(_encoded(expected)),
        "source_binding_sha256": _sha256(_encoded(source_identity)),
    }


def _importer_identity(route: Mapping[str, Any]) -> dict[str, Any]:
    importer = importers.importer_for(route["provider"])
    return {
        "schema": "apg.h-importer-owner/v1",
        "owner": "testing.h_eval.importers",
        "factory": "importer_for",
        "provider": route["provider"],
        "name": importer.__name__,
    }


def _runtime_observation(runtime_inputs: Mapping[str, Any] | None, *, live: bool) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    if runtime_inputs is None:
        if live:
            raise ValueError("sealed runtime inputs required before live arm")
        return None, {"schema": "apg.h-runtime-observation/v1", "status": "unavailable", "test_only": True}
    from . import runtime_manifest

    if runtime_inputs.get("schema") != runtime_manifest.COMPLETE_SCHEMA:
        raise ValueError("complete v2 runtime manifest required for arm construction")
    current = runtime_manifest.verify_complete(runtime_inputs, probe_versions=live)
    if live and current.get("lifecycle", {}).get("state") != "sealed":
        raise ValueError("sealed runtime manifest required before live arm")
    digest = runtime_manifest.manifest_digest(current)
    return current, {
        "schema": "apg.h-runtime-observation/v1",
        "status": "valid",
        "manifest_sha256": digest,
        "lifecycle": current["lifecycle"],
        "pre_run": "valid",
        "post_run": "pending",
        "test_only": not live,
    }


def _construction_record(
    scenario: Mapping[str, Any],
    route: Mapping[str, Any],
    source_identity: Mapping[str, Any],
    subject_factory: Mapping[str, Any],
    task_contract: Mapping[str, Any],
    oracle_identity: Mapping[str, Any],
    importer_identity: Mapping[str, Any],
    runtime_observation: Mapping[str, Any],
    execution_mode: str,
) -> dict[str, Any]:
    return {
        "schema": CONSTRUCTION_SCHEMA,
        "owner": "testing.h_eval.execution",
        "scenario_id": scenario["scenario_id"],
        "mode": route["requested_mode"],
        "execution": execution_mode,
        "source": deepcopy(dict(source_identity)),
        "route": {
            "provider": route["provider"], "profile": route["profile"], "model": route["model"],
            "binding_id": route["role_binding"]["binding_id"],
            "roles": list(route["role_binding"]["roles"]),
            "source_sha256": deepcopy(dict(route.get("source_sha256", {}))),
            "sha256": _sha256(_encoded(route)),
        },
        "subject_factory": deepcopy(dict(subject_factory)),
        "task_contract": deepcopy(dict(task_contract)),
        "oracle": deepcopy(dict(oracle_identity)),
        "importer": deepcopy(dict(importer_identity)),
        "runtime": deepcopy(dict(runtime_observation)),
        "replay_authorized": False,
    }


def _source_context_inputs(
    *,
    source_root: Path,
    subject: Path,
    run: Path,
    scenario: Mapping[str, Any],
    route: Mapping[str, Any],
    mode: str,
    runtime_inputs: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Derive context planning and instruction custody from frozen sources."""
    from . import dry_run

    mandatory, instruction_records, plan_inputs = dry_run._frozen_plan_inputs(
        source_root, scenario, route,
    )
    source_identity = route.get("source_identity")
    if not isinstance(source_identity, Mapping):
        raise ValueError("source context requires the frozen source identity")
    provenance = source_identity.get("identity_sources")
    if not isinstance(provenance, list) or not provenance or any(not isinstance(item, str) for item in provenance):
        raise ValueError("frozen route source provenance is incomplete")
    capture = {
        "settings": {"mode": mode, **dict(plan_inputs.get("settings", {}))},
        "provenance": list(provenance),
        "overrides": [dict(item) for item in plan_inputs.get("overrides", [])],
        "apgr_home": str(run),
        "project_root": str(subject),
    }
    records_for_plan = deepcopy(list(instruction_records))
    argv_suffix = None
    if route["provider"] == "codex":
        # Resolve standing guidance only from the accepted source tree.  This
        # avoids codex_guidance_overrides(), whose disable-policy read is
        # intentionally operator-owned and therefore unsuitable for a frozen
        # H arm context record.
        from agent_source_guidance import source_guidance

        provider_file = (scenario.get("mandatory_instructions") or {}).get("provider_file")
        if provider_file != "codex/AGENTS.md":
            raise ValueError("codex route provider instruction source is not frozen")
        guidance = source_guidance(
            source_root / "codex", [], workers=False,
            instruction_file="AGENTS.md", provider="codex",
            provider_mode="instructions", executable="rtk",
        )
        for component in guidance.instruction_components:
            retained = deepcopy(dict(component))
            retained.setdefault("id", "standing-and-rtk")
            retained.setdefault("bytes", retained.get("source_bytes"))
            retained.setdefault("sha256", retained.get("source_sha256"))
            records_for_plan.append(retained)
        if guidance.prompt:
            payload = "developer_instructions=" + json.dumps(
                guidance.prompt, ensure_ascii=False,
            )
            argv_suffix = ("-c", payload)

    planner = None
    projection = None
    if mode == "adaptive":
        # The native planner must be run by the sealed RuntimeTransaction
        # owned by the enclosing provider-free transaction.  Falling back to
        # context_adapter.native_plan here would reintroduce ambient PATH.
        def planner(request: Mapping[str, Any], supplied: Mapping[str, Any]) -> dict[str, Any]:
            if runtime_inputs is not None and dry_run.ACTIVE_RUNTIME.get() is None:
                raise ValueError("sealed runtime transaction is required for adaptive arm planning")
            return dry_run._native_frozen_planner(
                request, supplied,
                mandatory=mandatory,
                facts=plan_inputs.get("facts", []),
                overrides=plan_inputs.get("overrides", []),
            )

        if scenario["scenario_id"] not in {"scenario-05", "scenario-07", "scenario-13"}:
            # The same source-owned bridge is exercised by instrumented
            # provider-free arms and remains available to the later live arm.
            # Its qualification receipt is still explicitly plumbing-only; it
            # never upgrades live readiness or native discovery evidence.
            projection = dry_run._ProviderFreeProjection(
                run_dir=run / "projection",
                scenario_id=scenario["scenario_id"],
                source_root=source_root,
            )

    return {
        "capture": capture,
        "planner": planner,
        "projection": projection,
        "instruction_records": records_for_plan,
        "argv_suffix": argv_suffix,
        "mandatory": mandatory,
        "plan_inputs": plan_inputs,
    }


def _safe_subject_files(subject_files: Mapping[str, bytes | str]) -> dict[str, bytes]:
    if not isinstance(subject_files, Mapping) or not subject_files or len(subject_files) > MAX_FILES:
        raise ValueError("bounded clean subject required")
    output: dict[str, bytes] = {}
    total = 0
    for name, value in subject_files.items():
        if not isinstance(name, str) or Path(name).is_absolute() or "\\" in name:
            raise ValueError("unsafe subject path")
        parts = name.split("/")
        if any(part in ("", ".", "..") for part in parts):
            raise ValueError("unsafe subject path")
        if isinstance(value, str):
            value = value.encode()
        if not isinstance(value, bytes):
            raise ValueError("subject file bytes required")
        total += len(value)
        if total > MAX_BYTES:
            raise ValueError("subject exceeds archive budget")
        output[name] = value
    return output


def _bind_instrumented_executable(
    arm_dir: Path,
    route: Mapping[str, Any],
    executable_paths: Mapping[str, str] | None,
    runner: Callable[..., Any] | None,
) -> dict[str, str]:
    """Bind an instrumented route to an arm-owned fixture or active tripwire."""
    paths = {str(key): str(value) for key, value in (executable_paths or {}).items()}
    if runner is not None:
        return paths
    provider_key = {
        "codex": "codex_executable",
        "claude": "claude_launcher",
        "antigravity": "antigravity_launcher",
    }[route["provider"]]
    requested = paths.get(provider_key)
    if not requested:
        raise ValueError("instrumented arm requires an explicit fake runner or executable")
    path = Path(requested)
    if path.resolve() != path or path.is_symlink() or not path.is_file() or not os.access(path, os.X_OK):
        raise ValueError("instrumented task executable must be a direct executable fixture")
    guard = None
    try:
        from .provider_free import ACTIVE_GUARD
        guard = ACTIVE_GUARD.get()
    except ImportError:
        pass
    if guard is not None:
        expected = Path(guard.executable(route["provider"], route["profile"]))
        try:
            path.relative_to(arm_dir.parent.resolve())
        except ValueError:
            # An absolute path outside the arm-owned fixture root must never
            # bypass the durable guard while provider-free qualification runs.
            paths[provider_key] = str(expected)
    else:
        try:
            path.relative_to(arm_dir.parent.resolve())
        except ValueError as error:
            raise ValueError("instrumented task executable must be arm-owned") from error
    return paths


def _files_from_root(root: Path) -> dict[str, bytes]:
    inventory = snapshot_tree(root)
    return {name: direct_bytes(root / name, utf8=False, max_bytes=MAX_BYTES) for name in inventory}


def _materialize(subject: Path, subject_files: Mapping[str, bytes | str],
                 modes: Mapping[str, int] | None = None) -> None:
    for name, data in _safe_subject_files(subject_files).items():
        path = subject / name
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        _write_bytes(path, data)
        if modes is not None and name in modes:
            os.chmod(path, int(modes[name]), follow_symlinks=False)


def _call_oracle(
    oracle: Any,
    subject: Path,
    returned: Any,
    scenario: Mapping[str, Any],
    *,
    before: Mapping[str, Any],
    arm_evidence: Mapping[str, Any],
    provider_result: Mapping[str, Any],
) -> Any:
    if oracle is None:
        raise ValueError("substantive oracle owner required")
    target = getattr(oracle, "evaluate", oracle)
    if not callable(target):
        raise ValueError("oracle is not callable")
    try:
        signature = inspect.signature(target)
    except (TypeError, ValueError):
        signature = None
    keyword_call = (
        (scenario["scenario_id"], subject),
        {
            "before": before,
            "arm_evidence": arm_evidence,
            "provider_result": provider_result,
        },
    )
    if signature is not None:
        try:
            signature.bind(*keyword_call[0], **keyword_call[1])
        except TypeError:
            pass
        else:
            return target(*keyword_call[0], **keyword_call[1])
    candidates = ((subject, returned, scenario), (subject, returned), (scenario, subject), (subject,))
    for args in candidates:
        if signature is None:
            return target(*args)
        try:
            signature.bind(*args)
        except TypeError:
            continue
        return target(*args)
    raise TypeError("unsupported oracle signature")


def _call_importer(importer: Callable[..., Any], raw: bytes, route: Mapping[str, Any],
                   terminal: Mapping[str, Any]) -> Any:
    try:
        signature = inspect.signature(importer)
    except (TypeError, ValueError):
        return importer(raw, route, terminal=terminal)
    try:
        signature.bind(raw, route, terminal=terminal)
    except TypeError:
        signature.bind(raw, route)
        return importer(raw, route)
    return importer(raw, route, terminal=terminal)


def _normalize_returned(value: Any) -> Any:
    if isinstance(value, tuple) and len(value) >= 3 and isinstance(value[0], int):
        return SimpleNamespace(
            exit_code=value[0],
            stdout=value[1],
            stderr=value[2],
            truncated=bool(value[3]) if len(value) > 3 else False,
            stderr_truncated=bool(value[6]) if len(value) > 6 else False,
        )
    return value


def _terminal(returned: Any) -> dict[str, Any]:
    stdout = getattr(returned, "stdout", b"")
    stderr = getattr(returned, "stderr", b"")
    if not isinstance(stdout, bytes) or not isinstance(stderr, bytes):
        raise ValueError("provider streams must be bytes")
    return {
        "exit_code": getattr(returned, "exit_code", None),
        "truncated": bool(getattr(returned, "truncated", False)),
        "stderr_truncated": bool(getattr(returned, "stderr_truncated", False)),
        "stdout": {"bytes": len(stdout), "sha256": _sha256(stdout)},
        "stderr": {"bytes": len(stderr), "sha256": _sha256(stderr)},
        "cleanup": getattr(returned, "cleanup", None),
    }


def _oracle_receipt(value: Any, expected: Any) -> dict[str, Any]:
    from .paired import import_oracle
    return import_oracle(value, expected)


def _delivery_evidence(
    run: Path,
    mode: str,
    route: Mapping[str, Any],
    extra_events: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    trace = load(run / "attempt.context-deliveries.json")
    diagnostics: list[Any] = []
    late = records(run, mode, diagnostics=diagnostics)
    observed = delivery_entries(
        [*trace["events"], *(row["event"] for row in late), *(extra_events or [])],
        run_id=mode,
        binding_id=route["binding_id"],
        attempt_id="one",
    )
    if trace.get("coverage") != "complete" or observed.get("coverage") != "complete" or diagnostics:
        raise ValueError("incomplete transmission coverage")
    deliveries = observed["deliveries"]
    initial, cumulative = delivered_totals(deliveries)
    return {
        "deliveries": deliveries,
        "initial": initial,
        "cumulative": cumulative,
        "coverage": "complete",
        "late_acquisitions": [
            row for row in late
            if isinstance(row.get("event"), Mapping)
            and row["event"].get("phase") == "late"
        ],
    }


SETTINGS_RECEIPT_SCHEMA = "apg.h-settings-observation/v1"
DISCOVERY_RECEIPT_SCHEMA = "apg.h-discovery-observation/v1"
# An absent provider global skill root is observed as absent: only the named
# root and the identity metadata of its lexical path components are read.
DISCOVERY_ABSENT_RECEIPT_SCHEMA = "apg.h-discovery-observation/v2"
DISCOVERY_ABSENCE_SCHEMA = "apg.h-discovery-absence/v1"


def _observation_identity(path: Path, *, unresolved_links: bool = False) -> dict[str, Any]:
    """Read one manifest-bound file or directory identity.

    The oracle's ``_file_identity`` vocabulary is intentionally used for both
    regular settings files and discovery directories.  Directory bytes and
    digests come from the same bounded physical-tree owner as the runtime
    manifest; no marker file is created to stand in for an operator input.

    ``unresolved_links`` is enabled only when the provider's global discovery
    root itself exists, where an operator may legitimately keep a stale skill
    link.  The link text and errno are bound into the digest; settings,
    projection and run-root observations keep the strict refusal.  An absent
    discovery root is never replaced by an inventory of an ancestor; see
    ``_discovery_root_state``.
    """
    path = Path(path)
    if path.resolve() != path or path.is_symlink() or not path.exists():
        raise ValueError("observation target must be a present physical path")
    info = path.lstat()
    if stat.S_ISREG(info.st_mode):
        data = direct_bytes(path, utf8=False, max_bytes=MAX_BYTES)
        digest = _sha256(data)
        size = len(data)
    elif stat.S_ISDIR(info.st_mode):
        from . import runtime_manifest

        observed = runtime_manifest._input(path, unresolved_links=unresolved_links)
        if observed.get("kind") != "directory":
            raise ValueError("directory observation did not retain a directory identity")
        digest = observed.get("sha256")
        size = observed.get("bytes")
        if not isinstance(digest, str) or len(digest) != 64 or type(size) is not int:
            raise ValueError("directory observation identity is incomplete")
    else:
        raise ValueError("observation target must be a regular file or directory")
    return {
        "path": str(path),
        "device": int(info.st_dev),
        "inode": int(info.st_ino),
        "mode": stat.S_IMODE(info.st_mode),
        "bytes": size,
        "sha256": digest,
    }


def _settings_path_from_argv(run: Path, argv: list[str]) -> Path | None:
    """Resolve an argv settings handoff without accepting inline contents."""
    for index, argument in enumerate(argv[:-1]):
        if argument != "--settings":
            continue
        candidate = argv[index + 1]
        if not candidate or candidate.lstrip().startswith("{"):
            continue
        path = Path(candidate)
        if not path.is_absolute() or path.resolve() != path:
            raise ValueError("settings handoff must be an absolute physical path")
        if path.is_symlink() or not path.is_file():
            raise ValueError("settings handoff is unavailable")
        return path
    return None


def _manifest_environment_home(runtime_inputs: Mapping[str, Any]) -> Path:
    environment = runtime_inputs.get("environment")
    home = environment.get("home") if isinstance(environment, Mapping) else None
    if not isinstance(home, str) or not home:
        raise ValueError("runtime manifest HOME is not bound")
    path = Path(home)
    if path.resolve() != path or path.is_symlink() or not path.is_dir():
        raise ValueError("runtime manifest HOME is not a physical directory")
    return path


def _global_discovery_candidate(runtime_inputs: Mapping[str, Any], provider_name: str) -> Path:
    """Resolve the provider's global skill root under the sealed HOME.

    This is an observation boundary only.  The provider is never launched by
    this module, and the returned path is checked against the manifest-bound
    environment rather than the process environment.
    """
    home = _manifest_environment_home(runtime_inputs)
    if provider_name == "claude":
        values = runtime_inputs.get("environment", {}).get("set", {})
        configured = values.get("CLAUDE_CONFIG_DIR") if isinstance(values, Mapping) else None
        base = Path(configured) if isinstance(configured, str) and configured else home / ".claude"
        return base / "skills"
    if provider_name == "codex":
        return home / ".agents" / "skills"
    if provider_name == "antigravity":
        return home / ".gemini" / "skills"
    raise ValueError("unsupported provider discovery root")


def discovery_absence_digest(record: Mapping[str, Any]) -> str:
    """Digest a discovery absence record without its own digest field."""
    return _sha256(_encoded({key: value for key, value in record.items() if key != "sha256"}))


def _component_identity(path: Path, info: os.stat_result) -> dict[str, Any]:
    """Identity metadata of one existing lexical component; never its contents."""
    if stat.S_ISLNK(info.st_mode):
        try:
            link_text = os.readlink(path)
            target = os.stat(path)
        except OSError as error:
            # A broken or unreadable link is not an absence.
            raise ValueError("discovery root path link is unresolved") from error
        if not stat.S_ISDIR(target.st_mode):
            raise ValueError("discovery root path component is not a directory")
        return {
            "path": str(path), "kind": "symlink", "device": int(info.st_dev),
            "inode": int(info.st_ino), "mode": int(info.st_mode), "link_text": link_text,
            "target": {"device": int(target.st_dev), "inode": int(target.st_ino),
                       "mode": int(target.st_mode)},
        }
    if not stat.S_ISDIR(info.st_mode):
        raise ValueError("discovery root path component is not a directory")
    return {"path": str(path), "kind": "directory", "device": int(info.st_dev),
            "inode": int(info.st_ino), "mode": int(info.st_mode)}


def _discovery_root_state(candidate: Path) -> tuple[str, Any]:
    """Classify a provider global skill root as present or explicitly absent.

    Only the lexical components from ``/`` to the root are examined, one
    ``lstat`` each (plus ``readlink``/``stat`` for a symlink component).  No
    directory is listed, hashed or created, and no size or time field is
    recorded, so unrelated sibling churn cannot change the record.  A
    component that exists but is not a directory, a broken link, a permission
    error or any other ``OSError`` refuses; only ``ENOENT`` becomes absence.

    Returns ``("present", candidate)`` when the root exists in any form (the
    caller's physical-directory observation then applies), otherwise
    ``("absent", record)`` with a self-digested absence record.
    """
    candidate = Path(candidate)
    if not candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("discovery root must be an absolute lexical path")
    chain = [Path(*candidate.parts[:index + 1]) for index in range(len(candidate.parts))]
    components: list[dict[str, Any]] = []
    for index, path in enumerate(chain):
        try:
            info = os.lstat(path)
        except FileNotFoundError:
            if index == 0:
                raise ValueError("discovery root has no existing path prefix")
            missing = [str(item) for item in chain[index:]]
            record: dict[str, Any] = {
                "schema": DISCOVERY_ABSENCE_SCHEMA,
                "kind": "absent",
                "lexical_root": str(candidate),
                "missing": missing,
                "existing_prefix": str(chain[index - 1]),
                "components": components,
            }
            record["sha256"] = discovery_absence_digest(record)
            return "absent", record
        except OSError as error:
            raise ValueError("discovery root path component is not observable") from error
        if path == candidate:
            return "present", candidate
        components.append(_component_identity(path, info))
    raise ValueError("discovery root path component is not observable")


def _operator_settings_paths(runtime_inputs: Mapping[str, Any]) -> list[Path]:
    """Select the real operator settings paths bound by the sealed manifest."""
    if runtime_inputs.get("schema") != "apg.h-runtime-inputs/v2":
        raise ValueError("typed settings observations require a complete runtime manifest")
    groups = runtime_inputs.get("groups")
    files = runtime_inputs.get("files")
    if not isinstance(groups, Mapping) or not isinstance(files, Mapping):
        raise ValueError("runtime manifest source groups are unavailable")
    declared = groups.get("operator_settings")
    if not isinstance(declared, list) or not declared:
        raise ValueError("operator settings sources are not manifest-bound")
    settings_paths: list[Path] = []
    for value in declared:
        if not isinstance(value, str) or not value.startswith("/"):
            raise ValueError("operator settings path is not physical")
        record = files.get(value)
        if not isinstance(record, Mapping) or not isinstance(record.get("physical_path"), str):
            raise ValueError("operator settings path is not retained by the manifest")
        path = Path(record["physical_path"])
        if path.resolve() != path or path.is_symlink() or not path.exists():
            raise ValueError("manifest-bound operator settings path drifted")
        settings_paths.append(path)
    return settings_paths


def _operator_observation(runtime_inputs: Mapping[str, Any], *, provider_name: str) -> dict[str, Any]:
    """Observe manifest-bound settings and the provider's global skill root.

    This is the arm-independent half of the begin observation.  The
    non-consuming prelaunch check calls the same owner.
    """
    settings_paths = _operator_settings_paths(runtime_inputs)
    settings_before = [_observation_identity(path) for path in settings_paths]
    candidate = _global_discovery_candidate(runtime_inputs, provider_name)
    state, absence = _discovery_root_state(candidate)
    if state == "present":
        # The real skill root keeps the accepted bounded content inventory and
        # its stale-link tolerance.
        if candidate.is_symlink() or not candidate.is_dir() or candidate.resolve() != candidate:
            raise ValueError("discovery root is not a physical directory")
        scope, global_absent = "existing-root", []
        global_before = _observation_identity(candidate, unresolved_links=True)
    else:
        # An absent root is observed as absent.  No ancestor (HOME, a vendor
        # store) is inventoried or stands in for the missing root.
        scope, global_absent, global_before = "absent-root", list(absence["missing"]), absence
    return {
        "settings_paths": settings_paths,
        "settings_before": settings_before,
        "global_candidate": candidate,
        "global_scope": scope,
        "global_absent": global_absent,
        "global_path": candidate,
        "global_before": global_before,
    }


def _manifest_observation_paths(
    runtime_inputs: Mapping[str, Any],
    *,
    provider_name: str,
    argv: list[str],
    run: Path,
) -> dict[str, Any]:
    """Select real operator/settings and discovery paths from the sealed manifest."""
    operator = _operator_observation(runtime_inputs, provider_name=provider_name)
    argv_settings = _settings_path_from_argv(run, argv)
    projection_before = None
    if argv_settings is not None and argv_settings not in operator["settings_paths"]:
        projection_before = _observation_identity(argv_settings)
    return {
        **operator,
        "projection_path": argv_settings if projection_before is not None else None,
        "projection_before": projection_before,
        "run_root": run,
        "run_root_before": _observation_identity(run),
    }


def _begin_observation(
    run: Path,
    scenario: Mapping[str, Any],
    mode: str,
    argv: list[str],
    provider_name: str,
    runtime_inputs: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    """Open a real runtime observation boundary, or remain test-only absent."""
    if runtime_inputs is None:
        # Direct instrumented unit fixtures do not own operator settings or a
        # provider HOME.  They remain test-only and must not manufacture a
        # typed settings/discovery receipt from a marker file.
        return None
    return _manifest_observation_paths(
        runtime_inputs,
        provider_name=provider_name,
        argv=argv,
        run=run,
    )


_IDENTITY_FIELDS = ("path", "device", "inode", "mode", "bytes", "sha256")
_MAX_DELTA_ROWS = 64


def _identity_delta(before: Any, after: Any) -> dict[str, Any]:
    """Name the changed fields of two identities; keep only scalar identity values.

    Nested records such as directory entries or absence components contribute
    field names only, never contents.
    """
    left = dict(before) if isinstance(before, Mapping) else {}
    right = dict(after) if isinstance(after, Mapping) else {}
    changed = sorted(key for key in set(left) | set(right) if left.get(key) != right.get(key))
    delta: dict[str, Any] = {"path": left.get("path", right.get("path")), "changed_fields": changed}
    scalar = [key for key in _IDENTITY_FIELDS if key in changed and all(
        isinstance(side.get(key), (int, str, type(None))) for side in (left, right))]
    if scalar:
        delta["before"] = {key: left.get(key) for key in scalar}
        delta["after"] = {key: right.get(key) for key in scalar}
    return delta


def _finish_observation(state: Mapping[str, Any], *, drift: dict[str, Any] | None = None) -> dict[str, Any]:
    """Close the source-owned observation boundary after provider return.

    Every check runs before the first failure is raised, in the historical
    order and with the historical message, so one refusal cannot hide
    another.  ``drift`` receives bounded identity deltas: ``refusing`` names
    changes that refuse the arm and ``informational`` records observed
    changes that are not refusals here (the run root gains the retained
    provider streams; an existing global root is judged by the task oracle).
    """
    sink = drift if drift is not None else {}
    sink.update(refusing=[], unavailable=[], informational=[])
    errors: list[BaseException] = []

    def observe(component: str, read: Callable[[], Any], path: Any = None) -> Any:
        try:
            return read()
        except (OSError, ValueError) as error:
            row = {"component": component, "type": type(error).__name__}
            if path is not None:
                row["path"] = str(path)
            sink["unavailable"].append(row)
            errors.append(error)
            return None

    settings_after = [
        observe("settings", lambda path=Path(path): _observation_identity(path), path)
        for path in state["settings_paths"]
    ]
    changed = [_identity_delta(before, after)
               for before, after in zip(state["settings_before"], settings_after)
               if after is not None and after != before]
    sink["settings"] = {"compared": len(settings_after), "changed": changed[:_MAX_DELTA_ROWS],
                        "changed_omitted": max(0, len(changed) - _MAX_DELTA_ROWS)}
    if changed:
        sink["refusing"].append("settings")
        errors.append(ValueError("manifest-bound operator settings changed during arm"))
    projection_after = None
    if state.get("projection_path") is not None:
        projection_after = observe("projection", lambda: _observation_identity(Path(state["projection_path"])))
        if projection_after is not None and projection_after != state.get("projection_before"):
            sink["refusing"].append("projection")
            sink["projection"] = _identity_delta(state.get("projection_before"), projection_after)
            errors.append(ValueError("run-owned projected settings changed during arm"))
    candidate = Path(state["global_candidate"])
    global_path = Path(state["global_path"])
    absent_root = state.get("global_scope") == "absent-root"
    global_after: Any = None
    if absent_root:
        # Re-examine only the named root and its path components.  Appearance
        # of the root, replacement of a component or a retargeted link on the
        # path refuses; unrelated siblings are never part of the record.
        observed = observe("discovery", lambda: _discovery_root_state(candidate))
        if observed is not None:
            after_state, global_after = observed
            if after_state != "absent":
                sink["refusing"].append("discovery")
                sink["discovery"] = {"scope": "absent-root", "status": "appeared"}
                errors.append(ValueError("global discovery absence assertion changed during arm"))
            elif global_after != state["global_before"]:
                sink["refusing"].append("discovery")
                sink["discovery"] = {"scope": "absent-root",
                                     **_identity_delta(state["global_before"], global_after)}
                errors.append(ValueError("global discovery absent path changed during arm"))
    else:
        global_after = observe("discovery", lambda: _observation_identity(global_path, unresolved_links=True))
        if global_after is not None and global_after != state["global_before"]:
            sink["informational"].append({"component": "discovery", "scope": "existing-root",
                                          **_identity_delta(state["global_before"], global_after)})
    run_root_after = observe("run_root", lambda: _observation_identity(Path(state["run_root"])))
    if run_root_after is not None and run_root_after != state["run_root_before"]:
        sink["informational"].append({"component": "run_root",
                                      **_identity_delta(state["run_root_before"], run_root_after)})
    sink["status"] = "valid" if not errors else "drift" if sink["refusing"] else "error"
    if errors:
        raise errors[0]
    discovery_receipt = {
        "schema": DISCOVERY_RECEIPT_SCHEMA,
        "run_root": deepcopy(dict(state["run_root_before"])),
        "global_before": deepcopy(dict(state["global_before"])),
        "global_after": global_after,
        "scoped_to_run": (Path(state["run_root"]) != candidate
                          and not Path(state["run_root"]).is_relative_to(candidate)),
        "run_root_after": run_root_after,
        "global_path": str(global_path),
        "global_candidate": str(candidate),
        "global_absent": list(state["global_absent"]),
    }
    if absent_root:
        # Additive: an existing root keeps the byte-shape-unchanged v1 receipt.
        discovery_receipt["schema"] = DISCOVERY_ABSENT_RECEIPT_SCHEMA
        discovery_receipt["global_scope"] = "absent-root"
    return {
        "settings_receipt": {
            "schema": SETTINGS_RECEIPT_SCHEMA,
            "before": deepcopy(dict(state["settings_before"][0])),
            "after": dict(settings_after[0]),
            "inputs_before": deepcopy(list(state["settings_before"])),
            "inputs_after": settings_after,
            "manifest_paths": [str(path) for path in state["settings_paths"]],
            "projection_before": deepcopy(state.get("projection_before")),
            "projection_after": projection_after,
        },
        "discovery_receipt": discovery_receipt,
    }


FAILURE_DETAIL_SCHEMA = "apg.h-arm-failure/v1"
_H_EVAL_DIR = Path(__file__).resolve().parent
_MAX_FAILURE_FRAMES = 12
_MAX_FAILURE_REASON = 200


@lru_cache(maxsize=None)
def _source_literals(path: str) -> frozenset[str]:
    """Return the string literals of one ``testing/h_eval`` module."""
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    return frozenset(
        node.value for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    )


def _errno_name(error: BaseException | None) -> str | None:
    value = getattr(error, "errno", None)
    return errno.errorcode.get(value) if type(value) is int else None


def _failure_detail(error: BaseException, step: str) -> dict[str, Any]:
    """Return a bounded, content-free description of an arm failure.

    Only ``testing/h_eval`` frames (file, function, line) are kept, never
    locals.  The message is kept only when it is a string literal in the
    innermost such module; interpolated text may carry paths or values.
    """
    detail: dict[str, Any] = {
        "schema": FAILURE_DETAIL_SCHEMA,
        "step": step,
        "type": type(error).__name__,
        "errno": _errno_name(error),
        "reason": None,
        "reason_omitted": True,
        "cause": None,
        "frames": [],
    }
    try:
        owned = [
            frame for frame in traceback.extract_tb(error.__traceback__)
            if Path(frame.filename).resolve().parent == _H_EVAL_DIR
        ]
        if len(owned) > _MAX_FAILURE_FRAMES:
            owned = owned[:1] + owned[-(_MAX_FAILURE_FRAMES - 1):]
        detail["frames"] = [
            {"file": f"testing/h_eval/{Path(frame.filename).name}", "function": frame.name,
             "line": frame.lineno}
            for frame in owned
        ]
        message = str(error.args[0]) if len(error.args) == 1 and isinstance(error.args[0], str) else None
        if (owned and message and len(message) <= _MAX_FAILURE_REASON
                and message in _source_literals(owned[-1].filename)):
            detail["reason"] = message
            detail["reason_omitted"] = False
        cause = error.__cause__
        if cause is not None:
            detail["cause"] = {"type": type(cause).__name__, "errno": _errno_name(cause)}
    except Exception:  # noqa: BLE001 - diagnostics must never replace the failure
        detail.update({"reason": None, "reason_omitted": True, "frames": [], "cause": None})
    return detail


def _persist_integrity(arm_dir: Path) -> None:
    files = snapshot_tree(arm_dir)
    directories = snapshot_dirs(arm_dir)
    result = files.get(_RESULT)
    if result is None:
        raise ValueError("arm result missing")
    _write_json(arm_dir / _INTEGRITY, {
        "schema": "apg.h-arm-integrity/v1",
        "files": files,
        "directories": directories,
        "result_sha256": result["sha256"],
    })


def _finish(arm_dir: Path, result: dict[str, Any]) -> dict[str, Any]:
    _write_json(arm_dir / _RESULT, result)
    _persist_integrity(arm_dir)
    return result


POSTRUN_SCHEMA = "apg.h-arm-postrun/v1"
PROVIDER_RETURN_SCHEMA = "apg.h-provider-return/v1"
DIAGNOSTIC_SCHEMA = "apg.h-arm-diagnostic/v1"
INVOCATION_SEMANTICS = (
    "provider_invocations counts one admitted runner invocation attempt, recorded after provider "
    "stdin and before the provider environment is bound; postrun_checks.provider_return shows "
    "whether a runner returned. Neither value is a validated model start, authentication status, "
    "cleanup proof or task completion."
)


def _postrun_checks(*, runtime: bool) -> dict[str, Any]:
    """Return the independent post-return outcomes, each explicitly not yet run."""
    return {
        "schema": POSTRUN_SCHEMA,
        "invocation_semantics": INVOCATION_SEMANTICS,
        "provider_return": {"status": "not_run"},
        "observation": {"status": "not_run"},
        "runtime_close": {"status": "not_run" if runtime else "not_applicable"},
    }


def _retain_provider_return(run: Path, returned: Any) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Persist returned provider streams before any independent post-run check.

    Each stream is written once through the exclusive no-follow owner; an
    existing or partial file is never overwritten or removed.  A failed write
    is recorded, not retried, and never escapes, so later checks cannot erase
    the provider outcome.  A returned runner is not a validated model start.
    """
    receipt: dict[str, Any] = {
        "schema": PROVIDER_RETURN_SCHEMA,
        "event": "runner_returned",
        "model_start": "not_established",
        "status": "failed",
        "exit_code": None,
        "transport": "not_evaluated",
        "streams": {},
    }
    try:
        terminal = _terminal(returned)
    except Exception as error:  # noqa: BLE001 - retention must not replace the arm failure
        receipt["failure_detail"] = _failure_detail(error, "provider_return_retain")
        for name in ("stdout", "stderr"):
            receipt["streams"][name] = {"path": f"run/provider.{name}", "status": "not_written"}
        return receipt, None
    # Record the transport outcome now, with the predicate the later
    # provider_terminal step enforces, so an earlier refusal cannot hide it.
    receipt["exit_code"] = terminal["exit_code"]
    receipt["transport"] = "failed" if terminal["exit_code"] != 0 or terminal["truncated"] else "ok"
    retained = 0
    for name, truncated in (("stdout", "truncated"), ("stderr", "stderr_truncated")):
        data = getattr(returned, name, b"")
        row: dict[str, Any] = {"path": f"run/provider.{name}", **terminal[name], "truncated": terminal[truncated]}
        try:
            _write_bytes(run / f"provider.{name}", data)
        except Exception as error:  # noqa: BLE001 - a retention failure stays visible
            row.update(status="write_failed", failure_detail=_failure_detail(error, "provider_return_retain"))
        else:
            row["status"] = "retained"
            retained += 1
        receipt["streams"][name] = row
    receipt["status"] = "retained" if retained == 2 else "partial" if retained else "failed"
    return receipt, terminal


def _failed_runtime_revalidation(
    previous: Mapping[str, Any] | None,
    error: BaseException,
    *,
    owned: bool,
    close: str,
    runtime_inputs: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Replace a pre-run-only runtime record after a failed post-run check.

    The recorded pre-run value is kept; post-run is ``failed``.  The current
    drift is described only by bounded identity rows from
    ``runtime_manifest.drift_report``.  This helper never raises.
    """
    record: dict[str, Any] = {
        **dict(previous or {}),
        "schema": "apg.h-runtime-observation/v1",
        "status": "invalid",
        "pre_run": (previous or {}).get("pre_run", "unknown"),
        "post_run": "failed",
    }
    try:
        record["transaction"] = {
            "schema": "apg.h-runtime-transaction/v1",
            "status": "owned" if owned else "borrowed",
            "begin": "valid",
            "revalidate": "failed",
            "close": close,
        }
        record["failure_detail"] = _failure_detail(error, "runtime_close")
        from . import runtime_manifest
        try:
            record["drift"] = runtime_manifest.drift_report(runtime_inputs or {})
        except Exception as report_error:  # noqa: BLE001
            record["drift"] = {"status": "unavailable", "type": type(report_error).__name__}
    except Exception:  # noqa: BLE001 - the invalid status above must survive
        pass
    return record


def run_one_arm(
    *,
    arm_dir: str | Path,
    source_root: str | Path,
    scenario: Mapping[str, Any],
    mode: str,
    route: Mapping[str, Any],
    subject_files: Mapping[str, bytes | str] | None = None,
    subject_root: str | Path | None = None,
    prompt: bytes | None = None,
    static_context: bytes = b"",
    executable_paths: Mapping[str, str] | None = None,
    oracle: Any = None,
    projection: Any = None,
    planner: Callable[..., Any] | None = None,
    liveness_policy: Any = None,
    capture: Mapping[str, Any] | None = None,
    runtime_inputs: Mapping[str, Any] | None = None,
    seal: Mapping[str, Any] | None = None,
    live_authorization: Mapping[str, Any] | None = None,
    importer: Callable[..., dict[str, Any]] | None = None,
    runner: Callable[..., Any] | None = None,
    invoker: Callable[..., Any] | None = None,
    subject_modes: Mapping[str, int] | None = None,
    construction: Mapping[str, Any] | None = None,
    runtime_observation: Mapping[str, Any] | None = None,
    recovery_receipt: Mapping[str, Any] | None = None,
    _construction_token: object | None = None,
) -> dict[str, Any]:
    """Execute exactly one arm and retain a terminal result on every path.

    The admission directory is created before context preparation. Its
    existence blocks replay even when provider startup fails or a pre-model
    artifact is consumed. A separate attempt must use a fresh directory.
    """
    arm_dir, source_root = Path(arm_dir), Path(source_root)
    if arm_dir.resolve() != arm_dir or source_root.resolve() != source_root:
        raise ValueError("arm and source roots must be physical")
    if not source_root.is_dir() or arm_dir.exists() or arm_dir.is_symlink():
        raise ValueError("arm admission path is unavailable")
    if not isinstance(scenario, Mapping) or not scenario.get("scenario_id"):
        raise ValueError("scenario identity required")
    selected = _route(route, mode, None)
    selected["scenario_id"] = scenario["scenario_id"]
    runtime_bindings: dict[str, Any] | None = None
    admission: dict[str, Any] | None = None
    admission_receipt: dict[str, Any] | None = None
    if selected["execution"] == "live":
        from . import live_admission
        # Only external decision/grant record paths are accepted; booleans,
        # seals and feature flags are refused before any other live work.
        live_admission.check_shape(live_authorization)
        if _construction_token is not _CONSTRUCTION_TOKEN:
            if any(value is not None for value in (
                oracle, importer, runner, invoker, projection, planner, capture,
                subject_root, prompt,
            )) or subject_files is not None or static_context:
                raise ValueError("live arm caller injection is not accepted")
            raise ValueError("live arm requires repository-owned construction")
        if runtime_inputs is None:
            raise ValueError("runtime inputs required before live arm")
        admission = live_admission.admit(
            source_root, live_authorization,
            live_admission.scenario_unit(scenario["scenario_id"], mode),
            runtime_inputs=runtime_inputs,
        )
        from . import runtime_manifest
        runtime_manifest.verify(runtime_inputs, probe_versions=True)
        from .preregistration import verify_bindings
        frozen = next(
            row for row in verify_bindings(source_root)["scenarios"]
            if row["scenario_id"] == scenario["scenario_id"]
        )
        frozen_route = frozen["routes"][mode]
        expected_binding = frozen_route["role_binding"]
        if (
            frozen_route["provider"] != selected["provider"]
            or frozen_route["profile"] != selected["profile"]
            or frozen_route["model"] != selected["model"]
            or expected_binding["binding_id"] != selected["binding_id"]
            or expected_binding["roles"] != selected["roles"]
        ):
            raise ValueError("live arm route is not the frozen scenario route")
        scenario_path = source_root / frozen["scenario_path"]
        if scenario_path.resolve() != scenario_path or not scenario_path.is_file():
            raise ValueError("frozen scenario source is unavailable")
        frozen_scenario = load(scenario_path)
        if _sha256(scenario_path.read_bytes()) != frozen["scenario_sha256"]:
            raise ValueError("frozen scenario identity changed")
        if dict(frozen_scenario) != dict(scenario):
            raise ValueError("live arm scenario is not the frozen scenario")
        derived_scenario, _frozen_row, frozen_route, source_identity = _frozen_inputs(
            source_root, scenario["scenario_id"], mode
        )
        if dict(derived_scenario) != dict(scenario):
            raise ValueError("live arm scenario is not source-owned")
        if construction is None or construction.get("schema") != CONSTRUCTION_SCHEMA:
            raise ValueError("source-owned arm construction is required")
        if construction.get("source") != source_identity:
            raise ValueError("live arm source identity is not frozen")
        if construction.get("route", {}).get("source_sha256") != frozen_route.get("source_sha256"):
            raise ValueError("live arm route source identity is not frozen")
        subject_files, subject_modes, _subject_factory = _frozen_subject(source_root, scenario["scenario_id"])
        task_contract_value = __import__("testing.h_eval.execution_evidence", fromlist=["task_contract"]).task_contract(
            scenario, source_binding=source_identity
        )
        if construction.get("task_contract") != task_contract_value:
            raise ValueError("live arm task contract is not frozen")
        from . import oracles
        oracle = oracles.oracle_for(scenario)
        importer = importers.importer_for(selected["provider"])
        if construction.get("oracle", {}).get("owner") != "testing.h_eval.oracles" or construction.get("importer", {}).get("owner") != "testing.h_eval.importers":
            raise ValueError("live arm substantive owners are not repository-owned")
        runtime_inputs, runtime_observation = _runtime_observation(runtime_inputs, live=True)
        executable_paths, runtime_bindings = _live_provider_bindings(source_root, runtime_inputs)
        selected["runtime_bindings"] = deepcopy(runtime_bindings)
    else:
        subject_modes = subject_modes or {}
        if runner is None:
            provider_key = {
                "codex": "codex_executable",
                "claude": "claude_launcher",
                "antigravity": "antigravity_launcher",
            }[selected["provider"]]
            if not executable_paths or not executable_paths.get(provider_key):
                raise ValueError("instrumented arm requires an explicit fake runner or executable")
    if construction is not None:
        if construction.get("schema") != CONSTRUCTION_SCHEMA:
            raise ValueError("arm construction identity is invalid")
        if construction.get("scenario_id") != scenario["scenario_id"] or construction.get("mode") != mode:
            raise ValueError("arm construction does not bind scenario and mode")
        derived_scenario, _derived_row, derived_route, derived_source = _frozen_inputs(
            source_root, scenario["scenario_id"], mode
        )
        derived_files, _derived_modes, derived_factory = _frozen_subject(source_root, scenario["scenario_id"])
        from .execution_evidence import task_contract
        derived_contract = task_contract(derived_scenario, source_binding=derived_source)
        supplied_files = dict(subject_files or {})
        normalized_supplied = {
            name: value.encode() if isinstance(value, str) else value
            for name, value in supplied_files.items()
        }
        if (dict(derived_scenario) != dict(scenario)
                or construction.get("source") != derived_source
                or construction.get("subject_factory") != derived_factory
                or construction.get("task_contract") != derived_contract
                or normalized_supplied != derived_files):
            raise ValueError("arm construction is not source-owned")
        if (selected["provider"], selected["profile"], selected["model"], selected["binding_id"], selected["roles"]) != (
            derived_route["provider"], derived_route["profile"], derived_route["model"],
            derived_route["role_binding"]["binding_id"], derived_route["role_binding"]["roles"],
        ):
            raise ValueError("arm route is not source-owned")
        selected["source_identity"] = deepcopy(construction.get("source", {}))
        selected["subject_factory_identity"] = deepcopy(construction.get("subject_factory", {}))
        selected["construction_identity"] = _sha256(_encoded(construction))
        selected["route_identity"] = deepcopy(construction.get("route", {}))
    if selected["execution"] == "instrumented":
        executable_paths = _bind_instrumented_executable(
            arm_dir, selected, executable_paths, runner,
        )
    if not isinstance(static_context, bytes):
        raise ValueError("static context must be bytes")
    if prompt is None:
        from .execution_evidence import task_prompt
        prompt = task_prompt(scenario)
    if not isinstance(prompt, bytes):
        raise ValueError("prompt must be bytes")
    prompt.decode("utf-8")
    static_context.decode("utf-8")
    if selected["execution"] == "live":
        from .execution_evidence import task_prompt
        expected_prompt = task_prompt(scenario)
        if prompt != expected_prompt:
            raise ValueError("live arm prompt is not the frozen task prompt")
        # Consume the unit immediately before the arm exists.  A later failure
        # remains a consumed start with retained evidence, never a replay.
        admission_receipt = live_admission.consume(admission)

    arm_dir.mkdir(mode=0o700)
    run = arm_dir / "run"
    subject = arm_dir / "subject"
    run.mkdir(mode=0o700)
    subject.mkdir(mode=0o700)
    # The accepted source manifest owns recursive source custody. Walking the
    # whole repository here would incorrectly reject legitimate repository
    # projections (and would duplicate that manifest's authority).
    source_inventory = {"root": str(source_root), "resolved_root": str(source_root.resolve())}
    if subject_root is not None:
        input_root = Path(subject_root)
        if input_root.resolve() != input_root or not input_root.is_dir():
            raise ValueError("subject source root must be physical")
        subject_files = _files_from_root(input_root)
    if subject_files is None:
        raise ValueError("subject factory output required")
    clean_files = _safe_subject_files(subject_files)
    _materialize(subject, clean_files, subject_modes)
    git_executable, git_environment, git_environment_source = _prepare_subject_repository(
        subject, executable_paths, runtime_inputs=runtime_inputs,
    )
    before = snapshot_tree(subject)
    before_dirs = snapshot_dirs(subject)
    git_before = _git_authority(
        subject, git_executable, environment=git_environment,
        environment_source=git_environment_source,
    )
    _write_json(arm_dir / "admission.json", {
        "schema": SCHEMA,
        "scenario_id": scenario["scenario_id"],
        "mode": mode,
        "route": selected,
        "scenario_sha256": _sha256(_encoded(scenario)),
        "prompt_sha256": _sha256(prompt),
        "subject": before,
        "subject_directories": before_dirs,
        "git_authority_before": git_before,
        "source_inventory_sha256": _sha256(_encoded(source_inventory)),
        "attempt_id": "one",
        "replay_authorized": False,
        "live_admission": deepcopy(admission_receipt),
    })
    if runtime_inputs is not None:
        # Retain the sealed runtime before provider work so failed arms keep a
        # manifest-derived git environment for provider-free readback.
        _write_json(arm_dir / "runtime-inputs.json", runtime_inputs)
    _write_json(run / "started.json", {"attempt_id": "one", "replay_authorized": False})

    result: dict[str, Any] = {
        "schema": SCHEMA,
        "scenario_id": scenario["scenario_id"],
        "mode": mode,
        "route": selected,
        "status": "incomplete",
        "provider_invocations": 0,
        "retries": 0,
        "restarts": 0,
        "attempt_id": "one",
        "replay_authorized": False,
        "subject_before": before,
        "subject_directories_before": before_dirs,
        "git_authority_before": git_before,
        "source_inventory_sha256": _sha256(_encoded(source_inventory)),
        "exact_recovery": None,
        "construction": deepcopy(dict(construction)) if construction is not None else None,
        "runtime_revalidation": deepcopy(dict(runtime_observation)) if runtime_observation is not None else None,
        "recovery_receipt": deepcopy(dict(recovery_receipt)) if recovery_receipt is not None else None,
        "settings_receipt": None,
        "discovery_receipt": None,
        "live_admission": deepcopy(admission_receipt),
        "postrun_checks": _postrun_checks(runtime=runtime_inputs is not None),
    }
    postrun_checks = result["postrun_checks"]
    source_context: dict[str, Any] | None = None
    runtime_transaction = None
    runtime_token = None
    runtime_transaction_owned = False
    runtime_transaction_closed = False
    returned = None
    observation_state: Mapping[str, Any] | None = None
    # Prospective diagnostics only: the last step entered before a failure.
    step = "runtime_transaction"

    def _close_runtime_transaction(*, probe_versions: bool) -> None:
        """Revalidate and close an arm-owned transaction exactly once."""
        nonlocal runtime_transaction_closed, runtime_observation
        if runtime_transaction is None or runtime_transaction_closed:
            return
        from . import dry_run, runtime_manifest

        def _deactivate() -> None:
            """Close an owned transaction even when revalidation has drifted."""
            nonlocal runtime_transaction_closed
            try:
                if runtime_transaction_owned:
                    runtime_transaction.close(probe_versions=probe_versions)
            finally:
                if runtime_transaction_owned and runtime_token is not None:
                    dry_run.ACTIVE_RUNTIME.reset(runtime_token)
                runtime_transaction_closed = True

        pre_run = deepcopy(dict(runtime_observation or {}))
        try:
            runtime_test_only = bool((runtime_observation or {}).get("test_only", False))
            checked = runtime_transaction.revalidate(probe_versions=probe_versions)
            runtime_observation = {
                **dict(runtime_observation or {}),
                "schema": "apg.h-runtime-observation/v1",
                "status": "valid",
                "manifest_sha256": runtime_manifest.manifest_digest(checked),
                "lifecycle": checked["lifecycle"],
                "pre_run": (runtime_observation or {}).get("pre_run", "valid"),
                "post_run": "valid",
                "test_only": False,
                "transaction": {
                    "schema": "apg.h-runtime-transaction/v1",
                    "status": "owned" if runtime_transaction_owned else "borrowed",
                    "begin": "valid",
                    "revalidate": "valid",
                    "close": "valid" if runtime_transaction_owned else "delegated",
                    "manifest_sha256": runtime_manifest.manifest_digest(checked),
                },
            }
            runtime_observation["test_only"] = runtime_test_only
        except BaseException as error:
            # Close is still mandatory after a failed post-run revalidation.
            # runtime_execution.close() deactivates its owner in a finally block;
            # this local wrapper also releases the ContextVar token even when the
            # second check reports the same drift.
            close = "closed" if runtime_transaction_owned else "delegated"
            try:
                _deactivate()
            except BaseException:
                close = "failed"
            _record_failed_close(pre_run, error, close=close)
            raise
        try:
            _deactivate()
        except BaseException as error:
            _record_failed_close(pre_run, error, close="failed", revalidate="valid")
            raise
        result["runtime_revalidation"] = runtime_observation
        postrun_checks["runtime_close"] = {
            "status": "valid", "revalidate": "valid",
            "close": "valid" if runtime_transaction_owned else "delegated",
        }

    def _record_failed_close(previous: Any, error: BaseException, *, close: str,
                             revalidate: str = "failed") -> None:
        """Make a failed post-run runtime check visible instead of pre-run-valid."""
        record = _failed_runtime_revalidation(
            previous, error, owned=runtime_transaction_owned, close=close, runtime_inputs=runtime_inputs,
        )
        if isinstance(record.get("transaction"), dict):
            record["transaction"]["revalidate"] = revalidate
        result["runtime_revalidation"] = record
        postrun_checks["runtime_close"] = {
            "status": "failed", "revalidate": revalidate, "close": close,
            "failure_detail": record.get("failure_detail"),
        }

    try:
        if runtime_inputs is not None:
            runtime_transaction, runtime_token, runtime_transaction_owned = _acquire_runtime_transaction(
                runtime_inputs, work_dir=run,
            )
        if construction is not None:
            step = "source_context"
            source_context = _source_context_inputs(
                source_root=source_root,
                subject=subject,
                run=run,
                scenario=scenario,
                route=selected,
                mode=mode,
                runtime_inputs=runtime_inputs,
            )
        step = "provider_argv"
        read_only = scenario.get("task_input", {}).get("task_authority") == "read_only"
        endpoint = provider.Endpoint(selected["provider"], selected["profile"])
        provider_paths = {
            key: value
            for key, value in (executable_paths or {}).items()
            if key in {"codex_executable", "claude_launcher", "antigravity_launcher"}
        }
        argv = provider.build_argv(
            endpoint,
            "reviewer" if read_only else "producer",
            source_root,
            read_only=read_only,
            pin_profile=selected["execution"] == "live",
            **provider_paths,
        )
        if selected["provider"] == "codex":
            if source_context is not None:
                suffix = source_context.get("argv_suffix")
                if suffix is not None:
                    argv[-1:-1] = list(suffix)
            else:
                from agent_source_guidance import codex_guidance_overrides
                additions = [
                    part
                    for value in codex_guidance_overrides(source_root, workers=False)
                    for part in ("-c", value)
                ]
                argv[-1:-1] = additions
        if source_context is not None:
            if capture is not None or planner is not None or projection is not None:
                raise ValueError("source-owned construction rejects caller context injection")
            selected_capture = deepcopy(dict(source_context["capture"]))
            planner = source_context["planner"]
            projection = source_context["projection"]
            if scenario["scenario_id"] == "scenario-15" and projection is not None:
                argv.extend([
                    "--settings", str(projection.run_dir / "selected/isolated-claude-settings.json"),
                    "--setting-sources", "", "--add-dir", str(projection.run_dir / "selected"),
                ])
            source_instruction_records = deepcopy(list(source_context["instruction_records"]))
        else:
            selected_capture = dict(capture or {})
            source_instruction_records = []
        selected_capture.setdefault("settings", {"mode": mode})
        selected_capture.setdefault("provenance", [])
        selected_capture.setdefault("overrides", [])
        selected_capture.setdefault("apgr_home", str(run))
        selected_capture.setdefault("project_root", str(subject))
        selected_capture["settings"] = {**selected_capture["settings"], "mode": mode}
        from .execution_evidence import contract_identity
        response_identity = contract_identity(scenario)
        instruction_records = source_instruction_records
        if response_identity["required"]:
            instruction_records.append({"id": "evaluation-response-contract", **response_identity})
        step = "context_prepare"
        argv, payload, prepared = context_adapter.prepare(
            capture=selected_capture,
            run_dir=run,
            prefix="attempt",
            run_id=mode,
            binding_id=selected["binding_id"],
            attempt_id="one",
            roles=selected["roles"],
            consumer=selected["provider"],
            argv=argv,
            prompt=prompt + static_context if mode == "static" else prompt,
            projection=projection,
            planner=planner,
            instruction_records=instruction_records,
        )
        if not prepared.get("reference") or prepared.get("record") is None:
            raise ValueError("context plan was not retained")
        prepared["evaluation_transport"] = True
        step = "observation_begin"
        observation_state = _begin_observation(
            run, scenario, mode, argv, selected["provider"], runtime_inputs,
        )
        native_reads = None
        if selected["execution"] == "live" and selected["provider"] == "claude":
            from . import claude_reads
            step = "native_read_prepare"
            argv = claude_reads.prepare(
                prepared, argv, qualification=(admission or {}).get("native_read_qualification"),
            )
        step = "provider_stdin"
        _write_bytes(run / "provider.stdin", payload)
        result["prepared"] = {"reference": prepared["reference"], "record": prepared["record"]}
        result["provider_invocations"] = 1
        step = "provider_environment"
        if selected["execution"] == "live":
            provider_environment = _manifest_environment(runtime_inputs, cwd=subject)
            if runtime_bindings is None:
                raise ValueError("live provider runtime binding is unavailable")
            runtime_bindings["environment"] = {
                **dict(runtime_bindings.get("environment", {})),
                "identity": _git_environment_identity(provider_environment, source="runtime-manifest"),
            }
            selected["runtime_bindings"] = deepcopy(runtime_bindings)
            runner = _bound_provider_runner(provider_environment)
        else:
            runner = runner or provider.run
        invoker = invoker or context_adapter.invoke
        step = "provider_invoke"
        returned = _normalize_returned(
            invoker(
                prepared,
                runner,
                argv,
                payload,
                subject,
                liveness_policy=liveness_policy,
            )
        )
        # Retain the returned streams before any independent post-run check
        # can refuse; a settings or runtime refusal must not hide them.
        step = "provider_return_retain"
        provider_return, retained_terminal = _retain_provider_return(run, returned)
        postrun_checks["provider_return"] = provider_return
        if retained_terminal is not None:
            result["provider_terminal"] = retained_terminal
        step = "observation_finish"
        if observation_state is not None:
            observed: dict[str, Any] = {}
            try:
                result.update(_finish_observation(observation_state, drift=observed))
            except BaseException as error:
                postrun_checks["observation"] = {
                    **observed, "status": observed.get("status", "error"),
                    "failure_detail": _failure_detail(error, step),
                }
                raise
            postrun_checks["observation"] = observed
            # Preserve the historical aliases for readers that only understand
            # the earlier activity vocabulary; typed receipts are canonical.
            result["settings_identity"] = deepcopy(result["settings_receipt"])
            result["discovery_identity"] = deepcopy(result["discovery_receipt"])
        else:
            postrun_checks["observation"] = {"status": "not_applicable"}
        step = "provider_terminal"
        if provider_return["status"] != "retained" or retained_terminal is None:
            raise ValueError("provider return was not fully retained")
        terminal = retained_terminal
        if terminal["exit_code"] != 0 or terminal["truncated"]:
            raise ValueError("provider transport did not complete")
        terminal_bytes = returned.stdout
        if prepared.get("claude_read_stream"):
            native_reads = claude_reads.collect(prepared, returned)
            native_events = deepcopy(native_reads.get("events", []))
            prelaunch_entries = []
            for captured in (prepared.get("claude_read_capture") or {}).values():
                entry = captured.get("entry") if isinstance(captured, Mapping) else None
                if isinstance(entry, Mapping) and dict(entry) not in prelaunch_entries:
                    prelaunch_entries.append(dict(entry))
            postrun_entries = []
            for event in native_events:
                entry = event.get("recovery_entry") if isinstance(event, Mapping) else None
                if isinstance(entry, Mapping) and dict(entry) not in postrun_entries:
                    postrun_entries.append(dict(entry))
            result["native_reads"] = {
                "schema": native_reads["schema"],
                "raw_stream": native_reads["raw_stream"],
                "read_count": len(native_reads["reads"]),
                "coverage": native_reads.get("coverage"),
                "scope": deepcopy(native_reads.get("scope")),
                "session_id": native_reads.get("session_id"),
                "reads": deepcopy(native_reads.get("reads", [])),
                "terminal": deepcopy(native_reads.get("terminal")),
                "events": native_events,
                # claude_reads.collect() has already compared every authorized
                # source snapshot before and after the provider stream.  Keep
                # that source-owned proof beside the events so exact recovery
                # cannot be reconstructed from Read coverage alone.
                "recovery_authority": {
                    "schema": "apg.h-recovery-authority/v1",
                    "scope": deepcopy(native_reads.get("scope")),
                    "session_id": native_reads.get("session_id"),
                    "prelaunch": {"status": "captured", "entries": prelaunch_entries},
                    "postrun": {"status": "verified", "entries": postrun_entries},
                },
            }
            # collect binds returned.stdout to the durable raw stream receipt.
            # The model-authored result is opaque task text, never a new wire envelope.
            terminal_bytes = returned.stdout
        step = "provider_import"
        import_fn = importer or importers.importer_for(selected["provider"])
        imported = _call_importer(import_fn, terminal_bytes, selected, terminal)
        if not isinstance(imported, Mapping) or imported.get("schema") != importers.SCHEMA:
            raise ValueError("provider result importer returned an invalid receipt")
        result["provider_import"] = dict(imported)
        if imported.get("parse_status") in ("empty", "malformed"):
            raise ValueError("provider terminal result is not importable")
        step = "delivery_evidence"
        result.update(_delivery_evidence(
            run, mode, selected,
            extra_events=(native_reads or {}).get("events", []) if native_reads else None,
        ))
        step = "runtime_close"
        if selected["execution"] == "live":
            from . import live_admission
            _close_runtime_transaction(probe_versions=True)
            live_admission.verify_current(admission, source_root, runtime_inputs)
        elif runtime_inputs is not None:
            _close_runtime_transaction(probe_versions=False)
        step = "subject_authority"
        after = snapshot_tree(subject)
        after_dirs = snapshot_dirs(subject)
        git_after = _git_authority(
            subject, git_executable, environment=git_environment,
            environment_source=git_environment_source,
        )
        changed = sorted(name for name in before.keys() | after.keys() if before.get(name) != after.get(name))
        changed_dirs = sorted(name for name in before_dirs.keys() | after_dirs.keys()
                              if before_dirs.get(name) != after_dirs.get(name))
        allowed = set(scenario.get("task_input", {}).get("mutation_scope", []))
        git_unchanged = git_before == git_after
        unexpected_dirs = changed_dirs if read_only else [
            name for name in changed_dirs
            if not any(path == name or path.startswith(name + "/") for path in changed)
        ]
        permitted = ((not changed and not changed_dirs and git_unchanged)
                     if read_only else set(changed) <= allowed and not unexpected_dirs)
        result["authority"] = {
            "read_only": read_only,
            "unchanged": not changed,
            "changed_paths": changed,
            "subject_directories_before": before_dirs,
            "subject_directories_after": after_dirs,
            "changed_directories": changed_dirs,
            "unexpected_directories": unexpected_dirs,
            "directories_unchanged": not changed_dirs,
            "git_before": git_before,
            "git_after": git_after,
            "git_unchanged": git_unchanged,
            "permitted": permitted,
        }
        if not permitted:
            raise ValueError("subject authority changed outside permitted scope")
        if result.get("recovery_receipt") is None and result.get("native_reads") is not None:
            result["recovery_receipt"] = {
                "schema": "apg.h-recovery-receipt/v1",
                "status": "complete",
                "mode": "native-read",
                "native_reads": deepcopy(result["native_reads"]),
            }
        arm_evidence: dict[str, Any] = {
            "authority": result["authority"],
            "context_plan": prepared["record"],
            "provider_import": imported,
            "provider_terminal": terminal,
            "native_reads": result.get("native_reads"),
            "coverage": result.get("coverage"),
            "mode": mode,
            "runtime": result.get("runtime_revalidation"),
            "construction": result.get("construction"),
            "settings_receipt": result.get("settings_receipt"),
            "discovery_receipt": result.get("discovery_receipt"),
        }
        if prepared["record"].get("requested_mode") == "adaptive" and prepared["record"].get("effective_mode") == "static":
            arm_evidence["static_fallback_triggered"] = True
        if scenario.get("mcp_prelaunch_status"):
            arm_evidence["mcp_prelaunch_status"] = scenario["mcp_prelaunch_status"]
        from .preregistration import verify_bindings
        frozen_row = next(
            row for row in verify_bindings(source_root)["scenarios"]
            if row["scenario_id"] == scenario["scenario_id"]
        )
        result["source_cohorts"] = deepcopy(dict(frozen_row.get("cohorts", {})))
        step = "evidence_retain"
        from .execution_evidence import retain
        construction_value = result.get("construction")
        receipt_root = retain(
            arm_dir,
            scenario,
            prepared,
            result,
            source_root=source_root,
            source_seal=seal,
            runtime=runtime_inputs,
            source_binding=(construction_value or {}).get("source") if isinstance(construction_value, Mapping) else None,
            subject_factory=(construction_value or {}).get("subject_factory") if isinstance(construction_value, Mapping) else None,
            oracle_owner=(construction_value or {}).get("oracle") if isinstance(construction_value, Mapping) else None,
            task_contract_value=(construction_value or {}).get("task_contract") if isinstance(construction_value, Mapping) else None,
            runtime_revalidation=result.get("runtime_revalidation"),
            recovery_receipt=result.get("recovery_receipt"),
        )
        arm_evidence["receipt_root"] = str(receipt_root)
        step = "task_oracle"
        oracle_value = _call_oracle(
            oracle,
            subject,
            returned,
            scenario,
            before=before,
            arm_evidence=arm_evidence,
            provider_result=imported,
        )
        from .execution_evidence import finalize_oracle_receipt
        command_close = finalize_oracle_receipt(
            arm_dir,
            claimed=result.get("oracle_command_receipt"),
        )
        result["oracle_command_receipt"] = command_close["receipt"]
        result["evidence_owner"] = {
            "path": "oracle-input/identity.json",
            "sha256": command_close["identity_sha256"],
        }
        result["task_oracle"] = _oracle_receipt(
            oracle_value,
            scenario["expected_outcome"]["quality_oracle"],
        )
        _write_json(arm_dir / "task-oracle.json", result["task_oracle"])
        if isinstance(result.get("construction"), Mapping):
            result["task_contract"] = deepcopy(result["construction"].get("task_contract"))
            result["oracle_owner"] = deepcopy(result["construction"].get("oracle"))
            result["importer_owner"] = deepcopy(result["construction"].get("importer"))
        step = "bundle_validation"
        from .execution_evidence import validate_retained_bundle
        try:
            retained = validate_retained_bundle(
                arm_dir,
                result,
                scenario={**dict(scenario), "cohorts": frozen_row.get("cohorts", {})},
                mode=mode,
            )
        except (OSError, TypeError, ValueError) as validation_error:
            # Keep the terminal arm record available for provider-free
            # diagnostics.  read_arm_result() and assembly re-run the full
            # retained-bundle validation before consuming any facts, so this
            # incomplete receipt cannot qualify a package arm.
            result["qualification_eligibility"] = {
                "schema": "apg.h-qualification-eligibility/v1",
                "status": "ineligible",
                "require_live": True,
                "reasons": [f"retained bundle validation failed: {type(validation_error).__name__}"],
            }
            result["exact_recovery"] = False
            result["exact_recovery_evidence"] = {
                "schema": "apg.h-exact-recovery/v1",
                "status": "not_observed",
                "value": False,
                "source": "retained-evidence",
                "reason": "retained bundle validation failed",
            }
        else:
            result["qualification_eligibility"] = retained["qualification_eligibility"]
            result["exact_recovery"] = retained["exact_recovery"]
            result["exact_recovery_evidence"] = retained["exact_recovery_evidence"]
        result["status"] = "complete"
    except BaseException as error:
        # ``failure`` keeps its historical type-name form; the bounded detail
        # is additive so earlier results without it remain readable.
        result["failure"] = type(error).__name__
        result["failure_detail"] = _failure_detail(error, step)
        if runtime_transaction is not None and not runtime_transaction_closed:
            try:
                _close_runtime_transaction(probe_versions=selected["execution"] == "live")
            except Exception:  # noqa: BLE001
                # Preserve the provider/arm failure as the terminal result.
                # The failed close replaced the pre-run runtime receipt and is
                # recorded in postrun_checks.runtime_close.
                pass
        if returned is not None and "provider_terminal" not in result:
            try:
                result["provider_terminal"] = _terminal(returned)
            except (TypeError, ValueError):
                pass
        try:
            after = snapshot_tree(subject)
            after_dirs = snapshot_dirs(subject)
            changed = sorted(name for name in before.keys() | after.keys() if before.get(name) != after.get(name))
            changed_dirs = sorted(name for name in before_dirs.keys() | after_dirs.keys()
                                  if before_dirs.get(name) != after_dirs.get(name))
            result["authority"] = {
                "read_only": scenario.get("task_input", {}).get("task_authority") == "read_only",
                "unchanged": before == after,
                # Subject-relative names only; permission is not assessed on
                # a failed arm and these observations name no actor.
                "changed_paths": changed[:_MAX_DELTA_ROWS],
                "changed_paths_omitted": max(0, len(changed) - _MAX_DELTA_ROWS),
                "changed_directories": changed_dirs[:_MAX_DELTA_ROWS],
                "changed_directories_omitted": max(0, len(changed_dirs) - _MAX_DELTA_ROWS),
                "assessment": "not_evaluated",
            }
        except Exception:  # noqa: BLE001 - the terminal result must still be retained
            result["authority"] = {"read_only": None, "unchanged": None, "git_unchanged": None}
        _write_json(run / "terminal.json", result)
        _finish(arm_dir, result)
        if isinstance(error, (KeyboardInterrupt, SystemExit)):
            raise
        return result
    _write_json(run / "terminal.json", result)
    return _finish(arm_dir, result)


def construct_arm(
    *,
    arm_dir: str | Path,
    source_root: str | Path,
    scenario_id: str,
    mode: str,
    execution: str = "instrumented",
    executable_paths: Mapping[str, str] | None = None,
    fake_runner: Callable[..., Any] | None = None,
    test_oracle: Any = None,
    source_seal: Mapping[str, Any] | None = None,
    runtime_inputs: Mapping[str, Any] | None = None,
    live_authorization: Mapping[str, Any] | None = None,
    liveness_policy: Any = None,
    recovery_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Construct one arm exclusively from frozen source-owned identities.

    Instrumented execution is an explicit test seam: it requires a supplied
    fake runner or an explicitly bound fake executable and records any
    test-only oracle override as such.  Live construction derives the frozen
    subject, task contract, oracle, importer, route and executable paths and
    refuses caller-owned substitutes.  ``live_authorization`` must contain only
    ``decision_path`` and ``grant_path`` for external manager records; the arm
    is admitted and consumed by ``live_admission`` before it exists.
    """
    source_root = Path(source_root)
    arm_dir = Path(arm_dir)
    if source_root.resolve() != source_root or arm_dir.resolve() != arm_dir:
        raise ValueError("arm and source roots must be physical")
    if execution not in ("instrumented", "live"):
        raise ValueError("unsupported arm execution mode")
    scenario, _row, frozen_route, source_identity = _frozen_inputs(source_root, scenario_id, mode)
    subject_files, subject_modes, subject_factory = _frozen_subject(source_root, scenario_id)
    from .execution_evidence import task_contract
    contract = task_contract(scenario, source_binding=source_identity)
    oracle_identity = _oracle_identity(scenario, source_identity)
    importer_identity = _importer_identity(frozen_route)
    runtime_value, runtime_observation = _runtime_observation(runtime_inputs, live=execution == "live")

    route = deepcopy(frozen_route)
    route["execution"] = execution
    route["source_identity"] = source_identity
    route["subject_factory_identity"] = subject_factory
    route["construction_identity"] = source_identity["route_sha256"]
    construction = _construction_record(
        scenario, frozen_route, source_identity, subject_factory, contract,
        oracle_identity, importer_identity, runtime_observation, execution,
    )
    if execution == "instrumented":
        provider_key = {
            "codex": "codex_executable",
            "claude": "claude_launcher",
            "antigravity": "antigravity_launcher",
        }[frozen_route["provider"]]
        if fake_runner is None and (not executable_paths or not executable_paths.get(provider_key)):
            raise ValueError("instrumented arm requires an explicit fake runner or executable")
        oracle = test_oracle
        if oracle is None:
            from . import oracles
            oracle = oracles.oracle_for(scenario)
        if test_oracle is not None:
            oracle_identity = {
                **oracle_identity,
                "owner": "test-only",
                "status": "instrumented-fixture",
            }
            construction["oracle"] = oracle_identity
    else:
        if test_oracle is not None or fake_runner is not None:
            raise ValueError("live arm cannot use instrumented oracle or runner")
        oracle = None

    return run_one_arm(
        arm_dir=arm_dir,
        source_root=source_root,
        scenario=scenario,
        mode=mode,
        route=route,
        subject_files=subject_files,
        prompt=None,
        static_context=b"",
        executable_paths=executable_paths,
        oracle=oracle,
        projection=None,
        planner=None,
        liveness_policy=liveness_policy,
        capture=None,
        runtime_inputs=runtime_value,
        seal=source_seal,
        live_authorization=live_authorization,
        importer=None,
        runner=fake_runner,
        invoker=None,
        subject_modes=subject_modes,
        construction=construction,
        runtime_observation=runtime_observation,
        recovery_receipt=recovery_receipt,
        _construction_token=_CONSTRUCTION_TOKEN,
    )


def _verified_arm_record(arm_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Verify only the retained arm integrity inventory; run no git or manifest.

    This is the integrity half of ``read_arm_result``.  It is also the reader
    for historical predecessor evidence, whose retained runtime manifest must
    not be re-verified against today's host files.
    """
    arm_dir = Path(arm_dir)
    if arm_dir.resolve() != arm_dir or not arm_dir.is_dir():
        raise ValueError("arm result directory must be physical")
    integrity = load(arm_dir / _INTEGRITY)
    result = load(arm_dir / _RESULT)
    if (
        integrity.get("schema") != "apg.h-arm-integrity/v1"
        or integrity.get("result_sha256") != _sha256(_encoded(result))
    ):
        raise ValueError("arm result identity changed")
    actual = snapshot_tree(arm_dir)
    actual.pop(_INTEGRITY, None)
    if actual != integrity.get("files"):
        raise ValueError("arm evidence changed or lost")
    if "directories" in integrity and snapshot_dirs(arm_dir) != integrity.get("directories"):
        raise ValueError("arm directory topology changed or lost")
    return result, integrity


def read_arm_result(arm_dir: str | Path) -> dict[str, Any]:
    """Read an immutable arm receipt without invoking or preparing a provider."""
    arm_dir = Path(arm_dir)
    result, _integrity = _verified_arm_record(arm_dir)
    authority = result.get("authority") if isinstance(result, Mapping) else None
    expected_git = authority.get("git_after") if isinstance(authority, Mapping) else None
    if not isinstance(expected_git, Mapping):
        expected_git = result.get("git_authority_before") if isinstance(result, Mapping) else None
    if isinstance(expected_git, Mapping) and expected_git.get("executable"):
        subject = arm_dir / "subject"
        git_environment: dict[str, str] | None = None
        environment_source = "test-only-isolated"
        runtime_path = arm_dir / "oracle-input" / "runtime.json"
        if not runtime_path.is_file():
            runtime_path = arm_dir / "runtime-inputs.json"
        if runtime_path.is_file() and not runtime_path.is_symlink():
            try:
                runtime_value = load(runtime_path)
            except (OSError, ValueError):
                runtime_value = None
            if isinstance(runtime_value, Mapping) and runtime_value.get("schema") == "apg.h-runtime-inputs/v2":
                from . import runtime_manifest

                runtime_for_environment = dict(runtime_value)
                runtime_for_environment.pop("revalidation", None)
                runtime_manifest.verify_complete(runtime_for_environment, probe_versions=False)
                git_environment = _manifest_environment(runtime_for_environment, cwd=subject)
                environment_source = "runtime-manifest"
        observed_git = _git_authority(
            subject, str(expected_git["executable"]), environment=git_environment,
            environment_source=environment_source,
        )
        if observed_git != dict(expected_git):
            raise ValueError("arm subject git authority changed")
    if result.get("status") == "complete":
        from .execution_evidence import validate_retained_bundle
        retained = validate_retained_bundle(arm_dir, result)
        # Rehydrate derived facts from the immutable receipt bundle after the
        # integrity checks.  Callers cannot turn copied result fields into
        # completion, recovery, or qualification evidence.
        result["qualification_eligibility"] = retained["qualification_eligibility"]
        result["exact_recovery"] = retained["exact_recovery"]
        result["exact_recovery_evidence"] = retained["exact_recovery_evidence"]
        result["authority"] = retained["authority"]
    return result


_RUNTIME_POST_RUN = {"valid": "verified_at_run", "failed": "failed_at_run"}


def read_arm_diagnostic(arm_dir: str | Path, *, observe_current_runtime: bool = True) -> dict[str, Any]:
    """Explain a retained FAILED arm; never qualify, promote or re-run it.

    Integrity comes only from ``_verified_arm_record``: changed or lost bytes,
    modes, directories or result identity refuse.  Only an incomplete arm with
    a recorded failure and no success claim is accepted.  No git, provider,
    version probe or other process runs, and the strict ``read_arm_result``
    checks are neither performed nor relaxed.  Missing original evidence is
    disclosed.  ``current_runtime`` compares today's host identities with the
    retained manifest; it is not the historical post-run state.
    """
    arm_dir = Path(arm_dir)
    result, integrity = _verified_arm_record(arm_dir)
    if not isinstance(result, Mapping) or result.get("schema") != SCHEMA:
        raise ValueError("arm result schema is invalid")
    if result.get("status") != "incomplete":
        raise ValueError("diagnostic readback is limited to incomplete arms")
    if not isinstance(result.get("failure"), str) or not result["failure"]:
        raise ValueError("incomplete arm records no failure")
    eligibility = result.get("qualification_eligibility")
    if (isinstance(eligibility, Mapping) and eligibility.get("status") == "eligible") or result.get("exact_recovery") is True:
        raise ValueError("incomplete arm claims qualification")
    files = integrity.get("files") if isinstance(integrity.get("files"), Mapping) else {}
    terminal = result.get("provider_terminal") if isinstance(result.get("provider_terminal"), Mapping) else None
    missing: list[str] = []
    streams: dict[str, Any] = {}
    for name in ("stdout", "stderr"):
        relative = f"run/provider.{name}"
        expected = terminal.get(name) if terminal is not None else None
        observed = files.get(relative)
        if observed is None:
            if isinstance(expected, Mapping):
                streams[name] = {"status": "absent_original_not_retained",
                                 "expected": {"bytes": expected.get("bytes"), "sha256": expected.get("sha256")}}
                missing.append(f"{relative}: original bytes were not retained; a digest cannot reconstruct them")
            else:
                streams[name] = {"status": "not_returned"}
            continue
        row = {"path": relative, "bytes": observed["bytes"], "sha256": observed["sha256"], "mode": observed["mode"]}
        if not isinstance(expected, Mapping):
            streams[name] = {**row, "status": "retained_without_terminal"}
        elif (observed["bytes"], observed["sha256"]) == (expected.get("bytes"), expected.get("sha256")):
            streams[name] = {**row, "status": "retained", "matches_terminal": True}
        else:
            streams[name] = {**row, "status": "mismatch", "matches_terminal": False,
                             "expected": {"bytes": expected.get("bytes"), "sha256": expected.get("sha256")}}
    postrun = result.get("postrun_checks")
    if not isinstance(postrun, Mapping):
        missing.append("postrun_checks: not_recorded; this result predates apg.h-arm-postrun/v1")
    runtime = result.get("runtime_revalidation") if isinstance(result.get("runtime_revalidation"), Mapping) else None
    runtime_post_run = _RUNTIME_POST_RUN.get((runtime or {}).get("post_run"), "unverified")
    if runtime is not None and runtime_post_run == "unverified":
        missing.append("runtime_revalidation: post-run check not recorded; its status reflects the pre-run observation only")
    if not observe_current_runtime:
        current: dict[str, Any] = {"status": "not_observed", "reason": "caller did not request a current host observation"}
    elif "runtime-inputs.json" not in files:
        current = {"status": "not_observed", "reason": "no integrity-covered runtime manifest is retained"}
    else:
        from . import runtime_manifest
        try:
            report = runtime_manifest.drift_report(load(arm_dir / "runtime-inputs.json"))
        except (OSError, ValueError) as error:
            current = {"status": "unavailable", "type": type(error).__name__}
        else:
            current = {"status": "observed", "report": report,
                       "scope": "current host identities versus the retained manifest; "
                                "not the historical post-run state and not an actor attribution"}
    return {
        "schema": DIAGNOSTIC_SCHEMA,
        "qualification": {"status": "not_qualification", "eligible": False, "aggregation": "excluded"},
        "result_is_current": False,
        "strict_readback": "not_performed_by_diagnostic_reader",
        "integrity": {"status": "verified", "result_sha256": integrity.get("result_sha256"), "files": len(files)},
        "outcome": {
            key: deepcopy(result.get(key))
            for key in ("scenario_id", "mode", "status", "failure", "failure_detail", "provider_invocations",
                        "retries", "restarts", "provider_terminal", "authority", "live_admission")
        },
        "invocation_semantics": INVOCATION_SEMANTICS,
        "postrun_checks": deepcopy(postrun) if isinstance(postrun, Mapping) else None,
        "runtime_revalidation": deepcopy(runtime),
        "runtime_post_run": runtime_post_run,
        "raw_streams": streams,
        "missing_evidence": missing,
        "current_runtime": current,
    }


# Naming aliases keep the owner discoverable to controllers without creating
# multiple execution implementations.
execute_arm = run_one_arm
run_arm = run_one_arm
read_arm = read_arm_result


__all__ = [
    "SCHEMA",
    "construct_arm",
    "execute_arm",
    "read_arm",
    "read_arm_diagnostic",
    "read_arm_result",
    "run_arm",
    "run_one_arm",
    "snapshot_dirs",
    "snapshot_tree",
]
