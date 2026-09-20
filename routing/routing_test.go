package routing_test

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"testing"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/routing"
)

func TestCanonicalDigest_GoldenVectors(t *testing.T) {
	path := filepath.Join("..", "testing", "fixtures", "conformance", "observation_digest_vectors.json")
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("failed to read %s: %v", path, err)
	}

	var fixture struct {
		Vectors []struct {
			ObservationID   string         `json:"observation_id"`
			Producer        string         `json:"producer"`
			ObservationType string         `json:"observation_type"`
			Provider        string         `json:"provider"`
			Profile         *string        `json:"profile"`
			Timestamp       float64        `json:"timestamp"`
			ExpiresAt       *float64       `json:"expires_at"`
			StateValue      string         `json:"state_value"`
			Detail          map[string]any `json:"detail"`
			ExpectedDigest  string         `json:"expected_digest"`
		} `json:"vectors"`
	}

	if err := json.Unmarshal(data, &fixture); err != nil {
		t.Fatalf("failed to parse %s: %v", path, err)
	}

	for _, v := range fixture.Vectors {
		t.Run(v.ObservationID, func(t *testing.T) {
			obs := routing.OperationalObservation{
				ObservationID:   v.ObservationID,
				Producer:        v.Producer,
				ObservationType: v.ObservationType,
				Provider:        v.Provider,
				Profile:         v.Profile,
				Timestamp:       v.Timestamp,
				ExpiresAt:       v.ExpiresAt,
				StateValue:      v.StateValue,
				Detail:          v.Detail,
			}

			digest, err := routing.CanonicalDigest(obs)
			if err != nil {
				t.Fatalf("CanonicalDigest failed: %v", err)
			}

			if digest != v.ExpectedDigest {
				t.Errorf("digest mismatch for %s:\n got:      %s\n expected: %s",
					v.ObservationID, digest, v.ExpectedDigest)
			}
		})
	}
}

func TestCanonicalDigest_EdgeCases(t *testing.T) {
	// Case 1: Empty detail map should yield identical digest to nil detail map
	obsEmpty := routing.OperationalObservation{
		ObservationID:   "test-empty",
		Producer:        "probe",
		ObservationType: "availability",
		Provider:        "codex",
		Timestamp:       1726500000.0,
		StateValue:      "available",
		Detail:          map[string]any{},
	}
	obsNil := routing.OperationalObservation{
		ObservationID:   "test-empty",
		Producer:        "probe",
		ObservationType: "availability",
		Provider:        "codex",
		Timestamp:       1726500000.0,
		StateValue:      "available",
		Detail:          nil,
	}

	dEmpty, err := routing.CanonicalDigest(obsEmpty)
	if err != nil {
		t.Fatalf("CanonicalDigest(obsEmpty) error: %v", err)
	}
	dNil, err := routing.CanonicalDigest(obsNil)
	if err != nil {
		t.Fatalf("CanonicalDigest(obsNil) error: %v", err)
	}

	expectedEmpty := "5d8046f0715548994f51eb55604a3200ddd4d34e62867f6fb864de2c0e05e87b"
	if dEmpty != expectedEmpty {
		t.Errorf("expected empty detail digest %s, got %s", expectedEmpty, dEmpty)
	}
	if dEmpty != dNil {
		t.Errorf("expected empty and nil detail digests to match, got %s vs %s", dEmpty, dNil)
	}

	// Case 2: Special chars (<, >, &) and non-ASCII unicode matching Python json.dumps oracle
	obsSpecial := routing.OperationalObservation{
		ObservationID:   "test-special",
		Producer:        "probe",
		ObservationType: "availability",
		Provider:        "codex",
		Timestamp:       1726500000.0,
		StateValue:      "available",
		Detail: map[string]any{
			"cmd": "<tag> & ok",
			"msg": "café \U0001F600",
		},
	}
	dSpecial, err := routing.CanonicalDigest(obsSpecial)
	if err != nil {
		t.Fatalf("CanonicalDigest(obsSpecial) error: %v", err)
	}
	expectedSpecial := "d826b8d9ace0b6b830446357bbe40807339bc020b7534f4cd0c224d6f54be0d9"
	if dSpecial != expectedSpecial {
		t.Errorf("expected special chars digest %s, got %s", expectedSpecial, dSpecial)
	}
}

