# Skill Authoring and Maintenance

<!-- APG-CANDIDATE-STATE: css-language-profile retained-provisional -->

The marker above is the mechanical current-state authority. Bounded
contradiction diagnostics cover only their frozen vocabulary; arbitrary prose
still requires human review.

## Purpose and ownership

This guide is the normative maintainer-facing procedure for creating,
correcting, supporting, maturing, deprecating, or removing an APG skill. The
[project model](project-model.md) owns general artifact destination and practice
lifecycle policy. The [skill catalog](../skills/README.md) owns current leaves,
discovery shape, and maturity labels. [Provenance](provenance.md) owns source,
rights, derivation, and notice records. Evaluations and exits own bounded
evidence and phase history.

This procedure does not grant authority. Work requires a human-authorized phase
or assignment, and repository policy continues to own project-specific
parameters.

## Choose the owner

| Need | Destination |
| --- | --- |
| A concise rule that must apply to nearly all repository work | Root instruction |
| A demonstrated gap in an existing triggerable procedure | Existing skill correction |
| One coherent reusable problem with no adequate existing owner | New skill |
| Detailed guidance needed only after one skill triggers | Supporting reference |
| A stable skill-local operation that benefits from deterministic execution | Deterministic helper |
| Architecture, authority, privacy, test, release, or repository-specific requirements | Project policy |
| An observation, scenario result, source mapping, or bounded review | Evidence only |
| Duplicated, unjustified, incompatible, or excessively project-specific material | Rejection |

External packaging, repeated slogans, or authoritative tone do not establish an
APG owner. Prefer the smallest existing owner that can address a demonstrated
gap without broadening its trigger.

## Lifecycle

1. Authorize and define the concrete problem.
2. Inspect existing owners, repository policy, and native capability.
3. Inventory source identity, publication status, reuse rights, and notice
   duties.
4. Classify the change as new skill, frontmatter-only correction,
   behavior-bearing correction, support/helper addition, maturity-only
   disposition, or deprecation/removal.
5. Freeze acceptance, representative non-trigger, edge or stop, and rollback
   evidence proportional to the change.
6. Establish baseline behavior when behavior will change.
7. Author the smallest APG-native artifact in its owning destination.
8. Run the affected scenarios, `apg-check-skill-library`, and repository gates.
9. Obtain fresh non-author review of the resulting state.
10. Record provenance, maturity, maintenance impact, disposition, limitations,
    and rollback.

Do not infer permission to expand the change from this lifecycle. An unmet
authority, privacy, rights, or safety condition stops the work.

## Change-class matrix

| Class | Required evidence | Default correction bound | Mechanical checks | Independent review | Records | Rollback | Maturity effect |
| --- | --- | --- | --- | --- | --- | --- | --- |
| New skill | Ownership gap; source rights; multiple independent positive and non-trigger families; edge or stop behavior | One candidate plus one bounded material correction | Full library, catalog, projection, link, and repository gates | Fresh procedure and complete-diff review | Public evaluation, provenance, catalog, ADR or exit as required; private source evidence when needed | Remove leaf, projection, catalog row, active references, and support while preserving history | None unless separately authorized |
| Frontmatter-only discovery correction | Reproduced discovery gap and unaffected procedure baseline | One correction | Metadata, catalog, projection, discovery-focused regression | Fresh non-author leaf review | Evaluation/provenance/exit update proportional to the correction | Restore prior frontmatter and rerun discovery checks | None |
| Behavior-bearing procedure correction | Frozen gap; current and candidate results on the same affected positive, non-trigger, and edge or stop cases | One bounded correction unless the phase declares another finite bound | Full checker plus affected repository regression | Fresh non-author procedure and resulting-state review | Public evaluation and provenance; private exact evidence when needed | Restore prior leaf, rerun frozen cases and gates, supersede the decision if material | None unless separately authorized |
| Support file or deterministic helper | Demonstrated leaf-local need, interface, safety boundary, dependency status, and executable examples where applicable | One bounded correction | Leaf shape, links, helper syntax and behavior, repository regression | Fresh code/content and safety review | Catalog or guide only when behavior changes; provenance/evaluation as needed | Remove support and references together; restore prior leaf | None |
| Maturity-only disposition | Complete evidence inventory against the accepted maturity criteria | No procedure correction; any correction becomes another class | Full current checker and regression evidence | Fresh per-skill disposition review | Catalog, evaluation, provenance, ADR/exit as required | Revert label and supersede unsupported disposition; do not erase evidence | Only the explicitly authorized label change |
| Deprecation or removal | Replacement or obsolescence evidence, dependency/reference inventory, migration and history plan | One bounded reconciliation pass | Full checker during deprecation; post-removal catalog/projection/reference gates | Fresh ownership, impact, and complete-diff review | Catalog, provenance, roadmap/evaluation/exit, and replacement links | Restore retained version when safe or supersede with a corrected transition | `deprecated` only when explicitly authorized; removal is not maturity |

Exact commands, scenario counts, and record depth remain phase- and
repository-owned. The defaults above are not universal gates for unrelated
projects.

