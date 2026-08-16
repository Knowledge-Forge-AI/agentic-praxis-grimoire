# APG v0.5 Roadmap

<!-- APG-CANDIDATE-STATE: css-language-profile retained-provisional -->

The marker above is the mechanical current-state authority. Bounded
contradiction diagnostics cover only their frozen vocabulary; arbitrary prose
still requires human review.

## Authority and status

APG44 records this human-approved, dependency-ordered v0.5 roadmap, APG45
records the independent dispositions and corrects its owner graph, APG46
through APG47 complete the separately authorized authoring and integration
cycle for accepted evidence guidance, APG48 completes the Workstream 2
dogfood and candidate authoring, APG49 completes its independently
authorized validation disposition, APG50 opens Workstream 3 with the
web and Node profile-family architecture and source baselines, and APG51
independently corrects and terminally dispositions that architecture. APG52
repairs the rejected corpus evidence foundation without reopening that
decision. APG58 authors the CSS pilot and APG59 independently validates and
rejects it. A roadmap entry records an intended bounded result; it does
not allocate a semantic
phase ID and it does not authorize execution. Each slice requires separate
maintainer authority, and no maturity or release decision is made by
roadmap implication. No phase after APG59 is authorized by this document.

The v0.5 line begins from published corrected v0.4.0: twenty-eight canonical
skills, twenty-eight catalog rows, twenty-eight projections, fourteen stable
and fourteen provisional, twenty-six general-router entries, one
ChatGPT-local entry, and no mandatory chain. v0.5 work must preserve that
release and its active integration unless a later release or integration
phase explicitly owns a change. Direct selection and no mandatory profile
chain are preserved throughout v0.5.

## Workstream 1 — fact-check analysis, peer review, and implementation

