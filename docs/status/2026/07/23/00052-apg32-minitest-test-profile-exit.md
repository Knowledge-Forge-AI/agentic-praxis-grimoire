# APG32 Minitest Test Profile Exit

Phase ID: `APG32`

Status date: 2026-07-23

Disposition: Complete — Minitest test profile implemented provisionally

## Scope and outcome

APG32 evaluates and retains one direct-child
`minitest-test-profile`. The profile owns materially Minitest-specific test and
spec organization, assertions and refutations, lifecycle, mocks and stubs,
fixture alternatives, isolation, parallelism, filtering, runner, plugin,
reporter, boundary effects, and structural warning signals. It does not select
the framework, dependencies, versions, project commands, worker counts,
coverage thresholds, CI policy, fixture architecture, or external authority.

Current primary-source calibration covers Minitest 6.0.6,
`minitest-mock` 5.27.0, and Ruby 4.0.6. Minitest and `minitest-mock` are
MIT-licensed. Ruby is available under the Ruby License or two-clause BSD,
subject to file-specific terms. These versions are calibration evidence, not
project requirements or a universal compatibility matrix. The retained
procedure is independently written synthesis.

Thirty-six frozen scenario families retain their expected outcomes. One
behavior-bearing correction makes fixture alternatives and Minitest-specific
effects around subprocess, filesystem, and database tests explicit while
preserving general real-boundary truthfulness, Ruby subprocess semantics, and
repository isolation with their existing owners. The correction changes no
frozen outcome.

## Resulting shape

- Development contains 23 canonical skills, 23 catalog rows, and 23 flat
  projections.
- Maturity is fourteen stable and nine provisional rows.
- The general router has twenty-one entries, the ChatGPT-local router has one
  entry, and the checked total is twenty-two route edges.
- The public executable scenario fixture, focused mirrored contract, strict
  inventory, current-development release policy, and release-validator surface
  are integrated without a public dependency on publication-excluded evidence.
- Public and active v0.3.0 remain unchanged at 19/19/19.
- No dependency, framework, command, coverage target, readiness action,
  release, publication, active integration, or successor phase is selected.
- No ADR 0025 is needed because existing lifecycle and ownership decisions
  cover the retained provisional leaf.

## Structural and semantic disposition

The profile defines Minitest-specific Green, Yellow, Orange, and Red fallback
signals for physical lines, tests or examples, effective lifecycle hooks,
mixed-in helpers, mock or stub boundaries, shared mutable domains,
parallel-worker writable domains, custom inheritance, responsibilities, and
generated cases. Publication-excluded evidence explains each threshold and
both coupling rules.

Semantic Red stops include false-passing required assertions, uncontrolled
order or seed dependence, parallel collision or thread-unsafe shared state,
false integration claims, failed restoration, protected-data leakage,
unsupported version or plugin claims, silent omission or empty required
collection, unauthorized destructive external mutation, and crisis-level
undecomposed ownership without an accepted exception.

## Validation and review

| Gate | Result |
| --- | --- |
| Frozen scenarios and focused mirrored contract | Passed: 36 outcomes retained; 5 focused tests |
| Affected pytest selection | Passed: 135 unit tests plus the affected skill-library and public-release integration selection, with one expected skip |
| Development checker | Passed in text and JSON at 23/23/23 |
| Public v0.3 checker | Passed in text and JSON at 19/19/19 |
| Source/mirror inventory | Passed: 18 maintained Python sources and 37 mirrored tests |
| Python compilation | Passed |
| Record identity | Passed before allocation at 24 ADRs and 51 exits; APG32 allocates exit 00052 and no ADR |
| Disposable current-development candidate/check | Passed for a local v0.4.0 candidate without publication |
| Markdown, links, privacy, durable identity, and whitespace | Passed |
| Fresh non-author review | Passed for semantics/source, ownership/overlap, mocks/isolation/parallelism/truthfulness, structural thresholds/stops, integration, provenance/rights, and complete diff |
| Formal commit-message checker | Required before and after the APG32 commit |
| Managed reports | One postcommit Git-show record and one explicitly associated operational record required |
| APG remote equality | Required after the normal push |

Combined, full, readiness, smoke, release, publication, source-repository, and
target-repository suites are intentionally not run. The focused selection and
disposable candidate express the affected APG32 boundaries without expanding
into an unauthorized gate.

## Rollback and next boundary

Rollback removes the leaf, flat projection, catalog and general-map entries,
current-development release-policy and validator entries, strict inventory
row, focused test, current-surface test expectation, and public scenario
fixture together while preserving the evaluation and exit history. No private
guidance was migrated.

No phase after APG32 is authorized. Dockerfile, Vagrantfile, Go-test, nix-test,
readiness, compatibility remediation, active-integration change, and v0.4.0
release work require separate maintainer authority.
