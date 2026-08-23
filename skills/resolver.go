package skills

import (
	"context"
	"fmt"
	"math"
	"sort"
	"unicode/utf8"
)

type inclusion struct {
	reasons map[string]bool
	facts   map[string]bool
}

// Resolve deterministically selects the minimal union of explicit owners and
// exact structured-fact owners. Composition never adds a skill.
func Resolve(ctx context.Context, request BundleRequest) (BundleResult, error) {
	if err := contextError(ctx); err != nil {
		return BundleResult{}, err
	}
	index, err := loadIndex()
	if err != nil {
		return BundleResult{}, err
	}
	if err := validateRequest(request, index); err != nil {
		return BundleResult{}, err
	}
	normalized := normalizeRequest(request)
	requestJSON, err := canonicalJSON(normalized)
	if err != nil {
		return BundleResult{}, fmt.Errorf("%w: request identity", ErrInvalidRequest)
	}
	selected := map[string]*inclusion{}
	add := func(id, reason, fact string) {
		entry := selected[id]
		if entry == nil {
			entry = &inclusion{reasons: map[string]bool{}, facts: map[string]bool{}}
			selected[id] = entry
		}
		entry.reasons[reason] = true
		entry.facts[fact] = true
	}
	for _, id := range normalized.ExplicitSkillIDs {
		add(id, "explicit", factExplicit+":"+id)
	}
	exclusions := []Exclusion{}
	facts := requestFacts(normalized)
	lookup := map[string]SelectionRule{}
	for _, rule := range selectionRulesV1 {
		lookup[rule.FactKind+":"+rule.FactValue] = rule
	}
	for _, fact := range facts {
		key := fact.kind + ":" + fact.value
		if rule, ok := lookup[key]; ok {
			add(rule.SkillID, "structured_fact", key)
			continue
		}
		exclusions = append(exclusions, Exclusion{Reason: "no_unique_owner", SkillID: "", SourceFact: key})
	}
	ids := make([]string, 0, len(selected))
	for id := range selected {
		ids = append(ids, id)
	}
	sort.Strings(ids)
	conflicts := []Conflict{}
	for _, id := range ids {
		if isChatGPTOnly(index.byID[id]) && normalized.Consumer.Kind != ConsumerChatGPT {
			conflicts = append(conflicts, Conflict{Reason: "consumer_incompatible", SkillID: id, SourceFact: firstFact(selected[id].facts)})
		}
	}
	result, buildErr := buildResult(normalized, sha256Hex(requestJSON), index, ids, selected, exclusions, conflicts)
	if buildErr != nil {
		return BundleResult{}, buildErr
	}
	if len(conflicts) > 0 {
		return result, fmt.Errorf("%w: selected provider-specific skill", ErrConsumerMismatch)
	}
	if !result.Budget.BodyBytes.Passed || !result.Budget.DescriptionBytes.Passed || !result.Budget.InitialContextBytes.Passed {
		return result, &BudgetError{Budget: result.Budget}
	}
	return result, nil
}

type structuredFact struct{ kind, value string }

func requestFacts(request BundleRequest) []structuredFact {
	result := []structuredFact{}
	if request.WorkClass != "" {
		result = append(result, structuredFact{factWorkClass, request.WorkClass})
	}
	for _, item := range request.Languages {
		result = append(result, structuredFact{factLanguage, item})
	}
	for _, item := range request.Runtimes {
		result = append(result, structuredFact{factRuntime, item})
	}
	for _, item := range request.TestFrameworks {
		result = append(result, structuredFact{factTestFramework, item})
	}
	for _, item := range request.RepositoryCharacteristics {
		result = append(result, structuredFact{factRepositoryCharacteristic, item})
	}
	for _, item := range request.Capabilities {
		result = append(result, structuredFact{factCapability, item})
	}
	sort.Slice(result, func(left, right int) bool {
		if result[left].kind != result[right].kind {
			return result[left].kind < result[right].kind
		}
		return result[left].value < result[right].value
	})
	return result
}

