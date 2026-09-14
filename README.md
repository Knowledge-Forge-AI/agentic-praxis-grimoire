# Agentic Praxis Grimoire

<!-- APG-CANDIDATE-STATE: css-language-profile retained-provisional -->

## What is Agentic Praxis Grimoire?

Agentic Praxis Grimoire (APGR) is a provider-neutral toolkit and skill corpus
for bounded agent engineering. It provides coding-agent platforms, LLM
harnesses, and agentic workflows with deterministic primitives for selecting
task-scoped guidance, collecting immutable evidence, capturing curated
environments, inspecting repository structures, and measuring context footprints
without dictating an orchestration workflow.

This documentation covers the **unreleased v0.11.0 candidate**. It retains 45
canonical skills and adds closure governance, hotspot schema v2, report-key
support, and preparation for public staging PR validation. v0.10.0 remains the
published release across GitHub, Go, PyPI and npm; earlier releases stay frozen.
See the [candidate notes](release/v0.11.0-notes.md) and
[v0.11 closure roadmap](docs/v0-11-roadmap.md). Candidate preparation does not
establish hosted CI acceptance or publication.

APGR includes:

- **45 canonical agent skills** across 14 stable and 31 provisional leaves;
- **Context-footprint accounting** for measuring, comparing, and projecting
  context budgets across descriptions, bodies, and support material;
- **Reusable Go packages** for schemas, canonical reports, skill bundles,
  strict environment snapshots, structural hotspot analysis, and footprint
  accounting;
- **The `apgr` command-line interface** for direct terminal and script use;
- **Thin Python and npm distribution adapters** providing binary-backed
  compatibility without rewriting portable logic; and
- **Deterministic verification tooling** ensuring reproducible outputs and
  uncompromising safety boundaries.

### Who is APGR for?

- **AI Agent System Engineers**: Embed deterministic skills and context
  accounting directly into agent runtimes and harnesses.
- **Coding Agent Platform Teams**: Supply bounded, task-specific instructions
  to coding models rather than dumping exhaustive, token-heavy global prompts.
- **Tool and Harness Authors**: Leverage strict, allowlisted environment
  snapshots and structural hotspot analysis to prepare clean agent workspaces.
- **Auditors and Evaluators**: Verify exact, canonical operational records,
  evidence bundles, and cryptographic hashes.

### What APGR is not

APGR is an engineering toolkit, **not** an autonomous agent or orchestrator.
It does not:
- Select models, prompt templates, or inference providers;
- Make autonomous decisions about retries, task loops, or self-healing;
- Act as a background daemon or cloud service; or
- Execute arbitrary code or mutate system configuration outside caller-specified
  targets.

Orchestrators such as Joint Agentic Command Aegis (JACA) or custom agent
frameworks invoke APGR as an in-process library or CLI subprocess.

## Core capabilities

- **Task-scoped skill selection**: Resolve only the guidance relevant to the
  immediate task rather than injecting global instruction sets into every
  session.
- **Context-footprint accounting**: Measure exact byte and UTF-8 character sizes
  of prompts, skill bodies, and support documents with versioned
  `apg.context-footprint/v1` schemas; compare compatible records; and create
  source-bound projections with explicit fidelity and omission disclosure.
- **Deterministic evidence**: Produce canonical Show, Diff, and Operational
  records with stable domain-separated cryptographic digests.
- **Strict environment snapshots**: Capture allowlisted, non-secret environment
  variables and resolve isolated or overlay execution environments with recorded
  provenance.
- **Structural hotspot analysis**: Rank complex or structurally critical files
  before bounded refactoring while clearly separating deep metrics, structural
  metrics, and unavailable capabilities.
- **Portable Go core**: Portable logic is authored in standalone, dependency-free
  Go packages; Python and npm packages serve as thin, verified distribution
  front doors.

### Skill corpus and maturity

APGR v0.11.0 retains 45 canonical leaves: 14 stable and 31 provisional. Canonical Markdown
under `skills/` is the maintained body authority; embedded metadata and package
resources are verified projections of it:

- Corpus topology: **45 canonical / 45 catalog / 45 projections / 45
  discoverable**
- Maturity: **14 stable / 31 provisional**

## Quick start

