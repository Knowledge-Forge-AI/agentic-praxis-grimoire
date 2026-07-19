# APG8 RepoMap Managed Projection Adoption Exit

## Phase identity

- **Phase:** APG8
- **Date:** 2026-07-19
- **Exit sequence:** `00012`
- **Disposition:** Complete — RepoMap projections adopted and verified
- **Terminal result:** `managed-adoption-complete`
- **Controlling decision:** ADR 0004, Accepted and unchanged

## Authority and objective

APG8 authorized one bounded real-project deployment: use the corrected
`apg-project-skills` command to adopt RepoMap's six existing compatible manual
APG links into tool-owned Git-local state, verify managed compliance, and record
the result in APG without changing RepoMap's tracked repository.

RepoMap's tracked tree, index, branch, commits, remotes, configuration, runtime,
graph state, database state, and report destinations remained read-only. The
only authorized target writes were the existing local projection paths, one
Git-local ownership state, and one exact managed exclusion block.

## APG7A acceptance

APG7A is externally accepted as **Complete — idempotent install and adopt
compliance corrected**. APG8 used that committed command without modification.
The corrected semantic-status guard, 28-family regression suite, ADR 0004,
state version, exclusion grammar, ownership rules, locking, transaction order,
and rollback architecture remain accepted.

## RepoMap synchronization boundary

The required fetch initially found the authorized target clean at the expected
orientation but one legitimate upstream commit behind. APG8 stopped before
mutation. The maintainer synchronized the worktree and explicitly directed the
phase to ignore later upstream advancement caused by active development.

The refreshed pre-adoption checkpoint was clean and remote-equal. APG8 then
preserved that checked-out branch and commit without another fetch, pull, merge,
reset, checkout, commit, or push. A distinct current checkout visible in the
environment contained no APG links and was not substituted or mutated.

## RepoMap before state

Preflight established:

- an ordinary worktree on `main` with clean normal status;
- no merge, rebase, cherry-pick, revert, bisect, or sequencer operation;
- six existing ordinary symbolic links with the canonical APG names;
- exact raw and resolved targets to current APG leaves;
- readable, matching `SKILL.md` bytes and frontmatter names;
- no tracked projection path or seventh projection entry;
- ordinary pre-existing `.agents` and `.agents/skills` directories;
- no APG ownership state, managed block, or active mutation lock; and
- one user-owned exact manual exclusion entry for each projection.

Before-state evidence froze link inodes and targets, canonical and linked skill
hashes, the tracked tree, index identity, Git-local exclusion bytes, local
metadata modes, APG command hashes, global sentinels, and RepoMap report-state
sentinels.

## Unmanaged pre-check

The explicit read-only check named all six skills. It returned exit `1` and
reported that the requested skills were not locally managed. This was the
expected ADR 0004 disposition for compatible manual links without ownership
state.

## Adoption result

The default all-six adoption command was run once without `--skill`. It returned
exit `0`, reported six managed skills, and emitted the full Codex application
restart reminder.

The command created no link and replaced, retargeted, copied, or removed none.
It created one private version-1 ownership state and added one exact APG block
to the existing Git-local exclude file.

## Managed verification

Both default check and explicit six-name check returned exit `0` and verified
six managed skills.

The state has exactly the accepted keys, current physical canonical and target
roots, six sorted unique names, no created containers, private permissions, and
no remaining active lock. The APG block appears exactly once and agrees with
state.

## Preservation evidence

Fresh before-and-after comparison proved:

- all six link inodes, raw targets, and resolved targets were unchanged;
- canonical and linked skill hashes remained equal;
- pre-existing unrelated exclusion bytes remained byte-identical and
  user-owned outside the APG block;
- no separator repair was required;
- the RepoMap branch, commit, `HEAD^{tree}`, index, and Git configuration were
  unchanged by adoption;
- normal status remained clean and no tracked or cached diff appeared;
- no unexpected local APG metadata path appeared;
- APG command and helper hashes remained unchanged;
- user-level Codex and installed Superpowers sentinels remained unchanged; and
- RepoMap received no managed report.

RepoMap received no tracked change, stage, commit, push, branch change, remote
change, runtime action, graph action, database action, or managed report from
APG8. No uninstall, partial deployment, reinstall, or rollback command was run
against RepoMap.

## APG skill decisions

- `planning-repository-work` applied to the dependent preflight, before-state,
  adoption, verification, evidence, review, and closeout units.
- `reviewing-and-verifying-repository-work` applied to target invariants,
  independent review, complete-diff disposition, and terminal claims.
