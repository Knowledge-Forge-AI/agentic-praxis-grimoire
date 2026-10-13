package skills

import (
	"context"
	"fmt"
	apgfootprint "github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/footprint"
)

// ContextPlanFootprint measures the prospective rendered transmission, not file
// materialization or provider/model use. It never resolves a retained catalog.
func ContextPlanFootprint(plan ContextPlan) (apgfootprint.Record, error) {
	if plan.SchemaVersion != ContextPlanSchemaV1 || contextCost(plan.Payload) != plan.PayloadCost {
		return apgfootprint.Record{}, fmt.Errorf("invalid context payload identity")
	}
	return apgfootprint.Measure(context.Background(), apgfootprint.MeasureRequest{
		SchemaVersion: apgfootprint.FootprintSchemaV1,
		Observation: apgfootprint.Observation{Basis: apgfootprint.ObservationBasisDirectMeasurement, Availability: apgfootprint.Available,
			Exclusions: []string{"provider_total_context", "provider_context_fit", "model_consumption"}, Harness: ContextRuleVersionV1, Method: "rendered-payload-byte-count",
			Provider: "provider-neutral", Quality: apgfootprint.QualityVerified, Repetitions: 1, StudyDesign: apgfootprint.StudyDesignSingleRun, Tokenizer: "not_applicable", Variant: plan.ContentIdentity, Workload: "prospective_context"},
		Components: []apgfootprint.ComponentInput{
			availableBytes(apgfootprint.ComponentBundle, "rendered_transmission", plan.PayloadCost.Bytes),
			unavailableBytes(apgfootprint.ComponentPromptOverhead, "provider_native_overhead", "not observed"),
		}, Sensitivity: apgfootprint.SensitivityInternal, Retention: apgfootprint.RetentionRetained,
	})
}
