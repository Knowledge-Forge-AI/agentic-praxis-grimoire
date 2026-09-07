package xoconsumer

import (
	"context"
	"encoding/json"
	"errors"
	"go/ast"
	"go/parser"
	"go/token"
	"go/types"
	"os/exec"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
	"time"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/footprint"
	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/schema"
	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/skills"
)

func fieldNames(idents []*ast.Ident) string {
	if len(idents) == 0 {
		return "<anonymous>"
	}
	names := make([]string, len(idents))
	for i, id := range idents {
		names[i] = id.Name
	}
	return strings.Join(names, ", ")
}

// checkASTForAPGRTypes inspects all exported struct fields and exported function/method
// signatures in an AST for disallowed APGR domain type references.
func checkASTForAPGRTypes(node *ast.File) []string {
	disallowedTypeSubstrings := []string{
		"footprint.",
		"skills.",
		"schema.",
		"agentic-praxis-grimoire",
	}
	var leaks []string

	for _, decl := range node.Decls {
		switch d := decl.(type) {
		case *ast.GenDecl:
			if d.Tok == token.TYPE {
				for _, spec := range d.Specs {
					ts, ok := spec.(*ast.TypeSpec)
					if !ok || !ast.IsExported(ts.Name.Name) {
						continue
					}
					st, ok := ts.Type.(*ast.StructType)
					if !ok {
						leaks = append(leaks, "unsupported exported non-struct type definition "+ts.Name.Name+": "+types.ExprString(ts.Type))
						continue
					}
					for _, field := range st.Fields.List {
						fieldTypeStr := types.ExprString(field.Type)
						if fieldTypeStr == "" {
							leaks = append(leaks, "unhandled or empty type string for field "+fieldNames(field.Names))
							continue
						}
						for _, dis := range disallowedTypeSubstrings {
							if strings.Contains(fieldTypeStr, dis) {
								leaks = append(leaks, "exported struct "+ts.Name.Name+" leaks APGR type in field "+fieldNames(field.Names)+": "+fieldTypeStr)
							}
						}
					}
				}
			} else if d.Tok == token.VAR || d.Tok == token.CONST {
				for _, spec := range d.Specs {
					vs, ok := spec.(*ast.ValueSpec)
					if !ok {
						continue
					}
					for _, name := range vs.Names {
						if ast.IsExported(name.Name) && vs.Type != nil {
							typeStr := types.ExprString(vs.Type)
							if typeStr == "" {
								leaks = append(leaks, "unhandled or empty type string for exported var/const "+name.Name)
								continue
							}
							for _, dis := range disallowedTypeSubstrings {
								if strings.Contains(typeStr, dis) {
									leaks = append(leaks, "exported var/const "+name.Name+" leaks APGR type: "+typeStr)
								}
							}
						}
					}
				}
			}
		case *ast.FuncDecl:
			if ast.IsExported(d.Name.Name) {
				if d.Type.Params != nil {
					for _, param := range d.Type.Params.List {
						paramTypeStr := types.ExprString(param.Type)
						if paramTypeStr == "" {
							leaks = append(leaks, "unhandled or empty type string for param "+fieldNames(param.Names))
							continue
						}
						for _, dis := range disallowedTypeSubstrings {
							if strings.Contains(paramTypeStr, dis) {
								leaks = append(leaks, "exported func/method "+d.Name.Name+" leaks APGR type in param "+fieldNames(param.Names)+": "+paramTypeStr)
							}
						}
					}
				}
				if d.Type.Results != nil {
					for _, res := range d.Type.Results.List {
						resTypeStr := types.ExprString(res.Type)
						if resTypeStr == "" {
							leaks = append(leaks, "unhandled or empty type string for result "+fieldNames(res.Names))
							continue
						}
						for _, dis := range disallowedTypeSubstrings {
							if strings.Contains(resTypeStr, dis) {
								leaks = append(leaks, "exported func/method "+d.Name.Name+" leaks APGR type in result "+fieldNames(res.Names)+": "+resTypeStr)
							}
						}
					}
				}
			}
		}
	}
	return leaks
}

