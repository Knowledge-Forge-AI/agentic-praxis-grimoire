package footprint

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"sort"
	"strings"
	"unicode/utf8"
)

// CanonicalJSON returns the canonical JSON encoding for one of the public
// footprint schema values.  The encoding is compact, uses the declared Go
// struct field order, normalizes set-like slices into stable order, and ends
// in exactly one LF.  Unknown values are rejected instead of being encoded as
// an accidental private schema.
func CanonicalJSON(value any) ([]byte, error) {
	switch typed := value.(type) {
	case Record:
		return typed.CanonicalJSON()
	case *Record:
		if typed == nil {
			return nil, invalid(ErrInvalidRecord, ErrInvalidType, "nil record")
		}
		return typed.CanonicalJSON()
	case Comparison:
		return typed.CanonicalJSON()
	case *Comparison:
		if typed == nil {
			return nil, invalid(ErrInvalidComparison, ErrInvalidType, "nil comparison")
		}
		return typed.CanonicalJSON()
	case Projection:
		return typed.CanonicalJSON()
	case *Projection:
		if typed == nil {
			return nil, invalid(ErrInvalidProjection, ErrInvalidType, "nil projection")
		}
		return typed.CanonicalJSON()
	case ComponentRegistry:
		return typed.CanonicalJSON()
	case *ComponentRegistry:
		if typed == nil {
			return nil, invalid(ErrInvalidRegistry, ErrInvalidType, "nil component registry")
		}
		return typed.CanonicalJSON()
	case ControlMapping:
		return typed.CanonicalJSON()
	case *ControlMapping:
		if typed == nil {
			return nil, invalid(ErrInvalidControlMapping, ErrInvalidType, "nil control mapping")
		}
		return typed.CanonicalJSON()
	case interface{ CanonicalJSON() ([]byte, error) }:
		return typed.CanonicalJSON()
	default:
		return nil, invalid(ErrInvalidType, nil, "unsupported canonical JSON value %T", value)
	}
}

// MarshalRecord is an explicit name for the canonical record encoder.
func MarshalRecord(record Record) ([]byte, error) { return record.CanonicalJSON() }

// MarshalFootprint is an alias for MarshalRecord.
func MarshalFootprint(record Footprint) ([]byte, error) { return record.CanonicalJSON() }

// MarshalComparison is an explicit name for the canonical comparison encoder.
func MarshalComparison(comparison Comparison) ([]byte, error) {
	return comparison.CanonicalJSON()
}

// MarshalProjection is an explicit name for the canonical projection encoder.
func MarshalProjection(projection Projection) ([]byte, error) {
	return projection.CanonicalJSON()
}

// MarshalComponentRegistry is an explicit name for the canonical registry
// encoder.
func MarshalComponentRegistry(registry ComponentRegistry) ([]byte, error) {
	return registry.CanonicalJSON()
}

// MarshalControlMapping is an explicit name for the canonical mapping encoder.
func MarshalControlMapping(mapping ControlMapping) ([]byte, error) {
	return mapping.CanonicalJSON()
}

func (record Record) CanonicalJSON() ([]byte, error) {
	if err := validateRecord(record); err != nil {
		return nil, err
	}
	return marshalCanonical(normalizeRecord(record))
}

func (comparison Comparison) CanonicalJSON() ([]byte, error) {
	if err := validateComparison(comparison); err != nil {
		return nil, err
	}
	return marshalCanonical(normalizeComparison(comparison))
}

func (projection Projection) CanonicalJSON() ([]byte, error) {
	if err := validateProjection(projection); err != nil {
		return nil, err
	}
	return marshalCanonical(normalizeProjection(projection))
}

func (registry ComponentRegistry) CanonicalJSON() ([]byte, error) {
	if err := validateRegistry(registry); err != nil {
		return nil, err
	}
	return marshalCanonical(normalizeRegistry(registry))
}

func (mapping ControlMapping) CanonicalJSON() ([]byte, error) {
	if err := validateControlMapping(mapping); err != nil {
		return nil, err
	}
	return marshalCanonical(normalizeControlMapping(mapping))
}

