package hotspot

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"syscall"
)

const maxDirectoryDepth = 256

var defaultExcludedDirectories = []string{
	".git", ".hg", ".svn", "node_modules", "vendor", ".venv", "venv",
	"dist", "build", "target", ".scratch", "outbox", ".pytest_cache",
	".mypy_cache", "__pycache__", ".cache", "coverage", ".coverage",
}

type exclusionCounter struct {
	description string
	directories int
	files       int
}

type scanner struct {
	ctx          context.Context
	parent       context.Context
	request      Request
	root         string
	totalBytes   int64
	files        []FileRow
	owners       []OwnerRow
	regions      []RegionRow
	warnings     []Warning
	exclusions   map[string]*exclusionCounter
	includeLangs map[Language]bool
	readObserver func(int)
}

func newScanner(ctx, parent context.Context, request Request, root string) *scanner {
	result := &scanner{ctx: ctx, parent: parent, request: request, root: root, files: []FileRow{}, owners: []OwnerRow{}, regions: []RegionRow{}, warnings: []Warning{}, exclusions: map[string]*exclusionCounter{}, includeLangs: map[Language]bool{}}
	for _, name := range defaultExcludedDirectories {
		result.exclusions["default-directory:"+name] = &exclusionCounter{description: "default source-first directory exclusion"}
	}
	for _, path := range request.Filters.ExcludePaths {
		result.exclusions["caller-path:"+path] = &exclusionCounter{description: "caller-supplied root-relative exclusion"}
	}
	for _, rule := range []struct{ name, description string }{
		{"symlink", "symlink entries are never followed"},
		{"non-regular", "non-regular filesystem entries are not source files"},
		{"unknown-extensionless", "extensionless files require a recognized supported shebang"},
		{"include-filter", "file is outside caller include paths"},
		{"language-filter", "file language is outside caller include languages"},
	} {
		result.exclusions[rule.name] = &exclusionCounter{description: rule.description}
	}
	for _, language := range request.Filters.IncludeLanguages {
		result.includeLangs[language] = true
	}
	return result
}

func (scan *scanner) checkContext() error {
	if err := scan.ctx.Err(); err != nil {
		if errors.Is(err, context.Canceled) || scan.parent.Err() != nil {
			return err
		}
		return limitExceeded("elapsed-time limit reached")
	}
	return nil
}

func (scan *scanner) walk(relative string, depth int) error {
	if err := scan.checkContext(); err != nil {
		return err
	}
	if depth > maxDirectoryDepth {
		return limitExceeded("directory depth exceeds 256")
	}
	path := scan.root
	if relative != "" {
		path = filepath.Join(scan.root, filepath.FromSlash(relative))
	}
	metadata, err := os.Lstat(path)
	if err != nil || metadata.Mode()&os.ModeSymlink != 0 || !metadata.IsDir() {
		return rootSafety("directory topology changed during scan")
	}
	entries, err := os.ReadDir(path)
	if err != nil {
		return unreadable(relativeOrDot(relative))
	}
	for _, entry := range entries {
		if err := scan.walkEntry(relative, depth, entry); err != nil {
			return err
		}
	}
	after, err := os.Lstat(path)
	if err != nil || after.Mode()&os.ModeSymlink != 0 || !after.IsDir() || !os.SameFile(metadata, after) {
		return rootSafety("directory topology changed during scan")
	}
	return nil
}

func (scan *scanner) walkEntry(relative string, depth int, entry os.DirEntry) error {
	if err := scan.checkContext(); err != nil {
		return err
	}
	child := entry.Name()
	if relative != "" {
		child = relative + "/" + entry.Name()
	}
	info, err := entry.Info()
	if err != nil {
		return unreadable(child)
	}
	if info.Mode()&os.ModeSymlink != 0 {
		scan.exclusions["symlink"].files++
		return nil
	}
	if info.IsDir() {
		return scan.walkDirectoryEntry(child, entry.Name(), depth)
	}
	if !info.Mode().IsRegular() {
		scan.exclusions["non-regular"].files++
		return nil
	}
	return scan.scanRegularFile(child, entry.Name())
}

