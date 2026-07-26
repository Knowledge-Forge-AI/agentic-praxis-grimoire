# APG25 v0.4 Structured Project Work Foundation

Phase ID: `APG25`

## Outcome

Complete — v0.4 structured-project architecture and roadmap accepted.

APG25 accepts ADRs 0020-0022 and the detailed v0.4 roadmap. It establishes
project-owned formal and non-phase defaults, scoped testing and coverage
architecture, Python-first report design, ChatGPT-manager topology, and a
bounded personal hygiene-skill transition plan. It implements only one
authorized behavior-bearing correction to an existing assignment-composition
skill.

## Structured work and prompt compression

[`docs/structured-project-phase-defaults.md`](../structured-project-phase-defaults.md)
defines one-commit formal phases, finalized status or exit before commit,
formal commit content, minimal ADRs, proportional formal and non-phase docs-only
work, ordinary atomic non-phase commits, scoped validation, associated managed
reports, and the no-successor boundary. The convention remains subordinate to
the target repository and task authority.

`composing-approved-roadmap-assignments` now loads those defaults, references
them instead of repeating ordinary mechanics, and preserves deviations,
phase-specific evidence, authority, acceptance, stop, and successor boundaries.
Three frozen public-safe assignment pairs cover ordinary implementation,
formal docs-only, and release/high-risk behavior. All retain their material
contract while removing repeated procedure. The correction count is one.
One pre-existing simple-direct-task non-trigger remains unchanged.

## Testing and coverage

[`docs/testing-and-coverage-policy.md`](../testing-and-coverage-policy.md)
sets scoped unit and changed-boundary integration tests as the ordinary default.
Complete or smoke suites require a testing-infrastructure, defect, repository,
CI/CD, readiness, release, or explicit authority reason.

Coverage remediation expands from current-task behavior through adjacent code,
edited modules, packages, and parent packages only while a useful untested
contract exists. It stops for human input after the suite-owned source surface
is exhausted. A later bounded correction to
`implementing-with-test-discipline` will own that executable procedure.

Unit tests may isolate external or unsafe collaborators but must execute the
subject's real logic. Integration tests use the real boundary they claim; a
mocked Git, filesystem, subprocess, or report collaborator cannot be described
as integrated.

The accepted APG migration architecture uses pytest, pytest-xdist, pytest-cov,
coverage.py branch measurement, eight workers, mirrored test roots, independent
80% statement and branch gates, and an 85% statement and branch union gate.
It explicitly fails empty collection, source omission, stale or duplicate
paths, suite contamination, worker crash, incomplete data, exact-threshold
failure, and unsupported-platform silent omission.

## Python-first reporting

[`docs/agent-reporting-architecture.md`](../agent-reporting-architecture.md)
adopts Python for new executable APG tooling by default. The future reporting
core separates Git extraction, model, rendering, envelope, destination/locking,
operational framing, and CLI adapters. Fixed-argument standard-library
subprocess calls to Git are the baseline; GitPython remains permitted only
after a dependency and parity evaluation.

The future `git-show-report` preserves current root, parent, merge, patch, and
destination behavior. A new `git-diff-report` will use a private temporary
index for intent-to-add coverage, capture complete `git diff HEAD` and staged/
unstaged status, permit status document `NONE`, and prove the real index and
worktree remain unchanged.

An operational record associated with Git show or diff belongs in the same
phase report and explicitly relates to that Git record. Standalone operational
creation is valid only when no associated Git record exists.

## ChatGPT topology and private transition

[`docs/chatgpt-manager-skill-topology.md`](../chatgpt-manager-skill-topology.md)
accepts `skills/chatgpt/<name>/` as the future canonical owner for
actor-qualified manager leaves while retaining flat Codex projections. A
dedicated future subrouter owns only ChatGPT-manager selection; the general
router sees that subrouter as one capability. Explicit selection remains valid
and there is no mandatory chain.

`composing-approved-roadmap-assignments` is the only current leaf classified
for initial relocation. Worker assignment, planning, design, implementation,
debugging, review, synthesis, and technical profiles remain general.

The publication-excluded coherent-unit ledger recommends later decommission
evaluation for `docs-only-change-hygiene`, scope reduction for
`git-history-hygiene`, and later decommission evaluation for
`repomap-phase-hygiene`. Each requires current replacement evidence,
source-qualified positive and non-trigger shadow, private-only disposition,
restoration proof, fresh review, and explicit human authority. APG25 edits none
of them.

## Roadmap

The [detailed v0.4 roadmap](../v0-4-roadmap.md) places APG26 first with
`pytest-test-profile` and `converting-bash-scripts-to-python`. Later unallocated
slices cover report conversion and new diff reporting, test migration, existing
process-skill corrections, ChatGPT relocation/subrouting, personal-skill
transition, remaining test/profile gaps, cross-repository dogfood, individual
readiness, and v0.4.0 publication. No later phase ID is allocated.

The remaining capability list explicitly retains independent Minitest, Nix
test, Vagrantfile, Dockerfile, native Go test, `matryer/is`, and `go-cmp`
owners plus a unified Go testing-stack owner that does not erase its components'
separate triggers.

## Source treatment and preservation

Current APG report/test/skill owners, the designated RepoMap prototype, current
official pytest/xdist/coverage/Python/Git sources, and three personal skills
were inspected. RepoMap's serial coverage and suite model is useful evidence,
but its current xdist path disables coverage and is not adopted as an APG
solution. Private material supplies classification evidence only and is not
copied or made a public dependency.

Private development remains nineteen canonical skills, nineteen catalog rows,
nineteen checked-in projections, fourteen stable rows, five provisional rows,
and eighteen routable non-router capabilities. Public v0.3.0 and the active
integration remain unchanged.

## Validation and review

The composition correction has a failing-first static contract test, manual
positive/non-trigger scenario comparison, and resulting skill-library
validation. Documentation, directly affected checker and skill tests, identity,
privacy, link, Python compilation, applicable shell syntax, and whitespace
gates pass. The complete APG suite is deliberately not run because APG25 is
architecture plus one focused skill correction, not a release checkpoint.

Fresh non-author review covers phase defaults and prompt compression,
testing/coverage and report architecture, ChatGPT topology and personal
transition, and the complete roadmap and diff. Corrections were re-reviewed;
the final disposition has zero unresolved material defects.

## Boundary

APG25 adds no skill, dependency, package metadata, pytest runner, test move,
report conversion, `git-diff-report`, ChatGPT canonical move, subrouter,
personal-skill edit, public release, active-source change, or successor work.
APG26 may begin only after the APG25 commit is pushed, remote-equal, and fully
reported.
