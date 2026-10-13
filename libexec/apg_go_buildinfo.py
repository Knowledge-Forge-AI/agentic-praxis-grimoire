"""Pure Python reader and validator for Go 1.18+ inline build info.

Extracts Go 1.18+ magic/varint build information directly from binary bytes
without invoking any Go or platform subprocesses. Validates strict APGR
compiler and build-setting contracts (Go 1.26.9, canonical module path,
target GOOS/GOARCH, CGO_ENABLED=0, -trimpath=true) and checks field-for-field
agreement with recorded `go version -m` text when supplied.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

BUILD_INFO_MAGIC = b"\xff Go buildinf:"
BUILD_INFO_HEADER_SIZE = 32
BUILD_INFO_ALIGN = 16

REQUIRED_GO_VERSION = "go1.26.9"
REQUIRED_MODULE = "github.com/Knowledge-Forge-AI/agentic-praxis-grimoire"

INFO_START = bytes.fromhex("3077af0c9274080241e1c107e6d618e6")
INFO_END = bytes.fromhex("f932433186182072008242104116d8f2")

FLAGS_VERSION_MASK = 0x2
FLAGS_VERSION_INL = 0x2


class BuildInfoError(ValueError):
    """Go build information is unavailable, malformed, or fails policy."""


class UnsupportedFormatError(BuildInfoError):
    """Binary container format is not supported."""


def check_executable_format(data: bytes) -> str:
    """Verify that binary data begins with a recognized executable container format.

    Recognizes:
    - ELF (Linux): ``\\x7fELF``
    - Mach-O (macOS): 32-bit, 64-bit, and Fat/Universal headers
    - PE (Windows): ``MZ``

    Raises UnsupportedFormatError if unrecognized.
    """
    if len(data) < 4:
        raise UnsupportedFormatError("binary data too short to identify format")
    if data.startswith(b"\x7fELF"):
        return "elf"
    if data.startswith(b"MZ"):
        return "pe"

    macho_prefixes = (
        b"\xfe\xed\xfa\xce",
        b"\xce\xfa\xed\xfe",
        b"\xfe\xed\xfa\xcf",
        b"\xcf\xfa\xed\xfe",
        b"\xca\xfe\xba\xbe",
        b"\xbe\xba\xfe\xca",
        b"\xca\xfe\xba\xbf",
        b"\xbf\xba\xfe\xca",
    )
    if any(data.startswith(prefix) for prefix in macho_prefixes):
        return "macho"
    raise UnsupportedFormatError(f"unsupported binary format: {data[:16]!r}")


def decode_uvarint(data: bytes, offset: int = 0) -> tuple[int, int]:
    """Read an unsigned LEB128 varint from data at offset.

    Returns (value, next_offset).
    """
    result = 0
    shift = 0
    pos = offset
    while True:
        if pos >= len(data):
            raise BuildInfoError("unexpected end of file reading varint")
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if (byte & 0x80) == 0:
            break
        shift += 7
        if shift >= 64:
            raise BuildInfoError("varint overflow")
    return result, pos


def encode_uvarint(value: int) -> bytes:
    """Encode non-negative integer as unsigned LEB128 varint."""
    if value < 0:
        raise ValueError("value must be non-negative")
    parts = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value != 0:
            parts.append(byte | 0x80)
        else:
            parts.append(byte)
            break
    return bytes(parts)


def extract_raw_build_info(data: bytes) -> tuple[str, str]:
    """Extract Go version string and modinfo text from binary bytes without subprocess.

    Extracts inline 1.18+ magic/varint build info.
    Raises UnsupportedFormatError on invalid binary format.
    Raises BuildInfoError if magic not found, not inline 1.18+, or corrupted.
    """
    check_executable_format(data)
    offset = data.find(BUILD_INFO_MAGIC)
    if offset == -1:
        raise BuildInfoError("Go build information magic not found in binary")
    if offset + BUILD_INFO_HEADER_SIZE > len(data):
        raise BuildInfoError("truncated Go buildinfo header")

    flags = data[offset + 15]
    if (flags & FLAGS_VERSION_MASK) != FLAGS_VERSION_INL:
        raise BuildInfoError("unsupported Go buildinfo format: requires Go 1.18+ inline build info")

    vers_len, offset1 = decode_uvarint(data, offset + BUILD_INFO_HEADER_SIZE)
    if offset1 + vers_len > len(data):
        raise BuildInfoError("truncated Go version string in buildinfo")
    go_version = data[offset1 : offset1 + vers_len].decode("utf-8", errors="replace")

    mod_len, offset2 = decode_uvarint(data, offset1 + vers_len)
    if offset2 + mod_len > len(data):
        raise BuildInfoError("truncated modinfo string in buildinfo")
    mod_bytes = data[offset2 : offset2 + mod_len]

    if len(mod_bytes) >= 32 and mod_bytes[:16] == INFO_START and mod_bytes[-16:] == INFO_END or len(mod_bytes) >= 33 and mod_bytes[:16] == INFO_START and mod_bytes[-17] == 0x0A and mod_bytes[-16:] == INFO_END:
        mod_content = mod_bytes[16:-16]
    else:
        mod_content = mod_bytes
    mod_text = mod_content.decode("utf-8", errors="replace")
    return go_version, mod_text


def parse_mod_text(mod_text: str) -> dict[str, Any]:
    """Parse Go module info text into structured dictionary."""
    path: str | None = None
    module: str | None = None
    module_record: list[str] = []
    settings: dict[str, str] = {}
    deps: list[dict[str, str]] = []

    for raw_line in mod_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(("path\t", "path ")):
            path = line.split(None, 1)[1].strip()
        elif line.startswith(("mod\t", "mod ")):
            parts = line.split()
            if len(parts) >= 2:
                module = parts[1]
                module_record = parts[1:]
        elif line.startswith(("build\t", "build ")):
            setting = line.split(None, 1)[1].strip()
            if "=" in setting:
                key, val = setting.split("=", 1)
                if key in settings:
                    raise BuildInfoError(f"duplicate build setting: {key}")
                if (val.startswith('"') and val.endswith('"')) or (val.startswith('`') and val.endswith('`')):
                    val = val[1:-1]
                settings[key] = val
        elif line.startswith(("dep\t", "dep ")):
            parts = line.split()
            if len(parts) >= 2:
                deps.append({"path": parts[1], "version": parts[2] if len(parts) > 2 else "", "checksum": parts[3] if len(parts) > 3 else ""})

    return {
        "deps": deps,
        "module": module,
        "module_record": module_record,
        "path": path,
        "raw": mod_text,
        "settings": settings,
    }


def parse_recorded_metadata(recorded: str) -> dict[str, Any]:
    """Parse recorded `go version -m` text output into structured dictionary."""
    lines = recorded.strip().splitlines()
    if not lines:
        raise BuildInfoError("recorded go version -m text is empty")
    first = lines[0].strip()
    if ":" in first:
        _, recorded_version = first.split(":", 1)
        recorded_version = recorded_version.strip()
    elif first.startswith(("go\t", "go ")):
        recorded_version = first.split(None, 1)[1].strip()
    else:
        recorded_version = first

    mod_lines = "\n".join(lines[1:])
    parsed = parse_mod_text(mod_lines)
    parsed["go_version"] = recorded_version
    return parsed


def validate(
    binary: Path | str,
    target: str,
    recorded: str | None = None,
) -> dict[str, Any]:
    """Validate Go binary buildinfo strictly against target and release contract.

    Extracts build info bytes directly without any Go subprocess.
    Enforces strict matching:
    - Go compiler version: exactly go1.26.9
    - Module path: github.com/Knowledge-Forge-AI/agentic-praxis-grimoire
    - GOOS: target GOOS
    - GOARCH: target GOARCH
    - CGO_ENABLED: '0'
    - -trimpath: 'true'

    When `recorded` is provided (e.g. from retained native `go version -m`),
    validates field-for-field agreement.
    """
    binary_path = Path(binary)
    if not binary_path.is_file():
        raise BuildInfoError(f"binary file does not exist: {binary_path}")
    try:
        data = binary_path.read_bytes()
    except OSError as error:
        raise BuildInfoError(f"failed to read binary {binary_path}: {error}") from error

    go_version, mod_text = extract_raw_build_info(data)
    parsed = parse_mod_text(mod_text)

    if go_version != REQUIRED_GO_VERSION:
        raise BuildInfoError(
            f"binary Go version {go_version!r} does not match required {REQUIRED_GO_VERSION!r}"
        )
    if parsed.get("module") != REQUIRED_MODULE:
        raise BuildInfoError(
            f"binary module {parsed.get('module')!r} does not match required {REQUIRED_MODULE!r}"
        )
    if "/" not in target:
        raise BuildInfoError(f"invalid target specification: {target!r}")
    expected_goos, expected_goarch = target.split("/", 1)

    settings = parsed.get("settings", {})
    if settings.get("GOOS") != expected_goos:
        raise BuildInfoError(
            f"binary GOOS {settings.get('GOOS')!r} does not match target {expected_goos!r}"
        )
    if settings.get("GOARCH") != expected_goarch:
        raise BuildInfoError(
            f"binary GOARCH {settings.get('GOARCH')!r} does not match target {expected_goarch!r}"
        )
    if settings.get("CGO_ENABLED") != "0":
        raise BuildInfoError(
            f"binary CGO_ENABLED {settings.get('CGO_ENABLED')!r} must be '0'"
        )
    if settings.get("-trimpath") != "true":
        raise BuildInfoError(
            f"binary -trimpath {settings.get('-trimpath')!r} must be 'true'"
        )

    if recorded is not None:
        rec = parse_recorded_metadata(recorded)
        if rec["go_version"] != go_version:
            raise BuildInfoError(
                f"recorded Go version {rec['go_version']!r} does not match binary {go_version!r}"
            )
        if rec.get("module") != parsed.get("module"):
            raise BuildInfoError(
                f"recorded module {rec.get('module')!r} does not match binary {parsed.get('module')!r}"
            )
        if rec.get("path") != parsed.get("path"):
            raise BuildInfoError(
                f"recorded path {rec.get('path')!r} does not match binary {parsed.get('path')!r}"
            )
        rec_settings = rec.get("settings", {})
        for k in ("GOOS", "GOARCH", "CGO_ENABLED", "-trimpath"):
            if rec_settings.get(k) != settings.get(k):
                raise BuildInfoError(
                    f"recorded setting {k}={rec_settings.get(k)!r} does not match binary {settings.get(k)!r}"
                )
        for k, v in rec_settings.items():
            if k in settings and settings[k] != v:
                raise BuildInfoError(
                    f"recorded setting {k}={v!r} does not match binary {settings[k]!r}"
                )
        if rec_settings != settings or rec.get("deps") != parsed.get("deps") or rec.get("module_record") != parsed.get("module_record"):
            raise BuildInfoError("recorded build settings/dependencies differ from binary inventory")

    return {
        "binary_path": os.fspath(binary_path),
        "go_version": go_version,
        "goarch": expected_goarch,
        "goos": expected_goos,
        "module": parsed.get("module"),
        "path": parsed.get("path"),
        "settings": settings,
        "target": target,
    }


def make_synthetic_binary(
    *,
    target: str = "linux/amd64",
    go_version: str = REQUIRED_GO_VERSION,
    module: str = REQUIRED_MODULE,
    cgo_enabled: str = "0",
    trimpath: str = "true",
    format_type: str = "elf",
    extra_settings: Mapping[str, str] | None = None,
    corrupt_magic: bool = False,
    inline_flags: bool = True,
    include_sentinels: bool = True,
    prefix_padding: int = 16,
) -> bytes:
    """Construct synthetic binary bytes with embedded Go inline build info for testing."""
    if format_type == "elf":
        header = b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 8
    elif format_type == "macho":
        header = b"\xcf\xfa\xed\xfe\x07\x00\x00\x01" + b"\x00" * 8
    elif format_type == "pe":
        header = b"MZ\x90\x00" + b"\x00" * 12
    elif format_type == "unsupported":
        header = b"NOT_AN_EXECUTABLE_CONTAINER"
    else:
        header = b"\x00" * 16

    goos, goarch = target.split("/", 1) if "/" in target else (target, "")
    lines = [
        f"path\t{module}/cmd/apgr",
        f"mod\t{module}\t(devel)\t",
        "build\t-buildvcs=false",
        f"build\t-trimpath={trimpath}",
        f"build\tCGO_ENABLED={cgo_enabled}",
        f"build\tGOARCH={goarch}",
        f"build\tGOOS={goos}",
    ]
    if extra_settings:
        for k, v in extra_settings.items():
            lines.append(f"build\t{k}={v}")
    mod_text = "\n".join(lines) + "\n"
    mod_payload = mod_text.encode("utf-8")
    if include_sentinels:
        mod_payload = INFO_START + mod_payload + INFO_END

    version_bytes = go_version.encode("utf-8")

    magic = b"\x00" * 14 if corrupt_magic else BUILD_INFO_MAGIC
    ptr_size = b"\x08"
    flags = b"\x02" if inline_flags else b"\x00"
    build_info_hdr = magic + ptr_size + flags + b"\x00" * 16
    assert len(build_info_hdr) == 32

    payload = (
        build_info_hdr
        + encode_uvarint(len(version_bytes))
        + version_bytes
        + encode_uvarint(len(mod_payload))
        + mod_payload
    )

    alignment_pad = (16 - (len(header) % 16)) % 16
    data = header + (b"\x00" * alignment_pad) + (b"\x00" * prefix_padding)
    pad_to_16 = (16 - (len(data) % 16)) % 16
    return data + (b"\x00" * pad_to_16) + payload
