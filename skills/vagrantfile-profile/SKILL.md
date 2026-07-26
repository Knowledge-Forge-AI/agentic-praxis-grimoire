---
name: vagrantfile-profile
description: Use when Vagrantfile-specific judgment is material to configuration versions and loading, machines, boxes, provider blocks, networks, synced folders, provisioners, triggers, Vagrant state, host-dependent behavior, or warning and crisis thresholds beyond repository policy.
---

# Vagrantfile Profile

## Core principle

Treat a Vagrantfile as executable Ruby configuration whose effective behavior
depends on Vagrant version, configuration version, layered loading, host and
provider capabilities, external box and plugin state, and lifecycle context.
Establish those boundaries statically before recommending a change. Do not
evaluate a Vagrantfile or infer live success from source text.

Keep selection and action authority with the target repository and operator.
This profile maps Vagrantfile-specific consequences without choosing Vagrant,
a provider, box, plugin, host platform, network, folder, provisioner, command,
or lifecycle action. Assign the highest justified `Green — routine`,
`Yellow — caution`, `Orange — warning`, or `Red — crisis / stop` response for
one coherent current decision.

Structural measurements warn about proposed growth in maintained hand-written
Vagrant configuration. They do not choose topology, prove provider support,
grant VM authority, or demand unrelated legacy rewrites.

## Do not use

Do not use this profile for:

- ordinary Ruby code with no material Vagrant behavior;
- Terraform-only, Packer-only, or Docker-only work;
- generic shell scripts, application code, or infrastructure policy with no
  Vagrantfile-specific decision;
- provider or hypervisor administration outside a Vagrantfile;
- choosing Vagrant, a provider, box, plugin, host platform, provisioner,
  synced-folder implementation, network exposure, firewall rule, dependency,
  or tool;
- selecting an exact Vagrant or lifecycle command, project command, CI/CD
  workflow, release policy, or deployment procedure;
- installing, updating, repairing, or removing a box or plugin;
- evaluating or loading a Vagrantfile, `.vagrantplugins`, or Ruby helper;
- creating, reloading, provisioning, suspending, halting, snapshotting, or
  destroying a machine;
- treating `.vagrant`, a machine index, provider identity, plugin state, or box
  state as source;
- assuming source review proves that a provider or plugin is installed, a box
  is available, a port is free, a folder mounts, a machine boots, or
  provisioning succeeds;
- replacing general Ruby or shell guidance when those language semantics are
  independently material;
- treating generated, vendor-owned, home, or box configuration as maintained
  project source before classification; or
- automatically refactoring an existing Red Vagrantfile.

This profile does not grant authority to perform a Vagrant or provider
operation.

## Procedure

1. Establish task authority, repository instructions, selected Vagrant and
   configuration versions, supported Ruby runtime, host platform and
   architecture, provider and plugin policy, box and update policy, network and
   filesystem policy, protected-data boundary, exact validation scope, and
   source and operational rollback. Record every Vagrant, provider, box,
   plugin, network, folder, provisioner, trigger, host, hypervisor, and
   external-state action that remains unrun.
2. Classify each relevant artifact as a maintained root Vagrantfile,
   maintained Vagrant-only helper, general Ruby source, box or home
   configuration, generated output, vendor-owned file, fixture, example,
   plugin file, or operational state. `.vagrant` is generated machine and
   provider identity, not source. Change the authorized generator or owner
   when applicable. Classification can change structural treatment but never
   suppresses a semantic Red stop.
3. Establish configuration interpretation without executing Ruby. The
   configuration number is not the Vagrant product version. Current Vagrant
   documentation identifies configuration versions 1 and 2.
   `Vagrant.configure` stores a block for later environment loading. Identify
   the lookup root and every applicable box, home, project, multi-machine, and
   provider-specific layer. Map merge order, overrides, multiple configure
   blocks, helper loads, and shadowed values. A partial layer view is not the
   effective configuration.
