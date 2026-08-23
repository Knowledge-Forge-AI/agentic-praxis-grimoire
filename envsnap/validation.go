package envsnap

import (
	"fmt"
	"net/url"
	"regexp"
	"sort"
	"strings"
	"unicode/utf8"
)

var (
	environmentNamePattern = regexp.MustCompile(`^[A-Za-z_][A-Za-z0-9_]*$`)
	profileIDPattern       = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9._-]*$`)
	tokenPattern           = regexp.MustCompile(`^[A-Za-z0-9._-]+$`)
	hostPattern            = regexp.MustCompile(`^[A-Za-z0-9._:-]+$`)
	integerPattern         = regexp.MustCompile(`^-?[0-9]+$`)
)

var knownValidators = map[string]struct{}{
	string(ValidatorBool):      {},
	string(ValidatorCommand):   {},
	string(ValidatorHost):      {},
	string(ValidatorInteger):   {},
	string(ValidatorPath):      {},
	string(ValidatorPathList):  {},
	string(ValidatorPort):      {},
	string(ValidatorRawSafe):   {},
	string(ValidatorToken):     {},
	string(ValidatorTokenList): {},
	string(ValidatorURI):       {},
	string(ValidatorURIOrPath): {},
}

// ValidateProfile validates the strict v1 profile contract and all declared
// defaults. Description wording is deliberately not part of profile identity.
func ValidateProfile(profile Profile) error {
	if profile.SchemaVersion != ProfileSchemaV1 {
		return invalidProfile("unsupported schema version")
	}
	if err := validateProfileID(profile.ProfileID); err != nil {
		return err
	}
	seen := make(map[string]struct{}, len(profile.Entries))
	for _, entry := range profile.Entries {
		if err := validateProfileEntry(entry, seen); err != nil {
			return err
		}
	}
	return nil
}

func validateProfileID(id string) error {
	if !utf8.ValidString(id) || hasBannedControl(id) {
		return invalidProfile("profile id contains invalid text")
	}
	if id == "" || id == "." || id == ".." || !profileIDPattern.MatchString(id) {
		return invalidProfile("profile id is not path-safe")
	}
	if len(id) > 128 {
		return invalidProfile("profile id is too long")
	}
	return nil
}

func validateProfileEntry(entry ProfileEntry, seen map[string]struct{}) error {
	if !utf8.ValidString(entry.Name) || hasBannedControl(entry.Name) ||
		!environmentNamePattern.MatchString(entry.Name) {
		return invalidProfile("profile entry has an invalid environment name")
	}
	if _, ok := seen[entry.Name]; ok {
		return invalidProfile("profile contains duplicate environment names")
	}
	seen[entry.Name] = struct{}{}
	if sensitiveName(entry.Name) {
		return fmt.Errorf("%w: %w: %s", ErrInvalidProfile, ErrSensitiveName, entry.Name)
	}
	if _, ok := knownValidators[entry.Validator]; !ok {
		return invalidProfile("profile entry has an unknown validator")
	}
	if entry.MaxBytes <= 0 {
		return invalidProfile("profile entry max_bytes must be positive")
	}
	if !utf8.ValidString(entry.Validator) || hasBannedControl(entry.Validator) ||
		!utf8.ValidString(entry.Default) || hasBannedControl(entry.Default) ||
		!utf8.ValidString(entry.Description) || hasBannedControl(entry.Description) {
		return invalidProfile("profile entry contains invalid text")
	}
	if entry.Default != "" {
		if err := validateValue(entry.Default, entry.Validator, entry.MaxBytes); err != nil {
			return invalidProfile("profile entry default failed validation")
		}
	}
	return nil
}

func validateProvenance(provenance SnapshotProvenance) error {
	if provenance.Context == "" || len([]byte(provenance.Context)) > 1024 ||
		!utf8.ValidString(provenance.Context) || hasBannedControl(provenance.Context) {
		return invalidSnapshot("capture provenance context is required")
	}
	if len([]byte(provenance.Host)) > 1024 || len([]byte(provenance.Shell)) > 1024 ||
		!utf8.ValidString(provenance.Host) || hasBannedControl(provenance.Host) ||
		!utf8.ValidString(provenance.Shell) || hasBannedControl(provenance.Shell) {
		return invalidSnapshot("provenance contains invalid text")
	}
	return nil
}

// ValidateValue applies one of the twelve frozen validator families. Errors
// never include the value or a value-derived fragment.
func ValidateValue(value, validator string, maxBytes int) error {
	return validateValue(value, validator, maxBytes)
}

func validateValue(value, validator string, maxBytes int) error {
	if maxBytes <= 0 {
		return invalidValue("max_bytes must be positive")
	}
	if !utf8.ValidString(value) {
		return invalidValue("value is not valid UTF-8")
	}
	if len([]byte(value)) > maxBytes {
		return invalidValue("value exceeds max_bytes")
	}
	if hasBannedControl(value) {
		return invalidValue("value contains a banned control character")
	}
	if strings.EqualFold(value, "null") {
		return invalidValue("value is denied")
	}
	if _, ok := knownValidators[validator]; !ok {
		return invalidValue("unknown validator")
	}

	switch validator {
	case string(ValidatorRawSafe), string(ValidatorCommand):
		return nil
	case string(ValidatorToken):
		if !tokenPattern.MatchString(value) {
			return invalidValue("value has invalid token characters")
		}
	case string(ValidatorTokenList):
		for _, token := range strings.Split(value, ",") {
			if !tokenPattern.MatchString(token) {
				return invalidValue("value has invalid token-list syntax")
			}
		}
	case string(ValidatorPath):
		if strings.TrimSpace(value) == "" {
			return invalidValue("path is empty")
		}
	case string(ValidatorPathList):
		for _, part := range strings.Split(value, ":") {
			if strings.TrimSpace(part) == "" {
				return invalidValue("path-list contains an empty entry")
			}
		}
	case string(ValidatorURI):
		if !isURI(value) {
			return invalidValue("value is not an absolute URI")
		}
	case string(ValidatorURIOrPath):
		if !isURI(value) && strings.TrimSpace(value) == "" {
			return invalidValue("value is neither a URI nor a path")
		}
	case string(ValidatorHost):
		if !hostPattern.MatchString(value) {
			return invalidValue("value is not host-like")
		}
	case string(ValidatorPort):
		if !integerPattern.MatchString(value) || strings.HasPrefix(value, "-") {
			return invalidValue("value is not a numeric port")
		}
		port := 0
		for _, digit := range value {
			port = port*10 + int(digit-'0')
			if port > 65535 {
				return invalidValue("port is out of range")
			}
		}
		if port < 1 {
			return invalidValue("port is out of range")
		}
	case string(ValidatorBool):
		if !isBool(value) {
			return invalidValue("value is not boolean")
		}
	case string(ValidatorInteger):
		if !integerPattern.MatchString(value) {
			return invalidValue("value is not an integer")
		}
	}
	return nil
}

func isBool(value string) bool {
	switch strings.ToLower(value) {
	case "0", "1", "false", "no", "true", "yes":
		return true
	default:
		return false
	}
}

func isURI(value string) bool {
	parsed, err := url.Parse(value)
	return err == nil && parsed.Scheme != "" && (parsed.Host != "" || parsed.Path != "" || parsed.Opaque != "")
}

func hasBannedControl(value string) bool {
	for _, char := range value {
		if char < 32 || char == 127 {
			return true
		}
	}
	return false
}

// sensitiveName is deliberately token-aware. It does not reject bare AUTH or
// KEY, and SSH_AUTH_SOCK is a documented socket capability rather than secret
// material and is therefore explicitly permitted.
func sensitiveName(name string) bool {
	if strings.EqualFold(name, "SSH_AUTH_SOCK") {
		return false
	}
	upper := strings.ToUpper(name)
	parts := strings.Split(upper, "_")
	for _, part := range parts {
		switch part {
		case "PASSWORD", "PASSWD", "PASSPHRASE", "PASS_PHRASE", "SECRET", "TOKEN", "COOKIE", "SESSION", "CREDENTIAL", "CREDENTIALS":
			return true
		}
	}
	for _, part := range parts {
		if part == "PRIVATEKEY" {
			return true
		}
	}
	for index := 0; index+1 < len(parts); index++ {
		phrase := parts[index] + "_" + parts[index+1]
		switch phrase {
		case "API_KEY", "ACCESS_KEY", "PRIVATE_KEY", "AUTH_TOKEN", "AUTH_SECRET", "SESSION_TOKEN", "CLIENT_SECRET":
			return true
		}
	}
	return false
}

func sortedProfileEntries(profile Profile) []ProfileEntry {
	entries := append([]ProfileEntry(nil), profile.Entries...)
	sort.Slice(entries, func(i, j int) bool { return entries[i].Name < entries[j].Name })
	return entries
}

func profileEntryMap(profile Profile) map[string]ProfileEntry {
	entries := make(map[string]ProfileEntry, len(profile.Entries))
	for _, entry := range profile.Entries {
		entries[entry.Name] = entry
	}
	return entries
}

func validateName(name string) bool {
	return utf8.ValidString(name) && environmentNamePattern.MatchString(name)
}
