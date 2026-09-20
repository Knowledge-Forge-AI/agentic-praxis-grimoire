from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

import pytest

from agent_phase import envelope
from agent_phase import plan_material
from agent_phase.request import PhaseRequest

from test_agent_phase_dispatch import PHASE_ID, FakeRunner, make_dispatcher, repository


__all__ = ["repository"]


def _clone_stat(
    real: os.stat_result,
    *,
    st_uid: int | None = None,
    st_ino: int | None = None,
    st_size: int | None = None,
) -> os.stat_result:
    mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime = tuple(real)[:10]
    if st_uid is not None:
        uid = st_uid
    if st_ino is not None:
        ino = st_ino
    if st_size is not None:
        size = st_size
    extra: dict[str, Any] = {}
    for attr in (
        "st_atime_ns",
        "st_mtime_ns",
        "st_ctime_ns",
        "st_birthtime",
        "st_birthtime_ns",
        "st_blocks",
        "st_blksize",
        "st_rdev",
        "st_flags",
        "st_gen",
        "st_lspare",
        "st_qspare",
    ):
        if hasattr(real, attr):
            extra[attr] = getattr(real, attr)
    return os.stat_result(
        (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime),
        extra,
    )


def _brain_file(
    home: Path,
    content: bytes = b"# Complete plan\n",
    *,
    session: str = "session-1",
    name: str = "plan.md",
) -> Path:
    brain = home / ".gemini" / "antigravity-cli" / "brain" / session
    brain.mkdir(mode=0o700, parents=True)
    for parent in (
        home / ".gemini",
        home / ".gemini" / "antigravity-cli",
        home / ".gemini" / "antigravity-cli" / "brain",
        brain,
    ):
        parent.chmod(0o700)
    artifact = brain / name
    artifact.write_bytes(content)
    artifact.chmod(0o600)
    return artifact


def test_inline_stdout_is_the_exact_canonical_material() -> None:
    raw = b"# Plan\r\nkeep bytes exactly\r\n"

    material = plan_material.materialize(
        raw, provider="codex", profile="implementation-testing"
    )

    assert material.data == raw
    assert material.binding == {
        "schema": plan_material.SCHEMA,
        "relative_path": plan_material.CANONICAL_PATH,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "materialization_kind": "inline_stdout",
        "provider": "codex",
        "profile": "implementation-testing",
    }


def test_antigravity_brain_uri_materializes_only_fixed_private_shape(
    tmp_path: Path,
) -> None:
    source = _brain_file(tmp_path, b"# Complete plan\nwith detail\n")
    stdout = (
        b"Short summary. Full details are in "
        + source.as_uri().encode("ascii")
        + b"\n"
    )

    material = plan_material.materialize(
        stdout,
        provider="antigravity",
        profile="gemini-3.7-flash-medium",
        _home=tmp_path,
    )

    assert material.data == source.read_bytes()
    assert material.binding["materialization_kind"] == "antigravity_brain_file"
    assert str(source) not in repr(material.binding)


def test_tokenizer_captures_trailing_styling_from_bold_markdown_link(
    tmp_path: Path,
) -> None:
    source = _brain_file(tmp_path)
    text = f"👉 **[plan]({source.as_uri()})**\n"
    generic_matches = [
        match.group(0) for match in plan_material._FILE_URI.finditer(text)
    ]
    # Defect characterization: the unadapted broad generic tokenizer captures the trailing `)**`.
    assert generic_matches == [f"{source.as_uri()})**"]


@pytest.mark.parametrize(
    "template",
    [
        "👉 **[plan]({uri})**\n",
        "**[plan]({uri})**",
        "*[plan]({uri})*",
        "_[plan]({uri})_",
        "`[plan]({uri})`",
        "[plan]({uri})",
        "See [plan]({uri}).",
        "See [plan]({uri}), next steps.",
        "([plan]({uri}))",
    ],
)
def test_antigravity_markdown_link_materializes_exact_source_bytes(
    tmp_path: Path, template: str
) -> None:
    source = _brain_file(tmp_path, b"# Complete plan\nstyled markdown link\n")
    stdout = template.format(uri=source.as_uri()).encode("utf-8")

    material = plan_material.materialize(
        stdout,
        provider="antigravity",
        profile="gemini-3.7-flash-medium",
        _home=tmp_path,
    )

    assert material.data == b"# Complete plan\nstyled markdown link\n"
    assert material.binding["materialization_kind"] == "antigravity_brain_file"
    assert str(source) not in repr(material.binding)


