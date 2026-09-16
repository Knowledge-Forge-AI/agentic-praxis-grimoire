package jacaconsumer_test

import (
	"context"
	"go/ast"
	"go/parser"
	"go/token"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/routing"
	jacaconsumer "github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/testing/fixtures/jaca_consumer"
)

func TestConsumer_RequestV2StrictValidation(t *testing.T) {
	adapter := jacaconsumer.NewConsumerAdapter()
	ctx := context.Background()

	validJSON := []byte(`{
		"schema": "agent-phase-request-v2",
		"phase_type": "implementation_testing",
		"prompt": "Test work-only request"
	}`)

	req, err := adapter.ParseAndValidateRequest(ctx, validJSON)
	if err != nil {
		t.Fatalf("expected valid request, got: %v", err)
	}
	if !req.Validated || req.PhaseType != "implementation_testing" {
		t.Errorf("unexpected request state: %+v", req)
	}

	invalidCases := []struct {
		name string
		json string
	}{
		{
			name: "execution_mode included",
			json: `{"schema": "agent-phase-request-v2", "phase_type": "implementation_testing", "prompt": "foo", "execution_mode": "normal"}`,
		},
		{
			name: "constraints included",
			json: `{"schema": "agent-phase-request-v2", "phase_type": "implementation_testing", "prompt": "foo", "constraints": ["no_network"]}`,
		},
		{
			name: "unknown field",
			json: `{"schema": "agent-phase-request-v2", "phase_type": "implementation_testing", "prompt": "foo", "extra": 123}`,
		},
		{
			name: "empty prompt",
			json: `{"schema": "agent-phase-request-v2", "phase_type": "implementation_testing", "prompt": ""}`,
		},
	}

	for _, tc := range invalidCases {
		t.Run(tc.name, func(t *testing.T) {
			_, err := adapter.ParseAndValidateRequest(ctx, []byte(tc.json))
			if err == nil {
				t.Fatalf("expected error for %s, got nil", tc.name)
			}
		})
	}
}

func TestConsumer_RoutingAndIndependence(t *testing.T) {
	adapter := jacaconsumer.NewConsumerAdapter()
	ctx := context.Background()

	catalog := map[string]routing.EndpointCapabilities{
		"codex-plan": {
			EndpointAlias: "codex-plan",
			Provider:      "codex",
			Profile:       "codex_implementation",
			Capabilities:  []string{routing.CapRead, routing.CapReasoning},
			Posture:       routing.PostureReadOnly,
		},
		"codex-review": {
			EndpointAlias: "codex-review",
			Provider:      "codex",
			Profile:       "codex_review",
			Capabilities:  []string{routing.CapRead, routing.CapReasoning},
			Posture:       routing.PostureReadOnly,
		},
		"claude-review": {
			EndpointAlias: "claude-review",
			Provider:      "claude",
			Profile:       "claude_review",
			Capabilities:  []string{routing.CapRead, routing.CapReasoning},
			Posture:       routing.PostureReadOnly,
		},
	}

	// 1. Resolve Planner
	planRoute, err := adapter.ResolveTurnRoute(
		ctx,
		"binding_plan",
		[]string{"Planner"},
		"implementation_testing",
		catalog,
		nil,
		nil,
		1726500000.0,
	)
	if err != nil {
		t.Fatalf("planner route failed: %v", err)
	}
	if planRoute.Provider != "codex" {
		t.Errorf("expected planner provider codex, got %s", planRoute.Provider)
	}

	// 2. Resolve Plan Reviewer with independence enforcement
	prior := map[string]jacaconsumer.CallerRouteSelection{
		"binding_plan": *planRoute,
	}

	reviewRoute, err := adapter.ResolveTurnRoute(
		ctx,
		"binding_plan_review",
		[]string{"Plan Reviewer"},
		"architecture_docs",
		catalog,
		nil,
		prior,
		1726500000.0,
	)
	if err != nil {
		t.Fatalf("plan review route failed: %v", err)
	}
	if reviewRoute.Provider == "codex" {
		t.Fatalf("independence violation: plan review chose planner provider codex")
	}
	if reviewRoute.Provider != "claude" {
		t.Errorf("expected plan review provider claude, got %s", reviewRoute.Provider)
	}
}