// TestXOAdapterContainmentAndASTVerification performs bounded static inspection verifying that
// caller-facing control and evidence DTOs and method signatures in all runtime fixture files do not
// leak APGR implementation types, and that imports exclude disallowed packages (no os/exec,
// no internal/, no cmd/, no JACA packages).
func TestXOAdapterContainmentAndASTVerification(t *testing.T) {
	matches, err := filepath.Glob("*.go")
	if err != nil {
		t.Fatalf("glob *.go: %v", err)
	}
	var runtimeFiles []string
	for _, m := range matches {
		if !strings.HasSuffix(m, "_test.go") {
			runtimeFiles = append(runtimeFiles, m)
		}
	}
	if len(runtimeFiles) == 0 {
		t.Fatal("no runtime .go files found in xo_consumer fixture package")
	}

	fset := token.NewFileSet()
	for _, rf := range runtimeFiles {
		node, err := parser.ParseFile(fset, rf, nil, parser.ParseComments)
		if err != nil {
			t.Fatalf("parse %s: %v", rf, err)
		}

		// 1. Verify Imports
		for _, imp := range node.Imports {
			path := strings.Trim(imp.Path.Value, `"`)
			if imp.Name != nil && (imp.Name.Name == "." || imp.Name.Name == "_") {
				t.Fatalf("%s uses disallowed dot/blank import of %s", rf, path)
			}
			if strings.Contains(path, "agentic-praxis-grimoire") {
				if imp.Name != nil && imp.Name.Name != "" {
					t.Fatalf("%s aliases APGR import %s as %s", rf, path, imp.Name.Name)
				}
			}
			if strings.Contains(path, "internal") {
				t.Fatalf("%s imports internal package: %s", rf, path)
			}
			if strings.Contains(path, "/cmd/") || strings.HasSuffix(path, "/cmd") {
				t.Fatalf("%s imports cmd package: %s", rf, path)
			}
			if strings.Contains(path, "joint-agentic-command-aegis") || strings.Contains(path, "jaca") {
				t.Fatalf("%s imports JACA package: %s", rf, path)
			}
			if path == "os/exec" {
				t.Fatalf("%s imports os/exec directly: %s", rf, path)
			}
		}

		// 2. Verify Exported Types and Method Signatures
		leaks := checkASTForAPGRTypes(node)
		if len(leaks) > 0 {
			t.Fatalf("%s has APGR type leaks:\n%s", rf, strings.Join(leaks, "\n"))
		}
	}
}

// TestXOAdapterContainmentNegativeControl demonstrates that the AST containment checker fails
// closed when an intentional APGR domain type is introduced into an exported struct, function signature,
// or non-struct type definition/alias.
func TestXOAdapterContainmentNegativeControl(t *testing.T) {
	fset := token.NewFileSet()
	testSrc := `package testleaky
import "github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/footprint"

type LeakyStruct struct {
	Rec footprint.Record
}

func LeakyMethod() footprint.Record {
	return footprint.Record{}
}

type LeakyAlias = footprint.Record
`
	node, err := parser.ParseFile(fset, "negative_control.go", testSrc, 0)
	if err != nil {
		t.Fatalf("parse synthetic leaky source: %v", err)
	}
	leaks := checkASTForAPGRTypes(node)
	if len(leaks) == 0 {
		t.Fatal("expected negative control to detect intentional APGR type leaks, but found none")
	}
	if len(leaks) < 3 {
		t.Fatalf("expected at least 3 leaks detected in negative control, got %d: %v", len(leaks), leaks)
	}
}

// TestXOAdapterDependencyChainVerification inspects the runtime module dependency graph via
// go list -deps to verify that os/exec, APGR internal or cmd packages, and JACA modules are absent.
func TestXOAdapterDependencyChainVerification(t *testing.T) {
	cmd := exec.Command("go", "list", "-deps", ".")
	output, err := cmd.Output()
	if err != nil {
		t.Fatalf("go list -deps failed: %v", err)
	}

	lines := strings.Split(string(output), "\n")
	for _, line := range lines {
		dep := strings.TrimSpace(line)
		if dep == "" {
			continue
		}
		if dep == "os/exec" {
			t.Fatalf("disallowed dependency in chain: os/exec")
		}
		if strings.Contains(dep, "agentic-praxis-grimoire/internal") {
			t.Fatalf("disallowed dependency in chain: %s", dep)
		}
		if strings.Contains(dep, "agentic-praxis-grimoire/cmd") {
			t.Fatalf("disallowed dependency in chain: %s", dep)
		}
		if strings.Contains(dep, "joint-agentic-command-aegis") || strings.Contains(dep, "jaca") {
			t.Fatalf("disallowed dependency in chain: %s", dep)
		}
	}
}

