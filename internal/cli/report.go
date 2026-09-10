package cli

import (
	"context"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/internal/atomicfile"
	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/report"
)

const (
	reportUsage = `Usage: apgr report <command> [options]

Commands:
  show         publish one committed Git report
  diff         publish one uncommitted Git report
  operational  publish one operational report (alias: ops)
  path         print a canonical primary path without creating it
  recover      recover one interrupted canonical publication
  verify       verify one persisted report file

Options:
  --idempotent  opt in to exact retry for show, diff, and operational
  -h, --help   show this help
`
	canonicalShowUsage = `Usage: apgr report show PHASE COMMIT STATUS-DOC RESULT FINAL-GATE [--idempotent]

Append a Git commit report. --idempotent returns already-present for identical
retained record bytes and rejects a same-identity replay with differing bytes.
`
	canonicalDiffUsage = `Usage: apgr report diff PHASE RESULT FINAL-GATE [--status-doc PATH] [--idempotent]

Append a Git snapshot report. --idempotent returns already-present for identical
retained record bytes and rejects a same-identity replay with differing bytes.
`
	canonicalOperationalUsage = `Usage: apgr report operational PHASE SOURCE RESULT FINAL-GATE [options]

Options:
  --related-commit COMMIT
  --related-git-report-id ID
  --idempotent  return already-present for identical retained record bytes;
                reject a same-identity replay with differing bytes
  -h, --help

Alias: apgr report ops
`
	verifyUsage = `Usage: apgr report verify <path>

Verify one persisted report file without repository or outbox authority.
`
	showUsage = `Usage: git-show-report <ticket-id> <commit-hash> <status-doc-path-from-repo-root> <result> <final-gate>

Append one complete version-2 Git commit report to the current APGR phase outbox:
  ~/Documents/agent/outbox/<repo-name>/<ticket-id>/<ticket-id>.git.show.report.txt

Environment:
  APGR_OUTBOX_ROOT      Override the canonical outbox root directory.
  GIT_SHOW_REPORT_ROOT  Retain the legacy omnibus destination and append semantics.
`
	diffUsage = `Usage: git-diff-report <phase-id> <result> <final-gate> [--status-doc <repository-relative-path>]

Append one complete version-1 uncommitted Git snapshot report to the current APGR phase outbox:
  ~/Documents/agent/outbox/<repo-name>/<phase-id>/<phase-id>.git.diff.report.txt

Environment:
  APGR_OUTBOX_ROOT      Override the canonical outbox root directory.
  GIT_SHOW_REPORT_ROOT  Retain the legacy omnibus destination and append semantics.
`
	operationalUsage = `Usage: append-operational-report <ticket-id> <operational-report-path> <result> <final-gate> [options]

Append one complete operational-report record to the current APGR phase outbox:
  ~/Documents/agent/outbox/<repo-name>/<ticket-id>/<ticket-id>.ops.report.txt
  (or inside the current Git show/diff primary when one exists)

Options:
  --related-commit <commit>
  --related-git-report-id <GIT-SHOW-REPORT-id|GIT-DIFF-REPORT-id>
  -h, --help

Environment:
  APGR_OUTBOX_ROOT      Override the canonical outbox root directory.
  GIT_SHOW_REPORT_ROOT  Retain the legacy omnibus destination and append semantics.
`
)

func runReport(ctx context.Context, configuration config, arguments []string, stdout io.Writer) error {
	if len(arguments) == 0 {
		return usageError{"report requires show, diff, operational, ops, path, recover, or verify"}
	}
	action, tail := arguments[0], arguments[1:]
	if action == "-h" || action == "--help" || action == "help" {
		fmt.Fprint(stdout, reportUsage)
		return nil
	}
	if action == "path" {
		return reportPath(configuration, tail, stdout)
	}
	if action == "verify" {
		return verify(ctx, tail, stdout)
	}
	if err := validateExplicit(configuration, true); err != nil {
		return err
	}
	switch action {
	case "show":
		return show(ctx, configuration, tail, stdout, false)
	case "diff":
		return diff(ctx, configuration, tail, stdout, false)
	case "operational", "ops":
		return operational(ctx, configuration, tail, stdout, false)
	case "recover":
		return recover(ctx, configuration, tail, stdout)
	default:
		return usageError{"unknown report command"}
	}
}

