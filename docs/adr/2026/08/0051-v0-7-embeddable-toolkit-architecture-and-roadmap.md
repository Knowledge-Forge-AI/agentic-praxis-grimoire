# ADR 0051: v0.7 Embeddable Toolkit Architecture and Roadmap

## Status

Accepted

## Decision date

2026-08-21

## Context

APG v0.6.0 is terminally published as a 39-skill corpus and Python-distributed
CLI/repository tool. JACA is an active Go consumer that needs reusable APG
engineering primitives in-process, without invoking `apgr` or a shell. Portable
environment snapshot behavior also exists under `.flakes`, while structural
hotspot analysis and task-scoped context are not yet APG product surfaces.

Retaining Python and CLI invocation as the only reusable boundary would force
JACA through processes, intermediate files, and command-oriented contracts.
Rewriting for performance is not the objective; the objective is one embeddable,
provider-neutral library authority with compatible distribution adapters.

Current source establishes three constraints. APG reporting already has exact
Git/report/outbox compatibility semantics. JACA uses Go 1.25,
`context.Context`, exact-argv Git processes, strict JSON evidence, and SHA-256
artifact identities. `.flakes` environment capture uses typed allowlists,
owner-only atomic files, no-churn writes, metadata hashes, and thin prompt hooks.
The source identities and working-state qualifications are recorded in
publication-excluded APG94 evidence and are not public architecture gates.

The dispatcher plan review also required APG94 to remove two architecture
disjunctions: package layout and npm package name.

## Decision

1. Adopt the library-first Go direction. JACA imports APG public packages
   directly; APG does not import JACA or own orchestration.
2. Add one root Go module in APG95 with path
   `github.com/Knowledge-Forge-AI/agentic-praxis-grimoire`, Go 1.25 minimum,
   shared repository tag `v0.7.0`, `cmd/apgr`, and root domain packages
   `schema`, `report`, `skills`, `envsnap`, and `hotspot`. Do not use `pkg/` or a
   nested `/go` module.
3. Keep process and filesystem implementations under `internal/`. JACA may not
   import them. Initial Git collection uses native `git` through exact argv and
   `exec.CommandContext`; it never invokes a shell.
4. Make `report` the first vertical slice. Separate collection, normalized
   in-memory records, deterministic rendering/parsing, and optional publication.
   Preserve the current envelope and show/diff/operational schema bytes, IDs,
   field order, hashes, path safety, primary supersession, locking, atomicity,
   stdout/stderr, and error classes. APG95 must prove differential golden parity
   before Python stops owning behavior.
5. Use a strangler migration. The Go CLI adapts public libraries. Python
   delegates each migrated portable action and retains only classified
   repository/host maintenance during v0.7. JavaScript is an npm launcher only.
6. Keep `src/agentic_praxis_grimoire/VERSION` as the one editable version
   authority. Release builds inject and verify it in the Go binary; Go, GitHub,
   PyPI, npm, Nix handoff, embedded resources, and checksums share the same
   v0.7.0 identity.
7. Distribute Python through platform-specific wheels containing the Go binary
   for `darwin/arm64`, `linux/amd64`, and `linux/arm64`. Preserve the `apgr`
   console script and `python -m agentic_praxis_grimoire`. The sdist requires a
   compatible Go toolchain. Do not download a binary at runtime and do not use
   Go FFI/cgo.
8. Name the npm launcher `@knowledge-forge-ai/apgr`, with same-version optional
   platform packages `apgr-darwin-arm64`, `apgr-linux-x64`, and
   `apgr-linux-arm64` in that scope. The launcher verifies and spawns the binary
   and owns no semantics.
9. Keep canonical skill Markdown in `skills/`. The Go `skills` package embeds
   those exact leaves directly. Resolve task bundles only from versioned
   structured facts, explicit IDs, deterministic rule tables, and fail-closed
   byte budgets. Composition edges never create an implied mandatory profile
   chain. Materialize an owner-only agent-scoped discovery root; qualification
   fails if the same agent still sees the global APG root.
10. Preserve the v0.6 9,527-byte global discovery ceiling and current 9,504-byte
    corpus measurement. Separately report canonical corpus, selected discovery,
    selected body, and initial prompt footprints. Token conversion remains
    provider-owned.
11. Move portable environment semantics to `envsnap` only after APG98 parity.
    Use explicit typed profiles, canonical JSON, deterministic fingerprints,
    owner-only atomic storage, no-churn behavior, staleness visibility, and
    isolated/overlay in-process resolution. V1 snapshot profiles reject secret
    material. `.flakes` retains operational authority until qualified cutover
    and permanently retains host profile/hook/activation ownership.
12. Add `hotspot` with stable JSON as machine authority and deterministic
    terminal/Markdown renderings. Ship deep semantic metrics only where a
    qualified parser exists, initially Go; classify every authorized language
    surface and represent unavailable metrics explicitly. Use confidence and a
    deterministic relative-risk vector. Defer Git churn/growth beyond v0.7.
