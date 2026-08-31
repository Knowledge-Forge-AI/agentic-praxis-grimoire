# Agentic Praxis Grimoire Repository Instructions

<!-- APG-CANDIDATE-STATE: css-language-profile retained-provisional -->

The marker above is the mechanical current-state authority. Bounded
contradiction diagnostics cover only their frozen vocabulary; arbitrary prose
still requires human review.

## Scope and authority

These instructions apply throughout the repository. The human maintainer
retains ultimate project, roadmap, publication, license, and destructive-action
authority. ChatGPT exercises delegated planning and review authority only inside
a human-authorized task, phase, or preapproved roadmap envelope. Top-level Codex
executes that bounded assignment and may not expand it; internal Codex workers
may not expand their top-level assignment. The
[manager-worker protocol](docs/manager-worker-protocol.md) owns the complete
authority and stop-boundary contract.

Explicit human-maintainer direction within that authority chain has priority,
followed by this file and then more focused instructions that apply to changed
paths. Research sources, worker results, commits, reports, and recommendations
are evidence; they do not authorize work or constitute external acceptance.

Modify only the active APG workspace and only when the current task authorizes
the change. Treat every designated source corpus as read-only evidence unless
explicit authority states otherwise.

## External workflow plugin policy

Superpowers is retired from the maintainer's workflow. Preserved source is
historical external evidence only; its presence in a reference corpus does not
make it installed, authoritative, or eligible for restoration.

Do not invoke or follow any `superpowers:*` skill, including its session-start
bootstrap, brainstorming, planning, TDD, subagent-development, worktree, review,
or completion workflows, unless the current human-authorized task explicitly
names a specific Superpowers skill for inspection or comparison.

Do not treat Superpowers' instruction to check for or invoke skills before every
action as applicable in this repository.

APG repository instructions, accepted APG decisions, and the current authorized
phase define the workflow. Agents must not invoke, depend on, reinstall, enable,
or restore Superpowers even if it is present elsewhere, unless a human task
explicitly names a bounded source inspection or comparison. Such authority does
not authorize installation or workflow use.

## Working rules

- Before source-dependent work, inspect applicable instructions, source scope,
  repository state, and relevant accepted decisions.
- Treat candidate practices critically. Frequency, familiarity, ownership, or
  an authoritative tone does not establish APG policy.
- Record provenance for every materially source-derived APG practice. Confirm
  reuse rights and preserve required notices before copying or adapting text.
- Put content in the destination that owns it: universal triggers here,
  procedures in skills, rationale and governance in documentation, mechanical
  invariants in tools, and unadopted material in evidence records.
- Keep publishable files free of unpublished repository identities, private
  source topology, development commit identities, local paths, and private
  operational details. Put exact non-public evidence only in the
  publication-excluded area, and never create a public dependency on it.
- Use the canonical semantic phase ID assigned before implementation. Keep ADR
  and exit sequences independent and finalize current documentation and phase
  records before commit. Exact Git identities belong in managed reports,
  transient verification evidence, or explicitly authorized publication-
  excluded reproducibility records; they never replace durable public semantic
  identity or create a public dependency on `private/`. Follow the
  [phase and record identity guide](docs/phase-and-record-identity.md).
- For an APG formal-phase commit, write the complete message to a private file,
  validate it with `bin/apg-check-phase-commit-message --phase <PHASE-ID>
  --message-file <path>`, commit with `git commit -F <path>`, and validate the
  resulting commit with the same checker and `--commit <revision>` before
  generating reports. The checker validates message form; it grants no commit
  or continuation authority.
- Prefer deterministic checks for stable mechanical constraints. Do not call a
  prose requirement or one-time inspection tool-enforced.
- Validate instruction, skill, documentation, and tool changes in proportion to
  affected behavior. Keep documentation, tests, provenance, and implementation
  consistent.
- For ordinary implementation, start with scoped unit evidence and changed-
  boundary integration evidence. Broaden only for a recorded risk, focused
  failure, project checkpoint, or explicit requirement. Coverage remediation
  follows the useful-contract hierarchy and stop owned by
  `implementing-with-test-discipline` and the testing policy.
- For delegated work, follow the
  [manager-worker protocol](docs/manager-worker-protocol.md). Internal workers
  return through the agent harness; top-level phase reports follow the external
  assignment contract.
- When a phase requires managed Git and operational evidence, generate the Git
  show or Git diff record first and append the operational record to the same
  canonical phase report with its exact existing Git record ID. A standalone
  operational append is valid only when that report contains no Git record.
- A completion claim requires fresh evidence from the resulting repository
  state. A worker result, commit, or report is evidence, not automatic
  acceptance.

## Machine-local APG durable scratch

Repository-local `.scratch/` is ignored, machine-local APG durable scratch.
Future agents may inspect its local migration manifest when present, but must
never assume that state exists on another machine, commit or package it, or use
it for qualification/runtime temporary storage, which remains external to the
repository. Missing local scratch must result in reconstruction or an explicit
prerequisite, never a fabricated fact.

## Project map

- [Project model](docs/project-model.md): artifact ownership and practice
  lifecycle.
- [Provenance policy](docs/provenance.md): derivation, licensing, and adoption
  records.
- [Manager-worker protocol](docs/manager-worker-protocol.md): delegation,
  reporting, review, and disposition.
- [Structured project defaults](docs/structured-project-phase-defaults.md):
  formal/non-phase procedure and manager-assignment compression.
- [Testing and coverage policy](docs/testing-and-coverage-policy.md): scoped
  tests, remediation, real boundaries, and the adopted pytest architecture.
- [Agent reporting architecture](docs/agent-reporting-architecture.md):
  adopted Python Git show/diff and operational-report implementation, safety
  boundary, and rollback.
- [ChatGPT manager topology](docs/chatgpt-manager-skill-topology.md): implemented
  nested ownership and subrouting, plus personal transition gates.
- [Architecture decisions](docs/adr/README.md): accepted and superseded project
  decisions.
- [Exit records](docs/status/README.md): phase outcomes and next authorization.
- [Phase and record identity](docs/phase-and-record-identity.md): semantic phase
  IDs, independent sequences, durable references, and precommit finalization.
- [Skill library](skills/README.md): thirty-nine skill owners, fourteen stable
  and twenty-five provisional, and current scope.
- [Roadmap](docs/roadmap.md): completed phases and future authorization
  boundary.
- [v0.4 roadmap](docs/v0-4-roadmap.md): dependency-ordered implementation,
  transition, readiness, and release slices without automatic authority.
- [v0.5 roadmap](docs/v0-5-roadmap.md): fact-check evidence workstream, Go
  test-component reconsideration, and web/Node profile family without
  automatic authority.
- [v0.6 scope record](docs/v0-6-roadmap.md): six approved future profile
  candidates and explicit project-selected context/projection infrastructure
  without implementation authority.
- [v0.6 architecture contract](docs/architecture/v0-6-skill-ownership-and-context-budget.md):
  frozen six-profile scope, ownership and composition matrix, derived context
  budget, selection authority, and the bounded APG86–APG90 sequence.
- [v0.7 architecture contract](docs/architecture/v0-7-embeddable-toolkit.md):
  library-first Go ownership, APIs and schemas, distribution, task-scoped
  context, environment, hotspots, documentation IA, and APG95–APG103 sequence.
- [APG-JACA integration boundary](docs/architecture/apg-jaca-integration.md):
  direct Go imports, in-memory evidence, context/error behavior, and the strict
  orchestration/non-orchestration boundary.
- [v0.7 roadmap](docs/v0-7-roadmap.md): reporting, CLI, context, environment,
  analysis, packaging, documentation, readiness, and publication slices without
  automatic successor authority.
- [v0.8 architecture contract](docs/architecture/v0-8-context-footprint-and-skill-inventory.md):
  APGR-owned capacity, selection identity, footprint, projection, qualification,
  and JACA consumer-handoff boundaries without implementation authority.
- [v0.8 roadmap](docs/v0-8-roadmap.md): CAP0 and CXT0 architecture entries and
  dependency-ordered additive successors without automatic start authority.
- [APG85 architecture evaluation](docs/evaluations/apg85-v0-6-architecture-discoverability-and-context-budget.md):
  budget derivation from measured evidence, enforcement ownership, and the
  stated-but-unenforced limitation boundary.
- [APG86 GoMock and Vitest integration](docs/evaluations/apg86-gomock-vitest-profiles-and-context-budget-enforcement.md):
  provisional profile ownership, context-budget enforcement, conserved
  headroom, and the APG87 stop boundary.
- [APG87 JSX and React integration](docs/evaluations/apg87-jsx-react-profiles-and-apg88-headroom-conservation.md):
  provisional syntax/component ownership, boundary evidence, APG88 headroom
  conservation, and the no-successor boundary.
- [APG88 MDX and Astro integration](docs/evaluations/apg88-mdx-astro-profiles-and-v0-6-authoring-completion.md):
  provisional document/framework ownership, complete six-profile authoring,
  terminal context budget, and the no-successor boundary.
