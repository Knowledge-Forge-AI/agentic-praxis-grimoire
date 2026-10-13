"""Bounded communication for a child launched in its own owned session.

Only that session's process group may be signalled. Detached browser processes
are outside this proof; the failure evidence keeps that limitation explicit.
"""

import fcntl
import json
import math
import os
from pathlib import Path
import signal
import stat
import subprocess
import time


HARNESS_TIMEOUT_SECONDS = 180
MAX_BROWSER_CASES = 114
BROWSER_COUNT_LIMIT = 3
# Two controlled runs (30s + 5s drain each), readiness/interrupt (45s each),
# cleanup (5s) and bounded process snapshot/drain overhead (15s), per browser.
PW10_BROWSER_SECONDS = 180
SLOT_LOCK_NAME = ".apg-real-browser.lock"
SLOT_TIMEOUT_SECONDS = 2100
SLOT_POLL_SECONDS = 0.25


def _text(value):
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value or ""


def _bounded_int(value, name, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} must be an int in {low}..{high}: {value!r}")
    return value


def harness_timeout_seconds(case_count, pw10_browsers=0):
    """Bound one harness run: max(180, 30 + 4 * cases) plus 180s per browser running PW10."""
    _bounded_int(case_count, "case_count", 1, MAX_BROWSER_CASES)
    _bounded_int(pw10_browsers, "pw10_browsers", 0, BROWSER_COUNT_LIMIT)
    return max(HARNESS_TIMEOUT_SECONDS, 30 + 4 * case_count) + PW10_BROWSER_SECONDS * pw10_browsers


class BrowserSlotError(Exception):
    """The shared real-browser slot was unsafe or not acquired within its bound."""

    def __init__(self, message, *, wait_seconds=0.0, timed_out=False):
        super().__init__(message)
        self.wait_seconds = wait_seconds
        self.timed_out = timed_out


class BrowserSlot:
    """Exclusive flock on a lock file directly inside the shared scratch root."""

    def __init__(self, scratch_root, *, timeout=SLOT_TIMEOUT_SECONDS, poll=SLOT_POLL_SECONDS,
                 clock=time.monotonic, sleep=time.sleep):
        for name, value, maximum in (("timeout", timeout, SLOT_TIMEOUT_SECONDS),
                                     ("poll", poll, SLOT_POLL_SECONDS)):
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or not 0 <= value <= maximum
                    or (name == "poll" and value == 0)):
                raise ValueError(f"Browser slot {name} is outside its finite bound")
        self.path = Path(scratch_root) / SLOT_LOCK_NAME
        self.timeout, self.poll, self.clock, self.sleep = timeout, poll, clock, sleep
        self.fd = None

    def _open_safely(self):
        try:
            if not stat.S_ISDIR(os.lstat(self.path.parent).st_mode):
                raise BrowserSlotError(f"Browser slot root is not a direct directory: {self.path.parent}")
            flags = (os.O_RDWR | os.O_CREAT | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0)
                     | getattr(os, "O_NOFOLLOW", 0))
            fd = os.open(self.path, flags, 0o600)
        except OSError as err:
            raise BrowserSlotError(f"Browser slot lock could not be opened safely: {type(err).__name__}") from err
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                    or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) & 0o022):
                raise BrowserSlotError(f"Browser slot lock is not a private regular file: {self.path.name}")
        except BaseException:
            os.close(fd)
            raise
        return fd, info

    def acquire(self):
        """Return seconds waited; raise BrowserSlotError when unsafe or after the wait bound."""
        started = self.clock()
        fd, info = self._open_safely()
        try:
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    pass
                waited = self.clock() - started
                if waited >= self.timeout:
                    raise BrowserSlotError(
                        f"Browser slot not acquired within {self.timeout}s", wait_seconds=waited, timed_out=True)
                self.sleep(min(self.poll, self.timeout - waited))
            # The lock must still guard the path other harnesses will open.
            now = os.lstat(self.path)
            if (now.st_dev, now.st_ino) != (info.st_dev, info.st_ino):
                raise BrowserSlotError("Browser slot lock was replaced while waiting")
        except BrowserSlotError:
            os.close(fd)
            raise
        except OSError as err:
            os.close(fd)
            raise BrowserSlotError(f"Browser slot lock failed: {type(err).__name__}",
                                   wait_seconds=self.clock() - started) from err
        except BaseException:
            os.close(fd)
            raise
        self.fd = fd
        return self.clock() - started

    def release(self):
        """Idempotent; closing the descriptor drops the flock even if unlock fails."""
        fd, self.fd = self.fd, None
        if fd is None:
            return
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            pass
        finally:
            os.close(fd)


def append_progress_marker(path: Path, marker: dict):
    """Append one JSON line to a direct regular progress file; order is the only timeline."""
    flags = (os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0)
             | getattr(os, "O_NOFOLLOW", 0))
    fd = os.open(path, flags, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_nlink != 1:
            raise OSError("progress marker target is not a regular file")
        line = json.dumps(marker, sort_keys=True).encode("utf-8") + b"\n"
        if info.st_size and os.pread(fd, 1, info.st_size - 1) != b"\n":
            line = b"\n" + line
        if os.write(fd, line) != len(line):
            raise OSError("progress marker append was incomplete")
    finally:
        os.close(fd)


def communicate_owned(proc, *, timeout=HARNESS_TIMEOUT_SECONDS, grace=5, on_deadline=None):
    """Reap on every communication failure and preserve the initiating exception.

    on_deadline runs only for the initial TimeoutExpired, before any group signal;
    its failure is recorded as cleanup evidence and never replaces the primary error.
    """
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
        if on_deadline is not None and isinstance(primary, subprocess.TimeoutExpired):
            try:
                on_deadline()
            except BaseException as err:
                cleanup["errors"].append("on_deadline:" + type(err).__name__)
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
