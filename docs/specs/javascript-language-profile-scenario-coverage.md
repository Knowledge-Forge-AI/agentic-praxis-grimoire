# JavaScript Language-Profile Scenario Coverage

Candidate status: authored in APG78, hardened through APG79B, given human debt
dispositions by APG79C and APG79E, and provisionally integrated in APG79E after
the APG79D Test262 source-role correction and product gates. ADR 0045 is
**Accepted with amendment**; lifecycle is
`provisionally-integrated-with-known-debt`.

Navigation only. This record maps each APG78 candidate scenario to the stable
clause markers that govern it and, where one exists, to the APG-owned fixture
case that carries a concrete authored construct for the same decision scope.

It is **not** a behavior oracle. No row states an expected outcome, an exact
action, a required bookkeeping step, a consequence vector, or a pass/fail
result. A row answers only "where is this decided?" — the
[candidate leaf](../../skills/javascript-language-profile/SKILL.md) and
[specification](javascript-language-profile.md) answer "what does it decide?"

APG79A and APG79B preserve APG79's independent reconstruction. Neither uses
this record, the candidate prose, or the fixture manifest as an oracle.

## Scenario rows

| Scenario | Decision scope | Stable clauses | Fixture case |
| --- | --- | --- | --- |
| `APG78-JS-001` | Ordinary established JavaScript expression and evaluation order | `JS-TRIGGER`, `JS-EVIDENCE`, `JS-SELECTION`, `JS-EVALUATION-ORDER` | `APG78-FX-001` |
| `APG78-JS-002` | `let`/`const` lexical scope and temporal dead zone | `JS-BINDINGS-SCOPE` | `APG78-FX-002` |
| `APG78-JS-003` | `var` and function declaration instantiation and hoisting boundary | `JS-BINDINGS-SCOPE` | `APG78-FX-002` |
| `APG78-JS-004` | Closure capture and mutable binding observation | `JS-BINDINGS-SCOPE`, `JS-FUNCTIONS-THIS` | `APG78-FX-005` |
| `APG78-JS-005` | Script versus Module strictness consequence | `JS-STRICTNESS`, `JS-SOURCE-GOAL` | `APG78-FX-012` |
| `APG78-JS-006` | `ToPrimitive`/`ToNumber`/`ToString` coercion boundary | `JS-COERCION-EQUALITY` | `APG78-FX-003` |
| `APG78-JS-007` | Strict equality, abstract equality, and the `SameValue`/`Object.is` distinction | `JS-COERCION-EQUALITY` | `APG78-FX-003` |
| `APG78-JS-008` | Short-circuit, optional chaining, and nullish-coalescing evaluation boundary | `JS-EVALUATION-ORDER`, `JS-COERCION-EQUALITY` | `APG78-FX-001` |
| `APG78-JS-009` | Property lookup and prototype-chain consequence | `JS-OBJECTS-PROTOTYPES` | `APG78-FX-004` |
| `APG78-JS-010` | Descriptor, assignment, deletion, and strict-mode failure boundary | `JS-PROPERTIES`, `JS-STRICTNESS` | `APG78-FX-004` |
| `APG78-JS-011` | Ordinary-function `this` versus lexical arrow `this` | `JS-FUNCTIONS-THIS` | `APG78-FX-005` |
| `APG78-JS-012` | Parameter, default, rest, and spread evaluation consequence | `JS-FUNCTIONS-THIS`, `JS-EVALUATION-ORDER` | `APG78-FX-005` |
| `APG78-JS-013` | Class construction, `super`, fields, and private-element boundary | `JS-CLASSES` | `APG78-FX-004` |
| `APG78-JS-014` | Destructuring, iteration, and iterator-closing consequence | `JS-ITERATION` | `APG78-FX-006` |
| `APG78-JS-015` | `throw`/`return`/`finally` completion interaction | `JS-ERRORS` | `APG78-FX-007` |
| `APG78-JS-016` | Promise reaction and language-job ordering boundary | `JS-PROMISES-ASYNC`, `JS-HOST-BOUNDARY` | `APG78-FX-008` |
| `APG78-JS-017` | Async/await fulfillment, rejection, and error-propagation boundary | `JS-PROMISES-ASYNC`, `JS-ERRORS` | `APG78-FX-008` |
| `APG78-JS-018` | Established Script versus Module language goal | `JS-SOURCE-GOAL` | `APG78-FX-012` |
| `APG78-JS-019` | ECMAScript module live binding and namespace boundary after linking | `JS-MODULES` | `APG78-FX-009` |
| `APG78-JS-020` | Dynamic import, resolution, loading, and host boundary | `JS-MODULES`, `JS-HOST-BOUNDARY`, `JS-ROUTES` | — |
| `APG78-JS-021` | `.js`/`.mjs`/`.cjs` host classification boundary | `JS-SOURCE-GOAL`, `JS-HOST-BOUNDARY` | `APG78-FX-011` |
| `APG78-JS-022` | Checked JavaScript keeps JavaScript ownership with bounded TypeScript analysis | `JS-CHECKED-JS`, `JS-SELECTION` | `APG78-FX-013` |
| `APG78-JS-023` | JSX, Astro/MDX host, Node API, and browser API non-owner routes | `JS-NONTRIGGER`, `JS-ROUTES` | — |
| `APG78-JS-024` | Unknown goal or host stop, and language success as not-operational-completion | `JS-UNKNOWN-STOP`, `JS-RESPONSE`, `JS-STATIC-HOST-COMPLETION`, `JS-CLI-BOUNDARY` | `APG78-FX-014` |