// Fingerprint returns the domain-separated SHA-256 identity for a supported
// canonical value, or an empty string when the value is invalid.
func Fingerprint(value any) string {
	switch typed := value.(type) {
	case Record:
		return FingerprintRecord(typed)
	case *Record:
		if typed != nil {
			return FingerprintRecord(*typed)
		}
	case Comparison:
		return FingerprintComparison(typed)
	case *Comparison:
		if typed != nil {
			return FingerprintComparison(*typed)
		}
	case Projection:
		return FingerprintProjection(typed)
	case *Projection:
		if typed != nil {
			return FingerprintProjection(*typed)
		}
	case ComponentRegistry:
		return FingerprintComponentRegistry(typed)
	case *ComponentRegistry:
		if typed != nil {
			return FingerprintComponentRegistry(*typed)
		}
	case ControlMapping:
		return FingerprintControlMapping(typed)
	case *ControlMapping:
		if typed != nil {
			return FingerprintControlMapping(*typed)
		}
	}
	return ""
}

// FingerprintRecord returns a record identity with the fp-sha256 domain
// prefix.
func FingerprintRecord(record Record) string {
	canonical, err := record.CanonicalJSON()
	if err != nil {
		return ""
	}
	return domainFingerprint("fp-sha256:", FootprintSchemaV1, canonical)
}

// Fingerprint returns the same record identity as FingerprintRecord.
func (record Record) Fingerprint() string { return FingerprintRecord(record) }

// FingerprintFootprint is an alias for FingerprintRecord.
func FingerprintFootprint(record Footprint) string { return FingerprintRecord(record) }

// FingerprintComparison returns a comparison identity with the cmp-sha256
// domain prefix.
func FingerprintComparison(comparison Comparison) string {
	canonical, err := comparison.CanonicalJSON()
	if err != nil {
		return ""
	}
	return domainFingerprint("cmp-sha256:", ComparisonSchemaV1, canonical)
}

// Fingerprint returns the same comparison identity as FingerprintComparison.
func (comparison Comparison) Fingerprint() string { return FingerprintComparison(comparison) }

// FingerprintProjection returns a projection identity with the proj-sha256
// domain prefix.
func FingerprintProjection(projection Projection) string {
	canonical, err := projection.CanonicalJSON()
	if err != nil {
		return ""
	}
	return domainFingerprint("proj-sha256:", ProjectionSchemaV1, canonical)
}

// Fingerprint returns the same projection identity as FingerprintProjection.
func (projection Projection) Fingerprint() string { return FingerprintProjection(projection) }

// FingerprintComponentRegistry returns the registry identity.  Registries are
// footprint vocabulary artifacts, so they use the general fp-sha256 domain.
func FingerprintComponentRegistry(registry ComponentRegistry) string {
	canonical, err := registry.CanonicalJSON()
	if err != nil {
		return ""
	}
	return domainFingerprint("fp-sha256:", ComponentRegistrySchemaV1, canonical)
}

// Fingerprint returns the same identity as FingerprintComponentRegistry.
func (registry ComponentRegistry) Fingerprint() string { return FingerprintComponentRegistry(registry) }

// FingerprintControlMapping returns the control-mapping identity.  Mappings
// are footprint vocabulary artifacts, so they use the general fp-sha256
// domain.
func FingerprintControlMapping(mapping ControlMapping) string {
	canonical, err := mapping.CanonicalJSON()
	if err != nil {
		return ""
	}
	return domainFingerprint("fp-sha256:", ControlMappingSchemaV1, canonical)
}

// Fingerprint returns the same identity as FingerprintControlMapping.
func (mapping ControlMapping) Fingerprint() string { return FingerprintControlMapping(mapping) }

// FingerprintWithError is useful to adapters that need to distinguish an
// invalid value from a valid value whose identity happens to be empty.
func FingerprintWithError(value any) (string, error) {
	canonical, err := CanonicalJSON(value)
	if err != nil {
		return "", err
	}
	schema, prefix, err := identityDomain(value)
	if err != nil {
		return "", err
	}
	return domainFingerprint(prefix, schema, canonical), nil
}

