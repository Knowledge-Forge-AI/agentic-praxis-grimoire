package cli

import (
	"context"
	"errors"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/hotspot"
	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/internal/buildinfo"
)

const analyzeUsage = `Usage: apgr --repository ABSOLUTE-PATH analyze hotspots [options]

Options:
  --format terminal|json|markdown  output format (default: terminal)
  --output ABSOLUTE-PATH          create one new report outside the analyzed root
  --root-id ID                    logical root identity (default: safe root basename)
  --top N                         terminal display rows, 1..100 (default: 10)
  --max-files N                   maximum analyzed files (default: 50000)
  --max-bytes-per-file N          maximum bytes per file (default: 16777216)
  --max-total-bytes N             maximum total bytes read (default: 536870912)
  --timeout DURATION              maximum elapsed time (default: 2m)
  --include-language LANGUAGE     include one frozen language (repeatable)
  --include-path RELATIVE-PATH    include one literal relative subtree (repeatable)
  --exclude-path RELATIVE-PATH    exclude one literal relative subtree (repeatable)
  --disable-default-exclusions    scan ordinary default-excluded directories
  -h, --help                      show this help
`

type analyzeOptions struct {
	format  string
	output  string
	request hotspot.Request
}

func runAnalyze(ctx context.Context, configuration config, arguments []string, stdout io.Writer) error {
	if len(arguments) == 0 || arguments[0] != "hotspots" {
		return usageError{"analyze requires the hotspots command"}
	}
	if configuration.repository == "" || !filepath.IsAbs(configuration.repository) || filepath.Clean(configuration.repository) != configuration.repository {
		return usageError{"an absolute clean --repository is required"}
	}
	options, err := parseAnalyzeOptions(configuration.repository, arguments[1:])
	if err != nil {
		return err
	}
	if options.output != "" {
		if err := validateAnalyzeOutput(options.request.Root, options.output); err != nil {
			return err
		}
	}
	report, err := hotspot.Analyze(ctx, options.request)
	if err != nil {
		return err
	}
	content, err := renderAnalyzeReport(options.format, report)
	if err != nil {
		return err
	}
	if options.output == "" {
		_, err = stdout.Write(content)
		return err
	}
	return writeAnalyzeOutput(options.output, content)
}

func renderAnalyzeReport(format string, report hotspot.Report) ([]byte, error) {
	switch format {
	case "terminal":
		return hotspot.RenderTerminal(report)
	case "json":
		return hotspot.MarshalJSON(report)
	case "markdown":
		return hotspot.RenderMarkdown(report)
	}
	return nil, usageError{"format must be terminal, json, or markdown"}
}

func writeAnalyzeOutput(path string, content []byte) error {
	file, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o600)
	if errors.Is(err, os.ErrExist) {
		return errors.New("output destination already exists")
	}
	if err != nil {
		return errors.New("output destination could not be created")
	}
	written := false
	defer func() {
		_ = file.Close()
		if !written {
			_ = os.Remove(path)
		}
	}()
	if _, err := file.Write(content); err != nil {
		return errors.New("output destination could not be written")
	}
	if err := file.Sync(); err != nil {
		return errors.New("output destination could not be synchronized")
	}
	if err := file.Close(); err != nil {
		return errors.New("output destination could not be closed")
	}
	written = true
	return nil
}

