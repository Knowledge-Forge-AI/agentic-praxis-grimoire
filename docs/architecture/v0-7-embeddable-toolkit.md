# APG v0.7 Embeddable Toolkit Architecture

## Status and authority

This is the normative APG94 architecture for v0.7.0. It is accepted through
[ADR 0051](../adr/2026/08/0051-v0-7-embeddable-toolkit-architecture-and-roadmap.md).
It freezes implementation boundaries for APG95 through APG103; it does not
authorize any successor phase.

APG v0.6.0 remains terminally published. APG94 changes no implementation,
package version, skill, maturity, projection, public release, JACA checkout,
`.flakes` checkout, or Nix composition.

## Product thesis and invariants

APG v0.7 makes APG an embeddable agent-engineering toolkit. The portable Go
libraries are the primary product surface. `apgr`, Python, npm, and Nix are
adapters or distributions over those libraries, not independent semantic
implementations.

The following invariants are binding:

1. JACA can import APG Go packages and call them in-process. JACA does not need
   to invoke `apgr` or a shell.
2. APG remains stateless and provider-neutral. It does not persist attempts,
   select providers or reviewers, advance roadmaps, authorize work, or become
   an orchestration engine.
3. APG never imports JACA. The module graph is acyclic.
4. Initial Git reporting is shell-free at the JACA boundary but may execute the
   native `git` executable with an exact argument vector and
   `exec.CommandContext`. Command strings and `sh -c`-style execution are
   forbidden.
5. Current report bytes and schemas are compatibility authority until an
   explicitly versioned successor schema is accepted.
6. Canonical skill Markdown remains under `skills/`; no second maintained skill
   tree is introduced.
7. Task-scoped context is real only when the target agent sees an isolated
   selected discovery root rather than the global 39-skill root.
8. Environment snapshots are curated configuration artifacts, not secret
   stores and not shell programs.
9. Hotspot metrics report unavailable capabilities honestly. They never invent
   semantic statement or complexity values.

## Ownership

| Owner | Owns in v0.7 | Does not own |
| --- | --- | --- |
| APG | Skill corpus and metadata; deterministic bundle resolution; report collection, models, rendering, and optional publication; portable environment capture and resolution; hotspot analysis; stable schemas; `apgr`; Python/npm/Nix distribution adapters | Attempts, retries, phase progression, provider calls, reviewer choice, authorization, orchestration state, deployment activation |
| JACA | Task and phase lifecycle; attempts and retry policy; provider and reviewer selection; authorization and escalation; concurrency and replay; durable orchestration evidence; deciding when to call APG | APG report, resolver, snapshot, or analyzer semantics |
| `.flakes`, nix-darwin, and composition owners | Host installation, activation, allowlist/profile selection, shell-hook wiring, Nix packaging, and deployment | Portable APG library semantics |
| Consumer repository | Project policy, selected bundle facts, environment profile contents, analyzer inclusion/exclusion policy, and acceptance thresholds | Reimplementation of APG schemas under the APG name |

Portable behavior migrates only after parity qualification. Until APG98 is
accepted, `.flakes`' current `codex-env` Python implementation remains the
operational environment-snapshot authority. After APG98 parity and an
independently authorized consumer cutover, APG owns portable snapshot semantics
while `.flakes` keeps its allowlists, hooks, installation, and activation.

## Go module and package layout

The repository gains one root module in APG95:

```text
module github.com/Knowledge-Forge-AI/agentic-praxis-grimoire

schema/             stable shared identities and canonical JSON helpers
report/             report collection, models, rendering, parsing, publication
skills/             canonical Markdown leaves plus embedded corpus and resolver
envsnap/            environment profile, capture, storage, and resolution
hotspot/            repository analysis models, analyzers, ranking, renderers
cmd/apgr/           CLI adapter over public packages
internal/gitexec/   exact-argv native Git process implementation
internal/atomicfile private path, lock, transaction, and atomic-write helpers
internal/cli/        CLI-only parsing and presentation
```

There is no generic `pkg/` directory and no nested `/go` module. Root domain
packages give JACA stable import paths under the shared `v0.7.0` repository tag;
a nested module would require subdirectory-prefixed tags and a second release
surface.

Go 1.25 is the v0.7 minimum because the inspected JACA consumer modules declare
Go 1.25. Production builds are `CGO_ENABLED=0`. The initial supported build
matrix is `darwin/arm64`, `linux/amd64`, and `linux/arm64`. Windows and
`darwin/amd64` fail as unsupported in v0.7 rather than receiving unqualified
binaries.

