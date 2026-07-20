# ADR 0008: Skill Authoring, Maintenance, and Mechanical Validation

## Status

Accepted

## Date

2026-07-20

## Acceptance authority

The human maintainer's APG11 assignment accepts this decision and authorizes a
maintainer-facing lifecycle guide, one dependency-free read-only checker,
focused tests, legacy-roadmap closure, private development integration, and
managed reports. It does not authorize a seventh skill, a generalized
evaluator, maturity promotion, public release work, dependency changes, or
mutation of external repositories and integrations.

## Context

APG4 through APG10 repeatedly applied the same underlying practices when
creating, correcting, evaluating, projecting, and reviewing skills. Those
practices include choosing one owner, preserving provenance, freezing bounded
scenarios before behavior changes, separating semantic judgment from stable
mechanical constraints, obtaining non-author review, and retaining rollback
evidence. Reconstructing that lifecycle from phase records is now unnecessary
maintenance cost.

The repository also repeats a smaller set of structural checks: canonical leaf
shape, required metadata, adopted headings, catalog agreement, optional support
shape, local-link containment, and checked-in Codex projection identity. These
properties are deterministic enough for repository-owned tooling. Trigger
quality, usefulness, authority, rights, provenance truth, scenario adequacy,
privacy, over-triggering, maturity, and production readiness remain matters of
evidence and review.

The pinned Agent Skills specification permits optional metadata and additional
skill-local files and does not require APG's body headings. APG therefore needs
an explicitly narrower project contract rather than a claim of complete Agent
Skills validation.

## Decision

### Normative owners

[`docs/skill-authoring-and-maintenance.md`](../../../skill-authoring-and-maintenance.md)
is the normative maintainer-facing owner of the APG skill-specific lifecycle.
The project model remains authoritative for general artifact destination and
practice lifecycle policy. `skills/README.md` remains the catalog, discovery
shape summary, and current maturity index; it routes maintenance questions to
the guide instead of redefining its procedure. Provenance records own source,
rights, derivation, and notice facts. Evaluations and exits own bounded evidence
and phase history. The mechanical checker owns only the machine-verifiable
invariants adopted here and in the guide.

APG does not create a seventh skill for authoring skills. Skill authoring is a
maintainer activity with authority, evidence, and repository-policy decisions;
it is not a generally triggerable procedure for task execution.

### Change classes and proportional evidence

APG distinguishes six classes:

1. a new skill;
2. a frontmatter-only discovery correction;
3. a behavior-bearing procedure correction;
4. a support-file or deterministic-helper addition;
5. a maturity-only disposition; and
6. deprecation or removal.

Each class receives evidence, review, records, and rollback proportional to its
effect. One ceremony does not govern all six.

### New-skill threshold

A new skill requires evidence that one coherent reusable problem exists;
existing instructions, skills, project policy, and native capability do not
already own it adequately; a precise trigger and material non-triggers exist;
the procedure is independently removable; authority and project-owned policy
remain outside the skill; source and derivation rights are known; and positive,
non-trigger, edge or stop, and independent-review evidence support retention.
An external source's packaging does not establish an APG owner.

### Behavior-bearing correction contract

Before changing procedure wording, the phase identifies the current owner,
freezes the material gap and affected scenarios, establishes current behavior,
authors independently from source evidence, and defines rollback. One bounded
correction is permitted by default. The corrected owner is then rerun against
all affected positive, non-trigger, and edge or stop cases, the mechanical and
repository regression gates, and fresh non-author review. A phase may declare a
different finite correction bound; silence does not authorize unlimited
iteration.

### Mechanical checker contract

`bin/apg-check-skill-library` validates only the adopted APG subset. It accepts
an explicit root or defaults to the repository containing the command, emits
deterministic text or JSON, returns `0` for compliance, `1` for library
noncompliance, and `2` for usage errors, and performs no repair. It uses the
Python standard library only, performs no Git, network, package-manager, or
subprocess operation, disables Python bytecode writes before loading its helper,
and reports repository-relative paths.

The accepted leaf shape consists of `SKILL.md` and optional nonempty ordinary
directories named `scripts`, `references`, `assets`, or `agents`. `agents` is
reserved for separately justified harness metadata such as
`agents/openai.yaml`; accepting its shape does not authorize or validate a
harness integration. Symlinks below support directories must resolve within the
owning canonical leaf.

The checker uses the following narrow lexical grammar rather than general YAML
or Markdown parsing:

- frontmatter opens with `---` at byte zero and ends at a later line containing
  exactly `---`;
- every column-zero frontmatter mapping key uses ASCII letters, digits,
  underscores, or hyphens followed immediately by one key-terminating colon;
  blank lines, comments, and indented optional metadata remain uninterpreted;
- required `name` and `description` entries are unique top-level, unquoted,
  one-line plain scalars in exact `key: value` form, without inline comments or
  multiline YAML forms;
- headings, inline links, images, and catalog tables are recognized only
  outside backtick or tilde fenced code blocks;
- an accepted link is a same-line inline link or image with an unescaped opener
  and either one literal no-whitespace destination token or an angle-bracket
  destination;
- external schemes and fragment-only destinations are not fetched; a fragment
  on a local destination is removed before resolving; percent encoding is not
  decoded; local destinations are relative to the containing Markdown file and
  must exist within the owning skill leaf; and
