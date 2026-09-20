# Agent-Central Ownership Transition Handoff (v0.12)

- Status: **Proposed** — APGR-side decision recorded; delivered unaccepted for Agent-Central team disposition
- Target Version: APGR v0.12 / Agent-Central Evolution
- Inspected Pinned Baseline: Agent-Central `56e9bb039536dfc8893e61a431681d6a32167b6f` (verified present; working tree clean and unmodified by this phase)
- Governing Decisions: ADR 0058, ADR 0061

## Status and authority

This document has **no** authority over Agent-Central. It records APGR's own
ownership decision and offers coordination guidance. Nothing here has been
reviewed or accepted by the Agent-Central team, APGR mutates nothing in that
repository, and every recommendation below is declinable.

## Overview

This document provides guidance and coordination details for the Agent-Central team regarding the transition of the single-phase execution runtime into APGR. It outlines the proposed staged migration schedule, offers recommended compatibility wrappers to preserve existing operator habits, and clarifies the architectural boundary between phase dispatch and Agent-Central's local interactive worker tooling.

---

## 1. Staged Transfer Schedule

The transfer is structured across APGR v0.12 milestones to minimize operational disruption:

```text
+-------------------+---------------------------------------------------------+
| Milestone         | Transition Activities & Agent-Central Impact            |
+-------------------+---------------------------------------------------------+
| V0120-A           | - Architectural formalization & inventory freeze        |
| (Current)         | - No code modifications in either repository            |
+-------------------+---------------------------------------------------------+
| V0120-B           | - Direct migration of libexec/agent_phase/ to APGR     |
|                   | - Route tables & profiles migrated to APGR              |
|                   | - 100% Request V1 parity verified in APGR               |
+-------------------+---------------------------------------------------------+
| V0120-C           | - Request V2 and SQLite state implemented in APGR       |
|                   | - Initial testing of compatibility forwarding in AC     |
+-------------------+---------------------------------------------------------+
| V0120-D           | - Provider capability normalization in APGR             |
|                   | - Bounded dynamic router available in APGR              |
+-------------------+---------------------------------------------------------+
| V0120-E           | - Go surfaces exported; JACA qualified against APGR     |
|                   | - Recommended deprecation of prototype dispatch in AC   |
+-------------------+---------------------------------------------------------+
```

---

## 2. Recommended Agent-Central Compatibility Forwarding

To ensure that existing operational scripts, dispatcher aliases, and muscle memory remain functional without interruption, we recommend that the Agent-Central team replace `bin/agent-phase-dispatch` with a lightweight forwarding wrapper pointing to APGR's native launcher once stage `V0120-B` is operational.

### Native APGR Dispatcher Entrypoint
In APGR `V0120-B`, the single-phase execution dispatcher is installed directly as native standalone executable wrappers in APGR's `bin/`:
- `bin/agent-phase-dispatch` (invokes `libexec/controller_generation_bootstrap.py dispatch`, preserving exact generation-isolation and cutover mechanics)
- `bin/agent-phase-resolve` (phase route resolution)
- `bin/agent-phase-archive` (run artifact packaging)
- `bin/agent-phase-finalize` (safe Git finalization)
- `bin/agent-phase-native-git` (native Git command authorization)
- `bin/agent-phase-ownership` (ownership challenge disposition)
- `bin/agent-phase-adopt` / `bin/agent-phase-adopt-entry` (candidate adoption)
- `bin/agent-phase-scan-label` / `bin/agent-phase-scan-summary` (prompt telemetry labeling)

### Concrete Wrapper Shape (`bin/agent-phase-dispatch` in Agent-Central)
```bash
#!/usr/bin/env bash
# Agent-Central compatibility wrapper forwarding to native APGR dispatcher.
set -euo pipefail

SELF_REALPATH="$(python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$0" 2>/dev/null || readlink -f "$0" 2>/dev/null || echo "$0")"

# Prefer explicit APGR_ROOT environment variable, then standard candidate locations
APGR_CANDIDATES=(
    "${APGR_ROOT:-}"
    "${HOME}/projs/agentic-praxis-grimoire_dev"
    "${HOME}/projs/apg/agentic-praxis-grimoire_dev"
)

for candidate in "${APGR_CANDIDATES[@]}"; do
    if [[ -n "${candidate}" && -x "${candidate}/bin/agent-phase-dispatch" ]]; then
        TARGET_REALPATH="$(python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "${candidate}/bin/agent-phase-dispatch" 2>/dev/null || echo "")"
        if [[ "${SELF_REALPATH}" != "${TARGET_REALPATH}" ]]; then
            exec "${candidate}/bin/agent-phase-dispatch" "$@"
        fi
    fi
done

# Fallback to PATH lookup with recursion prevention
if command -v agent-phase-dispatch >/dev/null 2>&1; then
    TARGET_REALPATH="$(python3 -c 'import os, sys, shutil; p = shutil.which(sys.argv[1]); print(os.path.realpath(p) if p else "")' "agent-phase-dispatch" 2>/dev/null || echo "")"
    if [[ "${SELF_REALPATH}" != "${TARGET_REALPATH}" && -n "${TARGET_REALPATH}" ]]; then
        exec agent-phase-dispatch "$@"
    fi
fi

echo "Error: Native APGR agent-phase-dispatch executable not found or resolves recursively to this wrapper. Set APGR_ROOT to the APGR repository root." >&2
exit 127
```

### Configuration and Route Discovery
In APGR, route tables and model endpoints are maintained at:
- `common/dispatcher/endpoints.toml`
- `common/dispatcher/routes.toml`

For V1 baseline parity, configuration discovery is strictly repository-relative under `common/dispatcher/` rooted at the active repository root. External configuration override (such as via an `APGR_DISPATCHER_CONFIG` environment variable) is a proposed extension tracked for V0120-C; in V0120-B, discovery defaults to repository-relative `common/dispatcher/`.

*(Note: These changes are recommendations delivered for evaluation and authoring by the Agent-Central team. APGR mutates nothing in Agent-Central; status remains **Proposed**.)*

---

## 3. Preservation of Local Interactive Worker Management (`agent-worker`)

A critical architectural distinction is preserved during this transition:
- **Phase Execution Dispatcher (`agent-phase-dispatch`)**: Bounded, structured stage lifecycle executing defined task contracts and emitting formal verification artifacts. **Transfers permanently to APGR.**
- **Local Interactive Subagent Supervisor (`bin/agent-worker`, `libexec/agent_workers/`)**: Ad-hoc, interactive supervisor managing local leaf subagent processes, child concurrency limits (e.g., 4 Gemini / 4 Luna pools), and workstation quota enforcement. **Permanently retained in Agent-Central.**

The local worker supervisor serves developer UX and workstation multitasking. It remains independent of APGR's phase execution engine, although single-phase tasks executed by APGR may internally coordinate with local workers via their inherited supervisor contracts when running in worker-enabled execution modes.
