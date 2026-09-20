"""Focused D1 wrapper/capture repairs using disposable provider executables."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from agent_phase.transmission import SCOPE_ENV
from claude_vc_profile import (
    ProfileError,
    READ_ONLY_TOOLS,
    extract_read_only_tools,
    read_only_contract,
    run_live,
)


ROOT = Path(__file__).resolve().parents[3]


def _executable(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!{sys.executable}\n{body}")
    path.chmod(0o700)
    return path


def _argv_fake(path: Path) -> Path:
    return _executable(
        path,
        """
import json
import os
import pathlib
import sys

if '--version' in sys.argv:
    print('2.1.259')
    raise SystemExit(0)
try:
    tool_value = sys.argv[sys.argv.index('--tools') + 1]
except (ValueError, IndexError):
    tool_value = None
pathlib.Path(os.environ['APGR_TEST_ARGV']).write_text(
    json.dumps({'argv': sys.argv, 'advertised_tools':
                None if tool_value is None else tool_value.split(',')})
)
""",
    )


def _capture_fake(path: Path) -> Path:
    return _executable(
        path,
        """
import json
import os
import sys

mode = os.environ.get('APGR_CAPTURE_MODE', 'nonzero')
if mode == 'truncated':
    sys.stdout.write('{"type":"result"')
    sys.stdout.flush()
    raise SystemExit(0)
print(json.dumps({'type': 'result', 'subtype': 'error', 'is_error': True,
                  'terminal_reason': 'api_error'}), flush=True)
raise SystemExit(7)
""",
    )


def _wrapper_env(tmp_path: Path, fake: Path, argv_record: Path) -> dict[str, str]:
    home = tmp_path / "operator-home"
    home.mkdir()
    environment = dict(os.environ)
    environment.update({
        "PATH": str(fake.parent) + os.pathsep + environment["PATH"],
        "HOME": str(home),
        "APGR_TEST_ARGV": str(argv_record),
    })
    return environment


def test_read_only_tools_reach_real_wrapper_and_fake_argv(tmp_path):
    fake = _argv_fake(tmp_path / "bin" / "claude")
    record = tmp_path / "argv.json"
    environment = _wrapper_env(tmp_path, fake, record)

    result = subprocess.run(
        [str(ROOT / "bin/claude-profile"), "normal-final-review", "--read-only",
         "--read-only-tools", "Read", "-p"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        timeout=10,
        check=False,
    )

    assert result.returncode == 0, result.stderr.decode()
    observed = json.loads(record.read_text())
    argv = observed["argv"]
    assert argv[argv.index("--tools") + 1] == "Read"
    assert observed["advertised_tools"] == ["Read"]
    assert argv[argv.index("--permission-mode") + 1] == "plan"

    record.unlink()
    result = subprocess.run(
        [str(ROOT / "bin/claude-profile"), "normal-final-review", "--read-only", "-p"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode()
    observed = json.loads(record.read_text())
    assert observed["advertised_tools"] == list(READ_ONLY_TOOLS)


@pytest.mark.parametrize(
    "arguments",
    [
        ["--read-only-tools", ""],
        ["--read-only-tools", "Read,Read"],
        ["--read-only-tools", "Bash"],
        ["--read-only-tools", "Read", "--read-only-tools", "Glob"],
        ["--read-only-tools"],
    ],
)
def test_read_only_tools_parser_rejects_unsafe_subsets(arguments):
    with pytest.raises(ProfileError):
        extract_read_only_tools(arguments)


def test_read_only_tools_parser_preserves_native_tail_and_contract_defaults():
    cleaned, selected = extract_read_only_tools(
        ["--read-only-tools=Read,Glob", "-p", "--", "--read-only-tools", "Bash"]
    )
    assert selected == ["Read", "Glob"]
    assert cleaned == ["-p", "--", "--read-only-tools", "Bash"]
    default = read_only_contract(ROOT / "claude", "normal-final-review", headless=True)
    narrowed = read_only_contract(
        ROOT / "claude", "normal-final-review", headless=True, tools=selected
    )
    assert default["tools"] == list(READ_ONLY_TOOLS)
    assert narrowed["tools"] == selected
    with pytest.raises(ProfileError, match="worker facade"):
        read_only_contract(ROOT / "claude", "normal-final-review", tools=["Read"], worker_facade=object())
    with pytest.raises(ProfileError, match="no-tools"):
        read_only_contract(ROOT / "claude", "normal-final-review", tools=["Read"], no_tools=True)


def _live_scope(log_path: Path) -> dict[str, str]:
    return {
        SCOPE_ENV: json.dumps({
            "claude_read_stream": str(log_path),
            "reference": {"path": "plan.json", "sha256": "a" * 64},
            "record": {"run_id": "run", "binding_id": "review", "attempt_id": "one"},
        })
    }


def test_complete_nonzero_capture_retains_v2_receipt_without_logging_failure(tmp_path, capsys):
    fake = _capture_fake(tmp_path / "bin" / "claude")
    log_path = tmp_path / "run" / "stream.jsonl"
    result = run_live(
        str(fake), [str(fake)], _live_scope(log_path), log_path, "raw", "normal-final-review"
    )

    assert result == 7
    receipt = json.loads(log_path.with_suffix(".complete.json").read_text())
    assert receipt["schema"] == "apg.claude-stream-completion/v2"
    assert receipt["process_status"] == 7
    assert b"live logging failed" not in capsys.readouterr().err.encode()


def test_truncated_capture_has_no_completion_receipt(tmp_path, capsys):
    fake = _capture_fake(tmp_path / "bin" / "claude")
    log_path = tmp_path / "run" / "stream.jsonl"
    environment = _live_scope(log_path)
    environment["APGR_CAPTURE_MODE"] = "truncated"
    result = run_live(
        str(fake), [str(fake)], environment, log_path, "raw", "normal-final-review"
    )

    assert result == 1
    assert not log_path.with_suffix(".complete.json").exists()
    assert b"live logging failed" in capsys.readouterr().err.encode()


def test_invalid_line_before_terminal_is_not_complete(tmp_path):
    fake = _capture_fake(tmp_path / "bin" / "claude")
    fake.write_text(fake.read_text().replace("mode = os.environ", "print('invalid-json', flush=True)\nmode = os.environ"))
    log_path = tmp_path / "run" / "stream.jsonl"
    assert run_live(str(fake), [str(fake)], _live_scope(log_path), log_path, "raw", "normal-final-review") == 7
    assert not log_path.with_suffix(".complete.json").exists()


def test_escaped_pipe_holder_cannot_certify_capture(tmp_path, monkeypatch):
    import time
    import claude_vc_profile as wrapper
    done = tmp_path / "descendant-done"
    fake = _executable(tmp_path / "bin" / "claude", f"""
import json, os, time
from pathlib import Path
child = os.fork()
if child == 0:
    os.setsid()
    time.sleep(0.5)
    os.close(1)
    os.close(2)
    Path({str(done)!r}).write_text('closed')
    os._exit(0)
time.sleep(0.05)
print(json.dumps({{'type':'result','subtype':'success','is_error':False}}), flush=True)
""")
    monkeypatch.setattr(wrapper, "STREAM_DRAIN_GRACE_SECONDS", 0.02)
    log_path = tmp_path / "run" / "stream.jsonl"
    assert run_live(str(fake), [str(fake)], _live_scope(log_path), log_path, "raw", "normal-final-review") == 1
    assert not log_path.with_suffix(".complete.json").exists()
    deadline = time.monotonic() + 2
    while not done.exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    assert done.read_text() == "closed"
