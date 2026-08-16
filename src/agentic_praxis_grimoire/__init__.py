"""Agentic Praxis Grimoire's installed Python package.

The package-owned ``VERSION`` resource is mandatory: corrupt or incomplete
installations intentionally fail before any command is dispatched.
"""

from .version import VERSION, __version__

__all__ = ["VERSION", "__version__"]
