# Node.js Runtime Profile — candidate specification

Status: **Provisionally integrated in APG81H under ADR 0046, Accepted with amendment.**
Lifecycle: `provisionally-integrated`.
Lifecycle ADR: `Accepted with amendment`.

This specification carries the source, boundary, and detailed semantics for the
candidate leaf at [`skills/nodejs-runtime-profile/SKILL.md`](../../skills/nodejs-runtime-profile/SKILL.md).
Navigation is recorded separately in
[the scenario-coverage record](nodejs-runtime-profile-scenario-coverage.md).

APG80 authored this candidate and decided nothing. APG81H accepts ADR 0046
with amendment and integrates the profile provisionally. Current development
therefore adds the exact Node catalog row, projection, provisional maturity
row, capability route, project selection, release owner, maintained test
owner, and test-inventory row. Candidate-preserving rollback removes those
integration owners while retaining the candidate and accepted decision.

## 1. Governing authority

ADR 0042 (Accepted) governs candidate authoring, iterative hardening, and
provisional integration. The production-recovery charter, the iterative-hardening
contract, and the known-debt register in `docs/governance/` remain controlling.
APG80 added no debt entry and changed none of the ten existing entries.

## 2. Reusable owner

This profile owns Node.js-specific host, module-loading, process, built-in API,
and CLI-adapter behavior for an established Node execution role — after the exact
Node version, platform, architecture, package scope, module mapping, loader,
invocation, external-resource evidence, and whole-file owner are established.

It may receive the decision-scoped owner names `node-runtime-owner`,
`node-commonjs-owner`, and `module-loader-owner` when the exact selected
implementation is Node's built-in runtime or loader. One profile receiving
several owner names does not collapse their decisions; each route keeps its exact
scope. Receiving `node-commonjs-owner` for a standalone CommonJS artifact does
not make this profile the whole-file owner of every source Node executes.

The profile **consumes** an exact project-selected runtime, version, platform,
package boundary, module system, invocation, and external-resource state. It
selects none of them. It does not select Node for every JavaScript or TypeScript
artifact, and it hard-codes no runtime version — not the APG qualification
engine, and not either target's declared range.

## 3. Product orientation

The JavaScript profile owns ECMAScript language semantics for an established
region. The TypeScript profile owns TypeScript static semantics under an exact
compiler role. This profile owns Node-specific host, loader, process, built-in
API, and CLI-adapter decisions under an exact selected runtime role. Project
design chooses JavaScript versus TypeScript, Node versus another runtime,
package shape, service shape, architecture, deployment, and migration.

This profile is usable with JavaScript, with JavaScript emitted from TypeScript,
or with another Node-loadable artifact only after exact source, transform, and
runtime roles are established. It decides none of the following: whether a
utility should be JavaScript or TypeScript; whether a script should become a
package, service, daemon, worker, or web application; whether synchronous or
asynchronous architecture is acceptable; whether a child process or worker is
preferable; whether runtime complexity justifies migration; or whether Node.js
is approved for deployment.

## 4. Sources, roles, and rights

