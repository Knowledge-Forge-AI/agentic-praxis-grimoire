"""Affirmatively identify APG Python children measured by coverage.py."""

from __future__ import annotations

import atexit
import json
import os
from pathlib import Path
import secrets
import sys
from types import FrameType


def _append(path: Path, event: dict[str, object]) -> None:
    line = (json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n").encode()
    descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.write(descriptor, line)
    finally:
        os.close(descriptor)


def _required_child_id() -> tuple[str, bool] | None:
    explicit = os.environ.get("APG_TEST_REQUIRED_CHILD_ID")
    if explicit:
        return explicit, True
    try:
        allowed = set(json.loads(os.environ["APG_TEST_REQUIRED_ENTRYPOINTS"]))
    except (KeyError, OSError, TypeError, ValueError):
        return None
    name = Path(sys.argv[0]).name
    if name in allowed:
        return f"{name}-{os.getpid()}-{secrets.token_hex(8)}", False
    return None


def _register() -> None:
    required = _required_child_id()
    if required is None:
        return
    process_id, explicit = required
    try:
        run_id = os.environ["APG_TEST_RUN_ID"]
        suite = os.environ["APG_TEST_SUITE"]
        path = Path(os.environ["APG_TEST_CHILD_MANIFEST"])
    except KeyError:
        return
    context = f"apg-child:{run_id}:{process_id}"
    common = {
        "run_id": run_id,
        "suite": suite,
        "process_id": process_id,
        "context": context,
    }

    registered = False

    def register_events() -> None:
        nonlocal registered
        if registered:
            return
        registered = True
        if os.environ.get("APG_TEST_DISABLE_CHILD_COVERAGE") != "1":
            try:
                from coverage import Coverage

                current = Coverage.current()
                if current is not None:
                    current.switch_context(context)
            except Exception:
                pass
        _append(path, {**common, "event": "child-start"})
        atexit.register(
            lambda: _append(path, {**common, "event": "child-complete"})
        )

    if explicit:
        register_events()
        return

    try:
        allowed_modules = set(
            json.loads(os.environ["APG_TEST_REQUIRED_MODULE_BASENAMES"])
        )
        canonical_libexec = Path(
            os.environ["APG_TEST_CANONICAL_LIBEXEC"]
        ).resolve(strict=True)
    except (KeyError, TypeError, ValueError):
        return
    previous_profile = sys.getprofile()

    def profile(frame: FrameType, event: str, argument: object) -> None:
        if previous_profile is not None:
            previous_profile(frame, event, argument)
        if event != "call":
            return
        filename = Path(frame.f_code.co_filename)
        if filename.name not in allowed_modules:
            return
        try:
            module_path = filename.resolve(strict=True)
        except OSError:
            return
        canonical = module_path.is_relative_to(canonical_libexec)
        public_copy = any(
            parent.name == "public-source"
            and module_path.is_relative_to(parent / "libexec")
            for parent in module_path.parents
        )
        if not canonical and not public_copy:
            return
        register_events()
        sys.setprofile(previous_profile)

    sys.setprofile(profile)


_register()
