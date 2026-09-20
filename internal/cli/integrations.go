package cli

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

// RTKConfigurationSource records one inspected configuration source file.
type RTKConfigurationSource struct {
	SourceType string  `json:"source_type"`
	Path       string  `json:"path"`
	Exists     bool    `json:"exists"`
	Digest     *string `json:"digest"`
}

// RTKProviderInfo records declared and effective modes for one provider.
type RTKProviderInfo struct {
	DeclaredMode  string `json:"declared_mode"`
	EffectiveMode string `json:"effective_mode"`
	Reason        string `json:"reason"`
}

// RTKDoctorView models the canonical RTK doctor output structure (apgr-rtk-doctor-v1).
type RTKDoctorView struct {
	DoctorVersion        string                     `json:"doctor_version"`
	Status               string                     `json:"status"`
	EffectiveHome        string                     `json:"effective_home"`
	TargetProject        *string                    `json:"target_project"`
	ConfigurationSources []RTKConfigurationSource   `json:"configuration_sources"`
	Enabled              bool                       `json:"enabled"`
	Required             bool                       `json:"required"`
	ConfiguredExecutable *string                    `json:"configured_executable"`
	ResolvedExecutable   *string                    `json:"resolved_executable"`
	ExecutableIdentity   map[string]interface{}     `json:"executable_identity"`
	ExpectedVersion      string                     `json:"expected_version"`
	ObservedVersion      *string                    `json:"observed_version"`
	Providers            map[string]RTKProviderInfo `json:"providers"`
	HookRegistration     map[string]interface{}     `json:"hook_registration"`
	CanonicalSkill       map[string]interface{}     `json:"canonical_skill"`
	Probes               map[string]interface{}     `json:"probes"`
	Diagnostics          []string                   `json:"diagnostics"`
}

// ParseRTKDoctorView parses and validates a JSON-encoded RTKDoctorView.
func ParseRTKDoctorView(r io.Reader) (*RTKDoctorView, error) {
	var view RTKDoctorView
	decoder := json.NewDecoder(r)
	if err := decoder.Decode(&view); err != nil {
		return nil, fmt.Errorf("invalid rtk doctor JSON: %w", err)
	}
	if view.DoctorVersion != "apgr-rtk-doctor-v1" {
		return nil, fmt.Errorf("unsupported doctor_version: %q (expected %q)", view.DoctorVersion, "apgr-rtk-doctor-v1")
	}
	if view.Status != "available" && view.Status != "unavailable" && view.Status != "disabled" {
		return nil, fmt.Errorf("unsupported rtk doctor status: %q", view.Status)
	}
	if view.EffectiveHome == "" || !filepath.IsAbs(view.EffectiveHome) {
		return nil, fmt.Errorf("effective_home must be an absolute path, got %q", view.EffectiveHome)
	}
	return &view, nil
}

