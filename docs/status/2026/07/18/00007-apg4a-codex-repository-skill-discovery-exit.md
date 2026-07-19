# APG4A Codex Repository Skill Discovery Exit

## Phase identity

- **Phase:** APG4A
- **Date:** 2026-07-18
- **Exit sequence:** `00007`
- **Disposition:** Complete — Codex repository discovery projection installed
- **Controlling decision:**
  [ADR 0003](../../../../adr/2026/07/0003-bootstrap-maturity-and-superpowers-coexistence.md),
  Accepted and unchanged

## External correction disposition

External review returned `correction-required` for APG4. The canonical leaves
were committed under `skills/`, but Codex discovers repository-local skills
under `.agents/skills/`. APG4 therefore authored and validated the bundle
without installing its Codex repository discovery projection.

APG4A corrects only that integration omission. It does not reinterpret the
omission as a behavioral failure of a skill or reopen APG4's accepted maturity,
scenario, correction, review, provenance, transition, or decommission results.

## Accepted APG4 content preserved

APG4A preserves byte for byte:

- all six canonical `SKILL.md` procedures;
- all 18 scenario dispositions;
- the planning and debugging corrections;
- independent per-skill and finished-diff review;
- Accepted ADR 0003 and the bootstrap maturity model;
- the Superpowers transition map and provenance; and
- the repository-local behavioral opt-out and no-decommission state.

Every skill remains `provisional`.

## Canonical and projection architecture

Canonical APG procedure content remains under `skills/<skill-name>/SKILL.md`.
Documentation, provenance, maturity, and evaluation records continue to identify
those paths. The checked-in `.agents/skills/` directory is Codex-specific
discovery layout and contains no independent skill content.

