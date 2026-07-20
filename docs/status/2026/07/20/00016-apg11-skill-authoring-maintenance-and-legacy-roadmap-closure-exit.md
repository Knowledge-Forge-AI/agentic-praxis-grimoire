# APG11 Skill Authoring, Maintenance, and Legacy Roadmap Closure Exit

## Phase identity

- **Phase:** APG11
- **Date:** 2026-07-20
- **Exit sequence:** `00016`
- **Disposition:** Complete — authoring lifecycle and mechanical validation adopted
- **Terminal result:** `authoring-lifecycle-and-mechanical-validation-adopted`
- **Controlling decision:** ADR 0008, Accepted

## Authority and objective

The human APG11 assignment accepts APG10 and authorizes a maintainer-facing
skill-authoring and maintenance procedure, one dependency-free read-only
mechanical skill-library checker, focused tests and dogfood, terminal closure of
the legacy candidate-theme ledger, public and publication-excluded evidence,
one private development commit and push, and linked managed reports.

The phase may not add or change a current skill, promote maturity, add a
dependency, evaluator, plugin, registry, or runtime, mutate public or reference
repositories, change global integration or RepoMap, restore Superpowers,
publish a release, or start APG12 through APG14.

## APG10 acceptance

APG10 is accepted as Complete — targeted APG refinements validated. ADR 0007,
the experimental-source dispositions, one bounded implementation-discipline
correction, complete source and rollback evidence, and unchanged six-skill
`provisional` maturity are retained. APG11's retrospective application confirms
that APG10 satisfied the semantic and predecessor-gate portions of the new
behavior-correction lifecycle; APG11's current checker supplies the newly
adopted mechanical gate rather than rewriting APG10 history.

## ADR 0008 and normative guide

[ADR 0008](../../../../adr/2026/07/0008-skill-authoring-maintenance-and-mechanical-validation.md)
accepts [`docs/skill-authoring-and-maintenance.md`](../../../../skill-authoring-and-maintenance.md)
as the normative skill-specific lifecycle owner. The project model remains the
general destination and practice-lifecycle owner; the catalog owns current
leaves and maturity; provenance owns source and rights records; evaluations and
exits own bounded evidence; and the checker owns only adopted mechanical
invariants.

The guide distinguishes new skills, frontmatter-only corrections, behavior-
bearing corrections, support/helper additions, maturity-only dispositions, and
deprecation/removal. Each class has proportional evidence, a finite correction
bound, mechanical gates, review, records, rollback, and maturity effect. APG
creates no seventh authoring skill.

## Checker command and scope

`bin/apg-check-skill-library` is a thin executable over one Python 3.10+
standard-library helper:

```text
apg-check-skill-library [--root <path>] [--format text|json]
apg-check-skill-library --help
```

The default root is the command repository. Exit `0` means the adopted
mechanical subset passed, exit `1` means library noncompliance, and exit `2`
means usage or invalid installation layout. Text and schema-versioned JSON are
deterministic and repository-relative. The wrapper disables bytecode writes;
the command performs no repair, Git operation, subprocess, network request,
package-manager action, or third-party import.

The checker validates canonical real directories and regular UTF-8 leaves,
APG's required plain-scalar frontmatter subset, name grammar and agreement,
trigger-oriented descriptions, one H1 and seven adopted H2 owners, nonempty
support shape and contained symlinks, accepted local links outside frontmatter
and fenced code, exact catalog shape/bijection/link/maturity, and exact checked-
in Codex projection type/raw-target/resolved identity.

## Semantic and mechanical boundary

The checker does not prove trigger quality, usefulness, authority, privacy,
source rights, provenance truth, scenario quality, over-triggering, client
discovery or invocation, maturity fitness, public-release completeness,
production readiness, or stable behavior. It is not a general YAML, Markdown,
Agent Skills, harness-metadata, evaluator, or publication validator. Passing it
does not authorize a change or alter maturity.

## Test and dogfood result

