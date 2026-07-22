---
name: python-language-profile
description: Use when Python implementation, design, debugging, or review needs Python-specific judgment about structure, complexity, public APIs, typing, concurrency, serialization, packaging, or warning and crisis thresholds beyond repository policy.
---

# Python Language Profile

## Core principle

Apply Python-specific judgment only when it is material. Inspect the
repository's supported Python versions and policy before recommending a
construct, threshold response, or compatibility change. Use the highest
justified `Green — routine`, `Yellow — caution`, `Orange — warning`, or
`Red — crisis / stop` response for the current coherent decision.

Prevent uncontrolled growth of maintained hand-written modules and callables
without turning measurements into architecture authority. Preserve existing
repository precedence, public contracts, proportionality, and the current task
boundary.

## Do not use

Do not use this profile for:

- a comment, typo, mechanical rename, or other edit with no material
  Python-specific judgment;
- generic planning, implementation, debugging, or review procedure;
- selecting a framework, formatter, linter, type checker, test runner, package
  manager, Python version, coverage target, or deployment model;
- authorizing dependencies, migrations, live operations, publication, or
  destructive action;
- automatic broad refactoring of legacy code;
- direct treatment of generated, vendored, migration, snapshot, or protocol
  output before its ownership and generation path are classified; or
- enforcing style preferences or warning levels as semantic truth.

## Procedure

1. Establish the current task authority and applicable repository
   instructions. A profile warning never grants authority.
2. Identify supported Python versions and platforms, runtime and deployment
   constraints, public compatibility, formatter/linter/type policy, tests,
   packaging, dependency rules, and generated-code boundaries.
3. Classify the task and changed artifacts: maintained source, test, legacy,
   generated, vendored, migration, snapshot, protocol, or machine-produced.
4. Measure current and projected structural signals using the repository's
   configured analyzer when present. Record its version and settings.
5. When no configured analyzer exists, use the fallback measurement rules
   below and label the results as APG fallback counts. Do not compare counts
   from incompatible analyzers as though they were identical.
6. Assign the highest justified level for the current coherent decision. Three
   or more related, independent Yellow structural signals normally justify
   Orange unless recorded evidence demonstrates that they are a correlated
   false positive. Do not aggregate unrelated findings into a score.
7. Apply the response: proceed proportionally for Green; inspect policy and
   evidence for Yellow; require an explicit local decision, rationale,
   rollback, and focused validation for Orange; stop Red growth or unsafe
   action pending decomposition, an accepted bounded exception, or governing
   authority.
8. Inspect Python semantic hazards independently of structural size: public
   imports and signatures, serialization and persisted forms, annotations at
   runtime, import-time effects, global mutable state, circular imports,
   async/concurrency ownership, subprocess construction, dynamic execution,
   unsafe loaders, broad failure suppression, secret handling, and
   unmeasured optimization.
9. Pair with the applicable APG process capability when both boundaries
   matter. For example, a behavior change may use
   `implementing-with-test-discipline` as the primary process capability and
   this profile for Python judgment; a public-API acceptance review may pair
   `reviewing-and-verifying-repository-work` with this profile.
10. Preserve project-owned choices and stricter thresholds. Relax only a
    profile default under an accepted, scoped repository rationale with
    evidence, validation, and rollback; never relax a superior safety,
    privacy, compatibility, or authority prohibition.
11. State the relevant evidence, exception, decomposition boundary, and
    rollback. Avoid unrelated cleanup or a retrospective wholesale rewrite.
12. When the profile was material, complete with the level, signals, project
    policy, required response, and verification.

### Structural threshold contract

These defaults apply to maintained hand-written Python. They are guidance
signals, not linter claims or automatic architecture decisions.

| Signal | Green — routine | Yellow — caution | Orange — warning | Red — crisis / stop |
| --- | ---: | ---: | ---: | ---: |
| Module size | `<= 400` | `401–800` | `801–1,000` | `>= 1,001` |
| Function or method size | `<= 20` | `21–35` | `36–50` | `>= 51` |
| Cyclomatic complexity | `1–5` | `6–10` | `11–20` | `>= 21` |
| Branches | `<= 5` | `6–8` | `9–12` | `>= 13` |
| Nesting depth | `<= 2` | `3` | `4–5` | `>= 6` |
| Arguments | `<= 3` | `4–5` | `6–9` | `>= 10` |
| Locals | `<= 8` | `9–12` | `13–15` | `>= 16` |
| Responsibility count | `1` | `2` | `3` | `>= 4` |

