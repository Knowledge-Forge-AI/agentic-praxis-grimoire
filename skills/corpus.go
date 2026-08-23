// Package skills embeds the canonical APG skill corpus and resolves
// deterministic, task-scoped bundles without prompt interpretation.
package skills

import (
	"bytes"
	"embed"
	"encoding/json"
	"fmt"
	"io/fs"
	"path"
	"sort"
	"strings"
	"sync"
	"unicode/utf8"
)

//go:embed */SKILL.md chatgpt/*/SKILL.md
var embeddedCorpus embed.FS

type corpusIndex struct {
	byID                  map[string]SkillMetadata
	bodyByID              map[string][]byte
	descriptionBytes      int64
	descriptionCharacters int64
	fingerprint           string
	manifestJSON          []byte
	skills                []SkillMetadata
}

var (
	indexOnce  sync.Once
	indexValue corpusIndex
	indexError error
)

// Corpus returns a read-only filesystem containing only canonical embedded
// skill leaves. It never reads the host checkout.
func Corpus() fs.FS { return embeddedCorpus }

// Metadata returns a caller-owned projection reconstructed from embedded skill
// bodies.
func Metadata() (CorpusMetadata, error) {
	index, err := loadIndex()
	if err != nil {
		return CorpusMetadata{}, err
	}
	return CorpusMetadata{
		DescriptionBytes:      index.descriptionBytes,
		DescriptionCharacters: index.descriptionCharacters,
		Fingerprint:           index.fingerprint,
		ManifestJSON:          append([]byte(nil), index.manifestJSON...),
		Skills:                append([]SkillMetadata(nil), index.skills...),
	}, nil
}

func loadIndex() (corpusIndex, error) {
	indexOnce.Do(func() { indexValue, indexError = buildIndex(embeddedCorpus) })
	return indexValue, indexError
}

func buildIndex(corpus fs.FS) (corpusIndex, error) {
	flat, err := fs.Glob(corpus, "*/SKILL.md")
	if err != nil {
		return corpusIndex{}, fmt.Errorf("%w: flat embed pattern", ErrCorpusMismatch)
	}
	nested, err := fs.Glob(corpus, "chatgpt/*/SKILL.md")
	if err != nil {
		return corpusIndex{}, fmt.Errorf("%w: nested embed pattern", ErrCorpusMismatch)
	}
	paths := append(flat, nested...)
	sort.Strings(paths)
	if len(paths) != 39 {
		return corpusIndex{}, fmt.Errorf("%w: expected 39 leaves", ErrCorpusMismatch)
	}
	index := corpusIndex{byID: map[string]SkillMetadata{}, bodyByID: map[string][]byte{}}
	for _, relative := range paths {
		body, readErr := fs.ReadFile(corpus, relative)
		if readErr != nil {
			return corpusIndex{}, fmt.Errorf("%w: unreadable leaf", ErrCorpusMismatch)
		}
		metadata, parseErr := parseSkill(relative, body)
		if parseErr != nil {
			return corpusIndex{}, parseErr
		}
		if _, exists := index.byID[metadata.ID]; exists {
			return corpusIndex{}, fmt.Errorf("%w: duplicate skill ID", ErrCorpusMismatch)
		}
		index.byID[metadata.ID] = metadata
		index.bodyByID[metadata.ID] = append([]byte(nil), body...)
		index.skills = append(index.skills, metadata)
		index.descriptionBytes += metadata.DescriptionBytes
		index.descriptionCharacters += metadata.DescriptionCharacters
	}
	sort.Slice(index.skills, func(left, right int) bool { return index.skills[left].ID < index.skills[right].ID })
	if index.descriptionBytes != 9504 || index.descriptionCharacters != 9492 || index.descriptionBytes > GlobalDescriptionLimit {
		return corpusIndex{}, fmt.Errorf("%w: canonical description footprint", ErrCorpusMismatch)
	}
	manifest := metadataManifest{SchemaVersion: 1, Skills: make([]metadataRow, 0, len(index.skills))}
	for _, skill := range index.skills {
		manifest.Skills = append(manifest.Skills, metadataRow{
			Name: skill.ID, Description: skill.Description, Path: "skills/" + skill.CanonicalPath,
			SourceBlobBytes: skill.BodyBytes, SourceBlobCharacters: skill.BodyCharacters,
			SourceLines: skill.Lines, SourceSHA256: skill.BodySHA256,
		})
	}
	index.manifestJSON, err = json.Marshal(manifest)
	if err != nil {
		return corpusIndex{}, fmt.Errorf("%w: metadata serialization", ErrCorpusMismatch)
	}
	index.manifestJSON = append(index.manifestJSON, '\n')
	index.fingerprint = sha256Hex(index.manifestJSON)
	return index, nil
}

