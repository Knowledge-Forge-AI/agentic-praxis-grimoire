# APG142 CSS Trigger Audit: CSS-QD-001

## Metadata and Binding

- **Trigger ID**: `CSS-QD-001`
- **Ledger Item Binding**: `APGR-DEBT-CSS-QD-001`
- **Governing Phase**: `APG142`
- **Target Profile**: `css-language-profile`
- **Severity**: Medium
- **Maturity Blocking Status**: Blocks stable maturity (`blocks_stable: true`); does not block provisional integration (`blocks_provisional: false`)
- **Review Status**: `REVIEWED_WITH_FINDINGS_AMENDED`

## Accepted Baseline

The accepted baseline is the terminal `APG77D` provisional integration (exit 00115; ADR 0044 Accepted with amendment). Under explicit human acceptance recorded in [language-profile-known-debt.json](../../language-profile-known-debt.json) and [language-profile-known-debt.md](../../language-profile-known-debt.md), `CSS-QD-001` was admitted as an accepted qualification-machinery limitation.

- **Baseline Known Consequence**: The maintained validator does not independently prevent a coordinated wrong-source mutation across the current `TARGET-007` scenario and compact row.
- **Baseline Integration Safety**: `TARGET-007`'s current SVG embedded-style and media-query authority was independently reviewed and is correct; no automated authority change is accepted without primary-source and non-author review.
- **Baseline Operational Bound**: Compact v3 source validation serves as supporting qualification evidence only, requiring explicit primary-source and non-author review for any authority change affecting `TARGET-007`.

## Current Paths Inspected

1. `docs/governance/language-profile-known-debt.json`
2. `docs/governance/language-profile-known-debt.md`
3. `docs/governance/maintenance-triggers.json`
4. `docs/governance/v0-11-closure-ledger.json`
5. `src/test/fixtures/apg76-css-target-first/fixture-manifest.json`
6. `src/test/fixtures/apg77-css-language-profile-scenarios.json`
7. `src/test/support/apg_css_profile_fixture_contract.py`
8. `src/test/support/apg_css_profile_candidate_contract.py`
9. `src/test/support/apg_css_evidence_retention_contract.py`
10. `skills/css-language-profile/SKILL.md`
11. `docs/specs/css-language-profile.md`
12. `docs/specs/css-language-profile-scenario-coverage.md`

*(Note: In-harness verification also inspected the private purpose and target fact registry and compact v3 decision records through existing test support bindings.)*

## Exact Condition Distinction

- **Canonical Refresh Condition**: `TARGET-007 purpose, source IDs, target identity, or source registry changes`
- **Canonical Repair Condition**: `Introduce a compact independent source-purpose binding when future TARGET-007 maintenance justifies it.`

### Semantic Distinction

The canonical refresh condition defines the exact recurring triggers that necessitate re-evaluating the debt. In contrast, the repair condition defines the prospective remediation architecture ("Introduce a compact independent source-purpose binding") that is justified only when future `TARGET-007` maintenance arises. A TRUE refresh observation must not be relabelled FALSE merely because the separate repair condition is narrower; the FALSE finding below rests on the named source comparison.

## Path and Semantic Comparison

A bounded comparison between the accepted `APG77D` terminal baseline and current repository state demonstrates:

1. **TARGET-007 Purpose**: Unchanged. `APG77-TARGET-007` remains mapped to the website target embedded SVG style region and media-query evaluation boundary (`embedded-route` selection, `bounded-local-decision` response) across the scenario fixture, coverage specification, and candidate contract.
2. **Source IDs**: Unchanged. The normative source references governing `TARGET-007` (SVG 2 Styling, CSS Syntax 3 and Media Queries 5 in the scenario, with the APG host-boundary contract and fresh target inventory) remain identical. The manifest binds CSS Syntax 3 and Media Queries 5 by shortname and dated URI, and SVG 2 as an auxiliary authority; the relevant rows, rights and normative consequences are preserved.
3. **Target Identity**: Unchanged. The pinned website target repository identity, commit tree, and path inventory remain identical to the accepted baseline.
4. **Source Registry**: Unchanged. The 21 question-specific W3C CSS modules and 2 auxiliary authorities in `fixture-manifest.json` have had zero semantic, URI, date, or structural changes since the `APG77D` terminal integration commit.

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

The named refresh condition has not fired. No change has occurred in the purpose, source IDs, target identity, or source registry governing `TARGET-007`.

## Evidence Limits

This audit is an internal producer assessment prepared under `APG142` leaf worker authority. Evidence inspection is strictly bounded to repository-tracked sources and current harness contracts. No archive sweeps, external crawls, or machine-local scratch reconstructions were performed or required.

## Maturity Consequence

`CSS-QD-001` remains an active debt item. Under accepted project governance, it blocks stable maturity (`blocks_stable: true`) for `css-language-profile` until repaired or separately re-evaluated under human authority. It does not block provisional integration (`blocks_provisional: false`).

## Next Owner and Refresh Procedure

- **Owner**: CSS profile maintainers
- **Refresh Procedure**: Introduce a compact independent source-purpose binding when future `TARGET-007` maintenance justifies it. Refresh only under the named condition and preserve historical evidence.
- **Workaround / Stop Behavior**: Treat compact-v3 source validation as supporting evidence only and require explicit primary-source and non-author review for any `TARGET-007` authority change.

## Review Status

The supplied [independent work review](work-review.md) supports the FALSE finding. The terminal receipt and ledger transition were authored afterward and verified at closeout; no independent review of amended bytes is claimed.

Terminal decision: [individual receipt](decisions/APGR-DEBT-CSS-QD-001.json).
Review and post-review amendment boundary: [supplied work review](work-review.md).
