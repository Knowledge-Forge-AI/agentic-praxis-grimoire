"""Real-process fixtures for the provider launch gate (APG166ZF).

Providers here are small fake executables; nothing contacts a model. The
driver is a separate dispatcher-side process that a test may SIGKILL at an
exact gate boundary.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from controller_generation_process import process_identity

LIBEXEC = Path(__file__).resolve().parents[3] / "libexec"
WORKER_ENV = ("APGR_WORKER_FACADE", "APGR_DISPATCH_WORKERS", "APGR_PARENT_ID", "APGR_WORKER_STATE_DIR",
              "APGR_WORKERS_REQUIRED", "APGR_DISPATCH_OBSERVATIONS", "APGR_GENERATION_LEASE")

# A provider body that proves when it ran: it records its own process facts
# and the launch-evidence phase it observed before reading any stdin.
BODY = r'''#!{python}
import json, os, pathlib, sys, time
marker = pathlib.Path(os.environ["FAKE_MARKER_DIR"])
evidence = os.environ.get("FAKE_EVIDENCE")
phase = json.loads(pathlib.Path(evidence).read_text())["phase"] if evidence else None
(marker / f"body-{{os.getpid()}}.json").write_text(json.dumps({{
    "pid": os.getpid(), "pgid": os.getpgid(0), "sid": os.getsid(0), "phase": phase}}))
data = sys.stdin.buffer.read()
if os.environ.get("FAKE_MODE") == "block":
    print("started", flush=True)
    time.sleep(600)
sys.stdout.buffer.write(data)
'''

# A lifecycle provider for both Claude and Codex argv shapes. A stage armed by
# ``block-<stage>`` writes worktree residue, signals readiness and blocks.
LIFECYCLE = r'''#!{python}
import json, os, pathlib, re, sys, time
prompt = sys.stdin.read()
state = pathlib.Path(os.environ["FAKE_PROVIDER_DIR"])
match = re.search(r"^stage: ([a-z_]+)$", prompt, re.MULTILINE)
stage = match.group(1) if match else ""
with open(state / "calls.jsonl", "a", encoding="utf-8") as stream:
    stream.write(json.dumps({{"pid": os.getpid(), "pgid": os.getpgid(0), "sid": os.getsid(0),
                             "argv": sys.argv, "stage": stage}}) + "\n")
armed = state / f"block-{{stage}}"
if armed.exists():
    armed.unlink()
    (pathlib.Path.cwd() / "interrupted-work.txt").write_text("written by the killed work stage\n")
    (state / "ready").write_text(str(os.getpid()))
    time.sleep(600)
    sys.exit(3)
if stage == "work":
    (pathlib.Path.cwd() / "work.txt").write_text("work product\n")
phase = re.search(r"<<<AGENT-PHASE-RESULT ([0-9a-f]{{32}})>>>", prompt)
review = re.search(r"<<<AGENT-REVIEW-RESULT ([0-9a-f]{{32}})>>>", prompt)
if phase:
    token = phase.group(1)
    payload = dict(version=1, stage=stage, outcome="completed", body="fake completed",
                   commit_message=dict(subject="Fake provider-launch change", body=""))
    print(f"<<<AGENT-PHASE-RESULT {{token}}>>>\n{{json.dumps(payload)}}\n<<<END-AGENT-PHASE-RESULT {{token}}>>>")
elif review:
    token = review.group(1)
    payload = dict(version=1, stage=stage, outcome="reviewed_with_no_findings", body="fake review")
    print(f"<<<AGENT-REVIEW-RESULT {{token}}>>>\n{{json.dumps(payload)}}\n<<<END-AGENT-REVIEW-RESULT {{token}}>>>")
else:
    print(f"{{stage}} fake output")
'''


def write_executable(path: Path, template: str) -> Path:
    path.write_text(template.format(python=sys.executable))
    path.chmod(0o700)
    return path


def clean_environment(**extra: str) -> dict[str, str]:
    environment = {key: value for key, value in os.environ.items() if key not in WORKER_ENV}
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(LIBEXEC), str(Path(__file__).resolve().parent), os.environ.get("PYTHONPATH", "")])
    environment.update(extra)
    return environment


def read_record(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def wait_until(predicate, timeout: float = 20.0, interval: float = 0.05):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    raise AssertionError("condition not reached before the deadline")


def process_gone(pid: int) -> bool:
    if process_identity(pid) is not None:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    except OSError:
        return False
    return False


def kill_group(pgid: int) -> None:
    try:
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def run_driver(script: str, *arguments: str, environment: dict[str, str]) -> subprocess.Popen:
    return subprocess.Popen([sys.executable, "-c", script, *arguments], env=environment,
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


__all__ = [
    "BODY", "LIFECYCLE", "clean_environment", "kill_group", "process_gone", "read_record",
    "run_driver", "wait_until", "write_executable",
]
