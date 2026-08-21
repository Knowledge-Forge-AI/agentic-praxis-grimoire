# Exit Records

<!-- APG-CANDIDATE-STATE: css-language-profile retained-provisional -->

The marker above is the mechanical current-state authority. Bounded
contradiction diagnostics cover only their frozen vocabulary; arbitrary prose
still requires human review.

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
- [`00040 — APG24A v0.3 External Smoke and Router Transition Closeout Exit`](2026/07/22/00040-apg24a-v0-3-external-smoke-and-router-transition-closeout-exit.md)
- [`00041 — APG25 v0.4 Structured Project Work Foundation Exit`](2026/07/22/00041-apg25-v0-4-structured-project-work-foundation-exit.md)
- [`00042 — APG26 Pytest and Bash-to-Python Capabilities Exit`](2026/07/22/00042-apg26-pytest-and-bash-to-python-capabilities-exit.md)
- [`00043 — APG26A Formal-Phase Commit-Message Enforcement Exit`](2026/07/22/00043-apg26a-formal-phase-commit-message-enforcement-exit.md)
- [`00044 — APG27 Python Agent Reporting and Git-Diff Report Exit`](2026/07/22/00044-apg27-python-agent-reporting-and-git-diff-report-exit.md)
- [`00045 — APG27A Python Agent Reporting Correction and Adoption Exit`](2026/07/22/00045-apg27a-python-agent-reporting-correction-and-adoption-exit.md)
- [`00046 — APG28 Pytest Suite and Coverage Migration Exit`](2026/07/22/00046-apg28-pytest-suite-and-coverage-migration-exit.md)
- [`00047 — APG28A Pytest Migration Correction and Adoption Exit`](2026/07/22/00047-apg28a-pytest-migration-correction-and-adoption-exit.md)
- [`00048 — APG29 Process-Skill Alignment Exit`](2026/07/22/00048-apg29-process-skill-alignment-exit.md)
- [`00049 — APG30 ChatGPT-Manager Topology and Subrouter Exit`](2026/07/23/00049-apg30-chatgpt-manager-topology-and-subrouter-exit.md)
- [`00050 — APG31 Personal-Hygiene Shadow and Transition Exit`](2026/07/23/00050-apg31-personal-hygiene-shadow-and-transition-exit.md)
- [`00051 — APG31A Personal-Hygiene Transition Completion Exit`](2026/07/23/00051-apg31a-personal-hygiene-transition-completion-exit.md)
- [`00052 — APG32 Minitest Test Profile Exit`](2026/07/23/00052-apg32-minitest-test-profile-exit.md)
- [`00053 — APG33 Dockerfile Profile Exit`](2026/07/24/00053-apg33-dockerfile-profile-exit.md)
- [`00054 — APG34 Vagrantfile Profile Exit`](2026/07/24/00054-apg34-vagrantfile-profile-exit.md)
- [`00055 — APG35 v0.4 Remaining-Skill Authoring Exit`](2026/07/25/00055-apg35-v0-4-remaining-skill-authoring-exit.md)
- [`00056 — APG36 Claude-Authored Skill Integration Exit`](2026/07/25/00056-apg36-claude-authored-skill-integration-exit.md)
- [`00057 — APG37 Go and Nix Test Profile Redesign Exit`](2026/07/25/00057-apg37-go-and-nix-test-profile-redesign-exit.md)
- [`00058 — APG38 APG37 Go and Nix Integration Exit`](2026/07/25/00058-apg38-apg37-go-and-nix-integration-exit.md)
- [`00059 — APG39 matryer/is and Nix Final Redesign Exit`](2026/07/26/00059-apg39-matryer-is-and-nix-final-redesign-exit.md)
- [`00060 — APG40 APG39 matryer/is and Nix Integration Exit`](2026/07/26/00060-apg40-apg39-matryer-nix-integration-exit.md)
- [`00061 — APG41 v0.4 Readiness and Pre-Release Smoke Exit`](2026/07/26/00061-apg41-v0-4-readiness-and-pre-release-smoke-exit.md)
- [`00062 — APG42 v0.4 Release Publication and Active Deployment Exit`](2026/07/26/00062-apg42-v0-4-release-publication-and-active-deployment-exit.md)
- [`00063 — APG43 v0.4 NOTICE Brand Correction Exit`](2026/07/26/00063-apg43-v0-4-notice-brand-correction-exit.md)
- [`00064 — APG44 Fact-Check Skill Comparative Analysis Exit`](2026/07/26/00064-apg44-fact-check-skill-comparative-analysis-exit.md)
- [`00065 — APG45 Fact-Check Peer Review and Roadmap Disposition Exit`](2026/07/26/00065-apg45-fact-check-peer-review-and-roadmap-disposition-exit.md)
- [`00066 — APG46 Accepted Evidence Guidance Authoring Exit`](2026/07/26/00066-apg46-accepted-evidence-guidance-authoring-exit.md)
- [`00067 — APG47 Accepted Evidence Guidance Integration Exit`](2026/07/26/00067-apg47-accepted-evidence-guidance-integration-exit.md)
- [`00068 — APG48 Go Test-Harness Dogfood and Candidate Authoring Exit`](2026/07/27/00068-apg48-go-test-harness-dogfood-and-candidate-authoring-exit.md)
- [`00069 — APG49 matryer/is Validation and Integration Exit`](2026/07/27/00069-apg49-matryer-is-validation-and-integration-exit.md)
- [`00070 — APG50 Web and Node Profile-Family Architecture Exit`](2026/07/27/00070-apg50-web-and-node-profile-family-architecture-exit.md)
- [`00071 — APG51 Web and Node Architecture Peer Review Exit`](2026/07/28/00071-apg51-web-and-node-architecture-peer-review-exit.md)
- [`00072 — APG52 Reproducible Web and Node Evidence Foundation Exit`](2026/07/28/00072-apg52-reproducible-web-node-evidence-foundation-exit.md)
- [`00073 — APG53 Operational Tooling and Report Hygiene Exit`](2026/07/28/00073-apg53-operational-tooling-and-report-hygiene-exit.md)
- [`00074 — APG54 Global Skill Installer Integration Exit`](2026/07/28/00074-apg54-global-skill-installer-integration-exit.md)
- [`00075 — APG55 Global Skill Installer Transaction Hardening Exit`](2026/07/29/00075-apg55-global-skill-installer-transaction-hardening-exit.md)
- [`00076 — APG56 Web and Node Architecture Reconstruction Exit`](2026/07/29/00076-apg56-web-and-node-architecture-reconstruction-exit.md)
- [`00077 — APG57 Web and Node Architecture Review Exit`](2026/07/29/00077-apg57-web-and-node-architecture-review-exit.md)
- [`00078 — APG58 CSS Language-Profile Pilot Authoring Exit`](2026/07/29/00078-apg58-css-language-profile-pilot-authoring-exit.md)
- [`00079 — APG59 CSS Language-Profile Validation and Integration Exit`](2026/07/29/00079-apg59-css-language-profile-validation-and-integration-exit.md)
- [`00080 — APG60 CSS Re-entry Contract and Removal-Closure Foundation Exit`](2026/07/29/00080-apg60-css-reentry-contract-and-removal-foundation-exit.md)
- [`00081 — APG60A CSS Contract Foundation Hardening Exit`](2026/07/29/00081-apg60a-css-contract-foundation-hardening-exit.md)
- [`00082 — APG60B CSS Traceability and Decision Closure Exit`](2026/07/30/00082-apg60b-css-traceability-and-decision-closure-exit.md)
- [`00083 — APG60C CSS Runtime and Terminal Lifecycle Closure Exit`](2026/07/30/00083-apg60c-css-runtime-and-terminal-lifecycle-closure-exit.md)
- [`00084 — APG60D CSS Source-Binding and Phase-History Closure Exit`](2026/07/30/00084-apg60d-css-source-binding-and-history-closure-exit.md)
- [`00085 — APG60E CSS Repository Path and Candidate-Surface Closure Exit`](2026/07/30/00085-apg60e-css-repository-path-and-candidate-surface-closure-exit.md)
- [`00086 — APG60F CSS Import, Owner, and Projection Closure Exit`](2026/07/30/00086-apg60f-css-import-owner-and-projection-closure-exit.md)
- [`00087 — APG60G CSS Snapshot, Role, and Derived-Set Closure Exit`](2026/07/30/00087-apg60g-css-snapshot-role-and-derived-set-closure-exit.md)
- [`00088 — APG60H CSS Snapshot and Full-Path Binding Closure Exit`](2026/07/31/00088-apg60h-css-snapshot-and-full-path-binding-closure-exit.md)
- [`00089 — APG60I Worker Temporary-Root Binding and Cleanup Closure Exit`](2026/07/31/00089-apg60i-worker-temp-binding-and-cleanup-closure-exit.md)
- [`00090 — APG61 CSS Language-Profile Authoring from Frozen Contract Exit`](2026/07/31/00090-apg61-css-language-profile-authoring-exit.md)
- [`00091 — APG62 CSS Language-Profile Validation and Integration Exit`](2026/07/31/00091-apg62-css-language-profile-validation-and-integration-exit.md)
- [`00092 — APG63 Markdown Language-Profile Architecture Exit`](2026/07/31/00092-apg63-markdown-language-profile-architecture-exit.md)
- [`00093 — APG64 Markdown Architecture Peer Review Exit`](2026/07/31/00093-apg64-markdown-architecture-peer-review-exit.md)
- [`00094 — APG65 Markdown Language-Profile Authoring Exit`](2026/07/31/00094-apg65-markdown-language-profile-authoring-exit.md)
- [`00095 — APG66 Markdown Language-Profile Validation and Integration Exit`](2026/08/01/00095-apg66-markdown-language-profile-validation-and-integration-exit.md)
- [`00096 — APG66A Markdown Replay-Evidence Truth Exit`](2026/08/01/00096-apg66a-markdown-replay-evidence-truth-exit.md)
- [`00097 — APG66B Markdown Register Vocabulary and Guard Exactness Exit`](2026/08/01/00097-apg66b-markdown-register-vocabulary-and-guard-exactness-exit.md)
- [`00098 — APG66C Markdown Clause-Polarity and Predicate-Binding Exit`](2026/08/01/00098-apg66c-markdown-clause-polarity-and-predicate-binding-exit.md)
- [`00099 — APG66D Repository-Import Cache Entry-Presence Exit`](2026/08/01/00099-apg66d-repository-import-cache-entry-presence-exit.md)
- [`00100 — APG67 JavaScript Language-Profile Architecture Exit`](2026/08/02/00100-apg67-javascript-language-profile-architecture-exit.md)
- [`00101 — APG68 JavaScript Architecture Peer Review Exit`](2026/08/02/00101-apg68-javascript-architecture-peer-review-exit.md)
- [`00102 — APG69 JavaScript Core Layered-Architecture Exit`](2026/08/02/00102-apg69-javascript-core-layered-architecture-exit.md)
- [`00103 — APG70 JavaScript Core Layered-Architecture Peer Review Exit`](2026/08/02/00103-apg70-javascript-core-layered-architecture-peer-review-exit.md)
- [`00104 — APG71 TypeScript Language-Profile Architecture Exit`](2026/08/02/00104-apg71-typescript-language-profile-architecture-exit.md)
- [`00105 — APG72 TypeScript Architecture Peer Review Exit`](2026/08/02/00105-apg72-typescript-architecture-peer-review-exit.md)
- [`00106 — APG73 Language-Profile Production Recovery Charter Exit`](2026/08/03/00106-apg73-language-profile-production-recovery-charter-exit.md)
- [`00107 — APG74 TypeScript Language-Profile Candidate Exit`](2026/08/03/00107-apg74-typescript-language-profile-candidate-exit.md)
- [`00108 — APG75 TypeScript Iterative Hardening and Integration Exit`](2026/08/03/00108-apg75-typescript-iterative-hardening-and-integration-exit.md)
- [`00109 — APG75A TypeScript Scope and Lifecycle Closure Exit`](2026/08/03/00109-apg75a-typescript-scope-and-lifecycle-closure-exit.md)
- [`00110 — APG76 CSS Language-Profile Candidate Recovery Exit`](2026/08/04/00110-apg76-css-language-profile-candidate-recovery-exit.md)
- [`00111 — APG77 CSS Iterative Hardening and Integration Exit`](2026/08/04/00111-apg77-css-iterative-hardening-and-integration-exit.md)
- [`00112 — APG77A CSS Evidence-Retention Closure and Integration Exit`](2026/08/06/00112-apg77a-css-evidence-retention-closure-and-integration-exit.md)
- [`00113 — APG77B CSS Traceability, Clean-Room Closure, and Integration Exit`](2026/08/06/00113-apg77b-css-traceability-clean-room-closure-and-integration-exit.md)
- [`00114 — APG77C CSS Evidence Proportionality and Integration Exit`](2026/08/07/00114-apg77c-css-evidence-proportionality-and-integration-exit.md)
- [`00115 — APG77D CSS Known Debt and Provisional Integration Exit`](2026/08/08/00115-apg77d-css-known-debt-and-provisional-integration-exit.md)
- [`00116 — APG78 JavaScript Core Candidate Exit`](2026/08/08/00116-apg78-javascript-core-candidate-exit.md)
- [`00117 — APG79 JavaScript Core Iterative Hardening Repair Checkpoint Exit`](2026/08/08/00117-apg79-javascript-core-iterative-hardening-and-integration-exit.md)
- [`00118 — APG79A JavaScript Terminal-Proof Closure and Integration Exit`](2026/08/08/00118-apg79a-javascript-terminal-proof-closure-and-integration-exit.md)
- [`00119 — APG79B JavaScript Contract/Harness Closure and Integration Exit`](2026/08/08/00119-apg79b-javascript-contract-harness-closure-and-integration-exit.md)
- [`00120 — APG79C JavaScript Known Debt and Provisional Integration Exit`](2026/08/08/00120-apg79c-javascript-known-debt-and-provisional-integration-exit.md)
- [`00121 — APG79D Test262 Source Evidence and JavaScript Integration Exit`](2026/08/08/00121-apg79d-test262-source-evidence-and-javascript-integration-exit.md)
- [`00122 — APG79E JavaScript Report-Binding Debt and Provisional Integration Exit`](2026/08/09/00122-apg79e-javascript-report-binding-debt-and-provisional-integration-exit.md)
- [`00123 — APG80 Node.js Runtime and CLI-Stack Candidate Exit`](2026/08/09/00123-apg80-nodejs-runtime-and-cli-stack-candidate-exit.md)
- [`00124 — APG81 Node.js Runtime and CLI Iterative Hardening Repair Checkpoint Exit`](2026/08/10/00124-apg81-nodejs-runtime-cli-iterative-hardening-and-integration-exit.md)
- [`00125 — APG81A Node.js Threat-Model Correction Repair Checkpoint Exit`](2026/08/10/00125-apg81a-nodejs-qualification-threat-model-and-harness-simplification-exit.md)
- [`00126 — APG81B Node.js Integration-Contract Clarification Repair Checkpoint Exit`](2026/08/10/00126-apg81b-nodejs-integration-contract-clarification-and-provisional-adoption-exit.md)
- [`00127 — APG81C Node.js Lifecycle, Test, and Scratch Closure Repair Checkpoint Exit`](2026/08/10/00127-apg81c-nodejs-lifecycle-test-and-scratch-closure-exit.md)
- [`00128 — APG81D Node.js Repo-Local Scratch Integration Repair Checkpoint Exit`](2026/08/10/00128-apg81d-nodejs-provisional-integration-exit.md)
- [`00129 — APG81E Node.js Final Integration Closure Repair Checkpoint Exit`](2026/08/11/00129-apg81e-nodejs-final-integration-closure-exit.md)
- [`00130 — APG81F Node.js Actual-Test-Projection Repair Checkpoint Exit`](2026/08/11/00130-apg81f-nodejs-actual-test-projection-and-integration-closure-exit.md)
- [`00131 — APG81G Node.js Selector, Release, and Integration Closure Exit`](2026/08/11/00131-apg81g-nodejs-selector-release-and-integration-closure-exit.md)
- [`00132 — APG81H Node.js Reviewable Qualification and Integration Closure Exit`](2026/08/11/00132-apg81h-nodejs-reviewable-qualification-and-integration-closure-exit.md)
- [`00133 — APG82 APGR CLI, Distribution, Configuration, and Artifact Foundation Exit`](2026/08/15/00133-apg82-apgr-cli-distribution-configuration-and-artifact-contract-foundation-exit.md)
- [`00134 — APG83 v0.5 Bounded Dogfood and Release Readiness Exit`](2026/08/16/00134-apg83-v0-5-bounded-dogfood-and-release-readiness-exit.md)
- [`00135 — APG84 v0.5 Public GitHub and PyPI Publication Exit`](2026/08/16/00135-apg84-v0-5-public-github-and-pypi-publication-exit.md)
- [`00136 — APG85 v0.6 Architecture, Discoverability, and Context-Budget Exit`](2026/08/18/00136-apg85-v0-6-architecture-discoverability-and-context-budget-exit.md)
- [`00137 — APG86 GoMock and Vitest Profiles and Context-Budget Enforcement Exit`](2026/08/20/00137-apg86-gomock-vitest-profiles-and-context-budget-enforcement-exit.md)
- [`00138 — APG87 JSX and React Profiles with APG88 Headroom Conservation Exit`](2026/08/20/00138-apg87-jsx-react-profiles-and-apg88-headroom-conservation-exit.md)
- [`00139 — APG88 MDX and Astro Profiles Complete the v0.6 Authoring Set Exit`](2026/08/20/00139-apg88-mdx-astro-profiles-and-v0-6-authoring-completion-exit.md)
- [`00140 — APG89 v0.6 Dogfood, Composition, Context, and Readiness Exit`](2026/08/20/00140-apg89-v0-6-dogfood-composition-context-and-readiness-exit.md)
- [`00141 — APG90 v0.6 Publication Preparation and Public Release Handoff Exit`](2026/08/21/00141-apg90-v0-6-publication-preparation-and-public-release-handoff-exit.md)
