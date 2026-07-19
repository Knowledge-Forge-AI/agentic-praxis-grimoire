# APG4 Bootstrap v0.1 Exit

## Phase identity

- **Phase:** APG4
- **Date:** 2026-07-18
- **Exit sequence:** `00006`
- **Disposition:** Complete — six provisional skills bootstrapped
- **Decision:**
  [ADR 0003](../../../../adr/2026/07/0003-bootstrap-maturity-and-superpowers-coexistence.md),
  Accepted

## Human-authorized course correction

The human maintainer accepted APG3's blocked disposition as truthful evidence
about its evaluation environment while rejecting the interpretation that APG
must remain skill-free until Superpowers can be removed globally or a clean A/B
harness exists.

APG4 was authorized to retain Superpowers for other repositories, make it
reference-only for APG through root instructions, bootstrap multiple useful but
provisional skills, accept structural, scenario, independent-review, and
dogfooding evidence without a superiority claim, and defer clean comparative
evaluation and decommissioning.

## APG3 disposition preserved

APG3 remains `blocked`. It stopped before plan freeze, baseline execution,
candidate authoring, or comparison because the exposed environment lacked an
isolated skill profile, observable invocation event, and controlled candidate
availability and loading. APG4 does not rewrite that result as a failed skill,
an adequate baseline, or evidence against later evaluation.

## Repository-local Superpowers policy

The root repository policy states semantically:

- Superpowers is reference evidence only for work in APG;
- no `superpowers:*` skill governs the workflow unless a human-authorized task
  explicitly names one for inspection or comparison;
- Superpowers' universal skill-invocation bootstrap does not apply here; and
- APG instructions, accepted decisions, and the current authorized phase own
  the workflow while Superpowers remains installed for other repositories.

This is a behavioral policy, not proof that the plugin is mechanically unloaded
or absent from model context. The policy was already present in the clean fetched
APG4 baseline and was preserved unchanged.

## ADR 0003 and bootstrap model

Accepted ADR 0003 distinguishes source availability from process authority,
permits provisional authorship before clean comparison, defines `bootstrap`,
`provisional`, `evaluated`, `stable`, and `deprecated` maturity, preserves APG3
history, and requires explicit coverage and rollback gates before Superpowers
decommissioning.

The APG v0.1 bootstrap model defines skill acceptance, public/private evidence,
project-owned parameters, independent removal, dogfooding, decommissioning, and
later clean-evaluation requirements. No APG4 skill can become `stable` until it
has succeeded in more than one real repository and survived explicit post-
Superpowers review.

## Skills authored and omitted

| Skill | Maturity | Scenario result | Corrections | Independent disposition |
| --- | --- | --- | ---: | --- |
| `composing-bounded-worker-assignments` | `provisional` | Pass | 0 | Accept provisional |
| `designing-significant-changes` | `provisional` | Pass | 0 | Accept provisional |
| `planning-repository-work` | `provisional` | Pass after rerun | 1 | Accept provisional |
| `implementing-with-test-discipline` | `provisional` | Pass | 0 | Accept provisional |
| `debugging-systematically` | `provisional` | Pass after rerun | 1 | Accept provisional after correction review |
| `reviewing-and-verifying-repository-work` | `provisional` | Pass with fixture limitation | 0 | Accept provisional |

Omitted skills: none.

No skill authorizes delegation, expands human-approved scope, requires managed
reports from ordinary workers, embeds private conventions, or claims that Codex
is incapable without it.

## Scenario validation

Six fresh read-only workers performed 18 deliberate public-safe walkthroughs:
six positive-use cases, six non-trigger cases, and six edge or stop cases. All
18 reached their frozen disposition. The planning and debugging leaves each
received one bounded wording correction and a complete three-scenario rerun with
no regression or remaining material defect.

This was deliberate skill application rather than automatic-trigger telemetry.
No baseline condition was run, no clean causal comparison was attempted, and no
superiority claim is made.

## Independent review

Fresh non-author reviewers assessed every skill against trigger precision,
authority, proportionality, completeness, project-policy separation,
public/private safety, source-expression independence, evidence, rollback, and
ADR 0003.

They found one material issue, resolved in the debugging skill: evidence was
incorrectly phrased as authorizing correction. The corrected text separates
evidentiary support from assignment and project-owned mutation authority, passed
all scenario reruns, and passed narrow independent re-review.

Two minor clarity notes remain without correction: the implementation and
review skills rely on the controlling bootstrap and project policy for rollback
or recovery rather than naming those parameters in every local list. The review
positive fixture also tested evidentiary restraint rather than substantive
finding quality because it did not include a concrete synthetic diff and test
output.

No blocker or material finding remains.

## Superpowers transition result

The transition map covers `using-superpowers`, design, planning, plan execution,
test discipline, debugging, verification, review request and response, parallel
and subagent development, worktrees, branch completion, and skill authoring.
Each routes to an APG v0.1 skill, native Codex capability, repository policy,
intentional deferral, or intentional rejection.

