# APG19 Shell and Shell-Test Profiles Evaluation

## Outcome

Partial — Bash, Bats, and Zsh profiles implemented; ZUnit deferred.

APG18 and APG18A completed their accepted decisions, correction, review,
commit, push, remote equality, and managed reports before APG19 began. APG19
accepts [ADR 0014](../adr/2026/07/0014-shell-language-and-shell-test-profile-ownership.md),
retains three provisional profiles, and records one truthful disposition for
each candidate:

| Candidate | Disposition | Candidate corrections |
| --- | --- | ---: |
| [`bash-language-profile`](../../skills/bash-language-profile/SKILL.md) | `retained-provisional` | 1 |
| [`bats-test-profile`](../../skills/bats-test-profile/SKILL.md) | `retained-provisional` | 1 |
| [`zsh-language-profile`](../../skills/zsh-language-profile/SKILL.md) | `retained-provisional` | 1 |
| `zunit-test-profile` | `deferred-source-or-version` | 0 |

## Ownership separation

Bash and Zsh retain distinct language owners. Bats owns test evaluation,
capture, assertions, hooks, TAP/file descriptors, isolation, parallelism, and
harness cleanup without duplicating Bash semantics. ZUnit retains a future
test-harness ownership reservation but no current operational skill. No generic
all-shell profile is adopted.

A task selects process, language, and test owners independently. Ordinary Bash
or Zsh work does not require a test profile. Bats work adds the Bash profile
only when production-language semantics are material. No profile grants action
authority.

## Source identities and maintenance boundaries

Sources were inspected on 2026-07-21. GNU Bash 5.3 documentation and patches
through patch 15, ShellCheck 0.11.0 factual rule evidence, bats-core 1.13.0,
and the official Zsh 5.9.2 release and manual support the retained profiles.
Bash is GPL-3.0-or-later; its manual is GFDL-1.3-or-later without invariant
sections or cover texts. ShellCheck is GPL-3.0. bats-core is MIT. Zsh uses its
permissive distribution notice with file-specific terms for contributions.

ZUnit's latest release is v0.8.2 from 2018. `APG19-ZUNIT-SOURCE-02` identifies
the mutable default-branch observation from 2020; it was documentation-only and
has no semantic revision. Historical upstream runtime evidence ends at Zsh
5.3.1. Local use cannot establish current stable-Zsh support. Re-entry requires
current maintained upstream/runtime evidence and fresh APG verification, or
separate authorization for a legacy-only version-bounded profile.

APG uses independently written synthesis and copies or adapts no source or
private expression or code. Versions and tools are evidence, not universal
project requirements. Each retained profile defines refresh, deprecation,
independent removal, and no-private-restoration boundaries.

## Bash thresholds

| Signal | Green | Yellow | Orange | Red |
| --- | ---: | ---: | ---: | ---: |
| Script physical lines | `<= 150` | `151–300` | `301–500` | `>= 501` |
| Function/top-level command count | `<= 15` | `16–25` | `26–40` | `>= 41` |
| Decision paths | `<= 4` | `5–7` | `8–12` | `>= 13` |
| Nesting depth | `<= 2` | `3` | `4` | `>= 5` |
| Fixed positional parameters | `<= 4` | `5–6` | `7–9` | `>= 10` |
| Mutable globals/cross-function state | `0–1` | `2–3` | `4–6` | `>= 7` |
| Pipeline/process graph breadth | `0–2` | `3–4` | `5–7` | `>= 8` |
| Independent responsibility families | `1` | `2` | `3` | `>= 4` |

## Bats thresholds

| Signal | Green | Yellow | Orange | Red |
| --- | ---: | ---: | ---: | ---: |
| Test-file physical lines | `<= 200` | `201–350` | `351–600` | `>= 601` |
| Test count | `<= 12` | `13–24` | `25–40` | `>= 41` |
| Maximum test-body commands | `<= 15` | `16–25` | `26–50` | `>= 51` |
| Maximum setup/teardown/bootstrap commands | `<= 12` | `13–20` | `21–35` | `>= 36` |
| Maximum helper commands | `<= 20` | `21–35` | `36–50` | `>= 51` |
| Shared fixture/global-state owners | `0–1` | `2–3` | `4–5` | `>= 6` |
| Maximum concurrent background child groups | `0` | `1, owned` | `2–3, owned` | `>= 4`, or any unowned/leaking child |
| Independent responsibility families | `1` | `2` | `3` | `>= 4` |

## Zsh thresholds

| Signal | Green | Yellow | Orange | Red |
| --- | ---: | ---: | ---: | ---: |
| Script physical lines | `<= 200` | `201–300` | `301–500` | `>= 501` |
| Commands in one function or top-level region | `<= 15` | `16–25` | `26–40` | `>= 41` |
| Decision points | `<= 3` | `4–6` | `7–10` | `>= 11` |
| Maximum control/subshell nesting | `<= 2` | `3` | `4–5` | `>= 6` |
| Positional parameters | `<= 3` | `4–5` | `6–9` | `>= 10` |
| Distinct option mutations in one scope | `<= 2` | `3–5` | `6–9` | `>= 10` |
| Mutable global/cross-function parameters | `<= 2` | `3–5` | `6–9` | `>= 10` |
| Autoload/module/hook/ZLE/completion breadth | `<= 2` | `3–5` | `6–10` | `>= 11` |
| External process/pipeline families | `<= 2` | `3–5` | `6–9` | `>= 10` |
| Independent responsibility families | `1` | `2` | `3` | `>= 4` |

