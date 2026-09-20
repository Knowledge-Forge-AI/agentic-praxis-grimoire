"""Deterministic stage projection of the APGR-owned Claude standing instructions.

``claude/CLAUDE.md`` stays the authoritative static source, byte for byte. The
sibling ``instruction-fragments-v1.json`` manifest carries classification only:
it names fragments by ``## `` section heading plus an optional exact anchor
line, and every byte of the source belongs to exactly one fragment or section
lead. A projection concatenates the selected fragments in source order without
normalization. The closed manifest schema has no tool, permission, MCP, worker
or path fields, so a projection can only omit instruction text.

This module is pure: it reads nothing and writes nothing. The dispatcher and
the wrapper both call it with the same bytes and must obtain the same result.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA = "apg.claude-instruction-fragments/v1"
PROJECTION_SCHEMA = "apg.claude-instruction-projection/v1"
MANIFEST_NAME = "instruction-fragments-v1.json"
SOURCE_NAME = "CLAUDE.md"
CLASSES = ("planning", "review_verification", "implementation", "closeout")
CAPABILITIES = ("ambient_tools",)
FRAGMENT_KEYS = frozenset({"id", "section", "anchor", "stages", "requires", "invariant", "why"})
MAX_MANIFEST_BYTES = 256 * 1024
MAX_SOURCE_BYTES = 1024 * 1024
BOUNDARY = ("APGR tracked Claude standing-instruction source (claude/CLAUDE.md body; excludes the "
            "launcher header, RTK slice, worker facade prompt and worker-skill notice)")


class ProjectionError(ValueError):
    """A prelaunch projection input failure with a stable static-fallback code."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code


def identity(raw: bytes) -> dict[str, Any]:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _decode(raw: bytes) -> Any:
    def pairs(items):
        keys = [k for k, _ in items]
        if len(keys) != len(set(keys)):
            raise ProjectionError("instruction_manifest_invalid", "duplicate JSON key")
        return dict(items)
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError("constant")))
    except ProjectionError:
        raise
    except (UnicodeDecodeError, ValueError) as error:
        raise ProjectionError("instruction_manifest_invalid", type(error).__name__) from error


def _fragment(row: Any, seen: set[str]) -> dict[str, Any]:
    if not isinstance(row, dict) or set(row) - FRAGMENT_KEYS or not {"id", "section", "why"} <= set(row):
        raise ProjectionError("instruction_manifest_invalid", "fragment keys")
    ident = row["id"]
    if not isinstance(ident, str) or not ident or ident in seen:
        raise ProjectionError("instruction_manifest_invalid", f"duplicate or invalid fragment id {ident!r}")
    seen.add(ident)
    if row["section"] is not None and not isinstance(row["section"], str):
        raise ProjectionError("instruction_manifest_invalid", f"{ident}: section")
    if "anchor" in row and (not isinstance(row["anchor"], str) or not row["anchor"] or "\n" in row["anchor"]):
        raise ProjectionError("instruction_manifest_invalid", f"{ident}: anchor")
    if not isinstance(row["why"], str) or not row["why"]:
        raise ProjectionError("instruction_manifest_invalid", f"{ident}: why")
    invariant = row.get("invariant", False)
    if type(invariant) is not bool:
        raise ProjectionError("instruction_manifest_invalid", f"{ident}: invariant")
    if invariant:
        # Invariant core applies to every stage and capability; it cannot be narrowed.
        if "stages" in row or "requires" in row:
            raise ProjectionError("instruction_manifest_invalid", f"{ident}: invariant fragments declare no stages")
        stages, requires = list(CLASSES), []
    else:
        stages, requires = row.get("stages"), row.get("requires", [])
        if (not isinstance(stages, list) or not stages or len(set(stages)) != len(stages)
                or any(s not in CLASSES for s in stages)):
            raise ProjectionError("instruction_manifest_invalid", f"{ident}: stages")
        if (not isinstance(requires, list) or len(set(requires)) != len(requires)
                or any(r not in CAPABILITIES for r in requires)):
            raise ProjectionError("instruction_manifest_invalid", f"{ident}: requires")
    return {"id": ident, "section": row["section"], "anchor": row.get("anchor"), "invariant": invariant,
            "stages": [s for s in CLASSES if s in stages], "requires": list(requires), "why": row["why"]}


