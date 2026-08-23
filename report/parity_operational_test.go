package report

import (
	"bytes"
	"context"
	"errors"
	"os"
	"path/filepath"
	"testing"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/schema"
)

func writeOperationalSource(t *testing.T, directory, name string, body []byte) string {
	t.Helper()
	path := filepath.Join(directory, name)
	writeFileTest(t, path, body)
	if err := os.Chmod(path, 0o600); err != nil {
		t.Fatal(err)
	}
	return path
}

func lastRecordTest(t *testing.T, content []byte) Record {
	t.Helper()
	records, err := ParseRecords(content)
	if err != nil {
		t.Fatal(err)
	}
	if len(records) == 0 {
		t.Fatal("report contains no records")
	}
	return records[len(records)-1]
}

func TestOperationalStandaloneDifferentialParity(t *testing.T) {
	repository, environment := newGitRepository(t)
	writeFileTest(t, filepath.Join(repository, "tracked.txt"), []byte("tracked\n"))
	runGitTest(t, repository, nil, "add", "tracked.txt")
	_ = commitTest(t, repository, environment, "root", "", false)
	cases := []struct {
		phase, name string
		body        []byte
	}{
		{"OPS-V1", "canonical.txt", []byte("report_schema: operational-report-v1\nphase: OPS-V1\noutcome: passed\n")},
		{"OPS-LEGACY", "legacy.txt", []byte("phase: OPS-LEGACY\noutcome: passed\nlegacy field: retained\n")},
		{"OPS-FREE", "free.txt", []byte("free form operational evidence")},
	}
	for _, testCase := range cases {
		t.Run(testCase.phase, func(t *testing.T) {
			result, err := Operational(context.Background(), OperationalRequest{
				RequestMetadata: RequestMetadata{Phase: testCase.phase, Result: "passed", FinalGate: "gate"},
				Project:         filepath.Base(repository), SourceName: testCase.name, Source: testCase.body,
			}, nil)
			if err != nil {
				t.Fatal(err)
			}
			outbox := filepath.Join(t.TempDir(), "outbox")
			source := writeOperationalSource(t, t.TempDir(), testCase.name, testCase.body)
			exit, output := pythonCommandTest(t, repository, "append-operational-report", outbox, testCase.phase, source, "passed", "gate")
			if exit != 0 {
				t.Fatalf("Python operational oracle exited %d: %s", exit, output)
			}
			pythonBytes, err := os.ReadFile(canonicalPythonPath(outbox, repository, testCase.phase, "ops"))
			if err != nil {
				t.Fatal(err)
			}
			pythonRecord := lastRecordTest(t, pythonBytes)
			encoded, err := buildRecord(pythonRecord)
			if err != nil {
				t.Fatal(err)
			}
			assertBytesEqual(t, encoded, result.Bytes)
		})
	}
}

