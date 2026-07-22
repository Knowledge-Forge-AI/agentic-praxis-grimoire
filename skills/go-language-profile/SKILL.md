---
name: go-language-profile
description: Use when Go-specific judgment is material to structure, errors, context, interfaces, generics, concurrency, public APIs, reflection, unsafe, cgo, subprocesses, compatibility, or warning and crisis thresholds beyond repository policy.
---

# Go Language Profile

## Core principle

Apply Go-specific judgment only when it is material. Establish the supported Go
versions, build configurations, platforms, compatibility policy, and task
authority before recommending a construct or response. Use the highest justified
`Green — routine`, `Yellow — caution`, `Orange — warning`, or
`Red — crisis / stop` level for one coherent current decision.

Keep packages and callables focused, preserve observable error and cancellation
contracts, and make concurrency and resource ownership deterministic. Structural
measurements warn about proposed growth; they do not select architecture or
authorize retrospective rewrites.

## Do not use

Do not use this profile for:

- a comment, typo, mechanical rename, or ordinary test edit with no material
  Go-specific judgment;
- generic planning, implementation, debugging, or review procedure;
- selecting a Go version, module layout, formatter, analyzer, test command,
  dependency, platform, cgo policy, or release process;
- authorizing builds, dependency fetches, live operations, publication,
  host mutation, or destructive action;
- automatically refactoring existing Red code;
- treating generated, vendored, fixture, migration, snapshot, protocol, or
  machine-produced artifacts as maintained source before classification; or
- treating a warning level or fallback count as deterministic semantic truth.

## Procedure

1. Establish task authority, repository instructions, supported Go versions,
   build configurations, platforms, module and public compatibility promises,
   tools, tests, generated-code policy, and mutation and rollback boundaries.
2. Classify each relevant artifact as maintained source, test, legacy,
   generated, vendored, fixture, migration, snapshot, protocol, or other
   machine-produced material. Classification never suppresses semantic Red.
3. Use the repository's configured analyzer when present and record its version,
   settings, build matrix, and exclusions. Otherwise use the fallback rules
   below and label the result an APG fallback count.
4. Measure the current and projected owner. Do not compare incompatible tool
   counts as though they were equivalent or claim completeness when a supported
   configuration cannot be inspected without unauthorized execution.
5. Assign the highest justified response. Three materially coupled Yellow signals normally justify Orange. Two materially coupled Orange signals over
   one owner are presumptively Red unless accepted cohesive evidence supports
   Orange. One Red signal remains Red. Correlated complexity and decision
   counts are not independent signals.
6. Proceed proportionally for Green; inspect policy and evidence for Yellow;
   require an explicit local decision, rationale, rollback, and focused
   validation for Orange; stop Red growth or unsafe behavior pending
   decomposition, an accepted bounded exception, or governing authority.
7. Inspect errors, context, goroutines, channels, races, synchronization,
   resource lifetime, interfaces, generics, package initialization, public
   compatibility, reflection, `unsafe`, cgo, subprocesses, protected-data
   flows, and performance independently of structure.
8. Pair separately with the applicable process capability.
   `implementing-with-test-discipline` may remain primary for a behavior change;
   `reviewing-and-verifying-repository-work` may remain primary for acceptance
   review. This profile supplies Go judgment without silently invoking either.
9. Preserve stricter project policy. Relax only a profile default through an
   accepted scoped rationale, evidence, validation, growth limit, and rollback;
   never relax a superior safety, privacy, compatibility, or authority stop.
10. Report the level, measured and semantic signals, build/configuration basis,
    artifact classification, policy inputs, required response, evidence, and
    rollback or decomposition boundary.

### Structural threshold contract

These defaults apply mainly to proposed growth in maintained hand-written Go.
They are guidance signals, not linter claims or architecture decisions.

| Signal | Green — routine | Yellow — caution | Orange — warning | Red — crisis / stop |
| --- | ---: | ---: | ---: | ---: |
| File physical lines | `<= 400` | `401–700` | `701–1,000` | `>= 1,001` |
| Function or method statements | `<= 20` | `21–35` | `36–50` | `>= 51` |
| Cyclomatic complexity | `1–5` | `6–10` | `11–20` | `>= 21` |
| Branch or decision count | `<= 5` | `6–9` | `10–16` | `>= 17` |
| Maximum control nesting | `<= 2` | `3` | `4–5` | `>= 6` |
| Parameters | `<= 4` | `5–6` | `7–9` | `>= 10` |
| Local bindings | `<= 10` | `11–15` | `16–20` | `>= 21` |
| Exported API breadth per package | `<= 15` | `16–30` | `31–50` | `>= 51` |
| Independent concurrency ownership breadth | `<= 2` | `3–4` | `5–7` | `>= 8` |
| Independent responsibility families | `1` | `2` | `3` | `>= 4` |

