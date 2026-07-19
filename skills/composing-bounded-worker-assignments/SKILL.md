---
name: composing-bounded-worker-assignments
description: Use when internal delegation is already authorized and independently selected, and one non-trivial worker assignment needs explicit scope, ownership, evidence, acceptance, or return boundaries.
---

# Composing Bounded Worker Assignments

## Core principle

Compose one executable assignment without authorizing or dispatching the
delegation it describes.

## Do not use

Do not use this skill when delegation is unauthorized, unselected, unnecessary,
or less clear than direct work. Do not use it to resolve an objective, design,
roadmap, or authority question; schedule or monitor workers; generate an
external human prompt; create a manager runtime; or restate an already adequate
assignment.

Do not split coupled work into assignments with shared write ownership or
material whole-system context merely to enable parallelism.

## Procedure

1. Confirm that the governing authority already permits internal delegation
   and that a manager has independently selected one worker for the objective.
2. State one concrete objective and the worker identity or role needed to
   pursue it.
3. Bound the source material the worker may inspect.
4. Define exclusive write scope, or state that the assignment is read-only.
5. Name only material prohibited actions and preserved invariants.
6. Specify the evidence the worker must gather and the concrete deliverable it
   must return.
7. Define observable acceptance criteria and the normal agent-harness return
   method.
8. Add snapshots, validation commands, commit authority, privacy handling,
   cleanup, rollback, or stop conditions only when the task makes them
   material.
9. Check that the assignment neither invents authority nor repeats policy that
   can be referenced once.

The semantic core may be compactly combined; it does not require a fixed
heading template.

## Project-owned parameters

The repository or current task owns its branch and commit policy, exact paths,
validation commands, privacy classes, runtime permissions, report mechanics,
worker limits, and integration process. Preserve those values as supplied;
do not generalize or fabricate them.

## Evidence and completion

The output is exactly one ready-to-send internal worker assignment. Completion
means every semantic boundary is present, proportional, internally consistent,
and reviewable. It does not mean the worker has been dispatched or its result
accepted.

## Stop or escalate

Stop when authority is unresolved, one objective cannot be isolated, required
source is unavailable, write ownership overlaps, acceptance cannot be observed,
or the task would require the worker to expand scope. Return the unresolved
boundary instead of composing a misleading assignment.

## Common mistakes

- treating assignment composition as permission to delegate;
- combining several objectives under one worker label;
- omitting read-only or write ownership;
- requiring managed Git or operational reports from an ordinary worker;
- copying repository-wide policy into every assignment; and
- using length or heading count as a substitute for executability.
