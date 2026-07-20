# Exit Records

Exit records preserve the truthful terminal disposition of a bounded APG phase.
They summarize scope, outcome, validation, deferrals, and the next authorization.
They are project history, not substitutes for Git or operational report
artifacts.

## Path and sequence

Use:

```text
docs/status/YYYY/MM/DD/NNNNN-<phase>-<slug>-exit.md
```

- `YYYY/MM/DD` is the local calendar date encoded in the committer timestamp of
  the commit that first introduced the logical exit record.
- Preserve the date in that timestamp's numeric offset. Do not convert the
  timestamp to UTC or to the reviewing machine's timezone.
- Later moves or corrections do not change the assigned introduction date.
- `NNNNN` is a five-digit sequence that advances across the complete exit-record
  tree. The first value is `00001`.
- Select the next value by finding the greatest assigned exit number and adding
  one.
- An assigned exit number and date are stable and are never reused or changed,
  including when a phase is partial, blocked, rejected, stopped, or its record
  later moves explicitly.
- Each exit number must be unique within the exit-record namespace.
- Exit numbering is independent of the ADR namespace under `docs/adr/`.

## Record contract

- The filename ends in `-exit.md`.
- The document title contains `Exit`.
- The disposition is truthful; an incomplete phase may still close with a
  partial, blocked, rejected, or stopped exit.
- The record states phase identity, scope, outcome, validation actually run,
  deferred work, and the next authorized decision or action.
- Publishable exit records do not expose unpublished repository identities,
  private source topology, private commit identities, local paths, or private
  report destinations.

## Index

- [`00001 — APG0 Foundation Exit`](2026/07/18/00001-apg0-foundation-exit.md)
- [`00002 — APG1 Public Projection and Documentation Hygiene Exit`](2026/07/18/00002-apg1-public-projection-and-document-hygiene-exit.md)
- [`00003 — APG2 Roadmap Reconciliation Proposal Exit`](2026/07/18/00003-apg2-roadmap-reconciliation-proposal-exit.md)
- [`00004 — APG2A First Implementation Sequence Acceptance Exit`](2026/07/18/00004-apg2a-first-implementation-sequence-acceptance-exit.md)
- [`00005 — APG3 Bounded Worker-Assignment Skill Evaluation Exit`](2026/07/18/00005-apg3-bounded-worker-assignment-skill-evaluation-exit.md)
- [`00006 — APG4 Bootstrap v0.1 Exit`](2026/07/18/00006-apg4-bootstrap-v0-1-exit.md)
- [`00007 — APG4A Codex Repository Skill Discovery Exit`](2026/07/18/00007-apg4a-codex-repository-skill-discovery-exit.md)
- [`00008 — APG5 First Codex Dogfooding and Commit-Message Hygiene Exit`](2026/07/18/00008-apg5-first-codex-dogfooding-and-commit-message-hygiene-exit.md)
- [`00009 — APG6 RepoMap Cross-Repository Dogfooding Exit`](2026/07/19/00009-apg6-repomap-cross-repository-dogfooding-exit.md)
- [`00010 — APG7 Project-Local Skill Projection and Rollback Tooling Exit`](2026/07/19/00010-apg7-project-local-skill-projection-and-rollback-tooling-exit.md)
- [`00011 — APG7A Idempotent Projection Compliance Correction Exit`](2026/07/19/00011-apg7a-idempotent-projection-compliance-correction-exit.md)
- [`00012 — APG8 RepoMap Managed Projection Adoption Exit`](2026/07/19/00012-apg8-repomap-managed-projection-adoption-exit.md)
- [`00013 — APG-TEST0 Repository Test Layout and Report-Tool Coverage Exit`](2026/07/19/00013-apg-test0-repository-test-layout-and-report-tool-coverage-exit.md)
- [`00014 — APG9 v0.1 Release, Decommission, and v0.2 Roadmap Exit`](2026/07/19/00014-apg9-v0-1-release-decommission-and-v0-2-roadmap-exit.md)
- [`00015 — APG10 Karpathy Guidelines Evaluation and Selective Integration Exit`](2026/07/19/00015-apg10-karpathy-guidelines-evaluation-and-selective-integration-exit.md)
- [`00016 — APG11 Skill Authoring, Maintenance, and Legacy Roadmap Closure Exit`](2026/07/20/00016-apg11-skill-authoring-maintenance-and-legacy-roadmap-closure-exit.md)
- [`00017 — APG11A Skill-Library Lexical Correction Exit`](2026/07/20/00017-apg11a-skill-library-lexical-correction-exit.md)
- [`00018 — APG12 Public Distribution and Release Validation Exit`](2026/07/20/00018-apg12-public-distribution-and-release-validation-exit.md)
- [`00019 — APG12A Public Lineage and Read-Only Validation Correction Exit`](2026/07/20/00019-apg12a-public-lineage-and-read-only-validation-correction-exit.md)
- [`00020 — APG13 Six-Skill Post-Superpowers Stability Review Exit`](2026/07/20/00020-apg13-six-skill-post-superpowers-stability-review-exit.md)
- [`00021 — APG14 v0.2.0 Release Candidate and Publication Exit`](2026/07/20/00021-apg14-v0-2-release-candidate-and-publication-exit.md)
