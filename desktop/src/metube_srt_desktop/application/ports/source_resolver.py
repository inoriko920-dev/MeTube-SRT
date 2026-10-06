from __future__ import annotations

from typing import Protocol

from metube_srt_desktop.application.dto.download import ResolvedSource, ResolveRequest


class SourceResolveError(RuntimeError):
    """Application-owned sanitized source-resolution failure."""

    def __init__(self, error_code: str, message: str) -> None:
        if not error_code.strip():
            raise ValueError("error_code must be non-empty")
        if not message.strip():
            raise ValueError("message must be non-empty")
        super().__init__(message)
        self.error_code = error_code
        self.message = message


class SourceResolverPort(Protocol):
    """Application-owned boundary for metadata-only source resolution."""

    def resolve(self, request: ResolveRequest) -> ResolvedSource:
        """Resolve one URL without downloading media."""
        ...
