# ChatGPT Manager Skill Topology

## Scope

This document defines the v0.4 topology for capabilities whose primary actor is
the ChatGPT top-level manager. APG30 implements the first namespace, subrouter,
and classified-leaf move. It does not alter public or active v0.3.0, remove a
personal skill, or provide post-restart application-discovery evidence.

Actor and trigger evidence control classification. A skill is not ChatGPT-only
merely because a ChatGPT manager may use it, because its name contains
"composition," or because it participates in a managed phase.

## Canonical and projection shape

ChatGPT-manager leaves use nested canonical ownership:

```text
skills/
├── agentic-praxis-grimoire-workflow/
├── composing-bounded-worker-assignments/
├── ...
└── chatgpt/
    ├── chatgpt-manager-workflow/
    │   └── SKILL.md
    └── composing-approved-roadmap-assignments/
        └── SKILL.md
```

Codex discovery remains flat and source-qualified:

```text
.agents/skills/composing-approved-roadmap-assignments
  -> ../../skills/chatgpt/composing-approved-roadmap-assignments
```

Canonical bytes live only under `skills/chatgpt/<name>/`. A projection is a
relative symbolic link and contains no independent procedure. Catalog names
remain globally unique even when canonical owners are nested.

## Classification

`composing-approved-roadmap-assignments` is the initial ChatGPT-manager leaf.
Its trigger is translation of human-approved roadmap authority into a top-level
coding-agent manager assignment, and its output is specifically consumed at
that management layer.

The following remain general APG capabilities unless later trigger evidence
supports a separate decision:

- `composing-bounded-worker-assignments`, because any Codex manager with
  delegated internal work may need one worker contract;
- `planning-repository-work`, because accepted repository objectives need
  decomposition regardless of the external manager;
- `reviewing-and-verifying-repository-work`, because bounded artifacts and
  results need evidence-backed disposition at multiple levels;
- `designing-significant-changes`, because architecture judgment is not
  ChatGPT-specific; and
- the language, database, testing, debugging, implementation, and synthesis
  owners, whose triggers are technical rather than actor-specific.

Classification changes require their own frozen trigger and non-trigger cases.

## Dedicated subrouter

The `chatgpt-manager-workflow` is a narrow subrouter. It owns selection
only among ChatGPT-manager capabilities. It does not approve work, compose the
result itself, select ordinary Codex process or language skills, dispatch an
agent, accept a result, or continue a roadmap.

The general `agentic-praxis-grimoire-workflow` capability map contains the
subrouter as one capability and does not enumerate each ChatGPT-manager leaf.
When a request clearly names an applicable leaf, explicit selection remains
valid. When ChatGPT-specific selection is ambiguous, the general router may
select the subrouter, which then selects the smallest sufficient ChatGPT leaf
or none.

There is no mandatory router chain. Ordinary Codex managers do not route
through ChatGPT-manager skills, and explicit applicable APG selection does not
need either router.

## Catalog and checker model

APG30 updates the former direct-child assumptions together:

- recursively discover canonical leaves only at allowed owners, initially
  `skills/<name>/SKILL.md` and `skills/chatgpt/<name>/SKILL.md`;
- reject an intermediate directory that masquerades as a leaf or contains an
  unrecognized nested owner;
- derive global identity from frontmatter `name`, not the immediate parent
  depth alone;
- require one unique canonical path, one catalog row, and one flat projection
  for each name;
- validate the catalog link against the canonical path;
- compute each projection's exact relative target from that canonical path;
- keep lifecycle managed-name sets independent of canonical depth;
- allow capability maps to name the ChatGPT subrouter while a checked
  ChatGPT-local map owns its leaves; and
- report canonical, catalog, and projection counts without counting namespace
  directories as skills.

The current-development public projection and candidate checker preserve nested canonical
paths recursively, flat projection link bytes, support files, modes, and
manifest identities. Project- and user-scope lifecycle tools must resolve the
source-declared and verified canonical path rather than assuming
`skills/<name>`.

Public v0.3.0 retains nineteen direct-child canonical leaves and its
schema-version-1 source declarations. Historical v0.1.0 through v0.3.0 policy
remains version-bounded and is not reinterpreted by the development topology.

## Personal hygiene transition summary

The detailed publication-excluded ledger classifies coherent units from three
personal skills without copying private wording. APG31 applies the transition
gate independently:

| Personal capability | APG or project replacement | APG31 disposition |
| --- | --- | --- |
| `docs-only-change-hygiene` | Structured formal/non-phase docs-only defaults and repository-owned checks | Decommissioned after source-qualified shadow, exact restoration, and non-author review |
| `git-history-hygiene` | Structured commit defaults plus repository conventions | Deferred unchanged because the required private routing and destructive-stop boundary remains unresolved |
| `repomap-phase-hygiene` | RepoMap-owned contributor convention, APG structured defaults, and separate private operational owners | Deferred unchanged because a current private caller route remains outside APG31 write authority |

APG31 changes no APG skill. Exact private source locations, bytes, Git
identities, personal details, and machine policy remain publication-excluded
evidence rather than public APG dependencies.

APG31A records the subsequent external smoke as passed without rewriting
APG31's Partial result. It completes the two deferred transitions after a fresh
publication-excluded review: `git-history-hygiene` is scope-reduced after
generalized behavior returns to APG and repository owners, and
`repomap-phase-hygiene` is decommissioned after generalized behavior returns
to current RepoMap owners. APG31A changes no APG skill or router map.

## Transition gate

Each future transition is independently authorized and requires:

1. a coherent-unit owner map that distinguishes APG, repository, personal, and
   machine content;
2. current replacement evidence from the intended source-qualified owner;
3. positive trigger and representative non-trigger observations in fresh
   sessions;
4. proof that duplicate-name discovery is not being mistaken for precedence;
5. no unexplained loss of private-only behavior;
6. an exact retrievable restoration source and rollback procedure;
7. independent review; and
8. explicit human authority for removal or scope reduction.

A failed shadow, missing source qualification, absent restoration evidence, or
material private-only contract stops the transition. APG does not absorb
machine integration, personal flow support, or destructive history-rewrite
authority merely to enable decommission.

## Migration order and rollback

APG30 extended checker, catalog, lifecycle, projection, router-map, and
public-candidate tests before moving a current leaf. It then added the
subrouter and moved one classified leaf in a single reviewable slice. The old
canonical path remains exactly retrievable from the pre-migration commit, and
rollback restores the canonical path, catalog link, router maps, and flat
projection together.

APG31 confirms that personal-skill transitions occur only after the topology
and structured defaults are stable enough to serve as replacement evidence.
Replacement evidence is necessary but not sufficient: unresolved caller
routing or restoration boundaries defer a target independently. A
post-transition application restart remains required before refreshed personal
discovery is claimed.

APG31A closes that external restart boundary and demonstrates the deferred
transition path. Generalized behavior returns to current source-qualified
owners before a personal capability is narrowed or removed; exact private
boundaries remain publication-excluded.
