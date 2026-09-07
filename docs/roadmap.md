# APG Roadmap

<!-- APG-CANDIDATE-STATE: css-language-profile retained-provisional -->

The marker above is the mechanical current-state authority. Bounded
contradiction diagnostics cover only their frozen vocabulary; arbitrary prose
still requires human review.

## Roadmap policy

APG115 prepared v0.9.0 release source after APG114 integrated qualification.
APG116's [wording amendment](evaluations/apg116-v090-release-wording-amendment.md)
corrects a package-facing defect found at the first release qualification gate.
Qualification of the amended committed source, product publication and host
promotion remain separate boundaries; no final release bundle is claimed.
APG117's [prerequisite evaluation](evaluations/apg117-v090-release-qualification-prerequisites.md)
records incomplete qualification after pre-final review and closeout amendment.
The unavailable strict PyPI renderer limits description rendering only; APG116
and the v0.8.1 correction also deferred that check. The build/test toolchain was
present but unused. Candidate and publication qualification remain incomplete;
the missing renderer does not prevent the other required work.

The human maintainer retains ultimate roadmap authority. ChatGPT may advance
successive bounded phases only within a human-approved task or preapproved
roadmap envelope and must stop at its defined boundary. Codex recommendations,
commits, and reports are evidence rather than authorization.

APG0 through APG8 are the closed v0.1 development epic, with every historical
terminal outcome preserved, including APG3's blocked preflight. The epic
established governance, the bootstrap maturity model, six provisional skills,
Codex repository discovery, APG and RepoMap dogfooding, project-local projection
and rollback, and RepoMap managed adoption. The APG9 human assignment supplies
APG8's previously requested final external acceptance.

Public v0.1.0 was subsequently published in one intentionally squashed public
commit. The public checkout is the canonical source for the maintainer's
separately managed user-global Codex integration. Superpowers was decommissioned
by explicit human decision, and a bounded fresh RepoMap smoke discovered all six
skills, successfully applied the review skill, passed managed checks, preserved
the tracked repository, and did not use Superpowers as workflow authority.
These later facts reconcile current state without rewriting contemporaneous
phase records.

APG-TEST0 is the first post-v0.1 development-foundation phase. It establishes
the current test layout and the 22-family Bats and 28-family Python integration
suites. APG13 promoted all six current skills to `stable` under ADR 0010.
APG14 publishes those six stable leaves as public v0.2.0 through APG12's exact
projection and reproducible squashed-release process, correcting the v0.1.0
omitted-wrapper class without rewriting the historical release.

APG9 accepts the bounded APG10 through APG14 v0.2 sequence. It is not a
preapproved roadmap envelope. Separate human assignments completed APG10's
experimental-source disposition, APG11's skill-maintenance formalization,
APG12's public distribution and release validation, APG12A's bounded
correction, APG13's six individual maturity dispositions, and APG14's v0.2.0
publication sequence. No successor roadmap epic is authorized.

## APG0 — Foundation and governance

- **Status:** complete; see the
  [APG0 Foundation Exit](status/2026/07/18/00001-apg0-foundation-exit.md).
- **Objective:** establish project identity, artifact ownership, provenance,
  manager-worker coordination, a compatible skill leaf, research evidence, and
  a bounded migration direction.
- **Artifact:** concise root instructions, core governance documents, skill
  index, publication-excluded research, roadmap, and exit record.
- **Result:** governance adopted; no production skill, taxonomy, validator,
  dependency, or publication.

## APG1 — Public projection and documentation boundaries

- **Status:** complete; see
  [ADR 0001](adr/2026/07/0001-public-projection-private-evidence-and-agent-reporting-boundaries.md)
  and the
  [APG1 exit](status/2026/07/18/00002-apg1-public-projection-and-document-hygiene-exit.md).
- **Objective:** establish the private-working/public-projection contract,
  two-level provenance, corrected report direction, independent record
  namespaces, and a publication-safe documentation surface.
- **Artifact:** ADR 0001, record indexes, private evidence ledger, sanitized
  public documents, normalized APG0 exit, and APG1 exit.
- **Result at APG1 close:** publication boundary adopted; repository creation,
  skills, validation, licensing, and release remained future work.

## APG2 — Roadmap reconciliation and first-implementation proposal

- **Status:** complete as a proposal phase; externally accepted by APG2A. See
  [ADR 0002](adr/2026/07/0002-first-implementation-sequence-and-evaluation-baseline.md),
  which is Accepted, and the
  [APG2 exit](status/2026/07/18/00003-apg2-roadmap-reconciliation-proposal-exit.md).
- **Objective:** compare the credible first-implementation choices under common
  criteria, correct the public authority chain, and recommend exactly one
  bounded next phase.
- **Artifact:** authority-model corrections, publication-excluded decision
  evidence, proposed ADR 0002, this reconciled roadmap, and the APG2 exit.
- **Result:** one evaluation-first skill vertical slice was accepted as APG3.
  No implementation occurred during APG2 or APG2A.

## APG3 — Bounded worker-assignment skill vertical slice

- **Status:** phase closeout complete; terminal outcome `blocked` at the
  mandatory harness preflight. See the
  [public evaluation summary](evaluations/apg3-composing-bounded-worker-assignments.md)
  and [APG3 exit](status/2026/07/18/00005-apg3-bounded-worker-assignment-skill-evaluation-exit.md).
- **Objective:** evaluate whether ordinary Codex assignment composition has a
  material deficit and, only when the frozen baseline-adequacy rule demonstrates
  that deficit, author and evaluate at most one narrowly triggered, reversible
  `composing-bounded-worker-assignments` skill. It would turn an already
  authorized objective into one proportional internal worker assignment only
  after delegation is separately permitted and selected.
- **Artifact:** a public-safe blocked evaluation record, exact publication-
  excluded preflight evidence, updated skill and provenance records, and one
  APG3 exit. No candidate leaf exists.
- **Evaluation result:** the accepted method required an independent evaluator
  to freeze calibration, sealed confirmation, bounded sampling, a rubric, a
  baseline-adequacy rule, and safe downstream cases before authoring. That
  sequence did not begin. Active overlapping skill behavior could not be
  removed from both conditions through a supported internal-agent profile, and
  the harness exposed neither an invocation event nor candidate availability
  and deliberate-loading controls. The experiment therefore could not preserve
  the candidate as the sole intended treatment difference.
- **Dependency result:** Accepted ADR 0002, APG2A authorization, manager-worker
  boundaries, and the manual public-surface gate were present. The required
  comparable harness was absent, which activated the accepted stop condition.
- **Non-goals:** delegation authorization, a manager runtime, scheduler,
  registry, external-prompt generator, reusable evaluation framework,
  publication validator, taxonomy, harness adapter, dependency, license choice,
  publication decision, or another roadmap theme.
- **No-leaf state:** the candidate was never authored. No active or empty
  candidate directory, rollback mutation, or rejected-candidate snapshot
  exists.
- **Authorization boundary:** APG2A authorized only this vertical slice. APG3
  applied its stop boundary and is closed. Later themes below remain
  unauthorized.

## APG4 — Bootstrap APG v0.1 under Superpowers coexistence

- **Status:** complete as a provisional bootstrap phase; see
  [ADR 0003](adr/2026/07/0003-bootstrap-maturity-and-superpowers-coexistence.md),
  the [APG4 evaluation summary](evaluations/apg4-bootstrap-v0.1.md), and the
  [APG4 exit](status/2026/07/18/00006-apg4-bootstrap-v0-1-exit.md).
- **Objective:** make Superpowers reference-only for this repository, accept a
  bootstrap-before-clean-evaluation maturity model, and author a small canonical
  APG skill bundle without changing global plugin state.
- **Artifact:** ADR 0003, the bootstrap model, six direct-child skill leaves,
  the Superpowers transition map, public and publication-excluded scenario and
  review evidence, updated indexes, and one APG4 exit.
- **Skills:** `composing-bounded-worker-assignments`,
  `designing-significant-changes`, `planning-repository-work`,
  `implementing-with-test-discipline`, `debugging-systematically`, and
  `reviewing-and-verifying-repository-work`.
- **Maturity:** every retained skill is `provisional`. No skill is called
  evaluated, stable, production-proven, or superior.
- **Evidence:** 18 deliberate public-safe scenario walkthroughs and independent
  per-skill and complete-diff review. This is not automatic-trigger telemetry
  or isolated baseline-versus-treatment evidence.
- **Superpowers state at phase close:** installation was unchanged and
  decommission had not occurred. Repository instructions suppressed workflow
  authority behaviorally without claiming mechanical unloading.
- **Non-goals:** plugin mutation, isolated profile, adapter, evaluator framework,
  dependency, runtime, scheduler, registry, taxonomy, publication, license
  decision, or another implementation epic.
- **Authorization boundary:** APG4 closes after bootstrap, push, and reporting.
  It does not authorize promotion, decommissioning, or a subsequent phase.
- **Subsequent disposition:** skill content and evidence accepted;
  `correction-required` for the omitted Codex repository discovery projection.

## APG4A — Codex repository skill discovery integration

- **Status:** complete as a forward integration correction; see the
  [APG4A exit](status/2026/07/18/00007-apg4a-codex-repository-skill-discovery-exit.md).
- **Objective:** expose the six canonical APG v0.1 leaves through Codex's
  repository discovery location without copying or changing their content.
- **Artifact:** a real `.agents/skills/` directory containing six relative
  symbolic links to the matching canonical leaves under `skills/`, reconciled
  public documentation, and exit `00007`.
- **Evidence:** exact relative targets, repository containment, readable
  matching leaves, unchanged canonical SHA-256 values, Git mode `120000`,
  Markdown and confidentiality gates, and fresh finished-diff review.
- **Maturity:** every skill remains `provisional`; projection correctness is
  integration evidence, not invocation or dogfooding evidence.
- **Superpowers state at phase close:** installation was unchanged and
  behaviorally reference-only for APG.
- **Authorization boundary:** APG4A ends after integration, validation, push,
  and reporting. It does not begin dogfooding or authorize promotion,
  decommissioning, packaging, publication, or another implementation phase.

## APG5 — First Codex dogfooding and commit-message hygiene

- **Status:** complete; see the
  [APG5 evaluation](evaluations/apg5-first-codex-dogfooding.md) and
  [APG5 exit](status/2026/07/18/00008-apg5-first-codex-dogfooding-and-commit-message-hygiene-exit.md).
- **Objective:** record the accepted fresh-session discovery and first explicit
  APG skill use, diagnose APG4A's literal backslash-`n` commit-body sequences,
  and correct only the repository-owned cause supported by evidence.
- **Artifact:** public and publication-excluded dogfooding evidence, focused
  commit-message hygiene in the manager-worker reporting contract, reconciled
  project history, and exit `00008`.
- **Result:** six-skill discovery and explicit review-skill use passed. Exact-byte
  evidence localized the anomaly to caller-side message construction; the Git
  report preserved the commit correctly and required no executable change.
- **Maturity:** all six skills remain `provisional`; automatic invocation,
  comparison, stable maturity, and production readiness remain unmeasured.
- **Superpowers state at phase close:** installation was unchanged and
  reference-only for APG; no Superpowers workflow governed APG5.
- **Authorization boundary:** APG5 ends after validation, commit, push, and
  linked reporting. It does not authorize promotion, decommissioning,
  publication, licensing, or another implementation phase.

## APG6 — RepoMap cross-repository dogfooding

- **Status:** complete and externally accepted; see the
  [APG6 evaluation](evaluations/apg6-repomap-cross-repository-dogfooding.md) and
  [APG6 exit](status/2026/07/19/00009-apg6-repomap-cross-repository-dogfooding-exit.md).
- **Objective:** record separate RepoMap migration-design and accepted
  documentation-only implementation observations, correct review-skill
  discovery for bounded repository artifacts, and align APG exit placement
  with introducing-committer-date semantics.
- **Artifact:** public and publication-excluded cross-repository evidence, one
  review frontmatter and index correction, explicit status-date policy, the
  corrected APG5 exit placement, reconciled maturity and decommission records,
  and exit `00009`.
- **Evidence:** successful use of `designing-significant-changes`,
  `planning-repository-work`, and `reviewing-and-verifying-repository-work` in
  RepoMap; proportional material non-triggers; fresh correction scenarios;
  non-author leaf review; complete finished-diff review; and public/private,
  sequence, link, and projection checks.
- **Maturity:** every skill remains `provisional`. The observations are neither
  automatic-selection nor comparative evidence.
- **Superpowers state at phase close:** installation was unchanged and
  reference-only for APG. Material mapping, APG use, one additional-repository
  use, and a preserved source snapshot supported the gate, while decommission
  still awaited later human action and smoke.
- **Authorization boundary:** APG6 ends after validation, one commit, push, and
  linked reporting. It does not authorize promotion, decommissioning,
  publication, licensing, another skill, or another implementation phase.

## APG7 — Project-local skill projection and rollback tooling

- **Status:** accepted in substance and corrected forward by APG7A; see the
  [APG7 evaluation](evaluations/apg7-project-local-projection-tooling.md),
  [ADR 0004](adr/2026/07/0004-project-local-skill-projection-and-rollback.md),
  and APG7 exit `00010`.
- **Objective:** provide safe opt-in install, adopt, check, and uninstall
  operations for the six canonical APG skills without tracked target or global
  Codex and Superpowers mutation.
- **Artifact:** one Python 3.10+ standard-library executable with two
  non-executable helpers, 26 behavioral test families, project-local deployment
  guidance, a human Superpowers decommission and rollback runbook, public and
  publication-excluded evidence, and exit `00010`.
- **Evidence:** accepted ownership and rollback design; intended pre-production
  failing evidence; 26 passing behavioral tests in temporary Git worktrees and
  temporary `HOME`; one separate passing disposable lifecycle; fresh code and
  safety review; fresh complete-diff review; and integrated source, projection,
  Markdown, confidentiality, sequence, mode, and Git checks.
- **Skill use:** design, planning, implementation discipline, review, and
  bounded reviewer-assignment composition applied within their triggers.
  Systematic debugging remained a material non-trigger because no unexplained
  failure occurred.
- **Maturity:** every skill remains `provisional`. The executable observation is
  neither automatic-selection, comparative, stable, nor production-readiness
  evidence.
- **Superpowers state at phase close:** installation was unchanged and
  reference-only for APG. The documented and tested local uninstall plus human
  rollback runbook supported the rollback-plan component; later human action
  and smoke remained pending.
- **Authorization boundary:** APG7 ends after validation, one commit, push, and
  linked reporting. It does not authorize global plugin action, promotion,
  publication, licensing, another skill, or a successor phase.

## APG7A — Idempotent projection compliance correction

- **Status:** complete and externally accepted; see the APG7
  evaluation's subsequent-correction section and exit `00011`.