func validateRequest(request BundleRequest, index corpusIndex) error {
	if request.SchemaVersion != BundleRequestSchemaV1 {
		return fmt.Errorf("%w: unsupported schema version", ErrInvalidRequest)
	}
	sets := []struct {
		name   string
		values []string
	}{
		{"capabilities", request.Capabilities}, {"explicit skill IDs", request.ExplicitSkillIDs}, {"languages", request.Languages},
		{"repository characteristics", request.RepositoryCharacteristics}, {"runtimes", request.Runtimes}, {"test frameworks", request.TestFrameworks},
		{"provider constraints", request.Consumer.ProviderConstraints},
	}
	for _, set := range sets {
		if err := validateSet(set.name, set.values); err != nil {
			return err
		}
	}
	for _, id := range request.ExplicitSkillIDs {
		if _, ok := index.byID[id]; !ok {
			return fmt.Errorf("%w: unavailable explicit skill", ErrInvalidRequest)
		}
	}
	for _, fact := range requestFacts(request) {
		if !knownFact(fact.kind, fact.value) {
			return fmt.Errorf("%w: unknown structured identifier", ErrInvalidRequest)
		}
	}
	if request.WorkClass != "" && !utf8.ValidString(request.WorkClass) {
		return fmt.Errorf("%w: invalid work class", ErrInvalidRequest)
	}
	if err := validateConsumer(request.Consumer); err != nil {
		return err
	}
	for _, limit := range []*int64{request.Budget.MaxBodyBytes, request.Budget.MaxDescriptionBytes, request.Budget.MaxInitialContextBytes} {
		if limit != nil && *limit < 0 {
			return fmt.Errorf("%w: negative budget", ErrInvalidRequest)
		}
	}
	if request.Budget.PromptOverheadBytes < 0 {
		return fmt.Errorf("%w: negative prompt overhead", ErrInvalidRequest)
	}
	return nil
}

func validateSet(name string, values []string) error {
	seen := map[string]bool{}
	for _, value := range values {
		if value == "" || !utf8.ValidString(value) || seen[value] {
			return fmt.Errorf("%w: invalid or duplicate %s", ErrInvalidRequest, name)
		}
		seen[value] = true
	}
	return nil
}

func knownFact(kind, value string) bool {
	for _, rule := range selectionRulesV1 {
		if rule.FactKind == kind && rule.FactValue == value {
			return true
		}
	}
	return acceptedUnmappedFactsV1[kind][value]
}

func validateConsumer(consumer Consumer) error {
	switch consumer.Kind {
	case ConsumerGo, ConsumerCodex, ConsumerClaude, ConsumerChatGPT:
	default:
		return fmt.Errorf("%w: unknown consumer", ErrInvalidRequest)
	}
	switch consumer.MaterializationForm {
	case MaterializationInMemory, MaterializationFlatDirectory:
	default:
		return fmt.Errorf("%w: unsupported materialization form", ErrInvalidRequest)
	}
	if consumer.Kind != ConsumerGo && consumer.MaterializationForm != MaterializationFlatDirectory {
		return fmt.Errorf("%w: filesystem consumer requires flat materialization", ErrInvalidRequest)
	}
	if (consumer.OperatingSystem == "") != (consumer.Architecture == "") {
		return fmt.Errorf("%w: incomplete target constraint", ErrInvalidRequest)
	}
	if consumer.OperatingSystem != "" {
		target := consumer.OperatingSystem + "/" + consumer.Architecture
		if target != "darwin/arm64" && target != "linux/amd64" && target != "linux/arm64" {
			return fmt.Errorf("%w: unsupported target constraint", ErrInvalidRequest)
		}
	}
	allowed := map[string]bool{"filesystem_skill_discovery": true, "in_process_library": true, "isolated_apg_root": true}
	for _, constraint := range consumer.ProviderConstraints {
		if !allowed[constraint] {
			return fmt.Errorf("%w: unknown provider constraint", ErrInvalidRequest)
		}
		if constraint == "filesystem_skill_discovery" && consumer.MaterializationForm != MaterializationFlatDirectory {
			return fmt.Errorf("%w: contradictory provider constraint", ErrInvalidRequest)
		}
		if constraint == "isolated_apg_root" && consumer.MaterializationForm != MaterializationFlatDirectory {
			return fmt.Errorf("%w: contradictory provider constraint", ErrInvalidRequest)
		}
		if constraint == "in_process_library" && (consumer.Kind != ConsumerGo || consumer.MaterializationForm != MaterializationInMemory) {
			return fmt.Errorf("%w: contradictory provider constraint", ErrInvalidRequest)
		}
	}
	return nil
}

