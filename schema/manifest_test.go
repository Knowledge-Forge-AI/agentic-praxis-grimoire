package schema_test

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/schema"
)

func TestValidateDispatcherSchemaManifest_CommittedFile(t *testing.T) {
	manifestPath := filepath.Join("..", "docs", "architecture", "dispatcher-sqlite-schema-v5.json")
	data, err := os.ReadFile(manifestPath)
	if err != nil {
		t.Fatalf("failed to read %s: %v", manifestPath, err)
	}

	var m schema.DispatcherSchemaManifest
	if err := json.Unmarshal(data, &m); err != nil {
		t.Fatalf("failed to unmarshal manifest: %v", err)
	}

	if err := schema.ValidateDispatcherSchemaManifest(m); err != nil {
		t.Fatalf("manifest validation failed: %v", err)
	}

	if m.Version != 5 {
		t.Errorf("expected version 5, got %d", m.Version)
	}

	// Verify required tables are present
	for _, req := range []string{
		"runs",
		"review_mutation_observations",
		"review_mutation_policies",
		"legacy_quarantine_review_mutation_observations",
		"legacy_quarantine_review_mutation_policies",
	} {
		tbl, ok := m.Tables[req]
		if !ok {
			t.Errorf("table %s missing from manifest", req)
			continue
		}
		if len(tbl.Columns) == 0 {
			t.Errorf("table %s has no columns", req)
		}
	}
}

func TestValidateDispatcherSchemaManifest_ValidationErrors(t *testing.T) {
	valid := schema.DispatcherSchemaManifest{
		Schema:  schema.DispatcherSchemaManifestSchema,
		Version: schema.DispatcherSchemaVersion,
		Tables: map[string]schema.TableShape{
			"runs":                                           {Columns: []schema.ColumnShape{{Name: "run_id"}}},
			"actor_bindings":                                 {Columns: []schema.ColumnShape{{Name: "binding_id"}}},
			"semantic_responsibilities":                      {Columns: []schema.ColumnShape{{Name: "id"}}},
			"invocation_attempts":                            {Columns: []schema.ColumnShape{{Name: "attempt_id"}}},
			"route_resolutions":                              {Columns: []schema.ColumnShape{{Name: "resolution_id"}}},
			"operational_observations":                       {Columns: []schema.ColumnShape{{Name: "observation_id"}}},
			"review_mutation_observations":                   {Columns: []schema.ColumnShape{{Name: "run_id"}}},
			"review_mutation_policies":                       {Columns: []schema.ColumnShape{{Name: "run_id"}}},
			"legacy_quarantine_review_mutation_observations": {Columns: []schema.ColumnShape{{Name: "run_id"}}},
			"legacy_quarantine_review_mutation_policies":     {Columns: []schema.ColumnShape{{Name: "run_id"}}},
		},
	}

	if err := schema.ValidateDispatcherSchemaManifest(valid); err != nil {
		t.Fatalf("expected valid manifest, got: %v", err)
	}

	// Bad schema
	badSchema := valid
	badSchema.Schema = "bad-schema"
	if err := schema.ValidateDispatcherSchemaManifest(badSchema); err == nil {
		t.Error("expected error for bad schema, got nil")
	}

	// Bad version
	badVer := valid
	badVer.Version = 4
	if err := schema.ValidateDispatcherSchemaManifest(badVer); err == nil {
		t.Error("expected error for bad version, got nil")
	}

	// Empty tables
	emptyTables := valid
	emptyTables.Tables = nil
	if err := schema.ValidateDispatcherSchemaManifest(emptyTables); err == nil {
		t.Error("expected error for empty tables, got nil")
	}

	// Missing required table
	missingTbl := valid
	missingTbl.Tables = make(map[string]schema.TableShape)
	for k, v := range valid.Tables {
		if k != "runs" {
			missingTbl.Tables[k] = v
		}
	}
	if err := schema.ValidateDispatcherSchemaManifest(missingTbl); err == nil {
		t.Error("expected error for missing table runs, got nil")
	}
}
