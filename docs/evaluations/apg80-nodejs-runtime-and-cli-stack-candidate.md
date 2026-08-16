# APG80 Node.js Runtime and CLI-Stack Candidate

## Status

Complete. APG80 authored one narrow reusable `nodejs-runtime-profile` candidate,
its specification, a navigation-only twenty-four-scenario coverage record, a
fourteen-case APG-owned target-first fixture, and Proposed ADR 0046 on a Claude
authoring branch. It integrated nothing, decided nothing, and began no successor.

## What was authored

The candidate owns Node.js-specific host, module-loading, process, built-in API,
and CLI-adapter behavior for an established Node execution role — after the
exact version, platform, architecture, package scope, module mapping, loader,
invocation, external-resource evidence, and whole-file owner are established. It
may receive `node-runtime-owner`, `node-commonjs-owner`, and
`module-loader-owner` for decisions whose exact selected implementation is
Node's built-in runtime or loader, without collapsing those decisions.

Selection remains `selected`, `embedded-route`, `route-to-owner`, or
`non-trigger`; response remains `proceed-routine`, `inspect-before-judgment`,
`bounded-local-decision`, or `stop-and-escalate`; the vocabularies stay closed
and disjoint, and selection stays orthogonal to whole-file ownership.

## The central design decision

The profile consumes runtime roles and selects none. Fresh target evidence made
that the only defensible shape. Across both read-only targets there is no
directly authored Node command-line entrypoint, no hashbang, no `.cjs` artifact,
and no plain `.js` source file, while runtime evidence exists at four non-equal
levels — dependency engine constraints in a lockfile, a declared minimum range,
a continuous-integration release-line selection, and, separately again, the
local authoring engine. Exact version, platform, architecture, flags, and
invocation are unresolved for every target role, and target execution was not
observed. A profile that assumed an exact runtime would have been wrong in both
real projects it was meant to serve.

For the same reason, Node structural policy is deferred. There is no Node
structural material in either target against which any threshold could be
calibrated, so inventing one would be arbitrary rather than conservative.

## Evidence

Node sources were freshly verified: the release schedule and currently supported
release lines, the versioned API documentation identity at an exact release tag,
and the license identity. Repository source and tests were treated as
implementation evidence only. No documentation prose, example, source, test, or
generated API data was copied. ECMA-262 remains the authority for ECMAScript
semantics and is routed rather than restated. Test262 was not needed, not read,
and not used as a corpus or oracle; its source-role record is unchanged.

A bounded scratch-only authoring smoke ran on the exact APG79E qualification
engine, with every observation bounded to that executable, version, V8 version,
platform, architecture, flag set, command, and input. It is authoring evidence
only — never a maintained test, a normative oracle, target-execution proof, or
an integration gate. No package install, shell command, external network
request, or target command ran.

Two smoke observations shaped the candidate rather than merely confirming it.
The commonly repeated rule that a `.js` file without a package `type` is
CommonJS proved false on the observed runtime whenever the source carries
module-only syntax, so mapping is recorded as depending on the exact version and
flags. And identical scheduling calls produced a different relative order from
an ECMAScript module entry than from a CommonJS entry on the same runtime with
the same flags, so an ordering claim may never be reused without its exact
scheduling context.

## Boundaries kept

APG80 added no known-debt entry and changed none of the ten existing entries.
`CSS-QD-001` through `CSS-QD-005` and `JS-QD-001` through `JS-QD-005` are exact.
The retained CommonJS stop was used as a target-first case without superseding
`JS-QD-001` or `JS-QD-005`. JavaScript, CSS, TypeScript, and Markdown lifecycles
are unchanged. No catalog row, projection, maturity row, capability route,
project selection, release owner, or test-inventory row changed, and both
targets and the corrected public and active v0.4.0 are unchanged and unexecuted.

The candidate branch is transitionally 33 canonical leaves against 32 catalog
rows and 32 projections. That shape is expected and truthful for an uncataloged
candidate; the skill-library checker was not weakened to hide it. The mainline
remains the exact APG79E terminal at 32/32/32.

## Known limitation

Twelve of the candidate's named receiving owners do not exist as integrated
profiles, so a route to any of them is a stop with an addressee rather than a
live handoff. Every version-sensitive claim rests on observations from a single
executable on a single platform plus the versioned documentation identity, and
neither target exercises a Node CLI entrypoint, child process, worker, network
path, or signal path. These are the candidate's thinnest areas and are recorded
for independent hardening rather than resolved here.

## Boundary

ADR 0046 is Proposed. APG81 is recommended, without beginning, as Codex Node.js
runtime and CLI iterative hardening and provisional integration at exit 00124.
Integration is possible only after independent reconstruction, zero Critical or
High findings, explicit human acceptance for any remaining Medium or Low, and
full regression, release, and rollback evidence. Codex cannot reject or remove
the candidate without human authority.