4. Inspect host-controlled configuration inputs. `VAGRANT_CWD` changes the
   lookup start, `VAGRANT_HOME` changes global state such as boxes and plugins,
   and `VAGRANT_DOTFILE_PATH` changes the default `.vagrant` state location.
   Map `ENV`, filesystem reads, `load`, `require`, conditionals, iteration,
   exception handling, subprocess APIs, and `.vagrantplugins` without running
   them. Bound every host or platform branch. Uncontrolled consequential
   behavior is Orange; representing it as portable or verified is Red.
5. Inspect boxes and external inputs. Record box name, source, exact or ranged
   version, provider, architecture, metadata, URL, checksum behavior, update
   policy, credentials, trust, availability assumptions, and rollback. The
   documented default is the latest available version satisfying `>= 0`.
   A download checksum applies only within its documented download boundary;
   the checksum does not prove provenance, provider or architecture
   compatibility, guest behavior, or boot success.
6. Inspect plugin and capability assumptions. `Vagrant.has_plugin?` can test a
   plugin name and optional version requirement against enabled or installed
   state. `Vagrant.require_plugin` is deprecated and has no effect in Vagrant
   2.4.9. Record exact plugin name, version, source, compatibility, load and
   failure behavior, and project policy. Presence alone is not semantic
   compatibility or host, guest, provider, provisioner, or synced-folder
   capability evidence. Do not install, update, repair, or remove a plugin.
7. Draw the concrete machine graph. Count the implicit default machine once
   only when no named `config.vm.define` results exist. Otherwise count each
   statically bounded named result once. Map shared configuration,
   machine-local overrides, dependencies, primary and autostart behavior,
   command fan-out, identity, and rollback. Expand bounded loops and tables:
   one root declaration applied to four machines counts four concrete
   applications for machine-scoped network, folder, provisioner, and provider
   measurements.
8. Map provider-specific blocks by machine and provider. Record general
   settings overridden within each block, selected and alternative providers,
   host requirements, versioned plugin state, availability, capability
   assumptions, and rollback. Vagrant can ignore configuration for an
   unavailable provider; source presence does not prove applicability.
   Provider-specific behavior represented as portable is Red.
9. Map every network declaration to exact machine, provider, host interface,
   host and guest address or port, protocol, subnet, bridge, DHCP or static
   allocation, collision policy, exposure, consumer, firewall owner,
   validation, and rollback. For most providers, forwarded ports bind all host
   interfaces by default unless narrowed. Per-port auto-correction changes the
   host port and therefore requires consumer ownership. A static address
   remains project-owned collision responsibility. Public-network meaning
   varies by provider. Stop when ports, addresses, machine names, or state
   identities can collide or an unintended service can be exposed.
10. Map every synced folder from its exact host path to its absolute guest
    path. Include the default `/vagrant` project share unless the effective
    configuration disables it. Establish implementation type, provider and
    plugin support, creation behavior, direction, ownership, group, mode,
    mount options, symlink behavior, platform differences, protected-data
    boundary, validation, and rollback. A host home directory or broad
    sensitive root is Red.
11. Map provisioning by concrete machine, provisioner, source, transport,
    interpreter, arguments, environment, privilege, order, run frequency,
    reboot or capability effects, inputs, outputs, logs, failure, idempotency,
    validation, and rollback. Vagrant source and configuration do not
    establish provisioner idempotency. Fixed shell arguments remain Yellow
    until guest, interpreter, quoting, privilege, repeatability, and failure
    behavior are explicit. Untrusted source-to-command flow is Red.
12. Map triggers by scope, before or after timing, command, action or hook,
    definition order, host or guest execution, condition, effect, failure
    mode, abort behavior, repeatability, partial-effect recovery, and rollback.
    Triggers run in definition order, but that fact does not make their effects
    safe. A destructive external effect attached to halt, destroy, or another
    lifecycle event is Red without exact authority and remains Orange after
    authorization until adverse behavior and rollback are accepted.
13. Inspect Ruby behavior only when it materially affects configuration.
    Establish the Vagrant-supported Ruby range before interpreting syntax or
    APIs. Vagrant 2.4.9 declares Ruby `>= 3.0` and `< 3.5`; current Ruby
    availability does not authorize newer syntax. Pair
    `ruby-language-profile` for independently material blocks, control flow,
    exceptions, shared state, loading, filesystem access, subprocesses, or
    Ruby structure. Do not duplicate its language contract here.
