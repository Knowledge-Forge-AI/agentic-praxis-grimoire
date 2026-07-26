# APG39 matryer/is and Nix Final Redesign Evaluation

Phase ID: `APG39`

Evaluation date: 2026-07-26

## Objective and accepted starting state

APG39 authors narrowly corrected final replacement candidates for the two
profiles APG38 deferred, proposes one conditional architecture record, and
hands a complete integration package to a later separately authorized Codex
phase. It is an authoring phase: it integrates nothing, runs no project or
upstream test suite, executes no Go or Nix surface, and validates no
candidate.

APG38 is accepted as complete and correct. Every APG38 decision is
preserved: `go-test-profile` and `go-cmp-test-profile` remain
retained-provisional and unchanged; ADR 0026 remains Accepted and
controlling for those two owners; ADR 0025 remains Rejected;
`go-testing-stack` remains rejected and absent. The APG38
one-correction-cycle deferrals are honored process boundaries, not
repository defects; APG39 is a separately authorized fresh authoring phase
that closes only the corrected-state defects those deferrals recorded.

## Two replacement candidates

| Candidate | Scenario families | Authoring disposition |
| --- | ---: | --- |
| `matryer-is-test-profile` | 24 | `authored-pending-independent-review` |
| `nix-test-profile` | 40 | `authored-pending-independent-review` |

Both candidates preserve every successful APG38 correction and close only
their corrected-state defects:

- the matryer/is candidate replaces depth-based wrapper severity with a
  registration-completeness and contract-coherence model, in which a fully
  registered nested wrapper chain that reports the actionable contract may
  remain Green, and replaces count-based relaxed-mode escalation with a
  causality model in which no assertion or continuation count alone
  produces Orange or Red; and
- the Nix candidate states the exact-source sandbox defaults separately for
  Linux and FreeBSD — both enabled, with namespace and jail implementations
  distinguished — leaves other platforms default-disabled with no
  unverified further claim, and makes the actual project and host
  configuration controlling over any default, which becomes orientation
  evidence only.

All 24 and 40 APG37 predecessor families map to APG39 successors, and every
APG38 correction family is explicitly mapped. Both structural models are
categorical: every Orange or Red requires a named concrete risk, and
counterexamples demonstrate that nesting, count, size, node count, matrix
size, and expense alone never escalate.

## Proposed ADR 0027

[ADR 0027](../adr/2026/07/0027-version-bounded-matryer-is-go-test-component.md)
is **Proposed**. It records, conditionally, that a later Codex phase
retaining the matryer/is candidate would add it as a third independent,
exact-version-bounded, optional Go component; that ADR 0027 would then
supersede ADR 0026 only as the complete current Go owner-graph record while
preserving every still-valid ADR 0026 decision; and that no stack or
mandatory chain returns. If the candidate is not retained, ADR 0027 should
be Rejected and ADR 0026 remains controlling. ADR 0026 is not altered,
superseded, or reopened during APG39. No Nix ADR was created: no
consequential architecture decision appeared that the project model and the
Nix specification cannot own.

Two candidate specifications accompany the leaves:
matryer/is and
[Nix test](../specs/nix-test-profile.md).

## Source and rights

| Family | Exact state | Rights |
| --- | --- | --- |
| matryer/is | tag `v1.4.1`, reverified 2026-07-26 as the newest upstream tag | MIT |
| Nix | tag `2.35.1`, reverified 2026-07-26 as the newest upstream release | LGPL-2.1-or-later |
| Nixpkgs | 26.05 line at the exact APG38-pinned commit | MIT, component exceptions |
| NixOS | 26.05 system-test documentation at the same pinned commit | MIT, component exceptions |

Every behavior-bearing fact was reverified against these exact sources on
2026-07-26; preserved APG38 facts are marked as preserved rather than
re-derived. One source discrepancy is recorded: the sandbox setting's own
descriptive text lags its implementation conditional, and implementation
plus release notes are treated as controlling. All APG text is independently
written synthesis; no upstream prose, code, example, table, or diagnostic
text is copied or adapted.

