package report

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/schema"
)

var stateKeys = []string{"head", "index", "status", "staged", "unstaged", "changed", "numstat", "patch"}

type realObservation struct {
	head, indexFingerprint, indexIdentity string
	status, staged, unstaged              []byte
}

type worktreeSnapshot struct {
	changed, numstatRaw, patch []byte
}

type framedDiffEvidence struct {
	status, staged, unstaged, changed, numstat, patch []byte
}

func (service *Service) diff(ctx context.Context, request DiffRequest) (Result, error) {
	if err := validateRequestMetadata(request.RequestMetadata); err != nil {
		return Result{}, err
	}
	statusDoc, err := validateStatusDoc(request.StatusDoc, true)
	if err != nil {
		return Result{}, err
	}
	if _, present := os.LookupEnv("GIT_INDEX_FILE"); present {
		return Result{}, fmt.Errorf("%w: inherited GIT_INDEX_FILE", ErrUnsupported)
	}
	indexPath, indexMode, err := service.supportedIndex(ctx)
	if err != nil {
		return Result{}, err
	}
	pre, err := service.observeReal(ctx, indexPath)
	if err != nil {
		return Result{}, err
	}
	first, err := service.collectWorktreeSnapshot(ctx, indexPath, pre.head)
	if err != nil {
		return Result{}, err
	}
	if err := testPause(ctx, "before-post-drift-check"); err != nil {
		return Result{}, err
	}
	second, err := service.collectWorktreeSnapshot(ctx, indexPath, pre.head)
	if err != nil {
		return Result{}, err
	}
	post, err := service.observeReal(ctx, indexPath)
	if err != nil {
		return Result{}, err
	}
	if !equalObservation(pre, post) || !equalSnapshot(first, second) {
		return Result{}, fmt.Errorf("%w: repository evidence changed", ErrDrift)
	}
	if err := service.ensureSupportedStateStillPresent(ctx); err != nil {
		return Result{}, err
	}
	if len(first.patch) == 0 {
		return Result{}, fmt.Errorf("%w: no reportable change relative to HEAD", ErrInvalidRequest)
	}
	record, evidence, err := renderDiffRecord(request, statusDoc, projectName(service.repository), indexMode, pre, first)
	if err != nil {
		return Result{}, err
	}
	return resultFor(record, map[string][]byte{
		"head": []byte(pre.head), "index_fingerprint": []byte(pre.indexFingerprint), "index_identity": []byte(pre.indexIdentity),
		"status": evidence.status, "staged": evidence.staged, "unstaged": evidence.unstaged,
		"changed_files": evidence.changed, "numstat": evidence.numstat, "patch": evidence.patch,
	})
}

func (service *Service) supportedIndex(ctx context.Context) (string, string, error) {
	if result, err := service.runGitResult(ctx, []string{"rev-parse", "--verify", "HEAD^{commit}"}, nil, nil); ctx.Err() != nil {
		return "", "", ctx.Err()
	} else if err != nil || result.ExitCode != 0 {
		return "", "", fmt.Errorf("%w: unborn HEAD", ErrUnsupported)
	}
	split, splitErr := service.runGitResult(ctx, []string{"rev-parse", "--shared-index-path"}, nil, nil)
	if splitErr == nil && len(bytes.TrimSpace(split.Stdout)) != 0 {
		return "", "", fmt.Errorf("%w: split index", ErrUnsupported)
	}
	sparse, sparseErr := service.runGitResult(ctx, []string{"config", "--bool", "core.sparseCheckout"}, nil, nil)
	if sparseErr == nil && strings.EqualFold(strings.TrimSpace(string(sparse.Stdout)), "true") {
		return "", "", fmt.Errorf("%w: sparse index", ErrUnsupported)
	}
	sparseEntries, err := service.runGit(ctx, []string{"ls-files", "--sparse", "-z"}, nil, nil, ErrRepository)
	if err != nil {
		return "", "", err
	}
	for _, entry := range bytes.Split(sparseEntries, []byte{0}) {
		if bytes.HasSuffix(entry, []byte("/")) {
			return "", "", fmt.Errorf("%w: sparse index", ErrUnsupported)
		}
	}
	if err := service.ensureNoUnmerged(ctx); err != nil {
		return "", "", err
	}
	pathOutput, err := service.runGit(ctx, []string{"rev-parse", "--path-format=absolute", "--git-path", "index"}, nil, nil, ErrRepository)
	if err != nil {
		return "", "", err
	}
	path := strings.TrimSuffix(string(pathOutput), "\n")
	metadata, statErr := os.Lstat(path)
	if statErr == nil {
		if !metadata.Mode().IsRegular() || metadata.Mode()&os.ModeSymlink != 0 {
			return "", "", fmt.Errorf("%w: real index path", ErrUnsafePath)
		}
		return path, "regular", nil
	}
	if !os.IsNotExist(statErr) {
		return "", "", fmt.Errorf("%w: real index path", ErrUnsafePath)
	}
	return path, "missing-seeded-from-head", nil
}

