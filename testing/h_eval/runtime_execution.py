"""Manifest-bound command execution for provider-free H qualification.

This owner supplies the execution seam used by command-backed oracles and the
APGR planner.  Every executable and every environment value comes from a
sealed v2 runtime manifest.  Provider names are reserved for bounded version
queries; task/model arguments cannot be sent through this owner.
"""
from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import runtime_manifest

NETWORK_VARIABLES = frozenset({
    "ALL_PROXY", "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY",
    "GOPROXY", "GOSUMDB", "GONOSUMDB", "npm_config_offline",
    "npm_config_prefer_offline", "npm_config_registry", "npm_config_proxy",
    "npm_config_http_proxy", "npm_config_https_proxy", "npm_config_noproxy",
    "npm_config_audit", "npm_config_fund", "PIP_NO_INDEX", "PIP_INDEX_URL",
    "PIP_EXTRA_INDEX_URL", "PIP_TRUSTED_HOST", "PIP_FIND_LINKS",
})
EXTRA_ENVIRONMENT_KEYS = frozenset({"GOCACHE", "GOMODCACHE", "npm_config_cache", "PYTHONPATH"})


def _physical_path(path: str | Path) -> Path:
    value = Path(path)
    if (not value.is_absolute() or value.is_symlink() or value.resolve() != value
            or not value.exists() or not (value.is_file() or value.is_dir())):
        raise ValueError("runtime environment path must be a physical file or directory")
    return value


def _physical_directory(path: str | Path) -> Path:
    value = Path(path)
    if not value.is_absolute() or value.resolve() != value or not value.is_dir() or value.is_symlink():
        raise ValueError("runtime command cwd must be a physical directory")
    return value


def _run_owned_path(path: str, roots: Sequence[Path]) -> str:
    """Accept a cache override only inside an existing run-owned root."""
    value = Path(path)
    if not value.is_absolute() or value.is_symlink() or value.resolve() != value:
        raise ValueError("runtime override must be an absolute physical path")
    parent = value.parent
    if not parent.is_dir() or parent.is_symlink() or parent.resolve() != parent:
        raise ValueError("runtime override parent must be a physical directory")
    if not any(value == root or value.is_relative_to(root) for root in roots):
        raise ValueError("runtime override is outside the run-owned roots")
    return str(value)


