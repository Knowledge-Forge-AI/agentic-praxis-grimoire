# Skill Authoring and Maintenance

## Purpose and ownership

This guide is the normative maintainer-facing procedure for creating,
correcting, supporting, maturing, deprecating, or removing an APG skill. The
[project model](project-model.md) owns general artifact destination and practice
lifecycle policy. The [skill catalog](../skills/README.md) owns current leaves,
discovery shape, and maturity labels. [Provenance](provenance.md) owns source,
rights, derivation, and notice records. Evaluations and exits own bounded
evidence and phase history.

This procedure does not grant authority. Work requires a human-authorized phase
or assignment, and repository policy continues to own project-specific
parameters.

## Choose the owner

| Need | Destination |
| --- | --- |
| A concise rule that must apply to nearly all repository work | Root instruction |
| A demonstrated gap in an existing triggerable procedure | Existing skill correction |
| One coherent reusable problem with no adequate existing owner | New skill |
| Detailed guidance needed only after one skill triggers | Supporting reference |
| A stable skill-local operation that benefits from deterministic execution | Deterministic helper |
| Architecture, authority, privacy, test, release, or repository-specific requirements | Project policy |
| An observation, scenario result, source mapping, or bounded review | Evidence only |
| Duplicated, unjustified, incompatible, or excessively project-specific material | Rejection |

External packaging, repeated slogans, or authoritative tone do not establish an
APG owner. Prefer the smallest existing owner that can address a demonstrated
gap without broadening its trigger.

## Lifecycle

1. Authorize and define the concrete problem.
2. Inspect existing owners, repository policy, and native capability.
3. Inventory source identity, publication status, reuse rights, and notice
   duties.
4. Classify the change as new skill, frontmatter-only correction,
   behavior-bearing correction, support/helper addition, maturity-only
   disposition, or deprecation/removal.
5. Freeze acceptance, representative non-trigger, edge or stop, and rollback
   evidence proportional to the change.
6. Establish baseline behavior when behavior will change.
7. Author the smallest APG-native artifact in its owning destination.
8. Run the affected scenarios, `apg-check-skill-library`, and repository gates.
9. Obtain fresh non-author review of the resulting state.
10. Record provenance, maturity, maintenance impact, disposition, limitations,
    and rollback.

Do not infer permission to expand the change from this lifecycle. An unmet
authority, privacy, rights, or safety condition stops the work.

## Change-class matrix

| Class | Required evidence | Default correction bound | Mechanical checks | Independent review | Records | Rollback | Maturity effect |
| --- | --- | --- | --- | --- | --- | --- | --- |
| New skill | Ownership gap; source rights; multiple independent positive and non-trigger families; edge or stop behavior | One candidate plus one bounded material correction | Full library, catalog, projection, link, and repository gates | Fresh procedure and complete-diff review | Public evaluation, provenance, catalog, ADR or exit as required; private source evidence when needed | Remove leaf, projection, catalog row, active references, and support while preserving history | None unless separately authorized |
| Frontmatter-only discovery correction | Reproduced discovery gap and unaffected procedure baseline | One correction | Metadata, catalog, projection, discovery-focused regression | Fresh non-author leaf review | Evaluation/provenance/exit update proportional to the correction | Restore prior frontmatter and rerun discovery checks | None |
| Behavior-bearing procedure correction | Frozen gap; current and candidate results on the same affected positive, non-trigger, and edge or stop cases | One bounded correction unless the phase declares another finite bound | Full checker plus affected repository regression | Fresh non-author procedure and resulting-state review | Public evaluation and provenance; private exact evidence when needed | Restore prior leaf, rerun frozen cases and gates, supersede the decision if material | None unless separately authorized |
| Support file or deterministic helper | Demonstrated leaf-local need, interface, safety boundary, dependency status, and executable examples where applicable | One bounded correction | Leaf shape, links, helper syntax and behavior, repository regression | Fresh code/content and safety review | Catalog or guide only when behavior changes; provenance/evaluation as needed | Remove support and references together; restore prior leaf | None |
| Maturity-only disposition | Complete evidence inventory against the accepted maturity criteria | No procedure correction; any correction becomes another class | Full current checker and regression evidence | Fresh per-skill disposition review | Catalog, evaluation, provenance, ADR/exit as required | Revert label and supersede unsupported disposition; do not erase evidence | Only the explicitly authorized label change |
| Deprecation or removal | Replacement or obsolescence evidence, dependency/reference inventory, migration and history plan | One bounded reconciliation pass | Full checker during deprecation; post-removal catalog/projection/reference gates | Fresh ownership, impact, and complete-diff review | Catalog, provenance, roadmap/evaluation/exit, and replacement links | Restore retained version when safe or supersede with a corrected transition | `deprecated` only when explicitly authorized; removal is not maturity |

Exact commands, scenario counts, and record depth remain phase- and
repository-owned. The defaults above are not universal gates for unrelated
projects.

## New-skill threshold

Retain a new skill only when all of the following are supported:

- one coherent reusable problem exists;
- instructions, existing skills, project policy, and native capability do not
  already own it adequately;
