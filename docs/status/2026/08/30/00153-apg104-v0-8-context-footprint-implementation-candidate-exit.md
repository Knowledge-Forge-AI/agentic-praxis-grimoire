# APG104 v0.8 Context-Footprint Implementation Candidate Exit

Phase ID: `APG104`

## Status

**Work-stage source candidate implemented and qualified — immutable artifact
and fixture evidence is packet-owned. This is not a v0.8.0 release or
publication claim.**

Terminal disposition:
`V08_IMPLEMENTATION_CANDIDATE_AWAITING_PRE_FINAL_REVIEW`.

## Scope and decisions

APG104 is the canonical semantic phase for the bounded APGR v0.8
context-footprint and skill-inventory program. `APGR-CAP0` and `APGR-CXT0` are
program-entry labels within this phase, not additional phase IDs.

CAP0 retains the historical 9,527-byte canonical-description integrity
control, separates description, semantic body, support, and materialized-bundle
accounting, and selects zero new skill candidates. RepoMap and Theme Forge
queues remain deferred. The optional CXT2B external importer is deferred
because its required format, provenance, licensing, fixture, fail-closed
mapping, and consumer-value gates are not satisfied.

CXT0 freezes the additive `footprint` boundary and strict versioned records:
`apg.context-footprint/v1`, `apg.context-comparison/v1`,
`apg.context-projection/v1`, `apg.context-component-registry/v1`, and
`apg.capacity-control-mapping/v1`. Canonical bytes and domain-separated
fingerprints are deterministic; unknown versions, fields, units, mappings, or
evidence fail closed; missing and unavailable values are explicit and never
zero; and bounded projections retain source identity and refuse
consequence-bearing omissions or sensitivity/retention downgrades.

The architecture remains additive to the public v0.7.0 package boundary. APGR
does not own providers, credentials, orchestration, workflow progression,
security enforcement, or JACA control-protocol types. Nix remains a read-only
consumer handoff and is not an activation or release prerequisite.

## Evidence state

The APG104 architecture evaluation records the CAP0/CXT0 decisions and their
compatibility, provenance, and boundary dispositions. Go vet and 364 Go tests,
including the race run, pass. The configured test runner passes 3,374 unit
tests and 605 integration tests with two declared environmental skips. Exact
deterministic artifacts, the immutable candidate-proxy consumer run, manifests,
and checksums are retained in the publication-excluded pre-final packet; the
dispatcher-owned pre-final review remains required before a release claim.

No v0.8.0 public branch, tag, GitHub release, Go-module publication, PyPI
publication, npm publication, deployment, or active consumer cutover has
occurred.

## Not run at this exit

The following are intentionally pending parent-owned completion and are not
represented as passing evidence here:

- the immutable independent consumer fixture against the final public module;
- dispatcher pre-final review and any dispatcher-owned Git finalization; and
- external v0.8.0 publication and fresh GitHub, Go, PyPI, and npm readback.

## Next action

Complete the bounded implementation and focused/release qualification, retain
the exact candidate packet and evidence, and submit that resulting candidate
to the dispatcher-owned pre-final review. Only an accepted pre-final result
may proceed to closeout publication. APG104 grants no automatic successor
authority.
