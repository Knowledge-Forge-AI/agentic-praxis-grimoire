package response

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"syscall"
	"testing"
	"time"
)

func responseOptions(t *testing.T) (string, string, string) {
	t.Helper()
	root := filepath.Join(t.TempDir(), "outbox")
	return root, "project", "APG100"
}

func TestCapturePreservesExactStdinBytesAndPrivateModes(t *testing.T) {
	root, project, phase := responseOptions(t)
	body := []byte("# exact\n\x00\xff\n")
	path, err := Capture(context.Background(), Options{
		OutboxRoot: root,
		Project:    project,
		Phase:      phase,
		Stdin:      bytes.NewReader(body),
	})
	if err != nil {
		t.Fatal(err)
	}
	want := filepath.Join(root, project, phase, phase+".001.response.md")
	if path != want {
		t.Fatalf("path = %q, want %q", path, want)
	}
	content, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(content, body) {
		t.Fatalf("body = %x, want %x", content, body)
	}
	for name, mode := range map[string]os.FileMode{
		path:                             0o600,
		filepath.Dir(path):               0o700,
		filepath.Dir(filepath.Dir(path)): 0o700,
		filepath.Join(filepath.Dir(path), LockName): 0o600,
	} {
		metadata, statErr := os.Stat(name)
		if statErr != nil {
			t.Fatal(statErr)
		}
		if metadata.Mode().Perm() != mode {
			t.Errorf("%s mode = %o, want %o", name, metadata.Mode().Perm(), mode)
		}
	}
	reservations, err := ListReservations(filepath.Dir(path))
	if err != nil || len(reservations) != 0 {
		t.Fatalf("reservations = %v, err = %v", reservations, err)
	}
}

func TestCaptureFileInputEmptyBodyAndAliasesAllocateWithoutOverwrite(t *testing.T) {
	root, project, phase := responseOptions(t)
	source := filepath.Join(t.TempDir(), "response.md")
	firstBody := []byte("first\n")
	if err := os.WriteFile(source, firstBody, 0o600); err != nil {
		t.Fatal(err)
	}
	first, err := Capture(context.Background(), Options{OutboxRoot: root, Project: project, Phase: phase, InputPath: source})
	if err != nil {
		t.Fatal(err)
	}
	second, err := Record(context.Background(), Options{OutboxRoot: root, Project: project, Phase: phase, Body: []byte("second\n")})
	if err != nil {
		t.Fatal(err)
	}
	third, err := CaptureResponse(context.Background(), Options{OutboxRoot: root, Project: project, Phase: phase, Body: []byte{}})
	if err != nil {
		t.Fatal(err)
	}
	if filepath.Base(first) != phase+".001.response.md" || filepath.Base(second) != phase+".002.response.md" || filepath.Base(third) != phase+".003.response.md" {
		t.Fatalf("allocated paths = %q, %q, %q", first, second, third)
	}
	if content, err := os.ReadFile(first); err != nil || !bytes.Equal(content, firstBody) {
		t.Fatalf("first body = %q, err = %v", content, err)
	}
	if content, err := os.ReadFile(second); err != nil || string(content) != "second\n" {
		t.Fatalf("second body = %q, err = %v", content, err)
	}
	if content, err := os.ReadFile(third); err != nil || len(content) != 0 {
		t.Fatalf("empty body = %q, err = %v", content, err)
	}
}

func TestCaptureValidatesOneInputAndBoundedIdentities(t *testing.T) {
	root, project, phase := responseOptions(t)
	cases := []struct {
		name string
		call func() error
		want error
	}{
		{name: "no input", call: func() error {
			_, err := Capture(context.Background(), Options{OutboxRoot: root, Project: project, Phase: phase})
			return err
		}, want: ErrUsage},
		{name: "two inputs", call: func() error {
			_, err := Capture(context.Background(), Options{OutboxRoot: root, Project: project, Phase: phase, Body: []byte("body"), Stdin: bytes.NewReader(nil)})
			return err
		}, want: ErrUsage},
		{name: "relative root", call: func() error {
			_, err := Capture(context.Background(), Options{OutboxRoot: "relative", Project: project, Phase: phase, Body: []byte("body")})
			return err
		}, want: ErrUsage},
		{name: "unsafe phase", call: func() error {
			_, err := Capture(context.Background(), Options{OutboxRoot: root, Project: project, Phase: "bad/name", Body: []byte("body")})
			return err
		}, want: ErrUsage},
	}
	for _, testCase := range cases {
		t.Run(testCase.name, func(t *testing.T) {
			if err := testCase.call(); !errors.Is(err, testCase.want) {
				t.Fatalf("err = %v, want %v", err, testCase.want)
			}
		})
	}
	oversized := make([]byte, MaxResponseBytes+1)
	if _, err := Capture(context.Background(), Options{OutboxRoot: root, Project: project, Phase: phase, Body: oversized}); !errors.Is(err, ErrInput) {
		t.Fatalf("oversized err = %v", err)
	}
}

