"""Unit tests for pure Python apg_go_buildinfo reader and validator."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from src.test.apg_test_support import repository_root

REPOSITORY_ROOT = repository_root(__file__)
import sys

sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import apg_go_buildinfo as buildinfo


def test_validate_synthetic_elf_and_macho_targets(tmp_path: Path) -> None:
    # Linux amd64 (ELF)
    elf_bin = tmp_path / "apgr-linux-amd64"
    elf_bin.write_bytes(buildinfo.make_synthetic_binary(target="linux/amd64", format_type="elf"))
    result_elf = buildinfo.validate(elf_bin, "linux/amd64")
    assert result_elf["target"] == "linux/amd64"
    assert result_elf["go_version"] == "go1.26.9"
    assert result_elf["module"] == "github.com/Knowledge-Forge-AI/agentic-praxis-grimoire"
    assert result_elf["settings"]["CGO_ENABLED"] == "0"
    assert result_elf["settings"]["-trimpath"] == "true"
    assert result_elf["goos"] == "linux"
    assert result_elf["goarch"] == "amd64"

    # Darwin arm64 (Mach-O)
    macho_bin = tmp_path / "apgr-darwin-arm64"
    macho_bin.write_bytes(buildinfo.make_synthetic_binary(target="darwin/arm64", format_type="macho"))
    result_macho = buildinfo.validate(macho_bin, "darwin/arm64")
    assert result_macho["target"] == "darwin/arm64"
    assert result_macho["goos"] == "darwin"
    assert result_macho["goarch"] == "arm64"

    # Linux arm64 (ELF)
    arm64_bin = tmp_path / "apgr-linux-arm64"
    arm64_bin.write_bytes(buildinfo.make_synthetic_binary(target="linux/arm64", format_type="elf"))
    result_arm64 = buildinfo.validate(arm64_bin, "linux/arm64")
    assert result_arm64["target"] == "linux/arm64"
    assert result_arm64["goos"] == "linux"
    assert result_arm64["goarch"] == "arm64"


def test_recorded_metadata_requires_complete_settings_inventory(tmp_path: Path) -> None:
    path = tmp_path / "apgr"
    raw = buildinfo.make_synthetic_binary(target="linux/amd64")
    path.write_bytes(raw)
    _, module = buildinfo.extract_raw_build_info(raw)
    incomplete = "binary: go1.26.9\n" + module.replace("build\t-buildvcs=false\n", "")
    with pytest.raises(buildinfo.BuildInfoError, match="inventory"):
        buildinfo.validate(path, "linux/amd64", recorded=incomplete)
    duplicate = "binary: go1.26.9\n" + module + "build\tGOARCH=amd64\n"
    with pytest.raises(buildinfo.BuildInfoError, match="duplicate"):
        buildinfo.validate(path, "linux/amd64", recorded=duplicate)


def test_validate_no_subprocess_called(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden_subprocess(*_args, **_kwargs):
        pytest.fail("Subprocess invocation forbidden in pure Python buildinfo reader")

    monkeypatch.setattr(subprocess, "run", forbidden_subprocess)
    monkeypatch.setattr(subprocess, "Popen", forbidden_subprocess)

    bin_path = tmp_path / "apgr"
    bin_path.write_bytes(buildinfo.make_synthetic_binary(target="linux/amd64", format_type="elf"))
    result = buildinfo.validate(bin_path, "linux/amd64")
    assert result["target"] == "linux/amd64"


def test_validate_with_recorded_matching_text(tmp_path: Path) -> None:
    bin_path = tmp_path / "apgr"
    bin_path.write_bytes(
        buildinfo.make_synthetic_binary(
            target="linux/amd64",
            format_type="elf",
            extra_settings={"GOAMD64": "v1"},
        )
    )

    recorded_text = (
        f"{bin_path}: go1.26.9\n"
        "	path	github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/cmd/apgr\n"
        "	mod	github.com/Knowledge-Forge-AI/agentic-praxis-grimoire	(devel)	\n"
        "	build	-buildvcs=false\n"
        "	build	-trimpath=true\n"
        "	build	CGO_ENABLED=0\n"
        "	build	GOAMD64=v1\n"
        "	build	GOARCH=amd64\n"
        "	build	GOOS=linux\n"
    )

    result = buildinfo.validate(bin_path, "linux/amd64", recorded=recorded_text)
    assert result["target"] == "linux/amd64"
    assert result["settings"]["GOAMD64"] == "v1"


def test_validate_recorded_disagreements(tmp_path: Path) -> None:
    bin_path = tmp_path / "apgr"
    bin_path.write_bytes(buildinfo.make_synthetic_binary(target="linux/amd64", format_type="elf"))

    # Disagreeing Go version
    bad_vers = (
        f"{bin_path}: go1.25.10\n"
        "\tpath\tgithub.com/Knowledge-Forge-AI/agentic-praxis-grimoire/cmd/apgr\n"
        "	mod	github.com/Knowledge-Forge-AI/agentic-praxis-grimoire	(devel)	\n"
        "	build	CGO_ENABLED=0\n"
        "	build	GOARCH=amd64\n"
        "	build	GOOS=linux\n"
        "	build	-trimpath=true\n"
    )
    with pytest.raises(buildinfo.BuildInfoError, match="recorded Go version 'go1.25.10' does not match"):
        buildinfo.validate(bin_path, "linux/amd64", recorded=bad_vers)

    # Disagreeing module
    bad_mod = (
        f"{bin_path}: go1.26.9\n"
        "\tpath\tgithub.com/Knowledge-Forge-AI/agentic-praxis-grimoire/cmd/apgr\n"
        "	mod	github.com/Other/repo	(devel)	\n"
        "	build	CGO_ENABLED=0\n"
        "	build	GOARCH=amd64\n"
        "	build	GOOS=linux\n"
        "	build	-trimpath=true\n"
    )
    with pytest.raises(buildinfo.BuildInfoError, match="recorded module 'github.com/Other/repo' does not match"):
        buildinfo.validate(bin_path, "linux/amd64", recorded=bad_mod)

    # Disagreeing GOARCH
    bad_arch = (
        f"{bin_path}: go1.26.9\n"
        "\tpath\tgithub.com/Knowledge-Forge-AI/agentic-praxis-grimoire/cmd/apgr\n"
        "	mod	github.com/Knowledge-Forge-AI/agentic-praxis-grimoire	(devel)	\n"
        "	build	CGO_ENABLED=0\n"
        "	build	GOARCH=arm64\n"
        "	build	GOOS=linux\n"
        "	build	-trimpath=true\n"
    )
    with pytest.raises(buildinfo.BuildInfoError, match="recorded setting GOARCH='arm64' does not match"):
        buildinfo.validate(bin_path, "linux/amd64", recorded=bad_arch)

    # Disagreeing CGO_ENABLED
    bad_cgo = (
        f"{bin_path}: go1.26.9\n"
        "\tpath\tgithub.com/Knowledge-Forge-AI/agentic-praxis-grimoire/cmd/apgr\n"
        "	mod	github.com/Knowledge-Forge-AI/agentic-praxis-grimoire	(devel)	\n"
        "	build	CGO_ENABLED=1\n"
        "	build	GOARCH=amd64\n"
        "	build	GOOS=linux\n"
        "	build	-trimpath=true\n"
    )
    with pytest.raises(buildinfo.BuildInfoError, match="recorded setting CGO_ENABLED='1' does not match"):
        buildinfo.validate(bin_path, "linux/amd64", recorded=bad_cgo)


def test_validate_unsupported_formats(tmp_path: Path) -> None:
    # Text script
    script = tmp_path / "script.sh"
    script.write_bytes(b"#!/usr/bin/env bash\necho hello\n")
    with pytest.raises(buildinfo.UnsupportedFormatError, match="unsupported binary format"):
        buildinfo.validate(script, "linux/amd64")

    # Short file
    short = tmp_path / "short"
    short.write_bytes(b"ab")
    with pytest.raises(buildinfo.UnsupportedFormatError, match="too short"):
        buildinfo.validate(short, "linux/amd64")

    # Random binary bytes
    rand = tmp_path / "rand.bin"
    rand.write_bytes(b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f")
    with pytest.raises(buildinfo.UnsupportedFormatError, match="unsupported binary format"):
        buildinfo.validate(rand, "linux/amd64")

    # Explicit unsupported format in make_synthetic_binary
    unsupported = tmp_path / "bad.bin"
    unsupported.write_bytes(buildinfo.make_synthetic_binary(format_type="unsupported"))
    with pytest.raises(buildinfo.UnsupportedFormatError, match="unsupported binary format"):
        buildinfo.validate(unsupported, "linux/amd64")


def test_validate_missing_magic_or_corrupt_header(tmp_path: Path) -> None:
    # ELF without buildinfo magic
    no_magic = tmp_path / "no_magic"
    no_magic.write_bytes(buildinfo.make_synthetic_binary(corrupt_magic=True))
    with pytest.raises(buildinfo.BuildInfoError, match="magic not found"):
        buildinfo.validate(no_magic, "linux/amd64")

    # Pre-1.18 pointer flags (flags & 2 != 2)
    old_flags = tmp_path / "old_flags"
    old_flags.write_bytes(buildinfo.make_synthetic_binary(inline_flags=False))
    with pytest.raises(buildinfo.BuildInfoError, match="requires Go 1.18\\+ inline build info"):
        buildinfo.validate(old_flags, "linux/amd64")

    # Truncated file after magic
    raw = buildinfo.make_synthetic_binary()
    offset = raw.find(buildinfo.BUILD_INFO_MAGIC)
    truncated = tmp_path / "truncated"
    truncated.write_bytes(raw[: offset + 20])  # cut off header
    with pytest.raises(buildinfo.BuildInfoError, match="truncated Go buildinfo header"):
        buildinfo.validate(truncated, "linux/amd64")


def test_validate_strict_matching_failures(tmp_path: Path) -> None:
    # Wrong Go version
    bad_vers = tmp_path / "bad_vers"
    bad_vers.write_bytes(buildinfo.make_synthetic_binary(go_version="go1.25.10"))
    with pytest.raises(buildinfo.BuildInfoError, match="does not match required 'go1.26.9'"):
        buildinfo.validate(bad_vers, "linux/amd64")

    # Wrong module
    bad_mod = tmp_path / "bad_mod"
    bad_mod.write_bytes(buildinfo.make_synthetic_binary(module="github.com/evil/mod"))
    with pytest.raises(buildinfo.BuildInfoError, match="does not match required 'github.com/Knowledge-Forge-AI/agentic-praxis-grimoire'"):
        buildinfo.validate(bad_mod, "linux/amd64")

    # Target GOOS mismatch
    good_bin = tmp_path / "good_bin"
    good_bin.write_bytes(buildinfo.make_synthetic_binary(target="linux/amd64"))
    with pytest.raises(buildinfo.BuildInfoError, match="binary GOOS 'linux' does not match target 'darwin'"):
        buildinfo.validate(good_bin, "darwin/arm64")

    # Target GOARCH mismatch
    with pytest.raises(buildinfo.BuildInfoError, match="binary GOARCH 'amd64' does not match target 'arm64'"):
        buildinfo.validate(good_bin, "linux/arm64")

    # CGO_ENABLED != 0
    cgo_bin = tmp_path / "cgo_bin"
    cgo_bin.write_bytes(buildinfo.make_synthetic_binary(target="linux/amd64", cgo_enabled="1"))
    with pytest.raises(buildinfo.BuildInfoError, match="binary CGO_ENABLED '1' must be '0'"):
        buildinfo.validate(cgo_bin, "linux/amd64")

    # -trimpath != true
    notrim_bin = tmp_path / "notrim_bin"
    notrim_bin.write_bytes(buildinfo.make_synthetic_binary(target="linux/amd64", trimpath="false"))
    with pytest.raises(buildinfo.BuildInfoError, match="binary -trimpath 'false' must be 'true'"):
        buildinfo.validate(notrim_bin, "linux/amd64")


def test_validate_nonexistent_or_unframed_modinfo(tmp_path: Path) -> None:
    # Nonexistent binary
    with pytest.raises(buildinfo.BuildInfoError, match="binary file does not exist"):
        buildinfo.validate(tmp_path / "nonexistent", "linux/amd64")

    # Valid binary without sentinel framing in modinfo
    plain_bin = tmp_path / "plain_bin"
    plain_bin.write_bytes(buildinfo.make_synthetic_binary(target="linux/amd64", include_sentinels=False))
    result = buildinfo.validate(plain_bin, "linux/amd64")
    assert result["target"] == "linux/amd64"
    assert result["module"] == "github.com/Knowledge-Forge-AI/agentic-praxis-grimoire"
