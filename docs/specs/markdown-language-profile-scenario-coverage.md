# Markdown Language Profile — Scenario Coverage

## Status and scope

- Phase: APG65 authoring, terminally validated in APG66
- Status: current navigation record for the provisional candidate retained
  under Accepted-with-amendment
  [ADR 0038](../adr/2026/07/0038-markdown-language-profile-candidate.md)
- Candidate: [skills/markdown-language-profile/SKILL.md](../../skills/markdown-language-profile/SKILL.md)
  and the [candidate specification](markdown-language-profile.md)

This record is a compact navigation index, not a second behavior oracle. The
accepted APG63 scenario register, as corrected by APG64, controls the
expected owner, selection, response, route, invariant, forbidden outcome,
and rollback for every scenario; none of those fields is restated here.
Mapping a scenario to clause IDs proves navigation — that a reviewer can
find the clauses that should support the scenario — not semantic
sufficiency. APG66 independently established that sufficiency for the one
corrected candidate and preserved the exact pre-review evidence boundary.

The thirty-four candidate-semantic scenarios are APG63-MD-001 through
APG63-MD-034, each listed exactly once below. The two review-process
invariants, APG63-MD-035 and APG63-MD-036, bound the APG66 review and remain
deliberately absent from this record: the candidate neither explains nor
satisfies them.

## Clause inventory

Twenty-four stable clause IDs exist, each exactly once across the candidate
leaf and specification. Leaf clauses: `MARKDOWN-TRIGGER`,
`MARKDOWN-NONTRIGGER`, `MARKDOWN-VALIDATION`, `MARKDOWN-STOP`.
Specification clauses: `MARKDOWN-EFFECTIVE-GRAMMAR`,
`MARKDOWN-UNKNOWN-GRAMMAR`, `MARKDOWN-PARSER-CONFLICT`, `MARKDOWN-OWNER`,
`MARKDOWN-NONOWNERS`, `MARKDOWN-AXES`, `MARKDOWN-BLOCK-INLINE`,
`MARKDOWN-HEADING-STRUCTURE`, `MARKDOWN-EXTENSION-EVIDENCE`,
`MARKDOWN-LINK-REFERENCE`, `MARKDOWN-FENCE`, `MARKDOWN-RAW-HTML`,
`MARKDOWN-FRONTMATTER`, `MARKDOWN-MDX-HOST`, `MARKDOWN-EMBEDDED-ROUTE`,
`MARKDOWN-SEMANTIC-RISK`, `MARKDOWN-STRUCTURAL-POLICY`,
`MARKDOWN-STRUCTURAL-SIGNALS`, `MARKDOWN-GENERATED`,
`MARKDOWN-LEGACY-EXCEPTION`.

## Scenario-to-clause map

