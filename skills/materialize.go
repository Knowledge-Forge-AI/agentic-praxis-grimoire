package skills

import (
	"bytes"
	"context"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"syscall"
)

const cleanupOwnership = "caller owns removal of the returned isolated bundle root"

// Materialize verifies a prior result, writes an owner-only staged view from
// embedded bytes, and atomically publishes the isolated discovery root.
func Materialize(ctx context.Context, request MaterializeRequest) (Materialization, error) {
	if err := contextError(ctx); err != nil {
		return Materialization{}, err
	}
	index, err := loadIndex()
	if err != nil {
		return Materialization{}, err
	}
	if err := validateMaterializableResult(request.Result, index); err != nil {
		return Materialization{}, err
	}
	parent, err := openDestinationParent(request.DestinationParent)
	if err != nil {
		return Materialization{}, err
	}
	defer parent.Close()
	manifest, manifestJSON, materialization, err := materializationDocuments(request.Result)
	if err != nil {
		return Materialization{}, err
	}
	_ = manifest
	finalName := materializedBasename(request.Result.BundleFingerprint)
	if _, statErr := parent.Lstat(finalName); statErr == nil {
		if verifyErr := verifyExistingMaterialization(parent, finalName, manifestJSON, request.Result, index); verifyErr != nil {
			return Materialization{}, verifyErr
		}
		materialization.Root = filepath.Join(request.DestinationParent, finalName)
		materialization.Reused = true
		return materialization, nil
	} else if !errors.Is(statErr, fs.ErrNotExist) {
		return Materialization{}, fmt.Errorf("%w: final root inspection", ErrUnsafeDestination)
	}

	stage, err := createStage(parent, request.Result.BundleFingerprint)
	if err != nil {
		return Materialization{}, err
	}
	stageOwned := true
	defer func() {
		if stageOwned {
			_ = parent.RemoveAll(stage)
		}
	}()
	for _, selected := range request.Result.SelectedSkills {
		if err := contextError(ctx); err != nil {
			return Materialization{}, err
		}
		directory := filepath.ToSlash(filepath.Join(stage, selected.ID))
		if err := parent.Mkdir(directory, 0o700); err != nil {
			return Materialization{}, fmt.Errorf("%w: staging directory", ErrUnsafeDestination)
		}
		body := index.bodyByID[selected.ID]
		name := filepath.ToSlash(filepath.Join(directory, "SKILL.md"))
		if err := writePrivateFile(parent, name, body); err != nil {
			return Materialization{}, err
		}
		if err := syncRootDirectory(parent, directory); err != nil {
			return Materialization{}, err
		}
	}
	if err := contextError(ctx); err != nil {
		return Materialization{}, err
	}
	if err := writePrivateFile(parent, filepath.ToSlash(filepath.Join(stage, ManifestFilename)), manifestJSON); err != nil {
		return Materialization{}, err
	}
	if err := syncRootDirectory(parent, stage); err != nil {
		return Materialization{}, err
	}
	if err := contextError(ctx); err != nil {
		return Materialization{}, err
	}
	if err := parent.Rename(stage, finalName); err != nil {
		if verifyErr := verifyExistingMaterialization(parent, finalName, manifestJSON, request.Result, index); verifyErr != nil {
			return Materialization{}, fmt.Errorf("%w: final root already exists", ErrCollision)
		}
		materialization.Root = filepath.Join(request.DestinationParent, finalName)
		materialization.Reused = true
		return materialization, nil
	}
	stageOwned = false
	if err := syncRootDirectory(parent, "."); err != nil {
		return Materialization{}, err
	}
	materialization.Root = filepath.Join(request.DestinationParent, finalName)
	return materialization, nil
}

