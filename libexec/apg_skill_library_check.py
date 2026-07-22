"""Read-only mechanical validation for the APG skill library."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Sequence


COMMAND_NAME = "apg-check-skill-library"
CURRENT_CATALOG_HEADING = "## Current development catalog"
LEGACY_CATALOG_HEADING = "## APG v0.1 catalog"
CATALOG_HEADINGS = frozenset(
    {CURRENT_CATALOG_HEADING, LEGACY_CATALOG_HEADING}
)
CATALOG_HEADER = "| Skill | Trigger boundary | Maturity |"
CATALOG_SEPARATOR = "| --- | --- | --- |"
MATURITY_VALUES = frozenset(
    {"bootstrap", "provisional", "evaluated", "stable", "deprecated"}
)
REQUIRED_H2S = (
    "Core principle",
    "Do not use",
    "Procedure",
    "Project-owned parameters",
    "Evidence and completion",
    "Stop or escalate",
    "Common mistakes",
)
SUPPORT_DIRECTORIES = frozenset({"scripts", "references", "assets", "agents"})
SKILL_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
TOP_LEVEL_KEY = re.compile(r"(?P<key>[A-Za-z0-9_-]+):")
OPENING_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
INLINE_LINK = re.compile(
    r"(?<!\\)!?\[[^\]\n]*\]\((?:<(?P<angle>[^>\n]+)>|"
    r"(?P<plain>[^\s()<>\n]+))\)"
)
CATALOG_ROW = re.compile(
    r"^\| \[`(?P<name>[^`|]+)`\]\((?P<target>[^\s()|]+)\) "
    r"\| (?P<trigger>[^|]*?) \| `(?P<maturity>[^`|]+)` \|$"
)
EXTERNAL_DESTINATION = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


@dataclass(frozen=True)
class ScalarField:
    """One accepted top-level required frontmatter scalar."""

    key: str
    value: str
    line: int


@dataclass(frozen=True)
class FrontmatterResult:
    """Lexical result for APG's required-field frontmatter subset."""

    starts_at_byte_one: bool
    terminated: bool
    body_start_line: int
    fields: tuple[ScalarField, ...]
    invalid_required: tuple[tuple[str, int], ...]
    invalid_top_level_keys: tuple[int, ...]

    def values(self, key: str) -> tuple[str, ...]:
        return tuple(field.value for field in self.fields if field.key == key)

    def line_for(self, key: str) -> int | None:
        for field in self.fields:
            if field.key == key:
                return field.line
        return None


@dataclass(frozen=True)
class LinkToken:
    """One accepted literal inline Markdown destination."""

    destination: str
    line: int


@dataclass(frozen=True)
class CatalogRow:
    """One row in the adopted APG catalog table."""

    name: str
    target: str
    trigger: str
    maturity: str
    line: int


@dataclass(frozen=True)
class CatalogResult:
    """Lexical result for the exact APG catalog contract."""

    heading_count: int
    header_valid: bool
    rows: tuple[CatalogRow, ...]
    malformed_lines: tuple[int, ...]


@dataclass(frozen=True)
class Diagnostic:
    """One deterministic noncompliance diagnostic."""

    code: str
    path: str
    invariant: str
    message: str
    action: str
    line: int | None = None
    column: int | None = None

    def json_value(self) -> dict[str, object]:
        return {
            "action": self.action,
            "code": self.code,
            "column": self.column,
            "invariant": self.invariant,
            "line": self.line,
            "message": self.message,
            "path": self.path,
        }


@dataclass(frozen=True)
class CheckResult:
    """Complete checker result and bounded counts."""

    diagnostics: tuple[Diagnostic, ...]
    canonical_skills: int
    catalog_rows: int
    projections: int

    @property
    def passed(self) -> bool:
        return not self.diagnostics


def valid_skill_name(value: str) -> bool:
    """Return whether value satisfies APG's pinned skill-name grammar."""

    return 1 <= len(value) <= 64 and SKILL_NAME.fullmatch(value) is not None


