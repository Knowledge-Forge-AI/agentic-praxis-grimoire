#!/usr/bin/env python3
"""Integration tests for libexec/apg_skill_library_check.py discovery policy enforcement."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

from apg_skill_library_check import (  # noqa: E402
    check_library,
    _resolve_discovery_policy,
    ORIGINAL_39_SKILL_DESCRIPTIONS,
    FROZEN_SVG_SKILL_DESCRIPTION,
    FROZEN_PLAYWRIGHT_SKILL_DESCRIPTION,
    FROZEN_WEB_ACCESSIBILITY_SKILL_DESCRIPTION,
    DISCOVERY_POLICY_VERSION_V010,
    DISCOVERY_POLICY_VERSION_V010_BROWSER_UI,
    DISCOVERY_POLICY_VERSION_V010_TOOLCHAIN,
    V010_BROWSER_UI_ADMITTED_CANDIDATES,
    V010_TOOLCHAIN_ADMITTED_CANDIDATES,
    REQUIRED_H2S,
    FROZEN_VITE_SKILL_DESCRIPTION,
    FROZEN_NPM_SKILL_DESCRIPTION,
    DISCOVERY_POLICY_VERSION_V010_BROWSER_RUNTIME,
    V010_BROWSER_RUNTIME_ADMITTED_CANDIDATES,
)


def _build_skill_md(name: str, description: str, body_extra: str = "") -> str:
    sections = "".join(f"\n## {heading}\nEvidence for {heading.lower()}.\n" for heading in REQUIRED_H2S)
    return (
        f"---\nname: {name}\ndescription: {description}\n---\n"
        f"# {name}\n"
        f"{body_extra}"
        f"{sections}"
    )


def _build_synthetic_42_library(
    root: Path,
    policy: str = DISCOVERY_POLICY_VERSION_V010_BROWSER_UI,
    extra_svg_body: str = "",
    extra_playwright_body: str = "",
    playwright_desc: str | None = None,
    web_a11y_desc: str | None = None,
    svg_desc: str | None = None,
    candidate_names: tuple[str, ...] = V010_BROWSER_UI_ADMITTED_CANDIDATES,
    omit_skills: tuple[str, ...] = (),
) -> None:
    skills_dir = root / "skills"
    chatgpt_dir = skills_dir / "chatgpt"
    chatgpt_dir.mkdir(parents=True, exist_ok=True)
    testing_dir = root / "testing"
    testing_dir.mkdir(parents=True, exist_ok=True)

    (testing_dir / "apg-discovery-policy.json").write_text(
        json.dumps({"schema_version": 1, "policy": policy}),
        encoding="utf-8",
    )
    (skills_dir / "discovery_policy.go").write_text("package skills\n", encoding="utf-8")

    all_skills: dict[str, tuple[str, str]] = {}
    for name, desc in ORIGINAL_39_SKILL_DESCRIPTIONS.items():
        if name not in omit_skills:
            all_skills[name] = (desc, "")

    if "svg-language-profile" in candidate_names and "svg-language-profile" not in omit_skills:
        all_skills["svg-language-profile"] = (
            svg_desc if svg_desc is not None else FROZEN_SVG_SKILL_DESCRIPTION,
            extra_svg_body,
        )
    if "playwright-test-profile" in candidate_names and "playwright-test-profile" not in omit_skills:
        all_skills["playwright-test-profile"] = (
            playwright_desc
            if playwright_desc is not None
            else "Use when Playwright browser tests, locators, tracing, and fixtures are evaluated.",
            extra_playwright_body,
        )
    if "web-accessibility-profile" in candidate_names and "web-accessibility-profile" not in omit_skills:
        all_skills["web-accessibility-profile"] = (
            web_a11y_desc
            if web_a11y_desc is not None
            else "Use when web accessibility checks, ARIA semantics, landmarks, and WCAG are evaluated.",
            "",
        )
    for cname in candidate_names:
        if cname not in all_skills and cname not in omit_skills:
            all_skills[cname] = (f"Use when {cname} applies to repository automation.", "")

    for name, (desc, body_extra) in all_skills.items():
        is_chatgpt = name in {"chatgpt-manager-workflow", "composing-approved-roadmap-assignments"}
        parent = chatgpt_dir if is_chatgpt else skills_dir
        leaf = parent / name
        leaf.mkdir(parents=True, exist_ok=True)
        (leaf / "SKILL.md").write_text(
            _build_skill_md(name, desc, body_extra),
            encoding="utf-8",
        )


def _build_synthetic_44_library(
    root: Path,
    policy: str = DISCOVERY_POLICY_VERSION_V010_TOOLCHAIN,
    extra_svg_body: str = "",
    extra_vite_body: str = "",
    extra_npm_body: str = "",
    playwright_desc: str | None = None,
    web_a11y_desc: str | None = None,
    svg_desc: str | None = None,
    vite_desc: str | None = None,
    npm_desc: str | None = None,
    candidate_names: tuple[str, ...] = V010_TOOLCHAIN_ADMITTED_CANDIDATES,
    omit_skills: tuple[str, ...] = (),
) -> None:
    skills_dir = root / "skills"
    chatgpt_dir = skills_dir / "chatgpt"
    chatgpt_dir.mkdir(parents=True, exist_ok=True)
    testing_dir = root / "testing"
    testing_dir.mkdir(parents=True, exist_ok=True)

    (testing_dir / "apg-discovery-policy.json").write_text(
        json.dumps({"schema_version": 1, "policy": policy}),
        encoding="utf-8",
    )
    (skills_dir / "discovery_policy.go").write_text("package skills\n", encoding="utf-8")

    all_skills: dict[str, tuple[str, str]] = {}
    for name, desc in ORIGINAL_39_SKILL_DESCRIPTIONS.items():
        if name not in omit_skills:
            all_skills[name] = (desc, "")

    if "svg-language-profile" in candidate_names and "svg-language-profile" not in omit_skills:
        all_skills["svg-language-profile"] = (
            svg_desc if svg_desc is not None else FROZEN_SVG_SKILL_DESCRIPTION,
            extra_svg_body,
        )
    if "playwright-test-profile" in candidate_names and "playwright-test-profile" not in omit_skills:
        all_skills["playwright-test-profile"] = (
            playwright_desc if playwright_desc is not None else FROZEN_PLAYWRIGHT_SKILL_DESCRIPTION,
            "",
        )
    if "web-accessibility-profile" in candidate_names and "web-accessibility-profile" not in omit_skills:
        all_skills["web-accessibility-profile"] = (
            web_a11y_desc if web_a11y_desc is not None else FROZEN_WEB_ACCESSIBILITY_SKILL_DESCRIPTION,
            "",
        )
    if "vite-build-profile" in candidate_names and "vite-build-profile" not in omit_skills:
        all_skills["vite-build-profile"] = (
            vite_desc
            if vite_desc is not None
            else "Use when Vite build configuration, bundling, plugins, dev server, or asset processing are evaluated.",
            extra_vite_body,
        )
    if "npm-package-manager-profile" in candidate_names and "npm-package-manager-profile" not in omit_skills:
        all_skills["npm-package-manager-profile"] = (
            npm_desc
            if npm_desc is not None
            else "Use when npm package management, dependencies, workspaces, scripts, or publishing workflows are evaluated.",
            extra_npm_body,
        )
    for cname in candidate_names:
        if cname not in all_skills and cname not in omit_skills:
            all_skills[cname] = (f"Use when {cname} applies to repository automation.", "")

    for name, (desc, body_extra) in all_skills.items():
        is_chatgpt = name in {"chatgpt-manager-workflow", "composing-approved-roadmap-assignments"}
        parent = chatgpt_dir if is_chatgpt else skills_dir
        leaf = parent / name
        leaf.mkdir(parents=True, exist_ok=True)
        (leaf / "SKILL.md").write_text(
            _build_skill_md(name, desc, body_extra),
            encoding="utf-8",
        )


class DiscoveryPolicyResolutionIntegrationTests(unittest.TestCase):
    def test_resolve_policy_with_current_selector(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "testing").mkdir()
            (root / "testing" / "apg-discovery-policy.json").write_text(
                json.dumps({"schema_version": 1, "policy": DISCOVERY_POLICY_VERSION_V010_TOOLCHAIN}),
                encoding="utf-8",
            )
            policy, err = _resolve_discovery_policy(root)
            self.assertIsNone(err)
            self.assertEqual(policy, DISCOVERY_POLICY_VERSION_V010_TOOLCHAIN)

    def test_resolve_policy_missing_selector_when_go_owner_present(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "skills").mkdir()
            (root / "skills" / "discovery_policy.go").write_text("package skills\n", encoding="utf-8")
            policy, err = _resolve_discovery_policy(root)
            self.assertIsNone(policy)
            self.assertIn("missing", err or "")

    def test_resolve_policy_malformed_selectors(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            selector = root / "testing" / "apg-discovery-policy.json"
            selector.parent.mkdir()

            cases = (
                ("{broken", "malformed"),
                ("[]", "duplicate, missing or unknown"),
                ('{"schema_version": 2, "policy": "v0.10-toolchain"}', "unknown policy selector schema"),
                ('{"schema_version": 1, "policy": ""}', "requires a policy string"),
                ('{"schema_version": 1, "policy": null}', "requires a policy string"),
                ('{"schema_version": 1, "policy": "v0.10-toolchain", "extra": 1}', "duplicate, missing or unknown"),
            )
            for content, err_fragment in cases:
                with self.subTest(content=content):
                    selector.write_text(content, encoding="utf-8")
                    policy, err = _resolve_discovery_policy(root)
                    self.assertIsNone(policy)
                    self.assertIsNotNone(err)
                    self.assertIn(err_fragment, err or "")

    def test_resolve_policy_symlink_selector(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "target.json"
            target.write_text(
                json.dumps({"schema_version": 1, "policy": DISCOVERY_POLICY_VERSION_V010_TOOLCHAIN}),
                encoding="utf-8",
            )
            sel = root / "testing" / "apg-discovery-policy.json"
            sel.parent.mkdir()
            sel.symlink_to(target)
            policy, err = _resolve_discovery_policy(root)
            self.assertIsNone(policy)
            self.assertIn("regular file", err or "")

    def test_resolve_policy_explicit_override_and_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "testing").mkdir()
            (root / "testing" / "apg-discovery-policy.json").write_text(
                json.dumps({"schema_version": 1, "policy": DISCOVERY_POLICY_VERSION_V010_TOOLCHAIN}),
                encoding="utf-8",
            )
            # Matching explicit selection succeeds
            policy, err = _resolve_discovery_policy(root, explicit_policy=DISCOVERY_POLICY_VERSION_V010_TOOLCHAIN)
            self.assertIsNone(err)
            self.assertEqual(policy, DISCOVERY_POLICY_VERSION_V010_TOOLCHAIN)

            # Conflicting explicit selection fails
            policy, err = _resolve_discovery_policy(root, explicit_policy=DISCOVERY_POLICY_VERSION_V010)
            self.assertIsNone(policy)
            self.assertIn("conflicts with selector", err or "")

    def test_check_library_fail_closed_on_policy_errors(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "skills").mkdir()
            (root / "skills" / "discovery_policy.go").write_text("package skills\n", encoding="utf-8")
            res = check_library(root, policy="v99.99")
            codes = {d.code for d in res.diagnostics}
            self.assertIn("APG048", codes)


class SyntheticLibraryBrowserUIPolicyIntegrationTests(unittest.TestCase):
    def test_valid_42_skill_library_passes_policy_checks(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _build_synthetic_42_library(root)
            res = check_library(root)
            policy_diagnostics = [
                d for d in res.diagnostics
                if d.code in {"APG042", "APG043", "APG044", "APG045", "APG046", "APG047", "APG048"}
            ]
            self.assertEqual(
                policy_diagnostics,
                [],
                f"expected no policy diagnostics on valid 42 library, got: {policy_diagnostics}",
            )

    def test_candidate_description_over_330_bytes_emits_apg042(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            desc331 = "Use when Playwright applies " + ("x" * (331 - len("Use when Playwright applies ")))
            self.assertEqual(len(desc331.encode("utf-8")), 331)
            _build_synthetic_42_library(root, playwright_desc=desc331)
            res = check_library(root)
            codes = {d.code for d in res.diagnostics}
            self.assertIn("APG042", codes)

    def test_svg_file_size_over_20480_emits_apg043(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            padding = "<!-- " + ("p" * 21000) + " -->\n"
            _build_synthetic_42_library(root, extra_svg_body=padding)
            res = check_library(root)
            codes = {d.code for d in res.diagnostics}
            self.assertIn("APG043", codes)

    def test_non_svg_candidate_file_size_over_20480_exempt_from_apg043(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            padding = "<!-- " + ("p" * 25000) + " -->\n"
            _build_synthetic_42_library(root, extra_playwright_body=padding)
            res = check_library(root)
            svg_file_errors = [d for d in res.diagnostics if d.code == "APG043"]
            self.assertEqual(
                svg_file_errors,
                [],
                "non-SVG candidate (playwright-test-profile) must be exempt from APG043 file size limit",
            )

    def test_original_39_description_mutation_emits_apg044(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _build_synthetic_42_library(root)
            # Mutate one original skill
            skill_file = root / "skills" / "agentic-praxis-grimoire-workflow" / "SKILL.md"
            skill_file.write_text(
                _build_skill_md(
                    "agentic-praxis-grimoire-workflow",
                    "Use when APG routing is needed.",
                ),
                encoding="utf-8",
            )
            res = check_library(root)
            codes = {d.code for d in res.diagnostics}
            self.assertIn("APG044", codes)

    def test_svg_description_mutation_emits_apg044(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _build_synthetic_42_library(root, svg_desc="Use when SVG authoring is needed.")
            res = check_library(root)
            codes = {d.code for d in res.diagnostics}
            self.assertIn("APG044", codes)

    def test_count_mismatch_41_skills_emits_apg045(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _build_synthetic_42_library(root, omit_skills=("web-accessibility-profile",))
            res = check_library(root)
            codes = {d.code for d in res.diagnostics}
            self.assertIn("APG045", codes)

    def test_count_mismatch_40_skills_emits_apg045(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _build_synthetic_42_library(
                root,
                omit_skills=("playwright-test-profile", "web-accessibility-profile"),
            )
            res = check_library(root)
            codes = {d.code for d in res.diagnostics}
            self.assertIn("APG045", codes)

    def test_unauthorized_candidate_admission_emits_apg046(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _build_synthetic_42_library(
                root,
                candidate_names=(
                    "svg-language-profile",
                    "playwright-test-profile",
                    "browser-runtime-profile",  # unauthorized replacement for web-accessibility-profile
                ),
            )
            res = check_library(root)
            codes = {d.code for d in res.diagnostics}
            self.assertIn("APG046", codes)

    def test_missing_original_39_emits_apg047(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _build_synthetic_42_library(
                root,
                omit_skills=("bash-language-profile",),
                candidate_names=(
                    "svg-language-profile",
                    "playwright-test-profile",
                    "web-accessibility-profile",
                    "extra-candidate-profile",  # keep total at 42 to specifically isolate APG047
                ),
            )
            res = check_library(root)
            codes = {d.code for d in res.diagnostics}
            self.assertIn("APG047", codes)


class SyntheticLibraryToolchainPolicyIntegrationTests(unittest.TestCase):
    def test_valid_44_skill_library_passes_policy_checks(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _build_synthetic_44_library(root)
            res = check_library(root)
            policy_diagnostics = [
                d for d in res.diagnostics
                if d.code in {"APG042", "APG043", "APG044", "APG045", "APG046", "APG047", "APG048"}
            ]
            self.assertEqual(
                policy_diagnostics,
                [],
                f"expected no policy diagnostics on valid 44 library, got: {policy_diagnostics}",
            )

    def test_candidate_description_over_330_bytes_emits_apg042(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            desc331 = "Use when Vite applies " + ("x" * (331 - len("Use when Vite applies ")))
            self.assertEqual(len(desc331.encode("utf-8")), 331)
            _build_synthetic_44_library(root, vite_desc=desc331)
            res = check_library(root)
            codes = {d.code for d in res.diagnostics}
            self.assertIn("APG042", codes)

    def test_svg_file_size_over_20480_emits_apg043(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            padding = "<!-- " + ("p" * 21000) + " -->\n"
            _build_synthetic_44_library(root, extra_svg_body=padding)
            res = check_library(root)
            codes = {d.code for d in res.diagnostics}
            self.assertIn("APG043", codes)

    def test_non_svg_candidate_file_size_over_20480_exempt_from_apg043(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            padding = "<!-- " + ("p" * 25000) + " -->\n"
            _build_synthetic_44_library(root, extra_vite_body=padding)
            res = check_library(root)
            svg_file_errors = [d for d in res.diagnostics if d.code == "APG043"]
            self.assertEqual(
                svg_file_errors,
                [],
                "non-SVG candidate (vite-build-profile) must be exempt from APG043 file size limit",
            )

    def test_original_39_description_mutation_emits_apg044(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _build_synthetic_44_library(root)
            skill_file = root / "skills" / "agentic-praxis-grimoire-workflow" / "SKILL.md"
            skill_file.write_text(
                _build_skill_md(
                    "agentic-praxis-grimoire-workflow",
                    "Use when APG routing is needed.",
                ),
                encoding="utf-8",
            )
            res = check_library(root)
            codes = {d.code for d in res.diagnostics}
            self.assertIn("APG044", codes)

    def test_svg_description_mutation_emits_apg044(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _build_synthetic_44_library(root, svg_desc="Use when SVG authoring is needed.")
            res = check_library(root)
            codes = {d.code for d in res.diagnostics}
            self.assertIn("APG044", codes)

    def test_playwright_description_mutation_emits_apg044(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _build_synthetic_44_library(root, playwright_desc="Use when Playwright applies.")
            res = check_library(root)
            codes = {d.code for d in res.diagnostics}
            self.assertIn("APG044", codes)

    def test_web_accessibility_description_mutation_emits_apg044(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _build_synthetic_44_library(root, web_a11y_desc="Use when accessibility applies.")
            res = check_library(root)
            codes = {d.code for d in res.diagnostics}
            self.assertIn("APG044", codes)

    def test_count_mismatch_43_skills_emits_apg045(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _build_synthetic_44_library(root, omit_skills=("npm-package-manager-profile",))
            res = check_library(root)
            codes = {d.code for d in res.diagnostics}
            self.assertIn("APG045", codes)

    def test_count_mismatch_42_skills_emits_apg045(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _build_synthetic_44_library(
                root,
                omit_skills=("vite-build-profile", "npm-package-manager-profile"),
            )
            res = check_library(root)
            codes = {d.code for d in res.diagnostics}
            self.assertIn("APG045", codes)

    def test_unauthorized_candidate_admission_emits_apg046(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _build_synthetic_44_library(
                root,
                candidate_names=(
                    "svg-language-profile",
                    "playwright-test-profile",
                    "web-accessibility-profile",
                    "vite-build-profile",
                    "browser-runtime-profile",
                ),
            )
            res = check_library(root)
            codes = {d.code for d in res.diagnostics}
            self.assertIn("APG046", codes)

    def test_missing_original_39_emits_apg047(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _build_synthetic_44_library(
                root,
                omit_skills=("bash-language-profile",),
                candidate_names=(
                    "svg-language-profile",
                    "playwright-test-profile",
                    "web-accessibility-profile",
                    "vite-build-profile",
                    "npm-package-manager-profile",
                    "extra-candidate-profile",
                ),
            )
            res = check_library(root)
            codes = {d.code for d in res.diagnostics}
            self.assertIn("APG047", codes)


class HistoricalPolicyV010IntegrationTests(unittest.TestCase):
    def test_v010_historical_policy_accepts_39_and_40(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # 40 skills under v0.10 with SVG
            _build_synthetic_42_library(
                root,
                policy=DISCOVERY_POLICY_VERSION_V010,
                candidate_names=("svg-language-profile",),
            )
            res40 = check_library(root, policy=DISCOVERY_POLICY_VERSION_V010)
            policy_codes_40 = {
                d.code for d in res40.diagnostics
                if d.code in {"APG042", "APG043", "APG044", "APG045", "APG046", "APG047", "APG048"}
            }
            self.assertEqual(policy_codes_40, set())

    def test_v010_historical_rejects_playwright_at_40(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _build_synthetic_42_library(
                root,
                policy=DISCOVERY_POLICY_VERSION_V010,
                candidate_names=("playwright-test-profile",),
            )
            res = check_library(root, policy=DISCOVERY_POLICY_VERSION_V010)
            codes = {d.code for d in res.diagnostics}
            self.assertIn("APG046", codes)


class LiveCorpusExpectedStatusIntegrationTests(unittest.TestCase):
    def test_live_selector_is_v010_browser_runtime(self) -> None:
        selector = REPOSITORY_ROOT / "testing" / "apg-discovery-policy.json"
        self.assertTrue(selector.is_file())
        self.assertFalse(selector.is_symlink())
        data = json.loads(selector.read_text(encoding="utf-8"))
        self.assertEqual(data, {"schema_version": 1, "policy": DISCOVERY_POLICY_VERSION_V010_BROWSER_RUNTIME})

    def test_live_repository_requires_complete_current_admission(self) -> None:
        # Current admission is exact; historical smaller sets are tested separately.
        res = check_library(REPOSITORY_ROOT)
        codes = {d.code for d in res.diagnostics}
        self.assertNotIn("APG045", codes)
        self.assertEqual(list(res.diagnostics), [])


if __name__ == "__main__":
    unittest.main()



def _apg125_build_skill_md(name: str, description: str, body_extra: str = "") -> str:
    sections = "".join(f"\n## {heading}\nEvidence for {heading.lower()}.\n" for heading in REQUIRED_H2S)
    return (
        f"---\nname: {name}\ndescription: {description}\n---\n"
        f"# {name}\n"
        f"{body_extra}"
        f"{sections}"
    )


def _apg125_build_synthetic_45_library(
    root: Path,
    policy: str = DISCOVERY_POLICY_VERSION_V010_BROWSER_RUNTIME,
    extra_svg_body: str = "",
    extra_browser_runtime_body: str = "",
    browser_runtime_desc: str | None = None,
    vite_desc: str | None = None,
    npm_desc: str | None = None,
    candidate_names: tuple[str, ...] = tuple(sorted(V010_BROWSER_RUNTIME_ADMITTED_CANDIDATES)),
    omit_skills: tuple[str, ...] = (),
) -> None:
    skills_dir = root / "skills"
    chatgpt_dir = skills_dir / "chatgpt"
    chatgpt_dir.mkdir(parents=True, exist_ok=True)
    testing_dir = root / "testing"
    testing_dir.mkdir(parents=True, exist_ok=True)

    (testing_dir / "apg-discovery-policy.json").write_text(
        json.dumps({"schema_version": 1, "policy": policy}),
        encoding="utf-8",
    )
    (skills_dir / "discovery_policy.go").write_text("package skills\n", encoding="utf-8")

    all_skills: dict[str, tuple[str, str]] = {}
    for name, desc in ORIGINAL_39_SKILL_DESCRIPTIONS.items():
        if name not in omit_skills:
            all_skills[name] = (desc, "")

    if "svg-language-profile" in candidate_names and "svg-language-profile" not in omit_skills:
        all_skills["svg-language-profile"] = (FROZEN_SVG_SKILL_DESCRIPTION, extra_svg_body)
    if "playwright-test-profile" in candidate_names and "playwright-test-profile" not in omit_skills:
        all_skills["playwright-test-profile"] = (FROZEN_PLAYWRIGHT_SKILL_DESCRIPTION, "")
    if "web-accessibility-profile" in candidate_names and "web-accessibility-profile" not in omit_skills:
        all_skills["web-accessibility-profile"] = (FROZEN_WEB_ACCESSIBILITY_SKILL_DESCRIPTION, "")
    if "vite-build-profile" in candidate_names and "vite-build-profile" not in omit_skills:
        all_skills["vite-build-profile"] = (
            vite_desc if vite_desc is not None else FROZEN_VITE_SKILL_DESCRIPTION,
            "",
        )
    if "npm-package-manager-profile" in candidate_names and "npm-package-manager-profile" not in omit_skills:
        all_skills["npm-package-manager-profile"] = (
            npm_desc if npm_desc is not None else FROZEN_NPM_SKILL_DESCRIPTION,
            "",
        )
    if "browser-runtime-profile" in candidate_names and "browser-runtime-profile" not in omit_skills:
        all_skills["browser-runtime-profile"] = (
            browser_runtime_desc
            if browser_runtime_desc is not None
            else "Use when web decisions depend on browser host behavior — Window, Document, DOM mutation, event phases, tasks, microtasks, timers, rAF, MutationObserver, URL, History, Fetch, CORS, cookies, WebStorage, IndexedDB, custom elements, Shadow DOM, geometry, workers, or object URLs — for an established browser execution role.",
            extra_browser_runtime_body,
        )

    for cname in candidate_names:
        if cname not in all_skills and cname not in omit_skills:
            all_skills[cname] = (f"Use when {cname} applies to repository automation.", "")

    for name, (desc, body_extra) in all_skills.items():
        is_chatgpt = name in {"chatgpt-manager-workflow", "composing-approved-roadmap-assignments"}
        parent = chatgpt_dir if is_chatgpt else skills_dir
        leaf = parent / name
        leaf.mkdir(parents=True, exist_ok=True)
        (leaf / "SKILL.md").write_text(_apg125_build_skill_md(name, desc, body_extra), encoding="utf-8")

    catalog_rows = "\n".join(
        f"| [`{name}`]({'chatgpt/' if name in {'chatgpt-manager-workflow', 'composing-approved-roadmap-assignments'} else ''}{name}/SKILL.md) | {desc[:40]} | `provisional` |"
        for name, (desc, _) in sorted(all_skills.items())
    )
    (skills_dir / "README.md").write_text(
        f"# Skills Catalog\n\n| Skill | Trigger | Maturity |\n| --- | --- | --- |\n{catalog_rows}\n",
        encoding="utf-8",
    )

    agents_dir = root / ".agents" / "skills"
    agents_dir.mkdir(parents=True, exist_ok=True)
    for name in all_skills:
        is_chatgpt = name in {"chatgpt-manager-workflow", "composing-approved-roadmap-assignments"}
        target = Path("../../skills/chatgpt" if is_chatgpt else "../../skills") / name
        link = agents_dir / name
        if not link.exists():
            link.symlink_to(target, target_is_directory=True)


class SyntheticV010BrowserRuntimeIntegrationTests(unittest.TestCase):
    def test_prior_browser_ui_descriptions_remain_frozen_after_runtime_admission(self) -> None:
        for name in ("svg-language-profile", "playwright-test-profile", "web-accessibility-profile"):
            with self.subTest(skill=name), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                _apg125_build_synthetic_45_library(root)
                leaf = root / "skills" / name / "SKILL.md"
                original = leaf.read_text(encoding="utf-8")
                leaf.write_text(
                    _apg125_build_skill_md(name, "Use when a different trigger applies."),
                    encoding="utf-8",
                )
                result = check_library(root)
                self.assertTrue(any(d.code == "APG044" and name in d.path for d in result.diagnostics))
                leaf.write_text(original, encoding="utf-8")
                self.assertFalse(any(d.code == "APG044" for d in check_library(root).diagnostics))

    def test_aggregate_description_inflation_is_reported_with_freeze_violation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _apg125_build_synthetic_45_library(root)
            leaf = root / "skills" / "bash-language-profile" / "SKILL.md"
            original = leaf.read_text(encoding="utf-8")
            # Aggregate overflow necessarily violates a frozen description as well:
            # the sole unfrozen candidate cannot exceed its 330-byte reservation.
            leaf.write_text(
                _apg125_build_skill_md("bash-language-profile", "Use when " + "x" * 12000),
                encoding="utf-8",
            )
            codes = {d.code for d in check_library(root).diagnostics}
            self.assertTrue({"APG044", "APG048", "APG040"}.issubset(codes))
            leaf.write_text(original, encoding="utf-8")
            self.assertFalse({"APG044", "APG048", "APG040"} & {d.code for d in check_library(root).diagnostics})

    def test_complete_synthetic_45_library_passes_policy_checks(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _apg125_build_synthetic_45_library(root)
            res = check_library(root)
            policy_diagnostics = [
                d for d in res.diagnostics
                if d.code in {"APG042", "APG043", "APG044", "APG045", "APG046", "APG047", "APG048"}
            ]
            self.assertEqual(policy_diagnostics, [])

    def test_browser_runtime_description_reservation_ceiling_apg042(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            over_desc = "Use when browser runtime applies " + ("x" * (331 - len("Use when browser runtime applies ")))
            _apg125_build_synthetic_45_library(root, browser_runtime_desc=over_desc)
            res = check_library(root)
            codes = {d.code for d in res.diagnostics}
            self.assertIn("APG042", codes)

    def test_svg_file_size_limit_apg043(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            extra_padding = "<!-- " + ("p" * 21000) + " -->\n"
            _apg125_build_synthetic_45_library(root, extra_svg_body=extra_padding)
            res = check_library(root)
            codes = {d.code for d in res.diagnostics}
            self.assertIn("APG043", codes)

    def test_browser_runtime_large_body_exempt_from_svg_limit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            extra_padding = "<!-- " + ("p" * 35000) + " -->\n"
            _apg125_build_synthetic_45_library(root, extra_browser_runtime_body=extra_padding)
            res = check_library(root)
            svg_file_diagnostics = [
                d for d in res.diagnostics
                if d.code == "APG043" and "browser-runtime" in d.location
            ]
            self.assertEqual(svg_file_diagnostics, [])

    def test_vite_freeze_theft_emits_apg044(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _apg125_build_synthetic_45_library(
                root,
                vite_desc="Use when Vite dev serving or building is evaluated.",
            )
            res = check_library(root)
            codes = {d.code for d in res.diagnostics}
            self.assertIn("APG044", codes)

    def test_npm_freeze_theft_emits_apg044(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _apg125_build_synthetic_45_library(
                root,
                npm_desc="Use when npm CLI commands are evaluated.",
            )
            res = check_library(root)
            codes = {d.code for d in res.diagnostics}
            self.assertIn("APG044", codes)

    def test_count_mismatch_44_emits_apg045(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            # 44 leaves under browser runtime policy
            _apg125_build_synthetic_45_library(
                root,
                omit_skills=("browser-runtime-profile",),
            )
            res = check_library(root)
            codes = {d.code for d in res.diagnostics}
            self.assertIn("APG045", codes)

    def test_unauthorized_candidate_emits_apg046(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _apg125_build_synthetic_45_library(
                root,
                candidate_names=(
                    "svg-language-profile",
                    "playwright-test-profile",
                    "web-accessibility-profile",
                    "vite-build-profile",
                    "npm-package-manager-profile",
                    "unauthorized-runtime-profile",
                ),
            )
            res = check_library(root)
            codes = {d.code for d in res.diagnostics}
            self.assertIn("APG046", codes)

    def test_missing_original_39_emits_apg047(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _apg125_build_synthetic_45_library(
                root,
                omit_skills=("bash-language-profile",),
                candidate_names=(
                    "svg-language-profile",
                    "playwright-test-profile",
                    "web-accessibility-profile",
                    "vite-build-profile",
                    "npm-package-manager-profile",
                    "browser-runtime-profile",
                    "extra-candidate-profile",
                ),
            )
            res = check_library(root)
            codes = {d.code for d in res.diagnostics}
            self.assertIn("APG047", codes)