func (scan *scanner) walkDirectoryEntry(child, base string, depth int) error {
	if rule := scan.excludedPathRule(child, base, true); rule != "" {
		scan.exclusions[rule].directories++
		return nil
	}
	if !scan.directoryMayMatchInclude(child) {
		scan.exclusions["include-filter"].directories++
		return nil
	}
	return scan.walk(child, depth+1)
}

func (scan *scanner) scanRegularFile(child, base string) error {
	if rule := scan.excludedPathRule(child, base, false); rule != "" {
		scan.exclusions[rule].files++
		return nil
	}
	if !scan.pathIncluded(child) {
		scan.exclusions["include-filter"].files++
		return nil
	}
	content, identity, err := scan.readStable(child, nil)
	if err != nil {
		return err
	}
	class := classify(child, content)
	if class.excludeExtensionless {
		scan.exclusions["unknown-extensionless"].files++
		return nil
	}
	if len(scan.includeLangs) > 0 && !scan.includeLangs[class.language] {
		scan.exclusions["language-filter"].files++
		return nil
	}
	if len(scan.files)+1 > scan.request.Limits.MaxFiles {
		return limitExceeded("maximum analyzed file count reached")
	}
	row, owners, regions, warnings := analyzeFile(child, class, content, identity)
	if err := scan.checkContext(); err != nil {
		return err
	}
	scan.files = append(scan.files, row)
	scan.owners = append(scan.owners, owners...)
	scan.regions = append(scan.regions, regions...)
	scan.warnings = append(scan.warnings, warnings...)
	return nil
}

func (scan *scanner) excludedPathRule(relative, base string, directory bool) string {
	if directory && !scan.request.Filters.DisableDefaultExclusions {
		for _, excluded := range defaultExcludedDirectories {
			if base == excluded {
				return "default-directory:" + excluded
			}
		}
	}
	for _, excluded := range scan.request.Filters.ExcludePaths {
		if pathPrefixMatch(relative, excluded) {
			return "caller-path:" + excluded
		}
	}
	return ""
}

func pathPrefixMatch(path, prefix string) bool {
	return path == prefix || strings.HasPrefix(path, prefix+"/")
}

func (scan *scanner) pathIncluded(relative string) bool {
	if len(scan.request.Filters.IncludePaths) == 0 {
		return true
	}
	for _, include := range scan.request.Filters.IncludePaths {
		if pathPrefixMatch(relative, include) {
			return true
		}
	}
	return false
}

func (scan *scanner) directoryMayMatchInclude(relative string) bool {
	if len(scan.request.Filters.IncludePaths) == 0 {
		return true
	}
	for _, include := range scan.request.Filters.IncludePaths {
		if pathPrefixMatch(relative, include) || pathPrefixMatch(include, relative) {
			return true
		}
	}
	return false
}

type fileIdentity struct {
	bytes  int64
	sha256 string
	lines  *int64
}

func (scan *scanner) readStable(relative string, afterRead func()) ([]byte, fileIdentity, error) {
	if err := scan.checkContext(); err != nil {
		return nil, fileIdentity{}, err
	}
	file, before, err := scan.openStable(relative)
	if err != nil {
		return nil, fileIdentity{}, err
	}
	defer file.Close()
	content, err := scan.readBounded(file, before.Size(), relative)
	if err != nil {
		return nil, fileIdentity{}, err
	}
	if afterRead != nil {
		afterRead()
	}
	if err := scan.verifyStable(file, before, relative, int64(len(content))); err != nil {
		return nil, fileIdentity{}, err
	}
	scan.totalBytes += int64(len(content))
	hash := sha256.Sum256(content)
	lineCount := physicalLines(content)
	return content, fileIdentity{bytes: int64(len(content)), sha256: "sha256:" + hex.EncodeToString(hash[:]), lines: &lineCount}, nil
}

