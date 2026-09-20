"""Live operator display. An observer, never a participant.

Two properties are load-bearing and everything in this module exists to keep
them:

* It cannot change dispatcher truth. Nothing here is read back by the
  dispatcher; it never touches captured bytes, candidate identities, scanner
  input, result parsing, or model context. Every write failure is absorbed.
* It cannot stall the run. Provider reader threads hand chunks to a bounded
  queue and never block on terminal I/O. A stalled or slow consumer of the
  dispatcher's stderr costs display lines, not progress: since a provider stage
  has no wall clock, a blocking write on a reader thread would fill the
  provider's pipe and deadlock the phase with nothing left to break the tie.

Human text goes to stderr so stdout stays a clean machine-readable channel.
"""

from __future__ import annotations

import queue
import threading
from typing import Any, TextIO


QUEUE_SIZE = 4096
CLOSE_TIMEOUT_SECONDS = 5.0

# Provider bytes and closeout prose reach the terminal verbatim, and a model can
# put an escape sequence in either. Stripping C0 controls (bar newline and tab),
# DEL, and the 8-bit CSI leaves the text readable while denying it the operator's
# title bar, cursor, and OSC-52 clipboard.
_KEEP = {ord("\n"), ord("\t")}
_STRIP = {code: None for code in range(0x20) if code not in _KEEP}
_STRIP[0x7F] = None
_STRIP[0x9B] = None


