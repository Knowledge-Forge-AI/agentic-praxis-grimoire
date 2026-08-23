package skills

import (
	"bytes"
	"context"
	"errors"
	"io/fs"
	"os"
	"path/filepath"
	"sync"
	"syscall"
	"testing"
)

func TestMaterializeExactPrivateFlattenedBundle(t *testing.T) {
	request := baseRequest("chatgpt-manager-workflow", "composing-approved-roadmap-assignments")
	request.Consumer = Consumer{Kind: ConsumerChatGPT, MaterializationForm: MaterializationFlatDirectory}
	result, err := Resolve(context.Background(), request)
	if err != nil {
		t.Fatal(err)
	}
	parent := privateParent(t)
	materialized, err := Materialize(context.Background(), MaterializeRequest{DestinationParent: parent, Result: result})
	if err != nil {
		t.Fatal(err)
	}
	rootInfo, err := os.Lstat(materialized.Root)
	if err != nil || rootInfo.Mode().Perm() != 0o700 || rootInfo.Mode()&os.ModeSymlink != 0 {
		t.Fatalf("root = %v, %v", rootInfo, err)
	}
	for _, id := range result.SelectedSkillIDs {
		path := filepath.Join(materialized.Root, id, "SKILL.md")
		info, statErr := os.Lstat(path)
		if statErr != nil || !info.Mode().IsRegular() || info.Mode().Perm() != 0o600 || info.Mode()&os.ModeSymlink != 0 {
			t.Fatalf("%s = %v, %v", id, info, statErr)
		}
		stat := info.Sys().(*syscall.Stat_t)
		if stat.Nlink != 1 {
			t.Fatalf("%s links = %d", id, stat.Nlink)
		}
		body, readErr := os.ReadFile(path)
		if readErr != nil || !bytes.Equal(body, skillBody(t, id)) {
			t.Fatalf("%s body mismatch: %v", id, readErr)
		}
	}
	if _, err := os.Stat(filepath.Join(materialized.Root, "chatgpt")); !os.IsNotExist(err) {
		t.Fatal("canonical ChatGPT namespace leaked into flattened root")
	}
	entries, err := os.ReadDir(materialized.Root)
	if err != nil || len(entries) != len(result.SelectedSkillIDs)+1 {
		t.Fatalf("root entries = %v, %v", entries, err)
	}
	manifest, err := os.ReadFile(filepath.Join(materialized.Root, ManifestFilename))
	if err != nil || sha256Hex(manifest) != materialized.ManifestFingerprint {
		t.Fatalf("manifest = %v", err)
	}
	manifestInfo, err := os.Lstat(filepath.Join(materialized.Root, ManifestFilename))
	if err != nil || !manifestInfo.Mode().IsRegular() || manifestInfo.Mode().Perm() != 0o600 || manifestInfo.Sys().(*syscall.Stat_t).Nlink != 1 {
		t.Fatalf("manifest metadata = %v, %v", manifestInfo, err)
	}
}

