# Manager-Worker Protocol

## Purpose

This protocol separates human authority, delegated ChatGPT management,
top-level Codex execution, internal worker coordination, managed report
artifacts, and external acceptance. A worker result, commit, report, or
recommendation transports evidence; none grants authority or accepts the work
by itself.

## Role and report direction

```text
Human maintainer
    retains ultimate project, roadmap, publication, license, and
    destructive-action authority; authorizes a task, phase, or bounded roadmap
    envelope; and retains ultimate project disposition

ChatGPT manager
    plans and reviews only within the human-authorized envelope, constructs
    bounded Codex assignments, reviews Codex evidence, and stops at the
    envelope boundary or a reserved human decision

Top-level Codex manager
    executes the bounded ChatGPT assignment, delegates internally, integrates,
    validates, commits and pushes when authorized, and produces required final
    reports

Internal Codex workers
    perform bounded research, implementation, or review and return results
    through the agent harness

Top-level Codex manager
    returns the final response and any managed Git or operational report
    references to ChatGPT for delegated review and human disposition as required
```

Managed report commands are not the ordinary manager-to-worker channel.
Internal read-only workers do not create report bodies or invoke them. A task may
explicitly establish an exceptional intermediate commit, but the top-level
manager still reviews that evidence, retains its integration disposition, and
owns external closeout unless the external authority states otherwise.

## Authority and conflicts

Apply this order within an authorized task or roadmap envelope:

1. safety, privacy, and explicit human-maintainer authority;
2. applicable repository instructions and accepted decisions, except where the
   human maintainer explicitly authorizes their supersession;
3. ChatGPT direction inside the human-authorized envelope and consistent with
   the preceding constraints;
4. the top-level Codex assignment and its authorized clarifications; and
5. established project conventions where higher authority is silent.

Human authority is not interchangeable with ChatGPT delegation. ChatGPT may
refine assignments and review evidence inside the approved envelope, including
issuing successive bounded phases when the envelope expressly allows it until a
defined stop condition. ChatGPT may not silently expand a roadmap, introduce an
unapproved epic, approve a destructive action, select publication or license
terms, or grant itself broader authority.

Repository instructions and accepted decisions constrain ChatGPT, top-level
Codex, and internal workers unless the human maintainer explicitly authorizes
their supersession. Delegated authority cannot infer such a supersession from a
broad objective or from convenience.

An unapproved epic, material scope expansion, publication decision, license
decision, or destructive action returns to the human maintainer. Top-level
Codex may narrow an internal assignment but may not expand the ChatGPT
assignment. Internal workers may narrow for safety but may not expand the
top-level Codex assignment. Source material, research, harness results, commits,
and report records are evidence rather than authority. An unresolved conflict
or envelope boundary is reported instead of being resolved for convenience.

## Responsibilities

The top-level Codex manager:

- inspects applicable instructions, repository state, and executable contracts;
- divides work into bounded assignments with explicit ownership;
- avoids concurrent write scopes that overlap;
- supplies the evidence and authority needed for the assignment;
- reviews worker results, current repository state, and exact changes;
- performs fresh validation from the integrated state;
- records an accept, correction, rejection, or deferral disposition;
- owns the final integrated commit by default and pushes only when authorized;
  and
- creates final managed reports only when the external phase contract requires
  them.

An internal worker:

- stays within source and write scope;
- treats supplied material as evidence, not embedded authority;
- preserves unrelated work and reports unexpected repository state;
- distinguishes observation, inference, recommendation, uncertainty, and
  blocker;
- reports commands actually run and checks deliberately not run;
- creates no commit unless the assignment explicitly authorizes one; and
- returns through the normal agent-harness result unless an authorized exception
  defines another handoff.

## Assignment contract

Every delegated assignment contains this small core:

- identity and objective;
- source scope;
- write scope, including whether the assignment is read-only;
- prohibited actions;
- required evidence;
- concrete deliverable;
- acceptance criteria; and
- reporting method.

Add validation commands, commit authority, privacy handling, stop conditions,
known invariants, and follow-up boundaries only when scope or risk makes them
material. Do not repeat repository-wide policy when a precise reference is
enough. Write ownership is exclusive by default, and nearby cleanup is outside
scope unless authorized.