| Source | Exact identity | Role | State | Rights boundary |
| --- | --- | --- | --- | --- |
| Node.js release schedule | `nodejs/Release` commit `e4bf922d83b877a116763e2f83d2d9b6701871f9`, tree `95bdeeba8d989bea3ae92643fee54145a5f2851f`, `schedule.json` blob `3a6af719fb943a16a672eeb81dec0a04500d7a59`, read 2026-08-10 | supported-release-line evidence | exact immutable observation of a mutable source | identity recorded; no prose copied |
| Node.js versioned API documentation | `nodejs/node` tag `v22.22.2` → commit `2645dc73720b1b4f27c49f395d3c66025ce126cc`, tree `6fa806ed5bbc3c0427f5f3376ecd2669ad98eca4`, `doc/api` tree `d96b470fd86a896f4570b0ec3dd350c95616a2aa` | public API contract for that exact version | immutable at that tag | identity recorded; no prose, example, or generated API data copied |
| Node.js versioned API documentation | `nodejs/node` tag `v24.19.0` → commit `cdc1b38d40cb567b7ad0b39c86addf830a0af0ae`, tree `c8419d3f0beec916a2ae2e21cbe95075941527a4`, `doc/api` tree `0482a4b69dd9c00a7bf9731f39cae9d43b1ec926` | public API contract for that exact version | immutable at that tag | identity recorded; no prose, example, or generated API data copied |
| Node.js license | blob `a640a1f4708257449c53645022c8762488d7261f` | rights evidence | immutable at that tag | MIT-style grant for project code plus externally maintained library sections; APG policy forbids copying regardless |
| Node.js license | v24.19.0 blob `2842efa1288eef1de3a6778b5dd3519bc903308d` | rights evidence | immutable at that tag | MIT-style grant for project code plus externally maintained library sections; APG policy forbids copying regardless |
| ECMA-262 | `tc39/ecma262` tag `es2026` → `f7db29f16c5175a93f0d6e8fb27a8e3cb9b97a9e` | authority for ECMAScript semantics | immutable | routed to the JavaScript owner; not restated here |
| libuv | version `1.51.0` as reported by the observed runtime | component identity only | bound to that build | no retained claim depends on libuv internals |
| WHATWG and other Web-platform specifications | not pinned | authority for standards-defined API algorithms | mutable | no retained claim depends on them; they are named as routes |
| Package-manager documentation | not pinned | adjacent-owner evidence | mutable | no retained claim depends on it |
| Target repositories | pinned in §12 | target evidence | mutable | read-only; no source, path, or command body copied |

Node's official versioned public documentation may define the supported public
API contract for that exact Node version. Repository source and tests are
implementation evidence, not a license to copy expression and not an automatic
override of the public contract. ECMA-262 remains authority for ECMAScript
semantics; Node documentation defines Node host and API behavior only where it
actually makes the claim.

Test262 is not needed by this profile and was not read, copied, executed,
inventoried, or used as a corpus or oracle. Its APG79D source-role record is
unchanged.

### 4.1 Supported release lines as of 2026-08-10

Release line 22 is a maintenance long-term-support line ending 2027-04-30.
Release line 24 is an active long-term-support line ending 2028-04-30. Release line 26
is the current line, scheduled to enter long-term support later in 2026. Lines
20, 23, and 25 have passed their end dates. A supported release line is a
support fact. It is not a project's runtime selection, and it is not an exact
version.

## 5. Runtime roles and the evidence ladder

Every consequence-bearing runtime role records: role identity; runtime family;
exact version or `unresolved`; executable or host identity; selection source;
product state (`intended`, `current`, `temporary`, `unresolved`); invocation
state (`invoked`, `not-invoked`, `unresolved`); platform; architecture; flags;
retirement condition when temporary; present evidence; and required evidence.

These are distinct facts and never substitute for one another:

1. a runtime executable is available on some machine;
2. a runtime family is selected by a project;
3. a dependency graph constrains an install through its own engine fields;
4. a manifest declares an accepted version range;
5. a continuous-integration configuration selects a release line;
6. an exact version is resolved;
7. flags, conditions, and loaders are selected;
8. a platform and architecture are selected;
9. a command is actually invoked;
10. an execution is observed.

A claim that depends on level *n* stops when level *n* is unresolved, even when
every lower level is known. The local authoring engine is a separate fact again:
it is never evidence about a target.

### 5.1 The APG80 authoring observation

APG80 ran a bounded authoring smoke on the exact APG79E qualification engine:
Node `v22.22.2`, V8 `12.4.254.21-node.39`, `darwin/arm64`, executable SHA-256
`b7fff29202c2d59eeff28c53588d2832323b45cb2e854ba29bea47ade37d8359`, empty
`execArgv`, no `NODE_OPTIONS`. Every observation below is bounded to that
executable, version, V8 version, platform, architecture, flag set, command,
input, and scratch state. None of it establishes that either target used that
executable, and none of it is a reusable runtime selection.

### 5.2 The APG81 contrasting runtime observation

