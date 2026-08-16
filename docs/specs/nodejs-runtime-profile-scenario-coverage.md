# Node.js Runtime Profile — scenario coverage

Status: **Candidate navigation record authored in APG80, independently
reconstructed in APG81, and provisionally integrated in APG81H under ADR 0046,
Accepted with amendment.**
Lifecycle: `provisionally-integrated`.

This record answers exactly one question for each scenario: **where is this
decided?** It does not answer *what is the result?* It carries no expected
outcome, no pass or fail state, and no oracle. It is navigation.

Stable clauses name markers in
[`skills/nodejs-runtime-profile/SKILL.md`](../../skills/nodejs-runtime-profile/SKILL.md).
Fixture cases name cases in
[`src/test/fixtures/apg80-nodejs-runtime-cli/`](../../src/test/fixtures/apg80-nodejs-runtime-cli/).
A fixture reference means the case exercises the same boundary; it does not mean
the fixture decides the scenario. The maintained structured reconstruction is
`src/test/fixtures/apg81-nodejs-runtime-profile-scenarios.json`; this table
remains navigation-only.

| Scenario | Decision scope | Stable clauses | Fixture case |
| --- | --- | --- | --- |
| `APG80-NODE-001` | Established Node runtime role and selection state | `NODE-TRIGGER`, `NODE-SELECTION`, `NODE-RESPONSE` | `APG80-FX-001` |
| `APG80-NODE-002` | Exact version, platform, architecture, flags, and feature availability | `NODE-RUNTIME-ROLE`, `NODE-FLAGS-PERMISSIONS` | `APG80-FX-001` |
| `APG80-NODE-003` | `.mjs` Node ESM mapping | `NODE-MODULE-MAPPING` | `APG80-FX-002` |
| `APG80-NODE-004` | `.cjs` Node CommonJS mapping | `NODE-MODULE-MAPPING`, `NODE-COMMONJS` | `APG80-FX-002` |
| `APG80-NODE-005` | `.js` under a `type: "module"` package scope | `NODE-PACKAGE-SCOPE` | `APG80-FX-002` |
| `APG80-NODE-006` | `.js` under a `type: "commonjs"` package scope | `NODE-PACKAGE-SCOPE`, `NODE-MODULE-MAPPING` | `APG80-FX-002` |
| `APG80-NODE-007` | Unresolved or version- and flag-sensitive `.js`, standard-input, or evaluated-input mapping | `NODE-MODULE-MAPPING`, `NODE-UNKNOWN-STOP` | `APG80-FX-002` |
| `APG80-NODE-008` | CommonJS wrapper bindings and whole-file host ownership | `NODE-COMMONJS` | `APG80-FX-003` |
| `APG80-NODE-009` | Node ESM metadata and the absence of CommonJS wrapper globals | `NODE-ESM` | `APG80-FX-004` |
| `APG80-NODE-010` | Built-in, relative, absolute, and package specifier resolution | `NODE-RESOLUTION` | `APG80-FX-005` |
| `APG80-NODE-011` | Package `exports`, `imports`, conditions, and encapsulation | `NODE-RESOLUTION`, `NODE-ESM` | `APG80-FX-006` |
| `APG80-NODE-012` | ESM and CommonJS interoperability and dynamic import | `NODE-INTEROP` | `APG80-FX-007` |
| `APG80-NODE-013` | Module cache and identity boundaries | `NODE-CACHE` | `APG80-FX-008` |
| `APG80-NODE-014` | Package-manager, install-graph, lockfile, and Node runtime separation | `NODE-PACKAGE-MANAGER-BOUNDARY` | `APG80-FX-014` |
| `APG80-NODE-015` | Package script and shell boundary | `NODE-PACKAGE-MANAGER-BOUNDARY`, `NODE-NONTRIGGER` | `APG80-FX-014` |
| `APG80-NODE-016` | CLI entrypoint, `argv`, `execArgv`, `execPath`, hashbang, and working directory | `NODE-CLI-ENTRY` | `APG80-FX-009` |
| `APG80-NODE-017` | Environment, platform, process state, and the secret boundary | `NODE-PROCESS-STATE`, `NODE-EVIDENCE` | `APG80-FX-010` |
| `APG80-NODE-018` | Standard streams, backpressure, and exit status | `NODE-STDIO-STREAMS`, `NODE-ERRORS-EXIT` | `APG80-FX-011` |
| `APG80-NODE-019` | Filesystem, path, file URL, permissions, and durability boundary | `NODE-FILESYSTEM` | `APG80-FX-012` |
| `APG80-NODE-020` | Errors, rejections, warnings, signals, and process lifecycle | `NODE-ERRORS-EXIT`, `NODE-SIGNALS-LIFECYCLE` | `APG80-FX-013` |
| `APG80-NODE-021` | `nextTick`, microtasks, timers, immediates, and event-loop boundary | `NODE-EVENT-LOOP` | `APG80-FX-013` |
| `APG80-NODE-022` | Child processes, shell selection, workers, and cleanup | `NODE-CHILD-PROCESS`, `NODE-WORKERS` | `APG80-FX-013` |
| `APG80-NODE-023` | Network, Web-compatible APIs, protocol, security, and deployment boundary | `NODE-NETWORK-WEBAPI`, `NODE-ROUTES` | — |
| `APG80-NODE-024` | Target runtime and package-manager role, CLI core and adapter separation, and operational completion | `NODE-STATIC-RUNTIME-COMPLETION`, `NODE-STRUCTURE-DEFERRED` | `APG80-FX-014` |

## Reading the table

Twenty-four scenarios cite twenty-nine of the leaf's thirty stable clauses.
`NODE-ROLLBACK` is deliberately uncited and is identified here as
**operational-only**: it governs what a repair must record before it is made,
which is an operational obligation rather than a navigation question, and
inventing a scenario for it would pad the count without adding navigation.

`APG80-NODE-023` carries no fixture case. APG80 performs no external network
request, and no fixture case may contact one, so any fixture reference here would
misrepresent unexercised prose as exercised. The scenario still routes: Node's
exposure and local lifecycle of a network API is the profile's, while protocol
correctness, remote-system availability, security approval, and deployment are
not.

Several scenarios share a fixture case because one case genuinely spans them.
`APG80-FX-002` carries the whole module-mapping matrix that scenarios 003
through 007 navigate; `APG80-FX-013` carries the failure, signal, and scheduling
boundaries that scenarios 020 through 022 navigate; and `APG80-FX-014` carries
the target-role, package-manager, and completion boundaries that scenarios 014,
015, and 024 navigate. Splitting those cases to make the mapping one-to-one would
have separated artifacts whose evidence is a single observation. APG81A changes
only the qualification threat model and harness proof boundary: the same 24
navigation scenarios remain candidate-semantic evidence, while hostile same-UID
isolation routes separately and is not claimed by this register.
