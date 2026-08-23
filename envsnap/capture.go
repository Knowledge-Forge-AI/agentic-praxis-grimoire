package envsnap

import (
	"context"
	"sort"
)

const sourceCapture = SourceCapture

// Capture validates an explicit profile and captures only present, non-empty
// values from the caller-owned map. It never reads os.Environ and never
// mutates the supplied map.
func Capture(ctx context.Context, request CaptureRequest) (Snapshot, error) {
	if ctx == nil {
		ctx = context.Background()
	}
	if err := ctx.Err(); err != nil {
		return Snapshot{}, err
	}
	if err := ValidateProfile(request.Profile); err != nil {
		return Snapshot{}, err
	}
	if err := validateProvenance(request.Provenance); err != nil {
		return Snapshot{}, err
	}
	profileHash, err := profileFingerprint(request.Profile)
	if err != nil {
		return Snapshot{}, err
	}
	entries := sortedProfileEntries(request.Profile)
	values := make([]SnapshotEntry, 0, len(entries))
	missing := make([]string, 0)
	requiredMissing := make([]string, 0)
	for _, entry := range entries {
		if err := ctx.Err(); err != nil {
			return Snapshot{}, err
		}
		value, present := request.Environment[entry.Name]
		if !present || value == "" {
			if entry.Required {
				requiredMissing = append(requiredMissing, entry.Name)
			} else {
				missing = append(missing, entry.Name)
			}
			continue
		}
		if err := validateValue(value, entry.Validator, entry.MaxBytes); err != nil {
			return Snapshot{}, invalidValueForName(entry.Name, entry.Validator, err)
		}
		values = append(values, SnapshotEntry{
			Name:      entry.Name,
			Validator: entry.Validator,
			Value:     value,
			Source:    sourceCapture,
		})
	}
	if len(requiredMissing) > 0 {
		sort.Strings(requiredMissing)
		return Snapshot{}, &MissingRequiredError{Names: requiredMissing}
	}
	sort.Strings(missing)
	snapshot := Snapshot{
		SchemaVersion:      SnapshotSchemaV1,
		ProfileID:          request.Profile.ProfileID,
		ProfileFingerprint: profileHash,
		ProducerVersion:    request.ProducerVersion,
		Provenance:         request.Provenance,
		CapturedAt:         nowUTC(request.Clock),
		Entries:            values,
		MissingOptional:    missing,
	}
	if snapshot.ProducerVersion == "" {
		snapshot.ProducerVersion = ProducerVersion
	}
	if len([]byte(snapshot.ProducerVersion)) > 1024 {
		return Snapshot{}, invalidSnapshot("producer version is too long")
	}
	snapshot.ContentFingerprint, err = snapshotFingerprint(snapshot)
	if err != nil {
		return Snapshot{}, err
	}
	return cloneSnapshot(snapshot), nil
}

func invalidValueForName(name, validator string, err error) error {
	return &namedValueError{name: name, validator: validator, cause: err}
}

type namedValueError struct {
	name      string
	validator string
	cause     error
}

func (e *namedValueError) Error() string {
	return "environment value failed validation for " + e.name + " (" + e.validator + ")"
}

func (e *namedValueError) Unwrap() error { return e.cause }