// TestXOAdapterPublicWorkflowAndContainment verifies that public APIs work deterministically,
// produce stable fingerprints, preserve component availability, and populate caller DTOs.
func TestXOAdapterPublicWorkflowAndContainment(t *testing.T) {
	ctx := context.Background()
	adapter := NewXOAdapter()

	// 1. ResolveSkills
	skills1, err := adapter.ResolveSkills(ctx, []string{"go-language-profile"})
	if err != nil {
		t.Fatalf("ResolveSkills 1 failed: %v", err)
	}
	if len(skills1.SelectedSkillIDs) != 1 || skills1.SelectedSkillIDs[0] != "go-language-profile" {
		t.Fatalf("unexpected skill IDs: %#v", skills1.SelectedSkillIDs)
	}
	if skills1.BundleFingerprint == "" {
		t.Fatal("empty bundle fingerprint")
	}

	// Repeatability
	skills2, err := adapter.ResolveSkills(ctx, []string{"go-language-profile"})
	if err != nil {
		t.Fatalf("ResolveSkills 2 failed: %v", err)
	}
	if skills1.BundleFingerprint != skills2.BundleFingerprint {
		t.Fatalf("skills resolution not repeatable: %s != %s",
			skills1.BundleFingerprint, skills2.BundleFingerprint)
	}

	// 2. FootprintSkills Direct Public API Parity & Availability Fidelity
	req := buildSkillBundleRequest([]string{"go-language-profile"}, nil)
	directRes, err := skills.Resolve(ctx, req)
	if err != nil {
		t.Fatalf("direct skills.Resolve failed: %v", err)
	}
	directRec, err := skills.FootprintContext(ctx, req, directRes)
	if err != nil {
		t.Fatalf("direct skills.FootprintContext failed: %v", err)
	}

	fpEvidence, err := adapter.FootprintSkills(ctx, []string{"go-language-profile"})
	if err != nil {
		t.Fatalf("FootprintSkills failed: %v", err)
	}

	if fpEvidence.RecordFingerprint != directRec.Fingerprint() {
		t.Fatalf("fingerprint mismatch between adapter DTO and direct API: %s != %s",
			fpEvidence.RecordFingerprint, directRec.Fingerprint())
	}
	if fpEvidence.SchemaVersion != directRec.SchemaVersion {
		t.Fatalf("schema version mismatch: %s != %s", fpEvidence.SchemaVersion, directRec.SchemaVersion)
	}
	if fpEvidence.MetricCount != len(directRec.Components) {
		t.Fatalf("metric count mismatch: %d != %d", fpEvidence.MetricCount, len(directRec.Components))
	}
	if len(fpEvidence.Components) != len(directRec.Components) {
		t.Fatalf("component count mismatch: %d != %d", len(fpEvidence.Components), len(directRec.Components))
	}

	// Assert individual component availability, values, and reasons against direct public API
	var foundAvailableBody, foundUnavailableOverhead bool
	for i, comp := range fpEvidence.Components {
		directComp := directRec.Components[i]
		if comp.Kind != string(directComp.Kind) {
			t.Fatalf("component %d kind mismatch: %s != %s", i, comp.Kind, directComp.Kind)
		}
		if comp.Name != directComp.Name {
			t.Fatalf("component %d name mismatch: %s != %s", i, comp.Name, directComp.Name)
		}
		if comp.Unit != string(directComp.Metric.Unit) {
			t.Fatalf("component %d unit mismatch: %s != %s", i, comp.Unit, directComp.Metric.Unit)
		}
		if comp.Availability != string(directComp.Metric.Availability) {
			t.Fatalf("component %d availability mismatch: %s != %s", i, comp.Availability, directComp.Metric.Availability)
		}

		if comp.Availability == "available" {
			if comp.Value == nil {
				t.Fatalf("component %s marked available but has nil value", comp.Name)
			}
			if *comp.Value != *directComp.Metric.Value {
				t.Fatalf("component %s value mismatch: %d != %d", comp.Name, *comp.Value, *directComp.Metric.Value)
			}
			if *comp.Value <= 0 {
				t.Fatalf("component %s expected positive value, got %d", comp.Name, *comp.Value)
			}
			if comp.Reason != "" {
				t.Fatalf("component %s marked available should not have reason, got: %s", comp.Name, comp.Reason)
			}
			if comp.Name == "selected_bodies" {
				foundAvailableBody = true
			}
		} else if comp.Availability == "unavailable" {
			if comp.Value != nil {
				t.Fatalf("component %s marked unavailable must have nil value, got %d", comp.Name, *comp.Value)
			}
			if comp.Reason == "" {
				t.Fatalf("component %s marked unavailable must have non-empty reason", comp.Name)
			}
			if comp.Reason != directComp.Metric.Reason {
				t.Fatalf("component %s reason mismatch: %q != %q", comp.Name, comp.Reason, directComp.Metric.Reason)
			}
			if comp.Name == "provider_prompt_overhead" {
				foundUnavailableOverhead = true
			}
		}
	}
	if !foundAvailableBody {
		t.Fatal("expected to find available selected_bodies component")
	}
	if !foundUnavailableOverhead {
		t.Fatal("expected to find unavailable provider_prompt_overhead component")
	}

	// Observation metadata and exclusions verification against direct public API
	if fpEvidence.ObservationBasis != string(directRec.Observation.Basis) {
		t.Fatalf("observation basis mismatch: %s != %s", fpEvidence.ObservationBasis, directRec.Observation.Basis)
	}
	if fpEvidence.ObservationHarness != directRec.Observation.Harness {
		t.Fatalf("observation harness mismatch: %s != %s", fpEvidence.ObservationHarness, directRec.Observation.Harness)
	}
	if len(fpEvidence.ObservationExclusions) != len(directRec.Observation.Exclusions) {
		t.Fatalf("observation exclusions count mismatch: %d != %d",
			len(fpEvidence.ObservationExclusions), len(directRec.Observation.Exclusions))
	}
	var foundTotalCtxExcl, foundFitExcl bool
	for i, excl := range fpEvidence.ObservationExclusions {
		if excl != directRec.Observation.Exclusions[i] {
			t.Fatalf("observation exclusion %d mismatch: %s != %s", i, excl, directRec.Observation.Exclusions[i])
		}
		if excl == "provider_total_context" {
			foundTotalCtxExcl = true
		}
		if excl == "provider_context_fit" {
			foundFitExcl = true
		}
	}
	if !foundTotalCtxExcl || !foundFitExcl {
		t.Fatalf("expected provider_total_context and provider_context_fit in exclusions, got: %#v", fpEvidence.ObservationExclusions)
	}

	// Source references verification against direct public API
	if len(fpEvidence.SourceReferences) != len(directRec.SourceReferences) {
		t.Fatalf("source references count mismatch: %d != %d",
			len(fpEvidence.SourceReferences), len(directRec.SourceReferences))
	}
	if len(fpEvidence.SourceReferences) == 0 {
		t.Fatal("expected non-empty source references for resolved skill footprint")
	}
	var foundCorpusRef bool
	for i, ref := range fpEvidence.SourceReferences {
		directRef := directRec.SourceReferences[i]
		if ref.URI != directRef.URI || ref.Digest != directRef.Digest || ref.MediaType != directRef.MediaType || ref.Size != directRef.Size {
			t.Fatalf("source ref %d mismatch: %#v != %#v", i, ref, directRef)
		}
		if ref.URI == "" || ref.Digest == "" || ref.MediaType == "" || ref.Size <= 0 {
			t.Fatalf("source ref %d has invalid or empty fields: %#v", i, ref)
		}
		if strings.Contains(ref.URI, "corpus") {
			foundCorpusRef = true
		}
	}
	if !foundCorpusRef {
		t.Fatal("expected at least one corpus source reference in footprint evidence")
	}

	// JSON round-trip verification: ensure serialization preserves available vs unavailable (nil vs zero)
	// and preserves observation and source reference evidence.
	marshaledFP, err := json.Marshal(fpEvidence)
	if err != nil {
		t.Fatalf("json.Marshal failed: %v", err)
	}
	var unmarshaledFP CallerFootprintEvidence
	if err := json.Unmarshal(marshaledFP, &unmarshaledFP); err != nil {
		t.Fatalf("json.Unmarshal failed: %v", err)
	}
	if unmarshaledFP.RecordFingerprint != fpEvidence.RecordFingerprint {
		t.Fatalf("roundtrip fingerprint mismatch: %s != %s",
			unmarshaledFP.RecordFingerprint, fpEvidence.RecordFingerprint)
	}
	if unmarshaledFP.ObservationBasis != fpEvidence.ObservationBasis {
		t.Fatalf("roundtrip observation basis mismatch: %s != %s",
			unmarshaledFP.ObservationBasis, fpEvidence.ObservationBasis)
	}
	if unmarshaledFP.ObservationHarness != fpEvidence.ObservationHarness {
		t.Fatalf("roundtrip observation harness mismatch: %s != %s",
			unmarshaledFP.ObservationHarness, fpEvidence.ObservationHarness)
	}
	if len(unmarshaledFP.ObservationExclusions) != len(fpEvidence.ObservationExclusions) {
		t.Fatalf("roundtrip observation exclusions count mismatch: %d != %d",
			len(unmarshaledFP.ObservationExclusions), len(fpEvidence.ObservationExclusions))
	}
	for i, excl := range fpEvidence.ObservationExclusions {
		if unmarshaledFP.ObservationExclusions[i] != excl {
			t.Fatalf("roundtrip exclusion %d corrupted: %s != %s", i, unmarshaledFP.ObservationExclusions[i], excl)
		}
	}
	if len(unmarshaledFP.SourceReferences) != len(fpEvidence.SourceReferences) {
		t.Fatalf("roundtrip source references count mismatch: %d != %d",
			len(unmarshaledFP.SourceReferences), len(fpEvidence.SourceReferences))
	}
	for i, ref := range fpEvidence.SourceReferences {
		unmRef := unmarshaledFP.SourceReferences[i]
		if ref != unmRef {
			t.Fatalf("roundtrip source ref %d corrupted: %#v != %#v", i, unmRef, ref)
		}
	}
	for i, comp := range fpEvidence.Components {
		unmComp := unmarshaledFP.Components[i]
		if comp.Availability == "unavailable" && unmComp.Value != nil {
			t.Fatalf("roundtrip error: unavailable component %s gained non-nil value: %d",
				comp.Name, *unmComp.Value)
		}
		if comp.Availability == "available" && (unmComp.Value == nil || *unmComp.Value != *comp.Value) {
			t.Fatalf("roundtrip error: available component %s value lost or corrupted", comp.Name)
		}
	}

	// Explicit available zero vs unavailable nil distinction check
	zeroVal := int64(0)
	availableZeroComp := CallerComponentEvidence{
		Kind:         "test_kind",
		Name:         "zero_metric",
		Unit:         "bytes",
		Availability: "available",
		Value:        &zeroVal,
	}
	zeroMarshaled, err := json.Marshal(availableZeroComp)
	if err != nil {
		t.Fatalf("marshal availableZeroComp: %v", err)
	}
	var zeroUnmarshaled CallerComponentEvidence
	if err := json.Unmarshal(zeroMarshaled, &zeroUnmarshaled); err != nil {
		t.Fatalf("unmarshal availableZeroComp: %v", err)
	}
	if zeroUnmarshaled.Value == nil || *zeroUnmarshaled.Value != 0 {
		t.Fatalf("available zero coerced to nil or wrong value: %#v", zeroUnmarshaled.Value)
	}

	// 3. MeasureFootprint
	fp1, err := adapter.MeasureFootprint(ctx, "control", 128)
	if err != nil {
		t.Fatalf("MeasureFootprint 1 failed: %v", err)
	}
	if fp1.RecordFingerprint == "" {
		t.Fatal("empty record fingerprint")
	}
	if fp1.MetricCount != 3 {
		t.Fatalf("expected 3 metrics, got %d", fp1.MetricCount)
	}

	// Repeatability
	fp2, err := adapter.MeasureFootprint(ctx, "control", 128)
	if err != nil {
		t.Fatalf("MeasureFootprint 2 failed: %v", err)
	}
	if fp1.RecordFingerprint != fp2.RecordFingerprint {
		t.Fatalf("footprint measurement not repeatable: %s != %s",
			fp1.RecordFingerprint, fp2.RecordFingerprint)
	}

	// 4. CompareFootprints
	comp, err := adapter.CompareFootprints(ctx, 100, 150, false)
	if err != nil {
		t.Fatalf("CompareFootprints failed: %v", err)
	}
	if comp.Delta != 50 {
		t.Fatalf("expected delta 50, got %d", comp.Delta)
	}
	if comp.Unit != "bytes" {
		t.Fatalf("expected unit 'bytes', got %s", comp.Unit)
	}
	if comp.ComponentKind != "selected_body" || comp.ComponentName != "selected_body" {
		t.Fatalf("unexpected comparison component: %s/%s", comp.ComponentKind, comp.ComponentName)
	}
	if comp.ComparisonSchema != "apg.context-comparison/v1" {
		t.Fatalf("unexpected comparison schema: %s", comp.ComparisonSchema)
	}

	// 5. ProjectFootprint Source-Bound Direct Comparison
	proj, err := adapter.ProjectFootprint(ctx, 200, []string{"body"})
	if err != nil {
		t.Fatalf("ProjectFootprint failed: %v", err)
	}
	directRecord, err := adapter.internalMeasure(ctx, "basis", footprint.UnitBytes, 200)
	if err != nil {
		t.Fatalf("internalMeasure failed: %v", err)
	}
	directProj, err := footprint.Project(ctx, footprint.ProjectRequest{
		Source:        directRecord,
		Fidelity:      footprint.FidelitySummarizedLossy,
		OmittedFields: []string{"body"},
	})
	if err != nil {
		t.Fatalf("direct footprint.Project failed: %v", err)
	}
	directRecCanonical, err := directProj.Record.CanonicalJSON()
	if err != nil {
		t.Fatalf("direct Record.CanonicalJSON failed: %v", err)
	}

	if proj.CanonicalSourceDigest != directProj.CanonicalSourceDigest {
		t.Fatalf("source digest mismatch: %s != %s", proj.CanonicalSourceDigest, directProj.CanonicalSourceDigest)
	}
	if proj.CanonicalSourceSchema != directProj.CanonicalSourceSchema {
		t.Fatalf("source schema mismatch: %s != %s", proj.CanonicalSourceSchema, directProj.CanonicalSourceSchema)
	}
	if proj.CanonicalSourceSize != directProj.CanonicalSourceSize {
		t.Fatalf("source size mismatch: %d != %d", proj.CanonicalSourceSize, directProj.CanonicalSourceSize)
	}
	if proj.ProjectionFingerprint != directProj.Fingerprint() {
		t.Fatalf("projection fingerprint mismatch: %s != %s", proj.ProjectionFingerprint, directProj.Fingerprint())
	}
	if proj.ProjectedRecordBytes != int64(len(directRecCanonical)) {
		t.Fatalf("projected record bytes mismatch: %d != %d", proj.ProjectedRecordBytes, len(directRecCanonical))
	}
	if proj.ProjectedRecordBytes <= 0 {
		t.Fatalf("expected positive projected record bytes, got %d", proj.ProjectedRecordBytes)
	}
	if proj.Fidelity != string(footprint.FidelitySummarizedLossy) {
		t.Fatalf("unexpected fidelity: %s", proj.Fidelity)
	}
	if len(proj.OmittedFields) != len(directProj.OmittedFields) {
		t.Fatalf("omitted fields count mismatch: %d != %d", len(proj.OmittedFields), len(directProj.OmittedFields))
	}
	for i, f := range proj.OmittedFields {
		if f != directProj.OmittedFields[i] {
			t.Fatalf("omitted field %d mismatch: %s != %s", i, f, directProj.OmittedFields[i])
		}
	}
	if proj.Sensitivity != string(directProj.Sensitivity) {
		t.Fatalf("sensitivity mismatch: %s != %s", proj.Sensitivity, directProj.Sensitivity)
	}
	if proj.Retention != string(directProj.Retention) {
		t.Fatalf("retention mismatch: %s != %s", proj.Retention, directProj.Retention)
	}

	// 6. Schema Validation and Fixed Fixture Source Reference Payload
	if !adapter.ValidateSchemaCompatibility() {
		t.Fatal("expected schema compatibility to be true")
	}
	expectedSourceDigest := "sha256:" + schema.SHA256([]byte(fixtureSourcePayload))
	if len(expectedSourceDigest) != 71 {
		t.Fatalf("unexpected digest length: %s", expectedSourceDigest)
	}
	if int64(len(fixtureSourcePayload)) != 28 {
		t.Fatalf("unexpected fixture source payload length: %d", len(fixtureSourcePayload))
	}
}

