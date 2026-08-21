# APG90 v0.6 Publication Preparation and Public Release Handoff

## Phase disposition

APG90 advances the tracked package and release policy to v0.6.0 and prepares a
same-phase external-publication handoff. Provider work does not stage, commit,
tag, push, publish, deploy, or mutate active APGR state. Until immutable public
GitHub and PyPI readback exists, the only valid disposition is **tracked
publication preparation complete; external public finalization pending**.

## APG89 authority

The external supervisory review bound APG89 private-development commit
`6c3f21be262265944b12cb1f2781591773916660` and tree
`4520877d455b9040fee222769d1636def2bc7ad0`. It returned **ACCEPT** with
C0/H0/M0/L0 technical findings and terminalized APG89 as `READY_FOR_APG90`.
APG90 records that result forward without changing APG89 history and without
equating its private-development push with public release publication.

## Version and policy transition

`src/agentic_praxis_grimoire/VERSION` is the canonical 0.6.0 package version.
The release workflow binds published tag `v0.6.0`, exact wheel
`agentic_praxis_grimoire-0.6.0-py3-none-any.whl`, exact normalized sdist
`agentic_praxis_grimoire-0.6.0.tar.gz`, and `SHA256SUMS` before the unchanged
immutable PyPA Trusted Publishing action.

The release-audit owner now exposes two independent surfaces:

- historical v0.5.0 is digest-pinned at
  `9f20ad43ffd4f4eeb72fe4cfe4aeb1cbe6449e5993bc641563f36a99a378bbef`,
  retains 33 skills and 33 projections, and rejects all APG86-APG90 owners;
- current v0.6.0 retains exactly 39 skills and 39 projections and includes the
  APG86-APG90 release-critical records.

Historical v0.4.0 and earlier policy paths are unchanged. The former mixed
`V05_ONLY_*` name is replaced by the truthful `POST_V04_*` boundary.

## Release epoch

Historical v0.5.0 keeps release epoch `1700000000`. v0.6.0 freezes
`1787270400` (2026-08-21 00:00:00 UTC). The normalizer accepts only those two
named values and requires matching `SOURCE_DATE_EPOCH`; the v0.6 bundle owner
selects only the latter. No historical epoch is silently reinterpreted.

## Live historical release readback

Read-only live checks on 2026-08-21 establish:

- public repository: `Knowledge-Forge-AI/agentic-praxis-grimoire`;
- public `main` and annotated `v0.5.0` both resolve to commit
  `c305ab633db652d4f9e14f68f9ad3cbcc068a49a`;
- the v0.5.0 tree is `9c01a1b4345b65ae23d4a9efc9734500c11d2451`;
- its sole parent is public v0.4.0 commit
  `d23a09477a2da8e4ea2214910a5a0de6e9be24b5`;
- annotated tag object `6365a6d7a22e32a8ed74434ce96bc7ade9c62f6b`
  points to the v0.5.0 commit;
- the published non-draft, non-prerelease GitHub Release has exactly the wheel,
  sdist, and `SHA256SUMS` assets; and
- PyPI v0.5.0 reports wheel SHA-256
  `e3cfa7cc1fe90d644e831a58b43419daa5d62a256f0910f0067425b1f86acf5d`
  and sdist SHA-256
  `1f8a80359e7af6a86a883a1f4182304d3d065077e96f9c81ca6b9a26e9c10134`,
  matching the GitHub assets.

Live v0.1.0 through v0.4.0 tag identities remain present. No force push or
history rewrite is needed: v0.6.0 is a normal forward release whose sole public
parent must be the live v0.5.0 commit above. Reprojecting the repository-owned
exact APG84 source while excluding only `private/` produces tree
`9c01a1b4345b65ae23d4a9efc9734500c11d2451`, byte-identical to the live public
v0.5.0 tree. The v0.6 policy therefore does not reinterpret its historical
surface.

## v0.6 release surface

The release keeps all six new profiles provisional: GoMock, Vitest, JSX,
React, MDX, and Astro. The complete library remains 39 canonical skills, 39
catalog rows, 39 exact projections, 39 discoverable, zero malformed, 14 stable
and 25 provisional. Descriptions remain 9,504 UTF-8 bytes and 9,492 characters,
leaving 23 bytes under the 9,527-byte ceiling. Project-selected projection is
explicit-only; there is no seventh profile, mandatory chain, or aggregate
owner.