func (scan *scanner) openStable(relative string) (*os.File, os.FileInfo, error) {
	path := filepath.Join(scan.root, filepath.FromSlash(relative))
	if err := validatePathChain(scan.root, relative); err != nil {
		return nil, nil, err
	}
	before, err := os.Lstat(path)
	if err != nil || before.Mode()&os.ModeSymlink != 0 || !before.Mode().IsRegular() {
		return nil, nil, rootSafety("file entry is not a direct regular file: " + relative)
	}
	if before.Size() > scan.request.Limits.MaxBytesPerFile {
		return nil, nil, limitExceeded("per-file byte limit reached at " + relative)
	}
	if before.Size() > scan.request.Limits.MaxTotalBytes-scan.totalBytes {
		return nil, nil, limitExceeded("total byte limit reached")
	}
	file, err := os.OpenFile(path, os.O_RDONLY|syscall.O_NOFOLLOW, 0)
	if err != nil {
		return nil, nil, unreadable(relative)
	}
	opened, err := file.Stat()
	if err != nil || !opened.Mode().IsRegular() || !os.SameFile(before, opened) {
		_ = file.Close()
		return nil, nil, fileDrift(relative)
	}
	return file, before, nil
}

func (scan *scanner) readBounded(file *os.File, expectedSize int64, relative string) ([]byte, error) {
	capacity := expectedSize
	if capacity > 1<<20 {
		capacity = 1 << 20
	}
	content := make([]byte, 0, int(capacity))
	buffer := make([]byte, 64*1024)
	for {
		if err := scan.checkContext(); err != nil {
			return nil, err
		}
		count, readErr := file.Read(buffer)
		if count > 0 {
			if int64(len(content)+count) > scan.request.Limits.MaxBytesPerFile || int64(len(content)+count) > scan.request.Limits.MaxTotalBytes-scan.totalBytes {
				return nil, limitExceeded("byte limit reached during file read")
			}
			content = append(content, buffer[:count]...)
			if scan.readObserver != nil {
				scan.readObserver(count)
			}
		}
		if readErr == io.EOF {
			return content, nil
		}
		if readErr != nil {
			return nil, unreadable(relative)
		}
	}
}

func (scan *scanner) verifyStable(file *os.File, before os.FileInfo, relative string, bytesRead int64) error {
	path := filepath.Join(scan.root, filepath.FromSlash(relative))
	openedAfter, err := file.Stat()
	if err != nil {
		return fileDrift(relative)
	}
	pathAfter, err := os.Lstat(path)
	if err != nil || pathAfter.Mode()&os.ModeSymlink != 0 || !pathAfter.Mode().IsRegular() {
		return fileDrift(relative)
	}
	if !sameStableFile(before, openedAfter) || !sameStableFile(before, pathAfter) || bytesRead != before.Size() {
		return fileDrift(relative)
	}
	if err := validatePathChain(scan.root, relative); err != nil {
		return err
	}
	return nil
}

func sameStableFile(before, after os.FileInfo) bool {
	return os.SameFile(before, after) && before.Size() == after.Size() && before.Mode() == after.Mode() && before.ModTime().Equal(after.ModTime())
}

func validatePathChain(root, relative string) error {
	current := root
	parts := strings.Split(filepath.ToSlash(relative), "/")
	for _, part := range parts {
		if part == "" || part == "." || part == ".." {
			return rootSafety("invalid root-relative path")
		}
		current = filepath.Join(current, part)
		metadata, err := os.Lstat(current)
		if err != nil || metadata.Mode()&os.ModeSymlink != 0 {
			return rootSafety("path chain is not direct: " + relative)
		}
	}
	return nil
}

func (scan *scanner) exclusionRows() []Exclusion {
	keys := make([]string, 0, len(scan.exclusions))
	for key := range scan.exclusions {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	rows := make([]Exclusion, 0, len(keys))
	for _, key := range keys {
		counter := scan.exclusions[key]
		rows = append(rows, Exclusion{Rule: key, Description: counter.description, Directories: counter.directories, Files: counter.files})
	}
	return rows
}

func relativeOrDot(relative string) string {
	if relative == "" {
		return "."
	}
	return relative
}
