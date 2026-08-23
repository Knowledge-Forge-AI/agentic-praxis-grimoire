package cli

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"
	"syscall"
	"time"
	"unicode/utf8"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/envsnap"
	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/internal/buildinfo"
)

const (
	maxEnvironmentProfileBytes = 1 << 20
	envUsage                   = `Usage: apgr env <profile-check|snapshot|show|resolve|run> [options]

Commands:
  profile-check --profile FILE       validate one canonical profile
  snapshot --profile FILE --storage-root PATH --context LABEL
                                      capture the process environment explicitly
  show --profile FILE --storage-root PATH
                                      show metadata and entry names
  resolve --profile FILE --storage-root PATH
                                      resolve isolated or overlay environment
  run --profile FILE --storage-root PATH -- COMMAND [ARGS...]
                                      run one exact argv without a shell

Options:
  --profile FILE       absolute, clean, owner-only 0600 profile JSON
  --storage-root PATH  absolute, clean APGR storage root
  --context LABEL      required, non-empty capture provenance label (snapshot)
  --mode MODE          isolated (default) or overlay
  --override NAME=VAL  validated explicit override (repeatable)
  --max-age DURATION   reject a snapshot older than this duration
  --with-values        deliberately include values in show/resolve output
  --json               emit machine-readable output
  -h, --help           show this help
`
)

type envOptions struct {
	action      string
	profilePath string
	storageRoot string
	context     string
	hasContext  bool
	mode        string
	maxAge      time.Duration
	hasMaxAge   bool
	withValues  bool
	json        bool
	overrides   []string
	command     []string
}

type childExitError struct{ code int }

func (err childExitError) Error() string { return "environment command exited unsuccessfully" }

type envProfileView struct {
	SchemaVersion string `json:"schema_version"`
	ProfileID     string `json:"profile_id"`
	EntryCount    int    `json:"entry_count"`
}

type envEntryView struct {
	Name      string `json:"name"`
	Validator string `json:"validator"`
	Source    string `json:"source"`
	Value     string `json:"value,omitempty"`
}

type envSnapshotView struct {
	SchemaVersion      string         `json:"schema_version"`
	ProfileID          string         `json:"profile_id"`
	ProfileFingerprint string         `json:"profile_fingerprint"`
	ProducerVersion    string         `json:"producer_version"`
	Provenance         any            `json:"provenance"`
	CapturedAt         time.Time      `json:"captured_at"`
	AgeSeconds         int64          `json:"age_seconds"`
	Stale              bool           `json:"stale"`
	Entries            []envEntryView `json:"entries"`
	MissingOptional    []string       `json:"missing_optional,omitempty"`
	ContentFingerprint string         `json:"content_fingerprint"`
	Disposition        string         `json:"disposition,omitempty"`
}

type envResolvedView struct {
	Mode        string              `json:"mode"`
	Names       []string            `json:"names"`
	Provenance  []envProvenanceView `json:"provenance"`
	Environment map[string]string   `json:"environment,omitempty"`
}

type envProvenanceView struct {
	Name   string `json:"name"`
	Source string `json:"source"`
}

func runEnv(ctx context.Context, arguments []string, stdin io.Reader, stdout, stderr io.Writer) error {
	if len(arguments) == 0 {
		return usageError{"env requires profile-check, snapshot, show, resolve, or run"}
	}
	if arguments[0] == "-h" || arguments[0] == "--help" {
		if len(arguments) != 1 {
			return usageError{"env help takes no arguments"}
		}
		_, err := io.WriteString(stdout, envUsage)
		return err
	}
	if len(arguments) == 2 && (arguments[1] == "-h" || arguments[1] == "--help") {
		_, err := io.WriteString(stdout, envUsage)
		return err
	}
	options, err := parseEnvOptions(arguments)
	if err != nil {
		return err
	}
	switch options.action {
	case "profile-check":
		return runEnvProfileCheck(options, stdout)
	case "snapshot":
		return runEnvSnapshot(ctx, options, stdout)
	case "show":
		return runEnvShow(ctx, options, stdout)
	case "resolve":
		return runEnvResolve(ctx, options, stdout)
	case "run":
		return runEnvRun(ctx, options, stdin, stdout, stderr)
	default:
		return usageError{"unknown env command"}
	}
}

