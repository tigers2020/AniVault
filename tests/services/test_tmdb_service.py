"""Test enhanced TMDB service functionality."""

import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import os
from unittest.mock import Mock, patch

import pytest
from requests.exceptions import RequestException

from anivault.services.tmdb_service import RobustTMDb, TMDBService


class TestRobustTMDb:
    """Test RobustTMDb class functionality."""

    @pytest.fixture
    def robust_tmdb(self):
        """Create test RobustTMDb instance."""
        with patch("tmdbv3api.TMDb.__init__"):
            return RobustTMDb(max_retries=3, proactive_delay_ms=10)

    def test_initialization(self, robust_tmdb):
        """Test RobustTMDb initialization."""
        assert robust_tmdb._max_retries == 3
        assert robust_tmdb._proactive_delay_ms == 10

    def test_parse_retry_after_integer(self, robust_tmdb):
        """Test parsing integer Retry-After header."""
        wait_time = robust_tmdb._parse_retry_after("5")
        assert wait_time == 5.0

    def test_parse_retry_after_date(self, robust_tmdb):
        """Test parsing HTTP-date Retry-After header."""
        # Use a future date to ensure positive wait time
        future_date = "Mon, 01 Jan 2030 12:00:00 GMT"
        wait_time = robust_tmdb._parse_retry_after(future_date)
        assert wait_time > 0  # Should be positive

    def test_parse_retry_after_invalid(self, robust_tmdb):
        """Test parsing invalid Retry-After header."""
        wait_time = robust_tmdb._parse_retry_after("invalid")
        assert wait_time == 5.0  # Default fallback

    def test_parse_retry_after_none(self, robust_tmdb):
        """Test parsing None Retry-After header."""
        wait_time = robust_tmdb._parse_retry_after(None)
        assert wait_time == 5.0  # Default fallback

    def test_call_success(self, robust_tmdb):
        """Test successful API call."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 123, "title": "Test"}

        with patch.object(robust_tmdb, "_session") as mock_session:
            mock_session.get.return_value = mock_response
            result = robust_tmdb._call("https://api.test.com/test", {})

            assert result == {"id": 123, "title": "Test"}
            mock_session.get.assert_called_once()

    def test_call_429_with_retry_after(self, robust_tmdb):
        """Test handling 429 with Retry-After header."""
        # First response: 429 with Retry-After
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {"Retry-After": "1"}

        # Second response: success
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"id": 123, "title": "Test"}

        with (
            patch.object(robust_tmdb, "_session") as mock_session,
            patch("time.sleep") as mock_sleep,
        ):
            mock_session.get.side_effect = [mock_response_429, mock_response_success]

            result = robust_tmdb._call("https://api.test.com/test", {})

            assert result == {"id": 123, "title": "Test"}
            assert mock_session.get.call_count == 2
            # Should have slept for proactive delay + retry after
            assert mock_sleep.call_count == 2

    def test_call_429_max_retries_exceeded(self, robust_tmdb):
        """Test 429 handling when max retries exceeded."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "1"}

        with patch.object(robust_tmdb, "_session") as mock_session, patch("time.sleep"):
            mock_session.get.return_value = mock_response

            with pytest.raises(Exception):  # TMDbException
                robust_tmdb._call("https://api.test.com/test", {})

            # Should have tried max_retries times
            assert mock_session.get.call_count == robust_tmdb._max_retries

    def test_call_network_error_with_backoff(self, robust_tmdb):
        """Test network error handling with exponential backoff."""
        with (
            patch.object(robust_tmdb, "_session") as mock_session,
            patch("time.sleep") as mock_sleep,
        ):
            mock_session.get.side_effect = RequestException("Network error")

            with pytest.raises(Exception):  # TMDbException
                robust_tmdb._call("https://api.test.com/test", {})

            # Should have tried max_retries times
            assert mock_session.get.call_count == robust_tmdb._max_retries
            # Should have exponential backoff sleeps
            assert mock_sleep.call_count == robust_tmdb._max_retries


