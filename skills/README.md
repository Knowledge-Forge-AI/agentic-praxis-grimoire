# APG Skill Library

## Current status

APG contains six direct-child skills. APG13 individually reviewed and promoted
all six current catalog entries to `stable` after repeated real use,
representative non-triggers, edge or stop behavior, post-Superpowers evidence,
complete regression, and fresh non-author review. Stability means suitability
for routine bounded use within each recorded trigger and project boundary; it
does not mean production warranty, universal applicability, automatic
invocation, or comparative superiority.

Public v0.2.0 appends one intentionally squashed release commit and annotated
tag to the preserved public v0.1.0 history and supplies the maintainer's
separately managed user-global Codex source. Superpowers was
subsequently decommissioned, and a bounded fresh RepoMap smoke discovered all
six skills, successfully applied the review skill, passed managed checks, and
preserved the target repository. These are distribution and post-transition
evidence; they do not promote any skill.

[APG10](../docs/evaluations/apg10-karpathy-guidelines-evaluation.md) evaluated
one experimental source under frozen concealed-source scenarios. Existing
owners already handled assumptions, alternatives, traceability, speculative
scope, necessary consistency work, and proportional escalation. Two independent
positive scenarios supported one correction to
`implementing-with-test-discipline`: when policy and removal authority are
clear, its coherent slice now includes locally owned code or test artifacts
whose sole purpose ended because of the authorized change. Unrelated cleanup
and project-owned lifecycle decisions remain outside that rule. No other leaf
changed, no seventh skill was added, and all six remain `provisional`.

APG3 remains a truthful blocked experiment. It stopped before its clean
comparison could begin and authored no candidate. APG4 uses a separately
authorized bootstrap standard; it does not rewrite APG3 or claim clean A/B
evidence.