func TestConsumer_ObservationDigest(t *testing.T) {
	adapter := jacaconsumer.NewConsumerAdapter()
	ctx := context.Background()

	exp := 1726500060.0
	obs := routing.OperationalObservation{
		ObservationID:   "obs-test-1",
		Producer:        "probe",
		ObservationType: "availability",
		Provider:        "codex",
		Timestamp:       1726500000.0,
		ExpiresAt:       &exp,
		StateValue:      "available",
		Detail:          map[string]any{"version": "1.0"},
	}

	fact, err := adapter.DigestObservation(ctx, obs)
	if err != nil {
		t.Fatalf("DigestObservation failed: %v", err)
	}
	if len(fact.CanonicalDigest) != 64 {
		t.Errorf("expected 64-char hex digest, got %q", fact.CanonicalDigest)
	}
}

func TestConsumer_EvidenceAndDispositions(t *testing.T) {
	adapter := jacaconsumer.NewConsumerAdapter()
	ctx := context.Background()

	findings := []jacaconsumer.CallerFindingEvidence{
		{
			FindingID: "F-1",
			Severity:  "blocking",
			Category:  "contract_violation",
			Summary:   "Schema violation",
			FilePath:  "phase/request.go",
			LineStart: 10,
			LineEnd:   12,
		},
	}
	dispositions := []jacaconsumer.CallerFindingDisposition{
		{
			FindingID: "F-1",
			Action:    "amend",
			Basis:     "accepted_authority",
			Rationale: "Amended per specification",
		},
	}

	if err := adapter.ValidateFindingsAndDispositions(ctx, findings, dispositions); err != nil {
		t.Fatalf("expected valid findings/dispositions, got: %v", err)
	}

	// Path traversal in finding must fail
	badFindings := []jacaconsumer.CallerFindingEvidence{
		{
			FindingID: "F-2",
			Severity:  "advisory",
			Category:  "clarity",
			Summary:   "Notice",
			FilePath:  "../secret.txt",
		},
	}
	if err := adapter.ValidateFindingsAndDispositions(ctx, badFindings, nil); err == nil {
		t.Fatal("expected error on path traversal, got nil")
	}
}

func TestConsumer_CandidateAndArtifacts(t *testing.T) {
	adapter := jacaconsumer.NewConsumerAdapter()
	ctx := context.Background()

	cand := jacaconsumer.CallerCandidateSummary{
		CandidateID:  "cand-1",
		Generation:   1,
		ProducerRole: "Producer",
		Commit:       "4885f5f290fe6adc0d763cc8a284ac1179be5c90",
		TreeDigest:   "0ec1c98f51e3b6419e4ab0f3d25fa120aaffb1f8",
	}

	arts := []jacaconsumer.CallerArtifactRecord{
		{
			ArtifactID:   "art-1",
			RelativePath: "docs/report.md",
			MediaType:    "text/markdown",
			ByteSize:     512,
			SHA256:       "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
		},
	}

	if err := adapter.ValidateCandidateAndArtifacts(ctx, cand, arts); err != nil {
		t.Fatalf("expected valid candidate and artifacts, got: %v", err)
	}

	// Invalid relative path with .. must fail
	badArts := []jacaconsumer.CallerArtifactRecord{
		{
			ArtifactID:   "art-2",
			RelativePath: "../escape.md",
			MediaType:    "text/markdown",
			ByteSize:     512,
			SHA256:       "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
		},
	}
	if err := adapter.ValidateCandidateAndArtifacts(ctx, cand, badArts); err == nil {
		t.Fatal("expected error on path traversal, got nil")
	}
}

