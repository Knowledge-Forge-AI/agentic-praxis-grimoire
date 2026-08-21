"""Unit contracts for installed skill resources and context measurement."""

from __future__ import annotations

import importlib.resources as package_resources
import json
from pathlib import Path
import sys

import pytest

from src.test.apg_test_support import repository_root

from agentic_praxis_grimoire import skills


ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src"))


def test_installed_skill_metadata_is_deterministic_and_complete() -> None:
    metadata = skills.list_skill_metadata()
    assert len(metadata) == 39
    assert [entry.name for entry in metadata] == sorted(entry.name for entry in metadata)
    assert all(entry.description for entry in metadata)


def test_apg88_packaged_context_and_headroom_are_exact() -> None:
    report = skills.context_footprint_report()
    by_name = {entry["name"]: entry for entry in report["skills"]}

    assert report["skill_count"] == 39
    assert report["discoverable_skill_count"] == 39
    assert report["malformed"] == []
    assert report["total_description_bytes"] == 9504
    assert by_name["gomock-test-profile"]["description_bytes"] == 276
    assert by_name["vitest-test-profile"]["description_bytes"] == 293
    assert by_name["jsx-language-profile"]["description_bytes"] == 248
    assert by_name["react-component-profile"]["description_bytes"] == 268
    assert by_name["mdx-profile"]["description_bytes"] == 214
    assert by_name["astro-profile"]["description_bytes"] == 238
    assert report["total_description_bytes"] - 7967 == 1537
    assert 9527 - report["total_description_bytes"] == 23


def test_context_report_counts_exact_utf8_description_bytes_and_characters() -> None:
    report = skills.context_footprint_report()
    assert report["malformed"] == []
    metadata = skills.list_skill_metadata()
    assert report["skill_count"] == len(metadata)
    assert report["total_bytes"] == sum(
        len(entry.description.encode("utf-8")) for entry in metadata
    )
    assert report["total_characters"] == sum(
        len(entry.description) for entry in metadata
    )
    rows = report["skills"]
    assert rows == sorted(rows, key=lambda row: (-row["bytes"], row["name"]))


def test_canonical_resource_sync_checks_exact_repository_blobs() -> None:
    assert skills.validate_canonical_resources(ROOT) == ()


def test_packaged_metadata_manifest_is_bounded_and_source_bound() -> None:
    packaged = (
        package_resources.files("agentic_praxis_grimoire")
        .joinpath("resources", "skill-metadata.json")
        .read_bytes()
    )
    document = json.loads(packaged)

    assert document["schema_version"] == 1
    assert len(document["skills"]) == 39
    paths = [row["path"] for row in document["skills"]]
    assert paths == sorted(paths)
    assert all(len(row["source_sha256"]) == 64 for row in document["skills"])


def test_malformed_metadata_is_reported_without_inventing_a_count() -> None:
    report = skills.context_footprint_report(
        blobs={"broken/SKILL.md": b"---\nname: broken\n"}
    )
    assert report["skill_count"] == 0
    assert report["total_bytes"] == 0
    assert report["total_characters"] == 0
    assert report["malformed"]
    assert "broken/SKILL.md" in report["malformed"][0]["path"]


def test_missing_resource_root_is_reported_as_malformed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(skills, "_resource_root", lambda: Path("missing-resource"))
    report = skills.context_footprint_report()
    assert report["skill_count"] == 0
    assert report["malformed"][0]["path"] == "resources/skills"


def _blob(name: str = "sample", description: str = "description") -> bytes:
    return f"---\nname: {name}\ndescription: {description}\n---\n# Body\n".encode()