## New-skill threshold

Retain a new skill only when all of the following are supported:

- one coherent reusable problem exists;
- instructions, existing skills, project policy, and native capability do not
  already own it adequately;
- the trigger is precise and material non-triggers are explicit;
- the procedure is independently removable;
- authority and project-owned policy remain outside the skill;
- source and derivation rights are known; and
- representative positive, non-trigger, edge or stop, and independent-review
  evidence supports retention.

Reject or route elsewhere when any missing condition is structural rather than
correctable within one bounded iteration.

## Source-derived work

Record one APG provenance mode:

- `copied`: expression is reproduced substantially verbatim;
- `adapted`: recognizable expression or structure is modified;
- `synthesized`: new APG-native expression combines evaluated ideas and project
  evidence without preserving source expression;
- `inspired`: a source prompted investigation but no material expression or
  procedure was retained.

External license labels do not replace complete rights and notice review for
copied or adapted expression. Preserve required notices before adoption.
Frequency, source ownership, or permissive-looking metadata does not establish
semantic value or APG authority.

## Scenario guidance

Use representative positive, non-trigger, and edge or stop behavior without a
fixed universal count. A new skill normally needs multiple independent positive
and non-trigger families. A frontmatter-only correction may use focused
discovery cases. A behavior-bearing correction compares current and candidate
behavior against the same frozen cases. Support/helper changes add direct
interface, failure, and safety evidence appropriate to the helper.

Comparative A/B evidence is optional unless a phase expressly makes it part of
the claim. Passing prose inspection is not a substitute for executable evidence
when behavior is deterministic and testable.

## Maintenance, deprecation, and removal

Re-evaluate an owner when evidence shows over-triggering, authority drift,
source or license change, changed harness discovery, repeated corrections,
stale project assumptions, better native capability, overlap with another
owner, or a credible deprecation/removal need.

Repeated correction is a design signal, not permission for indefinite editing.
Stop and reconsider the owner when the declared correction bound is exhausted
or when a correction changes the original problem, authority, or safety model.

Deprecation keeps the leaf only while an explicit transition needs it and uses
the `deprecated` catalog maturity when authorized. Removal reconciles the
canonical leaf, discovery projection, catalog, provenance, evaluations, active
references, replacement guidance, and rollback. Historical ADRs, exits, and
evaluations remain intact.

## Mechanical checker

Run:

```text
bin/apg-check-skill-library [--root <path>] [--format text|json]
bin/apg-check-skill-library --help
```

The default root is the repository containing the command. `--root` permits
read-only validation of another APG-shaped tree. Exit `0` means the adopted
mechanical subset passed; exit `1` reports library noncompliance; exit `2`
reports command-line misuse.

The checker validates:

- a real canonical `skills/` tree, regular `skills/README.md`, regular
  `SKILL.md` leaves, and contained optional `scripts`, `references`, `assets`,
  or `agents` directories;
- APG's plain-scalar `name` and `description` subset, name grammar, directory
  agreement, uniqueness, `Use when` descriptions, one H1, and exactly one of
  each adopted H2 owner;
- nonempty support directories and contained support symlinks;
- accepted same-line literal Markdown links and images outside fenced code,
  resolved from the containing Markdown file and contained within the leaf;
- the exact catalog table under the recognized current or historical catalog
  heading, including canonical bijection, links, trigger cells, and maturity
  vocabulary; and
- exact checked-in `.agents/skills/<name>` projections to each declared direct
  or `chatgpt/`-nested canonical path, resolved identity, and containment.

ADR 0022 and APG30 accept exactly direct leaves and
`skills/chatgpt/<name>` leaves while keeping projections flat. The checker
derives each exact relative target from the canonical path, keeps frontmatter
names globally unique, excludes namespace owners from counts, and rejects
unknown namespaces or deeper owners. Historical public policy remains
version-bounded rather than being reinterpreted by current development.

The parser deliberately does not implement general YAML or Markdown. Every
column-zero frontmatter mapping key must contain only ASCII letters, digits,
underscores, or hyphens followed immediately by its key-terminating colon.
Blank lines and comments remain accepted, and indented optional metadata is
uninterpreted. Required frontmatter values must use exact `name: value` and
`description: value` syntax as top-level, unquoted, one-line plain scalars
without inline comments. Unsupported top-level key syntax fails closed. Link
recognition is limited to unescaped same-line inline link/image syntax with a
literal token or angle-bracket destination; external schemes and fragment-only
references are not fetched, local fragments are removed before resolution,
and percent escapes are not decoded. Headings, links, and the catalog are
recognized only outside backtick or tilde fenced code. A closing fence must use
the opening marker character at least as many times and may contain only spaces
or tabs after the marker. Frontmatter is not scanned as Markdown. A contained
`.md` support symlink is scanned with local destinations resolved from the
symlink's containing directory. Unsupported Markdown forms receive no semantic
validation.

