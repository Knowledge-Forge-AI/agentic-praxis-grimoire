package skills

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"reflect"
	"strings"
	"testing"
)

func baseRequest(ids ...string) BundleRequest {
	return BundleRequest{
		SchemaVersion:    BundleRequestSchemaV1,
		ExplicitSkillIDs: ids,
		Consumer: Consumer{
			Kind:                ConsumerGo,
			MaterializationForm: MaterializationInMemory,
		},
		Budget: Budget{},
	}
}

func TestResolveExplicitStructuredAndNoImplicitChain(t *testing.T) {
	tests := []struct {
		name    string
		request BundleRequest
		want    []string
	}{
		{"explicit", baseRequest("planning-repository-work"), []string{"planning-repository-work"}},
		{"multiple explicit", baseRequest("pytest-test-profile", "go-language-profile"), []string{"go-language-profile", "pytest-test-profile"}},
		{"go only", withLanguage(baseRequest(), "go"), []string{"go-language-profile"}},
		{"gomock only", withTestFramework(baseRequest(), "gomock-v0.6.0"), []string{"gomock-test-profile"}},
		{"react only", withCapability(baseRequest(), "react-components"), []string{"react-component-profile"}},
		{"astro only", withCapability(baseRequest(), "astro-framework"), []string{"astro-profile"}},
		{"node only", withRuntime(baseRequest(), "nodejs"), []string{"nodejs-runtime-profile"}},
		{"pytest only", withTestFramework(baseRequest(), "pytest"), []string{"pytest-test-profile"}},
		{"explicit union", withLanguage(withTestFramework(baseRequest(), "pytest"), "go"), []string{"go-language-profile", "pytest-test-profile"}},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			result, err := Resolve(context.Background(), test.request)
			if err != nil {
				t.Fatal(err)
			}
			if !reflect.DeepEqual(result.SelectedSkillIDs, test.want) {
				t.Fatalf("selected = %v, want %v", result.SelectedSkillIDs, test.want)
			}
		})
	}
}

func TestResolveChatGPTCompatibilityAndComposition(t *testing.T) {
	request := baseRequest("chatgpt-manager-workflow", "composing-approved-roadmap-assignments")
	request.Consumer = Consumer{Kind: ConsumerChatGPT, MaterializationForm: MaterializationFlatDirectory}
	result, err := Resolve(context.Background(), request)
	if err != nil {
		t.Fatal(err)
	}
	if len(result.SelectedSkills) != 2 {
		t.Fatalf("selected = %#v", result.SelectedSkills)
	}

	incompatible := baseRequest("chatgpt-manager-workflow")
	result, err = Resolve(context.Background(), incompatible)
	if !errors.Is(err, ErrConsumerMismatch) || len(result.Conflicts) != 1 {
		t.Fatalf("consumer mismatch = %#v, %v", result, err)
	}

	composed := withCapability(withCapability(withLanguage(baseRequest(), "typescript"), "react-components"), "jsx")
	result, err = Resolve(context.Background(), composed)
	if err != nil {
		t.Fatal(err)
	}
	wantEdge := CompositionEdge{From: "jsx-language-profile", To: "react-component-profile"}
	if !containsEdge(result.CompositionEdges, wantEdge) {
		t.Fatalf("composition edges = %#v", result.CompositionEdges)
	}
	if len(result.SelectedSkillIDs) != 3 {
		t.Fatalf("composition selected a sibling: %v", result.SelectedSkillIDs)
	}
}

func TestResolveDeterministicAcrossSetOrder(t *testing.T) {
	request := flatRequest("pytest-test-profile", "go-language-profile")
	request.Languages = []string{"python", "go"}
	request.Runtimes = []string{"nodejs", "browser"}
	request.TestFrameworks = []string{"pytest", "jest"}
	request.RepositoryCharacteristics = []string{"dockerfile", "monorepo"}
	request.Capabilities = []string{"react-components", "accessibility"}
	request.Consumer.ProviderConstraints = []string{"filesystem_skill_discovery", "isolated_apg_root"}
	baseline, err := Resolve(context.Background(), request)
	if err != nil {
		t.Fatal(err)
	}
	for mask := 0; mask < 128; mask++ {
		permuted := request
		sets := []*[]string{&permuted.ExplicitSkillIDs, &permuted.Languages, &permuted.Runtimes, &permuted.TestFrameworks, &permuted.RepositoryCharacteristics, &permuted.Capabilities, &permuted.Consumer.ProviderConstraints}
		for bit, set := range sets {
			if mask&(1<<bit) != 0 {
				*set = reverse(*set)
			} else {
				*set = append([]string(nil), (*set)...)
			}
		}
		result, resolveErr := Resolve(context.Background(), permuted)
		if resolveErr != nil {
			t.Fatalf("permutation %d: %v", mask, resolveErr)
		}
		if baseline.RequestFingerprint != result.RequestFingerprint || baseline.BundleFingerprint != result.BundleFingerprint || string(mustJSON(t, baseline)) != string(mustJSON(t, result)) {
			t.Fatalf("permutation %d changed canonical identity", mask)
		}
	}
}

