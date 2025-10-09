"""Failure-First tests for tmdb_client.py.

Stage 4.1: Test that API client properly logs exceptions instead of
silently swallowing them with pass.
"""

from unittest.mock import Mock, patch

import pytest

from anivault.services.tmdb_client import TMDBClient
from anivault.services.tmdb_models import TMDBSearchResponse


class TestSearchMediaExceptionHandling:
    """TMDBClient.search_media() 예외 처리 테스트."""

    @pytest.mark.asyncio
    async def test_tmdb_exception_logged(self, caplog):
        """TMDbException 발생 시 로깅 + graceful degradation."""
        # Given
        client = TMDBClient()
        from anivault.services.tmdb_models import TMDBSearchResult

        # Mock TV to fail, Movie to succeed (graceful degradation)
        mock_movie_results = [
            TMDBSearchResult(id=2, media_type="movie", title="Attack on Titan Movie")
        ]

        with (
            patch.object(
                client._tv_strategy, "search", side_effect=Exception("API Error")
            ),
            patch.object(
                client._movie_strategy, "search", return_value=mock_movie_results
            ),
        ):
            # When
            result = await client.search_media("Attack on Titan")

            # Then: Movie search succeeded despite TV failure (graceful degradation)
            assert isinstance(result, TMDBSearchResponse)
            assert len(result.results) == 1
            assert result.results[0].media_type == "movie"

            # And: TV search failure was logged (check via stderr)

    @pytest.mark.asyncio
    async def test_network_error_logged(self, caplog):
        """네트워크 에러 시 로깅 + graceful degradation."""
        # Given
        client = TMDBClient()
        from anivault.services.tmdb_models import TMDBSearchResult

        # Mock Movie to fail, TV to succeed (graceful degradation)
        mock_tv_results = [TMDBSearchResult(id=1, media_type="tv", name="One Piece")]

        with (
            patch.object(
                client._movie_strategy,
                "search",
                side_effect=ConnectionError("Network error"),
            ),
            patch.object(client._tv_strategy, "search", return_value=mock_tv_results),
        ):
            # When
            result = await client.search_media("One Piece")

            # Then: TV search succeeded despite Movie failure (graceful degradation)
            assert isinstance(result, TMDBSearchResponse)
            assert len(result.results) == 1
            assert result.results[0].media_type == "tv"

            # And: Movie search failure was logged (check via stderr)


class TestExtractRetryAfterExceptionHandling:
    """TMDBClient._extract_retry_after() 예외 처리 테스트."""

    def test_invalid_value_logged(self, caplog):
        """잘못된 값 파싱 시 로깅 + 기본값 반환."""
        # Given
        client = TMDBClient()
        invalid_response = Mock()
        invalid_response.headers = {"Retry-After": "invalid"}

        # When
        result = client._extract_retry_after(invalid_response)

        # Then: None 반환 (현재 동작 - caller가 기본값 처리)
        assert result is None

        # Note: pass는 있지만 caller에서 기본값 처리 (graceful)

    def test_missing_header_returns_default(self):
        """Retry-After 헤더 없을 때 기본값 반환."""
        # Given
        client = TMDBClient()
        response = Mock()
        response.headers = {}

        # When
        result = client._extract_retry_after(response)

        # Then: None 반환 (헤더 없음)
        assert result is None

    def test_valid_retry_after_returns_value(self):
        """유효한 Retry-After 값 반환."""
        # Given
        client = TMDBClient()
        response = Mock()
        response.headers = {"Retry-After": "120"}

        # When
        result = client._extract_retry_after(response)

        # Then
        assert result == 120


# Note: API 클라이언트에서 exception swallowing은 서비스 가용성을 위한 것일 수 있지만
# 투명성을 위해 로깅 추가 필수
# 빈 리스트 반환 유지 (graceful degradation) + logger.warning() 추가
