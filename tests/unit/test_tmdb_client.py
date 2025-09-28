"""Test TMDB client functionality and rate limiting."""

import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import time
from unittest.mock import Mock, patch

import pytest
from requests.exceptions import RequestException, Timeout

from anivault.services.tmdb_client import (
    RateLimitConfig,
    RateLimitState,
    TMDBClient,
    TMDBConfig,
)


class TestTMDBClient:
    """Test TMDB client functionality."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return TMDBConfig(
            api_key="test_api_key",
            rate_limit=RateLimitConfig(
                max_requests_per_second=10.0,  # Fast for testing
                max_concurrent_requests=2,
                max_retries=2,
                circuit_breaker_threshold=0.5,
                circuit_breaker_timeout=60,
            ),
        )

    @pytest.fixture
    def client(self, config):
        """Create test client."""
        with patch("tmdbv3api.TMDb"), patch("tmdbv3api.TV"), patch("tmdbv3api.Movie"):
            return TMDBClient(config)

    def test_client_initialization(self, config):
        """Test client initialization."""
        with (
            patch("tmdbv3api.TMDb") as mock_tmdb,
            patch("tmdbv3api.TV") as mock_tv,
            patch("tmdbv3api.Movie") as mock_movie,
        ):
            client = TMDBClient(config)

            assert client.config == config
            assert client.rate_limit_state == RateLimitState.NORMAL
            assert client.request_count == 0
            assert client.failure_count == 0
            assert client.circuit_breaker_start is None

            # Verify TMDB API was initialized
            mock_tmdb.assert_called_once()
            mock_tv.assert_called_once()
            mock_movie.assert_called_once()

    def test_rate_limit_check(self, client):
        """Test rate limiting functionality."""
        # Test normal operation
        assert client._check_rate_limit() is True

        # Test rate limiting with fast requests
        client.config.rate_limit.max_requests_per_second = 1.0
        start_time = time.time()

        # First request should pass
        assert client._check_rate_limit() is True

        # Second request should be delayed
        client._check_rate_limit()
        elapsed = time.time() - start_time
        assert elapsed >= 0.9  # Should wait ~1 second

    def test_handle_429_error_with_retry_after(self, client):
        """Test handling 429 error with Retry-After header."""
        mock_response = Mock()
        mock_response.headers = {"Retry-After": "2"}
        mock_response.status_code = 429

        with patch("time.sleep") as mock_sleep:
            client._handle_429_error(mock_response)

            assert client.rate_limit_state == RateLimitState.THROTTLE
            assert client.failure_count == 1
            mock_sleep.assert_called_once_with(2.0)

    def test_handle_429_error_without_retry_after(self, client):
        """Test handling 429 error without Retry-After header."""
        mock_response = Mock()
        mock_response.headers = {}
        mock_response.status_code = 429

        with patch("time.sleep") as mock_sleep:
            client._handle_429_error(mock_response)

            assert client.rate_limit_state == RateLimitState.THROTTLE
            assert client.failure_count == 1
            mock_sleep.assert_called_once_with(1.0)  # Exponential backoff

    def test_circuit_breaker_activation(self, client):
        """Test circuit breaker activation."""
        # Simulate high failure rate
        client.total_requests = 20
        client.failure_count = 15  # 75% failure rate

        client._update_circuit_breaker(False)  # Another failure

        assert client.circuit_breaker_start is not None
        assert client.rate_limit_state == RateLimitState.CACHE_ONLY

    def test_circuit_breaker_timeout(self, client):
        """Test circuit breaker timeout."""
        # Activate circuit breaker
        client.circuit_breaker_start = time.time() - 70  # 70 seconds ago
        client.rate_limit_state = RateLimitState.CACHE_ONLY

        # Check circuit breaker
        result = client._check_circuit_breaker()

        assert result is False  # Should be closed
        assert client.circuit_breaker_start is None
        assert client.rate_limit_state == RateLimitState.NORMAL
        assert client.failure_count == 0

    def test_make_request_success(self, client):
        """Test successful request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}

        with patch.object(
            client.session,
            "request",
            return_value=mock_response,
        ) as mock_request:
            response = client._make_request("GET", "https://api.test.com/test")

            assert response == mock_response
            assert client.request_count == 1
            assert client.failure_count == 0
            assert client.rate_limit_state == RateLimitState.NORMAL

    def test_make_request_429_error(self, client):
        """Test request with 429 error."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "1"}

        with (
            patch.object(client.session, "request", return_value=mock_response),
            patch("time.sleep"),
        ):
            with pytest.raises(RequestException, match="Rate limited"):
                client._make_request("GET", "https://api.test.com/test")

            assert client.failure_count == 1
            assert client.rate_limit_state == RateLimitState.THROTTLE

    def test_make_request_timeout(self, client):
        """Test request timeout."""
        with patch.object(
            client.session,
            "request",
            side_effect=Timeout("Request timeout"),
        ):
            with pytest.raises(Timeout):
                client._make_request("GET", "https://api.test.com/test")

            assert client.failure_count == 1

    def test_search_tv_success(self, client):
        """Test successful TV search."""
        mock_results = [{"id": 1, "name": "Test Show"}]

        with patch.object(client.tv, "search", return_value=mock_results):
            results = client.search_tv("Test Show")

            assert results == mock_results

    def test_search_tv_failure(self, client):
        """Test TV search failure."""
        with patch.object(client.tv, "search", side_effect=Exception("API Error")):
            with pytest.raises(Exception, match="API Error"):
                client.search_tv("Test Show")

    def test_get_tv_details_success(self, client):
        """Test successful TV details retrieval."""
        mock_details = {"id": 1, "name": "Test Show", "overview": "Test overview"}

        with patch.object(client.tv, "details", return_value=mock_details):
            details = client.get_tv_details(1)

            assert details == mock_details

    def test_search_movie_success(self, client):
        """Test successful movie search."""
        mock_results = [{"id": 1, "title": "Test Movie"}]

        with patch.object(client.movie, "search", return_value=mock_results):
            results = client.search_movie("Test Movie")

            assert results == mock_results

    def test_get_movie_details_success(self, client):
        """Test successful movie details retrieval."""
        mock_details = {"id": 1, "title": "Test Movie", "overview": "Test overview"}

        with patch.object(client.movie, "details", return_value=mock_details):
            details = client.get_movie_details(1)

            assert details == mock_details

    def test_get_rate_limit_status(self, client):
        """Test rate limit status reporting."""
        client.request_count = 10
        client.failure_count = 2
        client.total_requests = 10
        client.last_request_time = time.time()

        status = client.get_rate_limit_status()

        assert status["request_count"] == 10
        assert status["failure_count"] == 2
        assert status["total_requests"] == 10
        assert status["failure_rate"] == 0.2
        assert status["circuit_breaker_open"] is False
        assert "last_request_time" in status

    def test_reset_rate_limit(self, client):
        """Test rate limit reset."""
        # Set some state
        client.rate_limit_state = RateLimitState.THROTTLE
        client.failure_count = 5
        client.circuit_breaker_start = time.time()

        client.reset_rate_limit()

        assert client.rate_limit_state == RateLimitState.NORMAL
        assert client.failure_count == 0
        assert client.circuit_breaker_start is None

    def test_close(self, client):
        """Test client cleanup."""
        with patch.object(client.session, "close") as mock_close:
            client.close()
            mock_close.assert_called_once()


class TestTMDBClientIntegration:
    """Integration tests for TMDB client."""

    @pytest.mark.slow
    def test_memory_usage_over_time(self, config):
        """Test memory usage over extended period."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        with patch("tmdbv3api.TMDb"), patch("tmdbv3api.TV"), patch("tmdbv3api.Movie"):
            client = TMDBClient(config)

            # Simulate many requests
            for i in range(100):
                with patch.object(client, "_make_request") as mock_request:
                    mock_response = Mock()
                    mock_response.status_code = 200
                    mock_request.return_value = mock_response

                    client._make_request("GET", f"https://api.test.com/test{i}")

            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory

            # Memory increase should be reasonable (< 10MB)
            assert memory_increase < 10 * 1024 * 1024, (
                f"Memory increased by {memory_increase / 1024 / 1024:.2f}MB"
            )

            client.close()

    @pytest.mark.integration
    def test_real_api_key_validation(self):
        """Test with real API key (if available)."""
        api_key = "test_key"  # Replace with real key for integration testing

        if api_key == "test_key":
            pytest.skip("No real API key provided for integration test")

        config = TMDBConfig(api_key=api_key)
        client = TMDBClient(config)

        try:
            # Test basic functionality
            results = client.search_tv("Attack on Titan")
            assert isinstance(results, list)

            if results:
                details = client.get_tv_details(results[0]["id"])
                assert "id" in details
                assert "name" in details

        finally:
            client.close()


if __name__ == "__main__":
    pytest.main([__file__])
