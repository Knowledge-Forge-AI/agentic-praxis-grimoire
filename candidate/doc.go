// Package candidate provides immutable candidate identity definitions, artifact
// manifest specifications, and pure in-memory validation routines.
//
// Stability: Experimental / Provisional for APGR v0.12 (ICR-004 / ICR-005).
// Exported candidate contracts are candidate surfaces for JACA XO evaluation.
// Transition to Supported status occurs upon production qualification in v1.0.
//
// Authority Boundary:
// This package owns data models and pure validation only. Repository mutation,
// Git commit creation, publication, and workspace custody remain behind caller-owned
// authority implementations (e.g. JACA repository mutation fence).
//
// Concurrency and Immutability:
// All types and values in this package are immutable once constructed and safe
// for concurrent access across goroutines.
package candidate
