# APG15 v0.3 Foundation Design Exit

## Disposition

Complete — proposal delivered; external disposition required

## Authority and scope

The human maintainer authorized APG15 to design the v0.3 architecture, promote
the private workflow concept into a public-skill proposal, prefer synthesis
over one-to-one Codex VC migration, design ten language profiles and four
warning levels, classify reusable and personal guidance, and recommend a phased
successor roadmap.

APG15 did not implement a skill, change maturity, migrate active root or private
guidance, replace private integration, modify distribution tooling, create a
release candidate, or perform publication.

## Delivered proposals

- [ADR 0011](../../../../adr/2026/07/0011-v0-3-workflow-synthesis-and-modular-guidance-architecture.md)
  proposes the public router, guidance-synthesis capability, twelve-candidate
  inventory, ownership, migration, private-overlay boundary, and APG16 scope.
- [ADR 0012](../../../../adr/2026/07/0012-language-profile-contract-and-warning-levels.md)
  proposes shared Green, Yellow, Orange, and Red semantics and language-specific
  coverage for Python, Bash, Bats, Go, Ruby, Zsh, ZUnit, Nix, PostgreSQL, and
  SQLite.
- The [APG15 evaluation](../../../../evaluations/apg15-v0-3-foundation-design.md)
  records the evidence basis, ownership matrix, migration strategy, Codex VC
  retention dispositions, risks, alternatives, APG15+ roadmap, and recommended
  APG16 vertical slice.
- Publication-excluded evidence records exact private and local source identity
  without creating a public dependency on it.

Both ADRs remain `Proposed`. Candidate inventory does not establish adoption,
implementation, maturity, or release inclusion.

## Architectural outcome

The recommended v0.3 shape is:

1. one public `agentic-praxis-grimoire-workflow` router that selects but does
   not chain or duplicate APG leaves;
2. one `synthesizing-repository-guidance` candidate that produces owner and
   migration dispositions instead of mirroring source files;
3. ten independently triggerable language or framework profile candidates;
4. one shared warning contract whose levels express response and evidence
   needs rather than permission or maturity;
5. repository-local ownership for exact versions, commands, tests, coverage,
   migrations, deployment, and compatibility; and
6. continued Codex VC ownership for personal preferences, private topology,
   machine operations, installed-tool state, and private repository policy.

## Verification

APG15 used documentation-only verification. `git diff --check` and
`git diff --cached --check` pass on the resulting worktree. No source-code,
skill-library, distribution, release, network mutation, graph refresh, or
language-runtime test was run or required for this design-only change.

## Risks and limitations

- Twelve candidate skills would materially expand discovery and maintenance;
  every addition still requires the accepted new-skill threshold.
- Warning calibration has not been tested against concealed representative
  scenarios.
- Upstream versions and reuse rights must be pinned per implementation phase.
- Framework-versus-language and database-engine overlap remains an empirical
  question for later phases.
- The private router remains the active private integration source; no cutover
  has occurred.
- The full-restart v0.2.0 discovery smoke remains a separate external
  observation.

## External disposition requested

The human maintainer should choose one of:

1. accept ADRs 0011 and 0012 and separately authorize bounded APG16;
2. request a bounded correction to one or both proposals;
3. defer the v0.3 architecture; or
4. reject the proposal.

No option is inferred from this exit. APG16 remains unauthorized until the
required disposition is explicit.

Terminal outcome:

```text
proposal-delivered-apg16-unauthorized
```

## Subsequent external disposition

The maintainer accepted APG15 as `Complete — v0.3 foundation architecture
proposed`, accepted ADR 0011's capability-oriented, synthesis-first
architecture through APG16, and separately authorized APG16. ADR 0012 remains
`Proposed`. This subsequent disposition does not rewrite the historical
terminal outcome above and authorizes no other v0.3 phase automatically.
