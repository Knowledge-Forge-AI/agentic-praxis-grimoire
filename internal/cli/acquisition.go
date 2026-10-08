package cli

import (
	"encoding/json"
	"io"
	"os"
	"path/filepath"
	"strings"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/internal/acquisition"
	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/skills"
)

// The config-file route is a captured per-invocation authority, never operator
// configuration. Direct CLI flags capture only explicitly selected roots.
func acquisitionEngine(args []string) (*acquisition.Engine, error) {
	c := acquisition.Config{Catalog: skills.CatalogInput{SchemaVersion: skills.CatalogSchemaV1}, Consumer: skills.ConsumerGo}
	seen := map[string]bool{}
	for i := 0; i < len(args); i += 2 {
		if i+1 == len(args) || seen[args[i]] {
			return nil, usageError{"acquisition option missing or repeated"}
		}
		seen[args[i]] = true
		key, value := args[i], args[i+1]
		switch key {
		case "--config":
			if len(args) != 2 || !filepath.IsAbs(value) {
				return nil, usageError{"--config requires sole absolute run authority file"}
			}
			root, err := os.OpenRoot(filepath.Dir(value))
			if err != nil {
				return nil, err
			}
			raw, err := acquisition.ReadFile(root, filepath.Base(value), 64<<20)
			root.Close()
			if err != nil {
				return nil, err
			}
			if err = acquisition.StrictJSON(raw, &c); err != nil {
				return nil, err
			}
		case "--run-dir":
			c.RunDir = value
		case "--run-id":
			c.RunID = value
		case "--binding-id":
			c.BindingID = value
		case "--attempt-id":
			c.AttemptID = value
		case "--consumer":
			c.Consumer = skills.ConsumerKind(value)
		case "--project-root", "--apgr-home":
			source := "project"
			if key == "--apgr-home" {
				source = "user"
			}
			captured, err := skills.CaptureCatalogSource(source, value)
			if err != nil {
				return nil, err
			}
			c.Catalog.Snapshots = append(c.Catalog.Snapshots, captured.Snapshots...)
			c.Catalog.Sources = append(c.Catalog.Sources, captured.Sources...)
			c.Catalog.Diagnostics = append(c.Catalog.Diagnostics, captured.Diagnostics...)
		default:
			return nil, usageError{"unknown acquisition option"}
		}
	}
	for _, source := range []struct{ name, root string }{{"project", c.ProjectRoot}, {"user", c.APGRHome}} {
		if source.root == "" {
			continue
		}
		captured, err := skills.CaptureCatalogSource(source.name, source.root)
		if err != nil {
			return nil, err
		}
		c.Catalog.Snapshots = append(c.Catalog.Snapshots, captured.Snapshots...)
		c.Catalog.Sources = append(c.Catalog.Sources, captured.Sources...)
		c.Catalog.Diagnostics = append(c.Catalog.Diagnostics, captured.Diagnostics...)
	}
	return acquisition.Open(c)
}
func runAcquisition(action string, args []string, out io.Writer) error {
	if len(args) == 0 || strings.HasPrefix(args[0], "--") {
		return usageError{"search/acquire requires query or qualified identity"}
	}
	target := args[0]
	channel := "cli"
	if action == "acquire" && len(args) > 1 && args[1] == "--prepare-only" {
		channel = "preparation"
		args = append([]string{target}, args[2:]...)
	}
	e, err := acquisitionEngine(args[1:])
	if err != nil {
		return err
	}
	defer e.Close()
	if action == "search" {
		rows, err := e.Search(target, "cli")
		if err != nil {
			return err
		}
		raw, err := json.Marshal(rows)
		if err != nil {
			return err
		}
		raw = append(raw, '\n')
		n, err := out.Write(raw)
		if err != nil {
			return err
		}
		if n != len(raw) {
			return io.ErrShortWrite
		}
		return e.ResponseDelivered("cli", "skill_search", n, raw)
	}
	result, err := e.Acquire(target, channel)
	if err != nil {
		return err
	}
	// JSON is the stable command-channel envelope. Body/support []byte values
	// use Go's base64 encoding, preserving all exact bytes without ambiguity.
	raw, err := json.Marshal(result)
	if err != nil {
		return err
	}
	raw = append(raw, '\n')
	n, err := out.Write(raw)
	if err != nil {
		return err
	}
	if n != len(raw) {
		return io.ErrShortWrite
	}
	if channel == "preparation" {
		return nil
	}
	return e.Delivered(result.EventID, channel, n, raw)
}
func runMCP(args []string, in io.Reader, out, diagnostics io.Writer) error {
	if len(args) == 0 || args[0] != "serve" {
		return usageError{"mcp requires serve"}
	}
	e, err := acquisitionEngine(args[1:])
	if err != nil {
		return err
	}
	defer e.Close()
	return e.Serve(in, out, diagnostics)
}