The existing `skills/` directory becomes the Go `skills` package. Its Go source
uses `embed.FS` with `*/SKILL.md` and `chatgpt/*/SKILL.md` (embedding all 39
canonical leaves across flat and `chatgpt/` namespaces), so canonical Markdown is
embedded directly without `..` patterns, generated copies, or a second source
tree. Package functions return immutable byte copies and content identities;
callers never receive a mutable global buffer.

`internal/` packages are not JACA API. Public packages may share `schema`, but
JACA must not import APG internal process, resource, or filesystem owners.

## Public API rules

All consequence-bearing operations accept `context.Context` first and return
promptly on cancellation. Cancellation is observable through an error matching
`context.Canceled` or `context.DeadlineExceeded`. Public sentinel errors classify
stable failure families through `errors.Is`; bounded typed details may support
`errors.As`. Error text is diagnostic, not an API, and must not contain report
payloads, environment values, patches, or private local paths.

Public request and result structs are value types. Collections returned to
callers are newly allocated. No package starts a background goroutine that can
outlive the call. No public API accepts a command string, shell fragment, or
JACA type.

### Initial reporting API

APG95 implements this shape in `report`:

```go
type Service struct { /* unexported state */ }

type Options struct {
    Repository string
    GitPath    string
}

func New(options Options) (*Service, error)
func (s *Service) Show(ctx context.Context, request ShowRequest) (Result, error)
func (s *Service) Diff(ctx context.Context, request DiffRequest) (Result, error)

func Operational(ctx context.Context, request OperationalRequest, existing []Record) (Result, error)
func ParseRecords(content []byte) ([]Record, error)
func Append(ctx context.Context, request AppendRequest) (Publication, error)
```

`Show` and `Diff` collect Git evidence, normalize it, render the canonical
record, and return it in memory. `Operational` accepts caller-supplied bytes and
already parsed canonical records; it has no filesystem precondition. `Append`
is the optional APG-owned publication layer. JACA may retain `Result.Record` or
`Result.Bytes` directly without calling `Append`.

`Options.Repository` must be an exact worktree root. Empty `GitPath` means the
fixed executable name `git`; a non-empty value must be an absolute regular-file
path chosen by the caller. APG appends its own fixed flags and exact arguments.
The Git child receives bounded stdin/stdout/stderr, `LC_ALL=C`, `LANG=C`,
`GIT_PAGER=cat`, `PAGER=cat`, `GIT_OPTIONAL_LOCKS=0`, and
the remaining current process environment. It never inherits `GIT_INDEX_FILE`
for diff collection. Changing replace-object or other Git environment semantics
requires explicit parity evidence; APG94 does not add such a control.

The request/result ownership is:

| Type | Required fields | Result |
| --- | --- | --- |
| `ShowRequest` | `Phase`, `Commit`, `StatusDoc`, `Result`, `FinalGate` | Resolved commit plus normalized metadata/evidence and canonical bytes |
| `DiffRequest` | `Phase`, `Result`, `FinalGate`, optional `StatusDoc` | Observed HEAD/index/worktree identity plus canonical bytes |
| `OperationalRequest` | `Phase`, `Project`, `Result`, `FinalGate`, `SourceName`, `Source`, optional related commit and exact Git report ID | Validated operational record and canonical bytes |
| `AppendRequest` | Absolute outbox root, project, phase, one canonical `Record` | Final primary path, stale-primary disposition, and record identity |
| `Result` | `Record`, `Bytes`, and type-specific normalized evidence | In-memory consumption; no implied write |

The request field named `Result` preserves the current report vocabulary. It is
not a Go method result.

### Frozen report compatibility

The common envelope remains version 1. Header and trailer field order remains:
envelope identity, version, record type, record format version, record ID,
project, phase, payload SHA-256, and payload byte size. The trailer repeats the
common identity and ends with `RECORD-COMPLETE: true`.

| Record | Version and ID | Ordered sections | Identity and integrity contract |
| --- | --- | --- | --- |
| Git show | format 2; `GIT-SHOW-REPORT-<resolved-commit>` | Reading guide; report identity; commit summary; changed files; numstat; commit message; patch; integrity summary | Preserves phase, commit input/resolution, status doc, result, final gate, repository, root/merge/parent facts, author/committer metadata, subject, file counts, patch mode, and SHA-256 for changed files, numstat, message, and patch |
| Git diff | format 1; `GIT-DIFF-REPORT-<sha256-of-ordered-state-identity>` | Reading guide; report identity; worktree summary; porcelain-v2 status; staged summary; unstaged summary; changed files; numstat; patch; integrity summary | Preserves HEAD, real index fingerprint/identity, index mode, status doc, result, final gate, repository, counts, all evidence hashes, two-pass drift matches, no-real-mutation assertion, and patch completion |
| Operational | format 1; `OPERATIONAL-REPORT-<sha256-of-exact-source>` | Reading guide; operational identity; operational summary; related records; exact framed body; integrity summary | Preserves phase/project/result/final gate, source basename/hash/size, body schema and declared identity, related commit/report ID, source and framed-body sizes/hashes, and body completion |

