# APG6 RepoMap Cross-Repository Dogfooding Exit

## Phase identity

- **Phase:** APG6
- **Date:** 2026-07-19
- **Exit sequence:** `00009`
- **Disposition:** Complete — cross-repository dogfooding recorded and review trigger clarified
- **Controlling decision:** ADR 0003, Accepted and unchanged

## Authority and objective

The human maintainer accepted RepoMap DOC-LAYOUT0 as complete and authorized
APG6 to record the resulting design and implementation observations, correct
one review-skill discovery description, align APG5 exit placement with the
introducing committer date, reconcile APG governance, and close the phase with
one private development commit and linked reports.

This public record uses RepoMap's canonical public identity `repo-map`.

APG6 did not reopen RepoMap's archive decision or authorize another RepoMap
phase. RepoMap was not modified.

## Accepted DOC-LAYOUT0 disposition

DOC-LAYOUT0 is accepted without a correction phase. It moved 41 historical
ADRs and 636 historical status records to daily archive layouts while keeping
every historical status record under `docs/status/` and preserving historical
numbers, basenames, H1 titles, semantic roles, and archive ownership. It added
accepted ADR 0042 and status exit 00637.

All 677 introduction-date placements matched the introducing commit's
committer timestamp at its recorded numeric offset with zero ambiguity. Target
collisions and active old-layout references were zero. Review classified 266
retained old-layout occurrences as deliberate historical, remediation, plan,
command or report, or synthetic evidence. Local Markdown links and fragments
passed, independent review accepted the documentation-only result, and the
commit was pushed and verified remote-equal.

No source, test, dependency, runtime, semantic archive classification,
compatibility stub, symlink, or migration framework was added.

## Cross-repository observations

### Read-only migration design

`designing-significant-changes` and
`reviewing-and-verifying-repository-work` were explicitly selected. Planning,
implementation test discipline, systematic debugging, and bounded-worker
assignment composition were material non-triggers because the design was not
yet accepted, implementation was unauthorized, no unexplained defect existed,
and delegation was unnecessary.

Result: `pass-with-follow-up`.

The design preserved historical status ownership rather than reclassifying
records based on exit framing. It supplied current-state inventory,
alternatives, date and counter semantics, migration and rollback boundaries,
non-goals, and maintainer decisions. The follow-up identified that the review
procedure handled the exact design artifact but its frontmatter did not make
bounded repository artifacts readily discoverable.

### Accepted documentation-only implementation

`planning-repository-work` and
`reviewing-and-verifying-repository-work` were explicitly selected. Significant
change design, bounded-worker assignment composition, systematic debugging, and
implementation test discipline were material non-triggers because the design
was accepted, implementation was not delegated, no unexplained failure
occurred, and executable behavior did not change.

Result: `complete`.

The selected skills added useful sequencing, evidence, review, privacy, and
completion discipline without unnecessary branches, tests, reports, or
ceremony. No APG correction resulted from the implementation.

Superpowers was not invoked or followed in either observation.

## Cross-repository discovery

A fresh Codex macOS session rooted in RepoMap discovered all six linked APG
skills after a full application restart. APG6 independently confirmed that the
six linked entries remained readable and resolved to the matching canonical APG
leaves at preflight. The restart requirement is an observed fact for the
sampled environment, not a universal Codex guarantee.

## Review-skill correction

APG6 changed only the frontmatter description of
`reviewing-and-verifying-repository-work` and the matching skill-index summary.
The description now explicitly covers a bounded repository artifact and an
evidence-backed disposition. The existing procedure already governs the exact
artifact or resulting state under review, so its body remains unchanged.

A fresh four-case scenario worker returned `pass` for the positive design-
artifact case, positive resulting-state case, casual-feedback non-trigger, and
stale-or-changing-evidence edge. A separate fresh non-author leaf reviewer
returned `accept`. Neither found a blocker, material finding, minor finding, or
second-correction need. Design ideation remains excluded, unresolved design is
not silently accepted, the description grants no authority, and review
authority and severity remain project-owned parameters.

The review skill remains `provisional`.

## APG5 exit-placement correction

APG5's introducing commit has committer timestamp
`2026-07-18T21:19:51-04:00`. APG6 moved exit `00008` from `2026/07/19/` to
`2026/07/18/`, changed its declared date to `2026-07-18`, added a subsequent-
correction note, and updated every inbound link. APG5's outcome, evidence,
disposition, and sequence number are unchanged.

