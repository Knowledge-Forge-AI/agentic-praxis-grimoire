# APG142 CSS Trigger Audit: CSS-QD-003

## Metadata and Binding

- **Trigger ID**: `CSS-QD-003`
- **Ledger Item Binding**: `APGR-DEBT-CSS-QD-003`
- **Governing Phase**: `APG142`
- **Target Profile**: `css-language-profile`
- **Severity**: Medium
- **Maturity Blocking Status**: Blocks stable maturity (`blocks_stable: true`); does not block provisional integration (`blocks_provisional: false`)
- **Review Status**: `REVIEWED_WITH_FINDINGS_AMENDED`

## Accepted Baseline

The accepted baseline is the terminal `APG77D` provisional integration (exit 00115; ADR 0044 Accepted with amendment). Under explicit human acceptance recorded in [language-profile-known-debt.json](../../language-profile-known-debt.json) and [language-profile-known-debt.md](../../language-profile-known-debt.md), `CSS-QD-003` was admitted as an accepted qualification-machinery limitation.

- **Baseline Known Consequence**: Adjudication source IDs are checked for global existence but not complete row-specific relevance.
- **Baseline Integration Safety**: Current adjudication sources received human and source review, no false current binding is known, and source IDs remain supporting evidence rather than an automatic semantic oracle.
- **Baseline Operational Bound**: Require row-specific non-author review for every changed adjudication source.

## Current Paths Inspected

1. `docs/governance/language-profile-known-debt.json`
2. `docs/governance/language-profile-known-debt.md`
3. `docs/governance/maintenance-triggers.json`
4. `docs/governance/v0-11-closure-ledger.json`
5. `src/test/fixtures/apg76-css-target-first/fixture-manifest.json`
6. `src/test/fixtures/apg77-css-language-profile-scenarios.json`
7. `docs/adr/2026/08/0044-css-language-profile-candidate-and-target-first-harness.md`
8. `skills/css-language-profile/SKILL.md`
9. `docs/specs/css-language-profile.md`
10. `src/test/support/apg_css_profile_fixture_contract.py`
11. `src/test/support/apg_css_evidence_retention_contract.py`

*(Note: In-harness verification also inspected the private purpose and target fact registry and compact v3 decision records through existing test support bindings.)*

## Exact Condition Distinction

- **Canonical Refresh Condition**: `Adjudication, source registry, purpose, or authority changes`
- **Canonical Repair Condition**: `Add a bounded row/source relation only when a real maintenance workflow needs machine generation or automatic adjudication.`

### Semantic Distinction

The canonical refresh condition triggers when any of the core semantic governance inputs change: the adjudication decisions, the source registry, the canonical purpose set, or the governing authority documents. The repair condition specifies introducing a formal bounded row/source relation *only when a real maintenance workflow needs machine generation or automatic adjudication*.

The operational need for automated adjudication or machine generation is an independent future maintenance threshold, not a recurring trigger condition. This campaign is a manual source comparison and introduces no machine-generation or automatic-adjudication workflow; it does not survey every possible future workflow. The refresh finding rests on the named source comparison below, independently of that repair condition.

## Public basis and supporting comparison

The publicly inspectable basis is the unchanged APG77D scenario, source-registry
and retention/candidate contracts listed above. Complete private lane, purpose
and compact row comparisons support the producer observation; a public reader
cannot reproduce all of those private row contents from these public owners.
The supplied reviewer corroborated the public path history and semantic boundary.

## Path and Semantic Comparison

A bounded comparison between the accepted `APG77D` terminal baseline and the current repository state indicates:

1. **Adjudications**: Unchanged. The eighteen adjudicated disagreement rows in compact v3 retain identical decision texts, selections, responses, routes, and source authority bindings.
2. **Source Registry**: Unchanged. The 21 W3C CSS modules and 2 auxiliary normative authorities defined in `fixture-manifest.json` are byte-identical and semantically intact since `APG77D`.
3. **Purposes**: Unchanged. All 45 canonical purposes (24 CSS scenarios, 14 fixture cases, and 7 target cases) defined in `purpose-and-target-fact-registry.json` and mirrored in the scenario fixture retain identical statements and scopes.
4. **Governing Authority**: Unchanged. ADR 0044 Accepted with amendment, governing ADR 0042, and the skill candidate authority in `skills/css-language-profile/SKILL.md` remain the stable project standard for static CSS semantics.

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

None of the named refresh condition elements (adjudication, source registry, purpose, or authority) have changed. The refresh condition has not fired.

## Evidence Limits

This audit is an internal producer assessment conducted under `APG142` leaf worker authority. Inspection is strictly bounded to repository-tracked paths and current harness contracts. No archive sweeps, external crawls, or machine-local scratch reconstructions were conducted.

## Maturity Consequence

`CSS-QD-003` remains an active debt item. Under accepted project governance, it blocks stable maturity (`blocks_stable: true`) for `css-language-profile` until repaired or separately re-evaluated under human authority. It does not block provisional integration (`blocks_provisional: false`).

## Next Owner and Refresh Procedure

- **Owner**: CSS profile maintainers
- **Refresh Procedure**: Add a bounded row/source relation only when a real maintenance workflow needs machine generation or automatic adjudication. Refresh only under the named condition and preserve historical evidence.
- **Workaround / Stop Behavior**: Require row-specific non-author review for every changed adjudication source.

## Review Status

The supplied [independent work review](work-review.md) supports the FALSE finding. The terminal receipt and ledger transition were authored afterward and verified at closeout; no independent review of amended bytes is claimed.

Terminal decision: [individual receipt](decisions/APGR-DEBT-CSS-QD-003.json).
Review and post-review amendment boundary: [supplied work review](work-review.md).
