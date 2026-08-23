# APG102 Cross-Consumer v0.7 Release Readiness

## Result

APG102 qualifies the exact v0.7.0 release candidate across its Go, CLI,
Python, npm, target-runtime, agent-discovery, JACA, environment, hotspot,
historical, and rollback boundaries. Publication is the remaining meaningful
step.

Terminal disposition:
`V07_RELEASE_CANDIDATE_READY_FOR_APG103`.

No tag, GitHub Release, PyPI upload, npm publication, Go proxy publication,
Nix change, active installation, or deployment occurs in this phase.

## Readiness corrections and baseline repairs

APG102 applies bounded corrections and baseline repairs inside accepted v0.7
architecture.

First, the public candidate Go test suite is corrected: `report/testhelpers_test.go`
guards differential python oracle execution with a test skip when
`report/testdata/python_oracle.py` is absent. Because `report/testdata/` is
intentionally excluded from the public source projection by distribution policy,
this ensures `go test ./...` passes cleanly with zero failures across all public
packages in the materialized candidate.

Second, the public Markdown link gate now classifies
`hotspot/testdata/classification/` as test data rather than human
documentation. The intentionally absent fixture-relative target remains
absent, preserving hotspot classification behavior. The exclusion is narrow:
ordinary public and human Markdown remains link-checked, and a regression
proves that a broken link outside that test-data prefix still fails.

Third, Python wheel validation now checks the complete
`apg.binary-manifest/v1` object rather than a subset. It rejects extra or
missing keys and disagreement in schema, version, Go target, Python and npm
mapping, binary name, size, checksum, corpus identity, report and feature
schemas, Go module and toolchain facts, build flags, build identity, and
embedded build information. Complete regression coverage validates each refusal
path.

Additionally, two failing baseline checks inherited from APG101 were repaired:
`report/testdata/python_oracle.py` sys.path was repaired to locate `agent_report`
under `private/oracles/` (resolving `ModuleNotFoundError` during dev parity
tests), and the APG98 evaluation test was updated to read
`docs/guides/environment-snapshots.md` instead of the APG101 redirect stub.

None of these changes alters a public API, schema, target, package name,
version, or distribution architecture. No ADR is allocated.

## Exact candidate and artifact result

The single editable version authority remains `0.7.0`. The final prospective
source tree is materialized through the public-release policy, then two
disjoint clean roots build the complete release-shaped candidate. Every
corresponding artifact is byte-identical across the two builds:

- three `CGO_ENABLED=0` Go binaries and three
  `apg.binary-manifest/v1` manifests for `darwin/arm64`, `linux/amd64`, and
  `linux/arm64`;
- platform wheels tagged `macosx_11_0_arm64`, `manylinux_2_17_x86_64`, and
  `manylinux_2_17_aarch64`;
- one Go-source, self-contained source distribution;
- the dependency-free npm launcher and three platform packages; and
- the coordinated distribution manifest and checksum inventory.

The source distribution rebuilds the host wheel from its own contents with a
local Go 1.25 toolchain. The rebuilt wheel is byte-identical to the direct
host wheel, and no checkout content outside the source distribution is used.
The public candidate contains the five public Go packages, `cmd/apgr`, thin
Python and npm adapters, canonical skills, build helpers, documentation, and
license material. Private evidence, generated artifacts, operator state, and
obsolete portable semantic implementations remain excluded.

Exact final tree, public-source fingerprint, filenames, sizes, SHA-256 values,
manifest identities, and build-information fields are retained in the
publication-excluded readiness packet. Keeping those values outside public
candidate documentation avoids making the source distribution describe its
own changing checksum.

## Direct and installed parity

The native direct binary, the Python wheel, and the npm platform package use
the same canonical binary bytes. Representative version, build-information,
report, skill list/context/resolve/materialize, environment, hotspot JSON, and
response operations agree in output, exit behavior, and generated artifacts
where portable semantics own the result.

Python installation uses a fresh virtual environment, disposable home and
APGR roots, `--no-index`, and only local artifacts. npm installation uses a
fresh project, local tarballs, offline mode, and disabled audit and funding
requests. Neither installed wrapper downloads, builds, or reimplements APG at
runtime. Repository-maintenance commands retain their repository-authority
checks.

## Supported target runtime qualification

Every advertised Go target executes in a real disposable runtime:

- `darwin/arm64` runs natively, including direct, Python, and npm paths;
- `linux/amd64` runs the exact static target binary through the already
  available local OrbStack x86 execution facility; and
- `linux/arm64` runs the exact binary plus isolated Python-wheel and Node 22
  npm-package smokes in existing local containers.

The local x86 facility has no Python or Node image or interpreter, so the
linux/amd64 wrapper packages receive complete structural, manifest, archive,
and embedded-binary validation while their exact embedded binary receives the
required real x86 runtime smoke. No image is pulled, no hypervisor is
installed, and no network or persistent host configuration is used. This is
not a cross-build-only claim: all three target binary byte sets execute and
report the expected target, version, corpus, and feature identity.

## JACA direct-consumer result

Current JACA remains read-only. A disposable exact source copy adds one narrow
JACA-owned adapter in its existing readiness package and a local module
replacement from semantic version `v0.7.0` to the final release-shaped APG
candidate.

The adapter imports only APG public packages and proves, in process:

