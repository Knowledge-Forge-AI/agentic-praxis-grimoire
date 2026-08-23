package hotspot

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func writeFixture(t *testing.T, root, name, content string) {
	t.Helper()
	path := filepath.Join(root, filepath.FromSlash(name))
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(content), 0o600); err != nil {
		t.Fatal(err)
	}
}

func testRequest(t *testing.T, root string) Request {
	t.Helper()
	if filepath.IsAbs(root) {
		resolved, err := filepath.EvalSymlinks(root)
		if err != nil {
			t.Fatal(err)
		}
		root = resolved
	}
	request := DefaultRequest(root)
	request.RootID = "fixture"
	request.ToolVersion = "test"
	return request
}

func fileByPath(t *testing.T, report Report, path string) FileRow {
	t.Helper()
	for _, row := range report.Files {
		if row.Path == path {
			return row
		}
	}
	t.Fatalf("file %q missing from report", path)
	return FileRow{}
}

func ownerByName(t *testing.T, report Report, name string) OwnerRow {
	t.Helper()
	for _, row := range report.Owners {
		if row.DisplayName == name {
			return row
		}
	}
	t.Fatalf("owner %q missing from report", name)
	return OwnerRow{}
}

func metricValue(t *testing.T, metrics []Metric, name string) int64 {
	t.Helper()
	for _, metric := range metrics {
		if metric.Name == name && metric.Value != nil {
			return *metric.Value
		}
	}
	t.Fatalf("available metric %q missing from %#v", name, metrics)
	return 0
}

func metricAvailability(t *testing.T, metrics []Metric, name string) Availability {
	t.Helper()
	for _, metric := range metrics {
		if metric.Name == name {
			return metric.Availability
		}
	}
	t.Fatalf("metric %q missing from %#v", name, metrics)
	return ""
}

func TestAnalyzeGoMetricsAndDeterministicRenderers(t *testing.T) {
	root := t.TempDir()
	writeFixture(t, root, "main.go", `package sample

func Add(a, b int) int {
	if a > 0 && b > 0 {
		for i := 0; i < a; i++ {
			b += i
		}
	}
	return b
}

var Closure = func(value int) int { return value + 1 }
`)
	writeFixture(t, root, "guide.md", "# Guide\n\nProse [link](target).\n\n```go\nfmt.Println(1)\n```\n")

	first, err := Analyze(context.Background(), testRequest(t, root))
	if err != nil {
		t.Fatal(err)
	}
	second, err := Analyze(context.Background(), testRequest(t, root))
	if err != nil {
		t.Fatal(err)
	}
	firstJSON, err := MarshalJSON(first)
	if err != nil {
		t.Fatal(err)
	}
	secondJSON, err := MarshalJSON(second)
	if err != nil {
		t.Fatal(err)
	}
	if string(firstJSON) != string(secondJSON) || first.Fingerprint != second.Fingerprint {
		t.Fatalf("repeat scan differs\nfirst: %s\nsecond: %s", firstJSON, secondJSON)
	}
	if first.SchemaVersion != ReportSchemaV1 || first.CompletionStatus != CompletionComplete {
		t.Fatalf("report identity = %#v", first)
	}
	if !strings.HasPrefix(first.Fingerprint, "sha256:") {
		t.Fatalf("fingerprint = %q", first.Fingerprint)
	}
	assertGoFixtureMetrics(t, first)
	assertMarkdownFixtureMetrics(t, first)
	assertFixtureRenderers(t, first)
}

func assertGoFixtureMetrics(t *testing.T, report Report) {
	t.Helper()
	owner := ownerByName(t, report, "Add")
	if got := metricValue(t, owner.Metrics, MetricStatements); got != 6 {
		t.Fatalf("Add statements = %d, want 6", got)
	}
	if got := metricValue(t, owner.Metrics, MetricCyclomatic); got != 4 {
		t.Fatalf("Add cyclomatic = %d, want 4", got)
	}
	if got := metricValue(t, owner.Metrics, MetricNesting); got != 2 {
		t.Fatalf("Add nesting = %d, want 2", got)
	}
	if got := metricValue(t, owner.Metrics, MetricParameters); got != 2 {
		t.Fatalf("Add parameters = %d, want 2", got)
	}
	closure := ownerByName(t, report, "func literal at 12:15")
	if got := metricValue(t, closure.Metrics, MetricStatements); got != 1 {
		t.Fatalf("closure statements = %d, want 1", got)
	}
}

