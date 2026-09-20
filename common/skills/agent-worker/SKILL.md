---
name: agent-worker
description: Delegate bounded leaf work through the selected APGR dispatcher worker facility and retain admission, result and cleanup evidence.
---

# APGR worker facility

Use only the parent context, kinds and ceilings exposed by this launch.
The selected APGR runtime owns this guidance and its absolute worker entrypoints.
Do not resolve a same-named command from another installation through PATH.

In `triple_pool_4x4x4`, Gemini, Luna and Sonnet each have four independent
slots, excluding the parent, with no borrowing. Luna remains `gpt-6-luna`/max;
Sonnet is `claude-sonnet-5-5`/high. Claude parents use external Gemini/Luna and
native Sonnet. Codex parents use external Gemini/Sonnet and native Luna.
Gemini parents use external Gemini/Luna/Sonnet. Native and foreign transport
names in resolved capability evidence are authoritative for the admitted run.
Historical two-pool generations retain their original capacity and controller.

Workers are nonrecursive leaves. Parent authority bounds worker authority.
Read-only tasks forbid tests, builds, installers, formatters, Git mutation and
product edits. Writing tasks require explicit disjoint relative path ownership.
Workers return findings through the facility and never satisfy independent
dispatcher review checkpoints.

Use the exposed `mcp__agent_worker__submit`, `status`, `result`, `wait`, `outcome`,
`cancel`, `abandon` and `pause_pool` tools. Supply a bounded objective,
acceptance criteria, idempotency key and task authority. The launcher supplies
parent identity, source root, workspace and policy. Do not initialize a second
parent or create a fresh allowance. Codex parents submit Luna only through native
Codex tools; their external facade exposes Gemini and Sonnet. Claude parents
invoke only the launcher-bound native Sonnet Agent type. Native Sonnet leaves
have no Bash, Agent, Task or worker MCP tools; other native agent types and
per-call model overrides are denied. Native hook admission is atomic and
requires `run_in_background=false`. For a native writing job, put
`APGR-MUTATION-SCOPE: ["repository/relative/path"]` on the first prompt line.
Admission freezes that scope and refuses overlap with active native or
external writers. Read-only jobs cannot claim a write scope. Hook errors
return blocking exit 2; a guarded deadline precedes the provider timeout.
Uncertain interrupted reservations remain occupied until proven cleanup.

A wait timeout is not job failure. Inspect progress and deliberately continue,
investigate or abandon; do not poll indefinitely. Two attempts per logical task
are the ceiling. A replacement must identify its predecessor and explicitly
adopt, amend or reject retained partial work after cleanup is proven.

Quota exhaustion pauses the affected pool. Do not retry automatically, poll
quota resets, change accounts or silently fall back. Report unavailable with a
diagnostic when required capabilities cannot be used. Record used for actual
admissions or declined with a bounded reason when available work stays local.

APGR context uses `APGR_PARENT_ID`, `APGR_WORKER_STATE_DIR` and
`APGR_WORKER_FACADE`. Other dispatchers' environment markers grant no authority.
Ledger reservations and uncertain cleanup retain custody until proven drained.
Completion is not proof that native threads were deleted; native active
occupancy remains Codex-owned.

See [worker recovery](WORKER-RECOVERY.md). The parent owns integration,
verification, worker disposition and the final cleanup record.
