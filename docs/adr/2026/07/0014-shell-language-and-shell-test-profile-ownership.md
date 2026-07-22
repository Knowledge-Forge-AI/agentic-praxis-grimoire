# ADR 0014: Shell Language and Shell-Test Profile Ownership

## Status

Accepted

## Date

2026-07-21

## Acceptance authority

The human maintainer's APG19 assignment accepts this decision after current
source research, independent calibration and design criticism, frozen
scenarios, read-only dogfood, focused tests, and independent resulting-tree
review. It authorizes provisional Bash, Bats, and Zsh profiles in private
development. ZUnit is deferred. It does not authorize maturity promotion,
source migration, root reduction, private decommission, public release,
application smoke, or APG20.

## Context

Bash and Zsh share a broad shell lineage but differ materially in option state,
arrays, expansion, splitting, globbing, startup behavior, autoloading, and
interactive facilities. Bats and ZUnit add test-runner semantics that their
underlying languages do not own. A single generic shell owner would erase
those distinctions; embedding test-harness behavior in language profiles would
make ordinary implementation tasks load unrelated runner guidance.

Current sources support bounded Bash, Bats, and Zsh guidance. ZUnit's current
release remains v0.8.2 from 2018, its latest canonical commit is from 2020, and
its historical upstream runtime evidence ends at Zsh 5.3.1. Local use does not
establish current public support for stable Zsh.

## Decision

### Separate owners

- `bash-language-profile` owns Bash quoting, expansion, arrays, pipelines,
  traps, subprocesses, files, portability, and structural/semantic warnings.
- `bats-test-profile` owns Bats evaluation, `run`, status and output capture,
  hooks, skips, TAP and file descriptors, fixtures, parallelism, and harness
  cleanup. It consumes but does not duplicate Bash semantics.
- `zsh-language-profile` owns Zsh options, arrays, splitting, expansion,
  globbing, startup and interactive boundaries, autoload, hooks, ZLE,
  completion, modules, processes, and structural/semantic warnings.
- ZUnit retains a future separate test-harness ownership reservation but no
  operational APG profile. `zunit-test-profile` is
  `deferred-source-or-version`.

Interpreter, shebang, runner, invocation mode, and repository policy determine
the applicable owner. A shell-test task may pair a primary process skill, the
underlying shell profile, and a retained test profile only when every trigger
is independently material. No generic all-shell profile is adopted.

### Warning and structure contract

Retained profiles follow ADR 0012 and the language-profile contract. Structural
thresholds apply mainly to maintained hand-written scripts and tests.
Generated, vendored, snapshot, fixture, migration, compatibility, and
data-driven artifacts are classified before structural action. Classification
never suppresses a semantic Red stop.

One metric does not select architecture. One Red signal remains Red; three
materially coupled Yellow signals normally justify Orange; two materially
coupled Orange signals affecting the same owner are presumptively Red unless a
cohesive-artifact rationale, repository acceptance, evidence, validation, and
rollback justify retaining Orange. This is contextual judgment, not a score.

Red stops unsafe action and meaningful crisis-level growth. An existing Red
legacy artifact may receive the smallest safe fix without a new responsibility
or meaningful growth. A major new responsibility requires decomposition or an
accepted bounded exception. Repository policy may strengthen defaults and may
relax only profile defaults through accepted rationale, evidence, validation,
and rollback; superior safety, privacy, compatibility, destructive-action, and
authority rules remain controlling.

Every retained profile begins `provisional`. Aggregate application discovery
and explicit-use smoke remain deferred to APG23 and APG24.

### ZUnit re-entry condition

ZUnit may be reconsidered when a canonical upstream or clearly maintained
successor publishes a current release or commit with a supported range covering
current stable Zsh and APG freshly verifies runner, assertion, hook,
configuration, discovery, output, and lifecycle behavior. A legacy-only
v0.8.2 profile would require separate authorization and fresh compatibility
testing over an explicitly pinned historical runtime range.

