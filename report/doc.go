// Package report collects, parses, renders, and optionally publishes canonical
// APG Git-show, Git-diff, and operational report records.
//
// Collection is in-memory at the public boundary. The package may invoke the
// caller-selected native Git executable with a fixed argument vector, but it
// never invokes a shell or requires the APG CLI or Python implementation.
package report
