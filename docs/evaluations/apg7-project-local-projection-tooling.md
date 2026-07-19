# APG7 Project-Local Projection Tooling Evaluation

## Objective and decision

APG7 is the first bounded executable-tooling phase. It adds one dependency-free
command for installing, adopting, checking, and removing local APG skill
projections in an opted-in Git worktree without changing tracked target files or
global Codex and Superpowers state.

[ADR 0004](../adr/2026/07/0004-project-local-skill-projection-and-rollback.md)
is Accepted. It keeps canonical skill content under `skills/`, makes strict
Git-local state the sole destructive ownership authority, and rejects force,
copying, automatic enrollment, and global installation.

## Command and implementation

The command surface is:

```text
apg-project-skills list
apg-project-skills install [--repo <path>] [--skill <name> ...]
apg-project-skills adopt [--repo <path>] [--skill <name> ...]
apg-project-skills check [--repo <path>] [--skill <name> ...]
apg-project-skills uninstall [--repo <path>] [--skill <name> ...]
apg-project-skills --help
```

The executable and two non-executable helpers use Python 3.10+ and only the
standard library. The selected implementation makes strict JSON, physical path
resolution, byte-preserving exclusion updates, atomic replacement, subprocess
classification, POSIX advisory locking, and interruption rollback explicit.
Current portability evidence covers macOS, Python 3.10+, Git, symbolic links,
and POSIX file locking. No network or third-party dependency is used.

## Behavioral test result

The repository-owned `unittest` suite invokes the real executable in temporary
Git worktrees with a temporary `HOME`. All 26 required behavioral families
passed:

1. canonical listing;
2. full install;
3. subset install;
4. idempotent reinstall;
5. managed check;
6. exact manual-link adoption;
7. mismatched adoption refusal;
8. tracked-path refusal;
9. file and directory conflict refusal;
10. symlinked-parent refusal;
11. malformed and unsupported state refusal;
12. missing and tampered link detection;
13. retargeted-link uninstall refusal;
14. subset uninstall;
15. complete uninstall;
16. repeated uninstall no-op;
17. unrelated skill-content preservation;
18. unrelated exclude-byte preservation;
19. duplicate and malformed block refusal;
20. paths containing spaces;
21. clean normal Git status after install and adopt;
22. no tracked target changes;
23. no user-level Codex or Superpowers changes;
24. competing mutation lock refusal;
25. restart reminders; and
26. usage and exit statuses.

Result: **26 passed, 0 failed**. The suite uses executable behavior rather than
source-string assertions. It creates no network request, external dependency,
or persistent target repository.

## Subsequent correction: APG7A

APG7 was accepted in substance with one bounded correction. Its idempotent
install and adopt fast paths validated state, exact links, tracked-path absence,
and the syntactic APG exclusion block, then returned `already compliant` before
checking semantic cleanliness in normal Git status.

A disposable reproduction installed or adopted one exact projection, appended
a later Git-local negation rule for that projection, and confirmed the path was
visible as untracked. Repeated install and adopt each returned exit `0` and
`already compliant`, while `check` returned exit `1` against the same state.
The later rule did not corrupt the APG block; it changed Git's effective ignore
result after the block.

APG7A adds one shared idempotent-compliance guard before both success returns.
It applies the existing `managed_status` query to the complete managed set and
fails when any managed projection is visible. The diagnostic directs the
operator to restore the exact local ignore behavior and run check before
retrying. The command does not edit, reorder, delete, or broaden unrelated
ignore rules.

Two focused behavioral families prove install and adopt refusal plus byte-exact
non-mutation of state and exclusion, link identity, tracked content, and an
unrelated sentinel. The clean idempotent controls now also require a subsequent
passing check. Both new tests failed against APG7 production for the intended
exit-`0` reason and pass after correction. The complete corrected suite result
is **28 passed, 0 failed**.

The full disposable lifecycle and a separate recovery control pass. Restoring
the exact pre-negation exclude bytes restores passing check and idempotent
success. A fresh non-author code-and-safety reviewer independently reproduced
the APG7 defect, the intended baseline test failures, and the corrected result,
then returned `accept` with no finding.

APG7A changes no command, option, state schema or version, state path,
exclusion grammar or markers, ownership rule, locking or transaction order,
dependency, portability claim, or global behavior. ADR 0004 remains Accepted.
All six skills remain `provisional`, Superpowers remains installed and
unchanged, and decommission readiness remains false.