func parseAnalyzeOptions(root string, arguments []string) (analyzeOptions, error) {
	request := hotspot.DefaultRequest(root)
	request.ToolVersion = buildinfo.Version
	result := analyzeOptions{format: "terminal", request: request}
	seen := map[string]bool{}
	for index := 0; index < len(arguments); index++ {
		argument := arguments[index]
		if argument == "-h" || argument == "--help" {
			if len(arguments) != 1 {
				return analyzeOptions{}, usageError{"analyze help takes no additional arguments"}
			}
			return analyzeOptions{}, renderedUsage{analyzeUsage}
		}
		if argument == "--disable-default-exclusions" {
			if seen[argument] {
				return analyzeOptions{}, usageError{"--disable-default-exclusions may be specified only once"}
			}
			seen[argument] = true
			result.request.Filters.DisableDefaultExclusions = true
			continue
		}
		if index+1 >= len(arguments) {
			return analyzeOptions{}, usageError{argument + " requires a value"}
		}
		value := arguments[index+1]
		index++
		switch argument {
		case "--include-language":
			result.request.Filters.IncludeLanguages = append(result.request.Filters.IncludeLanguages, hotspot.Language(value))
		case "--include-path":
			result.request.Filters.IncludePaths = append(result.request.Filters.IncludePaths, value)
		case "--exclude-path":
			result.request.Filters.ExcludePaths = append(result.request.Filters.ExcludePaths, value)
		default:
			if !singleAnalyzeOption(argument) {
				return analyzeOptions{}, usageError{"unknown analyze option: " + argument}
			}
			if seen[argument] {
				return analyzeOptions{}, usageError{argument + " may be specified only once"}
			}
			seen[argument] = true
			if err := applyAnalyzeOption(&result, argument, value); err != nil {
				return analyzeOptions{}, err
			}
		}
	}
	return result, nil
}

func singleAnalyzeOption(value string) bool {
	switch value {
	case "--format", "--output", "--root-id", "--top", "--max-files", "--max-bytes-per-file", "--max-total-bytes", "--timeout":
		return true
	default:
		return false
	}
}

func applyAnalyzeOption(options *analyzeOptions, name, value string) error {
	switch name {
	case "--format":
		if value != "terminal" && value != "json" && value != "markdown" {
			return usageError{"format must be terminal, json, or markdown"}
		}
		options.format = value
	case "--output":
		options.output = value
	case "--root-id":
		options.request.RootID = value
	case "--top", "--max-files":
		parsed, err := strconv.Atoi(value)
		if err != nil {
			return usageError{strings.TrimPrefix(strings.ReplaceAll(name, "-", " "), "  ") + " must be an integer"}
		}
		if name == "--top" {
			options.request.DisplayTopN = parsed
		} else {
			options.request.Limits.MaxFiles = parsed
		}
	case "--max-bytes-per-file", "--max-total-bytes":
		parsed, err := strconv.ParseInt(value, 10, 64)
		if err != nil {
			return usageError{strings.TrimPrefix(strings.ReplaceAll(name, "-", " "), "  ") + " must be an integer"}
		}
		if name == "--max-bytes-per-file" {
			options.request.Limits.MaxBytesPerFile = parsed
		} else {
			options.request.Limits.MaxTotalBytes = parsed
		}
	case "--timeout":
		parsed, err := time.ParseDuration(value)
		if err != nil {
			return usageError{"timeout must be a duration"}
		}
		options.request.Limits.MaxDuration = parsed
	}
	return nil
}

func validateAnalyzeOutput(root, output string) error {
	if output == "" || !filepath.IsAbs(output) || filepath.Clean(output) != output {
		return usageError{"--output must be an absolute clean path"}
	}
	if pathWithin(root, output) {
		return usageError{"--output must be outside the analyzed root"}
	}
	parent := filepath.Dir(output)
	metadata, err := os.Lstat(parent)
	if err != nil || metadata.Mode()&os.ModeSymlink != 0 || !metadata.IsDir() {
		return usageError{"--output parent must be an existing direct directory"}
	}
	resolved, err := filepath.EvalSymlinks(parent)
	if err != nil || resolved != parent {
		return usageError{"--output parent must be a physical directory"}
	}
	if _, err := os.Lstat(output); err == nil {
		return nil
	} else if !errors.Is(err, os.ErrNotExist) {
		return usageError{"--output destination is unsafe"}
	}
	return nil
}

func pathWithin(root, candidate string) bool {
	relative, err := filepath.Rel(root, candidate)
	if err != nil {
		return false
	}
	return relative == "." || relative != ".." && !strings.HasPrefix(relative, ".."+string(filepath.Separator))
}
