package report

import (
	"bytes"
	"context"
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"testing"
	"time"
)

func initializeDiffRepository(t *testing.T) (string, []string) {
	t.Helper()
	repository, environment := newGitRepository(t)
	writeFileTest(t, filepath.Join(repository, "tracked.txt"), []byte("tracked\n"))
	writeFileTest(t, filepath.Join(repository, "binary.bin"), []byte{0, 1, 2})
	runGitTest(t, repository, nil, "add", "tracked.txt", "binary.bin")
	_ = commitTest(t, repository, environment, "root", "", false)
	return repository, environment
}

func TestDiffDifferentialParityAndNoMutation(t *testing.T) {
	cases := []struct {
		name  string
		setup func(*testing.T, string)
	}{
		{"staged", func(t *testing.T, repository string) {
			writeFileTest(t, filepath.Join(repository, "staged.txt"), []byte("staged\n"))
			runGitTest(t, repository, nil, "add", "staged.txt")
		}},
		{"unstaged", func(t *testing.T, repository string) {
			writeFileTest(t, filepath.Join(repository, "tracked.txt"), []byte("tracked\nunstaged\n"))
		}},
		{"mixed", func(t *testing.T, repository string) {
			writeFileTest(t, filepath.Join(repository, "tracked.txt"), []byte("tracked\nstaged\n"))
			runGitTest(t, repository, nil, "add", "tracked.txt")
			writeFileTest(t, filepath.Join(repository, "tracked.txt"), []byte("tracked\nstaged\nunstaged\n"))
		}},
		{"untracked", func(t *testing.T, repository string) {
			writeFileTest(t, filepath.Join(repository, "untracked.txt"), []byte("untracked\n"))
		}},
		{"intent-to-add", func(t *testing.T, repository string) {
			writeFileTest(t, filepath.Join(repository, "intent.txt"), []byte("intent\n"))
			runGitTest(t, repository, nil, "add", "-N", "--", "intent.txt")
		}},
		{"rename", func(t *testing.T, repository string) {
			runGitTest(t, repository, nil, "mv", "tracked.txt", "renamed.txt")
		}},
		{"binary", func(t *testing.T, repository string) {
			writeFileTest(t, filepath.Join(repository, "binary.bin"), []byte{0, 1, 2, 3, 255})
		}},
	}
	for _, testCase := range cases {
		t.Run(testCase.name, func(t *testing.T) {
			repository, _ := initializeDiffRepository(t)
			testCase.setup(t, repository)
			service, err := New(Options{Repository: repository})
			if err != nil {
				t.Fatal(err)
			}
			indexPath := string(runGitTest(t, repository, nil, "rev-parse", "--path-format=absolute", "--git-path", "index"))
			indexPath = indexPath[:len(indexPath)-1]
			indexBefore, err := os.ReadFile(indexPath)
			if err != nil {
				t.Fatal(err)
			}
			statusBefore := runGitTest(t, repository, nil, "status", "--porcelain=v2", "-z", "--untracked-files=all")
			phase := "DIFF-" + testCase.name
			result, err := service.Diff(context.Background(), DiffRequest{RequestMetadata: RequestMetadata{Phase: phase, Result: "passed", FinalGate: "gate"}, StatusDoc: "status.md"})
			if err != nil {
				t.Fatal(err)
			}
			outbox := filepath.Join(t.TempDir(), "outbox")
			exit, output := pythonCommandTest(t, repository, "git-diff-report", outbox, phase, "passed", "gate", "--status-doc", "status.md")
			if exit != 0 {
				t.Fatalf("Python diff oracle exited %d: %s", exit, output)
			}
			pythonBytes, err := os.ReadFile(canonicalPythonPath(outbox, repository, phase, "git.diff"))
			if err != nil {
				t.Fatal(err)
			}
			assertBytesEqual(t, pythonBytes, result.Bytes)
			indexAfter, err := os.ReadFile(indexPath)
			if err != nil {
				t.Fatal(err)
			}
			statusAfter := runGitTest(t, repository, nil, "status", "--porcelain=v2", "-z", "--untracked-files=all")
			if !bytes.Equal(indexBefore, indexAfter) || !bytes.Equal(statusBefore, statusAfter) {
				t.Fatal("report collection mutated the real index or worktree status")
			}
		})
	}
}