## Subsequent APG22B disposition

The maintainer separately authorized legacy, version-bounded evaluation in
APG22B. A disposable unprivileged harness built and tested exact ZUnit v0.8.2
with Zsh 5.3.1 and 5.9.2. The 5.3.1 runner dependency probe did not complete on
the tested environment, so that pair is unsupported and excluded. The exact
5.9.2 pair passed the tagged 98-test upstream suite, seven APG focused tests,
expected adverse cases, and cleanup checks.

APG22B therefore retains `zunit-test-profile` provisionally for exactly ZUnit
v0.8.2 with Zsh 5.9.2. It claims no version range or other platform. The owner
remains separate from `zsh-language-profile`, and every different pair stops
pending fresh disposable evidence. This subsequent disposition satisfies the
legacy re-entry path without rewriting APG19's truthful source/version
deferral.

## Subsequent APG22C disposition

APG22C reproduced that APG22B installed its startup sentinel under the
temporary home while supplying a separate `ZDOTDIR`. The original sentinel-
absence assertion therefore did not prove selected user-startup isolation.

The corrected harness places the sentinel at the selected `ZDOTDIR/.zshenv`,
requires an unsuppressed positive control to load it, requires `-f` to suppress
it, and requires the focused ZUnit test process to observe its absence. The
corrected exact matrix retains ZUnit v0.8.2 with Zsh 5.9.2, preserves Zsh 5.3.1
as unsupported because its independent dependency probe times out, and makes
no broader startup, version-range, or platform claim. No skill wording,
ownership, maturity, or distribution decision changes.

## Alternatives considered

### One generic shell profile

Rejected. It would conflate Bash and Zsh semantics and test-harness behavior.

### Bash and Zsh only

Rejected as the complete architecture because current Bats evidence supports
an independently useful harness trigger. It remains the implemented language
subset when a framework profile is not material.

### Embed Bats in Bash and ZUnit in Zsh

Rejected. Harness evaluation, assertions, lifecycle, and output behavior are
independent of ordinary production-language work.

### Four separate owners

Accepted as the ownership architecture, but only Bash, Bats, and Zsh are
implemented. ZUnit's owner is reserved and deferred rather than fabricated.

### Defer the unsupported or stale framework

Accepted for ZUnit. Local use cannot substitute for current upstream/runtime
support evidence in a public-facing profile.

### Copy private shell standards

Rejected. Private commands, platform policy, preferences, and machine state
remain with their current owners.

### Independently synthesize calibrated profiles

Accepted. APG uses current public semantics, measured read-only examples,
frozen scenarios, and independently written expression.

## Consequences

Private development contains twelve canonical skills and projections, six
stable process rows, six provisional rows, and eleven routable non-router
capabilities. Public v0.2.0, active integration, the six-skill managed defaults,
and schema version 1 remain unchanged.

The separation improves routing precision but adds maintenance work. Bash,
Bats, and Zsh source/version assumptions and false-escalation evidence require
refresh. ZUnit users receive an explicit source/version limitation rather than
unsupported current guidance.

## Migration and rollback

APG19 migrates or removes no root or private guidance. Each retained profile is
independently reversible: remove only its canonical leaf, relative projection,
catalog and capability-map row, known-unmanaged treatment, and focused tests,
while preserving this ADR, evaluation, and exit history. Removing Bats does not
remove Bash; removing Zsh does not create or restore ZUnit. ZUnit has no
implementation rollback surface; its deferred evidence and re-entry condition
remain historical.

Public release, active integration, maturity, and application smoke remain
separate future decisions. APG20 does not begin automatically.

APG22B adds the independently reversible ZUnit leaf, relative projection,
catalog and capability-map entries, known-unmanaged handling, focused tests,
and compatibility fixtures. Removing it restores the preceding development
shape while preserving APG19 and APG22B records. Public v0.2.0, the six managed
defaults, schema version 1, active integration, and root/private guidance
remain unchanged.