func parseEnvOptions(arguments []string) (envOptions, error) {
	if len(arguments) == 0 {
		return envOptions{}, usageError{"env requires a command"}
	}
	result := envOptions{action: arguments[0], mode: "isolated"}
	if result.action != "profile-check" && result.action != "snapshot" && result.action != "show" && result.action != "resolve" && result.action != "run" {
		return envOptions{}, usageError{"unknown env command"}
	}
	seen := map[string]bool{}
	for position := 1; position < len(arguments); position++ {
		argument := arguments[position]
		if argument == "--" {
			if result.action != "run" || len(result.command) != 0 || position+1 >= len(arguments) {
				return envOptions{}, usageError{"env run requires -- COMMAND [ARGS...]"}
			}
			result.command = append([]string(nil), arguments[position+1:]...)
			break
		}
		if argument == "-h" || argument == "--help" {
			if position != 1 || len(arguments) != 2 {
				return envOptions{}, usageError{"env help takes no additional arguments"}
			}
			return envOptions{}, renderedUsage{envUsage}
		}
		switch argument {
		case "--profile", "--storage-root", "--context", "--mode", "--max-age", "--override", "--format":
			if position+1 >= len(arguments) {
				return envOptions{}, usageError{argument + " requires a value"}
			}
			value := arguments[position+1]
			position++
			if argument == "--override" {
				result.overrides = append(result.overrides, value)
				continue
			}
			if seen[argument] {
				return envOptions{}, usageError{argument + " may be specified only once"}
			}
			seen[argument] = true
			switch argument {
			case "--profile":
				result.profilePath = value
			case "--storage-root":
				result.storageRoot = value
			case "--context":
				result.context = value
				result.hasContext = true
			case "--mode":
				result.mode = value
			case "--max-age":
				duration, parseErr := time.ParseDuration(value)
				if parseErr != nil || duration <= 0 {
					return envOptions{}, usageError{"--max-age must be a positive duration"}
				}
				result.maxAge, result.hasMaxAge = duration, true
			case "--format":
				if value != "json" && value != "text" {
					return envOptions{}, usageError{"--format must be json or text"}
				}
				result.json = value == "json"
			}
		case "--with-values":
			if seen[argument] {
				return envOptions{}, usageError{argument + " may be specified only once"}
			}
			seen[argument], result.withValues = true, true
		case "--json":
			if seen[argument] {
				return envOptions{}, usageError{argument + " may be specified only once"}
			}
			seen[argument], result.json = true, true
		default:
			if strings.HasPrefix(argument, "-") {
				return envOptions{}, usageError{"unknown env option"}
			}
			if result.action == "profile-check" && result.profilePath == "" {
				result.profilePath = argument
				continue
			}
			return envOptions{}, usageError{"env command received an unexpected argument"}
		}
	}
	if result.action == "run" && len(result.command) == 0 {
		return envOptions{}, usageError{"env run requires -- COMMAND [ARGS...]"}
	}
	if result.withValues && result.action != "show" && result.action != "resolve" {
		return envOptions{}, usageError{"--with-values is supported only by env show and env resolve"}
	}
	if result.action != "snapshot" && result.hasContext {
		return envOptions{}, usageError{"--context is supported only by env snapshot"}
	}
	if result.action == "snapshot" && (!result.hasContext || result.context == "") {
		return envOptions{}, usageError{"env snapshot requires one non-empty --context LABEL"}
	}
	if result.action != "resolve" && result.action != "run" && len(result.overrides) != 0 {
		return envOptions{}, usageError{"--override is supported only by env resolve and env run"}
	}
	if result.action != "show" && result.hasMaxAge {
		return envOptions{}, usageError{"--max-age is supported only by env show"}
	}
	if result.action != "resolve" && result.action != "run" && seen["--mode"] {
		return envOptions{}, usageError{"--mode is supported only by env resolve and env run"}
	}
	if result.mode != "isolated" && result.mode != "overlay" {
		return envOptions{}, usageError{"--mode must be isolated or overlay"}
	}
	return result, nil
}

func runEnvProfileCheck(options envOptions, stdout io.Writer) error {
	profile, err := loadEnvironmentProfile(options.profilePath)
	if err != nil {
		return err
	}
	view := envProfileView{SchemaVersion: profile.SchemaVersion, ProfileID: profile.ProfileID, EntryCount: len(profile.Entries)}
	if options.json {
		return writeEnvJSON(stdout, view)
	}
	fmt.Fprintf(stdout, "valid profile: %s\n", view.ProfileID)
	fmt.Fprintf(stdout, "schema: %s\n", view.SchemaVersion)
	fmt.Fprintf(stdout, "entries: %d\n", view.EntryCount)
	return nil
}