- **Objective:** make repeated install and adopt success require the same
  semantic managed-path cleanliness that check already enforces.
- **Artifact:** one shared idempotent-compliance guard in the existing command
  helper, two focused behavioral families, strengthened clean controls,
  reconciled APG7 records, focused publication-excluded evidence, and exit
  `00011`.
- **Evidence:** exact disposable reproduction for install and adopt; two tests
  failing against APG7 production for the intended exit-`0` reason; four
  focused corrected controls; 28 passing behavioral families; a full
  disposable lifecycle; a semantic-override and exact-recovery control; and
  fresh code-and-safety and complete-diff review.
- **Skill use:** systematic debugging, implementation test discipline, and
  review apply. Repository planning and significant-change design remain
  material non-triggers because the accepted architecture and one-step
  correction remain unchanged. Bounded assignment composition applies only to
  the separately authorized reviewers.
- **Architecture:** command grammar, state format version 1, state path,
  exclusion grammar and markers, ownership, locking, transaction ordering,
  dependencies, portability boundary, and global behavior remain unchanged.
- **Maturity:** every skill remains `provisional`. The correction is neither
  automatic-selection, comparative, stable, nor production-readiness evidence.
- **Superpowers state at phase close:** installation was unchanged and
  reference-only for APG; decommission remained pending.
- **Authorization boundary:** APG7A ends after validation, one forward-only
  commit, push, and linked reporting. It does not authorize another command,
  architecture phase, skill promotion, external project mutation, publication,
  licensing, decommissioning, or a successor phase.

## APG8 — RepoMap managed projection adoption

- **Status:** complete and externally accepted by the APG9 human assignment;
  see the
  [APG8 evaluation](evaluations/apg8-repomap-managed-projection-adoption.md) and
  exit `00012`.
- **Objective:** adopt RepoMap's six existing compatible manual APG links into
  managed Git-local state and verify them without changing RepoMap's tracked
  repository.
- **Artifact:** one public deployment evaluation, focused
  publication-excluded before/adoption/check evidence, reconciled rollout and
  decommission records, and exit `00012`. The command and tests are unchanged.
- **Evidence:** synchronized clean target checkpoint; exact six-link and
  canonical validation; expected unmanaged pre-check; one successful default
  adoption; default and explicit managed checks; preserved link inodes,
  targets, hashes, user-owned exclusion bytes, tracked tree, index, status,
  global sentinels, and report state; and fresh independent review.
- **Skill use:** planning and review apply. Significant-change design,
  implementation test discipline, and systematic debugging remain material
  non-triggers. Bounded assignment composition applies only to the authorized
  reviewer.
- **Maturity:** every skill remains `provisional`. Managed deployment is not
  discovery-after-restart, invocation, automatic-selection, comparative,
  stable, or production-readiness evidence.
- **Decommission effect:** material workflow mapping, real APG and additional-
  project use, source preservation, tested local lifecycle behavior,
  real-project managed adoption and check, and the human rollback runbook are
  supported. The full gate remains incomplete.
- **Subsequent disposition:** the maintainer completed Superpowers
  decommission, and the bounded fresh RepoMap smoke passed. It discovered all
  six skills, explicitly applied the review skill, passed managed checks,
  preserved RepoMap, and did not use Superpowers as authority.
- **Authorization boundary:** APG8 ends after one APG commit, push, and linked
  reporting. It does not authorize RepoMap uninstall, another target, command
  change, skill promotion, global plugin action, publication, licensing, the
  fresh-session smoke, or another phase.

## APG-TEST0 — Repository test layout and report-tool coverage

- **Status:** complete; see exit `00013`.
- **Objective:** establish the project-owned unit and integration test layout,
  add behavior coverage for both report commands, and migrate the existing
  project-skill suite without changing executable behavior.
- **Artifact:** two Bash Bats suites under `src/test/unit/bash`, the migrated
  Python suite under `src/test/int/python`, documented layout and commands, and
  exit `00013`.
- **Evidence:** 22 report-tool behavior families passed; all 28 project-skill
  integration families passed; Bash syntax, executable help, test discovery,
  repository links, confidentiality, sequence, and Git whitespace checks
  passed.
- **Skill use:** planning, implementation test discipline, and review apply.
  Significant-change design and systematic debugging remain material
  non-triggers. No worker assignment was composed.
- **Maturity:** the phase strengthens executable regression evidence but does
  not change the maturity of any APG workflow skill.
- **Authorization boundary:** APG-TEST0 changes test ownership and layout only.
  It does not authorize report-format changes, a new dependency manifest,
  coverage policy, publication, release, skill promotion, or another phase.

## APG9 — v0.1 closeout and v0.2 roadmap adoption

- **Status:** complete; see
  [ADR 0006](adr/2026/07/0006-v0-2-objectives-roadmap-and-maturity-promotion.md),
  the [APG9 public evaluation](evaluations/apg9-v0-1-closeout-and-v0-2-roadmap.md),
  and [exit `00014`](status/2026/07/19/00014-apg9-v0-1-release-decommission-and-v0-2-roadmap-exit.md).
- **Objective:** accept public v0.1.0 and its squashed-history model, reconcile
  user-global public integration and Superpowers decommission, close the v0.1
  epic, and assign every remaining roadmap concern to a bounded v0.2 phase or
  terminal disposition.
- **Result:** APG8 receives final external acceptance; APG0 through APG8 close
  as the v0.1 epic with historical outcomes preserved; APG-TEST0 remains the
  first post-release foundation; and APG10 through APG14 are accepted as
  separately authorized phases.
- **Maturity:** all six skills remain `provisional`. APG13 targets `stable` for
  each skill after individual post-Superpowers review; a concrete material
  defect may block one skill, while absent clean A/B or second-repository
  positive evidence does not block by itself.
- **Release limitation:** public v0.1.0 omitted the documented
  `bin/apg-project-skills` wrapper. APG12 owns the validated correction; APG9
  does not modify or republish public.
- **Karpathy status:** the tracked source remains experimental. APG10 owns
  adopt, defer, and reject dispositions and defaults to independent synthesis,
  not a seventh overlapping skill.
- **Authorization boundary:** APG9 ends after validation, one private
  development commit and push, and linked reports. It does not start APG10,
  edit or promote a skill, restore Superpowers, modify public/reference, or
  publish v0.2.

## APG10 — Karpathy evaluation and selective integration

- **Status:** complete; see
  [ADR 0007](adr/2026/07/0007-experimental-karpathy-guidelines-disposition.md),
  the [APG10 evaluation](evaluations/apg10-karpathy-guidelines-evaluation.md),
  and [exit `00015`](status/2026/07/19/00015-apg10-karpathy-guidelines-evaluation-and-selective-integration-exit.md).
- **Objective:** establish exact public provenance and reuse limits for the
  experimental source, test current APG behavior under a frozen concealed-
  source contract, and adopt only a demonstrated gap into its current owner.
- **Result:** assumptions and alternatives, semantic change traceability,
  speculative-scope avoidance, necessary consistency work, proportional
  reversible progress, and project-owned boundaries were already covered.
  Two independent current-change-cleanup positives were materially partial and
  supported one APG-native correction to
  `implementing-with-test-discipline`.
- **Provenance:** `APG10-KARPATHY-SOURCE-01` identifies the unversioned public
  source inspected for APG10. Its mutable locator and MIT declaration do not
  supply a semantic revision, complete license, or notice payload, so APG10
  copies or adapts no expression and adds no guessed third-party notice.
- **Scope:** one current leaf changes once. No root universal, other leaf,
  seventh skill, support directory, dependency, test policy, or maturity state
  changes.
- **Maturity:** all six skills remain `provisional`; the APG10 evidence becomes
  input to APG13 rather than a promotion decision.
- **Authorization boundary:** APG10 ends after one private development commit,
  push, and linked reports. It does not begin APG11, alter public/reference,
  change global integration or RepoMap, restore Superpowers, or publish v0.2.

## Legacy theme dispositions

APG11 closes all 24 former candidate and explicitly deferred questions in the
[legacy roadmap closure ledger](legacy-roadmap-closure.md). The ledger preserves
implemented, conditional, and rejected/project-owned dispositions. APG12
through APG14 now have completed artifacts where the ledger records them.

## Accepted v0.2 sequence

### APG10 — Karpathy evaluation and selective integration

Completed. The experimental source was evaluated against existing owners under
frozen scenarios. APG10 adopted one current-change cleanup correction in the
implementation leaf, recorded every other idea as already covered,
project-owned, or rejected, and added no seventh skill.

### APG11 — Skill authoring, maintenance, and legacy-roadmap closure

Completed. ADR 0008 and the maintainer guide formalize the repeated lifecycle,
the dependency-free checker enforces only adopted mechanical invariants, and
the terminal ledger closes 24 legacy themes. No skill leaf, maturity state,
dependency, public release, or external integration changed.

APG11A subsequently corrected required-key shadowing and fenced-code closure
false negatives in that checker. The correction preserves ADR 0008's narrow
parser architecture, the accepted APG11 lifecycle and ledger, all six skill
leaves and `provisional` maturity states, and the APG12 boundary.

### APG12 — Public distribution and release validation

Completed. ADR 0009, the strict public-surface policy, and
`apg-public-release` establish exact projection of every tracked non-private
path, critical-owner checks, and one deterministic local squashed commit after
the accepted public base. `apg-user-skills` separately establishes verified
public-source install, adopt, check, update, rollback, and uninstall with direct
links and user-local ownership state. Disposable dogfood detects the v0.1
omitted-wrapper class and leaves public and active integration state unchanged.

APG12A subsequently corrects four bounded tooling defects without reopening
the accepted architecture. Both release and user tools now share an exact
public-lineage verifier, executable candidate validation uses only isolated
disposable repository copies and temporary state, and user `check` creates
nothing while using an existing shared lock. The APG12 historical test record,
v0.1 omission regression, schema versions, six provisional skills, and APG13
and APG14 ownership boundaries remain unchanged.

### APG13 — Six-skill post-Superpowers stability review

Completed. ADR 0010 records six individual evidence inventories, frozen current
applications, zero procedure corrections, six `accept-stable` final reviews,
and six `stable` catalog entries. Historical provisional records and public
v0.1.0 remain unchanged. APG14 subsequently corrects two overbroad APG9
evidence labels without changing any procedure or maturity disposition.

### APG14 — v0.2.0 release candidate and publication

Completed. APG14 prepares the exact public-safe source, independently verifies
two deterministic candidates and the isolated user lifecycle, atomically
publishes one squashed v0.2.0 release commit and annotated tag over v0.1.0, and
fast-forwards the existing public-backed integration source without changing
its link ownership shape. The maintainer subsequently completed the requested
full restart and fresh-session discovery smoke and reported that it passed.

## Accepted v0.3 architecture and bounded sequence

APG15 proposed a synthesis-oriented capability architecture rather than
one-to-one Codex VC migration. The maintainer accepted APG15 and
[ADR 0011](adr/2026/07/0011-v0-3-workflow-synthesis-and-modular-guidance-architecture.md)
through APG16. APG18 accepts
[ADR 0012](adr/2026/07/0012-language-profile-contract-and-warning-levels.md)
after bounded contract correction and one Python vertical slice. APG17 accepts
[ADR 0013](adr/2026/07/0013-repository-guidance-synthesis-and-migration-dispositions.md)
for bounded pre-rewrite guidance classification.

### APG15 — v0.3 foundation design

Completed and externally accepted as `Complete — v0.3 foundation architecture
proposed`. The phase designed the public workflow router, guidance-synthesis
candidate, ten language profiles, shared warning proposal, root-guidance
migration, private-overlay boundary, ownership matrix, risks, and successor
roadmap without implementing a skill or beginning release work.

### APG16 — Public APG workflow router

Completed in private development. The maintainer subsequently confirmed the
requested duplicate-name discovery result: both same-name routers were visible
and selectable in the APG repository, while only the private router was visible
and selectable globally.
One provisional `agentic-praxis-grimoire-workflow` router selects among the six
stable process leaves for ambiguity, routing audit, or capability-health
diagnosis. Twenty-one frozen scenario families passed without candidate
correction initially; after semantic review required one bounded non-trigger
inspection correction, 21 fresh applications reran and passed the complete
contract. A checked skill-local map enforces future catalog disposition.
The phase does not modify the six leaves, replace private integration,
implement profiles or synthesis, change stable maturity, or publish.

### APG17 — Repository-guidance synthesis

Completed in private development. Its historical terminal outcome retained a
pending fresh-session application smoke.
One provisional `synthesizing-repository-guidance` leaf owns decomposition and
bounded owner, provenance, privacy, migration, and rollback dispositions before
rewrite. Sixteen frozen families passed with zero candidate corrections, and a
34-unit dogfood ledger exercised every authorized source class without changing
or removing source guidance. The router map now covers seven routable leaves;
the six-skill v0.2 distribution contracts remain unchanged. No language profile,
root migration, private cutover, manager-prompt skill, release, or APG18 work
occurred.

APG17A subsequently corrected two publication-excluded public-release identity
fields without changing public state or any APG17 result. The maintainer
deferred APG17 and APG18 application smoke to the aggregate APG23 readiness and
APG24 release-preparation gates; that deferral does not reverse APG17
repository acceptance.

### APG18 — Language-profile foundation and Python vertical slice

Completed in private development. ADR 0012 and the normative language-profile
contract establish accessible Green/Yellow/Orange/Red responses, project-policy
precedence, artifact classification, exception evidence, and rollback. One
provisional `python-language-profile` passed twenty-four frozen scenarios with
one bounded candidate correction and a seven-case read-only dogfood ledger. Private
development contains six stable process skills and three provisional skills;
the router map contains eight routable non-router capabilities. Public v0.2.0
and its project, user, and release lifecycle remain six-skill contracts.
Application smoke remains deferred to APG23/APG24. Retention of one profile
does not authorize the remaining nine or APG19.

### APG19 — Shell and shell-test profiles

Completed in private development. ADR 0014 accepts separate language and
test-harness ownership. Bash, Bats, and Zsh are `retained-provisional`; ZUnit is
`deferred-source-or-version`. The corrected candidates use concrete monotonic
thresholds, combined-signal crisis handling, frozen scenarios, and read-only
dogfood. Private development contains six stable and six provisional skills,
twelve canonical leaves and projections, and eleven routable non-router map
entries. Public v0.2.0 and its six-skill lifecycle remain unchanged.

### APG19A — Semantic phase identity and APG19 reconciliation