var testMatrixJSON = []byte("{\n  \"schema\": \"apgr-provider-conformance-matrix-v1\",\n  \"generated_at\": \"2026-09-16T20:30:00Z\",\n  \"providers\": [\"codex\", \"claude\", \"antigravity\"],\n  \"rows\": [\n    {\n      \"id\": \"executable_version_provenance\",\n      \"name\": \"Executable & Version Provenance\",\n      \"description\": \"Subprocess execution and version query of provider tooling without interactive TTY or GUI requirement.\",\n      \"support\": {\n        \"codex\": {\"supported\": true, \"notes\": \"Discovered from PATH via codex --version.\"},\n        \"claude\": {\"supported\": true, \"notes\": \"Discovered via bin/claude-profile or PATH.\"},\n        \"antigravity\": {\"supported\": true, \"notes\": \"Discovered via bin/antigravity-profile or PATH.\"}\n      }\n    },\n    {\n      \"id\": \"profile_resolution\",\n      \"name\": \"Profile Resolution & Pinning\",\n      \"description\": \"Deterministic resolution and pinning of profile configuration parameters into execution arguments.\",\n      \"support\": {\n        \"codex\": {\"supported\": true, \"notes\": \"Compiled profile arguments via controller_generation.codex_profile_arguments.\"},\n        \"claude\": {\"supported\": true, \"notes\": \"Wrapper-owned profile configuration resolution.\"},\n        \"antigravity\": {\"supported\": true, \"notes\": \"Wrapper-owned profile configuration resolution.\"}\n      }\n    },\n    {\n      \"id\": \"requested_model_readback\",\n      \"name\": \"Requested Model Readback\",\n      \"description\": \"Explicit verification and readback of the requested model in provider configuration.\",\n      \"support\": {\n        \"codex\": {\"supported\": true, \"notes\": \"Verified via profile and endpoint configuration.\"},\n        \"claude\": {\"supported\": true, \"notes\": \"Verified via profile and endpoint configuration.\"},\n        \"antigravity\": {\"supported\": true, \"notes\": \"Verified via profile and endpoint configuration.\"}\n      }\n    },\n    {\n      \"id\": \"reasoning_effort_readback\",\n      \"name\": \"Reasoning / Effort Readback\",\n      \"description\": \"Configuration and readback of reasoning/thinking effort settings where supported.\",\n      \"support\": {\n        \"codex\": {\"supported\": true, \"notes\": \"Supported via reasoning effort profile parameters.\"},\n        \"claude\": {\"supported\": true, \"notes\": \"Supported via thinking budget profile parameters.\"},\n        \"antigravity\": {\"supported\": true, \"notes\": \"Supported via thinking/effort parameters in Gemini and Claude profiles.\"}\n      }\n    },\n    {\n      \"id\": \"planner_role_qualification\",\n      \"name\": \"Planner Eligibility\",\n      \"description\": \"Eligibility to serve as the Planner producing structured implementation plans.\",\n      \"support\": {\n        \"codex\": {\"supported\": true, \"notes\": \"Qualified via codex primary endpoints.\"},\n        \"claude\": {\"supported\": true, \"notes\": \"Qualified via claude primary endpoints.\"},\n        \"antigravity\": {\"supported\": true, \"notes\": \"Qualified via antigravity-gemini-* endpoints.\"}\n      }\n    },\n    {\n      \"id\": \"reviewer_role_qualification\",\n      \"name\": \"Reviewer Role Qualification\",\n      \"description\": \"Qualification as independent Plan Reviewer or Work Reviewer satisfying independence invariants.\",\n      \"support\": {\n        \"codex\": {\"supported\": true, \"notes\": \"Qualified for review via codex-*-review endpoints with -s read-only sandbox posture in capabilities.toml.\"},\n        \"claude\": {\"supported\": true, \"notes\": \"Qualified for review via claude-*-review endpoints with --read-only launcher argument in capabilities.toml.\"},\n        \"antigravity\": {\"supported\": true, \"notes\": \"Qualified for review via antigravity-claude-opus-review endpoint with --reviewer argument in capabilities.toml.\"}\n      }\n    },\n    {\n      \"id\": \"producer_role_qualification\",\n      \"name\": \"Producer Eligibility\",\n      \"description\": \"Eligibility to serve as the Producer executing mutating implementation work.\",\n      \"support\": {\n        \"codex\": {\"supported\": true, \"notes\": \"Qualified with mutation capability and workspace execution.\"},\n        \"claude\": {\"supported\": true, \"notes\": \"Qualified with mutation capability and workspace execution.\"},\n        \"antigravity\": {\"supported\": true, \"notes\": \"Qualified with mutation capability and workspace execution.\"}\n      }\n    },\n    {\n      \"id\": \"reviser_role_qualification\",\n      \"name\": \"Reviser Eligibility\",\n      \"description\": \"Eligibility to serve as Reviser incorporating work-review findings into amended candidate trees.\",\n      \"support\": {\n        \"codex\": {\"supported\": true, \"notes\": \"Qualified for post-review revisions.\"},\n        \"claude\": {\"supported\": true, \"notes\": \"Qualified for post-review revisions.\"},\n        \"antigravity\": {\"supported\": true, \"notes\": \"Qualified for post-review revisions.\"}\n      }\n    },\n    {\n      \"id\": \"closeout_role_qualification\",\n      \"name\": \"Closeout Eligibility\",\n      \"description\": \"Eligibility to serve as Closeout Agent producing terminal verification and closeout receipts.\",\n      \"support\": {\n        \"codex\": {\"supported\": true, \"notes\": \"Qualified for closeout execution.\"},\n        \"claude\": {\"supported\": true, \"notes\": \"Qualified for closeout execution.\"},\n        \"antigravity\": {\"supported\": true, \"notes\": \"Qualified for closeout execution.\"}\n      }\n    },\n    {\n      \"id\": \"adapter_structured_output\",\n      \"name\": \"Adapter Structured Output CLI Flag\",\n      \"description\": \"Direct CLI-level native JSON schema enforcement flag in upstream vendor adapter.\",\n      \"support\": {\n        \"codex\": {\"supported\": false, \"notes\": \"Truthful claim: upstream CLI flag unsupported; APGR uses nonce-fenced structured decoding.\"},\n        \"claude\": {\"supported\": false, \"notes\": \"Truthful claim: upstream CLI flag unsupported; APGR uses nonce-fenced structured decoding.\"},\n        \"antigravity\": {\"supported\": false, \"notes\": \"Truthful claim: upstream CLI flag unsupported; APGR uses nonce-fenced structured decoding.\"}\n      }\n    },\n    {\n      \"id\": \"process_group_cleanup\",\n      \"name\": \"Process Group Supervision & Cleanup\",\n      \"description\": \"Clean termination of entire process trees and nested process groups upon completion or cancellation.\",\n      \"support\": {\n        \"codex\": {\"supported\": true, \"notes\": \"Process group kill via SIGTERM/SIGKILL with custody tracking.\"},\n        \"claude\": {\"supported\": true, \"notes\": \"Process group kill via SIGTERM/SIGKILL with custody tracking.\"},\n        \"antigravity\": {\"supported\": true, \"notes\": \"Process group kill via SIGTERM/SIGKILL and activity pipe pgid tracking.\"}\n      }\n    },\n    {\n      \"id\": \"stdout_overflow_protection\",\n      \"name\": \"Bounded Stdout Capture\",\n      \"description\": \"Strict bounding of captured stdout buffer (4 MiB ceiling) with fatal overflow exception.\",\n      \"support\": {\n        \"codex\": {\"supported\": true, \"notes\": \"Enforced by supervisor reader thread.\"},\n        \"claude\": {\"supported\": true, \"notes\": \"Enforced by supervisor reader thread.\"},\n        \"antigravity\": {\"supported\": true, \"notes\": \"Enforced by supervisor reader thread.\"}\n      }\n    },\n    {\n      \"id\": \"stderr_overflow_drain\",\n      \"name\": \"Stderr Overflow Draining\",\n      \"description\": \"Non-fatal draining and truncation of noisy stderr streams exceeding capture buffer limits.\",\n      \"support\": {\n        \"codex\": {\"supported\": true, \"notes\": \"Supervisor drains excess stderr without terminating execution.\"},\n        \"claude\": {\"supported\": true, \"notes\": \"Supervisor drains excess stderr without terminating execution.\"},\n        \"antigravity\": {\"supported\": true, \"notes\": \"Supervisor drains excess stderr without terminating execution.\"}\n      }\n    },\n    {\n      \"id\": \"liveness_outer_ceiling\",\n      \"name\": \"Absolute Timeout / Outer Ceiling\",\n      \"description\": \"Enforcement of absolute execution time limit (default 90,000s) to prevent unbounded execution.\",\n      \"support\": {\n        \"codex\": {\"supported\": true, \"notes\": \"Enforced by provider execution supervisor.\"},\n        \"claude\": {\"supported\": true, \"notes\": \"Enforced by provider execution supervisor.\"},\n        \"antigravity\": {\"supported\": true, \"notes\": \"Enforced by provider execution supervisor.\"}\n      }\n    },\n    {\n      \"id\": \"liveness_advisory_silence\",\n      \"name\": \"Liveness / Advisory Silence Observation\",\n      \"description\": \"Tracking silence periods without premature hard termination of active background work.\",\n      \"support\": {\n        \"codex\": {\"supported\": true, \"notes\": \"Monitored via 900s advisory notice intervals without termination.\"},\n        \"claude\": {\"supported\": true, \"notes\": \"Monitored via 900s advisory notice intervals without termination.\"},\n        \"antigravity\": {\"supported\": true, \"notes\": \"Monitored via 900s advisory notice intervals without termination.\"}\n      }\n    },\n    {\n      \"id\": \"interruption_cleanup\",\n      \"name\": \"Interruption & Signal Cleanup\",\n      \"description\": \"Orderly termination and worktree preservation upon SIGINT/SIGTERM operator interruption.\",\n      \"support\": {\n        \"codex\": {\"supported\": true, \"notes\": \"Supervisor traps signals and cleanly kills child process group.\"},\n        \"claude\": {\"supported\": true, \"notes\": \"Supervisor traps signals and cleanly kills child process group.\"},\n        \"antigravity\": {\"supported\": true, \"notes\": \"Supervisor traps signals and cleanly kills child process group.\"}\n      }\n    },\n    {\n      \"id\": \"tokenless_auth_probe\",\n      \"name\": \"Tokenless Authentication Probe\",\n      \"description\": \"Free, non-intrusive, tokenless query to verify authentication status without credentials scraping.\",\n      \"support\": {\n        \"codex\": {\"supported\": false, \"notes\": \"Truthful claim: no non-intrusive probe exists; returns unknown fail-open.\"},\n        \"claude\": {\"supported\": false, \"notes\": \"Truthful claim: no non-intrusive probe exists; returns unknown fail-open.\"},\n        \"antigravity\": {\"supported\": false, \"notes\": \"Truthful claim: no non-intrusive probe exists; returns unknown fail-open.\"}\n      }\n    },\n    {\n      \"id\": \"tokenless_quota_probe\",\n      \"name\": \"Tokenless Quota Usage Observation\",\n      \"description\": \"Free, non-intrusive query of remaining rate limit / token quota without model burn.\",\n      \"support\": {\n        \"codex\": {\"supported\": false, \"notes\": \"Truthful claim: quota unobservable without model turn; returns unknown fail-open.\"},\n        \"claude\": {\"supported\": false, \"notes\": \"Truthful claim: quota unobservable without model turn; returns unknown fail-open.\"},\n        \"antigravity\": {\"supported\": false, \"notes\": \"Truthful claim: quota unobservable without model turn; returns unknown fail-open.\"}\n      }\n    },\n    {\n      \"id\": \"subagent_worker_support\",\n      \"name\": \"Subagent / Worker Support\",\n      \"description\": \"Support for provider-local internal worker delegation beneath the parent process.\",\n      \"support\": {\n        \"codex\": {\"supported\": false, \"notes\": \"Provider lacks internal supervisor worker protocol in APGR runtime.\"},\n        \"claude\": {\"supported\": false, \"notes\": \"Provider lacks internal supervisor worker protocol in APGR runtime.\"},\n        \"antigravity\": {\"supported\": true, \"notes\": \"Supported via agent-worker supervisor facility and gemini_sub / gemini_flash_sub modes.\"}\n      }\n    },\n    {\n      \"id\": \"failure_cooldown_tracking\",\n      \"name\": \"Failure Cooldown Tracking\",\n      \"description\": \"Tracking of provider failure events in SQLite to enforce transient cooldowns in dynamic router.\",\n      \"support\": {\n        \"codex\": {\"supported\": true, \"notes\": \"Probed via SQLite invocation_attempts failure history within window_seconds.\"},\n        \"claude\": {\"supported\": true, \"notes\": \"Probed via SQLite invocation_attempts failure history within window_seconds.\"},\n        \"antigravity\": {\"supported\": true, \"notes\": \"Probed via SQLite invocation_attempts failure history within window_seconds.\"}\n      }\n    },\n    {\n      \"id\": \"run_resumption\",\n      \"name\": \"Resume & Recovery Evidence\",\n      \"description\": \"Resumption of multi-turn phase execution preserving attempt lineage and route pinning.\",\n      \"support\": {\n        \"codex\": {\"supported\": true, \"notes\": \"Supported via V2 dispatch resume_from_run_id and attempt derivation.\"},\n        \"claude\": {\"supported\": true, \"notes\": \"Supported via V2 dispatch resume_from_run_id and attempt derivation.\"},\n        \"antigravity\": {\"supported\": true, \"notes\": \"Supported via V2 dispatch resume_from_run_id and attempt derivation.\"}\n      }\n    },\n    {\n      \"id\": \"activity_pipe_telemetry\",\n      \"name\": \"Activity Pipe Telemetry\",\n      \"description\": \"Out-of-band progress telemetry and process group reporting via dedicated file descriptor pipe.\",\n      \"support\": {\n        \"codex\": {\"supported\": false, \"notes\": \"Upstream CLI does not expose progress token pipe.\"},\n        \"claude\": {\"supported\": false, \"notes\": \"Upstream CLI does not expose progress token pipe.\"},\n        \"antigravity\": {\"supported\": true, \"notes\": \"Supported via AGENT_CENTRAL_ANTIGRAVITY_ACTIVITY_FD token pipe.\"}\n      }\n    }\n  ]\n}\n")

