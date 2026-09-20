"""Bounded communication for a child launched in its own owned session.

Only that session's process group may be signalled. Detached browser processes
are outside this proof; the failure evidence keeps that limitation explicit.
"""

import os
from pathlib import Path
import signal
import stat
import subprocess
import time


HARNESS_TIMEOUT_SECONDS = 180


def _text(value):
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value or ""


def communicate_owned(proc, *, timeout=HARNESS_TIMEOUT_SECONDS, grace=5):
    """Reap on every communication failure and preserve the initiating exception."""
    started = time.monotonic()
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        return stdout, stderr
    except BaseException as primary:
        stdout = _text(getattr(primary, "output", ""))
        stderr = _text(getattr(primary, "stderr", ""))
        cleanup = {"child_reaped": False, "pipe_retained_after_group_kill": False,
                   "detached_descendants": "not_verified", "errors": [],
                   "communication_started_monotonic": started,
                   "exception_observed_monotonic": time.monotonic()}
        try:
            cleanup["child_returncode_at_exception"] = proc.poll() if hasattr(proc, "poll") else proc.returncode
        except OSError as err:
            cleanup["errors"].append(type(err).__name__)
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(proc.pid, sig)
            except ProcessLookupError:
                pass
            except OSError as err:
                cleanup["errors"].append(type(err).__name__)
            try:
                stdout, stderr = proc.communicate(timeout=grace)
                break
            except subprocess.TimeoutExpired as err:
                # communicate retries return cumulative output; do not duplicate it.
                stdout = _text(err.output) or stdout
                stderr = _text(err.stderr) or stderr
            except BaseException as err:
                cleanup["errors"].append(type(err).__name__)
        else:
            cleanup["pipe_retained_after_group_kill"] = True
            for stream in (proc.stdout, proc.stderr):
                if stream is not None:
                    try:
                        stream.close()
                    except OSError as err:
                        cleanup["errors"].append(type(err).__name__)
            try:
                proc.wait(timeout=grace)
            except BaseException as err:
                cleanup["errors"].append(type(err).__name__)
        cleanup["child_reaped"] = proc.returncode is not None
        cleanup["cleanup_completed_monotonic"] = time.monotonic()
        primary.output, primary.stderr, primary.cleanup = stdout, stderr, cleanup
        raise


def progress_tail(path: Path, *, lines=48):
    """Read a small terminal slice from a direct regular progress file."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode):
                return []
            stream.seek(max(0, info.st_size - 65536))
            return stream.read(65536).decode("utf-8", errors="replace").splitlines()[-lines:]
    except OSError:
        return []
