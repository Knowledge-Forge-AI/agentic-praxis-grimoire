package hotspot

import (
	"context"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func createSafetyGitRepo(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()
	resolved, err := filepath.EvalSymlinks(dir)
	if err != nil {
		t.Fatal(err)
	}
	gitSafetyExec(t, resolved, "init")
	gitSafetyExec(t, resolved, "config", "user.name", "APG Safety Test")
	gitSafetyExec(t, resolved, "config", "user.email", "apg-safety@example.com")
	gitSafetyExec(t, resolved, "config", "commit.gpgsign", "false")
	return resolved
}

func gitSafetyExec(t *testing.T, dir string, args ...string) string {
	t.Helper()
	cmd := exec.Command("git", args...)
	cmd.Dir = dir
	cmd.Env = append(os.Environ(),
		"GIT_AUTHOR_NAME=APG Safety Test",
		"GIT_AUTHOR_EMAIL=apg-safety@example.com",
		"GIT_COMMITTER_NAME=APG Safety Test",
		"GIT_COMMITTER_EMAIL=apg-safety@example.com",
		"GIT_CONFIG_NOSYSTEM=1",
	)
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("git %v in %s failed: %v\n%s", args, dir, err, out)
	}
	return strings.TrimSpace(string(out))
}

func TestGitSafetyPreflightFailClosed(t *testing.T) {
	ctx := context.Background()

	tests := []struct {
		name        string
		setup       func(t *testing.T, root string) string
		errContains string
	}{
		{
			name: "normal repository succeeds",
			setup: func(t *testing.T, root string) string {
				if err := os.WriteFile(filepath.Join(root, "init.txt"), []byte("init"), 0o600); err != nil {
					t.Fatal(err)
				}
				gitSafetyExec(t, root, "add", ".")
				gitSafetyExec(t, root, "commit", "-m", "init")
				return root
			},
			errContains: "",
		},
		{
			name: "bare repository refused",
			setup: func(t *testing.T, root string) string {
				bareDir := filepath.Join(t.TempDir(), "bare.git")
				gitSafetyExec(t, t.TempDir(), "clone", "--bare", root, bareDir)
				resolved, err := filepath.EvalSymlinks(bareDir)
				if err != nil {
					t.Fatal(err)
				}
				return resolved
			},
			errContains: "bare repositories are not supported",
		},
		{
			name: "subtree subdirectory refused",
			setup: func(t *testing.T, root string) string {
				sub := filepath.Join(root, "subdir")
				if err := os.Mkdir(sub, 0o700); err != nil {
					t.Fatal(err)
				}
				return sub
			},
			errContains: "root must equal physical Git toplevel; subtrees are not supported",
		},
		{
			name: "shallow repository via marker file refused",
			setup: func(t *testing.T, root string) string {
				if err := os.WriteFile(filepath.Join(root, ".git", "shallow"), []byte("deadbeef\n"), 0o600); err != nil {
					t.Fatal(err)
				}
				return root
			},
			errContains: "shallow repositories are not supported",
		},
		{
			name: "grafts file refused",
			setup: func(t *testing.T, root string) string {
				infoDir := filepath.Join(root, ".git", "info")
				_ = os.MkdirAll(infoDir, 0o700)
				if err := os.WriteFile(filepath.Join(infoDir, "grafts"), []byte("deadbeef\n"), 0o600); err != nil {
					t.Fatal(err)
				}
				return root
			},
			errContains: "git grafts are not supported",
		},
		{
			name: "alternates file with content refused",
			setup: func(t *testing.T, root string) string {
				altDir := filepath.Join(root, ".git", "objects", "info")
				_ = os.MkdirAll(altDir, 0o700)
				if err := os.WriteFile(filepath.Join(altDir, "alternates"), []byte("/alt/path\n"), 0o600); err != nil {
					t.Fatal(err)
				}
				return root
			},
			errContains: "git alternates are not supported",
		},
		{
			name: "empty alternates file refused",
			setup: func(t *testing.T, root string) string {
				altDir := filepath.Join(root, ".git", "objects", "info")
				_ = os.MkdirAll(altDir, 0o700)
				if err := os.WriteFile(filepath.Join(altDir, "alternates"), []byte(""), 0o600); err != nil {
					t.Fatal(err)
				}
				return root
			},
			errContains: "git alternates are not supported",
		},
		{
			name: "http-alternates file refused",
			setup: func(t *testing.T, root string) string {
				altDir := filepath.Join(root, ".git", "objects", "info")
				_ = os.MkdirAll(altDir, 0o700)
				if err := os.WriteFile(filepath.Join(altDir, "http-alternates"), []byte("https://example.com/obj\n"), 0o600); err != nil {
					t.Fatal(err)
				}
				return root
			},
			errContains: "git http-alternates are not supported",
		},
		{
			name: "partial clone extension config refused",
			setup: func(t *testing.T, root string) string {
				gitSafetyExec(t, root, "config", "extensions.partialclone", "origin")
				return root
			},
			errContains: "partial or promisor clones are not supported",
		},
		{
			name: "promisor remote config refused",
			setup: func(t *testing.T, root string) string {
				gitSafetyExec(t, root, "config", "remote.origin.promisor", "true")
				return root
			},
			errContains: "partial or promisor clones are not supported",
		},
		{
			name: "partialclonefilter config refused",
			setup: func(t *testing.T, root string) string {
				gitSafetyExec(t, root, "config", "remote.origin.partialclonefilter", "blob:none")
				return root
			},
			errContains: "partial or promisor clones are not supported",
		},
		{
			name: "pack promisor file present without config refused",
			setup: func(t *testing.T, root string) string {
				packDir := filepath.Join(root, ".git", "objects", "pack")
				_ = os.MkdirAll(packDir, 0o700)
				if err := os.WriteFile(filepath.Join(packDir, "pack-1111111111111111111111111111111111111111.promisor"), []byte(""), 0o600); err != nil {
					t.Fatal(err)
				}
				return root
			},
			errContains: "partial or promisor clones are not supported",
		},
		{
			name: "local protocol configuration refused",
			setup: func(t *testing.T, root string) string {
				gitSafetyExec(t, root, "config", "protocol.http.allow", "always")
				return root
			},
			errContains: "local protocol configurations are not supported",
		},
		{
			name: "malformed git config syntax refused",
			setup: func(t *testing.T, root string) string {
				cfgPath := filepath.Join(root, ".git", "config")
				if err := os.WriteFile(cfgPath, []byte("[unclosed section\nkey = val\n"), 0o600); err != nil {
					t.Fatal(err)
				}
				return root
			},
			errContains: "invalid or unreadable git config",
		},
		{
			name: "symlinked git directory refused",
			setup: func(t *testing.T, root string) string {
				realGit := filepath.Join(t.TempDir(), "realgit")
				if err := os.Rename(filepath.Join(root, ".git"), realGit); err != nil {
					t.Fatal(err)
				}
				if err := os.Symlink(realGit, filepath.Join(root, ".git")); err != nil {
					t.Fatal(err)
				}
				return root
			},
			errContains: "git directory symlinks are not supported",
		},
		{
			name: "linked worktree file gitdir refused",
			setup: func(t *testing.T, root string) string {
				wtDir := filepath.Join(t.TempDir(), "wt")
				gitSafetyExec(t, root, "worktree", "add", wtDir)
				resolved, err := filepath.EvalSymlinks(wtDir)
				if err != nil {
					t.Fatal(err)
				}
				return resolved
			},
			errContains: "linked worktrees and non-directory .git are not supported",
		},
		{
			name: "symlinked objects directory refused",
			setup: func(t *testing.T, root string) string {
				realObj := filepath.Join(t.TempDir(), "realobj")
				if err := os.Rename(filepath.Join(root, ".git", "objects"), realObj); err != nil {
					t.Fatal(err)
				}
				if err := os.Symlink(realObj, filepath.Join(root, ".git", "objects")); err != nil {
					t.Fatal(err)
				}
				return root
			},
			errContains: "git objects directory symlinks are not supported",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			root := createSafetyGitRepo(t)
			testRoot := tt.setup(t, root)

			gc, err := initGitContext(ctx, testRoot)
			if tt.errContains == "" {
				if err != nil {
					t.Fatalf("expected success, got error: %v", err)
				}
				if gc == nil {
					t.Fatal("expected non-nil gitContext")
				}
			} else {
				if err == nil {
					t.Fatalf("expected error containing %q, got nil", tt.errContains)
				}
				if !strings.Contains(err.Error(), tt.errContains) {
					t.Fatalf("expected error containing %q, got: %v", tt.errContains, err)
				}
			}
		})
	}
}

