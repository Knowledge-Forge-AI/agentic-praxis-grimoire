package skills

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"io"
	"os"
	"path/filepath"
	"reflect"
	"runtime"
	"sort"
	"testing"

	apgfootprint "github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/footprint"
)

const apg125CompositionFixtureVersion = "apg125.profile-composition/v1"

type apg125CompositionFixture struct {
	SchemaVersion    int                         `json:"schema_version"`
	FixtureID        string                      `json:"fixture_id"`
	FixtureVersion   string                      `json:"fixture_version"`
	Authority        apg125CompositionAuthority  `json:"authority"`
	Controls         []apg125CompositionControl  `json:"controls"`
	Scenarios        []apg125CompositionScenario `json:"scenarios"`
	NegativeControls []apg125CompositionNegative `json:"negative_controls"`
}

type apg125CompositionAuthority struct {
	Phase                  string `json:"phase"`
	Selection              string `json:"selection"`
	CompositionRuleVersion string `json:"composition_rule_version"`
	Description            string `json:"description"`
	MeasurementBoundary    string `json:"measurement_boundary"`
}

type apg125CompositionControl struct {
	ID                string   `json:"id"`
	Purpose           string   `json:"purpose"`
	ExplicitSkillIDs  []string `json:"explicit_skill_ids"`
	ExpectedSkillIDs  []string `json:"expected_skill_ids"`
	ExcludedNeighbors []string `json:"excluded_neighbors"`
	InsufficientFor   []string `json:"insufficient_for"`
	Insufficiency     string   `json:"insufficiency"`
}

type apg125CompositionScenario struct {
	ID                 string                     `json:"id"`
	Name               string                     `json:"name"`
	Task               string                     `json:"task"`
	ExplicitSkillIDs   []string                   `json:"explicit_skill_ids"`
	ExpectedSkillIDs   []string                   `json:"expected_skill_ids"`
	ExcludedNeighbors  []string                   `json:"excluded_neighbors"`
	OwnershipRationale []apg125OwnershipRationale `json:"ownership_rationale"`
	NarrowerControlIDs []string                   `json:"narrower_control_ids"`
}

type apg125OwnershipRationale struct {
	SkillID   string `json:"skill_id"`
	Rationale string `json:"rationale"`
}

type apg125CompositionNegative struct {
	ID                 string   `json:"id"`
	FactKind           string   `json:"fact_kind"`
	FactValue          string   `json:"fact_value"`
	ExpectedError      *string  `json:"expected_error"`
	ExpectedSkillIDs   []string `json:"expected_selected_skill_ids"`
	ExpectedExclusions []string `json:"expected_exclusions"`
	Rationale          string   `json:"rationale"`
}

type apg125BundleEvidence struct {
	Request         BundleRequest
	Result          BundleResult
	Materialization Materialization
	Record          apgfootprint.Record
	DiskBytes       int64
	SupportBytes    int64
}

var apg125CompositionProfileIDs = []string{
	"browser-runtime-profile",
	"css-language-profile",
	"javascript-language-profile",
	"jsx-language-profile",
	"nodejs-runtime-profile",
	"npm-package-manager-profile",
	"playwright-test-profile",
	"react-component-profile",
	"svg-language-profile",
	"typescript-language-profile",
	"vite-build-profile",
	"web-accessibility-profile",
}

