"""Tests for Matching Engine Domain Models.

This module contains unit tests for the frozen dataclasses defined in
src/anivault/core/matching/models.py.
"""

from __future__ import annotations

import pytest

from anivault.core.matching.models import MatchResult, NormalizedQuery


class TestNormalizedQuery:
    """Test cases for NormalizedQuery dataclass."""

    def test_normalized_query_valid_data(self) -> None:
        """Test NormalizedQuery with valid data."""
        # Given
        title = "진격의 거인"
        year = 2013

        # When
        query = NormalizedQuery(title=title, year=year)

        # Then
        assert query.title == title
        assert query.year == year

    def test_normalized_query_without_year(self) -> None:
        """Test NormalizedQuery without year hint."""
        # Given
        title = "원피스"

        # When
        query = NormalizedQuery(title=title, year=None)

        # Then
        assert query.title == title
        assert query.year is None

    def test_normalized_query_empty_title(self) -> None:
        """Test NormalizedQuery raises ValueError for empty title."""
        # Given
        empty_title = ""

        # When & Then
        with pytest.raises(ValueError, match="title cannot be empty or whitespace"):
            NormalizedQuery(title=empty_title, year=2020)

    def test_normalized_query_whitespace_title(self) -> None:
        """Test NormalizedQuery raises ValueError for whitespace-only title."""
        # Given
        whitespace_title = "   "

        # When & Then
        with pytest.raises(ValueError, match="title cannot be empty or whitespace"):
            NormalizedQuery(title=whitespace_title, year=2020)

    def test_normalized_query_year_too_old(self) -> None:
        """Test NormalizedQuery raises ValueError for year < 1900."""
        # Given
        title = "Test"
        old_year = 1899

        # When & Then
        with pytest.raises(ValueError, match="year must be between"):
            NormalizedQuery(title=title, year=old_year)

    def test_normalized_query_year_too_future(self) -> None:
        """Test NormalizedQuery raises ValueError for year too far in future."""
        # Given
        title = "Test"
        future_year = 2035  # Assuming current year is 2025, future_limit is 2030

        # When & Then
        with pytest.raises(ValueError, match="year must be between"):
            NormalizedQuery(title=title, year=future_year)

    def test_normalized_query_immutability(self) -> None:
        """Test NormalizedQuery is immutable (frozen)."""
        # Given
        query = NormalizedQuery(title="Test", year=2020)

        # When & Then
        with pytest.raises((AttributeError, TypeError)):  # Frozen dataclass error
            query.title = "New Title"  # type: ignore[misc]

        with pytest.raises((AttributeError, TypeError)):  # Frozen dataclass error
            query.year = 2021  # type: ignore[misc]


class TestMatchResult:
    """Test cases for MatchResult dataclass."""

    def test_match_result_valid_data(self) -> None:
        """Test MatchResult with valid data."""
        # Given
        tmdb_id = 1429
        title = "진격의 거인"
        year = 2013
        confidence_score = 0.95
        media_type = "tv"

        # When
        result = MatchResult(
            tmdb_id=tmdb_id,
            title=title,
            year=year,
            confidence_score=confidence_score,
            media_type=media_type,
        )

        # Then
        assert result.tmdb_id == tmdb_id
        assert result.title == title
        assert result.year == year
        assert result.confidence_score == confidence_score
        assert result.media_type == media_type

    def test_match_result_without_year(self) -> None:
        """Test MatchResult without year."""
        # Given
        result = MatchResult(
            tmdb_id=100,
            title="Test",
            year=None,
            confidence_score=0.8,
            media_type="movie",
        )

        # Then
        assert result.year is None

    def test_match_result_empty_title(self) -> None:
        """Test MatchResult raises ValueError for empty title."""
        # When & Then
        with pytest.raises(ValueError, match="title cannot be empty or whitespace"):
            MatchResult(
                tmdb_id=1,
                title="",
                year=2020,
                confidence_score=0.5,
                media_type="tv",
            )

    def test_match_result_confidence_score_too_low(self) -> None:
        """Test MatchResult raises ValueError for confidence_score < 0.0."""
        # When & Then
        with pytest.raises(
            ValueError,
            match="Confidence score must be between",
        ):
            MatchResult(
                tmdb_id=1,
                title="Test",
                year=2020,
                confidence_score=-0.1,
                media_type="tv",
            )

    def test_match_result_confidence_score_too_high(self) -> None:
        """Test MatchResult raises ValueError for confidence_score > 1.0."""
        # When & Then
        with pytest.raises(
            ValueError,
            match="Confidence score must be between",
        ):
            MatchResult(
                tmdb_id=1,
                title="Test",
                year=2020,
                confidence_score=1.1,
                media_type="tv",
            )

    def test_match_result_invalid_media_type(self) -> None:
        """Test MatchResult raises ValueError for invalid media_type."""
        # When & Then
        with pytest.raises(ValueError, match=r"media_type must be one of"):
            MatchResult(
                tmdb_id=1,
                title="Test",
                year=2020,
                confidence_score=0.5,
                media_type="invalid",
            )

    def test_match_result_immutability(self) -> None:
        """Test MatchResult is immutable (frozen)."""
        # Given
        result = MatchResult(
            tmdb_id=1,
            title="Test",
            year=2020,
            confidence_score=0.5,
            media_type="tv",
        )

        # When & Then
        with pytest.raises((AttributeError, TypeError)):  # Frozen dataclass error
            result.title = "New Title"  # type: ignore[misc]

        with pytest.raises((AttributeError, TypeError)):  # Frozen dataclass error
            result.confidence_score = 0.9  # type: ignore[misc]