Measure module size as physical lines after universal-newline decoding: blank
lines, comments, and multiline strings count; CRLF is one line ending; a final
non-empty segment without a line ending counts as one line. Measure callable
size as recursive Python statement nodes owned by that callable, excluding
nested function, lambda, and class bodies.

For fallback cyclomatic complexity, start at one and add decision paths for
`if`/`elif`, loops, exception handlers, Boolean-operation operands after the
first, comprehension filters, and `match` cases after the first. Count branches
as observable `if` arms, loop and loop-`else` paths, exception/`else`/`finally`
paths, and `match` cases. Nesting is the maximum depth of control-flow blocks
within the callable. Use one consistent fallback implementation for before and
after measurements and disclose that configured Ruff, Pylint, Radon, or other
analyzers may count some syntax differently.

Arguments include positional-only, positional-or-keyword, keyword-only,
`*args`, and `**kwargs`; exclude only a conventional leading `self` or `cls` for
a bound method. Locals are unique bindings in the callable, including
assignment, loop, context-manager, exception, import, and pattern targets,
excluding parameters and nested scopes.

For responsibility count, name the independently changeable behavior families
or external contracts. Helpers, validation, serialization, and adapters serving
one cohesive outcome do not automatically become separate responsibilities.
This reviewer-assessed count may set a response level but does not mechanically
select an extraction design.

### Classification and exceptions

Classify generated, vendored, protocol, migration, snapshot, and
machine-produced artifacts before applying the table. Inspect and change the
owner or generator when authorized; do not demand hand refactoring or edit
generated output solely because a threshold is exceeded. Structural
classification never suppresses a semantic Red stop.

An existing Red legacy file may receive the smallest safe fix under repository
authority when it adds no independent responsibility and avoids meaningful
structural growth. Record a decomposition or follow-up boundary. A major
feature or new responsibility remains Red.

A coherent data-driven test may receive Orange rather than a line-count-only
Red response only when repository policy accepts the exception, no other Red
signal applies, its fixture and behavior boundary remains cohesive, and new
growth has a bounded rationale. A test filename alone is not an exemption.

### Semantic response guide

- Preserve accepted public imports, signatures, exceptions, and serialized or
  persisted forms. An authorized compatibility change is Orange and needs
  consumer, migration, test, and rollback evidence; an unresolved public break
  is Red.
- A small justified dataclass or protocol can be Green or Yellow. Custom
  decorators, descriptors, protocols, or dispatch require local need; runtime
  registration, metaclasses, monkey patching, or behavior-altering decorators
  are normally Orange.
- A local coroutine or lock can be Yellow. A concurrency-model change is
  Orange and requires ownership, cancellation, shutdown, ordering, failure,
  and rollback evidence. Concurrency that can outlive authority or lose
  failures is Red.
- Declarative, idempotent imports are Green. A justified lazy or platform
  import, small explicit registry, or managed circular dependency is Yellow.
  Import-time I/O, hidden registration, order-dependent initialization,
  circular initialization, or global mutable singleton state is Orange and
  requires clean-process and import-order evidence plus rollback. Untrusted,
  destructive, secret-bearing, or live import effects are Red.
- Ordinary annotations supported by project policy are Green. A justified
  `TypedDict`, dataclass, bounded generic, overload, or protocol is Yellow.
  Public recursive types, annotation-driven runtime behavior, complex
  variance/overloads, backport dependencies, or version-sensitive introspection
  are Orange and need checker, runtime, compatibility, and simplification
  evidence. Treating static types or casts as runtime security validation is
  Red.
- Broad exception handling at a true boundary requires an explicit observable
  contract. Silent broad failure suppression is Orange or Red according to
  corruption, security, cancellation, or partial-mutation impact.
- A fixed or allowlisted project-owned dynamic import and a fixed executable
  with an argument sequence can be Green or Yellow according to platform and
  lifecycle context. Custom loaders, dynamically selected executables, shell
  invocation, complex pipelines, or externally consequential processes are
  Orange and require exact input provenance, platform behavior, failure and
  timeout tests, and rollback. No shell flag or import mechanism is universally
  safe or forbidden outside its real input and platform boundary.
- Stop when untrusted input reaches `eval`, when untrusted input reaches `exec`,
  or when an import or shell path can execute untrusted content.