## Defect closure

The publication-excluded closure ledger classifies every material APG38
finding for the two candidates. The three terminal defects — registered
nested wrapper attribution, relaxed-mode count escalation, and sandbox
platform defaults — are `closed-in-APG39-redesign`; every other applicable
finding is `preserved-from-APG38`, `retained-as-project-owned`, or
`retained-as-explicit-uncertainty`. Nothing is `blocks-authoring`, no
finding was removed as invalid, and no precise defect was replaced with a
generic refresh instruction.

## Review limitation

The APG39 review is an **adversarial author self-review, not an independent
non-author review**, followed by one coherent final author correction pass.
It found and resolved three authoring defects (length compression, a
Yellow/Red registration ambiguity, one residual platform phrasing) and makes
**no retention prediction** for either candidate. Codex APG40 must perform
fresh independent source, behavior, structural, rights, and privacy review
with executable evidence before retaining anything.

## Not run

No project test, integration checker, lifecycle test, readiness check,
smoke test, or release build ran. No `go test`, benchmark, fuzz, race, or
coverage run occurred. No Nix parse, evaluation, build, flake check,
package test, store action, container test, NixOS VM test, activation, or
deployment occurred. Static inspection of exact tagged sources is source
evidence, not executable compatibility evidence; neither candidate carries
executable evidence of any kind.

## Delivery and integration boundary

APG39 delivers one formal authoring commit on
`claude/apg39-v0.4-matryer-nix-final-redesign`. `main` is not moved, merged,
rebased, or amended, and no earlier phase history is rewritten. The exact
push result is recorded in the APG39 phase report and its explicitly
associated operational record.

A publication-excluded integration handoff records, for each candidate, the
proposed catalog wording, router entry, projection, fixture, mirrored test
owner, compatibility and source probes, release-policy and inventory
additions, expected count delta, uncertainties, rollback, correction-cycle
state, and ADR dependency. If Codex later retains both candidates,
integrated development would become 29/29/29 with 15 provisional rows, 27
general-router entries, and 28 checked route edges — predictions, not
current facts.

## Current state preserved

Integrated development remains **27 canonical skills, 27 catalog rows, and
27 flat projections**, with 14 stable and 13 provisional rows, 25
general-router entries, 1 ChatGPT-local entry, and 26 checked route edges.
The authoring branch carries two candidate leaf directories that are
deliberately not integrated: no projection, catalog row, router entry,
maturity row, release-policy owner, test-inventory entry, fixture, or test
was added.

Public and active v0.3.0 remain **19/19/19** and unchanged. No public,
active, reference, RepoMap, personal, or target repository object was
modified, and no Nix state, database, container, virtual machine, or
external service was touched.

Neither candidate is integrated, adopted, mature, compatible, published, or
deployed.

## Subsequent APG40 disposition

APG40 preserves APG39 as a complete authoring phase and does not rewrite its
historical claims. Independent exact-source review found additional
matryer/is equality, caller-resolution, diagnostic, writer, and metadata
defects plus Nix phase-gating, flake-output, sandbox-fallback, configuration,
package-test, and structural-accounting defects. After one coherent correction
pass per candidate, fresh corrected-state review retained `nix-test-profile`
provisionally and deferred `matryer-is-test-profile` because its equality
mechanism remained materially inaccurate. ADR 0027 was Rejected; ADR 0026
remained Accepted; no stack returned. Resulting development is 28/28/28; public
and active v0.3.0 remain 19/19/19.

## Next authorization boundary

APG39 authorizes nothing further. Independent review, executable fixtures,
compatibility probes, the ADR 0027 decision, integration, readiness, smoke,
v0.4 publication, deployment, and any successor phase each require fresh
maintainer authority. No phase after APG39 is authorized.