- the catalog is the single table immediately following the single exact
  `## APG v0.1 catalog` heading, with the adopted three-column header and
  separator. Arbitrary Markdown tables are not parsed.

The checker enforces canonical shape, required metadata and APG name grammar,
one H1, exactly one of each adopted H2 owner, support-directory shape and
nonemptiness, accepted local-link resolution and containment, catalog
bijection/link/maturity vocabulary, and checked-in Codex projection type, raw
target, resolved identity, and containment. Additional H2 headings are not
prohibited. Optional YAML, unsupported Markdown link forms, support-file
semantics, and harness metadata semantics are not interpreted.

Frontmatter is never scanned as Markdown body content. When a contained support
symlink has a `.md` name and resolves to a regular file, its accepted literal
links are checked relative to the symlink's containing directory.

The checker does not prove trigger quality, semantic usefulness, authority or
privacy correctness, source rights, provenance truth, scenario quality,
over-triggering, client discovery or invocation, maturity fitness, public
release completeness, production readiness, or stable behavior. Passing the
checker cannot change maturity.

### Maturity and roadmap closure

Authoring, correction, publication, discovery, or passing mechanical checks
does not automatically change maturity. APG13 owns the next six individual
maturity dispositions.

APG11 closes the former unnumbered candidate-theme ledger through a durable
record with stable source identities and explicit sub-dispositions for
composite themes. Future ownership closes a legacy question but does not claim
future implementation. APG12 through APG14 remain active, separately authorized
v0.2 phases.

## Alternatives considered

### Retain only ad hoc phase prompts

Rejected. Repeated authoring and correction practice is sufficiently stable to
have one maintainable owner.

### Add a seventh authoring skill

Rejected. The work is project-maintainer governance and would duplicate
existing ownership rather than add one independently triggerable procedure.

### Create a generalized evaluator

Rejected. Semantic evaluation requires frozen scenarios, authority, source
review, and bounded human judgment. Current evidence does not justify a prompt
scorer, harness framework, or dependency.

### Create documentation only

Rejected. The recurring structural invariants are stable and mechanical, and
leaving them manual would preserve preventable drift.

### Create documentation plus a narrow mechanical checker

Accepted. This keeps judgment in the lifecycle while making deterministic
structural constraints repeatable.

### Enforce semantic quality mechanically

Rejected. Structural proxies cannot establish usefulness, authority, rights,
privacy, maturity, or correct behavior.

### Leave the legacy roadmap section open

Rejected. Its questions now have completed, active-owner, conditional, or
terminal dispositions. A closure ledger is clearer than retaining a second
roadmap queue.

## Consequences

- Maintainers receive one skill-specific lifecycle owner without another skill.
- Structural drift receives deterministic, dependency-free diagnostics and
  machine-readable output suitable for later APG12 use.
- The checker deliberately accepts less syntax than the full Agent Skills and
  Markdown/YAML ecosystems; richer forms require an explicit APG contract
  change.
- Semantic and source-review burdens remain visible rather than being
  misrepresented as tool-enforced.
- Legacy themes gain terminal dispositions without collapsing distinct future
  phases or claiming their implementation.

## Subsequent correction: APG11A

APG11A corrects two lexical false negatives without superseding this decision.
The original APG11 helper recognized only exact `name:` and `description:`
prefixes, so quoted, whitespace-before-colon, tabbed, and explicit mapping-key
forms could create a second YAML-equivalent required key while escaping the
uniqueness checks. APG11A adds one bounded column-zero key recognizer and fails
unsupported top-level mapping-key syntax with a deterministic diagnostic.
Required scalar restrictions and uninterpreted indented optional metadata are
unchanged.

The original fence scanner also used its permissive opening-prefix expression
as a closing test. A same-marker line with trailing language text could
therefore close an open fence and expose a hidden structural heading. APG11A
separates opening and closing recognition. A closer must use the same marker,
meet or exceed the opening length, and contain only optional spaces or tabs
after the marker. The corrected visibility path remains shared by headings,
links, and catalog parsing.

Failing-first unit and integration evidence reproduced both APG11 false
negatives before the helper correction. The corrected 15-test unit and 58-test
integration suites, existing regression suites, development and public v0.1.0
dogfood, generated alias and fence cases, no-mutation checks, and independent
review support the forward correction. No skill, projection, maturity,
dependency, command surface, output schema, or accepted APG11 owner changes.

## Rollback

Checker false positives, incompatible future skill syntax, repeated portability
failure, or evidence that the guide assigns the wrong owner require a bounded
superseding decision. Remove the wrapper, helper, tests, and active checker
references atomically; restore the prior catalog and roadmap wording where it
remains accurate; and replace the guide's active ownership through a successor.
Preserve this ADR, APG11 evaluation, exit, and private evidence as history.

APG11 changes no canonical skill leaf or discovery projection, so its rollback
requires no skill-content or projection mutation.

## Deferred decisions

- APG12 owns publication-surface validation and public-sourced user-global
  lifecycle formalization.
- APG13 owns individual post-Superpowers maturity dispositions.
- APG14 owns the public v0.2 release candidate and publication.
- Generalized semantic evaluation remains conditional on a separately frozen
  and authorized design.
