# APG30 ChatGPT-Manager Topology and Subrouter Exit

Phase ID: `APG30`

Status date: 2026-07-23

Disposition: Complete — nested ChatGPT-manager topology and subrouter
implemented.

## Scope

APG30 implements ADR 0022's nested ChatGPT-manager canonical owner and
subrouter. It moves the unchanged manager-assignment leaf, preserves flat
Codex discovery, updates current checker, project/user lifecycle,
current-development public-projection policy, tests, and current documents,
and retains historical direct-child release compatibility.

## Outcome

- Development is 22 canonical leaves, 22 catalog rows, and 22 flat
  projections.
- Maturity is fourteen stable and eight provisional rows.
- The general map has nineteen ordinary non-ChatGPT leaves and one
  `chatgpt-manager-workflow` edge.
- The ChatGPT-local map has one
  `composing-approved-roadmap-assignments` edge.
- The moved manager-assignment procedure bytes and maturity are unchanged.
- Project and user lifecycle code resolves source-declared direct or nested
  canonical paths without changing flat state names or schema.
- Historical v0.1.0 through v0.3.0 policy remains direct-child and immutable.
- Public and active v0.3.0 remain 19/19/19.
- No personal skill, target repository, application configuration, release
  ref, database, graph, Nix state, or deployment changed.

## Validation

| Gate | Result |
| --- | --- |
| Frozen topology cases | Passed: 30 expected outcomes retained |
| Focused affected pytest | Passed across two disjoint lanes: 313 tests, 1 skipped phase-evidence gate, 706 subtests |
| Isolated pytest runner | Passed: 5 focused regressions; unit component 283 tests and 1,544/1,928 covered branches |
| Development checker | Passed in text and JSON at 22/22/22 |
| Public v0.3 checker | Passed in text and JSON at 19/19/19 |
| Source/mirror inventory | Passed: 36 tests and 18 maintained Python sources |
| Python compilation and affected help | Passed |
| Moved-leaf byte identity | Passed; exact pre-move and post-move `SKILL.md` bytes match |
| Disposable current-development candidate/check | Passed for a local v0.4.0 candidate without publication |
| Markdown, local links, privacy, identity, and whitespace | Passed |
| Fresh non-author review | Passed across nested discovery, lifecycle/history, router ownership, public projection/rollback, and complete diff |
| Formal commit-message checker | Required before and after the APG30 commit |
| Managed reports | One postcommit Git-show record and one explicitly associated operational record required |
| Remote equality | Required after the normal push |

No combined, readiness, smoke, or release suite ran. The focused selection
reliably expressed the affected unit and integration boundary.

## Structural disposition

The new nested-discovery and router-map responsibility is isolated in a
focused Python topology module. Project canonical discovery was decomposed to
remove the new Red callable signal. The legacy checker remains a bounded
Red-size owner. The user lifecycle module crosses from the 1,000-line Orange
ceiling to 1,015 lines under an explicit bounded new Red-size exception for
one cohesive existing responsibility, with adverse transition evidence,
complete APG29 rollback, and decomposition required before further growth.
The three initial test-file Red crossings were decomposed. The pytest runner's
deterministic pinned-plugin loading has focused regression assertions while
the canonical owner is 597 lines, below its 598-line entry size and within the
Orange band. No unrelated
refactor was mixed into APG30. Exact structural evidence
and rollback are recorded in the APG30 evaluation and publication-excluded
phase records.

## Deferred work and next authorization

Application discovery requires a post-commit full Codex application restart.
Its absence is not an APG30 defect. APG31 is authorized only after this phase
is committed, pushed, remote-equal, fully reported, and followed by that
restart. APG31 owns fresh source-qualified topology evidence and the bounded
personal-hygiene shadow and conditional transition.

No phase after APG31 is authorized. APG30 does not authorize v0.4.0
publication, active-integration change, maturity review, readiness, or release.
