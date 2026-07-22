---
name: zsh-language-profile
description: Use when Zsh-specific judgment is material to option state, arrays, expansion, globbing, autoloading, startup or interactive behavior, hooks, modules, processes, or warning and crisis thresholds beyond repository policy.
---

# Zsh Language Profile

## Core principle

Apply Zsh-specific judgment only when native Zsh behavior is material. Confirm
the interpreter, invocation mode, supported release range, and ambient option
state before relying on a semantic assumption. Use the highest justified
`Green — routine`, `Yellow — caution`, `Orange — warning`, or
`Red — crisis / stop` response for the current coherent decision.

Keep option, parameter, startup, autoload, hook, completion, module, and process
lifecycles explicit. Structural measurements warn about maintained hand-written
code whose state model is outgrowing shell; they neither choose architecture
nor authorize unrelated legacy rewrites.

## Do not use

Do not use this profile for:

- Bash, POSIX-shell, or another dialect with no material native Zsh behavior;
- ZUnit runner, assertion, discovery, configuration, or fixture behavior;
- generic implementation, debugging, planning, or review procedure;
- selecting a shell, framework, formatter, linter, test runner, completion
  system, plugin manager, or exact command;
- authorizing startup mutation, host changes, dependencies, privilege,
  publication, or destructive action;
- a typo, comment, rename, or edit with no material Zsh judgment;
- automatic broad refactoring of legacy startup or operational code; or
- structural treatment of generated, vendored, fixture, snapshot, migration,
  compatibility, or data artifacts before classification.

## Procedure

1. Establish task authority, repository instructions, interpreter/shebang,
   supported Zsh versions, invocation mode, platform, startup and interactive
   scope, option baseline, tests, mutation boundary, and rollback.
2. Classify relevant artifacts as maintained source, startup configuration,
   interactive code, test, legacy, generated, vendored, fixture, snapshot,
   migration, compatibility material, or data. Classification never suppresses
   a semantic Red stop.
3. Measure current and projected structure with configured repository tooling
   when available; otherwise use the APG fallback rules below.
4. Inspect `emulate` and local options, arrays, splitting, parameter-expansion
   flags, globbing, `fpath`, autoload, startup files, hooks, traps, ZLE,
   completion, modules, subprocesses, dynamic execution, destructive paths,
   secrets, and Bash/POSIX compatibility assumptions.
5. Assign the highest justified level. Three materially coupled Yellow signals
   normally justify Orange. Two materially coupled Orange signals affecting
   the same owner are presumptively Red unless a cohesive-artifact rationale,
   repository acceptance, evidence, validation, and rollback justify retaining
   Orange. One Red signal remains Red. Do not aggregate unrelated findings.
6. Proceed normally for Green; inspect policy and evidence for Yellow; require
   an accepted local design, rationale, rollback, and focused validation for
   Orange; stop Red growth or unsafe action pending decomposition, an accepted
   bounded exception, or governing authority.
7. Pair separately with an applicable process skill. A behavior change may
   keep `implementing-with-test-discipline` primary; a completion review may
   keep `reviewing-and-verifying-repository-work` primary. ZUnit work
   additionally needs its independently triggered test profile. APG19 retained
   none; APG22B subsequently retains only the exact ZUnit v0.8.2 and Zsh 5.9.2
   pair.
8. Preserve stricter repository policy. Relax only a profile default through
   accepted scope, rationale, evidence, validation, and rollback; never relax
   superior safety, privacy, compatibility, or authority rules.
9. Report level, signals, version and invocation assumptions, lifecycle and
   safety evidence, exception if any, validation, and rollback.

### Structural threshold contract

These defaults apply mainly to maintained hand-written Zsh. They are guidance
signals, not linter enforcement or automatic architecture selection.

