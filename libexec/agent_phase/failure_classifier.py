"""Provider-result operational failure classifier.

Classifies provider subprocess exit codes, bounded stderr, and stdout into
typed, immutable classifications and bounded operational observations.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, tzinfo
import hashlib
import re
import time
from typing import Mapping

from .dynamic_router import OperationalObservation
from .probes import compute_observation_digest

CLASSIFIER_PRODUCER = "apgr_provider_result_feedback"

DEFAULT_QUOTA_FALLBACK_TTL = 3600.0        # 1 hour
DEFAULT_RATE_LIMIT_FALLBACK_TTL = 300.0    # 5 minutes
DEFAULT_AUTH_FAILURE_TTL = 1800.0          # 30 minutes
DEFAULT_STARTUP_FAILURE_TTL = 300.0        # 5 minutes
DEFAULT_TRANSPORT_FAILURE_TTL = 60.0       # 1 minute
MAX_RESET_HORIZON_SECONDS = 7 * 86400.0    # 7 days

CATEGORY_QUOTA_EXHAUSTED = "quota_exhausted"
CATEGORY_RATE_LIMITED = "rate_limited"
CATEGORY_AUTHENTICATION_UNUSABLE = "authentication_unusable"
CATEGORY_STARTUP_UNAVAILABLE = "startup_unavailable"
CATEGORY_TRANSPORT_FAILURE = "transport_failure"
CATEGORY_UNKNOWN_FAILURE = "unknown_failure"

CLASSIFIER_CATEGORIES = (
    CATEGORY_QUOTA_EXHAUSTED,
    CATEGORY_RATE_LIMITED,
    CATEGORY_AUTHENTICATION_UNUSABLE,
    CATEGORY_STARTUP_UNAVAILABLE,
    CATEGORY_TRANSPORT_FAILURE,
    CATEGORY_UNKNOWN_FAILURE,
)

CONFIDENCE_EXACT = "exact_signature_match"
CONFIDENCE_HEURISTIC = "heuristic_match"
CONFIDENCE_FALLBACK = "fallback_match"

# Classifier category to router observation mapping table (Scope E)
ROUTER_MAPPING_BY_CATEGORY: Mapping[str, tuple[str, str, bool]] = {
    CATEGORY_QUOTA_EXHAUSTED: ("quota", "exhausted", True),
    CATEGORY_AUTHENTICATION_UNUSABLE: ("authentication", "unusable", False),
    CATEGORY_STARTUP_UNAVAILABLE: ("availability", "unavailable", False),
    CATEGORY_RATE_LIMITED: ("cooldown", "active_cooldown", False),
    CATEGORY_TRANSPORT_FAILURE: ("availability", "unavailable", False),
    CATEGORY_UNKNOWN_FAILURE: ("unknown", "unknown", False),
}


@dataclass(frozen=True)
class ProviderFailureClassification:
    category: str
    confidence: str
    provider: str
    profile: str | None
    is_provider_wide: bool
    is_pre_substantive_reroutable: bool
    observations_to_persist: tuple[OperationalObservation, ...]
    sanitized_evidence_excerpt: str
    stdout_sha256: str
    stderr_sha256: str
    exit_code: int
    match_basis: str = "none"
    reset_hint: str | None = None
    parsed_reset_timestamp: float | None = None
    timezone_assumption: str | None = None


def sanitize_evidence(text: str, max_chars: int = 500) -> str:
    """Sanitize and bound error evidence, redacting potential secrets."""
    if not text:
        return ""
    cleaned = re.sub(r"sk-[a-zA-Z0-9_\-]{8,}", "sk-[REDACTED]", text)
    cleaned = re.sub(r"Bearer\s+[a-zA-Z0-9_\-\.]{8,}", "Bearer [REDACTED]", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"(token|secret|password|api[_\-]?key)\s*[:=]\s*['\"]?[a-zA-Z0-9_\-\.]{8,}['\"]?",
        r"\1=[REDACTED]",
        cleaned,
        flags=re.IGNORECASE,
    )
    deduped_lines: list[str] = []
    for line in cleaned.splitlines():
        trimmed = line.strip()
        if not deduped_lines or deduped_lines[-1] != trimmed:
            deduped_lines.append(trimmed)
    merged = "\n".join(deduped_lines).strip()
    if len(merged) > max_chars:
        return merged[:max_chars] + "... [truncated]"
    return merged


def parse_codex_reset_hint(
    hint: str,
    now: float,
    *,
    tz: tzinfo | None = None,
) -> tuple[float | None, str | None]:
    """Parse Codex usage-limit reset hint timestamp deterministically.

    Understands ordinal date patterns, e.g.:
      'Sep 19th, 2026 8:20 AM' or 'Sep 19, 2026 8:20 AM'
    Interprets timezone-less timestamps using host local timezone, recording explicit provenance.
    Rejects past timestamps and caps overly distant timestamps.
    """
    cleaned = hint.strip().rstrip(".")
    cleaned_norm = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", cleaned)

    target_dt: datetime | None = None
    date_patterns = [
        "%b %d, %Y %I:%M %p",
        "%b %d %Y %I:%M %p",
        "%B %d, %Y %I:%M %p",
        "%B %d %Y %I:%M %p",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %I:%M %p",
    ]
    for pat in date_patterns:
        try:
            target_dt = datetime.strptime(cleaned_norm, pat)
            break
        except ValueError:
            continue

    if target_dt is None:
        return None, None

    if tz is None:
        local_tz = datetime.now().astimezone().tzinfo or timezone.utc
        tz_name = getattr(local_tz, "key", str(local_tz))
        tz_provenance = f"host_local_timezone:{tz_name}"
        target_dt = target_dt.replace(tzinfo=local_tz)
    else:
        tz_name = getattr(tz, "key", str(tz))
        tz_provenance = f"explicit_timezone:{tz_name}"
        target_dt = target_dt.replace(tzinfo=tz)

    parsed_epoch = target_dt.timestamp()

    # Reject past hints
    if parsed_epoch <= now:
        return None, tz_provenance

    # Bound maximum reset horizon to 7 days
    if (parsed_epoch - now) > MAX_RESET_HORIZON_SECONDS:
        return now + MAX_RESET_HORIZON_SECONDS, tz_provenance

    return parsed_epoch, tz_provenance


def _extract_codex_reset_hint(text: str) -> str | None:
    """Extract reset timestamp hint string from Codex usage limit error message."""
    m = re.search(r"try again at\s+([^.\n]+)", text, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


def is_recognized_codex_quota_banner_only(stdout_bytes: bytes) -> bool:
    """Check if stdout is non-empty but wholly consists of the recognized Codex usage-limit banner.
    
    Per Scope B/G and Finding F1, if stdout contains only this banner it is pre-substantive.
    If stdout contains agent prose/output in addition to the banner, it is substantive.
    """
    text = stdout_bytes.decode("utf-8", errors="replace").strip()
    if not text:
        return False
    text_lower = text.lower()
    if not ("hit your usage limit" in text_lower or "usage limit. visit" in text_lower) or "codex/settings/usage" not in text_lower:
        return False
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    non_banner_lines = []
    for line in lines:
        lowered = line.lower()
        if (
            "hit your usage limit" in lowered
            or "codex/settings/usage" in lowered
            or "purchase more credits" in lowered
            or "try again at" in lowered
            or lowered.startswith("error:")
        ):
            continue
        non_banner_lines.append(line)
    return len(non_banner_lines) == 0


def classify_provider_result(
    provider: str,
    *,
    profile: str | None = None,
    exit_code: int,
    stdout: bytes = b"",
    stderr: bytes = b"",
    attempt_id: str = "attempt-unknown",
    now: float | None = None,
    tz: tzinfo | None = None,
) -> ProviderFailureClassification:
    """Classify a nonzero provider subprocess exit with high-confidence signature matching."""
    ref_now = time.time() if now is None else float(now)
    stdout_sha256 = hashlib.sha256(stdout).hexdigest()
    stderr_sha256 = hashlib.sha256(stderr).hexdigest()

    err_text = stderr.decode("utf-8", errors="replace")
    out_text = stdout.decode("utf-8", errors="replace")
    combined_err = (err_text + "\n" + out_text).strip()
    sanitized_excerpt = sanitize_evidence(combined_err or f"Exit {exit_code}")

    category = CATEGORY_UNKNOWN_FAILURE
    confidence = CONFIDENCE_FALLBACK
    match_basis = "fallback"
    is_provider_wide = False
    is_reroutable = False
    obs_type = "unknown"
    state_value = "unknown"
    ttl = DEFAULT_QUOTA_FALLBACK_TTL
    reset_hint: str | None = None
    parsed_reset_ts: float | None = None
    tz_assumption: str | None = None

    prov = provider.lower().strip()

    if prov == "codex":
        # Captured exact Codex Quota Exhaustion signature:
        # "ERROR: You've hit your usage limit. Visit https://chatgpt.com/codex/settings/usage to purchase more credits or try again at Sep 19th, 2026 8:20 AM."
        # Per Scope B / HIGH-1, only check stderr directly or stdout ONLY IF stdout strictly consists
        # of the recognized banner. Agent-controlled model prose on stdout is never provider authority.
        codex_err_match = (
            ("hit your usage limit" in err_text.lower() or "usage limit. visit" in err_text.lower())
            and "codex/settings/usage" in err_text.lower()
        )
        codex_stdout_match = is_recognized_codex_quota_banner_only(stdout)
        if codex_err_match or codex_stdout_match:
            category = CATEGORY_QUOTA_EXHAUSTED
            confidence = CONFIDENCE_EXACT
            match_basis = "codex_usage_limit_signature"
            is_provider_wide = True
            is_reroutable = True
            banner_source = err_text if codex_err_match else out_text
            reset_hint = _extract_codex_reset_hint(banner_source)
            if reset_hint:
                parsed_reset_ts, tz_assumption = parse_codex_reset_hint(reset_hint, ref_now, tz=tz)
            ttl = (parsed_reset_ts - ref_now) if parsed_reset_ts is not None else DEFAULT_QUOTA_FALLBACK_TTL

    # Scope E: derive observation type, state value, and base reroutability from mapping table
    obs_type, state_value, _ = ROUTER_MAPPING_BY_CATEGORY.get(
        category, ("unknown", "unknown", False)
    )
    if confidence != CONFIDENCE_EXACT:
        is_reroutable = False

    observations_to_persist: list[OperationalObservation] = []

    # Only CONFIDENCE_EXACT classifications yield routing-visible persisted observations
    if confidence == CONFIDENCE_EXACT and is_reroutable and category != CATEGORY_UNKNOWN_FAILURE:
        expires_at = ref_now + max(1.0, float(ttl))
        obs_profile = None if is_provider_wide else profile
        obs_id = f"obs-result-{category}-{prov}-{attempt_id}"
        obs_detail = {
            "attempt_id": attempt_id,
            "category": category,
            "confidence": confidence,
            "match_basis": match_basis,
            "exit_code": exit_code,
            "reset_hint": reset_hint,
            "parsed_reset_timestamp": parsed_reset_ts,
            "timezone_assumption": tz_assumption,
            "evidence_excerpt": sanitized_excerpt,
            "stderr_sha256": stderr_sha256,
            "stdout_sha256": stdout_sha256,
        }
        digest = compute_observation_digest(
            obs_id,
            CLASSIFIER_PRODUCER,
            obs_type,
            prov,
            state_value,
            profile=obs_profile,
            timestamp=ref_now,
            expires_at=expires_at,
            detail=obs_detail,
        )
        observations_to_persist.append(
            OperationalObservation(
                observation_id=obs_id,
                producer=CLASSIFIER_PRODUCER,
                observation_type=obs_type,
                provider=prov,
                profile=obs_profile,
                timestamp=ref_now,
                expires_at=expires_at,
                state_value=state_value,
                digest=digest,
                detail=obs_detail,
            )
        )

    return ProviderFailureClassification(
        category=category,
        confidence=confidence,
        provider=prov,
        profile=None if is_provider_wide else profile,
        is_provider_wide=is_provider_wide,
        is_pre_substantive_reroutable=is_reroutable,
        observations_to_persist=tuple(observations_to_persist),
        sanitized_evidence_excerpt=sanitized_excerpt,
        stdout_sha256=stdout_sha256,
        stderr_sha256=stderr_sha256,
        exit_code=exit_code,
        match_basis=match_basis,
        reset_hint=reset_hint,
        parsed_reset_timestamp=parsed_reset_ts,
        timezone_assumption=tz_assumption,
    )