func validateMaterializableResult(result BundleResult, index corpusIndex) error {
	if err := validateResultBasics(result); err != nil {
		return err
	}
	switch result.ConsumerKind {
	case ConsumerGo, ConsumerCodex, ConsumerClaude, ConsumerChatGPT:
	default:
		return fmt.Errorf("%w: unknown result consumer", ErrInvalidResult)
	}
	if result.MaterializationForm != MaterializationFlatDirectory {
		return fmt.Errorf("%w: result is not a filesystem materialization", ErrInvalidResult)
	}
	if result.CompositionEdges == nil || result.Conflicts == nil || result.Exclusions == nil || result.SelectedSkillIDs == nil || result.SelectedSkills == nil {
		return fmt.Errorf("%w: noncanonical result collections", ErrInvalidResult)
	}
	if result.EmbeddedCorpusFingerprint != index.fingerprint || result.CanonicalCorpusSkillCount != len(index.skills) || result.CanonicalCorpusDescriptionBytes != index.descriptionBytes || result.CanonicalCorpusDescriptionCharacters != index.descriptionCharacters {
		return fmt.Errorf("%w: stale corpus identity", ErrInvalidResult)
	}
	if len(result.SelectedSkillIDs) != len(result.SelectedSkills) || !sortedUnique(result.SelectedSkillIDs) {
		return fmt.Errorf("%w: selected ID order", ErrInvalidResult)
	}
	var bodyBytes, descriptionBytes int64
	for position, item := range result.SelectedSkills {
		if item.InclusionReasons == nil || item.SourceFacts == nil || item.ID != result.SelectedSkillIDs[position] || !sortedUnique(item.InclusionReasons) || !sortedUnique(item.SourceFacts) || len(item.InclusionReasons) == 0 || len(item.SourceFacts) == 0 {
			return fmt.Errorf("%w: selected skill projection", ErrInvalidResult)
		}
		canonical, ok := index.byID[item.ID]
		if !ok || item.BodyBytes != canonical.BodyBytes || item.BodySHA256 != canonical.BodySHA256 || item.CanonicalPath != canonical.CanonicalPath || item.DescriptionBytes != canonical.DescriptionBytes {
			return fmt.Errorf("%w: selected skill identity", ErrInvalidResult)
		}
		if err := validateReasons(item); err != nil {
			return err
		}
		if isChatGPTOnly(canonical) && result.ConsumerKind != ConsumerChatGPT {
			return fmt.Errorf("%w: provider-specific result consumer", ErrInvalidResult)
		}
		bodyBytes += item.BodyBytes
		descriptionBytes += item.DescriptionBytes
	}
	if bodyBytes != result.SelectedBodyBytes || descriptionBytes != result.SelectedDescriptionBytes {
		return fmt.Errorf("%w: selected measurements", ErrInvalidResult)
	}
	initial := result.FixedPromptOverheadBytes + descriptionBytes
	if result.EagerBodies {
		initial += bodyBytes
	}
	if result.FixedPromptOverheadBytes < 0 || initial != result.InitialContextBytes {
		return fmt.Errorf("%w: initial context measurement", ErrInvalidResult)
	}
	wantBudget := BudgetResult{
		BodyBytes:           evaluateBudget(result.Budget.BodyBytes.Limit, bodyBytes),
		DescriptionBytes:    evaluateBudget(result.Budget.DescriptionBytes.Limit, descriptionBytes),
		InitialContextBytes: evaluateBudget(result.Budget.InitialContextBytes.Limit, initial),
	}
	if !budgetResultsEqual(result.Budget, wantBudget) {
		return fmt.Errorf("%w: budget measurement", ErrInvalidResult)
	}
	wantEdges := selectedEdges(result.SelectedSkillIDs)
	if !edgesEqual(result.CompositionEdges, wantEdges) {
		return fmt.Errorf("%w: composition projection", ErrInvalidResult)
	}
	if !sortedExclusions(result.Exclusions) || !validExclusions(result.Exclusions) {
		return fmt.Errorf("%w: exclusion projection", ErrInvalidResult)
	}
	return nil
}

func validateReasons(item SelectedSkill) error {
	reasons := map[string]bool{}
	for _, reason := range item.InclusionReasons {
		reasons[reason] = true
	}
	for _, reason := range item.InclusionReasons {
		if reason != "explicit" && reason != "structured_fact" {
			return fmt.Errorf("%w: inclusion reason", ErrInvalidResult)
		}
	}
	for _, fact := range item.SourceFacts {
		kind, value, ok := strings.Cut(fact, ":")
		if !ok {
			return fmt.Errorf("%w: source fact", ErrInvalidResult)
		}
		if kind == factExplicit {
			if !reasons["explicit"] || value != item.ID {
				return fmt.Errorf("%w: explicit source fact", ErrInvalidResult)
			}
			continue
		}
		matched := false
		for _, rule := range selectionRulesV1 {
			if rule.FactKind == kind && rule.FactValue == value && rule.SkillID == item.ID {
				matched = true
				break
			}
		}
		if !matched || !reasons["structured_fact"] {
			return fmt.Errorf("%w: structured source fact", ErrInvalidResult)
		}
	}
	return nil
}

