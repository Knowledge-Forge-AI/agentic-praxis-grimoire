package report

import (
	"bytes"
	"context"
	"fmt"
	"regexp"
	"strings"
)

const numstatHeading = "COLUMNS: ADDED-LINES\tDELETED-LINES\tPATH\nBINARY-MARKER: -\n"

// Reconstruct inputs from persisted evidence, then use the canonical renderers
// to check all derived summaries, field ordering and inner/outer identities.
func validateShowRecord(record Record) error {
	return validateShowRecordWithContext(context.Background(), record, nil)
}

func validateShowRecordWithContext(ctx context.Context, record Record, stats *envelopeExtractionStats) error {
	sections, err := decodeSectionsWithContext(ctx, record.Payload, []sectionSpec{
		{name: "READING GUIDE"}, {name: "REPORT IDENTITY"}, {name: "COMMIT SUMMARY"},
		{name: "CHANGED FILES", hash: "CHANGED-FILES-SHA256"}, {name: "NUMSTAT", hash: "NUMSTAT-SHA256"},
		{name: "COMMIT MESSAGE", hash: "COMMIT-MESSAGE-SHA256"}, {name: "PATCH", hash: "PATCH-SHA256"},
	}, stats)
	if err != nil {
		return err
	}
	identity, _, err := parseSectionFieldsWithContext(ctx, sections["REPORT IDENTITY"])
	if err != nil {
		return err
	}
	commit := identity["COMMIT"]
	if !showIDValidationPattern.MatchString("GIT-SHOW-REPORT-"+commit) || !commitInputPattern.MatchString(identity["COMMIT-INPUT"]) || !strings.HasPrefix(commit, strings.ToLower(identity["COMMIT-INPUT"])) {
		return fmt.Errorf("%w: invalid persisted commit", ErrCompatibility)
	}
	basis, err := persistedComparison(identity["PARENTS"])
	if err != nil {
		return err
	}
	numstat, err := persistedNumstat(sections["NUMSTAT"])
	if err != nil {
		return err
	}
	metadata := commitMetadata{commit: commit, parents: identity["PARENTS"], authorName: identity["AUTHOR-NAME"], authorEmail: identity["AUTHOR-EMAIL"], authorDate: identity["AUTHOR-DATE"], committerName: identity["COMMITTER-NAME"], committerEmail: identity["COMMITTER-EMAIL"], committerDate: identity["COMMITTER-DATE"], subject: identity["SUBJECT"]}
	request := ShowRequest{RequestMetadata: RequestMetadata{Phase: record.Phase, Result: identity["RESULT"], FinalGate: identity["FINAL-GATE"]}, Commit: identity["COMMIT-INPUT"], StatusDoc: identity["STATUS-DOC"]}
	evidence := showEvidence{changed: sections["CHANGED FILES"], numstatRaw: numstat, numstat: sections["NUMSTAT"], message: sections["COMMIT MESSAGE"], patch: sections["PATCH"]}
	canonical, err := renderShowRecord(request, request.StatusDoc, record.Project, metadata, basis, evidence)
	return comparePersistedRecord(record, canonical, err)
}

func persistedComparison(parents string) (comparison, error) {
	if parents == "NONE" {
		return comparison{parentsValue: "NONE", rootCommit: "true", mergeCommit: "false", patchMode: "root"}, nil
	}
	values := strings.Split(parents, " ")
	for _, value := range values {
		if !showIDValidationPattern.MatchString("GIT-SHOW-REPORT-" + value) {
			return comparison{}, fmt.Errorf("%w: malformed persisted parents", ErrCompatibility)
		}
	}
	basis := comparison{parentsValue: parents, parentCount: len(values), rootCommit: "false", mergeCommit: "false", patchMode: "single-parent"}
	if len(values) > 1 {
		basis.mergeCommit = "true"
		basis.patchMode = "first-parent-merge"
	}
	return basis, nil
}

func validateDiffRecord(record Record) error {
	return validateDiffRecordWithContext(context.Background(), record, nil)
}

