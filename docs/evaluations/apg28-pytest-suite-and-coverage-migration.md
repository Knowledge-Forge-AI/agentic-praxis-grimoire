# APG28 Pytest Suite and Coverage Migration

## Scope

APG28 evaluates an implementation of ADR 0021's deferred test architecture and
records ADR 0024 as a proposal. Public and active
v0.3.0, target repositories, personal skills, and canonical skill content are
outside the write scope.

## Result

Partial. The uncommitted candidate collects the APG Python suite from mirrored
unit and integration roots and supplies a Python-first runner, exact dependency
pins, strict inventory validation, exact integer arithmetic, and coverage-data
union. It was not adopted.

The corrected full-source unit run passed 152 tests but measured only
1,850/4,623 statements and 554/1,774 branches. The integration candidate
measured 3,682/4,623 statements and 1,180/1,774 branches, but four
release-policy tests failed. The measured data union reached 4,056/4,623
statements and 1,410/1,774 branches. These results miss unit 80/80,
integration 80/80, and combined 85% branches.

Fresh reviews also found that Python child-process coverage and xdist worker
completion were not affirmatively accounted for, and that the removed
Git-show Bats scenarios were optional skips rather than unconditional pytest
coverage. Those are material migration defects.

The exact dependency versions are pytest 9.1.1, pytest-xdist 3.8.0,
pytest-cov 7.1.0, and coverage.py 7.15.2. The first three are MIT-licensed;
coverage.py is Apache-2.0 licensed. No runtime dependency was added.

## Coverage policy

The first candidate excluded most maintained modules from gate denominators.
Fresh review rejected that as coverage gaming. The bounded correction assigns
every maintained `libexec` module to every component and union gate. The
corrected runner therefore fails instead of reporting a misleading pass.

## Preservation

Historical v0.2 and v0.3 public policy arrays retain their original paths.
The uncommitted development candidate names mirrored pytest owners and test
infrastructure. Public v0.3.0 and the active installation are unchanged.

## Subsequent disposition

APG28 remains Partial. APG28A preserved this exact stopped-worktree state in a
managed Git-diff report with an explicitly associated operational record, then
corrected and adopted the candidate forward. That later adoption does not
rewrite APG28's measurements, review findings, or terminal result.