Failing-first evidence preceded production. The absent helper and executable
failed the initial 11-unit and 46-case integration surfaces. Six checker-review
regressions then failed before the bounded parser/safety correction, and one
missing-helper regression failed before the complete-diff correction.

The final focused result is:

- 11 of 11 lexical-parser unit tests passed;
- 56 of 56 command integration tests passed with the fresh public v0.1.0 root
  supplied;
- all 34 assignment-required behavior families are represented;
- valid generated libraries passed and invalid generated libraries returned
  bounded sorted diagnostics and exit `1`;
- usage and invalid installation returned exit `2`; and
- target and command-repository fingerprints were unchanged.

Development and fresh public v0.1.0 checks both reported six canonical skills,
six catalog rows, and six projections in text and deterministic JSON. The
public pass covers skill-library structure only. It does not hide or repair the
known omitted public `bin/apg-project-skills` wrapper; APG12 retains that
publication defect.

## Dogfood dispositions

The retrospective APG10 review confirmed owner, rights boundary, frozen
scenarios, baseline, one correction, candidate rerun, non-author review,
predecessor regression gates, provenance, rollback, and unchanged maturity.

A generic Karpathy Guidelines skill remains unjustified because its useful
ideas are already covered, project-owned, rejected, or resolved through one
existing owner. A skill-authoring skill remains unjustified because the project
model, provenance policy, maintainer guide, checker, and review procedure
already own its separable concerns. Neither proposal demonstrates an
independently triggerable gap.

## Legacy roadmap closure

The terminal ledger contains stable IDs `LT01` through `LT24` exactly once:
nine implemented, one implemented by APG11, five future-active, six conditional,
and three rejected or project-owned. Composite implementation/test and review/
delivery themes preserve their distinct sub-dispositions. APG12 owns two
distribution questions, APG13 owns broader maturity and explicit post-
Superpowers review as distinct questions, and APG14 owns public v0.2
publication. Future ownership closes a legacy question without claiming future
implementation.

## APG skill use and debugging disposition

`designing-significant-changes`, `planning-repository-work`,
`implementing-with-test-discipline`, `composing-bounded-worker-assignments`, and
`reviewing-and-verifying-repository-work` applied within their triggers.
`debugging-systematically` was a material non-trigger for expected missing-
implementation failures, then triggered for one pre-existing Bats concurrency
failure during a parallel multi-suite run. The focused case and complete Bats
suite passed serially; no APG11 production path participated and no code change
was justified.

## Independent reviews

Four pre-implementation analyses covered lifecycle, invariants, ledger, and
design. The design critic returned `correction-required`; all six findings were
corrected before production.

Fresh checker/safety and process/roadmap reviewers each returned
`correction-required`. Their eleven combined parser, safety, source-rights,
ownership, sequencing, dogfood-timing, and ledger-wording findings were
corrected. Narrow confirmations returned `pass` with no residual finding.

A fresh complete-diff reviewer inspected the exact 20-file staged terminal
candidate at staged-patch SHA-256
`fe51c44a0feadbdbe3c95a15aee92f23c82130730838e663f8dd9b14d327131f`,
returned `correction-required` for two residuals, and then accepted both
corrections with no residual finding at staged-patch SHA-256
`bda2ec785470a817beca0408e3f0e152f000d2911e513b50cbdd398626937288`.
Terminal record integration then received a final narrow confirmation. The
reviewer required the ADR and exit dates to follow the introducing commit's
local `2026-07-20` date; after that correction, the complete 22-file staged
state passed with no residual substantive finding.

## Validation

Fresh validation of the complete resulting state established:

- development and public v0.1.0 checker text/JSON passes with six skills, rows,
  and projections;
- 11 of 11 checker unit tests and 56 of 56 checker integration tests;
- 22 of 22 Bats report-tool tests and 28 of 28 project-skill integration tests;
- Python byte compilation, executable syntax, and command help;
- deterministic text/JSON, correct noncompliance and usage exits, and no
  checker mutation;
- six canonical skills, six exact checked-in projections, and six
  `provisional` catalog rows;
