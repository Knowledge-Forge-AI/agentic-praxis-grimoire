---
name: vitest-test-profile
description: Use when a project has already selected Vitest 4.1 and runner-specific judgment is material to configuration, projects, environments, assertions, mocks, timers, concurrency, isolation, snapshots, or coverage providers; not for test sufficiency, language or React semantics, or coverage policy.
---

# Vitest Test Profile

Lifecycle: `provisionally-integrated`.
Lifecycle ADR: `Accepted with amendment`.

## Core principle

Apply Vitest-specific judgment only after the project has selected Vitest 4.1.x
and the current decision materially depends on runner invocation, configuration
or projects, environment selection, assertions and failure output, spies or
module mocking, fake timers, concurrency or isolation, snapshots, or
coverage-provider mechanics. Establish the exact Vitest patch, Node runtime,
configuration entrypoint, project selection, pool, environment, and invocation
before a version-sensitive conclusion.

Own how the selected runner behaves, not whether a test should exist.
`implementing-with-test-discipline` and project test strategy retain
sufficiency and real-versus-fake decisions. ECMAScript and TypeScript semantics
remain with `javascript-language-profile` and
`typescript-language-profile`; Node host behavior remains with
`nodejs-runtime-profile`; component behavior remains with the future
`react-component-profile`. No owner is silently invoked.

Use the highest justified `Green — routine`, `Yellow — caution`,
`Orange — warning`, or `Red — crisis / stop` response for one coherent
Vitest decision. A runner result never supplies dependency, coverage-policy,
snapshot-acceptance, publication, or live-mutation authority.

## Do not use

Do not use this profile for:

- deciding whether to adopt Vitest, Vite, a DOM environment, browser provider,
  coverage provider, or another dependency;
- deciding what to test, whether evidence is sufficient, or how implementation
  and review work should be sequenced;
- ECMAScript evaluation, TypeScript checking or emit, Node host behavior,
  component or hook semantics, JSX syntax, or browser and DOM correctness;
- choosing coverage targets, exclusions, thresholds, branch policy, source
  inventory, or acceptance;
- package-manager resolution, Vite or bundler internals, deployment, or product
  behavior;
- generic planning, debugging, review, or repository architecture; or
- authorizing dependency changes, network or service access, host mutation,
  snapshot acceptance, publication, deployment, or destructive action.

A routed question keeps its receiving owner's obligation open. Runner success
does not answer a language, runtime, component, coverage-policy, or product
question.

## Procedure

1. Establish task authority and repository policy. Bind the exact Vitest and
   Node versions, package and lock evidence, configuration source, working
   directory, invocation, selected projects, pool, environment, isolation,
   concurrency, reporters, snapshot mode, coverage provider, source ownership,
   protected-data policy, exact checks, and rollback.
2. Classify affected material as test, configuration, setup file, environment,
   project definition, mock, snapshot, fixture, generated artifact, cache,
   report, or legacy. Classification never suppresses a semantic Red stop.
3. Resolve configuration and project ownership from the actual invocation.
   Distinguish a Vite config, Vitest config, inline options, CLI overrides, and
   per-project options. Root-only settings must not be represented as
   project-local behavior.
4. Bind the test environment and pool independently. `node`, `jsdom`,
   `happy-dom`, edge-style environments, and custom environments expose
   different globals and lifecycles. Declarations or package presence do not
   prove an environment was selected or executed.
5. Inspect the assertion and failure contract. Confirm each asynchronous
   assertion is awaited or returned, exception and rejection expectations
   execute the subject, custom equality or serializers are bounded, and failure
   output cannot expose protected data.
6. Inspect spies, function mocks, module mocking, and fake timers as distinct
   features. Bind the resolved module and environment, account for transformed
   and hoisted module mocks, restore global or module state, drain or abandon
   timers intentionally, and never call a replaced boundary real integration.
7. Inspect file concurrency, `test.concurrent`, pool workers, project
   scheduling, and isolation separately. Sequential execution is not isolation;
   disabling isolation requires explicit state-reset evidence.
8. Inspect snapshot ownership: serializer and path resolution, external versus
   inline mutation, environment-sensitive values, update mode, obsolete
   entries, CI behavior, diff review, and rollback. A snapshot update is a
   source mutation requiring explicit acceptance.
9. Inspect coverage-provider mechanics: selected `v8`, `istanbul`, or custom
   provider; transform and remap path; worker results; source inclusion;
   combination; output; and provider limitations. Leave thresholds, exclusions,
   and sufficiency to project coverage policy.
10. Assign the highest response below. Proceed proportionally for Green; inspect
    exact config and version evidence for Yellow; require a bounded accepted
    design and adverse cases for Orange; stop Red false-pass, collision, leak,
    unsafe mutation, or unsupported claim.
11. Pair independently with the applicable process and adjacent domain owners.
    Report each unresolved route without reproducing that owner's guidance.

### Response model

