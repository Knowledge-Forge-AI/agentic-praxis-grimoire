# ADR 0010: Six-Skill Post-Superpowers Stability Dispositions

## Status

Accepted

## Date

2026-07-20

## Acceptance authority

The human maintainer's APG13 assignment accepts this decision. It authorizes
individual maturity disposition, at most one demonstrated material procedure
correction per skill, current-document reconciliation, one private development
commit and push, and required managed reports. It does not authorize a public
candidate, publication, active integration change, external-repository
mutation, Superpowers restoration, or APG14 work.

## Context

APG12A is accepted as complete: it corrects public lineage and read-only
validation while preserving ADR 0009, version-1 schemas, command surfaces,
skills, projections, maturity, public and reference repositories, RepoMap, and
active integration. Its corrected terminal suites contain 15 checker unit and
58 checker integration tests, 8 release unit and 32 release integration tests,
8 user unit and 39 user integration tests, 22 report-tool Bats families, and 28
project-skill integration families.

ADR 0006 targets all six current skills for individual `stable` disposition.
It makes repeated real use, representative non-triggers, absence of unresolved
material authority/privacy/safety/procedure defects, post-Superpowers review,
and supported rollback mandatory. Clean A/B superiority, automatic invocation,
publication, global installation, and positive use in every second repository
are not independent blockers.

## Decision

### Stable criteria

Each skill is reviewed for:

1. one coherent owner with precise positive and non-trigger boundaries;
2. preservation of human, task, and repository authority;
3. a coherent, proportional, independently removable procedure;
4. repeated real use, non-trigger and edge/stop evidence, and fresh completion
   evidence;
5. safety, privacy, destructive-action, source-trust, and publication
   boundaries;
6. post-Superpowers positive or direct-review evidence without retired-tool
   dependency;
7. correction history, regression status, maintenance, and rollback; and
8. current mechanical regression plus fresh non-author maturity review.

`stable` means suitable for routine bounded use within the recorded trigger and
project boundaries. It does not mean universal applicability, automatic
invocation, comparative superiority, production warranty, or independent
action authority.

### Evidence classes

Positive real use, textual scenario application, non-trigger evidence,
integration evidence, mechanical evidence, distribution evidence, and
historical correction are recorded separately. Projection, installation,
release, discovery, and catalog success do not become positive semantic use.
Non-triggers do not count as positive use.

### Frozen current applications

Before any maturity change, APG13 froze one positive, non-trigger, and edge or
stop family per skill. Fresh read-only workers applied the unchanged leaves:

- assignment composition produced one complete bounded read-only review
  assignment, skipped unnecessary delegation, and stopped on overlapping writes
  or phase expansion;
- significant-change design produced a bounded consequential-decision request,
  preserved accepted-design and reversible-work non-triggers, and stopped on
  reserved authority, public-contract, or destructive uncertainty;
- repository planning produced dependent implementation, documentation, test,
  release-evidence, and handoff units, skipped one local correction, and stopped
  when state or accepted decisions invalidated later units;
- implementation discipline produced proportional behavioral and final-gate
  evidence, skipped documentation/mechanical ceremony, and stopped cleanup at
  generated, migration, external, or lifecycle ownership boundaries;
- systematic debugging produced a hypothesis-driven diagnostic record,
  excluded expected failing-first behavior, and bounded or stopped stale,
  unreproducible, indistinguishable, or unauthorized investigation; and
- review and verification produced a scope-first preliminary disposition,
  excluded casual brainstorming, and withheld acceptance for changed artifacts,
  stale evidence, or missing authority.

All six applications recommended `stable-candidate`. None demonstrated a
material defect.

### Corrections and rollback

No procedure correction was made. Every `SKILL.md` remains byte-identical to
the APG12A baseline, so each APG13 correction count is zero. If a maturity
disposition becomes unsupported, restore that catalog row to `provisional`,
supersede the disposition, reconcile current owners, and rerun affected gates
without erasing historical evidence. Behavior-bearing rollback remains owned by
the skill lifecycle and each skill's recorded correction history.

### Individual dispositions

| Skill | Evidence summary | Final non-author review | Maturity |
| --- | --- | --- | --- |
| `composing-bounded-worker-assignments` | APG4 scenarios; repeated APG6-APG12A bounded assignments; direct-work non-triggers; overlap/authority stops; post-retirement use | `accept-stable` | `stable` |
| `designing-significant-changes` | APG4 scenarios; APG6 RepoMap and APG7/APG11/APG12 design; multiple accepted-design non-triggers; reversible/reserved-choice edge | `accept-stable` | `stable` |
| `planning-repository-work` | APG4 scenarios; APG6-APG12A dependent plans; one-action non-triggers; invalidated-plan stops | `accept-stable` | `stable` |
| `implementing-with-test-discipline` | APG4 scenarios; APG7/APG7A/APG10-APG12A behavioral work; APG8/APG9 and documentation non-triggers; APG10 cleanup correction and ownership stop | `accept-stable` | `stable` |
| `debugging-systematically` | APG4 scenarios; APG7A/APG11-APG12A diagnosis; APG9 and expected-red non-triggers; APG11 no-production-fix and stale/authority stops | `accept-stable` | `stable` |
| `reviewing-and-verifying-repository-work` | APG4 scenarios; APG5-APG12A review; casual-feedback non-trigger; APG6 frontmatter correction; stale/missing-authority stops | `accept-stable` | `stable` |

All six catalog rows become `stable`. `LT21` and `LT24` become
`implemented-by-APG13`.

### Release boundary

APG13 creates no real v0.2.0 candidate and performs no publication or active
integration update. Public v0.1.0 retains its original commit, tree, lightweight
tag identity, historical provisional catalog, and role as the active
public-backed source. APG14 is ready under the v0.2 objective but remains
separately authorized and unstarted.

## Alternatives considered

### Promote all six from accumulated evidence without fresh review

Rejected. Historical strength does not replace frozen current applications,
fresh resulting-state evidence, or non-author disposition.

### Require clean A/B superiority

Rejected as a mandatory gate. It may be useful future evidence but is not a
material defect under ADR 0006.

### Require second-repository positive use for every skill

Rejected as a universal gate. Cross-repository breadth is recorded where
present; repeated positive APG use may satisfy maturity.

### Retain every skill provisional indefinitely

Rejected. It would disregard the accepted criteria and accumulated evidence
without naming a concrete defect.

### Review and disposition each skill separately

Accepted. Evidence distribution, correction history, edge behavior, and
rollback differ by owner.

### Treat distribution success as maturity

Rejected. Distribution proves availability and integrity, not semantic
procedure quality.

### Treat only a concrete material defect as a blocker

Accepted. Stylistic preferences, hypothetical failures, and absent non-required
claims do not consume correction budgets or block promotion.

## Consequences

- The development catalog contains six `stable` rows and no provisional row.
- Current owners identify APG13 as complete and APG14 as next but separately
  authorized.
- Historical provisional statements remain phase-accurate.
- No skill content, projection, command, schema, dependency, plugin, or public
  artifact changes in APG13.
- Future correction, deprecation, removal, and maturity rollback continue to
  follow the skill lifecycle; `stable` is not irreversible.

## Deferred decisions

- the APG14 real v0.2.0 candidate, active candidate verification, publication,
  public tag, public push, and active integration update;
- any clean comparative or automatic-invocation study;
- any new skill, dependency, plugin, harness adapter, registry, daemon,
  telemetry, hosted service, or release cadence; and
- any change to public v0.1.0 or preserved Superpowers evidence.