func TestCaptureRejectsFifoAndSymlinkInputWithoutWaiting(t *testing.T) {
	root, project, phase := responseOptions(t)
	fifo := filepath.Join(t.TempDir(), "response.fifo")
	if err := syscall.Mkfifo(fifo, 0o600); err != nil {
		t.Fatal(err)
	}
	started := time.Now()
	_, err := Capture(context.Background(), Options{OutboxRoot: root, Project: project, Phase: phase, InputPath: fifo})
	if !errors.Is(err, ErrInput) || !strings.Contains(err.Error(), "regular file") {
		t.Fatalf("fifo err = %v", err)
	}
	if time.Since(started) > time.Second {
		t.Fatal("fifo input blocked instead of being rejected")
	}
	target := filepath.Join(t.TempDir(), "target")
	if err := os.WriteFile(target, []byte("target"), 0o600); err != nil {
		t.Fatal(err)
	}
	symlink := filepath.Join(t.TempDir(), "response.md")
	if err := os.Symlink(target, symlink); err != nil {
		t.Fatal(err)
	}
	if _, err := Capture(context.Background(), Options{OutboxRoot: root, Project: project, Phase: phase, InputPath: symlink}); !errors.Is(err, ErrInput) {
		t.Fatalf("symlink err = %v", err)
	}
}

func TestCaptureSkipsExistingLinksAndCleansOwnerOrphan(t *testing.T) {
	root, project, phase := responseOptions(t)
	phaseDirectory, err := PhaseDirectory(root, project, phase)
	if err != nil {
		t.Fatal(err)
	}
	target := filepath.Join(t.TempDir(), "target")
	if err := os.WriteFile(target, []byte("keep"), 0o600); err != nil {
		t.Fatal(err)
	}
	first := filepath.Join(phaseDirectory, phase+".001.response.md")
	if err := os.Symlink(target, first); err != nil {
		t.Fatal(err)
	}
	orphan := filepath.Join(phaseDirectory, ".response-write.dead-process.tmp")
	if err := os.WriteFile(orphan, []byte("partial"), 0o600); err != nil {
		t.Fatal(err)
	}
	created, err := Capture(context.Background(), Options{OutboxRoot: root, Project: project, Phase: phase, Body: []byte("complete")})
	if err != nil {
		t.Fatal(err)
	}
	if filepath.Base(created) != phase+".002.response.md" {
		t.Fatalf("created = %q", created)
	}
	if _, err := os.Lstat(orphan); !os.IsNotExist(err) {
		t.Fatalf("orphan remains: %v", err)
	}
	if content, err := os.ReadFile(target); err != nil || string(content) != "keep" {
		t.Fatalf("symlink target = %q, err = %v", content, err)
	}
}

