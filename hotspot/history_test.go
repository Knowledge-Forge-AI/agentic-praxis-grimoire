package hotspot

import (
	"context"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func createGitRepo(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()
	resolved, err := filepath.EvalSymlinks(dir)
	if err != nil {
		t.Fatal(err)
	}
	gitExec(t, resolved, "init")
	gitExec(t, resolved, "config", "user.name", "APG Test")
	gitExec(t, resolved, "config", "user.email", "apg-test@example.com")
	gitExec(t, resolved, "config", "commit.gpgsign", "false")
	return resolved
}

func gitExec(t *testing.T, dir string, args ...string) string {
	t.Helper()
	cmd := exec.Command("git", args...)
	cmd.Dir = dir
	cmd.Env = append(os.Environ(),
		"GIT_AUTHOR_NAME=APG Test",
		"GIT_AUTHOR_EMAIL=apg-test@example.com",
		"GIT_COMMITTER_NAME=APG Test",
		"GIT_COMMITTER_EMAIL=apg-test@example.com",
		"GIT_CONFIG_NOSYSTEM=1",
		"GIT_AUTHOR_DATE=2026-01-01T00:00:00Z",
		"GIT_COMMITTER_DATE=2026-01-01T00:00:00Z",
	)
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("git %v in %s failed: %v\n%s", args, dir, err, out)
	}
	return strings.TrimSpace(string(out))
}

