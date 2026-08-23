# APG and JACA Integration Boundary

## Purpose

This document freezes the v0.7 direct-library contract between Agentic Praxis
Grimoire (APG) and Joint Agentic Command Aegis (JACA). The complete APG product
architecture remains in
[the v0.7 embeddable toolkit contract](v0-7-embeddable-toolkit.md).

The boundary is asymmetric:

```text
JACA orchestration
    |
    | imports public Go packages; passes context and structured requests
    v
APG report | skills | envsnap | hotspot
    |
    | returns deterministic in-memory models, bytes, identities, errors
    v
JACA evidence persistence and lifecycle
```

APG never imports JACA. JACA decides when to call APG and how to persist or act
on the returned evidence.

## Source-derived consumer fit

The inspected JACA source has separate Go modules for controller, orchestrator,
manager, and runner responsibilities, all declaring Go 1.25. Its orchestrator
owns phase sequencing and invocation, while controller and runner surfaces use
strict JSON evidence, SHA-256-bound artifacts, exact Git argument vectors,
`context.Context`, and bounded errors.

The first APG dependency therefore belongs in the JACA orchestrator module
behind a JACA-owned internal adapter. That adapter may translate APG results
into JACA protocol/evidence types. APG packages must not accept JACA request,
manifest, result, artifact, or roadmap types. A later JACA controller or runner
may import the same APG public packages if its own ownership requires it; that
does not move orchestration into APG.

The exact source revisions and inspected paths are recorded in APG94's
publication-excluded evidence. They are evidence, not a public compatibility
dependency.

## Required call contract

Every JACA call:

1. passes the active operation's `context.Context`;
2. passes an exact repository root or immutable bytes rather than ambient
   current-directory authority;
3. uses APG public request structs containing no JACA implementation type;
4. receives a deterministic value result plus stable schema/fingerprint
   identities;
5. handles cancellation through `errors.Is`;
6. classifies other stable failure families through APG sentinel errors;
7. persists APG evidence only under JACA's own evidence and authorization rules;
8. never treats an APG recommendation as authority to advance work.

APG does not retain a JACA callback, start a lifecycle goroutine, write JACA
state, or call a provider.

## Capability promises

| JACA need | APG v0.7 promise | JACA remains responsible for |
| --- | --- | --- |
| Commit report | `report.Service.Show` returns normalized evidence and canonical report bytes | Selecting the phase/commit, persistence, review, disposition |
| Worktree report | `report.Service.Diff` returns a drift-checked snapshot without real-index mutation | Deciding whether uncommitted evidence is authorized and how it is retained |
| Operational record | `report.Operational` validates caller bytes and exact record relations in memory | Authoring the operational body and its truth claims |
| Report publication | Optional `report.Append` preserves APG outbox transaction semantics | Selecting the outbox and authorizing the write |
| Skill bundle | `skills.Resolve` returns a deterministic selected set, reasons, budget result, and fingerprint | Supplying structured task facts and deciding when guidance applies |
| Skill content | `skills` returns exact embedded bodies and materializes an isolated discovery view | Pointing an agent only at that view and cleaning task state |
| Environment | `envsnap.Load`/`Resolve` returns a validated environment map and provenance | Selecting the profile, providing secret channels, spawning the provider |
| Hotspots | `hotspot.Analyze` returns stable JSON-domain results and deterministic renderings | Choosing repositories, limits, acceptance policy, and any refactoring action |

## Shell-free and process-free boundaries

JACA integration is shell-free: it imports APG and does not invoke `apgr`,
`bash`, `zsh`, or another shell. Initial report collection is not process-free:
APG may execute native `git` with `exec.CommandContext`, fixed environment
controls, bounded pipes, and exact argv.

This distinction preserves real Git object, merge, status, index, rename,
binary, and patch behavior without forcing JACA through a CLI. A future
process-free Git implementation requires a separate decision and parity proof.
APG94 does not select one.

## Evidence mapping

JACA may persist this compact APG identity alongside its own artifacts:

```json
{
  "producer": "apg",
  "producer_version": "0.7.0",
  "schema": "apg.<domain>/v1",
  "record_id": "<domain identity>",
  "fingerprint": "<sha256>",
  "content_sha256": "<sha256>"
}
```

The mapping is not a replacement for JACA's manifest. JACA binds exact bytes
with its own artifact path, size, and SHA-256 rules. APG IDs remain domain
identities; JACA request, attempt, result, and review IDs remain orchestration
identities.

No APG error includes source payloads, environment values, patch contents,
provider credentials, or private absolute paths. JACA may add bounded context
after applying its own protected-data policy.

## Cancellation and failure

Cancellation stops collection, analysis, or materialization at the next safe
boundary. APG cleans invocation-owned temporary state before returning unless
the relevant publication API has emitted a recoverable transaction marker. It
does not convert cancellation into success or a partial valid report.

The stable failure families are:

- invalid request or schema;
- unsupported platform or capability;
- repository or Git precondition;
- concurrent drift;
- unsafe path, owner, permission, or file type;
- budget exceeded;
- unavailable analyzer metric;
- compatibility/parity mismatch;
- publication conflict or recoverable transaction; and
- context cancellation/deadline.

Partial diagnostic data may be returned only in a type that cannot be confused
with a successful domain result. Unavailable hotspot metrics are ordinary
declared capability results, not synthetic failures and not numeric zeroes.

## Dependency and cycle rule

The allowed module edge is:

```text
JACA xo (and, only when separately justified, ctrl or rnr)
    -> github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/<public-package>
```

Forbidden edges include APG to any JACA module, JACA to an APG `internal/`
package, and an APG public package to a JACA protocol package. JACA adapters are
consumer code and live in JACA.

APG95 acceptance must include a small external-module compile test importing
`report` without importing `cmd/apgr`, Python, or an APG internal package.
APG102 must exercise the real JACA adapter under its current module graph and
prove the absence of a cycle.

## Explicit exclusions

APG does not persist attempts, choose a provider/model/reviewer, retry failed
work, sequence phases, enforce dispatcher review cadence, authorize report
writes, mutate JACA state, or interpret a task prompt. JACA does not redefine
APG record schemas, bundle fingerprints, snapshot validation, or hotspot
metrics.

APG94 modifies neither repository and grants no JACA integration or APG95
implementation authority.
