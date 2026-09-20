"""ACTIVEUPDATE1 generation pinning for the Gemini Flash parent mode."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time
import tomllib

import pytest
pytest.importorskip("agent_workers", reason="agent_workers subsystem retained in Agent-Central")

from controller_generation_fixtures import GUARDED, git, make_process_reader
from controller_generation_store import coordinate, materialize
from test_controller_generation_real_cli import candidate


ROOT = Path(__file__).resolve().parents[3]
FLASH_MODE = "gemini_flash_sub"
PHASE_TYPES = ("implementation_testing", "architecture_docs", "sysadmin")
STANDARD_SLOTS = ("plan", "plan_review", "work", "final_review", "closeout")
PINNED_FILES = (
    "libexec/agent_workers/gemini_parent.py",
    "libexec/agent_workers/policy.py",
    "libexec/agent_phase/worker_capability.py",
    "common/workers/policy.json",
    "common/skills/agent-worker/SKILL.md",
    "common/dispatcher/routes.toml",
    "common/dispatcher/endpoints.toml",
    "antigravity/GEMINI.md",
    "antigravity/profiles/gemini-3.8-flash-high.json",
)


def _without_flash_routes(raw: bytes) -> bytes:
    lines = raw.decode("utf-8").splitlines(keepends=True)
    result: list[str] = []
    skipping = False
    for line in lines:
        if line.startswith("[routes.") and (
            ".gemini_flash_sub]" in line or ".gemini_flash_opus_sub]" in line
        ):
            skipping = True
            continue
        if skipping and line.startswith("[routes."):
            skipping = False
        if not skipping:
            result.append(line)
    return "".join(result).encode("utf-8")


def _routes(root: Path) -> dict[str, dict[str, dict[str, str]]]:
    return tomllib.loads(
        (root / "common/dispatcher/routes.toml").read_text(encoding="utf-8")
    )["routes"]


def _endpoints(root: Path) -> dict[str, dict[str, str]]:
    return tomllib.loads(
        (root / "common/dispatcher/endpoints.toml").read_text(encoding="utf-8")
    )["endpoints"]


def _is_astra_medium(root: Path, endpoint: dict[str, str]) -> bool:
    if endpoint["provider"] != "codex":
        return False
    profile = root / "codex/profiles" / f"{endpoint['profile']}.config.toml"
    try:
        value = tomllib.loads(profile.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return False
    return (
        value.get("model") == "gpt-6-astra"
        and value.get("model_reasoning_effort") == "medium"
    )


def _reentry_probe(
    root: Path, store: Path, prior: Path, operation: str, flag: str, output: Path
) -> dict:
    driver = r'''
import json, os, sys
from pathlib import Path
root = Path(sys.argv[1])
prior = Path(sys.argv[2])
operation = sys.argv[3]
flag = sys.argv[4]
output = Path(sys.argv[5])
sys.path.insert(0, str(root / "libexec"))
import controller_generation_bootstrap as bootstrap

def capture(executable, argv, environment):
    lease = Path(environment[bootstrap.LEASE_ENV])
    record = json.loads(lease.read_text())
    output.write_text(json.dumps({
        "executable": executable,
        "argv": argv,
        "target": argv[2],
        "generation": record["generation"],
    }))
    lease.unlink()
    raise SystemExit(0)

bootstrap.os.execve = capture
sys.argv = ["agent-phase-" + operation, operation, flag, str(prior)]
bootstrap.enter(root)
raise AssertionError("bootstrap did not select a pinned executable")
'''
    env = os.environ.copy()
    env["AGENT_CENTRAL_GENERATION_STORE"] = str(store)
    env["AGENT_CENTRAL_ACTIVE_ROOT"] = str(root)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("AGENT_CENTRAL_GENERATION_LEASE", None)
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            driver,
            str(root),
            str(prior),
            operation,
            flag,
            str(output),
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(output.read_text(encoding="utf-8"))


def _start_pinned_old_process(
    record: dict,
    active: Path,
    store: Path,
    ready: Path,
    release: Path,
    output: Path,
):
    record_file = output.with_name("old-generation-record.json")
    record_file.write_text(json.dumps(record), encoding="utf-8")
    driver = r'''
import json, os, sys, time
from pathlib import Path
record = json.loads(Path(sys.argv[3]).read_text())
pinned = Path(record["generation_root"])
ready = Path(sys.argv[4])
release = Path(sys.argv[5])
output = Path(sys.argv[6])
sys.path.insert(0, str(pinned / "libexec"))
from controller_generation import LEASE_ENV, activate, create_lease
from controller_generation_store import coordinate
with coordinate(Path(record["controller_root"])) as store:
    lease = create_lease(store, record)
os.environ[LEASE_ENV] = str(lease)
activate(pinned, lease)
ready.write_text("ready\n")
while not release.exists():
    time.sleep(0.02)
from agent_phase.request import RequestError, parse_request
from agent_phase.roster import load_roster
payload = json.dumps({
    "schema": "agent-phase-request-v1",
    "phase_type": "implementation_testing",
    "execution_mode": "gemini_flash_sub",
    "prompt": "old pinned generation probe",
}).encode("utf-8")
try:
    parse_request(payload)
except RequestError as error:
    flash_error = str(error)
else:
    flash_error = None

payload_opus = json.dumps({
    "schema": "agent-phase-request-v1",
    "phase_type": "implementation_testing",
    "execution_mode": "gemini_flash_opus_sub",
    "prompt": "old pinned generation probe opus",
}).encode("utf-8")
try:
    parse_request(payload_opus)
except RequestError as error:
    flash_opus_error = str(error)
else:
    flash_opus_error = None

routes = load_roster(pinned).route_aliases("implementation_testing", "gemini_sub")
output.write_text(json.dumps({
    "flash_error": flash_error,
    "flash_opus_error": flash_opus_error,
    "gemini_sub": routes,
}))
'''
    env = os.environ.copy()
    env["AGENT_CENTRAL_GENERATION_STORE"] = str(store)
    env["AGENT_CENTRAL_ACTIVE_ROOT"] = str(active)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("PYTHONPATH", None)
    expected_cli = Path(record["generation_root"]) / "libexec/agent_phase/cli.py"
    process = subprocess.Popen(
        [
            sys.executable,
            "-B",
            "-c",
            driver,
            str(expected_cli),
            "dispatch",
            str(record_file),
            str(ready),
            str(release),
            str(output),
        ],
        cwd=active,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    deadline = time.monotonic() + 20
    while not ready.exists() and time.monotonic() < deadline:
        if process.poll() is not None:
            stderr = process.stderr.read().decode("utf-8", "replace") if process.stderr else ""
            raise AssertionError(f"old pinned process exited: {stderr}")
        time.sleep(0.02)
    if not ready.exists():
        process.terminate()
        process.wait(timeout=5)
        raise AssertionError("old pinned process did not acquire its generation lease")
    return process


def test_activeupdate1_pins_old_and_new_flash_generations(tmp_path, monkeypatch):
    seed = tmp_path / "seed"
    candidate(seed)
    original_routes = (seed / "common/dispatcher/routes.toml").read_bytes()
    original_request = (seed / "libexec/agent_phase/request.py").read_bytes()

    # Recreate a pre-mode commit by removing only the new enum and route tables.
    (seed / "common/dispatcher/routes.toml").write_bytes(_without_flash_routes(original_routes))
    request_text = original_request.decode("utf-8")
    request_text = request_text.replace('    "gemini_flash_sub",\n', "", 1)
    request_text = request_text.replace('    "gemini_flash_opus_sub",\n', "", 1)
    request_text = request_text.replace('        "gemini_flash_opus_sub",\n', "", 1)
    (seed / "libexec/agent_phase/request.py").write_text(request_text, encoding="utf-8")
    git(seed, "add", "common/dispatcher/routes.toml", "libexec/agent_phase/request.py")
    git(seed, "commit", "-qm", "pre-flash-generation")

    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "--bare", "-q", remote)
    git(seed, "remote", "add", "origin", remote)
    git(seed, "push", "-qu", "origin", "main")
    active = tmp_path / "active"
    git(tmp_path, "clone", "-q", "-b", "main", remote, active)
    git(active, "config", "user.email", "fixture@example.invalid")
    git(active, "config", "user.name", "Generation Fixture")

    store_base = tmp_path / "generation-store"
    monkeypatch.setenv("AGENT_CENTRAL_GENERATION_STORE", str(store_base))
    smoke_request = tmp_path / "flash-smoke.json"
    smoke_request.write_text(
        json.dumps(
            {
                "schema": "agent-phase-request-v1",
                "phase_type": "implementation_testing",
                "execution_mode": FLASH_MODE,
                "prompt": "provider-free generation smoke",
            }
        ),
        encoding="utf-8",
    )
    with coordinate(active) as generation_store:
        old_record = materialize(active, generation_store)
    old_root = Path(old_record["generation_root"])
    old_routes = _routes(old_root)

    ready = tmp_path / "old-ready"
    release = tmp_path / "old-release"
    old_output = tmp_path / "old-result.json"
    process = _start_pinned_old_process(
        old_record, active, store_base, ready, release, old_output
    )
    try:
        # Restore the candidate's new mode in the seed, then publish a real remote commit.
        (seed / "common/dispatcher/routes.toml").write_bytes(original_routes)
        (seed / "libexec/agent_phase/request.py").write_bytes(original_request)
        git(seed, "add", "common/dispatcher/routes.toml", "libexec/agent_phase/request.py")
        git(seed, "commit", "-qm", "flash-generation")
        new_commit = git(seed, "rev-parse", "HEAD").stdout.strip()
        git(seed, "push", "-q", "origin", "main")

        evidence = tmp_path / "evidence-new"
        report = GUARDED._update_active_checkout(
            active,
            evidence,
            smoke_request,
            process_reader=make_process_reader({process.pid}),
        )
        assert report["status"] == "completed"
        assert report["final_head"] == new_commit
        new_record = report["smoke_generation"]
        new_root = Path(new_record["generation_root"])
        new_routes = _routes(new_root)
        endpoints = _endpoints(new_root)
        assert (
            new_routes["implementation_testing"]["gemini_sub"]
            == old_routes["implementation_testing"]["gemini_sub"]
        )
        assert all(
            new_routes[phase]["gemini_sub"] == old_routes[phase]["gemini_sub"]
            for phase in PHASE_TYPES
        )

        # Resolve each phase from the materialized new generation and inspect the real parent identity.
        resolver_env = os.environ.copy()
        resolver_env["AGENT_CENTRAL_GENERATION_STORE"] = str(store_base)
        resolver_env["AGENT_CENTRAL_ACTIVE_ROOT"] = str(active)
        resolver_env["PYTHONDONTWRITEBYTECODE"] = "1"
        resolver_env.pop("AGENT_CENTRAL_GENERATION_LEASE", None)
        resolver_env.pop("PYTHONPATH", None)
        for phase_type in PHASE_TYPES:
            request = tmp_path / f"{phase_type}.json"
            request.write_text(
                json.dumps(
                    {
                        "schema": "agent-phase-request-v1",
                        "phase_type": phase_type,
                        "execution_mode": FLASH_MODE,
                        "prompt": "pinned Flash resolution",
                    }
                ),
                encoding="utf-8",
            )
            resolved = subprocess.run(
                [
                    str(new_root / "bin/agent-phase-resolve"),
                    str(request),
                    "--lifecycle",
                    "standard",
                    "--finalization",
                    "checkpoint",
                ],
                cwd=active,
                env=resolver_env,
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert resolved.returncode == 0, resolved.stderr
            document = json.loads(resolved.stdout)
            assert document["execution_mode"] == FLASH_MODE
            for slot in STANDARD_SLOTS:
                source_alias = new_routes[phase_type]["gemini_sub"][slot]
                target_alias = new_routes[phase_type][FLASH_MODE][slot]
                source_endpoint = endpoints[source_alias]
                target_endpoint = endpoints[target_alias]
                if _is_astra_medium(new_root, source_endpoint):
                    assert target_alias == "antigravity-gemini-high"
                    assert target_endpoint == {
                        "provider": "antigravity",
                        "profile": "gemini-3.8-flash-high",
                    }
                else:
                    assert target_alias == source_alias
                    assert target_endpoint == source_endpoint
                stage = document["stages"][slot]
                assert stage["endpoint_alias"] == target_alias
                if target_endpoint == {
                    "provider": "antigravity",
                    "profile": "gemini-3.8-flash-high",
                }:
                    capability = stage["worker_capability"]
                    assert capability["parent_family"] == "gemini_flash"
                    assert capability["policy_selection"] == "dual_pool_4x4"
                    assert capability["limits"]["max_gemini"] == capability["limits"]["max_luna"] == 4
                    assert capability["limits"]["max_aggregate"] == 8
                    assert capability["borrowing"] is False
                    assert capability["luna_worker"]["transport"] == "codex_external"
                    assert capability["native_worker"] == {"enabled": False}

        for phase_type in PHASE_TYPES:
            request = tmp_path / f"{phase_type}-opus.json"
            request.write_text(
                json.dumps(
                    {
                        "schema": "agent-phase-request-v1",
                        "phase_type": phase_type,
                        "execution_mode": "gemini_flash_opus_sub",
                        "prompt": "pinned Flash Opus resolution",
                    }
                ),
                encoding="utf-8",
            )
            resolved = subprocess.run(
                [
                    str(new_root / "bin/agent-phase-resolve"),
                    str(request),
                    "--lifecycle",
                    "standard",
                    "--finalization",
                    "checkpoint",
                ],
                cwd=active,
                env=resolver_env,
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert resolved.returncode == 0, resolved.stderr
            document = json.loads(resolved.stdout)
            assert document["execution_mode"] == "gemini_flash_opus_sub"
            for slot in STANDARD_SLOTS:
                target_alias = new_routes[phase_type]["gemini_flash_opus_sub"][slot]
                target_endpoint = endpoints[target_alias]
                stage = document["stages"][slot]
                assert stage["endpoint_alias"] == target_alias
                if target_endpoint == {
                    "provider": "antigravity",
                    "profile": "gemini-3.8-flash-high",
                }:
                    capability = stage["worker_capability"]
                    assert capability["parent_family"] == "gemini_flash"
                    assert capability["policy_selection"] == "dual_pool_4x4"
                    assert capability["limits"]["max_gemini"] == capability["limits"]["max_luna"] == 4
                    assert capability["limits"]["max_aggregate"] == 8
                    assert capability["borrowing"] is False
                    assert capability["luna_worker"]["transport"] == "codex_external"
                    assert capability["native_worker"] == {"enabled": False}

        pinned_bytes = {
            relative: (new_root / relative).read_bytes() for relative in PINNED_FILES
        }
        manifest = json.loads(
            (generation_store / "manifests" / f"{new_record['commit']}.json").read_text(
                encoding="utf-8"
            )
        )
        assert all(relative in manifest["entries"] for relative in PINNED_FILES)
        assert all(
            (active / relative).read_bytes() == data
            for relative, data in pinned_bytes.items()
        )

        release.touch()
        process.wait(timeout=10)
        assert process.returncode == 0, process.stderr.read().decode("utf-8", "replace")
        old_result = json.loads(old_output.read_text(encoding="utf-8"))
        assert "unsupported execution_mode" in old_result["flash_error"]
        assert "unsupported execution_mode" in old_result["flash_opus_error"]
        assert old_result["gemini_sub"] == old_routes["implementation_testing"]["gemini_sub"]

        # A later live route/helper/config/guidance edit must not alter the new pinned generation.
        route_file = seed / "common/dispatcher/routes.toml"
        route_bytes = route_file.read_text(encoding="utf-8")
        old_marker = '[routes.implementation_testing.gemini_flash_sub]\nplan = "antigravity-gemini-high"'
        assert route_bytes.count(old_marker) == 1
        route_file.write_text(
            route_bytes.replace(
                old_marker,
                '[routes.implementation_testing.gemini_flash_sub]\nplan = "antigravity-gemini-medium"',
                1,
            ),
            encoding="utf-8",
        )
        (seed / "libexec/agent_workers/gemini_parent.py").write_bytes(
            (seed / "libexec/agent_workers/gemini_parent.py").read_bytes()
            + b"\n# later generation helper\n"
        )
        (seed / "common/workers/policy.json").write_bytes(
            (seed / "common/workers/policy.json").read_bytes() + b"\n"
        )
        (seed / "common/skills/agent-worker/SKILL.md").write_bytes(
            (seed / "common/skills/agent-worker/SKILL.md").read_bytes()
            + b"\nLater generation guidance.\n"
        )
        git(seed, "add", *PINNED_FILES)
        git(seed, "commit", "-qm", "later-route-and-worker-edit")
        later_commit = git(seed, "rev-parse", "HEAD").stdout.strip()
        git(seed, "push", "-q", "origin", "main")
        later_report = GUARDED._update_active_checkout(
            active,
            tmp_path / "evidence-later",
            smoke_request,
            process_reader=make_process_reader(set()),
        )
        assert later_report["status"] == "completed"
        assert later_report["final_head"] == later_commit
        assert (
            (active / "common/dispatcher/routes.toml").read_bytes()
            != pinned_bytes["common/dispatcher/routes.toml"]
        )
        assert (active / "libexec/agent_workers/gemini_parent.py").read_bytes() != pinned_bytes["libexec/agent_workers/gemini_parent.py"]
        assert (active / "common/workers/policy.json").read_bytes() != pinned_bytes["common/workers/policy.json"]
        assert (active / "common/skills/agent-worker/SKILL.md").read_bytes() != pinned_bytes["common/skills/agent-worker/SKILL.md"]
        assert all(
            (new_root / relative).read_bytes() == data
            for relative, data in pinned_bytes.items()
        )

        prior = tmp_path / "prior-run"
        prior.mkdir()
        (prior / "state.json").write_text(
            json.dumps({"controller_generation": new_record}), encoding="utf-8"
        )
        for operation, flag in (("dispatch", "--resume"), ("finalize", "--run")):
            observed = _reentry_probe(
                active,
                store_base,
                prior,
                operation,
                flag,
                tmp_path / f"{operation}-reentry.json",
            )
            assert observed["target"] == str(new_root / "libexec/agent_phase/cli.py")
            assert observed["generation"]["commit"] == new_record["commit"]
            assert observed["generation"]["generation_root"] == str(new_root)
    finally:
        if process.poll() is None:
            release.touch()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