The checker cannot prove trigger quality, usefulness, authority, privacy,
source rights, provenance truth, scenario quality, client discovery or
invocation, over-triggering, maturity fitness, public-release completeness,
production readiness, or stable behavior. Those remain evidence and review
responsibilities. Passing the checker does not authorize a change or alter
maturity.

Public release completeness is mechanically owned by `apg-public-release` and
the strict public-surface policy under ADR 0009. That release gate composes the
skill-library checker but does not change this lifecycle, validate semantic
skill quality, or authorize maturity promotion.

## Phase records and identity checks

Skill work follows the
[phase and record identity guide](phase-and-record-identity.md). Assign the
canonical phase ID before implementation. Finalize the leaf, tests, catalog,
capability map, integration owners, provenance, evaluation, exit, and applicable
indexes before commit. Use semantic source versions and phase-local evidence
IDs as durable identities. Exact Git identities ordinarily belong in
post-commit managed reports or transient verification evidence; an explicitly
authorized publication-excluded reproducibility record may retain them without
becoming public or canonical identity.

Run the standard-library record checker when a phase changes records or current
owners:

```text
bin/apg-check-record-identity [--root <path>] [--format text|json]
  [--expect-available <phase>] [--expect-allocated <phase>]
```

It validates the adopted mechanical phase, ADR, exit, and index subset. A
focused changed-file and current-owner scan separately checks whether an
internal or maintainer-project hash is being used as a durable identity. Do not
replace that semantic review with a repository-wide hexadecimal ban.

Public v0.2.0 carries the six ADR 0010 `stable` dispositions without changing a
skill procedure. APG14 publication evidence is distribution evidence; future
skill correction, maturity rollback, deprecation, or removal continues to
require this lifecycle and separate authority.

Public v0.3.0 carries all nineteen ADR 0018 release-included skills: fourteen
stable and five provisional. APG24 distribution and lifecycle evidence does not
promote a provisional row, change a trigger, or substitute projection success
for this maintenance procedure. No `SKILL.md` changes in APG24.

APG25 applies one behavior-bearing correction to
`composing-approved-roadmap-assignments` after freezing three representative
before/after assignment pairs and a failing focused test. The leaf now loads
repository structured defaults, omits repeated ordinary procedure, and retains
authority, acceptance, stop, and successor boundaries. Its trigger, name,
provisional maturity, catalog row, projection, and route do not change.

APG26 applies this new-skill lifecycle separately to
`pytest-test-profile` and `converting-bash-scripts-to-python`. Each candidate
has current source and rights evidence, thirty frozen positive/non-trigger/edge
or stop families, failing-first focused contracts, explicit project and
authority boundaries, rollback, and fresh non-author review. Both are retained
`provisional`; pytest needs no behavior-bearing candidate correction, while
conversion uses one bounded option-injection correction. The generic native
skill scaffold does not add harness metadata or support directories when APG's
checked direct-child text-only leaf contract has no demonstrated need for them.

APG28A adopts the corrected move of the pytest-profile contract test beneath
the mirrored skill owner without changing `SKILL.md`, maturity, catalog,
projection, or route state. The runner collects it as pytest and the inventory
checks its production owner and exact mirror.

APG29 applies one behavior-bearing correction to each of
`implementing-with-test-discipline`, `planning-repository-work`,
`reviewing-and-verifying-repository-work`, and
`composing-approved-roadmap-assignments`. Fifty-one frozen cases cover useful-
test coverage remediation, scoped testing, mock and real boundaries, formal
and non-phase defaults, and manager-prompt compression. Names, triggers,
maturity rows, catalog descriptions, projections, and capability-map entries
remain unchanged.

APG30 applies this lifecycle to one new provisional subrouter and one
procedure-preserving canonical move. Thirty frozen cases cover direct and
nested discovery, catalog identity, flat projections, project/user lifecycle,
historical release compatibility, router ownership, and stop boundaries.
`chatgpt-manager-workflow` begins provisional. The moved
`composing-approved-roadmap-assignments` bytes and maturity remain unchanged;
its catalog path, flat projection, and local-map owner change together.

APG32 applies this lifecycle to `minitest-test-profile`. Current official
Minitest, separately extracted mock, Ruby, and RubyGems sources establish the
version and rights boundary before thirty-six trigger, non-trigger, semantic,
structural, and stop families are frozen. A failing-first mirrored contract
then covers the leaf, route, projection, and scenario inventory. The retained
candidate begins `provisional` after one bounded trigger and ownership
correction. The native
skill scaffold is used, while harness metadata and support directories are
omitted because the checked APG direct-child text-only contract demonstrates no
need for them.

APG33 applies this lifecycle to `dockerfile-profile`. Current official Docker
documentation, Dockerfile frontend, BuildKit, and OCI Image Spec sources
establish the version and rights boundary before forty trigger, non-trigger,
semantic, structural, platform, protected-data, truthfulness, and authority
families are frozen. A failing-first mirrored contract then covers the leaf,
route, projection, threshold rows, and scenario inventory. The retained
candidate begins `provisional` after one bounded context, ownership, and
measurement correction. The native
skill scaffold is used, while harness metadata and support directories are
omitted because the checked APG direct-child text-only contract demonstrates no
need for them.