func runLegacy(ctx context.Context, configuration config, arguments []string, stdout io.Writer) error {
	if len(arguments) == 0 {
		return usageError{"legacy command is required"}
	}
	command, tail := arguments[0], arguments[1:]
	configuration.compatibility = true
	if configuration.repository == "" {
		return usageError{"an absolute clean --repository is required"}
	}
	configuration.project = strings.TrimLeft(filepath.Base(configuration.repository), ".")
	if configuration.project == "" {
		return errors.New("normalized repository name is empty")
	}
	if root := os.Getenv("GIT_SHOW_REPORT_ROOT"); root != "" {
		configuration.outbox = root
		configuration.legacy = true
	} else {
		configuration.legacy = false
		if configuration.outbox == "" {
			configuration.outbox = os.Getenv("APGR_OUTBOX_ROOT")
		}
		if configuration.outbox == "" {
			home, err := os.UserHomeDir()
			if err != nil {
				return errors.New("default outbox is unavailable")
			}
			configuration.outbox = filepath.Join(home, "Documents", "agent", "outbox")
		}
	}
	if err := validateExplicit(configuration, true); err != nil {
		return err
	}
	switch command {
	case "git-show-report":
		return show(ctx, configuration, tail, stdout, true)
	case "git-diff-report":
		return diff(ctx, configuration, tail, stdout, true)
	case "append-operational-report":
		return operational(ctx, configuration, tail, stdout, true)
	default:
		return usageError{"unknown historical report command"}
	}
}

func show(ctx context.Context, configuration config, arguments []string, stdout io.Writer, compatibility bool) error {
	if len(arguments) > 0 && (arguments[0] == "-h" || arguments[0] == "--help") {
		usage := canonicalShowUsage
		if compatibility {
			usage = showUsage
		}
		fmt.Fprint(stdout, usage)
		return nil
	}
	if compatibility {
		if len(arguments) != 5 {
			return renderedUsage{showUsage}
		}
	} else {
		if len(arguments) < 5 {
			return usageError{"report show requires PHASE COMMIT STATUS-DOC RESULT FINAL-GATE [--idempotent]"}
		}
	}
	phase := arguments[0]
	commit := arguments[1]
	statusDoc := arguments[2]
	result := arguments[3]
	finalGate := arguments[4]

	idempotent := false
	if !compatibility {
		for i := 5; i < len(arguments); i++ {
			switch arguments[i] {
			case "--idempotent":
				if idempotent {
					return usageError{"--idempotent may be specified only once"}
				}
				idempotent = true
			default:
				return usageError{"unknown report show option: " + arguments[i]}
			}
		}
	}

	if err := validateIdentifier(phase, "ticket id"); err != nil {
		return err
	}
	if !commitInputPattern.MatchString(commit) {
		return usageError{"commit must be a 7-to-64-character hexadecimal object name"}
	}
	if err := validateMetadata(statusDoc, "status document path"); err != nil {
		return err
	}
	if err := validateMetadata(result, "result"); err != nil {
		return err
	}
	if err := validateMetadata(finalGate, "final gate"); err != nil {
		return err
	}
	service, err := report.New(report.Options{Repository: configuration.repository})
	if err != nil {
		return err
	}
	for _, s := range []string{"metadata", "changed-files", "numstat", "commit-message", "patch", "record-assembly"} {
		if err := testFailStep(s); err != nil {
			return err
		}
	}
	res, err := service.Show(ctx, report.ShowRequest{RequestMetadata: report.RequestMetadata{Phase: phase, Result: result, FinalGate: finalGate}, Commit: commit, StatusDoc: statusDoc})
	if err != nil {
		return err
	}
	policy := report.AppendAlways
	if idempotent {
		policy = report.AppendIdempotent
	}
	publication, err := publish(ctx, configuration, res, policy)
	if err != nil {
		return err
	}
	commitID := strings.TrimPrefix(res.Record.ID, "GIT-SHOW-REPORT-")
	action := "appended"
	if publication.Disposition == report.PublishedAlreadyPresent {
		action = "already-present"
	}
	fmt.Fprintf(stdout, "git-show-report: %s %s to %s\n", action, commitID, publication.FinalPath)
	return nil
}