func TestDiffRejectedStateParity(t *testing.T) {
	t.Run("empty", func(t *testing.T) {
		repository, _ := initializeDiffRepository(t)
		service, err := New(Options{Repository: repository})
		if err != nil {
			t.Fatal(err)
		}
		_, err = service.Diff(context.Background(), DiffRequest{RequestMetadata: RequestMetadata{Phase: "EMPTY", Result: "failed", FinalGate: "gate"}})
		if !errors.Is(err, ErrInvalidRequest) {
			t.Fatalf("empty diff error = %v", err)
		}
		if exit, _ := pythonCommandTest(t, repository, "git-diff-report", filepath.Join(t.TempDir(), "outbox"), "EMPTY", "failed", "gate"); exit != 1 {
			t.Fatalf("Python empty diff exit = %d", exit)
		}
	})

	t.Run("inherited-index", func(t *testing.T) {
		repository, _ := initializeDiffRepository(t)
		writeFileTest(t, filepath.Join(repository, "tracked.txt"), []byte("changed\n"))
		service, err := New(Options{Repository: repository})
		if err != nil {
			t.Fatal(err)
		}
		t.Setenv("GIT_INDEX_FILE", filepath.Join(t.TempDir(), "custom-index"))
		_, err = service.Diff(context.Background(), DiffRequest{RequestMetadata: RequestMetadata{Phase: "CUSTOM", Result: "failed", FinalGate: "gate"}})
		if !errors.Is(err, ErrUnsupported) {
			t.Fatalf("custom index error = %v", err)
		}
		if exit, _ := pythonCommandTest(t, repository, "git-diff-report", filepath.Join(t.TempDir(), "outbox"), "CUSTOM", "failed", "gate"); exit != 1 {
			t.Fatalf("Python custom-index exit = %d", exit)
		}
	})

	t.Run("unmerged", func(t *testing.T) {
		repository, environment := initializeDiffRepository(t)
		runGitTest(t, repository, nil, "checkout", "-qb", "side")
		writeFileTest(t, filepath.Join(repository, "tracked.txt"), []byte("side\n"))
		runGitTest(t, repository, nil, "add", "tracked.txt")
		_ = commitTest(t, repository, environment, "side", "", false)
		runGitTest(t, repository, nil, "checkout", "-q", "main")
		writeFileTest(t, filepath.Join(repository, "tracked.txt"), []byte("main\n"))
		runGitTest(t, repository, nil, "add", "tracked.txt")
		_ = commitTest(t, repository, environment, "main", "", false)
		command := execCommand("git", "-C", repository, "merge", "side")
		command.Env = environment
		if err := command.Run(); err == nil {
			t.Fatal("expected merge conflict")
		}
		service, err := New(Options{Repository: repository})
		if err != nil {
			t.Fatal(err)
		}
		_, err = service.Diff(context.Background(), DiffRequest{RequestMetadata: RequestMetadata{Phase: "UNMERGED", Result: "failed", FinalGate: "gate"}})
		if !errors.Is(err, ErrUnsupported) {
			t.Fatalf("unmerged error = %v", err)
		}
		if exit, _ := pythonCommandTest(t, repository, "git-diff-report", filepath.Join(t.TempDir(), "outbox"), "UNMERGED", "failed", "gate"); exit != 1 {
			t.Fatalf("Python unmerged exit = %d", exit)
		}
	})
}

func TestDiffDetectsDriftAndCancellation(t *testing.T) {
	driftCases := []struct {
		name   string
		mutate func(*testing.T, string, []string)
	}{
		{"worktree", func(t *testing.T, repository string, _ []string) {
			writeFileTest(t, filepath.Join(repository, "tracked.txt"), []byte("after\n"))
		}},
		{"index", func(t *testing.T, repository string, _ []string) {
			writeFileTest(t, filepath.Join(repository, "tracked.txt"), []byte("staged drift\n"))
			runGitTest(t, repository, nil, "add", "tracked.txt")
		}},
		{"head", func(t *testing.T, repository string, environment []string) {
			writeFileTest(t, filepath.Join(repository, "tracked.txt"), []byte("committed drift\n"))
			runGitTest(t, repository, nil, "add", "tracked.txt")
			_ = commitTest(t, repository, environment, "drift", "", false)
		}},
	}
	for _, testCase := range driftCases {
		t.Run(testCase.name, func(t *testing.T) {
			repository, environment := initializeDiffRepository(t)
			writeFileTest(t, filepath.Join(repository, "tracked.txt"), []byte("before\n"))
			service, err := New(Options{Repository: repository})
			if err != nil {
				t.Fatal(err)
			}
			signals, errorsChannel := startPausedDiff(t, service, "DRIFT-"+testCase.name, context.Background())
			testCase.mutate(t, repository, environment)
			writeFileTest(t, filepath.Join(signals, "continue"), []byte{})
			if err := <-errorsChannel; !errors.Is(err, ErrDrift) {
				t.Fatalf("drift error = %v", err)
			}
		})
	}

	t.Run("active-cancellation", func(t *testing.T) {
		repository, _ := initializeDiffRepository(t)
		writeFileTest(t, filepath.Join(repository, "tracked.txt"), []byte("before\n"))
		service, err := New(Options{Repository: repository})
		if err != nil {
			t.Fatal(err)
		}
		ctx, cancel := context.WithCancel(context.Background())
		_, errorsChannel := startPausedDiff(t, service, "CANCEL", ctx)
		cancel()
		if err := <-errorsChannel; !errors.Is(err, context.Canceled) {
			t.Fatalf("cancellation error = %v", err)
		}
	})
}

func startPausedDiff(t *testing.T, service *Service, phase string, ctx context.Context) (string, <-chan error) {
	t.Helper()
	signals := t.TempDir()
	t.Setenv("APG_REPORT_GO_TESTING", "1")
	t.Setenv("APG_REPORT_GO_TEST_PAUSE_STEP", "before-post-drift-check")
	t.Setenv("APG_REPORT_GO_TEST_SIGNAL_DIR", signals)
	errorsChannel := make(chan error, 1)
	go func() {
		_, callErr := service.Diff(ctx, DiffRequest{RequestMetadata: RequestMetadata{Phase: phase, Result: "failed", FinalGate: "gate"}})
		errorsChannel <- callErr
	}()
	deadline := time.Now().Add(10 * time.Second)
	for {
		if _, err := os.Stat(filepath.Join(signals, "ready")); err == nil {
			return signals, errorsChannel
		}
		if time.Now().After(deadline) {
			t.Fatal("diff drift hook did not become ready")
		}
		time.Sleep(10 * time.Millisecond)
	}
}

// execCommand is a narrow seam so the expected-failure merge setup does not
// weaken runGitTest's fail-fast behavior.
var execCommand = exec.Command
