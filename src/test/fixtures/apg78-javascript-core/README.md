# APG78 JavaScript Core Fixture

APG-owned, independently authored fixture for the narrow JavaScript
language-profile candidate authored under ADR 0045, corrected through APG79D,
and provisionally integrated with known debt (**Accepted with amendment**).

No target source is copied. No specification prose, algorithm, grammar, table,
example, Test262 test, or engine test is copied. Every file here is new APG
expression.

## What this fixture is

Fourteen cases, `APG78-FX-001` through `APG78-FX-014`, each carrying a concrete
authored construct for one decision scope named by
[`fixture-manifest.json`](fixture-manifest.json).

It is a **maintained fixture**, not an oracle. APG79 reconstructed every
expectation independently before correction. Its candidate-independent
consequence fixture is the semantic test input; this manifest is a projection
and boundary contract.

## What this fixture is not

- Not normative authority. Maintained tests prove bounded structure and exact
  implementation observations; ECMA-262 and fresh human review decide semantics.
- Not a package. There is no lockfile, no `node_modules`, no dependency, no
  generated output, no bundled or minified artifact, and no source map.
- Not an I/O exercise. No file here performs a filesystem, network, process,
  environment, signal, or exit-status operation, and APG78 ran none.

## The one module-mode boundary

`package.json` declares `"type": "module"`. That single declaration is the
fixture's explicit module-mode boundary, and it is deliberate: it is the host
and project evidence that establishes the parse goal for the `.js` files here.

The `.cjs` files are CommonJS only under an exact Node host mapping. CommonJS is
a **host artifact context**, not an ECMAScript Script or Module goal, and its
whole-file owner is `node-commonjs-owner`. The JavaScript profile may inspect
only bounded ordinary-language regions once their wrapper context is known.

## Layout

```text
package.json                       one explicit module-mode boundary
fixture-manifest.json              fourteen cases, canonical JSON
src/evaluation.mjs                 FX-001  evaluation order, short-circuit
src/scope.mjs                      FX-002  hoisting, TDZ, per-iteration bindings
src/coercion.mjs                   FX-003  conversion hints, four equalities
src/objects.mjs                    FX-004  prototypes, descriptors, classes
src/functions.mjs                  FX-005  this, defaults, rest/spread, closure
src/iteration.mjs                  FX-006  iteration protocol, iterator closing
src/errors.mjs                     FX-007  throw/return/finally completions
src/async.mjs                      FX-008  promise reactions, async propagation
src/modules/counter.mjs            FX-009  live-binding exporter
src/modules/consumer.mjs           FX-009  live-binding importer, namespace
src/modules/cycle-a.mjs            FX-009  cyclic TDZ boundary
src/modules/cycle-b.mjs            FX-009  cyclic TDZ boundary
src/modules/top-level-await.mjs    FX-009  async module-evaluation boundary
src/dynamic-import-boundary.mjs    FX-009  dynamic-import host-load boundary
src/module-boundary.mjs            FX-010  .mjs established module goal
src/commonjs-boundary.cjs          FX-011  .cjs host boundary, Node-owned
src/mode-selected.js               FX-012  .js goal established by package type
unbound/mode-neutral.js.txt        FX-012  non-executed unresolved-goal control
unbound/sloppy-script.js.txt       FX-012  exact non-strict Script-goal control
unbound/strict-script.js.txt       FX-012  exact strict Script-goal control
src/checked.js                     FX-013  checked JavaScript, @ts-check
src/cli-core.mjs                   FX-014  effect-free ECMAScript computation
src/cli-node-adapter-boundary.cjs  FX-014  adapter boundary, described only
```

Every manifest path exists, and every file is owned by at least one case.

## The CLI boundary

`cli-core.mjs` receives argument and environment values as ordinary data. It
parses, transforms, and returns a structured result including message data. It
does not call an injected writer. That part may be language-owned.

`cli-node-adapter-boundary.cjs` **describes** the adapter — argument
acquisition, environment reads, stdout and stderr, filesystem, network, signal
handling, exit status — as data. It performs none of it. Every one of those
concerns routes to `node-runtime-owner`.

A correct core result is not a working command.

## Authoring smoke

A bounded scratch-only smoke was run against a *copy* of this tree under one
exact engine, and its exact results are recorded in the APG78 private evaluation
bundle. The smoke proves only that engine's parse and observed evaluation
results under the exact commands, version, mode, and inputs recorded there. It
proves nothing about universal ECMAScript semantics, target runtime selection,
Node.js ownership, browser behavior, or host completion.

## APG79A and APG79B qualification

APG79 selected an explicit exact external-engine prerequisite for the maintained
qualification gate. APG79B routes every semantic and syntax-check subprocess
through one process-spawn site in the invocation owner, which validates the direct regular executable,
version, platform, metadata, and digest immediately before invocation and
revalidates the same bounded facts immediately afterward. Raw stdout and stderr
remain local, a closed output contract validates every material field, and only
a redacted structured observation returns on success. Fresh review found that
failure tracebacks can retain raw values and that four root-scalar contracts
lack same-type wrong-value mutations. No continuous-identity claim is made.
Cases that are normative-only say `not-required`; uninvoked host adapters say
`not-invoked`. Neither state is promoted to target runtime or target invocation
evidence. Lifecycle: `repair-required-after-apg79b`.

## APG79C decision boundary

APG79C human-accepts exactly four retained Medium qualification limitations
for provisional use. It does not change fixture bytes, case meanings, engine
observations, or semantic authority. APG-owned non-sensitive fixture inputs
remain mandatory and all four items block stable maturity. A separate
unaccepted source-identity defect blocks integration, so this fixture and the
candidate remain `repair-required-after-apg79b` and unintegrated.

## APG79D source-role boundary

This fixture still contains only original APG expression. Test262 is
non-normative rights-only evidence: no Test262 body or path inventory is read,
copied, executed, vendored, or used as an oracle. Its historical reviewed pin,
fresh mutable head, and exact licence object are separately recorded. Head
drift alone does not change any fixture purpose or result when rights and the
no-corpus role remain unchanged. APG79D preserves the source-role correction at
a repair checkpoint after terminal review finds the separate report-binding
limitation.

## APG79E integration boundary

APG79E human-accepts that exact fifth Medium supporting qualification
limitation, directly verifies the current APG79B report, and does not claim the
maintained proxy is repaired. With every ordinary product gate green, this
fixture is maintained current evidence for the
`provisionally-integrated-with-known-debt` profile. All five JavaScript debt
items block stable maturity.