func materializationDocuments(result BundleResult) (BundleManifest, []byte, Materialization, error) {
	manifest := BundleManifest{
		BundleFingerprint: result.BundleFingerprint, EmbeddedCorpusFingerprint: result.EmbeddedCorpusFingerprint,
		Files: []ManifestFile{}, RuleTableVersion: result.RuleTableVersion, SchemaVersion: ManifestSchemaV1,
		SelectedSkillIDs: append([]string(nil), result.SelectedSkillIDs...),
	}
	files := []MaterializedFile{}
	for _, selected := range result.SelectedSkills {
		relative := selected.ID + "/SKILL.md"
		manifest.Files = append(manifest.Files, ManifestFile{BodyBytes: selected.BodyBytes, BodySHA256: selected.BodySHA256, CanonicalPath: selected.CanonicalPath, MaterializedPath: relative, SkillID: selected.ID})
		files = append(files, MaterializedFile{BodyBytes: selected.BodyBytes, BodySHA256: selected.BodySHA256, RelativePath: relative, SkillID: selected.ID})
	}
	content, err := canonicalJSON(manifest)
	if err != nil {
		return BundleManifest{}, nil, Materialization{}, fmt.Errorf("%w: manifest serialization", ErrInvalidResult)
	}
	materialization := Materialization{BundleFingerprint: result.BundleFingerprint, CleanupOwnership: cleanupOwnership, ManifestFingerprint: sha256Hex(content), ManifestSchemaVersion: ManifestSchemaV1, SelectedFiles: files}
	return manifest, content, materialization, nil
}

func openDestinationParent(name string) (*os.Root, error) {
	if name == "" || !filepath.IsAbs(name) || filepath.Clean(name) != name {
		return nil, fmt.Errorf("%w: parent must be absolute and clean", ErrUnsafeDestination)
	}
	current := string(filepath.Separator)
	for _, component := range strings.Split(strings.TrimPrefix(name, current), string(filepath.Separator)) {
		if component == "" {
			continue
		}
		current = filepath.Join(current, component)
		info, err := os.Lstat(current)
		if err != nil || info.Mode()&os.ModeSymlink != 0 {
			return nil, fmt.Errorf("%w: parent path traversal", ErrUnsafeDestination)
		}
	}
	info, err := os.Lstat(name)
	if err != nil || !info.IsDir() || info.Mode()&0o022 != 0 {
		return nil, fmt.Errorf("%w: parent ownership or mode", ErrUnsafeDestination)
	}
	stat, ok := info.Sys().(*syscall.Stat_t)
	if !ok || stat.Uid != uint32(os.Getuid()) {
		return nil, fmt.Errorf("%w: parent ownership", ErrUnsafeDestination)
	}
	root, err := os.OpenRoot(name)
	if err != nil {
		return nil, fmt.Errorf("%w: parent open", ErrUnsafeDestination)
	}
	opened, openErr := root.Stat(".")
	after, afterErr := os.Lstat(name)
	if openErr != nil || afterErr != nil || after.Mode()&os.ModeSymlink != 0 || !os.SameFile(info, opened) || !os.SameFile(after, opened) {
		root.Close()
		return nil, fmt.Errorf("%w: parent changed during open", ErrUnsafeDestination)
	}
	current = string(filepath.Separator)
	for _, component := range strings.Split(strings.TrimPrefix(name, current), string(filepath.Separator)) {
		if component == "" {
			continue
		}
		current = filepath.Join(current, component)
		observed, observeErr := os.Lstat(current)
		if observeErr != nil || observed.Mode()&os.ModeSymlink != 0 {
			root.Close()
			return nil, fmt.Errorf("%w: parent path changed during open", ErrUnsafeDestination)
		}
	}
	return root, nil
}

func createStage(parent *os.Root, fingerprint string) (string, error) {
	for range 16 {
		random := make([]byte, 8)
		if _, err := rand.Read(random); err != nil {
			return "", fmt.Errorf("%w: staging identity", ErrUnsafeDestination)
		}
		name := ".apg-stage-" + fingerprint[:12] + "-" + hex.EncodeToString(random)
		if err := parent.Mkdir(name, 0o700); err == nil {
			return name, nil
		} else if !errors.Is(err, fs.ErrExist) {
			return "", fmt.Errorf("%w: staging root", ErrUnsafeDestination)
		}
	}
	return "", fmt.Errorf("%w: staging collision", ErrCollision)
}

func writePrivateFile(root *os.Root, name string, content []byte) error {
	file, err := root.OpenFile(name, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o600)
	if err != nil {
		return fmt.Errorf("%w: staged file creation", ErrUnsafeDestination)
	}
	if _, err = file.Write(content); err == nil {
		err = file.Sync()
	}
	closeErr := file.Close()
	if err != nil || closeErr != nil {
		return fmt.Errorf("%w: staged file write", ErrUnsafeDestination)
	}
	return nil
}