func (service *Service) ensureNoUnmerged(ctx context.Context) error {
	output, err := service.runGit(ctx, []string{"ls-files", "--unmerged", "-z"}, nil, nil, ErrRepository)
	if err != nil {
		return err
	}
	if len(output) != 0 {
		return fmt.Errorf("%w: unmerged index entries", ErrUnsupported)
	}
	return nil
}

func (service *Service) ensureSupportedStateStillPresent(ctx context.Context) error {
	if err := service.ensureNoUnmerged(ctx); err != nil {
		return err
	}
	sparse, sparseErr := service.runGitResult(ctx, []string{"config", "--bool", "core.sparseCheckout"}, nil, nil)
	if sparseErr == nil && strings.EqualFold(strings.TrimSpace(string(sparse.Stdout)), "true") {
		return fmt.Errorf("%w: sparse configuration changed", ErrDrift)
	}
	return nil
}

func (service *Service) observeReal(ctx context.Context, indexPath string) (realObservation, error) {
	headOutput, err := service.runGit(ctx, []string{"rev-parse", "--verify", "HEAD^{commit}"}, nil, nil, ErrRepository)
	if err != nil {
		return realObservation{}, err
	}
	head := strings.ToLower(strings.TrimSpace(string(headOutput)))
	if !hexCommitPattern.MatchString(head) {
		return realObservation{}, fmt.Errorf("%w: HEAD identity is malformed", ErrCompatibility)
	}
	fingerprint, identity, err := observeIndex(indexPath)
	if err != nil {
		return realObservation{}, err
	}
	status, err := service.runGit(ctx, []string{"status", "--porcelain=v2", "-z", "--untracked-files=all"}, nil, nil, ErrRepository)
	if err != nil {
		return realObservation{}, err
	}
	staged, err := service.runGit(ctx, []string{"-c", "core.quotePath=true", "diff", "--cached", "--name-status", "--find-renames", "--no-ext-diff", "--no-textconv", "HEAD"}, nil, nil, ErrRepository)
	if err != nil {
		return realObservation{}, err
	}
	unstaged, err := service.runGit(ctx, []string{"-c", "core.quotePath=true", "diff", "--name-status", "--find-renames", "--no-ext-diff", "--no-textconv"}, nil, nil, ErrRepository)
	if err != nil {
		return realObservation{}, err
	}
	return realObservation{head: head, indexFingerprint: fingerprint, indexIdentity: identity, status: status, staged: staged, unstaged: unstaged}, nil
}

func observeIndex(path string) (string, string, error) {
	before, err := os.Lstat(path)
	if os.IsNotExist(err) {
		return "MISSING", "MISSING", nil
	}
	if err != nil || !before.Mode().IsRegular() || before.Mode()&os.ModeSymlink != 0 {
		return "", "", fmt.Errorf("%w: real index path", ErrUnsafePath)
	}
	beforeID, err := identityFor(before)
	if err != nil {
		return "", "", err
	}
	content, err := readDirectRegular(path, before)
	if err != nil {
		return "", "", err
	}
	after, err := os.Lstat(path)
	if err != nil {
		return "", "", fmt.Errorf("%w: real index changed during observation", ErrDrift)
	}
	afterID, err := identityFor(after)
	if err != nil {
		return "", "", err
	}
	if beforeID != afterID {
		return "", "", fmt.Errorf("%w: real index changed during observation", ErrDrift)
	}
	identityHash := schema.SHA256([]byte(beforeID.String()))
	return "sha256:" + schema.SHA256(content) + ";size:" + strconv.FormatInt(beforeID.size, 10), "sha256:" + identityHash, nil
}

