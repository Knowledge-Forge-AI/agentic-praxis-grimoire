# APG27 Python Agent Reporting and Git-Diff Report

Phase ID: `APG27`

## Outcome

Partial. The Python report candidate and focused safety corrections pass their
assigned review lanes, but APG27 stops before commit because the public-release
policy component exposed a second material compatibility correction need.
Historical v0.3.0 policy reconstruction remains unsupported by the candidate.

## Implemented slice

APG27 applies ADR 0021 through accepted ADR 0023. The former Bash report family
is replaced by one dependency-free importable package:

| Owner | Responsibility |
| --- | --- |
| `git_adapter.py` | Fixed-vector Git subprocesses with no shell evaluation, pager, color, or optional lock side effects |
| `models.py` | Immutable common-record and Git-observation contracts |
| `rendering.py` | Exact sections, common envelopes, digests, and complete-record parsing |
| `safety.py` | Lexical validation, POSIX file invariants, lock directories, private temporary state, and same-directory replacement |
| `show.py` | Version-2 commit metadata, parent comparison, changed files, numstat, message, patch, and integrity |
| `diff.py` | Version-1 private-index uncommitted snapshots, deterministic state IDs, and drift rejection |
| `operational.py` | Exact source-body framing, version-1 validation, existing-record lookup, and show/diff association |
| `cli.py` | Compatible show and operational adapters plus the new diff CLI and bounded exit classes |

The three extensionless `bin/` entry points use Python directly and remain
executable on POSIX. Interpreter invocation is documented for Windows. The old
shared shell helper is deleted only after its consumers and the 23 Bats
contracts run against the new entry points. Git history is the rollback owner.

## Format and compatibility disposition

Git-show report format version 2, the common envelope, record ID, hash scopes,
section ordering, root/single-parent/first-parent-merge comparison, exact
message handling, full-index patch, rename/binary/path behavior, append,
contention, permissions, and failure injection remain compatible on the
characterized POSIX platform.

The old/new parity harness uses one deterministic disposable repository and
compares exact report bytes for root, ordinary, empty, rename/binary/unusual-
path, and merge commits. Compatible standalone operational version-1,
legacy-key-value, and free-form records are also byte-identical. The only help
text difference is the required extension that names Git-diff record IDs.

Operational records remain distinct append events even when identical source
bytes produce the same record ID. No historical report migration is required.

## Git-diff state evidence

`git-diff-report` introduces format version 1 and
`GIT-DIFF-REPORT-<state-digest>` identities. The digest is domain-separated
from commit IDs and covers `HEAD`, the real-index fingerprint, NUL-delimited
porcelain-v2 status, staged and unstaged summaries, complete changed-file and
numstat evidence, and the full-index patch. Result, gate, and optional status-
document labels do not change the state identity; an absent status document is
rendered as `NONE`.

The command rejects inherited `GIT_INDEX_FILE`, unborn `HEAD`, split or sparse
indexes, unmerged entries, a clean state, unsafe paths or destinations, and
pre/post drift. It copies or seeds only an invocation-owned index, applies
intent-to-add only there, includes non-ignored untracked files, and repeats both
real-state and private-index evidence before acceptance. Focused integration
evidence confirms that staged, unstaged, mixed, renamed, binary, and untracked
state is captured while the real index bytes and porcelain status remain exact.
Interruption and injected failures leave no report or invocation-owned
temporary state.

## Operational association

The canonical project/phase report is the only association lookup surface. The
destination lock is held while complete common records are parsed, the exact
related Git record is selected, the body contract is cross-checked, and the
replacement is written.

- A show relation requires an existing show ID, the matching resolved commit,
  and matching `primary_commit`.
- A diff relation requires an existing diff ID, no related commit, and matching
  `primary_git_report_id`.
