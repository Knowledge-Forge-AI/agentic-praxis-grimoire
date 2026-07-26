# Agent Reporting Architecture

## Decision scope

This document defines the adopted v0.4 implementation for APG managed phase
reports. APG27A applies ADR 0021 and ADR 0023 through the standard-library
`libexec/agent_report` package, Python entry points for `git-show-report` and
`append-operational-report`, and `git-diff-report`. APG27 remains the truthful
partial precursor; APG27A corrects and adopts its preserved worktree.

The commands produce evidence only. They do not authorize a repository action,
accept a phase result, prove publication or push state, or permit work outside
the current assignment.

## Python-first executable policy

New executable APG project tooling is Python by default. Node.js requires a
strong project-specific reason. Shell remains appropriate for a thin launcher
or a task whose shell semantics are materially simpler and better supported.

Python-first does not mean dependency-first. Prefer the standard library and
the existing Git executable when they preserve exact behavior. A third-party
dependency must satisfy the project's dependency policy and demonstrate a
clear correctness or maintenance advantage.

## Shared reporting core

The implementation uses one importable Python package with thin `bin/`
CLI adapters. The package separates:

| Component | Responsibility |
| --- | --- |
| Git source adapter | Fixed-argument Git discovery and extraction for commits, indexes, worktrees, status, and patches |
| Report model | Typed commit, diff, path, section, relationship, and status-document values |
| Section rendering | Deterministic text sections, ordering, escaping, and binary/rename representation |
| Record envelope | Record kind, schema, identity, checksum, relationship, and framing |
| Safe destination and locking | Destination validation, exclusive lock, temporary output, atomic replacement, and cleanup |
| Operational-body framing | Body validation, association lookup, distinct-record append behavior, and standalone eligibility |
| CLI adapters | Argument parsing, diagnostics, exit codes, and invocation compatibility |

The core returns structured values and bounded diagnostics. CLI code does not
reimplement Git parsing, envelope rules, or destination safety.

## Git adapter decision

