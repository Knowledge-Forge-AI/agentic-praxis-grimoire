"""Non-model custody shared by fresh headless provider adapters."""
from __future__ import annotations
import os
import signal
import subprocess
import tempfile
import time
from typing import Any


def run_bound_parent(binding, argv, ledger, *, popen_factory=subprocess.Popen,
                     prompt_file=None, prompt=None, output_dir=None,
                     drain_timeout_seconds=15.0, term_grace_seconds=2.0,
                     kill_grace_seconds=2.0):
    from . import native_launch as native
    stdin_handle: Any = None
    output_handles = []
    process: Any = None
    process_pgid: int | None = None
    exit_code: int | None = None
    cancel_state: dict[str, Any] = {"requested": False, "pgid": None}
    old_handlers: dict[int, Any] = {}

    def request_stop(signum: int, _frame: Any) -> None:
        cancel_state["requested"] = True
        cancel_state.setdefault("signals", []).append(signum)
        cancel_state.setdefault(
            "deadline", time.monotonic() + term_grace_seconds
        )
        if process is not None:
            native._signal_group(process, cancel_state.get("pgid"), signal.SIGTERM)

    launch_error: BaseException | None = None
    launch_traceback = None
    try:
        for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            try:
                old_handlers[signum] = signal.getsignal(signum)
                signal.signal(signum, request_stop)
            except (ValueError, OSError):
                pass
        if prompt_file is not None:
            prompt_file = native._resolved_path(prompt_file, "prompt_file")
            if not prompt_file.is_file() or not os.access(prompt_file, os.R_OK):
                raise native.NativeLaunchError("prompt_file must be a readable regular file")
            stdin_handle = prompt_file.open("rb")
        elif prompt is not None:
            stdin_handle = tempfile.TemporaryFile()
            stdin_handle.write(prompt.encode("utf-8"))
            stdin_handle.seek(0)
        if output_dir is not None:
            output_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
            for name in ("provider.stdout", "provider.stderr"):
                output_handles.append((output_dir / name).open("xb"))
        environment = os.environ.copy()
        for key in list(environment.keys()):
            if key.startswith("AGENT_CENTRAL"):
                environment.pop(key, None)
        environment.update(binding.facade_environment())
        environment["APGR_MANAGED_PARENT"] = "1"
        environment[native.FACADE_MARKER] = "1" if binding.facade_enabled else "0"
        process = popen_factory(
            argv,
            cwd=str(binding.workspace),
            env=environment,
            stdin=stdin_handle,
            start_new_session=True,
            **({"stdout": output_handles[0], "stderr": output_handles[1]} if output_handles else {}),
        )
        process_pgid = getattr(process, "pid", None)
        cancel_state["pgid"] = process_pgid
        try:
            native.bind_parent_process(binding, process.pid, process_pgid)
        except native.NativeLaunchError:
            # The durable claim remains; do not permit an unbound process to
            # outlive this wrapper or be mistaken for a reusable parent.
            native._signal_group(process, process_pgid, signal.SIGTERM)
            native._wait(process, term_grace_seconds)
            raise
        exit_code = native._wait_for_parent(
            process, cancel_state, term_grace_seconds=term_grace_seconds
        )
    except BaseException as error:
        launch_error = error
        launch_traceback = error.__traceback__
        if process is None:
            native._update_launch_record(
                binding,
                status="launch_failed",
                error=f"{type(error).__name__}: {str(error)[:240]}",
            )
        else:
            exit_code = getattr(process, "returncode", None)
            if not isinstance(exit_code, int):
                exit_code = -int(getattr(error, "errno", 1) or 1)
    finally:
        for signum, handler in old_handlers.items():
            try:
                signal.signal(signum, handler)
            except (ValueError, OSError):
                pass
        if stdin_handle is not None:
            stdin_handle.close()
        for handle in output_handles:
            handle.close()

    # Cleanup is part of the one-shot launch contract, including failed Popen,
    # failed identity binding, and interrupted waits.  The process-free result
    # is explicit so a missing child is not reported as an unknown process.
    drain = native.drain_parent_process(
        process,
        process_pgid,
        cancel_requested=bool(cancel_state.get("requested")),
        term_grace_seconds=term_grace_seconds,
        kill_grace_seconds=kill_grace_seconds,
    )
    drain["scope"] = "fresh-" + binding.parent_family + "-parent-process-group"
    ledger_drain = ledger.drain_and_close(timeout_seconds=drain_timeout_seconds, parent_exit_observed=bool(drain.get("cleanup_proven")))
    cleanup_proven = bool(drain.get("cleanup_proven")) and not ledger_drain.get(
        "uncertain_cleanup"
    )
    status = "drained" if cleanup_proven else "cleanup_uncertain"
    record_changes: dict[str, Any] = {
        "status": status,
        "process": {
            "pid": getattr(process, "pid", None),
            "pgid": process_pgid,
            "identity": (
                native._process_identity(getattr(process, "pid", -1), process_pgid or -1)
                if process is not None
                else None
            ),
        },
        "exit_code": exit_code,
        "drain": drain,
        "ledger_drain": ledger_drain,
        "cleanup_status": "proven" if cleanup_proven else "unknown",
    }
    if launch_error is not None:
        record_changes["launch_error"] = (
            f"{type(launch_error).__name__}: {str(launch_error)[:240]}"
        )
    record = native._update_launch_record(
        binding,
        **record_changes,
    )
    if launch_error is not None:
        raise launch_error.with_traceback(launch_traceback)
    binding_evidence = binding.evidence()
    binding_evidence["native_launch_binding"] = binding.launch_binding(argv)
    return {
        "status": status,
        "exit_code": exit_code,
        "argv": argv,
        "binding": binding_evidence,
        "record": record,
        "drain": drain,
        "ledger_drain": ledger_drain,
    }
