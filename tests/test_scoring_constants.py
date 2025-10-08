"""Tests for scoring constants migration.

This module tests that:
1. ScoringWeights constants are correctly defined
2. Weights sum to 1.0 (required for proper scoring)
3. scoring.py correctly uses the constants
4. No hardcoded magic values remain in scoring.py
"""

import pytest

from anivault.shared.constants.matching import ScoringWeights


class TestScoringWeights:
    """Test ScoringWeights constants."""

    def test_weights_sum_to_one(self) -> None:
        """Test that all weights sum to 1.0."""
        total = (
            ScoringWeights.TITLE_MATCH
            + ScoringWeights.YEAR_MATCH
            + ScoringWeights.MEDIA_TYPE_MATCH
            + ScoringWeights.POPULARITY_MATCH
        )
        
        # Allow small floating point error
        assert abs(total - 1.0) < 0.001, f"Weights sum to {total}, expected 1.0"

    def test_weights_are_positive(self) -> None:
        """Test that all weights are positive."""
        assert ScoringWeights.TITLE_MATCH > 0
        assert ScoringWeights.YEAR_MATCH > 0
        assert ScoringWeights.MEDIA_TYPE_MATCH > 0
        assert ScoringWeights.POPULARITY_MATCH > 0

    def test_title_weight_is_highest(self) -> None:
        """Test that title weight is the highest (most important factor)."""
        assert ScoringWeights.TITLE_MATCH > ScoringWeights.YEAR_MATCH
        assert ScoringWeights.TITLE_MATCH > ScoringWeights.MEDIA_TYPE_MATCH
        assert ScoringWeights.TITLE_MATCH > ScoringWeights.POPULARITY_MATCH

    def test_weights_match_actual_values(self) -> None:
        """Test that weights match the empirically tested values."""
        # These values were tested and validated in production
        assert ScoringWeights.TITLE_MATCH == 0.5
        assert ScoringWeights.YEAR_MATCH == 0.25
        assert ScoringWeights.MEDIA_TYPE_MATCH == 0.15
        assert ScoringWeights.POPULARITY_MATCH == 0.1

    def test_legacy_aliases_exist(self) -> None:
        """Test that legacy aliases are maintained for backwards compatibility."""
        assert ScoringWeights.GENRE_MATCH == ScoringWeights.MEDIA_TYPE_MATCH
        assert ScoringWeights.RATING_MATCH == ScoringWeights.POPULARITY_MATCH


class TestScoringMigration:
    """Test that scoring.py correctly uses constants."""

    def test_no_hardcoded_weights_in_scoring(self) -> None:
        """Test that scoring.py doesn't contain hardcoded weight values."""
        from pathlib import Path
        
        scoring_file = Path("src/anivault/core/matching/scoring.py")
        content = scoring_file.read_text(encoding="utf-8")
        
        # Check that old hardcoded weights pattern doesn't exist
        assert 'weights = {' not in content, (
            "Found hardcoded weights dict in scoring.py. "
            "Should use ScoringWeights constants instead."
        )
        
        # Check that we're not hardcoding the weight values directly
        assert '"title": 0.5' not in content
        assert '"year": 0.25' not in content
        assert '"media_type": 0.15' not in content
        assert '"popularity": 0.1' not in content

    def test_scoring_imports_constants(self) -> None:
        """Test that scoring.py imports ScoringWeights."""
        from pathlib import Path
        
        scoring_file = Path("src/anivault/core/matching/scoring.py")
        content = scoring_file.read_text(encoding="utf-8")
        
        assert "from ...shared.constants.matching import ScoringWeights" in content, (
            "scoring.py must import ScoringWeights from shared.constants.matching"
        )

    def test_scoring_uses_constants(self) -> None:
        """Test that scoring.py uses ScoringWeights constants."""
        from pathlib import Path
        
        scoring_file = Path("src/anivault/core/matching/scoring.py")
        content = scoring_file.read_text(encoding="utf-8")
        
        # Check that constants are actually used
        assert "ScoringWeights.TITLE_MATCH" in content
        assert "ScoringWeights.YEAR_MATCH" in content
        assert "ScoringWeights.MEDIA_TYPE_MATCH" in content
        assert "ScoringWeights.POPULARITY_MATCH" in content


class TestScoringBehavior:
    """Test that scoring behavior is preserved after migration.
    
    These tests verify that migrating to constants doesn't change
    the actual matching behavior.
    """

    def test_confidence_score_calculation(self) -> None:
        """Test basic confidence score calculation."""
        from anivault.core.matching.scoring import calculate_confidence_score
        
        # Test data
        normalized_query = {
            "title": "attack on titan",
            "year": 2013,
            "language": "en"
        }
        
        tmdb_result = {
            "title": "Attack on Titan",
            "release_date": "2013-04-07",
            "media_type": "tv",
            "popularity": 85.2
        }
        
        # Calculate score
        score = calculate_confidence_score(normalized_query, tmdb_result)
        
        # Score should be high (good match)
        assert 0.8 <= score <= 1.0, f"Expected high confidence, got {score}"

    def test_zero_score_on_empty_query(self) -> None:
        """Test that empty query returns 0.0 score."""
        from anivault.core.matching.scoring import calculate_confidence_score
        
        normalized_query = {"title": "", "year": None}
        tmdb_result = {"title": "Some Title"}
        
        score = calculate_confidence_score(normalized_query, tmdb_result)
        assert score == 0.0

    def test_zero_score_on_invalid_data(self) -> None:
        """Test graceful degradation on invalid data."""
        from anivault.core.matching.scoring import calculate_confidence_score
        
        # Invalid query type
        score = calculate_confidence_score("invalid", {"title": "Test"})
        assert score == 0.0
        
        # Invalid result type
        score = calculate_confidence_score({"title": "Test"}, "invalid")
        assert score == 0.0

