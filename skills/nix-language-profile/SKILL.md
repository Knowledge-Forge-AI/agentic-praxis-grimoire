---
name: nix-language-profile
description: Use when Nix-specific judgment is material to expressions, attribute sets, modules, derivations, flakes, overlays, purity, evaluation, store exposure, activation, remote builders, or warning and crisis thresholds beyond repository policy.
---

# Nix Language Profile

## Core principle

Apply Nix-specific judgment only when it is material. Establish the supported
Nix, NixOS, and Nixpkgs versions; repository and deployment policy; artifact
ownership; evaluation and build boundaries; protected-data policy; target
platforms; and task authority before recommending a construct or response. Use
the highest justified `Green — routine`, `Yellow — caution`,
`Orange — warning`, or `Red — crisis / stop` response for one coherent current
decision.

Keep expression structure, merge semantics, dependency ownership, evaluation,
build, store, activation, and rollback authority separate. Static inspection
can warn about proposed growth and semantic risk; it cannot establish an
evaluation result, derivation closure, build success, activation behavior, or
runtime safety. This provisional profile classifies and recommends and does not grant
evaluation, fetch, build, store, activation, or destructive
authority.

## Do not use

Do not use this profile for:

- a comment, typo, formatting-only edit, or mechanical rename with no material
  Nix-specific judgment;
- generic design, planning, implementation, debugging, or review procedure;
- selecting a Nix, NixOS, or Nixpkgs version, formatter, analyzer, module
  system, package source, deployment model, or host policy;
- authorizing expression evaluation, dependency fetch, a build, store
  inspection or mutation, garbage collection, activation, system switch,
  remote builder, or destructive action;
- automatically rewriting generated lock files, machine-produced expressions,
  historical artifacts, or existing Red owners;
- treating a hash or locked revision as proof of source trust, provenance,
  licensing, compatibility, or review; or
- inferring reachable attribute names, derivation contents, store paths,
  closure size, build behavior, or activation effects by executing target Nix.

## Procedure

1. Establish task authority, repository instructions, supported Nix, NixOS,
   and Nixpkgs versions, platform matrix, evaluation and build policy, flake or
   channel ownership, module and overlay ownership, protected-data boundary,
   activation targets, rollback, and destructive-action limits.
2. Classify each artifact as maintained expression, module, package,
   derivation, overlay, flake, lock, test, legacy, generated, vendored,
   machine-produced, or other derived material. Classification never
   suppresses semantic Red.
3. Use the repository's configured static Nix parser or analyzer when present
   and record its name, version, settings, and supported syntax. Otherwise use
   the bounded lexical rules below. Do not evaluate an expression, fetch an
   input, inspect the store, or run a build to obtain a structural count.
4. Measure current and projected owners separately across supported static
   configurations. Use the maximum established value and report computed or
   conditional branches incomplete when their complete structure cannot be
   bounded statically.
5. Assign the highest justified response. Three materially coupled Yellow signals
   normally justify Orange. Two materially coupled Orange signals over one owner
   are presumptively Red unless accepted cohesive evidence supports Orange.
   One Red signal remains Red. Correlated size, breadth, dependency,
   output, shell, and responsibility measures are not independent escalation
   evidence.
6. Proceed proportionally for Green; inspect policy and evidence for Yellow;
   require an explicit local decision, bounded source and target, compatibility
   evidence, rollback, and focused validation for Orange; stop Red growth or
   unsafe behavior pending decomposition, an accepted bounded exception, or
   governing authority.
7. Inspect merge precedence, recursion, fixed points, module priorities,
   impurity, import-from-derivation, fetch and lock behavior, string context,
   derivation and store exposure, embedded shell interpretation, activation,
   remote trust, and destructive operations independently of structure.
8. Pair separately with the applicable process capability.
   `implementing-with-test-discipline` may remain primary for an authorized
   behavior change; `reviewing-and-verifying-repository-work` may remain
   primary for acceptance review. This profile supplies Nix judgment without
   silently invoking either.
9. Preserve stricter project policy. Relax only a profile default through an
   accepted scoped rationale, evidence, validation, growth limit, and rollback;
   never relax superior reproducibility, supply-chain, security, privacy,
   integrity, activation, destructive-action, or authority stops.
