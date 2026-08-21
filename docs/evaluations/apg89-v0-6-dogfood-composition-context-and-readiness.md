# APG89 v0.6 Dogfood, Composition, Context, and Readiness

## Candidate disposition

APG89 evaluates the complete committed 39-skill development tree after APG88.
The candidate remained at version `0.5.0`; public and active v0.5.0 were
unchanged. The implementation/testing candidate satisfied the bounded APG89
readiness gate. A later external supervisory review accepted the exact APG89
candidate with C0/H0/M0/L0 technical findings and terminalized its current
state as `READY_FOR_APG90`. The historical APG89 commit remains unchanged.

## Supervisory review disposition

The external supervisory review bound the already-pushed private-development
APG89 commit `6c3f21be262265944b12cb1f2781591773916660` and tree
`4520877d455b9040fee222769d1636def2bc7ad0`. Its verdict was **ACCEPT** with
zero Critical, High, Medium, or Low technical findings. This later disposition
is recorded forward for APG90; it does not rewrite APG89 implementation or
turn the private-development push into public v0.6 publication.

## Baseline readback

The clean committed APG88 baseline passed 3,342 unit tests with statement
coverage 8,609/9,973 and branch coverage 2,862/3,574. All 630 integration
behavioral tests passed with two skips, but the first integration observation
failed the branch threshold at 2,858/3,574. The combined run passed with unit
8,609/2,862, integration 8,675/2,862, and union 9,222/3,174 statement/branch
numerators over the corresponding 9,973/3,574 denominators.

The same baseline reported 39 canonical skills, 39 catalog rows, 39 exact
relative projections, 14 stable and 25 provisional rows, 39 discoverable
entries, zero malformed metadata, 9,504 description bytes, and 9,492
characters. This is 23 bytes beneath the 9,527 ceiling. The six-profile set is
exactly Astro, GoMock, JSX, MDX, React, and Vitest; no seventh profile exists.

## Read-only target dogfood

| Target | Inspected revision | Relevant tracked surfaces | Result |
| --- | --- | --- | --- |
| Knowledge Forge site | `e806e49a45797937e62f7bde61c711bec38725c7` | 5 Markdown, 2 MDX, 1 TypeScript, 1 MJS; no Astro, JSX/TSX, React source, or Vitest config | locked npm install and production build passed; 10 pages built |
| Knowledge Forge Terminal Nova | `cad2b8bdddfc0f2ac3718e7ca92e24e6b82051e0` | 15 Markdown, 13 MDX, 5 Astro, 4 TypeScript; no JSX/TSX or Vitest | locked pnpm install truthfully stopped because seven manifest dependencies were absent from the lockfile; no unlocked install or build ran |
| cal.diy | `176037d0afbe572f870a3c702985e7cd83fe6c0c` | 356 Markdown, 25 MDX, 1,147 TSX, 3,878 TypeScript, 31 JavaScript, React, JSX, and Vitest | immutable Yarn install, 19 focused Vitest tests, and UI workspace type-check passed |
| conduit-connector-http | `dba2f5a39c28e1ac408605a2ff085d0d67ba1c38` | Go with GoMock v0.6.0 and go-cmp v0.7.0 selected together | `go test ./...` passed |

Both established Knowledge Forge targets therefore ground Markdown, MDX,
Astro, TypeScript, JavaScript, and Node concerns but cannot by themselves ground
React, JSX/TSX, or Vitest. The clean third web target closes that reviewed
qualification gap. Every target remained tracked-tree clean; the existing
dirty and divergent Terminal Nova checkout was not touched.

## Deterministic cross-profile ownership

The APG89 fixture makes selection explicit, rejects a mandatory profile chain,
declares no aggregate owner, and names exactly the six frozen v0.6 profiles.
Assertions are distributed through the participating profiles' existing owner
tests, so the owner-keyed test inventory gains no unowned path.

| Web question | Narrowest owner |
| --- | --- |
| pure Markdown structure | `markdown-language-profile` |
| Markdown/component seam | `mdx-profile` |
| island placement and directive | `astro-profile` |
| component state, Hooks, effects, and rerendering | `react-component-profile` |
| library-independent JSX/TSX syntax and transform | `jsx-language-profile` |
| checking and type erasure | `typescript-language-profile` |
| ECMAScript evaluation | `javascript-language-profile` |
| process, package, loader, and runtime | `nodejs-runtime-profile` |
| selected Vitest mechanics | `vitest-test-profile` |
| useful-test and evidence sufficiency policy | `implementing-with-test-discipline` |

| Go question | Narrowest owner |
| --- | --- |
| language and type semantics | `go-language-profile` |
| native test lifecycle | `go-test-profile` |
| selected GoMock mechanics | `gomock-test-profile` |
| selected go-cmp comparison mechanics | `go-cmp-test-profile` |
| useful-test and evidence sufficiency policy | `implementing-with-test-discipline` |

The matrix creates no implicit invocation, mandatory sequence, aggregate stack
owner, contradiction, or seventh v0.6 profile.

## Explicit-selection qualification

Disposable Git roots exercised project install, check, and default uninstall.
An exact two-skill subset, a 33-name pre-v0.6-style subset, the nine-skill web
composition set, and the four-skill Go composition set each retained exactly
its selected membership while the source advertised 39 skills. Default check
and uninstall followed recorded ownership without expansion; unrelated files
survived. No live user or global projection was read as selection authority or
mutated. v0.6 remains explicit-selection-only and adds no advisory discovery.

## Installed context and reproducibility

Two disjoint committed-source bundle builds produced byte-identical artifacts:

