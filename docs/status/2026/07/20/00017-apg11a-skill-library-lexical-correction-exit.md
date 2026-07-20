# APG11A Skill-Library Lexical Correction Exit

## Phase identity

- **Phase:** APG11A
- **Date:** 2026-07-20
- **Exit sequence:** `00017`
- **Disposition:** Complete — required-key and fenced-code validation corrected
- **Terminal result:** `skill-library-lexical-validation-corrected`
- **Controlling decision:** ADR 0008, Accepted and corrected forward

## Authority and external correction disposition

The APG11A assignment accepts APG11 in substance and authorizes one narrow
forward correction to its dependency-free read-only skill-library checker. The
phase reproduces required-key shadowing and fenced-code closure false negatives,
adds failing-first behavioral evidence, corrects only the bounded lexical
contracts, reconciles affected APG11 records, obtains fresh checker and
complete-diff review, validates the integrated result, and delivers one private
development commit with linked managed reports.

The phase does not reopen ADR 0008, add general YAML or Markdown, change a
skill, maturity, projection, dependency, command surface, output schema,
diagnostic-code stability policy, public release, global integration, RepoMap,
reference evidence, or retired Superpowers state. It does not begin APG12.

## Accepted APG11 substance

ADR 0008, the normative authoring and maintenance guide, the decision not to
create a seventh authoring skill, the semantic-versus-mechanical ownership
boundary, the standard-library wrapper/helper architecture, the APG-TEST0 test
locations, the 24-theme legacy closure ledger, the APG12 through APG14 roadmap,
and the schema-valid APG11 operational record remain accepted.

All six skill leaves and checked-in projections remain unchanged. All six
catalog rows remain `provisional`.

## Exact false-negative reproductions

Against generated otherwise valid APG libraries, the original APG11 checker
returned exit `0` with empty diagnostics when a valid `name` entry was followed
by either a quoted `"name": other-skill` entry or a
`name : other-skill` entry. Equivalent tested aliases for both required keys
included single quotes, tab-before-colon syntax, and explicit `? key` syntax.

The original checker also returned exit `0` when the only `## Procedure`
heading appeared inside this fence-like body:

````markdown
```markdown
```python
## Procedure
```
```
````

Generated-tree SHA-256 fingerprints were identical before and after every
reproduction command. Exact commands, JSON output, temporary paths, and
fingerprints are retained in publication-excluded evidence.

## Root causes

`parse_frontmatter` recognized only literal `name:` and `description:`
prefixes. Unsupported YAML-equivalent key forms were therefore neither accepted
fields nor invalid fields and could bypass uniqueness, grammar, and
directory-agreement checks.

`visible_lines` used the same permissive prefix expression for fence opening
and closing. While a fence was open, a same-marker line with trailing language
text was incorrectly accepted as a closer, exposing structural content that
should remain hidden.

## Corrected lexical contracts

Every recognized column-zero mapping key must use only ASCII letters, digits,
underscores, or hyphens followed immediately by its key-terminating colon.
Unsupported quoted, whitespace-before-colon, tabbed, and explicit top-level key
forms fail with deterministic diagnostic `APG035`. Exact `name: value` and
`description: value` required scalars remain required once each. Blank lines,
comments, indented optional metadata, indentationless optional sequences, and
optional values remain uninterpreted.

Outside a fence, the existing bounded opening syntax remains accepted. Inside a
fence, closure requires the same marker character, a marker length at least the
opening length, and no trailing content other than spaces or tabs. A marker with
language or other text is content rather than a closer. The shared
`visible_lines` path continues to own heading, link, and catalog visibility.

## Production and test changes

Only `libexec/apg_skill_library_check.py` changes production behavior.
`parse_frontmatter` records unsupported top-level mapping-key forms and
preserves optional-value syntax. `visible_lines` separates opening and closing
recognition. The wrapper is unchanged.

Focused unit coverage includes:

- `test_rejects_ambiguous_top_level_required_key_forms`;
- `test_accepts_plain_top_level_keys_and_ignores_nested_keys`;
- `test_rejects_unsupported_optional_top_level_key_form`; and
- `test_fence_closers_require_same_long_enough_bare_marker`.

Focused integration coverage includes:

- `test_ambiguous_top_level_required_key_is_bounded_noncompliance`; and
- `test_fence_like_content_does_not_expose_required_section`.

