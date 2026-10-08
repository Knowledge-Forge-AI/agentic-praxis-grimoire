"""Closed Python-owned context capture; no optional planner imports or probes."""
from __future__ import annotations

import hashlib
from pathlib import Path
from .config_routing import (
    discover_project_root, global_config_path, load_config_file,
    project_config_path, resolve_global_home,
)


def capture_context_config(*, project_root=None, start=None, apgr_home=None):
    """Capture each config once; project values override home values per key."""
    project = Path(project_root).expanduser().resolve() if project_root is not None else discover_project_root(start)
    home = resolve_global_home(apgr_home)
    result = {"mode": "static"}
    observations = {}
    provenance = []
    overrides = []
    paths = [("home", global_config_path(home))]
    if project is not None:
        paths.append(("project", project_config_path(project)))
    for source, path in paths:
        if not path.is_file():
            continue
        raw = path.read_bytes()
        values = load_config_file(path, raw_bytes=raw)
        digest = hashlib.sha256(raw).hexdigest()
        context = values.get("dispatcher", {}).get("context", {})
        result.update(context)
        observations.update(values.get("dispatcher", {}).get("observations", {}))
        provenance.append({"source": source, "path": str(path), "sha256": digest, "context": dict(context)})
        if source == "project":
            overrides = [{"requested": k, "selected": v, "config_path": str(path), "config_sha256": digest}
                         for k, v in sorted(values.get("skills", {}).get("overrides", {}).items())]
    return {"settings": result, "observations": observations,
            "provenance": provenance, "overrides": overrides,
            "project_root": str(project) if project else None, "apgr_home": str(home)}