| Artifact | SHA-256 |
| --- | --- |
| `agentic_praxis_grimoire-0.5.0-py3-none-any.whl` | `a37d85826a440f55bd1921c3dbb8324a3c0ab78cd969775f34a6fd6fc1d7dc03` |
| `agentic_praxis_grimoire-0.5.0.tar.gz` | `d5ebe11646c14769cb2bb77a6679307fa45e55b9bffe661013d14b9c1081df18` |
| `SHA256SUMS` | `85a3a626c01a75a6368e3f4d68b69d62d6340d384d6c795e694395b65a7caa63` |

A selected wheel installed into a fresh outside-checkout virtual environment
with isolated APGR, cache, configuration, and home roots. Installed `skills
list --json` returned the exact 39 metadata rows and resource digests. Installed
`skills context-report --json` matched checkout readback exactly: 39 skills, 39
discoverable, 9,504 bytes, 9,492 characters, and an empty malformed list.

## Coverage determinism investigation

The recurring observation is real and was not present in the APG86-APG88
tracked narratives. A fixed five-integration and five-combined baseline sample
was selected before outcomes were inspected. No threshold, rounding,
denominator, exclusion, or retry-until-green policy changed.

| Sample | Integration statements | Integration branches | Outcome |
| --- | ---: | ---: | --- |
| integration 1 | 8,667/9,973 | 2,861/3,574 | pass |
| integration 2 | 8,667/9,973 | 2,861/3,574 | pass |
| integration 3 | 8,673/9,973 | 2,862/3,574 | pass |
| integration 4 | 8,661/9,973 | 2,858/3,574 | branch failure |
| integration 5 | 8,659/9,973 | 2,858/3,574 | branch failure |
| combined 1 | 8,673/9,973 | 2,862/3,574 | union 9,220/3,174, pass |
| combined 2 | 8,667/9,973 | 2,861/3,574 | union 9,220/3,175, pass |
| combined 3 | 8,659/9,973 | 2,858/3,574 | integration branch failure; union 9,218/3,173 passed |
| combined 4 | 8,673/9,973 | 2,862/3,574 | union 9,220/3,174, pass |
| combined 5 | 8,675/9,973 | 2,862/3,574 | union 9,222/3,174, pass |

Retained coverage reports localized seven moving arcs in
`libexec/agent_report/safety.py`: `491->511`, `505->507`, `507->510`,
`511->512`, `536->537`, `550->557`, and `563->567`. The first five belong to
fresh ownerless report-lock contention and exhaustion. The last two are the
normal live-owned-lock predicate and positive-PID path. Additional variance was
localized to response allocation contention. Three deterministic integration
tests exercise the observed paths: fresh ownerless report-lock refusal,
live-owned report-lock refusal, and one response phase-lock retry. A focused
two-lock coverage run executes all seven report-lock arcs. Production code,
coverage policy, thresholds, exclusions, and rounding remain unchanged.

The first corrected integration sample, before the live-owned-lock test was
added, passed all 632 tests with two skips and branch observations 2,865,
2,865, 2,865, 2,863, and 2,865 over 3,574. The low observation omitted exactly
the two live-owned-lock arcs. The final predeclared fixed sample used the
resulting 633-test tree and the updated 9,974-statement denominator:

| Final sample | Integration statements | Integration branches | Combined unit statements/branches | Combined union statements/branches | Outcome |
| --- | ---: | ---: | ---: | ---: | --- |
| integration 1 | 8,678/9,974 | 2,865/3,574 | - | - | pass |
| integration 2 | 8,678/9,974 | 2,865/3,574 | - | - | pass |
| integration 3 | 8,678/9,974 | 2,865/3,574 | - | - | pass |
| integration 4 | 8,678/9,974 | 2,865/3,574 | - | - | pass |
| integration 5 | 8,680/9,974 | 2,865/3,574 | - | - | pass |
| combined 1 | 8,678/9,974 | 2,865/3,574 | 8,610/2,862 | 9,223/3,177 | pass |
| combined 2 | 8,678/9,974 | 2,865/3,574 | 8,610/2,862 | 9,223/3,177 | pass |
| combined 3 | 8,678/9,974 | 2,865/3,574 | 8,610/2,862 | 9,223/3,177 | pass |
| combined 4 | 8,678/9,974 | 2,865/3,574 | 8,610/2,862 | 9,223/3,177 | pass |
| combined 5 | 8,678/9,974 | 2,865/3,574 | 8,610/2,862 | 9,223/3,177 | pass |

Every combined unit component passed 3,355 tests, and every integration
component passed 633 tests with two skips. One zero-test runtime-binding
preflight and one platform-default temporary-root setup attempt were rejected
before the valid combined sample; neither is counted as an observation. The
fixed branch result is therefore deterministic for the bounded sample rather
than inferred from threshold success alone.

## Provenance, compatibility, and stop

APG89 changes no skill body, description, catalog row, projection, maturity,
route, source, rights, or provenance owner. The accepted APG85-APG88
architecture and six source/rights/provenance families remain unchanged.
Public and active v0.5.0, dependencies, lockfiles, tags, publication workflows,
and active projections remain unchanged.

The Terminal Nova lockfile defect is target-owned and blocks only that target's
locked executable build; APG did not patch or bypass it. Candidate readiness
is bounded to the tested targets, explicit selection cases, installed context,
package reproducibility, and fixed coverage sample recorded here. No version
advance, release candidate naming, tag, upload, deployment, active projection
mutation, APG90 execution, provider staging, commit, or push is authorized or
performed. The completed supervisory review is external evidence for this
historical implementation/testing candidate. Its accepted terminal disposition
is `READY_FOR_APG90`; APG90 remains responsible for any version advance and
tracked release preparation.
