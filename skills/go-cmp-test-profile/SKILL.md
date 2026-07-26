---
name: go-cmp-test-profile
description: Use when a repository has already selected google/go-cmp v0.7.0 and comparison judgment is material to equality versus diff, option composition and filters, comparers and transformers, ignores and unexported fields, sorting, approximation, panics, diagnostic exposure, or thresholds beyond repository policy.
---

# go-cmp Test Profile

## Core principle

Apply go-cmp judgment only after the repository has already selected the
dependency and the task materially depends on semantic comparison. This profile
is calibrated to release `v0.7.0`. Confirm the selected release before relying
on any behavior claim below; a different release requires a source refresh. Use
the highest justified `Green — routine`, `Yellow — caution`,
`Orange — warning`, or `Red — crisis / stop` response for the current coherent
decision.

Own equality versus diff, option composition and filtering, custom comparers
and transformers, ignoring and unexported-field boundaries, sorting and
approximation contracts, ambiguity and panic conditions, and diagnostic
exposure. Leave native lifecycle, subtests, cleanup, and parallelism to a
retained `go-test-profile`, and leave terse local expectations to explicit
project-owned assertion policy.

## Do not use

Do not use this profile for:

- deciding whether to adopt go-cmp, which is project-owned;
- a repository that has not selected the dependency;
- a selected release other than the calibrated one, until the option, sorting,
  approximation, and panic claims are reverified against that release;
- native test lifecycle, subtests, cleanup, or parallelism, owned by a retained
  `go-test-profile` or project-owned native test policy;
- terse local assertions, owned by project-owned assertion policy;
- production equality, hashing, or ordering design for shipped types;
- general Go semantics already owned by `go-language-profile`;
- generic implementation, debugging, planning, or review procedure;
- selecting commands, flags, coverage thresholds, CI, or dependency versions; or
- authorizing live services, host mutation, credentials, or destructive action.

## Procedure

1. Establish task authority, repository policy, the exact selected release, the
   compared types, the option set in scope, exact checks, and rollback.
2. Confirm the release matches the calibration. If it does not, stop and
   reverify option, sorting, approximation, unexported, and panic behavior
   against that release's source before continuing.
3. Determine the exact semantic contract each comparison must protect, and
   which differences must remain detectable.
4. Inspect equality versus diff use, option composition and filter scope,
   comparer and transformer properties, ignore breadth, unexported-field
   handling, sorting contracts, tolerance justification, panic and ambiguity
   risk, and diagnostic content.
5. Assign the highest level justified by a concrete risk in the structural
   contract below. Coupled signals may explain one higher-level risk, but their
   count never manufactures Orange or Red. One semantic Red remains Red.
6. Proceed proportionally for Green; inspect policy and evidence for Yellow;
   require an accepted local design, rationale, rollback, and focused
   validation for Orange; stop a Red hidden-behavior, nondeterminism, ambiguity,
   ownership, or exposure condition.
7. Pair independently with a process skill and, only when material, with a
   retained `go-test-profile`. No chain is mandatory; when that owner is
   unavailable, use explicit project-owned native test policy.
8. Preserve stricter repository policy. Never relax a superior safety, privacy,
   truthfulness, or authority stop.
9. Report level, signals, release assumption, option set, detectability
   evidence, exception if any, and rollback.

### Equality, diff, and diagnostics

The equality function supplies a boolean comparison without producing a value
report. The diff function instead constructs a value-rendering diagnostic;
when it has no difference to report, its result is empty. Computing both for
one assertion often duplicates work and is Yellow on proportionality unless
the caller has two independently stated needs.

Treat diff text as human-facing diagnostic output whose layout can change.
Exact-text assertions and parsers are unsupported; use a reporter when a
program needs structured comparison events.

Classify protected data before a rendering call or user option side effect.
Filtering alone does not redact values. Ignoring or transforming a protected
field changes what the comparison can detect and is permitted only when the
required equality contract remains truthful. A sensitive diff must not reach a
durable log, artifact, or report. When a diagnostic is withheld, report that
fact without implying a reviewer inspected the hidden values.

### Comparers, transformers, and filters

For every pair a custom comparer accepts, reversing the arguments must preserve
the judgment, repeated calls must not drift, and the call must neither change
its inputs nor produce observable side effects. Violating any of those
obligations is Red.

