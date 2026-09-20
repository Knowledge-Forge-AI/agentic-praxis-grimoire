"""Human presentation for Claude's authoritative raw stream-json output."""

from __future__ import annotations

import json
from typing import Any, BinaryIO


MAX_PRESENTATION_RECORD_BYTES = 1024 * 1024
_REPLACEMENT = "\N{REPLACEMENT CHARACTER}"
_MAX_LABEL_CHARACTERS = 128


def neutralize_terminal_controls(value: str) -> str:
    """Replace terminal-active control characters while preserving text layout."""
    return "".join(
        character
        if character in "\n\t"
        or not (
            ord(character) < 0x20
            or 0x7F <= ord(character) <= 0x9F
            or 0xD800 <= ord(character) <= 0xDFFF
            or 0x200B <= ord(character) <= 0x200F
            or 0x202A <= ord(character) <= 0x202E
            or 0x2066 <= ord(character) <= 0x2069
        )
        else _REPLACEMENT
        for character in value
    )


def bounded_label(value: Any, fallback: str) -> str:
    if not isinstance(value, str) or not value:
        return fallback
    if len(value) > _MAX_LABEL_CHARACTERS:
        return f"{value[:_MAX_LABEL_CHARACTERS]}…"
    return value


def write_all(destination: BinaryIO, chunk: bytes) -> None:
    remaining = memoryview(chunk)
    while remaining:
        written = destination.write(remaining)
        if written is None or written <= 0:
            raise OSError("stream write made no progress")
        remaining = remaining[written:]


class HumanRenderer:
    """Render the small, observed subset of Claude events useful to operators."""

    def __init__(
        self, profile_name: str, terminal: BinaryIO, warning_stream: BinaryIO
    ) -> None:
        self.profile_name = profile_name
        self.terminal = terminal
        self.warning_stream = warning_stream
        self.tool_names: dict[str, str] = {}
        self.last_assistant_text: str | None = None
        self.output_started = False

    def warn(self, message: str) -> None:
        self.warning_stream.write(f"[stream] {message}\n".encode("utf-8"))
        self.warning_stream.flush()

    def _emit_block(self, value: str) -> None:
        safe = neutralize_terminal_controls(value)
        if not safe:
            return
        if self.output_started:
            self.terminal.write(b"\n")
        self.terminal.write(safe.encode("utf-8"))
        if not safe.endswith("\n"):
            self.terminal.write(b"\n")
        self.terminal.flush()
        self.output_started = True

    def render(self, event: Any) -> None:
        if not isinstance(event, dict):
            return
        event_type = event.get("type")
        if event_type == "system" and event.get("subtype") == "init":
            self._render_init(event)
        elif event_type == "assistant":
            self._render_assistant(event)
        elif event_type == "user":
            self._render_tool_results(event)
        elif event_type == "result":
            self._render_result(event)

    def _render_init(self, event: dict[str, Any]) -> None:
        model = bounded_label(event.get("model"), "")
        pieces = ["[claude]"]
        if model:
            pieces.append(model)
        if self.profile_name:
            pieces.extend(("·", self.profile_name))
        self._emit_block(" ".join(pieces))

    @staticmethod
    def _content_blocks(event: dict[str, Any]) -> list[Any]:
        message = event.get("message")
        if not isinstance(message, dict):
            return []
        content = message.get("content")
        return content if isinstance(content, list) else []

    def _render_assistant(self, event: dict[str, Any]) -> None:
        for block in self._content_blocks(event):
            if not isinstance(block, dict):
                continue
            block_type = block.get("type")
            if block_type == "text":
                value = block.get("text")
                if isinstance(value, str) and value:
                    self._emit_block(value)
                    self.last_assistant_text = value
            elif block_type == "tool_use":
                name = bounded_label(block.get("name"), "tool")
                tool_id = block.get("id")
                if isinstance(tool_id, str) and tool_id:
                    self.tool_names[tool_id] = name
                self._emit_block(f"[tool] {name}")

    def _render_tool_results(self, event: dict[str, Any]) -> None:
        for block in self._content_blocks(event):
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            tool_id = block.get("tool_use_id")
            name = self.tool_names.get(tool_id, "tool") if isinstance(tool_id, str) else "tool"
            state = "error" if block.get("is_error") is True else "done"
            self._emit_block(f"[tool] {name} {state}")

    @staticmethod
    def _duration(value: Any) -> str | None:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            return None
        seconds = int(value / 1000)
        minutes, seconds = divmod(seconds, 60)
        return f"{minutes}m {seconds}s" if minutes else f"{seconds}s"

    def _render_result(self, event: dict[str, Any]) -> None:
        result = event.get("result")
        if (
            isinstance(result, str)
            and result
            and result != self.last_assistant_text
        ):
            self._emit_block(result)

        status = "error" if event.get("is_error") is True else event.get("subtype")
        if status != "success":
            status = "error"
        pieces = [f"[done] {status}"]
        turns = event.get("num_turns")
        if isinstance(turns, int) and not isinstance(turns, bool) and turns >= 0:
            pieces.append(f"{turns} turn" if turns == 1 else f"{turns} turns")
        duration = self._duration(event.get("duration_ms"))
        if duration is not None:
            pieces.append(duration)
        self._emit_block(" · ".join(pieces))


