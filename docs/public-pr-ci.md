# Public Staging PR CI Architecture and Operational Guide

<!-- APG-CANDIDATE-STATE: css-language-profile retained-provisional -->

The marker above is the mechanical current-state authority. Bounded
contradiction diagnostics cover only their frozen vocabulary; arbitrary prose
still requires human review.

## Purpose and scope

This document defines the continuous integration architecture, trust boundaries,
security controls, scanner inventory, and matrix completeness verification for
public pull requests targeting the canonical `main` branch of
`Knowledge-Forge-AI/agentic-praxis-grimoire`.

This unreleased preparation defines a future qualification gate for changes promoted from the
`staging` branch to `main`. It operates under strict public-only boundaries:
read-only credentials, unpersisted tokens, standard GitHub-hosted runners,
independently verified upstream action pins, Software Bill of Materials (SBOM) generation across source and deliverables,
vulnerability and code scanning, and explicit evidence accounting. Local defects
and pending finding dispositions block readiness; hosted acceptance is unobserved.

## Trust boundary and threat model

1. **Standard GitHub-hosted runners only**:
   Static, packaging, scanner, and CodeQL jobs execute on standard `ubuntu-latest`
   GitHub-hosted runners. The canonical APGR suite runs on standard `macos-15`
   arm64 because its qualified Node and browser inputs are Darwin-specific. No
   self-hosted runners, ephemeral private runners, or Tart VM orchestrators are used.

2. **Least privilege permissions**:
   - Workflow default permission is strictly read-only: `permissions: contents: read`.
   - `persist-credentials: false` is enforced across every `actions/checkout` invocation.
   - The CodeQL analysis job is the sole job granted elevated permissions
     (`permissions: { contents: read, security-events: write }`) required exclusively
     for SARIF upload to GitHub Advanced Security.
   - Publishing credentials, package registry tokens (PyPI, npm), and OIDC minting
     (`id-token: write`) are strictly forbidden in this workflow.

3. **Repository and branch guard**:
   The initial `guard` job enforces boundary preconditions before expensive matrix
   dispatch:
   - Target repository must match `Knowledge-Forge-AI/agentic-praxis-grimoire`.
   - Target repository ID must match `1306002537`.
   - PR base branch must be `main`.
   - PR head branch must be `staging`.
   - PR head repository must be identical to base repository (`Knowledge-Forge-AI/agentic-praxis-grimoire`).
     Forked pull requests and arbitrary feature branches are rejected.

4. **Concurrency and cancellation**:
   `concurrency: { group: public-pr-${{ github.event.pull_request.number || github.ref }}, cancel-in-progress: true }`
   ensures that outdated commits on an active pull request are cancelled immediately,
   preventing redundant resource consumption.

## Upstream action and tool pins

Every external GitHub Action is pinned to an exact 40-character commit SHA resolved
from official upstream repository tags and peeled commits. SHA identities are never
fabricated:

