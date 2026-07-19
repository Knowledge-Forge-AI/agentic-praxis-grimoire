# APG Skill Library

## Current status

APG v0.1 contains six direct-child skills. Every skill is `provisional`: it has
passed structural validation, one positive scenario, one non-trigger scenario,
one edge or stop scenario, and independent review within APG4's recorded limits.
No skill is `evaluated`, `stable`, production-proven, or comparatively superior.

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
| [`composing-bounded-worker-assignments`](composing-bounded-worker-assignments/SKILL.md) | Delegation is already authorized and selected, and one non-trivial worker assignment needs explicit boundaries | `provisional` |
| [`designing-significant-changes`](designing-significant-changes/SKILL.md) | Consequential behavior, architecture, ownership, contracts, safety, or irreversible choices remain unresolved | `provisional` |
| [`planning-repository-work`](planning-repository-work/SKILL.md) | An accepted objective needs dependent steps, cross-file coordination, staged risk reduction, or durable handoff | `provisional` |
| [`implementing-with-test-discipline`](implementing-with-test-discipline/SKILL.md) | A code change benefits from executable behavioral evidence | `provisional` |
| [`debugging-systematically`](debugging-systematically/SKILL.md) | Behavior is failing, inconsistent, flaky, unexplained, or has multiple plausible causes | `provisional` |
| [`reviewing-and-verifying-repository-work`](reviewing-and-verifying-repository-work/SKILL.md) | A bounded repository artifact, change, phase, commit, or worker result needs evidence-backed acceptance, correction, disposition, or a completion claim | `provisional` |

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

A retained skill must continue to:

1. solve one coherent reusable problem;
2. state precise trigger and non-trigger boundaries;
3. preserve authority and project-owned parameters;
4. produce observable evidence, completion, or stop expectations;
5. avoid private conventions and copied external expression;
6. pass representative positive, non-trigger, and edge scenarios;
7. survive independent review and fresh structural validation; and
8. remain removable with its index, provenance, and evaluation references.

Scenario equivalence, over-triggering, authority drift, private leakage,
unsupported machinery, or repeated correction need is evidence to narrow,
deprecate, or remove a skill. Presence in this directory is not permanent
acceptance.

## Evidence and next maturity step

The [APG4 public evaluation summary](../docs/evaluations/apg4-bootstrap-v0.1.md)
records the bounded scenario and review result. The
[Superpowers transition map](../docs/superpowers-transition.md) records coverage
and remaining gaps.

The next evidence step begins with a full restart and fresh RepoMap session
discovery smoke, then broader repeated real-project dogfooding across the six
skills, including positive and material non-trigger decisions, followed by
external review. The sampled RepoMap environment required a full Codex
application restart before newly linked cross-repository skills appeared; this
is an observed bootstrap fact rather than a universal refresh guarantee. No
additional synthetic activation gate is currently required. APG7's executable
observation and projection-tool tests add regression evidence but do not promote
a skill. No skill can become `stable` until it has survived repeated
real-project use and an explicit post-Superpowers review.
