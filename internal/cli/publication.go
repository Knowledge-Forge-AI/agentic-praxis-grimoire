package cli

import (
	"context"
	"errors"
	"path/filepath"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/internal/atomicfile"
	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/report"
)

func publish(ctx context.Context, configuration config, result report.Result) (string, error) {
	if configuration.legacy {
		return appendLegacy(ctx, configuration.outbox, configuration.project, result.Record.Phase, result.Bytes)
	}
	publication, err := report.Append(ctx, report.AppendRequest{OutboxRoot: configuration.outbox, Project: configuration.project, Phase: result.Record.Phase, Record: result.Record})
	if err != nil {
		return "", err
	}
	return publication.FinalPath, nil
}

func existingRecords(configuration config, phase string) ([]report.Record, error) {
	if configuration.legacy {
		content, exists, err := readLegacy(filepath.Join(configuration.outbox, configuration.project, phase+".report.txt"))
		if err != nil || !exists {
			return nil, err
		}
		return report.ParseRecords(content)
	}
	paths, err := atomicfile.Prepare(configuration.outbox, configuration.project, phase)
	if err != nil {
		return nil, err
	}
	names := []string{phase + ".git.show.report.txt", phase + ".git.diff.report.txt", phase + ".ops.report.txt"}
	var content []byte
	present := 0
	for _, name := range names {
		candidate, exists, readErr := atomicfile.ReadPrivate(filepath.Join(paths.Directory, name))
		if readErr != nil {
			return nil, readErr
		}
		if exists {
			content = candidate
			present++
		}
	}
	if present > 1 {
		return nil, errors.New("multiple current primary report artifacts")
	}
	if present == 0 {
		return nil, nil
	}
	return report.ParseRecords(content)
}