APG44 analyzes the external
[`petar-nauka/fact-check-skill`](https://github.com/petar-nauka/fact-check-skill)
repository (main at `ebfde09a28b5547cbed29f5f66ddfd3595e64ade`, MIT) and
freezes ten clean-room recommendations with author dispositions — five
forwarded sentence-scale improvements to existing owners, one deferred
fact-check-owner question, and four recorded rejections (numeric risk
scoring, fixed source tiers and universal source counts, duplicate output
tooling, already-owned revision policy). See the
[APG44 comparative analysis](evaluations/apg44-fact-check-skill-comparative-analysis.md).

Order within the workstream:

1. APG45 independently reviewed every recommendation and accepted ADR 0029
   with graph amendments.
2. APG46 authored the candidate REC-01 through REC-04 guidance on a Claude
   branch under the terminal dispositions, preserving integrated 28/28/28;
   see the
   [APG46 evaluation](evaluations/apg46-accepted-evidence-guidance-authoring.md).
3. APG47 preserved and integrated the exact APG46 object after failing-first
   contracts, a successful no-pointer policy-discoverability probe, one forward
   correction cycle, and the complete stable-skill regression gates; see the
   [APG47 evaluation](evaluations/apg47-accepted-evidence-guidance-integration.md).

REC-05 and REC-07 through REC-10 are rejected. REC-06 is deferred until
recurring repository-relevant real use exceeds current owners. Acceptance is
not implementation; APG45 changed no skill. APG47 now integrates only the
accepted REC-01 through REC-04 guidance.

## Workstream 2 — Go test-component reconsideration

After accepted fact-check recommendations are implemented, reconsider the
previously rejected/deferred Go composition candidates:

```text
matryer-is-test-profile
go-testing-stack
```

Evidence base: bounded dogfood in five named repositories (the maintainer
expanded the original three with two negative or project-convention
controls; local clones verified present, clean, and remote-equal in APG48):

- [conduitio-labs/conduit-connector-http](https://github.com/conduitio-labs/conduit-connector-http)
- [esnet/gdg](https://github.com/esnet/gdg)
- [blockvisionhq/sui-go-sdk](https://github.com/blockvisionhq/sui-go-sdk)
- [kubernetes-sigs/bom](https://github.com/kubernetes-sigs/bom)
- [apache/skywalking-mcp](https://github.com/apache/skywalking-mcp)

Retention rule: the stack (or a corrected matryer/is profile) is an
evidence-tested candidate, not a predetermined addition. It may be retained
only if the dogfood repositories expose recurring composition work not
already owned by direct `go-test-profile`, `go-cmp-test-profile`,
project-local conventions, or a corrected matryer/is profile. ADR 0025
remains Rejected, ADR 0026 Accepted and controlling, and ADR 0027 Rejected
unless a later authorized phase decides otherwise on that evidence.

APG48 result: the `matryer-is-test-profile` candidate is authored
(`authored-pending-codex-review`) with exact v1.4.1 calibration, all eight
historical defect families closed, and frozen scenarios APG48-IS-01…24;
`go-testing-stack` is not authored (`not-authored-no-independent-value`)
after the eight-part stack-evidence gate failed on fresh five-repository
evidence.
[ADR 0030](adr/2026/07/0030-dogfood-grounded-go-testing-component-and-composition-ownership.md)
is Proposed with no current architecture change; see the
[APG48 evaluation](evaluations/apg48-go-test-harness-dogfood-and-candidate-authoring.md).
APG48 left Codex verification, probing, one correction cycle, the ADR 0030
decision, and any integration to a later separately authorized phase.

APG49 result: exact byte-level source, five-repository dogfood, public-safe
failing-first, and isolated runtime evidence supported one correction pass.
Fresh corrected-state review then found new material source-filename,
parent/subtest severity, selected-version classification, and scenario-
continuity defects. The candidate is `deferred-material-defect` and current
surfaces are removed. ADR 0030 is Rejected, ADR 0026 remains Accepted and
controlling, development stays 28/28/28, and the terminal no-stack result is
unchanged.

## Workstream 3 — web and Node profile family

Develop evidence-tested candidates for:

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

Dogfood targets (stack evidence verified 2026-07-26: Astro 7 with Starlight
and React 19 in the first; Node >=22.12, pnpm 10, Astro 7, ESLint 10, and
Starlight theme work in the second):

- [Knowledge-Forge-AI/Knowledge-Forge-AI.github.io](https://github.com/Knowledge-Forge-AI/Knowledge-Forge-AI.github.io)
- [Knowledge-Forge-AI/theme-forge-terminal-nova](https://github.com/Knowledge-Forge-AI/theme-forge-terminal-nova)

Owner boundaries:

- JavaScript and TypeScript profiles own their actual artifact semantics.
  The maintainer preference "JavaScript for short/simple utilities,
  TypeScript for large/complicated utilities" is a project policy
  preference, not a universal complexity threshold.
- `nodejs-runtime-profile` owns Node-specific runtime and CLI behavior for
  either language, separate from both language owners.
- No Starlight-specific profile unless later dogfood demonstrates a
  coherent owner not covered by Astro, Markdown/MDX, React, CSS, and
  project policy.

APG50 result: bounded read-only inspection of both targets at exact
commits, complete source/version/rights baselines, and one architecture
disposition per candidate — javascript, typescript, nodejs-runtime, css,
markdown, mdx, and astro `architecture-supported`; jsx
`architecture-supported-with-target-evidence-gap` (JSX appears only
MDX-embedded); react-component and vitest-test `defer-missing-dogfood`
(React configuration-only, Vitest absent). HTML and the browser/DOM
runtime are recorded unowned adjacent gaps; a Starlight residual is
recorded and deferred; sixty architecture scenarios (APG50-WEB-001…060)
are frozen; bounded slices A (JS/TS/Node), B (CSS/Markdown), C (MDX +
conditional JSX), and D (Astro) are proposed with React and Vitest
excluded pending real target evidence.
[ADR 0031](adr/2026/07/0031-web-and-node-profile-family-ownership-and-authoring-sequence.md)
is Proposed with no current architecture change; see the
[APG50 evaluation](evaluations/apg50-web-and-node-profile-family-architecture.md)
and the [family architecture document](architecture/web-and-node-profile-family.md).
APG50 left independent verification, scenario testing, one forward
correction cycle, the ADR 0031 decision, and any authoring to a later
separately authorized phase.

APG51 result: fresh corrected-state review finds a false JSX rights
classification and a non-reproducible structural corpus record after the one
authorized correction. ADR 0031 is Rejected; all ten candidates are `defer`;
no authoring slice is eligible. Consumer-specific TypeScript evidence,
candidate dual-axis bands, Policy A, and browser/HTML/accessibility
recommendations remain review evidence for a fresh separately authorized
architecture cycle. See the
[APG51 evaluation](evaluations/apg51-web-and-node-architecture-peer-review.md).
No skill or slice was authored.

APG52 result: committed APG51 evidence is confirmed not fully reproducible.
Every named abbreviated source identity is recovered without silent
substitution, and a separately selected exact-object corpus is generated twice
from disjoint acquisitions with byte-identical canonical outputs. Nine
whole-file classes are reproducible-sufficient; scoped CSS and standalone
JSX/TSX retain explicit source-family insufficiencies. The APG51 values remain
hypotheses, ADR 0031 remains Rejected, ADR 0032 is not created, all ten
candidates remain deferred, and no authoring slice is eligible. See the
[APG52 evaluation](evaluations/apg52-reproducible-web-node-evidence-foundation.md).

APG53 result: exact APG52 evidence and its managed report are verified without
changing any Web/Node conclusion. The current tree removes three complete
regenerable JSONL datasets after exact hash and disposable-regeneration
verification, while compact evidence and external-output reproduction remain.
The supplied `flatten-skill-symlinks` command, corrected report storage and
project identity, and deterministic change-size enforcement become
current-development surfaces under Accepted ADR 0032. No skill is authored,
all ten Web/Node candidates remain deferred, and public/active v0.4.0 remain
unchanged. See the
[APG53 evaluation](evaluations/apg53-operational-tooling-and-report-hygiene.md).

APG54 result: the exact final APG53 correction and managed-report recovery
shape are verified. The supplied global-installer purpose becomes one
standard-library Python command for combined local repository-set projection
to current Codex or Claude personal roots. Accepted ADR 0033 owns default APG,
explicit source sets, duplicate-name refusal, state, transaction, rollback,
and coexistence boundaries. The command is future-v0.5 candidate content; no
live installation or publication occurs. Development remains 28/28/28 and
public/active corrected v0.4.0 remain unchanged. See the
[APG54 evaluation](evaluations/apg54-global-skill-installer-integration.md).

APG56 result: a fresh architecture reconstruction consumes the APG52
foundation without reopening rejected ADR 0031. All ten candidates receive
separate owner-validity, authoring-eligibility, and growth-band decisions:
six are proposed authoring-eligible (JavaScript, CSS, Markdown plain;
TypeScript, Node, Astro with narrowing), JSX and MDX are coherent owners
with deferred authoring, and React and Vitest remain Policy A deferrals. A
frozen family-balanced method derives eight exact proposed bands; scoped
CSS, standalone JSX/TSX, and MDX stay non-normative. Eighty fresh scenarios
(APG56-WEB-001…080), typed owner-graph and one-count rules, adjacent-gap
recommendations, and a bounded W1–W4 slice sequence (CSS-only first) are
recorded.
[ADR 0034](adr/2026/07/0034-web-and-node-profile-family-reconstruction-and-authoring-sequence.md)
is Proposed pending independent Codex review; see the
[APG56 evaluation](evaluations/apg56-web-and-node-architecture-reconstruction.md)
and the
[reconstruction architecture document](architecture/web-and-node-profile-family-reconstruction.md).
No skill is authored or integrated.

APG57 result: initial review reproduces the APG56 thresholds and finds every
class unfit for normative use. Corrected-state review then finds material
interval, target-placement, reproduction-gate, ledger, and scenario defects,
so ADR 0034 is Rejected under the one-correction rule. All authoring and bands
remain deferred, no W1–W4 slice is eligible, and corrected public/active
v0.4.0 and development 28/28/28 remain unchanged.

APG58 result: a CSS-only pilot replaces sampled-tail inference with explicit
policy-selected structural limits (300/600/900 nonblank lines). One candidate
`css-language-profile` leaf and `docs/specs/css-language-profile.md`
specification are authored,
[ADR 0035](adr/2026/07/0035-css-language-profile-and-policy-selected-structural-limits.md)
is Proposed, thirty scenarios are frozen, all twelve pinned target
stylesheets are placed (the 995-line control legacy Red), and a Codex APG59
validation handoff is recorded. Nothing is integrated; both rejected ADRs
and all other candidates stay unchanged; see the
[APG58 evaluation](evaluations/apg58-css-language-profile-pilot-authoring.md).

APG59 result: failing-first contracts reproduce projected/resulting-count,
task-aggregation, authority, accessibility, and custom-property defects. One
forward correction closes them without retuning 300/600/900; fresh review
finds material executable-contract and removal defects. ADR 0035 is Rejected,
the candidate is removed, and development, corrected public, and active remain
28/28/28; see the
[APG59 evaluation](evaluations/apg59-css-language-profile-validation-and-integration.md).

APG60 result: a frozen candidate-independent contract executes exactly sixty
CSS response and lifecycle cases, while a generic 50-owner manifest exercises
retained and rejected cleanup against every current owner and preserves
history. The CSS candidate remains absent, ADR 0035 remains Rejected, ADR
0036 is unused, and development/public/active state is unchanged; see the
[APG60 evaluation](evaluations/apg60-css-reentry-contract-and-removal-foundation.md).

## Dependency order

Arrows describe analysis and design inputs, not mandatory runtime invocation:

```text
fact-check analysis (APG44)
  → terminal Codex dispositions (APG45)
    → APG46 authoring
      → APG47 validation and integration

accepted evidence/review improvements
  → Go test-component dogfood and redesign
    → Codex integration disposition

javascript-language-profile
  ├─→ typescript-language-profile
  ├─→ nodejs-runtime-profile
  └─→ jsx-language-profile

typescript-language-profile
  ├─→ nodejs-runtime-profile
  └─→ jsx-language-profile              # TSX boundary

css-language-profile           (early, independent)
markdown-language-profile      (early, independent)
react-component-profile        (independent candidate root)

jsx-language-profile
  ─→ react-component-profile            # conditional integration

markdown-language-profile + jsx-language-profile
  → mdx-profile
react-component-profile
  ─→ mdx-profile                        # conditional runtime pairing

javascript/typescript + applicable css + markdown/mdx
  → astro-profile
react-component-profile
  ─→ astro-profile                      # optional framework adapter

javascript/typescript + nodejs-runtime-profile
  → vitest-test-profile

all retained web profiles
  → bounded dogfood in the two Knowledge Forge AI repositories
    → v0.5 readiness
      → separately authorized v0.5 publication
```

CSS, Markdown, and React are independent candidate roots. Node is not a
prerequisite for TypeScript language semantics. JSX owns both JavaScript JSX
and the TypeScript TSX boundary. React may be used without JSX, and it is not
required for every MDX or Astro artifact. Exact adapters, build tools, package
managers, browser environments, and target frameworks remain project-owned.

[ADR 0029](adr/2026/07/0029-v0-5-evidence-go-testing-and-web-profile-roadmap.md)
is Accepted with amendment. It records the consequential ordering and
ownership decisions behind this roadmap, accepts no profile, and creates no
mandatory skill chain.

## Next action

APG60 completes only the pre-authoring CSS contract and removal foundation
after APG59's rejection.
ADR 0031 and ADR 0034 remain Rejected. Live migration,
browser/HTML/accessibility evidence phases, v0.5 readiness/publication, and
every authoring or integration slice remain later, separately authorized
roadmap entries.
## APG60A corrected CSS foundation

APG60A is complete. It preserves the APG60 rejection and policy bands while
hardening projection-overrun, exception authority, broken-symlink residue, and
actual retained-surface closure. APG61 fresh authoring is the recommended next
phase but remains separately authorized. No CSS candidate, ADR 0036, target,
publication, deployment, or active state is created by APG60A.

## APG60B CSS closure hardening

APG60B is complete. It preserves the APG60A sixty-case behavior contract and
closes exact map, clause-anchor,
narrative-state, Python-binding, derived-value, isolation, and future ADR
lifecycle mechanics before any new CSS prose exists. APG61 remains the
recommended authoring phase but requires separate authority; no other Web or
Node candidate is advanced.

## APG60C CSS runtime and lifecycle closure

APG60C is complete. It preserves accepted APG60B while recording the
owner-source finality claim later narrowed forward by APG60D, truthful
bounded narrative diagnostics, an actual authored Proposed but unintegrated
terminal state, preserved-history rejection, and direct regular
current-survivor ownership. The sixty-case behavior contract, 28/28/28
inventory, and 14/14 maturity split remain unchanged. APG61 remains recommended
but separately authorized; no other candidate or successor begins.

## APG60D CSS source-binding and phase-history closure

APG60D is complete. It preserves accepted APG60C while replacing the
runtime/call-finality overclaim with truthful static source-binding integrity
and requiring exact direct-regular phase bundles. APG58 through APG60D are the
foundation; APG61 is required for authored state; APG61 and APG62 are required
for retained or rejected state. APG60D owns exit 00084, so future APG61 and
APG62 exits are 00085 and 00086. CSS remains absent, ADR 0036 remains unused,
and no candidate or successor begins automatically.

## APG60E CSS repository-path and candidate-surface closure

APG60E is complete. It preserves accepted APG60D while closing authority-input,
authored-owner, retained-owner, and projection-target path provenance through
one physical-root descriptor-relative no-follow contract. APG58 through
APG60E are the foundation; APG61 is required for authored state; APG61 and
APG62 are required for retained or rejected state. APG60E owns exit 00085, so
future APG61 and APG62 exits are 00086 and 00087. CSS remains absent, ADR 0036
remains unused, and no candidate or successor begins automatically.

## APG60F CSS import, owner, and projection closure

Status: Complete.

APG60F preserves accepted APG60E while closing repository-local transitive
import and cache isolation, exact required-role authority, and coherent
projection/target observation. APG58 through APG60F are the foundation; APG61
is required for authored state, and APG61 plus APG62 are required for retained
or rejected state. Future exits are 00087 and 00088. CSS remains absent, ADR
0036 remains unused, and APG61 remains recommended but separately authorized.

Terminal unit, integration, combined-union, configured Bats, all-five-state
lifecycle, integrity, privacy, rights, and independent non-author review gates
passed.

## APG60G CSS snapshot, role, and derived-set closure

Status: Complete.

APG60G preserves accepted APG60F while closing replacement-root,
cardinality-only derived-set, coordinated semantic-role, and stale-authority
false passes. APG58 through APG60G are the foundation; APG61 is required for
authored state, and APG61 plus APG62 are required for retained or rejected
state. Future exits are 00088 and 00089. CSS remains absent, ADR 0035 remains
Rejected, ADR 0036 remains unused, and APG61 remains recommended but
separately authorized.

The pinned-root, exact-set, code-owned role, coherent-read, all-five-state,
full-regression, privacy, rights, and independent-review gates are the APG60G
terminal foundation checks.

## APG60H foundation completion

APG60H completes the pre-authoring snapshot and full-path foundation. APG61
remains recommended but separately authorized, uses exit 00089, and must
preserve all APG60H lifecycle and temporary-storage contracts. APG62 remains
future exit 00090.

## APG60I worker temporary-root foundation correction

APG60I preserves the maintainer-directed APG60H adoption and corrects its two
known worker temporary-storage exceptions forward. APG61 remains recommended
but separately authorized, uses exit 00090, and must preserve the APG60I
descriptor-binding and cleanup lifecycle. APG62 remains future exit 00091.

## APG61 CSS candidate authoring

APG61 consumed exit 00090: one fresh `css-language-profile` candidate was
authored from the frozen contract on the preserved Claude authoring branch
with ADR 0036 Proposed, and no integration surface changed — current
candidate-state markers remain absent and development `main` remains at
exact APG60I. APG62 validation remains separately authorized future exit
00091.

## APG62 CSS candidate validation and rejection

APG62 consumed exit 00091. Independent reconstruction and semantic review of
all sixty frozen outcomes produced seven initial defects; the one authorized
coherent correction was followed by a new material six-case
`record-growth-state` overreach. ADR 0036 is Rejected and all current CSS
candidate owners are removed. Development remains 28/28/28 with 14 stable /
14 provisional, APG61 history is preserved, and public, active, and target
state remains unchanged. No successor is authorized.

## APG63 Markdown architecture and lean contract

APG63 consumed exit 00092. The Markdown profile line begins with a
docs-only architecture phase: a narrowed coherent owner, closed raw-HTML,
frontmatter, and MDX/host boundaries, qualitative structure-first
structural policy under ten pre-frozen purpose controls, the lean
thirty-six-scenario candidate-independent contract, and Proposed ADR 0037,
with the authoring-eligibility result authoring-eligible-with-narrowing.
The terminal CSS rejection is preserved untouched; no skill is authored
and nothing is integrated; development remains 28/28/28 with 14 stable /
14 provisional; and public, active, and target state remains unchanged.
Codex peer review (recommended APG64) terminally decides ADR 0037 and
remains separately authorized.

## APG64 Markdown architecture peer review

APG64 consumed exit 00093 and terminally reviewed exact APG63. The accepted
amendment makes the actual parser/configuration authoritative, separates
selection, response, and routing, makes 34 semantic scenarios deterministic,
types two lifecycle rows as process invariants, and retains qualitative
structure-first policy without numeric bands. ADR 0037 is Accepted with
amendment and authoring eligibility remains authoring-eligible-with-narrowing,
but no Markdown candidate, integration, or successor is authorized.

## APG65 Markdown language-profile candidate authoring

APG65 authored the first post-architecture Markdown candidate on the Claude
authoring branch: an operational leaf, the complete candidate specification,
and a navigation-only scenario-coverage record under Proposed ADR 0038. The
candidate keeps the accepted actual-parser-first grammar hierarchy, the
separated selection/response/routing axes, and qualitative no-band
structural policy. It remains branch-only, Proposed, unintegrated, and
pending separately authorized APG66 validation; no integration, maturity,
route, release, publication, or successor authority exists.

## APG66 Markdown language-profile validation and integration

APG66 independently validates and retains the APG65 Markdown candidate with
one coherent amendment. Development becomes 29/29/29 with 14 stable / 15
provisional; the general map becomes 27 entries, the ChatGPT-local map remains
one, and 28 edges are checked. Historical corrected v0.4.0 reconstruction,
public and active state, CSS absence, rejected CSS ADRs, and read-only target
state remain unchanged. No readiness, publication, deployment, APG67, or
successor is authorized.

## APG67 JavaScript language-profile architecture

APG67 opens the v0.5-line JavaScript work with architecture only: ADR 0039
is Proposed, the lean contract and forty-row register are frozen on the
Claude architecture branch, and authoring eligibility is
`authoring-eligible-with-narrowing`. Development remains 29/29/29 with 14
stable / 15 provisional and 27/1/28 routes; the Markdown profile remains
retained provisional; public and active corrected v0.4.0 are unchanged. The
terminal ADR 0039 decision belongs to separately authorized APG68, and no
candidate authoring, integration, readiness, publication, or successor is
authorized.

## APG68 JavaScript architecture review

APG68 terminally rejects ADR 0039 after one coherent correction and fresh
review. Qualitative disposition C remains historical evidence, but material
response, route, signal, host, and source-boundary defects prevent an
authoring oracle. Eligibility is `not-applicable-rejected`; no skill or
integration owner exists. APG69 is not recommended or begun.

## APG69 JavaScript core architecture reset

APG69 restarts the JavaScript line under new human authority with a
fresh branch-only proposal: ADR 0040 (Proposed), a narrower
ECMAScript-core owner, four separated decision layers with an ordered
effective route union, independent 24/10/8/2 registers, and qualitative
disposition C selected on fresh grounds. ADR 0039 remains Rejected;
Markdown remains retained provisional; public and active corrected
v0.4.0 are unchanged. Eligibility is
`authoring-eligible-with-narrowing`; APG70 terminally decides ADR 0040.

## APG70 JavaScript core layered-architecture peer review

APG70 preserves exact APG69, freezes independent vectors and the complete
initial set, uses one coherent correction, and preserves the actual corrected
patch. Fresh review finds new material defects after the sole correction, so
ADR 0040 is Rejected and eligibility is `not-applicable-rejected`. The fresh
architecture is historical evidence only; no JavaScript candidate or
integration owner exists. APG71 is not recommended, ADR 0041 and exit 00104
remain unused, and no successor is authorized.

## APG71 TypeScript architecture and compiler-generation boundary

APG71, under separate new human authority for TypeScript only, proposes
ADR 0041 and exit 00104: an independent TypeScript static-semantics owner
under project-selected exact compiler authority, separate TypeScript 7
native and TypeScript 6 legacy source generations, closed
`.tsx`/checked-`.js`/embedded-host/declaration boundaries, structural
disposition D, and eligibility `authoring-eligible-with-narrowing` with no
candidate authority. ADR 0039 and ADR 0040 remain Rejected; no TypeScript
skill or integration owner exists. APG72 is recommended to terminally
decide ADR 0041; exit 00105 remains unused, and no successor is
authorized.

## APG72 TypeScript architecture peer review

APG72 terminally reviews exact APG71, uses one correction, and preserves the
corrected 22/14/2 state before two fresh non-author lanes find new material
owner/route, role-state, source-kind, and evidence-state defects. ADR 0041 is
Rejected and eligibility is `not-applicable-rejected`; exit 00105 is consumed.
No TypeScript skill or current architecture input exists. APG73 is not
recommended or begun, and no successor is authorized.

## APG73 language-profile production recovery charter

APG73 consumes exit 00106 under new human governance authority and accepts ADR
0042. The production-recovery charter retires automatic rejection after one
correction, retains one coherent correction per round, and allows up to three
separately preserved rounds by default. Repairable remaining defects normally
yield `repair-required`; Critical and High defects block integration;
Medium/Low debt and terminal rejection require explicit human decisions.
TypeScript is essential and TypeScript 7 is the intended primary generation;
CSS and JavaScript are desirable; JSX is deferred; temporary TypeScript 6 is
role-bound. No profile or integration surface changes. APG74 is recommended
but not begun.

## Intended APG74–APG77 recovery order

These identities are roadmap-only and each requires separate human authority:

1. APG74 — Claude TypeScript Language-Profile Candidate and Intended-State
   Target Harness; exit 00107; ADR 0043 Proposed; no integration.
2. APG75 — Codex TypeScript Iterative Hardening and Provisional Integration;
   exit 00108; decide ADR 0043; up to three rounds.
3. APG75A — TypeScript Scope and Lifecycle Closure; exit 00109; no new ADR.
4. APG76 — Claude CSS Candidate Recovery; exit 00110; ADR 0044 Proposed; no
   integration.
5. APG77 — Codex CSS Iterative Hardening and Provisional Integration; exit
   00111; decide ADR 0044.

APG73 begins none of them.

APG74 has since executed under that separate authority as candidate
authoring only: leaf, specification, scenario coverage, fixture, and
Proposed ADR 0043 exist branch-only with no integration surface change. The
intended order above is otherwise unchanged; APG75 is recommended next and
is not begun.

APG75 has since completed under separate authority. It retains the corrected
TypeScript profile provisionally after three rounds, accepts ADR 0043 with
amendment, and consumes exit 00108. Development becomes 30/30/30, 14/16, and
28/1/29 while public and active corrected v0.4.0 remain unchanged. APG76 and
APG77 stay unbegun roadmap identities and require separate human authority.

APG75A has since closed the reusable compiler-generation, response-axis,
current-lifecycle, delivery, and clean-runner defects while preserving the
provisional TypeScript integration. Narrow JavaScript recovery moves after the
separately authorized CSS authoring/hardening pair. APG76 and APG77 are not
begun.
## APG76 CSS candidate recovery status

APG76 is delivered as a Claude authoring phase: ADR 0044 Proposed, exit 00110,
one reusable CSS profile candidate, one navigation-only coverage record, and one
fourteen-case target-first fixture, all unintegrated on a branch. The structural
disposition is deferred and no parser smoke ran, because no exact current target
CSS tool role is selected. APG77 remains a separately authorized Codex hardening
phase and is not begun.

## APG77 repair checkpoint status

APG77 has since used three immutable correction rounds. Fresh terminal review
finds two High evidence defects, so ADR 0044 remains Proposed and the CSS
candidate is preserved `repair-required` without integration. Development
remains 30/30/30, 14/16, and 28/1/29. APG78 and narrow JavaScript recovery do
not begin; further CSS repair requires a new human continuation decision.

## APG77A evidence-retention checkpoint status

APG77A uses the explicit human continuation to preserve complete target
identity evidence and two independent 45-purpose vector sets. Fresh review
finds three High defects and no accepted debt, so ADR 0044 remains Proposed and
CSS remains `repair-required` without integration. Development remains
30/30/30, 14/16, and 28/1/29. APG78 and narrow JavaScript recovery are not
recommended or begun; further CSS work requires a new human decision.

## APG77B traceability and clean-room checkpoint status

APG77B uses the explicit H3-H5 continuation to preserve corrected SVG authority,
complete purpose/lane/provenance evidence, and current-tree removal of
contaminated Lane T bytes. Four-lane fresh review finds four High and two
Medium defects with no accepted debt, so ADR 0044 remains Proposed and CSS
remains `repair-required` without integration. Development remains 30/30/30,
14/16, and 28/1/29. APG78 and narrow JavaScript recovery are not recommended
or begun; further CSS work requires a new human decision.

## APG77C evidence-proportionality checkpoint status

APG77C uses explicit human proportionality authority to preserve compact
consequence-bearing evidence and an exact private historical-patch exception.
Fresh review finds six Medium and one Low unaccepted qualification defects, so
ADR 0044 remains Proposed and CSS remains `repair-required` without
integration. Development remains 30/30/30, 14/16, and 28/1/29. APG78 and
narrow JavaScript recovery are not recommended or begun; further CSS work
requires a new human decision.

## APG77D CSS provisional integration status

APG77D has since exercised the human decision and retained CSS provisionally
with exact known qualification debt. ADR 0044 is Accepted with amendment;
development becomes 31/31/31, 14/17, and 29/1/30. The four Medium debt items
block stable maturity, while no Critical/High or semantic/source/target/runtime/
release/rollback debt is accepted. Corrected public/active v0.4.0 and targets
remain unchanged. APG78 narrow JavaScript candidate work is recommended next
but is not begun and requires separate human authority.

## APG78/APG79 JavaScript recovery status

APG78 subsequently authored the narrow JavaScript candidate. APG79 preserved
three independently reviewed correction rounds, but terminal review leaves two
High and two Medium material defects with no accepted JavaScript debt. ADR 0045
remains Proposed, JavaScript is `repair-required-after-round-3`, and no
integration owner changes. Development remains 31/31/31, 14/17, and 29/1/30;
CSS known debt, corrected public/active v0.4.0, and targets remain unchanged.
APG80 is not recommended pending a new human decision.

## APG79A JavaScript terminal-proof status

APG79A subsequently exercises the separate human continuation decision and
preserves one immutable correction. Four fresh lanes find zero Critical, zero
High, five Medium, and zero Low material defects with no accepted JavaScript
debt. ADR 0045 remains Proposed, JavaScript is
`repair-required-after-apg79a`, and no integration owner changes. Development
remains 31/31/31, 14/17, and 29/1/30; CSS known debt, corrected public/active
v0.4.0, and targets remain unchanged. APG80 is not recommended pending a new
human decision.


## APG79B JavaScript contract and harness status

APG79B subsequently exercises another separate human continuation decision and
preserves one immutable correction. Five fresh lanes find zero Critical, zero
High, four unique Medium, and zero Low material defects with no accepted
JavaScript debt. ADR 0045 remains Proposed, JavaScript is
`repair-required-after-apg79b`, and no integration owner changes. Development
remains 31/31/31, 14/17, and 29/1/30; CSS debt, corrected public/active v0.4.0,
and targets remain unchanged. APG80 is not recommended pending a new human
decision.

## APG79C JavaScript human-debt and integration status

APG79C exercises explicit human debt authority for the four APG79B Medium
qualification limitations. All four are accepted for provisional use and
block stable maturity; no Critical, High, semantic, source, target, owner,
release, or rollback debt is accepted. Fresh preflight found one separate
unaccepted Medium Test262 identity discrepancy, so integration stopped. ADR
0045 remains Proposed, JavaScript remains `repair-required-after-apg79b`, and
development remains 31/31/31, 14/17, and 29/1/30. APG80 is not recommended.

## APG79D Test262 source-evidence checkpoint status

APG79D preserves one immutable forward correction of the false APG79B Test262
identity and separates the historical reviewed pin, mutable head observation,
exact rights object, normative authority, corpus use, and refresh consequence.
Terminal review then finds a Medium false proxy because the maintained
historical-report-rewrite mutation does not bind the managed report bytes; the
report itself remains byte-exact. The integration candidate is discarded.
ADR 0045 remains Proposed, JavaScript remains repair-required and unintegrated,
and development remains 31/31/31, 14/17, and 29/1/30. APG80 is not recommended;
further action requires a human decision.

## APG79E JavaScript provisional integration status

APG79E accepts `JS-QD-005` as one additional Medium supporting qualification
limitation and directly verifies the current APG79B report without claiming the
maintained proxy is repaired. The complete product and rollback gates pass with
zero Critical, High, or unaccepted Medium/Low findings. ADR 0045 is Accepted
with amendment and JavaScript is `provisionally-integrated-with-known-debt`
under exactly `JS-QD-001` through `JS-QD-005`. Development is 32/32/32, 14/18,
and 30/1/31. APG80 is recommended but separately authorized.
## APG80 Node.js candidate status

APG80 authors the `nodejs-runtime-profile` candidate branch-only under Proposed
ADR 0046 and integrates nothing. The candidate consumes runtime roles, selects
none, hard-codes no Node version, and defers structural policy entirely because
neither target contains Node structural material against which a threshold could
be calibrated. Known debt remains exactly `CSS-QD-001` through `CSS-QD-005` and
`JS-QD-001` through `JS-QD-005`; JavaScript, CSS, TypeScript, and Markdown
lifecycles are unchanged. Mainline development remains 32/32/32, 14/18, and
30/1/31. APG81 is recommended but separately authorized.

## APG81 Node.js hardening repair-checkpoint status

APG81 subsequently preserves three immutable correction rounds. Fresh terminal
review leaves zero Critical, three High, two Medium, and zero Low material
qualification-harness findings. No Node debt is accepted. ADR 0046 remains
Proposed, Node is `repair-required-after-round-3` and unintegrated, main remains
32/32/32, 14/18, and 30/1/31, and the candidate branch remains 33/32/32. A new
human continuation decision is required; APG81A, APG82, and successor work are
not begun or authorized.

## APG81A Node.js threat-model correction checkpoint

APG81A preserves a fresh zero-finding correction under the controlled local-or-
CI threat model and accepts no Node debt. One High rollback defect and one
Medium contradictory ADR-index lifecycle defect block the terminal integration
candidate. ADR 0046 therefore remains Proposed, Node remains corrected and
unintegrated, main remains exact APG79E at 32/32/32, 14/18, and 30/1/31, and a
new human decision is required. APG82 and successor work are not authorized.

## APG81B Node.js integration-contract clarification checkpoint

APG81B clarifies candidate-preserving rollback as 33/32/32 but does not
integrate Node. Five-scope staged review finds three Medium defects with zero
Node debt, including one unauthorized test-only correction. All attempted
integration bytes are removed; ADR 0046 remains Proposed and Node remains
corrected, repair-required, and unintegrated. Main remains exact APG79E at
32/32/32, 14/18, and 30/1/31. No APG82 or successor authority is granted.

## APG81C Node.js lifecycle, test, and scratch repair checkpoint

APG81C preserves the reviewed integration-support correction and ignored local
scratch policy, but immutable review finds one Medium contradiction in retained
review-state prose. Integration stops before source/target refresh or the full
integration gate. ADR 0046 remains Proposed; Node stays repair-required and
unintegrated at 33/32/32; main remains exact APG79E at 32/32/32, 14/18, and
30/1/31. No APG82 or successor work is authorized.

## APG81D Node.js repo-local scratch integration checkpoint

APG81D completes diagnostic regression, release, and rollback construction but
does not integrate Node. Final staged review finds C0/H1/M3/L0, so every
attempted integration/product/test owner is removed. ADR 0046 stays Proposed;
Node stays repair-required and unintegrated at 33/32/32; exact APG79E main stays
32/32/32, 14/18, and 30/1/31. No Node or scratch debt is accepted, and no
successor is authorized.

## APG81E Node.js final-integration review checkpoint

APG81E completes diagnostic integrated, rollback, scratch-cleanup, regression,
and release evidence, then stops on final staged review at C0/H1/M2/L0. The
incomplete rollback test-owner projection, chronology defect, and omitted fresh
release-schedule identity set are retained findings rather than accepted debt.
Attempted integration owners are discarded; ADR 0046 remains Proposed and Node
remains repair-required and unintegrated at 33/32/32. Exact APG79E main remains
32/32/32, 14/18, and 30/1/31. No APG82 or successor authority is granted.

## APG81F Node.js actual-test-projection repair checkpoint

APG81F stops its single correction on fresh C0/H3/M2/L0 review. No runner,
test, catalog, projection, maturity, route, project, release, inventory, or
current lifecycle owner is retained from the attempt. ADR 0046 remains Proposed
and Node remains unintegrated at 33/32/32. Zero Node or scratch debt is accepted,
and no APG82 or successor authority is granted.

## APG81G Node.js selector, release, and integration closure

APG81G attempted one correction of the APG81F selector, two-state execution,
release-import, chronology, and exact-evidence findings. Fresh review found two
High and four Medium defects, so all attempted implementation and test bytes are
discarded. ADR 0046 remains Proposed; Node remains retained, repair-required,
and unintegrated at 33/32/32; no successor is authorized.

## APG81H Node.js reviewable qualification and integration closure

APG81H authorizes one correction after the APG81G checkpoint and places exact
integrated-versus-rollback qualification at the later integration gate where
those bytes exist. Fresh correction review found one Medium defect because the
frozen topology evidence did not bind the complete actual lifecycle map. The
attempted implementation and test bytes were discarded. ADR 0046 remains
Proposed and Node remains unintegrated at 33/32/32; no successor is authorized.

The resumed APG81H recovery provisionally integrates Node after correcting the
adjacent generic change-size fixture without changing production. Development
is 33/33/33, 14/19, and 31/1/32; ADR 0046 is Accepted with amendment, Node and
scratch debt are zero, and corrected public/active v0.4.0 remains unchanged.
No APG81I, APG82, or successor implementation is authorized.

## APG82 APGR foundation and frozen remaining scope

APG82 establishes the canonical `apgr` CLI and local Python distribution
foundation without publication. It owns configuration at `~/.apgr` (or
`APGR_HOME`) and `<project-root>/.apgr`, installed skill-resource discovery,
context-footprint measurement, one-primary terminal report delivery, numbered
response capture, compatibility shims, and exact current/historical release
separation.

Successful APG82 freezes all remaining v0.5 work to two separately authorized
phases:

1. APG83 dogfoods the retained product and packaged APGR CLI only against the
   already selected Knowledge Forge repositories and decides readiness without
   publication.
2. APG84, from an explicitly approved ready tree, builds and verifies the exact
   v0.5.0 Git and Python artifacts and performs approved GitHub and PyPI
   publication.

The v0.5 profile set is frozen. Astro, JSX, MDX, React, Vitest, and GoMock are
v0.6 scope, not APG83 prerequisites, unless APG83 identifies a material unowned
blocker requiring a fresh human decision. APG82 starts neither APG83 nor APG84.

## APG83 bounded dogfood and release readiness result

APG83 completes bounded dogfood against exact approved Knowledge Forge target
revisions and qualifies installed APGR, its configuration and terminal artifact
contracts, the public-Git release/PyPI-runtime split, deterministic Python
artifacts, and a reproducibly reconstructed local v0.5.0 release. The retained
twelve-row matrix has eleven passes, one deferred-v0.6/project-owner result, and
no material APG blocker. A deterministic sdist archive-metadata defect is fixed
within APG83.

The result is `READY_FOR_APG84`. APG84 publication remains separately
authorized. No publication, upload, Nix deployment, target mutation, maturity
promotion, v0.6 implementation, or successor execution occurs in APG83.

## APG84 public GitHub and PyPI publication

APG84 is the final authorized v0.5 phase. Its exact tracked candidate closes
the APG83 publication-enforcement concern with a two-root normalized Python
publication bundle and a published-release-only PyPI Trusted Publishing
workflow. The workflow verifies the triggering GitHub Release's exact wheel,
normalized sdist, and `SHA256SUMS` before publishing only the two distribution
files through an immutable official PyPA action commit.

Public Git refs, GitHub Release state, workflow execution, PyPI hashes, and
fresh public installation are external gates recorded in the canonical APG84
terminal report and response, not self-attested by tracked documentation. On
successful readback, v0.5 is finished. Nix deployment and v0.6 remain outside
APG84.