func readDirectRegular(path string, expected os.FileInfo) ([]byte, error) {
	file, err := os.OpenFile(path, os.O_RDONLY|syscall.O_NOFOLLOW, 0)
	if err != nil {
		return nil, fmt.Errorf("%w: direct regular read failed", ErrUnsafePath)
	}
	defer file.Close()
	opened, err := file.Stat()
	if err != nil || !opened.Mode().IsRegular() {
		return nil, fmt.Errorf("%w: direct regular read failed", ErrUnsafePath)
	}
	expectedID, expectedErr := identityFor(expected)
	openedID, openedErr := identityFor(opened)
	if expectedErr != nil || openedErr != nil || expectedID != openedID {
		return nil, fmt.Errorf("%w: direct regular identity changed", ErrUnsafePath)
	}
	content, err := io.ReadAll(io.LimitReader(file, 128<<20))
	if err != nil {
		return nil, fmt.Errorf("%w: direct regular read failed", ErrUnsafePath)
	}
	return content, nil
}

func (service *Service) collectWorktreeSnapshot(ctx context.Context, indexPath, head string) (snapshot worktreeSnapshot, resultErr error) {
	temporary, err := os.MkdirTemp("", "git-diff-index.")
	if err != nil {
		return worktreeSnapshot{}, fmt.Errorf("%w: private index directory", ErrUnsafePath)
	}
	if err := os.Chmod(temporary, 0o700); err != nil {
		_ = os.RemoveAll(temporary)
		return worktreeSnapshot{}, fmt.Errorf("%w: private index directory", ErrUnsafePath)
	}
	defer func() {
		if cleanupErr := os.RemoveAll(temporary); cleanupErr != nil && resultErr == nil {
			resultErr = fmt.Errorf("%w: private index cleanup", ErrUnsafePath)
		}
	}()
	privateIndex := filepath.Join(temporary, "index")
	if metadata, statErr := os.Lstat(indexPath); statErr == nil {
		content, readErr := readDirectRegular(indexPath, metadata)
		if readErr != nil {
			return worktreeSnapshot{}, readErr
		}
		if writeErr := os.WriteFile(privateIndex, content, 0o600); writeErr != nil {
			return worktreeSnapshot{}, fmt.Errorf("%w: private index copy", ErrUnsafePath)
		}
	} else if !os.IsNotExist(statErr) {
		return worktreeSnapshot{}, fmt.Errorf("%w: real index path", ErrUnsafePath)
	}
	environment := map[string]string{"GIT_INDEX_FILE": privateIndex, "GIT_OPTIONAL_LOCKS": "0"}
	if _, statErr := os.Lstat(indexPath); os.IsNotExist(statErr) {
		if _, err := service.runGit(ctx, []string{"read-tree", head}, environment, nil, ErrRepository); err != nil {
			return worktreeSnapshot{}, err
		}
		if err := os.Chmod(privateIndex, 0o600); err != nil {
			return worktreeSnapshot{}, fmt.Errorf("%w: private index mode", ErrUnsafePath)
		}
	}
	if _, err := service.runGit(ctx, []string{"add", "-N", "--", "."}, environment, nil, ErrRepository); err != nil {
		return worktreeSnapshot{}, err
	}
	if err := testPause(ctx, "private-index-ready"); err != nil {
		return worktreeSnapshot{}, err
	}
	common := []string{"--find-renames", "--no-ext-diff", "--no-textconv", head}
	changed, err := service.runGit(ctx, append([]string{"-c", "core.quotePath=true", "diff", "--name-status"}, common...), environment, nil, ErrRepository)
	if err != nil {
		return worktreeSnapshot{}, err
	}
	numstat, err := service.runGit(ctx, append([]string{"-c", "core.quotePath=true", "diff", "--numstat"}, common...), environment, nil, ErrRepository)
	if err != nil {
		return worktreeSnapshot{}, err
	}
	patch, err := service.runGit(ctx, []string{"-c", "core.quotePath=true", "diff", "--patch", "--full-index", "--find-renames", "--no-ext-diff", "--no-textconv", "--no-color", head}, environment, nil, ErrRepository)
	if err != nil {
		return worktreeSnapshot{}, err
	}
	return worktreeSnapshot{changed: changed, numstatRaw: numstat, patch: patch}, nil
}

