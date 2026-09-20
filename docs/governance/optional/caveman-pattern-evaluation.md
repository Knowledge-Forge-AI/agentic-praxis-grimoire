# Evaluation: Upstream Caveman Pattern Analysis and Licensing Boundaries

- **Status**: Authoritative Architectural Evaluation
- **Phase**: APG159 (Milestone V0130-A)
- **Governing Document**: Manager Disposition on APGR v0.13.0 (2026-09-20)
- **Prior Rejection**: Phase APG141 (`APGR-CXT2B`)

---

## 1. Context and Licensing Investigation

Upstream Caveman (`JuliusBrussee/caveman`) explores token reduction, context packing, and runtime prompt compression. As part of researching adaptive context delivery for v0.13, Caveman's architecture and licensing were formally audited:

### Upstream License Split
- **MIT Surfaces**: Skill definitions, documentation, thin client wrappers, contract definitions, and catalog metadata.
- **BSL-1.1 Surfaces**: Core compression engine, context window packing (`contextwindow.Pack()`), runtime proxy, cache engine, MCP server, and Go platform components (converting to Apache-2.0 no earlier than 2030-06-21).

### Standing Rejection
In milestone V0110-B (Phase APG141), APGR formally evaluated and rejected `APGR-CXT2B` (the Caveman importer). That rejection **remains fully in effect**.

---

## 2. Policy Disposition: Clean-Room Pattern Adoption Only

APGR adopts zero code, zero text, and zero runtime dependencies from upstream Caveman:
1. **Zero BSL-1.1 Re-use**: No component under BSL-1.1 is imported, linked, transcribed, or embedded.
2. **Zero Runtime Proxy**: APGR rejects adding a proxy layer between the dispatcher and provider APIs.
3. **Zero Prompt Compression / Rewriting**: APGR rejects lossy compression, token-stripping, or heuristic prompt rewriting.
4. **Clean-Room Design Patterns Adopted**: APGR extracts three architectural *patterns*, implemented entirely natively within `skills` and `footprint`:
   - **Budget-First Selection**: Determining context inclusion based on explicit byte capacity, partitioning candidates into selected, deferred, and inapplicable subsets.
   - **Small Initial Context with Exact Recovery**: Delivering minimal necessary context on turn 1 while providing deterministic, in-band mechanisms (CLI and stdio MCP) to retrieve full skill bodies on demand.
   - **Measured Accounting**: Rigorous, transparent measurement of prompt delivery rather than speculative claims.

---

## 3. Evaluation Conclusion

- Upstream Caveman remains external reference material with strict intellectual property boundaries.
- APGR v0.13 implements all adaptive context capabilities clean-room in the Go `skills` and `footprint` packages.
- No legal, licensing, or runtime risks are introduced.