14. Pair `bash-language-profile` or the applicable shell profile only when a
    provisioner or trigger materially depends on that shell's quoting,
    expansion, arrays, pipelines, traps, portability, or process lifecycle.
    Vagrant placement, transport, privilege, order, repetition, and lifecycle
    remain with this profile.
15. Measure current and projected structure using repository tooling when
    available. Otherwise use the APG fallback contract below and label the
    measurement. Expand statically bounded machines and declarations, include
    maintained Vagrant-only helpers, use the maximum of mutually exclusive
    bounded variants, and refuse to invent a consequential count from dynamic
    Ruby or uncontrolled host state.
16. Assign the highest structural or semantic level. Proceed proportionally
    for Green; inspect project policy and bounded evidence for Yellow; require
    an accepted local decision, rationale, adverse-case validation, growth
    limit, and rollback for Orange; stop a Red unsupported, exposed,
    colliding, destructive, protected, untrusted, falsely verified,
    unauthorized, or crisis-level boundary.
17. Preserve stricter repository policy and project-owned commands. Static
    review cannot prove a box is available or trusted, a plugin or provider is
    installed and compatible, a capability exists, a port or address is free,
    a folder mounts safely, a machine boots, a provisioner is idempotent, a
    trigger rolls back, or a lifecycle command succeeds. Report those checks
    as unrun unless separately authorized and executed.
18. Report the level, source and configuration versions, Ruby range, effective
    layers, host/provider assumptions, machines, boxes, plugins, networks,
    folders, provisioners, triggers, state domains, structural signals,
    protected-data and collision boundaries, accepted exception if any,
    validation limits, unrun live checks, and source rollback. No Vagrant
    lifecycle or provider operation is authorized by this procedure.

### Structural threshold contract

These defaults apply mainly to a maintained hand-written Vagrantfile owner:
the root Vagrantfile plus directly owned Vagrant-only helper configuration.
They are guidance signals, not provider policy, topology selection, linter
output, automatic rewrite authority, or lifecycle authority.

| Signal | Green — routine | Yellow — caution | Orange — warning | Red — crisis / stop |
| --- | ---: | ---: | ---: | ---: |
| Physical lines per Vagrantfile owner | `<= 200` | `201–350` | `351–500` | `>= 501` |
| Concrete machine definitions | `1–4` | `5–8` | `9–16` | `>= 17` |
| Concrete machine-provider block applications | `0–2` | `3–4` | `5–7` | `>= 8` |
| Concrete machine-network declarations | `0–3` | `4–8` | `9–16` | `>= 17` |
| Concrete machine-synced-folder declarations | `0–2` | `3–5` | `6–10` | `>= 11` |
| Concrete provisioner and trigger effect families | `0–3` | `4–7` | `8–12` | `>= 13` |
| Host or platform conditional branches | `0–1` | `2–3` | `4–6` | `>= 7` |
| Plugin and external dependency families | `0–1` | `2–3` | `4–6` | `>= 7` |
| Shared mutable host or VM state domains | `0` | `1` | `2–3` | `>= 4` |
| Independent responsibility families | `1` | `2` | `3` | `>= 4` |

Count physical lines after universal-newline decoding. Blank lines, comments,
heredoc delimiters and payload, embedded scripts, and a final non-empty
unterminated segment count. Sum the root Vagrantfile and directly loaded
Vagrant-only helpers so file splitting does not hide growth. Report any helper
that independently crosses the Ruby profile's file threshold. General-purpose
Ruby libraries retain their own owner.

Count the implicit default environment as one machine only when no named
machine definitions exist. Otherwise count each statically bounded named
`config.vm.define` result once. Expand bounded loops and data tables into
concrete results. Shared configuration counts once per concrete machine to
which effective merge and override rules apply.