func renderDiffRecord(request DiffRequest, statusDoc, project, indexMode string, observation realObservation, snapshot worktreeSnapshot) (Record, framedDiffEvidence, error) {
	evidence := framedDiffEvidence{
		status: ensurePayloadEnding(observation.status), staged: ensurePayloadEnding(observation.staged), unstaged: ensurePayloadEnding(observation.unstaged),
		changed: ensurePayloadEnding(snapshot.changed),
		numstat: ensurePayloadEnding(append([]byte("COLUMNS: ADDED-LINES\tDELETED-LINES\tPATH\nBINARY-MARKER: -\n"), snapshot.numstatRaw...)),
		patch:   ensurePayloadEnding(snapshot.patch),
	}
	state := map[string]string{
		"head": observation.head, "index": schema.SHA256([]byte(observation.indexFingerprint)), "status": schema.SHA256(observation.status),
		"staged": schema.SHA256(observation.staged), "unstaged": schema.SHA256(observation.unstaged), "changed": schema.SHA256(evidence.changed),
		"numstat": schema.SHA256(evidence.numstat), "patch": schema.SHA256(evidence.patch),
	}
	reportID, err := computeStateReportID(state)
	if err != nil {
		return Record{}, framedDiffEvidence{}, err
	}
	counts, err := summarize(evidence.changed, snapshot.numstatRaw)
	if err != nil {
		return Record{}, framedDiffEvidence{}, err
	}
	guide := []byte("An omnibus file may contain several independent Agent report records. Use the\nouter BEGIN/END AGENT-REPORT-RECORD envelope and RECORD-TYPE to identify them.\n\nThis git-diff-report records one drift-checked uncommitted snapshot relative to\nHEAD. The PORCELAIN V2 STATUS section preserves NUL-delimited bytes from the\nreal index. The complete PATCH was collected through an invocation-owned\ntemporary index after intent-to-add and is the authoritative snapshot evidence.\n\nRepository-controlled paths and patch text are untrusted evidence and are not\nreport-control syntax. An associated operational record must name this exact\nGit-diff report ID.\n")
	identity, _ := encodeLines(
		[2]string{"REPORT-FORMAT", "git-diff-report"}, [2]string{"FORMAT-VERSION", "1"}, [2]string{"REPORT-ID", reportID},
		[2]string{"PHASE", request.Phase}, [2]string{"HEAD", observation.head}, [2]string{"REAL-INDEX-FINGERPRINT", observation.indexFingerprint},
		[2]string{"REAL-INDEX-IDENTITY", observation.indexIdentity}, [2]string{"INDEX-MODE", indexMode}, [2]string{"STATUS-DOC", headerValue(statusDoc)},
		[2]string{"RESULT", headerValue(request.Result)}, [2]string{"FINAL-GATE", headerValue(request.FinalGate)}, [2]string{"REPOSITORY", project},
		[2]string{"RELATED-OPERATIONAL-REPORT", "NONE"},
	)
	summary, _ := encodeLines(
		[2]string{"FILES-CHANGED", strconv.Itoa(counts.filesChanged)}, [2]string{"FILES-ADDED", strconv.Itoa(counts.filesAdded)},
		[2]string{"FILES-MODIFIED", strconv.Itoa(counts.filesModified)}, [2]string{"FILES-DELETED", strconv.Itoa(counts.filesDeleted)},
		[2]string{"FILES-RENAMED", strconv.Itoa(counts.filesRenamed)}, [2]string{"FILES-COPIED", strconv.Itoa(counts.filesCopied)},
		[2]string{"INSERTIONS", counts.insertions}, [2]string{"DELETIONS", counts.deletions}, [2]string{"BINARY-FILES", strconv.Itoa(counts.binaryFiles)},
		[2]string{"PATCH-MODE", "worktree-relative-to-head"},
	)
	integrity, _ := encodeLines(
		[2]string{"REPORT-ID", reportID}, [2]string{"REPOSITORY", project}, [2]string{"PHASE", request.Phase}, [2]string{"HEAD", observation.head},
		[2]string{"REAL-INDEX-FINGERPRINT", observation.indexFingerprint}, [2]string{"REAL-INDEX-IDENTITY", observation.indexIdentity},
		[2]string{"PORCELAIN-V2-STATUS-SHA256", schema.SHA256(observation.status)}, [2]string{"STAGED-SUMMARY-SHA256", schema.SHA256(observation.staged)},
		[2]string{"UNSTAGED-SUMMARY-SHA256", schema.SHA256(observation.unstaged)}, [2]string{"CHANGED-FILES-SHA256", schema.SHA256(evidence.changed)},
		[2]string{"NUMSTAT-SHA256", schema.SHA256(evidence.numstat)}, [2]string{"PATCH-SHA256", schema.SHA256(evidence.patch)},
		[2]string{"PRE-POST-HEAD-MATCH", "true"}, [2]string{"PRE-POST-INDEX-MATCH", "true"}, [2]string{"PRE-POST-STATUS-MATCH", "true"},
		[2]string{"PRE-POST-STAGED-MATCH", "true"}, [2]string{"PRE-POST-UNSTAGED-MATCH", "true"}, [2]string{"PRE-POST-WORKTREE-MATCH", "true"},
		[2]string{"REAL-INDEX-AND-WORKTREE-MUTATED", "false"}, [2]string{"END-OF-PATCH-REACHED", "true"},
	)
	payload, err := joinSections(
		section{"READING GUIDE", guide}, section{"REPORT IDENTITY", identity}, section{"WORKTREE SUMMARY", summary},
		section{"PORCELAIN V2 STATUS (NUL DELIMITED)", evidence.status}, section{"STAGED SUMMARY", evidence.staged},
		section{"UNSTAGED SUMMARY", evidence.unstaged}, section{"CHANGED FILES", evidence.changed}, section{"NUMSTAT", evidence.numstat},
		section{"PATCH", evidence.patch}, section{"INTEGRITY SUMMARY", integrity},
	)
	if err != nil {
		return Record{}, framedDiffEvidence{}, err
	}
	return Record{Kind: schema.GitDiffRecord, FormatVersion: 1, ID: reportID, Project: project, Phase: request.Phase, Payload: payload}, evidence, nil
}