10. Report the level, structural and semantic signals, artifact class, version
    and parser basis, known and unknown evaluation or runtime facts, required
    response, focused validation, and rollback or decomposition boundary.

### Structural threshold contract

These defaults apply mainly to proposed growth in maintained hand-written Nix
expressions. They are review signals, not evaluation, build, closure, runtime,
or activation claims.

| Signal | Green — routine | Yellow — caution | Orange — warning | Red — crisis / stop |
| --- | ---: | ---: | ---: | ---: |
| File physical lines | `<= 200` | `201–350` | `351–500` | `>= 501` |
| Function formals | `<= 6` | `7–12` | `13–20` | `>= 21` |
| Direct `let` bindings | `<= 8` | `9–16` | `17–28` | `>= 29` |
| Direct attribute-set breadth | `<= 12` | `13–24` | `25–40` | `>= 41` |
| Attribute-definition depth | `<= 3` | `4` | `5–6` | `>= 7` |
| Direct imports | `<= 5` | `6–10` | `11–18` | `>= 19` |
| Module option leaf paths | `<= 8` | `9–16` | `17–28` | `>= 29` |
| Merge/override mechanism families | `<= 1` | `2` | `3` | `>= 4` |
| Direct derivation attributes | `<= 15` | `16–25` | `26–40` | `>= 41` |
| Direct flake inputs | `<= 6` | `7–12` | `13–20` | `>= 21` |
| Direct derivation input dependencies | `<= 10` | `11–20` | `21–35` | `>= 36` |
| Direct outputs | `<= 2` | `3–4` | `5–7` | `>= 8` |
| Embedded shell physical lines | `<= 20` | `21–40` | `41–80` | `>= 81` |
| Independent responsibility families | `1` | `2` | `3` | `>= 4` |

Count physical lines after universal-newline decoding; blanks, comments,
multiline strings, embedded shell, and a final non-empty unterminated segment
count. Record generated sections separately rather than silently excluding
them.

Count formals per callable boundary. An identifier lambda contributes one
formal. A set pattern counts each named formal once; a default does not add a
second formal, ellipsis is not a formal, and a whole-set alias does not
duplicate the set-pattern count. Curried functions remain separate callable
boundaries rather than being flattened into one ambiguous total.

Count direct `let` bindings by names introduced in the selected lexical owner.
Count direct attribute breadth from assignment and `inherit` names. A dotted
path contributes its direct first segment once, and repeated first segments do
not inflate breadth; measure path depth separately. Computed names whose
possible set cannot be established statically make the breadth incomplete
rather than authorizing evaluation.

Count direct imports under the repository's static import definition. Count
module option leaves by distinct declared or assigned option leaf paths in the
owner, with repeated path prefixes contributing only to depth. Count direct
derivation attributes, direct flake inputs, direct declared derivation input
dependencies, and direct outputs once per name in each supported static
configuration. Do not union mutually exclusive configurations; use the
maximum established current or projected value and identify its configuration.

Count embedded shell physical lines separately inside maintained multiline
command payloads. Structural shell size does not prove quoting, interpretation,
environment, or lifecycle safety; pair the Bash or Zsh profile only when that
language is independently material.

Merge/override mechanism breadth counts independently changeable semantic
families, not occurrences or helper names:

1. shallow attribute-set update such as `//` or `mergeAttrsList`;
2. generated-name or collision aggregation such as `listToAttrs`, `genAttrs'`,
   `concatMapAttrs`, or `zipAttrsWith`;
3. recursive or path update such as `recursiveUpdate`;
4. fixed-point, package override, or overlay behavior; and
5. module-type merge, definition priority, or ordering behavior.

Repeated occurrences of one family count once structurally. Helpers with
materially different precedence remain semantically distinct even when their
structural family is shared. Structural breadth and semantic merge risk are
independent axes.

Responsibilities are independently changeable evaluation, dependency,
packaging, module, compatibility, deployment, security, data, platform, or
recovery concerns rather than steps in one cohesive result. Disclose correlated
measures instead of stacking them automatically.

