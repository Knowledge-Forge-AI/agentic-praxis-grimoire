// Package footprint provides deterministic, provider-neutral context
// footprint records and bounded derived comparisons and projections.
//
// The package deliberately owns data and validation only. It does not execute
// providers, select routes, manage credentials, or implement workflow
// authority. Canonical bytes are UTF-8 JSON with one trailing line feed; the
// corresponding fingerprints are domain-separated SHA-256 identities.
package footprint
