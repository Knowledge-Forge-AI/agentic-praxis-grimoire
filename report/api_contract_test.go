package report

import (
	"bytes"
	"context"
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"testing"
)

func TestNewValidatesExactRepositoryAndGitExecutable(t *testing.T) {
	repository, _ := initializeDiffRepository(t)

	nested := filepath.Join(repository, "nested")
	if err := os.Mkdir(nested, 0o700); err != nil {
		t.Fatal(err)
	}
	if _, err := New(Options{Repository: nested}); !errors.Is(err, ErrRepository) {
		t.Fatalf("nested repository error = %v", err)
	}
	if _, err := New(Options{Repository: repository, GitPath: "git"}); !errors.Is(err, ErrInvalidRequest) {
		t.Fatalf("relative Git path error = %v", err)
	}
	gitPath, err := exec.LookPath("git")
	if err != nil {
		t.Fatal(err)
	}
	gitPath, err = filepath.EvalSymlinks(gitPath)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := New(Options{Repository: repository, GitPath: gitPath}); err != nil {
		t.Fatalf("direct Git path rejected: %v", err)
	}
	gitLink := filepath.Join(t.TempDir(), "git-link")
	if err := os.Symlink(gitPath, gitLink); err != nil {
		t.Fatal(err)
	}
	if _, err := New(Options{Repository: repository, GitPath: gitLink}); !errors.Is(err, ErrUnsafePath) {
		t.Fatalf("linked Git path error = %v", err)
	}
	repositoryLink := filepath.Join(t.TempDir(), "repository-link")
	if err := os.Symlink(repository, repositoryLink); err != nil {
		t.Fatal(err)
	}
	if _, err := New(Options{Repository: repositoryLink}); !errors.Is(err, ErrUnsafePath) {
		t.Fatalf("linked repository error = %v", err)
	}
	nonRepository, err := filepath.EvalSymlinks(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	if _, err := New(Options{Repository: nonRepository}); !errors.Is(err, ErrRepository) {
		t.Fatalf("non-repository error = %v", err)
	}
}

func TestResultAndParserReturnDefensiveCopies(t *testing.T) {
	source := []byte("report_schema: operational-report-v1\nphase: COPIES\noutcome: passed\n")
	result, err := Operational(context.Background(), OperationalRequest{
		RequestMetadata: RequestMetadata{Phase: "COPIES", Result: "passed", FinalGate: "gate"},
		Project:         "project", SourceName: "ops.txt", Source: source,
	}, nil)
	if err != nil {
		t.Fatal(err)
	}
	originalBytes := bytes.Clone(result.Bytes)
	originalPayload := bytes.Clone(result.Record.Payload)
	source[0] ^= 1
	result.Evidence["source"][0] ^= 1
	if !bytes.Equal(result.Record.Payload, originalPayload) || !bytes.Equal(result.Bytes, originalBytes) {
		t.Fatal("caller source or evidence aliases canonical result storage")
	}
	result.Record.Payload[0] ^= 1
	if !bytes.Equal(result.Bytes, originalBytes) {
		t.Fatal("record payload aliases canonical envelope bytes")
	}
	parsed, err := ParseRecords(originalBytes)
	if err != nil || len(parsed) != 1 {
		t.Fatalf("parse: records=%d err=%v", len(parsed), err)
	}
	originalBytes[0] ^= 1
	if !bytes.Equal(parsed[0].Payload, originalPayload) {
		t.Fatal("parsed payload aliases caller content")
	}
}

func TestServiceSupportsConcurrentIndependentShowCalls(t *testing.T) {
	repository, environment := newGitRepository(t)
	writeFileTest(t, filepath.Join(repository, "tracked.txt"), []byte("tracked\n"))
	runGitTest(t, repository, nil, "add", "tracked.txt")
	commit := commitTest(t, repository, environment, "root", "", false)
	service, err := New(Options{Repository: repository})
	if err != nil {
		t.Fatal(err)
	}
	const calls = 4
	results := make(chan []byte, calls)
	errorsChannel := make(chan error, calls)
	var group sync.WaitGroup
	for index := 0; index < calls; index++ {
		group.Add(1)
		go func() {
			defer group.Done()
			result, callErr := service.Show(context.Background(), ShowRequest{
				RequestMetadata: RequestMetadata{Phase: "CONCURRENT", Result: "passed", FinalGate: "gate"},
				Commit:          commit, StatusDoc: "status.md",
			})
			if callErr != nil {
				errorsChannel <- callErr
				return
			}
			results <- result.Bytes
		}()
	}
	group.Wait()
	close(results)
	close(errorsChannel)
	for callErr := range errorsChannel {
		t.Fatal(callErr)
	}
	var reference []byte
	for content := range results {
		if reference == nil {
			reference = content
		} else if !bytes.Equal(reference, content) {
			t.Fatal("concurrent show results differ")
		}
	}
}

func TestExternalModuleImportsAndUsesReport(t *testing.T) {
	repository, environment := newGitRepository(t)
	writeFileTest(t, filepath.Join(repository, "tracked.txt"), []byte("tracked\n"))
	runGitTest(t, repository, nil, "add", "tracked.txt")
	commit := commitTest(t, repository, environment, "root", "", false)
	module := t.TempDir()
	root := repositoryRootForTest(t)
	goMod := "module example.invalid/apg95-consumer\n\ngo 1.25\n\nrequire github.com/Knowledge-Forge-AI/agentic-praxis-grimoire v0.0.0\n\nreplace github.com/Knowledge-Forge-AI/agentic-praxis-grimoire => " + root + "\n"
	program := `package main

import (
	"context"
	"os"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/report"
)

func main() {
	service, err := report.New(report.Options{Repository: os.Getenv("APG95_REPOSITORY")})
	if err != nil { panic(err) }
	result, err := service.Show(context.Background(), report.ShowRequest{
		RequestMetadata: report.RequestMetadata{Phase: "CONSUMER", Result: "passed", FinalGate: "gate"},
		Commit: os.Getenv("APG95_COMMIT"), StatusDoc: "status.md",
	})
	if err != nil { panic(err) }
	records, err := report.ParseRecords(result.Bytes)
	if err != nil || len(records) != 1 || records[0].ID != result.Record.ID { panic("record round trip failed") }
	_, _ = os.Stdout.Write([]byte(result.Record.ID + "\n"))
}
`
	if strings.Contains(program, "os/exec") || strings.Contains(program, "cmd/apgr") || strings.Contains(program, "Python") {
		t.Fatal("external consumer crosses the accepted boundary")
	}
	if err := os.WriteFile(filepath.Join(module, "go.mod"), []byte(goMod), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(module, "main.go"), []byte(program), 0o600); err != nil {
		t.Fatal(err)
	}
	command := exec.Command("go", "run", ".")
	command.Dir = module
	command.Env = append(os.Environ(), "APG95_REPOSITORY="+repository, "APG95_COMMIT="+commit)
	output, err := command.CombinedOutput()
	if err != nil {
		t.Fatalf("external consumer failed: %v\n%s", err, output)
	}
	if !strings.HasPrefix(string(output), "GIT-SHOW-REPORT-"+commit) {
		t.Fatalf("external consumer output = %q", output)
	}
}