func TestOperationalShowAndDiffAssociationParity(t *testing.T) {
	t.Run("show", func(t *testing.T) {
		repository, environment := newGitRepository(t)
		writeFileTest(t, filepath.Join(repository, "tracked.txt"), []byte("tracked\n"))
		runGitTest(t, repository, nil, "add", "tracked.txt")
		commit := commitTest(t, repository, environment, "root", "", false)
		service, err := New(Options{Repository: repository})
		if err != nil {
			t.Fatal(err)
		}
		show, err := service.Show(context.Background(), ShowRequest{RequestMetadata: RequestMetadata{Phase: "OPS-SHOW", Result: "passed", FinalGate: "gate"}, Commit: commit, StatusDoc: "status.md"})
		if err != nil {
			t.Fatal(err)
		}
		body := []byte("report_schema: operational-report-v1\nphase: OPS-SHOW\noutcome: passed\nprimary_commit: " + commit + "\n")
		operational, err := Operational(context.Background(), OperationalRequest{
			RequestMetadata: RequestMetadata{Phase: "OPS-SHOW", Result: "passed", FinalGate: "gate"}, Project: filepath.Base(repository),
			SourceName: "show-ops.txt", Source: body, RelatedCommit: commit, RelatedGitReportID: show.Record.ID,
		}, []Record{show.Record})
		if err != nil {
			t.Fatal(err)
		}
		outbox := filepath.Join(t.TempDir(), "outbox")
		if exit, output := pythonCommandTest(t, repository, "git-show-report", outbox, "OPS-SHOW", commit, "status.md", "passed", "gate"); exit != 0 {
			t.Fatalf("Python show setup exited %d: %s", exit, output)
		}
		source := writeOperationalSource(t, t.TempDir(), "show-ops.txt", body)
		if exit, output := pythonCommandTest(t, repository, "append-operational-report", outbox, "OPS-SHOW", source, "passed", "gate", "--related-commit", commit, "--related-git-report-id", show.Record.ID); exit != 0 {
			t.Fatalf("Python show association exited %d: %s", exit, output)
		}
		content, err := os.ReadFile(canonicalPythonPath(outbox, repository, "OPS-SHOW", "git.show"))
		if err != nil {
			t.Fatal(err)
		}
		pythonRecord := lastRecordTest(t, content)
		encoded, err := buildRecord(pythonRecord)
		if err != nil {
			t.Fatal(err)
		}
		assertBytesEqual(t, encoded, operational.Bytes)
	})

	t.Run("diff", func(t *testing.T) {
		repository, _ := initializeDiffRepository(t)
		writeFileTest(t, filepath.Join(repository, "tracked.txt"), []byte("changed and longer\n"))
		service, err := New(Options{Repository: repository})
		if err != nil {
			t.Fatal(err)
		}
		diff, err := service.Diff(context.Background(), DiffRequest{RequestMetadata: RequestMetadata{Phase: "OPS-DIFF", Result: "passed", FinalGate: "gate"}})
		if err != nil {
			t.Fatal(err)
		}
		body := []byte("report_schema: operational-report-v1\nphase: OPS-DIFF\noutcome: passed\nprimary_git_report_id: " + diff.Record.ID + "\n")
		operational, err := Operational(context.Background(), OperationalRequest{
			RequestMetadata: RequestMetadata{Phase: "OPS-DIFF", Result: "passed", FinalGate: "gate"}, Project: filepath.Base(repository),
			SourceName: "diff-ops.txt", Source: body, RelatedGitReportID: diff.Record.ID,
		}, []Record{diff.Record})
		if err != nil {
			t.Fatal(err)
		}
		outbox := filepath.Join(t.TempDir(), "outbox")
		if exit, output := pythonCommandTest(t, repository, "git-diff-report", outbox, "OPS-DIFF", "passed", "gate"); exit != 0 {
			t.Fatalf("Python diff setup exited %d: %s", exit, output)
		}
		source := writeOperationalSource(t, t.TempDir(), "diff-ops.txt", body)
		if exit, output := pythonCommandTest(t, repository, "append-operational-report", outbox, "OPS-DIFF", source, "passed", "gate", "--related-git-report-id", diff.Record.ID); exit != 0 {
			t.Fatalf("Python diff association exited %d: %s", exit, output)
		}
		content, err := os.ReadFile(canonicalPythonPath(outbox, repository, "OPS-DIFF", "git.diff"))
		if err != nil {
			t.Fatal(err)
		}
		pythonRecord := lastRecordTest(t, content)
		encoded, err := buildRecord(pythonRecord)
		if err != nil {
			t.Fatal(err)
		}
		assertBytesEqual(t, encoded, operational.Bytes)
	})
}