APG81 independently retained a second exact supported line: official Node
`v24.19.0`, V8 `13.6.233.17-node.51`, libuv `1.52.1`, `darwin/arm64`, executable
SHA-256 `27db838bb204ef7c21df2931f5656e4c8fb32e6e947f363a402b49714d32b5b1`,
provisioned from the official archive whose SHA-256 is
`8294b7aa9b03997481c06babf1e8b270c859358f27da57a11509afe537ac381d`.
The v22.22.2 and v24.19.0 roles remain distinct exact observations; neither is a
reusable default or target-runtime claim.

Material contrasts are retained instead of flattened: the v24 CommonJS
namespace adds a `module.exports` marker; the documented require-of-ESM and
type-stripping maturity and disabling flags differ; and v24 no longer exposes
the v22 `--experimental-default-type` CLI option. Any conclusion touching those
surfaces binds the exact runtime and flags.

## 6. Decision axes

Selection is exactly one of `selected`, `embedded-route`, `route-to-owner`, or
`non-trigger`, and is decision-scoped and orthogonal to whole-file ownership.
Response is exactly one of `proceed-routine`, `inspect-before-judgment`,
`bounded-local-decision`, or `stop-and-escalate`. The two vocabularies are
disjoint: `route-to-owner` is a selection and never a response.

Worked examples:

- Node `process.argv` behavior for an established Node CLI adapter: `selected`.
- Node loader behavior for a project-configuration-owned `.mjs` file:
  `selected` for the loader decision, with whole-file ownership unchanged.
- Node source genuinely nested inside another host file: `embedded-route`, and
  only when such a nested region actually exists.
- An ECMAScript coercion question: `route-to-owner` to the JavaScript owner.
- A lockfile resolution question: `non-trigger`, or `route-to-owner` to
  `package-manager-owner`.

Routes are a small ordered set with one item per consequence-bearing adjacent
decision. Routing never lowers the response, and a routed stop stays stopped.

## 7. Package scope and module mapping

Package scope is established from the exact filesystem and the nearest
controlling manifest. One package's `type` does not leak across an independently
established package boundary. Mapping is Node host behavior, not ECMAScript
grammar authority. Source syntax participates in mapping only where the exact
version and flags establish that it does. An unknown mapping blocks every
dependent host and parse-goal conclusion and nothing else. TypeScript, bundler,
test-runner, and framework resolution may differ from Node's and must never be
silently substituted.

Observed on the runtime in §5.1, with no flags:

| Input | Nearest manifest | Observed mapping | Evidence class |
| --- | --- | --- | --- |
| `.mjs` | `type: "module"` root | ESM | explicit extension |
| `.cjs` | `type: "module"` root | CommonJS | explicit extension |
| `.js` | `type: "module"` | ESM | explicit package type |
| `.js`, CommonJS-only syntax | `type: "commonjs"` | CommonJS | explicit package type |
| `.js`, module-only syntax | `type: "commonjs"` | refused with a syntax error, exit status 1 | explicit package type wins over syntax |
| `.js`, module-only syntax | manifest without `type` | reparsed as ESM, with a typeless-package diagnostic | version-specific syntax detection |
| `.js`, CommonJS-only syntax | manifest without `type` | CommonJS, no diagnostic | version-specific syntax detection |
| `.js`, module-only syntax | no manifest found | reparsed as ESM, without that diagnostic | version-specific syntax detection |
| `.js`, goal-neutral syntax | manifest without `type` | not settleable from the artifact | mapping requires the exact version and flags |

Two consequences matter more than the table. First, the widely repeated rule
that a `.js` file without a package `type` is CommonJS is **false on this exact
runtime** whenever the source carries module-only syntax; a profile that encoded
that rule from memory or from older documentation would be wrong. Second, an
explicit `type` is not merely a default — it *overrides* syntax, so an explicit
scope and an absent scope are different evidence states, not two spellings of
one.

Standard input, `--eval` input, `--input-type`, and any default-type or
detection flag are part of the same evidence set. A conclusion about them
requires the exact flag values, not their names.

## 8. CommonJS host boundary

For a standalone CommonJS artifact the whole-file owner is
`node-commonjs-owner`; an ECMAScript decision inside the artifact may separately
select the JavaScript profile; the wrapper and loader result are Node-owned.
This preserves the boundary the JavaScript profile already records and does not
modify `JS-QD-001`.