| Signal | Green — routine | Yellow — caution | Orange — warning | Red — crisis / stop |
| --- | ---: | ---: | ---: | ---: |
| Script physical lines | `<= 200` | `201–300` | `301–500` | `>= 501` |
| Commands in one function or top-level region | `<= 15` | `16–25` | `26–40` | `>= 41` |
| Decision points | `<= 3` | `4–6` | `7–10` | `>= 11` |
| Maximum control/subshell nesting | `<= 2` | `3` | `4–5` | `>= 6` |
| Positional parameters | `<= 3` | `4–5` | `6–9` | `>= 10` |
| Distinct option mutations in one scope | `<= 2` | `3–5` | `6–9` | `>= 10` |
| Mutable global/cross-function parameters | `<= 2` | `3–5` | `6–9` | `>= 10` |
| Autoload/module/hook/ZLE/completion breadth | `<= 2` | `3–5` | `6–10` | `>= 11` |
| External process/pipeline families | `<= 2` | `3–5` | `6–9` | `>= 10` |
| Independent responsibility families | `1` | `2` | `3` | `>= 4` |

Count physical lines after universal-newline decoding; comments, blanks, and a
final non-empty unterminated segment count. Count simple and assignment-only
commands and each pipeline member; exclude comments, delimiter-only lines, and
heredoc payloads. Decision points include `if`, `elif`, loop conditions, each
`case` arm, and control-significant `&&` or `||`. Nesting is the maximum
simultaneously open control, subshell, or command/process-substitution boundary.

Positional count is the declared arity or highest directly interpreted slot;
variadic `$@` or `$*` begins at Yellow when validation is not explicit. Count
distinct options changed by `setopt`, `unsetopt`, or short equivalents;
`emulate -L zsh` is one baseline action rather than every implicit default.
Count independently mutable parameter owner domains assigned outside local
scope and read or changed across scopes; scalar aliases do not multiply the
count, and immutable one-time configuration is recorded separately.

Lifecycle breadth counts distinct `fpath` additions, autoloaded functions,
modules, hook/trap registrations, ZLE widgets or keymaps, and completion
systems. External breadth is the maximum coupled execution breadth owned by
one function or decision path: repeated aliases for one executable family do
not multiply the count, but independent pipeline members, substitutions,
coprocesses, and background stages do. Background lifecycle is semantic Red
whenever ownership or cleanup is unsafe. Option, parameter, and lifecycle
breadth remain separate signals and participate in combined-signal judgment.
Responsibilities are independently testable behavior families.

### Classification and proportional exceptions

Classify generated, vendored, fixture, snapshot, migration, compatibility, and
data-driven artifacts before structural action. An accepted coherent
compatibility matrix may receive a bounded line-count exception, but semantic
Red stops and other structural signals remain effective.

An existing Red legacy artifact may receive the smallest safe fix when it adds
no independent responsibility and no meaningful growth. Record a decomposition
or follow-up boundary. A major feature or new responsibility remains Red until
decomposition or an accepted bounded exception resolves it.

### Semantic response guide

- `emulate -L zsh` at a function boundary can be Green when native semantics
  are intended because it establishes local option restoration. Trap ownership
  remains separate. Ambient or leaked option mutation is Orange; unresolved
  privilege-sensitive or cross-boundary mutation is Red.
- Zsh arrays are one-based by default. Compatibility options can change
  indexing and expansion. Local documented compatibility is Yellow; mixed
  ambient indexing across an interface is Orange; likely destructive
  misaddressing is Red.
- Default Zsh does not apply ordinary shell-style word splitting. Controlled
  array or expansion-flag splitting can be Green or Yellow. Ambient
  `SH_WORD_SPLIT` is Orange; uncontrolled data split into commands or paths is
  Red.
- Parameter-expansion flags, `EXTENDED_GLOB`, glob qualifiers, null-match
  behavior, recursive globs, and symlink-following forms require version and
  option-state evidence. Code-executing qualifiers, uncontrolled execution, or
  unresolved recursive destructive globs are Red.
- Startup files have distinct all-invocation, login, interactive, and logout
  scopes. Startup changes are normally Orange and need exact target, clean
  invocation-mode evidence, and rollback. Unauthorized global startup mutation
  is Red.
