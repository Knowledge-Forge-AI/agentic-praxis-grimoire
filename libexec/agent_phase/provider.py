"""Provider invocation. The dispatcher owns command construction.

argv arrays only; there is no shell string anywhere in this module, and the
prompt travels on stdin rather than as an argument.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import threading
import time
from typing import Any, Callable, NamedTuple, Sequence

from .routing import (
    Endpoint,
    PROVIDER_ANTIGRAVITY,
    PROVIDER_CLAUDE,
    PROVIDER_CODEX,
)


# Vendor executables are discovered neutrally from PATH. The selected absolute
# executable is retained for launched operations, issuing a clear diagnostic if
# unavailable.
def resolve_codex_executable(path: str | None = None) -> str:
    resolved = shutil.which("codex", path=path)
    if not resolved:
        raise ProviderError("Codex executable not found on PATH: codex")
    return os.path.abspath(resolved)


CLAUDE_LAUNCHER = "bin/claude-profile"
ANTIGRAVITY_LAUNCHER = "bin/antigravity-profile"

MAX_STAGE_OUTPUT_BYTES = 4 * 1024 * 1024
KILL_GRACE_SECONDS = 5.0
POLL_SECONDS = 0.05
PROCESS_GROUP_STATUS_TIMEOUT_SECONDS = 0.25
TEARDOWN_ATTEMPTS = 3

# Liveness is a provider-source contract. The dispatcher deliberately has no
# timeout input and never selects these values from a request or prompt. Tests
# may inject a short policy, but production selection is source-owned.
#
# Silence is NOT proof of death. A generic 900s hard inactivity bound used to be
# enforced here, and on 2026-09-04 it killed a healthy Claude work stage that had
# already modified nineteen tracked paths: stdout_bytes=0, stderr_bytes=1242 of
# startup permission diagnostics, silent=900.006s, cleanup_proven=true. The
# provider was running a legitimate quiet foreground command. A provider that
# emits no bytes for fifteen, thirty, or sixty minutes may simply be executing a
# long test, build, Nix evaluation, or deployment check.
#
# Production therefore has NO hard inactivity bound. Silence is advisory: it is
# observed, counted, and reported, but never terminates a provider. What still
# terminates is unchanged and independent of silence -- the absolute outer
# ceiling below, operator interruption, stdout overflow, provider exit or error,
# terminal-fence cleanup, and proven process-cleanup failure.
DEFAULT_ADVISORY_SILENCE_SECONDS = 900.0
DEFAULT_ADVISORY_INTERVAL_SECONDS = 900.0
DEFAULT_OUTER_CEILING_SECONDS = 90_000.0

# Bounded evidence: the notice count keeps rising, but only this many individual
# notice records are retained, so a very long quiet stage cannot grow storage.
STALL_WARNING_RECORD_LIMIT = 16

# The managed Antigravity wrapper is the only provider which can report nested
# activity.  The pipe is private to the wrapper and this provider; its contents
# are a closed, bounded token vocabulary rather than provider-controlled text.
ACTIVITY_PIPE_ENV = "AGENT_CENTRAL_ANTIGRAVITY_ACTIVITY_FD"
ACTIVITY_MAX_TOKEN_BYTES = 64
ACTIVITY_MAX_BUFFER_BYTES = 4096
ACTIVITY_STDOUT_TOKEN = b"O\n"
ACTIVITY_STDERR_TOKEN = b"E\n"
ACTIVITY_PROTOCOL_TOKEN = b"P\n"
# A parsed protocol event that proves nothing advanced -- a keepalive, ping, or
# a non-terminal `waiting`/`pending` status. It is counted, never credited.
ACTIVITY_WAITING_TOKEN = b"W\n"
ACTIVITY_PGID_PREFIX = b"G:"
LIVENESS_TERM_GRACE_SECONDS = 1.0
LIVENESS_KILL_GRACE_SECONDS = 1.0

STREAM_STDOUT = "stdout"
STREAM_STDERR = "stderr"

# The dispatcher does not select a phase time limit. The provider source owns a
# long liveness safety envelope: the outer ceiling bounds a stage that never
# ends at all, while silence only produces advisory evidence. Per-stream capture
# limits and explicit operator interruption remain separate outcomes. Stdout
# overflow is fatal; excess stderr is drained and discarded.


class ProviderError(RuntimeError):
    """A provider could not be invoked as the dispatcher requires."""


@dataclass(frozen=True)
class LivenessPolicy:
    """Source-owned bounds for a provider that may be making no progress.

    `inactivity_seconds` is the hard silence bound and defaults to `None`,
    meaning production never terminates a provider merely because it is quiet.
    A finite value is still honoured so deterministic tests -- and any future
    explicitly accepted policy -- can inject one and get the typed
    `ProviderLivenessExpired` evidence path.

    `advisory_silence_seconds` is the first-notice threshold and
    `advisory_interval_seconds` rate-limits later notices. Neither can terminate
    anything. `outer_ceiling_seconds` is the absolute safety ceiling and is
    always enforced.
    """

    inactivity_seconds: float | None = None
    outer_ceiling_seconds: float = DEFAULT_OUTER_CEILING_SECONDS
    advisory_silence_seconds: float | None = DEFAULT_ADVISORY_SILENCE_SECONDS
    advisory_interval_seconds: float = DEFAULT_ADVISORY_INTERVAL_SECONDS

    def __post_init__(self) -> None:
        optional = {"inactivity_seconds", "advisory_silence_seconds"}
        for name in (
            "inactivity_seconds",
            "outer_ceiling_seconds",
            "advisory_silence_seconds",
            "advisory_interval_seconds",
        ):
            value = getattr(self, name)
            if value is None and name in optional:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be a finite positive number")
            if not math.isfinite(float(value)) or value <= 0:
                raise ValueError(f"{name} must be a finite positive number")

    @property
    def inactivity(self) -> float | None:
        """Compatibility spelling for evidence and focused test callers."""
        return self.inactivity_seconds

    @property
    def outer_ceiling(self) -> float:
        """Compatibility spelling for evidence and focused test callers."""
        return self.outer_ceiling_seconds


DEFAULT_LIVENESS_POLICY = LivenessPolicy()


class ProviderInterrupted(BaseException):
    """The operator interrupted a provider stage.

    Derived from `BaseException` for the same reason `KeyboardInterrupt` is: an
    interrupted run must not be swallowed by a handler that meant to catch
    ordinary stage failure. It carries the bytes read before the interrupt so
    the stage's partial output can still be persisted as evidence.
    """

    def __init__(
        self,
        stdout: bytes,
        stderr: bytes,
        truncated: bool = False,
        stderr_truncated: bool = False,
        *,
        termination: dict[str, Any] | None = None,
        cleanup: dict[str, Any] | None = None,
    ) -> None:
        super().__init__("provider stage interrupted by operator")
        self.stdout = stdout
        self.stderr = stderr
        self.truncated = truncated
        self.stderr_truncated = stderr_truncated
        self.partial_stdout = stdout
        self.partial_stderr = stderr
        self.stdout_truncated = truncated
        self.partial_stdout_truncated = truncated
        self.partial_stderr_truncated = stderr_truncated
        self.termination = termination or {}
        self.cleanup = cleanup or {}
        self.termination_facts = self.termination
        self.cleanup_facts = self.cleanup


class ProviderCleanupFailed(ProviderError):
    """A normally completed provider could not be proven fully cleaned up.

    The provider result remains a six-field-compatible ``Result`` tuple.  A
    cleanup failure is exceptional instead, carrying the exact bytes captured
    before the cleanup/join boundary and a serializable fact set for the
    dispatcher to persist.  This keeps cleanup evidence additive without
    changing the legacy tuple's positional shape.
    """

    def __init__(
        self,
        stdout: bytes,
        stderr: bytes,
        truncated: bool = False,
        stderr_truncated: bool = False,
        *,
        cleanup: dict[str, Any],
        termination: dict[str, Any] | None = None,
        exit_code: int | None = None,
        started: float | None = None,
        ended: float | None = None,
    ) -> None:
        super().__init__("provider cleanup could not be proven complete")
        self.stdout = stdout
        self.stderr = stderr
        self.truncated = truncated
        self.stderr_truncated = stderr_truncated
        self.partial_stdout = stdout
        self.partial_stderr = stderr
        self.stdout_truncated = truncated
        self.partial_stdout_truncated = truncated
        self.partial_stderr_truncated = stderr_truncated
        self.cleanup = cleanup
        self.cleanup_facts = cleanup
        self.termination = termination or {}
        self.termination_facts = self.termination
        self.exit_code = exit_code
        self.returncode = exit_code
        self.started = started
        self.ended = ended


class ProviderLivenessExpired(BaseException):
    """A provider stopped making progress under the source-owned policy.

    This is deliberately a separate ``BaseException`` family from
    :class:`ProviderInterrupted`: an operator interrupt and an automatic
    liveness teardown have different recovery/accounting meaning.  All stream
    bytes read before and during bounded cleanup are retained up to the normal
    output cap, while truncation facts remain explicit.
    """

    def __init__(
        self,
        stdout: bytes,
        stderr: bytes,
        truncated: bool,
        stderr_truncated: bool,
        *,
        policy: LivenessPolicy,
        reason: str,
        elapsed_seconds: float,
        silent_seconds: float,
        last_activity_monotonic: float,
        last_activity_stream: str | None,
        termination: dict[str, Any],
        cleanup: dict[str, Any],
        activity_counts: dict[str, dict[str, int]] | None = None,
    ) -> None:
        super().__init__(
            f"provider liveness expired ({reason}); "
            f"silent={silent_seconds:.3f}s elapsed={elapsed_seconds:.3f}s"
        )
        self.stdout = stdout
        self.stderr = stderr
        self.truncated = truncated
        self.stderr_truncated = stderr_truncated
        self.partial_stdout = stdout
        self.partial_stderr = stderr
        self.stdout_truncated = truncated
        self.partial_stdout_truncated = truncated
        self.partial_stderr_truncated = stderr_truncated
        self.policy = policy
        self.reason = reason
        self.expiry_reason = reason
        self.elapsed_seconds = elapsed_seconds
        self.elapsed = elapsed_seconds
        self.silent_seconds = silent_seconds
        self.silent = silent_seconds
        self.silent_for = silent_seconds
        self.last_activity_monotonic = last_activity_monotonic
        self.last_activity = last_activity_monotonic
        self.last_activity_stream = last_activity_stream
        self.last_activity_kind = last_activity_stream
        self.last_activity_age_seconds = silent_seconds
        # Bounded, closed-vocabulary counters. Diagnosing a future stall needs to
        # separate "the provider went quiet" from "the provider only ever emitted
        # noise that no longer counts", without retaining any pipe payload.
        self.activity_counts = activity_counts or {"progress": {}, "non_progress": {}}
        self.activity_facts = {
            "elapsed_seconds": elapsed_seconds,
            "silent_seconds": silent_seconds,
            "last_activity_monotonic": last_activity_monotonic,
            "last_activity_stream": last_activity_stream,
            "activity_counts": self.activity_counts,
        }
        self.termination = termination
        self.cleanup = cleanup
        self.termination_facts = termination
        self.cleanup_facts = cleanup


class _ResultTuple(NamedTuple):
    exit_code: int
    stdout: bytes
    stderr: bytes
    truncated: bool
    started: float
    ended: float
    stderr_truncated: bool = False


class Result(_ResultTuple):
    """Legacy seven-item result tuple with additive cleanup evidence.

    ``cleanup`` deliberately lives outside the tuple fields.  Existing callers
    can keep constructing, unpacking, serializing, and replacing the established
    seven values while real subprocess results expose the custody proof as an
    attribute.
    """

    cleanup: dict[str, Any] | None = None

    def __new__(
        cls,
        exit_code: int,
        stdout: bytes,
        stderr: bytes,
        truncated: bool,
        started: float,
        ended: float,
        stderr_truncated: bool = False,
        *,
        cleanup: dict[str, Any] | None = None,
    ) -> "Result":
        result = super().__new__(
            cls,
            exit_code,
            stdout,
            stderr,
            truncated,
            started,
            ended,
            stderr_truncated,
        )
        result.cleanup = cleanup
        return result

    def _replace(self, /, **changes: Any) -> "Result":
        cleanup = changes.pop("cleanup", self.cleanup)
        values = self._asdict()
        unknown = set(changes) - set(self._fields)
        if unknown:
            raise ValueError(f"Got unexpected field names: {sorted(unknown)!r}")
        values.update(changes)
        return type(self)(**values, cleanup=cleanup)

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.truncated


def build_argv(
    endpoint: Endpoint,
    role: str,
    root: Path,
    codex_executable: str | None = None,
    claude_launcher: str | None = None,
    antigravity_launcher: str | None = None,
    *,
    read_only: bool | None = None,
    evidence_prefix: Path | None = None,
    pin_profile: bool = True,
) -> list[str]:
    effective_read_only = role == "reviewer" if read_only is None else read_only
    if endpoint.provider == PROVIDER_CLAUDE:
        launcher = claude_launcher or os.fspath(root / CLAUDE_LAUNCHER)
        # The launcher owns model, effort, permission mode, scope, and settings.
        # Reconstructing any of them here is what the launcher exists to prevent.
        argv = [launcher, endpoint.profile]
        if effective_read_only:
            # Wrapper-only flag: the launcher owns and validates the exact CLI
            # permission/tool posture. This is not a Claude CLI override.
            argv.append("--read-only")
        argv.append("-p")
        return argv
    if endpoint.provider == PROVIDER_CODEX:
        resolved = codex_executable or resolve_codex_executable()
        from controller_generation import codex_profile_arguments
        profile_args = (codex_profile_arguments(root, endpoint.profile) if pin_profile
                        else ["--profile", endpoint.profile])
        argv = [resolved, "exec", *profile_args]
        if effective_read_only:
            # Matches the established reviewer convention in bin/codex-peer-review.
            argv.extend(["-s", "read-only"])
        # Primaries get no sandbox flag: the compiled base config owns that policy.
        argv.append("-")
        return argv
    if endpoint.provider == PROVIDER_ANTIGRAVITY:
        launcher = antigravity_launcher or os.fspath(root / ANTIGRAVITY_LAUNCHER)
        argv = [launcher, endpoint.profile, "-p"]
        if effective_read_only:
            argv.append("--reviewer")
        if evidence_prefix is not None:
            argv.extend(["--evidence-prefix", os.fspath(evidence_prefix)])
        return argv
    raise ProviderError(f"unknown provider: {endpoint.provider}")


def _is_managed_antigravity_launcher(argv: Sequence[str], cwd: Path) -> bool:
    """Recognize only this checkout's Antigravity wrapper for activity wiring."""
    if not argv:
        return False
    candidate = Path(argv[0])
    if not candidate.is_absolute():
        candidate = cwd / candidate
    managed = Path(__file__).resolve().parents[2] / ANTIGRAVITY_LAUNCHER
    try:
        return candidate.resolve(strict=False) == managed.resolve(strict=False)
    except OSError:
        return False