func TestOperationalRejectedInputDifferentialParity(t *testing.T) {
	repository, environment := newGitRepository(t)
	writeFileTest(t, filepath.Join(repository, "tracked.txt"), []byte("tracked\n"))
	runGitTest(t, repository, nil, "add", "tracked.txt")
	commit := commitTest(t, repository, environment, "root", "", false)
	project := filepath.Base(repository)
	const phase = "OPS-REJECT"
	base := OperationalRequest{
		RequestMetadata: RequestMetadata{Phase: phase, Result: "passed", FinalGate: "gate"},
		Project:         project, SourceName: "ops.txt",
	}
	standalone := []struct {
		name string
		body []byte
		id   string
	}{
		{"wrong-phase", []byte("report_schema: operational-report-v1\nphase: WRONG\noutcome: passed\n"), ""},
		{"wrong-outcome", []byte("report_schema: operational-report-v1\nphase: OPS-REJECT\noutcome: wrong\n"), ""},
		{"truncated", []byte("report_schema: operational-report-v1\nphase: OPS-REJECT\n"), ""},
		{"orphan-relation", []byte("report_schema: operational-report-v1\nphase: OPS-REJECT\noutcome: passed\nprimary_git_report_id: GIT-DIFF-REPORT-" + string(bytes.Repeat([]byte{'a'}, 64)) + "\n"), "GIT-DIFF-REPORT-" + string(bytes.Repeat([]byte{'a'}, 64))},
	}
	for _, testCase := range standalone {
		t.Run(testCase.name, func(t *testing.T) {
			request := base
			request.Source = testCase.body
			request.RelatedGitReportID = testCase.id
			if _, err := Operational(context.Background(), request, nil); err == nil {
				t.Fatal("Go accepted rejected operational input")
			}
			source := writeOperationalSource(t, t.TempDir(), "ops.txt", testCase.body)
			arguments := []string{phase, source, "passed", "gate"}
			if testCase.id != "" {
				arguments = append(arguments, "--related-git-report-id", testCase.id)
			}
			if exit, _ := pythonCommandTest(t, repository, "append-operational-report", filepath.Join(t.TempDir(), "outbox"), arguments...); exit != 1 {
				t.Fatalf("Python rejection exit = %d", exit)
			}
		})
	}

	service, err := New(Options{Repository: repository})
	if err != nil {
		t.Fatal(err)
	}
	show, err := service.Show(context.Background(), ShowRequest{RequestMetadata: base.RequestMetadata, Commit: commit, StatusDoc: "status.md"})
	if err != nil {
		t.Fatal(err)
	}
	associatedBody := []byte("report_schema: operational-report-v1\nphase: OPS-REJECT\noutcome: passed\nprimary_commit: " + commit + "\n")
	wrongID := "GIT-SHOW-REPORT-" + string(bytes.Repeat([]byte{'b'}, 40))
	relationCases := []struct {
		name, relatedID, relatedCommit string
	}{
		{"wrong-report-id", wrongID, commit},
		{"wrong-related-commit", show.Record.ID, string(bytes.Repeat([]byte{'b'}, 40))},
	}
	for _, testCase := range relationCases {
		t.Run(testCase.name, func(t *testing.T) {
			request := base
			request.Source = associatedBody
			request.RelatedGitReportID = testCase.relatedID
			request.RelatedCommit = testCase.relatedCommit
			if _, err := Operational(context.Background(), request, []Record{show.Record}); err == nil {
				t.Fatal("Go accepted rejected Git relation")
			}
			outbox := filepath.Join(t.TempDir(), "outbox")
			if exit, output := pythonCommandTest(t, repository, "git-show-report", outbox, phase, commit, "status.md", "passed", "gate"); exit != 0 {
				t.Fatalf("Python show setup exited %d: %s", exit, output)
			}
			source := writeOperationalSource(t, t.TempDir(), "ops.txt", associatedBody)
			if exit, output := pythonCommandTest(t, repository, "append-operational-report", outbox, phase, source, "passed", "gate", "--related-commit", testCase.relatedCommit, "--related-git-report-id", testCase.relatedID); exit != 2 {
				t.Fatalf("Python relation rejection exit = %d: %s", exit, output)
			}
		})
	}
}

