---
name: designing-significant-changes
description: Use when consequential behavior, architecture, ownership, interfaces, data contracts, safety boundaries, or irreversible choices remain unresolved before implementation.
---

# Designing Significant Changes

## Core principle

Resolve consequential uncertainty before turning it into implementation
commitment.

## Do not use

Do not use this skill for an accepted design, straightforward implementation,
tiny reversible maintenance, mechanical documentation cleanup, or a phase
whose design authority has already been settled. Do not reopen an accepted
decision merely because another design is possible.

## Procedure

1. Identify the decision owner, authorized design boundary, and concrete
   consequence that makes prior design useful.
2. Inspect current behavior, governing contracts, constraints, and relevant
   evidence before proposing a solution.
3. State unresolved questions, assumptions, non-goals, and preserved
   invariants.
4. Develop credible alternatives, including the status quo when it remains
   viable. Compare behavior, safety, compatibility, maintenance, reversibility,
   and evidence cost.
5. Select or recommend a decision only to the extent authorized. Record why it
   fits better than the alternatives and what evidence remains uncertain.
6. Define interfaces, ownership, data or state transitions, failure behavior,
   migration and rollback boundaries where applicable, and explicit exclusions.
7. State acceptance conditions and the separate authorization needed before
   implementation begins.
8. Return a design artifact, a bounded decision request, or a stop disposition;
   do not leak into implementation by default.

Use questions and diagrams only when they materially clarify the unresolved
decision. No fixed interview or approval ceremony is required.

## Project-owned parameters

The project owns its decision record format, architecture vocabulary,
compatibility window, security and privacy policy, migration authority,
dependency policy, reviewers, and implementation handoff. Treat these as
inputs rather than universal procedure.

## Evidence and completion

A completed design identifies the problem, material evidence, uncertainties,
alternatives, tradeoffs, decision or requested disposition, non-goals,
acceptance boundaries, and unresolved risks. Design completion is not
implementation authorization.

## Stop or escalate

Stop when the decision owner or authority is absent, a reserved choice is
required, evidence cannot distinguish alternatives, a destructive or public
action lacks authorization, or the requested design would exceed its stated
boundary.

## Common mistakes

- treating every change as a design project;
- presenting one favored option as a comparison;
- confusing source familiarity with project authority;
- omitting the status quo, non-goals, or rollback boundary;
- prescribing implementation details before the decision is accepted; and
- claiming consensus or acceptance that was not granted.
