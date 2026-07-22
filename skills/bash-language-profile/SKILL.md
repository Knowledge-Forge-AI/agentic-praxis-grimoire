---
name: bash-language-profile
description: Use when Bash-specific judgment is material to quoting, expansion, arrays, pipelines, traps, subprocesses, files, portability, or warning and crisis thresholds beyond repository policy.
---

# Bash Language Profile

## Core principle

Apply Bash-specific judgment only when the task materially depends on Bash
semantics. Establish the selected interpreter and supported version range
before relying on syntax or behavior. Use the highest justified
`Green — routine`, `Yellow — caution`, `Orange — warning`, or
`Red — crisis / stop` response for the current coherent decision.

Preserve argument boundaries, observable failure, resource ownership, and the
task's authority. Structural measurements warn about maintained hand-written
scripts whose state model is outgrowing shell; they do not choose architecture
or demand unrelated legacy rewrites.

## Do not use

Do not use this profile for:

- portable POSIX shell work unless Bash behavior is also materially involved;
- Zsh-native semantics or another shell dialect;
- Bats discovery, hooks, assertions, TAP, or runner behavior;
- generic implementation, debugging, planning, or review procedure;
- selecting a shell, formatter, linter, test runner, coverage target, or CI
  command;
- authorizing dependencies, publication, privilege, live mutation, or
  destructive action;
- a comment, typo, mechanical rename, or edit with no material Bash judgment;
- automatic broad refactoring of a legacy script; or
- structural treatment of generated, vendored, fixture, snapshot, migration,
  or compatibility artifacts before classification.

## Procedure

1. Establish task authority, repository instructions, interpreter/shebang,
   supported Bash versions, platforms, portability promises, tests, and exact
   mutation and rollback boundaries.
2. Classify each relevant artifact as maintained source, test, legacy,
   generated, vendored, fixture, snapshot, migration, compatibility material,
   or data. Classification never suppresses a semantic Red stop in proposed
   executable behavior.
3. Measure current and projected structure with a configured repository tool
   when one exists. Otherwise use the fallback rules below and label the
   result as an APG fallback count.
4. Inspect quoting, expansion, arrays, `IFS`, `read`, substitutions, pipelines,
   option state, traps, temporary paths, symlink boundaries, process lifetime,
   dynamic execution, destructive targets, secrets, and dialect compatibility.
5. Assign the highest justified level. Three materially coupled Yellow signals
   normally justify Orange. Two materially coupled Orange signals affecting
   the same owner are presumptively Red unless a cohesive-artifact rationale,
   repository acceptance, evidence, validation, and rollback justify retaining
   Orange. One Red signal remains Red. This is judgment, not a numeric score;
   do not aggregate unrelated findings.
6. Proceed normally for Green; inspect local evidence for Yellow; require an
   explicit local decision, rationale, rollback, and focused validation for
   Orange; stop Red growth or unsafe action until decomposition, an accepted
   bounded exception, or governing authority resolves it.
7. Pair separately with an applicable process skill. A behavior change may
   keep `implementing-with-test-discipline` primary; a completion review may
   keep `reviewing-and-verifying-repository-work` primary. Add
   `bats-test-profile` only when Bats harness behavior is independently
   material.
8. Preserve stricter repository policy. Relax only a profile default through
   an accepted scoped rationale, evidence, validation, and rollback; never
   relax a superior safety, privacy, compatibility, or authority rule.
9. Report the level, signals, policy inputs, required response, validation, and
   rollback. Avoid unrelated cleanup.

### Structural threshold contract

These defaults apply mainly to maintained hand-written Bash. They are guidance
signals, not linter claims or automatic architecture decisions.

| Signal | Green — routine | Yellow — caution | Orange — warning | Red — crisis / stop |
| --- | ---: | ---: | ---: | ---: |
| Script physical lines | `<= 150` | `151–300` | `301–500` | `>= 501` |
| Function/top-level command count | `<= 15` | `16–25` | `26–40` | `>= 41` |
| Decision paths | `<= 4` | `5–7` | `8–12` | `>= 13` |
| Nesting depth | `<= 2` | `3` | `4` | `>= 5` |
| Fixed positional parameters | `<= 4` | `5–6` | `7–9` | `>= 10` |
| Mutable globals/cross-function state | `0–1` | `2–3` | `4–6` | `>= 7` |
| Pipeline/process graph breadth | `0–2` | `3–4` | `5–7` | `>= 8` |
| Independent responsibility families | `1` | `2` | `3` | `>= 4` |

Count physical lines after universal-newline decoding; comments, blank lines,
and heredoc bodies count, and a final non-empty unterminated segment is one
line. For a named function or top-level region, count Bash grammar command
nodes; count pipeline stages, nested substitutions, and nested commands, but
not comments, blank lines, terminators, or heredoc data.

Decision paths count `if` and `elif`, loops, `select`, each `case` arm, and
control-significant `&&` or `||`. Nesting is the maximum simultaneously open
conditional, loop, case, subshell, or command/process-substitution boundary.
Fixed parameters are the highest independently interpreted positional slot;
pure `"$@"` pass-through adds no fixed slot, while a variadic parser is at least
Yellow.

Mutable shared state is the number of independently mutable owner domains
written at top level and read or written across functions, or written by
multiple functions; scalar aliases for one domain do not multiply the count.
Process breadth is the maximum status-coupled or concurrently active execution
graph owned by one function or decision path, including independent pipeline
stages, process substitutions, and background children; repeated aliases for
one executable family do not multiply the count. Background concurrency is
still semantic Red whenever ownership or cleanup is unsafe. Responsibilities
are named, independently testable behavior families, not stages of one
cohesive outcome.