func identityDomain(value any) (schema, prefix string, err error) {
	switch value.(type) {
	case Record, *Record:
		return FootprintSchemaV1, "fp-sha256:", nil
	case Comparison, *Comparison:
		return ComparisonSchemaV1, "cmp-sha256:", nil
	case Projection, *Projection:
		return ProjectionSchemaV1, "proj-sha256:", nil
	case ComponentRegistry, *ComponentRegistry:
		return ComponentRegistrySchemaV1, "fp-sha256:", nil
	case ControlMapping, *ControlMapping:
		return ControlMappingSchemaV1, "fp-sha256:", nil
	default:
		return "", "", invalid(ErrInvalidType, nil, "unsupported fingerprint value %T", value)
	}
}

func domainFingerprint(prefix, schema string, canonical []byte) string {
	hash := sha256.New()
	_, _ = hash.Write([]byte(schema))
	_, _ = hash.Write([]byte{0})
	_, _ = hash.Write(canonical)
	return prefix + hex.EncodeToString(hash.Sum(nil))
}

func marshalCanonical(value any) ([]byte, error) {
	encoded, err := json.Marshal(value)
	if err != nil {
		return nil, err
	}
	if !utf8.Valid(encoded) {
		return nil, fmt.Errorf("%w: canonical JSON is not valid UTF-8", ErrInvalidUTF8)
	}
	return append(encoded, '\n'), nil
}

// DecodeRecord strictly decodes one canonical context-footprint record.
func DecodeRecord(data []byte) (Record, error) {
	var record Record
	if err := strictJSON(data); err != nil {
		return record, invalid(ErrInvalidRecord, err, "record JSON is invalid")
	}
	if err := shapeRecord(data); err != nil {
		return record, invalid(ErrInvalidRecord, err, "record JSON shape is invalid")
	}
	if err := decodeTyped(data, &record); err != nil {
		return Record{}, invalid(ErrInvalidRecord, err, "record JSON values are invalid")
	}
	if err := validateRecord(record); err != nil {
		return Record{}, err
	}
	canonical, err := record.CanonicalJSON()
	if err != nil {
		return Record{}, err
	}
	if !bytes.Equal(data, canonical) {
		return Record{}, invalid(ErrInvalidRecord, ErrNonCanonical, "record JSON is not canonical")
	}
	return record, nil
}

// DecodeFootprint is an alias for DecodeRecord.
func DecodeFootprint(data []byte) (Footprint, error) { return DecodeRecord(data) }

// DecodeMeasurement is an alias for DecodeRecord.
func DecodeMeasurement(data []byte) (Record, error) { return DecodeRecord(data) }

// DecodeComparison strictly decodes one canonical integer comparison.
func DecodeComparison(data []byte) (Comparison, error) {
	var comparison Comparison
	if err := strictJSON(data); err != nil {
		return comparison, invalid(ErrInvalidComparison, err, "comparison JSON is invalid")
	}
	if err := shapeComparison(data); err != nil {
		return comparison, invalid(ErrInvalidComparison, err, "comparison JSON shape is invalid")
	}
	if err := decodeTyped(data, &comparison); err != nil {
		return Comparison{}, invalid(ErrInvalidComparison, err, "comparison JSON values are invalid")
	}
	if err := validateComparison(comparison); err != nil {
		return Comparison{}, err
	}
	canonical, err := comparison.CanonicalJSON()
	if err != nil {
		return Comparison{}, err
	}
	if !bytes.Equal(data, canonical) {
		return Comparison{}, invalid(ErrInvalidComparison, ErrNonCanonical, "comparison JSON is not canonical")
	}
	return comparison, nil
}

// DecodeProjection strictly decodes one canonical source-bound projection.
func DecodeProjection(data []byte) (Projection, error) {
	var projection Projection
	if err := strictJSON(data); err != nil {
		return projection, invalid(ErrInvalidProjection, err, "projection JSON is invalid")
	}
	if err := shapeProjection(data); err != nil {
		return projection, invalid(ErrInvalidProjection, err, "projection JSON shape is invalid")
	}
	if err := decodeTyped(data, &projection); err != nil {
		return Projection{}, invalid(ErrInvalidProjection, err, "projection JSON values are invalid")
	}
	if err := validateProjection(projection); err != nil {
		return Projection{}, err
	}
	canonical, err := projection.CanonicalJSON()
	if err != nil {
		return Projection{}, err
	}
	if !bytes.Equal(data, canonical) {
		return Projection{}, invalid(ErrInvalidProjection, ErrNonCanonical, "projection JSON is not canonical")
	}
	return projection, nil
}

