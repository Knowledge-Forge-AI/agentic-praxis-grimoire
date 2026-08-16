# APG46 Accepted Evidence Guidance Authoring

Phase ID: `APG46`

Evaluation date: 2026-07-26

## Objective and boundary

APG46 authors the smallest coherent implementation candidate for the
recommendations APG45 terminally accepted: REC-01 and REC-02 in the canonical
review skill, and REC-03 and REC-04 in the provenance policy. The exact
accepted inputs are the APG45 evaluation and disposition records and the
frozen APG44 scenarios S01–S41. The candidate is authored on a Claude branch
and is not integrated: the terminal authoring result is
authoring-complete-pending-codex-validation-and-integration, and the stable
review skill on `main` is unchanged at APG45.

A separate external manager review of APG45 supplied refinements that APG46
adopts as authoring input only: plain operational wording instead of
falsifiability jargon, absence claims scoped to the inspected boundary,
counterevidence treated as weighable rather than automatically dispositive, a
single normative REC-03 owner, a discoverability test before any synthesis
pointer, no REC-04 pseudo-schema, and execution gates deferred to the later
Codex phase. That review is manager input, not repository authority, and no
APG45 terminal disposition was rewritten.

## Authored candidate contracts

**REC-01 (review skill).** A new `Material claims and evidence direction`
subsection requires identifying, before disposing a material claim, whether
it is a presently checkable fact, judgment or interpretation, a forecast, or
an assertion with no presently defined check or disconfirming observation;
restating any unstated inference that acceptance would rely on as its own
claim with matching evidence; and keeping this proportional — no claim
ledger, fixed taxonomy, or classification ceremony — without weakening the
fresh resulting-state evidence completion claims already require.

**REC-02 (review skill, same subsection).** When material evidence does not
establish a claim, the review reports evidence direction: no relevant
evidence within the inspected scope (which must be named), relevant but
inconclusive evidence, or evidence weighing against the claim. Missing
support is not refutation; countervailing evidence is weighed rather than
automatically dispositive; established claims gain no added ceremony; and
debugging keeps its existing domain behavior.

**REC-03 (`docs/provenance.md`, sole normative owner).** A new
`Claim-relative source authority` section weighs material evidence by how
directly its inspectable basis bears on the exact claim; lets a first-party
source settle its own formal record while denying interested sources
automatic control over impact, reliability, safety, quality, disputed
interpretation, or contested behavior; treats artifacts reusing one
evidentiary basis as one corroborating lineage while preserving derivative
summaries as discovery aids; keeps corroboration volume claim- and
project-owned; and adopts no universal source tiers and no source-count
minimum.

**REC-04 (`docs/provenance.md`).** A new `Material access limitations`
section adds optional free-prose guidance: when incomplete access could
materially affect a conclusion, record what inspection was constrained and
how that constrained validation, confidence, or the terminal claim, without
exposing protected content, credentials, private paths, machine topology, or
confidential source details; omit the note for complete or immaterial
access. No required field, key, schema, template, validator, source ledger,
scalar independence value, or structured evidence relationship is
introduced, and existing free-prose records remain valid.

REC-05 and REC-07 through REC-10 remain rejected and REC-06 remains
deferred; none re-entered directly or indirectly.

## Scenario expectations and records

Authored resulting-state expectations are frozen for every mapped scenario:
REC-01 supporting S02, S04, S05, S06, S07, S17 with adverse S03, S27, S34,
S39; REC-02 supporting S14, S15, S32 with adverse S27; REC-03 supporting
S08–S11, S17–S20, S24–S26, S28 with adverse S01, S22, S34; and REC-04
supporting S12, S13, S30 with adverse S01, S22, S36, S39. The expectations
preserve S04's independent completion evidence, S27's exemption for fresh
count evidence, and S39's freedom from classification ritual. They are
authored analysis, not executable evidence, and S01–S41 identities are
unchanged. Exact authoring records, the reconciliation, the scenario matrix,
the clean-room review, the cross-owner review, and the complete Codex
handoff remain publication excluded under `private/evaluations/apg46/`.

## Clean-room result

Every candidate sentence was written from the APG45 accepted contracts; the
external source was opened only for the pre-commit copied-expression
comparison. That comparison found two source-shaped draft phrasings — an
access-state word run and a forecast sentence shape — and both were
independently re-expressed before commit. Remaining overlaps are generic
factual identifiers. Derivation mode is independently written synthesis; no
external table, tier ordering, schema, score, mode taxonomy, template, or
output structure is adopted.

## Limitations and pending work

This phase is author self-review only. No test, fixture, probe, integration,
publication, or deployment ran, and no synthesis pointer was added: the
claim that the REC-03 policy is discoverable without one is an author
hypothesis. The later separately authorized Codex phase owns independent
object verification, failing-first executable contracts, the
policy-discoverability probe (with at most one concise non-normative
application pointer in `synthesizing-repository-guidance` only on a material
probe failure), one coherent forward correction cycle, stable-skill and
repository regression gates, mainline integration through exact ancestry,
push, and managed reports.

## State

Integrated development remains 28 canonical skills, 28 catalog rows, and 28
projections with unchanged maturity, routing, release policy, test
inventory, executables, and dependencies. Public and active remain the
corrected v0.4.0 at 28/28/28. `main` did not move. No Go or web workstream
began, and no successor phase is authorized.

## Subsequent APG47 disposition

APG47 later verified and delivered the exact APG46 object without rewriting
it, recorded failing-first evidence, corrected the judgment/advice and
counterevidence defects forward, and retained REC-01 through REC-04 after
independent review and complete stable-skill gates. The provenance policy
remains the sole normative owner, no synthesis pointer was needed, and APG46's
authoring-only facts remain unchanged.
