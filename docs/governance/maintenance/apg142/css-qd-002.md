# APG142 CSS Trigger Audit: CSS-QD-002

## Metadata and Binding

- **Trigger ID**: `CSS-QD-002`
- **Ledger Item Binding**: `APGR-DEBT-CSS-QD-002`
- **Governing Phase**: `APG142`
- **Target Profile**: `css-language-profile`
- **Severity**: Medium
- **Maturity Blocking Status**: Blocks stable maturity (`blocks_stable: true`); does not block provisional integration (`blocks_provisional: false`)
- **Review Status**: `REVIEWED_WITH_FINDINGS_AMENDED`

## Accepted Baseline

The accepted baseline is the terminal `APG77D` provisional integration (exit 00115; ADR 0044 Accepted with amendment). Under explicit human acceptance recorded in [language-profile-known-debt.json](../../language-profile-known-debt.json) and [language-profile-known-debt.md](../../language-profile-known-debt.md), `CSS-QD-002` was admitted as an accepted qualification-machinery limitation.

- **Baseline Known Consequence**: The validator does not prove that every Lane N and Lane T2 Selection or Response disagreement has an adjudication.
- **Baseline Integration Safety**: The current compact record retains all eighteen independently reviewed disagreements and any lane or compact-row change requires fresh human comparison.
- **Baseline Operational Bound**: Do not treat adjudication count alone as proof of complete disagreement coverage; require fresh human comparison for lane or compact-row changes.

## Current Paths Inspected

1. `docs/governance/language-profile-known-debt.json`
2. `docs/governance/language-profile-known-debt.md`
3. `docs/governance/maintenance-triggers.json`
4. `docs/governance/v0-11-closure-ledger.json`
5. `skills/css-language-profile/SKILL.md`
6. `docs/specs/css-language-profile.md`
7. `docs/specs/css-language-profile-scenario-coverage.md`
8. `src/test/support/apg_css_profile_fixture_contract.py`
9. `src/test/support/apg_css_evidence_retention_contract.py`
10. `src/test/fixtures/apg77-css-language-profile-scenarios.json`

*(Note: In-harness verification also inspected the private Lane N, Lane T2, and compact v3 decision records through existing test support bindings.)*

## Exact Condition Distinction

- **Canonical Refresh Condition**: `Lane N, Lane T2, compact v3, Selection, or Response changes`
- **Canonical Repair Condition**: `Add an independently frozen disagreement index if the lane mechanism becomes current authority again.`

### Semantic Distinction

The canonical refresh condition identifies the exact inputs whose modification would reopen the trigger: alterations to Lane N, Lane T2, compact decisions v3, or the closed Selection and Response vocabularies. The separate repair condition specifies adding an independently frozen disagreement index if the lane mechanism becomes current authority again.

At present, the dual-lane mechanism is retained historical evidence; current qualification authority rests on the maintained scenario fixture and compact decisions. The condition for the repair ("if the lane mechanism becomes current authority again") is distinct from the refresh condition and has not occurred. That repair observation does not decide the refresh finding; any named lane or compact change still requires fresh human comparison.

## Public basis and supporting comparison

The publicly inspectable basis is the unchanged APG77D scenario, source-registry
and retention/candidate contracts listed above. Complete private lane, purpose
and compact row comparisons support the producer observation; a public reader
cannot reproduce all of those private row contents from these public owners.
The supplied reviewer corroborated the public path history and semantic boundary.

## Path and Semantic Comparison

A bounded comparison between the accepted `APG77D` terminal baseline and the current repository state shows:

1. **Lane N Complete Vectors**: Unchanged. The historical Lane N complete vector record retains the exact 45 rows established in `APG77A` without modification.
2. **Lane T2 Complete Vectors**: Unchanged. The historical Lane T2 complete vector record retains the exact 45 rows established in `APG77B` without modification.
3. **Compact v3 Structured Decisions**: Unchanged. The compact v3 record preserves all eighteen independently reviewed disagreements with identical row bindings and adjudications as finalized in `APG77D`.
4. **Selection Vocabulary and Assignments**: Unchanged. The four-valued closed selection vocabulary (`selected`, `embedded-route`, `route-to-owner`, `non-trigger`) remains strictly enforced across the skill leaf, specification, scenario coverage, and test contracts.
5. **Response Vocabulary and Assignments**: Unchanged. The four-valued closed response vocabulary (`proceed-routine`, `inspect-before-judgment`, `bounded-local-decision`, `stop-and-escalate`) remains strictly preserved across all candidate and evaluation surfaces.

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

None of Lane N, Lane T2, compact decisions v3, Selection, or Response have undergone any modification since the accepted baseline. The refresh condition has not fired.

## Evidence Limits

This audit is an internal producer assessment conducted under `APG142` leaf worker authority. Inspection was strictly bounded to repository-tracked paths and current harness contracts. No archive sweeps, external crawls, or machine-local scratch reconstructions were conducted.

## Maturity Consequence

`CSS-QD-002` remains an active debt item. Under accepted project governance, it blocks stable maturity (`blocks_stable: true`) for `css-language-profile` until repaired or separately re-evaluated under human authority. It does not block provisional integration (`blocks_provisional: false`).

## Next Owner and Refresh Procedure

- **Owner**: CSS profile maintainers
- **Refresh Procedure**: Add an independently frozen disagreement index if the lane mechanism becomes current authority again. Refresh only under the named condition and preserve historical evidence.
- **Workaround / Stop Behavior**: Do not treat adjudication count alone as proof of complete disagreement coverage; require fresh human comparison for lane or compact-row changes.

## Review Status

The supplied [independent work review](work-review.md) supports the FALSE finding. The terminal receipt and ledger transition were authored afterward and verified at closeout; no independent review of amended bytes is claimed.

Terminal decision: [individual receipt](decisions/APGR-DEBT-CSS-QD-002.json).
Review and post-review amendment boundary: [supplied work review](work-review.md).
