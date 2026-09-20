package cli

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestHome_ShowJSONExplicit(t *testing.T) {
	tempHome := t.TempDir()
	outbox := t.TempDir()

	exit, stdout, stderr := runTest(t, context.Background(), "--apgr-home", tempHome, "--outbox-root", outbox, "home", "show", "--json")
	if exit != 0 {
		t.Fatalf("unexpected exit %d (stderr: %s)", exit, stderr)
	}

	var view HomeView
	if err := json.Unmarshal([]byte(stdout), &view); err != nil {
		t.Fatalf("cannot unmarshal json: %v", err)
	}

	if view.LayoutVersion != "apgr-home-layout-v1" {
		t.Errorf("unexpected layout_version: %s", view.LayoutVersion)
	}
	if view.Scope != "paths_only" {
		t.Errorf("unexpected scope: %s (want paths_only)", view.Scope)
	}
	if view.PrecedenceSource != "cli" {
		t.Errorf("unexpected precedence_source: %s", view.PrecedenceSource)
	}
	if view.EffectiveHome != tempHome {
		t.Errorf("effective_home mismatch: got %s, want %s", view.EffectiveHome, tempHome)
	}
	expectedKeys := []string{
		"home", "config", "dispatcher", "claude_settings",
		"database", "state", "state_runs", "generations",
		"scratch", "skills", "outbox_root",
	}
	for _, key := range expectedKeys {
		if _, ok := view.Paths[key]; !ok {
			t.Errorf("missing expected path key: %s", key)
		}
	}
	if view.Paths["database"] != filepath.Join(tempHome, "state", "dispatcher.sqlite3") {
		t.Errorf("unexpected database path: %s", view.Paths["database"])
	}
	if view.Paths["outbox_root"] != outbox {
		t.Errorf("unexpected outbox_root: %s", view.Paths["outbox_root"])
	}
}

func TestHome_ShowJSONEnvironment(t *testing.T) {
	tempHome := t.TempDir()
	t.Setenv("APGR_HOME", tempHome)

	exit, stdout, stderr := runTest(t, context.Background(), "home", "show", "--json")
	if exit != 0 {
		t.Fatalf("unexpected exit %d (stderr: %s)", exit, stderr)
	}

	var view HomeView
	if err := json.Unmarshal([]byte(stdout), &view); err != nil {
		t.Fatalf("cannot unmarshal json: %v", err)
	}

	if view.Scope != "paths_only" {
		t.Errorf("unexpected scope: %s (want paths_only)", view.Scope)
	}
	if view.PrecedenceSource != "environment" {
		t.Errorf("unexpected precedence_source: %s", view.PrecedenceSource)
	}
	if view.EffectiveHome != tempHome {
		t.Errorf("effective_home mismatch: got %s, want %s", view.EffectiveHome, tempHome)
	}
	if view.Paths["outbox_root"] != "" {
		t.Errorf("paths_only without explicit outbox should have empty outbox_root, got %s", view.Paths["outbox_root"])
	}
	hasOutboxDiag := false
	for _, d := range view.Diagnostics {
		if strings.Contains(d, "outbox_root unconfigured in paths_only scope") {
			hasOutboxDiag = true
			break
		}
	}
	if !hasOutboxDiag {
		t.Errorf("expected outbox diagnostic in paths_only scope, got %v", view.Diagnostics)
	}
}

func TestHome_ShowTerminal(t *testing.T) {
	tempHome := t.TempDir()

	exit, stdout, stderr := runTest(t, context.Background(), "--apgr-home", tempHome, "home", "show")
	if exit != 0 {
		t.Fatalf("unexpected exit %d (stderr: %s)", exit, stderr)
	}

	if !strings.Contains(stdout, "layout_version: apgr-home-layout-v1") {
		t.Errorf("missing layout_version in stdout: %s", stdout)
	}
	if !strings.Contains(stdout, "scope: paths_only") {
		t.Errorf("missing scope in stdout: %s", stdout)
	}
	if !strings.Contains(stdout, "precedence_source: cli") {
		t.Errorf("missing precedence_source in stdout: %s", stdout)
	}
}

func TestHome_RejectsRelativePath(t *testing.T) {
	exit, _, stderr := runTest(t, context.Background(), "--apgr-home", "relative/path", "home", "show", "--json")
	if exit != 2 {
		t.Errorf("expected exit 2, got %d (stderr: %s)", exit, stderr)
	}
	if !strings.Contains(stderr, "must be an absolute path") {
		t.Errorf("unexpected error message: %s", stderr)
	}
}

func TestHome_DiagnosticsNonExistent(t *testing.T) {
	tempHome := filepath.Join(t.TempDir(), "nonexistent")

	exit, stdout, stderr := runTest(t, context.Background(), "--apgr-home", tempHome, "home", "show", "--json")
	if exit != 0 {
		t.Fatalf("unexpected exit %d (stderr: %s)", exit, stderr)
	}

	var view HomeView
	if err := json.Unmarshal([]byte(stdout), &view); err != nil {
		t.Fatalf("cannot unmarshal json: %v", err)
	}
	if len(view.Diagnostics) == 0 {
		t.Errorf("expected diagnostic for nonexistent home")
	}
	if _, err := os.Stat(tempHome); !os.IsNotExist(err) {
		t.Errorf("inspect_home must not create nonexistent home directory")
	}
}

