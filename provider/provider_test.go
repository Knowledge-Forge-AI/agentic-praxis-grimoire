package provider_test

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/provider"
)

func TestLoadConformanceMatrix_CommittedFile(t *testing.T) {
	path := filepath.Join("..", "docs", "architecture", "provider-conformance-matrix.json")
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("failed to read matrix file %s: %v", path, err)
	}

	matrix, err := provider.LoadConformanceMatrix(data)
	if err != nil {
		t.Fatalf("LoadConformanceMatrix failed: %v", err)
	}

	if len(matrix.Rows) != provider.RequiredRowCount {
		t.Errorf("expected %d rows, got %d", provider.RequiredRowCount, len(matrix.Rows))
	}

	if len(matrix.Providers) != 3 {
		t.Errorf("expected 3 providers, got %d", len(matrix.Providers))
	}
}

func TestValidateMatrix_RejectsInvalidRowCount(t *testing.T) {
	m := provider.ConformanceMatrix{
		Schema:    provider.ConformanceMatrixSchema,
		Providers: provider.CanonicalFamilies,
		Rows:      []provider.ConformanceRow{}, // empty
	}
	if err := provider.ValidateMatrix(&m); err == nil {
		t.Fatal("expected error for empty matrix, got nil")
	}
}