- [APG89 v0.6 readiness](docs/evaluations/apg89-v0-6-dogfood-composition-context-and-readiness.md):
  read-only target dogfood, deterministic cross-profile ownership, explicit
  selection, installed context and reproducibility, and bounded coverage
  determinism evidence.
- [APG94 v0.7 architecture](docs/evaluations/apg94-v0-7-embeddable-toolkit-architecture.md):
  source-first ownership and API freeze, migration/distribution decisions,
  resolver/environment/hotspot contracts, and the no-successor boundary.
- [APG95 Go reporting library](docs/evaluations/apg95-go-reporting-library-vertical-slice.md):
  root Go module, public in-memory report API, Python byte/error parity,
  publication safety, external import proof, and the APG96 stop boundary.
- [APG96 Go CLI and report bridge](docs/evaluations/apg96-go-cli-foundation-and-python-report-migration-bridge.md):
  root Go command, private build/CLI adapters, Python strangler migration,
  compatibility routing, and the APG97 stop boundary.
- [APG97 deterministic skill context bundles](docs/evaluations/apg97-deterministic-skill-context-bundles-and-agent-scoped-materialization.md):
  embedded canonical corpus, structured resolver, fail-closed budgets, isolated
  materialization, Go/Python consumer routes, and the APG98 stop boundary.
- [APG98 portable environment snapshots](docs/evaluations/apg98-portable-environment-snapshots-and-resolution.md):
  strict profiles and snapshots, explicit-map capture, locked no-churn storage,
  isolated/overlay resolution, `.flakes` parity, and the APG99 stop boundary.
- [APG99 structural hotspot analyzer](docs/evaluations/apg99-structural-hotspot-analyzer.md):
  provider-neutral read-only analysis, the frozen capability matrix, canonical
  machine reports, deterministic rankings and renderers, and the APG100 stop
  boundary.
- [APG100 Go strangler and multi-ecosystem distribution](docs/evaluations/apg100-complete-go-strangler-and-multi-ecosystem-distribution.md):
  Go-owned response capture, verified thin wrappers, reproducible target
  binaries, platform wheels, source distribution, npm packages, and the
  APG101 stop boundary.
- [APG101 human documentation restructuring](docs/evaluations/apg101-human-documentation-restructuring.md):
  concise landing-page onboarding, frozen task-oriented documentation owners,
  preserved phase archaeology, explicit v0.6-public/v0.7-candidate status, and
  the APG102 stop boundary.
- [APG104 v0.8 context-footprint and skill-inventory delivery](docs/evaluations/apg104-v0-8-context-footprint-and-skill-inventory.md):
  CAP0/CXT0 capacity and footprint contracts, additive package ownership,
  fail-closed evidence boundaries, and the current implementation/pre-final
  review boundary.
- [APG41 readiness evaluation](docs/evaluations/apg41-v0-4-readiness-and-pre-release-smoke.md):
  retained provisional dispositions, candidate smoke, limitations, and the
  publication boundary.
- [APG42 release evaluation](docs/evaluations/apg42-v0-4-release-publication-and-active-deployment.md):
  v0.4.0 publication, aggregate-owned active deployment, grouped limitations,
  and rollback boundary.
- [APG43 NOTICE correction evaluation](docs/evaluations/apg43-v0-4-notice-brand-correction.md):
  one-time identity correction, exceptional history action, and v0.5 boundary.
- [APG44 fact-check comparative analysis](docs/evaluations/apg44-fact-check-skill-comparative-analysis.md):
  external-source identity and rights, frozen recommendations, rejected
  patterns, and the Codex peer-review boundary.
- [APG45 fact-check peer review](docs/evaluations/apg45-fact-check-peer-review-and-roadmap-disposition.md):
  terminal recommendation dispositions, corrected rights/source facts, ADR
  0029 decision, and the pending-implementation boundary.
- [APG46 accepted evidence guidance authoring](docs/evaluations/apg46-accepted-evidence-guidance-authoring.md):
  candidate REC-01 through REC-04 review-skill and provenance authoring,
  clean-room result, and the pending Codex validation and integration
  boundary.
- [APG47 accepted evidence guidance integration](docs/evaluations/apg47-accepted-evidence-guidance-integration.md):
  failing-first correction, retained REC-01 through REC-04 contracts,
  no-pointer discoverability result, and the successor stop boundary.
- [APG48 Go test-harness dogfood and candidate authoring](docs/evaluations/apg48-go-test-harness-dogfood-and-candidate-authoring.md):
  five-repository bounded dogfood, the authored matryer/is candidate, the
  terminal no-stack result, Proposed ADR 0030, and the Codex review boundary.
- [APG49 matryer/is validation](docs/evaluations/apg49-matryer-is-validation-and-integration.md):
  exact-source and runtime validation, corrected-state deferral, Rejected ADR
  0030, and unchanged no-stack development state.
- [APG50 Web and Node architecture](docs/evaluations/apg50-web-and-node-profile-family-architecture.md):
  ten proposed owners, source baselines, frozen scenarios, and the Codex review
  boundary.
- [APG51 Web and Node peer review](docs/evaluations/apg51-web-and-node-architecture-peer-review.md):
  material corrected-state rights/corpus defects, ten candidate deferrals,
  Rejected ADR 0031, and the fresh-architecture boundary.
- [APG52 reproducible Web and Node evidence foundation](docs/evaluations/apg52-reproducible-web-node-evidence-foundation.md):
  exact-object corpus tooling, two-run reproducibility, named evidence
  limitations, unchanged candidate deferrals, and the no-successor boundary.
- [APG53 operational tooling and report hygiene](docs/evaluations/apg53-operational-tooling-and-report-hygiene.md):
  shared-skills projection tooling, report storage and project identity,
  current-tree evidence compaction, deterministic change-size policy, and the
  no-successor boundary.
- [APG54 global skill installer integration](docs/evaluations/apg54-global-skill-installer-integration.md):
  multi-repository Codex/Claude projection, combined ownership and rollback,
  current agent-root evidence, and the no-live-installation boundary.
- [APG55 global skill installer transaction hardening](docs/evaluations/apg55-global-skill-installer-transaction-hardening.md):
  partial-container rollback, explicit replacement stages, exact private-state
  reads, source identity revalidation, and the no-successor boundary.
- [APG56 Web and Node architecture reconstruction](docs/evaluations/apg56-web-and-node-architecture-reconstruction.md):
  fresh candidate dispositions on reproducible evidence, frozen band
  derivation, Proposed ADR 0034, and the pending independent-review boundary.
- [APG57 Web and Node architecture review](docs/evaluations/apg57-web-and-node-architecture-review.md):
  independent purpose and robustness falsification, corrected-state evidence
  defects, Rejected ADR 0034, and no eligible authoring slice.
- [APG58 CSS language-profile pilot](docs/evaluations/apg58-css-language-profile-pilot-authoring.md):
  one unintegrated CSS candidate under explicit policy-selected 300/600/900
  limits, Proposed ADR 0035, thirty frozen scenarios, and the pending
  independent-validation boundary.
- [APG59 CSS language-profile validation and integration](docs/evaluations/apg59-css-language-profile-validation-and-integration.md):
  failing-first correction, corrected-state executable/removal defects,
  Rejected ADR 0035, candidate cleanup, and the no-successor boundary.
- [APG60 CSS re-entry contract and removal foundation](docs/evaluations/apg60-css-reentry-contract-and-removal-foundation.md):
  sixty candidate-independent executable cases, complete current/historical
  owner closure, unchanged rejected CSS state, and the no-successor boundary.
- [APG60B CSS traceability and decision closure](docs/evaluations/apg60b-css-traceability-and-decision-closure.md):
  exact future traceability rows and clause anchors, mechanical narrative
  state, declared Python owner bindings, actual derived release values, and
  future ADR lifecycle closure without candidate authoring.
- [APG60C CSS runtime and terminal lifecycle closure](docs/evaluations/apg60c-css-runtime-and-terminal-lifecycle-closure.md):
  the historical owner-source finality claim later narrowed by APG60D,
  bounded narrative diagnostics, actual lifecycle gates, and direct regular
  survivor ownership without candidate authoring.
- [APG60D CSS source-binding and phase-history closure](docs/evaluations/apg60d-css-source-binding-and-history-closure.md):
  truthful static source-binding integrity, exact APG58 through APG62 phase
  bundles, future exits 00085/00086, and no candidate authoring.
- [APG60E CSS repository-path and candidate-surface closure](docs/evaluations/apg60e-css-repository-path-and-candidate-surface-closure.md):
  physical-root descriptor-relative authority reads, direct candidate-owner
  ancestry, exact projection provenance, future exits 00086/00087, and no
  candidate authoring.
- [APG60F CSS import, owner, and projection closure](docs/evaluations/apg60f-css-import-owner-and-projection-closure.md):
  closed repository imports, exact required-role authority, coherent
  projection observation, future exits 00087/00088, and no candidate
  authoring.