// DecodeComponentRegistry strictly decodes the complete built-in registry.
func DecodeComponentRegistry(data []byte) (ComponentRegistry, error) {
	var registry ComponentRegistry
	if err := strictJSON(data); err != nil {
		return registry, invalid(ErrInvalidRegistry, err, "component registry JSON is invalid")
	}
	if err := shapeRegistry(data); err != nil {
		return registry, invalid(ErrInvalidRegistry, err, "component registry JSON shape is invalid")
	}
	if err := decodeTyped(data, &registry); err != nil {
		return ComponentRegistry{}, invalid(ErrInvalidRegistry, err, "component registry JSON values are invalid")
	}
	if err := validateRegistry(registry); err != nil {
		return ComponentRegistry{}, err
	}
	canonical, err := registry.CanonicalJSON()
	if err != nil {
		return ComponentRegistry{}, err
	}
	if !bytes.Equal(data, canonical) {
		return ComponentRegistry{}, invalid(ErrInvalidRegistry, ErrNonCanonical, "component registry JSON is not canonical")
	}
	return registry, nil
}

// DecodeRegistry is an alias for DecodeComponentRegistry.
func DecodeRegistry(data []byte) (ComponentRegistry, error) { return DecodeComponentRegistry(data) }

// DecodeControlMapping strictly decodes the complete built-in mapping.
func DecodeControlMapping(data []byte) (ControlMapping, error) {
	var mapping ControlMapping
	if err := strictJSON(data); err != nil {
		return mapping, invalid(ErrInvalidControlMapping, err, "control mapping JSON is invalid")
	}
	if err := shapeMapping(data); err != nil {
		return mapping, invalid(ErrInvalidControlMapping, err, "control mapping JSON shape is invalid")
	}
	if err := decodeTyped(data, &mapping); err != nil {
		return ControlMapping{}, invalid(ErrInvalidControlMapping, err, "control mapping JSON values are invalid")
	}
	if err := validateControlMapping(mapping); err != nil {
		return ControlMapping{}, err
	}
	canonical, err := mapping.CanonicalJSON()
	if err != nil {
		return ControlMapping{}, err
	}
	if !bytes.Equal(data, canonical) {
		return ControlMapping{}, invalid(ErrInvalidControlMapping, ErrNonCanonical, "control mapping JSON is not canonical")
	}
	return mapping, nil
}

// DecodeCapacityControlMapping is an alias for DecodeControlMapping.
func DecodeCapacityControlMapping(data []byte) (CapacityControlMapping, error) {
	return DecodeControlMapping(data)
}

func decodeTyped(data []byte, destination any) error {
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.DisallowUnknownFields()
	decoder.UseNumber()
	if err := decoder.Decode(destination); err != nil {
		return fmt.Errorf("%w: %v", ErrInvalidType, err)
	}
	if _, err := decoder.Token(); err != io.EOF {
		if err == nil {
			return ErrTrailingData
		}
		return fmt.Errorf("%w: %v", ErrTrailingData, err)
	}
	return nil
}

func strictJSON(data []byte) error {
	if !utf8.Valid(data) {
		return ErrInvalidUTF8
	}
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.UseNumber()
	if err := walkJSON(decoder); err != nil {
		return err
	}
	if _, err := decoder.Token(); err != io.EOF {
		if err == nil {
			return ErrTrailingData
		}
		return fmt.Errorf("%w: %v", ErrMalformedJSON, err)
	}
	return nil
}

