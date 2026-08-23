from __future__ import annotations

from io import BytesIO, StringIO
from pathlib import Path
import stat
import sys

import pytest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from agentic_praxis_grimoire import go_bridge, response  # noqa: E402


def _captured(path: Path, *, returncode: int = 0, stderr: bytes = b"") -> go_bridge.CapturedResult:
    return go_bridge.CapturedResult(returncode, f"{path}\n".encode(), stderr)


def test_body_capture_delegates_exact_argv_and_bytes_without_python_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outbox = tmp_path / "outbox"
    created = outbox / "project" / "APG100" / "APG100.001.response.md"
    observed: list[tuple[list[str], dict[str, object]]] = []

    def fake_capture(arguments, *, repository_root, input_bytes, environment=None):
        observed.append((list(arguments), {
            "repository_root": repository_root,
            "input_bytes": input_bytes,
            "environment": environment,
        }))
        return _captured(created)

    monkeypatch.setattr(response.go_bridge, "run_capture", fake_capture)
    result = response.capture_response(
        outbox_root=outbox,
        project="project",
        phase="APG100",
        body=b"exact\x00\xff\n",
        repository_root=tmp_path,
    )
    assert result == created
    assert observed == [
        ([
            "--repository", str(tmp_path),
            "--outbox-root", str(outbox),
            "--project", "project",
            "response", "capture", "--phase", "APG100",
        ], {
            "repository_root": tmp_path,
            "input_bytes": b"exact\x00\xff\n",
            "environment": None,
        })
    ]


def test_file_capture_passes_source_path_to_go_without_reading_or_replacing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "response.md"
    source.write_bytes(b"source bytes")
    created = tmp_path / "outbox" / "project" / "APG100" / "APG100.001.response.md"
    observed: list[tuple[list[str], bytes | None]] = []
    monkeypatch.setattr(
        response.go_bridge,
        "run_capture",
        lambda arguments, *, repository_root, input_bytes, environment=None: (
            observed.append((list(arguments), input_bytes)) or _captured(created)
        ),
    )
    assert response.record_response(
        outbox_root=tmp_path / "outbox",
        project="project",
        phase="APG100",
        input_path=source,
    ) == created
    assert observed == [
        ([
            "--outbox-root", str(tmp_path / "outbox"),
            "--project", "project",
            "response", "capture", "--phase", "APG100",
            "--input", str(source),
        ], None)
    ]
    assert source.read_bytes() == b"source bytes"


def test_stdin_body_is_read_once_and_sent_byte_for_byte(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    created = tmp_path / "outbox" / "project" / "APG100" / "APG100.001.response.md"
    observed: list[bytes | None] = []
    monkeypatch.setattr(
        response.go_bridge,
        "run_capture",
        lambda _arguments, *, repository_root, input_bytes, environment=None: (
            observed.append(input_bytes) or _captured(created)
        ),
    )
    assert response.capture_response(
        outbox_root=tmp_path / "outbox",
        project="project",
        phase="APG100",
        stdin=BytesIO(b"stdin\x00\xff"),
    ) == created
    assert observed == [b"stdin\x00\xff"]


def test_input_selection_and_size_errors_happen_before_bridge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        response.go_bridge,
        "run_capture",
        lambda *_args, **_kwargs: pytest.fail("invalid input reached Go"),
    )
    with pytest.raises(response.ResponseUsageError, match="exactly one"):
        response.capture_response(
            outbox_root=tmp_path,
            project="project",
            phase="APG100",
        )
    with pytest.raises(response.ResponseUsageError, match="exactly one"):
        response.capture_response(
            outbox_root=tmp_path,
            project="project",
            phase="APG100",
            body=b"body",
            stdin=BytesIO(b"stdin"),
        )
    with pytest.raises(response.ResponseInputError, match="bytes"):
        response.capture_response(
            outbox_root=tmp_path,
            project="project",
            phase="APG100",
            stdin=StringIO("text"),
        )
    with pytest.raises(response.ResponseInputError, match="8 MiB"):
        response.capture_response(
            outbox_root=tmp_path,
            project="project",
            phase="APG100",
            body=b"x" * (response.MAX_RESPONSE_BYTES + 1),
        )