- [APG82 APGR foundation](docs/evaluations/apg82-apgr-cli-distribution-configuration-and-artifact-contract-foundation.md):
  canonical CLI and Python distribution, configuration, terminal outbox and
  response contracts, installed resources, and successor scope freeze.
- [APG83 v0.5 release readiness](docs/evaluations/apg83-v0-5-bounded-dogfood-and-release-readiness.md):
  bounded Knowledge Forge dogfood, installed-distribution qualification,
  reproducible Python artifacts, and the APG84 readiness disposition.
- [APG84 v0.5 publication](docs/evaluations/apg84-v0-5-public-github-and-pypi-publication.md):
  normalized publication-bundle enforcement, published-release-only Trusted
  Publishing, and external GitHub/PyPI readback boundaries.
- [Public release process](docs/public-release-process.md): exact projection,
  local candidate construction, validation, and publication boundary.
- [User-scoped skill integration](docs/user-scoped-skill-integration.md):
  public-sourced direct links, ownership, update, rollback, and migration.
- [Language-profile production recovery charter](docs/governance/language-profile-production-recovery-charter.md):
  human product authority, bounded iterative hardening, target-first
  acceptance, debt, rollback, and terminal-disposition boundaries.
## APG60A CSS contract foundation hardening

APG60A is the forward-correction owner for the APG60 CSS foundation. Its
public evaluation is
`docs/evaluations/apg60a-css-contract-foundation-hardening.md`; executable
owners remain under `src/test/fixtures/` and `src/test/support/`, and
publication-excluded evidence is under `private/evaluations/apg60a/`.
APG60A authors no candidate, allocates no ADR, and grants no APG61 authority.

## APG60B CSS pre-authoring closure

APG60B preserves the exact accepted APG60A behavior contract while hardening
the mechanics a future CSS candidate must satisfy. Contract maps bind every
row and stable clause anchor to that frozen contract; current narratives use
one exact maturity-aware state marker; Python owners bind exact declared
variables and isolated derived values; and future ADR 0036 has explicit
unused, retained, and rejected lifecycle rules. CSS remains absent, ADR 0036
remains unused, and APG61 remains recommended but unauthorized.

## APG60C CSS runtime and lifecycle closure

APG60C preserves accepted APG60B and closes newly reproduced owner-source
final-value, narrative-scope, historical-preservation, and current-survivor
false passes. Its owner-source finality claim is historical and was narrowed
forward by APG60D to truthful static source-binding integrity.
The authored Proposed but unintegrated state is positively gated before
APG61. Terminal rejection requires preserved history, and current survivors
must be direct regular files parsed as their declared type. The sixty-case
behavior contract is unchanged. APG60C authors no candidate, creates no ADR,
and grants no APG61 or successor authority.

## APG60D CSS source-binding and phase-history closure

APG60D preserves accepted APG60C while narrowing the Python proof to one exact
static declaration and mechanically identifiable protected-name write
refusal. Runtime value, arbitrary caller/callback/protocol mutation, and
general library-mediated reflective call effects are outside that syntactic
proof.
Every future lifecycle state requires exact direct-regular phase bundles:
APG58 through APG60D as foundation, APG61 for authored state, and APG61 plus
APG62 for retained or rejected state. APG60D authors no candidate, creates no
ADR, consumes exit 00084, and grants no APG61 or successor authority.

## APG60E CSS repository-path and candidate-surface closure

APG60E preserves accepted APG60D while requiring lifecycle authority inputs,
authored owners, and retained current owners beneath one resolved physical
repository root. Direct regular files use descriptor-relative no-follow
complete reads. The expected projection remains one exact relative symlink,
but its ancestors and canonical target must be direct repository owners.
APG58 through APG60E are the foundation; future APG61 and APG62 exits are
00086 and 00087. APG60E authors no candidate, creates no ADR, and grants no
successor authority.

## APG60F CSS import, owner, and projection closure

APG60F preserves accepted APG60E while closing transitive import provenance,
parent-cache and cross-root isolation, required-role self-deletion, and
projection/target observation gaps. All 52 required lifecycle roles and their
cross-references are exact. APG58 through APG60F are the foundation; APG61 and
APG62 advance to exits 00087 and 00088. CSS remains absent, ADR 0036 remains
unused, and APG60F grants no APG61 or successor authority.

## APG60G CSS snapshot, role, and derived-set closure

APG60G preserves accepted APG60F and closes replacement-root, cardinality-only
derived-set, coordinated required-role, and stale-authority false passes.
Dynamic consumers use a pinned root descriptor with parent-entry
revalidation; topology, library, and installer results match the complete
exact canonical skill set; the 52-role code-owned registry is independent of
the manifest and plan; and direct regular reads observe entry/descriptor/entry
around the complete read. APG58 through APG60G are the foundation; APG61 and
APG62 advance to exits 00088 and 00089. CSS remains absent, ADR 0035 remains
Rejected, ADR 0036 remains unused, and APG60G grants no APG61 or successor
authority.

## APG60H CSS snapshot and full-path binding closure

APG60H preserves Claude's immutable implementation and closes worker temporary
storage, exact snapshot cleanup, present/absent full-path observation, final
root binding, and projection identity. APG58 through APG60H are foundation;
future exits are 00089 and 00090. CSS remains absent, ADR 0036 unused, and no
APG61 or successor authority is granted.

## APG60I worker temporary-root binding and cleanup closure

APG60I preserves APG60H's maintainer-directed adoption and corrects its two
known worker temporary-storage exceptions forward. Worker child creation is
descriptor-relative to the retained no-follow temporary root, cleanup
ownership begins before creation, and final path-chain revalidation is
mandatory. APG58 through APG60I are foundation; APG61 and APG62 use exits
00090 and 00091. CSS remains absent, ADR 0036 unused, and no successor is
authorized.

## APG61 CSS language-profile authoring

APG61 authors one fresh `css-language-profile` candidate from the frozen
APG60A contract on the preserved Claude authoring branch: a clause-marked
leaf, a normative specification, and a sixty-case traceability map, with
ADR 0036 Proposed and indexed. The candidate is not integrated: no catalog,
projection, route, maturity, release, fixture, focused-test, or inventory
surface changed; current candidate-state markers remain absent; integrated
counts remain 28/28/28; and development `main` remains at exact APG60I.
APG62 validation (exit 00091) is recommended but separately authorized.

## APG62 CSS language-profile validation and rejection

APG62 independently delivered and validated exact APG61, reconstructed all
sixty frozen outcomes, reproduced seven initial semantic-navigation defects,
and used its one permitted coherent correction. Corrected-state review found
a new material six-case overreach in the `record-growth-state` obligation, so
ADR 0036 is Rejected and every current candidate artifact and validation-only
candidate test is removed. Current markers remain absent; development remains
28 canonical skills, 28 catalog rows, 28 projections, and 14 stable / 14
provisional rows. APG61 history is preserved, public, active, and target state
is unchanged, and no successor is authorized.

## APG63 Markdown architecture and lean contract

APG63 begins the next profile line after the terminal CSS rejection, which
remains terminal: CSS is not retried or repaired, and ADR 0036 stays
Rejected. It reconstructs Markdown architecture from exact CommonMark
0.31.2, pinned GFM, rights, corpus, and target evidence; defines a narrowed
coherent Markdown owner with closed raw-HTML, frontmatter, and MDX
boundaries; selects qualitative structure-first structural policy
(disposition C, no numeric whole-file bands) under ten pre-frozen purpose
controls; freezes a lean thirty-six-scenario candidate-independent
contract; and proposes ADR 0037. No skill is authored and nothing is
integrated: development remains 28/28/28 with 14 stable / 14 provisional,
and public, active, and target state are unchanged. The eligibility result
is authoring-eligible-with-narrowing; Codex peer review (recommended
APG64) terminally decides ADR 0037 and is separately authorized.

## APG64 Markdown architecture peer review

APG64 preserves and remotely delivers exact APG63, independently reverifies
Markdown sources, rights, target parsers, and all tracked target Markdown,
then replays all thirty-six scenarios. One coherent forward correction closes
the initial owner/routing/response, determinism, process-separation,
structural-policy, dialect-hierarchy, corpus, and rights defects. Fresh review
finds no new material defect, so ADR 0037 is Accepted with amendment and the
architecture remains authoring-eligible-with-narrowing. No Markdown skill is
authored or integrated; development remains 28/28/28 and 14/14; no successor
is authorized.

## APG65 Markdown language-profile candidate authoring

APG65 starts from exact APG64 and authors one fresh branch-only
markdown-language-profile candidate: an operational leaf, a complete
candidate specification, and a navigation-only scenario-coverage record,
bound by twenty-four stable clause IDs and mapped to all thirty-four
candidate-semantic scenarios. ADR 0038 is Proposed; the candidate is
branch-only, Proposed, unintegrated, and pending separately authorized APG66
validation. The accepted ADR 0037 architecture is unchanged, no numeric
whole-file band exists, no integration owner changes, and development main
remains 28/28/28 and 14/14. No successor is authorized.