func TestConsumer_ProviderMatrix(t *testing.T) {
	adapter := jacaconsumer.NewConsumerAdapter()
	ctx := context.Background()

	data := testMatrixJSON
	// Try reading from repository if present, otherwise use embedded canonical fixture
	matrixPath := filepath.Join("..", "..", "..", "docs", "architecture", "provider-conformance-matrix.json")
	if fileData, err := os.ReadFile(matrixPath); err == nil {
		data = fileData
	}

	summary, err := adapter.VerifyProviderMatrix(ctx, data)
	if err != nil {
		t.Fatalf("VerifyProviderMatrix failed: %v", err)
	}
	if summary.RowCount != 22 {
		t.Errorf("expected 22 rows, got %d", summary.RowCount)
	}
	if len(summary.SupportedFamilies) != 3 {
		t.Errorf("expected 3 families, got %d", len(summary.SupportedFamilies))
	}
}

func TestConsumer_ASTTypeContainment(t *testing.T) {
	fset := token.NewFileSet()
	node, err := parser.ParseFile(fset, "adapter.go", nil, 0)
	if err != nil {
		t.Fatalf("failed to parse adapter.go: %v", err)
	}

	prohibitedPrefixes := []string{
		"phase.",
		"routing.",
		"evidence.",
		"candidate.",
		"provider.",
	}

	for _, decl := range node.Decls {
		genDecl, ok := decl.(*ast.GenDecl)
		if !ok || genDecl.Tok != token.TYPE {
			continue
		}
		for _, spec := range genDecl.Specs {
			typeSpec, ok := spec.(*ast.TypeSpec)
			if !ok || !strings.HasPrefix(typeSpec.Name.Name, "Caller") {
				continue
			}
			structType, ok := typeSpec.Type.(*ast.StructType)
			if !ok {
				continue
			}
			for _, field := range structType.Fields.List {
				// Format field type
				fieldTypeStr := formatNode(field.Type)
				for _, p := range prohibitedPrefixes {
					if strings.Contains(fieldTypeStr, p) {
						t.Errorf("AST Containment Violation: type %s field contains leaked APGR type %q (found in %s)",
							typeSpec.Name.Name, p, fieldTypeStr)
					}
				}
			}
		}
	}
}

