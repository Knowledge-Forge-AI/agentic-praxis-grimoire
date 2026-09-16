"""Read-only mechanical validation for the APG skill library."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from functools import partial
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Sequence

import apg_skill_topology


COMMAND_NAME = "apg-check-skill-library"
CURRENT_CATALOG_HEADING = "## Current development catalog"
LEGACY_CATALOG_HEADING = "## APG v0.1 catalog"
CATALOG_HEADINGS = frozenset(
    {CURRENT_CATALOG_HEADING, LEGACY_CATALOG_HEADING}
)
CATALOG_HEADER = "| Skill | Trigger boundary | Maturity |"
CATALOG_SEPARATOR = "| --- | --- | --- |"
MATURITY_VALUES = frozenset(
    {"bootstrap", "provisional", "evaluated", "stable", "deprecated"}
)
REQUIRED_H2S = (
    "Core principle",
    "Do not use",
    "Procedure",
    "Project-owned parameters",
    "Evidence and completion",
    "Stop or escalate",
    "Common mistakes",
)
SUPPORT_DIRECTORIES = frozenset({"scripts", "references", "assets", "agents"})
V06_PROFILE_NAMES = frozenset(
    {
        "astro-profile",
        "gomock-test-profile",
        "jsx-language-profile",
        "mdx-profile",
        "react-component-profile",
        "vitest-test-profile",
    }
)
V06_DESCRIPTION_BYTES_MINIMUM = 170
V06_DESCRIPTION_BYTES_MAXIMUM = 330
V06_TOTAL_DESCRIPTION_BYTES_MAXIMUM = 9527

DISCOVERY_POLICY_VERSION_V010 = "v0.10"
DISCOVERY_POLICY_VERSION_V010_BROWSER_UI = "v0.10-browser-ui"
DISCOVERY_POLICY_VERSION_V010_TOOLCHAIN = "v0.10-toolchain"
DISCOVERY_POLICY_VERSION_V010_BROWSER_RUNTIME = "v0.10-browser-runtime"
DISCOVERY_POLICY_VERSION = DISCOVERY_POLICY_VERSION_V010_BROWSER_RUNTIME
HISTORICAL_SKILL_COUNT = 39
HISTORICAL_DESCRIPTION_BYTES = 9504
HISTORICAL_DESCRIPTION_CHARACTERS = 9492
HISTORICAL_GLOBAL_DESCRIPTION_LIMIT = 9527

V010_MAX_RESERVATION_DESCRIPTION_BYTES = 330
V010_CURRENT_SVG_ADMISSION_CEILING = 9857
V010_BROWSER_UI_ADMISSION_CEILING = 10517
V010_CURRENT_BROWSER_UI_ADMISSION_CEILING = 10517
V010_TOOLCHAIN_ADMISSION_CEILING = 11177
V010_CURRENT_TOOLCHAIN_ADMISSION_CEILING = 11177
V010_BROWSER_RUNTIME_ADMISSION_CEILING = 11507
V010_CURRENT_BROWSER_RUNTIME_ADMISSION_CEILING = 11507
V010_OVERALL_FUTURE_CEILING = 11507
V010_MAX_SVG_FILE_BYTES = 20480
V010_CURRENT_ADMITTED_CANDIDATE = "svg-language-profile"
V010_ADMITTED_SKILL_COUNT = 40
V010_BROWSER_UI_ADMITTED_SKILL_COUNT = 42
V010_TOOLCHAIN_ADMITTED_SKILL_COUNT = 44
V010_BROWSER_RUNTIME_ADMITTED_SKILL_COUNT = 45
V010_ELIGIBLE_CANDIDATES = frozenset(
    {
        "svg-language-profile",
        "playwright-test-profile",
        "web-accessibility-profile",
        "browser-runtime-profile",
        "npm-package-manager-profile",
        "vite-build-profile",
    }
)
V010_BROWSER_UI_ADMITTED_CANDIDATES = frozenset(
    {
        "svg-language-profile",
        "playwright-test-profile",
        "web-accessibility-profile",
    }
)
V010_TOOLCHAIN_ADMITTED_CANDIDATES = frozenset(
    {
        "svg-language-profile",
        "playwright-test-profile",
        "web-accessibility-profile",
        "vite-build-profile",
        "npm-package-manager-profile",
    }
)
V010_BROWSER_RUNTIME_ADMITTED_CANDIDATES = frozenset(
    {
        "svg-language-profile",
        "playwright-test-profile",
        "web-accessibility-profile",
        "vite-build-profile",
        "npm-package-manager-profile",
        "browser-runtime-profile",
    }
)

FROZEN_SVG_SKILL_DESCRIPTION = (
    "Use when SVG authoring depends on namespaces, viewBox, paths, transforms, "
    "paint, reuse, clipping, masking, text, naming, resources, or serialization; "
    "not for general CSS, JSX, React, browser runtime, accessibility audits, or "
    "test automation."
)
FROZEN_PLAYWRIGHT_SKILL_DESCRIPTION = (
    "Use when a project selects Playwright Test and decisions depend on "
    "configuration, fixtures, locators, waiting, isolation, parallel execution, "
    "browser projects, network controls, or test artifacts; not for accessibility "
    "standards or general browser/runtime semantics."
)
FROZEN_WEB_ACCESSIBILITY_SKILL_DESCRIPTION = (
    "Use when web implementation decisions affect native semantics, accessible "
    "names, keyboard and focus behavior, images/SVG, forms, dynamic content, "
    "motion, contrast, or accessibility evidence; not for test-runner mechanics "
    "or a claim of automated WCAG conformance."
)
FROZEN_VITE_SKILL_DESCRIPTION = (
    "Use when a project selects Vite for dev serving or production building and decisions "
    "depend on root, base, publicDir, mode, env prefixes, loopback fs limits, Rolldown bundling, "
    "alias/CSS/plugin hooks, SSR seams, or preview."
)
FROZEN_NPM_SKILL_DESCRIPTION = (
    "Use when package management decisions depend on npm CLI contracts, package.json and "
    "lockfile v3 integrity, install versus ci execution, peer dependencies and overrides, "
    "workspaces, script lifecycle and ignore-scripts, local pack tarballs, caching, or "
    "publication provenance; not for Node host runtime or bundler transforms."
)

# Documented update requirement:
# The original 39 skill identities and their exact descriptions are frozen under
# Discovery Policy v0.10. Modifying, renaming, removing, or changing descriptions
# of the original 39 skills constitutes reservation theft and requires formal APG
# governance authorization and an approved specification change.
FROZEN_ORIGINAL_39_DIGEST = (
    "f9255d38eadff7b2bfc5ab13cd1722b8d98ac1ea974d8220475ff7067a1e8cc7"
)

ORIGINAL_39_SKILL_DESCRIPTIONS: dict[str, str] = {
    "agentic-praxis-grimoire-workflow": (
        "Use when an operator or manager needs to choose among multiple plausible "
        "APG skills, audit an APG routing decision, or diagnose a missing or stale APG capability."
    ),
    "astro-profile": (
        "Use when Astro behavior hinges on .astro execution, islands/client "
        "directives, server/client boundaries, collections, routing, or "
        "integrations; not for React, JSX, MDX, TypeScript, Node, Vite, "
        "Starlight, CSS, accessibility, or deployment."
    ),
    "bash-language-profile": (
        "Use when Bash-specific judgment is material to quoting, expansion, "
        "arrays, pipelines, traps, subprocesses, files, portability, or warning "
        "and crisis thresholds beyond repository policy."
    ),
    "bats-test-profile": (
        "Use when Bats-specific test judgment is material to evaluation, run "
        "status and output, hooks, fixtures, TAP, file descriptors, parallelism, "
        "background cleanup, or warning and crisis thresholds beyond repository policy."
    ),
    "chatgpt-manager-workflow": (
        "Use when selection among multiple plausible ChatGPT top-level-manager "
        "capabilities is ambiguous or a ChatGPT-manager routing decision requires audit."
    ),
    "composing-approved-roadmap-assignments": (
        "Use when a human-approved roadmap phase or explicitly approved bounded "
        "phase sequence must become a reviewable top-level coding-agent manager "
        "assignment with authority, scope, evidence, acceptance, stop, "
        "reporting, and handoff boundaries."
    ),
    "composing-bounded-worker-assignments": (
        "Use when internal delegation is already authorized and independently "
        "selected, and one non-trivial worker assignment needs explicit scope, "
        "ownership, evidence, acceptance, or return boundaries."
    ),
    "converting-bash-scripts-to-python": (
        "Use when an existing Bash executable or script family needs a bounded "
        "conversion to Python that preserves or deliberately migrates its observable contract."
    ),
    "css-language-profile": (
        "Use when a material decision depends on CSS-specific static semantics "
        "\u2014 syntax validity, selector specificity, cascade ordering, "
        "inheritance, shorthand resets, custom-property substitution, or "
        "value consequences \u2014 for an established CSS region whose artifact "
        "boundary and consequence-bearing evidence are identified."
    ),
    "debugging-systematically": (
        "Use when behavior is failing, inconsistent, flaky, unexplained, or "
        "affected by multiple plausible causes."
    ),
    "designing-significant-changes": (
        "Use when consequential behavior, architecture, ownership, interfaces, "
        "data contracts, safety boundaries, or irreversible choices remain unresolved before implementation."
    ),
    "dockerfile-profile": (
        "Use when Dockerfile-specific judgment is material to parser directives, "
        "build stages, instruction forms, variable scope, build context, copies, "
        "mounts, cache behavior, file ownership, runtime metadata, platform "
        "behavior, or warning and crisis thresholds beyond repository policy."
    ),
    "go-cmp-test-profile": (
        "Use when a repository has already selected google/go-cmp v0.7.0 and "
        "comparison judgment is material to equality versus diff, option "
        "composition and filters, comparers and transformers, ignores and "
        "unexported fields, sorting, approximation, panics, diagnostic "
        "exposure, or thresholds beyond repository policy."
    ),
    "go-language-profile": (
        "Use when Go-specific judgment is material to structure, errors, "
        "context, interfaces, generics, concurrency, public APIs, reflection, "
        "unsafe, cgo, subprocesses, compatibility, or warning and crisis "
        "thresholds beyond repository policy."
    ),
    "go-test-profile": (
        "Use when native Go test judgment is material to package placement, "
        "subtests, helper attribution, cleanup and isolation, TestMain, "
        "parallelism, goroutine reporting, examples, benchmarks, fuzzing, "
        "caching, effective language version, or warning and crisis thresholds "
        "beyond repository policy."
    ),
    "gomock-test-profile": (
        "Use when a project has already selected GoMock v0.6.0 and judgment is "
        "material to mockgen generation, generated mocks, controller lifecycle, "
        "expectations, call counts or order, matchers, or GoMock failure "
        "diagnosis; not for native test lifecycle, value diffs, or Go semantics."
    ),
    "implementing-with-test-discipline": (
        "Use when implementing a bugfix, new behavior, behavioral refactor, "
        "schema or contract change, or another code change whose correctness "
        "benefits from executable evidence."
    ),
    "javascript-language-profile": (
        "Use when a material decision depends on ECMAScript language semantics "
        "\u2014 evaluation order, lexical scope and temporal dead zones, coercion "
        "and equality, prototypes and property descriptors, this binding, classes, "
        "iteration, completion values, promise and async semantics, or module "
        "live bindings \u2014 for an established JavaScript source region whose "
        "parse goal, strictness state, and whole-file owner are identified."
    ),
    "jsx-language-profile": (
        "Use when JSX-specific judgment is material to element, attribute, child, "
        "expression, fragment, spread, file-kind, or transform semantics; not "
        "for React behavior, TypeScript checking, JavaScript evaluation, runtime hosts, "
        "MDX, Astro, or build tools."
    ),
    "markdown-language-profile": (
        "Use when a material decision depends on the repository's actual Markdown "
        "parser or selected-dialect document semantics, or on qualitative "
        "Markdown document-structure policy."
    ),
    "mdx-profile": (
        "Use when an MDX decision depends on the Markdown-to-JSX/component seam, "
        "imports/exports, expressions, provider mapping, or compile/runtime split; "
        "not for pure Markdown, JSX, React, TypeScript, JavaScript, or Astro."
    ),
    "minitest-test-profile": (
        "Use when Minitest-specific judgment is material to test or spec "
        "organization, assertions, lifecycle, mocks, stubs, fixture alternatives, "
        "isolation, parallelism, filtering, runners, plugins, reporters, "
        "subprocess, filesystem, or database test boundaries, or warning and "
        "crisis thresholds beyond repository policy."
    ),
    "nix-language-profile": (
        "Use when Nix-specific judgment is material to expressions, attribute sets, "
        "modules, derivations, flakes, overlays, purity, evaluation, store exposure, "
        "activation, remote builders, or warning and crisis thresholds beyond repository policy."
    ),
    "nix-test-profile": (
        "Use when Nix test judgment is material to selecting which already-selected "
        "testing surface can prove an exact claim, package check and install-check "
        "behavior, flake checks, Nixpkgs or NixOS test ownership, test-evidence "
        "qualification across sandbox, store, builder, or cache boundaries, or "
        "Nix-test-specific structural review."
    ),
    "nodejs-runtime-profile": (
        "Use when a material decision depends on Node.js-specific host behavior "
        "\u2014 package scope and module mapping, CommonJS wrapper bindings, ESM "
        "host metadata, specifier resolution and package exports, module identity, "
        "process and CLI state, stdio and exit status, filesystem and path APIs, "
        "errors, signals, timers and the event loop, child processes and workers, "
        "or Node's exposure of network and Web-compatible APIs \u2014 for an "
        "established Node execution role whose exact version, platform, flags, "
        "package scope, loader, and whole-file owner are identified."
    ),
    "planning-repository-work": (
        "Use when an accepted objective requires multiple dependent implementation "
        "steps, cross-file coordination, staged risk reduction, or a durable handoff."
    ),
    "postgresql-database-profile": (
        "Use when PostgreSQL-specific judgment is material to SQL, schemas, MVCC, "
        "transactions, locks, DDL, migrations, routines, triggers, security, "
        "backup and restore, replication, maintenance, or warning and crisis "
        "thresholds beyond repository policy."
    ),
    "pytest-test-profile": (
        "Use when pytest-specific judgment is material to discovery, collection, "
        "assertions, fixtures, parametrization, mocks, isolation, xdist, coverage, "
        "or warning and crisis thresholds beyond repository policy."
    ),
    "python-language-profile": (
        "Use when Python implementation, design, debugging, or review needs "
        "Python-specific judgment about structure, complexity, public APIs, typing, "
        "concurrency, serialization, packaging, or warning and crisis thresholds "
        "beyond repository policy."
    ),
    "react-component-profile": (
        "Use when React component judgment is material to composition, props, "
        "rendering, state, effects, hooks, context, memoization, error boundaries, "
        "or component testing; not for JSX syntax, language typing, runner mechanics, "
        "routing, styling, MDX, Astro, or metaframeworks."
    ),
    "reviewing-and-verifying-repository-work": (
        "Use when a bounded repository artifact, change, phase, commit, or worker "
        "result requires evidence-backed acceptance, correction, disposition, or "
        "a completion claim."
    ),
    "ruby-language-profile": (
        "Use when Ruby-specific judgment is material to structure, exceptions, "
        "blocks, shared state, dynamic dispatch, metaprogramming, callbacks, "
        "concurrency, gems, public compatibility, serialization, subprocesses, "
        "or warning and crisis thresholds beyond repository policy."
    ),
    "sqlite-database-profile": (
        "Use when SQLite-specific judgment is material to SQL, transaction modes, "
        "single-writer concurrency, busy handling, journal or WAL behavior, schema "
        "rebuilds, pragmas, affinity, file ownership, backup and integrity, "
        "extensions, or warning and crisis thresholds beyond repository policy."
    ),
    "synthesizing-repository-guidance": (
        "Use when a dense, duplicated, mixed-scope, private, or source-derived "
        "guidance corpus needs ownership, provenance, privacy, migration, or "
        "rejection dispositions before any rewrite."
    ),
    "typescript-language-profile": (
        "Use when a material decision depends on TypeScript-specific static "
        "semantics or type-erasure boundaries for an established source region, "
        "after the exact compiler role, version, options, project, source kind, "
        "and declaration environment are evidenced."
    ),
    "vagrantfile-profile": (
        "Use when Vagrantfile-specific judgment is material to configuration "
        "versions and loading, machines, boxes, provider blocks, networks, "
        "synced folders, provisioners, triggers, Vagrant state, host-dependent "
        "behavior, or warning and crisis thresholds beyond repository policy."
    ),
    "vitest-test-profile": (
        "Use when a project has already selected Vitest 4.1 and runner-specific "
        "judgment is material to configuration, projects, environments, assertions, "
        "mocks, timers, concurrency, isolation, snapshots, or coverage providers; "
        "not for test sufficiency, language or React semantics, or coverage policy."
    ),
    "zsh-language-profile": (
        "Use when Zsh-specific judgment is material to option state, arrays, "
        "expansion, globbing, autoloading, startup or interactive behavior, hooks, "
        "modules, processes, or warning and crisis thresholds beyond repository policy."
    ),
    "zunit-test-profile": (
        "Use when a repository explicitly uses the APG-verified ZUnit v0.8.2 and "
        "Zsh 5.9.2 pair and needs ZUnit-specific judgment about runner invocation, "
        "discovery, assertions, hooks, configuration, output, isolation, process "
        "cleanup, compatibility, or warning and crisis thresholds beyond repository policy."
    ),
}


def compute_original_39_digest(descriptions: dict[str, str]) -> str:
    """Compute the SHA-256 digest of the 39 original skill descriptions in canonical order."""
    lines = [f"{name}:{descriptions[name]}\n" for name in sorted(descriptions)]
    return hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()


def validate_discovery_policy(
    policy_version: str,
    skills: Sequence[dict[str, object]],
) -> list[str]:
    """Validate skill rows against the versioned discovery capacity policy."""
    failures: list[str] = []
    if policy_version not in (
        DISCOVERY_POLICY_VERSION_V010,
        DISCOVERY_POLICY_VERSION_V010_BROWSER_UI,
        DISCOVERY_POLICY_VERSION_V010_TOOLCHAIN,
        DISCOVERY_POLICY_VERSION_V010_BROWSER_RUNTIME,
    ):
        return [f"unknown discovery policy {policy_version!r}"]

    count = len(skills)
    if policy_version == DISCOVERY_POLICY_VERSION_V010:
        if count not in (HISTORICAL_SKILL_COUNT, V010_ADMITTED_SKILL_COUNT):
            return [
                f"expected {HISTORICAL_SKILL_COUNT} or {V010_ADMITTED_SKILL_COUNT} leaves under {policy_version} discovery policy, got {count}"
            ]
    elif policy_version == DISCOVERY_POLICY_VERSION_V010_BROWSER_UI:
        if count != V010_BROWSER_UI_ADMITTED_SKILL_COUNT:
            return [
                f"expected {V010_BROWSER_UI_ADMITTED_SKILL_COUNT} leaves under {policy_version} discovery policy, got {count}"
            ]
    elif policy_version == DISCOVERY_POLICY_VERSION_V010_TOOLCHAIN:
        if count != V010_TOOLCHAIN_ADMITTED_SKILL_COUNT:
            return [
                f"expected {V010_TOOLCHAIN_ADMITTED_SKILL_COUNT} leaves under {policy_version} discovery policy, got {count}"
            ]
    elif policy_version == DISCOVERY_POLICY_VERSION_V010_BROWSER_RUNTIME:
        if count != V010_BROWSER_RUNTIME_ADMITTED_SKILL_COUNT:
            return [
                f"expected {V010_BROWSER_RUNTIME_ADMITTED_SKILL_COUNT} leaves under {policy_version} discovery policy, got {count}"
            ]

    by_id: dict[str, dict[str, object]] = {}
    total_bytes = 0
    total_characters = 0

    for item in skills:
        name = str(item.get("name") or "")
        desc = str(item.get("description") or "")
        if not name or not desc:
            failures.append("malformed skill metadata with empty name or description")
            continue
        if not desc.startswith("Use when "):
            failures.append(f"skill {name!r} description must begin with 'Use when '")

        measured_bytes = len(desc.encode("utf-8"))
        measured_characters = len(desc)

        # Validate recorded description bytes
        recorded_bytes = item.get("bytes")
        if recorded_bytes is None:
            recorded_bytes = item.get("description_bytes")
        if recorded_bytes is not None:
            try:
                rec_b = int(recorded_bytes)
                if rec_b <= 0:
                    failures.append(f"skill {name!r} description bytes {rec_b} must be positive")
                elif rec_b != measured_bytes:
                    failures.append(
                        f"skill {name!r} description bytes mismatch (recorded {rec_b}, measured {measured_bytes})"
                    )
            except (ValueError, TypeError):
                failures.append(f"skill {name!r} malformed description bytes {recorded_bytes!r}")

        # Validate recorded description characters
        recorded_chars = item.get("characters")
        if recorded_chars is None:
            recorded_chars = item.get("description_characters")
        if recorded_chars is not None:
            try:
                rec_c = int(recorded_chars)
                if rec_c <= 0:
                    failures.append(f"skill {name!r} description characters {rec_c} must be positive")
                elif rec_c != measured_characters:
                    failures.append(
                        f"skill {name!r} description characters mismatch (recorded {rec_c}, measured {measured_characters})"
                    )
            except (ValueError, TypeError):
                failures.append(f"skill {name!r} malformed description characters {recorded_chars!r}")

        # Validate body measurements
        body_val = item.get("blob_bytes")
        if body_val is None:
            body_val = item.get("body_bytes")
        if body_val is None:
            body_val = item.get("source_blob_bytes")
        if body_val is not None:
            try:
                b_val = int(body_val)
                if b_val <= 0:
                    failures.append(f"skill {name!r} body bytes {b_val} must be positive")
            except (ValueError, TypeError):
                failures.append(f"skill {name!r} malformed body bytes {body_val!r}")

        if name in by_id:
            failures.append(f"duplicate skill ID {name!r}")
        by_id[name] = item
        total_bytes += measured_bytes
        total_characters += measured_characters

    if failures:
        return failures

    for orig_name, orig_desc in ORIGINAL_39_SKILL_DESCRIPTIONS.items():
        if orig_name not in by_id:
            failures.append(f"missing original 39 skill {orig_name!r}")
            continue
        actual_desc = str(by_id[orig_name].get("description") or "")
        if actual_desc != orig_desc:
            failures.append(
                f"original 39 skill {orig_name!r} description mutated (reservation theft)"
            )

    measured_39 = {
        name: str(by_id[name].get("description") or "")
        for name in ORIGINAL_39_SKILL_DESCRIPTIONS
        if name in by_id
    }
    if len(measured_39) == HISTORICAL_SKILL_COUNT:
        digest = compute_original_39_digest(measured_39)
        if digest != FROZEN_ORIGINAL_39_DIGEST:
            failures.append(
                f"original 39 digest mismatch: got {digest}, want {FROZEN_ORIGINAL_39_DIGEST}"
            )

    if policy_version == DISCOVERY_POLICY_VERSION_V010:
        if count == HISTORICAL_SKILL_COUNT:
            if (
                total_bytes != HISTORICAL_DESCRIPTION_BYTES
                or total_characters != HISTORICAL_DESCRIPTION_CHARACTERS
                or total_bytes > HISTORICAL_GLOBAL_DESCRIPTION_LIMIT
            ):
                failures.append(
                    f"baseline description footprint mismatch: bytes={total_bytes}, chars={total_characters}, limit={HISTORICAL_GLOBAL_DESCRIPTION_LIMIT}"
                )
            return failures

        # count == V010_ADMITTED_SKILL_COUNT (40)
        non_orig = [item for item in skills if str(item.get("name") or "") not in ORIGINAL_39_SKILL_DESCRIPTIONS]
        if len(non_orig) != 1:
            failures.append(f"expected exactly 1 admitted candidate skill, got {len(non_orig)}")
            return failures

        added = non_orig[0]
        added_name = str(added.get("name") or "")
        if added_name != V010_CURRENT_ADMITTED_CANDIDATE:
            failures.append(
                f"candidate {added_name!r} is not authorized for admission under {policy_version} discovery policy"
            )
        added_bytes = len(str(added.get("description") or "").encode("utf-8"))
        if added_bytes <= 0 or added_bytes > V010_MAX_RESERVATION_DESCRIPTION_BYTES:
            failures.append(
                f"candidate {added_name!r} description bytes {added_bytes} exceeds reservation ceiling of {V010_MAX_RESERVATION_DESCRIPTION_BYTES}"
            )
        added_body = added.get("blob_bytes")
        if added_body is None:
            added_body = added.get("body_bytes")
        if added_body is None:
            added_body = added.get("source_blob_bytes")
        if added_body is None:
            failures.append(f"candidate {added_name!r} missing required body bytes measurement")
        else:
            try:
                b_int = int(added_body)
                if b_int <= 0:
                    failures.append(f"candidate {added_name!r} body bytes {b_int} must be positive")
                elif b_int > V010_MAX_SVG_FILE_BYTES:
                    failures.append(
                        f"candidate {added_name!r} body bytes {b_int} exceeds SVG file limit of {V010_MAX_SVG_FILE_BYTES}"
                    )
            except (ValueError, TypeError):
                failures.append(f"candidate {added_name!r} malformed body bytes {added_body!r}")

        if total_bytes > V010_CURRENT_SVG_ADMISSION_CEILING:
            failures.append(
                f"total description bytes {total_bytes} exceeds current SVG admission ceiling of {V010_CURRENT_SVG_ADMISSION_CEILING}"
            )
        if total_bytes > V010_OVERALL_FUTURE_CEILING:
            failures.append(
                f"total description bytes {total_bytes} exceeds overall future ceiling of {V010_OVERALL_FUTURE_CEILING}"
            )
        return failures

    if policy_version == DISCOVERY_POLICY_VERSION_V010_BROWSER_UI:
        non_orig = [item for item in skills if str(item.get("name") or "") not in ORIGINAL_39_SKILL_DESCRIPTIONS]
        non_orig_names = {str(item.get("name") or "") for item in non_orig}

        for name in sorted(non_orig_names):
            if name not in V010_BROWSER_UI_ADMITTED_CANDIDATES:
                failures.append(
                    f"candidate {name!r} is not authorized for admission under {policy_version} discovery policy"
                )

        for req_name in sorted(V010_BROWSER_UI_ADMITTED_CANDIDATES):
            if req_name not in non_orig_names:
                failures.append(f"missing required candidate skill {req_name!r}")
                continue
            item = by_id[req_name]
            desc = str(item.get("description") or "")
            cand_bytes = len(desc.encode("utf-8"))
            if cand_bytes <= 0 or cand_bytes > V010_MAX_RESERVATION_DESCRIPTION_BYTES:
                failures.append(
                    f"candidate {req_name!r} description bytes {cand_bytes} exceeds reservation ceiling of {V010_MAX_RESERVATION_DESCRIPTION_BYTES}"
                )
            if req_name == "svg-language-profile":
                if desc != FROZEN_SVG_SKILL_DESCRIPTION:
                    failures.append(
                        "candidate 'svg-language-profile' description mutated (reservation theft)"
                    )
                body_val = item.get("blob_bytes")
                if body_val is None:
                    body_val = item.get("body_bytes")
                if body_val is None:
                    body_val = item.get("source_blob_bytes")
                if body_val is None:
                    failures.append("candidate 'svg-language-profile' missing required body bytes measurement")
                else:
                    try:
                        b_int = int(body_val)
                        if b_int <= 0:
                            failures.append(f"candidate 'svg-language-profile' body bytes {b_int} must be positive")
                        elif b_int > V010_MAX_SVG_FILE_BYTES:
                            failures.append(
                                f"candidate 'svg-language-profile' body bytes {b_int} exceeds SVG file limit of {V010_MAX_SVG_FILE_BYTES}"
                            )
                    except (ValueError, TypeError):
                        failures.append(f"candidate 'svg-language-profile' malformed body bytes {body_val!r}")
            else:
                body_val = item.get("blob_bytes")
                if body_val is None:
                    body_val = item.get("body_bytes")
                if body_val is None:
                    body_val = item.get("source_blob_bytes")
                if body_val is None:
                    failures.append(f"candidate {req_name!r} missing required body bytes measurement")

        if total_bytes > V010_BROWSER_UI_ADMISSION_CEILING:
            failures.append(
                f"total description bytes {total_bytes} exceeds current browser UI admission ceiling of {V010_BROWSER_UI_ADMISSION_CEILING}"
            )
        if total_bytes > V010_OVERALL_FUTURE_CEILING:
            failures.append(
                f"total description bytes {total_bytes} exceeds overall future ceiling of {V010_OVERALL_FUTURE_CEILING}"
            )

        return failures

    if policy_version == DISCOVERY_POLICY_VERSION_V010_TOOLCHAIN:
        non_orig = [item for item in skills if str(item.get("name") or "") not in ORIGINAL_39_SKILL_DESCRIPTIONS]
        non_orig_names = {str(item.get("name") or "") for item in non_orig}

        for name in sorted(non_orig_names):
            if name not in V010_TOOLCHAIN_ADMITTED_CANDIDATES:
                failures.append(
                    f"candidate {name!r} is not authorized for admission under {policy_version} discovery policy"
                )

        for req_name in sorted(V010_TOOLCHAIN_ADMITTED_CANDIDATES):
            if req_name not in non_orig_names:
                failures.append(f"missing required candidate skill {req_name!r}")
                continue
            item = by_id[req_name]
            desc = str(item.get("description") or "")
            cand_bytes = len(desc.encode("utf-8"))
            if cand_bytes <= 0 or cand_bytes > V010_MAX_RESERVATION_DESCRIPTION_BYTES:
                failures.append(
                    f"candidate {req_name!r} description bytes {cand_bytes} exceeds reservation ceiling of {V010_MAX_RESERVATION_DESCRIPTION_BYTES}"
                )
            if req_name == "svg-language-profile":
                if desc != FROZEN_SVG_SKILL_DESCRIPTION:
                    failures.append(
                        "candidate 'svg-language-profile' description mutated (reservation theft)"
                    )
                body_val = item.get("blob_bytes")
                if body_val is None:
                    body_val = item.get("body_bytes")
                if body_val is None:
                    body_val = item.get("source_blob_bytes")
                if body_val is None:
                    failures.append("candidate 'svg-language-profile' missing required body bytes measurement")
                else:
                    try:
                        b_int = int(body_val)
                        if b_int <= 0:
                            failures.append(f"candidate 'svg-language-profile' body bytes {b_int} must be positive")
                        elif b_int > V010_MAX_SVG_FILE_BYTES:
                            failures.append(
                                f"candidate 'svg-language-profile' body bytes {b_int} exceeds SVG file limit of {V010_MAX_SVG_FILE_BYTES}"
                            )
                    except (ValueError, TypeError):
                        failures.append(f"candidate 'svg-language-profile' malformed body bytes {body_val!r}")
            elif req_name == "playwright-test-profile":
                if desc != FROZEN_PLAYWRIGHT_SKILL_DESCRIPTION:
                    failures.append(
                        "candidate 'playwright-test-profile' description mutated (reservation theft)"
                    )
                body_val = item.get("blob_bytes")
                if body_val is None:
                    body_val = item.get("body_bytes")
                if body_val is None:
                    body_val = item.get("source_blob_bytes")
                if body_val is None:
                    failures.append(f"candidate {req_name!r} missing required body bytes measurement")
            elif req_name == "web-accessibility-profile":
                if desc != FROZEN_WEB_ACCESSIBILITY_SKILL_DESCRIPTION:
                    failures.append(
                        "candidate 'web-accessibility-profile' description mutated (reservation theft)"
                    )
                body_val = item.get("blob_bytes")
                if body_val is None:
                    body_val = item.get("body_bytes")
                if body_val is None:
                    body_val = item.get("source_blob_bytes")
                if body_val is None:
                    failures.append(f"candidate {req_name!r} missing required body bytes measurement")
            else:
                body_val = item.get("blob_bytes")
                if body_val is None:
                    body_val = item.get("body_bytes")
                if body_val is None:
                    body_val = item.get("source_blob_bytes")
                if body_val is None:
                    failures.append(f"candidate {req_name!r} missing required body bytes measurement")

        if total_bytes > V010_TOOLCHAIN_ADMISSION_CEILING:
            failures.append(
                f"total description bytes {total_bytes} exceeds current toolchain admission ceiling of {V010_TOOLCHAIN_ADMISSION_CEILING}"
            )
        if total_bytes > V010_OVERALL_FUTURE_CEILING:
            failures.append(
                f"total description bytes {total_bytes} exceeds overall future ceiling of {V010_OVERALL_FUTURE_CEILING}"
            )

        return failures

    # policy_version == DISCOVERY_POLICY_VERSION_V010_BROWSER_RUNTIME (45)
    non_orig = [item for item in skills if str(item.get("name") or "") not in ORIGINAL_39_SKILL_DESCRIPTIONS]
    non_orig_names = {str(item.get("name") or "") for item in non_orig}

    for name in sorted(non_orig_names):
        if name not in V010_BROWSER_RUNTIME_ADMITTED_CANDIDATES:
            failures.append(
                f"candidate {name!r} is not authorized for admission under {policy_version} discovery policy"
            )

    for req_name in sorted(V010_BROWSER_RUNTIME_ADMITTED_CANDIDATES):
        if req_name not in non_orig_names:
            failures.append(f"missing required candidate skill {req_name!r}")
            continue
        item = by_id[req_name]
        desc = str(item.get("description") or "")
        cand_bytes = len(desc.encode("utf-8"))
        if cand_bytes <= 0 or cand_bytes > V010_MAX_RESERVATION_DESCRIPTION_BYTES:
            failures.append(
                f"candidate {req_name!r} description bytes {cand_bytes} exceeds reservation ceiling of {V010_MAX_RESERVATION_DESCRIPTION_BYTES}"
            )
        if req_name == "svg-language-profile":
            if desc != FROZEN_SVG_SKILL_DESCRIPTION:
                failures.append(
                    "candidate 'svg-language-profile' description mutated (reservation theft)"
                )
            body_val = item.get("blob_bytes")
            if body_val is None:
                body_val = item.get("body_bytes")
            if body_val is None:
                body_val = item.get("source_blob_bytes")
            if body_val is None:
                failures.append("candidate 'svg-language-profile' missing required body bytes measurement")
            else:
                try:
                    b_int = int(body_val)
                    if b_int <= 0:
                        failures.append(f"candidate 'svg-language-profile' body bytes {b_int} must be positive")
                    elif b_int > V010_MAX_SVG_FILE_BYTES:
                        failures.append(
                            f"candidate 'svg-language-profile' body bytes {b_int} exceeds SVG file limit of {V010_MAX_SVG_FILE_BYTES}"
                        )
                except (ValueError, TypeError):
                    failures.append(f"candidate 'svg-language-profile' malformed body bytes {body_val!r}")
        elif req_name == "playwright-test-profile":
            if desc != FROZEN_PLAYWRIGHT_SKILL_DESCRIPTION:
                failures.append(
                    "candidate 'playwright-test-profile' description mutated (reservation theft)"
                )
            body_val = item.get("blob_bytes")
            if body_val is None:
                body_val = item.get("body_bytes")
            if body_val is None:
                body_val = item.get("source_blob_bytes")
            if body_val is None:
                failures.append(f"candidate {req_name!r} missing required body bytes measurement")
        elif req_name == "web-accessibility-profile":
            if desc != FROZEN_WEB_ACCESSIBILITY_SKILL_DESCRIPTION:
                failures.append(
                    "candidate 'web-accessibility-profile' description mutated (reservation theft)"
                )
            body_val = item.get("blob_bytes")
            if body_val is None:
                body_val = item.get("body_bytes")
            if body_val is None:
                body_val = item.get("source_blob_bytes")
            if body_val is None:
                failures.append(f"candidate {req_name!r} missing required body bytes measurement")
        elif req_name == "vite-build-profile":
            if desc != FROZEN_VITE_SKILL_DESCRIPTION:
                failures.append(
                    "candidate 'vite-build-profile' description mutated (reservation theft)"
                )
            body_val = item.get("blob_bytes")
            if body_val is None:
                body_val = item.get("body_bytes")
            if body_val is None:
                body_val = item.get("source_blob_bytes")
            if body_val is None:
                failures.append(f"candidate {req_name!r} missing required body bytes measurement")
        elif req_name == "npm-package-manager-profile":
            if desc != FROZEN_NPM_SKILL_DESCRIPTION:
                failures.append(
                    "candidate 'npm-package-manager-profile' description mutated (reservation theft)"
                )
            body_val = item.get("blob_bytes")
            if body_val is None:
                body_val = item.get("body_bytes")
            if body_val is None:
                body_val = item.get("source_blob_bytes")
            if body_val is None:
                failures.append(f"candidate {req_name!r} missing required body bytes measurement")
        else:
            body_val = item.get("blob_bytes")
            if body_val is None:
                body_val = item.get("body_bytes")
            if body_val is None:
                body_val = item.get("source_blob_bytes")
            if body_val is None:
                failures.append(f"candidate {req_name!r} missing required body bytes measurement")

    if total_bytes > V010_BROWSER_RUNTIME_ADMISSION_CEILING:
        failures.append(
            f"total description bytes {total_bytes} exceeds current browser runtime admission ceiling of {V010_BROWSER_RUNTIME_ADMISSION_CEILING}"
        )
    if total_bytes > V010_OVERALL_FUTURE_CEILING:
        failures.append(
            f"total description bytes {total_bytes} exceeds overall future ceiling of {V010_OVERALL_FUTURE_CEILING}"
        )

    return failures


DISCOVERY_POLICY_SELECTOR = Path("testing/apg-discovery-policy.json")


def _resolve_discovery_policy(
    root: Path, explicit_policy: str | None = None
) -> tuple[str | None, str | None]:
    """Select the one current policy; historical/synthetic roots have no selector.

    The current Go policy owner requires its selector. An explicit selection
    cannot override a malformed, missing-required or conflicting selector.
    """
    candidate = root / DISCOVERY_POLICY_SELECTOR
    required = (root / "skills/discovery_policy.go").exists()
    selected = None
    if candidate.exists() or candidate.is_symlink():
        if not _ordinary_file(candidate):
            return None, "policy selector must be a direct regular file"
        try:
            pairs = json.loads(candidate.read_text(encoding="utf-8"), object_pairs_hook=list)
            if not isinstance(pairs, list) or any(not isinstance(p, tuple) or len(p) != 2 for p in pairs):
                return None, "policy selector must be an object"
            data = dict(pairs)
            if len(data) != len(pairs) or set(data) != {"schema_version", "policy"}:
                return None, "policy selector has duplicate, missing or unknown fields"
            if type(data["schema_version"]) is not int or data["schema_version"] != 1:
                return None, "unknown policy selector schema"
            selected = data["policy"]
            if not isinstance(selected, str) or not selected:
                return None, "policy selector requires a policy string"
        except (OSError, ValueError, TypeError):
            return None, "unreadable or malformed policy selector"
    elif required:
        return None, "current discovery policy selector is missing"
    if explicit_policy is not None:
        if not isinstance(explicit_policy, str) or not explicit_policy.strip():
            return None, "empty explicit discovery policy"
        if selected is not None and selected != explicit_policy:
            return None, "explicit policy conflicts with selector"
        selected = explicit_policy
    return selected, None


SKILL_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
TOP_LEVEL_KEY = re.compile(r"(?P<key>[A-Za-z0-9_-]+):")
OPENING_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
INLINE_LINK = re.compile(
    r"(?<!\\)!?\[[^\]\n]*\]\((?:<(?P<angle>[^>\n]+)>|"
    r"(?P<plain>[^\s()<>\n]+))\)"
)
CATALOG_ROW = re.compile(
    r"^\| \[`(?P<name>[^`|]+)`\]\((?P<target>[^\s()|]+)\) "
    r"\| (?P<trigger>[^|]*?) \| `(?P<maturity>[^`|]+)` \|$"
)
EXTERNAL_DESTINATION = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


def context_footprint_report(*, blobs: dict[str, bytes]) -> dict[str, object]:
    """Measure repository metadata for the governance gate.

    Portable consumer discovery is Go-owned.  This deliberately narrow local
    measurement reuses the checker's accepted frontmatter grammar so the
    release-shaped source tree does not retain the old Python consumer module.
    """

    rows: list[dict[str, object]] = []
    malformed: list[dict[str, str]] = []
    for relative_path, blob in sorted(blobs.items()):
        parsed = parse_frontmatter(blob)
        names = parsed.values("name")
        descriptions = parsed.values("description")
        if (
            not parsed.starts_at_byte_one
            or not parsed.terminated
            or len(names) != 1
            or len(descriptions) != 1
        ):
            malformed.append(
                {
                    "path": relative_path,
                    "error": "metadata is not one accepted name/description frontmatter pair",
                }
            )
            continue
        description = descriptions[0]
        rows.append(
            {
                "name": names[0],
                "description": description,
                "bytes": len(description.encode("utf-8")),
                "characters": len(description),
                "relative_path": relative_path,
            }
        )
    rows.sort(key=lambda row: (-int(row["bytes"]), str(row["name"])))
    total_bytes = sum(int(row["bytes"]) for row in rows)
    total_characters = sum(int(row["characters"]) for row in rows)
    return {
        "skill_count": len(rows),
        "discoverable_skill_count": len(rows),
        "total_bytes": total_bytes,
        "total_characters": total_characters,
        "total_description_bytes": total_bytes,
        "total_description_characters": total_characters,
        "skills": rows,
        "malformed": malformed,
    }


@dataclass(frozen=True)
class ScalarField:
    """One accepted top-level required frontmatter scalar."""

    key: str
    value: str
    line: int


@dataclass(frozen=True)
class FrontmatterResult:
    """Lexical result for APG's required-field frontmatter subset."""

    starts_at_byte_one: bool
    terminated: bool
    body_start_line: int
    fields: tuple[ScalarField, ...]
    invalid_required: tuple[tuple[str, int], ...]
    invalid_top_level_keys: tuple[int, ...]

    def values(self, key: str) -> tuple[str, ...]:
        return tuple(field.value for field in self.fields if field.key == key)

    def line_for(self, key: str) -> int | None:
        for field in self.fields:
            if field.key == key:
                return field.line
        return None


