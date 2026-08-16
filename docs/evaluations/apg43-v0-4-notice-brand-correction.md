# APG43 v0.4 NOTICE Brand Correction

## Decision and scope

APG43 is a one-time, explicitly maintainer-authorized correction of a
release-blocking project-identity defect in the v0.4.0 `NOTICE`. The exact
historical Agentic Praxis Grimoire bytes were restored in the amended APG42
source, rebuilt into v0.4.0, published to the public repository, and applied to
the active public-backed checkout.

The correction changes only the `NOTICE` identity and the APG42 factual records
that depended on the false acceptance of that identity. The release remains
28/28/28, with fourteen stable and fourteen provisional rows, twenty-six
general routes, one ChatGPT-local route, twenty-seven checked edges, and no
mandatory chain. ADR 0025 remains Rejected, ADR 0026 remains Accepted and
controlling, ADR 0027 remains Rejected, and the deferred/absent candidates are
unchanged.

## Exceptional history action

The maintainer authorized the exact exception recorded in ADR 0028: amend the
current APG42 development commit, replace development `main`, rebuild the
release, atomically replace public `main` and the annotated `v0.4.0` tag with
explicit leases, and converge the active source. The historical v0.1.0 through
v0.3.0 commits and tags remain unchanged. This is not a general force-push
policy. Future releases return to append-only history, and v0.5 requires a
separate authorization.

## Verification

Two disjoint corrected candidates were equal in manifest, tree, commit, tag,
metadata, refs, modes, symbolic-link targets, and recursive tree fingerprint.
The live public refs, a fresh public checkout, and the active source all
contain the canonical `NOTICE` bytes. Skill-library, record-identity, release,
Python, Bats, and configured test gates passed in the supported disposable
environment; the aggregate-owned skill integration and its 28 resolved skills
were preserved without direct-link migration or configuration change.

The complete object identities, leases, report hashes, active-link
fingerprints, and command-level evidence are publication-excluded in
`private/evaluations/apg43/` and the managed APG42/APG43 reports.

## Limitations and disposition

No fresh supported-client invocation was fabricated where it could not be
observed safely. No skill, projection, catalog, route, maturity, dependency,
target repository, signing, announcement, GitHub Release, or v0.5 work is part
of APG43.

**Result:** Complete — canonical NOTICE restored in amended APG42, corrected
public v0.4.0, and active public-backed source; exceptional rewrite recorded;
v0.5 not started.
