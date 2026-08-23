# APG99 Structural Hotspot Analyzer

## Terminal result

APG99 implements accepted ADR 0051's structural-hotspot slice as the public,
provider-neutral Go package `hotspot`. The public operations are `Analyze`,
`MarshalJSON`, `RenderTerminal`, and `RenderMarkdown`. The request and report
schemas are `apg.hotspot-request/v1` and `apg.hotspot-report/v1`.

The analyzer requires one absolute clean direct-directory root and a logical
root ID. It walks read-only without following symlinks, reads direct regular
files through no-follow descriptors, binds identity before and after each
bounded read, revalidates the path chain, and fails closed on root escape,
drift, hard limits, unreadable included files, cancellation, or elapsed-time
expiry. Canonical reports contain only logical and root-relative identities.

## Capability and metric result

The frozen matrix is implemented without a third-party dependency. Go uses
`go/parser`, `go/ast`, and `go/token` for exact statement, receiver-qualified
owner, cyclomatic, control-nesting, parameter, package-initializer, and `init`
metrics. Function literals are distinct source-coordinate owners and do not
inflate their parent.

Markdown, MDX, Astro, HTML, XML, XML plist, binary plist, JSON-family, CSS,
YAML, TOML, Terraform, Gradle, SQL, Bash, Zsh, POSIX shell, Dockerfile, and
Vagrantfile rows preserve their frozen exact, structural, unavailable, or
not-applicable status. Python, Java, Kotlin, JavaScript, TypeScript, JSX, and
TSX remain physical-line/lexical inventory with explicit unavailable semantic
metrics. Malformed recognized text stays in inventory with an unavailable
reason and warning rather than an invented approximation.

Default limits are 50,000 files, 16 MiB per file, 512 MiB total bytes, 120
seconds, directory depth 256, and structured depth 512. The deterministic
default exclusions and every observed exclusion count remain visible. Unknown
files with extensions remain byte/line inventory; unsupported extensionless
files require a conservative recognized shebang.

## Report and ranking result

Canonical JSON contains full file, owner, and procedural-region populations,
content SHA-256 identities, capability declarations, unavailable reasons,
confidence, language aggregates, rankings, deterministic candidate reason
codes, and `growth/churn: deferred`. Its report SHA-256 excludes host paths,
timestamps, elapsed duration, process/host identity, random values, and human
warning prose.

Ranking uses separate file, owner, and procedural-region populations. Integer
0..10,000 percentiles are further separated by metric capability class; equal
raw values share their tie-group midpoint percentile. The frozen weights are
cyclomatic 35, statements 25, nesting 15, procedural size 15, and size 10.
Missing metrics contribute neither value nor denominator. Final ordering is
score, available weight, confidence, UTF-8 relative path, then deterministic
row ID.

Default terminal output is a bounded top-10 situational view. Detailed
Markdown includes a table of contents, configuration, exclusions, capability
legend, full language and hotspot views, unavailable/deferred semantics,
warnings, and a complete path-sorted appendix. Both consume only `Report`;
JSON is the machine interchange authority.

## Consumer and dogfood result

The Go CLI uses the existing global absolute `--repository` option and exposes
terminal, JSON, Markdown, top-N, limit, filter, and exclusive external-output
options. Normal Python `apgr analyze hotspots` delegates the exact tail argv to
the established Go bridge and implements no analysis fallback. A disposable
external Go module consumes all four public operations in process.

Two immutable APG candidate scans and two scans of a freshly bound read-only
JACA source snapshot produce byte-identical canonical JSON and fingerprints
within each repository. The reports remain report-local and do not compare
their percentiles as a shared population. Current JACA source identities are
retained in publication-excluded APG99 evidence; exact candidate manifests,
fingerprints, counts, and top rows remain in machine-local scratch and the
dispatcher pre-final handoff so they do not make the analyzed source
self-referential. Neither target was modified or executed.

## Preserved boundaries

Version remains 0.6.0. Skills remain 39 canonical, 39 catalog rows, 39
projections, and 39 discoverable, with 14 stable / 25 provisional, zero
malformed, 9,504 description bytes, 9,492 characters, and the 9,527-byte
ceiling. APG96 reporting, APG97 context bundles, and APG98 environment
snapshots remain unchanged.

APG99 changes no skill body, maturity, report/skill/environment schema,
build-info contract, JACA, `.flakes`, Nix, package version, wheel, npm package,
response capture, public release, deployment, README information architecture,
or APG100 state. It neither imports JACA nor inspects Git history.

## Verification and disposition

Focused evidence covers every classification row, exact Go metric vectors,
hybrid and structural metrics, strict JSON/XML depth, binary and malformed
rows, ties and capability classes, unavailable-weight omission, deterministic
JSON/rendering, root safety, exclusions, file/per-file/total-byte/time/depth
limits, cancellation during walk/read, unreadable input, drift, CLI modes and
output safety, Python exact-argv delegation, and external Go consumption.

Exact resulting-state command counts, supported-target cross-build evidence,
dual-dogfood identities, regression gates, invariant checks, and the
prospective candidate byte manifest belong to the dispatcher pre-final
handoff. The broad Python gate retains its truthful external-prerequisite
disposition if the exact required compiler remains unavailable.

Terminal disposition:
`V07_STRUCTURAL_HOTSPOTS_READY_FOR_APG100`.

APG99 is preserved by APG100.
