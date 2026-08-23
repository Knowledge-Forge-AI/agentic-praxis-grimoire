# APG96 Go CLI Foundation and Python Report Migration Bridge Exit

Phase ID: `APG96`

## Status

**Complete — Go CLI report bridge terminally accepted.**

Terminal disposition:
`V07_GO_CLI_REPORT_BRIDGE_READY_FOR_APG97`.

## Outcome

APG96 adds `cmd/apgr`, private CLI and build-information packages, canonical
report show/diff/operational/ops/path/recover adapters, legacy omnibus
compatibility, deterministic supported-target builds, and version/corpus linker
injection. Public `report` APIs and accepted report bytes remain unchanged.

Python retains configuration and outbox resolution but delegates every normal
report action and the three historical names to Go through exact argv and no
shell. The frozen Python implementation is test-oracle-only, reached directly
through a test-owned entry. Missing Go execution fails closed without a Python
semantic fallback.

The source-checkout bridge is qualified, but final package-bundled platform
binaries remain APG100 work. Installed packages without a bundled or explicit
binary therefore cannot yet execute report routes independently of a checkout.

## Reconciliations

- APG95 is recorded as terminally operator-accepted at commit `04f13598...`,
  tree `fe3ca7a...`, without source-byte drift from the reviewed closeout tree.
- APG95's four ignored required read/encoding errors now fail immediately.
- Accepted ADR 0051 and the normative architecture state the accepted ops-only
  supersession rule: remove without copying forward; later operational evidence
  appends inside an existing Git primary.

## Preserved state

- Version remains 0.6.0.
- Skills remain 39/39/39/39 and 14 stable / 25 provisional.
- Discovery remains zero malformed, 9,504 description bytes, 9,492 characters,
  and the unchanged 9,527-byte ceiling.
- Public v0.6 artifacts remain immutable.
- No APG97, skill embedding, environment, hotspot, response migration, final
  wheel/npm packaging, JACA, `.flakes`, Nix, publication, or deployment occurs.

## Next authorization

APG97 may implement the canonical Go `skills` package, deterministic task
bundles, context-budget enforcement, bundle fingerprints, and isolated
task-scoped materialization only under separate authorization. This exit does
not begin APG97.
