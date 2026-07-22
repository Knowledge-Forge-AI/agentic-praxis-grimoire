# ADR 0015: Semantic Phase Identity and Record Finalization

## Status

Accepted

## Date

2026-07-21

## Acceptance authority

The human maintainer's APG19A assignment directly accepts this decision and
authorizes its policy, documentation, deterministic checker, APG19 identity
reconciliation, and one evidence-backed Bats correction. It does not authorize
public release, application smoke, distribution broadening, maturity change,
root-guidance migration, private-skill removal, or a phase after APG20.

## Context

APG already used phase names, ADR numbers, exit numbers, Git commits, releases,
source versions, and content digests for different purposes, but their identity
boundaries were not complete. Some publication-excluded records treated exact
Git objects or content hashes as durable state identities. Exit and ADR
mechanics described independent sequences, but no single owner stated that
numeric equality across those namespaces is valid. Phase records were also
completed partly after commits in earlier work, allowing a transient mismatch
between implementation and current documentation.

Commit-derived phase identity is circular: the phase needs a stable identity
before it can finalize its evaluation, exit, and commit. Exact Git objects are
valuable execution evidence, but they are unsuitable semantic names for the
decision or state described by tracked documents.

## Decision

### Semantic phase identity

A phase ID is assigned before implementation and is the durable semantic
identity of one bounded phase. Canonical spelling is uppercase. Existing forms
such as `APG19`, `APG19A`, and `APG-TEST0` remain valid. Phase IDs are globally
unique, compared case-insensitively, and never reused after any terminal
disposition, supersession, or revert.

The same canonical phase ID appears in the phase evaluation, exit, roadmap,
managed-report `phase` field, and final response. A commit does not assign or
change the phase ID.

### Independent record namespaces

ADR and exit sequences remain independent:

- ADR numbers are unique only within `docs/adr/` and use four digits.
- Exit numbers are unique only within `docs/status/` and use five digits.
- Numeric equality between an ADR and an exit is permitted and is not a
  collision.
- Phase-ID allocation is independent of both record sequences.
- A phase may create an exit without an ADR, and an ADR does not allocate a
  phase ID.

The next ADR and exit values are computed separately from the greatest assigned
value in each namespace. Every exit is indexed exactly once. For records from
exit 00029 onward, the lowercase phase token in the path and canonical phase ID
in the status index, H1, and explicit `Phase ID` field must agree.

### Durable reference forms

Tracked public and publication-excluded documents use semantic identifiers:
phase IDs, ADR IDs, exit IDs, release versions, external source versions or
revisions, and stable phase-local evidence IDs. Content digests may verify bytes
transiently but do not identify a phase, source decision, baseline, migration,
or cross-document owner.

Internal APG and maintainer-project commit hashes are not durable identities in
tracked documents, including `private/`. Exact Git IDs remain in
machine-generated Git reports, schema-valid operational reports, and transient
execution evidence owned by the applicable reporting or verification process.
They are not copied back into tracked documentation.

External provenance prefers an official release, version, tag, specification
revision, or date. If no meaningful semantic revision exists, the record uses a
stable phase-local source ID, a public locator, an inspection date, and an
explicit mutability or revision limitation. APG does not invent immutability.

This decision narrows ADR 0001's treatment of exact publication-excluded
identity evidence. Exact Git objects remain valid report evidence, but they no
longer serve as durable tracked-document identities.

### Subsequent APG24 clarification

APG24 preserves the semantic-identity rule while clarifying the evidence
location. Exact Git objects may be retained in tracked publication-excluded
reproducibility records when a human-authorized phase explicitly permits them.
They remain evidence rather than durable phase or public project identity, and
public records cannot depend on them or on `private/`. This does not change the
precommit finalization rule.

### Pre-commit record finalization

Before a phase commit, the implementation, current-owner documentation,
roadmap, provenance, integration documents, evaluation, exit, applicable ADR,
and indexes describe the actual resulting tree. A fresh non-author review and
deterministic identity checks run before staging; the complete staged diff and
staged checks run before commit.

Managed Git and operational reports are necessarily generated after commit
because they include the resulting Git identity. They do not excuse incomplete
tracked documentation or an exit that promises required precommit work later.

Historical facts remain truthful to their original collection. A later policy
or correction is recorded forward in a subsequent evaluation, ADR, or exit
rather than rewriting history as though the later rule always applied.

### Mechanical checks

`apg-check-record-identity` validates exit-index coverage and exactness,
independent ADR and exit uniqueness, case-insensitive phase uniqueness,
canonical spelling and new-record agreement, explicit phase-allocation
expectations, and independently computed next values. Passing proves only this
mechanical subset. A focused changed-file and current-owner review checks
durable hash usage because a repository-wide hexadecimal ban would confuse
licenses, fixtures, generated evidence, and valid report-owned objects with
semantic references.

## Alternatives considered

### Continue using commits as private identities

Rejected. Publication exclusion does not make an implementation object a
stable semantic name, and tracked private records still participate in project
history and current-state reasoning.

### Derive phase identity from commit identity

Rejected. The phase must be named before its evaluation, exit, and commit can
be finalized, so commit-derived identity is circular and unstable during
implementation.

### Use one global counter for ADRs and exits

Rejected. Decisions and phase outcomes are different record classes with
independent lifecycles.

### Compare ADR and exit numbers

Rejected. Their widths, purposes, and allocation rules differ. Equality across
the two namespaces carries no semantic meaning.

### Use semantic phase IDs with independent sequences

Accepted. It gives work a stable precommit identity while preserving each
record class's own mechanics.

### Finalize documentation after commit

Rejected as the normal phase workflow. It knowingly commits an inconsistent
current state and creates avoidable corrective phases.

### Finalize documentation before commit

Accepted. The commit contains one internally consistent resulting state, while
post-commit reports retain exact Git evidence in their proper owner.

## Consequences

Future phases allocate semantic phase IDs before implementation, compute ADR
and exit numbers independently, and finish tracked records before commit.
Tracked documents become less coupled to repository topology and Git history;
managed reports remain exact execution evidence.

Every new exit needs an explicit phase field and agreement across its path,
index, and H1. The new checker and public-release surface add a small
standard-library maintenance cost. Semantic review remains necessary because
the checker cannot determine whether a source version, phase disposition,
evaluation, or completion claim is truthful.

## Migration and rollback

APG19A corrects current owners and APG19's durable identity anti-patterns
forward while retaining substantive APG19 dispositions. Historical managed
reports and unrelated older records are not rewritten. Removing this policy
would require a superseding ADR, corresponding guide and instruction changes,
and explicit disposition of the checker and all records that depend on it.
