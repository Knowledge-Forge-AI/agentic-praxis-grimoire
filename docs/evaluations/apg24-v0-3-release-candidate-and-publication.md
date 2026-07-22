# APG24 v0.3.0 Release Candidate and Publication

## Objective and accepted input

APG24 accepts APG23 as complete and applies ADR 0019 to the final v0.3.0
distribution. APG23 established nineteen release-included skills, fourteen
`stable` rows, five `provisional` rows, nineteen projections, and eighteen
non-router capability-map entries with no unresolved behavior-bearing defect.

The phase broadens the strict public policy and local lifecycle contracts,
constructs and independently reviews two deterministic candidates, publishes
one appended public commit and one annotated tag, verifies a fresh checkout,
and fast-forwards the existing active public-backed source. It changes no skill
procedure, maturity disposition, dependency, target repository, database, Nix
state, graph, deployment, or personal router.

## Distribution and lifecycle result

Public v0.3.0 contains all nineteen canonical skills and checked-in projections.
Every APG23 release-included owner is critical under the current public policy.
Exact non-private projection remains the completeness contract, so the critical
set cannot act as an omission allowlist. All public files remain independently
usable without `private/`.

ADR 0019 retains user and project state schema version 1 because the existing
representations already encode source-specific skill hashes and explicit
managed subsets. User transitions validate each release independently, compute
additions, retargets, and removals, preflight before mutation, commit state last,
and restore the exact previous set on failure. Disposable validation exercises
v0.2 six-link installation, v0.3 nineteen-link update, exact six-link rollback,
nineteen-link re-update, conservative uninstall, conflict refusal, injected
failure recovery, and unrelated-skill preservation.

New project installs default to nineteen while explicit subsets remain valid.
Existing six-skill version-1 state checks and uninstalls only its owned subset;
it does not expand implicitly. No real target project is mutated.

Focused corrected lifecycle evidence passes 14 user unit tests, 3 variable-set
user integration tests, 39 legacy user integration tests with one expected
fixture skip, and 30 project integration tests. It includes exact 6 to 19 to 6
transition and re-update, injected addition and removal restoration,
policy/projection agreement, unrelated-skill preservation, new nineteen-skill
project defaults, and existing six-skill project-state compatibility.

## Candidate and public history

Candidate A and candidate B use the same reviewed release-source tree, exact
public v0.2.0 base, version, frozen RFC3339 timestamp, and verified maintainer
identity. Acceptance requires identical manifests, trees, release commits,
annotated tag objects, refs, metadata, subject, and parent. Each candidate must
pass the complete release, lineage, lifecycle, test, syntax, documentation,
licensing, confidentiality, and projection gates.

Public v0.2.0 remains historical and unchanged. v0.3.0 appends one squashed
`Release v0.3.0` commit whose sole parent is v0.2.0 and adds one annotated
`v0.3.0` tag. Publication uses an atomic dry-run followed by one normal atomic
push of only public `main` and that tag. Live-remote inspection and a fresh
public checkout must confirm the exact reviewed objects, preserved v0.1.0 and
v0.2.0 refs, and no additional public ref.

## Active integration and shadow boundary

After publication and fresh-checkout verification, the existing active public
source fast-forwards from v0.2.0 to exact v0.3.0. Its aggregate-link inode, raw
target, resolved ownership shape, user state, and Codex configuration remain
unchanged. Shell-level checks establish nineteen resolved public skills,
fourteen stable rows, five provisional rows, eighteen routes, and byte parity
with the release. They do not establish refreshed application discovery.

The personal same-name router remains installed. The resulting public/personal
duplicate is an intentional shadow. A full Codex restart and source-qualified
fresh-session selection of the public v0.3.0 router remain an externally
observable result. APG24 neither fabricates that evidence nor decommissions the
personal router.

## Support and authority limits

ZUnit support remains exactly v0.8.2 with Zsh 5.9.2 in the tested environment
and APG22C selected-user-startup boundary. Exact Zsh 5.3.1 is unsupported;
every other pair is unverified. The Nix, PostgreSQL, and SQLite profiles grant
no evaluation, build, connection, migration, database mutation, activation, or
destructive authority.

Release inclusion does not equal stable maturity, automatic invocation,
comparative superiority, universal applicability, or production warranty. No
root/private cutover occurs, all public artifacts remain independent of
publication-excluded evidence, and no successor roadmap or phase is authorized.

## Terminal boundary

The release-source record targets
`published-pending-fresh-session-shadow-smoke`. Exact postcommit Git objects,
remote observations, link identities, report identifiers, and reviewer returns
are retained only in publication-excluded or managed operational evidence.
