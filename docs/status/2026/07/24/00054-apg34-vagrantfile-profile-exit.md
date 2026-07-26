# APG34 Vagrantfile Profile Exit

Phase ID: `APG34`

Status date: 2026-07-24

Disposition: Complete — Vagrantfile profile implemented provisionally

## Scope and outcome

APG34 evaluates and retains one direct-child `vagrantfile-profile`. The profile
owns materially Vagrantfile-specific configuration-version, load-order,
machine, box, provider, plugin, network, synced-folder, provisioner, trigger,
state, host-dependent, and structural judgment. It does not select Vagrant, a
provider, box, plugin, host platform, network, folder, provisioner, project
command, lifecycle action, release policy, or external authority.

Current primary-source calibration covers Vagrant 2.4.9, current Vagrant
development source and documentation, Vagrant's declared Ruby `>= 3.0` and
`< 3.5` boundary, and current Ruby 4.0.6 language and licensing sources.
Vagrant and the inspected official-documentation source are available under
Business Source License 1.1 with MPL 2.0 as the change license. Ruby is
available under the Ruby License or two-clause BSD terms, subject to
file-specific legal notices. These sources are calibration evidence, not
project requirements or a universal compatibility matrix. The retained
procedure is independently written synthesis.

Forty frozen scenario families retain their expected outcomes. One
behavior-bearing source-semantics and machine-measurement correction makes the
implicit default machine mutually exclusive with named machines and qualifies
the forwarded-port host-binding default as applicable to most providers. No
frozen outcome or numeric band changes. Four earlier capitalization-only test
assertions changed no candidate behavior or frozen outcome.

## Resulting shape

- Development contains 25 canonical skills, 25 catalog rows, and 25 flat
  projections.
- Maturity is fourteen stable and eleven provisional rows.
- The general router has twenty-three entries, the ChatGPT-local router has
  one entry, and the checked total is twenty-four route edges.
- The public executable scenario fixture, focused mirrored contract, strict
  inventory, current-development release policy, and release-validator surface
  are integrated without a public dependency on publication-excluded evidence.
- Public and active v0.3.0 remain unchanged at 19/19/19.
- No dependency, provider, box, plugin, host platform, network, synced-folder
  implementation, provisioner, project command, lifecycle action, readiness
  action, Vagrantfile evaluation, Vagrant operation, release, publication, or
  active integration is selected.
- No ADR 0025 is needed because existing lifecycle and ownership decisions
  cover the retained provisional leaf.

## Structural and semantic disposition

The profile defines Vagrantfile-specific Green, Yellow, Orange, and Red
fallback signals for physical lines, concrete machines, provider
applications, network declarations, synced folders, provisioner and trigger
effects, host or platform branches, plugin and external dependency families,
shared mutable state domains, and responsibilities. Publication-excluded
evidence explains each threshold, measurement rule, coupling rule,
generated/vendor treatment, bounded exception, and rollback.

Semantic Red stops include unauthorized Vagrantfile evaluation or lifecycle
mutation; unsupported version, provider, box, plugin, host, Ruby, or
capability claims; protected-data or untrusted-command flow; unintended
network exposure; port, address, name, identity, or resource collisions;
unsafe synced folders; destructive or non-idempotent provisioner and trigger
effects; unresolved or manually mutated state; provider-specific behavior
represented as portable; false live-success claims; and crisis-level
undecomposed ownership without an accepted exception.

## Validation and review

| Gate | Result |
| --- | --- |
| Frozen scenarios and focused mirrored contract | Passed: 40 outcomes retained; 5 focused tests |
| Affected pytest selection | Passed: 129 candidate/policy unit tests; 80 project-projection/router tests; 109 release/skill-library integration tests plus 1 expected skip |
| Development checker | Passed in text and JSON at 25/25/25 |
| Public v0.3 checker | Passed in text and JSON at 19/19/19 |
| Source/mirror inventory | Passed: 18 maintained Python sources and 39 mirrored tests, split 23 unit and 16 integration |
| Python compilation | Passed |
| Record identity | Passed at 24 ADRs and 54 exits; APG34 allocates exit 00054 and no ADR; next ADR is 0025 and next exit is 00055 |
| Disposable current-development candidate/check | Passed for a local v0.4.0 candidate without publication using the declared pinned test environment |
| Markdown, links, privacy, durable identity, and whitespace | Passed |
| Fresh non-author review | Passed after one correction for source/rights, ownership/overlap, boxes/plugins/providers/networks/folders/provisioners/triggers/lifecycle safety, structural thresholds, integration, Ruby/Bash overlap, project authority, provenance/rollback, and complete diff |
| Formal commit-message checker | Required before and after the APG34 commit |
| Managed reports | One postcommit Git-show record and one explicitly associated operational record required |
| APG remote equality | Required after the normal push |

Combined, full, readiness, smoke, release, publication, source-repository,
target-repository, Vagrantfile evaluation, Vagrant command, plugin, box,
provider, machine, network, synced-folder, hypervisor, `.vagrant`, and global
Vagrant-state suites are intentionally not run. The focused selection and
disposable APG release candidate express the affected APG34 boundaries without
claiming Vagrant execution evidence.

## Rollback and next boundary

Rollback removes the leaf, flat projection, catalog and general-map entries,
current-development release-policy and validator entries, strict inventory
row, focused test, current-surface test expectation, and public scenario
fixture together while preserving the evaluation and exit history. No private
guidance was migrated. The project-scoped projection owner and its fixtures
remove only Vagrantfile, retain the APG33 Dockerfile profile, and expect 24
current leaves. The general router returns to 22 entries while the
ChatGPT-local route remains one.

No phase after APG34 is authorized. Native Go-test, `matryer/is`, `go-cmp`, a
unified Go testing-stack owner, nix-test, compatibility remediation,
readiness, smoke, and v0.4.0 release work remain separate future decisions
requiring explicit maintainer authority.
