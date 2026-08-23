# APG93 v0.6 Public GitHub and PyPI Publication Exit

Phase ID: `APG93`

## Status

**Complete — v0.6.0 published to GitHub and PyPI and verified by live readback.**

Terminal disposition: `V06_PUBLISHED_GITHUB_AND_PYPI`.

## Result

1. The pre-final review accepted the hardened publication packet, and operator
   execution published public release v0.6.0.
2. Public `main` is release commit `d37727d5c928f542cbee89b1be1979d4046c4d65`,
   with sole parent historical public v0.5.0 commit
   `c305ab633db652d4f9e14f68f9ad3cbcc068a49a` and exact APG90 public tree
   `ecc2fc000389a66952ec239225e7e870b03298a5`.
3. Annotated tag `v0.6.0` (object `eedcacf685bea32612f534e174bc5c12592c56a0`)
   peels to the v0.6.0 release commit.
4. GitHub Release `v0.6.0` is published (non-draft, non-prerelease) with exactly
   the three frozen APG90 release assets (`SHA256SUMS`, wheel, and sdist).
5. GitHub Actions Trusted Publishing succeeded via the fail-closed release
   workflow.
6. PyPI distribution `agentic-praxis-grimoire` 0.6.0 reports exact wheel and
   sdist hashes matching APG90.
7. Isolated installation of `agentic-praxis-grimoire 0.6.0` reports version 0.6.0,
   exactly 39 skills, 39 discoverable, zero malformed, 9,504 description bytes,
   9,492 characters, and 23 bytes headroom below the context budget ceiling.
8. Historical public v0.1.0 through v0.5.0 tags and releases remain intact and
   unmodified.

## Verification

Live GitHub API, PyPI JSON API, and isolated package installation readback
confirmed all release artifacts, hashes, metadata, and skill context. The
operator packet unit suite passed 18/18 tests under the pinned Python
environment. Packet `--check-packet` verified `already_terminal_exact`. Record
identity checks passed across all ADRs, exits, and phase IDs.

## Next authorization

v0.6 publication is complete. No Nix adapter deployment, active APGR projection
mutation, or v0.7 work occurred. Next work requires separate human authorization.
