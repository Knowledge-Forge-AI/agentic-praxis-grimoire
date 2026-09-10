package report

import (
	"bytes"
	"context"
	"errors"
	"os"
	"path/filepath"
	"sync"
	"testing"
	"time"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/internal/atomicfile"
	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/schema"
)

func TestIdempotencyDefaultDuplicatesPreserved(t *testing.T) {
	repository, environment := newGitRepository(t)
	writeFileTest(t, filepath.Join(repository, "tracked.txt"), []byte("v1\n"))
	runGitTest(t, repository, nil, "add", "tracked.txt")
	commit := commitTest(t, repository, environment, "commit 1", "", false)

	service, err := New(Options{Repository: repository})
	if err != nil {
		t.Fatal(err)
	}
	show, err := service.Show(context.Background(), ShowRequest{
		RequestMetadata: RequestMetadata{Phase: "IDEM-DUP", Result: "passed", FinalGate: "gate"},
		Commit:          commit,
		StatusDoc:       "status.md",
	})
	if err != nil {
		t.Fatal(err)
	}

	outbox := filepath.Join(t.TempDir(), "outbox")
	project := filepath.Base(repository)
	phase := "IDEM-DUP"

	// First append with AppendAlways
	pub1, err := Append(context.Background(), AppendRequest{
		OutboxRoot: outbox,
		Project:    project,
		Phase:      phase,
		Record:     show.Record,
		Policy:     AppendAlways,
	})
	if err != nil {
		t.Fatalf("first append failed: %v", err)
	}
	if pub1.Disposition != PublishedNew {
		t.Fatalf("expected PublishedNew, got %s", pub1.Disposition)
	}

	// Second append with AppendAlways (and zero-value policy) creates duplicate
	pub2, err := Append(context.Background(), AppendRequest{
		OutboxRoot: outbox,
		Project:    project,
		Phase:      phase,
		Record:     show.Record,
		Policy:     AppendAlways,
	})
	if err != nil {
		t.Fatalf("second append failed: %v", err)
	}
	if pub2.Disposition != PublishedAppend {
		t.Fatalf("expected PublishedAppend, got %s", pub2.Disposition)
	}

	content, err := os.ReadFile(pub2.FinalPath)
	if err != nil {
		t.Fatal(err)
	}
	records, err := ParseRecords(content)
	if err != nil {
		t.Fatalf("ParseRecords failed: %v", err)
	}
	if len(records) != 2 {
		t.Fatalf("expected 2 records (default duplicates preserved), got %d", len(records))
	}
	if records[0].ID != show.Record.ID || records[1].ID != show.Record.ID {
		t.Fatalf("expected both records to have ID %s", show.Record.ID)
	}
}

func TestIdempotencyExactRetry(t *testing.T) {
	repository, environment := newGitRepository(t)
	writeFileTest(t, filepath.Join(repository, "tracked.txt"), []byte("v1\n"))
	runGitTest(t, repository, nil, "add", "tracked.txt")
	commit := commitTest(t, repository, environment, "commit 1", "", false)

	service, err := New(Options{Repository: repository})
	if err != nil {
		t.Fatal(err)
	}
	show, err := service.Show(context.Background(), ShowRequest{
		RequestMetadata: RequestMetadata{Phase: "IDEM-RETRY", Result: "passed", FinalGate: "gate"},
		Commit:          commit,
		StatusDoc:       "status.md",
	})
	if err != nil {
		t.Fatal(err)
	}

	outbox := filepath.Join(t.TempDir(), "outbox")
	project := filepath.Base(repository)
	phase := "IDEM-RETRY"

	// First publication with AppendIdempotent
	pub1, err := Append(context.Background(), AppendRequest{
		OutboxRoot: outbox,
		Project:    project,
		Phase:      phase,
		Record:     show.Record,
		Policy:     AppendIdempotent,
	})
	if err != nil {
		t.Fatalf("first append failed: %v", err)
	}
	if pub1.Disposition != PublishedNew {
		t.Fatalf("expected PublishedNew, got %s", pub1.Disposition)
	}

	statBefore, err := os.Stat(pub1.FinalPath)
	if err != nil {
		t.Fatal(err)
	}
	contentBefore, err := os.ReadFile(pub1.FinalPath)
	if err != nil {
		t.Fatal(err)
	}

	// Exact retry with AppendIdempotent
	pub2, err := Append(context.Background(), AppendRequest{
		OutboxRoot: outbox,
		Project:    project,
		Phase:      phase,
		Record:     show.Record,
		Policy:     AppendIdempotent,
	})
	if err != nil {
		t.Fatalf("idempotent retry failed: %v", err)
	}
	if pub2.Disposition != PublishedAlreadyPresent {
		t.Fatalf("expected PublishedAlreadyPresent, got %s", pub2.Disposition)
	}
	if pub2.FinalPath != pub1.FinalPath {
		t.Fatalf("final path mismatch: %s != %s", pub2.FinalPath, pub1.FinalPath)
	}
	if pub2.RecordID != show.Record.ID {
		t.Fatalf("record ID mismatch: %s != %s", pub2.RecordID, show.Record.ID)
	}

	statAfter, err := os.Stat(pub2.FinalPath)
	if err != nil {
		t.Fatal(err)
	}
	contentAfter, err := os.ReadFile(pub2.FinalPath)
	if err != nil {
		t.Fatal(err)
	}

	if !bytes.Equal(contentBefore, contentAfter) {
		t.Fatal("file content changed on idempotent retry")
	}
	if statBefore.ModTime() != statAfter.ModTime() {
		t.Fatalf("file was touched/rewritten: before mtime %v != after mtime %v", statBefore.ModTime(), statAfter.ModTime())
	}
	if statAfter.Mode().Perm() != 0o600 {
		t.Fatalf("expected primary file mode 0600, got %v", statAfter.Mode().Perm())
	}

	records, err := ParseRecords(contentAfter)
	if err != nil || len(records) != 1 {
		t.Fatalf("expected exactly 1 record on idempotent retry, got %d (err: %v)", len(records), err)
	}
}

