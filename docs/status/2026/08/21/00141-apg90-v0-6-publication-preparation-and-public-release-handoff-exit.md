# APG90 v0.6 Publication Preparation and Public Release Handoff Exit

Phase ID: `APG90`

## Status

**Tracked publication preparation complete; external public finalization
pending.**

This provider result advances tracked package and release-policy state to
v0.6.0 without staging, committing, tagging, pushing, publishing, deploying,
or mutating active APGR state. Dispatcher pre-final review, private-development
commit/push, and final archive remain dispatcher-owned lifecycle work.

## Result

1. APG89's later supervisory **ACCEPT** disposition is recorded forward as
   `READY_FOR_APG90` without rewriting APG89 history.
2. Historical v0.5.0 is a digest-pinned 33-skill/33-projection policy surface;
   v0.6.0 is the exact 39-skill/39-projection current surface.
3. The package, release workflow, release assets, notes, and release epoch are
   bound to v0.6.0 while historical v0.5.0 remains independently reconstructible.
4. The six v0.6 profiles remain provisional, context remains 9,504 bytes with
   23 bytes headroom, and selection remains explicit-only.
5. Read-only live evidence binds the expected public parent to v0.5.0 commit
   `c305ab633db652d4f9e14f68f9ad3cbcc068a49a`; no history rewrite is required.
6. The evaluation owns the exact same-phase external-publication sequence and
   stop conditions.

## Verification

Managed verification passed 3,358 unit cases and 633 integration cases with
two declared skips. The combined union covers 9,253/10,003 statements and
3,188/3,584 branches. Two disjoint source qualifications produced identical
wheel, normalized sdist, and checksum-manifest bytes; their exact hashes and
the isolated installed 0.6.0 context readback are recorded in the APG90
evaluation. Public GitHub and PyPI finalization are not part of this provider
work-stage result.

## Stop

Do not claim `V06_PUBLISHED_GITHUB_AND_PYPI`. The public release commit and
annotated tag, GitHub Release assets, Trusted Publishing outcome, published
PyPI package, and isolated published-package readback remain pending external
same-phase finalization. No APG91 or v0.7 successor is authorized.
