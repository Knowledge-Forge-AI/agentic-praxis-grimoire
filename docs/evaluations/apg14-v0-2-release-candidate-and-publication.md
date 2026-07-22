# APG14 v0.2.0 Release Candidate and Publication

## Objective and authority

APG14 accepts APG13, corrects two APG9 evidence classifications without
changing stability, prepares the final public-safe source, builds and reviews a
deterministic v0.2.0 candidate, publishes exactly one public release commit and
annotated tag, and fast-forwards the existing public-backed integration source.
It does not change a skill, maturity row, schema, command surface, dependency,
plugin, Codex configuration, reference repository, RepoMap checkout, or retired
Superpowers state. It authorizes no successor roadmap epic.

## Release content

Public v0.2.0 contains six stable skills. APG10 selectively integrated one
independently written current-change cleanup refinement into the implementation
owner. APG11 formalized skill maintenance and dependency-free mechanical
validation. APG12 and APG12A added corrected exact public distribution,
lineage, isolated executable validation, and genuinely read-only user checks.
APG13 promoted all six current skills to `stable` after individual review.

APG14 corrects the APG13 record so APG9 is a non-trigger rather than positive
use for implementation and debugging. Each owner retains repeated positive use
before and after Superpowers retirement. No procedure correction, frozen
application, final review, correction count, or maturity disposition changes.

## Candidate and public history

The release source is a reviewed clean private commit. Candidate A and an
independent deterministic rebuild use exact public v0.1.0 as base, one frozen
RFC3339 timestamp, and the verified maintainer identity. Their projected
manifests, trees, release commits, annotated tag objects, metadata, branch,
subject, and parent must be identical. Every tracked non-private path is
projected exactly once with matching bytes, modes, and symbolic-link targets;
`private/` is absent.

Public v0.1.0 remains historical and unchanged. Public v0.2.0 appends one
squashed `Release v0.2.0` commit whose sole parent is v0.1.0 and adds one
annotated `v0.2.0` tag. The v0.1.0 omitted-wrapper class is corrected by the
exact projection. Publication uses an atomic dry-run and one normal atomic
fast-forward push of only public `main` and `v0.2.0`, followed by live-remote
and fresh-checkout validation.

## Validation and review

The source and candidate gates include the complete checker, release, user,
report-tool, and project-skill suites; deterministic manifests; Python
compilation; shell syntax and help; Markdown and local links; confidentiality;
licensing and notices; critical owners; counters; schemas; modes; projections;
history; refs; and Git whitespace. Isolated candidate user-scope validation
covers list, install, check, repository duplicate warning, exact skill hashes,
stable catalog, conservative uninstall, and unrelated-skill preservation.

Fresh non-author reviews separately cover the APG13 record correction, staged
release source, candidate, public v0.1.0-to-v0.2.0 diff, active-integration
update plan, and complete resulting state. A blocker or material finding stops
publication until corrected and fully revalidated.

## Active integration and restart boundary

After verified publication, the maintainer's clean public checkout
fast-forwards from v0.1.0 to exact v0.2.0. Existing aggregate-link objects and
raw targets remain unchanged; only their public source content advances. Six
resolved skill hashes must match the public candidate. No `apg-user-skills`
state migration, Codex configuration change, install, adoption, update,
rollback, or uninstall occurs.

Shell-level integration checks do not prove that a running Codex application
has refreshed discovery. A full application restart followed by fresh-session
discovery and explicit invocation remains an external observation. APG14 does
not fabricate or trigger that observation.

## Limitations and boundary

The release does not establish automatic invocation, comparative superiority,
universal applicability, production warranty, publisher authentication, or a
release cadence. Candidate tests execute trusted project code rather than a
hostile-code sandbox. The terminal repository outcome is
`published-pending-fresh-session-smoke`; no successor phase begins
automatically.

## Subsequent external application disposition

The maintainer later completed the requested full Codex restart and
fresh-session smoke and reported that it passed. This closes the current
application-observation dependency without changing APG14's historical
terminal result. No exact user-interface log, timestamp, invocation telemetry,
or duplicate-source observation was supplied or inferred.