v0.10.0 packages are published and can be installed from the supported
registries using the version-pinned commands in the
[upgrade guidance](#upgrade-guidance-and-release-status).

### Source checkout first

Run these commands from the root of your APGR source checkout:

```sh
go run ./cmd/apgr --version
go run ./cmd/apgr skills list
```

### Supported platforms and developer qualification gate

Prebuilt distribution runtime targets include:
- **macOS Apple Silicon**: `darwin/arm64`
- **Linux x86_64**: `linux/amd64` (`linux/x64`)
- **Linux ARM64**: `linux/arm64`

**Developer qualification gate status**: Darwin arm64 is fully qualified (APG114 / Exit `00159`).
The Linux developer qualification gate is currently pending: the `policy` suite is
pending runner qualification, and `unit`, `integration`, and `combined` (`unit-integration`)
suites are blocked by whole-inventory preflight binding Darwin arm64 Nix store digests.

### Prerequisites and dispatch boundaries

- **Core runtime commands**: `cmd/apgr` and the thin distribution wrappers execute
  the portable Go command families (`skills`, `footprint`, `env`, `analyze hotspots`,
  `report`, `response`).
- **Repository test runner**: Running `apgr test` (including `--summary-file` and the
  `policy` mechanical role) is a repository maintenance workflow requiring an APGR Git
  source checkout and the developer toolchain (Python 3.11+, pytest, coverage,
  pytest-cov, pytest-xdist, Git 2.40+, Go 1.25+).
- **Bare packages**: Prebuilt native binaries (`cmd/apgr`) and bare wheels / npm packages
  do **not** carry the test runner or test suites.

### First use

The examples below use a small source-checkout runner. Set `APGR_BIN` to an
installed native Go/npm executable when one is available; otherwise the helper
builds and runs the checkout's Go command. Each input file is absolute and
owner-only (`0600`) because the CLI treats the records as caller-owned data.

<!-- apgr-example: source-cli-skills -->

```sh
set -eu

apgr() {
  if [ -n "${APGR_BIN:-}" ]; then
    "$APGR_BIN" "$@"
  else
    go run ./cmd/apgr "$@"
  fi
}

apgr skills list
```

<!-- apgr-example: source-cli-hotspots -->

```sh
set -eu

apgr() {
  if [ -n "${APGR_BIN:-}" ]; then
    "$APGR_BIN" "$@"
  else
    go run ./cmd/apgr "$@"
  fi
}

apgr --repository "$PWD" analyze hotspots --include-path cmd/apgr
```

The Python frontend uses a different global root option for this command:
`apgr --project-root "$PWD" analyze hotspots --include-path cmd/apgr`.
The skills and footprint commands below use the same arguments on both frontends.

<!-- apgr-example: source-cli-footprint -->

```sh
set -eu

apgr() {
  if [ -n "${APGR_BIN:-}" ]; then
    "$APGR_BIN" "$@"
  else
    go run ./cmd/apgr "$@"
  fi
}

tmp_root="${TMPDIR:-/tmp}"
tmp_root="${tmp_root%/}"
workdir="$(mktemp -d "$tmp_root/apgr-readme.XXXXXX")"
workdir="$(cd "$workdir" && pwd -P)"
trap 'rm -rf "$workdir"' EXIT
request="$workdir/request.json"
treatment_request="$workdir/treatment-request.json"
control="$workdir/control.json"
treatment="$workdir/treatment.json"
comparison="$workdir/comparison.json"
projection="$workdir/projection.json"

python3 - "$request" "$treatment_request" <<'PY'
import json
import pathlib
import sys

base = {
    "schema_version": "apg.context-footprint/v1",
    "observation": {
        "harness": "cli",
        "method": "direct",
        "provider": "local",
        "quality": "verified",
        "repetitions": 1,
        "study_design": "single_run",
        "tokenizer": "none",
        "variant": "first-use",
        "workload": "skill-body",
        "availability": "available",
        "basis": "direct_measurement",
    },
    "components": [{
        "kind": "selected_body",
        "name": "implementing-with-test-discipline",
        "unit": "bytes",
        "text": "Write a failing test before writing production code.\n",
    }],
    "sensitivity": "public",
    "retention": "ephemeral",
}
treatment = json.loads(json.dumps(base))
treatment["components"][0]["text"] += "Keep the test focused.\n"
for path, value in zip(sys.argv[1:], (base, treatment)):
    pathlib.Path(path).write_text(json.dumps(value) + "\n", encoding="utf-8")
PY
chmod 600 "$request" "$treatment_request"

apgr footprint measure --input "$request" > "$control"
apgr footprint measure --input "$treatment_request" > "$treatment"
chmod 600 "$control" "$treatment"
apgr footprint compare --control "$control" --treatment "$treatment" > "$comparison"
apgr footprint project --source "$treatment" --fidelity exact > "$projection"
chmod 600 "$comparison" "$projection"

python3 - "$control" "$comparison" "$projection" <<'PY'
import json
import pathlib
import sys

control, comparison, projection = (json.loads(pathlib.Path(p).read_text()) for p in sys.argv[1:])
assert control["schema_version"] == "apg.context-footprint/v1"
assert comparison["schema_version"] == "apg.context-comparison/v1"
assert comparison["delta"] > 0
assert projection["schema_version"] == "apg.context-projection/v1"
assert projection["fidelity"] == "exact"
assert projection["omitted_fields"] == []
print("footprint measure, compare, and project examples passed")
PY
```

## Context-footprint walkthrough

The `footprint` subsystem enables principled, reproducible accounting of agent
context budgets. It treats context as a scarce, measurable resource with distinct
components and explicitly tracks unavailable metrics rather than reporting
misleading zeroes.

Key principles of context accounting:
- **Source-bound observations, not capacity forecasts**: Footprints record explicit
  measurements and source-bound projections, not predictive capacity models or
  exhaustion guarantees.
- **Unavailable is not zero (`unavailable != 0`)**: Bytes and UTF-8 characters
  are measured locally. Provider-specific token estimates remain explicitly marked
  as unavailable with stated reasons and nil values unless an observed value is
  supplied by the caller. An available zero is a measured fact; an unavailable
  metric is an unmeasured boundary.
- **Component separation (overlap is not additive)**: Selected descriptions, selected
  bodies, support material, repository references, and provider prompt overhead are
  measured as distinct components. Because prompt templates and harnesses overlap in
  structure, component metrics cannot be naïvely summed across boundaries without accounting.

### 1. Measure (`apgr footprint measure`)

Measure converts a strict measurement request into a validated `apg.context-footprint/v1`
canonical record with exact byte and character metrics. It accepts `--stdin` or `--input FILE`
(requiring an absolute, clean, owner-only `0600` file):

The marked [first-use fence](#first-use) above is the executable owner for
this walkthrough. It creates complete disposable fixtures, runs all three
footprint actions, and asserts the schema, positive comparison delta, exact
projection fidelity, and empty omission disclosure.

### 2. Compare (`apgr footprint compare`)

Compare computes treatment-minus-control deltas between two context footprint
records using the `apg.context-comparison/v1` schema. Both records must be
clean, owner-only `0600` files with matching observation dimensions:

The same executable fence runs `footprint compare` with absolute `0600`
records and checks the canonical comparison output.

Comparison outputs highlight:
- Net byte and character changes per component;
- Added or removed components; and
- Deterministic comparison digests (`cmp-sha256:...`).

### 3. Project (`apgr footprint project`)

Project creates a bounded, source-bound canonical projection retaining source
identity, fidelity level, and explicit omission disclosure using the
`apg.context-projection/v1` schema:

The same executable fence runs `footprint project` with an exact fidelity
request and checks the source-bound projection fields. A projection records
fidelity and omitted fields; it is not a capacity estimate or an exhaustion
control.

Projection discloses structural fidelity and omitted fields; it creates a
deterministic, source-bound representation rather than a capacity estimate.

## Go library integration

APGR is designed to be imported directly into Go applications and orchestration
adapters.

<!-- apgr-example: go-library -->

```go
package main

import (
	"context"
	"fmt"
	"log"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/footprint"
	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/skills"
)

func main() {
	ctx := context.Background()

	// Deterministically resolve a curated skill bundle
	req := skills.BundleRequest{
		SchemaVersion:    skills.BundleRequestSchemaV1,
		ExplicitSkillIDs: []string{"implementing-with-test-discipline"},
		Consumer: skills.Consumer{
			Kind:                skills.ConsumerGo,
			MaterializationForm: skills.MaterializationInMemory,
			ProviderConstraints: []string{"in_process_library"},
		},
	}
	result, err := skills.Resolve(ctx, req)
	if err != nil {
		log.Fatalf("failed to resolve skills: %v", err)
	}

	// Calculate its deterministic context footprint record
	record, err := skills.Footprint(req, result)
	if err != nil {
		log.Fatalf("failed to calculate footprint: %v", err)
	}

	fmt.Printf("Resolved %d skills; footprint components: %d\n",
		len(result.SelectedSkillIDs), len(record.Components))

	// Create a source-bound projection with fidelity and omission disclosure
	proj, err := footprint.Project(ctx, footprint.ProjectRequest{
		Source:   record,
		Fidelity: footprint.FidelityLosslessStructural,
	})
	if err != nil {
		log.Fatalf("failed to project footprint: %v", err)
	}

	fmt.Printf("Projected fidelity: %s; canonical digest: %s\n",
		proj.Fidelity, proj.CanonicalSourceDigest)
}
```

See the [Go library reference](docs/reference/go-library.md) for full package
documentation.

### JACA XO compatibility pattern

Downstream Go consumers (such as the Joint Agentic Command Aegis Executive Orchestrator,
JACA XO) consume `skills`, `footprint`, and supporting `schema` behind a caller-owned
internal adapter, as modeled in `testing/fixtures/xo_consumer/`:

- **Caller DTO containment**: External callers define their own data transfer objects
  (`CallerSkillEvidence`, `CallerFootprintEvidence`, `CallerComponentEvidence`,
  `CallerSourceReference`, `CallerComparisonDelta`, `CallerProjectionEvidence`). The
  internal adapter translates between APGR domain types and caller DTOs, ensuring
  zero APGR types leak into caller method signatures or public struct fields.
- **Pure in-memory execution**: Execution requires no subprocess invocation (`os/exec`)
  or network calls.
- **Context propagation & error sentinels**: Cancelled contexts return `ctx.Err()`
  or wrap `footprint.ErrContextCancelled`, while domain errors retain documented sentinels
  (`footprint.ErrUnitMismatch`, `footprint.ErrConsequenceBearingOmissionRefused`,
  `skills.ErrBudgetExceeded`).
- **Dual-lane verification**: Qualified across Lane A (published v0.8.1 baseline via Go proxy)
  and Lane B (exact source under qualification via local replace).

> [!IMPORTANT]
> **Separation of Authority**:
> - **APGR-local conformance != JACA registration**: APGR-local qualification is completed
>   on Darwin arm64 under APG114, but runner registration in JACA CI (`tools/ci/evidence.go`)
>   is consumer-owned and pending.
> - **XO fixture != production adapter or security proof**: The caller-owned adapter
>   fixture in `testing/fixtures/xo_consumer/` qualifies APGR Go package compatibility,
>   but is not JACA's production adapter (which belongs in `xo/src/main/go`), and passive DTOs
>   are not a workflow security proof.

### v0.9 CI qualification summary interface

For CI pipelines qualifying APGR from a Git source checkout with the developer toolchain,
`apgr test <suite> --summary-file <path>` emits strict 6-field machine-readable JSON:

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

Suites include `policy` (mechanical repository and corpus checks), `unit`, `integration`,
and `unit-integration` (`combined`). Note that `apgr test` requires an APGR Git checkout
and developer toolchain; bare wheel/npm native packages do not carry the full runner.
`combined` is the receipt suite name, and `apg-dev-gate` is a JACA role alias;
pass `unit-integration` to the CLI. The synthetic commit above illustrates the
shape: real receipts bind entry HEAD, with a separate inventory needed for
uncommitted tested bytes. See the [CI handoff](docs/architecture/jaca-ci-handoff.md)
for pinned test, Node, and TypeScript prerequisites. An installed Python frontend
can dispatch through that checkout; the native/npm binary cannot run `test`.

## Upgrade guidance and release status

### Preparing v0.11.0

v0.11.0 is unreleased. Exercise candidate features from a source checkout or
locally qualified wheel/npm artifacts; registry installation commands below
refer to the published predecessor. The release route is public `staging` →
pull request → squash merge to `main` → release. See the
[release procedure](docs/public-release-process.md). Local preparation does not
mean a public PR has run or that branch protection is configured.

### Upgrading to v0.10.0

The published v0.10.0 release adds six frontend profiles,
report verification and qualification maintenance; see the
[v0.10.0 release notes](release/v0.10.0-notes.md). The CI-first qualification
interface (`--summary-file`, `policy` role) and Go consumer interfaces remain.

Install the published v0.10.0 packages with these commands:

- **Go consumers**: Require `github.com/Knowledge-Forge-AI/agentic-praxis-grimoire v0.10.0`
  or run `go get github.com/Knowledge-Forge-AI/agentic-praxis-grimoire@v0.10.0`.
  Public APIs in `schema`, `report`, `skills`, `envsnap`, `hotspot`, and `footprint`
  preserve v0.8.1 compatibility.
- **Python users**: `pip install agentic-praxis-grimoire==0.10.0`.
- **npm users**: `npm install -g @knowledge-forge-ai/apgr@0.10.0`.

APGR-side JACA CI/XO compatibility work is complete. Actual JACA adoption and
activation remain JACA-owned. Linux runtime execution is separate from Darwin
qualification. Theme Forge and Repo Map remain separate roadmap scope.

### Preserved predecessor: v0.8.1

The **v0.8.1** release is the frozen predecessor across Git, GitHub Releases, PyPI,
npm, and the Go module proxy:
- Public Git commit: `565f924aa8fda9551da8732cceb5708db069e127`
- Public Git tree: `1ec7a01ca252a63cc869caf4e5bbe152fb6d2868`
- Annotated tag: `b6b3e996536ac89e1a58912caf3b3cb9c251dbd7`

Historical `v0.8.0` is preserved as immutable predecessor state. For technical details,
see the [v0.8.1 release notes](release/v0.8.1-notes.md) and
[v0.9.0 release notes](release/v0.9.0-notes.md).

## Security and trust boundaries

APGR is engineered with strict operational boundaries:

- **Explicit Process Boundaries**: Core subprocess adapters execute binaries with
  argument vectors. Public CI uses maintained shell scripts in disposable jobs.
- **Secret-Rejecting Environment Snapshots**: Environment profiles enforce strict
  allowlists. Secret-like variables (containing tokens, keys, passwords, or
  credentials) are rejected fail-closed.
- **Filesystem Isolation**: Materialized skill bundles and scratch operations are
  confined to caller-owned, disposable directories. APGR never mutates user-global
  skill roots or configuration without explicit flags.
- **Local Core Operations**: Report, skill, environment and hotspot operations
  use local inputs without telemetry. CI provisioning and vulnerability database
  refresh use declared public network endpoints.
- **Reproducible Builds**: All distribution archives, Go binaries, and package
  manifests are bit-for-bit reproducible under fixed release epochs.

## Documentation index

- [Task-Oriented Documentation Index](docs/README.md)
- [CLI Reference](docs/reference/cli.md)
- [Go Library Reference](docs/reference/go-library.md)
- [Skill Context Bundles Guide](docs/guides/skill-context-bundles.md)
- [Environment Snapshots Guide](docs/guides/environment-snapshots.md)
- [Hotspot Analysis Guide](docs/guides/hotspot-analysis.md)
- [Distribution and Packaging](docs/distribution.md)
- [APG–JACA Integration Architecture](docs/architecture/apg-jaca-integration.md)
- [JACA CI Integration Handoff](docs/architecture/jaca-ci-handoff.md)
- [JACA XO Compatibility Handoff](docs/architecture/jaca-xo-handoff.md)
- [Context Footprint & Skill Inventory](docs/architecture/v0-8-context-footprint-and-skill-inventory.md)
- [v0.10 Roadmap](docs/v0-10-roadmap.md)
- [Repo Map Support Roadmap](docs/repo-map-support-roadmap.md)
- [v0.9 Roadmap](docs/v0-9-roadmap.md)
- [Project Model & Governance](docs/project-model.md)
- [Provenance Policy](docs/provenance.md)
- [Status and Exit Records](docs/status/README.md)
- [Release Notes (v0.10.0)](release/v0.10.0-notes.md)
- [Release Notes (v0.9.0)](release/v0.9.0-notes.md)
- [Release Notes (v0.8.1)](release/v0.8.1-notes.md)

## Contributing and licensing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting contributions.
Contributions require adherence to the project contribution terms in
[CLA.md](CLA.md).

Agentic Praxis Grimoire is free software licensed under the
**GNU Affero General Public License v3.0 or later** ([AGPL-3.0-or-later](LICENSE)).
Commercial licensing options and enterprise support are available from the
Project Steward at [Knowledge Forge AI](https://www.knowledge-forge.ai).

Third-party copyright notices and attributions are recorded in [NOTICE](NOTICE).

## Qualification limitations

JS-QD-005 remains active under the condition-triggered refresh policy in
[ADR 0054](docs/adr/2026/09/0054-js-qd-005-refresh-trigger-interpretation.md).
The [Repo Map support roadmap](docs/repo-map-support-roadmap.md)
is a v0.10.0 deliverable with RM-S0 through RM-S5 intact.

The release retains these limits:

- **Skill corpus and maturity**: 45 canonical leaves across 14 stable and 31 provisional
  profiles, under the 11,507-byte discovery integrity ceiling.
- **Frontend profile qualification**: Desktop browser execution does not qualify the
  Tauri embedded WebView, native host, sidecars, or assistive technology.
- **Platform qualification gate**: v0.11 requires fresh candidate evidence on
  macOS Apple Silicon (`darwin/arm64`); prior release results are not inherited.
  Linux cross-build and archive inspection remain separate from Linux execution.
  Prepared hosted jobs do not establish hosted runtime qualification.
- **Process execution guard**: Static function and process checks verify named source files
  and bindings; dynamic metaprogramming and reflection require manual source review.
- **Report verification**: Report verification guarantees artifact-local integrity up to
  128 MiB; it does not attest to external Git states or operational truth.