func assertMarkdownFixtureMetrics(t *testing.T, report Report) {
	t.Helper()
	markdown := fileByPath(t, report, "guide.md")
	if got := metricValue(t, markdown.Metrics, MetricProseLines); got != 2 {
		t.Fatalf("Markdown prose lines = %d, want 2", got)
	}
	if got := metricValue(t, markdown.Metrics, MetricFenceLines); got != 1 {
		t.Fatalf("Markdown fence lines = %d, want 1", got)
	}
	if metricAvailability(t, markdown.Metrics, MetricCyclomatic) != AvailabilityNotApplicable {
		t.Fatal("Markdown cyclomatic must be not-applicable")
	}
}

func assertFixtureRenderers(t *testing.T, report Report) {
	t.Helper()
	terminal, err := RenderTerminal(report)
	if err != nil {
		t.Fatal(err)
	}
	for _, text := range []string{"fixture", "Largest files", "Hotspot candidates", "sha256:"} {
		if !strings.Contains(string(terminal), text) {
			t.Fatalf("terminal missing %q:\n%s", text, terminal)
		}
	}
	markdownReport, err := RenderMarkdown(report)
	if err != nil {
		t.Fatal(err)
	}
	for _, heading := range []string{"## Table of contents", "## Scan configuration and exclusions", "## Capability and confidence legend", "## Refactoring candidates", "## Unavailable and deferred metrics", "## Appendix: all analyzed files"} {
		if !strings.Contains(string(markdownReport), heading) {
			t.Fatalf("Markdown missing %q", heading)
		}
	}
}

func TestClassificationInventoryAndUnavailableSemantics(t *testing.T) {
	root := t.TempDir()
	fixtures := map[string]string{
		"a.py": "print('x')\n", "a.java": "class A {}\n", "a.kt": "class A\n",
		"a.js": "const x = 1;\n", "a.ts": "const x: number = 1;\n",
		"a.jsx": "const x = <div/>;\n", "a.tsx": "const x: JSX.Element = <div/>;\n",
		"a.html": "<h1 id=\"x\">X</h1>\n", "a.css": "a { color: red; }\n",
		"a.xml": "<root a=\"b\"><child/></root>\n", "a.plist": "<?xml version=\"1.0\"?><plist><dict/></plist>\n",
		"a.json": "{\"a\":[1,{\"b\":2}]}\n", "a.jsonc": "{\"a\": 1,}\n",
		"a.yaml": "root:\n  child: value\n", "a.toml": "[root]\nchild = 1\n",
		"a.tf": "resource \"x\" \"y\" { value = 1 }\n", "build.gradle": "plugins { id 'java' }\n",
		"a.sql": "SELECT * FROM x WHERE id = 1;\n", "a.bash": "#!/bin/bash\necho x\n",
		"a.zsh": "#!/bin/zsh\nprint x\n", "a.sh": "#!/bin/sh\necho x\n",
		"run": "#!/usr/bin/env bash\necho x\n", "Dockerfile": "FROM scratch AS base\nRUN echo x \\\n+ && echo y\n",
		"Vagrantfile": "Vagrant.configure(\"2\") do |config|\nend\n",
		"a.mdx":       "# X\n\n<Component />\n", "a.astro": "---\nconst x = 1\n---\n<h1>X</h1>\n",
		"unknown.xyz": "ordinary text\n", "ignored-extensionless": "ordinary text\n",
	}
	for name, content := range fixtures {
		writeFixture(t, root, name, content)
	}
	writeFixture(t, root, "binary.plist", "bplist00\x00\x01")
	report, err := Analyze(context.Background(), testRequest(t, root))
	if err != nil {
		t.Fatal(err)
	}
	want := map[string]Language{
		"a.py": LanguagePython, "a.java": LanguageJava, "a.kt": LanguageKotlin,
		"a.js": LanguageJavaScript, "a.ts": LanguageTypeScript, "a.jsx": LanguageJSX, "a.tsx": LanguageTSX,
		"a.html": LanguageHTML, "a.css": LanguageCSS, "a.xml": LanguageXML, "a.plist": LanguageXMLPlist,
		"binary.plist": LanguageBinaryPlist, "a.json": LanguageJSON, "a.jsonc": LanguageJSONFamily,
		"a.yaml": LanguageYAML, "a.toml": LanguageTOML, "a.tf": LanguageTerraform,
		"build.gradle": LanguageGradle, "a.sql": LanguageSQL, "a.bash": LanguageBash,
		"a.zsh": LanguageZsh, "a.sh": LanguagePOSIXShell, "run": LanguageBash,
		"Dockerfile": LanguageDockerfile, "Vagrantfile": LanguageVagrantfile,
		"a.mdx": LanguageMDX, "a.astro": LanguageAstro, "unknown.xyz": LanguageUnknown,
	}
	if len(report.Files) != len(want) {
		t.Fatalf("files = %d, want %d: %#v", len(report.Files), len(want), report.Files)
	}
	for path, language := range want {
		row := fileByPath(t, report, path)
		if row.Language != language {
			t.Errorf("%s language = %q, want %q", path, row.Language, language)
		}
	}
	python := fileByPath(t, report, "a.py")
	for _, name := range []string{MetricStatements, MetricSymbols, MetricCyclomatic, MetricNesting, MetricProceduralSize} {
		if metricAvailability(t, python.Metrics, name) != AvailabilityUnavailable {
			t.Errorf("Python %s must be unavailable", name)
		}
	}
	jsonDialect := fileByPath(t, report, "a.jsonc")
	if jsonDialect.ParseFailure == "" || metricAvailability(t, jsonDialect.Metrics, MetricNesting) != AvailabilityUnavailable {
		t.Fatalf("JSON dialect parse result = %#v", jsonDialect)
	}
	if len(report.Capabilities) != 25 {
		t.Fatalf("capability rows = %d, want 25", len(report.Capabilities))
	}
	if len(report.DeferredCapabilities) != 1 || report.DeferredCapabilities[0].Name != "growth/churn" || report.DeferredCapabilities[0].Status != "deferred" {
		t.Fatalf("deferred capabilities = %#v", report.DeferredCapabilities)
	}
}

