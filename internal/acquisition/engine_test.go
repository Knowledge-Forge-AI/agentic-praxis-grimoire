package acquisition

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/skills"
)

func TestExactRepeatAndScope(t *testing.T) {
	input := skills.CatalogInput{SchemaVersion: skills.CatalogSchemaV1}
	root := t.TempDir()
	e, err := Open(Config{RunDir: root, RunID: "run", BindingID: "binding", AttemptID: "attempt", Consumer: skills.ConsumerClaude, Catalog: input})
	if err != nil {
		t.Fatal(err)
	}
	defer e.Close()
	a, err := e.Acquire("apgr:go-test-profile", "cli")
	if err != nil {
		t.Fatal(err)
	}
	selected, _ := skills.ResolveCatalog(input, "apgr:go-test-profile", skills.ConsumerClaude)
	if !bytes.Equal(a.Selection.Snapshot.Body, selected.Snapshot.Body) {
		t.Fatal("body changed")
	}
	body, err := os.ReadFile(filepath.Join(root, a.MaterializedPath, "SKILL.md"))
	if err != nil || !bytes.Equal(body, selected.Snapshot.Body) {
		t.Fatal("snapshot missing")
	}
	if err := e.Delivered(a.EventID, "cli", 123); err != nil {
		t.Fatal(err)
	}
	b, err := e.Acquire("apgr:go-test-profile", "mcp")
	if err != nil || !b.IsRepeatDelivery || b.EventID == a.EventID {
		t.Fatal("repeat identity")
	}
}

func TestUnsafeAndUnqualifiedRequests(t *testing.T) {
	e, err := Open(Config{RunDir: t.TempDir(), RunID: "run", BindingID: "binding", AttemptID: "attempt", Consumer: skills.ConsumerCodex, Catalog: skills.CatalogInput{SchemaVersion: skills.CatalogSchemaV1}})
	if err != nil {
		t.Fatal(err)
	}
	defer e.Close()
	for _, id := range []string{"go-test-profile", "apgr:../secret", "user:/tmp/x", "apgr:unknown"} {
		if _, err := e.Acquire(id, "mcp"); err == nil {
			t.Fatalf("accepted %q", id)
		}
	}
}

func TestOverrideSupportAndStoreIsolation(t *testing.T) {
	input := skills.CatalogInput{SchemaVersion: skills.CatalogSchemaV1, Snapshots: []skills.SkillSnapshot{{QualifiedID: "project:local", Path: "explicit/source/SKILL.md", Body: []byte("---\nname: local\ndescription: Explicit local source.\nsupport: [\"refs/data.bin\"]\n---\nExact local body.\n"), Support: map[string][]byte{"refs/data.bin": {0, 255, 1}}}}, Overrides: []skills.CatalogOverride{{Requested: "apgr:go-test-profile", Selected: "project:local", ConfigPath: "explicit/config.toml", ConfigSHA256: strings.Repeat("a", 64)}}}
	root := t.TempDir()
	e, err := Open(Config{RunDir: root, RunID: "run/a", BindingID: "review", AttemptID: "attempt", Consumer: skills.ConsumerClaude, Catalog: input})
	if err != nil {
		t.Fatal(err)
	}
	defer e.Close()
	result, err := e.Acquire("apgr:go-test-profile", "mcp")
	if err != nil {
		t.Fatal(err)
	}
	if result.Selection.SelectedIdentity != "project:local" || !bytes.Equal(result.Selection.Snapshot.Body, input.Snapshots[0].Body) {
		t.Fatal("override lost")
	}
	support, err := os.ReadFile(filepath.Join(root, result.MaterializedPath, "refs/data.bin"))
	if err != nil || !bytes.Equal(support, []byte{0, 255, 1}) {
		t.Fatal("support changed", err)
	}
	outside := t.TempDir()
	unsafe := t.TempDir()
	if err = os.Symlink(outside, filepath.Join(unsafe, "acquisitions")); err != nil {
		t.Fatal(err)
	}
	if bad, err := Open(Config{RunDir: unsafe, RunID: "run", BindingID: "review", AttemptID: "a", Consumer: skills.ConsumerClaude, Catalog: input}); err == nil {
		bad.Close()
		t.Fatal("store escape accepted")
	}
	entries, _ := os.ReadDir(outside)
	if len(entries) != 0 {
		t.Fatal("escaped mutation")
	}
}

func TestScopeCollisionAndAllowlist(t *testing.T) {
	root := t.TempDir()
	seen := map[string]bool{}
	for _, attempt := range []string{"one", "two", "one"} {
		e, err := Open(Config{RunDir: root, RunID: "run", BindingID: "review", AttemptID: attempt, Consumer: skills.ConsumerClaude, Catalog: skills.CatalogInput{SchemaVersion: skills.CatalogSchemaV1}, AllowedIDs: []string{"apgr:go-test-profile"}})
		if err != nil {
			t.Fatal(err)
		}
		r, err := e.Acquire("apgr:go-test-profile", "mcp")
		if err != nil {
			t.Fatal(err)
		}
		if seen[r.EventID] {
			t.Fatal("collision")
		}
		seen[r.EventID] = true
		if _, err = e.Acquire("apgr:sqlite-database-profile", "mcp"); err == nil {
			t.Fatal("allowlist widened")
		}
		e.Close()
	}
}

