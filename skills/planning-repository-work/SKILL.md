---
name: planning-repository-work
description: Use when an accepted objective requires multiple dependent implementation steps, cross-file coordination, staged risk reduction, or a durable handoff.
---

# Planning Repository Work

## Core principle

Organize accepted work into coherent, independently reviewable units around
dependencies and evidence rather than arbitrary time boxes.

## Do not use

Do not use this skill for one obvious local action, unresolved design or
authority, open-ended exploration without a planning objective, or an adequate
existing plan. Do not use planning to reopen accepted design decisions.

## Procedure

1. Confirm the accepted objective, applicable decisions, current repository
   state, and the boundary the plan may implement.
2. Identify affected responsibilities, files or stable code surfaces,
   interfaces, tests, documentation, and compatibility obligations.
3. Divide the work into units that each answer one review question and leave a
   coherent state. Avoid artificial microtasks.
4. For every unit, state the outcome, owned surfaces, prerequisites, preserved
   behavior, validation, acceptance conditions, and stop boundary.
5. Order units by dependency and risk. Put discovery or characterization ahead
   of irreversible or broad changes when it reduces uncertainty.
6. Identify parallel work only where source and write scopes are independent
   and integration responsibility is explicit. Use sequential units when write
   scopes overlap but overall ownership and integration remain clear.
7. Record project-owned commit, review, migration, rollout, rollback, or
   publication steps only when supplied by current policy or authority.
8. End with the integrated verification and handoff needed to judge the whole
   objective, plus intentional deferrals.

## Project-owned parameters

The repository owns its file layout, phase model, task size, branch and commit
policy, test commands, required artifacts, reviewer gates, deployment process,
and report format. A plan references or instantiates those rules without
turning them into APG defaults.

## Evidence and completion

A completed plan is executable by a competent contributor without guessing
the objective, ownership, dependencies, validation, or stop conditions. Exact
line numbers and complete code are included only when they remain stable and
material.

## Stop or escalate

Stop when the objective or design is unaccepted, dependencies are unknown
enough to make sequencing fictional, overall write authority or integration
ownership is unresolved, a required migration or destructive action lacks
authority, or planning reveals a new design decision.

## Common mistakes

- decomposing by minutes instead of reviewable outcomes;
- hiding design decisions inside implementation steps;
- listing files without dependencies or acceptance evidence;
- forcing parallelism across shared state;
- copying every repository rule into the plan; and
- omitting integrated verification and intentional deferrals.
