---
name: go-language-profile
description: Synthetic project-local Go conventions fixture for APGR context-eval scenarios 08 and 09. Not a canonical APGR skill.
---

# Synthetic project Go profile (fixture)

This is a synthetic miniature skill fixture. It exists only to exercise
`project:` namespace collision and explicit override behaviour in the APGR
context-eval corpus. It is not guidance and carries no canonical-corpus
savings evidence.

## Project conventions

- Use `pkg/log` for structured logging; never call `log.Printf` directly.
- Wrap sentinel errors with `%w` and expose them through `pkg/errs`.
- Open database handles only through `pkg/db.Open`, which enforces timeouts.