Completed under the maintainer's two-phase authorization. ADR 0015 adopts
globally unique semantic phase IDs, independent ADR and exit sequences,
semantic durable references, precommit record finalization, and deterministic
identity validation. APG19's substantive dispositions remain accepted. One
reproduced Bats fallback-count defect is corrected for the supported comment
function form; Bash and Zsh remain byte-identical, ZUnit remains deferred, and
catalog, maturity, distribution, and application-smoke boundaries are
unchanged.

### APG20 — Go and Ruby profiles

Completed under the maintainer's APG19A-to-APG20 assignment. Independent Go and
Ruby candidates completed current-source research, concrete threshold design,
frozen scenarios, and one bounded design correction each. Fresh review found
additional material semantic, measurement, source-license, dogfood, and
classification defects. The one-correction limit required both candidates to
be `deferred-material-defect`; no candidate leaf or integration is retained.
Private development remains six stable and six provisional skills, twelve
canonical leaves and projections, and eleven routable non-router map entries.
Public v0.2.0 and its six-skill lifecycle remain unchanged.

### APG20A — Go and Ruby profile corrections

Completed under the maintainer's APG20A-to-APG21 assignment. APG20A uses the
complete APG20 defect ledger as its corrected baseline, reproduces and fixes
the report append-lock release race, and retains corrected Go and Ruby profiles
as provisional development skills. Both profiles pass frozen and defect-
specific scenarios, read-only calibration, and fresh non-author review. Private
development contains six stable and eight provisional skills, fourteen
canonical leaves and projections, and thirteen routable non-router map entries.
Public v0.2.0, schema version 1, and active integration remain unchanged.

### APG21 — Nix and relational-engine profiles

Completed under the maintainer's APG20A-to-APG21 assignment. APG21 accepts ADR
0016, retains separate provisional PostgreSQL and SQLite profiles, and adopts
no generic SQL owner. Nix is `deferred-material-defect` after one bounded
correction and a second material scenario contradiction. PostgreSQL and SQLite
pass frozen scenarios, read-only dogfood, and fresh non-author review. Private
development contains six stable and ten provisional skills, sixteen canonical
leaves and projections, and fifteen routable non-router map entries.
No profile grants evaluation, build, live database, migration, activation, or
destructive authority. Public v0.2.0, schema version 1, and active integration
remain unchanged.

### APG21A — Nix profile correction

Completed under the maintainer's APG21A-to-APG22 assignment. APG21A uses the
complete APG21 Nix defect ledger as its corrected baseline, separates structural
merge-family breadth from semantic merge behavior, and retains the corrected
Nix profile provisionally. One newly discovered PostgreSQL false-escalation
contradiction is corrected with failing evidence and focused re-review; SQLite
and router behavior remain accepted. Private development contains six stable
and eleven provisional skills, seventeen canonical leaves and projections, and
sixteen routable non-router map entries. Public v0.2.0, schema version 1, and
active integration remain unchanged.

### APG22 — Cross-repository dogfood and guidance migration proposal

Completed under the maintainer's APG21A-to-APG22 assignment. APG22 applies the
router, synthesis procedure, and nine retained profiles to 35 frozen read-only
APG, RepoMap, private-classification, and public-safe synthetic cases. All
expected dispositions match, with no behavior-bearing APG defect. Application
discovery remains unavailable and is not inferred from explicit reading. The
phase records bounded root and private transition proposals without performing
a cutover, decommission, public release, active-integration mutation, or
application smoke.

### APG22A — Approved-roadmap manager assignments

Completed under the maintainer's APG22A-to-APG22B assignment. APG22A retains
`composing-approved-roadmap-assignments` provisionally after an exhaustive
historic-corpus inventory, current native-capability review, strong ordinary-
prompting baseline, and 30/30 frozen candidate cases. The leaf translates
approved authority without approving, dispatching, executing, accepting, or
continuing work. Development becomes 18/18/18 with 17 routes; the six-skill
public v0.2 boundary remains unchanged.

### APG22B — Version-bounded ZUnit profile

Completed under the maintainer's APG22A-to-APG22B assignment. APG22B retains a
provisional `zunit-test-profile` for exact ZUnit v0.8.2 with Zsh 5.9.2 in the
tested environment. The exact ZUnit v0.8.2 with Zsh 5.3.1 pair is unsupported
because its dependency probe does not complete. The retained leaf owns ZUnit
runner, discovery, assertion, output, fixture, hook, isolation, and lifecycle
judgment while pairing with the Zsh profile for shell semantics. It passes
48/48 frozen cases with zero candidate corrections. Development becomes
19/19/19 with 18 routes; the six-skill public v0.2 boundary remains unchanged.

### APG22C — ZUnit startup-isolation evidence correction

Completed under the maintainer's APG22C-to-APG23 assignment. APG22C reproduces
that the APG22B startup sentinel was outside the path selected by `ZDOTDIR`,
then corrects the disposable harness to require a loading positive control, a
suppressing negative control, and sentinel absence inside the focused ZUnit
test process. The corrected exact matrix retains ZUnit v0.8.2 with Zsh 5.9.2,
preserves Zsh 5.3.1 as unsupported because its runner dependency probe times
out, and leaves the ZUnit skill bytes and zero-correction count unchanged.
Development remains 19/19/19 with 18 routes; public v0.2 remains 6/6/6.
Application smoke and APG23 do not occur in the APG22C session.

### APG23 — Individual readiness and maturity review

Completed after the required full restart in a new APG-rooted session. All
nineteen repository skills were directly discoverable and selectable, the
duplicate workflow router was source-qualified with client path evidence, and
all required router, synthesis, profile, and process/domain applications
passed. Eight v0.3 rows are promoted to stable, five remain provisional, all
thirteen are `include-v0.3`, and no behavior correction is required.

### APG24 — v0.3 release candidate and publication

Completed under the maintainer's explicit APG24 publication authority. ADR
0019 expands the release, user, and project distribution contracts to the exact
nineteen-skill v0.3.0 set while retaining schema version 1, source-specific
user rollback, and existing project-subset ownership. Two deterministic
candidates precede one appended public commit and annotated tag. The active
public-backed source fast-forwards without changing aggregate-link ownership.
The personal router remains installed, and source-qualified fresh-session
shadow smoke remains the external terminal observation.

### APG24A — v0.3 external smoke and router transition closeout

Completed under the maintainer's explicit APG24A authority. The human-reported
fresh-session public-v0.3 shadow passed, and the personal same-name router was
subsequently decommissioned under separate authority. Focused verification
confirms unchanged public and active v0.3.0 state, nineteen aggregate skills,
preserved personal transition targets, and an exact private restoration source.
No behavior-bearing skill, release, active source, or target repository changes.

### APG25 — v0.4 structured project work foundation

Completed under the maintainer's APG24A-to-APG26 assignment. ADRs 0020-0022
accept structured formal/non-phase defaults, prompt compression, scoped tests,
coverage remediation and mock boundaries, Python-first reporting, pytest/xdist
coverage architecture, nested ChatGPT-manager ownership, and evidence-gated
personal hygiene transitions. One bounded correction makes the approved-roadmap
assignment skill consume repository defaults without dropping authority or stop
boundaries. Development remains 19/19/19 with fourteen stable and five
provisional rows; no dependency, executable conversion, test migration,
canonical move, private-skill change, or release occurs.

The complete dependency order and unallocated slices are maintained in the
[v0.4 roadmap](v0-4-roadmap.md) rather than duplicated here.

### APG26 — pytest and Bash-to-Python capabilities

Completed under the maintainer's bounded sequence. APG26 retains provisional
`pytest-test-profile` and `converting-bash-scripts-to-python` after current-
source calibration, sixty frozen scenario families, failing-first focused
contracts, read-only report-tool dogfood, and fresh non-author review. Pytest
uses no behavior-bearing correction; conversion uses one bounded option-
injection correction. Development becomes 21/21/21
with fourteen stable rows, seven provisional rows, and twenty routes. Public
and active v0.3.0 remain unchanged; no report executable or test is migrated.

### APG26A — formal-phase commit-message enforcement

APG26A records that APG26's formal-phase commit has only its subject. APG26 is
not rewritten, and its substantive capability, scenario, routing, and maturity
decisions remain accepted. A dependency-free Python checker enforces the
canonical phase subject, one blank separator, and ordered nonempty `Scope`,
`Result`, `Verification`, and `Not run` sections before and after future APG
formal-phase commits. The correction changes no skill, report format or
executable, public or active v0.3.0 state, target repository, or personal skill.

### APG27 — Python agent-reporting core and Git-record association

APG27 accepts ADR 0023 and produces an uncommitted candidate for the first
report slice. The candidate implements the importable standard-library core,
fixed-vector Git access, exact Git-show compatibility, temporary-index Git-diff
evidence, operational association, and safety corrections. It is not adopted.

Git-show format version 2 and compatible standalone operational format version
1 remain byte-compatible on the characterized POSIX platform. Git-diff format
version 1 records deterministic state evidence without mutating the real index
or worktree. Operational records name an existing complete show or diff record
in the same canonical phase report whenever Git evidence exists. APG27 stops
partial after the release-policy component needs a second material correction:
historical v0.2 configured validation is repaired, but immutable v0.3.0 policy
lacks a version-bounded historical surface. The candidate also retains a Red
Python branch-count stop. No commit or push occurs.

### APG27A — Python reporting correction and adoption

APG27A preserves APG27's partial records and stopped worktree, then corrects
both recorded acceptance defects. Immutable v0.3.0 policy is independently
frozen from the current v0.4 development inventory, malformed and unsupported
identities fail closed, and the Red source-path validator is decomposed without
changing diagnostics. The resulting dependency-free Python report core,
Git-diff evidence, and Git/operational association are adopted after focused
parity, safety, historical-release, and independent review gates.

### APG28 — pytest, xdist, coverage, and mirrored paths

APG28 closes Partial. Its uncommitted candidate includes an exact dependency
stack, eight-worker runner, mirrored paths, strict source inventory, and
coverage-data union. Fresh review rejected the first narrowed denominator; the
corrected full-source gates then exposed material unit, integration, and union
branch deficits, four release-policy failures, incomplete process accounting,
and missing unconditional Git-show Bats equivalence. ADR 0024 remains Proposed.
Public and active v0.3.0 remain unchanged.

### APG28A — pytest migration correction and adoption

APG28A preserves APG28's stopped worktree and Partial result, corrects runner
aggregation, release policy, process completeness, artifact lifecycle, and
coverage quality, and satisfies exact 80/80 component and 85/85 union gates.
Both Bats owners remain. ADR 0024 is Accepted. Public and active v0.3.0 remain
unchanged.

### APG29 — process-skill alignment

APG29 aligns four existing owners with the adopted structured-project and test
defaults. `implementing-with-test-discipline` owns bounded useful-contract
coverage remediation; `planning-repository-work` owns scoped evidence and
justified expansion; `reviewing-and-verifying-repository-work` checks honest
coverage, mock and real-boundary claims, and Git/operational evidence; and
`composing-approved-roadmap-assignments` never assumes a broad suite while
compressing ordinary procedure. All four receive one bounded correction after
fifty-one frozen cases. No trigger, maturity row, route, catalog description,
release object, ChatGPT path, personal skill, or target repository changes.

### APG30 — ChatGPT-manager topology and subrouter

APG30 implements ADR 0022's accepted actor-qualified topology. Canonical
discovery now supports direct leaves and exactly one `skills/chatgpt/<name>`
class, while flat Codex projections remain globally named. The new provisional
`chatgpt-manager-workflow` owns one local manager-leaf route; the general
router owns the subrouter route and no manager leaf. Project, user, and
current-development release owners resolve source-declared canonical paths,
while immutable v0.1.0 through v0.3.0 policy remains direct-child.

Development is 22/22/22 with fourteen stable rows, eight provisional rows,
twenty general-map entries, one ChatGPT-local entry, and twenty-one route
edges. Public and active v0.3.0 remain 19/19/19. No personal skill is changed
and no post-restart application-discovery evidence is claimed.

### APG31 — personal-hygiene shadow and conditional transition

APG31 passes APG30's fresh-session source-qualified topology, routing,
semantic-identity, and managed-report gates without correction. Current APG,
private, and RepoMap owners replace the three targeted general procedures, but
the independent transition gates produce a partial result.

The personal docs-only capability is decommissioned after source-qualified
shadow, exact restoration, and non-author review. Git-history scope reduction
remains deferred because current private routing and destructive-stop ownership
do not yet satisfy the narrowed contract. RepoMap phase-hygiene
decommissioning remains deferred because a current private caller route is
outside APG31 write authority. APG development stays 22/22/22, public and
active v0.3.0 remain 19/19/19, and no target repository changes.

#### APG31 subsequent gate

At APG31 exit, the maintainer still had to restart Codex and run the required
post-transition discovery smoke. Any later assignment had to record or correct
that result before a remaining v0.4 profile slice could begin.

APG31A later supplies the bounded smoke-closeout and caller-correction authority
without altering that historical stop.

### APG31A — personal-hygiene transition completion

APG31A records the maintainer-reported APG31 external smoke as passed while
preserving APG31's historical Partial result. Publication-excluded review
supports two independent results: `git-history-hygiene` is scope-reduced after
generalized behavior returns to APG and repository owners, and
`repomap-phase-hygiene` is decommissioned after generalized behavior returns to
current RepoMap owners.

APG development remains 22/22/22 with fourteen stable and eight provisional
rows. The general and ChatGPT-local maps remain twenty and one. Public and
active v0.3.0 remain 19/19/19, and no target repository changes.

### APG32 — Minitest test profile

APG32 retains `minitest-test-profile` provisionally after current official
Minitest 6.0.6, `minitest-mock` 5.27.0, and Ruby 4.0.6 calibration; source and
rights review; ownership analysis; thirty-six frozen scenarios; a failing-first
mirrored contract; structural classification; integration; and fresh
non-author review. The candidate uses one bounded trigger and ownership
correction.

Development becomes 23/23/23 with fourteen stable and nine provisional rows.
The general map becomes twenty-one edges, the ChatGPT-local map remains one
edge, and public and active v0.3.0 remain 19/19/19. APG32 adds no dependency,
selects no framework or project command, runs no readiness or smoke gate, and
does not construct or publish a release.

### APG33 — Dockerfile profile

APG33 retains `dockerfile-profile` provisionally after current official Docker
documentation, stable Dockerfile frontend 1.25.0, BuildKit 0.31.2, and OCI
Image Spec 1.1.1 calibration; source and rights review; ownership analysis;
forty frozen scenarios; a failing-first mirrored contract; structural
classification; integration; and fresh non-author review.

Development becomes 24/24/24 with fourteen stable and ten provisional rows.
The general map becomes twenty-two edges, the ChatGPT-local map remains one
edge, and public and active v0.3.0 remain 19/19/19. APG33 adds no dependency,
selects no image, builder, platform, project command, or runtime policy,
performs no Docker operation, runs no readiness or smoke gate, and does not
construct or publish a release.

