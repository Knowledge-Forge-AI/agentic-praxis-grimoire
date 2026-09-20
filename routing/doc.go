// Package routing provides pure, deterministic route eligibility, ranking,
// tie-breaking evaluation, and operational observation models.
//
// Stability: Experimental / Provisional for APGR v0.12 (ICR-004 / ICR-005).
// Exported resolver primitives and observation types are candidate surfaces for
// JACA XO evaluation. Transition to Supported status occurs upon production qualification.
//
// Policy Neutrality & Non-Authority Contract:
// The resolver in this package is an unprivileged, pure in-memory calculation engine.
// It accepts caller-supplied capability catalogs, observations, and requirement structs.
// Exporting or invoking routing.Resolve transfers NO route-policy authority to APGR.
// When consumed by JACA XO or external orchestrators, JACA retains complete policy,
// selection, and accounting authority over route decisions.
//
// Environment Invariants:
// This package contains zero subprocess execution, zero filesystem access, zero SQLite
// persistence, and zero reliance on ambient working directory or environment variables.
//
// Concurrency:
// All exported structures, observation digests, and resolver functions are safe for
// concurrent use by multiple goroutines.
package routing
