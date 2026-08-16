# APG49 matryer/is Validation and Integration

Status: Complete — candidate deferred after a new corrected-state material
defect; ADR 0026 remains controlling and no Go testing stack exists.

## Scope

APG49 preserved and verified the exact immutable APG48 authoring input,
validated its Git-show and associated operational report, delivered the exact
previously absent authoring branch, and created one forward Codex branch.
APG48 was not amended, rebased, squashed, recreated, or otherwise rewritten.

The phase independently:

- obtained byte-exact matryer/is v1.4.1 source and upstream tests;
- re-read the five bounded dogfood repositories at their recorded identities;
- created and ran public-safe failing-first controls;
- ran isolated exact-version compatibility probes;
- collected independent source, owner, structural, rights, and privacy
  findings;
- applied one coherent candidate correction pass;
- performed fresh corrected-state review; and
- terminally decided ADR 0030 without speculative integration.

## Exact source and rights

The canonical lightweight `v1.4.1` tag peels to upstream commit
`02e4121244e0f9e27b5ebdade62f5da7b7a42f23`. The module checksum is
`h1:55ehd8zaGABKLXQUe2awZ99BD/PTc2ls+KV/dXphgEQ=` and the module-file
checksum is `h1:8I/i5uYgLzgsgEloJE1U6xx5HkBQpAZvepWuujKwMRU=`. Byte-level
review covered the module and license, both Go-version implementation files,
the shared implementation, and relevant upstream tests. The active probe
toolchain selected `is.go` and `is-1.7.go`.

The source is MIT licensed. APG49 guidance was independently worded; no
material source expression or license text entered a public artifact, and no
new notice duty arose. Raw source and runtime output remain excluded from the
public surface.

## Dogfood and no-stack result

Read-only reverification confirmed two direct v1.4.1 users, one unused
indirect declaration, one project-convention negative, and one native-only
checksum-drift negative. It narrowed two authoring-time labels: three
dependency entries across two repositories were checksum-only rather than
indirect requirements, and one
subtest-count claim lacked a recorded counting method. Neither affected owner
or severity conclusions.

Maintained use reproduced optional direct component value, go-cmp diff strings
consumed by exact string assertions, and a parent-bound instance used in child
subtests. No recurring case showed two direct owners giving contradictory
answers about the same observable contract. `go-testing-stack` remains
`not-authored-no-independent-value`; no stack artifact exists.

## Failing-first and runtime results

The exact APG48 candidate produced seven failures — six expected semantic
failures and one expected pre-integration-state failure — and three passes.
The failures covered:

- import-first then selected-version triggering;
- exact nil kinds and the unsafe boundary;
- line-oriented lexical diagnostics;
- legitimate diff-string composition;
- native parent/child lifecycle;
- lexical source-filename frame exclusion; and
- the intentionally absent integration surfaces.

Isolated probes confirmed the six reflected nil kinds, excluded
`unsafe.Pointer` and `uintptr`, one-sided rendering, the unconditional
reflected-value-wrapper fallback, strict and relaxed routing, helper
registration and wrong-instance behavior, native-helper divergence, bounded
fallback, parent/child lifecycle, lexical diagnostic failure modes, protected
diff exposure with sanitized data, shared-registry race behavior, and
race-clean separate instances.

## One correction pass

The single correction pass implemented the manager-predeclared M1 through M5
findings and the independent filename-exclusion finding. It also repaired
public/private expression independence, strengthened protected-output and
public-safety controls, and truthfully preserved a supplied author-review file
as APG49 evidence rather than representing it as part of APG48.

The corrected focused result was nine passes and one expected pre-integration
failure. Rights/privacy review passed with no material five-token source or
private-ledger overlap.

## Corrected-state disposition

Fresh non-author review then found new material candidate defects:

1. strict parent-bound child use was Red in prose but Orange in the
   controlling structural table;
2. another selected version was both a source-refresh stop and a non-trigger
   in the specification;
3. the source-filename exclusion omitted the exact terminal anchor and
   misstated suffix-match and relocation boundaries; and
4. scenario identifiers were counted but one frozen scenario family had been
   reassigned, so semantic continuity was not proved.

The one-cycle rule permits no second behavior correction.
`matryer-is-test-profile` is therefore `deferred-material-defect`. Its current
leaf, specification, fixture, and focused owner are forward removed. The exact
source, dogfood, probe, correction, and review evidence remains durable.

## Architecture and current state

ADR 0030 is Rejected. ADR 0026 remains Accepted and controlling as the complete
current Go owner-graph record. ADR 0025 and ADR 0027 remain Rejected.
Development remains:

```text
28 canonical skills
28 catalog rows
28 relative projections
14 stable and 14 provisional
26 general-router entries
1 ChatGPT-local entry
27 checked route edges
```

No projection, catalog row, route, release-policy row, strict inventory owner,
dependency, or runtime is added. Public and active corrected v0.4.0 remain
unchanged at 28/28/28.

## Repository validation

Terminal no-retention validation passed:

- 339 unit tests;
- 271 integration tests with 2 skips;
- combined coverage at 4720/5042 statements and 1747/1928 branches;
- 23 configured Bats tests;
- Python compilation, shell syntax, command help, JSON, skill-library,
  record-identity, projection install/check/uninstall, privacy, provenance,
  links, complete diff, and whitespace checks.

The initial integration invocation exposed only an isolated test-environment
PATH omission for Bats. The focused case and complete suite passed after the
repository's exact test environment was combined with the original tool PATH;
no source change was made for that environment issue.

## Boundaries

No dogfood repository was changed or tested. No unverified matryer/is version
was claimed compatible. No Go testing stack, web or Node profile, readiness,
release, publication, deployment, target mutation, or successor phase began.
Any renewed component attempt requires separate maintainer authority, fresh
exact-source evidence, and a new correction and decision boundary.
