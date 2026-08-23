package envsnap

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"testing"
	"time"
)

type fixedClock struct{ now time.Time }

func (clock fixedClock) Now() time.Time { return clock.now }

func testProfile() Profile {
	return Profile{
		SchemaVersion: ProfileSchemaV1,
		ProfileID:     "test-profile",
		Entries: []ProfileEntry{
			{Name: "PATH", Validator: string(ValidatorPathList), MaxBytes: 128, Required: true},
			{Name: "TERM", Validator: string(ValidatorToken), MaxBytes: 64},
			{Name: "SSH_AUTH_SOCK", Validator: string(ValidatorPath), MaxBytes: 128},
			{Name: "RAW_VALUE", Validator: string(ValidatorRawSafe), MaxBytes: 128},
		},
	}
}

func TestProfileStrictDecodeAndSensitiveNamePolicy(t *testing.T) {
	if SensitiveNamePolicyV1 != "apg.environment-sensitive-name-policy/v1" {
		t.Fatalf("unexpected sensitive-name policy identity: %s", SensitiveNamePolicyV1)
	}
	profile := testProfile()
	data, err := MarshalProfile(profile)
	if err != nil {
		t.Fatal(err)
	}
	decoded, err := DecodeProfile(data)
	if err != nil {
		t.Fatal(err)
	}
	if FingerprintProfile(decoded) != FingerprintProfile(profile) {
		t.Fatal("profile fingerprint changed after canonical round trip")
	}
	for _, input := range []string{
		`{"schema_version":"apg.environment-profile/v1","profile_id":"p","entries":[],"unknown":true}`,
		`{"schema_version":"apg.environment-profile/v1","profile_id":"p","entries":[],"entries":[]}`,
	} {
		if _, err := DecodeProfile([]byte(input)); err == nil {
			t.Fatalf("accepted unsafe profile JSON: %s", input)
		}
	}
	for _, name := range []string{"DB_PASSWORD", "API_TOKEN", "PRIVATE_KEY", "AWS_SECRET_ACCESS_KEY", "GPG_PASSPHRASE"} {
		bad := Profile{
			SchemaVersion: ProfileSchemaV1,
			ProfileID:     "p",
			Entries:       []ProfileEntry{{Name: name, Validator: "raw_safe", MaxBytes: 32}},
		}
		if err := ValidateProfile(bad); !errors.Is(err, ErrSensitiveName) {
			t.Fatalf("sensitive name %q error = %v", name, err)
		}
	}
	if err := ValidateProfile(profile); err != nil {
		t.Fatalf("SSH_AUTH_SOCK capability path rejected: %v", err)
	}
}

func TestValidatorsParityFamilies(t *testing.T) {
	cases := []struct {
		name      string
		validator string
		good      string
		bad       string
	}{
		{"bool", "bool", "yes", "maybe"},
		{"command", "command", "", "\x00"},
		{"host", "host", "db.example:5432", "db/example"},
		{"integer", "integer", "-12", "+12"},
		{"path", "path", "/tmp/work", "   "},
		{"path_list", "path_list", "/bin:/usr/bin", "/bin::/usr/bin"},
		{"port", "port", "65535", "65536"},
		{"raw_safe", "raw_safe", "shell * chars", "bad\nvalue"},
		{"token", "token", "xterm-256color", "bad value"},
		{"token_list", "token_list", "one,two", "one,,two"},
		{"uri", "uri", "https://example.test/a", "example.test/a"},
		{"uri_or_path", "uri_or_path", "/tmp/work", "   "},
	}
	for _, test := range cases {
		t.Run(test.name, func(t *testing.T) {
			if err := ValidateValue(test.good, test.validator, 256); err != nil {
				t.Fatalf("good value rejected: %v", err)
			}
			if err := ValidateValue(test.bad, test.validator, 256); err == nil {
				t.Fatal("bad value accepted")
			}
		})
	}
}

