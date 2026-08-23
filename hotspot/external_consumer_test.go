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
  "path/filepath"
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
`
	if err := os.WriteFile(filepath.Join(consumer, "consumer_test.go"), []byte(program), 0o600); err != nil {
		t.Fatal(err)
	}
	command := exec.CommandContext(context.Background(), "go", "test", "./...")
	command.Dir = consumer
	command.Env = append(os.Environ(), "GOTOOLCHAIN=local", "GOWORK=off")
	output, err := command.CombinedOutput()
	if err != nil {
		t.Fatalf("external consumer failed: %v\n%s", err, strings.TrimSpace(string(output)))
	}
}
