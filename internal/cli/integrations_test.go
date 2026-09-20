package cli

import (
	"bytes"
	"context"
	"os"
	"strings"
	"testing"
)

const sampleValidDoctorJSON = `{
  "doctor_version": "apgr-rtk-doctor-v1",
  "status": "available",
  "effective_home": "/tmp/test_home",
  "target_project": "/tmp/test_project",
  "configuration_sources": [
    {
      "source_type": "project_config",
      "path": "/tmp/test_project/.apgr/config.toml",
      "exists": true,
      "digest": "abc123digest"
    }
  ],
  "enabled": true,
  "required": false,
  "configured_executable": "/run/current-system/sw/bin/rtk",
  "resolved_executable": "/nix/store/test-rtk/bin/rtk",
  "executable_identity": {
    "path": "/nix/store/test-rtk/bin/rtk",
    "is_regular_file": true,
    "is_executable": true
  },
  "expected_version": ">= 0.43.0",
  "observed_version": "0.43.0",
  "providers": {
    "claude": {
      "declared_mode": "hook",
      "effective_mode": "hook",
      "reason": "hook_registered"
    },
    "codex": {
      "declared_mode": "instructions",
      "effective_mode": "instructions",
      "reason": "declared_mode"
    },
    "antigravity": {
      "declared_mode": "instructions",
      "effective_mode": "instructions",
      "reason": "declared_mode"
    }
  },
  "hook_registration": {
    "claude": {
      "registered": true,
      "source_file": "/tmp/test_home/claude/settings.json",
      "command": "rtk hook claude"
    }
  },
  "canonical_skill": {
    "name": "rtk-command-proxy",
    "discoverable": true,
    "path": "/tmp/test_project/skills/rtk-command-proxy/SKILL.md"
  },
  "probes": {
    "version": {
      "executed": true,
      "ok": true
    },
    "hook_check": {
      "executed": true,
      "ok": true
    }
  },
  "diagnostics": []
}`

func TestParseRTKDoctorView_Valid(t *testing.T) {
	r := strings.NewReader(sampleValidDoctorJSON)
	view, err := ParseRTKDoctorView(r)
	if err != nil {
		t.Fatalf("ParseRTKDoctorView failed: %v", err)
	}
	if view.DoctorVersion != "apgr-rtk-doctor-v1" {
		t.Errorf("got doctor_version %q, want apgr-rtk-doctor-v1", view.DoctorVersion)
	}
	if view.Status != "available" {
		t.Errorf("got status %q, want available", view.Status)
	}
	if !view.Enabled {
		t.Errorf("got enabled=false, want true")
	}
	if view.Required {
		t.Errorf("got required=true, want false")
	}
	if view.ObservedVersion == nil || *view.ObservedVersion != "0.43.0" {
		t.Errorf("got observed_version %v, want 0.43.0", view.ObservedVersion)
	}
	if len(view.Providers) != 3 {
		t.Errorf("got %d providers, want 3", len(view.Providers))
	}
}

func TestParseRTKDoctorView_InvalidVersion(t *testing.T) {
	bad := strings.Replace(sampleValidDoctorJSON, "apgr-rtk-doctor-v1", "unsupported-v0", 1)
	_, err := ParseRTKDoctorView(strings.NewReader(bad))
	if err == nil || !strings.Contains(err.Error(), "unsupported doctor_version") {
		t.Fatalf("expected unsupported doctor_version error, got: %v", err)
	}
}

func TestParseRTKDoctorView_InvalidStatus(t *testing.T) {
	bad := strings.Replace(sampleValidDoctorJSON, `"status": "available"`, `"status": "bogus"`, 1)
	_, err := ParseRTKDoctorView(strings.NewReader(bad))
	if err == nil || !strings.Contains(err.Error(), "unsupported rtk doctor status") {
		t.Fatalf("expected unsupported status error, got: %v", err)
	}
}

func TestParseRTKDoctorView_RelativeHome(t *testing.T) {
	bad := strings.Replace(sampleValidDoctorJSON, `"/tmp/test_home"`, `"relative/path"`, 1)
	_, err := ParseRTKDoctorView(strings.NewReader(bad))
	if err == nil || !strings.Contains(err.Error(), "effective_home must be an absolute path") {
		t.Fatalf("expected absolute path error, got: %v", err)
	}
}