APG34 applies this lifecycle to `vagrantfile-profile`. Current official
Vagrant release and development source, documentation, licensing, and declared
Ruby compatibility establish the version and rights boundary before forty
trigger, non-trigger, configuration, box, provider, plugin, network, folder,
provisioner, trigger, state, structural, truthfulness, and authority families
are frozen. A failing-first mirrored contract then covers the leaf, route,
projection, threshold rows, and scenario inventory. The retained candidate
begins `provisional` after one bounded source-semantics and machine-measurement
correction. The native skill scaffold is used, while harness metadata and
support directories are omitted because the checked APG direct-child text-only
contract demonstrates no need for them.

APG38 applies this lifecycle independently to the four APG37 replacement
candidates. `go-test-profile` and `go-cmp-test-profile` pass current-source
review, public-safe fixture conversion, isolated compatibility evidence, one
coherent correction cycle, and fresh corrected-state review, then begin
`provisional`. `matryer-is-test-profile` and `nix-test-profile` do not pass:
fresh corrected-state review finds new material attribution/false-escalation
and FreeBSD sandbox-default defects after their correction cycles. Both are
`deferred-material-defect`, and all current integration surfaces are removed.
Candidate deferral does not promote or block the retained owners.

APG39 re-authors the two deferred candidates as fresh authoring-branch
leaves from their APG38 corrected-state defects: wrapper severity follows
registration completeness rather than depth, relaxed-mode severity follows
causality rather than count, and sandbox defaults are stated separately and
exactly per platform with the actual configuration controlling. The
candidates are `authored-pending-independent-review`; the lifecycle's
independent review, fixtures, compatibility evidence, correction cycle, and
integration belong to a later separately authorized Codex phase.

APG40 applies that lifecycle. `nix-test-profile` passes one coherent
source-fact correction cycle, forty executable public-safe scenarios,
source-only corpus calibration, rights/privacy review, and fresh non-author
corrected-state review, then begins `provisional`. `matryer-is-test-profile`
is `deferred-material-defect`: its corrected-state equality mechanism still
misstates exact source, so the one-cycle rule forbids another behavior
correction and its current surfaces are removed. Mechanical public-test
privacy repair does not consume a behavior cycle.

APG41 applies readiness review to all fourteen live provisional rows without
promoting them. Minitest, Dockerfile, and Vagrantfile each receive one
candidate-independent removal-description repair: remove the public scenario
fixture with the focused test and derive surviving counts from live
inventories instead of embedding historical totals. These are rollback
wording and contract repairs, not behavior corrections. Fresh corrected-state
review accepts all three.

APG42 publishes the exact APG41 skill set without changing a leaf, trigger,
procedure, source calibration, route, projection target, or maturity row.
Release inclusion leaves fourteen rows stable and fourteen provisional.
`matryer-is-test-profile` and `go-testing-stack` remain absent; ADR 0026's
independent Go component ownership remains controlling.

APG49 applies the one-cycle rule to the APG48 matryer/is candidate. Exact
source and runtime review supports one correction pass, but fresh non-author
review then finds new material trigger, source-filename, subtest-severity, and
scenario-continuity defects. The lifecycle requires
`deferred-material-defect`, forward removal of current candidate surfaces, and
no integration. Mechanical evidence remains durable; it does not authorize a
second correction.

APG59 applies the same lifecycle to the APG58 CSS pilot. Failing-first
contracts reproduce five material gaps and one coherent correction improves
them without retuning 300/600/900. Fresh non-author corrected-state review
then finds material executable-contract and removal defects. The one-cycle
rule requires `rejected-material-defect`, forward removal of current candidate
surfaces, and no second behavior correction.

APG60 turns those defects into a candidate-independent entry gate rather than
another correction cycle. The closed fixture predates any replacement
candidate, exact response actions are evaluated structurally, complete
collection is mandatory, and retained/rejected cleanup is falsified against
every current owner. A future fresh candidate may consume this contract but
may not edit it, define its own retention tests, or treat the handoff as
authorizing authoring or integration.

Canonical leaves may exist only at `skills/<name>/SKILL.md` or
`skills/chatgpt/<name>/SKILL.md`. The namespace is not a skill, names remain
globally unique, and catalog links and projection targets must name the exact
canonical path. Adding another namespace class requires a separate design and
checker decision.
## APG60A retained-candidate closure

Before a future CSS candidate can be retained, its leaf, relative projection,
specification, contract map, fixtures, focused tests, route, catalog, maturity,
project allowlists, release owners, inventory, dynamic consumers, and current
narratives must agree through the actual-tree retained-surface checker.
Historical evidence remains preserved. Passing this mechanical closure does
not approve the candidate's prose or semantics.

## APG60B future-candidate closure

A future candidate contract map must bind the exact frozen contract digest,
all expected rows, and stable unique clause markers. Current narrative owners
carry one exact maturity-aware state marker. Python mirrors are checked only
through their declared assignments, and derived release owners are evaluated
through the closed isolated mechanism. Retention additionally requires a
terminal accepted candidate-decision ADR with index agreement; rejection
preserves the Rejected ADR as history. These rules do not authorize candidate
authoring or decide semantic adequacy.