def load_manifest(raw: bytes) -> dict[str, Any]:
    if len(raw) > MAX_MANIFEST_BYTES:
        raise ProjectionError("instruction_manifest_invalid", "manifest exceeds bound")
    value = _decode(raw)
    if not isinstance(value, dict) or set(value) != {"schema", "source", "fragments"} or value["schema"] != SCHEMA:
        raise ProjectionError("instruction_manifest_invalid", "manifest keys or schema")
    source = value["source"]
    if (not isinstance(source, dict) or set(source) != {"path", "bytes", "sha256"} or source["path"] != SOURCE_NAME
            or type(source["bytes"]) is not int or not isinstance(source["sha256"], str)):
        raise ProjectionError("instruction_manifest_invalid", "source identity")
    if not isinstance(value["fragments"], list) or not value["fragments"]:
        raise ProjectionError("instruction_manifest_invalid", "fragments")
    seen: set[str] = set()
    return {"source": dict(source), "fragments": [_fragment(row, seen) for row in value["fragments"]]}


def _sections(text: str) -> list[tuple[str | None, str, list[tuple[int, str]]]]:
    """Fence-aware ``## `` split: (heading, lead, [(offset, line)]) per section.

    The lead is the heading line plus the blank lines that follow it; the
    preamble (``None``) has an empty lead. Offsets index the section content.
    """
    sections: list[tuple[str | None, list[str]]] = [(None, [])]
    fenced = False
    for line in text.splitlines(keepends=True):
        stripped = line.rstrip("\r\n")
        if stripped.startswith("```"):
            fenced = not fenced
        if not fenced and stripped.startswith("## "):
            sections.append((stripped[3:], [line]))
        else:
            sections[-1][1].append(line)
    result = []
    for heading, lines in sections:
        lead_count = 0
        if heading is not None:
            lead_count = 1
            while lead_count < len(lines) and not lines[lead_count].strip():
                lead_count += 1
        lead = "".join(lines[:lead_count])
        rows, offset = [], 0
        for line in lines[lead_count:]:
            rows.append((offset, line))
            offset += len(line)
        result.append((heading, lead, rows))
    return result


