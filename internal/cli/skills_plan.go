package cli

import (
	"encoding/json"
	apgskills "github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/skills"
	"io"
)

func runSkillPlan(args []string, in io.Reader, out io.Writer) error {
	if len(args) < 1 || args[0] != "--stdin" {
		return usageError{"plan requires --stdin"}
	}
	data, err := io.ReadAll(io.LimitReader(in, (96<<20)+1))
	if err != nil {
		return err
	}
	if len(data) > 96<<20 {
		return usageError{"plan input too large"}
	}
	r, err := apgskills.DecodeContextPlanRequest(data)
	if err != nil {
		return err
	}
	// Optional explicit roots are captured once, before the pure boundary.
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
			return usageError{"unknown plan source option"}
		}
		c, e := apgskills.CaptureCatalogSource(source, args[i+1])
		if e != nil {
			return e
		}
		r.Catalog.Snapshots = append(r.Catalog.Snapshots, c.Snapshots...)
		r.Catalog.Diagnostics = append(r.Catalog.Diagnostics, c.Diagnostics...)
		r.Catalog.Sources = append(r.Catalog.Sources, c.Sources...)
	}
	p, err := apgskills.PlanContext(r)
	if err != nil {
		return err
	}
	return json.NewEncoder(out).Encode(p)
}