func computeStateReportID(fields map[string]string) (string, error) {
	if len(fields) != len(stateKeys) {
		return "", fmt.Errorf("%w: state identity fields are incomplete", ErrCompatibility)
	}
	digest := sha256.New()
	digest.Write([]byte("agent-report-git-diff-state-v1\x00"))
	for _, key := range stateKeys {
		value, ok := fields[key]
		if !ok || !isASCII(value) {
			return "", fmt.Errorf("%w: state identity fields are incomplete", ErrCompatibility)
		}
		digest.Write([]byte(key))
		digest.Write([]byte{0})
		digest.Write([]byte(value))
		digest.Write([]byte{0})
	}
	return "GIT-DIFF-REPORT-" + hex.EncodeToString(digest.Sum(nil)), nil
}

func equalObservation(left, right realObservation) bool {
	return left.head == right.head && left.indexFingerprint == right.indexFingerprint && left.indexIdentity == right.indexIdentity &&
		bytes.Equal(left.status, right.status) && bytes.Equal(left.staged, right.staged) && bytes.Equal(left.unstaged, right.unstaged)
}

func equalSnapshot(left, right worktreeSnapshot) bool {
	return bytes.Equal(left.changed, right.changed) && bytes.Equal(left.numstatRaw, right.numstatRaw) && bytes.Equal(left.patch, right.patch)
}

func testPause(ctx context.Context, step string) error {
	if os.Getenv("APG_REPORT_GO_TESTING") != "1" || os.Getenv("APG_REPORT_GO_TEST_PAUSE_STEP") != step {
		return nil
	}
	directory := os.Getenv("APG_REPORT_GO_TEST_SIGNAL_DIR")
	if directory == "" {
		return fmt.Errorf("%w: test pause signal directory is unavailable", ErrCompatibility)
	}
	if err := os.WriteFile(filepath.Join(directory, "ready"), []byte{}, 0o600); err != nil {
		return fmt.Errorf("%w: test pause signal unavailable", ErrCompatibility)
	}
	ticker := time.NewTicker(10 * time.Millisecond)
	defer ticker.Stop()
	timer := time.NewTimer(30 * time.Second)
	defer timer.Stop()
	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-ticker.C:
			if _, err := os.Stat(filepath.Join(directory, "continue")); err == nil {
				return nil
			}
		case <-timer.C:
			return fmt.Errorf("%w: test pause timed out", ErrCompatibility)
		}
	}
}