@dataclass(frozen=True)
class LinkToken:
    """One accepted literal inline Markdown destination."""

    destination: str
    line: int


@dataclass(frozen=True)
class CatalogRow:
    """One row in the adopted APG catalog table."""

    name: str
    target: str
    trigger: str
    maturity: str
    line: int


@dataclass(frozen=True)
class CatalogResult:
    """Lexical result for the exact APG catalog contract."""

    heading_count: int
    header_valid: bool
    rows: tuple[CatalogRow, ...]
    malformed_lines: tuple[int, ...]


@dataclass(frozen=True)
class Diagnostic:
    """One deterministic noncompliance diagnostic."""

    code: str
    path: str
    invariant: str
    message: str
    action: str
    line: int | None = None
    column: int | None = None

    def json_value(self) -> dict[str, object]:
        return {
            "action": self.action,
            "code": self.code,
            "column": self.column,
            "invariant": self.invariant,
            "line": self.line,
            "message": self.message,
            "path": self.path,
        }


@dataclass(frozen=True)
class CheckResult:
    """Complete checker result and bounded counts."""

    diagnostics: tuple[Diagnostic, ...]
    canonical_skills: int
    catalog_rows: int
    projections: int

    @property
    def passed(self) -> bool:
        return not self.diagnostics


def valid_skill_name(value: str) -> bool:
    """Return whether value satisfies APG's pinned skill-name grammar."""

    return 1 <= len(value) <= 64 and SKILL_NAME.fullmatch(value) is not None