## APG60C final-value and lifecycle closure

APG60C historically required one immutable supported assignment and a stronger
closed owner-source finality claim. APG60D supersedes that proof scope below.
Candidate markers remain the sole mechanical current-state authority; bounded
diagnostics do not replace human prose review. APG61 authoring must terminate
at the positive authored Proposed but unintegrated gate. Current survivor
owners must be direct regular no-follow files with strict declared-type
parsing, and any later terminal rejection must preserve its required public
and publication-excluded history.

## APG60D source-binding and phase-bundle closure

Future CSS owner declarations are read statically from exact source. The
checker proves one immutable declaration and refuses mechanically identifiable
protected-name writes. It does not claim runtime immutability, arbitrary
callback closure, or general library-mediated reflective call-effect closure.
Future lifecycle evidence uses the closed APG60D phase-history manifest, not
wildcards: authored state requires APG61, and retained or rejected state
requires APG61 plus APG62, on top of the complete APG58 through APG60D
foundation. Repository records are direct regular, UTF-8, nonempty, and
no-follow.

## APG60E repository-path ownership closure

Lifecycle authority files and current candidate owners are validated from one
resolved physical repository root. Direct regular files are opened and read
descriptor-relatively without following descendant symlinks; the read is
bounded, complete, and checked for metadata stability. Globs enumerate beneath
verified direct parents.

The candidate projection remains an exact relative symlink, but both its
parent hierarchy and its direct canonical target hierarchy are required to be
repository-resident. Future APG61 authoring must create every permitted owner
as a direct file beneath direct ancestors and terminate at the authored
Proposed but unintegrated gate.

## APG60F import and required-role closure

Dynamic consumers must load through the closed repository-import boundary;
external, symlinked, dangling, site-injected, cross-root, or parent-cached
dependencies cannot establish retained state. Candidate authority requires all
52 declared roles and exact authored, traceability, decision, binding, dynamic,
narrative, history, and report references.

Projection validation must revalidate the expected link and direct canonical
target after the composite read. Future APG61 authoring may not add or modify a
dynamic-consumer dependency and must preserve the APG60F contracts and
phase-history manifest.

## APG60G snapshot, role, and derived-set closure

APG60G preserves APG60F and requires dynamic consumers to use the pinned
repository root object used during source collection. It also requires the
complete exact sorted canonical skill set, a code-owned semantic registry for
all 52 required lifecycle roles, and entry/descriptor/entry coherence for
every authoritative regular-file read. Future APG61 authoring may not add or
modify a dynamic-consumer dependency, role authority, derived-set authority,
or read primitive, and must preserve the APG60G phase-history manifest.

## APG60H snapshot and full-path binding closure

Future authoring must preserve validated external worker scratch, parent-owned
termination cleanup, exact snapshot reads and lexical cleanup, present-chain
and double-observed absence, final pinned-root binding, retained projection
identity, and the APG60H phase-history manifest.

## APG60I worker temporary-root lifecycle closure

Future authoring must preserve APG60I's already-opened no-follow temporary-root
authority, descriptor-relative child creation, cleanup ownership before the
first create attempt, lexical absence proof, primary/secondary failure order,
and final path-chain revalidation. It must use the APG60I phase-history
manifest and preserve APG60H's exact-read and snapshot contracts.

## APG61 candidate authoring state

APG61 authored one unintegrated `css-language-profile` candidate — leaf,
specification, and contract map — on the preserved Claude authoring branch,
with ADR 0036 Proposed. This lifecycle is authored-proposed-unintegrated:
the candidate is design evidence, not a canonical skill; no catalog,
projection, capability-map, test, inventory, or release owner references it;
current candidate-state markers remain absent; and the skill-library checker
truthfully reports the transitional 29-canonical/28-catalog shape on the
authoring branch. Separately authorized APG62 validation decides retention,
amendment, or rejection.

## APG62 terminal candidate state

APG62 independently validates the APG61 candidate and terminates it as
rejected-preserved after fresh corrected-state review finds a new material
defect following the one permitted coherent correction. ADR 0036 is Rejected.
The current candidate leaf, specification, contract map, fixture, focused
tests, projection, catalog, maturity, capability, project, release, and test
inventory owners are absent; current markers remain absent and integrated
counts remain 28/28/28 with 14 stable / 14 provisional. Exact APG61 and APG62
history remains authoritative evidence. Raw historical revert is not a valid
removal method, and no successor is authorized.

## APG64 accepted Markdown architecture boundary

APG64 accepts ADR 0037 with amendment as architecture input only. A future
Markdown candidate, if separately authorized, must use the actual
parser/configuration as effective grammar; keep selection, ordered response,
and receiving-owner routing separate; satisfy only the 34 candidate-semantic
scenarios; and apply qualitative structural signals without numeric whole-file
bands. The two process invariants remain review-owned. This decision creates
no skill, catalog, projection, maturity, route, fixture, test, release, public,
or active surface and grants no successor authority.

