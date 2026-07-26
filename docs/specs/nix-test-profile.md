# Specification: Nix Test Profile

Status: retained provisional by APG40. No ADR governs this
candidate: it proposes no owner-graph change beyond adding one independent
profile under the existing project model, and no genuinely consequential
architecture decision appeared during APG39 that the project model or this
specification cannot own. `nix-language-profile` and the process skills
remain unchanged owners of their contracts.

`nix-test-profile` is an APG capability name. No single universal upstream
Nix test command exists, and this specification never implies one.

## Claim-relative matrix

The profile's controlling model is claim-relative, never scalar. Every
engagement begins from the exact claim to be proved — including system,
platform, and the boundary it must not cross — and selects the already
project-owned surface that supports that claim. Surfaces are never ranked
weakest to strongest, and no surface's evidence subsumes another's.

## Surface taxonomy

The minimum distinguished surfaces, with their execution class:

| Surface | Supports | Cannot support | Execution and mutation class |
| --- | --- | --- | --- |
| evaluation/assertion | well-formedness and evaluation-time assertions | building, installing, running | evaluation only |
| derivation build | build-platform buildability | runtime, other platforms | build; durable store paths and logs |
| package check phase | in-build source-tree suite | installed output, targets the build platform cannot execute | build-time execution when enabled and executable |
| install-check phase | its exact installed-output contract | system runtime, targets the build platform cannot execute | build-time execution when enabled, executable, and nonempty |
| package-associated test derivation | that derivation's exact claim | anything outside that claim; no automatic participation in the package build | separately scheduled build |
| flake check | flake evaluation rules plus selected check buildability | fresh execution of substitutable checks, uniform deep checking of every recognized output, unselected systems | evaluation plus output-specific validation and selected check builds |
| Nixpkgs tester/helper | the helper's own documented claim | anything broader | the surface it generates |
| container runtime | behavior under container isolation | virtual-machine or real-host behavior | container execution |
| NixOS VM/system runtime | behavior on a booted test system | activation on a real host, deployment | virtual-machine execution |
| activation/deployment | outside this profile | never inferred from any surface above | requires separate authority |
| external-service behavior | outside this profile | never inferred from any surface above | requires separate authority |

For every selected surface the profile records: claims it may support, claims
it cannot, execution and mutation class, authority owner, platform and
system, store, log, and artifact effects, cleanup and rollback, and the
project-owned command that drives it.

## Sandbox and platform qualification

At exact Nix 2.35.1 source, the sandbox setting defaults to enabled on Linux
and on FreeBSD, and to disabled on every other platform. The two enabled
defaults are stated separately: Linux sandboxing isolates builds in private
process, mount, network, interprocess-communication, and hostname
namespaces; FreeBSD sandboxing is jail-based and recorded by the release
itself as less exercised than Linux. Neither platform's implementation is
described as the other's. For any other platform, a default is claimed only
when verified from the exact selected source.

A default is orientation evidence only. Effective behavior reflects system
configuration, reverse-ordered user configuration, `NIX_CONFIG`, command-line
overrides, trusted or accepted flake `nixConfig`, and daemon-owned settings.
Because `sandbox-fallback` defaults enabled and can disable requested Linux
sandboxing when namespace prerequisites are unavailable, runtime isolation
evidence must record effective client and daemon settings, fallback,
prerequisite availability, builder, and actual outcome. Relaxed mode exempts
fixed-output and chroot-opt-out derivations from sandboxing entirely;
fixed-output derivations are deliberately outside the private network
namespace; configured sandbox paths are bind-mounted with store-resident
closure exposure; local and remote builders, emulation, and binary caches
each change where and whether execution happened. Universal "sandboxed" or
"no network" claims are prohibited.

## Evidence and non-evidence

Source inspection is source evidence, never execution evidence. A cached or
substitutable output is not a fresh execution; remote or emulated success is
not local native verification; mocked behavior disclosed is Yellow and
represented as integrated is Red; an enabled check or install-check phase
that executes no target is not evidence; evaluation is never runtime proof;
and activation, deployment, and external-service claims are never inferred
from any in-profile surface. Completion reports name every check not run.

Package phases are gated by whether the build platform can execute the host
platform, not by build/host identity inequality alone. Package-associated
tests own only their derivation's exact claim, need not exercise the associated
package, and do not automatically participate in or change the package build.
Flake checking applies output-specific validation: selected `checks` may be
build targets, several standard classes receive their own checks,
`legacyPackages` is shallow, known community outputs may be deliberately
unchecked, and unknown outputs warn. Recognized does not mean uniformly
checked; checked does not mean built.

