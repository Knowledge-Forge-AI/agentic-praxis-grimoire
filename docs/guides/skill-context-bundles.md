# Deterministic Skill Context Bundles

This guide is the current human-facing owner for task-scoped skill selection,
context budgets, and isolated materialization.

APG makes the canonical Markdown under `skills/` directly importable as the
public Go package `github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/skills`.
The Markdown remains the only maintained body authority. The Go package embeds
the flat and ChatGPT-nested leaves with `*/SKILL.md` and
`chatgpt/*/SKILL.md`; `Corpus()` exposes only those embedded resources.

`Metadata()` reconstructs each front-matter name and description plus its
canonical path, byte, character, line, and SHA-256 facts. The reconstructed
projection is serialized with the established Python metadata-resource format.
Its SHA-256 is the corpus fingerprint. A release-like `apgr build-info` reports
the injected expected fingerprint, the embedded actual fingerprint, and their
equality; a mismatch fails closed.

## Public Go API

The task-scoped API is:

```go
func Corpus() fs.FS
func Metadata() (CorpusMetadata, error)
func Resolve(context.Context, BundleRequest) (BundleResult, error)
func Materialize(context.Context, MaterializeRequest) (Materialization, error)
func SelectionRules() []SelectionRule
func CompositionRules() []CompositionEdge
```

`Resolve` reads no prompt or checkout and invokes no model. It sorts set-valued
input before computing request and bundle fingerprints. `Materialize` verifies
a prior result; it never reruns selection.

## Versioned contracts

- request: `apg.skill-bundle-request/v1`
- result: `apg.skill-bundle-result/v1`
- manifest: `apg.skill-bundle-manifest/v1`
- selection rules: `apg.skill-selection-rules/v1`
- composition rules: `apg.skill-composition-rules/v1`

Consequence-bearing JSON refuses unknown fields, duplicate keys, malformed
UTF-8, unsupported versions, duplicate set members, unknown identifiers,
contradictory consumer constraints, invalid materialization forms, and negative
or overflowing budgets. Canonical output is compact UTF-8 JSON with ordered
keys, deterministic arrays, integer numbers, and one trailing LF.

Consumer kinds are `go_library`, `codex`, `claude`, and `chatgpt`.
Materialization forms are `in_memory` and `flat_directory`. The two canonical
ChatGPT leaves are selectable only for `chatgpt`; general leaves remain
provider-neutral. Provider constraints are packaging facts only and do not
select skills or models.

## Selection inventory

The complete v1 automatic mapping is:

| Fact kind | Accepted value | Exact owner |
| --- | --- | --- |
| capability | `apg-routing` | `agentic-praxis-grimoire-workflow` |
| capability | `astro-framework` | `astro-profile` |
| capability | `bash-to-python-conversion` | `converting-bash-scripts-to-python` |
| capability | `chatgpt-manager-routing` | `chatgpt-manager-workflow` |
| capability | `jsx` | `jsx-language-profile` |
| capability | `mdx-documents` | `mdx-profile` |
| capability | `react-components` | `react-component-profile` |
| language | `bash` | `bash-language-profile` |
| language | `css` | `css-language-profile` |
| language | `go` | `go-language-profile` |
| language | `javascript` | `javascript-language-profile` |
| language | `markdown` | `markdown-language-profile` |
| language | `nix` | `nix-language-profile` |
| language | `python` | `python-language-profile` |
| language | `ruby` | `ruby-language-profile` |
| language | `typescript` | `typescript-language-profile` |
| language | `zsh` | `zsh-language-profile` |
| repository characteristic | `dockerfile` | `dockerfile-profile` |
| repository characteristic | `postgresql` | `postgresql-database-profile` |
| repository characteristic | `sqlite` | `sqlite-database-profile` |
| repository characteristic | `vagrantfile` | `vagrantfile-profile` |
| runtime | `nodejs` | `nodejs-runtime-profile` |
| test framework | `bats` | `bats-test-profile` |
| test framework | `go-cmp-v0.7.0` | `go-cmp-test-profile` |
| test framework | `go-native` | `go-test-profile` |
| test framework | `gomock-v0.6.0` | `gomock-test-profile` |
| test framework | `minitest` | `minitest-test-profile` |
| test framework | `nix` | `nix-test-profile` |
| test framework | `pytest` | `pytest-test-profile` |
| test framework | `vitest-v4.1` | `vitest-test-profile` |
| test framework | `zunit-v0.8.2-zsh-v5.9.2` | `zunit-test-profile` |
| work class | `debugging` | `debugging-systematically` |
| work class | `design` | `designing-significant-changes` |
| work class | `guidance_synthesis` | `synthesizing-repository-guidance` |
| work class | `implementation_testing` | `implementing-with-test-discipline` |
| work class | `planning` | `planning-repository-work` |
| work class | `review_verification` | `reviewing-and-verifying-repository-work` |
| work class | `roadmap_delegation` | `composing-approved-roadmap-assignments` |
| work class | `worker_delegation` | `composing-bounded-worker-assignments` |

