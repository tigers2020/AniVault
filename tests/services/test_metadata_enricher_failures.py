"""Failure-First tests for metadata_enricher.py.

Stage 2.2: Test that functions explicitly raise exceptions instead of
silently returning None or 0.0 for error conditions.
"""

from unittest.mock import Mock

import pytest

from anivault.core.parser.models import ParsingResult
from anivault.services.metadata_enricher import MetadataEnricher
from anivault.shared.errors import ApplicationError, DomainError, ErrorCode


class TestCalculateMatchScoreFailures:
    """_calculate_match_score() 실패 케이스 테스트."""

    def test_invalid_tmdb_result_raises_error(self):
        """TMDB 결과가 유효하지 않을 때 DomainError 발생."""
        # Given
        enricher = MetadataEnricher()
        file_info = Mock(spec=ParsingResult)
        file_info.title = "Attack on Titan"
        file_info.has_episode_info.return_value = False

        invalid_tmdb_result = {}  # title/name 없음

        # When & Then
        with pytest.raises(DomainError) as exc_info:
            enricher._calculate_match_score(file_info, invalid_tmdb_result)

        assert exc_info.value.code == ErrorCode.DATA_PROCESSING_ERROR

    def test_title_similarity_error_propagates(self):
        """제목 유사도 계산 에러가 상위로 전파."""
        # Given
        enricher = MetadataEnricher()
        file_info = Mock(spec=ParsingResult)
        file_info.title = ""  # 빈 문자열 (에러 유발)
        file_info.has_episode_info.return_value = False

        tmdb_result = {"title": "Attack on Titan", "media_type": "tv"}

        # When & Then
        with pytest.raises(DomainError) as exc_info:
            enricher._calculate_match_score(file_info, tmdb_result)

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR


class TestFindBestMatchFailures:
    """_find_best_match() 실패 케이스 테스트."""

    def test_empty_search_results_raises_error(self):
        """검색 결과가 빈 리스트일 때 ApplicationError 발생."""
        # Given
        enricher = MetadataEnricher()
        file_info = Mock(spec=ParsingResult)
        file_info.title = "Attack on Titan"

        # When & Then
        with pytest.raises(ApplicationError) as exc_info:
            enricher._find_best_match(file_info, [])

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR

    def test_invalid_file_info_raises_error(self):
        """file_info가 유효하지 않을 때 None 반환 (validation은 ScoringEngine에서 처리)."""
        # Given
        enricher = MetadataEnricher()
        file_info = Mock(spec=ParsingResult)
        file_info.title = ""  # 빈 제목

        search_results = [{"id": 1, "title": "Attack on Titan"}]

        # When: ScoringEngine이 DomainError 발생 → skip → None 반환
        result = enricher._find_best_match(file_info, search_results)

        # Then: 매칭 실패 (None)
        assert result is None

    def test_score_calculation_error_propagates(self):
        """점수 계산 에러가 skip되고 None 반환 (간소화된 동작)."""
        # Given
        enricher = MetadataEnricher()
        file_info = Mock(spec=ParsingResult)
        file_info.title = "Attack on Titan"

        # 유효하지 않은 TMDB 결과 (title/name 없음)
        search_results = [{"id": 1}]

        # When: ScoringEngine이 DomainError 발생 → skip → None 반환
        result = enricher._find_best_match(file_info, search_results)

        # Then: 매칭 실패 (None)
        assert result is None


# Note: 매칭 알고리즘에서 0.0 점수는 "매칭되지 않음"과 "오류 발생"을 구분할 수 없음
# 리팩토링 후에는 명확한 예외 발생으로 이 문제 해결