def parse_frontmatter(data: bytes) -> FrontmatterResult:
    """Parse only APG's top-level plain-scalar required fields."""

    starts = data.startswith(b"---\n") or data.startswith(b"---\r\n")
    text = data.decode("utf-8")
    lines = text.splitlines()
    terminated = False
    end = len(lines)
    body_start_line = 1
    if starts:
        body_start_line = len(lines) + 1
        for index, line in enumerate(lines[1:], start=1):
            if line == "---":
                terminated = True
                end = index
                body_start_line = index + 2
                break

    fields: list[ScalarField] = []
    invalid: list[tuple[str, int]] = []
    invalid_top_level_keys: list[int] = []
    scan_start = 1 if starts else 0
    for index, line in enumerate(lines[scan_start:end], start=scan_start + 1):
        if not line or line[0].isspace() or line.startswith("#"):
            continue
        key_match = TOP_LEVEL_KEY.match(line)
        if key_match is None:
            explicit_key = line == "?" or line.startswith(("? ", "?\t"))
            closing = (
                line.rfind("]")
                if line.startswith("[")
                else line.rfind("}") if line.startswith("{") else -1
            )
            flow_key = (
                closing >= 0
                and line[closing + 1 :].lstrip(" \t").startswith(":")
            )
            mapping_like = flow_key or (
                ":" in line
                and not line.startswith(("- ", "-\t", "[", "{"))
            )
            if explicit_key or mapping_like:
                invalid_top_level_keys.append(index)
            continue
        key = key_match.group("key")
        if key not in ("name", "description"):
            continue
        expected_prefix = f"{key}: "
        value = line[len(expected_prefix) :] if line.startswith(expected_prefix) else ""
        invalid_value = (
            not line.startswith(expected_prefix)
            or not value
            or value[0] in {'"', "'", "|", ">"}
            or " #" in value
            or "\t" in value
            or any(ord(character) < 32 for character in value)
        )
        if invalid_value:
            invalid.append((key, index))
        else:
            fields.append(ScalarField(key, value, index))
    return FrontmatterResult(
        starts,
        terminated,
        body_start_line,
        tuple(fields),
        tuple(invalid),
        tuple(invalid_top_level_keys),
    )


