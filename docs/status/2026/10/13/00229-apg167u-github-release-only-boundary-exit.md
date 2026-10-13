# APG167U GitHub-only release boundary candidate exit

Phase ID: `APG167U`

Status: terminal amended candidate after supplied independent work review;
dispatcher finalization remains separate.

## Scope and result

Candidate native authority-discovery repair, read-only release workflow and
tree-bound no-rebuild GitHub-only attestation. See the
[evaluation](../../../../evaluations/apg167u-github-release-only-boundary.md)
and [ADR 0079](../../../../adr/2026/10/0079-github-release-only-boundary-and-tree-bound-attestation.md).
This record does not claim dispatcher acceptance or release qualification.

## Verification and remaining stops

Fresh terminal fixture verification passes 446 focused Python cases. Scoped
Ruff, workflow topology, test inventory and public-policy consistency pass.
The work-review findings are dispositioned as amend: capture premerge authority,
recheck durable run/artifact evidence after merge, use the earliest artifact
expiry and bind native guard/scan evidence. Terminal amendments were not
independently re-reviewed.
Actual historical artifact replay is network-blocked; fresh hosted RC success
is pending. Required-check enforcement and eligible review or an explicit
reviewed waiver must be read back before any attended merge.

The producer does not stage or commit; the dispatcher owns local finalization.
Public staging, settings changes, merge, tag and GitHub Release are distinct
attended operations. No package-manager publication or local binary build is
authorized. Release Starport 9 receives the verified GitHub handoff only after
publication. No successor authority is granted here.
