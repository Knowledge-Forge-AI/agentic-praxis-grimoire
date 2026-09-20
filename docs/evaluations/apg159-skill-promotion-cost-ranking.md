# Evaluation: Skill Promotion Candidate Cost Ranking and Qualification Tranche

- **Status**: Authoritative Promotion Evaluation Report (Corrected under APG159A / V0130-A-CORR1)
- **Phase**: APG159A (Milestone V0130-A-CORR1)
- **Governing ADR**: [ADR 0073](../adr/2026/09/0073-unified-skill-catalog-and-deterministic-resolution.md)
- **Maturity Authority**: `docs/governance/skill-maturity-ledger.json` and `docs/governance/maturity/apg139/*.json`
- **Measurement Authority**: the canonical `skills/**/SKILL.md` files at the APG159A source tree, reproduced by the command in §1. SHA-256 digests and the command output are retained in a publication-excluded APG159A measurement record and the phase outbox; this document does not depend on them.

---

## 1. Governance Framework and Measurement Methodology

To achieve the milestone V0130-H requirement of promoting five provisional skills to stable maturity, APGR evaluates provisional candidates across the seven mandatory evidence categories defined in `docs/governance/skill-maturity-ledger.json` and APG139 candidate records:

1. `repeated_positive_use` — Demonstrated, documented positive invocations across real repository tasks. (Under APG139, all candidates are assessed **LIMITED**; technology presence in the repo, such as Go code or pytest tests, does not constitute repeated guidance use).
2. `representative_non_triggers` — Explicit, tested boundaries where the skill must NOT trigger. (Assessed **LIMITED** across candidates; boundaries exist but require rigorous adversarial evaluation).
3. `defect_debt_disposition` — Verification that the skill carries zero unresolved blocking or active debts.
4. `rollback` — Demonstrated non-destructive de-projection and removal. (**SUPPORTED** across candidates).
5. `provenance` — Clean-room authoring documentation and third-party rights clearance. (**SUPPORTED** across candidates).
6. `independent_review` — Structured adversarial evaluation by an independent review agent. (**PENDING** dispatcher pre-final review across candidates).
7. `current_validation` — Clean validation under `bin/apg-check-skill-library`. (**LIMITED** across candidates; structural validation alone does not prove semantic efficacy).

### Measurement Standards and Units
- **Measurement Units**: UTF-8 bytes and Unicode characters. Measured over canonical repository files under `skills/**/SKILL.md`.
- **Newline Treatment**: Canonical POSIX line feed (`\n`, `0x0A`).
- **Frontmatter Boundary**: Opening delimiter `---\n` (bytes 0–4) through closing delimiter `\n---\n` inclusive.
- **Body Boundary**: Content strictly following the frontmatter closing delimiter `\n---\n` through EOF. Whole-source bytes and body-only bytes are distinct and never interchanged.
- **Description Boundary**: the value of the frontmatter `description:` key, stripped of surrounding whitespace, measured in UTF-8 bytes and Unicode characters. Description bytes are a subset of frontmatter bytes, never of body bytes.
- **Semantic Source Basis**: canonical skills are unchanged since APG158A; neither APG159 nor APG159A modifies skill bodies. Whole-file values were cross-checked against the generated `skill-metadata.json` source-blob bytes, with source treated as authoritative.
- **Reproducible Command** (run from the repository root; standard library only):
  ```bash
  python3 - <<'EOF'
  import hashlib, pathlib, re
  for cp in [
      "skills/go-language-profile/SKILL.md",
      "skills/go-test-profile/SKILL.md",
      "skills/pytest-test-profile/SKILL.md",
      "skills/markdown-language-profile/SKILL.md",
      "skills/sqlite-database-profile/SKILL.md",
      "skills/postgresql-database-profile/SKILL.md",
      "skills/typescript-language-profile/SKILL.md",
      "skills/chatgpt/composing-approved-roadmap-assignments/SKILL.md",
      "skills/converting-bash-scripts-to-python/SKILL.md",
      "skills/css-language-profile/SKILL.md",
  ]:
      raw = pathlib.Path(cp).read_bytes(); text = raw.decode("utf-8")
      end = raw.index(b"\n---\n", 4) + 5; fm, body = raw[:end], raw[end:]
      desc = re.search(r"^description:\s*(.*)$", fm.decode("utf-8"), re.M).group(1).strip()
      print(cp, "whole", len(raw), len(text), "fm", len(fm), "body", len(body), len(body.decode("utf-8")),
            "desc", len(desc.encode("utf-8")), len(desc), hashlib.sha256(raw).hexdigest(), hashlib.sha256(body).hexdigest())
  EOF
  ```

