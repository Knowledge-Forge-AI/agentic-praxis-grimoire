# ADR 0046: Node.js Runtime and CLI-Stack Candidate and Target-First Harness

## Status

Accepted with amendment. APG80 authored one narrow reusable `nodejs-runtime-profile` candidate,
its specification, a navigation-only twenty-four-scenario coverage record, and a
fourteen-case APG-owned target-first fixture on a Claude authoring branch. APG80
integrated nothing and decided nothing. A separate Codex phase was required to
independently reconstruct every candidate and fixture expectation before this
ADR could be decided. Codex could not reject or remove the candidate without
human authority. APG81 independently reconstructed the candidate through three
preserved rounds and stopped at a terminal repair checkpoint. APG81A exercised
separate human continuation authority, completed a fresh zero-finding harness
correction, and stopped its later integration candidate on rollback and ADR-
index findings. APG81B clarified the future candidate-preserving rollback
target, but its complete integration candidate stopped on three Medium staged-
review defects. APG81C retained an immutable integration-support correction,
then stopped when fresh postcommit review found a Medium contradiction between
committed pending-review prose and the completed review evidence. No integration
commit existed at that checkpoint, so ADR 0046 remained Proposed. APG81D later reconstructed the
complete integration candidate, but final staged review found one High and
three Medium defects. Those attempted bytes were discarded without correction,
so ADR 0046 remained Proposed and Node remained repair-required and unintegrated.

APG81F later attempted one explicitly authorized actual-test-projection,
chronology, and source-evidence correction. Fresh review found three High and
two Medium defects in the correction, so its implementation and test bytes
were discarded. Its status remained Proposed; APG81F neither integrated nor
rejected the candidate.

APG81G exercised a new explicit human continuation and attempted one bounded
correction of those five findings. Fresh review found two High and four Medium
defects, so the attempted implementation and test bytes were discarded. No Node
integration commit existed at that checkpoint, so ADR 0046 remained Proposed.

APG81H exercises the next explicit human continuation. Fresh review of its
single bounded correction found one Medium defect because the frozen evidence
did not bind the complete actual language-profile lifecycle map. Attempted
implementation and test bytes were discarded before commit. No integration
commit existed at that checkpoint, so ADR 0046 remained Proposed.

APG81H final resume preserves that history and the immutable lifecycle-map and
test-isolation corrections. This integration candidate selects ADR 0046 as
Accepted with amendment and provisionally integrates Node in intended State A.
Required State A and candidate-preserving State B mechanical qualification is
complete: the configured unit, integration, and combined-coverage gates pass
for the applicable exact trees. Final staged review remains an external commit
gate and is not self-attested by this tree. The amendment makes lifecycle
distinct from maturity, retains exact non-Node topology, and preserves rollback as
`accepted-integration-rolled-back` without reopening candidate semantics or
the threat model. It grants no stable maturity, readiness, publication,
deployment, target execution, or successor authority.

## Context

ADR 0042 (Accepted) established candidate authoring separated from independent
hardening, a default budget of up to three preserved correction rounds, Critical
and High findings blocking integration, explicit human acceptance for any
remaining Medium or Low, and human authority for terminal rejection or removal.

The JavaScript profile was provisionally integrated in APG79E with `JS-QD-001`
through `JS-QD-005` accepted as Medium qualification limitations. It names
`node-runtime-owner`, `node-commonjs-owner`, and `module-loader-owner` as
receivers for decisions it explicitly refuses — CommonJS wrapper bindings,
specifier resolution, package exports, process and stdio state, Node timers and
event-loop phases, and the CLI adapter beside an effect-free core. None of those
receivers exists as an integrated profile, so every such route is currently a
stop with an addressee rather than a live handoff.

APG80 was separately authorized to begin closing that gap by authoring — not
integrating — a Node candidate.

APG81's immutable-flag and copied-runtime experiment remains valid historical
falsification evidence: same-UID mutation, deeper path redirects, pre-pin setup,
outside-parent mutation, and partial restoration disproved the stronger
containment and cleanup claims. APG81A narrows current qualification to trusted
APG fixtures in controlled local or CI execution. The harness is not a security
boundary; direct runtime identity is observed before and after use, continuous
identity is not claimed, and hostile or untrusted execution routes to a separate
security, sandbox, CI-isolation, or operating-system owner.

