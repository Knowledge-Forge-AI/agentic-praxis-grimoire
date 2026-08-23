package report

import (
	"bytes"
	"context"
	"errors"
	"os"
	"path/filepath"
	"testing"
)

func TestPublicationDifferentialParity(t *testing.T) {
	t.Run("show-operational-append", func(t *testing.T) {
		repository, environment := newGitRepository(t)
		writeFileTest(t, filepath.Join(repository, "tracked.txt"), []byte("tracked\n"))
		runGitTest(t, repository, nil, "add", "tracked.txt")
		commit := commitTest(t, repository, environment, "root", "", false)
		service, err := New(Options{Repository: repository})
		if err != nil {
			t.Fatal(err)
		}
		show, err := service.Show(context.Background(), ShowRequest{RequestMetadata: RequestMetadata{Phase: "PUB-SHOW", Result: "passed", FinalGate: "gate"}, Commit: commit, StatusDoc: "status.md"})
		if err != nil {
			t.Fatal(err)
		}
		body := []byte("report_schema: operational-report-v1\nphase: PUB-SHOW\noutcome: passed\nprimary_commit: " + commit + "\n")
		ops, err := Operational(context.Background(), OperationalRequest{
			RequestMetadata: RequestMetadata{Phase: "PUB-SHOW", Result: "passed", FinalGate: "gate"},
			Project:         filepath.Base(repository), SourceName: "ops.txt", Source: body, RelatedCommit: commit, RelatedGitReportID: show.Record.ID,
		}, []Record{show.Record})
		if err != nil {
			t.Fatal(err)
		}
		goOutbox := filepath.Join(t.TempDir(), "go-outbox")
		for _, record := range []Record{show.Record, ops.Record} {
			if _, err := Append(context.Background(), AppendRequest{OutboxRoot: goOutbox, Project: filepath.Base(repository), Phase: "PUB-SHOW", Record: record}); err != nil {
				t.Fatal(err)
			}
		}
		pythonOutbox := filepath.Join(t.TempDir(), "python-outbox")
		if exit, output := pythonCommandTest(t, repository, "git-show-report", pythonOutbox, "PUB-SHOW", commit, "status.md", "passed", "gate"); exit != 0 {
			t.Fatalf("Python show exited %d: %s", exit, output)
		}
		source := writeOperationalSource(t, t.TempDir(), "ops.txt", body)
		if exit, output := pythonCommandTest(t, repository, "append-operational-report", pythonOutbox, "PUB-SHOW", source, "passed", "gate", "--related-commit", commit, "--related-git-report-id", show.Record.ID); exit != 0 {
			t.Fatalf("Python operational append exited %d: %s", exit, output)
		}
		goBytes, err := os.ReadFile(canonicalPythonPath(goOutbox, repository, "PUB-SHOW", "git.show"))
		if err != nil {
			t.Fatal(err)
		}
		pythonBytes, err := os.ReadFile(canonicalPythonPath(pythonOutbox, repository, "PUB-SHOW", "git.show"))
		if err != nil {
			t.Fatal(err)
		}
		assertBytesEqual(t, pythonBytes, goBytes)
	})

	t.Run("show-diff-supersession", func(t *testing.T) {
		repository, environment := newGitRepository(t)
		writeFileTest(t, filepath.Join(repository, "tracked.txt"), []byte("tracked\n"))
		runGitTest(t, repository, nil, "add", "tracked.txt")
		commit := commitTest(t, repository, environment, "root", "", false)
		writeFileTest(t, filepath.Join(repository, "tracked.txt"), []byte("changed and longer\n"))
		service, err := New(Options{Repository: repository})
		if err != nil {
			t.Fatal(err)
		}
		show, err := service.Show(context.Background(), ShowRequest{RequestMetadata: RequestMetadata{Phase: "PUB-SWAP", Result: "passed", FinalGate: "gate"}, Commit: commit, StatusDoc: "status.md"})
		if err != nil {
			t.Fatal(err)
		}
		diff, err := service.Diff(context.Background(), DiffRequest{RequestMetadata: RequestMetadata{Phase: "PUB-SWAP", Result: "passed", FinalGate: "gate"}})
		if err != nil {
			t.Fatal(err)
		}
		goOutbox := filepath.Join(t.TempDir(), "go-outbox")
		if _, err := Append(context.Background(), AppendRequest{OutboxRoot: goOutbox, Project: filepath.Base(repository), Phase: "PUB-SWAP", Record: show.Record}); err != nil {
			t.Fatal(err)
		}
		publication, err := Append(context.Background(), AppendRequest{OutboxRoot: goOutbox, Project: filepath.Base(repository), Phase: "PUB-SWAP", Record: diff.Record})
		if err != nil {
			t.Fatal(err)
		}
		if publication.Disposition != PublishedSuperseding {
			t.Fatalf("disposition = %s", publication.Disposition)
		}
		pythonOutbox := filepath.Join(t.TempDir(), "python-outbox")
		if exit, output := pythonCommandTest(t, repository, "git-show-report", pythonOutbox, "PUB-SWAP", commit, "status.md", "passed", "gate"); exit != 0 {
			t.Fatalf("Python show exited %d: %s", exit, output)
		}
		if exit, output := pythonCommandTest(t, repository, "git-diff-report", pythonOutbox, "PUB-SWAP", "passed", "gate"); exit != 0 {
			t.Fatalf("Python diff exited %d: %s", exit, output)
		}
		goBytes, err := os.ReadFile(canonicalPythonPath(goOutbox, repository, "PUB-SWAP", "git.diff"))
		if err != nil {
			t.Fatal(err)
		}
		pythonBytes, err := os.ReadFile(canonicalPythonPath(pythonOutbox, repository, "PUB-SWAP", "git.diff"))
		if err != nil {
			t.Fatal(err)
		}
		assertBytesEqual(t, pythonBytes, goBytes)
		if _, err := os.Stat(canonicalPythonPath(goOutbox, repository, "PUB-SWAP", "git.show")); !os.IsNotExist(err) {
			t.Fatal("stale show primary remains")
		}
	})

	t.Run("ops-to-show-supersession", func(t *testing.T) {
		repository, environment := newGitRepository(t)
		writeFileTest(t, filepath.Join(repository, "tracked.txt"), []byte("tracked\n"))
		runGitTest(t, repository, nil, "add", "tracked.txt")
		commit := commitTest(t, repository, environment, "root", "", false)
		service, err := New(Options{Repository: repository})
		if err != nil {
			t.Fatal(err)
		}
		show, err := service.Show(context.Background(), ShowRequest{RequestMetadata: RequestMetadata{Phase: "PUB-ABSORB", Result: "passed", FinalGate: "gate"}, Commit: commit, StatusDoc: "status.md"})
		if err != nil {
			t.Fatal(err)
		}
		body := []byte("report_schema: operational-report-v1\nphase: PUB-ABSORB\noutcome: passed\n")
		ops, err := Operational(context.Background(), OperationalRequest{RequestMetadata: RequestMetadata{Phase: "PUB-ABSORB", Result: "passed", FinalGate: "gate"}, Project: filepath.Base(repository), SourceName: "ops.txt", Source: body}, nil)
		if err != nil {
			t.Fatal(err)
		}
		goOutbox := filepath.Join(t.TempDir(), "go-outbox")
		if _, err := Append(context.Background(), AppendRequest{OutboxRoot: goOutbox, Project: filepath.Base(repository), Phase: "PUB-ABSORB", Record: ops.Record}); err != nil {
			t.Fatal(err)
		}
		publication, err := Append(context.Background(), AppendRequest{OutboxRoot: goOutbox, Project: filepath.Base(repository), Phase: "PUB-ABSORB", Record: show.Record})
		if err != nil {
			t.Fatal(err)
		}
		if publication.Disposition != PublishedSuperseding {
			t.Fatalf("disposition = %s", publication.Disposition)
		}
		pythonOutbox := filepath.Join(t.TempDir(), "python-outbox")
		source := writeOperationalSource(t, t.TempDir(), "ops.txt", body)
		if exit, output := pythonCommandTest(t, repository, "append-operational-report", pythonOutbox, "PUB-ABSORB", source, "passed", "gate"); exit != 0 {
			t.Fatalf("Python ops exited %d: %s", exit, output)
		}
		if exit, output := pythonCommandTest(t, repository, "git-show-report", pythonOutbox, "PUB-ABSORB", commit, "status.md", "passed", "gate"); exit != 0 {
			t.Fatalf("Python show exited %d: %s", exit, output)
		}
		goBytes, err := os.ReadFile(canonicalPythonPath(goOutbox, repository, "PUB-ABSORB", "git.show"))
		if err != nil {
			t.Fatal(err)
		}
		pythonBytes, err := os.ReadFile(canonicalPythonPath(pythonOutbox, repository, "PUB-ABSORB", "git.show"))
		if err != nil {
			t.Fatal(err)
		}
		assertBytesEqual(t, pythonBytes, goBytes)
	})
}

