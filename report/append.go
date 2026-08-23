package report

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"path/filepath"
	"strings"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/internal/atomicfile"
	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/schema"
)

// Append atomically publishes exactly one canonical record under
// <outbox>/<project>/<phase>/ and preserves the single-primary contract.
func Append(ctx context.Context, request AppendRequest) (Publication, error) {
	if err := ctx.Err(); err != nil {
		return Publication{}, err
	}
	if err := validateIdentifier(request.Project, "project"); err != nil {
		return Publication{}, err
	}
	if err := validateIdentifier(request.Phase, "phase"); err != nil {
		return Publication{}, err
	}
	if request.Record.Project != request.Project || request.Record.Phase != request.Phase {
		return Publication{}, fmt.Errorf("%w: record identity conflicts with append request", ErrInvalidRequest)
	}
	encoded, err := buildRecord(request.Record)
	if err != nil {
		return Publication{}, err
	}
	parsed, err := ParseRecords(encoded)
	if err != nil || len(parsed) != 1 {
		return Publication{}, fmt.Errorf("%w: append requires one canonical record", ErrCompatibility)
	}
	paths, err := atomicfile.Prepare(request.OutboxRoot, request.Project, request.Phase)
	if err != nil {
		return Publication{}, mapAtomicError(err)
	}
	showName := request.Phase + ".git.show.report.txt"
	diffName := request.Phase + ".git.diff.report.txt"
	opsName := request.Phase + ".ops.report.txt"
	names := []string{showName, diffName, opsName}
	publication := Publication{RecordID: request.Record.ID}
	err = atomicfile.WithLock(ctx, paths, func() error {
		if err := atomicfile.EnsureNoTransaction(paths); err != nil {
			return err
		}
		contents := map[string][]byte{}
		present := []string{}
		for _, name := range names {
			content, exists, readErr := atomicfile.ReadPrivate(filepath.Join(paths.Directory, name))
			if readErr != nil {
				return readErr
			}
			if exists {
				contents[name] = content
				present = append(present, name)
			}
		}
		if len(present) > 1 {
			return fmt.Errorf("%w: multiple current primary artifacts", atomicfile.ErrConflict)
		}
		current := ""
		if len(present) == 1 {
			current = present[0]
		}
		target := targetName(request.Record.Kind, current, showName, diffName, opsName)
		if target == "" {
			return fmt.Errorf("%w: unsupported report record type", atomicfile.ErrConflict)
		}
		existing := contents[target]
		if existing != nil {
			records, parseErr := ParseRecords(existing)
			if parseErr != nil {
				return fmt.Errorf("%w: existing report structure", atomicfile.ErrUnsafe)
			}
			if err := validateExistingRecords(records, request.Project, request.Phase); err != nil {
				return err
			}
			if request.Record.Kind == schema.OperationalRecord {
				if err := validateAppendAssociation(request.Record, records); err != nil {
					return err
				}
			}
		}
		combined := appendRecord(existing, encoded)
		disposition := PublishedNew
		if current == target && current != "" {
			disposition = PublishedAppend
		} else if current != "" {
			disposition = PublishedSuperseding
		}
		if records, parseErr := ParseRecords(combined); parseErr != nil || len(records) == 0 {
			return fmt.Errorf("%w: combined report structure", atomicfile.ErrUnsafe)
		}
		stale := make([]string, 0, 2)
		for _, name := range names {
			if name != target {
				stale = append(stale, name)
			}
		}
		if err := atomicfile.Replace(ctx, paths, target, stale, combined); err != nil {
			return err
		}
		publication.FinalPath = filepath.Join(paths.Directory, target)
		publication.Disposition = disposition
		return nil
	})
	if err != nil {
		return Publication{}, mapAtomicError(err)
	}
	return publication, nil
}

func targetName(kind schema.RecordKind, current, showName, diffName, opsName string) string {
	switch kind {
	case schema.GitShowRecord:
		return showName
	case schema.GitDiffRecord:
		return diffName
	case schema.OperationalRecord:
		if current == showName || current == diffName {
			return current
		}
		return opsName
	default:
		return ""
	}
}

func appendRecord(existing, record []byte) []byte {
	if len(existing) == 0 {
		return bytes.Clone(record)
	}
	result := bytes.Clone(existing)
	if result[len(result)-1] != '\n' {
		result = append(result, '\n')
	}
	return append(result, record...)
}

func validateExistingRecords(records []Record, project, phase string) error {
	for _, record := range records {
		if err := validateRecordIdentity(record); err != nil {
			return fmt.Errorf("%w: existing record identity", atomicfile.ErrUnsafe)
		}
		if record.Project != project || record.Phase != phase {
			return fmt.Errorf("%w: existing record ownership", atomicfile.ErrUnsafe)
		}
	}
	return nil
}

func validateAppendAssociation(record Record, existing []Record) error {
	related := payloadField(record.Payload, "RELATED-GIT-REPORT-ID")
	gitIDs := map[string]bool{}
	for _, item := range existing {
		if item.Kind == schema.GitShowRecord || item.Kind == schema.GitDiffRecord {
			gitIDs[item.ID] = true
		}
	}
	if len(gitIDs) == 0 {
		if related != "NONE" {
			return fmt.Errorf("%w: standalone operational relation", atomicfile.ErrUnsafe)
		}
		return nil
	}
	if related == "" || !gitIDs[related] {
		return fmt.Errorf("%w: operational Git relation", atomicfile.ErrUnsafe)
	}
	return nil
}

func payloadField(payload []byte, name string) string {
	prefix := []byte(name + ": ")
	for _, line := range bytes.Split(payload, []byte{'\n'}) {
		if bytes.HasPrefix(line, prefix) {
			return strings.TrimSpace(string(line[len(prefix):]))
		}
	}
	return ""
}

func mapAtomicError(err error) error {
	if errors.Is(err, atomicfile.ErrUnsafe) {
		return fmt.Errorf("%w: outbox filesystem state", ErrUnsafePath)
	}
	if errors.Is(err, atomicfile.ErrConflict) {
		return fmt.Errorf("%w: outbox transaction state", ErrPublication)
	}
	return err
}