func TestIdempotencyExactConcurrentRetry(t *testing.T) {
	repository, environment := newGitRepository(t)
	writeFileTest(t, filepath.Join(repository, "file.txt"), []byte("content\n"))
	runGitTest(t, repository, nil, "add", "file.txt")
	commit := commitTest(t, repository, environment, "c1", "", false)

	service, err := New(Options{Repository: repository})
	if err != nil {
		t.Fatal(err)
	}
	show, err := service.Show(context.Background(), ShowRequest{
		RequestMetadata: RequestMetadata{Phase: "IDEM-CONC", Result: "passed", FinalGate: "gate"},
		Commit:          commit,
		StatusDoc:       "status.md",
	})
	if err != nil {
		t.Fatal(err)
	}

	outbox := filepath.Join(t.TempDir(), "outbox")
	project := filepath.Base(repository)
	phase := "IDEM-CONC"

	// Initial publication
	pub0, err := Append(context.Background(), AppendRequest{
		OutboxRoot: outbox,
		Project:    project,
		Phase:      phase,
		Record:     show.Record,
		Policy:     AppendIdempotent,
	})
	if err != nil {
		t.Fatalf("initial append failed: %v", err)
	}
	if pub0.Disposition != PublishedNew {
		t.Fatalf("expected PublishedNew, got %s", pub0.Disposition)
	}

	const concurrency = 4
	var wg sync.WaitGroup
	dispositions := make([]PublicationDisposition, concurrency)
	errs := make([]error, concurrency)

	for i := 0; i < concurrency; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			var pub Publication
			var appendErr error
			for attempt := 0; attempt < 10; attempt++ {
				pub, appendErr = Append(context.Background(), AppendRequest{
					OutboxRoot: outbox,
					Project:    project,
					Phase:      phase,
					Record:     show.Record,
					Policy:     AppendIdempotent,
				})
				if appendErr == nil {
					break
				}
				time.Sleep(15 * time.Millisecond)
			}
			dispositions[idx] = pub.Disposition
			errs[idx] = appendErr
		}(i)
	}
	wg.Wait()

	for i := 0; i < concurrency; i++ {
		if errs[i] != nil {
			t.Fatalf("concurrent retry %d failed: %v", i, errs[i])
		}
		if dispositions[i] != PublishedAlreadyPresent {
			t.Fatalf("expected PublishedAlreadyPresent, got %s", dispositions[i])
		}
	}

	targetPath := filepath.Join(outbox, project, phase, phase+".git.show.report.txt")
	content, err := os.ReadFile(targetPath)
	if err != nil {
		t.Fatal(err)
	}
	records, err := ParseRecords(content)
	if err != nil || len(records) != 1 {
		t.Fatalf("expected exactly 1 record after concurrent retry, got %d", len(records))
	}
}

