---
name: dockerfile-profile
description: Use when Dockerfile-specific judgment is material to parser directives, build stages, instruction forms, variable scope, build context, copies, mounts, cache behavior, file ownership, runtime metadata, platform behavior, or warning and crisis thresholds beyond repository policy.
---

# Dockerfile Profile

## Core principle

Apply Dockerfile-specific judgment only when the task materially depends on a
Dockerfile. Establish task authority, repository policy, the selected
Dockerfile frontend and builder, target platforms, context, stage target, and
validation boundary before relying on instruction behavior. Use the highest
justified `Green — routine`, `Yellow — caution`, `Orange — warning`, or
`Red — crisis / stop` response for the current coherent decision.

Own parser directives, stages, Dockerfile instruction forms, argument and
environment scope, build context and ignore rules, copies and additions,
BuildKit mounts, cache consequences, file ownership, platform-specific
Dockerfile behavior, generated image defaults, and Dockerfile-specific
structural warnings. Preserve image selection, dependency policy, live
operations, runtime orchestration, release policy, and external mutation
authority with their existing owners.

## Do not use

Do not use this profile for:

- ordinary application code with no material Dockerfile behavior;
- Compose-only, Kubernetes-only, or orchestrator-only work;
- generic shell review with no Dockerfile-specific boundary;
- a simple text edit whose Dockerfile semantics are already established;
- choosing Docker, a base image, tag, digest, registry, frontend, builder,
  target platform, package manager, shell, scanner, or dependency;
- selecting an exact build, scan, push, run, sign, publish, or deployment
  command;
- changing project-owned context, image, dependency, update, registry,
  platform, runtime, CI, attestation, signing, or release policy;
- authorizing a daemon, builder, registry, network, secret store, image,
  container, volume, host, or cloud mutation;
- treating a Dockerfile review as proof of a build, image, runtime, or
  publication outcome;
- automatic restructuring of a legacy Dockerfile; or
- structural action on generated, vendored, fixture, compatibility, or
  policy-owned artifacts before classification.

This profile does not grant authority to perform a Docker operation.

## Procedure

1. Establish authority and project inputs. Record the repository-owned
   Dockerfile path or generator, selected frontend, builder and version,
   Linux or Windows container boundary, build and target platforms, build
   context, ignore files, named contexts, target stage, base-image and update
   policy, dependency sources, shell, user policy, exact project checks,
   protected-data boundary, network and external-mutation policy, validation,
   and rollback. This profile does not choose or authorize those inputs.
2. Classify each affected artifact as a maintained hand-written Dockerfile,
   generated output, vendor-owned file, compatibility matrix, fixture,
   example, or policy artifact. Change the authorized generator or owner when
   applicable. Classification can change structural treatment but never
   suppresses a semantic Red stop.
3. Establish parser behavior before interpreting the body. Parser directives
   occupy the initial directive block and each supported directive may occur
   only once. After an ordinary comment, empty line, or instruction is
   processed, directive-shaped text is only a comment. Map `syntax`, `escape`,
   and version-supported `check` behavior; do not infer support from spelling.
4. Draw the stage graph. Each `FROM` starts a stage. Record stage names,
   inheritance, base references, requested platform, project-selected target,
   and every `COPY --from` or mount source. A global `ARG` may parameterize
   `FROM` but remains outside ordinary stage scope and must be redeclared
   inside a stage before later stage instructions consume it.
5. Trace Dockerfile replacement and command interpretation separately. Record
   `ARG` and `ENV` declaration, scope, inheritance, persistence, and use.
   Distinguish shell form from exec form: exec form supplies a JSON argument
   vector without implicit shell expansion, while shell form uses the selected
   platform shell. `SHELL` changes later shell-form `RUN`, `CMD`, and
   `ENTRYPOINT` behavior. When the chosen shell's quoting, pipeline, trap, or
   process semantics are independently material, pair
   `bash-language-profile` or the applicable language profile rather than
   duplicating it here.
6. Map the build context as an input and disclosure boundary. Identify the
   caller-selected context root, recursive contents, named or remote contexts,
   applicable `.dockerignore`, and any Dockerfile-specific ignore file. A
   Dockerfile-specific ignore file takes precedence over the root ignore file;
   within the applicable rules, the final matching rule wins. Confirm that
   intended sources remain available and that protected or unrelated material
   is absent from builder inputs or explicitly governed. The Dockerfile and
   applicable ignore file remain builder inputs even when ignore rules exclude
   them, although they cannot then be copied or bind-mounted from the ordinary
   context. Local-context source paths in `COPY` and `ADD` cannot escape the
   context root. Remote `ADD`, named contexts, images, and `COPY --from` stages
   use separately governed roots and trust boundaries.
