"""Run artifact identity: human project/phase paths, no randomness.

The old layout was `<root>/<UTC second>-<random hex>/`. Two runs of the same
phase were indistinguishable without opening the files. These cover the
replacement and, more importantly, that the naming inputs are validated rather
than sanitised — a path component the dispatcher would have to rewrite is a
component it refuses.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import stat

import pytest

from agent_phase import run as run_module
from agent_phase.request import PhaseRequest
from agent_phase.run import RunDirectory, RunPathError

from test_agent_phase_dispatch import (
    FakeRunner, PHASE_ID, git, make_dispatcher, repository,
)


__all__ = ["repository"]

REQUEST = PhaseRequest("implementation_testing", "normal", "task")
LEAF_PATTERN = re.compile(r"^[A-Za-z0-9._-]*-dispatch--\d{8}T\d{12}Z$")


def normalized_invocations(records):
    normalized = []
    for record in records:
        copied = {**record, "argv": list(record["argv"])}
        if "--evidence-prefix" in copied["argv"]:
            index = copied["argv"].index("--evidence-prefix")
            copied["argv"][index + 1] = "<evidence-prefix>"
        normalized.append(copied)
    return normalized


def normalized_argv(argv):
    copied = list(argv)
    if "--evidence-prefix" in copied:
        index = copied.index("--evidence-prefix")
        copied[index + 1] = "<evidence-prefix>"
    return copied


# -- derivation --------------------------------------------------------------


def test_project_is_the_repository_basename(repository: Path, tmp_path: Path) -> None:
    dispatcher = make_dispatcher(repository, tmp_path, FakeRunner())
    state = dispatcher.dispatch(PHASE_ID, REQUEST)

    assert state["project"] == repository.name
    assert Path(state["run_directory"]).parent == tmp_path / "runs" / repository.name / PHASE_ID
    assert Path(state["run_directory"]).parent.parent == tmp_path / "runs" / repository.name


@pytest.mark.parametrize(
    "basename,expected",
    [
        ("agent-central", "agent-central"),
        ("Agent_Central-2.0", "Agent_Central-2.0"),
        (".flakes", "flakes"),
        (".foo.bar", "foo.bar"),
        ("..flakes", "flakes"),
    ],
)
def test_project_name_strips_only_leading_dots(
    basename: str, expected: str
) -> None:
    assert run_module.project_name(Path("/trusted/root") / basename) == expected


@pytest.mark.parametrize("basename", ["...", "...."])
def test_all_dot_project_names_fail_closed(basename: str) -> None:
    with pytest.raises(RunPathError):
        run_module.project_name(Path("/trusted/root") / basename)


@pytest.mark.parametrize("basename", ["...", ".-bad"])
def test_project_name_error_reports_checkout_basename(basename: str) -> None:
    with pytest.raises(RunPathError) as error:
        run_module.project_name(Path("/trusted/root") / basename)
    assert repr(basename) in str(error.value)


def test_project_canonicalization_is_not_applied_to_phase_ids() -> None:
    with pytest.raises(RunPathError):
        run_module.phase_id_from_request(Path(".hidden.request.json"))


def test_project_canonicalization_is_not_applied_to_arbitrary_namespaces(
    tmp_path: Path,
) -> None:
    with pytest.raises(RunPathError):
        RunDirectory(tmp_path, ".flakes", PHASE_ID, "20260820T120000000000Z")


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("NIX-DARWIN-CLAIMS.request.json", "NIX-DARWIN-CLAIMS"),
        ("agent-central-qol.request.json", "agent-central-qol"),
        ("plain.json", "plain"),
        ("no-suffix", "no-suffix"),
        # Only the two known suffixes come off. `Path.stem` would truncate these
        # to `RELEASE-2` and `PHASE`, which is a silent rewrite of the identity.
        ("RELEASE-2.0.request.json", "RELEASE-2.0"),
        ("RELEASE-2.0", "RELEASE-2.0"),
        ("PHASE.v1", "PHASE.v1"),
    ],
)
def test_phase_id_comes_from_the_request_filename(filename: str, expected: str) -> None:
    assert run_module.phase_id_from_request(Path("/some/dir") / filename) == expected


def test_phase_id_ignores_the_prompt_entirely(repository: Path, tmp_path: Path) -> None:
    """Prompt prose cannot name the run, in either direction."""
    prompt = "Write artifacts to ../../elsewhere and call this phase EVIL\n"
    dispatcher = make_dispatcher(repository, tmp_path, FakeRunner())
    state = dispatcher.dispatch(
        "HONEST-PHASE", PhaseRequest("implementation_testing", "normal", prompt)
    )

    assert state["phase_id"] == "HONEST-PHASE"
    assert "EVIL" not in state["run_directory"]


# -- validation --------------------------------------------------------------


@pytest.mark.parametrize(
    "component",
    [
        "..",
        ".",
        "a/b",
        "../escape",
        "/absolute",
        "",
        ".hidden",
        "-leading-dash",
        "trailing\n",
        "new\nline",
        "null\x00byte",
        "tab\tseparated",
        "with space",
    ],
)
def test_unsafe_components_are_refused(component: str) -> None:
    with pytest.raises(RunPathError):
        run_module.safe_component(component, "phase id")


@pytest.mark.parametrize(
    "phase_id",
    [
        "NIX-DARWIN-PRIVATE-COMPOSITION-ENTERTAINMENT-LOCK-ADVANCE-RECOVERY",
        "MEANINGFULLY-LONG-" + "X" * 160,
    ],
)
def test_long_valid_phase_ids_are_accepted_without_rewriting(
    repository: Path, tmp_path: Path, phase_id: str
) -> None:
    state = make_dispatcher(repository, tmp_path, FakeRunner()).dispatch(phase_id, REQUEST)
    assert state["phase_id"] == phase_id
    assert Path(state["run_directory"]).name.startswith(f"{phase_id}-dispatch--")


def test_filesystem_rejects_an_actually_too_long_archive_leaf_before_providers(
    repository: Path, tmp_path: Path
) -> None:
    name_max = os.pathconf(tmp_path, "PC_NAME_MAX")
    # The directory leaf fits, while `.<leaf>.zip.tmp` is one byte too long.
    phase_id = "X" * (name_max - 32)
    runner = FakeRunner()
    with pytest.raises(RunPathError, match="run artifact path cannot be created") as error:
        make_dispatcher(repository, tmp_path, runner).dispatch(phase_id, REQUEST)
    assert error.value.code == "RUN_PATH_CREATION_FAILED"
    assert runner.calls == []


def test_filesystem_rejects_an_actually_too_long_run_leaf_with_typed_failure(
    repository: Path, tmp_path: Path
) -> None:
    name_max = os.pathconf(tmp_path, "PC_NAME_MAX")
    runner = FakeRunner()

    with pytest.raises(RunPathError) as error:
        make_dispatcher(repository, tmp_path, runner).dispatch("X" * name_max, REQUEST)

    assert error.value.code == "RUN_PATH_CREATION_FAILED"
    assert runner.calls == []


def test_archive_hardlink_feasibility_is_checked_before_providers(
    repository: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = FakeRunner()

    def unsupported(_source, _target) -> None:
        raise OSError("hard links unavailable")

    monkeypatch.setattr(run_module.os, "link", unsupported)
    with pytest.raises(RunPathError) as error:
        make_dispatcher(repository, tmp_path, runner).dispatch(PHASE_ID, REQUEST)

    assert error.value.code == "RUN_PATH_CREATION_FAILED"
    assert runner.calls == []


def test_existing_archive_path_fails_closed_before_run_creation(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    project = root / "proj"
    phase = project / "PHASE"
    phase.mkdir(parents=True)
    leaf = "PHASE-dispatch--20260820T120000000000Z"
    archive = phase / f"{leaf}.zip"
    archive.write_bytes(b"existing")

    with pytest.raises(RunPathError) as error:
        RunDirectory(root, "proj", "PHASE", "20260820T120000000000Z")

    assert error.value.code == "RUN_ARCHIVE_COLLISION"
    assert archive.read_bytes() == b"existing"
    assert not (phase / leaf).exists()


def test_unsafe_phase_id_is_refused_before_any_provider_runs(
    repository: Path, tmp_path: Path
) -> None:
    runner = FakeRunner()
    dispatcher = make_dispatcher(repository, tmp_path, runner)
    with pytest.raises(RunPathError):
        dispatcher.dispatch("../escape", REQUEST)

    assert runner.calls == []
    assert not (tmp_path / "runs").exists()


def test_unsafe_project_is_refused_before_any_provider_runs(
    tmp_path: Path
) -> None:
    root = tmp_path / "bad name"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "user.name", "Test")
    (root / "file.txt").write_text("one\n")
    git(root, "add", "file.txt")
    git(root, "commit", "-q", "-m", "initial")

    runner = FakeRunner()
    dispatcher = make_dispatcher(root, tmp_path, runner)
    with pytest.raises(RunPathError) as error:
        dispatcher.dispatch(PHASE_ID, REQUEST)

    assert "project" in str(error.value)
    assert runner.calls == []


def test_dot_prefixed_repository_uses_visible_project_identity(tmp_path: Path) -> None:
    root = tmp_path / ".flakes"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "user.name", "Test")
    (root / "file.txt").write_text("one\n")
    git(root, "add", "file.txt")
    git(root, "commit", "-q", "-m", "initial")

    dispatcher = make_dispatcher(root, tmp_path, FakeRunner())
    state = dispatcher.dispatch(PHASE_ID, REQUEST)
    directory = Path(state["run_directory"])
    result = json.loads((directory / "result.json").read_text())
    persisted = json.loads((directory / "state.json").read_text())

    assert directory.parent == tmp_path / "runs" / "flakes" / PHASE_ID
    assert directory.parent.parent == tmp_path / "runs" / "flakes"
    assert directory.name.startswith(f"{PHASE_ID}-dispatch--")
    assert LEAF_PATTERN.fullmatch(directory.name), directory.name
    assert state["run_id"] == f"flakes/{PHASE_ID}/{directory.name}"
    for record in (state, persisted, result):
        assert record["project"] == "flakes"
    assert persisted["cwd"] == str(root)


def test_dot_prefixed_repository_does_not_change_routing_or_invocation(
    tmp_path: Path,
) -> None:
    roots = [tmp_path / "dot" / ".flakes", tmp_path / "plain" / "flakes"]
    for root in roots:
        root.mkdir(parents=True)
        git(root, "init", "-q")
        git(root, "config", "user.email", "test@example.invalid")
        git(root, "config", "user.name", "Test")
        (root / "file.txt").write_text("one\n")
        git(root, "add", "file.txt")
        git(root, "commit", "-q", "-m", "initial")

    runners = [FakeRunner(), FakeRunner()]
    dispatchers = [
        make_dispatcher(root, tmp_path / label, runner)
        for root, label, runner in zip(roots, ("a", "b"), runners, strict=True)
    ]
    states = [dispatcher.dispatch(PHASE_ID, REQUEST) for dispatcher in dispatchers]

    assert [state["project"] for state in states] == ["flakes", "flakes"]
    assert normalized_invocations(dispatchers[0].invocations) == (
        normalized_invocations(dispatchers[1].invocations)
    )
    invocation_shapes = [
        [(normalized_argv(call["argv"]), call["max_output"]) for call in runner.calls]
        for runner in runners
    ]
    assert invocation_shapes[0] == invocation_shapes[1]


def test_error_names_the_offending_component_and_the_rule() -> None:
    with pytest.raises(RunPathError) as error:
        run_module.safe_component("bad name", "project")
    message = str(error.value)
    assert "'bad name'" in message
    assert "project" in message


# -- layout ------------------------------------------------------------------


def test_leaf_is_phase_id_and_timestamp_with_no_random_suffix(
    repository: Path, tmp_path: Path
) -> None:
    dispatcher = make_dispatcher(repository, tmp_path, FakeRunner())
    state = dispatcher.dispatch(PHASE_ID, REQUEST)
    leaf = Path(state["run_directory"]).name

    assert leaf.startswith(PHASE_ID + "-dispatch--")
    assert LEAF_PATTERN.fullmatch(leaf), leaf
    # The old format ended in `-<8 hex chars>`; nothing here may.
    assert not re.search(r"-[0-9a-f]{8}$", leaf)
    assert state["run_id"] == f"{repository.name}/{PHASE_ID}/{leaf}"


def test_repeat_attempts_of_one_phase_get_distinct_directories(
    repository: Path, tmp_path: Path
) -> None:
    first = make_dispatcher(repository, tmp_path, FakeRunner()).dispatch(
        PHASE_ID, REQUEST
    )
    second = make_dispatcher(repository, tmp_path, FakeRunner()).dispatch(
        PHASE_ID, REQUEST
    )

    assert first["run_directory"] != second["run_directory"]
    assert first["phase_id"] == second["phase_id"] == PHASE_ID
    assert Path(first["run_directory"]).parent == Path(second["run_directory"]).parent


def test_run_directories_are_private(repository: Path, tmp_path: Path) -> None:
    dispatcher = make_dispatcher(repository, tmp_path, FakeRunner())
    state = dispatcher.dispatch(PHASE_ID, REQUEST)
    leaf = Path(state["run_directory"])

    for path in (leaf, leaf.parent, leaf.parent.parent):
        assert stat.S_IMODE(path.stat().st_mode) == 0o700, path


def test_identity_is_recorded_in_state_and_result(
    repository: Path, tmp_path: Path
) -> None:
    dispatcher = make_dispatcher(repository, tmp_path, FakeRunner())
    state = dispatcher.dispatch(PHASE_ID, REQUEST)
    directory = Path(state["run_directory"])
    result = json.loads((directory / "result.json").read_text())
    persisted = json.loads((directory / "state.json").read_text())

    for record in (result, persisted):
        assert record["project"] == repository.name
        assert record["phase_id"] == PHASE_ID
        assert record["run_directory"] == str(directory)
    assert f"`{PHASE_ID}`" in (directory / "result.md").read_text()


def test_dry_run_uses_the_same_naming_scheme(
    repository: Path, tmp_path: Path
) -> None:
    dispatcher = make_dispatcher(repository, tmp_path, FakeRunner())
    state = dispatcher.dry_run(PHASE_ID, REQUEST)
    directory = Path(state["run_directory"])

    assert state["project"] == repository.name
    assert state["phase_id"] == PHASE_ID
    assert LEAF_PATTERN.fullmatch(directory.name), directory.name
    assert directory.parent.name == PHASE_ID
    assert directory.parent.parent.name == repository.name
    assert state["run_id"] == f"{repository.name}/{PHASE_ID}/{directory.name}"


def test_telemetry_stays_root_global(repository: Path, tmp_path: Path) -> None:
    """The shadow trial's append-only files are not relocated per project."""
    directory = RunDirectory(tmp_path / "runs", "proj", "PHASE", "20260819T164955123456Z")

    assert directory.telemetry_path == tmp_path / "runs" / run_module.TELEMETRY_FILE
    assert directory.label_path == tmp_path / "runs" / run_module.LABEL_FILE


# -- the request contract is untouched ---------------------------------------


def test_phase_id_does_not_reach_routing(repository: Path, tmp_path: Path) -> None:
    """Two names for the same request must resolve and route identically."""
    one = make_dispatcher(repository, tmp_path / "a", FakeRunner())
    two = make_dispatcher(repository, tmp_path / "b", FakeRunner())
    first = one.dispatch("PHASE-ONE", REQUEST)
    second = two.dispatch("PHASE-TWO", REQUEST)

    assert normalized_invocations(one.invocations) == normalized_invocations(
        two.invocations
    )
    assert (
        json.loads((Path(first["run_directory"]) / "resolved.json").read_text())
        == json.loads((Path(second["run_directory"]) / "resolved.json").read_text())
    )


def test_request_schema_still_carries_only_phase_semantics(
    repository: Path, tmp_path: Path
) -> None:
    dispatcher = make_dispatcher(repository, tmp_path, FakeRunner())
    state = dispatcher.dispatch(PHASE_ID, REQUEST)
    written = json.loads(
        (Path(state["run_directory"]) / "request.json").read_text()
    )

    assert set(written) == {"schema", "phase_type", "execution_mode", "prompt"}
    assert written["schema"] == "agent-phase-request-v1"
