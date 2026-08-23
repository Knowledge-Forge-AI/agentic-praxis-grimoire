package envsnap

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"sort"
	"time"
	"unicode/utf8"
)

// DecodeProfile strictly decodes and validates one canonical profile JSON
// document. Duplicate object keys, unknown fields, trailing JSON, invalid
// UTF-8, and semantic profile errors are rejected.
func DecodeProfile(data []byte) (Profile, error) {
	var profile Profile
	if err := decodeStrict(data, &profile); err != nil {
		return Profile{}, fmt.Errorf("%w: %v", ErrInvalidProfile, err)
	}
	if err := validateProfileJSONTypes(data); err != nil {
		return Profile{}, fmt.Errorf("%w: %v", ErrInvalidProfile, err)
	}
	if err := ValidateProfile(profile); err != nil {
		return Profile{}, err
	}
	return profile, nil
}

// MarshalProfile returns compact canonical profile JSON with an LF final
// newline. Entries are emitted in deterministic name order.
func MarshalProfile(profile Profile) ([]byte, error) {
	if err := ValidateProfile(profile); err != nil {
		return nil, err
	}
	canonical := profile
	canonical.Entries = sortedProfileEntries(profile)
	if canonical.Entries == nil {
		canonical.Entries = []ProfileEntry{}
	}
	return marshalCanonical(canonical)
}

// DecodeSnapshot strictly decodes one snapshot document. Profile-dependent
// validation is performed by Load or Resolve when the expected profile is
// available.
func DecodeSnapshot(data []byte) (Snapshot, error) {
	var snapshot Snapshot
	if err := decodeStrict(data, &snapshot); err != nil {
		return Snapshot{}, fmt.Errorf("%w: %v", ErrInvalidSnapshot, err)
	}
	if err := validateSnapshotJSONTypes(data); err != nil {
		return Snapshot{}, fmt.Errorf("%w: %v", ErrInvalidSnapshot, err)
	}
	if err := validateSnapshotShape(snapshot); err != nil {
		return Snapshot{}, err
	}
	return snapshot, nil
}

func validateProfileJSONTypes(data []byte) error {
	object, err := rawObject(data)
	if err != nil {
		return err
	}
	for _, field := range []string{"schema_version", "profile_id", "entries"} {
		if raw, ok := object[field]; !ok || isJSONNull(raw) {
			return fmt.Errorf("profile field is missing or null")
		}
	}
	if err := requireRawString(object["schema_version"]); err != nil {
		return err
	}
	if err := requireRawString(object["profile_id"]); err != nil {
		return err
	}
	var entries []json.RawMessage
	if err := json.Unmarshal(object["entries"], &entries); err != nil || entries == nil {
		return fmt.Errorf("profile entries must be an array")
	}
	for _, raw := range entries {
		entry, err := rawObject(raw)
		if err != nil {
			return err
		}
		for _, field := range []string{"name", "validator", "max_bytes", "required"} {
			if value, ok := entry[field]; !ok || isJSONNull(value) {
				return fmt.Errorf("profile entry field is missing or null")
			}
		}
		for _, field := range []string{"name", "validator"} {
			if err := requireRawString(entry[field]); err != nil {
				return err
			}
		}
		var maxBytes int
		if err := json.Unmarshal(entry["max_bytes"], &maxBytes); err != nil {
			return fmt.Errorf("profile max_bytes must be an integer")
		}
		var required bool
		if err := json.Unmarshal(entry["required"], &required); err != nil {
			return fmt.Errorf("profile required must be boolean")
		}
		for _, field := range []string{"default", "description"} {
			if raw, ok := entry[field]; ok {
				if isJSONNull(raw) {
					return fmt.Errorf("profile optional field is null")
				}
				if err := requireRawString(raw); err != nil {
					return err
				}
			}
		}
	}
	return nil
}