def test_bare_prose_uri_with_trailing_parenthesis_is_preserved(
    tmp_path: Path,
) -> None:
    # A bare URI followed by a closing parenthesis in prose (e.g. parenthetical reference)
    # is preserved because generic trailing prose-punctuation stripping removes the `)`.
    source = _brain_file(tmp_path, b"# Bare parenthetical plan\n")
    stdout = f"(see {source.as_uri()})\n".encode("utf-8")

    material = plan_material.materialize(
        stdout,
        provider="antigravity",
        profile="gemini-3.7-flash-medium",
        _home=tmp_path,
    )

    assert material.data == b"# Bare parenthetical plan\n"
    assert material.binding["materialization_kind"] == "antigravity_brain_file"


def test_mixed_markdown_and_bare_same_artifact_deduplicate(tmp_path: Path) -> None:
    source = _brain_file(tmp_path, b"# Deduplicated mixed plan\n")
    uri = source.as_uri()
    stdout = (
        f"Styled: **[plan]({uri})**\nBare: {uri}\nUnstyled: [plan]({uri})\n"
    ).encode("utf-8")

    material = plan_material.materialize(
        stdout,
        provider="antigravity",
        profile="gemini-3.7-flash-medium",
        _home=tmp_path,
    )

    assert material.data == b"# Deduplicated mixed plan\n"
    assert material.binding["materialization_kind"] == "antigravity_brain_file"


@pytest.mark.parametrize(
    "stdout_template",
    [
        "**[plan1]({first})**\n**[plan2]({second})**",
        "**[plan1]({first})**\n{second}",
        "[plan1]({first})\n{second}",
    ],
)
def test_mixed_distinct_brain_artifacts_are_ambiguous(
    tmp_path: Path, stdout_template: str
) -> None:
    first = _brain_file(tmp_path, session="session-1", name="plan.md")
    second = _brain_file(tmp_path, session="session-2", name="alternative.md")
    stdout = stdout_template.format(
        first=first.as_uri(), second=second.as_uri()
    ).encode("utf-8")

    with pytest.raises(plan_material.PlanMaterialError) as caught:
        plan_material.materialize(
            stdout,
            provider="antigravity",
            profile="gemini-3.7-flash-medium",
            _home=tmp_path,
        )

    assert caught.value.code == "PLAN_ARTIFACT_SOURCE_AMBIGUOUS"
    assert str(tmp_path) not in str(caught.value)


def test_markdown_and_bare_repository_file_uris_use_inline_stdout_without_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def reject_read(*_args: object, **_kwargs: object) -> bytes:
        raise AssertionError("external file URI must not be read")

    monkeypatch.setattr(plan_material, "_read_brain_artifact", reject_read)
    stdout = (
        b"Plan references: **[doc](file:" b"///repository/docs/plan.md)** and "
        b"[main](file:" b"///repository/src/main.rs) and file:" b"///tmp/scratch.md"
    )
    assert Path("/repository/docs/plan.md").as_uri().encode() in stdout
    assert Path("/repository/src/main.rs").as_uri().encode() in stdout
    assert Path("/tmp/scratch.md").as_uri().encode() in stdout

    material = plan_material.materialize(
        stdout,
        provider="antigravity",
        profile="gemini-3.7-flash-medium",
        _home=tmp_path,
    )

    assert material.data == stdout
    assert material.binding["materialization_kind"] == "inline_stdout"


@pytest.mark.parametrize(
    "malicious_suffix",
    [
        ")/../../etc/passwd",
        "/../../etc/passwd",
        "/../../../etc/shadow",
    ],
)
def test_malicious_bare_uri_with_traversal_is_rejected(
    tmp_path: Path, malicious_suffix: str
) -> None:
    source = _brain_file(tmp_path)
    stdout = f"summary {source.as_uri()}{malicious_suffix}\n".encode("utf-8")

    with pytest.raises(plan_material.PlanMaterialError) as caught:
        plan_material.materialize(
            stdout,
            provider="antigravity",
            profile="gemini-3.7-flash-medium",
            _home=tmp_path,
        )

    assert caught.value.code == "PLAN_ARTIFACT_SOURCE_UNSAFE"
    assert str(tmp_path) not in str(caught.value)