## Language pairing

Nix language semantics remain with `nix-language-profile`; driver-language
semantics with the applicable language profile; shell payload semantics with
the applicable shell profile; process judgment with the process skills. The
profile pairs with them only when independently material, attributes a mixed
Nix, driver, and shell owner once, and mandates no chain.

## Structural ownership

Signals are categorical: claim coherence, surface breadth, node and container
topology, driver, expression, and shell coupling, platform and system
breadth, purity, pinning, network, builder, and cache domains, resource and
lifecycle ownership, store, log, and artifact exposure, and independent
responsibilities. Each physical line belongs to exactly one physical bucket:
Nix expression, driver, or phase script. Semantic topology, variants,
responsibilities, exposure, and coupling remain independently inspectable and
are not additive physical counts.
Mutually exclusive generated arms are measured by actual execution ownership:
maximum across statically exclusive arms, summing only consumer
co-scheduled arms. Physical size, node count, matrix size, and expense alone
are never Orange or Red; every Orange or Red names a concrete authority,
truthfulness, safety, capacity, or maintainability risk.

## Resource and cost handling

An expensive surface — virtual machine, multiple nodes, emulation, remote
builder, large allocation, or a project-costly runtime — is at least Yellow
on cost and must be disclosed. A disclosed, capacity-safe expensive test is
not automatically Orange; Orange requires a concrete capacity or lifecycle
risk against a known budget.

## Protected data and authority

Evaluation, build, store mutation, container and virtual-machine execution,
activation, deployment, and external operations each require explicit
authority; source review never confers it. Protected data must not reach a
derivation, the store, a log, an artifact, a machine, or output; store-path
disclosure is classified by what the path reveals. Containers and virtual
machines must not be able to mutate an unintended host or service.

## Project-owned inputs

The repository owns Nix, Nixpkgs, and NixOS selection and versions, channels
and flake inputs, pinning, exact commands and attributes, selected systems
and platforms, the actual sandbox and impurity configuration, builders,
caches, emulation, node and resource budgets, expensive-test policy, worker
and CI policy, artifact retention, protected-data classification, consumers,
accepted exceptions, execution authority, validation, and rollback. A
stricter project policy always wins; a more permissive one relaxes only
profile defaults through an accepted bounded exception and never an
authority, protected-data, evidence-class, or false-pass stop.

## Source and version refresh

Calibration rests on exact Nix 2.35.1 tag sources — the local store settings
implementation, the flake-check command source, and the release notes — and
on the Nixpkgs/NixOS 26.05 release sources for phases, package-associated
tests, testers, and system tests. Refresh before any behavior-bearing claim
when the selected releases differ or when sandbox defaults or platform
implementations, flake-check semantics, phase defaults or target fallback,
cross-compilation gating, package-associated-test consumers, or tester
behavior materially change. APG text is independently written synthesis.

## Removal and rollback

Removal is candidate-independent: one mechanical change deletes the
canonical leaf and every integration surface the adopting phase created,
repairs surviving references to a retained owner or the project-owned
fallback, and preserves ADR, evaluation, and exit history. Removal changes no
target repository configuration, store, machine, or deployment, and grants no
execution authority.

## APG40 integration result

APG40 independently reverified exact Nix 2.35.1 and pinned Nixpkgs/NixOS 26.05
sources and rights, reviewed the bounded source corpus, and corrected every
accepted initial source-fact finding in one coherent forward pass. The
public-safe forty-scenario fixture, fresh corrected-state review, terminal
source-only disposition, and atomic integration passed, so the profile begins
`provisional`. No Nix parse, evaluation, build, store, cache, container,
virtual-machine, activation, deployment, or external operation was run or is
implied by retention.

## Falsification conditions

This specification is wrong, and must be revised or withdrawn, if:

1. exact current source contradicts the stated Linux or FreeBSD sandbox
   defaults or their implementation distinction;
2. independent reviewers cannot apply the claim-relative matrix or the
   categorical signals consistently, or the signals escalate ordinary
   maintained upstream tests;
3. a surface's stated cannot-support boundary is shown too narrow or too
   broad by executable evidence;
4. the single-attribution accounting cannot be applied to real mixed
   Nix/driver/shell owners;
5. ordinary tasks repeatedly need a coordination owner this specification
   says does not exist, which is new ADR evidence; or
6. the calibrated facts change across patch releases faster than the refresh
   condition can carry, making project policy the right owner instead.