### APG34 — Vagrantfile profile

APG34 retains `vagrantfile-profile` provisionally after current official
Vagrant 2.4.9 and development-source calibration, current Vagrant
documentation, Vagrant's declared Ruby compatibility boundary, source and
rights review, ownership analysis, forty frozen scenarios, a failing-first
mirrored contract, structural classification, integration, and fresh
non-author review. One bounded source-semantics and machine-measurement
correction scopes forwarded-port behavior by provider and prevents an implicit
default machine from being added to named multi-machine counts.

Development becomes 25/25/25 with fourteen stable and eleven provisional rows.
The general map becomes twenty-three edges, the ChatGPT-local map remains one
edge, and public and active v0.3.0 remain 19/19/19. APG34 adds no dependency,
selects no provider, box, plugin, host platform, network, synced folder,
provisioner, project command, or lifecycle action, performs no Vagrantfile
evaluation or Vagrant operation, runs no readiness or smoke gate, and does not
construct or publish a release.

### APG35 — v0.4 remaining-skill authoring

APG35 authors, on the dedicated branch
`claude/apg35-v0.4-remaining-skill-authoring`, the five remaining v0.4
candidates: `go-test-profile`, `matryer-is-test-profile`,
`go-cmp-test-profile`, `go-testing-stack`, and `nix-test-profile`. It also
proposes ADR 0025 and two specifications, freezes one hundred fifty-four
scenario families, and produces a complete Codex integration handoff.

APG35 integrates nothing. It adds no flat projection, catalog row, router
entry, release-policy entry, strict inventory entry, executable fixture, or
test, and it changes no Python or shell code. It runs no project test, no
`go test`, and no Nix evaluation, build, flake check, or virtual-machine or
container test. Development therefore remains 25/25/25 with fourteen stable and
eleven provisional rows, the general map remains twenty-three edges, the
ChatGPT-local map remains one edge, and public and active v0.3.0 remain
19/19/19. ADR 0025 remains Proposed.

The phase's fresh non-author review requirement was not satisfied as specified:
independent reviewers could not be spawned, so the eight lanes were executed by
the author as separate adversarial passes with primary-source re-checks. That
limitation is recorded in the evaluation, the exit, and the handoff, and Codex
must re-run the affected lanes independently before accepting ADR 0025.

### APG36 — Claude-authored skill integration

APG36 preserves and adopts the exact APG35 authoring commit, reruns six fresh
independent review lanes, converts all 154 frozen families into transient
public-safe fixtures, establishes failing-first mirrored contracts, and runs a
disposable pinned Go compatibility harness.

Independent review finds more than one material behavior correction in
`go-test-profile`, `matryer-is-test-profile`, `go-cmp-test-profile`, and
`nix-test-profile`; each is `deferred-material-defect`.
`go-testing-stack` is `rejected-no-independent-value` because its required
native owner is not retained and its trigger, duplicate-owner response,
thinness, and removal semantics need multiple corrections. ADR 0025 is
Rejected.

All five candidates and both proposed specifications are removed through the
APG36 forward commit. Development remains 25/25/25 with fourteen stable and
eleven provisional rows, the general map remains twenty-three entries, the
ChatGPT-local map remains one entry, and checked route edges remain twenty-four.
Public and active v0.3.0 remain 19/19/19.

The Claude/Codex division-of-labor trial is supported for another bounded trial
only with immutable author history, independent Codex review, executable
fixtures, a one-correction allowance, forward-only corrections, and Codex-owned
final status, tests, reports, publication, and deployment.

### APG37 — Go and Nix test-profile redesign

APG37 redesigns the four APG36-deferred candidates on the authoring branch
`claude/apg37-v0.4-go-nix-redesign`, working from the APG36 defect dossier and
reverified current primary sources. It authors four replacement leaves,
proposes ADR 0026 and two specifications, freezes 130 scenario families mapped
to their APG35 predecessors, measures structural calibration against the
complete Go 1.25.10 standard-library and toolchain test corpus, and produces a
publication-excluded Codex integration handoff.

All twenty-four APG36 material findings received a terminal authoring
disposition: twenty-two closed in redesign and two removed as invalid
requirements. Measurement falsified the APG35 numeric structural bands, which
escalate 9.7% of maintained upstream Go test files to crisis on line count
alone, so every numeric crisis cutoff was removed in favour of categorical
conditions.

ADR 0026 proposes three independent component owners and no composition owner.
`go-testing-stack` remains `rejected-no-independent-value` and absent, and ADR
0025 remains Rejected and unreopened.

APG37 integrates nothing. It adds no flat projection, catalog row, router
entry, maturity row, release policy, inventory entry, executable fixture, or
test, and runs no project test, `go test`, or Nix operation. Its review was an
author self-review, not an independent review, and it makes no retention
prediction. Development remains 25/25/25 with fourteen stable and eleven
provisional rows, twenty-three general-map entries, one ChatGPT-local entry,
and twenty-four checked route edges. Public and active v0.3.0 remain 19/19/19.

### APG38 — APG37 Go and Nix integration

APG38 preserves the exact APG37 authoring object and performs independent
source, rights, privacy, owner-graph, structural, fixture, and compatibility
review. It retains provisional `go-test-profile` and `go-cmp-test-profile`;
accepts ADR 0026's two-component no-stack
architecture; and keeps ADR 0025 Rejected.

`matryer-is-test-profile` and `nix-test-profile` are
`deferred-material-defect` after fresh corrected-state review finds new
attribution/false-escalation and FreeBSD sandbox-default behavior defects.
Each candidate has already used its coherent correction cycle, so its leaf and
integration surfaces are forward removed rather than corrected again.

Development becomes 27/27/27 with fourteen stable and thirteen provisional
rows, twenty-five general-map entries, one ChatGPT-local entry, and twenty-six
checked route edges. Public and active v0.3.0 remain 19/19/19.

### APG39 — matryer/is and Nix final redesign

APG39 authors final replacement candidates for the two APG38-deferred
profiles on a Claude authoring branch. It reverifies matryer/is `v1.4.1`,
Nix 2.35.1, and Nixpkgs/NixOS 26.05 as exact current sources; closes the
registered-wrapper attribution, relaxed-mode count-escalation, and sandbox
platform-default defects; freezes 24 and 40 replacement scenario families
with complete predecessor mapping; proposes ADR 0027 conditionally for a
version-bounded third Go component; and hands independent review, fixtures,
compatibility probes, the ADR decision, and atomic integration to a later
separately authorized Codex phase.

Both candidates are `authored-pending-independent-review`. Development
remains 27/27/27 with unchanged maturity, router, and edge counts. Public
and active v0.3.0 remain 19/19/19.

### APG40 — APG39 matryer/is and Nix integration

APG40 preserves and adopts the exact APG39 authoring object, converts both
frozen scenario sets into corrected manager evidence, runs exact-version
matryer/is probes and mandatory Nix source/corpus review, and applies one
coherent correction pass per candidate. Corrected-state review retains
`nix-test-profile` provisionally and defers `matryer-is-test-profile` after its
equality correction remains materially inaccurate. ADR 0027 is Rejected; ADR
0026 remains Accepted; ADR 0025 remains Rejected; `go-testing-stack` remains
absent.

Development becomes 28/28/28 with fourteen stable and fourteen provisional
rows, twenty-six general-map entries, one ChatGPT-local entry, and twenty-seven
checked route edges. Public and active v0.3.0 remain 19/19/19. No Nix execution,
target-repository testing, readiness, smoke, release, publication, deployment,
or successor phase is included.

### APG41 — v0.4 readiness and pre-release smoke

APG41 retains all fourteen provisional rows without maturity promotion after
complete trigger, non-trigger, owner-boundary, adverse, limitation, and
removal review. Cross-profile dogfood preserves direct selection and no
mandatory chain. One bounded wording correction makes Minitest, Dockerfile,
and Vagrantfile removal candidate-independent; fresh corrected-state review
passes.

Complete repository gates, two repository-owned disposable v0.4.0 candidates,
and isolated user/project lifecycle smoke pass on the current host. The
terminal result is `ready-for-publication-with-provisional-limitations`.
Public and active v0.3.0 remain 19/19/19. APG41 publishes and deploys nothing
and authorizes no successor phase.

### APG42 — v0.4 publication and active deployment

APG42 reproduces the exact APG41 candidate, retains the canonical Agentic Praxis
Grimoire NOTICE bytes, freezes the release source, builds and independently reviews two
deterministic final candidates, and atomically publishes only public `main` and
the annotated `v0.4.0` tag. A live remote and fresh clone verify the append-only
lineage before the aggregate-owned active public source advances by exact
fast-forward.

Public and active v0.4.0 contain 28/28/28 with fourteen stable and fourteen
provisional rows. ADR 0025 and ADR 0027 remain Rejected; ADR 0026 remains
Accepted; matryer/is and the stack remain absent. No procedure or maturity
changes, GitHub Release, signing, announcement, plugin distribution, target
mutation, or successor phase are included.

### APG43 — Exceptional v0.4 NOTICE identity correction

APG43 applies one explicit maintainer-authorized correction for a
release-blocking unrelated project identity in `NOTICE`. It amends APG42,
replaces only the named development and public v0.4.0 refs with explicit
leases, verifies the corrected release, and converges the active public-backed
source. The 28/28/28 surface, maturity, routing, release metadata, historical
v0.1.0-v0.3.0 refs, and aggregate-owned integration remain unchanged.

ADR 0028 records the exceptional boundary. Future releases return to
append-only history. No phase after APG43 is authorized; v0.5 requires separate
explicit maintainer authority.

### APG44 — v0.5 foundation and fact-check comparative analysis

APG44 opens v0.5 with separate maintainer authority from the corrected APG43
baseline. It analyzes the external `petar-nauka/fact-check-skill` repository
at an exact verified identity, freezes ten clean-room recommendations with
author dispositions (five forwarded sentence-scale improvements to existing
owners, one deferred fact-check-owner question, four recorded rejections),
records the human-approved [v0.5 roadmap](v0-5-roadmap.md), proposes ADR
0029, and retains a complete Codex peer-review handoff. Nothing is accepted
or implemented; no skill, projection, catalog, route, maturity, release, or
target change occurs; development, public, and active remain 28/28/28. No
phase after APG44 is authorized.

### APG45 — fact-check peer review and roadmap disposition

APG45 preserves the exact APG44 authoring object, independently reverifies the
external source and rights boundary, corrects the scenario and source-count
defects, and terminally dispositions all ten recommendations. REC-01 through
REC-04 are accepted or accepted with narrowing for later implementation;
REC-05 and REC-07 through REC-10 are rejected; REC-06 is deferred.

ADR 0029 is Accepted with amendment after correcting the JavaScript,
TypeScript, Node.js, JSX, React, MDX, and Astro design graph. Development,
public, and active remain 28/28/28. No recommendation, Go owner, web profile,
release, publication, deployment, or successor phase is implemented.

### APG46 — accepted evidence guidance authoring

APG46 authors the candidate implementation of accepted REC-01 through REC-04
on a Claude branch from the exact APG45 base: material-claim identification
and evidence direction in the review skill, and claim-relative source
authority plus optional material access-limitation guidance in the provenance
policy, which remains the sole normative owner. Resulting-state scenario
expectations, the clean-room result, rollback, and the complete Codex
integration handoff are frozen. No synthesis pointer is added, no rejected or
deferred recommendation re-enters, no test runs, integrated `main` is
unchanged at APG45, and development, public, and active remain 28/28/28. No
phase after APG46 is authorized.

### APG47 — accepted evidence guidance integration

APG47 preserves and delivers the exact APG46 authoring object, records
failing-first semantic contracts, corrects the overbroad judgment/advice and
counterevidence rules in one forward pass, and retains REC-01 through REC-04
after independent corrected-state review. The provenance policy remains the
sole normative source-authority owner, material access limitations remain
optional prose, and fresh review and synthesis probes prove no additional
synthesis pointer is needed.

The complete stable-skill unit, integration, combined-union, and Bats gates
pass. Development remains 28/28/28 with unchanged 14/14 maturity and routing;
public and active tracked corrected-v0.4.0 fingerprints remain unchanged. No
rejected or deferred recommendation, Go owner, web profile, release,
publication, deployment, or successor phase is implemented.

### APG48 — Go test-harness dogfood and candidate authoring

APG48 opens v0.5 Workstream 2 from the exact APG47 base with bounded
read-only dogfood in five public Go repositories under the APG47 evidence
discipline: per-clone identity, remote-equality, and direct-versus-indirect
dependency verification, twelve deep-read sample files across ten packages,
a cross-repository pattern matrix, and the eight-part stack-evidence gate.
The `matryer-is-test-profile` candidate is authored on a Claude branch
(`authored-pending-codex-review`) with exact v1.4.1 calibration, a
selection-and-version trigger excluding indirect and checksum-only presence,
all eight historical defect families closed at authoring time, and frozen
scenarios APG48-IS-01 through APG48-IS-24. The `go-testing-stack` candidate
is not authored (`not-authored-no-independent-value`) after the gate failed
on fresh evidence with zero contradictory-owner-answer observations. ADR
0030 is Proposed with no current architecture change; ADR 0025, 0026, and
0027 statuses are unchanged. No test, integration surface, retained-profile
edit, release, or deployment occurs; development, public, and active remain
28/28/28. No phase after APG48 is authorized.

### APG49 — matryer/is validation and disposition

APG49 preserves and delivers the exact APG48 authoring input, independently
re-reads exact matryer/is v1.4.1 bytes and all five dogfood commits, freezes
failing-first controls, and runs isolated runtime probes. One coherent
correction pass addresses the initial source, trigger, diagnostic,
composition, lifecycle, rights, and privacy findings.

Fresh corrected-state review finds new material source-regex,
parent/subtest-severity, selected-version-classification, and
scenario-continuity defects. The one-cycle rule requires
`deferred-material-defect`; current candidate surfaces are forward removed.
ADR 0030 is Rejected, ADR 0026 remains Accepted and controlling, no stack
exists, and development, public, and active remain 28/28/28.

### APG50 — web and Node profile-family architecture

APG50 verifies the exact APG49 baseline, inspects the two Knowledge Forge
AI target repositories read-only at exact commits, and establishes
source/version/rights baselines for all ten Workstream 3 candidates.
Seven candidates are `architecture-supported` (javascript, typescript,
nodejs-runtime, css, markdown, mdx, astro), JSX is
`architecture-supported-with-target-evidence-gap`, and React and Vitest
are `defer-missing-dogfood`. HTML and the browser/DOM runtime are
recorded unowned adjacent gaps, a Starlight residual is recorded and
deferred, sixty architecture scenarios are frozen, bounded slices are
proposed, and ADR 0031 is Proposed. No profile leaf, test, integration
surface, release, or deployment occurs; development, public, and active
remain 28/28/28. No phase after APG50 is authorized.

