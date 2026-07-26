# APG33 Dockerfile Profile

## Objective and disposition

APG33 evaluates one bounded new-skill candidate: `dockerfile-profile`. The
candidate owns materially Dockerfile-specific judgment without selecting
Docker, images, registries, tags, digests, frontends, builders, platforms,
dependencies, shells, project commands, runtime policy, release policy, or
live-operation authority.

The lifecycle evidence supports provisional retention. No consequential project
decision requires ADR 0025.

## Current source and rights

Primary sources were inspected on 2026-07-24:

- current official Docker documentation and its Dockerfile, context, cache,
  multi-platform, build-check, secret, and attestation guidance;
- stable Dockerfile frontend 1.25.0 and BuildKit 0.31.2 documentation, source,
  and release records; and
- OCI Image Spec 1.1.1 image-configuration guidance.

Docker documentation, BuildKit, and OCI Image Spec are Apache-2.0. No
applicable top-level notice payload was found in the inspected roots. APG uses
the versions as calibration evidence, not project requirements or a universal
compatibility matrix. The profile is independently written synthesis and
copies or adapts no upstream prose, code, examples, or table structure.

The calibration preserves several version and truthfulness boundaries. The
`docker/dockerfile:1` frontend channel is mutable; labs and prerelease behavior
is not the stable baseline. Parser-directive position controls whether
directive-shaped text is active. Global and stage argument scopes differ.
Linux and Windows behavior is not interchangeable. Build checks, source
inspection, and image-configuration review do not prove a successful build,
correct image, supported platform, safe runtime, or complete artifact.

## Ownership and scenarios

The profile triggers only when parser directives, stages, Dockerfile
instruction forms, argument or environment scope, build context and ignore
rules, copies and additions, BuildKit mounts, cache consequences, file
ownership, platform behavior, or Dockerfile-generated image defaults
materially control a decision.

Ordinary application code, Compose-only or orchestrator-only work, generic
shell review, image and dependency selection, project commands, runtime
orchestration, registry administration, attestations, signing, release policy,
and live Docker operations remain non-triggers or project-owned inputs. Shell
profiles retain shell semantics; repository and operator policy retains image,
dependency, platform, runtime, protected-data, and external-action authority.

Forty frozen families cover positive and non-trigger decisions; frontend and
parser behavior; Linux and Windows boundaries; mutable and digest-pinned
bases; stage and argument scope; shell and exec forms; context and ignore
rules; copies and additions; mounts, cache, protected data, and
reproducibility; ownership and final-user behavior; runtime metadata;
structural classification; stricter policy; and external-action authority. A
mirrored unit contract failed first before the candidate existed and passes
against the integrated candidate.

## Structural contract

The profile supplies Green/Yellow/Orange/Red fallback signals for physical
lines, logical instructions, stages, commands in one shell-form `RUN`,
distinct `ARG` and `ENV` names, transfer-source domains, mount families,
root-execution span, platform-condition families, and independent
responsibilities.

Measurement distinguishes physical lines from logical instructions, counts
heredoc and `ONBUILD` ownership explicitly, refuses to invent a command count
for an unknown interpreter, uses the maximum of mutually exclusive platform
variants, and avoids automatically stacking correlated line, instruction, and
stage signals. Generated or vendor-owned cohesion can lower only one physical-
line response; semantic stops remain controlling.

Required Red stops remain semantic: unsupported frontend, builder, platform,
or feature claims; consequential mutable or remote input without project
authority and verification; untrusted source-to-shell flow; protected-data
ingress or output; wrong stage, source, context, copy, user, ownership, or
artifact behavior; unsafe final-user or runtime-default behavior; false build
or runtime proof; unauthorized external mutation; and crisis-level
undecomposed ownership.

## Integration

The retained development shape is:

- 24 canonical skills, 24 catalog rows, and 24 flat projections;
- 14 stable and 10 provisional rows;
- 22 general-router entries, including the Dockerfile profile and the
  ChatGPT-manager subrouter;
- 1 ChatGPT-local entry; and
- 23 checked route edges in total.

The current-development release policy, release validator, and strict test
inventory include the new leaf, projection, scenario fixture, and mirrored
contract. Public and active v0.3.0 remain unchanged at 19/19/19.

## Candidate correction and validation

The candidate uses one behavior-bearing correction. Initial fresh review
identified an overbroad local-context statement, contradictory shell-selection
ownership, false-Red responsibility counting for a cohesive multi-stage
product image, and ambiguous multi-stage root-execution aggregation. The
correction scopes local traversal separately from remote, image, named-context,
and stage roots; records the still-transmitted Dockerfile and ignore-file
boundary; returns shell selection to the project while retaining Dockerfile
`SHELL` effects; coalesces mechanisms that share one product owner and rollback
lifecycle; and measures root `RUN` spans per reachable stage using the maximum.
Concrete Green, Yellow, Red, and multi-stage root cases now bound the rules.
The correction changes no frozen outcome or numeric band.

Two capitalization-only focused assertions were aligned with candidate sentence
starts; they changed no candidate behavior or frozen outcome. A non-blocking
integration-record claim was narrowed from byte-identical punctuation to
semantic trigger identity.

The focused executable contract reads its scenario outcomes only from the
public-safe fixture; publication-excluded source, threshold, and review records
explain the contract but are not required by the public candidate.

Validation covers the failing-first and passing mirrored contract, skill
library, router and catalog, exact projection, release policy, strict
inventory, affected unit and integration selections, current and public-v0.3
checkers, Python compilation, Markdown and links, privacy and durable identity,
whitespace, and a disposable current-development candidate without
publication. Fresh non-author source, rights, boundary, safety, structural,
integration, provenance, rollback, and complete-diff reviews accept the
corrected result. Readiness, smoke, release, publication, and Docker-operation
suites remain outside APG33.

## Rollback and future boundary

Rollback removes the canonical leaf, flat projection, catalog row, general-map
entry, current-development release-policy and validator entries, inventory
row, focused test, scenario fixture, and current-surface test expectation
together while preserving this evaluation and the exit history. No private
guidance was migrated. The project-scoped projection owner and its fixtures
remove only Dockerfile, retain the APG32 Minitest repair, and expect 23 current
leaves; the general router returns to 21 entries and the ChatGPT-local router
remains at one. A raw APG33 commit revert is not rollback because it would
restore stale 22-leaf and 20-route expectations.

APG34 may begin only after APG33 is terminal, defect-free, committed, fully
reported, pushed, remote-equal, and accepted by fresh non-author review. APG34
owns only the separately bounded Vagrantfile profile lifecycle. No phase after
APG34 is authorized.
