---
name: zunit-test-profile
description: Use when a repository explicitly uses the APG-verified ZUnit v0.8.2 and Zsh 5.9.2 pair and needs ZUnit-specific judgment about runner invocation, discovery, assertions, hooks, configuration, output, isolation, process cleanup, compatibility, or warning and crisis thresholds beyond repository policy.
---

# ZUnit Test Profile

## Core principle

Apply this profile only to ZUnit v0.8.2 with Zsh 5.9.2. APG directly verified
that exact pair in a disposable source-built environment. No version range is
verified. ZUnit v0.8.2 with Zsh 5.3.1 is unsupported by the APG compatibility
harness because the runner's dependency probe did not complete. Every other
pair is unverified and stops pending a fresh disposable compatibility run.

Own ZUnit runner, discovery, assertions, hooks, configuration, output,
fixtures, isolation, lifecycle, and structural judgment. Leave Zsh option,
expansion, startup, command-construction, and process semantics to
`zsh-language-profile` when independently material. Apply the highest justified
`Green — routine`, `Yellow — caution`, `Orange — warning`, or
`Red — crisis / stop` response. A level is an evidence requirement, not action
authority or maturity.

## Do not use

Do not use this profile for:

- any ZUnit/Zsh pair other than v0.8.2 with 5.9.2;
- ordinary Zsh work without material ZUnit behavior;
- another Zsh test framework or a trivial edit with no framework judgment;
- choosing ZUnit, Zsh, Revolver, the runner command, CI platform, or coverage;
- generic implementation, debugging, planning, or review procedure;
- global installation, startup-file mutation, live host mutation, or framework
  maintenance;
- inferring current support from an upstream minimum or adjacent version;
- automatic broad restructuring of legacy tests; or
- structural action on generated, vendored, fixture, snapshot, compatibility,
  or data-driven artifacts before classification.

## Procedure

1. Establish task authority, repository policy, platform, exact ZUnit and Zsh
   versions, Revolver identity, runner invocation, configuration, discovery
   roots, isolation, expected checks, process policy, and rollback.
2. Stop unless the pair is exactly ZUnit v0.8.2 with Zsh 5.9.2. Reverify the
   exact pair in a disposable environment when the platform or runner boundary
   differs materially from APG evidence.
3. Classify the artifact as maintained test, helper, legacy, generated,
   vendored, fixture, snapshot, compatibility matrix, or data. Classification
   never suppresses semantic Red.
4. Inspect the required ZUnit shebang, unique test identities, explicit or
   configured discovery, `.zunit.yml`, support/bootstrap scope, `@setup` and
   `@teardown`, skips, risky tests, output mode, and cleanup ownership.
5. For every material command executed through `run`, assert `$state`
   explicitly. Assert `$output` or `$lines` when output matters. ZUnit's
   numeric `equals` and textual `same_as` are not interchangeable. Prefer
   `$lines` for multiline exactness because v0.8.2 comparison forwarding splits
   newline-bearing arguments.
6. Measure the current and projected structure using repository tooling when
   present, otherwise the fallback rules below. Assign the highest structural
   or semantic level.
7. Three materially coupled Yellow signals normally justify Orange. Two
   materially coupled Orange signals over one owner are presumptively Red.
   One Red signal remains Red. Do not aggregate unrelated findings.
8. Proceed proportionally for Green; inspect policy and evidence for Yellow;
   require an accepted local design, rollback, and focused adverse-case
   validation for Orange; stop false passes, unsupported pairs, leaks, unsafe
   mutation, or crisis-level Red growth.
9. Pair independently with a process skill and, only when Zsh language
   semantics are material, `zsh-language-profile`. Implementation may keep
   `implementing-with-test-discipline` primary; review may keep
   `reviewing-and-verifying-repository-work` primary.
10. Preserve stricter repository policy. Record level, signals, exact pair,
    runner and assertion evidence, isolation, cleanup, exception, and rollback.

### Structural threshold contract

These defaults apply mainly to maintained hand-written ZUnit tests. They are
guidance, not automatic enforcement or architecture selection.

| Signal | Green — routine | Yellow — caution | Orange — warning | Red — crisis / stop |
| --- | ---: | ---: | ---: | ---: |
| Test-file physical lines | `<= 150` | `151–300` | `301–500` | `>= 501` |
| Tests per file | `<= 8` | `9–15` | `16–24` | `>= 25` |
| Commands in one test body | `<= 12` | `13–20` | `21–35` | `>= 36` |
| Setup/teardown/bootstrap span | `<= 25` | `26–50` | `51–80` | `>= 81` |
| Helper function span | `<= 20` | `21–35` | `36–50` | `>= 51` |
| Mutable shared fixture/state domains | `<= 3` | `4–6` | `7–10` | `>= 11` |
| Cleanup-owned children/jobs | `<= 1` | `2–3` | `4–5` | `>= 6` |
| Independent responsibilities | `1` | `2` | `3` | `>= 4` |

Count physical records after universal-newline decoding, including comments,
blank lines, heredoc payload, and a final unterminated segment. Count only
runner-recognized `@test` declarations under v0.8.2's line-oriented discovery
grammar. A declaration-like heredoc line or duplicate identity is a discovery
defect to resolve, not a reason to inflate a valid count. Static counting must
not execute target tests.

For each test body, count Zsh grammar commands or compound-command starts;
continuations count once, while comments, blanks, delimiter-only lines, and
heredoc payload do not. Setup/teardown/bootstrap and helper spans use physical
lines from the opening declaration through its closing delimiter, including
comments, blanks, and heredoc payload; use the largest individual span.