7. Trace every transfer from governed source to exact stage and destination.
   Prefer `COPY` when it completely expresses a local, named-context, image, or
   stage-owned transfer. Treat remote `ADD`, Git sources, and automatic local
   archive extraction as materially broader behavior. Require project
   authority, source immutability or update policy, verification, ownership,
   mode, platform support, and rollback; do not rewrite automatically.
8. Map every `RUN --mount` by type, source, target, identity, ownership,
   sharing, lifetime, output path, and fallback. Bind writes are not ordinary
   output layers, cache contents are not correctness guarantees, tmpfs is
   transient, and secret or SSH mounts create temporary access boundaries. A
   secret mount does not prove the command avoided copying, printing,
   transforming, persisting, or exporting the value.
9. Review cache and reproducibility as instruction-specific behavior. Base
   identity and instruction text matter; `COPY`, `ADD`, and bind-mounted
   sources use metadata checksums that exclude modification time. An ordinary
   `RUN` cache match does not inspect changed external package state or files
   created inside the prior result. A secret value does not participate in the
   cache key, although secret identity and target properties can. Require a
   project-owned invalidation and clean-build path where correctness depends on
   mutable inputs or caches.
10. Trace filesystem and user effects by stage. Resolve `WORKDIR` chaining,
    source metadata, `COPY` or `ADD` ownership and mode, platform support,
    `USER` transitions, build-time effective user, final image user, and
    permission requirements. Do not infer final non-root behavior from an
    intermediate stage or from copied artifacts.
11. Review image and runtime-default metadata without taking runtime
    ownership. Map `EXPOSE`, `VOLUME`, `STOPSIGNAL`, `HEALTHCHECK`,
    `ENTRYPOINT`, `CMD`, `ONBUILD`, labels, environment, working directory,
    and user configuration. Establish forms, override behavior, signal
    forwarding, health status and output, volume initialization and mutation,
    and deferred downstream triggers. Runtime and orchestrator policy can
    replace or merge defaults and remains project-owned.
12. Establish platform truth. Map automatic build and target arguments, native
    versus target-stage execution, emulation, cross-compilation, path and
    escape rules, default shell, instruction options, ownership support, and
    the actual backend. Linux and Windows Dockerfile behavior is not
    interchangeable. Source text cannot prove that the selected worker,
    toolchain, exporter, or runtime supports the requested result.
13. Use parser or build-check output only within its versioned claim. Build
    checks can report warnings while the build still succeeds, and a check-only
    or error configuration can have different process behavior. Confirm which
    checks the selected frontend supplies and which mode the project owns.
    Lint or source evidence is not build, image, runtime, or artifact evidence.
14. Measure current and projected structure using repository tooling when
    available. Otherwise use the APG fallback contract below and label the
    measurement. Assign the highest structural or semantic level without
    double-counting correlated size signals.
15. Proceed proportionally for Green; inspect policy and bounded evidence for
    Yellow; require an accepted local decision, rationale, rollback, and
    adverse-case validation for Orange; stop a Red unsupported, ambiguous,
    mutable, unsafe, disclosed, falsely verified, unauthorized, or
    crisis-level boundary.
16. Pair independently with the applicable process, shell, language, security,
    package, test, runtime, and review owners. An authorized change can keep
    `implementing-with-test-discipline` primary; acceptance can keep
    `reviewing-and-verifying-repository-work` primary. This profile adds only
    materially Dockerfile-specific judgment.
17. Preserve stricter repository policy. Report the level, versions,
    platforms, stage and source graph, context and ignore assumptions, forms
    and variable scope, transfers, mounts, cache behavior, user and runtime
    metadata, structural signals, validation boundary, accepted exception if
    any, and rollback.

### Structural threshold contract

These defaults apply mainly to maintained hand-written Dockerfiles. They are
guidance signals, not Docker policy, architecture selection, base-image
selection, linter output, automatic enforcement, or build authority.

