package skills

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"sort"
	"unicode/utf8"
)

func sha256Hex(content []byte) string {
	digest := sha256.Sum256(content)
	return hex.EncodeToString(digest[:])
}

func canonicalJSON(value any) ([]byte, error) {
	content, err := json.Marshal(value)
	if err != nil {
		return nil, err
	}
	return append(content, '\n'), nil
}

func (request BundleRequest) CanonicalJSON() ([]byte, error) {
	return canonicalJSON(normalizeRequest(request))
}
func (result BundleResult) CanonicalJSON() ([]byte, error)    { return canonicalJSON(result) }
func (result Materialization) CanonicalJSON() ([]byte, error) { return canonicalJSON(result) }

// DecodeBundleRequest rejects duplicate keys, unknown fields, missing fields,
// malformed UTF-8, trailing JSON, and non-integer budget values.
func DecodeBundleRequest(content []byte) (BundleRequest, error) {
	want := []string{"budget", "capabilities", "consumer", "eager_bodies", "explicit_skill_ids", "languages", "repository_characteristics", "runtimes", "schema_version", "test_frameworks", "work_class"}
	seen, err := scanJSONObject(content)
	if err != nil || !sameKeys(seen, want) {
		return BundleRequest{}, fmt.Errorf("%w: malformed request JSON", ErrInvalidRequest)
	}
	var raw map[string]json.RawMessage
	if err := json.Unmarshal(content, &raw); err != nil {
		return BundleRequest{}, fmt.Errorf("%w: malformed request JSON", ErrInvalidRequest)
	}
	consumerKeys, err := scanJSONObject(raw["consumer"])
	if err != nil || !sameKeys(consumerKeys, []string{"architecture", "kind", "materialization_form", "operating_system", "provider_constraints"}) {
		return BundleRequest{}, fmt.Errorf("%w: malformed consumer", ErrInvalidRequest)
	}
	budgetKeys, err := scanJSONObject(raw["budget"])
	if err != nil || !sameKeys(budgetKeys, []string{"max_body_bytes", "max_description_bytes", "max_initial_context_bytes", "prompt_overhead_bytes"}) {
		return BundleRequest{}, fmt.Errorf("%w: malformed budget", ErrInvalidRequest)
	}
	var request BundleRequest
	if err := decodeTyped(content, &request); err != nil {
		return BundleRequest{}, fmt.Errorf("%w: malformed request JSON", ErrInvalidRequest)
	}
	return request, nil
}

// DecodeBundleResult strictly decodes a previously resolved result for CLI
// materialization.
func DecodeBundleResult(content []byte) (BundleResult, error) {
	want := []string{"budget", "bundle_fingerprint", "canonical_corpus_description_bytes", "canonical_corpus_description_characters", "canonical_corpus_skill_count", "composition_edges", "composition_rule_version", "conflicts", "consumer_kind", "eager_bodies", "embedded_corpus_fingerprint", "exclusions", "fixed_prompt_overhead_bytes", "initial_context_bytes", "materialization_form", "request_fingerprint", "rule_table_version", "schema_version", "selected_body_bytes", "selected_description_bytes", "selected_skill_ids", "selected_skills"}
	seen, err := scanJSONObject(content)
	if err != nil || !sameKeys(seen, want) {
		return BundleResult{}, fmt.Errorf("%w: malformed result JSON", ErrInvalidResult)
	}
	var result BundleResult
	if err := decodeTyped(content, &result); err != nil {
		return BundleResult{}, fmt.Errorf("%w: malformed result JSON", ErrInvalidResult)
	}
	canonical, err := result.CanonicalJSON()
	if err != nil || !bytes.Equal(content, canonical) {
		return BundleResult{}, fmt.Errorf("%w: result JSON is not canonical", ErrInvalidResult)
	}
	return result, nil
}

func decodeTyped(content []byte, destination any) error {
	decoder := json.NewDecoder(bytes.NewReader(content))
	decoder.DisallowUnknownFields()
	decoder.UseNumber()
	if err := decoder.Decode(destination); err != nil {
		return err
	}
	if err := ensureEOF(decoder); err != nil {
		return err
	}
	return nil
}

func scanJSONObject(content []byte) (map[string]bool, error) {
	if !utf8.Valid(content) {
		return nil, errorsJSON("invalid UTF-8")
	}
	decoder := json.NewDecoder(bytes.NewReader(content))
	decoder.UseNumber()
	token, err := decoder.Token()
	if err != nil {
		return nil, err
	}
	delimiter, ok := token.(json.Delim)
	if !ok || delimiter != '{' {
		return nil, errorsJSON("object required")
	}
	seen, err := scanObject(decoder)
	if err != nil {
		return nil, err
	}
	if err := ensureEOF(decoder); err != nil {
		return nil, err
	}
	return seen, nil
}

func scanObject(decoder *json.Decoder) (map[string]bool, error) {
	seen := map[string]bool{}
	for decoder.More() {
		token, err := decoder.Token()
		if err != nil {
			return nil, err
		}
		key, ok := token.(string)
		if !ok || seen[key] {
			return nil, errorsJSON("duplicate or invalid object key")
		}
		seen[key] = true
		if err := scanValue(decoder); err != nil {
			return nil, err
		}
	}
	token, err := decoder.Token()
	if err != nil || token != json.Delim('}') {
		return nil, errorsJSON("unterminated object")
	}
	return seen, nil
}

func scanValue(decoder *json.Decoder) error {
	token, err := decoder.Token()
	if err != nil {
		return err
	}
	delimiter, ok := token.(json.Delim)
	if !ok {
		return nil
	}
	switch delimiter {
	case '{':
		_, err = scanObject(decoder)
		return err
	case '[':
		for decoder.More() {
			if err := scanValue(decoder); err != nil {
				return err
			}
		}
		end, closeErr := decoder.Token()
		if closeErr != nil || end != json.Delim(']') {
			return errorsJSON("unterminated array")
		}
		return nil
	default:
		return errorsJSON("invalid JSON delimiter")
	}
}

func ensureEOF(decoder *json.Decoder) error {
	if _, err := decoder.Token(); err != io.EOF {
		if err == nil {
			return errorsJSON("trailing JSON")
		}
		return err
	}
	return nil
}

func errorsJSON(message string) error { return fmt.Errorf("invalid JSON: %s", message) }

func sameKeys(seen map[string]bool, want []string) bool {
	if len(seen) != len(want) {
		return false
	}
	for _, key := range want {
		if !seen[key] {
			return false
		}
	}
	return true
}

func normalizeRequest(request BundleRequest) BundleRequest {
	result := request
	result.Capabilities = sortedStrings(request.Capabilities)
	result.ExplicitSkillIDs = sortedStrings(request.ExplicitSkillIDs)
	result.Languages = sortedStrings(request.Languages)
	result.RepositoryCharacteristics = sortedStrings(request.RepositoryCharacteristics)
	result.Runtimes = sortedStrings(request.Runtimes)
	result.TestFrameworks = sortedStrings(request.TestFrameworks)
	result.Consumer.ProviderConstraints = sortedStrings(request.Consumer.ProviderConstraints)
	return result
}

func sortedStrings(values []string) []string {
	result := append([]string(nil), values...)
	sort.Strings(result)
	if result == nil {
		return []string{}
	}
	return result
}
