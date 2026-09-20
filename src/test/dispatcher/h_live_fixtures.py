"""Disposable external-authority fixtures for granted-live H tests.

Every provider here is a local fake executable that counts its starts.  The
decision and grant records are authored by the test in a private custody root
outside the source tree; they authorize only these fakes.  Mechanical evidence
recomputation is replaced by a deterministic seam that still binds the real
current source identity, because a full provider-free transaction belongs to
the separately authorized host run.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import sys
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

from testing.h_eval import live_admission, readiness
from testing.h_eval.evaluate import PRIMARY
from testing.h_eval.runtime_manifest import (
    REQUIRED_COMMANDS,
    REQUIRED_GROUPS,
    capture_complete,
    manifest_digest,
    seal,
)

ROOT = Path(__file__).resolve().parents[3]


def _stamp(delta: timedelta) -> str:
    return (datetime.now(timezone.utc) + delta).strftime("%Y-%m-%dT%H:%M:%SZ")


def binary_pattern(size: int) -> bytes:
    """Deterministic non-UTF-8 stream bytes of an exact length."""
    return (bytes(range(256)) * (size // 256 + 1))[:size]


def fake_provider(
    directory: Path,
    *,
    exit_code: int = 0,
    write: str | None = None,
    stdout: bool | bytes = True,
    stderr: bytes = b"",
    stderr_bytes: int = 0,
    replace: str | None = None,
    chmod: tuple[str, int] | None = None,
    create: tuple[str, bytes] | None = None,
) -> tuple[Path, Path]:
    """Codex-wire fake that counts non-version starts and optionally edits a file.

    The remaining options act once per counted start: ``stdout`` false emits
    no stdout and bytes emit exactly those bytes; ``stderr`` and
    ``stderr_bytes`` (``binary_pattern``) write raw stderr; ``replace``
    rewrites a file with its own bytes and mode through a new inode;
    ``chmod`` changes one mode; ``create`` writes bytes at a path that may be
    relative to the subject working directory.
    """
    directory.mkdir(parents=True, exist_ok=True)
    counter = directory / "starts"
    script = directory / "fake-codex"
    actions = []
    if write is not None:
        actions.append(f"Path({write!r}).write_text('edited by fake provider\\n')")
    if replace is not None:
        actions += [f"target = Path({replace!r})",
                    "staged = target.with_name(target.name + '.fake-replace')",
                    "staged.write_bytes(target.read_bytes())",
                    "os.chmod(staged, stat.S_IMODE(target.stat().st_mode))",
                    "os.replace(staged, target)"]
    if chmod is not None:
        actions.append(f"os.chmod({chmod[0]!r}, {chmod[1]!r})")
    if create is not None:
        actions.append(f"Path({create[0]!r}).write_bytes({create[1]!r})")
    if stdout is True:
        actions += [
            "print(json.dumps({'type': 'thread.started', 'thread_id': 'fake-thread', 'model': 'fake-model'}))",
            "print(json.dumps({'type': 'result', 'status': 'completed', 'result': 'fixture'}))",
        ]
    elif stdout is not False:
        actions += [f"sys.stdout.buffer.write({bytes(stdout)!r})", "sys.stdout.flush()"]
    if stderr:
        actions.append(f"sys.stderr.buffer.write({bytes(stderr)!r})")
    if stderr_bytes:
        actions.append(f"sys.stderr.buffer.write((bytes(range(256)) * ({stderr_bytes} // 256 + 1))[:{stderr_bytes}])")
    script.write_text(
        f"#!{sys.executable}\n"
        "import json, os, stat, sys\n"
        "from pathlib import Path\n"
        "if sys.argv[1:] == ['--version']:\n"
        "    print('fake-codex 0.0-test')\n"
        "    raise SystemExit(0)\n"
        f"counter = Path({str(counter)!r})\n"
        "counter.write_text(str(int(counter.read_text()) + 1) if counter.exists() else '1')\n"
        "sys.stdin.buffer.read()\n"
        + "".join(f"{line}\n" for line in actions)
        + "sys.stdout.flush()\n"
        "sys.stderr.flush()\n"
        f"raise SystemExit({exit_code})\n"
    )
    script.chmod(0o700)
    return script, counter


def starts(counter: Path) -> int:
    return int(counter.read_text()) if counter.exists() else 0


def sealed_runtime(provider: Path, home: Path) -> dict:
    """Bind the counting provider separately from a non-counting tool fake."""
    git = Path(shutil.which("git") or "/usr/bin/git")
    home.mkdir(parents=True, exist_ok=True)
    tool = provider.parent / "fake-tool"
    tool.write_text(f"#!{sys.executable}\nprint('fake-tool 0.0-test')\n")
    tool.chmod(0o700)
    return seal(capture_complete(
        providers={name: (provider, ["--version"]) for name in ("codex", "claude", "antigravity")},
        commands={name: ((git, ["--version"]) if name == "git" else (tool, ["--version"]))
                  for name in REQUIRED_COMMANDS},
        groups={group: [ROOT / "README.md"] for group in REQUIRED_GROUPS},
        routes={"fixture": "granted-live"},
        absent_settings=[home / "absent-setting"],
        environment={"home": str(home), "temp_root": str(home)},
    ))


def _write_private(path: Path, value) -> dict:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    data = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    path.write_bytes(data)
    path.chmod(0o600)
    return {"path": str(path), "sha256": hashlib.sha256(data).hexdigest()}


def report_group_writable(monkeypatch, path) -> None:
    """Make lstat report group write for one record; its disk mode is unchanged.

    Only st_mode differs from the real stat, so a refusal is attributable to
    the mode check and no fixture file is ever group-writable on disk.
    """
    target = Path(path)
    real = Path.lstat

    def lstat(candidate, *args, **kwargs):
        info = real(candidate, *args, **kwargs)
        if candidate != target:
            return info
        fields = list(info)
        fields[stat.ST_MODE] = info.st_mode | stat.S_IWGRP
        return os.stat_result(fields)

    monkeypatch.setattr(Path, "lstat", lstat)


class Authority:
    """Author one decision and any number of grants for one fake runtime."""

    def __init__(self, tmp_path: Path, monkeypatch, runtime: dict):
        self.tmp = tmp_path
        self.monkeypatch = monkeypatch
        self.custody = tmp_path / "custody"
        self.custody.mkdir(mode=0o700)
        self.runtime = runtime
        self.transaction = str(tmp_path / "retained-transaction")
        facts = live_admission.source_facts(ROOT)
        self.facts = facts
        seal_value = {"schema": "fixture-readiness", "source_identity": facts["source_identity"],
                      "mechanical_package": {"provider_free_mechanical_candidate": True,
                                             "source_identity": facts["source_identity"]}}
        self.readiness_value = seal_value

        def recomputed(root, evidence=None, **_kwargs):
            assert evidence == {"transaction_directory": self.transaction}
            return deepcopy(self.readiness_value)

        monkeypatch.setattr(readiness, "make_ready1_seal", recomputed)
        evidence = tmp_path / "evidence"
        self.evidence = {
            "readiness_seal": _write_private(evidence / "readiness.json", seal_value),
            "package_seal": _write_private(evidence / "package.json", seal_value["mechanical_package"]),
            "host_mechanical_result": _write_private(evidence / "host.json", {
                "schema": "apg166v-h-mechanical-host/v1", "status": "passed", "live_provider_starts": 0,
                "source_unchanged": True, "transaction_directory": self.transaction,
                "source": {"source_identity": facts["source_identity"]},
                "checks": {"scenario_records": 15, "equal_initial_trees": 15, "unchanged_subject_pairs": 15,
                           "promotion_fixture_pairs": 25, "provider_invocations": 0, "sentinels": 0,
                           "package_seal_valid": True, "readback_valid": True}}),
            "d1_decision": _write_private(evidence / "d1.json", {"external": "D1 acceptance/replay"}),
            "installed_home_comparison": _write_private(evidence / "installed.json", {"equal": True}),
            "skill_approvals": {skill: _write_private(evidence / f"{skill}.json", {"skill": skill})
                                for skill in PRIMARY},
        }
        self.decision = self.decision_record()
        self.decision_path = self.write_decision(self.decision)

    def decision_record(self, **changes) -> dict:
        value = {
            "schema": live_admission.DECISION_SCHEMA, "decision_id": "test-decision",
            "disposition": live_admission.DISPOSITION, "cohort_decision": live_admission.COHORT_DECISION,
            "scenario15": live_admission.SCENARIO15, "issued_at": _stamp(timedelta(minutes=-5)),
            "custody_root": str(self.custody), "source": dict(self.facts),
            "routes": live_admission.route_map(ROOT),
            "runtime": {"live_runtime_manifest_sha256": manifest_digest(self.runtime),
                        "transaction_directory": self.transaction},
            "evidence": deepcopy(self.evidence), "native_read_qualification": None,
        }
        value.update(changes)
        value["decision_sha256"] = live_admission.self_digest(value, "decision_sha256")
        return value

    def write_decision(self, value: dict, name: str = "decision.json") -> Path:
        return Path(_write_private(self.custody / name, value)["path"])

    def grant(self, units, *, name: str = "grant.json", redigest: bool = True, **changes) -> dict:
        value = {
            "schema": live_admission.GRANT_SCHEMA, "grant_id": name,
            "decision_sha256": self.decision["decision_sha256"], "custody_root": str(self.custody),
            "units": list(units), "start_ceiling": len(units), "max_starts_per_unit": 1,
            "replay_prohibited": True, "retries": 0, "valid_until": _stamp(timedelta(hours=1)),
            "evaluation_seal": None, "evaluation_binary": None,
        }
        value.update(changes)
        if redigest:
            value["grant_sha256"] = live_admission.self_digest(value, "grant_sha256")
        path = Path(_write_private(self.custody / name, value)["path"])
        return {"decision_path": str(self.decision_path), "grant_path": str(path)}

    def report_group_writable(self, path) -> None:
        report_group_writable(self.monkeypatch, path)
