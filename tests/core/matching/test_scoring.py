"""Unit tests for the confidence scoring system - UPDATED FOR DATACLASSES."""

import pytest

from anivault.core.matching.models import NormalizedQuery
from anivault.core.matching.scoring import (
    _calculate_media_type_score,
    _calculate_popularity_bonus,
    _calculate_title_score,
    _calculate_year_score,
    calculate_confidence_score,
)
from anivault.services.tmdb_models import TMDBSearchResult


class TestCalculateTitleScore:
    """Test cases for title similarity scoring."""

    def test_perfect_match(self):
        """Test perfect title match."""
        score = _calculate_title_score("Attack on Titan", "Attack on Titan")
        assert score == 1.0

    def test_case_insensitive_match(self):
        """Test case insensitive matching."""
        score = _calculate_title_score("attack on titan", "ATTACK ON TITAN")
        assert score == 1.0

    def test_partial_match(self):
        """Test partial title match."""
        score = _calculate_title_score(
            "Attack on Titan", "Attack on Titan: The Final Season"
        )
        assert score > 0.6  # Should be reasonably high but not perfect

    def test_no_match(self):
        """Test completely different titles."""
        score = _calculate_title_score("Attack on Titan", "Naruto")
        assert score < 0.3  # Should be low

    def test_empty_titles(self):
        """Test empty title handling."""
        score = _calculate_title_score("", "Attack on Titan")
        assert score == 0.0

        score = _calculate_title_score("Attack on Titan", "")
        assert score == 0.0

        score = _calculate_title_score("", "")
        assert score == 0.0


class TestCalculateYearScore:
    """Test cases for year matching scoring."""

    def test_perfect_year_match(self):
        """Test perfect year match."""
        score = _calculate_year_score(2013, "2013-04-07")
        assert score == 1.0

    def test_close_year_match(self):
        """Test close year match."""
        score = _calculate_year_score(2013, "2014-04-07")
        assert score == 0.8  # 1 year difference

        score = _calculate_year_score(2013, "2015-04-07")
        assert score == 0.6  # 2 year difference

    def test_reasonable_year_match(self):
        """Test reasonable year match."""
        score = _calculate_year_score(2013, "2016-04-07")
        assert score == 0.4  # 3 year difference

    def test_poor_year_match(self):
        """Test poor year match."""
        score = _calculate_year_score(2013, "2020-04-07")
        assert score == 0.1  # 7 year difference

    def test_missing_query_year(self):
        """Test missing query year."""
        score = _calculate_year_score(None, "2013-04-07")
        assert score == 0.5  # Neutral score

    def test_missing_release_date(self):
        """Test missing release date."""
        score = _calculate_year_score(2013, None)
        assert score == 0.5  # Neutral score

    def test_invalid_date_format(self):
        """Test invalid date format."""
        score = _calculate_year_score(2013, "invalid-date")
        assert score == 0.5  # Neutral score for invalid format


class TestCalculateMediaTypeScore:
    """Test cases for media type scoring."""

    def test_tv_show_score(self):
        """Test TV show preference."""
        score = _calculate_media_type_score("tv")
        assert score == 1.0

    def test_movie_score(self):
        """Test movie score."""
        score = _calculate_media_type_score("movie")
        assert score == 0.7

    def test_unknown_media_type(self):
        """Test unknown media type."""
        score = _calculate_media_type_score(None)
        assert score == 0.5  # Neutral score


class TestCalculatePopularityBonus:
    """Test cases for popularity bonus calculation."""

    def test_high_popularity(self):
        """Test high popularity bonus."""
        score = _calculate_popularity_bonus(100.0)
        assert score == 0.2  # Capped at 0.2

    def test_medium_popularity(self):
        """Test medium popularity bonus."""
        score = _calculate_popularity_bonus(50.0)
        assert score == 0.1  # Half of max bonus

    def test_low_popularity(self):
        """Test low popularity bonus."""
        score = _calculate_popularity_bonus(10.0)
        assert score < 0.05  # Small bonus

    def test_zero_popularity(self):
        """Test zero popularity."""
        score = _calculate_popularity_bonus(0.0)
        assert score == 0.0

    def test_negative_popularity(self):
        """Test negative popularity handling."""
        score = _calculate_popularity_bonus(-10.0)
        assert score == 0.0


