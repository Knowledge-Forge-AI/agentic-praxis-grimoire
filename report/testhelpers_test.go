package report

import (
	"bytes"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func repositoryRootForTest(t *testing.T) string {
	t.Helper()
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("cannot locate report test source")
	}
	return filepath.Dir(filepath.Dir(file))
}

func newGitRepository(t *testing.T) (string, []string) {
	t.Helper()
	base, err := filepath.EvalSymlinks(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	repository := filepath.Join(base, "repository")
	if err := os.Mkdir(repository, 0o700); err != nil {
		t.Fatal(err)
	}
	runGitTest(t, repository, nil, "init", "-q", "-b", "main")
	runGitTest(t, repository, nil, "config", "user.name", "Report Author")
	runGitTest(t, repository, nil, "config", "user.email", "report@example.invalid")
	environment := append(os.Environ(),
		"GIT_AUTHOR_DATE=2030-01-02T03:04:05+00:00",
		"GIT_COMMITTER_DATE=2030-01-02T03:04:05+00:00",
	)
	return repository, environment
}

func runGitTest(t *testing.T, repository string, environment []string, arguments ...string) []byte {
	t.Helper()
	command := exec.Command("git", append([]string{"-C", repository}, arguments...)...)
	if environment != nil {
		command.Env = environment
	}
	output, err := command.CombinedOutput()
	if err != nil {
		t.Fatalf("git %s failed: %v\n%s", strings.Join(arguments, " "), err, output)
	}
	return output
}

func commitTest(t *testing.T, repository string, environment []string, subject, body string, allowEmpty bool) string {
	t.Helper()
	arguments := []string{"commit", "-q"}
	if allowEmpty {
		arguments = append(arguments, "--allow-empty")
	}
	arguments = append(arguments, "-m", subject)
	if body != "" {
		arguments = append(arguments, "-m", body)
	}
	runGitTest(t, repository, environment, arguments...)
	return strings.TrimSpace(string(runGitTest(t, repository, nil, "rev-parse", "HEAD")))
}

func writeFileTest(t *testing.T, path string, content []byte) {
	t.Helper()
	if err := os.WriteFile(path, content, 0o600); err != nil {
		t.Fatal(err)
	}
}

func pythonCommandTest(t *testing.T, repository, commandName, outbox string, arguments ...string) (int, []byte) {
	t.Helper()
	commandPath := filepath.Join(repositoryRootForTest(t), "report", "testdata", "python_oracle.py")
	if _, err := os.Stat(commandPath); err != nil {
		t.Skipf("differential python oracle %s is absent in this source projection (%v)", commandPath, err)
	}
	python, err := exec.LookPath("python3")
	if err != nil {
		t.Skipf("python3 is not available on PATH (%v)", err)
	}
	command := exec.Command(python, append([]string{commandPath, commandName}, arguments...)...)
	command.Dir = repository
	command.Env = filteredEnvironment("GIT_SHOW_REPORT_ROOT", "APGR_OUTBOX_ROOT")
	command.Env = append(command.Env, "APGR_OUTBOX_ROOT="+outbox)
	output, runErr := command.CombinedOutput()
	if runErr == nil {
		return 0, output
	}
	if exitError, ok := runErr.(*exec.ExitError); ok {
		return exitError.ExitCode(), output
	}
	return -1, output
}

func filteredEnvironment(names ...string) []string {
	blocked := map[string]bool{}
	for _, name := range names {
		blocked[name] = true
	}
	result := []string{}
	for _, entry := range os.Environ() {
		name := entry
		if index := strings.IndexByte(entry, '='); index >= 0 {
			name = entry[:index]
		}
		if !blocked[name] {
			result = append(result, entry)
		}
	}
	return result
}

func canonicalPythonPath(outbox, repository, phase, kind string) string {
	return filepath.Join(outbox, filepath.Base(repository), phase, phase+"."+kind+".report.txt")
}

func assertBytesEqual(t *testing.T, want, got []byte) {
	t.Helper()
	if bytes.Equal(want, got) {
		return
	}
	limit := len(want)
	if len(got) < limit {
		limit = len(got)
	}
	index := 0
	for index < limit && want[index] == got[index] {
		index++
	}
	t.Fatalf("canonical bytes differ at offset %d (want=%d bytes got=%d bytes)", index, len(want), len(got))
}
