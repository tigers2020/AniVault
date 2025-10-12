"""Tests for YearScorer strategy implementation.

This module tests the year matching scoring logic with various
scenarios including exact matches, tolerance, and missing years.
"""

from __future__ import annotations

import pytest

from anivault.core.parser.models import ParsingResult
from anivault.services.metadata_enricher.models import ScoreResult
from anivault.services.metadata_enricher.scoring.year_scorer import YearScorer
from anivault.shared.errors import DomainError


class TestYearScorerInit:
    """Test suite for YearScorer initialization."""

    def test_default_parameters(self) -> None:
        """Test YearScorer with default parameters."""
        scorer = YearScorer()
        assert scorer.weight == 0.2
        assert scorer.tolerance == 1

    def test_custom_parameters(self) -> None:
        """Test YearScorer with custom parameters."""
        scorer = YearScorer(weight=0.3, tolerance=2)
        assert scorer.weight == 0.3
        assert scorer.tolerance == 2

    def test_invalid_weight_below_range(self) -> None:
        """Test YearScorer with weight below valid range."""
        with pytest.raises(ValueError, match=r"weight must be between"):
            YearScorer(weight=-0.1)

    def test_invalid_weight_above_range(self) -> None:
        """Test YearScorer with weight above valid range."""
        with pytest.raises(ValueError, match=r"weight must be between"):
            YearScorer(weight=1.5)

    def test_invalid_tolerance_negative(self) -> None:
        """Test YearScorer with negative tolerance."""
        with pytest.raises(ValueError, match=r"tolerance must be non-negative"):
            YearScorer(tolerance=-1)


class TestYearScorerScoring:
    """Test suite for YearScorer scoring logic."""

    def test_exact_year_match(self) -> None:
        """Test exact year match returns 1.0."""
        # Given
        scorer = YearScorer()
        file_info = ParsingResult(title="Attack on Titan", year=2013)
        tmdb_candidate = {"first_air_date": "2013-04-07", "id": 1429}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert isinstance(result, ScoreResult)
        assert result.score == 1.0
        assert result.weight == 0.2
        assert result.component == "year_match"
        assert "Exact year match" in result.reason
        assert "2013 vs 2013" in result.reason
        assert "delta: 0" in result.reason

    def test_year_within_tolerance_plus_one(self) -> None:
        """Test year +1 within tolerance."""
        # Given
        scorer = YearScorer(tolerance=1)
        file_info = ParsingResult(title="Test", year=2013)
        tmdb_candidate = {"first_air_date": "2014-01-01", "id": 123}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        # delta=1, tolerance=1 → score = 1.0 - (1 / (1 + 1)) = 0.5
        assert result.score == 0.5
        assert "Within tolerance" in result.reason
        assert "delta: 1" in result.reason

    def test_year_within_tolerance_minus_one(self) -> None:
        """Test year -1 within tolerance."""
        # Given
        scorer = YearScorer(tolerance=1)
        file_info = ParsingResult(title="Test", year=2014)
        tmdb_candidate = {"release_date": "2013-12-01", "id": 123}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 0.5
        assert "Within tolerance" in result.reason

    def test_year_beyond_tolerance(self) -> None:
        """Test year difference beyond tolerance returns 0.0."""
        # Given
        scorer = YearScorer(tolerance=1)
        file_info = ParsingResult(title="Test", year=2013)
        tmdb_candidate = {"first_air_date": "2015-01-01", "id": 123}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 0.0
        assert "Year mismatch" in result.reason
        assert "delta: 2" in result.reason

    def test_year_with_larger_tolerance(self) -> None:
        """Test year scoring with larger tolerance."""
        # Given
        scorer = YearScorer(tolerance=2)
        file_info = ParsingResult(title="Test", year=2013)
        tmdb_candidate = {"first_air_date": "2015-01-01", "id": 123}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        # delta=2, tolerance=2 → score = 1.0 - (2 / (2 + 1)) = 0.333...
        assert 0.3 <= result.score <= 0.4
        assert "Within tolerance" in result.reason

    def test_zero_tolerance(self) -> None:
        """Test year scoring with zero tolerance (exact match only)."""
        # Given
        scorer = YearScorer(tolerance=0)
        file_info_exact = ParsingResult(title="Test", year=2013)
        file_info_off = ParsingResult(title="Test", year=2014)
        tmdb_candidate = {"first_air_date": "2013-01-01", "id": 123}

        # When - exact match
        result_exact = scorer.score(file_info_exact, tmdb_candidate)
        # When - off by 1
        result_off = scorer.score(file_info_off, tmdb_candidate)

        # Then
        assert result_exact.score == 1.0
        assert result_off.score == 0.0


class TestYearScorerMissingYears:
    """Test suite for missing year scenarios."""

    def test_missing_file_year(self) -> None:
        """Test when file year is not available."""
        # Given
        scorer = YearScorer()
        file_info = ParsingResult(title="Attack on Titan")  # No year
        tmdb_candidate = {"first_air_date": "2013-04-07", "id": 1429}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 0.0
        assert "Year unavailable" in result.reason

    def test_missing_tmdb_year(self) -> None:
        """Test when TMDB year is not available."""
        # Given
        scorer = YearScorer()
        file_info = ParsingResult(title="Test", year=2013)
        tmdb_candidate = {"id": 123}  # No date fields

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 0.0
        assert "Year unavailable" in result.reason

    def test_both_years_missing(self) -> None:
        """Test when both years are missing."""
        # Given
        scorer = YearScorer()
        file_info = ParsingResult(title="Test")
        tmdb_candidate = {"id": 123}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 0.0
        assert "Year unavailable" in result.reason


