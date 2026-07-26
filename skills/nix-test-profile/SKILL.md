---
name: nix-test-profile
description: Use when Nix test judgment is material to selecting which already-selected testing surface can prove an exact claim, package check and install-check behavior, flake checks, Nixpkgs or NixOS test ownership, test-evidence qualification across sandbox, store, builder, or cache boundaries, or Nix-test-specific structural review.
---

# Nix Test Profile

## Core principle

`nix-test-profile` is an APG capability name. There is no single universal
upstream Nix test command, and none is claimed here.

Apply Nix test judgment only when the task materially depends on which testing
surface carries a claim. Begin from the claim, not from a ladder of surfaces:

```text
What exact claim must be proved?
```

Then select the already project-owned surface that can prove that claim, and
record what the selected surface cannot support. Surfaces are never ranked
weakest to strongest: a virtual-machine test proves nothing extra about
evaluation, and evaluation proves nothing about runtime. Use the highest
justified `Green — routine`, `Yellow — caution`, `Orange — warning`, or
`Red — crisis / stop` response, and require a named concrete risk for every
Orange or Red.

Leave Nix expression, module, derivation, flake, and purity semantics to
`nix-language-profile`, driver-language and shell semantics to the applicable
language profile, and all evaluation, build, store, machine, activation,
deployment, and external authority to the repository and the human operator.

## Do not use

Do not use this profile for:

- generic Nix language semantics with no test-surface decision, owned by
  `nix-language-profile`;
- dependency or input selection, pinning policy as such, or exact command,
  attribute, system, builder, or cache selection, which are project-owned;
- ordinary package implementation with no test-surface decision, or simple
  source edits governed by a complete repository-local policy;
- Python semantics in a driver script alone, or shell semantics in a phase
  script alone, owned by the applicable language profile;
- activation or deployment execution, which is outside this profile;
- generic implementation, debugging, planning, or review procedure; or
- authorizing evaluation, build, store mutation, container or virtual-machine
  execution, activation, deployment, or external services.

Pair with a language or process profile only when it is independently
material. No pairing is mandatory.

## Procedure

1. State the exact claim in one sentence, including the system, platform, and
   the boundary it must not cross.
2. Establish task authority, repository policy, pinned inputs, selected
   systems, effective client and daemon configuration, sandbox prerequisites
   and actual outcome, builder, cache, exact commands, and rollback. Source
   review is not execution authority.
3. Select the surface whose supported claim matches, using the matrix below.
   Record the claims it can support, the claims it cannot, its execution and
   mutation class, its authority owner, its platform and system, its store,
   log, and artifact effects, its cleanup and rollback, and the project-owned
   command that drives it.
4. Classify the artifact as maintained test, helper, driver, legacy,
   generated, or vendored. Classification never suppresses a semantic Red.
5. Inspect purity and pinning, sandbox and network exposure with exact
   platform qualification, systems and platforms, store and log content,
   resource cost against the known budget, cleanup and rollback, and whether
   any required test is skipped or empty.
6. Assign the highest justified level using the signal contract below. Every
   Orange or Red must name its concrete risk; no line, node, matrix, or cost
   figure justifies a level by itself.
7. Proceed proportionally for Green; inspect policy and evidence for Yellow;
   require an accepted local design, rationale, rollback, and focused
   validation for Orange; stop a Red authority, evidence-class, false-pass,
   exposure, or unbounded-resource condition.
8. Preserve stricter repository policy. Never relax a superior authority,
   protected-data, evidence-class, false-pass, or destructive-action stop.
9. Report the claim, the selected surface, what it cannot support, level,
   named risks, unrun checks, exception if any, and rollback.

### Claim-to-surface matrix

Each surface proves its own claim and nothing more. Selection is by claim,
never by rank.

| Claim to prove | Surface | It cannot support |
| --- | --- | --- |
| The expression is well-formed and its assertions hold | Evaluation and module assertions | that anything builds, installs, or runs |
| A derivation builds on the build platform | Derivation build | runtime behavior, or another platform |
| The source tree's own suite passes during the build | Package check phase | installed-output behavior, or a target the build platform cannot execute |
| The installed output passes the install-check contract | Package install-check phase | system runtime behavior, or a target the build platform cannot execute |
| One package-associated test derivation's exact claim holds | Package-associated test derivation | anything outside that derivation's claim; it does not automatically join or change the package build |
| The flake evaluation rules hold and selected declared checks are buildable | Flake check | fresh execution of substitutable checks, uniformly deep checking of every recognized output, or systems not selected |
| One narrow, named property holds | Nixpkgs tester or helper | any claim broader than the helper's own |
| A service behaves under container isolation | Container runtime test | virtual-machine or real-host behavior |
| A service behaves on a booted NixOS system | NixOS virtual-machine or system runtime test | activation on a real host, or deployment |
| A real host activates a configuration | Activation and deployment — outside this profile | never inferred from any surface above |
| An external service behaves | External-service claim — outside this profile | never inferred from any surface above |