func TestAPG125ExplicitProfileComposition(t *testing.T) {
	fixture := loadAPG125CompositionFixture(t)
	validateAPG125CompositionFixture(t, fixture)

	controls := make(map[string]apg125BundleEvidence, len(fixture.Controls))
	for _, control := range fixture.Controls {
		control := control
		t.Run("control/"+control.ID, func(t *testing.T) {
			request := apg125CompositionRequest(control.ExplicitSkillIDs, MaterializationFlatDirectory)
			evidence := measureAPG125Bundle(t, request, control.ExpectedSkillIDs)
			controls[control.ID] = evidence
			logAPG125BundleReceipt(t, "control", control.ID, nil, evidence)
		})
	}

	for _, scenario := range fixture.Scenarios {
		scenario := scenario
		t.Run(scenario.ID+"/"+scenario.Name, func(t *testing.T) {
			request := apg125CompositionRequest(scenario.ExplicitSkillIDs, MaterializationFlatDirectory)
			evidence := measureAPG125Bundle(t, request, scenario.ExpectedSkillIDs)
			assertAPG125Determinism(t, request, evidence)
			assertAPG125BudgetBoundaries(t, scenario.ExpectedSkillIDs, request)

			for _, controlID := range scenario.NarrowerControlIDs {
				control, ok := controls[controlID]
				if !ok {
					t.Fatalf("control %q was not measured", controlID)
				}
				assertAPG125Comparisons(t, control, evidence)
			}
			logAPG125BundleReceipt(t, "scenario", scenario.ID, scenario.NarrowerControlIDs, evidence)
		})
	}

	for _, negative := range fixture.NegativeControls {
		negative := negative
		t.Run("negative/"+negative.ID, func(t *testing.T) {
			assertAPG125StructuredFactNegative(t, negative)
		})
	}
}

func loadAPG125CompositionFixture(t *testing.T) apg125CompositionFixture {
	t.Helper()
	_, sourceFile, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("runtime.Caller failed while locating APG125 fixture")
	}
	fixturePath := filepath.Join(filepath.Dir(sourceFile), "..", "src", "test", "fixtures", "apg125-profile-composition-scenarios.json")
	content, err := os.ReadFile(fixturePath)
	if err != nil {
		t.Fatalf("read APG125 composition fixture: %v", err)
	}
	decoder := json.NewDecoder(bytes.NewReader(content))
	decoder.DisallowUnknownFields()
	var fixture apg125CompositionFixture
	if err := decoder.Decode(&fixture); err != nil {
		t.Fatalf("decode APG125 composition fixture: %v", err)
	}
	var extra any
	if err := decoder.Decode(&extra); !errors.Is(err, io.EOF) {
		t.Fatalf("APG125 fixture has trailing JSON: %v", err)
	}
	return fixture
}

