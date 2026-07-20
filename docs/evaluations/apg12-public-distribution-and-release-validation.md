# APG12 Public Distribution and Release Validation Evaluation

## Objective and accepted decision

APG12 accepts APG11A as complete, closes the public v0.1.0 omitted-wrapper
failure class, and formalizes two separate local mechanisms: reproducible
public-candidate construction and user-scoped integration from a verified
public release. [ADR 0009](../adr/2026/07/0009-public-distribution-and-reproducible-release-validation.md)
is Accepted. No public repository, active user integration, skill, projection,
or maturity state changes in this phase.

## Current Codex compatibility evidence

Official [Codex skill documentation](https://learn.chatgpt.com/docs/build-skills.md)
was inspected on 2026-07-20. It identifies `.agents/skills` as repository scope
from the working directory through the repository root and
`$HOME/.agents/skills` as user scope, follows supported symbolic-link targets,
does not merge duplicate names, normally detects changes automatically with
restart as a fallback, and recommends plugins for broader distribution. APG12
uses these as current compatibility facts and remains deliberately outside
plugin scope.

## Public projection and release history

All Git-tracked paths are publishable except paths under `private/`. The
candidate must be an exact bijection over every projected raw path, Git type,
mode, blob, and symbolic-link target. The strict
[`public-surface.json`](../../release/public-surface.json) policy adds critical
owner checks for wrappers, helpers, tests, licensing, governance, skills, and
projections; it cannot omit a projected source path or execute a command.

Each release appends one squashed commit with the previous public release as
its sole parent. Explicit version, timestamp, and identity inputs determine the
commit and annotated tag. `apg-public-release` builds and checks only local
disposable candidates and never contacts or pushes to a remote.

Public v0.1.0 contains the project-skill helper modules and documentation but
omits `bin/apg-project-skills`. A focused generated-repository regression
reproduces that surface and requires release checking to fail for the missing
wrapper and exact-tree disagreement.

## Commands and ownership

[`apg-public-release`](../../bin/apg-public-release) is a thin executable over
one Python standard-library helper and Git. It provides `manifest`, `build`,
and `check`. Its checker owns exact surface, history, tag, test, syntax, help,
compile, link, confidentiality, and license-presence facts. Publication
classification, provenance sufficiency, and license interpretation remain
review-owned.

[`apg-user-skills`](../../bin/apg-user-skills) is a separate thin executable
over one Python standard-library helper and Git. It provides `list`, `install`,
`adopt`, `check`, `update`, `rollback`, and `uninstall`. Six direct links and a
strict XDG-compatible state record prove ownership. Exact source identity,
atomic state replacement, a persistent mode-`0600` lock, state-last updates,
and container identity constrain rollback and removal. Repository-scope
duplicates are warnings without inferred precedence.

## Test and dogfood evidence

Implementation began with executable failing-first tests for both absent
commands. The resulting focused surfaces include eight release-helper unit
tests, twenty-two release-command integration tests, eight user-helper unit
tests, and twenty-nine user-command integration tests. They cover committed-object
projection, raw types and modes, unsafe outputs, history and tag metadata,
policy strictness, missing critical owners, no network or push, clean-source
requirements, source-release validation, exact adoption, state permissions,
concurrency, partial-operation recovery, duplicate warnings, update, rollback,
and uninstall ownership.

The complete APG11A and existing regression gates remain part of APG12:
fifteen checker unit tests, fifty-eight checker integration tests, twenty-two
Bats report-tool families, and twenty-eight project-skill integration tests.
Disposable dogfood builds the same prerelease candidate twice from one source,
v0.1.0 base, and fixed metadata, then compares tree, commit, annotated tag, and
manifest. A separate temporary user root exercises v0.1.0 install, duplicate
warning, candidate update, rollback, and uninstall while preserving an unrelated
skill and both repositories.

Exact commands, object identities, manifests, and terminal output remain in
publication-excluded evidence.

## Safety, privacy, licensing, and rollback

The release command rejects dirty repositories, nonordinary index flags,
unsafe or overlapping repository roles and outputs, symlink ancestors, unsafe
committed symlink graphs, unexpected refs, tag or branch collisions, private
paths, extra paths, metadata disagreement, and broken public links. Fixed
code-owned commands and disabled repository-provided fsmonitor/hooks avoid
source command execution. The manifest omits private development commit and
tree identity. Review remains necessary for semantic confidentiality and
licensing.

The user command refuses tracked or unsafe discovery and state roots, Git
worktree overlap, source overlap, conflicts, broken or retargeted links,
invalid state, noncanonical container ownership, mismatched immutable identity,
unrelated release history, and ambiguous cleanup. Sources must be the exact
accepted public v0.1.0 identity or a strict policy-complete descendant. It does
not write Codex configuration or a target repository. The maintainer's active
public-backed integration was observed read-only and remained unchanged.

Before publication, release rollback is disposal of the isolated candidate.
After publication, APG14 owns release rollback using the preserved public
parent. User rollback uses the exact stored previous public identity; uninstall
removes only state-proven links and unchanged tool-created containers.

## APG skill use and independent review

`designing-significant-changes` governed publication history, policy authority,
state ownership, and rollback. `planning-repository-work` organized the
dependent policy, two tools, tests, documentation, dogfood, and evidence.
`implementing-with-test-discipline` governed failing-first behavior and
regression. `debugging-systematically` triggered only for the unexplained
macOS physical-path alias mismatch discovered by an output-containment test.
`reviewing-and-verifying-repository-work` governs integrated acceptance.
`composing-bounded-worker-assignments` bounded the authorized design, threat,
test, and review analyses.

Three fresh final reviewers separately assess public-release safety,
user-scope safety, and the complete diff. Publication-excluded evidence records
their findings and dispositions.

## Limitations and next boundary

The commands trust local APG source and Git, do not sandbox tests, and do not
defend against hostile same-user filesystem races. The user installation
depends on persistent source checkouts. Mechanical validation cannot decide
semantic confidentiality, provenance, license meaning, invocation source, or
automatic discovery behavior.

All six skills and six checked-in projections remain unchanged, and all six
skills remain `provisional`. APG13 is the next separately authorized phase and
owns individual stability dispositions. APG14 alone owns the real v0.2.0
candidate, active integration update, public mutation, tag publication, and
release closeout. Neither successor begins automatically.

## Subsequent correction: APG12A

The original APG12 evidence remains historical: eight release unit tests,
twenty-two release integration tests, eight user unit tests, and twenty-nine
user integration tests passed the implementation that APG12 introduced. That
commit did not include the APG12A corrections.

Subsequent external reproductions established four omissions: release build
and check accepted an unrelated clean base; user source validation accepted an
untagged intermediate commit in later public history; configured validation
could mutate the original base and still pass; and read-only checks could leave
the original candidate dirty or create absent user-state directories and
locks. APG12A adds failing-first coverage for those cases and for missing,
retargeted, merged, truncated, current-tag-mismatched, and subject-mismatched
release histories.

One shared verifier now anchors both tools to exact public v0.1.0 and a strict
tagged single-parent release chain. Dynamic candidate validation runs only in
disposable repository copies and isolated temporary state, while complete Git
fingerprints protect the original roles. User `check` uses an existing
read-only shared lock and creates nothing when state is absent. The v0.1
omitted-wrapper regression and all accepted APG12 lifecycle behavior remain in
force. APG12A changes no skill, projection, maturity, schema, or successor
boundary.