Inferring an activation, deployment, or external-service result from a build,
check, container, or virtual-machine result is a Red evidence-class stop.
Mocked behavior disclosed as mocked is Yellow; mocked behavior represented as
integrated is Red.

### Flake checks

Flake checking evaluates the flake and applies output-specific validation.
Selected derivations under `checks` are build targets unless building is
disabled, but a substitutable result may satisfy buildability without fresh
execution. Other standard output classes receive their own checks: several
derivation, application, overlay, module, configuration, template, and bundler
classes are validated; `legacyPackages` is inspected shallowly; some known
community outputs are deliberately left unchecked; and unknown outputs
produce warnings. Recognized does not imply uniformly checked, and checked
does not imply built. An evaluate-only mode avoids check builds, and a separate
flag widens system selection. Command, system selection, and cache policy are
project-owned.

### Sandbox, network, and platform

Every isolation claim must carry its exact platform, setting, derivation-kind,
and builder qualifiers. Unqualified "sandboxed" or "no network" claims are
Red. At exact Nix 2.35.1 source:

- The sandbox setting defaults to enabled on Linux and on FreeBSD, and to
  disabled on every other platform. State the two enabled defaults
  separately: the Linux implementation isolates builds in private process,
  mount, network, interprocess-communication, and hostname namespaces, while
  the FreeBSD implementation uses jail-based sandboxing, which the release
  itself records as less exercised than Linux. Do not describe one platform's
  implementation as the other's merely because both default on.
- For any other platform, claim a default only when it is verified from the
  exact selected source; otherwise report the gap.
- A default is orientation evidence only. Effective configuration depends on
  system configuration, reverse-ordered user configuration, `NIX_CONFIG`, and
  command-line overrides; trusted or accepted flake `nixConfig` and
  daemon-owned settings further qualify the result. Completion evidence for a
  runtime isolation claim must record the effective client and daemon
  configuration, not infer it from an upstream default.
- `sandbox-fallback` defaults enabled. On Linux, when sandboxing is requested
  but required mount or PID namespaces are unavailable, fallback may disable
  sandboxing. Record prerequisite availability, fallback policy, builder, and
  the actual sandboxed outcome; configured intent alone does not prove
  isolation.
- Under the relaxed setting, fixed-output derivations and derivations marked
  to opt out of the chroot do not run in sandboxes at all.
- Fixed-output derivations are deliberately left outside the private network
  namespace so they can reach the network; qualify loopback versus external
  network access by platform, setting, and derivation kind.
- Configured sandbox paths are bind-mounted in, and a store-resident path
  brings its closure, widening what the build can see.
- Local and remote builders, emulation, and binary caches each change where
  and whether execution happened. A cached output is not a fresh execution,
  and remote or emulated success is not local native verification.

### Package phases and associated tests

In the generic build environment, the check and install-check phases are
skipped by default and must be enabled explicitly. The check phase runs the
source tree's own suite during the build, with check inputs folded into the
build when enabled; when the check target is unset it falls back to a
conventional target, then an alternative, then does nothing — so an enabled
phase can silently run no tests, a false pass when the test was required. The
install-check phase can also silently run no tests when no custom phase,
Makefile, or default install-check target exists. Both phases are additionally
gated on whether the build platform can execute the host platform; differing
build and host identities do not by themselves prove that execution is
disabled. These are the generic environment's defaults; other builders define
their own phase behavior, and generalizing one builder's defaults to another
is Red.

Package-associated tests are separate derivations whose exact own claim
controls; they need not depend on or test the associated package. They do not
automatically participate in or change the package build. A named consumer may
schedule them independently or alongside other work, so name that consumer
rather than asserting what consumers in general do. A Nixpkgs tester or helper
is a constructor role; the surface it generates determines the evidence class,
and it proves only its own documented claim.

### Structural signal contract

Measure per maintained Nix test owner, assigning each physical line to exactly
one physical bucket: Nix expression, driver, or phase script. Semantic
topology, variants, responsibilities, exposure, and coupling remain
independently inspectable; they are not additive physical-line counts.
Signals are categorical: claim coherence, surface breadth, node and container
topology, driver, expression, and shell coupling, platform and system breadth,
purity, pinning, network, builder, and cache domains, resource and lifecycle
ownership, store, log, and artifact exposure, and independent
responsibilities.

