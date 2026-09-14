"""APG140: Bounded synthetic APGR consumer fixtures and compatibility admission controls.

This module provides independently authored APGR-local evidence admission controls
for Repo Map public-read presentation envelopes and durable job coordinator contracts
(observed source main 2026-09-12; public ID: APG140-RM-MAIN-20260912).

IMPORTANT BOUNDARY AND GOVERNANCE NOTES:
- This consumer implementation is APGR-local evidence admission ONLY, NOT Repo Map runtime conformance.
- Strict wire version selection: version 0 (legacy bounded array) or version 1 (presentation envelope).
  Boolean schema versions and other integer/non-integer versions are strictly refused.
- Legacy bounded arrays (version 0) cannot prove completeness, snapshot isolation, or exhaustiveness.
- Incomplete / truncated pages cannot prove complete graph or cross-request snapshot isolation.
- Unknown envelope fields fail closed as an APGR selected policy (do not claim external owner mandates).
- Explicit cancellation before consumption returns a distinct error with no effects (APGR fixture policy).
- Synthetic graph checker compares independently provided expected nodes, directed edges, identity
  metadata, and provenance against observed graphs, cleanly accepting cycles, detecting conflicts,
  missing, spurious, and duplicate entries, and separating provenance quality from storage claims.
- Fixture cases manifest enforces exact member sets, SHA-256 byte digests, and rejects symlinks and
  path traversals.
- Public-safe contract names and clauses only. No private revisions or paths.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Any, Iterable, Mapping, Sequence


# --- Public Contract Metadata ---

PUBLIC_CONTRACT_ID = "APG140-RM-MAIN-20260912"
OBSERVED_SOURCE_DATE = "2026-09-12"
ALLOWED_WIRE_VERSIONS = (0, 1)


def admit_negotiation_observation(observation: dict) -> int:
    """Admit an ASYNC1 negotiation projection, not a complete worker frame.

    Source _protocol_core.py fixes schema_version=1 and protocol_versions=[1].
    Worker authentication, capabilities, framing and lifecycle are not tested
    by this two-field APGR evidence projection.
    """
    if not isinstance(observation, dict) or set(observation) != {"schema_version", "protocol_versions"}:
        raise EnvelopeValidationError("invalid negotiation projection fields")
    if type(observation["schema_version"]) is not int or observation["schema_version"] != 1:
        raise WireVersionError("unsupported negotiation schema")
    versions = observation["protocol_versions"]
    if not isinstance(versions, list) or len(versions) != 1 or type(versions[0]) is not int or versions[0] != 1:
        raise WireVersionError("negotiation_failed")
    return 1

DIRECT_RESULT_KINDS = ("canonical_nodes", "canonical_edges")
EMBEDDED_RESULT_KINDS = ("canonical_neighborhood", "canonical_edge_explanation")
ALL_RESULT_KINDS = DIRECT_RESULT_KINDS + EMBEDDED_RESULT_KINDS

V1_ENVELOPE_KEYS = frozenset({"schema_version", "result_kind", "items", "page", "diagnostics"})
V1_EMBEDDED_ENVELOPE_KEYS = frozenset({"schema_version", "result_kind", "result", "collections", "diagnostics"})
PAGE_DESCRIPTOR_KEYS = frozenset({"limit", "offset", "returned", "truncated", "next_offset"})

MIN_PAGE_LIMIT = 1
MAX_PAGE_LIMIT = 200
DEFAULT_PAGE_LIMIT = 50


# --- Exception Hierarchy ---

class CompatibilityError(Exception):
    """Base exception for external compatibility fixtures and consumer admission."""


class WireVersionError(CompatibilityError):
    """Raised when wire version selection is invalid or disallowed."""


class EnvelopeValidationError(CompatibilityError):
    """Raised when presentation envelope fails structure, bounds, or consistency checks."""


class UnknownFieldError(EnvelopeValidationError):
    """Raised when an unknown envelope or page field is encountered.

    Fails closed under APGR selected admission policy (not claimed as an external mandate).
    """


class IdentityDriftError(CompatibilityError):
    """Raised when observed payload drifts from caller expected binding."""


class CallerRefusalError(CompatibilityError):
    """Raised when the caller explicitly refuses consumption."""


class FixtureCancellationError(CompatibilityError):
    """Raised when explicit cancellation occurs before consumption.

    Produces zero side effects as APGR fixture policy.
    """


class ManifestVerificationError(CompatibilityError):
    """Raised when fixture manifest verification fails."""


class GraphCheckError(CompatibilityError):
    """Raised when synthetic graph comparison encounters structural violations."""


# --- Data Structures ---

@dataclass
class CancellationToken:
    """Cooperative cancellation token checked before consumption."""

    _cancelled: bool = False
    _reason: str = ""

    def cancel(self, reason: str = "cancelled by caller") -> None:
        self._cancelled = True
        self._reason = reason

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    @property
    def reason(self) -> str:
        return self._reason


@dataclass(frozen=True)
class CallerBinding:
    """Caller-owned expectations supplied separately from the public presentation envelope."""

    expected_result_kind: str | None = None
    expected_public_id: str | None = None
    expected_wire_version: int | None = None
    refuse_reason: str | None = None


@dataclass(frozen=True)
class PageDescriptor:
    """Validated pagination descriptor for Version 1 envelopes."""

    limit: int
    offset: int
    returned: int
    truncated: bool
    next_offset: int | None


@dataclass(frozen=True)
class DiagnosticRecord:
    """Diagnostic entry in presentation envelope."""

    code: str
    message: str
    collection: str | None = None


@dataclass
class ConsumerResult:
    """Outcome of consuming a presentation envelope or legacy array."""

    wire_version: int
    result_kind: str
    items: list[Any]
    page: PageDescriptor | None
    diagnostics: list[DiagnosticRecord]
    is_complete: bool
    raw_payload: Any
    collections: dict[str, PageDescriptor] | None = None
    embedded_result: dict[str, Any] | None = None

    def proves_completeness(self) -> bool:
        """Return True only if this result proves completeness for the single requested window.

        IMPORTANT:
        - Version 0 legacy bounded arrays cannot prove completeness.
        - Truncated pages (truncated=True) cannot prove complete graph or cross-request snapshot isolation.
        - Even untruncated pages do not prove cross-request snapshot isolation if the graph mutates.
        """
        if self.wire_version == 0:
            return False
        if self.page is None:
            return False
        if self.page.truncated:
            return False
        return True


# --- Wire Version and Envelope Parsing ---

def _unique_fields(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise EnvelopeValidationError("duplicate JSON field")
        value[key] = item
    return value


def validate_wire_version(version: Any) -> int:
    """Validate wire version selection under strict APGR admission rules.

    Permits only integers 0 and 1. Refuses boolean values and any other types.
    """
    if type(version) is bool:
        raise WireVersionError("boolean schema versions are refused; must be integer 0 or 1")
    if not isinstance(version, int):
        raise WireVersionError(f"wire version must be integer 0 or 1, got {type(version).__name__}")
    if version not in ALLOWED_WIRE_VERSIONS:
        raise WireVersionError(f"unsupported wire version {version}; accepted versions are 0 or 1")
    return version


def parse_and_validate_envelope(
    payload: str | bytes | dict[str, Any] | list[Any],
    *,
    wire_version: int = 1,
    caller_binding: CallerBinding | None = None,
    cancel_token: CancellationToken | None = None,
) -> ConsumerResult:
    """Parse and validate a presentation payload under APGR admission controls.

    Execution order and policy:
    1. Pre-consumption cancellation: checked before ANY payload processing.
    2. Wire version validation: strictly enforces 0 or 1.
    3. Caller refusal check: caller-owned refusal fails immediately with distinct error.
    4. Payload parsing: parses JSON if string or bytes.
    5. Version 0 validation: expects list, notes inability to prove completeness.
    6. Version 1 validation:
       - checks exact envelope keys (fails closed on unknown fields under APGR policy).
       - validates schema_version == 1.
       - checks caller expected binding for identity drift.
       - validates page bounds (limit 1..200, offset >= 0, returned == len(items) <= limit).
       - validates truncation consistency and lookahead next_offset.
       - validates diagnostic consistency with truncation state.
    """
    # 1. Explicit cancellation before consumption
    if cancel_token is not None and cancel_token.is_cancelled:
        raise FixtureCancellationError(
            f"consumption cancelled before processing: {cancel_token.reason or 'cancellation requested'}"
        )

    # 2. Wire version validation
    validated_version = validate_wire_version(wire_version)

    # 3. Caller-owned refusal check
    if caller_binding is not None and caller_binding.refuse_reason is not None:
        raise CallerRefusalError(f"caller refused consumption: {caller_binding.refuse_reason}")

    if caller_binding is not None:
        if caller_binding.expected_wire_version is not None:
            validate_wire_version(caller_binding.expected_wire_version)
        if caller_binding.expected_public_id not in (None, PUBLIC_CONTRACT_ID):
            raise IdentityDriftError("public contract identity drift")

    # 4. JSON parsing if raw text/bytes
    if isinstance(payload, (str, bytes)):
        try:
            data = json.loads(payload, object_pairs_hook=_unique_fields)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise EnvelopeValidationError(f"malformed JSON payload: {exc}") from exc
    else:
        data = payload

    # 5. Wire Version 0: Legacy Bounded Array
    if validated_version == 0:
        if not isinstance(data, list):
            raise EnvelopeValidationError(
                f"wire version 0 expects JSON array, got {type(data).__name__}"
            )
        if len(data) > MAX_PAGE_LIMIT:
            raise EnvelopeValidationError("legacy array exceeds bounded limit")
        if caller_binding is not None:
            if (
                caller_binding.expected_wire_version is not None
                and caller_binding.expected_wire_version != 0
            ):
                raise IdentityDriftError(
                    f"wire version drift: caller expected {caller_binding.expected_wire_version}, observed 0"
                )
        return ConsumerResult(
            wire_version=0,
            result_kind="legacy_bounded_array",
            items=data,
            page=None,
            diagnostics=[],
            is_complete=False,  # Legacy bounded array cannot prove completeness
            raw_payload=data,
        )

    # 6. Wire Version 1: Presentation Envelope
    if not isinstance(data, dict):
        raise EnvelopeValidationError(
            f"wire version 1 expects JSON object envelope, got {type(data).__name__}"
        )

    # Schema version in envelope
    if "schema_version" not in data:
        raise EnvelopeValidationError("missing required envelope field: 'schema_version'")
    env_schema_ver = data["schema_version"]
    validate_wire_version(env_schema_ver)
    if env_schema_ver != 1:
        raise EnvelopeValidationError(
            f"envelope schema_version {env_schema_ver} does not match requested wire version 1"
        )

    # Result kind in envelope
    if "result_kind" not in data:
        raise EnvelopeValidationError("missing required envelope field: 'result_kind'")
    result_kind = data["result_kind"]
    if result_kind not in ALL_RESULT_KINDS:
        raise EnvelopeValidationError(f"unknown or unallowlisted result_kind: '{result_kind}'")

    # Caller expected binding checks (Identity drift detection)
    if caller_binding is not None:
        if (
            caller_binding.expected_result_kind is not None
            and caller_binding.expected_result_kind != result_kind
        ):
            raise IdentityDriftError(
                f"result_kind identity drift: caller expected '{caller_binding.expected_result_kind}', "
                f"observed '{result_kind}'"
            )
        if (
            caller_binding.expected_public_id is not None
            and caller_binding.expected_public_id != PUBLIC_CONTRACT_ID
        ):
            raise IdentityDriftError(
                f"public contract identity drift: caller expected '{caller_binding.expected_public_id}', "
                f"observed '{PUBLIC_CONTRACT_ID}'"
            )
        if (
            caller_binding.expected_wire_version is not None
            and caller_binding.expected_wire_version != 1
        ):
            raise IdentityDriftError(
                f"wire version drift: caller expected {caller_binding.expected_wire_version}, observed 1"
            )

    # Direct canonical lists (nodes / edges)
    if result_kind in DIRECT_RESULT_KINDS:
        # Check unknown envelope fields (fails closed under APGR selected policy)
        extra_keys = set(data.keys()) - V1_ENVELOPE_KEYS
        if extra_keys:
            raise UnknownFieldError(
                f"unknown envelope field(s) {sorted(extra_keys)} fail closed under APGR selected policy "
                "(note: APGR admission policy, not claimed as external owner mandate)"
            )

        missing_keys = V1_ENVELOPE_KEYS - set(data.keys())
        if missing_keys:
            raise EnvelopeValidationError(
                f"missing required envelope field(s): {sorted(missing_keys)}"
            )

        # Validate items
        items = data["items"]
        if not isinstance(items, list):
            raise EnvelopeValidationError(f"'items' must be a list, got {type(items).__name__}")

        # Validate page descriptor
        page_dict = data["page"]
        if not isinstance(page_dict, dict):
            raise EnvelopeValidationError(f"'page' must be a dict, got {type(page_dict).__name__}")

        page_extra = set(page_dict.keys()) - PAGE_DESCRIPTOR_KEYS
        if page_extra:
            raise UnknownFieldError(
                f"unknown page field(s) {sorted(page_extra)} fail closed under APGR selected policy"
            )

        page_missing = PAGE_DESCRIPTOR_KEYS - set(page_dict.keys())
        if page_missing:
            raise EnvelopeValidationError(
                f"missing required page descriptor field(s): {sorted(page_missing)}"
            )

        limit = page_dict["limit"]
        offset = page_dict["offset"]
        returned = page_dict["returned"]
        truncated = page_dict["truncated"]
        next_offset = page_dict["next_offset"]

        if type(limit) is bool or not isinstance(limit, int) or limit < MIN_PAGE_LIMIT or limit > MAX_PAGE_LIMIT:
            raise EnvelopeValidationError(
                f"'page.limit' must be integer in range [{MIN_PAGE_LIMIT}, {MAX_PAGE_LIMIT}], got {limit!r}"
            )
        if type(offset) is bool or not isinstance(offset, int) or offset < 0:
            raise EnvelopeValidationError(
                f"'page.offset' must be non-negative integer, got {offset!r}"
            )
        if type(returned) is bool or not isinstance(returned, int) or returned < 0:
            raise EnvelopeValidationError(
                f"'page.returned' must be non-negative integer, got {returned!r}"
            )
        if returned != len(items):
            raise EnvelopeValidationError(
                f"'page.returned' ({returned}) does not match actual length of items ({len(items)})"
            )
        if returned > limit:
            raise EnvelopeValidationError(
                f"'page.returned' ({returned}) exceeds declared 'page.limit' ({limit})"
            )
        if type(truncated) is not bool:
            raise EnvelopeValidationError(
                f"'page.truncated' must be boolean, got {truncated!r}"
            )

        # Truncation and next_offset relations
        if truncated:
            if returned != limit:
                raise EnvelopeValidationError("truncated page must expose the full window")
            if type(next_offset) is bool or not isinstance(next_offset, int):
                raise EnvelopeValidationError(
                    f"'page.next_offset' must be integer when truncated=true, got {next_offset!r}"
                )
            expected_next = offset + returned
            if next_offset != expected_next:
                raise EnvelopeValidationError(
                    f"'page.next_offset' ({next_offset}) must equal offset + returned ({expected_next})"
                )
        else:
            if next_offset is not None:
                raise EnvelopeValidationError(
                    f"'page.next_offset' must be null (None) when truncated=false, got {next_offset!r}"
                )

        page_desc = PageDescriptor(
            limit=limit,
            offset=offset,
            returned=returned,
            truncated=truncated,
            next_offset=next_offset,
        )

        # Diagnostics validation and consistency check
        raw_diags = data["diagnostics"]
        if not isinstance(raw_diags, list):
            raise EnvelopeValidationError(
                f"'diagnostics' must be a list, got {type(raw_diags).__name__}"
            )

        diag_records: list[DiagnosticRecord] = []
        has_truncated_diag = False

        for d in raw_diags:
            if not isinstance(d, dict) or "code" not in d or "message" not in d:
                raise EnvelopeValidationError(f"malformed diagnostic record: {d!r}")
            code = d["code"]
            msg = d["message"]
            col = d.get("collection")
            if code == "result_truncated":
                has_truncated_diag = True
                if msg != "additional results are available":
                    raise EnvelopeValidationError(
                        f"diagnostic 'result_truncated' message must be 'additional results are available', got {msg!r}"
                    )
            diag_records.append(DiagnosticRecord(code=code, message=msg, collection=col))

        if truncated and not has_truncated_diag:
            raise EnvelopeValidationError(
                "diagnostic consistency violation: page is truncated (truncated=true) but diagnostics "
                "lacks required 'result_truncated' code"
            )
        if not truncated and has_truncated_diag:
            raise EnvelopeValidationError(
                "diagnostic consistency violation: page is exhausted (truncated=false) but diagnostics "
                "contains 'result_truncated' code"
            )

        is_complete = (not truncated)

        return ConsumerResult(
            wire_version=1,
            result_kind=result_kind,
            items=items,
            page=page_desc,
            diagnostics=diag_records,
            is_complete=is_complete,
            raw_payload=data,
        )

    # Embedded collections (neighborhood / explanation)
    extra_keys = set(data.keys()) - V1_EMBEDDED_ENVELOPE_KEYS
    if extra_keys:
        raise UnknownFieldError(
            f"unknown embedded envelope field(s) {sorted(extra_keys)} fail closed under APGR selected policy"
        )
    missing_keys = V1_EMBEDDED_ENVELOPE_KEYS - set(data.keys())
    if missing_keys:
        raise EnvelopeValidationError(
            f"missing required embedded envelope field(s): {sorted(missing_keys)}"
        )

    result_obj = data["result"]
    if not isinstance(result_obj, dict):
        raise EnvelopeValidationError(f"'result' must be a dict, got {type(result_obj).__name__}")

    collections_dict = data["collections"]
    if not isinstance(collections_dict, dict):
        raise EnvelopeValidationError(
            f"'collections' must be a dict, got {type(collections_dict).__name__}"
        )

    required_collections = ({"nodes", "edges"} if result_kind == "canonical_neighborhood" else {"evidence"})
    required_result = required_collections | ({"center"} if result_kind == "canonical_neighborhood" else {"edge"})
    if set(collections_dict) != required_collections or set(result_obj) != required_result:
        raise EnvelopeValidationError("missing or unknown embedded collection/result fields")
    raw_diags = data["diagnostics"]
    if not isinstance(raw_diags, list):
        raise EnvelopeValidationError("diagnostics must be a list")
    for diagnostic in raw_diags:
        if (not isinstance(diagnostic, dict)
                or set(diagnostic) != {"code", "message", "collection"}
                or diagnostic["collection"] not in required_collections):
            raise EnvelopeValidationError("malformed embedded diagnostic")
    collections_desc = {}
    diag_records = []
    any_truncated = False
    for name in sorted(required_collections):
        # Reuse the same direct-window checks, including counts and diagnostics.
        direct_diags = [{"code": d["code"], "message": d["message"]}
                        for d in raw_diags if d["collection"] == name]
        parsed = parse_and_validate_envelope({
            "schema_version": 1, "result_kind": "canonical_nodes",
            "items": result_obj[name], "page": collections_dict[name],
            "diagnostics": direct_diags,
        })
        collections_desc[name] = parsed.page
        any_truncated |= parsed.page.truncated
        diag_records.extend(DiagnosticRecord(d.code, d.message, name) for d in parsed.diagnostics)

    return ConsumerResult(
        wire_version=1,
        result_kind=result_kind,
        items=[],
        page=None,
        diagnostics=diag_records,
        is_complete=(not any_truncated),
        raw_payload=data,
        collections=collections_desc,
        embedded_result=result_obj,
    )


# --- Source-Bound Synthetic Graph Checker ---

@dataclass
class ProvenanceCheckFinding:
    """Finding regarding provenance quality, separate from storage existence."""

    key: str
    status: str  # 'verified', 'missing', 'mismatched', 'unlinked'
    details: str


@dataclass
class GraphCheckReport:
    """Report comparing independently given expected graph against observed graph."""

    # Node comparison
    matched_nodes: list[str] = field(default_factory=list)
    missing_nodes: list[str] = field(default_factory=list)
    spurious_nodes: list[str] = field(default_factory=list)
    duplicate_nodes: list[str] = field(default_factory=list)
    conflicted_nodes: list[dict[str, Any]] = field(default_factory=list)

    # Edge comparison
    matched_edges: list[tuple[str, str, str, str]] = field(default_factory=list)
    missing_edges: list[tuple[str, str, str, str]] = field(default_factory=list)
    spurious_edges: list[tuple[str, str, str, str]] = field(default_factory=list)
    duplicate_edges: list[tuple[str, str, str, str]] = field(default_factory=list)
    conflicted_edges: list[dict[str, Any]] = field(default_factory=list)

    # Graph characteristics
    cycles_detected: list[list[str]] = field(default_factory=list)
    cycles_accepted: bool = True

    # High-level partitions: Storage Claims vs Provenance Quality
    storage_is_exact_match: bool = False
    provenance_findings: list[ProvenanceCheckFinding] = field(default_factory=list)
    provenance_is_sound: bool | None = None


class SyntheticGraphChecker:
    """Compares independently given expected graph models against observed graphs.

    Properties:
    - Directed edges keyed by (source_key, edge_kind, target_key, identity_metadata_hash).
    - Nodes keyed by canonical_key.
    - Handles and reports duplicate observations (dedup tracking).
    - Accepts cyclic directed graphs cleanly without recursion errors.
    - Strictly separates storage claims (node/edge presence) from provenance quality.
    """

    def check_graph(
        self,
        expected_nodes: Iterable[dict[str, Any] | str],
        expected_edges: Iterable[dict[str, Any] | tuple[str, str, str, str]],
        observed_nodes: Iterable[dict[str, Any] | str],
        observed_edges: Iterable[dict[str, Any] | tuple[str, str, str, str]],
        *,
        expected_provenance: Mapping[str, Any] | None = None,
        observed_provenance: Mapping[str, Any] | None = None,
    ) -> GraphCheckReport:
        report = GraphCheckReport()

        # 1. Normalize expected nodes
        exp_nodes_map: dict[str, dict[str, Any]] = {}
        for n in expected_nodes:
            if isinstance(n, str):
                exp_nodes_map[n] = {"canonical_key": n}
            elif isinstance(n, dict):
                k = n.get("canonical_key")
                if not k:
                    raise GraphCheckError(f"node missing 'canonical_key': {n!r}")
                if k in exp_nodes_map:
                    raise GraphCheckError("duplicate expected node identity")
                exp_nodes_map[k] = n
            else:
                raise GraphCheckError(f"invalid expected node representation: {n!r}")

        # 2. Normalize observed nodes and track duplicates
        obs_nodes_map: dict[str, dict[str, Any]] = {}
        seen_node_keys: set[str] = set()
        for n in observed_nodes:
            if isinstance(n, str):
                k = n
                rec = {"canonical_key": n}
            elif isinstance(n, dict):
                k = n.get("canonical_key")
                if not k:
                    raise GraphCheckError(f"observed node missing 'canonical_key': {n!r}")
                rec = n
            else:
                raise GraphCheckError(f"invalid observed node representation: {n!r}")

            if k in seen_node_keys:
                report.duplicate_nodes.append(k)
                if obs_nodes_map[k] != rec:
                    report.conflicted_nodes.append({"canonical_key": k, "conflict": "duplicate_conflict"})
            else:
                seen_node_keys.add(k)
                obs_nodes_map[k] = rec

        # Node comparison
        for k, exp_rec in exp_nodes_map.items():
            if k not in obs_nodes_map:
                report.missing_nodes.append(k)
            else:
                obs_rec = obs_nodes_map[k]
                # Check for metadata/attribute conflicts
                exp_kind = exp_rec.get("kind")
                obs_kind = obs_rec.get("kind")
                if any(obs_rec.get(field) != value for field, value in exp_rec.items()):
                    report.conflicted_nodes.append({
                        "canonical_key": k,
                        "conflict": "kind_mismatch",
                        "expected": exp_kind,
                        "observed": obs_kind,
                    })
                else:
                    report.matched_nodes.append(k)

        for k in obs_nodes_map:
            if k not in exp_nodes_map:
                report.spurious_nodes.append(k)

        # 3. Normalize expected edges: (src, kind, tgt, hash)
        exp_edges_map: dict[tuple[str, str, str, str], dict[str, Any]] = {}
        for e in expected_edges:
            edge_tuple, edge_rec = self._normalize_edge(e)
            exp_edges_map[edge_tuple] = edge_rec

        # 4. Normalize observed edges and track duplicates
        obs_edges_map: dict[tuple[str, str, str, str], dict[str, Any]] = {}
        seen_edge_tuples: set[tuple[str, str, str, str]] = set()
        for e in observed_edges:
            edge_tuple, edge_rec = self._normalize_edge(e)
            if edge_tuple in seen_edge_tuples:
                report.duplicate_edges.append(edge_tuple)
            else:
                seen_edge_tuples.add(edge_tuple)
                obs_edges_map[edge_tuple] = edge_rec

        # Edge comparison
        for t, exp_rec in exp_edges_map.items():
            if t not in obs_edges_map:
                # Check if there is a conflict on same endpoint but differing metadata hash
                src, kind, tgt, h = t
                conflicts = [
                    (ot, o_rec) for ot, o_rec in obs_edges_map.items()
                    if ot[0] == src and ot[1] == kind and ot[2] == tgt and ot[3] != h
                ]
                if conflicts:
                    for ct, c_rec in conflicts:
                        report.conflicted_edges.append({
                            "source_key": src,
                            "edge_kind": kind,
                            "target_key": tgt,
                            "conflict": "identity_metadata_hash_mismatch",
                            "expected_hash": h,
                            "observed_hash": ct[3],
                        })
                else:
                    report.missing_edges.append(t)
            else:
                report.matched_edges.append(t)

        for t in obs_edges_map:
            if t not in exp_edges_map:
                # If not already recorded as conflict
                src, kind, tgt, h = t
                is_conflict = any(
                    et[0] == src and et[1] == kind and et[2] == tgt and et[3] != h
                    for et in exp_edges_map
                )
                if not is_conflict:
                    report.spurious_edges.append(t)

        # 5. Cycle Detection (accepts cycles cleanly)
        report.cycles_detected = self._find_cycles(obs_edges_map.keys())
        report.cycles_accepted = True

        # 6. Storage Claim Determination
        report.storage_is_exact_match = (
            len(report.missing_nodes) == 0
            and len(report.duplicate_nodes) == 0
            and len(report.duplicate_edges) == 0
            and len(report.spurious_nodes) == 0
            and len(report.conflicted_nodes) == 0
            and len(report.missing_edges) == 0
            and len(report.spurious_edges) == 0
            and len(report.conflicted_edges) == 0
        )

        # 7. Provenance Quality Evaluation (Partitioned separately)
        if expected_provenance is not None or observed_provenance is not None:
            exp_p = expected_provenance or {}
            obs_p = observed_provenance or {}
            sound = True

            for p_key, p_exp_val in exp_p.items():
                if p_key not in obs_p:
                    report.provenance_findings.append(
                        ProvenanceCheckFinding(
                            key=p_key,
                            status="missing",
                            details=f"expected provenance '{p_key}' absent in observed graph",
                        )
                    )
                    sound = False
                else:
                    p_obs_val = obs_p[p_key]
                    if p_exp_val != p_obs_val:
                        report.provenance_findings.append(
                            ProvenanceCheckFinding(
                                key=p_key,
                                status="mismatched",
                                details=f"provenance value mismatch for '{p_key}': expected {p_exp_val!r}, observed {p_obs_val!r}",
                            )
                        )
                        sound = False
                    else:
                        report.provenance_findings.append(
                            ProvenanceCheckFinding(
                                key=p_key,
                                status="verified",
                                details=f"provenance matched for '{p_key}'",
                            )
                        )

            for p_key in obs_p:
                if p_key not in exp_p:
                    sound = False
                    report.provenance_findings.append(
                        ProvenanceCheckFinding(
                            key=p_key,
                            status="unlinked",
                            details=f"unlinked extra provenance record '{p_key}' present in observed",
                        )
                    )

            report.provenance_is_sound = sound

        return report

    @staticmethod
    def _normalize_edge(
        e: dict[str, Any] | tuple[str, str, str, str],
    ) -> tuple[tuple[str, str, str, str], dict[str, Any]]:
        if isinstance(e, tuple):
            if len(e) != 4:
                raise GraphCheckError(f"edge tuple must have 4 elements (src, kind, tgt, hash), got {e!r}")
            return e, {"source_key": e[0], "edge_kind": e[1], "target_key": e[2], "identity_metadata_hash": e[3]}
        if isinstance(e, dict):
            src = e.get("source_key")
            kind = e.get("edge_kind") or e.get("kind")
            tgt = e.get("target_key")
            h = e.get("identity_metadata_hash", "")
            if not src or not kind or not tgt:
                raise GraphCheckError(f"edge dict missing source_key, edge_kind, or target_key: {e!r}")
            return (str(src), str(kind), str(tgt), str(h)), e
        raise GraphCheckError(f"invalid edge representation: {e!r}")

    @staticmethod
    def _find_cycles(edges: Iterable[tuple[str, str, str, str]]) -> list[list[str]]:
        """Find elementary directed cycles in the graph using DFS."""
        adj: dict[str, list[str]] = collections.defaultdict(list)
        for src, _kind, tgt, _h in edges:
            adj[src].append(tgt)

        cycles: list[list[str]] = []
        visited: set[str] = set()
        rec_stack: list[str] = []
        rec_set: set[str] = set()

        def dfs(node: str) -> None:
            visited.add(node)
            rec_stack.append(node)
            rec_set.add(node)

            for neighbor in adj.get(node, []):
                if neighbor in rec_set:
                    # Found a cycle
                    idx = rec_stack.index(neighbor)
                    cycle = list(rec_stack[idx:]) + [neighbor]
                    cycles.append(cycle)
                elif neighbor not in visited:
                    dfs(neighbor)

            rec_stack.pop()
            rec_set.remove(node)

        for n in list(adj.keys()):
            if n not in visited:
                dfs(n)

        return cycles


# --- Fixture Cases Manifest Verification ---

def verify_fixture_manifest(fixture_dir: Path | str) -> dict[str, Any]:
    """Verify fixture cases manifest integrity, member digests, and exact member set.

    Verification guarantees:
    - manifest.json exists and adheres to manifest_schema_version 1.
    - Declares valid public contract identity APG140-RM-MAIN-20260912.
    - Relative member paths only; no path traversal ('..') or absolute paths.
    - No symbolic links permitted anywhere in fixture members or cases.
    - Every declared member exists and matches its recorded SHA-256 digest and byte size.
    - Exact member set: No unlisted files in cases directory and no omitted files.
    """
    supplied = Path(fixture_dir).absolute()
    if any(part.is_symlink() for part in (supplied, *supplied.parents)):
        raise ManifestVerificationError("symlink fixture root is prohibited")
    root = supplied.resolve()
    manifest_file = root / "manifest.json"

    if manifest_file.is_symlink() or not manifest_file.is_file():
        raise ManifestVerificationError(f"manifest.json not found in {root}")

    try:
        manifest_data = json.loads(manifest_file.read_bytes(), object_pairs_hook=_unique_fields)
    except Exception as exc:
        raise ManifestVerificationError(f"manifest.json is malformed: {exc}") from exc

    if not isinstance(manifest_data, dict):
        raise ManifestVerificationError("manifest.json must be a JSON object")

    if type(manifest_data.get("manifest_schema_version")) is not int or manifest_data.get("manifest_schema_version") != 1:
        raise ManifestVerificationError(
            f"unsupported manifest_schema_version: {manifest_data.get('manifest_schema_version')}"
        )

    pub_contract = manifest_data.get("public_source_contract", {})
    pub_id = pub_contract.get("public_contract_id")
    if pub_id != PUBLIC_CONTRACT_ID:
        raise ManifestVerificationError(
            f"manifest public_contract_id '{pub_id}' does not match expected '{PUBLIC_CONTRACT_ID}'"
        )

    members = manifest_data.get("members")
    if not isinstance(members, list) or not members:
        raise ManifestVerificationError("manifest 'members' must be a list")

    declared_paths: set[str] = set()

    for idx, member in enumerate(members):
        if not isinstance(member, dict):
            raise ManifestVerificationError(f"member at index {idx} must be an object")

        rel_path = member.get("path")
        if not rel_path or not isinstance(rel_path, str):
            raise ManifestVerificationError(f"member at index {idx} missing valid 'path'")

        # Traversal and path security checks
        if ".." in rel_path or rel_path.startswith("/") or "\\" in rel_path:
            raise ManifestVerificationError(
                f"illegal path traversal or absolute path in member: {rel_path}"
            )

        if rel_path in declared_paths or Path(rel_path).as_posix() != rel_path or not rel_path.startswith("cases/"):
            raise ManifestVerificationError("duplicate or noncanonical member path")
        current = root
        for component in Path(rel_path).parts:
            current = current / component
            if current.is_symlink():
                raise ManifestVerificationError("symbolic links are strictly prohibited")
        full_path = (root / rel_path).resolve()
        try:
            full_path.relative_to(root)
        except ValueError:
            raise ManifestVerificationError(f"member path traverses outside fixture root: {rel_path}")

        # Symlink check
        raw_target = root / rel_path
        if raw_target.is_symlink() or os.path.islink(raw_target):
            raise ManifestVerificationError(f"symbolic links are strictly prohibited: {rel_path}")

        if not full_path.is_file():
            raise ManifestVerificationError(f"declared member file does not exist: {rel_path}")

        expected_sha = member.get("sha256")
        expected_size = member.get("size_bytes")
        if not expected_sha or expected_size is None:
            raise ManifestVerificationError(
                f"member '{rel_path}' missing 'sha256' or 'size_bytes'"
            )

        actual_bytes = full_path.read_bytes()
        actual_size = len(actual_bytes)
        actual_sha = hashlib.sha256(actual_bytes).hexdigest()

        if actual_size != expected_size:
            raise ManifestVerificationError(
                f"member size mismatch for '{rel_path}': expected {expected_size}, got {actual_size}"
            )
        if actual_sha != expected_sha:
            raise ManifestVerificationError(
                f"member SHA-256 digest mismatch for '{rel_path}': expected {expected_sha}, got {actual_sha}"
            )

        declared_paths.add(rel_path)

    # Exact member set: check for unlisted files in cases/
    cases_dir = root / "cases"
    if cases_dir.is_dir():
        for root_dir, dirs, files in os.walk(cases_dir):
            for directory in dirs:
                if (Path(root_dir) / directory).is_symlink():
                    raise ManifestVerificationError("symlink directory is prohibited")
            for file_name in files:
                file_full = Path(root_dir) / file_name
                if file_full.is_symlink() or os.path.islink(file_full):
                    raise ManifestVerificationError(
                        f"symlink found in fixture cases directory: {file_full}"
                    )
                rel_to_root = str(file_full.relative_to(root))
                if rel_to_root not in declared_paths:
                    raise ManifestVerificationError(
                        f"unlisted file found in fixture directory: {rel_to_root}"
                    )

    manifest_bytes = manifest_file.read_bytes()
    manifest_digest = hashlib.sha256(manifest_bytes).hexdigest()

    return {
        "verified_members_count": len(declared_paths),
        "manifest_path": str(manifest_file),
        "manifest_digest": manifest_digest,
        "public_contract_id": pub_id,
    }
