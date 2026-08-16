# APG52 Reproducible Web and Node Evidence Foundation

## Scope and outcome

APG52 repairs the evidence defect that forced rejection of the prior Web and
Node architecture decision. It does not make a replacement architecture
decision, accept a threshold, approve a profile, or begin authoring.

The result is **Complete**. Exact publication-excluded tooling and manifests
produce byte-identical evidence from two disjoint acquisitions. Nine
whole-file artifact classes have reproducible sufficient evidence. Standalone
JSX/TSX remains insufficient by source-family count, and scoped CSS remains
insufficient because APG52 selected no section artifacts. Those limitations
are explicit and unpadded.

ADR 0031 remains Rejected. ADR 0032 is not created. All ten Web and Node
candidates remain deferred, no authoring slice is eligible, and React and
Vitest retain Policy A.

## Reproduced defect

A new reviewer using only committed APG51 evidence could recover most source
family names and some abbreviated object prefixes, but not a complete
repository, commit, tree, artifact, exclusion, sample, or quantile contract.
The thirty-document Markdown sample could not be reconstructed, and no
published band could be regenerated from exact inputs. The overall APG51
corpus package is therefore not reproducible.

APG52 resolved every abbreviated source identity named in that evidence to a
full commit and tree without silent substitution. Recovery did not imply
selection. The new corpus was selected separately before accepted measurement.
The canonical JSX README control was independently rechecked and confirms its
inline CC BY 4.0 grant.

## Evidence implementation

The publication-excluded Python 3.10+ implementation uses only the standard
library. It validates closed manifests, inventories exact Git trees, reads
blobs only through exact object operations, records every included and
excluded path, measures the complete eligible universe, summarizes exact
distributions, selects a deterministic review sample, compares the unchanged
APG51 hypotheses, and verifies canonical output.

The implementation:

- uses fixed Git argument arrays and never `shell=True`;
- never reads corpus bytes from mutable worktree paths;
- validates full commits, trees, object formats, blob identities, byte
  lengths, SHA-256 values, and rights evidence;
- runs no source-provided command and writes to no source repository;
- requires no network during measurement, summary, comparison, or
  verification;
- emits sorted canonical JSON/JSONL without local paths, timestamps,
  durations, or cache identities; and
- returns 0 for success, 1 for evidence mismatch, and 2 for invocation or
  manifest error.

UTF-8 BOM handling, universal newline normalization, Unicode blank-only
classification, comment counting, final unterminated lines, section bounds,
and non-additive section behavior are exact contracts. Quantiles use
Hyndman-Fan type 7 with exact decimal interpolation and three-place
half-even rendering.

## Corpus result

The accepted complete universe contains 4,612 artifacts and 4,365 explicit
exclusions across ten exact sources.

| Artifact class | Artifacts | Source families | Target artifacts | Evidence status |
| --- | ---: | ---: | ---: | --- |
| JavaScript module | 1,892 | 6 | 1 | reproducible-sufficient |
| TypeScript module | 1,712 | 7 | 4 | reproducible-sufficient |
| Handwritten TypeScript declaration | 97 | 8 | 1 | reproducible-sufficient |
| TypeScript configuration | 103 | 7 | 3 | reproducible-sufficient |
| Node runtime or CLI | 318 | 4 | 1 | reproducible-sufficient |
| CSS stylesheet | 117 | 7 | 12 | reproducible-sufficient |
| CSS component or scoped section | 0 | 0 | 0 | insufficient-source-family-count |
| Markdown document | 263 | 10 | 7 | reproducible-sufficient |
| JSX/TSX standalone module | 17 | 2 | 0 | insufficient-source-family-count |
| MDX document | 47 | 5 | 5 | reproducible-sufficient |
| Astro component, page, or layout | 46 | 3 | 5 | reproducible-sufficient |

The two insufficient rows are evidence limitations, not candidate
dispositions. Artifact-weighted distributions are also materially imbalanced
for several classes, so per-source-family distributions are retained
separately and no mega-repository silently establishes policy.

