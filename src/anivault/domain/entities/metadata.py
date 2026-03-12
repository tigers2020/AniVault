"""Domain metadata entities (Phase 5).

Presentation layer metadata models - canonical location.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from anivault.domain.constants.entity_validation import (
    EMPTY_FILE_TYPE_ERROR,
    EMPTY_TITLE_ERROR,
    EPISODE_NEGATIVE_ERROR_TEMPLATE,
    MAX_VOTE_AVERAGE,
    MAX_YEAR,
    MIN_VOTE_AVERAGE,
    MIN_YEAR,
    SEASON_NEGATIVE_ERROR_TEMPLATE,
    VOTE_AVERAGE_RANGE_ERROR_TEMPLATE,
    YEAR_RANGE_ERROR_TEMPLATE,
)


@dataclass
class FileMetadata:
    """Lightweight metadata model for presentation layer (GUI/CLI)."""

    # Required fields
    title: str
    file_path: Path
    file_type: str

    # Optional core fields
    year: int | None = None
    season: int | None = None
    episode: int | None = None

    # TMDB enrichment fields
    genres: list[str] = field(default_factory=list)
    overview: str | None = None
    poster_path: str | None = None
    vote_average: float | None = None
    tmdb_id: int | None = None
    media_type: str | None = None
    match_confidence: float | None = None  # 0.0-1.0 from matching engine

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        self._validate_required_fields()
        self._validate_year()
        self._validate_season()
        self._validate_episode()
        self._validate_vote_average()
        self._validate_match_confidence()

    def _validate_required_fields(self) -> None:
        if not self.title:
            raise ValueError(EMPTY_TITLE_ERROR)
        if not self.file_type:
            raise ValueError(EMPTY_FILE_TYPE_ERROR)

    def _validate_year(self) -> None:
        if self.year is None:
            return
        if self.year < MIN_YEAR or self.year > MAX_YEAR:
            raise ValueError(YEAR_RANGE_ERROR_TEMPLATE.format(year=self.year))

    def _validate_season(self) -> None:
        if self.season is not None and self.season < 0:
            raise ValueError(SEASON_NEGATIVE_ERROR_TEMPLATE.format(season=self.season))

    def _validate_episode(self) -> None:
        if self.episode is not None and self.episode < 0:
            raise ValueError(EPISODE_NEGATIVE_ERROR_TEMPLATE.format(episode=self.episode))

    def _validate_vote_average(self) -> None:
        if self.vote_average is None:
            return
        if not MIN_VOTE_AVERAGE <= self.vote_average <= MAX_VOTE_AVERAGE:
            raise ValueError(VOTE_AVERAGE_RANGE_ERROR_TEMPLATE.format(vote_average=self.vote_average))

    def _validate_match_confidence(self) -> None:
        if self.match_confidence is None:
            return
        if not 0.0 <= self.match_confidence <= 1.0:
            msg = f"match_confidence must be between 0.0 and 1.0, got {self.match_confidence}"
            raise ValueError(msg)

    @property
    def display_name(self) -> str:
        """Get formatted display name with season/episode info."""
        parts = [self.title]

        if self.season is not None and self.episode is not None:
            season_str = f"S{self.season:02d}"
            episode_str = f"E{self.episode:02d}"
            parts.append(f"{season_str}{episode_str}")
        elif self.episode is not None:
            parts.append(f"E{self.episode:02d}")
        elif self.year is not None:
            parts.append(f"({self.year})")

        return " ".join(parts)

    @property
    def file_name(self) -> str:
        """Get the filename without path."""
        return self.file_path.name


@dataclass
class TMDBMatchResult:
    """TMDB API match result for anime files."""

    id: int
    title: str
    media_type: str
    year: int | None = None
    genres: list[str] = field(default_factory=list)
    overview: str | None = None
    vote_average: float | None = None
    poster_path: str | None = None

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if not self.title:
            raise ValueError(EMPTY_TITLE_ERROR)

        if self.id <= 0:
            msg = f"id must be positive, got {self.id}"
            raise ValueError(msg)

        if self.vote_average is not None:
            if not MIN_VOTE_AVERAGE <= self.vote_average <= MAX_VOTE_AVERAGE:
                raise ValueError(VOTE_AVERAGE_RANGE_ERROR_TEMPLATE.format(vote_average=self.vote_average))