def _effective_liveness_policy(override: LivenessPolicy | None) -> LivenessPolicy:
    # Select one source-owned policy before the provider process starts. There is
    # no per-provider hard silence bound: the managed Antigravity wrapper gets the
    # same advisory treatment as every other provider.
    if override is not None:
        if not isinstance(override, LivenessPolicy):
            raise TypeError("liveness_policy must be a LivenessPolicy")
        return override
    return DEFAULT_LIVENESS_POLICY


def _validated_nested_group(
    token: bytes, wrapper_pid: int
) -> tuple[int, int] | None:
    """Validate one wrapper-emitted nested process-group registration."""
    if not token.startswith(ACTIVITY_PGID_PREFIX):
        return None
    try:
        payload = token[len(ACTIVITY_PGID_PREFIX) :].decode("ascii")
        nested_pid_text, nested_pgid_text = payload.split(":", 1)
        nested_pid = int(nested_pid_text, 10)
        nested_pgid = int(nested_pgid_text, 10)
    except (UnicodeDecodeError, ValueError):
        return None
    if (
        nested_pid <= 0
        or nested_pgid <= 0
        or nested_pid != nested_pgid
        or nested_pid == wrapper_pid
        or nested_pgid == wrapper_pid
        or len(token) > ACTIVITY_MAX_TOKEN_BYTES
    ):
        return None
    try:
        # The wrapper launches AGY with start_new_session=True.  Requiring the
        # token's PID to be a session leader and to own the advertised PGID
        # prevents an arbitrary number received on the private pipe from being
        # treated as a kill target.
        if os.getpgid(nested_pid) != nested_pgid:
            return None
        if os.getsid(nested_pid) != nested_pid:
            return None
    except ProcessLookupError:
        # The source-owned wrapper emitted this registration before the nested
        # session leader exited. A TERM-ignoring descendant can keep the PGID
        # alive after that leader is gone, so validate group existence rather
        # than discarding the only safe cleanup handle.
        try:
            os.killpg(nested_pgid, 0)
        except (OSError, OverflowError, ValueError):
            return None
    except (OSError, OverflowError, ValueError):
        return None
    return nested_pid, nested_pgid


