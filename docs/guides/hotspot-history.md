# Hotspot Git History Analysis (v2)

APG's public Go package `hotspot` provides an opt-in v2 history analysis that
augments structural hotspot metrics with deterministic, file-level churn and
growth extracted from local Git history. Strict v1 in-process structural analysis
remains completely unchanged: v1 requests, reports, golden fixtures, rankings,
and byte contracts are preserved without alteration.

The canonical v2 machine schemas are `apg.hotspot-request/v2` and
`apg.hotspot-report/v2`.

## Public Go API

```go
report, err := hotspot.AnalyzeV2(ctx, requestV2)
jsonDocument, err := hotspot.MarshalJSONV2(report)
terminal, err := hotspot.RenderTerminalV2(report)
markdown, err := hotspot.RenderMarkdownV2(report)
```

`RequestV2` uses schema `apg.hotspot-request/v2`. Callers can construct a request
via `DefaultRequestV2(root, startOID, endOID)`, which configures mandatory v1
scan defaults alongside history defaults.

`ParseRequestV2JSON` is the strict JSON parser for v2 requests. It enforces the
same validation rules as v1 (no unknown fields, no duplicate keys, clean paths)
while adding strict validation for history parameters:
- `history.start_oid` and `history.end_oid` must both be provided as full 40-character (SHA-1)
  or 64-character (SHA-256) hexadecimal object identifiers.
- History limits must be positive integers not exceeding system bounds.

## CLI Invocation

History analysis is selected on the command line by supplying both `--history-start`
and `--history-end`:

```text
apgr --repository /absolute/git/root analyze hotspots \
  --history-start 0123456789abcdef0123456789abcdef01234567 \
  --history-end   fedcba9876543210fedcba9876543210fedcba98
```

The example uses the Go/npm CLI global option. The Python launcher selects the
current working directory by default; run it from the Git root and omit
`--repository`. Its explicit APG-workspace selector is `--project-root`.

When both flags are omitted, the CLI operates in strict v1 mode. Supplying only
one flag is refused. The `git`
executable on `PATH` is required ONLY when history flags are provided; v1 scans
do not require `git`.

## Git Invariants and Environment Isolation

History analysis operates strictly offline and read-only against the local
object database:

The observed trees must contain only supported regular files: a committed
symlink or gitlink anywhere refuses the request before include/exclude filtering.
APGR itself has committed skill-projection symlinks and cannot use this history
mode on its current tree. This is an explicit applicability limit; v1 structural
analysis remains available. Ranges cannot exceed 256 first-parent commits,
which is both the default and hard ceiling.

1. **Root equality**: The analyzed root must equal the physical Git top-level
   directory (`git rev-parse --show-toplevel`). Bare repositories and subtrees
   inside a larger repository are strictly refused.
2. **Environment isolation**: All inherited `GIT_*` environment variables are
   purged from subprocess execution. The environment is explicitly populated with:
   - `GIT_CONFIG_NOSYSTEM=1`
   - `GIT_CONFIG_GLOBAL=/dev/null`
   - `GIT_CONFIG_SYSTEM=/dev/null`
   - `GIT_NO_REPLACE_OBJECTS=1`
   - `GIT_NO_LAZY_FETCH=1`
   - `GIT_TERMINAL_PROMPT=0`
   - `GIT_OPTIONAL_LOCKS=0`
   - `LC_ALL=C`
   Every Git invocation additionally supplies `-c protocol.allow=never`.
3. **Repository sanity gates**: Prior to reading any object data, the analyzer
   inspects the repository and refuses:
   - Shallow repositories (`git rev-parse --is-shallow-repository` or `.git/shallow`).
   - Repositories with grafts (`.git/info/grafts`).
   - Repositories with alternates (`.git/objects/info/alternates`).
   - Partial or promisor clones (`extensions.partialclone` or promisor remotes).
   - Unsupported repository formats or missing Git directories.
4. **No mutations**: No network operations, fetching, credential helpers, hooks,
   working tree modifications, or index mutations are ever performed.

## Range Semantics and First-Parent Chain

1. **Range boundaries**: The commit range is defined as `startOID` excluded and
   `endOID` included (`start..end`) traversed strictly along the first-parent
   chain of `endOID`.