func syncRootDirectory(root *os.Root, name string) error {
	directory, err := root.Open(name)
	if err != nil {
		return fmt.Errorf("%w: directory sync open", ErrUnsafeDestination)
	}
	err = directory.Sync()
	closeErr := directory.Close()
	if err != nil || closeErr != nil {
		return fmt.Errorf("%w: directory sync", ErrUnsafeDestination)
	}
	return nil
}

func verifyExistingMaterialization(parent *os.Root, name string, manifestJSON []byte, result BundleResult, index corpusIndex) error {
	info, err := parent.Lstat(name)
	if err != nil || !info.IsDir() || info.Mode().Perm() != 0o700 || info.Mode()&os.ModeSymlink != 0 {
		return fmt.Errorf("%w: existing root", ErrCollision)
	}
	root, err := parent.OpenRoot(name)
	if err != nil {
		return fmt.Errorf("%w: existing root", ErrCollision)
	}
	defer root.Close()
	expected := map[string]bool{".": true, ManifestFilename: true}
	for _, selected := range result.SelectedSkills {
		expected[selected.ID] = true
		expected[selected.ID+"/SKILL.md"] = true
	}
	seen := map[string]bool{}
	err = fs.WalkDir(root.FS(), ".", func(path string, entry fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if !expected[path] || seen[path] {
			return fmt.Errorf("unexpected materialized entry")
		}
		seen[path] = true
		info, statErr := root.Lstat(path)
		if statErr != nil || info.Mode()&os.ModeSymlink != 0 {
			return fmt.Errorf("unsafe materialized entry")
		}
		if entry.IsDir() {
			if info.Mode().Perm() != 0o700 {
				return fmt.Errorf("unsafe directory mode")
			}
			return nil
		}
		if !info.Mode().IsRegular() || info.Mode().Perm() != 0o600 || !singleLink(info) {
			return fmt.Errorf("unsafe file metadata")
		}
		return nil
	})
	if err != nil || len(seen) != len(expected) {
		return fmt.Errorf("%w: mismatched existing root", ErrCollision)
	}
	actualManifest, err := root.ReadFile(ManifestFilename)
	if err != nil || !bytes.Equal(actualManifest, manifestJSON) {
		return fmt.Errorf("%w: mismatched manifest", ErrCollision)
	}
	for _, selected := range result.SelectedSkills {
		body, readErr := root.ReadFile(selected.ID + "/SKILL.md")
		if readErr != nil || !bytes.Equal(body, index.bodyByID[selected.ID]) {
			return fmt.Errorf("%w: mismatched skill body", ErrCollision)
		}
	}
	return nil
}

func singleLink(info os.FileInfo) bool {
	stat, ok := info.Sys().(*syscall.Stat_t)
	return ok && stat.Nlink == 1
}
func materializedBasename(fingerprint string) string { return "bundle-" + fingerprint }
func sortedUnique(values []string) bool {
	if !sort.StringsAreSorted(values) {
		return false
	}
	for i := 1; i < len(values); i++ {
		if values[i] == values[i-1] {
			return false
		}
	}
	return true
}
func budgetResultsEqual(left, right BudgetResult) bool {
	return budgetEvaluationEqual(left.BodyBytes, right.BodyBytes) && budgetEvaluationEqual(left.DescriptionBytes, right.DescriptionBytes) && budgetEvaluationEqual(left.InitialContextBytes, right.InitialContextBytes)
}
func budgetEvaluationEqual(left, right BudgetEvaluation) bool {
	if left.Measured != right.Measured || left.Passed != right.Passed || (left.Limit == nil) != (right.Limit == nil) {
		return false
	}
	return left.Limit == nil || *left.Limit == *right.Limit
}
func edgesEqual(left, right []CompositionEdge) bool {
	if len(left) != len(right) {
		return false
	}
	for i := range left {
		if left[i] != right[i] {
			return false
		}
	}
	return true
}
func sortedExclusions(values []Exclusion) bool {
	return sort.SliceIsSorted(values, func(i, j int) bool {
		if values[i].SourceFact != values[j].SourceFact {
			return values[i].SourceFact < values[j].SourceFact
		}
		return values[i].Reason < values[j].Reason
	})
}
func validExclusions(values []Exclusion) bool {
	for _, value := range values {
		kind, fact, ok := strings.Cut(value.SourceFact, ":")
		if !ok || value.Reason != "no_unique_owner" || value.SkillID != "" || !acceptedUnmappedFactsV1[kind][fact] {
			return false
		}
	}
	return true
}