func validateDiffRecordWithContext(ctx context.Context, record Record, stats *envelopeExtractionStats) error {
	sections, err := decodeSectionsWithContext(ctx, record.Payload, []sectionSpec{
		{name: "READING GUIDE"}, {name: "REPORT IDENTITY"}, {name: "WORKTREE SUMMARY"},
		{name: "PORCELAIN V2 STATUS (NUL DELIMITED)", hash: "PORCELAIN-V2-STATUS-SHA256", rawNewline: true},
		{name: "STAGED SUMMARY", hash: "STAGED-SUMMARY-SHA256", rawNewline: true}, {name: "UNSTAGED SUMMARY", hash: "UNSTAGED-SUMMARY-SHA256", rawNewline: true},
		{name: "CHANGED FILES", hash: "CHANGED-FILES-SHA256"}, {name: "NUMSTAT", hash: "NUMSTAT-SHA256"}, {name: "PATCH", hash: "PATCH-SHA256"},
	}, stats)
	if err != nil {
		return err
	}
	identity, _, err := parseSectionFieldsWithContext(ctx, sections["REPORT IDENTITY"])
	if err != nil {
		return err
	}
	if err := validatePersistedIndex(identity); err != nil {
		return err
	}
	numstat, err := persistedNumstat(sections["NUMSTAT"])
	if err != nil {
		return err
	}
	statusDoc, err := validateStatusDoc(identity["STATUS-DOC"], true)
	if err != nil {
		return err
	}
	request := DiffRequest{RequestMetadata: RequestMetadata{Phase: record.Phase, Result: identity["RESULT"], FinalGate: identity["FINAL-GATE"]}, StatusDoc: statusDoc}
	observation := realObservation{head: identity["HEAD"], indexFingerprint: identity["REAL-INDEX-FINGERPRINT"], indexIdentity: identity["REAL-INDEX-IDENTITY"], status: sections["PORCELAIN V2 STATUS (NUL DELIMITED)"], staged: sections["STAGED SUMMARY"], unstaged: sections["UNSTAGED SUMMARY"]}
	snapshot := worktreeSnapshot{changed: sections["CHANGED FILES"], numstatRaw: numstat, patch: sections["PATCH"]}
	if len(snapshot.patch) == 0 {
		return fmt.Errorf("%w: empty diff evidence", ErrCompatibility)
	}
	canonical, _, err := renderDiffRecord(request, statusDoc, record.Project, identity["INDEX-MODE"], observation, snapshot)
	return comparePersistedRecord(record, canonical, err)
}

var persistedFingerprint = regexp.MustCompile(`^sha256:[0-9a-f]{64};size:(0|[1-9][0-9]*)$`)

func validatePersistedIndex(identity map[string]string) error {
	if !showIDValidationPattern.MatchString("GIT-SHOW-REPORT-" + identity["HEAD"]) {
		return fmt.Errorf("%w: malformed persisted HEAD", ErrCompatibility)
	}
	switch identity["INDEX-MODE"] {
	case "missing-seeded-from-head":
		if identity["REAL-INDEX-FINGERPRINT"] == "MISSING" && identity["REAL-INDEX-IDENTITY"] == "MISSING" {
			return nil
		}
	case "regular":
		if persistedFingerprint.MatchString(identity["REAL-INDEX-FINGERPRINT"]) && strings.HasPrefix(identity["REAL-INDEX-IDENTITY"], "sha256:") && hex64.MatchString(strings.TrimPrefix(identity["REAL-INDEX-IDENTITY"], "sha256:")) {
			return nil
		}
	}
	return fmt.Errorf("%w: inconsistent persisted index metadata", ErrCompatibility)
}

func persistedNumstat(content []byte) ([]byte, error) {
	if !bytes.HasPrefix(content, []byte(numstatHeading)) {
		return nil, fmt.Errorf("%w: malformed numstat heading", ErrCompatibility)
	}
	return content[len(numstatHeading):], nil
}

func comparePersistedRecord(record, canonical Record, err error) error {
	if err != nil {
		return err
	}
	if record.Kind != canonical.Kind || record.FormatVersion != canonical.FormatVersion || record.ID != canonical.ID || !bytes.Equal(record.Payload, canonical.Payload) {
		return fmt.Errorf("%w: payload differs from canonical semantics", ErrCompatibility)
	}
	return nil
}
