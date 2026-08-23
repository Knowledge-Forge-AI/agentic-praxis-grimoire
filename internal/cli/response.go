package cli

import (
	"context"
	"errors"
	"fmt"
	"io"
	"path/filepath"
	"strings"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/internal/response"
)

const responseUsage = `Usage: apgr response [record|capture] [--phase PHASE] [--input PATH]

Capture one exact response body in the canonical numbered phase outbox.
  --phase PHASE       response phase identity (or provide PHASE positionally)
  --input PATH        read exact bytes from a regular file; '-' means stdin
  --file PATH         compatibility alias for --input
  -h, --help          show this help
`

func runResponse(ctx context.Context, configuration config, arguments []string, stdin io.Reader, stdout io.Writer) error {
	if len(arguments) == 1 && (arguments[0] == "-h" || arguments[0] == "--help") {
		_, _ = io.WriteString(stdout, responseUsage)
		return nil
	}
	if len(arguments) > 0 && (arguments[0] == "-h" || arguments[0] == "--help") {
		return usageError{"response help takes no additional arguments"}
	}
	values := append([]string(nil), arguments...)
	if len(values) > 0 && (values[0] == "record" || values[0] == "capture") {
		values = values[1:]
	}
	phase := ""
	inputPath := ""
	inputSelected := false
	for position := 0; position < len(values); position++ {
		value := values[position]
		switch value {
		case "--phase":
			if position+1 >= len(values) || phase != "" {
				return usageError{"--phase requires one value"}
			}
			phase = values[position+1]
			position++
		case "--input", "--file":
			if position+1 >= len(values) || inputSelected {
				return usageError{fmt.Sprintf("%s requires one value", value)}
			}
			inputSelected = true
			inputPath = values[position+1]
			position++
		case "--stdin":
			if inputSelected {
				return usageError{"response input may be specified only once"}
			}
			inputSelected = true
			inputPath = "-"
		default:
			if strings.HasPrefix(value, "-") {
				return usageError{fmt.Sprintf("unknown response option: %s", value)}
			}
			if phase != "" {
				return usageError{"response phase was specified more than once"}
			}
			phase = value
		}
	}
	if phase == "" {
		return usageError{"response phase is required"}
	}
	if configuration.outbox == "" || !filepath.IsAbs(configuration.outbox) || filepath.Clean(configuration.outbox) != configuration.outbox {
		return usageError{"an absolute clean --outbox-root is required"}
	}
	project := configuration.project
	if configuration.repository != "" {
		if !filepath.IsAbs(configuration.repository) || filepath.Clean(configuration.repository) != configuration.repository {
			return usageError{"an absolute clean --repository is required"}
		}
		repositoryProject := filepath.Base(configuration.repository)
		if project == "" {
			project = repositoryProject
		} else if project != repositoryProject {
			return usageError{"--project must match the repository basename for response writes"}
		}
	}
	if project == "" {
		return usageError{"a valid --project is required"}
	}
	options := response.Options{
		OutboxRoot: configuration.outbox,
		Project:    project,
		Phase:      phase,
	}
	if !inputSelected || inputPath == "-" {
		options.Stdin = stdin
	} else {
		options.InputPath = inputPath
	}
	created, err := response.Capture(ctx, options)
	if err != nil {
		if errors.Is(err, response.ErrUsage) {
			return usageError{err.Error()}
		}
		return err
	}
	_, _ = fmt.Fprintln(stdout, created)
	return nil
}
