package skills

import (
	"encoding/json"
	"fmt"
	"sort"
	"strings"
)

// BuildCatalog is a provisional pure selection boundary. Malformed optional
// leaves are partial-list diagnostics; duplicate identities and invalid override
// declarations are input errors. It never reads paths or mutates a shared cache.
func BuildCatalog(input CatalogInput) (Catalog, error) {
	if input.SchemaVersion != CatalogSchemaV1 {
		return Catalog{}, fmt.Errorf("unsupported catalog input version")
	}
	if len(input.Snapshots) > 4096 {
		return Catalog{}, fmt.Errorf("catalog exceeds snapshot limit")
	}
	total := 0
	for _, s := range input.Snapshots {
		total += len(s.Body)
		for _, b := range s.Support {
			total += len(b)
		}
	}
	if total > 64<<20 {
		return Catalog{}, fmt.Errorf("catalog exceeds byte limit")
	}
	var gen catalogGeneration
	if err := json.Unmarshal(generatedCatalog, &gen); err != nil {
		return Catalog{}, err
	}
	if gen.SchemaVersion != CatalogSchemaV1 {
		return Catalog{}, fmt.Errorf("invalid generated catalog version")
	}
	index, err := loadIndex()
	if err != nil {
		return Catalog{}, err
	}
	// JSON roundtrip gives callers sole ownership of every nested input collection.
	raw, err := json.Marshal(input)
	if err != nil {
		return Catalog{}, err
	}
	var ownedInput CatalogInput
	if err = json.Unmarshal(raw, &ownedInput); err != nil {
		return Catalog{}, err
	}
	input = ownedInput
	c := Catalog{DerivationInputs: gen.Authorities, SchemaVersion: CatalogSchemaV1, RuleVersion: CatalogRuleVersionV1, Skills: gen.Skills, Snapshots: []SkillSnapshot{}, Overrides: input.Overrides, Diagnostics: input.Diagnostics, Sources: input.Sources}
	if len(c.Skills) != len(index.skills) {
		return Catalog{}, fmt.Errorf("embedded descriptor membership drift")
	}
	seen := map[string]bool{}
	for _, d := range c.Skills {
		metadata, ok := index.byID[d.ID]
		if !ok || metadata.BodySHA256 != d.BodySHA256 {
			return Catalog{}, fmt.Errorf("embedded descriptor drift")
		}
		if seen[d.QualifiedID] {
			return Catalog{}, fmt.Errorf("duplicate embedded descriptor")
		}
		seen[d.QualifiedID] = true
		c.Snapshots = append(c.Snapshots, SkillSnapshot{QualifiedID: d.QualifiedID, Path: "skills/" + d.CanonicalPath, Body: append([]byte(nil), index.bodyByID[d.ID]...), Support: gen.Support[d.QualifiedID]})
	}
	for _, snapshot := range input.Snapshots {
		source, _, err := qualifiedParts(snapshot.QualifiedID)
		if err != nil || source == "apgr" {
			return Catalog{}, fmt.Errorf("external snapshot has invalid source identity")
		}
		if seen[snapshot.QualifiedID] {
			return Catalog{}, fmt.Errorf("duplicate source ID %s", snapshot.QualifiedID)
		}
		seen[snapshot.QualifiedID] = true
		d, err := descriptor(snapshot)
		if err != nil {
			c.Diagnostics = append(c.Diagnostics, CatalogDiagnostic{snapshot.QualifiedID, snapshot.Path, err.Error()})
			continue
		}
		c.Skills = append(c.Skills, d)
		c.Snapshots = append(c.Snapshots, snapshot)
	}
	sort.Slice(c.Skills, func(i, j int) bool { return c.Skills[i].QualifiedID < c.Skills[j].QualifiedID })
	sort.Slice(c.Snapshots, func(i, j int) bool { return c.Snapshots[i].QualifiedID < c.Snapshots[j].QualifiedID })
	byID := map[string]SkillDescriptor{}
	for _, d := range c.Skills {
		byID[d.QualifiedID] = d
	}
	mapped := map[string]bool{}
	targets := map[string]bool{}
	for _, o := range c.Overrides {
		source, _, err := qualifiedParts(o.Requested)
		replacement, _, targetErr := qualifiedParts(o.Selected)
		if err != nil || targetErr != nil || source != "apgr" || replacement != "project" || mapped[o.Requested] || targets[o.Selected] || !validDigest(o.ConfigSHA256) || o.ConfigPath == "" {
			return Catalog{}, fmt.Errorf("invalid/conflicting project override")
		}
		if _, ok := byID[o.Requested]; !ok {
			return Catalog{}, fmt.Errorf("unknown override origin %s", o.Requested)
		}
		mapped[o.Requested] = true
		targets[o.Selected] = true
		if _, ok := byID[o.Selected]; !ok {
			c.Diagnostics = append(c.Diagnostics, CatalogDiagnostic{o.Requested, o.ConfigPath, "override replacement unavailable: " + o.Selected})
		}
	}
	// Missing targets and cycles are diagnosed without suppressing unrelated skills.
	for _, d := range c.Skills {
		if err := validateDependencies(d.QualifiedID, byID, map[string]bool{}); err != nil {
			c.Diagnostics = append(c.Diagnostics, CatalogDiagnostic{d.QualifiedID, "", err.Error()})
		}
	}
	sort.Slice(c.Overrides, func(i, j int) bool { return c.Overrides[i].Requested < c.Overrides[j].Requested })
	sort.Slice(c.Diagnostics, func(i, j int) bool {
		a, b := c.Diagnostics[i], c.Diagnostics[j]
		return a.Identity+"\x00"+a.Path+"\x00"+a.Message < b.Identity+"\x00"+b.Path+"\x00"+b.Message
	})
	sort.Slice(c.Sources, func(i, j int) bool { return c.Sources[i].Source < c.Sources[j].Source })
	for _, snapshot := range c.Snapshots {
		c.Provenance = append(c.Provenance, CatalogProvenance{snapshot.QualifiedID, snapshot.Path, sha256Hex(snapshot.Body)})
	}
	// Content fingerprint excludes operation paths; config bytes remain authority.
	relations := []CatalogOverride{}
	for _, o := range c.Overrides {
		o.ConfigPath = ""
		relations = append(relations, o)
	}
	identity, _ := json.Marshal(struct {
		Version     string
		Authorities []CatalogFile
		Skills      []SkillDescriptor
		Overrides   []CatalogOverride
	}{CatalogRuleVersionV1, gen.Authorities, c.Skills, relations})
	c.Fingerprint = sha256Hex(identity)
	return c, nil
}