2. **First-parent merge diffs**: Merge commits on the first-parent chain are
   compared strictly against their first parent (parent 1), representing merge
   integration churn.
3. **Path identity**: Transitions use exact path identity without rename
   inference (`--no-renames`). A file rename is recorded as a deletion of the old
   path and an addition of the new path.
4. **Empty range**: When `startOID == endOID`, the range contains 0 commits. Supported committed text paths report zero transitions, churn and growth;
   binary or never-committed paths retain unavailable line metrics.
5. **Ancestry enforcement**: `startOID` must be an ancestor of `endOID` along the
   first-parent chain within the configured commit limit. If `startOID` cannot be
   reached along the first-parent chain, the entire operation is refused.

## Churn, Growth, and Transition Metrics

1. **Content-changing transition count**: A commit transition increments a
   path's transition count if and only if the blob object identifier changes
   (`old_oid != new_oid`). Pure mode changes do not increment the count.
2. **Physical lines**:
   - Lines are partitioned by line feed (`\n`, `0x0A`).
   - Carriage return (`\r`, `0x0D`) immediately preceding `\n` is preserved.
   - An unterminated non-empty final segment counts as a physical line.
   - An empty file has 0 lines.
3. **Deterministic LCS churn**:
   - For text files, churn is the sum of inserted lines and deleted lines
     across all transitions in the range, calculated using the Longest Common
     Subsequence (LCS) shortest edit script.
   - For an edit between sequences of lengths $M$ and $N$ with LCS length $L$,
     churn is $(M - L) + (N - L) = M + N - 2L$.
4. **Endpoint growth**:
   - Growth is the signed difference in physical line counts between the end
     endpoint and start endpoint: $\text{lines}(\text{end}) - \text{lines}(\text{start})$.
   - If a path did not exist at start, $\text{lines}(\text{start}) = 0$.
   - If a path was deleted before or at end, $\text{lines}(\text{end}) = 0$.
5. **Binary files**:
   - Any blob containing a NUL byte (`0x00`) or invalid UTF-8 is classified as
     binary.
   - If a file is binary at either endpoint or during any transition where line
     metrics are evaluated, line metrics (`churn` and `growth`) are marked
     `unavailable` (never reported as zero).
   - Content-changing transitions continue to be counted.
6. **Deleted paths**:
   - Paths present in history but deleted in the working tree or at `endOID`
     are retained in the history records.
7. **Content digest binding**:
   - The SHA-256 digest of each file in the working tree is bound against the
     blob SHA-256 at `endOID`.
   - Each file's working tree status is classified as:
     - `clean`: working tree content matches the `endOID` blob.
     - `modified`: working tree content differs from the `endOID` blob (dirty).
     - `untracked`: path exists in working tree but was not present in `endOID`.
     - `deleted`: path existed in history/end but is absent from working tree.
   - Unmatched files (`modified` or `untracked`) retain their explicit mismatch;
     committed path measurements do not attribute history to current content.
8. **Ranking preservation**:
   - v1 structural rankings are preserved without modification. History metrics
     are reported alongside structural metrics without disrupting v1 ranking
     vectors.

## Hard Limits and Fail-Closed Behavior

History analysis enforces mandatory upper bounds to guarantee bounded resource
consumption:

| Metric | Hard Limit |
| --- | ---: |
| Maximum commits in range | 256 |
| Maximum path transitions | 50,000 |
| Maximum bytes per blob | 4 MiB (4,194,304 bytes) |
| Maximum total input read | 128 MiB (134,217,728 bytes) |
| Maximum comparison cells per pair | 4,000,000 ($M \times N$) |
| Maximum aggregate comparison cells | 64,000,000 |

Callers may lower history limits in `RequestV2.History.Limits`, but cannot exceed the system
bounds. If any limit is exceeded or history is incomplete, the entire history
operation fails closed with an explicit error. Context cancellation and timeouts
are checked across traversal, diffing, and blob reads.

## Determinism and Output Views