func validateSnapshotJSONTypes(data []byte) error {
	object, err := rawObject(data)
	if err != nil {
		return err
	}
	for _, field := range []string{"schema_version", "profile_id", "profile_fingerprint", "producer_version", "provenance", "captured_at", "entries", "missing_optional", "content_fingerprint"} {
		if raw, ok := object[field]; !ok || isJSONNull(raw) {
			return fmt.Errorf("snapshot field is missing or null")
		}
	}
	for _, field := range []string{"schema_version", "profile_id", "profile_fingerprint", "producer_version", "captured_at", "content_fingerprint"} {
		if err := requireRawString(object[field]); err != nil {
			return err
		}
	}
	provenance, err := rawObject(object["provenance"])
	if err != nil {
		return err
	}
	if raw, ok := provenance["context"]; !ok || isJSONNull(raw) {
		return fmt.Errorf("snapshot provenance context is missing or null")
	}
	if err := requireRawString(provenance["context"]); err != nil {
		return err
	}
	for _, field := range []string{"host", "shell"} {
		if raw, ok := provenance[field]; ok {
			if isJSONNull(raw) {
				return fmt.Errorf("snapshot provenance field is null")
			}
			if err := requireRawString(raw); err != nil {
				return err
			}
		}
	}
	var entries []json.RawMessage
	if err := json.Unmarshal(object["entries"], &entries); err != nil || entries == nil {
		return fmt.Errorf("snapshot entries must be an array")
	}
	for _, raw := range entries {
		entry, err := rawObject(raw)
		if err != nil {
			return err
		}
		for _, field := range []string{"name", "validator", "value", "source"} {
			if value, ok := entry[field]; !ok || isJSONNull(value) {
				return fmt.Errorf("snapshot entry field is missing or null")
			}
			if err := requireRawString(entry[field]); err != nil {
				return err
			}
		}
	}
	var missing []json.RawMessage
	if err := json.Unmarshal(object["missing_optional"], &missing); err != nil || missing == nil {
		return fmt.Errorf("snapshot missing_optional must be an array")
	}
	for _, raw := range missing {
		if err := requireRawString(raw); err != nil {
			return err
		}
	}
	return nil
}

func rawObject(data []byte) (map[string]json.RawMessage, error) {
	var object map[string]json.RawMessage
	if err := json.Unmarshal(data, &object); err != nil || object == nil {
		return nil, fmt.Errorf("JSON object required")
	}
	return object, nil
}

func requireRawString(data json.RawMessage) error {
	var value string
	if err := json.Unmarshal(data, &value); err != nil {
		return fmt.Errorf("JSON string required")
	}
	return nil
}

func isJSONNull(data json.RawMessage) bool {
	return bytes.Equal(bytes.TrimSpace(data), []byte("null"))
}

// MarshalSnapshot returns compact canonical snapshot JSON with an LF final
// newline. Metadata remains in declared schema order and entries are sorted.
func MarshalSnapshot(snapshot Snapshot) ([]byte, error) {
	if err := validateSnapshotShape(snapshot); err != nil {
		return nil, err
	}
	canonical := cloneSnapshot(snapshot)
	sortSnapshotEntries(&canonical)
	if canonical.Entries == nil {
		canonical.Entries = []SnapshotEntry{}
	}
	if canonical.MissingOptional == nil {
		canonical.MissingOptional = []string{}
	}
	return marshalCanonical(canonical)
}

func marshalCanonical(value any) ([]byte, error) {
	encoded, err := json.Marshal(value)
	if err != nil {
		return nil, err
	}
	if !utf8.Valid(encoded) {
		return nil, fmt.Errorf("canonical JSON is not valid UTF-8")
	}
	return append(encoded, '\n'), nil
}

func decodeStrict(data []byte, target any) error {
	if !utf8.Valid(data) {
		return fmt.Errorf("JSON is not valid UTF-8")
	}
	if err := rejectDuplicateKeys(data); err != nil {
		return err
	}
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(target); err != nil {
		return err
	}
	var extra any
	if err := decoder.Decode(&extra); err != io.EOF {
		if err == nil {
			return fmt.Errorf("trailing JSON value")
		}
		return fmt.Errorf("trailing JSON: %v", err)
	}
	return nil
}