Current
[official Codex skill documentation](https://learn.chatgpt.com/docs/build-skills)
states that repository skills are discovered under `.agents/skills` and that
Codex follows symlinked skill folders. APG4A implements that supported layout
with relative symbolic links. The projection is not a plugin, runtime, registry,
adapter process, second canonical copy, or separate skill.

## Projection installed

| Projection path | Relative target |
| --- | --- |
| `.agents/skills/composing-bounded-worker-assignments` | `../../skills/composing-bounded-worker-assignments` |
| `.agents/skills/debugging-systematically` | `../../skills/debugging-systematically` |
| `.agents/skills/designing-significant-changes` | `../../skills/designing-significant-changes` |
| `.agents/skills/implementing-with-test-discipline` | `../../skills/implementing-with-test-discipline` |
| `.agents/skills/planning-repository-work` | `../../skills/planning-repository-work` |
| `.agents/skills/reviewing-and-verifying-repository-work` | `../../skills/reviewing-and-verifying-repository-work` |

`.agents/skills/` is an ordinary directory. Each entry is a relative symlink
whose target resolves within the repository to the matching canonical directory
and readable `SKILL.md`. No seventh projection, direct projected `SKILL.md`,
copied leaf, broken target, cycle, absolute target, or repository escape exists.

## Canonical hash preservation

| Canonical skill | Pre-APG4A SHA-256 | Final SHA-256 | Result |
| --- | --- | --- | --- |
| `composing-bounded-worker-assignments` | `4613b98e84708e97ff35dd109179139e54c9167d0bf0b11d6aa1ffa5a2c76bca` | `4613b98e84708e97ff35dd109179139e54c9167d0bf0b11d6aa1ffa5a2c76bca` | Equal |
| `debugging-systematically` | `d7bd9e4dfb27f9e334cdcbfb0ffaf6b8f2a8f26529ee421ee39271f383148316` | `d7bd9e4dfb27f9e334cdcbfb0ffaf6b8f2a8f26529ee421ee39271f383148316` | Equal |
| `designing-significant-changes` | `08b9c9ecde90ce047303e25610711c26f026dd6e4e91ed7cef3b701a7e043f90` | `08b9c9ecde90ce047303e25610711c26f026dd6e4e91ed7cef3b701a7e043f90` | Equal |
| `implementing-with-test-discipline` | `896af1208ab62547483434133887f8951a09be4da2f7f317af38b7282680bb06` | `896af1208ab62547483434133887f8951a09be4da2f7f317af38b7282680bb06` | Equal |
| `planning-repository-work` | `4571258a3e1bd70381d3b01d9c15fffc783e9028ecc3cfa58c659b6d157cca8b` | `4571258a3e1bd70381d3b01d9c15fffc783e9028ecc3cfa58c659b6d157cca8b` | Equal |
| `reviewing-and-verifying-repository-work` | `7e49626e8bba5382dc86c52c9b26ca5db7c69ff2187703149655f1835e01ab8b` | `7e49626e8bba5382dc86c52c9b26ca5db7c69ff2187703149655f1835e01ab8b` | Equal |

No canonical skill behavior changed.

## Documentation reconciliation

APG4A updates the README, project model, bootstrap model, skill index,
provenance, roadmap, APG4 evaluation summary, and APG4 exit to distinguish
canonical content from Codex discovery. Historical records now state that APG4
authored and reviewed six canonical leaves but did not install the projection;
they do not claim that the projection existed during the 18 scenarios.

## Maturity, Superpowers, and publication boundary

All six skills remain `provisional`. Projection validation establishes only the
filesystem and Git integration. It does not establish explicit invocation,
automatic invocation, trigger quality, dogfooding success, comparative
superiority, production readiness, or stable maturity.

Superpowers remains globally installed and behaviorally reference-only for APG.
No user-level Codex configuration, alternate Codex home, installer, plugin,
desktop metadata, dependency, adapter process, runtime, registry, taxonomy,
publication, license decision, or extra skill was added.

Public files contain no private source identity, path, snapshot, or topology and
do not link into `private/`. No publication-excluded APG4 evidence was rewritten.

## Validation

| Check | Result |
| --- | --- |
| Development and read-only source preflight | Passed. Development `main` began clean and remote-equal at the expected APG4 commit; the fetched source repository remains clean and remote-equal at its current snapshot. |
| Six canonical skill hashes before and after APG4A | Passed. All six canonical `SKILL.md` files are byte-identical to pre-APG4A `HEAD` and match the recorded SHA-256 values. |
| Six exact projection names, relative targets, containment, target identity, readable leaves, and no cycles or broken links | Passed for six of six. `.agents/skills/` is an ordinary directory with no seventh or direct `SKILL.md` entry. |
| Git mode `120000` for six projection entries | Passed for six of six; each indexed symlink blob contains the exact expected relative target. |
| Canonical skill leaf validation | Passed for all six canonical leaves. |
| Markdown headings, fences, and local links | Passed across all 53 tracked Markdown files. |
| Public confidentiality and public-to-private dependency scan | Passed. No public file exposes private identity, path, snapshot, or topology or links into `private/`. |
| ADR sequence through `0003`; exit sequence through `00007`; exit filenames, titles, and indexes | Passed. |
| Exact changed-path and prohibited-artifact review | Passed for 16 authorized paths. No configuration, plugin, metadata, dependency, adapter, runtime, registry, taxonomy, publication, license, or extra-skill artifact changed. |
| Independent finished-diff review | Passed. One fresh read-only reviewer answered all 16 integration questions, found no blocker, material, or minor issue, independently reproduced the staged-patch hash, and accepted the staged APG4A diff. |
| `git diff --check` | Passed. |
| `git diff --cached --check` | Passed. |
| Source tests and compilation | not run; documentation and repository discovery links only |

## Limitations

- The current APG4A session created and mechanically validated the projection;
  it did not begin a new app session that discovered the resulting commit.
- Explicit and automatic invocation through the projection remain untested.
- No dogfooding observation, behavioral re-evaluation, clean comparison, skill
  promotion, or Superpowers decommissioning occurred.
- Other harness projections and distribution packaging remain separately
  deferred.

## Next gate

Begin a new Codex APG thread that loads the committed repository state. Confirm
all six skills are discoverable, then perform bounded dogfooding only where their
triggers naturally apply. Record discovery, explicit or automatic selection,
non-trigger behavior, artifact or stop disposition, authority and privacy
results, verification, and unrun checks.

## Subsequent fresh-session evidence

APG5 later recorded a human-accepted fresh Codex application observation against
the committed APG4A state. Six of six APG skills were discovered, and
`reviewing-and-verifying-repository-work` was explicitly selected for a bounded
read-only integration and completion-evidence review with terminal disposition
`pass`.

This later result does not rewrite the APG4A session as having performed the
smoke. It is one explicit-use dogfooding observation, not automatic-invocation,
comparative, stable-maturity, production-readiness, or decommission-readiness
evidence. All six skills remain `provisional`.

## External review requested

External review is requested to **accept APG4A as Complete — Codex repository
discovery projection installed, preserve all six skills at `provisional`, and
authorize only fresh-session discovery plus bounded dogfooding as the next
evidence gate**.

That disposition does not promote a skill, claim invocation success,
decommission Superpowers, publish APG, choose a license or taxonomy, package a
plugin, or authorize another implementation phase.
