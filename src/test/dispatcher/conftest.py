from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType


ROOT = Path(__file__).resolve().parents[3]
LIBEXEC = ROOT / "libexec"
if str(LIBEXEC) not in sys.path:
    sys.path.insert(0, str(LIBEXEC))


def load_module(relative_path: str, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
