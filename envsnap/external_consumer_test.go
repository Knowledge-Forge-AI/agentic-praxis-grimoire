package envsnap

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
  "testing"
  "github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/envsnap"
)

func TestInProcess(t *testing.T) {
  profile := envsnap.Profile{SchemaVersion: envsnap.ProfileSchemaV1, ProfileID: "consumer", Entries: []envsnap.ProfileEntry{{Name: "PATH", Validator: "path", MaxBytes: 128, Required: true}}}
  if err := envsnap.ValidateProfile(profile); err != nil { t.Fatal(err) }
  snap, err := envsnap.Capture(context.Background(), envsnap.CaptureRequest{Profile: profile, Environment: map[string]string{"PATH": "/bin"}, Provenance: envsnap.SnapshotProvenance{Context: "consumer"}})
  if err != nil { t.Fatal(err) }
  root := t.TempDir()
  stored, err := envsnap.Store(context.Background(), envsnap.StoreRequest{StorageRoot: root, Snapshot: snap, Profile: &profile})
  if err != nil { t.Fatal(err) }
  loaded, err := envsnap.Load(context.Background(), envsnap.LoadRequest{StorageRoot: root, ProfileID: profile.ProfileID, ExpectedProfile: &profile})
  if err != nil { t.Fatal(err) }
  isolated, err := envsnap.Resolve(context.Background(), envsnap.ResolveRequest{Profile: &profile, Snapshot: loaded, Overrides: map[string]string{"PATH": "/usr/bin"}})
  if err != nil || isolated.Environment["PATH"] != "/usr/bin" || isolated.Provenance["PATH"].Source != envsnap.SourceOverride { t.Fatalf("isolated = %#v %v", isolated, err) }
  overlay, err := envsnap.Resolve(context.Background(), envsnap.ResolveRequest{Profile: &profile, Snapshot: loaded, Mode: envsnap.ModeOverlay, Base: map[string]string{"BASE_ONLY": "kept"}})
  if err != nil || overlay.Environment["PATH"] != "/bin" || overlay.Environment["BASE_ONLY"] != "kept" || overlay.Provenance["BASE_ONLY"].Source != envsnap.SourceBase { t.Fatalf("overlay = %#v %v", overlay, err) }
  if stored.Path == "" { t.Fatal("stored path missing") }
  if _, err := os.Stat(stored.Path); err != nil { t.Fatal(err) }
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