---

## 2. Canonical Skill Measurement and Maturity Matrix

| Candidate Skill ID | Canonical Path | Whole File (B / chars) | Body Only (B / chars) | Desc (B / chars) | Categories 1–3 (Use, Boundary, Debt) | Categories 4–5 (Rollback, Prov.) | Categories 6–7 (Review, Valid.) | Planning Rank |
|---|---|---:|---:|---:|---|---|---|:---:|
| **`go-language-profile`** | `skills/go-language-profile/SKILL.md` | 16,733 / 16,681 | 16,452 / 16,400 | 233 / 233 | Use: LIMITED; Boundary: LIMITED; Debts: 0 | Rollback: SUPPORTED; Prov: SUPPORTED | Review: PENDING; Valid: LIMITED | **1 (Primary)** |
| **`go-test-profile`** | `skills/go-test-profile/SKILL.md` | 17,821 / 17,805 | 17,487 / 17,471 | 290 / 290 | Use: LIMITED; Boundary: LIMITED; Debts: 0 | Rollback: SUPPORTED; Prov: SUPPORTED | Review: PENDING; Valid: LIMITED | **2 (Primary)** |
| **`pytest-test-profile`** | `skills/pytest-test-profile/SKILL.md` | 17,844 / 17,798 | 17,592 / 17,546 | 204 / 204 | Use: LIMITED; Boundary: LIMITED; Debts: 0 | Rollback: SUPPORTED; Prov: SUPPORTED | Review: PENDING; Valid: LIMITED | **3 (Primary)** |
| **`markdown-language-profile`** | `skills/markdown-language-profile/SKILL.md` | 11,566 / 11,522 | 11,339 / 11,295 | 173 / 173 | Use: LIMITED; Boundary: LIMITED; Debts: 0 | Rollback: SUPPORTED; Prov: SUPPORTED | Review: PENDING; Valid: LIMITED | **4 (Primary)** |
| **`sqlite-database-profile`** | `skills/sqlite-database-profile/SKILL.md` | 17,265 / 17,205 | 16,929 / 16,869 | 284 / 284 | Use: LIMITED; Boundary: LIMITED; Debts: 0 | Rollback: SUPPORTED; Prov: SUPPORTED | Review: PENDING; Valid: LIMITED | **5 (Primary)** |
| `postgresql-database-profile` | `skills/postgresql-database-profile/SKILL.md` | 17,232 / 17,174 | 16,931 / 16,873 | 245 / 245 | Use: LIMITED; Boundary: LIMITED; Debts: 0 | Rollback: SUPPORTED; Prov: SUPPORTED | Review: PENDING; Valid: LIMITED | 6 (Reserve) |
| `typescript-language-profile` | `skills/typescript-language-profile/SKILL.md` | 11,163 / 11,145 | 10,856 / 10,838 | 251 / 251 | Use: LIMITED; Boundary: LIMITED; Debts: 0 | Rollback: SUPPORTED; Prov: SUPPORTED | Review: PENDING; Valid: LIMITED | 7 (Reserve) |
| `composing-approved-roadmap-assignments` | `skills/chatgpt/composing-approved-roadmap-assignments/SKILL.md` | 9,182 / 9,182 | 8,877 / 8,877 | 238 / 238 | Use: LIMITED; Boundary: LIMITED; Debts: 0 | Rollback: SUPPORTED; Prov: SUPPORTED | Review: PENDING; Valid: LIMITED | 8 (Reserve) |
| `converting-bash-scripts-to-python` | `skills/converting-bash-scripts-to-python/SKILL.md` | 16,669 / 16,669 | 16,452 / 16,452 | 155 / 155 | Use: LIMITED; Boundary: LIMITED; Debts: 0 | Rollback: SUPPORTED; Prov: SUPPORTED | Review: PENDING; Valid: LIMITED | 9 (Deferred) |
| `css-language-profile` | `skills/css-language-profile/SKILL.md` | 13,187 / 13,169 | 12,818 / 12,804 | 320 / 316 | Use: LIMITED; Boundary: LIMITED; **Debts: 5 active (4 blocking stable: CSS-QD-001–004; 1 non-blocking: CSS-QD-005)** | Rollback: SUPPORTED; Prov: SUPPORTED | Review: PENDING; Valid: LIMITED | 10 (Excluded) |

