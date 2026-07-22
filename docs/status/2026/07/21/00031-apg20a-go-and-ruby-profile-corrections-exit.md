# APG20A Go and Ruby Profile Corrections Exit

Phase ID: `APG20A`

## Disposition

Complete — Go and Ruby profile defects corrected and both profiles implemented

## Scope and outcome

APG20A accepts APG20's deferred candidates and material findings as the
complete corrected baseline. It retains independent provisional Go and Ruby
profiles after current-source refresh, frozen and defect-specific scenarios,
read-only dogfood, focused tests, and fresh non-author acceptance.

The Go candidate uses one newly discovered bounded correction to make switch,
type-switch, and select decision counting clause-exact. Its exported-method
wording completes a known APG20 correction. The Ruby candidate uses one newly
discovered bounded correction to exclude ordinary statically named public
dispatch from dynamic-family breadth. Neither candidate has an unresolved
material defect.

No architecture decision was required. ADR 0016 remains the next available ADR
and is reserved for a later accepted ownership decision. This exit is 00031;
ADR and exit sequences remain independent.

## Report-lock defect

The APG20 concurrency retry reproduced under bounded concurrent stress. A
legitimate append-lock holder could remove its directory after failed
acquisition but before type validation, causing normal release to be reported
as unsafe. The helper now tolerates disappearance across both release windows
while rejecting unsafe files, FIFOs, and symlinks. A deterministic DEBUG-hook
regression exercises the exact interleaving. Focused, complete, stress, syntax,
and adversarial review accepts the correction.

## Profile results

The Go leaf corrects source-license boundaries, exported-API and local-binding
measurement, protected-data sink coverage, semantic responses, and dogfood
truth. Go 1.26.5 calibration covers genuine maintained Green, Yellow, Orange,
maintained Red, generated, semantic, and synthetic legacy cases.

The Ruby leaf corrects bounded dynamic-dispatch responses, shared-state
responses, thread/fiber/ractor lifecycle, authorized compatibility changes,
and dogfood truth. Ruby 4.0.6 and RubyGems/Bundler 4.0.16 calibration covers a
12-line maintained Green case plus Yellow, Orange, maintained Red, generated,
semantic, and synthetic legacy cases.

All shared structural, exact-boundary, coupled-signal, legacy, classified-
artifact, pairing, override, and non-trigger scenarios pass. All 20 frozen Go
and 22 frozen Ruby semantic scenarios and their defect-specific additions pass.

## Resulting repository and distribution

The private-development catalog contains 14 canonical leaves, 14 relative
projections, 6 stable process rows, 8 provisional rows, and 13 routable non-
router capability-map entries. Go and Ruby are known-unmanaged development
skills. The six v0.2 managed defaults and project, user, and release schema
version 1 remain unchanged. Public v0.2.0 and the active public-backed
integration remain 6/6/6.

## Validation and review

The skill-library, report-tool, project, checker, release, user, record-
identity, syntax, help, documentation, privacy, durable-reference, link, mode,
schema, and whitespace gates pass. Fresh Go, Ruby, report-lock, integration,
current-documentation, identity, distribution, and complete-diff reviews accept
the resulting tree. Preexisting skill and distribution artifacts remain
unchanged except for the explicitly authorized integration owners.

## Boundary and APG21 gate

No root guidance was migrated, no private skill was decommissioned, and no
dependency, plugin, public release, active-integration mutation, state-schema
change, Nix, PostgreSQL, SQLite, ZUnit, manager-prompt skill, application smoke,
or APG22 work occurred.

APG21 may begin only after this phase is committed, its managed Git report is
complete, private `main` is pushed and remote-equal, external state is verified
unchanged, and its schema-valid operational report is appended and detected.
