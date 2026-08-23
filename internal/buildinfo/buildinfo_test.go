package buildinfo

import (
	"bytes"
	"encoding/json"
	"runtime"
	"testing"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/schema"
	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/skills"
)

func TestCurrentSourceDefaultsAndSchemaAuthority(t *testing.T) {
	info := Current()
	metadata, err := skills.Metadata()
	if err != nil {
		t.Fatal(err)
	}
	if info.Version != "devel" || info.CorpusFingerprint != "devel" || info.EmbeddedCorpusFingerprint != metadata.Fingerprint || info.CorpusFingerprintVerified {
		t.Fatalf("source defaults = %q %q", info.Version, info.CorpusFingerprint)
	}
	if info.SchemaVersion != BuildInfoSchema {
		t.Fatalf("build-info schema = %q", info.SchemaVersion)
	}
	if info.Target != runtime.GOOS+"/"+runtime.GOARCH {
		t.Fatalf("target = %q", info.Target)
	}
	show, _ := schema.GitShowRecord.FormatVersion()
	diff, _ := schema.GitDiffRecord.FormatVersion()
	ops, _ := schema.OperationalRecord.FormatVersion()
	want := SchemaVersions{Envelope: schema.EnvelopeVersion, GitShow: show, GitDiff: diff, Operational: ops}
	if info.ReportSchemaVersion != want {
		t.Fatalf("schema versions = %#v", info.ReportSchemaVersion)
	}
}

func TestReleaseLikeCorpusVerificationFailsClosed(t *testing.T) {
	metadata, err := skills.Metadata()
	if err != nil {
		t.Fatal(err)
	}
	oldVersion, oldFingerprint := Version, CorpusFingerprint
	t.Cleanup(func() { Version, CorpusFingerprint = oldVersion, oldFingerprint })
	Version, CorpusFingerprint = "0.6.0", metadata.Fingerprint
	content, err := JSON()
	if err != nil {
		t.Fatal(err)
	}
	var info Info
	if err := json.Unmarshal(content, &info); err != nil {
		t.Fatal(err)
	}
	if !info.CorpusFingerprintVerified || info.CorpusFingerprint != info.EmbeddedCorpusFingerprint {
		t.Fatalf("release corpus = %#v", info)
	}
	CorpusFingerprint = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
	if _, err := JSON(); err == nil {
		t.Fatal("mismatched release corpus was accepted")
	}
}

func TestJSONIsStableAndRoundTrips(t *testing.T) {
	first, err := JSON()
	if err != nil {
		t.Fatal(err)
	}
	second, err := JSON()
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(first, second) || len(first) == 0 || first[len(first)-1] != '\n' {
		t.Fatalf("unstable JSON: %q / %q", first, second)
	}
	var decoded Info
	if err := json.Unmarshal(first, &decoded); err != nil {
		t.Fatal(err)
	}
	if decoded.ModulePath == "" || decoded.ModuleVersion == "" || decoded.GoVersion == "" {
		t.Fatalf("incomplete module build information: %#v", decoded)
	}
	if len(decoded.SupportedTargets) != 3 {
		t.Fatalf("supported targets = %#v", decoded.SupportedTargets)
	}
}
