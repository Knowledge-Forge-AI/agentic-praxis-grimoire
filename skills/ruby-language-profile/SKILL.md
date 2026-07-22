---
name: ruby-language-profile
description: Use when Ruby-specific judgment is material to structure, exceptions, blocks, shared state, dynamic dispatch, metaprogramming, callbacks, concurrency, gems, public compatibility, serialization, subprocesses, or warning and crisis thresholds beyond repository policy.
---

# Ruby Language Profile

## Core principle

Apply Ruby-specific judgment only when it is material. Establish supported Ruby
versions and engines, gem and Bundler policy, observable compatibility, runtime
and concurrency assumptions, and task authority before recommending a construct
or response. Use the highest justified `Green — routine`, `Yellow — caution`,
`Orange — warning`, or `Red — crisis / stop` response for one coherent current
decision.

Keep mutation and lifecycle ownership visible. Structural measurements warn
about proposed growth in maintained hand-written Ruby; they do not choose
architecture, grant action authority, or demand unrelated legacy rewrites.

## Do not use

Do not use this profile for:

- a comment, typo, mechanical rename, or edit with no material Ruby judgment;
- generic planning, implementation, debugging, or review procedure;
- selecting a Ruby engine or version, framework, formatter, analyzer, parser,
  test runner, gem manager, dependency, deployment, or release policy;
- authorizing runtime mutation, live operations, publication, dependencies, or
  destructive action;
- automatically refactoring existing Red code;
- treating generated, vendored, DSL, fixture, migration, snapshot, schema,
  protocol, or machine-produced artifacts as maintained source before
  classification; or
- treating RuboCop or fallback counts as universal semantic enforcement.

## Procedure

1. Establish task authority, repository instructions, supported Ruby versions
   and engines, gem and Bundler policy, compatibility promises, parser and tool
   settings, tests, artifact policy, and mutation and rollback boundaries.
2. Classify each relevant artifact as maintained source, test, legacy,
   generated, vendored, DSL, fixture, migration, snapshot, schema, protocol, or
   other machine-produced material. Classification never suppresses Red.
3. Use the configured analyzer when present and record version, target Ruby,
   parser backend, configuration, exclusions, and folding rules. Otherwise use
   the fallback rules below and label the result an APG fallback count.
4. Measure current and projected ownership using one method. Do not compare
   incompatible analyzers as equivalent or aggregate an entire repository into
   one warning score.
5. Assign the highest justified response. Three materially coupled Yellow signals normally justify Orange. Two materially coupled Orange signals over
   one owner are presumptively Red unless accepted cohesive evidence supports
   Orange. One Red signal remains Red. Correlated complexity and decision
   measures are not independent signals.
6. Proceed proportionally for Green; inspect policy and evidence for Yellow;
   require an explicit local decision, rationale, rollback, and focused
   validation for Orange; stop Red growth or unsafe behavior pending
   decomposition, an accepted bounded exception, or governing authority.
7. Inspect exceptions, blocks and closures, shared mutable state, dynamic
   dispatch, metaprogramming, constants, callbacks, thread/fiber/ractor
   lifecycle, public compatibility, gems, serialization, subprocesses,
   protected data, and performance independently of structure.
8. Pair separately with the applicable process capability.
   `implementing-with-test-discipline` may remain primary for a behavior change;
   `reviewing-and-verifying-repository-work` may remain primary for acceptance
   review. This profile supplies Ruby judgment without silently invoking either.
9. Preserve stricter project policy. Relax only a profile default through an
   accepted scoped rationale, evidence, validation, growth limit, and rollback;
   never relax a superior safety, privacy, compatibility, or authority stop.
10. Report the level, signals, owner and artifact classification, policy inputs,
    required response, validation, and rollback or decomposition boundary.

### Structural threshold contract

These defaults apply mainly to proposed growth in maintained hand-written Ruby.
They are guidance signals, not linter claims or architecture decisions.

| Signal | Green — routine | Yellow — caution | Orange — warning | Red — crisis / stop |
| --- | ---: | ---: | ---: | ---: |
| File physical lines | `<= 250` | `251–400` | `401–600` | `>= 601` |
| Method physical span | `<= 15` | `16–25` | `26–40` | `>= 41` |
| Cyclomatic complexity | `1–5` | `6–10` | `11–15` | `>= 16` |
| Explicit decisions | `<= 4` | `5–8` | `9–12` | `>= 13` |
| Control nesting depth | `<= 2` | `3` | `4–5` | `>= 6` |
| Declared parameters | `<= 3` | `4–5` | `6–8` | `>= 9` |
| Unique local bindings | `<= 8` | `9–12` | `13–16` | `>= 17` |
| Direct public API breadth per owner | `<= 8` | `9–15` | `16–24` | `>= 25` |
| Dynamic-dispatch/metaprogramming families per owner | `0` | `1` | `2` | `>= 3` |
| Callback/hook/lifecycle families per owner | `0–1` | `2–3` | `4–5` | `>= 6` |
| Independent responsibility families | `1` | `2` | `3` | `>= 4` |

