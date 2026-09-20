"""One unavailable RTK resolution shape for optional integration failures."""

from types import SimpleNamespace


def unavailable_rtk_resolution(error_text: str) -> SimpleNamespace:
    diagnostic = f"rtk resolution failed: {error_text}"
    return SimpleNamespace(
        status="unavailable",
        diagnostics=[diagnostic],
        providers={
            name: {"declared_mode": "off", "effective_mode": "off", "reason": "rtk_unavailable"}
            for name in ("claude", "codex", "antigravity")
        },
        configured_executable=None,
        resolved_executable=None,
        as_dict=lambda d=diagnostic: {"status": "unavailable", "diagnostics": [d]},
    )