func TestGitSafetyExactCommitVerification(t *testing.T) {
	ctx := context.Background()
	root := createSafetyGitRepo(t)

	if err := os.WriteFile(filepath.Join(root, "file.txt"), []byte("content\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	gitSafetyExec(t, root, "add", ".")
	gitSafetyExec(t, root, "commit", "-m", "initial commit")

	commitOID := gitSafetyExec(t, root, "rev-parse", "HEAD")

	// Create an annotated tag
	gitSafetyExec(t, root, "tag", "-a", "-m", "annotated tag message", "v1.0-tag", "HEAD")
	tagOID := gitSafetyExec(t, root, "rev-parse", "refs/tags/v1.0-tag")

	gc, err := initGitContext(ctx, root)
	if err != nil {
		t.Fatalf("initGitContext failed: %v", err)
	}

	// 1. Exact commit OID must succeed
	if err := gc.verifyCommitExists(ctx, commitOID, "start"); err != nil {
		t.Fatalf("valid commit OID failed: %v", err)
	}

	// 2. Annotated tag OID must be REJECTED, not peeled
	if tagOID == commitOID {
		t.Fatalf("tag OID (%s) must differ from commit OID (%s)", tagOID, commitOID)
	}
	errTag := gc.verifyCommitExists(ctx, tagOID, "start")
	if errTag == nil {
		t.Fatalf("expected annotated tag OID %s to be rejected, but it succeeded", tagOID)
	}
	if !strings.Contains(errTag.Error(), "not a commit") {
		t.Fatalf("expected error mentioning 'not a commit', got: %v", errTag)
	}

	// 3. Nonexistent OID must fail
	nonexistentOID := strings.Repeat("a", len(commitOID))
	errMissing := gc.verifyCommitExists(ctx, nonexistentOID, "end")
	if errMissing == nil {
		t.Fatalf("expected nonexistent OID to fail")
	}
	if !strings.Contains(errMissing.Error(), "does not exist") {
		t.Fatalf("expected error mentioning 'does not exist', got: %v", errMissing)
	}

	// 4. Invalid length / uppercase hex OID must fail
	errBadHex := gc.verifyCommitExists(ctx, strings.ToUpper(commitOID), "start")
	if errBadHex == nil || !strings.Contains(errBadHex.Error(), "does not match") {
		t.Fatalf("expected bad OID rejection, got: %v", errBadHex)
	}
}

func TestGitSafetyUnboundedHistoryCutoff(t *testing.T) {
	ctx := context.Background()
	root := createSafetyGitRepo(t)

	// Create initial commit
	if err := os.WriteFile(filepath.Join(root, "num.txt"), []byte("0\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	gitSafetyExec(t, root, "add", ".")
	tree := gitSafetyExec(t, root, "write-tree")
	startOID := gitSafetyExec(t, root, "commit-tree", tree, "-m", "commit 0")
	parent := startOID

	// Create 300 commits quickly using the same tree
	for i := 1; i <= 300; i++ {
		parent = gitSafetyExec(t, root, "commit-tree", tree, "-p", parent, "-m", "commit")
	}
	endOID := parent
	gitSafetyExec(t, root, "update-ref", "HEAD", endOID)

	gc, err := initGitContext(ctx, root)
	if err != nil {
		t.Fatalf("initGitContext failed: %v", err)
	}

	// Request history traversal with maxCommits = 256
	// Since there are 300 commits, rev-list --max-count=257 must cutoff at 257 without walking all 300 commits
	_, err = gc.firstParentCommits(ctx, startOID, endOID, 256)
	if err == nil {
		t.Fatal("expected history limit exceeded error for 300 commits with maxCommits=256, got nil")
	}
	if !strings.Contains(err.Error(), "history limit exceeded: commit count (257) exceeds limit (256)") {
		t.Fatalf("unexpected error message: %v", err)
	}
}

func TestGitSafetyCommandMetadataBudget(t *testing.T) {
	ctx := context.Background()
	root := createSafetyGitRepo(t)

	// Create a large object (17 MiB) in Git to exceed 16 MiB metadata budget
	largeData := make([]byte, 17*1024*1024)
	for i := range largeData {
		largeData[i] = byte('A' + (i % 26))
	}
	largeFile := filepath.Join(root, "large.txt")
	if err := os.WriteFile(largeFile, largeData, 0o600); err != nil {
		t.Fatal(err)
	}
	oid := gitSafetyExec(t, root, "hash-object", "-w", "large.txt")

	gc, err := initGitContext(ctx, root)
	if err != nil {
		t.Fatalf("initGitContext failed: %v", err)
	}

	// Attempt to run git command that produces 17 MiB of stdout
	start := time.Now()
	_, err = gc.runGit(ctx, "cat-file", "-p", oid)
	elapsed := time.Since(start)

	if err == nil {
		t.Fatal("expected metadata budget exceeded error, got nil")
	}
	if !strings.Contains(err.Error(), "exceeded metadata budget") {
		t.Fatalf("expected exceeded metadata budget error, got: %v", err)
	}
	if elapsed > 5*time.Second {
		t.Fatalf("command took too long to terminate on excess (%v)", elapsed)
	}
}

func TestGitSafetyOversizedBlobPromptReturnAndChildJoined(t *testing.T) {
	ctx := context.Background()
	root := createSafetyGitRepo(t)

	// Create a 5 MiB blob in git
	blobData := make([]byte, 5*1024*1024)
	for i := range blobData {
		blobData[i] = byte('X')
	}
	blobFile := filepath.Join(root, "blob.txt")
	if err := os.WriteFile(blobFile, blobData, 0o600); err != nil {
		t.Fatal(err)
	}
	oid := gitSafetyExec(t, root, "hash-object", "-w", "blob.txt")

	gc, err := initGitContext(ctx, root)
	if err != nil {
		t.Fatalf("initGitContext failed: %v", err)
	}

	limits := HistoryLimits{
		MaxBlobBytes:       4 * 1024 * 1024,   // 4 MiB limit
		MaxTotalInputBytes: 128 * 1024 * 1024, // 128 MiB limit
	}

	reader, err := newGitBlobReader(ctx, gc, limits)
	if err != nil {
		t.Fatalf("newGitBlobReader failed: %v", err)
	}

	// 1. readBlob must return promptly on oversized blob without hanging while child writes
	readStart := time.Now()
	_, err = reader.readBlob(oid)
	readElapsed := time.Since(readStart)

	if err == nil {
		t.Fatal("expected oversized blob error, got nil")
	}
	if !strings.Contains(err.Error(), "history limit exceeded: blob size (5242880 bytes) exceeds limit (4194304 bytes)") {
		t.Fatalf("unexpected error message: %v", err)
	}
	if readElapsed > 2*time.Second {
		t.Fatalf("readBlob took too long to return on oversized blob (%v)", readElapsed)
	}

	// 2. reader.close() must kill and join child without hanging
	closeStart := time.Now()
	reader.close()
	closeElapsed := time.Since(closeStart)

	if closeElapsed > 2*time.Second {
		t.Fatalf("reader.close() took too long to return (%v)", closeElapsed)
	}
	if reader.cmd.ProcessState == nil {
		t.Fatal("expected child process to be reaped and joined")
	}
}

func TestGitSafetyUnsupportedEntryTypes(t *testing.T) {
	ctx := context.Background()
	root := createSafetyGitRepo(t)

	// Commit 1: normal file
	if err := os.WriteFile(filepath.Join(root, "regular.txt"), []byte("regular\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	gitSafetyExec(t, root, "add", ".")
	t1 := gitSafetyExec(t, root, "write-tree")
	c1 := gitSafetyExec(t, root, "commit-tree", t1, "-m", "commit 1")
	gitSafetyExec(t, root, "update-ref", "HEAD", c1)

	// Commit 2: add a symlink
	if err := os.Symlink("regular.txt", filepath.Join(root, "symlink.txt")); err != nil {
		t.Fatal(err)
	}
	gitSafetyExec(t, root, "add", "symlink.txt")
	t2 := gitSafetyExec(t, root, "write-tree")
	c2 := gitSafetyExec(t, root, "commit-tree", t2, "-p", c1, "-m", "commit 2")
	gitSafetyExec(t, root, "update-ref", "HEAD", c2)

	gc, err := initGitContext(ctx, root)
	if err != nil {
		t.Fatalf("initGitContext failed: %v", err)
	}

	// 1. treeBlobs on commit with symlink must refuse
	_, err = gc.treeBlobs(ctx, c2)
	if err == nil || !strings.Contains(err.Error(), "symlinks are not supported") {
		t.Fatalf("expected treeBlobs symlink refusal, got: %v", err)
	}

	// 2. diffFirstParentCommit across symlink addition must refuse
	_, err = gc.diffFirstParentCommit(ctx, c1, c2)
	if err == nil || !strings.Contains(err.Error(), "symlinks are not supported") {
		t.Fatalf("expected diffFirstParentCommit symlink refusal, got: %v", err)
	}
}

func TestGitSafetyPathValidation(t *testing.T) {
	tests := []struct {
		path    string
		wantErr bool
	}{
		{"valid/path/file.go", false},
		{"README.md", false},
		{"a/b/c/d/e.txt", false},
		{"", true},
		{"/abs/path.go", true},
		{"valid\\path.go", true},
		{"../traversal.go", true},
		{"a/../b.go", true},
		{"a/./b.go", true},
		{"a//b.go", true},
		{".git/config", true},
		{"a/.git/b", true},
		{"path\x00null.go", true},
		{"path\nnewline.go", true},
		{"path\rreturn.go", true},
		{"path\ttab.go", true},
		{"path\x1fctrl.go", true},
		{"path\x7fdel.go", true},
		{"path\xffnonutf8.go", true},
	}

	for _, tt := range tests {
		err := validateGitPath(tt.path)
		if (err != nil) != tt.wantErr {
			t.Errorf("validateGitPath(%q) err = %v, wantErr %v", tt.path, err, tt.wantErr)
		}
	}
}