func walkJSON(decoder *json.Decoder) error {
	token, err := decoder.Token()
	if err != nil {
		return fmt.Errorf("%w: %v", ErrMalformedJSON, err)
	}
	delimiter, ok := token.(json.Delim)
	if !ok {
		return nil
	}
	switch delimiter {
	case '{':
		seen := map[string]struct{}{}
		for decoder.More() {
			keyToken, err := decoder.Token()
			if err != nil {
				return fmt.Errorf("%w: %v", ErrMalformedJSON, err)
			}
			key, ok := keyToken.(string)
			if !ok {
				return fmt.Errorf("%w: object key is not a string", ErrMalformedJSON)
			}
			if _, exists := seen[key]; exists {
				return fmt.Errorf("%w: %q", ErrDuplicateField, key)
			}
			seen[key] = struct{}{}
			if err := walkJSON(decoder); err != nil {
				return err
			}
		}
		if end, err := decoder.Token(); err != nil || end != json.Delim('}') {
			return fmt.Errorf("%w: unterminated object", ErrMalformedJSON)
		}
	case '[':
		for decoder.More() {
			if err := walkJSON(decoder); err != nil {
				return err
			}
		}
		if end, err := decoder.Token(); err != nil || end != json.Delim(']') {
			return fmt.Errorf("%w: unterminated array", ErrMalformedJSON)
		}
	default:
		return fmt.Errorf("%w: unexpected delimiter", ErrMalformedJSON)
	}
	return nil
}

func rawObject(data []byte) (map[string]json.RawMessage, error) {
	var object map[string]json.RawMessage
	if err := json.Unmarshal(data, &object); err != nil || object == nil {
		return nil, fmt.Errorf("%w: object required", ErrInvalidType)
	}
	return object, nil
}

func shapeObject(data []byte, required, optional []string) (map[string]json.RawMessage, error) {
	object, err := rawObject(data)
	if err != nil {
		return nil, err
	}
	allowed := make(map[string]struct{}, len(required)+len(optional))
	for _, field := range required {
		allowed[field] = struct{}{}
	}
	for _, field := range optional {
		allowed[field] = struct{}{}
	}
	for field, raw := range object {
		if _, ok := allowed[field]; !ok {
			return nil, fmt.Errorf("%w: %s", ErrUnknownField, field)
		}
		if bytes.Equal(bytes.TrimSpace(raw), []byte("null")) {
			return nil, fmt.Errorf("%w: %s", ErrInvalidType, field)
		}
	}
	for _, field := range required {
		if _, ok := object[field]; !ok {
			return nil, fmt.Errorf("%w: %s", ErrMissingField, field)
		}
	}
	return object, nil
}

func shapeArray(raw json.RawMessage) ([]json.RawMessage, error) {
	var values []json.RawMessage
	if err := json.Unmarshal(raw, &values); err != nil || values == nil {
		return nil, fmt.Errorf("%w: array required", ErrInvalidType)
	}
	return values, nil
}

func shapeString(raw json.RawMessage) error {
	var value string
	if err := json.Unmarshal(raw, &value); err != nil {
		return fmt.Errorf("%w: string required", ErrInvalidType)
	}
	return nil
}

func shapeInt(raw json.RawMessage) error {
	var value int64
	if err := json.Unmarshal(raw, &value); err != nil {
		return fmt.Errorf("%w: integer required", ErrInvalidType)
	}
	return nil
}

func shapeRecord(data []byte) error {
	root, err := shapeObject(data, []string{"schema_version", "observation", "components", "source_references", "sensitivity", "retention"}, nil)
	if err != nil {
		return err
	}
	if err := shapeObservation(root["observation"]); err != nil {
		return err
	}
	components, err := shapeArray(root["components"])
	if err != nil {
		return err
	}
	for _, component := range components {
		if err := shapeComponent(component); err != nil {
			return err
		}
	}
	references, err := shapeArray(root["source_references"])
	if err != nil {
		return err
	}
	for _, reference := range references {
		if _, err := shapeObject(reference, []string{"digest", "media_type", "size", "uri"}, nil); err != nil {
			return err
		}
		object, _ := rawObject(reference)
		for _, field := range []string{"digest", "media_type", "uri"} {
			if err := shapeString(object[field]); err != nil {
				return err
			}
		}
		if err := shapeInt(object["size"]); err != nil {
			return err
		}
	}
	for _, field := range []string{"schema_version", "sensitivity", "retention"} {
		if err := shapeString(root[field]); err != nil {
			return err
		}
	}
	return nil
}

