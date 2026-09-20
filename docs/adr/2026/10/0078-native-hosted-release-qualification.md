# ADR 0078: Native hosted release qualification

Date: 2026-10-11

Status: Proposed

Phase: APG167Q

## Context

Compiling every platform on one Linux runner does not prove native execution.
The release candidate needs three native Go and Nix lanes, sealed artifacts,
consumer smoke of already packaged bytes, and scans of all eleven distributables.
Hosted qualification has not yet been observed for this candidate.

## Decision

The proposed native qualification owner uses `macos-15` for Darwin ARM64,
`ubuntu-24.04` for Linux x64, and `ubuntu-24.04-arm` for Linux ARM64. Each lane
checks actual host identity and Go 1.26.9, runs native tests, vet and race checks,
compares two binary builds, and exercises the installed Nix runtime and profile.
The Go language floor remains 1.25. Native compiler evidence is retained and
bound to the exact binary, source commit and tree.

Assembly consumes sealed successful native artifacts by immutable artifact ID.
It packages three wheels, one sdist, four npm tarballs and three binaries without
compilation. Each native consumer exercises the exact sealed archives. Scans
cover source, eleven assets, a derived sdist installation, and the conditional
Python dependency: fourteen views. The derived installation may compile on its
native hosted Linux runner; it never replaces distributable bytes. The aggregate
fails on missing, failed, skipped, duplicate or mismatched evidence.

Consumers and scans verify the downloaded bundle's artifact ID, archive digest,
extracted bytes and producer seal in a dedicated step. Only that step exports
the read token; packaged consumer and scanner execution receive no such token.
The scan input and scan receipt independently recheck the expected seal and
source identity. Assembly's public projection manifest is retained beside its
matrix receipt, bound by digest, and linked from the aggregate index.

Ordinary PR security and governance checks remain active. Their former package,
SBOM and two-system Nix jobs are replaced by the native workflow's authority.
Before merge an attended administrator must migrate required checks and read
back the ruleset, including `native-release-candidate-gate`. Source staging
authorization does not authorize settings mutation or merge.

PR artifacts use fourteen-day retention. Optional ninety-day RC dispatch is a
future reviewed extension. Expired artifacts require fresh hosted qualification;
expiry never waives the gate. Event base SHAs can become stale relative to the
merge ref; the exact parent guard then fails closed until CI is refreshed.

Publication remains separately controlled. The existing private post-merge
asset-building path compiles locally and is unusable under the current owner
direction. Its source-commit requirement is not bypassed. A future publication
decision must explicitly reconcile squash provenance with sealed tree-bound
candidate artifacts or implement a native hosted post-merge qualification path.
No local rebuild, repack after consumer smoke, merge, tag or publication follows
automatically from a passing PR.

The current `release.yml` is knowingly unsatisfiable for the PR-native bundle:
its manifest binds the PR merge-ref commit while publication requires the
squash-merged release commit. The workflow labels this blocked v0.13 path and
preserves the failing identity check. A green native gate is not evidence of
publication readiness, and reserializing the manifest after smoke is forbidden.

## Consequences

Native runner availability, Nix compiler build time, real Go build-info parsing,
Darwin reproducibility, artifact transfer and offline consumer installs need
hosted evidence. Source fixtures establish their exercised contracts only.
All mutable work stays outside the source checkout. Release archives and their
SHA-256 seals survive consumer and scanner jobs unchanged.

Rollback restores the earlier source workflow only through a reviewed change;
it cannot relabel cross compilation as native qualification. Required-check
migration must be coordinated with whichever source topology is active.

### APG167R failure observability

Failed qualification commands retain sanitized stdout and stderr tails and an
early Go failure extract (including compile and vet errors), each bounded to
16 KiB. Qualification exceptions are
recorded as `apgr.native-lane-failure/v1` JSON outside the sealed lane output.
If diagnostics cannot be written, the sanitized original error remains in the
job log and the lane remains failed.
Each native lane uploads these diagnostics for fourteen days only when its
qualification step fails. The command and lane remain failed; diagnostics do
not satisfy a qualification gate. Each command has a forty-five-minute timeout;
on timeout the adapter kills its POSIX process group before recording partial
output. This leaves time for diagnostics when an early command stalls. A late
command or runner cancellation can still reach the overall job deadline first
and prevent retention.

The first Darwin Go-test cause remains
`MACOS_NATIVE_TEST_ROOT_CAUSE_PENDING_HOSTED_REEXECUTION`. Source fixtures prove
observability and failure behavior; the next native hosted run must establish
the actual cause and qualification outcome.

## Provenance

This design is independently written from APGR's existing packaging and CI
owners and the human-supplied native qualification requirements. Theme Forge
Nebular Fusion's public native RC workflow is architectural precedent; no code
or prose is copied. Action capabilities were checked against official pinned
[upload metadata](https://github.com/actions/upload-artifact/blob/b7c566a772e6b6bfb58ed0dc250532a479d7789f/action.yml)
and [download metadata](https://github.com/actions/download-artifact/blob/d3f86a106a0bac45b974a628896c90dbdf5c8093/action.yml).
The pinned [download implementation](https://github.com/actions/download-artifact/blob/d3f86a106a0bac45b974a628896c90dbdf5c8093/src/download-artifact.ts)
nests ID-based downloads under the artifact name even for one ID when
`merge-multiple` is false. Topology fixtures preserve that layout and require
fresh qualification before changing the pin.