@pytest.mark.parametrize(
    "malformed_construct",
    [
        # Markdown construct with path traversal continuation after `)`
        "[plan]({uri})/../../etc/passwd",
        "[plan]({uri})/subpath",
        "[plan]({uri})other",
        # Bare emphasis-wrapped URI (outside supported Markdown link form)
        "**{uri}**",
        "*{uri}*",
        # Raw parenthesis inside session or filename component
        "{brain_base}/sess)ion/plan.md",
        "{brain_base}/session-1/plan)name.md",
        # Malformed / unterminated Markdown with traversal
        "[plan({uri})/../../etc/passwd",
        # Unsupported query / fragment / authority / percent-encoded traversal in Markdown links
        "[plan]({uri}?query=1)",
        "[plan]({uri}#fragment)",
        "[plan]({brain_base}/session-1/%2e%2e/passwd.md)",
        "[plan]({brain_base}/session-1/nested/plan.md)",
        "[plan]({authority_uri})",
        "[plan]({localhost_uri})",
        # Unsupported query / fragment / authority / percent-encoded traversal in bare URIs
        "{authority_uri}",
        "{localhost_uri}",
        "{uri}?query=1",
        "{uri}#fragment",
        "{brain_base}/session-1/%2e%2e/passwd.md",
        "{brain_base}/session-1/nested/plan.md",
    ],
)
def test_malformed_and_unsafe_markdown_tokens_are_rejected(
    tmp_path: Path, malformed_construct: str
) -> None:
    source = _brain_file(tmp_path)
    brain_base = source.parent.parent.as_uri()
    uri_path = source.as_uri()[len("file://"):]
    authority_uri = f"file://attacker.example.com{uri_path}"
    localhost_uri = f"file://localhost{uri_path}"
    rendered = malformed_construct.format(
        uri=source.as_uri(),
        brain_base=brain_base,
        authority_uri=authority_uri,
        localhost_uri=localhost_uri,
    )
    stdout = f"Summary with {rendered}\n".encode("utf-8")

    with pytest.raises(plan_material.PlanMaterialError) as caught:
        plan_material.materialize(
            stdout,
            provider="antigravity",
            profile="gemini-3.7-flash-medium",
            _home=tmp_path,
        )

    assert caught.value.code == "PLAN_ARTIFACT_SOURCE_UNSAFE"
    assert str(tmp_path) not in str(caught.value)


def test_antigravity_brain_uri_ignores_repository_file_links(
    tmp_path: Path,
) -> None:
    source = _brain_file(tmp_path, b"# Detailed plan\nprovider-private detail\n")
    repository = tmp_path / "repository"
    references = [
        repository / "docs" / "architecture.md",
        repository / "src" / "main.rs",
        repository / "package.json",
        repository / "src-tauri" / "tauri.conf.json",
    ]
    stdout = b"\n".join(
        [
            b"Short planning summary; detailed plan: "
            + source.as_uri().encode("ascii"),
            *(
                b"Supporting reference: " + path.as_uri().encode("ascii")
                for path in references
            ),
        ]
    )

    material = plan_material.materialize(
        stdout,
        provider="antigravity",
        profile="gemini-3.7-flash-medium",
        _home=tmp_path,
    )

    assert material.data == b"# Detailed plan\nprovider-private detail\n"
    assert material.binding["materialization_kind"] == "antigravity_brain_file"
    assert str(source) not in repr(material.binding)


def test_duplicate_brain_uri_references_are_not_ambiguous(tmp_path: Path) -> None:
    source = _brain_file(tmp_path, b"# Deduplicated plan\n")
    uri = source.as_uri().encode("ascii")

    material = plan_material.materialize(
        b"Detailed plan: " + uri + b"\nRepeated detail link: " + uri,
        provider="antigravity",
        profile="gemini-3.7-flash-medium",
        _home=tmp_path,
    )

    assert material.data == b"# Deduplicated plan\n"


def test_two_distinct_brain_artifacts_are_ambiguous(tmp_path: Path) -> None:
    first = _brain_file(tmp_path, session="session-1", name="plan.md")
    second = _brain_file(tmp_path, session="session-2", name="alternative.md")

    with pytest.raises(plan_material.PlanMaterialError) as caught:
        plan_material.materialize(
            first.as_uri().encode("ascii")
            + b"\n"
            + second.as_uri().encode("ascii"),
            provider="antigravity",
            profile="gemini-3.7-flash-medium",
            _home=tmp_path,
        )

    assert caught.value.code == "PLAN_ARTIFACT_SOURCE_AMBIGUOUS"
    assert str(tmp_path) not in str(caught.value)


