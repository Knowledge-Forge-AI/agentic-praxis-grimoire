# APG7 Project-Local Skill Projection and Rollback Tooling Exit

## Phase identity

- **Phase:** APG7
- **Date:** 2026-07-19
- **Exit sequence:** `00010`
- **Disposition:** Complete — project-local projection and rollback tooling validated
- **Controlling decision:** ADR 0004, Accepted

## Authority and objective

The human maintainer accepted APG6 as complete and authorized APG7 to design,
implement, test, document, and dogfood one focused command for local APG skill
projection and one human Superpowers decommission and rollback runbook. The
authority allowed only the APG development repository to change.

APG7 did not authorize or perform global plugin mutation, Superpowers removal,
user-level Codex configuration changes, automatic project enrollment, public
release, licensing, packaging, a registry, a daemon, a generalized harness
adapter, or modification of another real project.

## Accepted design

[ADR 0004](../../../../adr/2026/07/0004-project-local-skill-projection-and-rollback.md)
is Accepted under the current human assignment. It preserves the six canonical
skill directories as the sole content source and defines local symbolic links
under an opted-in Git worktree as the projection representation.

The accepted design makes strict Git-local state the sole authority for
destructive uninstall, limits exclusion to an exact delimited block, refuses
tracked paths and unmanaged conflicts, validates adoption before claiming
ownership, commits ownership state last, serializes cooperating mutations, and
requires explicit inspection instead of force when state, links, or exclusion
disagree.

## Executable and command surface

APG7 adds one executable, `bin/apg-project-skills`, implemented with Python
3.10+ and two non-executable standard-library helpers. It has no third-party,
network, Homebrew, or Nix dependency.

The supported surface is:

```text
apg-project-skills list
apg-project-skills install [--repo <path>] [--skill <name> ...]
apg-project-skills adopt [--repo <path>] [--skill <name> ...]
apg-project-skills check [--repo <path>] [--skill <name> ...]
apg-project-skills uninstall [--repo <path>] [--skill <name> ...]
apg-project-skills --help
```

The tool resolves the actual non-bare target worktree through Git and strips
ambient Git repository-selection variables from its subprocess environment.
Its strict version-1 state records the physical APG root, physical target root,
managed skills, tool-created containers, and exclusion separator ownership.
The state is private Git metadata written by atomic replacement. The exact
Git-local exclusion block lists only managed projection paths.

Install creates only missing links. Adopt claims only exact, compatible,
untracked manual links without replacing them. Check is read-only and verifies
state, canonical leaves, tracked status, links, exclusion, and managed-path
status. Uninstall removes only links proven to be owned by valid state and
preserves unrelated repository content and exclusion bytes. There is no force
path. Mutating success records the observed full-restart precaution without
claiming control of Codex caching.

## Test discipline and result

`implementing-with-test-discipline` was applied before production behavior. The
first focused executable test failed because the command did not exist. The
smallest implementation then made that behavior pass, the complete suite was
made green, and a structure-only helper split was reverified against the same
behavioral contract.

The final repository-owned `unittest` suite contains 26 required behavioral
families. It invokes the real executable in temporary Git worktrees with a
temporary `HOME`; it does not substitute source-string assertions for behavior.

Final result:

```text
Ran 26 tests
OK
```

Python byte compilation, executable help, and Git whitespace checks also pass.
No third-party test framework, dependency, package metadata, lockfile, or test
runner policy changed.

## Disposable dogfooding

A disposable worktree whose path contained spaces completed the required full
lifecycle: list, install all, check, subset uninstall, remaining check, subset
reinstall, all check, complete uninstall, uninstalled check, compatible manual
link adoption, adopted check, adopted uninstall, and final uninstalled check.

Every command returned the expected status. Links resolved to the matching
canonical leaves, private state used mode `0600`, managed mutations left normal
Git status clean, the target tree object remained unchanged, exact exclusion
state was removed after complete uninstall, tool-created empty containers were
removed, manually created empty containers were preserved, adoption preserved
link inodes, and temporary Codex and Superpowers sentinels remained unchanged.
The lifecycle was rerun successfully after all review corrections.

Read-only orientation confirmed that the six existing manual links in
`repo-map` remain readable and match the six APG canonical leaves. No APG
mutating command ran in that repository.

## APG skill decisions

- `designing-significant-changes` produced the command, ownership, conflict,
  transaction, interruption, and rollback design before implementation.
- `planning-repository-work` sequenced design, failing evidence,
  implementation, dogfood, durable records, review, and final validation.
- `implementing-with-test-discipline` produced APG's first real executable
  implementation observation.
- `reviewing-and-verifying-repository-work` governed code-and-safety review,
  complete-diff review, and claim-specific final validation.
- `composing-bounded-worker-assignments` was used only for the independently
  authorized reviewer assignments.
- `debugging-systematically` was a material non-trigger. The initial red test
  was expected, and the mechanical split exposed direct `NameError` tracebacks
  whose missing imports were immediately identified. No unexplained,
  inconsistent, or multi-hypothesis defect occurred.

Superpowers was not invoked or followed.

## Independent review

The fresh non-author code-and-safety reviewer initially found four material
issues: repeat uninstall left an empty first-mutation lock placeholder; ambient
Git variables could redirect the named target; duplicate state members used
ambiguous last-value-wins parsing; and shared linked-worktree metadata did not
bind ownership state to one physical target.

The implementation now removes a newly created empty placeholder only after
inode and size proof, sanitizes the local-repository Git environment for every
subprocess, rejects duplicate JSON members, and strictly records and validates
`target_root`. Focused behavioral regressions cover every correction, including
a linked-worktree sibling that cannot claim or delete the recorded owner's
state or exact compatible link.

