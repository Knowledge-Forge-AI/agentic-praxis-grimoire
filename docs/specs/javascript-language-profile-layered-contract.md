# JavaScript Language-Profile Layered Validation Contract

## Status

- Phase: APG70 terminal rejected state
- Status: Rejected historical corrected state after fresh APG70 review under
  [ADR 0040](../adr/2026/08/0040-javascript-language-profile-core-and-layered-decision-model.md)
- Governing architecture: [JavaScript language-profile core layered architecture](../architecture/javascript-language-profile-core-layered-architecture.md)
- Historical boundary: [ADR 0039](../adr/2026/08/0039-javascript-language-profile-architecture-and-lean-validation.md)
  remains Rejected and supplies no current rule.

This rejected contract was candidate-independent. It would be false if all rows could pass
while an owner, authority, receiving obligation, permission, stop, severity,
source goal, host fact, rollback, or false-completion result remained wrong.
Mechanical shape is useful evidence, never semantic proof.

## Source identity and authority

ECMA-262, 17th edition (ECMAScript 2026), pinned to the exact `es2026`
annual object, is the normative language baseline. The exact
`es2026-errata` delta is non-semantic source-correspondence metadata and never
appears in a row-level normative-authority field. A future consequence-bearing
corrigendum stops for an explicit dual-source disposition before it may control
a result. The moving 2027 draft is refresh evidence only. Test262 is
non-normative conformance/corpus evidence under its verified Ecma BSD-style
license. Exact object and rights identities remain in publication-excluded
evidence; no source, test, or target expression is copied.

## Closed vocabularies

The contract, not a register, owns these exact ordered arrays. Tokens are
case-sensitive. `not-applicable` is explicit. Conceptual owners do not imply an
installed skill.

- **Primary owners (16):** `javascript-language-profile`,
  `typescript-owner`, `jsx-owner`, `node-host-owner`,
  `browser-host-owner`, `intl-owner`, `json-document-owner`,
  `parser-tool-owner`, `build-tool-owner`, `runtime-conformance-owner`,
  `project-design`, `project-policy`, `repository-policy`,
  `security-policy`, `human-instruction`, `generic-lifecycle`.
- **Selection (4):** `selected`, `embedded-route`, `route-to-owner`,
  `non-trigger`.
- **Response (4, low to high):** `proceed-routine`,
  `inspect-before-judgment`, `bounded-local-decision`,
  `stop-and-escalate`.
- **Semantic routes (14):** `javascript-language-profile`,
  `typescript-owner`, `jsx-owner`, `node-host-owner`,
  `browser-host-owner`, `intl-owner`, `json-document-owner`,
  `parser-tool-owner`, `build-tool-owner`, `runtime-conformance-owner`, `project-design`,
  `project-policy`, `security-policy`, `not-applicable`.
- **Structural routes (7):** `project-design`, `typescript-owner`,
  `build-tool-owner`, `node-host-owner`, `browser-host-owner`,
  `runtime-conformance-owner`, `not-applicable`.
- **Structural context-route rules (3):** `route-bound-concrete-host-owner`,
  `route-bound-resolution-owner`, `not-applicable`.
- **Policy routes (6):** `repository-policy`, `project-policy`,
  `security-policy`, `human-instruction`, `project-design`,
  `not-applicable`.
- **Rollback classes (7):** `not-applicable`,
  `discard-uncommitted-analysis`, `revert-bounded-edit`,
  `restore-prior-module-contract`, `restore-prior-data-shape-contract`,
  `regenerate-from-authoritative-source`, `stop-preserve-current-state`.
- **Normative authorities (3):** `ecma262-2026-annual`,
  `ecma402-exact-version`, `not-applicable`.
- **Context authorities (12):** `exact-source-goal-configuration`,
  `exact-browser-version`, `exact-node-version`,
  `exact-non-node-runtime-version`, `exact-runtime-locale-data`,
  `exact-runtime-unicode-data`, `exact-input-region-classification`,
  `exact-parser-transform-output`,
  `exact-embedded-region-boundary`, `exact-host-configuration`,
  `exact-repository-build-evidence`, `not-applicable`.
- **Policy authorities (5):** `repository-policy`, `project-policy`,
  `security-policy`, `human-instruction`, `not-applicable`.
- **Policy decisions (7):** `no-policy`, `permission-granted`,
  `permission-denied`, `acceptance-required`,
  `bounded-exception-granted`, `bounded-exception-overrun`,
  `non-superseding-instruction`.
- **Structural signals (10):** `multiple-runtime-responsibilities`,
  `host-language-responsibility-mixing`,
  `module-resolution-language-mixing`,
  `side-effect-and-pure-transform-mixing`, `implicit-shared-state`,
  `async-control-flow-fanout`, `error-contract-scattering`,
  `data-shape-contract-pressure`, `generated-manual-mixing`,
  `whole-module-review-boundary`.