func TestIdempotencyConflictingSameIdentity(t *testing.T) {
	repository, environment := newGitRepository(t)
	writeFileTest(t, filepath.Join(repository, "file.txt"), []byte("test\n"))
	runGitTest(t, repository, nil, "add", "file.txt")
	commit := commitTest(t, repository, environment, "c1", "", false)

	service, err := New(Options{Repository: repository})
	if err != nil {
		t.Fatal(err)
	}

	// Show report 1: Result = "passed", FinalGate = "gate1"
	show1, err := service.Show(context.Background(), ShowRequest{
		RequestMetadata: RequestMetadata{Phase: "IDEM-CONFLICT", Result: "passed", FinalGate: "gate1"},
		Commit:          commit,
		StatusDoc:       "status.md",
	})
	if err != nil {
		t.Fatal(err)
	}

	// Show report 2: Same commit (same ID!), but Result = "failed", FinalGate = "gate2"
	show2, err := service.Show(context.Background(), ShowRequest{
		RequestMetadata: RequestMetadata{Phase: "IDEM-CONFLICT", Result: "failed", FinalGate: "gate2"},
		Commit:          commit,
		StatusDoc:       "status.md",
	})
	if err != nil {
		t.Fatal(err)
	}

	if show1.Record.ID != show2.Record.ID {
		t.Fatalf("expected same Record ID for same commit, got %s vs %s", show1.Record.ID, show2.Record.ID)
	}

	outbox := filepath.Join(t.TempDir(), "outbox")
	project := filepath.Base(repository)
	phase := "IDEM-CONFLICT"

	// First publish show1 with AppendIdempotent
	pub1, err := Append(context.Background(), AppendRequest{
		OutboxRoot: outbox,
		Project:    project,
		Phase:      phase,
		Record:     show1.Record,
		Policy:     AppendIdempotent,
	})
	if err != nil {
		t.Fatalf("first publish failed: %v", err)
	}
	if pub1.Disposition != PublishedNew {
		t.Fatalf("expected PublishedNew, got %s", pub1.Disposition)
	}

	beforeContent, err := os.ReadFile(pub1.FinalPath)
	if err != nil {
		t.Fatal(err)
	}

	// Publish show2 with same ID but conflicting content under AppendIdempotent
	_, err = Append(context.Background(), AppendRequest{
		OutboxRoot: outbox,
		Project:    project,
		Phase:      phase,
		Record:     show2.Record,
		Policy:     AppendIdempotent,
	})
	if err == nil {
		t.Fatal("expected ErrReplayConflict on differing content with same identity, got nil")
	}
	if !errors.Is(err, ErrReplayConflict) {
		t.Fatalf("expected error Is ErrReplayConflict, got %v", err)
	}

	// File on disk must remain unchanged (no rewrite)
	afterContent, err := os.ReadFile(pub1.FinalPath)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(beforeContent, afterContent) {
		t.Fatal("file was modified despite replay conflict rejection")
	}
}

func TestIdempotencyMixedHistoricalDuplicates(t *testing.T) {
	repository, environment := newGitRepository(t)
	writeFileTest(t, filepath.Join(repository, "file.txt"), []byte("test\n"))
	runGitTest(t, repository, nil, "add", "file.txt")
	commit := commitTest(t, repository, environment, "c1", "", false)

	service, err := New(Options{Repository: repository})
	if err != nil {
		t.Fatal(err)
	}

	showPassed, err := service.Show(context.Background(), ShowRequest{
		RequestMetadata: RequestMetadata{Phase: "IDEM-MIXED", Result: "passed", FinalGate: "gate"},
		Commit:          commit,
		StatusDoc:       "status.md",
	})
	if err != nil {
		t.Fatal(err)
	}

	showFailed, err := service.Show(context.Background(), ShowRequest{
		RequestMetadata: RequestMetadata{Phase: "IDEM-MIXED", Result: "failed", FinalGate: "gate"},
		Commit:          commit,
		StatusDoc:       "status.md",
	})
	if err != nil {
		t.Fatal(err)
	}

	outbox := filepath.Join(t.TempDir(), "outbox")
	project := filepath.Base(repository)
	phase := "IDEM-MIXED"

	// Craft a target file with historical duplicates under default AppendAlways:
	// Record 1: showPassed
	// Record 2: showFailed (same ID, different content!)
	if _, err := Append(context.Background(), AppendRequest{
		OutboxRoot: outbox,
		Project:    project,
		Phase:      phase,
		Record:     showPassed.Record,
		Policy:     AppendAlways,
	}); err != nil {
		t.Fatal(err)
	}
	pub2, err := Append(context.Background(), AppendRequest{
		OutboxRoot: outbox,
		Project:    project,
		Phase:      phase,
		Record:     showFailed.Record,
		Policy:     AppendAlways,
	})
	if err != nil {
		t.Fatal(err)
	}

	beforeContent, err := os.ReadFile(pub2.FinalPath)
	if err != nil {
		t.Fatal(err)
	}

	// Now attempt AppendIdempotent for showPassed.
	// Even though an identical duplicate exists (showPassed is present),
	// a conflicting duplicate also exists (showFailed has same ID and different bytes).
	// Specification requires: any same-key different bytes => conflict no rewrite even if identical duplicates also exist.
	_, err = Append(context.Background(), AppendRequest{
		OutboxRoot: outbox,
		Project:    project,
		Phase:      phase,
		Record:     showPassed.Record,
		Policy:     AppendIdempotent,
	})
	if err == nil {
		t.Fatal("expected ErrReplayConflict on mixed historical duplicates, got nil")
	}
	if !errors.Is(err, ErrReplayConflict) {
		t.Fatalf("expected ErrReplayConflict, got %v", err)
	}

	afterContent, err := os.ReadFile(pub2.FinalPath)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(beforeContent, afterContent) {
		t.Fatal("file modified despite replay conflict on mixed historical duplicates")
	}
}

