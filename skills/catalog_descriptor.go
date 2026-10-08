package skills

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io/fs"
	"regexp"
	"sort"
	"strings"
	"unicode/utf8"
)

var catalogID = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$`)

func qualifiedParts(id string) (string, string, error) {
	source, name, ok := strings.Cut(id, ":")
	if !ok || !catalogID.MatchString(name) || name == "." || name == ".." || (source != "apgr" && source != "project" && source != "user") {
		return "", "", fmt.Errorf("invalid qualified skill identity %q", id)
	}
	return source, name, nil
}

// Catalog declarations use JSON arrays on single frontmatter lines; this is a
// closed metadata grammar, not general YAML. Prose never declares dependencies.
func catalogMetadata(body []byte) (map[string]string, []byte, error) {
	if len(body) > MaxCatalogFileBytes || !utf8.Valid(body) {
		return nil, nil, fmt.Errorf("oversize or non-UTF-8 skill")
	}
	lines := bytes.SplitAfter(body, []byte("\n"))
	if len(lines) < 4 || string(lines[0]) != "---\n" {
		return nil, nil, fmt.Errorf("missing frontmatter")
	}
	fields := map[string]string{}
	offset := len(lines[0])
	for _, line := range lines[1:] {
		offset += len(line)
		value := strings.TrimSuffix(string(line), "\n")
		if value == "---" {
			return fields, body[offset:], nil
		}
		key, val, ok := strings.Cut(value, ": ")
		if !ok || val == "" {
			return nil, nil, fmt.Errorf("malformed frontmatter")
		}
		switch key {
		case "name", "description", "requires", "support", "maturity":
		default:
			return nil, nil, fmt.Errorf("unknown frontmatter key %s", key)
		}
		if _, ok := fields[key]; ok {
			return nil, nil, fmt.Errorf("duplicate frontmatter key %s", key)
		}
		fields[key] = val
	}
	return nil, nil, fmt.Errorf("unterminated frontmatter")
}

func declaredList(fields map[string]string, key string) ([]string, error) {
	values := []string{}
	if raw, ok := fields[key]; ok {
		if err := json.Unmarshal([]byte(raw), &values); err != nil || values == nil || len(values) > 32 {
			return nil, fmt.Errorf("invalid %s declaration", key)
		}
	}
	sort.Strings(values)
	for i, v := range values {
		if v == "" || (i > 0 && values[i-1] == v) {
			return nil, fmt.Errorf("duplicate/empty %s declaration", key)
		}
	}
	return values, nil
}

func materialSection(body []byte, name string) string {
	lines := strings.Split(string(body), "\n")
	start := -1
	for i, line := range lines {
		if line == "## "+name {
			start = i + 1
			continue
		}
		if start >= 0 && strings.HasPrefix(line, "## ") {
			return strings.TrimSpace(strings.Join(lines[start:i], "\n"))
		}
	}
	if start >= 0 {
		return strings.TrimSpace(strings.Join(lines[start:], "\n"))
	}
	return ""
}

func descriptor(snapshot SkillSnapshot) (SkillDescriptor, error) {
	_, id, err := qualifiedParts(snapshot.QualifiedID)
	if err != nil {
		return SkillDescriptor{}, err
	}
	fields, body, err := catalogMetadata(snapshot.Body)
	if err != nil {
		return SkillDescriptor{}, err
	}
	if fields["name"] != id || fields["description"] == "" {
		return SkillDescriptor{}, fmt.Errorf("name/path/frontmatter mismatch")
	}
	// Retain the legacy parser and its exact whole-file measurement contract.
	clean := []byte("---\nname: " + id + "\ndescription: " + fields["description"] + "\n---\n")
	metadata, err := parseSkill(id+"/SKILL.md", append(clean, body...))
	if err != nil {
		return SkillDescriptor{}, err
	}
	metadata.BodyBytes = int64(len(snapshot.Body))
	metadata.BodyCharacters = int64(utf8.RuneCount(snapshot.Body))
	metadata.BodySHA256 = sha256Hex(snapshot.Body)
	metadata.Lines = int64(bytes.Count(snapshot.Body, []byte{'\n'}))
	if len(snapshot.Body) > 0 && snapshot.Body[len(snapshot.Body)-1] != '\n' {
		metadata.Lines++
	}
	deps, err := declaredList(fields, "requires")
	if err != nil {
		return SkillDescriptor{}, err
	}
	for _, dep := range deps {
		if _, _, err := qualifiedParts(dep); err != nil {
			return SkillDescriptor{}, err
		}
	}
	support, err := declaredList(fields, "support")
	if err != nil {
		return SkillDescriptor{}, err
	}
	d := SkillDescriptor{SchemaVersion: DescriptorSchemaV1, QualifiedID: snapshot.QualifiedID, SkillMetadata: metadata,
		BodyOnlyBytes: int64(len(body)), BodyOnlyCharacters: int64(utf8.RuneCount(body)), BodyOnlySHA256: sha256Hex(body), DescriptionSHA256: sha256Hex([]byte(metadata.Description)),
		DoNotUse: materialSection(body, "Do not use"), ProjectOwnedParameters: materialSection(body, "Project-owned parameters"),
		Maturity: "unqualified", SourceDeclaredMaturity: fields["maturity"], ConsumerLimitations: []string{}, SelectionFacts: []SelectionRule{}, RequiredDependencies: deps, SupportFiles: []CatalogFile{}}
	if len(snapshot.Support) != len(support) {
		return SkillDescriptor{}, fmt.Errorf("support snapshot differs from declarations")
	}
	for _, name := range support {
		if !fs.ValidPath(name) || name == "SKILL.md" || strings.Contains(name, "\\") {
			return SkillDescriptor{}, fmt.Errorf("invalid support path")
		}
		data, ok := snapshot.Support[name]
		if !ok || len(data) > MaxCatalogFileBytes {
			return SkillDescriptor{}, fmt.Errorf("missing/oversize support file %s", name)
		}
		d.SupportFiles = append(d.SupportFiles, CatalogFile{Path: name, Bytes: int64(len(data)), SHA256: sha256Hex(data), Captured: true})
	}
	sealDescriptor(&d)
	return d, nil
}

func sealDescriptor(d *SkillDescriptor) {
	d.ContentIdentity = ""
	data, _ := json.Marshal(d)
	d.ContentIdentity = sha256Hex(data)
}