- **Semantic signals (17):** `source-goal-mismatch`,
  `strict-mode-mismatch`, `runtime-divergence`,
  `coercion-or-equality-ambiguity`, `property-model-surprise`,
  `this-binding-mismatch`, `closure-or-ordering-risk`,
  `iterator-protocol-violation`, `async-propagation-risk`,
  `host-ordering-assumption`, `module-semantics-misunderstanding`,
  `commonjs-esm-boundary`, `regexp-or-unicode-version-mismatch`,
  `proxy-invariant-violation`, `finalization-timing-claim`,
  `shared-memory-ordering-assumption`, `false-runtime-validation`.
- **Evidence classes (3):** `mechanically-observable`,
  `bounded-reviewer-judgment`, `project-input`.
- **Artifact classes (5):** `handwritten-source`, `generated-artifact`,
  `bundled-artifact`, `minified-artifact`, `vendored-artifact`.
- **Source goals (3):** `script-goal`, `module-goal`, `not-applicable`.
- **Concrete hosts (5):** `exact-browser-page-host`,
  `exact-node-esm-host`, `exact-node-commonjs-host`,
  `exact-non-node-runtime-host`, `not-applicable`.
- **Permission (3):** `proceed`, `unresolved`, `stopped`.
- **Kinds (3):** `semantic`, `composition`, `process`.

## Semantic-signal predicates

A signal fires only on its positive predicate; its exclusion is an exact
false-positive control. Presence in text or availability of evidence never
fires a signal.

| Signal | Positive predicate | False-positive control |
| --- | --- | --- |
| `source-goal-mismatch` | established goal differs from the goal assumed by the claim or edit | a goal transition whose old and new consequences are both explicitly analyzed |
| `strict-mode-mismatch` | established strictness differs from the behavior assumed | Script goal alone, which is not implicitly strict but may contain a strict directive |
| `runtime-divergence` | exact runtime evidence contradicts the selected normative consequence | runtime evidence that agrees, or mere evidence availability |
| `coercion-or-equality-ambiguity` | the result depends on unestablished operand types or coercion | exact operands make the result unique |
| `property-model-surprise` | located descriptor/prototype facts contradict the asserted property result | a named descriptor fact whose result is already reflected |
| `this-binding-mismatch` | the edit changes an established receiver or lexical capture | a call site whose receiver/capture is proved equivalent |
| `closure-or-ordering-risk` | a binding or evaluation-order change can alter an established observation | explicit per-iteration/shared binding facts make the result unchanged |
| `iterator-protocol-violation` | a required iterator method/result violates ECMA-262 | absence of optional `return` without a separate cleanup contract |
| `async-propagation-risk` | an async change alters an established caller/importer completion contract | an isolated async result with no external completion dependency |
| `host-ordering-assumption` | a claim derives host task ordering from ECMAScript jobs | a claim confined to language job ordering |
| `module-semantics-misunderstanding` | language linking/evaluation is conflated with host loading/resolution | both sides are explicitly separated and routed |
| `commonjs-esm-boundary` | CommonJS host behavior is treated as ECMA-262 Module semantics or conversely | Script semantics inside an exact Node CommonJS wrapper are separately scoped |
| `regexp-or-unicode-version-mismatch` | exact runtime/Unicode evidence conflicts with the selected annual semantics | missing evidence or agreeing evidence |
| `proxy-invariant-violation` | a trap result violates an essential Proxy invariant | a trap/result combination proved invariant-preserving |
| `finalization-timing-claim` | correctness depends on collection or finalization timing | nondeterminism is observational only and not load-bearing |
| `shared-memory-ordering-assumption` | an ordering claim exceeds the proved Atomics/memory-model relation | worker creation/availability is separately routed to the host |
| `false-runtime-validation` | a concrete runtime claim is presented without exact runtime evidence | a statement expressly narrowed to normative semantics only |

## Semantic register

The corrected register contains exactly APG69-JS-S001 through S033. Every row
has exactly eighteen fields: `ID`, `Kind`, `In`, `ArtifactClass`, `SourceGoal`,
`ConcreteHost`, `PrimaryDecision`, `PrimaryOwner`, `Selection`,
`SemanticResponse`, `SemanticRoute`, `NonOwners`, `SemanticSignals`,
`NormativeAuthorities`, `ContextAuthorities`, `Invariant`, `Forbid`, and
`Rollbacks`.

`NonOwners` excludes an owner only from `PrimaryDecision`; it never erases a
separately listed bounded receiving route. `SemanticRoute` names unresolved
receivers, not authorities. A route also records a distinct obligation by its
row ID and route-array position when composition constructs effective
obligations. `Rollbacks` is an ordered array. A semantic row carries no
structural signal or policy permission.

`script-goal` and `module-goal` are the only language goals. Exact Node
CommonJS is a concrete host mode whose wrapped JavaScript uses Script semantics.
Host-specific consequences require the exact host/version/configuration that
controls them; a pure ownership-boundary route need not invent irrelevant
version evidence. Artifact classification precedes owner and permission
judgment.

## Structural register and intralayer aggregation