## Disposable dogfooding result

One additional disposable worktree with a path containing spaces completed:

```text
list
install all
check
uninstall one skill
check remaining
install the removed skill
check all
uninstall all
check uninstalled state
adopt six compatible manual links
check adopted state
uninstall adopted state
check uninstalled state
```

Every command returned its expected disposition. All links resolved to matching
canonical leaves; state had private permissions; the exact exclusion block hid
only managed projections; adopt preserved link inodes; complete managed removal
deleted tool-owned empty containers; adopted removal preserved manually created
empty containers; normal Git status was clean after every managed mutation; the
target tree object remained unchanged; and temporary user-level Codex and
Superpowers sentinels remained byte-identical.

## APG skill application

- `designing-significant-changes` produced the accepted command, ownership,
  conflict, transaction, interruption, and rollback design before production
  behavior.
- `planning-repository-work` sequenced design, failing evidence, implementation,
  dogfood, durable records, independent review, and the integrated gate.
- `implementing-with-test-discipline` produced a real APG executable observation:
  a focused test failed because the command was absent, the smallest behavior
  made it pass, the full 26-family suite passed, and a structure-only refactor
  was reverified against the same suite.
- `reviewing-and-verifying-repository-work` owns fresh code-and-safety review,
  complete-diff review, and the final claim-specific gate.
- `composing-bounded-worker-assignments` applies only to the separately
  authorized, bounded fresh reviewer assignments.
- `debugging-systematically` was a material non-trigger. Expected initial red
  evidence and immediately identified missing imports during a mechanical split
  did not present an unexplained or multi-hypothesis failure.

Test discipline did not trigger for documentation-only reconciliation after the
executable was green. Design was not repeated after ADR acceptance, and planning
did not authorize work outside APG7.

## Safety, privacy, and rollback findings

- Git resolves the physical non-bare target root; callers cannot redirect the
  canonical APG source. Ambient Git repository-selection variables are removed
  before every query, and strict state records the physical target root when
  linked worktrees share Git metadata.
- Tracked paths, unsafe parents, unmanaged conflicts, invalid state, invalid
  exclusion, and changed owned links fail closed with no force path.
- Adopt proves exact compatible links before ownership state claims them.
- Uninstall preflights the complete selected set and removes only valid
  state-owned links.
- State and exclusion use same-directory atomic replacement; ownership state is
  committed last. Cooperating mutators serialize on the state inode.
- Exact projection paths alone enter Git-local exclusion; unrelated bytes and
  `.agents/skills` content are preserved.
- Runtime absolute paths remain local metadata. Public examples use placeholders,
  and the executable does not access user-level Codex or Superpowers files.
- The tested rollback path is project-local uninstall. It does not remove or
  restore a global plugin.

## RepoMap compatibility orientation

Read-only inspection confirmed that RepoMap's six existing manual link names
still match the APG canonical names, resolve to the matching readable leaves,
and remain compatible with the adopt representation. APG7 did not run install,
adopt, check, or uninstall against that real checkout and does not claim managed
tool success there. RepoMap remained unchanged.

## Decommission-gate effect

The [human decommission and rollback runbook](../superpowers-decommission-runbook.md)
and tested project-projection uninstall now support the rollback-plan
documentation component. Material workflow mapping, APG use, one
additional-repository use, and preservation of the Superpowers source and
provenance snapshot were already supported.

Decommission readiness remains **false**. Broader repeated real-use and
regression evidence, an explicit human decision, actual global disable or
removal, and post-decommission smoke validation remain unresolved. APG7 made no
global plugin action.

## Limitations and disposition

- Evidence covers disposable Git worktrees on the current macOS environment,
  not all operating systems or Git implementations.
- Advisory locks coordinate participating commands, not a hostile same-user
  writer.
- Abrupt process loss may leave conservative disagreement requiring manual
  inspection; the tool intentionally refuses uncertain cleanup.
- Filesystem projection and check success do not establish Codex invocation or
  automatic trigger selection.
- This phase does not evaluate comparative improvement, production readiness,
  stable maturity, public packaging, or a general skill installer.

All six APG skills remain `provisional`. Superpowers remains globally installed
and reference-only for APG. No successor phase is authorized by this evaluation.