def split(source: str, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Return ordered sections, each with its lead and exact fragment bodies."""
    sections = _sections(source)
    headings = [h for h, _, _ in sections]
    if len(set(headings)) != len(headings):
        raise ProjectionError("instruction_manifest_invalid", "duplicate section heading in source")
    by_section: dict[str | None, list[dict[str, Any]]] = {}
    order: list[str | None] = []
    for fragment in manifest["fragments"]:
        if not order or order[-1] != fragment["section"]:
            if fragment["section"] in by_section:
                raise ProjectionError("instruction_manifest_invalid", "fragments out of section order")
            by_section[fragment["section"]] = []
            order.append(fragment["section"])
        by_section[fragment["section"]].append(fragment)
    present = [h for h in headings if h is not None or any(line.strip() for _, line in sections[0][2])]
    if order != present:
        raise ProjectionError("instruction_manifest_invalid", "manifest sections do not tile the source")
    result = []
    for heading, lead, rows in sections:
        if heading not in by_section:
            continue
        fragments = by_section[heading]
        content = "".join(line for _, line in rows)
        starts = [0]
        if fragments[0]["anchor"] is not None:
            raise ProjectionError("instruction_manifest_invalid", f"{fragments[0]['id']}: first fragment has an anchor")
        fenced, located = False, {}
        for offset, line in rows:
            stripped = line.rstrip("\r\n")
            if stripped.startswith("```"):
                fenced = not fenced
            elif not fenced and offset:
                located.setdefault(stripped, []).append(offset)
        for fragment in fragments[1:]:
            matches = located.get(fragment["anchor"] or "", [])
            if fragment["anchor"] is None or len(matches) != 1:
                raise ProjectionError("instruction_manifest_invalid", f"{fragment['id']}: anchor missing or ambiguous")
            if matches[0] <= starts[-1]:
                raise ProjectionError("instruction_manifest_invalid", f"{fragment['id']}: anchors out of order")
            starts.append(matches[0])
        bounds = [*starts, len(content)]
        result.append({"heading": heading, "lead": lead, "fragments": [
            {**fragment, "text": content[bounds[i]:bounds[i + 1]]} for i, fragment in enumerate(fragments)]})
    return result


def selected(fragment: dict[str, Any], classes: list[str], capabilities: dict[str, bool]) -> bool:
    return (bool(set(fragment["stages"]) & set(classes))
            and all(capabilities.get(name) is True for name in fragment["requires"]))


def normalize_selection(classes: Any, capabilities: Any) -> tuple[list[str], dict[str, bool]]:
    if (not isinstance(classes, (list, tuple)) or not classes or any(c not in CLASSES for c in classes)
            or len(set(classes)) != len(classes)):
        raise ProjectionError("instruction_selection_unavailable", "classes")
    if (not isinstance(capabilities, dict) or set(capabilities) != set(CAPABILITIES)
            or any(type(v) is not bool for v in capabilities.values())):
        raise ProjectionError("instruction_selection_unavailable", "capabilities")
    return [c for c in CLASSES if c in classes], {k: capabilities[k] for k in CAPABILITIES}


def project(source_raw: bytes, manifest_raw: bytes, classes: Any, capabilities: Any) -> dict[str, Any]:
    """Render one projection; raises ``ProjectionError`` with a fallback code."""
    classes, capabilities = normalize_selection(classes, capabilities)
    manifest = load_manifest(manifest_raw)
    if len(source_raw) > MAX_SOURCE_BYTES:
        raise ProjectionError("instruction_source_unavailable", "source exceeds bound")
    source_id, manifest_id = identity(source_raw), identity(manifest_raw)
    if {"bytes": manifest["source"]["bytes"], "sha256": manifest["source"]["sha256"]} != source_id:
        raise ProjectionError("instruction_source_changed", "source differs from the reviewed classification")
    try:
        source = source_raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ProjectionError("instruction_source_unavailable", "source is not UTF-8") from error
    sections = split(source, manifest)
    if "".join(s["lead"] + "".join(f["text"] for f in s["fragments"]) for s in sections) != source:
        raise ProjectionError("instruction_manifest_invalid", "fragments do not reproduce the source")
    parts, rows = [], []
    for section in sections:
        chosen = [f for f in section["fragments"] if selected(f, classes, capabilities)]
        if chosen:
            parts.append(section["lead"] + "".join(f["text"] for f in chosen))
        for fragment in section["fragments"]:
            text = fragment["text"].encode("utf-8")
            rows.append({"id": fragment["id"], "section": fragment["section"], "invariant": fragment["invariant"],
                         "stages": fragment["stages"], "requires": fragment["requires"],
                         "selected": fragment in chosen, "why": fragment["why"], **identity(text)})
    body = "".join(parts).encode("utf-8")
    selected_ids = [r["id"] for r in rows if r["selected"]]
    projection_id = hashlib.sha256(json.dumps(
        {"schema": PROJECTION_SCHEMA, "manifest_sha256": manifest_id["sha256"], "source_sha256": source_id["sha256"],
         "classes": classes, "capabilities": capabilities, "selected": selected_ids},
        sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    delta = source_id["bytes"] - len(body)
    return {"body": body, "projection_id": projection_id, "classes": classes, "capabilities": capabilities,
            "selected": selected_ids, "omitted": [r["id"] for r in rows if not r["selected"]],
            "fragments": rows, "source": source_id, "manifest": manifest_id,
            "projection": identity(body),
            "comparison": {"boundary": BOUNDARY, "static_bytes": source_id["bytes"], "projected_bytes": len(body),
                           "delta_bytes": delta,
                           "delta_percent": round(100.0 * delta / source_id["bytes"], 2) if source_id["bytes"] else None}}
