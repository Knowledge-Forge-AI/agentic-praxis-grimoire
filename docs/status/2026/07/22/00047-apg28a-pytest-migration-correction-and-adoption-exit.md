# APG28A Pytest Migration Correction and Adoption Exit

Phase ID: `APG28A`

Status date: 2026-07-22

Disposition: Complete — pytest, xdist, coverage, and mirrored test-path migration adopted

## Scope and result

APG28A begins from the preserved APG28 worktree, records that stopped candidate
in a canonical managed Git-diff report with an associated operational record,
and preserves APG28 as Partial. It corrects runner aggregation, exact coverage,
worker and child-process completeness, artifact lifecycle, current release
policy, caller-controlled test-environment spoofing, and coverage quality. ADR
0024 is Accepted.

Historical v0.2.0 and v0.3.0 release surfaces remain immutable. Current v0.4
development policy runs the adopted test interface and all required mirrored
owners. Both report-tool Bats files remain because review did not accept their
complete replacement by pytest.

## Validation and review

The unit component passes 269 tests at 4,119/4,808 statements and 1,480/1,848
branches. The standalone integration component passes 262 tests with two
documented skips at 4,242/4,808 statements and 1,479/1,848 branches. Exact
component thresholds pass. Combined mode attempts both components; its
integration component reaches 4,243/4,808 statements and 1,480/1,848 branches,
and its union reaches 4,510/4,808 statements and 1,673/1,848 branches, passing
the exact 85/85 union gate.

Focused failure-mode tests cover real xdist worker crash, missing Python-child
coverage contribution, incomplete or foreign manifests, component aggregation,
artifact cleanup and retention, test-environment spoofing, and immutable historical
policy. Inventory, release, identity, skill-library, compilation, remaining
shell, command-help, documentation, privacy, and whitespace checks are phase
gates.

Fresh reviewers accept runner arithmetic, worker completeness, subprocess and
artifact lifecycle, release-policy boundaries, test quality, retained Bats
disposition, and coverage remediation. A fresh complete-diff review owns the
terminal stable-tree disposition.

## Preserved boundary and next authorization

APG28A changes no canonical skill content, maturity row, ChatGPT topology,
personal skill, target repository, public or active v0.3.0 object, or release
tag. It performs no readiness or publication work. APG29 may begin only after
this phase is committed, fully reported with the adopted Python tools, pushed to
private `main`, and verified remote-equal.
