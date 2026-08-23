# APG98 Portable Environment Snapshots and Resolution

## Candidate result

APG98 implements accepted ADR 0051's portable environment slice as the public,
provider-neutral Go package `envsnap`. The package owns strict versioned
profiles, explicit-map capture, canonical JSON snapshots, deterministic
fingerprints, owner-only locked storage, verified loading, staleness, and
isolated or overlay resolution. It does not import APG internal packages and
does not read ambient process environment from its library API.

The five frozen public operations are `ValidateProfile`, `Capture`, `Store`,
`Load`, and `Resolve`. Profile and snapshot documents use
`apg.environment-profile/v1` and `apg.environment-snapshot/v1`. Defaults are
metadata only: neither capture nor resolution inserts them.

## Security and resolution result

The versioned `apg.environment-sensitive-name-policy/v1` policy refuses names
that identify secret or credential values. Its classifier is token-aware rather
than a naive substring test. `SSH_AUTH_SOCK` receives a narrow documented
capability-path disposition:
the socket path is not persisted credential material, while private-key,
password, secret, cookie, session-credential, API/access-key, and access/API/
auth-token value names remain refused. The lexical validator named `token` is
not itself a secret classification.

Capture treats absent and empty values as missing, validates included values,
records optional omissions, and never mutates the input map. Resolve requires
the matching profile and validates every snapshot and override entry. Isolated
mode is the default and contains only snapshot values followed by explicit
overrides. Overlay mode applies base, snapshot, then override, so the exact
precedence is override over snapshot over base. Consumer-owned base-only names
remain explicit provenance and are never persisted.

Errors and default CLI output identify metadata, names, sources, and bounded
failure classes without rendering environment values. Security tests seed
secret-looking values and check both direct values and derived fragments
against diagnostics.

## Storage and process result

Canonical snapshots live below an explicit storage root at
`environment/<profile-id>/current.json`. Direct owner-controlled directories
and files use 0700 and 0600. Profile inputs and stored snapshots are bounded,
direct regular, single-link, stable reads. Publication uses same-directory
private temporary files, file synchronization, atomic rename, and directory
synchronization where supported.

Each profile directory has an APG-owned interprocess lock with one invocation
token and owner record. Live, foreign, malformed, and ambiguous locks fail
closed; only a proven dead owner can be reclaimed, and only the acquiring
invocation removes its lock. Equivalent profile/content identity reuses the
existing snapshot without advancing the capture timestamp or changing file
content, inode, or modification time.

The Go CLI exposes `env profile-check`, `snapshot`, `show`, `resolve`, and
`run`. Its run adapter supplies an exact argument vector directly to a child
process without a shell. Normal Python `apgr env` routes delegate to that Go
family with one resolved APGR storage root and no Python semantic fallback.

## `.flakes` qualification and intentional differences

APG98 freshly binds the current read-only `.flakes` environment subsystem and
retains bounded fixtures for its twelve validators, shell snapshot behavior,
parser-safe environment runner, and Bash/Zsh prompt hook. Exact execution-time
source identities are recorded in publication-excluded APG98 evidence; the
publishable fixtures contain no operator values or private topology.

Parity is semantic rather than byte-for-byte. APG intentionally changes shell
text to strict JSON, ambient reads to explicit maps, implicit overlay to
default isolation, name-agnostic storage to sensitive-name refusal, content
hash metadata to profile/content fingerprints with age and provenance, and an
unlocked writer to an interprocess-locked no-churn store. No historical-value
archive or implicit default is introduced.

The thin-hook contract leaves `.flakes` in permanent ownership of host profile
contents, hook installation, and activation. A later independently authorized
cutover may call APGR immediately and per prompt with non-fatal behavior. Any
shell export view is a separate non-canonical adapter; APG98 does not keep
writing canonical shell files.

## Preserved boundaries

Version remains 0.6.0. Skills remain 39 canonical, 39 catalog rows, 39
projections, and 39 discoverable, with 14 stable / 25 provisional, zero
malformed, 9,504 description bytes, 9,492 characters, and the 9,527-byte
ceiling. APG96 reporting and APG97 context identities remain unchanged.

APG98 changes no `.flakes`, Nix, shell hook, live snapshot, JACA, hotspot,
response, package release, public release, deployment, APG99, or APG100 state.
Supported-target cross-builds are compilation evidence only and are not
foreign runtime qualification.

## Verification and disposition

Focused implementation evidence covers strict decoding, all validators,
capture, canonical JSON and fingerprints, store/load safety, locking,
concurrency, no-churn prompt-scale repetition, tampering, staleness,
resolution, sensitive-value non-leakage, CLI behavior, exact-argv process
launch, Python delegation, external Go consumption, `.flakes` parity fixtures,
and preserved APG96/APG97 behavior. Exact final command counts and the
prospective candidate tree belong to the dispatcher pre-final handoff.

Resulting-state verification ran all 213 Go tests normally and with the race
detector, plus `go vet ./...`. The dependency-independent Python unit owners
passed 3,349 tests and 1,217 subtests; dependency-independent integration
owners passed 615 tests and 203 subtests with two declared skips. The managed
combined Python gate stops at its preflight because no external exact
`typescript@7.0.2` compiler is bound; no compiler was installed or substituted.
All three supported Go targets cross-compiled with version 0.6.0 and the
unchanged embedded skill-corpus fingerprint.

Candidate terminal disposition:
`V07_ENVIRONMENT_SNAPSHOTS_READY_FOR_APG99`.

APG99 remains separately authorized.