func TestIdempotencyMultipleIdenticalHistoricalDuplicates(t *testing.T) {
	repository, environment := newGitRepository(t)
	writeFileTest(t, filepath.Join(repository, "file.txt"), []byte("test\n"))
	runGitTest(t, repository, nil, "add", "file.txt")
	commit := commitTest(t, repository, environment, "c1", "", false)

	service, err := New(Options{Repository: repository})
	if err != nil {
		t.Fatal(err)
	}

	show, err := service.Show(context.Background(), ShowRequest{
		RequestMetadata: RequestMetadata{Phase: "IDEM-IDENT", Result: "passed", FinalGate: "gate"},
		Commit:          commit,
		StatusDoc:       "status.md",
	})
	if err != nil {
		t.Fatal(err)
	}

	outbox := filepath.Join(t.TempDir(), "outbox")
	project := filepath.Base(repository)
	phase := "IDEM-IDENT"

	// Create two identical historical duplicates using AppendAlways
	for i := 0; i < 2; i++ {
		if _, err := Append(context.Background(), AppendRequest{
			OutboxRoot: outbox,
			Project:    project,
			Phase:      phase,
			Record:     show.Record,
			Policy:     AppendAlways,
		}); err != nil {
			t.Fatal(err)
		}
	}

	targetPath := filepath.Join(outbox, project, phase, phase+".git.show.report.txt")
	beforeContent, err := os.ReadFile(targetPath)
	if err != nil {
		t.Fatal(err)
	}
	records, err := ParseRecords(beforeContent)
	if err != nil || len(records) != 2 {
		t.Fatalf("expected 2 historical records, got %d", len(records))
	}

	// Specification requires: Multiple identical historical matches => already present.
	pub, err := Append(context.Background(), AppendRequest{
		OutboxRoot: outbox,
		Project:    project,
		Phase:      phase,
		Record:     show.Record,
		Policy:     AppendIdempotent,
	})
	if err != nil {
		t.Fatalf("expected already present for multiple identical matches, got error: %v", err)
	}
	if pub.Disposition != PublishedAlreadyPresent {
		t.Fatalf("expected PublishedAlreadyPresent, got %s", pub.Disposition)
	}

	afterContent, err := os.ReadFile(targetPath)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(beforeContent, afterContent) {
		t.Fatal("file rewritten despite multiple identical matches")
	}
}

func TestIdempotencyUnknownPolicyNoPreparation(t *testing.T) {
	repository, environment := newGitRepository(t)
	writeFileTest(t, filepath.Join(repository, "file.txt"), []byte("test\n"))
	runGitTest(t, repository, nil, "add", "file.txt")
	commit := commitTest(t, repository, environment, "c1", "", false)

	service, err := New(Options{Repository: repository})
	if err != nil {
		t.Fatal(err)
	}
	show, err := service.Show(context.Background(), ShowRequest{
		RequestMetadata: RequestMetadata{Phase: "IDEM-NOPREP", Result: "passed", FinalGate: "gate"},
		Commit:          commit,
		StatusDoc:       "status.md",
	})
	if err != nil {
		t.Fatal(err)
	}

	// Outbox directory that does NOT exist yet
	outbox := filepath.Join(t.TempDir(), "nonexistent-outbox")

	_, err = Append(context.Background(), AppendRequest{
		OutboxRoot: outbox,
		Project:    filepath.Base(repository),
		Phase:      "IDEM-NOPREP",
		Record:     show.Record,
		Policy:     AppendPolicy("unsupported-unknown-policy"),
	})
	if err == nil {
		t.Fatal("expected error for unknown policy, got nil")
	}
	if !errors.Is(err, ErrInvalidRequest) {
		t.Fatalf("expected ErrInvalidRequest, got %v", err)
	}

	// Verify no directory preparation occurred on disk
	if _, statErr := os.Stat(outbox); !os.IsNotExist(statErr) {
		t.Fatalf("outbox directory was prepared despite unknown policy rejection: %v", statErr)
	}
}