Count provider applications by concrete machine and provider block whose
settings or overrides can change independently. Count effective forwarded,
private, and public network declarations per machine. Count each effective
host-to-guest synced-folder mapping per machine, including the default project
share unless disabled.

Count provisioner and trigger effect families by concrete machine or host
scope, lifecycle event, independently ordered effect, failure contract, and
rollback. One cohesive idempotent provisioner remains one family per concrete
machine even when it contains multiple commands; those commands can still
trigger independent Ruby or shell warnings.

Count host and platform branches by materially different effective
configuration outcomes selected by OS, architecture, environment, provider,
capability, filesystem, or other host observation. Count plugin and external
dependency families by independently versioned, sourced, updated, or rolled
back plugin, provider plugin, box, remote script, host executable, imported
configuration package, or external artifact.

Count a shared mutable state domain only when behavior reads or mutates state
outside one machine's isolated lifecycle or shares identity across owners.
Domains include `.vagrant`, global box or plugin state, host environment,
broad host files, host network allocation, provider or hypervisor state,
shared guest filesystems, and external services. Ordinary state isolated to
one declared machine does not count by itself.

One responsibility family is one independently accepted environment outcome
with its own change and rollback lifecycle, not every machine or mechanism. A
conventional application and database pair owned and rolled back together is
one cohesive responsibility family. Independently operated application,
migration, CI, or network-appliance environments are separate.

For mutually exclusive, statically bounded host or provider variants, measure
each complete variant and use the maximum rather than summing duplicates.
Count variant arms separately and report exposure or state differences. If
Ruby evaluation, uncontrolled `ENV`, filesystem discovery, subprocess output,
plugin state, or another dynamic input prevents a truthful consequential
bound, classify the unknown as Orange; representing it as verified is Red.

Include maintained project-owned configuration layers. Record external box,
home, generated, and vendor layers separately without claiming their source
lines as maintained project ownership. Generated and vendor-owned files retain
their producer. A repository-accepted cohesive generated or vendor matrix may
lower only the physical-line response by one level; it cannot lower any other
structural or semantic signal.

Three materially coupled Yellow signals normally justify Orange. Two
materially coupled Orange signals affecting one owner are presumptively Red
unless cohesive evidence, repository acceptance, adverse-case validation, a
growth bound, and rollback justify retaining Orange. One Red signal remains
Red. Correlated machine, network, folder, and provisioner fan-out must be
disclosed but does not automatically stack as independent findings.

A four-machine application environment with one private network, one narrow
project share, and one idempotent bootstrap applied to every machine has Green
machine breadth and Yellow network, folder, and effect breadth. Those three
coupled Yellow signals normally justify Orange for topology and rollback
review; the four machines are not four responsibility families. A two-machine
application and database environment with one private network, no extra share,
and one bounded provisioner per machine can remain Green. Four independently
operated target environments are Red on responsibility breadth even if each
contains one machine.

An existing Red legacy Vagrantfile may receive the smallest safe authorized
fix when it adds no independent responsibility or meaningful structural
growth and records a decomposition boundary. New responsibility remains Red.
A bounded exception requires repository acceptance, evidence, adverse-case
validation, an owner, growth limit, refresh condition, and rollback. It cannot
relax protected-data, exposure, collision, support, truthfulness, state, or
authority stops.

Rollback restores the prior authorized Vagrantfile or generator output,
configuration layers, machine topology, declarations, host branches, and
state assumptions, then remeasures the static contract. It does not rewrite
`.vagrant`, global Vagrant state, boxes, plugins, providers, machines,
networks, folders, hypervisor state, or external effects and grants no live
authority.

### Vagrantfile semantic response guide

- Vagrant 2.4.9 is the latest stable calibration point on 2026-07-24.
  Current upstream `main` identifies itself as `2.4.10.dev`. Vagrant source and
  current documentation are available under Business Source License 1.1 with
  an MPL 2.0 change license. These facts are not a universal compatibility
  matrix or selected project target.
- The configuration number is not the Vagrant product version. Current
  configuration versions 1 and 2 select different configuration-object APIs.
  Multiple blocks and layers merge; old syntax cannot be assumed valid in the
  other version.
