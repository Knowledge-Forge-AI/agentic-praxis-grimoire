package atomicfile

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"strconv"
	"testing"
	"time"
)

func prepareTestPaths(t *testing.T) Paths {
	t.Helper()
	paths, err := Prepare(filepath.Join(t.TempDir(), "outbox"), "project", "PHASE")
	if err != nil {
		t.Fatal(err)
	}
	return paths
}

func writePrivateTest(t *testing.T, path string, content []byte) {
	t.Helper()
	if err := os.WriteFile(path, content, 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.Chmod(path, 0o600); err != nil {
		t.Fatal(err)
	}
}

func writeTransactionTest(t *testing.T, paths Paths, target string, stale ...string) {
	t.Helper()
	content := "agent-report-transaction-v1\nphase: " + paths.Phase + "\ntarget: " + target + "\nstale: "
	for index, name := range stale {
		if index != 0 {
			content += ","
		}
		content += name
	}
	content += "\ntoken: test\n"
	writePrivateTest(t, paths.Transaction, []byte(content))
}

func TestRecoverHandlesPreAndPostPublicationTransactions(t *testing.T) {
	allowed := []string{"PHASE.git.show.report.txt", "PHASE.git.diff.report.txt", "PHASE.ops.report.txt"}

	t.Run("pre-publication", func(t *testing.T) {
		paths := prepareTestPaths(t)
		stale := filepath.Join(paths.Directory, allowed[2])
		writePrivateTest(t, stale, []byte("stale"))
		writeTransactionTest(t, paths, allowed[0], allowed[1], allowed[2])
		recovered, err := Recover(context.Background(), paths, allowed)
		if err != nil || !recovered {
			t.Fatalf("recover = %v, %v", recovered, err)
		}
		if _, err := os.Stat(paths.Transaction); !os.IsNotExist(err) {
			t.Fatal("transaction marker remains")
		}
		if _, err := os.Stat(stale); err != nil {
			t.Fatal("pre-publication recovery removed the prior primary")
		}
	})

	t.Run("post-publication", func(t *testing.T) {
		paths := prepareTestPaths(t)
		target := filepath.Join(paths.Directory, allowed[0])
		stale := filepath.Join(paths.Directory, allowed[2])
		writePrivateTest(t, target, []byte("target"))
		writePrivateTest(t, stale, []byte("stale"))
		writeTransactionTest(t, paths, allowed[0], allowed[1], allowed[2])
		recovered, err := Recover(context.Background(), paths, allowed)
		if err != nil || !recovered {
			t.Fatalf("recover = %v, %v", recovered, err)
		}
		if _, err := os.Stat(stale); !os.IsNotExist(err) {
			t.Fatal("post-publication recovery retained stale primary")
		}
		if content, _, err := ReadPrivate(target); err != nil || string(content) != "target" {
			t.Fatalf("target after recovery = %q, %v", content, err)
		}
	})
}

func TestLockContentionCancellationAndStaleRecovery(t *testing.T) {
	t.Run("live-owner", func(t *testing.T) {
		paths := prepareTestPaths(t)
		if err := os.Mkdir(paths.Lock, 0o700); err != nil {
			t.Fatal(err)
		}
		writePrivateTest(t, filepath.Join(paths.Lock, "owner"), []byte(strconv.Itoa(os.Getpid())+"-live-PHASE\n"))
		ctx, cancel := context.WithTimeout(context.Background(), 40*time.Millisecond)
		defer cancel()
		err := WithLock(ctx, paths, func() error { return nil })
		if !errors.Is(err, context.DeadlineExceeded) {
			t.Fatalf("live lock error = %v", err)
		}
		if _, err := os.Stat(paths.Lock); err != nil {
			t.Fatal("foreign live lock was removed")
		}
	})

	t.Run("dead-owner", func(t *testing.T) {
		paths := prepareTestPaths(t)
		if err := os.Mkdir(paths.Lock, 0o700); err != nil {
			t.Fatal(err)
		}
		writePrivateTest(t, filepath.Join(paths.Lock, "owner"), []byte("99999999-dead-PHASE\n"))
		called := false
		if err := WithLock(context.Background(), paths, func() error { called = true; return nil }); err != nil {
			t.Fatal(err)
		}
		if !called {
			t.Fatal("action did not run after stale-lock recovery")
		}
		if _, err := os.Stat(paths.Lock); !os.IsNotExist(err) {
			t.Fatal("owned lock remains after release")
		}
	})
}

func TestPrivateReadRejectsLinksAndUnsafeModes(t *testing.T) {
	paths := prepareTestPaths(t)
	target := filepath.Join(paths.Directory, "target")
	writePrivateTest(t, target, []byte("private"))
	linked := filepath.Join(paths.Directory, "linked")
	if err := os.Link(target, linked); err != nil {
		t.Fatal(err)
	}
	if _, _, err := ReadPrivate(target); !errors.Is(err, ErrUnsafe) {
		t.Fatalf("hard-linked file error = %v", err)
	}
	if err := os.Remove(linked); err != nil {
		t.Fatal(err)
	}
	if err := os.Chmod(target, 0o644); err != nil {
		t.Fatal(err)
	}
	if _, _, err := ReadPrivate(target); !errors.Is(err, ErrUnsafe) {
		t.Fatalf("public-mode file error = %v", err)
	}
	symlink := filepath.Join(paths.Directory, "symlink")
	if err := os.Symlink(target, symlink); err != nil {
		t.Fatal(err)
	}
	if _, _, err := ReadPrivate(symlink); !errors.Is(err, ErrUnsafe) {
		t.Fatalf("symlink error = %v", err)
	}
}