@pytest.mark.parametrize("value", ["", ".", "..", "bad/name", "bad\\name", "x" * 129])
def test_project_and_phase_validation_is_preserved(
    tmp_path: Path, value: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        response.go_bridge,
        "run_capture",
        lambda *_args, **_kwargs: pytest.fail("unsafe identity reached Go"),
    )
    with pytest.raises(response.ResponseUsageError, match="safe path|identifier|separator"):
        response.capture_response(
            outbox_root=tmp_path,
            project=value,
            phase="APG100",
            body=b"body",
        )
    with pytest.raises(response.ResponseUsageError, match="safe path|identifier|separator"):
        response.capture_response(
            outbox_root=tmp_path,
            project="project",
            phase=value,
            body=b"body",
        )


def test_go_failure_preserves_bounded_failure_classes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    created = tmp_path / "outbox" / "project" / "APG100" / "APG100.001.response.md"
    monkeypatch.setattr(
        response.go_bridge,
        "run_capture",
        lambda *_args, **_kwargs: _captured(
            created, returncode=1, stderr=b"apgr: response: response numbers exhausted (001..999)\n"
        ),
    )
    with pytest.raises(response.ResponseAllocationError, match="exhausted"):
        response.capture_response(
            outbox_root=tmp_path / "outbox",
            project="project",
            phase="APG100",
            body=b"body",
        )


def test_go_filesystem_safety_failure_is_not_mislabeled_as_usage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    created = tmp_path / "outbox" / "project" / "APG100" / "APG100.001.response.md"
    monkeypatch.setattr(
        response.go_bridge,
        "run_capture",
        lambda *_args, **_kwargs: _captured(
            created, returncode=1, stderr=b"apgr: response: response phase directory is unsafe\n"
        ),
    )
    with pytest.raises(response.ResponseError, match="directory is unsafe") as failure:
        response.capture_response(
            outbox_root=tmp_path / "outbox",
            project="project",
            phase="APG100",
            body=b"body",
        )
    assert type(failure.value) is response.ResponseError


def test_response_main_preserves_aliases_and_prints_created_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    created = tmp_path / "outbox" / "project" / "APG100" / "APG100.001.response.md"
    observed: list[dict[str, object]] = []

    def fake_capture(**kwargs: object) -> Path:
        observed.append(kwargs)
        return created

    monkeypatch.setattr(response, "capture_response", fake_capture)
    source = tmp_path / "body.md"
    source.write_bytes(b"body")
    assert response.main(
        {"project": "project", "outbox_root": str(tmp_path / "outbox")},
        ["record", "--phase", "APG100", "--file", str(source)],
    ) == 0
    assert Path(capsys.readouterr().out.strip()) == created
    assert observed == [{
        "outbox_root": tmp_path / "outbox",
        "project": "project",
        "phase": "APG100",
        "source": source,
        "repository_root": None,
    }]


def test_phase_helpers_do_not_mutate_and_cleanup_refuses_python_deletion(
    tmp_path: Path,
) -> None:
    phase = response.phase_directory(tmp_path / "outbox", "project", "APG100")
    assert phase == tmp_path / "outbox" / "project" / "APG100"
    assert not phase.exists()
    assert response.list_reservation_artifacts(phase) == ()
    with pytest.raises(response.ResponseError, match="owned by the Go runtime"):
        response.clean_reservation_artifact(
            phase / ".APG100.001.response.md.reservation.token",
            outbox_root=tmp_path / "outbox",
            project="project",
            phase="APG100",
        )


