"""Durable provider-launch evidence and the pre-exec launch gate.

One run-owned record per parent provider attempt, ``<prefix>.provider-launch.json``,
is the recovery authority for whether a provider could still be running after
its dispatcher vanished. It is owned by the provider execution path, never by
context, observations or a provider self-report.

Invariant: a provider cannot begin execution unless durable evidence naming its
process and process group already exists. The dispatcher launches a tiny gate
(this file run as a script) in a new session. The gate records and fsyncs its
own pid, process group and process identity, reports readiness, and blocks. The
parent re-verifies those facts, makes ``authorized`` durable and only then sends
the proceed byte; the gate then ``exec``s the provider in the same process, so
pid, group and identity are unchanged. If the parent dies before proceeding,
its non-inheritable write end closes, the gate reads EOF and exits without
``exec``. No parent-death signal is involved, so the proof holds on Darwin and
Linux alike.

The record keeps bounded identities only: no prompt, stdin, environment or
argv beyond the executable path and an argv digest.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import errno
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
import sys
from typing import Any, Callable, Iterator, Mapping, Sequence

SCHEMA = "apgr-provider-launch-v1"
SUFFIX = ".provider-launch.json"
STATE_CONTRACT = "provider_launch_contract"
STATE_LAUNCHES = "provider_launches"

PREPARED = "prepared"
NOT_STARTED = "not_started"
AWAITING = "awaiting_authorization"
WITHDRAWN = "withdrawn_before_authorization"
AUTHORIZED = "authorized"
EXEC_CONFIRMED = "exec_confirmed"
EXEC_FAILED = "exec_failed"
RETURNED = "returned"
# Phase -> recovery classification. Every phase with process facts requires
# proof that the recorded process and process group ended.
CLASSIFICATION = {
    PREPARED: "not_started",
    NOT_STARTED: "not_started",
    AWAITING: "not_authorized",
    WITHDRAWN: "not_authorized",
    AUTHORIZED: "started",
    EXEC_CONFIRMED: "started",
    EXEC_FAILED: "returned",
    RETURNED: "returned",
}
PROCESS_PHASES = frozenset(CLASSIFICATION) - {PREPARED, NOT_STARTED}
RECORD_KEYS = frozenset({"schema", "phase", "binding", "exec", "process", "terminal"})
BINDING_KEYS = frozenset({"run_id", "stage", "prefix", "attempt_id", "index",
                          "invocation_kind", "route", "launch_id"})
PROCESS_KEYS = frozenset({"pid", "process_group", "session", "process_identity"})
EXEC_KEYS = frozenset({"executable", "argv_sha256"})
TERMINAL_KEYS = frozenset({"exit_code", "reaped"})
MAX_RECORD_BYTES = 16 * 1024
GATE_TIMEOUT_SECONDS = 30.0

# Gate exit codes; the gate never writes to the provider's streams.
GATE_EVIDENCE_INVALID = 120
GATE_IDENTITY_UNAVAILABLE = 121
GATE_SESSION_MISMATCH = 122
GATE_NOT_AUTHORIZED = 125
GATE_EXEC_FAILED = 127


class LaunchEvidenceError(RuntimeError):
    """Launch evidence could not be created or proven; the caller fails closed."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


# -- durable writer ------------------------------------------------------------

