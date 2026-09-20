# ADR 0059 — Decoupled Semantic Role Graph and Flexible Actor Binding

- Status: Accepted
- Date: 2026-09-16
- Phase: APG146 (Roadmap Stage: V0120-A)

## Context

In early dispatcher prototypes, agent roles and physical process invocations were tightly coupled. A "producer" stage invoked a model process that implicitly handled planning disposition, implementation, self-check, and artifact generation in a monolithic turn. Similarly, "closeout" merged work review disposition, final candidate revision, and release-receipt emission.

JACA ADR 0014 introduced a formal successor semantic role graph (`docs/specs/roadmap/roadmap-orchestration-v1.md` §18), clearly distinguishing semantic workflow obligations from actor binding policy. To ensure architectural alignment across the agentic toolchain, APGR requires a clear model that decouples immutable semantic responsibilities from flexible process grouping.

## Decision

1. **Alignment to JACA ADR 0014 Successor Terminology**:
   APGR adopts the following canonical semantic role vocabulary within the single-phase execution runtime:
   - **`Planner`**: Responsible for investigating task requirements and proposing an initial candidate plan material.
   - **`Plan Reviewer`**: Responsible for evaluating the plan proposal against repository constraints and emitting typed findings.
   - **`Plan Review Disposition`**: Responsible for dispositioning the plan proposal and review findings (accept, amend, reject, defer, or supersede).
   - **`Producer`**: Responsible for authoring candidate implementation artifacts within the bounded task scope.
   - **`Work Reviewer`**: Responsible for inspecting the candidate implementation and emitting work-stage findings.
   - **`Work Review Disposition`**: Responsible for dispositioning work-stage findings and determining whether revision is required.
   - **`Reviser`**: Responsible for addressing valid review findings and authoring a revised candidate.
   - **`Closeout Agent`**: Responsible for verifying terminal candidate criteria, recording disposition proofs, and preparing final artifacts.
   - *Outer Boundary Roles (JACA-owned)*: `Prompt Compiler` (compiles multi-phase roadmap requirements into a single-phase request) and `Item Dispositioner` (dispositions the roadmap item outcomes across phases).

2. **Decoupling Semantic Roles from Actor Invocations**:
   - A **semantic role** is an invariant workflow responsibility with strict input/output contracts.
   - An **actor binding** is an execution policy determining which process, model profile, or human operator performs one or more roles.
   - Roles may be bound 1:1 with separate process invocations or merged into multi-role invocations based on dispatcher execution policy and efficiency tradeoffs.

3. **Current Merged Responsibilities and Persistence Invariant**:
   - In current standard execution modes (such as `gemini_flash_opus_sub`), practical efficiency merges certain adjacent roles:
     - `Plan Review Disposition + Producer`: The work stage begins with the producer explicitly dispositioning the bound plan proposal and review findings before producing candidate artifacts.
     - `Work Review Disposition + Reviser/Closeout`: The terminal stage dispositions work findings and directly finalizes or revises the candidate.
   - **Persistence Invariant**: Regardless of actor grouping, APGR must generate and persist **distinct, decoupled semantic records** (e.g., plan disposition receipt vs. candidate patch; work review finding disposition vs. closeout proof).
   - This ensures that if future execution policies or higher-assurance workflows unmerge these roles into separate physical turns or distinct provider processes, the underlying data schemas and historical archives require zero reinterpretation.

## Alternatives Considered

- **Conflating Roles with Dispatcher Stages**: Rejected because stages are operational phases of execution, whereas roles represent logical responsibilities. Conflating them prevents unmerging roles when moving to higher-assurance multi-agent configurations.
- **Requiring Discrete Process Invocations for Every Role**: Rejected because invoking separate child processes for small sequential decisions (e.g., accepting an uncontested plan proposal) introduces unnecessary transport overhead, latency, and token consumption.

## Consequences

- In v0.12 stage `V0120-C`, APGR's stage engine will formally model the semantic role graph and ensure distinct record serialization for merged stages.
- Request V2 schemas will accommodate flexible role-to-actor binding without breaking Request V1 compatibility.