## APG66 Markdown language-profile validation and integration

APG66 preserves and remotely delivers exact APG65, independently rebuilds all
thirty-four accepted semantic scenarios, applies one coherent correction, and
preserves the exact corrected patch before fresh review. ADR 0038 is Accepted
with amendment and `markdown-language-profile` is retained provisionally.
Development is 29/29/29 with 14 stable / 15 provisional, 27 general routes,
one ChatGPT-local route, and 28 checked edges. ADR 0037 remains Accepted with
amendment; rejected CSS decisions remain closed. Public and active corrected
v0.4.0 and both read-only targets remain unchanged. No readiness, publication,
deployment, APG67, or successor is authorized.

## APG66A Markdown replay-evidence truth

APG66A preserves APG66's candidate, decision, integration, and fresh human
semantic review while correcting the maintained automated proof claim. Exact
APG64 register-fixture projection, mechanical navigation, and mutation-proven
targeted guards replace fixture self-copy and global-token false passes. The
profile remains retained provisional at 29/29/29, 14/15, and 27/1/28; public,
active, targets, and ADR statuses remain unchanged. APG67 is recommended but
not begun, and no successor is authorized.

## APG66B Markdown register-vocabulary and guard exactness

APG66B preserves APG66 and APG66A while correcting five bounded automated-
evidence gaps. One independently hash-bound APG64 vocabulary owner requires
exact ordered arrays; one shared lexical primitive rejects closed tokens inside
larger hyphenated or underscored strings; source guards retain seventeen
bounded local claims with polarity negatives; the row 032/034 rollback-class
distinction remains human-reviewed; and descriptive or expressly negative
counts remain allowed while normative count policy is rejected. Candidate and
ADR semantics remain unchanged. Markdown stays retained provisional at
29/29/29, 14/15, and 27/1/28. APG67 is recommended at exit 00098 but not begun,
and no successor is authorized.

## APG66C Markdown clause-polarity and predicate-binding closure

APG66C closes coordinated numeric-subject inheritance, subject-first rollback
obligations, and direct source, signal, and targeted-guard contradictions. Its
continuation also replaces one order-sensitive whole-process module-cache test
claim with bounded inspected-repository state evidence while preserving the
production importer and APG60F/APG60G isolation. Markdown remains retained
provisional; accepted candidate and ADR semantics are unchanged. APG67 is
recommended at exit 00099 but not begun, and no successor is authorized.

## APG66D Repository-import cache entry-presence closure

APG66D preserves accepted APG66C and corrects one bounded test-evidence gap:
the relevant-state helper now requires a pre-existing `sys.modules` key to
remain present before comparing its stored object by identity. A present
`None` sentinel therefore cannot be confused with a missing key. The
production repository importer, Markdown candidate semantics, accepted ADRs,
and retained integration are unchanged. APG67 is recommended at exit 00100
but not begun, and no successor is authorized.

## APG67 JavaScript language-profile architecture

APG67 proposes the JavaScript language-profile architecture and lean
validation contract under ADR 0039 (Proposed) on the Claude architecture
branch: ECMAScript 2026 (17th edition) is the stable annual reference, the
2027 draft is moving evidence only, JavaScript/TypeScript/Node.js remain
separate owners, structural policy is qualitative disposition C, and the
frozen register holds thirty-eight semantic scenarios plus two process
invariants. Authoring eligibility is `authoring-eligible-with-narrowing`;
no skill or integration owner changes and development remains 29/29/29.
APG68 is recommended at exit 00101 but not begun, and no successor is
authorized.

## APG68 JavaScript architecture peer review

APG68 preserves and delivers exact APG67, independently reverifies the
annual standard, errata, rights, Test262, targets, and corpus, and applies
one coherent source-authority, vocabulary, routing, scenario, and evidence-
truth correction. Fresh semantic review finds material defects after the
sole correction, so ADR 0039 is Rejected and eligibility is
`not-applicable-rejected`. No JavaScript skill or integration owner changes,
and development remains 29/29/29, 14/15, and 27/1/28. APG69 is not
recommended or begun, and no successor is authorized.

## APG69 JavaScript core architecture reset

APG69, under new human authority, proposes a fresh JavaScript core
architecture and layered validation contract under ADR 0040 (Proposed):
a narrower ECMAScript-core owner, question-specific typed authorities,
four separated decision layers with an ordered effective route union,
and independent semantic (24), structural (10-signal), composition (8),
and process (2) registers. ADR 0039 remains Rejected and unchanged.
Eligibility is `authoring-eligible-with-narrowing` with no
candidate-authoring authority. No JavaScript skill or integration owner
changes; development remains 29/29/29, 14/15, and 27/1/28. Separately
authorized APG70 terminally decides ADR 0040; no successor is
authorized.

## APG70 JavaScript core layered-architecture peer review

APG70 preserves and normally delivers exact APG69, independently reconstructs
the oracle, freezes the complete initial material set, and applies one coherent
correction. Three fresh non-author lanes find new material source-truth,
signal, context-route, policy-typing, proof, and adjacent-owner defects after
that sole correction. ADR 0040 is Rejected and eligibility is
`not-applicable-rejected`; the architecture is historical evidence, not current
authoring input. No JavaScript skill or integration owner changes; development
remains 29/29/29, 14/15, and 27/1/28. APG71 is not recommended or begun, and
no successor is authorized.

## APG71 TypeScript architecture and compiler-generation boundary

APG71, under separate new human authority scoped to TypeScript architecture
only (APG70's non-recommendation remains controlling for JavaScript
candidate authoring), proposes ADR 0041 on the Claude architecture branch:
an independent TypeScript static-semantics owner under project-selected
exact compiler authority, a first-class TypeScript 6/7 compiler-generation
boundary, closed `.tsx`/checked-`.js`/embedded-host/declaration boundaries,
a lean candidate-independent contract with eleven closed vocabularies, 22
semantic and 12 boundary rows plus 2 process invariants, structural
disposition D (deferred), and eligibility
`authoring-eligible-with-narrowing` with no candidate-authoring authority
granted. ADR 0039 and ADR 0040 remain Rejected; no TypeScript or JavaScript
skill exists; development remains 29/29/29, 14/15, and 27/1/28. Separately
authorized APG72 terminally decides ADR 0041; no successor is authorized.

## APG72 TypeScript architecture peer review

APG72 preserves and normally delivers exact APG71, independently reconstructs
the oracle and source/target evidence, freezes the complete initial material
set, and uses one coherent correction. Two fresh non-author lanes find new
material owner/route, role-state, source-kind, and present/required-evidence
defects after that sole correction. ADR 0041 is Rejected and eligibility is
`not-applicable-rejected`; the architecture and corrected registers are
historical evidence, not current authoring input. No TypeScript or JavaScript
skill or integration owner changes; development remains 29/29/29, 14/15, and
27/1/28. APG73 is not recommended or begun, and no successor is authorized.

## APG73 language-profile production recovery charter

APG73 exercises new human governance authority without changing APG72's
historical result. ADR 0042 is Accepted; the production-recovery charter and
iterative hardening contract retire automatic rejection after one correction
for future recovery work. One coherent correction remains one round, with up
to three separately preserved rounds by default; repairable remaining defects
normally yield `repair-required`. Critical and High defects block integration,
Medium and Low debt must be explicit and human accepted, and terminal
rejection or removal requires human authority. TypeScript is essential, CSS
and JavaScript are desirable, JSX is deferred, TypeScript 7 is the intended
primary generation, and temporary TypeScript 6 is role-bound. No profile or
integration owner changes; development remains 29/29/29, 14/15, and 27/1/28.
Markdown, rejected ADRs, public/active v0.4.0, and targets remain unchanged.
APG74 is recommended but not begun, and no successor is authorized.

## APG74 TypeScript language-profile candidate

APG74 authors the first product-recovery candidate under accepted ADR 0042:
one narrow TypeScript language-profile leaf, one candidate specification, one
navigation-only scenario-coverage record (24 scenarios, 24 stable clauses),
and one APG-owned TypeScript 7 intended-state fixture (14 cases with a
canonical manifest and scratch-verified smoke checks). ADR 0043 is Proposed;
the candidate is authored-proposed-unintegrated on the APG74 branch, whose
transitional 30/29/29 shape is expected and truthful. The exact stable
compiler is freshly selected (`typescript@7.0.2`, source-bound to
`microsoft/typescript-go`); the TypeScript 6 compatibility disposition is
`not-required` with a recorded refresh condition; and the freshly pinned
theme target's older checker line is migration-baseline evidence, not the
destination. Integrated development remains exact APG73 at 29/29/29, 14/15,
and 27/1/28; no integration owner changes; Markdown, rejected ADRs,
public/active v0.4.0, and targets remain unchanged. APG75 (exit 00108,
terminal ADR 0043 decision) is recommended but not begun, and no successor
is authorized.

