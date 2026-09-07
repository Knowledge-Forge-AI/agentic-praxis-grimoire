# APG115 v0.9.0 release source preparation exit

Phase ID: `APG115`

## Status and scope

APG115 is the repository record identity for `APGR-V090-RELEASE-PREP1`.
This release-source candidate prepares v0.9.0 after accepted APG114.
Dispatcher-owned pre-final review completed with advisory findings; closeout
amended the documentation and verified the affected bytes. Development Git
finalization remains dispatcher-owned. Public v0.8.1 stays published
and immutable; v0.9.0 is unpublished.

## Proposal and review disposition

Proposal disposition: **amend**. The original release-source scope is retained.
The six advisory plan findings are accepted: explicitly cover the v0.9 policy
surface and exclusions, repair future-version npm README enforcement, enumerate
version-bound tests while retaining historical fixtures, correct current release
prose and roadmap supersession, label foreign binaries as cross-compiled archive
evidence only, and distinguish cached upstream observations from remote parity.
No pre-production stage delta was reported. Internal worker results are integration
evidence, not either dispatcher checkpoint.

## Closeout disposition

Disposition: **amend**. The prepared source and prior work-stage corrections are
retained. The four independent review findings are dispositioned as follows:

- F1 accepted as a dispatcher staging requirement: include this new exit record
  and `release/v0.9.0-notes.md` explicitly; a tracked-only staging operation
  would omit required source. The closer leaves the index untouched.
- F2 accepted without code change: scanning excluded entries in v0.8.0 and
  v0.8.1 candidates enforces their existing projection exclusions. This changes
  local candidate validation, not published artifacts or frozen identities.
  The retained public-release owner tests and full gate cover this behavior.
- F3 amended: both npm READMEs link to the integrated qualification record and
  preserve the Linux developer-runner limitation. Candidate install availability
  is explicit in both templates.
- F4 amended: distribution documentation now describes the shared architecture
  and prepared v0.9.0 contract while retaining published v0.8.1 as the baseline.

The reviewer did not execute tests or access the private evidence packet. The
closer checked that packet and its source bindings directly. These later prose
amendments did not receive another independent review. Affected npm packages
were repacked and checked; policy, record identity, local/projected links and
diff checks were rerun. The full work-stage gate is retained for byte-identical
code and tests; it was not rerun for these documentation-only amendments.

## Prepared source

The single VERSION authority and current release workflow select 0.9.0.
The archive epoch table gains the September 7, 2026 UTC source epoch, and the
editable backend default agrees. Historical epochs and released compatibility
requirements remain unchanged. The existing public projector gains the v0.9
surface without admitting private evidence or the excluded Python report oracle.

Current human documentation and proposed release notes distinguish source
qualification from publication and consumer adoption. Python package descriptions
derive from the root README. The test and policy commands require the Python
frontend, an APGR Git checkout, and the relevant developer prerequisites;
native and npm executables do not implement the developer runner.

## Verification boundary

Fresh work-stage qualification passed on Darwin arm64: **3,426 unit tests and
621 integration tests**, with two explained historical-input skips. The exact
80/80 component and 85/85 combined coverage thresholds are unchanged:

- unit: statements 9595/11172; branches 3355/4168
- integration: statements 9586/11172; branches 3338/4168
- combined union: statements 10099/11172; branches 3619/4168

The skips require unavailable APG11 and APG12 public v0.1.0 roots; they are not
passing historical checks. Policy, record identity, focused metadata/version/
workflow/public-projection checks, changed examples, and link checks passed.
The canonical gate observed identical source inventories before and after its
execution. The subsequent result-only edit to this record is separately checked
and explicitly distinguished in the retained terminal source binding.

Actual backend hooks produced matching prepared metadata, wheel METADATA, and
sdist PKG-INFO, including the README body, Markdown content type, summary,
license, version, and five project URLs. An extracted sdist rebuilt the native
wheel. Native installed Python and npm runtime smoke checks passed; installed
Python policy dispatch also passed with the checkout and pinned developer stack.
Missing checkout, missing test prerequisites, and native/npm test-command
refusals were observed separately from successful runtime checks.

All four npm staged packages and tarballs passed README, discovery-field,
version, platform-role, and optional-dependency checks. Three genuine target
binaries were built; foreign Linux binaries were cross-compiled and not executed.
These are validation artifacts, not the final release bundle.

Go vet and race checks passed: 157 top-level tests across 12 packages. Both the
released and disposable local-candidate consumer lanes passed seven XO and five
external-consumer tests each. Released requirements and executable fixture
sources remain unchanged. Historical preservation checks found the 344 selected
release and requirement files byte-identical to entry.

The first complete attempt failed a stale epoch-list assertion; five focused
normalizer tests verified its repair. The second passed all tests but failed
integration branch coverage at 3,333/4,168. The existing real-Git projection
integration case now also verifies that v0.9 validation refuses reintroduced
excluded entries and accepts the projected set. Its 17 tests and 65 subtests
passed, followed by the complete passing gate above. Both failed attempts remain
retained; thresholds and production coverage inventory were not reduced.

Three bounded Gemini workers completed with cleanup proven. Their changes were
accepted with parent corrections and fresh checks; their findings do not replace
dispatcher review. No producer staging, commit, push, or public publication was
performed. Exact entry identities, changed-file hashes, source/fixture inventory,
actual command receipts, logs, and package extracts are retained privately.

## Limitations and remaining work

Linux developer-runner qualification remains pending. Released consumer checks
use the published v0.8.1 requirement and expected sums with a warm cache and public sumdb enabled;
candidate checks use disposable local replacements. Foreign runtime binaries
are archive evidence only and are not executed on Darwin. APG114's original
logs, failures, manifests, and the fact that five closer amendments followed its
independent review remain historical facts, not a new review claim.

After this source is committed, separately authorize: (1) deterministic public
candidate and ten-asset pair reconstruction with publication-packet qualification,
(2) attended public publication and readback, and (3) separate flake promotion if
requested. JACA CI registration, production XO adoption, and later Theme Forge
and Repo Map work remain outside this phase. No successor starts automatically.
