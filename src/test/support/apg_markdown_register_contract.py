"""Exact APG64 Markdown register identity and fixture-projection contract."""

from __future__ import annotations

import hashlib
import re
from typing import Any, NoReturn

from apg_markdown_vocabulary_contract import verify_exact_vocabulary


REGISTER_BLOB_OID = "d3ac0dc2140e9daa87cdde7249a80ca0fcb934d6"
REGISTER_FIELDS = (
    "In", "Dialect", "Decision", "Owner", "Selection", "Response", "Route",
    "Non", "Structural", "Semantic", "Invariant", "Forbid", "Rb", "Src",
)
HEADING_RE = re.compile(r"(?m)^### (APG63-MD-\d{3})[^\n]*$")
FIELD_RE = re.compile(r"(?m)^- ([A-Za-z]+): (.+)$")

DECISION_CLASSES = {
    "decide the document's block and inline Markdown semantics": "block-inline-semantics",
    "decide the table syntax under the enabled extension set": "extension-table-syntax",
    "decide task-item syntax without assigning workflow meaning": "extension-task-item-syntax",
    "decide whether the evidenced extension recognizes the bare URL": "extension-autolink-syntax",
    "decide whether the repository enables another parser extension": "extension-enable-policy",
    "identify the parser before dialect-dependent judgment": "parser-discovery",
    "decide whether to change tooling or accept its version-bound behavior": "parser-conflict-policy",
    "resolve the exact delimiter run before editing": "delimiter-resolution",
    "decide the proportionate Markdown-structure repair": "heading-structure-repair",
    "resolve the Markdown collision after project intent is supplied": "reference-collision-repair",
    "decide the valid replacement destination": "link-destination-policy",
    "decide Markdown syntax while routing accessibility acceptance": "image-syntax-accessibility-route",
    "decide the fence boundary while routing embedded semantics": "fence-boundary-embedded-route",
    "restore the smallest valid closing boundary": "fence-boundary-repair",
    "resolve the exact container structure before reflow": "container-structure-resolution",
    "decide the exact delimiter run": "code-span-delimiter-resolution",
    "decide the Markdown pass-through boundary and route HTML meaning": "raw-html-boundary-route",
    "apply the anti-evasion structural response and route permission policy": "raw-html-policy-evasion",
    "enforce the explicit repository prohibition": "raw-html-prohibition",
    "decide body Markdown beginning after the closing delimiter": "frontmatter-body-boundary",
    "identify the governing schema before changing fields": "frontmatter-schema-discovery",
    "restore the parser-owned delimiter without changing data values": "frontmatter-delimiter-repair",
    "decide ordinary whole-file Markdown semantics": "whole-file-markdown-semantics",
    "decline whole-file Markdown selection and route to MDX": "whole-file-mdx-handoff",
    "keep whole-file ownership with the host and inspect the embedded route": "host-fragment-route",
    "decide the current Markdown growth without using length as severity": "signal-free-legacy-growth",
    "repair the manual/generated ownership conflict through the generator": "generated-hand-edit-repair",
    "decide whether the proposed growth requires decomposition": "document-decomposition",
    "choose a bounded extraction seam for the current growth": "structural-extraction",
    "stop dependent work and obtain one authoritative project decision": "normative-contradiction-resolution",
    "add bounded navigation or choose an extraction seam": "navigation-repair",
    "stop dependent work and obtain the project-policy resolution": "normative-contradiction-resolution",
}

ROLLBACK_CLASSES = {
    "not material": "none",
    "preserve navigation and record the move map": "preserve-navigation-move-map",
    "record both definitions before material repair": "record-collision-definitions",
    "record both pre-change statements": "preserve-prechange-statements",
    "record pre-repair bytes for material edits": "record-frontmatter-bytes",
    "record the contradiction; no content rollback precedes resolution": "preserve-contradiction-pending-resolution",
    "record the extraction map": "record-extraction-map",
    "record the moved responsibility before material repair": "record-moved-responsibility",
    "record the pre-repair region for material edits": "record-reclassified-region",
    "record the predecision behavior for a material tooling decision": "record-predecision-behavior",
    "regeneration is the rollback path": "regenerate-from-owner",
}

SOURCE_BOUNDARY_CLASSES = {
    "actual MDX and host pipeline": "mdx-host-pipeline",
    "actual MDX pipeline": "mdx-pipeline",
    "actual MDX pipeline; outside pinned Markdown references": "mdx-pipeline-outside-references",
    "actual parser/configuration": "actual-parser-configuration",
    "actual parser/configuration and applicable reference": "actual-parser-plus-applicable-reference",
    "actual parser/configuration plus HTML owner": "actual-parser-plus-html-owner",
    "actual parser/configuration plus accessibility policy": "actual-parser-plus-accessibility-policy",
    "actual parser/configuration plus artifact classification": "parser-plus-artifact-classification",
    "actual parser/configuration plus bounded reference": "actual-parser-plus-bounded-reference",
    "actual parser/configuration plus navigation evidence": "parser-plus-navigation-evidence",
    "actual parser/configuration plus project input": "parser-plus-project-input",
    "actual parser/configuration plus repository policy": "actual-parser-plus-repository-policy",
    "actual parser/configuration plus reviewer evidence": "parser-plus-reviewer-evidence",
    "generator and parser evidence": "generator-plus-parser",
    "host renderer evidence": "host-renderer-evidence",
    "pinned CommonMark object plus parser evidence": "commonmark-plus-parser",
    "pinned GFM object plus parser evidence": "gfm-plus-parser",
    "pinned specifications plus parser evidence": "pinned-specifications-plus-parser",
    "project policy and repository evidence": "project-policy-plus-repository-evidence",
    "project schema and parser evidence": "project-schema-plus-parser",
    "project state and link policy": "project-state-plus-link-policy",
    "repository parser evidence required": "repository-parser-evidence-required",
    "repository policy plus parser evidence": "repository-policy-plus-parser",
}


