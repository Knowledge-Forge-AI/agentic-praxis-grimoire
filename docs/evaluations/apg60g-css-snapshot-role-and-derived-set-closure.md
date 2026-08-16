# APG60G CSS Snapshot, Role, and Derived-Set Closure

APG60G is a bounded forward correction after accepted APG60F. APG60F remains
accepted and its import provenance, isolated worker, 52-role graph, and
projection revalidation remain in force.

## Corrections

The APG60F post-review false passes were reproduced before correction:

- a worker could collect source from one repository and evaluate a replacement
  directory at the same pathname;
- topology and installer checks could accept a duplicate name while omitting a
  different canonical name;
- a required role could be redirected coherently in the declaration, manifest,
  and plan;
- an authoritative read could return an opened file after its directory entry
  had been replaced.

Dynamic consumers now inherit a pinned repository-root descriptor, enter it
with `fchdir`, and derive a bounded read-only snapshot of `skills` and
`.agents` through descriptor-relative, no-follow reads. The worker and parent
revalidate the pinned physical root before launch, during worker evaluation,
and after the worker returns; parent and worker descriptors close on ordinary
and exceptional paths. Runtime reads are confined to that verified snapshot,
not an unpinned pathname, and the bounded observation is not a claim of
post-return filesystem atomicity.

Topology, library, and installer observations now carry deterministic sorted
skill names. The expected set is independently derived from direct canonical
owners, and each consumer must match the complete exact set. Safe lowercase
dash-separated components, duplicate rejection, and ordering are part of the
contract; candidate presence remains explanatory only.

The 52 required lifecycle roles now reproduce a code-owned semantic registry
independent of the co-mutable manifest and removal plan. Frozen class, locator,
verification family, cardinality, lifecycle, and cross-reference semantics
reject coordinated redirection while allowing unrelated additive roles.

Every authoritative direct-regular read now observes final entry, opened
descriptor, complete bytes, descriptor stability, and final entry again. Same-
size replacement, symlink replacement, unlink/recreate, short reads, growth,
shrinkage, and metadata drift fail closed.

## Versioned foundation

The current manifest and removal plan are schema version 6. The current
phase-history artifact is APG60G schema version 2 and contains APG58 through
APG60G as foundation, APG61 as authored Proposed but unintegrated, and APG61
plus APG62 as retained or rejected terminal history. APG60F history remains an
immutable schema version 1 artifact.

APG60G consumes exit `00087`. The future APG61 and APG62 exits are `00088` and
`00089`. The superseding Claude handoff is recorded with the APG60G private
bundle and remains a recommendation, not authorization.

## Preserved state and verification

The sixty-case CSS behavior contract and all expected objects remain unchanged.
CSS remains absent; ADR 0035 remains Rejected and ADR 0036 remains unused.
Development remains 28/28/28 with fourteen stable and fourteen provisional
entries. Corrected public and active v0.4.0 remain unchanged. No target,
candidate, route, projection, catalog, maturity, release, or successor state
was created.

The failing-first J1–J4 controls were red on the APG60F tree and pass after
correction. Focused controls cover root replacement and descriptor cleanup,
exact derived sets, the coordinated semantic-role matrix, coherent reads, and
all five lifecycle states. Full unit, integration, combined, configured Bats,
coverage, JSON, links, record identity, privacy, rights, change-size, and
independent-review gates are required for the terminal report.

APG60G authors no skill, creates no ADR, publishes nothing, deploys nothing,
and grants no APG61 or successor authority.

## Subsequent correction

APG60H later preserved this accepted foundation while completing snapshot,
cleanup, full-path absence, final root-binding, and projection verification.
This note does not rewrite APG60G's result.