### APG51 — web and Node architecture peer review

APG51 preserves and delivers the complete APG50 malformed/revert/formal
history, independently reverifies both target snapshots and primary sources,
and performs one forward architecture correction. Fresh corrected-state
review then finds a false JSX rights classification and a non-reproducible
structural corpus record. The one-cycle rule requires ADR 0031 rejection.

All ten candidates are `defer`; no candidate or authoring slice is eligible
from APG51. The consumer-specific TypeScript result, candidate dual-axis
bands, one-count mixed artifacts, Policy A, and separate browser/HTML/
accessibility recommendations remain review evidence only. Development,
public, and active remain 28/28/28.

### APG52 — reproducible web and Node evidence foundation

APG52 reproduces the APG51 corpus defect from committed evidence, resolves all
named abbreviated source identities, and adds standard-library-only
publication-excluded tooling for exact Git-object inventories, exclusions,
measurements, statistics, deterministic sampling, hypothesis comparison,
rights evidence, and two-run verification. Two disjoint acquisitions produce
byte-identical canonical outputs.

Nine whole-file classes are reproducible-sufficient. Scoped CSS and standalone
JSX/TSX retain named source-family insufficiencies and are not padded. The
APG51 values remain hypotheses, ADR 0031 remains Rejected, ADR 0032 is not
created, all ten candidates remain deferred, and no authoring slice is
eligible. Development, public, active, and both targets remain unchanged.

### APG53 — operational tooling and report hygiene

APG53 verifies exact APG52 and its complete managed report, attributes 98.88%
of the formal patch to three complete generated JSONL datasets, and preserves
complete report rendering. It integrates the maintainer-supplied
`flatten-skill-symlinks` purpose through a thin public launcher and bounded
maintained owner-state implementation without mutating live Claude state.

All three report commands now default below
`~/Documents/agent/reports/<normalized-project>` while explicit overrides
remain exact and historical reports remain unmigrated. Leading ASCII periods
are removed from the Git-root basename, with empty identities rejected.

After exact hash and disposable-regeneration verification, the three complete
APG52 datasets are removed from the current tree while compact evidence and
external-output regeneration remain. ADR 0032 accepts deterministic
change-size policy and checking with no APG53 exception. Development remains
28/28/28; corrected public and active v0.4.0 remain unchanged; ADR 0031 remains
Rejected and all ten Web/Node candidates remain deferred.

### APG54 — multi-repository global skill installer integration

APG54 verifies the exact final APG53 correction and managed-report recovery
shape, preserves corroborating bytes matching the declared 944-byte supplied
Bash identity privately, and replaces its sequential one-source loop with a
thin launcher and standard-library Python owners. The command selects current
Codex or Claude personal roots,
uses installed APG by default or one explicit complete local repository set,
and supports `--include-apg`, exact overrides, check, dry-run, and uninstall.

Accepted ADR 0033 owns all-source-first discovery, duplicate-name refusal, one
combined state and lock, update and stale cleanup, state-last commit, rollback,
and refusal to adopt flattener, APG user-lifecycle, or unmanaged ownership.
Current-development release/test inventories include the command for a future
v0.5 candidate while historical v0.4 reconstruction remains unchanged.
Development stays 28/28/28 and corrected public/active v0.4.0 are preserved.

### APG55 — global skill installer transaction hardening

APG55 preserves exact APG54 and ADR 0033 while reproducing and correcting
partial destination creation outside rollback, pre-quarantine replacement
bookkeeping that could mask the original error, and one-read ownership state.
It adds identity-journal cleanup, explicit mutation stages, exact EOF and
metadata-stable reads, control-bearing path rejection, and source directory
and root identity revalidation around link and state mutation.

Command forms, roots, source-set semantics, ownership coexistence, and
current-development release/test ownership remain unchanged. Development
stays 28/28/28 and fourteen/fourteen. Corrected public/active v0.4.0 remain
unchanged; ADR 0031 remains Rejected and all ten Web/Node candidates remain
deferred.

### APG56 — Web and Node architecture reconstruction

APG56 starts from exact APG55, verifies the APG52 compact evidence hashes,
two-run result, and pinned target objects, and reconstructs all ten Web/Node
candidates from first principles with owner validity, authoring eligibility,
and growth-band eligibility decided separately. Six candidates are proposed
authoring-eligible (JavaScript, CSS, Markdown; TypeScript, Node, and Astro
with explicit narrowing), JSX and MDX remain coherent owners with deferred
authoring, and React and Vitest remain Policy A deferrals.

A pre-calculation method freeze and a deterministic byte-identical tool derive
eight family-balanced proposed bands; scoped CSS, standalone JSX/TSX, and MDX
remain non-normative without manufactured measurements. Eighty fresh
scenarios, typed owner-graph and one-count precedence rules, adjacent-gap
recommendations, and a bounded CSS-first slice sequence complete the design.
At APG56 exit ADR 0034 is Proposed and awaits independent Codex review; APG57
later completes that review as recorded below. ADR 0031 remains Rejected;
development remains 28/28/28 and corrected public/active v0.4.0 are unchanged.
No skill is authored or integrated.

### APG57 — Web and Node architecture independent review

APG57 preserves and delivers exact APG56, reverifies the APG52 compact
foundation and target/source/right facts, and corrects the APG56 proposal
total to six eligible and four deferred. A separately frozen reviewer exactly
reproduces APG56's output, then rejects or defers every class after mapped
purpose, tail-support, family-size, dominance, leave-one-family-out, and
metric-suitability checks. No replacement threshold is calculated.

Corrected-state review finds material interval, target-placement,
reproduction-gate, one-count-ledger, and scenario defects, so ADR 0034 is
Rejected under the one-correction rule. Every band and all authoring remain
deferred; React and Vitest retain Policy A; no W1–W4 slice is eligible. ADR
0031 remains Rejected; development stays 28/28/28 and fourteen/fourteen;
corrected public and active v0.4.0 remain unchanged. No skill is authored or
integrated.

### APG58 — CSS language-profile pilot with policy-selected limits

APG58 preserves exact APG57 and both rejected Web/Node ADRs, stops the
family-wide percentile-derivation cycle, and isolates the
strongest-supported candidate: CSS, with twelve pinned standalone target
stylesheets plus embedded sections. It authors one candidate
`css-language-profile` leaf and specification under explicit
maintainability-policy limits — Green < 300, Yellow 300–599, Orange
600–899, Red >= 900 nonblank lines — frozen before target placement and
never described as percentile results. Semantic risk stays a separate axis;
standalone files get one count; embedded CSS gets no additive count and no
scoped-block band; the 995-line target control classifies legacy Red while
nine ordinary sheets stay Green and two stay Yellow.

Thirty frozen scenarios (`APG58-CSS-001`–`030`), Proposed ADR 0035, and a
complete Codex APG59 handoff close the phase. ADR 0031 and ADR 0034 remain
Rejected; every other Web/Node candidate stays deferred; development remains
28/28/28 and fourteen/fourteen; corrected public/active v0.4.0 are
unchanged. No skill is integrated and no successor begins.

### APG59 — CSS language-profile validation and integration

APG59 preserves exact APG58, independently reverifies source, rights, target
counts, and placement, and freezes failing-first executable controls before
one forward correction. The correction classifies the highest baseline,
current, projected, and actual-result state; aggregates growth across the
complete task or phase; prohibits salami-slicing; and clarifies repository,
human, accessibility, and custom-property authority.

Fresh corrected-state review finds material executable-contract and removal
defects after the one correction pass. ADR 0035 is Rejected and every current
candidate surface is removed. Development remains 28/28/28 with fourteen
stable and fourteen provisional rows. ADR 0031 and ADR 0034 remain Rejected;
every Web/Node candidate stays deferred; corrected public and active v0.4.0
remain unchanged.

### APG60 — CSS re-entry contract and removal-closure foundation

APG60 preserves the APG59 rejection and freezes the candidate-independent
contract before any re-authoring. Exactly sixty executable cases cover
baseline/current/projected/actual growth, complete-task aggregation, operation
kind, authority, accessibility, custom properties, one-count, exclusions,
legacy behavior, exceptions, and removal closure. A generic 50-owner manifest
and CSS plan exercise retained and rejected synthetic lifecycles, including
independent omission and stale controls for every current owner, historical
preservation, survivor repair, and a real raw-revert negative.

No CSS or other Web/Node skill is authored or integrated. ADR 0035 remains
Rejected, ADR 0036 is unused, development remains 28/28/28 and fourteen/
fourteen, and corrected public/active v0.4.0 remain unchanged. The Claude
APG61 handoff is a recommendation only; APG60 authorizes no successor.

## Next action

No phase after APG60 is authorized. Live migration, every other authoring or
adjacent-evidence phase, a renewed matryer/is attempt, v0.5
readiness/publication/deployment, signing, announcement, GitHub Release,
plugin publication, target mutation, rollback, and every other successor
require separate maintainer authority.
## APG60A — CSS contract foundation hardening

Status: Complete.

APG60A closes the projection-overrun, exception-authority, broken-symlink, and
actual-retained-owner gaps found after APG60. CSS remains absent and ADR 0036
unused. The next recommended phase is APG61 fresh CSS candidate authoring from
the corrected frozen contract, but APG60A does not authorize it.

## APG60B — CSS traceability and decision closure

Status: Complete.

APG60B closes exact traceability, stable clause-anchor, current narrative
state, declared Python owner, actual derived release-value, import-isolation,
and fresh ADR 0036 lifecycle gaps while preserving the accepted APG60A
behavior contract. CSS remains absent and ADR 0036 remains unused. APG61 is
recommended in the superseding handoff but is not begun or authorized.

## APG60C — CSS runtime and terminal lifecycle closure

Status: Complete.

APG60C preserves accepted APG60B and records the owner-source finality claim
later narrowed forward by APG60D, truthful bounded narrative
diagnostics, positive authored-unintegrated lifecycle, terminal history
preservation, and direct regular current-survivor ownership.
The frozen sixty-case behavior contract is unchanged. CSS remains absent,
ADR 0036 remains unused, and APG61 is recommended in the superseding handoff
but is not begun or authorized.

## APG60D — CSS source-binding and phase-history closure

Status: Complete.

APG60D preserves accepted APG60C, narrows the Python proof to truthful static
source-binding integrity, requires exact APG58 through APG60D foundation
history and exact APG61/APG62 terminal history, rejects wildcard and symlink
substitution, and advances future exits to 00085/00086. CSS remains absent,
ADR 0036 remains unused, and APG61 requires separate future maintainer
authorization.

## APG60E — CSS repository-path and candidate-surface closure

Status: Complete.

APG60E preserves accepted APG60D and closes authority-input, authored-owner,
retained-owner, and projection-target path provenance through one physical-root
descriptor-relative no-follow contract. Exact APG58 through APG60E bundles are
the foundation. APG61 and APG62 advance to exits 00086 and 00087. CSS remains
absent, ADR 0036 remains unused, and APG61 requires separate future maintainer
authorization.

## APG60F — CSS import, owner, and projection closure

Status: Complete.

APG60F preserves accepted APG60E and closes repository-import provenance and
isolation, required-role authority, and coherent projection/target observation.
Exact APG58 through APG60F bundles are the foundation. APG61 and APG62 advance
to exits 00087 and 00088. CSS remains absent, ADR 0036 remains unused, and
APG61 remains recommended but requires separate future maintainer authority.

## APG60G — CSS snapshot, role, and derived-set closure

APG60G is complete. It preserves accepted APG60F and closes the remaining
candidate-independent false passes through a pinned runtime-root observation,
exact sorted canonical skill sets, an independent 52-role semantic registry,
and coherent entry/descriptor authority reads. The current manifest and plan
are schema 6; exact APG58 through APG60G bundles are the foundation. APG61 and
APG62 advance to exits 00088 and 00089. CSS remains absent, ADR 0035 remains
Rejected, ADR 0036 remains unused, and APG61 requires separate future
maintainer authority.

Terminal unit, integration, combined-union, configured Bats, all-five-state
lifecycle, integrity, privacy, rights, and independent non-author review gates
passed.

## APG60H — CSS snapshot and full-path binding closure

APG60H is complete. It preserves the Claude implementation, corrects worker
temporary ownership, path absence, platform error, timeout residue, glob, and
cleanup defects, and versions the foundation through APG60H. APG61 remains a
separately authorized future phase at exit 00089; APG62 remains future 00090.

## APG60I — worker temporary-root binding and cleanup closure

APG60I is complete. It preserves APG60H's maintainer-directed adoption and
corrects the known root-substitution and pre-cleanup residue defects forward.
The worker child is created beneath the retained no-follow root descriptor;
cleanup owns the lifecycle before creation and final path-chain revalidation
is required. APG61 remains separately authorized future exit 00090; APG62
remains future 00091.

## APG61 — CSS language-profile authoring from frozen contract

APG61 is complete as an authoring phase. One fresh `css-language-profile`
candidate — leaf, specification, and sixty-case traceability map — was
authored from the frozen APG60A contract on the preserved Claude authoring
branch, and ADR 0036 is Proposed. The candidate is not integrated: current
candidate-state markers remain absent, integrated counts remain 28/28/28,
and development `main` remains at exact APG60I. APG62 validation remains
separately authorized future exit 00091.

## APG62 — CSS language-profile validation and rejection

APG62 is complete at exit 00091. It remotely delivers exact APG61,
independently reconstructs all sixty frozen results, reproduces seven initial
semantic-navigation defects, and applies the one authorized coherent
correction. Fresh corrected-state review identifies a new material
`record-growth-state` obligation over six frozen cases, requiring rejection.
ADR 0036 is Rejected; all current CSS candidate surfaces are removed;
development remains 28/28/28 with 14 stable / 14 provisional; and APG61
history is preserved. Public, active, and target state is unchanged. No phase
after APG62 is authorized.

## APG63 — Markdown architecture and lean contract

APG63 is complete at exit 00092. It preserves the terminal CSS rejection
and moves to the next evidence-supported profile: Markdown. From exact
APG62 it reverifies CommonMark 0.31.2, the pinned GFM specification,
CC BY-SA 4.0 document rights, and the seven target Markdown documents;
defines a narrowed coherent Markdown owner with closed raw-HTML,
frontmatter, and MDX/host boundaries; selects qualitative structure-first
structural policy (disposition C) under ten pre-frozen purpose controls;
freezes the lean thirty-six-scenario candidate-independent contract; and
proposes ADR 0037. No skill is authored and nothing is integrated;
development remains 28/28/28 with 14 stable / 14 provisional; public,
active, and target state is unchanged. Codex peer review (recommended
APG64) terminally decides ADR 0037. No phase after APG63 is authorized.