def markdown_body(text: str, frontmatter: FrontmatterResult) -> str:
    """Return only the Markdown body while preserving source line numbers."""

    if not frontmatter.starts_at_byte_one or not frontmatter.terminated:
        return ""
    lines = text.splitlines()
    body_index = frontmatter.body_start_line - 1
    return ("\n" * body_index) + "\n".join(lines[body_index:])


def visible_lines(text: str) -> tuple[tuple[int, str], ...]:
    """Return nonempty lines outside backtick and tilde fenced code."""

    visible: list[tuple[int, str]] = []
    fence_character: str | None = None
    fence_length = 0
    for line_number, line in enumerate(text.splitlines(), start=1):
        if fence_character is None:
            match = OPENING_FENCE.match(line)
        else:
            match = re.fullmatch(
                rf" {{0,3}}{re.escape(fence_character)}"
                rf"{{{fence_length},}}[ \t]*",
                line,
            )
        if match is not None:
            if fence_character is not None:
                fence_character = None
                fence_length = 0
                continue
            marker = match.group(1)
            fence_character = marker[0]
            fence_length = len(marker)
            continue
        if fence_character is None and line.strip():
            visible.append((line_number, line))
    return tuple(visible)


def inline_links(text: str) -> tuple[LinkToken, ...]:
    """Return accepted same-line literal links and images outside fences."""

    tokens: list[LinkToken] = []
    for line_number, line in visible_lines(text):
        for match in INLINE_LINK.finditer(line):
            destination = match.group("angle") or match.group("plain")
            tokens.append(LinkToken(destination, line_number))
    return tuple(tokens)