Observed on the runtime in §5.1: the wrapper supplies `exports`, `require`,
`module`, `__filename`, and `__dirname`; top-level `this` is the initial
`module.exports`; `exports` and `module.exports` are the same object until
`module.exports` is reassigned, after which they differ; repeated `require` of
one resolved filename yields one cached instance recorded under that filename.

Cycle behavior, JSON and native-addon loading, and interaction with package
`exports` are covered only where an exact retained claim exists. Nothing here
establishes an external effect.

## 9. ESM host boundary

Observed on the runtime in §5.1: module identity is URL-based; `import.meta.url`,
`import.meta.dirname`, `import.meta.filename`, and `import.meta.resolve` are
present; no CommonJS wrapper global is defined; top-level `this` is `undefined`;
`node:` built-in specifiers resolve. `import.meta` field availability is
version-specific and must never be assumed on an unstated version.

ECMAScript module declarations, live bindings, namespace semantics, and
evaluation remain JavaScript-owned once Node's loading and linking facts are
established. Node's loader is not a bundler and not a package manager.

## 10. Resolution, exports, imports, and conditions

Keep these separate: specifier text; resolver inputs; package scope; the
`exports` and `imports` maps; the condition set; the filesystem and package
graph; the resolution result; the loading result; the linking result; the
ECMAScript evaluation result; and the external operational result.

Observed on the runtime in §5.1, from checked-in files with no installation, no
lockfile, and no `node_modules` directory: relative specifiers, `node:`
built-ins, package self-reference through the nearest manifest's `name`, an
exported subpath, and a `#`-prefixed `imports` specifier all resolve; a condition
key selects a different target when the runtime is invoked with the matching
custom condition; and a package-relative specifier for a path absent from
`exports` is refused with `ERR_PACKAGE_PATH_NOT_EXPORTED`.

Encapsulation is a resolution result. It is not a filesystem permission, not an
access control, and not a security boundary. A resolved specifier is not proof of
successful evaluation or of any external effect. A package manager's installed
graph is an input to Node's resolver, not an output Node created.

## 11. Interoperability and module identity

Interoperability is version-sensitive, and no single universal rule may be
stated across Node versions.

Observed on the runtime in §5.1: importing a CommonJS module from ESM yields a
default export carrying the whole `module.exports` object; statically assigned
export names are additionally surfaced as named exports; export names assigned
through a computed key are **not** surfaced, leaving only `default`, and a named
import of such a name fails at link time; `require` of an ECMAScript module
succeeds and returns a namespace on this version.

Static named-export detection is a Node loading affordance. It is not an
ECMAScript live binding and must never be promoted into one. The
`require`-of-module result is a property of this version and flag set alone.

Identity, observed on the same runtime: repeated `require` of one resolved
filename yields one instance present in the require cache; the same ESM specifier
yields the same namespace object; a query-suffixed specifier yields a distinct
namespace. Identity claims are bounded to one process under exact specifier and
loader facts. They are never process-independent, persistence, or deployment
semantics. Symlink and realpath consequences require exact version and flag
evidence before any claim.

## 12. Target evidence

Both targets were freshly remote-verified and pinned read-only on 2026-08-10. No target command was
run and no target byte changed.

The website target's default branch resolved to commit
`e806e49a45797937e62f7bde61c711bec38725c7`, tree
`93e3454a1b65d1fd5cb6e38df42e9d6cfc8c9248`, with 17 tracked paths — unchanged
from the APG79E orientation. The theme target's canonical default branch
resolved to commit `cad2b8bdddfc0f2ac3718e7ca92e24e6b82051e0`, tree
`f3d563af289611cbd1f22600b777bc1de8781934`, with 69 recursive tracked leaf
entries. Both official remote default-branch identities were freshly
reverified. No target worktree supplied evidence.

Findings that bear on the candidate:

- Neither target contains a single directly authored Node command-line
  entrypoint, hashbang, `.cjs` artifact, or plain `.js` source file. The one
  `.mjs` artifact across both targets is a framework configuration module.
