# APG18 Python Language Profile Evaluation

## Outcome

Complete — language-profile contract accepted and Python profile implemented.

APG17A completed its record correction, independent review, commit, push,
remote-equality, and managed reports before APG18 began. APG18 accepts
[ADR 0012](../adr/2026/07/0012-language-profile-contract-and-warning-levels.md),
adds the normative [language-profile contract](../language-profile-contract.md),
and retains exactly one provisional
[`python-language-profile`](../../skills/python-language-profile/SKILL.md).

No root guidance was migrated or removed. No private skill was decommissioned.
No other language profile, public release, distribution broadening, or APG19
work occurred.

## Contract clarifications

The accepted contract uses complete textual labels:

- `Green — routine`;
- `Yellow — caution`;
- `Orange — warning`; and
- `Red — crisis / stop`.

Levels classify one coherent current decision, not an author or repository.
The highest justified materially applicable level controls. No level grants
action authority. Stricter repository policy controls; relaxation applies only
to a profile default and requires accepted scope, rationale, evidence,
validation, and rollback. Superior safety, privacy, compatibility,
destructive-action, and task-authority rules cannot be relaxed by a profile.

Orange permits bounded continuation after an explicit local decision,
rationale, rollback, and focused validation. Red stops unsafe action or new
crisis-level growth until decomposition, an accepted bounded exception, or the
required governing authority resolves it.

The contract classifies generated, vendored, protocol, migration, snapshot,
machine-produced, test, and legacy artifacts before applying hand-written-code
structural defaults. Classification does not suppress a semantic Red stop.
Existing Red legacy code may receive the smallest safe fix without independent
responsibility or meaningful growth; it is not a loophole for a major feature.

## Python threshold contract

These defaults guide maintained hand-written Python. They are not linter claims
or automatic architecture decisions.

| Signal | Green | Yellow | Orange | Red |
| --- | ---: | ---: | ---: | ---: |
| Module physical lines | `<= 400` | `401–800` | `801–1,000` | `>= 1,001` |
| Callable statements | `<= 20` | `21–35` | `36–50` | `>= 51` |
| Cyclomatic complexity | `1–5` | `6–10` | `11–20` | `>= 21` |
| Branches | `<= 5` | `6–8` | `9–12` | `>= 13` |
| Nesting depth | `<= 2` | `3` | `4–5` | `>= 6` |
| Explicit arguments excluding a conventional receiver | `<= 3` | `4–5` | `6–9` | `>= 10` |
| Local bindings | `<= 8` | `9–12` | `13–15` | `>= 16` |
| Independent responsibility families | `1` | `2` | `3` | `>= 4` |

The skill defines reproducible fallback measurements and defers exact counting
to a repository's configured analyzer when present. It does not silently
compare incompatible analyzer counts. Responsibility count is an auditable
list of independent behavior families or external contracts; helpers serving
one cohesive outcome do not automatically count separately.

Three or more related, independent Yellow signals within one coherent decision
normally justify Orange unless recorded evidence demonstrates a correlated
false positive. Unrelated findings do not form a numeric score. One metric may
set a response level but does not mechanically select an extraction design.

## Source and calibration basis

Sources were inspected on 2026-07-21. Python 3.14.6 language and standard-library
documentation, PEP 8, PEP 387, PEP 484, PEP 544, current Python Packaging User
Guide material, Pylint 4.0.6, current Ruff settings, and Radon 6.0.1 supplied
semantic and numeric evidence. Python documentation is PSF License Version 2,
with examples additionally available under 0BSD. The inspected PEPs state
public-domain or current PEP reuse terms. The Packaging User Guide is CC BY-SA
3.0, Pylint is GPL-2.0, and Ruff and Radon are MIT.

Pylint and Ruff defaults supplied the 1,000 module-line, 50 statement, 10
complexity, 12 branch, 5 argument, 15 local, and 5 nesting evidence points.
Radon's published ranks supplied complexity bands. Read-only distributions from
APG and one representative maintainer repository supplied upper-tail and
false-escalation evidence. Intermediate bands are APG calibration choices.

APG uses independently written synthesis and copies or adapts no external or
private expression, table structure, or code. The profile requires no named
tool or third-party dependency. Python versions, analyzers, frameworks,
packaging, dependencies, and exact commands remain repository-owned.

## Frozen scenarios and correction

The frozen contract contained twenty-four families:

- nine structural-growth cases;
- nine Python-semantic cases; and
- six project-boundary, non-trigger, and process/domain-pairing cases.