func TestIdempotencyDiffMetadataConflict(t *testing.T) {
	repository, environment := newGitRepository(t)
	writeFileTest(t, filepath.Join(repository, "tracked.txt"), []byte("v1\n"))
	runGitTest(t, repository, nil, "add", "tracked.txt")
	commitTest(t, repository, environment, "c1", "", false)
	writeFileTest(t, filepath.Join(repository, "tracked.txt"), []byte("v2-uncommitted-change\n"))

	service, err := New(Options{Repository: repository})
	if err != nil {
		t.Fatal(err)
	}

	diff1, err := service.Diff(context.Background(), DiffRequest{
		RequestMetadata: RequestMetadata{Phase: "IDEM-DIFF", Result: "passed", FinalGate: "gate1"},
	})
	if err != nil {
		t.Fatal(err)
	}

	diff2, err := service.Diff(context.Background(), DiffRequest{
		RequestMetadata: RequestMetadata{Phase: "IDEM-DIFF", Result: "failed", FinalGate: "gate2"},
	})
	if err != nil {
		t.Fatal(err)
	}

	if diff1.Record.ID != diff2.Record.ID {
		t.Fatalf("expected same Diff ID for same repository drift state, got %s vs %s", diff1.Record.ID, diff2.Record.ID)
	}

	outbox := filepath.Join(t.TempDir(), "outbox")
	project := filepath.Base(repository)
	phase := "IDEM-DIFF"

	pub1, err := Append(context.Background(), AppendRequest{
		OutboxRoot: outbox,
		Project:    project,
		Phase:      phase,
		Record:     diff1.Record,
		Policy:     AppendIdempotent,
	})
	if err != nil {
		t.Fatal(err)
	}
	if pub1.Disposition != PublishedNew {
		t.Fatalf("expected PublishedNew, got %s", pub1.Disposition)
	}

	// Same drift ID, different metadata => ErrReplayConflict
	_, err = Append(context.Background(), AppendRequest{
		OutboxRoot: outbox,
		Project:    project,
		Phase:      phase,
		Record:     diff2.Record,
		Policy:     AppendIdempotent,
	})
	if err == nil {
		t.Fatal("expected ErrReplayConflict on differing metadata with same diff ID")
	}
	if !errors.Is(err, ErrReplayConflict) {
		t.Fatalf("expected ErrReplayConflict, got %v", err)
	}
}

