# APG Distribution

This documentation covers v0.10.0. The preceding **v0.9.0** and **v0.8.1** releases
remain frozen. The distribution architecture preserves the multi-registry packaging
model and provides the 45-skill corpus. Local build and inspection do not publish
packages.

APG has one editable release-version authority:
`src/agentic_praxis_grimoire/VERSION`. Release-like Go builds receive that
value and the canonical skill-corpus fingerprint through linker injection.
The Python and npm builders read the same file; generated package metadata is
never an additional version authority.

## Runtime ownership and dispatch boundaries

Go owns portable report, skill bundle, environment snapshot, hotspot,
response-capture, and context-footprint semantics. Python is a thin
compatibility front door for those command families. Python remains the
intentional repository or host maintenance owner for change-size,
phase-commit-message, record-identity, test orchestration (`apgr test`),
public-release preparation, user and global skill maintenance, flattening,
and the legacy project-local symlink projection.

Importantly, `apgr test` (including `--summary-file` and the `policy` mechanical role)
is a repository maintenance workflow requiring an APGR Git source checkout and
the developer toolchain (Python 3.11+, pytest stack, Git 2.40+, Go 1.25+). The
prebuilt native Go binary (`bin/apgr`), bare wheels, and npm platform packages do
**not** carry the test runner or test suites (`libexec/apg_test.py` and `src/test/`
are intentionally excluded from binary distribution packages).

`check skill-library` retains Python topology, catalog, and projection checks,
then requires the private Go CLI to compare the checked-out metadata and every
canonical skill body with its embedded corpus. Portable task selection and
materialization are `skills resolve` and `skills materialize`; the historical
`apg-project-skills` install/adopt/check/uninstall path is only repository-local
projection compatibility.

## Binary manifest and targets

Each supported target has one canonical `apgr` byte sequence and one canonical
`apg.binary-manifest/v1` document. The manifest binds the APG version, module,
Go target, Python and npm target mappings, binary basename, byte size, SHA-256,
corpus fingerprint, build flags, and build-information schema. It contains no
time, local path, host, user, or random value. APGR also
exposes the public `footprint` package and its three context-footprint schema
families; those identities are versioned independently from the binary
manifest.

The supported matrix is:

| Go target | Python platform tag | npm platform package |
| --- | --- | --- |
| `darwin/arm64` | `macosx_11_0_arm64` | `@knowledge-forge-ai/apgr-darwin-arm64` |
| `linux/amd64` | `manylinux_2_17_x86_64` | `@knowledge-forge-ai/apgr-linux-x64` |
| `linux/arm64` | `manylinux_2_17_aarch64` | `@knowledge-forge-ai/apgr-linux-arm64` |

While prebuilt runtime distribution targets include `darwin/arm64`, `linux/amd64`,
and `linux/arm64`, developer / CI qualification on Linux x86_64 remains pending:
the `policy` suite is pending runner qualification, and `unit`/`integration`/`combined`
suites are blocked by whole-inventory preflight binding Darwin arm64 Nix store digests.
macOS Apple Silicon (`darwin/arm64`) is fully qualified (APG114 / Exit `00159`).

Builds use Go 1.25, `CGO_ENABLED=0`, trimmed source paths, disabled VCS
stamping, and an empty controlled Go build ID. The distribution pipeline builds
each target twice in disjoint scratch roots and requires byte equality. It then
reuses those exact bytes in Python and npm artifacts rather than recompiling
inside either packager.

## Python distributions

APG builds exactly three non-pure `py3-none-<platform>` wheels. Each contains
the thin Python compatibility package, `VERSION`, canonical metadata, one
matching `bin/apgr`, its manifest, and the required license and notice files.
The wrapper verifies the manifest, version, host target, corpus, size, hash,
build information, direct-file type, and executable mode before launch. It
never downloads or searches `PATH` for an unrelated `apgr`.

The source distribution contains Go source, the canonical skills, the
thin Python source, the dependency-free build backend, packaging helpers,
the footprint subsystem, metadata, and licenses. Source distributions contain no
prebuilt executable. Building a wheel from an extracted source distribution
requires a supported host and a local Go 1.25 toolchain; the resulting
installed wheel does not require Go.
Unsupported build targets fail explicitly.

## npm distributions

The dependency-free CommonJS launcher package is
`@knowledge-forge-ai/apgr`. It declares same-version optional dependencies on
the three restricted platform packages. On each invocation it selects one
exact `process.platform` and `process.arch` mapping, checks launcher, package,
manifest, target, corpus, size, and binary hash identity, and spawns the caller's
exact argument vector with inherited standard streams and `shell: false`.

The packages have no install script, runtime download, semantic JavaScript
implementation, or third-party runtime dependency. Unsupported platforms fail
without a source-build or fallback package. Node 22 is the maintained runtime
baseline; qualification records the exact Node executable and version used.
The per-invocation full binary SHA-256 hash check provides complete fail-closed
tamper resistance at the deliberate cost of ~6.5 MB hashing latency on each
wrapper launch.

## Candidate manifest and qualification

`apg.distribution-manifest/v1` is the release-candidate checksum authority. It
records the version, corpus fingerprint, supported mappings, binary manifests,
three wheels, the source distribution, the launcher tarball, three platform
tarballs, and their exact sizes and SHA-256 values. It contains no private
development path or mutable publication identity.

Qualification is local and offline. It installs the host wheel in an isolated
virtual environment and the launcher plus host platform tarball in a disposable
npm project, then exercises the same packaged Go binary directly and through
both wrappers. Foreign artifacts receive structural, metadata, target, archive,
and checksum qualification without a false runtime-execution claim. Tampered,
missing, wrong-version, wrong-target, or wrong-corpus manifests and binaries
fail closed.

Source-checkout Python execution retains the existing explicit override,
package-bundled binary, then local source-build resolution order. The local
source build uses the current checkout's version and corpus and is removed after
the invocation. Installed wheels always use their bundled binary and never
require a runtime compiler or network access.

Once v0.10.0 is published, install Python with
`pip install agentic-praxis-grimoire==0.10.0`, npm with
`npm install -g @knowledge-forge-ai/apgr@0.10.0`, or the Go module with
`go get github.com/Knowledge-Forge-AI/agentic-praxis-grimoire@v0.10.0`.
