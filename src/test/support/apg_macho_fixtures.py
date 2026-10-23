"""Genuine bounded Darwin ARM64 Mach-O fixtures for deployment-seam tests.

Each fixture is a structurally coherent thin little-endian 64-bit ARM64
``MH_EXECUTE`` image: a real 32-byte header, a bounded load-command region and
an aligned Go 1.18+ inline build-info blob.  Every constant is written here
from the Mach-O and Go formats rather than imported from production helpers,
so these bytes are an independent oracle for the shared deployment predicate
in ``libexec/apg_go_build.py``.

Negative fixtures change exactly one property (an over-floor minimum, a bad
command size, a contradictory declaration, ...) and otherwise remain coherent,
so a refusal cannot come from a wrong hash, a missing API or a mocked guard.
These are synthetic test images, not executables, and prove nothing about
native execution or about what an actual Go toolchain emits.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import struct
from typing import Mapping, Sequence

MH_MAGIC_64 = b"\xcf\xfa\xed\xfe"
CPU_TYPE_ARM64 = 0x0100000C
CPU_TYPE_X86_64 = 0x01000007
CPU_SUBTYPE_ARM64_ALL = 0
CPU_SUBTYPE_ARM64E = 2
MH_OBJECT = 1
MH_EXECUTE = 2
MH_FLAGS = 0x00200085  # MH_NOUNDEFS | MH_DYLDLINK | MH_TWOLEVEL | MH_PIE
LC_UUID = 0x1B
LC_VERSION_MIN_MACOSX = 0x24
LC_VERSION_MIN_IPHONEOS = 0x25
LC_BUILD_VERSION = 0x32
PLATFORM_MACOS = 1
PLATFORM_IOS = 2
TOOL_LD = 3

SUPPORTED_MINIMUM = (12, 0, 0)
OVERFLOOR_MINIMUM = (13, 0, 0)

GO_VERSION = "go1.26.9"
MODULE = "github.com/Knowledge-Forge-AI/agentic-praxis-grimoire"
BUILD_INFO_MAGIC = b"\xff Go buildinf:"
INFO_START = bytes.fromhex("3077af0c9274080241e1c107e6d618e6")
INFO_END = bytes.fromhex("f932433186182072008242104116d8f2")
DEFAULT_SETTINGS = (
    ("-buildvcs", "false"),
    ("-trimpath", "true"),
    ("CGO_ENABLED", "0"),
    ("GOARCH", "arm64"),
    ("GOARM64", "v8.0"),
    ("GOOS", "darwin"),
)

Version = tuple[int, int, int]


def encode_version(version: Version) -> int:
    """Encode X.Y.Z as the Mach-O ``xxxx.yy.zz`` nibble layout."""

    major, minor, patch = version
    return (major << 16) | (minor << 8) | patch


def uuid_command() -> bytes:
    """A benign non-version command the predicate must skip."""

    return struct.pack("<2I", LC_UUID, 24) + bytes(range(16))


def build_version_command(
    minimum: Version,
    sdk: Version,
    *,
    platform: int = PLATFORM_MACOS,
    tools: Sequence[tuple[int, int]] = (),
    cmdsize: int | None = None,
) -> bytes:
    """Return one ``LC_BUILD_VERSION`` command with optional tool entries."""

    size = 24 + 8 * len(tools) if cmdsize is None else cmdsize
    body = struct.pack(
        "<6I",
        LC_BUILD_VERSION,
        size,
        platform,
        encode_version(minimum),
        encode_version(sdk),
        len(tools),
    ) + b"".join(struct.pack("<2I", tool, version) for tool, version in tools)
    return _fit(body, size)


def version_min_command(
    minimum: Version,
    sdk: Version,
    *,
    command: int = LC_VERSION_MIN_MACOSX,
    cmdsize: int | None = None,
) -> bytes:
    """Return one ``LC_VERSION_MIN_*`` command."""

    size = 16 if cmdsize is None else cmdsize
    body = struct.pack("<4I", command, size, encode_version(minimum), encode_version(sdk))
    return _fit(body, size)


def _fit(body: bytes, size: int) -> bytes:
    # A deliberately wrong cmdsize still occupies an 8-aligned slot so that
    # only the declared size, not the surrounding layout, is malformed.
    slot = max(len(body), (size + 7) // 8 * 8) if size > 0 else len(body)
    return body.ljust(slot, b"\0")


def _uvarint(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def mod_lines(settings: Mapping[str, str] | None = None) -> list[str]:
    """Return the module-info lines embedded in, and recorded for, a fixture."""

    merged = dict(DEFAULT_SETTINGS)
    merged.update(settings or {})
    return [
        f"path\t{MODULE}/cmd/apgr",
        f"mod\t{MODULE}\t(devel)\t",
        *(f"build\t{key}={value}" for key, value in merged.items()),
    ]


def build_info_blob(*, go_version: str = GO_VERSION, settings: Mapping[str, str] | None = None) -> bytes:
    """Return a 16-byte-aligned Go 1.18+ inline build-info blob."""

    header = BUILD_INFO_MAGIC + b"\x08" + b"\x02" + b"\0" * 16
    modinfo = INFO_START + ("\n".join(mod_lines(settings)) + "\n").encode("utf-8") + INFO_END
    version = go_version.encode("ascii")
    return header + _uvarint(len(version)) + version + _uvarint(len(modinfo)) + modinfo


def darwin_arm64(
    *,
    minimum: Version = SUPPORTED_MINIMUM,
    sdk: Version = SUPPORTED_MINIMUM,
    declarations: Sequence[str | bytes] = ("build_version",),
    magic: bytes = MH_MAGIC_64,
    cputype: int = CPU_TYPE_ARM64,
    cpusubtype: int = CPU_SUBTYPE_ARM64_ALL,
    filetype: int = MH_EXECUTE,
    ncmds: int | None = None,
    sizeofcmds: int | None = None,
    truncate: int | None = None,
    build_info: bool = True,
    go_version: str = GO_VERSION,
    settings: Mapping[str, str] | None = None,
) -> bytes:
    """Return one coherent Darwin ARM64 Mach-O fixture image.

    ``declarations`` names the minimum declarations in command order:
    ``"build_version"`` (LC_BUILD_VERSION, macOS), ``"version_min"``
    (LC_VERSION_MIN_MACOSX), ``"build_version_ios"`` (LC_BUILD_VERSION, iOS
    platform) or ``"version_min_iphoneos"``.  Raw ``bytes`` entries are
    inserted verbatim so a test can supply exactly one malformed command.
    ``ncmds``/``sizeofcmds`` override the otherwise exact header counts.
    """

    commands = [uuid_command()]
    for declaration in declarations:
        if isinstance(declaration, bytes):
            commands.append(declaration)
        elif declaration == "build_version":
            commands.append(build_version_command(minimum, sdk))
        elif declaration == "version_min":
            commands.append(version_min_command(minimum, sdk))
        elif declaration == "build_version_ios":
            commands.append(build_version_command(minimum, sdk, platform=PLATFORM_IOS))
        elif declaration == "version_min_iphoneos":
            commands.append(version_min_command(minimum, sdk, command=LC_VERSION_MIN_IPHONEOS))
        else:
            raise ValueError(f"unknown fixture declaration: {declaration!r}")
    region = b"".join(commands)
    header = magic + struct.pack(
        "<6I",
        cputype,
        cpusubtype,
        filetype,
        len(commands) if ncmds is None else ncmds,
        len(region) if sizeofcmds is None else sizeofcmds,
        MH_FLAGS,
    ) + b"\0" * 4
    image = header + region
    # Zero padding keeps an over-declared region inside the image, so the
    # region-fill check, not end-of-file, decides those negatives.
    image += b"\0" * (64 + (-len(image)) % 16)
    if build_info:
        image += build_info_blob(go_version=go_version, settings=settings)
    image = image.ljust(len(image) + (-len(image)) % 16, b"\0")
    return image if truncate is None else image[:truncate]


def recorded_go_version_m(
    binary_path: Path | str,
    *,
    go_version: str = GO_VERSION,
    settings: Mapping[str, str] | None = None,
) -> str:
    """Return ``go version -m`` text agreeing with a default-shaped fixture."""

    lines = [f"{os.fspath(binary_path)}: {go_version}"]
    lines.extend(f"\t{line}" for line in mod_lines(settings))
    return "\n".join(lines) + "\n"


def binary_manifest(root: Path, target: str, data: bytes) -> bytes:
    """Return canonical manifest bytes for ``data`` under ``root``'s identity.

    The caller must already have the repository ``libexec`` on ``sys.path``.
    The manifest is exact for the fixture bytes, so a seam refusal of an
    over-floor fixture cannot come from a size, hash or identity mismatch.
    """

    import apg_go_build

    version, corpus = apg_go_build.identities(root)
    manifest = apg_go_build._manifest(target=target, version=version, corpus=corpus, binary=data)
    rendered = apg_go_build.render_manifest(manifest)
    assert manifest["sha256"] == hashlib.sha256(data).hexdigest()
    return rendered


def write_artifact(
    directory: Path,
    data: bytes,
    *,
    root: Path,
    target: str = "darwin/arm64",
    recorded: bool = False,
) -> tuple[Path, Path]:
    """Write ``apgr`` (0o755) and its canonical manifest; optionally go-version-m.txt."""

    directory.mkdir(parents=True, exist_ok=True)
    binary = directory / "apgr"
    binary.write_bytes(data)
    binary.chmod(0o755)
    manifest = directory / "apgr.binary-manifest.json"
    manifest.write_bytes(binary_manifest(root, target, data))
    if recorded:
        (directory / "go-version-m.txt").write_text(recorded_go_version_m(binary), encoding="utf-8")
    return binary, manifest
