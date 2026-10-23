# ADR 0079: GitHub-only release and tree-bound native attestation

Date: 2026-10-13

Status: Proposed

Phase: APG167U

## Context

The v0.13.0 finish line is a published GitHub Release containing unchanged
native-hosted distributables. Package-manager publication belongs to a later
Release Starport 9 handoff. The previous release event workflow minted PyPI
OIDC credentials and offered an automatic publisher; that violates this
boundary even though its source-commit comparison currently fails.

Pull-request CI tests a synthetic merge commit. Squash merging produces a
different commit identity. Rewriting the tested manifest or rebuilding after
CI would discard the candidate's tested provenance.

## Decision

Replace the publisher with an exactly constrained read-only release audit.
It has no registry credentials, publication action, write permission or OIDC
grant. Workflow policy rejects publication markers across the workflow set.

Before attended merge, bind successful public and native runs to the same
head, base, synthetic merge commit and exact source tree. The synthetic commit
must have the frozen base and head as its ordered parents. Require actual
native index success, all nine matrix members, eleven distributables,
fourteen scan views and three consumers. Verify downloaded artifact archive
digests and unchanged bundle content.

Derive the tested merge commit from the native index. Before merge, capture
its ordered parents/tree and each run's exact PR association, run attempt,
workflow and check-suite identity. After merge, recheck durable run metadata,
successful jobs and pinned artifacts against that operator-reviewed candidate.
Do not depend on mutable live run PR associations or continued synthetic
commit availability. The candidate self-hash is an integrity check, not a
signature; the attended operator retains its accepted premerge digest.

Require active enforcement of both aggregate checks from GitHub Actions,
strict base freshness, pull-request, deletion and non-fast-forward rules and
no bypass actors. Require the eligible approval count configured by the
authenticated active ruleset, or an explicitly reviewed governance waiver.
A configured count of zero requires no approval. A waiver does not waive checks or permit an administrative
merge bypass. A waiver hash belongs in the squash message and its canonical
content accompanies the release attestation.

The squash commit must have the frozen base as sole parent, the exact tested
tree, the subject `Release v0.13.0`, and the exact PR association. The annotated
tag points to that commit. Preserve the tested merge-ref identity in manifests.

Upload sixteen unchanged files: eleven distributables, three binary manifests,
the distribution manifest and `SHA256SUMS`. A recorded mapping relates the
fifteen logical checksum paths to flat release filenames. Verify exact names,
sizes and SHA-256 from the draft before publication, then from the published
release. The release notes bind exact CI run IDs and the candidate attestation.
The hosted workflow is a postpublication audit, not the prepublication gate.

## Consequences

No publication is performed by this source phase. Missing governance, fresh
native success, read access or exact tree equality blocks the attended release.
Administrative bypass evidence is a reviewed premerge snapshot; hosted public
readback cannot prove current hidden administrator configuration.
The public aggregate has seven-day retention and native artifacts fourteen
days; the earliest actual expiry bounds the operation. Expired Actions
artifacts require renewed qualification; a late hosted audit
may fail after retention expires. Released assets and tags are never silently
replaced. Release Starport 9 receives verified URLs, tagged identity, hashes
and provenance, with package-manager writes explicitly unperformed.

## What would make this wrong

Different squash trees, incomplete API identity fields, inaccessible enforcement
evidence or expired artifacts prevent no-rebuild qualification. Failures require
a reviewed correction and fresh evidence, not relaxed identity checks. The
read-only workflow cannot prevent an operator publishing a bad release; the
attended draft verifier owns that stop.

## Provenance

Independently authored from the APG167U task, supplied plan-review findings and
existing APGR native artifact contracts. GitHub documents the
[pull-request merge ref](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request)
and [ruleset checks and integration binding](https://docs.github.com/en/rest/repos/rules).
No external code or prose is copied. This amends the publication boundary in
[ADR 0078](0078-native-hosted-release-qualification.md).

The supplied work review prompted the captured premerge bindings. GitHub's
[workflow-run API](https://docs.github.com/en/rest/actions/workflow-runs#get-a-workflow-run)
defines the readback surface; live historical readback observed changed PR
associations. That observation supports preserving associations before merge;
no guarantee about closed-PR association retention is assumed.
