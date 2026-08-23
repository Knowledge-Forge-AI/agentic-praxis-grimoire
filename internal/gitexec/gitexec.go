// Package gitexec owns bounded, exact-argument native Git execution.
package gitexec

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
)

const (
	maxStdout = 64 << 20
	maxStderr = 64 << 10
)

var errOutputLimit = errors.New("git output exceeded bounded capture")

// Runner executes one validated Git executable at one exact repository root.
type Runner struct {
	root string
	path string
}

// Result contains the bounded raw process result.
type Result struct {
	Stdout   []byte
	Stderr   []byte
	ExitCode int
}

// New constructs a native Git runner. Path validation belongs to report.New.
func New(root, path string) Runner {
	return Runner{root: root, path: path}
}

// Run invokes Git using an exact argument vector and no shell. Environment
// overrides are layered onto the inherited process environment.
func (runner Runner) Run(ctx context.Context, arguments []string, environment map[string]string, input []byte) (Result, error) {
	if err := ctx.Err(); err != nil {
		return Result{}, err
	}
	argv := make([]string, 0, len(arguments)+3)
	argv = append(argv, "-C", runner.root, "--no-pager")
	argv = append(argv, arguments...)
	command := exec.CommandContext(ctx, runner.path, argv...)
	command.Env = childEnvironment(environment)
	if input == nil {
		command.Stdin = nil
	} else {
		command.Stdin = bytes.NewReader(input)
	}
	stdout := newLimitedBuffer(maxStdout)
	stderr := newLimitedBuffer(maxStderr)
	command.Stdout = stdout
	command.Stderr = stderr
	err := command.Run()
	result := Result{Stdout: stdout.Bytes(), Stderr: stderr.Bytes(), ExitCode: 0}
	if stdout.Err() != nil || stderr.Err() != nil {
		return result, errOutputLimit
	}
	if err == nil {
		return result, nil
	}
	if contextErr := ctx.Err(); contextErr != nil {
		return result, contextErr
	}
	var exitError *exec.ExitError
	if errors.As(err, &exitError) {
		result.ExitCode = exitError.ExitCode()
		return result, fmt.Errorf("git command failed: %w", err)
	}
	return result, fmt.Errorf("git execution failed: %w", err)
}

func childEnvironment(overrides map[string]string) []string {
	values := map[string]string{}
	for _, entry := range os.Environ() {
		for index := 0; index < len(entry); index++ {
			if entry[index] == '=' {
				values[entry[:index]] = entry[index+1:]
				break
			}
		}
	}
	values["LC_ALL"] = "C"
	values["LANG"] = "C"
	values["GIT_PAGER"] = "cat"
	values["PAGER"] = "cat"
	values["GIT_OPTIONAL_LOCKS"] = "0"
	for key, value := range overrides {
		values[key] = value
	}
	result := make([]string, 0, len(values))
	for key, value := range values {
		result = append(result, key+"="+value)
	}
	return result
}

type limitedBuffer struct {
	buffer bytes.Buffer
	limit  int
	err    error
}

func newLimitedBuffer(limit int) *limitedBuffer {
	return &limitedBuffer{limit: limit}
}

func (buffer *limitedBuffer) Write(payload []byte) (int, error) {
	if buffer.err != nil {
		return 0, buffer.err
	}
	remaining := buffer.limit - buffer.buffer.Len()
	if len(payload) > remaining {
		if remaining > 0 {
			_, _ = buffer.buffer.Write(payload[:remaining])
		}
		buffer.err = errOutputLimit
		return len(payload), nil
	}
	return buffer.buffer.Write(payload)
}

func (buffer *limitedBuffer) Bytes() []byte {
	return bytes.Clone(buffer.buffer.Bytes())
}

func (buffer *limitedBuffer) Err() error {
	return buffer.err
}

var _ io.Writer = (*limitedBuffer)(nil)