## APG65 Markdown candidate authoring state

APG65 authored one unintegrated `markdown-language-profile` candidate —
leaf, candidate specification, and navigation-only scenario-coverage record
— on the preserved Claude authoring branch, with ADR 0038 Proposed. This
lifecycle is authored-proposed-unintegrated: the candidate is design
evidence, not a canonical skill; no catalog, projection, capability-map,
route, maturity, fixture, test, inventory, or release owner references it;
and the skill-library checker truthfully reports the transitional
29-canonical/28-catalog shape on the authoring branch while integrated
`main` remains 28/28/28. Separately authorized APG66 validation decides
retention, amendment, or rejection under the accepted register and the two
review-process invariants.

## APG66 Markdown retained lifecycle

APG66 completes that lifecycle as retained-provisional. The phase derives a
public-safe 34-row vector from accepted APG64, creates failing-first focused
tests, applies one coherent correction, preserves its exact patch before
fresh review, and then closes every catalog, projection, routing, project,
release, test, inventory, and narrative owner. Corrected-state review found no
new material defect, so ADR 0038 is Accepted with amendment. The generic CSS
lifecycle manifests remain CSS-specific; bounded Markdown integration tests
enforce retained-provisional exclusivity without inventing a CSS-style marker.

## APG66A Markdown automated-proof boundary

APG66A preserves the APG66 candidate and decision while correcting the test
evidence contract. The accepted APG64 register is the normative structured
source; the public-safe fixture is its exact executable projection. Maintained
automation may claim register-fixture identity, clause and scenario navigation,
locally encoded signal/source/rollback evidence, and named mutation-proven
guards. It may not copy expected fixture fields as observations, use unrelated
global tokens as mapped evidence, or claim complete parsing of natural-language
semantics. Fresh human corrected-state review remains the full semantic owner.

## APG66B Markdown exact-token and polarity boundary

APG66B forward-corrects that automated boundary without changing the accepted
candidate. Fixture vocabulary arrays must equal one independently owned,
ordered APG64 vocabulary; row membership alone cannot authorize a superset or
erase an accepted-but-unused token. Closed owner, selection, response, route,
signal, rollback, and source-boundary tokens use one lexical boundary that
rejects adjacent ASCII letters, digits, underscores, and hyphens. Seventeen
source rows retain bounded local positive and contradiction guards. The two
contradiction rollback classes remain exact in the register projection but are
human-reviewed distinctions; automation claims only shared local statement-
preservation evidence and explicit contradiction negatives. Numeric guards
reject normative thresholds, bands, classification, signals, responses, or
splits while permitting descriptive and expressly negative counts.

## APG66C Markdown clause-polarity boundary

APG66C preserves the accepted candidate and narrows Layer C to explicit
bounded states: positive, negative, conflicted, absent, or human-review-
required. Count subjects propagate only across named predicate coordination;
independent explicit subjects stop inheritance. Machine-enforced source,
signal, rollback, and targeted guards require local positive evidence without
a direct contradiction. Quoted, prohibited, negated, global-only, and larger-
token occurrences are not positive observations. Complete prose equivalence,
implicit contradiction, and complex discourse remain APG66 human authority.
The continuation also narrows one order-sensitive whole-process cache assertion
to relevant inspected-repository state; it changes no candidate semantics or
production importer behavior.

## APG66D Repository-import evidence boundary

APG66D preserves APG66C's bounded inspected-repository state model while
separating mapping entry presence from stored-value identity. A pre-existing
relevant module entry passes only when its key remains present and its value
is the identical object; `None` is a legal stored sentinel and is not a
missing-entry default. Relevant importer-cache entries already compared exact
key order, count, and object identity, so only adverse tests were added there.
This correction changes test evidence, not the production importer or any
Markdown semantic owner.

## APG67 JavaScript authoring boundary

APG67 proposes the JavaScript language-profile architecture and lean
contract without authoring a skill. A future JavaScript candidate-authoring
phase requires separate authorization and is bounded by the recorded
narrowings: ECMAScript language semantics only after goal and context are
established; no Node, browser/DOM, TypeScript, JSX, or toolchain ownership;
no numeric whole-file bands; no automatic JavaScript-to-TypeScript
migration; and mutation-negative executable evidence design decided by the
review phase. The frozen register's two process invariants stay outside any
future candidate's semantic prose.

## APG68 JavaScript authoring boundary

APG68 rejects ADR 0039 after the sole corrected state fails fresh semantic
review. The corrected architecture, contract, register, preimage, and ten
proposed narrowings are historical evidence, not an authoring contract. No
JavaScript candidate may be authored from them. APG69 is not recommended;
any future architecture requires new human authority.

## APG69 JavaScript authoring boundary

APG69 supplies that new human authority for architecture only. ADR 0040
(Proposed) and the layered contract define the future authoring
boundary: a narrower ECMAScript-core leaf with typed authorities and
layered decisions, no numeric whole-file bands, no automatic
JavaScript-to-TypeScript migration, and no complete prose-equivalence
claim from bounded parsing. Eligibility is
`authoring-eligible-with-narrowing`, but no candidate may be authored
until APG70 terminally decides ADR 0040 and a separate authoring
authority exists.

