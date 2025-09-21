"""Tests for TMDB API client functionality.

This module contains comprehensive tests for the TMDB client including
search functionality, metadata extraction, error handling, and caching.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from src.core.tmdb_client import (
    TMDBAPIError,
    TMDBClient,
    TMDBConfig,
    TMDBError,
    TMDBRateLimitError,
    create_tmdb_client,
    create_tmdb_client_with_config,
)


class TestTMDBConfig:
    """Test TMDB configuration."""

    def test_config_creation(self) -> None:
        """Test TMDBConfig creation with default values."""
        config = TMDBConfig(api_key="test_key")

        assert config.api_key == "test_key"
        assert config.language == "ko-KR"
        assert config.fallback_language == "en-US"
        assert config.timeout == 30
        assert config.max_retries == 3
        assert config.cache_only_mode is False

    def test_config_custom_values(self) -> None:
        """Test TMDBConfig with custom values."""
        config = TMDBConfig(
            api_key="custom_key",
            language="en-US",
            fallback_language="ja-JP",
            timeout=60,
            max_retries=5,
            cache_only_mode=True,
        )

        assert config.api_key == "custom_key"
        assert config.language == "en-US"
        assert config.fallback_language == "ja-JP"
        assert config.timeout == 60
        assert config.max_retries == 5
        assert config.cache_only_mode is True


class TestTMDBClient:
    """Test TMDB client functionality."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return TMDBConfig(api_key="test_api_key")

    @pytest.fixture
    def client(self, config):
        """Create test client."""
        return TMDBClient(config)

    @pytest.fixture
    def mock_series_data(self) -> None:
        """Mock series data for testing."""
        return {
            "id": 12345,
            "name": "Test Anime",
            "original_name": "テストアニメ",
            "overview": "A test anime series",
            "poster_path": "/test_poster.jpg",
            "backdrop_path": "/test_backdrop.jpg",
            "first_air_date": "2023-01-01",
            "last_air_date": "2023-12-31",
            "status": "Ended",
            "vote_average": 8.5,
            "vote_count": 1000,
            "popularity": 75.5,
            "genres": [{"name": "Action"}, {"name": "Adventure"}],
            "networks": [{"name": "Test Network"}],
            "number_of_seasons": 2,
            "number_of_episodes": 24,
            "original_language": "ja",
            "alternative_titles": {"results": [{"iso_3166_1": "KR", "title": "테스트 애니메이션"}]},
        }

    def test_client_initialization(self, config) -> None:
        """Test client initialization."""
        client = TMDBClient(config)

        assert client.config == config
        assert client._cache == {}
        assert client._rate_limited_until is None
        assert client._retry_stats["total_requests"] == 0
        assert client._cache_hits == 0
        assert client._cache_misses == 0

    @patch("src.core.tmdb_client.tmdb")
    def test_setup_tmdb(self, mock_tmdb, config) -> None:
        """Test TMDB setup."""
        _client = TMDBClient(config)

        mock_tmdb.API_KEY = config.api_key
        mock_tmdb.REQUESTS_TIMEOUT = config.timeout
        mock_tmdb.REQUESTS_SESSION.params.update.assert_called_once()

    def test_mask_api_key(self, client) -> None:
        """Test API key masking."""
        masked = client._mask_api_key("1234567890abcdef")
        assert masked == "123456****cdef"

        # Test short key
        masked_short = client._mask_api_key("123")
        assert masked_short == "***"

        # Test empty key
        masked_empty = client._mask_api_key("")
        assert masked_empty == ""

    def test_contains_korean_characters(self, client) -> None:
        """Test Korean character detection."""
        assert client._contains_korean_characters("안녕하세요") is True
        assert client._contains_korean_characters("Hello 안녕") is True
        assert client._contains_korean_characters("Hello World") is False
        assert client._contains_korean_characters("") is False
        assert client._contains_korean_characters(None) is False

    def test_find_korean_title(self, client, mock_series_data) -> None:
        """Test Korean title finding logic."""
        # Test with Korean alternative title
        korean_title = client.find_korean_title(mock_series_data)
        assert korean_title == "테스트 애니메이션"

        # Test without Korean alternative title
        data_no_korean = mock_series_data.copy()
        data_no_korean["alternative_titles"]["results"] = []
        korean_title = client.find_korean_title(data_no_korean)
        assert korean_title == ""  # No Korean title found

        # Test with original language Korean
        data_korean_original = mock_series_data.copy()
        data_korean_original["original_language"] = "ko"
        data_korean_original["alternative_titles"]["results"] = []
        korean_title = client.find_korean_title(data_korean_original)
        assert korean_title == "Test Anime"

    def test_get_title_priority_matrix(self, client, mock_series_data) -> None:
        """Test title priority matrix."""
        matrix = client.get_title_priority_matrix(mock_series_data)

        assert matrix["korean"] == "테스트 애니메이션"
        assert matrix["main"] == "Test Anime"
        assert matrix["original"] == "テストアニメ"
        assert matrix["english"] == ""  # No English alternative title

    def test_clean_title_for_comparison(self, client) -> None:
        """Test title cleaning for comparison."""
        # Test with prefixes
        cleaned = client._clean_title_for_comparison("[애니] Test Anime")
        assert cleaned == "Test Anime"

        # Test with suffixes
        cleaned = client._clean_title_for_comparison("Test Anime (TV)")
        assert cleaned == "Test Anime"

        # Test with multiple spaces
        cleaned = client._clean_title_for_comparison("  Test   Anime  ")
        assert cleaned == "Test Anime"

        # Test empty string
        cleaned = client._clean_title_for_comparison("")
        assert cleaned == ""

    def test_find_best_match(self, client) -> None:
        """Test best match finding."""
        query = "Attack on Titan"
        search_results = [
            {"id": 1, "name": "Attack on Titan", "original_name": "Shingeki no Kyojin"},
            {"id": 2, "name": "Titan", "original_name": "Titan"},
            {"id": 3, "name": "Attack on Something Else", "original_name": "Something"},
        ]

        best_match = client._find_best_match(query, search_results)
        assert best_match["id"] == 1
        assert best_match["name"] == "Attack on Titan"

        # Test with no results
        best_match = client._find_best_match(query, [])
        assert best_match is None

    def test_normalize_tmdb_id(self, client) -> None:
        """Test TMDB ID normalization."""
        assert client._normalize_tmdb_id(12345) == 12345
        assert client._normalize_tmdb_id("12345") == 12345
        assert client._normalize_tmdb_id(None) == 0
        assert client._normalize_tmdb_id("invalid") == 0

    def test_parse_date(self, client) -> None:
        """Test date parsing."""
        # Test valid date formats
        date1 = client._parse_date("2023-01-01", "test")
        assert isinstance(date1, datetime)
        assert date1.year == 2023
        assert date1.month == 1
        assert date1.day == 1

        # Test invalid date
        date2 = client._parse_date("invalid", "test")
        assert date2 is None

        # Test None
        date3 = client._parse_date(None, "test")
        assert date3 is None

    def test_normalize_rating(self, client) -> None:
        """Test rating normalization."""
        assert client._normalize_rating(8.5) == 8.5
        assert client._normalize_rating("8.5") == 8.5
        assert client._normalize_rating(15.0) == 10.0  # Clamp to max
        assert client._normalize_rating(-5.0) == 0.0  # Clamp to min
        assert client._normalize_rating("invalid") == 0.0

    def test_extract_and_normalize_genres(self, client) -> None:
        """Test genre extraction and normalization."""
        genres_data = [
            {"name": "Action"},
            {"name": " Adventure "},  # With extra spaces
            {"name": ""},  # Empty name
            {"invalid": "data"},  # Invalid structure
            {"name": "Action"},  # Duplicate
        ]

        genres = client._extract_and_normalize_genres(genres_data)
        assert genres == ["Action", "Adventure"]  # Deduplicated and normalized

    def test_extract_metadata(self, client, mock_series_data) -> None:
        """Test metadata extraction and normalization."""
        tmdb_anime = client.extract_metadata(mock_series_data)

        assert tmdb_anime.tmdb_id == 12345
        assert tmdb_anime.title == "Test Anime"
        assert tmdb_anime.original_title == "テストアニメ"
        assert tmdb_anime.korean_title == "테스트 애니메이션"
        assert tmdb_anime.overview == "A test anime series"
        assert tmdb_anime.poster_path == "/test_poster.jpg"
        assert tmdb_anime.backdrop_path == "/test_backdrop.jpg"
        assert tmdb_anime.status == "Ended"
        assert tmdb_anime.vote_average == 8.5
        assert tmdb_anime.vote_count == 1000
        assert tmdb_anime.popularity == 75.5
        assert tmdb_anime.genres == ["Action", "Adventure"]
        assert tmdb_anime.networks == ["Test Network"]
        assert tmdb_anime.number_of_seasons == 2
        assert tmdb_anime.number_of_episodes == 24
        assert tmdb_anime.raw_data == mock_series_data

        # Test dates
        assert isinstance(tmdb_anime.first_air_date, datetime)
        assert isinstance(tmdb_anime.last_air_date, datetime)

    def test_calculate_retry_delay(self, client) -> None:
        """Test retry delay calculation."""
        # Test basic exponential backoff
        delay1 = client._calculate_retry_delay(0, "generic")
        delay2 = client._calculate_retry_delay(1, "generic")
        delay3 = client._calculate_retry_delay(2, "generic")

        assert delay1 < delay2 < delay3

        # Test error-specific adjustments
        delay_rate_limit = client._calculate_retry_delay(1, "rate_limit")
        delay_server_error = client._calculate_retry_delay(1, "server_error")
        delay_generic = client._calculate_retry_delay(1, "generic")

        assert delay_rate_limit > delay_server_error > delay_generic

    def test_is_rate_limited(self, client) -> None:
        """Test rate limiting check."""
        # Not rate limited initially
        assert client._is_rate_limited() is False

        # Set rate limit
        client._set_rate_limit(60)
        assert client._is_rate_limited() is True

        # Clear rate limit
        client._clear_rate_limit()
        assert client._is_rate_limited() is False

    def test_set_cache_only_mode(self, client) -> None:
        """Test cache-only mode."""
        assert client.config.cache_only_mode is False

        client.set_cache_only_mode(True)
        assert client.config.cache_only_mode is True

        client.set_cache_only_mode(False)
        assert client.config.cache_only_mode is False

    def test_cache_operations(self, client) -> None:
        """Test cache operations."""
        # Test cache is empty initially
        assert len(client._cache) == 0

        # Add some test data
        client._cache["test_key"] = {"test": "data"}
        assert len(client._cache) == 1

        # Test cache stats
        stats = client.get_cache_stats()
        assert stats["cache_size"] == 1
        assert stats["cache_only_mode"] is False

        # Test cache info
        info = client.get_cache_info()
        assert info["cache_size"] == 1
        assert info["cache_keys"] == ["test_key"]
        assert info["cache_hit_rate"] == 0.0

        # Clear cache
        client.clear_cache()
        assert len(client._cache) == 0

    def test_retry_stats(self, client) -> None:
        """Test retry statistics."""
        # Initial stats
        stats = client.get_retry_stats()
        assert stats["total_requests"] == 0
        assert stats["successful_requests"] == 0
        assert stats["failed_requests"] == 0
        assert stats["success_rate"] == 0.0

        # Reset stats
        client.reset_retry_stats()
        stats = client.get_retry_stats()
        assert stats["total_requests"] == 0

    @patch("src.core.tmdb_client.tmdb")
    def test_search_tv_series_cache_only_mode(self, mock_tmdb, client) -> None:
        """Test search in cache-only mode."""
        client.set_cache_only_mode(True)

        # Should return empty list in cache-only mode
        results = client.search_tv_series("test query")
        assert results == []

    @patch("src.core.tmdb_client.tmdb")
    def test_get_tv_series_details_cache_only_mode(self, mock_tmdb, client) -> None:
        """Test get details in cache-only mode."""
        client.set_cache_only_mode(True)

        # Should return None in cache-only mode
        details = client.get_tv_series_details(12345)
        assert details is None

    @patch("src.core.tmdb_client.tmdb")
    def test_search_tv_series_with_cache(self, mock_tmdb, client) -> None:
        """Test search with caching."""
        # Mock search results
        mock_search = Mock()
        mock_search.tv.return_value = {
            "results": [{"id": 1, "name": "Test Anime", "original_name": "Test"}]
        }
        mock_tmdb.Search.return_value = mock_search

        # First call should hit API
        results1 = client.search_tv_series("test")
        assert len(results1) == 1
        assert client._cache_misses == 1
        assert client._cache_hits == 0

        # Second call should hit cache
        results2 = client.search_tv_series("test")
        assert len(results2) == 1
        assert client._cache_misses == 1
        assert client._cache_hits == 1

        # Results should be identical
        assert results1 == results2

    @patch("src.core.tmdb_client.tmdb")
    def test_get_tv_series_details_with_cache(self, mock_tmdb, client) -> None:
        """Test get details with caching."""
        # Mock TV details
        mock_tv = Mock()
        mock_tv.info.return_value = {"id": 12345, "name": "Test Anime"}
        mock_tmdb.TV.return_value = mock_tv

        # First call should hit API
        details1 = client.get_tv_series_details(12345)
        assert details1["id"] == 12345
        assert client._cache_misses == 1
        assert client._cache_hits == 0

        # Second call should hit cache
        details2 = client.get_tv_series_details(12345)
        assert details2["id"] == 12345
        assert client._cache_misses == 1
        assert client._cache_hits == 1

        # Results should be identical
        assert details1 == details2