func formatNode(node ast.Node) string {
	switch n := node.(type) {
	case *ast.Ident:
		return n.Name
	case *ast.SelectorExpr:
		return formatNode(n.X) + "." + n.Sel.Name
	case *ast.ArrayType:
		return "[]" + formatNode(n.Elt)
	case *ast.StarExpr:
		return "*" + formatNode(n.X)
	case *ast.MapType:
		return "map[" + formatNode(n.Key) + "]" + formatNode(n.Value)
	default:
		return ""
	}
}

func TestConsumer_DependencyBoundary(t *testing.T) {
	fset := token.NewFileSet()
	node, err := parser.ParseFile(fset, "adapter.go", nil, parser.ImportsOnly)
	if err != nil {
		t.Fatalf("failed to parse adapter.go imports: %v", err)
	}

	for _, imp := range node.Imports {
		path := strings.Trim(imp.Path.Value, `"`)
		if strings.Contains(path, "os/exec") {
			t.Errorf("Dependency Boundary Violation: os/exec imported in adapter.go")
		}
		if strings.Contains(path, "joint-agentic-command-aegis") || strings.Contains(path, "jaca") {
			t.Errorf("Dependency Boundary Violation: JACA package imported in adapter.go: %s", path)
		}
	}
}

func TestConsumer_ContextCancellation(t *testing.T) {
	adapter := jacaconsumer.NewConsumerAdapter()
	ctx, cancel := context.WithCancel(context.Background())
	cancel()

	_, err := adapter.ParseAndValidateRequest(ctx, []byte(`{}`))
	if err == nil {
		t.Fatal("expected error on cancelled context, got nil")
	}
}
