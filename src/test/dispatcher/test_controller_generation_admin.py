"""Real Git/process GC boundaries and startup contention with an actual cutover."""
import os
from pathlib import Path
import threading
import time

import pytest

from controller_generation_admin import inspect
from controller_generation_store import coordinate, materialize
from controller_generation_fixtures import cutover_env as _cutover_env, git, publish_remote_change, start_fixture_dispatcher, make_process_reader, GUARDED

cutover_env = _cutover_env


def retained_history(layout):
    records = []
    for index in range(6):
        if index:
            publish_remote_change(layout, helper_bytes=f"generation-{index}\n".encode())
            git(layout["active"], "pull", "--ff-only")
        with coordinate(layout["active"]) as store:
            records.append(materialize(layout["active"], store))
    return records


def test_gc_keeps_live_current_and_recent_and_deletes_exact_roots(cutover_env):
    layout = cutover_env
    child, _, release, output = start_fixture_dispatcher(layout)
    records = retained_history(layout)
    outside = layout["scratch_dir"] / "operator-data"
    outside.write_bytes(b"untouched")
    preview = inspect(layout["active"], gc=True)
    assert preview["provider_invocations"] == 0
    assert set(preview["gc"]["eligible"]) == {r["commit"] for r in records[1:3]}
    report = inspect(layout["active"], gc=True, apply=True)
    assert report["gc"]["deleted"] == preview["gc"]["eligible"]
    assert Path(records[0]["generation_root"]).is_dir()
    assert all(Path(r["generation_root"]).is_dir() for r in records[3:])
    assert outside.read_bytes() == b"untouched"
    assert child.poll() is None
    release.touch()
    child.wait(timeout=5)
    assert child.returncode == 0 and output.read_bytes() == b"generation-v1-bytes\n"


def test_gc_rejects_symlink_escape_before_any_deletion(cutover_env):
    layout = cutover_env
    records = retained_history(layout)
    target = Path(records[0]["generation_root"])
    retained = target.with_name("operator-saved")
    target.rename(retained)
    target.symlink_to(retained, target_is_directory=True)
    before = (retained / "libexec/helper.py").read_bytes()
    with pytest.raises(RuntimeError):
        inspect(layout["active"], gc=True, apply=True)
    assert (retained / "libexec/helper.py").read_bytes() == before
    assert all(Path(r["generation_root"]).exists() for r in records[1:])


def test_new_startup_waits_for_cutover_then_loads_wholly_new(cutover_env, monkeypatch):
    layout = cutover_env
    new_head = publish_remote_change(layout, helper_bytes=b"new-after-race\n")
    at_merge, release_merge = threading.Event(), threading.Event()
    original = GUARDED._run
    results, failures = [], []
    def paused(argv, **kwargs):
        if argv[:3] == ["git", "merge", "--ff-only"]:
            at_merge.set()
            assert release_merge.wait(10)
        return original(argv, **kwargs)
    monkeypatch.setattr(GUARDED, "_run", paused)
    def update():
        try:
            results.append(GUARDED._update_active_checkout(
                layout["active"], layout["evidence"], layout["request"],
                process_reader=make_process_reader(set())))
        except BaseException as error:
            failures.append(error)
    thread = threading.Thread(target=update)
    thread.start()
    try:
        assert at_merge.wait(10)
        child, ready, release, output = start_fixture_dispatcher(layout, wait_ready=False, bootstrap=True)
        time.sleep(0.2)
        assert child.poll() is None and not ready.exists()
        release_merge.set()
        thread.join(15)
        assert not thread.is_alive() and failures == []
        assert results[0]["final_head"] == new_head
        deadline = time.monotonic() + 10
        while not ready.exists() and time.monotonic() < deadline:
            assert child.poll() is None
            time.sleep(0.02)
        assert ready.exists()
        release.touch()
        child.wait(timeout=5)
        assert child.returncode == 0 and output.read_bytes() == b"new-after-race\n"
    finally:
        release_merge.set()
        thread.join(15)
        assert not thread.is_alive()


