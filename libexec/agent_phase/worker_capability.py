"""Worker capability resolution and subsystem qualification.

The shared worker facility is an enhancement to the local dispatcher.  The
dispatcher must remain importable when that facility is absent or damaged, so
this module deliberately has no import-time dependency on ``apgr_workers``.
Only a worker-capable execution-mode request for a
potentially eligible parent reaches the optional import boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any

from .request import WORKER_CAPABLE_MODES


_OPTIONAL_POLICY_MODULE = "apgr_workers.policy"
_OPTIONAL_POLICY_API = "resolve_worker_capability"
_PARENT_PROVIDERS = frozenset({"claude", "codex", "antigravity"})
_WORKER_EXECUTABLE = Path("bin/agent-worker")
_PARENT_FAMILIES = frozenset({"claude_fable", "claude_opus", "codex_parent", "gemini_flash"})
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

DYNAMIC_MODE = "dynamic"
MANDATORY_WORKER_MODES = frozenset(
    {"gemini_sub", DYNAMIC_MODE}
)
ALL_WORKER_CAPABLE_MODES = WORKER_CAPABLE_MODES | {DYNAMIC_MODE}


@dataclass(frozen=True)
class WorkerQualificationResult:
    eligible: bool
    reason: str | None = None
    capability: dict[str, Any] | None = None

    def __bool__(self) -> bool:
        return self.eligible

    def __iter__(self):
        return iter((self.eligible, self.reason, self.capability))


def _unavailable(reason: str, *, requirement: str | None = None) -> dict[str, Any]:
    cap: dict[str, Any] = {
        "mode": "shared-local-worker",
        "available": False,
        "allowed": False,
        "reason": reason,
    }
    if requirement is not None:
        cap["requirement"] = requirement
    return cap


def _error_detail(error: Exception) -> str:
    """Keep optional-boundary diagnostics useful without preserving newlines."""
    detail = str(error).replace("\n", " ").strip()
    return detail[:240] if detail else "no diagnostic detail"


def _executable_error(root: Path, relative_path: Path = _WORKER_EXECUTABLE) -> str | None:
    path = root / relative_path
    try:
        value = path.stat()
    except OSError as error:
        return (
            "optional worker executable unavailable "
            f"({type(error).__name__}: {_error_detail(error)})"
        )
    if not stat.S_ISREG(value.st_mode):
        return "optional worker executable unavailable (not a regular file)"
    if not os.access(path, os.X_OK):
        return "optional worker executable unavailable (not executable)"
    return None


def expected_parent_family_for_endpoint(
    provider: str,
    profile: str,
    root: Path | None = None,
    *,
    bundle: Any = None,
) -> str | None:
    """Derive expected parent family from runtime_models.selection, not substring in profile name."""
    repo_root = Path(root).resolve() if root is not None else Path.cwd().resolve()
    from .runtime_models import parent_family_for_endpoint
    return parent_family_for_endpoint(repo_root, provider, profile, bundle=bundle)


def check_subsystem_origin(root: Path) -> tuple[bool, str | None]:
    """Inspect actual subsystem origin in candidate libexec/apgr_workers."""
    candidate_root = Path(root).resolve()
    candidate_workers = candidate_root / "libexec" / "apgr_workers"
    if not candidate_workers.is_dir():
        return False, f"worker subsystem origin unavailable: {candidate_workers} not found or not a directory"

    # Verify origin of imported apgr_workers if loaded in sys.modules
    mod = sys.modules.get("apgr_workers")
    if mod is not None:
        mod_file = getattr(mod, "__file__", None)
        if not mod_file:
            return False, "worker subsystem origin mismatch: loaded apgr_workers has no __file__"
        mod_path = Path(mod_file).resolve()
        try:
            mod_path.relative_to(candidate_workers.resolve())
        except ValueError:
            return False, f"worker subsystem origin mismatch: loaded from {mod_path}, expected {candidate_workers}"
    return True, None


def check_worker_binaries(root: Path, provider: str) -> tuple[bool, str | None]:
    import shutil

    candidate_root = Path(root).resolve()
    worker_exe = (candidate_root / "bin" / "agent-worker").resolve()
    if not worker_exe.is_relative_to(candidate_root):
        return False, "worker entrypoint escapes the candidate root"
    if not worker_exe.is_file():
        return False, f"worker executable unavailable at {worker_exe}"
    if not os.access(worker_exe, os.X_OK):
        return False, f"worker executable not executable at {worker_exe}"

    if provider == "claude":
        facade_exe = (candidate_root / "bin" / "agent-worker-mcp").resolve()
        if not facade_exe.is_file():
            return False, f"worker facade unavailable at {facade_exe}"
        if not os.access(facade_exe, os.X_OK):
            return False, f"worker facade not executable at {facade_exe}"
    elif provider == "codex":
        codex_bin = shutil.which("codex")
        if not codex_bin:
            return False, "worker executable codex not found on PATH via shutil.which"
        try:
            import apgr_workers.native_launch as nl
            if not callable(getattr(nl, "prepare_native_binding", None)) or not callable(getattr(nl, "apply_native_binding", None)):
                return False, "codex native launch binding missing required interface"
        except Exception as err:
            return False, f"codex native launch binding unavailable ({err})"
    elif provider == "antigravity":
        agy_bin = shutil.which("agy") or shutil.which("antigravity")
        if not agy_bin:
            return False, "worker executable agy not found on PATH via shutil.which"
        try:
            import apgr_workers.gemini_parent as gp
            if not callable(getattr(gp, "capability_error", None)):
                return False, "antigravity gemini parent binding missing required interface"
        except Exception as err:
            return False, f"antigravity gemini parent binding unavailable ({err})"
    return True, None


def _validate_allowed_capability(
    capability: dict[str, Any],
    provider: str | None = None,
    profile: str | None = None,
    execution_mode: str | None = None,
    *,
    root: Path | None = None,
    bundle: Any = None,
) -> str | None:
    """Check fields consumed by the dispatcher before advertising a worker."""
    if capability.get("available") is not True:
        return "optional worker policy returned an inconsistent capability"
    parent_family = capability.get("parent_family")
    if parent_family not in _PARENT_FAMILIES:
        return "optional worker policy returned an invalid parent family"
    if provider is not None and profile is not None:
        expected_family = expected_parent_family_for_endpoint(
            provider, profile, root=root, bundle=bundle
        )
        if expected_family is None or parent_family != expected_family:
            return f"parent family {parent_family} does not match model/profile {provider}/{profile}"

    limits = capability.get("limits")
    if not isinstance(limits, dict):
        return "optional worker policy capability lacks limits"

    policy_selection = capability.get("policy_selection")
    # Fresh fixed-pool capabilities are distinct from retained two-pool evidence.
    if execution_mode == DYNAMIC_MODE or policy_selection is not None:
        if policy_selection != "triple_pool_4x4x4":
            return "fresh worker admission requires triple_pool_4x4x4; resume historical runs under their pinned generation"
        if any(type(limits.get("max_" + kind)) is not int or limits["max_" + kind] != 4
               for kind in ("gemini", "luna", "sonnet")):
            return "triple_pool_4x4x4 requires exactly 4 workers in each independent pool"
        if (capability.get("borrowing") is not False
                or capability.get("allow_borrowing") is True
                or limits.get("allow_borrowing") is True):
            return "triple_pool_4x4x4 forbids capacity borrowing"
        if capability.get("leaf_only") is not True or capability.get("parent_authority") is not True:
            return "triple_pool_4x4x4 requires leaf-only parent-bounded task authority"
        expected_transports = {
            "codex_parent": ("codex_native", "claude_external"),
            "claude_opus": ("codex_external", "claude_native"),
            "claude_fable": ("codex_external", "claude_native"),
            "gemini_flash": ("codex_external", "claude_external"),
        }
        for kind, transport in zip(("luna", "sonnet"), expected_transports[parent_family]):
            worker = capability.get(kind + "_worker", {})
            if worker.get("transport") != transport or worker.get("maximum_concurrency") != 4:
                return f"invalid {kind} transport or capacity for {parent_family}"
        sonnet = capability["sonnet_worker"]
        if sonnet.get("model") != "claude-sonnet-5-5" or sonnet.get("effort") != "high":
            return "Sonnet worker identity must be claude-sonnet-5-5/high"
    else:
        for name in ("max_gemini", "max_aggregate"):
            value = limits.get(name)
            if type(value) is not int or value <= 0:
                return f"optional worker policy capability has invalid {name} limit"

    gemini_worker = capability.get("gemini_worker")
    if not isinstance(gemini_worker, dict):
        return "optional worker policy capability lacks Gemini worker details"
    if not isinstance(gemini_worker.get("profile"), str) or not gemini_worker["profile"]:
        return "optional worker policy capability lacks a Gemini worker profile"
    if not isinstance(capability.get("policy_source"), str) or not capability["policy_source"]:
        return "optional worker policy capability lacks policy provenance"
    policy_sha256 = capability.get("policy_sha256")
    if not isinstance(policy_sha256, str) or _SHA256.fullmatch(policy_sha256) is None:
        return "optional worker policy capability has invalid policy provenance"
    return None


def resolve_worker_capability(
    root: Path,
    provider: str,
    profile: str,
    execution_mode: str,
    *,
    bundle: Any = None,
    snapshot: Any = None,
) -> dict[str, Any] | None:
    """Resolve an optional worker capability integrating canonical bundle worker policy."""
    is_mandatory = execution_mode in MANDATORY_WORKER_MODES or execution_mode == DYNAMIC_MODE
    req_field = "required" if is_mandatory else "optional"

    if execution_mode not in ALL_WORKER_CAPABLE_MODES or provider not in _PARENT_PROVIDERS:
        if is_mandatory:
            return _unavailable(
                f"mandatory worker capability unavailable for {provider}/{profile} in {execution_mode}",
                requirement=req_field,
            )
        return None
    if provider == "antigravity" and execution_mode not in (
        "gemini_sub",
        "gemini_flash_sub",
        "gemini_flash_opus_sub",
        DYNAMIC_MODE,
    ):
        if is_mandatory:
            return _unavailable(
                f"mandatory worker capability unavailable for {provider}/{profile} in {execution_mode}",
                requirement=req_field,
            )
        return None

    repository_root = Path(root).resolve()
    cand_workers = repository_root / "libexec" / "apgr_workers"
    if cand_workers.is_dir() and str(repository_root / "libexec") not in sys.path:
        sys.path.insert(0, str(repository_root / "libexec"))

    effective_bundle = snapshot if snapshot is not None else bundle
    from . import runtime_models
    from contextlib import nullcontext

    capture_ctx = runtime_models.captured(effective_bundle) if effective_bundle is not None else nullcontext()
    with capture_ctx:
        origin_ok, origin_err = check_subsystem_origin(repository_root)
        if not origin_ok:
            return _unavailable(
                f"worker subsystem origin unavailable: {origin_err}",
                requirement=req_field,
            )

        bin_ok, bin_err = check_worker_binaries(repository_root, provider)
        if not bin_ok:
            return _unavailable(f"worker executable unavailable: {bin_err}", requirement=req_field)

        parent_family = expected_parent_family_for_endpoint(
            provider, profile, root=repository_root, bundle=effective_bundle
        )
        if parent_family is None:
            return _unavailable(
                f"endpoint {provider}/{profile} does not map to a recognized parent family",
                requirement=req_field,
            )

        try:
            b = effective_bundle or runtime_models.current_bundle(repository_root)
            wp = getattr(b, "worker_policy", None)
            workers_member = b.members.get("workers.toml") if hasattr(b, "members") else None
            if wp is None or workers_member is None:
                return _unavailable(
                    "canonical worker policy or workers.toml missing from bundle",
                    requirement=req_field,
                )
        except Exception as err:
            return _unavailable(
                f"failed to load canonical worker policy from bundle: {err}",
                requirement=req_field,
            )

        if execution_mode == DYNAMIC_MODE:
            if wp.name != "triple_pool_4x4x4":
                return _unavailable(
                    "dynamic mode requires triple_pool_4x4x4 worker policy",
                    requirement=req_field,
                )
            if hasattr(wp, "mode_requirements") and execution_mode not in wp.mode_requirements:
                return _unavailable(
                    f"mode {execution_mode} not permitted by worker policy mode_requirements",
                    requirement=req_field,
                )

        import tomllib
        try:
            from apgr_workers.policy import selected_capability, resolve_worker_capability as policy_resolve
            if execution_mode in {"gemini_sub", "dynamic", "gemini_flash_sub", "gemini_flash_opus_sub"}:
                capability = selected_capability(
                    repository_root, parent_family, tomllib.loads(workers_member.raw.decode()),
                    str(workers_member.path), workers_member.sha256, wp.name)
            else:
                capability = policy_resolve(repository_root, provider, profile, execution_mode)
                if capability is None:
                    return _unavailable("worker policy does not support this endpoint", requirement=req_field)
            capability["requirement"] = req_field
            if parent_family == "gemini_flash":
                selected = runtime_models.selection(repository_root, provider, profile)
                capability.update(execution_mode=execution_mode, parent_provider=provider,
                                  parent_profile=profile, parent_model=selected["model"],
                                  parent_effort=selected["effort"], source_root=str(repository_root))
        except Exception as error:
            return _unavailable(f"worker model/policy resolution failed: {_error_detail(error)}", requirement=req_field)

        if provider == "claude":
            facade_error = _executable_error(repository_root, Path("bin/agent-worker-mcp"))
            if facade_error is not None:
                return _unavailable("optional worker facade unavailable: " + facade_error, requirement=req_field)
            capability["interface"] = "stdio-mcp"
        elif provider == "antigravity":
            capability["interface"] = "cli"
            if execution_mode in ("gemini_flash_sub", "gemini_flash_opus_sub"):
                try:
                    from apgr_workers.gemini_parent import capability_error
                    val_err = capability_error(capability)
                    if val_err is not None:
                        return _unavailable(val_err, requirement=req_field)
                except Exception as err:
                    return _unavailable(f"Gemini worker capability validation unavailable ({type(err).__name__})", requirement=req_field)
        elif provider == "codex":
            capability["interface"] = "native"

        val_err = _validate_allowed_capability(
            capability,
            provider=provider,
            profile=profile,
            execution_mode=execution_mode,
            root=repository_root,
            bundle=effective_bundle,
        )
        if val_err is not None:
            return _unavailable(val_err, requirement=req_field)

        exe_err = _executable_error(repository_root)
        if exe_err is not None:
            return _unavailable(exe_err, requirement=req_field)

        return capability


def qualify_worker_eligibility(
    endpoint: Any,
    *,
    root: Path | None = None,
    execution_mode: str = "dynamic",
    candidate_workers_dir: Path | None = None,
    bundle: Any = None,
    snapshot: Any = None,
) -> WorkerQualificationResult:
    """Comprehensive qualifier for worker subsystem eligibility."""
    if hasattr(endpoint, "provider"):
        provider = endpoint.provider
        profile = endpoint.profile
    elif isinstance(endpoint, dict):
        provider = endpoint.get("provider", "")
        profile = endpoint.get("profile", "")
    else:
        return WorkerQualificationResult(False, "worker_unavailable: invalid endpoint")

    repo_root = Path(root).resolve() if root is not None else Path.cwd().resolve()
    effective_bundle = snapshot if snapshot is not None else bundle

    from . import runtime_models
    from contextlib import nullcontext
    capture_ctx = runtime_models.captured(effective_bundle) if effective_bundle is not None else nullcontext()
    with capture_ctx:
        # 1. Subsystem origin check
        origin_ok, origin_err = check_subsystem_origin(repo_root)
        if not origin_ok:
            return WorkerQualificationResult(False, f"worker_unavailable: {origin_err}")

        # 2. Executable / facade / native binding availability
        bin_ok, bin_err = check_worker_binaries(repo_root, provider)
        if not bin_ok:
            return WorkerQualificationResult(False, f"worker_unavailable: {bin_err}")

        # 3. Model-based parent family matching
        exp_family = expected_parent_family_for_endpoint(
            provider, profile, root=repo_root, bundle=effective_bundle
        )
        if exp_family is None:
            return WorkerQualificationResult(
                False,
                f"worker_unavailable: endpoint {provider}/{profile} does not map to a recognized parent family",
            )

        # 4. Capability resolution and policy/capacity check
        cap = resolve_worker_capability(
            repo_root, provider, profile, execution_mode, bundle=effective_bundle
        )
        if cap is None:
            return WorkerQualificationResult(
                False,
                f"worker_unavailable: worker capability resolution returned None for {provider}/{profile}",
            )
        if not cap.get("available") or not cap.get("allowed"):
            reason = cap.get("reason", "not allowed or unavailable")
            return WorkerQualificationResult(
                False,
                f"worker_unavailable: {reason}",
                capability=cap,
            )

        val_err = _validate_allowed_capability(
            cap,
            provider=provider,
            profile=profile,
            execution_mode=execution_mode,
            root=repo_root,
            bundle=effective_bundle,
        )
        if val_err is not None:
            return WorkerQualificationResult(
                False,
                f"worker_unavailable: {val_err}",
                capability=cap,
            )

        return WorkerQualificationResult(True, None, capability=cap)
