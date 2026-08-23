// Package envsnap provides provider-neutral, explicit environment profiles,
// snapshots, locked storage, and deterministic resolution.
//
// The package never reads or mutates the process environment. Callers pass an
// explicit map to Capture and receive a fresh map from Resolve. Canonical
// snapshots use the apg.environment-snapshot/v1 JSON schema.
package envsnap