class TestTMDBService:
    """Test TMDBService class functionality."""

    @pytest.fixture
    def service(self):
        """Create test TMDBService instance."""
        with (
            patch("requests_cache.CachedSession"),
            patch("tmdbv3api.TMDb"),
            patch("tmdbv3api.Movie"),
            patch("tmdbv3api.TV"),
            patch("tmdbv3api.Search"),
        ):
            return TMDBService(api_key="test_api_key")

    def test_initialization(self, service):
        """Test TMDBService initialization."""
        assert service.tmdb.api_key == "test_api_key"
        assert service.tmdb.language == "en"
        assert service.movie_search is not None
        assert service.tv_search is not None
        assert service.movie is not None
        assert service.tv is not None

    def test_initialization_without_api_key(self):
        """Test initialization fails without API key."""
        with pytest.raises(ValueError, match="TMDB API key is required"):
            TMDBService(api_key="")

    def test_initialization_with_empty_api_key(self):
        """Test initialization fails with empty API key."""
        with pytest.raises(ValueError, match="TMDB API key is required"):
            TMDBService(api_key=None)

    def test_search_movie_success(self, service):
        """Test successful movie search."""
        mock_results = [{"id": 123, "title": "Test Movie"}]

        with patch.object(service.movie_search, "movies", return_value=mock_results):
            result = service.search_movie("Test Movie")

            assert result == mock_results[0]
            service.movie_search.movies.assert_called_once_with({"query": "Test Movie"})

    def test_search_movie_not_found(self, service):
        """Test movie search with no results."""
        with patch.object(service.movie_search, "movies", return_value=[]):
            result = service.search_movie("Nonexistent Movie")

            assert result is None

    def test_search_movie_api_error(self, service):
        """Test movie search with API error."""
        from tmdbv3api.exceptions import TMDbException

        with patch.object(
            service.movie_search,
            "movies",
            side_effect=TMDbException("API Error"),
        ):
            result = service.search_movie("Test Movie")

            assert result is None

    def test_search_tv_success(self, service):
        """Test successful TV search."""
        mock_results = [{"id": 456, "name": "Test Show"}]

        with patch.object(service.tv_search, "tv_shows", return_value=mock_results):
            result = service.search_tv("Test Show")

            assert result == mock_results[0]
            service.tv_search.tv_shows.assert_called_once_with({"query": "Test Show"})

    def test_get_movie_details_success(self, service):
        """Test successful movie details retrieval."""
        mock_details = {"id": 123, "title": "Test Movie", "overview": "Test overview"}

        with patch.object(service.movie, "details", return_value=mock_details):
            result = service.get_movie_details(123)

            assert result == mock_details
            service.movie.details.assert_called_once_with(123)

    def test_get_tv_details_success(self, service):
        """Test successful TV details retrieval."""
        mock_details = {"id": 456, "name": "Test Show", "overview": "Test overview"}

        with patch.object(service.tv, "details", return_value=mock_details):
            result = service.get_tv_details(456)

            assert result == mock_details
            service.tv.details.assert_called_once_with(456)

    def test_get_tv_season_details_success(self, service):
        """Test successful TV season details retrieval."""
        mock_season = {"id": 456, "season_number": 1, "episode_count": 12}

        # Mock the season method on the service's tv object
        service.tv.season = Mock(return_value=mock_season)

        result = service.get_tv_season_details(456, 1)

        assert result == mock_season
        service.tv.season.assert_called_once_with(456, 1)

    def test_get_cache_stats(self, service):
        """Test cache statistics retrieval."""
        # Mock cache attributes
        service.session.cache = Mock()
        service.session.cache.cache_name = "test_cache"
        service.session.cache.hit_count = 10
        service.session.cache.miss_count = 5
        service.session.cache.total_requests = 15

        stats = service.get_cache_stats()

        assert stats["cache_name"] == "test_cache"
        assert stats["hit_count"] == 10
        assert stats["miss_count"] == 5
        assert stats["total_requests"] == 15

    def test_clear_cache(self, service):
        """Test cache clearing."""
        service.session.cache = Mock()

        service.clear_cache()

        service.session.cache.clear.assert_called_once()

    def test_close(self, service):
        """Test service cleanup."""
        with patch.object(service.session, "close") as mock_close:
            service.close()
            mock_close.assert_called_once()


