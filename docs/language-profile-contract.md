# Language Profile Contract

## Purpose

This document is the normative contract for APG language profiles. A profile
supplies language-specific judgment after its trigger is satisfied. It does not
replace repository policy, an applicable APG process skill, or task authority.

## Warning levels

Every profile uses the complete textual label:

| Level | Meaning | Required response |
| --- | --- | --- |
| `Green — routine` | The decision is an idiomatic, low-risk default inside authority already supplied by the task and repository | Proceed proportionally and run project-owned checks |
| `Yellow — caution` | The decision depends materially on version, compatibility, performance, maintainability, or local convention | Inspect local policy and relevant evidence before choosing |
| `Orange — warning` | The decision crosses a consequential design, migration, concurrency, operational, compatibility, or rollback boundary | Continue only after an explicit local decision, bounded scope, rationale, rollback, and focused validation |
| `Red — crisis / stop` | The action or proposed growth is unsafe, exceeds a crisis boundary, or requires authority the profile does not possess | Stop; identify the safer design, accepted bounded exception, or governing authority required to continue |

Color styling is optional and never substitutes for the textual label, meaning,
or response. A level classifies one coherent current decision or proposed
change, not an author, artifact owner, repository, skill maturity, or repository
quality score. When several materially applicable signals govern that decision,
the highest justified level controls its response.

No level grants implementation, migration, destructive-action, publication,
exception, or successor-phase authority. Green means routine only within
authority that already exists. Orange permits bounded continuation only when
the required local decision is within that authority. Red stops the unsafe
action or proposed growth until its stated condition is resolved.

## Profile requirements

A language profile must contain:

1. a precise positive trigger and material non-triggers;
2. supported language, dialect, engine, framework, or version boundaries;
3. project-owned inputs, including compatibility, formatting, tests,
   packaging, migration, deployment, generated code, and runtime constraints;
4. a compact Green/Yellow/Orange/Red decision model;
5. a procedure for applying warnings to the current task;
6. explicit authority, safety, privacy, and destructive-action stops;
7. evidence expectations proportional to the highest applicable level;
8. source identity, version, license or reuse boundary, and derivation mode;
9. refresh, correction, maturity, deprecation, removal, and rollback boundaries;
   and
10. representative positive, non-trigger, project-override, false-escalation,
    legacy, and classified-artifact evidence.

Profiles do not choose project architecture, dependencies, formatters, type
checkers, test frameworks, coverage targets, package managers, migrations,
database access, live commands, deployment, or release policy. They consume
those choices when present and identify when a material choice is missing.

## Project precedence and exceptions

Stricter applicable repository policy controls. A repository may relax only a
profile default, not a superior safety, privacy, compatibility,
destructive-action, or task-authority rule. Relaxation requires an explicit
rationale accepted through the repository's governing decision process,
bounded scope, supporting evidence, focused validation, and rollback. When
authority or acceptance is unclear, retain the stricter response.

One structural metric does not mechanically choose an architecture. Profiles
must inspect current and projected signals together, explain combined-signal
judgment, and distinguish measurement from decision authority.

## Artifact classification and proportionality

Structural defaults apply primarily to proposed growth in maintained
hand-written code. Before applying them, classify generated, vendored,
protocol, migration, snapshot, machine-produced, test, and legacy artifacts.
Follow the artifact owner, generator, repository policy, and accepted exception;
do not demand hand refactoring or direct generated-output edits merely because a
threshold is exceeded. Classification never suppresses a semantic Red stop.

An existing Red legacy artifact may receive the smallest safe fix when current
authority permits it, the change adds no independent responsibility, and it
avoids meaningful structural growth. Record the preserved decomposition or
follow-up boundary. A major feature or new independent responsibility remains
Red unless decomposition or an accepted architecture exception resolves it.

A large coherent data-driven test may receive a lower response than its
line-count-only signal only when the repository accepts that treatment, no
other Red signal applies, the behavior and fixture boundary remains cohesive,
and new growth has a bounded rationale. A test filename alone is not an
exception or permission for unbounded growth.