| Scenario | Short name | Supporting clause IDs |
| --- | --- | --- |
| APG63-MD-001 | CommonMark ordinary document | `MARKDOWN-TRIGGER`, `MARKDOWN-EFFECTIVE-GRAMMAR`, `MARKDOWN-BLOCK-INLINE` |
| APG63-MD-002 | GFM table under selected extension | `MARKDOWN-EXTENSION-EVIDENCE`, `MARKDOWN-AXES` |
| APG63-MD-003 | GFM task list | `MARKDOWN-EXTENSION-EVIDENCE`, `MARKDOWN-AXES` |
| APG63-MD-004 | Extended autolink selected | `MARKDOWN-EXTENSION-EVIDENCE`, `MARKDOWN-AXES` |
| APG63-MD-005 | Unsupported repository extension | `MARKDOWN-UNKNOWN-GRAMMAR` |
| APG63-MD-006 | Unknown parser | `MARKDOWN-UNKNOWN-GRAMMAR` |
| APG63-MD-007 | Parser conflicts with reference | `MARKDOWN-PARSER-CONFLICT`, `MARKDOWN-STOP` |
| APG63-MD-008 | Deep delimiter ambiguity | `MARKDOWN-BLOCK-INLINE` |
| APG63-MD-009 | Heading hierarchy | `MARKDOWN-HEADING-STRUCTURE` |
| APG63-MD-010 | Reference-link collision | `MARKDOWN-LINK-REFERENCE`, `MARKDOWN-VALIDATION` |
| APG63-MD-011 | Broken destination ownership | `MARKDOWN-LINK-REFERENCE`, `MARKDOWN-NONOWNERS`, `MARKDOWN-SEMANTIC-RISK` |
| APG63-MD-012 | Image syntax and accessibility route | `MARKDOWN-LINK-REFERENCE`, `MARKDOWN-AXES` |
| APG63-MD-013 | Fenced code block | `MARKDOWN-FENCE`, `MARKDOWN-AXES`, `MARKDOWN-NONOWNERS` |
| APG63-MD-014 | Unterminated fence | `MARKDOWN-FENCE`, `MARKDOWN-VALIDATION` |
| APG63-MD-015 | Nested containers | `MARKDOWN-BLOCK-INLINE` |
| APG63-MD-016 | Inline code delimiters | `MARKDOWN-BLOCK-INLINE` |
| APG63-MD-017 | Raw inline HTML | `MARKDOWN-RAW-HTML`, `MARKDOWN-AXES` |
| APG63-MD-018 | Raw HTML policy evasion | `MARKDOWN-RAW-HTML`, `MARKDOWN-STRUCTURAL-SIGNALS`, `MARKDOWN-VALIDATION`, `MARKDOWN-AXES` |
| APG63-MD-019 | Repository-forbidden raw HTML | `MARKDOWN-RAW-HTML`, `MARKDOWN-STOP` |
| APG63-MD-020 | Valid frontmatter boundary | `MARKDOWN-FRONTMATTER`, `MARKDOWN-AXES` |
| APG63-MD-021 | Unknown frontmatter schema | `MARKDOWN-FRONTMATTER`, `MARKDOWN-NONOWNERS` |
| APG63-MD-022 | Frontmatter delimiter corruption | `MARKDOWN-FRONTMATTER`, `MARKDOWN-VALIDATION` |
| APG63-MD-023 | Ordinary .md | `MARKDOWN-TRIGGER`, `MARKDOWN-OWNER` |
| APG63-MD-024 | Markdown-looking .mdx | `MARKDOWN-MDX-HOST`, `MARKDOWN-NONTRIGGER` |
| APG63-MD-025 | MDX expression | `MARKDOWN-MDX-HOST`, `MARKDOWN-AXES` |
| APG63-MD-026 | JSX in MDX | `MARKDOWN-MDX-HOST`, `MARKDOWN-AXES` |
| APG63-MD-027 | Markdown embedded in a host | `MARKDOWN-EMBEDDED-ROUTE` |
| APG63-MD-028 | Long cohesive handwritten changelog | `MARKDOWN-STRUCTURAL-POLICY`, `MARKDOWN-LEGACY-EXCEPTION` |
| APG63-MD-029 | Generated output with hand edit | `MARKDOWN-GENERATED` |
| APG63-MD-030 | Mixed-purpose README | `MARKDOWN-STRUCTURAL-SIGNALS`, `MARKDOWN-STRUCTURAL-POLICY`, `MARKDOWN-VALIDATION` |
| APG63-MD-031 | Oversized tutorial section | `MARKDOWN-STRUCTURAL-SIGNALS`, `MARKDOWN-STRUCTURAL-POLICY`, `MARKDOWN-VALIDATION` |
| APG63-MD-032 | Divergent duplicated norms | `MARKDOWN-SEMANTIC-RISK`, `MARKDOWN-STOP`, `MARKDOWN-STRUCTURAL-SIGNALS` |
| APG63-MD-033 | Reference-table navigation failure | `MARKDOWN-STRUCTURAL-SIGNALS` |
| APG63-MD-034 | Short semantic Red document | `MARKDOWN-SEMANTIC-RISK`, `MARKDOWN-STOP` |

## Reachability

Every one of the twenty-four clause IDs is referenced by at least one row
above; no clause is dead and no row names an unknown clause. Coverage is
34/34 semantic scenarios, each exactly once, with zero process invariants
treated as candidate obligations.

## Limitation

A row here says where to look, not that the destination suffices. The
private APG65 review separately verified that each scenario's mapped clauses
collectively support its register expectations. APG66's independent
corrected-state replay passed 34/34 and is the terminal semantic decision.