Count physical lines after universal-newline decoding; blanks, comments, raw
strings, and a final non-empty unterminated segment count. Parse with
`go/parser`. Count each non-`ast.BlockStmt` statement recursively owned by a
function or method and exclude nested function-literal bodies. Complexity starts
at one and adds `if`, `for`, `range`, non-default switch and type-switch cases,
select communication clauses, and short-circuit operands after the first.
Decisions count `if` and `else if`, loops, every switch, type-switch, and select
clause, and short-circuit decisions. Nesting is the maximum owned control depth; nested function
literals start new owners. Parameters count grouped names separately, unnamed
and variadic parameters once, and exclude receivers and type parameters.

For local bindings, use type information when possible and count unique
callable-owned non-blank variable objects introduced by local `var`
declarations, newly introduced names in short declarations, range declarations,
type-switch case-specific implicit variables, receive declarations using `:=`,
and named results. Count bindings in nested lexical blocks. Exclude parameters,
receivers, unnamed results, `_`, reassignments including receive `=`, constants,
types, labels, and bindings owned by nested function literals. Shadowed objects
count separately; reassignment does not. Record a separate closure-capture subtotal
for captures that mutate, escape, extend lifetime, or own a channel,
cancel function, synchronization primitive, resource, or mutable state. A
parser-only estimate is not a type-accurate count.

For exported API breadth, measure each project-supported configuration
separately, recording Go version, `GOOS`, `GOARCH`, cgo state, build tags, and
production or test-package variant. If that matrix is undefined, report the
measurement incomplete. Count each exported identifier in grouped `const` and
grouped `var` declarations; each exported defined type and type aliases once;
each exported function; each directly declared exported receiver/type/method
pair, including an exported method on an unexported receiver type; unexported methods do not count; each
explicit exported struct field name; each embedded exported field; and each
directly declared exported interface method. Generic declarations count like
their non-generic category; type parameters and instantiations do not add
entries. Count direct members even on unexported receiver or container types.

Exclude promoted fields and methods and interface members inherited only by
embedding from the numeric direct-declaration count, but review their
compatibility effects. Include generated declarations in the raw count and
report a generated subtotal. Exclude `_test.go` from the production package and
report test-augmented surfaces separately. Do not union mutually exclusive
variants or double-count duplicate declarations across build variants. Select
the maximum count across supported build configurations and record the
configuration that produced it. Label `internal` and `main` package surfaces
without calling them unrestricted module APIs. Record cgo or generated
contributions as unresolved when they cannot be established without
unauthorized execution.

Concurrency breadth counts independently changeable lifecycle, cancellation,
shutdown, failure-propagation, communication-protocol, or synchronization
ownership families within one function, type, or package owner. A homogeneous
worker pool with one lifecycle and protocol is one family. Do not count raw
goroutines, channel values, sends, or receives. Responsibilities are named
independently changeable behavior or external-contract families, not stages of
one cohesive result.

### Classification and proportional exceptions

Follow the authorized owner or generator for generated, vendored, fixture,
migration, snapshot, protocol, and machine-produced artifacts. Do not demand
direct edits or hand refactoring because a derived artifact exceeds a threshold.
Tests use the same measurements; a test filename is not an exemption.

An existing Red legacy artifact may receive the smallest safe fix when current
authority permits it, the change adds no independent responsibility, and it
avoids meaningful growth. Record the preserved boundary. New responsibility or
major feature growth remains Red. A cohesive data-driven test may lower only a
line-count response under accepted project policy; other structural and
semantic signals remain effective.

### Semantic response guide

- Explicit error propagation and wrapping that preserves `errors.Is` and
  `errors.As` can be Green. A new public error promise is Yellow. Ignoring or
  shadowing a material error is Orange and becomes Red when corruption,
  security failure, data loss, or unsafe partial mutation is credible.
- Correct context deadline and cancellation propagation can be Green. A
  goroutine can outlive its owner or authority only at Red. An ambiguous channel
  send or close owner that can panic, deadlock, or lose work is Red. A known or credible data race is Red at any structural breadth.
- Retaining consequential resources through `defer` in a loop is Orange and
  becomes Red when exhaustion or unsafe partial mutation remains credible.
  Copying a synchronization-bearing value is Orange and becomes Red when the
  live copy can race, deadlock, or corrupt ownership.
- A small consumer-owned interface is Green or Yellow. A speculative broad
  interface or generic abstraction is Yellow and becomes Orange when public or
  cross-package; numeric Red still controls.
- Package `init` or mutable global registration is Orange and becomes Red when
  hidden state can race, corrupt, or escape lifecycle ownership.