## Qualified Python bundle

Two disjoint clean source roots were qualified under CPython 3.13.12,
`build` 1.3.0, setuptools 83.0.0, and zlib 1.3.2. Each source root completed
the maintained two-build normalization path. All four builds produced the same
bytes and modes. The selected release directory contains only:

- `agentic_praxis_grimoire-0.6.0-py3-none-any.whl` — SHA-256
  `923c56592d6f9b69ef024e8a52ca3857149f427787c39e230c9947b540044f30`;
- `agentic_praxis_grimoire-0.6.0.tar.gz` — SHA-256
  `2f64fbf329b99e4f294d5cfd0a350069afda705879f13f813f35b74374960a11`;
- `SHA256SUMS` — SHA-256
  `093641038997df99e6a9eec12dddc3f10ab5d603bd68e19e9961551af4c8d17e`.

An isolated wheel install outside the checkout reports `apgr 0.6.0`, 39
skills, 39 discoverable, 9,504 description bytes, 9,492 description
characters, and an empty malformed list.

## Verification

The corrected APG90 state passed:

- managed unit: 3,358 passed; statements 8,641/10,003; branches 2,869/3,584;
- managed integration: 633 passed and two declared skips; statements
  8,707/10,003; branches 2,875/3,584;
- combined union: statements 9,253/10,003; branches 3,188/3,584;
- exact v0.5-to-v0.6 lineage replay, including six lineage subtests;
- skill-library topology at 39/39/39 and record identity at 50 ADRs, 141
  exits, and 141 phase IDs;
- release workflow, historical/current public policy, Python distribution,
  normalization, installed resource/context, confidentiality, licensing, and
  Markdown-link checks exercised by the configured release suites;
- byte equality across the two independent qualified bundles; and
- `git diff --check` plus worktree size-policy inspection. The largest changed
  blob is 138,261 bytes under the 262,144-byte ordinary limit, and the longest
  changed line is 38,564 bytes under the 65,536-byte one-line limit.

The repository's change-size command is deliberately Git-object based. Its
dispatcher-owned staged/commit invocation remains a closeout check because the
provider may not stage or create Git objects.

## Exact same-phase external-publication handoff

The external operator must stop unless every identity and artifact below
matches the final APG90 closeout evidence:

1. Repository is `Knowledge-Forge-AI/agentic-praxis-grimoire`; live public
   `main` and peeled `v0.5.0` remain
   `c305ab633db652d4f9e14f68f9ad3cbcc068a49a`.
2. Construct one public commit with sole parent that v0.5.0 commit, the exact
   qualified APG90 public tree, and subject `Release v0.6.0`.
3. Create annotated tag `v0.6.0` pointing to that exact release commit. Do not
   rewrite, retarget, or delete any earlier tag or commit.
4. Publish a GitHub Release titled `v0.6.0`, tag `v0.6.0`, `draft=false`, and
   `prerelease=false`, with exactly the qualified wheel, normalized sdist, and
   `SHA256SUMS`.
5. Require all asset SHA-256 values to match the qualified bundle before the
   release event reaches the fail-closed Trusted Publishing workflow.
6. Stop on lineage, tree, tag, asset-count, filename, checksum, workflow,
   package, or historical-ref drift. Do not force push or substitute an
   unlocked/rebuilt artifact.
7. After Trusted Publishing succeeds, require PyPI 0.6.0 hashes to match,
   install from published PyPI in isolation, and reprove version 0.6.0 plus the
   exact 39-skill context. Recheck intact public/PyPI v0.5.0 state.

The three artifact hashes above are final. Because the provider may not create
Git objects, the exact public tree and release commit are frozen by dispatcher
closeout from the reviewed APG90 tracked bytes before this handoff can be
executed. Any later byte change invalidates the prepared bundle and tree.

## Explicit exclusions

APG90 performs no Nix adapter work, active global/project skill migration,
active user `.apgr` mutation, new profile, advisory discovery, v0.7 work, or
unrelated refactor. It does not claim `V06_PUBLISHED_GITHUB_AND_PYPI` while
external publication remains pending.
