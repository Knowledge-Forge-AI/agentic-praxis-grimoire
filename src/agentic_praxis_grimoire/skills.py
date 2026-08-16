"""Checkout-independent skill metadata and context-footprint measurement."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.resources as package_resources
import json
from pathlib import Path
import sys
from typing import Any


class SkillDiscoveryError(ValueError):
    """Raised when a packaged skill blob cannot be discovered reliably."""


@dataclass(frozen=True)
class SkillMetadata:
    """The discoverable front-matter metadata and identity of one skill blob."""

    name: str
    description: str
    relative_path: str
    blob: bytes
    source_blob_bytes: int | None = None
    source_blob_characters: int | None = None
    source_lines: int | None = None
    source_sha256: str | None = None

    @property
    def bytes(self) -> int:
        """UTF-8 byte count of the discoverable description."""

        return len(self.description.encode("utf-8"))

    @property
    def characters(self) -> int:
        """Unicode character count of the discoverable description."""

        return len(self.description)

    @property
    def blob_bytes(self) -> int:
        return self.source_blob_bytes if self.source_blob_bytes is not None else len(self.blob)

    @property
    def blob_characters(self) -> int:
        if self.source_blob_characters is not None:
            return self.source_blob_characters
        return len(self.blob.decode("utf-8"))

    @property
    def lines(self) -> int:
        return self.source_lines if self.source_lines is not None else len(self.blob.splitlines())

    @property
    def sha256(self) -> str:
        return self.source_sha256 or hashlib.sha256(self.blob).hexdigest()

    def as_dict(self) -> dict[str, Any]:
        """Return a stable machine-readable metadata row."""

        return {
            "name": self.name,
            "description": self.description,
            "path": self.relative_path,
            "bytes": self.bytes,
            "characters": self.characters,
            "description_bytes": self.bytes,
            "description_characters": self.characters,
            "blob_bytes": self.blob_bytes,
            "blob_characters": self.blob_characters,
            "lines": self.lines,
            "sha256": self.sha256,
        }


def _resource_root() -> Any:
    return package_resources.files("agentic_praxis_grimoire").joinpath(
        "resources"
    )


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, member in pairs:
        if key in value:
            raise ValueError(f"duplicate key: {key}")
        value[key] = member
    return value


def _manifest_metadata(root: Any) -> tuple[SkillMetadata, ...]:
    """Read the exact checkout-independent metadata projection."""

    resource = root.joinpath("skill-metadata.json")
    try:
        raw = resource.read_bytes()
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    except (AttributeError, OSError, UnicodeError, ValueError, json.JSONDecodeError) as error:
        raise SkillDiscoveryError("packaged skill metadata manifest is missing or malformed") from error
    if not isinstance(document, dict) or set(document) != {"schema_version", "skills"}:
        raise SkillDiscoveryError("packaged skill metadata manifest has an invalid schema")
    rows = document.get("skills")
    if document.get("schema_version") != 1 or not isinstance(rows, list) or not rows:
        raise SkillDiscoveryError("packaged skill metadata manifest has an invalid schema")
    expected_keys = {
        "name",
        "description",
        "path",
        "source_blob_bytes",
        "source_blob_characters",
        "source_lines",
        "source_sha256",
    }
    entries: list[SkillMetadata] = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != expected_keys:
            raise SkillDiscoveryError("packaged skill metadata row has an invalid schema")
        name = row["name"]
        description = row["description"]
        relative_path = row["path"]
        byte_count = row["source_blob_bytes"]
        character_count = row["source_blob_characters"]
        line_count = row["source_lines"]
        digest = row["source_sha256"]
        if (
            not isinstance(name, str)
            or not name
            or not isinstance(description, str)
            or not description
            or not isinstance(relative_path, str)
            or not relative_path.startswith("skills/")
            or not relative_path.endswith("/SKILL.md")
            or any(part in {"", ".", ".."} for part in Path(relative_path).parts)
            or not isinstance(byte_count, int)
            or byte_count <= 0
            or not isinstance(character_count, int)
            or character_count <= 0
            or not isinstance(line_count, int)
            or line_count <= 0
            or not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise SkillDiscoveryError("packaged skill metadata row has invalid values")
        blob = (
            f"---\nname: {name}\ndescription: {description}\n---\n"
        ).encode("utf-8")
        entries.append(
            SkillMetadata(
                name,
                description,
                relative_path,
                blob,
                byte_count,
                character_count,
                line_count,
                digest,
            )
        )
    paths = [entry.relative_path for entry in entries]
    names = [entry.name for entry in entries]
    if paths != sorted(paths) or len(set(paths)) != len(paths) or len(set(names)) != len(names):
        raise SkillDiscoveryError("packaged skill metadata rows are unsorted or duplicated")
    return tuple(sorted(entries, key=lambda entry: entry.name))


def _canonical_blobs(repository_root: Path) -> dict[str, bytes]:
    skills_root = repository_root / "skills"
    if skills_root.is_symlink() or not skills_root.is_dir():
        raise SkillDiscoveryError("canonical skills directory is missing or unsafe")
    blobs: dict[str, bytes] = {}
    for path in sorted(skills_root.rglob("SKILL.md")):
        if path.is_symlink() or not path.is_file():
            raise SkillDiscoveryError(f"canonical skill resource is unsafe: {path}")
        relative = Path("skills") / path.relative_to(skills_root)
        blobs[relative.as_posix()] = path.read_bytes()
    return blobs


def parse_skill_metadata(relative_path: str, blob: bytes) -> SkillMetadata:
    """Parse the small YAML-like front matter owned by APG skill leaves."""

    try:
        text = blob.decode("utf-8")
    except UnicodeDecodeError as error:
        raise SkillDiscoveryError(f"{relative_path}: metadata is not UTF-8") from error
    lines = text.splitlines()
    if len(lines) < 3 or lines[0] != "---":
        raise SkillDiscoveryError(f"{relative_path}: missing metadata front matter")
    try:
        end = lines.index("---", 1)
    except ValueError as error:
        raise SkillDiscoveryError(
            f"{relative_path}: unterminated metadata front matter"
        ) from error
    values: dict[str, str] = {}
    for line in lines[1:end]:
        key, separator, value = line.partition(":")
        if not separator or not key or not value.startswith(" "):
            raise SkillDiscoveryError(f"{relative_path}: malformed metadata line")
        if key in values:
            raise SkillDiscoveryError(
                f"{relative_path}: duplicate metadata key {key}"
            )
        values[key] = value[1:]
    name = values.get("name", "")
    description = values.get("description", "")
    if not name or not description:
        raise SkillDiscoveryError(f"{relative_path}: name and description are required")
    return SkillMetadata(name, description, relative_path, blob)


def _metadata_from_blobs(blobs: dict[str, bytes]) -> tuple[SkillMetadata, ...]:
    if not blobs:
        raise SkillDiscoveryError("no packaged skill metadata resources")
    entries: list[SkillMetadata] = []
    seen: set[str] = set()
    for relative_path, blob in blobs.items():
        entry = parse_skill_metadata(relative_path, blob)
        if entry.name in seen:
            raise SkillDiscoveryError(
                f"{relative_path}: duplicate skill name {entry.name}"
            )
        seen.add(entry.name)
        entries.append(entry)
    return tuple(sorted(entries, key=lambda entry: entry.name))


def list_skill_metadata() -> tuple[SkillMetadata, ...]:
    """List all installed skill metadata in stable name order."""

    return _manifest_metadata(_resource_root())


def context_footprint_report(
    *,
    blobs: dict[str, bytes] | None = None,
) -> dict[str, Any]:
    """Return deterministic description byte/character measurements.

    When a caller supplies blobs, malformed entries are represented in the
    report rather than omitted. This makes discovery accounting truthful when
    a package resource is damaged or incomplete.
    """

    malformed: list[dict[str, str]] = []
    entries: list[SkillMetadata] = []
    if blobs is None:
        try:
            entries.extend(list_skill_metadata())
        except SkillDiscoveryError as error:
            return {
                "skill_count": 0,
                "discoverable_skill_count": 0,
                "total_bytes": 0,
                "total_characters": 0,
                "total_description_bytes": 0,
                "total_description_characters": 0,
                "skills": [],
                "malformed": [{"path": "resources/skills", "error": str(error)}],
            }
        source: dict[str, bytes] = {}
    else:
        source = dict(sorted(blobs.items()))
    if blobs is not None and not source:
        malformed.append(
            {
                "path": "resources/skills",
                "error": "no packaged skill metadata resources",
            }
        )
    seen: set[str] = set()
    for relative_path, blob in source.items():
        try:
            entry = parse_skill_metadata(relative_path, blob)
            if entry.name in seen:
                raise SkillDiscoveryError(f"{relative_path}: duplicate skill name {entry.name}")
            seen.add(entry.name)
        except SkillDiscoveryError as error:
            malformed.append({"path": relative_path, "error": str(error)})
            continue
        entries.append(entry)
    rows = [
        entry.as_dict()
        for entry in sorted(entries, key=lambda item: (-item.bytes, item.name))
    ]
    total_bytes = sum(entry.bytes for entry in entries)
    total_characters = sum(entry.characters for entry in entries)
    return {
        "skill_count": len(entries),
        "discoverable_skill_count": len(entries),
        "total_bytes": total_bytes,
        "total_characters": total_characters,
        "total_description_bytes": total_bytes,
        "total_description_characters": total_characters,
        "skills": rows,
        "malformed": malformed,
    }


def validate_canonical_resources(
    repository_root: str | Path,
    *,
    resource_root: Any | None = None,
) -> tuple[str, ...]:
    """Return exact canonical/package resource sync diagnostics.

    The comparison intentionally checks relative path order, complete UTF-8
    content, SHA-256, line count, and blob length. It is callable by
    repository tests while installed consumers remain checkout-independent.
    """

    root = Path(repository_root).resolve()
    try:
        canonical = _canonical_blobs(root)
    except (OSError, SkillDiscoveryError) as error:
        return (str(error),)
    try:
        packaged_entries = _manifest_metadata(
            _resource_root() if resource_root is None else resource_root
        )
    except (OSError, SkillDiscoveryError) as error:
        return (str(error),)
    packaged = {entry.relative_path: entry for entry in packaged_entries}
    diagnostics: list[str] = []
    canonical_paths = tuple(canonical)
    packaged_paths = tuple(packaged)
    if canonical_paths != packaged_paths:
        diagnostics.append(
            "resource path/order mismatch: "
            f"canonical={canonical_paths!r} packaged={packaged_paths!r}"
        )
    for relative_path in sorted(set(canonical) | set(packaged)):
        expected = canonical.get(relative_path)
        actual_metadata = packaged.get(relative_path)
        if expected is None or actual_metadata is None:
            continue
        try:
            expected_metadata = parse_skill_metadata(relative_path, expected)
        except SkillDiscoveryError as error:
            diagnostics.append(str(error))
            continue
        if expected_metadata.as_dict() != actual_metadata.as_dict():
            diagnostics.append(f"{relative_path}: metadata mismatch")
    return tuple(diagnostics)


def assert_canonical_resource_sync(
    repository_root: str | Path,
    *,
    resource_root: Any | None = None,
) -> None:
    """Raise an assertion suitable for a repository synchronization gate."""

    diagnostics = validate_canonical_resources(
        repository_root, resource_root=resource_root
    )
    if diagnostics:
        message = "canonical skill resources are out of sync:\n" + "\n".join(
            diagnostics
        )
        raise AssertionError(message)


validate_resource_sync = validate_canonical_resources
assert_resource_sync = assert_canonical_resource_sync


def main(action: str, arguments: list[str] | None = None) -> int:
    """Serve the checkout-independent ``apgr skills`` consumer operations."""

    values = list(arguments or [])
    try:
        if values.count("--json") > 1 or values.count("--format") > 1:
            raise SkillDiscoveryError("output format may be specified only once")
        if "--json" in values and "--format" in values:
            raise SkillDiscoveryError("--json and --format may not be combined")
        output_json = "--json" in values
        if "--format" in values:
            format_index = values.index("--format")
            if format_index + 1 >= len(values):
                raise SkillDiscoveryError("--format requires a value")
            format_value = values[format_index + 1]
            if format_value not in {"json", "text"}:
                raise SkillDiscoveryError("--format must be json or text")
            output_json = format_value == "json"
    except SkillDiscoveryError as error:
        print(f"apgr skills: {error}", file=sys.stderr)
        return 2
    if action == "list":
        try:
            metadata = list_skill_metadata()
        except SkillDiscoveryError as error:
            print(f"apgr skills: {error}", file=sys.stderr)
            return 2
        if output_json:
            print(
                json.dumps(
                    [entry.as_dict() for entry in metadata],
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
        else:
            for entry in metadata:
                print(entry.name)
        return 0
    if action == "context-report":
        report = context_footprint_report()
        if output_json or not values:
            print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        else:
            print(f"discoverable skills: {report['skill_count']}")
            print(f"description bytes: {report['total_bytes']}")
            print(f"description characters: {report['total_characters']}")
            for row in report["skills"]:
                print(f"{row['name']}: {row['bytes']} bytes, {row['characters']} characters")
            if report["malformed"]:
                print("malformed:")
                for item in report["malformed"]:
                    print(f"- {item['path']}: {item['error']}")
        return 0
    print(f"apgr skills: unknown skills operation: {action}", file=sys.stderr)
    return 2


__all__ = [
    "SkillDiscoveryError",
    "SkillMetadata",
    "assert_canonical_resource_sync",
    "assert_resource_sync",
    "context_footprint_report",
    "list_skill_metadata",
    "main",
    "parse_skill_metadata",
    "validate_canonical_resources",
    "validate_resource_sync",
]