def _activity_counts(activity: dict[str, Any]) -> dict[str, dict[str, int]]:
    """Snapshot the closed per-kind activity vocabulary as plain integers.

    Callers must already hold the activity lock. The result is deliberately a
    copy: the live dictionaries keep mutating under the reader threads.
    """
    return {
        "progress": dict(activity["kinds"]),
        "non_progress": dict(activity["non_progress"]),
    }


def _new_stall_warnings(policy: LivenessPolicy) -> dict[str, Any]:
    """Bounded advisory-silence evidence for one provider run."""
    return {
        "count": 0,
        "first_at": None,
        "last_at": None,
        "threshold_seconds": policy.advisory_silence_seconds,
        "interval_seconds": policy.advisory_interval_seconds,
        "notices": [],
    }


def _record_stall_warning(
    stall_warnings: dict[str, Any],
    *,
    elapsed_seconds: float,
    silent_seconds: float,
    last_activity_kind: str | None,
    threshold_seconds: float,
    on_notice: Callable[[dict[str, Any]], None] | None,
) -> dict[str, Any]:
    """Record one advisory stall notice and offer it to the observer.

    This never terminates the provider, fails the phase, changes the result, or
    requires a broker. `count` keeps rising for truthful reporting while stored
    `notices` stop at STALL_WARNING_RECORD_LIMIT, so storage stays bounded no
    matter how long the stage stays quiet.
    """
    stall_warnings["count"] += 1
    notice = {
        "sequence": stall_warnings["count"],
        "at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "elapsed_seconds": elapsed_seconds,
        "silent_seconds": silent_seconds,
        "last_activity_kind": last_activity_kind,
        "threshold_seconds": threshold_seconds,
    }
    if stall_warnings["first_at"] is None:
        stall_warnings["first_at"] = notice["at"]
    stall_warnings["last_at"] = notice["at"]
    if len(stall_warnings["notices"]) < STALL_WARNING_RECORD_LIMIT:
        stall_warnings["notices"].append(notice)
    if on_notice is not None:
        try:
            on_notice(dict(notice))
        except Exception:
            # Advisory evidence must never be able to fail the stage.
            pass
    return notice