def parse_catalog(text: str) -> CatalogResult:
    """Parse the one exact catalog table outside fenced code."""

    lines = visible_lines(text)
    heading_indexes = [
        index for index, (_, line) in enumerate(lines) if line in CATALOG_HEADINGS
    ]
    if len(heading_indexes) != 1:
        return CatalogResult(len(heading_indexes), False, (), ())

    start = heading_indexes[0] + 1
    if start + 1 >= len(lines):
        return CatalogResult(1, False, (), ())
    header_valid = (
        lines[start][1] == CATALOG_HEADER
        and lines[start + 1][1] == CATALOG_SEPARATOR
    )
    if not header_valid:
        return CatalogResult(1, False, (), ())

    rows: list[CatalogRow] = []
    malformed: list[int] = []
    for line_number, line in lines[start + 2 :]:
        if not line.startswith("|"):
            break
        match = CATALOG_ROW.fullmatch(line)
        if match is None:
            malformed.append(line_number)
            continue
        rows.append(
            CatalogRow(
                match.group("name"),
                match.group("target"),
                match.group("trigger"),
                match.group("maturity"),
                line_number,
            )
        )
    return CatalogResult(1, True, tuple(rows), tuple(malformed))


def _relative(path: Path, root: Path) -> str:
    try:
        value = path.relative_to(root).as_posix()
    except ValueError:
        return "."
    return value or "."


def _ordinary_directory(path: Path) -> bool:
    try:
        return path.is_dir() and not path.is_symlink()
    except OSError:
        return False


def _ordinary_file(path: Path) -> bool:
    try:
        return stat.S_ISREG(path.lstat().st_mode) and not path.is_symlink()
    except OSError:
        return False