| Signal | Green — routine | Yellow — caution | Orange — warning | Red — crisis / stop |
| --- | ---: | ---: | ---: | ---: |
| Physical lines per Dockerfile | `<= 150` | `151–300` | `301–500` | `>= 501` |
| Logical Dockerfile instructions | `<= 20` | `21–40` | `41–70` | `>= 71` |
| Build stages | `1–3` | `4–6` | `7–10` | `>= 11` |
| Commands in one shell-form `RUN` | `<= 5` | `6–10` | `11–20` | `>= 21` |
| Distinct `ARG` and `ENV` names | `<= 6` | `7–12` | `13–20` | `>= 21` |
| Distinct `COPY` and `ADD` source domains | `0–2` | `3–4` | `5–7` | `>= 8` |
| Bind, cache, tmpfs, secret, or SSH mount families | `0–1` | `2–3` | `4–6` | `>= 7` |
| Instructions executing as root after the last explicit user transition | `0–2` | `3–5` | `6–10` | `>= 11` |
| Platform-conditional behavior families | `0–1` | `2–3` | `4–6` | `>= 7` |
| Independent responsibility families | `1` | `2` | `3` | `>= 4` |

Count physical lines after universal-newline decoding. Blank lines, comments,
parser directives, continuations, heredoc delimiters, and heredoc payload
count. A continued instruction counts once; directives, comments, and blank
lines do not count as logical instructions.

Count commands within shell-form `RUN` only when the selected interpreter and
complete static text can be parsed truthfully. Count independently sequenced,
conditional, subshell, and pipeline responsibility families rather than raw
tokens. If heredoc, interpolation, generated text, or an unknown interpreter
prevents a truthful consequential bound, classify the unknown as Orange;
representing it as verified is Red.

Count each distinct `ARG` and `ENV` name once while mapping scope separately.
Count independently governed source domains: local context family, named
context, named stage, external image, remote URL, Git source, local
archive-extraction family, and inline heredoc. A heredoc-backed `COPY` is one
instruction and one inline-source domain. Count each `ONBUILD` registration
once and also disclose its downstream responsibility.

Count mount families by independently governed contents, sharing, lifetime,
and purpose, not repeated syntax. For the root-execution signal, resolve the
selected target and stages statically reachable through inheritance,
`COPY --from`, or a stage-backed mount. Each `FROM` resets user state to its
base configuration. Count stage-local `RUN` instructions executed with
effective root identity after the latest stage-local `USER` transition,
starting from verified base-image user state. Measure each reachable stage
separately and use the maximum; do not sum stages. A final-stage non-root
transition cannot erase root work in a reachable build stage. If no target is
selected, measure each statically selectable maintained target and use the
maximum. Report maintained unreachable stages separately. An unknown
consequential base user, target, or reachability edge is Orange; representing
it as verified is Red. Disclose final image user separately.

For statically bounded platform variants, measure each variant and use the
maximum rather than summing mutually exclusive duplicates. Count platform
divergence separately. Dynamic consequential behavior that cannot be bounded
is Orange; representing unverified platform support or success as established
is Red.

One responsibility family is one independently accepted build-definition
outcome with its own change and rollback lifecycle, not each Dockerfile
mechanism. A conventional builder stage, one governed toolchain input, one
copied application artifact, and one runtime stage with defaults are one
cohesive responsibility family, not four, when they share one product owner
and lifecycle. Count separately when images, selectable targets,
independently released artifacts, external-input policies, platform branches,
or runtime-default contracts can change and roll back independently.
Generated, vendored, compatibility, fixture, and policy artifacts retain their
producer or repository ownership. A repository-accepted cohesive generated or
vendor matrix may lower only the physical-line response by one level; it
cannot relax a semantic Red stop.

A six-instruction, two-stage application Dockerfile with one governed
toolchain image, one build step, one cross-stage application copy, and one
fixed runtime entrypoint is one cohesive responsibility family and remains
structurally Green when its other signals are Green. An application image plus
an independently operated migration target is two families and Yellow on this
signal. Four independently released target images with distinct owners or
rollback lifecycles are four families and Red even if line, instruction, and
stage counts are otherwise Green.

A reachable build stage with three root-executed `RUN` instructions has a
root span of three even when the final runtime stage selects a non-root user.
The stages are not summed, and the final transition does not erase the
build-stage count. Unknown base-user or target reachability remains Orange
until established.

Three materially coupled Yellow signals normally justify Orange. Two
materially coupled Orange signals affecting the same owner are presumptively
Red unless a cohesive-artifact rationale, repository acceptance, evidence,
validation, growth bound, and rollback justify retaining Orange. One Red
signal remains Red. Do not aggregate unrelated findings into a score.
Physical-line, instruction, and stage counts are often correlated and do not
stack automatically.

