# APG82 APGR CLI, distribution, configuration, and artifact foundation

Status: implementation complete in the candidate tree; configured qualification,
exact-tree review, integration identity, and terminal artifacts are commit gates
recorded outside this tracked evaluation until their resulting objects exist.

APG82 begins from exact APG81H development main and establishes the settled
public identities: project Agentic Praxis Grimoire, distribution
`agentic-praxis-grimoire`, package `agentic_praxis_grimoire`, and executable
`apgr`. `src/agentic_praxis_grimoire/VERSION` is the one package version
resource, and `pyproject.toml` binds setuptools metadata to that file. The
runtime remains standard-library-only on Python 3.11 and later; the conditional
`tomli` dependency supplies the same TOML interface only on supported Python
3.10. Setuptools 83 is the exact qualified build backend. No system or user
Python environment is modified.

The CLI owns six coherent families: checks, skills, tests, reports, responses,
and release maintenance. Existing public executable names remain thin in-process
compatibility adapters and retain their argument/exit owners. Consumer skill
listing and context reporting read one exact, source-digest-bound metadata
manifest through `importlib.resources`; full skill content and projection stay
repository-maintenance operations that require an exact Git worktree and fail
with a bounded diagnostic outside one.

Global configuration resolves `--apgr-home` over `APGR_HOME` over `~/.apgr`.
The only APG82 scalar setting is `outbox_root`, resolved in explicit CLI,
project `.apgr/config.toml`, global `<APGR_HOME>/config.toml`, then built-in
order. Project discovery stops at the containing Git worktree unless an exact
`--project-root` is supplied. Project `.apgr` stays declarative. The future
`agentic-praxis-grimoire-nd` checkout path is reserved beneath the resolved
APGR home and is not created.

New terminal reports live beneath
`~/Documents/agent/outbox/<project>/<phase>/`. Exactly one show, diff, or
ops-only primary is current. Associated operational evidence remains a framed
record inside a Git primary. Same-directory replacement, complete-record
validation, Git drift checks, private modes, and exact association checks are
preserved; interrupted primary-kind supersession remains recoverable through a
private transaction marker. Explicit `GIT_SHOW_REPORT_ROOT` retains historical
omnibus behavior without migrating historical artifacts.

Final responses use immutable `<phase>.<NNN>.response.md` names. An advisory
phase lock is process-death-safe, allocation is bounded to 001 through 999,
publication uses an atomic no-overwrite hard-link operation, and incomplete
reservations are listable and exactly cleanable. The body is stored byte-for-
byte and the caller receives the created path.

`apgr skills context-report` deterministically reports discoverable count,
exact UTF-8 description bytes and characters, largest-first rows, and malformed
metadata. The APG82 baseline is 33 skills, 7,967 bytes, 7,955 characters, and
zero malformed resources. No token heuristic, threshold, or selective
projection policy is introduced.

All package, CLI, configuration, report, response, resource, test, and scope
owners are current-development v0.5 release paths and explicit historical-v0.4
forbidden owners. Corrected v0.4 reconstruction therefore remains byte-
isolated. APG82 changes no profile, maturity, route, target, or known-debt
semantics.

After APG82, v0.5 contains only separately authorized APG83 bounded dogfood and
readiness followed by APG84 publication. The v0.6 scope record names exactly
Astro, JSX, MDX, React, Vitest, and GoMock plus explicit project-selected
context/projection infrastructure. This phase starts none of that work.
