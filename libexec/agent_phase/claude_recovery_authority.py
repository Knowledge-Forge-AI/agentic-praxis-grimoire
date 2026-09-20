"""Exact physical acquisition subtree; never a caller-selected directory grant."""
import hashlib
from pathlib import Path
import stat

from .transmission import direct_bytes


def physical(path, *, directory=False):
    path = Path(path)
    if not path.is_absolute() or path.resolve(strict=True) != path:
        raise ValueError("nonphysical acquisition path")
    value = path.lstat()
    if not (stat.S_ISDIR(value.st_mode) if directory else stat.S_ISREG(value.st_mode)):
        raise ValueError("nonregular acquisition authority")
    return {"device": value.st_dev, "inode": value.st_ino, "mode": stat.S_IMODE(value.st_mode)}


def file_identity(path):
    before = physical(path)
    data = direct_bytes(path, utf8=False, max_bytes=128 << 20)
    if physical(path) != before:
        raise ValueError("acquisition identity changed during read")
    return {**before, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def capture(run_dir, expected):
    run_dir = Path(run_dir)
    run_identity = physical(run_dir, directory=True)
    root = run_dir / "acquisitions/skills"
    root_identity = physical(root, directory=True)
    files, directories = {}, {}
    for path in sorted(root.rglob("*")):
        if len(files) + len(directories) >= 20000:
            raise ValueError("recovery inventory exceeds bound")
        name = str(path.relative_to(run_dir))
        if path.is_dir() and not path.is_symlink():
            directories[name] = physical(path, directory=True)
        else:
            files[name] = file_identity(path)
    observed = {k: {f: v[f] for f in ("bytes", "sha256")} for k, v in files.items()}
    if not expected or observed != expected:
        raise ValueError("recovery subtree differs from exact selected inventory")
    allowed_directories = {str(parent) for name in expected for parent in Path(name).parents
                           if str(parent).startswith("acquisitions/skills/")}
    if set(directories) != allowed_directories:
        raise ValueError("unrelated recovery directory")
    if physical(root, directory=True) != root_identity or physical(run_dir, directory=True) != run_identity:
        raise ValueError("recovery root changed during capture")
    return {"path": str(root), "run_identity": run_identity, "root_identity": root_identity,
            "directories": directories, "files": files}


def verify(run_dir, authority):
    expected = {k: {f: v[f] for f in ("bytes", "sha256")} for k, v in authority["files"].items()}
    if capture(run_dir, expected) != authority:
        raise ValueError("recovery physical identity drift")
    return authority
