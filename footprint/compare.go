package footprint

import (
	"context"
	"fmt"
	"math"
)

// Compare returns the treatment-minus-control delta for one exactly matched
// component.  Observation dimensions must match except for Variant, which is
// the explicit control/treatment identity.  Metric values are integer-only
// and units are never converted implicitly.
func Compare(ctx context.Context, request CompareRequest) (Comparison, error) {
	if err := contextError(ctx); err != nil {
		return Comparison{}, err
	}
	if err := validateRecord(request.Control); err != nil {
		return Comparison{}, invalid(ErrInvalidComparison, err, "control record is invalid")
	}
	if err := validateRecord(request.Treatment); err != nil {
		return Comparison{}, invalid(ErrInvalidComparison, err, "treatment record is invalid")
	}
	if !observationsCompatible(request.Control.Observation, request.Treatment.Observation) {
		return Comparison{}, invalid(ErrInvalidComparison, ErrIncompatibleComparison, "observations are not compatible")
	}
	selector, err := comparisonSelector(request)
	if err != nil {
		return Comparison{}, err
	}
	control, err := selectComponent(request.Control, selector)
	if err != nil {
		return Comparison{}, invalid(ErrInvalidComparison, err, "control component is not selectable")
	}
	treatment, err := selectComponent(request.Treatment, selector)
	if err != nil {
		return Comparison{}, invalid(ErrInvalidComparison, err, "treatment component is not selectable")
	}
	if err := contextError(ctx); err != nil {
		return Comparison{}, err
	}
	if control.Metric.Availability != Available || treatment.Metric.Availability != Available || control.Metric.Value == nil || treatment.Metric.Value == nil {
		return Comparison{}, invalid(ErrInvalidComparison, ErrUnavailableMetric, "comparison requires two available integer metrics")
	}
	if control.Metric.Unit != treatment.Metric.Unit {
		return Comparison{}, invalid(ErrInvalidComparison, ErrUnitMismatch, "comparison metric units do not match")
	}
	delta, ok := subtractInt64(*treatment.Metric.Value, *control.Metric.Value)
	if !ok {
		return Comparison{}, invalid(ErrInvalidComparison, ErrIntegerOverflow, "comparison delta overflows int64")
	}
	comparison := Comparison{
		SchemaVersion: ComparisonSchemaV1,
		Component:     selector,
		Control: ComparisonObservation{
			RecordDigest: FingerprintRecord(request.Control),
			Observation:  normalizeObservation(request.Control.Observation),
			Metric:       normalizeMetric(control.Metric),
		},
		Treatment: ComparisonObservation{
			RecordDigest: FingerprintRecord(request.Treatment),
			Observation:  normalizeObservation(request.Treatment.Observation),
			Metric:       normalizeMetric(treatment.Metric),
		},
		Delta: delta,
		Unit:  control.Metric.Unit,
	}
	if comparison.Control.RecordDigest == "" || comparison.Treatment.RecordDigest == "" {
		return Comparison{}, invalid(ErrInvalidComparison, ErrInvalidRecord, "record fingerprint unavailable")
	}
	if err := validateComparison(comparison); err != nil {
		return Comparison{}, err
	}
	return normalizeComparison(comparison), nil
}

func comparisonSelector(request CompareRequest) (ComponentSelector, error) {
	selector := request.Component
	if request.ComponentKind != "" {
		if selector.Kind != "" && selector.Kind != request.ComponentKind {
			return ComponentSelector{}, invalid(ErrInvalidComparison, ErrUnknownVocabulary, "component kind selectors disagree")
		}
		selector.Kind = request.ComponentKind
	}
	if request.ComponentName != "" {
		if selector.Name != "" && selector.Name != request.ComponentName {
			return ComponentSelector{}, invalid(ErrInvalidComparison, ErrInvalidType, "component name selectors disagree")
		}
		selector.Name = request.ComponentName
	}
	if selector.Kind == "" || selector.Name == "" {
		if len(request.Control.Components) != 1 || len(request.Treatment.Components) != 1 {
			return ComponentSelector{}, invalid(ErrInvalidComparison, ErrInvalidType, "component selector is required when records have multiple components")
		}
		control := request.Control.Components[0]
		treatment := request.Treatment.Components[0]
		if control.Kind != treatment.Kind || control.Name != treatment.Name || control.ControlIdentity != treatment.ControlIdentity {
			return ComponentSelector{}, invalid(ErrInvalidComparison, ErrIncompatibleComparison, "single components do not correspond")
		}
		selector = ComponentSelector{ControlIdentity: control.ControlIdentity, Kind: control.Kind, Name: control.Name}
	}
	if selector.ControlIdentity == "" {
		selector.ControlIdentity = componentControls[selector.Kind]
	}
	if err := validateSelector(selector); err != nil {
		return ComponentSelector{}, err
	}
	return selector, nil
}

func selectComponent(record Record, selector ComponentSelector) (Component, error) {
	var selected Component
	found := false
	for _, component := range record.Components {
		if component.Kind != selector.Kind || component.Name != selector.Name || component.ControlIdentity != selector.ControlIdentity {
			continue
		}
		if found {
			return Component{}, fmt.Errorf("duplicate matching component")
		}
		selected = component
		found = true
	}
	if !found {
		return Component{}, fmt.Errorf("component is absent")
	}
	return selected, nil
}

func subtractInt64(left, right int64) (int64, bool) {
	if right > 0 && left < math.MinInt64+right {
		return 0, false
	}
	if right < 0 && left > math.MaxInt64+right {
		return 0, false
	}
	return left - right, true
}