- A Vagrantfile is executable Ruby, and `Vagrant.configure` stores
  configuration for later loading. Static inspection does not evaluate a
  Vagrantfile, helper, or plugin file. Vagrant 2.4.9's Ruby `>= 3.0` and
  `< 3.5` constraint controls compatibility even though newer Ruby releases
  exist.
- Effective configuration can include box, home, project, multi-machine, and
  provider-specific layers. `VAGRANT_CWD`, `VAGRANT_HOME`, and
  `VAGRANT_DOTFILE_PATH` can change lookup and state boundaries. Uncontrolled
  host conditionals are Orange; protected, unbounded, or falsely portable
  behavior is Red.
- A floating box is Yellow or Orange under project update policy. An exact
  version and checksum or metadata evidence can be Green or Yellow only after
  source, provider, architecture, update, provenance, and rollback are
  established. Neither source form proves availability or boot success.
- Plugin presence and version can be queried, but installation state is not a
  support promise. A missing required plugin is Red until resolved through
  separate authority. Plugin installation without authority is Red.
- A coherent named multi-machine environment can be Green or Yellow.
  Consequential dynamic generation that cannot be concretely expanded is
  Orange; representing its breadth or command fan-out as verified is Red.
- Provider blocks can override general configuration and an unavailable
  provider block can be ignored. Approved provider-specific behavior can be
  Green or Yellow with exact evidence. A portable claim without provider and
  host evidence is Red.
- Forwarded-port collision, unintended public binding, conflicting static
  addresses, or unintended public-network exposure is Red until exact
  allocation, authority, validation, and rollback are established.
- A narrow project-owned synced folder can be Green or Yellow after exact
  path, effective layer, implementation, ownership, permission, symlink,
  provider, and rollback review. A host home directory, broad sensitive path,
  or unsafe ownership boundary is Red.
- An idempotent project-approved provisioner can be Green or Yellow only after
  repeat and adverse-case evidence. Vagrant does not enforce idempotency.
  Untrusted input reaches Ruby, shell, host-command, or guest-command
  interpretation is Red.
- Triggers need explicit scope, order, host or guest execution, failure,
  repetition, partial-effect recovery, and rollback. Destructive external
  effects on halt or destroy are Red without exact authority.
- `.vagrant` is generated machine and provider identity rather than source.
  Stale, copied, shared, or manually changed identity is Red until source,
  local state, global index, provider ownership, backup, and recovery are
  reconciled.
- Static review cannot prove that a provider, plugin, capability, box, port,
  address, synced folder, boot, provisioning action, trigger, or rollback
  works in a live environment. Do not convert unrun checks into completion
  evidence.

### Source and maintenance boundary

This profile was inspected on 2026-07-24 against Vagrant 2.4.9, current
Vagrant `main` at `2.4.10.dev`, current official Vagrant 2.4.9 documentation,
and official Ruby language and core documentation. Vagrant source and current
documentation are Business Source License 1.1 with MPL 2.0 change licenses.
Ruby is available under the Ruby License or two-clause BSD, subject to
file-specific terms. These sources are calibration evidence, not
project-selected versions. APG copies or adapts no upstream prose, source,
example, or table; this procedure is independently written synthesis.

Refresh before a behavior-bearing correction, maturity review, or publication
when Vagrant stable or development identity, configuration loading, Ruby
compatibility, box metadata, provider or plugin behavior, networking, synced
folders, provisioning, triggers, state ownership, licensing, or
representative false-escalation evidence materially changes.

Removal is candidate-independent. It must delete the leaf, flat projection,
catalog and general-map entries, current-development release policy, strict
test inventory, focused test, and public scenario fixture while preserving
evaluation and exit history. The project-scoped projection owner and its
fixtures must remove only `vagrantfile-profile`, preserve every other live
skill, and recompute all surviving skill, catalog, projection, route, fixture,
and test counts. Derive counts from the resulting live inventories. A raw
APG34 commit revert is not valid rollback because it would restore historical
counts and integration state. Public and active v0.3.0 remain 19/19/19. No
private guidance was migrated, so rollback restores none of it.