- Both require `operational-report-v1`, matching phase, and matching outcome.
- Any existing Git record makes an omitted or nonexistent relation terminal.
- A standalone legacy, free-form, or validated version-1 record is compatible
  only when no Git record exists.
- Multiple Git records are never guessed, and duplicate associated operational
  appends remain distinct complete records after the selected Git record.

## Dependency and platform disposition

GitPython is not selected. Fixed-vector standard-library `subprocess` calls
preserve Git's object, index, rename, binary, quoting, and patch semantics
without adding dependency, packaging, license, or supply-chain surface.

The supported write boundary is a local POSIX filesystem with current-owner
directories and regular mode-0600 report files. Temporary replacement is
created in the destination directory and committed with `os.replace`. Foreign
or stale locks are not removed. Windows accepts interpreter-based argument
parsing but fails with a precise unsupported replacement-safety diagnostic;
reparse, sharing, and durability behavior is not claimed. Network filesystems
are unsupported.

## Python profile disposition

Python profile level: `Red`.

No repository-configured analyzer exists, so these are APG fallback counts for
the maintained package. Modules range from 5 to 437 physical lines;
`safety.py` and `show.py` are Yellow and the others are Green. The largest
callable contains 31 recursive statements, Yellow. Maximum cyclomatic
complexity is 19, Orange. Maximum branch count is 13, Red. Maximum nesting is 5
and maximum argument count is 8, both Orange. Maximum local bindings are 12,
Yellow.

The Orange and Red signals occur in explicit compatibility and safety decision tables:
source-path validation, supported-index rejection, status-path validation,
changed-file classification, binary numstat aggregation, and operational
association. The Red branch signal in `validate_source_path` requires
decomposition before acceptance. APG27 therefore records no exception and does
not claim Python-profile acceptance.

## Current validation boundary

Failing-first unit and integration runs initially failed because the package and
diff command did not exist. The current candidate passes eight focused
unit tests, seven real-repository integration tests, three exact parity tests,
and all 23 existing report-tool Bats tests. Directly affected public-release
tests pass at 10 unit, 31 integration, and 4 version-policy cases; the latter do
not yet pin immutable v0.3.0 policy reconstruction. Parity, temporary-index,
association, and platform-safety lanes accept the corrected candidate. The
packaging lane accepts package ownership, entry points, help, compilation,
rollback, and the version-specific configured-validation correction, but
reproduces the unresolved historical-v0.3 policy failure.
The sixth, complete-diff lane finds no additional material issue and accepts
the terminal partial disposition.

The complete APG suite is deliberately not run. APG27 is an implementation
slice, not a readiness or release checkpoint.

## Terminal stop

The first public-release-policy correction makes configured validation consume
the already validated version-specific wrapper, helper, and test arrays; a
historical v0.2 build-and-check regression passes. Fresh review then reproduces
a second material defect in that same component: every non-v0.2 identity is
matched only against the APG27 inventory, so the unchanged v0.3.0 policy cannot
be reconstructed or checked. The required version-bounded historical v0.3
surface is not added because the assignment permits only one bounded correction
per component.

APG27 is not committed or pushed. The working-tree candidate remains available
for a separately authorized correction or rollback decision. No successor is
authorized.

## Preserved boundaries

The APG27 candidate changes no skill, catalog row, capability map, maturity
disposition, pytest dependency or test-path migration, ChatGPT topology,
personal skill, target repository, active public-backed integration, published
v0.3.0 object, or release tag. Those immutable objects remain byte-unchanged,
but the candidate development checker does not yet preserve v0.3.0
reconstruction. No phase after APG27 is authorized.

## Subsequent disposition — APG27A

APG27 remains a truthful partial stopped-worktree phase. APG27A began from the
preserved candidate, corrected immutable v0.3.0 policy reconstruction and the
Red `validate_source_path` branch-count signal, and adopted the corrected
Python reporting implementation. This forward disposition does not rewrite
APG27's outcome, review limit, or original authorization boundary.
