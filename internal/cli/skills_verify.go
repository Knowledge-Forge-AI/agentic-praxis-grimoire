package cli

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"os"
	"path/filepath"
	"strings"

	apgskills "github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/skills"
)

func runSkillsVerifyCorpus(arguments []string) error {
	if len(arguments) != 2 || arguments[0] != "--repository" {
		return usageError{"verify-corpus requires one --repository PATH"}
	}
	root, err := directCorpusRoot(arguments[1])
	if err != nil {
		return err
	}
	metadata, err := apgskills.Metadata()
	if err != nil {
		return err
	}
	manifestPath := filepath.Join(root, "src", "agentic_praxis_grimoire", "resources", "skill-metadata.json")
	manifest, err := readDirectCorpusFile(root, manifestPath)
	if err != nil || !bytes.Equal(manifest, metadata.ManifestJSON) {
		return errors.New("checkout skill metadata disagrees with the embedded canonical corpus")
	}
	for _, skill := range metadata.Skills {
		name := filepath.Join(root, "skills", filepath.FromSlash(skill.CanonicalPath))
		body, readErr := readDirectCorpusFile(root, name)
		digest := sha256.Sum256(body)
		if readErr != nil || int64(len(body)) != skill.BodyBytes || hex.EncodeToString(digest[:]) != skill.BodySHA256 {
			return errors.New("checkout skill body disagrees with the embedded canonical corpus")
		}
	}
	return nil
}

func directCorpusRoot(value string) (string, error) {
	if value == "" || !filepath.IsAbs(value) || filepath.Clean(value) != value {
		return "", usageError{"--repository must be an absolute clean path"}
	}
	info, err := os.Lstat(value)
	if err != nil || !info.IsDir() || info.Mode()&os.ModeSymlink != 0 {
		return "", errors.New("skill repository root is unsafe")
	}
	resolved, err := filepath.EvalSymlinks(value)
	if err != nil || resolved != value {
		return "", errors.New("skill repository root is unsafe")
	}
	return value, nil
}

func readDirectCorpusFile(root, name string) ([]byte, error) {
	relative, err := filepath.Rel(root, name)
	if err != nil || relative == "." || relative == ".." || strings.HasPrefix(relative, ".."+string(filepath.Separator)) || filepath.IsAbs(relative) {
		return nil, errors.New("skill corpus path escapes the repository")
	}
	current := root
	for _, part := range splitPath(relative) {
		current = filepath.Join(current, part)
		info, statErr := os.Lstat(current)
		if statErr != nil || info.Mode()&os.ModeSymlink != 0 {
			return nil, errors.New("skill corpus path is unsafe")
		}
	}
	info, err := os.Lstat(name)
	if err != nil || !info.Mode().IsRegular() || info.Mode()&os.ModeSymlink != 0 {
		return nil, errors.New("skill corpus file is unsafe")
	}
	return os.ReadFile(name)
}

func splitPath(value string) []string {
	parts := []string{}
	for value != "." && value != string(filepath.Separator) && value != "" {
		directory, base := filepath.Split(value)
		parts = append([]string{base}, parts...)
		value = filepath.Clean(directory)
	}
	return parts
}
