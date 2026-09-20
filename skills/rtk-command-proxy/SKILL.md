---
name: rtk-command-proxy
description: Use when Codex or Claude Code needs to run, choose, verify, troubleshoot, or explain shell commands through RTK, including ordinary command execution, raw-output fallbacks, RTK meta commands, installation checks, name collisions, or Claude PreToolUse rewrite behavior.
---

# RTK Command Proxy

Status: Authored for the Agentic Praxis Grimoire (APGR) as provisional guidance
under ADR 0072. RTK is an external open-source token reduction tool for LLM CLI
workflows. This skill defines operational integration boundaries within APGR
dispatch and provider contexts.

## Core principle

Use Rust Token Killer (RTK) as an advisory tool to reduce shell-output tokens
without altering task authority, role permission boundaries, Git mutation
brokering, working directories, or intended command semantics. RTK is an optional
optimization; when unconfigured, disabled, unavailable, or unqualified, execute
ordinary commands directly without blocking work.

Output filtering is human-facing and non-authoritative. Always obtain machine
JSON reports, nonce results, Git commit hashes, tree identities, raw qualification
logs, SBOM records, manifests, and test receipts through uncompressed raw commands.
Never blindly re-run a failed command raw after underlying effects may have
occurred.

## Do not use

Do not use this skill:

- when the RTK integration is unconfigured, disabled, or unavailable;
- to bypass dispatcher-owned Git brokers, approval boundaries, or sandboxes;
- to compress authoritative evidence, including Git commit hashes, tree diffs,
  machine JSON reports, qualification receipts, or test artifacts;
- to install, upgrade, or modify RTK binaries, host settings, shell hooks, or
  project rules without explicit task authority;
- to wrap dispatcher, launcher, or orchestration lifecycle commands;
- to blindly replay a command raw after execution failure without inspecting
  underlying state changes; or
- as a substitute for explicit executable configuration.

## Procedure

1. **Check integration status**: Determine whether RTK is enabled and available
   for the active provider via configuration or `apgr integrations rtk doctor`.
   If disabled or unavailable, proceed with ordinary uncompressed commands.
2. **Apply client-appropriate execution**:
   - **Codex (`instructions` mode)**: Prefix eligible human-facing read and
     summary commands with the configured RTK executable (e.g., `rtk git status`).
     Do not prefix every shell command. Never double-prefix commands.
   - **Claude Code (`hook` mode)**: Issue ordinary unprefixed shell commands.
     Eligible commands are rewritten transparently by the configured
     `PreToolUse` hook. Keep Git commands single-command and unprefixed so
     dispatcher policy can broker mutations.
   - **Claude Code (`instructions` mode)**: Prefix eligible human-facing commands
     with the configured RTK executable.
   - **Antigravity (`instructions` mode)**: Prefer the RTK-proxied form for
     supported inspection commands.
3. **Execute RTK meta commands**: When authorized by the user's task or explicit
   need, run `rtk gain`, `rtk gain --history`, `rtk discover`, or `rtk proxy <cmd>`
   directly without nested prefixes. Meta commands are task-authorized operations,
   not automatic doctor or mandatory procedure steps.
4. **Preserve raw authoritative evidence**: For any command producing hashes,
   diffs for review, machine JSON, or qualification receipts, execute the raw
   unwrapped command directly. Do not offer `rtk proxy` as interchangeable with
   the required unwrapped authoritative path; dispatcher and qualification evidence
   require raw unwrapped execution.
5. **Handle execution failures safely**: If an RTK-wrapped command fails, inspect
   exit status, stdout, and stderr. Do not blindly re-run raw if the underlying
   command may have already executed or mutated state.

## Project-owned parameters

The target repository and operator configuration own:

- RTK integration enablement (`[integrations.rtk] enabled`);
- absolute path to the configured RTK executable (`executable`);
- minimum acceptable RTK version (`minimum_version`);
- per-provider declared and effective execution modes (`[integrations.rtk.providers]`);
- hook registration and settings paths (`settings.json`);
- tool permissions, execution boundaries, and mutation scopes; and
- qualification and verification standards.

## Evidence and completion

When reporting RTK command execution or doctor diagnostics, provide:

- configured and resolved executable paths and file identity;
- observed RTK version and compatibility against minimum requirements;
- active provider mode and effective rewrite mechanism;
- probe results (version check, hook rewrite check) with bounded execution times;
- distinction between raw authoritative outputs and advisory filtered outputs; and
- verification that Git mutations and candidate artifacts were captured uncompressed.

## Stop or escalate

Stop RTK usage or escalate immediately when:

- an RTK command fails after potentially mutating working tree or repository state;
- binary collision is suspected (e.g., `rtk` binary is not Rust Token Killer);
- a configured executable is missing, non-executable, or fails minimum version
  (stop RTK use and proceed with ordinary unwrapped commands without blocking work);
- an attempt is made to wrap dispatcher Git, commit, push, or candidate hashing;
- hook configuration requires modifying protected or operator-owned settings files;
- RTK rewrite changes intended command arguments, flags, or semantics; or
- mandatory strict-required execution (`required = true`) is demanded despite
  being deferred in v0.13.

## Common mistakes

- Treating RTK output compression as a substitute for raw authoritative evidence.
- Double-prefixing commands (e.g., `rtk rtk git status` or `rtk rtk gain`).
- Blindly retrying failed commands raw after side effects may have already executed.
- Bypassing Git mutation broker policies using `rtk` or `rtk proxy` prefixes.
- Prefixing every shell command indiscriminately in instruction mode.
- Modifying operator hooks or settings files to force RTK availability.
- Assuming an unconfigured integration is an error rather than an ordinary disabled state.
- Estimating token savings with rough heuristics instead of byte-exact measurements.