13. Rewrite the README only in APG101 as a human landing page. Preserve
    chronological material under detailed history, roadmap, evaluation, and
    status owners.
14. Retain `CSS-QD-001..005`, `JS-QD-001..005`, 39/39/39 skill topology, and
    14 stable / 25 provisional maturity unless a separately authorized phase
    materially owns a change.
15. Freeze APG94 through APG103 in the sequence recorded by
    [the v0.7 roadmap](../../../v0-7-roadmap.md), with APG102 as a separate
    cross-consumer readiness phase and APG103 as publication/readback.

APG96 clarification: the primary-supersession compatibility in decision 4 is
the behavior accepted from APG95. An ops-only file is the temporary current
primary only while no Git primary exists. A later Git show/diff primary removes
that stale ops file and does not copy its record forward. Operational evidence
created after a Git primary exists still appends inside that Git primary. Any
later retention change requires an explicit compatibility, schema, and evidence
decision; the earlier architecture shorthand “absorbs” did not authorize one.

The complete normative interfaces, schemas, matrices, security rules,
information architecture, and falsification conditions are in
[the embeddable toolkit architecture](../../../architecture/v0-7-embeddable-toolkit.md)
and [the APG-JACA boundary](../../../architecture/apg-jaca-integration.md).

## Alternatives considered

- **Retain Python and let JACA spawn `apgr`.** Rejected because it fails the
  required in-process boundary and makes command/filesystem adapters the API.
- **Make Git process-free immediately.** Rejected because real Git object,
  status, index, diff, merge, rename, and binary parity already has a native
  authority. Exact-argv native Git is acceptable; a Go Git library would need a
  separate parity justification.
- **Use a nested `/go` module.** Rejected because it complicates public import
  paths and normally requires subdirectory-prefixed tags for one coordinated
  release.
- **Use `pkg/report` or leave layout open.** Rejected by the package freeze:
  root domain packages communicate ownership and give APG95 binding imports.
- **Keep two long-lived report implementations.** Rejected because parity drift
  would make schema authority ambiguous. Python delegates after the Go slice is
  qualified.
- **Require an independently installed Go binary for Python.** Rejected because
  `pip install` would not be standalone. First-run download is rejected as an
  unpinned/offline executable boundary; FFI is rejected as unnecessary cgo/C-ABI
  complexity.
- **Publish unscoped `apgr` on npm.** Rejected because availability is external
  mutable state and the scoped name binds project ownership. Node remains only
  a launcher.
- **Expose all skills and return bundle advice.** Rejected because it conserves
  no agent discovery context. The isolated materialized root is part of the
  contract.
- **Let the resolver interpret prompts.** Rejected because a model-free toolkit
  must not invent workflow authority from prose.
- **Leave environment behavior permanently in `.flakes`.** Rejected because
  in-process curated resolution is portable and useful to non-Nix consumers.
  Immediate replacement is also rejected; current `.flakes` remains authority
  until APG98 parity and a separate cutover.
- **Claim equal hotspot depth for every language.** Rejected as false evidence.
  Classification, bounded structural metrics, explicit unavailability, and a
  parser extension boundary are truthful and independently reviewable.
- **Include growth/churn in v0.7.** Rejected to resolve the supplied design
  tension explicitly: history analysis is a future enhancement, while v0.7
  freezes non-historical structural hotspots.
- **Rewrite the README during APG94.** Rejected because user-facing structure
  should describe implemented surfaces after APG100, while APG94 is architecture
  only.

## Consequences

APG gains a public Go compatibility commitment beginning with APG95. Public API
and schema changes require JACA consumer evidence and rollback. Multi-platform
binary distribution replaces the universal Python-wheel assumption and adds a
coordinated npm surface. The honest hotspot matrix is less deep than the full
language list but avoids synthetic metrics and permits separately reviewed
parser growth.

The architecture is larger than a report-only port but remains split into small
vertical phases. The existing Python and `.flakes` implementations remain live
authorities until their named parity/cutover gates, preventing an unqualified
flag day.

APG94 itself adds no module, code, dependency, skill, maturity, version,
distribution, README rewrite, publication, deployment, JACA change, `.flakes`
change, Nix change, or APG95 implementation.

## Acceptance and rollback

ADR 0051 is wrong if APG95 cannot provide the frozen public package paths; JACA
must spawn a CLI or shell; the report corpus cannot achieve parity without an
unversioned schema change; embedded skills require a second maintained tree;
task-scoped agents still receive global discovery; environment values can leak
or secret names enter v1 snapshots; unsupported hotspot metrics become numeric;
or supported artifacts cannot share one version/binary/corpus identity.

Before successor implementation, rollback removes the APG94 records and index
updates. After a public successor contract exists, rollback must preserve its
compatibility and cannot silently restore duplicate semantic owners.

APG95 remains separately authorized.