## APG51 hypothesis comparison

The original derivation rule was not recovered for any APG51 band. The nine
sufficient-corpus rows are therefore conservatively labeled
`original-rule-not-recoverable`, rather than claiming consistency merely from
corpus sufficiency. Scoped CSS and standalone JSX/TSX are
`insufficient-evidence`. Each row separately records exact band percentages,
P90/P95/P99 threshold relationships, source-family imbalance, size outliers by
source family, and target placement.

The target stylesheet previously highlighted at 995 nonblank lines remains in
the APG51 Orange hypothesis interval. The target Astro component previously
highlighted at 137 remains below Yellow. These placements do not accept either
band or reduce semantic risk to size.

No APG51 value was altered to obtain a favorable result. No threshold,
authoring slice, maturity state, route, or candidate is accepted.

## Rights and consumer controls

The exact rights ledger keeps source code, specification, documentation,
README grants, and package-metadata absence controls distinct. It records the
separate ECMA-262 document and embedded-software terms; TypeScript source and
website terms; Node, CSSWG, CommonMark, and GFM terms; the JSX inline grant;
React source and react.dev documentation; and MDX, Astro, Starlight, and
Vitest terms. Approximate labels such as “public,” “MIT-adjacent,” and
“CC/MIT” are not used. APG52 performs factual measurement only and copies no
external expression into APG guidance.
Every one of the 21 ledger rows has a reproduced Git commit, tree, path, and
blob chain. The ECMA edition response hash remains separately identified as
historical rechecked web evidence, not an offline-regenerated response.

The TypeScript consumer result is unchanged. The website contains the selected
7.0.2 package and executable but no tracked project-script, Astro-check,
ordinary-build, or MDX consumer; editor/compiler-service use remains
inconclusive. The theme directly and transitively selects 5.9.3, and its
tracked lint command reaches Astro check as an effective diagnostic consumer.
No full target build was run.

## Reproducibility and validation

Two disjoint acquisition roots and two disjoint output roots used the same
committed manifests, exact Git objects, and Python/Git toolchain. Source
validation, membership, exclusions, measurements, sample, statistics,
source-family summary, band comparison, rights-object validation, and rights
JSON were byte-identical.

Fifty-three focused unit and real-Git integration tests cover manifest refusal, exact
objects, worktree isolation, encoding and newline cases, sections,
classification, exclusions, quantiles, bands, rights, symlinks, submodules,
binary data, mutation failures, and two-root identity. Python compilation and
the required APG mechanical, Markdown, link, privacy, JSON/JSONL, identity,
and diff checks pass. Complete, readiness, smoke, release, publication, and
deployment suites were not run because APG52 does not authorize them.

## Disposition and stop

APG52 changes no skill surface or release surface. Development remains
28/28/28 with fourteen stable and fourteen provisional skills, 26 general
routes, one ChatGPT-local route, and 27 checked edges. Corrected public and
active v0.4.0 remain unchanged. Both target repositories remain read-only and
unexecuted.

All ten Web and Node candidates remain deferred:

```text
javascript-language-profile
typescript-language-profile
nodejs-runtime-profile
css-language-profile
markdown-language-profile
jsx-language-profile
react-component-profile
mdx-profile
astro-profile
vitest-test-profile
```

No successor follows automatically. A new architecture decision, any profile
authoring, scoped-CSS section corpus, broader JSX corpus, browser/HTML/
accessibility work, or release action requires separate maintainer authority.

## Subsequent storage note

APG53 later verified the accepted hashes, counts, and complete two-run result,
then removed `corpus-artifacts.jsonl`, `corpus-exclusions.jsonl`, and
`corpus-measurements.jsonl` from the current tree as complete regenerable bulk
outputs. Exact inputs, compact evidence, hashes, summaries, tooling, and
reproduction records remain. Complete regeneration now requires an explicit
untracked output root outside the repository. This forward storage correction
does not change any APG52 conclusion or remove its historical Git objects.