## APG75 TypeScript iterative hardening and provisional integration

APG75 preserves exact APG74 and completes three separately reviewed correction
rounds under ADR 0042. The final fresh review returns zero Critical, High,
Medium, or Low findings, so ADR 0043 is Accepted with amendment and
`typescript-language-profile` is retained provisionally. Development is
30/30/30 with 14 stable / 16 provisional rows and 28 general / 1 ChatGPT-local
/ 29 checked routes. Exact TypeScript 7 remains the intended primary
generation; TypeScript 6 remains conditional and role-bound. Historical
corrected v0.4 reconstruction, public/active v0.4.0, Markdown, rejected ADRs,
and read-only targets remain unchanged. No readiness, publication, deployment,
target mutation, stable maturity, APG76, or successor is authorized.

## APG75A TypeScript scope and lifecycle closure

APG75A preserves exact APG74/APG75 history and keeps ADR 0043 Accepted with
amendment. The reusable profile consumes project-selected compiler role,
version, and migration policy; Theme Forge's TypeScript 7 destination remains
project-specific. Selection and the exact four-value Response axis are
disjoint, current fixture/coverage lifecycle is provisionally integrated, and
standard tests require an explicitly bound exact TypeScript 7.0.2 compiler.
Development remains 30/30/30, 14/16, and 28/1/29. APG76 is recommended at
exit 00110 but is not authorized or begun.
## APG76 CSS candidate recovery

APG76 authors one fresh reusable CSS language-profile candidate and one
APG-owned fourteen-case target-first fixture on a Claude branch, and integrates
nothing. ADR 0044 is Proposed; ADR 0035 and ADR 0036 remain Rejected and the
APG61 and APG62 objects are preserved unchanged. The structural-policy
disposition is deferred: qualitative signals route review to the project-design
owner and never decide failure. No parser or transformer smoke ran, because no
exact current target CSS tool role is selected. Integrated development remains
30/30/30, 14/16, and 28/1/29; the Claude branch is transitionally 31/30/30.
APG77 is recommended at exit 00111 but is not authorized or begun.

## APG77 CSS iterative hardening repair checkpoint

APG77 normally delivers exact APG76 and uses all three separately preserved
hardening rounds under ADR 0042. Fresh terminal review finds zero Critical,
two High, zero Medium, and zero Low defects: exact target hash/path-object
retention and two separately complete independent oracle vectors remain open.
ADR 0044 stays Proposed and the candidate is preserved `repair-required`;
CSS remains unintegrated and development remains 30/30/30, 14/16, and
28/1/29. No rejection, removal, stable maturity, public/active change, target
mutation, APG78, or successor is authorized. A human continuation decision is
required.

## APG77A CSS evidence-retention repair checkpoint

APG77A exercises the explicit human continuation for one narrow fourth
correction and preserves complete target identity evidence plus two separately
complete 45-purpose lanes. Fresh immutable-correction review finds zero
Critical, three High, zero Medium, and zero Low defects: a wrong SVG authority,
false-pass H2 qualification, and copied target bytes. ADR 0044 remains Proposed,
CSS remains `repair-required` and unintegrated, and development remains
30/30/30, 14/16, and 28/1/29. Main, public/active corrected v0.4.0, and targets
remain unchanged; APG78 is not recommended and no successor is authorized.

## APG77B CSS traceability and clean-room repair checkpoint

APG77B exercises the explicit human H3-H5 continuation and preserves one
immutable traceability and clean-room correction. Four-lane fresh review finds
zero Critical, four High, two Medium, and zero Low defects: adjudication
semantics, generated-report target overlap, escaped-copy detection, immutable
diff binding, distinct same-owner-obligation qualification, and artifact
proportionality remain open. No debt is accepted. ADR 0044 remains Proposed,
CSS remains `repair-required` and unintegrated, and development remains
30/30/30, 14/16, and 28/1/29. Main, public/active corrected v0.4.0, and targets
remain unchanged; APG78 is not recommended and no successor is authorized.

## APG77C CSS evidence-proportionality repair checkpoint

APG77C exercises explicit human proportionality authority and preserves one
immutable P1-P6 correction. It clarifies the private historical Git-patch
exception, narrows current proof to compact consequence-bearing evidence, and
states six exact supported no-copy forms. Fresh review finds zero Critical,
zero High, six Medium, and one Low qualification defects with no accepted debt.
ADR 0044 remains Proposed, CSS remains `repair-required` and unintegrated, and
development remains 30/30/30, 14/16, and 28/1/29. Main, provisional TypeScript
and Markdown, corrected public/active v0.4.0, and targets remain unchanged;
APG78 is not recommended and no successor is authorized.

## APG77D CSS known-debt integration

APG77D exercises explicit human authority for exactly four Medium and one Low
CSS qualification limitations, accepts no Critical/High or semantic, source,
target, runtime, release, or rollback debt, and closes live proportionality,
lifecycle, release, historical-exclusion, and disposable-rollback gates. ADR
0044 is Accepted with amendment; CSS is
`provisionally-integrated-with-known-debt` at 31/31/31, 14 stable / 17
provisional, and 29 general / one ChatGPT-local / 30 checked routes. Stable
maturity remains blocked. TypeScript and Markdown remain provisional; public,
active, and target state remains unchanged. APG78 is recommended but not begun,
and no successor is authorized.

## APG79 JavaScript core hardening repair checkpoint

APG79 preserves exact APG78, completes its associated operational report, and
uses all three default ADR 0042 correction rounds. Fresh terminal review finds
zero Critical, two High, two Medium, and zero Low material defects with no
accepted JavaScript debt. ADR 0045 remains Proposed and
`javascript-language-profile` is preserved `repair-required-after-round-3`
without catalog, projection, maturity, route, project, release, or test-
inventory integration. Development remains exact APG77D at 31/31/31, 14/17,
and 29/1/30. CSS known debt, provisional CSS/TypeScript/Markdown, corrected
public/active v0.4.0, and targets remain unchanged. APG80 is not recommended or
begun; further JavaScript work requires a new human continuation decision.

## APG79A JavaScript terminal-proof repair checkpoint

APG79A exercises the separate human continuation decision after APG79 and
preserves one immutable H1/H2/M1/M2 correction. Four fresh non-author lanes find
zero Critical, zero High, five Medium, and zero Low material defects with no
accepted JavaScript debt. ADR 0045 remains Proposed and
`javascript-language-profile` is `repair-required-after-apg79a` without any
catalog, projection, maturity, route, project, release, or test-inventory owner.
Development remains exact APG77D at 31/31/31, 14/17, and 29/1/30. CSS known
debt, provisional CSS/TypeScript/Markdown, public/active corrected v0.4.0, and
targets remain unchanged. APG80 is not recommended or begun; further action
requires a new human decision.


## APG79B JavaScript contract and harness repair checkpoint

APG79B exercises a second separate human continuation decision for exactly the
five APG79A Medium findings and preserves one immutable correction. Five fresh
non-author lanes find zero Critical, zero High, four unique Medium, and zero Low
material defects: incomplete CommonJS stop-vector closure, traceback-retained
engine streams, two further static alias bypasses, and missing root-scalar
wrong-value mutations. ADR 0045 remains Proposed and
`javascript-language-profile` is `repair-required-after-apg79b` without any
integration owner. Development remains exact APG77D at 31/31/31, 14/17, and
29/1/30. No JavaScript debt is accepted; main, CSS debt, public/active v0.4.0,
and targets remain unchanged. APG80 is not recommended; further action requires
a new human decision.

## APG79C JavaScript human-debt decision and integration checkpoint

APG79C records the maintainer's explicit acceptance of exactly `JS-QD-001`
through `JS-QD-004` as Medium qualification debt for provisional integration
only. Zero Critical or High JavaScript debt and no semantic, normative-source,
target, owner, release, or rollback debt is accepted. Fresh source preflight
found a separate unaccepted Medium Test262 identity discrepancy, so integration
stopped. ADR 0045 remains Proposed and `javascript-language-profile` remains
`repair-required-after-apg79b` and unintegrated. Development remains exact
APG77D at 31/31/31, 14/17, and 29/1/30; CSS debt, public/active v0.4.0, and
targets are unchanged. APG80 is not recommended; further action requires a new
human decision.

## APG79E JavaScript report-binding debt and provisional integration