func validDigest(s string) bool {
	if len(s) != 64 {
		return false
	}
	for _, r := range s {
		if !(r >= '0' && r <= '9' || r >= 'a' && r <= 'f') {
			return false
		}
	}
	return true
}
func validateDependencies(id string, byID map[string]SkillDescriptor, active map[string]bool) error {
	if active["done:"+id] {
		return nil
	}
	if active[id] {
		return fmt.Errorf("required dependency cycle at %s", id)
	}
	d, ok := byID[id]
	if !ok {
		return fmt.Errorf("missing required dependency %s", id)
	}
	active[id] = true
	defer delete(active, id)
	for _, dep := range d.RequiredDependencies {
		if err := validateDependencies(dep, byID, active); err != nil {
			return err
		}
	}
	active["done:"+id] = true
	return nil
}

// ResolveCatalog explicitly selects a qualified body. Bare IDs are accepted only
// when unique across all sources; unlike legacy Resolve, ambiguity is an error.
// Required edges are validated, never automatically packed or materialized.
func ResolveCatalog(input CatalogInput, requested string, consumer ConsumerKind) (CatalogSelection, error) {
	switch consumer {
	case ConsumerClaude, ConsumerCodex, ConsumerGo, ConsumerChatGPT:
	default:
		return CatalogSelection{}, ErrConsumerMismatch
	}
	c, err := BuildCatalog(input)
	if err != nil {
		return CatalogSelection{}, err
	}
	original := requested
	if !strings.Contains(requested, ":") {
		matches := []string{}
		for _, d := range c.Skills {
			if d.ID == requested {
				matches = append(matches, d.QualifiedID)
			}
		}
		if len(matches) != 1 {
			return CatalogSelection{}, fmt.Errorf("unknown or ambiguous skill %q; use a qualified identity", requested)
		}
		requested = matches[0]
	}
	selected := requested
	for _, o := range c.Overrides {
		if o.Requested == requested {
			selected = o.Selected
		}
	}
	for _, diag := range c.Diagnostics {
		if diag.Identity == requested || diag.Identity == selected {
			return CatalogSelection{}, fmt.Errorf("%s: %s", diag.Identity, diag.Message)
		}
	}
	for _, d := range c.Skills {
		if d.QualifiedID == selected {
			// Overriding a nested manager leaf cannot widen its canonical consumer scope.
			for _, candidate := range c.Skills {
				if candidate.QualifiedID == requested && strings.HasPrefix(candidate.CanonicalPath, "chatgpt/") && consumer != ConsumerChatGPT {
					return CatalogSelection{}, ErrConsumerMismatch
				}
			}
			if strings.HasPrefix(d.CanonicalPath, "chatgpt/") && consumer != ConsumerChatGPT {
				return CatalogSelection{}, ErrConsumerMismatch
			}
			for _, s := range c.Snapshots {
				if s.QualifiedID == selected {
					return CatalogSelection{original, selected, d.BodySHA256, d.ContentIdentity, c.Fingerprint, CatalogRuleVersionV1, s}, nil
				}
			}
		}
	}
	return CatalogSelection{}, fmt.Errorf("selected skill unavailable: %s", selected)
}

// DecodeCatalogInput strictly decodes the versioned explicit bridge input.
func DecodeCatalogInput(data []byte) (CatalogInput, error) {
	if _, err := scanJSONObject(data); err != nil {
		return CatalogInput{}, err
	}
	var input CatalogInput
	if err := decodeTyped(data, &input); err != nil {
		return CatalogInput{}, err
	}
	if input.SchemaVersion != CatalogSchemaV1 {
		return input, fmt.Errorf("unsupported catalog input schema")
	}
	return input, nil
}