## Decision

1. Author exactly one narrow reusable candidate named `nodejs-runtime-profile`,
   at `skills/nodejs-runtime-profile/SKILL.md`, with its specification and a
   navigation-only coverage record. Do not split it into module, process, CLI,
   filesystem, and network skills, and do not add a project-skill projection.
2. Define its reusable owner as Node.js-specific host, module-loading, process,
   built-in API, and CLI-adapter behavior for an established Node execution role,
   after the exact version, platform, architecture, package scope, module
   mapping, loader, invocation, external-resource evidence, and whole-file owner
   are established.
3. Allow the profile to receive `node-runtime-owner`, `node-commonjs-owner`, and
   `module-loader-owner` for decisions whose exact selected implementation is
   Node's built-in runtime or loader, without collapsing those decisions into
   one another.
4. Make the profile **consume** runtime roles and select none. It does not
   select Node because JavaScript or TypeScript source exists, and it hard-codes
   no runtime version — neither the APG qualification engine nor any target's
   declared range.
5. Record runtime evidence as an ordered ladder in which an available
   executable, a selected family, a dependency engine constraint, a declared
   range, a continuous-integration release line, an exact version, flags, a
   platform, an invocation, and an observation are distinct facts that never
   substitute for one another.
6. Keep Selection (`selected`, `embedded-route`, `route-to-owner`,
   `non-trigger`) and Response (`proceed-routine`, `inspect-before-judgment`,
   `bounded-local-decision`, `stop-and-escalate`) closed and disjoint, with
   selection decision-scoped and orthogonal to whole-file ownership.
7. Treat a standalone `.cjs` artifact as `node-commonjs-owner`-owned rather than
   `embedded-route`, preserving the boundary the JavaScript profile records and
   modifying `JS-QD-001` in no way.
8. Establish package scope from the exact filesystem and nearest controlling
   manifest, and make module mapping depend on the exact Node version and flags
   — including the case where an absent package `type` makes mapping depend on
   the file's own syntax, and the case where nothing in the artifact can settle
   it at all.
9. Keep Node's mapping, resolution, and loading results strictly separate from
   ECMAScript linking and evaluation, which remain JavaScript-owned.
10. Record interoperability, `require` of a module, and module identity as
    version-sensitive observations, never as universal rules, and never promote
    static named-export detection into a live-binding guarantee.
11. Exclude package-manager installation, registry behavior, lockfiles,
    workspace selection, and lifecycle-script orchestration from Node ownership;
    a `packageManager` declaration selects a package-manager role, not a Node
    process.
12. Exclude shell grammar, operating-system policy, network protocol
    correctness, TLS and credential policy, browser and Web-platform semantics,
    build transformation, test-framework semantics, security approval,
    performance acceptance, deployment, and product architecture.
13. Exclude ECMAScript language semantics and all TypeScript static semantics,
    including any inference that Node executes TypeScript.
14. Refuse operational completion claims: a resolved specifier is not
    evaluation, a write is not delivery, a filesystem call is not durability or
    authorization, a socket is not remote success, and a correct CLI core result
    is not a working command.
15. Defer Node structural policy entirely, with no numeric threshold of any kind
    and no automatic migration recommendation in either direction.
16. Author exactly twenty-four navigation scenarios, `APG80-NODE-001` through
    `APG80-NODE-024`, that answer only where a decision is made.
17. Author exactly fourteen fixture cases, `APG80-FX-001` through
    `APG80-FX-014`, APG-owned and independently written, recording every
    artifact separately and never flattening mixed artifacts into one mapping,
    owner, runtime state, or execution state.
18. Require the fixture to need no installation, contact no network, invoke no
    shell, touch no target, and write only beneath a validated
    invocation-owned scratch root.
19. Bound every executed observation to one exact executable, version, V8
    version, platform, architecture, flag set, command, and input, and treat the
    authoring smoke as evidence only — never a maintained test, oracle, or gate.
20. Use official versioned Node documentation as the public API contract for an
    exact version, treat repository source and tests as implementation evidence
    only, and copy no documentation, source, test, or generated API data.