Physical size, node count, matrix size, and expense alone are never Orange or
Red. An expensive test — a virtual machine, multiple nodes, emulation, a
remote builder, a large allocation, or a runtime the project treats as costly
— is at least Yellow on cost and its cost must be disclosed, but a disclosed,
capacity-safe expensive test is not automatically Orange; Orange requires a
concrete capacity or lifecycle risk against a known budget. Measure mutually
exclusive generated arms by actual execution ownership: take the maximum
across statically exclusive arms and sum only arms the actual consumer
co-schedules. Attribute a mixed Nix, driver-language, and shell owner once,
and route each language's semantics to its own profile.

Calibrated counterexamples: one large cohesive upstream virtual-machine test
may remain Yellow; a generated mutually exclusive matrix is measured by its
actual execution ownership, not blindly summed; an expensive but disclosed,
capacity-safe test is not automatically Orange; and a small, cheap test whose
evidence claim overstates its surface may be Red regardless of size.

### Source and maintenance boundary

This profile was calibrated from exact Nix 2.35.1 tag sources — including the
local store settings implementation, the flake-check command source, and the
release notes — and from the Nixpkgs and NixOS 26.05 release sources for
phases, package-associated tests, testers, and system tests. Nix is
LGPL-2.1-or-later; Nixpkgs and NixOS are MIT subject to component exceptions.
APG copies or adapts no upstream expression or code; this profile is
independently written synthesis. No Nix parse, evaluation, build, flake
check, store or cache operation, container or virtual-machine test,
activation, or deployment was run to produce it.

Refresh before any behavior-bearing claim when the selected Nix or
Nixpkgs/NixOS release differs from the calibration, or when sandbox defaults
or platform implementations, flake-check semantics, phase defaults or target
fallback, cross-compilation gating, package-associated-test consumers, or
tester behavior materially change. Removal of this profile is
candidate-independent: it deletes the canonical leaf and every integration
surface the adopting phase created, repairs surviving references to a
retained owner or the project-owned fallback, and changes no target
configuration, store, or deployment.

## Project-owned parameters

The repository owns Nix, Nixpkgs, and NixOS selection and versions, channels,
flake inputs and pinning, exact commands and attributes, selected systems and
platforms, the actual sandbox and impurity configuration, builders, caches,
emulation, node and resource budgets, expensive-test and capacity policy,
worker and CI policy, artifact retention, protected-data classification,
consumers, accepted exceptions, execution authority, validation, and
rollback.

## Evidence and completion

When material, report the exact claim, the selected surface, what that
surface cannot support, the level with each Orange or Red risk named, system
and platform qualifiers, effective client and daemon configuration, sandbox
prerequisites, fallback, actual isolation outcome, builder, and cache behavior
whenever a runtime claim depends on them, purity and pinning evidence,
resource cost against the known budget, exposure handling, exception if any,
and rollback. Distinguish source evidence from runtime evidence, name every
check that was not run, and never convert source review into execution
evidence.
Completion never claims integration, maturity, compatibility, publication, or
deployment.

## Stop or escalate

Stop or escalate when evaluation, build, virtual-machine, container, store,
activation, deployment, or external mutation lacks explicit authority; an
evidence class is overstated for the surface that produced it; sandbox,
platform, or network behavior is represented without exact qualification; a
required test is omitted, skipped, or empty; an unpinned, impure, networked,
remote-builder, or cache boundary is unaccepted; protected data can reach a
derivation, the store, a log, an artifact, a machine, or output; an
unsupported system or platform is represented as verified; a container or
virtual machine can mutate an unintended host or service; activation or
deployment success is inferred from another surface; mocked behavior is
represented as integrated; test lifecycle or resources cannot be bounded; or
crisis-level claim ownership lacks decomposition or an accepted bounded
exception.

## Common mistakes

- Ranking unlike surfaces on one scalar ladder instead of selecting by claim.
- Claiming flake checking builds every derivation-valued output.
- Stating that builds are sandboxed by default without naming the platform,
  lumping FreeBSD's default under a Linux-only claim, or describing Linux
  namespace isolation as FreeBSD jail behavior or the reverse.
- Inferring actual isolation from an upstream sandbox default or configured
  intent, or omitting effective client/daemon precedence, `sandbox-fallback`,
  prerequisites, builder, and actual outcome from runtime evidence.
- Forgetting that relaxed mode exempts fixed-output and chroot-opt-out
  derivations entirely.
- Assuming check phases run by default or are disabled solely because build and
  host identities differ, generalizing across builders, or treating an enabled
  check or install-check phase with no executed target as evidence.
- Universalizing package-associated-test consumers instead of naming the
  actual consumer.
- Summing mutually exclusive generated arms instead of measuring actual
  execution ownership, or escalating an expensive but disclosed,
  capacity-safe test to Orange without a concrete capacity risk.
- Reporting a cached or remote result as a fresh local execution, or
  inferring activation or deployment from a build, container, or
  virtual-machine result.
- Double-counting one physical line across physical buckets, confusing
  semantic dimensions with additive line counts, or escalating on line or node
  count alone.
