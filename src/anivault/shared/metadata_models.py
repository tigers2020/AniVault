"""Compatibility shim for presentation metadata models.

DEPRECATED: Prefer ``from anivault.shared.models.metadata import FileMetadata, TMDBMatchResult``.
This module is kept for backward compatibility and may be removed in a future release.
"""

from anivault.shared.models.metadata import FileMetadata, TMDBMatchResult

__all__ = ["FileMetadata", "TMDBMatchResult"]
