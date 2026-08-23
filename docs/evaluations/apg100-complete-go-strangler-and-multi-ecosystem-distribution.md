# APG100 Complete Go Strangler and Multi-Ecosystem Distribution

## Terminal result

APG100 completes the portable-runtime strangler for the v0.7.0 release
candidate. `src/agentic_praxis_grimoire/VERSION` advances from `0.6.0` to
`0.7.0` and remains the only editable release-version authority. Release-like
Go builds inject that value; source-development builds retain the truthful
`devel` sentinel.

Go owns report, skill selection and materialization, environment snapshots and
resolution, hotspot analysis, and response capture. Python remains the
repository and host maintenance owner for policy checks, test orchestration,
public-release preparation, user/global skill installation, flattening, and
the legacy repository-local project projection adapter. JavaScript is only a
dependency-free process launcher.

## Response migration

The private `internal/response` owner preserves exact input bytes, the 8 MiB
limit, component validation, `001..999` allocation, private directories and
files, bounded advisory locking, reservations, same-directory temporary
writes, fsync durability, hard-link no-overwrite publication, orphan cleanup,
cancellation, concurrent allocation, and retention after post-publication
cleanup failure. The Go CLI exposes the `record` and `capture` compatibility
forms.

The Python response module retains compatible call shapes and read-only
inspection helpers, but every artifact-creating call delegates exact inputs to
Go. No Python response mutation fallback remains. The generalized bridge uses
an explicit development binary, a verified package binary, or a deterministic
source-checkout build; it never searches `PATH` for an unrelated executable or
downloads at runtime.

## Distribution architecture

The canonical `apg.binary-manifest/v1` record binds version, module, Go target,
Python and npm target mappings, binary name, byte size, SHA-256, corpus
fingerprint, build-info schema, deterministic build flags, and build identity.
The Python and npm wrappers require the canonical record and fail closed on a
missing, malformed, wrong-target, wrong-version, wrong-corpus, non-executable,
or tampered binary.

The deterministic build pipeline produces one `CGO_ENABLED=0` binary byte
sequence for each of `darwin/arm64`, `linux/amd64`, and `linux/arm64`. The same
target bytes feed one corresponding platform-specific Python wheel and npm
platform package. There is no v0.7 universal wheel and no installer download.

The Python front door preserves `apgr`, `python -m agentic_praxis_grimoire`,
the import-only version API, and retained maintenance routes. Its dependency-
free local PEP 517 backend creates the three platform wheels and one source
distribution. The sdist contains the Go module, canonical skill corpus, thin
Python source, local build backend, metadata, and licenses; a compatible Go
1.25 toolchain builds a standalone host wheel from an extracted fresh root.

The npm source creates `@knowledge-forge-ai/apgr` and the three same-version
platform packages. The CommonJS launcher requires Node 22 or newer, maps only
the supported OS/CPU pairs, validates the binary manifest and hash, and spawns
exact caller argv with inherited stdio and `shell: false`. It has no runtime
dependency, install script, semantic implementation, or download path.

## Public and historical boundaries

The v0.7 public-source projection includes the Go module, 39 canonical skills,
thin Python front door, deterministic Python/npm packaging source, distribution
helpers, schemas, documentation, and license material. It excludes private
evidence, build outputs, the old Python report oracle, and the old Python skill
consumer. The report oracle remains only in the private development tree for
qualified regression evidence.

`check skill-library` remains Python repository governance, measures the
repository metadata using its own accepted frontmatter grammar, and requires
Go `skills verify-corpus` to bind the embedded corpus. The historical v0.6
surface and publication manifest remain frozen and separately reconstructible.
The `apg-project-skills` adapter remains available only as legacy
repository-local symlink projection compatibility; Go `skills resolve` and
`skills materialize` are the portable authorities.

## Verification and disposition

Focused qualification covers response bytes, paths, allocation, locking,
concurrency, interruption and safety; Go unit, race and vet gates; bridge
delegation and tamper refusal; twice-reproducible target binaries, wheels,
sdist, npm archives and coordinated manifests; isolated offline host installs;
foreign-package structure; source-distribution rebuild; current public-source
projection; historical v0.6 reconstruction; and the unchanged skill, corpus,
report, environment, and hotspot contracts.

The operator accepted the exact reviewed and corrected closeout source after
the dispatcher stopped only on result-fence recognition. That operational
failure changed no source bytes or accepted product state. Exact development
identities and resulting-state command counts do not belong in durable public
documentation.
Publication, deployment, tag creation, README restructuring, JACA integration,
Nix changes, and APG101 work remain outside APG100.

Terminal disposition:
`V07_MULTI_ECOSYSTEM_DISTRIBUTION_READY_FOR_APG101`.

APG101 subsequently began under separate authorization.
