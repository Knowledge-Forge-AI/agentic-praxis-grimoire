// Package report collects, parses, renders, verifies, and optionally publishes
// canonical APG Git-show, Git-diff, and operational report records.
//
// Collection is in-memory at the public boundary. The package may invoke the
// caller-selected native Git executable with a fixed argument vector, but it
// never invokes a shell or requires the APG CLI or Python implementation.
//
// Verification is context-aware and strictly validates contiguous canonical
// common-envelope records in-memory via Verify or on-disk via VerifyFile using
// read-only bounded complete read and stability observation without mutating
// permissions or filesystem state.
// Cancellation is checked at entry and between records; large delimiter-heavy
// sections do not have a qualified prompt-cancellation or linear-work bound.
package report