### Classification and proportional exceptions

Generated locks, machine-produced expressions, vendored material, fixtures,
snapshots, and historical configuration retain their producer and historical
ownership. Do not hand-refactor or normalize them solely because they exceed a
threshold. Review the producing workflow, update scope, reproducibility,
consumer compatibility, protected-data exposure, and rollback.

An existing Red legacy artifact may receive the smallest safe fix when current
authority permits it, the change adds no independent responsibility, and it
avoids meaningful growth. Record the preserved boundary. New responsibility or
major feature growth remains Red. A cohesive generated or data-driven artifact
can change only a line-count response through an accepted bounded exception;
semantic Red remains Red.

### Semantic merge and override contract

Determine possible names, input owners and layers, collision behavior,
precedence, shallow or recursive depth, consumers, compatibility, protected
invariants, rollback, and focused validation separately from family count.
A structurally Green merge-family count cannot downgrade an Orange or Red
semantic merge response.

| Semantic case | Response |
| --- | --- |
| Literal, statically disjoint local shallow update with unchanged ownership | Green, or Yellow when local compatibility evidence remains material |
| Known local collision with deliberate documented precedence and reviewed compatibility | Yellow; Orange when public compatibility, shared ownership, migration, or rollback is consequential |
| Closed computed-name merge that materially affects collision, precedence, ownership, or consumers | Orange |
| Open or insufficiently bounded names, collisions, owners, or consumers | Orange pending evidence when consequences remain bounded; Red when an invariant can be bypassed or safe behavior cannot be established |
| Recursive, repeated-layer, fixed-point, overlay, or module-priority merge | Orange; Red for unresolved recursion, uncontrolled collision, unsafe priority, or invariant bypass |
| Security, integrity, reproducibility, trust, or ownership invariant-bypassing priority override | Red |

The shallow `//` operator is right-biased on duplicate names.
`builtins.listToAttrs` keeps the first duplicate, while `mergeAttrsList` keeps
the later duplicate. `recursiveUpdate` descends while both values are sets and
then uses the right leaf. `zipAttrsWith` delegates collision reconciliation to
its supplied function. Overlay ordering changes a package-set fixed point and
does not recursively merge nested values merely by composition. NixOS option
types own definition merging; the lowest numeric override priority survives,
while ordering priority affects order rather than inclusion.

Do not classify every computed attribute as Orange. `mapAttrs` preserves the
input name set; collision-free local `genAttrs` construction over a literal
name list is not a merge; a literal conditional `optionalAttrs` addition is not
automatically a merge; and `rec` creates recursive lexical scope rather than an
attribute-set merge. Finiteness alone, however, does not make a closed computed
merge Green when material collision, precedence, ownership, or consumer
behavior remains. `mkForce` is Orange as explicit module-priority work and Red
when it bypasses an accepted security, integrity, reproducibility, trust, or
ownership invariant.

### Other semantic responses

- A pinned fetch with an accepted locator and verified hash is Green or Yellow
  under project policy. A mutable remote fetch at a reproducibility or trust
  boundary is Red. A revision or hash proves neither licensing nor trust.
- Focused flake input and lock maintenance is Yellow when the exact graph delta
  and rollback are reviewed. A broad or unresolved graph update is Orange, and
  an unauthorized or mutable supply-chain source is Red.
- Declared, bounded impurity can be Orange under explicit repository policy.
  Undeclared result-changing environment or filesystem input is Red. Import
  from derivation is Orange only with exact build and policy authority and is
  Red when forbidden or authority remains unresolved.
- Preserve string context when it owns derivation or store dependencies. Unsafe
  context removal that defeats dependency tracking is Red.
- A derivation or path input may place material in the store. Credentials,
  tokens, keys, personal data, or other protected values entering derivation
  output, store paths, builder arguments or environment, logs, errors, or
  diagnostics are Red unless the repository supplies an authorized design that
  prevents durable or overbroad exposure.
- A fixed shell program and explicit argument vector is Green or Yellow after
  environment and lifecycle review. Untrusted input reaching generated shell
  interpretation is Red. Parameterization does not by itself prevent protected
  data disclosure.