func TestIdempotencySourceStabilityOperationalVariations(t *testing.T) {
	repository, environment := newGitRepository(t)
	writeFileTest(t, filepath.Join(repository, "file.txt"), []byte("test\n"))
	runGitTest(t, repository, nil, "add", "file.txt")
	commit := commitTest(t, repository, environment, "c1", "", false)

	service, err := New(Options{Repository: repository})
	if err != nil {
		t.Fatal(err)
	}
	show, err := service.Show(context.Background(), ShowRequest{
		RequestMetadata: RequestMetadata{Phase: "IDEM-OPS-STAB", Result: "passed", FinalGate: "gate"},
		Commit:          commit,
		StatusDoc:       "status.md",
	})
	if err != nil {
		t.Fatal(err)
	}

	outbox := filepath.Join(t.TempDir(), "outbox")
	project := filepath.Base(repository)
	phase := "IDEM-OPS-STAB"

	// Publish Git show record first
	if _, err := Append(context.Background(), AppendRequest{
		OutboxRoot: outbox,
		Project:    project,
		Phase:      phase,
		Record:     show.Record,
		Policy:     AppendIdempotent,
	}); err != nil {
		t.Fatal(err)
	}

	rawBody := []byte("report_schema: operational-report-v1\nphase: IDEM-OPS-STAB\noutcome: passed\nprimary_commit: " + commit + "\n")

	// Baseline operational record
	opsBase, err := Operational(context.Background(), OperationalRequest{
		RequestMetadata:    RequestMetadata{Phase: phase, Result: "passed", FinalGate: "gate"},
		Project:            project,
		SourceName:         "baseline.txt",
		Source:             rawBody,
		RelatedCommit:      commit,
		RelatedGitReportID: show.Record.ID,
	}, []Record{show.Record})
	if err != nil {
		t.Fatal(err)
	}

	pubOps, err := Append(context.Background(), AppendRequest{
		OutboxRoot: outbox,
		Project:    project,
		Phase:      phase,
		Record:     opsBase.Record,
		Policy:     AppendIdempotent,
	})
	if err != nil {
		t.Fatal(err)
	}
	if pubOps.Disposition != PublishedAppend {
		t.Fatalf("expected PublishedAppend, got %s", pubOps.Disposition)
	}

	// Exact retry of opsBase succeeds with PublishedAlreadyPresent
	retryPub, err := Append(context.Background(), AppendRequest{
		OutboxRoot: outbox,
		Project:    project,
		Phase:      phase,
		Record:     opsBase.Record,
		Policy:     AppendIdempotent,
	})
	if err != nil {
		t.Fatal(err)
	}
	if retryPub.Disposition != PublishedAlreadyPresent {
		t.Fatalf("expected PublishedAlreadyPresent, got %s", retryPub.Disposition)
	}

	// Variation 1: Different SourceName (source basename differs, same source payload and same ID)
	opsDiffBasename, err := Operational(context.Background(), OperationalRequest{
		RequestMetadata:    RequestMetadata{Phase: phase, Result: "passed", FinalGate: "gate"},
		Project:            project,
		SourceName:         "different-basename.txt",
		Source:             rawBody,
		RelatedCommit:      commit,
		RelatedGitReportID: show.Record.ID,
	}, []Record{show.Record})
	if err != nil {
		t.Fatal(err)
	}
	if opsDiffBasename.Record.ID != opsBase.Record.ID {
		t.Fatalf("expected same Record ID for same source bytes, got %s vs %s", opsDiffBasename.Record.ID, opsBase.Record.ID)
	}
	_, err = Append(context.Background(), AppendRequest{
		OutboxRoot: outbox,
		Project:    project,
		Phase:      phase,
		Record:     opsDiffBasename.Record,
		Policy:     AppendIdempotent,
	})
	if !errors.Is(err, ErrReplayConflict) {
		t.Fatalf("expected ErrReplayConflict for differing source basename, got %v", err)
	}

	// Variation 2: Different FinalGate (metadata differs, same source payload and same ID)
	opsDiffGate, err := Operational(context.Background(), OperationalRequest{
		RequestMetadata:    RequestMetadata{Phase: phase, Result: "passed", FinalGate: "different-gate"},
		Project:            project,
		SourceName:         "baseline.txt",
		Source:             rawBody,
		RelatedCommit:      commit,
		RelatedGitReportID: show.Record.ID,
	}, []Record{show.Record})
	if err != nil {
		t.Fatal(err)
	}
	_, err = Append(context.Background(), AppendRequest{
		OutboxRoot: outbox,
		Project:    project,
		Phase:      phase,
		Record:     opsDiffGate.Record,
		Policy:     AppendIdempotent,
	})
	if !errors.Is(err, ErrReplayConflict) {
		t.Fatalf("expected ErrReplayConflict for differing metadata FinalGate, got %v", err)
	}
}

func TestIdempotencyRetainedScopeSupersession(t *testing.T) {
	repository, environment := newGitRepository(t)
	writeFileTest(t, filepath.Join(repository, "file.txt"), []byte("tracked\n"))
	runGitTest(t, repository, nil, "add", "file.txt")
	commit := commitTest(t, repository, environment, "c1", "", false)

	service, err := New(Options{Repository: repository})
	if err != nil {
		t.Fatal(err)
	}

	show, err := service.Show(context.Background(), ShowRequest{
		RequestMetadata: RequestMetadata{Phase: "IDEM-SUPER", Result: "passed", FinalGate: "gate"},
		Commit:          commit,
		StatusDoc:       "status.md",
	})
	if err != nil {
		t.Fatal(err)
	}

	opsBody := []byte("report_schema: operational-report-v1\nphase: IDEM-SUPER\noutcome: passed\n")
	ops, err := Operational(context.Background(), OperationalRequest{
		RequestMetadata: RequestMetadata{Phase: "IDEM-SUPER", Result: "passed", FinalGate: "gate"},
		Project:         filepath.Base(repository),
		SourceName:      "standalone.txt",
		Source:          opsBody,
	}, nil)
	if err != nil {
		t.Fatal(err)
	}

	outbox := filepath.Join(t.TempDir(), "outbox")
	project := filepath.Base(repository)
	phase := "IDEM-SUPER"

	// 1. First publish standalone operational record -> PublishedNew in IDEM-SUPER.ops.report.txt
	pub1, err := Append(context.Background(), AppendRequest{
		OutboxRoot: outbox,
		Project:    project,
		Phase:      phase,
		Record:     ops.Record,
		Policy:     AppendIdempotent,
	})
	if err != nil {
		t.Fatal(err)
	}
	if pub1.Disposition != PublishedNew {
		t.Fatalf("expected PublishedNew, got %s", pub1.Disposition)
	}

	opsFile := filepath.Join(outbox, project, phase, phase+".ops.report.txt")
	showFile := filepath.Join(outbox, project, phase, phase+".git.show.report.txt")
	if _, err := os.Stat(opsFile); err != nil {
		t.Fatal("ops file should exist")
	}

	// 2. Publish Git show record with AppendIdempotent -> supersedes ops record
	// Superseded removed primaries not searched
	pub2, err := Append(context.Background(), AppendRequest{
		OutboxRoot: outbox,
		Project:    project,
		Phase:      phase,
		Record:     show.Record,
		Policy:     AppendIdempotent,
	})
	if err != nil {
		t.Fatal(err)
	}
	if pub2.Disposition != PublishedSuperseding {
		t.Fatalf("expected PublishedSuperseding, got %s", pub2.Disposition)
	}
	if _, err := os.Stat(opsFile); !os.IsNotExist(err) {
		t.Fatal("superseded ops file should have been removed")
	}
	if _, err := os.Stat(showFile); err != nil {
		t.Fatal("show file should exist")
	}

	// 3. Retry Git show record with AppendIdempotent -> PublishedAlreadyPresent
	pub3, err := Append(context.Background(), AppendRequest{
		OutboxRoot: outbox,
		Project:    project,
		Phase:      phase,
		Record:     show.Record,
		Policy:     AppendIdempotent,
	})
	if err != nil {
		t.Fatal(err)
	}
	if pub3.Disposition != PublishedAlreadyPresent {
		t.Fatalf("expected PublishedAlreadyPresent, got %s", pub3.Disposition)
	}
}

