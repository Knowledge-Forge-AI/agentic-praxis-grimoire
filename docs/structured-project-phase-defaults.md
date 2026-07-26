# Structured Project Phase Defaults

## Scope

This document defines APG's project-owned defaults for formal phases and
ordinary non-phase repository work. It is an input to manager assignments, not
independent authority to change, commit, push, publish, destroy, accept, or
continue work. The current human-authorized task, repository instructions, and
accepted decisions remain controlling.

Another repository may replace these conventions with its own. APG exit
framing, commands, report destinations, and release mechanics are not universal
defaults.

## Formal phase default

A formal phase has a canonical semantic phase ID supplied externally. Unless a
more specific instruction says otherwise, one phase normally has:

- one coherent accepted objective and one terminal disposition;
- one commit after current documentation and the phase status or exit are
  final;
- a formal-phase commit message validated before and after commit;
- proportional validation of the changed contract;
- a push and remote-equality check when delivery is authorized;
- one postcommit Git report and one associated operational record; and
- a hard stop before any successor that lacks explicit authority.

Repository instructions and accepted ADRs control throughout. A report,
passing test, commit, push, or worker result is evidence and does not perform
external acceptance.

### Formal-phase commit

Use a concise imperative subject that identifies the semantic phase and its
result:

```text
<PHASE-ID>: <imperative result>
```

The body records material scope, observable result, validation actually run,
and significant checks deliberately not run. It does not copy the assignment,
embed private evidence, or use a future Git object as phase identity.

New APG formal-phase commits use this machine-checkable form:

```text
<PHASE-ID>: <nonempty imperative result>

Scope:
- <material changed ownership or bounded work>

Result:
- <observable terminal result>

Verification:
- <checks actually run and their result>

Not run:
- <material checks deliberately omitted and why, or "none">
```

The exact canonical phase and `: ` begin the subject. One blank line separates
the subject from the body. Each heading occurs once in the displayed order and
has at least one nonempty dash-space entry. The checker does not attempt to
infer grammatical imperative mood. Non-phase commits and another repository's
different convention remain outside this APG-specific check.

Write the message to a private file and validate it before commit:

```text
bin/apg-check-phase-commit-message --phase <PHASE-ID> \
  --message-file <path> [--format text|json]
git commit -F <path>
bin/apg-check-phase-commit-message --phase <PHASE-ID> \
  --commit <revision> [--format text|json]
```

Exit `0` is compliant, `1` is noncompliant, `2` is invalid usage, and `3` is a
message-source or repository error. The postcommit check precedes managed
report generation. Neither check grants commit, push, report, acceptance, or
successor authority.

One commit per phase is the default because it keeps the phase, exit, review,
and managed reports aligned. An explicit release split, an independently
reviewable corrective follow-up, an externally required integration boundary,
or a partial/blocked result that must preserve an uncommitted diff may justify
a different shape. The assignment must state that deviation; convenience alone
does not.

### Status, exit, and operational fallback

Before commit, finalize the project-owned status artifact that truthfully
records:

- phase identity and scope;
- terminal disposition;
- accepted evidence and validation;
- material limitations and deferrals; and
- the exact next authorization boundary.

APG formal phases use an exit record under [`docs/status/`](status/README.md).
When a target repository prohibits a tracked status file or owns a different
status convention, follow that owner. Required manager-facing status then falls
back to the operational report rather than fabricating an APG-style exit.

### Minimal ADR

Create an ADR only for a consequential architecture, ownership, compatibility,
security, lifecycle, or irreversible decision. A minimal ADR contains a
numbered title, status, date, context, decision, alternatives considered,
consequences, and deferred decisions. The independent ADR namespace and
record contract are defined in [`docs/adr/README.md`](adr/README.md).

Do not create an ADR to make routine implementation look formal. Conversely, a
docs-only phase may still require an ADR when the documentation is the accepted
decision.

### Formal docs-only phase

A formal docs-only phase keeps semantic identity, review, exit, commit, push,
and report requirements. Validation is proportional to documentation:

- inspect the complete diff;
- run applicable repository-local validators for affected links, indexes,
  identity, privacy, and generated documentation contracts;
- run whitespace and repository-specific documentation checks; and
- do not run source tests unless the documentation changes an executable
  contract, a repository rule requires them, or the assignment requests them.

