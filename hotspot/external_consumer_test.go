package hotspot

import (
	"context"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func TestExternalModuleConsumer(t *testing.T) {
	if testing.Short() {
		t.Skip("external module proof is not part of short feedback")
	}
	_, sourceFile, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("runtime caller unavailable")
	}
	repositoryRoot := filepath.Dir(filepath.Dir(sourceFile))
	consumer := t.TempDir()
	module := "module consumer.test\n\ngo 1.25\n\nrequire github.com/Knowledge-Forge-AI/agentic-praxis-grimoire v0.0.0\n\nreplace github.com/Knowledge-Forge-AI/agentic-praxis-grimoire => " + repositoryRoot + "\n"
	if err := os.WriteFile(filepath.Join(consumer, "go.mod"), []byte(module), 0o600); err != nil {
		t.Fatal(err)
	}
	program := `package consumer

import (
  "context"
  "os"
  "os/exec"
  "path/filepath"
  "strings"
  "testing"
  "github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/hotspot"
)

func TestInProcess(t *testing.T) {
  root, err := filepath.EvalSymlinks(t.TempDir())
  if err != nil { t.Fatal(err) }
  if err := os.WriteFile(filepath.Join(root, "main.go"), []byte("package p\nfunc F() {}\n"), 0600); err != nil { t.Fatal(err) }
  request := hotspot.DefaultRequest(root)
  request.RootID = "consumer"
  request.ToolVersion = "consumer-test"
  report, err := hotspot.Analyze(context.Background(), request)
  if err != nil { t.Fatal(err) }
  if _, err := hotspot.MarshalJSON(report); err != nil { t.Fatal(err) }
  if _, err := hotspot.RenderTerminal(report); err != nil { t.Fatal(err) }
  if _, err := hotspot.RenderMarkdown(report); err != nil { t.Fatal(err) }
}

func TestInProcessV2(t *testing.T) {
  root, err := filepath.EvalSymlinks(t.TempDir())
  if err != nil { t.Fatal(err) }
  runCmd := func(args ...string) string {
    c := exec.Command("git", args...)
    c.Dir = root
    c.Env = append(os.Environ(), "GIT_CONFIG_NOSYSTEM=1", "GIT_AUTHOR_NAME=Test", "GIT_AUTHOR_EMAIL=test@example.com", "GIT_COMMITTER_NAME=Test", "GIT_COMMITTER_EMAIL=test@example.com")
    out, err := c.CombinedOutput()
    if err != nil { t.Fatalf("git %v failed: %v %s", args, err, out) }
    return strings.TrimSpace(string(out))
  }
  runCmd("init")
  runCmd("config", "user.name", "Test")
  runCmd("config", "user.email", "test@example.com")
  if err := os.WriteFile(filepath.Join(root, "main.go"), []byte("package p\nfunc F() {}\n"), 0600); err != nil { t.Fatal(err) }
  runCmd("add", ".")
  oid := runCmd("commit-tree", runCmd("write-tree"), "-m", "init")
  runCmd("update-ref", "HEAD", oid)

  if err := os.WriteFile(filepath.Join(root, "main.go"), []byte("package p\nfunc F() {}\nfunc G() {}\n"), 0600); err != nil { t.Fatal(err) }
  runCmd("add", ".")
  end := runCmd("commit-tree", runCmd("write-tree"), "-p", oid, "-m", "grow")
  runCmd("update-ref", "HEAD", end)
  request := hotspot.DefaultRequestV2(root, oid, end)
  request.RootID = "consumer-v2"
  request.ToolVersion = "consumer-test"
  report, err := hotspot.AnalyzeV2(context.Background(), request)
  if err != nil { t.Fatal(err) }
  if report.History.CommitCount != 1 || report.History.TotalChurn != 1 || report.History.NetGrowth != 1 { t.Fatal("external history arithmetic mismatch") }
  if _, err := hotspot.MarshalJSONV2(report); err != nil { t.Fatal(err) }
  if _, err := hotspot.RenderTerminalV2(report); err != nil { t.Fatal(err) }
  if _, err := hotspot.RenderMarkdownV2(report); err != nil { t.Fatal(err) }
}
`
	if err := os.WriteFile(filepath.Join(consumer, "consumer_test.go"), []byte(program), 0o600); err != nil {
		t.Fatal(err)
	}
	command := exec.CommandContext(context.Background(), "go", "test", "./...")
	command.Dir = consumer
	command.Env = append(os.Environ(), "GOTOOLCHAIN=local", "GOWORK=off", "GOPROXY=off")
	output, err := command.CombinedOutput()
	if err != nil {
		t.Fatalf("external consumer failed: %v\n%s", err, strings.TrimSpace(string(output)))
	}
}