def _encode(record: dict[str, Any]) -> bytes:
    return (json.dumps(record, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _fsync_directory(directory: Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_descriptor(descriptor: int, data: bytes) -> None:
    try:
        view = memoryview(data)
        while view:
            view = view[os.write(descriptor, view):]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _create(path: Path, record: dict[str, Any]) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    _write_descriptor(os.open(path, flags, 0o600), _encode(record))
    _fsync_directory(path.parent)


def _replace(path: Path, record: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    try:
        _write_descriptor(os.open(temporary, flags, 0o600), _encode(record))
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    _fsync_directory(path.parent)


def _read_bytes(path: Path) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise ValueError("launch evidence is not a regular file")
        data = handle.read(MAX_RECORD_BYTES + 1)
    if len(data) > MAX_RECORD_BYTES:
        raise ValueError("launch evidence exceeds its bound")
    return data


def _parse(data: bytes) -> dict[str, Any]:
    value = json.loads(data)
    if not isinstance(value, dict):
        raise ValueError("launch evidence is not an object")
    return value


def _read(path: Path) -> dict[str, Any]:
    return _parse(_read_bytes(path))


# -- parent side ---------------------------------------------------------------

class Binding:
    """One prepared launch attempt; consumable by exactly one gated spawn."""

    def __init__(self, path: Path, record: dict[str, Any]) -> None:
        self.path = path
        self.record = record
        self.consumed = False
        self.process: Any = None

    @property
    def launch_id(self) -> str:
        return self.record["binding"]["launch_id"]

    def write(self, phase: str, **fields: Any) -> None:
        self.record = {**self.record, **fields, "phase": phase}
        _replace(self.path, self.record)


BOUND: ContextVar[Binding | None] = ContextVar("provider_launch_binding", default=None)


def evidence_name(prefix: str) -> str:
    return prefix + SUFFIX


def prepare(
    run_dir: Path, *, run_id: str, stage: str, prefix: str, index: int,
    invocation_kind: str, provider: str, profile: str,
) -> Binding:
    """Create the ``prepared`` record before any provider can be spawned."""
    path = Path(run_dir).resolve() / evidence_name(prefix)
    record = {
        "schema": SCHEMA,
        "phase": PREPARED,
        "binding": {
            "run_id": run_id, "stage": stage, "prefix": prefix,
            "attempt_id": f"att-{run_id}-{stage}-{index}", "index": index,
            "invocation_kind": invocation_kind,
            "route": {"provider": provider, "profile": profile},
            "launch_id": secrets.token_hex(16),
        },
        "exec": None, "process": None, "terminal": None,
    }
    try:
        _create(path, record)
    except FileExistsError as error:
        raise LaunchEvidenceError("PROVIDER_LAUNCH_EVIDENCE_EXISTS", path.name) from error
    except OSError as error:
        raise LaunchEvidenceError("PROVIDER_LAUNCH_EVIDENCE_UNAVAILABLE",
                                  f"{path.name}: {type(error).__name__}") from error
    return Binding(path, record)


@contextmanager
def bound(binding: Binding) -> Iterator[Binding]:
    token = BOUND.set(binding)
    try:
        yield binding
    finally:
        BOUND.reset(token)


def _await(descriptor: int, deadline: float) -> bytes:
    """Read until EOF or deadline; the gate writes at most a few bytes."""
    import select
    import time

    data = b""
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("provider launch gate did not respond")
        readable, _, _ = select.select([descriptor], [], [], remaining)
        if not readable:
            continue
        chunk = os.read(descriptor, 64)
        if not chunk:
            return data
        data += chunk
        if data[:1] == b"R" or len(data) > 32:
            return data


def _close(*descriptors: int | None) -> None:
    for descriptor in descriptors:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass


def spawn(
    binding: Binding,
    argv: Sequence[str],
    popen: Callable[[list[str], tuple[int, ...]], Any],
    *,
    before_authorize: Callable[[Any], None] | None = None,
    terminate: Callable[[Any], None],
    environment: Mapping[str, str] | None = None,
) -> Any:
    """Start ``argv`` behind the gate; return only once the provider exec'd.

    ``popen(args, pass_fds)`` must start the gate as a new session leader
    with ``environment`` (default: this process's). Any failure before the
    proceed byte leaves the provider unexecuted; the gate is terminated and
    reaped, and the record says so.
    """
    import time

    if binding.consumed:
        raise LaunchEvidenceError("PROVIDER_LAUNCH_EVIDENCE_CONSUMED", binding.path.name)
    binding.consumed = True
    # The gate interpreter may coerce a C locale by exporting LC_CTYPE
    # (PEP 538); it restores the provider's exact value before exec.
    ctype = (os.environ if environment is None else environment).get("LC_CTYPE")
    ready_read, ready_write = os.pipe()
    proceed_read, proceed_write = os.pipe()
    gate = [
        sys.executable, "-I", "-B", os.fspath(Path(__file__).resolve()), "gate",
        "--evidence", os.fspath(binding.path), "--launch-id", binding.launch_id,
        "--ready-fd", str(ready_write), "--proceed-fd", str(proceed_read),
        "--lc-ctype-state", "unset" if ctype is None else "set", "--lc-ctype", ctype or "",
        "--", *argv,
    ]
    try:
        process = popen(gate, (ready_write, proceed_read))
    except BaseException:
        _close(ready_read, ready_write, proceed_read, proceed_write)
        try:
            binding.write(NOT_STARTED)
        except OSError:
            pass
        raise
    _close(ready_write, proceed_read)
    binding.process = process
    authorized = False
    try:
        deadline = time.monotonic() + GATE_TIMEOUT_SECONDS
        if _await(ready_read, deadline)[:1] != b"R":
            raise LaunchEvidenceError("PROVIDER_LAUNCH_GATE_REFUSED",
                                      f"gate exited before readiness ({process.wait()})")
        from controller_generation_process import process_identity

        observed = _read(binding.path)
        facts = observed.get("process")
        if (observed.get("phase") != AWAITING
                or observed.get("binding") != binding.record["binding"]
                or not isinstance(facts, dict)
                or facts.get("pid") != process.pid
                or facts.get("process_group") != process.pid
                or facts.get("session") != process.pid
                or facts.get("process_identity") is None
                or facts.get("process_identity") != process_identity(process.pid)):
            raise LaunchEvidenceError("PROVIDER_LAUNCH_EVIDENCE_INVALID",
                                      "gate facts do not identify the spawned process")
        binding.record = observed
        if before_authorize is not None:
            before_authorize(process)
        binding.write(AUTHORIZED)
        authorized = True
        os.write(proceed_write, b"P")
        _close(proceed_write)
        proceed_write = None
        outcome = _await(ready_read, time.monotonic() + GATE_TIMEOUT_SECONDS)
        if outcome:
            code = process.wait()
            binding.write(EXEC_FAILED, terminal={"exit_code": code, "reaped": True})
            detail = outcome[1:].decode("ascii", "replace")
            number = int(detail) if detail.isdecimal() else errno.EIO
            raise OSError(number, os.strerror(number))
        binding.write(EXEC_CONFIRMED)
        return process
    except BaseException:
        _close(proceed_write)
        proceed_write = None
        terminate(process)
        if not authorized and process.poll() is not None:
            _withdraw(binding, process.returncode)
        raise
    finally:
        _close(ready_read, proceed_write)


def _withdraw(binding: Binding, exit_code: int) -> None:
    """Record a reaped, never-authorized gate from the file's actual phase."""
    try:
        current = _read(binding.path)
        if current.get("binding") != binding.record["binding"]:
            return
        terminal = {"terminal": {"exit_code": exit_code, "reaped": True}}
        if current.get("phase") == AWAITING:
            binding.record = current
            binding.write(WITHDRAWN, **terminal)
        elif current.get("phase") == PREPARED:
            binding.write(NOT_STARTED, **terminal)
    except (OSError, ValueError):
        pass


def record_terminal(binding: Binding) -> None:
    """Best-effort terminal fact once the provider was reaped; never masks a result."""
    process = binding.process
    if process is None or binding.record.get("phase") != EXEC_CONFIRMED:
        return
    code = process.poll()
    if code is None:
        return
    try:
        binding.write(RETURNED, terminal={"exit_code": code, "reaped": True})
    except (OSError, ValueError):
        pass


# -- gate (child side) -----------------------------------------------------------

def _gate(arguments: list[str]) -> int:
    import signal

    try:
        split = arguments.index("--")
        options, argv = arguments[:split], arguments[split + 1:]
        values = dict(zip(options[0::2], options[1::2]))
        path = Path(values["--evidence"])
        launch_id = values["--launch-id"]
        ready = int(values["--ready-fd"])
        proceed = int(values["--proceed-fd"])
        ctype_state, ctype = values["--lc-ctype-state"], values["--lc-ctype"]
    except (ValueError, KeyError):
        return GATE_EVIDENCE_INVALID
    if not argv or not path.is_absolute() or ctype_state not in ("set", "unset"):
        return GATE_EVIDENCE_INVALID
    from controller_generation_process import process_identity

    pid = os.getpid()
    if os.getpgid(0) != pid or os.getsid(0) != pid:
        return GATE_SESSION_MISMATCH
    identity = process_identity(pid)
    if not isinstance(identity, str) or not identity.startswith(f"{pid}:"):
        return GATE_IDENTITY_UNAVAILABLE
    try:
        record = _read(path)
        if (record.get("schema") != SCHEMA or record.get("phase") != PREPARED
                or not isinstance(record.get("binding"), dict)
                or record["binding"].get("launch_id") != launch_id):
            return GATE_EVIDENCE_INVALID
        record = {
            **record, "phase": AWAITING,
            "exec": {"executable": argv[0],
                     "argv_sha256": hashlib.sha256(json.dumps(argv).encode("utf-8")).hexdigest()},
            "process": {"pid": pid, "process_group": pid, "session": pid,
                        "process_identity": identity},
        }
        _replace(path, record)
    except (OSError, ValueError):
        return GATE_EVIDENCE_INVALID
    try:
        os.set_inheritable(ready, False)  # Closed by a successful exec.
        os.write(ready, b"R")
        authorization = os.read(proceed, 1)
    except OSError:
        return GATE_NOT_AUTHORIZED
    if authorization != b"P":
        return GATE_NOT_AUTHORIZED
    os.close(proceed)
    # The interpreter ignores these; the provider must inherit the defaults
    # that subprocess's restore_signals would otherwise have given it.
    for name in ("SIGPIPE", "SIGXFSZ"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), signal.SIG_DFL)
    if ctype_state == "set":
        os.environ["LC_CTYPE"] = ctype
    else:
        os.environ.pop("LC_CTYPE", None)
    try:
        os.execvp(argv[0], argv)
    except OSError as error:
        try:
            os.write(ready, b"E%d" % (error.errno or errno.EIO))
        except OSError:
            pass
        return GATE_EXEC_FAILED
    return GATE_EXEC_FAILED  # pragma: no cover - execvp does not return


# -- recovery proof (read-only) ----------------------------------------------------

def _invalid(detail: str) -> LaunchEvidenceError:
    return LaunchEvidenceError("RESUME_PROVIDER_LAUNCH_EVIDENCE_INVALID", detail)


def _refused(detail: str) -> LaunchEvidenceError:
    return LaunchEvidenceError("RESUME_RECOVERY_REFUSED", detail)


def _positive(value: Any) -> bool:
    return type(value) is int and value > 0


def _expected_index(lifecycle: Any, stage: str, kind: str) -> int | None:
    names = lifecycle.stage_names
    if stage not in names:
        return None
    position = names.index(stage) + 1
    if kind == "semantic":
        return position
    if kind == "auxiliary_review_retry":
        return position + lifecycle.expected_provider_invocations
    return None


def _validate(
    record: Any, prefix: str, state: dict[str, Any], routes: Callable[[str], Any], lifecycle: Any,
) -> dict[str, Any]:
    name = evidence_name(prefix)
    if not isinstance(record, dict) or set(record) != RECORD_KEYS or record["schema"] != SCHEMA:
        raise _invalid(f"{name} is not an exact {SCHEMA} record")
    phase, binding = record["phase"], record["binding"]
    if phase not in CLASSIFICATION:
        raise _invalid(f"{name} has unknown phase {phase!r}")
    if not isinstance(binding, dict) or set(binding) != BINDING_KEYS:
        raise _invalid(f"{name} binding is not exact")
    stage, index, kind, route = (binding["stage"], binding["index"],
                                 binding["invocation_kind"], binding["route"])
    launch_id = binding["launch_id"]
    if (binding["prefix"] != prefix or binding["run_id"] != state.get("run_id")
            or not isinstance(stage, str) or not _positive(index) or not isinstance(kind, str)
            or binding["attempt_id"] != f"att-{state.get('run_id')}-{stage}-{index}"
            or not isinstance(launch_id, str) or len(launch_id) != 32
            or any(c not in "0123456789abcdef" for c in launch_id)
            or not isinstance(route, dict) or set(route) != {"provider", "profile"}
            or not all(isinstance(route[key], str) and route[key] for key in route)):
        raise _invalid(f"{name} is bound to another run, attempt or route")
    expected = _expected_index(lifecycle, stage, kind)
    if kind in ("semantic", "auxiliary_review_retry"):
        stage_prefix = lifecycle.prefixes.get(stage)
        wanted = stage_prefix if kind == "semantic" else f"{stage_prefix}.review-retry"
        effective = routes(stage)
        if (stage_prefix is None or prefix != wanted or index != expected
                or not isinstance(effective, dict)
                or {key: effective.get(key) for key in ("provider", "profile")} != route):
            raise _invalid(f"{name} does not match its lifecycle stage and route")
    facts, execution, terminal = record["process"], record["exec"], record["terminal"]
    if phase in PROCESS_PHASES:
        if (not isinstance(facts, dict) or set(facts) != PROCESS_KEYS
                or not _positive(facts["pid"])
                or facts["process_group"] != facts["pid"] or facts["session"] != facts["pid"]
                or not isinstance(facts["process_identity"], str)
                or not facts["process_identity"].startswith(f"{facts['pid']}:")):
            raise _invalid(f"{name} lacks exact process facts for phase {phase}")
        if (not isinstance(execution, dict) or set(execution) != EXEC_KEYS
                or not all(isinstance(execution[key], str) for key in EXEC_KEYS)):
            raise _invalid(f"{name} lacks its exec binding")
    elif facts is not None or execution is not None:
        raise _invalid(f"{name} phase {phase} cannot carry process facts")
    if terminal is not None and (not isinstance(terminal, dict) or set(terminal) != TERMINAL_KEYS):
        raise _invalid(f"{name} terminal facts are not exact")
    return record


def _process_ended(pid: int, group: int, identity: str) -> str | None:
    """None when the recorded incarnation provably ended; otherwise a reason.

    Existence probes only; nothing is ever signalled. A pid now held by a newer
    incarnation proves the original ended: POSIX never reuses a pid while a
    process group with that id still exists.
    """
    from controller_generation_process import identity_supersedes, process_identity

    observed = process_identity(pid)
    if observed is not None:
        if observed == identity:
            return "provider_process_live"
        if identity_supersedes(pid, identity, observed):
            return None
        return "provider_process_identity_ambiguous"
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        pass
    except OSError:
        return "provider_process_identity_ambiguous"
    else:
        return "provider_process_identity_ambiguous"
    try:
        os.killpg(group, 0)
    except ProcessLookupError:
        return None
    except OSError:
        pass
    return "provider_process_group_live"


def recovery_proof(
    source: Path, state: dict[str, Any], interrupted_stage: str | None, *,
    routes: Callable[[str], Any], lifecycle: Any,
) -> dict[str, Any] | None:
    """Read-only proof that no parent provider of ``source`` can still run.

    Returns the deterministic receipt view, or None for a pre-contract source
    that had nothing in flight. Raises before any recovery write otherwise.
    """
    contract = state.get(STATE_CONTRACT)
    if contract is None:
        if interrupted_stage is None:
            return None
        raise _refused(
            "provider_launch_contract_absent: this source predates durable provider-launch "
            "evidence, so a surviving provider cannot be excluded; use the manager lane")
    if contract != SCHEMA:
        raise _invalid(f"unknown provider launch contract {contract!r}")
    launches = state.get(STATE_LAUNCHES)
    if (not isinstance(launches, list) or any(not isinstance(item, str) or not item for item in launches)
            or len(set(launches)) != len(launches)):
        raise _invalid("state provider_launches is not an exact list of attempt prefixes")
    present: dict[str, Path] = {}
    for path in sorted(source.iterdir()):
        if path.name.startswith(".") or not path.name.endswith(SUFFIX):
            continue
        if not stat.S_ISREG(os.lstat(path).st_mode):
            raise _invalid(f"{path.name} is not a regular file")
        present[path.name[:-len(SUFFIX)]] = path
    missing = sorted(set(launches) - set(present))
    if missing:
        raise _invalid(f"required launch evidence is missing: {evidence_name(missing[0])}")
    if (interrupted_stage is not None and not state.get("resumed")
            and lifecycle.prefixes.get(interrupted_stage) not in launches):
        raise _invalid("interrupted stage was invoked without recorded launch evidence")
    records = []
    for prefix, path in present.items():
        try:
            # One read: the receipt digest binds exactly the validated bytes.
            raw = _read_bytes(path)
            record = _validate(_parse(raw), prefix, state, routes, lifecycle)
        except (OSError, ValueError, UnicodeError) as error:
            raise _invalid(f"{path.name} is unreadable: {type(error).__name__}") from error
        phase = record["phase"]
        if prefix not in launches and phase != PREPARED:
            raise _invalid(f"{path.name} advanced past prepared without a state record")
        if phase in PROCESS_PHASES:
            facts = record["process"]
            reason = _process_ended(facts["pid"], facts["process_group"], facts["process_identity"])
            if reason is not None:
                raise _refused(f"{reason}: {path.name} pid {facts['pid']} is not proven ended")
        records.append({"name": path.name, "sha256": hashlib.sha256(raw).hexdigest(),
                        "phase": phase, "classification": CLASSIFICATION[phase]})
    return {"contract": SCHEMA, "records": records}


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "gate":
        sys.exit(GATE_EVIDENCE_INVALID)
    # Isolated mode (-I) omits the script directory; bind the sibling helper
    # explicitly from this file's own location.
    sys.path.insert(0, os.fspath(Path(__file__).resolve().parents[1]))
    sys.exit(_gate(sys.argv[2:]))
