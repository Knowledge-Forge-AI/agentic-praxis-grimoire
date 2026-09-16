# APG140 Bounded Synthetic APGR Consumer Fixtures

## Overview and Authority Boundary

This directory contains bounded synthetic consumer fixtures and compatibility admission controls
for external graph presentation envelopes. A separate two-field ASYNC1 negotiation
projection checks only the fixed supported-version observation; no worker state
machine, authentication or coordinator execution is qualified.

- **Observed Public Contract ID**: `APG140-RM-MAIN-20260912`
- **Source-Bound Observation Date**: `2026-09-12` (source `main` observed state)
- **Governing Public Contracts**:
  - `docs/specs/public-read-contract.md` (clauses: ARCH7A1, ARCH7A2, Version 1 Envelope, Version 1 Embedded Envelope, Bounds And Ordering, CLI Contract, MCP Contract)
  - `docs/specs/durable-job-and-coordinator-contract.md` (clauses: ADR 0039, ASYNC1-CLOSE, Versioned Request Envelope, Durable State Machine)

### Critical Governance and Admission Status

1. **APGR-Local Evidence Admission ONLY**: This independently authored consumer implementation provides
   APGR-local evidence admission only. It does **not** constitute, certify, or claim Repo Map runtime conformance.
2. **Zero Copied Source**: These fixtures and test utilities are independently authored from inspected
   specification documents. No source code was copied or extracted from Repo Map.
3. **No Private Paths or Revisions**: All contract identities, test cases, and diagnostic descriptors
   use public-safe identifiers. No private workspace roots, private git revisions, internal database
   connection strings, credentials, or volatile process identities appear in these public fixture files.

---

## Supported Capabilities

### 1. Strict Wire Version Selection
- Only wire versions `0` and `1` are accepted.
- Boolean schema versions (e.g. `True`, `False`) are strictly refused with dedicated validation errors.
- Other integer versions (e.g. `2`, `-1`) and non-integer representations (strings, floats) are refused.

### 2. Version 0 Legacy Bounded Array
- Version `0` admits bounded legacy JSON arrays (`[ { ... }, ... ]`).
- **Completeness Limitation**: A legacy bounded array cannot prove completeness, snapshot isolation,
  or exhaustiveness across multiple requests.

### 3. Version 1 Presentation Envelope
- Direct lists (`canonical_nodes`, `canonical_edges`) require the Version 1 envelope:
  `{"schema_version": 1, "result_kind": ..., "items": [...], "page": {...}, "diagnostics": [...]}`.
- Embedded collections (`canonical_neighborhood`, `canonical_edge_explanation`) require:
  `{"schema_version": 1, "result_kind": ..., "result": {...}, "collections": {...}, "diagnostics": [...]}`.
- Bounded paging validation:
  - `limit`: Integer in range `[1, 200]` (default 50).
  - `offset`: Non-negative integer (default 0).
  - `returned`: Non-negative integer, exactly equal to `len(items)`, and `<= limit`.
  - `truncated`: Boolean flag.
  - `next_offset`: Integer equal to `offset + returned` when `truncated=true`; `null` (`None`) when `truncated=false`.
- Diagnostic consistency:
  - When `truncated=true`: Diagnostics must contain `{"code": "result_truncated", "message": "additional results are available"}`.
  - When `truncated=false`: Diagnostics must not contain `result_truncated`.

### 4. Policy-Driven Fail-Closed Envelope Validation
- Unknown envelope fields fail closed with an explicit error identifying this as an **APGR selected admission policy**
  (not an external owner mandate).
- Partial/missing fields in the envelope or page descriptor fail closed.

### 5. Completeness and Snapshot Isolation Bounds
- Truncated pages cannot prove a complete graph.
- Continuation across pages assumes the selected graph does not mutate between requests; the contract does
  **not** claim cross-request snapshot isolation.

### 6. Adverse and Refusal Cases
- **Malformed JSON**: Syntactically invalid payloads are rejected safely.
- **Partial fields**: Missing required envelope or page fields fail closed.
- **Identity drift**: The caller supplies expected bindings (e.g., expected `result_kind`, `public_id`,
  `wire_version`) separately from the presentation envelope. Any drift is detected and rejected.
- **Caller-owned refusal**: Caller can refuse consumption if pre-conditions fail.
- **Pre-consumption cancellation**: An explicit cancellation request before consumption returns a distinct
  error (`FixtureCancellationError`) with zero side effects.

### 7. Source-Bound Synthetic Graph Checker
- Compares independently provided expected nodes, directed edges (source key, edge kind, target key,
  identity metadata hash), and provenance against observed graphs.
- Detects matches, missing elements, spurious elements, duplicates (dedup tracking), and metadata conflicts.
- **Cycle tolerance**: Accepts directed cycles cleanly (e.g. `A -> B -> C -> A`) without recursion errors.
- **Provenance separation**: Separates provenance quality (evidence linking, generation alignment) from
  storage claims (presence of canonical node/edge records).

### 8. Fixture Cases Manifest Verification
- `manifest.json` specifies all test cases with SHA-256 byte digests and byte lengths.
- Verifier validates:
  - Exact member set: No unlisted files and no omitted files.
  - Byte integrity: Re-computes SHA-256 digests over member bytes.
  - Security controls: Strict rejection of path traversals (`..`, absolute paths) and symlinks.

---

## Explicit Scope Limits

- **Bounded Consumer Only**: This fixture package is an admission consumer and verification suite. It is
  **not** a Repo Map protocol server, SQL query compiler, or async coordinator implementation.
- **No Network or Database Calls**: All operations run locally and synthetically in-process without network
  transports or live database instances.
- **No Copied Code**: Cleanroom implementation adhering strictly to standard Python 3 libraries.