## Project-owned parameters

The target repository owns whether to use Vagrant and a Vagrantfile; Vagrant,
Ruby, provider, plugin, box, metadata, architecture, URL, checksum, provenance,
version, and update policy; host platform, architecture, capability, provider,
and hypervisor support; configuration layers and helpers; machine topology,
names, primary and autostart policy; networks, addresses, ports, bridges,
interfaces, collision allocation, exposure, firewall, and consumers; synced
folders, paths, direction, implementation, ownership, permissions, modes,
symlinks, and disable behavior; provisioners, triggers, interpreters,
privilege, environment, inputs, outputs, idempotency, lifecycle, failure,
cleanup, and rollback; protected data; dependencies; exact commands; tests;
performance; accepted exceptions; mutation; release; and destructive-action
authority.

## Evidence and completion

When material, report the Vagrantfile profile level, source and configuration
versions, Ruby range, host and provider basis, effective layers, artifacts and
classification, boxes and plugins, concrete machines and declarations,
networks and collision boundaries, folders and host-path ownership,
provisioners and triggers, state domains, structural signals, protected-data
boundary, project policy, validation, unrun live checks, accepted exception if
any, and source rollback.

Green needs static project checks and explicit inputs. Yellow adds version,
host/provider, update, and tradeoff evidence. Orange adds an accepted local
decision, adverse-case validation, growth bound, and rollback. Red records the
stopped action, safer alternative, and exact condition for reconsideration.
Source inspection must not be reported as machine, provider, network, folder,
provisioning, trigger, or rollback execution evidence.

## Stop or escalate

Stop or escalate when:

- exact Vagrant, configuration, Ruby, box, provider, plugin, host, or
  capability support is unresolved but consequential behavior is claimed;
- protected data can reach source, environment, URL, logs, state, a
  provisioner, a trigger, or a durable artifact;
- untrusted input can reach Ruby evaluation, shell interpretation, host or
  guest commands, or dynamic filesystem loading;
- ports, addresses, machine names, host paths, state identities, or shared
  resources can collide;
- a network can expose an unintended service;
- a synced folder can expose protected host data or has unresolved ownership,
  permission, direction, type, provider, or symlink behavior;
- a provisioner or trigger can repeat, partially fail, or destroy state
  without exact authority, idempotency, validation, and rollback;
- `.vagrant`, global Vagrant, provider, machine-index, box, plugin, host,
  hypervisor, or external state is stale, shared, copied, unresolved, or
  outside its owner;
- provider-specific behavior is represented as portable;
- static review is represented as live success;
- a Vagrantfile or plugin file would be evaluated without authority;
- a Vagrant, provider, box, plugin, machine, network, folder, hypervisor, or
  external-state action lacks explicit authority; or
- meaningful new growth crosses Red without decomposition or an accepted
  bounded exception.

## Common mistakes

- Confusing the Vagrantfile configuration number with the Vagrant product
  version.
- Reviewing only the project file while ignoring box, home, multi-machine, or
  provider-specific layers.
- Evaluating executable Ruby to discover configuration during a static review.
- Treating `Vagrant.has_plugin?` as provider, plugin, or capability support
  evidence.
- Treating `Vagrant.require_plugin` as an installation or enforcement
  mechanism.
- Assuming an ignored unavailable-provider block proves portability.
- Calling a floating box reproducible or a checksum proof of boot behavior.
- Assuming port collision correction preserves a consumer's expected port.
- Assuming a private network is collision-free or a public network has one
  portable provider meaning.
- Treating a narrow synced-folder declaration as proof of the effective mount.
- Assuming Vagrant makes provisioners idempotent or trigger effects atomic.
- Treating `.vagrant` as committed source or manually repairing its identity.
- Hiding concrete fan-out behind Ruby loops, data tables, helpers, or imported
  configuration.
- Counting every machine as an independent responsibility when one environment
  owner and rollback control them together.
- Letting a generated or legacy classification lower a semantic Red stop.
- Converting source inspection into authority to run Vagrant or mutate a
  provider.