## Process and domain pairing

The smallest sufficient APG process skill remains primary for planning,
design, implementation, debugging, or review procedure. A separately
applicable language profile contributes domain judgment. The workflow router
may select both when a task crosses both boundaries; neither skill silently
invokes the other or expands the assignment.

## Evidence and maintenance

Green normally needs project-owned validation. Yellow adds local policy,
supported-version, and focused tradeoff evidence. Orange adds an accepted local
decision, adverse or compatibility evidence where relevant, and concrete
rollback. Red records the stopped action, source-to-sink or authority defect,
safer alternative, and exact disposition required before reconsideration.

A profile refresh must recheck version-sensitive sources and tool defaults,
real-code false escalation, project overrides, privacy, routing, and the frozen
scenario contract. Behavior-bearing correction follows the skill authoring and
maintenance guide. Maturity changes require separate evidence.

If a provisional profile is removed, remove its canonical leaf, checked
projection, catalog and capability-map entries, and focused compatibility tests
while preserving its ADR, evaluation, and exit history. If this shared contract
becomes unsound, supersede it through a later accepted decision and disposition
dependent profiles rather than rewriting accepted history. Source guidance is
restored only when a later separately authorized migration actually changed
it; APG18 performs no such migration.

## Current implementation boundary

APG18 implements one Python profile. APG19 implements separate Bash, Bats, and
Zsh profiles and historically defers ZUnit on then-current source/runtime
evidence. APG19A corrects the Bats test-count fallback to include runner-supported comment
function declarations without changing its bands or ownership. APG20 evaluates
Go and Ruby candidates and truthfully defers both after each reaches that
phase's correction limit with additional material defects. APG20A incorporates
the complete defect ledger into corrected candidates and retains both as
provisional profiles. Each retained profile owns its
calibrated numeric defaults; this shared contract does not generalize one
profile's values to another. APG21 applies this same warning contract while
evaluating a Nix language profile and separate PostgreSQL and SQLite engine
profiles under ADR 0016. PostgreSQL and SQLite are retained; Nix is deferred
after a second material candidate defect. Database profiles remain engine-
specific domain owners rather than a generic language or SQL owner. ZUnit
remains unimplemented.

APG21A subsequently separates Nix structural merge-family breadth from semantic
merge risk, retains the corrected Nix profile provisionally, and applies one
bounded PostgreSQL false-escalation correction. The shared warning contract,
engine-specific ownership, and the historical ZUnit deferral remain unchanged.

APG22 applies all nine retained profiles to a frozen cross-repository matrix.
Nine of nine profile cases match: three Green, one Yellow, one Orange, and four
Red, with one stricter project override, four classified artifacts (three of
which avoided false escalation), and four semantic-over-structural decisions.
No false escalation, false non-trigger, or profile correction is found. This
evidence changes no profile maturity or distribution boundary. APG22B later
uses explicit maintainer authority and direct disposable evidence to retain one
provisional ZUnit profile for exactly v0.8.2 with Zsh 5.9.2. Zsh 5.3.1 and every
unverified pair remain outside its support matrix. The profile conforms to this
warning contract without changing the six-skill distribution boundary.

APG23 completed fresh-session application discovery and explicit-use smoke for
the v0.3 catalog. APG24 publishes the accepted profiles and performs
public-candidate and active-integration shell validation without changing this
contract. Source-qualified dual-router application smoke after publication
remains an external observation.

APG22C subsequently corrects the ZUnit harness's selected user-startup path and
requires matched positive, negative, and in-runner controls. The exact ZUnit
v0.8.2 and Zsh 5.9.2 support boundary remains retained; Zsh 5.3.1 remains
unsupported because its independent runner dependency probe times out. The
correction changes no language-profile contract, skill wording, maturity,
catalog shape, distribution boundary, or application-smoke disposition.