func TestMaterializeRefusalsIdempotenceAndConcurrency(t *testing.T) {
	inMemory, err := Resolve(context.Background(), baseRequest("planning-repository-work"))
	if err != nil {
		t.Fatal(err)
	}
	if _, err := Materialize(context.Background(), MaterializeRequest{DestinationParent: privateParent(t), Result: inMemory}); !errors.Is(err, ErrInvalidResult) {
		t.Fatalf("in-memory result = %v", err)
	}

	result, err := Resolve(context.Background(), flatRequest("planning-repository-work"))
	if err != nil {
		t.Fatal(err)
	}
	parent := privateParent(t)
	first, err := Materialize(context.Background(), MaterializeRequest{DestinationParent: parent, Result: result})
	if err != nil {
		t.Fatal(err)
	}
	second, err := Materialize(context.Background(), MaterializeRequest{DestinationParent: parent, Result: result})
	if err != nil || !second.Reused || first.Root != second.Root {
		t.Fatalf("idempotent = %#v, %v", second, err)
	}

	tampered := result
	tampered.SelectedSkills = append([]SelectedSkill(nil), result.SelectedSkills...)
	tampered.SelectedSkills[0].BodySHA256 = stringsOf('a', 64)
	if _, err = Materialize(context.Background(), MaterializeRequest{DestinationParent: parent, Result: tampered}); !errors.Is(err, ErrInvalidResult) {
		t.Fatalf("tampered = %v", err)
	}
	stale := result
	stale.EmbeddedCorpusFingerprint = stringsOf('b', 64)
	stale.BundleFingerprint, err = resultFingerprint(stale)
	if err != nil {
		t.Fatal(err)
	}
	if _, err = Materialize(context.Background(), MaterializeRequest{DestinationParent: parent, Result: stale}); !errors.Is(err, ErrInvalidResult) {
		t.Fatalf("stale corpus = %v", err)
	}
	rejected := result
	rejected.Budget.DescriptionBytes.Passed = false
	rejected.BundleFingerprint, err = resultFingerprint(rejected)
	if err != nil {
		t.Fatal(err)
	}
	if _, err = Materialize(context.Background(), MaterializeRequest{DestinationParent: parent, Result: rejected}); !errors.Is(err, ErrInvalidResult) {
		t.Fatalf("rejected budget = %v", err)
	}
	unknownConsumer := result
	unknownConsumer.ConsumerKind = "unknown"
	unknownConsumer.BundleFingerprint, err = resultFingerprint(unknownConsumer)
	if err != nil {
		t.Fatal(err)
	}
	if _, err = Materialize(context.Background(), MaterializeRequest{DestinationParent: parent, Result: unknownConsumer}); !errors.Is(err, ErrInvalidResult) {
		t.Fatalf("unknown consumer = %v", err)
	}
	noncanonical := result
	noncanonical.Exclusions = nil
	noncanonical.BundleFingerprint, err = resultFingerprint(noncanonical)
	if err != nil {
		t.Fatal(err)
	}
	if _, err = Materialize(context.Background(), MaterializeRequest{DestinationParent: parent, Result: noncanonical}); !errors.Is(err, ErrInvalidResult) {
		t.Fatalf("noncanonical collections = %v", err)
	}

	linkParent := filepath.Join(t.TempDir(), "parent-link")
	if err := os.Symlink(parent, linkParent); err != nil {
		t.Fatal(err)
	}
	if _, err = Materialize(context.Background(), MaterializeRequest{DestinationParent: linkParent, Result: result}); !errors.Is(err, ErrUnsafeDestination) {
		t.Fatalf("symlink parent = %v", err)
	}

	otherParent := privateParent(t)
	sentinel := filepath.Join(filepath.Dir(otherParent), "invocation-unowned-sentinel")
	if err := os.WriteFile(sentinel, []byte("preserve"), 0o600); err != nil {
		t.Fatal(err)
	}
	final := filepath.Join(otherParent, materializedBasename(result.BundleFingerprint))
	if err := os.Mkdir(final, 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(final, "unrelated"), []byte("x"), 0o600); err != nil {
		t.Fatal(err)
	}
	if _, err = Materialize(context.Background(), MaterializeRequest{DestinationParent: otherParent, Result: result}); !errors.Is(err, ErrCollision) {
		t.Fatalf("collision = %v", err)
	}
	if content, readErr := os.ReadFile(sentinel); readErr != nil || string(content) != "preserve" {
		t.Fatalf("unowned sibling changed: %q %v", content, readErr)
	}

	concurrentParent := privateParent(t)
	var wait sync.WaitGroup
	errorsSeen := make(chan error, 2)
	results := make(chan Materialization, 2)
	for range 2 {
		wait.Add(1)
		go func() {
			defer wait.Done()
			value, callErr := Materialize(context.Background(), MaterializeRequest{DestinationParent: concurrentParent, Result: result})
			results <- value
			errorsSeen <- callErr
		}()
	}
	wait.Wait()
	close(errorsSeen)
	close(results)
	for callErr := range errorsSeen {
		if callErr != nil {
			t.Fatal(callErr)
		}
	}
	var roots []string
	for value := range results {
		roots = append(roots, value.Root)
	}
	if len(roots) != 2 || roots[0] != roots[1] {
		t.Fatalf("concurrent roots = %v", roots)
	}
}