- the trigger is precise and material non-triggers are explicit;
- the procedure is independently removable;
- authority and project-owned policy remain outside the skill;
- source and derivation rights are known; and
- representative positive, non-trigger, edge or stop, and independent-review
  evidence supports retention.

Reject or route elsewhere when any missing condition is structural rather than
correctable within one bounded iteration.

## Source-derived work

Record one APG provenance mode:

- `copied`: expression is reproduced substantially verbatim;
- `adapted`: recognizable expression or structure is modified;
- `synthesized`: new APG-native expression combines evaluated ideas and project
  evidence without preserving source expression;
- `inspired`: a source prompted investigation but no material expression or
  procedure was retained.

External license labels do not replace complete rights and notice review for
copied or adapted expression. Preserve required notices before adoption.
Frequency, source ownership, or permissive-looking metadata does not establish
semantic value or APG authority.

## Scenario guidance

Use representative positive, non-trigger, and edge or stop behavior without a
fixed universal count. A new skill normally needs multiple independent positive
and non-trigger families. A frontmatter-only correction may use focused
discovery cases. A behavior-bearing correction compares current and candidate
behavior against the same frozen cases. Support/helper changes add direct
interface, failure, and safety evidence appropriate to the helper.

Comparative A/B evidence is optional unless a phase expressly makes it part of
the claim. Passing prose inspection is not a substitute for executable evidence
when behavior is deterministic and testable.

## Maintenance, deprecation, and removal

Re-evaluate an owner when evidence shows over-triggering, authority drift,
source or license change, changed harness discovery, repeated corrections,
stale project assumptions, better native capability, overlap with another
owner, or a credible deprecation/removal need.

Repeated correction is a design signal, not permission for indefinite editing.
Stop and reconsider the owner when the declared correction bound is exhausted
or when a correction changes the original problem, authority, or safety model.

Deprecation keeps the leaf only while an explicit transition needs it and uses
the `deprecated` catalog maturity when authorized. Removal reconciles the
canonical leaf, discovery projection, catalog, provenance, evaluations, active
references, replacement guidance, and rollback. Historical ADRs, exits, and
evaluations remain intact.

## Mechanical checker

Run:

```text
bin/apg-check-skill-library [--root <path>] [--format text|json]
bin/apg-check-skill-library --help
```

The default root is the repository containing the command. `--root` permits
read-only validation of another APG-shaped tree. Exit `0` means the adopted
mechanical subset passed; exit `1` reports library noncompliance; exit `2`
reports command-line misuse.

The checker validates:

- a real canonical `skills/` tree, regular `skills/README.md`, regular
  `SKILL.md` leaves, and contained optional `scripts`, `references`, `assets`,
  or `agents` directories;
- APG's plain-scalar `name` and `description` subset, name grammar, directory
  agreement, uniqueness, `Use when` descriptions, one H1, and exactly one of
  each adopted H2 owner;
- nonempty support directories and contained support symlinks;
- accepted same-line literal Markdown links and images outside fenced code,
  resolved from the containing Markdown file and contained within the leaf;
- the exact catalog table under `## APG v0.1 catalog`, including canonical
  bijection, links, trigger cells, and maturity vocabulary; and
- exact checked-in `.agents/skills/<name> -> ../../skills/<name>` projections,
  resolved identity, and containment.

The parser deliberately does not implement general YAML or Markdown. Every
column-zero frontmatter mapping key must contain only ASCII letters, digits,
underscores, or hyphens followed immediately by its key-terminating colon.
Blank lines and comments remain accepted, and indented optional metadata is
uninterpreted. Required frontmatter values must use exact `name: value` and
`description: value` syntax as top-level, unquoted, one-line plain scalars
without inline comments. Unsupported top-level key syntax fails closed. Link
recognition is limited to unescaped same-line inline link/image syntax with a
literal token or angle-bracket destination; external schemes and fragment-only
references are not fetched, local fragments are removed before resolution,
and percent escapes are not decoded. Headings, links, and the catalog are
recognized only outside backtick or tilde fenced code. A closing fence must use
the opening marker character at least as many times and may contain only spaces
or tabs after the marker. Frontmatter is not scanned as Markdown. A contained
`.md` support symlink is scanned with local destinations resolved from the
symlink's containing directory. Unsupported Markdown forms receive no semantic
validation.

The checker cannot prove trigger quality, usefulness, authority, privacy,
source rights, provenance truth, scenario quality, client discovery or
invocation, over-triggering, maturity fitness, public-release completeness,
production readiness, or stable behavior. Those remain evidence and review
responsibilities. Passing the checker does not authorize a change or alter
maturity.

Public release completeness is mechanically owned by `apg-public-release` and
the strict public-surface policy under ADR 0009. That release gate composes the
skill-library checker but does not change this lifecycle, validate semantic
skill quality, or authorize maturity promotion.

Public v0.2.0 carries the six ADR 0010 `stable` dispositions without changing a
skill procedure. APG14 publication evidence is distribution evidence; future
skill correction, maturity rollback, deprecation, or removal continues to
require this lifecycle and separate authority.
