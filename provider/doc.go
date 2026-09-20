// Package provider defines machine-readable capability and conformance row types
// representing evaluated features across the Codex, Claude, and Antigravity provider
// families (ADR 0061 / ADR 0065).
//
// Stability: Experimental / Provisional for APGR v0.12 (ICR-004 / ICR-005).
// Exported conformance types are candidate surfaces for JACA XO evaluation.
// Transition to Supported status occurs upon production qualification in v1.0.
//
// Concurrency and Immutability:
// All types and values in this package are immutable once constructed and safe
// for concurrent access across goroutines.
package provider
