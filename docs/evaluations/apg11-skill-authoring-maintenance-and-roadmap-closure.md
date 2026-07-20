# APG11 Skill Authoring, Maintenance, and Roadmap Closure Evaluation

## Objective

APG11 formalizes repeated skill-authoring and maintenance practice without
creating another skill, adds one dependency-free read-only checker for stable
mechanical skill-library invariants, and closes every former unnumbered
candidate or explicitly deferred roadmap theme. It does not change a current
skill, maturity, dependency, release, public checkout, global integration,
RepoMap repository, or Superpowers retirement state.

## Repeated-practice basis

APG4 established six canonical leaves, frontmatter, structural owners,
scenario evidence, provenance, review, and rollback. APG6 corrected one
frontmatter discovery boundary. APG7 and APG7A added failing-first executable
evidence, deterministic helpers, bounded correction, recovery, and independent
review. APG9 reconciled release and transition facts. APG10 froze scenarios,
established current behavior, made one behavior-bearing correction, reran the
same cases, preserved provenance, and retained rollback and maturity boundaries.

Four independent APG11 analyses separately reviewed the lifecycle, mechanical
invariants, legacy ledger, and proposed design. The design review required
corrections for Python bytecode writes, justified `agents/` metadata,
frontmatter/Markdown/catalog lexical boundaries, duplicate maintenance
ownership, stable ledger identities, and APG11's own rollback. ADR 0008 and the
implementation incorporate those corrections.

The pinned specification is documentation under Creative Commons Attribution
4.0 International; repository code is separately Apache-2.0. APG11 copies or
adapts neither specification expression nor upstream code. It independently
implements compatible format facts and project-authored constraints, and the
immutable specification and license links provide attribution. No bundled
third-party license or notice text is required for that synthesized use.

## Accepted decision and owner

[ADR 0008](../adr/2026/07/0008-skill-authoring-maintenance-and-mechanical-validation.md)
accepts the [skill authoring and maintenance guide](../skill-authoring-and-maintenance.md)
as the normative skill-specific lifecycle owner. The project model remains the
general artifact-destination and practice-lifecycle owner; the skill catalog
owns current leaves and maturity; provenance owns source and rights facts;
evaluations and exits own bounded evidence; and the checker owns only adopted
mechanical invariants.

APG adds no skill-authoring leaf. The work is maintainer governance with
authority, evidence, and repository-policy inputs rather than a generally
triggerable execution procedure.

## Lifecycle and change classes

The guide uses ten steps: authorize the problem, inspect existing owners,
inventory sources and rights, classify the change, freeze proportional
acceptance/non-trigger/edge/stop/rollback evidence, establish baseline behavior
when behavior changes, author the smallest APG-native artifact, run scenarios
and mechanical checks, obtain independent review, and record provenance,
maturity, maintenance, disposition, and rollback.

Its change-class matrix distinguishes new skills, frontmatter-only discovery
corrections, behavior-bearing procedure corrections, support/helper additions,
maturity-only dispositions, and deprecation/removal. Evidence, correction
bounds, mechanical gates, records, review, rollback, and maturity effect scale
with the class rather than using one universal ceremony.

## Semantic and mechanical boundary

`bin/apg-check-skill-library` is a thin Python wrapper over one Python 3.10+
standard-library helper. The wrapper disables bytecode writes before loading the
helper. The command surface is:

```text
apg-check-skill-library [--root <path>] [--format text|json]
apg-check-skill-library --help
```

The default root is the repository containing the command. Success returns
`0`, library noncompliance returns `1`, and usage failure returns `2`. Text and
schema-versioned JSON output are deterministic, repository-relative, and
read-only.

The checker validates the canonical tree and regular leaves, APG's required
plain-scalar metadata subset, name grammar and directory agreement, trigger-
oriented descriptions, one H1 and the seven adopted H2 owners, accepted
nonempty support shape, contained support symlinks, accepted literal local
links outside fenced code, the exact catalog table and maturity vocabulary, and
checked-in Codex projection set/type/raw-target/resolved identity.

It does not implement general YAML or Markdown and does not prove semantic
trigger quality, usefulness, authority, privacy, source rights, provenance
truth, scenario quality, client discovery or invocation, over-triggering,
maturity fitness, public-release completeness, production readiness, or stable
behavior.

## Tests and dogfood

The principal unit and integration surfaces were written before production.
The unit suite initially failed because the helper did not exist. The
integration suite produced 45 expected executable-not-found errors and one
environment-gated public-check skip because the command did not exist.

After implementation:

- 11 lexical-parser unit tests pass;
- 56 command integration tests pass, including the supplied fresh public
  v0.1.0 checkout;
- all 34 required behavior families are represented;
- development text and JSON checks report six canonical skills, six catalog
  rows, and six projections;
- public v0.1.0 text and JSON checks report the same structural counts;
- valid generated libraries pass and representative invalid generated
  libraries produce bounded, sorted diagnostics and exit `1`; and
- target and command-repository fingerprints remain unchanged across ordinary
  checker execution.

The public v0.1.0 pass concerns only the skill-library structure. It does not
hide or correct the known omitted `bin/apg-project-skills` wrapper; APG12 still
owns that publication defect.

## Retrospective APG10 dogfood