class TestTMDBServiceIntegration:
    """Integration tests for TMDB service."""

    @pytest.mark.slow
    def test_memory_usage_stability(self):
        """Test memory usage remains stable during many requests."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        with (
            patch("requests_cache.CachedSession"),
            patch("tmdbv3api.TMDb"),
            patch("tmdbv3api.Movie"),
            patch("tmdbv3api.TV"),
            patch("tmdbv3api.Search"),
        ):
            service = TMDBService(api_key="test_api_key")

            # Mock successful responses
            mock_movie = {"id": 123, "title": "Test Movie"}
            with patch.object(
                service.movie_search,
                "movies",
                return_value=[mock_movie],
            ):
                # Simulate many requests
                for i in range(100):
                    result = service.search_movie(f"Movie {i}")
                    assert result == mock_movie

            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory

            # Memory increase should be reasonable (< 10MB)
            assert memory_increase < 10 * 1024 * 1024, (
                f"Memory increased by {memory_increase / 1024 / 1024:.2f}MB"
            )

            service.close()

    @pytest.mark.integration
    def test_real_api_key_validation(self):
        """Test with real API key (if available)."""
        api_key = os.getenv("TMDB_API_KEY")

        if not api_key:
            pytest.skip("No real API key provided for integration test")

        service = TMDBService(api_key=api_key)

        try:
            # Test basic functionality
            results = service.search_tv("Attack on Titan")
            assert isinstance(results, dict) or results is None

            if results:
                details = service.get_tv_details(results["id"])
                assert isinstance(details, dict) or details is None

        finally:
            service.close()


class TestTMDBServiceWithHypothesis:
    """Property-based testing with Hypothesis."""

    @pytest.fixture
    def service(self):
        """Create test TMDBService instance."""
        with (
            patch("requests_cache.CachedSession"),
            patch("tmdbv3api.TMDb"),
            patch("tmdbv3api.Movie"),
            patch("tmdbv3api.TV"),
            patch("tmdbv3api.Search"),
        ):
            return TMDBService(api_key="test_api_key")

    @pytest.mark.hypothesis
    def test_search_with_various_inputs(self, service):
        """Test search methods with various inputs using Hypothesis."""
        from hypothesis import given
        from hypothesis import strategies as st

        @given(st.text(min_size=1, max_size=100))
        def test_movie_search_with_text(query):
            """Test movie search with various text inputs."""
            with patch.object(service.movie_search, "movies", return_value=[]):
                result = service.search_movie(query)
                assert result is None

        @given(st.text(min_size=1, max_size=100))
        def test_tv_search_with_text(query):
            """Test TV search with various text inputs."""
            with patch.object(service.tv_search, "tv_shows", return_value=[]):
                result = service.search_tv(query)
                assert result is None

        test_movie_search_with_text()
        test_tv_search_with_text()

    @pytest.mark.hypothesis
    def test_details_with_various_ids(self, service):
        """Test details methods with various IDs using Hypothesis."""
        from hypothesis import given
        from hypothesis import strategies as st

        @given(st.integers(min_value=1, max_value=1000000))
        def test_movie_details_with_id(movie_id):
            """Test movie details with various IDs."""
            with patch.object(service.movie, "details", return_value=None):
                result = service.get_movie_details(movie_id)
                assert result is None

        @given(st.integers(min_value=1, max_value=1000000))
        def test_tv_details_with_id(tv_id):
            """Test TV details with various IDs."""
            with patch.object(service.tv, "details", return_value=None):
                result = service.get_tv_details(tv_id)
                assert result is None

        test_movie_details_with_id()
        test_tv_details_with_id()


if __name__ == "__main__":
    pytest.main([__file__])