- **JSON (`MarshalJSONV2`)**: Emits compact UTF-8 JSON terminated with one
  newline, validated against `apg.hotspot-report/v2`. Includes a SHA-256
  fingerprint computed over the canonical identity view (excluding the
  fingerprint itself, warning prose and execution resource counters).
  `total_blobs_read`, `total_input_bytes` and `aggregate_cells` remain visible
  diagnostics, but are normalized to zero in both history and report identity
  views. They are not semantic measurement inputs. Full JSON is repeatable for
  the same implementation and inputs; resource diagnostics may differ across
  implementation strategies without changing either semantic fingerprint.
- **Terminal (`RenderTerminalV2`)**: Concise situational view showing the
  history range, commit count, path transitions, available-only churn/growth subtotals and unavailable path count,
  path-ordered rows bounded by `--top`, and report fingerprint. No new ranking
  or complexity/churn combined score is selected.
- **Markdown (`RenderMarkdownV2`)**: Complete Markdown documentation including
  history configuration, range summary, per-file churn/growth table, and full
  appendix.

## Scope, completeness and compatibility details

Literal include/exclude paths and default directory exclusions apply to history.
The history population also includes selected committed regular files that the
current structural classifier omits, plus selected deleted paths. These do not
become synthetic zero-sized structural files. `not-scanned` means no current
content binding was obtained; it is not deletion. Historical language filters
are refused in v2 because current language does not establish historical
classification. V1 language selection is unchanged.

History JSON records policy `first-parent-path-lf-lcs/v1`, ordered commit IDs,
object format, exact start/end blob IDs, all limits and explicit units. Churn
counts inserted plus deleted physical lines; growth counts signed physical
lines. LF terminators are part of line identity: adding a final LF changes one
line identity (one deletion plus one insertion), while net growth stays zero.
Every selected transition blob is read even after binary detection. Missing
required history refuses the whole observation. Completeness is for the declared
first-parent path selection, not an audit of unrelated side-branch objects.

Available subtotals exclude unavailable rows and disclose their count; they do
not claim complete repository totals. Untracked content with no committed path
history has unavailable line metrics, not a favorable zero score. Dirty content
may display committed path history alongside its explicit mismatch, but receives
no historical attribution to current functions. No combined score is implemented.

`ParseRequestV2JSON` accepts at most 65,536 UTF-8 bytes. Its wire fields retain
the v1 flat scan-limit names (`max_files`, `max_bytes_per_file`, `max_total_bytes`,
`max_duration_milliseconds`) plus `history` with `start_oid`, `end_oid`, and
`limits`; Go request structs are constructed through `DefaultRequestV2` or this
parser, not assumed to have the same `encoding/json` representation. Unknown,
duplicate, overflowing or unsupported values are refused.

All v2 renderers verify history and report fingerprints. The structural part
retains its v1 fingerprint; the history report has its own v2 fingerprint.
Rollback selects existing v1 APIs and omits both history flags. No public v0.10
object, frozen fixture, default invocation or strict v1 schema changes. A strict
v1 consumer must explicitly adopt v2 types and semantics to consume history.
V0110-F must register the new source/test/document surfaces in v0.11 release
selection and qualify distribution and supported platforms.

The bounded Git store implementation additionally refuses linked worktrees,
non-directory `.git`, common-directory indirection, config includes, local
protocol overrides, object-store symlinks/nonregular entries, promisor pack
markers, historical symlinks and gitlinks. These are historical-mode limits,
not restrictions on v1 or unrelated tooling. Repository tree metadata is
validated before path filtering, so an unsupported historical entry anywhere
in an observed tree refuses the request, including outside selected prefixes.
Git metadata output is capped at 16 MiB per stream per command; tree/object
store inventory is capped at 100,000 entries and the selected historical path
population at 50,000. Object-store directory depth is bounded to three.

The offline subprocess environment also sets an empty `GIT_ALLOW_PROTOCOL` and
explicitly disables known protocol transports, external diffs, text conversion
and rename inference. No fallback object format is guessed. Full commit IDs
must name commits directly, not annotated tag objects. Native Git supplies
local object traversal; all selected blob payloads receive independent object
hash checks before use. No whole-repository fsck or unrelated side-branch
completeness is claimed. Unsupported object stores are refused rather than
fetched, repaired or reconfigured.
