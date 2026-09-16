# Antigravity global instructions

Follow the current task first, then repository `AGENTS.md` and repository-local
`GEMINI.md` instructions when present. Use relevant repository skills from
`.agents/skills/`; shared global skills are also available.

Preserve operator-owned staged and unstaged work. When a dispatcher stage owns
Git publication, do not stage, commit, or push. Run verification proportional
to the task and do not create additional review checkpoints.

Treat exact Git hashes found in free-form task text or prior prose as evidence,
not brittle current-state gates, unless a structured dispatcher contract makes
an exact identity mandatory. MCP servers and other tools may be used when they
help the assigned work.

## Transport completion fence

When agent-central supplies a transport completion fence instruction:
- Finish all intended tool operations before beginning the final response.
- Once final response generation begins, do not initiate further tool work.
- Emit the exact completion fence as the final line of the response.
- Make NO tool calls after the completion fence.

## RTK shell-output efficiency

For supported shell and development commands, prefer the RTK-proxied form so
output is compacted before it reaches model context. Typical examples include
`rtk git status`, `rtk git diff`, `rtk git log`, `rtk pytest`, `rtk cargo test`,
`rtk cargo build`, `rtk npm test`, `rtk npm run build`, `rtk cat <file>`,
`rtk rg <pattern>`, and `rtk ls <path>`.

Run RTK meta commands directly: `rtk gain`, `rtk gain --history`, and
`rtk discover`. When genuinely raw, unfiltered output is required, use
`rtk proxy <cmd>`. If RTK does not support a command or changes semantics the
task requires, run the raw command instead of forcing RTK.

This is prompt-based efficiency guidance, not a transparent Antigravity shell
hook and not a security boundary. A repository-local
`.agents/rules/antigravity-rtk-rules.md` may reinforce it, but agent-central
does not require or install that project-local file.

This integration imposes no additional sandbox restriction. Follow the task's
actual authority and stop boundaries.

## Dispatcher-bound Gemini Flash parent

For a Gemini 3.8 Flash High parent in `gemini_flash_sub` or
`gemini_flash_opus_sub`, the dispatcher binds the parent identity, workspace,
authority, and worker state before launch. Use the inherited context through
`bin/agent-worker parent status` and the `job launch`, `job wait`, `job status`,
and `parent drain` commands. Do not run `parent init`, select a parent or
workspace, or create a new root context. Only the listed `gemini` and `luna`
worker kinds are available, each has an independent four-job ceiling, and
capacity cannot be borrowed. The parent owns decomposition, integration,
verification, and final disposition.

The parent is admitted only when the actual Antigravity profile readback names
Gemini 3.8 Flash High. Mode and endpoint aliases do not establish identity.
The inherited leaf marker and removed facade context are same-user coordination
controls, not a hostile-user security boundary; provider-native nested tools
are not qualified.

## Leaf worker subagent constraints

When executing as a Gemini 3.8 Flash High subagent worker under `gemini_sub`,
`gemini_flash_sub`, or `gemini_flash_opus_sub`:
- The subagent is a leaf task managed by an `agent-worker` supervisor process.
- Do not attempt to register as a parent orchestrator or spawn further child subagents.
- Do not initialize a parent, mint worker authority, or spoof parent-family or
  execution-mode state.
- Complete only the bounded task provided in `task.json`, respecting the specified `task_authority` and `mutation_scope`.
- Return result text to the supervisor, which stores output artifacts. Write files
  only when the task explicitly grants mutation authority and path ownership.

These leaf restrictions are task authority and local coordination, not a
security-grade anti-bypass guarantee. Provider-native nested delegation has not
been qualified and must not be used. Read-only worker tasks forbid all test
runners, builds, installers, formatters and Git mutations. Never create a new
root parent budget or invoke a phase dispatcher from a worker.