@dataclass
class RuntimeTransaction:
    """One bounded capture/seal/use/revalidate transaction."""

    manifest: Mapping[str, Any]
    work_dir: str | Path | None = None
    home: str | Path | None = None
    _active: bool = False
    _sealed_digest: str | None = None

    def begin(self) -> RuntimeTransaction:
        if self._active:
            raise ValueError("runtime transaction already active")
        checked = runtime_manifest.revalidate(self.manifest)
        self._sealed_digest = runtime_manifest.manifest_digest(checked)
        if self.work_dir is not None:
            _physical_directory(self.work_dir)
        if self.home is not None:
            _physical_directory(self.home)
        self._active = True
        return self

    def _require_active(self) -> Mapping[str, Any]:
        """Check the sealed in-memory transaction identity without I/O.

        File and executable identity is checked at the explicit transaction
        boundaries.  Resolve/environment calls must not rescan a large bound
        cache or module tree merely to consume an already sealed record.
        """
        if not self._active:
            raise ValueError("runtime transaction is not active")
        if (not isinstance(self.manifest, Mapping)
                or self.manifest.get("schema") != runtime_manifest.COMPLETE_SCHEMA):
            raise ValueError("complete sealed runtime manifest required")
        lifecycle = self.manifest.get("lifecycle")
        if (not isinstance(lifecycle, Mapping) or lifecycle.get("state") != "sealed"
                or lifecycle.get("sealed_sha256") != self._sealed_digest):
            raise ValueError("runtime manifest changed during transaction")
        try:
            current_digest = runtime_manifest.manifest_digest(self.manifest)
        except (TypeError, ValueError):
            raise ValueError("runtime manifest changed during transaction") from None
        if current_digest != self._sealed_digest:
            raise ValueError("runtime manifest changed during transaction")
        return self.manifest

    def revalidate(self, *, probe_versions: bool = False) -> Mapping[str, Any]:
        """Revalidate the sealed inventory at a transaction boundary."""
        self._require_active()
        checked = runtime_manifest.revalidate(self.manifest, probe_versions=probe_versions)
        if runtime_manifest.manifest_digest(checked) != self._sealed_digest:
            raise ValueError("runtime manifest changed during transaction")
        return checked

    def resolve(self, name: str) -> str:
        """Resolve a command/provider only from the manifest's runtime table."""
        checked = self._require_active()
        record = checked["runtimes"].get(name)
        if not isinstance(record, Mapping):
            raise ValueError("runtime name is not bound")  # noqa: TRY004
        executable = record.get("executable")
        entry = checked["files"].get(executable)
        if not isinstance(entry, Mapping) or entry.get("kind") != "file":
            raise ValueError("runtime executable is not bound")
        return str(entry["physical_path"])

    def environment(
        self,
        *,
        cwd: str | Path | None = None,
        temp_root: str | Path | None = None,
        extra: Mapping[str, str] | None = None,
    ) -> dict[str, str]:
        """Build a closed environment with explicit network/cache policy."""
        checked = self._require_active()
        policy = checked["environment"]
        selected_home = self.home or policy.get("home")
        selected_temp = temp_root or policy.get("temp_root")
        if selected_home is None:
            if selected_temp is None:
                raise ValueError("explicit runtime HOME or temp root required")
            selected_home = selected_temp
        selected_home = _physical_directory(selected_home)
        if selected_temp is None:
            selected_temp = selected_home
        selected_temp = _physical_directory(selected_temp)
        selected_cwd = _physical_directory(cwd) if cwd is not None else None
        values = {str(k): str(v) for k, v in policy["set"].items()}
        values["PATH"] = os.pathsep.join(policy["path_dirs"])
        values["HOME"] = str(selected_home)
        values["TMPDIR"] = str(selected_temp)
        values["TMP"] = str(selected_temp)
        values["TEMP"] = str(selected_temp)
        if extra:
            if any(not isinstance(key, str) or not isinstance(value, str) for key, value in extra.items()):
                raise ValueError("runtime environment overrides must be strings")
            if any(key not in EXTRA_ENVIRONMENT_KEYS for key in extra):
                raise ValueError("runtime environment override is not owner-approved")
            if any(key in NETWORK_VARIABLES or key in {"PATH", "HOME", "TMPDIR", "TMP", "TEMP", "LD_PRELOAD",
                                                       "LD_LIBRARY_PATH", "LD_AUDIT"} for key in extra):
                raise ValueError("runtime environment boundary cannot be overridden")
            roots = [_physical_directory(self.work_dir)] if self.work_dir is not None else []
            roots.append(selected_temp)
            if selected_cwd is not None:
                roots.append(selected_cwd)
            for key in ("GOCACHE", "GOMODCACHE", "npm_config_cache"):
                if key in extra:
                    values[key] = _run_owned_path(extra[key], roots)
            if "PYTHONPATH" in extra:
                if selected_cwd is None:
                    raise ValueError("subject PYTHONPATH requires an explicit command cwd")
                base_parts = [part for part in values.get("PYTHONPATH", "").split(os.pathsep) if part]
                requested_parts = [part for part in extra["PYTHONPATH"].split(os.pathsep) if part]
                if not requested_parts:
                    raise ValueError("subject PYTHONPATH augmentation must not be empty")
                subject_parts: list[str] = []
                for part in requested_parts:
                    if part in base_parts:
                        continue
                    physical = _physical_path(part)
                    if physical != selected_cwd and not physical.is_relative_to(selected_cwd):
                        raise ValueError("subject PYTHONPATH must be inside the command cwd")
                    subject_parts.append(str(physical))
                values["PYTHONPATH"] = os.pathsep.join([*base_parts, *subject_parts])
        # Do not allow callers to smuggle an ambient PATH or shell expansion
        # into an otherwise manifest-derived process environment.
        if values.get("PATH") != os.pathsep.join(policy["path_dirs"]):
            raise ValueError("runtime PATH override refused")
        # Provider-free qualification may install durable native-provider
        # tripwires at the executable boundary. The tripwire projection is
        # deliberately applied here, after the sealed manifest environment is
        # built; bounded version probes use runtime_manifest directly and never
        # pass through this seam.
        try:
            from .provider_free import ACTIVE_GUARD
            guard = ACTIVE_GUARD.get()
        except (ImportError, AttributeError):
            guard = None
        if guard is not None:
            values = guard.path_environment(values)
        return values

    def run(
        self,
        name: str,
        arguments: Sequence[str] = (),
        *,
        stdin: bytes | None = None,
        cwd: str | Path | None = None,
        temp_root: str | Path | None = None,
        extra_environment: Mapping[str, str] | None = None,
        timeout: float = 120,
        check: bool = False,
    ) -> subprocess.CompletedProcess[bytes]:
        """Run one manifest-bound command with complete captured streams.

        Provider names are reserved for the runtime_manifest version-query
        owner, which supplies disposable private state for every probe. Neither
        task calls nor provider version queries may bypass it through this helper.
        """
        checked = self._require_active()
        if not isinstance(arguments, (list, tuple)) or any(not isinstance(arg, str) for arg in arguments):
            raise ValueError("runtime command arguments must be strings")
        record = checked["runtimes"].get(name)
        if not isinstance(record, Mapping) or record.get("executable") is None:
            raise ValueError("runtime name is unavailable")
        if name in runtime_manifest.PROVIDERS:
            raise ValueError("provider task invocation is forbidden; version queries require the bounded version owner")
        selected_cwd = cwd or self.work_dir
        if selected_cwd is None:
            raise ValueError("explicit runtime command cwd required")
        selected_cwd = _physical_directory(selected_cwd)
        environment = self.environment(cwd=selected_cwd, temp_root=temp_root, extra=extra_environment)
        # Full preflight is deliberately explicit and occurs once immediately
        # before the command. Resolve/environment above remain digest-only
        # consumers, so setup cannot multiply scans of large input trees.
        checked = self.revalidate()
        record = checked["runtimes"].get(name)
        entry = checked["files"].get(record.get("executable"))
        if not isinstance(entry, Mapping) or entry.get("kind") != "file":
            raise ValueError("runtime executable is not bound")
        executable = str(entry["physical_path"])
        try:
            result = subprocess.run(
                [executable, *arguments],
                cwd=str(selected_cwd),
                env=environment,
                input=stdin,
                capture_output=True,
                timeout=timeout,
                check=check,
                shell=False,
            )
        except subprocess.TimeoutExpired as error:
            # Keep timeout information bounded and recognizable by callers.
            raise ValueError("manifest-bound runtime command timed out") from error
        finally:
            # A command may have changed an inventoried cache/settings file;
            # revalidation must reject it even when the process exits nonzero.
            self.revalidate()
        return result

    def close(self, *, probe_versions: bool = False) -> Mapping[str, Any]:
        """Revalidate after the transaction and make reuse impossible."""
        try:
            return self.revalidate(probe_versions=probe_versions)
        finally:
            self._active = False

    def expire(self) -> dict[str, Any]:
        """Expire this transaction and return a non-usable manifest copy."""
        self._require_active()
        self._active = False
        return runtime_manifest.expire(self.manifest)


