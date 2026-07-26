"""Deterministic section and common-envelope byte rendering."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re

from .models import ParsedRecord, ReportRecord


ENVELOPE_LINE = b"=" * 80
SECTION_LINE = b"-" * 80
_START = ENVELOPE_LINE + b"\nBEGIN AGENT-REPORT-RECORD\n"
_SAFE_FIELD = re.compile(r"^[^\x00-\x1f\x7f\r\n]+$")


class RecordParseError(ValueError):
    """Raised when a canonical report contains a malformed common record."""


@dataclass(frozen=True, slots=True)
class _ParsedHeader:
    record_type: str
    format_version: int
    record_id: str
    project: str
    phase: str
    payload_sha: str
    payload_size: int
    common_lines: tuple[bytes, ...]


def ensure_payload_ending(payload: bytes) -> bytes:
    """Add the framing newline required after a non-empty raw payload."""

    if payload and not payload.endswith(b"\n"):
        return payload + b"\n"
    return payload


def render_section(name: str, payload: bytes) -> bytes:
    """Render one named section while preserving payload bytes exactly."""

    if not name or not name.isascii() or not _SAFE_FIELD.fullmatch(name):
        raise ValueError("section name is unsafe")
    framed = ensure_payload_ending(payload)
    encoded_name = name.encode("ascii")
    return b"".join(
        (
            SECTION_LINE,
            b"\nBEGIN ",
            encoded_name,
            b"\n",
            SECTION_LINE,
            b"\n",
            framed,
            SECTION_LINE,
            b"\nEND ",
            encoded_name,
            b"\n",
            SECTION_LINE,
            b"\n",
        )
    )


def _field(value: str) -> bytes:
    if not value or not _SAFE_FIELD.fullmatch(value):
        raise ValueError("record field is unsafe")
    return value.encode("utf-8")


def build_record(record: ReportRecord) -> bytes:
    """Render one complete version-1 common envelope."""

    payload_sha = hashlib.sha256(record.payload).hexdigest()
    common = (
        (b"RECORD-TYPE", _field(record.record_type)),
        (b"RECORD-FORMAT-VERSION", str(record.format_version).encode("ascii")),
        (b"RECORD-ID", _field(record.record_id)),
        (b"PROJECT", _field(record.project)),
        (b"PHASE", _field(record.phase)),
    )
    header = b"".join(
        (
            ENVELOPE_LINE + b"\n",
            b"BEGIN AGENT-REPORT-RECORD\n",
            b"ENVELOPE-FORMAT: agent-report-record\n",
            b"ENVELOPE-VERSION: 1\n",
            *(key + b": " + value + b"\n" for key, value in common),
            b"PAYLOAD-SHA256: " + payload_sha.encode("ascii") + b"\n",
            b"PAYLOAD-SIZE-BYTES: " + str(len(record.payload)).encode("ascii") + b"\n",
            ENVELOPE_LINE + b"\n",
        )
    )
    trailer = b"".join(
        (
            ENVELOPE_LINE + b"\n",
            b"END AGENT-REPORT-RECORD\n",
            b"ENVELOPE-FORMAT: agent-report-record\n",
            b"ENVELOPE-VERSION: 1\n",
            *(key + b": " + value + b"\n" for key, value in common),
            b"RECORD-COMPLETE: true\n",
            ENVELOPE_LINE + b"\n",
        )
    )
    return header + record.payload + trailer


def _read_line(data: bytes, offset: int) -> tuple[bytes, int] | None:
    ending = data.find(b"\n", offset)
    if ending < 0:
        return None
    return data[offset:ending], ending + 1


def _read_lines(data: bytes, offset: int, count: int) -> tuple[list[bytes], int] | None:
    lines: list[bytes] = []
    for _ in range(count):
        result = _read_line(data, offset)
        if result is None:
            return None
        line, offset = result
        lines.append(line)
    return lines, offset


def _parse_header(lines: list[bytes]) -> _ParsedHeader | None:
    if lines[0] != ENVELOPE_LINE or lines[1] != b"BEGIN AGENT-REPORT-RECORD":
        return None
    if lines[2:4] != [b"ENVELOPE-FORMAT: agent-report-record", b"ENVELOPE-VERSION: 1"]:
        return None
    if lines[11] != ENVELOPE_LINE:
        return None
    expected_prefixes = (
        b"RECORD-TYPE: ",
        b"RECORD-FORMAT-VERSION: ",
        b"RECORD-ID: ",
        b"PROJECT: ",
        b"PHASE: ",
        b"PAYLOAD-SHA256: ",
        b"PAYLOAD-SIZE-BYTES: ",
    )
    values: list[bytes] = []
    for line, prefix in zip(lines[4:11], expected_prefixes, strict=True):
        if not line.startswith(prefix):
            return None
        values.append(line[len(prefix) :])
    decoded = _decode_header_values(values)
    if decoded is None:
        return None
    record_type, format_version, record_id, project, phase, payload_sha, payload_size = decoded
    if payload_size < 0 or not re.fullmatch(r"[0-9a-f]{64}", payload_sha):
        return None
    return _ParsedHeader(
        record_type,
        format_version,
        record_id,
        project,
        phase,
        payload_sha,
        payload_size,
        tuple(lines[4:9]),
    )


def _decode_header_values(
    values: list[bytes],
) -> tuple[str, int, str, str, str, str, int] | None:
    try:
        return (
            values[0].decode("utf-8"),
            int(values[1].decode("ascii")),
            values[2].decode("utf-8"),
            values[3].decode("utf-8"),
            values[4].decode("utf-8"),
            values[5].decode("ascii"),
            int(values[6].decode("ascii")),
        )
    except (UnicodeDecodeError, ValueError):
        return None


def _parse_at(data: bytes, start: int) -> ParsedRecord | None:
    header_result = _read_lines(data, start, 12)
    if header_result is None:
        return None
    lines, offset = header_result
    header = _parse_header(lines)
    if header is None:
        return None
    payload_end = offset + header.payload_size
    if payload_end > len(data):
        return None
    payload = data[offset:payload_end]
    if hashlib.sha256(payload).hexdigest() != header.payload_sha:
        return None
    trailer_result = _read_lines(data, payload_end, 11)
    if trailer_result is None:
        return None
    trailer_lines, offset = trailer_result
    expected_trailer = [
        ENVELOPE_LINE,
        b"END AGENT-REPORT-RECORD",
        b"ENVELOPE-FORMAT: agent-report-record",
        b"ENVELOPE-VERSION: 1",
        *header.common_lines,
        b"RECORD-COMPLETE: true",
        ENVELOPE_LINE,
    ]
    if trailer_lines != expected_trailer:
        return None
    record = ReportRecord(
        record_type=header.record_type,
        format_version=header.format_version,
        record_id=header.record_id,
        project=header.project,
        phase=header.phase,
        payload=payload,
    )
    return ParsedRecord(
        record=record,
        payload_sha256=header.payload_sha,
        start=start,
        end=offset,
    )


def parse_complete_records(data: bytes) -> tuple[ParsedRecord, ...]:
    """Return every structurally complete common record, ignoring legacy text."""

    records: list[ParsedRecord] = []
    cursor = 0
    while True:
        start = data.find(_START, cursor)
        if start < 0:
            break
        parsed = _parse_at(data, start)
        if parsed is None:
            cursor = start + 1
            continue
        records.append(parsed)
        cursor = parsed.end
    return tuple(records)


def parse_canonical_records(data: bytes) -> tuple[ParsedRecord, ...]:
    """Validate contiguous appended records while allowing one legacy prefix."""

    records = parse_complete_records(data)
    if not records:
        if data.startswith(_START):
            raise RecordParseError("existing report contains an incomplete record")
        return ()
    for previous, following in zip(records, records[1:], strict=False):
        if previous.end != following.start:
            raise RecordParseError("existing report contains bytes between common records")
    if records[-1].end != len(data):
        raise RecordParseError("existing report ends with incomplete or unrelated bytes")
    return records