## Reachability

Twenty-four scenarios `APG78-JS-001` through `APG78-JS-024` appear exactly once
each, in order, with no gap and no repetition.

Twenty-four distinct stable clauses are cited by the rows above. The candidate
defines twenty-five clauses in total. The one clause that no scenario cites is
`JS-STRUCTURE-DEFERRED`, which records the deferred structural disposition. It
deliberately produces no scenario, because a scenario would imply the structural
judgment that the deferral withholds.

Every one of the fourteen fixture cases `APG78-FX-001` through `APG78-FX-014` is
cited by at least one row.

## The fixture-case column

A fixture case appears only where an APG-owned authored construct can carry the
same decision scope. Two scenarios carry a dash, and the reason differs:

- `APG78-JS-020` turns on specifier resolution and module loading. A fixture
  that exercised it would have to perform a real load, which would smuggle host
  and loader behavior into an APG-owned language fixture and would assert
  exactly the result that routes away from this profile.
- `APG78-JS-023` is a routing scenario rather than a construct. Its content is
  which owner receives which adjacent decision; a fixture file would add source
  without adding decision scope.

A dash records a deliberate boundary, not missing coverage. It never means the
scenario is unowned: every scenario maps to at least one clause.

## Target grounding

Two scenarios are grounded in artifacts that actually exist in the freshly
pinned read-only targets rather than only in the fixture:

- `APG78-JS-022` — the one whole-file JavaScript artifact across both targets is
  a checked `.mjs` configuration module. Its whole-file owner is
  `project-configuration-owner`, while JavaScript is `selected` only for the
  bounded ECMAScript decision; checked status transfers neither ownership nor
  proof of checker invocation.
- `APG78-JS-023` — both host-embedded regions across both targets are
  browser-oriented script regions inside Astro host files.

`APG78-JS-018` and `APG78-JS-021` are **not** target-grounded: neither target
contains a `.js` or `.cjs` file. Those scenarios are carried entirely by the
APG-owned fixture, with an explicit unknown control.

## Lifecycle

The candidate is `provisionally-integrated-with-known-debt`. APG78 is the historical
author; APG79 owns its three preserved hardening rounds, APG79A owns its
terminal-proof correction and repair checkpoint, and APG79B owns the separately
authorized five-finding correction. APG79C human-accepts four Medium
qualification limitations and APG79E accepts the exact fifth report-binding
limitation; all block stable maturity. Neither decision accepts semantic,
source, target, owner, release, or rollback debt. APG79D owns the separate
source-role correction and APG79E owns provisional integration under Accepted-
with-amendment ADR 0045.

Catalog, projection, provisional maturity, capability route, project
selection, release, and focused-test owners are current. The maintained APG79B
contract and harness remain supporting qualification evidence under the exact
accepted debt boundary.

Structural policy is deferred, so no scenario, clause, or fixture case in this
record decides a structural or migration question.

This record remains navigation-only coverage. Semantic authority comes from the
candidate specification, primary sources, exact target evidence, and human and
executable review — none of which APG78 supplies in maintained form.

## APG79D source-role boundary

The twenty-four semantic purposes, fourteen fixture purposes, three target
purposes, and their mappings are unchanged. Test262 supplies no scenario
outcome and is not an oracle. The APG79 historical pin, fresh mutable head, and
exact licence object are separate source-evidence roles. Ordinary head drift
with unchanged rights and no corpus use cannot change scenario coverage or
block integration; a rights-role, licence-object, copied-expression, or corpus-
use change stops for fresh review. APG79D preserved the immutable correction at
a repair checkpoint after terminal review found the separate report-binding
limitation.

## APG79E integration boundary

APG79E accepts only that exact Medium supporting qualification limitation,
directly verifies the current APG79B report, and leaves the maintained proxy
unrepaired. All ordinary product gates pass with zero unaccepted findings; ADR
0045 is Accepted with amendment and the candidate is
`provisionally-integrated-with-known-debt` under `JS-QD-001` through
`JS-QD-005`.