func TestPublicationModesAndPathSafety(t *testing.T) {
	result, err := Operational(context.Background(), OperationalRequest{
		RequestMetadata: RequestMetadata{Phase: "MODES", Result: "passed", FinalGate: "gate"},
		Project:         "project", SourceName: "ops.txt", Source: []byte("evidence\n"),
	}, nil)
	if err != nil {
		t.Fatal(err)
	}
	outbox := filepath.Join(t.TempDir(), "outbox")
	publication, err := Append(context.Background(), AppendRequest{OutboxRoot: outbox, Project: "project", Phase: "MODES", Record: result.Record})
	if err != nil {
		t.Fatal(err)
	}
	for _, path := range []string{outbox, filepath.Join(outbox, "project"), filepath.Join(outbox, "project", "MODES")} {
		metadata, err := os.Stat(path)
		if err != nil || metadata.Mode().Perm() != 0o700 {
			t.Fatalf("directory %s mode = %v err=%v", filepath.Base(path), metadata.Mode().Perm(), err)
		}
	}
	metadata, err := os.Stat(publication.FinalPath)
	if err != nil || metadata.Mode().Perm() != 0o600 {
		t.Fatalf("primary mode = %v err=%v", metadata.Mode().Perm(), err)
	}
	unsafe := filepath.Join(t.TempDir(), "unsafe")
	target := filepath.Join(t.TempDir(), "target")
	if err := os.Mkdir(target, 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(target, unsafe); err != nil {
		t.Fatal(err)
	}
	if _, err := Append(context.Background(), AppendRequest{OutboxRoot: unsafe, Project: "project", Phase: "MODES", Record: result.Record}); err == nil {
		t.Fatal("symlinked outbox root was accepted")
	}
}

func TestPublicationRejectionsDoNotPartiallyMutate(t *testing.T) {
	result, err := Operational(context.Background(), OperationalRequest{
		RequestMetadata: RequestMetadata{Phase: "NO-MUTATION", Result: "passed", FinalGate: "gate"},
		Project:         "project", SourceName: "ops.txt", Source: []byte("evidence\n"),
	}, nil)
	if err != nil {
		t.Fatal(err)
	}
	t.Run("invalid-request", func(t *testing.T) {
		outbox := filepath.Join(t.TempDir(), "outbox")
		request := AppendRequest{OutboxRoot: outbox, Project: "other", Phase: "NO-MUTATION", Record: result.Record}
		if _, err := Append(context.Background(), request); !errors.Is(err, ErrInvalidRequest) {
			t.Fatalf("append error = %v", err)
		}
		if _, err := os.Stat(outbox); !os.IsNotExist(err) {
			t.Fatal("invalid append created outbox state")
		}
	})
	t.Run("canceled", func(t *testing.T) {
		outbox := filepath.Join(t.TempDir(), "outbox")
		ctx, cancel := context.WithCancel(context.Background())
		cancel()
		request := AppendRequest{OutboxRoot: outbox, Project: "project", Phase: "NO-MUTATION", Record: result.Record}
		if _, err := Append(ctx, request); !errors.Is(err, context.Canceled) {
			t.Fatalf("append error = %v", err)
		}
		if _, err := os.Stat(outbox); !os.IsNotExist(err) {
			t.Fatal("canceled append created outbox state")
		}
	})
	t.Run("multiple-primary-conflict", func(t *testing.T) {
		outbox := filepath.Join(t.TempDir(), "outbox")
		request := AppendRequest{OutboxRoot: outbox, Project: "project", Phase: "NO-MUTATION", Record: result.Record}
		publication, err := Append(context.Background(), request)
		if err != nil {
			t.Fatal(err)
		}
		before, err := os.ReadFile(publication.FinalPath)
		if err != nil {
			t.Fatal(err)
		}
		conflict := filepath.Join(filepath.Dir(publication.FinalPath), "NO-MUTATION.git.show.report.txt")
		if err := os.WriteFile(conflict, before, 0o600); err != nil {
			t.Fatal(err)
		}
		if _, err := Append(context.Background(), request); !errors.Is(err, ErrPublication) {
			t.Fatalf("append conflict error = %v", err)
		}
		after, err := os.ReadFile(publication.FinalPath)
		if err != nil || !bytes.Equal(before, after) {
			t.Fatalf("existing primary changed: err=%v", err)
		}
		conflictAfter, err := os.ReadFile(conflict)
		if err != nil || !bytes.Equal(before, conflictAfter) {
			t.Fatalf("conflicting primary changed: err=%v", err)
		}
	})
}
