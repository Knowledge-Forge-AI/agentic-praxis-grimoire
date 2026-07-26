# APG33 Dockerfile Profile Exit

Phase ID: `APG33`

Status date: 2026-07-24

Disposition: Complete — Dockerfile profile implemented provisionally

## Scope and outcome

APG33 evaluates and retains one direct-child `dockerfile-profile`. The profile
owns materially Dockerfile-specific parser-directive, stage, instruction-form,
variable-scope, context, ignore, transfer, mount, cache, ownership,
runtime-default, platform, and structural judgment. It does not select Docker,
images, registries, tags, digests, frontends, builders, platforms, dependencies,
shells, project commands, runtime policy, release policy, or external authority.

Current primary-source calibration covers stable Dockerfile frontend 1.25.0,
BuildKit 0.31.2, Docker documentation, and OCI Image Spec 1.1.1. Those sources
are Apache-2.0. These versions are calibration evidence, not project
requirements or a universal compatibility matrix. The retained procedure is
independently written synthesis.

Forty frozen scenario families retain their expected outcomes. One
behavior-bearing correction fixes local-context and builder-input wording,
shell-selection ownership, cohesive responsibility counting, and per-stage
root-execution aggregation. Concrete adverse and boundary cases mirror the
correction. No frozen outcome or numeric band changes.

## Resulting shape

- Development contains 24 canonical skills, 24 catalog rows, and 24 flat
  projections.
- Maturity is fourteen stable and ten provisional rows.
- The general router has twenty-two entries, the ChatGPT-local router has one
  entry, and the checked total is twenty-three route edges.
- The public executable scenario fixture, focused mirrored contract, strict
  inventory, current-development release policy, and release-validator surface
  are integrated without a public dependency on publication-excluded evidence.
- Public and active v0.3.0 remain unchanged at 19/19/19.
- No dependency, image, builder, platform, project command, runtime policy,
  readiness action, Docker operation, release, publication, or active
  integration is selected.
- No ADR 0025 is needed because existing lifecycle and ownership decisions
  cover the retained provisional leaf.

## Structural and semantic disposition

The profile defines Dockerfile-specific Green, Yellow, Orange, and Red fallback
signals for physical lines, logical instructions, stages, commands in one
shell-form `RUN`, argument and environment breadth, transfer sources, mounts,
root-execution span, platform conditions, and responsibilities.
Publication-excluded evidence explains each threshold, measurement rule,
coupling rule, generated/vendor treatment, bounded exception, and rollback.

Semantic Red stops include unsupported frontend, builder, platform, or feature
claims; consequential mutable or remote input without project authority and
verification; untrusted source-to-shell flow; protected-data ingress or output;
wrong stage, source, context, copy, user, ownership, or artifact behavior;
unsafe final-user or runtime-default behavior; false build, image, runtime, or
artifact proof; unauthorized external mutation; and crisis-level undecomposed
ownership without an accepted exception.

## Validation and review

| Gate | Result |
| --- | --- |
| Frozen scenarios and focused mirrored contract | Passed: 40 outcomes retained; 5 focused tests |
| Affected pytest selection | Passed: 129 candidate/policy unit tests; 71 project-projection/router tests; 109 release/skill-library integration tests plus 1 expected skip |
| Development checker | Passed in text and JSON at 24/24/24 |
| Public v0.3 checker | Passed in text and JSON at 19/19/19 |
| Source/mirror inventory | Passed: 18 maintained Python sources and 38 mirrored tests, split 22 unit and 16 integration |
| Python compilation | Passed |
| Record identity | Passed before allocation at 24 ADRs and 52 exits; APG33 allocates exit 00053 and no ADR |
| Disposable current-development candidate/check | Passed for a local v0.4.0 candidate without publication using the declared pinned test environment |
| Markdown, links, privacy, durable identity, and whitespace | Passed |
| Fresh non-author review | Passed after one correction for source/rights, ownership/overlap, context/shell/secrets/cache/stage/runtime safety, structural thresholds, integration, provenance/rollback, and complete diff |
| Formal commit-message checker | Required before and after the APG33 commit |
| Managed reports | One postcommit Git-show record and one explicitly associated operational record required |
| APG remote equality | Required after the normal push |

Combined, full, readiness, smoke, release, publication, source-repository,
target-repository, Docker parser, Docker build, daemon, image, container, and
registry suites are intentionally not run. The focused selection and
disposable APG release candidate express the affected APG33 boundaries without
claiming Docker execution evidence.

## Rollback and next boundary

Rollback removes the leaf, flat projection, catalog and general-map entries,
current-development release-policy and validator entries, strict inventory
row, focused test, current-surface test expectation, and public scenario
fixture together while preserving the evaluation and exit history. No private
guidance was migrated. The project-scoped projection owner and its fixtures
remove only Dockerfile, retain the APG32 Minitest repair, and expect 23 current
leaves. The general router returns to 21 entries while the ChatGPT-local route
remains one. A raw APG33 commit revert is not valid rollback because it would
restore stale 22-leaf and 20-route expectations.

APG34 may begin only after the APG33 formal commit and postcommit validation,
Git-show and associated operational reports, normal push, remote equality, and
terminal no-material-finding review all pass. APG34 owns only the bounded
Vagrantfile profile lifecycle supplied by the maintainer. No phase after APG34
is authorized.