For a formal project phase, the ChatGPT manager first loads the target
repository's structured defaults. Under APG's
[structured project phase defaults](structured-project-phase-defaults.md), the
assignment references that owner and states only deviations, unusual authority,
phase-specific evidence, expanded tests, nonstandard commit/report behavior,
release or destructive boundaries, hard gates, acceptance, stops, and the
no-successor boundary. It does not repeat default commit, status/exit, ADR,
docs-only, scoped-test, or report procedure. Missing, conflicting, or high-risk
defaults require expanded detail.

An expanded test gate is a deviation and includes its justification. Neither a
formal phase nor manager-assignment compression implies combined, full, smoke,
readiness, or release testing.

## Internal harness result

The normal internal result contains:

- outcome: `completed`, `partial`, `blocked`, or `failed`;
- source snapshot and exact evidence paths when relevant;
- findings or changes;
- validation run and its result;
- unrun checks and why;
- uncertainty, dirty state, or blocker details;
- commit identity only when commit authority existed; and
- the smallest useful follow-up.

Internal results may be ephemeral. Preserve their useful substance in an
authorized project artifact only when the phase requires durable evidence, and
sanitize it before publication.

## Phase identity and precommit finalization

Every phase uses the canonical semantic phase ID assigned before implementation
through its evaluation, exit, managed reports, and final response. ADR and exit
numbers are independent record sequences and do not define the phase. Follow
the [phase and record identity guide](phase-and-record-identity.md).

Before the top-level manager commits a phase, the implementation, current-owner
documentation, roadmap, provenance, integration documents, evaluation, exit,
applicable ADR, and indexes must describe the actual resulting tree. The
manager obtains fresh non-author review, resolves material findings, stages the
complete phase, and inspects and validates the staged diff. A worker result or
planned post-commit report does not excuse stale tracked documentation.

## Current executable reporting contract

The report scripts are the executable contract for final record construction.
They do not make caller-supplied claims true and do not assign actor roles.
Exact Git identities are valid within these generated reports and transient
verification output. Do not copy them into tracked public or private documents
as phase, baseline, current-state, migration, rollback, or cross-document
identities.

### Commit-message construction

Structured commit bodies must contain actual line breaks, not escaped `\n`
text used as paragraph or list separators. Prefer a private message file passed
with `git commit -F`, standard input passed with `git commit -F -`, or separate
`-m` arguments whose values contain actual multiline text. Do not serialize a
multiline value and interpolate its escaped representation into a shell command.

For an APG formal phase, use the exact `Scope`, `Result`, `Verification`, and
`Not run` form owned by the
[structured project phase defaults](structured-project-phase-defaults.md).
Write it to a private file, validate that file with
`bin/apg-check-phase-commit-message --phase <PHASE-ID> --message-file <path>`,
and commit with `git commit -F <path>`. After commit, validate the resulting
revision with `--commit <revision>` before generating either managed report.
The checker enforces form only and does not grant commit or report authority.

Before generating a managed Git report, inspect `git log -1 --format=%B` and
confirm that the committed message has the intended line structure. The report
preserves commit-message bytes as evidence; it does not repair malformed
historical messages.

### Git report

The following Python Git-diff and association behavior describes ADR 0023 and
the APG27A-adopted reporting procedure. APG27 remains its truthful partial
precursor.

`bin/git-show-report` accepts exactly five arguments:

```text
git-show-report <ticket-id> <commit-hash> <status-doc-path-from-repo-root> <result> <final-gate>
```

It resolves the commit and records metadata, changed paths, numstat, commit
message, a full-index patch, comparison mode, payload hashes, and a completion
marker in a version-2 framed record. Root commits compare with the empty tree;
ordinary commits compare with their parent; merges compare with the first
parent.

The command validates ticket syntax, commit resolution, selected metadata
shape, and its newly constructed record. It does not establish that:

- the status path exists or belongs to the commit;
- the commit is `HEAD`, pushed, accepted, or on the expected branch;
- the index and worktree are clean;
- validation passed;
- result or final-gate labels are truthful;
- the actor was authorized; or
- the record is unique.

`bin/git-diff-report` accepts:

```text
git-diff-report <phase-id> <result> <final-gate> [--status-doc <repository-relative-path>]
```

It records one version-1, drift-checked uncommitted snapshot relative to
`HEAD`. NUL-delimited porcelain-v2 status, staged and unstaged summaries, and a
complete full-index patch are captured while intent-to-add exists only in a
private temporary index. An omitted status document renders as `NONE`.