def _write_manifest(root: Path, entries: list[tuple[str, bytes]]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    rows = []
    for relative_path, blob in sorted(entries):
        entry = skills.parse_skill_metadata(relative_path, blob)
        rows.append(
            {
                "name": entry.name,
                "description": entry.description,
                "path": relative_path,
                "source_blob_bytes": entry.blob_bytes,
                "source_blob_characters": entry.blob_characters,
                "source_lines": entry.lines,
                "source_sha256": entry.sha256,
            }
        )
    (root / "skill-metadata.json").write_text(
        json.dumps({"schema_version": 1, "skills": rows}), encoding="utf-8"
    )


def test_manifest_parser_rejects_bounded_corruption_classes(tmp_path: Path) -> None:
    manifest = tmp_path / "skill-metadata.json"

    manifest.write_text('{"schema_version":1,"schema_version":1,"skills":[]}')
    with pytest.raises(skills.SkillDiscoveryError, match="missing or malformed"):
        skills._manifest_metadata(tmp_path)

    manifest.write_text(json.dumps({"schema_version": 1, "foreign": []}))
    with pytest.raises(skills.SkillDiscoveryError, match="invalid schema"):
        skills._manifest_metadata(tmp_path)

    manifest.write_text(json.dumps({"schema_version": 1, "skills": []}))
    with pytest.raises(skills.SkillDiscoveryError, match="invalid schema"):
        skills._manifest_metadata(tmp_path)

    manifest.write_text(json.dumps({"schema_version": 1, "skills": [{}]}))
    with pytest.raises(skills.SkillDiscoveryError, match="row has an invalid schema"):
        skills._manifest_metadata(tmp_path)

    _write_manifest(tmp_path, [("skills/sample/SKILL.md", _blob())])
    document = json.loads(manifest.read_text())
    document["skills"][0]["name"] = ""
    manifest.write_text(json.dumps(document))
    with pytest.raises(skills.SkillDiscoveryError, match="row has invalid values"):
        skills._manifest_metadata(tmp_path)

    _write_manifest(
        tmp_path,
        [
            ("skills/alpha/SKILL.md", _blob("alpha")),
            ("skills/beta/SKILL.md", _blob("beta")),
        ],
    )
    document = json.loads(manifest.read_text())
    document["skills"].reverse()
    manifest.write_text(json.dumps(document))
    with pytest.raises(skills.SkillDiscoveryError, match="unsorted or duplicated"):
        skills._manifest_metadata(tmp_path)


def test_metadata_properties_are_exact_for_unicode() -> None:
    entry = skills.parse_skill_metadata("skills/sample/SKILL.md", _blob(description="café"))
    assert entry.name == "sample"
    assert entry.bytes == len("café".encode())
    assert entry.characters == len("café")
    assert entry.blob_bytes == len(entry.blob)
    assert entry.blob_characters == len(entry.blob.decode())
    assert entry.lines == len(entry.blob.splitlines())
    assert len(entry.sha256) == 64
    assert entry.as_dict()["path"] == "skills/sample/SKILL.md"


@pytest.mark.parametrize(
    "blob,diagnostic",
    (
        (b"\xff", "not UTF-8"),
        (b"name: sample\n", "missing metadata"),
        (b"---\nname: sample\ndescription: value\n", "unterminated"),
        (b"---\nbad\n---\n", "malformed"),
        (b"---\nname: one\nname: two\ndescription: d\n---\n", "duplicate"),
        (b"---\nname: sample\n---\n", "required"),
    ),
)
def test_metadata_parser_rejects_each_malformed_class(
    blob: bytes, diagnostic: str
) -> None:
    with pytest.raises(skills.SkillDiscoveryError, match=diagnostic):
        skills.parse_skill_metadata("skills/sample/SKILL.md", blob)


def test_metadata_set_rejects_empty_and_duplicate_names() -> None:
    with pytest.raises(skills.SkillDiscoveryError, match="no packaged"):
        skills._metadata_from_blobs({})
    with pytest.raises(skills.SkillDiscoveryError, match="duplicate skill name"):
        skills._metadata_from_blobs(
            {"skills/one/SKILL.md": _blob(), "skills/two/SKILL.md": _blob()}
        )


def test_context_report_counts_valid_rows_and_reports_invalid_rows() -> None:
    report = skills.context_footprint_report(
        blobs={"skills/good/SKILL.md": _blob(), "skills/bad/SKILL.md": b"bad"}
    )
    assert report["skill_count"] == 1
    assert len(report["malformed"]) == 1


def test_skill_cli_text_and_json_surfaces(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    metadata = (skills.parse_skill_metadata("skills/sample/SKILL.md", _blob()),)
    monkeypatch.setattr(skills, "list_skill_metadata", lambda: metadata)
    assert skills.main("list", []) == 0
    assert capsys.readouterr().out == "sample\n"
    assert skills.main("list", ["--json"]) == 0
    assert '"name": "sample"' in capsys.readouterr().out
    monkeypatch.setattr(
        skills,
        "context_footprint_report",
        lambda: {
            "skill_count": 1,
            "total_bytes": 11,
            "total_characters": 11,
            "skills": [metadata[0].as_dict()],
            "malformed": [{"path": "bad", "error": "broken"}],
        },
    )
    assert skills.main("context-report", ["--format", "text"]) == 0
    output = capsys.readouterr().out
    assert "discoverable skills: 1" in output
    assert "malformed:" in output
    assert skills.main("context-report", []) == 0
    assert '"skill_count": 1' in capsys.readouterr().out


def test_skill_cli_failures_are_bounded(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    assert skills.main("list", ["--format"]) == 2
    assert "requires a value" in capsys.readouterr().err
    assert skills.main("list", ["--json", "--format", "text"]) == 2
    assert "may not be combined" in capsys.readouterr().err
    assert skills.main("list", ["--format", "yaml"]) == 2
    assert "json or text" in capsys.readouterr().err
    monkeypatch.setattr(
        skills,
        "list_skill_metadata",
        lambda: (_ for _ in ()).throw(skills.SkillDiscoveryError("missing")),
    )
    assert skills.main("list", []) == 2
    assert "missing" in capsys.readouterr().err
    assert skills.main("unknown", []) == 2
    assert "unknown skills operation" in capsys.readouterr().err


def test_resource_sync_reports_missing_path_and_complete_content_drift(
    tmp_path: Path,
) -> None:
    assert "missing" in skills.validate_canonical_resources(tmp_path)[0]
    repository = tmp_path / "repository"
    canonical = repository / "skills" / "sample"
    canonical.mkdir(parents=True)
    (canonical / "SKILL.md").write_bytes(_blob())
    packaged = tmp_path / "packaged"
    _write_manifest(packaged, [("skills/other/SKILL.md", _blob("other"))])
    diagnostics = skills.validate_canonical_resources(
        repository, resource_root=packaged
    )
    assert any("path/order mismatch" in item for item in diagnostics)
    _write_manifest(
        packaged,
        [("skills/sample/SKILL.md", _blob(description="changed"))],
    )
    diagnostics = skills.validate_canonical_resources(
        repository, resource_root=packaged
    )
    assert any("metadata mismatch" in item for item in diagnostics)
    with pytest.raises(AssertionError, match="out of sync"):
        skills.assert_canonical_resource_sync(repository, resource_root=packaged)