func shapeObservation(data []byte) error {
	object, err := shapeObject(data, []string{"basis", "availability", "exclusions", "harness", "method", "provider", "quality", "repetitions", "study_design", "tokenizer", "variant", "workload"}, nil)
	if err != nil {
		return err
	}
	for _, field := range []string{"basis", "availability", "harness", "method", "provider", "quality", "study_design", "tokenizer", "variant", "workload"} {
		if err := shapeString(object[field]); err != nil {
			return err
		}
	}
	if err := shapeInt(object["repetitions"]); err != nil {
		return err
	}
	exclusions, err := shapeArray(object["exclusions"])
	if err != nil {
		return err
	}
	for _, exclusion := range exclusions {
		if err := shapeString(exclusion); err != nil {
			return err
		}
	}
	return nil
}

func shapeMetric(data []byte) error {
	object, err := shapeObject(data, []string{"availability", "unit"}, []string{"reason", "value"})
	if err != nil {
		return err
	}
	for _, field := range []string{"availability", "unit"} {
		if err := shapeString(object[field]); err != nil {
			return err
		}
	}
	if raw, ok := object["reason"]; ok {
		if err := shapeString(raw); err != nil {
			return err
		}
	}
	if raw, ok := object["value"]; ok {
		if err := shapeInt(raw); err != nil {
			return err
		}
	}
	return nil
}

func shapeComponent(data []byte) error {
	object, err := shapeObject(data, []string{"control_identity", "kind", "metric", "name"}, nil)
	if err != nil {
		return err
	}
	for _, field := range []string{"control_identity", "kind", "name"} {
		if err := shapeString(object[field]); err != nil {
			return err
		}
	}
	return shapeMetric(object["metric"])
}

func shapeComparison(data []byte) error {
	root, err := shapeObject(data, []string{"schema_version", "component", "control", "treatment", "delta", "unit"}, nil)
	if err != nil {
		return err
	}
	if err := shapeString(root["schema_version"]); err != nil {
		return err
	}
	if err := shapeString(root["unit"]); err != nil {
		return err
	}
	if err := shapeInt(root["delta"]); err != nil {
		return err
	}
	selector, err := shapeObject(root["component"], []string{"control_identity", "kind", "name"}, nil)
	if err != nil {
		return err
	}
	for _, field := range []string{"control_identity", "kind", "name"} {
		if err := shapeString(selector[field]); err != nil {
			return err
		}
	}
	for _, side := range []json.RawMessage{root["control"], root["treatment"]} {
		object, err := shapeObject(side, []string{"record_digest", "observation", "metric"}, nil)
		if err != nil {
			return err
		}
		if err := shapeString(object["record_digest"]); err != nil {
			return err
		}
		if err := shapeObservation(object["observation"]); err != nil {
			return err
		}
		if err := shapeMetric(object["metric"]); err != nil {
			return err
		}
	}
	return nil
}

func shapeProjection(data []byte) error {
	root, err := shapeObject(data, []string{"schema_version", "canonical_source_digest", "canonical_source_schema", "canonical_source_size", "fidelity", "omitted_fields", "record", "sensitivity", "retention"}, nil)
	if err != nil {
		return err
	}
	for _, field := range []string{"schema_version", "canonical_source_digest", "canonical_source_schema", "fidelity", "sensitivity", "retention"} {
		if err := shapeString(root[field]); err != nil {
			return err
		}
	}
	if err := shapeInt(root["canonical_source_size"]); err != nil {
		return err
	}
	omitted, err := shapeArray(root["omitted_fields"])
	if err != nil {
		return err
	}
	for _, field := range omitted {
		if err := shapeString(field); err != nil {
			return err
		}
	}
	return shapeRecord(root["record"])
}

func shapeRegistry(data []byte) error {
	root, err := shapeObject(data, []string{"schema_version", "components"}, nil)
	if err != nil {
		return err
	}
	if err := shapeString(root["schema_version"]); err != nil {
		return err
	}
	components, err := shapeArray(root["components"])
	if err != nil {
		return err
	}
	for _, component := range components {
		object, err := shapeObject(component, []string{"kind", "control_identity"}, nil)
		if err != nil {
			return err
		}
		for _, field := range []string{"kind", "control_identity"} {
			if err := shapeString(object[field]); err != nil {
				return err
			}
		}
	}
	return nil
}