def begin(manifest: Mapping[str, Any], *, work_dir: str | Path | None = None,
          home: str | Path | None = None) -> RuntimeTransaction:
    """Create and start a transaction from a sealed v2 manifest."""
    return RuntimeTransaction(manifest, work_dir=work_dir, home=home).begin()


begin_transaction = begin


def build_environment(manifest: Mapping[str, Any], *, cwd: str | Path,
                      temp_root: str | Path | None = None,
                      home: str | Path | None = None,
                      extra_environment: Mapping[str, str] | None = None) -> dict[str, str]:
    """Build a closed manifest-derived environment for one command boundary."""
    transaction = begin(manifest, work_dir=cwd, home=home)
    try:
        return transaction.environment(cwd=cwd, temp_root=temp_root, extra=extra_environment)
    finally:
        transaction.close()


def run_command(manifest: Mapping[str, Any], name: str, arguments: Sequence[str], *,
                stdin: bytes | None = None, cwd: str | Path, temp_root: str | Path | None = None,
                home: str | Path | None = None, timeout: float = 120,
                check: bool = False,
                extra_environment: Mapping[str, str] | None = None) -> subprocess.CompletedProcess[bytes]:
    """One-shot convenience wrapper with before/after revalidation."""
    transaction = begin(manifest, work_dir=cwd, home=home)
    try:
        return transaction.run(name, arguments, stdin=stdin, cwd=cwd, temp_root=temp_root, check=check,
                               timeout=timeout, extra_environment=extra_environment)
    finally:
        transaction.close()
