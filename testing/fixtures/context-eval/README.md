# Frozen Context Evaluation Scenarios Inventory

- **Status**: Authoritative Frozen Evaluation Corpus (Corrected under APG159A / V0130-A-CORR1)
- **Phase**: APG159A (Milestone V0130-A-CORR1)
- **Governing ADR**: [ADR 0074](../../../docs/adr/2026/09/0074-context-plan-byte-budgets-and-bounded-mcp-adapter.md)
- **Metrics Specification**: [`context-eval-metrics-and-oracles.json`](context-eval-metrics-and-oracles.json)
- **Correction Revision**: `APG159A-CORR1` supersedes the APG159 numerical freeze (retained in Git history at Exit 00205). This is a pre-implementation correction, not tuning against a held-out set.
- **Consistency Evidence**: a machine-readable all-15 consistency record with commands and results is retained as publication-excluded APG159A evidence; this corpus does not depend on it.

---

## 1. Overview

This directory contains 15 non-executable scenario definitions frozen before implementation tuning in milestone V0130-A and corrected under APG159A. The corpus is divided into two disjoint subsets:
1. **Calibration Subset (Scenarios 01–05)**: Used during early milestone development (V0130-E, V0130-F) for algorithm and budget calibration.
2. **Acceptance Subset (Scenarios 06–15)**: Untouched holdout corpus evaluated strictly in milestone V0130-H to determine whether adaptive mode qualifies as a safe default.

---

## 2. Scenario Catalog

| ID | Filename | Subset | Provider | Focus / Test Objective | Cohort Membership |
|---|---|---|---|---|---|
| **01** | `scenario-01-go-language-calibration.json` | Calibration | Codex | Positive trigger selection for Go language and test profiles. | Calibration, Savings-Eligible (Dev) |
| **02** | `scenario-02-multi-role-binding-calibration.json` | Calibration | Codex | Multi-role context plan merging (`[Plan Review Disposition, Producer]`). | Calibration, Savings-Eligible (Dev) |
| **03** | `scenario-03-non-trigger-negative-calibration.json` | Calibration | Claude | Negative control asserting unrelated language skills are not selected. | Calibration, Correctness-Only |
| **04** | `scenario-04-rtk-slice-calibration.json` | Calibration | Codex | RTK conditional instruction slice delivery under `instructions` mode. | Calibration, Savings-Eligible (Dev) |
| **05** | `scenario-05-antigravity-static-calibration.json` | Calibration | Antigravity | Verifies Antigravity static fallback completes successfully. | Calibration, Fallback-Only |
| **06** | `scenario-06-mixed-repo-evidence-acceptance.json` | Acceptance | Codex | Multi-language evidence ranking across Go, Python, and SQLite. | Acceptance, Savings-Eligible |
| **07** | `scenario-07-mandatory-budget-overflow-acceptance.json` | Acceptance | Claude | Fail-closed rejection when budget cannot fit mandatory doctrine. | Acceptance, Correctness-Only |
| **08** | `scenario-08-dependency-collision-acceptance.json` | Acceptance | Codex | Multi-source collision under default `supplement` policy. | Acceptance, Savings-Eligible |
| **09** | `scenario-09-explicit-source-override-acceptance.json` | Acceptance | Codex | Multi-source collision under explicit `replace` override policy. | Acceptance, Savings-Eligible |
| **10** | `scenario-10-withheld-skill-cli-acceptance.json` | Acceptance | Codex | Withheld skill late acquisition via `apgr skills acquire` CLI. | Acceptance, Savings-Eligible |
| **11** | `scenario-11-withheld-skill-mcp-acceptance.json` | Acceptance | Claude | Withheld skill late acquisition via stdio MCP adapter tool. | Acceptance, Savings-Eligible |
| **12** | `scenario-12-mid-turn-mcp-failure-acceptance.json` | Acceptance | Claude | Mid-turn MCP process exit recovery without replaying producer turn. | Acceptance, Correctness / Recovery |
| **13** | `scenario-13-prelaunch-no-mcp-fallback-acceptance.json` | Acceptance | Claude | Pre-launch MCP unavailability cleanly falling back to static mode. | Acceptance, Fallback-Only |
| **14** | `scenario-14-readonly-fence-safe-acquisition-acceptance.json` | Acceptance | Claude | Read-only reviewer acquiring skill without tripping immutability fence. | Acceptance, Correctness / Authority |
| **15** | `scenario-15-claude-isolated-settings-acceptance.json` | Acceptance | Claude | Selective skill projection via isolated Claude settings source. | Acceptance, Savings-Eligible (Contingent) |

