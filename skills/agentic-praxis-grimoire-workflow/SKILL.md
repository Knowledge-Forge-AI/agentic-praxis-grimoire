---
name: agentic-praxis-grimoire-workflow
description: Use when an operator or manager needs to choose among multiple plausible APG skills, audit an APG routing decision, or diagnose a missing or stale APG capability.
---

# Agentic Praxis Grimoire Workflow Router

## Core principle

Route, do not orchestrate. Select the smallest sufficient APG capability for
the current task segment. Each skill retains its own independent trigger, and
no skill is required when no trigger is satisfied.

## Do not use

Do not use this router when an explicit applicable skill was selected, one
unambiguous APG leaf is already the obvious owner, or the work needs no APG
specialization. It is not a session-start bootstrap, a mandatory workflow
chain, a delegation selector, an action-authorization mechanism, a substitute
for repository instructions, or a private-integration manager.

Do not use the router to dispatch workers, require review as ceremony, copy a
leaf's procedure, or infer precedence or source from duplicate skill names.

## Procedure

1. Establish the human-authorized task boundary and applicable repository
   instructions. Routing cannot broaden either one.
2. Preserve an explicit applicable skill selection. Stop if it conflicts with
   safety or repository policy.
3. Read the public [capability map](references/capability-map.json). Treat a
   missing or unreadable map as an integration fault.
4. Exclude this router from the candidate set.
5. Use the map to identify only the materially plausible candidates. Before
   selecting among them, read each candidate's canonical frontmatter and
   `Do not use` section. Treat missing or unreadable canonical content as an
   integration fault.
6. Compare the current segment with those positive triggers and material
   non-triggers. Report materially inconsistent advertised, catalog, map, or
   canonical metadata instead of silently choosing among them.
7. Choose one primary process skill by default. A likely later step is not a
   current trigger, and several plausible skills do not form a required chain.
8. Add a separately applicable current domain profile only when the catalog and
   capability map contain it and both the process and domain boundaries are
   independently material. The process skill remains primary for its procedure;
   the domain profile supplies only domain-specific judgment.
9. Select no skill when none applies.
10. State material overlap, non-trigger, missing or stale capability, or
   integration faults when they affect the result. Do not infer which source a
   duplicate name represents without client-supplied identifying evidence.
11. Hand off to the selected leaf. Read that leaf completely and apply it
    directly; do not perform or paraphrase its procedure in the routing result.

## Project-owned parameters

The task and repository continue to own authority, instructions, accepted
design, delegation decisions, verification commands, review authority,
release and push policy, language and framework versions, installed skill
scopes, and any duplicate-name precedence supplied by the client.

## Evidence and completion

Keep the result proportional. When the boundary matters, identify:

```text
Primary APG capability: <skill-name | none>
Reason: <trigger evidence>
Material non-triggers: <names and reasons, when relevant>
Boundary or fault: <authority, missing content, stale metadata, or none>
```

Equivalent natural language is sufficient. A routing result completes only
capability selection; it does not complete the selected procedure or the task.

## Stop or escalate

Stop routing and surface the condition when authority is unresolved; an
explicit selection conflicts with safety or repository policy; canonical
content is missing or unreadable; metadata sources materially disagree;
duplicate names cannot be distinguished for a source-dependent claim; routing
would require invented procedure; or the task requires a capability that the
current catalog does not own.

## Common mistakes

- Routing every task.
- Selecting several process skills just in case.
- Turning likely future steps into current triggers.
- Treating review as mandatory completion ceremony.
- Treating delegation as automatic.
- Copying leaf instructions into the routing result.
- Inferring source from duplicate names.
- Treating an integration fault as permission to repair integration.
- Importing private workflow or personal guidance.