func TestRenderRTKDoctorView_Text(t *testing.T) {
	r := strings.NewReader(sampleValidDoctorJSON)
	view, err := ParseRTKDoctorView(r)
	if err != nil {
		t.Fatalf("ParseRTKDoctorView failed: %v", err)
	}
	var buf bytes.Buffer
	if err := renderRTKDoctorView(view, false, &buf); err != nil {
		t.Fatalf("renderRTKDoctorView failed: %v", err)
	}
	out := buf.String()
	if !strings.Contains(out, "apgr rtk doctor (view from supplied JSON):") {
		t.Errorf("missing header in text output: %s", out)
	}
	if !strings.Contains(out, "status: available") {
		t.Errorf("missing status in text output: %s", out)
	}
	if !strings.Contains(out, "observed_version: 0.43.0") {
		t.Errorf("missing observed_version in text output: %s", out)
	}
	if !strings.Contains(out, "claude: hook (effective: hook, reason: hook_registered)") {
		t.Errorf("missing claude provider line in text output: %s", out)
	}
}

func TestRenderRTKDoctorView_JSON(t *testing.T) {
	r := strings.NewReader(sampleValidDoctorJSON)
	view, err := ParseRTKDoctorView(r)
	if err != nil {
		t.Fatalf("ParseRTKDoctorView failed: %v", err)
	}
	var buf bytes.Buffer
	if err := renderRTKDoctorView(view, true, &buf); err != nil {
		t.Fatalf("renderRTKDoctorView failed: %v", err)
	}
	out := buf.String()
	if !strings.Contains(out, `"doctor_version": "apgr-rtk-doctor-v1"`) {
		t.Errorf("missing doctor_version in json output: %s", out)
	}
}

func TestRunIntegrations_UsageErrors(t *testing.T) {
	ctx := context.Background()
	cfg := config{}
	var out bytes.Buffer

	// No arguments
	err := runIntegrations(ctx, cfg, nil, &out)
	if err == nil || !strings.Contains(err.Error(), "integrations requires a command") {
		t.Errorf("expected integrations usage error, got: %v", err)
	}

	// Unknown integration
	err = runIntegrations(ctx, cfg, []string{"other"}, &out)
	if err == nil || !strings.Contains(err.Error(), "unknown integration: other") {
		t.Errorf("expected unknown integration error, got: %v", err)
	}

	// Missing rtk command
	err = runIntegrations(ctx, cfg, []string{"rtk"}, &out)
	if err == nil || !strings.Contains(err.Error(), "rtk requires a command") {
		t.Errorf("expected rtk requires a command error, got: %v", err)
	}

	// Unknown rtk command
	err = runIntegrations(ctx, cfg, []string{"rtk", "unknown"}, &out)
	if err == nil || !strings.Contains(err.Error(), "unknown rtk command: unknown") {
		t.Errorf("expected unknown rtk command error, got: %v", err)
	}

	// Unknown option
	err = runIntegrations(ctx, cfg, []string{"rtk", "doctor", "--bad-opt"}, &out)
	if err == nil || !strings.Contains(err.Error(), "unknown option for integrations rtk doctor") {
		t.Errorf("expected unknown option error, got: %v", err)
	}

	// Missing --from-json
	err = runIntegrations(ctx, cfg, []string{"rtk", "doctor"}, &out)
	if err == nil || !strings.Contains(err.Error(), "requires --from-json") {
		t.Errorf("expected requires --from-json error, got: %v", err)
	}
}

func TestRunIntegrations_FromJSON(t *testing.T) {
	ctx := context.Background()
	cfg := config{}
	var out bytes.Buffer

	// Test passing valid json via stdin with --from-json=-
	// We can't mock stdin directly in unit test easily, but we can test via temporary file:
	tmpFile := t.TempDir() + "/doctor.json"
	if err := os.WriteFile(tmpFile, []byte(sampleValidDoctorJSON), 0o600); err != nil {
		t.Fatal(err)
	}

	err := runIntegrations(ctx, cfg, []string{"rtk", "doctor", "--from-json=" + tmpFile}, &out)
	if err != nil {
		t.Fatalf("runIntegrations with --from-json failed: %v", err)
	}
	if !strings.Contains(out.String(), "status: available") {
		t.Errorf("expected output to contain 'status: available', got: %s", out.String())
	}
}