func TestResolve_DynamicRoutingScenarios(t *testing.T) {
	path := filepath.Join("..", "testing", "fixtures", "conformance", "dynamic_routing_scenarios.json")
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("failed to read %s: %v", path, err)
	}

	var fixture struct {
		Catalog map[string]struct {
			EndpointAlias string   `json:"endpoint_alias"`
			Provider      string   `json:"provider"`
			Profile       string   `json:"profile"`
			Capabilities  []string `json:"capabilities"`
			Posture       string   `json:"posture"`
		} `json:"catalog"`
		Scenarios []struct {
			ID                   string   `json:"id"`
			Description          string   `json:"description"`
			PhaseType            string   `json:"phase_type"`
			BindingID            string   `json:"binding_id"`
			RequiredCapabilities []string `json:"required_capabilities"`
			IsMutating           bool     `json:"is_mutating"`
			Observations         []struct {
				ObservationID   string   `json:"observation_id"`
				Producer        string   `json:"producer"`
				ObservationType string   `json:"observation_type"`
				Provider        string   `json:"provider"`
				Profile         *string  `json:"profile"`
				Timestamp       float64  `json:"timestamp"`
				ExpiresAt       *float64 `json:"expires_at"`
				StateValue      string   `json:"state_value"`
			} `json:"observations"`
			PriorResolutions map[string]struct {
				BindingID string `json:"binding_id"`
				Provider  string `json:"provider"`
			} `json:"prior_resolutions"`
			Now              float64 `json:"now"`
			ExpectedWinner   string  `json:"expected_winner"`
			ExpectedProvider string  `json:"expected_provider"`
			ExpectedProfile  string  `json:"expected_profile"`
			ExpectedError    string  `json:"expected_error"`
		} `json:"scenarios"`
	}

	if err := json.Unmarshal(data, &fixture); err != nil {
		t.Fatalf("failed to parse %s: %v", path, err)
	}

	catalog := make(map[string]routing.EndpointCapabilities)
	for k, v := range fixture.Catalog {
		catalog[k] = routing.EndpointCapabilities{
			EndpointAlias: v.EndpointAlias,
			Provider:      v.Provider,
			Profile:       v.Profile,
			Capabilities:  v.Capabilities,
			Posture:       v.Posture,
		}
	}

	for _, sc := range fixture.Scenarios {
		t.Run(sc.ID, func(t *testing.T) {
			var obs []routing.OperationalObservation
			for _, o := range sc.Observations {
				obs = append(obs, routing.OperationalObservation{
					ObservationID:   o.ObservationID,
					Producer:        o.Producer,
					ObservationType: o.ObservationType,
					Provider:        o.Provider,
					Profile:         o.Profile,
					Timestamp:       o.Timestamp,
					ExpiresAt:       o.ExpiresAt,
					StateValue:      o.StateValue,
				})
			}

			var distinctProviders []string
			if sc.BindingID == "binding_plan_review" {
				if p, ok := sc.PriorResolutions["binding_plan"]; ok && p.Provider != "" {
					distinctProviders = append(distinctProviders, p.Provider)
				}
			}
			if sc.BindingID == "binding_work_review" {
				if p, ok := sc.PriorResolutions["binding_work"]; ok && p.Provider != "" {
					distinctProviders = append(distinctProviders, p.Provider)
				}
			}

			isReview := sc.BindingID == "binding_plan_review" || sc.BindingID == "binding_work_review"
			isProducer := sc.BindingID == "binding_work" || sc.BindingID == "binding_closeout"

			req := routing.ResolveRequest{
				Requirements: routing.RouteRequirements{
					PhaseType:            sc.PhaseType,
					RequiredCapabilities: sc.RequiredCapabilities,
					RequiresMutating:     sc.IsMutating,
					IsReviewTurn:         isReview,
					IsProducerTurn:       isProducer,
					DistinctProviders:    distinctProviders,
				},
				BindingID:           sc.BindingID,
				CapabilitiesCatalog: catalog,
				Observations:        obs,
				Now:                 sc.Now,
			}

			route, err := routing.Resolve(context.Background(), req)
			if sc.ExpectedError == "no_route" {
				if err == nil {
					t.Fatalf("scenario %s expected error, got route: %v", sc.ID, route)
				}
				if !errors.Is(err, routing.ErrNoRouteAvailable) {
					t.Errorf("scenario %s expected ErrNoRouteAvailable, got: %v", sc.ID, err)
				}
				return
			}

			if err != nil {
				t.Fatalf("scenario %s unexpected error: %v", sc.ID, err)
			}

			if route.EndpointAlias != sc.ExpectedWinner {
				t.Errorf("scenario %s winner mismatch: got %q, expected %q",
					sc.ID, route.EndpointAlias, sc.ExpectedWinner)
			}
			if route.Provider != sc.ExpectedProvider {
				t.Errorf("scenario %s provider mismatch: got %q, expected %q",
					sc.ID, route.Provider, sc.ExpectedProvider)
			}
			if route.Profile != sc.ExpectedProfile {
				t.Errorf("scenario %s profile mismatch: got %q, expected %q",
					sc.ID, route.Profile, sc.ExpectedProfile)
			}
		})
	}
}

func TestResolve_ContextCancellation(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	cancel()

	req := routing.ResolveRequest{
		CapabilitiesCatalog: map[string]routing.EndpointCapabilities{
			"ep-1": {
				EndpointAlias: "ep-1",
				Provider:      "codex",
				Profile:       "profile-a",
				Capabilities:  []string{routing.CapRead},
				Posture:       routing.PostureReadOnly,
			},
		},
		Requirements: routing.RouteRequirements{
			PhaseType:            "implementation_testing",
			RequiredCapabilities: []string{routing.CapRead},
		},
	}

	_, err := routing.Resolve(ctx, req)
	if !errors.Is(err, context.Canceled) {
		t.Fatalf("expected context.Canceled, got %v", err)
	}
}
