# APG71 — TypeScript Language-Profile Architecture

## Scope

APG71 exercised new human authority for an independent TypeScript
architecture phase after APG70 terminally rejected ADR 0040. It proposed
[ADR 0041](../adr/2026/08/0041-typescript-language-profile-architecture-and-compiler-generation-boundary.md)
(Proposed only), the
[TypeScript architecture](../architecture/typescript-language-profile-architecture.md),
and the
[lean contract](../specs/typescript-language-profile-lean-contract.md);
froze 22 semantic rows, 12 boundary rows, and 2 process invariants in
publication-excluded registers; authored no skill; changed no integration
owner; and left development `main` at exact APG70. APG70's
non-recommendation of APG71 remains controlling for JavaScript candidate
authoring; the new authority covers TypeScript architecture only.

## Sources and rights

TypeScript 7 (native, stable 7.0.2, released 2026-07-08 with no
programmatic API) and the TypeScript 6 legacy line (6.0 patch releases,
plus the `@typescript/typescript6` side-by-side package) were independently
verified as separate exact source generations: release tags, peeled
commits, trees, license blobs, npm versions, integrity values, and
package-to-source bindings were read from exact objects and recorded in the
single private identity record. Compiler repositories are Apache-2.0 with
byte-identical license blobs; documentation prose is CC-BY-4.0 with website
code MIT; targets keep their own terms. One exact gap is recorded:
`@typescript/typescript6` publishes no source-commit metadata, so claims
depending on that relation are blocked. The clean-room review identified no
copied or adapted compiler, baseline, test, diagnostic, documentation,
release-note, target, or rejected-JavaScript-architecture expression.

## Targets and corpus

Both read-only targets were reverified at their exact pinned objects and
fully inventoried: the website (17 tracked paths) resolves TypeScript 7.0.2
by npm peer auto-install with no direct compiler dependency; the theme
(76 tracked paths, resolving the historical 76-versus-77 count by exact
inventory) pins the legacy 5.9.3 line for `astro check`, the language
server, declaration-only emit, and `tsx` execution. Both targets resolve
the same Astro version yet resolve different effective compilers — the
decisive evidence that the project graph, not the framework, selects the
compiler.
APG52 corpus breadth stayed descriptive; the standalone JSX/TSX class
remains insufficient, and no percentile became policy.

## Architecture results

Source-authority disposition B (project-selected exact compiler baseline,
TypeScript 7 and 6 families separately pinned); a narrow static-semantics
owner with every §13 family classified fully-owned, partially-owned, or
routed; explicit non-owners for runtime, compiler operation, option
selection, module resolution, declarations, JSX, embedded hosts, Node,
browser, and policy; a first-class compiler-generation boundary whose
compatibility claims must name their scope; closed source-kind rules;
a 27-signal semantic-risk model with no numeric score; structural
disposition D (deferred, with the exact evidence gap and closure
conditions); and eligibility `authoring-eligible-with-narrowing` under
eight mandatory narrowings, granting no candidate-authoring authority.

## Verification

Docs-safe validation gates covered baseline identity, the APG70
four-record omnibus, branch parity, register schemas and IDs, closed
vocabularies, counts (29/29/29, 14/15, 27/1/28), links, privacy, rights,
change size, and whitespace, with mutation-negative demonstrations for the
mechanical checks. Thirty-three fresh non-author review lanes ran before
commit; two material evidence-attribution defects they found in the
lockfile-evidence narration were corrected pre-commit, with the corrected
facts strengthening the same conclusions. Two ordinary baseline
discrepancies were recorded: APG70's
terminal Git-show `STATUS-DOC` points at the public evaluation rather than
exit 00103 (bounded forward note only), and the ADR index carried a stale
`Proposed` marker for ADR 0040, corrected here to match APG70's terminal
rejection.

## Outcome

ADR 0041 Proposed; TypeScript architecture proposed on the Claude branch;
TypeScript skill absent; integration unchanged; Markdown retained
provisional; CSS absent; JavaScript has no current architecture or skill;
corrected public and active v0.4.0 unchanged. APG72 (Codex peer review,
exit 00105) is recommended in the private handoff and not begun. See the
[exit record](../status/2026/08/02/00104-apg71-typescript-language-profile-architecture-exit.md).

## APG72 forward disposition (2026-08-02)

Separately authorized APG72 preserved exact APG71, used its one correction,
and then rejected ADR 0041 after fresh non-author review found new material
defects. Eligibility is `not-applicable-rejected`; no current TypeScript
architecture input or skill exists, and APG73 is not recommended. This note
changes no APG71 object, branch, authorship, or historical proposal result.