Treat transform self-application as locally guarded: comparison will not keep
feeding one transform back into itself through an unbroken chain of
transformations. That branch-level protection says nothing about cycles formed
by several transforms. When output can re-enter the transform's own input
domain, select the acyclic constructor and state the domain boundary. Do not
generalize one constructor's guard to all transforms.

Path and value predicates bound where an option applies. Structural traversal
can call a path predicate when an indexed or keyed value exists on only one
side, so swapping the comparison operands must not change the predicate's
decision. A value predicate likewise must return the same decision after an
operand swap and across repeated calls.

When more than one comparer or transformer applies to one value, comparison
panics on an ambiguous option set; composition must be disambiguated by
filters. An `Ignore` option passed without a filter also panics. Both are Red
until resolved.

### Ignoring and unexported fields

Record every ignored field or type and confirm none carries behavior the test
exists to protect. An ignore that hides required behavior is a Red truthfulness
stop, and a growing ignore set is a signal that the compared type or the test's
contract needs review rather than more options.

Comparison panics when a struct contains unexported fields unless an ignoring
option excludes them or an exporting option explicitly permits them. Keep the
three responses distinct:

- **Ignoring.** The narrow ignore option excludes immediate unexported fields
  of the specified types. It can be Green or Yellow when an explicit stable
  contract proves the fields carry no required behavior; hiding required
  behavior is Red.
- **Allow-style access.** Forcibly introspecting unexported fields of named
  struct types reaches into those types' representation. Orange.
- **Exporter-style access.** A predicate can permit access for a broader set of
  types. Classify it by the concrete ownership and compatibility boundary.
  Reaching external representation across an unaccepted boundary is Orange or
  Red, but predicate form alone does not determine that result.

Do not normalize bypassing unexported fields as routine. Prefer comparing an
exported projection the owner guarantees.

### Sorting contracts

The two sorting transformers have **different** ordering requirements. Do not
merge them.

- **Slice sorting** requires a consistent relation without self-precedence or
  broken chains: if one value precedes a second and the second precedes a
  third, the first must precede the third. Distinct values may still share one
  rank. Their prior order is then preserved, so comparison can remain sensitive
  to input order.
- **Map sorting** must additionally distinguish every unequal key through the
  ordering relation. The helper panics when the relation cannot do so.

Claiming a total order is required for slice sorting is Red. Relying on slice
sorting to normalize elements the ordering treats as equivalent is Red when the
comparison result must be order-independent.

### Approximation

Approximate float comparison takes a relative fraction and an absolute margin,
and it panics when either parameter is negative or NaN. It does not apply when
an operand is NaN or infinite, so operand handling is a separate decision; a
separate option can equate NaN values. Approximate time comparison applies to
non-zero time values and panics on a negative margin.

The error-equating option implements the standard matching relation used by
`errors.Is`; that is not exact identity. When exact identity is the required
contract, use an exact project-owned comparison. The any-non-nil error sentinel
is Red when a particular error must be distinguished.

State these as the release's API facts. Do not present advice-level wording —
such as calling a tolerance "small enough" or "reasonable" — as an API rule. A
tolerance chosen to make a test pass, rather than justified by the domain, hides
a consequential difference and is Red.

### Structural threshold contract

Measure per **coherent comparison owner** — one comparison call site or one
comparison helper and the option set it applies — not per test file. Canonical
upstream option tests for this release compose as many as seven options in a
single comparison and use three or more options in many cases, so a small
per-file total is not evidence of safety and a large per-file total is not
evidence of risk. Summing unrelated comparisons across a file false-escalates
several independent, small, disjoint option sets that carry no aggregate
composition risk. Numeric per-file cutoffs are therefore not used here.

