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

- `YYYY/MM/DD` is normally the local calendar date encoded in the committer
  timestamp of the commit that first introduced the logical exit record. When
  an explicit phase assignment instead authorizes a document-stated status
  date, the path matches that stated date without later timestamp archaeology.
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
- Compute the next exit only from this namespace; do not compare it with an ADR
  number.

## Record contract

- The filename ends in `-exit.md`.
- The document title contains `Exit`.
- The disposition is truthful; an incomplete phase may still close with a
  partial, blocked, rejected, or stopped exit.
- The record states phase identity, scope, outcome, validation actually run,
  deferred work, and the next authorized decision or action.
- From exit 00029 onward, the path's lowercase phase token, index label, H1,
  and exactly one `Phase ID` field agree. Canonical phase
  spelling is uppercase and globally unique case-insensitively.
- Publishable exit records do not expose unpublished repository identities,
  private source topology, private commit identities, local paths, or private
  report destinations.

The [phase and record identity guide](../phase-and-record-identity.md) owns
phase forms, never-reuse, durable references, precommit finalization, and the
mechanical checker.

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
- [`00022 — APG15 v0.3 Foundation Design Exit`](2026/07/20/00022-apg15-v0-3-foundation-design-exit.md)
- [`00023 — APG16 Public Workflow Router Exit`](2026/07/20/00023-apg16-public-workflow-router-exit.md)
- [`00024 — APG17 Repository-Guidance Synthesis Exit`](2026/07/20/00024-apg17-repository-guidance-synthesis-exit.md)
- [`00025 — APG17A Public Release Identity Evidence Correction Exit`](2026/07/21/00025-apg17a-public-release-identity-evidence-correction-exit.md)
- [`00026 — APG18 Language-Profile Contract and Python Vertical Slice Exit`](2026/07/21/00026-apg18-language-profile-contract-and-python-vertical-slice-exit.md)
- [`00027 — APG18A Python-Profile Current-State Documentation Correction Exit`](2026/07/21/00027-apg18a-python-profile-current-state-documentation-correction-exit.md)
- [`00028 — APG19 Shell and Shell-Test Profiles Exit`](2026/07/21/00028-apg19-shell-and-shell-test-profiles-exit.md)
- [`00029 — APG19A Semantic Phase Identity and APG19 Reconciliation Exit`](2026/07/21/00029-apg19a-semantic-phase-identity-and-apg19-reconciliation-exit.md)
- [`00030 — APG20 Go and Ruby Language Profiles Exit`](2026/07/21/00030-apg20-go-and-ruby-language-profiles-exit.md)
- [`00031 — APG20A Go and Ruby Profile Corrections Exit`](2026/07/21/00031-apg20a-go-and-ruby-profile-corrections-exit.md)
- [`00032 — APG21 Nix, PostgreSQL, and SQLite Profiles Exit`](2026/07/21/00032-apg21-nix-postgresql-and-sqlite-profiles-exit.md)
- [`00033 — APG21A Nix Profile Correction Exit`](2026/07/21/00033-apg21a-nix-profile-correction-exit.md)
- [`00034 — APG22 Cross-Repository Dogfood and Guidance Migration Exit`](2026/07/21/00034-apg22-cross-repository-dogfood-and-guidance-migration-exit.md)
- [`00035 — APG22A Approved-Roadmap Manager Assignments Exit`](2026/07/21/00035-apg22a-approved-roadmap-manager-assignments-exit.md)
- [`00036 — APG22B Version-Bounded ZUnit Profile Exit`](2026/07/21/00036-apg22b-version-bounded-zunit-profile-exit.md)
- [`00037 — APG22C ZUnit Startup-Isolation Evidence Correction Exit`](2026/07/21/00037-apg22c-zunit-startup-isolation-evidence-correction-exit.md)
- [`00038 — APG23 v0.3 Readiness, Maturity, and Application Smoke Exit`](2026/07/21/00038-apg23-v0-3-readiness-maturity-and-application-smoke-exit.md)
- [`00039 — APG24 v0.3.0 Release Candidate and Publication Exit`](2026/07/22/00039-apg24-v0-3-release-candidate-and-publication-exit.md)