## Deferred ZUnit calibration evidence

The following research bands are not an implemented APG contract:

| Signal | Green | Yellow | Orange | Red |
| --- | ---: | ---: | ---: | ---: |
| File physical lines | `<= 150` | `151–300` | `301–500` | `>= 501` |
| Tests per file | `<= 8` | `9–15` | `16–24` | `>= 25` |
| Commands in one test body | `<= 12` | `13–20` | `21–35` | `>= 36` |
| Largest setup/teardown/bootstrap body lines | `<= 25` | `26–50` | `51–80` | `>= 81` |
| Largest helper function lines | `<= 20` | `21–35` | `36–50` | `>= 51` |
| Mutable shared fixture/state domains | `<= 3` | `4–6` | `7–10` | `>= 11` |
| Concurrent cleanup-owned children/jobs | `<= 1` | `2–3` | `4–5` | `>= 6` |
| Independent responsibilities | `1` | `2` | `3` | `>= 4` |

## Structural and semantic results

Every retained profile passed its twelve shared structural cases, twelve
domain-specific cases, exact first values for every threshold band, and the
upper-Orange composite case after one bounded correction. One Red remains Red;
three coupled Yellow signals normally become Orange; two coupled Orange signals
over one owner are presumptively Red absent an accepted cohesive exception.

The correction closed a composite-monster loophole, made state/process
measurements reproducible, added Bats `run`/pipeline false-confidence behavior,
and tightened Zsh's initially unsupported size disparity. Semantic Red stops
cover dynamic execution, destructive targets, protected-data disclosure,
unsafe process/cleanup ownership, false-pass assertions, startup or option
mutation, and meaningful crisis-level growth as applicable.

Generated, vendored, fixture, snapshot, migration, compatibility, and
data-driven artifacts are classified before structural action. A coherent
matrix may receive only the bounded exception stated by its profile. Existing
Red legacy code may receive the smallest safe fix without a new responsibility
or meaningful growth; a major feature remains Red.

## Read-only dogfood

Each retained profile used seven read-only cases across APG and at least one
additional maintained repository, with classified RepoMap examples supplying
non-executable semantic and false-positive evidence. The 21-case retained
ledger covers Green, Yellow, Orange, Red or near-Red, legacy-small-fix,
classified/coherent-large-artifact, and semantic safety or compatibility
behavior. No target source or test was executed or changed as part of dogfood.

## Router, catalog, and distribution

Private development now contains twelve canonical skills, twelve relative
checked projections, six stable process rows, six provisional rows, and eleven
routable non-router capability-map entries. The schema remains version 1.
Focused tests cover exact map/catalog alignment, routes, profile headings and
thresholds, process/domain pairing, stops, known-unmanaged handling, and the
twelve-skill checker count.

`apg-project-skills`, `apg-user-skills`, and public release continue to manage
exactly the six stable v0.2 process skills. Public v0.2.0 and the active
public-backed integration remain 6/6/6. No project/user state schema changes.

## Validation and review

Focused red/green evidence preceded implementation. The resulting tree passes
22 Bats cases; 25 skill-library, 8 release, and 8 user unit cases; and 28
project, 58 checker, 32 release, and 39 user integration cases. Both exact
public-v0.1-conditioned suites ran without a skip. Development checker text and
JSON pass at 12/12/12; the fresh public-v0.2 checkout remains 6/6/6. Python
compilation, Bash syntax for the Bash commands and helper, and all six command
help modes pass. Documentation, privacy, schema, external-state, and
complete-diff results are recorded in the APG19 exit after fresh resulting-tree
review.

Independent source calibration covered Bash, Bats, Zsh, and ZUnit. A separate
private-guidance synthesis preserved project/private ownership. The shared
design critic found no rejection blocker and produced the one bounded
correction applied to each retained candidate. Final non-author semantic,
ownership, integration, and complete-diff reviews govern terminal acceptance.

## Maturity, limitations, and boundary

The three retained profiles begin `provisional`; no existing maturity changes.
ZUnit remains deferred. Thresholds are calibrated guidance, not lint rules.
Exact tools, versions, runners, helpers, commands, platforms, CI, coverage, and
exceptions remain repository-owned.

No root guidance was removed, no private skill was decommissioned, and no
public release or active-integration update occurred. No Go, Ruby, Nix,
PostgreSQL, SQLite, or roadmap-to-manager-prompt skill was implemented.
Application smoke was not run and remains deferred to APG23/APG24. APG20 did
not begin and is not authorized by this evaluation.

## Subsequent APG19A correction

APG19A accepted every substantive APG19 disposition and reproduced one material
Bats fallback-count defect: bats-core v1.13.0 recognizes a supported comment
function form that the APG19 wording could exclude as a comment. APG19A applies
one forward correction so the test-count band uses runner-recognized native and
supported comment-form declarations, while excluding incidental static text and
not authorizing target evaluation merely to count tests. Thresholds, all other
profile semantics, maturity, catalog shape, ZUnit deferral, distribution, and
application-smoke boundaries remain unchanged.

## Subsequent APG22B disposition

APG22B later closes the APG19 ZUnit deferral by retaining a provisional profile
only for exact ZUnit v0.8.2 with Zsh 5.9.2 in the tested environment. The exact
ZUnit v0.8.2 with Zsh 5.3.1 pair is unsupported, and no version range is
claimed. This later disposition does not rewrite the historical APG19 result.
