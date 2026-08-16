# APG60E CSS Repository Path and Candidate-Surface Closure

APG60E is a bounded forward correction after accepted APG60D. It preserves the
sixty-case CSS behavior contract byte-for-byte, authors no candidate, creates
no ADR, and changes no catalog, projection, route, maturity, release, public,
active, or target surface.

## Finding and correction

Independent review reproduced three related false-pass families. Lifecycle
authority files could be read through symlinked ancestors; authored candidate
owners could be supplied from outside the repository; and retained
integration owners could be externalized behind parent-directory symlinks.

One standard-library repository-path contract now resolves the physical
repository root once, validates repository-relative POSIX paths, traverses
ancestors descriptor-relatively without following symlinks, and performs
bounded complete reads from the already-open direct regular file. Metadata
drift, short or premature reads, growth, shrinkage, replacement, wrong type,
and unsafe ancestry fail closed.

The expected projection entry remains one exact relative symlink. Its
ancestors must be direct repository directories, its link text must match the
declared target exactly, and the canonical target must be a direct regular file
beneath direct repository ancestors.

## Lifecycle closure

The common path boundary now protects the candidate-surface manifest, removal
plan, CSS behavior fixture, phase-history manifest, traceability input,
decision index and ADR, narrative owners, candidate leaf and specifications,
project and release owners, test inventory, focused tests and fixtures,
dynamic consumers, and every retained current owner.

The current phase-history manifest is versioned forward through APG60E.
APG58 through APG60E are the foundation; authored state requires APG61, and
retained or rejected state requires APG61 plus APG62. APG60E owns exit
`00085`; future APG61 and APG62 exits are `00086` and `00087`.

## Preserved boundary

APG60D remains accepted. The frozen contract remains cases
`APG60-CSS-001` through `APG60-CSS-060` with unchanged expected objects and
unchanged `300/600/900` thresholds. CSS remains absent rejected-evidence
pre-authoring policy. ADR 0031, ADR 0034, and ADR 0035 remain Rejected; ADR
0036 remains unused. Development remains 28/28/28 with fourteen stable and
fourteen provisional skills. Corrected public and active v0.4.0 remain
unchanged.

Focused repository-path, authority-input, authored, retained, projection,
schema, history, and lifecycle tests pass. Terminal full-regression and
delivery evidence is recorded in the associated managed APG60E report.

The updated publication-excluded handoff recommends a separately authorized
APG61 fresh-authoring phase. This evaluation grants no APG61 or successor
authority.

## Subsequent correction

APG60E remains accepted. APG60F later closes dynamic-import provenance,
required-role self-deletion, and projection/target observation gaps without
rewriting this phase's acceptance. APG60F owns exit `00086` and advances future
APG61 and APG62 exits to `00087` and `00088`.