func TestStrictRequestRefusals(t *testing.T) {
	valid := `{"budget":{"max_body_bytes":null,"max_description_bytes":null,"max_initial_context_bytes":null,"prompt_overhead_bytes":0},"capabilities":[],"consumer":{"architecture":"","kind":"go_library","materialization_form":"in_memory","operating_system":"","provider_constraints":[]},"eager_bodies":false,"explicit_skill_ids":[],"languages":[],"repository_characteristics":[],"runtimes":[],"schema_version":"apg.skill-bundle-request/v1","test_frameworks":[],"work_class":""}`
	tests := []struct {
		name string
		body string
	}{
		{"unknown field", strings.Replace(valid, `"work_class":""`, `"unknown":1,"work_class":""`, 1)},
		{"duplicate key", strings.Replace(valid, `"work_class":""`, `"work_class":"","work_class":""`, 1)},
		{"missing field", strings.Replace(valid, `,"work_class":""`, ``, 1)},
		{"overflow", strings.Replace(valid, `"prompt_overhead_bytes":0`, `"prompt_overhead_bytes":9223372036854775808`, 1)},
		{"negative", strings.Replace(valid, `"prompt_overhead_bytes":0`, `"prompt_overhead_bytes":-1`, 1)},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			request, err := DecodeBundleRequest([]byte(test.body))
			if err == nil {
				_, err = Resolve(context.Background(), request)
			}
			if err == nil {
				t.Fatal("request unexpectedly accepted")
			}
		})
	}

	request, err := DecodeBundleRequest([]byte(valid))
	if err != nil {
		t.Fatal(err)
	}
	request.Languages = []string{"go", "go"}
	if _, err = Resolve(context.Background(), request); !errors.Is(err, ErrInvalidRequest) {
		t.Fatalf("duplicate set = %v", err)
	}
	request = baseRequest("does-not-exist")
	if _, err = Resolve(context.Background(), request); !errors.Is(err, ErrInvalidRequest) {
		t.Fatalf("unknown explicit = %v", err)
	}
	request = withLanguage(baseRequest(), "brainfuck")
	if _, err = Resolve(context.Background(), request); !errors.Is(err, ErrInvalidRequest) {
		t.Fatalf("unknown language = %v", err)
	}
	request = baseRequest()
	request.Consumer = Consumer{Kind: ConsumerCodex, MaterializationForm: MaterializationInMemory}
	if _, err = Resolve(context.Background(), request); !errors.Is(err, ErrInvalidRequest) {
		t.Fatalf("contradictory consumer facts = %v", err)
	}
}

