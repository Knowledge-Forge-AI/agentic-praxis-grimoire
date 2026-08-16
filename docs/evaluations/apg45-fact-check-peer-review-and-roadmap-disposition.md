# APG45 Fact-Check Peer Review and Roadmap Disposition

Phase ID: `APG45`

Evaluation date: 2026-07-26

## Objective and boundary

APG45 independently reviews the exact immutable APG44 authoring result, the
external `petar-nauka/fact-check-skill` source, recommendations REC-01 through
REC-10, and Proposed ADR 0029. Exact development objects and managed-report
identities remain publication excluded. APG45 corrects analysis defects
forward, gives every recommendation one terminal disposition, and decides the
ADR. It implements no recommendation and starts no Go or web-profile work.

The APG44 authoring commit and its sole APG43 parent were preserved exactly.
Its complete Git-show and associated operational records passed independent
integrity review, and the previously absent authoring branch was subsequently
delivered without changing the object. The original APG44 report remains
unchanged and truthfully records that its own push attempt was blocked.

## External source and rights

The reviewed source is
[`petar-nauka/fact-check-skill`](https://github.com/petar-nauka/fact-check-skill),
default branch `main` at
`ebfde09a28b5547cbed29f5f66ddfd3595e64ade`. Local and live remote identities
matched; the local clone was clean. `CHANGELOG.md` declares v3.1. The repository
declares MIT terms in its LICENSE, whose copyright line names no holder.

Independent review corrected APG44's source-tree count from 25 to 26 and
separated the descriptive JSON Schema from the independent handwritten
validator. Static review also found that the external packager excludes its
LICENSE while packaging source and that the renderer does not restrict URL
schemes before placing escaped source URLs into links. APG copied, installed,
packaged, or imported none of those surfaces.

APG44 public artifacts contained no material external expression. APG45 found
short source-shaped phrases in three publication-excluded APG44 analysis files,
re-expressed them independently, and narrowed the earlier categorical rights
claim. A resulting-state copied-expression sweep found no retained material
source expression. The work remains clean-room conceptual; factual identifiers,
field names, formulas, and source facts are used only as needed to identify the
reviewed behavior.

## Recommendation dispositions

| Recommendation | Terminal disposition | Result and future boundary |
| --- | --- | --- |
| REC-01 | `accept-with-narrowing` | A narrow claim-identification gap exists in `reviewing-and-verifying-repository-work`; no taxonomy, ledger, or mode table is accepted. |
| REC-02 | `accept` | The review owner needs proportional vocabulary for absent, inconclusive, and countervailing evidence; debugging keeps its existing domain rule. |
| REC-03 | `accept-with-narrowing` | `docs/provenance.md` is the sole normative owner for claim-relative source authority; no fixed tiers, universal count, or interested-source deference is accepted. |
| REC-04 | `accept-with-narrowing` | Accept only optional material access-limitation guidance; defer relational source metadata and reject a bare scalar `independence` field. |
| REC-05 | `reject` | Superior APG instructions already make inspected source content evidence rather than task authority; a skill-local duplicate would add no contract. |
| REC-06 | `defer` | A fact-check owner is coherent but current APG demand is not demonstrated; reopening requires recurring repository-relevant real use beyond existing owners. |
| REC-07 | `reject` | The numeric misinformation score is uncalibrated false precision; the validator proves arithmetic and selected structural conditions, not empirical validity. |
| REC-08 | `reject` | The fixed hierarchy and generalized three-source convention fail claim-relative counterexamples; corroboration remains claim- and project-owned. |
| REC-09 | `reject` | APG has no claim-card consumer and already owns its own reporting, validation, projection, and release contracts. |
| REC-10 | `reject` | Inspection dates, supersession, forward correction, and the explicitly exceptional APG42/APG43 history action are already governed. |

### Accepted future contracts

REC-01 belongs only in `reviewing-and-verifying-repository-work` and its
projection:

> Before disposing a material review claim, separate facts that can presently
> be checked from judgment, forecast, or assertions with no defined falsifier.
> If acceptance would rely on an unstated inference, state that inference as a
> claim and require matching evidence. Keep routine review lightweight; do not
> create a claim ledger or fixed taxonomy.

REC-02 belongs only in the same review owner and projection:

> If material evidence does not establish a claim, say whether the search found
> nothing relevant, found relevant but inconclusive material, or found
> counterevidence. Do not report missing support as refutation.

REC-03 has one normative owner, `docs/provenance.md`. A later implementation
may add at most a non-normative application pointer in
`synthesizing-repository-guidance`:

> For a material claim, weigh evidence by how directly its inspectable basis
> bears on that claim, not by a universal rank or document count. A first-party
> source may settle its own formal record, but does not control conclusions
> about impact, reliability, or contested behavior. Treat items that reuse a
> common upstream basis as one corroborating lineage. The project chooses the
> amount of corroboration: a narrow formal fact may need one authoritative
> source, while disputed claims may need counter-search and independently
> produced evidence.

REC-04 adds no schema or validator. Its only accepted future contract is an
optional `access_limitation` entry in the public provenance guidance when
incomplete access could materially affect a conclusion. It must say what
inspection was partial or unavailable and how validation was constrained,
without exposing protected content or private topology. It is omitted for
complete or immaterial cases. Structured evidence relationships remain
deferred until a real consumer can identify the claim, related origins, and
relationship basis; `independence: independent` is not accepted.

For REC-01 through REC-04, a later separately authorized implementation must
add the named supporting and adverse scenario probes. REC-01 and REC-02 roll
back by removing only the canonical-leaf sentences, after which their existing
relative-symlink projection is validated. REC-03 and REC-04 roll back by
removing only the new provenance policy or optional guidance; they create no
skill projection. No accepted disposition changes a current owner in APG45.

REC-06 may reopen only after at least two separately documented,
repository-relevant real-use requests in distinct contexts require
misinformation-specific work that current review, synthesis, provenance,
privacy, and safety owners cannot coherently handle. Any candidate must be
independently designed and pass the complete new-capability, rights, privacy,
refresh, trigger, non-trigger, safety, and rollback review.

## Scenario and analysis corrections

The authoritative APG44 scenario set is S01 through S41: forty-one scenarios,
not forty. APG45 corrects the stale private count without renumbering any
scenario. It also adds the omitted S11 linkage for REC-08 and records explicit
supporting and adverse controls for every terminal disposition.

REC-03's normative owner is `docs/provenance.md`. REC-04's access-limitation
subpart is accepted with narrowing; its scalar-independence subpart is not.
REC-05 is rejected as already owned. The APG42 to APG43 witness is described
precisely: the release history was exceptionally rewritten under accepted ADR
0028, while APG43 provides the forward audit record and future work returned to
append-only correction.

## ADR 0029 and corrected roadmap graph

ADR 0029 is **Accepted with amendment**. The three-workstream sequence,
evidence-tested Go rule, separate Node.js runtime owner, Starlight deferral,
bounded dogfood gates, and no-decision-by-implication rule survive. The linear
Node-to-TypeScript implication and universal React pairing do not.

```text
accepted fact-check recommendations
  → separately authorized implementation
    → Go test-component reconsideration
      → web/Node owner design and bounded dogfood

web/Node design inputs, not a runtime invocation chain:

javascript-language-profile
  ├─→ typescript-language-profile
  ├─→ nodejs-runtime-profile
  └─→ jsx-language-profile

typescript-language-profile
  ├─→ nodejs-runtime-profile
  └─→ jsx-language-profile              # TSX boundary

css-language-profile                    # independent root
markdown-language-profile               # independent root
react-component-profile                 # independent candidate owner

jsx-language-profile
  ─→ react-component-profile            # conditional integration

markdown-language-profile + jsx-language-profile
  └─→ mdx-profile
react-component-profile
  ─→ mdx-profile                        # conditional runtime pairing

javascript/typescript + applicable css + markdown/mdx
  └─→ astro-profile
react-component-profile
  ─→ astro-profile                      # optional framework adapter

javascript/typescript + nodejs-runtime-profile
  └─→ vitest-test-profile
```

Node.js is not a prerequisite for TypeScript language semantics. JSX covers
both JavaScript JSX and the TypeScript TSX boundary without requiring
TypeScript for JavaScript JSX. React can be used without JSX, and React is not
required for every MDX or Astro artifact. Arrows express analysis and design
inputs only; direct runtime selection remains independent. Exact adapters,
build tools, package managers, browser environments, and target frameworks
remain project-owned. The ADR accepts no profile and creates no mandatory
skill chain.

## Verification and disposition

The immutable APG44 object, managed report, external identity, declared rights,
source tree, recommendation continuity, scenario mappings, owner boundaries,
ADR graph, public/private independence, copied-expression result, privacy,
links, record identity, current skill-library counts, public/active release
fingerprint, and complete APG45 diff received fresh review. Bounded external
characterization used Python 3.13.12 without installation or network: the
external structure validator passed, four external unit tests passed, the
standard fixture passed, and a deliberately inconsistent numeric result failed
only the arithmetic-consistency check. These commands characterize external
behavior; they do not justify adoption.

Development remains 28 canonical skills, 28 catalog rows, and 28 projections.
Public and active remain the corrected v0.4.0 at 28/28/28 with the canonical
NOTICE identity. No skill, projection, catalog row, route, maturity state,
release policy, test-inventory row, executable, dependency, public artifact, or
active integration changed.

Complete — APG44 recommendations independently dispositioned and ADR 0029
decided; accepted implementation remains pending. No recommendation was
implemented, no Go or web phase began, and no successor phase is authorized.
