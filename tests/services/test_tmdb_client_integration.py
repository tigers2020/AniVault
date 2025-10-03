"""Integration tests for TMDB client with rate limiting and error handling.

This module contains comprehensive integration tests that validate the TMDB client
works correctly with all its components under various load and error conditions.
"""

import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest
from pytest_httpserver import HTTPServer
from werkzeug import Response

from anivault.services.rate_limiter import TokenBucketRateLimiter
from anivault.services.semaphore_manager import SemaphoreManager
from anivault.services.state_machine import RateLimitState, RateLimitStateMachine
from anivault.services.tmdb_client import TMDBClient


class TestTMDBClientIntegration:
    """Integration tests for TMDB client with all components."""

    @pytest.fixture
    def mock_tmdb_server(self):
        """Create a mock TMDB API server for testing."""
        server = HTTPServer(host="127.0.0.1", port=0)
        server.start()
        yield server
        server.stop()

    @pytest.fixture
    def tmdb_client(self, mock_tmdb_server):
        """Create a TMDB client configured to use the mock server."""
        # Mock the config to use our test server
        with patch("anivault.services.tmdb_client.get_config") as mock_config:
            mock_config.return_value.tmdb.api_key = (
                "test_api_key"  # pragma: allowlist secret
            )
            mock_config.return_value.tmdb.base_url = (
                f"http://{mock_tmdb_server.host}:{mock_tmdb_server.port}"
            )
            mock_config.return_value.tmdb.timeout = 30
            mock_config.return_value.tmdb.retry_attempts = 3
            mock_config.return_value.tmdb.retry_delay = 0.1
            mock_config.return_value.tmdb.rate_limit_rps = 35.0
            mock_config.return_value.tmdb.concurrent_requests = 4
            mock_config.return_value.app.debug = True

            # Create client with test components
            rate_limiter = TokenBucketRateLimiter(capacity=35, refill_rate=35.0)
            semaphore_manager = SemaphoreManager(concurrency_limit=4)
            state_machine = RateLimitStateMachine()

            client = TMDBClient(
                rate_limiter=rate_limiter,
                semaphore_manager=semaphore_manager,
                state_machine=state_machine,
            )

            # Mock the TMDB API objects to use our test server
            with patch.object(client, "_tmdb") as mock_tmdb:
                mock_tmdb.api_key = "test_api_key"
                mock_tmdb.language = "en"
                mock_tmdb.debug = True

                yield client

    def test_successful_search_flow(self, tmdb_client, mock_tmdb_server):
        """Test successful search flow with rate limiting and concurrency control."""
        # Setup mock responses
        mock_tv_response = {
            "results": [
                {
                    "id": 1,
                    "name": "Test TV Show",
                    "overview": "A test TV show",
                    "first_air_date": "2023-01-01",
                }
            ]
        }

        mock_movie_response = {
            "results": [
                {
                    "id": 2,
                    "title": "Test Movie",
                    "overview": "A test movie",
                    "release_date": "2023-01-01",
                }
            ]
        }

        # Configure mock server responses
        mock_tmdb_server.expect_request(
            "/3/search/tv", query_string="api_key=test_api_key&language=en&query=test"
        ).respond_with_json(mock_tv_response)

        mock_tmdb_server.expect_request(
            "/3/search/movie",
            query_string="api_key=test_api_key&language=en&query=test",
        ).respond_with_json(mock_movie_response)

        # Mock the TMDB API calls
        with (
            patch.object(tmdb_client._tv, "search") as mock_tv_search,
            patch.object(tmdb_client._movie, "search") as mock_movie_search,
        ):
            mock_tv_search.return_value = mock_tv_response["results"]
            mock_movie_search.return_value = mock_movie_response["results"]

            # Run the test
            results = asyncio.run(tmdb_client.search_media("test"))

            # Verify results
            assert len(results) == 2
            assert results[0]["media_type"] == "tv"
            assert results[0]["name"] == "Test TV Show"
            assert results[1]["media_type"] == "movie"
            assert results[1]["title"] == "Test Movie"

    def test_429_recovery_mechanism(self, tmdb_client, mock_tmdb_server):
        """Test 429 error recovery with Retry-After header."""
        # Setup mock responses - first 429, then success
        mock_tv_response = {
            "results": [{"id": 1, "name": "Test TV Show", "overview": "A test TV show"}]
        }

        call_count = 0

        def mock_tv_search(title):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call returns 429
                raise Exception("429 Too Many Requests")
            else:
                # Subsequent calls return success
                return mock_tv_response["results"]

        # Mock the TMDB API calls
        with (
            patch.object(tmdb_client._tv, "search", side_effect=mock_tv_search),
            patch.object(tmdb_client._movie, "search", return_value=[]),
        ):
            # Mock the 429 exception with Retry-After header
            with patch("anivault.services.tmdb_client.TMDbException") as mock_exception:
                mock_exception.side_effect = Exception("429 Too Many Requests")

                # Run the test
                start_time = time.time()
                results = asyncio.run(tmdb_client.search_media("test"))
                end_time = time.time()

                # Verify results
                assert len(results) == 1
                assert results[0]["media_type"] == "tv"
                assert results[0]["name"] == "Test TV Show"

                # Verify retry occurred
                assert call_count == 2

    def test_high_concurrency_load(self, tmdb_client, mock_tmdb_server):
        """Test high concurrency load with rate limiting."""
        # Setup mock responses
        mock_response = {
            "results": [{"id": 1, "name": "Test Show", "overview": "A test show"}]
        }

        # Mock the TMDB API calls
        with (
            patch.object(
                tmdb_client._tv, "search", return_value=mock_response["results"]
            ),
            patch.object(tmdb_client._movie, "search", return_value=[]),
        ):
            # Run concurrent requests
            async def make_request(i):
                return await tmdb_client.search_media(f"test {i}")

            start_time = time.time()
            results = asyncio.run(self._run_concurrent_requests(make_request, 20))
            end_time = time.time()

            # Calculate metrics
            total_time = end_time - start_time
            rps = 20 / total_time

            # Verify results
            assert len(results) == 20
            assert rps <= 35.0  # Should respect rate limit
            assert rps > 10.0  # Should be reasonably fast

    def test_circuit_breaker_activation(self, tmdb_client, mock_tmdb_server):
        """Test circuit breaker activation under high error rate."""
        # Mock high error rate
        with (
            patch.object(
                tmdb_client._tv,
                "search",
                side_effect=Exception("500 Internal Server Error"),
            ),
            patch.object(
                tmdb_client._movie,
                "search",
                side_effect=Exception("500 Internal Server Error"),
            ),
        ):
            # Generate many errors to trigger circuit breaker
            for i in range(10):
                try:
                    asyncio.run(tmdb_client.search_media(f"test {i}"))
                except Exception:
                    pass

            # Verify circuit breaker is activated
            assert tmdb_client.state_machine.state == RateLimitState.CACHE_ONLY

            # Verify no more requests are made
            with pytest.raises(Exception, match="Service in cache-only mode"):
                asyncio.run(tmdb_client.search_media("test"))

    def test_semaphore_concurrency_limit(self, tmdb_client, mock_tmdb_server):
        """Test that semaphore properly limits concurrent requests."""
        # Track concurrent requests
        concurrent_requests = 0
        max_concurrent = 0

        def mock_search(title):
            nonlocal concurrent_requests, max_concurrent
            concurrent_requests += 1
            max_concurrent = max(max_concurrent, concurrent_requests)
            time.sleep(0.1)  # Simulate API delay
            concurrent_requests -= 1
            return []

        # Mock the TMDB API calls
        with (
            patch.object(tmdb_client._tv, "search", side_effect=mock_search),
            patch.object(tmdb_client._movie, "search", side_effect=mock_search),
        ):
            # Run more requests than concurrency limit
            async def make_request(i):
                return await tmdb_client.search_media(f"test {i}")

            asyncio.run(self._run_concurrent_requests(make_request, 10))

            # Verify concurrency was limited
            assert max_concurrent <= 4  # Should not exceed semaphore limit

    def test_rate_limiter_token_bucket(self, tmdb_client, mock_tmdb_server):
        """Test that rate limiter properly controls request rate."""
        # Mock fast API responses
        with (
            patch.object(tmdb_client._tv, "search", return_value=[]),
            patch.object(tmdb_client._movie, "search", return_value=[]),
        ):
            # Make many requests quickly
            start_time = time.time()
            for i in range(50):
                asyncio.run(tmdb_client.search_media(f"test {i}"))
            end_time = time.time()

            # Calculate actual RPS
            total_time = end_time - start_time
            actual_rps = 50 / total_time

            # Verify rate limiting worked
            assert actual_rps <= 35.0  # Should respect rate limit

    def test_state_machine_transitions(self, tmdb_client, mock_tmdb_server):
        """Test state machine transitions under different conditions."""
        # Start in NORMAL state
        assert tmdb_client.state_machine.state == RateLimitState.NORMAL

        # Test 429 handling
        with (
            patch.object(
                tmdb_client._tv,
                "search",
                side_effect=Exception("429 Too Many Requests"),
            ),
            patch.object(tmdb_client._movie, "search", return_value=[]),
        ):
            try:
                asyncio.run(tmdb_client.search_media("test"))
            except Exception:
                pass

            # Should transition to THROTTLE state
            assert tmdb_client.state_machine.state == RateLimitState.THROTTLE

        # Test recovery
        with (
            patch.object(tmdb_client._tv, "search", return_value=[]),
            patch.object(tmdb_client._movie, "search", return_value=[]),
        ):
            asyncio.run(tmdb_client.search_media("test"))

            # Should transition back to NORMAL
            assert tmdb_client.state_machine.state == RateLimitState.NORMAL

    def test_performance_metrics(self, tmdb_client, mock_tmdb_server):
        """Test performance metrics collection."""
        # Mock API responses
        with (
            patch.object(tmdb_client._tv, "search", return_value=[]),
            patch.object(tmdb_client._movie, "search", return_value=[]),
        ):
            # Make some requests
            for i in range(5):
                asyncio.run(tmdb_client.search_media(f"test {i}"))

            # Get stats
            stats = tmdb_client.get_stats()

            # Verify stats structure
            assert "rate_limiter" in stats
            assert "semaphore_manager" in stats
            assert "state_machine" in stats

            # Verify rate limiter stats
            assert "tokens_available" in stats["rate_limiter"]
            assert "capacity" in stats["rate_limiter"]
            assert "refill_rate" in stats["rate_limiter"]

            # Verify semaphore stats
            assert "active_requests" in stats["semaphore_manager"]
            assert "available_slots" in stats["semaphore_manager"]
            assert "concurrency_limit" in stats["semaphore_manager"]

            # Verify state machine stats
            assert "state" in stats["state_machine"]
            assert "recent_errors" in stats["state_machine"]
            assert "recent_successes" in stats["state_machine"]
            assert "error_rate_percent" in stats["state_machine"]

    async def _run_concurrent_requests(self, request_func, num_requests):
        """Helper method to run concurrent requests."""
        tasks = [request_func(i) for i in range(num_requests)]
        return await asyncio.gather(*tasks, return_exceptions=True)


class TestTMDBClientPerformance:
    """Performance tests for TMDB client under load."""

    @pytest.mark.benchmark
    def test_throughput_under_load(self):
        """Test system throughput under sustained load."""
        # This test would run against a real or more sophisticated mock
        # to measure actual performance characteristics
        pass

    @pytest.mark.benchmark
    def test_memory_usage_under_load(self):
        """Test memory usage under sustained load."""
        # This test would monitor memory usage during load testing
        pass

    @pytest.mark.benchmark
    def test_response_time_percentiles(self):
        """Test response time percentiles under load."""
        # This test would measure P50, P95, P99 response times
        pass