func TestHistoryStableVsHighChurn(t *testing.T) {
	root := createGitRepo(t)

	if err := os.WriteFile(filepath.Join(root, "large-stable.txt"), []byte(strings.Repeat("stable line\n", 1200)), 0o600); err != nil {
		t.Fatal(err)
	}
	// Commit 1: Initial commit with stable.go and churn.go
	if err := os.WriteFile(filepath.Join(root, "stable.go"), []byte("package p\n\nfunc Stable() int {\n\tx := 1\n\tif x > 0 {\n\t\treturn x\n\t}\n\treturn 0\n}\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "churn.go"), []byte("package p\n\nvar V = 1\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	gitExec(t, root, "add", ".")
	startOID := gitExec(t, root, "commit-tree", gitExec(t, root, "write-tree"), "-m", "initial")
	gitExec(t, root, "update-ref", "HEAD", startOID)

	// Commit 2: Modify churn.go
	if err := os.WriteFile(filepath.Join(root, "churn.go"), []byte("package p\n\nvar V = 2\nvar Extra = true\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	gitExec(t, root, "add", ".")
	c2 := gitExec(t, root, "commit-tree", gitExec(t, root, "write-tree"), "-p", startOID, "-m", "churn 1")
	gitExec(t, root, "update-ref", "HEAD", c2)

	// Commit 3: Modify churn.go again
	if err := os.WriteFile(filepath.Join(root, "churn.go"), []byte("package p\n\nvar V = 3\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	gitExec(t, root, "add", ".")
	c3 := gitExec(t, root, "commit-tree", gitExec(t, root, "write-tree"), "-p", c2, "-m", "churn 2")
	gitExec(t, root, "update-ref", "HEAD", c3)

	// Commit 4: Modify churn.go a third time; stable.go untouched
	if err := os.WriteFile(filepath.Join(root, "churn.go"), []byte("package p\n\nvar V = 4\n// trailing line\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	gitExec(t, root, "add", ".")
	endOID := gitExec(t, root, "commit-tree", gitExec(t, root, "write-tree"), "-p", c3, "-m", "churn 3")
	gitExec(t, root, "update-ref", "HEAD", endOID)

	req := DefaultRequestV2(root, startOID, endOID)
	report, err := AnalyzeV2(context.Background(), req)
	if err != nil {
		t.Fatalf("AnalyzeV2 failed: %v", err)
	}

	if report.History.CommitCount != 3 {
		t.Fatalf("expected 3 commits, got %d", report.History.CommitCount)
	}
	if report.History.PathTransitionCount != 3 {
		t.Fatalf("expected 3 transitions, got %d", report.History.PathTransitionCount)
	}

	var stableHist, churnHist *FileHistory
	for _, f := range report.History.Files {
		if f.Path == "large-stable.txt" && (f.Churn == nil || *f.Churn != 0 || f.StartLines == nil || *f.StartLines != 1200) {
			t.Fatalf("large stable file: %+v", f)
		}
		if f.Path == "stable.go" {
			h := f
			stableHist = &h
		}
		if f.Path == "churn.go" {
			h := f
			churnHist = &h
		}
	}

	if stableHist == nil || churnHist == nil {
		t.Fatalf("missing expected history files in summary: stable=%v churn=%v", stableHist, churnHist)
	}

	if stableHist.TransitionCount != 0 || *stableHist.Churn != 0 || *stableHist.Growth != 0 {
		t.Fatalf("stable.go expected 0 transitions and churn, got %+v", stableHist)
	}
	if churnHist.TransitionCount != 3 || *churnHist.Churn <= 0 {
		t.Fatalf("churn.go expected 3 transitions and positive churn, got %+v", churnHist)
	}
	if churnHist.WorkingTreeStatus != WorkingTreeClean {
		t.Fatalf("churn.go expected clean status, got %s", churnHist.WorkingTreeStatus)
	}
}

func TestHistoryNetZeroAndPosNegativeGrowth(t *testing.T) {
	root := createGitRepo(t)

	// Commit 1 (start)
	if err := os.WriteFile(filepath.Join(root, "netzero.txt"), []byte("line 1\nline 2\nline 3\nline 4\nline 5\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "pos.txt"), []byte("line 1\nline 2\nline 3\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "neg.txt"), []byte("1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	gitExec(t, root, "add", ".")
	startOID := gitExec(t, root, "commit-tree", gitExec(t, root, "write-tree"), "-m", "start")
	gitExec(t, root, "update-ref", "HEAD", startOID)

	// Commit 2: netzero grows to 7 lines, pos grows to 6 lines, neg shrinks to 5 lines
	if err := os.WriteFile(filepath.Join(root, "netzero.txt"), []byte("line 1\nline 2 modified\nline 3\nline 4\nline 5\nline 6\nline 7\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "pos.txt"), []byte("line 1\nline 2\nline 3\nline 4\nline 5\nline 6\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "neg.txt"), []byte("1\n2\n3\n4\n5\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	gitExec(t, root, "add", ".")
	c2 := gitExec(t, root, "commit-tree", gitExec(t, root, "write-tree"), "-p", startOID, "-m", "step")
	gitExec(t, root, "update-ref", "HEAD", c2)

	// Commit 3 (end): netzero shrinks back to 5 lines (net-zero growth!)
	if err := os.WriteFile(filepath.Join(root, "netzero.txt"), []byte("line 1\nline 2 replaced\nline 3\nline 4\nline 5\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	gitExec(t, root, "add", ".")
	endOID := gitExec(t, root, "commit-tree", gitExec(t, root, "write-tree"), "-p", c2, "-m", "end")
	gitExec(t, root, "update-ref", "HEAD", endOID)

	req := DefaultRequestV2(root, startOID, endOID)
	report, err := AnalyzeV2(context.Background(), req)
	if err != nil {
		t.Fatalf("AnalyzeV2 failed: %v", err)
	}

	var nz, pos, neg *FileHistory
	for _, f := range report.History.Files {
		switch f.Path {
		case "netzero.txt":
			h := f
			nz = &h
		case "pos.txt":
			h := f
			pos = &h
		case "neg.txt":
			h := f
			neg = &h
		}
	}

	if nz == nil || pos == nil || neg == nil {
		t.Fatalf("missing history entries: nz=%v pos=%v neg=%v", nz, pos, neg)
	}

	if *nz.Growth != 0 {
		t.Fatalf("netzero expected growth 0, got %d", *nz.Growth)
	}
	if *nz.Churn <= 0 {
		t.Fatalf("netzero expected churn > 0, got %d", *nz.Churn)
	}
	if *pos.Growth != 3 {
		t.Fatalf("pos expected growth +3, got %d", *pos.Growth)
	}
	if *neg.Growth != -5 {
		t.Fatalf("neg expected growth -5, got %d", *neg.Growth)
	}
}

func TestHistoryMissingFinalNewline(t *testing.T) {
	root := createGitRepo(t)

	// Start commit: no final newline (2 physical lines)
	if err := os.WriteFile(filepath.Join(root, "tail.txt"), []byte("line 1\nline 2"), 0o600); err != nil {
		t.Fatal(err)
	}
	gitExec(t, root, "add", ".")
	startOID := gitExec(t, root, "commit-tree", gitExec(t, root, "write-tree"), "-m", "start")
	gitExec(t, root, "update-ref", "HEAD", startOID)

	// End commit: 3 physical lines, still no final newline
	if err := os.WriteFile(filepath.Join(root, "tail.txt"), []byte("line 1\nline 2\nline 3"), 0o600); err != nil {
		t.Fatal(err)
	}
	gitExec(t, root, "add", ".")
	endOID := gitExec(t, root, "commit-tree", gitExec(t, root, "write-tree"), "-p", startOID, "-m", "end")
	gitExec(t, root, "update-ref", "HEAD", endOID)

	req := DefaultRequestV2(root, startOID, endOID)
	report, err := AnalyzeV2(context.Background(), req)
	if err != nil {
		t.Fatalf("AnalyzeV2 failed: %v", err)
	}

	var hist *FileHistory
	for _, f := range report.History.Files {
		if f.Path == "tail.txt" {
			h := f
			hist = &h
		}
	}
	if hist == nil {
		t.Fatal("missing tail.txt history")
	}
	if *hist.StartLines != 2 || *hist.EndLines != 3 || *hist.Growth != 1 {
		t.Fatalf("unexpected line metrics: start=%d end=%d growth=%d", *hist.StartLines, *hist.EndLines, *hist.Growth)
	}
}

func TestHistoryMergeRenameAddDeleteBinaryDirtyUntracked(t *testing.T) {
	root := createGitRepo(t)

	// Commit 1: start
	if err := os.WriteFile(filepath.Join(root, "rename_old.txt"), []byte("rename me\nline 2\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "deleted.txt"), []byte("to be deleted\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "binary.bin"), []byte{0x00, 0x01, 0x02, 0x03}, 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "dirty.txt"), []byte("clean content\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "main_file.txt"), []byte("base on main\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	gitExec(t, root, "add", ".")
	startOID := gitExec(t, root, "commit-tree", gitExec(t, root, "write-tree"), "-m", "start")
	gitExec(t, root, "update-ref", "HEAD", startOID)

	// Create branch for merge test
	branchOID := gitExec(t, root, "commit-tree", gitExec(t, root, "write-tree"), "-p", startOID, "-m", "branch commit")

	// Main commit with rename, add, delete, binary change
	if err := os.Remove(filepath.Join(root, "rename_old.txt")); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "rename_new.txt"), []byte("rename me\nline 2\nline 3\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.Remove(filepath.Join(root, "deleted.txt")); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "added.txt"), []byte("brand new file\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "binary.bin"), []byte{0x00, 0x01, 0x99, 0x88}, 0o600); err != nil {
		t.Fatal(err)
	}
	gitExec(t, root, "add", "-A")
	cMain := gitExec(t, root, "commit-tree", gitExec(t, root, "write-tree"), "-p", startOID, "-m", "main changes")

	// Merge commit (first-parent chain: cMain is parent 1, branchOID is parent 2)
	endOID := gitExec(t, root, "commit-tree", gitExec(t, root, "write-tree"), "-p", cMain, "-p", branchOID, "-m", "merge branch")
	gitExec(t, root, "update-ref", "HEAD", endOID)

	// Now make dirty and untracked changes in working tree
	if err := os.WriteFile(filepath.Join(root, "dirty.txt"), []byte("dirty working tree change\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, "untracked.txt"), []byte("not in git at all\n"), 0o600); err != nil {
		t.Fatal(err)
	}

	req := DefaultRequestV2(root, startOID, endOID)
	report, err := AnalyzeV2(context.Background(), req)
	if err != nil {
		t.Fatalf("AnalyzeV2 failed: %v", err)
	}

	histMap := make(map[string]FileHistory)
	for _, f := range report.History.Files {
		histMap[f.Path] = f
	}

	// Verify rename: rename_old is deleted, rename_new is added (no rename inference)
	if old, ok := histMap["rename_old.txt"]; !ok || old.WorkingTreeStatus != WorkingTreeDeleted {
		t.Fatalf("rename_old expected deleted status, got %+v", old)
	}
	if newF, ok := histMap["rename_new.txt"]; !ok || newF.TransitionCount != 1 {
		t.Fatalf("rename_new expected 1 transition, got %+v", newF)
	}

	// Verify deleted: retained in report
	if del, ok := histMap["deleted.txt"]; !ok || del.WorkingTreeStatus != WorkingTreeDeleted {
		t.Fatalf("deleted.txt expected retained with deleted status, got %+v", del)
	}

	// Verify added
	if add, ok := histMap["added.txt"]; !ok || add.TransitionCount != 1 || *add.Growth != 1 {
		t.Fatalf("added.txt expected 1 transition, got %+v", add)
	}

	// Verify binary: line metrics unavailable (never zero!), transition counted
	if bin, ok := histMap["binary.bin"]; !ok {
		t.Fatal("missing binary.bin")
	} else {
		if bin.TransitionCount != 1 {
			t.Fatalf("binary.bin expected 1 transition, got %d", bin.TransitionCount)
		}
		if bin.ChurnAvailability != AvailabilityUnavailable || bin.GrowthAvailability != AvailabilityUnavailable {
			t.Fatalf("binary.bin line metrics must be unavailable, got churn=%v growth=%v", bin.ChurnAvailability, bin.GrowthAvailability)
		}
		if bin.Churn != nil || bin.Growth != nil {
			t.Fatalf("binary.bin Churn and Growth must be nil, got %v %v", bin.Churn, bin.Growth)
		}
	}

	// Verify dirty
	if dirty, ok := histMap["dirty.txt"]; !ok || dirty.WorkingTreeStatus != WorkingTreeModified {
		t.Fatalf("dirty.txt expected modified status, got %+v", dirty)
	}

	// Verify untracked
	if untracked, ok := histMap["untracked.txt"]; !ok || untracked.WorkingTreeStatus != WorkingTreeUntracked {
		t.Fatalf("untracked.txt expected untracked status, got %+v", untracked)
	}
}

func TestHistoryEmptyRange(t *testing.T) {
	root := createGitRepo(t)
	if err := os.WriteFile(filepath.Join(root, "file.go"), []byte("package p\nfunc F() {}\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	gitExec(t, root, "add", ".")
	oid := gitExec(t, root, "commit-tree", gitExec(t, root, "write-tree"), "-m", "init")
	gitExec(t, root, "update-ref", "HEAD", oid)

	req := DefaultRequestV2(root, oid, oid)
	report, err := AnalyzeV2(context.Background(), req)
	if err != nil {
		t.Fatalf("AnalyzeV2 failed: %v", err)
	}

	if report.History.CommitCount != 0 {
		t.Fatalf("expected 0 commits for empty range, got %d", report.History.CommitCount)
	}
	if report.History.TotalChurn != 0 || report.History.NetGrowth != 0 {
		t.Fatalf("expected 0 churn and growth, got %d %d", report.History.TotalChurn, report.History.NetGrowth)
	}
}

func TestHistoryRefusedEnvironments(t *testing.T) {
	root := createGitRepo(t)
	if err := os.WriteFile(filepath.Join(root, "file.go"), []byte("package p\nfunc F() {}\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	gitExec(t, root, "add", ".")
	oid := gitExec(t, root, "commit-tree", gitExec(t, root, "write-tree"), "-m", "init")
	gitExec(t, root, "update-ref", "HEAD", oid)

	// Test subtree refusal
	subDir := filepath.Join(root, "sub")
	if err := os.Mkdir(subDir, 0o700); err != nil {
		t.Fatal(err)
	}
	reqSub := DefaultRequestV2(subDir, oid, oid)
	if _, err := AnalyzeV2(context.Background(), reqSub); err == nil || !strings.Contains(err.Error(), "subtrees are not supported") {
		t.Fatalf("expected subtree refusal, got %v", err)
	}

	// Test graft refusal
	graftsDir := filepath.Join(root, ".git", "info")
	_ = os.MkdirAll(graftsDir, 0o700)
	if err := os.WriteFile(filepath.Join(graftsDir, "grafts"), []byte("deadbeef\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	reqGraft := DefaultRequestV2(root, oid, oid)
	if _, err := AnalyzeV2(context.Background(), reqGraft); err == nil || !strings.Contains(err.Error(), "grafts are not supported") {
		t.Fatalf("expected grafts refusal, got %v", err)
	}
	_ = os.Remove(filepath.Join(graftsDir, "grafts"))

	// Test alternates refusal
	altDir := filepath.Join(root, ".git", "objects", "info")
	_ = os.MkdirAll(altDir, 0o700)
	if err := os.WriteFile(filepath.Join(altDir, "alternates"), []byte("/some/alt/path\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	reqAlt := DefaultRequestV2(root, oid, oid)
	if _, err := AnalyzeV2(context.Background(), reqAlt); err == nil || !strings.Contains(err.Error(), "alternates are not supported") {
		t.Fatalf("expected alternates refusal, got %v", err)
	}
	_ = os.Remove(filepath.Join(altDir, "alternates"))

	// Test shallow refusal
	if err := os.WriteFile(filepath.Join(root, ".git", "shallow"), []byte(oid+"\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	reqShallow := DefaultRequestV2(root, oid, oid)
	if _, err := AnalyzeV2(context.Background(), reqShallow); err == nil || !strings.Contains(err.Error(), "shallow repositories are not supported") {
		t.Fatalf("expected shallow refusal, got %v", err)
	}
	_ = os.Remove(filepath.Join(root, ".git", "shallow"))

	// Test non-ancestor start commit refusal
	otherTree := gitExec(t, root, "write-tree")
	orphanOID := gitExec(t, root, "commit-tree", otherTree, "-m", "orphan")
	reqNonAncestor := DefaultRequestV2(root, orphanOID, oid)
	if _, err := AnalyzeV2(context.Background(), reqNonAncestor); err == nil || !strings.Contains(err.Error(), "not an ancestor") {
		t.Fatalf("expected non-ancestor refusal, got %v", err)
	}
}

func TestHistoryCancellationAndLimits(t *testing.T) {
	root := createGitRepo(t)
	if err := os.WriteFile(filepath.Join(root, "file.go"), []byte("package p\nfunc F() {}\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	gitExec(t, root, "add", ".")
	c1 := gitExec(t, root, "commit-tree", gitExec(t, root, "write-tree"), "-m", "c1")
	if err := os.WriteFile(filepath.Join(root, "file.go"), []byte("package p\nfunc F2() {}\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	gitExec(t, root, "add", ".")
	c2 := gitExec(t, root, "commit-tree", gitExec(t, root, "write-tree"), "-p", c1, "-m", "c2")
	if err := os.WriteFile(filepath.Join(root, "file.go"), []byte("package p\nfunc F3() {}\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	gitExec(t, root, "add", ".")
	c3 := gitExec(t, root, "commit-tree", gitExec(t, root, "write-tree"), "-p", c2, "-m", "c3")
	gitExec(t, root, "update-ref", "HEAD", c3)

	// Context cancellation
	ctxCancel, cancel := context.WithCancel(context.Background())
	cancel()
	req := DefaultRequestV2(root, c1, c3)
	if _, err := AnalyzeV2(ctxCancel, req); err == nil {
		t.Fatal("expected cancellation error, got nil")
	}

	// Max commits limit
	reqCommits := DefaultRequestV2(root, c1, c3)
	reqCommits.History.Limits.MaxCommits = 1
	if _, err := AnalyzeV2(context.Background(), reqCommits); err == nil || !strings.Contains(err.Error(), "commit count") {
		t.Fatalf("expected max commits limit exceeded, got %v", err)
	}

	// Max path transitions limit
	reqTrans := DefaultRequestV2(root, c1, c3)
	reqTrans.History.Limits.MaxPathTransitions = 1
	if _, err := AnalyzeV2(context.Background(), reqTrans); err == nil || !strings.Contains(err.Error(), "path transitions") {
		t.Fatalf("expected max path transitions limit exceeded, got %v", err)
	}
}

func TestHistoryRepeatedIdenticalBytesSameRoot(t *testing.T) {
	root1 := createGitRepo(t)
	if err := os.WriteFile(filepath.Join(root1, "main.go"), []byte("package main\nfunc main() {}\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	gitExec(t, root1, "add", ".")
	startOID := gitExec(t, root1, "commit-tree", gitExec(t, root1, "write-tree"), "-m", "init")
	if err := os.WriteFile(filepath.Join(root1, "main.go"), []byte("package main\nimport \"fmt\"\nfunc main() { fmt.Println() }\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	gitExec(t, root1, "add", ".")
	endOID := gitExec(t, root1, "commit-tree", gitExec(t, root1, "write-tree"), "-p", startOID, "-m", "update")
	gitExec(t, root1, "update-ref", "HEAD", endOID)

	req1 := DefaultRequestV2(root1, startOID, endOID)
	req1.RootID = "repeat-fixture"
	req1.ToolVersion = "test"

	rep1, err := AnalyzeV2(context.Background(), req1)
	if err != nil {
		t.Fatalf("rep1 failed: %v", err)
	}
	json1, err := MarshalJSONV2(rep1)
	if err != nil {
		t.Fatalf("json1 failed: %v", err)
	}

	// Second run on same root
	rep2, err := AnalyzeV2(context.Background(), req1)
	if err != nil {
		t.Fatalf("rep2 failed: %v", err)
	}
	json2, err := MarshalJSONV2(rep2)
	if err != nil {
		t.Fatalf("json2 failed: %v", err)
	}

	if string(json1) != string(json2) {
		t.Fatal("JSON output across repeated runs on same root is not identical")
	}
	if rep1.Fingerprint != rep2.Fingerprint {
		t.Fatalf("fingerprint mismatch: %s vs %s", rep1.Fingerprint, rep2.Fingerprint)
	}
}

func TestNoHistoryWithoutGit(t *testing.T) {
	t.Setenv("PATH", t.TempDir())
	// Structural v1 analysis does NOT require Git
	tempDir, err := filepath.EvalSymlinks(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(tempDir, "file.go"), []byte("package p\nfunc F() {}\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	v1Req := DefaultRequest(tempDir)
	rep, err := Analyze(context.Background(), v1Req)
	if err != nil {
		t.Fatalf("v1 Analyze failed: %v", err)
	}
	if len(rep.Files) != 1 {
		t.Fatalf("expected 1 file in v1 report, got %d", len(rep.Files))
	}
}