func TestEmptyAllowlistDoesNotBecomeUnrestricted(t *testing.T) {
	e, err := Open(Config{RunDir: t.TempDir(), RunID: "run", BindingID: "review", AttemptID: "a", Consumer: skills.ConsumerClaude, Catalog: skills.CatalogInput{SchemaVersion: skills.CatalogSchemaV1}, AllowedIDs: []string{}})
	if err != nil {
		t.Fatal(err)
	}
	defer e.Close()
	if _, err = e.Acquire("apgr:go-test-profile", "mcp"); err == nil {
		t.Fatal("empty allowlist widened")
	}
}

func TestMaterializationIsNotPriorDelivery(t *testing.T) {
	e := server(t)
	first, err := e.Acquire("apgr:go-test-profile", "mcp")
	if err != nil {
		t.Fatal(err)
	}
	second, err := e.Acquire("apgr:go-test-profile", "mcp")
	if err != nil {
		t.Fatal(err)
	}
	if first.IsRepeatDelivery || second.IsRepeatDelivery {
		t.Fatal("availability claimed as delivery")
	}
	if err = e.Delivered(second.EventID, "mcp", 123); err != nil {
		t.Fatal(err)
	}
	third, err := e.Acquire("apgr:go-test-profile", "mcp")
	if err != nil || !third.IsRepeatDelivery {
		t.Fatal("known repeat missing", err)
	}
}

func TestRecoveryPreparationAndContentReuse(t *testing.T) {
	e := server(t)
	a, err := e.Acquire("apgr:go-test-profile", "preparation")
	if err != nil {
		t.Fatal(err)
	}
	b, err := e.Acquire("apgr:go-test-profile", "mcp")
	if err != nil || b.IsRepeatDelivery || a.MaterializedPath != b.MaterializedPath {
		t.Fatal("preparation must reuse exact storage without claiming delivery", err)
	}
	events, err := e.events()
	if err != nil {
		t.Fatal(err)
	}
	for _, event := range events {
		if event.Channel == "preparation" && (event.Kind == "requested" || event.Kind == "channel_delivered") {
			t.Fatal(event)
		}
	}
}

func TestInterruptedEventDoesNotBlockAcquisition(t *testing.T) {
	e := server(t)
	name := "acquisitions/event-" + strings.Repeat("a", 64) + ".jsonl"
	if err := e.write(name, []byte(`{"schema":`)); err != nil {
		t.Fatal(err)
	}
	if _, err := e.Acquire("apgr:go-test-profile", "mcp"); err != nil {
		t.Fatal(err)
	}
	facts, err := e.Explain()
	if err != nil || len(facts["diagnostics"].([]string)) != 1 {
		t.Fatal("missing corrupt-event diagnostic", err)
	}
}

func TestBindingBudgetDoesNotStarveNextBinding(t *testing.T) {
	e := server(t)
	for i := 0; i < MaxBindingEvents; i++ {
		if _, err := e.emit(Event{Kind: "search_miss", Channel: "cli"}); err != nil {
			t.Fatal(err)
		}
	}
	if _, err := e.Search("missing", "mcp"); err == nil || err.Error() != "ACQUIRE_BINDING_EVENT_LIMIT" {
		t.Fatal(err)
	}
	c := e.config
	c.BindingID = "next"
	next, err := Open(c)
	if err != nil {
		t.Fatal(err)
	}
	defer next.Close()
	if _, err := next.Acquire("apgr:go-test-profile", "mcp"); err != nil {
		t.Fatal(err)
	}
}

func TestMaterializationBudgetStopsBeforeArchiveLimit(t *testing.T) {
	e := server(t)
	f, err := e.root.Create("acquisitions/skills/retained")
	if err != nil {
		t.Fatal(err)
	}
	if err = f.Truncate(MaxStoreBytes); err != nil {
		t.Fatal(err)
	}
	f.Close()
	if _, err = e.Acquire("apgr:go-test-profile", "mcp"); err == nil || err.Error() != "ACQUIRE_STORE_LIMIT" {
		t.Fatal(err)
	}
}

func TestPublishedEventsAreCompleteAndPendingIgnored(t *testing.T) {
	e := server(t)
	if err := e.write("acquisitions/.pending-crash", []byte(`{`)); err != nil {
		t.Fatal(err)
	}
	if _, err := e.Acquire("apgr:go-test-profile", "mcp"); err != nil {
		t.Fatal(err)
	}
	events, err := e.events()
	if err != nil || len(events) != 3 {
		t.Fatal(err, events)
	}
	for _, event := range events {
		data, err := ReadFile(e.root, "acquisitions/event-"+event.EventID+".jsonl", 8192)
		if err != nil || !json.Valid(data) {
			t.Fatal(err)
		}
	}
	if fsPath("..") {
		t.Fatal("traversal accepted")
	}
}
