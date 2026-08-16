# APG84 v0.5 Public GitHub and PyPI Publication

## Candidate result

APG84 closes the APG83 publication-enforcement concern in the exact source
candidate. `bin/apg-build-python-release-bundle` builds a wheel and raw sdist
under `SOURCE_DATE_EPOCH=1700000000` in each of two disjoint roots, invokes the
maintained sdist normalizer for both builds, validates the wheel and normalized
sdist metadata, independently re-normalizes the selected sdist and requires
idempotent bytes, requires byte and mode equality, and atomically selects one
three-file publication directory. That directory contains only the exact wheel,
normalized sdist, and `SHA256SUMS`; raw sdists remain outside it.

The public `.github/workflows/release.yml` is JSON-compatible YAML and triggers
only when a GitHub Release is published. Its sole job uses the `pypi`
environment with only `contents: read` and `id-token: write`. It validates the
exact `v0.5.0` tag and three release-asset names, downloads assets by the
triggering release's asset IDs, verifies the exact checksum manifest, places
only the verified wheel and sdist in the PyPI input directory, and invokes the
official PyPA publish action at immutable commit
`dc37677b2e1c63e2034f94d8a5b11f265b73ba33` (release v1.14.2). It has no
checkout, rebuild, stored PyPI credential, manual trigger, or token fallback.
The tracked `release/v0.5.0-notes.md` owns the exact concise GitHub Release
body used by the operator after public Git ref readback.

## Publication boundary

GitHub administration, public source and tag publication, GitHub Release
creation, Trusted Publishing, PyPI readback, and public installation are
external gates. They cannot be self-attested by tracked source. The canonical
APG84 terminal Git-show report and numbered response record the actual outcome,
remote identities, artifact hashes, workflow run, and immutable readback after
those operations occur.

Before public mutation, APG84 requires the exact APG83 entry, absent public
v0.5 refs and release, absent or explicitly compatible PyPI project, green
qualification, reproducible Git and Python artifacts, and C0/H0/M0 final
review. Once public v0.5 Git or release state exists, it is append-only even if
PyPI publication remains blocked.

## Preserved product state

APG84 changes no skill content, profile semantics, maturity, routing, context
policy, or accepted debt. Development remains 33 canonical skills, 33 catalog
rows, and 33 projections; 14 stable and 19 provisional; 31 general routes, one
ChatGPT-local route, and 32 checked routes. Context remains 33 skills, 7,967
UTF-8 description bytes, 7,955 characters, and zero malformed entries. Node and
scratch debt remain zero; known debt remains exactly `CSS-QD-001` through
`CSS-QD-005` and `JS-QD-001` through `JS-QD-005`.

APG84 does not perform Nix deployment, create or modify
`agentic-praxis-grimoire-nd`, mutate real operator `~/.apgr`, migrate active
skills, push the private development remote, implement v0.6, or publish an
announcement.
