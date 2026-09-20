"""Provider launch gate and interrupted-recovery proof (APG166ZF).

Real subprocesses prove the gate itself; each fault is injected at the exact
byte boundary it models: before the proceed byte, or after exec.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

import pytest

from agent_phase import interrupted_recovery, provider, provider_launch
from agent_phase.dispatch import DispatchError
from agent_phase.lifecycle import get_lifecycle
from agent_phase.resume_validation import ResumeError
from controller_generation_process import process_identity
from interrupted_run_fixtures import (
    PHASE_ID,
    REQUEST,
    DispositionFakeRunner,
    interrupted_source,
    make_dispatcher,
    read_state,
    tree_bytes,
    write_state,
)
from provider_launch_fixtures import (
    BODY,
    clean_environment,
    kill_group,
    process_gone,
    read_record,
    run_driver,
    wait_until,
    write_executable,
)
from test_agent_phase_disposition_flow import repository as _repository

repository = _repository
STANDARD = get_lifecycle("standard")
ROUTE = {"provider": "claude", "profile": "p"}


def prepare(run_dir: Path, prefix: str = "03-work", stage: str = "work", index: int = 3,
            kind: str = "semantic") -> provider_launch.Binding:
    return provider_launch.prepare(run_dir, run_id="run", stage=stage, prefix=prefix, index=index,
                                   invocation_kind=kind, provider="claude", profile="p")


def proof(run_dir: Path, stage: str | None = "work", launches=("03-work",), **extra):
    state = {"run_id": "run", "provider_launch_contract": provider_launch.SCHEMA,
             "provider_launches": list(launches), **extra}
    return provider_launch.recovery_proof(run_dir, state, stage, routes=lambda _stage: dict(ROUTE),
                                          lifecycle=STANDARD)


def evidence(run_dir: Path, prefix: str = "03-work") -> dict:
    return read_record(run_dir / f"{prefix}.provider-launch.json")


@pytest.fixture
def body(tmp_path, monkeypatch):
    markers = tmp_path / "markers"
    markers.mkdir()
    runs = tmp_path / "run"
    runs.mkdir()
    monkeypatch.setenv("FAKE_MARKER_DIR", str(markers))
    monkeypatch.setenv("FAKE_EVIDENCE", str(runs / "03-work.provider-launch.json"))
    return write_executable(tmp_path / "fake-provider", BODY), markers, runs


def bodies(markers: Path) -> list[dict]:
    return [json.loads(path.read_text()) for path in sorted(markers.glob("body-*.json"))]


# -- the gate ------------------------------------------------------------------

def test_provider_body_runs_only_after_durable_process_facts(body):
    fake, markers, runs = body
    binding = prepare(runs)
    observed = {}

    def barrier(process, argv, cwd, environment):
        # The parent is paused before the proceed byte: facts are durable, the
        # provider has not run, and the hook sees provider argv, not the gate's.
        record = evidence(runs)
        observed.update(phase=record["phase"], pid=process.pid, argv=argv, facts=record["process"])
        import time
        time.sleep(0.3)
        assert not bodies(markers)

    token = provider.PROCESS_CREATION_HOOK.set(barrier)
    try:
        with provider_launch.bound(binding):
            result = provider.run([str(fake)], b"prompt bytes", runs)
    finally:
        provider.PROCESS_CREATION_HOOK.reset(token)

    assert result.exit_code == 0 and result.stdout == b"prompt bytes"
    assert observed["phase"] == provider_launch.AWAITING and observed["argv"] == [str(fake)]
    (ran,) = bodies(markers)
    assert ran["phase"] in (provider_launch.AUTHORIZED, provider_launch.EXEC_CONFIRMED)
    assert ran["pid"] == ran["pgid"] == ran["sid"] == observed["pid"] == observed["facts"]["pid"]
    final = evidence(runs)
    assert final["phase"] == provider_launch.RETURNED
    assert final["terminal"] == {"exit_code": 0, "reaped": True}
    assert final["process"] == observed["facts"]
    assert final["exec"] == {"executable": str(fake),
                             "argv_sha256": hashlib.sha256(json.dumps([str(fake)]).encode()).hexdigest()}
    assert binding.consumed
    assert proof(runs)["records"] == [{
        "name": "03-work.provider-launch.json",
        "sha256": hashlib.sha256((runs / "03-work.provider-launch.json").read_bytes()).hexdigest(),
        "phase": "returned", "classification": "returned"}]


DRIVER = r'''
import os, signal, sys
from pathlib import Path
from agent_phase import provider, provider_launch
mode, run_dir, fake = sys.argv[1:4]
binding = provider_launch.prepare(Path(run_dir), run_id="run", stage="work", prefix="03-work", index=3,
                                  invocation_kind="semantic", provider="claude", profile="p")
if mode == "before-proceed":
    def hook(process, argv, cwd, environment):
        Path(run_dir, "gate.pid").write_text(str(process.pid))
        os.kill(os.getpid(), signal.SIGKILL)
    provider.PROCESS_CREATION_HOOK.set(hook)
    with provider_launch.bound(binding):
        provider.run([fake], b"", Path(run_dir))
else:
    def lose(stream, chunk):
        if b"started" in chunk:
            os.kill(os.getpid(), signal.SIGKILL)
    with provider_launch.bound(binding):
        provider.run([fake], b"", Path(run_dir), on_output=lose)
'''


def test_parent_lost_before_proceed_never_runs_provider(body):
    fake, markers, runs = body
    driver = run_driver(DRIVER, "before-proceed", str(runs), str(fake), environment=clean_environment())
    assert driver.wait(timeout=30) == -signal.SIGKILL
    gate = int((runs / "gate.pid").read_text())
    wait_until(lambda: process_gone(gate))

    assert not bodies(markers), "the provider body must never run"
    record = evidence(runs)
    assert record["phase"] == provider_launch.AWAITING and record["process"]["pid"] == gate
    assert proof(runs)["records"][0]["classification"] == "not_authorized"


def test_live_provider_after_parent_loss_refuses_until_it_ends(body, monkeypatch):
    fake, markers, runs = body
    environment = clean_environment(FAKE_MODE="block")
    driver = run_driver(DRIVER, "after-start", str(runs), str(fake), environment=environment)
    assert driver.wait(timeout=30) == -signal.SIGKILL
    record = evidence(runs)
    pid = record["process"]["pid"]
    try:
        assert record["phase"] == provider_launch.EXEC_CONFIRMED
        assert process_identity(pid) == record["process"]["process_identity"]
        before = tree_bytes(runs)
        with pytest.raises(provider_launch.LaunchEvidenceError) as caught:
            proof(runs)
        assert caught.value.code == "RESUME_RECOVERY_REFUSED"
        assert caught.value.detail.startswith("provider_process_live")
        assert tree_bytes(runs) == before
    finally:
        kill_group(pid)
    wait_until(lambda: process_gone(pid))
    assert proof(runs)["records"][0]["classification"] == "started"


def test_reused_pid_is_not_mistaken_for_the_recorded_provider(tmp_path):
    other = subprocess.Popen([sys.executable, "-c", "import sys; sys.stdin.read()"],
                             stdin=subprocess.PIPE, start_new_session=True)
    try:
        live = process_identity(other.pid)
        pid, *rest = live.split(":")
        older = ":".join([pid, str(int(rest[0]) - 1), *rest[1:]]) if sys.platform == "darwin" \
            else ":".join([pid, rest[0], str(int(rest[1]) - 1)])
        newer = ":".join([pid, str(int(rest[0]) + 1), *rest[1:]]) if sys.platform == "darwin" \
            else ":".join([pid, rest[0], str(int(rest[1]) + 1)])
        outcomes = {}
        for label, identity in (("same", live), ("older", older), ("newer", newer),
                                ("malformed", f"{pid}:x:y")):
            run_dir = tmp_path / label
            run_dir.mkdir()
            binding = prepare(run_dir)
            binding.write(provider_launch.EXEC_CONFIRMED,
                          exec={"executable": "/fake", "argv_sha256": "0" * 64},
                          process={"pid": other.pid, "process_group": other.pid, "session": other.pid,
                                   "process_identity": identity})
            try:
                outcomes[label] = proof(run_dir)["records"][0]["classification"]
            except provider_launch.LaunchEvidenceError as error:
                outcomes[label] = error.detail.split(":")[0]
    finally:
        other.communicate(b"")
    # Only a strictly older recorded incarnation proves the original ended.
    assert outcomes == {"same": "provider_process_live", "older": "started",
                        "newer": "provider_process_identity_ambiguous",
                        "malformed": "provider_process_identity_ambiguous"}


def test_exec_failure_is_a_start_failure_with_retained_evidence(tmp_path):
    binding = prepare(tmp_path)
    missing = str(tmp_path / "no-such-provider")
    with provider_launch.bound(binding), pytest.raises(provider.ProviderStartFailed) as caught:
        provider.run([missing], b"", tmp_path)
    assert str(caught.value).startswith(f"cannot launch {missing}: ")
    record = evidence(tmp_path)
    assert record["phase"] == provider_launch.EXEC_FAILED
    assert record["terminal"]["reaped"] is True and record["terminal"]["exit_code"] == 127
    assert proof(tmp_path)["records"][0]["classification"] == "returned"


def test_creation_hook_failure_withdraws_before_authorization(body):
    fake, markers, runs = body
    binding = prepare(runs)

    def refuse(*_args):
        raise RuntimeError("custody refused")

    token = provider.PROCESS_CREATION_HOOK.set(refuse)
    try:
        with provider_launch.bound(binding), pytest.raises(RuntimeError, match="custody refused"):
            provider.run([str(fake)], b"", runs)
    finally:
        provider.PROCESS_CREATION_HOOK.reset(token)
    assert not bodies(markers)
    record = evidence(runs)
    assert record["phase"] == provider_launch.WITHDRAWN and record["terminal"]["reaped"] is True
    assert proof(runs)["records"][0]["classification"] == "not_authorized"


def test_gated_provider_inherits_default_signal_dispositions(tmp_path):
    # `yes` dies of SIGPIPE (status 141) only when SIGPIPE is not inherited as
    # ignored; the Python gate must restore what restore_signals gives Popen.
    argv = ["/bin/sh", "-c", '(yes; echo "yes-status=$?" >&2) | head -n 1 >/dev/null']
    direct = provider.run(argv, b"", tmp_path)
    with provider_launch.bound(prepare(tmp_path)):
        gated = provider.run(argv, b"", tmp_path)
    assert b"yes-status=141" in direct.stderr
    assert b"yes-status=141" in gated.stderr


@pytest.mark.parametrize("ctype", [None, "C"])
def test_gated_provider_inherits_the_exact_ctype_locale(tmp_path, monkeypatch, ctype):
    # The Python gate coerces a C locale by exporting LC_CTYPE (PEP 538); the
    # provider must still see exactly the environment a direct spawn gives it.
    for name in ("LC_ALL", "LC_CTYPE", "LANG"):
        monkeypatch.delenv(name, raising=False)
    if ctype is not None:
        monkeypatch.setenv("LC_CTYPE", ctype)
    argv = ["/bin/sh", "-c", 'printf "%s" "${LC_CTYPE-unset}"']
    direct = provider.run(argv, b"", tmp_path)
    with provider_launch.bound(prepare(tmp_path)):
        gated = provider.run(argv, b"", tmp_path)
    assert gated.stdout == direct.stdout == (ctype or "unset").encode()


def test_binding_is_single_use_and_prepare_is_create_only(tmp_path):
    binding = prepare(tmp_path)
    with provider_launch.bound(binding):
        provider.run(["/bin/sh", "-c", "exit 0"], b"", tmp_path)
        with pytest.raises(provider.ProviderStartFailed, match="PROVIDER_LAUNCH_EVIDENCE_CONSUMED"):
            provider.run(["/bin/sh", "-c", "exit 0"], b"", tmp_path)
    with pytest.raises(provider_launch.LaunchEvidenceError) as caught:
        prepare(tmp_path)
    assert caught.value.code == "PROVIDER_LAUNCH_EVIDENCE_EXISTS"


def test_evidence_retains_no_prompt_stdin_or_environment_payload(body, monkeypatch):
    fake, _markers, runs = body
    monkeypatch.setenv("APGR_TEST_SECRET", "sentinel-secret-value-7f3a")
    with provider_launch.bound(prepare(runs)):
        provider.run([str(fake)], b"sentinel-prompt-bytes-91c2", runs)
    raw = (runs / "03-work.provider-launch.json").read_bytes()
    for sentinel in (b"sentinel-secret-value-7f3a", b"APGR_TEST_SECRET", b"sentinel-prompt-bytes-91c2",
                     b"PATH", b"HOME"):
        assert sentinel not in raw
    record = json.loads(raw)
    assert set(record) == provider_launch.RECORD_KEYS
    assert set(record["binding"]) == provider_launch.BINDING_KEYS
    assert set(record["process"]) == provider_launch.PROCESS_KEYS
    assert set(record["exec"]) == provider_launch.EXEC_KEYS
    assert (runs / "03-work.provider-launch.json").stat().st_mode & 0o777 == 0o600


# -- the recovery proof ------------------------------------------------------------

def _returned(run_dir: Path, prefix: str = "03-work", **binding) -> Path:
    record = prepare(run_dir, prefix=prefix, **binding)
    record.write(provider_launch.RETURNED, exec={"executable": "/fake", "argv_sha256": "0" * 64},
                 process={"pid": 999999, "process_group": 999999, "session": 999999,
                          "process_identity": "999999:1:1"},
                 terminal={"exit_code": 0, "reaped": True})
    return run_dir / f"{prefix}.provider-launch.json"


def _mutate(path: Path, change) -> None:
    record = json.loads(path.read_text())
    change(record)
    path.write_text(json.dumps(record))


@pytest.mark.parametrize("damage", [
    "missing", "bad_json", "symlink", "extra_key", "unknown_phase", "started_without_process",
    "pid_not_group", "identity_prefix", "other_run", "attempt_mismatch", "route", "copied_retry",
    "unrecorded_started", "unknown_contract", "bad_launch_list", "invoked_without_record",
])
def test_invalid_launch_evidence_refuses(tmp_path, damage):
    path = _returned(tmp_path)
    kwargs: dict = {}
    if damage == "missing":
        path.unlink()
    elif damage == "bad_json":
        path.write_text("{")
    elif damage == "symlink":
        target = tmp_path / "elsewhere.json"
        path.rename(target)
        path.symlink_to(target)
    elif damage == "extra_key":
        _mutate(path, lambda r: r.update(prompt="x"))
    elif damage == "unknown_phase":
        _mutate(path, lambda r: r.update(phase="running"))
    elif damage == "started_without_process":
        _mutate(path, lambda r: r.update(phase="exec_confirmed", process=None))
    elif damage == "pid_not_group":
        _mutate(path, lambda r: r["process"].update(process_group=1))
    elif damage == "identity_prefix":
        _mutate(path, lambda r: r["process"].update(process_identity="1:1:1"))
    elif damage == "other_run":
        _mutate(path, lambda r: r["binding"].update(run_id="other", attempt_id="att-other-work-3"))
    elif damage == "attempt_mismatch":
        _mutate(path, lambda r: r["binding"].update(attempt_id="att-run-work-4"))
    elif damage == "route":
        _mutate(path, lambda r: r["binding"]["route"].update(profile="other"))
    elif damage == "copied_retry":
        path.rename(tmp_path / "03-work.review-retry.provider-launch.json")
        kwargs["launches"] = ("03-work", "03-work.review-retry")
        _returned(tmp_path)
    elif damage == "unrecorded_started":
        kwargs["launches"] = ()
        kwargs["resumed"] = True
    elif damage == "unknown_contract":
        kwargs["provider_launch_contract"] = "apgr-provider-launch-v0"
    elif damage == "bad_launch_list":
        kwargs["launches"] = ("03-work", "03-work")
    else:
        kwargs["launches"] = ()
    with pytest.raises(provider_launch.LaunchEvidenceError) as caught:
        proof(tmp_path, **kwargs)
    assert caught.value.code == "RESUME_PROVIDER_LAUNCH_EVIDENCE_INVALID", caught.value.detail


def test_prepared_or_withdrawn_evidence_recovers_and_legacy_depends_on_stage(tmp_path):
    prepare(tmp_path)
    assert proof(tmp_path)["records"][0]["classification"] == "not_started"
    # A crash between the create-new record and the state write leaves an
    # unrecorded prepared record: nothing could have been spawned yet.
    assert proof(tmp_path, stage=None, launches=())["records"][0]["phase"] == "prepared"
    legacy = {"run_id": "run"}
    assert provider_launch.recovery_proof(tmp_path, legacy, None, routes=dict, lifecycle=STANDARD) is None
    with pytest.raises(provider_launch.LaunchEvidenceError) as caught:
        provider_launch.recovery_proof(tmp_path, legacy, "work", routes=dict, lifecycle=STANDARD)
    assert caught.value.code == "RESUME_RECOVERY_REFUSED"
    assert caught.value.detail.startswith("provider_launch_contract_absent")


# -- dispatcher-written evidence ----------------------------------------------------

def modify(cwd: Path) -> None:
    (cwd / "README.md").write_text("# Interrupted phase edit\n")


def test_dispatcher_records_launch_before_invocation_and_recovers_unstarted_stage(repository, tmp_path):
    source = interrupted_source(repository, tmp_path, modify)
    state = read_state(source)
    assert state["provider_launch_contract"] == provider_launch.SCHEMA
    assert state["provider_launches"] == ["01-plan", "02-plan-review", "03-work"]
    work = read_record(source / "03-work.provider-launch.json")
    assert work["phase"] == "prepared", "the in-process fake runner never spawns a provider"
    assert work["binding"]["attempt_id"] == f"att-{state['run_id']}-work-3"

    interrupted_recovery.ensure(source)

    receipt = json.loads((source / "interrupted-recovery.json").read_text())
    assert [(r["name"], r["classification"]) for r in receipt["provider_launch"]["records"]] == [
        ("01-plan.provider-launch.json", "not_started"),
        ("02-plan-review.provider-launch.json", "not_started"),
        ("03-work.provider-launch.json", "not_started"),
    ]
    assert read_state(source)["provider_launches"] == state["provider_launches"]


def _start_retained(source: Path, prefix: str = "03-work") -> subprocess.Popen:
    """Run the real gate on the dispatcher-written prepared record."""
    path = source / f"{prefix}.provider-launch.json"
    binding = provider_launch.Binding(path, read_record(path))
    return provider_launch.spawn(
        binding, [sys.executable, "-c", "import sys; sys.stdin.read()"],
        lambda args, fds: subprocess.Popen(args, stdin=subprocess.PIPE, pass_fds=fds, start_new_session=True),
        terminate=provider._terminate,
    )


@pytest.fixture
def no_signals(monkeypatch):
    def guarded(real):
        def probe_only(target, signal_number):
            if signal_number != 0:
                raise AssertionError("recovery must never signal a provider")
            return real(target, 0)
        return probe_only

    monkeypatch.setattr(os, "kill", guarded(os.kill))
    monkeypatch.setattr(os, "killpg", guarded(os.killpg))


def test_live_started_provider_refuses_without_writes_then_recovers_idempotently(repository, tmp_path):
    source = interrupted_source(repository, tmp_path, modify)
    live = _start_retained(source)
    try:
        assert read_record(source / "03-work.provider-launch.json")["phase"] == "exec_confirmed"
        before = tree_bytes(source)
        with pytest.raises(ResumeError) as caught:
            interrupted_recovery.ensure(source)
        assert caught.value.code == "RESUME_RECOVERY_REFUSED"
        assert "provider_process_live" in caught.value.detail
        runner = DispositionFakeRunner()
        for dry_run in (True, False):
            with pytest.raises(DispatchError) as dispatched:
                make_dispatcher(repository, tmp_path / f"live-{dry_run}", runner).resume(
                    PHASE_ID, REQUEST, source, dry_run=dry_run, finalization_policy="checkpoint")
            assert dispatched.value.code == "RESUME_RECOVERY_REFUSED"
        assert runner.calls == []
        assert tree_bytes(source) == before
    finally:
        live.communicate(b"")

    record = interrupted_recovery.ensure(source)
    assert record["interrupted_stage"] == "work"
    recovered = tree_bytes(source)
    receipt = json.loads((source / "interrupted-recovery.json").read_text())
    assert receipt["provider_launch"]["records"][-1]["classification"] == "started"
    assert interrupted_recovery.ensure(source) is None
    assert tree_bytes(source) == recovered


def test_dry_run_starts_no_provider_and_writes_nothing(repository, tmp_path, monkeypatch, no_signals):
    source = interrupted_source(repository, tmp_path, modify)
    before = tree_bytes(source)
    monkeypatch.setattr(provider, "_run", lambda *a, **k: pytest.fail("no provider may start"))
    monkeypatch.setattr(provider_launch, "prepare", lambda *a, **k: pytest.fail("no launch may be prepared"))
    preview = make_dispatcher(repository, tmp_path / "dry", provider.run).resume(
        PHASE_ID, REQUEST, source, dry_run=True, finalization_policy="checkpoint")
    assert preview["interrupted_recovery"]["status"] == "qualified_not_materialized"
    assert tree_bytes(source) == before
    assert not (tmp_path / "dry").exists()


@pytest.mark.parametrize("damage", ["deleted", "tampered", "cross_attempt"])
def test_new_contract_source_with_bad_evidence_refuses_before_writes(repository, tmp_path, damage):
    source = interrupted_source(repository, tmp_path, modify)
    path = source / "03-work.provider-launch.json"
    if damage == "deleted":
        path.unlink()
    elif damage == "tampered":
        _mutate(path, lambda r: r.update(phase="exec_confirmed"))
    else:
        path.write_bytes((source / "02-plan-review.provider-launch.json").read_bytes())
    before = tree_bytes(source)
    with pytest.raises(ResumeError) as caught:
        interrupted_recovery.ensure(source)
    assert caught.value.code == "RESUME_PROVIDER_LAUNCH_EVIDENCE_INVALID"
    with pytest.raises(DispatchError) as dispatched:
        make_dispatcher(repository, tmp_path / "refused", DispositionFakeRunner()).resume(
            PHASE_ID, REQUEST, source, finalization_policy="checkpoint")
    assert dispatched.value.code == "RESUME_PROVIDER_LAUNCH_EVIDENCE_INVALID"
    assert tree_bytes(source) == before


def test_legacy_source_between_stages_still_recovers(repository, tmp_path):
    source = interrupted_source(repository, tmp_path, modify)
    state = read_state(source)
    state["stages_invoked"] = state["stages_completed"]
    for key in ("provider_launch_contract", "provider_launches"):
        state.pop(key)
    write_state(source, state)
    for path in source.glob("*.provider-launch.json"):
        path.unlink()
    for path in source.glob("03-work.*"):
        path.unlink()
    record = interrupted_recovery.ensure(source)
    assert record["interrupted_stage"] is None
    assert "provider_launch" not in json.loads((source / "interrupted-recovery.json").read_text())


def test_review_retry_keeps_distinct_launch_evidence(repository, tmp_path):
    from test_agent_phase_review_recovery import REQUEST as REVIEW_REQUEST, ReviewRunner
    from test_agent_phase_dispatch import make_dispatcher as review_dispatcher

    review_dispatcher(repository, tmp_path, ReviewRunner(1, "jsonc")).dispatch("RETRY", REVIEW_REQUEST)
    source = next((tmp_path / "runs").rglob("state.json")).parent
    state = read_state(source)
    semantic = read_record(source / "04-final-review.provider-launch.json")
    retry = read_record(source / "04-final-review.review-retry.provider-launch.json")
    assert semantic["binding"]["prefix"] == "04-final-review"
    assert semantic["binding"]["invocation_kind"] == "semantic"
    assert retry["binding"]["invocation_kind"] == "auxiliary_review_retry"
    assert retry["binding"]["index"] == 4 + STANDARD.expected_provider_invocations
    assert "04-final-review.review-retry" in state["provider_launches"]
    resolved = json.loads((source / "resolved.json").read_text())
    from agent_phase.route_provenance import stage_effective_route
    checked = provider_launch.recovery_proof(
        source, state, None, lifecycle=STANDARD, routes=lambda name: stage_effective_route(resolved, name))
    assert len(checked["records"]) == 6
