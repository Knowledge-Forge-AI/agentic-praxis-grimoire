# APG94 v0.7 Embeddable Toolkit Architecture

## Candidate result

APG94 accepts ADR 0051 and freezes APG v0.7 as a library-first embeddable Go
toolkit. The normative artifacts are:

- [the product architecture](../architecture/v0-7-embeddable-toolkit.md);
- [the APG-JACA boundary](../architecture/apg-jaca-integration.md); and
- [the dependency-ordered roadmap](../v0-7-roadmap.md).

No v0.7 implementation begins in this phase.

## Source-first findings

Current APG Python source has one canonical CLI with six families and maintained
report owners for Git show, Git diff, and operational append. The report
implementation binds exact envelope/record versions, field and section order,
Git semantics, hashes, strict parsing, safe paths, owner-only outbox state,
show/diff primary supersession, locks, transaction recovery, and stable CLI
error classes. Those behaviors become the APG95 differential oracle rather
than being redesigned for port convenience.

Current JACA committed Go source separates controller, orchestrator, manager,
and runner modules, uses Go 1.25, propagates `context.Context`, invokes native
Git with exact argv, and binds strict JSON evidence artifacts by size and
SHA-256. Its orchestrator is the natural first APG consumer because it decides
when primitives run. A JACA-owned internal adapter can translate APG public
values into JACA protocols without a module cycle or APG knowledge of JACA.

Current `.flakes` source uses exact typed allowlists, captures only named
variables, validates bounded values, skips optional missing values, writes
owner-only snapshots atomically without rewriting unchanged content, emits
SHA-256 metadata, parses imports without shell evaluation, and wires capture
through thin zsh/Bash prompt hooks. It remains operational authority until an
APG98 parity gate and separately authorized consumer cutover.

Exact source identities and live working-state qualifications are retained in
publication-excluded evidence. The public contract depends on semantic owners,
not a volatile external revision.

## Frozen architecture

One root Go module uses path
`github.com/Knowledge-Forge-AI/agentic-praxis-grimoire`, Go 1.25, a shared
`v0.7.0` tag, root domain packages `schema`, `report`, `skills`, `envsnap`, and
`hotspot`, `cmd/apgr`, and private `internal/` implementations. This resolves
the plan-review package-layout finding. Initial Git remains a native exact-argv
child process; JACA integration is shell-free but not process-free.

The first reporting API returns normalized records and canonical bytes in
memory and makes outbox publication optional. Envelope v1, show v2, diff v1,
operational v1, IDs, fields, ordering, hashing, path safety, locking, atomicity,
primary semantics, output channels, and error classes remain frozen. APG95 must
falsify parity with a broad differential golden corpus.

The CLI migration matrix classifies every family/action. Migrated portable
behavior has one Go owner. Repository and host maintenance may remain Python
during v0.7 but cannot reimplement migrated semantics.

Python uses supported-target wheels containing the Go binary, retains its
existing console/module entry points, and requires Go 1.25 for sdist builds.
The selected npm launcher is `@knowledge-forge-ai/apgr`, resolving the second
plan-review finding; three same-version optional platform packages carry the
binary. No wrapper downloads a runtime executable or uses FFI.

## Context, environment, and hotspot contracts

The model-free skill resolver accepts only versioned structured facts and
explicit IDs, emits deterministic reasons/conflicts/composition, enforces byte
budgets without truncation, and fingerprints exact content. Canonical Markdown
is embedded directly from `skills/`. Agent-scoped materialization is mandatory:
an agent that also sees the global root fails context-conservation
qualification.

The global 9,527-byte ceiling is not raised. APG94 preserves the 39-skill
9,504-byte / 9,492-character corpus and separates total corpus, selected
descriptions, selected bodies, and initial prompt bytes.

Environment snapshot v1 uses explicit typed profiles, canonical JSON,
deterministic fingerprints, no-churn owner-only storage, staleness visibility,
and isolated/overlay in-process resolution. Credential, token, password,
private-key, cookie, session, and secret values are outside the v1 snapshot
channel. Diagnostics never contain values.

Hotspot JSON is machine authority. The matrix classifies every requested
surface, adds Go for the direct APG/JACA consumers, and gives deep semantic
metrics only to qualified parsers. Missing metrics are unavailable rather than
zero or approximate. Relative risk includes raw coverage/confidence. Git
growth/churn is explicitly deferred beyond v0.7, resolving the supplied design
tension.

## Documentation and roadmap

The future README is a human landing page rather than a phase ledger. APG101
preserves historical material under detailed architecture, reference, guide,
distribution, release, governance, roadmap, status, and history owners.

The frozen sequence is APG94 architecture; APG95 reporting; APG96 Go CLI;
APG97 skill/context bundles; APG98 environment snapshots; APG99 hotspots;
APG100 remaining migration and Python/npm packaging; APG101 documentation;
APG102 cross-consumer readiness; and APG103 publication/readback. Readiness and
publication remain separate.

## Preserved state and limitations

APG94 adds no `go.mod`, Go code, dependency, skill, catalog row, projection,
maturity change, analyzer, environment implementation, package artifact,
version bump, README rewrite, release, deployment, JACA change, `.flakes`
change, Nix change, staging, commit, or push.

The architecture is stated but not implemented. Python remains report/CLI
authority; `.flakes` remains environment authority; no JACA adapter exists;
platform packages do not exist; parser depth beyond the frozen initial matrix
is unqualified. Each is assigned to a separately authorized phase.

`CSS-QD-001..005` and `JS-QD-001..005` remain unchanged. Current skill topology
is 39 canonical, 39 catalog, and 39 projections with 14 stable / 25 provisional,
zero malformed, and version 0.6.0.

## Disposition

The APG94 candidate freezes every authorized theme with an owner, interface or
schema boundary, migration/distribution rule, security or budget contract, and
independently reviewable successor.

Terminal disposition: `V07_ARCHITECTURE_FROZEN_READY_FOR_APG95`.

APG95 is recommended but separately authorized.