func TestFlakesValidatorParityFixture(t *testing.T) {
	_, sourceFile, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("runtime caller unavailable")
	}
	fixturePath := filepath.Join(filepath.Dir(sourceFile), "..", "src", "test", "fixtures", "apg98-environment", "validator-cases.json")
	data, err := os.ReadFile(fixturePath)
	if err != nil {
		t.Fatal(err)
	}
	type outcomes struct {
		Accepted []string `json:"accepted"`
		Rejected []string `json:"rejected"`
	}
	fixture := make(map[string]outcomes)
	if err := json.Unmarshal(data, &fixture); err != nil {
		t.Fatal(err)
	}
	if len(fixture) != len(knownValidators) {
		t.Fatalf("validator fixture count = %d, want %d", len(fixture), len(knownValidators))
	}
	for validator := range knownValidators {
		cases, present := fixture[validator]
		if !present || len(cases.Accepted) == 0 || len(cases.Rejected) == 0 {
			t.Fatalf("validator fixture is incomplete: %s", validator)
		}
		t.Run(validator, func(t *testing.T) {
			for _, value := range cases.Accepted {
				if err := ValidateValue(value, validator, 4096); err != nil {
					t.Fatalf("accepted fixture value rejected: %v", err)
				}
			}
			for _, value := range cases.Rejected {
				if err := ValidateValue(value, validator, 4096); err == nil {
					t.Fatal("rejected fixture value accepted")
				}
			}
		})
	}
}

