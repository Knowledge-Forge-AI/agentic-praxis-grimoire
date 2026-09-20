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
	"strings"
)

// HomeView models the canonical operator home inspection structure (apgr-home-layout-v1).
type HomeView struct {
	LayoutVersion    string            `json:"layout_version"`
	Scope            string            `json:"scope"`
	PrecedenceSource string            `json:"precedence_source"`
	EffectiveHome    string            `json:"effective_home"`
	Paths            map[string]string `json:"paths"`
	Diagnostics      []string          `json:"diagnostics"`
}

// ParseHomeView parses and validates a JSON-encoded HomeView produced by canonical Python inspection.
func ParseHomeView(r io.Reader) (*HomeView, error) {
	var view HomeView
	decoder := json.NewDecoder(r)
	if err := decoder.Decode(&view); err != nil {
		return nil, fmt.Errorf("invalid home view JSON: %w", err)
	}
	if view.LayoutVersion != "apgr-home-layout-v1" {
		return nil, fmt.Errorf("unsupported layout_version: %q (expected %q)", view.LayoutVersion, "apgr-home-layout-v1")
	}
	if view.Scope != "resolved_config" && view.Scope != "paths_only" {
		return nil, fmt.Errorf("unsupported home view scope: %q", view.Scope)
	}
	if view.EffectiveHome == "" || !filepath.IsAbs(view.EffectiveHome) {
		return nil, fmt.Errorf("effective_home must be an absolute path, got %q", view.EffectiveHome)
	}
	requiredPaths := []string{
		"home", "config", "dispatcher", "claude_settings",
		"database", "state", "state_runs", "generations",
		"scratch", "skills",
	}
	if view.Scope == "resolved_config" {
		requiredPaths = append(requiredPaths, "outbox_root")
	}
	for _, rp := range requiredPaths {
		p, ok := view.Paths[rp]
		if !ok || p == "" {
			return nil, fmt.Errorf("missing required path %q in home view", rp)
		}
		if !filepath.IsAbs(p) {
			return nil, fmt.Errorf("path %q must be absolute, got %q", rp, p)
		}
	}
	return &view, nil
}

