# ADR 0038: Markdown Language Profile Candidate

- Status: Accepted with amendment
- Date: 2026-07-31
- Proposed in: APG65
- Decided in: APG66 on 2026-08-01
- Relates to: ADR 0037 (Accepted with amendment; governing architecture),
  ADR 0031 (Rejected; unchanged), ADR 0034 (Rejected; unchanged),
  ADR 0035 (Rejected; unchanged), ADR 0036 (Rejected; unchanged)

## Context

ADR 0037 is Accepted with amendment and controls the Markdown architecture:
the accepted architecture document, lean validation contract, and corrected
scenario register are the binding inputs for any candidate. ADR 0031, 0034,
0035, and 0036 remain Rejected, and CSS remains absent; nothing here reopens
them. APG64 recorded authoring eligibility as
`authoring-eligible-with-narrowing`, and APG65 is the separately authorized
candidate-only authoring phase.

## Decision

APG65 authors one fresh `markdown-language-profile` candidate consisting of
the candidate leaf (`skills/markdown-language-profile/SKILL.md`), the
[candidate specification](../../../specs/markdown-language-profile.md), and
the compact
[scenario-coverage record](../../../specs/markdown-language-profile-scenario-coverage.md).
The candidate is proposed with these properties:

1. The repository's actual parser and configuration are the effective
   grammar; CommonMark 0.31.2 and GFM 0.29 are bounded references, never a
   synthetic composite dialect, and implementation behavior is version-bound
   `parser-tool-owner` input.
2. Selection, response severity, and receiving-owner routing are three
   separate axes; routing never lowers severity, and a routed stop remains
   stopped until resolved.
3. The candidate contains no numeric whole-file band: structural policy is
   qualitative, decision-scoped, and carried by the fourteen accepted
   signals with their evidence classes and false-positive controls.
4. The thirty-four candidate-semantic scenarios (APG63-MD-001 through
   APG63-MD-034) of the accepted register constrain the candidate; the
   scenario-coverage record maps each to stable clause IDs.
5. The two review-process invariants (APG63-MD-035 and APG63-MD-036)
   constrain the APG66 review, not candidate prose; the candidate neither
   explains nor satisfies them.
6. The scenario-coverage record is navigation-only; the accepted register
   remains the sole behavior oracle.
7. Twenty-four stable clause IDs, each globally unique across leaf and
   specification, carry the candidate's normative behavior.
8. APG65 creates no current integration owner: no catalog row, maturity
   row, projection, capability-map or router entry, project-skill
   ownership, release or public-surface ownership, fixture, focused test,
   or test-inventory owner.

## Alternatives considered

- Defer authoring despite the accepted architecture: rejected — APG64
  recorded authoring eligibility, this phase is separately authorized, and
  deferral would leave the accepted architecture untested by any concrete
  candidate.
- One combined candidate document instead of a leaf/specification split:
  rejected — the operational leaf must stay directly selectable and small
  while the complete normative model (signal table, boundary rules) needs
  room; combining them would breach the authoring-size discipline or force
  omissions.
- A scenario-by-scenario action mirror as the coverage artifact: rejected —
  the accepted contract forbids recreating an exact-action map, and the CSS
  rejection is standing evidence that such maps price bookkeeping as exact
  behavior.
- Numeric whole-file structural bands: rejected — the accepted disposition
  forbids them, and no target evidence supports any value.

## Lifecycle boundary

APG66 completes the candidate lifecycle as retained-provisional. It
independently rebuilt the accepted register oracle, applied one coherent
correction, preserved exact corrected bytes and the actual patch before fresh
review, and integrated every required current owner. The candidate remains
provisional; this decision grants no stability, publication, deployment, or
successor authority.

## APG66 corrected candidate state

APG66's independent initial replay requires one coherent amendment set before
terminal decision. The corrected candidate:

- removes the reversed host-embedding clause from the fenced-code scenario;
- makes the exact fence, raw-HTML, valid-frontmatter, and MDX consequence
  tuples navigable without changing their accepted owners or severities;
- narrows Orange rollback to decisions where rollback is material;
- records the exact move-map and extraction-map rollback for the two
  structural-move scenarios;
- makes `project-policy` the exact document-structure permission receiver for
  raw-HTML policy evasion; and
- links the operational leaf to the normative specification.

Two fresh corrected-state lanes found no new material candidate defect. The
six bullets above are the complete accepted amendment set; no second semantic
correction was applied.

## Consequences

- The retained operational leaf and specification are current development
  guidance at provisional maturity.
- Development becomes 29 canonical skills, 29 catalog rows, and 29 relative
  projections, with 14 stable and 15 provisional rows.
- The general capability map contains 27 routes; the ChatGPT-local map remains
  one route; 28 route edges are checked.
- Exact APG65 authoring history and APG66 corrected-state evidence remain
  preserved. Public and active corrected v0.4.0 remain unchanged.
- No target operation, readiness, publication, deployment, APG67, or
  successor is authorized.