- An authorized public API or module compatibility change is Orange and needs
  consumer, migration, validation, and rollback evidence. An unresolved break
  is Red.
- Bounded local reflection is Yellow; public serialization or dispatch effects
  are Orange. An `unsafe` or cgo boundary is Orange only with reviewed memory,
  lifetime, platform, validation, and rollback evidence; otherwise it is Red.
- A fixed executable and argument vector can be Green or Yellow according to
  lifecycle and platform policy. Stop at Red when untrusted input reaches shell
  interpretation. Process ownership, environment, timeout, pipes, cleanup, and
  platform behavior remain explicit.
- Performance-specific complexity is Yellow or Orange until representative
  measurement supports it. Assertion alone does not justify complexity.

### Protected-data source-to-sink review

Identify protected data under repository policy, including credentials, tokens,
keys, private or personal payloads, private paths and topology, connection
details, and classified identifiers. For each flow record source,
transformation, sink, recipient or storage, authorization, minimization, and
response. Inspect all of these sink families:

- logs, errors and wrapped errors, and panic or recover output;
- metrics and labels, trace attributes and events, and formatted strings;
- serialization, files, temporary files, filenames, and permissions;
- subprocess arguments, subprocess environment, and interpreted shell strings;
- network URLs, headers, bodies, redirects, and database or query text;
- test output, assertions, fixtures, snapshots, fuzz artifacts; and
- crash, core, profile, or debug output and retained diagnostics.

Parameterization and argument vectors can prevent injection without preventing
disclosure. Redaction must precede every downstream formatting, wrapping,
serialization, or fan-out boundary. Intentional disclosure to a bounded,
authorized recipient is Orange and needs minimization, retention, validation,
and rollback. Unauthorized, uncontrolled, overbroad, or unresolved disclosure
is Red even when the sink is internal or private and regardless of structure.

### Source and maintenance boundary

This profile was inspected on 2026-07-21 against Go 1.26.5, the Go 1.26
specification, Go 1 compatibility policy, the memory model, modules reference,
and current standard-library documentation for parsing, types, errors, context,
synchronization, reflection, `unsafe`, cgo, subprocesses, testing, and
diagnostics. Go website prose is generally CC BY 4.0 except where noted, while
code displayed on the site is BSD licensed. The Go source distribution,
including source comments and source examples, uses the three-clause BSD terms.
Third-party modules rendered by `pkg.go.dev` retain their own licenses. APG uses
facts and independently written synthesis; copied or adapted expression would
require its applicable notice and attribution.

Versions are evidence, not mandated targets. Refresh before behavior-bearing
correction, maturity review, or publication when supported releases,
compatibility, memory semantics, parser/type behavior, tool defaults, or
representative false-escalation evidence materially change. Removal must delete
the leaf, projection, catalog and map entries, known-unmanaged handling, and
focused tests while preserving ADR, evaluation, and exit history. No root or
private source guidance was migrated, so rollback restores none of it.

## Project-owned parameters

The target repository owns supported Go versions, configurations and platforms;
module, package, public API, compatibility, generated-code, build-tag, cgo,
formatter, analyzer, race, fuzz, benchmark, test, coverage, dependency,
supply-chain, deployment, concurrency, performance, artifact, exception,
validation, rollback, mutation, release, and destructive-action policy.

## Evidence and completion

When material, report the Go profile level, current and projected signals,
supported configuration and measurement method, artifact classification,
semantic and protected-data findings, project policy, required response,
verification, exception if any, and rollback. Green needs project checks;
Yellow adds version and tradeoff evidence; Orange adds an accepted local
decision, adverse or compatibility evidence, and rollback; Red records the
stopped action, safer alternative, and exact condition for reconsideration.

## Stop or escalate

Stop or escalate when a goroutine can outlive authority; channel ownership can
panic, deadlock, or lose work; a credible race or unsafe synchronization copy
remains; material errors can hide corruption or partial mutation; protected data
can reach an unauthorized sink; untrusted input reaches shell interpretation;
`unsafe` or cgo lacks reviewed lifetime and platform evidence; a public break
lacks migration and rollback; destructive or live mutation lacks exact
authority; or meaningful new growth crosses Red without decomposition or an
accepted bounded exception.

## Common mistakes

- Treating every Go edit as profile work.
- Counting raw goroutines, channels, sends, receives, or symbol spellings.
- Excluding bindings merely because they occur in a nested block.
- Calling promoted or variant declarations direct API, or ignoring their
  compatibility effects because they are excluded from the numeric count.
- Calling generated or cgo-dependent measurements complete without evidence.
- Using line count alone to choose architecture.
- Calling maintained upstream code legacy without owner evidence.
- Treating argument-vector construction or parameterization as data redaction.
- Treating a warning level as action authority.
- Describing Red behavior while allowing it to proceed.
