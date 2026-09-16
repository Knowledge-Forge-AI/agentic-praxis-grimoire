package hotspot

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func historyCommit(t *testing.T, root, parent string, files map[string]string) string {
	t.Helper()
	for p, body := range files {
		if err := os.MkdirAll(filepath.Dir(filepath.Join(root, p)), 0700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(filepath.Join(root, p), []byte(body), 0600); err != nil {
			t.Fatal(err)
		}
	}
	gitExec(t, root, "add", "-A")
	args := []string{"commit-tree", gitExec(t, root, "write-tree"), "-m", "fixture"}
	if parent != "" {
		args = append(args, "-p", parent)
	}
	oid := gitExec(t, root, args...)
	gitExec(t, root, "update-ref", "HEAD", oid)
	return oid
}

func TestHistoryPreservesStructuralRankingAndRespectsPathSelection(t *testing.T) {
	root := createGitRepo(t)
	start := historyCommit(t, root, "", map[string]string{"main.go": "package p\nfunc F(x int) int { if x>0 {return x};return 0 }\n", "skip/a.txt": "before\n", "node_modules/a.txt": "before\n"})
	end := historyCommit(t, root, start, map[string]string{"main.go": "package p\nfunc F(x int) int { if x>1 {return x};return 0 }\n", "skip/a.txt": "after\n", "node_modules/a.txt": "after\n"})
	req := DefaultRequestV2(root, start, end)
	req.Filters.ExcludePaths = []string{"skip"}
	got, err := AnalyzeV2(context.Background(), req)
	if err != nil {
		t.Fatal(err)
	}
	base := DefaultRequest(root)
	base.Filters = req.Filters
	v1, err := Analyze(context.Background(), base)
	if err != nil {
		t.Fatal(err)
	}
	extracted, err := structuralFromV2(got)
	if err != nil {
		t.Fatal(err)
	}
	a, _ := MarshalJSON(v1)
	b, _ := MarshalJSON(extracted)
	if !bytes.Equal(a, b) {
		t.Fatal("history changed structural metrics/rankings/candidates")
	}
	if len(got.History.Files) != 1 || got.History.Files[0].Path != "main.go" || got.History.PathTransitionCount != 1 {
		t.Fatalf("history ignored path exclusions: %+v", got.History)
	}
	if *got.History.Files[0].Churn != 2 || *got.History.Files[0].Growth != 0 {
		t.Fatal("replacement must count one deletion plus one insertion")
	}
}

func TestHistoryCanonicalBytesAcrossPhysicalRootsAndHostileEnvironment(t *testing.T) {
	root := createGitRepo(t)
	start := historyCommit(t, root, "", map[string]string{"a.txt": "one\n"})
	end := historyCommit(t, root, start, map[string]string{"a.txt": "two\nthree\n"})
	other, err := filepath.EvalSymlinks(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	gitExec(t, other, "clone", "--no-local", root, "copy")
	req := DefaultRequestV2(root, start, end)
	req.RootID = "same-logical-content"
	first, err := AnalyzeV2(context.Background(), req)
	if err != nil {
		t.Fatal(err)
	}
	a, err := MarshalJSONV2(first)
	if err != nil {
		t.Fatal(err)
	}
	req.Root = filepath.Join(other, "copy")
	t.Setenv("GIT_DIR", filepath.Join(other, "missing"))
	t.Setenv("GIT_CONFIG_COUNT", "1")
	t.Setenv("GIT_CONFIG_KEY_0", "core.abbrev")
	t.Setenv("GIT_CONFIG_VALUE_0", "4")
	t.Setenv("LC_ALL", "C")
	second, err := AnalyzeV2(context.Background(), req)
	if err != nil {
		t.Fatal(err)
	}
	b, err := MarshalJSONV2(second)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(a, b) {
		t.Fatal("same immutable content/history changed with physical root or inherited Git overrides")
	}
}

func TestHistoryUntrackedAvailabilityAndSkippedContentAreNotFalseZerosOrDeletion(t *testing.T) {
	root := createGitRepo(t)
	oid := historyCommit(t, root, "", map[string]string{"extensionless": "ordinary data\n", "a.txt": "known\n"})
	if err := os.WriteFile(filepath.Join(root, "untracked.txt"), []byte("new\n"), 0600); err != nil {
		t.Fatal(err)
	}
	r, err := AnalyzeV2(context.Background(), DefaultRequestV2(root, oid, oid))
	if err != nil {
		t.Fatal(err)
	}
	rows := map[string]FileHistory{}
	for _, h := range r.History.Files {
		rows[h.Path] = h
	}
	h := rows["untracked.txt"]
	if h.Churn != nil || h.Growth != nil || h.ChurnAvailability != AvailabilityUnavailable {
		t.Fatal("untracked content represented as measured zero")
	}
	if rows["extensionless"].WorkingTreeStatus != WorkingTreeNotScanned {
		t.Fatal("skipped current file represented as deleted")
	}
	if r.History.UnavailablePaths != 1 {
		t.Fatal("subtotal lacks unavailable population disclosure")
	}
}

func TestHistoryMissingIntermediateBinaryBlobRefusesCompleteObservation(t *testing.T) {
	root := createGitRepo(t)
	start := historyCommit(t, root, "", map[string]string{"a.bin": "\x00start"})
	mid := historyCommit(t, root, start, map[string]string{"a.bin": "\x00middle"})
	end := historyCommit(t, root, mid, map[string]string{"a.bin": "\x00end"})
	oid := gitExec(t, root, "rev-parse", mid+":a.bin")
	if err := os.Remove(filepath.Join(root, ".git", "objects", oid[:2], oid[2:])); err != nil {
		t.Fatal(err)
	}
	r, err := AnalyzeV2(context.Background(), DefaultRequestV2(root, start, end))
	if err == nil || !reflect.DeepEqual(r, ReportV2{}) {
		t.Fatal("missing intermediate binary object accepted as complete history")
	}
}

func TestV2RequestAndRendererRefusalsArePublic(t *testing.T) {
	root := createGitRepo(t)
	oid := historyCommit(t, root, "", map[string]string{"a.txt": "one\n"})
	req := DefaultRequestV2(root, oid, oid)
	wire := requestV2JSON{SchemaVersion: RequestSchemaV2, Root: root, RootID: "wire", ToolVersion: "test", MaxFiles: 10, MaxBytesFile: 1024, MaxTotalBytes: 4096, MaxDurationMS: 10000, DisplayTopN: 2, History: historyRequestJSON{StartOID: oid, EndOID: oid, Limits: historyLimitsJSON(req.History.Limits)}}
	data, err := json.Marshal(wire)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := ParseRequestV2JSON(data); err != nil {
		t.Fatal(err)
	}
	for _, bad := range [][]byte{bytes.Replace(data, []byte(`"schema_version":`), []byte(`"unknown":1,"schema_version":`), 1), bytes.Replace(data, []byte(`"root_id":"wire"`), []byte(`"root_id":"wire","root_id":"other"`), 1), append(data, []byte(" {}")...), []byte("\xff"), bytes.Replace(data, []byte(RequestSchemaV2), []byte(RequestSchemaV1), 1)} {
		if _, err := ParseRequestV2JSON(bad); err == nil {
			t.Fatal("unsupported v2 request accepted")
		}
	}
	r, err := AnalyzeV2(context.Background(), req)
	if err != nil {
		t.Fatal(err)
	}
	r.History.TotalChurn = 999
	for _, render := range []func(ReportV2) ([]byte, error){MarshalJSONV2, RenderTerminalV2, RenderMarkdownV2} {
		if _, err := render(r); err == nil {
			t.Fatal("tampered history accepted by renderer")
		}
	}
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	if _, err := AnalyzeV2(ctx, req); !errors.Is(err, context.Canceled) {
		t.Fatalf("cancellation class lost: %v", err)
	}
	req.Filters.IncludeLanguages = []Language{LanguageGo}
	if _, err := AnalyzeV2(context.Background(), req); err == nil || !strings.Contains(err.Error(), "language filters") {
		t.Fatal("unsupported historical language filtering accepted")
	}
}

func TestV2RenderersRefuseStructuralFileMissingFromHistory(t *testing.T) {
	root := createGitRepo(t)
	oid := historyCommit(t, root, "", map[string]string{"a.go": "package p\n"})
	r, err := AnalyzeV2(context.Background(), DefaultRequestV2(root, oid, oid))
	if err != nil {
		t.Fatal(err)
	}
	if len(r.Files) != 1 {
		t.Fatal("fixture must contain a structural file")
	}
	r.History.Files = []FileHistory{}
	r.Files[0].History = &FileHistory{}
	r.History.ID = historyIdentity(r.History)
	r.Fingerprint, err = fingerprintV2(r)
	if err != nil {
		t.Fatal(err)
	}
	for _, render := range []func(ReportV2) ([]byte, error){MarshalJSONV2, RenderTerminalV2, RenderMarkdownV2} {
		if _, err := render(r); err == nil {
			t.Fatal("unbound structural file accepted")
		}
	}
}

func TestV2ResourceDiagnosticsDoNotChangeSemanticIdentity(t *testing.T) {
	root := createGitRepo(t)
	oid := historyCommit(t, root, "", map[string]string{"a.go": "package p\n"})
	r, err := AnalyzeV2(context.Background(), DefaultRequestV2(root, oid, oid))
	if err != nil {
		t.Fatal(err)
	}
	original, err := MarshalJSONV2(r)
	if err != nil {
		t.Fatal(err)
	}
	r.History.TotalBlobsRead++
	r.History.TotalInputBytes++
	r.History.AggregateCells++
	if historyIdentity(r.History) != r.History.ID {
		t.Fatal("resource metering changed history identity")
	}
	changed, err := MarshalJSONV2(r)
	if err != nil {
		t.Fatalf("resource diagnostics changed report identity: %v", err)
	}
	if bytes.Equal(original, changed) {
		t.Fatal("resource diagnostics were lost from serialized report")
	}
	markdown, err := RenderMarkdownV2(r)
	if err != nil {
		t.Fatal(err)
	}
	if strings.Contains(string(markdown), "this analyzer does not inspect Git history") || !strings.Contains(string(markdown), "File-level history is explicitly selected") {
		t.Fatal("v2 Markdown must describe selected history, not v1 deferral")
	}
}