- `composing-bounded-worker-assignments` applied only to the separately
  authorized fresh read-only reviewer assignment.
- `designing-significant-changes` was a material non-trigger because ADR 0004
  already owns the design.
- `implementing-with-test-discipline` was a material non-trigger because the
  accepted command passed and APG8 changed no command or test.
- `debugging-systematically` was a material non-trigger because the temporary
  synchronization stop had an ordinary explained cause and adoption exposed no
  unexplained failure.

No Superpowers skill was invoked or followed.

## Independent review

One fresh read-only reviewer that did not perform adoption verified target
authority, the complete before-and-after evidence, link preservation, state and
block agreement, user-owned exclusion preservation, tracked-state cleanliness,
privacy, maturity, decommission claims, and the complete APG diff. The reviewer
returned `accept-with-follow-up`, found no substantive or command-defect issue,
and required only bounded reviewer-wording updates plus narrow confirmation
before commit. After those updates, the same reviewer confirmed the unchanged
14-path scope and implementation identity, clean whitespace and privacy checks,
and resolved wording, then returned `accept`.

## Validation

The integrated gate covers:

- the corrected 28-family projection suite;
- executable help and Python byte compilation;
- canonical six-skill and checked-in APG projection integrity;
- exact six-link and frontmatter validation in RepoMap;
- unmanaged pre-check and successful one-time adoption;
- default and explicit managed checks;
- state schema, private mode, and APG block agreement;
- link inode, target, and canonical-hash preservation;
- exact unrelated exclusion-byte preservation;
- RepoMap tracked tree, index, branch, configuration, status, and diff
  preservation;
- absence of a RepoMap commit, push, runtime action, or managed report;
- unchanged user Codex and Superpowers sentinels;
- exact APG changed-path review;
- Markdown headings, fences, local links, public/private boundaries, and
  confidentiality;
- ADR sequence through `0004` and exit sequence through `00012`; and
- both Git whitespace checks.

Report-tool tests are deliberately not run because APG8 changes no report
executable or shared helper.

## Public and private evidence

The public APG8 evaluation records the deployment result through canonical
project identities and public-safe categories. Publication-excluded evidence
retains exact target resolution, commits, paths, link identities, hashes, local
state, exclusion classification, synchronization instruction, and reviewer
disposition.

Public files do not depend on or link into publication-excluded evidence.

## Maturity and decommission state

APG8 supports real-project managed adoption and check while preserving manual
links and a clean tracked repository. Project-local rollout now has disposable
install, adopt, check, uninstall, and recovery evidence plus one real-project
adopt and check cycle.

All six skills remain `provisional`. No automatic invocation, comparative,
causal, stable, production-ready, or publication-ready claim is made.

Superpowers remains globally installed, unchanged, and reference-only for APG.
No global plugin action occurred. Decommission readiness remains false.

Supported gate components now include material workflow mapping, real APG use,
real additional-project use, preserved source and provenance, tested
project-local lifecycle behavior, real-project managed adoption and check, and
the human decommission and rollback runbook.

Broader repeated workflow use across active projects, explicit confirmation of
each dependent project's migration disposition, an explicit human decommission
decision, actual global disable or removal, and post-decommission smoke and
rollback evidence remain unresolved. APG8 does not invent an active-project
inventory.

## Limitations

- Evidence covers one synchronized macOS RepoMap worktree and one all-six
  adoption.
- APG8 does not test partial real-project adoption, uninstall, reinstall,
  rollback, hostile same-user writers, abrupt process loss, or non-Darwin use.
- Local exclusion owners can change effective Git ignore behavior after the
  observation; the corrected command detects but does not repair disagreement.
- Projection compliance establishes discovery layout and ownership, not Codex
  restart completion, discovery, invocation, automatic selection, or benefit.

## Next gate

The next gate is a full Codex application restart and a fresh RepoMap session
discovery smoke. It must verify six-skill discovery, record actual invocation
only when observable, preserve managed check and tracked cleanliness, and retain
Superpowers coexistence. APG8 does not perform or authorize that smoke
automatically.

## External review requested

External review is requested to **accept APG8 as Complete — RepoMap projections
adopted and verified, preserve ADR 0004 and APG7A, retain all six skills at
`provisional`, keep Superpowers installed with decommission readiness false,
and authorize no successor phase automatically**.

That disposition does not authorize another target, uninstall, rollback,
command change, skill promotion, publication, licensing, Superpowers mutation,
fresh-session smoke, or successor phase.