func TestIdempotencyRetryAfterTransactionRecovery(t *testing.T) {
	repository, environment := newGitRepository(t)
	writeFileTest(t, filepath.Join(repository, "file.txt"), []byte("tracked\n"))
	runGitTest(t, repository, nil, "add", "file.txt")
	commit := commitTest(t, repository, environment, "c1", "", false)

	service, err := New(Options{Repository: repository})
	if err != nil {
		t.Fatal(err)
	}

	show, err := service.Show(context.Background(), ShowRequest{
		RequestMetadata: RequestMetadata{Phase: "IDEM-REC", Result: "passed", FinalGate: "gate"},
		Commit:          commit,
		StatusDoc:       "status.md",
	})
	if err != nil {
		t.Fatal(err)
	}

	outbox := filepath.Join(t.TempDir(), "outbox")
	project := filepath.Base(repository)
	phase := "IDEM-REC"

	// 1. Initial publication of show
	pub, err := Append(context.Background(), AppendRequest{
		OutboxRoot: outbox,
		Project:    project,
		Phase:      phase,
		Record:     show.Record,
		Policy:     AppendIdempotent,
	})
	if err != nil {
		t.Fatal(err)
	}
	if pub.Disposition != PublishedNew {
		t.Fatalf("expected PublishedNew, got %s", pub.Disposition)
	}

	paths, err := atomicfile.Prepare(outbox, project, phase)
	if err != nil {
		t.Fatal(err)
	}

	// 2. Simulate an interrupted transaction by creating .phase.transaction marker
	target := phase + ".git.show.report.txt"
	stale := []string{phase + ".git.diff.report.txt", phase + ".ops.report.txt"}
	marker := "agent-report-transaction-v1\nphase: " + phase + "\ntarget: " + target + "\nstale: " + phase + ".git.diff.report.txt," + phase + ".ops.report.txt\ntoken: abcd1234abcd1234abcd1234abcd1234\n"
	if err := os.WriteFile(paths.Transaction, []byte(marker), 0o600); err != nil {
		t.Fatal(err)
	}

	// Append should now fail with ErrPublication due to unresolved transaction
	_, err = Append(context.Background(), AppendRequest{
		OutboxRoot: outbox,
		Project:    project,
		Phase:      phase,
		Record:     show.Record,
		Policy:     AppendIdempotent,
	})
	if !errors.Is(err, ErrPublication) {
		t.Fatalf("expected ErrPublication with unresolved transaction, got %v", err)
	}

	// 3. Perform explicit transaction recovery
	allowed := append([]string{target}, stale...)
	recovered, err := atomicfile.Recover(context.Background(), paths, allowed)
	if err != nil {
		t.Fatalf("recovery failed: %v", err)
	}
	if !recovered {
		t.Fatal("expected recovery to report true")
	}

	// 4. Retry with AppendIdempotent after recovery succeeds with PublishedAlreadyPresent
	retryPub, err := Append(context.Background(), AppendRequest{
		OutboxRoot: outbox,
		Project:    project,
		Phase:      phase,
		Record:     show.Record,
		Policy:     AppendIdempotent,
	})
	if err != nil {
		t.Fatalf("retry after recovery failed: %v", err)
	}
	if retryPub.Disposition != PublishedAlreadyPresent {
		t.Fatalf("expected PublishedAlreadyPresent after recovery, got %s", retryPub.Disposition)
	}
}

