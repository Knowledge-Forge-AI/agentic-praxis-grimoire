---
name: debugging-systematically
description: Use when behavior is failing, inconsistent, flaky, unexplained, or affected by multiple plausible causes.
---

# Debugging Systematically

## Core principle

Change behavior only after evidence identifies a plausible cause and a bounded
test of that cause.

## Do not use

Do not use this skill when the cause and correction are already established,
for unrelated preventive refactoring, or as permission to inspect or mutate
systems outside the authorized boundary. Route an accepted correction to the
appropriate implementation procedure.

## Procedure

1. State the observable symptom, expected behavior, environment, and known
   boundary. Preserve exact diagnostics in a privacy-safe form.
2. Reproduce the symptom reliably when practical. If it is intermittent, bound
   observation and record frequency, timing, and conditions without claiming a
   deterministic reproduction.
3. Inspect recent changes, inputs, state transitions, logs, and component
   boundaries that can distinguish plausible causes.
4. List explicit hypotheses and the evidence each predicts. Include multiple
   contributing causes when the observations support them.
5. Test one variable at a time where practical. Prefer read-only observation
   or reversible experiments before corrective mutation.
6. Distinguish root or contributing cause from symptom, containment, and
   unrelated defects.
7. Apply or recommend the narrowest correction supported by the evidence and
   permitted by the current assignment and project-owned mutation authority.
8. Re-run the original reproduction or observation, add regression evidence
   where appropriate, and run the proportional surrounding gate.
9. Record the cause confidence, correction, verification, unresolved
   alternatives, and any new issue class separately.

## Project-owned parameters

The project owns live-system access, log and data privacy, diagnostic tools,
retry and observation limits, environment cleanup, mutation authority,
containment and rollback procedure, and required regression evidence.

## Evidence and completion

A debugging result includes a reproduced or bounded symptom, gathered evidence,
tested hypotheses, cause assessment, narrow correction or disposition, and
reproduction-specific verification. An unreproduced failure may end in a
truthful observation or instrumentation recommendation rather than a guessed
fix.

## Stop or escalate

Stop when evidence requires secrets or unauthorized production access, safe
observation is unavailable, experiments would be destructive, hypotheses
remain indistinguishable, the environment is invalid, or a new architecture,
security, privacy, or ownership issue appears.

## Common mistakes

- guessing through successive unrelated patches;
- changing several variables at once;
- treating temporal correlation as a complete cause;
- weakening safeguards to make the symptom disappear;
- exposing sensitive diagnostics; and
- calling containment or non-recurrence proof of a unique root cause.