APG79E exercises explicit human authority for exactly one additional Medium
qualification limitation, `JS-QD-005`, without claiming the maintained report-
binding proxy is repaired. Direct current APG79B report verification supplies
the bounded workaround. Zero Critical or High and zero unaccepted Medium or Low
findings remain. ADR 0045 is Accepted with amendment and
`javascript-language-profile` is provisionally integrated with exactly
`JS-QD-001` through `JS-QD-005`. Development is 32/32/32, 14 stable / 18
provisional, and 30 general / one ChatGPT-local / 31 checked routes. Test262
remains non-normative rights-only evidence with no corpus or oracle use. CSS,
TypeScript, and Markdown remain provisional; public/active corrected v0.4.0 and
targets remain unchanged. APG80 is recommended but not begun.
APG80 authors one narrow reusable `nodejs-runtime-profile` candidate, its
specification, a navigation-only twenty-four-scenario coverage record, a
fourteen-case APG-owned target-first Node fixture, and Proposed ADR 0046 on a
Claude authoring branch. The candidate consumes an exact project-selected
runtime role and selects none; it hard-codes no Node version and keeps a
declared range, a package-manager declaration, a continuous-integration release
line, an exact version, and an invocation as separate facts. Node structural
policy is deferred. APG80 integrates nothing, adds no debt, and preserves
`CSS-QD-001` through `CSS-QD-005` and `JS-QD-001` through `JS-QD-005` exactly.
Mainline development remains 32/32/32, 14 stable / 18 provisional, and 30
general / one ChatGPT-local / 31 checked routes; the candidate branch is
transitionally 33/32/32. APG81 is recommended but not begun.

## APG81 Node.js hardening repair checkpoint

APG81 preserves three immutable correction rounds. Fresh terminal review of
exact Round 3 finds zero Critical, three High, two Medium, and zero Low material
qualification-harness defects. The default three-round correction budget is
exhausted, no Node debt is accepted, ADR 0046 remains Proposed, and
`nodejs-runtime-profile` is `repair-required-after-round-3` without any
integration owner. The candidate branch remains 33/32/32 while development
main remains exact APG79E at 32/32/32, 14 stable / 18 provisional, and 30
general / one ChatGPT-local / 31 checked routes. Existing CSS and JavaScript
debt, corrected public/active v0.4.0, and targets remain unchanged. Further
Node work required an explicit human continuation decision.

## APG81A Node.js threat-model correction checkpoint

APG81A retires the disproportionate immutable-flag and copied-runtime sealing
machinery, narrows qualification to controlled local or CI use, and preserves
direct exact-runtime pre/post observation, private invocation scratch, bounded
diagnostics, and attempt-all cleanup. The immutable correction passes fresh
review with zero findings and zero Node debt. A later integration candidate
stops on one High rollback defect and one Medium contradictory ADR-index
lifecycle defect, so ADR 0046 remains Proposed and `nodejs-runtime-profile`
remains corrected, repair-required, and unintegrated. Main remains exact APG79E
at 32/32/32, 14/18, and 30/1/31; the candidate branch remains 33/32/32. A new
human decision is required; APG82 and successor work are not begun or
authorized.

## APG81B Node.js integration-contract clarification checkpoint

APG81B clarifies that a candidate-preserving Node rollback must target
33/32/32 rather than delete the candidate to force 32 canonical skills. Five-
scope staged review of the reconstructed integration finds zero Critical, zero
High, three Medium, and zero Low defects with zero Node debt: retained rollback
lifecycle disagreement, staged-review/message contradiction, and one
unauthorized frozen-test correction. All attempted integration bytes are
removed. ADR 0046 remains Proposed and `nodejs-runtime-profile` remains
corrected, repair-required, and unintegrated. Main remains exact APG79E at
32/32/32, 14/18, and 30/1/31; the candidate branch remains 33/32/32. Further
work requires a new human decision; APG82 and successor work are not authorized.

## APG81C Node.js integration-support repair checkpoint

APG81C is the explicit human continuation after APG81B. Its single support
correction defines coherent candidate-preserving post-acceptance rollback,
keeps final staged-review evidence external to the tree it reviews, makes the
timeout cleanup test assert only its own invocation root, and establishes the
ignored machine-local `.scratch/` policy after auditing the shared purge root.
Fresh precommit review of the human-authorized extra correction returns zero
findings and zero Node debt. Immutable correction review then finds one Medium
contradiction between retained pending-review prose and the completed review,
commit, and report evidence. APG81C stops before integration at a terminal
repair checkpoint. The correction is retained, but no current Node integration
owner changes; ADR 0046 remains Proposed and Node remains repair-required and
unintegrated. APG82 and successor work remain unauthorized.

## APG81D Node.js repo-local scratch integration checkpoint

APG81D exercises explicit human authority for one reconstructed provisional-
integration attempt and a temporary ignored repo-local scratch boundary. Full
regression and deterministic release construction complete, but final staged
review of the exact integration candidate finds zero Critical, one High, three
Medium, and zero Low defects: rollback retains integrated-count test contracts,
the current specification contradicts its integration state, one scratch Git
query can fail open, and exact phase-root cleanup evidence is absent. All
attempted integration, product, harness, and test bytes are discarded. ADR 0046
remains Proposed; Node remains repair-required and unintegrated at 33/32/32;
exact APG79E main remains 32/32/32, 14/18, and 30/1/31. Zero Node or scratch
debt is accepted. APG82 and successor work are not authorized.

## APG81E Node.js final-integration review checkpoint

APG81E exercises the explicit human continuation after APG81D and reconstructs
the rollback-test, lifecycle, scratch, release, and provisional-integration
candidate. Full integrated and candidate-preserving rollback selections and
deterministic release reconstruction complete, but final staged review finds
zero Critical, one High, two Medium, and zero Low defects: the rollback test-
owner projection remains incomplete and self-attested, phase chronology is
misplaced, and the fresh Node release-schedule identity set is missing from the
phase evidence. Every attempted integration, product, harness, test, release,
and lifecycle-owner byte is discarded. ADR 0046 remains Proposed; Node remains
repair-required and unintegrated at 33/32/32; exact APG79E main remains
32/32/32, 14/18, and 30/1/31. Zero Node or scratch debt is accepted. APG82 and
successor work are not authorized.

## APG81F Node.js actual-test-projection repair checkpoint

APG81F exercises the explicit human continuation after APG81E and attempts the
single authorized H1/M1/M2 correction. Fresh review of the complete frozen
correction finds zero Critical, three High, two Medium, and zero Low defects:
ambient pytest selectors can omit nodes from both collections; required
integrated and rollback executions are absent; a release-selected test imports
an unreleased Node helper; chronology validation is self-maintained and
incomplete; and the phase source record omits mandatory exact identities. The
attempted implementation and test bytes are discarded. ADR 0046 remains
Proposed; Node remains repair-required and unintegrated at 33/32/32. Zero Node
or scratch debt is accepted. No integration, main adoption, APG82, or successor
work is authorized.

## APG81G Node.js selector, release, and integration closure

APG81G exercised explicit human continuation after APG81F and attempted one
bounded correction. Fresh review found two High and four Medium defects, so all
attempted implementation and test bytes are discarded. ADR 0046 remains
Proposed and Node remains retained, repair-required, and unintegrated at
33/32/32. No Node or scratch debt is accepted. No integration, main adoption,
APG82, or successor is authorized.

## APG81H Node.js reviewable qualification and integration closure

APG81H is the explicit human continuation after APG81G. It authorizes one
bounded correction of the repo-local task-scratch boundary, replacement-ref
chronology, exact Node-only topology-transition proof, and the APG81F source-
evidence omission ledger. Fresh correction review found one Medium defect: the
frozen baseline recorded catalog maturity but did not bind the complete actual
language-profile lifecycle map, including Node's repair-required lifecycle.
The attempted implementation and test bytes were discarded. ADR 0046 remains
Proposed; Node remains retained, repair-required, and unintegrated at 33/32/32.
No debt, integration, main adoption, target execution, APG82, or successor is
authorized.

The resumed APG81H recovery corrects the adjacent change-size negative fixture
without changing change-size production, then provisionally integrates the
retained Node.js profile. The resulting development topology is 33/33/33,
14 stable / 19 provisional, and 31 general / one ChatGPT-local / 32 checked
routes. Node lifecycle is `provisionally-integrated`, ADR 0046 is Accepted with
amendment, and Node and scratch debt remain zero. This grants no stable
maturity, readiness, publication, deployment, APG81I, APG82, or successor
authority.

## APG82 APGR CLI, distribution, configuration, and artifact foundation

APG82 establishes the canonical `apgr` Python CLI, the publishable
`agentic-praxis-grimoire` / `agentic_praxis_grimoire` distribution foundation,
packaged checkout-independent skill discovery and context measurement, bounded
global/project configuration, one-primary outbox reports, and immutable
numbered response capture. Maintained executable names remain compatibility
shims. The future adapter path is reserved at
`~/.apgr/agentic-praxis-grimoire-nd/` but no adapter, Nix integration, or live
deployment is created.

APG82 changes no profile semantics, maturity, or known debt. Current development
remains 33/33/33, 14 stable / 19 provisional, and 31 general / one
ChatGPT-local / 32 checked routes; Node and scratch debt remain zero and the
five CSS plus five JavaScript debt entries remain exact. Corrected historical
v0.4 identity remains isolated. APG83 bounded dogfood and readiness is
recommended next but separately authorized; APG82 grants no publication,
deployment, APG83, APG84, or v0.6 implementation authority.

## APG83 v0.5 bounded dogfood and release readiness