Against unchanged APG11 production, the expanded 15-test unit surface failed 12
required-key/fence subcases and the 58-test integration surface failed exactly
the two new command cases. The complete corrected surfaces pass 15 of 15 and 58
of 58. A reviewer-found optional-sequence regression then failed before its
bounded correction and passes in the resulting state.

## Regression and dogfood

The final integrated evidence includes:

- 15 of 15 checker unit tests;
- 58 of 58 checker integration tests with the public root supplied;
- 22 of 22 Bats report-tool families;
- 28 of 28 project-skill integration families;
- development and fresh public v0.1.0 checker passes in deterministic text and
  JSON modes with six skills, six catalog rows, and six projections;
- generated alias-family failures with `APG035`, nested optional metadata
  success, and fence-hidden-heading failure with `APG016`;
- Python byte compilation, command help, exit-status, and no-mutation checks;
- Markdown, local-link, public-to-private, confidentiality, ADR, exit, and Git
  whitespace gates; and
- unchanged skill hashes, projections, and maturity.

The public v0.1.0 pass concerns only the skill-library structure. Its known
omitted `bin/apg-project-skills` wrapper remains an APG12 release defect.

## APG skill use and non-triggers

`debugging-systematically` governed exact reproduction, hypotheses, root-cause
separation, and the bounded correction. `implementing-with-test-discipline`
governed failing-first unit and integration evidence and proportional
regression. `reviewing-and-verifying-repository-work` governed checker and
complete-diff disposition. `composing-bounded-worker-assignments` applied only
to the two authorized read-only reviewers.

`designing-significant-changes` was a non-trigger because ADR 0008's parser,
ownership, and safety architecture remain accepted. `planning-repository-work`
was a non-trigger because this was one bounded correction with one integrated
gate.

## Independent reviews

The fresh checker reviewer accepted the helper-and-test candidate with no
blocker, material finding, or advisory finding. The review independently
reproduced the parent false negatives, verified alias and nested metadata
boundaries, confirmed fence behavior across headings, links, and the catalog,
and passed current/public dogfood and path-safe deterministic diagnostics.

The fresh complete-diff reviewer initially returned `correction-required`.
The reviewer found that the first recognizer rejected indentationless optional
sequence values and found one duplicated private-evidence sentence fragment.
One focused unit regression reproduced the optional-value defect before
correction. The recognizer was narrowed, the duplicate fragment was removed,
and the affected and complete gates passed.

The first narrow confirmation also returned `correction-required`: the
optional flow-value exemption allowed complex top-level keys such as
`[name]: other` and `{name}: other`. Two focused unit subcases failed before
correction. The recognizer now distinguishes flow values from closed flow
collections followed by a key-terminating colon. The corrected terminal exit
and index received final narrow confirmation with no residual finding.

## Artifacts and unchanged state

Public artifacts are the corrected helper and tests, reconciled ADR 0008,
authoring guide, APG11 evaluation and exit, provenance and roadmap records, the
exit index, and this APG11A exit. Publication-excluded records retain exact
reproduction, root-cause, test, dogfood, external-state, and reviewer evidence.
Public artifacts do not link to publication-excluded records.

The reference repository and fresh public checkout remain clean and unchanged.
The active public-backed global checkout and link chain remain unchanged.
RepoMap remains clean at its pre-phase commit and upstream-distance state. The
current plugin configuration and cache retain no Superpowers installation
entry. No operation targeted public release state, global integration mutation,
RepoMap lifecycle, or Superpowers installation or restoration.

## Limitations

- The checker implements the adopted APG lexical subset, not general YAML,
  Markdown, Agent Skills, optional metadata semantics, or harness metadata.
- Passing structure does not establish semantic quality, authority, privacy,
  provenance truth, discovery, maturity, release completeness, or stability.
- The public v0.1.0 wrapper omission remains unresolved until APG12.
- No automatic invocation, comparative superiority, stable maturity, release
  candidate, restoration exercise, or hostile concurrent-writer defense was
  evaluated.

## Next authorization

APG12 remains the next roadmap phase and has not started. It requires a separate
human assignment. APG11A authorizes no successor implementation automatically.

## External disposition requested

External review is requested to **accept APG11A as Complete — required-key and
fenced-code validation corrected; retain accepted APG11 substance, ADR 0008,
the normative guide, the dependency-free checker architecture, the 24-theme
ledger, exactly six unchanged `provisional` skills and projections, unchanged
public/reference/global/RepoMap/Superpowers state, the APG12 ownership boundary,
and authorize no APG12 work automatically**.