## APG64 — Markdown architecture peer review

APG64 is complete at exit 00093. Exact APG63 was delivered, its source,
rights, parser, target, inventory, structural policy, and thirty-six scenarios
were independently reviewed, and one coherent correction closed the complete
initial material set. Fresh corrected-state review found no new material
defect; ADR 0037 is Accepted with amendment and the architecture remains
authoring-eligible-with-narrowing. No skill or integration exists; development
remains 28/28/28 with 14 stable / 14 provisional; public, active, CSS, and
target state is unchanged. No APG65 or successor is authorized.

## APG65 — Markdown language-profile candidate authoring

APG65 is complete at exit 00094. One fresh branch-only Markdown candidate —
leaf, specification, and navigation-only scenario-coverage record — is
authored from the accepted ADR 0037 architecture, with ADR 0038 Proposed and
all thirty-four candidate-semantic scenarios mapped to stable clauses. The
candidate is authored-proposed-unintegrated pending separately authorized
APG66 validation and integration decision; integrated development remains
28/28/28 with 14 stable / 14 provisional, CSS stays absent, and public,
active, and target state is unchanged. No phase after APG65 is authorized.

## APG66 — Markdown language-profile validation and integration

APG66 is complete at exit 00095. Exact APG65 is remotely delivered without
changing Claude authorship; two candidate-blind oracle lanes and two fresh
corrected-state lanes validate all thirty-four semantic scenarios. One
coherent correction closes the complete initial set and is preserved by an
actual Git-diff record before review. ADR 0038 is Accepted with amendment and
the profile is retained provisionally at 29/29/29, 14 stable / 15 provisional,
27 general routes, one ChatGPT-local route, and 28 checked edges. ADR 0037
remains Accepted with amendment; CSS remains absent; public/active corrected
v0.4.0 and targets remain unchanged. No phase after APG66 is authorized.

## APG66A — Markdown replay-evidence truth

APG66A is complete at exit 00096. Exact accepted-register projection,
mechanical navigation, targeted mutation guards, normative-spec direct-file
containment, and clean-release isolation replace fixture-self-copy and global-
token false passes without changing Markdown candidate semantics or ADR
decisions. The profile remains retained provisional at 29/29/29, 14/15, and
27/1/28. No phase after APG66A is authorized.

## APG66B — Markdown register vocabulary and guard exactness

APG66B consumes exit 00097 and corrects five later-reproduced automated-
evidence gaps: exact ordered vocabulary, closed lexical tokens, rollback/source
proof scope, source polarity, and descriptive-versus-normative numeric counts.
APG66 and APG66A remain accepted; candidate semantics, ADRs, retained Markdown
integration, public/active v0.4.0, and targets remain unchanged. APG67 JavaScript
architecture is recommended at exit 00098 but is not begun. No successor is
authorized.

## APG66C — Markdown clause polarity and predicate binding

APG66C consumes exit 00098 and completes the bounded correction for inherited
numeric predicates, rollback obligation order, source contradiction, signal
negation, and targeted-guard contradiction. A continuation reproduces the
order-sensitive repository-import assertion, classifies its whole-cache claim
as overbroad, and replaces it with inspected-root module, colliding-name,
search-path, and importer-cache evidence without changing production import
behavior. Candidate semantics, ADRs, retained integration, corrected public/
active v0.4.0, and targets remain unchanged. APG67 is recommended at exit
00099 but not begun; no successor is authorized.

## APG66D — Repository-import cache entry presence

APG66D consumes exit 00099 and forward-corrects one newly reproduced false
pass in APG66C's test-only relevant-state helper. Exact key presence and exact
stored-object identity are now separate requirements, including for `None`
sentinels; the bounded cache/import owner family contains no second defect of
that class. APG66C remains accepted, production import behavior and Markdown
semantics are unchanged, and retained state remains 29/29/29, 14/15, and
27/1/28. APG67 JavaScript architecture is recommended at exit 00100 but is
not begun. No successor is authorized.

## APG67 — JavaScript language-profile architecture and lean contract

APG67 consumes exit 00100 and proposes ADR 0039: one JavaScript
language-profile architecture from the exact ECMAScript 2026 annual source,
one candidate-independent lean validation contract, and one frozen forty-row
scenario register, with structural disposition C and
`authoring-eligible-with-narrowing` as the eligibility result. JavaScript,
TypeScript, and Node.js remain separate owners; no skill or integration
owner changes; retained state remains 29/29/29, 14/15, and 27/1/28; Markdown
remains retained provisional; CSS remains absent. APG68 — Codex JavaScript
architecture and lean-contract peer review, expected exit 00101 — is
recommended but not begun. No successor is authorized.

## APG68 — JavaScript architecture peer review

APG68 consumes exit 00101, preserves exact APG67, applies one coherent
source-authority/vocabulary/routing correction, then rejects ADR 0039 when
fresh semantic review finds material defects. Eligibility is
`not-applicable-rejected`; state remains 29/29/29, 14/15, and 27/1/28.
APG69 is not recommended; exit 00102 and ADR 0040 remain unused. No successor
starts.

## APG69 — JavaScript core architecture reset

APG69 consumes exit 00102 under new human authority. It proposes ADR
0040: a narrower ECMAScript-core owner, typed question-specific
authorities, a four-layer decision model with an ordered effective
route union, independent 24/10/8/2 registers, qualitative disposition
C, and eligibility `authoring-eligible-with-narrowing`. ADR 0039 stays
Rejected; state remains 29/29/29, 14/15, and 27/1/28; development main
stays at exact APG68. APG70 (expected exit 00103) is recommended for
terminal ADR 0040 decision; no successor starts.

## APG70 — JavaScript core layered-architecture peer review

APG70 consumes exit 00103, normally delivers exact APG69, independently
reconstructs and replays the layered oracle, freezes all initial findings, and
uses one coherent correction. Fresh non-author review finds new material
source-truth, signal, context-route, policy-typing, proof, and adjacent-owner
defects. ADR 0040 is Rejected; eligibility is
`not-applicable-rejected`; no current JavaScript architecture input or skill
exists. State remains 29/29/29, 14/15, and 27/1/28. APG71 is not recommended,
exit 00104 and ADR 0041 remain unused, and no successor starts.

## APG71 — TypeScript architecture and compiler-generation boundary