def _drain_activity(
    source_fd: int,
    wrapper_pid: int,
    lock: threading.Lock,
    activity: dict[str, Any],
    nested_groups: dict[int, int],
) -> None:
    """Read bounded internal activity tokens and register safe nested groups.

    Parsing deliberately precedes crediting. Only a recognized source-owned
    progress token refreshes liveness; a malformed, unknown, oversized, partial,
    or buffer-overflow-discarded read is counted as non-progress and cannot
    postpone inactivity expiry. A validated nested process-group registration is
    custody metadata rather than semantic progress: it is still recorded and
    still torn down, but a wrapper that only ever registers groups is silent.
    """
    pending = bytearray()
    try:
        while chunk := os.read(source_fd, 4096):
            pending.extend(chunk)
            if len(pending) > ACTIVITY_MAX_BUFFER_BYTES:
                pending.clear()
                with lock:
                    activity["non_progress"]["discarded"] += 1
                continue
            while b"\n" in pending:
                line, _, remainder = pending.partition(b"\n")
                pending = bytearray(remainder)
                token_bytes = len(line) + 1
                if token_bytes > ACTIVITY_MAX_TOKEN_BYTES:
                    with lock:
                        activity["non_progress"]["oversized"] += 1
                    continue
                if line == b"O":
                    stream = "nested.stdout"
                elif line == b"E":
                    stream = "nested.stderr"
                elif line == b"P":
                    stream = "nested.protocol"
                elif line == b"W":
                    # A recognized but explicitly non-advancing protocol event.
                    # Counting it separately is the whole point: generic wrapper
                    # chatter must not postpone the advisory silence clock.
                    with lock:
                        activity["non_progress"]["waiting"] += 1
                    continue
                else:
                    registration = _validated_nested_group(line, wrapper_pid)
                    if registration is None:
                        with lock:
                            activity["non_progress"]["unknown"] += 1
                        continue
                    nested_pid, nested_pgid = registration
                    with lock:
                        nested_groups[nested_pgid] = nested_pid
                        activity["non_progress"]["nested.pgid"] += 1
                    continue
                now = time.monotonic()
                with lock:
                    activity["last"] = now
                    activity["stream"] = stream
                    activity["reads"] += 1
                    activity["bytes"] += token_bytes
                    activity["kinds"][stream] += 1
        if pending:
            # EOF with an unterminated remainder: never a complete token.
            with lock:
                activity["non_progress"]["partial"] += 1
    except (OSError, ValueError):
        pass
    finally:
        try:
            os.close(source_fd)
        except OSError:
            pass


def _drain(
    stream,
    name: str,
    sink: list[bytes],
    cap: int,
    overflow: list[bool],
    observer: list[Callable[[str, bytes], None] | None],
    lock: threading.Lock,
    on_read: Callable[[str, bytes], None] | None = None,
) -> None:
    """Capture the stream, and optionally mirror it as it arrives.

    The observer is fed exactly the bytes that are stored, so the terminal can
    never show output the artifact does not contain. Storing and mirroring
    happen under `lock`, which `run` also holds when it retires the observer and
    snapshots the captured bytes: a reader thread that outlived its join — a
    provider-local worker can hold the pipe open past its parent's exit — would
    otherwise keep mirroring bytes that never reached the snapshot, and would
    print them under the *next* stage's label.

    The exception guard is here rather than in the observer because a raising
    callback would otherwise kill this thread and silently truncate the captured
    evidence while the stream's overflow flag stayed false.
    """
    total = 0
    try:
        # `read1`, not `read`: a buffered `read(n)` blocks until n bytes or EOF,
        # which would hold every byte until the provider exited and make live
        # mirroring impossible. `read1` returns what one raw read yielded.
        while chunk := stream.read1(65536):
            # Record activity before applying the capture cap. Excess output
            # is discarded for storage/display but still proves provider
            # progress and must postpone inactivity expiry.
            if on_read is not None:
                try:
                    on_read(name, chunk)
                except BaseException:
                    pass
            with lock:
                if total >= cap:
                    overflow[0] = True
                    continue
                room = cap - total
                stored = chunk[:room]
                sink.append(stored)
                total += len(stored)
                if observer[0] is not None:
                    try:
                        observer[0](name, stored)
                    except BaseException:
                        observer[0] = None
                if len(chunk) > room:
                    overflow[0] = True
    except (OSError, ValueError):
        pass


def _signal_group(pgid: int, signum: int) -> str:
    """Signal one validated process group and return bounded status text."""
    try:
        os.killpg(pgid, signum)
    except ProcessLookupError:
        return "absent"
    except PermissionError:
        return "permission_denied"
    except OSError:
        return "error"
    return "sent"


