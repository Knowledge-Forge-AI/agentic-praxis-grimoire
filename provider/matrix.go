package provider

import (
	"encoding/json"
	"fmt"
	"slices"
	"strings"
)

// ConformanceMatrixSchema is the schema identifier for provider capability evaluations.
const ConformanceMatrixSchema = "apgr-provider-conformance-matrix-v1"

// RequiredRowCount is the exact count of canonical conformance rows defined in ADR 0061/0065.
const RequiredRowCount = 22

// ProviderFamily identifies one of the three first-class supported provider families.
type ProviderFamily string

const (
	FamilyCodex       ProviderFamily = "codex"
	FamilyClaude      ProviderFamily = "claude"
	FamilyAntigravity ProviderFamily = "antigravity"
)

// CanonicalFamilies lists all three supported provider families.
var CanonicalFamilies = []ProviderFamily{
	FamilyCodex,
	FamilyClaude,
	FamilyAntigravity,
}

// SupportStatus records whether a capability is supported and any operational notes.
type SupportStatus struct {
	Supported bool   `json:"supported"`
	Notes     string `json:"notes"`
}

// ConformanceRow represents one evaluated provider capability dimension.
type ConformanceRow struct {
	ID          string                           `json:"id"`
	Name        string                           `json:"name"`
	Description string                           `json:"description"`
	Support     map[ProviderFamily]SupportStatus `json:"support"`
}

// ConformanceMatrix represents the complete 22-row capability evaluation matrix.
type ConformanceMatrix struct {
	Schema      string           `json:"schema"`
	GeneratedAt string           `json:"generated_at"`
	Providers   []ProviderFamily `json:"providers"`
	Rows        []ConformanceRow `json:"rows"`
}

// LoadConformanceMatrix unmarshals and validates a conformance matrix JSON payload.
func LoadConformanceMatrix(data []byte) (*ConformanceMatrix, error) {
	var m ConformanceMatrix
	if err := json.Unmarshal(data, &m); err != nil {
		return nil, fmt.Errorf("provider: json unmarshal error: %w", err)
	}
	if err := ValidateMatrix(&m); err != nil {
		return nil, err
	}
	return &m, nil
}

// ValidateMatrix verifies all 22 required rows are present with evaluations for all 3 families.
func ValidateMatrix(m *ConformanceMatrix) error {
	if m.Schema != ConformanceMatrixSchema {
		return fmt.Errorf("provider: unexpected matrix schema: %q", m.Schema)
	}
	if len(m.Rows) != RequiredRowCount {
		return fmt.Errorf("provider: expected exactly %d rows, got %d", RequiredRowCount, len(m.Rows))
	}

	seenIDs := make(map[string]bool)
	for i, row := range m.Rows {
		if strings.TrimSpace(row.ID) == "" {
			return fmt.Errorf("provider: row %d has empty id", i)
		}
		if seenIDs[row.ID] {
			return fmt.Errorf("provider: duplicate row id: %q", row.ID)
		}
		seenIDs[row.ID] = true

		if len(row.Support) != len(CanonicalFamilies) {
			return fmt.Errorf("provider: row %q must evaluate all %d families, got %d",
				row.ID, len(CanonicalFamilies), len(row.Support))
		}
		for _, fam := range CanonicalFamilies {
			if _, ok := row.Support[fam]; !ok {
				return fmt.Errorf("provider: row %q missing evaluation for family %q", row.ID, fam)
			}
		}
	}

	for _, fam := range CanonicalFamilies {
		if !slices.Contains(m.Providers, fam) {
			return fmt.Errorf("provider: providers header missing family %q", fam)
		}
	}

	return nil
}