Use `subprocess` with fixed Git argument vectors as the baseline. The Python
[subprocess guidance](https://docs.python.org/3/library/subprocess.html)
supports argument sequences without shell parsing, and Git remains the
authority for Git object, index, rename, binary, and path semantics.

GitPython is permitted but not selected. It can simplify repository discovery
and object access, but still relies on Git for important operations and would
add a runtime, packaging, license, compatibility, and supply-chain surface.
Adopt it only if a migration prototype demonstrates a smaller and more exact
implementation than fixed Git CLI calls. A bounded combination may use a
library for read-only object modeling while retaining Git CLI extraction, but
mixed ownership must not produce two interpretations of the same field.

Never construct a shell command string from repository data. Pass each
argument separately, use `--` before path operands, set the working directory
explicitly, decode with a declared encoding and error policy, and preserve raw
bytes where the report contract requires byte fidelity.

Observational Git commands run with optional index locking disabled, using
`git --no-optional-locks` or the equivalent `GIT_OPTIONAL_LOCKS=0` environment.
Machine-readable status and path lists use NUL-delimited forms rather than
newline or whitespace parsing. Patch, name-status, and numstat extraction carry
the current `--no-ext-diff`, `--no-textconv`, and `--no-color` safety choices;
repository configuration must not substitute an external renderer or text
conversion for Git's native evidence.

## `git-show-report`

The adopted Python implementation preserves the version-2 observable contract.
Characterization covers:

- repository and exact commit resolution;
- root commits;
- ordinary single-parent commits;
- first-parent treatment of merge commits;
- author, committer, parent, subject, and full-message fields;
- exact changed-file and numstat behavior;
- full-index patch behavior, rename and binary representation;
- empty commits and unusual paths;
- status-document association;
- deterministic section ordering and envelope bytes; and
- destination, lock, replacement, and failure behavior.

The current binary contract is a bounded textual Git summary: binary numstat
entries make insertion and deletion totals unknown, and the patch section says
that binary files differ without embedding a `GIT binary patch`. Both show and
diff parity use that contract. An applyable binary patch would be a separate
schema and compatibility decision.

Exact old/new fixtures cover root, ordinary, empty, rename/binary/unusual-path,
and first-parent merge commits. Any later schema or output change remains a
separate migration decision with a compatibility and rollback plan.

## `git-diff-report`

The adopted `git-diff-report` represents an uncommitted result without changing
the real worktree or index. It records both the complete `git diff HEAD` state
and enough status detail to distinguish staged, unstaged, renamed, binary, and
untracked-intent changes.

### Read-only temporary-index sequence

1. Resolve the repository root, `HEAD`, actual index path, and index mode with
   commands that cannot refresh the index and that disable optional locks.
2. Before any status or diff observation, characterize the index and capture
   its absence or its file identity, metadata, and content digest. The first
   implementation supports only index states covered by fixtures. It fails
   closed on uncharacterized split, sparse, inherited custom `GIT_INDEX_FILE`,
   or unmerged indexes; legitimate index absence requires its own fixture and
   temporary-index initialization contract.
3. Capture NUL-delimited `git status --porcelain=v2 -z --untracked-files=all`
   data and staged and unstaged payloads from the real index, with optional
   locks, external diffs, text conversion, and color disabled as applicable.
4. Create a private temporary directory and copy every characterized file that
   constitutes the supported real-index state. If the characterized repository
   legitimately has no index, initialize only the temporary index from `HEAD`
   using Git's index plumbing.
5. Set `GIT_INDEX_FILE` only for child Git processes that use the temporary
   index.
6. At the repository root, run the semantic equivalent of `git add -N -- .`
   against the temporary index so non-ignored untracked files appear in the
   complete comparison.
7. Extract a full-index, rename-aware diff against `HEAD`, using the current
   bounded textual binary representation and disabling external diffs, text
   conversion, and color.
8. Render status, staged, unstaged, and complete-diff sections from the captured
   model.
9. Re-read `HEAD`, the real-index fingerprint, NUL-delimited status, and the
   relevant Git payloads. Any concurrent change or payload disagreement is a
   terminal drift failure; a report assembled across two states is never
   accepted.
10. Delete the temporary index and directory through bounded cleanup. Claim
    success only when the pre/post `HEAD`, index, worktree-status, and payload
    checks agree.

Git documents intent-to-add through
[`git add -N`](https://git-scm.com/docs/git-add) and worktree/index comparison
through [`git diff`](https://git-scm.com/docs/git-diff). The environment-only
temporary index avoids leaving intent-to-add entries or changing staged state.
Report generation never resets, cleans, stashes, checks out, stages in the real
index, or restores the user's worktree.

The status document is optional. When omitted, the model records `NONE`; it
does not fabricate a path or an empty status artifact. Result, final-gate, and
status-document labels do not alter the deterministic state-evidence ID.

## Record and operational composition

ADR 0023 specifies, and the adopted implementation enforces, this invariant:

> When a Git show or Git diff report exists for a result, the operational
> record is appended to that same phase report and explicitly related to that
> Git record. A standalone operational report is allowed only when no
> associated Git record exists.

The project basename and phase identity resolve to one canonical destination.
The destination lock is acquired before reading existing records and is held
through relationship validation and replacement. A present Git record causes
append-to-associated behavior or a visible rejection. Multiple records are
never guessed. A caller-supplied arbitrary destination cannot bypass the
canonical lookup or create a second standalone record.

Operational-body validation moves beyond shallow header recognition for
associated records. The parser verifies the `operational-report-v1` schema,
phase, outcome, and the applicable `primary_commit` or
`primary_git_report_id`. Legacy and free-form bodies retain shallow
classification only for standalone records in a phase report with no Git
record. Classification is not represented as full semantic validation.
Current tools append every valid invocation as a distinct envelope, including
identical record IDs; the parity baseline preserves that behavior. Dedupe,
logical replacement, or correction-in-place would require a separate schema
and compatibility decision.

## Destination safety and locking

The cross-platform baseline uses standard-library primitives:

- `pathlib` for lexical and resolved path handling;
- an exclusive lock directory created atomically in the destination parent;
- a temporary regular file in that same parent;
- flush and file `fsync` before replacement where supported;
- [`os.replace`](https://docs.python.org/3/library/os.html#os.replace) for
  POSIX local-filesystem atomic same-filesystem replacement;
- directory `fsync` where the platform exposes it; and
- bounded cleanup that never follows an unexpected link.

On POSIX local filesystems, the implementation preserves the characterized
regular-file, owner, restrictive-mode, source hard-link, and symlink contracts.
The replacement is created in the destination directory, which establishes the
same-filesystem boundary for `os.replace`. Network filesystems are unsupported
until their rename, durability, and lock semantics receive explicit evaluation.

On Windows, executable bits and Unix ownership are not equivalent. Atomicity,
sharing behavior, reparse handling, destination replacement, and directory
durability must be characterized for every supported filesystem before the
tool claims parity. Until then it fails closed. A supported implementation uses
a private user-controlled directory, rejects reparse-point ambiguity, and
reports which POSIX invariants are inapplicable. Characterized sharing
violations may receive a bounded retry and then fail without partial
replacement.

The lock owner file contains an invocation token with process identity and
random material but no protected payload. A lock is not broken merely because
it is old. The bounded wait fails closed rather than removing an unproven lock.
Signal and exception handlers remove only temporary resources and lock tokens
owned by the current invocation; they never remove a foreign lock or
destination.

## Cross-platform invocation contract

| Concern | Contract |
| --- | --- |
| Invocation | Support explicit `python -m` or script invocation; thin launchers locate their package without relying on the caller's current directory |
| Shebang and executable bit | Useful on POSIX, not required on Windows; documentation always includes an interpreter-based form |
| Paths | Use native path objects internally; never parse path lists by splitting command output on whitespace |
| Subprocesses | Fixed argument vectors, explicit cwd, captured binary streams, no implicit shell |
| Encoding and locale | Deterministic UTF-8 metadata; explicit raw-byte status, message, path-list, and patch boundaries |
| Modes, owners, links | Enforce supported POSIX invariants; explicitly diagnose unsupported or different Windows semantics |
| Replacement | POSIX local same-filesystem replacement is the initial atomic baseline; Windows filesystems require explicit characterization and network filesystems are unsupported |
| Locking | Atomic lock-directory acquisition only on characterized filesystems, with bounded wait, association-before-destination ordering, and conservative stale-lock recovery |
| Signals | Preserve nonzero interruption outcome and clean only invocation-owned temporary state |
| Git | Require a compatible Git executable and record its relevant feature boundary; do not approximate Git semantics in Python |

## Packaging and public projection

The shared core is the normal Python package `libexec/agent_report`. Release
projection policy includes the package, thin adapters, and focused tests. POSIX
entry points retain executable modes. Windows documentation uses an explicit
interpreter invocation, for example `python bin/git-diff-report --help`; report
replacement remains fail-closed there until its safety semantics are
characterized.

No runtime dependency is adopted by this decision. If later evidence selects
GitPython, pytest plugins, or another package, the phase records its license,
supply-chain, packaging, compatibility, rollback, and correctness evidence.

## Migration and rollback

The APG27 working-tree candidate completed the characterization-first
conversion mechanics, and APG27A corrected and adopted it. Failing-first
package, diff, and association contracts preceded replacement. The APG28
candidate proposes retiring the existing 23 Bats contracts, but fresh review
found that ordinary pytest execution skips material Git-show parity scenarios.
APG28A restores and retains both Bats files while adding unconditional pytest
real-boundary coverage for the Python implementation. A separate harness continues
to compare compatible old/new output bytes. The obsolete shared shell owner was
deleted only after its consumers and tests were migrated.

Git history is the rollback source. Restore the two Bash entry points and
`libexec/agent-report/common.sh`, remove `git-diff-report` and the Python
package, and restore the prior public-surface and focused-test inventory. APG27
stopped partial before commit; APG27A independently freezes historical v0.3.0
policy, removes the Red path-safety signal, and adopts the implementation. No
managed report migration is required because common envelope version 1,
Git-show format version 2, and operational format version 1 remain compatible.
