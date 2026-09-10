# APG123/APG125 synthetic browser qualification

These APGR-owned fixtures contain no consumer artwork or private browser state.
The maintained register defines 38 cases: the original 24 (10 runner mechanics,
11 accessibility observations and 3 SVG resources) plus 14 APG125 browser-runtime
cases. Each executes in Chromium, Firefox and
WebKit from exact Playwright Test 1.62.1. Retries are disabled.

## Reproduction

Use the repository's qualified Node prerequisite and Python test environment.
Create a caller-owned mode-0700 external scratch root through the shared scratch
workflow. Copy `package.json` and `package-lock.json` into a child package directory
there; run `npm ci --ignore-scripts --no-audit --no-fund` with an owned npm cache.
The test-only Apache-2.0 Playwright packages and their installed notices remain
in scratch; optional platform dependencies retain their own notices.

Set these explicit environment inputs:

- `APG_JAVASCRIPT_NODE`: qualified Node executable under the existing Node contract.
- `APG_PLAYWRIGHT_OWNED_SCRATCH_ROOT`: the private external scratch directory.
- `APG_PLAYWRIGHT_PACKAGE_ROOT`: its child containing the exact `node_modules`.
- `PLAYWRIGHT_BROWSERS_PATH`: an existing cache used read-only, or a separate
  owned scratch cache when authorized browser downloads are required.

Never run an install against the global cache. A missing engine is a failed
prerequisite until installed in owned scratch; a branded channel is not a substitute.
Other canonical combined-runner prerequisites remain unchanged.

Run the two profile integration entrypoints through the maintained pytest runner.
The Playwright entrypoint preserves its 39 runner/SVG combinations; accessibility's
entrypoint preserves its 33 combinations. The browser support integration entrypoint
runs `apg123` (72) and `browser_runtime` (42) separately; `all` selects all 114. The combined runner invokes
both entrypoints after fail-closed package/cache validation. Unit tests verify
navigation/register and adverse prerequisite/receipt contracts separately.

`apg123_browser_ui.execute_browser_harness` copies fixtures into a unique owned
run directory, starts two ephemeral loopback servers and launches independent browser contexts.
`runner.mjs` invokes the selected library and actual Playwright Test supervisor
runs. The latter inspect controlled pass/failure artifacts and issue SIGINT only
after the child has loaded the fixture and signaled readiness.

## Policy and limitations

Only fixed synthetic loopback files and endpoints are served. Context routing
blocks other origins/paths before pages are created, except the BR06 CSP-contained
preflight lane described below. Service workers are blocked. Foreign SVG
use may be rejected by browser policy before routing. Its blank rendered result
and separate refused fetch probe are distinct observations. The permitted SVG
case uses inline document processing, not secure static image mode.

Screenshots and traces are synthetic, checked on disk before cleanup, and removed
with the run directory by default. A receipt's artifact names describe artifacts
observed during execution; `retained_on_disk` states whether they remain.
No cookies/auth-state files or real profiles are retained. Explicit keep-scratch
is for bounded synthetic evidence only and requires later owned cleanup.

Same-run screenshots prove controlled equality/difference on each engine/platform,
not portable golden baselines. Focus pixel differences do not establish contrast
ratios. Semantic snapshots are not a screen reader; these tests make no WCAG
conformance or real assistive-technology announcement claim.

## Browser-runtime evidence boundaries

BR06 observes actual CORS/preflight requests on the second loopback server.
Interception can suppress native preflight, so this one synthetic page installs a
restrictive CSP before removing interception. Only four exact loopback Fetch
endpoints are connectable; a valid fifth local endpoint is refused with no server
request as the negative control. This is a bounded meta-CSP/connect-src predicate,
not general CSP conformance or OS network isolation. Other lanes retain routing.
Server evidence contains method/path/header names and synthetic-cookie booleans,
never header or cookie values. Worker/module cases require actual server receipts.

BR07 uses an already-aborted default-reason signal; it does not qualify in-flight
server rollback or every custom abort reason. Worker termination checks bounded
post-termination message absence; it does not measure process memory reclamation.
Service workers remain blocked and unqualified. Desktop browser engines do not
qualify an actual embedded WebView or a Tauri native host.

## Browser family table and fail-closed hardening

Family and authority classification are governed by `family_table.json` (`schema_version: "1.0.0"`, `authority: "APG129-BROWSER-FAMILY-TABLE"`). This replaces independent prefix or group heuristics (`startsWith('PW')`, `startsWith('BR')`, etc.) with a single versioned authoritative table consumed by both the JavaScript runner (`runner.mjs`) and Python harness support (`apg123_browser_ui.py`).

### Preserved identities and CLI aliases

The family table binds the 38 frozen scenario identities to their canonical group and family:
- **`apg123` family**: 10 Playwright scenarios (`PW01`-`PW10`, group: `playwright`), 11 accessibility scenarios (`AX01`-`AX11`, group: `accessibility`), and 3 SVG scenarios (`SVG01`-`SVG03`, group: `svg`).
- **`apg125` family**: 14 browser runtime scenarios (`BR01`-`BR14`, group: `browser_runtime`).

It maintains seven CLI alias selections:
- `all`: All 38 scenarios.
- `apg123`: All 24 APG123 scenarios (`PW01`-`PW10`, `AX01`-`AX11`, `SVG01`-`SVG03`).
- `browser_runtime` / `browser-runtime`: All 14 APG125 runtime scenarios (`BR01`-`BR14`).
- `playwright`: The 10 Playwright core scenarios (`PW01`-`PW10`).
- `accessibility`: The 11 accessibility scenarios (`AX01`-`AX11`).
- `svg`: The 3 SVG resource scenarios (`SVG01`-`SVG03`).

### Pre-execution authority resolution

Authority is deterministically resolved once before starting loopback servers or launching browsers:
- Pure APG123 selection resolves to `APG123-BROWSER-UI-QUALIFIED-RECEIPT`.
- Pure APG125 selection resolves to `APG125-BROWSER-RUNTIME-QUALIFIED-RECEIPT`.
- Explicit supported mix (both APG123 and APG125 scenarios) resolves to `APG125-BROWSER-MIXED-QUALIFIED-RECEIPT`.

The pre-resolved authority is reused across both successful execution and failure receipt paths.

### Fail-closed validation boundaries

Both consumers enforce strict fail-closed validation:
1. **Schema versioning**: Any table `schema_version` other than `"1.0.0"` is refused.
2. **Duplicates**: Duplicate scenario IDs in table entries, aliases, CLI scenario filters, or target selections are refused.
3. **Ambiguity**: Conflicting group or family mappings for any scenario ID are refused.
4. **Unknown identity / group / pair**: Unknown scenario IDs, unknown groups, or mismatched `(id, group)` pairings are refused.
5. **Unsupported mixes**: Unsupported family combinations are refused.
6. **Table vs register agreement**: The family table and scenarios register (`scenarios.json`) must agree on all scenario IDs and group assignments. Any disagreement refuses execution before any browser or server is started, exiting with code 1 and writing NO receipt file.

### Receipt hash binding

Every generated receipt binds SHA-256 digests for:
- `runner_sha256`: Digest of `runner.mjs`.
- `register_sha256`: Digest of `scenarios.json`.
- `table_sha256`: Digest of `family_table.json`.

These digests are recorded under `runtime` and `manifests`, and schema metadata is recorded under `table` and `register`. Python receipt validation verifies these digest formats, validates all recorded `(scenario_id, group)` pairs against the family table, and validates expected selection completeness.
