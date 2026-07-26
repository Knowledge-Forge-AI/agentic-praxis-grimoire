# APG30 ChatGPT-Manager Topology and Subrouter Evaluation

## Scope

Phase ID: `APG30`

APG30 implements the topology portion of ADR 0022. It adds one
ChatGPT-manager namespace and subrouter, moves the existing
`composing-approved-roadmap-assignments` owner without changing its bytes or
maturity, and updates current-development checker, lifecycle, projection,
release-policy, test, and documentation owners.

APG30 does not modify a personal skill, public or active v0.3.0, application
configuration, a target repository, or release refs. Post-restart application
discovery remains APG31's entry gate.

## Frozen behavior

Thirty cases were frozen before production implementation:

- ten direct/nested discovery, catalog, support, depth, and global-identity
  cases;
- ten flat-projection, project/user lifecycle, historical-source, public
  projection, and rollback cases; and
- ten router/subrouter selection, non-trigger, metadata, and authority cases.

The cases preserve explicit leaf selection, allow the subrouter to select one
smallest sufficient manager leaf or none, reject cyclic or cross-domain map
ownership, and create no mandatory router chain.

## Resulting topology

| Surface | Result |
| --- | --- |
| Canonical leaves | 22 |
| Catalog rows | 22 |
| Flat Codex projections | 22 |
| Stable rows | 14 |
| Provisional rows | 8 |
| General-router entries | 20: nineteen ordinary non-ChatGPT leaves plus the ChatGPT subrouter |
| ChatGPT-local entries | 1: `composing-approved-roadmap-assignments` |
| Total checked route edges | 21 |

Canonical discovery accepts exactly:

```text
skills/<name>/SKILL.md
skills/chatgpt/<name>/SKILL.md
```

The `skills/chatgpt/` directory is not a skill. Identity remains the globally
unique frontmatter name. Catalog links and flat projection targets name the
exact canonical path. Unknown namespaces, unsupported depth, namespace-level
skill declarations, direct/nested duplicates, stale catalog links, escaping
links, and incomplete or cross-domain router maps fail closed.

## Lifecycle and compatibility

Project and user lifecycle owners resolve each skill through its
source-declared canonical path. Flat discovery names and state schema remain
unchanged. Focused evidence covers current-development default and subset
installation, direct-to-nested user update, nested-to-direct rollback, and
restoration after a failed transition.

Historical public v0.1.0 through v0.3.0 policy remains version-bounded and
direct-child. Current-development policy carries the two nested ChatGPT paths.
A disposable candidate preserves nested paths, support files, modes, and raw
flat-link bytes without publishing a release.

## Skill disposition

`chatgpt-manager-workflow` is retained `provisional`. It owns only selection
among ChatGPT top-level-manager capabilities. It cannot approve or revise a
roadmap, compose an assignment, select ordinary Codex capabilities, dispatch
or execute work, review or accept results, or continue automatically.

`composing-approved-roadmap-assignments` remains `provisional`. Its
`SKILL.md` bytes are unchanged by the move. The general router no longer
enumerates it; the ChatGPT-local map owns its one route.

## Python structure disposition

The repository has no configured Python structural analyzer, so APG fallback
counts were used. Nested discovery and router-map validation were extracted
into a focused module rather than adding a new responsibility to the legacy
checker. Project canonical discovery was decomposed before adoption so no
newly changed callable retained a Red signal.

The checker remains a pre-existing Red-size module at 1,080 lines, compared
with 1,073 at entry. The user lifecycle owner crosses from the 1,000-line
Orange ceiling to 1,015 lines, so APG30 records an explicit bounded new
Red-size exception. The retained growth is one cohesive source-path resolution
change for the existing lifecycle responsibility; frontmatter and canonical
path mapping moved to the topology helper, adverse exact-set and direct/nested
transition tests pass, and rollback is the complete APG29 direct-path tree.
Any further growth requires decomposition. The current public-release owner
remains pre-existing Red-size with only declarative policy growth. The Orange
pytest runner adds only explicit loading of its pinned xdist and pytest-cov
plugins so the public candidate's disabled-autoload environment retains the
accepted component coverage gate.

The three initial new test-file Red crossings were decomposed before
acceptance. APG30-specific topology contracts now have independent Orange
unit and Yellow integration owners. The isolated-pytest assertions remain in
the canonical runner unit owner at 597 lines, below its 598-line entry size
and within the Orange band. The shared
checker cases and user lifecycle integration owner also remain at their prior
Orange levels. Three
pre-existing Red integration or checker owners receive only the smallest
cohesive fixture and assertion changes required by the accepted topology. No
test module crosses into a new Red level.

## Verification summary

The two disjoint focused affected pytest lanes pass 313 tests with one
pre-existing phase-evidence skip and 706 subtests. The isolated-runner
regression passes five focused tests, and the complete unit component passes
283 tests at 1,544/1,928 covered branches. Source/mirror inventory, Python compilation,
affected command help, current checker text and JSON, and public v0.3 checker
text and JSON pass. Independent review, disposable candidate, record identity,
Markdown/link/privacy, and whitespace results are recorded in exit 00049 and
the managed APG30 report.

No combined, readiness, smoke, or release suite was run. The exact focused
selection expressed the affected unit and integration boundary reliably.

## Disposition

Complete — nested ChatGPT-manager topology and subrouter implemented.

Application discovery is neither tested nor inferred in APG30. APG31 may
begin only after APG30 is committed, pushed, remote-equal, fully reported, and
followed by a full Codex application restart.
