# APG28A Pytest Migration Correction and Adoption

Phase ID: `APG28A`

## Outcome

Complete. APG28A preserves APG28 as a truthful partial stopped-worktree phase,
corrects its test-infrastructure defects, and adopts the resulting pytest,
xdist, coverage, and mirrored-path implementation.

## Preserved starting state

Before correction, the complete APG28 worktree was captured in one canonical
Git-diff report with an explicitly associated operational record. The report
includes tracked and untracked candidate paths, preserves the real index and
worktree, and records the maintainer-supplied raw patch as supplementary
evidence. APG28's evaluation, exit, and private records continue to state its
Partial disposition.

## Corrected runner and process accounting

Standalone modes run one component. Combined mode attempts both independently
after shared preflight, reports all component failures, and computes a union
only from valid component data. Exact integer arithmetic enforces statements
and branches at 80% for each component and 85% for the union.

Every invocation receives an unpredictable run identifier. Controller, xdist
workers, and required Python children emit bounded run-scoped evidence for
start, collection, terminal results, completion, node-down, and coverage-data
contribution. Missing, duplicate, foreign, stale, wrong-run, incomplete, or
crash evidence fails. Real worker-crash and missing-child-contribution fixtures
exercise those failure paths.

Artifacts use a fresh invocation-owned directory. Success removes it. Failure
removes it by default or retains it only through the explicit retention option,
with the retained path reported. User-supplied parents are validated.

## Release and compatibility boundaries

Historical v0.2.0 and v0.3.0 policy surfaces remain immutable. Current v0.4
development policy requires the adopted runner and directly invokes all
configured Bats and mirrored pytest owners. Caller-supplied APG test controls,
pytest options, coverage variables, Python-path controls, and Git configuration
cannot spoof or redirect configured-test execution. Nested release fixtures are
bounded without relying on a caller-controlled recursion guard.

Both report-tool Bats files remain maintained. Review found that pytest did not
fully supersede every shell-harness boundary, so no deletion was accepted. The
Python integration owners nevertheless exercise current report behavior through
real Git repositories, filesystems, subprocesses, locking, and report framing.

## Coverage and review

The final unit gate passes 269 tests with 4,119/4,808 statements and
1,480/1,848 branches. The final standalone integration gate passes 262 tests
with two documented skips, 4,242/4,808 statements, and 1,479/1,848 branches.
Both meet their exact 80/80 contracts. The final combined run's integration
component independently reaches 4,243/4,808 statements and 1,480/1,848
branches; its union reaches 4,510/4,808 statements and 1,673/1,848 branches,
satisfying the exact 85/85 union contract.

Fresh non-author reviews accept aggregation and exact arithmetic, xdist
completeness, subprocess and artifact accounting, release recursion and version
surfaces, unit/mock and real-integration quality, retained Bats disposition, and
coverage-remediation quality. A complete-diff review owns terminal acceptance.

## Preserved boundaries

APG28A changes no canonical skill content, catalog maturity, ChatGPT topology,
personal skill, target repository, public or active v0.3.0 object, release tag,
or post-APG28A process-skill behavior. It does not claim readiness or publish a
release.
