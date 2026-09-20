"""Run-owned executable tripwires for provider-free H qualification.

This is accidental-launch protection, not confinement against a hostile process
running as the same user. Version inspection has a separate runtime owner.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import sys
import time
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Mapping, Sequence

ACTIVE_GUARD = ContextVar("h_provider_free_guard", default=None)
PROVIDERS = frozenset({"codex", "claude", "antigravity"})


class ProviderInvocationError(RuntimeError):
    """Durable launch evidence or changed guard custody invalidated the run."""


def _identity(path):
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or info.st_uid != os.getuid():
        raise ProviderInvocationError("tripwire custody changed")
    return [info.st_dev, info.st_ino, stat.S_IMODE(info.st_mode)]


class LaunchGuard:
    def __init__(self, root: Path):
        self.root = Path(root)
        if not self.root.is_absolute() or self.root.resolve() != self.root:
            raise ValueError("tripwire root must be physical")
        self.root.mkdir(mode=0o700)
        self.events = self.root / "sentinels"
        self.events.mkdir(mode=0o700)
        self.fake_events = self.root / "fake-events"
        self.fake_events.mkdir(mode=0o700)
        self.identities = {
            self.root: _identity(self.root),
            self.events: _identity(self.events),
            self.fake_events: _identity(self.fake_events),
        }
        self.executables = {}
        self.fake_subprocesses: list[dict[str, Any]] = []

    def account_fake_process(self, scenario: str, argv: Sequence[str], pid: int | None = None) -> dict[str, Any]:
        """Record an authorized fake subprocess execution under the tripwire guard."""
        rec = {
            "schema": "apg.h-fake-subprocess/v1",
            "scenario": str(scenario),
            "argv": [str(a) for a in argv],
            "pid": pid,
        }
        idx = len(self.fake_subprocesses)
        name = f"fake-{idx:04d}-{os.getpid()}-{int(time.time() * 1000)}.json"
        target = self.fake_events / name
        with target.open("xb") as s:
            s.write((json.dumps(rec, sort_keys=True, indent=2) + "\n").encode("utf-8"))
            s.flush()
            os.fsync(s.fileno())
        target.chmod(0o600)
        dfd = os.open(self.fake_events, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
        self.fake_subprocesses.append(rec)
        return rec

    def executable(self, provider: str, profile: str) -> str:
        if provider not in PROVIDERS or not isinstance(profile, str) or not profile:
            raise ValueError("provider and profile required")
        key = hashlib.sha256(json.dumps([provider, profile]).encode()).hexdigest()
        path = self.root / (provider + "-" + key)
        if path not in self.executables:
            # Create durable intent before reading stdin: a killed or blocked
            # invocation still invalidates the qualification transaction.
            script = f'''#!{Path(sys.executable).resolve()}
import hashlib, json, os, sys, tempfile
from pathlib import Path
root = Path({str(self.events)!r})
fd, name = tempfile.mkstemp(prefix="invocation-", suffix=".json", dir=root)
cwd = os.stat(".")
record = {{"schema": "apg.h-provider-sentinel/v1", "provider": {provider!r},
          "profile": {profile!r}, "argv_sha256": hashlib.sha256(json.dumps(sys.argv[1:]).encode()).hexdigest(),
          "cwd": {{"path_sha256": hashlib.sha256(os.getcwd().encode()).hexdigest(), "device": cwd.st_dev, "inode": cwd.st_ino}},
          "stdin": {{"status": "not-yet-read"}}}}
def write(fd, value):
    with os.fdopen(fd, "wb") as stream:
        stream.write((json.dumps(value, sort_keys=True) + "\\n").encode())
        stream.flush()
        os.fsync(stream.fileno())
write(fd, record)
digest, size = hashlib.sha256(), 0
if not sys.stdin.isatty():
    while True:
        chunk = sys.stdin.buffer.read(65536)
        if not chunk: break
        size += len(chunk)
        digest.update(chunk)
record["stdin"] = {{"status": "complete", "bytes": size, "sha256": digest.hexdigest()}}
fd, temporary = tempfile.mkstemp(prefix="pending-", dir=root)
write(fd, record)
os.replace(temporary, name)
directory = os.open(root, os.O_RDONLY)
os.fsync(directory)
os.close(directory)
sys.exit(97)
'''
            with path.open("x", encoding="utf-8") as stream:
                stream.write(script)
            path.chmod(0o700)
            self.identities[path] = _identity(path)
            self.executables[path] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assert_clean()
        return str(path)

    def assert_clean(self):
        for path, expected in self.identities.items():
            if _identity(path) != expected:
                raise ProviderInvocationError("tripwire identity changed")
        for path, digest in self.executables.items():
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ProviderInvocationError("tripwire executable changed")
        expected_entries = {self.events, self.fake_events, *self.executables}
        if set(self.root.iterdir()) != expected_entries:
            raise ProviderInvocationError("unexpected tripwire-root entry")
        if list(self.events.iterdir()):
            raise ProviderInvocationError("model/task invocation sentinel observed")
        fake_starts = len(list(self.fake_events.iterdir()))
        return {
            "schema": "apg.h-provider-free-guard/v1",
            "sentinels_observed": 0,
            "real_provider_starts": 0,
            "fake_subprocess_starts": fake_starts,
            "routes": {path.name: digest for path, digest in self.executables.items()},
            "entry_identities": {path.name: identity for path, identity in self.identities.items()
                                 if path != self.root},
            "root_identity": self.identities[self.root],
        }

    def receipt(self) -> dict[str, Any]:
        """Alias returning the guard receipt."""
        return self.assert_clean()

    def path_environment(self, base):
        """Catch accidental native CLI discovery in instrumented test children."""
        for name, provider in (("codex", "codex"), ("claude", "claude"),
                               ("agy", "antigravity"), ("antigravity", "antigravity")):
            source = Path(self.executable(provider, "native-path-boundary"))
            target = self.root / name
            if target not in self.executables:
                with target.open("xb") as stream:
                    stream.write(source.read_bytes())
                target.chmod(0o700)
                self.identities[target] = _identity(target)
                self.executables[target] = hashlib.sha256(target.read_bytes()).hexdigest()
        self.assert_clean()
        return {**base, "PATH": str(self.root) + os.pathsep + base.get("PATH", "")}

    def _on_process_created(
        self,
        process: subprocess.Popen,
        argv: Sequence[str],
        cwd: str,
        environment: Mapping[str, str] | None,
    ) -> dict[str, Any]:
        """Record an authorized fake subprocess execution under the tripwire guard directly at process creation."""
        exe_name = Path(argv[0]).name.lower()
        if exe_name in ("codex", "claude", "antigravity", "agy"):
            resolved_exe = Path(shutil.which(argv[0]) or argv[0]).resolve()
            if resolved_exe in self.executables or not str(resolved_exe).startswith(str(self.root)):
                raise ProviderInvocationError(f"real provider executable attempted under provider-free guard: {argv[0]}")

        if len(self.fake_subprocesses) >= 1:
            raise ProviderInvocationError("duplicate child start observed by tripwire guard")

        env_dict = dict(environment) if environment else {}
        env_digest = hashlib.sha256(json.dumps(sorted(env_dict.items())).encode("utf-8")).hexdigest()
        argv_list = [str(a) for a in argv]
        argv_digest = hashlib.sha256(json.dumps(argv_list).encode("utf-8")).hexdigest()

        rec = {
            "schema": "apg.h-fake-subprocess/v1",
            "pid": process.pid,
            "argv": argv_list,
            "argv_sha256": argv_digest,
            "cwd": str(Path(cwd).resolve()),
            "environment_digest": env_digest,
            "started_at": time.time(),
        }
        idx = len(self.fake_subprocesses)
        name = f"fake-{idx:04d}-{process.pid}-{int(time.time() * 1000)}.json"
        target = self.fake_events / name
        with target.open("xb") as s:
            s.write((json.dumps(rec, sort_keys=True, indent=2) + "\n").encode("utf-8"))
            s.flush()
            os.fsync(s.fileno())
        target.chmod(0o600)
        dfd = os.open(self.fake_events, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
        self.fake_subprocesses.append(rec)
        return rec

    def __enter__(self):
        from agent_phase import provider
        self.token = ACTIVE_GUARD.set(self)
        self.hook_token = provider.PROCESS_CREATION_HOOK.set(self._on_process_created)
        self.assert_clean()
        return self

    def __exit__(self, *exc):
        from agent_phase import provider
        provider.PROCESS_CREATION_HOOK.reset(self.hook_token)
        ACTIVE_GUARD.reset(self.token)
        self.assert_clean()


def verify_retained(root, receipt):
    """Recheck retained tripwire custody without recreating a guard or process."""
    root = Path(root)
    if isinstance(receipt, (str, Path)):
        receipt_data = json.loads(Path(receipt).read_bytes())
        receipt = receipt_data.get("provider_guard", receipt_data)
    elif isinstance(receipt, Mapping) and "provider_guard" in receipt:
        receipt = receipt["provider_guard"]

    if root.resolve() != root or _identity(root) != receipt["root_identity"]:
        raise ProviderInvocationError("retained guard root changed")
    if receipt.get("schema") != "apg.h-provider-free-guard/v1" or receipt.get("sentinels_observed") != 0:
        raise ProviderInvocationError("invalid retained guard receipt")
    if receipt.get("real_provider_starts", 0) != 0:
        raise ProviderInvocationError("real provider starts must be 0")
    routes = receipt["routes"]
    expected_dirs = {root / "sentinels"}
    if (root / "fake-events").exists():
        expected_dirs.add(root / "fake-events")
    if set(root.iterdir()) != {*expected_dirs, *(root / name for name in routes)}:
        raise ProviderInvocationError("retained guard entries changed")
    if list((root / "sentinels").iterdir()):
        raise ProviderInvocationError("model/task invocation sentinel observed")
    for name, expected in receipt["entry_identities"].items():
        if _identity(root / name) != expected:
            raise ProviderInvocationError("retained guard entry changed")
    for name, digest in routes.items():
        path = root / name
        if path.parent != root or _identity(path)[2] != 0o700:
            raise ProviderInvocationError("retained tripwire path changed")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ProviderInvocationError("retained tripwire changed")
    return {
        "status": "clean",
        "sentinels_observed": 0,
        "real_provider_starts": 0,
        "fake_subprocess_starts": receipt.get("fake_subprocess_starts", 0),
        "root": str(root),
    }