// TestXOAdapterCancellationAndSentinelPreservation proves context cancellation and deadline
// propagation through errors.Is on context-accepting APIs, plus sentinel error preservation.
func TestXOAdapterCancellationAndSentinelPreservation(t *testing.T) {
	adapter := NewXOAdapter()

	// 1. Context Cancellation on FootprintSkills
	ctx1, cancel1 := context.WithCancel(context.Background())
	cancel1()

	_, err := adapter.FootprintSkills(ctx1, []string{"go-language-profile"})
	if err == nil {
		t.Fatal("expected cancellation error, got nil")
	}
	if !errors.Is(err, context.Canceled) {
		t.Fatalf("expected errors.Is(err, context.Canceled), got: %v", err)
	}

	// 2. Already-expired deadline context on FootprintSkills
	ctxDead, cancelDead := context.WithDeadline(context.Background(), time.Now().Add(-1*time.Hour))
	defer cancelDead()

	_, err = adapter.FootprintSkills(ctxDead, []string{"go-language-profile"})
	if err == nil {
		t.Fatal("expected deadline exceeded error, got nil")
	}
	if !errors.Is(err, context.DeadlineExceeded) {
		t.Fatalf("expected errors.Is(err, context.DeadlineExceeded), got: %v", err)
	}

	// 3. Cancellation with invalid skill identifier
	// Proves skills.Resolve receives caller ctx and evaluates cancellation before input validation,
	// rather than executing silently with context.Background() and returning an invalid skill error.
	ctxInv, cancelInv := context.WithCancel(context.Background())
	cancelInv()

	_, err = adapter.FootprintSkills(ctxInv, []string{"non-existent-skill-id-xyz"})
	if err == nil {
		t.Fatal("expected cancellation error with invalid skill ID, got nil")
	}
	if !errors.Is(err, context.Canceled) {
		t.Fatalf("expected errors.Is(err, context.Canceled), got: %v", err)
	}

	// 4. Context Cancellation on MeasureFootprint (wraps footprint.ErrContextCancelled)
	ctx2, cancel2 := context.WithCancel(context.Background())
	cancel2()

	_, err = adapter.MeasureFootprint(ctx2, "cancelled", 128)
	if err == nil {
		t.Fatal("expected cancellation error, got nil")
	}
	if !errors.Is(err, footprint.ErrContextCancelled) {
		t.Fatalf("expected ErrContextCancelled, got: %v", err)
	}

	// 5. Sentinel: ErrUnitMismatch
	_, err = adapter.CompareFootprints(context.Background(), 10, 20, true)
	if err == nil {
		t.Fatal("expected unit mismatch error, got nil")
	}
	if !errors.Is(err, footprint.ErrUnitMismatch) {
		t.Fatalf("expected ErrUnitMismatch, got: %v", err)
	}

	// 6. Sentinel: ErrConsequenceBearingOmissionRefused
	_, err = adapter.ProjectFootprint(context.Background(), 100, []string{"observation"})
	if err == nil {
		t.Fatal("expected consequence-bearing omission error, got nil")
	}
	if !errors.Is(err, footprint.ErrConsequenceBearingOmissionRefused) {
		t.Fatalf("expected ErrConsequenceBearingOmissionRefused, got: %v", err)
	}

	// 7. Sentinel: ErrBudgetExceeded (Budget refusal)
	zero := int64(0)
	_, err = adapter.ResolveSkillsWithMaxBytes(context.Background(), []string{"go-language-profile"}, &zero)
	if err == nil {
		t.Fatal("expected budget exceeded error, got nil")
	}
	if !errors.Is(err, skills.ErrBudgetExceeded) {
		t.Fatalf("expected ErrBudgetExceeded, got: %v", err)
	}
}

