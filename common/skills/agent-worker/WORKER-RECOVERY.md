# Parent-directed worker recovery

A bounded wait observes a job; it does not set its lifetime. Quiet tests and
builds may be healthy. There is no default inactivity killer. Preserve upstream
AGY print timeout and ordinary stage outer ceiling. Advisory check-in budgets
return a decision to the parent, never an inferred deadlock.

1. Inspect status and retained partial output. Distinguish task outcome,
   cancellation decision, provider terminal state and cleanup. A useful partial
   answer is not success, and exit zero does not establish semantic acceptance.
   Record the parent's disposition through MCP `outcome` or CLI `job outcome`
   with evidence. This bookkeeping never proves cleanup or releases a slot.
2. Decide whether to continue other work, investigate, pause the affected pool,
   or abandon. `job abandon --reason ...` / MCP `abandon` persists the decision
   before signalling the exact owned supervisor. Finite TERM-to-KILL grace is
   cleanup after explicit cancellation, never a routine task timeout.
3. Retain occupancy and workspace custody until provider/tool cleanup is proven.
   Cancel acknowledgement, wrapper exit, dead supervisor, stale PID, and journal
   age cannot prove drain. Unknown identity must not authorize signalling an
   unrelated process. Repeated cancellation is idempotent; late bind cannot
   resurrect a stopping attempt. Disjoint work can continue during uncertainty.
4. After drain, inspect the stable partial candidate. Preserve useful bytes.
   A replacement receives the original acceptance criteria, observed partial
   state, failure reason and explicit adopt/amend/reject/continue decision.
   Supply the same task ID and previous job ID with the recovery decision/reason.
   Never replay the original mutation prompt blindly or delete a candidate to
   disguise a retry. Two delegated attempts per logical task is the default
   ceiling; then finish directly or disposition remaining work explicitly.
5. Explicit quota exhaustion pauses new admissions to that parent's affected
   pool without spawning providers. Do not infer exhaustion from silence,
   transient rate limits, authentication or protocol failures. Do not retry
   exhaustion/authentication automatically, switch accounts, change billing,
   downgrade models, or poll reset timers. Unpause requires explicit credible
   availability evidence. Viable in-flight jobs are not automatically killed.
6. Finish directly or use another allowed pool at its unchanged cap. Fallback
   preserves read-only authority, provider exclusions, workspace scope and
   top-level roster/review checkpoints. Astra and Luna may share account quota;
   another model is not evidence of independent capacity.
7. Supervisors and owning launchers retain task, result and custody evidence if
   the parent or MCP facade exits. A dead facade never releases jobs. A later
   explicitly invoked parent can inspect and drain that evidence before adopting
   work. Do not transparently create a second parent or replay a dispatcher.
   Unknown cleanup blocks overlapping capture/commit, not unrelated operation.

Reports must distinguish injected faults, observed provider errors, unobserved
state, and workspace-wide Git status from exclusively attributed task edits.
Keep partial output and process cleanup receipts even when no model turn remains.