Count independently mutable state or resource-owner domains visible across
tests or lifecycle scopes, not aliases or per-test values recreated in an
owned temporary directory. Count the maximum simultaneously alive children or
jobs whose cleanup this test owner controls; any unowned or leaking child is
semantic Red regardless of count. Responsibilities are independently
changeable behavior families.

Validate exact first values when calibrating: 151 lines, 9 tests, 13 commands,
26 setup lines, 21 helper lines, 4 shared domains, 2 owned children, and 2
responsibilities are Yellow; 301, 16, 21, 51, 36, 7, 4, and 3 are Orange; 501,
25, 36, 81, 51, 11, 6, and 4 are Red.

### Classification and proportional exceptions

Classify generated, vendored, fixture, snapshot, compatibility, migration, and
data-driven artifacts before structural action. A coherent repository-accepted
data matrix may receive a bounded line-count-only exception when executable
structure remains reviewable. Semantic Red and every other signal remain.

An existing Red legacy test may receive the smallest safe fix when it adds no
responsibility and no meaningful growth. A new responsibility in Red remains
Red. An accepted bounded exception records scope, rationale, owner, evidence,
refresh or expiry, validation, rollback, and why no semantic Red is hidden.

### Harness response guide

- Invoke the repository-owned runner with explicit startup isolation. ZUnit
  v0.8.2 requires Revolver in `PATH`. A missing or unresolved dependency,
  runner, or discovery boundary is Red.
- Discovery is recursive over supplied directories. Test files require the
  ZUnit shebang. Require unique, reviewable test identities because the pinned
  parser does not provide a sufficient duplicate-identity guarantee.
- `run` captures command status in `$state`, combined output in `$output`, and
  split lines in `$lines`. A nonzero command does not itself fail the test. An
  assertion-free materially required status is Red, even though the runner
  reports an assertion-free test as risky.
- A bounded, reasoned skip records no passing behavior. A completion claim
  depending on an unaccepted critical skip is Red. Do not use a version skip to
  represent an unverified pair as supported.
- Bootstrap state is shared. Setup and teardown are per test. Teardown and the
  runner time limit do not replace explicit ownership of temporary resources,
  children, signals, interruption behavior, or rollback.
- Fixed executables with explicit argument vectors can be Green. Dynamic shell
  strings are Orange when trusted and unavoidable. Untrusted input reaches
  dynamic shell evaluation is Red and requires a stop.
- Shared writable state is at least Yellow. Order-dependent state without
  accepted isolation is Red. Use an owned disposable directory and prove
  cleanup.
- TAP, text, HTML, verbose output, command capture, bootstrap messages, and
  failure diagnostics must exclude secrets, credentials, protected payloads,
  and private paths. An actual leak is Red.
- A background child that can leak, hang, or survive cleanup is Red. A timeout
  is containment, not proof of cleanup ownership.
- Real startup configuration or destructive host action requires exact
  authority, an isolated target, preview where appropriate, rollback, and
  adverse-case evidence. Otherwise stop at Red.

### Source and maintenance boundary

This profile was calibrated on 2026-07-21 from the MIT-licensed ZUnit v0.8.2
release, tagged source, documentation, runner, assertions, hooks,
configuration, discovery, output, upstream tests, and historical CI; the
MIT-licensed Revolver v0.2.4 tag; and official Zsh 5.3.1 and 5.9.2 releases.
APG copies no upstream expression. The exact 5.9.2 pair passed the tagged
upstream and APG compatibility suites; the exact 5.3.1 pair stopped at the
runner dependency probe on the tested environment.

Refresh before a behavior-bearing correction, maturity review, or publication;
when a project changes ZUnit, Zsh, Revolver, platform, runner, configuration,
or output mode; or when discovery, assertion, hook, process, or cleanup
semantics are disputed. Removal deletes the leaf, relative projection, catalog
and capability-map entries, known-unmanaged handling, focused tests, and
compatibility fixtures while preserving ADR, evaluation, and exit history.

## Project-owned parameters

The repository owns exact versions, platform, Revolver source, runner command,
startup isolation, discovery roots, configuration, output mode, test names,
helpers, fixtures, time limits, process policy, CI, coverage, artifact
classification, accepted exceptions, authority, validation, and rollback.

## Evidence and completion

Report the exact pair, platform and runner boundary, level, structural and
semantic signals, discovery and assertion evidence, lifecycle and output
behavior, upstream and focused results, cleanup and no-residue evidence,
accepted exception, and rollback. Unsupported or unverified pairs report the
stopped condition; they never become successful evidence.

## Stop or escalate

Stop when the pair is outside the verified matrix; runner or discovery behavior
is unresolved; a material status can false-pass; startup or host configuration
would be mutated without isolation and authority; shared state is
order-dependent; a child can leak or hang; protected data can enter output;
untrusted input reaches dynamic shell evaluation; a destructive action lacks
authority and rollback; unsupported behavior is represented as verified; or
meaningful Red growth lacks decomposition or an accepted bounded exception.

## Common mistakes

- Inferring a version range from one exact passing pair.
- Treating historical Zsh 5.3.1 CI as current APG compatibility evidence.
- Using numeric `equals` for text or assuming multiline shorthand is exact.
- Assuming `run` fails a test without an explicit status assertion.
- Treating risky-test reporting, teardown, or a timeout as complete safety.
- Letting duplicate names, startup state, shared fixtures, or children escape
  review.
- Duplicating Zsh semantics instead of pairing the Zsh profile when material.
- Using structure levels as permission, maturity, or automatic rewrite rules.
- Inventing project versions, commands, dependencies, or action authority.