func TestCaptureExplicitMapMissingAndNoLeak(t *testing.T) {
	profile := testProfile()
	clock := fixedClock{now: time.Date(2026, 8, 22, 5, 0, 0, 123000000, time.UTC)}
	snapshot, err := Capture(context.Background(), CaptureRequest{
		Profile:     profile,
		Environment: map[string]string{"PATH": "/bin:/usr/bin", "TERM": "xterm-256color", "RAW_VALUE": "one"},
		Provenance:  SnapshotProvenance{Context: "unit"},
		Clock:       clock,
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(snapshot.Entries) != 3 || len(snapshot.MissingOptional) != 1 || snapshot.MissingOptional[0] != "SSH_AUTH_SOCK" {
		t.Fatalf("capture classification = %#v missing=%#v", snapshot.Entries, snapshot.MissingOptional)
	}
	if snapshot.ContentFingerprint == "" || snapshot.ProfileFingerprint == "" {
		t.Fatal("capture fingerprints are empty")
	}
	secret := "super-secret-value-should-not-appear"
	_, err = Capture(context.Background(), CaptureRequest{
		Profile:         Profile{SchemaVersion: ProfileSchemaV1, ProfileID: "safe", Entries: []ProfileEntry{{Name: "RAW_VALUE", Validator: "token", MaxBytes: 4, Required: true}}},
		Environment:     map[string]string{"RAW_VALUE": secret},
		Provenance:      SnapshotProvenance{Context: "unit"},
		ProducerVersion: "test",
	})
	if err == nil || strings.Contains(err.Error(), secret) || strings.Contains(err.Error(), "super-secret") {
		t.Fatalf("value leaked in capture error: %v", err)
	}
	if _, err := Capture(context.Background(), CaptureRequest{Profile: profile, Environment: map[string]string{"PATH": ""}, Provenance: SnapshotProvenance{Context: "unit"}}); !errors.Is(err, ErrMissingRequired) {
		t.Fatalf("empty required value error = %v", err)
	}
}

func TestStoreLoadNoChurnAndResolve(t *testing.T) {
	profile := testProfile()
	root := t.TempDir()
	firstTime := time.Date(2026, 8, 22, 5, 0, 0, 0, time.UTC)
	first, err := Capture(context.Background(), CaptureRequest{
		Profile:     profile,
		Environment: map[string]string{"PATH": "/bin:/usr/bin", "TERM": "xterm", "RAW_VALUE": "one"},
		Provenance:  SnapshotProvenance{Context: "test"},
		Clock:       fixedClock{now: firstTime},
	})
	if err != nil {
		t.Fatal(err)
	}
	stored, err := Store(context.Background(), StoreRequest{StorageRoot: root, Snapshot: first, Profile: &profile})
	if err != nil {
		t.Fatal(err)
	}
	if stored.Disposition != DispositionStored {
		t.Fatalf("first disposition = %s", stored.Disposition)
	}
	infoBefore, err := os.Stat(stored.Path)
	if err != nil {
		t.Fatal(err)
	}
	second, err := Capture(context.Background(), CaptureRequest{
		Profile:     profile,
		Environment: map[string]string{"PATH": "/bin:/usr/bin", "TERM": "xterm", "RAW_VALUE": "one"},
		Provenance:  SnapshotProvenance{Context: "different-context"},
		Clock:       fixedClock{now: firstTime.Add(time.Hour)},
	})
	if err != nil {
		t.Fatal(err)
	}
	reused, err := Store(context.Background(), StoreRequest{StorageRoot: root, Snapshot: second, Profile: &profile})
	if err != nil {
		t.Fatal(err)
	}
	if reused.Disposition != DispositionUnchanged {
		t.Fatalf("second disposition = %s", reused.Disposition)
	}
	infoAfter, err := os.Stat(stored.Path)
	if err != nil {
		t.Fatal(err)
	}
	if !os.SameFile(infoBefore, infoAfter) || !infoBefore.ModTime().Equal(infoAfter.ModTime()) {
		t.Fatal("equivalent store changed inode or mtime")
	}
	loaded, err := Load(context.Background(), LoadRequest{
		StorageRoot:     root,
		ProfileID:       profile.ProfileID,
		ExpectedProfile: &profile,
		Clock:           fixedClock{now: firstTime.Add(30 * time.Minute)},
	})
	if err != nil {
		t.Fatal(err)
	}
	if loaded.Age != 30*time.Minute || loaded.Stale {
		t.Fatalf("loaded age/stale = %s/%v", loaded.Age, loaded.Stale)
	}
	if _, err := Load(context.Background(), LoadRequest{StorageRoot: root, ProfileID: profile.ProfileID, ExpectedProfile: &profile, MaxAge: time.Minute, Clock: fixedClock{now: firstTime.Add(30 * time.Minute)}}); !errors.Is(err, ErrStale) {
		t.Fatalf("stale load error = %v", err)
	}
	isolated, err := Resolve(context.Background(), ResolveRequest{
		Snapshot:  loaded,
		Profile:   &profile,
		Overrides: map[string]string{"TERM": "override"},
		Base:      map[string]string{"TERM": "base", "OUTSIDE": "retained only in overlay"},
	})
	if err != nil {
		t.Fatal(err)
	}
	if isolated.Environment["TERM"] != "override" || isolated.Environment["OUTSIDE"] != "" || isolated.Provenance["TERM"].Source != sourceOverride {
		t.Fatalf("isolated resolution = %#v %#v", isolated.Environment, isolated.Provenance)
	}
	overlay, err := Resolve(context.Background(), ResolveRequest{
		Snapshot: loaded,
		Profile:  &profile,
		Mode:     ModeOverlay,
		Base:     map[string]string{"TERM": "base", "OUTSIDE": "retained"},
	})
	if err != nil {
		t.Fatal(err)
	}
	if overlay.Environment["TERM"] != "xterm" || overlay.Environment["OUTSIDE"] != "retained" || overlay.Provenance["TERM"].Source != sourceSnapshot {
		t.Fatalf("overlay resolution = %#v %#v", overlay.Environment, overlay.Provenance)
	}
}

func TestStoreReclaimsDeadLockAndRejectsTamper(t *testing.T) {
	profile := testProfile()
	root := t.TempDir()
	snapshot, err := Capture(context.Background(), CaptureRequest{Profile: profile, Environment: map[string]string{"PATH": "/bin"}, Provenance: SnapshotProvenance{Context: "unit"}})
	if err != nil {
		t.Fatal(err)
	}
	directory := filepath.Join(root, "environment", profile.ProfileID)
	if err := os.MkdirAll(directory, 0o700); err != nil {
		t.Fatal(err)
	}
	lockDir := filepath.Join(directory, ".lock")
	if err := os.Mkdir(lockDir, 0o700); err != nil {
		t.Fatal(err)
	}
	owner := lockOwner{PID: 99999999, InvocationID: "dead-lock", CreatedAt: time.Now().UTC()}
	ownerData, _ := json.Marshal(owner)
	if err := os.WriteFile(filepath.Join(lockDir, "owner.json"), append(ownerData, '\n'), 0o600); err != nil {
		t.Fatal(err)
	}
	if _, err := Store(context.Background(), StoreRequest{StorageRoot: root, Snapshot: snapshot, Profile: &profile}); err != nil {
		t.Fatalf("dead lock was not reclaimed: %v", err)
	}
	path := filepath.Join(directory, "current.json")
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	data = []byte(strings.Replace(string(data), snapshot.ContentFingerprint, strings.Repeat("0", 64), 1))
	if err := os.WriteFile(path, data, 0o600); err != nil {
		t.Fatal(err)
	}
	if _, err := Load(context.Background(), LoadRequest{StorageRoot: root, ProfileID: profile.ProfileID, ExpectedProfile: &profile}); !errors.Is(err, ErrFingerprint) {
		t.Fatalf("tampered fingerprint error = %v", err)
	}
}

func TestSemanticIdentityCanonicalStrictnessAndSafety(t *testing.T) {
	profile := testProfile()
	changedDescription := profile
	changedDescription.Entries = append([]ProfileEntry(nil), profile.Entries...)
	changedDescription.Entries[0].Description = "different wording"
	if FingerprintProfile(profile) != FingerprintProfile(changedDescription) {
		t.Fatal("description wording changed semantic profile identity")
	}
	snapshot, err := Capture(context.Background(), CaptureRequest{
		Profile:     profile,
		Environment: map[string]string{"PATH": "/bin"},
		Provenance:  SnapshotProvenance{Context: "canonical"},
		Clock:       fixedClock{now: time.Date(2026, 8, 22, 5, 0, 0, 0, time.UTC)},
	})
	if err != nil {
		t.Fatal(err)
	}
	canonical, err := MarshalSnapshot(snapshot)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.HasSuffix(string(canonical), "\n") || strings.Contains(string(canonical), " ") {
		t.Fatal("snapshot is not compact canonical JSON")
	}
	decoded, err := DecodeSnapshot(canonical)
	if err != nil || decoded.ContentFingerprint != snapshot.ContentFingerprint {
		t.Fatalf("snapshot round trip = %#v %v", decoded, err)
	}
	withoutNewline := bytesTrimFinalNewline(canonical)
	for _, input := range [][]byte{
		append(append([]byte(nil), withoutNewline...), []byte(`{"unknown":true}`)...),
		[]byte(strings.Replace(string(withoutNewline), `"schema_version":"apg.environment-snapshot/v1"`, `"schema_version":"apg.environment-snapshot/v1","schema_version":"apg.environment-snapshot/v1"`, 1)),
	} {
		if _, err := DecodeSnapshot(input); err == nil {
			t.Fatal("unsafe snapshot JSON accepted")
		}
	}
	forged := snapshot
	forged.Entries = []SnapshotEntry{{Name: "DB_PASSWORD", Validator: "raw_safe", Value: "secret", Source: SourceCapture}}
	forged.ContentFingerprint = FingerprintSnapshot(forged)
	if _, err := MarshalSnapshot(forged); !errors.Is(err, ErrSensitiveName) {
		t.Fatalf("forged sensitive snapshot error = %v", err)
	}
}

func TestLoadIsReadOnlyAndRejectsUnsafeFiles(t *testing.T) {
	profile := testProfile()
	aliasParent := t.TempDir()
	if err := os.Mkdir(filepath.Join(aliasParent, "real"), 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(filepath.Join(aliasParent, "real"), filepath.Join(aliasParent, "owned-link")); err != nil {
		t.Fatal(err)
	}
	linkedRoot := filepath.Join(aliasParent, "owned-link", "root")
	if _, err := Store(context.Background(), StoreRequest{StorageRoot: linkedRoot, Snapshot: mustCapture(t, profile, map[string]string{"PATH": "/bin"}), Profile: &profile}); !errors.Is(err, ErrUnsafePath) {
		t.Fatalf("owned intermediate symlink error = %v", err)
	}
	missingRoot := filepath.Join(t.TempDir(), "not-created")
	if _, err := Load(context.Background(), LoadRequest{StorageRoot: missingRoot, ProfileID: profile.ProfileID, ExpectedProfile: &profile}); err == nil {
		t.Fatal("missing snapshot unexpectedly loaded")
	}
	if _, err := os.Lstat(missingRoot); !os.IsNotExist(err) {
		t.Fatalf("Load created missing root: %v", err)
	}
	if _, err := Load(context.Background(), LoadRequest{StorageRoot: t.TempDir(), ProfileID: profile.ProfileID}); !errors.Is(err, ErrProfileMismatch) {
		t.Fatalf("nil expected profile error = %v", err)
	}
	root := t.TempDir()
	snapshot := mustCapture(t, profile, map[string]string{"PATH": "/bin"})
	stored, err := Store(context.Background(), StoreRequest{StorageRoot: root, Snapshot: snapshot, Profile: &profile})
	if err != nil {
		t.Fatal(err)
	}
	current := stored.Path
	other := filepath.Join(filepath.Dir(current), "other.json")
	if err := os.Link(current, other); err != nil {
		t.Fatal(err)
	}
	if _, err := Load(context.Background(), LoadRequest{StorageRoot: root, ProfileID: profile.ProfileID, ExpectedProfile: &profile}); !errors.Is(err, ErrUnsafePath) {
		t.Fatalf("hard-linked snapshot error = %v", err)
	}
	if err := os.Remove(other); err != nil {
		t.Fatal(err)
	}
	if err := os.Chmod(current, 0o640); err != nil {
		t.Fatal(err)
	}
	if _, err := Load(context.Background(), LoadRequest{StorageRoot: root, ProfileID: profile.ProfileID, ExpectedProfile: &profile}); !errors.Is(err, ErrUnsafePath) {
		t.Fatalf("wrong-mode snapshot error = %v", err)
	}
	if err := os.Chmod(current, 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.Remove(current); err != nil {
		t.Fatal(err)
	}
	target := filepath.Join(filepath.Dir(current), "target.json")
	if err := os.WriteFile(target, []byte("not a snapshot"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(target, current); err != nil {
		t.Fatal(err)
	}
	if _, err := Load(context.Background(), LoadRequest{StorageRoot: root, ProfileID: profile.ProfileID, ExpectedProfile: &profile}); !errors.Is(err, ErrUnsafePath) {
		t.Fatalf("symlink snapshot error = %v", err)
	}
}

func TestLockSafetyCancellationAndConcurrency(t *testing.T) {
	profile := testProfile()
	snapshot := mustCapture(t, profile, map[string]string{"PATH": "/bin"})
	root := t.TempDir()
	directory := filepath.Join(root, "environment", profile.ProfileID)
	if err := os.MkdirAll(directory, 0o700); err != nil {
		t.Fatal(err)
	}
	lockDir := filepath.Join(directory, ".lock")
	if err := os.Mkdir(lockDir, 0o700); err != nil {
		t.Fatal(err)
	}
	live := lockOwner{PID: os.Getpid(), InvocationID: "live", CreatedAt: time.Now().UTC()}
	data, _ := json.Marshal(live)
	if err := os.WriteFile(filepath.Join(lockDir, "owner.json"), append(data, '\n'), 0o600); err != nil {
		t.Fatal(err)
	}
	if _, err := Store(context.Background(), StoreRequest{StorageRoot: root, Snapshot: snapshot, Profile: &profile}); !errors.Is(err, ErrLockConflict) {
		t.Fatalf("live lock error = %v", err)
	}
	if _, err := os.Stat(lockDir); err != nil {
		t.Fatalf("live lock was removed: %v", err)
	}
	if err := os.Remove(filepath.Join(lockDir, "owner.json")); err != nil {
		t.Fatal(err)
	}
	malformed, _ := json.Marshal(map[string]any{"pid": os.Getpid()})
	if err := os.WriteFile(filepath.Join(lockDir, "owner.json"), append(malformed, '\n'), 0o600); err != nil {
		t.Fatal(err)
	}
	if _, err := Store(context.Background(), StoreRequest{StorageRoot: root, Snapshot: snapshot, Profile: &profile}); !errors.Is(err, ErrLockConflict) {
		t.Fatalf("malformed lock error = %v", err)
	}
	if err := os.RemoveAll(lockDir); err != nil {
		t.Fatal(err)
	}
	canceled, cancel := context.WithCancel(context.Background())
	cancel()
	canceledRoot := filepath.Join(t.TempDir(), "cancelled")
	if _, err := Store(canceled, StoreRequest{StorageRoot: canceledRoot, Snapshot: snapshot, Profile: &profile}); !errors.Is(err, context.Canceled) {
		t.Fatalf("cancelled store error = %v", err)
	}
	if _, err := os.Lstat(canceledRoot); !os.IsNotExist(err) {
		t.Fatalf("cancelled store created state: %v", err)
	}
	concurrentRoot := t.TempDir()
	alternate := mustCapture(t, profile, map[string]string{"PATH": "/bin", "RAW_VALUE": "alternate"})
	var group sync.WaitGroup
	errorsCh := make(chan error, 8)
	for i := 0; i < 8; i++ {
		group.Add(1)
		go func(index int) {
			defer group.Done()
			candidate := snapshot
			if index%2 != 0 {
				candidate = alternate
			}
			_, err := Store(context.Background(), StoreRequest{StorageRoot: concurrentRoot, Snapshot: candidate, Profile: &profile, Timeout: 2 * time.Second})
			errorsCh <- err
		}(i)
	}
	group.Wait()
	close(errorsCh)
	for err := range errorsCh {
		if err != nil {
			t.Fatalf("concurrent store error = %v", err)
		}
	}
	loaded, err := Load(context.Background(), LoadRequest{StorageRoot: concurrentRoot, ProfileID: profile.ProfileID, ExpectedProfile: &profile})
	if err != nil || (loaded.ContentFingerprint != snapshot.ContentFingerprint && loaded.ContentFingerprint != alternate.ContentFingerprint) {
		t.Fatalf("concurrent publication is not one complete candidate: %#v %v", loaded, err)
	}
}

func TestPromptScaleNoChurnAndInputOwnership(t *testing.T) {
	profile := testProfile()
	root := t.TempDir()
	environment := map[string]string{"PATH": "/bin", "TERM": "xterm", "RAW_VALUE": "one"}
	snapshot := mustCapture(t, profile, environment)
	original := cloneStringMap(environment)
	first, err := Store(context.Background(), StoreRequest{StorageRoot: root, Snapshot: snapshot, Profile: &profile})
	if err != nil {
		t.Fatal(err)
	}
	info, err := os.Stat(first.Path)
	if err != nil {
		t.Fatal(err)
	}
	for i := 0; i < 100; i++ {
		repeated, err := Store(context.Background(), StoreRequest{StorageRoot: root, Snapshot: snapshot, Profile: &profile})
		if err != nil || repeated.Disposition != DispositionUnchanged {
			t.Fatalf("repeat %d = %s %v", i, repeated.Disposition, err)
		}
	}
	finalInfo, err := os.Stat(first.Path)
	if err != nil || !os.SameFile(info, finalInfo) || !info.ModTime().Equal(finalInfo.ModTime()) {
		t.Fatalf("prompt-scale write changed file: %v", err)
	}
	entries, err := os.ReadDir(filepath.Dir(first.Path))
	if err != nil {
		t.Fatal(err)
	}
	if len(entries) != 2 || entries[0].Name() == ".lock" || entries[1].Name() == ".lock" {
		t.Fatalf("prompt-scale left unexpected storage debt: %#v", entries)
	}
	seenCurrent, seenGuard := false, false
	for _, entry := range entries {
		seenCurrent = seenCurrent || entry.Name() == "current.json"
		seenGuard = seenGuard || entry.Name() == ".lock.guard"
	}
	if !seenCurrent || !seenGuard {
		t.Fatalf("prompt-scale artifacts = %#v", entries)
	}
	if !mapsEqual(environment, original) {
		t.Fatal("Capture mutated supplied environment map")
	}
	changed := cloneStringMap(environment)
	changed["RAW_VALUE"] = "two"
	changedSnapshot := mustCapture(t, profile, changed)
	changedStored, err := Store(context.Background(), StoreRequest{StorageRoot: root, Snapshot: changedSnapshot, Profile: &profile})
	if err != nil || changedStored.Disposition != DispositionStored {
		t.Fatalf("changed store = %s %v", changedStored.Disposition, err)
	}
	base := map[string]string{"TERM": "base", "OUTSIDE": "untouched"}
	overrides := map[string]string{"TERM": "override"}
	baseCopy, overrideCopy := cloneStringMap(base), cloneStringMap(overrides)
	resolved, err := Resolve(context.Background(), ResolveRequest{Profile: &profile, Snapshot: changedSnapshot, Mode: ModeOverlay, Base: base, Overrides: overrides})
	if err != nil || resolved.Environment["TERM"] != "override" {
		t.Fatalf("overlay = %#v %v", resolved, err)
	}
	if !mapsEqual(base, baseCopy) || !mapsEqual(overrides, overrideCopy) {
		t.Fatal("Resolve mutated supplied maps")
	}
}

func TestMetadataBoundsAndStaleReplacementIdentity(t *testing.T) {
	profile := testProfile()
	tooLarge, err := Capture(context.Background(), CaptureRequest{Profile: profile, Environment: map[string]string{"PATH": "/bin"}, Provenance: SnapshotProvenance{Context: strings.Repeat("x", 1025)}})
	if err == nil || tooLarge.SchemaVersion != "" {
		t.Fatalf("oversized provenance accepted: %#v %v", tooLarge, err)
	}
	root := t.TempDir()
	directory := filepath.Join(root, "environment", profile.ProfileID)
	if err := os.MkdirAll(directory, 0o700); err != nil {
		t.Fatal(err)
	}
	lockPath := filepath.Join(directory, ".lock")
	if err := os.Mkdir(lockPath, 0o700); err != nil {
		t.Fatal(err)
	}
	old := lockOwner{PID: 99999999, InvocationID: "old", CreatedAt: time.Now().UTC()}
	oldData, _ := json.Marshal(old)
	ownerPath := filepath.Join(lockPath, "owner.json")
	if err := os.WriteFile(ownerPath, append(oldData, '\n'), 0o600); err != nil {
		t.Fatal(err)
	}
	candidate, err := lockIsReclaimable(lockPath)
	if err != nil || candidate == nil {
		t.Fatalf("stale candidate = %#v %v", candidate, err)
	}
	if err := os.Remove(ownerPath); err != nil {
		t.Fatal(err)
	}
	newOwner := lockOwner{PID: os.Getpid(), InvocationID: "new", CreatedAt: time.Now().UTC()}
	newData, _ := json.Marshal(newOwner)
	if err := os.WriteFile(ownerPath, append(newData, '\n'), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := reclaimLock(candidate); !errors.Is(err, ErrLockConflict) {
		t.Fatalf("replacement lock reclaim error = %v", err)
	}
	if _, err := os.Stat(lockPath); err != nil {
		t.Fatalf("replacement lock was removed: %v", err)
	}
}

func mustCapture(t *testing.T, profile Profile, values map[string]string) Snapshot {
	t.Helper()
	snapshot, err := Capture(context.Background(), CaptureRequest{Profile: profile, Environment: values, Provenance: SnapshotProvenance{Context: "test"}, Clock: fixedClock{now: time.Date(2026, 8, 22, 5, 0, 0, 0, time.UTC)}})
	if err != nil {
		t.Fatal(err)
	}
	return snapshot
}

func bytesTrimFinalNewline(value []byte) []byte {
	if len(value) > 0 && value[len(value)-1] == '\n' {
		return value[:len(value)-1]
	}
	return value
}

func cloneStringMap(input map[string]string) map[string]string {
	clone := make(map[string]string, len(input))
	for key, value := range input {
		clone[key] = value
	}
	return clone
}

func mapsEqual(left, right map[string]string) bool {
	if len(left) != len(right) {
		return false
	}
	for key, value := range left {
		if right[key] != value {
			return false
		}
	}
	return true
}