func validateAPG125CompositionFixture(t *testing.T, fixture apg125CompositionFixture) {
	t.Helper()
	if fixture.SchemaVersion != 1 || fixture.FixtureID != "APG125-PROFILE-COMPOSITION" || fixture.FixtureVersion != apg125CompositionFixtureVersion {
		t.Fatalf("fixture identity = %#v", fixture)
	}
	if fixture.Authority.Phase != "APG125" || fixture.Authority.Selection != "explicit-only" || fixture.Authority.CompositionRuleVersion != CompositionVersionV1 {
		t.Fatalf("fixture authority = %#v", fixture.Authority)
	}
	if fixture.Authority.Description == "" || fixture.Authority.MeasurementBoundary == "" {
		t.Fatal("fixture authority must state selection and measurement boundaries")
	}
	if len(fixture.Scenarios) != 7 {
		t.Fatalf("scenario count = %d, want 7", len(fixture.Scenarios))
	}
	if len(fixture.Controls) != 5 {
		t.Fatalf("control count = %d, want 5", len(fixture.Controls))
	}
	if len(fixture.NegativeControls) != 3 {
		t.Fatalf("negative control count = %d, want 3", len(fixture.NegativeControls))
	}

	known := make(map[string]bool, len(apg125CompositionProfileIDs))
	for _, id := range apg125CompositionProfileIDs {
		known[id] = true
	}
	controls := make(map[string]apg125CompositionControl, len(fixture.Controls))
	for _, control := range fixture.Controls {
		if control.ID == "" || control.Purpose == "" || control.Insufficiency == "" || len(control.InsufficientFor) == 0 {
			t.Fatalf("incomplete control = %#v", control)
		}
		if _, exists := controls[control.ID]; exists {
			t.Fatalf("duplicate control %q", control.ID)
		}
		controls[control.ID] = control
		assertAPG125IDSet(t, control.ID+" explicit", control.ExplicitSkillIDs, known, false)
		assertAPG125IDSet(t, control.ID+" expected", control.ExpectedSkillIDs, known, true)
		assertAPG125IDSet(t, control.ID+" excluded", control.ExcludedNeighbors, known, true)
		if !reflect.DeepEqual(sortedAPG125IDs(control.ExplicitSkillIDs), sortedAPG125IDs(control.ExpectedSkillIDs)) {
			t.Fatalf("control %s explicit/expected mismatch: explicit=%v expected=%v", control.ID, control.ExplicitSkillIDs, control.ExpectedSkillIDs)
		}
		assertAPG125Partition(t, control.ID, control.ExpectedSkillIDs, control.ExcludedNeighbors, known)
	}

	scenarios := make(map[string]apg125CompositionScenario, len(fixture.Scenarios))
	for _, scenario := range fixture.Scenarios {
		if scenario.ID == "" || scenario.Name == "" || scenario.Task == "" || len(scenario.NarrowerControlIDs) == 0 {
			t.Fatalf("incomplete scenario = %#v", scenario)
		}
		if _, exists := scenarios[scenario.ID]; exists {
			t.Fatalf("duplicate scenario %q", scenario.ID)
		}
		scenarios[scenario.ID] = scenario
		assertAPG125IDSet(t, scenario.ID+" explicit", scenario.ExplicitSkillIDs, known, false)
		assertAPG125IDSet(t, scenario.ID+" expected", scenario.ExpectedSkillIDs, known, true)
		assertAPG125IDSet(t, scenario.ID+" excluded", scenario.ExcludedNeighbors, known, true)
		if !reflect.DeepEqual(sortedAPG125IDs(scenario.ExplicitSkillIDs), sortedAPG125IDs(scenario.ExpectedSkillIDs)) {
			t.Fatalf("scenario %s explicit/expected mismatch: explicit=%v expected=%v", scenario.ID, scenario.ExplicitSkillIDs, scenario.ExpectedSkillIDs)
		}
		assertAPG125Partition(t, scenario.ID, scenario.ExpectedSkillIDs, scenario.ExcludedNeighbors, known)

		rationales := make(map[string]string, len(scenario.OwnershipRationale))
		for _, rationale := range scenario.OwnershipRationale {
			if !known[rationale.SkillID] || rationale.Rationale == "" {
				t.Fatalf("scenario %s has invalid ownership rationale %#v", scenario.ID, rationale)
			}
			if _, exists := rationales[rationale.SkillID]; exists {
				t.Fatalf("scenario %s repeats rationale for %q", scenario.ID, rationale.SkillID)
			}
			rationales[rationale.SkillID] = rationale.Rationale
		}
		if len(rationales) != len(scenario.ExpectedSkillIDs) {
			t.Fatalf("scenario %s rationale count = %d, want %d", scenario.ID, len(rationales), len(scenario.ExpectedSkillIDs))
		}
		for _, id := range scenario.ExpectedSkillIDs {
			if rationales[id] == "" {
				t.Fatalf("scenario %s has no rationale for %q", scenario.ID, id)
			}
		}
		for _, controlID := range scenario.NarrowerControlIDs {
			control, ok := controls[controlID]
			if !ok {
				t.Fatalf("scenario %s references unknown control %q", scenario.ID, controlID)
			}
			if !apg125StrictSubset(control.ExpectedSkillIDs, scenario.ExpectedSkillIDs) {
				t.Fatalf("scenario %s control %s is not a strict narrower subset", scenario.ID, controlID)
			}
			if !containsAPG125String(control.InsufficientFor, scenario.ID) {
				t.Fatalf("control %s does not declare insufficiency for %s", controlID, scenario.ID)
			}
		}
	}
	for _, control := range fixture.Controls {
		for _, scenarioID := range control.InsufficientFor {
			if _, ok := scenarios[scenarioID]; !ok {
				t.Fatalf("control %s names unknown insufficient scenario %q", control.ID, scenarioID)
			}
		}
	}

	for _, negative := range fixture.NegativeControls {
		if negative.ID == "" || negative.FactKind == "" || negative.FactValue == "" || negative.Rationale == "" {
			t.Fatalf("incomplete negative control = %#v", negative)
		}
		if negative.ExpectedError == nil && negative.ExpectedExclusions == nil {
			t.Fatalf("negative control %s has neither an error nor exclusions", negative.ID)
		}
		if negative.ExpectedError != nil && *negative.ExpectedError != "ErrInvalidRequest" {
			t.Fatalf("negative control %s expected unsupported error %q", negative.ID, *negative.ExpectedError)
		}
	}
}