| Action | Tag / Version | Verified Commit SHA |
| --- | --- | --- |
| `actions/checkout` | v7.0.1 | `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| `actions/setup-python` | v7.0.0 | `5fda3b95a4ea91299a34e894583c3862153e4b97` |
| `actions/setup-go` | v7.0.0 | `b7ad1dad31e06c5925ef5d2fc7ad053ef454303e` |
| `actions/setup-node` | v6.5.0 | `249970729cb0ef3589644e2896645e5dc5ba9c38` |
| `actions/setup-java` | v5.7.0 | `b6effb05e454b25005698d916606bdc6ffcbf961` |
| `actions/upload-artifact` | v6.0.0 | `b7c566a772e6b6bfb58ed0dc250532a479d7789f` |
| `actions/download-artifact` | v4.1.8 | `fa0a91b85d4f404e444e00e005971372dc801d16` |
| `github/codeql-action/init` | v4.38.0 | `b96794f015dfd88f77b49b1c93e0fa7110f94c63` |
| `github/codeql-action/analyze` | v4.38.0 | `b96794f015dfd88f77b49b1c93e0fa7110f94c63` |

The canonical runtime job uses `cachix/install-nix-action` v31.11.1 at
`13d8dd58da0234aa297dedd986986ccb8e7f3e24`, selecting Nix 2.35.2.

The release publisher separately pins `pypa/gh-action-pypi-publish` to
`dc37677b2e1c63e2034f94d8a5b11f265b73ba33`; the retained Low advisory remains
visible pending a verified update.

The upload v6 / download v4 pairing uses the v4 artifact backend. Upload v6
changes the action runtime to Node 24; download v4 supports `pattern` and
`merge-multiple: false`, preserving one directory per receipt artifact.
This is supported by the pinned [upload documentation](https://github.com/actions/upload-artifact/blob/b7c566a772e6b6bfb58ed0dc250532a479d7789f/README.md)
and [download documentation](https://github.com/actions/download-artifact/blob/fa0a91b85d4f404e444e00e005971372dc801d16/README.md).
Hosted execution of this pairing remains pending.

Pinned native tools and SHA-256 archive hashes are managed in
[`tools/ci/pre_review_tools.json`](../tools/ci/pre_review_tools.json).

## Adapted compact APGR static runner

The static analysis suite is executed by [`tools/ci/run_pre_review.py`](../tools/ci/run_pre_review.py)
and covers twenty distinct mechanical and security checks. It strictly segregates
**tool failures** (missing interpreters, uninstalled binaries, operational crashes) from
**policy findings** (lint errors, unratcheted regressions, security findings):

1. `ruff`: Repository-wide Python linting across `src`, `libexec`, `tools`, `bin`, `src/test`.
2. `pyflakes`: Core runtime syntax and undefined-name checks via `ruff check --select F`.
3. `mypy`: Static type analysis against typed module manifest [`tools/ci/python_type_ownership.json`](../tools/ci/python_type_ownership.json).
4. `retained-python-ratchets`: Verification of module quality ratchets against [`tools/ci/retained_python_ratchets.json`](../tools/ci/retained_python_ratchets.json).
5. `python-retention-inventory`: Census verification of tracked Python modules and line counts.
6. `ci-topology`: Structural verification of GitHub Actions workflow triggers, permissions, and runner markers.
7. `python-compile`: Bytecode compilation across all Python sources via `compileall`.
8. `actionlint`: Syntax and expression checking of `.github/workflows/*.yml`.
9. `zizmor`: Security audit of GitHub Actions workflows in offline mode.
10. `pip-audit`: Known CVE vulnerability audit of three separate resolved
    inventories: the conditional Python 3.10 `tomli` runtime fallback, the
    maintained APGR test requirements, and the pinned CI tools. Each inventory
    is resolved with transitive dependencies; empty or malformed output and
    auditor failures block the lane.
11. `govulncheck`: Vulnerability audit of the Go codebase via
    `golang.org/x/vuln`; JSON findings are parsed even when the tool exits zero,
    and reachable symbol findings block.
12. `semgrep`: The installed Semgrep executable runs static analysis against
    repository-owned rules in [`tools/ci/semgrep.yml`](../tools/ci/semgrep.yml);
    module-wrapper deprecation warnings are not treated as a valid invocation.
13. `betterleaks`: Secret detection across the complete clean public source root;
   findings block until a separate, narrow review records an exception.
14. `malskanner`: Static inspection of repository instruction payloads for prompt injection; it does not establish complete natural-language safety.
15. `prompt-defense-audit`: Named injection-pattern and Unicode anomaly checks over `AGENTS.md` and `skills/**/SKILL.md`. Missing or unreadable inputs fail; pattern coverage is deliberately bounded.
16. `scanner-suppressions`: Inventory and drift audit of inline suppression comments (`# noqa`, `//nolint`, etc.).
17. `liquibase`: N/A while the repository has no owned migration or changelog surface; the inventory check refuses newly introduced undeclared surfaces.
18. `hadolint`: Dockerfile linting includes the concrete `hotspot/testdata/classification/Dockerfile` test fixture. It is not an operational image; findings remain visible and unwaived. Any introduced operational Dockerfile is also checked.
19. `generated-code-drift`: A disposable Go build invokes the maintained `apgr skills verify-corpus` owner, comparing exact metadata bytes and canonical body digests with embedded resources. Build failures are distinct from corpus mismatches.

The maintained `bin/apg-check-change-size` checker remains owned by the separate
`policy` job, where it evaluates the tested PR change scope through
`testing/apg-change-size-policy.json`. The static runner does not apply a copied
whole-history line-count baseline to inherited release evidence.

Missing applicable tools fail closed with classification `tool-failure`. No automatic
debt baseline is accepted by this lane, and mass reformatting is prohibited. Evidence logs are capped at 200 KB per check, sealed in
an evidence envelope (<= 5 MB total), and verified via SHA-256 manifest.

## Syft SBOM and Grype vulnerability policy

[`release/ci/sbom_policy.json`](../release/ci/sbom_policy.json) and [`release/ci/grype.yaml`](../release/ci/grype.yaml)
define software supply chain assurance:

- **Dual coverage**: Syft scans the exact public checkout and each built deliverable
  target, including Python distribution wheels/sdist and compiled native Go CLI
  binaries (`apgr-darwin-arm64`, `apgr-linux-amd64`, `apgr-linux-arm64`).
