# APGR CLI Reference

`cmd/apgr` is the canonical Go command adapter over APG's public packages and
private path/publication adapters. Portable report, skill, environment,
hotspot, and response semantics remain owned by their Go packages; private
`internal/cli` code owns argument handling, consequence-bearing input-file
safety, exact-argv process adapters, and compatibility routing.

## Implemented command surface

The bounded Go surface is:

```text
apgr --help
apgr --version
apgr build-info
apgr report show
apgr report diff
apgr report operational
apgr report ops
apgr report path
apgr report recover
apgr skills list
apgr skills context-report
apgr skills resolve
apgr skills materialize
apgr footprint measure
apgr footprint compare
apgr footprint project
apgr env profile-check
apgr env snapshot
apgr env show
apgr env resolve
apgr env run
apgr analyze hotspots
apgr response capture
apgr response record
```

Direct Go report execution requires explicit repository, outbox, and project
values as applicable. The Go CLI does not parse APGR TOML. Python remains the
configuration owner for `--apgr-home`, `APGR_HOME`, project/global configuration,
`outbox_root` precedence, project discovery, and reserved adapter-path checks.
It forwards the resolved scalar values to Go using an exact argument vector and
never a shell.

Repository maintenance commands, including the `test` command family (`apgr test`),
are routed through Python to repository-local helpers (`libexec/apg_test.py`). These
maintenance commands require an APGR Git source checkout and the developer
toolchain; they are not carried by the prebuilt native Go binary (`cmd/apgr`) or
bare distribution packages.

Exit classes remain 0 for success, 2 for usage, 1 for runtime/repository/
publication failure, and 130 for keyboard interruption. SIGTERM and SIGHUP use
the bounded runtime-failure class rather than being mislabeled as keyboard
interruptions.

## Build information

Source defaults are `devel`. A release-like build injects the package version
and corpus fingerprint through Go linker variables; Go source contains no
second release-version constant. `build-info` emits deterministic compact JSON
with version, module path/version, target, Go toolchain, corpus fingerprint,
report envelope/schema versions derived from `schema`, and the ordered supported
target matrix. It includes no current time, hostname, username, caller path, or
environment dump.

APG96 defined the corpus identity as SHA-256 of the canonical installed metadata
resource `src/agentic_praxis_grimoire/resources/skill-metadata.json`. APG97
reconstructs those exact bytes from the embedded canonical bodies and reports
the injected expected fingerprint, embedded actual fingerprint, and equality.
Release-like mismatch fails closed. The current identity is
`0509803b3c12e0366917a341c9d56945d7966897953415acf0c997254e1331c1`.

`bin/apg-build-go-cli` is a thin wrapper over `libexec/apg_go_build.py`. It reads
the one editable Python `VERSION` resource, hashes the canonical metadata
resource, rejects targets outside `darwin/arm64`, `linux/amd64`, and
`linux/arm64`, sets `CGO_ENABLED=0`, builds with trimmed source paths and no VCS
stamping, and reports the resulting binary SHA-256. Successful cross-build is
build evidence only; it is not runtime qualification of a foreign target.

## Python strangler bridge

Normal Python report routing uses this deterministic locator order:

1. an explicit `APGR_GO_BINARY` development/test override naming an absolute,
   clean, direct regular executable;
2. the package-bundled `agentic_praxis_grimoire/bin/apgr` binary; or
3. an exact source-checkout development build from the verified APG root module.

The source-checkout bridge builds a release-like binary in an
invocation-private temporary directory from the exact checkout version and
corpus, verifies its build information, runs exact argv, forwards interruption
signals, and removes the directory on return. It performs no runtime download
and does not search `PATH` for an unrelated `apgr` executable. This mode
requires a local Go toolchain and writable Go cache. The explicit
`APGR_GO_BINARY` development/test override is also build-information verified.

For a bundled wheel binary, the bridge validates canonical manifest bytes,
package version, host target, module, corpus, build flags and schema,
executable size and SHA-256, and release-like `build-info` before launch.
Installed wheels never build, download, or search `PATH` for APGR.

The canonical `apgr report` routes and all three historical names
`git-show-report`, `git-diff-report`, and `append-operational-report` delegate to
Go. `libexec/agent_report` is reachable only through the test-owned direct
oracle entry used by differential regression. A missing Go bridge fails
clearly; there is no Python semantic fallback.

Historical `GIT_SHOW_REPORT_ROOT` remains private CLI compatibility behavior.
An empty value selects the normal canonical destination. Canonical `apgr report`
uses Python's explicit resolved outbox and ignores the historical override.

APG97 also routes normal Python `skills list` and `skills context-report` to
the Go CLI with oracle parity. Python `skills resolve` and `skills materialize`
are new Go-backed convenience routes. Legacy project/user/install-global/
flatten maintenance remains Python-owned, and no migrated consumer route has a
Python semantic fallback. The public contracts and operator syntax are
documented in [Deterministic Skill Context Bundles](../guides/skill-context-bundles.md).

## Context-footprint commands

The `footprint` family is the CLI adapter for the public Go `footprint`
package:

```text
apgr footprint measure ...
apgr footprint compare ...
apgr footprint project ...
```

`measure` emits a canonical `apg.context-footprint/v1` record from explicit
local inputs. `compare` emits an integer-only
`apg.context-comparison/v1` result for compatible control and treatment
records. `project` emits a source-bound `apg.context-projection/v1` record with
fidelity and omission disclosure. Each command supports `--help` for its
current input and output contract and writes structured output suitable for
capture by a caller-owned process.