The canonical APG skill sources live under `skills/`. Codex repository
discovery is supplied by the checked-in `.agents/skills/` directory, whose six
entries are relative symbolic links to these canonical leaves. The projection
contains no independent skill content and does not change maturity. Current
[official Codex skill documentation](https://learn.chatgpt.com/docs/build-skills)
identifies `.agents/skills` as a repository discovery location and states that
Codex follows symlinked skill folders.

The [APG v0.1 bootstrap model](../docs/bootstrap-v0.1.md) defines maturity,
acceptance, rollback, dogfooding, and later clean-evaluation requirements.

[APG5](../docs/evaluations/apg5-first-codex-dogfooding.md) records the first
real explicit-use observation: six-skill discovery passed and
`reviewing-and-verifying-repository-work` produced an evidence-backed `pass` in
the APG private working repository. Automatic selection was not evaluated, and
all six skills remain `provisional`.

[APG6](../docs/evaluations/apg6-repomap-cross-repository-dogfooding.md) records
the first successful additional-repository use. RepoMap supplied one read-only
design observation using `designing-significant-changes` and the review skill,
plus one accepted documentation-only implementation and closeout using
`planning-repository-work` and the review skill. Material non-triggers were
proportionate, and the review leaf received one evidence-backed frontmatter
discovery correction for bounded repository artifacts. No procedure changed,
automatic selection was not measured, and every skill remains `provisional`.

[APG7](../docs/evaluations/apg7-project-local-projection-tooling.md) records one
real APG executable observation for `implementing-with-test-discipline` and a
26-family behavioral suite plus disposable project-local lifecycle. Design,
planning, review, and bounded reviewer-assignment procedures were used within
their triggers; debugging was a material non-trigger. This is tooling evidence,
not automatic-selection, comparative, stable-maturity, or production-readiness
evidence. Every skill remains `provisional`.

APG7A adds a bounded correction observation for `debugging-systematically`,
`implementing-with-test-discipline`, and the review skill. The semantic ignore
override was reproduced, focused tests failed against APG7 production, and the
corrected 28-family suite and disposable recovery control passed. Planning and
significant-change design remained material non-triggers. This evidence adds no
maturity transition; every skill remains `provisional`.

[APG8](../docs/evaluations/apg8-repomap-managed-projection-adoption.md)
records the first real-project managed adoption and check. Planning and review
applied to the bounded deployment and evidence gate; significant-change design,
implementation test discipline, and systematic debugging remained material
non-triggers. Six existing RepoMap links, user-owned exclusion bytes, and the
tracked repository were preserved. This evidence adds no maturity transition;
every skill remains `provisional`.

[APG13](../docs/evaluations/apg13-six-skill-post-superpowers-stability-review.md)
separately inventories the complete evidence for each leaf and applies one
frozen positive, non-trigger, and edge or stop family per skill. All six current
leaves passed without a procedure correction and remain byte-identical to the
APG12A baseline. Six fresh final per-skill reviews returned `accept-stable`.

## Canonical leaf and discovery shape

Each canonical APG skill source is a direct child of `skills/`:

```text
skills/
└── <skill-name>/
    ├── SKILL.md
    ├── scripts/       # optional deterministic helpers
    ├── references/    # optional detailed guidance
    └── assets/        # optional templates or media
```

`SKILL.md` is required. Supporting directories are optional and exist only when
the skill actually uses them. APG v0.1 needs no support directories.
Harness-specific metadata, such as an `agents/openai.yaml` file, may be added
only when a target harness and validation need justify it.

Codex uses a separate repository-local projection:

```text
.agents/
└── skills/
    └── <skill-name> -> ../../skills/<skill-name>
```

Every APG v0.1 projection entry is a relative symbolic link to one matching
canonical leaf. Canonical documentation, provenance, maturity, and evaluation
records continue to identify `skills/`; `.agents/skills/` owns discovery layout
only. Separate opted-in Git worktrees may use `apg-project-skills` to manage
machine-local absolute links to the same leaves with strict Git-local ownership
and exclusion. [The projection guide](../docs/project-skill-projection.md)
defines that installation and rollback boundary. Other harness projections
require separate evidence and authorization.

This shape follows the Agent Skills specification pinned for APG0 at
[`agentskills/agentskills@38a2ff8`](https://github.com/agentskills/agentskills/blob/38a2ff82958afee88dadf4831509e6f7e9d8ef4e/docs/specification.mdx).
Future work must re-evaluate compatibility against an explicitly recorded newer
snapshot rather than silently changing the APG0 basis.

## APG v0.1 catalog

| Skill | Trigger boundary | Maturity |
| --- | --- | --- |
| [`composing-bounded-worker-assignments`](composing-bounded-worker-assignments/SKILL.md) | Delegation is already authorized and selected, and one non-trivial worker assignment needs explicit boundaries | `stable` |
| [`designing-significant-changes`](designing-significant-changes/SKILL.md) | Consequential behavior, architecture, ownership, contracts, safety, or irreversible choices remain unresolved | `stable` |
| [`planning-repository-work`](planning-repository-work/SKILL.md) | An accepted objective needs dependent steps, cross-file coordination, staged risk reduction, or durable handoff | `stable` |
| [`implementing-with-test-discipline`](implementing-with-test-discipline/SKILL.md) | A code change benefits from executable behavioral evidence | `stable` |
| [`debugging-systematically`](debugging-systematically/SKILL.md) | Behavior is failing, inconsistent, flaky, unexplained, or has multiple plausible causes | `stable` |
| [`reviewing-and-verifying-repository-work`](reviewing-and-verifying-repository-work/SKILL.md) | A bounded repository artifact, change, phase, commit, or worker result needs evidence-backed acceptance, correction, disposition, or a completion claim | `stable` |

These functional groupings do not adopt a category-directory taxonomy. A skill
retains one canonical leaf and may be discovered through more than one concept.

## Procedure and project-policy boundary

Each leaf owns one reusable procedure after its trigger is satisfied. The
target repository or current task continues to own authority, architecture,
privacy, exact scopes, test commands, coverage policy, branch and worktree
workflow, commits, reviews, pushes, publication, reports, rollback, and
destructive actions. A skill consumes those parameters; it does not invent or
universalize them.

The bounded-assignment skill composes one assignment only. It does not authorize
or dispatch delegation, and ordinary internal workers return through the agent
harness rather than managed report commands.

## Acceptance and maintenance

The [skill authoring and maintenance guide](../docs/skill-authoring-and-maintenance.md)
is the normative owner for new skills, frontmatter and behavior-bearing
corrections, support additions, maturity-only dispositions, deprecation, and
removal. Retained leaves continue to require a coherent reusable problem,
precise trigger and non-trigger boundaries, project-owned authority, observable
evidence or stop behavior, appropriate provenance, representative scenarios,
independent review, structural validation, and a removal path. This catalog
summarizes current state; it does not redefine that procedure.

`bin/apg-check-skill-library` validates the adopted mechanical leaf, catalog,
link-containment, and checked-in projection subset. A pass does not establish
semantic usefulness, rights, privacy, discovery, maturity, or stability.

## Current maturity evidence and release boundary

The [APG4 public evaluation summary](../docs/evaluations/apg4-bootstrap-v0.1.md)
records the bounded scenario and review result. The
[Superpowers transition map](../docs/superpowers-transition.md) records coverage
and remaining gaps.

The fresh RepoMap discovery smoke, APG10 source-disposition review, APG11
maintenance formalization, APG12 distribution validation, APG12A correction,
and APG13 individual maturity review are complete. ADR 0010 records positive,
representative non-trigger, edge or stop, real-use, correction, regression,
authority, privacy, and rollback evidence for each skill. All six current
leaves passed their frozen applications and final non-author reviews without an
APG13 procedure correction.

Clean A/B superiority and a positive use in a second repository are valuable
evidence but are not independent stability blockers under ADR 0006. A concrete
unresolved material authority, privacy, safety, or procedure defect may block an
individual skill. The current catalog is `stable`. Public v0.1.0 retains its
historical provisional catalog; public v0.2.0 contains the six stable leaves.
APG14 changes no skill procedure or maturity row. No successor phase begins
automatically.