class TestTMDBClientFactory:
    """Test TMDB client factory functions."""

    @patch("src.core.tmdb_client.get_config_manager")
    def test_create_tmdb_client_with_config(self, mock_get_config_manager) -> None:
        """Test creating client with config manager."""
        # Mock config manager
        mock_config_manager = Mock()
        mock_config_manager.get_tmdb_api_key.return_value = "test_key"
        mock_config_manager.get_tmdb_language.return_value = "ko-KR"
        mock_get_config_manager.return_value = mock_config_manager

        client = create_tmdb_client()

        assert client.config.api_key == "test_key"
        assert client.config.language == "ko-KR"
        assert client.config.fallback_language == "en-US"

    @patch("src.core.tmdb_client.get_config_manager")
    def test_create_tmdb_client_no_api_key(self, mock_get_config_manager) -> None:
        """Test creating client without API key."""
        # Mock config manager with no API key
        mock_config_manager = Mock()
        mock_config_manager.get_tmdb_api_key.return_value = None
        mock_get_config_manager.return_value = mock_config_manager

        with pytest.raises(TMDBError, match="TMDB API key not configured"):
            create_tmdb_client()

    def test_create_tmdb_client_with_explicit_config(self) -> None:
        """Test creating client with explicit configuration."""
        client = create_tmdb_client_with_config(
            api_key="test_key", language="en-US", fallback_language="ja-JP"
        )

        assert client.config.api_key == "test_key"
        assert client.config.language == "en-US"
        assert client.config.fallback_language == "ja-JP"