## APG70 JavaScript authoring boundary

APG70 terminally rejects ADR 0040 after fresh review finds new material defects
in the sole corrected state. The APG69 proposal, APG70 correction, registers,
and review artifacts are historical evidence, not an authoring contract.
Eligibility is `not-applicable-rejected`; no JavaScript candidate may be
authored from these materials. APG71 is not recommended, and any future
JavaScript architecture requires new human authority.

## APG71 TypeScript authoring boundary

APG71 supplies that separate new human authority for TypeScript
architecture only: ADR 0041 is Proposed, the eligibility result is
`authoring-eligible-with-narrowing`, and its eight recorded narrowings bind
any future TypeScript candidate — static semantics and boundary
identification only, exact compiler/config/project evidence per
version-dependent judgment, no `.tsx` plain selection, bounded embedded and
checked-JavaScript routes, no runtime claims from static success, and
blocked claims where exact source relations are unavailable. No TypeScript
candidate may be authored until ADR 0041 is terminally decided and a
separate authoring authorization exists. JavaScript candidate authoring
remains not recommended.

## APG72 TypeScript terminal authoring boundary

APG72 rejects ADR 0041 after fresh review finds new material defects in the
sole corrected architecture. Eligibility is `not-applicable-rejected`; the
architecture, contract, and registers are historical evidence, not an
authoring contract. No TypeScript candidate may be authored from them. APG73
is not recommended, and any later TypeScript architecture attempt requires
separate new human authority.

## APG73 production recovery authoring boundary

APG73 supplies that new human authority as governance, not profile authoring.
ADR 0042 accepts the production recovery charter: a future repairable defect
normally produces `repair-required`, up to three separately preserved rounds
are available by default, and terminal rejection or removal requires human
authority. Critical and High defects block integration; Medium and Low debt
must be explicit and human accepted. TypeScript is essential and TypeScript 7
is its intended primary generation; temporary TypeScript 6 is allowed only for
an exact required role with retirement criteria. CSS and JavaScript are
desirable; JSX is deferred. No candidate may be authored from rejected ADRs.
APG74 is a roadmap recommendation only and requires separate authority.

## APG74 TypeScript candidate authoring boundary

APG74 uses that authority for one narrow candidate authored fresh under ADR
0042 — not from the rejected ADR 0041 architecture. The candidate leaf,
specification, and navigation-only coverage follow the accepted Markdown
candidate lifecycle precedent; the fourteen-case TypeScript 7 intended-state
fixture is the executable authoring harness, smoke-checked in scratch with
an exact `typescript@7.0.2` pin and an explicit `not-required` TypeScript 6
disposition. The candidate is authored-proposed-unintegrated: no catalog
row, projection, maturity row, route, or maintained test exists for it, and
only separately authorized APG75 may harden, decide ADR 0043, and
provisionally integrate.

## APG75 TypeScript retained lifecycle

APG75 applies ADR 0042's bounded iterative-hardening contract: each coherent
correction is a separately preserved round followed by fresh non-author review.
Rounds 1 and 2 remain `repair-required`; Round 3 closes all material findings.
ADR 0043 is Accepted with amendment and the profile is retained provisional.
Removal, rejection, stable maturity, target mutation, publication, deployment,
and successor work remain human-owned decisions.

## APG75A reusable TypeScript maintenance boundary

Reusable language profiles consume project-selected compiler generations and
migration policies; they do not convert one target's destination into a
universal rule. TypeScript decisions keep Selection, Response, and route-owner
obligations separate. The maintained response set is exactly
`proceed-routine`, `inspect-before-judgment`, `bounded-local-decision`, and
`stop-and-escalate`. Compiler-backed maintenance uses the repository runner's
documented exact-compiler prerequisite and never installs a tool as an implicit
test side effect.
## APG76 CSS authoring boundary

A CSS decision binds the artifact class and whole-file owner before anything
else, and binds the exact module and level rather than citing CSS as one
authority. Selection, the four-value Response axis, and route obligations stay
disjoint, and routing never lowers a response. Present and required evidence
stay disjoint, and parser, transformer, and browser roles are bound
independently: a package in a manifest or lockfile is availability evidence and
never invocation evidence. A cascade winner is not named while the participating
declaration set is unknown, and a host component's embedded style region is
reasoned about at most as an embedded route.

## APG77 CSS repair-required lifecycle

Three coherent APG77 corrections each receive fresh immutable-object review.
The final review leaves two High evidence defects, so the default round budget
ends at `repair-required`. The candidate, fixture, tests, findings, and round
objects are preserved; ADR 0044 remains Proposed and no catalog, projection,
maturity, route, project, release, or integration-test owner is added. Further
repair requires explicit human continuation authority.

## APG77D CSS retained lifecycle

