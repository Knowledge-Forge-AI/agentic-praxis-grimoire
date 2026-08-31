package cli

import (
	"bytes"
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/footprint"
)

func footprintTestObservation(variant string) footprint.Observation {
	return footprint.Observation{
		Basis:        footprint.ObservationBasisDirectMeasurement,
		Availability: footprint.Available,
		Exclusions:   []string{},
		Harness:      "cli-test",
		Method:       "fixture",
		Provider:     "local",
		Quality:      footprint.QualityVerified,
		Repetitions:  1,
		StudyDesign:  footprint.StudyDesignSingleRun,
		Tokenizer:    "none",
		Variant:      variant,
		Workload:     "footprint-cli",
	}
}

func footprintTestRecord(t *testing.T, variant string, bodyUnit footprint.Unit, bodyMetric footprint.Metric) (footprint.Record, string) {
	t.Helper()
	record := footprint.Record{
		SchemaVersion: footprint.FootprintSchemaV1,
		Observation:   footprintTestObservation(variant),
		Components: []footprint.Component{
			{
				ControlIdentity: string(footprint.ControlSelectedBody),
				Kind:            footprint.ComponentSelectedBody,
				Metric:          bodyMetric,
				Name:            "body",
			},
			{
				ControlIdentity: string(footprint.ControlSelectedDiscovery),
				Kind:            footprint.ComponentSelectedDescription,
				Metric: footprint.Metric{
					Availability: footprint.Available,
					Unit:         footprint.UnitCharacters,
					Value:        footprintTestInt64(2),
				},
				Name: "description",
			},
		},
		SourceReferences: []footprint.SourceReference{},
		Sensitivity:      footprint.SensitivityPublic,
		Retention:        footprint.RetentionEphemeral,
	}
	if bodyUnit != "" {
		record.Components[0].Metric.Unit = bodyUnit
	}
	content, err := record.CanonicalJSON()
	if err != nil {
		t.Fatal(err)
	}
	return record, writeFootprintTestFile(t, content)
}

func footprintTestInt64(value int64) *int64 { return &value }

func writeFootprintTestFile(t *testing.T, content []byte) string {
	t.Helper()
	path := filepath.Join(t.TempDir(), "footprint.json")
	if err := os.WriteFile(path, content, 0o600); err != nil {
		t.Fatal(err)
	}
	return path
}

func footprintTestMeasureDocument() (measureDocument, footprint.MeasureRequest) {
	document := measureDocument{
		SchemaVersion: footprint.FootprintSchemaV1,
		Observation:   footprintTestObservation("measure"),
		Components: []measureComponentDocument{
			{
				Kind: footprint.ComponentSelectedBody,
				Name: "body",
				Unit: footprint.UnitBytes,
				Text: footprintTestString("hello"),
			},
		},
		SourceReferences: []footprint.SourceReference{},
		Sensitivity:      footprint.SensitivityPublic,
		Retention:        footprint.RetentionEphemeral,
	}
	request := footprint.MeasureRequest{
		SchemaVersion:    document.SchemaVersion,
		Observation:      document.Observation,
		Components:       []footprint.ComponentInput{{Kind: footprint.ComponentSelectedBody, Name: "body", Unit: footprint.UnitBytes, Text: "hello"}},
		SourceReferences: document.SourceReferences,
		Sensitivity:      document.Sensitivity,
		Retention:        document.Retention,
	}
	return document, request
}

func footprintTestString(value string) *string { return &value }

func TestFootprintHelpAndUsage(t *testing.T) {
	for _, arguments := range [][]string{{"footprint", "--help"}, {"footprint", "measure", "--help"}, {"footprint", "compare", "--help"}, {"footprint", "project", "--help"}} {
		exit, stdout, stderr := runTest(t, context.Background(), arguments...)
		if exit != 0 || stderr != "" || !strings.Contains(stdout, "Usage: apgr footprint") {
			t.Fatalf("help %v = exit %d stdout %q stderr %q", arguments, exit, stdout, stderr)
		}
	}
	for _, arguments := range [][]string{{"footprint"}, {"footprint", "unknown"}, {"footprint", "measure", "--unknown"}} {
		exit, _, _ := runTest(t, context.Background(), arguments...)
		if exit != 2 {
			t.Fatalf("usage %v = exit %d, want 2", arguments, exit)
		}
	}
}

