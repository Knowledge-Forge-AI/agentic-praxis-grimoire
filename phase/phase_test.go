package phase_test

import (
	"encoding/json"
	"os"
	"path/filepath"
	"slices"
	"testing"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/phase"
)

func TestParseRequestV2_Valid(t *testing.T) {
	raw := []byte(`{
		"schema": "agent-phase-request-v2",
		"phase_type": "implementation_testing",
		"prompt": "Implement the feature"
	}`)

	req, err := phase.ParseRequestV2(raw)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if req.Schema != phase.SchemaNameV2 {
		t.Errorf("expected schema %q, got %q", phase.SchemaNameV2, req.Schema)
	}
	if req.PhaseType != phase.PhaseTypeImplementationTesting {
		t.Errorf("expected phase_type %q, got %q", phase.PhaseTypeImplementationTesting, req.PhaseType)
	}
	if req.Prompt != "Implement the feature" {
		t.Errorf("expected prompt 'Implement the feature', got %q", req.Prompt)
	}
}

func TestParseRequestV2_RejectsExecutionModeAndConstraints(t *testing.T) {
	cases := []struct {
		name string
		json string
	}{
		{
			name: "execution_mode included",
			json: `{"schema": "agent-phase-request-v2", "phase_type": "implementation_testing", "prompt": "foo", "execution_mode": "normal"}`,
		},
		{
			name: "constraints included",
			json: `{"schema": "agent-phase-request-v2", "phase_type": "implementation_testing", "prompt": "foo", "constraints": ["no_network"]}`,
		},
		{
			name: "provider included",
			json: `{"schema": "agent-phase-request-v2", "phase_type": "implementation_testing", "prompt": "foo", "provider": "codex"}`,
		},
		{
			name: "model included",
			json: `{"schema": "agent-phase-request-v2", "phase_type": "implementation_testing", "prompt": "foo", "model": "gpt-5"}`,
		},
		{
			name: "unknown key included",
			json: `{"schema": "agent-phase-request-v2", "phase_type": "implementation_testing", "prompt": "foo", "arbitrary": 123}`,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			_, err := phase.ParseRequestV2([]byte(tc.json))
			if err == nil {
				t.Fatalf("expected rejection for %s, got nil error", tc.name)
			}
		})
	}
}

func TestParseRequestV2_RejectsInvalidSchemaAndPhase(t *testing.T) {
	cases := []struct {
		name string
		json string
	}{
		{
			name: "v1 schema rejected",
			json: `{"schema": "agent-phase-request-v1", "phase_type": "implementation_testing", "prompt": "foo"}`,
		},
		{
			name: "unknown phase_type rejected",
			json: `{"schema": "agent-phase-request-v2", "phase_type": "bad_phase", "prompt": "foo"}`,
		},
		{
			name: "empty prompt rejected",
			json: `{"schema": "agent-phase-request-v2", "phase_type": "implementation_testing", "prompt": ""}`,
		},
		{
			name: "whitespace-only prompt rejected",
			json: `{"schema": "agent-phase-request-v2", "phase_type": "implementation_testing", "prompt": "   \n\t  "}`,
		},
		{
			name: "trailing JSON data rejected",
			json: `{"schema": "agent-phase-request-v2", "phase_type": "implementation_testing", "prompt": "foo"} extra_data`,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			_, err := phase.ParseRequestV2([]byte(tc.json))
			if err == nil {
				t.Fatalf("expected error for %s, got nil", tc.name)
			}
		})
	}
}

func TestRequestV2_GoldenVectors(t *testing.T) {
	path := filepath.Join("..", "testing", "fixtures", "conformance", "request_v2_vectors.json")
	data, err := os.ReadFile(path)
	if err != nil {
		t.Skipf("conformance fixtures not yet created: %v", err)
	}

	var fixture struct {
		ValidVectors []struct {
			ID      string          `json:"id"`
			Payload json.RawMessage `json:"payload"`
		} `json:"valid_vectors"`
		InvalidVectors []struct {
			ID            string          `json:"id"`
			Payload       json.RawMessage `json:"payload"`
			ExpectedError string          `json:"expected_error"`
		} `json:"invalid_vectors"`
	}

	if err := json.Unmarshal(data, &fixture); err != nil {
		t.Fatalf("failed to parse fixture %s: %v", path, err)
	}

	for _, vec := range fixture.ValidVectors {
		t.Run(vec.ID, func(t *testing.T) {
			req, err := phase.ParseRequestV2(vec.Payload)
			if err != nil {
				t.Fatalf("vector %s failed: %v", vec.ID, err)
			}
			if req.Schema != phase.SchemaNameV2 {
				t.Errorf("expected schema %q, got %q", phase.SchemaNameV2, req.Schema)
			}
		})
	}

	for _, vec := range fixture.InvalidVectors {
		t.Run(vec.ID, func(t *testing.T) {
			_, err := phase.ParseRequestV2(vec.Payload)
			if err == nil {
				t.Fatalf("vector %s expected error, got nil", vec.ID)
			}
		})
	}
}