- canonical Show, Diff, and Operational report records for read-only APG and
  JACA repositories;
- structured deterministic skill resolution and task-scoped
  materialization, including bundle and manifest fingerprints;
- environment profile validation, capture, store, load, Isolated resolution,
  Overlay resolution, and provenance;
- separate JACA-owned injection of a synthetic secret after APG resolution,
  with sensitive-name refusal and no value leakage into APG evidence; and
- hotspot model and canonical JSON consumption, including rankings,
  confidence, and unavailable reasons without Markdown parsing.

Focused adapter tests, the complete safe JACA Go-module test suite, vet, and
dependency inspection pass. The adapter has no APG internal import, APG CLI
child process, shell boundary, reverse JACA import, or cycle. The real JACA
checkout is unchanged. A publication-excluded patch and hash form the bounded
post-release JACA-owned landing handoff.

## Selected-only agent discovery

A real Codex 0.147 app-server probe uses a disposable home, Codex home, and
project whose repository skill surface contains only the APG resolver's
two-skill materialization. The intersection of discovered skills with the
canonical APG corpus is exactly `go-language-profile` and `go-test-profile`.
Independent provider system skills may appear, but no other canonical APG ID
and no global 39-skill APG root appears. The readiness packet binds the
selection, bundle, materialization, provider, and returned discovery facts to
the final candidate.

## Historical and rollback result

The exact v0.6.0 source authority reconstructs twice into the published
universal wheel, source distribution, and checksum bytes. Their SHA-256 values
remain identical to the frozen publication packet. In a disposable Python and
APGR environment, local package installation returns version and runtime
identity through `0.6.0` to `0.7.0` and back to `0.6.0`.

The v0.7 candidate therefore neither changes historical v0.6 interpretation
nor prevents package/runtime rollback. No claim is made that v0.6 understands
v0.7-only state.

## Verification and preserved state

The canonical unit/integration gate runs with its exact TypeScript, JavaScript,
Node, Go, and Python prerequisites. Go package tests, race tests, vet, Python
packaging and bridge tests, npm tests, report/skills/environment/hotspot/
response suites, public projection and link checks, manifest tamper tests,
historical reconstruction, target smokes, external Go consumption, JACA
consumption, real agent discovery, and isolated rollback all pass.

## Publication readiness and authority correction

APG102 establishes the authoritative publication architecture for v0.7.0:

1. **Release Asset Authority**: `libexec/apg_distribution_candidate_contract.py`
   defines the authoritative machine-readable inventory and role mapping for all
   ten GitHub Release assets (1 manifest, 1 checksum file, 3 platform Python
   wheels, 1 Python sdist, 3 npm platform tarballs, 1 npm launcher tarball).
2. **PyPI Trusted Publishing**: `.github/workflows/release.yml` is updated for
   v0.7.0. It executes only on published GitHub Releases, enforces PyPA OIDC
   Trusted Publishing (`id-token: write`, `environment: pypi`), verifies
   repository and `v0.7.0` tag identity, and filters the three platform wheels
   (`darwin/arm64`, `linux/amd64`, `linux/arm64`) and normalized sdist. It verifies
   checksums against `SHA256SUMS`, rejects universal `py3-none-any`, missing,
   extra, duplicate, or mismatched Python artifacts, and publishes only the
   `verified-dist` directory without token fallback or runtime compilation.
3. **npm Publication Authority**: `libexec/apg_npm_distribution.py` defines the
   first-publication bootstrap and steady-state transition:
   - First-release bootstrap is operator-owned using prequalified package
     tarballs with `--access public`.
   - Platform packages (`@knowledge-forge-ai/apgr-darwin-arm64`,
     `@knowledge-forge-ai/apgr-linux-x64`, `@knowledge-forge-ai/apgr-linux-arm64`)
     publish strictly before the launcher package (`@knowledge-forge-ai/apgr`).
   - Every publication step is followed by live readback verification of package
     name, version, and integrity.
   - Partial or mismatched registry state triggers a fail-closed stop without
     destructive unpublishing.
   - Credential safety is enforced: no tokens in arguments, logs, or files.
   - Steady-state transitions to GitHub Actions OIDC Trusted Publishing once the
     initial bootstrap packages exist on npmjs.com.

The release candidate preserves:

- 39 canonical skills, 39 catalog rows, 39 projections, and 39 discoverable
  skills;
- 14 stable and 25 provisional skills with zero malformed entries;
- 9,504 description bytes and 9,492 description characters beneath the
  9,527-byte ceiling;
- corpus fingerprint
  `0509803b3c12e0366917a341c9d56945d7966897953415acf0c997254e1331c1`;
- accepted report, skill-bundle, environment, hotspot, response, and
  distribution schemas; and
- the three-target matrix, package names, and existing CSS and JavaScript
  qualification debt.

No real APGR, agent, Codex shell-environment, JACA, Nix, `.flakes`, registry,
remote, tag, or release state is changed.

## APG103 boundary

The publication-excluded machine packet and human operator handoff bind the
exact final candidate, artifact and package inventory, checksums, supported
target results, JACA and discovery evidence, rollback, publication ordering,
stop and rollback boundaries, and immutable external readback plan.

APG103 may publish only that exact terminal candidate under separate
authorization. If any external artifact or immutable readback differs, APG103
must stop rather than repair or substitute it. Deployment and active host
integration remain separate even after publication.