| Level | Vitest condition | Required response |
| --- | --- | --- |
| Green — routine | exact invocation and config, isolated state, awaited assertions, bounded mocks or timers | run focused project-owned Vitest checks |
| Yellow — caution | version-sensitive option, project override, custom environment, snapshot serializer, provider-specific coverage, or flexible concurrency | inspect exact config, patch version, artifacts, and local policy |
| Orange — warning | disabled isolation, shared mutable setup, broad module mock, custom pool or environment, snapshot mutation, custom coverage provider, or cross-project coupling | require an accepted bounded design, adverse cases, cleanup, rollback, and artifact review |
| Red — crisis / stop | required assertion can false-pass, async work is unobserved, worker state collides, mock or timer state leaks, snapshot mutation lacks acceptance, coverage is incomplete but claimed complete, or protected data reaches output | stop until truthfulness, isolation, ownership, and rollback are restored |

Do not convert counts of tests, mocks, snapshots, projects, or workers into a
universal structural threshold. Escalation requires a concrete truthfulness,
isolation, ownership, exposure, or maintainability consequence.

### Runner boundaries

Vitest projects select distinct test configurations inside one run; their
settings do not merge into one imaginary project. Root-level reporting,
coverage, and snapshot resolution can span projects. Record the exact selected
project set and the final effective option values.

Module mocking is transform- and environment-sensitive. A `vi.mock` call may
be hoisted ahead of imports; browser-style environments can use a different
replacement mechanism. Establish the actual environment and transform before
claiming mock timing or module identity.

Fake timers alter runner-controlled time surfaces, not every external clock or
host effect. Restore real timers and settle required scheduled work before the
owner completes. Route language ordering to the language owner and Node
event-loop behavior to the runtime owner.

Coverage provider configuration proves only collection mechanics under the
executed run. It does not prove the project selected the correct source set,
threshold, exclusions, or sufficiency policy.

### Source and maintenance boundary

This profile was independently written from the official Vitest 4.1
documentation and the stable v4.1.7 repository sources for configuration,
projects, environments, assertions, mocking, timers, pools and isolation,
snapshots, and coverage. Vitest is MIT licensed; its published package records
separately licensed bundled dependencies. APG copies no upstream prose, code,
example, table, or diagnostic text; factual API identifiers and behavior are
used as facts.

Refresh before a behavior-bearing correction, maturity review, or publication
when the selected Vitest line changes, configuration resolution or project
ownership changes, environment or pool behavior changes, mock transformation or
timer behavior changes, snapshot mutation changes, coverage providers change,
or Node support and runtime assumptions change.

Removal is candidate-independent. Remove the canonical leaf, projection,
catalog and capability-map entries, current-development release-policy entry,
strict inventory row, focused tests, and public scenario fixture; repair
surviving routes to the retained owner or project-owned fallback; and preserve
ADR, evaluation, exit, and provenance history. Removal changes no target
dependency, test, snapshot, or coverage artifact.

## Project-owned parameters

The target repository owns whether Vitest and each environment, pool, browser,
coverage, or reporting dependency is selected; exact versions and Node support;
package manager and lockfile; config entrypoints and precedence; projects,
patterns, setup, globals, environment, pool, isolation, concurrency, timeouts,
retries, reporters, cache, and CI; assertion, mock, timer, snapshot, serializer,
and update policy; coverage sources, thresholds, exclusions, branch policy,
combination, retention, and acceptance; external services; protected data;
accepted exceptions; validation; rollback; dependency mutation; release;
publication; deployment; and destructive-action authority.

Stricter repository policy controls. No local exception weakens a superior
safety, privacy, truthfulness, compatibility, or task-authority stop.

## Evidence and completion

When material, report the exact Vitest and Node versions, invocation and
effective configuration, selected projects, environment and pool, concurrency
and isolation, assertion completion, replaced versus real boundaries, timer
cleanup, snapshot mutation and review state, coverage provider and completeness,
response level, protected-output handling, checks, exception if any, and
rollback. Distinguish static configuration, collection, mocked evidence,
executed runner evidence, provider output, and external integration.

Green needs focused project checks. Yellow adds exact version and effective
configuration evidence. Orange adds an accepted bounded design, adverse-case
validation, cleanup, artifact review, and rollback. Red records the stopped
false-pass, collision, leak, unsafe mutation, or unsupported claim and the
condition required before reconsideration.

## Stop or escalate

Stop when the exact runner role, version, invocation, config, project,
environment, or pool is missing for a dependent claim; an async assertion or
required task can finish unobserved; collection omission is accepted as success;
mock, timer, module, global, filesystem, cache, snapshot, or coverage state can
leak across owners; worker-shared state can collide; a mocked boundary is called
integrated; a snapshot is created or updated without source-mutation authority
and review; coverage fragments or remapping are incomplete but represented as
complete; protected values can reach failures, snapshots, reports, paths, or
artifacts; or language, runtime, component, coverage-policy, build, or
deployment completion is inferred from runner success.

## Common mistakes

- Selecting Vitest because a JavaScript, TypeScript, or component test exists.
- Reading a package, config, or script definition as proof of invocation.
- Treating sequential execution as isolation.
- Forgetting that module mocks can be transformed and hoisted.
- Leaving fake timers, spies, modules, or globals modified for another test.
- Failing to await asynchronous assertions or timer work.
- Updating snapshots without reviewing the source mutation.
- Treating provider configuration or a percentage as complete coverage proof.
- Calling a mocked, DOM-emulated, or runner-local boundary real integration.
- Answering language, Node, component, or test-sufficiency questions under
  runner authority.
- Inventing dependency, version, command, threshold, or mutation authority.