func assertAPG125IDSet(t *testing.T, label string, values []string, known map[string]bool, requireSorted bool) {
	t.Helper()
	if len(values) == 0 {
		t.Fatalf("%s is empty", label)
	}
	seen := make(map[string]bool, len(values))
	for _, id := range values {
		if !known[id] {
			t.Fatalf("%s contains unknown profile %q", label, id)
		}
		if seen[id] {
			t.Fatalf("%s repeats profile %q", label, id)
		}
		seen[id] = true
	}
	if requireSorted && !sort.StringsAreSorted(values) {
		t.Fatalf("%s must be canonical sorted IDs: %v", label, values)
	}
}

func assertAPG125Partition(t *testing.T, label string, selected, excluded []string, known map[string]bool) {
	t.Helper()
	all := append(append([]string(nil), selected...), excluded...)
	if len(all) != len(known) || !reflect.DeepEqual(sortedAPG125IDs(all), apg125CompositionProfileIDs) {
		t.Fatalf("%s does not partition the complete neighbor set: selected=%v excluded=%v", label, selected, excluded)
	}
	for _, id := range selected {
		if containsAPG125String(excluded, id) {
			t.Fatalf("%s selects and excludes %q", label, id)
		}
	}
}

func sortedAPG125IDs(values []string) []string {
	result := append([]string(nil), values...)
	sort.Strings(result)
	return result
}

func apg125StrictSubset(candidate, broader []string) bool {
	candidateSet := make(map[string]bool, len(candidate))
	for _, id := range candidate {
		candidateSet[id] = true
	}
	broaderSet := make(map[string]bool, len(broader))
	for _, id := range broader {
		broaderSet[id] = true
	}
	if len(candidateSet) >= len(broaderSet) {
		return false
	}
	for id := range candidateSet {
		if !broaderSet[id] {
			return false
		}
	}
	return true
}

func containsAPG125String(values []string, want string) bool {
	for _, value := range values {
		if value == want {
			return true
		}
	}
	return false
}

func apg125IDsEqual(left, right []string) bool {
	if len(left) != len(right) {
		return false
	}
	for index := range left {
		if left[index] != right[index] {
			return false
		}
	}
	return true
}

func apg125CompositionRequest(ids []string, form MaterializationForm) BundleRequest {
	return BundleRequest{
		SchemaVersion:    BundleRequestSchemaV1,
		ExplicitSkillIDs: append([]string(nil), ids...),
		Consumer:         Consumer{Kind: ConsumerGo, MaterializationForm: form},
		Budget:           Budget{},
	}
}

