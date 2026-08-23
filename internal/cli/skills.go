package cli

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"syscall"

	apgskills "github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/skills"
)

const maxSkillDocumentBytes = 4 << 20

func runSkills(ctx context.Context, arguments []string, stdin io.Reader, stdout io.Writer) error {
	if len(arguments) == 0 {
		return usageError{"skills requires a command"}
	}
	switch arguments[0] {
	case "list":
		return runSkillsList(arguments[1:], stdout)
	case "context-report":
		return runSkillsContext(arguments[1:], stdout)
	case "resolve":
		return runSkillsResolve(ctx, arguments[1:], stdin, stdout)
	case "materialize":
		return runSkillsMaterialize(ctx, arguments[1:], stdout)
	case "verify-corpus":
		return runSkillsVerifyCorpus(arguments[1:])
	default:
		return usageError{"unknown skills command"}
	}
}

func runSkillsList(arguments []string, stdout io.Writer) error {
	jsonOutput, err := parseSkillFormat(arguments, false)
	if err != nil {
		return err
	}
	metadata, err := apgskills.Metadata()
	if err != nil {
		return err
	}
	if !jsonOutput {
		for _, skill := range metadata.Skills {
			fmt.Fprintln(stdout, skill.ID)
		}
		return nil
	}
	rows := make([]map[string]any, 0, len(metadata.Skills))
	for _, skill := range metadata.Skills {
		rows = append(rows, compatibilitySkillRow(skill))
	}
	content, err := pythonStyleJSON(rows)
	if err == nil {
		_, err = stdout.Write(content)
	}
	return err
}

func runSkillsContext(arguments []string, stdout io.Writer) error {
	jsonOutput, err := parseSkillFormat(arguments, true)
	if err != nil {
		return err
	}
	metadata, err := apgskills.Metadata()
	if err != nil {
		return err
	}
	ordered := append([]apgskills.SkillMetadata(nil), metadata.Skills...)
	sort.Slice(ordered, func(left, right int) bool {
		if ordered[left].DescriptionBytes != ordered[right].DescriptionBytes {
			return ordered[left].DescriptionBytes > ordered[right].DescriptionBytes
		}
		return ordered[left].ID < ordered[right].ID
	})
	if !jsonOutput {
		fmt.Fprintf(stdout, "discoverable skills: %d\n", len(metadata.Skills))
		fmt.Fprintf(stdout, "description bytes: %d\n", metadata.DescriptionBytes)
		fmt.Fprintf(stdout, "description characters: %d\n", metadata.DescriptionCharacters)
		for _, skill := range ordered {
			fmt.Fprintf(stdout, "%s: %d bytes, %d characters\n", skill.ID, skill.DescriptionBytes, skill.DescriptionCharacters)
		}
		return nil
	}
	rows := make([]map[string]any, 0, len(ordered))
	for _, skill := range ordered {
		rows = append(rows, compatibilitySkillRow(skill))
	}
	report := map[string]any{
		"discoverable_skill_count": len(metadata.Skills), "malformed": []any{}, "skill_count": len(metadata.Skills), "skills": rows,
		"total_bytes": metadata.DescriptionBytes, "total_characters": metadata.DescriptionCharacters,
		"total_description_bytes": metadata.DescriptionBytes, "total_description_characters": metadata.DescriptionCharacters,
	}
	content, err := pythonStyleJSON(report)
	if err == nil {
		_, err = stdout.Write(content)
	}
	return err
}

func compatibilitySkillRow(skill apgskills.SkillMetadata) map[string]any {
	return map[string]any{
		"blob_bytes": skill.BodyBytes, "blob_characters": skill.BodyCharacters,
		"bytes": skill.DescriptionBytes, "characters": skill.DescriptionCharacters,
		"description": skill.Description, "description_bytes": skill.DescriptionBytes, "description_characters": skill.DescriptionCharacters,
		"lines": skill.Lines, "name": skill.ID, "path": "skills/" + skill.CanonicalPath, "sha256": skill.BodySHA256,
	}
}

func parseSkillFormat(arguments []string, defaultJSON bool) (bool, error) {
	jsonOutput := defaultJSON
	seenJSON, seenFormat := false, false
	for position := 0; position < len(arguments); position++ {
		switch arguments[position] {
		case "--json":
			if seenJSON || seenFormat {
				return false, usageError{"output format may be specified only once"}
			}
			seenJSON = true
			jsonOutput = true
		case "--format":
			if seenJSON || seenFormat {
				return false, usageError{"output format may be specified only once"}
			}
			seenFormat = true
			position++
			if position >= len(arguments) {
				return false, usageError{"--format requires a value"}
			}
			if arguments[position] != "json" && arguments[position] != "text" {
				return false, usageError{"--format must be json or text"}
			}
			jsonOutput = arguments[position] == "json"
		default:
			return false, usageError{"unknown skills output option"}
		}
	}
	return jsonOutput, nil
}

