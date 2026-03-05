"""AniVault Domain Layer (Phase 5).

Clean Architecture domain layer with entities and interfaces.
No external dependencies - pure business logic.
"""

from anivault.domain.entities import FileMetadata, ParsingAdditionalInfo, ParsingResult, TMDBMatchResult

__all__ = [
    "FileMetadata",
    "ParsingAdditionalInfo",
    "ParsingResult",
    "TMDBMatchResult",
]
