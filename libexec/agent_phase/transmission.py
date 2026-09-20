"""Controlled launch observations, independent of provider/model consumption.

One recorder is selected by context_adapter.invoke for V1 and V2. Only the
process owner calls its write/start methods. Prepared plans never call them.
Observation failure is diagnostic for normal dispatch and incomplete H evidence.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import threading
import uuid

MAX_BYTES = 16 << 20
SCOPE_ENV = "APGR_CONTROLLED_TRANSMISSION_SCOPE"


def direct_bytes(path, *, utf8=True, max_bytes=MAX_BYTES):
    path = Path(path)
    if not path.is_absolute() or path.resolve() != path:
        raise ValueError("transport reference must be a physical absolute path")
    owner = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=owner)
            os.close(owner)
            owner = child
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=owner)
    finally:
        os.close(owner)
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > max_bytes:
            raise ValueError("unsafe transport reference")
        data = stream.read(max_bytes + 1)
        after = os.fstat(stream.fileno())
    entry = path.lstat()
    key = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
    if len(data) > max_bytes or not key(before) == key(after) == key(entry):
        raise ValueError("transport reference changed")
    if utf8:
        data.decode("utf-8")
    return data


class Transport:
    def __init__(self, prepared):
        self.prepared = prepared
        self.events = []
        self.diagnostics = []
        self.started = False
        self.stdin_written = False
        self.lock = threading.Lock()
        self.launcher = None
        self.references = {}

    def environment(self, argv, environment):
        names = {Path(a).name for a in argv[:2]}
        self.launcher = next((name for name in ("claude-profile", "antigravity-profile") if name in names), None)
        if self.launcher and not (self.prepared.get("evaluation_transport") is True
                                  or self.prepared["record"].get("requested_mode") == "adaptive"):
            self.diagnostics.append("native launch observation requires evaluation or adaptive opt-in")
            self.launcher = None
        result = dict(environment)
        # Never inherit an unrelated attempt's measurement scope.
        result.pop(SCOPE_ENV, None)
        for i, arg in enumerate(argv):
            if i and argv[i-1] in ("--mcp-config", "--settings") and not arg.lstrip().startswith("{"):
                try:
                    self.references[arg] = direct_bytes(arg)
                except (OSError, ValueError, UnicodeError) as error:
                    self.diagnostics.append(type(error).__name__)
        if self.launcher:
            scope = {"path": str(self.prepared["path"]),
                                           "reference": self.prepared["reference"],
                                           "claude_read_stream": self.prepared.get("claude_read_stream"),
                                           "record": {k: self.prepared["record"][k] for k in ("run_id", "binding_id", "attempt_id")}}
            handoff = self.prepared["record"].get("acquisition", {}).get("wrapper_handoff")
            if handoff and self.prepared["record"].get("effective_mode") == "adaptive":
                from .claude_acquisition_handoff import identity
                scope["handoff"] = {"path": handoff, **identity(direct_bytes(handoff))}
            context_handoff = self.prepared["record"].get("acquisition", {}).get("context_handoff")
            if context_handoff and self.prepared["record"].get("effective_mode") == "adaptive":
                from .claude_context_acquisition import identity
                try:
                    scope["context_acquisition"] = {"path": context_handoff, **identity(direct_bytes(context_handoff))}
                except (OSError, ValueError) as error:
                    # The wrapper then refuses before starting Claude; never replayed.
                    self.diagnostics.append("context acquisition handoff unreadable: " + type(error).__name__)
            instructions = self.prepared["record"].get("instruction_projection") or {}
            if instructions.get("status") == "projected" and self.prepared["record"].get("effective_mode") == "adaptive":
                from .claude_context_acquisition import identity
                path = instructions.get("handoff", {}).get("path")
                try:
                    scope["instruction_projection"] = {"path": path, **identity(direct_bytes(path, utf8=False))}
                except (OSError, ValueError, TypeError) as error:
                    # The wrapper then refuses before starting Claude; never replayed.
                    self.diagnostics.append("instruction projection handoff unreadable: " + type(error).__name__)
            result[SCOPE_ENV] = json.dumps(scope)
        return result

    def emit(self, payload, channel, provenance, kind, **facts):
        payload.decode("utf-8")
        record = self.prepared["record"]
        scope = {k: record[k] for k in ("run_id", "binding_id", "attempt_id")}
        event_id = hashlib.sha256(json.dumps([*scope.values(), uuid.uuid4().hex]).encode()).hexdigest()
        self.events.append({"schema": "apg.acquisition-event/v1", **scope,
                            "event_id": event_id, "kind": "initial_delivered", "phase": "initial",
                            "channel": channel, "controlled_bytes": len(payload),
                            "payload_sha256": hashlib.sha256(payload).hexdigest(),
                            "provenance": provenance, "observation_kind": kind,
                            "provider_observed": None, "model_observed": None, **facts})

    def process_started(self, argv):
        with self.lock:
            if self.started:
                self.diagnostics.append("multiple process starts in one attempt")
                return
            self.started = True
            try:
                # These count actual argument bytes, not JSON reconstructions of
                # argv. Flags, paths, and overlapping component views are facts.
                for i, arg in enumerate(argv):
                    if arg.startswith("developer_instructions="):
                        self.emit(arg.encode(), "instructions", "provider-argv", "process_argv", argv_index=i)
                    elif arg.startswith("mcp_servers.apgr="):
                        self.emit(arg.encode(), "mcp_configuration", "provider-argv", "process_argv", argv_index=i)
                    elif i and argv[i-1] in ("--append-system-prompt", "--system-prompt"):
                        self.emit(arg.encode(), "instructions", "provider-argv", "process_argv", argv_index=i)
                    elif i and argv[i-1] in ("--mcp-config", "--settings"):
                        channel = "instructions" if argv[i-1] == "--settings" else "mcp_configuration"
                        if arg.lstrip().startswith("{"):
                            self.emit(arg.encode(), channel, "provider-argv", "process_argv", argv_index=i)
                        else:
                            # The process receives the reference, not these bytes.
                            # H explicitly binds controlled config bytes to that
                            # handoff; neither file read nor model use is inferred.
                            data = direct_bytes(arg)
                            if arg in self.references and self.references[arg] != data:
                                raise ValueError("configuration changed across process start")
                            self.emit(data, channel, "provider-settings-reference" if channel == "instructions" else "run-config-reference", "process_path_handoff",
                                      reference=arg, argv_index=i, reference_bytes=len(arg.encode()))
            except (OSError, ValueError, UnicodeError) as error:
                self.diagnostics.append(type(error).__name__)

    def wrote_stdin(self, payload):
        with self.lock:
            try:
                if self.stdin_written:
                    raise ValueError("duplicate stdin observation")
                components = list(self.prepared["record"].get("instruction_plan", {}).get("components", []))
                plan = self.prepared["record"].get("prospective_plan") or {}
                if self.prepared["record"].get("effective_mode") == "adaptive" and plan.get("selected_snapshots"):
                    # The selected bodies are serialized inside this one prompt.
                    # Source views distinguish them, but never add another count.
                    planned = plan["payload"].encode()
                    if not payload.startswith(planned):
                        raise ValueError("selected skill transport differs from plan")
                    import base64
                    from .acquisition_records import _pairs
                    envelope = planned.rsplit(b"\n<apgr-skills>\n", 1)[1].split(b"\n</apgr-skills>\n", 1)[0]
                    rows = json.loads(envelope, object_pairs_hook=_pairs)
                    for snapshot in plan["selected_snapshots"]:
                        body = base64.b64decode(snapshot["body"], validate=True)
                        matches = [r for r in rows if r["id"] == snapshot["qualified_id"]]
                        if len(matches) != 1 or matches[0]["text"].encode() != body:
                            raise ValueError("selected source body not witnessed in prompt")
                        components.append({"kind": "selected-skill-source-view", "id": snapshot["qualified_id"],
                                           "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                                           "boundary": "source body serialized in the measured prompt; not an extra transmission"})
                self.emit(payload, "prompt", "rendered-runner-stdin", "complete_pipe_write", components=components)
                self.stdin_written = True
            except (ValueError, UnicodeError, KeyError, IndexError, TypeError) as error:
                self.diagnostics.append(type(error).__name__)

    def finish(self):
        from .context_adapter import _write_new
        path = self.prepared["path"]
        if self.launcher:
            try:
                from .acquisition_records import _pairs
                native = json.loads(direct_bytes(path.with_name(path.name.replace(".context-plan.json", ".context-launcher-deliveries.json"))), object_pairs_hook=_pairs)
                if native["plan"] != self.prepared["reference"] or native["coverage"] != "complete":
                    raise ValueError("incomplete downstream transport")
                if self.launcher == "antigravity-profile":
                    # The wrapper transforms stdin into the final -p argument.
                    # Only that final representation counts as a transmission.
                    parents = [e for e in self.events if e["channel"] == "prompt"]
                    prompts = [e for e in native["events"] if e["channel"] == "prompt"]
                    if len(parents) != 1 or len(prompts) != 1:
                        raise ValueError("ambiguous transformed prompt")
                    parent, prompt = parents[0], prompts[0]
                    if prompt.get("input_view") != {"bytes": parent["controlled_bytes"], "sha256": parent["payload_sha256"]}:
                        raise ValueError("transformed prompt lost controlled input")
                    prompt["components"] = [*parent.get("components", []), *prompt.get("components", [])]
                    self.events = [e for e in self.events if e["channel"] != "prompt"]
                self.events.extend(native["events"])
            except (OSError, ValueError, KeyError, TypeError):
                self.diagnostics.append("downstream launcher additions not witnessed")
        value = {"schema": "apg.controlled-transmissions/v1", "plan": self.prepared["reference"],
                 "boundary": "APGR runner process argv and complete stdin pipe write",
                 "events": self.events, "diagnostics": self.diagnostics,
                 "coverage": "complete" if self.started and self.stdin_written and not self.diagnostics else "incomplete",
                 "model_observed": None}
        try:
            _write_new(path.with_name(path.name.replace(".context-plan.json", ".context-deliveries.json")), value)
        except (OSError, ValueError):
            # Absent evidence cannot pass the evaluation coverage gate.
            pass


NATIVE_ENVIRONMENT_DIGEST_CLASSIFICATION = "diagnostic-non-authoritative"


def native_launch_facts(process, argv, environment):
    """Observe the successful native Popen boundary, distinct from its wrapper.

    The environment digest covers the mapping passed to native Popen (the
    scope variable removed exactly as the launch owner removes it). That
    mapping also holds host launcher additions such as shell and toolchain
    shim variables, so readback cannot derive it from source. It is diagnostic
    only; authoritative environment custody is the independently verified
    outer launch-owner start receipt.
    """
    native_env = dict(environment)
    native_env.pop(SCOPE_ENV, None)
    physical = Path(argv[0]).resolve(strict=True)
    def observed(fn):
        try:
            return fn(process.pid)
        except OSError:
            return None
    return {"argv": list(process.args), "physical_executable": str(physical),
            "physical_executable_sha256": hashlib.sha256(physical.read_bytes()).hexdigest(),
            "cwd": str(Path.cwd().resolve()), "pid": process.pid, "parent_pid": os.getpid(),
            "process_group": observed(os.getpgid), "session_id": observed(os.getsid),
            "diagnostic_environment_digest": hashlib.sha256(json.dumps(native_env, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "diagnostic_environment_digest_classification": NATIVE_ENVIRONMENT_DIGEST_CLASSIFICATION}


def instruction_launch_view(view, argv):
    """Witness a wrapper-applied instruction projection in the actual native argv."""
    view = dict(view)
    body = view.pop("_body", None)
    argument = argv[argv.index("--append-system-prompt") + 1] if "--append-system-prompt" in argv[:-1] else None
    witnessed = bool(view.get("applied") and body and argument is not None and body in argument)
    view.update(witnessed=witnessed, instructions_argument_bytes=len(argument.encode()) if argument is not None else 0,
                measurement="observed_at_launcher_boundary" if witnessed
                else "prospective_only:" + (view.get("reason") or "not_witnessed"))
    return view


def launcher_started(argv, environment, *, prompt_flag=None, process=None, instruction_view=None):
    """Called by native launch owners only after successful Popen, never preflight."""
    raw = environment.get(SCOPE_ENV)
    if not raw:
        return
    try:
        from .context_adapter import _write_new
        prepared = json.loads(raw)
        prepared["path"] = Path(prepared["path"])
        trace = Transport(prepared)
        trace.process_started(argv)
        if prompt_flag is not None:
            if argv.count(prompt_flag) != 1:
                raise ValueError("ambiguous native prompt")
            index = argv.index(prompt_flag) + 1
            payload = argv[index].encode()
            plan_bytes = direct_bytes(prepared["path"])
            if hashlib.sha256(plan_bytes).hexdigest() != prepared["reference"]["sha256"]:
                raise ValueError("launcher plan changed")
            expected = json.loads(plan_bytes)["transport"]["stdin"]
            prefix = payload[:expected["bytes"]]
            if len(prefix) != expected["bytes"] or hashlib.sha256(prefix).hexdigest() != expected["sha256"]:
                raise ValueError("native prompt differs from controlled input")
            suffix = payload[len(prefix):]
            trace.emit(payload, "prompt", "rendered-native-argv", "process_argv", argv_index=index,
                       input_view={"bytes": len(prefix), "sha256": hashlib.sha256(prefix).hexdigest()},
                       components=[{"kind": "launcher-instructions-source-view", "bytes": len(suffix),
                                    "sha256": hashlib.sha256(suffix).hexdigest(),
                                    "boundary": "instruction suffix in measured prompt; not an extra transmission"}])
        path = prepared["path"]
        value = {"schema": "apg.controlled-transmissions/v1", "plan": prepared["reference"],
                 "boundary": "native launcher process argv; inherited stdin counted by parent once",
                 "launch_facts": native_launch_facts(process, argv, environment) if process is not None else None,
                 "events": trace.events, "diagnostics": trace.diagnostics,
                 "coverage": "incomplete" if trace.diagnostics else "complete", "model_observed": None}
        if instruction_view is not None:
            value["instruction_projection"] = instruction_launch_view(instruction_view, argv)
        _write_new(path.with_name(path.name.replace(".context-plan.json", ".context-launcher-deliveries.json")), value)
    except (OSError, ValueError, KeyError, TypeError):
        # Normal provider availability does not depend on optional evidence.
        return


def run_observed_inherited(executable, argv, environment, *, instruction_view=None):
    """Opt-in observed replacement for execve, retaining inherited streams.

    Child remains in the launcher's process group so the dispatcher's existing
    group cleanup owns interruption. No capture, replay, or tool-policy changes.
    """
    import signal
    import subprocess
    native_environment = dict(environment)
    native_environment.pop(SCOPE_ENV, None)
    previous = {}
    child = None
    pending = []
    def forward(signum, frame):
        pending.append(signum)
        if child is not None and child.poll() is None:
            child.send_signal(signum)
    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.signal(signum, forward)
        child = subprocess.Popen(argv, executable=executable, env=native_environment)
        launcher_started(argv, environment, instruction_view=instruction_view)
        for signum in pending:
            if child.poll() is None:
                child.send_signal(signum)
        code = child.wait()
        if code < 0:
            # Preserve execve's signal exit semantics for the outer dispatcher;
            # translating SIGTERM into exit(143) changes failure classification.
            signum = -code
            if signum not in (signal.SIGKILL, signal.SIGSTOP):
                signal.signal(signum, signal.SIG_DFL)
            os.kill(os.getpid(), signum)
        return code
    finally:
        if child is not None and child.poll() is None:
            child.kill()
            child.wait()
        for signum, handler in previous.items():
            signal.signal(signum, handler)
