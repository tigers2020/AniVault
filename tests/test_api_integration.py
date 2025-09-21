"""Integration tests for TMDB API functionality.

This module contains comprehensive integration tests that test the actual
TMDB API integration, including real API calls, error handling, and rate limiting.
"""

import os
import time
from unittest.mock import Mock, patch

import pytest
import requests

from src.core.tmdb_client import TMDBAnime, TMDBClient


class TestTMDBAPIIntegration:
    """Integration tests for TMDB API functionality."""

    @pytest.fixture
    def api_key(self) -> str:
        """Get TMDB API key from environment or use test key."""
        api_key = os.getenv("TMDB_API_KEY")
        if not api_key:
            pytest.skip("TMDB_API_KEY environment variable not set")
        return api_key

    @pytest.fixture
    def tmdb_client(self, api_key: str) -> TMDBClient:
        """Create TMDBClient instance for testing."""
        from src.core.tmdb_client import TMDBConfig

        config = TMDBConfig(api_key=api_key)
        return TMDBClient(config=config)

    def test_real_api_search_anime(self, tmdb_client: TMDBClient) -> None:
        """Test real API search for anime."""
        # Test with a well-known anime
        results = tmdb_client.search_anime("Attack on Titan")

        assert len(results) > 0
        assert all(isinstance(anime, TMDBAnime) for anime in results)

        # Verify the first result has expected properties
        first_result = results[0]
        assert first_result.title is not None
        assert first_result.overview is not None
        assert first_result.release_date is not None
        assert first_result.vote_average >= 0
        assert first_result.vote_count >= 0

    def test_real_api_get_anime_details(self, tmdb_client: TMDBClient) -> None:
        """Test real API get anime details."""
        # First search for an anime to get an ID
        search_results = tmdb_client.search_anime("Attack on Titan")
        assert len(search_results) > 0

        anime_id = search_results[0].id
        details = tmdb_client.get_anime_details(anime_id)

        assert details is not None
        assert details.id == anime_id
        assert details.title is not None
        assert details.overview is not None

    def test_api_rate_limiting(self, tmdb_client: TMDBClient) -> None:
        """Test API rate limiting behavior."""
        # Make multiple rapid requests to test rate limiting
        start_time = time.time()

        for i in range(5):  # Make 5 requests
            try:
                _results, _success = tmdb_client.search_comprehensive(f"Test Anime {i}")
                # Small delay to avoid hitting rate limits
                time.sleep(0.1)
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:  # Rate limited
                    # This is expected behavior
                    break
                else:
                    raise

        # Should complete within reasonable time
        duration = time.time() - start_time
        assert duration < 10.0  # Should complete within 10 seconds

    def test_api_network_error_handling(self, tmdb_client: TMDBClient) -> None:
        """Test API error handling for network issues."""
        # Mock requests to simulate network error
        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError("Network error")

            # Should handle network error gracefully
            results, success = tmdb_client.search_comprehensive("Test")
            assert results is None or results == []  # Should return None or empty list on error
            assert success is False  # Should indicate failure

    def test_api_invalid_key_handling(self) -> None:
        """Test API behavior with invalid API key."""
        from src.core.tmdb_client import TMDBConfig

        config = TMDBConfig(api_key="invalid_key")
        invalid_client = TMDBClient(config=config)

        # Should handle invalid key gracefully
        results, success = invalid_client.search_comprehensive("Test")
        assert results is None or results == []  # Should return None or empty list on error
        assert success is False  # Should indicate failure

    def test_api_timeout_handling(self, tmdb_client: TMDBClient) -> None:
        """Test API timeout handling."""
        # Mock requests to simulate timeout
        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout("Request timeout")

            # Should handle timeout gracefully
            results, success = tmdb_client.search_comprehensive("Test")
            assert results is None or results == []  # Should return None or empty list on error
            assert success is False  # Should indicate failure

    def test_api_http_error_handling(self, tmdb_client: TMDBClient) -> None:
        """Test API HTTP error handling."""
        # Mock requests to simulate HTTP error
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
                "Server error"
            )
            mock_get.return_value = mock_response

            # Should handle HTTP error gracefully
            results, success = tmdb_client.search_comprehensive("Test")
            assert results is None or results == []  # Should return None or empty list on error
            assert success is False  # Should indicate failure

    def test_api_search_with_special_characters(self, tmdb_client: TMDBClient) -> None:
        """Test API search with special characters."""
        # Test with anime titles containing special characters
        special_titles = [
            "Attack on Titan: The Final Season",
            "One Piece: Stampede",
            "Naruto: Shippuden",
            "Dragon Ball Z",
        ]

        for title in special_titles:
            results = tmdb_client.search_anime(title)
            # Should handle special characters gracefully
            assert isinstance(results, list)
            # Small delay to avoid rate limiting
            time.sleep(0.1)

    def test_api_search_empty_query(self, tmdb_client: TMDBClient) -> None:
        """Test API search with empty query."""
        results = tmdb_client.search_anime("")
        assert results == []  # Should return empty list for empty query

    def test_api_search_very_long_query(self, tmdb_client: TMDBClient) -> None:
        """Test API search with very long query."""
        long_query = "A" * 1000  # Very long query
        results = tmdb_client.search_anime(long_query)
        assert isinstance(results, list)  # Should handle long query gracefully

    def test_api_concurrent_requests(self, tmdb_client: TMDBClient) -> None:
        """Test API with concurrent requests."""
        import queue
        import threading

        results_queue = queue.Queue()

        def search_worker(query: str) -> None:
            try:
                results = tmdb_client.search_anime(query)
                results_queue.put((query, results))
            except Exception as e:
                results_queue.put((query, e))

        # Start multiple threads
        threads = []
        queries = ["Attack on Titan", "One Piece", "Naruto", "Dragon Ball"]

        for query in queries:
            thread = threading.Thread(target=search_worker, args=(query,))
            thread.start()
            threads.append(thread)
            time.sleep(0.1)  # Stagger requests

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)

        # Collect results
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())

        # Should have results for all queries
        assert len(results) == len(queries)

        # All results should be lists (successful searches)
        for query, result in results:
            if isinstance(result, Exception):
                # Some requests might fail due to rate limiting
                continue
            assert isinstance(result, list)

    def test_api_response_validation(self, tmdb_client: TMDBClient) -> None:
        """Test API response validation."""
        results = tmdb_client.search_anime("Attack on Titan")

        if results:  # If we got results
            for anime in results:
                # Validate required fields
                assert hasattr(anime, "id")
                assert hasattr(anime, "title")
                assert hasattr(anime, "overview")
                assert hasattr(anime, "release_date")
                assert hasattr(anime, "vote_average")
                assert hasattr(anime, "vote_count")

                # Validate data types
                assert isinstance(anime.id, int)
                assert isinstance(anime.title, str)
                assert isinstance(anime.overview, str)
                assert isinstance(anime.vote_average, (int, float))
                assert isinstance(anime.vote_count, int)

                # Validate value ranges
                assert anime.vote_average >= 0
                assert anime.vote_average <= 10
                assert anime.vote_count >= 0

    def test_api_retry_mechanism(self, tmdb_client: TMDBClient) -> None:
        """Test API retry mechanism for transient failures."""
        # Mock requests to simulate transient failure followed by success
        call_count = 0

        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call fails
                raise requests.exceptions.ConnectionError("Transient error")
            else:
                # Second call succeeds
                mock_response = Mock()
                mock_response.json.return_value = {
                    "results": [
                        {
                            "id": 1,
                            "title": "Test Anime",
                            "overview": "Test overview",
                            "release_date": "2020-01-01",
                            "vote_average": 8.5,
                            "vote_count": 100,
                        }
                    ]
                }
                mock_response.raise_for_status.return_value = None
                return mock_response

        with patch("requests.get", side_effect=mock_get):
            results = tmdb_client.search_comprehensive("Test")
            # Should retry and eventually succeed
            assert len(results) > 0
            assert call_count > 1  # Should have retried


