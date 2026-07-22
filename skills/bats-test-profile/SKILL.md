---
name: bats-test-profile
description: Use when Bats-specific test judgment is material to evaluation, run status and output, hooks, fixtures, TAP, file descriptors, parallelism, background cleanup, or warning and crisis thresholds beyond repository policy.
---

# Bats Test Profile

## Core principle

Apply Bats-specific judgment only when the task materially depends on the Bats
harness. Establish the repository's Bats and Bash versions before relying on a
runner feature. Use the highest justified `Green — routine`,
`Yellow — caution`, `Orange — warning`, or `Red — crisis / stop` response for
the current coherent decision.

Own Bats evaluation, `run`, assertion state, hooks, skips, TAP and file
descriptor behavior, fixture scopes, parallel-test isolation, and harness
cleanup. Leave Bash quoting, expansion, pipelines, traps, and command
construction to `bash-language-profile` when those semantics are independently
material.

## Do not use

Do not use this profile for:

- ordinary Bash implementation or review with no material Bats behavior;
- Bash language semantics already owned by `bash-language-profile`;
- choosing Bats, helper libraries, a runner version, formatter, coverage tool,
  CI platform, or exact test command;
- generic implementation, debugging, planning, or review procedure;
- authorizing live services, host mutation, credentials, or destructive action;
- a typo, comment, rename, or test edit with no harness-specific judgment;
- automatic broad restructuring of legacy tests; or
- structural judgment of generated, vendored, fixture, snapshot, migration,
  compatibility, or data-driven artifacts before classification.

## Procedure

1. Establish task authority, repository policy, selected Bats and Bash
   versions, platform, helper libraries, runner flags, parallel policy,
   isolation boundary, exact checks, and rollback.
2. Classify the artifact as maintained test, helper, legacy, generated,
   vendored, fixture, snapshot, migration, compatibility matrix, or data.
   Classification never suppresses a semantic Red stop.
3. Measure current and projected test structure using repository tooling when
   present. Otherwise use the APG fallback rules below.
4. Inspect file evaluation, `run`, required status and output assertions,
   hooks, suite setup, skips, version guards, TAP output, file descriptor 3,
   temp scopes, parallelism, shared state, background children, teardown, and
   rollback.
5. Assign the highest justified level. Three materially coupled Yellow signals
   normally justify Orange. Two materially coupled Orange signals affecting
   the same owner are presumptively Red unless a cohesive-artifact rationale,
   repository acceptance, evidence, validation, and rollback justify retaining
   Orange. One Red signal remains Red. Do not aggregate unrelated findings.
6. Proceed proportionally for Green; inspect policy and evidence for Yellow;
   require an accepted local design, rationale, rollback, and focused
   validation for Orange; stop a Red false-pass, leak, unsafe mutation, or
   crisis-level growth.
7. Pair independently with a process skill and, only when material, the Bash
   profile. A behavior change can keep `implementing-with-test-discipline`
   primary; a test review can keep
   `reviewing-and-verifying-repository-work` primary.
8. Preserve stricter repository policy. Relax only a profile default through
   accepted scope, rationale, evidence, validation, and rollback; never relax
   a superior safety, privacy, compatibility, or authority stop.
9. Report level, signals, version and runner assumptions, assertions,
   isolation and cleanup evidence, exception if any, and rollback.

### Structural threshold contract

These defaults apply mainly to maintained hand-written Bats tests. They are
guidance, not automatic enforcement or architecture selection.

| Signal | Green — routine | Yellow — caution | Orange — warning | Red — crisis / stop |
| --- | ---: | ---: | ---: | ---: |
| Test-file physical lines | `<= 200` | `201–350` | `351–600` | `>= 601` |
| Test count | `<= 12` | `13–24` | `25–40` | `>= 41` |
| Maximum test-body commands | `<= 15` | `16–25` | `26–50` | `>= 51` |
| Maximum setup/teardown/bootstrap commands | `<= 12` | `13–20` | `21–35` | `>= 36` |
| Maximum helper commands | `<= 20` | `21–35` | `36–50` | `>= 51` |
| Shared fixture/global-state owners | `0–1` | `2–3` | `4–5` | `>= 6` |
| Maximum concurrent background child groups | `0` | `1, fully owned` | `2–3, fully owned` | `>= 4, or any unowned/leaking child` |
| Independent responsibility families | `1` | `2` | `3` | `>= 4` |

Count physical records after universal-newline decoding, including comments,
blank lines, and a final unterminated segment. Count runner-recognized tests,
including native `@test` declarations and supported comment function forms.
Exclude incidental comments, strings, heredoc data, generated fixtures, and
static-extraction samples. Do not evaluate a Bats file merely to count tests
without authority to run that target code.

For each test, hook, or helper, count shell grammar commands or compound-command
starts; continuations count once, while comments, blanks, delimiter-only lines,
and heredoc payloads do not. Use the maximum individual body. Count mutable
independently mutable state or resource owner domains visible to multiple tests
or file/suite hooks, not scalar aliases or per-test values recreated under the
per-test temporary directory. Count the
maximum simultaneously alive child or service groups, not sequential external
commands. Responsibilities are independently changeable behavior families.

### Classification and proportional exceptions

