# CSS Language-Profile Scenario Coverage

Navigation only. This record maps each APG76 candidate scenario to the stable
clause markers that govern it and, where one exists, to the APG-owned fixture
case that carries a concrete authored construct for the same decision scope.

It is **not** a behavior oracle. No row states an expected outcome, an exact
action, a required bookkeeping step, or a pass/fail result. A row answers only
"where is this decided?" — the candidate leaf and
[specification](css-language-profile.md) answer "what does it decide?"

APG77 reconstructs every expectation independently and does not use this
record, the candidate prose, or the fixture manifest as an oracle.

## Scenario rows

| Scenario | Decision scope | Stable clauses | Fixture case |
| --- | --- | --- | --- |
| `APG76-CSS-001` | Ordinary authored CSS region with exact parser and configuration evidence | `CSS-TRIGGER`, `CSS-EVIDENCE`, `CSS-SELECTION` | `APG76-FX-001` |
| `APG76-CSS-002` | Syntax invalidation and its exact recovery boundary under the selected grammar | `CSS-SYNTAX`, `CSS-SOURCE-MODULES` | `APG76-FX-001` |
| `APG76-CSS-003` | Selector-list invalidation and the forgiving-selector boundary | `CSS-SELECTORS` | — |
| `APG76-CSS-004` | Ordinary selector specificity comparison | `CSS-SPECIFICITY` | `APG76-FX-002` |
| `APG76-CSS-005` | Specificity boundary of `:is()`, `:not()`, `:has()`, and `:where()` | `CSS-SPECIFICITY`, `CSS-SELECTORS` | `APG76-FX-002` |
| `APG76-CSS-006` | Origin and importance ordering | `CSS-CASCADE-ORDER` | `APG76-FX-003` |
| `APG76-CSS-007` | Cascade layers and unlayered declarations, normal and important | `CSS-LAYERS` | `APG76-FX-003` |
| `APG76-CSS-008` | Specificity and source-order tie resolution | `CSS-CASCADE-ORDER`, `CSS-SPECIFICITY` | `APG76-FX-002` |
| `APG76-CSS-009` | Inheritance and the CSS-wide keywords | `CSS-INHERITANCE` | `APG76-FX-004` |
| `APG76-CSS-010` | A shorthand resetting longhands the author did not mention | `CSS-SHORTHANDS` | `APG76-FX-005` |
| `APG76-CSS-011` | Custom-property inheritance and substitution scope | `CSS-CUSTOM-PROPERTIES` | `APG76-FX-006` |
| `APG76-CSS-012` | `var()` fallback selection and comma handling | `CSS-SUBSTITUTION` | `APG76-FX-006` |
| `APG76-CSS-013` | Custom-property cycle and invalid-at-computed-value-time result | `CSS-SUBSTITUTION`, `CSS-CUSTOM-PROPERTIES` | `APG76-FX-007` |
| `APG76-CSS-014` | Exact units, `calc()`/`min()`/`max()`/`clamp()` consequence, and the logical/physical property boundary | `CSS-VALUES-UNITS`, `CSS-LOGICAL` | `APG76-FX-010` |
| `APG76-CSS-015` | Target-selected color consequence and `currentColor` resolution | `CSS-COLOR` | `APG76-FX-011` |
| `APG76-CSS-016` | Media-query condition with an uncontrolled environment | `CSS-CONDITIONS`, `CSS-UNKNOWN-STOP` | `APG76-FX-008` |
| `APG76-CSS-017` | Supports-query condition and its exact parser or support evidence | `CSS-CONDITIONS`, `CSS-EVIDENCE` | `APG76-FX-008` |
| `APG76-CSS-018` | Target-selected nesting boundary and resolved specificity | `CSS-NESTING` | `APG76-FX-009` |
| `APG76-CSS-019` | Pseudo-class state routed to DOM and runtime evidence | `CSS-PSEUDO`, `CSS-ROUTES` | — |
| `APG76-CSS-020` | Pseudo-element and generated-content boundary | `CSS-PSEUDO` | — |
| `APG76-CSS-021` | Host embedded-style ownership boundary | `CSS-HOST-EMBEDDED`, `CSS-SELECTION` | `APG76-FX-012` |
| `APG76-CSS-022` | Generated, vendor, and minified artifact boundary | `CSS-PROVENANCE` | `APG76-FX-013` |
| `APG76-CSS-023` | Unknown parser, transform, browser, or configuration stop | `CSS-UNKNOWN-STOP`, `CSS-RESPONSE` | `APG76-FX-014` |
| `APG76-CSS-024` | Static or transform success is not render or runtime completion | `CSS-STATIC-RENDER` | `APG76-FX-014` |

## Reachability

Twenty-four scenarios `APG76-CSS-001` through `APG76-CSS-024` appear exactly
once each, in order, with no gap and no repetition.

Twenty-five distinct stable clauses are cited by the rows above. The candidate
defines twenty-seven clauses in total; the two that no scenario cites are
operational rather than semantic:

- `CSS-NONTRIGGER` governs when the profile declines a question and names the
  receiving owner. It is exercised by every non-CSS handoff rather than by one
  semantic scenario.
- `CSS-STRUCTURE-DEFERRED` records the deferred structural disposition. It
  deliberately produces no scenario, because a scenario would imply a
  structural judgment the disposition withholds.

Every one of the fourteen fixture cases `APG76-FX-001` through `APG76-FX-014`
is cited by at least one row.

## The fixture-case column

A fixture case appears only where an APG-owned authored construct can carry
the same decision scope statically. Three scenarios carry a dash, and the
reason differs in each:

- `APG76-CSS-003` turns on an *invalid* selector. A fixture file containing
  one would need an expected recovery result to be useful, and that result is
  exactly what APG77 must reconstruct independently. It stays prose-only.
- `APG76-CSS-019` turns on document state. Whether a state rule applies is a
  DOM-owner or runtime-owner claim, so no static fixture can carry it without
  smuggling in a document.
- `APG76-CSS-020` turns on whether a pseudo-element generates a box, which
  depends on the originating element and its computed `content`. The static
  half is covered by the specification; the rest routes.

A dash therefore records a deliberate boundary, not missing coverage. It never
means the scenario is unowned: every scenario maps to at least one clause.

## Lifecycle

The candidate is `provisionally-integrated-with-known-debt` after APG77D.
APG76 remains the historical author; APG77 and APG77A through APG77C remain the
hardening and qualification history. ADR 0044 is Accepted with amendment. The
current catalog, projection, provisional maturity row, capability route,
project selection, release owner, and integrated test owner are present.

This record remains navigation-only coverage. Semantic authority comes from
the candidate specification, maintained semantic scenarios, primary sources,
exact target evidence, and human and executable review. Compact v3 is
supporting qualification evidence with the exact limitations recorded in the
known-debt owner; it is not a semantic, source, lifecycle, release, or rollback
oracle. Four accepted Medium qualification limitations block stable maturity.