APG83 exercises retained v0.5 guidance against exact approved Knowledge Forge
target revisions and qualifies installed APGR, the Git-release/PyPI-runtime
split, deterministic Python artifacts, and the reconstructed local v0.5.0
release. The twelve-row dogfood matrix has eleven passes and one deferred-v0.6
boundary. Terminal Nova's frozen-install failure is a pre-existing target
manifest/lockfile defect, not an APG defect.

APG83 corrects one deterministic sdist archive-metadata defect without changing
profile semantics, maturity, routes, or debt. Development remains 33/33/33,
14/19, and 31/1/32; Node and scratch debt remain zero, and the exact ten CSS
and JavaScript debt entries remain unchanged. Corrected historical v0.4 stays
exact and isolated. APG84 publication is recommended but separately authorized;
APG83 performs no publication, upload, deployment, target mutation, stable
promotion, v0.6 implementation, or APG84 execution.

## APG84 v0.5 public GitHub and PyPI publication

APG84 closes the APG83 publication-enforcement concern with one exact
two-root Python publication-bundle owner and a published-GitHub-Release-only
Trusted Publishing workflow. Both raw sdists pass through the maintained
normalizer at epoch `1700000000`; only a byte- and mode-reproducible wheel,
normalized sdist, and `SHA256SUMS` bundle is eligible for GitHub upload. The
workflow verifies those exact release assets before giving only the two
distribution files to the immutable official PyPA action.

The tracked APG84 source and exit record do not self-attest external
publication. The canonical terminal report and numbered response own actual
GitHub refs, release assets, workflow outcome, PyPI hashes, and public install
readback. Successful readback finishes v0.5. APG84 grants no Nix deployment,
adapter creation, active skill migration, v0.6, target mutation, private-remote
push, or announcement authority.

## APG85 v0.6 architecture, discoverability, and context budget

APG85 is the first v0.6 phase and is architecture and documentation only. ADR
0047 freezes the exact six-profile scope — `astro-profile`,
`jsx-language-profile`, `mdx-profile`, `react-component-profile`,
`vitest-test-profile`, and `gomock-test-profile` — with a no-seventh rule, gives
each an owns, does-not-own, and composes-with boundary, and adds a deterministic
composition rule under which the narrowest applicable owner answers and ties
resolve by a stated layer order from document to mock library.

The context budget is derived from the measured 22-profile corpus rather than
chosen by intuition: two descriptions exceeding twice the 173-byte minimum are
treated as outliers, and the remaining 20-profile body yields a 170 to 330
UTF-8 byte band per new profile, an aggregate v0.6 delta of at most 1,560 bytes,
and a post-v0.6 total of at most 9,527 bytes over exactly 39 skills. Enforcement
is fail-closed in `libexec/apg_skill_library_check.py`, and its aggregate gate
must call `context_footprint_report(blobs=...)` so no second competing context
report exists. The band binds only the six new profiles; diagnostic APG014 is
unchanged. Explicit project selection remains the sole projection authority, and
any advisory surface must be read-only, evidence-separated, deterministic, and
never implicit.

The successor sequence is frozen as APG86 (GoMock and Vitest), APG87 (JSX and
React), APG88 (MDX and Astro), APG89 (dogfood, composition, and the context and
readiness gate), and APG90 (publication), with expected topology 35/35/35, then
37/37/37, then 39/39/39. Development remains 33/33/33 and 14/19 at the APG85
terminal. APG85 implements no skill body, adds no catalog row or projection,
implements no budget check, advances no version, and performs no publication,
deployment, target mutation, remote push, or APG86 execution.

## APG86 GoMock and Vitest profile integration

APG86 provisionally integrates exactly `gomock-test-profile` and
`vitest-test-profile` under ADR 0048. GoMock owns v0.6.0 generator,
controller, expectation, matcher, and diagnostic behavior without absorbing
native Go testing, go-cmp, or Go semantics. Vitest owns 4.1.x runner,
configuration, environment, assertion, mock, timer, isolation, snapshot, and
coverage-provider mechanics without absorbing language, Node, React, generic
test-discipline, coverage-policy, or dependency-selection decisions.

Diagnostics APG039 and APG040 activate the APG85 description and aggregate
budget through the canonical context-report owner. The shipped checker remains
topology-agnostic and relational: exact 35/35/35 belongs to APG86 tests and
phase evidence, and neither the 7,967 baseline nor a 340-to-660 delta rule is
generic enforcement. GoMock uses 276 description bytes, Vitest uses 293, the
library total is 8,536, and 991 bytes remain under the 9,527 ceiling.

Development is 35/35/35 with 35 discoverable, zero malformed, and 14 stable /
21 provisional. Existing explicit project subsets do not expand implicitly.
No package version, dependency, lockfile, advisory discovery, public or active
release, target, publication, deployment, remote push, APG87, JSX, React, MDX,
or Astro work is included.

## APG87 JSX and React profile integration

APG87 provisionally integrates exactly `jsx-language-profile` and
`react-component-profile` under ADR 0049. JSX owns library-independent syntax
and transform semantics; React owns host-independent component, render, state,
Effect, Hook, context, memoization, error-boundary, and component-test
interactions. TypeScript, JavaScript, Node, Vitest, generic test discipline,
MDX, Astro, routing, styling, accessibility, build tooling, and metaframework
behavior remain independent owners or reserved routes.

Development is 37/37/37 with 37 discoverable, zero malformed, and 14 stable /
23 provisional. JSX uses 248 description bytes and React uses 268; the 516-byte
pair produces a 9,052-byte total and preserves 475 bytes under 9,527 for APG88.
The APG86 generic checker is unchanged and remains topology-agnostic. Existing
explicit project subsets do not expand implicitly.

No MDX/Astro implementation, APG88, package version, dependency, lockfile,
advisory discovery, publication, deployment, target mutation, or remote push is
included.

## APG88 MDX and Astro profile integration

APG88 provisionally integrates exactly `mdx-profile` and `astro-profile` under
ADR 0050. MDX owns the Markdown-to-JSX/component seam, ESM, expressions,
provider mapping, and MDX-specific compile/runtime boundary. Astro owns `.astro`
structure, frontmatter/template execution, islands and directives,
server/client placement, content collections, routes, project conventions, and
Astro integration configuration. Markdown, JSX, React, TypeScript, JavaScript,
Node, Vite, Starlight, styling, accessibility, hosting, and deployment remain
independent owners or explicit project routes.

Development is 39/39/39 with 39 discoverable, zero malformed, and 14 stable /
25 provisional. MDX uses 214 description bytes and Astro uses 238; the 452-byte
pair produces a 9,504-byte total and preserves 23 bytes under 9,527. The generic
APG039/APG040 checker is unchanged and remains topology-agnostic. Existing
explicit project subsets do not expand implicitly.

No APG89, package version, dependency, lockfile, advisory discovery, release
publication, deployment, active projection mutation, provider staging, commit,
push, or successor work is included.

## APG89 v0.6 dogfood and readiness

APG89 exercises the complete 39-skill development tree against read-only web
and Go targets, binds fifteen composition questions to their one narrowest
existing owner, proves exact explicit project subsets, and compares checkout
with isolated installed context. It preserves 39/39/39, 14 stable / 25
provisional, 39 discoverable, zero malformed, 9,504 bytes, 9,492 characters,
the 9,527-byte ceiling, and the exact no-seventh-profile set.

Target-owned locked-install failure is retained rather than bypassed. Coverage
variance must be investigated with a fixed sample and unchanged policy; passing
thresholds alone do not establish determinism. APG89 changes no skill,
description, route, source, rights, provenance, package version, dependency,
lockfile, public release, active projection, or deployment. APG90 remains
separately authorized and must not begin from a non-terminal readiness result.

## APG90 v0.6 publication preparation and public release handoff

The external APG89 supervisory review accepted exact APG89 with C0/H0/M0/L0
technical findings and terminalized it as `READY_FOR_APG90` without rewriting
history. APG90 advances the canonical package version to 0.6.0, preserves the
digest-pinned historical thirty-three-skill v0.5.0 policy, and binds the exact
thirty-nine-skill v0.6.0 policy, release epoch, notes, workflow assets,
distribution bundle, installed readback, and public handoff.

The six v0.6 profiles remain provisional; explicit project selection remains
authoritative; no seventh profile, mandatory chain, advisory selection, Nix
deployment, or active APGR mutation is added. Provider work does not stage,
commit, tag, push, or publish. Unless an authorized external mechanism actually
completes immutable GitHub and PyPI readback, the terminal APG90 disposition is
tracked publication preparation complete with external public finalization
pending. No APG91 or v0.7 work is authorized.

## APG94 v0.7 embeddable toolkit architecture

APG94 follows terminal public v0.6.0 and accepts ADR 0051 under explicit human
architecture authority. It freezes one root Go module with public domain
packages `schema`, `report`, `skills`, `envsnap`, and `hotspot`, plus
`cmd/apgr` and private `internal/` implementation. JACA imports public packages
in-process and owns all orchestration; APG never imports JACA. Initial Git may
remain a native exact-argv child process without shell interpretation.