func runEnvSnapshot(ctx context.Context, options envOptions, stdout io.Writer) error {
	profile, err := loadEnvironmentProfile(options.profilePath)
	if err != nil {
		return err
	}
	if err := validateStorageRoot(options.storageRoot); err != nil {
		return err
	}
	provenance := envsnap.SnapshotProvenance{Context: options.context}
	snapshot, err := envsnap.Capture(ctx, envsnap.CaptureRequest{
		Profile: profile, Environment: processEnvironment(), Provenance: provenance,
		ProducerVersion: buildinfo.Version,
	})
	if err != nil {
		return err
	}
	stored, err := envsnap.Store(ctx, envsnap.StoreRequest{StorageRoot: options.storageRoot, Snapshot: snapshot, Profile: &profile})
	if err != nil {
		return err
	}
	view := snapshotView(stored.Snapshot, string(stored.Disposition), false, 0)
	if options.json {
		return writeEnvJSON(stdout, view)
	}
	fmt.Fprintf(stdout, "snapshot %s\n", view.Disposition)
	fmt.Fprintf(stdout, "profile_id: %s\n", view.ProfileID)
	fmt.Fprintf(stdout, "content_fingerprint: %s\n", view.ContentFingerprint)
	fmt.Fprintf(stdout, "entries: %s\n", strings.Join(entryNames(stored.Snapshot), ", "))
	if len(stored.Snapshot.MissingOptional) != 0 {
		fmt.Fprintf(stdout, "missing_optional: %s\n", strings.Join(stored.Snapshot.MissingOptional, ", "))
	}
	return nil
}

func runEnvShow(ctx context.Context, options envOptions, stdout io.Writer) error {
	profile, profileID, err := profileForLoad(options)
	if err != nil {
		return err
	}
	if err := validateStorageRoot(options.storageRoot); err != nil {
		return err
	}
	request := envsnap.LoadRequest{StorageRoot: options.storageRoot, ProfileID: profileID, ExpectedProfile: profile}
	if options.hasMaxAge {
		request.MaxAge = options.maxAge
	}
	snapshot, err := envsnap.Load(ctx, request)
	if err != nil {
		return err
	}
	age := snapshot.Age
	if age == 0 {
		age = snapshotAge(snapshot.CapturedAt)
	}
	stale := snapshot.Stale
	view := snapshotView(snapshot, "", options.withValues, age)
	view.Stale = stale
	if options.json {
		return writeEnvJSON(stdout, view)
	}
	fmt.Fprintf(stdout, "profile_id: %s\n", view.ProfileID)
	fmt.Fprintf(stdout, "profile_fingerprint: %s\n", view.ProfileFingerprint)
	fmt.Fprintf(stdout, "content_fingerprint: %s\n", view.ContentFingerprint)
	fmt.Fprintf(stdout, "captured_at: %s\n", view.CapturedAt.UTC().Format(time.RFC3339Nano))
	fmt.Fprintf(stdout, "age_seconds: %d\n", view.AgeSeconds)
	fmt.Fprintf(stdout, "stale: %t\n", view.Stale)
	for _, entry := range view.Entries {
		if options.withValues {
			fmt.Fprintf(stdout, "%s [%s, %s] = %s\n", entry.Name, entry.Validator, entry.Source, entry.Value)
		} else {
			fmt.Fprintf(stdout, "%s [%s, %s]\n", entry.Name, entry.Validator, entry.Source)
		}
	}
	if len(view.MissingOptional) != 0 {
		fmt.Fprintf(stdout, "missing_optional: %s\n", strings.Join(view.MissingOptional, ", "))
	}
	return nil
}

func runEnvResolve(ctx context.Context, options envOptions, stdout io.Writer) error {
	profile, profileID, err := profileForLoad(options)
	if err != nil {
		return err
	}
	if profile == nil {
		return usageError{"env resolve requires --profile FILE"}
	}
	if err := validateStorageRoot(options.storageRoot); err != nil {
		return err
	}
	snapshot, err := envsnap.Load(ctx, envsnap.LoadRequest{StorageRoot: options.storageRoot, ProfileID: profileID, ExpectedProfile: profile})
	if err != nil {
		return err
	}
	overrides, err := parseOverrides(options.overrides)
	if err != nil {
		return err
	}
	mode := envsnap.ModeIsolated
	base := map[string]string{}
	if options.mode == "overlay" {
		mode = envsnap.ModeOverlay
		base = processEnvironment()
	}
	resolved, err := envsnap.Resolve(ctx, envsnap.ResolveRequest{Snapshot: snapshot, Mode: mode, Base: base, Overrides: overrides, Profile: profile})
	if err != nil {
		return err
	}
	view := resolvedView(resolved, options.withValues)
	if options.json {
		return writeEnvJSON(stdout, view)
	}
	fmt.Fprintf(stdout, "mode: %s\n", view.Mode)
	for _, provenance := range view.Provenance {
		fmt.Fprintf(stdout, "%s: %s\n", provenance.Name, provenance.Source)
	}
	if options.withValues {
		for _, name := range view.Names {
			fmt.Fprintf(stdout, "%s=%s\n", name, view.Environment[name])
		}
	}
	return nil
}

