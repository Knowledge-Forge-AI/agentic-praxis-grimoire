# ADR 0028: Exceptional v0.4 NOTICE Identity Correction

- Status: Accepted
- Date: 2026-07-26
- Proposed and accepted in: APG43
- Relates to: APG42 release publication, APG19 semantic record identity

## Context

APG42 published a release-blocking unrelated project identity in `NOTICE`.
The maintainer explicitly authorized one exact correction: restore the
canonical historical Agentic Praxis Grimoire bytes, amend APG42, replace the
development and public release refs with explicit leases, converge the active
public-backed source, and record the action forward in APG43.

## Decision

Accept this as a one-time exception to the normal forward-only and append-only
history rules. The amended APG42 source, public `main`, annotated `v0.4.0`, and
active public-backed checkout contain the canonical NOTICE. Public v0.1.0
through v0.3.0 remain unchanged. The v0.4.0 scope, maturity, routing, release
metadata, and limitations remain unchanged.

The old and new Git objects, leases, active-link evidence, and replacement
managed reports remain in private audit evidence. The exception does not
authorize a reusable force-push policy, a tag replacement for another reason,
or a general history-rewrite capability.

## Consequences and boundary

The corrected APG42 is the semantic release source; APG43 is its forward audit
record. Future releases return to append-only behavior. No phase after APG43 is
authorized, and v0.5 begins only after separate explicit maintainer authority.
No skill, projection, catalog, route, maturity, dependency, or target-
repository change is implied by this correction.

## Alternatives considered

* Leave the incorrect identity in place: rejected because it leaves a
  release-blocking identity defect in the public artifact.
* Correct only the active checkout: rejected because development and public
  release objects would remain inconsistent.
* Establish a standing rewrite policy: rejected because this authority is
  exact, exceptional, and limited to the named correction.