- **Coverage record**: The maintained scanner adapter consumes the exported
  distribution bundle, verifies its `SHA256SUMS`, and retains target/SBOM digests
  and cataloger coverage. An empty or unsupported package inventory is a blocker. The source distribution
  retains its raw scan and additionally uses an offline disposable installation
  through its maintained PEP 517 backend. A separate derived SBOM identifies the
  resulting Python metadata and native binary, bound to the original archive
  digest; metadata is not relabeled to satisfy a cataloger.
- **Vulnerability gating**: Grype consumes the exact Syft JSON documents. High
  and Critical unwaived findings block; lower severities and unfixed findings
  remain visible. Tool failures and stale, missing, or unverifiable vulnerability
  databases block. No blanket unfixed-vulnerability exemption is applied.
- **Exceptions**: Each exception needs an exact finding/package scope, reason,
  owner and expiry. Local scanner execution does not establish hosted acceptance.

## Advanced CodeQL configuration

CodeQL analysis runs across four matrix categories with compatible build modes:
- `go`: manual build mode (`go build ./cmd/apgr`), category `/language:go`
- `python`: build mode `none`, category `/language:python`
- `javascript-typescript`: build mode `none`, category `/language:javascript-typescript`
- `actions`: build mode `none`, category `/language:actions`

Alert merge protection requires zero high or critical alerts and zero analysis errors to
permit PR merge on GitHub.

> [!NOTE]
> **No hosted success claim**: Hosted GitHub Advanced Security check status, ruleset
> evaluation, and security alert merge protection require execution on GitHub infrastructure.
> Local verification proves configuration validity, schema compatibility, and matrix topology
> without asserting that hosted checks have passed.

## Canonical APGR suite and matrix completeness

The canonical test suite requires the exact qualified runtime declared in
[`testing/public-ci-runtime.json`](../testing/public-ci-runtime.json). On `macos-15`,
`tools/ci/bootstrap_runtime.py` materializes the root-owned Nix Node binding, verifies
the separately downloaded Node archive, installs the pinned Python/npm packages in a
task-owned root, provisions Playwright browsers there, and writes only job environment
bindings. It refuses missing tools, digest mismatches, symlinked bindings, and roots
inside the checkout. A generic `setup-node` binding is not a substitute.

Member jobs are wired to existing repository commands:
- `guard`: boundary and repository identity verification
- `static-analysis`: `tools/ci/run_pre_review.py`
- `policy`: `bin/apg-check-skill-library`, `bin/apg-check-record-identity`, `bin/apg-check-change-size`
- `unit-integration`: `bin/apg-test policy` followed by
  `bin/apg-test unit-integration --public-version 0.11.0` using the bootstrapped runtime. This explicit public mode uses the versioned release owner's six exact private-history deselections; public behavioral fixture companions run, and component/union thresholds remain unchanged
- `closure`: both normal and `--require-zero` roadmap-closure modes
- `go`: `go test ./...`, `go vet ./...`, `go test -race ./...`
- `package`: all three Go targets, the maintained Python and npm builders,
  `bin/apg-public-release manifest`, distribution-candidate build/check, and
  repeated Python/npm builds for reproducibility
- `sbom-and-vulnerability`: source and actual deliverable SBOMs, exact target records, and a
  separate Grype scan of each SBOM with database freshness and finding checks
- `codeql`: Advanced CodeQL matrix

Every completed member job attempts to emit an identity-bound receipt (`*-receipt.json`) with its actual
success, failure, cancellation, or skip status. Each CodeQL language has a distinct
SARIF filename and receipt identity. The terminal `public-pr-gate` job executes
`release/ci/matrix_receipts.py verify` with the explicit `needs.<job>.result` map to prove that:
- Every required member job executed and reported `status: success`.
- No member was skipped, cancelled, or failed.
- Receipts bind the tested merge candidate, PR head/base and workflow digest.
  Selected evidence accompanies its receipt with exact hashes. Missing or duplicate
  matrix artifacts fail; download directories are preserved before validation.

## Settings handoff record

Operational settings state at APG144 candidate handoff:
- `public_staging`: `not_started` (candidate qualified locally; drift observed: diverged remote staging branch e537cb22 exists with parent 9813a152, requiring reconciliation before attended staging)
- `public_pr_ci`: `not_run` (local readiness qualification complete; hosted PR CI unperformed)
- `public_release`: `not_started` (gated behind public PR CI qualification and v0.11 release authorization)
- `branch_protection`: `unconfigured` (empirically observed on 2026-09-13: 404 branch not protected, 0 rulesets)

