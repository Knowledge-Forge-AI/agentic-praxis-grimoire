# Structural Hotspot Analysis

APG's public Go package `hotspot` analyzes one exact source root in process. It
does not execute source, invoke a shell, load target plugins or configuration,
follow symlinks, read outside the root, or inspect Git history. The canonical
machine schema is `apg.hotspot-report/v1`; terminal and Markdown output render
the same report model.

## Public Go API

```go
report, err := hotspot.Analyze(ctx, request)
jsonDocument, err := hotspot.MarshalJSON(report)
terminal, err := hotspot.RenderTerminal(report)
markdown, err := hotspot.RenderMarkdown(report)
```

`Request` uses schema `apg.hotspot-request/v1`. Callers can start with
`DefaultRequest(root)`, then set a logical `RootID` and the producer's
`ToolVersion`. The root must be an absolute clean path to an existing direct
directory, and its resolved physical path must equal the requested path. The
report contains only the logical root ID and root-relative paths; it never
contains the absolute root.

`ParseRequestJSON` is the strict JSON adapter. It rejects unknown fields,
duplicate keys at any object depth, multiple JSON values, unknown or duplicate
language filters, unsafe relative-path filters, unsupported schema versions,
and invalid limits. Direct callers receive the same validation from `Analyze`.

## Default limits and filters

All limits are mandatory and positive. The defaults are:

| Limit | Default |
| --- | ---: |
| analyzed files | 50,000 |
| bytes per file | 16,777,216 |
| total bytes read | 536,870,912 |
| elapsed time | 120 seconds |
| terminal rows per section | 10 |
| maximum directory depth | 256 |
| maximum parsed JSON/XML depth | 512 |

File, per-file byte, total-byte, directory-depth, structured-depth, and elapsed
limits fail closed. Cancellation is checked during directory traversal, every
64 KiB read chunk, after language analysis, and before report completion. No
partial result receives a complete fingerprint.

Include and exclude paths are literal clean root-relative path prefixes, not
globs. Include-language values must name a frozen classification. Default
directory exclusions are `.git`, `.hg`, `.svn`, `node_modules`, `vendor`,
`.venv`, `venv`, `dist`, `build`, `target`, `.scratch`, `outbox`,
`.pytest_cache`, `.mypy_cache`, `__pycache__`, `.cache`, `coverage`, and
`.coverage`. Every rule appears in the report with observed directory and file
entry counts where known. A caller may disable the complete default directory
set and may add explicit relative exclusions.

The walker reads direct regular files only. It records symlink and non-regular
entries as exclusions. An unknown extensionless file is excluded unless a
bounded shebang recognizes Bash, Zsh, POSIX shell, Python, or Node JavaScript.
`/usr/bin/env` accepts exactly one non-option interpreter name; `env -S` and
ambiguous argument forms are rejected. Unknown files with an extension remain
inventory rows with byte/line size and explicit unavailable semantics.

Each included file is bound by `lstat`, a no-follow open, file-descriptor stat,
a bounded read, another descriptor stat, a final `lstat`, path-chain
revalidation, size/mode/identity/modification-time comparison, and a content
SHA-256. Drift, unreadable files, root topology changes, and hard limits fail
the entire scan.

## Classification and capability matrix

`exact` means exact for the stated grammar or file property. `structural` means
a bounded lexical or structural scan. `unavailable` has no numeric
approximation. `not-applicable` is not meaningful.