- Unsafe untrusted deserialization, including untrusted or tamperable pickle
  input, is Red.
- Dependency, packaging, interpreter-support, entry-point, or build-backend
  changes are Orange when authorized and require compatibility, provenance,
  installation, deployment, and rollback evidence. An unauthorized dependency
  or release change is Red.
- Added complexity for an assumed hot path is Yellow or Orange: measure the
  representative workload before committing the complexity.

### Source and maintenance boundary

This profile was inspected and calibrated on 2026-07-21 from Python 3.14.6
language and standard-library documentation, PEP 8, PEP 387, PEP 484, PEP 544,
current Python Packaging User Guide material, Pylint 4.0.6 standard checker
options, current Ruff settings, and Radon 6.0.1 complexity ranks. Python
documentation is under the PSF License Version 2, with examples additionally
available under 0BSD. The inspected PEPs state public-domain or current PEP
reuse terms. The Packaging User Guide is CC BY-SA 3.0, Pylint is GPL-2.0, and
Ruff and Radon are MIT. APG copies or adapts no source expression or code; this
procedure and its calibration are independently written synthesis.

These versions are evidence, not mandated project tools or target versions.
Refresh the semantic guidance and thresholds before a behavior-bearing
correction, maturity review, or publication when supported Python semantics,
packaging specifications, analyzer defaults, or representative false-escalation
evidence materially change. Record source versions, settings, and derivation in
the refresh evidence.

Behavior-bearing corrections follow the APG skill authoring and maintenance
guide. Maturity changes remain separate decisions. Deprecation or removal must
remove the canonical leaf, checked projection, catalog and capability-map
entries, and focused compatibility tests while preserving ADR, evaluation, and
exit history. APG18 changes no root or private source guidance, so its rollback
does not restore or delete those sources.

## Project-owned parameters

The target repository owns:

- supported Python versions and platforms;
- framework, formatter, linter, type checker, test runner, and coverage policy;
- package manager, build backend, dependency, and supply-chain policy;
- public API, import, serialization, persistence, and compatibility promises;
- generated, vendored, protocol, migration, snapshot, and test classifications;
- deployment, concurrency, performance, and resource goals;
- accepted threshold exceptions, architecture, validation commands, and
  rollback form; and
- mutation, migration, release, publication, and destructive-action authority.

Stricter project policy controls. A project exception does not weaken a
superior safety, privacy, or task-authority stop.

## Evidence and completion

When this profile is material, report:

```text
Python profile level: Green | Yellow | Orange | Red
Signals: <size, complexity, API, concurrency, safety, or other>
Project policy: <relevant inputs>
Required response: <normal, inspect, decompose/design, or stop>
Evidence: <tests, compatibility, measurement, exception, and rollback>
```

Green normally needs supported-version awareness and project tests. Yellow adds
local policy and focused tradeoff evidence. Orange adds an accepted local
decision, adverse or compatibility tests where relevant, and concrete rollback.
Red records the stopped action, the source-to-sink or authority defect, the
safer alternative, and the exact disposition required before reconsideration.

## Stop or escalate

Stop or escalate when:

- untrusted input reaches `eval`, untrusted input reaches `exec`, or equivalent
  dynamic execution;
- unsafe untrusted deserialization is proposed or present;
- a secret, credential, private payload, username, or private path would be
  exposed;
- destructive or live mutation lacks exact authority and target validation;
- a public compatibility break lacks an accepted migration and rollback;
- concurrency lacks safe ownership, cancellation, shutdown, or failure
  propagation;
- broad suppression can conceal corruption, security failure, cancellation,
  or partial mutation; or
- new maintained hand-written growth crosses a Red structural boundary without
  decomposition or an accepted bounded exception.

## Common mistakes

- Treating every Python edit as profile-worthy.
- Using line count alone to choose architecture.
- Letting one sub-threshold metric hide combined complexity.
- Aggregating unrelated Yellow findings into a score.
- Forcing an unrelated rewrite of an existing Red legacy file.
- Treating a test filename as an unlimited size exception.
- Editing generated output instead of its authorized owner or generator.
- Inventing framework, tool, command, version, coverage, or packaging policy.
- Treating a warning level as action authority or deterministic enforcement.
- Creating abstractions to satisfy aesthetics rather than a current contract.
- Suppressing failures or cancellation to make a path appear successful.
- Describing a crisis while allowing the proposed growth to continue.