func TestSemanticRoles_Properties(t *testing.T) {
	if len(phase.CanonicalRoles) != 8 {
		t.Fatalf("expected 8 canonical roles, got %d", len(phase.CanonicalRoles))
	}

	mutatingRoles := []phase.SemanticRole{phase.RoleProducer, phase.RoleReviser, phase.RoleCloseoutAgent}
	for _, r := range phase.CanonicalRoles {
		if slices.Contains(mutatingRoles, r) {
			if !phase.IsMutating(r) {
				t.Errorf("role %s should be mutating", r)
			}
		} else {
			if phase.IsMutating(r) {
				t.Errorf("role %s should not be mutating", r)
			}
		}
	}

	readOnlyRoles := []phase.SemanticRole{phase.RolePlanner, phase.RolePlanReviewer, phase.RoleWorkReviewer}
	for _, r := range phase.CanonicalRoles {
		if slices.Contains(readOnlyRoles, r) {
			if !phase.IsReadOnly(r) {
				t.Errorf("role %s should be read-only", r)
			}
		} else {
			if phase.IsReadOnly(r) {
				t.Errorf("role %s should not be read-only", r)
			}
		}
	}
}

func TestActorBinding_DefaultAndUnmergedTopologies(t *testing.T) {
	defaults := phase.DefaultBindings()
	if len(defaults) != 5 {
		t.Fatalf("expected 5 default bindings, got %d", len(defaults))
	}

	expectedIDs := []string{"binding_plan", "binding_plan_review", "binding_work", "binding_work_review", "binding_closeout"}
	for i, b := range defaults {
		if b.BindingID != expectedIDs[i] {
			t.Errorf("binding %d: expected ID %q, got %q", i, expectedIDs[i], b.BindingID)
		}
		if b.PolicyName != "default_standard" {
			t.Errorf("binding %d: expected policy 'default_standard', got %q", i, b.PolicyName)
		}
	}

	unmerged := phase.UnmergedBindings()
	if len(unmerged) != 8 {
		t.Fatalf("expected 8 unmerged bindings, got %d", len(unmerged))
	}

	for i, b := range unmerged {
		if len(b.Roles) != 1 {
			t.Errorf("unmerged binding %s has %d roles, expected 1", b.BindingID, len(b.Roles))
		}
		if b.Roles[0] != phase.CanonicalRoles[i] {
			t.Errorf("unmerged binding %d: expected role %s, got %s", i, phase.CanonicalRoles[i], b.Roles[0])
		}
	}
}

func TestSemanticRoles_GoldenVectors(t *testing.T) {
	path := filepath.Join("..", "testing", "fixtures", "conformance", "semantic_roles_vectors.json")
	data, err := os.ReadFile(path)
	if err != nil {
		t.Skipf("conformance fixtures not yet created: %v", err)
	}

	var fixture struct {
		Roles []struct {
			Name                 string   `json:"name"`
			IsMutating           bool     `json:"is_mutating"`
			IsReadOnly           bool     `json:"is_read_only"`
			RequiredCapabilities []string `json:"required_capabilities"`
		} `json:"roles"`
		Topologies struct {
			DefaultStandard []struct {
				BindingID            string   `json:"binding_id"`
				Roles                []string `json:"roles"`
				PolicyName           string   `json:"policy_name"`
				IsMutating           bool     `json:"is_mutating"`
				ProcessReadOnly      bool     `json:"process_read_only"`
				RequiredCapabilities []string `json:"required_capabilities"`
			} `json:"default_standard"`
		} `json:"topologies"`
	}

	if err := json.Unmarshal(data, &fixture); err != nil {
		t.Fatalf("failed to parse fixture %s: %v", path, err)
	}

	for _, r := range fixture.Roles {
		role := phase.SemanticRole(r.Name)
		if !phase.ValidRole(role) {
			t.Errorf("role %q is not marked valid", r.Name)
		}
		if phase.IsMutating(role) != r.IsMutating {
			t.Errorf("role %q is_mutating mismatch: got %v, expected %v", r.Name, phase.IsMutating(role), r.IsMutating)
		}
		if phase.IsReadOnly(role) != r.IsReadOnly {
			t.Errorf("role %q is_read_only mismatch: got %v, expected %v", r.Name, phase.IsReadOnly(role), r.IsReadOnly)
		}
		caps := phase.RequiredCapabilities(role)
		if !slices.Equal(caps, r.RequiredCapabilities) {
			t.Errorf("role %q required_capabilities mismatch: got %v, expected %v", r.Name, caps, r.RequiredCapabilities)
		}
	}

	defaults := phase.DefaultBindings()
	for i, exp := range fixture.Topologies.DefaultStandard {
		b := defaults[i]
		if b.BindingID != exp.BindingID {
			t.Errorf("binding %d: expected %s, got %s", i, exp.BindingID, b.BindingID)
		}
		if b.IsMutating != exp.IsMutating {
			t.Errorf("binding %s: is_mutating expected %v, got %v", b.BindingID, exp.IsMutating, b.IsMutating)
		}
		if b.ProcessReadOnly != exp.ProcessReadOnly {
			t.Errorf("binding %s: process_read_only expected %v, got %v", b.BindingID, exp.ProcessReadOnly, b.ProcessReadOnly)
		}
		if !slices.Equal(b.RequiredCapabilities, exp.RequiredCapabilities) {
			t.Errorf("binding %s: capabilities expected %v, got %v", b.BindingID, exp.RequiredCapabilities, b.RequiredCapabilities)
		}
	}
}