func diff(ctx context.Context, configuration config, arguments []string, stdout io.Writer, compatibility bool) error {
	if len(arguments) > 0 && (arguments[0] == "-h" || arguments[0] == "--help") {
		usage := canonicalDiffUsage
		if compatibility {
			usage = diffUsage
		}
		fmt.Fprint(stdout, usage)
		return nil
	}
	if compatibility {
		if len(arguments) != 3 && len(arguments) != 5 {
			return renderedUsage{diffUsage}
		}
	} else {
		if len(arguments) < 3 {
			return usageError{"report diff requires PHASE RESULT FINAL-GATE [--status-doc PATH] [--idempotent]"}
		}
	}
	phase := arguments[0]
	result := arguments[1]
	finalGate := arguments[2]

	status := ""
	idempotent := false
	if compatibility {
		if len(arguments) == 5 {
			if arguments[3] != "--status-doc" || arguments[4] == "" {
				return renderedUsage{diffUsage}
			}
			status = arguments[4]
		}
	} else {
		for i := 3; i < len(arguments); i++ {
			switch arguments[i] {
			case "--idempotent":
				if idempotent {
					return usageError{"--idempotent may be specified only once"}
				}
				idempotent = true
			case "--status-doc":
				if status != "" {
					return usageError{"--status-doc may be specified only once"}
				}
				if i+1 >= len(arguments) {
					return usageError{"report diff status document option requires a value"}
				}
				status = arguments[i+1]
				i++
			default:
				return usageError{"unknown report diff option: " + arguments[i]}
			}
		}
	}

	if err := validateIdentifier(phase, "phase id"); err != nil {
		return err
	}
	if err := validateMetadata(result, "result"); err != nil {
		return err
	}
	if err := validateMetadata(finalGate, "final gate"); err != nil {
		return err
	}
	if status != "" {
		if filepath.IsAbs(status) || filepath.Clean(status) != status || status == "." || strings.HasPrefix(status, ".."+string(filepath.Separator)) {
			return usageError{"status document path must be clean and repository-relative"}
		}
	}
	service, err := report.New(report.Options{Repository: configuration.repository})
	if err != nil {
		return err
	}
	res, err := service.Diff(ctx, report.DiffRequest{RequestMetadata: report.RequestMetadata{Phase: phase, Result: result, FinalGate: finalGate}, StatusDoc: status})
	if err != nil {
		return err
	}
	policy := report.AppendAlways
	if idempotent {
		policy = report.AppendIdempotent
	}
	publication, err := publish(ctx, configuration, res, policy)
	if err != nil {
		return err
	}
	action := "appended"
	if publication.Disposition == report.PublishedAlreadyPresent {
		action = "already-present"
	}
	fmt.Fprintf(stdout, "git-diff-report: %s %s to %s\n", action, res.Record.ID, publication.FinalPath)
	return nil
}

func verify(ctx context.Context, arguments []string, stdout io.Writer) error {
	if len(arguments) > 0 && (arguments[0] == "-h" || arguments[0] == "--help") {
		fmt.Fprint(stdout, verifyUsage)
		return nil
	}
	if len(arguments) != 1 {
		return usageError{"report verify requires PATH"}
	}
	path := arguments[0]
	if path == "" {
		return usageError{"report verify requires a non-empty PATH"}
	}
	verification, err := report.VerifyFile(ctx, path)
	if err != nil {
		return err
	}
	records := "records"
	if verification.RecordCount == 1 {
		records = "record"
	}
	if verification.CompatibilityLimited {
		fmt.Fprintf(stdout, "verified %d %s (compatibility-limited)\n", verification.RecordCount, records)
	} else {
		fmt.Fprintf(stdout, "verified %d %s\n", verification.RecordCount, records)
	}
	return nil
}

type renderedUsage struct{ content string }

func (err renderedUsage) Error() string { return err.content }

func validateMetadata(value, label string) error {
	for _, character := range value {
		if character < 0x20 || character == 0x7f {
			return usageError{label + " contains a control character"}
		}
	}
	return nil
}

func reportPath(configuration config, arguments []string, stdout io.Writer) error {
	if err := validateExplicit(configuration, false); err != nil {
		return err
	}
	var phase, kind string
	for i := 0; i < len(arguments); i++ {
		switch arguments[i] {
		case "--phase":
			if i+1 >= len(arguments) || phase != "" {
				return usageError{"report path requires --phase PHASE --kind KIND"}
			}
			phase = arguments[i+1]
			i++
		case "--kind":
			if i+1 >= len(arguments) || kind != "" {
				return usageError{"report path requires --phase PHASE --kind KIND"}
			}
			kind = arguments[i+1]
			i++
		default:
			return usageError{"report path requires --phase PHASE --kind KIND"}
		}
	}
	if phase == "" || kind == "" {
		return usageError{"report path requires --phase PHASE --kind KIND"}
	}
	if err := validateIdentifier(phase, "phase"); err != nil {
		return err
	}
	suffix := map[string]string{"show": "git.show.report.txt", "diff": "git.diff.report.txt", "ops": "ops.report.txt"}[kind]
	if suffix == "" {
		return usageError{"report kind must be show, diff, or ops"}
	}
	fmt.Fprintln(stdout, filepath.Join(configuration.outbox, configuration.project, phase, phase+"."+suffix))
	return nil
}

func recover(ctx context.Context, configuration config, arguments []string, stdout io.Writer) error {
	if len(arguments) != 2 || arguments[0] != "--phase" {
		return usageError{"report recover requires --phase PHASE"}
	}
	phase := arguments[1]
	if err := validateIdentifier(phase, "phase"); err != nil {
		return err
	}
	paths, err := atomicfile.Prepare(configuration.outbox, configuration.project, phase)
	if err != nil {
		return err
	}
	allowed := []string{phase + ".git.show.report.txt", phase + ".git.diff.report.txt", phase + ".ops.report.txt"}
	recovered, err := atomicfile.Recover(ctx, paths, allowed)
	if err != nil {
		return err
	}
	if recovered {
		fmt.Fprintln(stdout, "recovered")
	} else {
		fmt.Fprintln(stdout, "no transaction")
	}
	return nil
}
