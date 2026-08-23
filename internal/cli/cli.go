// Package cli owns the private APGR command-line adapter.
package cli

import (
	"context"
	"errors"
	"fmt"
	"io"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/internal/buildinfo"
)

const help = `Usage: apgr [--repository PATH] [--outbox-root PATH] [--project NAME] <command>

Commands:
  build-info            print deterministic machine-readable build information
  report show           publish one committed Git report
  report diff           publish one uncommitted Git report
  report operational    publish one operational report (alias: ops)
  report path           print a canonical primary path without creating it
  report recover        recover one interrupted canonical publication
  skills list           list embedded canonical skills
  skills context-report report embedded discovery context
  skills resolve        resolve one strict structured bundle request
  skills materialize    materialize one previously resolved bundle
  env profile-check     validate one canonical environment profile
  env snapshot          capture and store a canonical environment snapshot
  env show              show snapshot metadata and entry names
  env resolve           resolve an isolated or overlay environment
  env run               run one exact command argv without a shell
  analyze hotspots      analyze one exact source root without executing it
  response record       capture one immutable numbered response (alias: capture)

Options:
  -h, --help            show this help
  --version             print the APGR version
`

var identifierPattern = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9._-]*$`)

type usageError struct{ message string }

func (err usageError) Error() string { return err.message }

type config struct {
	repository    string
	outbox        string
	project       string
	legacy        bool
	compatibility bool
}

// Run executes one APGR invocation and returns the public exit class.
func Run(ctx context.Context, arguments []string, stdout, stderr io.Writer) int {
	return RunWithInput(ctx, arguments, strings.NewReader(""), stdout, stderr)
}

// RunWithInput executes one APGR invocation with an explicit standard input.
func RunWithInput(ctx context.Context, arguments []string, stdin io.Reader, stdout, stderr io.Writer) int {
	configuration, tail, err := parseGlobal(arguments)
	if err != nil {
		fmt.Fprintf(stderr, "apgr: %s\n", err)
		return 2
	}
	if len(tail) == 0 {
		fmt.Fprint(stderr, help)
		return 2
	}
	switch tail[0] {
	case "-h", "--help":
		if len(tail) != 1 {
			fmt.Fprint(stderr, help)
			return 2
		}
		fmt.Fprint(stdout, help)
		return 0
	case "--version":
		if len(tail) != 1 {
			fmt.Fprint(stderr, help)
			return 2
		}
		fmt.Fprintf(stdout, "apgr %s\n", buildinfo.Version)
		return 0
	case "build-info":
		if len(tail) != 1 {
			fmt.Fprintln(stderr, "apgr: build-info takes no arguments")
			return 2
		}
		content, jsonErr := buildinfo.JSON()
		if jsonErr != nil {
			fmt.Fprintln(stderr, "apgr: build information is unavailable")
			return 1
		}
		_, _ = stdout.Write(content)
		return 0
	case "report":
		err = runReport(ctx, configuration, tail[1:], stdout)
	case "skills":
		err = runSkills(ctx, tail[1:], stdin, stdout)
	case "env":
		err = runEnv(ctx, tail[1:], stdin, stdout, stderr)
	case "analyze":
		err = runAnalyze(ctx, configuration, tail[1:], stdout)
	case "response":
		err = runResponse(ctx, configuration, tail[1:], stdin, stdout)
	case "legacy":
		configuration.legacy = true
		err = runLegacy(ctx, configuration, tail[1:], stdout)
	default:
		err = usageError{"unknown command"}
	}
	if err == nil {
		return 0
	}
	name := "apgr"
	if configuration.legacy && len(tail) > 1 {
		name = tail[1]
	}
	if errors.Is(err, context.Canceled) {
		fmt.Fprintf(stderr, "%s: interrupted\n", name)
		return 1
	}
	var childExit childExitError
	if errors.As(err, &childExit) {
		if childExit.code > 0 {
			return childExit.code
		}
		return 1
	}
	var rendered renderedUsage
	if errors.As(err, &rendered) {
		fmt.Fprint(stderr, rendered.content)
		return 2
	}
	var invalid usageError
	if errors.As(err, &invalid) {
		fmt.Fprintf(stderr, "%s: %s\n", name, err)
		return 2
	}
	fmt.Fprintf(stderr, "%s: %s\n", name, err)
	return 1
}

func parseGlobal(arguments []string) (config, []string, error) {
	values := append([]string(nil), arguments...)
	result := config{}
	for len(values) > 0 && strings.HasPrefix(values[0], "--") {
		if values[0] == "--help" || values[0] == "--version" {
			break
		}
		if len(values) < 2 {
			return result, nil, usageError{values[0] + " requires a value"}
		}
		option, value := values[0], values[1]
		values = values[2:]
		switch option {
		case "--repository", "--repo":
			if result.repository != "" {
				return result, nil, usageError{"repository may be specified only once"}
			}
			result.repository = value
		case "--outbox-root":
			if result.outbox != "" {
				return result, nil, usageError{"outbox root may be specified only once"}
			}
			result.outbox = value
		case "--project":
			if result.project != "" {
				return result, nil, usageError{"project may be specified only once"}
			}
			result.project = value
		default:
			return result, nil, usageError{"unknown global option: " + option}
		}
	}
	return result, values, nil
}

func validateExplicit(configuration config, repositoryRequired bool) error {
	if repositoryRequired {
		if configuration.repository == "" || !filepath.IsAbs(configuration.repository) || filepath.Clean(configuration.repository) != configuration.repository {
			return usageError{"an absolute clean --repository is required"}
		}
		expected := filepath.Base(configuration.repository)
		if configuration.compatibility {
			expected = strings.TrimLeft(expected, ".")
		}
		if configuration.project != expected {
			return usageError{"--project must match the repository basename for report writes"}
		}
	}
	if configuration.project == "" || !identifierPattern.MatchString(configuration.project) {
		return usageError{"a valid --project is required"}
	}
	if !configuration.legacy {
		if configuration.outbox == "" || !filepath.IsAbs(configuration.outbox) || filepath.Clean(configuration.outbox) != configuration.outbox {
			return usageError{"an absolute clean --outbox-root is required"}
		}
	}
	return nil
}

func validateIdentifier(value, label string) error {
	if len(value) > 128 || value == "." || value == ".." || !identifierPattern.MatchString(value) {
		return usageError{label + " is invalid"}
	}
	return nil
}