func measureAPG125Bundle(t *testing.T, request BundleRequest, expectedIDs []string) apg125BundleEvidence {
	t.Helper()
	result, err := Resolve(context.Background(), request)
	if err != nil {
		t.Fatalf("Resolve: %v", err)
	}
	if !reflect.DeepEqual(result.SelectedSkillIDs, expectedIDs) {
		t.Fatalf("selected IDs = %v, want %v", result.SelectedSkillIDs, expectedIDs)
	}
	parent := apg125CompositionMaterializationParent(t)
	materialization, err := Materialize(context.Background(), MaterializeRequest{DestinationParent: parent, Result: result})
	if err != nil {
		t.Fatalf("Materialize: %v", err)
	}
	record, err := FootprintWithMaterialization(request, result, materialization)
	if err != nil {
		t.Fatalf("FootprintWithMaterialization: %v", err)
	}
	assertAPG125SourceBindings(t, request, result, record)

	supportBytes := apg125ActualFileBytes(t, filepath.Join(materialization.Root, ManifestFilename))
	var diskBytes int64
	for _, selected := range result.SelectedSkills {
		path := filepath.Join(materialization.Root, selected.ID, "SKILL.md")
		info, statErr := os.Lstat(path)
		if statErr != nil {
			t.Fatalf("stat materialized %s: %v", selected.ID, statErr)
		}
		if info.Mode()&os.ModeSymlink != 0 || !info.Mode().IsRegular() || info.Size() != selected.BodyBytes {
			t.Fatalf("materialized %s size = %d, want %d", selected.ID, info.Size(), selected.BodyBytes)
		}
		body, readErr := os.ReadFile(path)
		if readErr != nil {
			t.Fatalf("read materialized %s: %v", selected.ID, readErr)
		}
		if int64(len(body)) != selected.BodyBytes {
			t.Fatalf("materialized %s bytes = %d, want %d", selected.ID, len(body), selected.BodyBytes)
		}
		diskBytes += info.Size()
	}
	diskBytes += supportBytes
	fullMetric := apg125MetricValue(t, record, apgfootprint.ComponentMaterializedBundle, FootprintMaterializedBundle)
	if fullMetric != diskBytes {
		t.Fatalf("materialized metric = %d, actual disk bytes = %d", fullMetric, diskBytes)
	}
	if apg125MetricValue(t, record, apgfootprint.ComponentSupportMaterial, FootprintSupportMaterial) != supportBytes {
		t.Fatalf("support metric does not equal manifest bytes")
	}
	if containsAPG125String(record.Observation.Exclusions, "filesystem_materialization_not_executed") {
		t.Fatal("executed materialization marked as unexecuted")
	}

	return apg125BundleEvidence{
		Request:         request,
		Result:          result,
		Materialization: materialization,
		Record:          record,
		DiskBytes:       diskBytes,
		SupportBytes:    supportBytes,
	}
}

func apg125ActualFileBytes(t *testing.T, path string) int64 {
	t.Helper()
	info, err := os.Lstat(path)
	if err != nil {
		t.Fatalf("stat %s: %v", filepath.Base(path), err)
	}
	if info.Mode()&os.ModeSymlink != 0 || !info.Mode().IsRegular() {
		t.Fatalf("%s is not a regular file", filepath.Base(path))
	}
	content, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read %s: %v", filepath.Base(path), err)
	}
	if int64(len(content)) != info.Size() {
		t.Fatalf("%s read size=%d stat size=%d", filepath.Base(path), len(content), info.Size())
	}
	return info.Size()
}

func assertAPG125Determinism(t *testing.T, request BundleRequest, evidence apg125BundleEvidence) {
	t.Helper()
	second, err := Resolve(context.Background(), request)
	if err != nil {
		t.Fatalf("repeat Resolve: %v", err)
	}
	firstJSON, err := evidence.Result.CanonicalJSON()
	if err != nil {
		t.Fatalf("canonical first result: %v", err)
	}
	secondJSON, err := second.CanonicalJSON()
	if err != nil {
		t.Fatalf("canonical second result: %v", err)
	}
	if evidence.Result.RequestFingerprint != second.RequestFingerprint || evidence.Result.BundleFingerprint != second.BundleFingerprint || !bytes.Equal(firstJSON, secondJSON) {
		t.Fatal("repeated Resolve changed request or bundle identity")
	}
	permutedRequest := request
	permutedRequest.ExplicitSkillIDs = append([]string(nil), request.ExplicitSkillIDs...)
	for left, right := 0, len(permutedRequest.ExplicitSkillIDs)-1; left < right; left, right = left+1, right-1 {
		permutedRequest.ExplicitSkillIDs[left], permutedRequest.ExplicitSkillIDs[right] = permutedRequest.ExplicitSkillIDs[right], permutedRequest.ExplicitSkillIDs[left]
	}
	permuted, err := Resolve(context.Background(), permutedRequest)
	if err != nil {
		t.Fatalf("permuted Resolve: %v", err)
	}
	if evidence.Result.RequestFingerprint != permuted.RequestFingerprint || evidence.Result.BundleFingerprint != permuted.BundleFingerprint {
		t.Fatal("explicit ID order changed request or bundle identity")
	}
	reused, err := Materialize(context.Background(), MaterializeRequest{DestinationParent: filepath.Dir(evidence.Materialization.Root), Result: evidence.Result})
	if err != nil {
		t.Fatalf("repeat Materialize: %v", err)
	}
	if !reused.Reused || reused.Root != evidence.Materialization.Root || reused.ManifestFingerprint != evidence.Materialization.ManifestFingerprint {
		t.Fatalf("repeat Materialize identity = %#v, want reused root and manifest", reused)
	}
	recordAgain, err := FootprintWithMaterialization(request, evidence.Result, reused)
	if err != nil {
		t.Fatalf("repeat FootprintWithMaterialization: %v", err)
	}
	firstRecordJSON, err := evidence.Record.CanonicalJSON()
	if err != nil {
		t.Fatalf("canonical first footprint: %v", err)
	}
	secondRecordJSON, err := recordAgain.CanonicalJSON()
	if err != nil {
		t.Fatalf("canonical second footprint: %v", err)
	}
	if evidence.Record.Fingerprint() != recordAgain.Fingerprint() || !bytes.Equal(firstRecordJSON, secondRecordJSON) {
		t.Fatal("repeated footprint changed identity")
	}
}

