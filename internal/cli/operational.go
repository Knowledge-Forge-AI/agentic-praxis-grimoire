package cli

import (
	"context"
	"fmt"
	"io"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/internal/gitexec"
	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/report"
)

var commitInputPattern = regexp.MustCompile(`^[0-9A-Fa-f]{7,64}$`)

type operationalArguments struct {
	phase, source, result, finalGate, relatedCommit, relatedID string
}

func operational(ctx context.Context, configuration config, arguments []string, stdout io.Writer, compatibility bool) error {
	if len(arguments) > 0 && (arguments[0] == "-h" || arguments[0] == "--help") {
		fmt.Fprint(stdout, operationalUsage)
		return nil
	}
	parsed, err := parseOperational(arguments)
	if err != nil {
		if compatibility && len(arguments) < 4 {
			return renderedUsage{operationalUsage}
		}
		return err
	}
	if err := validateMetadata(parsed.result, "result"); err != nil {
		return err
	}
	if err := validateMetadata(parsed.finalGate, "final gate"); err != nil {
		return err
	}
	if parsed.relatedCommit != "" && parsed.relatedID == "" {
		return usageError{"related commit requires a related Git report id"}
	}
	if parsed.relatedCommit != "" {
		parsed.relatedCommit, err = resolveCommit(ctx, configuration.repository, parsed.relatedCommit)
		if err != nil {
			return err
		}
	}
	if parsed.relatedCommit != "" && parsed.relatedID != "GIT-SHOW-REPORT-"+parsed.relatedCommit {
		return usageError{"related commit and Git report id conflict"}
	}
	existing, err := existingRecords(configuration, parsed.phase)
	if err != nil {
		return err
	}
	if parsed.relatedID != "" {
		found := false
		for _, record := range existing {
			if record.ID == parsed.relatedID {
				found = true
				break
			}
		}
		if !found {
			return fmt.Errorf("related Git report id does not exist in the canonical phase report")
		}
	}
	destinations := destinationPaths(configuration, parsed.phase)
	source, name, err := readOperationalSource(ctx, parsed.source, destinations)
	if err != nil {
		return err
	}
	result, err := report.Operational(ctx, report.OperationalRequest{
		RequestMetadata: report.RequestMetadata{Phase: parsed.phase, Result: parsed.result, FinalGate: parsed.finalGate},
		Project:         configuration.project, SourceName: name, Source: source,
		RelatedCommit: parsed.relatedCommit, RelatedGitReportID: parsed.relatedID,
	}, existing)
	if err != nil {
		return err
	}
	path, err := publish(ctx, configuration, result)
	if err != nil {
		return err
	}
	fmt.Fprintf(stdout, "append-operational-report: appended %s to %s\n", result.Record.ID, path)
	return nil
}

func parseOperational(arguments []string) (operationalArguments, error) {
	if len(arguments) < 4 {
		return operationalArguments{}, usageError{"operational report requires PHASE SOURCE RESULT FINAL-GATE"}
	}
	result := operationalArguments{phase: arguments[0], source: arguments[1], result: arguments[2], finalGate: arguments[3]}
	for index := 4; index < len(arguments); {
		if index+1 >= len(arguments) {
			return operationalArguments{}, usageError{"operational report option requires a value"}
		}
		option, value := arguments[index], arguments[index+1]
		index += 2
		switch option {
		case "--related-commit":
			if result.relatedCommit != "" {
				return operationalArguments{}, usageError{"related commit may be specified only once"}
			}
			result.relatedCommit = value
		case "--related-git-report-id":
			if result.relatedID != "" {
				return operationalArguments{}, usageError{"related Git report id may be specified only once"}
			}
			result.relatedID = value
		default:
			return operationalArguments{}, usageError{"unknown operational report option"}
		}
	}
	if err := validateIdentifier(result.phase, "phase"); err != nil {
		return operationalArguments{}, err
	}
	return result, nil
}

func resolveCommit(ctx context.Context, repository, value string) (string, error) {
	if !commitInputPattern.MatchString(value) {
		return "", usageError{"related commit must be a 7-to-64-character hexadecimal object name"}
	}
	runner := gitexec.New(repository, "git")
	resolved, err := runner.Run(ctx, []string{"rev-parse", "--verify", value + "^{commit}"}, nil, nil)
	if err != nil {
		return "", usageError{"related commit does not resolve to a commit"}
	}
	commit := strings.TrimSuffix(string(resolved.Stdout), "\n")
	if len(commit) != 40 && len(commit) != 64 {
		return "", fmt.Errorf("repository precondition failed: related commit identity is unsupported")
	}
	return strings.ToLower(commit), nil
}

func destinationPaths(configuration config, phase string) []string {
	if configuration.legacy {
		return []string{filepath.Join(configuration.outbox, configuration.project, phase+".report.txt")}
	}
	directory := filepath.Join(configuration.outbox, configuration.project, phase)
	return []string{
		filepath.Join(directory, phase+".git.show.report.txt"),
		filepath.Join(directory, phase+".git.diff.report.txt"),
		filepath.Join(directory, phase+".ops.report.txt"),
	}
}