class TestCalculateConfidenceScore:
    """Test cases for the main confidence score calculation - UPDATED FOR DATACLASSES."""

    def test_perfect_match(self):
        """Test perfect match scenario."""
        query = NormalizedQuery(title="Attack on Titan", year=2013)
        result = TMDBSearchResult(
            id=1429,
            media_type="tv",
            title="Attack on Titan",
            name=None,
            release_date="2013-04-07",
            first_air_date=None,
            popularity=85.2,
            vote_average=9.0,
            vote_count=5000,
            overview="Test overview",
            original_language="ja",
            genre_ids=[16],
        )

        score = calculate_confidence_score(query, result)
        assert score > 0.9  # Should be very high

    def test_good_match(self):
        """Test good match scenario."""
        query = NormalizedQuery(title="Attack on Titan", year=2013)
        result = TMDBSearchResult(
            id=1429,
            media_type="tv",
            title="Attack on Titan: The Final Season",
            name=None,
            release_date="2014-04-07",
            first_air_date=None,
            popularity=75.0,
            vote_average=9.0,
            vote_count=5000,
            overview="Test overview",
            original_language="ja",
            genre_ids=[16],
        )

        score = calculate_confidence_score(query, result)
        assert 0.6 <= score < 0.9  # Should be high but not perfect

    def test_medium_match(self):
        """Test medium match scenario."""
        query = NormalizedQuery(title="Attack on Titan", year=2013)
        result = TMDBSearchResult(
            id=1429,
            media_type="tv",
            title="Attack on Titan: Junior High",
            name=None,
            release_date="2015-10-03",
            first_air_date=None,
            popularity=45.0,
            vote_average=7.0,
            vote_count=1000,
            overview="Test overview",
            original_language="ja",
            genre_ids=[16],
        )

        score = calculate_confidence_score(query, result)
        assert 0.4 <= score < 0.7  # Should be medium

    def test_poor_match(self):
        """Test poor match scenario."""
        query = NormalizedQuery(title="Attack on Titan", year=2013)
        result = TMDBSearchResult(
            id=1234,
            media_type="tv",
            title="Naruto",
            name=None,
            release_date="2002-10-03",
            first_air_date=None,
            popularity=90.0,
            vote_average=8.0,
            vote_count=3000,
            overview="Test overview",
            original_language="ja",
            genre_ids=[16],
        )

        score = calculate_confidence_score(query, result)
        assert score < 0.4  # Should be low

    def test_missing_data(self):
        """Test handling of missing data."""
        query = NormalizedQuery(title="Attack on Titan", year=None)
        result = TMDBSearchResult(
            id=1429,
            media_type="tv",
            title="Attack on Titan",
            name=None,
            release_date=None,
            first_air_date=None,
            popularity=0.0,
            vote_average=0.0,
            vote_count=0,
            overview="",
            original_language="ja",
            genre_ids=[],
        )

        score = calculate_confidence_score(query, result)
        assert 0.0 <= score <= 1.0  # Should be valid score

    def test_empty_query(self):
        """Test empty query handling."""
        # NormalizedQuery validates title, so empty query not possible
        pytest.skip("Empty title not allowed in NormalizedQuery dataclass")

    def test_empty_result(self):
        """Test empty result handling."""
        query = NormalizedQuery(title="Attack on Titan", year=2013)
        result = TMDBSearchResult(
            id=1,
            media_type="tv",
            title="",
            name=None,
            release_date=None,
            first_air_date=None,
            popularity=0.0,
            vote_average=0.0,
            vote_count=0,
            overview="",
            original_language="en",
            genre_ids=[],
        )

        score = calculate_confidence_score(query, result)
        assert score == 0.0  # Should be 0 for empty result

    def test_invalid_data_handling(self):
        """Test handling of invalid data."""
        query = NormalizedQuery(title="Attack on Titan", year=2013)
        result = TMDBSearchResult(
            id=1429,
            media_type="tv",
            title="Attack on Titan",
            name=None,
            release_date="invalid-date",  # Invalid date format
            first_air_date=None,
            popularity=85.2,
            vote_average=9.0,
            vote_count=5000,
            overview="Test",
            original_language="ja",
            genre_ids=[],
        )

        # Should handle gracefully
        score = calculate_confidence_score(query, result)
        assert 0.0 <= score <= 1.0

    def test_score_bounds(self):
        """Test that scores are always within valid bounds."""
        test_cases = [
            (
                NormalizedQuery(title="Attack on Titan", year=2013),
                TMDBSearchResult(
                    id=1,
                    media_type="tv",
                    title="Attack on Titan",
                    name=None,
                    release_date="2013-04-07",
                    first_air_date=None,
                    popularity=100.0,
                    vote_average=10.0,
                    vote_count=10000,
                    overview="Test",
                    original_language="ja",
                    genre_ids=[],
                ),
            ),
            (
                NormalizedQuery(title="Test", year=None),
                TMDBSearchResult(
                    id=2,
                    media_type="movie",
                    title="Different Title",
                    name=None,
                    release_date=None,
                    first_air_date=None,
                    popularity=0.0,
                    vote_average=0.0,
                    vote_count=0,
                    overview="",
                    original_language="en",
                    genre_ids=[],
                ),
            ),
        ]

        for query, result in test_cases:
            score = calculate_confidence_score(query, result)
            assert 0.0 <= score <= 1.0