func assertAPG125BudgetBoundaries(t *testing.T, expectedIDs []string, baselineRequest BundleRequest) {
	t.Helper()
	request := apg125CompositionRequest(baselineRequest.ExplicitSkillIDs, MaterializationInMemory)
	baseline, err := Resolve(context.Background(), request)
	if err != nil {
		t.Fatalf("budget baseline Resolve: %v", err)
	}
	request.Budget.MaxDescriptionBytes = apg125Int64Pointer(baseline.SelectedDescriptionBytes)
	if exact, exactErr := Resolve(context.Background(), request); exactErr != nil || !reflect.DeepEqual(exact.SelectedSkillIDs, expectedIDs) {
		t.Fatalf("description exact fit = selected %v, err %v", exact.SelectedSkillIDs, exactErr)
	}
	underDescription := apg125CompositionRequest(baselineRequest.ExplicitSkillIDs, MaterializationInMemory)
	underDescription.Budget.MaxDescriptionBytes = apg125Int64Pointer(baseline.SelectedDescriptionBytes - 1)
	apg125AssertBudgetRefusal(t, underDescription, expectedIDs, "description_bytes")

	request = apg125CompositionRequest(baselineRequest.ExplicitSkillIDs, MaterializationInMemory)
	request.Budget.MaxBodyBytes = apg125Int64Pointer(baseline.SelectedBodyBytes)
	if exact, exactErr := Resolve(context.Background(), request); exactErr != nil || !reflect.DeepEqual(exact.SelectedSkillIDs, expectedIDs) {
		t.Fatalf("body exact fit = selected %v, err %v", exact.SelectedSkillIDs, exactErr)
	}
	underBody := apg125CompositionRequest(baselineRequest.ExplicitSkillIDs, MaterializationInMemory)
	underBody.Budget.MaxBodyBytes = apg125Int64Pointer(baseline.SelectedBodyBytes - 1)
	apg125AssertBudgetRefusal(t, underBody, expectedIDs, "body_bytes")

	eagerRequest := apg125CompositionRequest(baselineRequest.ExplicitSkillIDs, MaterializationInMemory)
	eagerRequest.EagerBodies = true
	eager, err := Resolve(context.Background(), eagerRequest)
	if err != nil {
		t.Fatalf("eager budget baseline Resolve: %v", err)
	}
	eagerRequest.Budget.MaxInitialContextBytes = apg125Int64Pointer(eager.InitialContextBytes)
	if exact, exactErr := Resolve(context.Background(), eagerRequest); exactErr != nil || !reflect.DeepEqual(exact.SelectedSkillIDs, expectedIDs) {
		t.Fatalf("eager initial-context exact fit = selected %v, err %v", exact.SelectedSkillIDs, exactErr)
	}
	underInitial := apg125CompositionRequest(baselineRequest.ExplicitSkillIDs, MaterializationInMemory)
	underInitial.EagerBodies = true
	underInitial.Budget.MaxInitialContextBytes = apg125Int64Pointer(eager.InitialContextBytes - 1)
	apg125AssertBudgetRefusal(t, underInitial, expectedIDs, "initial_context_bytes")
}