def _group_probe(pgid: int) -> str:
    """Return live-state for the launch-owned session/group identity."""
    probe_status = "present"
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return "absent"
    except PermissionError:
        probe_status = "permission_denied"
    except (OSError, OverflowError, ValueError):
        return "error"

    try:
        listing = subprocess.run(
            ["/bin/ps", "-axo", "pid=,pgid=,stat="],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=PROCESS_GROUP_STATUS_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    if listing.returncode != 0:
        return "unknown"

    matching_row = False
    for line in listing.stdout.splitlines():
        try:
            fields = line.decode("ascii").split()
            if len(fields) < 3:
                continue
            row_pid = int(fields[0], 10)
            row_pgid = int(fields[1], 10)
        except (UnicodeDecodeError, ValueError):
            continue
        if row_pgid != pgid:
            continue
        matching_row = True
        if fields[2].startswith("Z"):
            continue
        try:
            if os.getsid(row_pid) == pgid:
                return probe_status
        except ProcessLookupError:
            continue
        except (OSError, ValueError):
            return "unknown"
        return "unknown"
    if matching_row:
        return "absent"

    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return "absent"
    except PermissionError:
        return "permission_denied"
    except (OSError, OverflowError, ValueError):
        return "error"
    return "unknown"


def _cleanup_process_groups(
    process: subprocess.Popen,
    nested_groups: dict[int, int],
    *,
    registration_lock: threading.Lock | None = None,
    activity_thread: threading.Thread | None = None,
    readers: Sequence[threading.Thread] | None = None,
    writer: threading.Thread | None = None,
    term_grace: float,
    kill_grace: float,
    reason: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Terminate every trusted group and prove the complete cleanup boundary.

    The provider parent owns one private process group.  The managed
    Antigravity wrapper may register additional, independently-sessioned groups
    through the private activity pipe.  Cleanup therefore has two registration
    drains: one after the outer TERM and one after the outer KILL.  This closes
    the initially-empty and late-registration races before stream readers are
    joined.  The function returns facts instead of assuming that a signal was
    effective; callers can turn an unproven boundary into a typed failure.
    """

    stream_readers = list(readers or [])

    def registered_groups() -> list[int]:
        if registration_lock is None:
            items = list(nested_groups.items())
        else:
            with registration_lock:
                items = list(nested_groups.items())
        groups: list[int] = []
        for pgid, nested_pid in sorted(items):
            if pgid == process.pid:
                continue
            try:
                # Revalidate the PID/PGID relationship at teardown so a stale
                # registration cannot target a newly reused process group.
                if (
                    os.getpgid(nested_pid) != pgid
                    or os.getsid(nested_pid) != nested_pid
                ):
                    continue
            except ProcessLookupError:
                if _group_probe(pgid) != "present":
                    continue
            except (OSError, OverflowError, ValueError):
                continue
            groups.append(pgid)
        return groups

    def recorded_group_ids() -> list[int]:
        if registration_lock is None:
            return sorted(nested_groups)
        with registration_lock:
            return sorted(nested_groups)

    def join_thread(thread: threading.Thread | None, timeout: float) -> bool:
        if thread is None:
            return True
        try:
            thread.join(timeout=max(0.0, timeout))
        except RuntimeError:
            # A thread object can be present when startup was interrupted before
            # its ``start`` call. It has no work to join in that case.
            return True
        return not thread.is_alive()

    def wait_for_groups(pgids: Sequence[int], timeout: float) -> dict[int, str]:
        tracked = sorted(set(pgids))
        end_monotonic = time.monotonic() + max(0.0, timeout)
        while True:
            statuses = {pgid: _group_probe(pgid) for pgid in tracked}
            if all(status == "absent" for status in statuses.values()):
                return statuses
            remaining = end_monotonic - time.monotonic()
            if remaining <= 0:
                return statuses
            time.sleep(min(POLL_SECONDS, remaining))

    def append_signal(bucket: str, pgid: int, signum: int) -> None:
        state = _group_probe(pgid)
        if state != "present":
            termination[bucket].append({
                "pgid": pgid,
                "status": (
                    "absent" if state == "absent" else f"not_sent_{state}"
                ),
            })
            return
        termination[bucket].append({
            "pgid": pgid,
            "status": _signal_group(pgid, signum),
        })

    # Signal the trusted outer group first. Its source-owned wrapper handler
    # forwards TERM to AGY while the activity reader consumes any registration
    # token already in flight. Snapshotting only before this grace leaks late
    # registrations, especially when the wrapper starts with an empty map.
    initial_nested_targets = registered_groups()
    termination: dict[str, Any] = {
        "reason": reason,
        "wrapper_pgid": process.pid,
        "outer_pgid": process.pid,
        "nested_pgids": list(initial_nested_targets),
        "term": [],
        "kill": [],
    }
    append_signal("term", process.pid, signal.SIGTERM)

    parent_reaped = False
    try:
        process.wait(timeout=term_grace)
        parent_reaped = True
    except subprocess.TimeoutExpired:
        pass
    except (OSError, ValueError):
        parent_reaped = process.poll() is not None

    activity_joined = join_thread(activity_thread, term_grace)

    nested_targets = sorted(set(initial_nested_targets) | set(registered_groups()))
    termination["nested_pgids"] = list(nested_targets)
    for pgid in nested_targets:
        append_signal("term", pgid, signal.SIGTERM)
    nested_term_status = wait_for_groups(nested_targets, term_grace)

    # The outer group may still contain a generic descendant after the parent
    # exits. If it remains present after the TERM grace, escalate the entire
    # trusted group. This is also what closes a retained activity writer.
    outer_term_status = _group_probe(process.pid)
    if outer_term_status == "present":
        append_signal("kill", process.pid, signal.SIGKILL)
    wait_for_groups((process.pid,), kill_grace)[process.pid]
    parent_reaped = parent_reaped or process.poll() is not None

    # A registration can be emitted after the initial drain (or an initially
    # empty map can be populated only during wrapper teardown). Close the pipe
    # by joining the activity reader, then TERM newly observed groups before
    # the final bounded KILL pass.
    activity_joined = join_thread(activity_thread, kill_grace)
    late_active = sorted(set(registered_groups()))
    late_targets = sorted(set(nested_targets) | set(late_active))
    newly_registered = sorted(set(late_active) - set(nested_targets))
    for pgid in newly_registered:
        append_signal("term", pgid, signal.SIGTERM)
    if newly_registered:
        wait_for_groups(newly_registered, kill_grace)
    for pgid in late_targets:
        if _group_probe(pgid) == "present":
            append_signal("kill", pgid, signal.SIGKILL)
    nested_kill_status = wait_for_groups(late_targets, kill_grace)

    # A final bounded join makes stream closure an explicit part of cleanup,
    # rather than allowing a child-retained pipe to outlive the returned result.
    activity_joined = join_thread(activity_thread, kill_grace)
    reader_joined = [join_thread(reader, kill_grace) for reader in stream_readers]
    writer_joined = join_thread(writer, kill_grace)

    recorded_targets = sorted(set(late_targets) | set(recorded_group_ids()))
    termination["nested_pgids"] = recorded_targets
    final_nested_status = {
        pgid: _group_probe(pgid) for pgid in recorded_targets
    }
    outer_final_status = _group_probe(process.pid)
    parent_reaped = parent_reaped or process.poll() is not None
    readers_joined = all(reader_joined)
    streams_joined = readers_joined and writer_joined
    nested_absent = all(
        status == "absent" for status in final_nested_status.values()
    )
    outer_absent = outer_final_status == "absent"
    absence_verified = outer_absent and nested_absent
    failure_reasons: list[str] = []
    if not parent_reaped:
        failure_reasons.append("parent_not_reaped")
    if not activity_joined:
        failure_reasons.append("activity_reader_not_joined")
    if not readers_joined:
        failure_reasons.append("stream_reader_not_joined")
    if not writer_joined:
        failure_reasons.append("stdin_writer_not_joined")
    if not absence_verified:
        failure_reasons.append("process_group_absence_unverified")
    cleanup_proven = not failure_reasons
    cleanup = {
        "wrapper_reaped": parent_reaped,
        "parent_reaped": parent_reaped,
        "nested_groups_registered": len(recorded_targets),
        "nested_groups_targeted": len(late_targets),
        "bounded_term_grace_seconds": term_grace,
        "bounded_kill_grace_seconds": kill_grace,
        "outer_group_absent": outer_absent,
        "nested_groups_absent": nested_absent,
        "verified_absence": absence_verified,
        "cleanup_proven": cleanup_proven,
        "activity_reader_joined": activity_joined,
        "activity_joined": activity_joined,
        "stdout_reader_joined": reader_joined[0] if reader_joined else True,
        "stderr_reader_joined": reader_joined[1] if len(reader_joined) > 1 else True,
        "readers_joined": readers_joined,
        "stream_readers_joined": readers_joined,
        "writer_joined": writer_joined,
        "stdin_writer_joined": writer_joined,
        "streams_joined": streams_joined,
        "outer_group_status": outer_final_status,
        "nested_group_status": {
            str(pgid): status for pgid, status in final_nested_status.items()
        },
        "failure_reasons": failure_reasons,
        "term_nested_group_status": {
            str(pgid): status for pgid, status in nested_term_status.items()
        },
        "kill_nested_group_status": {
            str(pgid): status for pgid, status in nested_kill_status.items()
        },
    }
    termination["sigterm_sent"] = any(
        item["status"] == "sent" for item in termination["term"]
    )
    termination["sigkill_sent"] = any(
        item["status"] == "sent" for item in termination["kill"]
    )
    cleanup["reaped"] = parent_reaped
    return termination, cleanup


def run(
    argv: Sequence[str],
    prompt: bytes,
    cwd: Path,
    max_output: int = MAX_STAGE_OUTPUT_BYTES,
    on_output: Callable[[str, bytes], None] | None = None,
    *,
    liveness_policy: LivenessPolicy | None = None,
    on_notice: Callable[[dict[str, Any]], None] | None = None,
) -> Result:
    # `on_notice` is deliberately separate from `on_output`. Advisory notices are
    # local observations, not provider bytes; routing them through the output
    # observer would break its documented mirror-of-the-record invariant.
    managed_antigravity = _is_managed_antigravity_launcher(argv, cwd)
    policy = _effective_liveness_policy(liveness_policy)
    started = time.time()
    started_monotonic = time.monotonic()
    activity_read_fd: int | None = None
    activity_write_fd: int | None = None
    popen_options: dict[str, Any] = {}
    if managed_antigravity:
        activity_read_fd, activity_write_fd = os.pipe()
        activity_environment = os.environ.copy()
        activity_environment[ACTIVITY_PIPE_ENV] = str(activity_write_fd)
        popen_options.update(
            env=activity_environment,
            pass_fds=(activity_write_fd,),
        )
    try:
        process = subprocess.Popen(
            list(argv),
            cwd=cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            **popen_options,
        )
    except OSError as error:
        if activity_read_fd is not None:
            os.close(activity_read_fd)
        if activity_write_fd is not None:
            os.close(activity_write_fd)
        raise ProviderError(f"cannot launch {argv[0]}: {error}") from error
    finally:
        # The parent never writes to or retains the inherited writer. The
        # wrapper owns its copy and closes it after its supervised run.
        if activity_write_fd is not None:
            try:
                os.close(activity_write_fd)
            except OSError:
                pass

    out_chunks: list[bytes] = []
    err_chunks: list[bytes] = []
    stdout_overflow = [False]
    stderr_overflow = [False]
    observer: list[Callable[[str, bytes], None] | None] = [on_output]
    lock = threading.Lock()
    readers: list[threading.Thread] = []
    writer: threading.Thread | None = None
    activity_thread: threading.Thread | None = None
    nested_groups: dict[int, int] = {}
    stall_warnings = _new_stall_warnings(policy)
    # `reads`/`bytes` count *meaningful* progress only. The per-kind counters are
    # a closed vocabulary of bounded integers; no activity-pipe payload is ever
    # stored, so this evidence cannot leak provider-controlled text.
    activity: dict[str, Any] = {
        "last": started_monotonic,
        "stream": None,
        "reads": 0,
        "bytes": 0,
        "kinds": {
            STREAM_STDOUT: 0,
            STREAM_STDERR: 0,
            "nested.stdout": 0,
            "nested.stderr": 0,
            "nested.protocol": 0,
        },
        "non_progress": {
            "nested.pgid": 0,
            "waiting": 0,
            "unknown": 0,
            "oversized": 0,
            "partial": 0,
            "discarded": 0,
        },
    }

    def note_stream_read(stream: str, chunk: bytes) -> None:
        # This callback runs before capture-cap handling in _drain. It records
        # the read itself, not merely bytes that survived storage/mirroring:
        # real provider output past the capture cap is still real progress.
        now = time.monotonic()
        with lock:
            activity["last"] = now
            activity["stream"] = stream
            activity["reads"] += 1
            activity["bytes"] += len(chunk)
            activity["kinds"][stream] += 1

    if activity_read_fd is not None:
        activity_thread = threading.Thread(
            target=_drain_activity,
            args=(activity_read_fd, process.pid, lock, activity, nested_groups),
            name="provider-antigravity-activity",
            daemon=True,
        )
        activity_thread.start()

    # Everything from here to the poll loop is inside the guard: an interrupt
    # arriving while the threads are still being started would otherwise escape
    # before anything had signalled the child, orphaning its process group.
    try:
        readers = [
            threading.Thread(
                target=_drain,
                args=(process.stdout, STREAM_STDOUT, out_chunks, max_output,
                      stdout_overflow, observer, lock, note_stream_read),
                daemon=True,
            ),
            threading.Thread(
                target=_drain,
                args=(process.stderr, STREAM_STDERR, err_chunks, max_output,
                      stderr_overflow, observer, lock, note_stream_read),
                daemon=True,
            ),
        ]
        for reader in readers:
            reader.start()

        def feed() -> None:
            try:
                assert process.stdin is not None
                process.stdin.write(prompt)
                process.stdin.close()
            except (OSError, ValueError):
                pass

        writer = threading.Thread(target=feed, daemon=True)
        writer.start()

        expired_reason: str | None = None
        expiration_facts: tuple[float, float, float, str | None] | None = None
        # Advisory silence bookkeeping. `next_notice_at` is a silence *age*, and
        # `notice_epoch` is the meaningful-activity timestamp the current schedule
        # belongs to, so fresh progress resets the schedule with the clock.
        next_notice_at = policy.advisory_silence_seconds
        notice_epoch = started_monotonic
        termination: dict[str, Any] | None = None
        cleanup: dict[str, Any] | None = None
        while process.poll() is None:
            # Hard stdout overflow wins a simultaneous liveness race. Stderr
            # overflow remains diagnostic-only, and its reads still count as
            # progress because _drain records activity before discarding.
            with lock:
                overflowed = stdout_overflow[0]
            if overflowed:
                termination, cleanup = _cleanup_process_groups(
                    process,
                    nested_groups,
                    registration_lock=lock,
                    activity_thread=activity_thread,
                    readers=readers,
                    writer=writer,
                    term_grace=KILL_GRACE_SECONDS,
                    kill_grace=KILL_GRACE_SECONDS,
                    reason="stdout_overflow",
                )
                break
            now = time.monotonic()
            with lock:
                last_activity = float(activity["last"])
                last_stream = activity["stream"]
                stdout_overflowed = stdout_overflow[0]
            elapsed = now - started_monotonic
            silent = now - last_activity
            # Re-check overflow under the same snapshot used for the policy so
            # bytes arriving at the cap take precedence over expiry.
            if stdout_overflowed:
                termination, cleanup = _cleanup_process_groups(
                    process,
                    nested_groups,
                    registration_lock=lock,
                    activity_thread=activity_thread,
                    readers=readers,
                    writer=writer,
                    term_grace=KILL_GRACE_SECONDS,
                    kill_grace=KILL_GRACE_SECONDS,
                    reason="stdout_overflow",
                )
                break
            if elapsed >= policy.outer_ceiling_seconds:
                expired_reason = "outer_ceiling"
            elif (
                policy.inactivity_seconds is not None
                and silent >= policy.inactivity_seconds
            ):
                # Production leaves `inactivity_seconds` unset. This branch exists
                # for deterministic tests and any future explicitly accepted
                # policy that injects a finite hard bound.
                expired_reason = "inactivity"
            if expired_reason is None and next_notice_at is not None:
                if last_activity != notice_epoch:
                    # Meaningful progress arrived: restart the advisory schedule.
                    notice_epoch = last_activity
                    next_notice_at = policy.advisory_silence_seconds
                elif silent >= next_notice_at:
                    _record_stall_warning(
                        stall_warnings,
                        elapsed_seconds=elapsed,
                        silent_seconds=silent,
                        last_activity_kind=last_stream,
                        threshold_seconds=next_notice_at,
                        on_notice=on_notice,
                    )
                    next_notice_at = silent + policy.advisory_interval_seconds
            if expired_reason is not None:
                expiration_facts = (elapsed, silent, last_activity, last_stream)
                termination, cleanup = _cleanup_process_groups(
                    process,
                    nested_groups,
                    registration_lock=lock,
                    activity_thread=activity_thread,
                    readers=readers,
                    writer=writer,
                    term_grace=LIVENESS_TERM_GRACE_SECONDS,
                    kill_grace=LIVENESS_KILL_GRACE_SECONDS,
                    reason=expired_reason,
                )
                break
            time.sleep(POLL_SECONDS)
    except BaseException:
        # Ctrl-C reaches the dispatcher, not the provider: the child runs in its
        # own session, so without this the process group would be orphaned and
        # keep running after the dispatcher exited.
        termination, cleanup = _teardown(
            process,
            readers,
            nested_groups=nested_groups,
            registration_lock=lock,
            activity_thread=activity_thread,
            writer=writer,
        )
        with lock:
            observer[0] = None
            interrupted_stdout = b"".join(out_chunks)
            interrupted_stderr = b"".join(err_chunks)
            interrupted_truncated = stdout_overflow[0]
            interrupted_stderr_truncated = stderr_overflow[0]
        # This path builds cleanup from _teardown rather than cleanup_facts, so
        # the advisory evidence has to be attached explicitly to survive Ctrl-C.
        cleanup = {**cleanup, "stall_warnings": stall_warnings}
        raise ProviderInterrupted(
            interrupted_stdout,
            interrupted_stderr,
            interrupted_truncated,
            interrupted_stderr_truncated,
            termination=termination,
            cleanup=cleanup,
        )

    # Cleanup is deliberately before stream joins. A normally exiting provider
    # can leave a descendant holding stdout/stderr open; joining first would
    # wait on the retained pipe and then return a false-success Result.
    if termination is None or cleanup is None:
        termination, cleanup = _cleanup_process_groups(
            process,
            nested_groups,
            registration_lock=lock,
            activity_thread=activity_thread,
            readers=readers,
            writer=writer,
            term_grace=KILL_GRACE_SECONDS,
            kill_grace=KILL_GRACE_SECONDS,
            reason="normal_completion",
        )
    exit_code = process.poll()
    # `or` would rewrite a clean exit 0 — the process can exit normally during
    # the termination race — into a fabricated kill status. A still-unreaped
    # parent is instead part of the typed cleanup failure below.
    if exit_code is None and cleanup.get("cleanup_proven"):
        exit_code = -signal.SIGKILL
    with lock:
        # Retiring the observer and snapshotting together is what makes the
        # mirrored bytes and the stored bytes the same set even if a reader
        # thread outlived its join.
        observer[0] = None
        stdout = b"".join(out_chunks)
        stderr = b"".join(err_chunks)
        truncated = stdout_overflow[0]
        stderr_truncated = stderr_overflow[0]
        overflowed = truncated
        activity_reads = activity["reads"]
        activity_bytes = activity["bytes"]
        last_activity = float(activity["last"])
        last_stream = activity["stream"]
        activity_counts = _activity_counts(activity)
    cleanup_facts = {
        **cleanup,
        "termination": termination,
        # These two keep their established names and now count *meaningful*
        # progress only; non-progress noise is reported under activity_counts.
        "activity_reads": activity_reads,
        "activity_bytes": activity_bytes,
        "activity_counts": activity_counts,
        "last_activity_kind": last_stream,
        "last_activity_age_seconds": max(0.0, time.monotonic() - last_activity),
        "stall_warnings": stall_warnings,
    }
    # A hard output cap wins if the final drain discovered it while liveness
    # teardown was in progress. This keeps the established Result contract and
    # prevents a race from turning an output-limit failure into expiry.
    if overflowed:
        if not cleanup_facts.get("cleanup_proven"):
            raise ProviderCleanupFailed(
                stdout,
                stderr,
                True,
                stderr_truncated,
                cleanup=cleanup_facts,
                termination=termination,
                exit_code=exit_code,
                started=started,
                ended=time.time(),
            )
        return Result(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            truncated=True,
            started=started,
            ended=time.time(),
            stderr_truncated=stderr_truncated,
            cleanup=cleanup_facts,
        )
    if expired_reason is not None and expiration_facts is not None:
        elapsed, silent, detected_last_activity, detected_stream = expiration_facts
        assert termination is not None and cleanup is not None
        raise ProviderLivenessExpired(
            stdout,
            stderr,
            False,
            stderr_truncated,
            policy=policy,
            reason=expired_reason,
            elapsed_seconds=elapsed,
            silent_seconds=silent,
            last_activity_monotonic=detected_last_activity,
            last_activity_stream=detected_stream,
            termination=termination,
            cleanup=cleanup_facts,
            activity_counts=activity_counts,
        )
    if not cleanup_facts.get("cleanup_proven"):
        raise ProviderCleanupFailed(
            stdout,
            stderr,
            truncated,
            stderr_truncated,
            cleanup=cleanup_facts,
            termination=termination,
            exit_code=exit_code,
            started=started,
            ended=time.time(),
        )
    return Result(
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        truncated=truncated,
        started=started,
        ended=time.time(),
        stderr_truncated=stderr_truncated,
        cleanup=cleanup_facts,
    )


def _teardown(
    process: subprocess.Popen,
    readers: list[threading.Thread],
    *,
    nested_groups: dict[int, int] | None = None,
    registration_lock: threading.Lock | None = None,
    activity_thread: threading.Thread | None = None,
    writer: threading.Thread | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Tear down an interrupted stage, absorbing further interrupts.

    An operator who presses Ctrl-C twice must still get a dead process group;
    without this, the second interrupt lands inside the first one's teardown and
    leaves the provider running. Attempts are bounded so a persistently failing
    teardown cannot spin.
    """
    groups = nested_groups if nested_groups is not None else {}
    last_termination: dict[str, Any] = {
        "reason": "operator_interrupt",
        "wrapper_pgid": process.pid,
        "outer_pgid": process.pid,
        "nested_pgids": [],
        "term": [],
        "kill": [],
    }
    last_cleanup: dict[str, Any] = {
        "cleanup_proven": False,
        "failure_reasons": ["cleanup_attempt_not_completed"],
        "parent_reaped": False,
        "wrapper_reaped": False,
        "activity_reader_joined": False,
        "readers_joined": False,
        "writer_joined": False,
        "outer_group_absent": False,
        "nested_groups_absent": False,
        "verified_absence": False,
    }
    for _ in range(TEARDOWN_ATTEMPTS):
        try:
            return _cleanup_process_groups(
                process,
                groups,
                registration_lock=registration_lock,
                activity_thread=activity_thread,
                readers=readers,
                writer=writer,
                term_grace=KILL_GRACE_SECONDS,
                kill_grace=KILL_GRACE_SECONDS,
                reason="operator_interrupt",
            )
        except BaseException:
            continue
    return last_termination, last_cleanup


def _terminate(process: subprocess.Popen) -> None:
    for signum in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(process.pid, signum)
        except (ProcessLookupError, PermissionError):
            return
        try:
            process.wait(timeout=KILL_GRACE_SECONDS)
            return
        except subprocess.TimeoutExpired:
            continue
