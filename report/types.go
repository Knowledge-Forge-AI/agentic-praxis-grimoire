package report

import (
	"context"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/internal/gitexec"
	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/schema"
)

// Record is the public canonical report-record value.
type Record = schema.Record

// Options selects the exact repository root and native Git executable.
type Options struct {
	// Repository is the absolute, clean, exact Git worktree root.
	Repository string
	// GitPath is empty for the fixed name git or an absolute direct regular file.
	GitPath string
}

// Service is a reusable, immutable report collector for one repository.
// Independent calls may safely run concurrently.
type Service struct {
	repository string
	git        gitexec.Runner
}

// RequestMetadata is the common caller-owned report metadata.
type RequestMetadata struct {
	// Phase is the canonical caller-selected phase identifier.
	Phase string
	// Result is the report's caller-owned outcome vocabulary.
	Result string
	// FinalGate is the caller-owned final verification description.
	FinalGate string
}

// ShowRequest requests one committed Git-show record.
type ShowRequest struct {
	RequestMetadata
	// Commit is a 7-to-64-character hexadecimal commit input.
	Commit string
	// StatusDoc is the caller-owned status-document association.
	StatusDoc string
}

// DiffRequest requests one drift-checked uncommitted Git-diff record.
type DiffRequest struct {
	RequestMetadata
	// StatusDoc is an optional clean repository-relative association.
	StatusDoc string
}

// OperationalRequest requests one caller-supplied operational record.
type OperationalRequest struct {
	RequestMetadata
	// Project is the canonical outbox-safe project identifier.
	Project string
	// SourceName is the source basename recorded in canonical evidence.
	SourceName string
	// Source is the exact caller-supplied operational payload.
	Source []byte
	// RelatedCommit is set only for a matching Git-show relation.
	RelatedCommit string
	// RelatedGitReportID selects the exact related canonical Git record.
	RelatedGitReportID string
}

// AppendRequest publishes exactly one canonical record into one phase outbox.
type AppendRequest struct {
	// OutboxRoot is the absolute, clean owner-only outbox root.
	OutboxRoot string
	// Project is the canonical outbox project identifier.
	Project string
	// Phase is the canonical outbox phase identifier.
	Phase string
	// Record is exactly one canonical record to publish.
	Record Record
}

// Result is an in-memory canonical report result. Evidence contains fresh
// caller-owned normalized values; byte-valued entries are defensive copies.
type Result struct {
	// Record is the parsed canonical record with caller-owned payload storage.
	Record Record
	// Bytes is the exact canonical envelope with caller-owned storage.
	Bytes []byte
	// Evidence holds type-specific normalized values with caller-owned storage.
	Evidence map[string][]byte
}

// PublicationDisposition identifies the deterministic outbox transition.
type PublicationDisposition string

const (
	// PublishedNew created the phase's first primary.
	PublishedNew PublicationDisposition = "published-new"
	// PublishedAppend appended to the existing primary type.
	PublishedAppend PublicationDisposition = "published-append"
	// PublishedSuperseding replaced a different primary type.
	PublishedSuperseding PublicationDisposition = "published-superseding"
)

// Publication identifies the resulting primary and publication transition.
type Publication struct {
	// FinalPath is the resulting canonical primary path.
	FinalPath string
	// RecordID is the published record's canonical identity.
	RecordID string
	// Disposition describes the deterministic primary transition.
	Disposition PublicationDisposition
}

// Show collects and renders one exact committed report without publishing it.
func (service *Service) Show(ctx context.Context, request ShowRequest) (Result, error) {
	return service.show(ctx, request)
}

// Diff collects and renders one drift-checked report without publishing it.
func (service *Service) Diff(ctx context.Context, request DiffRequest) (Result, error) {
	return service.diff(ctx, request)
}
