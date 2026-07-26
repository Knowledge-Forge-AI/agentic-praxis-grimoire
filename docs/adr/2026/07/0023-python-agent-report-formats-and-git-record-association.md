# ADR 0023: Python Agent-Report Formats and Git-Record Association

## Status

Accepted

## Date

2026-07-22

## Context

ADR 0021 selected a standard-library Python reporting core, fixed-vector Git
commands, a private-index uncommitted snapshot, and explicit Git/operational
composition as the preferred v0.4 architecture. The existing implementation
still consisted of two Bash entry points and one shared shell helper. It had no
uncommitted-diff record and treated related record identifiers as shallow text
rather than verified records in the canonical phase report.

The conversion must preserve exact `git-show-report` version-2 evidence and
compatible operational-report version-1 records while introducing a distinct
Git-diff identity. The implementation also needs one unambiguous rule for when
an operational record may stand alone, how it relates to show and diff records,
and which filesystem and platform claims are supported.

## Decision

Use the importable standard-library `libexec/agent_report` Python package as the
single implementation owner for Git subprocesses, report models, section and
envelope rendering, destination safety and locking, Git-show collection,
Git-diff collection, operational validation and association, and CLI adapters.
The extensionless `bin/` programs remain executable Python entry points.

Preserve `git-show-report` report format version 2, its five-argument CLI, its
`GIT-SHOW-REPORT-<full-commit>` identity, and its characterized observable
contract. Preserve common envelope version 1 and operational-report format
version 1. Relationship fields may be extended for Git-diff association, but
compatible standalone operational records retain their existing bytes.

Introduce `git-diff-report` format version 1. Its identity is
`GIT-DIFF-REPORT-<state-digest>`, where the digest is domain-separated and
derived from `HEAD`, the real-index fingerprint, real-index status, staged and
unstaged summaries, complete changed-file and numstat evidence, and the
full-index patch. It is state evidence, not a commit identity. The optional
status document renders as `NONE` when omitted and does not affect the state
identity.

Collect a Git-diff snapshot through an invocation-owned temporary index. Reject
an inherited `GIT_INDEX_FILE`, unborn `HEAD`, split or sparse index, unmerged
entries, clean state, unsafe destination, or concurrent drift. Disable optional
Git locks, seed the private index from the characterized real index or `HEAD`,
run intent-to-add only there, capture complete `git diff HEAD` evidence, repeat
the real and private-index observations, and accept only an exact pre/post
match. Never reset, clean, restore, stage through, or replace the real index or
worktree.

An operational record associated with Git evidence is appended to the same
canonical phase report and names one existing complete Git record exactly.

- A Git-show relation requires the matching resolved commit, show record ID,
  and `operational-report-v1` `primary_commit`.
- A Git-diff relation has no related commit and requires a matching
  `primary_git_report_id`.
- When any complete Git show or diff record exists, an operational append
  without an exact relation is rejected.
- When no Git record exists, a standalone operational record remains valid.
- Multiple Git records are never guessed; the caller supplies the exact ID.
- Every successful invocation remains a distinct appended envelope, including
  duplicate operational record IDs.

Use `pathlib`, `hashlib`, fixed subprocess argument vectors with `shell=False`,
private temporary directories, atomic lock-directory creation, a same-directory
temporary replacement, `fsync` where supported, and `os.replace`. POSIX local
filesystems are the characterized write boundary. On Windows, interpreter
invocation and native argument parsing are supported, but report replacement
fails with a precise unsupported-safety diagnostic until reparse, sharing, and
replacement behavior is characterized. Network filesystems are unsupported.

Do not adopt GitPython. The fixed-vector Git CLI implementation preserves Git's
object, index, path, rename, binary, and patch semantics without adding a
runtime, packaging, license, or supply-chain dependency.

Rollback restores the pre-conversion Bash entry points and shared shell helper
from Git history, removes `git-diff-report` and the Python package, and restores
the prior focused tests and public-surface inventory. Existing managed report
files require no migration because common envelope version 1, Git-show format
version 2, and operational format version 1 remain readable.

## Alternatives considered

- Continue extending the shared Bash implementation. Rejected because diff
  state modeling, cross-record parsing, platform policy, and association would
  couple more behavior to shell control flow.
- Adopt GitPython. Rejected because no measured parity or maintenance advantage
  justified a dependency and Git CLI calls remain necessary for exact patch and
  index semantics.
- Use `git add -N` in the real index and restore it. Rejected because an
  interruption could leave user staging state changed.
- Give Git-diff records commit-shaped identifiers. Rejected because an
  uncommitted snapshot is mutable state evidence and not a commit object.
- Guess the only or newest Git record during operational append. Rejected
  because ordering and concurrency can make that choice ambiguous.
- Reject all standalone operational records. Rejected because read-only and
  non-Git phases still require compatible operational evidence.
- Claim Windows or network-filesystem parity from Python alone. Rejected because
  language portability does not establish replacement, sharing, lock, or
  durability semantics.

## Consequences

The decision calls for one typed, importable implementation and one canonical
record parser. The partial APG27 candidate preserves existing Git-show bytes on
the characterized POSIX platform. Compatible standalone operational output also
remains byte-compatible; candidate associated records gain semantic validation
and verified same-report relationships.

Candidate Git-diff reports include non-ignored untracked files without modifying
the real index. Their IDs are reproducible for the same captured state even when
result, gate, or optional status-document labels differ. Drift produces no
report.

APG27A includes the Python package, three entry points, and focused Bats and
Python contracts in the public source inventory. APG27 remains partial; APG27A
corrects its historical-policy and path-safety stops and adopts the
implementation. The prior shell implementation remains available through Git
history. No dependency,
pytest migration, Windows write-parity claim, network-filesystem claim, release,
or successor authorization follows from this decision.
