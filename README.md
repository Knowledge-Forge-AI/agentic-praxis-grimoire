# Agentic Praxis Grimoire

<!-- APG-CANDIDATE-STATE: css-language-profile retained-provisional -->

## What is Agentic Praxis Grimoire?

Agentic Praxis Grimoire (APGR) is a provider-neutral toolkit and skill corpus
for bounded agent engineering. It provides coding-agent platforms, LLM
harnesses, and agentic workflows with deterministic primitives for selecting
task-scoped guidance, collecting immutable evidence, capturing curated
environments, inspecting repository structures, and measuring context footprints
without dictating an orchestration workflow.

APGR includes:

- **39 canonical agent skills** across 14 stable and 25 provisional leaves;
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

APG has 39 canonical leaves: 14 stable and 25 provisional. Canonical Markdown
under `skills/` is the maintained body authority; embedded metadata and package
resources are verified projections of it:

- Corpus topology: **39 canonical / 39 catalog / 39 projections / 39
  discoverable**
- Maturity: **14 stable / 25 provisional**

## Quick start

The public release remains **v0.8.0** on Git and the Go module proxy. GitHub
Releases, PyPI, and npm do not contain v0.8.1. This documentation covers the
prepared v0.8.1 source candidate; it is not a publication claim.

### Source checkout first

Run these commands from the physical root of your prepared v0.8.1 source
checkout. A fresh public clone currently retrieves the v0.8.0 release line,
not this unpublished candidate:

```sh
go run ./cmd/apgr --version
go run ./cmd/apgr skills list
```

The prepared source candidate is pending the separate source-freeze and
production qualification boundary. Do not use an unpublished registry version
as a dependency or claim that these commands prove publication.

### Supported platforms

The prepared distribution targets include:
- **macOS Apple Silicon**: `darwin/arm64`
- **Linux x86_64**: `linux/amd64` (`linux/x64`)
- **Linux ARM64**: `linux/arm64`

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

### 1. Measure (`apgr footprint measure`)

Measure converts a strict measurement request into a validated `apg.context-footprint/v1`
canonical record with exact byte and character metrics. It accepts `--stdin` or `--input FILE`
(requiring an absolute, clean, owner-only `0600` file):

The marked [first-use fence](#first-use) above is the executable owner for
this walkthrough. It creates complete disposable fixtures, runs all three
footprint actions, and asserts the schema, positive comparison delta, exact
projection fidelity, and empty omission disclosure.

Key principles of measurement:
- **Separation of components**: Selected descriptions, selected bodies, support
  material, repository references, and provider prompt overhead are measured as
  distinct components.
- **Honest metrics**: Bytes and UTF-8 characters are measured locally.
  Provider-specific token estimates are marked explicitly as unavailable unless
  an observed value is provided by the caller.

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

## Upgrade guidance and release recovery

### Upgrading from v0.7.0 to the prepared v0.8.1 source

The v0.8 series introduces the complete context-footprint subsystem (`footprint`
Go package introduced in v0.8.0 and `apgr footprint` CLI command family), refined
skill metadata, and multi-surface distribution packages with packaged
documentation and rich project metadata.

- **Go Consumers**: Keep released consumers on the exact published version they
  already qualify. To exercise the prepared source, use a checkout-local Go
  module and the source-build path above; do not add an unpublished `v0.8.1`
  requirement.
- **CLI / Python / npm Users**: Use the source-checkout command while v0.8.1
  remains pending freeze and publication. Registry installation is deferred.

### Truthful v0.8.0 release status & v0.8.1 recovery

During the initial publication of v0.8.0 on 2026-08-31:
- Git commit `fc0fd99b41d24951d7db3535402c46ef9c671143` was pushed to `main`;
- Annotated tag `v0.8.0` was pushed; and
- The Go module proxy (`proxy.golang.org`) successfully indexed and authenticated
  `v0.8.0`.

However, downstream publication to GitHub Releases, PyPI, and npm was not completed
due to credential and interactive TTY requirements. In strict adherence to
public-registry immutability and zero-overwrite policies:
- The immutable `v0.8.0` tag and Go proxy entries are preserved as historical
  immutable predecessor state without force-pushing, retagging, or deletion.
- **v0.8.1** is a prepared multi-surface recovery candidate pending source freeze
  and publication. It is not published to GitHub Releases, PyPI, or npm, and no
  release page, package install, or module requirement should imply otherwise.

For technical details, see the [v0.8.1 release notes](release/v0.8.1-notes.md)
and [qualification exit record](docs/status/2026/09/03/00154-apg107-108-v081-qualification-and-recovery-exit.md).

## Security and trust boundaries

APGR is engineered with strict operational boundaries:

- **No Shell Execution**: Subprocess adapters execute binaries directly using
  exact argument vectors (`execve`), never passing strings through a shell.
- **Secret-Rejecting Environment Snapshots**: Environment profiles enforce strict
  allowlists. Secret-like variables (containing tokens, keys, passwords, or
  credentials) are rejected fail-closed.
- **Filesystem Isolation**: Materialized skill bundles and scratch operations are
  confined to caller-owned, disposable directories. APGR never mutates user-global
  skill roots or configuration without explicit flags.
- **Zero Telemetry / Offline Operation**: All local commands operate completely
  offline with no telemetry, tracking, or unexpected network requests.
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
- [Context Footprint & Skill Inventory](docs/architecture/v0-8-context-footprint-and-skill-inventory.md)
- [Project Model & Governance](docs/project-model.md)
- [Provenance Policy](docs/provenance.md)
- [Status and Exit Records](docs/status/README.md)
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
