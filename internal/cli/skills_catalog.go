package cli

import (
	"encoding/json"
	"fmt"
	apgskills "github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/skills"
	"io"
	"os"
)

func generateSkillCatalog(args []string, out io.Writer) error {
	if len(args) != 2 || args[0] != "--repository" {
		return usageError{"generate-catalog requires --repository PATH"}
	}
	data, err := apgskills.GenerateCatalog(os.DirFS(args[1]))
	if err == nil {
		_, err = out.Write(data)
	}
	return err
}

func runSkillCatalog(args []string, in io.Reader, out io.Writer) error {
	if len(args) < 1 || args[0] != "--stdin" {
		return usageError{"catalog requires --stdin"}
	}
	data, err := io.ReadAll(io.LimitReader(in, (64<<20)+1))
	if err != nil {
		return err
	}
	if len(data) > 64<<20 {
		return usageError{"catalog input too large"}
	}
	input, err := apgskills.DecodeCatalogInput(data)
	if err != nil {
		return err
	}
	for i := 1; i < len(args); i += 2 {
		if i+1 >= len(args) {
			return usageError{"source option requires path"}
		}
		source := ""
		switch args[i] {
		case "--project-root":
			source = "project"
		case "--apgr-home":
			source = "user"
		default:
			return usageError{"unknown catalog source option"}
		}
		captured, captureErr := apgskills.CaptureCatalogSource(source, args[i+1])
		if captureErr != nil {
			return captureErr
		}
		input.Snapshots = append(input.Snapshots, captured.Snapshots...)
		input.Diagnostics = append(input.Diagnostics, captured.Diagnostics...)
		input.Sources = append(input.Sources, captured.Sources...)
	}
	catalog, err := apgskills.BuildCatalog(input)
	if err != nil {
		return err
	}
	catalog.Snapshots = nil
	return json.NewEncoder(out).Encode(catalog)
}

func runSkillCatalogList(args []string, out io.Writer) error {
	input := apgskills.CatalogInput{SchemaVersion: apgskills.CatalogSchemaV1}
	format := []string{}
	for i := 0; i < len(args); i++ {
		switch args[i] {
		case "--all-sources":
		case "--project-root", "--apgr-home":
			key := args[i]
			i++
			if i == len(args) {
				return usageError{"source root requires a value"}
			}
			source := "project"
			if key == "--apgr-home" {
				source = "user"
			}
			captured, err := apgskills.CaptureCatalogSource(source, args[i])
			if err != nil {
				return err
			}
			input.Snapshots = append(input.Snapshots, captured.Snapshots...)
			input.Diagnostics = append(input.Diagnostics, captured.Diagnostics...)
			input.Sources = append(input.Sources, captured.Sources...)
		default:
			format = append(format, args[i])
		}
	}
	jsonOutput, err := parseSkillFormat(format, false)
	if err != nil {
		return err
	}
	c, err := apgskills.BuildCatalog(input)
	if err != nil {
		return err
	}
	c.Snapshots = nil
	if jsonOutput {
		return json.NewEncoder(out).Encode(c)
	}
	for _, d := range c.Skills {
		fmt.Fprintln(out, d.QualifiedID)
	}
	for _, d := range c.Diagnostics {
		fmt.Fprintf(out, "diagnostic %s: %s\n", d.Identity, d.Message)
	}
	for _, s := range c.Sources {
		fmt.Fprintf(out, "source %s: %s\n", s.Source, s.Status)
	}
	return nil
}
