# APG141 result-fields decision

Outcome: **REJECTED** for `APGR-REPORT-RESULT-FIELDS`, after supplied independent
review. No producer field changes are made.

## Current contracts and observation

[The Go API](../../../../report/types.go) exposes `report.Result` with `Record`,
`Bytes`, and `Evidence map[string][]byte`. These are transport and normalized
evidence values, with caller-owned storage. They are distinct from
`RequestMetadata.Result`, the caller-owned outcome string rendered into report
metadata. [Validation](../../../../report/validation.go) refuses characters
below U+0020 and U+007F in outcome/final-gate metadata; it does not enumerate
outcomes. Empty metadata is rendered as `NULL`. Type-specific evidence keys
remain owned by their report operation rather than a new global vocabulary.

Dated source observation `APG141-JACA-REPORT-SOURCE-20260912` inspected the
current consumer's report-artifact and report-payload owners. They parse record
framing, project and phase identities, sizes, digests, generated fields and
payload associations. The generated-field parser checks syntax, safety, bounds
and duplicates. It does not establish a reusable closed outcome enumeration
or an allowlist for the APGR in-memory Evidence map. The consumer's prepared,
blocked and failed artifact classifications are its own validation results,
not a producer outcome vocabulary.

[APG140's maintained ownership decision](../../external/apg140/maintenance.md)
already assigns legacy envelope differences to consumer adoption. This phase
does not alter producer fields to disguise that mismatch and makes no fresh
consumer runtime or adoption claim.

## Rationale and consequences

No inspected current consumer establishes a provider requirement to restrict
these fields. A new enumeration would remove valid caller-owned values without
solving the observed envelope mismatch. Existing API ownership, metadata safety,
canonical record validation and append identity/integrity checks meet the
observed provider need. Therefore reject the inherited optional restriction.
This conclusion is bounded to the inspected contracts; a materially different
future consumer request belongs on a new roadmap.

Existing report API/parser/append/operational tests and CLI custom-outcome
publication qualify preservation. No schema, envelope, wrapper or consumer
mutation is needed. No outbox, transaction, scheduling, retry or adoption owner
moves into APGR. Rollback is unnecessary because the provider behavior remains
unchanged; a future restriction requires explicit version/extension/refusal
policy and its own reviewed authorization.
