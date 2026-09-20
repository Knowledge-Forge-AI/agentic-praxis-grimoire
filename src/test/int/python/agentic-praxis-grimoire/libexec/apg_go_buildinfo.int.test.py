"""Source-only file-to-metadata contracts for supplied Go buildinfo payloads.

Cases write controlled bytes to real temporary files and traverse the reader,
parser and metadata validator without replacing those functions. The boundary
is filesystem input to validated metadata or a refusal; fixtures are never
executed. Native Go compatibility and packaged consumers remain hosted checks.
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path
import sys

import pytest

from src.test.apg_test_support import repository_root

ROOT = repository_root(__file__)
sys.path.insert(0, os.fspath(ROOT / "libexec"))

buildinfo = importlib.import_module("apg_go_buildinfo")


def _make_binary_with_mod_text(
    mod_text: str,
    *,
    format_type: str = "elf",
    go_version: str = buildinfo.REQUIRED_GO_VERSION,
    include_sentinels: bool = True,
    trailing_newline: bool = True,
    inline_flags: bool = True,
) -> bytes:
    """Build synthetic binary bytes containing arbitrary mod_text."""
    headers = {
        "elf": b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 8,
        "macho": b"\xcf\xfa\xed\xfe\x07\x00\x00\x01" + b"\x00" * 8,
        "pe": b"MZ\x90\x00" + b"\x00" * 12,
    }
    header = headers.get(format_type, b"\x00" * 16)
    mod_bytes = mod_text.encode("utf-8")
    if include_sentinels:
        sep = b"\n" if trailing_newline else b""
        mod_payload = buildinfo.INFO_START + mod_bytes + sep + buildinfo.INFO_END
    else:
        mod_payload = mod_bytes

    vers_bytes = go_version.encode("utf-8")
    flags = b"\x02" if inline_flags else b"\x00"
    hdr = buildinfo.BUILD_INFO_MAGIC + b"\x08" + flags + (b"\x00" * 16)
    payload = (
        hdr
        + buildinfo.encode_uvarint(len(vers_bytes))
        + vers_bytes
        + buildinfo.encode_uvarint(len(mod_payload))
        + mod_payload
    )
    return header + (b"\x00" * 16) + payload


@pytest.mark.parametrize(
    ("target", "format_type", "expected_goos", "expected_goarch"),
    [
        ("linux/amd64", "elf", "linux", "amd64"),
        ("linux/arm64", "elf", "linux", "arm64"),
        ("darwin/arm64", "macho", "darwin", "arm64"),
        ("windows/amd64", "pe", "windows", "amd64"),
    ],
)
def test_validate_all_supported_targets_and_formats(
    tmp_path: Path, target: str, format_type: str, expected_goos: str, expected_goarch: str
) -> None:
    bin_path = tmp_path / f"apgr-{expected_goos}-{expected_goarch}"
    bin_path.write_bytes(buildinfo.make_synthetic_binary(target=target, format_type=format_type))
    result = buildinfo.validate(bin_path, target)
    assert result == {
        "binary_path": os.fspath(bin_path),
        "go_version": "go1.26.9",
        "goarch": expected_goarch,
        "goos": expected_goos,
        "module": "github.com/Knowledge-Forge-AI/agentic-praxis-grimoire",
        "path": "github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/cmd/apgr",
        "settings": {
            "-buildvcs": "false",
            "-trimpath": "true",
            "CGO_ENABLED": "0",
            "GOARCH": expected_goarch,
            "GOOS": expected_goos,
        },
        "target": target,
    }


@pytest.mark.parametrize("trailing_newline", [True, False])
def test_sentinel_framing_variants(tmp_path: Path, trailing_newline: bool) -> None:
    raw_text = (
        "path\tgithub.com/Knowledge-Forge-AI/agentic-praxis-grimoire/cmd/apgr\n"
        "mod\tgithub.com/Knowledge-Forge-AI/agentic-praxis-grimoire\t(devel)\t\n"
        "build\t-buildvcs=false\n"
        "build\t-trimpath=true\n"
        "build\tCGO_ENABLED=0\n"
        "build\tGOARCH=amd64\n"
        "build\tGOOS=linux"
    )
    bin_framed = tmp_path / f"sentinel-{trailing_newline}.bin"
    bin_framed.write_bytes(
        _make_binary_with_mod_text(raw_text, include_sentinels=True, trailing_newline=trailing_newline)
    )
    res_framed = buildinfo.validate(bin_framed, "linux/amd64")
    assert res_framed["target"] == "linux/amd64"
    assert res_framed["settings"]["GOOS"] == "linux"

    bin_unframed = tmp_path / "unframed.bin"
    bin_unframed.write_bytes(
        buildinfo.make_synthetic_binary(target="linux/amd64", include_sentinels=False)
    )
    res_unframed = buildinfo.validate(bin_unframed, "linux/amd64")
    assert res_unframed["target"] == "linux/amd64"
    assert res_unframed["settings"]["GOARCH"] == "amd64"


@pytest.mark.parametrize(
    "header_form",
    [
        "binary: go1.26.9",
        "go\tgo1.26.9",
        "go go1.26.9",
        "go1.26.9",
    ],
)
def test_recorded_metadata_valid_forms_and_dependencies(
    tmp_path: Path, header_form: str
) -> None:
    bin_path = tmp_path / "apgr-deps"
    mod_lines = (
        "path\tgithub.com/Knowledge-Forge-AI/agentic-praxis-grimoire/cmd/apgr\n"
        "mod\tgithub.com/Knowledge-Forge-AI/agentic-praxis-grimoire\t(devel)\t\n"
        "dep\tgolang.org/x/sys\tv0.1.0\th1:xyz123\n"
        "build\t-buildvcs=false\n"
        "build\t-trimpath=true\n"
        'build\tCGO_CFLAGS="-O2 -Wall"\n'
        "build\tCGO_ENABLED=0\n"
        "build\tGOARCH=amd64\n"
        "build\tGOOS=linux\n"
    )
    bin_path.write_bytes(_make_binary_with_mod_text(mod_lines))

    recorded = f"{header_form}\n{mod_lines}"
    result = buildinfo.validate(bin_path, "linux/amd64", recorded=recorded)
    assert result["target"] == "linux/amd64"
    assert result["settings"]["CGO_CFLAGS"] == "-O2 -Wall"
    assert result["settings"]["CGO_ENABLED"] == "0"


def test_recorded_metadata_drift_refusals(tmp_path: Path) -> None:
    bin_path = tmp_path / "apgr-drift"
    base_mod = (
        "path\tgithub.com/Knowledge-Forge-AI/agentic-praxis-grimoire/cmd/apgr\n"
        "mod\tgithub.com/Knowledge-Forge-AI/agentic-praxis-grimoire\t(devel)\t\n"
        "dep\tgolang.org/x/sys\tv0.1.0\th1:xyz123\n"
        "build\t-buildvcs=false\n"
        "build\t-trimpath=true\n"
        "build\tCGO_ENABLED=0\n"
        "build\tEXTRA_OPT=fast\n"
        "build\tGOARCH=amd64\n"
        "build\tGOOS=linux\n"
    )
    bin_path.write_bytes(_make_binary_with_mod_text(base_mod))

    with pytest.raises(buildinfo.BuildInfoError, match="recorded go version -m text is empty"):
        buildinfo.validate(bin_path, "linux/amd64", recorded="")

    with pytest.raises(buildinfo.BuildInfoError, match="recorded Go version 'go1.27.0' does not match"):
        buildinfo.validate(bin_path, "linux/amd64", recorded=f"apgr: go1.27.0\n{base_mod}")

    with pytest.raises(buildinfo.BuildInfoError, match="recorded module 'github.com/Other/mod' does not match"):
        buildinfo.validate(
            bin_path,
            "linux/amd64",
            recorded=f"apgr: go1.26.9\n{base_mod.replace(buildinfo.REQUIRED_MODULE, 'github.com/Other/mod')}",
        )

    with pytest.raises(buildinfo.BuildInfoError, match="recorded path 'other/cmd' does not match"):
        bad_path = base_mod.replace(
            "github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/cmd/apgr", "other/cmd"
        )
        buildinfo.validate(bin_path, "linux/amd64", recorded=f"apgr: go1.26.9\n{bad_path}")

    with pytest.raises(buildinfo.BuildInfoError, match="recorded setting CGO_ENABLED='1' does not match"):
        buildinfo.validate(
            bin_path,
            "linux/amd64",
            recorded=f"apgr: go1.26.9\n{base_mod.replace('CGO_ENABLED=0', 'CGO_ENABLED=1')}",
        )

    with pytest.raises(buildinfo.BuildInfoError, match="recorded setting EXTRA_OPT='slow' does not match"):
        buildinfo.validate(
            bin_path,
            "linux/amd64",
            recorded=f"apgr: go1.26.9\n{base_mod.replace('EXTRA_OPT=fast', 'EXTRA_OPT=slow')}",
        )

    with pytest.raises(buildinfo.BuildInfoError, match="recorded build settings/dependencies differ"):
        buildinfo.validate(
            bin_path,
            "linux/amd64",
            recorded=f"apgr: go1.26.9\n{base_mod.replace('v0.1.0', 'v0.2.0')}",
        )

    with pytest.raises(buildinfo.BuildInfoError, match="recorded build settings/dependencies differ"):
        missing_setting = base_mod.replace("build\t-buildvcs=false\n", "")
        buildinfo.validate(
            bin_path,
            "linux/amd64",
            recorded=f"apgr: go1.26.9\n{missing_setting}",
        )


@pytest.mark.parametrize(
    ("kwargs", "validate_target", "error_match"),
    [
        (
            {"go_version": "go1.25.10"},
            "linux/amd64",
            "binary Go version 'go1.25.10' does not match required 'go1.26.9'",
        ),
        (
            {"module": "github.com/evil/mod"},
            "linux/amd64",
            "binary module 'github.com/evil/mod' does not match required",
        ),
        ({"cgo_enabled": "1"}, "linux/amd64", "binary CGO_ENABLED '1' must be '0'"),
        ({"trimpath": "false"}, "linux/amd64", "binary -trimpath 'false' must be 'true'"),
        ({"target": "linux/amd64"}, "darwin/amd64", "binary GOOS 'linux' does not match target 'darwin'"),
        ({"target": "linux/amd64"}, "linux/arm64", "binary GOARCH 'amd64' does not match target 'arm64'"),
        ({}, "invalid-target-no-slash", "invalid target specification: 'invalid-target-no-slash'"),
    ],
)
def test_strict_contract_refusals(
    tmp_path: Path, kwargs: dict[str, str], validate_target: str, error_match: str
) -> None:
    bin_path = tmp_path / "bad-contract-bin"
    bin_path.write_bytes(buildinfo.make_synthetic_binary(**kwargs))
    with pytest.raises(buildinfo.BuildInfoError, match=error_match):
        buildinfo.validate(bin_path, validate_target)


@pytest.mark.parametrize(
    ("content", "error_match"),
    [
        (b"MZ", "binary data too short to identify format"),
        (b"#!/usr/bin/env bash\necho hi\n", "unsupported binary format"),
        (b"\x00" * 32, "unsupported binary format"),
        (buildinfo.make_synthetic_binary(format_type="unsupported"), "unsupported binary format"),
    ],
)
def test_container_format_refusals(tmp_path: Path, content: bytes, error_match: str) -> None:
    bin_path = tmp_path / "container-refusal.bin"
    bin_path.write_bytes(content)
    with pytest.raises(buildinfo.UnsupportedFormatError, match=error_match):
        buildinfo.validate(bin_path, "linux/amd64")


def test_header_magic_and_flags_refusals(tmp_path: Path) -> None:
    missing = tmp_path / "missing-file.bin"
    with pytest.raises(buildinfo.BuildInfoError, match="binary file does not exist"):
        buildinfo.validate(missing, "linux/amd64")

    no_magic = tmp_path / "no-magic.bin"
    no_magic.write_bytes(buildinfo.make_synthetic_binary(corrupt_magic=True))
    with pytest.raises(buildinfo.BuildInfoError, match="Go build information magic not found in binary"):
        buildinfo.validate(no_magic, "linux/amd64")

    pre_118 = tmp_path / "pre-118.bin"
    pre_118.write_bytes(buildinfo.make_synthetic_binary(inline_flags=False))
    with pytest.raises(buildinfo.BuildInfoError, match="requires Go 1.18\\+ inline build info"):
        buildinfo.validate(pre_118, "linux/amd64")

    raw = buildinfo.make_synthetic_binary()
    offset = raw.find(buildinfo.BUILD_INFO_MAGIC)
    truncated_hdr = tmp_path / "truncated-hdr.bin"
    truncated_hdr.write_bytes(raw[: offset + 24])
    with pytest.raises(buildinfo.BuildInfoError, match="truncated Go buildinfo header"):
        buildinfo.validate(truncated_hdr, "linux/amd64")


def test_malformed_uvarint_and_truncated_payload(tmp_path: Path) -> None:
    raw = bytearray(buildinfo.make_synthetic_binary(target="linux/amd64"))
    offset = raw.find(buildinfo.BUILD_INFO_MAGIC)

    # 1. Truncated at varint start (unexpected EOF reading varint)
    eof_varint = tmp_path / "eof-varint.bin"
    eof_varint.write_bytes(bytes(raw[: offset + 32]))
    with pytest.raises(buildinfo.BuildInfoError, match="unexpected end of file reading varint"):
        buildinfo.validate(eof_varint, "linux/amd64")

    # 2. Varint overflow (>= 64 bits shift)
    overflow = tmp_path / "overflow.bin"
    overflow_bytes = bytes(raw[: offset + 32] + (b"\x80" * 10) + raw[offset + 33:])
    overflow.write_bytes(overflow_bytes)
    with pytest.raises(buildinfo.BuildInfoError, match="varint overflow"):
        buildinfo.validate(overflow, "linux/amd64")

    # 3. Truncated Go version payload
    trunc_ver = tmp_path / "trunc-version.bin"
    trunc_ver_bytes = bytes(raw[: offset + 32] + buildinfo.encode_uvarint(99999) + raw[offset + 33:])
    trunc_ver.write_bytes(trunc_ver_bytes)
    with pytest.raises(buildinfo.BuildInfoError, match="truncated Go version string in buildinfo"):
        buildinfo.validate(trunc_ver, "linux/amd64")

    # 4. Truncated modinfo payload
    vers_len, off1 = buildinfo.decode_uvarint(raw, offset + 32)
    trunc_mod = tmp_path / "trunc-mod.bin"
    trunc_mod_bytes = bytes(raw[: off1 + vers_len] + buildinfo.encode_uvarint(99999) + raw[off1 + vers_len + 1:])
    trunc_mod.write_bytes(trunc_mod_bytes)
    with pytest.raises(buildinfo.BuildInfoError, match="truncated modinfo string in buildinfo"):
        buildinfo.validate(trunc_mod, "linux/amd64")


def test_duplicate_settings_refusal(tmp_path: Path) -> None:
    # Duplicate setting inside the binary
    dup_mod = (
        "path\tgithub.com/Knowledge-Forge-AI/agentic-praxis-grimoire/cmd/apgr\n"
        "mod\tgithub.com/Knowledge-Forge-AI/agentic-praxis-grimoire\t(devel)\t\n"
        "build\t-buildvcs=false\n"
        "build\t-trimpath=true\n"
        "build\tCGO_ENABLED=0\n"
        "build\tGOARCH=amd64\n"
        "build\tGOOS=linux\n"
        "build\tGOOS=linux\n"
    )
    dup_bin = tmp_path / "dup-setting.bin"
    dup_bin.write_bytes(_make_binary_with_mod_text(dup_mod))
    with pytest.raises(buildinfo.BuildInfoError, match="duplicate build setting: GOOS"):
        buildinfo.validate(dup_bin, "linux/amd64")

    # Duplicate setting in recorded metadata
    valid_bin = tmp_path / "valid.bin"
    valid_bin.write_bytes(buildinfo.make_synthetic_binary(target="linux/amd64"))
    dup_rec = (
        f"{valid_bin}: go1.26.9\n"
        "path\tgithub.com/Knowledge-Forge-AI/agentic-praxis-grimoire/cmd/apgr\n"
        "mod\tgithub.com/Knowledge-Forge-AI/agentic-praxis-grimoire\t(devel)\t\n"
        "build\t-buildvcs=false\n"
        "build\t-trimpath=true\n"
        "build\tCGO_ENABLED=0\n"
        "build\tGOARCH=amd64\n"
        "build\tGOARCH=amd64\n"
        "build\tGOOS=linux\n"
    )
    with pytest.raises(buildinfo.BuildInfoError, match="duplicate build setting: GOARCH"):
        buildinfo.validate(valid_bin, "linux/amd64", recorded=dup_rec)