def test_repository_file_uris_use_inline_stdout_without_file_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stdout = b"Plan text with file:" b"///repository/docs/plan.md and file:" b"///tmp/source.rs"
    assert Path("/repository/docs/plan.md").as_uri().encode() in stdout
    assert Path("/tmp/source.rs").as_uri().encode() in stdout

    def reject_read(*_args: object, **_kwargs: object) -> bytes:
        raise AssertionError("external file URI must not be read")

    monkeypatch.setattr(plan_material, "_read_brain_artifact", reject_read)
    material = plan_material.materialize(
        stdout,
        provider="antigravity",
        profile="gemini-3.7-flash-medium",
        _home=tmp_path,
    )

    assert material.data == stdout
    assert material.binding["materialization_kind"] == "inline_stdout"


def test_antigravity_effective_home_requires_safe_directory_mode(
    tmp_path: Path,
) -> None:
    source = _brain_file(tmp_path)
    tmp_path.chmod(0o777)

    with pytest.raises(plan_material.PlanMaterialError) as caught:
        plan_material.materialize(
            b"summary " + source.as_uri().encode("ascii"),
            provider="antigravity",
            profile="gemini-3.7-flash-medium",
            _home=tmp_path,
        )

    assert caught.value.code == "PLAN_ARTIFACT_SOURCE_MODE"