func TestMaterializeCancellationLeavesNoPartialRoot(t *testing.T) {
	result, err := Resolve(context.Background(), flatRequest("planning-repository-work", "go-language-profile"))
	if err != nil {
		t.Fatal(err)
	}
	for _, cancelAt := range []int{1, 4} {
		parent := privateParent(t)
		ctx := &countingCancelContext{Context: context.Background(), cancelAt: cancelAt}
		_, err := Materialize(ctx, MaterializeRequest{DestinationParent: parent, Result: result})
		if !errors.Is(err, context.Canceled) {
			t.Fatalf("cancel at %d = %v", cancelAt, err)
		}
		entries, readErr := os.ReadDir(parent)
		if readErr != nil || len(entries) != 0 {
			t.Fatalf("partial state at %d = %v, %v", cancelAt, entries, readErr)
		}
	}
}

type countingCancelContext struct {
	context.Context
	calls, cancelAt int
}

func (ctx *countingCancelContext) Err() error {
	ctx.calls++
	if ctx.calls >= ctx.cancelAt {
		return context.Canceled
	}
	return nil
}

func privateParent(t *testing.T) string {
	t.Helper()
	parent, err := filepath.EvalSymlinks(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	if err := os.Chmod(parent, 0o700); err != nil {
		t.Fatal(err)
	}
	return parent
}
func stringsOf(value byte, count int) string { return string(bytes.Repeat([]byte{value}, count)) }

func flatRequest(ids ...string) BundleRequest {
	request := baseRequest(ids...)
	request.Consumer.MaterializationForm = MaterializationFlatDirectory
	return request
}

func TestMaterializedRootHasNoSymlinksOrUnexpectedFiles(t *testing.T) {
	result, err := Resolve(context.Background(), flatRequest("planning-repository-work"))
	if err != nil {
		t.Fatal(err)
	}
	value, err := Materialize(context.Background(), MaterializeRequest{DestinationParent: privateParent(t), Result: result})
	if err != nil {
		t.Fatal(err)
	}
	err = filepath.WalkDir(value.Root, func(path string, entry fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		info, statErr := os.Lstat(path)
		if statErr != nil {
			return statErr
		}
		if info.Mode()&os.ModeSymlink != 0 {
			t.Fatalf("symlink %s", filepath.Base(path))
		}
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
}

func TestDecodeBundleResultRefusesNestedDuplicatesAndUnknownFields(t *testing.T) {
	result, err := Resolve(context.Background(), flatRequest("planning-repository-work"))
	if err != nil {
		t.Fatal(err)
	}
	content, err := result.CanonicalJSON()
	if err != nil {
		t.Fatal(err)
	}
	duplicate := bytes.Replace(content, []byte(`"body_bytes":`), []byte(`"body_bytes":0,"body_bytes":`), 1)
	if _, err := DecodeBundleResult(duplicate); !errors.Is(err, ErrInvalidResult) {
		t.Fatalf("nested duplicate = %v", err)
	}
	unknown := bytes.Replace(content, []byte(`"selected_skills":`), []byte(`"unknown":0,"selected_skills":`), 1)
	if _, err := DecodeBundleResult(unknown); !errors.Is(err, ErrInvalidResult) {
		t.Fatalf("unknown field = %v", err)
	}
	spaced := bytes.Replace(content, []byte(`,"bundle_fingerprint"`), []byte(`, "bundle_fingerprint"`), 1)
	if _, err := DecodeBundleResult(spaced); !errors.Is(err, ErrInvalidResult) {
		t.Fatalf("noncanonical whitespace = %v", err)
	}
}
