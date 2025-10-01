"""Unit tests for the confidence scoring system."""

import pytest

from anivault.core.matching.scoring import (
    calculate_confidence_score,
    _calculate_title_score,
    _calculate_year_score,
    _calculate_media_type_score,
    _calculate_popularity_bonus,
)


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
        score = _calculate_title_score("Attack on Titan", "Attack on Titan: The Final Season")
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

    def test_invalid_release_date(self):
        """Test invalid release date format."""
        score = _calculate_year_score(2013, "invalid-date")
        assert score == 0.5  # Neutral score for invalid format


class TestCalculateMediaTypeScore:
    """Test cases for media type scoring."""

    def test_tv_show_preference(self):
        """Test TV show preference."""
        score = _calculate_media_type_score("tv")
        assert score == 1.0

    def test_movie_score(self):
        """Test movie score."""
        score = _calculate_media_type_score("movie")
        assert score == 0.7

    def test_unknown_media_type(self):
        """Test unknown media type."""
        score = _calculate_media_type_score("unknown")
        assert score == 0.5

    def test_none_media_type(self):
        """Test None media type."""
        score = _calculate_media_type_score(None)
        assert score == 0.5


class TestCalculatePopularityBonus:
    """Test cases for popularity bonus scoring."""

    def test_zero_popularity(self):
        """Test zero popularity."""
        bonus = _calculate_popularity_bonus(0)
        assert bonus == 0.0

    def test_negative_popularity(self):
        """Test negative popularity."""
        bonus = _calculate_popularity_bonus(-10)
        assert bonus == 0.0

    def test_medium_popularity(self):
        """Test medium popularity."""
        bonus = _calculate_popularity_bonus(50)
        assert bonus == 0.1  # 50/100 * 0.2

    def test_high_popularity(self):
        """Test high popularity."""
        bonus = _calculate_popularity_bonus(100)
        assert bonus == 0.2  # Capped at 0.2

    def test_very_high_popularity(self):
        """Test very high popularity (capped)."""
        bonus = _calculate_popularity_bonus(200)
        assert bonus == 0.2  # Capped at 0.2


class TestCalculateConfidenceScore:
    """Test cases for the main confidence score calculation."""

    def test_perfect_match(self):
        """Test perfect match scenario."""
        query = {
            "title": "Attack on Titan",
            "language": "en",
            "year": 2013
        }
        result = {
            "title": "Attack on Titan",
            "release_date": "2013-04-07",
            "media_type": "tv",
            "popularity": 85.2,
            "genres": [{"name": "Animation"}]
        }
        
        score = calculate_confidence_score(query, result)
        assert score > 0.9  # Should be very high

    def test_good_match(self):
        """Test good match scenario."""
        query = {
            "title": "Attack on Titan",
            "language": "en",
            "year": 2013
        }
        result = {
            "title": "Attack on Titan: The Final Season",
            "release_date": "2014-04-07",
            "media_type": "tv",
            "popularity": 75.0,
            "genres": [{"name": "Animation"}]
        }
        
        score = calculate_confidence_score(query, result)
        assert 0.6 <= score < 0.9  # Should be high but not perfect

    def test_medium_match(self):
        """Test medium match scenario."""
        query = {
            "title": "Attack on Titan",
            "language": "en",
            "year": 2013
        }
        result = {
            "title": "Attack on Titan: Junior High",
            "release_date": "2015-10-03",
            "media_type": "tv",
            "popularity": 45.0,
            "genres": [{"name": "Animation"}]
        }
        
        score = calculate_confidence_score(query, result)
        assert 0.4 <= score < 0.7  # Should be medium

    def test_poor_match(self):
        """Test poor match scenario."""
        query = {
            "title": "Attack on Titan",
            "language": "en",
            "year": 2013
        }
        result = {
            "title": "Naruto",
            "release_date": "2002-10-03",
            "media_type": "tv",
            "popularity": 90.0,
            "genres": [{"name": "Animation"}]
        }
        
        score = calculate_confidence_score(query, result)
        assert score < 0.4  # Should be low

    def test_missing_data(self):
        """Test handling of missing data."""
        query = {
            "title": "Attack on Titan",
            "language": "en",
            "year": None
        }
        result = {
            "title": "Attack on Titan",
            "release_date": None,
            "media_type": None,
            "popularity": 0,
            "genres": []
        }
        
        score = calculate_confidence_score(query, result)
        assert 0.0 <= score <= 1.0  # Should be valid score

    def test_empty_query(self):
        """Test empty query handling."""
        query = {}
        result = {
            "title": "Attack on Titan",
            "release_date": "2013-04-07",
            "media_type": "tv",
            "popularity": 85.2,
            "genres": [{"name": "Animation"}]
        }
        
        score = calculate_confidence_score(query, result)
        assert score == 0.0  # Should be 0 for empty query

    def test_empty_result(self):
        """Test empty result handling."""
        query = {
            "title": "Attack on Titan",
            "language": "en",
            "year": 2013
        }
        result = {}
        
        score = calculate_confidence_score(query, result)
        assert score == 0.0  # Should be 0 for empty result

    def test_invalid_data_handling(self):
        """Test handling of invalid data."""
        query = {
            "title": "Attack on Titan",
            "language": "en",
            "year": 2013
        }
        result = {
            "title": "Attack on Titan",
            "release_date": "invalid-date",
            "media_type": "tv",
            "popularity": "invalid-popularity",
            "genres": [{"name": "Animation"}]
        }
        
        score = calculate_confidence_score(query, result)
        assert 0.0 <= score <= 1.0  # Should handle gracefully

    def test_score_bounds(self):
        """Test that scores are always within bounds."""
        query = {
            "title": "Test",
            "language": "en",
            "year": 2020
        }
        result = {
            "title": "Test",
            "release_date": "2020-01-01",
            "media_type": "tv",
            "popularity": 1000,  # Very high popularity
            "genres": [{"name": "Animation"}]
        }
        
        score = calculate_confidence_score(query, result)
        assert 0.0 <= score <= 1.0  # Should be within bounds
