package hotspot

import (
	"bufio"
	"context"
	"crypto/sha1"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"os/exec"
	"strconv"
	"strings"
	"sync"
)

// gitBlobReader provides bounded streaming blob reads via git cat-file --batch.
type gitBlobReader struct {
	cmd             *exec.Cmd
	stdin           io.WriteCloser
	stdout          io.ReadCloser
	reader          *bufio.Reader
	limits          HistoryLimits
	cache           map[string][]byte
	totalBlobsRead  int
	totalInputBytes int64
	objectFormat    string
	broken          bool
	closeOnce       sync.Once
}

func newGitBlobReader(ctx context.Context, gc *gitContext, limits HistoryLimits) (*gitBlobReader, error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}

	cmdArgs := []string{
		"-c", "protocol.allow=never",
		"-c", "protocol.file.allow=never",
		"-c", "protocol.http.allow=never",
		"-c", "protocol.https.allow=never",
		"-c", "protocol.ssh.allow=never",
		"-c", "protocol.git.allow=never",
		"-c", "protocol.ext.allow=never",
		"-c", "core.useReplaceRefs=false",
		"cat-file", "--batch",
	}
	cmd := exec.CommandContext(ctx, gc.gitPath, cmdArgs...)
	cmd.Dir = gc.root
	cmd.Env = gc.env

	stdin, err := cmd.StdinPipe()
	if err != nil {
		return nil, fmt.Errorf("failed to open stdin pipe for cat-file: %w", err)
	}
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		_ = stdin.Close()
		return nil, fmt.Errorf("failed to open stdout pipe for cat-file: %w", err)
	}

	if err := cmd.Start(); err != nil {
		_ = stdin.Close()
		_ = stdout.Close()
		if ctx.Err() != nil {
			return nil, ctx.Err()
		}
		return nil, fmt.Errorf("failed to start git cat-file: %w", err)
	}

	return &gitBlobReader{
		cmd:          cmd,
		stdin:        stdin,
		stdout:       stdout,
		reader:       bufio.NewReader(stdout),
		limits:       limits,
		cache:        make(map[string][]byte),
		objectFormat: gc.objectFormat,
	}, nil
}

func (br *gitBlobReader) markBrokenAndKill() {
	br.broken = true
	if br.stdin != nil {
		_ = br.stdin.Close()
		br.stdin = nil
	}
	if br.cmd != nil && br.cmd.Process != nil {
		_ = br.cmd.Process.Kill()
	}
}

func (br *gitBlobReader) readBlob(oid string) ([]byte, error) {
	if oid == "" || isZeroOID(oid, br.objectFormat) {
		return nil, nil
	}
	if !isValidOID(oid, br.objectFormat) {
		return nil, fmt.Errorf("invalid blob OID %q", oid)
	}
	if data, ok := br.cache[oid]; ok {
		return data, nil
	}
	if br.broken {
		return nil, errors.New("blob reader is closed or corrupted")
	}

	if _, err := fmt.Fprintf(br.stdin, "%s\n", oid); err != nil {
		br.markBrokenAndKill()
		return nil, fmt.Errorf("failed to write to cat-file stdin: %w", err)
	}

	header, err := br.reader.ReadString('\n')
	if err != nil {
		br.markBrokenAndKill()
		return nil, fmt.Errorf("failed to read cat-file header for %s: %w", oid, err)
	}

	header = strings.TrimRight(header, "\r\n")
	if strings.HasSuffix(header, " missing") {
		return nil, fmt.Errorf("blob object %s is missing", oid)
	}

	fields := strings.Fields(header)
	if len(fields) != 3 {
		br.markBrokenAndKill()
		return nil, fmt.Errorf("unexpected cat-file response for %s: %s", oid, header)
	}

	if fields[0] != oid {
		br.markBrokenAndKill()
		return nil, fmt.Errorf("cat-file header oid %q does not match requested oid %q", fields[0], oid)
	}
	if fields[1] != "blob" {
		br.markBrokenAndKill()
		return nil, fmt.Errorf("unexpected cat-file object type for %s: expected blob, got %s", oid, fields[1])
	}

	size, err := strconv.ParseInt(fields[2], 10, 64)
	if err != nil || size < 0 {
		br.markBrokenAndKill()
		return nil, fmt.Errorf("invalid blob size %q for %s: %w", fields[2], oid, err)
	}

	if size > br.limits.MaxBlobBytes {
		br.markBrokenAndKill()
		return nil, fmt.Errorf("history limit exceeded: blob size (%d bytes) exceeds limit (%d bytes)", size, br.limits.MaxBlobBytes)
	}
	if br.totalInputBytes+size > br.limits.MaxTotalInputBytes {
		br.markBrokenAndKill()
		return nil, fmt.Errorf("history limit exceeded: total input bytes (%d) exceeds limit (%d)", br.totalInputBytes+size, br.limits.MaxTotalInputBytes)
	}

	data := make([]byte, size)
	if _, err := io.ReadFull(br.reader, data); err != nil {
		br.markBrokenAndKill()
		return nil, fmt.Errorf("failed to read blob content for %s: %w", oid, err)
	}

	delim, err := br.reader.ReadByte()
	if err != nil {
		br.markBrokenAndKill()
		return nil, fmt.Errorf("failed to read cat-file newline delimiter for %s: %w", oid, err)
	}
	if delim != '\n' {
		br.markBrokenAndKill()
		return nil, fmt.Errorf("invalid cat-file trailing delimiter %q for %s: expected newline", delim, oid)
	}

	if !blobIdentityMatches(oid, data, br.objectFormat) {
		br.markBrokenAndKill()
		return nil, errors.New("blob content does not match object identity")
	}
	br.totalBlobsRead++
	br.totalInputBytes += size
	br.cache[oid] = data
	return data, nil
}

func (br *gitBlobReader) close() {
	br.closeOnce.Do(func() {
		if br.stdin != nil {
			_ = br.stdin.Close()
			br.stdin = nil
		}
		if br.broken && br.cmd != nil && br.cmd.Process != nil {
			_ = br.cmd.Process.Kill()
		}
		if br.stdout != nil {
			_ = br.stdout.Close()
			br.stdout = nil
		}
		if br.cmd != nil && br.cmd.Process != nil {
			_ = br.cmd.Wait()
		}
	})
}

func blobIdentityMatches(oid string, data []byte, format string) bool {
	prefix := []byte(fmt.Sprintf("blob %d%c", len(data), 0))
	if format == "sha256" {
		h := sha256.New()
		h.Write(prefix)
		h.Write(data)
		return hex.EncodeToString(h.Sum(nil)) == oid
	}
	h := sha1.New()
	h.Write(prefix)
	h.Write(data)
	return hex.EncodeToString(h.Sum(nil)) == oid
}
