// Package phase provides reusable, deterministic domain contracts for single-phase
// lifecycles, work-only Request V2 parsing, semantic responsibility definitions,
// actor binding topologies, and invocation attempt models.
//
// Stability: Experimental / Provisional for APGR v0.12 (ICR-004 / ICR-005).
// Exported domain types are candidate surfaces for JACA XO evaluation. Transition
// to Supported status occurs upon production qualification in v1.0.
//
// Request V2 enforces a strict work-only schema: schema, phase_type, and prompt.
// Runtime policy fields such as execution_mode, constraints, provider, model, or
// profile are strictly rejected at parse time.
//
// Concurrency and Immutability:
// All types and values in this package are immutable once constructed and safe
// for concurrent access across goroutines.
package phase
