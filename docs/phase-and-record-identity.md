# Phase and Record Identity

## Purpose

This guide implements [ADR 0015](adr/2026/07/0015-semantic-phase-identity-and-record-finalization.md).
It owns APG's semantic phase identity, independent ADR and exit sequences,
durable reference forms, and precommit record-finalization procedure.

## Phase IDs

A phase ID names one bounded phase before implementation begins. Accepted forms
are:

```text
APG<number>
APG<number><uppercase-letter-suffix>
APG-TEST<number>
```

Examples include `APG19`, `APG19A`, `APG20`, and `APG-TEST0`. Canonical
spelling is uppercase. Comparison is case-insensitive so a lowercase or
mixed-case spelling cannot allocate a second phase. A phase ID is globally
unique across APG history and is never reused after complete, partial, blocked,
rejected, superseded, reverted, or other terminal work.

Use the same canonical phase ID in:

- the phase evaluation and roadmap entry;
- the exit path token, status-index label, H1, and explicit phase field;
- managed Git and operational report phase or ticket fields; and
- the final response.

The path token is the lowercase filename form of the canonical phase ID. New
exit records declare exactly one field:

```text
Phase ID: `APG20`
```

The phase ID is assigned before implementation and does not depend on a commit,
ADR, or exit number.

## ADR and exit namespaces

ADR and exit numbers are separate identifiers:

```text
docs/adr/YYYY/MM/NNNN-<slug>.md
docs/status/YYYY/MM/DD/NNNNN-<phase>-<slug>-exit.md
```

ADR numbers are unique within `docs/adr/`. Exit numbers are unique within
`docs/status/`. Compute the next number by adding one to the greatest assigned
number in that same namespace. Never compare the two sequences. ADR 0001 and
exit 00001 may coexist without collision.

A phase can have an exit without creating an ADR. An ADR can apply across
several phases and does not consume a phase ID. Once allocated, ADR, exit, and
phase identifiers remain stable and are not reused.

Every exit file is indexed exactly once. For exit 00029 and later, all of these
must agree:

1. the sequence and lowercase phase token in the path;
2. the sequence and canonical phase ID in the status-index label;
3. the canonical phase ID in the H1; and
4. the explicit `Phase ID` field.

## Durable references

Tracked APG documents, including publication-excluded records, identify durable
state with semantic references:

```text
APG19
ADR 0014
exit 00028
public v0.2.0
bats-core v1.13.0
APG19-BATS-DOGFOOD-01
```

Do not use an internal APG or maintainer-project Git object as a phase,
baseline, current-state, migration, rollback, or cross-document identity.
Content digests may be transient byte-verification evidence, but they do not
become durable phase, source-decision, or candidate identities.

Exact Git IDs ordinarily belong in machine-generated Git reports, schema-valid
operational reports, and transient verification output. An explicitly
authorized publication-excluded reproducibility record may also retain them,
but they remain evidence rather than canonical phase, baseline, migration, or
public project identity. Public records must not depend on `private/` or require
those objects for semantic interpretation.

For an external source, prefer an official semantic version, release, tag,
specification revision, or date. When none exists, assign a stable phase-local
source ID, cite a public repository or document locator, state the inspection
date, and describe the source's mutable or unversioned limitation. Do not claim
that a mutable branch or page is immutable.

## Precommit finalization

After implementation and focused tests are otherwise final, complete this
sequence before commit:

1. update every current owner affected by the phase;
2. update roadmap, provenance, catalog, capability, and integration documents;
3. finalize the phase evaluation, exit, applicable ADR, and both indexes;
4. scan current owners and changed tracked files for stale state and durable
   internal or maintainer-project commit-hash references;
5. run `apg-check-record-identity` with explicit allocation expectations;
6. run a fresh non-author resulting-tree and record review;
7. resolve material findings;
8. stage the complete implementation and documentation together;
9. inspect the complete staged diff and rerun staged identity and whitespace
   checks; and
10. commit only after the staged tree is internally consistent.

The focused hash review examines changed files and current-state owners. It is
not a naive repository-wide ban on forty hexadecimal characters: licenses,
fixtures, historical raw evidence, and report-owned objects can legitimately
contain such values. The review asks whether a hash is being used as a durable
semantic identity in a tracked document.

Git and operational reports are generated only after commit. Their required
post-commit timing does not defer any tracked-document finalization step.
Authorized publication-excluded records mark genuinely postcommit facts as
pending rather than fabricating them in the release-source tree.

## Subsequent corrections

Preserve the truth of historical records. If a later phase changes policy,
finds a material defect, or replaces a durable identity form, record the change
forward in the later evaluation, ADR when required, and exit. Do not rewrite an
older record to imply that later evidence or policy existed at its original
collection time.

A focused correction may update a current owner or remove a now-invalid durable
reference from an older evidence record. The subsequent correction record must
state what changed and why while preserving the older phase's substantive
disposition unless new evidence actually changes it.

## Mechanical validation

Run:

```text
bin/apg-check-record-identity [--root <path>] [--format text|json]
  [--expect-available <phase>] [--expect-allocated <phase>]
```

The expectation options are repeatable. Exit `0` means the mechanical identity
subset passed, exit `1` reports noncompliance, and exit `2` reports invalid
usage or an unreadable root. The command is read-only and uses only the Python
standard library.

It verifies indexed exit existence and exact coverage, independent ADR and
exit uniqueness, case-insensitive phase uniqueness, canonical spelling,
new-record path/index/H1/field agreement, explicit allocation expectations,
and independently computed next ADR and exit values. Passing does not establish
authority, semantic accuracy, provenance truth, evaluation quality, review
quality, report validity, or phase acceptance.

## Examples and non-examples

| Purpose | Use | Do not use |
| --- | --- | --- |
| Phase identity | `APG19A` | an APG development commit hash |
| Architecture reference | `ADR 0015` | an exit number treated as the ADR number |
| Phase outcome | `exit 00029` | a number selected by comparing ADRs and exits |
| Release state | `public v0.2.0` | the public repository's current commit hash |
| Versioned external source | `bats-core v1.13.0` | a source commit when the release identifies it |
| Unversioned external source | phase-local source ID, public locator, date, and limitation | invented immutable revision |
| Dogfood evidence | `APG20-GO-DOGFOOD-01` | a file digest used as the case identity |
| Exact Git evidence | managed report or explicitly authorized publication-excluded reproducibility record | a hash used as durable public identity |