func renderHomeView(view *HomeView, jsonOutput bool, stdout io.Writer) error {
	if jsonOutput {
		encoded, mErr := json.MarshalIndent(view, "", "  ")
		if mErr != nil {
			return mErr
		}
		_, err := fmt.Fprintf(stdout, "%s\n", encoded)
		return err
	}

	fmt.Fprintf(stdout, "layout_version: %s\n", view.LayoutVersion)
	if view.Scope != "" {
		fmt.Fprintf(stdout, "scope: %s\n", view.Scope)
	}
	fmt.Fprintf(stdout, "precedence_source: %s\n", view.PrecedenceSource)
	fmt.Fprintf(stdout, "effective_home: %s\n", view.EffectiveHome)
	fmt.Fprintln(stdout, "paths:")
	var keys []string
	for k := range view.Paths {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	for _, k := range keys {
		fmt.Fprintf(stdout, "  %s: %s\n", k, view.Paths[k])
	}
	if len(view.Diagnostics) > 0 {
		fmt.Fprintln(stdout, "diagnostics:")
		for _, d := range view.Diagnostics {
			fmt.Fprintf(stdout, "  - %s\n", d)
		}
	}
	return nil
}

func runHome(ctx context.Context, configuration config, arguments []string, stdout io.Writer) error {
	if len(arguments) == 0 {
		return usageError{"home requires a command (try: home show --json)"}
	}
	if arguments[0] != "show" {
		return usageError{"unknown home command: " + arguments[0]}
	}

	jsonOutput := false
	var fromJSONPath string
	for i := 1; i < len(arguments); i++ {
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
			return usageError{"unknown option for home show: " + arg}
		}
	}

	if fromJSONPath != "" {
		var r io.Reader
		if fromJSONPath == "-" {
			r = os.Stdin
		} else {
			f, err := os.Open(fromJSONPath)
			if err != nil {
				return fmt.Errorf("cannot open home view JSON: %w", err)
			}
			defer f.Close()
			r = f
		}
		view, err := ParseHomeView(r)
		if err != nil {
			return err
		}
		return renderHomeView(view, jsonOutput, stdout)
	}

	precedenceSource := "default"
	var effectiveHome string

	if configuration.apgrHome != "" {
		precedenceSource = "cli"
		expanded, err := expandHomePath(configuration.apgrHome)
		if err != nil {
			return usageError{"--apgr-home is not a valid path: " + err.Error()}
		}
		if !filepath.IsAbs(expanded) {
			return usageError{"--apgr-home must be an absolute path"}
		}
		effectiveHome = filepath.Clean(expanded)
	} else if envHome := os.Getenv("APGR_HOME"); envHome != "" {
		precedenceSource = "environment"
		expanded, err := expandHomePath(envHome)
		if err != nil {
			return usageError{"APGR_HOME is not a valid path: " + err.Error()}
		}
		if !filepath.IsAbs(expanded) {
			return usageError{"APGR_HOME must be an absolute path"}
		}
		effectiveHome = filepath.Clean(expanded)
	} else {
		precedenceSource = "default"
		userHome, err := os.UserHomeDir()
		if err != nil {
			return fmt.Errorf("cannot determine user home directory: %w", err)
		}
		effectiveHome = filepath.Join(userHome, ".apgr")
	}

	diagnostics := make([]string, 0)

	var effectiveOutbox string
	if configuration.outbox != "" {
		expanded, err := expandHomePath(configuration.outbox)
		if err == nil && filepath.IsAbs(expanded) {
			effectiveOutbox = filepath.Clean(expanded)
		} else {
			effectiveOutbox = configuration.outbox
		}
	} else {
		diagnostics = append(diagnostics, "outbox_root unconfigured in paths_only scope: full resolution requires configuration evaluation (use apgr home show or --from-json)")
	}

	paths := map[string]string{
		"home":            effectiveHome,
		"config":          filepath.Join(effectiveHome, "config.toml"),
		"dispatcher":      filepath.Join(effectiveHome, "dispatcher"),
		"claude_settings": filepath.Join(effectiveHome, "claude", "settings.json"),
		"database":        filepath.Join(effectiveHome, "state", "dispatcher.sqlite3"),
		"state":           filepath.Join(effectiveHome, "state"),
		"state_runs":      filepath.Join(effectiveHome, "state", "runs"),
		"generations":     filepath.Join(effectiveHome, "generations"),
		"scratch":         filepath.Join(effectiveHome, "scratch"),
		"skills":          filepath.Join(effectiveHome, "skills"),
		"outbox_root":     effectiveOutbox,
	}

	fi, err := os.Lstat(effectiveHome)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			diagnostics = append(diagnostics, fmt.Sprintf("home directory does not exist: %s", effectiveHome))
		} else {
			diagnostics = append(diagnostics, fmt.Sprintf("cannot access home directory: %v", err))
		}
	} else if fi.Mode()&os.ModeSymlink != 0 {
		diagnostics = append(diagnostics, fmt.Sprintf("home directory must not be a symlink: %s", effectiveHome))
	} else if !fi.IsDir() {
		diagnostics = append(diagnostics, fmt.Sprintf("home path is not a directory: %s", effectiveHome))
	} else {
		// Check config file
		configPath := paths["config"]
		if cfi, cerr := os.Lstat(configPath); cerr == nil {
			if cfi.Mode()&os.ModeSymlink != 0 {
				diagnostics = append(diagnostics, fmt.Sprintf("config file must not be a symlink: %s", configPath))
			} else if !cfi.Mode().IsRegular() {
				diagnostics = append(diagnostics, fmt.Sprintf("config path is not a regular file: %s", configPath))
			}
		}

		// Check dispatcher roster bundle
		dispPath := paths["dispatcher"]
		if dfi, derr := os.Lstat(dispPath); derr == nil {
			if dfi.Mode()&os.ModeSymlink != 0 {
				diagnostics = append(diagnostics, fmt.Sprintf("dispatcher roster directory must not be a symlink: %s", dispPath))
			} else if !dfi.IsDir() {
				diagnostics = append(diagnostics, fmt.Sprintf("dispatcher roster path is not a directory: %s", dispPath))
			} else {
				requiredFiles := []string{"routes.toml", "endpoints.toml", "capabilities.toml", "policy.toml", "models.toml", "workers.toml", "bundle.json"}
				var missing []string
				for _, fname := range requiredFiles {
					fpath := filepath.Join(dispPath, fname)
					if fi, err := os.Lstat(fpath); err != nil || !fi.Mode().IsRegular() {
						missing = append(missing, fname)
					}
				}
				if len(missing) > 0 {
					sort.Strings(missing)
					diagnostics = append(diagnostics, fmt.Sprintf("partial operator dispatcher roster in %s: missing %s", dispPath, formatTomlList(missing)))
				}
			}
		}

		// Check state dir permissions
		statePath := paths["state"]
		if sfi, serr := os.Lstat(statePath); serr == nil {
			if sfi.Mode()&os.ModeSymlink != 0 {
				diagnostics = append(diagnostics, fmt.Sprintf("state directory must not be a symlink: %s", statePath))
			} else if sfi.IsDir() {
				perm := sfi.Mode().Perm()
				if perm != 0700 {
					diagnostics = append(diagnostics, fmt.Sprintf("state directory permissions are 0o%o, expected 0700: %s", perm, statePath))
				}
			}
		}

		// Check claude settings
		claudeSettings := paths["claude_settings"]
		if cfi, cerr := os.Lstat(claudeSettings); cerr == nil {
			if cfi.Mode()&os.ModeSymlink != 0 {
				diagnostics = append(diagnostics, fmt.Sprintf("claude settings must not be a symlink: %s", claudeSettings))
			} else if !cfi.IsDir() {
				raw, rerr := os.ReadFile(claudeSettings)
				if rerr == nil {
					var js any
					if jerr := json.Unmarshal(raw, &js); jerr != nil {
						diagnostics = append(diagnostics, fmt.Sprintf("claude settings is invalid JSON: %v", jerr))
					}
				}
			}
		}
	}

	view := HomeView{
		LayoutVersion:    "apgr-home-layout-v1",
		Scope:            "paths_only",
		PrecedenceSource: precedenceSource,
		EffectiveHome:    effectiveHome,
		Paths:            paths,
		Diagnostics:      diagnostics,
	}

	return renderHomeView(&view, jsonOutput, stdout)
}

func expandHomePath(path string) (string, error) {
	if path == "~" {
		home, err := os.UserHomeDir()
		if err != nil {
			return "", err
		}
		return home, nil
	}
	if strings.HasPrefix(path, "~/") {
		home, err := os.UserHomeDir()
		if err != nil {
			return "", err
		}
		return filepath.Join(home, strings.TrimPrefix(path, "~/")), nil
	}
	if strings.HasPrefix(path, "~") {
		return "", errors.New("unsupported user home syntax")
	}
	return path, nil
}

func formatTomlList(items []string) string {
	var quoted []string
	for _, item := range items {
		quoted = append(quoted, fmt.Sprintf("'%s'", item))
	}
	return "[" + strings.Join(quoted, ", ") + "]"
}
