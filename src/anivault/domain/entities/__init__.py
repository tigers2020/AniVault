"""Domain entities (Phase 5)."""

from anivault.domain.entities.metadata import FileMetadata, TMDBMatchResult
from anivault.domain.entities.parser import ParsingAdditionalInfo, ParsingResult

__all__ = [
    "FileMetadata",
    "ParsingAdditionalInfo",
    "ParsingResult",
    "TMDBMatchResult",
]
