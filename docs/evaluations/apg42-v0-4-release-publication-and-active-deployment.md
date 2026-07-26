# APG42 v0.4 Release Publication and Active Deployment

## Objective and accepted input

APG42 applies the accepted public-release process to APG41's
`ready-for-publication-with-provisional-limitations` result. The release source
contains exactly 28 canonical skills, 28 catalog rows, and 28 projections:
14 stable and 14 provisional. It preserves 26 general routes,
one ChatGPT-local direct route, 27 checked route edges, and no mandatory chain.

ADR 0025 remains Rejected, ADR 0026 remains Accepted and controlling, and
ADR 0027 remains Rejected. `matryer-is-test-profile` remains absent and
`go-testing-stack` remains absent. APG42 adds no skill, changes no procedure,
and makes no maturity disposition.

The current-v0.4 release checker adds the APG42 public contract and release
records to its exact audited surface. Immutable v0.1.0 through v0.3.0 policy
owners remain unchanged.

## Release and history model

Public v0.4.0 is one deterministic squashed `Release v0.4.0` commit whose sole
parent is exact public v0.3.0, plus one annotated `v0.4.0` tag. The release
projects the complete tracked non-private source with identical path, bytes,
mode, and raw symbolic-link target. It does not publish private development
history.

Two candidates are built from the same committed source, accepted public base,
verified maintainer identity, and frozen RFC3339 timestamp. Acceptance requires
equal manifests, trees, commits, annotated tags, refs, metadata, modes, raw
symbolic-link targets, and recursive tree fingerprints. Publication then uses
one atomic dry-run and one normal atomic push of only public `main` and
`v0.4.0`. Historical public commits and tags remain unchanged.

The release source retains the canonical Agentic Praxis Grimoire NOTICE bytes
from the verified historical object `d622b081f4cf109501d03bbfebd1224a3ecbcf33`.
An unrelated project identity was not maintainer-approved and is not part of
the release. The public release and active source converge on those exact
canonical bytes; the repository identity remains `agentic-praxis-grimoire`.

## Active public-backed deployment

After live-remote and fresh-public-checkout verification, the existing active
public-backed source advances by exact fast-forward from public v0.3.0 to
public v0.4.0. The aggregate discovery integration remains aggregate-owned:
APG42 does not run `apg-user-skills`, create schema-version-1 direct-link state,
recreate the aggregate link, or alter Codex configuration.

Mechanical acceptance requires a clean active checkout at the exact public
release tree, preserved aggregate path/type/ownership/raw target, and exact
resolution of all 28 public skills. It establishes local mechanical discovery,
not automatic client invocation or precedence. If a genuinely fresh supported
client cannot be observed safely, the truthful result is
`published-and-active-mechanically-verified-pending-fresh-client-smoke`.

## Current-host verified

- release tooling and strict public v0.1.0 through v0.4.0 lineage;
- exact projection, skill-library, record-identity, and router validation;
- configured Python and Bats suites in the locked environment;
- isolated user and project lifecycle behavior; and
- active-source mechanical integration and aggregate preservation.

## Source/fixture-reviewed provisional domains

- Go language and native testing;
- google/go-cmp v0.7.0;
- Ruby and Minitest;
- Dockerfile and Vagrantfile;
- Nix testing;
- PostgreSQL and SQLite; and
- manager and Bash-to-Python conversion procedures.

These retained owners are usable only under their own triggers and limits.
Their publication does not convert source or fixture evidence into target
runtime evidence.

## Not claimed

- universal cross-platform compatibility;
- target-repository compatibility;
- automatic invocation or precedence;
- Docker, Vagrant, Nix, or database runtime success;
- external-service, container, virtual-machine, registry, or cloud behavior;
- production warranty; or
- stable maturity for provisional rows.

No maturity promotion occurs. No matryer/is owner or testing stack is included.

## Rollback and authority boundary

Before publication, a failed gate leaves public and active v0.3.0 unchanged.
After publication, v0.4.0 remains append-only; APG42 never deletes or replaces
its tag or rewrites public history. After active fast-forward, moving the active
checkout backward requires separate human rollback authority. Exact public
v0.3.0 remains the rollback source, not an automatically authorized action.

APG42 creates no GitHub Release, signature, announcement, plugin distribution,
or successor authorization. It performs no target-repository, Docker, Vagrant,
Nix, database, container, virtual-machine, registry, cloud, or external-service
operation.

## External acceptance

This release-source record is complete only with the associated postcommit
Git-show and operational evidence. External acceptance requires that evidence
to prove candidate reproducibility, the exact atomic public update, live and
fresh-checkout verification, active fast-forward and aggregate preservation,
development parity, cleanup, and every deliberately unrun boundary.