func runSkillsResolve(ctx context.Context, arguments []string, stdin io.Reader, stdout io.Writer) error {
	content, err := readOneSkillInput(arguments, "--request", "--stdin", stdin)
	if err != nil {
		return err
	}
	request, err := apgskills.DecodeBundleRequest(content)
	if err != nil {
		return err
	}
	result, err := apgskills.Resolve(ctx, request)
	if err != nil {
		return err
	}
	content, err = result.CanonicalJSON()
	if err == nil {
		_, err = stdout.Write(content)
	}
	return err
}

func runSkillsMaterialize(ctx context.Context, arguments []string, stdout io.Writer) error {
	resultPath, parent, err := parseMaterializeArguments(arguments)
	if err != nil {
		return err
	}
	content, err := readPrivateDocument(resultPath)
	if err != nil {
		return err
	}
	result, err := apgskills.DecodeBundleResult(content)
	if err != nil {
		return err
	}
	materialized, err := apgskills.Materialize(ctx, apgskills.MaterializeRequest{DestinationParent: parent, Result: result})
	if err != nil {
		return err
	}
	content, err = materialized.CanonicalJSON()
	if err == nil {
		_, err = stdout.Write(content)
	}
	return err
}

func readOneSkillInput(arguments []string, pathFlag, stdinFlag string, stdin io.Reader) ([]byte, error) {
	if len(arguments) == 1 && arguments[0] == stdinFlag {
		return readBounded(stdin)
	}
	if len(arguments) == 2 && arguments[0] == pathFlag {
		return readPrivateDocument(arguments[1])
	}
	return nil, usageError{"resolve requires exactly one of --stdin or --request FILE"}
}

func parseMaterializeArguments(arguments []string) (string, string, error) {
	values := map[string]string{}
	for len(arguments) > 0 {
		if len(arguments) < 2 || (arguments[0] != "--result" && arguments[0] != "--destination-parent") || values[arguments[0]] != "" {
			return "", "", usageError{"materialize requires one --result and one --destination-parent"}
		}
		values[arguments[0]] = arguments[1]
		arguments = arguments[2:]
	}
	if values["--result"] == "" || values["--destination-parent"] == "" {
		return "", "", usageError{"materialize requires one --result and one --destination-parent"}
	}
	return values["--result"], values["--destination-parent"], nil
}

func readPrivateDocument(name string) ([]byte, error) {
	if name == "" || !filepath.IsAbs(name) || filepath.Clean(name) != name {
		return nil, usageError{"input file must be absolute and clean"}
	}
	before, err := os.Lstat(name)
	if err != nil || !before.Mode().IsRegular() || before.Mode()&os.ModeSymlink != 0 || before.Mode().Perm() != 0o600 || !ownedSingleLink(before) || before.Size() > maxSkillDocumentBytes {
		return nil, errors.New("skill document input is unsafe")
	}
	file, err := os.OpenFile(name, os.O_RDONLY|syscall.O_NOFOLLOW, 0)
	if err != nil {
		return nil, errors.New("skill document input is unsafe")
	}
	defer file.Close()
	content, err := readBounded(file)
	if err != nil {
		return nil, err
	}
	after, err := os.Lstat(name)
	if err != nil || !os.SameFile(before, after) || after.Size() != int64(len(content)) {
		return nil, errors.New("skill document input changed during read")
	}
	return content, nil
}

func readBounded(reader io.Reader) ([]byte, error) {
	content, err := io.ReadAll(io.LimitReader(reader, maxSkillDocumentBytes+1))
	if err != nil || len(content) == 0 || len(content) > maxSkillDocumentBytes {
		return nil, errors.New("skill document input is empty or oversized")
	}
	return content, nil
}

func ownedSingleLink(info os.FileInfo) bool {
	stat, ok := info.Sys().(*syscall.Stat_t)
	return ok && stat.Uid == uint32(os.Getuid()) && stat.Nlink == 1
}

func pythonStyleJSON(value any) ([]byte, error) {
	compact, err := json.Marshal(value)
	if err != nil {
		return nil, err
	}
	result := make([]byte, 0, len(compact)+64)
	quoted, escaped := false, false
	for _, character := range compact {
		result = append(result, byte(character))
		if quoted {
			if escaped {
				escaped = false
			} else if character == '\\' {
				escaped = true
			} else if character == '"' {
				quoted = false
			}
			continue
		}
		if character == '"' {
			quoted = true
		} else if character == ',' || character == ':' {
			result = append(result, ' ')
		}
	}
	return append(result, '\n'), nil
}