def _contained(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _diagnostic(
    diagnostics: list[Diagnostic],
    code: str,
    path: str,
    invariant: str,
    message: str,
    action: str,
    line: int | None = None,
) -> None:
    diagnostics.append(
        Diagnostic(code, path, invariant, message, action, line=line, column=1 if line else None)
    )


def _read_utf8(
    path: Path,
    relative: str,
    diagnostics: list[Diagnostic],
) -> tuple[bytes, str] | None:
    try:
        data = path.read_bytes()
    except OSError:
        _diagnostic(
            diagnostics,
            "APG005",
            relative,
            "skill-file-readable",
            "required file could not be read",
            "restore an ordinary readable file and rerun the checker",
        )
        return None
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        _diagnostic(
            diagnostics,
            "APG006",
            relative,
            "utf8-text",
            "file is not valid UTF-8",
            "encode the file as valid UTF-8 and rerun the checker",
        )
        return None
    return data, text


def _check_frontmatter_and_body(
    leaf: Path,
    skill_file: Path,
    relative: str,
    data: bytes,
    text: str,
    diagnostics: list[Diagnostic],
    declared: list[tuple[str, str]],
    policy: str | None = DISCOVERY_POLICY_VERSION,
) -> str:
    parsed = parse_frontmatter(data)
    if not parsed.starts_at_byte_one:
        _diagnostic(
            diagnostics,
            "APG007",
            relative,
            "frontmatter-byte-one",
            "frontmatter does not begin with --- at byte one",
            "move the opening delimiter to byte one without a byte-order mark",
            1,
        )
    if not parsed.terminated:
        _diagnostic(
            diagnostics,
            "APG008",
            relative,
            "frontmatter-closure",
            "frontmatter has no exact closing --- delimiter",
            "add the closing delimiter before the Markdown body",
        )

    invalid_keys = {key for key, _ in parsed.invalid_required}
    for line in parsed.invalid_top_level_keys:
        _diagnostic(
            diagnostics,
            "APG035",
            relative,
            "top-level-frontmatter-key-grammar",
            "top-level frontmatter key does not match the accepted APG "
            "plain-key grammar",
            "use a column-zero key containing only ASCII letters, digits, "
            "underscores, or hyphens followed immediately by a colon",
            line,
        )
    for key, line in parsed.invalid_required:
        _diagnostic(
            diagnostics,
            "APG010",
            relative,
            "required-plain-scalar",
            f"{key} is not an accepted top-level unquoted plain scalar",
            f"write {key} as one unquoted 'key: value' line without a comment",
            line,
        )
    for key in ("name", "description"):
        values = parsed.values(key)
        occurrence_count = len(values) + sum(
            1 for invalid_key, _ in parsed.invalid_required if invalid_key == key
        )
        if occurrence_count != 1:
            _diagnostic(
                diagnostics,
                "APG009",
                relative,
                "required-frontmatter-key",
                f"{key} occurs {occurrence_count} times; exactly one is required",
                f"retain exactly one accepted top-level {key} scalar",
            )

    names = parsed.values("name")
    if len(names) == 1 and "name" not in invalid_keys:
        name = names[0]
        line = parsed.line_for("name")
        declared.append((name, relative))
        if not valid_skill_name(name):
            _diagnostic(
                diagnostics,
                "APG011",
                relative,
                "skill-name-grammar",
                "name does not satisfy the accepted APG grammar",
                "use 1-64 lowercase ASCII letters, digits, and single internal hyphens",
                line,
            )
        if name != leaf.name:
            _diagnostic(
                diagnostics,
                "APG012",
                relative,
                "name-directory-agreement",
                "frontmatter name does not match the canonical directory",
                "make the name scalar and directory basename identical",
                line,
            )

    descriptions = parsed.values("description")
    if len(descriptions) == 1 and "description" not in invalid_keys:
        description = descriptions[0]
        if not description.startswith("Use when ") or len(description) > 1024:
            _diagnostic(
                diagnostics,
                "APG014",
                relative,
                "trigger-oriented-description",
                "description must begin with 'Use when ' and contain at most 1024 characters",
                "write one bounded trigger-oriented description",
                parsed.line_for("description"),
            )
        description_bytes = len(description.encode("utf-8"))
        if leaf.name in V06_PROFILE_NAMES and not (
            V06_DESCRIPTION_BYTES_MINIMUM
            <= description_bytes
            <= V06_DESCRIPTION_BYTES_MAXIMUM
        ):
            _diagnostic(
                diagnostics,
                "APG039",
                relative,
                "v0-6-description-byte-band",
                "v0.6 profile description is outside the inclusive 170 to 330 UTF-8 byte band",
                "sharpen the v0.6 trigger and non-trigger boundary within the frozen byte band",
                parsed.line_for("description"),
            )
        if policy in (
            DISCOVERY_POLICY_VERSION_V010,
            DISCOVERY_POLICY_VERSION_V010_BROWSER_UI,
            DISCOVERY_POLICY_VERSION_V010_TOOLCHAIN,
            DISCOVERY_POLICY_VERSION_V010_BROWSER_RUNTIME,
        ):
            if leaf.name in V010_ELIGIBLE_CANDIDATES and description_bytes > V010_MAX_RESERVATION_DESCRIPTION_BYTES:
                _diagnostic(
                    diagnostics,
                    "APG042",
                    relative,
                    "v0-10-description-reservation",
                    f"v0.10 candidate description is {description_bytes} UTF-8 bytes; exceeds reservation ceiling of {V010_MAX_RESERVATION_DESCRIPTION_BYTES}",
                    "shorten the description to within the 330 UTF-8 byte reservation limit",
                    parsed.line_for("description"),
                )
            if leaf.name == "svg-language-profile" and len(data) > V010_MAX_SVG_FILE_BYTES:
                _diagnostic(
                    diagnostics,
                    "APG043",
                    relative,
                    "svg-file-size-limit",
                    f"SVG file is {len(data)} bytes; exceeds maximum permitted size of {V010_MAX_SVG_FILE_BYTES} bytes",
                    "reduce the SVG file size to at most 20480 bytes",
                )
            if leaf.name in ORIGINAL_39_SKILL_DESCRIPTIONS and description != ORIGINAL_39_SKILL_DESCRIPTIONS[leaf.name]:
                _diagnostic(
                    diagnostics,
                    "APG044",
                    relative,
                    "original-39-description-freeze",
                    f"description for original skill {leaf.name!r} differs from frozen original description (reservation theft)",
                    "restore the exact frozen description for the original skill",
                    parsed.line_for("description"),
                )
            if policy in (
                DISCOVERY_POLICY_VERSION_V010_BROWSER_UI,
                DISCOVERY_POLICY_VERSION_V010_TOOLCHAIN,
                DISCOVERY_POLICY_VERSION_V010_BROWSER_RUNTIME,
            ) and leaf.name == "svg-language-profile" and description != FROZEN_SVG_SKILL_DESCRIPTION:
                _diagnostic(
                    diagnostics,
                    "APG044",
                    relative,
                    "original-39-description-freeze",
                    f"description for SVG candidate {leaf.name!r} differs from frozen description (reservation theft)",
                    "restore the exact frozen description for the SVG candidate",
                    parsed.line_for("description"),
                )
            if policy in (
                DISCOVERY_POLICY_VERSION_V010_TOOLCHAIN,
                DISCOVERY_POLICY_VERSION_V010_BROWSER_RUNTIME,
            ):
                if leaf.name == "playwright-test-profile" and description != FROZEN_PLAYWRIGHT_SKILL_DESCRIPTION:
                    _diagnostic(
                        diagnostics,
                        "APG044",
                        relative,
                        "original-39-description-freeze",
                        f"description for Playwright candidate {leaf.name!r} differs from frozen description (reservation theft)",
                        "restore the exact frozen description for the Playwright candidate",
                        parsed.line_for("description"),
                    )
                elif leaf.name == "web-accessibility-profile" and description != FROZEN_WEB_ACCESSIBILITY_SKILL_DESCRIPTION:
                    _diagnostic(
                        diagnostics,
                        "APG044",
                        relative,
                        "original-39-description-freeze",
                        f"description for Web Accessibility candidate {leaf.name!r} differs from frozen description (reservation theft)",
                        "restore the exact frozen description for the Web Accessibility candidate",
                        parsed.line_for("description"),
                    )
            if policy == DISCOVERY_POLICY_VERSION_V010_BROWSER_RUNTIME:
                if leaf.name == "vite-build-profile" and description != FROZEN_VITE_SKILL_DESCRIPTION:
                    _diagnostic(
                        diagnostics,
                        "APG044",
                        relative,
                        "original-39-description-freeze",
                        f"description for Vite candidate {leaf.name!r} differs from frozen description (reservation theft)",
                        "restore the exact frozen description for the Vite candidate",
                        parsed.line_for("description"),
                    )
                elif leaf.name == "npm-package-manager-profile" and description != FROZEN_NPM_SKILL_DESCRIPTION:
                    _diagnostic(
                        diagnostics,
                        "APG044",
                        relative,
                        "original-39-description-freeze",
                        f"description for NPM candidate {leaf.name!r} differs from frozen description (reservation theft)",
                        "restore the exact frozen description for the NPM candidate",
                        parsed.line_for("description"),
                    )

    body = markdown_body(text, parsed)
    lines = visible_lines(body)
    h1_count = sum(1 for _, line in lines if re.fullmatch(r"#\s+\S.*", line))
    if h1_count != 1:
        _diagnostic(
            diagnostics,
            "APG015",
            relative,
            "single-h1",
            f"skill body contains {h1_count} H1 headings; exactly one is required",
            "retain one descriptive H1 outside fenced code",
        )
    for heading in REQUIRED_H2S:
        count = sum(1 for _, line in lines if line == f"## {heading}")
        if count != 1:
            _diagnostic(
                diagnostics,
                "APG016",
                relative,
                "required-h2-owner",
                f"heading '## {heading}' occurs {count} times; exactly one is required",
                f"retain exactly one '## {heading}' heading outside fenced code",
            )
    return body


def _check_local_links(
    leaf: Path,
    markdown: Path,
    text: str,
    root: Path,
    diagnostics: list[Diagnostic],
) -> None:
    relative = _relative(markdown, root)
    try:
        physical_leaf = leaf.resolve(strict=True)
    except OSError:
        return
    for token in inline_links(text):
        destination = token.destination
        if destination.startswith("#") or destination.startswith("//"):
            continue
        if EXTERNAL_DESTINATION.match(destination):
            continue
        local = destination.split("#", 1)[0]
        if not local:
            continue
        candidate = markdown.parent / local
        try:
            resolved = candidate.resolve(strict=True)
        except (OSError, RuntimeError):
            _diagnostic(
                diagnostics,
                "APG021",
                relative,
                "skill-local-link",
                f"local destination does not resolve: {destination!r}",
                "restore the target or correct the literal relative destination",
                token.line,
            )
            continue
        expected_spec = root / "docs/specs" / f"{leaf.name}.md"
        lexical_candidate = Path(os.path.normpath(candidate))
        normative_spec = (
            markdown == leaf / "SKILL.md"
            and destination.split("#", 1)[0]
            == f"../../docs/specs/{leaf.name}.md"
            and lexical_candidate == expected_spec
            and _ordinary_directory(root / "docs")
            and _ordinary_directory(root / "docs/specs")
            and _ordinary_file(expected_spec)
            and resolved == expected_spec.resolve(strict=True)
        )
        if not _contained(resolved, physical_leaf) and not normative_spec:
            _diagnostic(
                diagnostics,
                "APG021",
                relative,
                "skill-local-link",
                f"local destination escapes the owning skill: {destination!r}",
                "point the link to an existing path inside the owning skill",
                token.line,
            )


def _check_leaf(
    root: Path,
    leaf: Path,
    diagnostics: list[Diagnostic],
    declared: list[tuple[str, str]],
    policy: str | None = None,
) -> None:
    skill_file = leaf / "SKILL.md"
    skill_relative = _relative(skill_file, root)
    if not _ordinary_file(skill_file):
        _diagnostic(
            diagnostics,
            "APG005",
            skill_relative,
            "skill-file-regular",
            "required SKILL.md is missing, a symlink, or not a regular file",
            "restore one ordinary readable SKILL.md in the canonical leaf",
        )
        return

    loaded = _read_utf8(skill_file, skill_relative, diagnostics)
    if loaded is not None:
        data, text = loaded
        body = _check_frontmatter_and_body(
            leaf, skill_file, skill_relative, data, text, diagnostics, declared, policy=policy
        )
        _check_local_links(leaf, skill_file, body, root, diagnostics)

    try:
        entries = sorted(leaf.iterdir(), key=lambda item: item.name)
    except OSError:
        entries = []
    for entry in entries:
        if entry.name == "SKILL.md":
            continue
        entry_relative = _relative(entry, root)
        if entry.name not in SUPPORT_DIRECTORIES:
            _diagnostic(
                diagnostics,
                "APG017",
                entry_relative,
                "accepted-leaf-entry",
                "top-level skill entry is outside the adopted APG leaf shape",
                "remove it or authorize and document an APG leaf-shape change",
            )
            continue
        if not _ordinary_directory(entry):
            _diagnostic(
                diagnostics,
                "APG018",
                entry_relative,
                "support-directory-type",
                "optional support entry is not an ordinary directory",
                "replace it with an ordinary contained directory or remove it",
            )
            continue
        try:
            support_entries = sorted(entry.rglob("*"), key=lambda item: item.as_posix())
        except OSError:
            support_entries = []
        if not support_entries:
            _diagnostic(
                diagnostics,
                "APG019",
                entry_relative,
                "support-directory-nonempty",
                "optional support directory is empty",
                "remove the directory or add the justified support artifact",
            )
            continue
        try:
            physical_leaf = leaf.resolve(strict=True)
        except OSError:
            physical_leaf = leaf
        for support in support_entries:
            support_relative = _relative(support, root)
            if support.is_symlink():
                try:
                    target = support.resolve(strict=True)
                except (OSError, RuntimeError):
                    target = None
                if target is None or not _contained(target, physical_leaf):
                    _diagnostic(
                        diagnostics,
                        "APG020",
                        support_relative,
                        "support-link-containment",
                        "support symlink is broken or escapes the owning skill",
                        "remove it or retarget it to an existing path inside the skill",
                    )
                elif (
                    support.suffix.lower() == ".md"
                    and target.is_file()
                ):
                    loaded_support = _read_utf8(
                        support, support_relative, diagnostics
                    )
                    if loaded_support is not None:
                        _check_local_links(
                            leaf,
                            support,
                            loaded_support[1],
                            root,
                            diagnostics,
                        )
                continue
            if support.is_file() and support.suffix.lower() == ".md":
                loaded_support = _read_utf8(support, support_relative, diagnostics)
                if loaded_support is not None:
                    _check_local_links(
                        leaf,
                        support,
                        loaded_support[1],
                        root,
                        diagnostics,
                    )


def _check_catalog(
    root: Path,
    readme: Path,
    canonical: dict[str, Path] | set[str],
    diagnostics: list[Diagnostic],
) -> tuple[CatalogRow, ...]:
    canonical_paths = (
        canonical
        if isinstance(canonical, dict)
        else {name: readme.parent / name for name in canonical}
    )
    canonical_names = set(canonical_paths)
    relative = _relative(readme, root)
    if not _ordinary_file(readme):
        _diagnostic(
            diagnostics,
            "APG002",
            relative,
            "catalog-file-regular",
            "skills/README.md is missing, a symlink, or not a regular file",
            "restore the ordinary catalog file",
        )
        return ()
    loaded = _read_utf8(readme, relative, diagnostics)
    if loaded is None:
        return ()
    parsed = parse_catalog(loaded[1])
    if parsed.heading_count != 1:
        _diagnostic(
            diagnostics,
            "APG022",
            relative,
            "single-catalog-heading",
            f"exact APG catalog heading occurs {parsed.heading_count} times",
            "retain one exact current or legacy APG catalog heading outside "
            "fenced code",
        )
    if not parsed.header_valid or parsed.malformed_lines:
        _diagnostic(
            diagnostics,
            "APG023",
            relative,
            "catalog-table-shape",
            "catalog header, separator, or row does not match the adopted table grammar",
            "restore the exact three-column catalog contract",
            parsed.malformed_lines[0] if parsed.malformed_lines else None,
        )
    counts = Counter(row.name for row in parsed.rows)
    for name, count in sorted(counts.items()):
        if count > 1:
            _diagnostic(
                diagnostics,
                "APG024",
                relative,
                "catalog-row-unique",
                f"catalog contains {count} rows for {name!r}",
                "retain exactly one catalog row per canonical skill",
            )
    catalog_names = set(counts)
    if catalog_names != canonical_names:
        _diagnostic(
            diagnostics,
            "APG025",
            relative,
            "catalog-canonical-bijection",
            "catalog skill names do not equal the canonical skill directories",
            "add missing rows and remove unknown rows until the sets match",
        )
    for row in parsed.rows:
        leaf = canonical_paths.get(row.name)
        expected = (
            f"{_relative(leaf, readme.parent)}/SKILL.md"
            if leaf is not None
            else f"{row.name}/SKILL.md"
        )
        target = readme.parent / row.target
        if row.target != expected or not _ordinary_file(target):
            _diagnostic(
                diagnostics,
                "APG026",
                relative,
                "catalog-canonical-link",
                f"catalog link for {row.name!r} is not the matching canonical SKILL.md",
                f"set the target to {expected!r}",
                row.line,
            )
        if not row.trigger.strip():
            _diagnostic(
                diagnostics,
                "APG027",
                relative,
                "catalog-trigger-cell",
                f"catalog trigger boundary is empty for {row.name!r}",
                "record a nonempty trigger-boundary summary",
                row.line,
            )
        if row.maturity not in MATURITY_VALUES:
            _diagnostic(
                diagnostics,
                "APG028",
                relative,
                "catalog-maturity-vocabulary",
                f"catalog maturity {row.maturity!r} is not recognized",
                "use bootstrap, provisional, evaluated, stable, or deprecated",
                row.line,
            )
    return parsed.rows


def _check_projection(
    root: Path,
    canonical: dict[str, Path],
    diagnostics: list[Diagnostic],
) -> int:
    agents = root / ".agents"
    projection = agents / "skills"
    if not _ordinary_directory(agents) or not _ordinary_directory(projection):
        _diagnostic(
            diagnostics,
            "APG029",
            ".agents/skills",
            "projection-root-real",
            ".agents and .agents/skills must be ordinary directories",
            "restore the checked-in ordinary projection directories",
        )
        return 0
    try:
        entries = {entry.name: entry for entry in projection.iterdir()}
    except OSError:
        entries = {}
    expected_names = set(canonical)
    actual_names = set(entries)
    if actual_names != expected_names:
        _diagnostic(
            diagnostics,
            "APG030",
            ".agents/skills",
            "projection-canonical-bijection",
            "projection names do not equal the canonical skill directories",
            "add missing projections and remove extra entries",
        )
    try:
        physical_root = root.resolve(strict=True)
        physical_skills = (root / "skills").resolve(strict=True)
    except OSError:
        physical_root = root
        physical_skills = root / "skills"
    for name in sorted(expected_names & actual_names):
        link = entries[name]
        relative = _relative(link, root)
        if not link.is_symlink():
            _diagnostic(
                diagnostics,
                "APG031",
                relative,
                "projection-entry-symlink",
                "projection entry is not a symbolic link",
                "replace it with the exact relative canonical symlink",
            )
            continue
        try:
            raw_target = os.readlink(link)
        except OSError:
            raw_target = ""
        expected_raw = Path(
            os.path.relpath(canonical[name], start=link.parent)
        ).as_posix()
        if raw_target != expected_raw:
            _diagnostic(
                diagnostics,
                "APG032",
                relative,
                "projection-raw-target",
                f"raw target differs from {expected_raw!r}",
                f"recreate the link with raw target {expected_raw!r}",
            )
        try:
            resolved = link.resolve(strict=True)
            expected = canonical[name].resolve(strict=True)
        except (OSError, RuntimeError):
            _diagnostic(
                diagnostics,
                "APG033",
                relative,
                "projection-resolution",
                "projection is broken, cyclic, or cannot resolve",
                "restore the exact contained link to the canonical directory",
            )
            continue
        if (
            resolved != expected
            or not _contained(resolved, physical_skills)
            or not _contained(resolved, physical_root)
        ):
            _diagnostic(
                diagnostics,
                "APG033",
                relative,
                "projection-resolution",
                "projection does not resolve to the matching contained canonical leaf",
                "restore the exact contained link to the canonical directory",
            )
            continue
        projected_skill = link / "SKILL.md"
        canonical_skill = canonical[name] / "SKILL.md"
        try:
            projected_file = projected_skill.resolve(strict=True)
            canonical_file = canonical_skill.resolve(strict=True)
        except (OSError, RuntimeError):
            projected_file = None
            canonical_file = None
        if (
            projected_file is None
            or projected_file != canonical_file
            or not _ordinary_file(canonical_skill)
        ):
            _diagnostic(
                diagnostics,
                "APG034",
                _relative(projected_skill, root),
                "projected-skill-identity",
                "projected SKILL.md does not resolve to the canonical regular file",
                "restore the canonical file and exact projection",
            )
    return len(entries)


def check_library(root: Path, policy: str | None = None) -> CheckResult:
    """Validate root without mutation and return all deterministic diagnostics."""

    diagnostics: list[Diagnostic] = []
    root = Path(root)
    skills = root / "skills"
    canonical: dict[str, Path] = {}
    canonical_leaves: tuple[Path, ...] = ()
    if not _ordinary_directory(skills):
        _diagnostic(
            diagnostics,
            "APG001",
            "skills",
            "skills-root-real",
            "skills is missing, a symlink, or not an ordinary directory",
            "restore the repository-owned ordinary skills directory",
        )
    else:
        canonical_leaves = apg_skill_topology.discover_canonical_leaves(
            root,
            skills,
            partial(_diagnostic, diagnostics),
        )
        leaf_name_counts = Counter(leaf.name for leaf in canonical_leaves)
        canonical = {
            leaf.name: leaf
            for leaf in canonical_leaves
            if leaf_name_counts[leaf.name] == 1
        }

    resolved_policy, policy_error = _resolve_discovery_policy(root, policy)
    if policy_error is not None:
        _diagnostic(
            diagnostics,
            "APG048",
            "policy",
            "discovery-policy-resolution",
            f"discovery policy resolution failed: {policy_error}",
            "supply a valid discovery capacity policy or correct selector",
        )

    declared: list[tuple[str, str]] = []
    for leaf in sorted(canonical_leaves, key=lambda item: item.as_posix()):
        if not leaf.is_symlink():
            _check_leaf(root, leaf, diagnostics, declared, policy=resolved_policy)
    for name, count in sorted(Counter(value for value, _ in declared).items()):
        if count > 1:
            for declared_name, relative in declared:
                if declared_name == name:
                    _diagnostic(
                        diagnostics,
                        "APG013",
                        relative,
                        "unique-frontmatter-name",
                        f"frontmatter name {name!r} is declared by {count} leaves",
                        "give every canonical leaf one unique matching name",
                    )

    if resolved_policy is not None and policy_error is None:
        skills_for_policy: list[dict[str, object]] = []
        for leaf in sorted(canonical_leaves, key=lambda item: item.as_posix()):
            skill_file = leaf / "SKILL.md"
            if leaf.is_symlink() or not _ordinary_file(skill_file):
                continue
            try:
                b_data = skill_file.read_bytes()
                p_res = parse_frontmatter(b_data)
                names = p_res.values("name")
                descs = p_res.values("description")
                s_name = names[0] if names else leaf.name
                s_desc = descs[0] if descs else ""
                skills_for_policy.append(
                    {
                        "name": s_name,
                        "description": s_desc,
                        "bytes": len(s_desc.encode("utf-8")),
                        "characters": len(s_desc),
                        "blob_bytes": len(b_data),
                    }
                )
            except OSError:
                continue

        policy_failures = validate_discovery_policy(resolved_policy, skills_for_policy)
        if resolved_policy == DISCOVERY_POLICY_VERSION_V010 and len(skills_for_policy) != V010_ADMITTED_SKILL_COUNT:
            policy_failures.append("current policy requires exactly 40 admitted leaves including SVG")
        elif resolved_policy == DISCOVERY_POLICY_VERSION_V010_BROWSER_UI and len(skills_for_policy) != V010_BROWSER_UI_ADMITTED_SKILL_COUNT:
            policy_failures.append("current policy requires exactly 42 admitted leaves including browser UI profiles")
        elif resolved_policy == DISCOVERY_POLICY_VERSION_V010_TOOLCHAIN and len(skills_for_policy) != V010_TOOLCHAIN_ADMITTED_SKILL_COUNT:
            policy_failures.append("current policy requires exactly 44 admitted leaves including toolchain profiles")
        elif resolved_policy == DISCOVERY_POLICY_VERSION_V010_BROWSER_RUNTIME and len(skills_for_policy) != V010_BROWSER_RUNTIME_ADMITTED_SKILL_COUNT:
            policy_failures.append("current policy requires exactly 45 admitted leaves including browser runtime profile")
        for failure in policy_failures:
            if "unknown discovery policy" in failure:
                _diagnostic(
                    diagnostics,
                    "APG048",
                    "policy",
                    "unknown-discovery-policy",
                    failure,
                    "use an authorized discovery capacity policy version",
                )
            elif "exceeds reservation ceiling" in failure:
                cand_match = re.search(r"candidate '([^']+)'", failure)
                target_loc = f"skills/{cand_match.group(1)}" if cand_match else "skills"
                _diagnostic(
                    diagnostics,
                    "APG042",
                    target_loc,
                    "v0-10-description-reservation",
                    failure,
                    "shorten description to within reservation ceiling",
                )
            elif "exceeds SVG file limit" in failure or "body bytes" in failure:
                _diagnostic(
                    diagnostics,
                    "APG043",
                    f"skills/{V010_CURRENT_ADMITTED_CANDIDATE}",
                    "svg-file-size-limit",
                    failure,
                    "reduce SVG file size to within limit",
                )
            elif "reservation theft" in failure or "mutated" in failure or "differs" in failure:
                _diagnostic(
                    diagnostics,
                    "APG044",
                    "skills",
                    "original-39-description-freeze",
                    failure,
                    "restore exact frozen description",
                )
            elif "expected" in failure and "leaves" in failure:
                _diagnostic(
                    diagnostics,
                    "APG045",
                    "skills",
                    "v0-10-capacity-count",
                    failure,
                    "restore expected canonical skill count",
                )
            elif "not authorized for admission" in failure or "unauthorized" in failure or "missing required candidate" in failure:
                _diagnostic(
                    diagnostics,
                    "APG046",
                    "skills",
                    "v0-10-unauthorized-admission",
                    failure,
                    "remove unauthorized candidate or restore required candidate",
                )
            elif "missing original 39" in failure:
                _diagnostic(
                    diagnostics,
                    "APG047",
                    "skills",
                    "original-39-preservation",
                    failure,
                    "restore all original 39 skills",
                )
            else:
                _diagnostic(
                    diagnostics,
                    "APG048",
                    "skills",
                    "v0-10-discovery-policy",
                    failure,
                    "satisfy discovery capacity policy constraints",
                )

    if V06_PROFILE_NAMES.intersection(canonical) or V010_ELIGIBLE_CANDIDATES.intersection(canonical):
        blobs: dict[str, bytes] = {}
        for leaf in sorted(canonical_leaves, key=lambda item: item.as_posix()):
            skill_file = leaf / "SKILL.md"
            if leaf.is_symlink() or not _ordinary_file(skill_file):
                continue
            try:
                blobs[_relative(skill_file, root)] = skill_file.read_bytes()
            except OSError:
                continue
        context_report = context_footprint_report(blobs=blobs)
        aggregate_failures: list[str] = []
        if resolved_policy == DISCOVERY_POLICY_VERSION_V010_BROWSER_RUNTIME:
            ceiling = V010_BROWSER_RUNTIME_ADMISSION_CEILING
        elif resolved_policy == DISCOVERY_POLICY_VERSION_V010_TOOLCHAIN:
            ceiling = V010_TOOLCHAIN_ADMISSION_CEILING
        elif resolved_policy == DISCOVERY_POLICY_VERSION_V010_BROWSER_UI:
            ceiling = V010_BROWSER_UI_ADMISSION_CEILING
        elif resolved_policy == DISCOVERY_POLICY_VERSION_V010 or V010_CURRENT_ADMITTED_CANDIDATE in canonical:
            ceiling = V010_CURRENT_SVG_ADMISSION_CEILING
        else:
            ceiling = V06_TOTAL_DESCRIPTION_BYTES_MAXIMUM
        if (
            context_report["total_description_bytes"]
            > ceiling
        ):
            aggregate_failures.append(f"total description bytes exceed {ceiling}")
        if (
            context_report["discoverable_skill_count"]
            != context_report["skill_count"]
        ):
            aggregate_failures.append("discoverable and measured skill counts disagree")
        if context_report["malformed"]:
            aggregate_failures.append("canonical context metadata is malformed")
        if aggregate_failures:
            _diagnostic(
                diagnostics,
                "APG040",
                "skills",
                "v0-6-context-budget",
                "; ".join(aggregate_failures),
                "restore complete discoverable metadata and keep the canonical context report within the frozen capacity ceiling",
            )

    rows = _check_catalog(
        root, skills / "README.md", canonical, diagnostics
    )
    projections = _check_projection(root, canonical, diagnostics)

    apg_skill_topology.check_router_maps(
        root,
        canonical,
        valid_skill_name,
        partial(_diagnostic, diagnostics),
    )
    ordered = tuple(
        sorted(
            diagnostics,
            key=lambda item: (
                item.path,
                item.line or 0,
                item.column or 0,
                item.code,
                item.message,
            ),
        )
    )
    return CheckResult(ordered, len(canonical_leaves), len(rows), projections)


def _embedded_corpus_failure(root: Path) -> str | None:
    """Require the private Go CLI to bind checkout bytes to its embedded corpus."""

    if not (root / "cmd" / "apgr").is_dir() and not (root / "internal" / "skills").is_dir():
        return None
    environment = dict(os.environ)
    environment.pop("APGR_GO_BINARY", None)
    source = os.fspath(root / "src")
    inherited = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = source if not inherited else os.pathsep.join((source, inherited))
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "agentic_praxis_grimoire",
                "skills",
                "verify-corpus",
                "--repository",
                os.fspath(root),
            ],
            cwd=root,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            shell=False,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return apg_skill_topology.format_embedded_corpus_failure(1, error=error)
    return apg_skill_topology.format_embedded_corpus_failure(
        completed.returncode,
        completed.stdout,
        completed.stderr,
    )