---

## 3. Evaluation Rules and Mathematical Formulas

1. **No Tuning on Acceptance Scenarios**: Any algorithm or weight tuning must be performed exclusively against Scenarios 01–05. Scenarios 06–15 must remain untouched until the final qualification run in V0130-H.
2. **Fixed Model / Route Baseline**: When comparing adaptive vs static delivery, the underlying model route and provider binding must remain strictly identical.
3. **Cohort Predeclaration** (cohort ids in fixtures use exactly the keys declared in the metrics file):
   - `savings_eligible_cohort`: Evaluated for median initial byte savings and cumulative growth. Acceptance members are {06, 08, 09, 10, 11, 15}. Scenario 15 savings is contingent on qualifying Claude selective projection.
   - `savings_eligible_calibration_subset`: {01, 02, 04}. Development calibration only; never feeds the default-flip decision.
   - **Synthetic inputs**: Scenarios 08 and 09 embed a synthetic miniature `project:` skill body (`source_kind: synthetic`) that does not exist in the repository. They are flagged `synthetic_inputs: true`; the default-flip gate is evaluated both over the full savings-eligible cohort and with synthetic-input scenarios excluded, and both must pass. Synthetic bytes never support a canonical corpus savings claim.
   - **Value sources**: every numeric input carries a tag from `measured | synthetic | estimate | declared | unavailable`. `mandatory_doctrine_bytes` is a planning estimate until V0130-F defines the measurable doctrine slice; the RTK slice and the `rtk-command-proxy` skill (Scenario 04) were planned at the original freeze. D has since admitted the canonical skill provisionally; the frozen scenario measurements are historical, not current measurements.
   - `correctness_failure_only_cohort`: {03, 07, 12, 13, 14}. Evaluated as pass/fail correctness, overflow, and authority gates; excluded from savings calculation.
   - `fallback_cohort`: {05, 13}. Evaluated for clean static fallback.
4. **Frozen Mathematical Formulas**:
   - **Initial Controlled Byte Savings**:
     $$\text{Savings} = 1 - \frac{\text{adaptive\_initial}}{\text{static\_initial}}$$
     (with strictly positive measured denominator).
     **Target**: Median savings $\ge 0.20$ (20% reduction) on predeclared savings-eligible acceptance cohort.
   - **Cumulative Controlled Byte Growth**:
     $$\text{Growth} = \frac{\text{adaptive\_cumulative}}{\text{static\_cumulative}} - 1$$
     **Target**: Nearest-rank 95th percentile (p95) growth $\le 0.10$ (10% ceiling).
     *Nearest-rank method*: For $n$ sorted observations, use index $\lceil 0.95 \cdot n \rceil - 1$.
5. **Exact Recovery and Authority Gates (Zero-Tolerance)**:
   - $100\%$ exact body recovery on mandatory recovery scenarios (10, 11, 12, 14).
   - Zero authority regressions (zero worktree drift under `block`, zero index drift, zero HEAD move).
   - Zero material correctness or availability failures.
6. **Token Overhead and Unavailable Data**:
   - Provider-native tokenization overhead is recorded as `unavailable` unless measured directly via provider token counters.
   - The 4-characters-per-token heuristic is strictly rejected. Missing required measurements fail the gate rather than passing by assumption.
7. **Small Samples and Enforcement Status**: the savings-eligible cohort has n = 6 (n = 4 excluding synthetic-input scenarios); with n ≤ 6 the nearest-rank p95 is the maximum observation. These are engineering gates, not statistical population guarantees. Enforcement of every oracle is **planned** (V0130-B/E/F/H), not implemented.

## E-CATALOG1 contract correction

APG163 records `catalog_contract_correction` in scenarios 08 and 09. Executable
Go and installed Python source fixtures now qualify namespace retention and
explicit replacement. This supersedes untested catalog assumptions only; the
synthetic payloads, numerical freeze, ranking/delivery expectations and cohort
policy remain unchanged. No H evaluation, savings result or promotion is claimed.