The register contains exactly ten signal rows. Each has ten fields: `Signal`,
`EvidenceClass`, `PositiveEvidence`, `DecisionScope`, `DefaultResponse`,
`DefaultRoute`, `ContextRouteRule`, `FalsePositiveControl`, `LegacyBehavior`,
and `Rollbacks`.

For one input, consider signals in contract order. Apply each false-positive
control before activation. The structural response is the maximum active
default. Structural routes are the ordered unique receiver summary in signal
then route order. `route-bound-concrete-host-owner` and
`route-bound-resolution-owner` must resolve to the exact context owner before
completion. Structural obligations preserve every active signal and route
position even when the receiver summary deduplicates. Structural rollbacks are
the ordered unique non-`not-applicable` union in signal order. An inactive
signal contributes nothing; no active signal is canceled by another inactive
one. Line count is descriptive only.

## Policy layer

The accepted generic language-profile authority contract controls policy:
applicable repository and security restrictions are conjunctive; stricter
repository policy controls; an explicit human instruction supersedes only when
its authority and scope expressly cover the decision; and every bounded
exception records authority, scope, rationale, evidence, validation, and
rollback. An exception overrun stops.

`PolicyAuthorities` records deciding authorities. `PolicyRoute` records only
unresolved receiving obligations; an already resolved authority is not a route.
Multiple authorities remain ordered `repository-policy`, `project-policy`,
`security-policy`, `human-instruction`. Policy rollback is preserved beside
semantic and structural rollback. `acceptance-required` means permission is
`unresolved`, never `proceed`.

## Composition and process registers

The corrected composition register contains APG69-JS-C001 through C015. Every
row has exactly twenty-four fields: `ID`, `Kind`, `SemanticScenarioRef`,
`StructuralSignals`, `InactiveStructuralSignals`, `ArtifactClass`,
`PolicyAuthorities`, `PolicyDecision`, `ExpectedSemanticResponse`,
`ExpectedStructuralResponse`, `ExpectedPolicyResponse`, `EffectiveResponse`,
`SemanticRoute`, `StructuralRoute`, `PolicyRoute`, `EffectiveRoutes`,
`EffectiveObligations`, `Permission`, `SemanticRollbacks`,
`StructuralRollbacks`, `PolicyRollbacks`, `EffectiveRollbacks`, `Invariant`,
and `Forbid`.

References are exact IDs/tokens, not prose. Expected semantic results equal the
referenced row. Structural inputs replay active register defaults after
deactivation and context-route resolution. Effective response is the maximum
active response. `EffectiveRoutes` is only an ordered unique receiver summary,
S then T then P. `EffectiveObligations` contains every non-applicable-free
`semantic:<route-position>`, `structural:<signal>:<route-position>`, or
`policy:<route-position>` reference; deduplicating a receiver never discharges
two obligations. Effective rollback is the ordered unique union S then T then
P. Any Red stops. Any unresolved policy decision leaves permission unresolved.
Completion requires every obligation, permission, and rollback to be resolved.

The process register remains exactly P001 and P002 with five fields: `ID`,
`Kind`, `ProcessOwner`, `Invariant`, `Forbid`. These lifecycle gates stay
outside candidate prose and dominate any lower-layer appearance of completion.

## Exact control coverage

C001-C008 preserve the original severity, route, false-positive, and generated
artifact purposes in corrected typed form. C009 tests two active structural
signals. C010 tests one false-positive-deactivated signal beside an active one.
C011 tests simultaneous repository and security authorities. C012 tests a
non-superseding human instruction. C013 tests a bounded authorized exception
and its exact scope. C014 tests two distinct layer obligations to the same
receiver. C015 tests bounded-exception overrun. The semantic additions S025-S033 cover TypeScript/TSX and JSX
non-triggers, embedded regions, parser/emitted/runtime separation, dynamic-code
security routing, and generated/bundled/minified/vendored artifact classification.

## Severity and one-correction discipline

Green is routine, Yellow requires inspection before judgment, Orange requires
an explicit bounded decision and rollback, and Red stops. Wrong owner,
authority, goal/host, response, route, permission, rollback, trigger, rights,
privacy, or false success is material. Wording/navigation with one clear
consequence is ordinary.

APG70 collects the complete initial material set, applies this one coherent
correction, preserves the actual full-index patch and corrected hashes, and
then discards every pre-correction review for terminal acceptance. A genuinely
new material defect after this correction requires rejection. Fresh APG70
review found such defects, so ADR 0040 is Rejected and eligibility is
`not-applicable-rejected`. Retention preserves immutable APG69/APG70 history.
This contract is not current authoring input and grants no candidate,
integration, release, publication, deployment, or successor authority.

## Known limitations

Pinned targets and APG52 corpus facts are descriptive and cannot calibrate a
numeric whole-file policy. The registers are bounded validation oracles, not an
exact-action map. Human semantic review remains necessary even when schema,
vocabulary, arithmetic, and mutation controls pass.