def test_dispatch_archives_and_forwards_only_canonical_brain_bytes(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan_bytes = b"# Complete plan\r\nprivate detail\r\n"
    source = _brain_file(tmp_path, plan_bytes)
    source_path = str(source)
    source_uri = source.as_uri().encode("ascii")
    stdout = f"👉 **[plan]({source.as_uri()})**\n".encode("utf-8")
    monkeypatch.setattr(plan_material, "_effective_home", lambda _override: tmp_path)

    def make_brain_unavailable(index: int) -> None:
        if index == 1:
            brain = tmp_path / ".gemini" / "antigravity-cli" / "brain"
            brain.rename(tmp_path / "brain-unavailable-to-reviewer")

    runner = FakeRunner(stdout_by_index={0: stdout}, on_stage=make_brain_unavailable)

    state = make_dispatcher(repository, tmp_path, runner).dispatch(
        PHASE_ID,
            # The product-validated Gemini-only mode keeps this transport test stable.
            PhaseRequest("implementation_testing", "gemini_only", "bounded task"),
        finalization_policy="checkpoint",
    )

    run_directory = Path(state["run_directory"])
    assert not source.exists()
    assert (run_directory / plan_material.CANONICAL_PATH).read_bytes() == plan_bytes
    assert (run_directory / "01-plan.stdout.md").read_bytes() == stdout
    assert state["plan_candidate"]["materialization_kind"] == "antigravity_brain_file"
    assert source_path not in repr(state)
    assert source_path not in repr(state["plan_candidate"])
    assert source_uri.decode("ascii") not in repr(state)

    for index in (1, 2, 3, 4):
        prompt = runner.calls[index]["prompt"]
        assert source_uri not in prompt
        assert source_path.encode("utf-8") not in prompt

    for index in (1, 2):
        assert plan_bytes in runner.calls[index]["prompt"]

    result_json = (run_directory / "result.json").read_text(encoding="utf-8")
    result_md = (run_directory / "result.md").read_text(encoding="utf-8")
    assert source_path not in result_json
    assert source_uri.decode("ascii") not in result_json
    assert source_path not in result_md
    assert source_uri.decode("ascii") not in result_md

    for artifact in run_directory.iterdir():
        if artifact.name == "01-plan.stdout.md":
            continue
        content = artifact.read_bytes()
        assert source_path.encode("utf-8") not in content
        assert source_uri not in content


@pytest.mark.parametrize("include_valid", [False, True])
def test_unsafe_brain_namespace_uri_blocks_before_review(
    tmp_path: Path, include_valid: bool
) -> None:
    source = _brain_file(tmp_path)
    unsafe = source.parent.as_uri().encode("ascii") + b"/../other.md"
    stdout = b"summary " + unsafe
    if include_valid:
        stdout += b" valid " + source.as_uri().encode("ascii")

    with pytest.raises(plan_material.PlanMaterialError) as caught:
        plan_material.materialize(
            stdout,
            provider="antigravity",
            profile="gemini-3.7-flash-medium",
            _home=tmp_path,
        )

    assert caught.value.code == "PLAN_ARTIFACT_SOURCE_UNSAFE"
    assert str(tmp_path) not in str(caught.value)


def test_symlinked_brain_artifact_is_rejected(tmp_path: Path) -> None:
    source = _brain_file(tmp_path)
    replacement = tmp_path / "replacement.md"
    replacement.write_bytes(b"outside\n")
    replacement.chmod(0o600)
    source.unlink()
    source.symlink_to(replacement)
    stdout = b"summary " + source.as_uri().encode("ascii")

    with pytest.raises(plan_material.PlanMaterialError) as caught:
        plan_material.materialize(
            stdout,
            provider="antigravity",
            profile="gemini-3.7-flash-medium",
            _home=tmp_path,
        )

    assert caught.value.code == "PLAN_ARTIFACT_SOURCE_SYMLINK"


def test_missing_brain_artifact_is_rejected_without_disclosing_home(
    tmp_path: Path,
) -> None:
    brain = tmp_path / ".gemini" / "antigravity-cli" / "brain" / "session-1"
    brain.mkdir(mode=0o700, parents=True)
    for parent in (
        tmp_path / ".gemini",
        tmp_path / ".gemini" / "antigravity-cli",
        tmp_path / ".gemini" / "antigravity-cli" / "brain",
        brain,
    ):
        parent.chmod(0o700)
    stdout = b"summary " + (brain / "missing.md").as_uri().encode("ascii")

    with pytest.raises(plan_material.PlanMaterialError) as caught:
        plan_material.materialize(
            stdout,
            "antigravity",
            "gemini-3.7-flash-medium",
            _home=tmp_path,
        )

    assert caught.value.code == "PLAN_ARTIFACT_SOURCE_MISSING"
    assert str(tmp_path) not in str(caught.value)


@pytest.mark.parametrize("mode", [0o666, 0o700])
def test_brain_artifact_requires_private_regular_file_mode(
    tmp_path: Path, mode: int
) -> None:
    source = _brain_file(tmp_path)
    source.chmod(mode)
    stdout = b"summary " + source.as_uri().encode("ascii")

    with pytest.raises(plan_material.PlanMaterialError) as caught:
        plan_material.materialize(
            stdout,
            "antigravity",
            "gemini-3.7-flash-medium",
            _home=tmp_path,
        )

    assert caught.value.code == "PLAN_ARTIFACT_SOURCE_MODE"


def test_invalid_utf8_brain_artifact_is_rejected(tmp_path: Path) -> None:
    source = _brain_file(tmp_path, b"\xff")
    stdout = b"summary " + source.as_uri().encode("ascii")

    with pytest.raises(plan_material.PlanMaterialError) as caught:
        plan_material.materialize(
            stdout,
            "antigravity",
            "gemini-3.7-flash-medium",
            _home=tmp_path,
        )

    assert caught.value.code == "PLAN_ARTIFACT_SOURCE_NOT_UTF8"


def test_brain_artifact_wrong_owner_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _brain_file(tmp_path)
    target_stat = source.stat()
    target_identity = (target_stat.st_dev, target_stat.st_ino)
    expected_uid = target_stat.st_uid + 1000
    real_stat = os.stat
    stat_fired = 0

    def fake_stat(
        path: Any,
        *args: Any,
        dir_fd: int | None = None,
        follow_symlinks: bool = True,
        **kwargs: Any,
    ) -> os.stat_result:
        nonlocal stat_fired
        real = real_stat(
            path,
            *args,
            dir_fd=dir_fd,
            follow_symlinks=follow_symlinks,
            **kwargs,
        )
        if (real.st_dev, real.st_ino) == target_identity:
            stat_fired += 1
            return _clone_stat(real, st_uid=expected_uid)
        return real

    monkeypatch.setattr(os, "stat", fake_stat)

    real_file_mode = plan_material._file_mode
    file_mode_calls: list[os.stat_result] = []

    def wrapped_file_mode(info: os.stat_result, *, source: str) -> None:
        file_mode_calls.append(info)
        real_file_mode(info, source=source)

    monkeypatch.setattr(plan_material, "_file_mode", wrapped_file_mode)

    stdout = b"summary " + source.as_uri().encode("ascii")

    with pytest.raises(plan_material.PlanMaterialError) as caught:
        plan_material.materialize(
            stdout,
            "antigravity",
            "gemini-3.7-flash-medium",
            _home=tmp_path,
        )

    assert caught.value.code == "PLAN_ARTIFACT_SOURCE_OWNER"
    assert caught.value.detail == "brain artifact has the wrong owner"
    assert stat_fired == 1
    assert len(file_mode_calls) == 1
    assert file_mode_calls[0].st_uid == expected_uid
    assert (file_mode_calls[0].st_dev, file_mode_calls[0].st_ino) == target_identity


def test_brain_directory_wrong_owner_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _brain_file(tmp_path)
    target_dir = source.parent.parent
    target_stat = target_dir.stat()
    target_identity = (target_stat.st_dev, target_stat.st_ino)
    expected_uid = target_stat.st_uid + 1000
    real_stat = os.stat
    stat_fired = 0

    def fake_stat(
        path: Any,
        *args: Any,
        dir_fd: int | None = None,
        follow_symlinks: bool = True,
        **kwargs: Any,
    ) -> os.stat_result:
        nonlocal stat_fired
        real = real_stat(
            path,
            *args,
            dir_fd=dir_fd,
            follow_symlinks=follow_symlinks,
            **kwargs,
        )
        if (real.st_dev, real.st_ino) == target_identity:
            stat_fired += 1
            return _clone_stat(real, st_uid=expected_uid)
        return real

    monkeypatch.setattr(os, "stat", fake_stat)
    stdout = f"👉 **[plan]({source.as_uri()})**\n".encode("utf-8")

    with pytest.raises(plan_material.PlanMaterialError) as caught:
        plan_material.materialize(
            stdout,
            "antigravity",
            "gemini-3.7-flash-medium",
            _home=tmp_path,
        )

    assert caught.value.code == "PLAN_ARTIFACT_SOURCE_OWNER"
    assert caught.value.detail == "brain path component has the wrong owner"
    assert stat_fired == 1


def test_brain_artifact_hard_link_is_rejected(tmp_path: Path) -> None:
    source = _brain_file(tmp_path)
    link = tmp_path / "hardlink.md"
    os.link(source, link)
    stdout = b"summary " + source.as_uri().encode("ascii")

    with pytest.raises(plan_material.PlanMaterialError) as caught:
        plan_material.materialize(
            stdout,
            "antigravity",
            "gemini-3.7-flash-medium",
            _home=tmp_path,
        )

    assert caught.value.code == "PLAN_ARTIFACT_SOURCE_LINKS"


def test_brain_artifact_replacement_race_on_open_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _brain_file(tmp_path)
    target_identity = (source.stat().st_dev, source.stat().st_ino)
    real_fstat = os.fstat
    fstat_fired = 0

    def fake_fstat(fd: int) -> os.stat_result:
        nonlocal fstat_fired
        stat_res = real_fstat(fd)
        if (stat_res.st_dev, stat_res.st_ino) == target_identity:
            fstat_fired += 1
            return _clone_stat(stat_res, st_ino=stat_res.st_ino + 100)
        return stat_res

    monkeypatch.setattr(os, "fstat", fake_fstat)
    stdout = b"summary " + source.as_uri().encode("ascii")

    with pytest.raises(plan_material.PlanMaterialError) as caught:
        plan_material.materialize(
            stdout,
            "antigravity",
            "gemini-3.7-flash-medium",
            _home=tmp_path,
        )

    assert caught.value.code == "PLAN_ARTIFACT_SOURCE_REPLACED"
    assert caught.value.detail == "brain artifact changed while opening"
    assert fstat_fired == 1


def test_brain_artifact_replacement_race_during_read_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_data = b"# Original plan content\n"
    replacement_data = b"# Replaced plan content\n"
    assert len(replacement_data) == len(original_data)
    source = _brain_file(tmp_path, original_data)
    moved_source = source.with_name(f".{source.name}.opened")
    original_stat = source.stat()
    original_identity = plan_material._identity(original_stat)
    real_read = os.read
    real_fstat = os.fstat
    replacement_fired = 0
    descriptor_identities: list[tuple[int, int, int, int, int, int, int]] = []
    read_lengths: list[int] = []

    def fake_read(fd: int, n: int) -> bytes:
        nonlocal replacement_fired
        if replacement_fired == 0:
            source.rename(moved_source)
            source.write_bytes(replacement_data)
            source.chmod(0o600)
            replacement_fired += 1
        data = real_read(fd, n)
        descriptor_identities.append(plan_material._identity(real_fstat(fd)))
        read_lengths.append(len(data))
        return data

    monkeypatch.setattr(os, "read", fake_read)
    stdout = b"summary " + source.as_uri().encode("ascii")

    with pytest.raises(plan_material.PlanMaterialError) as caught:
        plan_material.materialize(
            stdout,
            "antigravity",
            "gemini-3.7-flash-medium",
            _home=tmp_path,
        )

    assert caught.value.code == "PLAN_ARTIFACT_SOURCE_REPLACED"
    assert caught.value.detail == "brain artifact changed while reading"
    assert replacement_fired == 1
    assert descriptor_identities
    condition_vector = (
        descriptor_identities[-1] != original_identity,
        plan_material._identity(source.stat()) != original_identity,
        sum(read_lengths) != original_stat.st_size,
    )
    assert condition_vector == (False, True, False)
    assert plan_material._identity(moved_source.stat()) == original_identity


def test_stat_result_clone_preserves_identity(tmp_path: Path) -> None:
    source = _brain_file(tmp_path)
    real = source.stat()
    original_identity = plan_material._identity(real)
    original_nanoseconds = (real.st_atime_ns, real.st_mtime_ns, real.st_ctime_ns)
    unperturbed = _clone_stat(real)
    assert plan_material._identity(unperturbed) == original_identity
    assert (
        unperturbed.st_atime_ns,
        unperturbed.st_mtime_ns,
        unperturbed.st_ctime_ns,
    ) == original_nanoseconds

    perturbed_ino = _clone_stat(real, st_ino=real.st_ino + 100)
    expected_ino_identity = list(original_identity)
    expected_ino_identity[1] = real.st_ino + 100
    assert plan_material._identity(perturbed_ino) == tuple(expected_ino_identity)

    perturbed_uid = _clone_stat(real, st_uid=real.st_uid + 1000)
    expected_uid_identity = list(original_identity)
    expected_uid_identity[3] = real.st_uid + 1000
    assert plan_material._identity(perturbed_uid) == tuple(expected_uid_identity)

    for perturbed in (perturbed_ino, perturbed_uid):
        assert (
            perturbed.st_atime_ns,
            perturbed.st_mtime_ns,
            perturbed.st_ctime_ns,
        ) == original_nanoseconds


def test_brain_artifact_oversized_is_rejected(tmp_path: Path) -> None:
    source = _brain_file(tmp_path, b"x" * (plan_material.MAX_PLAN_BYTES + 1))
    stdout = b"summary " + source.as_uri().encode("ascii")

    with pytest.raises(plan_material.PlanMaterialError) as caught:
        plan_material.materialize(
            stdout,
            "antigravity",
            "gemini-3.7-flash-medium",
            _home=tmp_path,
        )

    assert caught.value.code == "PLAN_ARTIFACT_SOURCE_OVERSIZED"


def test_inline_stdout_oversized_is_rejected() -> None:
    raw = b"x" * (plan_material.MAX_PLAN_BYTES + 1)

    with pytest.raises(plan_material.PlanMaterialError) as caught:
        plan_material.materialize(
            raw,
            provider="codex",
            profile="implementation-testing",
        )

    assert caught.value.code == "PLAN_ARTIFACT_OVERSIZED"


def test_canonical_artifact_round_trip_and_tamper_rejection(tmp_path: Path) -> None:
    raw = b"exact\r\nplan"
    material = plan_material.materialize(raw, "codex", "implementation-testing")
    directory = tmp_path / "run"
    directory.mkdir()

    plan_material.write(directory, material)
    assert (directory / plan_material.CANONICAL_PATH).read_bytes() == raw
    assert plan_material.verify(directory, material.binding) == raw

    (directory / plan_material.CANONICAL_PATH).write_bytes(b"tampered")
    with pytest.raises(plan_material.PlanMaterialError) as caught:
        plan_material.verify(directory, material.binding)
    assert caught.value.code == "PLAN_ARTIFACT_BINDING_MISMATCH"


def test_binary_segments_preserve_exact_plan_bytes_without_newline_normalization() -> None:
    raw = b"first\r\nsecond"
    rendered = envelope.render(
        [envelope.Segment(envelope.SEGMENT_PRIOR_MATERIAL, raw)]
    )

    assert rendered.data == raw
    segment = rendered.segments[0]
    assert rendered.data[segment["start"] : segment["end"]] == raw
