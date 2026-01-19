"""Shared parser output models."""

from __future__ import annotations

from dataclasses import dataclass, field

from anivault.shared.models.metadata import TMDBMatchResult


@dataclass
class ParsingAdditionalInfo:
    """Additional information extracted during parsing."""

    match_result: TMDBMatchResult | None = None
    error: str | None = None
    parser_specific: dict[str, object] = field(default_factory=dict)


@dataclass
class ParsingResult:
    """Result of parsing an anime filename."""

    title: str
    episode: int | None = None
    season: int | None = None
    year: int | None = None
    quality: str | None = None
    source: str | None = None
    codec: str | None = None
    audio: str | None = None
    release_group: str | None = None
    confidence: float = 0.0
    parser_used: str = "unknown"
    additional_info: ParsingAdditionalInfo = field(default_factory=ParsingAdditionalInfo)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            msg = f"Confidence must be between 0.0 and 1.0, got {self.confidence}"
            raise ValueError(msg)

    def is_valid(self) -> bool:
        """Check if the parsing result contains essential information."""
        return bool(self.title and self.title.strip())

    def has_episode_info(self) -> bool:
        """Check if the result contains episode information."""
        return self.episode is not None

    def has_season_info(self) -> bool:
        """Check if the result contains season information."""
        return self.season is not None


__all__ = ["ParsingAdditionalInfo", "ParsingResult"]