func TestOperationalRejectionsAndRepeatedIdentity(t *testing.T) {
	base := OperationalRequest{
		RequestMetadata: RequestMetadata{Phase: "OPS", Result: "passed", FinalGate: "gate"}, Project: "project", SourceName: "ops.txt",
		Source: []byte("report_schema: operational-report-v1\nphase: WRONG\noutcome: passed\n"),
	}
	if _, err := Operational(context.Background(), base, nil); !errors.Is(err, ErrCompatibility) {
		t.Fatalf("wrong phase error = %v", err)
	}
	base.Source = []byte("report_schema: operational-report-v1\nphase: OPS\noutcome: wrong\n")
	if _, err := Operational(context.Background(), base, nil); !errors.Is(err, ErrCompatibility) {
		t.Fatalf("wrong outcome error = %v", err)
	}
	base.Source = []byte("report_schema: operational-report-v1\nphase: OPS\noutcome: passed\n")
	base.RelatedGitReportID = "GIT-DIFF-REPORT-" + string(bytes.Repeat([]byte{'a'}, 64))
	if _, err := Operational(context.Background(), base, nil); !errors.Is(err, ErrCompatibility) {
		t.Fatalf("missing relation error = %v", err)
	}
	base.RelatedGitReportID = ""
	base.Source = []byte("report_schema: operational-report-v1\nphase: OPS\n")
	if _, err := Operational(context.Background(), base, nil); !errors.Is(err, ErrCompatibility) {
		t.Fatalf("truncated canonical body error = %v", err)
	}

	showCommit := string(bytes.Repeat([]byte{'a'}, 40))
	show := Record{Kind: schema.GitShowRecord, FormatVersion: 2, ID: "GIT-SHOW-REPORT-" + showCommit, Project: "project", Phase: "OPS", Payload: []byte("payload\n")}
	base.Source = []byte("report_schema: operational-report-v1\nphase: OPS\noutcome: passed\nprimary_commit: " + showCommit + "\n")
	base.RelatedGitReportID = "GIT-SHOW-REPORT-" + string(bytes.Repeat([]byte{'b'}, 40))
	base.RelatedCommit = showCommit
	if _, err := Operational(context.Background(), base, []Record{show}); !errors.Is(err, ErrInvalidRequest) {
		t.Fatalf("wrong related report error = %v", err)
	}
	base.RelatedGitReportID = show.ID
	base.RelatedCommit = string(bytes.Repeat([]byte{'b'}, 40))
	if _, err := Operational(context.Background(), base, []Record{show}); !errors.Is(err, ErrInvalidRequest) {
		t.Fatalf("wrong related commit error = %v", err)
	}
	wrongProject := show
	wrongProject.Project = "other-project"
	base.RelatedCommit = showCommit
	if _, err := Operational(context.Background(), base, []Record{wrongProject}); !errors.Is(err, ErrCompatibility) {
		t.Fatalf("wrong existing project error = %v", err)
	}

	base.RelatedGitReportID = ""
	base.RelatedCommit = ""
	base.Source = []byte("report_schema: operational-report-v1\nphase: OPS\noutcome: passed\n")
	result, err := Operational(context.Background(), base, nil)
	if err != nil {
		t.Fatal(err)
	}
	outbox := filepath.Join(t.TempDir(), "outbox")
	request := AppendRequest{OutboxRoot: outbox, Project: "project", Phase: "OPS", Record: result.Record}
	if _, err := Append(context.Background(), request); err != nil {
		t.Fatal(err)
	}
	if _, err := Append(context.Background(), request); err != nil {
		t.Fatal(err)
	}
	content, err := os.ReadFile(filepath.Join(outbox, "project", "OPS", "OPS.ops.report.txt"))
	if err != nil {
		t.Fatal(err)
	}
	records, err := ParseRecords(content)
	if err != nil {
		t.Fatal(err)
	}
	if len(records) != 2 || records[0].ID != records[1].ID || records[0].Kind != schema.OperationalRecord {
		t.Fatalf("repeated records = %#v", records)
	}
}
