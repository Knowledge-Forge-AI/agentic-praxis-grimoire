# Go Library Reference

This documentation covers v0.10.0.

APG's embeddable module is
`github.com/Knowledge-Forge-AI/agentic-praxis-grimoire` at Go 1.25. Public
consumers import root packages directly; they do not import `cmd/apgr` or any
`internal/` package.

## Package map

| Package | Purpose | Detailed owner |
| --- | --- | --- |
| `schema` | Shared schema and envelope version constants | This reference |
| `report` | Commit, worktree, and operational evidence plus optional publication | [Reporting](#reporting) |
| `skills` | Embedded corpus, deterministic bundle resolution, and isolated materialization | [Skill context bundles](../guides/skill-context-bundles.md) |
| `envsnap` | Strict profiles, canonical snapshots, storage, loading, and resolution | [Environment snapshots](../guides/environment-snapshots.md) |
| `hotspot` | Bounded structural analysis, stable results, and renderers | [Hotspot analysis](../guides/hotspot-analysis.md) |
| `footprint` | Deterministic context-footprint records, comparisons, measurements, projections, and component/control registries | [Context footprints](#context-footprints) |
| `phase` | Immutable work-only Request V2 envelope, attempt identifiers, execution status, semantic role constants, and routing adapters (Experimental / Provisional) | [Single-Phase Envelopes](#single-phase-envelopes) |
| `routing` | Policy-neutral deterministic routing ladder and canonical observation digest calculation (Experimental / Provisional) | [Routing Primitives](#routing-primitives) |
| `evidence` | Path-traversal-safe review finding structures, finding dispositions, and validation receipts (Experimental / Provisional) | [Evidence Primitives](#evidence-primitives) |
| `candidate` | Immutable candidate identity and artifact manifest structures with path traversal rejection (Experimental / Provisional) | [Candidate Primitives](#candidate-primitives) |
| `provider` | Static provider capability matrix and validation (22 rows across Codex, Claude, Antigravity) (Experimental / Provisional) | [Provider Capability Matrix](#provider-capability-matrix) |

APG exposes no orchestration package. A consumer supplies context, structured
requests, repository or storage authority, and its own lifecycle decisions.
The [APG–JACA boundary](../architecture/apg-jaca-integration.md) is the
controlling integration contract.


## Context footprints

The additive `footprint` package is a provider-neutral data and validation
owner. It measures explicit local inputs, compares compatible observations, and
creates source-bound projections. It does not execute a provider or tokenizer,
select a route, handle credentials, or own workflow or JACA authority.
Accounting is governed by three strict principles:
1. **Source-bound observations, not capacity forecasts**: Footprints record explicit
   measurements and source-bound projections, not predictive capacity models or
   exhaustion guarantees.
2. **Unavailable is not zero (`unavailable != 0`)**: Missing or unavailable metrics
   remain explicit with stated reasons and nil values; they are not coerced to zero.
   An available zero is a measured observation; an unavailable metric is an unmeasured boundary.
3. **Component separation (overlap is not additive)**: Selected descriptions, selected
   bodies, support material, repository references, and provider prompt overhead are
   measured as distinct components. Because prompt templates and harnesses overlap in
   structure, component metrics cannot be summed across boundaries without accounting.

The public schema identities are:

| Identity | Purpose |
| --- | --- |
| `apg.context-footprint/v1` | Canonical footprint records |
| `apg.context-comparison/v1` | Treatment-minus-control comparisons |
| `apg.context-projection/v1` | Bounded source-bound projections |
| `apg.context-component-registry/v1` | Closed measurable-component registry |
| `apg.capacity-control-mapping/v1` | Versioned component-to-control mapping |

The primary operations accept `context.Context` and return a value or error:

```go
record, err := footprint.Measure(ctx, footprint.MeasureRequest{...})
comparison, err := footprint.Compare(ctx, footprint.CompareRequest{...})
projection, err := footprint.Project(ctx, footprint.ProjectRequest{...})
```

`Record` (also named `Footprint`) contains an `Observation`, named
`Component` measurements, source references, and sensitivity/retention labels.
`Metric` carries an explicit unit and an `available` or `unavailable` state;
an unavailable metric has a reason and no value, while an available zero is a
valid measurement. Built-in units include bytes, UTF-8 characters, and named
provider-token units. APGR measures bytes and characters locally; callers must
supply provider-token observations explicitly, and no unit conversion is
performed implicitly.

`Compare` requires matching observation dimensions and two available metrics in
the same unit. It returns an integer treatment-minus-control `Delta`, binds the
selected component, and retains both input record fingerprints. A unit,
workload, method, harness, provider, tokenizer, repetition, study-design, or
availability mismatch fails closed.

`Project` retains the canonical source fingerprint, source schema, and source
size. It records `exact`, `lossless_structural`, or `summarized_lossy` fidelity
and sorted omitted fields. Authority, security, failure, diagnostic, finding,
refusal, uncertainty, unavailable-state, source-binding, sensitivity, and
retention content cannot be omitted; sensitivity and retention cannot be
downgraded.

`DefaultComponentRegistry` and `DefaultControlMapping` return the complete
code-owned registries. `ValidateRecord`, `ValidateComparison`,
`ValidateProjection`, `ValidateComponentRegistry`, and
`ValidateControlMapping` validate in-memory values without publication or
external I/O.

### Canonical bytes and identities

`CanonicalJSON` and the `MarshalRecord`, `MarshalComparison`,
`MarshalProjection`, `MarshalComponentRegistry`, and `MarshalControlMapping`
helpers emit compact UTF-8 JSON with deterministic field ordering, normalized
set-like fields, and exactly one trailing LF. `DecodeRecord`,
`DecodeComparison`, and `DecodeProjection` accept only canonical bytes and
reject malformed JSON, unknown versions or fields, duplicate fields, invalid
UTF-8, trailing data, noncanonical ordering, invalid mappings, and missing
required values.

`FingerprintRecord`, `FingerprintComparison`, and `FingerprintProjection`
produce domain-separated SHA-256 identities with `fp-sha256:`,
`cmp-sha256:`, and `proj-sha256:` prefixes. Registry and control-mapping
identities use the `fp-sha256:` domain with their own schema identity.

### JACA XO consumer compatibility pattern

External Go orchestrators such as Joint Agentic Command Aegis Executive Orchestrator
(JACA XO) consume `skills`, `footprint`, and supporting `schema` behind a caller-owned
internal adapter, as demonstrated and verified in `testing/fixtures/xo_consumer/`:

- **Caller DTO containment**: The caller defines its own data transfer objects
  (`CallerSkillEvidence`, `CallerFootprintEvidence`, `CallerComponentEvidence`,
  `CallerSourceReference`, `CallerComparisonDelta`, `CallerProjectionEvidence`). The
  internal adapter translates between APGR domain types and caller DTOs, ensuring
  zero APGR types leak into caller method signatures or public struct fields.
- **Pure in-memory execution**: Operations execute entirely in memory without
  spawning subprocesses (`os/exec` is strictly absent from the dependency tree).
- **Context cancellation & error sentinels**: Cancelled contexts return `ctx.Err()`
  or wrap `footprint.ErrContextCancelled`, and domain sentinels are preserved
  (`footprint.ErrUnitMismatch`, `footprint.ErrConsequenceBearingOmissionRefused`,
  `skills.ErrBudgetExceeded`).
- **Metric availability & budgets**: Unavailable metrics (such as prompt overhead
  without caller observation) remain explicit with reason preserved and nil value;
  they are never coerced to zero (`unavailable != 0`). Explicit zero budgets fail
  closed with `skills.ErrBudgetExceeded`.
- **Dual-lane verification**: Clean dual-lane conformance has been qualified across
  Lane A (published v0.8.1 baseline via public Go proxy) and Lane B (exact source
  under qualification via local replace).

> [!IMPORTANT]
> **Boundary of Authority**:
> - **APGR-local conformance != JACA registration**: Conformance is qualified on
>   Darwin arm64 under APG114, but downstream runner registration in JACA CI
>   (`tools/ci/evidence.go`) and production XO adoption (`xo/src/main/go`) are
>   consumer-owned in JACA and remain pending.
> - **XO fixture != production adapter or security proof**: The caller-owned adapter
>   fixture in `testing/fixtures/xo_consumer/` qualifies APGR Go package compatibility,
>   but is not JACA's production adapter, and passive DTOs do not enforce workflow security.

## Reporting

Consumers import `report`, construct a repository-bound `Service`, and call
`Show` or `Diff` with a `context.Context`. `Operational` validates
caller-supplied bytes and already parsed records entirely in memory.
`ParseRecords` validates canonical common-envelope records, and `Append`
optionally publishes one record under the owner-only APG outbox convention.

The v0.10.0 release adds `Verify(ctx, content)` and
`VerifyFile(ctx, path)`, returning `Verification` with a record count and
compatibility-limited flag. Both reuse the canonical parser; file verification
performs read-only bounded observation without outbox preparation. Empty input
is `ErrEmptyReport`, distinct from envelope parsing's accepted empty sequence.
Malformed/unsupported records use report error families; `ErrVerifyIO`
distinguishes file I/O failures. Historical compatibility allowances do not
mean that new malformed structured operational bodies may be generated.
They also do not authorize republication: `Append` strictly validates a newly
supplied operational record, so archived compatibility-limited bytes may verify
successfully yet be refused when appended into another outbox.

Verification checks artifact-local integrity, not external Git truth, executed
operations or absent external relationships. Refer to the
[reporting architecture](../agent-reporting-architecture.md#read-only-persisted-verification)
for precise proof limits and raw-versus-rendered hash handling.
Current-version verification requires canonical renderer equality. Changes to
renderer bytes require versioned verification preserving accepted historical
formats. Delimiter scanning and incremental hashing now check cancellation
within 64 KiB work windows and at candidates. This extraction bound does not
promise verifier-wide latency across canonical rendering and library calls.
CLI malformed-input and I/O failures both exit 1 with different
diagnostics, while library callers can distinguish their error families.

Results contain the parsed record, exact canonical bytes, and fresh
caller-owned evidence copies. The package does not require `cmd/apgr`, Python,
or a shell at the consumer boundary. Report collection may execute the
caller-selected native Git binary through `exec.CommandContext`, fixed exact
arguments, bounded streams, deterministic locale/pager/lock controls, and the
remaining inherited environment.

Public sentinel errors support `errors.Is`; context cancellation and deadlines
remain the standard context errors. Diagnostics do not contain report bodies,
patches, environment values, or caller-supplied absolute paths.

## Compatibility authority

The Python implementation under `libexec/agent_report/` was the active CLI owner
and byte-level compatibility oracle through APG95. APG96 retained it during the
migration while normal canonical and historical routes delegated to Go. The
optional differential test skips when that historical oracle is absent; a skip
does not establish parity. APG127's checked-in persisted fixtures and real-file
regressions provide maintained evidence independently of it: two fixtures were
rendered by unchanged APG126 source; six are format regressions without an
independently recorded earlier reporting-source renderer identity.

Accepted Show, Diff, and Operational fixtures compare exact canonical bytes.
Rejected fixtures compare stable failure families and mutation-safety
postconditions. Publication tests separately preserve owner-only modes,
single-primary supersession, append behavior, locks, stale-lock recovery,
transaction recovery, atomic replacement, and link refusal.

The Python oracle removes an operational-only primary when a later Git primary
is published; it does not copy that operational record into the Git primary.
The Go implementation follows those observed bytes. APG96 reconciles Accepted
ADR 0051 and the normative architecture accordingly: a later Git primary
removes the stale ops-only primary without copying its record. Operational
evidence created after a Git primary exists still appends inside that primary.

## Publication and recovery boundary

`Append` accepts an absolute clean outbox root, project, phase, and exactly one
canonical record. Directories are mode 0700 and files are mode 0600. Show and
Diff primaries supersede each other. Operational records append to an existing
Git primary or use an ops-only primary when no Git primary exists.

`AppendRequest.Policy` defaults to `AppendAlways`, preserving duplicate
envelopes. `AppendIdempotent` returns `PublishedAlreadyPresent` when every
retained record sharing project/phase/kind/ID has the same complete canonical
bytes; any differing match returns `ErrReplayConflict` without replacement.
The policy rejects unknown values before filesystem preparation. It searches
only retained records and does not change supersession or transaction recovery.
New operational records receive semantic validation before append framing;
show/diff payload validation at append retains the historical contract.

Source stability includes exact source bytes, basename, metadata and relations.
Show IDs name commits and diff IDs name state evidence, so changed labels or
native Git rendering can produce a conflict under the same ID. Callers must not
mutate request buffers during a call. This is an explicit retry policy, not
automatic deduplication or an execution/authorization ledger.

Private locking and transaction helpers retain recoverable interruption state
and never remove a live or foreign lock. Stale-lock recovery uses PID inspection,
assuming a local, single-host, owner-only outbox. If an interrupted execution
leaves a `.phase.transaction` file behind, `internal/atomicfile.Recover` provides
the underlying recovery mechanics. APG96 adds user-facing CLI path and recovery
adapters.

## Supported platforms

In accordance with Accepted ADR 0051, the embeddable Go surface targets POSIX
Unix environments (Linux and macOS) requiring direct regular files, owner modes,
and `O_NOFOLLOW` symlink refusal. Windows is not a supported target for the
embeddable Go reporting core.

## Related command and distribution surfaces

The [APGR CLI reference](cli.md) documents command adapters, footprint
operations, path and recovery operations, build information, and Python
delegation. The [distribution contract](../distribution.md) documents
supported targets, the multi-registry packaging model, and the package
architecture. The published v0.9.0 release includes the public `footprint`
package alongside the core Go packages (`schema`, `report`, `skills`, `envsnap`, `hotspot`).
This documentation covers v0.10.0 and preview additions for v0.12.0. APGR retains compatibility with v0.8.1 across all
six public Go packages (`schema`, `report`, `skills`, `envsnap`, `hotspot`, `footprint`). In v0.12, five additive
domain packages (`phase`, `routing`, `evidence`, `candidate`, `provider`) are added with Provisional / Experimental
stability (ICR-004 / ICR-005) for JACA XO consumer qualification. (Note: `phase` imports `routing` for route binding adapters;
`routing` may be consumed independently, while `phase` brings in `routing`.)
Once published, Go consumers can require `github.com/Knowledge-Forge-AI/agentic-praxis-grimoire v0.12.0`
(or `go get github.com/Knowledge-Forge-AI/agentic-praxis-grimoire@v0.12.0`) through the normal
public Go proxy and checksum database.

