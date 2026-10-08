"""Explicit catalog operation: Python config ownership, Go catalog selection."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path
import sys

from . import go_bridge
from .config import ConfigError, load_config
from .paths import discover_project_root, global_config_path, project_config_path, resolve_global_home


def list_catalog(arguments: list[str], options: dict[str, str]) -> int:
    parser = argparse.ArgumentParser(prog="apgr skills list")
    parser.add_argument("--all-sources", action="store_true", required=True)
    parser.add_argument("--project-root", default=options.get("project_root"))
    parser.add_argument("--apgr-home", default=options.get("apgr_home"))
    parser.add_argument("--start", type=Path, default=Path.cwd())
    formats = parser.add_mutually_exclusive_group()
    formats.add_argument("--json", action="store_true")
    formats.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(arguments)
    request, argv = capture_catalog(args.start, args.project_root, args.apgr_home)
    result = go_bridge.run_capture(argv, repository_root=None, input_bytes=json.dumps(request).encode())
    if result.returncode:
        sys.stderr.buffer.write(result.stderr)
        return result.returncode
    catalog = json.loads(result.stdout)
    if args.json or args.format == "json":
        print(json.dumps(catalog, indent=2, sort_keys=True))
    else:
        for descriptor in catalog["skills"]:
            print(descriptor["qualified_id"])
        available = {row["qualified_id"] for row in catalog["skills"]}
        for relation in catalog["overrides"] or []:
            status = "available" if relation["selected"] in available else "unavailable"
            print(f'override {relation["requested"]} -> {relation["selected"]} '
                  f'[{status}] config={relation["config_path"]} sha256={relation["config_sha256"]}')
        for source in catalog["sources"] or []:
            print(f'source {source["source"]}: {source["status"]}')
        for diagnostic in catalog["diagnostics"] or []:
            print(f'diagnostic {diagnostic["identity"]}: {diagnostic["message"]}')
    return 0


def capture_catalog(start: Path, project_root=None, apgr_home=None):
    """Capture the exact project override authority shared by catalog channels."""
    project = discover_project_root(start.absolute(), explicit=project_root)
    home = resolve_global_home(apgr_home)
    request: dict[str, object] = {"schema_version": "apg.skill-catalog/v1", "overrides": [], "sources": []}
    # Global mappings never authorize replacement. Report an existing global
    # config without parsing it or making its validity a catalog prerequisite.
    global_path = global_config_path(home)
    try:
        global_path.lstat()
    except FileNotFoundError:
        pass
    except OSError:
        request["diagnostics"] = [{"identity": "global-configuration", "path": str(global_path),
                                   "message": "global configuration unavailable; overrides are project-only"}]
    else:
        request["diagnostics"] = [{"identity": "global-configuration", "path": str(global_path),
                                   "message": "global configuration not consulted; skills.overrides applies only in project configuration"}]
    argv = ["skills", "catalog", "--stdin", "--apgr-home", str(home)]
    if project is None:
        request["sources"] = [{"source": "project", "selected_root": "", "resolved_root": "", "status": "not-selected"}]
    if project is not None:
        argv.extend(["--project-root", str(project_root or project)])
        config_path = project_config_path(project)
        # Use the same exact byte snapshot for TOML and provenance. Configuration
        # is never sought in an ancestor or global home for replacement authority.
        try:
            before = config_path.lstat()
        except FileNotFoundError:
            before = None
        if before is not None:
            if not stat.S_ISREG(before.st_mode) or before.st_size > 1 << 20:
                raise ConfigError("catalog configuration is not a bounded regular file")
            try:
                config_path.resolve().relative_to(project)
            except ValueError as error:
                raise ConfigError("catalog configuration escapes project") from error
            descriptor = os.open(config_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(descriptor, "rb") as stream:
                opened = os.fstat(stream.fileno())
                data = stream.read((1 << 20) + 1)
                after = os.fstat(stream.fileno())
            entry = config_path.lstat()
            identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
            if len(data) > 1 << 20 or not identity(before) == identity(opened) == identity(after) == identity(entry):
                raise ConfigError("catalog configuration changed during capture")
            config = load_config(config_path, raw_bytes=data)
            digest = hashlib.sha256(data).hexdigest()
            request["overrides"] = [
                {"requested": key, "selected": value, "config_path": str(config_path), "config_sha256": digest}
                for key, value in sorted(config.get("skills", {}).get("overrides", {}).items())
            ]
    return request, argv
