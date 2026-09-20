# Evaluation: Context Footprint Baseline and Discovery Accounting

- **Status**: Frozen APGR-side accounting baseline (file bytes with provenance; provider delivery unobserved)
- **Phase**: APG159 (Milestone V0130-A)
- **Governing ADR**: [ADR 0072](../adr/2026/09/0072-optional-rtk-integration-and-conditional-slices.md), [ADR 0074](../adr/2026/09/0074-context-plan-byte-budgets-and-bounded-mcp-adapter.md)
- **Accounting Standard**: `apg.context-footprint/v1` ([ADR 0052](../adr/2026/08/0052-v0-8-context-footprint-and-skill-inventory.md))

---

## 1. Accounting Principles and Invariants

Context measurements adhere strictly to the invariants codified in the Go `footprint` package:
1. **Measured Units**: APGR measures controlled UTF-8 bytes and characters. Token counts are classified as `unavailable` unless measured by a named tokenizer or provider API counter. Approximate heuristics (e.g. 4 chars per token) are strictly prohibited from entering canonical accounting.
2. **"Unavailable is not Zero"**: If a component cannot be measured directly, it is marked as `unavailable`, not zero.
3. **"Overlap is not Additive"**: Shared content (such as shared instruction headers or duplicate descriptions across roots) is counted once under total delivered bytes.
4. **Planned vs Materialized vs Delivered**: Accounting distinguishes:
   - *Planned*: Bytes budgeted by the context planner.
   - *Materialized*: Bytes written to run-owned snapshot stores.
   - *Delivered*: Bytes actually emitted into the provider prompt or tool definitions.

---

## 2. Canonical Discovery Ceiling Accounting

Under `libexec/apg_skill_library_check.py:439,1399`, the discovery ceiling applies to the sum of UTF-8 description bytes across all canonical skills:

| Metric | Measured Value | Authority / Reference |
|---|---|---|
| **Canonical Skills Count** | 45 skills | `bin/apg-check-skill-library` |
| **Current Total Description Bytes** | 11,142 bytes | `bin/apgr skills context-report` |
| **Current Total Description Characters** | 11,126 chars | `bin/apgr skills context-report` |
| **Governing Discovery Ceiling** | 11,507 bytes | ADR 0053 (`v0.10-browser-runtime`) |
| **Current Available Headroom** | 365 bytes | $11,507 - 11,142 = 365$ |
| **Candidate `rtk-command-proxy` Description** | 268 bytes | Measured UTF-8 bytes |
| **Projected 46-Skill Total Bytes** | 11,410 bytes | $11,142 + 268 = 11,410$ |
| **Projected Headroom after Adoption** | 97 bytes | $11,507 - 11,410 = 97$ |

### Discovery Policy Decision
The measured description of `rtk-command-proxy` (268 bytes) fits completely within the existing 11,507-byte ceiling, leaving 97 bytes of headroom. Therefore:
1. **No ceiling expansion is authorized for the adoption of `rtk-command-proxy`**.
2. **Any 47th canonical skill in v0.13 will require an explicit, measured discovery policy revision** (such as `v0.13-adaptive-context`).

---

## 3. Static Baseline Components per Provider (APGR-Side File Bytes)

In v0.12 static mode, the APGR-controlled inputs to a provider launch are:
- The APGR provider instruction file retained in the controller generation store (`codex/AGENTS.md`, `claude/CLAUDE.md`, or `antigravity/GEMINI.md`; see `libexec/controller_generation_store.py`). The target repository's own root `AGENTS.md` / `CLAUDE.md` / `GEMINI.md` is repository doctrine read natively by the provider and is **not** an APGR-controlled transport component; it is excluded from this table.
- 45 canonical skill descriptions (11,142 bytes) projected into discovery directories.
- Full skill bodies on demand or projected.

### 3.1 Measured APGR-Side File Bytes

Every figure below is an exact UTF-8 byte count of a file (or line range) in this clone at the APG159 candidate tree, measured on 2026-09-20 with `wc -c` (whole files) and `sed -n '<start>,<end>p' <file> | wc -c` (line ranges). They are **file bytes on the APGR side**, not observed provider delivery. No `~` approximations remain; anything not measured is `unavailable`.

| Component | Codex | Claude | Antigravity | Provenance |
|---|---|---|---|---|
| **Provider instruction file** | `codex/AGENTS.md`: 7,939 bytes | `claude/CLAUDE.md`: 11,071 bytes | `antigravity/GEMINI.md`: 4,238 bytes | `wc -c` on the named file; identical bytes in the read-only source checkout at APG158A |
| **RTK slice within that file** | 240 bytes (`## RTK` section, lines 129–133) | 35 bytes (one clause, line 143: ``The Bash hook is `rtk hook claude`;`` inside `## PreToolUse Policy`); **no separable slice exists** | 1,041 bytes (`## RTK shell-output efficiency` section, lines 24–43) | `sed -n` line range piped to `wc -c`; Claude clause measured with `grep -o` |
| **Native discovery descriptions** | 11,142 bytes | 11,142 bytes | 11,142 bytes | `bin/apgr skills context-report` (canonical corpus description bytes; projection to each provider root assumed byte-identical, delivery unobserved) |
| **Tool schema / MCP overhead** | `unavailable` (no adapter exists yet) | `unavailable` | `unavailable` | Measured in V0130-G once `apgr mcp serve` exists |
| **Actually delivered provider bytes** | `unavailable` | `unavailable` | `unavailable` | Requires provider-side observation or a transport capture; not performed in APG159 |

Limitations:
1. The RTK "slice" is a v0.13 design construct (ADR 0072). In v0.12 the RTK text is inline prose; the Claude clause is a single sentence fragment in the PreToolUse section and cannot be removed as a unit without editing the surrounding sentence. V0130-D must define the exact slice boundaries before any RTK-off byte claim is made.
2. Sums across rows are deliberately not reported as "delivery": instruction files and discovery descriptions reach the provider through different channels, and "overlap is not additive" applies to any shared content.
3. Byte counts of `codex/AGENTS.md` versus the root repository `AGENTS.md` (92,493 bytes at APG158A) differ by an order of magnitude; earlier drafts mixed these classes. Only the provider instruction file is APGR-controlled and appears here.

### 3.2 No-RTK Static Baseline (Definition, Not a Measured Delivery)

When RTK is disabled (`[integrations.rtk] enabled = false`, ADR 0072), the RTK slice is omitted from the provider instruction file. The expected APGR-side instruction file bytes after omission, computed by subtracting the measured slice from the measured file, are:

| Provider | File bytes | Slice bytes | Expected no-RTK file bytes |
|---|---|---|---|
| Codex | 7,939 | 240 | 7,699 |
| Claude | 11,071 | 35 | 11,036 (subject to the boundary limitation above) |
| Antigravity | 4,238 | 1,041 | 3,197 |

These are the frozen **input definitions** for the V0130-D corrected no-RTK baseline. They become the V0130-H control baseline only after V0130-D materializes the slices and records the actual transported bytes with digests; until then they are arithmetic over file bytes and carry no delivery claim.