An existing Red legacy Dockerfile may receive the smallest safe authorized fix
when it adds no independent responsibility or meaningful structural growth
and records a decomposition or follow-up boundary. New responsibility remains
Red. A bounded exception requires repository acceptance, evidence, validation,
an owner, growth limit, refresh condition, and rollback. It cannot relax
protected-data, support, truthfulness, or authority stops.

Rollback restores the prior authorized Dockerfile or generator output, context
and ignore assumptions, stage graph, variables, mounts, user transitions, and
platform branches, then remeasures the static contract. It grants no live
Docker authority.

### Dockerfile semantic response guide

- Dockerfile frontend 1.25.0, BuildKit 0.31.2, and OCI Image Spec 1.1.1 are
  calibration points, not selected project dependencies or a universal
  compatibility matrix. `docker/dockerfile:1` is mutable because it selects
  the latest stable 1.x frontend at build time. Exact stable pins, labs
  channels, and prereleases have different update and support boundaries.
- Only `ARG` may precede the first `FROM`. A global `ARG` can parameterize
  `FROM` but must be redeclared inside a stage for ordinary later use.
  `ARG` starts at declaration and follows stage inheritance; `ENV` persists in
  image configuration and descendant stages. `ARG` and `ENV` are not
  protected-value transports.
- A named multi-stage graph is Green when the selected target, dependencies,
  and exact artifact transfers are unambiguous. Missing, wrong, dynamic, or
  ambiguous `COPY --from` ownership is Red until resolved. Unnecessary stage
  proliferation begins at least Yellow.
- Shell form is deliberate only when the selected platform shell, expansion,
  quoting, pipelines, and failure behavior are established. Exec form is
  Green for a fixed supported argument vector but does not provide shell
  expansion or builtins. Untrusted source-to-shell flow is Red.
- Context review must reconcile caller selection, ignore precedence, final
  match behavior, required sources, protected material, and transfer size.
  An ignored required source is Orange until reconciled. Protected context
  exposure is Red. A narrower context or `COPY` preference does not authorize
  restructuring.
- Remote `ADD` is Red without source authority, immutability or update policy,
  verification, and rollback. Deliberate local archive extraction is Yellow or
  Orange according to ownership and adverse-case evidence.
- Package-index refresh and installation belong in one owned transaction only
  when the selected package manager and project policy require it. Do not
  universalize that pattern. A long `RUN` chain is Orange when it obscures
  command failure or responsibility ownership.
- Secret and SSH mounts reduce ordinary layer ingress but do not establish safe
  command data flow, log output, artifacts, cache, provenance, or exports.
  Copying, printing, persisting, or exporting protected data is Red.
- Cache and bind mounts require contents, sharing, mutation, invalidation,
  cleanup, and a clean-build fallback. Correctness that silently depends on a
  retained cache is Red. The absence of mount contents from a normal output
  layer is not proof that a command emitted nothing elsewhere.
- `WORKDIR` affects later build and runtime-default instructions and relative
  paths can chain. `USER` affects later build execution and image runtime
  defaults; one group can suppress supplementary groups. Resolve stage,
  platform, source metadata, ownership, mode, and permissions together.
- `EXPOSE` records intended port metadata but does not publish a host port.
  `VOLUME` declares a runtime mount point and has builder-dependent
  post-declaration mutation behavior. `STOPSIGNAL` supplies a default that
  runtime configuration can override.
- Only the last `HEALTHCHECK` applies. A false-pass, unsafe timeout, or
  protected diagnostic output is Red. `ONBUILD` stores downstream triggers
  whose context, source, ordering, and mutation ownership must be explicit;
  hidden consequential downstream behavior is at least Orange.
- Exec-form `ENTRYPOINT` receives runtime arguments and can pair with exec-form
  `CMD` defaults. Shell-form entrypoints normally interpose a shell and can
  discard `CMD` or runtime arguments and fail to forward signals. Establish
  the exact form and override matrix rather than inferring runtime behavior.
- OCI image configuration standardizes several runtime-default fields but not
  every Dockerfile semantic. Health-check behavior, `ONBUILD`, `SHELL`, layer
  production, exporter behavior, attestations, registry policy, signing, and
  runtime override remain separately owned.
- Parser and build checks are versioned configuration evidence. Source review
  cannot prove that an image builds, that dependencies are available, that the
  result runs on a target platform, or that output and attestations contain no
  unintended data.

### Source and maintenance boundary