The later operator must configure and read back a `main` ruleset requiring a PR,
at least one current approval with stale approvals dismissed, an up-to-date branch,
and the following exact required checks from GitHub Actions: `guard`,
`static-analysis`, `policy`, `unit-integration`, `closure`, `go`, `package`,
`sbom-and-vulnerability`, `codeql (go)`, `codeql (python)`,
`codeql (javascript-typescript)`, `codeql (actions)` and `public-pr-gate`.
Require CodeQL code-scanning merge protection at **High or higher** security
severity and **Errors** alert severity. Permit squash promotion only, with subject
`Release v0.11.0`; disallow force pushes and deletion of protected release history.
Verify public `main` still equals the accepted public base immediately before
merge. A moved base requires a newly bound candidate and qualification.

These settings have not been changed or verified. If the future operator lacks
ruleset or code-scanning permissions, the handoff is to an authorized repository
administrator; requirements must not be disabled. Uploaded SARIF and successful
workflow execution alone do not prove absence of CodeQL alerts.

The initial suppression census is retained as review evidence, not an accepted
waiver. Exact occurrences without an accepted reason, owner and unexpired review
remain blocking. The helper has no automatic baseline-update operation. Existing
Ruff/mypy findings remain attributable through their independent checker output;
no threshold or coverage exclusion was raised to qualify this preparation.

## Local evidence boundaries

Canonical component and union coverage measures `libexec/` and
`src/agentic_praxis_grimoire/`. It does not measure `tools/ci/` or `release/ci/`.
Their focused tests establish only the exercised CI contracts; no percentage
coverage or complete bootstrap execution is claimed for these owners. Missing
bootstrap and helper boundary tests remain qualification concerns.

The suppression inventory records observations, not approvals. Entries lacking
an accepted, specific, owned and unexpired decision deliberately block the
static lane. An observed baseline does not grandfather them. No second
baseline allowance overrides this decision check.

The enforced SBOM coverage policy is `scan.coverage`: source Go/npm inventories,
a separately bound conditional Python dependency receipt, and per-deliverable
package and embedded-binary coverage. Source scanning excludes Python bytecode
cache directories. Grype 0.118.0 maps threshold findings to exit 2 and other
errors to exit 1 in its [pinned CLI source](https://github.com/anchore/grype/blob/v0.118.0/cmd/grype/cli/cli.go);
both outcomes block, with distinct evidence classifications.

READINESS2 historically stopped on a missing-policy sentinel. READINESS3 adopts
[`tools/ci/file_length_policy.json`](../tools/ci/file_length_policy.json): LF-delimited
physical lines, warning above 400 and failure above 1,000. The shared tracked
Python inventory covers package source, libexec, tools, release/ci, tests and
Python-shebang entry scripts in bin. It records excluded artifact classes and
refuses missing, unreadable or empty inputs. The public prospective capture
tracks new candidate files before scanning; development HEAD alone is insufficient.

Eighteen existing oversized READINESS2 files have individual content-bound entry
allowances. Each remains visible retained debt; growth above its bound and new
unlisted oversized files fail. Allowances cannot transfer on removal or increase
automatically. Reviewed reductions may tighten bounds; retire an allowance once
its file falls to the ordinary limit. This is a no-growth migration, with no
promise or authorization of a later refactoring campaign.

Suppression result schema `apg-scanner-suppression-inventory-v3` uses Python
comment tokens and a hash of the owning statement and enclosing scope names.
Line numbers remain diagnostic. Movement alone preserves identity; changed
multiline imports, rules, context and occurrence multiplicity do not. Necessary
records require a concrete owner, reason, actual review reference and expiry.
READINESS3 proposals were formally approved in READINESS4 following independent pre-final
work-review verification under Manager Decision C; all 225 active directives have concrete
owners, reasons, and expiry 2026-12-31. Other formats use bounded quote-aware line-comment
recognition, not a general language parser.

BetterLeaks observations retain the raw count. Three manager-reviewed nonsecret
contexts are reconciled by exact path/rule/source-line/context hashes: two
synthetic redaction inputs and one public integrity digest. The aggregate reports
`reviewed_nonsecret`, unresolved observations and unmatched dispositions separately.
Changed or additional matches inherit no allowance. Full redaction remains enabled;
source bytes are hashed in memory and scanner payloads are not retained in logs.

The deliverable export copies Python wheels and sdist archives explicitly.
The Python builder's nested checksum index is not a distribution artifact;
including it would fail the scanner's exact manifest file-set check. The
export boundary is exercised through the actual shell copy block.

The READINESS3 lint adaptation preserves the exact APG140 support fixture
identified by its accepted support binding. Its two F401 observations remain
visible under an exact content-and-occurrence classification; changes to bytes,
rules or multiplicity do not inherit it. 145 targeted Ruff findings were corrected,
and all 225 active suppressions are formally approved under Decision C, qualifying the
static pre-review aggregate (exit=0 across all 20 checks).
