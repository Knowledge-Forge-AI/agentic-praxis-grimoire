from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[6]
SPEC = importlib.util.spec_from_file_location("apg_nix_smoke", ROOT / "libexec/apg_nix_smoke.py")
assert SPEC is not None and SPEC.loader is not None
smoke = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(smoke)


def test_environment_is_allowlisted_and_isolated(tmp_path: Path, monkeypatch) -> None:
    for name, value in {"APGR_OUTBOX_ROOT": "/operator/outbox", "APGR_HOME": "/operator/home",
                        "APGR_GO_BINARY": "/ambient/apgr", "APGR_GENERATION_LEASE": "/lease.json",
                        "PYTHONPATH": "/ambient", "HOME": "/home/operator", "LANG": "C.UTF-8"}.items():
        monkeypatch.setenv(name, value)
    env = smoke._environment(tmp_path, tmp_path / "bin")
    assert env["APGR_OUTBOX_ROOT"] == str(tmp_path / "outbox")
    assert env["APGR_HOME"] == str(tmp_path / "apgr-home")
    assert env["HOME"] == str(tmp_path / "home") and env["TMPDIR"] == str(tmp_path)
    assert "APGR_GO_BINARY" not in env and "APGR_GENERATION_LEASE" not in env and "PYTHONPATH" not in env
    assert env["LANG"] == "C.UTF-8"
    path = env["PATH"].split(":")
    assert path[:2] == [str(tmp_path / "provider-sentinels"), str(tmp_path / "bin")]
    assert sorted(p.name for p in (tmp_path / "provider-sentinels").iterdir()) == list(smoke.PROVIDERS)


def test_run_reports_command_failure_with_bounded_detail(tmp_path: Path) -> None:
    with pytest.raises(smoke.SmokeError, match=r"probe failed \(3\): first \| last"):
        smoke._run(["/bin/sh", "-c", "echo first >&2; echo last >&2; exit 3"],
                   env={"PATH": "/usr/bin:/bin"}, cwd=tmp_path, label="probe")
    assert smoke._run(["/bin/sh", "-c", "echo ok"], env={"PATH": "/usr/bin:/bin"}, cwd=tmp_path,
                      label="probe") == "ok\n"


def test_main_reports_missing_package(tmp_path: Path, capsys) -> None:
    with pytest.raises(FileNotFoundError):
        smoke.main(["--package", str(tmp_path / "missing"), "--target", "darwin/arm64"])