Within those sections the ordered field sequences are frozen exactly:

- show identity: `REPORT-FORMAT`, `FORMAT-VERSION`, `REPORT-ID`, `PHASE`,
  `COMMIT-INPUT`, `COMMIT`, `STATUS-DOC`, `RESULT`, `FINAL-GATE`,
  `REPOSITORY`, `RELATED-OPERATIONAL-REPORT`, `ROOT-COMMIT`, `MERGE-COMMIT`,
  `PARENT-COUNT`, `PARENTS`, `AUTHOR-NAME`, `AUTHOR-EMAIL`, `AUTHOR-DATE`,
  `COMMITTER-NAME`, `COMMITTER-EMAIL`, `COMMITTER-DATE`, `SUBJECT`; summary:
  `FILES-CHANGED`, `FILES-ADDED`, `FILES-MODIFIED`, `FILES-DELETED`,
  `FILES-RENAMED`, `FILES-COPIED`, `INSERTIONS`, `DELETIONS`, `BINARY-FILES`,
  `PATCH-MODE`; integrity: `REPORT-ID`, `REPOSITORY`, `PHASE`, `COMMIT`,
  `CHANGED-FILES-SHA256`, `NUMSTAT-SHA256`, `COMMIT-MESSAGE-SHA256`,
  `PATCH-SHA256`, `END-OF-PATCH-REACHED`;
- diff identity: `REPORT-FORMAT`, `FORMAT-VERSION`, `REPORT-ID`, `PHASE`,
  `HEAD`, `REAL-INDEX-FINGERPRINT`, `REAL-INDEX-IDENTITY`, `INDEX-MODE`,
  `STATUS-DOC`, `RESULT`, `FINAL-GATE`, `REPOSITORY`,
  `RELATED-OPERATIONAL-REPORT`; summary uses the same ten fields as show;
  integrity: `REPORT-ID`, `REPOSITORY`, `PHASE`, `HEAD`,
  `REAL-INDEX-FINGERPRINT`, `REAL-INDEX-IDENTITY`,
  `PORCELAIN-V2-STATUS-SHA256`, `STAGED-SUMMARY-SHA256`,
  `UNSTAGED-SUMMARY-SHA256`, `CHANGED-FILES-SHA256`, `NUMSTAT-SHA256`,
  `PATCH-SHA256`, `PRE-POST-HEAD-MATCH`, `PRE-POST-INDEX-MATCH`,
  `PRE-POST-STATUS-MATCH`, `PRE-POST-STAGED-MATCH`,
  `PRE-POST-UNSTAGED-MATCH`, `PRE-POST-WORKTREE-MATCH`,
  `REAL-INDEX-AND-WORKTREE-MUTATED`, and `END-OF-PATCH-REACHED`; and
- operational identity: `REPORT-FORMAT`, `FORMAT-VERSION`, `RECORD-ID`,
  `PHASE`, `RESULT`, `FINAL-GATE`, `PROJECT`, `SOURCE-FILE-BASENAME`,
  `SOURCE-PAYLOAD-SHA256`, `SOURCE-PAYLOAD-SIZE-BYTES`, `RELATED-COMMIT`,
  `RELATED-GIT-REPORT-ID`; summary: `PROJECT`, `PHASE`, `RESULT`,
  `FINAL-GATE`, `RELATED-COMMIT-COUNT`, `SOURCE-LINES`, `SOURCE-BYTES`,
  `BODY-SCHEMA-DETECTED`, `SOURCE-DECLARED-PHASE`,
  `SOURCE-DECLARED-OUTCOME`, `SOURCE-PRIMARY-COMMIT`, and, for a diff
  relation, `SOURCE-PRIMARY-GIT-REPORT-ID`; relations: `RELATED-COMMIT`,
  `RELATED-GIT-REPORT-ID`; integrity: `RECORD-ID`, `PROJECT`, `PHASE`,
  `SOURCE-PAYLOAD-SHA256`, `SOURCE-PAYLOAD-SIZE-BYTES`,
  `FRAMED-BODY-SHA256`, `FRAMED-BODY-SIZE-BYTES`, and
  `END-OF-OPERATIONAL-BODY-REACHED`.

