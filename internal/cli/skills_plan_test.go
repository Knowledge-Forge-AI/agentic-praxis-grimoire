package cli

import (
	"bytes"
	"context"
	"encoding/json"
	"strings"
	"testing"
)

func TestSkillPlanCLI(t *testing.T) {
	input := `{"schema_version":"apg.context-plan/v1","run_id":"r","binding_id":"b","attempt_id":"a","roles":["work"],"consumer":"go_library","requested_mode":"adaptive","catalog":{"schema_version":"apg.skill-catalog/v1"},"facts":[{"kind":"language","value":"go"}],"mandatory":[{"id":"task","text":"task é"}],"qualification":{}}`
	var out bytes.Buffer
	if err := runSkills(context.Background(), []string{"plan", "--stdin"}, strings.NewReader(input), &out); err != nil {
		t.Fatal(err)
	}
	var p map[string]any
	if err := json.Unmarshal(out.Bytes(), &p); err != nil {
		t.Fatal(err)
	}
	if p["effective_mode"] != "static" || p["tokens"] != nil {
		t.Fatal("qualification hidden")
	}
	for _, bad := range []string{strings.Replace(input, `"roles":`, `"unknown":0,"roles":`, 1), strings.Replace(input, `"run_id":"r"`, `"run_id":"r","run_id":"s"`, 1)} {
		if err := runSkills(context.Background(), []string{"plan", "--stdin"}, strings.NewReader(bad), &out); err == nil {
			t.Fatal("invalid request accepted")
		}
	}
}
