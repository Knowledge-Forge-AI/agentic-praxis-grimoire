// Package hotspot provides deterministic, read-only structural source analysis.
//
// The package never executes target source, invokes a shell, follows symlinks,
// loads target plugins, or inspects Git history. JSON is the machine authority;
// terminal and Markdown output are deterministic renderings of the same Report.
package hotspot