class TestTMDBExceptions:
    """Test TMDB exception classes."""

    def test_tmdb_error(self) -> None:
        """Test TMDBError exception."""
        error = TMDBError("Test error")
        assert str(error) == "Test error"

    def test_tmdb_api_error(self) -> None:
        """Test TMDBAPIError exception."""
        error = TMDBAPIError("API error", status_code=404)
        assert str(error) == "API error"
        assert error.status_code == 404

    def test_tmdb_rate_limit_error(self) -> None:
        """Test TMDBRateLimitError exception."""
        error = TMDBRateLimitError("Rate limited")
        assert str(error) == "Rate limited"


class TestIntegration:
    """Integration tests for TMDB client."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return TMDBConfig(api_key="test_api_key")

    @pytest.fixture
    def client(self, config):
        """Create test client."""
        return TMDBClient(config)

    @patch("src.core.tmdb_client.tmdb")
    def test_search_and_get_metadata_integration(self, mock_tmdb, client) -> None:
        """Test complete search and metadata extraction workflow."""
        # Mock search results
        mock_search = Mock()
        mock_search.tv.return_value = {
            "results": [{"id": 12345, "name": "Test Anime", "original_name": "Test"}]
        }
        mock_tmdb.Search.return_value = mock_search

        # Mock TV details
        mock_tv = Mock()
        mock_tv.info.return_value = {
            "id": 12345,
            "name": "Test Anime",
            "original_name": "Test",
            "overview": "Test overview",
            "poster_path": "/poster.jpg",
            "backdrop_path": "/backdrop.jpg",
            "first_air_date": "2023-01-01",
            "last_air_date": "2023-12-31",
            "status": "Ended",
            "vote_average": 8.5,
            "vote_count": 1000,
            "popularity": 75.5,
            "genres": [{"name": "Action"}],
            "networks": [{"name": "Test Network"}],
            "number_of_seasons": 1,
            "number_of_episodes": 12,
            "original_language": "en",
            "alternative_titles": {"results": []},
        }
        mock_tmdb.TV.return_value = mock_tv

        # Test complete workflow
        metadata = client.search_and_get_metadata("Test Anime")

        assert metadata is not None
        assert metadata.tmdb_id == 12345
        assert metadata.title == "Test Anime"
        assert metadata.overview == "Test overview"
        assert len(metadata.genres) == 1
        assert metadata.genres[0] == "Action"

    def test_error_handling_integration(self, client) -> None:
        """Test error handling in various scenarios."""
        # Test with empty query
        results = client.search_tv_series("")
        assert results == []

        # Test with whitespace-only query
        results = client.search_tv_series("   ")
        assert results == []

        # Test rate limiting
        client._set_rate_limit(60)
        assert client._is_rate_limited() is True

        # Test cache-only mode
        client.set_cache_only_mode(True)
        results = client.search_tv_series("test")
        assert results == []