func runEnvRun(ctx context.Context, options envOptions, stdin io.Reader, stdout, stderr io.Writer) error {
	profile, profileID, err := profileForLoad(options)
	if err != nil {
		return err
	}
	if profile == nil {
		return usageError{"env run requires --profile FILE"}
	}
	if err := validateStorageRoot(options.storageRoot); err != nil {
		return err
	}
	snapshot, err := envsnap.Load(ctx, envsnap.LoadRequest{StorageRoot: options.storageRoot, ProfileID: profileID, ExpectedProfile: profile})
	if err != nil {
		return err
	}
	overrides, err := parseOverrides(options.overrides)
	if err != nil {
		return err
	}
	mode := envsnap.ModeIsolated
	base := map[string]string{}
	if options.mode == "overlay" {
		mode = envsnap.ModeOverlay
		base = processEnvironment()
	}
	resolved, err := envsnap.Resolve(ctx, envsnap.ResolveRequest{Snapshot: snapshot, Mode: mode, Base: base, Overrides: overrides, Profile: profile})
	if err != nil {
		return err
	}
	command := options.command
	path := command[0]
	if !strings.ContainsRune(path, filepath.Separator) {
		path = findExecutable(path, resolved.Environment["PATH"])
		if path == "" {
			return errors.New("environment command was not found")
		}
	}
	// Construct the child with the already-resolved path so os/exec cannot
	// perform a second lookup through the parent process's ambient PATH. Keep
	// Args unchanged so the child observes the operator's exact argv.
	child := exec.CommandContext(ctx, path, command[1:]...)
	child.Args = append([]string(nil), command...)
	child.Stdin, child.Stdout, child.Stderr = stdin, stdout, stderr
	child.Env = sortedEnvironment(resolved.Environment)
	if err := child.Run(); err != nil {
		if ctx.Err() != nil {
			return ctx.Err()
		}
		var exitError *exec.ExitError
		if errors.As(err, &exitError) {
			return childExitError{code: exitError.ExitCode()}
		}
		return errors.New("environment command failed")
	}
	return nil
}

func profileForLoad(options envOptions) (*envsnap.Profile, string, error) {
	if options.profilePath == "" {
		return nil, "", usageError{"env command requires --profile FILE"}
	}
	profile, err := loadEnvironmentProfile(options.profilePath)
	if err != nil {
		return nil, "", err
	}
	return &profile, profile.ProfileID, nil
}

func loadEnvironmentProfile(name string) (envsnap.Profile, error) {
	content, err := readEnvironmentProfile(name)
	if err != nil {
		return envsnap.Profile{}, err
	}
	return envsnap.DecodeProfile(content)
}

func readEnvironmentProfile(name string) ([]byte, error) {
	if name == "" || !filepath.IsAbs(name) || filepath.Clean(name) != name {
		return nil, usageError{"profile file must be absolute and clean"}
	}
	before, err := os.Lstat(name)
	if err != nil || !before.Mode().IsRegular() || before.Mode()&os.ModeSymlink != 0 || before.Mode().Perm() != 0o600 || !ownedSingleLink(before) || before.Size() > maxEnvironmentProfileBytes {
		return nil, errors.New("environment profile file is unsafe")
	}
	file, err := os.OpenFile(name, os.O_RDONLY|syscall.O_NOFOLLOW, 0)
	if err != nil {
		return nil, errors.New("environment profile file is unsafe")
	}
	defer file.Close()
	content, err := io.ReadAll(io.LimitReader(file, maxEnvironmentProfileBytes+1))
	if err != nil || len(content) == 0 || len(content) > maxEnvironmentProfileBytes || !utf8.Valid(content) {
		return nil, errors.New("environment profile file is empty, oversized, or invalid UTF-8")
	}
	after, err := os.Lstat(name)
	if err != nil || !os.SameFile(before, after) || after.Size() != int64(len(content)) || after.Mode().Perm() != 0o600 || !ownedSingleLink(after) || after.ModTime() != before.ModTime() {
		return nil, errors.New("environment profile file changed during read")
	}
	return content, nil
}

