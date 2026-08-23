package schema

import (
	"crypto/sha256"
	"encoding/hex"
)

// EnvelopeFormat is the common report envelope identity.
const EnvelopeFormat = "agent-report-record"

// EnvelopeVersion is the current common report envelope version.
const EnvelopeVersion = 1

// RecordKind identifies a canonical APG report record family.
type RecordKind string

const (
	// GitShowRecord is a committed Git-show report.
	GitShowRecord RecordKind = "git-show-report"
	// GitDiffRecord is a drift-checked uncommitted Git-diff report.
	GitDiffRecord RecordKind = "git-diff-report"
	// OperationalRecord is caller-supplied operational evidence.
	OperationalRecord RecordKind = "operational-report"
)

// FormatVersion returns the accepted record format version for kind.
func (kind RecordKind) FormatVersion() (int, bool) {
	switch kind {
	case GitShowRecord:
		return 2, true
	case GitDiffRecord, OperationalRecord:
		return 1, true
	default:
		return 0, false
	}
}

// SHA256 returns the lowercase hexadecimal SHA-256 identity of data.
func SHA256(data []byte) string {
	digest := sha256.Sum256(data)
	return hex.EncodeToString(digest[:])
}

// Record is one canonical APG report payload and its common-envelope identity.
// Payload is caller-owned; APG results always populate it with a fresh copy.
type Record struct {
	// Kind identifies the canonical record family.
	Kind RecordKind
	// FormatVersion is the kind-specific record format version.
	FormatVersion int
	// ID is the canonical domain identity.
	ID string
	// Project is the canonical project owner.
	Project string
	// Phase is the canonical phase owner.
	Phase string
	// Payload is the exact common-envelope payload.
	Payload []byte
}
