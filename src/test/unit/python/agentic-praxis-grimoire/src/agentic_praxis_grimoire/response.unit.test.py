"""Unit contracts for APGR numbered response capture."""

from __future__ import annotations

from io import BytesIO, StringIO
import os
from pathlib import Path
import stat
import sys
import time

import pytest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from agentic_praxis_grimoire import response  # noqa: E402


def _phase_root(tmp_path: Path) -> Path:
    return tmp_path / "outbox"


def test_stdin_body_is_written_byte_for_byte_with_private_modes(
    tmp_path: Path,
) -> None:
    body = b"# exact\n\x00\xff\n"

    created = response.capture_response(
        outbox_root=_phase_root(tmp_path),
        project="project",
        phase="APG82",
        stdin=BytesIO(body),
    )

    assert created == _phase_root(tmp_path) / "project" / "APG82" / "APG82.001.response.md"
    assert created.read_bytes() == body
    assert stat.S_IMODE(created.stat().st_mode) == 0o600
    assert stat.S_IMODE(created.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(created.parent.parent.stat().st_mode) == 0o700
    assert response.list_reservation_artifacts(created.parent) == ()
    assert stat.S_IMODE((created.parent / response.LOCK_NAME).stat().st_mode) == 0o600


def test_file_input_and_monotonic_numbering_never_overwrite(
    tmp_path: Path,
) -> None:
    outbox = _phase_root(tmp_path)
    source = tmp_path / "response.md"
    first_body = b"first\n"
    source.write_bytes(first_body)

    first = response.capture_response(
        outbox_root=outbox,
        project="project",
        phase="APG82",
        source=source,
    )
    second = response.record_response(
        outbox_root=outbox,
        project="project",
        phase="APG82",
        body=b"second\n",
    )

    assert first.name == "APG82.001.response.md"
    assert second.name == "APG82.002.response.md"
    assert first.read_bytes() == first_body
    assert second.read_bytes() == b"second\n"


def test_fifo_input_is_rejected_without_waiting_for_a_writer(tmp_path: Path) -> None:
    fifo = tmp_path / "response.fifo"
    os.mkfifo(fifo)

    started = time.monotonic()
    with pytest.raises(response.ResponseInputError, match="regular file"):
        response._read_source(fifo)

    assert time.monotonic() - started < 1.0


@pytest.mark.parametrize(
    "value",
    ["", ".", "..", "bad/name", "bad\\name", "bad\nname", "bad\tname", "x" * 129],
)
def test_project_and_phase_components_reject_ambiguous_path_values(
    tmp_path: Path, value: str
) -> None:
    with pytest.raises(response.ResponseUsageError, match="unsafe"):
        response.phase_directory(_phase_root(tmp_path), value, "APG82")
    with pytest.raises(response.ResponseUsageError, match="unsafe"):
        response.phase_directory(_phase_root(tmp_path), "project", value)


def test_response_requires_one_byte_preserving_input(tmp_path: Path) -> None:
    outbox = _phase_root(tmp_path)
    with pytest.raises(response.ResponseUsageError, match="exactly one"):
        response.capture_response(
            outbox_root=outbox,
            project="project",
            phase="APG82",
        )
    with pytest.raises(response.ResponseUsageError, match="exactly one"):
        response.capture_response(
            outbox_root=outbox,
            project="project",
            phase="APG82",
            body=b"body",
            stdin=BytesIO(b"stdin"),
        )
    with pytest.raises(response.ResponseInputError, match="bytes"):
        response.capture_response(
            outbox_root=outbox,
            project="project",
            phase="APG82",
            stdin=StringIO("text"),
        )


def test_existing_symlink_is_never_replaced(tmp_path: Path) -> None:
    outbox = _phase_root(tmp_path)
    phase_dir = response.phase_directory(outbox, "project", "APG82")
    target = tmp_path / "target"
    target.write_bytes(b"target\n")
    first = phase_dir / "APG82.001.response.md"
    first.symlink_to(target)

    created = response.capture_response(
        outbox_root=outbox,
        project="project",
        phase="APG82",
        body=b"new\n",
    )

    assert created.name == "APG82.002.response.md"
    assert first.is_symlink()
    assert target.read_bytes() == b"target\n"


def test_failed_atomic_publication_cleans_temp_reservation_and_lock(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    outbox = _phase_root(tmp_path)
    phase_dir = response.phase_directory(outbox, "project", "APG82")

    def fail_link(*_arguments: object, **_kwargs: object) -> None:
        raise OSError("injected publication failure")

    monkeypatch.setattr(response.os, "link", fail_link)
    with pytest.raises(response.ResponseError, match="publication"):
        response.capture_response(
            outbox_root=outbox,
            project="project",
            phase="APG82",
            body=b"must not claim completion\n",
        )

    assert not tuple(phase_dir.glob("APG82.*.response.md"))
    assert response.list_reservation_artifacts(phase_dir) == ()
    assert stat.S_IMODE((phase_dir / response.LOCK_NAME).stat().st_mode) == 0o600
    assert not tuple(phase_dir.glob(response.TEMP_GLOB))


def test_failed_publication_durability_leaves_no_false_completed_claim(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    phase_dir = response.phase_directory(tmp_path, "project", "APG82")
    original_fsync = response._fsync_directory
    calls = 0

    def fail_first_fsync(path: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("injected durability failure")
        original_fsync(path)

    monkeypatch.setattr(response, "_fsync_directory", fail_first_fsync)
    with pytest.raises(response.ResponseError, match="write failed"):
        response.capture_response(
            outbox_root=tmp_path,
            project="project",
            phase="APG82",
            body=b"not durable",
        )
    assert not tuple(phase_dir.glob("APG82.*.response.md"))
    assert response.list_reservation_artifacts(phase_dir) == ()


def test_reservation_directory_sync_failure_removes_owned_reservation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    phase_dir = response.phase_directory(tmp_path, "project", "APG82")

    def fail_directory_sync(_path: Path) -> None:
        raise OSError("injected reservation durability failure")

    monkeypatch.setattr(response, "_fsync_directory", fail_directory_sync)
    with pytest.raises(response.ResponseError, match="reservation"):
        response._reserve(phase_dir, "APG82")

    assert response.list_reservation_artifacts(phase_dir) == ()


def test_post_link_durability_failure_preserves_exact_published_response(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    phase_dir = response.phase_directory(tmp_path, "project", "APG82")
    original_link = response.os.link
    original_fsync = response._fsync_directory
    published = False

    def observe_link(*arguments: object, **kwargs: object) -> None:
        nonlocal published
        original_link(*arguments, **kwargs)
        published = True

    def fail_after_link(path: Path) -> None:
        if published:
            raise OSError("injected post-link durability failure")
        original_fsync(path)

    monkeypatch.setattr(response.os, "link", observe_link)
    monkeypatch.setattr(response, "_fsync_directory", fail_after_link)
    with pytest.raises(response.ResponseError, match="cleanup was incomplete"):
        response.capture_response(
            outbox_root=tmp_path,
            project="project",
            phase="APG82",
            body=b"published exactly\n",
        )

    completed = phase_dir / "APG82.001.response.md"
    assert completed.read_bytes() == b"published exactly\n"
    assert stat.S_IMODE(completed.stat().st_mode) == 0o600


def test_destination_appearing_at_publication_is_never_overwritten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_link = response.os.link

    def racing_link(source: Path, destination: Path, **kwargs: object) -> None:
        destination.write_bytes(b"pre-existing")
        original_link(source, destination, **kwargs)

    monkeypatch.setattr(response.os, "link", racing_link)
    with pytest.raises(response.ResponseError, match="publication"):
        response.capture_response(
            outbox_root=tmp_path,
            project="project",
            phase="APG82",
            body=b"new-body",
        )
    assert (
        tmp_path / "project" / "APG82" / "APG82.001.response.md"
    ).read_bytes() == b"pre-existing"


def test_stale_unlocked_lock_file_is_recovered(tmp_path: Path) -> None:
    phase_dir = response.phase_directory(tmp_path, "project", "APG82")
    lock = phase_dir / response.LOCK_NAME
    lock.write_bytes(b"response-lock-v2\n")
    lock.chmod(0o600)
    created = response.capture_response(
        outbox_root=tmp_path,
        project="project",
        phase="APG82",
        body=b"body",
    )
    assert created.read_bytes() == b"body"
    assert stat.S_IMODE(lock.stat().st_mode) == 0o600


def test_capture_rejects_relative_outbox_root(tmp_path: Path) -> None:
    del tmp_path
    with pytest.raises(response.ResponseUsageError, match="absolute"):
        response.capture_response(
            outbox_root="relative-outbox",
            project="project",
            phase="APG82",
            body=b"body",
        )


def test_next_capture_cleans_owner_only_orphan_temporary(tmp_path: Path) -> None:
    phase_dir = response.phase_directory(tmp_path, "project", "APG82")
    orphan = phase_dir / ".response-write.dead-process.tmp"
    orphan.write_bytes(b"sensitive partial body")
    orphan.chmod(0o600)

    created = response.capture_response(
        outbox_root=tmp_path,
        project="project",
        phase="APG82",
        body=b"complete",
    )

    assert created.read_bytes() == b"complete"
    assert not orphan.exists()


def test_cli_invalid_tilde_input_is_bounded(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    result = response.main(
        {"project": "project", "outbox_root": str(tmp_path)},
        ["record", "--phase", "APG82", "--input", "~doesnotexist/body"],
        None,
    )
    assert result == 2
    assert "input path is invalid" in capsys.readouterr().err


def test_response_write_rejects_repository_project_mismatch(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repository = tmp_path / "canonical-project"
    repository.mkdir()
    result = response.main(
        {"project": "other-project", "outbox_root": str(tmp_path / "outbox")},
        ["record", "--phase", "APG82"],
        repository,
    )
    assert result == 2
    assert "must match the repository basename" in capsys.readouterr().err


def test_reservation_artifacts_are_listable_and_exactly_cleanable(
    tmp_path: Path,
) -> None:
    phase_dir = response.phase_directory(_phase_root(tmp_path), "project", "APG82")
    reservation = phase_dir / ".APG82.007.response.md.reservation.test-token"
    reservation.write_bytes(b"reservation-v1\n")
    reservation.chmod(0o600)

    assert response.list_reservation_artifacts(phase_dir) == (reservation,)
    response.clean_reservation_artifact(
        reservation, outbox_root=_phase_root(tmp_path), project="project", phase="APG82"
    )
    assert not reservation.exists()
    assert response.list_reservation_artifacts(phase_dir) == ()


def test_existing_reservation_blocks_its_number_until_exact_cleanup(
    tmp_path: Path,
) -> None:
    outbox = _phase_root(tmp_path)
    phase_dir = response.phase_directory(outbox, "project", "APG82")
    reservation = phase_dir / ".APG82.001.response.md.reservation.foreign"
    reservation.write_bytes(b"reservation-v1\n")
    reservation.chmod(0o600)

    created = response.capture_response(
        outbox_root=outbox,
        project="project",
        phase="APG82",
        body=b"second-number\n",
    )

    assert created.name == "APG82.002.response.md"
    assert reservation.exists()
    response.clean_reservation_artifact(
        reservation, outbox_root=outbox, project="project", phase="APG82"
    )


def test_clean_reservation_artifact_rejects_unrelated_or_symlinked_paths(
    tmp_path: Path,
) -> None:
    phase_dir = response.phase_directory(_phase_root(tmp_path), "project", "APG82")
    unrelated = phase_dir / "not-a-reservation"
    unrelated.write_bytes(b"keep\n")
    with pytest.raises(response.ResponseUsageError, match="reservation"):
        response.clean_reservation_artifact(
            unrelated, outbox_root=_phase_root(tmp_path), project="project", phase="APG82"
        )
    assert unrelated.read_bytes() == b"keep\n"

    target = tmp_path / "target"
    target.write_bytes(b"keep\n")
    symlink = phase_dir / ".APG82.008.response.md.reservation.symlink"
    symlink.symlink_to(target)
    with pytest.raises(response.ResponseError, match="regular"):
        response.clean_reservation_artifact(
            symlink, outbox_root=_phase_root(tmp_path), project="project", phase="APG82"
        )
    assert target.read_bytes() == b"keep\n"


def test_allocator_stops_at_three_digit_limit_without_claiming_a_path(
    tmp_path: Path,
) -> None:
    phase_dir = response.phase_directory(_phase_root(tmp_path), "project", "APG82")
    for number in range(1, 1000):
        (phase_dir / f"APG82.{number:03d}.response.md").write_bytes(b"occupied")

    with pytest.raises(response.ResponseAllocationError, match="001..999"):
        response.capture_response(
            outbox_root=_phase_root(tmp_path),
            project="project",
            phase="APG82",
            body=b"no number\n",
        )

    assert response.list_reservation_artifacts(phase_dir) == ()
    assert stat.S_IMODE((phase_dir / response.LOCK_NAME).stat().st_mode) == 0o600


def test_exact_input_selector_rejects_alias_conflicts_and_non_bytes(tmp_path: Path) -> None:
    source = tmp_path / "body.md"
    source.write_bytes(b"body")
    with pytest.raises(response.ResponseUsageError, match="exactly one"):
        response._read_input(
            body=None, source=source, input_path=source, stdin=None
        )
    with pytest.raises(response.ResponseInputError, match="body must be bytes"):
        response._read_input(
            body="text", source=None, input_path=None, stdin=None  # type: ignore[arg-type]
        )

    class BrokenInput:
        def read(self) -> bytes:
            raise OSError("injected")

    with pytest.raises(response.ResponseInputError, match="response stdin"):
        response._read_input(
            body=None, source=None, input_path=None, stdin=BrokenInput()  # type: ignore[arg-type]
        )

    class SegmentedInput:
        def __init__(self) -> None:
            self.parts = iter((b"first", b"-second", b""))

        def read(self, _size: int) -> bytes:
            return next(self.parts)

    assert response._read_input(
        body=None, source=None, input_path=None, stdin=SegmentedInput()  # type: ignore[arg-type]
    ) == b"first-second"


def test_response_cli_rejects_duplicate_stdin_and_file_selectors(tmp_path: Path) -> None:
    source = tmp_path / "body.md"
    source.write_bytes(b"body")
    with pytest.raises(response.ResponseUsageError, match="requires one value"):
        response._parse_main_arguments(("--input", "-", "--input", str(source)))
    with pytest.raises(response.ResponseUsageError, match="requires one value"):
        response._parse_main_arguments(("--file", str(source), "--input", "-"))


def test_response_directory_rejects_foreign_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outbox = _phase_root(tmp_path)
    response.phase_directory(outbox, "project", "APG82")
    actual_uid = os.getuid()
    monkeypatch.setattr(response.os, "getuid", lambda: actual_uid + 1)
    with pytest.raises(response.ResponseError, match="owner"):
        response.phase_directory(outbox, "project", "APG82")


def test_input_file_must_exist_and_be_regular(tmp_path: Path) -> None:
    with pytest.raises(response.ResponseInputError, match="could not read"):
        response._read_source(tmp_path / "missing")
    with pytest.raises(response.ResponseInputError, match="regular file"):
        response._read_source(tmp_path)


def test_response_inputs_are_bounded_before_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(response, "MAX_RESPONSE_BYTES", 3)
    source = tmp_path / "body.md"
    source.write_bytes(b"four")
    with pytest.raises(response.ResponseInputError, match="8 MiB"):
        response._read_source(source)
    with pytest.raises(response.ResponseInputError, match="8 MiB"):
        response._read_input(
            body=b"four", source=None, input_path=None, stdin=None
        )
    with pytest.raises(response.ResponseInputError, match="8 MiB"):
        response._read_input(
            body=None, source=None, input_path=None, stdin=BytesIO(b"four")
        )


def test_response_directories_and_listing_reject_unsafe_entries(tmp_path: Path) -> None:
    assert response.list_reservation_artifacts(tmp_path / "missing") == ()
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "linked"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(response.ResponseError, match="directory is unsafe"):
        response.phase_directory(link, "project", "APG82")
    with pytest.raises(response.ResponseError, match="phase directory is unsafe"):
        response.list_reservation_artifacts(link)


def test_reservation_cleanup_requires_matching_phase_and_allows_absence(
    tmp_path: Path,
) -> None:
    wrong_parent = tmp_path / "other" / ".APG82.001.response.md.reservation.token"
    with pytest.raises(response.ResponseUsageError, match="belong"):
        response.clean_reservation_artifact(
            wrong_parent, outbox_root=tmp_path, project="project", phase="APG82"
        )
    absent = tmp_path / "project" / "APG82" / ".APG82.001.response.md.reservation.token"
    response.clean_reservation_artifact(
        absent, outbox_root=tmp_path, project="project", phase="APG82"
    )

    unrelated = tmp_path / "unrelated" / "APG82"
    unrelated.mkdir(parents=True)
    shaped = unrelated / ".APG82.001.response.md.reservation.token"
    shaped.write_bytes(b"keep")
    shaped.chmod(0o600)
    with pytest.raises(response.ResponseUsageError, match="belong"):
        response.clean_reservation_artifact(
            shaped, outbox_root=tmp_path, project="project", phase="APG82"
        )
    assert shaped.read_bytes() == b"keep"

    outside_phase = tmp_path / "outside" / "APG82"
    outside_phase.mkdir(parents=True)
    redirected = outside_phase / ".APG82.002.response.md.reservation.token"
    redirected.write_bytes(b"keep")
    redirected.chmod(0o600)
    outbox = tmp_path / "symlink-outbox"
    outbox.mkdir()
    (outbox / "project").symlink_to(outside_phase.parent, target_is_directory=True)
    lexical = outbox / "project" / "APG82" / redirected.name
    with pytest.raises(response.ResponseError, match="ancestry"):
        response.clean_reservation_artifact(
            lexical, outbox_root=outbox, project="project", phase="APG82"
        )
    assert redirected.read_bytes() == b"keep"


@pytest.mark.parametrize(
    "arguments,message",
    [
        (["--phase"], "requires one value"),
        (["--phase", "APG82", "--phase", "APG82"], "requires one value"),
        (["--input"], "requires one value"),
        (["--unknown"], "unknown response option"),
        (["APG82", "APG83"], "specified more than once"),
    ],
)
def test_response_cli_argument_errors_are_bounded(
    arguments: list[str], message: str
) -> None:
    with pytest.raises(response.ResponseUsageError, match=message):
        response._parse_main_arguments(arguments)


def test_response_cli_help_and_required_context(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert response.main({}, ["--help"]) == 0
    assert "usage: apgr response" in capsys.readouterr().out
    assert response.main({}, ["record", "--phase", "APG82"]) == 2
    assert "--project is required" in capsys.readouterr().err


def test_response_cli_file_input_prints_created_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "body.md"
    source.write_bytes(b"exact")
    assert response.main(
        {"project": "project", "outbox_root": str(tmp_path / "outbox")},
        ["capture", "APG82", "--file", str(source)],
    ) == 0
    created = Path(capsys.readouterr().out.strip())
    assert created.read_bytes() == b"exact"


def test_existing_lock_with_unsafe_mode_is_rejected(tmp_path: Path) -> None:
    phase_dir = response.phase_directory(tmp_path, "project", "APG82")
    lock = phase_dir / response.LOCK_NAME
    lock.write_bytes(b"unsafe")
    lock.chmod(0o644)
    with pytest.raises(response.ResponseError, match="lock is unsafe"):
        response.capture_response(
            outbox_root=tmp_path,
            project="project",
            phase="APG82",
            body=b"body",
        )