class JsonlPresenter:
    """Incrementally frame bounded JSONL records for human presentation."""

    def __init__(
        self,
        renderer: HumanRenderer,
        max_record_bytes: int = MAX_PRESENTATION_RECORD_BYTES,
    ) -> None:
        self.renderer = renderer
        self.max_record_bytes = max_record_bytes
        self.buffer = bytearray()
        self.discarding_oversized = False

    def feed(self, chunk: bytes) -> None:
        remaining = chunk
        while remaining:
            newline = remaining.find(b"\n")
            if self.discarding_oversized:
                if newline < 0:
                    return
                self.discarding_oversized = False
                remaining = remaining[newline + 1 :]
                continue

            if newline < 0:
                if len(self.buffer) + len(remaining) > self.max_record_bytes:
                    self.buffer.clear()
                    self.discarding_oversized = True
                    self.renderer.warn("oversized event preserved in raw log")
                else:
                    self.buffer.extend(remaining)
                return

            fragment = remaining[:newline]
            if len(self.buffer) + len(fragment) > self.max_record_bytes:
                self.buffer.clear()
                self.renderer.warn("oversized event preserved in raw log")
            else:
                self.buffer.extend(fragment)
                self._render_buffered_record()
            remaining = remaining[newline + 1 :]

    def finish(self) -> None:
        if self.buffer and not self.discarding_oversized:
            self._render_buffered_record()
        self.buffer.clear()

    def _render_buffered_record(self) -> None:
        record = bytes(self.buffer)
        self.buffer.clear()
        if not record.strip():
            return
        try:
            event = json.loads(record.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.renderer.warn("unrecognized event preserved in raw log")
            return
        self.renderer.render(event)


class LivePresentation:
    """Keep terminal presentation failures isolated from authoritative logging."""

    def __init__(
        self,
        display: str,
        profile_name: str,
        terminal: BinaryIO,
        warning_stream: BinaryIO,
    ) -> None:
        self.terminal = terminal
        self.warning_stream = warning_stream
        self.presenter = (
            JsonlPresenter(HumanRenderer(profile_name, terminal, warning_stream))
            if display == "human"
            else None
        )
        self.healthy = True

    def feed(self, chunk: bytes) -> None:
        if not self.healthy:
            return
        try:
            if self.presenter is None:
                write_all(self.terminal, chunk)
                self.terminal.flush()
            else:
                self.presenter.feed(chunk)
        except Exception:
            if self.presenter is None:
                raise
            self._disable()

    def finish(self) -> None:
        if not self.healthy or self.presenter is None:
            return
        try:
            self.presenter.finish()
        except Exception:
            self._disable()

    def _disable(self) -> None:
        self.healthy = False
        try:
            write_all(
                self.warning_stream,
                b"[stream] live presentation failed; raw log remains authoritative\n",
            )
            self.warning_stream.flush()
        except Exception:
            pass
