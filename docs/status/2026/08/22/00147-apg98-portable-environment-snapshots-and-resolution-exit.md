# APG98 Portable Environment Snapshots and Resolution Exit

Phase ID: `APG98`

## Status

**Complete candidate — portable environment snapshots ready for
dispatcher-owned pre-final inspection and publication disposition.**

Candidate terminal disposition:
`V07_ENVIRONMENT_SNAPSHOTS_READY_FOR_APG99`.

Dispatcher-owned staging, commit, push, and final acceptance remain outside
provider work.

## Outcome

APG98 adds the provider-neutral public Go `envsnap` package with strict v1
profiles and snapshots, explicit-map capture, deterministic identities,
owner-only locked and no-churn storage, verified load and staleness, and exact
isolated/overlay resolution. The CLI provides profile-check, snapshot, show,
resolve, and exact-argv run adapters; Python delegates the `env` family to Go
without reimplementing semantics.

The sensitive-name policy fails closed for credential material across profiles,
snapshots, and overrides; non-profile ambient base entries in Overlay mode pass
through as consumer-owned base state with `base` provenance. Diagnostics
are value-safe. `SSH_AUTH_SOCK` is deliberately classified as an access-
capability path rather than secret bytes. Resolution always receives the
matching profile, and explicit override beats snapshot, which beats base only
in explicit Overlay mode. Isolated mode remains the default.

## Qualification

- All twelve validators are bound to bounded current `.flakes` source
  semantics where APG did not intentionally change architecture.
- Canonical JSON identities are stable across timestamps and storage paths.
- Equivalent prompt-scale stores preserve the original timestamp, inode,
  modification time, and bytes; changed content publishes once.
- Live, stale, malformed, foreign, concurrent, and cancelled lock/store paths
  have bounded ownership and cleanup evidence.
- Load rejects unsafe files, tampering, profile mismatch, and caller-declared
  stale age.
- A disposable external Go module consumes profile, capture, store/load,
  resolve, and provenance entirely in process.
- CLI output is values-safe by default and `env run` uses exact argv without a
  shell.
- The thin-hook contract is documented but not activated.

## Preserved state

- Version remains 0.6.0.
- Skills remain 39/39/39/39 and 14 stable / 25 provisional.
- Discovery remains zero malformed, 9,504 description bytes, 9,492 characters,
  and the unchanged 9,527-byte ceiling.
- APG96 report and APG97 skill-context behavior remain intact.
- No `.flakes`, live snapshot, shell hook, host environment, JACA, Nix,
  hotspot, response, package-release, publication, or successor state changes.

## Next authorization

APG99 may implement the structural-hotspot contract only under a separate
dispatcher assignment. This exit does not begin APG99 or APG100.
