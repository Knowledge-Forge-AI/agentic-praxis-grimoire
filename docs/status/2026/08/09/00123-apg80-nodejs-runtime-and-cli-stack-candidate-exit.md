# APG80 Node.js Runtime and CLI-Stack Candidate Exit

Phase ID: `APG80`

## Result

Complete — narrow Node.js runtime and CLI-stack candidate authored, ADR 0046
Proposed, twenty-four navigation scenarios and fourteen-case target-first
fixture complete, integration absent, and APG81 recommended but unbegun.

## Current state

- One narrow reusable `nodejs-runtime-profile` candidate is authored on a Claude
  authoring branch with its specification and a navigation-only coverage record.
  It is `authored-proposed-unintegrated`.
- ADR 0046 is Proposed. APG80 neither accepted nor rejected it.
- The candidate consumes runtime roles and selects none. It hard-codes no Node
  version and treats an available executable, a selected family, a dependency
  engine constraint, a declared range, a continuous-integration release line, an
  exact version, flags, a platform, an invocation, and an observation as
  distinct facts.
- Explicit non-owners are ECMAScript and TypeScript semantics, package-manager
  behavior, shell grammar, operating-system policy, network protocol and
  security outcomes, browser and Web-platform semantics, build transformation,
  test-framework semantics, readiness, publication, and deployment.
- Node structural policy is deferred. No numeric threshold exists and no
  migration is recommended in either direction.
- Twenty-four scenarios `APG80-NODE-001` through `APG80-NODE-024` cite
  twenty-nine of the leaf's thirty stable clauses; `NODE-ROLLBACK` is
  identified as operational-only.
- The APG-owned fixture carries fourteen cases `APG80-FX-001` through
  `APG80-FX-014` with thirty-eight separately recorded case artifacts. It needs
  no installation, contacts no network, invokes no shell, touches no target, and
  writes only inside a caller-injected directory.
- A bounded scratch-only authoring smoke ran on the exact APG79E qualification
  engine. Every observation is bounded to that executable, version, platform,
  architecture, flag set, command, and input. It is not a maintained test, an
  oracle, target-execution proof, or an integration gate.
- Node integration is absent. No catalog row, projection, maturity row,
  capability route, project selection, release owner, or test-inventory row
  changed. The candidate branch is transitionally 33 canonical leaves / 32
  catalog rows / 32 projections; the mainline remains exact APG79E at 32/32/32.
- Known debt is exactly CSS-QD-001 through CSS-QD-005 and JS-QD-001 through
  JS-QD-005, unchanged. No Node debt was added or accepted.
- JavaScript, CSS, TypeScript, and Markdown remain provisionally integrated with
  their lifecycles unchanged. Test262 remained unused as a corpus or oracle and
  its source-role record is unchanged.
- Both read-only targets were freshly pinned and remain unmodified and
  unexecuted. No package-manager install or target script ran. Corrected public
  and active v0.4.0 are unchanged.

## Boundary

APG81 is recommended, without beginning, as Codex Node.js runtime and CLI
iterative hardening and provisional integration at exit 00124 under ADR 0046. No
Node integration, stable maturity, readiness, publication, deployment, target
execution, APG81, or successor work is authorized by this exit.
