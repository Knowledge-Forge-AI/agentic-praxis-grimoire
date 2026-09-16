package hotspot

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"os"
	"path/filepath"
	"strings"
)

type historyCollector struct {
	ctx        context.Context
	root       string
	request    RequestV2
	git        *gitContext
	blobs      *gitBlobReader
	scan       *scanner
	structural Report
	cells      int64
}

func (c *historyCollector) collect(commits []string) (HistorySummary, error) {
	start, err := c.git.treeBlobs(c.ctx, c.request.History.StartOID)
	if err != nil {
		return HistorySummary{}, err
	}
	end, err := c.git.treeBlobs(c.ctx, c.request.History.EndOID)
	if err != nil {
		return HistorySummary{}, err
	}
	transitions, count, err := c.transitions(commits)
	if err != nil {
		return HistorySummary{}, err
	}
	paths := map[string]bool{}
	scanned := map[string]FileRow{}
	for _, f := range c.structural.Files {
		paths[f.Path] = true
		scanned[f.Path] = f
	}
	for p := range start {
		if historyPathIncluded(c.scan, p) {
			paths[p] = true
		}
	}
	for p := range end {
		if historyPathIncluded(c.scan, p) {
			paths[p] = true
		}
	}
	for p := range transitions {
		paths[p] = true
	}
	if len(paths) > DefaultMaxPathTransitions {
		return HistorySummary{}, limitExceeded("history path inventory exceeds 50000")
	}
	h := HistorySummary{Policy: HistoryPolicyV2, StartOID: c.request.History.StartOID, EndOID: c.request.History.EndOID, ObjectFormat: c.git.objectFormat, Commits: append([]string{}, commits...), CommitCount: len(commits), PathTransitionCount: count, Limits: c.request.History.Limits, Files: []FileHistory{}}
	for _, p := range sortedHistoryPaths(paths) {
		if err := validateGitPath(p); err != nil {
			return HistorySummary{}, invalidRequest("unsupported history path")
		}
		if err := c.ctx.Err(); err != nil {
			return HistorySummary{}, err
		}
		f, err := c.measure(p, start[p], end[p], transitions[p], scanned)
		if err != nil {
			return HistorySummary{}, err
		}
		h.Files = append(h.Files, f)
		if f.Churn == nil {
			h.UnavailablePaths++
		} else {
			h.TotalChurn += *f.Churn
		}
		if f.Growth != nil {
			h.NetGrowth += *f.Growth
		}
	}
	h.TotalBlobsRead = c.blobs.totalBlobsRead
	h.TotalInputBytes = c.blobs.totalInputBytes
	h.AggregateCells = c.cells
	h.ID = historyIdentity(h)
	return h, nil
}

func (c *historyCollector) transitions(commits []string) (map[string][]pathTransition, int, error) {
	result := map[string][]pathTransition{}
	count := 0
	parent := c.request.History.StartOID
	for _, commit := range commits {
		changes, err := c.git.diffFirstParentCommit(c.ctx, parent, commit)
		if err != nil {
			return nil, 0, err
		}
		for _, change := range changes {
			if !historyPathIncluded(c.scan, change.path) {
				continue
			}
			count++
			if count > c.request.History.Limits.MaxPathTransitions {
				return nil, 0, limitExceeded("history path transitions exceed limit")
			}
			result[change.path] = append(result[change.path], change)
		}
		parent = commit
	}
	return result, count, nil
}

func (c *historyCollector) measure(path, startOID, endOID string, transitions []pathTransition, scanned map[string]FileRow) (FileHistory, error) {
	start, err := c.blobs.readBlob(startOID)
	if err != nil {
		return FileHistory{}, err
	}
	end, err := c.blobs.readBlob(endOID)
	if err != nil {
		return FileHistory{}, err
	}
	status := c.workingStatus(path, endOID, end, scanned)
	h := FileHistory{Path: path, StartOID: startOID, EndOID: endOID, WorkingTreeStatus: status, TransitionCount: len(transitions), ChurnUnit: "physical-lines-inserted-plus-deleted", GrowthUnit: "physical-lines", ChurnAvailability: AvailabilityUnavailable, GrowthAvailability: AvailabilityUnavailable}
	binary := isBinary(start) || isBinary(end)
	churn, unavailable, err := c.churn(transitions, binary)
	if err != nil {
		return FileHistory{}, err
	}
	if unavailable || (startOID == "" && endOID == "" && len(transitions) == 0) {
		return h, nil
	}
	h.ChurnAvailability = AvailabilityExact
	h.Churn = &churn
	startLines, endLines := physicalLines(start), physicalLines(end)
	h.StartLines = &startLines
	h.EndLines = &endLines
	growth := endLines - startLines
	h.GrowthAvailability = AvailabilityExact
	h.Growth = &growth
	return h, nil
}

func (c *historyCollector) churn(transitions []pathTransition, unavailable bool) (int64, bool, error) {
	var total int64
	for _, tr := range transitions {
		if err := c.ctx.Err(); err != nil {
			return 0, false, err
		}
		// Read every required blob even after detecting binary content: absence is
		// a completeness refusal, not an unavailable numeric metric.
		old, err := c.blobs.readBlob(tr.oldOID)
		if err != nil {
			return 0, false, err
		}
		next, err := c.blobs.readBlob(tr.newOID)
		if err != nil {
			return 0, false, err
		}
		if isBinary(old) || isBinary(next) {
			unavailable = true
		}
		if unavailable {
			continue
		}
		n, err := computeLCSChurn(c.ctx, splitPhysicalLines(old), splitPhysicalLines(next), c.request.History.Limits.MaxComparisonCellsPerPair, &c.cells, c.request.History.Limits.MaxAggregateComparisonCells)
		if err != nil {
			return 0, false, err
		}
		total += n
	}
	return total, unavailable, nil
}

func (c *historyCollector) workingStatus(path, endOID string, end []byte, scanned map[string]FileRow) WorkingTreeStatus {
	if f, ok := scanned[path]; ok {
		if endOID == "" {
			return WorkingTreeUntracked
		}
		sum := sha256.Sum256(end)
		if f.SHA256 == "sha256:"+hex.EncodeToString(sum[:]) {
			return WorkingTreeClean
		}
		return WorkingTreeModified
	}
	// A skipped current entry (including symlinks/extensionless files) is never
	// presented as deleted merely because the structural scanner omitted it.
	current := c.root
	for _, part := range strings.Split(path, "/") {
		current = filepath.Join(current, part)
		info, err := os.Lstat(current)
		if errors.Is(err, os.ErrNotExist) {
			return WorkingTreeDeleted
		}
		if err != nil || info.Mode()&os.ModeSymlink != 0 {
			return WorkingTreeNotScanned
		}
	}

	return WorkingTreeNotScanned
}