The commands do not execute providers or tokenizers, contact a registry, read
credentials, select routes, or account for a provider or JACA's total context.
Footprint accounting enforces three core principles:
1. **Source-bound observations, not capacity forecasts**: Records reflect explicit
   measurements and source-bound projections, not predictive capacity models or
   exhaustion controls.
2. **Unavailable is not zero (`unavailable != 0`)**: Missing or unavailable metrics
   remain explicit with stated reasons and nil values; they are not coerced to zero.
   An available zero is a measured fact; an unavailable metric is an unmeasured boundary.
3. **Component separation (overlap is not additive)**: Selected descriptions, selected
   bodies, support material, repository references, and provider prompt overhead are
   measured as distinct components. Because prompt templates and harnesses overlap in
   structure, component metrics cannot be summed across boundaries without accounting.

Unknown schema versions, fields, units, mappings, malformed input,
noncanonical bytes, incompatible comparisons, and consequence-bearing
projection omissions fail closed.

The Python `footprint` command family forwards its exact argument tail to this
Go owner and has no Python semantic fallback. These commands were included in
v0.8.1 and remain available in the 0.9.0 interface described here.

## CI qualification runner (`apgr test`)

In an APGR Git source checkout with the developer toolchain, `apgr test`
(and legacy wrapper `bin/apg-test`) provides the v0.9 CI qualification interface:

```text
apgr test <suite> [--workers <N>] [--summary-file <path>]
```

Supported suites:
- `policy`: fast mechanical checks (repository inventory, toolchain versions, skill library
  rules, Go embedded corpus identity, and record identity).
- `unit`: Python unit testing with exact 80/80 statement and branch coverage gates.
- `integration`: Python integration and CLI boundary tests with exact 80/80 gates.
- `unit-integration` (`combined` / `apg-dev-gate`): combined union gate requiring 85/85
  statement and branch coverage.

When `--summary-file <path>` is specified, APGR writes a strict 6-field machine-readable
JSON evidence receipt adhering to JACA's subproject evidence contract:

```json
{
  "version": 1,
  "subproject": "apg",
  "suite": "policy",
  "test_status": "pass",
  "gate_status": "pass",
  "source_commit": "1111111111111111111111111111111111111111"
}
```

> [!IMPORTANT]
> **Boundary of Authority**:
> - **Checkout and toolchain prerequisite**: `apgr test` requires an APGR Git checkout
>   and the full developer toolchain (Python 3.11+, pytest, coverage, pytest-cov,
>   pytest-xdist, Git 2.40+, Go 1.25+). The bare wheel, prebuilt native binary (`cmd/apgr`),
>   and npm platform packages do **not** carry the test runner or test suites.
> - **APGR-local qualification != JACA registration**: Conformance is qualified on
>   Darwin arm64 under APG114, but downstream runner registration in JACA CI
>   (`tools/ci/evidence.go`, `workflow.go`, `trustedRoleOrder`) is consumer-owned and pending.

`combined` is the emitted summary suite, and `apg-dev-gate` is a consumer role
alias; neither is an accepted CLI suite argument. The commit above is synthetic.
Real `source_commit` values bind entry HEAD, not uncommitted tested bytes. An
installed Python frontend can load the runner from the checkout when its Python
environment has the pinned test stack. Native/npm executables cannot dispatch
`test`, even from that checkout. See the [CI handoff](../architecture/jaca-ci-handoff.md)
for exact toolchain and environment prerequisites.

## Environment and hotspot analysis

`apgr env` validates strict environment profiles, captures explicit
allowlisted values into owner-only snapshots, shows values-free metadata by
default, resolves `isolated` or explicit `overlay` maps, and runs exact argv
without a shell. The canonical syntax and safety boundaries are in the
[environment snapshot guide](../guides/environment-snapshots.md).

`apgr analyze hotspots` requires an absolute physical repository root. It
walks beneath that root without following symlinks or executing target source,
then emits terminal, canonical JSON, or Markdown output. See the
[hotspot analysis guide](../guides/hotspot-analysis.md).

## Response capture

APG100 moves immutable response capture into the private Go response owner.
The terminal layout remains `<outbox>/<project>/<phase>/` with private
directories and `<phase>.<NNN>.response.md` files numbered `001..999`.
Capture preserves exact stdin or direct-file bytes up to 8 MiB, uses a bounded
phase lock, durable reservations and same-directory temporary writes, and
publishes by an atomic hard link so an existing destination is never replaced.
Concurrent writers receive distinct numbers. Unsafe links, ownership or inode
changes, exhaustion, interruption, and lock contention fail without partial
publication; a response already published is retained if later cleanup fails.

Python retains configuration and repository/project discovery, then delegates
`response capture` and its `response record` compatibility alias to Go. The
importable Python compatibility functions also invoke Go; no normal Python path
contains an independent response mutation implementation.

## Distribution

The target-specific binary manifest, Python wheels and source distribution,
npm launcher and platform packages, offline qualification, and unsupported
target behavior are documented in [APG Distribution](../distribution.md).
Prebuilt native binaries target macOS Apple Silicon (`darwin/arm64`), Linux x86_64
(`linux/amd64`), and Linux ARM64 (`linux/arm64`). Developer CI qualification
on Linux x86_64 remains pending; Darwin arm64 is fully qualified.