The rule API also exposes the source document for each row. The following
closed-vocabulary values are accepted but deliberately unselected because no
unique current owner exists: capability `accessibility`; languages `c`,
`csharp`, `java`, `kotlin`, `php`, `rust`, `swift`; repository characteristic
`monorepo`; runtimes `browser`, `bun`, `deno`, `jvm`; test frameworks `jest`,
`mocha`, `rspec`, `unittest`; and work class `research`. Results record those
facts as `no_unique_owner` exclusions.

Explicit IDs add only their named owners. Structured facts add only their exact
table owners. There is no implicit language, runtime, test, or component chain:
composition cannot add a skill.

## Composition inventory

The complete informational v1 edge inventory is:

```text
astro-profile -- jsx-language-profile
astro-profile -- mdx-profile
astro-profile -- nodejs-runtime-profile
astro-profile -- react-component-profile
astro-profile -- typescript-language-profile
go-cmp-test-profile -- gomock-test-profile
go-language-profile -- gomock-test-profile
go-test-profile -- gomock-test-profile
javascript-language-profile -- jsx-language-profile
javascript-language-profile -- react-component-profile
javascript-language-profile -- vitest-test-profile
jsx-language-profile -- mdx-profile
jsx-language-profile -- nodejs-runtime-profile
jsx-language-profile -- react-component-profile
jsx-language-profile -- typescript-language-profile
markdown-language-profile -- mdx-profile
mdx-profile -- react-component-profile
nodejs-runtime-profile -- vitest-test-profile
react-component-profile -- typescript-language-profile
react-component-profile -- vitest-test-profile
typescript-language-profile -- vitest-test-profile
```

Only edges whose two endpoints are already selected enter a bundle result.

## Budgets and identity

The global corpus check remains 9,527 discovery-description bytes; the current
39-leaf corpus occupies 9,504 bytes and 9,492 characters. Task bundle limits are
independent and optional. A missing pointer means unbounded; a present zero is
an exact zero limit.

Initial-context bytes equal caller prompt overhead plus selected description
bytes, plus selected body bytes only in eager-body mode. Overage returns exact
measured/limit facts and no usable materialization: no description is
truncated, no skill is dropped, and no substitute is selected.

The bundle fingerprint covers the normalized request identity, schema and rule
versions, selected content identities, reasons, source facts, exclusions,
conflicts, selected-only edges, and deterministic budget measurements. It
excludes local paths, time, host identity, process identity, randomness, and
diagnostic prose.

## Isolated materialization

Filesystem materialization requires an absolute, clean, physical destination
parent owned by the caller and not group- or other-writable. No path component
may be a symlink. The v1 caller creates the parent before calling APG.

APG writes an owner-only staging child beneath that parent, creates 0700 skill
directories, writes exactly one 0600 direct regular `<skill-id>/SKILL.md` per
selection from embedded bytes, and writes 0600 canonical `manifest.json`.
Files and directories are synchronized before an atomic rename to
`bundle-<full-bundle-fingerprint>`. The flattened target view does not retain
the canonical `chatgpt/` namespace.

An existing exact verified root is reusable; an unknown or mismatched collision
is refused. Cancellation before publication removes only invocation-owned
staging state. The returned cleanup statement assigns later removal to the
caller/task lifecycle. APG never mutates a global or project skill root.

For agent discovery, pass or project the returned root into a disposable
agent-scoped discovery surface. Codex 0.147 qualification used an isolated
project `.agents/skills` entry pointing only at the returned root because that
installed app-server version's generated `skills/list` schema did not yet carry
the newer extra-user-root request field. The returned root itself remained
direct-regular and symlink-free.

## CLI and Python bridge

The Go CLI exposes:

```text
apgr skills list
apgr skills context-report
apgr skills resolve --stdin | --request ABSOLUTE_FILE
apgr skills materialize --result ABSOLUTE_FILE --destination-parent ABSOLUTE_DIR
```

File inputs supplied to `--request` and `--result` must be absolute, clean,
regular files owned by the caller with exact permissions `0600` (single link,
no symlinks). List and context-report preserve the previous Python observable
text/JSON forms. Resolve emits canonical result JSON. Materialize consumes that
prior result and emits canonical materialization JSON. Usage failures exit 2;
bounded runtime, validation, budget, and safety failures exit 1.

Normal Python `skills list` and `skills context-report` are migrated consumer
routes and delegate to Go without semantic fallback. Python `skills resolve`
and `skills materialize` are Go-backed convenience routes. Portable task
selection and materialization are therefore Go-owned.

`skills project` and the historical `apg-project-skills`
install/adopt/check/uninstall command remain Python-owned only as legacy
repository-local symlink projection compatibility. They retain their local
Git-exclude, state, rollback, and safety behavior, but are not a portable bundle
authority and are not a dependency of the standalone Go binary. User/global
installation and flattening also remain classified host maintenance.

APG100 adds the standalone package distributions without changing these bundle
schemas or the corpus. JACA changes, `.flakes`, Nix, publication, deployment,
and activation remain outside this contract.