func renderRTKDoctorView(view *RTKDoctorView, jsonOutput bool, stdout io.Writer) error {
	if jsonOutput {
		encoded, mErr := json.MarshalIndent(view, "", "  ")
		if mErr != nil {
			return mErr
		}
		_, err := fmt.Fprintf(stdout, "%s\n", encoded)
		return err
	}

	fmt.Fprintln(stdout, "apgr rtk doctor (view from supplied JSON):")
	fmt.Fprintf(stdout, "  status: %s\n", view.Status)
	fmt.Fprintf(stdout, "  effective_home: %s\n", view.EffectiveHome)
	proj := "none"
	if view.TargetProject != nil && *view.TargetProject != "" {
		proj = *view.TargetProject
	}
	fmt.Fprintf(stdout, "  target_project: %s\n", proj)
	fmt.Fprintf(stdout, "  enabled: %t\n", view.Enabled)
	fmt.Fprintf(stdout, "  required: %t\n", view.Required)
	cfgExec := "none"
	if view.ConfiguredExecutable != nil && *view.ConfiguredExecutable != "" {
		cfgExec = *view.ConfiguredExecutable
	}
	fmt.Fprintf(stdout, "  configured_executable: %s\n", cfgExec)
	resExec := "none"
	if view.ResolvedExecutable != nil && *view.ResolvedExecutable != "" {
		resExec = *view.ResolvedExecutable
	}
	fmt.Fprintf(stdout, "  resolved_executable: %s\n", resExec)

	if view.ObservedVersion != nil && *view.ObservedVersion != "" {
		fmt.Fprintf(stdout, "  observed_version: %s (expected: %s)\n", *view.ObservedVersion, view.ExpectedVersion)
	} else {
		fmt.Fprintf(stdout, "  expected_version: %s\n", view.ExpectedVersion)
	}

	fmt.Fprintln(stdout, "  providers:")
	provKeys := make([]string, 0, len(view.Providers))
	for k := range view.Providers {
		provKeys = append(provKeys, k)
	}
	sort.Strings(provKeys)
	for _, k := range provKeys {
		pinfo := view.Providers[k]
		fmt.Fprintf(stdout, "    %s: %s (effective: %s, reason: %s)\n",
			k, pinfo.DeclaredMode, pinfo.EffectiveMode, pinfo.Reason)
	}

	fmt.Fprintln(stdout, "  hook_registration:")
	if claudeHook, ok := view.HookRegistration["claude"].(map[string]interface{}); ok {
		if reg, ok := claudeHook["registered"].(bool); ok && reg {
			sourceFile, _ := claudeHook["source_file"].(string)
			fmt.Fprintf(stdout, "    claude: registered (%s)\n", sourceFile)
		} else {
			fmt.Fprintln(stdout, "    claude: not registered")
		}
	} else {
		fmt.Fprintln(stdout, "    claude: not registered")
	}

	if skill, ok := view.CanonicalSkill["name"].(string); ok {
		skillStatus := "unavailable"
		if disc, ok := view.CanonicalSkill["discoverable"].(bool); ok && disc {
			skillStatus = "discoverable"
		}
		fmt.Fprintf(stdout, "  canonical_skill:\n    %s: %s\n", skill, skillStatus)
	}

	if len(view.Diagnostics) > 0 {
		fmt.Fprintln(stdout, "  diagnostics:")
		for _, d := range view.Diagnostics {
			fmt.Fprintf(stdout, "    - %s\n", d)
		}
	}

	return nil
}

func runIntegrations(ctx context.Context, configuration config, arguments []string, stdout io.Writer) error {
	if len(arguments) == 0 {
		return usageError{"integrations requires a command (try: integrations rtk doctor)"}
	}
	if arguments[0] != "rtk" {
		return usageError{"unknown integration: " + arguments[0]}
	}
	if len(arguments) < 2 {
		return usageError{"rtk requires a command (try: integrations rtk doctor)"}
	}
	if arguments[1] != "doctor" {
		return usageError{"unknown rtk command: " + arguments[1]}
	}

	jsonOutput := false
	var fromJSONPath string
	for i := 2; i < len(arguments); i++ {
		arg := arguments[i]
		if arg == "--json" {
			jsonOutput = true
		} else if arg == "--from-json" {
			if i+1 >= len(arguments) {
				return usageError{"--from-json requires a file path argument"}
			}
			i++
			fromJSONPath = arguments[i]
		} else if strings.HasPrefix(arg, "--from-json=") {
			fromJSONPath = strings.TrimPrefix(arg, "--from-json=")
		} else {
			return usageError{"unknown option for integrations rtk doctor: " + arg}
		}
	}

	if fromJSONPath == "" {
		return usageError{"integrations rtk doctor requires --from-json <file> in Go CLI (use 'python3 -m agentic_praxis_grimoire.cli integrations rtk doctor' for live evaluation)"}
	}

	var r io.Reader
	if fromJSONPath == "-" {
		r = os.Stdin
	} else {
		f, err := os.Open(fromJSONPath)
		if err != nil {
			return fmt.Errorf("cannot open rtk doctor JSON: %w", err)
		}
		defer f.Close()
		r = f
	}
	view, err := ParseRTKDoctorView(r)
	if err != nil {
		return err
	}
	return renderRTKDoctorView(view, jsonOutput, stdout)
}
