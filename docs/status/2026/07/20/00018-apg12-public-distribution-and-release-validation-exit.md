# APG12 Public Distribution and Release Validation Exit

## Disposition

**Complete — public distribution and release validation adopted**

## Authority and objective

The human maintainer's APG12 assignment accepts APG11A, authorizes this bounded
private-development architecture, tooling, test, documentation, and validation
phase, and supplies acceptance authority for ADR 0009. APG12 formalizes a
complete public projection, reproducible local release candidates, and a safe
user-scoped lifecycle sourced from verified public releases. It does not
authorize public or reference mutation, active integration mutation, a plugin,
skill or maturity changes, APG13, or APG14 publication.

## APG11A acceptance

APG11A is accepted as **Complete — required-key and fenced-code validation
corrected**. Its bounded lexical corrections, deterministic `APG035`, 15-unit
and 58-integration checker results, existing regressions, independent reviews,
unchanged ADR 0008 architecture, unchanged six skills and projections, and
unchanged `provisional` maturity states remain accepted.

## Accepted architecture and implementation

[ADR 0009](../../../../adr/2026/07/0009-public-distribution-and-reproducible-release-validation.md)
accepts one complement projection: every tracked path outside `private/` enters
the public candidate exactly once with identical raw path, type, executable
mode, bytes, and symbolic-link target. A strict public schema-version-1 policy
adds critical wrapper, helper, test, license, notice, contribution, CLA, skill,
projection, governance, and release-owner checks without becoming an
omission-capable allowlist.

Each public version appends one squashed commit whose sole parent is the prior
accepted public head. Explicit identity and timestamp inputs make the projected
tree, release commit, and annotated tag reproducible. APG12 creates disposable
local candidates only; it performs no network operation, push, publication, or
public mutation.

[`apg-public-release`](../../../../../bin/apg-public-release) is a dependency-free
Python 3 and Git command with `manifest`, `build`, and `check`. It constructs
from committed Git objects, refuses dirty repositories and unsafe outputs, and
checks the exact surface, history, tag, deterministic manifest, configured
tests, syntax, help, compilation, links, generic confidentiality, and licensing
owners.

[`apg-user-skills`](../../../../../bin/apg-user-skills) is a separate
dependency-free Python 3 and Git command with `list`, `install`, `adopt`,
`check`, `update`, `rollback`, and `uninstall`. It validates clean tagged public
sources, manages six direct user-scope links, stores strict XDG-compatible
ownership and previous-source state, uses mode-`0600` atomic state and a
persistent lock, warns about repository duplicates without claiming
precedence, removes only proven ownership, and provides restart guidance.

## Tests, omission regression, and dogfood

The focused resulting suites pass:

- 8 of 8 release-helper unit tests;
- 22 of 22 release-command integration tests;
- 8 of 8 user-helper unit tests; and
- 29 of 29 user-command integration tests.

Existing gates also pass: 15 of 15 checker unit tests, 58 of 58 checker
integration tests using a fresh public root, 22 of 22 report-tool Bats
families, and 28 of 28 project-skill integration families.

The release regression reproduces the public v0.1.0 class in which documentation
and implementation modules exist but `bin/apg-project-skills` is omitted. The
checker rejects that projection for the missing wrapper and exact-tree
disagreement.

Disposable dry runs use a fresh v0.1.0 base, a committed snapshot of the final
development state, fixed prerelease metadata, two independent candidate
outputs, and temporary user discovery/state roots. The candidates match in
tree, commit, annotated tag, and manifest and pass the complete candidate gate.
The user lifecycle passes v0.1.0 install and check, repository-duplicate
warning, candidate update and check, exact rollback and check, and uninstall
while preserving an unrelated skill and repository fingerprints. No candidate
is pushed or published.

## Safety, reviews, and preservation

The implementation includes strict policy ownership, source/base/output
separation, physical containment checks, branch and tag collision refusal,
sole-parent and metadata verification, no manifest-selected execution, exact raw
link targets, all-path preflight, state-last recovery, and created-container
identity checks. The manifest exposes projected entries and hashes without a
private development commit or full-tree identity.

Five bounded design-stage analyses and three fresh final non-author reviews
cover release safety, user-scope safety, and the complete diff. Material
design-stage findings were corrected and received focused regression evidence;
the final reviews found no unresolved blocker or material defect.

The active public-backed integration was inspected read-only and remains in its
legacy aggregate-link shape. Public, reference, active integration, and RepoMap
repositories remain unchanged. No operation restored or used Superpowers as
workflow authority.

## Skill use and non-triggers

`designing-significant-changes`, `planning-repository-work`,
`implementing-with-test-discipline`, and
`reviewing-and-verifying-repository-work` governed the architecture, dependent
execution, failing-first evidence, and acceptance. The bounded-assignment skill
governed authorized analyses and reviews. Systematic debugging triggered only
for an unexplained physical-path alias discovered by an output safety test.

Plugin creation, a general packaging framework, registry, daemon, hosted
service, dependency, new skill, public publication, maturity promotion, APG13,
and APG14 were material non-triggers or explicit non-goals.

## Artifacts, maturity, and limitations

Public artifacts are ADR 0009, the public-surface policy, two commands and
helpers, focused tests, release and user guides, the APG12 evaluation,
reconciled owner documents, and this exit. Publication-excluded design,
inventory, dogfood, integration-comparison, and review records retain exact
private operational evidence. Public files do not depend on or link to those
records.

All six `SKILL.md` files and six checked-in `.agents/skills` projections are
unchanged from the APG11A baseline. All six skills remain `provisional`.

The commands trust local APG and Git, do not sandbox candidate tests, do not
defend against hostile same-user races, and cannot decide semantic
confidentiality, provenance sufficiency, license interpretation, discovery
precedence, or automatic invocation. Direct user links require their recorded
source checkout to remain available.

## Next authorization

APG13 is the next roadmap phase and requires separate human authorization. It
owns individual six-skill stability dispositions. APG14 remains separately
authorized and alone owns the real v0.2.0 candidate, active integration update,
public push, public tag, publication, and closeout. APG13 and APG14 have not
started and do not begin automatically.

## External disposition requested

External review is requested to **accept APG12 as Complete — public
distribution and release validation adopted; retain APG11A acceptance, ADR
0009, the exact non-private public projection, one-squashed-commit release
model, strict public-surface policy, dependency-free release and user-scope
commands, executable v0.1 omission regression, reproducible isolated dogfood,
unchanged active/public/reference/RepoMap/Superpowers state, exactly six
unchanged provisional skills and projections, the APG13 and APG14 boundaries,
and authorize no successor phase automatically**.

## Subsequent correction: APG12A

This record remains the historical APG12 exit. Its original test and dogfood
results describe the implementation at the APG12 commit; that commit did not
already contain the APG12A fixes.

APG12A later reproduced and corrected four tooling violations: unrelated bases
were accepted, later user history could contain an untagged intermediate
commit, configured validation could mutate original release repositories, and
read-only checks could leave candidate or user-state mutations. The correction
anchors both tools to one exact public lineage, moves executable validation to
isolated disposable repositories and state roots, and makes user `check`
non-creating with a shared existing lock. It retains this exit's accepted
projection, policy, lifecycle, omitted-wrapper regression, skill state, and
APG13/APG14 boundaries.