func TestBudgetBoundariesAndEagerBodies(t *testing.T) {
	request := baseRequest("planning-repository-work")
	baseline, err := Resolve(context.Background(), request)
	if err != nil {
		t.Fatal(err)
	}
	request.Budget.MaxDescriptionBytes = pointer(baseline.SelectedDescriptionBytes)
	request.Budget.MaxBodyBytes = pointer(baseline.SelectedBodyBytes)
	request.Budget.MaxInitialContextBytes = pointer(baseline.InitialContextBytes)
	if _, err = Resolve(context.Background(), request); err != nil {
		t.Fatalf("exact fit: %v", err)
	}
	request.Budget.MaxDescriptionBytes = pointer(baseline.SelectedDescriptionBytes + 1)
	if _, err = Resolve(context.Background(), request); err != nil {
		t.Fatalf("one byte spare: %v", err)
	}
	request.Budget.MaxDescriptionBytes = pointer(baseline.SelectedDescriptionBytes - 1)
	result, err := Resolve(context.Background(), request)
	var budgetErr *BudgetError
	if !errors.As(err, &budgetErr) || result.Budget.DescriptionBytes.Passed {
		t.Fatalf("one below = %#v, %v", result.Budget, err)
	}
	if result.SelectedSkillIDs[0] != "planning-repository-work" {
		t.Fatal("budget failure truncated or substituted selection")
	}

	zero := int64(0)
	request = baseRequest("planning-repository-work")
	request.Budget.MaxDescriptionBytes = &zero
	if _, err = Resolve(context.Background(), request); !errors.Is(err, ErrBudgetExceeded) {
		t.Fatalf("explicit zero = %v", err)
	}

	request = baseRequest("planning-repository-work")
	request.EagerBodies = true
	request.Budget.PromptOverheadBytes = 7
	result, err = Resolve(context.Background(), request)
	if err != nil {
		t.Fatal(err)
	}
	want := int64(7) + result.SelectedDescriptionBytes + result.SelectedBodyBytes
	if result.InitialContextBytes != want {
		t.Fatalf("initial context = %d, want %d", result.InitialContextBytes, want)
	}
	request.Budget.MaxBodyBytes = pointer(result.SelectedBodyBytes - 1)
	if _, err = Resolve(context.Background(), request); !errors.Is(err, ErrBudgetExceeded) {
		t.Fatalf("body overage = %v", err)
	}
	request.Budget.MaxBodyBytes = nil
	request.Budget.MaxInitialContextBytes = pointer(result.InitialContextBytes - 1)
	if _, err = Resolve(context.Background(), request); !errors.Is(err, ErrBudgetExceeded) {
		t.Fatalf("initial-context overage = %v", err)
	}
}

func withLanguage(request BundleRequest, value string) BundleRequest {
	request.Languages = []string{value}
	return request
}
func withRuntime(request BundleRequest, value string) BundleRequest {
	request.Runtimes = []string{value}
	return request
}
func withTestFramework(request BundleRequest, value string) BundleRequest {
	request.TestFrameworks = []string{value}
	return request
}
func withCapability(request BundleRequest, value string) BundleRequest {
	request.Capabilities = append(request.Capabilities, value)
	return request
}
func pointer(value int64) *int64 { return &value }
func reverse(values []string) []string {
	result := append([]string(nil), values...)
	for left, right := 0, len(result)-1; left < right; left, right = left+1, right-1 {
		result[left], result[right] = result[right], result[left]
	}
	return result
}
func containsEdge(values []CompositionEdge, value CompositionEdge) bool {
	for _, candidate := range values {
		if candidate == value {
			return true
		}
	}
	return false
}
func mustJSON(t *testing.T, result BundleResult) []byte {
	t.Helper()
	content, err := result.CanonicalJSON()
	if err != nil {
		t.Fatal(err)
	}
	return content
}
func TestSelectionRuleInventoryIsCentralizedAndValid(t *testing.T) {
	metadata, err := Metadata()
	if err != nil {
		t.Fatal(err)
	}
	known := map[string]bool{}
	for _, skill := range metadata.Skills {
		known[skill.ID] = true
	}
	seen := map[string]bool{}
	for _, rule := range SelectionRules() {
		key := fmt.Sprintf("%s:%s", rule.FactKind, rule.FactValue)
		if seen[key] || !known[rule.SkillID] {
			t.Fatalf("invalid rule %#v", rule)
		}
		seen[key] = true
	}
}

func TestEverySelectionRuleAndUnmappedFact(t *testing.T) {
	for _, rule := range SelectionRules() {
		rule := rule
		t.Run(rule.FactKind+"/"+rule.FactValue, func(t *testing.T) {
			request := requestForFact(rule.FactKind, rule.FactValue)
			if rule.SkillID == "chatgpt-manager-workflow" || rule.SkillID == "composing-approved-roadmap-assignments" {
				request.Consumer = Consumer{Kind: ConsumerChatGPT, MaterializationForm: MaterializationFlatDirectory}
			}
			result, err := Resolve(context.Background(), request)
			if err != nil {
				t.Fatal(err)
			}
			if !reflect.DeepEqual(result.SelectedSkillIDs, []string{rule.SkillID}) || len(result.Exclusions) != 0 {
				t.Fatalf("rule result = %#v", result)
			}
		})
	}
	for kind, values := range acceptedUnmappedFactsV1 {
		for value := range values {
			kind, value := kind, value
			t.Run("unmapped/"+kind+"/"+value, func(t *testing.T) {
				result, err := Resolve(context.Background(), requestForFact(kind, value))
				if err != nil {
					t.Fatal(err)
				}
				if len(result.SelectedSkillIDs) != 0 || len(result.Exclusions) != 1 || result.Exclusions[0].SourceFact != kind+":"+value {
					t.Fatalf("unmapped result = %#v", result)
				}
			})
		}
	}
}