func apg125AssertBudgetRefusal(t *testing.T, request BundleRequest, expectedIDs []string, dimension string) {
	t.Helper()
	result, err := Resolve(context.Background(), request)
	var budgetErr *BudgetError
	if !errors.As(err, &budgetErr) || !errors.Is(err, ErrBudgetExceeded) {
		t.Fatalf("%s one-byte-under error = %v", dimension, err)
	}
	if !reflect.DeepEqual(result.SelectedSkillIDs, expectedIDs) {
		t.Fatalf("%s refusal changed selected IDs = %v, want %v", dimension, result.SelectedSkillIDs, expectedIDs)
	}
	var passed bool
	switch dimension {
	case "description_bytes":
		passed = result.Budget.DescriptionBytes.Passed
	case "body_bytes":
		passed = result.Budget.BodyBytes.Passed
	case "initial_context_bytes":
		passed = result.Budget.InitialContextBytes.Passed
	default:
		t.Fatalf("unknown budget dimension %q", dimension)
	}
	if passed {
		t.Fatalf("%s one-byte-under was marked passed", dimension)
	}
}

func assertAPG125SourceBindings(t *testing.T, request BundleRequest, result BundleResult, record apgfootprint.Record) {
	t.Helper()
	requestJSON, err := request.CanonicalJSON()
	if err != nil {
		t.Fatalf("canonical request for source binding: %v", err)
	}
	resultJSON, err := result.CanonicalJSON()
	if err != nil {
		t.Fatalf("canonical result for source binding: %v", err)
	}
	want := map[string]string{
		"apg:skill-bundle-request/" + BundleRequestSchemaV1:                                "sha256:" + sha256Hex(requestJSON),
		"apg:skill-bundle-result/" + BundleResultSchemaV1 + "/" + result.BundleFingerprint: "sha256:" + sha256Hex(resultJSON),
	}
	for uri, digest := range want {
		found := false
		for _, reference := range record.SourceReferences {
			if reference.URI == uri {
				if reference.Digest != digest || reference.Size <= 0 {
					t.Fatalf("source %s binding = %#v, want digest %s", uri, reference, digest)
				}
				found = true
				break
			}
		}
		if !found {
			t.Fatalf("source binding %s is absent", uri)
		}
	}
	corpusURI := "apg:skill-corpus/" + result.EmbeddedCorpusFingerprint
	if !containsAPG125SourceURI(record.SourceReferences, corpusURI) {
		t.Fatalf("corpus source binding %s is absent", corpusURI)
	}
}

func containsAPG125SourceURI(references []apgfootprint.SourceReference, want string) bool {
	for _, reference := range references {
		if reference.URI == want && reference.Digest != "" && reference.Size > 0 {
			return true
		}
	}
	return false
}

func assertAPG125Comparisons(t *testing.T, control, treatment apg125BundleEvidence) {
	t.Helper()
	comparisons := []struct {
		kind  apgfootprint.ComponentKind
		name  string
		delta int64
	}{
		{apgfootprint.ComponentSelectedDescription, FootprintSelectedDescriptions, treatment.Result.SelectedDescriptionBytes - control.Result.SelectedDescriptionBytes},
		{apgfootprint.ComponentSelectedBody, FootprintSelectedBodies, treatment.Result.SelectedBodyBytes - control.Result.SelectedBodyBytes},
		{apgfootprint.ComponentSupportMaterial, FootprintSupportMaterial, treatment.SupportBytes - control.SupportBytes},
		{apgfootprint.ComponentMaterializedBundle, FootprintMaterializedBundle, treatment.DiskBytes - control.DiskBytes},
	}
	for _, want := range comparisons {
		comparison, err := apgfootprint.Compare(context.Background(), apgfootprint.CompareRequest{
			Control:       control.Record,
			Treatment:     treatment.Record,
			ComponentKind: want.kind,
			ComponentName: want.name,
		})
		if err != nil {
			t.Fatalf("Compare %s/%s: %v", want.kind, want.name, err)
		}
		if comparison.Delta != want.delta || comparison.Unit != apgfootprint.UnitBytes {
			t.Fatalf("Compare %s/%s delta=%d unit=%s, want delta=%d unit=%s", want.kind, want.name, comparison.Delta, comparison.Unit, want.delta, apgfootprint.UnitBytes)
		}
		if comparison.Control.RecordDigest != control.Record.Fingerprint() || comparison.Treatment.RecordDigest != treatment.Record.Fingerprint() {
			t.Fatalf("Compare %s/%s lost record identity", want.kind, want.name)
		}
	}
}