Field spelling, ordering, newline rules, section delimiters, NUL framing, header
escaping, hash inputs, summary counting, and parser strictness remain byte-for-
byte compatible with the Python authority. Report construction adds no current
time, random value, or host path to record bytes.

The diff ID hash starts with the domain bytes
`agent-report-git-diff-state-v1\0` and then, in order, hashes each ASCII key,
NUL, ASCII value, NUL for `head`, `index`, `status`, `staged`, `unstaged`,
`changed`, `numstat`, and `patch`. `index` is SHA-256 of the real-index
fingerprint string; the remaining evidence values use their current exact byte
hashes. Show and operational IDs remain the resolved commit and exact source
payload SHA-256 respectively.

Show accepts a 7-to-64-character hexadecimal commit input, resolves it to one
commit, and preserves real Git root/merge semantics. Diff rejects an inherited
`GIT_INDEX_FILE`, unsupported index layout, unmerged state, concurrent HEAD,
index, status, staged, unstaged, or worktree drift, and an empty snapshot. It
uses an invocation-owned temporary index for intent-to-add coverage and never
mutates the real index or worktree.

Operational source must be non-empty, bounded by the current source limit, a
safe direct regular file at the CLI boundary, and valid `operational-report-v1`
or accepted legacy input. A canonical report containing Git records requires
the exact related Git report ID. A related commit is valid only for the matching
Git-show record.

Publication preserves the current owner-only directory, no-follow path, lock,
stale-lock recovery, transaction marker, atomic replacement, directory fsync,
and interrupted-recovery rules. Directories are mode 0700 and files are mode
0600. A new show primary supersedes the current diff primary and conversely;
an operational-only phase uses its canonical ops file, while an operational
record created after a show/diff primary exists is appended inside that Git
primary. A later Git show/diff primary supersedes and removes the stale
ops-only primary without copying its operational record into the new Git
primary. Changing that supersession-retention rule requires an explicit
compatibility, schema, and evidence decision. Legacy omnibus mode remains
explicit. The CLI keeps
success output on stdout, bounded diagnostics on stderr, and exit classes 0
success, 2 usage, 1 runtime, and 130 keyboard interruption.

APG95 must falsify compatibility with a differential golden corpus that runs
the current Python and Go paths over root commits, ordinary commits, merges,
binary/rename/copy diffs, staged/unstaged/untracked/intent-to-add states,
operational associations, invalid input, drift, interrupted transaction, and
recovery cases. Python remains authoritative until every accepted byte and
error-class comparison passes.

## CLI strangler migration

The Go `cmd/apgr` CLI is always an adapter over public packages. The Python
distribution may dispatch during migration, but no migrated command retains an
independent Python implementation.

| Family/action | v0.7 disposition | Phase |
| --- | --- | --- |
| `report show`, `diff`, `operational`/`ops` and compatibility names | Migrate to `report`; Python delegates and parity remains enforced | APG95-APG96 |
| `report path`, `recover` | Migrate with Go CLI/publication foundation | APG96 |
| `skills list`, `context-report` | Migrate to embedded `skills` corpus | APG97 |
| `skills project` install/adopt/check/uninstall | Replace portable selection/materialization with Go; keep legacy repository projection adapter only for compatibility | APG97 then APG100 |
| `skills user`, `install-global`, `flatten` | Remain Python host/repository maintenance in v0.7; not portable semantic authority | Through v0.7 |
| `check skill-library` | Go validates embedded/canonical identity; Python repository check delegates or compares | APG97/APG100 |
| `check change-size`, `phase-commit-message`, `record-identity` | Remain repository-maintenance Python in v0.7 | Through v0.7 |
| `test` | Remains the repository-owned Python test orchestrator | Through v0.7 |
| `response` record/capture | Migrate atomic portable behavior to Go | APG100 |
| `release public` | Remains Python operator/repository maintenance; it invokes and verifies Go artifacts rather than reimplementing them | Through v0.7 |
| Python bundle/sdist normalization compatibility wrappers | Remain release-build helpers; revised for platform wheels | APG100 |

Repository-maintenance Python is intentionally temporary where a portable Go
owner is planned and explicitly retained where the action is APG repository
governance rather than toolkit semantics. APG103 cannot ship two independent
implementations of any migrated action.

## Distribution and version contract

`src/agentic_praxis_grimoire/VERSION` remains the single editable version
authority and stays `0.6.0` in APG94. Release tooling requires it to equal the
repository tag. Go release builds inject that value into
`internal/buildinfo.Version` with `-ldflags`; the source default is `devel`, not
a second release constant. The binary reports version, module build
information, target, corpus fingerprint, and schema versions. Release checks
fail if any embedded value disagrees.