APG71 consumes exit 00103 under separate new human authority scoped to
TypeScript architecture (APG70's JavaScript non-recommendation stands),
verifies exact APG70 and its four-record omnibus, independently reverifies
TypeScript 7 native and TypeScript 6 legacy sources, packages, rights,
targets, and corpus, and proposes ADR 0041 with exit 00104: disposition B
source authority, a first-class compiler-generation boundary, 22 semantic
and 12 boundary rows plus 2 process invariants, structural disposition D,
and eligibility `authoring-eligible-with-narrowing`. No skill or
integration owner changes; state remains 29/29/29, 14/15, and 27/1/28.
APG72 (expected exit 00105) is recommended for terminal ADR 0041 decision;
no successor is authorized.

## APG72 — TypeScript architecture peer review

APG72 consumes exit 00104, normally delivers exact APG71, independently
reconstructs source/target and 22/12/2 oracle evidence, freezes M1-M18 plus
A1-A5, applies one coherent correction to 22/14/2, and preserves the actual
corrected patch. Fresh non-author review finds new material owner/route,
role-state, source-kind, and evidence-state defects. ADR 0041 is Rejected,
eligibility is `not-applicable-rejected`, and exit 00105 records no current
TypeScript architecture input. No skill or integration owner changes; state
remains 29/29/29, 14/15, and 27/1/28. APG73 is not recommended or begun.

## APG73 — Language-profile production recovery charter

APG73 consumes exit 00106 under new human governance authority and accepts ADR
0042. It preserves every rejected CSS, JavaScript, and TypeScript ADR while
replacing automatic rejection after one correction with bounded iterative
hardening for future production recovery. One coherent correction remains one
round; up to three separately evidenced rounds are allowed by default; a
repairable remaining defect normally yields `repair-required`. Critical and
High defects block integration. Medium and Low debt must be explicit and human
accepted. Terminal rejection or removal requires human authority.

TypeScript is essential, CSS and JavaScript are desirable, and JSX is deferred.
TypeScript 7 is the intended primary compiler generation; the older target
snapshot is a migration baseline; temporary TypeScript 6 is permitted only for
an independently required role with a retirement condition. APG73 authors and
integrates no profile. Development remains 29/29/29, 14/15, and 27/1/28;
Markdown, rejected ADRs, corrected public/active v0.4.0, and targets remain
unchanged.

The intended sequence is APG74 TypeScript candidate and intended-state harness
(exit 00107, ADR 0043 Proposed, no integration), APG75 TypeScript iterative
hardening and possible provisional integration (exit 00108, decide ADR 0043),
APG75A TypeScript scope/lifecycle closure (exit 00109, no new ADR), APG76 CSS
candidate recovery (exit 00110, ADR 0044 Proposed, no integration), and APG77
Codex CSS hardening and possible provisional integration (exit 00111, decide
ADR 0044). These are roadmap identities only, and each successor requires
separate human authority. Narrow JavaScript recovery moves to later separate
authorization.

APG74 has now executed the first step of that sequence as candidate
authoring only: the TypeScript language-profile candidate and the
TypeScript 7 intended-state fixture exist on the APG74 branch with ADR 0043
Proposed, `typescript@7.0.2` freshly selected, TypeScript 6 recorded
`not-required` with a refresh condition, and nothing integrated —
development main remains exact APG73 at 29/29/29, 14/15, and 27/1/28.
APG75 (exit 00108) remains the next recommended phase and requires separate
human authority; APG76 and APG77 identities are unchanged.

APG75 has now executed under separate authority and provisionally integrates
the TypeScript profile after three preserved rounds and a zero-finding terminal
review. ADR 0043 is Accepted with amendment; development is 30/30/30, 14/16,
and 28/1/29. APG76 and APG77 remain roadmap identities only. APG75 does not
authorize either successor.

APG75A has now executed under explicit human continuation authority. It closes
the reusable/project compiler boundary, response-axis contamination, stale
current lifecycle surfaces, APG75 delivery evidence, and clean-runner
prerequisite without changing provisional integration. APG76 and APG77 remain
recommendations only and are not begun.
## APG76 CSS candidate recovery

APG76 opens the CSS production-recovery line under accepted ADR 0042 with one
Claude authoring phase: ADR 0044 Proposed, exit 00110, candidate and fixture on
a branch, and no integration. It repairs, revives, and amends none of the
rejected CSS history. APG77 remains the separately authorized Codex hardening
phase that terminally decides ADR 0044 at exit 00111. Integrated development is
unchanged at 30/30/30, 14/16, and 28/1/29.

## APG77 CSS repair checkpoint

APG77 executes under separate authority and consumes exit 00111. It uses all
three default hardening rounds; terminal review leaves two High retained-
evidence defects. ADR 0044 remains Proposed, CSS remains unintegrated, and
development remains 30/30/30, 14/16, and 28/1/29. APG78 is not recommended or
begun. Any continuation is a new human product decision, not automatic roadmap
authority.

## APG77A CSS evidence-retention repair checkpoint

APG77A executes the human-selected one-round continuation and consumes exit
00112. Complete H1 target identities and separately complete H2 lanes are
preserved, but fresh review finds three High defects and no debt is accepted.
ADR 0044 remains Proposed, CSS remains unintegrated, and development remains
30/30/30, 14/16, and 28/1/29. APG78 is not recommended or begun. Any further
CSS action requires another human product decision.

## APG79A JavaScript terminal-proof checkpoint

APG79A consumes exit 00118 under separate human continuation authority and
preserves one immutable H1/H2/M1/M2 correction. Fresh review finds five Medium
material defects and no accepted JavaScript debt. ADR 0045 remains Proposed,
JavaScript is `repair-required-after-apg79a`, and integration remains absent.
Development stays exact APG77D at 31/31/31, 14/17, and 29/1/30; public/active
corrected v0.4.0 and targets remain unchanged. APG80 is not recommended and any
continuation requires another human decision.

## APG78 and APG79 JavaScript recovery checkpoint

APG78 authors the narrow JavaScript core candidate at exit 00116. APG79 consumes
exit 00117, preserves three correction rounds, and terminally retains ADR 0045
Proposed after fresh review finds two High and two Medium material defects with
no accepted debt. JavaScript remains `repair-required-after-round-3` and
unintegrated. Development stays exact APG77D at 31/31/31, 14/17, and 29/1/30;
public/active corrected v0.4.0 and targets remain unchanged. APG80 is not
recommended; further JavaScript work requires a human continuation decision.

## APG77D CSS known-debt integration

APG77D consumes exit 00115 under explicit human product authority. Exactly four
Medium and one Low qualification limitations are accepted for provisional use;
zero Critical/High and no semantic/source/target/runtime/release/rollback debt
is accepted. ADR 0044 is Accepted with amendment and CSS is integrated
provisionally at 31/31/31, 14/17, and 29/1/30 after live lifecycle, release,
historical-exclusion, regression, and rollback closure. Stable maturity remains
blocked. APG78 is recommended at exit 00116 but remains separately authorized
and unbegun.

## APG77B CSS traceability and clean-room repair checkpoint

APG77B executes the human-selected H3-H5 continuation and consumes exit 00113.
The exact SVG authority, 45-purpose registry, retained Lane N, independent Lane
T2, resolved provenance, and current-tree tombstone are preserved. Four-lane
fresh review finds four High and two Medium defects, and no debt is accepted.
ADR 0044 remains Proposed, CSS remains unintegrated, and development remains
30/30/30, 14/16, and 28/1/29. APG78 is not recommended or begun. Any further
CSS action requires another human product decision.

## APG77C CSS evidence-proportionality repair checkpoint

APG77C executes the human-selected P1-P6 continuation and consumes exit 00114.
The governance clarification, exact private historical-patch exception,
supported scanner forms, and compact v3 are preserved. Three-lane fresh review
finds six Medium and one Low qualification defects, and no debt is accepted.
ADR 0044 remains Proposed, CSS remains unintegrated, and development remains
30/30/30, 14/16, and 28/1/29. APG78 is not recommended or begun. Any further
CSS action requires another human product decision.

## APG79B JavaScript contract and harness checkpoint

APG79B consumes exit 00119 under separate human continuation authority and
preserves one immutable correction for the five APG79A findings. Fresh review
finds zero Critical, zero High, four unique Medium, and zero Low defects with no
accepted debt. JavaScript is `repair-required-after-apg79b`, ADR 0045 remains
Proposed, and integration is absent. Development stays exact APG77D at
31/31/31, 14/17, and 29/1/30; public/active corrected v0.4.0 and targets remain
unchanged. APG80 is not recommended and any continuation requires another human
decision.

## APG79C JavaScript human-debt integration checkpoint

APG79C consumes exit 00120 under explicit human debt authority and accepts
exactly four Medium JavaScript qualification limitations for provisional use.
Zero Critical/High and no semantic, source, target, owner, release, or rollback
debt is accepted. A separate unaccepted Medium Test262 identity discrepancy
blocks integration. JavaScript remains `repair-required-after-apg79b`, ADR 0045
remains Proposed, and development stays exact APG77D at 31/31/31, 14/17, and
29/1/30. APG80 is not recommended; further action requires a human decision.

## APG79D Test262 source-evidence correction

APG79D consumes exit 00121 under the narrow human continuation authority. Its
first immutable commit corrects the current Test262 source-role model without
rewriting the APG79B report: the APG79 reviewed pin is historical, fresh
default-branch identity is mutable refresh evidence, and the exact licence
object owns the rights boundary. Test262 remains non-normative and no corpus
content is consumed. Ordinary head drift is non-blocking while rights and role
remain unchanged; consequence-bearing rights or corpus changes stop. ADR 0045
Terminal review of the separately gated integration candidate finds zero
Critical, zero High, three unaccepted Medium, and two unaccepted Low defects.
The consequence-bearing blocker is a Medium false proxy: the maintained
historical-report-rewrite mutation does not bind the managed report bytes.
The report itself remains byte-exact. The integration candidate is discarded,
ADR 0045 remains Proposed, and JavaScript remains repair-required and
unintegrated at exact APG77D development state. No additional debt is accepted,
APG80 is not recommended, and further action requires a human decision.

## APG79E JavaScript report-binding debt and provisional integration

APG79E consumes exit 00122 under explicit human-debt authority, accepts only
`JS-QD-005` as one additional Medium supporting qualification limitation, and
uses direct current APG79B report verification as its workaround. Zero Critical,
High, or unaccepted Medium/Low findings remain. ADR 0045 is Accepted with
amendment and JavaScript is provisionally integrated under exactly
`JS-QD-001` through `JS-QD-005`. Development is 32/32/32, 14/18, and 30/1/31.
APG80 is recommended but separately authorized and has not begun.
## APG80 Node.js runtime and CLI-stack candidate

APG80 consumes exit 00123 as a Claude authoring phase. It authors one narrow
reusable `nodejs-runtime-profile` candidate, its specification, a
navigation-only twenty-four-scenario coverage record, a fourteen-case APG-owned
target-first fixture, and Proposed ADR 0046. It integrates nothing, decides
nothing, adds no debt, and changes no lifecycle. Mainline development remains
32/32/32, 14/18, and 30/1/31. APG81 is recommended as Codex Node.js runtime and
CLI iterative hardening and provisional integration at exit 00124, is separately
authorized, and has not begun.

## APG81 Node.js hardening repair checkpoint

APG81 consumes exit 00124 and preserves three immutable correction rounds.
Fresh terminal review leaves zero Critical, three High, two Medium, and zero
Low material qualification-harness findings with no accepted Node debt. ADR
0046 remains Proposed and `nodejs-runtime-profile` remains
`repair-required-after-round-3` and unintegrated. Main remains exact APG79E at
32/32/32, 14/18, and 30/1/31; the candidate branch remains 33/32/32. Further
work requires a new human continuation decision. APG81A, APG82, and successor
work are not begun or authorized.

## APG81A Node.js threat-model correction checkpoint

APG81A completes and independently validates the controlled-local-or-CI harness
correction with zero findings and zero Node debt. Terminal review of the later
integration candidate finds one High rollback defect and one Medium
contradictory ADR-index lifecycle defect. Integration stops, ADR 0046 remains
Proposed, Node remains corrected, repair-required, and unintegrated, and exact
APG79E main remains 32/32/32, 14/18, and 30/1/31. A new human continuation
decision is required; APG82 and successor work are not authorized.

## APG81B Node.js integration-contract clarification checkpoint

APG81B establishes the future candidate-preserving rollback target as
33/32/32, then stops its reconstructed integration on three Medium staged-
review defects with zero Node debt. The attempted integration and unauthorized
test-only repair are removed. ADR 0046 remains Proposed; Node remains corrected,
repair-required, and unintegrated; exact APG79E main remains 32/32/32, 14/18,
and 30/1/31. APG82 and successor work remain unauthorized pending a new human
decision.

## APG81C Node.js lifecycle, test, and scratch repair checkpoint

APG81C retains the authorized support correction and machine-local scratch
policy after fresh zero-finding precommit review. Immutable review finds one
Medium contradiction between retained pending-review prose and the completed
review/commit/report evidence, so integration does not open. ADR 0046 remains
Proposed; Node remains corrected, repair-required, and unintegrated at
33/32/32; exact APG79E main remains 32/32/32, 14/18, and 30/1/31. APG82 and
successor work remain unauthorized pending a new human decision.

## APG81D Node.js repo-local scratch integration checkpoint

APG81D reconstructs the Node integration and release candidate, then stops on
final staged review at C0/H1/M3/L0. Attempted integration, product, harness,
and test bytes are discarded. ADR 0046 remains Proposed and Node remains
repair-required and unintegrated at 33/32/32; main remains exact APG79E at
32/32/32, 14/18, and 30/1/31. Zero Node or scratch debt is accepted. APG82 and
successor work remain unauthorized pending a new human decision.

## APG81E Node.js final-integration review checkpoint

APG81E reconstructs integrated and candidate-preserving rollback selections,
the fail-closed scratch query, exact phase-root cleanup, and deterministic
release evidence. Final staged review stops the candidate at C0/H1/M2/L0: the
rollback test-owner projection does not bind the actual selected filesystem,
current phase summaries are chronologically misplaced, and the phase source
record omits the fresh Node release-schedule identities. All attempted
integration bytes are removed. ADR 0046 remains Proposed; Node remains
repair-required and unintegrated at 33/32/32; main remains exact APG79E at
32/32/32, 14/18, and 30/1/31. Zero Node or scratch debt is accepted, and APG82
or successor work requires a new human decision.

## APG81F Node.js actual-test-projection repair checkpoint

APG81F attempts the one authorized correction after APG81E. Frozen review finds
C0/H3/M2/L0 across selection control, two-state execution evidence, release
projection, chronology proof, and exact source evidence. The attempted
correction is discarded. ADR 0046 remains Proposed and Node remains
repair-required and unintegrated at 33/32/32; main remains exact APG79E. No
successor is authorized.

## APG81G Node.js selector, release, and integration closure

APG81G was the bounded continuation after APG81F. Its one correction was frozen
before commit and fresh review found two High and four Medium defects. All
attempted implementation and test bytes are discarded. ADR 0046 stays Proposed,
Node stays retained, repair-required, and unintegrated at 33/32/32, no Node or
scratch debt is accepted, and no successor is authorized.

## APG81H Node.js reviewable qualification and integration closure

APG81H is the explicit continuation after APG81G. Fresh review found one Medium
defect in its bounded correction: catalog maturity evidence did not bind the
complete actual language-profile lifecycle map, including Node's current
repair-required lifecycle. Attempted implementation and test bytes were
discarded. ADR 0046 remains Proposed; Node remains retained, repair-required,
and unintegrated at 33/32/32. No integration, main adoption, target execution,
APG82, or successor is authorized.

The resumed APG81H recovery provisionally integrates Node after correcting the
adjacent generic change-size fixture without changing production. Development
is 33/33/33, 14/19, and 31/1/32; ADR 0046 is Accepted with amendment, Node and
scratch debt are zero, and corrected public/active v0.4.0 remains unchanged.
No APG81I, APG82, or successor implementation is authorized.

## APG82 APGR CLI, distribution, configuration, and artifact foundation

APG82 establishes `apgr`, the `agentic-praxis-grimoire` distribution, packaged
checkout-independent consumer resources, bounded global/project configuration,
one-primary terminal outbox reports, immutable numbered response capture, and
read-only context-footprint measurement. Existing profile lifecycles, maturity,
and the exact CSS/JavaScript debt ledger are unchanged. Corrected historical
v0.4 identity remains isolated from all APG82-only owners.

After APG82, the remaining v0.5 sequence is only APG83 bounded real dogfood and
readiness, followed by APG84 publication from a separately approved ready tree.
Neither is started here. The separately recorded v0.6 candidate scope is the
six named Astro, JSX, MDX, React, Vitest, and GoMock profiles plus explicit
project-selected context/projection infrastructure; it grants no implementation
authority.

## APG83 v0.5 bounded dogfood and release readiness

APG83 completes the first remaining v0.5 slice. Exact approved Knowledge Forge
targets provide bounded JavaScript, TypeScript, Node.js, CSS, Markdown, and
multi-owner dogfood evidence. Installed APGR and the version-bound public-Git
release/PyPI-runtime split pass outside-checkout qualification. A deterministic
sdist metadata defect is corrected within the phase, and final Git and Python
artifacts are reconstructed twice from disjoint roots.

The result is `READY_FOR_APG84`. APG84 remains the sole remaining v0.5 phase and
requires separate authority for public GitHub and PyPI publication. The frozen
v0.6 candidate set and context/projection infrastructure workstream remain
unchanged and unimplemented.

## APG84 v0.5 public GitHub and PyPI publication

APG84 is the final v0.5 phase. It adds the exact normalized publication-bundle
owner and the narrow GitHub Release to PyPI Trusted Publishing workflow, then
subjects the frozen source, reconstructed public Git objects, and Python
artifacts to final qualification and C0/H0/M0 review before any public ref
mutation. Actual GitHub/PyPI publication and immutable readback remain
operational facts recorded outside the prepublication source commit.

Successful APG84 finishes v0.5. It does not start Nix deployment,
`agentic-praxis-grimoire-nd`, `composition-nd`, or v0.6.

## APG85 v0.6 architecture, discoverability, and context budget

APG85 is the first v0.6 phase and is architecture and documentation only. Under
ADR 0047 it freezes the exact six-profile scope, states each profile's owns,
does-not-own, and composes-with boundary, and adds a deterministic composition
rule under which the narrowest applicable owner answers and ties resolve by a
stated layer order.

It derives the first real growth limit on discovery metadata from the measured
existing profile corpus: a 170 to 330 UTF-8 byte band per new profile, at most
1,560 aggregate bytes for the six, and at most 9,527 bytes over exactly 39
skills, with an expected envelope of 8,987 to 9,527. Enforcement is fail-closed
under one measurement owner, binds only the six new profiles, and leaves
diagnostic APG014 unchanged. Explicit project selection remains the sole
projection authority, and any advisory surface must be read-only,
evidence-separated, deterministic, and never implicit.

The successor sequence is frozen as APG86 (GoMock and Vitest), APG87 (JSX and
React), APG88 (MDX and Astro), APG89 (dogfood, composition, and the context and
readiness gate), and APG90 (publication). APG85 implements no skill body, adds
no catalog row or projection, advances no version, and performs no publication,
deployment, target mutation, or push. Each successor phase remains separately
authorized.

## APG86 GoMock and Vitest implementation

APG86 implements the first two frozen v0.6 profiles and the APG85 budget gate.
GoMock v0.6.0 and Vitest 4.1.x receive narrow provisional owners, public-safe
boundary fixtures, catalog rows, routes, projections, packaged metadata, and
current project/release inventory ownership. Development is 35/35/35, 14/21,
and 35 discoverable with zero malformed entries.

APG039 enforces the six-name 170-to-330 UTF-8 byte band. APG040 calls the
canonical context-report implementation and enforces the 9,527-byte ceiling,
relational discoverability, and malformed-entry refusal without a phase-
specific topology or baseline. The two descriptions add 569 bytes, producing
8,536 total and preserving 991 bytes for APG87 and APG88.

APG86 changes no version, dependency, lockfile, public release, active target,
or advisory discovery surface and starts no APG87 work. APG87 remains the next
separately authorized phase.

## APG87 JSX and React implementation

APG87 implements the second frozen v0.6 pair. JSX receives a
library-independent syntax/transform owner and React receives a host-independent
component/render owner, with public-safe boundary fixtures, catalog rows,
routes, projections, packaged metadata, and current project/release inventory
ownership. Development is 37/37/37, 14/23, and 37 discoverable with zero
malformed entries.

The descriptions consume 248 and 268 bytes, 516 combined, producing 9,052
total and preserving 475 bytes for APG88. This dispositions the post-planning
review's headroom finding without changing the generic topology-agnostic
checker. APG87 changes no version, dependency, lockfile, public release, active
target, or advisory discovery surface and starts no MDX/Astro or APG88 work.
APG88 remains separately authorized.

## APG88 MDX and Astro implementation

APG88 implements the final frozen v0.6 authoring pair. MDX receives a
document/component-seam owner and Astro receives a framework/project/execution
owner, with public-safe boundary fixtures, catalog rows, routes, projections,
packaged metadata, and current project/release inventory ownership. Development
is 39/39/39, 14/25, and 39 discoverable with zero malformed entries.

The descriptions consume 214 and 238 bytes, 452 combined, producing 9,504
total and preserving 23 bytes beneath 9,527. This dispositions the reviewed
topology, Markdown-route, description-allocation, and `AGENTS.md` findings
without changing the generic topology-agnostic checker. All six frozen v0.6
profiles are authored and provisionally integrated. APG88 changes no version,
dependency, lockfile, public release, active target, or advisory discovery
surface and starts no APG89 work. APG89 remains separately authorized.

## APG89 v0.6 dogfood, composition, context, and readiness

APG89 qualifies the complete 39-skill development tree without changing its
skills, routes, descriptions, maturity, dependencies, or version. Read-only
web and Go dogfood, a fifteen-row owner matrix, exact explicit project subsets,
isolated installed context, and two disjoint package builds exercise the
accepted APG85-APG88 architecture. The result preserves 39/39/39, 14/25, 39
discoverable, zero malformed, 9,504 bytes, 9,492 characters, 23 bytes of
headroom, and the no-seventh-profile rule.

The recurring integration branch variance is reproduced with a fixed sample
and corrected only through deterministic test evidence; production behavior,
thresholds, exclusions, rounding, and denominators remain unchanged. APG89
does not advance a version, name or publish a release candidate, tag, upload,
deploy, mutate active projections, or begin APG90. APG90 remains separately
authorized and depends on a terminal green APG89 disposition.

## APG90 v0.6 publication preparation and public release handoff

The external APG89 supervisory review returned **ACCEPT** with C0/H0/M0/L0
technical findings, so APG90 advances the canonical package version to 0.6.0
and prepares the exact public release. Historical v0.5.0 remains a digest-
pinned thirty-three-skill policy surface; current v0.6.0 contains exactly 39
skills and 39 projections, with all six new profiles still provisional and
project selection explicit-only.

APG90 binds the v0.6 release epoch, exact GitHub workflow tag and assets,
release notes, reproducible Python bundle, installed context, normal forward
public lineage, and a same-phase operator handoff. Provider work does not
stage, commit, tag, push, publish, deploy, or mutate active projections.

## APG93 v0.6 public GitHub and PyPI publication

APG91 diagnosed initial runner environment binding issues during publication.
APG92 proved the frozen APG90 release content exact, hardened the operator
publication packet, pinned validation python, resolved tool bindings, passed
unit tests, and committed the hardened packet.

APG93 established the external publication authority boundary. Following
dispatcher pre-final review acceptance and operator execution of
`finalize-public-release.sh --execute`, public v0.6.0 was published to GitHub
and PyPI. Live readback confirmed release commit `d37727d5c928f542cbee89b1be1979d4046c4d65`,
annotated tag `v0.6.0` (object `eedcacf685bea32612f534e174bc5c12592c56a0`), 3
GitHub Release assets matching APG90 hashes, successful Trusted Publishing,
matching PyPI 0.6.0 distribution hashes, and isolated package readback reporting
version 0.6.0 with the exact 39-skill context. No Nix or active APGR deployment
occurred; v0.6 is complete.

## APG94 v0.7 embeddable toolkit architecture

APG94 begins the separately authorized v0.7 architecture line after terminal
v0.6 publication. ADR 0051 and
[the normative v0.7 architecture](architecture/v0-7-embeddable-toolkit.md)
freeze APG as a library-first Go toolkit that JACA can import without invoking
`apgr` or a shell. The root module uses domain packages for reporting, skills,
environment snapshots, hotspots, and shared schemas; native Git remains an
exact-argv child process behind APG's in-process boundary.

The architecture preserves current report schemas through Python/Go golden
parity, freezes the complete CLI migration matrix, selects binary-containing
Python wheels and scoped npm launcher `@knowledge-forge-ai/apgr`, defines
model-free structured skill bundles and real agent-scoped materialization,
keeps the 9,527-byte global ceiling unchanged, and assigns portable environment
capture plus honest language-capability hotspot analysis to independent phases.
Growth/churn is explicitly deferred beyond v0.7.

[The v0.7 roadmap](v0-7-roadmap.md) freezes APG95 reporting, APG96 Go CLI,
APG97 context bundles, APG98 environment snapshots, APG99 hotspots, APG100
remaining migration and Python/npm packaging, APG101 documentation, APG102
cross-consumer readiness, and APG103 publication/readback. Each remains
separately authorized.

APG94 changes no implementation, module, dependency, skill, maturity, package
version, public release, deployment, JACA, `.flakes`, or Nix state. Development
remains 39/39/39, 14 stable / 25 provisional, 9,504 description bytes, 9,492
characters, zero malformed, and version 0.6.0.

## APG95 Go reporting library vertical slice

APG95 implements the first ADR 0051 vertical slice as a root Go 1.25 module
with public `schema` and `report` packages and private exact-argv Git and atomic
publication owners. It provides in-memory Show, Diff, Operational,
ParseRecords, and optional Append behavior without adding `cmd/apgr` or
changing the active Python CLI.

The maintained differential corpus binds accepted canonical bytes and rejected
failure classes to the Python oracle, exercises read-only temporary-index and
publication safety, and proves a disposable external module can import and use
`report` without APG internals, Python, or a shell at the consumer boundary.
The observed Python rule removes rather than carries forward an ops-only
primary when Git supersedes it; APG95 preserves that behavior and records the
APG94 wording discrepancy.

The operator terminally accepted the reviewed APG95 closeout candidate
after dispatcher finalization was blocked on entry dirt overlap, without
source-byte drift. APG95 preserves version 0.6.0, 39/39/39 skills, 14 stable / 25
provisional, 9,504 description bytes, 9,492 characters, zero malformed, and the
9,527-byte ceiling.

## APG96 Go CLI and report migration bridge

APG96 adds the root `cmd/apgr` adapter, private CLI and build-information
owners, report show/diff/operational/path/recovery commands, legacy omnibus
compatibility, and a deterministic supported-target build helper. Python keeps
configuration and outbox resolution but delegates every normal report route
and all three historical names to Go with exact argv and no shell. The frozen
Python implementation remains directly reachable only by parity tests.

The bridge carries injected version 0.6.0 and the SHA-256 identity of the
canonical skill metadata resource. Source defaults report `devel`; final
platform-wheel/npm binary assembly remains deferred to APG100. APG96 changes no
skill, maturity, context, package version, public v0.6 artifact, JACA, `.flakes`,
Nix, environment, hotspot, response, publication, or deployment surface.

## APG97 deterministic skill context bundles

APG97 turns the existing canonical `skills/` tree into the public Go `skills`
package without moving or duplicating Markdown. All 39 leaves, including both
nested ChatGPT leaves, are embedded and mechanically reconstructed into the
existing metadata projection and corpus fingerprint.

Strict request, result, rule, composition, and manifest v1 contracts provide
model-free explicit/structured selection, deterministic identities,
selected-only informational edges, and fail-closed byte budgets. Verified
results materialize from embedded bytes into isolated owner-only roots through
private staging and atomic publication; no global or active project root is
mutated.

Go owns normal list/context semantics plus resolve/materialize. Python delegates
list/context and exposes new Go-backed resolve/materialize convenience routes,
while project/user/install-global/flatten maintenance remains Python-owned. A
disposable external Go module and isolated Codex launch qualify direct import
and selected-only discovery. APG97 is terminal and preserved by APG98.

## APG98 portable environment snapshots

APG98 adds the public provider-neutral `envsnap` package with strict versioned
profile and snapshot JSON, capture from explicit maps, stable profile/content
fingerprints, owner-only interprocess-locked no-churn storage, verified loading
and staleness, and default-isolated or explicit-overlay resolution. Sensitive
credential names fail closed; defaults remain metadata and are never inserted.

Go exposes profile-check, snapshot, show, resolve, and exact-argv run adapters.
Python delegates the `env` family without a semantic fallback. Bounded fixtures
bind the current `.flakes` validators, snapshot, parser-safe run, and prompt-
hook behavior while documenting APG's intentional JSON, explicit-map,
isolation, fingerprint, staleness, sensitive-name, and locking differences. A
thin-hook cutover contract is documented but not executed. APG98 changes no
`.flakes`, Nix, live shell, host snapshot, JACA, hotspot, response, packaging,
publication, or successor state. APG98 is terminal and preserved by APG99.

## APG99 structural hotspot analyzer

APG99 adds the public provider-neutral `hotspot` package and
`apgr analyze hotspots`. It scans one exact physical root through bounded,
no-follow, stable direct reads; emits the canonical
`apg.hotspot-report/v1` machine model; and renders concise terminal and
detailed deterministic Markdown views from that model. Python delegates the
new family to Go with exact argv and no semantic fallback.

Go AST analysis owns exact statement, symbol, cyclomatic, nesting, and
package/init-region metrics. Markdown, hybrid documents, structured data,
Dockerfiles, and bounded declarative scanners expose only the frozen exact or
structural capabilities; unsupported procedural-language semantics remain
explicitly unavailable. Ranking is report-local, capability-separated, and
uses the frozen 35/25/15/15/10 weights without treating missing metrics as
zero. Growth/churn and all Git-history inspection remain deferred.

Immutable APG candidate and read-only JACA snapshots repeat byte-identically
without target mutation or execution. APG99 changes no skill, maturity,
version, JACA, `.flakes`, Nix, packaging, release, deployment, or successor
state. APG99 is terminal and preserved by APG100.

## APG100 complete Go strangler and multi-ecosystem distribution

APG100 advances the single editable version authority to `0.7.0`, moves
response capture to a private Go owner, and completes normal Python portable
routes as exact-argv Go delegation without a mutation fallback. Repository and
host maintenance remains deliberately Python-owned, including the legacy
project-local symlink projection adapter; portable skill selection and
materialization remains Go-owned.

One canonical target manifest binds three reproducible `CGO_ENABLED=0` Go
binaries. The same target bytes enter three platform Python wheels and three
npm platform packages. A dependency-free npm launcher, one Go-source Python
sdist, and one coordinated distribution manifest complete the local release-
candidate surface. Wrappers verify version, target, hash, corpus, and build
identity and never download at runtime.

The v0.7 public-source projection removes the old Python report oracle and
consumer skill implementation while retaining historical v0.6 reconstruction.
APG100 changes no skill, maturity, report/skill/environment/hotspot schema,
JACA, `.flakes`, Nix, deployment, publication, or README information
architecture. The operator accepted the reviewed and corrected closeout source
after a dispatcher result-fence recognition failure; the failure changed no
source bytes. APG101 subsequently began under separate authorization.

## APG101 human documentation and README restructuring

APG101 replaces the phase-ledger root README with a concise human landing page
in the frozen v0.7 information architecture. A task-oriented `docs/README.md`
routes readers to the canonical CLI, Go library, skill-context, environment,
hotspot, distribution, JACA, governance, status, release, and history owners.
The former README chronology remains available at
`docs/history/releases-and-phases.md`.

The landing page distinguishes published v0.6.0 from the locally qualified,
unpublished v0.7.0 release candidate and provides safe source-checkout
commands. APG101 changes no runtime API, CLI syntax, schema, package
architecture, version, skill, maturity, JACA, Nix, active integration, or
publication state. APG102 cross-consumer readiness remains separately
authorized.

## APG102 cross-consumer v0.7 release readiness

APG102 qualifies the exact v0.7.0 candidate across reproducible Go, Python,
and npm artifacts; direct and installed command parity; real execution of all
three supported target binaries; self-contained source rebuild; public-package
imports exercised through a disposable JACA-owned adapter that created no
production JACA dependency; selected-only Codex discovery; environment resolution
with separate secret injection; hotspot structured consumption; exact v0.6
reconstruction; and isolated package rollback.

The intentionally broken hotspot test fixture is narrowly excluded from human
documentation link authority, and Python wheel validation now enforces the
complete exact binary manifest. The canonical broad gate and focused release
surfaces are green. Exact publication inputs and immutable readback steps are
bound in publication-excluded APG103 handoff evidence. APG102 changes no skill,
maturity, target, package name, accepted public schema, active root, Nix state,
tag, registry, or publication state. APG103 remains separately authorized.

## APGR v0.8 context-footprint and skill-inventory program

The [v0.8 architecture contract](architecture/v0-8-context-footprint-and-skill-inventory.md)
integrates the APGR-owned capacity, selection-identity, footprint, projection,
qualification, and consumer-boundary dispositions. The
[v0.8 roadmap](v0-8-roadmap.md) makes only `APGR-CAP0` and `APGR-CXT0` eligible
for separate architecture or read-only-measurement starts. The direct bounded
operator assignment now authorizes APG104's implementation campaign, but it
does not grant automatic successor authority. APG103 has already closed the
v0.7 publication and readback handoff; the v0.8 product line advances through
v0.8.1 release recovery.

## APG103 v0.7 public publication and readback

APG103 completed the previously prepared v0.7 publication handoff. The public
`v0.7.0` annotated tag resolves to release commit
`718344778e937629b8db7e164ae600a95142c05d` in the Knowledge Forge public
repository, with the accepted public `v0.6.0` release as its sole parent. The
public GitHub release contains the ten expected assets: one distribution
manifest, one checksum manifest, three platform Python wheels, one Python
source distribution, three platform npm packages, and one npm launcher
package. Public Go module, PyPI, and npm readback completed for the v0.7.0
identities and integrity values.

The earlier APG100, APG101, and APG102 entries intentionally describe the
candidate as unpublished because that was their phase-local state. APG103
updates the current release state without rewriting those historical entries.
The v0.7.0 release is the exact public base for APG104. No Nix activation or
host/profile mutation occurred; Nix remains a consumer-side handoff only.

## APG104 v0.8 context-footprint implementation candidate

APG104 is the canonical semantic delivery phase for the bounded APGR v0.8
program. CAP0 retains the historical 9,527-byte integrity control, separates
description, body, support, and materialized-bundle accounting, selects zero
new skill candidates, and defers the optional Caveman importer. CXT0 freezes
the additive `footprint` architecture, strict versioned records, deterministic
domain-separated fingerprints, unit-safe comparisons, and reference-preserving
projections with explicit unavailable, sensitivity, retention, fidelity, and
omission states.

Implementation and integration are in progress. Focused and complete
qualification, deterministic release construction, independent consumer
qualification, and the dispatcher-owned pre-final review remain required
before any v0.8 publication. APG104 does not change the v0.7 public release,
modify JACA, activate Nix, or authorize a successor phase. The optional
importer and any skill-candidate work remain non-blocking and deferred unless
their stated evidence gates pass.

## APG105 v0.8.0 publication preflight and partial prefix

APG105 prepared the v0.8.0 release. Publication reached Git and the Go module proxy
before stopping prior to downstream completion on GitHub Releases, PyPI, and npm.
The public v0.8.0 Git commit and tag are preserved as immutable historical predecessor state.

## APG106 TTY publication executor qualification

APG106 qualified the fail-closed publication executor, resolving Go module `.info`
extension tolerance and remote readback classification.

## APG107 and APG108 v0.8.1 qualification and release recovery

APG107 qualifies v0.8.1 as the complete, synchronized release of the v0.8 product
line with audited human-facing documentation, verified project URLs, npm READMEs,
and deterministic two-build evidence. APG108 delivers the publication executor
and repository metadata reconciliation.

The v0.8.1 product is published across all four distribution channels (GitHub Releases,
PyPI, npm, and Go proxy). Reconciliation completed in run
`APGR-V081-RECONCILE1--20260906T173602166416Z`.

## APGR v0.9 Program — CI-First Foundation and Backlog Ordering

The active development program is ordered by the [v0.9 Roadmap](v0-9-roadmap.md).
v0.9 prioritizes JACA CI qualification support, JACA XO compatibility, and cross-release
backlog disposition across future v0.10 (Theme Forge) and v0.11 (Repo Map) candidates.
v0.9 is active development, not a published release.

## APG118 v0.9.0 release bundle qualification

APG118 built paired APG116 candidates and all ten assets, and completed source,
rendering, installed-consumer, Go, and inert publisher checks. Full public
validation found a private local path in the APG113 public exit. A bounded
correction preserves that exit's historical result; disposition is
`V090_SOURCE_AMENDMENT_REQUIRES_QUALIFICATION`. Corrected-source release
qualification remains pending. APG117 is unchanged. Dispatcher review and
closeout remain pending; no public publication or successor is authorized.
See the [APG118 evaluation](evaluations/apg118-v090-release-bundle-qualification.md).