*Correction Note*: APG159 previously reported incorrect whole/body byte figures and erroneously substituted 3,146 B (the size of `composing-bounded-worker-assignments`) for `composing-approved-roadmap-assignments` (actual whole size: 9,182 B). Furthermore, APG159 incorrectly attributed `JS-QD-005` to `css-language-profile`. The debt ledger `docs/governance/language-profile-known-debt.json` establishes that `css-language-profile` carries four active debts that block stable promotion (`CSS-QD-001`, `CSS-QD-002`, `CSS-QD-003`, `CSS-QD-004`) and one active non-blocking debt (`CSS-QD-005`).

---

## 3. Primary Promotion Tranche (5 Skills)

The five primary candidates are selected based on planning priority, domain diversity (Go, Python testing, documentation, persistence), and fixture availability for context resolution evaluation. No skill is promoted in this phase; stable criteria remain strictly unlowered.

### 1. `go-language-profile`
- **Cost**: 233 description bytes, 16,452 body bytes (16,733 whole file bytes).
- **Maturity Baseline**: APG139 record notes calibration and code execution do not establish repeated effective guidance use (`repeated_positive_use: LIMITED`, `current_validation: LIMITED`).
- **Gaps to Close for Stable Promotion (V0130-H)**:
  1. Record $\ge 3$ concrete, verified positive guidance invocations on non-trivial Go implementation tasks.
  2. Complete independent adversarial review by a non-author review agent.
  3. Validate sharp non-triggers against Go test files and non-Go repositories.

### 2. `go-test-profile`
- **Cost**: 290 description bytes, 17,487 body bytes (17,821 whole file bytes).
- **Maturity Baseline**: APG139 record notes `repeated_positive_use: LIMITED`, `current_validation: LIMITED`.
- **Gaps to Close for Stable Promotion (V0130-H)**:
  1. Document positive guidance use during Go test suite authoring.
  2. Complete independent adversarial review.
  3. Validate non-triggers against production Go files and foreign test suites.

### 3. `pytest-test-profile`
- **Cost**: 204 description bytes, 17,592 body bytes (17,844 whole file bytes).
- **Maturity Baseline**: APG139 record notes `repeated_positive_use: LIMITED`, `current_validation: LIMITED`.
- **Gaps to Close for Stable Promotion (V0130-H)**:
  1. Document verified guidance use in Python test dispatch tasks.
  2. Complete independent adversarial review.
  3. Validate non-triggers against Bats and unit test runners.

### 4. `markdown-language-profile`
- **Cost**: 173 description bytes, 11,339 body bytes (11,566 whole file bytes).
- **Maturity Baseline**: APG139 record notes `repeated_positive_use: LIMITED`, `current_validation: LIMITED`.
- **Gaps to Close for Stable Promotion (V0130-H)**:
  1. Document positive guidance use in architectural documentation phases.
  2. Complete independent adversarial review.
  3. Validate non-triggers against `.mdx` and structured JSON/YAML frontmatter.

### 5. `sqlite-database-profile`
- **Cost**: 284 description bytes, 16,929 body bytes (17,265 whole file bytes).
- **Maturity Baseline**: APG139 record notes `repeated_positive_use: LIMITED`, `current_validation: LIMITED`.
- **Gaps to Close for Stable Promotion (V0130-H)**:
  1. Document positive guidance use during SQLite persistence maintenance.
  2. Complete independent adversarial review.
  3. Validate non-triggers against PostgreSQL and generic SQL dialects.

---

## 4. Bounded Reserve Tranche (3 Skills)

If any primary candidate fails independent review or reveals blocking debt during V0130-H, one of the three reserve candidates may be substituted:

1. **`postgresql-database-profile`** (Rank 6): Cost: 245 description B / 16,931 body B. 0 debts, clean provenance, pending independent review.
2. **`typescript-language-profile`** (Rank 7): Cost: 251 description B / 10,856 body B. 0 debts, clean provenance, pending independent review.
3. **`composing-approved-roadmap-assignments`** (Rank 8): Cost: 238 description B / 8,877 body B (9,182 whole file B). Located at `skills/chatgpt/composing-approved-roadmap-assignments/SKILL.md`. 0 debts, clean provenance, pending independent review.

### Excluded and Deferred Candidates
- **`converting-bash-scripts-to-python`** (Rank 9): Deferred due to low task frequency across current roadmap dispatches.
- **`css-language-profile`** (Rank 10): Explicitly **excluded from stable promotion** because it carries four accepted debts that block stable promotion (`CSS-QD-001`, `CSS-QD-002`, `CSS-QD-003`, `CSS-QD-004`) and one active non-blocking debt (`CSS-QD-005`). Stable promotion criteria are not lowered.