Current Python reporting is the APG95 byte/schema/error oracle. The CLI uses a
strangler migration with one semantic owner per migrated action. Python v0.7
uses supported-target binary wheels, npm uses scoped launcher
`@knowledge-forge-ai/apgr` with platform packages, and all ecosystems share one
version and binary/corpus identity.

The skill resolver is structured, model-free, deterministic, fail-closed on
budget, and materially conserves context through an isolated agent discovery
root. Environment v1 uses typed allowlists, canonical JSON, owner-only no-churn
storage, non-secret values, and in-process resolution; `.flakes` remains
authority until APG98 parity and separate cutover. Hotspot v1 reports only
qualified metrics, explicit unavailable values, confidence, stable JSON, and no
v0.7 churn history. APG101 owns the later human README restructure.

APG95 through APG103 are frozen but separately authorized. APG94 adds no
`go.mod`, Go code, dependency, skill, projection, maturity change, version,
package artifact, README rewrite, publication, deployment, JACA, `.flakes`, or
Nix change. Current state remains 39/39/39, 14 stable / 25 provisional, 9,504
description bytes, 9,492 characters, zero malformed, and version 0.6.0.

## APG95 Go reporting library vertical slice

APG95 implements the first Accepted ADR 0051 slice as one root Go 1.25 module.
Public `schema` and `report` packages expose in-memory Show, Diff, Operational,
ParseRecords, and optional Append behavior. Exact-argv native Git and atomic
publication mechanics remain private under `internal/`; the module has no
third-party dependency.

During APG95, the maintained Python report implementation remained the active
CLI and compatibility oracle. Differential fixtures bind accepted canonical bytes and
rejected failure classes, while Go invariants cover cancellation, drift,
real-index preservation, defensive copies, concurrent reuse, locks,
transactions, modes, and link safety. An external disposable Go module imports
and uses `report` without APG internals, Python, `cmd/apgr`, or a shell at the
consumer boundary.

Observed Python publication supersession removes an ops-only primary without
copying its record into the later Git primary. APG95 preserves those oracle
bytes and records the APG94 architecture's “absorbs” wording discrepancy.
Version remains 0.6.0 and the skill/context invariants remain unchanged. APG95
adds no CLI, route migration, version injection, skill/environment/hotspot
implementation, packaging, JACA, `.flakes`, Nix, release, or publication work.
The operator terminally accepted the reviewed APG95 closeout candidate
after dispatcher finalization was blocked on entry dirt overlap, without
source-byte drift.

## APG96 Go CLI foundation and Python report migration bridge

APG96 adds `cmd/apgr` as a thin adapter over the public Go `report` package,
with private `internal/cli` and `internal/buildinfo` owners. It implements
show, diff, operational/ops, path, recovery, stable build information, the
three supported binary targets, and deterministic release-like linker
injection from the Python `VERSION` and canonical skill-metadata identity.

Python keeps APGR configuration, repository, project, and outbox resolution,
then delegates every normal report route and all three historical report names
to Go with exact argv and no shell. The frozen `libexec/agent_report` owner is
test-oracle-only; a missing Go bridge fails without semantic fallback. Legacy
`GIT_SHOW_REPORT_ROOT` remains private compatibility logic, while canonical
routes use the explicit Python-resolved outbox.

APG96 preserves accepted report bytes and the removal-without-copying ops-only
supersession rule. Version and skill/context invariants remain unchanged. Final
wheel/npm binaries remain APG100 work.

## APG97 deterministic skill context bundles

APG97 embeds the existing 39 canonical skill leaves directly into the public
Go `skills` package and self-verifies the embedded projection against the
established corpus fingerprint. Strict request/result/manifest schemas,
versioned source-backed selection and informational composition tables,
order-invariant identities, and fail-closed byte budgets implement the ADR
0051 context contract without prompt interpretation or implicit profile chains.

Verified results materialize exactly selected direct regular skills plus one
canonical manifest through owner-only staging and atomic publication. Go owns
list/context/resolve/materialize consumer semantics; Python list/context and
new resolve/materialize routes delegate to Go while project/user/global/
flatten maintenance remains Python-owned. External Go consumption and isolated
selected-only Codex discovery are qualified. Version and the 39/39/39,
14/25, 9,504-byte, 9,492-character, and 9,527-ceiling invariants remain
unchanged. APG97 grants no APG98 or successor authority.

## APG98 portable environment snapshots

APG98 adds the provider-neutral public Go `envsnap` package with strict v1
profiles and snapshots, explicit-map capture, deterministic fingerprints,
owner-only interprocess-locked no-churn storage, verified load and staleness,
and default-isolated or explicit-overlay resolution. Go exposes profile-check,
snapshot, show, resolve, and exact-argv run adapters; Python delegates the
`env` family without reimplementing semantics.

Bounded fixtures source-bind the current `.flakes` validators, snapshot,
parser-safe runner, and prompt hook while preserving intentional APG JSON,
explicit-map, sensitive-name, isolation, staleness, and locking differences.
The thin-hook cutover contract is documented but not activated. Version and
skill/context invariants remain unchanged. APG99 is recommended but separately
authorized.

## APG99 structural hotspot analyzer

APG99 adds the provider-neutral public Go `hotspot` package and
`apgr analyze hotspots`. Exact root-relative inventory, direct stable reads,
mandatory file/byte/time bounds, cancellation, symlink refusal, and drift
detection produce canonical `apg.hotspot-report/v1` JSON without executing
source, shells, plugins, configuration, or Git history. Python delegates the
command through the exact-argv Go bridge and has no analysis fallback.

Go receives AST-derived statements, owners, cyclomatic complexity, nesting,
and package/init regions. Every other frozen surface receives only its exact
or bounded structural capability; unsupported semantic metrics remain
explicitly unavailable. Report-local ranking uses the frozen
35/25/15/15/10 weights, capability-separated integer percentiles, visible
available weight and confidence, and deterministic ordering. Terminal output
is concise, Markdown is a deterministic detailed view, and JSON remains the
machine authority. Growth/churn is deferred.

APG99 changes no skill, maturity, version, JACA, `.flakes`, Nix, packaging,
release, deployment, or active target state. APG99 is terminal and preserved
by APG100.

## APG100 complete Go strangler and multi-ecosystem distribution

APG100 advances the single editable release authority to `0.7.0`, moves
response capture to a private Go owner, completes thin verified Python
delegation, and assembles reproducible Go, platform-wheel, source-distribution,
and npm candidate artifacts without publication. One canonical binary manifest
and one coordinated distribution manifest bind version, target, hash, corpus,
and build identity across ecosystems.

Repository and host maintenance remains Python-owned. The legacy project skill
projection adapter remains compatibility-only; Go resolve/materialize remains
portable authority. The v0.7 public candidate excludes the old Python report
oracle and consumer skill module while preserving historical v0.6
reconstruction. APG101 subsequently began under separate authorization.

## APG101 human documentation restructuring

APG101 preserves APG100's accepted runtime and local distribution state while
replacing the root phase ledger with a concise landing page in the frozen
v0.7 information architecture. `docs/README.md` owns task-oriented navigation,
the architecture-frozen reference and guide paths are current, and the former
README chronology remains under `docs/history/releases-and-phases.md`.
Published v0.6.0 and the unpublished, locally qualified v0.7.0 release
candidate are explicit. APG101 changes no runtime, package, version, skill,
maturity, JACA, Nix, active integration, or publication state. APG102 remains
separately authorized.

## APG103 v0.7 public publication and readback

APG103 completed the v0.7.0 public publication handoff. The annotated public
`v0.7.0` tag resolves to release commit
`718344778e937629b8db7e164ae600a95142c05d` with public v0.6.0 as its sole
release parent. The ten-asset GitHub release, Go module, PyPI distribution,
and four npm package surfaces were read back from their public registries.
Earlier APG100 through APG102 candidate wording remains historical to those
phase-local states and is not a current unpublished-release assertion. No Nix
activation, host/profile mutation, or global APGR installation occurred.

## APG104 v0.8 context-footprint implementation candidate

APG104 is the current canonical semantic phase for the bounded APGR v0.8
delivery campaign. CAP0 retains the historical 9,527-byte integrity control,
separates discovery and materialization cost surfaces, selects zero new skill
candidates, and defers the optional external importer. CXT0 freezes the
additive `footprint` package, strict versioned records, deterministic
domain-separated fingerprints, unit-safe comparisons, and
reference-preserving projections with explicit unavailable, sensitivity,
retention, fidelity, and omission handling.

Implementation and qualification remain in progress. No v0.8 release,
publication, deployment, JACA mutation, or host/Nix activation is authorized
by this repository instruction. The candidate requires focused and complete
qualification, the independent public-consumer fixture, and the
dispatcher-owned pre-final review before any closeout publication. Any future
successor still requires separate authority.