- The only Node built-in specifiers anywhere in either target appear in exactly
  one TypeScript source artifact — the same artifact a package `exports` map
  designates as the package entry. That is source and tool evidence. It is not
  proof that Node directly executes TypeScript, and the same map also exports
  framework component files that Node's loader cannot load at all.
- Runtime evidence exists at four non-equal levels: dependency engine
  constraints inside the lockfile; a declared minimum range on the theme's
  retained manifests; a continuous-integration release-line selection on the
  theme; and, separately again, the local authoring engine. The website declares
  no range at all and delegates runtime selection to a third-party composite
  action.
- Exact runtime version, platform, architecture, flag set, and invocation are
  `unresolved` for every target role. Target execution was not observed.

The practical consequence is that a Node profile written against these targets
must be built to consume runtime roles and to stop when they are unresolved,
because in the only two real projects available the exact runtime is *never*
resolved from project evidence alone.

## 13. Package-manager, script, and shell boundary

Package-manager identity and version, workspace selection, lockfile and install
graph, script name, script command, the shell the package manager selected,
environment and `PATH` mutations, the Node executable the command named, the
invocation, and the resulting process status are ten separate facts. A
`packageManager` declaration selects a package-manager role, not a Node process.
A package script may invoke a framework CLI, a linter, a release tool, a shell,
or Node; the exact decision must be identified before Node is selected. No
package-manager command was run in APG80.

Shell tokenization, quoting, expansion, pipelines, redirection, globbing,
command-injection approval, and executable trust are `shell-owner` decisions. A
`child_process` API decision and the shell command it may invoke are separate.

## 14. Process, CLI, stdio, and filesystem

Entrypoint selection, `process.execPath`, `process.execArgv`, `process.argv`,
working directory, `process.chdir`, `process.env`, platform, architecture,
`NODE_OPTIONS` and selected flags, terminal state, and the parent process or
package-script wrapper are all evidence fields. Argument acquisition, argument
parsing performed by the application, shell parsing performed before Node
started, project configuration, secret handling, and business logic are
different layers.

Environment values are external inputs. Their presence authorizes no logging,
publication, or persistence. Fixtures and diagnostics use synthetic
non-sensitive values only, and no diagnostic may normalize dumping arbitrary
environment variables or child output.

Observed on the runtime in §5.1: under a piped invocation the standard streams
are not terminals; a write below the buffer threshold is accepted and a larger
write is refused before a subsequent drain on an in-memory sink; and
`process.exitCode` records a status that the process exits with. A write call is
not proof that bytes reached a terminal, file, pipe consumer, or remote system.
`process.exit` truncates pending work; `process.exitCode` does not.

Node owns its documented filesystem, path, and file-URL API contracts. Observed:
file-URL conversion round-trips, a rename preserves content, and a missing path
reports `ENOENT`. Node proves no permission policy, no cross-filesystem
atomicity, no durability after power loss, no remote-filesystem consistency, no
path safety for untrusted input, and no business authorization.

APG qualification runs only in a controlled local or CI context with reviewed
APG fixtures and synthetic non-sensitive inputs. The parent creates one private
unique direct-child invocation root with exact `tmp`, `npm-cache`, `pnpm-home`,
`work`, and `fs-case` children; ordinary preflight rejects relative paths,
lexical or resolved escapes, foreign directories, and pre-existing symlinks.
The exact configured runtime is a direct regular executable observed by path,
file identity, digest, and public identity before and after invocation. That is
pre/post evidence, not continuous identity or hostile same-UID resistance.

The harness is not a security boundary. Target code, user code, credentials,
secrets, untrusted fixtures, shell execution, application dependency
installation, and fixture network access are prohibited. Concurrent hostile
same-UID mutation and untrusted execution route to the environment's security,
sandbox, CI-isolation, or operating-system owner; with no integrated receiver,
the response is `stop-and-escalate`. Owned cleanup attempts every action,
reports success only after the invocation root is absent, and reports retained
artifacts through bounded contract IDs rather than raw paths or streams. The
machine-readable contract is
`testing/nodejs-profile-qualification-threat-model.json`.

