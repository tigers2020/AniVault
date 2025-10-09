"""Failure-First tests for metadata_enricher.py.

Stage 2.2: Test that functions explicitly raise exceptions instead of
silently returning None or 0.0 for error conditions.
"""

from unittest.mock import Mock, patch

import pytest

from anivault.core.parser.models import ParsingResult
from anivault.services.metadata_enricher import MetadataEnricher
from anivault.shared.errors import ApplicationError, DomainError, ErrorCode


class TestCalculateTitleSimilarityFailures:
    """_calculate_title_similarity() 실패 케이스 테스트."""

    def test_empty_title1_raises_error(self):
        """첫 번째 제목이 빈 문자열일 때 DomainError 발생."""
        # Given
        enricher = MetadataEnricher()

        # When & Then
        with pytest.raises(DomainError) as exc_info:
            enricher._calculate_title_similarity("", "Attack on Titan")

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
        assert "empty" in str(exc_info.value.message).lower()

    def test_empty_title2_raises_error(self):
        """두 번째 제목이 빈 문자열일 때 DomainError 발생."""
        # Given
        enricher = MetadataEnricher()

        # When & Then
        with pytest.raises(DomainError) as exc_info:
            enricher._calculate_title_similarity("Attack on Titan", "")

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
        assert "empty" in str(exc_info.value.message).lower()

    def test_non_string_title_raises_error(self):
        """문자열이 아닌 타입일 때 DomainError 발생."""
        # Given
        enricher = MetadataEnricher()

        # When & Then
        with pytest.raises(DomainError) as exc_info:
            enricher._calculate_title_similarity(None, "Attack on Titan")  # type: ignore

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR

    def test_valid_titles_returns_score(self):
        """유효한 제목일 때 점수 반환."""
        # Given
        enricher = MetadataEnricher()

        # When
        score = enricher._calculate_title_similarity(
            "Attack on Titan", "Attack on Titan"
        )

        # Then
        assert 0.0 <= score <= 1.0


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
        """file_info가 유효하지 않을 때 DomainError 발생."""
        # Given
        enricher = MetadataEnricher()
        file_info = Mock(spec=ParsingResult)
        file_info.title = ""  # 빈 제목

        search_results = [{"id": 1, "title": "Attack on Titan"}]

        # When & Then
        with pytest.raises(DomainError) as exc_info:
            enricher._find_best_match(file_info, search_results)

        assert exc_info.value.code == ErrorCode.VALIDATION_ERROR

    def test_score_calculation_error_propagates(self):
        """점수 계산 에러가 상위로 전파."""
        # Given
        enricher = MetadataEnricher()
        file_info = Mock(spec=ParsingResult)
        file_info.title = "Attack on Titan"

        # 유효하지 않은 TMDB 결과 (title/name 없음)
        search_results = [{"id": 1}]

        # When & Then: 모든 결과 실패 시 ApplicationError 발생
        with pytest.raises(ApplicationError) as exc_info:
            enricher._find_best_match(file_info, search_results)

        assert exc_info.value.code == ErrorCode.DATA_PROCESSING_ERROR
        assert "all" in str(exc_info.value.message).lower()


# Note: 매칭 알고리즘에서 0.0 점수는 "매칭되지 않음"과 "오류 발생"을 구분할 수 없음
# 리팩토링 후에는 명확한 예외 발생으로 이 문제 해결