func TestHome_ParseHomeView_Valid(t *testing.T) {
	validJSON := `{
  "layout_version": "apgr-home-layout-v1",
  "scope": "resolved_config",
  "precedence_source": "environment",
  "effective_home": "/tmp/test_home",
  "paths": {
    "home": "/tmp/test_home",
    "config": "/tmp/test_home/config.toml",
    "dispatcher": "/tmp/test_home/dispatcher",
    "claude_settings": "/tmp/test_home/claude/settings.json",
    "database": "/tmp/test_home/state/dispatcher.sqlite3",
    "state": "/tmp/test_home/state",
    "state_runs": "/tmp/test_home/state/runs",
    "generations": "/tmp/test_home/generations",
    "scratch": "/tmp/test_home/scratch",
    "skills": "/tmp/test_home/skills",
    "outbox_root": "/tmp/test_outbox"
  },
  "diagnostics": []
}`
	view, err := ParseHomeView(strings.NewReader(validJSON))
	if err != nil {
		t.Fatalf("unexpected error parsing valid home view: %v", err)
	}
	if view.LayoutVersion != "apgr-home-layout-v1" {
		t.Errorf("unexpected layout_version: %s", view.LayoutVersion)
	}
	if view.Scope != "resolved_config" {
		t.Errorf("unexpected scope: %s", view.Scope)
	}
	if view.Paths["outbox_root"] != "/tmp/test_outbox" {
		t.Errorf("unexpected outbox_root: %s", view.Paths["outbox_root"])
	}
}

func TestHome_ParseHomeView_Invalid(t *testing.T) {
	cases := []struct {
		name string
		json string
	}{
		{"invalid json", "not a json"},
		{"wrong version", `{"layout_version":"wrong-v1","scope":"resolved_config","effective_home":"/tmp","paths":{}}`},
		{"wrong scope", `{"layout_version":"apgr-home-layout-v1","scope":"unknown_scope","effective_home":"/tmp","paths":{}}`},
		{"relative home", `{"layout_version":"apgr-home-layout-v1","scope":"resolved_config","effective_home":"relative","paths":{}}`},
		{"missing outbox in resolved_config", `{
			"layout_version": "apgr-home-layout-v1",
			"scope": "resolved_config",
			"effective_home": "/tmp/home",
			"paths": {
				"home": "/tmp/home", "config": "/tmp/home/config.toml", "dispatcher": "/tmp/home/disp",
				"claude_settings": "/tmp/home/s.json", "database": "/tmp/home/d.db", "state": "/tmp/home/st",
				"state_runs": "/tmp/home/r", "generations": "/tmp/home/g", "scratch": "/tmp/home/sc",
				"skills": "/tmp/home/sk"
			}
		}`},
		{"relative path in paths", `{
			"layout_version": "apgr-home-layout-v1",
			"scope": "resolved_config",
			"effective_home": "/tmp/home",
			"paths": {
				"home": "relative", "config": "/tmp/home/config.toml", "dispatcher": "/tmp/home/disp",
				"claude_settings": "/tmp/home/s.json", "database": "/tmp/home/d.db", "state": "/tmp/home/st",
				"state_runs": "/tmp/home/r", "generations": "/tmp/home/g", "scratch": "/tmp/home/sc",
				"skills": "/tmp/home/sk", "outbox_root": "/tmp/outbox"
			}
		}`},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			_, err := ParseHomeView(strings.NewReader(tc.json))
			if err == nil {
				t.Errorf("expected error for case %s, got nil", tc.name)
			}
		})
	}
}

func TestHome_ShowFromJSON(t *testing.T) {
	tempDir := t.TempDir()
	jsonPath := filepath.Join(tempDir, "resolved_home.json")
	validJSON := `{
  "layout_version": "apgr-home-layout-v1",
  "scope": "resolved_config",
  "precedence_source": "environment",
  "effective_home": "/tmp/test_home",
  "paths": {
    "home": "/tmp/test_home",
    "config": "/tmp/test_home/config.toml",
    "dispatcher": "/tmp/test_home/dispatcher",
    "claude_settings": "/tmp/test_home/claude/settings.json",
    "database": "/tmp/test_home/state/dispatcher.sqlite3",
    "state": "/tmp/test_home/state",
    "state_runs": "/tmp/test_home/state/runs",
    "generations": "/tmp/test_home/generations",
    "scratch": "/tmp/test_home/scratch",
    "skills": "/tmp/test_home/skills",
    "outbox_root": "/tmp/test_outbox"
  },
  "diagnostics": []
}`
	if err := os.WriteFile(jsonPath, []byte(validJSON), 0o600); err != nil {
		t.Fatalf("failed to write test json: %v", err)
	}

	// Test --from-json with --json
	exit, stdout, stderr := runTest(t, context.Background(), "home", "show", "--from-json", jsonPath, "--json")
	if exit != 0 {
		t.Fatalf("unexpected exit %d (stderr: %s)", exit, stderr)
	}
	var view HomeView
	if err := json.Unmarshal([]byte(stdout), &view); err != nil {
		t.Fatalf("cannot unmarshal json: %v", err)
	}
	if view.Scope != "resolved_config" {
		t.Errorf("expected scope resolved_config, got %s", view.Scope)
	}
	if view.Paths["outbox_root"] != "/tmp/test_outbox" {
		t.Errorf("unexpected outbox_root: %s", view.Paths["outbox_root"])
	}

	// Test --from-json text rendering
	exit, stdout, stderr = runTest(t, context.Background(), "home", "show", "--from-json", jsonPath)
	if exit != 0 {
		t.Fatalf("unexpected exit %d (stderr: %s)", exit, stderr)
	}
	if !strings.Contains(stdout, "scope: resolved_config") {
		t.Errorf("missing scope in text rendering: %s", stdout)
	}
	if !strings.Contains(stdout, "outbox_root: /tmp/test_outbox") {
		t.Errorf("missing outbox_root in text rendering: %s", stdout)
	}
}