def _summary(result: CheckResult) -> dict[str, int]:
    return {
        "canonical_skills": result.canonical_skills,
        "catalog_rows": result.catalog_rows,
        "projections": result.projections,
    }


def render_json(result: CheckResult) -> str:
    """Render deterministic schema-versioned JSON with one terminal newline."""

    payload = {
        "diagnostics": [item.json_value() for item in result.diagnostics],
        "schema_version": 1,
        "status": "pass" if result.passed else "fail",
        "summary": _summary(result),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"


def render_text(result: CheckResult) -> str:
    """Render deterministic human-readable output with safe actions."""

    counts = (
        f"{result.canonical_skills} canonical skills, "
        f"{result.catalog_rows} catalog rows, {result.projections} projections"
    )
    if result.passed:
        return f"PASS APG skill library: {counts}\n"
    lines: list[str] = []
    for item in result.diagnostics:
        location = json.dumps(item.path, ensure_ascii=True)[1:-1]
        if item.line is not None:
            location += f":{item.line}"
            if item.column is not None:
                location += f":{item.column}"
        lines.append(
            f"{location} {item.code} {item.invariant}: {item.message}; "
            f"action: {item.action}"
        )
    noun = "diagnostic" if len(result.diagnostics) == 1 else "diagnostics"
    lines.append(
        f"FAIL APG skill library: {len(result.diagnostics)} {noun}, {counts}"
    )
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    """Build the bounded public command surface."""

    parser = argparse.ArgumentParser(
        prog=COMMAND_NAME,
        description=(
            "Validate the adopted mechanical APG skill-library subset without "
            "repair, Git, network access, or third-party modules. Passing does "
            "not prove semantic quality, authority, privacy, provenance, "
            "discovery, maturity, release completeness, or stable behavior."
        ),
    )
    parser.add_argument(
        "--root",
        type=Path,
        help="APG-shaped repository root (default: repository containing command)",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="deterministic output format (default: text)",
    )
    parser.add_argument(
        "--policy",
        type=str,
        default=None,
        help="explicit discovery capacity policy version (fail-closed if unknown)",
    )
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    """Run the checker and return its documented exit status."""

    parser = build_parser()
    options = parser.parse_args(arguments)
    default_root = Path(__file__).resolve(strict=True).parent.parent
    root = options.root if options.root is not None else default_root
    result = check_library(root, policy=options.policy)
    if result.passed:
        failure = _embedded_corpus_failure(Path(root))
        if failure is not None:
            result = CheckResult(
                (
                    Diagnostic(
                        "APG041",
                        "skills",
                        "go-embedded-corpus-identity",
                        failure,
                        "restore the exact canonical skill bodies and Go embedded corpus identity",
                    ),
                ),
                result.canonical_skills,
                result.catalog_rows,
                result.projections,
            )
    output = render_json(result) if options.format == "json" else render_text(result)
    sys.stdout.write(output)
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