| Surface | Classification inputs | Statements | Cyclomatic | Nesting | Procedural regions | Confidence |
| --- | --- | --- | --- | --- | --- | --- |
| Go | `.go` | exact AST | exact AST | exact AST | package initializers and `init` | high |
| Markdown | `.md`, `.markdown` | not applicable | not applicable | structural heading depth | not applicable | high |
| MDX | `.mdx` | unavailable | unavailable | structural region depth | embedded regions | medium |
| Astro | `.astro` | unavailable | unavailable | structural region depth | frontmatter/template regions | medium |
| Python | `.py`, `.pyi`, shebang | unavailable | unavailable | unavailable | unavailable | low |
| Java | `.java` | unavailable | unavailable | unavailable | unavailable | low |
| Kotlin | `.kt`, `.kts` | unavailable | unavailable | unavailable | unavailable | low |
| JavaScript | `.js`, `.mjs`, `.cjs`, shebang | unavailable | unavailable | unavailable | unavailable | low |
| TypeScript | `.ts`, `.mts`, `.cts` | unavailable | unavailable | unavailable | unavailable | low |
| JSX / TSX | `.jsx`, `.tsx` | unavailable | unavailable | unavailable | unavailable | low |
| HTML | `.html`, `.htm` | not applicable | not applicable | balanced-tag structural depth | not applicable | medium |
| XML / XML plist | `.xml`, `.xsd`, `.svg`, `.xsl`, `.xslt`, text `.plist` | not applicable | not applicable | exact parsed depth | not applicable | high |
| binary plist | `bplist00` `.plist` | not applicable | not applicable | unavailable | not applicable | low |
| CSS | `.css` | unavailable | not applicable | structural block depth | top-level rules | medium |
| JSON family | `.json`, `.jsonc`, `.json5` | not applicable | not applicable | exact when strict JSON parses | not applicable | high |
| YAML / TOML | `.yaml`, `.yml`, `.toml` | not applicable | not applicable | unavailable | not applicable | low |
| Terraform / Gradle | `.tf`, `.tfvars`, Gradle names/extensions | unavailable | unavailable | unavailable | top-level blocks | low |
| SQL | `.sql` | unavailable | unavailable | unavailable | statement-like regions | low |
| Bash / Zsh / POSIX shell | extensions and supported shebangs | unavailable | unavailable | unavailable | top-level structural regions | low |
| Dockerfile | `Dockerfile`, `Containerfile`, bounded variants | structural logical instructions | not applicable | not applicable | exact instruction regions | high |
| Vagrantfile | exact `Vagrantfile` | unavailable | unavailable | unavailable | top-level structural regions | low |

Known text extensions are still subject to bounded binary detection. A binary
payload is not treated as text merely because its name has a source extension.
Strict JSON-family bytes are never normalized: comments or trailing commas
produce a parse warning and explicit unavailable deep metrics. Streaming JSON
counts duplicate keys rather than collapsing them. XML uses `encoding/xml` and
does not perform external I/O. Binary plist is bytes-only in v1.

Markdown counts physical lines, non-empty prose lines outside fences, fence
content lines, ATX headings, maximum heading depth, fenced blocks, and the
conservative inline-link token `](`. Setext headings and complex inline syntax
are not grammar-parsed. MDX and Astro preserve prose and embedded-region line
counts independently; embedded statements remain unavailable.

Structural scanners count only their named lexical surfaces: HTML tags and
attributes; CSS braces, selectors, and semicolon declarations; YAML/TOML keys
and indentation; Terraform/Gradle/Vagrant braces, assignments, and calls; SQL
statement separators and named clauses; shell non-comment command lines and
named control tokens; and Dockerfile continuations, instructions, stages, and
`RUN` instructions. These values do not claim grammar validity or semantic
complexity.

## Go metric definitions

Go files use `go/parser`, `go/ast`, and `go/token` with one deterministic token
file set per file. A syntax error retains the file inventory/hash/line row and
makes deep metrics unavailable; it does not crash the scan.

Each function, receiver-qualified method, and function literal is a distinct
owner. Function-literal IDs use the root-relative path and source line/column.
Nested literals do not contribute their bodies to the parent owner.

- Statements count every recursively owned `ast.Stmt` except
  `ast.BlockStmt`. This includes `for` initializer/post statements and case or
  communication clauses. Nested function-literal bodies are excluded.
- Cyclomatic complexity begins at 1. It adds one for each `if`, `for`,
  `range`, non-default expression/type-switch case, non-default select
  communication clause, and each AST `&&` or `||` operator. A switch or select
  container does not add a second increment beyond its consequence-bearing
  clauses.
- Nesting is maximum owned depth across `if`, `for`, `range`, expression
  switch, type switch, and select constructs.
- Parameters count grouped names individually and unnamed parameters once;
  receivers and type parameters are excluded.

The standard `// Code generated ... DO NOT EDIT.` header marks generated Go.
Generated files remain in inventory and aggregates but are excluded from
refactoring rankings by default.

## Owners and procedural regions

Every file, owner, and region has a deterministic report-local ID based on its
relative path, kind, and source coordinates. Rows include confidence, line
span, available raw metrics, unavailable reasons, and a ranking vector.

