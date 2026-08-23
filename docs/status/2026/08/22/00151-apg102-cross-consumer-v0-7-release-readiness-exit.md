# APG102 Cross-Consumer v0.7 Release Readiness Exit

Phase ID: `APG102`

## Status

**Complete — the exact v0.7.0 release candidate is ready for separately
authorized APG103 publication.**

Terminal disposition:
`V07_RELEASE_CANDIDATE_READY_FOR_APG103`.

## Outcome

The final release-shaped source produces two byte-identical builds of three Go
binaries and manifests, three platform Python wheels, one Go-source source
distribution, one npm launcher, three npm platform packages, and the
coordinated distribution inventory. The source distribution independently
rebuilds the byte-identical host wheel.

Direct Go, installed Python, and installed npm host paths share the same binary
bytes and agree across representative report, skill, environment, hotspot, and
response operations. Every advertised target binary executes in a real
disposable runtime. Native Darwin and Linux arm64 additionally run their
Python and npm packages; linux/amd64 package structure and embedded bytes are
fully validated, and the exact embedded x86 binary executes under the existing
local x86 facility.

## Cross-consumer evidence

A disposable copy of current JACA directly imports APG's public report,
skills, environment, and hotspot packages through a narrow JACA readiness
adapter. In-memory report records, selected-only materialization, environment
resolution with separate synthetic-secret injection, and structured hotspot
consumption pass the focused and full safe module tests. There is no APG CLI,
shell semantic boundary, internal APG import, reverse import, or cycle. The
real JACA checkout remains unchanged.

A real isolated Codex app-server probe discovers exactly the two selected APG
skill IDs and no non-selected canonical APG skill or global APG corpus root.

## Corrections and readiness gates

The public candidate Go test suite is corrected to skip differential python
oracle tests when `report/testdata/python_oracle.py` is absent, allowing
`go test ./...` to pass cleanly in the public projection. The intentionally
broken hotspot Markdown fixture is narrowly removed from human-documentation link
authority while ordinary public Markdown remains strictly checked. Python wheel
validation now checks the complete exact binary manifest and fails closed on
schema and identity disagreement. Inherited baseline gate failures
(`python_oracle.py` module import and APG98 evaluation test path) are repaired.
All corrections remain within accepted architecture and have regression coverage.

The canonical broad gate, Go test/race/vet, packaging and wrapper tests,
complete report/skills/environment/hotspot/response suites, public and
historical projections, external Go consumer, target-runtime smokes, JACA
adapter, real discovery, and isolated rollback pass against the final
candidate.

The publication authority is corrected for v0.7.0:
- `.github/workflows/release.yml` implements PyPI Trusted Publishing for the
  real v0.7 Python distribution (3 platform wheels with `manylinux_2_17_*` and
  `macosx_11_0_arm64` tags, 1 sdist, no universal wheel) with manifest-driven
  checksum and asset verification.
- `libexec/apg_npm_distribution.py` and
  `libexec/apg_distribution_candidate_contract.py` define authoritative asset
  roles, platform-before-launcher publication ordering, preflight checks,
  fail-closed registry state classification, live readback verification, and
  credential safety for npm packages.

The exact v0.6 source reconstructs the published artifact bytes, and a local
isolated installation returns `0.6.0` to `0.7.0` and back to `0.6.0`.

## Preserved state

Version is `0.7.0`. The corpus remains 39/39/39/39, 14 stable / 25
provisional, zero malformed, 9,504 description bytes, 9,492 description
characters, and the 9,527-byte ceiling with unchanged corpus fingerprint
`0509803b3c12e0366917a341c9d56945d7966897953415acf0c997254e1331c1`.

No skill, maturity, target, package name, public schema, Nix surface, active
root, tag, GitHub Release, registry artifact, deployment, or publication state
changes.

## Publication handoff

The publication-excluded readiness packet (`apg102-readiness-packet.json`) and
APG103 operator handoff (`apg103-publication-handoff.md`) were emitted as
private operator-handoff artifacts and are not part of the public repository.
They bind the exact final prospective tree, public-source identity, artifact names
and checksums, target results, package inventory, JACA patch, discovery bundle,
rollback result, broad gate, publication order, stop boundaries, and immutable
readback plan. Public documentation intentionally does not embed private
development identities or self-referential source-distribution checksums.

## Next authorization

APG103 may begin only under a separate dispatcher assignment and may publish
only the exact APG102 packet candidate. It owns the annotated `v0.7.0` tag,
GitHub assets, Go proxy readback, PyPI and npm publication/readback, and Nix
handoff. Any mismatch must stop publication. Deployment and active host
mutation remain separately authorized.