func TestCommittedClassificationCorpus(t *testing.T) {
	working, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	root, err := filepath.EvalSymlinks(filepath.Join(working, "testdata", "classification"))
	if err != nil {
		t.Fatal(err)
	}
	report, err := Analyze(context.Background(), testRequest(t, root))
	if err != nil {
		t.Fatal(err)
	}
	want := map[string]Language{
		"sample.go": LanguageGo, "generated.go": LanguageGo, "broken.go": LanguageGo,
		"sample.md": LanguageMarkdown, "sample.mdx": LanguageMDX, "sample.astro": LanguageAstro,
		"sample.py": LanguagePython, "Sample.java": LanguageJava, "Sample.kt": LanguageKotlin,
		"sample.js": LanguageJavaScript, "sample.ts": LanguageTypeScript, "sample.jsx": LanguageJSX, "sample.tsx": LanguageTSX,
		"sample.html": LanguageHTML, "sample.css": LanguageCSS, "sample.xml": LanguageXML, "sample.plist": LanguageXMLPlist,
		"binary.plist": LanguageBinaryPlist, "sample.json": LanguageJSON, "sample.jsonc": LanguageJSONFamily,
		"sample.yaml": LanguageYAML, "sample.toml": LanguageTOML, "sample.tf": LanguageTerraform,
		"build.gradle": LanguageGradle, "sample.sql": LanguageSQL, "sample.bash": LanguageBash,
		"sample.zsh": LanguageZsh, "sample.sh": LanguagePOSIXShell, "extensionless-shell": LanguageBash,
		"Dockerfile": LanguageDockerfile, "Vagrantfile": LanguageVagrantfile, "unsupported.xyz": LanguageUnknown,
	}
	if len(report.Files) != len(want) {
		t.Fatalf("committed corpus files = %d, want %d", len(report.Files), len(want))
	}
	for path, language := range want {
		if got := fileByPath(t, report, path).Language; got != language {
			t.Errorf("%s = %s, want %s", path, got, language)
		}
	}
	jsonRow := fileByPath(t, report, "sample.json")
	if got := metricValue(t, jsonRow.Metrics, MetricKeys); got != 4 {
		t.Fatalf("duplicate-preserving JSON key count = %d, want 4", got)
	}
	if !fileByPath(t, report, "generated.go").Generated {
		t.Fatal("committed generated Go fixture was not detected")
	}
}

