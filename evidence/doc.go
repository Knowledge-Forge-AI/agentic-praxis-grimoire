// Package evidence defines structured models for review findings, severities,
// categories, dispositions, review bindings, and completion receipts.
//
// Stability: Experimental / Provisional for APGR v0.12 (ICR-004 / ICR-005).
// Exported evidence types are candidate surfaces for JACA XO evaluation. Transition
// to Supported status occurs upon production qualification in v1.0.
//
// Security & Path Safety:
// Review findings strictly reject path traversal tokens ("..", leading slashes,
// or non-normalized forms) to protect consumer systems from path leakage or tampering.
//
// Concurrency and Immutability:
// All types and values in this package are immutable once constructed and safe
// for concurrent access across goroutines.
package evidence