def parse_frontmatter(data: bytes) -> FrontmatterResult:
    """Parse only APG's top-level plain-scalar required fields."""

    starts = data.startswith(b"---\n") or data.startswith(b"---\r\n")
    text = data.decode("utf-8")
    lines = text.splitlines()
    terminated = False
    end = len(lines)
    body_start_line = 1
    if starts:
        body_start_line = len(lines) + 1
        for index, line in enumerate(lines[1:], start=1):
            if line == "---":
                terminated = True
                end = index
                body_start_line = index + 2
                break

    fields: list[ScalarField] = []
    invalid: list[tuple[str, int]] = []
    invalid_top_level_keys: list[int] = []
    scan_start = 1 if starts else 0
    for index, line in enumerate(lines[scan_start:end], start=scan_start + 1):
        if not line or line[0].isspace() or line.startswith("#"):
            continue
        key_match = TOP_LEVEL_KEY.match(line)
        if key_match is None:
            explicit_key = line == "?" or line.startswith(("? ", "?\t"))
            closing = (
                line.rfind("]")
                if line.startswith("[")
                else line.rfind("}") if line.startswith("{") else -1
            )
            flow_key = (
                closing >= 0
                and line[closing + 1 :].lstrip(" \t").startswith(":")
            )
            mapping_like = flow_key or (
                ":" in line
                and not line.startswith(("- ", "-\t", "[", "{"))
            )
            if explicit_key or mapping_like:
                invalid_top_level_keys.append(index)
            continue
        key = key_match.group("key")
        if key not in ("name", "description"):
            continue
        expected_prefix = f"{key}: "
        value = line[len(expected_prefix) :] if line.startswith(expected_prefix) else ""
        invalid_value = (
            not line.startswith(expected_prefix)
            or not value
            or value[0] in {'"', "'", "|", ">"}
            or " #" in value
            or "\t" in value
            or any(ord(character) < 32 for character in value)
        )
        if invalid_value:
            invalid.append((key, index))
        else:
            fields.append(ScalarField(key, value, index))
    return FrontmatterResult(
        starts,
        terminated,
        body_start_line,
        tuple(fields),
        tuple(invalid),
        tuple(invalid_top_level_keys),
    )


def markdown_body(text: str, frontmatter: FrontmatterResult) -> str:
    """Return only the Markdown body while preserving source line numbers."""

    if not frontmatter.starts_at_byte_one or not frontmatter.terminated:
        return ""
    lines = text.splitlines()
    body_index = frontmatter.body_start_line - 1
    return ("\n" * body_index) + "\n".join(lines[body_index:])


def visible_lines(text: str) -> tuple[tuple[int, str], ...]:
    """Return nonempty lines outside backtick and tilde fenced code."""

    visible: list[tuple[int, str]] = []
    fence_character: str | None = None
    fence_length = 0
    for line_number, line in enumerate(text.splitlines(), start=1):
        if fence_character is None:
            match = OPENING_FENCE.match(line)
        else:
            match = re.fullmatch(
                rf" {{0,3}}{re.escape(fence_character)}"
                rf"{{{fence_length},}}[ \t]*",
                line,
            )
        if match is not None:
            if fence_character is not None:
                fence_character = None
                fence_length = 0
                continue
            marker = match.group(1)
            fence_character = marker[0]
            fence_length = len(marker)
            continue
        if fence_character is None and line.strip():
            visible.append((line_number, line))
    return tuple(visible)


def inline_links(text: str) -> tuple[LinkToken, ...]:
    """Return accepted same-line literal links and images outside fences."""

    tokens: list[LinkToken] = []
    for line_number, line in visible_lines(text):
        for match in INLINE_LINK.finditer(line):
            destination = match.group("angle") or match.group("plain")
            tokens.append(LinkToken(destination, line_number))
    return tuple(tokens)


def parse_catalog(text: str) -> CatalogResult:
    """Parse the one exact catalog table outside fenced code."""

    lines = visible_lines(text)
    heading_indexes = [
        index for index, (_, line) in enumerate(lines) if line in CATALOG_HEADINGS
    ]
    if len(heading_indexes) != 1:
        return CatalogResult(len(heading_indexes), False, (), ())

    start = heading_indexes[0] + 1
    if start + 1 >= len(lines):
        return CatalogResult(1, False, (), ())
    header_valid = (
        lines[start][1] == CATALOG_HEADER
        and lines[start + 1][1] == CATALOG_SEPARATOR
    )
    if not header_valid:
        return CatalogResult(1, False, (), ())

    rows: list[CatalogRow] = []
    malformed: list[int] = []
    for line_number, line in lines[start + 2 :]:
        if not line.startswith("|"):
            break
        match = CATALOG_ROW.fullmatch(line)
        if match is None:
            malformed.append(line_number)
            continue
        rows.append(
            CatalogRow(
                match.group("name"),
                match.group("target"),
                match.group("trigger"),
                match.group("maturity"),
                line_number,
            )
        )
    return CatalogResult(1, True, tuple(rows), tuple(malformed))


