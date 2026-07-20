# APG9 v0.1 Closeout and v0.2 Roadmap

## Objective and result

APG9 closes the v0.1 development epic, reconciles current state after public
release and Superpowers decommission, and accepts the bounded v0.2 roadmap in
ADR 0006.

Terminal result: `v0-1-closed-v0-2-roadmap-accepted`.

APG0 through APG8 are the closed v0.1 epic, with every historical terminal
outcome preserved, including APG3's blocked preflight. The APG9 human assignment
supplies APG8's previously requested final external acceptance. APG-TEST0 is the
first post-v0.1 development-foundation phase.

## Public v0.1.0 and release model

Public APG v0.1.0 exists as one intentionally squashed public commit, distinct
from private development history. It contains the six canonical skills, Codex
repository discovery links, reporting components, public governance,
evaluations, status records, and licensing and contribution terms. The public
checkout is the canonical source for the maintainer's separately managed
user-global Codex integration.

The release has one material tracked-surface limitation: public documentation
requires the project-local projection command, but the public v0.1.0 tree omits
its `bin/apg-project-skills` wrapper while retaining the implementation modules.
The release also predates APG-TEST0's reproducible test layout and retains some
pre-publication current-state text. APG9 does not modify or republish the public
repository. APG12 owns a validated projection and reproducible squashed-release
process that must detect this class of omission.

## User-global and project-local integration

The maintainer implemented user-global discovery from a clean public checkout.
All six public skill leaves were observable in the current Codex environment,
and their content matched public v0.1.0.

This global integration is distinct from APG's repository-local and managed
project-local projections. RepoMap retains six managed project-local links to
the APG development source, and both supported managed check forms passed
during APG9 without changing RepoMap. Duplicate names may therefore appear from
global and project scope; discovery precedence and deduplication belong to the
client, and APG does not infer an invocation source from a name alone.

APG12 must formalize global update, check, uninstall or disable, rollback,
restart, duplicate-scope, and failed-update recovery behavior. The existing
project-local command remains outside global installation ownership.

## Superpowers decommission and smoke

The maintainer explicitly decommissioned Superpowers. A bounded fresh RepoMap
smoke discovered all six APG skills, explicitly selected and successfully
applied `reviewing-and-verifying-repository-work`, passed default and explicit
managed checks, preserved RepoMap's clean tracked state, and did not use
Superpowers as workflow authority.

The preserved Superpowers source remains external historical evidence. It is
not installation, current policy, or restoration authority. APG9 does not
reinstall, restore, invoke, or modify Superpowers.

The closeout facts do not establish an exhaustive active-project inventory,
automatic skill selection, universal workflow coverage, comparative
superiority, or tested restoration. They are sufficient for the maintainer's
bounded v0.1 decommission closeout without promoting a skill.

## APG8 and APG-TEST0 reconciliation

APG8's managed RepoMap adoption remains historically accurate. APG9 adds the
subsequent final external acceptance and completed fresh-session smoke as later
dispositions rather than rewriting the APG8 exit.

APG-TEST0 remains post-release development work. Its source layout owns two
Bats report-tool suites covering 22 behavior families and one Python
project-skill integration suite covering 28 families. Both suites passed before
APG9 edits. Their results strengthen the development foundation but do not
retroactively prove that public v0.1.0 shipped its omitted wrapper or tests.

## Six-skill evidence and maturity

All six skills retain valid structural, positive, non-trigger, edge or stop,
independent-review, rollback, and accumulated real-use evidence. No APG9 worker
found a current material authority, privacy, safety, or procedure defect.

- assignment composition has repeated bounded reviewer-assignment use;
- design has APG and RepoMap positive and accepted-design non-trigger evidence;
- planning has repeated APG and RepoMap use plus a resolved overlap correction;
- implementation discipline has baseline-red, full-suite-green, refactor, and
  correction evidence in APG;
- debugging has competing-hypothesis, reproduction, localization, correction,
  and regression evidence; and
- review has repeated APG and RepoMap artifact, code, finished-diff, and target-
  state use plus the post-decommission smoke.

All six remain `provisional`. ADR 0006 refines the v0.2 stability policy:
repeated positive use and representative non-triggers are separate requirements;
cross-repository breadth and clean comparison remain useful evidence but are
not independent blockers. APG13 must review each skill separately and may block
one only for an unresolved material defect under a recorded correction condition.

## Experimental Karpathy source

The tracked Karpathy Guidelines source remains experimental reference evidence.
Its four broad themes overlap heavily with existing APG owners. The source
frontmatter declares MIT, but APG has not yet verified complete upstream
identity, immutable version, copyright, full license text, or notice duties.
APG9 copies or adapts none of its expression.

The bounded comparison identified only three possible APG10 gaps: proportional
handling of consequential assumptions and simpler alternatives, traceability of
changed surfaces to the accepted objective and required evidence, and cleanup
made necessary by the current change. These are candidates for independent
APG-native synthesis and scenario testing, not accepted changes. Absolute or
universal rules for ambiguity, planning, tests, style, abstractions, code size,
and incidental reporting conflict with APG proportionality or remain project-
owned. No seventh skill is preauthorized.

## Legacy-roadmap disposition

Every former unnumbered theme now has an owner or terminal condition. APG11
owns the durable closure ledger; APG9 records preliminary assignments:

- APG11: evaluate and formalize the repeated skill-authoring and maintenance
  lifecycle and bounded mechanical checks;
- APG12: public global distribution and validated projection/release mechanics;
- APG13: individual post-Superpowers stability review;
- APG14: verified public v0.2.0 projection and release closeout;
- existing skills and ADRs satisfy the core procedure, project-local
  projection, licensing, contribution, release-existence, rollback, and source-
  preservation themes;
- generic delivery, universal test policy, release cadence, autonomous worker
  infrastructure, and wholesale source migration are rejected as unnecessary
  or project-owned; and
- prompt scoring, profiles, other harnesses, hosted services, telemetry, and
  clean comparison are deferred under explicit evidence and authority conditions.

No legacy theme remains without a preliminary terminal owner. Assignment to a
future phase is not completed implementation.

## Accepted v0.2 sequence

ADR 0006 accepts:

1. **APG10:** experimental-source evaluation and selective integration;
2. **APG11:** skill authoring, maintenance, and legacy-roadmap closure;
3. **APG12:** public distribution and release validation;
4. **APG13:** six-skill post-Superpowers stability review; and
5. **APG14:** v0.2.0 release candidate and publication.

APG10 owns source-derived deltas. APG13 may correct only a residual material
defect discovered during maturity review. Each phase requires a separate human
assignment; this roadmap is not automatic execution authority.

## Evidence boundaries and limitations

Public documentation uses canonical identities and generalized operation
categories. Exact repositories, commits, local paths, link targets, hashes,
plugin observations, worker findings, and report identities remain
publication-excluded. Public files do not link to exact private evidence.

APG9 does not repair public v0.1.0, repeat the original application restart,
test Superpowers restoration, prove automatic invocation, perform clean A/B
comparison, edit a skill, change maturity, add a dependency, publish v0.2, or
begin APG10.

## Next phase

APG10 is the next decision. It does not begin automatically and requires a
separate human assignment.
