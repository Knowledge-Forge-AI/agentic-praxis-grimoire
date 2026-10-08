"""Carry one captured model inventory through resolution and provider launch."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import json
import os
from pathlib import Path
import stat
import tomllib
from typing import Mapping

_CAPTURED = ContextVar("apgr_models", default=None)
_SOURCE_DEFAULTS = ContextVar("apgr_source_defaults", default=False)
class ModelAuthorityConflict(ValueError):
    """An ambient fallback attempts to bypass selected authority."""


CAPTURE_ENV = "APGR_DISPATCH_MODELS"
DIGEST_ENV = "APGR_DISPATCH_MODELS_SHA256"


def current_bundle(root: Path):
    from .bundle import load_bundle
    return _CAPTURED.get() or load_bundle(repo_root=_root(root))


def _root(root: Path) -> Path:
    return root.parent if root.name in {"claude", "codex", "antigravity"} else root


def _read_capture(path: Path, digest: str) -> dict:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > 256 * 1024:
            raise ValueError("invalid captured model inventory")
        raw = stream.read(256 * 1024 + 1)
        after = os.fstat(stream.fileno())
    def identity(st):
        return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
    if identity(before) != identity(after) or hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError("captured model inventory changed")
    return tomllib.loads(raw.decode("utf-8"))


def classify_parent_family(provider: str, model: str, role: str | None = None) -> str | None:
    """Central provider-aware parent family classifier; effort is separate."""
    if not isinstance(provider, str) or not isinstance(model, str) or not model:
        return None
    p = provider.strip().lower()
    m = model.strip().lower()
    if p == "antigravity":
        if m.startswith("gemini-") and "flash" in m.split("-"):
            return "gemini_flash"
    elif p == "claude":
        if m.startswith("claude-opus-"):
            return "claude_opus"
        elif m.startswith("claude-fable-"):
            return "claude_fable"
    elif p == "codex":
        if role == "parent":
            return "codex_parent"
    return None


def parent_family_for_endpoint(
    root: Path, provider: str, profile: str, *, bundle=None
) -> str | None:
    """Derive parent family from captured/selected model, not profile name."""
    from .bundle_io import BundleError
    try:
        sel = selection(root, provider, profile, bundle=bundle)
    except ModelAuthorityConflict:
        raise
    except (ValueError, BundleError):
        return None
    return classify_parent_family(provider, sel["model"], role=sel.get("role"))


def selection(root: Path, provider: str, profile: str, *, bundle=None) -> dict:
    if _SOURCE_DEFAULTS.get() is True:
        from .roster import _capture_source, _revalidate_source
        source = _capture_source(_root(root), Path("common/dispatcher/models.toml"))
        _revalidate_source(_root(root), source)
        catalog = tomllib.loads(source.raw.decode())
        return _validate(catalog.get("providers", {}).get(provider, {}).get(profile), provider, profile)

    is_ambient_source_defaults = os.environ.get("APGR_MODEL_AUTHORITY") == "source-defaults"

    captured_b = bundle or _CAPTURED.get()
    if captured_b is not None:
        if is_ambient_source_defaults:
            raise ModelAuthorityConflict(
                "ambient APGR_MODEL_AUTHORITY=source-defaults conflicts with captured model authority"
            )
        return _validate(captured_b.select_model(provider, profile).as_dict(), provider, profile)

    path = os.environ.get(CAPTURE_ENV)
    if path:
        if is_ambient_source_defaults:
            raise ModelAuthorityConflict(
                "ambient APGR_MODEL_AUTHORITY=source-defaults conflicts with captured model authority"
            )
        catalog = _read_capture(Path(path), os.environ.get(DIGEST_ENV, ""))
        entry = catalog.get("providers", {}).get(provider, {}).get(profile)
        return _validate(entry, provider, profile)

    from .bundle import load_bundle
    from .config_routing import resolve_global_home
    from .bundle_io import read_home_bundle_required
    home = resolve_global_home()
    if is_ambient_source_defaults and ((home / "dispatcher").exists() or read_home_bundle_required(home)):
        raise ModelAuthorityConflict("ambient APGR_MODEL_AUTHORITY=source-defaults conflicts with selected home model authority")
    selected_bundle = load_bundle(repo_root=_root(root))
    return _validate(selected_bundle.select_model(provider, profile).as_dict(), provider, profile)


def _validate(entry, provider: str, profile: str) -> dict:
    if not isinstance(entry, Mapping):
        raise ValueError(f"missing model selection: {provider}/{profile}")
    model, effort = entry.get("model"), entry.get("effort")
    if not isinstance(model, str) or not model or any(c.isspace() for c in model):
        raise ValueError("invalid selected model")
    if effort not in {"low", "medium", "high", "xhigh", "max", "ultra"}:
        raise ValueError("invalid selected effort")
    return {**entry, "provider": provider, "profile": profile}


def selected_worker_profile(root: Path, kind: str) -> str:
    from apgr_workers.policy import load_worker_policy
    policy, _, _ = load_worker_policy(_root(root))
    selections = policy.get("selections", {})
    policy_name = policy.get("policy", {}).get("name")
    selection = selections.get(policy_name) if policy_name else None
    if selection is None:
        selection = selections.get("triple_pool_4x4x4") or selections.get("dual_pool_4x4", {})
    entry = selection.get(kind + "_worker")
    if kind == "gemini" and not entry:
        entry = policy.get("gemini_worker")
    if not isinstance(entry, Mapping) or not isinstance(entry.get("profile"), str) or not entry["profile"]:
        raise ValueError("selected worker profile unavailable")
    return entry["profile"]


@contextmanager
def captured(bundle):
    token = _CAPTURED.set(bundle)
    try:
        yield
    finally:
        _CAPTURED.reset(token)


@contextmanager
def source_defaults():
    """Explicit source-bound qualification lane; never selected as a fallback."""
    token = _SOURCE_DEFAULTS.set(True)
    previous = os.environ.get("APGR_MODEL_AUTHORITY")
    os.environ["APGR_MODEL_AUTHORITY"] = "source-defaults"
    try:
        yield
    finally:
        _SOURCE_DEFAULTS.reset(token)
        if previous is None:
            os.environ.pop("APGR_MODEL_AUTHORITY", None)
        else:
            os.environ["APGR_MODEL_AUTHORITY"] = previous


@contextmanager
def launch_capture(bundle, directory: Path):
    """Pass the immutable capture to child launchers, never recapture operator home."""
    member = bundle.members["models.toml"]
    path = directory / "launch-models.toml"
    if path.exists():
        if _read_capture(path, member.sha256) != tomllib.loads(member.raw.decode()):
            raise ValueError("launch inventory mismatch")
    else:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(member.raw)
    worker = bundle.members["workers.toml"]
    worker_path = directory / "launch-workers.toml"
    if not worker_path.exists():
        fd = os.open(worker_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(worker.raw)
    _read_capture(worker_path, worker.sha256)
    values = {CAPTURE_ENV: str(path), DIGEST_ENV: member.sha256,
              "APGR_DISPATCH_WORKERS": str(worker_path),
              "APGR_DISPATCH_WORKERS_SHA256": worker.sha256,
              "APGR_MODEL_AUTHORITY": "captured-bundle"}
    prior = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        with captured(bundle):
            yield
    finally:
        for key, value in prior.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def apply_selection(argv: list[str], endpoint, root: Path, *, bundle=None) -> list[str]:
    """Codex accepts explicit overrides; wrapper launchers read the capture."""
    if endpoint.provider != "codex":
        return argv
    choice = selection(root, endpoint.provider, endpoint.profile, bundle=bundle)
    result = list(argv)
    prompt_index = len(result)
    if result and result[-1] == "-":
        prompt_index = len(result) - 1
    model_args = [
        "-c", "model=" + json.dumps(choice["model"]),
        "-c", "model_reasoning_effort=" + json.dumps(choice["effort"]),
    ]
    return result[:prompt_index] + model_args + result[prompt_index:]