Procedural regions are not renamed functions. Go exposes package initializer
and `init` regions. MDX/Astro expose embedded regions. CSS exposes rule
regions. Terraform, Gradle, and Vagrantfile expose top-level blocks. SQL and
shell expose bounded top-level regions. Dockerfile exposes each logical
instruction.

## Deterministic ranking

Files, semantic owners, and procedural regions are separate populations.
Within each population, each available metric is ranked only with the same
metric capability class. For example, exact Go AST statements and structural
Dockerfile instructions never share a statement percentile. Exact byte size is
a shared file-size class.

Percentiles are integers from 0 through 10,000. Equal raw values receive the
same midpoint percentile for their tie group:

```text
floor((first_zero_based_rank + last_zero_based_rank) * 10000
      / (2 * (population_size - 1)))
```

A one-row class receives 10,000. Path and ID order make population construction
deterministic but never give equal raw values different percentiles.

The frozen weights are:

| Metric | Weight |
| --- | ---: |
| cyclomatic complexity | 35 |
| statements | 25 |
| nesting | 15 |
| top-level procedural size | 15 |
| file/owner/region size | 10 |

The risk score is the integer weighted mean of available percentile values.
Unavailable metrics contribute neither value nor weight. Final order is score
descending, available weight descending, confidence high-to-low, relative path
ascending by UTF-8 bytes, then report-local ID ascending.

Refactoring candidates are deterministic metric-derived inspection prompts.
Reason codes are limited to `large-file`, `high-cyclomatic`, `large-owner`,
`deep-nesting`, `large-procedural-region`, `multiple-hotspot-owners`, and
`low-confidence-size-only`. They do not assert coupling, a responsibility
violation, a "god object", or a valid extraction boundary. Percentiles are
report-local and must not be compared across repositories as one population.

## JSON schema and fingerprint

`MarshalJSON` emits compact UTF-8 JSON plus one newline. The complete report
contains schema/tool versions, logical root ID, scan configuration, all
exclusion rules, capability declarations, `growth/churn: deferred`, language
aggregates, complete file/owner/region rows, explicit unavailable reasons,
rankings, candidates, warnings, content hashes, and the report fingerprint.

The SHA-256 fingerprint covers a canonical JSON identity view containing all
deterministic consequence-bearing scan facts and ranking results. It excludes
the fingerprint field itself and human warning prose. It never includes an
absolute root, timestamp, elapsed duration, hostname, PID, user name, random
nonce, or Git-history fact. A compact multi-language example is maintained at
`hotspot/testdata/golden/multilanguage.json` and includes unavailable Python
semantic metrics.

## CLI and renderers

The Go adapter uses the existing global root option:

```text
apgr --repository /absolute/physical/root analyze hotspots
apgr --repository /absolute/physical/root analyze hotspots --format json
apgr --repository /absolute/physical/root analyze hotspots --format markdown
```

Terminal is the default and limits each situational section to 10 rows unless
`--top` selects 1 through 100. It shows the logical root, language aggregate,
largest files with their true primary unit, difficult Go owners, metric-derived
candidates, material warning count, and compact fingerprint.

Markdown contains an executive summary, table of contents, configuration and
exclusions, capability/confidence legend, largest files, aggregates,
per-language results, complexity owners, procedural regions, refactoring
candidates, unavailable/deferred semantics, warnings, and a path-sorted full
file appendix. Machines consume JSON and never need to parse Markdown.

`--output` creates one new owner-only file outside the analyzed root. It
requires an absolute clean path with a physical existing parent, refuses an
existing destination, and never replaces or writes a target source file.

Normal Python `apgr analyze hotspots` resolves the current physical directory
or explicit APG project root and delegates the exact analysis tail to the Go
binary bridge. Python has no analyzer or semantic fallback.

## Dogfood and future consumers

For repeatability evidence, materialize one immutable source snapshot, keep
report output outside that root, scan it twice with the same logical root ID,
and compare canonical JSON bytes and fingerprints. Analyzing a second project
does not authorize its source, build, tests, or history; APG99 JACA dogfood is
source-read-only.

A later JACA planner or separately authorized APG refactoring skill may select
ranked file, owner, or region IDs and cite raw metrics, confidence, and
unavailable reasons. It may not rewrite metric/rank/fingerprint authority,
convert structural guesses into semantic facts, or claim that a high score
proves a design violation. Growth/churn, Git history, PR deltas, AI-authored
refactoring plans, and skill authoring are outside hotspot v1.