Go consumers use the repository tag `v0.7.0` and module proxies; there is no
separate Go upload registry. GitHub release assets, Go proxy readback, PyPI,
npm, and the Nix handoff all bind the same version and binary hashes.

### Python

The selected architecture is platform-specific Python wheels containing the Go
binary, the thin Python launcher, configuration helpers needed for compatibility,
and a manifest binding binary SHA-256, target, APG version, and corpus
fingerprint. The existing package name, `apgr` console script, and
`python -m agentic_praxis_grimoire` remain. Both launch the bundled binary with
an exact argument vector for migrated commands; retained repository-maintenance
commands route to their Python owner.

Wheels are produced for the frozen three-target matrix. `pip install` from a
wheel is standalone and performs no runtime download. The sdist contains the Go
source, canonical skill corpus, Python wrapper, and build metadata; building it
requires a compatible Go 1.25 toolchain and fails closed when the target is
unsupported or the built binary identity disagrees. The v0.6 universal
`py3-none-any` wheel ends at v0.6; v0.7 must not falsely claim universality.

Rejected Python alternatives are: requiring an independently installed binary
(not standalone), first-run binary download (mutable executable and offline
failure), and shared-library/FFI (cgo/C-ABI and lifecycle complexity without a
v0.7 need).

### npm

The canonical launcher package is `@knowledge-forge-ai/apgr`. The platform
packages are:

- `@knowledge-forge-ai/apgr-darwin-arm64`;
- `@knowledge-forge-ai/apgr-linux-x64`; and
- `@knowledge-forge-ai/apgr-linux-arm64`.

The launcher declares same-version platform packages as optional dependencies,
selects exactly one from `process.platform` and `process.arch`, verifies its
manifest and binary SHA-256, and spawns it with exact argv and inherited stdio.
It contains no APG semantics and performs no download. Missing, mismatched, or
unsupported packages fail with a bounded installation diagnostic. Unscoped
`apgr` is rejected because namespace availability is not an architecture
authority and a scoped package binds ownership explicitly.

### Coordinated release readback

APG103 requires: annotated Git tag and GitHub assets; Go proxy resolution of the
root module at the tag; isolated Go import; isolated supported Python-wheel
installs plus sdist build; isolated npm installs for each supported target;
binary/version/corpus/checksum agreement across all artifacts; and a Nix adapter
handoff that binds the same hashes. Credentials and account configuration
remain external operator concerns.

## Deterministic skill and context resolver

The `skills` package accepts only structured facts. It never reads a prose
prompt, infers authorization, selects a model, or mutates a global discovery
root.

Its public call surface is:

```go
func Corpus() fs.FS
func Resolve(ctx context.Context, request BundleRequest) (BundleResult, error)
func Materialize(ctx context.Context, request MaterializeRequest) (Materialization, error)
```

`Corpus` exposes a read-only sub-filesystem rooted at canonical skill resources;
mutable byte slices returned by reads are caller-owned copies. `Materialize`
accepts a previously resolved result and exact destination parent rather than
rerunning selection implicitly.

### Request schema

`apg.skill-bundle-request/v1` contains:

- `work_class`: one versioned APG work-class identifier;
- `explicit_skill_ids`: an ordered-irrelevant set of canonical skill IDs;
- `languages`, `runtimes`, and `test_frameworks`: closed versioned identifiers;
- `repository_characteristics` and `capabilities`: closed versioned facts;
- `consumer`: consumer kind, supported materialization form, OS/architecture,
  and provider constraints that affect packaging only;
- `budget`: maximum discovery-description bytes, materialized-body bytes, and
  initial-context bytes, plus caller-supplied fixed prompt overhead;
- `eager_bodies`: whether full selected bodies enter the initial prompt; and
- `schema_version`.

Unknown fields, identifiers, duplicate IDs, contradictory facts, negative
budgets, and unavailable explicit skills fail closed. Input set order has no
effect.

### Selection and result

Selection uses a versioned APG-owned rule table. Explicit IDs are included
first; exact structured facts may add their one mapped owner. Results sort by
canonical skill ID. Composition edges are reported among selected skills but
do not select a sibling by implication. No language, runtime, test, or adjacent
profile chain is globally mandatory.

`apg.skill-bundle-result/v1` contains the request identity, rule-table version,
selected IDs, mapping from canonical skill ID to relative canonical source/embedded
content path (for example `chatgpt/chatgpt-manager-workflow/SKILL.md` or
`<skill-id>/SKILL.md`) and SHA-256 identity, inclusion reason and source fact
for each item, exclusions and conflicts, composition edges, canonical-corpus
description bytes, selected description bytes, selected body bytes,
initial-context bytes, every budget limit/result, and a bundle fingerprint.

