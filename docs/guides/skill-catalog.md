# Unified skill catalog (experimental)

APG163 adds an explicit catalog operation. Ordinary `skills list`, context-report,
V1 Resolve, materialize and corpus verification retain canonical-only semantics.
No provider startup, static dispatcher, worker, broker, SQLite or network service
requires this catalog. New interfaces are provisional; no JACA adoption is claimed.

## List local sources

The canonical Python CLI accepts:

```sh
apgr skills list --all-sources --format json \
  --project-root /selected/project --apgr-home /selected/home
```

Global project/home options before `skills` also work. Without an explicit project,
`--start` (default cwd) discovers the nearest Git worktree marker. An explicit
config-free project is authoritative. Home precedence is CLI, `APGR_HOME`, then
`~/.apgr`. Listing does not mutate source/home roots and executes no skill or support file.
Selected root symlinks are resolved once and both selected and resolved roots are
reported. Only immediate leaves under `.apgr/skills` and home `skills` are read;
`.agents/skills`, siblings, ancestors beyond worktree discovery and recursive
vendor trees are not sources. Canonical nested ChatGPT leaves remain restricted
to the ChatGPT consumer, including when explicitly replaced.

The namespaces are `apgr:`, `project:` and `user:`. Supplement retains all names.
A project config may declare:

```toml
[skills.overrides]
"apgr:go-language-profile" = "project:go-language-profile"
```

Only that project's captured configuration authorizes replacements. Global home
configuration cannot replace project/canonical authority. An existing global
config is reported as not consulted, without parsing it or blocking listing. Listings retain both
source descriptors and the separate relation with config path and SHA-256.
Text output also marks whether the replacement body is available.
Self, cross-authority, duplicate-origin and conflicting-target mappings are
rejected. The closed configuration owners accept only `skills.overrides` as a
string-to-string table; semantic validation runs during explicit catalog use.
F adds the closed dispatcher.context table described in [context planning](context-planning.md). No MCP table is admitted.

Malformed optional leaves are excluded with identity/path diagnostics. Missing
roots are empty sources with status. A missing/malformed override target is a
partial-list diagnostic and an error when that origin is explicitly selected.
Unrelated explicit selections remain usable. Duplicate source IDs are invalid
input. A bare multi-source ID resolves only when unique; canonical V1 bare IDs
keep their prior behavior. Directory order and mtimes never choose winners.

## Go and native CLI boundary

`skills.BuildCatalog(CatalogInput)` is the pure model; `CaptureCatalogSource`
is its explicit filesystem adapter. `ResolveCatalog(input, requested, consumer)`
returns requested identity, selected identity, source SHA-256, portable content
identity, rule/catalog fingerprints and a caller-owned exact byte snapshot.
No exported result shares mutable cache collections. Sources supplied to the pure
model cannot assert the `apgr:` namespace or APGR-certified maturity.

Python loads TOML through the established closed owner, snapshots and hashes
those exact bytes, and passes `apg.skill-catalog/v1` JSON to native
`skills catalog --stdin [--project-root PATH] [--apgr-home PATH]`. Go does not
parse TOML or launch a second resolver. Native `skills list --all-sources` is an
explicit-data convenience for embedded or caller-selected roots; it does not
discover projects, consult APGR_HOME/default home, discover configuration or
apply TOML mappings. With no root flags it lists embedded records only and has
no optional-source statuses. Configuration-aware callers use
the Python command or supply captured relations through `catalog --stdin`.
JSON listings omit snapshot body payloads but retain per-leaf provenance.

## Source and measurement boundaries

`BodyBytes`, `BodyCharacters` and `BodySHA256` retain the exact whole SKILL.md
meaning. `BodyOnly*` measures bytes immediately after the closing frontmatter
line and its terminating LF, through EOF. Description bytes/digest measure the
literal value after `description: ` without a terminating LF. Characters count
UTF-8 code points, never tokens. Tokens are unavailable (`null`). H2 `Do not use`
and `Project-owned parameters` text is derived without semantic classification.

The closed single-line frontmatter grammar requires name and description. New
optional `requires` and `support` keys contain JSON arrays of distinct strings:

```text
requires: ["project:build-rules"]
support: ["references/contract.md"]
```

Only `requires` creates typed directed edges, with missing-target and cycle
validation. It does not add bodies to selection. Prose links and undirected
`CompositionRules()` never create dependencies. `support` files are exact byte
snapshots with their own size and digest. `captured` means captured at source,
not delivered into a provider context; merely referenced companions are not
claimed delivered. External `maturity` is separately source-declared metadata;
its qualified maturity remains `unqualified`.

Each skill/support file is bounded to 1 MiB, declarations to 32 entries, source
enumeration and explicit snapshot inputs to 4096 leaves, and pure input bytes to
64 MiB. Descriptor-relative `os.Root` access confines descendant traversal;
final skill/support symlinks and nonregular files are refused. File identity,
size and modification observations are checked around capture. These are
operation-local observations, not a long-lived filesystem transaction or lock.
Portable content identity excludes concrete roots and source paths; provenance
retains those paths. The catalog fingerprint includes rule identity, descriptors
and override/config digests, excluding operation path spelling.

## Generation and qualification

`skills/catalog_generated.json` is generated, not a fourth manual classification
source. `skills generate-catalog --repository ABSOLUTE_ROOT` writes deterministic
JSON to stdout. Save it to a separate temporary file, then replace the generated
owner. `skills verify-corpus` now verifies it alongside existing corpus metadata.
Generation derives canonical descriptions/sections, catalog Trigger boundaries,
ledger maturity, maintained consumer references, selection facts and costs.
Authority digests bind exact canonical bytes and declared dependencies; no clock,
absolute host path or user identity enters embedded metadata. Built binaries
need no runtime ledger or catalog Markdown.

APG163 reconciles only RTK's factual D provisional admission, with empty maturity
evidence and unavailable independent review. Existing promotion criteria remain
unchanged. The E collision/source fixtures record correction revision E-CATALOG1 for
previously untested catalog contracts in scenarios 08/09, preserving their
synthetic payloads and numerical freeze; canonical CLI compatibility uses measured
accepted D entry outputs in a separate fixture, preserving the v0.10 release
fixture; they do not complete H's evaluation.

## Late acquisition

APG165 adds [run-owned CLI and MCP acquisition](skill-acquisition.md) over this
same explicit catalog/source authority. It does not change legacy canonical-only
operations, source precedence or planner applicability.
