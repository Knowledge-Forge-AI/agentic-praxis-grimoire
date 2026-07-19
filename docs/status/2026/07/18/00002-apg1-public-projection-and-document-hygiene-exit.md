# APG1 Public Projection and Documentation Hygiene Exit

## Phase identity

- **Phase:** APG1
- **Date:** 2026-07-18
- **Exit sequence:** `00002`
- **Disposition:** Complete
- **ADR:**
  [`ADR 0001`](../../../../adr/2026/07/0001-public-projection-private-evidence-and-agent-reporting-boundaries.md),
  Accepted

## Objective

Establish and apply the boundary among private development, future squashed
public projections, publication-excluded evidence, public-safe provenance,
internal worker coordination, final Codex-to-external-authority reporting, and
independent ADR and phase-exit histories.

## Outcome

- Accepted ADR 0001 as the publication, provenance, reporting, record, and
  roadmap-governance decision.
- Established a tracked `private/` boundary that future public projections omit.
- Moved six detailed APG0 research records into that boundary without replacing
  their historical source snapshot or old logical paths.
- Added a private migration ledger that maps historical and reorganized evidence
  and separates ownership, publication eligibility, license, derivation, and
  adoption.
- Removed private repository identities, source topology, snapshots, local
  checkout observations, and report destinations from publishable documents.
- Rewrote public provenance around generalized maintainer evidence, RepoMap,
  Superpowers under MIT, and the public Agent Skills specification.
- Corrected the manager-worker protocol so internal Codex workers return through
  the agent harness and the top-level Codex process owns externally required
  phase reports, while ChatGPT or the human maintainer retains final phase
  acceptance.
- Created independent ADR and exit-record indexes and reserved ADR `0001` and
  exit `00002` without cross-namespace coupling.
- Renamed and sanitized the APG0 record while preserving exit sequence `00001`.
- Replaced the old APG1 skill assumption with APG2 roadmap reconciliation and
  moved later work into unnumbered candidate themes.
- Removed one stale project-specific ignore rule.

No substantive skill, final taxonomy, publication framework, or report-tool
change was implemented.

## Artifact changes

Added:

- ADR and exit-record indexes;
- ADR 0001;
- the publication-excluded area instructions and overview;
- the APG0 source migration and provenance ledger; and
- this APG1 exit record.

Moved or renamed:

- six APG0 research records into publication-excluded development evidence; and
- the APG0 status document to the required `-exit.md` filename and `Exit` title.

Materially rewritten:

- project introduction and repository instructions;
- project model and provenance policy;
- manager-worker protocol;
- roadmap and skill-candidate language; and
- APG0's publishable exit summary.

## Audit findings and resolutions

| Audit | Material finding | Resolution |
| --- | --- | --- |
| Public-surface confidentiality | Publishable files disclosed working repositories, private source projects, private snapshots, and the local checkout-derived report identity. | Replaced with canonical public identities or generalized source families; moved exact evidence; removed the stale ignore entry; left generic executable destination behavior unchanged. |
| Provenance and licensing | APG0's historical no-license observation was valid at its snapshot, while the reorganized evidence now includes the MIT License for unchanged Superpowers material. Ownership, publication status, and license were conflated. | Preserved the historical claim privately, recorded the current MIT resolution and identical-object mapping, split public/private provenance, and kept APG's own license deferred. |
| Roles and report direction | APG0 inferred that read-only internal workers could append managed reports even though the harness already returns their results, and its acceptance layer was ambiguous. | Marked the inference historically superseded, assigned final managed reports to top-level Codex-to-external-authority closeout, limited Codex disposition to internal worker output, and retained external phase acceptance with ChatGPT or the human maintainer. |
| ADR, exit, and roadmap consistency | APG0 did not use the required exit grammar, no ADR index existed, and the roadmap still authorized skill implementation as APG1. | Created independent indexes and counters, normalized APG0, made APG1 the cleanup phase, made APG2 the next decision phase, and left later themes unnumbered. |

