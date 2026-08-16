# Language-Profile Known Debt

The canonical machine-readable owner is
[`language-profile-known-debt.json`](language-profile-known-debt.json). It is a
small current register for explicitly human-accepted language-profile debt, not
a general issue tracker. Duplicate debt IDs are invalid. A profile rollback
deactivates only that profile's current entries without deleting either
historical phase decision.

APG77D exercises the accepted ADR 0042 human-debt authority for exactly five
CSS qualification limitations. It accepts no Critical or High debt and no CSS
semantic, source, target, ownership, runtime, release, or rollback debt.

APG79C separately exercises that authority for four Medium JavaScript
qualification limitations. It accepts zero Critical or High JavaScript debt
and no JavaScript language-semantic, normative-source, target-fact,
whole-file-ownership, host-result, release, or rollback debt. Qualification
machinery remains supporting evidence rather than sufficient semantic or source
authority.

APG79E exercises the same accepted authority for exactly one additional Medium
qualification limitation, `JS-QD-005`. The maintained proxy does not directly
bind the APG79B managed-report bytes. The report is currently directly verified
through EOF at SHA-256
`9b56d503039c2907d371b37b72451b6e0b71cca41aa0cd23c074453229698827`,
including regenerated Git-show records and exact operational associations. The
report remains immutable historical evidence, not semantic, source, target,
runtime, release, or deployment authority. APG79E accepts no Critical or High
JavaScript debt and no semantic, normative-source, target, ownership,
host-result, release, or rollback debt.

| Debt | Severity | Scope | Provisional integration | Stable maturity |
| --- | --- | --- | --- | --- |
| `CSS-QD-001` | Medium | Independent TARGET-007 source guard | Does not block under the explicit APG77D decision | Blocks until repaired or separately re-evaluated |
| `CSS-QD-002` | Medium | Exhaustive disagreement enforcement | Does not block | Blocks |
| `CSS-QD-003` | Medium | Adjudication-source relevance | Does not block | Blocks |
| `CSS-QD-004` | Medium | Conflicting route-stop qualification | Does not block | Blocks |
| `CSS-QD-005` | Low | Empty adjudication arrays | Does not block | Does not block by itself |

| Debt | Severity | Scope | Provisional integration | Stable maturity |
| --- | --- | --- | --- | --- |
| `JS-QD-001` | Medium | supporting CommonJS qualification machinery only | Does not block under the explicit APG79C decision | Blocks until repaired or separately re-evaluated |
| `JS-QD-002` | Medium | JavaScript qualification harness diagnostics only | Does not block under the APG-owned non-sensitive fixture restriction | Blocks |
| `JS-QD-003` | Medium | supporting static process-invocation qualification only | Does not block with mandatory human diff review | Blocks |
| `JS-QD-004` | Medium | supporting output-contract qualification only | Does not block with exact-value and non-author review | Blocks |
| `JS-QD-005` | Medium | supporting Test262 source-role and historical managed-report integrity qualification only | Does not block under the explicit APG79E decision and direct current-report verification | Blocks |

The safe operating boundary is deliberately manual where the supporting
qualification machinery is incomplete: source, lane, adjudication, and route
changes require the exact non-author review named by the register. Compact v3
supports that review but is not sufficient source, disagreement, route,
lifecycle, release, or rollback authority. Current product semantics remain
owned by the candidate specification, maintained semantic scenarios, primary
sources, exact target evidence, and human and executable review.

Each canonical JSON entry records its consequence, safety basis, workaround or
stop, owner, repair and refresh conditions, rollback relevance, target impact,
integration effect, maturity effect, phase, and explicit human acceptance.

The JavaScript operating boundary is exact. CommonJS wrapper execution,
loading, resolution, interop, and runtime completion remain stopped and
Node-owned. The qualification harness accepts only APG-owned non-sensitive
fixtures and public-safe synthetic sentinels; target, user, credential-bearing,
and secret-bearing payloads are prohibited, and failure tracebacks are not
publishable. Every JavaScript qualification-source or process-call change
requires explicit human diff review. Changes to the four root-scalar expected
values require source-backed non-author review. Each JavaScript item blocks
stable JavaScript maturity until repair or separate human re-evaluation.

For `JS-QD-005`, directly locate and parse the canonical APG79B report through
EOF, regenerate both Git-show payloads from the immutable commits, verify both
operational associations, and compare the exact full-file digest before current
integration and after any material source-role, report-generator, report-format,
report-identity, or managed-report change. This explicit workaround does not
repair the maintained false proxy or turn the managed report into a semantic
oracle or product input.