class TestYearScorerDateFormats:
    """Test suite for different date format handling."""

    def test_first_air_date_tv_show(self) -> None:
        """Test extraction from first_air_date (TV shows)."""
        # Given
        scorer = YearScorer()
        file_info = ParsingResult(title="Test", year=2013)
        tmdb_candidate = {"first_air_date": "2013-04-07", "id": 123}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 1.0

    def test_release_date_movie(self) -> None:
        """Test extraction from release_date (movies)."""
        # Given
        scorer = YearScorer()
        file_info = ParsingResult(title="Test", year=2013)
        tmdb_candidate = {"release_date": "2013-07-15", "id": 123}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 1.0

    def test_display_date_pydantic_model(self) -> None:
        """Test extraction from display_date (TMDBMediaDetails)."""
        # Given
        scorer = YearScorer()
        file_info = ParsingResult(title="Test", year=2013)
        tmdb_candidate = {"display_date": "2013-04-07", "id": 123}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 1.0

    def test_first_air_date_priority(self) -> None:
        """Test first_air_date takes priority over release_date."""
        # Given
        scorer = YearScorer()
        file_info = ParsingResult(title="Test", year=2013)
        tmdb_candidate = {
            "first_air_date": "2013-04-07",
            "release_date": "2014-01-01",  # Different year, should be ignored
            "id": 123,
        }

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 1.0  # Matches first_air_date


class TestYearScorerValidation:
    """Test suite for input validation."""

    def test_invalid_file_info_type(self) -> None:
        """Test invalid file_info type raises DomainError."""
        # Given
        scorer = YearScorer()
        file_info = {"title": "Test", "year": 2013}  # type: ignore[arg-type]  # Wrong type
        tmdb_candidate = {"first_air_date": "2013-01-01", "id": 123}

        # When & Then
        with pytest.raises(DomainError) as exc_info:
            scorer.score(file_info, tmdb_candidate)  # type: ignore[arg-type]

        assert exc_info.value.code.value == "VALIDATION_ERROR"

    def test_invalid_tmdb_candidate_type(self) -> None:
        """Test invalid tmdb_candidate type raises DomainError."""
        # Given
        scorer = YearScorer()
        file_info = ParsingResult(title="Test", year=2013)
        tmdb_candidate = "2013-01-01"  # type: ignore[arg-type]  # Wrong type

        # When & Then
        with pytest.raises(DomainError) as exc_info:
            scorer.score(file_info, tmdb_candidate)  # type: ignore[arg-type]

        assert exc_info.value.code.value == "VALIDATION_ERROR"


class TestYearScorerEdgeCases:
    """Test suite for edge cases."""

    def test_invalid_date_format(self) -> None:
        """Test handling of invalid date format."""
        # Given
        scorer = YearScorer()
        file_info = ParsingResult(title="Test", year=2013)
        tmdb_candidate = {"first_air_date": "invalid-date", "id": 123}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 0.0  # Treat as unavailable

    def test_year_out_of_reasonable_range_low(self) -> None:
        """Test year below reasonable range (< 1900)."""
        # Given
        scorer = YearScorer()
        file_info = ParsingResult(title="Test", year=2013)
        tmdb_candidate = {"first_air_date": "1800-01-01", "id": 123}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 0.0  # Out of range, treat as unavailable

    def test_year_out_of_reasonable_range_high(self) -> None:
        """Test year above reasonable range (> 2100)."""
        # Given
        scorer = YearScorer()
        file_info = ParsingResult(title="Test", year=2013)
        tmdb_candidate = {"first_air_date": "2200-01-01", "id": 123}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 0.0  # Out of range, treat as unavailable

    def test_empty_date_string(self) -> None:
        """Test handling of empty date string."""
        # Given
        scorer = YearScorer()
        file_info = ParsingResult(title="Test", year=2013)
        tmdb_candidate = {"first_air_date": "", "id": 123}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 0.0

    def test_non_string_date_field(self) -> None:
        """Test handling of non-string date field."""
        # Given
        scorer = YearScorer()
        file_info = ParsingResult(title="Test", year=2013)
        tmdb_candidate = {"first_air_date": 2013, "id": 123}  # type: ignore[dict-item]  # int

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert result.score == 0.0

    def test_score_result_structure(self) -> None:
        """Test ScoreResult has correct structure."""
        # Given
        scorer = YearScorer(weight=0.3)
        file_info = ParsingResult(title="Test", year=2013)
        tmdb_candidate = {"first_air_date": "2013-01-01", "id": 123}

        # When
        result = scorer.score(file_info, tmdb_candidate)

        # Then
        assert hasattr(result, "score")
        assert hasattr(result, "weight")
        assert hasattr(result, "reason")
        assert hasattr(result, "component")
        assert result.weight == 0.3