def _relative(path: Path, root: Path) -> str:
    try:
        value = path.relative_to(root).as_posix()
    except ValueError:
        return "."
    return value or "."


def _ordinary_directory(path: Path) -> bool:
    try:
        return path.is_dir() and not path.is_symlink()
    except OSError:
        return False


def _ordinary_file(path: Path) -> bool:
    try:
        return stat.S_ISREG(path.lstat().st_mode) and not path.is_symlink()
    except OSError:
        return False


def _contained(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _diagnostic(
    diagnostics: list[Diagnostic],
    code: str,
    path: str,
    invariant: str,
    message: str,
    action: str,
    line: int | None = None,
) -> None:
    diagnostics.append(
        Diagnostic(code, path, invariant, message, action, line=line, column=1 if line else None)
    )


def _read_utf8(
    path: Path,
    relative: str,
    diagnostics: list[Diagnostic],
) -> tuple[bytes, str] | None:
    try:
        data = path.read_bytes()
    except OSError:
        _diagnostic(
            diagnostics,
            "APG005",
            relative,
            "skill-file-readable",
            "required file could not be read",
            "restore an ordinary readable file and rerun the checker",
        )
        return None
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        _diagnostic(
            diagnostics,
            "APG006",
            relative,
            "utf8-text",
            "file is not valid UTF-8",
            "encode the file as valid UTF-8 and rerun the checker",
        )
        return None
    return data, text


def _check_frontmatter_and_body(
    leaf: Path,
    skill_file: Path,
    relative: str,
    data: bytes,
    text: str,
    diagnostics: list[Diagnostic],
    declared: list[tuple[str, str]],
) -> str:
    parsed = parse_frontmatter(data)
    if not parsed.starts_at_byte_one:
        _diagnostic(
            diagnostics,
            "APG007",
            relative,
            "frontmatter-byte-one",
            "frontmatter does not begin with --- at byte one",
            "move the opening delimiter to byte one without a byte-order mark",
            1,
        )
    if not parsed.terminated:
        _diagnostic(
            diagnostics,
            "APG008",
            relative,
            "frontmatter-closure",
            "frontmatter has no exact closing --- delimiter",
            "add the closing delimiter before the Markdown body",
        )

    invalid_keys = {key for key, _ in parsed.invalid_required}
    for line in parsed.invalid_top_level_keys:
        _diagnostic(
            diagnostics,
            "APG035",
            relative,
            "top-level-frontmatter-key-grammar",
            "top-level frontmatter key does not match the accepted APG "
            "plain-key grammar",
            "use a column-zero key containing only ASCII letters, digits, "
            "underscores, or hyphens followed immediately by a colon",
            line,
        )
    for key, line in parsed.invalid_required:
        _diagnostic(
            diagnostics,
            "APG010",
            relative,
            "required-plain-scalar",
            f"{key} is not an accepted top-level unquoted plain scalar",
            f"write {key} as one unquoted 'key: value' line without a comment",
            line,
        )
    for key in ("name", "description"):
        values = parsed.values(key)
        occurrence_count = len(values) + sum(
            1 for invalid_key, _ in parsed.invalid_required if invalid_key == key
        )
        if occurrence_count != 1:
            _diagnostic(
                diagnostics,
                "APG009",
                relative,
                "required-frontmatter-key",
                f"{key} occurs {occurrence_count} times; exactly one is required",
                f"retain exactly one accepted top-level {key} scalar",
            )

    names = parsed.values("name")
    if len(names) == 1 and "name" not in invalid_keys:
        name = names[0]
        line = parsed.line_for("name")
        declared.append((name, relative))
        if not valid_skill_name(name):
            _diagnostic(
                diagnostics,
                "APG011",
                relative,
                "skill-name-grammar",
                "name does not satisfy the accepted APG grammar",
                "use 1-64 lowercase ASCII letters, digits, and single internal hyphens",
                line,
            )
        if name != leaf.name:
            _diagnostic(
                diagnostics,
                "APG012",
                relative,
                "name-directory-agreement",
                "frontmatter name does not match the canonical directory",
                "make the name scalar and directory basename identical",
                line,
            )

    descriptions = parsed.values("description")
    if len(descriptions) == 1 and "description" not in invalid_keys:
        description = descriptions[0]
        if not description.startswith("Use when ") or len(description) > 1024:
            _diagnostic(
                diagnostics,
                "APG014",
                relative,
                "trigger-oriented-description",
                "description must begin with 'Use when ' and contain at most 1024 characters",
                "write one bounded trigger-oriented description",
                parsed.line_for("description"),
            )

    body = markdown_body(text, parsed)
    lines = visible_lines(body)
    h1_count = sum(1 for _, line in lines if re.fullmatch(r"#\s+\S.*", line))
    if h1_count != 1:
        _diagnostic(
            diagnostics,
            "APG015",
            relative,
            "single-h1",
            f"skill body contains {h1_count} H1 headings; exactly one is required",
            "retain one descriptive H1 outside fenced code",
        )
    for heading in REQUIRED_H2S:
        count = sum(1 for _, line in lines if line == f"## {heading}")
        if count != 1:
            _diagnostic(
                diagnostics,
                "APG016",
                relative,
                "required-h2-owner",
                f"heading '## {heading}' occurs {count} times; exactly one is required",
                f"retain exactly one '## {heading}' heading outside fenced code",
            )
    return body


def _check_local_links(
    leaf: Path,
    markdown: Path,
    text: str,
    root: Path,
    diagnostics: list[Diagnostic],
) -> None:
    relative = _relative(markdown, root)
    try:
        physical_leaf = leaf.resolve(strict=True)
    except OSError:
        return
    for token in inline_links(text):
        destination = token.destination
        if destination.startswith("#") or destination.startswith("//"):
            continue
        if EXTERNAL_DESTINATION.match(destination):
            continue
        local = destination.split("#", 1)[0]
        if not local:
            continue
        candidate = markdown.parent / local
        try:
            resolved = candidate.resolve(strict=True)
        except (OSError, RuntimeError):
            _diagnostic(
                diagnostics,
                "APG021",
                relative,
                "skill-local-link",
                f"local destination does not resolve: {destination!r}",
                "restore the target or correct the literal relative destination",
                token.line,
            )
            continue
        if not _contained(resolved, physical_leaf):
            _diagnostic(
                diagnostics,
                "APG021",
                relative,
                "skill-local-link",
                f"local destination escapes the owning skill: {destination!r}",
                "point the link to an existing path inside the owning skill",
                token.line,
            )


def _check_leaf(
    root: Path,
    leaf: Path,
    diagnostics: list[Diagnostic],
    declared: list[tuple[str, str]],
) -> None:
    leaf_relative = _relative(leaf, root)
    skill_file = leaf / "SKILL.md"
    skill_relative = _relative(skill_file, root)
    if not _ordinary_file(skill_file):
        _diagnostic(
            diagnostics,
            "APG005",
            skill_relative,
            "skill-file-regular",
            "required SKILL.md is missing, a symlink, or not a regular file",
            "restore one ordinary readable SKILL.md in the canonical leaf",
        )
        return

    loaded = _read_utf8(skill_file, skill_relative, diagnostics)
    if loaded is not None:
        data, text = loaded
        body = _check_frontmatter_and_body(
            leaf, skill_file, skill_relative, data, text, diagnostics, declared
        )
        _check_local_links(leaf, skill_file, body, root, diagnostics)

    try:
        entries = sorted(leaf.iterdir(), key=lambda item: item.name)
    except OSError:
        entries = []
    for entry in entries:
        if entry.name == "SKILL.md":
            continue
        entry_relative = _relative(entry, root)
        if entry.name not in SUPPORT_DIRECTORIES:
            _diagnostic(
                diagnostics,
                "APG017",
                entry_relative,
                "accepted-leaf-entry",
                "top-level skill entry is outside the adopted APG leaf shape",
                "remove it or authorize and document an APG leaf-shape change",
            )
            continue
        if not _ordinary_directory(entry):
            _diagnostic(
                diagnostics,
                "APG018",
                entry_relative,
                "support-directory-type",
                "optional support entry is not an ordinary directory",
                "replace it with an ordinary contained directory or remove it",
            )
            continue
        try:
            support_entries = sorted(entry.rglob("*"), key=lambda item: item.as_posix())
        except OSError:
            support_entries = []
        if not support_entries:
            _diagnostic(
                diagnostics,
                "APG019",
                entry_relative,
                "support-directory-nonempty",
                "optional support directory is empty",
                "remove the directory or add the justified support artifact",
            )
            continue
        try:
            physical_leaf = leaf.resolve(strict=True)
        except OSError:
            physical_leaf = leaf
        for support in support_entries:
            support_relative = _relative(support, root)
            if support.is_symlink():
                try:
                    target = support.resolve(strict=True)
                except (OSError, RuntimeError):
                    target = None
                if target is None or not _contained(target, physical_leaf):
                    _diagnostic(
                        diagnostics,
                        "APG020",
                        support_relative,
                        "support-link-containment",
                        "support symlink is broken or escapes the owning skill",
                        "remove it or retarget it to an existing path inside the skill",
                    )
                elif (
                    support.suffix.lower() == ".md"
                    and target.is_file()
                ):
                    loaded_support = _read_utf8(
                        support, support_relative, diagnostics
                    )
                    if loaded_support is not None:
                        _check_local_links(
                            leaf,
                            support,
                            loaded_support[1],
                            root,
                            diagnostics,
                        )
                continue
            if support.is_file() and support.suffix.lower() == ".md":
                loaded_support = _read_utf8(support, support_relative, diagnostics)
                if loaded_support is not None:
                    _check_local_links(
                        leaf,
                        support,
                        loaded_support[1],
                        root,
                        diagnostics,
                    )


def _check_catalog(
    root: Path,
    readme: Path,
    canonical_names: set[str],
    diagnostics: list[Diagnostic],
) -> tuple[CatalogRow, ...]:
    relative = _relative(readme, root)
    if not _ordinary_file(readme):
        _diagnostic(
            diagnostics,
            "APG002",
            relative,
            "catalog-file-regular",
            "skills/README.md is missing, a symlink, or not a regular file",
            "restore the ordinary catalog file",
        )
        return ()
    loaded = _read_utf8(readme, relative, diagnostics)
    if loaded is None:
        return ()
    parsed = parse_catalog(loaded[1])
    if parsed.heading_count != 1:
        _diagnostic(
            diagnostics,
            "APG022",
            relative,
            "single-catalog-heading",
            f"exact APG catalog heading occurs {parsed.heading_count} times",
            "retain one exact current or legacy APG catalog heading outside "
            "fenced code",
        )
    if not parsed.header_valid or parsed.malformed_lines:
        _diagnostic(
            diagnostics,
            "APG023",
            relative,
            "catalog-table-shape",
            "catalog header, separator, or row does not match the adopted table grammar",
            "restore the exact three-column catalog contract",
            parsed.malformed_lines[0] if parsed.malformed_lines else None,
        )
    counts = Counter(row.name for row in parsed.rows)
    for name, count in sorted(counts.items()):
        if count > 1:
            _diagnostic(
                diagnostics,
                "APG024",
                relative,
                "catalog-row-unique",
                f"catalog contains {count} rows for {name!r}",
                "retain exactly one catalog row per canonical skill",
            )
    catalog_names = set(counts)
    if catalog_names != canonical_names:
        _diagnostic(
            diagnostics,
            "APG025",
            relative,
            "catalog-canonical-bijection",
            "catalog skill names do not equal the canonical skill directories",
            "add missing rows and remove unknown rows until the sets match",
        )
    for row in parsed.rows:
        expected = f"{row.name}/SKILL.md"
        target = readme.parent / row.target
        if row.target != expected or not _ordinary_file(target):
            _diagnostic(
                diagnostics,
                "APG026",
                relative,
                "catalog-canonical-link",
                f"catalog link for {row.name!r} is not the matching canonical SKILL.md",
                f"set the target to {expected!r}",
                row.line,
            )
        if not row.trigger.strip():
            _diagnostic(
                diagnostics,
                "APG027",
                relative,
                "catalog-trigger-cell",
                f"catalog trigger boundary is empty for {row.name!r}",
                "record a nonempty trigger-boundary summary",
                row.line,
            )
        if row.maturity not in MATURITY_VALUES:
            _diagnostic(
                diagnostics,
                "APG028",
                relative,
                "catalog-maturity-vocabulary",
                f"catalog maturity {row.maturity!r} is not recognized",
                "use bootstrap, provisional, evaluated, stable, or deprecated",
                row.line,
            )
    return parsed.rows


def _check_projection(
    root: Path,
    canonical: dict[str, Path],
    diagnostics: list[Diagnostic],
) -> int:
    agents = root / ".agents"
    projection = agents / "skills"
    if not _ordinary_directory(agents) or not _ordinary_directory(projection):
        _diagnostic(
            diagnostics,
            "APG029",
            ".agents/skills",
            "projection-root-real",
            ".agents and .agents/skills must be ordinary directories",
            "restore the checked-in ordinary projection directories",
        )
        return 0
    try:
        entries = {entry.name: entry for entry in projection.iterdir()}
    except OSError:
        entries = {}
    expected_names = set(canonical)
    actual_names = set(entries)
    if actual_names != expected_names:
        _diagnostic(
            diagnostics,
            "APG030",
            ".agents/skills",
            "projection-canonical-bijection",
            "projection names do not equal the canonical skill directories",
            "add missing projections and remove extra entries",
        )
    try:
        physical_root = root.resolve(strict=True)
        physical_skills = (root / "skills").resolve(strict=True)
    except OSError:
        physical_root = root
        physical_skills = root / "skills"
    for name in sorted(expected_names & actual_names):
        link = entries[name]
        relative = _relative(link, root)
        if not link.is_symlink():
            _diagnostic(
                diagnostics,
                "APG031",
                relative,
                "projection-entry-symlink",
                "projection entry is not a symbolic link",
                "replace it with the exact relative canonical symlink",
            )
            continue
        try:
            raw_target = os.readlink(link)
        except OSError:
            raw_target = ""
        expected_raw = f"../../skills/{name}"
        if raw_target != expected_raw:
            _diagnostic(
                diagnostics,
                "APG032",
                relative,
                "projection-raw-target",
                f"raw target differs from {expected_raw!r}",
                f"recreate the link with raw target {expected_raw!r}",
            )
        try:
            resolved = link.resolve(strict=True)
            expected = canonical[name].resolve(strict=True)
        except (OSError, RuntimeError):
            _diagnostic(
                diagnostics,
                "APG033",
                relative,
                "projection-resolution",
                "projection is broken, cyclic, or cannot resolve",
                "restore the exact contained link to the canonical directory",
            )
            continue
        if (
            resolved != expected
            or not _contained(resolved, physical_skills)
            or not _contained(resolved, physical_root)
        ):
            _diagnostic(
                diagnostics,
                "APG033",
                relative,
                "projection-resolution",
                "projection does not resolve to the matching contained canonical leaf",
                "restore the exact contained link to the canonical directory",
            )
            continue
        projected_skill = link / "SKILL.md"
        canonical_skill = canonical[name] / "SKILL.md"
        try:
            projected_file = projected_skill.resolve(strict=True)
            canonical_file = canonical_skill.resolve(strict=True)
        except (OSError, RuntimeError):
            projected_file = None
            canonical_file = None
        if (
            projected_file is None
            or projected_file != canonical_file
            or not _ordinary_file(canonical_skill)
        ):
            _diagnostic(
                diagnostics,
                "APG034",
                _relative(projected_skill, root),
                "projected-skill-identity",
                "projected SKILL.md does not resolve to the canonical regular file",
                "restore the canonical file and exact projection",
            )
    return len(entries)


def check_library(root: Path) -> CheckResult:
    """Validate root without mutation and return all deterministic diagnostics."""

    diagnostics: list[Diagnostic] = []
    root = Path(root)
    skills = root / "skills"
    canonical: dict[str, Path] = {}
    if not _ordinary_directory(skills):
        _diagnostic(
            diagnostics,
            "APG001",
            "skills",
            "skills-root-real",
            "skills is missing, a symlink, or not an ordinary directory",
            "restore the repository-owned ordinary skills directory",
        )
    else:
        try:
            entries = sorted(skills.iterdir(), key=lambda item: item.name)
        except OSError:
            entries = []
        for entry in entries:
            if entry.name == "README.md":
                continue
            if entry.is_dir():
                canonical[entry.name] = entry
                if entry.is_symlink():
                    _diagnostic(
                        diagnostics,
                        "APG004",
                        _relative(entry, root),
                        "canonical-directory-real",
                        "canonical skill directory is a symbolic link",
                        "restore an ordinary direct-child canonical directory",
                    )
                continue
            _diagnostic(
                diagnostics,
                "APG003",
                _relative(entry, root),
                "skills-root-entry",
                "unexpected non-directory entry exists under skills",
                "remove it or move its content into an authorized owner",
            )

    declared: list[tuple[str, str]] = []
    for name, leaf in sorted(canonical.items()):
        if not leaf.is_symlink():
            _check_leaf(root, leaf, diagnostics, declared)
    for name, count in sorted(Counter(value for value, _ in declared).items()):
        if count > 1:
            for declared_name, relative in declared:
                if declared_name == name:
                    _diagnostic(
                        diagnostics,
                        "APG013",
                        relative,
                        "unique-frontmatter-name",
                        f"frontmatter name {name!r} is declared by {count} leaves",
                        "give every canonical leaf one unique matching name",
                    )

    rows = _check_catalog(
        root, skills / "README.md", set(canonical), diagnostics
    )
    projections = _check_projection(root, canonical, diagnostics)
    ordered = tuple(
        sorted(
            diagnostics,
            key=lambda item: (
                item.path,
                item.line or 0,
                item.column or 0,
                item.code,
                item.message,
            ),
        )
    )
    return CheckResult(ordered, len(canonical), len(rows), projections)


def _summary(result: CheckResult) -> dict[str, int]:
    return {
        "canonical_skills": result.canonical_skills,
        "catalog_rows": result.catalog_rows,
        "projections": result.projections,
    }


def render_json(result: CheckResult) -> str:
    """Render deterministic schema-versioned JSON with one terminal newline."""

    payload = {
        "diagnostics": [item.json_value() for item in result.diagnostics],
        "schema_version": 1,
        "status": "pass" if result.passed else "fail",
        "summary": _summary(result),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"


def render_text(result: CheckResult) -> str:
    """Render deterministic human-readable output with safe actions."""

    counts = (
        f"{result.canonical_skills} canonical skills, "
        f"{result.catalog_rows} catalog rows, {result.projections} projections"
    )
    if result.passed:
        return f"PASS APG skill library: {counts}\n"
    lines: list[str] = []
    for item in result.diagnostics:
        location = json.dumps(item.path, ensure_ascii=True)[1:-1]
        if item.line is not None:
            location += f":{item.line}"
            if item.column is not None:
                location += f":{item.column}"
        lines.append(
            f"{location} {item.code} {item.invariant}: {item.message}; "
            f"action: {item.action}"
        )
    noun = "diagnostic" if len(result.diagnostics) == 1 else "diagnostics"
    lines.append(
        f"FAIL APG skill library: {len(result.diagnostics)} {noun}, {counts}"
    )
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    """Build the bounded public command surface."""

    parser = argparse.ArgumentParser(
        prog=COMMAND_NAME,
        description=(
            "Validate the adopted mechanical APG skill-library subset without "
            "repair, Git, network access, or third-party modules. Passing does "
            "not prove semantic quality, authority, privacy, provenance, "
            "discovery, maturity, release completeness, or stable behavior."
        ),
    )
    parser.add_argument(
        "--root",
        type=Path,
        help="APG-shaped repository root (default: repository containing command)",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="deterministic output format (default: text)",
    )
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    """Run the checker and return its documented exit status."""

    parser = build_parser()
    options = parser.parse_args(arguments)
    default_root = Path(__file__).resolve(strict=True).parent.parent
    result = check_library(options.root if options.root is not None else default_root)
    output = render_json(result) if options.format == "json" else render_text(result)
    sys.stdout.write(output)
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
