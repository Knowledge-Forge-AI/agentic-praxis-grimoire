# APG60B CSS Traceability and Decision Closure

<!-- APG-CANDIDATE-STATE: css-language-profile absent -->

Status: Complete — APG60A remains accepted and the pre-authoring CSS
foundation is hardened forward without candidate authoring.

APG60B starts from exact APG60A and closes five independently reproduced
false-pass classes plus one record defect:

- E1 replaces syntactic traceability rows with schema-v2 rows that bind the
  exact APG60A contract digest and every frozen selected owner, required
  action, forbidden action, and rollback result;
- E2 replaces narrative substrings with exactly one
  `APG-CANDIDATE-STATE` marker per current narrative owner and checks bounded
  paragraph-level contradictions using exact phrases and whole words;
- E3 binds each Python mirror to its declared assignment rather than scanning
  unrelated top-level strings;
- E4 derives actual `AUDITED_*` values through a closed static AST evaluator,
  executes no owner module, and isolates inspected-root imports from
  module-cache state;
- E5 adds the unused, retained-terminal, and rejected-preserved lifecycle for
  the future ADR 0036 and requires the ADR index to agree; and
- R1 records forward that an actual result above the authorized projection,
  not a valid projected band crossing, is the stop condition.

The future contract-map schema is:

```text
schema_version: 2
candidate_id: css-language-profile
contract_revision: APG60A
contract_sha256: exact frozen contract digest
semantic_boundary:
  navigation-only; clause prose requires APG62 semantic validation
cases:
  all APG60-CSS-001 through APG60-CSS-060 in order
```

Each row contains only `case_id`, `clause_ids`, `selected_owner`,
`required_actions`, `forbidden_actions`, and `rollback_required`. Clause
anchors use `<!-- APG-CLAUSE: CSS-... -->`; every referenced anchor must exist
exactly once across the future leaf and specification, and every declared
anchor must be referenced. This proves stable navigation and frozen-contract
agreement, not that candidate prose semantically satisfies the contract.

Current narrative owners contain exactly:

```text
<!-- APG-CANDIDATE-STATE: css-language-profile absent -->
```

Retention must change that marker to `retained-provisional` or
`retained-stable` according to the actual maturity row. APG61 authoring leaves
the integrated state absent. Rejection preserves or restores absent.

The APG60A CSS behavior fixture remains byte-identical at
`1e96535c451dda91dea871679f5a6c9ee7639f4bcd443b4dfbbda4eb28086aed`.
All sixty IDs, expected results, 300/600/900 thresholds, exception authority,
projection-overrun behavior, counting rules, and exclusions are unchanged.

CSS remains absent. ADR 0035 remains Rejected and ADR 0036 remains unused.
Development remains 28 canonical skills, 28 catalog rows, 28 projections, and
fourteen stable plus fourteen provisional skills. Corrected public and active
v0.4.0 remain unchanged. APG61 is only recommended by the
publication-excluded handoff; no successor is authorized.

## Subsequent forward correction

[APG60C](apg60c-css-runtime-and-terminal-lifecycle-closure.md) preserves this
accepted result and corrects newly reproduced final-value, narrative-scope,
historical-preservation, and survivor-integrity false passes forward. It does
not rewrite APG60B or change the frozen sixty-case CSS behavior contract.