func TestReservationListingCleanupAndNumberBlocking(t *testing.T) {
	root, project, phase := responseOptions(t)
	phaseDirectory, err := PhaseDirectory(root, project, phase)
	if err != nil {
		t.Fatal(err)
	}
	reservation := filepath.Join(phaseDirectory, "."+phase+".001.response.md.reservation.foreign")
	if err := os.WriteFile(reservation, []byte("reservation-v1\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	reservations, err := ListReservations(phaseDirectory)
	if err != nil || len(reservations) != 1 || reservations[0] != reservation {
		t.Fatalf("reservations = %v, err = %v", reservations, err)
	}
	created, err := Capture(context.Background(), Options{OutboxRoot: root, Project: project, Phase: phase, Body: []byte("second")})
	if err != nil {
		t.Fatal(err)
	}
	if filepath.Base(created) != phase+".002.response.md" {
		t.Fatalf("created = %q", created)
	}
	if err := CleanReservation(reservation, root, project, phase); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Lstat(reservation); !os.IsNotExist(err) {
		t.Fatalf("reservation remains: %v", err)
	}
}

func TestCaptureExhaustionLeavesNoReservation(t *testing.T) {
	root, project, phase := responseOptions(t)
	phaseDirectory, err := PhaseDirectory(root, project, phase)
	if err != nil {
		t.Fatal(err)
	}
	for number := 1; number <= MaxResponseNumber; number++ {
		path := filepath.Join(phaseDirectory, fmt.Sprintf("%s.%03d.response.md", phase, number))
		if err := os.WriteFile(path, []byte("occupied"), 0o600); err != nil {
			t.Fatal(err)
		}
	}
	if _, err := Capture(context.Background(), Options{OutboxRoot: root, Project: project, Phase: phase, Body: []byte("unallocated")}); !errors.Is(err, ErrAllocation) {
		t.Fatalf("exhaustion err = %v", err)
	}
	reservations, err := ListReservations(phaseDirectory)
	if err != nil || len(reservations) != 0 {
		t.Fatalf("reservations after exhaustion = %v, err = %v", reservations, err)
	}
}

func TestConcurrentCapturesAllocateDistinctExactBodies(t *testing.T) {
	root, project, phase := responseOptions(t)
	const count = 24
	type result struct {
		path string
		err  error
		body []byte
	}
	results := make(chan result, count)
	for index := 0; index < count; index++ {
		body := []byte(fmt.Sprintf("response-%02d\n", index))
		go func(body []byte) {
			path, err := Capture(context.Background(), Options{OutboxRoot: root, Project: project, Phase: phase, Body: body})
			results <- result{path: path, err: err, body: body}
		}(body)
	}
	paths := make([]string, 0, count)
	for index := 0; index < count; index++ {
		value := <-results
		if value.err != nil {
			t.Fatal(value.err)
		}
		content, err := os.ReadFile(value.path)
		if err != nil || !bytes.Equal(content, value.body) {
			t.Fatalf("%s content = %q, err = %v", value.path, content, err)
		}
		paths = append(paths, filepath.Base(value.path))
	}
	sort.Strings(paths)
	for index, path := range paths {
		want := fmt.Sprintf("%s.%03d.response.md", phase, index+1)
		if path != want {
			t.Fatalf("path %d = %q, want %q", index, path, want)
		}
	}
}

func TestCaptureCancellationStopsLockWait(t *testing.T) {
	root, project, phase := responseOptions(t)
	phaseDirectory, err := PhaseDirectory(root, project, phase)
	if err != nil {
		t.Fatal(err)
	}
	holder, err := acquireLock(context.Background(), phaseDirectory)
	if err != nil {
		t.Fatal(err)
	}
	defer holder.release()
	ctx, cancel := context.WithTimeout(context.Background(), 40*time.Millisecond)
	defer cancel()
	_, err = Capture(ctx, Options{OutboxRoot: root, Project: project, Phase: phase, Body: []byte("cancelled")})
	if !errors.Is(err, context.DeadlineExceeded) {
		t.Fatalf("lock cancellation err = %v", err)
	}
	reservations, err := ListReservations(phaseDirectory)
	if err != nil || len(reservations) != 0 {
		t.Fatalf("reservations after cancellation = %v, err = %v", reservations, err)
	}
}

func TestCleanReservationRejectsSymlink(t *testing.T) {
	root, project, phase := responseOptions(t)
	phaseDirectory, err := PhaseDirectory(root, project, phase)
	if err != nil {
		t.Fatal(err)
	}
	target := filepath.Join(t.TempDir(), "target")
	if err := os.WriteFile(target, []byte("keep"), 0o600); err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(phaseDirectory, "."+phase+".001.response.md.reservation.link")
	if err := os.Symlink(target, path); err != nil {
		t.Fatal(err)
	}
	if err := CleanReservation(path, root, project, phase); !errors.Is(err, ErrUnsafe) {
		t.Fatalf("symlink cleanup err = %v", err)
	}
	if content, err := os.ReadFile(target); err != nil || string(content) != "keep" {
		t.Fatalf("target = %q, err = %v", content, err)
	}
}

func TestPublishedArtifactSurvivesPostPublicationSyncFailure(t *testing.T) {
	root, project, phase := responseOptions(t)
	original := syncPublishedDirectory
	syncPublishedDirectory = func(string) error {
		return errors.New("injected post-publication sync failure")
	}
	t.Cleanup(func() { syncPublishedDirectory = original })

	path, err := Capture(context.Background(), Options{
		OutboxRoot: root,
		Project:    project,
		Phase:      phase,
		Body:       []byte("published bytes\n"),
	})
	if err == nil || path != "" {
		t.Fatalf("capture = %q, %v; want bounded failure after publication", path, err)
	}
	destination := filepath.Join(root, project, phase, phase+".001.response.md")
	content, readErr := os.ReadFile(destination)
	if readErr != nil || string(content) != "published bytes\n" {
		t.Fatalf("published artifact = %q, %v", content, readErr)
	}
}
