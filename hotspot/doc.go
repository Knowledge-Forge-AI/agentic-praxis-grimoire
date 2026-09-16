// Package hotspot provides deterministic, read-only structural source analysis
// and opt-in Git history analysis.
//
// # Version 1 (v1)
//
// The v1 API (Analyze, Request, Report) provides pure in-process structural
// source analysis. It never executes target source, invokes a shell, follows
// symlinks, loads target plugins, or inspects Git history. Growth and churn
// metrics remain explicitly deferred. The canonical machine schema is
// apg.hotspot-report/v1, and terminal and Markdown renderings are deterministic
// projections of the same report model.
//
// # Version 2 (v2)
//
// The v2 API (AnalyzeV2, RequestV2, ReportV2) augments structural analysis
// with opt-in, offline Git history metrics over a specified first-parent
// commit range (start excluded, end included). It computes deterministic
// content-changing transition counts, LCS-based physical line churn, endpoint
// growth, and working-tree digest bindings. All Git interactions run in an
// isolated, read-only subprocess environment with strict refusal checks for
// shallow, grafted, alternate, or partial repositories, and fail-closed resource
// limits. The canonical machine schema is apg.hotspot-report/v2.
package hotspot