The fingerprint is SHA-256 over a canonical UTF-8 JSON identity view with
lexicographically ordered object keys, deterministic arrays, LF newlines, no
insignificant whitespace, schema/rule versions, selected IDs, content hashes,
reasons, and composition edges. It excludes timestamps, local paths, and
diagnostic prose.

Budget enforcement never truncates a description, drops a selected skill, or
substitutes a smaller skill. Initial-context bytes equal caller overhead plus
selected discovery descriptions and, only when `eager_bodies` is true, selected
body bytes. Provider-token conversion is consumer-owned because it depends on
the exact tokenizer; APG's reproducible authority is UTF-8 bytes.

### Agent-scoped materialization

Materialization creates a new owner-only staging directory, writes one
`<skill-id>/SKILL.md` direct regular file per selected skill (flattening the
view to standard `<target-root>/<skill-id>/SKILL.md` direct regular files for
uniform agent discovery, regardless of canonical source namespace) plus a
canonical manifest, fsyncs it, and atomically renames the completed view.
Directories are 0700 and files 0600. Bytes come from the embedded canonical
corpus and are verified against the bundle result. No symlink points into an
APG checkout.

JACA gives the target agent only this root as its APG discovery root. If the
client also injects the global APG root, context conservation has failed and
qualification must reject the run. Cleanup ownership remains with JACA's task
lifecycle; APG returns the exact created root and manifest identity.

The v0.6 9,527-byte global ceiling remains a canonical-corpus integrity gate,
not the v0.7 per-task budget. APG94 preserves 39 skills, 9,504 description bytes,
and 9,492 characters. v0.7 reports total corpus, selected discovery, selected
body, and initial prompt footprints separately and does not raise the global
ceiling.

## Portable environment snapshots

### Profile and snapshot schema

An `envsnap.Profile` is an explicit, named, versioned allowlist. Each row has an
exact variable name, validator ID, maximum UTF-8 bytes, required flag, optional
validated default metadata, and description. Defaults are descriptive/profile
validation data in v1 and are never inserted implicitly during capture or
resolution. Ambient wildcard capture is invalid. V1 validators preserve the
current typed families: boolean, command, host, integer, path, path list, port,
raw-safe scalar, token, token list, URI, and URI-or-path.

The public call surface is:

```go
func ValidateProfile(profile Profile) error
func Capture(ctx context.Context, request CaptureRequest) (Snapshot, error)
func Store(ctx context.Context, request StoreRequest) (StoredSnapshot, error)
func Load(ctx context.Context, request LoadRequest) (Snapshot, error)
func Resolve(ctx context.Context, request ResolveRequest) (ResolvedEnvironment, error)
```

Capture and resolution accept explicit maps. Store/Load own canonical JSON and
path safety; none of these functions launches a process or mutates `os.Environ`.

`apg.environment-snapshot/v1` is canonical JSON containing schema version,
profile ID and hash, producer version, capture provenance, capture timestamp,
ordered entries with name/validator/value/source, missing optional names, and a
content fingerprint. The fingerprint covers the profile identity and exact
ordered resolved entries but excludes timestamp and storage path. If that
identity is unchanged, capture does not rewrite the file or advance its
timestamp.

The CLI's canonical current-snapshot path is
`<APGR_HOME>/environment/<profile-id>/current.json`, where APGR home keeps the
existing precedence `--apgr-home`, `APGR_HOME`, then `~/.apgr`. A library caller
supplies an exact storage root and receives the resolved path. Each profile
directory has one owner-identity lock directory during replacement; an unsafe
or live lock fails closed, while a verifiably stale APG-owned lock may be
recovered. This interprocess lock is a new portable APG safety capability beyond
the inherited `.flakes` baseline (which had no interprocess lock) and carries its
own test obligation in APG98. No historical-value archive is created implicitly.

The canonical store is JSON, never shell syntax. A separate CLI adapter may
render a parser-safe shell export view for a hook, but neither APG nor JACA
sources it. JACA loads and resolves the JSON in-process.

### Security and resolution

Environment snapshots are not a secrets vault. V1 allowlists reject names
identified as credential, token, password, private-key, cookie, session, or
secret material. Such values must enter through a separately authorized
provider secret channel, never an environment snapshot. Diagnostics list only
variable names, validators, and error classes; values and value-derived
fragments never enter logs or errors.

Capture reads one caller-supplied environment map, validates every included
value, and writes through an owner-only 0700 directory and 0600 atomic file.
Symlinks, non-regular files, owner mismatch, unsafe permissions, duplicate
names, unknown validators, control characters, and oversized values fail
closed. The result exposes capture age and staleness without declaring stale
data invalid unless the caller supplied a maximum age.

