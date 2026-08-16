# APG48 Go Test-Harness Dogfood and Candidate Authoring Exit

Phase ID: `APG48`

Status date: 2026-07-27

## Status

Complete — matryer/is candidate authored and Go stack not authored for lack of
independent value; Codex validation pending

## Scope and result

APG48 opened v0.5 Workstream 2 from the exact APG47 base: bounded read-only
dogfood in five public Go repositories under the APG47 evidence discipline,
with per-clone remote-equality verification and per-clone direct-versus-
indirect dependency verification. The `matryer-is-test-profile` candidate is
authored on the Claude branch (`authored-pending-codex-review`): exact
v1.4.1 calibration, a three-part selection-and-version trigger that excludes
indirect and checksum-only presence, all eight historical defect families
closed at authoring time, and twenty-four frozen scenario families
APG48-IS-01 through APG48-IS-24. The `go-testing-stack` candidate is not
authored (`not-authored-no-independent-value`): the eight-part
stack-evidence gate failed on fresh five-repository evidence, and zero
contradictory-owner-answer cases were observed. ADR 0030 is Proposed with no
current architecture change; ADR 0025 remains Rejected, ADR 0026 Accepted
and controlling, ADR 0027 Rejected. See the
[APG48 evaluation](../../../../evaluations/apg48-go-test-harness-dogfood-and-candidate-authoring.md).

```text
integrated current skills:
  28

candidate leaves on authoring branch:
  1 (matryer-is-test-profile), plus 1 candidate specification

catalog/routes/projections/tests:
  unchanged and not added

public and active:
  corrected v0.4.0 unchanged

successor:
  not authorized
```

## Validation

Authoring-safe checks only: clean exact APG47 base and branch scope; dogfood
read-only preservation with per-clone identity and remote-equality records;
source, version, rights, and access-ledger completeness including the
recorded fetch-summarized canonical-source limitation; bounded sample limits
(twelve deep-read files, ten packages); cross-repository matrix and
stack-gate completeness; historical defect-closure completeness; candidate
frontmatter and canonical headings; twenty-four-scenario continuity; no
placeholder stack artifact; ADR statuses unchanged; no retained-profile or
integration-surface edits; 28/28/28 integrated claims; clean-room
copied-expression, privacy, and personal-data review; public/private
independence; Markdown and local links; record identity; whitespace and
complete staged-diff review; and the formal APG48 commit-message gate.

APG unit, integration, combined, readiness, and smoke suites; Go tests,
builds, benchmarks, fuzzing, race, coverage, generators, linters, and
package commands; target-repository tests; Node and web commands; and
release, publication, and deployment were not run. Those gates belong to
later separately authorized phases.

## Next authorization

No successor is authorized. A future maintainer decision may authorize Codex
APG49 to verify the exact APG48 object and dogfood claims, independently
re-read the canonical sources and repositories, create executable fixtures
and exact-version probes with failing-first evidence, apply one coherent
forward correction cycle, decide ADR 0030, integrate only retained
candidates, and run the complete repository gates.

## Subsequent disposition

APG49 later completed that separately authorized review. New material defects
after the single correction pass required `deferred-material-defect`; current
candidate surfaces were forward removed and ADR 0030 was Rejected. ADR 0026
remains controlling and the no-stack result remains current. This note changes
no APG48 authoring-time evidence or validation claim.