func shapeMapping(data []byte) error {
	root, err := shapeObject(data, []string{"schema_version", "mappings"}, nil)
	if err != nil {
		return err
	}
	if err := shapeString(root["schema_version"]); err != nil {
		return err
	}
	mappings, err := shapeArray(root["mappings"])
	if err != nil {
		return err
	}
	for _, mapping := range mappings {
		object, err := shapeObject(mapping, []string{"component_kind", "control_identity"}, nil)
		if err != nil {
			return err
		}
		for _, field := range []string{"component_kind", "control_identity"} {
			if err := shapeString(object[field]); err != nil {
				return err
			}
		}
	}
	return nil
}

func normalizeObservation(observation Observation) Observation {
	result := observation
	result.Exclusions = append([]string(nil), observation.Exclusions...)
	if result.Exclusions == nil {
		result.Exclusions = []string{}
	}
	sort.Strings(result.Exclusions)
	return result
}

func normalizeMetric(metric Metric) Metric {
	result := metric
	if metric.Value != nil {
		value := *metric.Value
		result.Value = &value
	}
	return result
}

func normalizeComponent(component Component) Component {
	result := component
	result.Metric = normalizeMetric(component.Metric)
	return result
}

func normalizeRecord(record Record) Record {
	result := record
	result.Observation = normalizeObservation(record.Observation)
	result.Components = make([]Component, len(record.Components))
	for index, component := range record.Components {
		result.Components[index] = normalizeComponent(component)
	}
	sort.Slice(result.Components, func(i, j int) bool {
		left, right := result.Components[i], result.Components[j]
		if left.ControlIdentity != right.ControlIdentity {
			return left.ControlIdentity < right.ControlIdentity
		}
		if left.Kind != right.Kind {
			return left.Kind < right.Kind
		}
		return left.Name < right.Name
	})
	result.SourceReferences = append([]SourceReference(nil), record.SourceReferences...)
	if result.SourceReferences == nil {
		result.SourceReferences = []SourceReference{}
	}
	sort.Slice(result.SourceReferences, func(i, j int) bool {
		left, right := result.SourceReferences[i], result.SourceReferences[j]
		if left.URI != right.URI {
			return left.URI < right.URI
		}
		if left.Digest != right.Digest {
			return left.Digest < right.Digest
		}
		if left.MediaType != right.MediaType {
			return left.MediaType < right.MediaType
		}
		return left.Size < right.Size
	})
	return result
}

func normalizeSelector(selector ComponentSelector) ComponentSelector { return selector }

func normalizeComparison(comparison Comparison) Comparison {
	result := comparison
	result.Component = normalizeSelector(comparison.Component)
	result.Control.Observation = normalizeObservation(comparison.Control.Observation)
	result.Control.Metric = normalizeMetric(comparison.Control.Metric)
	result.Treatment.Observation = normalizeObservation(comparison.Treatment.Observation)
	result.Treatment.Metric = normalizeMetric(comparison.Treatment.Metric)
	return result
}

func normalizeProjection(projection Projection) Projection {
	result := projection
	result.OmittedFields = append([]string(nil), projection.OmittedFields...)
	if result.OmittedFields == nil {
		result.OmittedFields = []string{}
	}
	sort.Strings(result.OmittedFields)
	result.Record = normalizeRecord(projection.Record)
	return result
}

func normalizeRegistry(registry ComponentRegistry) ComponentRegistry {
	result := registry
	result.Components = append([]ComponentDefinition(nil), registry.Components...)
	if result.Components == nil {
		result.Components = []ComponentDefinition{}
	}
	sort.Slice(result.Components, func(i, j int) bool {
		return result.Components[i].Kind < result.Components[j].Kind
	})
	return result
}

func normalizeControlMapping(mapping ControlMapping) ControlMapping {
	result := mapping
	result.Mappings = append([]ControlMappingEntry(nil), mapping.Mappings...)
	if result.Mappings == nil {
		result.Mappings = []ControlMappingEntry{}
	}
	sort.Slice(result.Mappings, func(i, j int) bool {
		return result.Mappings[i].ComponentKind < result.Mappings[j].ComponentKind
	})
	return result
}

func isDigest(value, prefix string) bool {
	if !strings.HasPrefix(value, prefix) || len(value) != len(prefix)+64 {
		return false
	}
	decoded, err := hex.DecodeString(value[len(prefix):])
	return err == nil && len(decoded) == 32 && value[len(prefix):] == strings.ToLower(value[len(prefix):])
}
