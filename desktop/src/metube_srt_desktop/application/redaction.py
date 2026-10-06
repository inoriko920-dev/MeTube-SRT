from __future__ import annotations

import re
from dataclasses import dataclass

_REDACTED = "[SECRET DISEMBUNYIKAN]"

_API_KEY_PATTERN = re.compile(r"AIza[0-9A-Za-z_-]{20,}")
_BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+\-/]{12,}=*")
_BASIC_AUTH_URL_PATTERN = re.compile(
    r"(?i)\b(https?://)([^/\s:@]+):([^@\s/]+)@"
)
_NAMED_SECRET_PATTERN = re.compile(
    r"(?i)\b("
    r"api[_ -]?key|"
    r"access[_ -]?token|"
    r"refresh[_ -]?token|"
    r"client[_ -]?secret|"
    r"token|authorization|cookie|password|passwd|secret"
    r")\s*[:=]\s*([^\s,;]+)"
)


@dataclass(frozen=True, slots=True)
class RedactionResult:
    text: str
    secret_detected: bool


def redact_sensitive_text(value: str) -> RedactionResult:
    """Redact common credential shapes before UI/provider serialization."""

    redacted = value
    detected = False

    redacted, count = _API_KEY_PATTERN.subn(_REDACTED, redacted)
    detected = detected or count > 0

    redacted, count = _BEARER_PATTERN.subn(_REDACTED, redacted)
    detected = detected or count > 0

    redacted, count = _BASIC_AUTH_URL_PATTERN.subn(
        lambda match: f"{match.group(1)}{_REDACTED}@",
        redacted,
    )
    detected = detected or count > 0

    redacted, count = _NAMED_SECRET_PATTERN.subn(
        lambda match: f"{match.group(1)}={_REDACTED}",
        redacted,
    )
    detected = detected or count > 0

    return RedactionResult(text=redacted, secret_detected=detected)
