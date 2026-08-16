# APG61 CSS Language-Profile Authoring from Frozen Contract

APG61 is the candidate-only CSS authoring phase after the completed
APG60–APG60I pre-authoring foundation. It starts from the exact APG60I
baseline — the APG60I delivery commit on development `main`, with the frozen
CSS behavior contract, candidate-surface manifest, removal/lifecycle plan,
APG60I phase history, and APG60I handoff verified byte-identical before any
write — and terminates as authored, Proposed, and unintegrated.

## Fresh candidate

APG61 authors one genuinely fresh `css-language-profile` candidate:

- `skills/css-language-profile/SKILL.md` — the candidate leaf;
- `docs/specs/css-language-profile.md` — the normative specification;
- `docs/specs/css-language-profile.contract-map.json` — the traceability map.

The candidate is independently written behavioral synthesis against the
frozen APG60A contract. It is not a restoration of the rejected APG58 pilot
and does not copy the APG58 leaf or specification with patches: its
architecture differs (contract-anchored stable clause markers across a lean
leaf and a full normative specification, governing-state vocabulary, and
candidate lifecycle clauses, none of which the pilot had), and its prose was
authored from the frozen sixty-case contract rather than from pilot text.
APG58/APG59 served as historical evidence and defect input only.

## Policy and boundaries

The growth policy is explicit: nonblank physical lines in ordinary
handwritten standalone stylesheets (`.css`, `.module.css`), Green below 300,
Yellow 300–599, Orange 600–899, Red at 900 or more. The numbers 300/600/900
are policy-selected, not corpus inference, and were not tuned during source
or target review. The candidate separates semantic risk from physical growth
as independent axes, preserves complete-task aggregation and the
projection-overrun stop, keeps the one-count rule and every frozen exclusion
family, preserves legacy Red and bounded-exception behavior, resolves
authority by real grant source, and explicitly routes non-owned concerns —
design, brand, token meaning and value, HTML semantics, browser APIs,
browser-support acceptance, accessibility requirements and outcomes,
host-framework conventions, packaging, build, formatting, deployment,
content — back to their owners.

## Sixty-case traceability

The contract map uses the frozen traceability schema (version 2), contract
revision APG60A, and the frozen contract digest. It contains all sixty cases
`APG60-CSS-001` through `APG60-CSS-060` in order, each row copying the exact
frozen selected owner, sorted required actions, sorted forbidden actions,
and rollback boolean, and binding one or more stable clause markers. All
declared clause markers across the leaf and specification are unique,
substantive, and referenced; no dead or duplicate clause exists. The map
proves navigation and exact frozen-result agreement only — semantic
sufficiency of the clause prose is APG62's independent judgment.

## Proposed ADR 0036

ADR 0036 (`docs/adr/2026/07/0036-css-language-profile-from-frozen-contract.md`)
is Proposed in APG61 and indexed as Proposed. ADR 0031, ADR 0034, and
ADR 0035 remain Rejected. The ADR records the fresh-candidate boundary, the
explicit policy, the owner and non-owner model, the APG61 authoring-only
scope, and the APG62 decision boundary — accept, accept with amendment
within its authority, or reject with candidate-surface removal and preserved
history. APG61 does not decide the ADR.

## Source, rights, and targets

The CSSWG source identities and rights — the `w3c/csswg-drafts` pinned
commit and tree, the license blob, the W3C Software and Document License
with document-specific headers kept distinct, the review date, and refresh
conditions — were recovered from the repository-owned APG52/APG58 records
and reverified. Both read-only targets were verified live at their exact
pinned commits and trees with Git object reads only: the theme tracks
exactly twelve standalone stylesheets with the known legacy Red control at
995 nonblank lines, and the website tracks no standalone CSS. No target was
installed, built, tested, linted, previewed, browsed, deployed, or mutated,
and no source or target expression was copied into any candidate artifact.

## Lifecycle and verification

The terminal state is authored-proposed-unintegrated: the maintained live
lifecycle checker passes for that state on the authored tree and refuses the
pre-authoring, retained, and rejected terminal gates. Every current
narrative owner keeps its exact `absent` candidate-state marker; no catalog
row, projection, route, maturity row, release surface, candidate fixture,
focused candidate test, or test-inventory owner was added; integrated
development counts remain 28/28/28 with 14 stable / 14 provisional maturity;
public and active corrected v0.4.0 are unchanged.

The full APG60I regression suites were run on the clean baseline before
authoring and rerun on the authored tree, with the expected authored-state
differences and all other results unchanged; exact numbers live in the
APG61 managed report and publication-excluded records.

## Boundary

APG61 issues no target command and begins no integration, readiness,
publication, deployment, or activation. APG62 validation is recommended in
the publication-excluded handoff and remains separately authorized; nothing
in this evaluation grants it.