This profile was inspected on 2026-07-24 against the Apache-2.0 Docker
documentation and BuildKit sources associated with stable Dockerfile frontend
1.25.0 and BuildKit 0.31.2, plus the Apache-2.0 OCI Image Spec 1.1.1. These are
calibration facts, not project-selected versions or proof of a supported
combination. APG copies or adapts no upstream prose, source, example, or table;
this procedure is independently written synthesis.

Refresh before a behavior-bearing correction, maturity review, or publication
when the stable frontend, builder behavior, instruction set, build checks,
context or ignore rules, cache, mount, Windows, platform, provenance, OCI
configuration, licensing, or representative false-escalation evidence
materially changes.

Removal is candidate-independent. It must delete the leaf, flat projection,
catalog and capability-map entries, current-development release policy, strict
test inventory, focused test, and public scenario fixture while preserving
evaluation and exit history. The project-scoped projection owner and its
fixtures must remove only `dockerfile-profile`, preserve every other live
skill, and recompute all surviving skill, catalog, projection, route, fixture,
and test counts. Derive counts from the resulting live inventories. A raw
APG33 commit revert is not valid rollback because it would restore historical
counts and integration state. No private guidance was migrated, so rollback
restores none of it.

## Project-owned parameters

The target repository owns whether to use Docker and a Dockerfile; Dockerfile
path or generator; base image, registry, tag, digest, update policy, and
provenance; frontend, builder, Engine, Buildx, and BuildKit versions; Linux or
Windows containers; build and target platforms; context roots, ignore files,
named or remote contexts; target stages; shell and package manager; dependency
sources and exact commands; user, group, ownership, mode, ports, volumes,
health, signal, entrypoint, command, and runtime policy; mount identities and
sharing; network, cache, secret, SSH, and entitlement policy; scanners,
exporters, SBOM, attestations, signing, registries, CI, publication, rollback,
protected data, external mutation, release, and destructive-action authority.

## Evidence and completion

When material, report the Dockerfile profile level; exact frontend, builder,
platform, context, target, and policy basis; parser directives; stage and
source graph; argument and environment scope; shell and exec forms; ignore
rules; copy and add ownership; mounts, cache, protected-data flow, and
clean-build fallback; work directory, user, permissions, and runtime metadata;
structural and semantic signals; project checks actually run; unsupported or
unverified boundaries; accepted exception if any; and rollback.

Green needs project checks. Yellow needs focused inspection. Orange needs an
accepted local decision and adverse-case validation. Red records the stopped
unsupported claim, ambiguity, mutable or unverified input, wrong artifact,
protected-data path, unsafe runtime default, false completion claim,
unauthorized mutation, or growth and the condition required before
reconsideration. Static review, a parser, lint, or build checks do not become
build, artifact, runtime, or publication evidence.

## Stop or escalate

Stop or escalate when effective frontend, parser, builder, platform, or feature
support is unverified; stage, context, source, ignore, copy, user, ownership,
or target behavior can produce the wrong artifact; mutable or remote input
lacks required authority and verification; untrusted data reaches a shell;
protected data can enter image configuration, history, layers, cache,
provenance, logs, health output, or exported artifacts; cache or mount behavior
can silently control correctness; final-root, entrypoint, signal, health,
volume, or downstream-trigger behavior remains unsafe; source or lint evidence
is represented as build or runtime success; a Dockerfile can mutate
destructive or consequential external state without exact authority; or
meaningful Red growth lacks decomposition or an accepted bounded exception.

## Common mistakes

- Triggering for ordinary application, Compose, orchestration, or shell work.
- Selecting Docker, images, versions, platforms, dependencies, commands, or
  runtime and release policy.
- Treating a late parser-directive-shaped comment as an active directive.
- Assuming a global `ARG` is available throughout every stage.
- Treating exec form as shell syntax or shell form as a fixed argument vector.
- Ignoring context selection, Dockerfile-specific ignore precedence, or a
  required file excluded by `.dockerignore`.
- Using remote `ADD` without project authority and immutable verification.
- Treating a secret mount, cache mount, or bind mount as proof of safe data
  flow or reproducibility.
- Assuming a mutable base or package source is current, compatible, or
  reproducible.
- Inferring final user, permissions, target support, signal behavior, health,
  persistence, or downstream effects from syntax alone.
- Treating source review, lint, build checks, or OCI metadata as a successful
  build, correct image, or safe runtime.
- Duplicating shell semantics instead of pairing the applicable language
  profile when material.
- Using structure levels as permission, maturity, or automatic rewrite rules.
