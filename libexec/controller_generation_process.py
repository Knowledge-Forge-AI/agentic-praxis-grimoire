"""Process identity for generation controllers and worker processes.

Provides reuse-resistant process identity strings using OS-level birth times
with microsecond resolution (macOS) or boot-id + start-ticks (Linux).
"""

from __future__ import annotations

import ctypes
import ctypes.util
import os
from pathlib import Path
import re
import sys

# macOS proc_info definitions
_PROC_PIDTBSDINFO = 3
_MAXCOMLEN = 16


class _ProcBsdInfo(ctypes.Structure):
    _fields_ = [
        ("pbi_flags", ctypes.c_uint32),
        ("pbi_status", ctypes.c_uint32),
        ("pbi_xstatus", ctypes.c_uint32),
        ("pbi_pid", ctypes.c_uint32),
        ("pbi_ppid", ctypes.c_uint32),
        ("pbi_uid", ctypes.c_uint32),
        ("pbi_gid", ctypes.c_uint32),
        ("pbi_ruid", ctypes.c_uint32),
        ("pbi_rgid", ctypes.c_uint32),
        ("pbi_svuid", ctypes.c_uint32),
        ("pbi_svgid", ctypes.c_uint32),
        ("rfu_1", ctypes.c_uint32),
        ("pbi_comm", ctypes.c_char * _MAXCOMLEN),
        ("pbi_name", ctypes.c_char * (_MAXCOMLEN * 2)),
        ("pbi_nfiles", ctypes.c_uint32),
        ("pbi_pgid", ctypes.c_uint32),
        ("pbi_pjobc", ctypes.c_uint32),
        ("e_tdev", ctypes.c_uint32),
        ("e_tpgid", ctypes.c_uint32),
        ("pbi_nice", ctypes.c_int32),
        ("pbi_start_tvsec", ctypes.c_uint64),
        ("pbi_start_tvusec", ctypes.c_uint64),
    ]


def _process_identity_darwin(pid: int) -> str | None:
    try:
        lib_path = ctypes.util.find_library("proc") or "/usr/lib/libproc.dylib"
        libproc = ctypes.CDLL(lib_path)
        libproc.proc_pidinfo.argtypes = [
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint64,
            ctypes.c_void_p,
            ctypes.c_int,
        ]
        libproc.proc_pidinfo.restype = ctypes.c_int

        info = _ProcBsdInfo()
        ret = libproc.proc_pidinfo(
            ctypes.c_int(pid),
            _PROC_PIDTBSDINFO,
            ctypes.c_uint64(0),
            ctypes.byref(info),
            ctypes.c_int(ctypes.sizeof(info)),
        )
        if ret != ctypes.sizeof(info) or info.pbi_pid != pid:
            return None
        # Verify non-zero birth time
        if info.pbi_start_tvsec == 0 and info.pbi_start_tvusec == 0:
            return None
        return f"{pid}:{info.pbi_start_tvsec}:{info.pbi_start_tvusec}"
    except (OSError, AttributeError, TypeError, ValueError):
        return None


def _get_linux_boot_id() -> str | None:
    try:
        boot_id_file = Path("/proc/sys/kernel/random/boot_id")
        if boot_id_file.is_file():
            text = boot_id_file.read_text(encoding="utf-8").strip()
            if text:
                return text
    except (OSError, UnicodeDecodeError):
        pass

    try:
        proc_stat = Path("/proc/stat")
        if proc_stat.is_file():
            for line in proc_stat.read_text(encoding="utf-8").splitlines():
                if line.startswith("btime "):
                    parts = line.split()
                    if len(parts) >= 2:
                        return f"btime-{parts[1]}"
    except (OSError, UnicodeDecodeError):
        pass

    return None


def _process_identity_linux(pid: int) -> str | None:
    boot_id = _get_linux_boot_id()
    if not boot_id:
        return None

    stat_path = Path(f"/proc/{pid}/stat")
    try:
        content = stat_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    last_paren = content.rfind(")")
    if last_paren == -1:
        return None

    rest = content[last_paren + 1:].split()
    # In Linux /proc/[pid]/stat, field 3 (state) is index 0 of rest.
    # Field 22 (starttime) is at index 19 (22 - 3 = 19).
    if len(rest) < 20:
        return None

    startticks = rest[19]
    return f"{pid}:{boot_id}:{startticks}"


def process_identity(pid: int) -> str | None:
    """Return a unique, reuse-resistant process identity string for the given PID.

    On Linux: uses /proc/<pid>/stat startticks + boot_id.
    On macOS: uses proc_pidinfo PROC_PIDTBSDINFO birth time with microsecond resolution.
    Returns None if the process does not exist, is dead, or if the platform is unknown (fail closed).
    """
    if type(pid) is not int or pid <= 0:
        return None

    if sys.platform == "darwin":
        return _process_identity_darwin(pid)
    elif sys.platform.startswith("linux"):
        return _process_identity_linux(pid)
    return None


def current_process_identity() -> str | None:
    """Return the process identity of the current process."""
    return process_identity(os.getpid())


def identity_supersedes(pid: int, previous: str, observed: str) -> bool:
    """Prove a recorded incarnation is older; never certify the current process.

    Wall-clock lease timestamps are not used as identity or cleanup evidence.
    Unknown formats and backwards birth observations remain ambiguous.
    """
    old, new = previous.split(":"), observed.split(":")
    if len(old) != 3 or len(new) != 3 or old[0] != str(pid) or new[0] != str(pid):
        return False
    if sys.platform == "darwin":
        if not all(value.isdecimal() for value in (*old[1:], *new[1:])):
            return False
        old_birth, new_birth = tuple(map(int, old[1:])), tuple(map(int, new[1:]))
        return (old_birth[0] > 0 and new_birth[0] > 0
                and old_birth[1] < 1000000 and new_birth[1] < 1000000
                and new_birth > old_birth)
    if sys.platform.startswith("linux"):
        boot = r"(?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|btime-[0-9]+)"
        if not all(re.fullmatch(boot, item[1]) and item[2].isdecimal() for item in (old, new)):
            return False
        if old[1].startswith("btime-") and new[1].startswith("btime-") and old[1] != new[1]:
            return int(new[1][6:]) > int(old[1][6:])
        return old[1] != new[1] or int(new[2]) > int(old[2])
    return False


def verify_process_identity(pid: int, expected_identity: str) -> bool:
    """Verify that the process with the given PID matches the expected identity."""
    if not expected_identity or not isinstance(expected_identity, str):
        return False
    current = process_identity(pid)
    return current is not None and current == expected_identity
