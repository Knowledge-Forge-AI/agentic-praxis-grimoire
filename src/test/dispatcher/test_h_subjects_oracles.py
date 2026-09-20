"""Focused APG166D subject-factory contracts.

The oracle implementation is owned by another bounded worker.  These tests
cover only clean subject construction, source-manifest binding, and isolation.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import sqlite3
import stat

import pytest

from testing.h_eval import subjects


SCENARIOS = subjects.all_scenario_ids()


def test_fixture_parent_link_refused(tmp_path):
    (tmp_path / "subjects").symlink_to(subjects.SUBJECT_ROOT, target_is_directory=True)
    with pytest.raises(subjects.SubjectError):
        subjects.subject_files("scenario-01", corpus_root=tmp_path)


def test_nonregular_inventory_entry_refused(tmp_path):
    os.mkfifo(tmp_path / "not-a-source-file")
    with pytest.raises(subjects.SubjectError):
        subjects.inventory(tmp_path)


def test_encoded_and_decoded_collision_refused(tmp_path):
    import base64
    fixture = tmp_path / "schema"
    fixture.mkdir()
    data = b"SQLite format 3\x00fixture"
    (fixture / "db.sqlite").write_bytes(data)
    (fixture / "db.sqlite.b64").write_bytes(base64.b64encode(data))
    with pytest.raises(subjects.SubjectError, match="duplicate"):
        list(subjects._iter_fixture_files(tmp_path, "scenario-06"))


def test_manifest_recomputes_all_fifteen_source_trees():
    value = subjects.verify_manifest()
    assert value["schema"] == subjects.MANIFEST_SCHEMA
    assert tuple(value["scenarios"]) == SCENARIOS
    assert all(value["scenarios"][sid]["files"] for sid in SCENARIOS)


@pytest.mark.parametrize("scenario_id", SCENARIOS)
def test_materialize_has_exact_repeatable_inventory(tmp_path: Path, scenario_id: str):
    static_root = tmp_path / "static"
    adaptive_root = tmp_path / "adaptive"
    static = subjects.materialize(scenario_id, static_root)
    adaptive = subjects.materialize(scenario_id, adaptive_root)

    assert static == adaptive
    assert static["scenario_id"] == scenario_id
    assert static["files"] == subjects.inventory(static_root)["files"]
    assert static["files"] == subjects.inventory(adaptive_root)["files"]
    subjects.verify_inventory(static_root, static)
    subjects.verify_inventory(adaptive_root, adaptive)
    assert not list(static_root.rglob("*.b64"))
    assert all(not path.is_symlink() for path in static_root.rglob("*"))
    assert all(stat.S_IMODE(path.stat().st_mode) in (0o644, 0o755)
               for path in static_root.rglob("*") if path.is_file())


def test_script_mode_and_binary_sqlite_are_bound(tmp_path: Path):
    script = subjects.materialize("scenario-04", tmp_path / "script")
    script_record = next(item for item in script["files"] if item["path"] == "scripts/build.sh")
    assert script_record["mode"] == 0o755
    assert stat.S_IMODE((tmp_path / "script/scripts/build.sh").stat().st_mode) == 0o755

    sqlite_inventory = subjects.materialize("scenario-06", tmp_path / "sqlite")
    database = tmp_path / "sqlite/schema/db.sqlite"
    raw = database.read_bytes()
    assert raw.startswith(b"SQLite format 3\x00")
    assert hashlib.sha256(raw).hexdigest() == next(
        item["sha256"] for item in sqlite_inventory["files"] if item["path"] == "schema/db.sqlite")
    with sqlite3.connect(database) as connection:
        assert connection.execute("select name from sqlite_master where type='table'").fetchone() == ("users",)


def test_synthetic_project_inputs_are_exact_and_isolated(tmp_path: Path):
    first = subjects.materialize("scenario-08", tmp_path / "eight")
    second = subjects.materialize("scenario-09", tmp_path / "nine")
    project_skill = (tmp_path / "eight/.apgr/skills/go-language-profile/SKILL.md").read_bytes()
    override = (tmp_path / "nine/.apgr/config.toml").read_bytes()
    assert b"Synthetic project Go profile" in project_skill
    assert b'"apgr:go-language-profile" = "project:go-language-profile"' in override
    assert first["tree_sha256"] != second["tree_sha256"]


def test_scenario15_contains_user_visible_component_contract(tmp_path: Path):
    subjects.materialize("scenario-15", tmp_path / "fifteen")
    requirements = (tmp_path / "fifteen/frontend/README.md").read_text()
    assert "keyboard movement" in requirements
    assert "explicit empty state" in requirements
    assert "Review the deployment checklist" in requirements


def test_inventory_fails_closed_after_subject_drift(tmp_path: Path):
    root = tmp_path / "subject"
    retained = subjects.materialize("scenario-11", root)
    path = root / "pkg/api/client.go"
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(subjects.SubjectError, match="changed"):
        subjects.verify_inventory(root, retained)


def test_materialize_refuses_existing_root_and_manifest_drift(tmp_path: Path):
    root = tmp_path / "subject"
    subjects.materialize("scenario-12", root)
    with pytest.raises(FileExistsError):
        subjects.materialize("scenario-12", root)

    copied_corpus = tmp_path / "corpus"
    (copied_corpus / "subjects").mkdir(parents=True)
    manifest = subjects.SUBJECT_ROOT / "manifest.json"
    copied = copied_corpus / "subjects/manifest.json"
    shutil.copy2(manifest, copied)
    copied.write_bytes(copied.read_bytes().replace(
        b"apg.h-subject-manifest/v1", b"wrong-manifest-v1"))
    with pytest.raises(subjects.SubjectError, match="schema"):
        subjects.load_manifest(corpus_root=copied_corpus)