The status policy now defines exit placement from the introducing commit's
committer timestamp, preserves the local calendar date in that timestamp's
numeric offset, prohibits conversion to UTC or the reviewing machine's
timezone, and keeps assigned exit dates and numbers stable through later moves
or corrections. ADR and exit counters remain independent.

## Evidence artifacts

The public evaluation is
[APG6 RepoMap Cross-Repository Dogfooding](../../../../evaluations/apg6-repomap-cross-repository-dogfooding.md).
Publication-excluded APG6 records preserve exact checkout snapshots, report
identifiers, cross-repository integration details, skill hashes, scenarios, and
review dispositions. Public APG files do not link to that tree and remain
complete without it.

## Maturity and decommission state

APG has now succeeded in its own repository and one additional real project.
RepoMap supplies one external design use for `designing-significant-changes`,
one external implementation use for `planning-repository-work`, and two
external uses for `reviewing-and-verifying-repository-work`. The review skill
also retains its successful APG use.

Every APG skill remains `provisional`; no skill was promoted. No automatic-
selection, comparative, causal, stable-maturity, production-ready, or
decommission-ready claim is made.

Current evidence supports material Superpowers workflow mapping, successful APG
use, successful use in one additional repository, and a preserved Superpowers
source and provenance snapshot. Decommission readiness remains false. Broader
real-use coverage across the six skills, repeated regression evidence, an
explicit uninstall rollback plan, an explicit human decision, actual removal,
and post-decommission smoke validation remain unresolved. Superpowers remains
globally installed, unchanged, and reference-only for APG.

## Independent review

The correction-scenario and non-author leaf reviews passed with no finding.

A fresh read-only reviewer that did not author the correction inspected the
complete staged APG6 diff and resulting state. It independently reproduced the
DOC-LAYOUT0 evidence, historical-preservation boundary, observation separation,
skill decisions, description support, procedure stability, APG5 placement,
date semantics, maturity, decommission state, confidentiality boundary,
repository states, staged scope, record structure, links, counters, skill
frontmatter, and both APG and RepoMap projection integrity.

Disposition: `accept-with-follow-up`.

- Blockers: none.
- Material findings: none.
- Minor findings: none.
- Optional repository findings: none.
- Procedural follow-up: record the review and rerun `git diff --check` and
  `git diff --cached --check` after the review closeout update.

The review initially stopped when the supplied patch fingerprint did not match
raw Git bytes. Investigation established that the supplied value had hashed a
filtered diff rendering rather than the raw patch. No staged artifact had
changed. The reviewer correctly applied the changing-or-stale-artifact stop
boundary, reproduced the stable raw patch identity, and resumed. This was an
evidence-convention correction, not a repository finding.

After the closeout update, `git diff --check` and
`git diff --cached --check` passed. The same reviewer independently reproduced
the updated raw staged-patch identity, confirmed no unstaged diff, verified the
review representation and confidentiality boundary, and returned final
disposition `accept`. No finding or follow-up remains.

## Validation

Preflight confirmed:

- APG development `main` began clean, fetched, and remote-equal at the expected
  APG5 commit;
- the APG source repository began clean, fetched, and remote-equal; it advanced
  externally during validation, remained clean and remote-equal at the newer
  state, and was not modified by APG6;
- RepoMap remained clean, fetched, and remote-equal at the accepted DOC-LAYOUT0
  commit;
- the six RepoMap linked skill entries resolved to the matching APG canonical
  leaves before the APG6 correction;
- APG5's introducing committer timestamp encoded local date `2026-07-18`; and
- accepted `main` assigned next exit sequence `00009` on local date
  `2026-07-19` while the ADR sequence remained through `0003`.

The complete APG documentation, link, confidentiality, sequence, skill,
projection, scope, and Git whitespace gate is rerun from the integrated state
after this exit and the independent review closeout are present. Source tests
and compilation are recorded as:

```text
not run; documentation, evidence, one frontmatter correction, and one exit move only
```

## Limitations

- The RepoMap evidence contains two accepted observations in one additional
  repository, not repeated or controlled comparison.
- Automatic selection was not measured.
- Full-restart discovery is sampled environment evidence only.
- Broader skill-use and repeated regression coverage remain necessary.
- No skill maturity transition, publication, license, or decommission decision
  occurred.

## External review requested

External review is requested to **accept APG6 as Complete — cross-repository
dogfooding recorded and review trigger clarified, retain all six skills at
`provisional`, preserve Superpowers coexistence, and authorize no successor
phase automatically**.

That disposition does not authorize another RepoMap phase, another APG skill,
skill promotion, Superpowers decommissioning, publication, license selection,
taxonomy adoption, or another implementation phase.