def test_response_main_usage_and_help_remain_bounded(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert response.main({}, ["--help"]) == 0
    assert "usage: apgr response" in capsys.readouterr().out
    assert response.main({}, ["record", "--phase", "APG100"]) == 2
    assert "--project is required" in capsys.readouterr().err


def test_response_constants_match_go_authority() -> None:
    assert response.MAX_COMPONENT_LENGTH == 128
    assert response.MAX_RESPONSE_NUMBER == 999
    assert response.MAX_RESPONSE_BYTES == 8 * 1024 * 1024
    assert response.MAX_RESPONSE_BYTES == 8388608
    # Verify against Go source definitions in internal/response/response.go
    go_source = (REPOSITORY_ROOT / "internal/response/response.go").read_text(encoding="utf-8")
    assert "MaxComponentLength = 128" in go_source
    assert "MaxResponseNumber  = 999" in go_source
    assert "MaxResponseBytes   = 8 << 20" in go_source


def test_compatibility_readers_cover_regular_chunked_and_refusal_paths(
    tmp_path: Path,
) -> None:
    source = tmp_path / "input"
    source.write_bytes(b"exact bytes")
    assert response._read_source(source) == b"exact bytes"
    assert response._read_input(body=b"body", source=None, input_path=None, stdin=None) == b"body"
    assert response._read_input(body=None, source=source, input_path=None, stdin=None) == b"exact bytes"
    assert response._read_input(body=None, source=None, input_path=None, stdin=BytesIO(b"stdin")) == b"stdin"

    with pytest.raises(response.ResponseInputError, match="regular file"):
        response._read_source(tmp_path)
    with pytest.raises(response.ResponseInputError, match="could not read"):
        response._read_source(tmp_path / "missing")
    link = tmp_path / "link"
    link.symlink_to(source)
    with pytest.raises(response.ResponseInputError, match="could not read"):
        response._read_source(link)
    oversized = tmp_path / "oversized"
    oversized.write_bytes(b"")
    with oversized.open("r+b") as stream:
        stream.truncate(response.MAX_RESPONSE_BYTES + 1)
    with pytest.raises(response.ResponseInputError, match="8 MiB"):
        response._read_source(oversized)

    with pytest.raises(response.ResponseUsageError, match="exactly one"):
        response._read_input(body=None, source=source, input_path=source, stdin=None)
    with pytest.raises(response.ResponseInputError, match="bytes"):
        response._read_input(body="text", source=None, input_path=None, stdin=None)  # type: ignore[arg-type]


def test_reservation_listing_validates_directory_and_entries(tmp_path: Path) -> None:
    phase = tmp_path / "APG102"
    phase.mkdir()
    valid = phase / ".APG102.001.response.md.reservation.token"
    valid.write_bytes(b"")
    (phase / "ignored").write_bytes(b"")
    (phase / ".OTHER.002.response.md.reservation.token").write_bytes(b"")
    assert response.list_reservation_artifacts(phase) == (valid,)

    unsafe = phase / ".APG102.002.response.md.reservation.token"
    unsafe.symlink_to(valid)
    with pytest.raises(response.ResponseError, match="artifact is unsafe"):
        response.list_reservation_artifacts(phase)
    with pytest.raises(response.ResponseError, match="directory is unsafe"):
        response.list_reservation_artifacts(valid)


@pytest.mark.parametrize(
    ("returncode", "detail", "error_type"),
    [
        (130, b"stopped", response.ResponseError),
        (1, b"input is not a regular file", response.ResponseInputError),
        (1, b"invalid option", response.ResponseUsageError),
        (1, b"--project must match", response.ResponseUsageError),
        (1, b"lock contention", response.ResponseAllocationError),
        (1, b"", response.ResponseError),
    ],
)
def test_bridge_failure_classification_is_complete(
    returncode: int, detail: bytes, error_type: type[response.ResponseError]
) -> None:
    result = go_bridge.CapturedResult(returncode, b"", detail)
    assert type(response._bridge_failure(result)) is error_type


@pytest.mark.parametrize(
    "arguments",
    [
        ["--phase"],
        ["--phase", "APG102", "--phase", "OTHER"],
        ["--input"],
        ["--input", "a", "--file", "b"],
        ["--unknown"],
        ["APG102", "OTHER"],
    ],
)
def test_response_argument_parser_refuses_ambiguous_forms(arguments: list[str]) -> None:
    with pytest.raises(response.ResponseUsageError):
        response._parse_main_arguments(arguments)


@pytest.mark.parametrize("rendered", [b"", b"relative\n", b"/tmp/a\n/tmp/b\n", b"/tmp/../tmp/a\n"])
def test_created_path_requires_one_canonical_absolute_path(rendered: bytes) -> None:
    with pytest.raises(response.ResponseError, match="created path"):
        response._created_path(go_bridge.CapturedResult(0, rendered, b""))


def test_capture_and_main_wrap_bridge_and_repository_identity_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        response.go_bridge,
        "run_capture",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(go_bridge.GoBridgeError("bridge failed")),
    )
    with pytest.raises(response.ResponseError, match="bridge failed"):
        response.capture_response(
            outbox_root=tmp_path,
            project="project",
            phase="APG102",
            body=b"body",
        )
    with pytest.raises(response.ResponseUsageError, match="absolute clean"):
        response.capture_response(
            outbox_root="relative",
            project="project",
            phase="APG102",
            body=b"body",
        )

    repository = tmp_path / "actual-project"
    repository.mkdir()
    assert response.main(
        {"project": "different", "outbox_root": str(tmp_path / "outbox")},
        ["APG102"],
        repository,
    ) == 2
    assert "must match" in capsys.readouterr().err