21. Use Test262 not at all: it is neither needed nor read, and its APG79D
    source-role record is unchanged.
22. Preserve `CSS-QD-001` through `CSS-QD-005` and `JS-QD-001` through
    `JS-QD-005` exactly, and add no Node debt.
23. Integrate nothing: add no catalog row, projection, maturity row, capability
    route, project selection, release owner, or test-inventory row, and leave
    `main` at the exact APG79E terminal.
24. Require a separate Codex phase to independently reconstruct every candidate
    and fixture expectation from official versioned Node sources, exact
    implementation observations, fresh target facts, and accepted APG contracts,
    treating APG80 prose, manifest expectations, smoke results, and author-side
    review as proposals and evidence rather than as an oracle.

## Consequences

The repository gains a Node candidate that is deliberately narrow, explicitly
partial, and structured to stop rather than guess. Its most valuable property is
that it refuses to select a runtime: fresh target evidence shows that in the only
two real projects available, the exact Node version is never resolvable from
project evidence alone, so a profile that assumed one would be wrong in every
real case it was meant to serve.

The candidate's most significant practical limitation is that twelve of its
named receiving owners do not exist as integrated profiles. Routes to them are
stops with addressees, not live handoffs. Provisional integration would not
change that, and whether it is acceptable is a question APG80 did not settle.

APG81 corrects the original single-executable limitation with maintained exact
v22.22.2 and v24.19.0 roles on `darwin/arm64`, preserving their material
interop and flag differences. Platform and architecture breadth remains
deliberately unclaimed, together with the absence of any target-side Node CLI
entrypoint, child process, worker, network path, or signal path.

Rollback is history preserving. It may remove or deactivate current Node
integration owners only, restoring the exact pre-integration catalog,
projection, maturity, route, project, release, and test state. It preserves the
candidate, this ADR, APG80/APG81 commits and records, fixture/evidence history,
and every known-debt entry. Candidate removal remains a separate human action,
not rollback.

Structural deferral is retained, not out of caution but because there is no Node
structural material in either target against which any threshold could be
calibrated.

APG80 does not accept or reject this ADR.

APG81 preserved three immutable hardening rounds, but fresh terminal review of
Round 3 left three High and two Medium qualification-harness findings. The
correction budget was exhausted, none of the findings was accepted as Node debt,
and integration was blocked. This ADR therefore remained **Proposed**;
`nodejs-runtime-profile` was `repair-required-after-round-3` without rejection,
removal, or integration. Further correction, debt acceptance, or disposition
required a new human decision.

APG81A through APG81D preserved later controlled-qualification and integration-
support corrections while repeatedly stopping attempted integration on fresh
review findings. APG81E reconstructed the final integration candidate under new
human authority, but final staged review found one High incomplete rollback
test-owner projection and two Medium chronology and source-evidence defects.
All attempted integration bytes were discarded. No Node or scratch debt was
accepted. This ADR therefore remained **Proposed**; the candidate remained
repair-required, retained, and unintegrated. Rejection, removal, debt
acceptance, integration, or further continuation required new human authority.

APG81F and APG81G preserved that retained candidate while later bounded
corrections again stopped on fresh qualification findings. APG81H first preserved
its stopped lifecycle-map checkpoint, then applied immutable lifecycle-authority
and change-size test-isolation corrections before constructing a new integration
candidate. Its bounded coverage continuation closed the superseded State A
branch-coverage failure without changing production lifecycle/topology or
coverage-policy bytes. The later replacement-control correction preserved
production `GIT_NO_REPLACE_OBJECTS=1`, and the historical corrected-v0.4 gate
was reclassified to exact immutable identity and prior-qualification binding;
the current-runtime replay remained `DIAGNOSTIC_NONQUALIFYING`.

The mechanically qualified State A selects this ADR as **Accepted with
amendment** and provisionally integrates `nodejs-runtime-profile`. Its
candidate-preserving State B retains the candidate and this decision while
removing current integration owners and recording
`accepted-integration-rolled-back`. Final Sol and Claude review remains an
external commit gate and is not self-attested by this tracked decision. No Node
or scratch debt is accepted, and stable maturity remains outside APG81H.
