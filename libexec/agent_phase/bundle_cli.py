#!/usr/bin/env python3
"""APGR Dispatcher Bundle Utility (Generation 8).

Manages capture, atomic projection, verification, and inspection of the
canonical six-member dispatcher configuration bundle.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import json
import os
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[2]

from agent_phase.bundle import (
    BUNDLE_GENERATION,
    BUNDLE_MEMBERS,
    BUNDLE_SCHEMA,
    MANIFEST_FILENAME,
    BundleError,
    BundleGenerationError,
    BundleNotFoundError,
    BundleTamperError,
    LegacyBundleError,
    capture_bundle,
    load_bundle,
    publish_bundle,
    verify_bundle,
)
from agent_phase.config_routing import resolve_global_home


def cmd_capture(args: argparse.Namespace) -> int:
    source_dir = Path(args.source_dir).resolve() if args.source_dir else (_ROOT / "common" / "dispatcher")
    try:
        members, manifest = capture_bundle(source_dir, expected_generation=args.generation)
    except BundleError as error:
        sys.stderr.write(f"capture error: {error}\n")
        return 1

    if args.output_manifest:
        out_path = Path(args.output_manifest).resolve()
        out_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"Captured {len(members)} bundle members to manifest: {out_path}")
    else:
        print(f"Successfully captured {len(members)} bundle members (generation {manifest['generation']}):")
        for name in sorted(members):
            m = members[name]
            print(f"  {name:20s} sha256={m.sha256[:12]}... ({m.size} bytes)")
    return 0


def cmd_project(args: argparse.Namespace) -> int:
    source_dir = Path(args.source_dir).resolve() if args.source_dir else (_ROOT / "common" / "dispatcher")
    if args.target_dir:
        target_dir = Path(args.target_dir).absolute()
    else:
        home = resolve_global_home(args.apgr_home)
        target_dir = home / "dispatcher"

    try:
        snapshot = publish_bundle(source_dir, target_dir, expected_generation=args.generation)
    except BundleError as error:
        sys.stderr.write(f"publish error: {error}\n")
        return 1

    print(f"Atomically projected bundle (generation {snapshot.generation}) to {target_dir}:")
    for name, m in sorted(snapshot.members.items()):
        print(f"  {name:20s} sha256={m.sha256[:12]}... ({m.size} bytes)")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    if args.bundle_dir:
        bundle_dir = Path(args.bundle_dir).absolute()
    else:
        home = resolve_global_home(args.apgr_home)
        bundle_dir = home / "dispatcher"

    try:
        manifest = verify_bundle(bundle_dir, expected_generation=args.generation)
    except LegacyBundleError as error:
        sys.stderr.write(f"legacy migration error: {error}\n")
        return 1
    except BundleTamperError as error:
        sys.stderr.write(f"tamper error: {error}\n")
        return 1
    except BundleGenerationError as error:
        sys.stderr.write(f"generation error: {error}\n")
        return 1
    except BundleError as error:
        sys.stderr.write(f"verification error: {error}\n")
        return 1

    print(f"Verified bundle at {bundle_dir} (generation {manifest['generation']}):")
    files = manifest.get("files", {})
    for name in sorted(files):
        entry = files[name]
        sha = entry.get("sha256", "") if isinstance(entry, dict) else entry
        print(f"  {name:20s} sha256={sha[:12]}... OK")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    bundle_path = args.bundle_dir or args.source_dir
    if bundle_path:
        target_override = Path(bundle_path).absolute()
    else:
        target_override = None

    try:
        snapshot = load_bundle(
            apgr_home=args.apgr_home,
            repo_root=_ROOT,
            required=args.required,
            target_override=target_override,
        )
    except BundleError as error:
        sys.stderr.write(f"load error: {error}\n")
        return 1

    if args.json:
        data = {
            "generation": snapshot.generation,
            "bundle_dir": str(snapshot.bundle_dir),
            "manifest": dict(snapshot.manifest),
            "worker_policy": snapshot.worker_policy.as_dict(),
            "members": {name: m.sha256 for name, m in snapshot.members.items()},
        }
        print(json.dumps(data, indent=2, sort_keys=True, default=lambda o: dict(o) if isinstance(o, Mapping) else str(o)))
    else:
        print(f"Dispatcher Bundle Snapshot (Generation {snapshot.generation}):")
        print(f"  Directory: {snapshot.bundle_dir}")
        print(f"  Worker Policy: {snapshot.worker_policy.name} "
              f"(Gemini={snapshot.worker_policy.max_gemini}, Luna={snapshot.worker_policy.max_luna}, "
              f"borrowing={snapshot.worker_policy.borrowing})")
        print("  Members:")
        for name, m in sorted(snapshot.members.items()):
            print(f"    {name:20s} sha256={m.sha256[:12]}... ({m.size} bytes)")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="APGR Dispatcher Bundle Management Utility (Generation 8)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # capture
    p_capture = subparsers.add_parser("capture", help="Capture and validate bundle members")
    p_capture.add_argument("--source-dir", "-s", help="Source directory containing the 6 TOML files")
    p_capture.add_argument("--generation", "-g", type=int, default=None, help="Expected generation")
    p_capture.add_argument("--output-manifest", "-o", help="Write bundle.json manifest to this path")

    # project / publish
    p_project = subparsers.add_parser("project", aliases=["publish"], help="Atomically project bundle to target directory")
    p_project.add_argument("--source-dir", "-s", help="Source directory containing the 6 TOML files")
    p_project.add_argument("--target-dir", "-t", help="Target bundle directory (defaults to <APGR_HOME>/dispatcher)")
    p_project.add_argument("--apgr-home", help="Explicit APGR_HOME path")
    p_project.add_argument("--generation", "-g", type=int, default=None, help="Expected generation")

    # verify
    p_verify = subparsers.add_parser("verify", help="Verify bundle integrity and manifest hashes")
    p_verify.add_argument("--bundle-dir", "-b", help="Bundle directory to verify (defaults to <APGR_HOME>/dispatcher)")
    p_verify.add_argument("--apgr-home", help="Explicit APGR_HOME path")
    p_verify.add_argument("--generation", "-g", type=int, default=None, help="Expected generation")

    # show
    p_show = subparsers.add_parser("show", aliases=["status", "info"], help="Display bundle status and metadata")
    p_show.add_argument("--bundle-dir", "-b", help="Bundle directory to show")
    p_show.add_argument("--source-dir", "-s", help="Source directory containing bundle files")
    p_show.add_argument("--apgr-home", help="Explicit APGR_HOME path")
    p_show.add_argument("--required", action="store_true", default=None, help="Require captured home bundle (disable fallback)")
    p_show.add_argument("--json", action="store_true", help="Output JSON format")

    args = parser.parse_args(argv)

    if args.command == "capture":
        return cmd_capture(args)
    elif args.command in ("project", "publish"):
        return cmd_project(args)
    elif args.command == "verify":
        return cmd_verify(args)
    elif args.command in ("show", "status", "info"):
        return cmd_show(args)
    else:
        sys.stderr.write(f"unknown command: {args.command}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