func assertAPG125StructuredFactNegative(t *testing.T, negative apg125CompositionNegative) {
	t.Helper()
	request := apg125CompositionRequest(nil, MaterializationInMemory)
	switch negative.FactKind {
	case "language":
		request.Languages = []string{negative.FactValue}
	case "capability":
		request.Capabilities = []string{negative.FactValue}
	case "runtime":
		request.Runtimes = []string{negative.FactValue}
	default:
		t.Fatalf("unsupported negative fact kind %q", negative.FactKind)
	}
	result, err := Resolve(context.Background(), request)
	if negative.ExpectedError != nil {
		if *negative.ExpectedError != "ErrInvalidRequest" || !errors.Is(err, ErrInvalidRequest) {
			t.Fatalf("%s error = %v, want ErrInvalidRequest", negative.ID, err)
		}
		return
	}
	if err != nil {
		t.Fatalf("%s unexpected error = %v", negative.ID, err)
	}
	if !apg125IDsEqual(result.SelectedSkillIDs, negative.ExpectedSkillIDs) {
		t.Fatalf("%s selected = %v, want %v", negative.ID, result.SelectedSkillIDs, negative.ExpectedSkillIDs)
	}
	var exclusions []string
	for _, exclusion := range result.Exclusions {
		exclusions = append(exclusions, exclusion.SourceFact)
	}
	if !reflect.DeepEqual(exclusions, negative.ExpectedExclusions) {
		t.Fatalf("%s exclusions = %v, want %v", negative.ID, exclusions, negative.ExpectedExclusions)
	}
	if containsAPG125String(result.SelectedSkillIDs, "browser-runtime-profile") {
		t.Fatal("accepted runtime browser fact auto-loaded browser-runtime-profile")
	}
}

func apg125MetricValue(t *testing.T, record apgfootprint.Record, kind apgfootprint.ComponentKind, name string) int64 {
	t.Helper()
	var found *apgfootprint.Component
	for index := range record.Components {
		component := &record.Components[index]
		if component.Kind == kind && component.Name == name {
			if found != nil {
				t.Fatalf("duplicate footprint component %s/%s", kind, name)
			}
			found = component
		}
	}
	if found == nil || found.Metric.Availability != apgfootprint.Available || found.Metric.Value == nil {
		t.Fatalf("footprint component %s/%s unavailable: %#v", kind, name, found)
	}
	return *found.Metric.Value
}

func logAPG125BundleReceipt(t *testing.T, kind, id string, controls []string, evidence apg125BundleEvidence) {
	t.Helper()
	t.Logf("APG125 sanitized receipt kind=%s id=%s controls=%v corpus_id=%s request_id=%s result_id=%s record_id=%s manifest_id=%s selected_ids=%v description_bytes=%d body_bytes=%d support_bytes=%d materialized_bytes=%d", kind, id, controls, evidence.Result.EmbeddedCorpusFingerprint, evidence.Result.RequestFingerprint, evidence.Result.BundleFingerprint, evidence.Record.Fingerprint(), evidence.Materialization.ManifestFingerprint, evidence.Result.SelectedSkillIDs, evidence.Result.SelectedDescriptionBytes, evidence.Result.SelectedBodyBytes, evidence.SupportBytes, evidence.DiskBytes)
}

func apg125CompositionMaterializationParent(t *testing.T) string {
	t.Helper()
	parent := t.TempDir()
	var err error
	parent, err = filepath.EvalSymlinks(parent)
	if err != nil {
		t.Fatalf("resolve APG125 materialization parent: %v", err)
	}
	if err := os.Chmod(parent, 0o700); err != nil {
		t.Fatalf("set APG125 materialization parent mode: %v", err)
	}
	return parent
}

func apg125Int64Pointer(value int64) *int64 { return &value }