func validateStorageRoot(root string) error {
	if root == "" || !filepath.IsAbs(root) || filepath.Clean(root) != root {
		return usageError{"storage root must be absolute and clean"}
	}
	return nil
}

func processEnvironment() map[string]string {
	result := make(map[string]string)
	for _, entry := range os.Environ() {
		position := strings.IndexByte(entry, '=')
		if position > 0 {
			result[entry[:position]] = entry[position+1:]
		}
	}
	return result
}

func parseOverrides(values []string) (map[string]string, error) {
	result := make(map[string]string, len(values))
	for _, value := range values {
		position := strings.IndexByte(value, '=')
		if position <= 0 || !identifierPattern.MatchString(value[:position]) {
			return nil, usageError{"override must be NAME=VALUE"}
		}
		name := value[:position]
		if _, exists := result[name]; exists {
			return nil, usageError{"override names must be unique"}
		}
		result[name] = value[position+1:]
	}
	return result, nil
}

func snapshotView(snapshot envsnap.Snapshot, disposition string, withValues bool, age time.Duration) envSnapshotView {
	entries := make([]envEntryView, 0, len(snapshot.Entries))
	for _, entry := range snapshot.Entries {
		view := envEntryView{Name: entry.Name, Validator: entry.Validator, Source: entry.Source}
		if withValues {
			view.Value = entry.Value
		}
		entries = append(entries, view)
	}
	return envSnapshotView{
		SchemaVersion: snapshot.SchemaVersion, ProfileID: snapshot.ProfileID,
		ProfileFingerprint: snapshot.ProfileFingerprint, ProducerVersion: snapshot.ProducerVersion,
		Provenance: snapshot.Provenance, CapturedAt: snapshot.CapturedAt,
		AgeSeconds: int64(age / time.Second), Entries: entries,
		MissingOptional: append([]string(nil), snapshot.MissingOptional...), ContentFingerprint: snapshot.ContentFingerprint,
		Disposition: disposition,
	}
}

func resolvedView(resolved envsnap.ResolvedEnvironment, withValues bool) envResolvedView {
	names := make([]string, 0, len(resolved.Environment))
	for name := range resolved.Environment {
		names = append(names, name)
	}
	sort.Strings(names)
	provenance := make([]envProvenanceView, 0, len(resolved.Provenance))
	for _, item := range resolved.Provenance {
		provenance = append(provenance, envProvenanceView{Name: item.Name, Source: item.Source})
	}
	sort.Slice(provenance, func(left, right int) bool { return provenance[left].Name < provenance[right].Name })
	environment := map[string]string(nil)
	if withValues {
		environment = make(map[string]string, len(resolved.Environment))
		for _, name := range names {
			environment[name] = resolved.Environment[name]
		}
	}
	return envResolvedView{Mode: string(resolved.Mode), Names: names, Provenance: provenance, Environment: environment}
}

func entryNames(snapshot envsnap.Snapshot) []string {
	names := make([]string, 0, len(snapshot.Entries))
	for _, entry := range snapshot.Entries {
		names = append(names, entry.Name)
	}
	return names
}

func snapshotAge(capturedAt time.Time) time.Duration {
	age := time.Since(capturedAt)
	if age < 0 {
		return 0
	}
	return age
}

func writeEnvJSON(writer io.Writer, value any) error {
	content, err := json.Marshal(value)
	if err != nil {
		return err
	}
	content = append(content, '\n')
	_, err = writer.Write(content)
	return err
}

func sortedEnvironment(environment map[string]string) []string {
	names := make([]string, 0, len(environment))
	for name := range environment {
		names = append(names, name)
	}
	sort.Strings(names)
	result := make([]string, 0, len(names))
	for _, name := range names {
		result = append(result, name+"="+environment[name])
	}
	return result
}

func findExecutable(command, pathValue string) string {
	if pathValue == "" {
		return ""
	}
	for _, directory := range strings.Split(pathValue, string(filepath.ListSeparator)) {
		if directory == "" {
			directory = "."
		}
		candidate := filepath.Join(directory, command)
		info, err := os.Stat(candidate)
		if err == nil && info.Mode().IsRegular() && info.Mode()&0o111 != 0 {
			return candidate
		}
	}
	return ""
}