APG77D accepts exactly five bounded qualification limitations under explicit
human authority and retains the candidate as
`provisionally-integrated-with-known-debt`. The candidate specification,
maintained semantic scenarios, primary sources, exact target evidence, and
human and executable review own CSS semantics. Compact v3 is supporting
qualification evidence only. Four Medium items block stable maturity; the Low
schema redundancy does not block it by itself. Any debt-set, source, route,
lifecycle, or target change triggers the exact refresh behavior in the current
known-debt register.

## APG79 JavaScript repair-required lifecycle

APG79 preserves three coherent corrections with fresh immutable-object review.
Terminal review leaves two High and two Medium material defects, so the default
round budget ends at `repair-required-after-round-3`. The candidate, fixture,
tests, findings, and round objects are preserved; ADR 0045 remains Proposed and
no catalog, projection, maturity, route, project, release, or test-inventory
integration owner is added. Further repair requires explicit human continuation
authority.

## APG79A JavaScript continued repair lifecycle

APG79A exercises one separate human-authorized correction after the default
round budget. Four fresh immutable-object review lanes leave five Medium
material defects, so the lifecycle advances to
`repair-required-after-apg79a`. The candidate, fixture, correction, tests,
findings, and checkpoint are preserved; ADR 0045 remains Proposed and no current
integration owner is added. No post-review correction or implicit debt
acceptance occurs. Further repair requires a new human decision.

## APG79E JavaScript accepted-debt integration lifecycle

APG79E accepts `JS-QD-005` as one additional Medium supporting qualification
limitation without repairing the maintained managed-report proxy. Direct exact
report verification supplies the current workaround. All five JavaScript items
block stable maturity. With zero Critical, High, or unaccepted Medium/Low
findings and all ordinary product gates green, the candidate advances to
`provisionally-integrated-with-known-debt`, ADR 0045 is Accepted with amendment,
and the complete catalog, projection, maturity, route, project, release, test,
source-role, debt, and rollback owners are present.

## APG79D JavaScript source-evidence lifecycle

APG79D preserves the accepted four-item JavaScript qualification-debt decision
and corrects only Test262's current evidence role. A historical reviewed pin,
fresh mutable head, and exact rights object are distinct. Moving-head equality
is not a lifecycle gate when no corpus is consumed and rights are unchanged;
rights-role, licence-object, copied-expression, or corpus-use changes require
fresh review. The immutable historical false assertion is preserved and
superseded rather than rewritten or accepted as debt. Terminal non-author
review finds that the maintained historical-report-rewrite mutation does not
bind the managed report bytes. The candidate remains repair-required and
unintegrated, ADR 0045 remains Proposed, and further correction requires a new
human decision.

## APG79C JavaScript accepted-debt lifecycle

APG79C accepts exactly four Medium qualification limitations for provisional
integration without modifying the APG79B candidate or its supporting
qualification machinery. All four block stable maturity. A separate
unaccepted Medium source-identity defect stops integration, so the candidate
remains `repair-required-after-apg79b`, ADR 0045 remains Proposed, and no
current integration owner is added. APG80 is not recommended and the next
action requires human authority.


## APG79B JavaScript continued repair lifecycle

APG79B exercises one further separate human-authorized correction for exactly
the five APG79A findings. Five fresh immutable-object review lanes leave four
unique Medium material defects, so the lifecycle advances to
`repair-required-after-apg79b`. The candidate, fixture, correction, tests,
findings, and checkpoint are preserved; ADR 0045 remains Proposed and no current
integration owner is added. No post-review correction or implicit debt
acceptance occurs. Further repair requires a new human decision.
## APG80 Node.js candidate authoring lifecycle

APG80 authors one narrow Node candidate under the separated authoring lifecycle:
a concise procedural leaf carrying thirty uniquely marked stable clauses, a
specification carrying source, boundary, and detailed semantics, and a
navigation-only coverage record that answers where a decision is made and never
what its result is. Twenty-four scenarios cite twenty-nine of the thirty
clauses; the remaining clause is identified as operational-only rather than
padded into a scenario. The candidate is not split into module, process, CLI,
filesystem, and network skills, and no project-skill projection is added. The
lifecycle is `authored-proposed-unintegrated`; independent hardening in a
separate phase is required before any integration decision.

## APG81 Node.js hardening lifecycle

APG81 preserves three immutable corrections, then stops at the required repair
checkpoint after fresh review finds three High and two Medium
qualification-harness defects. The lifecycle is
`repair-required-after-round-3`: the candidate remains present and branch-only,
ADR 0046 remains Proposed, no Node debt is accepted, and no catalog,
projection, maturity, route, project, release, or test-inventory owner is
added. Further correction or disposition requires a new human decision.

## APG81H Node.js provisional integration

APG81H retains the hardened candidate, accepts ADR 0046 with amendment, and
installs the complete current integration owner set after independent State A
and candidate-preserving State B qualification. The lifecycle is
`provisionally-integrated`; maturity is provisional, Node debt is zero, and
rollback retains the candidate with lifecycle
`accepted-integration-rolled-back`. Stable maturity, readiness, publication,
deployment, and successor work require separate authority.