Count physical lines after universal-newline decoding; blanks, comments,
heredocs, embedded data, and a final non-empty unterminated segment count. A
method span includes its definition through terminal `end`; an endless method
occupies its source line. Treat an identifiable `define_method` block as the
method contract it creates.

Complexity starts at one and adds conditionals, loops, ternaries, each `when`
or `in` arm, rescue clauses, and short-circuit operands after the first.
Decisions count explicit conditional, loop, case or pattern arm, ternary, and
rescue sites without the extra Boolean operands. Nesting is maximum conditional,
loop, case or pattern, and rescue depth; class, module, method, and ordinary
block containers add no depth. Parameters count positional, keyword, optional,
rest, keyword-rest, and explicit block parameters once each; `...` is one
open-ended family and separately needs compatibility review.

Local bindings are unique method-owned variable objects introduced by
assignment, destructuring, patterns, rescue, loops, or blocks. Exclude method
parameters and nested `def`, class, or module owners. Public API breadth counts
directly owned public instance and singleton methods; readers and writers,
aliases, and known generated methods count separately. Inherited methods do not
count. Record visibility and generated-method effects rather than assuming the
number alone defines compatibility.

Dynamic breadth counts closed, owner-scoped mechanism or contract families:
dynamic dispatch, runtime evaluation, runtime method definition or class/module
mutation, and dynamic constant or autoload behavior. Ordinary statically named
public dispatch does not count as a dynamic family. Callback
breadth counts owner-scoped lifecycle or event sources with separately
changeable registration, ordering, failure, or teardown contracts. Repeated use
of one bounded mechanism remains one family. When generated methods, callbacks,
public API, and dynamic dispatch overlap, disclose the overlap rather than
mechanically double-scoring it. Responsibilities are named independently
changeable behavior or external-contract families, not every helper.

### Classification and proportional exceptions

Follow the authorized owner or generator for generated, vendored, DSL, fixture,
migration, snapshot, schema, protocol, and machine-produced artifacts. Do not
demand direct edits or hand refactoring because a derived artifact is large.
Tests use the same measurements; a coherent-test exception may lower only a
line-count response and cannot lower method, API, lifecycle, or semantic
signals.

An existing Red legacy artifact may receive the smallest safe fix when current
authority permits it, the change adds no independent responsibility, and it
avoids meaningful growth. Record the preserved boundary. New responsibility or
major feature growth remains Red.

### Dynamic dispatch and metaprogramming

- Treat ordinary public dispatch as Green when receiver, public method, signature,
  and supported-version contract are established.
- Fixed allowlisted `public_send` is Yellow only when receiver, names,
  arguments, and visibility are bounded and the allowlist cannot reach unsafe
  trampoline behavior such as public `send`. Untrusted unsafe reachability is
  Red.
- `send` is Orange because it bypasses ordinary visibility. Untrusted method
  selection, arguments, or unsafe reachability is Red.
- Bounded `method_missing` is Orange. Require a closed name grammar or
  allowlist, explicit argument and block semantics, matching
  `respond_to_missing?`, delegation of unsupported names to `super`, and
  compatibility and error tests. Introspection is not a safety control;
  unbounded unsafe reachability is Red.
- Deterministic closed generated methods can be Yellow. Public API effect or
  runtime class or module mutation is Orange and needs isolation and rollback.
  Untrusted generated names or bodies and unauthorized core/public mutation are
  Red.
- Bounded dynamic constant lookup is Yellow. Material loading, ordering, or
  compatibility effects are Orange. A closed owner/path `autoload` can be
  Yellow; material side effects are Orange; attacker-controlled names or paths
  are Red.
- Runtime evaluation must distinguish block forms from interpreted strings.
  Bounded trusted code mutation is Orange. Untrusted evaluation through
  `eval`, `class_eval`, `module_eval`, `instance_eval`, or equivalent is Red.

### Shared mutable state

- Receiver-owned state and immutable configuration are Green. Owner-visible
  bounded registries and memoization with immutable values, deterministic
  invalidation, and established confinement can be Yellow.
- Treat globals and class variables, mutable constants, singleton state, registries
  and memoization, environment mutation, process-global configuration, and
  test-visible shared state as Orange when owner, mutation window,
  synchronization, cleanup or reset, failure behavior, isolation, validation,
  and rollback are explicit.
- A constant binding does not make its value immutable, and shallow freezing
  does not freeze an object graph. `ENV` is process-wide and must be restored in
  `ensure` when changed by tests or tools.
- Hidden, unbounded, or escaping state that can race, corrupt behavior,
  contaminate tests or tenants, leak protected data, bypass security, or resist
  reliable restoration is Red.

### Thread, fiber, or ractor lifecycle

- Synchronous work is Green. A locally bounded thread, fiber, or ractor can be
  Yellow when it has one clear owner, result and failure observation, no
  escaping mutable state, and established engine/version support.
