"""Provider-specific prompt transport bounds."""

from __future__ import annotations

from collections.abc import Callable

from antigravity_profile import MAX_PROMPT_BYTES as ANTIGRAVITY_MAX_PROMPT_BYTES

from .envelope import RenderedPrompt
from .routing import Endpoint, PROVIDER_ANTIGRAVITY


class PromptLimitError(RuntimeError):
    """A rendered provider prompt exceeds its transport contract."""


def ensure_prompt_fits(
    stage: str, endpoint: Endpoint, rendered: RenderedPrompt
) -> None:
    if (
        endpoint.provider == PROVIDER_ANTIGRAVITY
        and len(rendered.data) > ANTIGRAVITY_MAX_PROMPT_BYTES
    ):
        raise PromptLimitError(
            f"stage {stage} prompt is {len(rendered.data)} bytes; "
            f"Antigravity accepts at most {ANTIGRAVITY_MAX_PROMPT_BYTES}"
        )


def preflight_closeout_capacity(
    endpoint: Endpoint, render: Callable[[str], RenderedPrompt]
) -> None:
    if endpoint.provider != PROVIDER_ANTIGRAVITY:
        return
    ensure_prompt_fits("closeout", endpoint, render(""))