Resolution has two explicit modes:

1. `Isolated` (default) returns only snapshot entries plus validated explicit
   overrides.
2. `Overlay` starts with the caller's base map, applies snapshot entries, then
   explicit overrides. Snapshot and override names must be in the profile; the
   base map is consumer-owned and is not persisted.

Thus explicit override beats snapshot, snapshot beats base, and no implicit
default is inserted. All layers use the same validator and sensitive-name
policy. Resolution returns a new map and a provenance record; it never mutates
the process environment or launches a command.

APG98 must parity-test the current `.flakes` allowlist validation, missing-value
behavior, shell detection adapters, no-churn writes, atomicity, 0700/0600 modes,
metadata hash, prompt-hook frequency, parser-safe run behavior, and error
classes before any host consumer cutover.

## Structural-hotspot analyzer

The analyzer is an in-process `hotspot` library with CLI adapter
`apgr analyze hotspots`. It walks an exact repository root without following
symlinks, executing source, invoking a shell, loading plugins from the target,
or reading outside the root. Context cancellation, maximum files, maximum bytes
per file, total bytes, and elapsed-time limits are mandatory inputs with safe
defaults.

Every complete report answers, to the depth its declared capabilities permit:
which files are largest, how languages contribute to the repository, which
functions or methods are difficult, where large top-level procedural regions
exist, and which candidates rank highest for refactoring attention. It emits a
concise terminal view, a detailed human Markdown view, and stable machine JSON.

The public call surface is:

```go
func Analyze(ctx context.Context, request Request) (Report, error)
func MarshalJSON(report Report) ([]byte, error)
func RenderTerminal(report Report) ([]byte, error)
func RenderMarkdown(report Report) ([]byte, error)
```

All renderers consume the same immutable model. `MarshalJSON` emits the
canonical machine schema; the two human renderers cannot add metric facts.

### Capability matrix

`E` means exact for the stated grammar, `S` means bounded structural scan, `U`
means unavailable, and `N/A` means not meaningful. Confidence describes the
strongest emitted metric, not file classification.

| Surface | Classification | Line/prose | Statements | Symbols | Cyclomatic | Nesting | Procedural regions | Structural metrics | Confidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Go | E | E | E via `go/parser` | E | E | E | E for package/init regions | E | high |
| Markdown | E | E physical/prose/fence | N/A | S headings/fences | N/A | S section depth | N/A | E link/fence/section counts | high |
| MDX, Astro | E | E separated prose and embedded regions | U for embedded code | S region owners | U | S region depth | S top-level embedded regions | S | medium |
| Python | E | E physical | U | U | U | U | U | S lexical density only | low |
| Java, Kotlin | E | E physical | U | U | U | U | U | S lexical density only | low |
| JavaScript, TypeScript, JSX, TSX | E | E physical | U | U | U | U | U | S lexical density only | low |
| HTML | E | E physical/prose | N/A | S element IDs/headings | N/A | S tag depth when balanced | N/A | S element/attribute counts | medium |
| XML, XML plist | E | E physical | N/A | S element paths | N/A | E parsed depth | N/A | E node/attribute counts | high |
| binary plist | E | E bytes only | N/A | U | N/A | U | N/A | U | low |
| CSS | E | E physical | U | S rule/at-rule labels | N/A | S block depth | S top-level rule regions | S selector/declaration counts | medium |
| JSON family | E | E physical | N/A | S object paths | N/A | E parsed depth | N/A | E node/key/array counts | high |
| YAML, TOML | E | E physical | N/A | U | N/A | U | N/A | S indentation/key counts | low |
| Terraform, Gradle | E | E physical | U | U | U | U | S top-level blocks | S block/key counts | low |
| SQL | E | E physical | U | U | U | U | S top-level statement regions | S keyword/clause counts | low |
| Bash, Zsh, POSIX shell, extensionless shebang scripts | E | E physical | U | U | U | U | S top-level regions | S command/control-token counts | low |
| Dockerfile | E | E physical | S logical instructions | S stages | N/A | N/A | E top-level instruction regions | E instruction/stage counts | high |
| Vagrantfile | E | E physical | U | U | U | U | S top-level regions | S block/call counts | low |

The v0.7 matrix deliberately makes semantic metrics unavailable for languages
without a qualified parser. APG99 may add an in-process parser dependency only
through the repository dependency policy: explicit problem, alternatives,
license and supply-chain review, compatibility and packaging impact, rollback,
and parser-corpus tests. A dependency may deepen a row but may not fabricate
parity across unrelated grammars. Runtime parser downloads and target-provided
plugins are forbidden.