type metadataManifest struct {
	SchemaVersion int           `json:"schema_version"`
	Skills        []metadataRow `json:"skills"`
}

type metadataRow struct {
	Name                 string `json:"name"`
	Description          string `json:"description"`
	Path                 string `json:"path"`
	SourceBlobBytes      int64  `json:"source_blob_bytes"`
	SourceBlobCharacters int64  `json:"source_blob_characters"`
	SourceLines          int64  `json:"source_lines"`
	SourceSHA256         string `json:"source_sha256"`
}

func parseSkill(relative string, body []byte) (SkillMetadata, error) {
	if !utf8.Valid(body) {
		return SkillMetadata{}, fmt.Errorf("%w: non-UTF-8 leaf", ErrCorpusMismatch)
	}
	parts := strings.Split(relative, "/")
	var pathID string
	switch {
	case len(parts) == 2 && parts[1] == "SKILL.md":
		pathID = parts[0]
	case len(parts) == 3 && parts[0] == "chatgpt" && parts[2] == "SKILL.md":
		pathID = parts[1]
	default:
		return SkillMetadata{}, fmt.Errorf("%w: invalid canonical path", ErrCorpusMismatch)
	}
	lines := strings.Split(string(body), "\n")
	if len(lines) < 5 || lines[0] != "---" {
		return SkillMetadata{}, fmt.Errorf("%w: missing front matter", ErrCorpusMismatch)
	}
	end := -1
	for position := 1; position < len(lines); position++ {
		if lines[position] == "---" {
			end = position
			break
		}
	}
	if end < 0 {
		return SkillMetadata{}, fmt.Errorf("%w: unterminated front matter", ErrCorpusMismatch)
	}
	values := map[string]string{}
	for _, line := range lines[1:end] {
		key, value, ok := strings.Cut(line, ": ")
		if !ok || key == "" || value == "" {
			return SkillMetadata{}, fmt.Errorf("%w: malformed front matter", ErrCorpusMismatch)
		}
		if _, exists := values[key]; exists {
			return SkillMetadata{}, fmt.Errorf("%w: duplicate front matter key", ErrCorpusMismatch)
		}
		values[key] = value
	}
	if len(values) != 2 || values["name"] == "" || values["description"] == "" || values["name"] != pathID {
		return SkillMetadata{}, fmt.Errorf("%w: name/path/front matter mismatch", ErrCorpusMismatch)
	}
	lineCount := bytes.Count(body, []byte{'\n'})
	if len(body) > 0 && body[len(body)-1] != '\n' {
		lineCount++
	}
	description := values["description"]
	return SkillMetadata{
		BodyBytes: int64(len(body)), BodyCharacters: int64(utf8.RuneCount(body)), BodySHA256: sha256Hex(body),
		CanonicalPath: path.Clean(relative), Description: description,
		DescriptionBytes: int64(len([]byte(description))), DescriptionCharacters: int64(utf8.RuneCountInString(description)),
		ID: pathID, Lines: int64(lineCount),
	}, nil
}