func TestIdempotencyValidateAssociationRejectsDanglingNewOperationalRelation(t *testing.T) {
	outbox := filepath.Join(t.TempDir(), "outbox")
	project := "test-proj"
	phase := "IDEM-DANGLING"

	// Construct an operational record with a dangling relation to a non-existent Git record
	body := []byte("report_schema: operational-report-v1\nphase: IDEM-DANGLING\noutcome: passed\nprimary_commit: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n")
	ops, err := Operational(context.Background(), OperationalRequest{
		RequestMetadata:    RequestMetadata{Phase: phase, Result: "passed", FinalGate: "gate"},
		Project:            project,
		SourceName:         "ops.txt",
		Source:             body,
		RelatedCommit:      "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
		RelatedGitReportID: "GIT-SHOW-REPORT-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
	}, []Record{
		// Fake git record passed to Operational builder so building succeeds
		{
			Kind:          schema.GitShowRecord,
			FormatVersion: 2,
			ID:            "GIT-SHOW-REPORT-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
			Project:       project,
			Phase:         phase,
			Payload:       []byte("dummy"),
		},
	})
	if err != nil {
		t.Fatal(err)
	}

	// Now try to Append into an empty outbox where NO target Git report exists on disk
	// "Validate association even when no target exists to reject dangling new operational relation."
	_, err = Append(context.Background(), AppendRequest{
		OutboxRoot: outbox,
		Project:    project,
		Phase:      phase,
		Record:     ops.Record,
		Policy:     AppendIdempotent,
	})
	if err == nil {
		t.Fatal("expected error on dangling operational relation in empty outbox, got nil")
	}
	if !errors.Is(err, ErrUnsafePath) {
		t.Fatalf("expected ErrUnsafePath for dangling operational relation, got %v", err)
	}

	// Verify no primary was published
	opsPrimary := filepath.Join(outbox, project, phase, phase+".ops.report.txt")
	if _, statErr := os.Stat(opsPrimary); !os.IsNotExist(statErr) {
		t.Fatal("ops primary file was published despite dangling relation")
	}
}

func TestIdempotencyOperationalValidationBeforePrepare(t *testing.T) {
	outbox := filepath.Join(t.TempDir(), "nonexistent-outbox-ops")
	project := "test-proj"
	phase := "IDEM-VAL-PREP"

	// 1. Invalid operational record: empty payload or malformed format
	invalidOps := Record{
		Kind:          schema.OperationalRecord,
		FormatVersion: 1,
		ID:            "OPERATIONAL-REPORT-" + string(bytes.Repeat([]byte{'a'}, 64)),
		Project:       project,
		Phase:         phase,
		Payload:       []byte("malformed-not-valid-ops-payload\n"),
	}

	_, err := Append(context.Background(), AppendRequest{
		OutboxRoot: outbox,
		Project:    project,
		Phase:      phase,
		Record:     invalidOps,
		Policy:     AppendIdempotent,
	})
	if err == nil {
		t.Fatal("expected validation error for invalid operational record, got nil")
	}

	// Verify no outbox directory was prepared on disk
	if _, statErr := os.Stat(outbox); !os.IsNotExist(statErr) {
		t.Fatalf("outbox directory was created despite invalid operational record rejection: %v", statErr)
	}

	// 2. Show/diff payloads remain append-unvalidated compatibility:
	// A Show record with a custom/opaque payload is NOT rejected by validateOperationalRecord
	customShow := Record{
		Kind:          schema.GitShowRecord,
		FormatVersion: 2,
		ID:            "GIT-SHOW-REPORT-" + string(bytes.Repeat([]byte{'b'}, 40)),
		Project:       project,
		Phase:         phase,
		Payload:       []byte("custom opaque show payload for append-unvalidated compatibility\n"),
	}
	showOutbox := filepath.Join(t.TempDir(), "show-outbox")
	pub, err := Append(context.Background(), AppendRequest{
		OutboxRoot: showOutbox,
		Project:    project,
		Phase:      phase,
		Record:     customShow,
		Policy:     AppendIdempotent,
	})
	if err != nil {
		t.Fatalf("show payload should remain append-unvalidated, got error: %v", err)
	}
	if pub.Disposition != PublishedNew {
		t.Fatalf("expected PublishedNew, got %s", pub.Disposition)
	}
}