- `fpath` is ordered and autoload may select compiled or source definitions.
  Fixed trusted paths and bounded autoload are Green or Yellow. Computed or
  writable search roots are Orange; untrusted roots are Red.
- Hooks share shell state and run in defined lifecycle positions. Hooks, traps,
  completion, modules, and ZLE work need idempotence, scope, registration and
  removal ownership. Cross-cutting coupling is Orange; untrusted modules or
  irreversible host mutation are Red.
- Fixed executable plus argument-vector subprocesses are Green. Pipelines,
  substitutions, and background work require explicit status and cleanup.
  Trusted unavoidable shell strings are normally Orange. Untrusted dynamic
  source, `eval`, interpolated command execution, or executable glob behavior
  is Red.
- `ERR_EXIT` or `set -e` is not proof of failure handling. Assuming uniform
  propagation through compound contexts is Orange and becomes Red when it
  permits unsafe continuation or false completion.
- Destructive globbing is Orange only with a resolved allowed root, bounded
  match set, operand separation, appropriate preview or confirmation, rollback,
  and authority. An empty, unresolved, symlink-crossing, or uncontrolled
  destructive glob is Red.
- Keep secrets, credentials, private paths, startup contents, and inherited
  environments out of examples and diagnostics. Plausible exposure is Orange;
  actual exposure is Red.
- Native Zsh is not Bash or POSIX shell by default. An invocation or
  compatibility change is Orange. A false compatibility claim governing
  consequential behavior is Red.

### Source and maintenance boundary

This profile was inspected and calibrated on 2026-07-21 from the official Zsh
5.9.2 release and manual sections for options, parameters, expansion, globbing,
functions, startup files, execution, builtins, modules, ZLE, completion, and
hooks, plus read-only maintained Zsh and classified examples. Zsh uses its
permissive distribution notice, with file-specific terms controlling some
contributions. APG copies or adapts no upstream or private expression or code;
this profile is independently written synthesis.

The current official release is evidence, not a mandated project target.
Refresh before a behavior-bearing correction, maturity review, or publication
when stable Zsh semantics, supported representative versions, lifecycle
behavior, or false-escalation evidence materially change. Do not treat
unreleased upstream development as a stable baseline. Removal must delete the
canonical leaf, checked projection, catalog and capability-map entries, and
focused tests while preserving ADR, evaluation, and exit history. No root or
private guidance is migrated, so rollback restores none of it.

## Project-owned parameters

The repository owns Zsh versions, interpreter and invocation mode, option
baseline, platform, startup scope, interactive behavior, completion, ZLE,
module and plugin policy, formatter and analyzer choices, tests, exact commands,
dependencies, artifact classifications, accepted exceptions, architecture,
privilege, mutation, destructive-action authority, validation, and rollback.

## Evidence and completion

When material, report the Zsh profile level, structural and semantic signals,
version, invocation and option inputs, lifecycle and target evidence, project
checks, accepted exception if any, and rollback. Orange requires an accepted
local design plus focused compatibility or adverse-case validation. Red records
the stopped action and exact condition for reconsideration.

## Stop or escalate

Stop or escalate when untrusted dynamic source, evaluation, or execution is
possible; a destructive glob or path lacks exact target control; global
startup, option, or hook mutation lacks authority or rollback; a secret or
private path would be exposed; a process can outlive authority or lose cleanup;
or meaningful new growth crosses Red without decomposition or an accepted
bounded exception.

## Common mistakes

- Treating Zsh as Bash or portable POSIX shell.
- Assuming array indexing or word splitting without checking option state.
- Letting option changes leak beyond their intended scope.
- Treating a complex glob as mere syntax instead of a target boundary.
- Loading autoload or plugin code from writable or uncontrolled paths.
- Treating startup, hook, completion, or ZLE changes as ordinary local edits.
- Treating `ERR_EXIT` as proof of observable failure handling.
- Using line count alone or rewriting unrelated Red legacy code.
- Duplicating a test harness owner inside the Zsh profile.
- Inventing project versions, commands, tools, or action authority.