APG10 satisfies the semantic and predecessor-gate portions of the new behavior-
bearing correction contract without rewriting its history. It identified
`implementing-with-test-discipline` as the owner,
bounded source rights and derivation, froze twelve scenarios, established
current behavior, made one correction, reran affected positive/non-trigger/edge
cases, obtained fresh non-author leaf review, passed regression gates, updated
provenance, recorded rollback, and left maturity unchanged. APG11's current
checker pass supplies the newly adopted mechanical gate that could not have run
during APG10.

## Subsequent correction: APG11A

APG11A preserves the accepted lifecycle, checker purpose, parser architecture,
and legacy-roadmap closure while correcting two independently reproduced
lexical false negatives in the original helper. A quoted or whitespace-before-
colon top-level `name` or `description` key could shadow the accepted required
entry because APG11 scanned only exact required-key prefixes. A same-marker
fence line with trailing language text could close an open fence because the
opening-prefix recognizer also served as the closing test.

APG11A first added focused behavioral evidence. Against the unchanged APG11
helper, the 15-test unit surface failed 12 required-key and fence subcases, and
the 58-test integration surface failed exactly the two new command cases by
returning exit `0`. The correction adds one narrow top-level key recognizer,
diagnostic `APG035` for unsupported column-zero key syntax, and a closing-fence
contract requiring the same marker, sufficient length, and no trailing content
other than spaces or tabs.

After correction, 15 unit tests, 58 checker integration tests, 22 report-tool
Bats families, and 28 project-skill integration families pass. Generated cases
reject quoted, whitespace-before-colon, tabbed, and explicit mapping-key forms
for both required keys; nested optional metadata remains supported; and the
reproduced hidden `## Procedure` fails with `APG016`. Development and fresh
public v0.1.0 libraries pass in deterministic text and JSON modes without
mutation. A fresh checker reviewer accepted the correction with no finding.

This is subsequent correction evidence. It does not claim that the APG11
commit already contained the fix, change any skill or maturity state, conceal
the public v0.1.0 wrapper omission, or start APG12.

## New-skill rejection dogfood

A generic Karpathy Guidelines skill remains unjustified because APG10 found the
useful themes already owned, project-owned, rejected, or addressable by one
existing procedure correction. A skill-authoring skill is also unjustified:
the project model, provenance policy, maintainer guide, checker, and review
procedure already own its separable concerns. Neither proposal demonstrates an
independently triggerable ownership gap, and both would duplicate existing
authority and procedure.

## Legacy roadmap closure

The [legacy roadmap ledger](../legacy-roadmap-closure.md) assigns 24 stable
identities and terminal dispositions: nine implemented, one implemented by
APG11, five future-active, six conditional, and three rejected or project-
owned. Composite implementation/test and review/delivery themes retain explicit
sub-dispositions. The two APG13 questions remain distinct: broader evidence and
maturity disposition versus explicit post-Superpowers suitability.

Future-active ownership closes a legacy question but does not claim
implementation. APG12 owns two distribution questions, APG13 owns two skill-
review questions, and APG14 owns public v0.2 publication.

## APG skill use and non-triggers

`designing-significant-changes` resolved the owner, parser, safety, and rollback
decisions. `planning-repository-work` organized the dependent implementation and
documentation sequence. `implementing-with-test-discipline` governed failing-
first checker work. `composing-bounded-worker-assignments` bounded the four
authorized independent analyses. `reviewing-and-verifying-repository-work`
governs artifact acceptance and completion evidence.

`debugging-systematically` remained a non-trigger for the expected missing-
implementation failures. It triggered later when one pre-existing Bats
concurrency case failed during a parallel multi-suite run after passing at
baseline. The case and then the complete 22-test suite passed serially; no APG11
production path participated, so the evidence supported no code correction and
the final gate remained serial.

## Independent review

The pre-implementation design critic returned `correction-required`; all six
material corrections were incorporated before production implementation. The
fresh checker/safety review and process/roadmap review also returned
`correction-required`. Their frontmatter/body isolation, contained Markdown
symlink, catalog-column, diagnostic escaping, installation exit, source-rights,
completion-timing, APG10 timing, and ledger-wording findings have been corrected.
Narrow confirmation accepted both focused review correction sets. A fresh
complete-diff reviewer then returned `correction-required` for two residuals;
the candidate-summary and missing-helper corrections passed narrow confirmation
at staged-patch SHA-256
`bda2ec785470a817beca0408e3f0e152f000d2911e513b50cbdd398626937288`
with no residual finding.

## Limitations

- The checker validates an APG lexical subset, not complete YAML, Markdown,
  Agent Skills, harness metadata, or release compatibility.
- Passing structure does not establish semantic or maturity claims.
- External links are not fetched, unsupported Markdown link forms are not
  semantically validated, and optional YAML is uninterpreted.
- The public v0.1.0 wrapper omission remains unresolved until APG12.
- APG11 evaluates no automatic invocation, clean A/B superiority, stable
  maturity, release candidate, restoration exercise, or additional harness.

## Disposition and next boundary

APG11 is accepted as one maintainer procedure, one narrow mechanical checker,
and one closed legacy ledger. All six skill leaves remain byte-identical to the
APG10 baseline and remain `provisional`.

APG12 is the next separately authorized phase. It owns public-sourced global
integration and validated public projection/release mechanics. APG11 does not
begin APG12, APG13, APG14, public mutation, global integration change, RepoMap
mutation, Superpowers restoration, maturity promotion, or v0.2 publication.