The first complete application passed every family. Final semantic review then
found that public source/maintenance boundaries and several proportional
semantic classifications were not explicit enough in the canonical profile.
One bounded correction added source identity and reuse, refresh and removal,
and explicit responses for import initialization, circular dependencies,
global state, advanced typing, dynamic imports, subprocesses, and shell
construction.

A fresh complete corrected-candidate application passed `24/24`. No second
correction was needed. The retained candidate correctly triggers or declines,
selects the expected response, preserves repository policy and authority,
avoids mandatory broad refactoring, and keeps domain judgment separate from
process procedure.

## Read-only real-code dogfood

Seven representative files were measured without modification across APG and
one additional maintainer repository:

| Result | Count |
| --- | ---: |
| Green | 1 |
| Yellow | 1 |
| Orange | 4 |
| Red | 1 |

The sample included a small module, a serialization/publication boundary, a
process-supervision module, an oversized legacy release module, a coherent
integration-test matrix, a classified migration, and a combined
publication/concurrency boundary. It exercised line count, callable size,
complexity, branches, nesting, arguments, locals, combined signals, legacy
minimal fixes, test coherence, migration ownership, API compatibility, and
concurrency lifecycle.

The Red legacy case stopped meaningful new growth without demanding an
unrelated wholesale rewrite. The test and migration cases avoided structural
false escalation without weakening compatibility, destructive-action, or
safety stops. The dogfood required no threshold correction.

## Router and catalog integration

Private development now contains:

```text
9 canonical skills
9 checked-in relative projections
6 stable process rows
3 provisional rows
8 routable non-router capability-map entries
```

The map adds one `Python language profile` entry and excludes the router. The
router procedure remains unchanged and supports one primary process capability
plus a separately applicable domain profile. A Python behavior change may keep
`implementing-with-test-discipline` primary while applying the profile for
Python judgment. A Python public-API review may keep
`reviewing-and-verifying-repository-work` primary while applying the profile
for compatibility judgment.

Current-development compatibility recognizes the router, synthesis skill, and
Python profile as known unmanaged skills while project installation continues
to manage only the six stable v0.2 skills. Public v0.2.0 remains `6/6/6`.
Project, user, and release state schemas remain version 1.

## Validation and external state

The resulting tree passed 22 Bats cases; 21 skill-library, 8 release, and 8
user unit cases; and 28 project, 58 checker, 32 release, and 39 user integration
cases. Both exact public-v0.1 compatibility tests ran without a skip.
Development checker text and JSON passed at 9/9/9, and a fresh public-v0.2
checkout passed at 6/6/6. Python compilation, Bash syntax, six command-help
modes, Markdown structure and links, privacy, counters, projection targets,
schema versions, and protected-surface hashes also passed.

The public repository, reference repository, RepoMap checkout, active public
integration, and fresh public checkout remained clean and unchanged. Dogfood
was read-only. APG18 modified only the private development repository.

## Maturity, smoke, and boundaries

The Python profile begins `provisional`. The six process skills remain
`stable`; the router and synthesis skill remain `provisional`. APG18 supplies no
maturity promotion.

Fresh-session application discovery and explicit-use smoke were intentionally
not run. APG23 owns aggregate v0.3 readiness smoke; APG24 owns public-candidate
and active-integration release-preparation smoke. No selector or invocation
observation is fabricated here.

The profile is calibrated guidance, not semantic enforcement. Analyzer counts
are version-sensitive; responsibility is reviewer-assessed; project exceptions
remain contextual. Cross-repository use, aggregate discovery, maintenance cost,
maturity, distribution, and public integration remain future evidence.

APG19 has not started and is not authorized by this evaluation.

## APG18A subsequent current-owner correction

APG18A found that several publishable current-owner documents still described
the APG17 eight-skill state, ADR 0012 as proposed, or only the router and
synthesis skill as provisional development additions. It corrected README and
the project-projection, user-integration, public-release, and roadmap owners to
the accepted APG18 state.

The correction changes no APG18 semantic decision, profile or threshold byte,
capability map, catalog maturity, projection, test, schema, managed default,
public release, active integration, or external repository. Historical APG15
through APG17 records remain truthful in their original phase context.

The maintainer's APG18A-then-APG19 assignment conditionally authorizes APG19
only after APG18A is independently accepted, committed, pushed, remote-equal,
and fully reported. This subsequent note does not retroactively make APG19 part
of APG18 authority. Application smoke remains deferred to APG23/APG24.
