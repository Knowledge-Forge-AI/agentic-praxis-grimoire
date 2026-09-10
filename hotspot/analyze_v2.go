package hotspot

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"sort"
	"strings"
)

// AnalyzeV2 adds explicit bounded history to the unchanged structural analysis.
func AnalyzeV2(ctx context.Context, request RequestV2) (result ReportV2, resultErr error) {
	validated, err := validateRequestV2(request)
	if err != nil {
		return ReportV2{}, err
	}
	root, err := validateRoot(validated.Root)
	if err != nil {
		return ReportV2{}, err
	}
	bounded, cancel := context.WithTimeout(ctx, validated.Limits.MaxDuration)
	defer cancel()
	defer func() {
		if ctx.Err() != nil {
			result = ReportV2{}
			resultErr = ctx.Err()
		} else if bounded.Err() != nil {
			result = ReportV2{}
			resultErr = limitExceeded("elapsed-time limit reached")
		}
	}()
	gc, err := initGitContext(bounded, root)
	if err != nil {
		return ReportV2{}, err
	}
	for _, endpoint := range []struct{ role, oid string }{{"start", validated.History.StartOID}, {"end", validated.History.EndOID}} {
		if err := gc.verifyCommitExists(bounded, endpoint.oid, endpoint.role); err != nil {
			return ReportV2{}, err
		}
	}
	commits, err := gc.firstParentCommits(bounded, validated.History.StartOID, validated.History.EndOID, validated.History.Limits.MaxCommits)
	if err != nil {
		return ReportV2{}, err
	}
	v1req := Request{SchemaVersion: RequestSchemaV1, Root: root, RootID: validated.RootID, ToolVersion: validated.ToolVersion, Limits: validated.Limits, Filters: validated.Filters, DisplayTopN: validated.DisplayTopN}
	structural, err := Analyze(bounded, v1req)
	if err != nil {
		return ReportV2{}, err
	}
	br, err := newGitBlobReader(bounded, gc, validated.History.Limits)
	if err != nil {
		return ReportV2{}, err
	}
	defer br.close()
	collector := historyCollector{ctx: bounded, root: root, request: validated, git: gc, blobs: br, scan: newScanner(bounded, ctx, v1req, root), structural: structural}
	history, err := collector.collect(commits)
	if err != nil {
		return ReportV2{}, err
	}
	result = combineHistory(validated, structural, history)
	result.Fingerprint, err = fingerprintV2(result)
	if err != nil {
		return ReportV2{}, err
	}
	return result, nil
}

func combineHistory(req RequestV2, v1 Report, history HistorySummary) ReportV2 {
	histories := map[string]FileHistory{}
	for _, h := range history.Files {
		histories[h.Path] = h
	}
	files := make([]FileRowV2, 0, len(v1.Files))
	for _, f := range v1.Files {
		h := histories[f.Path]
		files = append(files, FileRowV2{ID: f.ID, Path: f.Path, Language: f.Language, Confidence: f.Confidence, SHA256: f.SHA256, Bytes: f.Bytes, PhysicalLines: f.PhysicalLines, PrimarySize: f.PrimarySize, Generated: f.Generated, RankingEligible: f.RankingEligible, ParseFailure: f.ParseFailure, Metrics: f.Metrics, Ranking: f.Ranking, History: &h})
	}
	c := v1.ScanConfiguration
	return ReportV2{SchemaVersion: ReportSchemaV2, ToolVersion: v1.ToolVersion, RootID: v1.RootID, CompletionStatus: v1.CompletionStatus,
		ScanConfiguration: ScanConfigurationV2{RequestSchemaVersion: RequestSchemaV2, MaxFiles: c.MaxFiles, MaxBytesPerFile: c.MaxBytesPerFile, MaxTotalBytes: c.MaxTotalBytes, MaxDurationMilliseconds: c.MaxDurationMilliseconds, DefaultExclusionsEnabled: c.DefaultExclusionsEnabled, IncludeLanguages: c.IncludeLanguages, IncludePaths: c.IncludePaths, ExcludePaths: c.ExcludePaths, DisplayTopN: c.DisplayTopN, HistoryStartOID: req.History.StartOID, HistoryEndOID: req.History.EndOID, HistoryLimits: req.History.Limits},
		Exclusions:        v1.Exclusions, CapabilityVersion: CapabilityMatrixV2, Capabilities: v1.Capabilities, DeferredCapabilities: []DeferredCapability{}, LanguageAggregates: v1.LanguageAggregates, Files: files, Owners: v1.Owners, ProceduralRegions: v1.ProceduralRegions, RefactoringCandidates: v1.RefactoringCandidates, History: history, Warnings: v1.Warnings}
}

// History uses literal path/default-directory filters, independent of the
// current language classifier. Historical language filters are refused.
func historyPathIncluded(scan *scanner, path string) bool {
	if !scan.pathIncluded(path) {
		return false
	}
	parts := strings.Split(path, "/")
	for i, part := range parts {
		if scan.excludedPathRule(strings.Join(parts[:i+1], "/"), part, i < len(parts)-1) != "" {
			return false
		}
	}
	return true
}

func historyIdentity(h HistorySummary) string {
	h = historyIdentityView(h)
	h.ID = ""
	content, _ := json.Marshal(h)
	sum := sha256.Sum256(content)
	return "sha256:" + hex.EncodeToString(sum[:])
}

func sortedHistoryPaths(paths map[string]bool) []string {
	result := make([]string, 0, len(paths))
	for p := range paths {
		result = append(result, p)
	}
	sort.Strings(result)
	return result
}

// Resource diagnostics describe execution, not semantic observation identity.
func historyIdentityView(h HistorySummary) HistorySummary {
	h.TotalBlobsRead = 0
	h.TotalInputBytes = 0
	h.AggregateCells = 0
	return h
}
