# APG34 Vagrantfile Profile

## Objective and disposition

APG34 evaluates one bounded new-skill candidate: `vagrantfile-profile`. The
candidate owns materially Vagrantfile-specific configuration judgment without
selecting Vagrant, a provider, box, plugin, host platform, network, synced
folder, provisioner, project command, lifecycle action, release policy, or
live-operation authority.

The lifecycle evidence supports provisional retention. No consequential
project decision requires ADR 0025.

## Current source and rights

Primary sources were inspected on 2026-07-24:

- Vagrant 2.4.9 tagged source and current Vagrant development source;
- current official Vagrant documentation for Vagrantfiles, configuration
  versions and loading, machines, boxes, providers, plugins, networks, synced
  folders, provisioners, triggers, environment variables, and state; and
- Ruby 4.0.6 release, language, and licensing sources for the general language
  boundary.

The inspected Vagrant and official-documentation source repositories are
available under Business Source License 1.1 with MPL 2.0 as the change
license. Ruby is available under the Ruby License or two-clause BSD terms,
subject to file-specific legal notices. APG uses these sources as calibration
evidence, not selected project requirements or a universal compatibility
matrix. The profile is independently written synthesis and copies or adapts no
upstream prose, code, examples, or table structure.

Vagrant 2.4.9 declares Ruby `>= 3.0` and `< 3.5`; a newer Ruby release does not
expand that compatibility boundary. The Vagrantfile configuration number is
not the Vagrant product version. Current documentation identifies
configuration versions 1 and 2. Effective configuration can merge box, home,
project, multi-machine, and provider-specific layers. Vagrantfiles and helper
files are executable Ruby, so static review must not load or evaluate them.

## Ownership and scenarios

The profile triggers only when configuration version or loading, machines,
boxes, provider blocks, plugins, networks, synced folders, provisioners,
triggers, Vagrant state, host-dependent behavior, or Vagrantfile-specific
structure materially controls a decision.

Ordinary Ruby code, Terraform-only, Packer-only, Docker-only, generic shell,
provider-administration, host-firewall, cloud-administration, project-command,
CI/CD, release-policy, and simple non-semantic text work remain non-triggers or
separate owners. Ruby and shell profiles retain their language semantics.
Repository and operator policy retain provider, box, plugin, host, network,
filesystem, protected-data, project-command, lifecycle, and external-action
authority.

Forty frozen families cover positive and non-trigger decisions;
configuration versions, loading, and uncontrolled host state; boxes,
providers, and plugins; machines and networks; synced folders; provisioning
and triggers; `.vagrant` state; host variation; generated ownership;
structural classification; stricter policy; and lifecycle authority. A
mirrored unit contract failed first before the candidate and projection
existed and passes against the integrated candidate.

## Structural contract

The profile supplies Green/Yellow/Orange/Red fallback signals for physical
lines, concrete machines, machine-provider applications, machine-network
declarations, machine-synced-folder declarations, provisioner and trigger
effects, host or platform branches, plugin and external dependencies, shared
mutable host or VM state domains, and independent responsibilities.

Measurement expands statically bounded loops and shared machine declarations,
includes maintained Vagrant-only helpers, separates general Ruby sources and
external configuration layers, uses the maximum of mutually exclusive bounded
variants, and refuses to invent a consequential count from dynamic Ruby or
uncontrolled host state. Generated or vendor-owned cohesion can lower only one
physical-line response; semantic stops remain controlling. Three coupled
Yellow signals normally justify Orange, two coupled Orange signals are
presumptively Red, and one Red remains Red.

Required Red stops remain semantic: unauthorized evaluation or lifecycle
mutation; unsupported version, provider, box, plugin, host, Ruby, or capability
claims; protected-data or untrusted-command flow; unintended network exposure;
port, address, name, identity, or shared-resource collision; unsafe synced
folders; destructive or non-idempotent provisioner and trigger effects;
unresolved or manually mutated Vagrant state; provider-specific behavior
represented as portable; static review represented as live success; and
crisis-level undecomposed ownership.

## Integration

The retained development shape is:

- 25 canonical skills, 25 catalog rows, and 25 flat projections;
- 14 stable and 11 provisional rows;
- 23 general-router entries, including the Vagrantfile profile and the
  ChatGPT-manager subrouter;
- 1 ChatGPT-local entry; and
- 24 checked route edges in total.

The current-development release policy, release validator, and strict test
inventory include the new leaf, projection, scenario fixture, and mirrored
contract. Public and active v0.3.0 remain unchanged at 19/19/19.

## Candidate correction and validation

The candidate uses one behavior-bearing correction. Initial fresh review found
that its machine measurement could add a nonexistent implicit default to a
named multi-machine environment and that its forwarded-port host-binding
statement omitted the official most-provider qualifier. One coherent
source-semantics and machine-measurement correction makes the implicit default
mutually exclusive with named machines and scopes the host-binding default to
most providers. The focused contract preserves both rules. No frozen outcome
or numeric band changes.

Before review, four capitalization-only focused assertions were aligned with
candidate sentence starts; they changed no candidate behavior or frozen
outcome.

The focused executable contract reads its scenario outcomes only from the
public-safe fixture. Publication-excluded source, threshold, integration, and
review records explain the contract but are not required by the public
candidate.

Validation covers the failing-first and passing mirrored contract, skill
library, router and catalog, exact projection, release policy, strict
inventory, affected unit and integration selections, current and public-v0.3
checkers, Python compilation, Markdown and links, privacy and durable identity,
whitespace, and a disposable current-development candidate without
publication. Fresh non-author source, rights, boundary, safety, structural,
integration, provenance, rollback, and complete-diff reviews accept the
result. Readiness, smoke, release, publication, Vagrantfile evaluation, and
Vagrant or provider operations remain outside APG34.

## Rollback and future boundary

Rollback removes the canonical leaf, flat projection, catalog row, general-map
entry, current-development release-policy and validator entries, inventory row,
focused test, scenario fixture, and current-surface test expectation together
while preserving this evaluation and the exit history. No private guidance was
migrated. The project-scoped projection owner and its fixtures remove only the
Vagrantfile profile, retain the APG33 Dockerfile profile, and expect 24 current
leaves; the general router returns to 22 entries and the ChatGPT-local router
remains at one.

No phase after APG34 is authorized. Native Go-test, `matryer/is`, `go-cmp`, a
unified Go testing-stack owner, nix-test, compatibility remediation,
readiness, smoke, and v0.4.0 release work require separate maintainer
authority.
