"""Real-process and real-Git generation cutover regressions."""
from controller_generation_fixtures import (
    Any,
    GUARDED,
    Path,
    controller_generation,
    controller_generation_store,
    cutover_env as _cutover_env,
    git,
    inspect,
    json,
    load_evidence,
    make_process_reader,
    os,
    publish_remote_change,
    pytest,
    start_fixture_dispatcher,
    subprocess,
    sys,
    time,
)

cutover_env = _cutover_env


def test_dirty_development_preserves_worktree_execution(cutover_env):
    layout = cutover_env
    body = "def get_bytes(): return b'development-bytes'\n"
    for name in ("helper.py", "late_import.py"):
        (layout["active"] / "libexec" / name).write_text(body)
    env = os.environ.copy()
    env["AGENT_CENTRAL_ACTIVE_ROOT"] = str(layout["scratch_dir"] / "other-controller")
    result = subprocess.run([sys.executable, "-B", str(layout["active"] / "libexec/agent_phase/cli.py"),
                             "dispatch"], env=env, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr.decode()
    assert result.stdout == b"development-bytes"
    store = controller_generation_store.resolve_controller_dir(layout["active"])
    assert not (store / "leases").exists()


def test_untracked_development_input_preserves_worktree_execution(cutover_env):
    layout = cutover_env
    body = ("from pathlib import Path\n"
            "def get_bytes():\n"
            "    path = Path(__file__).with_name('local-development.txt')\n"
            "    return path.read_bytes() if path.exists() else b'committed-default'\n")
    publish_remote_change(layout, extra_files={"libexec/helper.py": body, "libexec/late_import.py": body})
    git(layout["active"], "pull", "--ff-only")
    (layout["active"] / "libexec/local-development.txt").write_bytes(b'untracked-development')
    env = os.environ.copy()
    env["AGENT_CENTRAL_ACTIVE_ROOT"] = str(layout["scratch_dir"] / "other-controller")
    result = subprocess.run([sys.executable, "-B", str(layout["active"] / "libexec/agent_phase/cli.py"),
                             "dispatch"], env=env, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr.decode()
    assert result.stdout == b"untracked-development"
    store = controller_generation_store.resolve_controller_dir(layout["active"])
    assert not (store / "leases").exists()


@pytest.mark.parametrize("operation,option", [("dispatch", "--resume"), ("finalize", "--run")])
def test_historical_reentry_preserves_generation(cutover_env, operation, option):
    layout = cutover_env
    original, _, release, output = start_fixture_dispatcher(layout)
    store = controller_generation_store.resolve_controller_dir(layout["active"])
    lease = controller_generation.read_record(store / "leases" / f"{original.pid}.json")
    prior = layout["scratch_dir"] / "prior-run"
    prior.mkdir()
    (prior / "state.json").write_text(json.dumps({"controller_generation": lease["generation"]}))
    publish_remote_change(layout)
    git(layout["active"], "pull", "--ff-only")
    resumed, _, resume_release, resume_output = start_fixture_dispatcher(
        layout, bootstrap=True, operation=operation, extra_args=[option, str(prior)])
    resumed_lease = controller_generation.read_record(store / "leases" / f"{resumed.pid}.json")
    assert resumed_lease["generation"] == lease["generation"]
    for process, gate, result in [(original, release, output), (resumed, resume_release, resume_output)]:
        gate.touch()
        process.wait(timeout=5)
        assert process.returncode == 0
        assert result.read_bytes() == b"generation-v1-bytes\n"

def test_production_adapter_signature() -> None:
    """The public production adapter must not expose a process_reader override."""
    assert "process_reader" not in inspect.signature(GUARDED.update_active_checkout).parameters


@pytest.mark.parametrize("same_generation_count", [1, 2])
def test_multiple_safe_generations_permit_update(cutover_env: dict[str, Any], same_generation_count: int) -> None:
    """Multiple active dispatchers pinned to valid generations permit cutover without blocking."""
    layout = cutover_env
    active = layout["active"]
    evidence = layout["evidence"]
    request = layout["request"]

    # Start Dispatcher 1 on Gen 1
    proc1, _, release1, out1 = start_fixture_dispatcher(layout)
    siblings = [start_fixture_dispatcher(layout) for _ in range(same_generation_count - 1)]

    # Publish commit 2 and update active to Gen 2
    commit2 = publish_remote_change(layout, helper_bytes=b"generation-v2-bytes\n")
    reader_gen1 = make_process_reader({proc1.pid, *(p.pid for p, _, _, _ in siblings)})
    report1 = GUARDED._update_active_checkout(active, evidence, request, process_reader=reader_gen1)
    assert report1["status"] == "completed"
    assert report1["final_head"] == commit2

    # Start Dispatcher 2 on Gen 2
    proc2, _, release2, out2 = start_fixture_dispatcher(layout)

    # Publish commit 3
    commit3 = publish_remote_change(layout, helper_bytes=b"generation-v3-bytes\n")

    # Both Dispatcher 1 (pinned to Gen 1) and Dispatcher 2 (pinned to Gen 2) are running
    reader_both = make_process_reader({proc1.pid, proc2.pid, *(p.pid for p, _, _, _ in siblings)})
    evidence3 = layout["scratch_dir"] / "evidence3"
    report2 = GUARDED._update_active_checkout(active, evidence3, request, process_reader=reader_both)

    assert report2["status"] == "completed"
    assert report2["final_head"] == commit3
    safe_pids = {item["pid"] for item in report2["dispatcher_generations"]["safe"]}
    assert proc1.pid in safe_pids
    assert proc2.pid in safe_pids
    assert not report2["dispatcher_generations"]["blockers"]

    for sibling, _, release, output in siblings:
        release.touch()
        sibling.wait(timeout=5)
        assert sibling.returncode == 0 and output.read_bytes() == b"generation-v1-bytes\n"

    # Unblock dispatchers and verify isolated emissions
    release1.write_text("go\n")
    release2.write_text("go\n")
    proc1.wait(timeout=5.0)
    proc2.wait(timeout=5.0)
    assert proc1.returncode == 0
    assert proc2.returncode == 0
    assert out1.read_bytes() == b"generation-v1-bytes\n"
    assert out2.read_bytes() == b"generation-v2-bytes\n"


def test_valid_and_legacy_dispatcher_blocks_update(cutover_env: dict[str, Any]) -> None:
    """A running valid generation dispatcher plus an unleased legacy dispatcher blocks cutover."""
    layout = cutover_env
    active = layout["active"]
    evidence = layout["evidence"]
    request = layout["request"]

    # Start valid leased Dispatcher 1
    proc1, _, release1, _ = start_fixture_dispatcher(layout)

    # Start an unleased legacy dispatcher process running active cli.py
    legacy_cmd = [
        sys.executable,
        "-B",
        "-c",
        "import sys, time\ntime.sleep(20)\n",
        str(active / "libexec/agent_phase/cli.py"),
        "dispatch",
    ]
    legacy_proc = layout["proc_mgr"].spawn(
        legacy_cmd,
        cwd=str(active),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    publish_remote_change(layout)
    initial_head = git(active, "rev-parse", "HEAD").stdout.strip()

    reader = make_process_reader({proc1.pid, legacy_proc.pid})
    with pytest.raises(GUARDED.GuardError) as exc_info:
        GUARDED._update_active_checkout(active, evidence, request, process_reader=reader)

    assert "ACTIVE_DISPATCHER" in str(exc_info.value)
    assert git(active, "rev-parse", "HEAD").stdout.strip() == initial_head
    report = load_evidence(evidence)
    assert report["status"] == "blocked"
    assert report["error_code"] == "ACTIVE_DISPATCHER"
    blocker_pids = [b["pid"] for b in report["active_dispatchers"]]
    assert legacy_proc.pid in blocker_pids
    assert proc1.pid not in blocker_pids

    release1.write_text("go\n")
    legacy_proc.terminate()
    proc1.wait(timeout=5.0)


def test_running_dispatcher_helper_stays_old_after_cutover(cutover_env: dict[str, Any]) -> None:
    """A running dispatcher pinned to Gen 1 continues to run its Gen 1 helper after cutover to Gen 2."""
    layout = cutover_env
    active = layout["active"]
    evidence = layout["evidence"]
    request = layout["request"]

    # Start Dispatcher 1 on Gen 1 and pause at file gate
    proc1, _, release1, out1 = start_fixture_dispatcher(layout)

    # Publish remote change Gen 2
    commit2 = publish_remote_change(layout, helper_bytes=b"generation-v2-bytes\n")

    # Run update cutover
    reader = make_process_reader({proc1.pid})
    report = GUARDED._update_active_checkout(active, evidence, request, process_reader=reader)
    assert report["status"] == "completed"
    assert report["final_head"] == commit2

    # Verify active checkout on disk has changed to Gen 2 bytes
    assert b"generation-v2-bytes" in (active / "libexec/helper.py").read_bytes()

    # Now release gate for Dispatcher 1; it must run its pinned helper and emit Gen 1 bytes
    release1.write_text("go\n")
    proc1.wait(timeout=5.0)
    assert proc1.returncode == 0
    assert out1.read_bytes() == b"generation-v1-bytes\n"


def test_new_startup_after_cutover_runs_new_generation(cutover_env: dict[str, Any]) -> None:
    """A new dispatcher started after cutover materializes and runs from the new generation."""
    layout = cutover_env
    active = layout["active"]
    evidence = layout["evidence"]
    request = layout["request"]

    # Initial cutover to Gen 2
    commit2 = publish_remote_change(layout, helper_bytes=b"generation-v2-bytes\n")
    report = GUARDED._update_active_checkout(active, evidence, request, process_reader=make_process_reader(set()))
    assert report["status"] == "completed"
    assert report["final_head"] == commit2

    # Start new dispatcher from the updated active checkout
    proc, _, release, out = start_fixture_dispatcher(layout)
    release.write_text("go\n")
    proc.wait(timeout=5.0)
    assert proc.returncode == 0
    assert out.read_bytes() == b"generation-v2-bytes\n"


def test_lock_race_old_new_wholly(cutover_env: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    """Store coordination lock contention blocks cutover cleanly without tearing repository state."""
    layout = cutover_env
    active = layout["active"]
    evidence = layout["evidence"]
    request = layout["request"]

    publish_remote_change(layout)
    initial_head = git(active, "rev-parse", "HEAD").stdout.strip()

    monkeypatch.setattr(controller_generation_store, "DEFAULT_LOCK_TIMEOUT", 0.2)

    # Hold the coordination lock externally
    with controller_generation_store.coordinate(active) as store_dir:
        assert store_dir.is_dir()
        with pytest.raises(GUARDED.GuardError) as exc_info:
            GUARDED._update_active_checkout(active, evidence, request, process_reader=make_process_reader(set()))

        assert "CUTOVER_LOCK_FAILED" in str(exc_info.value)
        assert git(active, "rev-parse", "HEAD").stdout.strip() == initial_head
        report = load_evidence(evidence)
        assert report["status"] == "blocked"
        assert report["cutover_lock"] == "unavailable"

    # Once lock is released, cutover wholly succeeds
    evidence2 = layout["scratch_dir"] / "evidence_wholly"
    report2 = GUARDED._update_active_checkout(active, evidence2, request, process_reader=make_process_reader(set()))
    assert report2["status"] == "completed"
    assert report2["final_head"] != initial_head
    assert git(active, "rev-parse", "HEAD").stdout.strip() == report2["final_head"]


def test_stale_dead_pid_does_not_block_update(cutover_env: dict[str, Any]) -> None:
    """A dead process with a leftover lease record is marked stale and does not block update."""
    layout = cutover_env
    active = layout["active"]
    evidence = layout["evidence"]
    request = layout["request"]

    # Start a real dispatcher process and wait for it to exit
    proc, _, release, _ = start_fixture_dispatcher(layout)
    dead_pid = proc.pid
    release.write_text("go\n")
    proc.wait(timeout=5.0)
    assert proc.returncode == 0

    # Ensure process is truly dead
    with pytest.raises(ProcessLookupError):
        os.kill(dead_pid, 0)

    # Lease file should still exist or be present
    store_dir = controller_generation_store.resolve_controller_dir(active)
    lease_file = store_dir / "leases" / f"{dead_pid}.json"
    assert lease_file.exists()

    remote_head = publish_remote_change(layout)
    report = GUARDED._update_active_checkout(active, evidence, request, process_reader=make_process_reader(set()))

    assert report["status"] == "completed"
    assert report["final_head"] == remote_head
    stale_entries = report["dispatcher_generations"]["stale"]
    assert any(entry["pid"] == dead_pid and entry["reason"] == "dead_process" for entry in stale_entries)
    assert not report["dispatcher_generations"]["blockers"]


def test_identity_mismatch_blocks_update(cutover_env: dict[str, Any]) -> None:
    """A lease whose recorded birth identity mismatches the living process blocks cutover."""
    layout = cutover_env
    active = layout["active"]
    evidence = layout["evidence"]
    request = layout["request"]

    # Spawn a living dummy process
    dummy = layout["proc_mgr"].spawn(
        [sys.executable, "-c", "import time\ntime.sleep(20)\n"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Materialize generation to get valid record
    store_dir = controller_generation_store.resolve_controller_dir(active)
    with controller_generation_store.coordinate(active) as cdir:
        gen = controller_generation_store.materialize(active, cdir)

    # Write a forged lease with mismatched identity for the living PID
    leases_dir = store_dir / "leases"
    leases_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    mismatched_lease = leases_dir / f"{dummy.pid}.json"
    controller_generation.write_record(
        mismatched_lease,
        {
            "schema": "controller-generation-lease-v1",
            "pid": dummy.pid,
            "process_identity": f"{dummy.pid}:999999:0",
            "created_at": time.time(),
            "run_id": None,
            "status": "running",
            "generation": gen,
        },
    )

    publish_remote_change(layout)
    initial_head = git(active, "rev-parse", "HEAD").stdout.strip()

    with pytest.raises(GUARDED.GuardError) as exc_info:
        GUARDED._update_active_checkout(active, evidence, request, process_reader=make_process_reader({dummy.pid}))

    assert "ACTIVE_DISPATCHER" in str(exc_info.value)
    assert git(active, "rev-parse", "HEAD").stdout.strip() == initial_head
    report = load_evidence(evidence)
    assert report["status"] == "blocked"
    assert any(b.get("pid") == dummy.pid for b in report["active_dispatchers"])


def test_malformed_missing_tampered_generation_blocks_update(cutover_env: dict[str, Any]) -> None:
    """Unexpected lease entries, corrupted lease records, and tampered generation roots block cutover."""
    layout = cutover_env
    active = layout["active"]
    evidence = layout["evidence"]
    request = layout["request"]
    store_dir = controller_generation_store.resolve_controller_dir(active)
    store_dir.mkdir(mode=0o700, exist_ok=True)
    leases_dir = store_dir / "leases"
    leases_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

    # Case A: Unexpected non-decimal entry in lease directory
    bogus_file = leases_dir / "non_decimal_pid.json"
    bogus_file.write_text("{}", encoding="utf-8")

    with pytest.raises(GUARDED.GuardError) as exc_info:
        GUARDED._update_active_checkout(active, evidence, request, process_reader=make_process_reader(set()))
    assert "ACTIVE_DISPATCHER" in str(exc_info.value)
    bogus_file.unlink()

    # Case B: Malformed JSON lease
    malformed_lease = leases_dir / "123456.json"
    malformed_lease.write_text("{not-valid-json", encoding="utf-8")
    with pytest.raises(GUARDED.GuardError) as exc_info:
        GUARDED._update_active_checkout(active, evidence.with_name("evidence-malformed"), request, process_reader=make_process_reader(set()))
    assert "ACTIVE_DISPATCHER" in str(exc_info.value)
    malformed_lease.unlink()

    # Case C: Tampered generation root while dispatcher is running
    proc, _, release, _ = start_fixture_dispatcher(layout)
    gen_root = store_dir / "objects" / layout["base_commit"]
    tampered_file = gen_root / "libexec/helper.py"

    try:
        os.chmod(tampered_file, 0o600)
        tampered_file.write_bytes(b"tampered-content\n")
        os.chmod(tampered_file, 0o400)

        with pytest.raises(GUARDED.GuardError) as exc_info:
            GUARDED._update_active_checkout(active, evidence.with_name("evidence-tampered"), request, process_reader=make_process_reader({proc.pid}))
        assert "ACTIVE_DISPATCHER" in str(exc_info.value)
    finally:
        release.write_text("go\n")
        proc.wait(timeout=5.0)


def test_smoke_failure_truthful_head_and_old_dispatchers_stay_alive(cutover_env: dict[str, Any]) -> None:
    """Post-merge smoke failure reports updated_verification_failed, truthfully records HEAD, and leaves old dispatchers alive."""
    layout = cutover_env
    active = layout["active"]
    evidence = layout["evidence"]
    request = layout["request"]

    # Start Dispatcher 1 on Gen 1
    proc1, _, release1, out1 = start_fixture_dispatcher(layout)

    # Publish remote change that intentionally breaks provider-free smoke
    broken_commit = publish_remote_change(
        layout,
        helper_bytes=b"broken-bytes\n",
        extra_files={"tools/add_dispatcher_roster_operator_directions.py": "#!/usr/bin/env python3\nimport sys\nsys.exit(99)\n"},
    )

    reader = make_process_reader({proc1.pid})
    with pytest.raises(GUARDED.GuardError) as exc_info:
        GUARDED._update_active_checkout(active, evidence, request, process_reader=reader)

    assert "SMOKE_FAILED" in str(exc_info.value)
    report = load_evidence(evidence)

    # Truthful HEAD reporting and recovery guidance
    assert report["status"] == "updated_verification_failed"
    assert report["final_head"] == broken_commit
    assert report["active_generation_after"]["commit"] == broken_commit
    assert "repair forward" in report["recovery"]
    assert "do not reset or terminate pinned runs" in report["recovery"]

    # Old generation dispatcher must still be alive and functional
    assert proc1.poll() is None
    release1.write_text("go\n")
    proc1.wait(timeout=5.0)
    assert proc1.returncode == 0
    assert out1.read_bytes() == b"generation-v1-bytes\n"


def test_injected_previous_cutover_mismatch_is_reported(cutover_env: dict[str, Any]) -> None:
    """An injected last-cutover mismatch is reported; this does not perform a manual pull."""
    layout = cutover_env
    active = layout["active"]
    evidence = layout["evidence"]
    request = layout["request"]

    # Start Dispatcher 1 on Gen 1
    proc1, _, release1, out1 = start_fixture_dispatcher(layout)

    # Record an artificial previous cutover in last-cutover.json
    store_dir = controller_generation_store.resolve_controller_dir(active)
    movement_file = store_dir / "last-cutover.json"
    controller_generation.write_record(movement_file, {"schema": "controller-cutover-v1", "commit": "0" * 40})

    remote_head = publish_remote_change(layout, helper_bytes=b"generation-v2-bytes\n")
    reader = make_process_reader({proc1.pid})
    report = GUARDED._update_active_checkout(active, evidence, request, process_reader=reader)

    assert report["status"] == "completed"
    assert report["unsupervised_movement"] is True
    assert report["final_head"] == remote_head
    assert controller_generation.read_record(movement_file)["commit"] == remote_head

    # Old dispatcher remains safe
    release1.write_text("go\n")
    proc1.wait(timeout=5.0)
    assert proc1.returncode == 0
    assert out1.read_bytes() == b"generation-v1-bytes\n"


def test_no_argv_prompt_leakage(cutover_env: dict[str, Any]) -> None:
    """Prompts, secret flags, and arbitrary command-line arguments are never leaked into records or reports."""
    layout = cutover_env
    active = layout["active"]
    evidence = layout["evidence"]
    request = layout["request"]

    secret_prompt = "TOP_SECRET_USER_PROMPT_PAYLOAD_987654"
    secret_token = "BEARER_TOKEN_CLASSIFIED_SECRET_XYZ"

    # Start dispatcher with secret prompt flags
    proc1, _, release1, _ = start_fixture_dispatcher(
        layout,
        extra_args=["--prompt", secret_prompt, "--token", secret_token],
    )

    # Spawn legacy blocker with secret flag
    legacy_proc = layout["proc_mgr"].spawn(
        [
            sys.executable,
            "-B",
            "-c",
            "import sys, time\ntime.sleep(20)\n",
            str(active / "libexec/agent_phase/cli.py"),
            "dispatch",
            f"--secret-flag={secret_token}",
        ],
        cwd=str(active),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    publish_remote_change(layout)
    reader = make_process_reader({proc1.pid, legacy_proc.pid})

    with pytest.raises(GUARDED.GuardError):
        GUARDED._update_active_checkout(active, evidence, request, process_reader=reader)

    report_text = (evidence / "guarded-active-checkout-update.json").read_text(encoding="utf-8")
    assert secret_prompt not in report_text
    assert secret_token not in report_text

    # Check all files in store
    store_dir = controller_generation_store.resolve_controller_dir(active)
    for root, _, files in os.walk(store_dir):
        for f in files:
            content = (Path(root) / f).read_bytes()
            assert secret_prompt.encode("utf-8") not in content
            assert secret_token.encode("utf-8") not in content

    # Check active_dispatchers blocker payload structure
    report = json.loads(report_text)
    for blocker in report.get("active_dispatchers", []):
        assert set(blocker.keys()) <= {
            "pid",
            "ppid",
            "executable",
            "source_context",
            "source_context_observed",
            "cwd",
        }

    release1.write_text("go\n")
    legacy_proc.terminate()
    proc1.wait(timeout=5.0)


def test_operator_root_and_codex_profile_arguments(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify operator_root resolution and codex_profile_arguments flattening."""
    gen_root = tmp_path / "gen_root"
    ctrl_root = tmp_path / "ctrl_root"
    gen_root.mkdir()
    ctrl_root.mkdir()

    # Without binding
    assert controller_generation.operator_root(gen_root) == gen_root
    assert controller_generation.codex_profile_arguments(gen_root, "default") == ["--profile", "default"]

    # With binding
    lease_file = tmp_path / "lease.json"
    lease_data = {
        "schema": controller_generation.SCHEMA,
        "generation": {
            "controller_root": str(ctrl_root),
            "generation_root": str(gen_root),
        },
    }
    controller_generation.write_record(lease_file, lease_data)
    monkeypatch.setenv(controller_generation.LEASE_ENV, str(lease_file))

    assert controller_generation.operator_root(gen_root) == ctrl_root

    profiles_dir = gen_root / "codex/profiles"
    profiles_dir.mkdir(parents=True)
    (profiles_dir / "custom.config.toml").write_text(
        '[model]\nfamily = "gpt-6"\ntemperature = 0\nenable_feature = true\n', encoding="utf-8"
    )

    args = controller_generation.codex_profile_arguments(gen_root, "custom")
    assert "-c" in args
    assert 'model.family="gpt-6"' in args
    assert "model.temperature=0" in args
    assert "model.enable_feature=true" in args