### Classification and proportional exceptions

Classify generated, vendored, fixture, snapshot, migration, compatibility, and
data-driven artifacts before structural action. Change the authorized owner or
generator when appropriate; do not demand hand refactoring solely because a
derived artifact is large. A coherent compatibility matrix may receive a
bounded line-count exception under accepted repository policy, but semantic
Red stops and other structural signals remain effective.

An existing Red legacy artifact may receive the smallest safe fix when it adds
no independent responsibility and no meaningful growth. Record a decomposition
or follow-up boundary. A major feature or new responsibility remains Red until
decomposition or an accepted bounded exception resolves it.

### Semantic response guide

- Quote expansions by default. Deliberate controlled globbing or splitting can
  be Green or Yellow. Uncontrolled expansion is Orange and becomes Red when it
  reaches a destructive, privileged, secret-bearing, path, or execution sink.
- Prefer arrays for fixed argument vectors and expand them as
  `"${args[@]}"`. Version-sensitive arrays are Yellow. Flattening and rebuilding
  arguments is Orange; reconstructing untrusted data as shell syntax is Red.
- Bounded `IFS= read -r` parsing can be Green. Intentional delimiter or escape
  behavior is Yellow. Global `IFS` mutation, implicit splitting, or ignored
  read status is Orange when it changes later behavior and Red at an unsafe
  sink.
- A quoted command substitution with material status handled can be Green.
  Status masking or assumptions about subshell state are Orange; false success
  that controls destruction, security, publication, or cleanup is Red.
- A pipeline is Green only when its intended status is observed. A material
  intermediate failure without `pipefail`, `PIPESTATUS`, or equivalent
  handling is Orange and becomes Red across a consequential boundary.
- `set -e`, `set -u`, and `pipefail` are contextual policy, not proof of safe
  failure handling. Reliance on uniform propagation through conditions, lists,
  functions, substitutions, or pipelines is Orange; unsafe continuation or
  false completion is Red.
- One idempotent cleanup owner over bounded resources can be Green. Signal
  composition is Yellow; interacting traps, nested shells, or background
  owners are Orange. A child that can outlive authority or cleanup that can be
  lost is Red.
- Use privately owned temporary resources and exact quoted targets. Predictable
  consequential paths or check/use gaps are Orange. An attacker-influenced
  path or unsafe symlink race at a consequential boundary is Red.
- An exact authorized cleanup target can be Green. Consequential destructive
  mutation is Orange only with authority, target proof, rollback, and focused
  validation. An unresolved destructive command target is Red.
- A fixed argument-vector subprocess or constant repository-owned source can
  be Green. A trusted, validated dynamic boundary is normally Orange.
  Stop when untrusted or uncontrolled data reaches `eval`, `source`, `bash -c`, or
  equivalent dynamic execution only at Red, and the action must stop.
- Redact secrets and private paths. Plausible exposure through tracing,
  diagnostics, inheritance, or captured output is Orange; actual exposure is
  Red.
- A declared and tested Bash dialect is Green. Version-specific features are
  Yellow. A shebang or compatibility change is Orange. A false Bash/POSIX
  compatibility claim governing consequential behavior is Red.

### Source and maintenance boundary

This profile was inspected and calibrated on 2026-07-21 from the GNU Bash 5.3
manual and release series, current patches through Bash 5.3 patch 15,
ShellCheck 0.11.0 rule documentation, read-only maintained scripts, and
classified static-extraction examples. Bash is GPL-3.0-or-later; its manual is
GFDL-1.3-or-later without invariant sections or cover texts; ShellCheck is
GPL-3.0. APG copies or adapts no upstream or private expression or code. This
procedure is independently written synthesis and requires no named tool.

Source versions are evidence, not mandated project targets. Refresh before a
behavior-bearing correction, maturity review, or publication when Bash
semantics, supported representative versions, analyzer rules, or
false-escalation evidence materially change. Deprecation or removal must remove
the canonical leaf, checked projection, catalog and capability-map entries,
and focused tests while preserving ADR, evaluation, and exit history. No root
or private guidance is migrated, so rollback restores none of it.

## Project-owned parameters

The target repository owns supported Bash versions and platforms,
interpreter/shebang policy, POSIX compatibility, formatter and analyzer
choices, tests and coverage, exact commands, dependency and supply-chain
policy, artifact classifications, architecture, accepted exceptions,
deployment, privilege, mutation, release, destructive-action authority,
validation, and rollback.

## Evidence and completion

When material, report the Bash profile level, structural and semantic signals,
repository policy, required response, tests or measurements, accepted
exception if any, and rollback. Green needs applicable project checks; Yellow
adds local semantic and version evidence; Orange adds an accepted decision and
focused adverse-case validation; Red records the stopped action and condition
required for reconsideration.

## Stop or escalate

Stop or escalate when untrusted input reaches dynamic execution; an
uncontrolled source path can execute content; a destructive target is
unresolved; a secret or private path would be exposed; a consequential temp or
symlink race remains; a trap or background lifecycle can outlive authority or
lose cleanup; or meaningful new growth crosses Red without decomposition or an
accepted bounded exception.

## Common mistakes

- Treating every shell edit as Bash-profile work.
- Claiming Bash behavior is portable POSIX shell behavior.
- Treating strict-mode options as a safety proof.
- Flattening an argument vector into a command string.
- Using line count alone to select architecture.
- Letting a test or fixture label suppress a semantic Red stop.
- Forcing an unrelated rewrite of existing Red legacy code.
- Duplicating Bats harness guidance in the Bash owner.
- Inventing project versions, commands, tools, or action authority.
