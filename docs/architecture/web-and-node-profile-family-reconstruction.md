# Web and Node Profile-Family Reconstruction

APG56 reconstructed the Web and Node candidate family from APG52 reproducible
evidence. APG57 independently reviewed and corrected it once, then
corrected-state review found material architecture and numerical-evidence
defects. [ADR
0034](../adr/2026/07/0034-web-and-node-profile-family-reconstruction-and-authoring-sequence.md)
is **Rejected**. Rejected [ADR
0031](../adr/2026/07/0031-web-and-node-profile-family-ownership-and-authoring-sequence.md)
remains unchanged. No skill was authored or integrated.

## Evidence lineage

```text
APG50 proposal -> APG51 rejection -> APG52 reproducible evidence
  -> APG56 fresh reconstruction -> APG57 corrected-state rejection
```

APG57 reverified the compact APG52 hashes, schema-bearing version-one files,
intentional schema-less rules file, byte-identical two-run result, and exact
pinned target objects. Both target trees remained read-only and unexecuted.

## Reviewed candidate evidence

APG56's proposal table mechanically contained six proposed eligible and four
deferred candidates, not the repeated five/five prose. APG57's attempted
corrected ledger then recorded zero eligible, eight deferred-evidence, and two
deferred-policy. Corrected-state review found that the ledger assigned the
single deferred JSX/TSX whole-file class in both TypeScript and JSX rows
without clearly separating TypeScript's non-additive semantic route. The
ledger is therefore review evidence, not accepted architecture.

Independent review still supports these future questions:

- JavaScript, TypeScript, and Node should be evaluated as separately selected
  language, compile-time, and runtime concerns.
- JSX, TSX, MDX, and Astro must not imply React; Markdown must not imply MDX.
- Embedded languages must be non-additive semantic routes.
- Browser/DOM runtime, generic HTML, and accessibility remain separate
  evidence gaps.
- Starlight, package managers, bundlers/Vite, lint/format, deployment,
  browser support, visual design, and content strategy remain project-owned.
- No edge may form a mandatory skill chain.

These statements preserve prior boundaries; ADR 0034 accepts no owner graph.

## Sources, versions, rights, and target evidence

| Owner | Version and consumer boundary | Rights boundary |
| --- | --- | --- |
| JavaScript | ECMA-262 ES2026 | document, embedded-software, and repository-source grants separate |
| TypeScript | 5.9.3 theme Astro-check consumer; native 7.0.2 website package-only | source/packages Apache-2.0; website/handbook CC BY 4.0 |
| Node | target engine floor `>=22.12.0`; CI Node 24 line | source/docs MIT; bundled notices separate |
| CSS | dated CSSWG/W3C module set | W3C Software and Document License |
| Markdown | CommonMark 0.31.2 plus GFM | specifications CC BY-SA 4.0; implementation terms separate |
| JSX | pinned canonical draft | README CC BY 4.0; no standalone license file |
| React | 19.2.8, configuration-only | source MIT; react.dev CC BY 4.0 |
| MDX | 3.1.1 | repository MIT; nested notices file-specific |
| Astro | both targets resolve 7.1.3; website declares `^7.0.2` | repository MIT; vendor terms separate |
| Vitest | absent from targets | repository MIT |

The theme's original baseline carries `LICENSE-MIT`; exact post-baseline
additions and modifications carry an AGPL-3.0 notice, package metadata says
AGPL-3.0-or-later, and commercial, NOTICE, and CLA surfaces remain separate.
The website grants no reuse license and is measurement-only.

At the pinned snapshots, CSS has twelve standalone stylesheets, Markdown has
seven documents, MDX has five documents, Astro has five behavioral
components, TypeScript has one verified theme diagnostic consumer, JavaScript
has one standalone module plus embedded expressions, and Node has one
44-line build script plus engine/toolchain facts. React is configuration-only
and Vitest is absent. These are evidence boundaries, not authoring approval.

## Growth-review result

APG57 reproduced the APG56 thresholds and found purpose, robustness, or metric
defects in every claimed class. JavaScript, TypeScript module, and Node fail
mapped monster-file controls. TypeScript declaration, CSS, and Astro show
tail or leave-one-family-out instability. Markdown and TypeScript
configuration physical-line metrics are unsuitable without separately frozen
structure. Scoped CSS, JSX/TSX, and MDX lack sufficient balanced evidence.
No replacement threshold was calculated.

Corrected-state review then rejected the APG57 evidence package itself:

- target samples can be labeled complete solely because sample-row count
  equals target count, while exact placement is unavailable;
- compact threshold intervals omit mandatory minimum/maximum bounds for
  interior thresholds;
- the executable reproduction gate does not compare the complete APG56 class
  projection; and
- focused tests miss those required branches.

The output remains publication-excluded failure evidence. It supports neither
an accepted nor amended band. TypeScript configuration option D remains a
reviewed future direction—project-owned structural growth with TypeScript
semantic ownership—but is not accepted by rejected ADR 0034.

## Counting, scenarios, and authoring boundary

Prior constraints still require at most one whole-file growth owner,
non-additive embedded routes, semantic risk independent of size, generated
and derived exclusions, and a legacy smallest-safe-fix or explicit exception
path. Rejected ADR 0034 creates no new policy.

The eighty APG56 scenarios remain continuous candidate-boundary evidence with
their numeric outcomes superseded. The five APG57 supplemental entries are
not accepted scenarios because they omit the established input, selection,
non-selection, project, semantic, growth, source, action, and rollback fields;
the broad-owner entry also names no owner.

There is no eligible authoring slice. W1–W4 remain deferred and W3 is not
authorized as a combined JavaScript/TypeScript/Node batch. React and Vitest
remain under ADR 0029 Policy A.

Development remains 28/28/28 with fourteen stable and fourteen provisional
skills. Corrected public and active v0.4.0 are unchanged. A future attempt
requires separately authorized evidence and architecture work; no successor
is authorized.