class Display:
    """Renders run progress to a text stream. Disabled instances do nothing."""

    def __init__(self, stream: TextIO | None, enabled: bool = True) -> None:
        self.enabled = enabled and stream is not None
        self.stream = stream
        self.dropped = 0
        self._queue: queue.Queue[str | None] = queue.Queue(maxsize=QUEUE_SIZE)
        self._partial: dict[str, str] = {}
        self._label = ""
        self._writer: threading.Thread | None = None
        if self.enabled:
            self._writer = threading.Thread(target=self._pump, daemon=True)
            self._writer.start()

    # -- transport ---------------------------------------------------------

    def _pump(self) -> None:
        while True:
            item = self._queue.get()
            if item is None:
                return
            if self.stream is None:
                continue
            try:
                self.stream.write(item)
                self.stream.flush()
            except (OSError, ValueError, UnicodeError):
                # A closed or broken stderr ends the display, not the run.
                self.stream = None

    def _emit(self, text: str) -> None:
        if not self.enabled:
            return
        try:
            self._queue.put_nowait(text.translate(_STRIP))
        except queue.Full:
            # Dropping display lines is the correct failure: the artifacts are
            # the record, and blocking here is what must never happen.
            self.dropped += 1

    def _line(self, text: str = "") -> None:
        self._emit(text + "\n")

    def close(self) -> None:
        if not self.enabled:
            return
        if self.dropped:
            self._line(f"  ({self.dropped} display line(s) dropped; artifacts are complete)")
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        if self._writer is not None:
            self._writer.join(timeout=CLOSE_TIMEOUT_SECONDS)
        self.enabled = False

    # -- run framing -------------------------------------------------------

    def run_started(
        self,
        project: str,
        phase_id: str,
        phase_type: str,
        execution_mode: str,
        endpoints: dict[str, Any],
        dry_run: bool = False,
        lifecycle: str = "standard",
        finalization_policy: str = "publish",
        review_count: int = 2,
        operation: str | None = None,
    ) -> None:
        kind = "dry run" if dry_run else "dispatch"
        self._line()
        self._line(f"phase {kind}: {project} / {phase_id}")
        self._line(f"  phase type:     {phase_type}")
        self._line(f"  execution mode: {execution_mode}")
        self._line(f"  lifecycle:      {lifecycle} ({review_count} review(s))")
        self._line(f"  finalization:   {finalization_policy}")
        if operation is not None:
            self._line(f"  operation:      {operation}")
        for stage, endpoint in endpoints.items():
            self._line(
                f"  {stage + ':':<16}{endpoint.provider} {endpoint.profile}"
            )

    def artifacts(self, path: Any) -> None:
        self._line(f"  artifacts:      {path}")

    def scanner(self, available: bool, version: str | None) -> None:
        state = f"available ({version})" if available and version else (
            "available" if available else "unavailable"
        )
        self._line(f"  scanner:        {state} — shadow only, never blocks a run")

    # -- stages ------------------------------------------------------------

    def stage_started(
        self,
        index: int,
        stage: str,
        role: str,
        endpoint: Any,
        stage_count: int = 5,
    ) -> None:
        self._label = f"{index}/{stage_count} {stage}"
        self._line()
        self._line(
            f"[{index}/{stage_count}] {stage} — {role} "
            f"{endpoint.provider} {endpoint.profile}"
        )

    def stage_output(self, stream: str, chunk: bytes) -> None:
        """Mirror provider bytes. Called from a provider reader thread."""
        if not self.enabled:
            return
        text = self._partial.get(stream, "") + chunk.decode("utf-8", "replace")
        lines = text.split("\n")
        self._partial[stream] = lines.pop()
        tag = "out" if stream == "stdout" else "err"
        for line in lines:
            self._emit(f"  {self._label} {tag}| {line}\n")

    def stage_notice(self, notice: dict) -> None:
        """Render one advisory stall notice.

        This is a local observation, not provider output, so it is deliberately
        tagged `warn` and never mixed into the mirrored `out`/`err` record. It is
        rate-limited by the provider, not by this method, and it never implies
        the stage is being terminated.
        """
        if not self.enabled:
            return
        self._emit(
            f"  {self._label} warn| provider quiet for "
            f"{notice['silent_seconds']:.0f}s "
            f"(elapsed {notice['elapsed_seconds']:.0f}s, "
            f"last activity {notice['last_activity_kind'] or 'none'}); "
            "still running, not terminated\n"
        )

    def stage_finished(self, stage: str, exit_code: int, seconds: float) -> None:
        self._flush_partial()
        self._line(
            f"[{stage}] complete — exit {exit_code} in {seconds:.1f}s"
        )

    def stage_failed(self, stage: str, detail: str) -> None:
        self._flush_partial()
        self._line(f"[{stage}] failed — {detail}")

    def _flush_partial(self) -> None:
        for stream, text in sorted(self._partial.items()):
            if text:
                tag = "out" if stream == "stdout" else "err"
                self._emit(f"  {self._label} {tag}| {text}\n")
        self._partial = {}

    def checkpoint(self, name: str) -> None:
        self._line(f"  checkpoint complete: {name}")

    # -- closeout ----------------------------------------------------------

    def git_delta(self, paths: list[str]) -> None:
        if not paths:
            self._line("  git: no phase delta; nothing to commit")
            return
        self._line(f"  git: phase delta is {len(paths)} path(s)")
        for path in paths:
            self._line(f"       {path}")

    def git_committing(self, subject: str) -> None:
        self._line(f"  git: committing — {subject}")

    def git_committed(self, sha: str) -> None:
        self._line(f"  git: committed {sha}")

    def push_starting(
        self, remote: str, remote_ref: str, preexisting_count: int | None
    ) -> None:
        self._line(f"  push: starting normal push to {remote} {remote_ref}")
        if preexisting_count:
            self._line(
                f"  push: will also publish {preexisting_count} pre-existing local "
                f"ancestor commit(s)"
            )
        elif preexisting_count == 0:
            self._line("  push: no pre-existing unpushed ancestor commits")
        else:
            self._line("  push: pre-existing unpushed ancestor count is indeterminate")

    def push_finished(
        self, succeeded: bool, remote: str, remote_ref: str, remote_head: str | None
    ) -> None:
        status = "succeeded" if succeeded else "failed"
        self._line(f"  push: {status}")
        self._line(f"  push: {remote} {remote_ref} -> {remote_head or 'unavailable'}")

    def finished(self, state: dict[str, Any], directory: Any = None) -> None:
        self._line()
        if state.get("dry_run"):
            self._line("outcome: dry run — stage 1 prompt rendered, nothing launched")
        else:
            self._line(
                f"outcome: {state.get('outcome')} "
                f"(complete={state.get('complete', False)})"
            )
        expected = state.get("expected_stages") or []
        self._line(
            "  stages: "
            f"invoked={len(state.get('stages_invoked', []))}/{len(expected)} "
            "transported="
            f"{len(state.get('stage_transports_completed', []))}/{len(expected)} "
            f"completed={len(state.get('stages_completed', []))}/{len(expected)}"
        )
        self._line(
            "  terminal result validated: "
            f"{state.get('terminal_result_validated', False)}"
        )
        commit = state.get("commit")
        if commit:
            self._line(f"  commit: {commit['sha']} {commit['subject']}")
        blocking = state.get("blocking_reason")
        if blocking:
            self._line(f"  blocked: {blocking['code']}")
            self._line(f"           {blocking['detail']}")
        if state.get("manager_disposition_required"):
            self._line("  manager disposition: required before Git mutation")
        prompt_policy = state.get("prompt_policy") or {}
        if prompt_policy:
            self._line(
                "  prompt policy: "
                f"{prompt_policy.get('total_removal_count', 0)} removal(s)"
            )
        if directory is not None:
            self._line(f"  result: {directory / 'result.json'}")
            self._line(f"          {directory / 'result.md'}")
        archive_path = state.get("archive_path")
        if archive_path:
            status = (state.get("archive") or {}).get("status", "unknown")
            self._line(f"  archive ({status}): {archive_path}")
        failure = (state.get("archive") or {}).get("failure")
        if isinstance(failure, dict):
            code = str(failure.get("code", "RUN_ARCHIVE_FAILED"))[:80]
            detail = str(failure.get("detail", ""))[:1200]
            safe = "".join(c if c.isprintable() else "?" for c in f"{code}: {detail}")
            self._line(f"  archive failure: {safe}")
        self._line()