// TestXOAdapterPureInMemoryRuntimeSmoke performs in-memory smoke execution verifying that
// skill resolution and footprint measurement execute cleanly in memory without external process
// invocation or network calls.
func TestXOAdapterPureInMemoryRuntimeSmoke(t *testing.T) {
	adapter := NewXOAdapter()
	ctx := context.Background()

	res, err := adapter.ResolveSkills(ctx, []string{"go-language-profile"})
	if err != nil {
		t.Fatalf("smoke skill resolution failed: %v", err)
	}
	if len(res.SelectedSkillIDs) == 0 {
		t.Fatal("smoke skill resolution returned empty list")
	}

	fp, err := adapter.MeasureFootprint(ctx, "smoke", 64)
	if err != nil {
		t.Fatalf("smoke footprint measurement failed: %v", err)
	}
	if fp.MetricCount == 0 {
		t.Fatal("smoke footprint measurement returned zero metrics")
	}
}

// TestXOAdapterContractItem7NonAuthority verifies through structural reflection across all caller
// DTO types (CallerSkillEvidence, CallerComponentEvidence, CallerSourceReference,
// CallerFootprintEvidence, CallerComparisonDelta, CallerProjectionEvidence) that exported fields
// are strictly constrained to an allowlist of passive observation and provenance fields, containing
// no workflow progression tokens, provider credentials, route selection directives, or persistence execution handles.
func TestXOAdapterContractItem7NonAuthority(t *testing.T) {
	// 1. Structural reflection check across all caller DTOs
	allowedFieldsByType := map[string]map[string]bool{
		"CallerSkillEvidence": {
			"SelectedSkillIDs":  true,
			"BundleFingerprint": true,
			"SchemaVersion":     true,
		},
		"CallerComponentEvidence": {
			"Kind":         true,
			"Name":         true,
			"Unit":         true,
			"Availability": true,
			"Value":        true,
			"Reason":       true,
		},
		"CallerSourceReference": {
			"URI":       true,
			"Digest":    true,
			"MediaType": true,
			"Size":      true,
		},
		"CallerFootprintEvidence": {
			"RecordFingerprint":     true,
			"SchemaVersion":         true,
			"MetricCount":           true,
			"Components":            true,
			"SourceReferences":      true,
			"ObservationBasis":      true,
			"ObservationHarness":    true,
			"ObservationExclusions": true,
		},
		"CallerComparisonDelta": {
			"ComparisonSchema":     true,
			"BaselineFingerprint":  true,
			"CandidateFingerprint": true,
			"ComponentKind":        true,
			"ComponentName":        true,
			"Delta":                true,
			"Unit":                 true,
		},
		"CallerProjectionEvidence": {
			"ProjectionFingerprint": true,
			"ProjectionSchema":      true,
			"CanonicalSourceDigest": true,
			"CanonicalSourceSchema": true,
			"CanonicalSourceSize":   true,
			"Fidelity":              true,
			"OmittedFields":         true,
			"Sensitivity":           true,
			"Retention":             true,
			"ProjectedRecordBytes":  true,
		},
	}

	dtoTypes := []reflect.Type{
		reflect.TypeOf(CallerSkillEvidence{}),
		reflect.TypeOf(CallerComponentEvidence{}),
		reflect.TypeOf(CallerSourceReference{}),
		reflect.TypeOf(CallerFootprintEvidence{}),
		reflect.TypeOf(CallerComparisonDelta{}),
		reflect.TypeOf(CallerProjectionEvidence{}),
	}

	disallowedKeywords := []string{
		"token", "auth", "credential", "action", "dispatch",
		"state", "advance", "transition", "workflow", "route",
		"role", "permission", "execute", "persist",
	}

	for _, typ := range dtoTypes {
		typeName := typ.Name()
		allowed, ok := allowedFieldsByType[typeName]
		if !ok {
			t.Fatalf("unregistered DTO type in non-authority test: %s", typeName)
		}

		for i := 0; i < typ.NumField(); i++ {
			field := typ.Field(i)
			if !field.IsExported() {
				continue
			}
			if !allowed[field.Name] {
				t.Fatalf("DTO %s has unpermitted field %s outside passive observation allowlist", typeName, field.Name)
			}
			lowerName := strings.ToLower(field.Name)
			for _, kw := range disallowedKeywords {
				if strings.Contains(lowerName, kw) {
					t.Fatalf("DTO %s field %s contains authority-implying keyword %q", typeName, field.Name, kw)
				}
			}
		}
	}

	// 2. Behavioral verification of returned DTO values
	adapter := NewXOAdapter()
	ctx := context.Background()

	// Verify Skill DTO
	skillEv, err := adapter.ResolveSkills(ctx, []string{"go-language-profile"})
	if err != nil {
		t.Fatalf("ResolveSkills failed: %v", err)
	}
	if skillEv.SchemaVersion == "" || skillEv.BundleFingerprint == "" {
		t.Fatal("empty passive fields in skill evidence")
	}

	// Verify Footprint DTO
	fpEv, err := adapter.MeasureFootprint(ctx, "non-authority-test", 128)
	if err != nil {
		t.Fatalf("MeasureFootprint failed: %v", err)
	}
	if fpEv.RecordFingerprint == "" || fpEv.SchemaVersion != "apg.context-footprint/v1" || fpEv.MetricCount != 3 {
		t.Fatalf("unexpected values in footprint evidence: %#v", fpEv)
	}

	// Verify Comparison DTO
	compEv, err := adapter.CompareFootprints(ctx, 100, 150, false)
	if err != nil {
		t.Fatalf("CompareFootprints failed: %v", err)
	}
	if compEv.ComparisonSchema == "" || compEv.BaselineFingerprint == "" || compEv.CandidateFingerprint == "" {
		t.Fatalf("unexpected values in comparison evidence: %#v", compEv)
	}

	// Verify Projection DTO
	projEv, err := adapter.ProjectFootprint(ctx, 128, []string{"body"})
	if err != nil {
		t.Fatalf("ProjectFootprint failed: %v", err)
	}
	if projEv.ProjectionFingerprint == "" || projEv.CanonicalSourceDigest == "" || projEv.ProjectedRecordBytes <= 0 {
		t.Fatalf("unexpected values in projection evidence: %#v", projEv)
	}
}