## 15. Errors, signals, lifecycle, and scheduling

Synchronous thrown errors, callback errors, promise rejection, uncaught
exceptions, unhandled rejections, warnings, `exit` and `beforeExit`, signal
events, signal-derived termination, and shutdown boundaries are distinct. An
uncaught-exception handler is not a generic recovery strategy, and a handler
running is not proof that cleanup completed. No unrelated process may be
signalled.

Observed on the runtime in §5.1: an APG-owned child spawned directly through the
running executable with no shell, terminated by its parent, installed a handler,
exited normally, and was reaped with an observed close status.

Scheduling requires its exact context. Observed, reproducibly, on one runtime
with one flag set: identical scheduling calls made from an ECMAScript module
entry and from a CommonJS entry produce **different** relative order —
`process.nextTick` runs before microtasks from the CommonJS entry and after them
from the module entry. The entry's module system alone changed the answer. This
is the reason an ordering claim may never be reused without its exact scheduling
context, entry module system, version, and flags, and the reason no latency or
fairness guarantee may be offered without matching evidence.

ECMAScript Promise and `queueMicrotask` semantics remain language-owned.
Operating-system scheduling, wall-clock timing, and platform behavior remain
non-owners.

## 16. Child processes, workers, and network

`spawn`, `exec`, `execFile`, `fork`, stdio configuration, the shell-versus-direct
invocation choice, environment and working directory, exit, close, error and
signal events, and cleanup are Node API contracts under exact evidence. Shell
grammar, quoting, expansion, command injection, executable trust, credential
policy, operating-system authorization, and remote effects route separately.

Worker coverage is bounded to availability, entrypoint selection, message
passing, structured clone and transfer, errors and exit, and resource and
termination state. ECMAScript shared-memory semantics require exact language
sources. Operating-system scheduling, performance acceptance, native addons, and
application concurrency design are non-owners. Where comprehensive worker
semantics are not maintained, the profile stops rather than implying coverage.

Network coverage is bounded to Node's exposure and local lifecycle of `net`,
`dgram`, `dns`, HTTP-family, TLS, `URL`, `fetch`, Web Streams, and `AbortSignal`
integration on an exact version. Protocol application correctness, DNS truth,
remote-system availability, TLS and certificate policy, credential handling,
firewall behavior, browser behavior, security approval, and deployment remain
separate. APG80 performed no external network request, and the fixture contacts
no external service.

## 17. Flags, loaders, permissions, and partial coverage

`NODE_OPTIONS`, `--input-type`, `--conditions`, `--require`, `--import`, source
maps, warnings and deprecations, custom loaders and hooks, the permission model,
the inspector, and experimental or release-candidate APIs are evidence fields
whenever a retained claim touches them. A feature available in one release is
not universal, and a flag may change package mapping, loader behavior, security
surface, or diagnostics.

One observation from §5.1 illustrates the risk precisely: on this runtime, and
with no flag, a TypeScript source file with fully erasable syntax executed
directly, while a file using non-erasable TypeScript syntax did not. Both facts
belong to that exact version. Neither makes Node an owner of TypeScript, and
neither may be carried to another version or to either target.

The initial profile does not cover native addons or N-API, WASI, `vm` and policy
sandboxes, `cluster`, the inspector protocol, the full crypto surface, all
diagnostic channels, all experimental APIs, or all platform differences. Those
stop at the exact local boundary and require separate source-backed extension.

## 18. Explicit non-owners

Node does not own ECMAScript language semantics; TypeScript parsing, checking,
inference, emit, erasure, options, transformation, or migration; package-manager
installation, registry selection, lockfile generation, workspace filtering,
dependency solving, lifecycle-script orchestration, publication, or supply-chain
approval; shell grammar or operating-system policy; DNS, HTTP application
correctness, TLS policy, remote-service behavior, credential approval, threat
acceptance, firewall policy, or deployment exposure; DOM, rendering, browser
storage, navigation, or browser compatibility; or bundlers, transforms, source
maps as transformation truth, lint policy, test-framework semantics, release
approval, readiness, publication, deployment, or product behavior.

