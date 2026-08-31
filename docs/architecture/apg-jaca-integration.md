# APG and JACA Integration Boundary

## Purpose

This document freezes the v0.7 direct-library contract between Agentic Praxis
Grimoire (APG) and Joint Agentic Command Aegis (JACA) and owns the versioned
consumer handoff for additive v0.8 work. The complete v0.7 APG product
architecture remains in
[the v0.7 embeddable toolkit contract](v0-7-embeddable-toolkit.md). The additive
program boundary is in the
[v0.8 context-footprint and skill-inventory contract](v0-8-context-footprint-and-skill-inventory.md).

The boundary is asymmetric:

```text
JACA orchestration
    |
    | imports public Go packages; passes context and structured requests
    v
APG report | skills | envsnap | hotspot | footprint
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
| Context footprint | `footprint.Measure`, `Compare`, and `Project` return deterministic records, comparisons, and source-bound projections | Supplying task facts, provider-side total-context accounting, custody, enforcement, and adoption |

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

## Versioned JACA consumer handoff — revision 1

This section is the canonical APGR-published handoff for JACA. It defines what
JACA may consume and what evidence must cross the boundary. It does not create
a JACA dependency or claim a production landing.

### Package and released-version gate

The module path is
`github.com/Knowledge-Forge-AI/agentic-praxis-grimoire`. The direct public
boundary is `schema`, `report`, `skills`, `envsnap`, `hotspot`, and the additive
`footprint` package. JACA imports only those public packages behind one
JACA-owned internal adapter;
it does not import `cmd/apgr`, an APG `internal/` package, Python, or npm.

Production use requires an exact published semantic version and matching module
sums. A mutable branch, private source copy, development `replace`, or local
checkout is not a released dependency. The latest published release is
v0.7.0, which supplies the five-package direct-import boundary. The v0.8.0
`footprint` package and projection schemas are present in the work-stage
candidate but are not yet a published JACA dependency. JACA must not create a
permanent private lookalike and later call it the APGR schema.

The corresponding JACA program entries remain JACA-owned. `JACA-APG0` and
`CTX-DOCS` are documentation-only prerequisites and receive no implementation
authority from this APGR contract. JACA's own route measurement and reduction
must precede provider exposure, projection treatments, diagnostics, or
optimizer canaries. There is no standalone `JACA-APG4`; JACA terminally
dispositions the report and hotspot questions in APG0 or in a later separately
authorized package-specific start.

### Package dispositions

| Surface | APGR output | JACA adoption rule |
| --- | --- | --- |
| `schema` | Shared APGR schema and envelope identities | Supporting APGR model only; never a JACA control protocol |
| `skills` | Deterministic selection, exact corpus/rule/bundle identities, budget results, and isolated materialization | First package qualification target, not a production provider-exposure lane; JACA owns task facts, exposure, cleanup, and attempt relation |
| `envsnap` | Validated profiles, canonical snapshots, explicit-map capture, loading, and isolated or overlay resolution | Deferred pending JACA/Agent-Central environment ownership, secret-injection, redaction, and taint disposition |
| `hotspot` | Structured bounded analysis, rankings, confidence, and unavailable reasons | Advisory evidence only; cannot create work, expand scope, or override verification |
| `report.Show` / `report.Diff` | Canonical in-memory Git evidence | JACA compares and terminally adopts narrowly, defers, or rejects under its source-evidence authority |
| `report.Operational` | In-memory validation of caller-authored operational bytes and record relations | Not prioritized until JACA identifies a unique gap |
| `report.Append` | Optional APGR outbox publication | Rejected for JACA adoption while JACA retains one artifact authority |
| `footprint` / projection | Canonical APGR-domain measurement and bounded derived evidence under `apg.context-footprint/v1`, `apg.context-comparison/v1`, and `apg.context-projection/v1` | Consume only from a released, qualified version; JACA retains separate total-context, custody, and enforcement authority |

### Semantics and errors

The adapter passes the active `context.Context`, immutable bytes or an exact
repository/storage root, and public APG request values. It receives
deterministic domain models, canonical bytes, schema identities, record IDs,
and fingerprints. JACA copies or translates those results into JACA-owned
evidence without changing their APGR meaning.

JACA classifies public APG sentinel families through `errors.Is` and preserves
`context.Canceled` and `context.DeadlineExceeded`. A cancellation, unsupported
capability, invalid input, unsafe path, drift, budget refusal, unavailable
metric, compatibility mismatch, or publication conflict is not coerced into a
successful result. Partial diagnostic data is usable only through a type that
cannot be confused with success. The adapter maps an APG error into a JACA
failure or evidence type; APGR does not define JACA retry, route, or transition
semantics.

### Provenance and custody

For every retained APG result, JACA records the applicable identities from this
set:

- exact APGR semantic version and module sums;
- public package and API/schema version;
- APGR build, corpus, rule, composition, capacity-policy, component-registry,
  projection, serializer, and digest identities when present;
- request, bundle, materialization, record, projection, and source-artifact
  fingerprints when present;
- consumer-adapter and qualification-fixture identities; and
- JACA's own authoritative digest and length for the stored bytes.

An APGR artifact may exist before or outside an attempt. JACA owns zero or more
relations from that artifact to a phase, work item, attempt, stage, role,
predecessor, replacement, or disposition. Attempt-bound bundles and
projections receive an attempt relation; reusable qualification fixtures and
source comparisons need not. APGR producer identity never replaces JACA
custody, sensitivity, retention, or authorization evidence.

### Qualification, upgrade, and rollback

Before adopting a new released APGR version, the JACA-owned adapter must:

1. pin the version and module sums;
2. exercise selected packages with valid, boundary, malformed, cancellation,
   and stable-error cases applicable to that package;
3. compare canonical bytes, schemas, corpus/rule identities, change class,
   and fingerprints against the previously qualified version;
4. record package-specific adoption, deferral, or rejection;
5. reject unknown or incompatible identities rather than guess; and
6. keep one attempt on one resolved APGR and corpus/rule identity set.

A selection-affecting corpus or rule change requires explicit JACA
requalification. A running or completed attempt is never silently re-resolved
under a newer identity.

Rollback changes the version used for new attempts or disables a newly adopted
surface. JACA preserves the prior adapter, module and schema identities, stored
bytes, relations, and decoder support required to interpret existing attempts.
Rollback does not rewrite historical evidence or resume one attempt under a
different APGR identity.

### Forbidden inversion and JACA-owned controls

Official provider CLI execution, terminal executable provenance,
authentication-failure classification, fresh provider fallback, login policy,
notification subscription, role and network policy, prompt-injection handoff
controls, retries, routes, attempts, and workflow progression are JACA and
security concerns. They are not APGR packages or features.

In particular, APGR neither invokes a hosted model nor decides whether a
provider process qualifies. JACA must enforce any official-CLI boundary and no-
login-automation rule outside this adapter. An APGR result cannot cause a
provider fallback, notification, retry, route change, or phase transition.

## Shared interface-control register — revision 1

APGR publishes the following rows. JACA acknowledgment is required before a
shared row governs production integration. An unresolved row blocks only the
affected cross-team work, not independent APGR architecture or qualification.

| ID | Boundary | APGR responsibility | JACA responsibility | Change trigger |
| --- | --- | --- | --- | --- |
| `ICR-001` | Handoff ownership | Publish APGR-domain records; define no JACA runtime handoff | Own adapter, artifact custody, relations, attempts, findings, and dispositions | Either side proposes a shared control schema or duplicate authority appears |
| `ICR-002` | Corpus and selection identity | Publish corpus/rule identities, change class, affected facts, and fixture requirement | Store identities and gate adoption and replay | Any selection-affecting corpus, rule, or ambient-discovery change |
| `ICR-003` | Qualification first mover | Use a substantive immutable independent consumer fixture for new public package work | Add real-consumer qualification when scheduled | Public API change or new JACA exposure mechanism |
| `ICR-004` | Released version | Publish and qualify exact public schemas before claiming support | Depend only on a released qualified version; keep prototypes disposable | Version, schema, serializer, fidelity, sensitivity, or module-sum change |
| `ICR-005` | Optional importer | Declare internal, experimental, or supported status for each pinned format | Do not production-depend on internal API or create a competing permanent schema | Upstream format/method change or production-consumer request |
| `ICR-006` | Capacity and component mapping | Publish component registry, policy identity, and versioned mapping | Keep APGR bundle policy separate from JACA total-context policy | Component-kind or capacity-control change |

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

APG95 included a small external-module compile test importing `report` without
importing `cmd/apgr`, Python, or an APG internal package. APG102 exercised a
disposable JACA-owned adapter under the current JACA module graph and found no
cycle. That readiness evidence did not modify JACA or create a production
dependency.

## Explicit exclusions

APG does not persist attempts, choose a provider/model/reviewer, retry failed
work, sequence phases, enforce dispatcher review cadence, authorize report
writes, mutate JACA state, or interpret a task prompt. JACA does not redefine
APG record schemas, bundle fingerprints, snapshot validation, or hotspot
metrics.

APG94 modifies neither repository and grants no JACA integration or APG95
implementation authority.

This revision records documentation and handoff doctrine only. It changes no
APGR or JACA runtime, dependency, schema, provider route, release, or host state.