class RegisterContractError(ValueError):
    """The accepted register or its fixture projection violates the contract."""


def fail(message: str) -> NoReturn:
    raise RegisterContractError(message)


def git_blob_oid(data: bytes) -> str:
    """Return the Git SHA-1 object identity for exact blob bytes."""

    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data, usedforsecurity=False).hexdigest()


def verify_register_blob(data: bytes) -> str:
    oid = git_blob_oid(data)
    if oid != REGISTER_BLOB_OID:
        fail("accepted Markdown register blob identity is invalid")
    return oid


def parse_register(text: str) -> tuple[dict[str, str], ...]:
    """Parse the closed fourteen-field APG64 register without prose inference."""

    headings = list(HEADING_RE.finditer(text))
    ids = [match.group(1) for match in headings]
    expected = [f"APG63-MD-{index:03d}" for index in range(1, 37)]
    if ids != expected:
        fail("register IDs must be contiguous rows 001 through 036")
    rows: list[dict[str, str]] = []
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        pairs = FIELD_RE.findall(text[heading.end():end])
        names = [name for name, _ in pairs]
        duplicates = sorted(name for name in set(names) if names.count(name) > 1)
        if duplicates:
            fail(f"{ids[index]} contains duplicate field: {duplicates[0]}")
        unknown = sorted(set(names) - set(REGISTER_FIELDS))
        if unknown:
            fail(f"{ids[index]} contains unknown field: {unknown[0]}")
        missing = sorted(set(REGISTER_FIELDS) - set(names))
        if missing:
            fail(f"{ids[index]} is missing field: {missing[0]}")
        if tuple(names) != REGISTER_FIELDS:
            fail(f"{ids[index]} fields are not in the accepted order")
        rows.append({"id": ids[index], **dict(pairs)})
    return tuple(rows)


def _list_field(value: str) -> list[str]:
    if value in {"none", "not-applicable"}:
        return []
    return [item.strip() for item in value.split(",")]


def _mapped(mapping: dict[str, str], value: str, field: str, row_id: str) -> str:
    try:
        return mapping[value]
    except KeyError:
        fail(f"{row_id} uses unknown {field}")


def project_semantic_rows(
    rows: tuple[dict[str, str], ...], vocabulary: dict[str, Any]
) -> list[dict[str, Any]]:
    """Project rows 001-034 into the public fixture schema."""

    if len(rows) != 36:
        fail("register must contain 34 semantic and 2 process rows")
    if [row["id"] for row in rows[34:]] != ["APG63-MD-035", "APG63-MD-036"]:
        fail("register process rows are invalid")
    try:
        verify_exact_vocabulary(vocabulary)
    except ValueError as error:
        fail(str(error))
    required_vocab = {
        "owners", "responses", "rollback_classes", "selections",
        "semantic_signals", "source_boundary_classes", "structural_signals",
    }
    if set(vocabulary) != required_vocab:
        fail("fixture vocabulary schema is invalid")
    allowed = {key: set(value) for key, value in vocabulary.items()}
    projected: list[dict[str, Any]] = []
    for row in rows[:34]:
        row_id = row["id"]
        nonowners = _list_field(row["Non"])
        structural = _list_field(row["Structural"])
        semantic = _list_field(row["Semantic"])
        result = {
            "id": row_id,
            "decision_class": _mapped(DECISION_CLASSES, row["Decision"], "decision", row_id),
            "owner": row["Owner"],
            "selection": row["Selection"],
            "response": row["Response"],
            "route": row["Route"],
            "nonowners": nonowners,
            "structural_signals": structural,
            "semantic_signals": semantic,
            "rollback_class": _mapped(ROLLBACK_CLASSES, row["Rb"], "rollback", row_id),
            "source_boundary_class": _mapped(
                SOURCE_BOUNDARY_CLASSES, row["Src"], "source boundary", row_id
            ),
        }
        for field, vocab_key in (
            ("owner", "owners"), ("selection", "selections"),
            ("response", "responses"), ("rollback_class", "rollback_classes"),
            ("source_boundary_class", "source_boundary_classes"),
        ):
            if result[field] not in allowed[vocab_key]:
                fail(f"{row_id} uses unknown {field}")
        if result["route"] != "not-applicable" and result["route"] not in allowed["owners"]:
            fail(f"{row_id} uses unknown route")
        for field, vocab_key in (
            ("nonowners", "owners"), ("structural_signals", "structural_signals"),
            ("semantic_signals", "semantic_signals"),
        ):
            if not set(result[field]) <= allowed[vocab_key]:
                fail(f"{row_id} uses unknown {field}")
        projected.append(result)
    return projected


def verify_fixture_projection(register_data: bytes, fixture: dict[str, Any]) -> None:
    """Bind exact accepted register bytes to the complete public-safe fixture."""

    verify_register_blob(register_data)
    try:
        text = register_data.decode("utf-8")
    except UnicodeDecodeError:
        fail("accepted Markdown register is not UTF-8")
    rows = parse_register(text)
    expected_authority = {
        "source_phase": "APG64",
        "register_blob_oid": REGISTER_BLOB_OID,
        "semantic_rows": 34,
        "process_rows": 0,
    }
    if fixture.get("authority") != expected_authority:
        fail("fixture authority binding is invalid")
    projected = project_semantic_rows(rows, fixture.get("vocabulary", {}))
    if fixture.get("rows") != projected:
        fail("fixture rows disagree with the accepted register projection")
