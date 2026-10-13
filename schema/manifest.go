package schema

import (
	"errors"
	"fmt"
)

// DispatcherSchemaManifestSchema is the canonical schema identifier for v5.
const DispatcherSchemaManifestSchema = "dispatcher-sqlite-schema-v5"

// DispatcherSchemaVersion is the current SQLite schema version.
const DispatcherSchemaVersion = 5

// DispatcherSchemaManifest describes the complete SQLite database schema.
type DispatcherSchemaManifest struct {
	Schema  string                `json:"schema"`
	Version int                   `json:"version"`
	Tables  map[string]TableShape `json:"tables"`
}

// TableShape describes the shape of a single SQLite table.
type TableShape struct {
	Columns     []ColumnShape     `json:"columns"`
	ForeignKeys []ForeignKeyShape `json:"foreign_keys"`
	Indexes     []IndexShape      `json:"indexes"`
}

// ColumnShape describes a column as returned by PRAGMA table_info.
type ColumnShape struct {
	CID          int     `json:"cid"`
	Name         string  `json:"name"`
	Type         string  `json:"type"`
	NotNull      bool    `json:"notnull"`
	DefaultValue *string `json:"default_value"`
	PK           int     `json:"pk"`
}

// ForeignKeyShape describes a foreign key relation as returned by PRAGMA foreign_key_list.
type ForeignKeyShape struct {
	ID         int    `json:"id"`
	Seq        int    `json:"seq"`
	ToTable    string `json:"to_table"`
	FromColumn string `json:"from_column"`
	ToColumn   string `json:"to_column"`
	OnUpdate   string `json:"on_update"`
	OnDelete   string `json:"on_delete"`
	Match      string `json:"match"`
}

// IndexShape describes an index as returned by PRAGMA index_list and index_info.
type IndexShape struct {
	Name    string   `json:"name"`
	Unique  bool     `json:"unique"`
	Origin  string   `json:"origin"`
	Partial bool     `json:"partial"`
	Columns []string `json:"columns"`
}

// ValidateDispatcherSchemaManifest performs structural validation on a schema manifest.
func ValidateDispatcherSchemaManifest(m DispatcherSchemaManifest) error {
	if m.Schema != DispatcherSchemaManifestSchema {
		return fmt.Errorf("invalid schema identifier: %q, expected %q", m.Schema, DispatcherSchemaManifestSchema)
	}
	if m.Version != DispatcherSchemaVersion {
		return fmt.Errorf("invalid schema version: %d, expected %d", m.Version, DispatcherSchemaVersion)
	}
	if len(m.Tables) == 0 {
		return errors.New("tables map must not be empty")
	}

	requiredTables := []string{
		"runs",
		"actor_bindings",
		"semantic_responsibilities",
		"invocation_attempts",
		"route_resolutions",
		"operational_observations",
		"review_mutation_observations",
		"review_mutation_policies",
		"legacy_quarantine_review_mutation_observations",
		"legacy_quarantine_review_mutation_policies",
	}

	for _, req := range requiredTables {
		tbl, ok := m.Tables[req]
		if !ok {
			return fmt.Errorf("missing required table: %s", req)
		}
		if len(tbl.Columns) == 0 {
			return fmt.Errorf("table %s has no columns", req)
		}
	}

	return nil
}
