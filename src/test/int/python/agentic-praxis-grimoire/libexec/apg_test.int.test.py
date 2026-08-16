"""Real filesystem and coverage-data contracts for libexec/apg_test.py."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from coverage import CoverageData
import pytest

from libexec import apg_test
from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)


def write_events(path: Path, events: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(event) + "\n" for event in events),
        encoding="utf-8",
    )


def run_covered_child(
    script: Path,
    cwd: Path,
    manifest: Path,
    coverage_base: Path,
    *,
    entrypoints: list[str],
    modules: list[str],
) -> set[str]:
    manifest.write_text("", encoding="utf-8")
    environment = os.environ.copy()
    for name in tuple(environment):
        if name.startswith(("APG_TEST_", "COV_CORE_")) or name == (
            "COVERAGE_PROCESS_CONFIG"
        ):
            environment.pop(name)
    environment.update(
        {
            "APG_TEST_RUN_ID": "bootstrap-run",
            "APG_TEST_SUITE": "integration",
            "APG_TEST_CHILD_MANIFEST": str(manifest),
            "APG_TEST_REQUIRED_ENTRYPOINTS": json.dumps(entrypoints),
            "APG_TEST_REQUIRED_MODULE_BASENAMES": json.dumps(modules),
            "APG_TEST_CANONICAL_LIBEXEC": str(REPOSITORY_ROOT / "libexec"),
            "APG_TEST_CANONICAL_PACKAGE": str(
                REPOSITORY_ROOT / "src" / "agentic_praxis_grimoire"
            ),
            "COVERAGE_PROCESS_START": str(REPOSITORY_ROOT / ".coveragerc"),
            "COVERAGE_FILE": str(coverage_base),
            "PYTHONPATH": os.pathsep.join(
                (
                    str(REPOSITORY_ROOT / "src/test/apg_coverage_bootstrap"),
                    str(REPOSITORY_ROOT),
                )
            ),
        }
    )
    command = ["/usr/bin/env"]
    for name in (
        "COV_CORE_SOURCE",
        "COV_CORE_CONFIG",
        "COV_CORE_DATAFILE",
        "COV_CORE_BRANCH",
    ):
        command.extend(("-u", name))
    result = subprocess.run(
        [*command, sys.executable, str(script)],
        cwd=cwd,
        env=environment,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert result.returncode == 0, result
    contexts: set[str] = set()
    coverage_paths = [
        coverage_base,
        *coverage_base.parent.glob(f"{coverage_base.name}.*"),
    ]
    for path in coverage_paths:
        if not path.is_file():
            continue
        data = CoverageData(basename=str(path))
        data.read()
        contexts.update(data.measured_contexts())
        data.close(force=True)
    return contexts


def worker_events() -> list[dict[str, object]]:
    shared = {"run_id": "run-1", "suite": "unit"}
    node_ids = [f"{apg_test.UNIT_ROOT.as_posix()}/owner.unit.test.py::test_one"]
    events: list[dict[str, object]] = []
    for worker in ("gw0", "gw1"):
        events.extend(
            [
                {**shared, "event": "worker-start", "worker": worker},
                {**shared, "event": "collection", "worker": worker, "node_ids": node_ids},
                {**shared, "event": "worker-complete", "worker": worker, "exitstatus": 0},
                {**shared, "event": "node-down", "worker": worker, "error": False, "exitstatus": 0},
            ]
        )
    events.extend(
        [
            {**shared, "event": "test-result", "nodeid": node_ids[0], "outcome": "passed"},
            {**shared, "event": "controller-complete", "exitstatus": 0},
        ]
    )
    return events


def test_worker_manifest_accepts_complete_jsonl_and_coverage_contexts(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "workers.jsonl"
    write_events(manifest, worker_events())
    apg_test.validate_worker_manifest(
        manifest,
        "run-1",
        "unit",
        2,
        apg_test.UNIT_ROOT.as_posix(),
        {"apg-worker:run-1:gw0", "apg-worker:run-1:gw1"},
    )


def test_child_manifest_reads_real_coverage_context_data(tmp_path: Path) -> None:
    coverage_path = tmp_path / "coverage"
    data = CoverageData(basename=str(coverage_path))
    data.set_context("apg-child:run-1:one")
    data.add_lines({str(tmp_path / "source.py"): {1}})
    data.write()
    data.close(force=True)
    contexts = apg_test._coverage_contexts(coverage_path)
    manifest = tmp_path / "children.jsonl"
    write_events(
        manifest,
        [
            {
                "run_id": "run-1",
                "suite": "unit",
                "event": event,
                "process_id": "one",
                "context": "apg-child:run-1:one",
            }
            for event in ("child-start", "child-complete")
        ],
    )
    apg_test.validate_child_manifest(manifest, "run-1", "unit", contexts)


def test_real_bootstrap_discovers_only_required_maintained_python_children(
    tmp_path: Path,
) -> None:
    modules = sorted(
        path.name for path in (REPOSITORY_ROOT / "libexec").rglob("*.py")
    )

    canonical = tmp_path / "canonical" / "git-show-report"
    canonical.parent.mkdir()
    canonical.write_text(
        "from libexec.agent_report.rendering import ensure_payload_ending\n"
        "assert ensure_payload_ending(b\"payload\") == b\"payload\\n\"\n",
        encoding="utf-8",
    )
    canonical_manifest = tmp_path / "canonical.children.jsonl"
    canonical_contexts = run_covered_child(
        canonical,
        REPOSITORY_ROOT,
        canonical_manifest,
        tmp_path / "canonical.coverage",
        entrypoints=[canonical.name],
        modules=modules,
    )
    apg_test.validate_child_manifest(
        canonical_manifest,
        "bootstrap-run",
        "integration",
        canonical_contexts,
    )
    assert any(
        context.startswith("apg-child:bootstrap-run:git-show-report-")
        for context in canonical_contexts
    )

    public_source = tmp_path / "public-source"
    public_libexec = public_source / "libexec"
    public_libexec.mkdir(parents=True)
    shutil.copy2(
        REPOSITORY_ROOT / "libexec/apg_project_skills_core.py",
        public_libexec / "apg_project_skills_core.py",
    )
    copied = public_source / "apg-project-skills"
    copied.write_text(
        "import sys\n"
        "sys.path.insert(0, 'libexec')\n"
        "import apg_project_skills_core as core\n"
        "assert core.relative_projection('example') == '.agents/skills/example'\n",
        encoding="utf-8",
    )
    copied_manifest = tmp_path / "copied.children.jsonl"
    copied_contexts = run_covered_child(
        copied,
        public_source,
        copied_manifest,
        tmp_path / "copied.coverage",
        entrypoints=[copied.name],
        modules=modules,
    )
    apg_test.validate_child_manifest(
        copied_manifest,
        "bootstrap-run",
        "integration",
        copied_contexts,
    )
    assert any(
        context.startswith("apg-child:bootstrap-run:apg-project-skills-")
        for context in copied_contexts
    )

    inert = tmp_path / "inert" / "git-show-report"
    inert.parent.mkdir()
    inert.write_text("pass\n", encoding="utf-8")
    inert_manifest = tmp_path / "inert.children.jsonl"
    inert_contexts = run_covered_child(
        inert,
        tmp_path,
        inert_manifest,
        tmp_path / "inert.coverage",
        entrypoints=[inert.name],
        modules=modules,
    )
    assert inert_manifest.read_text(encoding="utf-8") == ""
    assert not {context for context in inert_contexts if context.startswith("apg-child:")}

    unrelated = tmp_path / "unrelated-tool"
    unrelated.write_text(canonical.read_text(encoding="utf-8"), encoding="utf-8")
    unrelated_manifest = tmp_path / "unrelated.children.jsonl"
    unrelated_contexts = run_covered_child(
        unrelated,
        REPOSITORY_ROOT,
        unrelated_manifest,
        tmp_path / "unrelated.coverage",
        entrypoints=[canonical.name],
        modules=modules,
    )
    subprocess.run(["/bin/sh", "-c", "exit 0"], check=True, env=os.environ.copy())
    assert unrelated_manifest.read_text(encoding="utf-8") == ""
    assert not {context for context in unrelated_contexts if context.startswith("apg-child:")}


def test_artifact_directory_identity_controls_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APG_TEST_ARTIFACT_ROOT", str(tmp_path))
    artifact = apg_test._artifact_directory(REPOSITORY_ROOT)
    assert artifact.path.stat().st_mode & 0o777 == 0o700
    (artifact.path / "evidence").write_text("bounded", encoding="utf-8")
    substituted = apg_test.ArtifactDirectory(
        artifact.path, artifact.device, artifact.inode + 1
    )
    with pytest.raises(apg_test.ToolError, match="identity changed"):
        apg_test._cleanup_artifacts(substituted)
    apg_test._cleanup_artifacts(artifact)
    assert not artifact.path.exists()


def test_real_coverage_databases_combine_into_one_report(tmp_path: Path) -> None:
    source = REPOSITORY_ROOT / "libexec/apg_test.py"
    paths: list[Path] = []
    for index, line in enumerate((1, 2)):
        path = tmp_path / f"component-{index}.coverage"
        data = CoverageData(basename=str(path))
        data.add_lines({str(source): {line}})
        data.write()
        data.close(force=True)
        paths.append(path)
    report = apg_test._combine_coverage(
        REPOSITORY_ROOT,
        paths,
        tmp_path / "combined.coverage",
    )
    assert "libexec/apg_test.py" in report["files"]


def test_real_manifest_files_reject_stale_duplicate_and_incomplete_lifecycles(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        '{"run_id":"run-1","run_id":"run-1","suite":"unit"}\n',
        encoding="utf-8",
    )
    with pytest.raises(apg_test.ToolError, match="malformed"):
        apg_test.validate_child_manifest(manifest, "run-1", "unit", set())

    write_events(
        manifest,
        [{"run_id": "stale", "suite": "unit", "event": "child-start"}],
    )
    with pytest.raises(apg_test.ToolError, match="foreign or stale"):
        apg_test.validate_child_manifest(manifest, "run-1", "unit", set())

    cases = (
        ([{"event": "unknown", "process_id": "one", "context": "apg-child:run-1:one"}], {"apg-child:run-1:one"}, "unexpected event"),
        ([{"event": "child-start", "process_id": "", "context": "apg-child:run-1:one"}], {"apg-child:run-1:one"}, "malformed"),
        ([{"event": "child-start", "process_id": "one", "context": "apg-child:run-1:one"}], {"apg-child:run-1:one"}, "exactly once"),
        ([
            {"event": "child-start", "process_id": "one", "context": "apg-child:run-1:one"},
            {"event": "child-complete", "process_id": "one", "context": "apg-child:run-1:one"},
        ], set(), "no observable coverage"),
    )
    for events, contexts, message in cases:
        write_events(
            manifest,
            [{"run_id": "run-1", "suite": "unit", **event} for event in events],
        )
        with pytest.raises(apg_test.ToolError, match=message):
            apg_test.validate_child_manifest(manifest, "run-1", "unit", contexts)

    complete = [
        {"event": "child-start", "process_id": "one", "context": "apg-child:run-1:one"},
        {"event": "child-complete", "process_id": "one", "context": "apg-child:run-1:one"},
    ]
    write_events(
        manifest,
        [{"run_id": "run-1", "suite": "unit", **event} for event in complete],
    )
    with pytest.raises(apg_test.ToolError, match="child coverage contribution differs"):
        apg_test.validate_child_manifest(
            manifest,
            "run-1",
            "unit",
            {"apg-child:run-1:one", "apg-child:foreign:stale"},
        )


def test_worker_manifest_rejects_real_crash_and_foreign_context_evidence(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "workers.jsonl"
    events = worker_events()
    events[3]["error"] = "crash"
    write_events(manifest, events)
    with pytest.raises(apg_test.ToolError, match="reports a crash"):
        apg_test.validate_worker_manifest(
            manifest,
            "run-1",
            "unit",
            2,
            apg_test.UNIT_ROOT.as_posix(),
        )
    write_events(manifest, worker_events())
    with pytest.raises(apg_test.ToolError, match="foreign=.*stale"):
        apg_test.validate_worker_manifest(
            manifest,
            "run-1",
            "unit",
            2,
            apg_test.UNIT_ROOT.as_posix(),
            {
                "apg-worker:run-1:gw0",
                "apg-worker:run-1:gw1",
                "apg-worker:stale:gw0",
            },
        )


def test_worker_manifest_rejects_incomplete_real_lifecycle_evidence(
    tmp_path: Path,
) -> None:
    cases = (
        (lambda events: events.append({"run_id": "run-1", "suite": "unit", "event": "unknown"}), "unexpected event"),
        (lambda events: events.pop(0), "worker-start set is incomplete"),
        (lambda events: events[1].update(node_ids=[]), "collection evidence is malformed or empty"),
        (lambda events: events[1].update(node_ids=["same", "same"]), "collection evidence is malformed or empty"),
        (lambda events: events[2].update(exitstatus=1), "completion evidence reports failure"),
        (lambda events: events[5].update(node_ids=["different::test"]), "did not collect identical node IDs"),
        (
            lambda events: [
                event.update(node_ids=["outside.py::test"])
                for event in events
                if event["event"] == "collection"
            ],
            "outside the selected root",
        ),
        (lambda events: events.pop(-2), "exactly one terminal result"),
        (lambda events: events[-2].pop("outcome"), "terminal result is malformed"),
        (lambda events: events.pop(), "controller completion evidence reports failure"),
        (lambda events: events[-1].update(exitstatus=1), "controller completion evidence reports failure"),
    )
    manifest = tmp_path / "workers.jsonl"
    for mutate, message in cases:
        events = worker_events()
        mutate(events)
        write_events(manifest, events)
        with pytest.raises(apg_test.ToolError, match=message):
            apg_test.validate_worker_manifest(
                manifest,
                "run-1",
                "unit",
                2,
                apg_test.UNIT_ROOT.as_posix(),
            )


def test_real_artifact_roots_and_coverage_databases_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APG_TEST_ARTIFACT_ROOT", "relative")
    with pytest.raises(apg_test.ToolError, match="absolute real directory"):
        apg_test._artifact_directory(REPOSITORY_ROOT)
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    monkeypatch.setenv("APG_TEST_ARTIFACT_ROOT", str(link))
    with pytest.raises(apg_test.ToolError, match="absolute real directory"):
        apg_test._artifact_directory(REPOSITORY_ROOT)

    manifest = tmp_path / "manifest"
    manifest.mkdir()
    with pytest.raises(apg_test.ToolError, match="unreadable"):
        apg_test.validate_child_manifest(manifest, "run-1", "unit", set())
    manifest.rmdir()
    manifest.write_text("[]\n", encoding="utf-8")
    with pytest.raises(apg_test.ToolError, match="not an object"):
        apg_test.validate_child_manifest(manifest, "run-1", "unit", set())

    invalid = tmp_path / "invalid.coverage"
    invalid.write_text("invalid", encoding="utf-8")
    with pytest.raises(apg_test.ToolError, match="contexts are unreadable"):
        apg_test._coverage_contexts(invalid)
    with pytest.raises(apg_test.ToolError, match="could not be combined"):
        apg_test._combine_coverage(
            REPOSITORY_ROOT,
            [invalid],
            tmp_path / "failed.coverage",
        )