func rejectDuplicateKeys(data []byte) error {
	decoder := json.NewDecoder(bytes.NewReader(data))
	var walk func() error
	walk = func() error {
		token, err := decoder.Token()
		if err != nil {
			return err
		}
		delim, isDelim := token.(json.Delim)
		if !isDelim {
			return nil
		}
		switch delim {
		case '{':
			seen := make(map[string]struct{})
			for decoder.More() {
				keyToken, err := decoder.Token()
				if err != nil {
					return err
				}
				key, ok := keyToken.(string)
				if !ok {
					return fmt.Errorf("object key is not a string")
				}
				if _, exists := seen[key]; exists {
					return fmt.Errorf("duplicate JSON object key")
				}
				seen[key] = struct{}{}
				if err := walk(); err != nil {
					return err
				}
			}
			_, err = decoder.Token()
			return err
		case '[':
			for decoder.More() {
				if err := walk(); err != nil {
					return err
				}
			}
			_, err = decoder.Token()
			return err
		default:
			return fmt.Errorf("unexpected JSON delimiter")
		}
	}
	if err := walk(); err != nil {
		return err
	}
	if _, err := decoder.Token(); err != io.EOF {
		if err == nil {
			return fmt.Errorf("trailing JSON value")
		}
		return err
	}
	return nil
}

func profileFingerprint(profile Profile) (string, error) {
	if err := ValidateProfile(profile); err != nil {
		return "", err
	}
	entries := sortedProfileEntries(profile)
	if entries == nil {
		entries = []ProfileEntry{}
	}
	type identityEntry struct {
		Name      string `json:"name"`
		Validator string `json:"validator"`
		MaxBytes  int    `json:"max_bytes"`
		Required  bool   `json:"required"`
		Default   string `json:"default"`
	}
	type identity struct {
		SchemaVersion string          `json:"schema_version"`
		ProfileID     string          `json:"profile_id"`
		Entries       []identityEntry `json:"entries"`
	}
	identityEntries := make([]identityEntry, 0, len(entries))
	for _, entry := range entries {
		identityEntries = append(identityEntries, identityEntry{
			Name: entry.Name, Validator: entry.Validator, MaxBytes: entry.MaxBytes,
			Required: entry.Required, Default: entry.Default,
		})
	}
	payload := identity{SchemaVersion: profile.SchemaVersion, ProfileID: profile.ProfileID, Entries: identityEntries}
	encoded, err := json.Marshal(payload)
	if err != nil {
		return "", err
	}
	digest := sha256.Sum256(encoded)
	return hex.EncodeToString(digest[:]), nil
}

// FingerprintProfile returns the semantic profile fingerprint, or an empty
// string when the profile is invalid.
func FingerprintProfile(profile Profile) string {
	fingerprint, _ := profileFingerprint(profile)
	return fingerprint
}

type snapshotFingerprintPayload struct {
	SchemaVersion      string          `json:"schema_version"`
	ProfileID          string          `json:"profile_id"`
	ProfileFingerprint string          `json:"profile_fingerprint"`
	Entries            []SnapshotEntry `json:"entries"`
}

func snapshotFingerprint(snapshot Snapshot) (string, error) {
	entries := append([]SnapshotEntry(nil), snapshot.Entries...)
	if entries == nil {
		entries = []SnapshotEntry{}
	}
	sort.Slice(entries, func(i, j int) bool { return entries[i].Name < entries[j].Name })
	payload := snapshotFingerprintPayload{
		SchemaVersion:      snapshot.SchemaVersion,
		ProfileID:          snapshot.ProfileID,
		ProfileFingerprint: snapshot.ProfileFingerprint,
		Entries:            entries,
	}
	encoded, err := json.Marshal(payload)
	if err != nil {
		return "", err
	}
	digest := sha256.Sum256(encoded)
	return hex.EncodeToString(digest[:]), nil
}

// FingerprintSnapshot returns the timestamp/path-independent content
// fingerprint, or an empty string when the snapshot cannot be fingerprinted.
func FingerprintSnapshot(snapshot Snapshot) string {
	fingerprint, _ := snapshotFingerprint(snapshot)
	return fingerprint
}