func TestConsumerAndSchemaRefusals(t *testing.T) {
	tests := []struct {
		name   string
		mutate func(*BundleRequest)
	}{
		{"schema", func(request *BundleRequest) { request.SchemaVersion = "apg.skill-bundle-request/v2" }},
		{"consumer", func(request *BundleRequest) { request.Consumer.Kind = "unknown" }},
		{"form", func(request *BundleRequest) { request.Consumer.MaterializationForm = "archive" }},
		{"partial target", func(request *BundleRequest) { request.Consumer.OperatingSystem = "linux" }},
		{"unsupported target", func(request *BundleRequest) {
			request.Consumer.OperatingSystem, request.Consumer.Architecture = "windows", "amd64"
		}},
		{"unknown constraint", func(request *BundleRequest) { request.Consumer.ProviderConstraints = []string{"automatic_router"} }},
		{"contradictory constraint", func(request *BundleRequest) {
			request.Consumer.ProviderConstraints = []string{"filesystem_skill_discovery"}
		}},
		{"duplicate constraint", func(request *BundleRequest) {
			request.Consumer.ProviderConstraints = []string{"in_process_library", "in_process_library"}
		}},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			request := baseRequest()
			test.mutate(&request)
			if _, err := Resolve(context.Background(), request); !errors.Is(err, ErrInvalidRequest) {
				t.Fatalf("refusal = %v", err)
			}
		})
	}
}

func TestEquivalentJSONKeyOrderHasSameIdentity(t *testing.T) {
	request := withLanguage(withTestFramework(baseRequest("planning-repository-work"), "pytest"), "go")
	canonical, err := request.CanonicalJSON()
	if err != nil {
		t.Fatal(err)
	}
	var raw map[string]json.RawMessage
	if err := json.Unmarshal(canonical, &raw); err != nil {
		t.Fatal(err)
	}
	order := []string{"work_class", "test_frameworks", "schema_version", "runtimes", "repository_characteristics", "languages", "explicit_skill_ids", "eager_bodies", "consumer", "capabilities", "budget"}
	reordered := orderedRawObject(t, raw, order)
	decoded, err := DecodeBundleRequest(reordered)
	if err != nil {
		t.Fatal(err)
	}
	left, err := Resolve(context.Background(), request)
	if err != nil {
		t.Fatal(err)
	}
	right, err := Resolve(context.Background(), decoded)
	if err != nil {
		t.Fatal(err)
	}
	if left.RequestFingerprint != right.RequestFingerprint || left.BundleFingerprint != right.BundleFingerprint {
		t.Fatalf("key order changed identity: %#v %#v", left, right)
	}
}

func TestCompositionInventoryIsCanonicalAndInformational(t *testing.T) {
	edges := CompositionRules()
	if len(edges) != 21 {
		t.Fatalf("composition edge count = %d", len(edges))
	}
	for position, edge := range edges {
		if edge.From >= edge.To || (position > 0 && (edges[position-1].From > edge.From || (edges[position-1].From == edge.From && edges[position-1].To >= edge.To))) {
			t.Fatalf("non-canonical edges = %#v", edges)
		}
	}
}

func requestForFact(kind, value string) BundleRequest {
	request := baseRequest()
	switch kind {
	case factCapability:
		request.Capabilities = []string{value}
	case factLanguage:
		request.Languages = []string{value}
	case factRepositoryCharacteristic:
		request.RepositoryCharacteristics = []string{value}
	case factRuntime:
		request.Runtimes = []string{value}
	case factTestFramework:
		request.TestFrameworks = []string{value}
	case factWorkClass:
		request.WorkClass = value
	}
	return request
}

func orderedRawObject(t *testing.T, values map[string]json.RawMessage, order []string) []byte {
	t.Helper()
	var result bytes.Buffer
	result.WriteByte('{')
	for position, key := range order {
		if position > 0 {
			result.WriteByte(',')
		}
		encoded, err := json.Marshal(key)
		if err != nil {
			t.Fatal(err)
		}
		result.Write(encoded)
		result.WriteByte(':')
		result.Write(values[key])
	}
	result.WriteString("}\n")
	return result.Bytes()
}