- An activation-script definition or system integration change is Orange with
  an exact target, compatibility review, bounded rollout, validation, and
  rollback. Evaluation, build, dry activation, switch, and boot-default changes
  remain separate acts. Missing activation authority or truthful rollback is
  Red.
- Remote builders and cross-system outputs are Orange with explicit platform,
  trust, credential, transport, and lifecycle evidence. Missing trust,
  platform compatibility, or authority is Red.
- Garbage collection, store deletion, profile mutation, activation, and system
  or user switching require exact task authority. No structural level or safety
  observation authorizes them.

### Source and maintenance boundary

This profile was inspected on 2026-07-21 against the mutable Nix 2.35.2 manual,
the separately versioned Nix 2.35.1 public source, and the NixOS and Nixpkgs
26.05 semantic series. The manual and source are not claimed to be one snapshot.
Nix source and its bundled reference manual use LGPL-2.1-or-later. Nixpkgs and
NixOS source use MIT subject to component-specific exceptions. Independently
authored nix.dev site content uses CC BY-SA 4.0. APG uses facts and independently
written synthesis; copied or adapted expression would require the applicable
notice, attribution, and source obligations.

Versions are evidence, not mandated targets. Refresh before behavior-bearing
correction, maturity review, or publication when the Nix minor series, source
tag, NixOS or Nixpkgs series, merge or module semantics, purity, locking,
activation, store behavior, or license boundary materially changes. Removal
must delete the leaf, projection, catalog and map entries, known-unmanaged
handling, and focused tests while preserving ADR, evaluation, and exit history.
No root or private source guidance was migrated, so rollback restores none of
it.

## Project-owned parameters

The target repository owns supported Nix, NixOS, and Nixpkgs versions;
platforms; formatter and analyzer; flake, lock, channel, overlay, module,
package, derivation, output, store, remote-builder, deployment, activation,
test, supply-chain, protected-data, exception, validation, rollback, release,
and destructive-action policy. The current task owns whether any evaluation,
fetch, build, store, activation, remote, or destructive operation is authorized.
No response level grants Nix evaluation or host access.

## Evidence and completion

When material, report the Nix profile level, current and projected signals,
supported version and configuration basis, artifact classification, semantic
merge and protected-data findings, project policy, required response,
verification, exception if any, and rollback. Green needs project checks;
Yellow adds version and tradeoff evidence; Orange adds an accepted local
decision, adverse or compatibility evidence, bounded rollout, and rollback;
Red records the stopped action, safer alternative, and exact condition for
reconsideration.

Static inspection cannot establish evaluation results, derivation contents,
reachable closure, build success, runtime platform behavior, remote-builder
trust, activation effects, store safety, or rollback success. Do not upgrade a
claim beyond the evidence actually obtained.

## Stop or escalate

Stop for any Red signal, including a mutable supply-chain source at a protected
boundary; undeclared material impurity; forbidden or unauthorized import from
derivation; uncontrolled collision, recursion, or invariant-bypassing override;
unsafe string-context removal; protected data entering durable or uncontrolled
store or diagnostic material; untrusted shell interpretation; unauthorized
evaluation, build, store, remote-builder, activation, switch, garbage
collection, or deletion; missing truthful rollback; or crisis structural
growth without decomposition or an accepted bounded exception.

## Common mistakes

- Treating one merge-family count as the complete merge-risk decision.
- Assuming every computed name is dangerous or every finite name set is safe.
- Treating `//`, `listToAttrs`, `mergeAttrsList`, and recursive or module merges
  as though they share one collision and precedence rule.
- Treating `mkForce` as always Red or as harmless priority syntax.
- Calling `rec`, `with`, `inherit`, `mapAttrs`, or `genAttrs` a merge without
  inspecting their actual name and dependency behavior.
- Calling a locked revision or hash trusted, licensed, or compatible without
  separate evidence.
- Removing string context because a resulting string looks equivalent.
- Treating evaluation, build, dry activation, switch, and rollback as one act.
- Assuming static inspection proves store contents, closure size, build or
  activation success, or host safety.
