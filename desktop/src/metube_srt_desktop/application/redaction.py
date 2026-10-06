from __future__ import annotations

import re
from dataclasses import dataclass

_REDACTED = "[SECRET DISEMBUNYIKAN]"

_PATTERNS = (
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+\-/]{12,}=*"),
    re.compile(
        r"(?i)\b(api[_ -]?key|token|authorization|cookie)\s*[:=]\s*([^\s,;]+)"
    ),
)


@dataclass(frozen=True, slots=True)
class RedactionResult:
    text: str
    secret_detected: bool


def redact_sensitive_text(value: str) -> RedactionResult:
    """Redact common credential shapes before UI/provider serialization."""

    redacted = value
    detected = False

    for pattern in _PATTERNS:
        if not pattern.search(redacted):
            continue
        detected = True
        if pattern is _PATTERNS[2]:
            redacted = pattern.sub(lambda match: f"{match.group(1)}={_REDACTED}", redacted)
        else:
            redacted = pattern.sub(_REDACTED, redacted)

    return RedactionResult(text=redacted, secret_detected=detected)
