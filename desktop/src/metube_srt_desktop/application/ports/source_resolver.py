from __future__ import annotations

from typing import Protocol

from metube_srt_desktop.application.dto.download import ResolveRequest, ResolvedSource


class SourceResolverPort(Protocol):
    """Application-owned boundary for metadata-only source resolution."""

    def resolve(self, request: ResolveRequest) -> ResolvedSource:
        """Resolve one URL without downloading media."""
        ...
