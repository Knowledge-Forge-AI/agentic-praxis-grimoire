# APG21A Nix Profile Correction

Phase ID: `APG21A`

## Outcome

Complete — corrected Nix profile retained and APG21 focused audit closed.

APG21A reconstructs `nix-language-profile` from the retained APG21 evidence,
corrects the recorded merge-response contradiction, and integrates one
provisional development leaf. It also applies one newly discovered bounded
PostgreSQL false-escalation correction. SQLite and workflow-router behavior are
unchanged.

The correction grants no authority to evaluate Nix, fetch inputs, build,
inspect or mutate the store, activate a system or user configuration, open or
operate a database, or perform destructive work.

## Corrected Nix decision

APG21 used merge/override mechanism-family breadth as a structural signal but
did not independently classify merge semantics. A closed computed-name merge
therefore received structural Green for one family even though the frozen
scenario required semantic Orange.

APG21A preserves the fourteen structural thresholds and adds a separate
semantic merge decision:

| Case | Response |
| --- | --- |
| Literal, statically disjoint local shallow update | Green, or Yellow when local compatibility evidence remains material |
| Known local collision with deliberate precedence | Yellow; Orange at a consequential compatibility, ownership, migration, or rollback boundary |
| Closed computed-name merge with material collision, precedence, ownership, or consumer effect | Orange |
| Open or insufficiently bounded merge | Orange pending evidence; Red when safe behavior or an invariant cannot be established |
| Recursive, repeated-layer, fixed-point, overlay, or module-priority merge | Orange; Red for unresolved recursion, uncontrolled collision, unsafe priority, or invariant bypass |
| Security, integrity, reproducibility, trust, or ownership invariant bypass | Red |

A structurally Green merge-family count cannot downgrade semantic Orange or
Red. The contract also avoids false escalation: a local disjoint `//`,
name-preserving `mapAttrs`, collision-free local generation, and `rec` without
a merge are not automatically Orange. `mkForce` is not universally Red, but it
is Red when it bypasses an accepted invariant.

## Evidence and correction allowance

The initial corrected candidate passed the complete APG21 Nix scenario set,
ten APG21A merge cases, focused integration tests, and read-only semantic
source review. A focused audit then reproduced one material PostgreSQL
contradiction: operation-specific forward recovery for a non-destructive
concurrent index or RLS change conflicted with a generic requirement that every
consequential change complete a tested restore.

The single permitted newly discovered APG21A correction scopes tested-restore
evidence to a consequential change that relies on restoration as its recovery
boundary. The existing Red stop for destructive work backed only by an
untested backup remains unchanged. No second correction was required.

## Sources, rights, and dogfood

The Nix semantic basis remains the mutable Nix 2.35.2 manual, separately
versioned Nix 2.35.1 public source, and NixOS/Nixpkgs 26.05 semantic series.
The manual and source are not represented as one snapshot. Nix source and its
bundled manual use LGPL-2.1-or-later; Nixpkgs/NixOS source uses MIT subject to
component-specific exceptions; independently authored nix.dev site content
uses CC BY-SA 4.0. The profile is independently written synthesis and copies no
third-party expression or code.

Read-only dogfood rechecks maintained Green, Yellow, Orange, and Red files; a
generated lock; impurity; activation authority; legacy minimal-fix behavior;
and dynamic merges. No Nix expression was evaluated, no input fetched, no
build performed, and no store or activation action occurred.

Fresh review corrected one inherited APG21 dogfood label: a 27-line maintained
source is structurally Green but semantic Orange pending evidence because it
converts open output names with `listToAttrs` and merges them across owners. A
separate 48-line maintained package expression supplies the genuine Green
control. This evidence correction changes no procedure and does not consume a
second behavior-bearing correction allowance.

## Resulting development shape

The private development repository contains 17 canonical leaves, 17 relative
checked-in projections, 6 stable rows, 11 provisional rows, and 16 routable
non-router capability-map entries. Nix is known-unmanaged by the project-local
lifecycle command. The six managed v0.2 defaults and schema version 1 are
unchanged.

Public v0.2.0 and the active public-backed integration remain six-skill
contracts. APG21A performs no candidate build, publication, active-integration
mutation, root-guidance cutover, private-skill decommission, ZUnit work,
manager-prompt implementation, application smoke, or APG22 work.

## Validation and disposition

The complete APG21 shared and Nix scenario sets, ten merge-specific cases,
focused Nix and PostgreSQL tests, canonical/catalog/projection validation,
capability-map exactness, project/user/release boundaries, source and rights
review, read-only dogfood, documentation, privacy, record identity, and fresh
non-author review support `retained-provisional` for
`nix-language-profile` and the bounded PostgreSQL correction.

Retention does not establish automatic invocation, comparative superiority,
stable maturity, application discovery, build correctness, or release
readiness. Those claims remain owned by later separately authorized phases.
