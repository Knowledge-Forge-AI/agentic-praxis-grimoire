package report

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"testing"
)

func TestShowDifferentialParity(t *testing.T) {
	repository, environment := newGitRepository(t)
	writeFileTest(t, filepath.Join(repository, "root.txt"), []byte("root\n"))
	runGitTest(t, repository, nil, "add", "root.txt")
	root := commitTest(t, repository, environment, "root subject", "root body", false)

	writeFileTest(t, filepath.Join(repository, "root.txt"), []byte("root\nordinary\n"))
	runGitTest(t, repository, nil, "add", "root.txt")
	ordinary := commitTest(t, repository, environment, "ordinary", "", false)
	empty := commitTest(t, repository, environment, "empty", "", true)

	runGitTest(t, repository, nil, "mv", "root.txt", "renamed.txt")
	rename := commitTest(t, repository, environment, "rename", "", false)

	writeFileTest(t, filepath.Join(repository, "binary.bin"), []byte{0, 1, 2, 255})
	runGitTest(t, repository, nil, "add", "binary.bin")
	binary := commitTest(t, repository, environment, "binary", "", false)

	writeFileTest(t, filepath.Join(repository, "unusual name\t.txt"), []byte("unusual\n"))
	runGitTest(t, repository, nil, "add", "--", "unusual name\t.txt")
	unusualMessage := commitTest(t, repository, environment, "unusual", "full message body\nsecond line", false)

	runGitTest(t, repository, nil, "checkout", "-qb", "side", ordinary)
	writeFileTest(t, filepath.Join(repository, "side.txt"), []byte("side\n"))
	runGitTest(t, repository, nil, "add", "side.txt")
	_ = commitTest(t, repository, environment, "side", "", false)
	runGitTest(t, repository, nil, "checkout", "-q", "main")
	runGitTest(t, repository, environment, "merge", "--no-ff", "-qm", "merge", "side")
	merge := string(runGitTest(t, repository, nil, "rev-parse", "HEAD"))
	merge = merge[:len(merge)-1]

	service, err := New(Options{Repository: repository})
	if err != nil {
		t.Fatal(err)
	}
	cases := []struct {
		phase, commit, status string
	}{
		{"ROOT", root, ""},
		{"ORDINARY", ordinary, "status.md"},
		{"EMPTY", empty, "status.md"},
		{"RENAME", rename, "status.md"},
		{"BINARY", binary, "status.md"},
		{"UNUSUAL-MESSAGE", unusualMessage, "status.md"},
		{"MERGE", merge, "status.md"},
	}
	for _, testCase := range cases {
		t.Run(testCase.phase, func(t *testing.T) {
			result, err := service.Show(context.Background(), ShowRequest{
				RequestMetadata: RequestMetadata{Phase: testCase.phase, Result: "passed", FinalGate: "gate"},
				Commit:          testCase.commit, StatusDoc: testCase.status,
			})
			if err != nil {
				t.Fatal(err)
			}
			outbox := filepath.Join(t.TempDir(), "outbox")
			exit, output := pythonCommandTest(t, repository, "git-show-report", outbox, testCase.phase, testCase.commit, testCase.status, "passed", "gate")
			if exit != 0 {
				t.Fatalf("Python show oracle exited %d: %s", exit, output)
			}
			pythonBytes, err := os.ReadFile(canonicalPythonPath(outbox, repository, testCase.phase, "git.show"))
			if err != nil {
				t.Fatal(err)
			}
			assertBytesEqual(t, pythonBytes, result.Bytes)
			result.Bytes[0] ^= 1
			if result.Record.Payload[0] == result.Bytes[0] {
				t.Fatal("Result.Bytes aliases Record.Payload")
			}
		})
	}
}

func TestShowRejectsInvalidAndUnresolvableCommits(t *testing.T) {
	repository, environment := newGitRepository(t)
	writeFileTest(t, filepath.Join(repository, "tracked.txt"), []byte("tracked\n"))
	runGitTest(t, repository, nil, "add", "tracked.txt")
	_ = commitTest(t, repository, environment, "root", "", false)
	service, err := New(Options{Repository: repository})
	if err != nil {
		t.Fatal(err)
	}
	_, err = service.Show(context.Background(), ShowRequest{RequestMetadata: RequestMetadata{Phase: "INVALID", Result: "failed", FinalGate: "gate"}, Commit: "not-hex", StatusDoc: "status.md"})
	if !errors.Is(err, ErrInvalidRequest) {
		t.Fatalf("invalid commit error = %v", err)
	}
	_, err = service.Show(context.Background(), ShowRequest{RequestMetadata: RequestMetadata{Phase: "MISSING", Result: "failed", FinalGate: "gate"}, Commit: "0000000", StatusDoc: "status.md"})
	if !errors.Is(err, ErrRepository) {
		t.Fatalf("missing commit error = %v", err)
	}
	outbox := filepath.Join(t.TempDir(), "outbox")
	if exit, _ := pythonCommandTest(t, repository, "git-show-report", outbox, "INVALID", "not-hex", "status.md", "failed", "gate"); exit != 2 {
		t.Fatalf("Python invalid syntax exit = %d", exit)
	}
	if exit, _ := pythonCommandTest(t, repository, "git-show-report", outbox, "MISSING", "0000000", "status.md", "failed", "gate"); exit != 1 {
		t.Fatalf("Python missing commit exit = %d", exit)
	}
}
