"""Build provider process environments without leaking ambient values."""
import os
from pathlib import Path
from typing import Sequence


def process_options(argv, environment, transport, *, managed, activity_key):
    """Return Popen options and owned activity descriptors.

    Validate before acquiring descriptors and close them if transport enrichment
    fails. An explicit environment replaces the ambient environment entirely.
    """
    if environment is not None and any(
        not isinstance(key, str) or not isinstance(value, str)
        for key, value in environment.items()
    ):
        raise TypeError("provider environment must contain string keys and values")
    values = dict(os.environ if environment is None else environment)
    options = {"env": {key: value for key, value in values.items()
                       if not key.startswith("AGENT_CENTRAL_")}}
    read_fd = write_fd = None
    try:
        if managed:
            read_fd, write_fd = os.pipe()
            values = dict(options.get("env", os.environ))
            values[activity_key] = str(write_fd)
            options.update(env=values, pass_fds=(write_fd,))
        if transport is not None:
            options["env"] = transport.environment(argv, options.get("env", os.environ))
        return options, read_fd, write_fd
    except BaseException:
        for descriptor in (read_fd, write_fd):
            if descriptor is not None:
                os.close(descriptor)
        raise


def is_managed_antigravity_launcher(argv: Sequence[str], cwd: Path, launcher: str) -> bool:
    """Recognize only this checkout's Antigravity wrapper for activity wiring."""
    if not argv:
        return False
    candidate = Path(argv[0])
    if not candidate.is_absolute():
        candidate = cwd / candidate
    managed = Path(__file__).resolve().parents[2] / launcher
    try:
        return candidate.resolve(strict=False) == managed.resolve(strict=False)
    except OSError:
        return False