- A material lifecycle or concurrency-model change is Orange. Require explicit
  ownership, start and stop rules, shutdown and cancellation, bounded join or
  value observation, exception propagation, queue or port ownership and
  closure, mutable-sharing rules, thread/fiber-local semantics, fiber scheduler
  assumptions, ractor shareability and isolation, process-exit behavior,
  cleanup in `ensure`, failure tests, and rollback.
- Work that can outlive authority, lose failures, deadlock, leak resources,
  violate sharing/isolation, or depend on asynchronous kill or process exit for
  cleanup is Red. A fiber scheduler is per-thread behavior, not an assumed
  global contract. Ractor shareability does not prove thread safety inside one
  ractor, and CRuby runtime assumptions do not automatically apply to other
  engines.

### Public compatibility and other semantics

- Preserve public methods, method visibility, positional and keyword arguments,
  block and yield contracts, constants, gem APIs, aliases, deprecations,
  refinements, monkey patches, serialization formats, and supported versions.
  Additive compatible behavior can be Yellow with consumer tests.
- An authorized non-additive compatibility change is Orange and requires exact
  authority, consumer inventory, migration or deprecation plan, support window,
  compatibility tests, and rollback. An unresolved compatibility break is Red.
  A public/core monkey patch is Red by default and can be Orange only with
  bounded authority, isolation, evidence, migration, validation, and rollback.
- Broad rescue at a true observable boundary is Orange. Rescue of `Exception`
  or silent suppression of material failure is Red when it can hide corruption,
  security failure, cancellation, or partial mutation.
- Unsafe or tamperable `Marshal` or YAML deserialization is Red. A specialized
  allowlist is bounded evidence only and does not make arbitrary loading safe.
- A fixed executable and argument vector can be Green or Yellow according to
  platform and lifecycle. Dynamic shell construction from untrusted input is
  Red. Process ownership, environment, timeout, cleanup, and output remain
  explicit.
- Performance-specific complexity is Yellow or Orange until representative
  measurement supports it. Assertion alone does not justify complexity.

### Source and maintenance boundary

This profile was inspected on 2026-07-21 against Ruby 4.0.6 language, core,
standard-library, security, maintenance, and compatibility documentation, and
RubyGems and Bundler 4.0.16. RuboCop 1.87 supplied configurable metric facts
only and is not a required tool. The Ruby distribution is available under the
Ruby License or two-clause BSD, subject to file-specific terms listed in
`LEGAL`. RubyGems and Bundler source is available under MIT or its Ruby-like
license terms. Website and news-page facts are independently summarized rather
than assigned a blanket software license. APG copies or adapts no source
expression, code, or table structure; this procedure is independently written
synthesis.

Versions are evidence, not mandated targets. Refresh before behavior-bearing
correction, maturity review, or publication when Ruby or engine semantics,
maintenance status, RubyGems/Bundler compatibility, parser or analyzer behavior,
or representative false-escalation evidence materially change. Removal must
delete the leaf, projection, catalog and map entries, known-unmanaged handling,
and focused tests while preserving ADR, evaluation, and exit history. No root
or private source guidance was migrated, so rollback restores none of it.

## Project-owned parameters

The target repository owns supported Ruby versions and engines; frameworks,
gems, Bundler, formatter, analyzer, parser, test and coverage policy; public API,
serialization, compatibility, autoload, callback, concurrency, subprocess,
generated and artifact policy; dependencies, supply chain, deployment,
performance, accepted exceptions, validation, rollback, mutation, release, and
destructive-action authority.

## Evidence and completion

When material, report the Ruby profile level, current and projected structural
and semantic signals, owner and artifact classification, supported version and
engine basis, project policy, required response, tests or measurements,
accepted exception if any, and rollback. Green needs project checks; Yellow
adds version and tradeoff evidence; Orange adds an accepted decision, adverse
or compatibility tests, and rollback; Red records the stopped action, safer
alternative, and exact condition for reconsideration.

## Stop or escalate

Stop or escalate when untrusted evaluation or unsafe dispatch can reach
behavior; unsafe or tamperable deserialization is proposed; shared state can
race, corrupt, leak, contaminate, or escape ownership; thread, fiber, or ractor
work can outlive authority or lose failure; cleanup depends on asynchronous
termination; an unresolved compatibility break lacks migration and rollback;
protected data can reach an unauthorized sink; destructive or live mutation
lacks exact authority; or meaningful new growth crosses Red without
decomposition or an accepted bounded exception.

## Common mistakes

- Treating every Ruby edit as profile work.
- Treating `public_send` or `respond_to_missing?` as safety controls by
  themselves.
- Conflating block evaluation with string evaluation.
- Counting raw dynamic calls or callbacks instead of owner-scoped families.
- Assuming constants, freezing, Ractors, the GVL, or process exit establish
  ownership or safety.
- Using asynchronous thread termination as cancellation or cleanup.
- Lowering non-line signals because a file is a test or DSL.
- Calling maintained upstream code legacy without owner evidence.
- Treating tool defaults as APG authority.
- Describing Red behavior while allowing it to proceed.