| Signal | Green — routine | Yellow — caution | Orange — warning | Red — crisis / stop |
| --- | --- | --- | --- | --- |
| Options in one comparison owner | few, each independently justified | several, with one shared purpose | a set no reviewer can evaluate as a whole | composition is ambiguous or panics |
| Comparer and transformer families | none, or one documented rule | two disjoint domains | overlapping domains bounded only by ordering | properties violated, or applicability ambiguous |
| Filter layers on one option | none needed | one explicit predicate | nested predicates that obscure scope | scope cannot be stated |
| Ignored field and type breadth | none, or one justified exclusion | a few independently justified | breadth that makes detectability unclear | required behavior is hidden |
| Unexported handling | not needed, or exported projection compared | narrow ignore of immediate fields | allow- or exporter-style access to owned types | access across an unaccepted external boundary |
| Comparison-helper layering | comparison at the call site | one helper with a stated contract | layered helpers spanning domains | the protected contract cannot be identified |
| Semantic domains per helper | one | two, each explicit | several unrelated domains | a domain's rules silently apply to another |

Inspect a comparer, transformer, or ignore family by the distinct domain or
independently justified exclusion it governs, not by call-site totals. Inspect
filter nesting around each option and each independently meaningful semantic
domain without turning either into an escalation counter.

Separate the subject under test from the harness. Expected-panic and
adverse-option cases that prove the protected behavior are not defects in the
test owner. Escalating on option or domain count alone is a defect. Every
Orange or Red must name a detectability, determinism, ownership, or exposure
risk.

### Source and maintenance boundary

This profile was corrected and calibrated on 2026-07-25 from the canonical
`v0.7.0` sources for the comparison and option surfaces, the sorting and
equating helpers, and the release's own option tests. The library is
BSD-3-Clause licensed. The procedure is independently worded and uses factual
API identifiers.

Refresh before a behavior-bearing correction, maturity review, or publication
when the selected release changes, or when the option set, comparer
obligations, transformer filtering, unexported handling, sorting or
approximation contracts, or documented panic conditions materially change.
Removal is candidate-independent but must delete the canonical leaf, checked
projection, catalog and capability-map entries, current-development
release-policy entry, strict inventory entry, focused tests, and public
fixture. It must repair surviving cross-references with the retained owner or
project-owned fallback while preserving ADR, evaluation, and exit history.
Removal does not add, remove, or change the project's dependency.

## Project-owned parameters

The repository owns whether the dependency exists at all, its exact version and
upgrade policy, domain adapters and option packages, tolerance policy, ignore
policy, protected-data classification and redaction rules, comparison helper
design, exact commands, flags, coverage thresholds, CI, accepted exceptions,
authority, validation, and rollback.

## Evidence and completion

When material, report the profile level, structural and composition signals,
the exact release assumption, the option set and what each option removes from
detection, determinism evidence, diagnostic and redaction handling, exception
if any, and rollback. State plainly which differences the comparison can no
longer detect. Orange requires an accepted local design and focused
adverse-case evidence. Red records the stopped hidden-behavior, nondeterminism,
ambiguity, ownership, or exposure condition and the condition required before
reconsideration.

## Stop or escalate

Stop or escalate when reversing a comparer changes its answer, repeated calls
drift, or a comparer modifies operands or observable state; when a comparison
is nondeterministic; when an ignore
hides required behavior; unexported access bypasses another type's ownership or
an unaccepted compatibility boundary; a transformer recurses or broadens the
comparison domain unsafely; option composition is ambiguous or panics; a
tolerance hides a consequential difference; protected values can enter a
comparison or its output; an unsupported release, option, or domain behavior is
represented as verified; mocked comparison is described as integration
evidence; or crisis-level comparison ownership lacks decomposition or an
accepted bounded exception.

## Common mistakes

- Applying this profile before the repository has selected the dependency.
- Assuming a different release behaves like the calibrated one.
- Requiring a total order for slice sorting, or merging the two sorting
  contracts into one rule.
- Expecting slice sorting to normalize elements its ordering calls equivalent.
- Treating a transformer's implicit filter as general recursion protection.
- Generalizing one helper's containment to every transform.
- Passing an unfiltered ignore option, or leaving two comparers applicable to
  one value.
- Normalizing allow- or exporter-style unexported access as routine.
- Stating advice-level tolerance wording as an API rule, or ignoring the
  documented NaN, infinity, zero-time, and negative-parameter behavior.
- Asserting on diff text or treating the report format as stable.
- Letting a diff render protected values, or withholding diagnostics without
  saying so.
- Counting options across a whole test file as one comparison owner.
- Inventing project commands, versions, or action authority.
