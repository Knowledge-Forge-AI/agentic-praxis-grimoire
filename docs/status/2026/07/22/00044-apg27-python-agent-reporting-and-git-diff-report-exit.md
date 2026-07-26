# APG27 Python Agent Reporting and Git-Diff Report Exit

Phase ID: `APG27`

## Disposition

Partial — report candidate implemented but historical v0.3 policy compatibility unresolved

## Scope and result

APG27 accepts ADR 0023 and implements a working-tree Python-first reporting
candidate. The candidate is not committed or adopted because its release-
policy adapter does not preserve historical v0.3.0 reconstruction. The former
Bash Git-show and operational-report commands are
thin Python entry points over the dependency-free `libexec/agent_report`
package. The shared `libexec/agent-report/common.sh` owner is removed after its
consumers and compatibility contracts migrate. Git history remains the
rollback source.

The package separates Git command execution, report models, rendering and
parsing, destination safety, Git-show collection, Git-diff collection,
operational validation and association, and CLI behavior. GitPython is not
selected; fixed Git CLI argument vectors preserve Git semantics without a new
runtime or packaging dependency.

Git-show format version 2 and the compatible operational envelope remain
unchanged on the characterized POSIX boundary. Exact old/new fixtures cover
root, ordinary, empty, rename, binary, unusual-path, and first-parent merge
commits, plus compatible standalone operational bodies. Distinct operational
append events remain distinct records.

## Git-diff and association behavior

The new `git-diff-report` command emits format version 1 with deterministic
`GIT-DIFF-REPORT-<state-digest>` identity. It observes `HEAD`, the real index,
NUL-delimited porcelain-v2 status, staged and unstaged summaries, changed-file
and numstat evidence, and the full-index patch. An invocation-owned temporary
index adds intent only privately so non-ignored untracked files participate.
The command rejects inherited custom, split, sparse, unmerged, unborn, clean,
unsafe, or drifting states and verifies the real index and worktree observation
again before accepting a report.

An associated operational append must name a complete Git-show or Git-diff
record already present in the same canonical phase report. Show association
cross-checks the resolved commit and `primary_commit`; diff association permits
no related commit and cross-checks `primary_git_report_id`. Multiple Git
records are never guessed. Standalone compatible operational append remains
available only when the phase report has no Git record.

## Safety and platform boundary

The supported write surface is a local POSIX filesystem with current-owner
directories and regular mode-0600 report files. The implementation preserves
the characterized symlink, hard-link, lock-directory, same-directory temporary
file, replacement, cleanup, and append boundaries. Windows supports
interpreter-based argument handling but replacement fails closed with an
unsupported-safety diagnostic until reparse, sharing, and durability behavior
is characterized. Network filesystems remain unsupported.

## Validation and review

Failing-first unit and integration tests initially fail for the absent package
and Git-diff command. The resulting eight focused unit tests, seven disposable-
repository integration tests, three exact old/new parity tests, and all 23
existing report-tool Bats tests pass. Directly affected public-release tests
pass at 10 unit, 31 integration, and 4 version-policy cases; fresh review
independently reproduces the unpinned v0.3.0 historical-policy failure.
Identity, skill-library, compilation,
focused release-policy, launcher, and whitespace checks pass where run. Five
fresh lanes accept report parity, temporary-index behavior, association,
platform safety, and package ownership after bounded corrections. Packaging
review then reproduces a second material correction need in the public-release-
policy component: v0.2 configured validation now uses its loaded historical
arrays, but the unchanged v0.3.0 policy has no equivalent version-bounded
historical surface. The assignment's one-correction-per-component rule stops
APG27 at that boundary. A sixth, complete-diff lane finds no additional
material issue and accepts this terminal partial disposition. The complete APG
suite is deliberately not run.

APG fallback Python measurement is Red: the maximum branch count is 13 in
`validate_source_path`. That structural stop also remains unresolved in the
uncommitted candidate.

## Preserved boundary and next authorization

The candidate changes no skill, catalog row, capability-map entry, maturity
decision, pytest dependency or suite location, ChatGPT topology, personal
skill, target repository, active public-backed integration, published v0.3.0
object, or release tag. No APG27 commit, push, or Git-show report is produced.
Partial worktree evidence uses the accepted Git-diff format with one explicitly
associated operational record. No successor phase is authorized; any resume,
correction, rollback, or later v0.4 slice requires a new maintainer request.

## Subsequent disposition — APG27A

APG27 remains a truthful partial stopped-worktree phase. APG27A preserved that
candidate and its evidence, corrected the two recorded acceptance defects, and
adopted the resulting Python reporting implementation. This later disposition
does not alter APG27's original partial result.