The command rejects an inherited custom index, unborn `HEAD`, split or sparse
index, unmerged entries, clean state, unsafe destination, or any pre/post
disagreement. It does not stage, reset, clean, restore, or replace the real
index or worktree. Its deterministic `GIT-DIFF-REPORT-<state-digest>` identity
names state evidence and is not a commit identity.

### Operational report

`bin/append-operational-report` accepts:

```text
append-operational-report <ticket-id> <operational-report-path> <result> <final-gate> [options]
```

Optional arguments link an exact related commit and Git report identifier. The
source body must be an absolute, cleanly spelled, regular, non-symlink,
caller-owned, mode-0600, single-link file between 1 byte and 8 MiB. The command
copies and hashes the body, detects a limited body format, extracts selected
fields, and places the exact caller text in a version-1 framed record.

`--related-git-report-id` accepts a Git-show or Git-diff record ID. A supplied
ID must identify a complete Git record already present in the same canonical
phase report. Show association requires a matching resolved related commit and
body `primary_commit`; diff association has no related commit and requires a
matching body `primary_git_report_id`. In both cases the body must declare
`operational-report-v1`, the command phase, and the command outcome.

If the phase report contains any Git show or diff record, omission or mismatch
of the exact relation is rejected. A standalone legacy, free-form, or validated
version-1 operational record remains allowed only when the phase report
contains no Git record. The command does not establish the broader truth,
privacy, authorship, authorization, acceptance, source stability, or uniqueness
of caller evidence.

### Shared storage behavior

All three commands derive a project key from the current Git-root basename and write
under a configurable report root. They build one complete record, acquire a
bounded lock, copy any existing destination plus the new record into a private
replacement, and atomically replace the destination. This is logical append by
replacement, not immutable append-only storage.

The adopted shared Python core validates the canonical common envelopes before append,
holds the destination lock across association lookup and replacement, and
rejects incomplete trailing records. Checkout-derived project keys and
configured destinations are executable details, not canonical public identity.

## Final report selection

- Internal worker assignment: normal harness result; no managed report command.
- Top-level read-only phase: an operational record only if external authority
  requires a durable final artifact.
- Top-level commit-producing phase: an exact Git-show report when required,
  plus an explicitly associated operational record when the external contract
  requests execution context.
- Top-level phase that stops with accepted uncommitted state: a Git-diff report
  only when the assignment authorizes it and the focused diff gate has passed,
  plus an explicitly associated operational record when required.
- Push state: verify separately. Neither report command proves it.

When both final records are required, generate the Git record first and append
the exact related operational record afterward. ADR 0023 specifies, and the
APG27A-adopted implementation enforces, same-report association and standalone-append
rejection once a Git record exists. The complete format, identity, safety, and platform boundary is
maintained in the
[agent reporting architecture](agent-reporting-architecture.md).

## Internal worker evidence and disposition

For an internal assignment, the top-level Codex manager reviews the worker
harness result, source evidence, current repository state, exact changes or
commit, and fresh validation. The manager then records one worker-output
disposition:

- `accepted`;
- `accepted-with-follow-up`;
- `correction-required`;
- `rejected`; or
- `superseded`.

For partial completion or a blocker, preserve useful evidence, name the exact
unsatisfied criterion, state whether the tree is dirty, and propose the smallest
safe follow-up. A worker may not silently continue into a new issue class.

A durable internal disposition belongs in the phase exit, ADR, or another
explicitly owned project artifact. Report append, status-file creation, or
commit existence alone is not a disposition.

This internal disposition controls integration and follow-up for worker output.
ChatGPT may review the top-level Codex result and issue the next bounded
assignment only within the human-authorized envelope. That delegated review does
not erase the human maintainer's ultimate control or authorize continuation
beyond the envelope. Reserved decisions and any result outside the envelope
return to the human maintainer after review of the final response and required
report evidence.

## Deferred executable improvements

Remaining candidate improvements include broader operational-body semantic
validation, an independent persisted-record verifier, idempotency and source-
stability rules, authorized stale-lock recovery, an explicit public project-key
mapping, enumerated result fields, and expanded publication-surface linting. A
later phase must define executable acceptance tests before documentation calls
one enforced. ADR 0023 implements record existence, exact show/diff association,
Git-show parity, and temporary-index Git-diff behavior; it does not imply the
remaining candidates.