def test_missing_generation_blocks_and_is_not_rematerialized(cutover_env):
    layout = cutover_env
    child, _, _release, _output = start_fixture_dispatcher(layout)
    with coordinate(layout["active"]) as store:
        record = materialize(layout["active"], store)
    target = Path(record["generation_root"])
    retained = target.with_name("retained-missing-root")
    target.rename(retained)
    publish_remote_change(layout)
    with pytest.raises(GUARDED.GuardError, match="ACTIVE_DISPATCHER"):
        GUARDED._update_active_checkout(layout["active"], layout["evidence"], layout["request"],
                                        process_reader=make_process_reader({child.pid}))
    assert not target.exists() and retained.is_dir() and child.poll() is None


def test_updater_reports_manual_movement_since_previous_cutover(cutover_env):
    layout = cutover_env
    publish_remote_change(layout)
    GUARDED._update_active_checkout(layout["active"], layout["evidence"], layout["request"],
                                    process_reader=make_process_reader(set()))
    manual = publish_remote_change(layout, helper_bytes=b"manual-movement\n")
    git(layout["active"], "pull", "--ff-only")
    report = GUARDED._update_active_checkout(layout["active"], layout["evidence"].with_name("second"),
              layout["request"], process_reader=make_process_reader(set()))
    assert report["unsupervised_movement"] is True
    assert report["active_generation_before"]["commit"] == manual


def test_ambient_pythonpath_cannot_redirect_late_imports(cutover_env, monkeypatch):
    layout = cutover_env
    with coordinate(layout["active"]) as store:
        old = materialize(layout["active"], store)
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join([
        str(layout["active"] / "libexec"), str(Path(old["generation_root"]) / "libexec")]))
    child, _, release, output = start_fixture_dispatcher(layout)
    publish_remote_change(layout)
    GUARDED._update_active_checkout(layout["active"], layout["evidence"], layout["request"],
                                    process_reader=make_process_reader({child.pid}))
    release.touch()
    child.wait(timeout=5)
    assert child.returncode == 0 and output.read_bytes() == b"generation-v1-bytes\n"


def test_retire_exited_lease_releases_old_generation(cutover_env):
    from controller_generation import read_record
    from controller_generation_admin import retire_lease
    layout = cutover_env
    child, _, release, _ = start_fixture_dispatcher(layout)
    release.touch()
    child.wait(timeout=5)
    with coordinate(layout["active"]) as store:
        lease = store / "leases" / f"{child.pid}.json"
        record = read_record(lease)
    assert record["status"] == "exited"
    records = retained_history(layout)
    assert records[0]["commit"] not in inspect(layout["active"], gc=True)["gc"]["eligible"]
    preview = retire_lease(layout["active"], child.pid, record["process_identity"])
    assert preview["status"] == "eligible" and lease.exists()
    with pytest.raises(RuntimeError, match="child cleanup"):
        retire_lease(layout["active"], child.pid, record["process_identity"], apply=True)
    retired = retire_lease(layout["active"], child.pid, record["process_identity"],
                           apply=True, confirm_child_cleanup=True)
    assert retired["status"] == "retired" and not lease.exists()
    assert records[0]["commit"] in inspect(layout["active"], gc=True, apply=True)["gc"]["deleted"]


def test_retire_recycled_identity_without_signalling_current_process(cutover_env):
    import sys
    from controller_generation import read_record, write_record
    from controller_generation_admin import retire_lease
    from controller_generation_process import process_identity
    layout = cutover_env
    child, _, release, output = start_fixture_dispatcher(layout)
    observed = process_identity(child.pid)
    parts = observed.split(":")
    # Model an older incarnation of this real living PID. This is an injected
    # reuse record, not a claim that the OS actually recycled a PID in this test.
    parts[1 if sys.platform == "darwin" else 2] = str(int(parts[1 if sys.platform == "darwin" else 2]) - 1)
    previous = ":".join(parts)
    with coordinate(layout["active"]) as store:
        path = store / "leases" / f"{child.pid}.json"
        record = read_record(path)
        record["process_identity"] = previous
        write_record(path, record)
    with pytest.raises(RuntimeError, match="ambiguous leases"):
        inspect(layout["active"], gc=True, apply=True)
    with pytest.raises(RuntimeError, match="identity"):
        retire_lease(layout["active"], child.pid, "wrong", apply=True, confirm_child_cleanup=True)
    result = retire_lease(layout["active"], child.pid, previous,
                          apply=True, confirm_child_cleanup=True)
    assert result["reason"] == "replaced_process" and child.poll() is None
    assert inspect(layout["active"])["leases"]["blockers"] == []
    # Retirement never grants safety to the current process: without its lease
    # the ordinary process scan continues to block an update.
    with pytest.raises(GUARDED.GuardError, match="ACTIVE_DISPATCHER"):
        GUARDED._update_active_checkout(layout["active"], layout["evidence"], layout["request"],
                                        process_reader=make_process_reader({child.pid}))
    release.touch()
    child.wait(timeout=5)
    assert child.returncode == 0 and output.read_bytes() == b"generation-v1-bytes\n"