## Licensing and provenance result

Superpowers is recorded as external MIT-licensed material. APG1 found no current
APG expression classified as copied or adapted from Superpowers, so no new
notice is required by this phase. RepoMap and generalized internal evidence are
recorded as maintainer-authored without inferring a license grant. APG's own
distribution license remains undecided.

Exact internal repositories, source snapshots, paths, object mappings, and APG0
research remain available to maintainers in tracked publication-excluded
evidence. Public artifacts do not link to or depend on them.

## Record counters

- ADR namespace: `0001`, four digits, unique and independent.
- Exit namespace: APG0 `00001`, APG1 `00002`, five digits, unique and
  independent.
- All phase exit filenames end in `-exit.md` and their titles contain `Exit`.

## Validation

The final documentation, repository-path, and independent-review gate produced
these results:

| Check | Result |
| --- | --- |
| Public-surface confidentiality and identity scan | Passed across every file outside the publication-excluded tree; the only retained 40-character value is the classified public Agent Skills pin. |
| Private snapshot and source-path mapping verification | Passed for all five prefix mappings by identical Git tree objects. |
| Markdown structure, fence balance, and local links | Passed across all 21 tracked Markdown files: 12 publishable and 9 publication-excluded. |
| ADR and exit path, title, sequence, and uniqueness checks | Passed: ADR `0001`; exits `00001` and `00002`; independent namespaces. |
| Public/private dependency check | Passed; no publishable Markdown link targets `private/`. |
| Licensing and provenance consistency | Passed; current Superpowers MIT evidence verified, historical no-license state preserved, and no APG license inferred. |
| Manager-worker protocol reconciliation | Passed against both commands' current help and source; report executables are unchanged. |
| Roadmap phase and candidate-theme check | Passed: numbered phases are APG0–APG2 only, and APG2 explicitly does not implement a skill. |
| Complete staged diff and independent finished-diff review | Passed after one material role-boundary correction and a narrow independent re-review. |
| `git diff --check` | Passed. |
| `git diff --cached --check` | Passed. |
| Source tests and compilation | Not run; documentation and repository-path changes only. |

## Independent review

A fresh read-only reviewer found no confidentiality, licensing, counter,
roadmap, or historical-record defect. It found one material ambiguity: the
protocol assigned internal Codex disposition but did not state explicitly that
ChatGPT or the human maintainer retains acceptance of the top-level phase. The
protocol, ADR, and this exit record now make that boundary explicit. A narrow
read-only re-review accepted the correction before commit. No minor finding was
deferred.

## Deferred decisions and retained risks

- APG's own license and contribution policy remain deferred.
- No public repository, release cadence, tags, or projection notices were
  created or selected.
- Publication filtering, automated public-surface validation, and explicit
  report project-key mapping remain future candidates.
- Two-level provenance creates a documentation-drift risk until tooling is
  justified and implemented.
- Public readers cannot independently reproduce exact publication-excluded
  evidence; maintainers retain that evidence privately.
- The first substantive skill remains unselected.

## Next authorization

APG2 should reconcile the roadmap against APG0 and APG1 evidence, decide whether
`write-manager-work-order` remains the best first substantive-skill candidate,
decide whether publication validation must precede skill development, and
prepare exactly one bounded next-implementation recommendation for external
approval, correction, deferral, or rejection. APG2 does not implement a skill.

## Subsequent authority clarification

APG2 clarified that APG1's phrase “ChatGPT or the human maintainer” incorrectly
combined two authority levels. The human maintainer retains ultimate project,
roadmap, publication, license, and destructive-action authority. ChatGPT reviews
and advances work only within a human-authorized task, phase, or preapproved
roadmap envelope. Top-level Codex and internal workers remain bounded beneath
that delegation. This clarification corrects the actor model without changing
APG1's completed publication-boundary disposition.

## Publication statement

APG1 created or published no public repository. It changed only the private
working project's documentation, tracked evidence organization, and repository
hygiene.