The reviewer also identified one minor portability wording issue. Durable
records now state the actual Python 3.10+ prerequisite instead of an
unqualified Python 3 claim. After correction, the reviewer independently ran
all 26 families and reported no remaining code, safety, privacy, or portability
finding.

The fresh complete-diff reviewer independently confirmed the exact 23-path
scope, unchanged read-only repositories, ADR-to-behavior agreement, public
privacy, real behavioral evidence, fail-closed safety cases, absence of scope
expansion, unchanged canonical skills and maturity, false decommission
readiness, correct counters, and fresh validation claims.

Initial disposition was `accept-with-follow-up`, with no blocker, material,
minor, optional, privacy, or safety finding. The only follow-up was to record
the review and rerun staged checks after that record-only update. The same
reviewer then independently confirmed the resulting staged identity, no
unstaged diff, accurate review representation, and both Git whitespace checks,
and returned final disposition `accept`. No finding or follow-up remains.

## Documentation and rollback runbook

The [project-skill projection guide](../../../../project-skill-projection.md)
documents canonical and projected ownership, prerequisites, commands, effects,
conflicts, restart guidance, privacy, checkout movement, manual-link migration,
troubleshooting, rollback, and limitations.

The [Superpowers decommission and rollback runbook](../../../../superpowers-decommission-runbook.md)
defines a human-owned 12-stage future sequence covering readiness, projection
verification, evidence preservation, current plugin state, explicit decision,
supported global controls, restart, representative smoke, failure criteria,
restoration, optional APG projection removal, and post-rollback smoke.

The runbook and tested projection uninstall support only the rollback-plan
documentation component of the decommission gate. They do not satisfy the
human decision, actual global disable or removal, or post-removal smoke.

## Evidence and project reconciliation

The public [APG7 evaluation](../../../../evaluations/apg7-project-local-projection-tooling.md)
records the accepted behavior, verification, safety boundaries, skill uses,
decommission effect, and limitations. Publication-excluded records preserve
exact repository snapshots, threat analysis, test and dogfood details, review
findings, and final report identities. No public file depends on or links to
that private evidence.

The project model, bootstrap, provenance, roadmap, transition map, skill index,
and top-level orientation now consistently record project-local deployment,
the executable implementation observation, tested projection rollback, false
decommission readiness, and unchanged skill maturity.

## Decommission and maturity state

Material workflow mapping, successful APG use, use in one additional real
repository, preservation of the Superpowers source and provenance snapshot,
and rollback-plan documentation are supported gate components.

Decommission readiness remains false. Broader repeated real-use and regression
evidence, an explicit human decision, actual global disable or removal, and
post-decommission smoke remain unresolved. Superpowers remains globally
installed, unchanged, and reference-only for APG. No global Codex or
Superpowers state changed during APG7.

All six APG skills remain `provisional`. APG7 makes no comparative,
automatic-selection, causal, stable-maturity, production-ready, publication,
licensing, or decommission-ready claim.

## Validation

The integrated phase gate covers executable help and byte compilation, the
complete 26-family test suite, the disposable lifecycle dogfood, canonical
skill validation, APG projection validation, read-only `repo-map` orientation,
Markdown headings and fences, local Markdown links, the public-to-private
dependency boundary, confidentiality, ADR and exit counters, file modes,
global-state sentinels, target tree preservation, exact changed paths, and both
unstaged and staged Git whitespace checks.

Report-tool tests are deliberately not run because APG7 does not change a
report executable or shared report helper. Non-macOS portability is not claimed
or tested because the supported dogfood environment is macOS. Global plugin
removal, restoration, and post-decommission smoke are deliberately not run
because they are outside APG7 authority.

## Subsequent correction: APG7A

External disposition accepted APG7's architecture and evidence in substance
but identified one idempotent compliance omission. A later Git-local negation
could make a state-owned projection visible while leaving state, links, and the
APG exclusion block syntactically exact. Repeated install and adopt then
returned `already compliant`, while check rejected the same repository state.

APG7A reproduced both paths in disposable repositories and added two focused
behavioral families that failed against APG7 production for the intended exit-
`0` reason. Both idempotent fast paths now apply the existing semantic managed-
status query before success. Visible managed paths fail closed without changing
state, links, exclusion bytes, tracked content, or unrelated files. Clean
idempotent install and adopt remain successful and each implies a passing
check.

The corrected suite contains 28 passing families. The full disposable lifecycle
and a separate semantic-override recovery control pass. A fresh non-author code
and safety review returned `accept` with no finding. APG7A preserves ADR 0004,
the command and state contract, all six skills at `provisional`, unchanged
Superpowers state, and false decommission readiness. The original APG7 commit
did not contain this correction; APG7A is a forward-only follow-up recorded by
exit `00011`.

## Limitations

- Portability evidence covers the current macOS environment, Python 3.10+,
  Git, symbolic links, and POSIX advisory locking.
- Advisory locks coordinate participating commands, not a hostile same-user
  writer with concurrent filesystem access.
- Abrupt process loss can leave conservative disagreement requiring manual
  inspection; uncertain ownership is never force-cleaned.
- Filesystem projection and successful check do not prove Codex invocation or
  automatic trigger selection.
- Version-1 state permits one managed target per shared linked-worktree Git
  metadata path.
- Broader real-project use and repeated regression evidence remain necessary.

## External review requested

External review is requested to **accept APG7 as Complete — project-local
projection and rollback tooling validated, retain all six skills at
`provisional`, preserve Superpowers coexistence with decommission readiness
false, and authorize no successor phase automatically**.

That disposition does not authorize global plugin mutation, Superpowers
decommissioning, another real-project mutation, another implementation phase,
skill promotion, publication, licensing, packaging, or a successor phase.