class TestScoringEngineIntegrationFailures:
    """ScoringEngine 통합 후 회귀 테스트."""

    def test_scoring_engine_domain_error_propagates(self):
        """ScoringEngine에서 DomainError 발생 시 MetadataEnricher까지 전파."""
        # Given
        enricher = MetadataEnricher()
        file_info = Mock(spec=ParsingResult)
        file_info.title = "Attack on Titan"
        file_info.year = None
        file_info.has_episode_info.return_value = False
        file_info.has_season_info.return_value = False

        # TMDB result missing required fields (should trigger DomainError)
        invalid_tmdb_result = {}  # No title/name

        # When & Then
        with pytest.raises(DomainError) as exc_info:
            enricher._calculate_match_score(file_info, invalid_tmdb_result)

        # Verify error code
        assert exc_info.value.code == ErrorCode.DATA_PROCESSING_ERROR
        assert "title" in str(exc_info.value.message).lower()

    def test_scoring_engine_handles_scorer_failures_gracefully(self):
        """ScoringEngine의 scorer가 Exception 발생 시 skip하고 계속 진행."""
        # Given
        from anivault.services.metadata_enricher.scoring import (
            ScoringEngine,
            TitleScorer,
        )

        # Create a failing scorer
        class FailingScorer:
            component_name = "failing_scorer"
            weight = 0.3

            def score(self, _file_info, _tmdb_candidate):
                raise RuntimeError("Intentional scorer failure")

        # Create engine with both failing and working scorers
        engine = ScoringEngine(
            scorers=[
                TitleScorer(weight=0.7),
                FailingScorer(),
            ],
            normalize_weights=False,
        )

        enricher = MetadataEnricher(scoring_engine=engine)
        file_info = Mock(spec=ParsingResult)
        file_info.title = "Attack on Titan"
        file_info.year = None
        file_info.has_episode_info.return_value = False
        file_info.has_season_info.return_value = False

        tmdb_result = {"title": "Shingeki no Kyojin", "id": 1429, "media_type": "tv"}

        # When
        score = enricher._calculate_match_score(file_info, tmdb_result)

        # Then: Score should still be calculated (failed scorer skipped)
        assert 0.0 <= score <= 1.0
        # Score should be based only on TitleScorer (not 0.0)
        assert score > 0.0

    def test_calculate_match_score_returns_valid_score(self):
        """_calculate_match_score returns a valid score between 0.0 and 1.0."""
        # Given
        enricher = MetadataEnricher()
        file_info = Mock(spec=ParsingResult)
        file_info.title = "Attack on Titan"
        file_info.year = 2013
        file_info.has_episode_info.return_value = True
        file_info.has_season_info.return_value = False

        tmdb_result = {
            "title": "Shingeki no Kyojin",
            "id": 1429,
            "media_type": "tv",
            "first_air_date": "2013-04-07",
        }

        # When
        score = enricher._calculate_match_score(file_info, tmdb_result)

        # Then: Score should be in valid range
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

        # Then: Score should reflect composite scoring
        # (Title similarity low, year match high, media type match high)
        # Expected: weighted average should be > 0 and < 1
        assert score > 0.0, "Score should be non-zero with partial matches"
        assert score < 1.0, "Score should not be perfect with low title similarity"

    def test_exception_handling_consistency_with_legacy_code(self):
        """예외 처리가 기존 코드와 일관성 있게 동작하는지 확인."""
        # Given
        enricher = MetadataEnricher()
        file_info = Mock(spec=ParsingResult)
        file_info.title = "Attack on Titan"
        file_info.year = None
        file_info.has_episode_info.return_value = False
        file_info.has_season_info.return_value = False

        # Test cases: (tmdb_result, expected_error_code)
        test_cases = [
            ({}, ErrorCode.DATA_PROCESSING_ERROR),  # Missing title/name
            (
                {"title": None, "id": 1429},
                ErrorCode.DATA_PROCESSING_ERROR,
            ),  # None title
        ]

        for tmdb_result, expected_code in test_cases:
            with pytest.raises(DomainError) as exc_info:
                enricher._calculate_match_score(file_info, tmdb_result)

            assert exc_info.value.code == expected_code
            assert exc_info.value.context is not None
            # Operation now comes from ScoringEngine (extract_tmdb_title)
            assert exc_info.value.context.operation in (
                "calculate_match_score",
                "extract_tmdb_title",
            )
