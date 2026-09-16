# APG142 CSS Trigger Audit: CSS-QD-004

## Metadata and Binding

- **Trigger ID**: `CSS-QD-004`
- **Ledger Item Binding**: `APGR-DEBT-CSS-QD-004`
- **Governing Phase**: `APG142`
- **Target Profile**: `css-language-profile`
- **Severity**: Medium
- **Maturity Blocking Status**: Blocks stable maturity (`blocks_stable: true`); does not block provisional integration (`blocks_provisional: false`)
- **Review Status**: `REVIEWED_WITH_FINDINGS_AMENDED`

## Accepted Baseline

The accepted baseline is the terminal `APG77D` provisional integration (exit 00115; ADR 0044 Accepted with amendment). Under explicit human acceptance recorded in [language-profile-known-debt.json](../../language-profile-known-debt.json) and [language-profile-known-debt.md](../../language-profile-known-debt.md), `CSS-QD-004` was admitted as an accepted qualification-machinery limitation.

- **Baseline Known Consequence**: Distinct obligation IDs with the same owner and decision scope can carry contradictory stop states without compact-validator rejection.
- **Baseline Integration Safety**: No contradictory current route-stop pair is known after human review, routes remain decision-scoped and human-reviewed, and a conflicting pair is always treated as a defect.
- **Baseline Operational Bound**: Inspect owner and decision scope independently of obligation ID whenever route rows change.

## Current Paths Inspected

1. `docs/governance/language-profile-known-debt.json`
2. `docs/governance/language-profile-known-debt.md`
3. `docs/governance/maintenance-triggers.json`
4. `docs/governance/v0-11-closure-ledger.json`
5. `src/test/support/apg_css_evidence_retention_contract.py`
6. `skills/css-language-profile/SKILL.md`
7. `docs/specs/css-language-profile.md`
8. `src/test/support/apg_css_profile_fixture_contract.py`

*(Note: In-harness verification also inspected the private compact v3 decision records through existing test support bindings.)*

## Exact Condition Distinction

- **Canonical Refresh Condition**: `Route owner, decision scope, stop state, or obligation schema changes`
- **Canonical Repair Condition**: `Add the invariant during the next material route-schema revision.`

### Semantic Distinction

The canonical refresh condition specifies the conditions under which the audit triggers: modifications to route ownership, decision scopes, stop states, or the obligation schema. The repair condition schedules the introduction of the validation invariant specifically during the next *material route-schema revision*.

Unrelated repository-level schema developments (such as maintenance trigger schemas, v0.11 closure ledger schemas, or hotspot classification schemas) do not constitute a material revision of the CSS qualification route and obligation schema. Because no material route-schema revision has taken place, and no route attributes have changed, the refresh condition has not fired. The repair condition remains deferred to that future route-schema revision.

## Path and Semantic Comparison

A bounded comparison between the accepted `APG77D` terminal baseline and the current repository state indicates:

1. **Route Owners**: Unchanged. The owner designations across all routed rows (e.g., SVG styling, HTML/DOM integration, build tooling, browser engines) remain identical to the accepted baseline.
2. **Decision Scopes**: Unchanged. Every decision scope declared in compact rows and candidate specifications remains bounded and unchanged.
3. **Stop States**: Unchanged. All stop states remain explicit, non-lowered, and consistent with human review; the audit preserves the accepted human review without claiming a new exhaustive contradiction proof.
4. **Obligation Schema**: Unchanged. The route and obligation schema enforced by `ROUTE_KEYS_V3 = {"decision_scope", "obligation_id", "owner", "stop_state"}` in `apg_css_evidence_retention_contract.py` has not undergone any revision.

## Observed source deltas and baseline sufficiency

The parent compared the APG77D terminal Git source with current source, including
its accepted lifecycle-only fixture and compact source-binding updates. The Lane N,
Lane T2, purpose/target registry, compact v3, retention contract, scenario fixture,
target-first manifest, candidate contract and scenario coverage are byte-identical.
The CSS leaf and specification gained the explicit lifecycle ADR annotation
confirming their already accepted status. The shared fixture contract gained
JavaScript debt support and APG128 resolution machinery; the five CSS debt objects
and CSS source/route/compact semantics are preserved. These are observed changes,
not an assertion that every inspected file is unchanged. Neither annotation nor
JavaScript register machinery revises this debt's named CSS authority.
Exact comparisons are retained in publication-excluded phase evidence. Public
semantic review can follow APG77D and the maintained paths above without private
Git identities. The retained compact/lane artifacts are supporting evidence,
not sufficient source or semantic oracles. No technology qualification was rerun.

## Audit Finding and Trigger State

- **Current Trigger State**: `FALSE` (not triggered)
- **Active Debt Disposition**: Preserved active (`accepted-for-provisional-integration`).

None of route owner, decision scope, stop state, or the CSS obligation schema have been modified. The refresh condition has not fired.

## Evidence Limits

This audit is an internal producer assessment conducted under `APG142` leaf worker authority. Inspection is strictly bounded to repository-tracked paths and current harness contracts. No archive sweeps, external crawls, or machine-local scratch reconstructions were conducted.

## Maturity Consequence

`CSS-QD-004` remains an active debt item. Under accepted project governance, it blocks stable maturity (`blocks_stable: true`) for `css-language-profile` until repaired or separately re-evaluated under human authority. It does not block provisional integration (`blocks_provisional: false`).

## Next Owner and Refresh Procedure

- **Owner**: CSS profile maintainers
- **Refresh Procedure**: Add the invariant during the next material route-schema revision. Refresh only under the named condition and preserve historical evidence.
- **Workaround / Stop Behavior**: Inspect owner and decision scope independently of obligation ID whenever route rows change.

## Review Status

The supplied [independent work review](work-review.md) supports the FALSE finding. The terminal receipt and ledger transition were authored afterward and verified at closeout; no independent review of amended bytes is claimed.

Terminal decision: [individual receipt](decisions/APGR-DEBT-CSS-QD-004.json).
Review and post-review amendment boundary: [supplied work review](work-review.md).
