# APG93 v0.6 Public GitHub and PyPI Publication

## Phase disposition

Claim exactly: `V06_PUBLISHED_GITHUB_AND_PYPI`.

Public release v0.6.0 is published, verified, and terminal on both GitHub and
PyPI. Dispatcher pre-final review accepted the candidate packet, the operator
executed `finalize-public-release.sh --execute` under authorized operator
authority, and this resumed APG93 closeout independently verified live immutable
readback across GitHub, PyPI, and isolated installation.

## APG91-APG93 lineage and authority reconciliation

- **APG90** prepared tracked v0.6 release artifacts, qualified the exact
  reproducible Python bundle, froze release epoch `1787270400`, and established
  the same-phase operator handoff contract.
- **APG91** attempted external execution but encountered environment qualification
  defects (specifically, runner JS/TS/Node qualification bindings).
- **APG92** diagnosed the failure as Category A packet/harness environment
  issues (the APG90 release content remained exact and unmutated), pinned the
  validation Python environment, hardened the private operator packet, passed
  non-mutating candidate validation in 1,217s, passed 18 unit tests, corrected
  draft release readback and workflow timestamp handling, and committed/pushed
  the hardened packet.
- **APG93** served as the narrow external-publication authority boundary and
  terminal readback phase. It intentionally consumed the reviewed APG92-identified
  operator packet and outbox artifacts to preserve byte hash chains and frozen
  qualification. Following pre-final review acceptance and operator execution,
  APG93 performs terminal readback and authors post-publication private development
  records.

## Immutable public readback

Live verification on 2026-08-21 confirms:

1. **Public repository:** `Knowledge-Forge-AI/agentic-praxis-grimoire`.
2. **Release commit:** `d37727d5c928f542cbee89b1be1979d4046c4d65`.
   - Sole parent is historical public v0.5.0 commit
     `c305ab633db652d4f9e14f68f9ad3cbcc068a49a`.
   - Tree is `ecc2fc000389a66952ec239225e7e870b03298a5` (exact APG90 public tree).
   - Subject is `Release v0.6.0`.
3. **Annotated tag:** `v0.6.0` (tag object `eedcacf685bea32612f534e174bc5c12592c56a0`),
   peeling directly to `d37727d5c928f542cbee89b1be1979d4046c4d65`.
4. **GitHub Release:** Release ID `374665935`, published at `2026-08-21T20:43:28Z`,
   state `published`, `draft=false`, `prerelease=false`, URL
   `https://github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/releases/tag/v0.6.0`.
5. **Release assets:** Exactly three assets matching APG90 frozen hashes:
   - `SHA256SUMS` (ID 524234462, 216 bytes):
     `093641038997df99e6a9eec12dddc3f10ab5d603bd68e19e9961551af4c8d17e`
   - `agentic_praxis_grimoire-0.6.0-py3-none-any.whl` (ID 524234460, 65,360 bytes):
     `923c56592d6f9b69ef024e8a52ca3857149f427787c39e230c9947b540044f30`
   - `agentic_praxis_grimoire-0.6.0.tar.gz` (ID 524234461, 101,815 bytes):
     `2f64fbf329b99e4f294d5cfd0a350069afda705879f13f813f35b74374960a11`
6. **Trusted Publishing:** GitHub Actions workflow run `32525015498`, job
   `96905102968` (`publish`), status `completed`, conclusion `success`.
7. **PyPI distribution:** `agentic-praxis-grimoire 0.6.0` on PyPI reporting:
   - `agentic_praxis_grimoire-0.6.0-py3-none-any.whl`:
     `923c56592d6f9b69ef024e8a52ca3857149f427787c39e230c9947b540044f30`
   - `agentic_praxis_grimoire-0.6.0.tar.gz`:
     `2f64fbf329b99e4f294d5cfd0a350069afda705879f13f813f35b74374960a11`
8. **Installed package readback:** Isolated wheel installation outside the
   checkout reports:
   - Version: `0.6.0`
   - Skills: 39 total, 39 discoverable, 0 malformed
   - Description size: 9,504 UTF-8 bytes, 9,492 characters (23 bytes headroom)
   - Context report SHA-256:
     `075a8e8fb0625a2e5bf9165a027761241d3d86e267858f73fbc8c926945a1dab`
9. **Historical releases:** Public v0.1.0 through v0.5.0 tags, commits, and
   assets remain completely intact and unmodified.

## Exclusions and preserved state

APG93 made no changes to APG90 release content. No Nix adapter deployment,
active APGR projection mutation, global profile installation, or v0.7 work
occurred. Deployment remains a future separately authorized phase.
