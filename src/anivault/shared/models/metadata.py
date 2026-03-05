"""Presentation layer metadata models for AniVault.

Re-exports from domain.entities for backward compatibility.
"""

from __future__ import annotations

from anivault.domain.entities.metadata import FileMetadata, TMDBMatchResult

__all__ = ["FileMetadata", "TMDBMatchResult"]