func buildResult(request BundleRequest, requestFingerprint string, index corpusIndex, ids []string, selected map[string]*inclusion, exclusions []Exclusion, conflicts []Conflict) (BundleResult, error) {
	result := BundleResult{
		BundleFingerprint: "", CanonicalCorpusDescriptionBytes: index.descriptionBytes,
		CanonicalCorpusDescriptionCharacters: index.descriptionCharacters, CanonicalCorpusSkillCount: len(index.skills),
		CompositionEdges: selectedEdges(ids), CompositionRuleVersion: CompositionVersionV1, Conflicts: conflicts,
		ConsumerKind: request.Consumer.Kind, EagerBodies: request.EagerBodies, EmbeddedCorpusFingerprint: index.fingerprint, Exclusions: exclusions,
		FixedPromptOverheadBytes: request.Budget.PromptOverheadBytes, RequestFingerprint: requestFingerprint,
		MaterializationForm: request.Consumer.MaterializationForm,
		RuleTableVersion:    RuleTableVersionV1, SchemaVersion: BundleResultSchemaV1,
		SelectedSkillIDs: append([]string(nil), ids...), SelectedSkills: []SelectedSkill{},
	}
	for _, id := range ids {
		skill := index.byID[id]
		details := selected[id]
		item := SelectedSkill{BodyBytes: skill.BodyBytes, BodySHA256: skill.BodySHA256, CanonicalPath: skill.CanonicalPath, DescriptionBytes: skill.DescriptionBytes, ID: id, InclusionReasons: keys(details.reasons), SourceFacts: keys(details.facts)}
		result.SelectedSkills = append(result.SelectedSkills, item)
		if result.SelectedBodyBytes > math.MaxInt64-skill.BodyBytes || result.SelectedDescriptionBytes > math.MaxInt64-skill.DescriptionBytes {
			return BundleResult{}, fmt.Errorf("%w: measurement overflow", ErrInvalidRequest)
		}
		result.SelectedBodyBytes += skill.BodyBytes
		result.SelectedDescriptionBytes += skill.DescriptionBytes
	}
	initial := request.Budget.PromptOverheadBytes
	if initial > math.MaxInt64-result.SelectedDescriptionBytes {
		return BundleResult{}, fmt.Errorf("%w: initial context overflow", ErrInvalidRequest)
	}
	initial += result.SelectedDescriptionBytes
	if request.EagerBodies {
		if initial > math.MaxInt64-result.SelectedBodyBytes {
			return BundleResult{}, fmt.Errorf("%w: initial context overflow", ErrInvalidRequest)
		}
		initial += result.SelectedBodyBytes
	}
	result.InitialContextBytes = initial
	result.Budget = BudgetResult{
		BodyBytes:           evaluateBudget(request.Budget.MaxBodyBytes, result.SelectedBodyBytes),
		DescriptionBytes:    evaluateBudget(request.Budget.MaxDescriptionBytes, result.SelectedDescriptionBytes),
		InitialContextBytes: evaluateBudget(request.Budget.MaxInitialContextBytes, result.InitialContextBytes),
	}
	fingerprint, err := resultFingerprint(result)
	if err != nil {
		return BundleResult{}, err
	}
	result.BundleFingerprint = fingerprint
	return result, nil
}

func evaluateBudget(limit *int64, measured int64) BudgetEvaluation {
	copyLimit := limit
	if limit != nil {
		value := *limit
		copyLimit = &value
	}
	return BudgetEvaluation{Limit: copyLimit, Measured: measured, Passed: limit == nil || measured <= *limit}
}

func selectedEdges(ids []string) []CompositionEdge {
	selected := map[string]bool{}
	for _, id := range ids {
		selected[id] = true
	}
	result := []CompositionEdge{}
	for _, edge := range compositionRulesV1 {
		if selected[edge.From] && selected[edge.To] {
			result = append(result, edge)
		}
	}
	return result
}

func resultFingerprint(result BundleResult) (string, error) {
	identity := result
	identity.BundleFingerprint = ""
	content, err := canonicalJSON(identity)
	if err != nil {
		return "", fmt.Errorf("%w: result identity", ErrInvalidResult)
	}
	return sha256Hex(content), nil
}

func isChatGPTOnly(skill SkillMetadata) bool {
	return len(skill.CanonicalPath) > len("chatgpt/") && skill.CanonicalPath[:len("chatgpt/")] == "chatgpt/"
}
func firstFact(values map[string]bool) string {
	list := keys(values)
	if len(list) == 0 {
		return ""
	}
	return list[0]
}
func keys(values map[string]bool) []string {
	result := make([]string, 0, len(values))
	for value := range values {
		result = append(result, value)
	}
	sort.Strings(result)
	return result
}
func contextError(ctx context.Context) error {
	if err := ctx.Err(); err != nil {
		return err
	}
	select {
	case <-ctx.Done():
		return ctx.Err()
	default:
		return nil
	}
}

func validateResultBasics(result BundleResult) error {
	if result.SchemaVersion != BundleResultSchemaV1 || result.RuleTableVersion != RuleTableVersionV1 || result.CompositionRuleVersion != CompositionVersionV1 {
		return fmt.Errorf("%w: unsupported result version", ErrInvalidResult)
	}
	fingerprint, err := resultFingerprint(result)
	if err != nil || fingerprint != result.BundleFingerprint {
		return fmt.Errorf("%w: fingerprint mismatch", ErrInvalidResult)
	}
	if !result.Budget.BodyBytes.Passed || !result.Budget.DescriptionBytes.Passed || !result.Budget.InitialContextBytes.Passed {
		return fmt.Errorf("%w: rejected budget", ErrInvalidResult)
	}
	if len(result.Conflicts) != 0 {
		return fmt.Errorf("%w: unresolved conflict", ErrInvalidResult)
	}
	return nil
}