Prefer self-contained repository evidence. An observation that depends on an
external service belongs only when the task or repository owns that need. A
source-language compilation or build belongs only when the documentation edit
changes that executable contract; otherwise it is outside proportional
docs-only validation. A claimed executable contract change is not docs-only
merely because its implementation is untouched.

The commit body and exit state which source tests were not run and why. A
docs-only label does not excuse checking references or current-state accuracy.

## Ordinary implementation testing

For an ordinary implementation phase, use scoped unit tests for changed unit
behavior and scoped integration tests only for a changed integration boundary.
Do not run a combined, automated smoke/system, or complete repository suite by
default. The justified expansion conditions and coverage-remediation policy are
defined in [`docs/testing-and-coverage-policy.md`](testing-and-coverage-policy.md).

## Non-phase default

Outside a formal phase:

- create clean atomic commits with descriptive, context-fitting messages when
  commit authority is supplied;
- do not invent a phase ID, exit, status, or ADR ceremony;
- validate only what is needed to preserve the changed contract or what the
  request or repository requires;
- preserve unrelated work and split independent changes when doing so does not
  rewrite or discard user state; and
- stop at the requested result rather than starting an adjacent improvement
  campaign.

A direct request to "commit uncommitted changes" authorizes appropriate atomic
commit or commits for the supplied worktree state. It does not authorize an
unrelated refactor, dependency change, test expansion, cleanup, history rewrite,
or push unless separately stated.

### Non-phase docs-only work

Use the same proportional documentation checks as a formal docs-only phase, but
do not manufacture phase records. A commit body should disclose intentionally
unrun source tests when that fact helps a future reviewer understand the
evidence boundary.

## Manager-assignment compression

The ChatGPT manager first loads the repository's current defaults. When this
document applies, an assignment may reference "the repository's
structured-project defaults" once and omit the ordinary commit, status/exit,
ADR, docs-only, scoped-test, and managed-report procedure.

Compression does not imply a combined, full, smoke, readiness, or release
suite. An assignment names a broader gate only when the approved phase, a
material risk or focused failure, or a project checkpoint justifies it.

The assignment still states:

- deviations and unusual authority;
- phase-specific deliverables and evidence;
- expanded test or review requirements;
- nonstandard commit or report behavior;
- release, destructive, privacy, or migration boundaries;
- gates between separately approved phases;
- observable acceptance and its external owner;
- stop, partial, blocked, and failure behavior; and
- the no-successor boundary.

Expand procedural detail when defaults are absent, incomplete, conflicting, or
inapplicable, or when a release, destructive action, or other high-risk task
needs exact mechanics. Compression must remove repetition, not material scope or
authority.

## Reporting relationship

ADR 0023 specifies that an operational record associated with a Git show or Git
diff record is appended to the same phase report and explicitly names an
existing complete Git record. The partial APG27 candidate enforces that
relationship and APG27A adopts the corrected implementation. The format,
identity, diff-snapshot, and platform contracts are specified in
[`docs/agent-reporting-architecture.md`](agent-reporting-architecture.md).

APG28A adopts `bin/apg-test unit`, `bin/apg-test integration`, and
`bin/apg-test unit-integration` with exact component and union gates. Invoking a
component remains scoped evidence; it does not authorize target-repository
tests or a broader release/readiness phase.

APG29 aligns the planning, implementation, review, and roadmap-assignment
skills with these defaults. Formal phases still finalize current status before
commit; dirty stopped results use authorized Git-diff evidence; committed
results use Git-show evidence; and required operational evidence names the
existing Git record in the same phase report.

APG31 applies these defaults as replacement evidence for formal and non-phase
docs-only work and ordinary Git commit cases. That evidence supports one
independent personal docs-only decommission without changing this procedure.
Two other personal transitions defer because current private routing cannot
satisfy their required non-trigger and stop boundaries within APG31 authority.
The deferrals confirm that replacement evidence does not by itself authorize a
cutover or caller correction.

APG31A supplies the missing caller authority without changing these defaults.
Generalized behavior returns to APG, repository, and RepoMap owners before the
two personal capabilities are narrowed or removed. Exact private behavior
remains publication-excluded rather than becoming a structured-project
default.

## Boundaries

These defaults do not authorize publication, release tagging, destructive
actions, dependency changes, external mutation, successor work, or acceptance.
They do not replace a repository's stricter policy. Missing phase identity,
unclear write scope, conflicting current state, or absent release/destructive
authority remains a stop condition.