- Markdown heading/fence/local-link and public confidentiality checks;
- exact 24-row legacy-ledger coverage without a lost active theme;
- ADR sequence `0001` through `0008` and exit sequence `00001` through `00016`;
- no dependency, plugin, registry, runtime, seventh skill, maturity, public
  release, global integration, RepoMap, or Superpowers mutation;
- clean unchanged public and reference repositories and unchanged global and
  RepoMap tracked states; and
- staged and unstaged Git whitespace checks.

## Unchanged skill hashes and maturity

| Skill | APG10 baseline and APG11 final SHA-256 | Maturity |
| --- | --- | --- |
| `composing-bounded-worker-assignments` | `4613b98e84708e97ff35dd109179139e54c9167d0bf0b11d6aa1ffa5a2c76bca` | `provisional` |
| `debugging-systematically` | `d7bd9e4dfb27f9e334cdcbfb0ffaf6b8f2a8f26529ee421ee39271f383148316` | `provisional` |
| `designing-significant-changes` | `08b9c9ecde90ce047303e25610711c26f026dd6e4e91ed7cef3b701a7e043f90` | `provisional` |
| `implementing-with-test-discipline` | `d700441d21ce72ed76cdae1bc4fb047e5869b0c560dab9e5533aafa6b7d0ccc0` | `provisional` |
| `planning-repository-work` | `4571258a3e1bd70381d3b01d9c15fffc783e9028ecc3cfa58c659b6d157cca8b` | `provisional` |
| `reviewing-and-verifying-repository-work` | `cd6650ba75a46cc1c5be3d4a846e903f185a80a1b40f5dbb89175046a6118740` | `provisional` |

No current `SKILL.md` or discovery projection changed.

## External state and artifacts

Public v0.1.0, the reference repository, public-backed global checkout and link
chain, RepoMap, and Superpowers retirement remain unchanged. No operation
targeted public release state, global integration mutation, RepoMap lifecycle,
or Superpowers installation or restoration.

Public artifacts are ADR 0008, the maintainer guide, checker and tests, legacy
ledger, APG11 evaluation, reconciled project owners, and this exit. Five
publication-excluded records retain exact development analysis, tests, dogfood,
ledger, and reviewer evidence. Public artifacts do not link to private records.

## Subsequent correction: APG11A

APG11A subsequently reproduced and corrected two lexical false negatives in
the APG11 helper: unsupported top-level required-key aliases could escape the
required-key checks, and a same-marker fence line with trailing text could be
mistaken for a closer. The forward correction adds a narrow top-level key
grammar and a same-character, sufficient-length, trailing-whitespace-only fence
closure rule. Failing-first tests establish that the APG11 implementation did
not already contain these corrections.

The APG11 lifecycle, accepted ADR, checker purpose, standard-library
architecture, 24-theme ledger, and historical 11-unit/56-integration result
remain accepted. APG11A expands the corrected surfaces to 15 unit and 58
integration tests and leaves all six skills, projections, and `provisional`
maturity states unchanged. The APG11A exit records the exact correction result;
APG12 remains next and unstarted.

## Limitations

- The checker intentionally supports a narrow lexical subset and does not
  defend against a hostile concurrent local writer.
- Passing structure makes no semantic, discovery, release, or maturity claim.
- The public v0.1.0 wrapper omission remains unresolved until APG12.
- No automatic invocation, clean A/B superiority, stable maturity, release
  candidate, restoration exercise, or additional harness was evaluated.
- Terminal delivery still requires the APG11 commit, push parity, and linked
  managed reports.

## Next authorization

APG12 is the next accepted roadmap phase but has not started. It requires a
separate human assignment. APG11 authorizes no successor work automatically.

## External disposition requested

External review is requested to **accept APG11 as Complete — authoring lifecycle
and mechanical validation adopted; accept ADR 0008 and the normative guide;
accept the dependency-free read-only checker and terminal 24-theme ledger;
retain exactly six `provisional` skills; preserve public, reference, global
integration, RepoMap, and Superpowers state; and authorize no APG12 work
automatically**.