The map preserves useful engineering values while removing universal ceremony,
fixed templates, mandatory skill chains, and project-specific mechanics. It
does not imply that Superpowers has been decommissioned.

## Provenance and publication boundary

Public provenance identifies generalized maintainer-authored practices,
RepoMap, Superpowers under the MIT License, and the public Agent Skills
specification as applicable. APG4 uses independently written synthesis and
introduces no copied or adapted Superpowers expression or new notice requirement.
APG's own distribution license remains deferred.

Exact repository snapshots, source mappings, scenario artifacts, hashes,
correction details, and reviewer dispositions remain in publication-excluded
evidence. Public files do not link into that tree and remain independently
understandable.

## Validation

The final documentation and skill gate records:

| Check | Result |
| --- | --- |
| Development and read-only source baselines | Passed. Development `main` matched its fetched remote before editing; the source repository remains clean and equal to its fetched remote. |
| Authorized APG4 scope and changed-file classification | Passed. All 22 staged paths are authorized APG4 documentation, publication-excluded evidence, indexes, or the six skill leaves; no unstaged change remains. |
| Superpowers policy and no mechanical-disable claim | Passed. The root reference-only policy is present and is characterized only as behavioral. |
| Exact skill count, direct-child shape, frontmatter, names, trigger descriptions, non-triggers, and local links | Passed. Six exact leaves passed the pinned leaf validator and the repository structural gate; no support directory exists. |
| Authority, worker-report, and project-parameter boundaries | Passed. Semantic inspection and independent per-skill review found no delegation authorization, scope expansion, or ordinary-worker managed-report requirement. |
| Markdown headings, fences, and local links | Passed across all 52 Markdown files. |
| Public confidentiality and public-to-private dependency scan | Passed. Public files contain no private source identity, snapshot, local path, username, or link into `private/`. |
| ADR and exit namespaces and indexes | Passed. ADR sequence is `0001`–`0003`; exit sequence is `00001`–`00006`; filenames, titles, and indexes agree. |
| Provisional maturity and prohibited-claim scan | Passed. All six skills remain `provisional`; clean causal, statistical, universal, stable, and superiority claims are explicitly denied or deferred. |
| No prohibited plugin, profile, adapter, framework, dependency, runtime, scheduler, registry, taxonomy, publication, license, or extra-skill artifact | Passed by exact staged-path and artifact review. |
| External and project license boundaries | Passed. Superpowers remains external MIT-licensed evidence; APG's own distribution license remains deferred. |
| Independent complete staged-diff review | Passed. One fresh non-author reviewer independently reproduced the structural, scenario, transition, sequence, privacy, parity, and whitespace evidence; found no blocker, material finding, or new minor finding; and accepted the candidate staged diff. |
| `git diff --check` | Passed. |
| `git diff --cached --check` | Passed. |
| Source tests and compilation | not run; documentation and skill content only |

## Limitations

- The 18 scenarios are abstract and sample-bound.
- Automatic activation, downstream execution, and comparative advantage were
  not measured.
- Most positive artifacts were plans or dispositions rather than real-project
  execution.
- One concrete synthetic review fixture remains needed.
- Superpowers remained globally installed and may have remained in model
  context.
- Clean post-Superpowers comparison remains deferred.

## No-decommission state and gate

No decommissioning occurred. Readiness remains false until every material
workflow is mapped, APG succeeds in this repository and another real project,
no authority, privacy, destructive-action, or completion-evidence regression
remains, an uninstall rollback plan and preserved source snapshot exist, the
human explicitly approves decommissioning, and post-decommission smoke passes.

APG4 supplies transition coverage and a preserved source snapshot, but it does
not satisfy the real-use, regression, rollback-plan, human-decision, or smoke
requirements.

## Exact dogfooding recommendation

Deliberately use each retained skill when its trigger naturally occurs in APG
and at least one additional real repository. For every use, record the trigger
decision, project-owned parameters, artifact or stop disposition, correction,
authority and privacy result, verification run, and checks intentionally not
run. Include real non-trigger observations. Add a concrete public-safe review
fixture and a schema or contract-change implementation case before requesting
any maturity beyond `provisional`.

## External review requested

External review is requested to **accept APG4 as Complete — six provisional
skills bootstrapped, retain all six skills at `provisional`, and authorize only
the recorded dogfooding and external-review next action**.

That disposition does not promote a skill, decommission Superpowers, resume
APG3, publish APG, choose a license or taxonomy, or authorize another
implementation phase.

## Subsequent correction

External review returned `correction-required`: APG4 authored and validated six
canonical leaves under `skills/` but did not install the `.agents/skills/`
repository projection required for Codex discovery. The omission did not change
the six procedures, 18 scenario dispositions, two corrections, independent
reviews, maturity, provenance, or no-decommission result.

[APG4A](00007-apg4a-codex-repository-skill-discovery-exit.md) later added the
six-link projection as a forward-only integration correction. No APG4 scenario
or review is rewritten as though the projection existed during that work, and
no APG4 or APG4A record claims that explicit or automatic invocation occurred.
