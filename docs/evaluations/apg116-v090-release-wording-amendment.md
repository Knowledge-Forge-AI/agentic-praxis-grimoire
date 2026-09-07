# APG116 v0.9.0 release wording amendment

## Scope and disposition

APG116 began qualification of the APG115 release source. Inspection of actual
retained Python package metadata reproduced permanent instructions telling
v0.9.0 users to remain on v0.8.1. The same preparation-only status appeared in
release-facing documentation. The authorized source-amendment branch therefore
applies: `V090_SOURCE_AMENDMENT_REQUIRES_QUALIFICATION`.

Proposal disposition: **amend**. The original qualification scope is preserved;
the plan and advisory findings do not replace it. Closeout corrected the
docs-index omission found by independent review and extended the executable
wording gate to all eleven audited package-facing surfaces. Dated historical preparation records remain
historical, and the released consumer control requirements remain unchanged.

## Amendment

Permanent documentation must describe the version it accompanies and make
installation conditional on publication without asserting a publication event.
The bounded amendment covers Python's root README description, release notes,
distribution, index and CLI/Go reference documentation, rendered npm README
templates and Go fixture introductions. The stale Python publication epoch alias
now agrees with v0.9.0 while production builds retain version-selected epochs.
Generic future-version placeholders, runtime/developer distinctions,
Darwin qualification limits and pending JACA adoption are preserved.

## Evidence boundary

Both actual APG115 evidence packets were checked against their retained file
inventories, and their terminal inventory was compared with committed source
blobs, file kinds and executable status. This confirms historical packet integrity;
it does not qualify amended source or replace fresh release construction.

Live development equality was observed separately from stale cached tracking.
Read-only public refs still identify the released v0.8.1 predecessor and contain
no v0.9.0 tag. Registry contents and immutable checksum history were not qualified
in this amendment branch.

Affected verification and its limits are recorded in
[exit 00161](../status/2026/09/08/00161-apg116-v090-release-wording-amendment-exit.md).
The dispatcher supplied the independent pre-final findings. Closeout amended the
reviewed material and rechecked affected scopes without another substantive review;
internal worker output remains implementation evidence only.

## Deferred work

The private handoff is an amendment evidence skeleton, not an executable
publication packet. Final candidate identities, ten-asset reproducibility,
prospective module sums, installed consumers and publisher regression qualification
are deferred until the amended committed source is available and qualification
is authorized. No older bundle is represented as final for the changed source.

Public publication, registry operations, host activation and downstream adoption
remain separate boundaries. JACA CI, JACA XO, Theme Forge and Repo Map retain
their support order. No successor begins automatically.
