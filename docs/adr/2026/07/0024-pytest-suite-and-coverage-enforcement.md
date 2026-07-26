# ADR 0024: Pytest Suite and Coverage Enforcement

- Status: Accepted
- Date: 2026-07-22
- Phase: APG28

## Context

ADR 0021 selected pytest, xdist, pytest-cov, coverage.py branch measurement,
mirrored ownership paths, and exact 80/80/85 gates. APG28 must turn that design
into one deterministic repository interface while preserving the existing
behavioral suite and immutable public v0.3.0.

## Decision

APG owns `bin/apg-test` with `unit`, `integration`, and `unit-integration`
modes. The default is eight xdist workers; restarts are disabled. Exact integer
statement and branch counts enforce 80% for each component and 85% for the
combined data union.

`testing/apg-test-inventory.json` inventories every maintained `libexec` Python
source, every thin Python launcher exclusion, and every mirrored test owner.
All inventoried sources must appear in every coverage report and participate
in the unit, integration, and combined denominators. A source cannot disappear
from a gate to improve a threshold.

Python tests live below the hyphenated mirror roots. The runner rejects stale
flat paths, missing owners, wrong mirrors, untracked sources, foreign coverage,
unexpected parallel data, missing output, nonzero pytest status, and dependency
version drift. Coverage subprocess patching and the invoked virtual-environment
directory preserve Python child measurement. Disposable project-skill copies
use direct coverage.py parallel collection and canonical path equivalence.

Python subprocess and xdist worker activity use invocation-scoped manifests.
The controller requires matching start, collection, completion, node-down, and
coverage-contribution evidence and rejects missing, duplicate, foreign, stale,
or incomplete records. Combined mode attempts both valid components and reports
their failures before deciding the exact union result. Invocation-owned
artifacts are removed after success and may be retained explicitly on failure.

The two report-tool Bats files remain maintained because material shell-harness
boundaries are not fully superseded by pytest. Pytest independently exercises
the Python report implementation through real Git, filesystem, subprocess,
append, association, concurrency, and safety boundaries.

## Consequences

The adopted test stack is pytest 9.1.1, pytest-xdist 3.8.0, pytest-cov 7.1.0,
and coverage.py 7.15.2. APG28 did not accept its proposal because the honest
full inventory missed coverage gates, release-policy tests failed, process
accounting remained incomplete, and Bats deletion lacked sufficient evidence.
APG28A corrected those defects, satisfied the exact component and union gates,
retained both Bats owners, and accepted this decision.