func TestFootprintMeasureCanonicalOutputAndDirectParity(t *testing.T) {
	document, request := footprintTestMeasureDocument()
	input, err := json.Marshal(document)
	if err != nil {
		t.Fatal(err)
	}
	path := writeFootprintTestFile(t, input)
	expectedRecord, err := footprint.Measure(context.Background(), request)
	if err != nil {
		t.Fatal(err)
	}
	expected, err := expectedRecord.CanonicalJSON()
	if err != nil {
		t.Fatal(err)
	}

	var stdout, stderr bytes.Buffer
	exit := RunWithInput(context.Background(), []string{"footprint", "measure", "--input", path}, strings.NewReader(""), &stdout, &stderr)
	if exit != 0 || stderr.Len() != 0 || !bytes.Equal(stdout.Bytes(), expected) {
		t.Fatalf("measure file = exit %d output %q stderr %q, want %q", exit, stdout.String(), stderr.String(), expected)
	}
	if _, err := footprint.DecodeRecord(stdout.Bytes()); err != nil {
		t.Fatalf("measure output is not canonical: %v", err)
	}

	stdout.Reset()
	stderr.Reset()
	exit = RunWithInput(context.Background(), []string{"footprint", "measure", "--stdin"}, bytes.NewReader(input), &stdout, &stderr)
	if exit != 0 || stderr.Len() != 0 || !bytes.Equal(stdout.Bytes(), expected) {
		t.Fatalf("measure stdin = exit %d output %q stderr %q", exit, stdout.String(), stderr.String())
	}
}

func TestFootprintCompareCanonicalOutputAndUnitAvailabilityErrors(t *testing.T) {
	controlMetric := footprint.Metric{Availability: footprint.Available, Unit: footprint.UnitBytes, Value: footprintTestInt64(5)}
	treatmentMetric := footprint.Metric{Availability: footprint.Available, Unit: footprint.UnitBytes, Value: footprintTestInt64(8)}
	control, controlPath := footprintTestRecord(t, "control", footprint.UnitBytes, controlMetric)
	treatment, treatmentPath := footprintTestRecord(t, "treatment", footprint.UnitBytes, treatmentMetric)
	expectedComparison, err := footprint.Compare(context.Background(), footprint.CompareRequest{
		Control:       control,
		Treatment:     treatment,
		ComponentKind: footprint.ComponentSelectedBody,
		ComponentName: "body",
	})
	if err != nil {
		t.Fatal(err)
	}
	expected, err := expectedComparison.CanonicalJSON()
	if err != nil {
		t.Fatal(err)
	}

	var stdout, stderr bytes.Buffer
	exit := RunWithInput(context.Background(), []string{"footprint", "compare", "--control", controlPath, "--treatment", treatmentPath, "--component-kind", "selected_body", "--component-name", "body"}, strings.NewReader(""), &stdout, &stderr)
	if exit != 0 || stderr.Len() != 0 || !bytes.Equal(stdout.Bytes(), expected) {
		t.Fatalf("compare = exit %d output %q stderr %q, want %q", exit, stdout.String(), stderr.String(), expected)
	}
	if _, err := footprint.DecodeComparison(stdout.Bytes()); err != nil {
		t.Fatalf("compare output is not canonical: %v", err)
	}

	_, mismatchedPath := footprintTestRecord(t, "treatment", footprint.UnitCharacters, footprint.Metric{Availability: footprint.Available, Unit: footprint.UnitCharacters, Value: footprintTestInt64(8)})
	exit, _, stderrValue := runTest(t, context.Background(), "footprint", "compare", "--control", controlPath, "--treatment", mismatchedPath, "--kind", "selected_body", "--name", "body")
	if exit != 1 || !strings.Contains(stderrValue, "unit") {
		t.Fatalf("unit mismatch = exit %d stderr %q", exit, stderrValue)
	}
	_, unavailablePath := footprintTestRecord(t, "treatment", footprint.UnitBytes, footprint.Metric{Availability: footprint.Unavailable, Unit: footprint.UnitBytes, Reason: "not observed"})
	exit, _, stderrValue = runTest(t, context.Background(), "footprint", "compare", "--control", controlPath, "--treatment", unavailablePath, "--kind", "selected_body", "--name", "body")
	if exit != 1 || !strings.Contains(stderrValue, "unavailable") {
		t.Fatalf("unavailable = exit %d stderr %q", exit, stderrValue)
	}
}