## 19. Layer separation

Source-language semantics; source transformation or type stripping; Node package
and module mapping; Node resolution and loading; ECMAScript linking and
evaluation; Node runtime and built-in API behavior; external operational effect;
and product readiness and deployment are eight separate layers. A result in one
never establishes a result in another. A correct CLI core result does not prove
argument acquisition, output delivery, filesystem mutation, exit status, or
user-visible completion; a working command does not prove readiness,
publication, or deployment.

## 20. Structural policy

Node structural policy is **deferred**. No threshold exists or may be introduced
for file size, statement or function count, dependency count, side effects,
child processes or workers, cyclomatic complexity, latency, throughput, memory,
or package size, and none automatically selects a runtime, an architecture, or a
migration.

This deferral is grounded, not merely cautious. Across both targets there is no
directly authored Node command-line program, no `.cjs` artifact, and no plain
`.js` source file — that is, no Node structural material at all against which any
threshold could be calibrated. Inventing one would be arbitrary.

Qualitative observations may route review to `project-design-owner`: language
core and Node adapter entangled; implicit process-global state; unbounded
filesystem or network effects; ambiguous shutdown; shell invocation hidden behind
a helper; runtime selection hidden in package-manager behavior; an unclear
module-system boundary; synchronous blocking on a server or interactive path; or
unowned worker and child lifecycle. Such an observation never decides failure,
migration, or architecture.

## 21. Fixture

The APG-owned fixture at
[`src/test/fixtures/apg80-nodejs-runtime-cli/`](../../src/test/fixtures/apg80-nodejs-runtime-cli/)
carries fourteen cases, `APG80-FX-001` through `APG80-FX-014`, with a separate
record for each of its 41 case artifacts and its two documentation artifacts. It
requires no installation, contacts no network, invokes no shell, touches no
target, and performs its synthetic filesystem case only inside the exact
parent-created `fs-case` directory for that controlled invocation.

It is maintained current evidence after the APG81A threat-model correction. It
is not a normative oracle, target-execution proof, or security boundary;
maintained contracts independently own its schema, hashes, direct pre/post
runtime observations, controlled scratch contract, and stopped states.

## 22. Known limitations of this candidate

1. **Most named receiving owners do not exist as integrated profiles.**
   `package-manager-owner`, `shell-owner`, `operating-system-owner`,
   `filesystem-owner`, `network-owner`, `browser-platform-owner`,
   `build-transform-owner`, `test-owner`, `security-owner`,
   `performance-owner`, `deployment-owner`, and `service-supervisor-owner` are
   named addressees. A route to any of them is a stop with an addressee, not a
   live handoff. This is the candidate's most significant practical limitation
   and it is unresolved by APG80.
2. **Platform coverage remains intentionally bounded.** Two exact supported
   release lines are observed on `darwin/arm64`; no other platform or
   architecture is claimed.
3. **Target grounding is thin by nature.** Neither target exercises a Node CLI
   entrypoint, child process, worker, network API, or signal path, so those
   boundaries are argued from documentation and from the APG-owned fixture
   rather than from target practice.
4. **Coverage is deliberately partial**, as §17 records. Partial coverage never
   implies comprehensive Node ownership.
5. **The profile is provisionally integrated.** ADR 0046 is Accepted with
   amendment after exact State A and candidate-preserving State B qualification.

## 23. Rollback

Rollback is history preserving. It may deactivate or remove only current Node
integration owners: the projection, catalog row, maturity row, capability and
project routes, current-development release membership, and maintained current
test/inventory bindings. It preserves the candidate leaf and specification,
ADR 0046, APG80/APG81/APG81A commits and records, fixture and evidence history, and all
ten CSS/JavaScript known-debt entries. Rollback never deletes phase history and
never rewrites a commit. After ADR 0046 is accepted, rollback keeps that
historical decision accepted and gives every retained current candidate
lifecycle surface the exact state `accepted-integration-rolled-back`; historical
APG80 prose may still record that the candidate was authored while the ADR was
Proposed. A current Proposed state, a deleted candidate, or any retained current
integration owner is not a successful rollback.