Go is added because APG and JACA are direct v0.7 consumers even though it was
omitted from the supplied initial list. Every supplied surface remains
classified; no unsupported semantic value is approximated.

### Report and ranking

`apg.hotspot-report/v1` contains tool/schema version, root identity supplied by
the caller without an absolute private path, scan configuration, exclusions,
per-language aggregates, capability declarations, file rows, owner rows,
procedural-region rows, unavailable metrics with reasons, confidence, warnings,
and deterministic ranking.

JSON is the machine authority. A concise terminal table and detailed Markdown
are deterministic renderings of the model; machines never parse Markdown.
Rows sort by UTF-8 path bytes. Hashes use SHA-256 over canonical JSON identity
views that exclude elapsed time and local paths.

Ranking is relative within one report. For each available metric, the analyzer
computes an integer 0-10,000 percentile within the same capability class and
path tie order. The risk score is the weighted mean of available percentiles:
35 complexity, 25 statements, 15 nesting, 15 top-level procedural size, and 10
file size. Missing metrics contribute neither value nor weight. The total order
is score descending, available weight descending, confidence high-to-low, then
path ascending. Reports expose the raw vector and available weight, so a
high-ranked low-confidence file cannot masquerade as a deep semantic finding.

The supplied question "which files are growing fastest" requires history, while
the supplied feature sequencing calls recent growth a future enhancement.
APG94 resolves the tension by deferring churn and growth beyond v0.7. The v1
report declares that capability `deferred`; it does not inspect Git history.

A future refactoring skill may consume the stable JSON and cite file/owner IDs,
metrics, confidence, and unavailable reasons. Model prose never changes a metric,
rank, or fingerprint.

## README and documentation information architecture

APG101 rewrites the root README as a human landing page with this order:

1. what APG is;
2. objectives and value;
3. concrete use cases;
4. quick start;
5. install and consumption choices;
6. core concepts;
7. JACA and library integration;
8. detailed-document navigation;
9. current project status; and
10. contribution and license links.

The root README stops being the phase ledger. Existing material is preserved
under `docs/history/releases-and-phases.md` or the existing roadmap/evaluation
owners, with redirects from the new navigation. Git history is not treated as
the only preservation mechanism.

| Subject | Detailed owner frozen for APG101 |
| --- | --- |
| Product and module architecture | `docs/architecture/v0-7-embeddable-toolkit.md` |
| APG-JACA boundary | `docs/architecture/apg-jaca-integration.md` |
| CLI reference | `docs/reference/cli.md` |
| Go library reference | `docs/reference/go-library.md` |
| Skills and context bundles | `docs/guides/skill-context-bundles.md` |
| Environment snapshots | `docs/guides/environment-snapshots.md` |
| Hotspot analysis | `docs/guides/hotspot-analysis.md` |
| Package/distribution | `docs/distribution.md` |
| Release | `docs/public-release-process.md` |
| Governance and phase history | `docs/project-model.md`, `docs/roadmap.md`, `docs/status/`, `docs/history/releases-and-phases.md` |

APG94 does not create those future reference documents or rewrite the README.

## Quality debt

`CSS-QD-001` through `CSS-QD-005` and `JS-QD-001` through `JS-QD-005` remain
unchanged. A v0.7 phase refreshes only debt whose owned qualification machinery
it materially changes and only under existing human-debt authority. No debt is
closed, reclassified, or promoted by this architecture, and no maturity changes
occur.

## Non-goals and rollback

APG94 adds no `go.mod`, Go source, dependency, skill, route, projection, schema
implementation, environment snapshot, analyzer, distribution artifact, version
bump, publication, deployment, JACA change, `.flakes` change, Nix change, or
README rewrite.

Before APG95 implementation, rollback is deletion of the APG94 architecture,
ADR, roadmap, integration, evaluation, and exit records plus index reversions.
After a successor implements a public contract, rollback follows that phase's
compatibility and artifact rules; it may not silently restore an independent
Python implementation or mutate an existing v0.7 schema.

## Acceptance and falsification

The architecture is falsified if JACA needs a CLI or shell to call APG; APG
imports JACA; a migrated command has two semantic owners; report golden bytes or
error classes diverge without versioning; task-scoped agents still receive the
global discovery root; snapshot values can leak into diagnostics or include
secret material; unsupported hotspot metrics receive numeric values; a
distribution carries a mismatched version/corpus/binary identity; or APG95
cannot implement the public package paths without changing this decision.

APG95 requires separate human authorization.
