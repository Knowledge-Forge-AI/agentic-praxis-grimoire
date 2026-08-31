package footprint

import (
	"context"
	"fmt"
	"unicode/utf8"
)

// Measure converts explicit first-party inputs into one validated record.  It
// measures bytes and UTF-8 characters locally; provider-specific token units
// must be supplied as an already observed metric or are represented as an
// explicit unavailable metric.  No provider, tokenizer, or other APGR package
// is consulted.
func Measure(ctx context.Context, request MeasureRequest) (Record, error) {
	if err := contextError(ctx); err != nil {
		return Record{}, err
	}
	if request.SchemaVersion != FootprintSchemaV1 {
		return Record{}, invalid(ErrInvalidRecord, ErrUnknownSchema, "unsupported measurement schema version %q", request.SchemaVersion)
	}
	if _, ok := knownSensitivities[request.Sensitivity]; !ok {
		return Record{}, invalid(ErrInvalidRecord, ErrUnknownVocabulary, "unknown measurement sensitivity %q", request.Sensitivity)
	}
	if _, ok := knownRetentions[request.Retention]; !ok {
		return Record{}, invalid(ErrInvalidRecord, ErrUnknownVocabulary, "unknown measurement retention %q", request.Retention)
	}
	if len(request.Components) == 0 {
		return Record{}, invalid(ErrInvalidRecord, ErrMissingField, "measurement requires at least one component")
	}
	components := make([]Component, 0, len(request.Components))
	for _, input := range request.Components {
		if err := contextError(ctx); err != nil {
			return Record{}, err
		}
		component, err := measureComponent(input)
		if err != nil {
			return Record{}, err
		}
		components = append(components, component)
	}
	if err := contextError(ctx); err != nil {
		return Record{}, err
	}
	record := Record{
		SchemaVersion:    FootprintSchemaV1,
		Observation:      normalizeObservation(request.Observation),
		Components:       components,
		SourceReferences: append([]SourceReference(nil), request.SourceReferences...),
		Sensitivity:      request.Sensitivity,
		Retention:        request.Retention,
	}
	if request.SourceReferences == nil {
		record.SourceReferences = []SourceReference{}
	}
	if err := validateRecord(record); err != nil {
		return Record{}, err
	}
	return normalizeRecord(record), nil
}

func measureComponent(input ComponentInput) (Component, error) {
	if _, ok := componentControls[input.Kind]; !ok {
		return Component{}, invalid(ErrInvalidRecord, ErrUnknownVocabulary, "unknown component kind %q", input.Kind)
	}
	control := input.ControlIdentity
	if control == "" {
		control = componentControls[input.Kind]
	}
	component := Component{
		ControlIdentity: control,
		Kind:            input.Kind,
		Name:            input.Name,
	}
	metric, err := metricForInput(input)
	if err != nil {
		return Component{}, err
	}
	component.Metric = metric
	if err := validateComponent(component); err != nil {
		return Component{}, err
	}
	return component, nil
}

func metricForInput(input ComponentInput) (Metric, error) {
	unit := input.Unit
	if input.Metric.Unit != "" {
		if unit != "" && unit != input.Metric.Unit {
			return Metric{}, invalid(ErrInvalidRecord, ErrUnitMismatch, "measurement metric units do not match")
		}
		unit = input.Metric.Unit
	}
	if _, ok := knownUnits[unit]; !ok {
		return Metric{}, invalid(ErrInvalidRecord, ErrUnknownVocabulary, "unknown measurement unit %q", unit)
	}
	if input.Metric.Availability != "" {
		metric := normalizeMetric(input.Metric)
		metric.Unit = unit
		if err := validateMetric(metric); err != nil {
			return Metric{}, err
		}
		return metric, nil
	}
	if input.Metric.Value != nil || input.Metric.Reason != "" {
		return Metric{}, invalid(ErrInvalidRecord, ErrInvalidType, "metric availability is required")
	}

	switch unit {
	case UnitBytes:
		var value int64
		if input.Data != nil {
			value = int64(len(input.Data))
		} else {
			if !utf8.ValidString(input.Text) {
				return Metric{}, invalid(ErrInvalidRecord, ErrInvalidUTF8, "byte measurement text is not valid UTF-8")
			}
			value = int64(len([]byte(input.Text)))
		}
		return availableMetric(unit, value), nil
	case UnitCharacters:
		var value int64
		if input.Data != nil {
			if !utf8.Valid(input.Data) {
				return Metric{}, invalid(ErrInvalidRecord, ErrInvalidUTF8, "character measurement data is not valid UTF-8")
			}
			value = int64(utf8.RuneCount(input.Data))
		} else {
			if !utf8.ValidString(input.Text) {
				return Metric{}, invalid(ErrInvalidRecord, ErrInvalidUTF8, "character measurement text is not valid UTF-8")
			}
			value = int64(utf8.RuneCountInString(input.Text))
		}
		return availableMetric(unit, value), nil
	default:
		return Metric{Availability: Unavailable, Reason: "provider tokenizer is not available to first-party measurement", Unit: unit}, nil
	}
}

func availableMetric(unit Unit, value int64) Metric {
	return Metric{Availability: Available, Unit: unit, Value: &value}
}

func contextError(ctx context.Context) error {
	if ctx == nil {
		return nil
	}
	if err := ctx.Err(); err != nil {
		return fmt.Errorf("%w: %w", ErrContextCancelled, err)
	}
	return nil
}

// DefaultComponentRegistry returns a fresh copy of the complete code-owned
// component registry in canonical order.
func DefaultComponentRegistry() ComponentRegistry {
	kinds := sortedComponentKinds()
	components := make([]ComponentDefinition, 0, len(kinds))
	for _, kind := range kinds {
		components = append(components, ComponentDefinition{Kind: kind, ControlIdentity: componentControls[kind]})
	}
	return ComponentRegistry{SchemaVersion: ComponentRegistrySchemaV1, Components: components}
}

// DefaultControlMapping returns a fresh copy of the complete code-owned
// component-to-capacity-control mapping in canonical order.
func DefaultControlMapping() ControlMapping {
	kinds := sortedComponentKinds()
	mappings := make([]ControlMappingEntry, 0, len(kinds))
	for _, kind := range kinds {
		mappings = append(mappings, ControlMappingEntry{ComponentKind: kind, ControlIdentity: componentControls[kind]})
	}
	return ControlMapping{SchemaVersion: ControlMappingSchemaV1, Mappings: mappings}
}
