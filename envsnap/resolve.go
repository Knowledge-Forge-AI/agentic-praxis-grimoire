package envsnap

import (
	"context"
	"fmt"
	"sort"
)

const (
	sourceSnapshot = SourceSnapshot
	sourceOverride = SourceOverride
	sourceBase     = SourceBase
)

// Resolve produces a fresh environment map from an explicitly supplied
// profile, snapshot, and maps. Isolated is the default; Overlay applies the
// exact precedence override > snapshot > base.
func Resolve(ctx context.Context, request ResolveRequest) (ResolvedEnvironment, error) {
	if ctx == nil {
		ctx = context.Background()
	}
	if err := ctx.Err(); err != nil {
		return ResolvedEnvironment{}, err
	}
	if request.Profile == nil {
		return ResolvedEnvironment{}, ErrProfileMismatch
	}
	profile := *request.Profile
	if err := ValidateProfile(profile); err != nil {
		return ResolvedEnvironment{}, err
	}
	mode := request.Mode
	if mode == "" {
		mode = ModeIsolated
	}
	if mode != ModeIsolated && mode != ModeOverlay {
		return ResolvedEnvironment{}, ErrInvalidMode
	}
	if err := validateSnapshotAgainstProfile(request.Snapshot, profile); err != nil {
		return ResolvedEnvironment{}, err
	}
	profileEntries := profileEntryMap(profile)
	result := ResolvedEnvironment{
		Mode:        mode,
		Environment: make(map[string]string),
		Provenance:  make(map[string]ValueProvenance),
	}
	if mode == ModeOverlay {
		if err := applyBase(ctx, &result, request.Base, profileEntries); err != nil {
			return ResolvedEnvironment{}, err
		}
	}
	if err := ctx.Err(); err != nil {
		return ResolvedEnvironment{}, err
	}
	for _, entry := range request.Snapshot.Entries {
		result.Environment[entry.Name] = entry.Value
		result.Provenance[entry.Name] = ValueProvenance{Name: entry.Name, Source: sourceSnapshot}
	}
	for _, name := range sortedKeys(request.Overrides) {
		if err := ctx.Err(); err != nil {
			return ResolvedEnvironment{}, err
		}
		value := request.Overrides[name]
		entry, ok := profileEntries[name]
		if !ok {
			return ResolvedEnvironment{}, fmt.Errorf("%w: override %s is not in profile", ErrInvalidProfile, name)
		}
		if err := validateValue(value, entry.Validator, entry.MaxBytes); err != nil {
			return ResolvedEnvironment{}, invalidValueForName(name, entry.Validator, err)
		}
		result.Environment[name] = value
		result.Provenance[name] = ValueProvenance{Name: name, Source: sourceOverride}
	}
	return result, nil
}

func applyBase(ctx context.Context, result *ResolvedEnvironment, base map[string]string, profileEntries map[string]ProfileEntry) error {
	for _, name := range sortedKeys(base) {
		if err := ctx.Err(); err != nil {
			return err
		}
		value := base[name]
		if entry, ok := profileEntries[name]; ok {
			if err := validateValue(value, entry.Validator, entry.MaxBytes); err != nil {
				return invalidValueForName(name, entry.Validator, err)
			}
		}
		result.Environment[name] = value
		result.Provenance[name] = ValueProvenance{Name: name, Source: sourceBase}
	}
	return nil
}

func sortedKeys(values map[string]string) []string {
	keys := make([]string, 0, len(values))
	for name := range values {
		keys = append(keys, name)
	}
	sort.Strings(keys)
	return keys
}