def test_retire_refuses_live_identity(cutover_env):
    from controller_generation import read_record
    from controller_generation_admin import retire_lease
    layout = cutover_env
    child, _, _, _ = start_fixture_dispatcher(layout)
    with coordinate(layout["active"]) as store:
        record = read_record(store / "leases" / f"{child.pid}.json")
    with pytest.raises(RuntimeError, match="still alive"):
        retire_lease(layout["active"], child.pid, record["process_identity"],
                     apply=True, confirm_child_cleanup=True)
    assert child.poll() is None


def test_startup_survives_cutover_longer_than_old_ten_second_limit(cutover_env):
    layout = cutover_env
    with coordinate(layout["active"]):
        child, ready, release, output = start_fixture_dispatcher(layout, wait_ready=False, bootstrap=True)
        time.sleep(10.5)
        assert child.poll() is None and not ready.exists()
    deadline = time.monotonic() + 10
    while not ready.exists() and time.monotonic() < deadline:
        assert child.poll() is None
        time.sleep(0.02)
    assert ready.exists()
    release.touch()
    child.wait(timeout=5)
    assert child.returncode == 0 and output.read_bytes() == b"generation-v1-bytes\n"


def test_updater_status_gc_and_retirement_never_invoke_provider(cutover_env, monkeypatch):
    import subprocess
    from controller_generation_admin import retire_lease
    from controller_generation import read_record
    layout = cutover_env
    sentinels = layout["scratch_dir"] / "provider-sentinels"
    sentinels.mkdir()
    marker = sentinels / "invoked"
    monkeypatch.setenv("PROVIDER_SENTINEL_MARKER", str(marker))
    for name in ("codex", "claude", "agy", "gemini"):
        command = sentinels / name
        command.write_text('#!/bin/sh\nprintf invoked >> "$PROVIDER_SENTINEL_MARKER"\nexit 97\n')
        command.chmod(0o700)
    monkeypatch.setenv("PATH", str(sentinels) + os.pathsep + os.environ["PATH"])
    assert subprocess.run(["claude"], capture_output=True).returncode == 97
    assert marker.read_text() == "invoked"
    marker.unlink()
    child, _, release, _ = start_fixture_dispatcher(layout)
    with coordinate(layout["active"]) as store:
        record = read_record(store / "leases" / f"{child.pid}.json")
    publish_remote_change(layout)
    GUARDED._update_active_checkout(layout["active"], layout["evidence"], layout["request"],
                                    process_reader=make_process_reader({child.pid}))
    inspect(layout["active"])
    inspect(layout["active"], gc=True, apply=True)
    release.touch()
    child.wait(timeout=5)
    retire_lease(layout["active"], child.pid, record["process_identity"],
                 apply=True, confirm_child_cleanup=True)
    assert not marker.exists()


def test_retirement_unblocks_same_pid_startup_without_trusting_stale_record(cutover_env):
    import sys
    from controller_generation import create_lease, read_record, write_record, LeaseRetirementRequired
    from controller_generation_admin import retire_lease
    from controller_generation_process import process_identity
    layout = cutover_env
    current = process_identity(os.getpid())
    parts = current.split(":")
    index = 1 if sys.platform == "darwin" else 2
    parts[index] = str(int(parts[index]) - 1)
    previous = ":".join(parts)
    with coordinate(layout["active"]) as store:
        generation = materialize(layout["active"], store)
        path = create_lease(store, generation)
        record = read_record(path)
        record.update(process_identity=previous, status="exited")
        write_record(path, record)
        with pytest.raises(LeaseRetirementRequired):
            create_lease(store, generation)
    retire_lease(layout["active"], os.getpid(), previous, apply=True, confirm_child_cleanup=True)
    with coordinate(layout["active"]) as store:
        fresh = read_record(create_lease(store, generation))
    assert fresh["status"] == "starting" and fresh["process_identity"] == current