class TestTMDBAPIPerformance:
    """Performance tests for TMDB API integration."""

    @pytest.fixture
    def api_key(self) -> str:
        """Get TMDB API key from environment or use test key."""
        api_key = os.getenv("TMDB_API_KEY")
        if not api_key:
            pytest.skip("TMDB_API_KEY environment variable not set")
        return api_key

    @pytest.fixture
    def tmdb_client(self, api_key: str) -> TMDBClient:
        """Create TMDBClient instance for testing."""
        from src.core.tmdb_client import TMDBConfig

        config = TMDBConfig(api_key=api_key)
        return TMDBClient(config=config)

    def test_api_response_time(self, tmdb_client: TMDBClient) -> None:
        """Test API response time."""
        start_time = time.time()
        results = tmdb_client.search_anime("Attack on Titan")
        response_time = time.time() - start_time

        # Should respond within reasonable time
        assert response_time < 5.0  # Should respond within 5 seconds
        assert isinstance(results, list)

    def test_api_memory_usage(self, tmdb_client: TMDBClient) -> None:
        """Test API memory usage with multiple requests."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Make multiple requests
        for i in range(10):
            tmdb_client.search_anime(f"Test Anime {i}")
            time.sleep(0.1)  # Small delay to avoid rate limiting

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 10MB)
        assert memory_increase < 10 * 1024 * 1024  # 10MB

    def test_api_concurrent_performance(self, tmdb_client: TMDBClient) -> None:
        """Test API performance with concurrent requests."""
        import queue
        import threading
        import time

        results_queue = queue.Queue()

        def search_worker(query: str) -> None:
            start_time = time.time()
            try:
                results = tmdb_client.search_anime(query)
                end_time = time.time()
                results_queue.put((query, results, end_time - start_time))
            except Exception as e:
                end_time = time.time()
                results_queue.put((query, e, end_time - start_time))

        # Start multiple threads
        threads = []
        queries = ["Attack on Titan", "One Piece", "Naruto", "Dragon Ball", "Bleach"]

        start_time = time.time()
        for query in queries:
            thread = threading.Thread(target=search_worker, args=(query,))
            thread.start()
            threads.append(thread)
            time.sleep(0.1)  # Stagger requests

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=15)

        total_time = time.time() - start_time

        # Should complete all requests within reasonable time
        assert total_time < 20.0  # Should complete within 20 seconds

        # Collect results
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())

        # Should have results for most queries
        assert len(results) >= len(queries) * 0.8  # At least 80% success rate