func TestRootBoundsCancellationAndSymlinks(t *testing.T) {
	root := t.TempDir()
	writeFixture(t, root, "a.go", "package p\n")
	writeFixture(t, root, "b.go", "package p\n")
	request := testRequest(t, root)
	request.Limits.MaxFiles = 1
	if _, err := Analyze(context.Background(), request); !errors.Is(err, ErrLimitExceeded) {
		t.Fatalf("max files error = %v", err)
	}
	request = testRequest(t, root)
	request.Limits.MaxBytesPerFile = 4
	if _, err := Analyze(context.Background(), request); !errors.Is(err, ErrLimitExceeded) {
		t.Fatalf("per-file bytes error = %v", err)
	}
	cancelled, cancel := context.WithCancel(context.Background())
	cancel()
	if _, err := Analyze(cancelled, testRequest(t, root)); !errors.Is(err, context.Canceled) {
		t.Fatalf("cancel error = %v", err)
	}
	outside := t.TempDir()
	writeFixture(t, outside, "secret.go", "package secret\n")
	if err := os.Symlink(filepath.Join(outside, "secret.go"), filepath.Join(root, "escape.go")); err != nil {
		t.Fatal(err)
	}
	report, err := Analyze(context.Background(), testRequest(t, root))
	if err != nil {
		t.Fatal(err)
	}
	for _, row := range report.Files {
		if row.Path == "escape.go" {
			t.Fatal("symlink target was analyzed")
		}
	}
	found := false
	for _, exclusion := range report.Exclusions {
		if exclusion.Rule == "symlink" && exclusion.Files == 1 {
			found = true
		}
	}
	if !found {
		t.Fatalf("symlink exclusion missing: %#v", report.Exclusions)
	}

	relative := testRequest(t, ".")
	if _, err := Analyze(context.Background(), relative); !errors.Is(err, ErrInvalidRequest) {
		t.Fatalf("relative root error = %v", err)
	}
	symlinkRoot := filepath.Join(t.TempDir(), "root")
	if err := os.Symlink(root, symlinkRoot); err != nil {
		t.Fatal(err)
	}
	symlinkRequest := DefaultRequest(symlinkRoot)
	symlinkRequest.RootID = "symlink-root"
	symlinkRequest.ToolVersion = "test"
	if _, err := Analyze(context.Background(), symlinkRequest); !errors.Is(err, ErrRootSafety) {
		t.Fatalf("symlink root error = %v", err)
	}
}

func TestElapsedLimitAndStrictRequestJSON(t *testing.T) {
	root := t.TempDir()
	writeFixture(t, root, "a.go", "package p\n")
	request := testRequest(t, root)
	request.Limits.MaxDuration = time.Nanosecond
	if _, err := Analyze(context.Background(), request); !errors.Is(err, ErrLimitExceeded) && !errors.Is(err, context.DeadlineExceeded) {
		t.Fatalf("elapsed limit error = %v", err)
	}
	duplicate := `{"schema_version":"apg.hotspot-request/v1","schema_version":"apg.hotspot-request/v1"}`
	if _, err := ParseRequestJSON([]byte(duplicate)); !errors.Is(err, ErrInvalidRequest) {
		t.Fatalf("duplicate request key error = %v", err)
	}
}

func TestAnalyzeGoBodylessDeclarationsAndSizeFloor(t *testing.T) {
	root := t.TempDir()
	writeFixture(t, root, "asm_stub.go", "package sample\n\n//go:noescape\nfunc memmove(to, from, n uintptr)\n")
	writeFixture(t, root, "small.md", "# Small\n")
	writeFixture(t, root, "large.go", "package sample\n\n"+strings.Repeat("func F() int { return 1 }\n", 100))

	report, err := Analyze(context.Background(), testRequest(t, root))
	if err != nil {
		t.Fatalf("Analyze failed on bodyless Go func: %v", err)
	}

	owner := ownerByName(t, report, "memmove")
	if got := metricValue(t, owner.Metrics, MetricStatements); got != 0 {
		t.Fatalf("memmove statements = %d, want 0", got)
	}
	if got := metricValue(t, owner.Metrics, MetricCyclomatic); got != 1 {
		t.Fatalf("memmove cyclomatic = %d, want 1", got)
	}
	if got := metricValue(t, owner.Metrics, MetricNesting); got != 0 {
		t.Fatalf("memmove nesting = %d, want 0", got)
	}
	if got := metricValue(t, owner.Metrics, MetricParameters); got != 3 {
		t.Fatalf("memmove parameters = %d, want 3", got)
	}

	for _, candidate := range report.RefactoringCandidates {
		if candidate.Path == "small.md" {
			for _, code := range candidate.ReasonCodes {
				if code == "large-file" {
					t.Fatalf("small.md under 1024 bytes got large-file reason code: %#v", candidate)
				}
			}
		}
	}
}
