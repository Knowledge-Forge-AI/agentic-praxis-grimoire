# Go Library Reference

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

APG exposes no orchestration package. A consumer supplies context, structured
requests, repository or storage authority, and its own lifecycle decisions.
The [APG–JACA boundary](../architecture/apg-jaca-integration.md) is the
controlling integration contract.

## Context footprints

The additive `footprint` package is a provider-neutral data and validation
owner. It measures explicit local inputs, compares compatible observations, and
creates source-bound projections. It does not execute a provider or tokenizer,
select a route, handle credentials, or own workflow or JACA authority.

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

## Reporting

Consumers import `report`, construct a repository-bound `Service`, and call
`Show` or `Diff` with a `context.Context`. `Operational` validates
caller-supplied bytes and already parsed records entirely in memory.
`ParseRecords` validates canonical common-envelope records, and `Append`
optionally publishes one record under the owner-only APG outbox convention.

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

The maintained Python implementation under `libexec/agent_report/` was the
active CLI owner and byte-level compatibility oracle through APG95. APG96 keeps
it as a frozen, directly invoked test oracle while normal canonical and
historical report routes delegate to the Go CLI.

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
supported targets, the multi-registry packaging model, and the prepared v0.8.1
candidate architecture. The source candidate adds the public `footprint`
package alongside the existing core Go packages; released-package availability
remains pending source freeze and publication.
