# APG66D Repository-Import Cache Entry Presence

Date: 2026-08-01

## Result

Complete — APG66C remains accepted while the test-only repository-import
state helper now distinguishes exact mapping-key presence from exact stored-
object identity for `None` sentinels and every relevant module entry.

## Accepted baseline

APG66C remains accepted at commit
`437f101a2b61f312663848c2fdd4a3ab01061cce`, tree
`eda676ee6e545b9e1baa866a7083c0f0f0b1ed41`, with sole parent exact APG66B
`db847b287321a087c7413b16c989c15e07a3b167`. Its preserved blocked Git-diff,
blocked operational, final Git-show, and final operational record IDs are:

- `GIT-DIFF-REPORT-360e91ce42620af49e29699443780f548aef22542f4aea28769ebb2f7344566d`;
- `OPERATIONAL-REPORT-0800e81597909e009b5ba4eb97b06c75dbc0158b000ebf9b1480f7f0ce6d928e`;
- `GIT-SHOW-REPORT-437f101a2b61f312663848c2fdd4a3ab01061cce`; and
- `OPERATIONAL-REPORT-102e5ffc3e695002c35809521d6b50f78fc76856e750566ddf6969779fbc0eaf`.

Fresh parsing found exactly those four complete records in order. Local and
fetched `main` and APG66C refs were equal before implementation.
APG66C's result remains
`complete-markdown-clause-polarity-predicate-binding` and its delivered final
gate remains `retained-provisional-main-fast-forwarded-remote-equality`.

## Failing-first result and behavioral distinction

Against exact APG66C, a synthetic uniquely named relevant entry was present in
`sys.modules` with value `None`, captured, and then deleted. The former helper
called `sys.modules.get(name)`; both the missing lookup and the recorded value
were `None`, so the restoration assertion passed incorrectly. The focused
regression test failed because the required `RepositoryImportCacheError` was
not raised.

This is behaviorally material in Python's import cache. A present entry whose
value is `None` halts import with `ModuleNotFoundError`; deleting the key lets
normal import search proceed. A disposable standard-library-only control
demonstrates both outcomes and restores the module entry, search path, and
relevant importer-cache key exactly.

## Correction and bounded audit

For every pre-existing relevant module entry, the helper now requires the key
to remain present and then requires the stored value to be the identical
object. It does not compare equality and does not special-case `None`.

The bounded owner-family audit classified the former restoration
`sys.modules.get()` as defective. The later `before_modules.get()` is safe for
its narrower repository-origin residue check because that branch is reached
only for a current object with a root-bound module path; it does not infer
entry presence from a `None` result. Test-owner lookups use a private missing
sentinel, and the production import owner contains no analogous lookup.
Production repository-import bytes are unchanged.

The existing importer-cache tuple contract already compares exact relevant
key count, ordered keys, and stored-object identity. Added controls confirm
that a present relevant `None` value passes, removal or replacement fails, and
an absent relevant key acquiring `None` fails. No symmetry rewrite was made.

## Sentinel and isolation evidence

The thirty-control matrix covers exact module, package, submodule, and `None`
preservation; removal and every object/`None` replacement direction; absent-
name insertion; coordinated deletion and introduction; importer removal,
replacement, and absent-to-`None`; unrelated names; physical-prefix and same-
suffix near misses; parent/child independence; equal-but-distinct objects; and
coexisting present-`None` and absent local names. Every negative fails for its
named reason.

The cache owner passes alone and twice. Cache-before-import and import-before-
cache each pass, as do both cache/import-to-Markdown orders and configured
eight-worker xdist. APG66C repository residue, exception residue, replacement,
path, importer, cross-root, standard-library shadow, package, submodule,
namespace, prefix, and unrelated-module controls remain green.

## Preserved Markdown, integration, and release state

The unchanged complete Markdown owner set passes 1,386 unit cases and 1,391
with integration. APG66C P1 through P5 remain 17 source rows, 11 signal
instances across 7 rows, and 18 targeted guards, with complete 34-row prose
semantics still owned by APG66 human review.

The Markdown leaf, specification, coverage, register, fixture, and ADR bytes
are unchanged. ADR 0037 and ADR 0038 remain Accepted with amendment.
`markdown-language-profile` remains retained provisional at 29 canonical
skills, 29 catalog rows, and 29 projections; maturity remains 14 stable / 15
provisional; routes remain 27 general / 1 ChatGPT-local / 28 checked. CSS
remains absent and ADRs 0031, 0034, 0035, and 0036 remain Rejected.

The current-development release owns the APG66D public records. Historical
corrected v0.4 excludes them and the APG66C current-only helper/test owners.
Corrected public and active v0.4.0 remain unchanged. Targets remain read-only,
unchanged, and unexecuted.

## Verification and boundary

Pinned Python 3.13.12, pytest 9.1.1, pytest-cov 7.1.0, coverage.py 7.15.2,
and pytest-xdist 3.8.0 run the focused and complete gates. Unit passes 2,646
tests at 6,314/7,294 statements and 2,149/2,686 branches. Integration passes
563 tests with two expected skips at 6,422/7,294 statements and 2,150/2,686
branches. The combined union reaches 6,824/7,294 statements and 2,417/2,686
branches. Configured Bats 1.12.0 passes 23/23. Lifecycle, release, identity,
link, JSON, privacy, rights, structure, and delivery results are retained in
the associated phase evidence.

APG67 JavaScript architecture is recommended at exit 00100 but not begun. No
JavaScript, TypeScript, Node.js, JSX, MDX, Astro, React, Vitest, readiness,
publication, deployment, APG67, or successor work is authorized by APG66D.