Classify generated, vendored, fixture, snapshot, migration, compatibility, and
data-driven tests before structural action. A repository-accepted coherent
matrix may lower a line-count-only response by at most one level when no other
Red signal applies and bounded growth is justified. It does not relax shared
state, lifecycle, status, safety, privacy, or authority stops.

An existing Red legacy suite may receive the smallest safe fix when it adds no
independent responsibility and avoids meaningful growth. A new responsibility
or major feature remains Red pending decomposition or an accepted bounded
exception.

### Harness response guide

- A Bats file is evaluated once to count tests and once per test in a separate
  process. Keep free code declarative and bounded. Repeated mutation is Orange;
  output that corrupts TAP or exposes protected data is Red.
- `run` records command status in `$status`, combined output in `$output`, and
  lines in `$lines`, while returning control to the test. Plain `run` requires
  an explicit status assertion whenever status is material. An output-only
  intent can be Yellow when explicit; ambiguity is Orange; a materially
  required status that can false-pass is Red.
- Shell parsing places a literal pipeline in `run producer | consumer` outside
  the intended `run` boundary. Use the version-supported Bats pipeline helper
  form when repository policy selects it, and assert the selected or expected
  status explicitly. Bats owns `run` and helper capture semantics; the Bash
  profile owns the underlying pipeline and command construction. Neither
  `set -e` nor `pipefail` replaces an observable test assertion.
- Runner forms that assert expected status are version-sensitive repository
  choices. Exact, semantic output assertions can be Green. Regex, ordering,
  locale, empty-line, or channel assumptions are Yellow until verified.
- Per-test `setup` and `teardown`, file hooks, and suite hooks have different
  scopes. Shared file or suite state is at least Yellow, consequential external
  state is Orange, and order-dependent state without accepted isolation is
  Red. Cleanup must be explicit even when teardown normally follows failure.
- A skip with an explicit reason and bounded version or platform condition is
  Yellow because it records no passing behavior. A completion claim depending
  on an unaccepted critical skip is Red.
- Bats separates test output from TAP with file descriptor 3. A long-running
  background child inheriting file descriptor 3 can hang the run. One child
  with explicit descriptor closure, PID ownership, wait/kill, and teardown is
  Yellow; two or three are Orange; any child that can leak, hang, or survive
  cleanup is Red regardless of count.
- Serial execution is the default; parallel order is not guaranteed. Isolated
  parallel fixtures are Yellow and need repeated evidence. Shared writable
  locations require Orange design evidence; order dependence is Red.
- Prefer the runner's per-test temporary directory for isolated resources.
  File/suite temporary roots are shared and at least Yellow. Fixed or live
  paths require Orange isolation review; unisolated live or destructive
  mutation is Red.
- Secrets or private payloads must not enter TAP, diagnostics, fixtures, or
  captured output. Plausible exposure is Orange; actual exposure is Red.
- A timeout does not replace PID ownership, descriptor closure, teardown, or
  rollback.

### Source and maintenance boundary

This profile was inspected and calibrated on 2026-07-21 from bats-core 1.13.0
documentation and source, including evaluation, `run`, hooks, parallelism,
support-matrix, TAP, and file-descriptor behavior, plus read-only Bats suites.
bats-core and its associated documentation are MIT-licensed. APG copies or
adapts no upstream or private expression or code; this profile is independently
written synthesis.

The inspected support matrix and local runner are evidence, not a universal
minimum or target. Refresh before a behavior-bearing correction, maturity
review, or publication when Bats releases, Bash support, evaluation, runner
flags, hooks, parallelism, file descriptors, or representative
false-escalation evidence materially change. Removal must delete the canonical
leaf, checked projection, catalog and capability-map entries, and focused tests
while preserving ADR, evaluation, and exit history. No private guidance is
migrated, so rollback restores none of it.

## Project-owned parameters

The repository owns Bats and Bash versions, helper libraries, file layout,
runner flags, formatter, TAP consumer, parallelism, timeouts, fixtures,
temporary roots, live-service policy, test commands, coverage, CI, artifact
classification, accepted exceptions, authority, validation, and rollback.

## Evidence and completion

When material, report the Bats profile level, structural and harness signals,
version and policy inputs, status/output assertions, hook scope, isolation,
background ownership, test evidence, exception if any, and rollback. Orange
requires an accepted local design and focused adverse-case evidence. Red
records the stopped false-pass, leak, unsafe mutation, exposure, or growth and
the condition required before reconsideration.

## Stop or escalate

Stop or escalate when a test mutates live or destructive state without exact
authority and disposable isolation; a background child can hang, leak, retain
file descriptor 3, or survive cleanup; a test can pass without validating a
materially required status; secrets or private payloads can leak; suite-level
state makes results order-dependent without accepted isolation; or meaningful
new growth crosses Red without decomposition or an accepted bounded exception.

## Common mistakes

- Treating ordinary Bash work as Bats-profile work.
- Duplicating Bash quoting or pipeline rules in the harness owner.
- Assuming plain `run` fails the test on a nonzero command status.
- Treating output assertions as status assertions.
- Printing uncontrolled free-code output into TAP.
- Letting a background child inherit file descriptor 3.
- Enabling parallelism over shared writable fixtures without evidence.
- Treating teardown or a timeout as complete lifecycle ownership.
- Using line count alone or granting unlimited test-matrix exceptions.
- Inventing project helpers, commands, versions, or action authority.
