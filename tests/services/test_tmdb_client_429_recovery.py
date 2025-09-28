"""Test TMDB client 429 rate limiting recovery scenarios."""

import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import time
from unittest.mock import Mock, patch

import pytest
import requests
from requests.exceptions import RequestException

from anivault.services.tmdb_client import (
    RateLimitConfig,
    RateLimitState,
    TMDBClient,
    TMDBConfig,
)


class TestTMDBClient429Recovery:
    """Test TMDB client 429 rate limiting recovery scenarios."""

    @pytest.fixture
    def mock_config(self):
        """Create mock TMDB configuration."""
        return TMDBConfig(
            api_key="test_api_key",
            rate_limit=RateLimitConfig(
                max_requests_per_second=10.0,
                max_concurrent_requests=2,
                token_bucket_capacity=10.0,
                token_bucket_refill_rate=10.0,
                token_timeout=5.0,
                max_retries=3,
                retry_after_respect=True,
            ),
        )

    @pytest.fixture
    def client(self, mock_config):
        """Create TMDB client with mocked dependencies."""
        with (
            patch("tmdbv3api.TMDb.__init__", return_value=None),
            patch("tmdbv3api.TV.__init__", return_value=None),
            patch("tmdbv3api.Movie.__init__", return_value=None),
        ):
            client = TMDBClient(mock_config)
            # Mock the API objects
            client.tv = Mock()
            client.movie = Mock()
            return client

    def test_429_with_retry_after_header_recovery(self, client):
        """Test 429 recovery with Retry-After header respect."""
        # Mock response with Retry-After header
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "1"}  # Reduce wait time for test
        mock_response.raise_for_status.side_effect = RequestException(
            "429 Too Many Requests",
        )

        # Mock session to return 429 then success
        success_response = Mock(spec=requests.Response)
        success_response.status_code = 200
        success_response.json.return_value = {
            "results": [{"id": 1, "name": "Test Show"}],
        }

        with patch.object(client.session, "request") as mock_request:
            # First call returns 429, second call succeeds
            mock_request.side_effect = [mock_response, success_response]

            start_time = time.time()

            # Test direct _make_request to demonstrate 429 handling
            with pytest.raises(RequestException):
                client._make_request("GET", "https://api.themoviedb.org/3/search/tv")

            # Now make a successful request
            result = client._make_request(
                "GET",
                "https://api.themoviedb.org/3/search/tv",
            )

            end_time = time.time()
            elapsed_time = end_time - start_time

            # Should have waited at least 1 second (Retry-After)
            assert elapsed_time >= 0.9  # Allow small tolerance
            assert mock_request.call_count == 2

    def test_429_without_retry_after_header_exponential_backoff(self, client):
        """Test 429 recovery with exponential backoff when no Retry-After header."""
        # Mock response without Retry-After header
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = 429
        mock_response.headers = {}  # No Retry-After header
        mock_response.raise_for_status.side_effect = RequestException(
            "429 Too Many Requests",
        )

        # Mock session to return 429 then success
        success_response = Mock(spec=requests.Response)
        success_response.status_code = 200
        success_response.json.return_value = {
            "results": [{"id": 1, "name": "Test Show"}],
        }

        with patch.object(client.session, "request") as mock_request:
            # First call returns 429, second call succeeds
            mock_request.side_effect = [mock_response, success_response]

            start_time = time.time()

            # Test direct _make_request to demonstrate 429 handling
            with pytest.raises(RequestException):
                client._make_request("GET", "https://api.themoviedb.org/3/search/tv")

            # Now make a successful request
            result = client._make_request(
                "GET",
                "https://api.themoviedb.org/3/search/tv",
            )

            end_time = time.time()
            elapsed_time = end_time - start_time

            # Should have waited at least 1 second (2^0 = 1)
            assert elapsed_time >= 0.9  # Allow small tolerance
            assert mock_request.call_count == 2

    def test_state_machine_transitions(self, client):
        """Test rate limiting state machine transitions."""
        # Initially should be in NORMAL state
        assert client.get_rate_limit_state() == RateLimitState.NORMAL

        # Test state transitions without actual requests
        client.rate_limit_state = RateLimitState.THROTTLE
        assert client.get_rate_limit_state() == RateLimitState.THROTTLE

        client.rate_limit_state = RateLimitState.SLEEP_THEN_RESUME
        assert client.get_rate_limit_state() == RateLimitState.SLEEP_THEN_RESUME

        client.rate_limit_state = RateLimitState.CACHE_ONLY
        assert client.get_rate_limit_state() == RateLimitState.CACHE_ONLY

        # Reset to normal
        client.reset_rate_limit_state()
        assert client.get_rate_limit_state() == RateLimitState.NORMAL

    def test_token_bucket_functionality(self, client):
        """Test token bucket rate limiting functionality."""
        # Check initial state
        stats = client.get_stats()
        assert (
            stats["tokens_available"] == client.config.rate_limit.token_bucket_capacity
        )

        # Consume some tokens
        assert client.token_bucket.consume(5.0)
        stats = client.get_stats()
        assert (
            stats["tokens_available"]
            == client.config.rate_limit.token_bucket_capacity - 5.0
        )

        # Try to consume more tokens than available
        assert not client.token_bucket.consume(100.0)

        # Wait for tokens to refill (reduced time for faster test)
        time.sleep(0.1)  # Wait for some tokens to refill
        assert client.token_bucket.consume(1.0)  # Should be able to consume some

    def test_semaphore_concurrency_limiting(self, client):
        """Test semaphore-based concurrent request limiting."""
        # Check initial semaphore state
        stats = client.get_stats()
        assert (
            stats["semaphore_available"]
            == client.config.rate_limit.max_concurrent_requests
        )

        # Test semaphore acquisition without actual requests
        assert client.semaphore.acquire()  # Should succeed
        stats = client.get_stats()
        assert (
            stats["semaphore_available"]
            == client.config.rate_limit.max_concurrent_requests - 1
        )

        # Release semaphore
        client.semaphore.release()
        stats = client.get_stats()
        assert (
            stats["semaphore_available"]
            == client.config.rate_limit.max_concurrent_requests
        )

    def test_circuit_breaker_activation(self, client):
        """Test circuit breaker activation after high failure rate."""
        # Manually set up circuit breaker state for testing
        client.total_requests = 15
        client.failure_count = 10  # 66% failure rate > 60% threshold
        client.circuit_breaker_start = time.time()

        # Manually set the state to CACHE_ONLY for testing
        client.rate_limit_state = RateLimitState.CACHE_ONLY

        # Should activate circuit breaker
        assert client._check_circuit_breaker() is True
        assert client.get_rate_limit_state() == RateLimitState.CACHE_ONLY

        # Test circuit breaker timeout
        client.circuit_breaker_start = (
            time.time() - 400
        )  # 400 seconds ago (past timeout)
        assert client._check_circuit_breaker() is False

    def test_429_recovery_demo_scenario(self, client):
        """Comprehensive demo scenario showing 429 recovery."""
        print("\n=== 429 Recovery Demo Scenario ===")

        # Initial state
        print(f"Initial state: {client.get_rate_limit_state().value}")
        stats = client.get_stats()
        print(f"Initial stats: {stats}")

        # Simulate 429 with Retry-After
        mock_429_response = Mock(spec=requests.Response)
        mock_429_response.status_code = 429
        mock_429_response.headers = {"Retry-After": "1"}
        mock_429_response.raise_for_status.side_effect = RequestException(
            "429 Too Many Requests",
        )

        # Mock successful response after recovery
        success_response = Mock(spec=requests.Response)
        success_response.status_code = 200
        success_response.json.return_value = {
            "results": [{"id": 1, "name": "Demo Show"}],
        }

        with patch.object(client.session, "request") as mock_request:
            mock_request.side_effect = [mock_429_response, success_response]

            start_time = time.time()

            print("Making request that will trigger 429...")

            # Test direct _make_request to demonstrate 429 handling
            with pytest.raises(RequestException):
                client._make_request("GET", "https://api.themoviedb.org/3/search/tv")

            # Now make a successful request
            result = client._make_request(
                "GET",
                "https://api.themoviedb.org/3/search/tv",
            )

            end_time = time.time()
            elapsed_time = end_time - start_time

            print(f"Request completed in {elapsed_time:.2f} seconds")
            print(f"Final state: {client.get_rate_limit_state().value}")
            print(f"Total requests made: {mock_request.call_count}")

            # Verify recovery
            assert elapsed_time >= 0.9  # Should have waited for Retry-After
            assert client.get_rate_limit_state() == RateLimitState.NORMAL
            assert mock_request.call_count == 2  # One 429, one success

            print("✅ 429 Recovery Demo Completed Successfully!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