func validateSnapshotShape(snapshot Snapshot) error {
	if snapshot.SchemaVersion != SnapshotSchemaV1 {
		return invalidSnapshot("unsupported schema version")
	}
	if err := validateProfileID(snapshot.ProfileID); err != nil {
		return invalidSnapshot("profile id is invalid")
	}
	if snapshot.ProfileFingerprint == "" || !isHexFingerprint(snapshot.ProfileFingerprint) {
		return invalidSnapshot("profile fingerprint is invalid")
	}
	if snapshot.ProducerVersion == "" || len([]byte(snapshot.ProducerVersion)) > 1024 || !utf8.ValidString(snapshot.ProducerVersion) || hasBannedControl(snapshot.ProducerVersion) {
		return invalidSnapshot("producer version is invalid")
	}
	if snapshot.CapturedAt.IsZero() {
		return invalidSnapshot("capture timestamp is missing")
	}
	if err := validateProvenance(snapshot.Provenance); err != nil {
		return err
	}
	seen := make(map[string]struct{}, len(snapshot.Entries))
	for _, entry := range snapshot.Entries {
		if !validateName(entry.Name) {
			return invalidSnapshot("snapshot entry has an invalid name")
		}
		if sensitiveName(entry.Name) {
			return fmt.Errorf("%w: %w: snapshot entry name", ErrInvalidSnapshot, ErrSensitiveName)
		}
		if _, ok := seen[entry.Name]; ok {
			return invalidSnapshot("snapshot contains duplicate names")
		}
		seen[entry.Name] = struct{}{}
		if _, ok := knownValidators[entry.Validator]; !ok {
			return invalidSnapshot("snapshot entry has an unknown validator")
		}
		if !utf8.ValidString(entry.Value) {
			return invalidSnapshot("snapshot entry value is not valid UTF-8")
		}
		if entry.Source != sourceCapture {
			return invalidSnapshot("snapshot entry source is not canonical")
		}
		if !tokenPattern.MatchString(entry.Source) {
			return invalidSnapshot("snapshot entry source is invalid")
		}
	}
	for i, name := range snapshot.MissingOptional {
		if !validateName(name) {
			return invalidSnapshot("missing optional name is invalid")
		}
		if i > 0 && snapshot.MissingOptional[i-1] >= name {
			return invalidSnapshot("missing optional names are not sorted")
		}
	}
	if snapshot.ContentFingerprint == "" || !isHexFingerprint(snapshot.ContentFingerprint) {
		return invalidSnapshot("content fingerprint is invalid")
	}
	computed, err := snapshotFingerprint(snapshot)
	if err != nil || computed != snapshot.ContentFingerprint {
		return fmt.Errorf("%w: %w", ErrFingerprint, ErrInvalidSnapshot)
	}
	return nil
}

func isHexFingerprint(value string) bool {
	if len(value) != 64 {
		return false
	}
	for _, char := range value {
		if !((char >= '0' && char <= '9') || (char >= 'a' && char <= 'f')) {
			return false
		}
	}
	return true
}

func cloneSnapshot(snapshot Snapshot) Snapshot {
	clone := snapshot
	clone.Entries = append([]SnapshotEntry(nil), snapshot.Entries...)
	clone.MissingOptional = append([]string(nil), snapshot.MissingOptional...)
	if clone.Entries == nil {
		clone.Entries = []SnapshotEntry{}
	}
	if clone.MissingOptional == nil {
		clone.MissingOptional = []string{}
	}
	return clone
}

func sortSnapshotEntries(snapshot *Snapshot) {
	sort.Slice(snapshot.Entries, func(i, j int) bool { return snapshot.Entries[i].Name < snapshot.Entries[j].Name })
	sort.Strings(snapshot.MissingOptional)
}

func nowUTC(clock Clock) time.Time {
	if clock == nil {
		return time.Now().UTC()
	}
	return clock.Now().UTC()
}
