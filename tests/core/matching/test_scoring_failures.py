"""Failure-First tests for scoring.py.

Stage 6: Test that calculate_confidence_score handles errors gracefully
by returning 0.0 (no match) while logging errors for debugging.

This is INTENTIONAL graceful degradation - one candidate failure
should not stop evaluation of other candidates.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from anivault.core.matching.models import NormalizedQuery
from anivault.core.matching.scoring import calculate_confidence_score
from anivault.services.tmdb_models import TMDBSearchResult


class TestCalculateConfidenceScoreFailures:
    """calculate_confidence_score() 실패 케이스 테스트."""

    def test_empty_query_returns_zero(self):
        """빈 쿼리 시 0.0 반환 (정상 동작)."""
        # Given: 빈 쿼리 - NormalizedQuery validation will prevent empty title
        # This test is now invalid as NormalizedQuery validates title in __post_init__
        pytest.skip("Empty title not allowed in NormalizedQuery dataclass")

    def test_empty_result_returns_zero(self):
        """빈 결과 시 0.0 반환 (정상 동작)."""
        # Given: NormalizedQuery and minimal TMDBSearchResult
        query = NormalizedQuery(title="Attack on Titan", year=2013)
        result = TMDBSearchResult(
            id=1,
            media_type="tv",
            title="",  # Empty title
            name=None,
            popularity=0.0,
            vote_average=0.0,
            vote_count=0,
            overview="",
            original_language="en",
            genre_ids=[],
        )

        # When
        score = calculate_confidence_score(query, result)

        # Then: 0.0 반환 (매칭 불가)
        assert score == 0.0

    def test_value_error_returns_zero_with_logging(self):
        """ValueError 발생 시 0.0 반환하고 로깅 (graceful)."""
        # Given: Valid dataclass inputs, but mock to raise ValueError
        query = NormalizedQuery(title="Test", year=2013)
        result = TMDBSearchResult(
            id=1,
            media_type="tv",
            title="Test",
            name=None,
            popularity=50.0,
            vote_average=8.0,
            vote_count=100,
            overview="Test",
            original_language="en",
            genre_ids=[],
        )

        # Mock _calculate_title_score to raise ValueError
        with patch(
            "anivault.core.matching.scoring._calculate_title_score"
        ) as mock_score:
            mock_score.side_effect = ValueError("Invalid similarity")

            with patch("anivault.core.matching.scoring.logger") as mock_logger:
                # When
                score = calculate_confidence_score(query, result)

                # Then: graceful degradation
                assert score == 0.0
                # Verify logging
                mock_logger.exception.assert_called_once()
                call_args = mock_logger.exception.call_args[0]
                assert "Error calculating confidence score" in call_args[0]

    def test_unexpected_error_returns_zero_with_logging(self):
        """예상치 못한 에러 시 0.0 반환하고 로깅 (graceful)."""
        # Given: Valid dataclass inputs
        query = NormalizedQuery(title="Test", year=2013)
        result = TMDBSearchResult(
            id=1,
            media_type="tv",
            title="Test",
            name=None,
            popularity=50.0,
            vote_average=8.0,
            vote_count=100,
            overview="Test",
            original_language="en",
            genre_ids=[],
        )

        # Mock to raise unexpected error
        with patch("anivault.core.matching.scoring.fuzz") as mock_fuzz:
            mock_fuzz.ratio.side_effect = RuntimeError("Unexpected")

            with patch("anivault.core.matching.scoring.logger") as mock_logger:
                # When
                score = calculate_confidence_score(query, result)

                # Then: graceful degradation
                assert score == 0.0
                # Verify logging
                mock_logger.exception.assert_called_once()
                call_args = mock_logger.exception.call_args[0]
                assert "Unexpected error" in call_args[0]

    def test_valid_input_returns_score(self):
        """유효한 입력 시 점수 반환."""
        # Given: 유효한 NormalizedQuery와 TMDBSearchResult
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
            genre_ids=[16],  # Animation
        )

        # When
        score = calculate_confidence_score(query, result)

        # Then: 높은 점수 (정확한 매칭)
        assert 0.8 <= score <= 1.0


# Note: graceful degradation 패턴 - 한 후보 실패해도 다른 후보 계속 평가
# 이건 매칭 알고리즘의 의도된 설계임