func TestFootprintProjectCanonicalOutputAndRefusal(t *testing.T) {
	source, sourcePath := footprintTestRecord(t, "source", footprint.UnitBytes, footprint.Metric{Availability: footprint.Available, Unit: footprint.UnitBytes, Value: footprintTestInt64(5)})
	expectedProjection, err := footprint.Project(context.Background(), footprint.ProjectRequest{Source: source, Fidelity: footprint.FidelitySummarizedLossy, OmittedFields: []string{"body"}})
	if err != nil {
		t.Fatal(err)
	}
	expected, err := expectedProjection.CanonicalJSON()
	if err != nil {
		t.Fatal(err)
	}
	var stdout, stderr bytes.Buffer
	exit := RunWithInput(context.Background(), []string{"footprint", "project", "--source", sourcePath, "--fidelity", "summarized_lossy", "--omit", "body"}, strings.NewReader(""), &stdout, &stderr)
	if exit != 0 || stderr.Len() != 0 || !bytes.Equal(stdout.Bytes(), expected) {
		t.Fatalf("project = exit %d output %q stderr %q, want %q", exit, stdout.String(), stderr.String(), expected)
	}
	if _, err := footprint.DecodeProjection(stdout.Bytes()); err != nil {
		t.Fatalf("project output is not canonical: %v", err)
	}

	exit, _, stderrValue := runTest(t, context.Background(), "footprint", "project", "--source", sourcePath, "--fidelity", "summarized_lossy", "--omit", "authority")
	if exit != 1 || !strings.Contains(stderrValue, "refused") {
		t.Fatalf("consequence omission = exit %d stderr %q", exit, stderrValue)
	}
}

func TestFootprintStrictInputAndCancellation(t *testing.T) {
	document, _ := footprintTestMeasureDocument()
	valid, err := json.Marshal(document)
	if err != nil {
		t.Fatal(err)
	}
	unknown := append([]byte(`{"unexpected":true,`), valid[1:]...)
	duplicateKey := append([]byte(`{"schema_version":"`+footprint.FootprintSchemaV1+`",`), valid[1:]...)
	explicitNull := append([]byte(`{"schema_version":null,`), valid[len(`{"schema_version":`):]...)

	for _, input := range [][]byte{[]byte(`{"schema_version":`), unknown, duplicateKey, explicitNull} {
		exit, _, stderr := runTestWithFootprintInput(t, context.Background(), input, "footprint", "measure", "--stdin")
		if exit != 1 || stderr == "" {
			t.Fatalf("invalid input = exit %d stderr %q", exit, stderr)
		}
	}

	// Test --input and --source exclusivity in project action
	_, sourcePath := footprintTestRecord(t, "source", footprint.UnitBytes, footprint.Metric{Availability: footprint.Available, Unit: footprint.UnitBytes, Value: footprintTestInt64(5)})
	exit, _, stderr := runTest(t, context.Background(), "footprint", "project", "--input", sourcePath, "--source", sourcePath)
	if exit != 2 || !strings.Contains(stderr, "one footprint input source is required") {
		t.Fatalf("multiple input sources = exit %d stderr %q", exit, stderr)
	}

	cancelled, cancel := context.WithCancel(context.Background())
	cancel()
	exit, _, stderr = runTestWithFootprintInput(t, cancelled, valid, "footprint", "measure", "--stdin")
	if exit != 1 || !strings.Contains(stderr, "interrupted") {
		t.Fatalf("cancelled input = exit %d stderr %q", exit, stderr)
	}
}

func runTestWithFootprintInput(t *testing.T, ctx context.Context, input []byte, arguments ...string) (int, string, string) {
	t.Helper()
	var stdout, stderr bytes.Buffer
	exit := RunWithInput(ctx, arguments, bytes.NewReader(input), &stdout, &stderr)
	return exit, stdout.String(), stderr.String()
}
