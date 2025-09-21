"""Unit tests for MetadataCache error handling and data validation."""

from collections import OrderedDict
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.core.compression import CacheDeserializationError
from src.core.metadata_cache import (
    CacheError,
    CacheSerializationError,
    CacheStorageError,
    CacheValidationError,
    MetadataCache,
)
from src.core.models import ParsedAnimeInfo, TMDBAnime


class TestCacheValidation:
    """Test cache validation functionality."""

    def test_validate_cache_key_valid(self):
        """Test validation of valid cache keys."""
        cache = MetadataCache()

        # Valid keys should not raise exceptions
        valid_keys = [
            "tmdb:123",
            "parsed:/path/to/file.mp4",
            "test-key_123",
            "key.with.dots",
            "key-with-dashes",
        ]

        for key in valid_keys:
            cache._validate_cache_key(key)  # Should not raise

    def test_validate_cache_key_invalid(self):
        """Test validation of invalid cache keys."""
        cache = MetadataCache()

        # Invalid keys should raise CacheValidationError
        invalid_cases = [
            (None, "Cache key must be a non-empty string"),
            ("", "Cache key must be a non-empty string"),
            (123, "Cache key must be a non-empty string"),
            ("a" * 256, "Cache key too long (max 255 characters)"),
            ("key\x00with_null", "Cache key contains invalid character"),
            ("key\nwith_newline", "Cache key contains invalid character"),
            ("key\rwith_carriage_return", "Cache key contains invalid character"),
            ("key\twith_tab", "Cache key contains invalid character"),
        ]

        for key, expected_message in invalid_cases:
            with pytest.raises(CacheValidationError) as exc_info:
                cache._validate_cache_key(key)
            assert expected_message in str(exc_info.value)
            assert exc_info.value.key == key

    def test_validate_cache_value_valid(self):
        """Test validation of valid cache values."""
        cache = MetadataCache()

        # Valid ParsedAnimeInfo
        parsed_info = ParsedAnimeInfo(
            title="Test Anime",
            episode_title="Episode 1",
            episode=1,
            season=1,
            year=2023,
            resolution="1080p",
            video_codec="H.264",
            audio_codec="AAC",
            release_group="TEST",
            file_extension=".mp4",
            source="test",
        )
        cache._validate_cache_value(parsed_info, "test_key")  # Should not raise

        # Valid TMDBAnime
        tmdb_anime = TMDBAnime(
            tmdb_id=123,
            title="Test Anime",
            original_title="Test Anime Original",
            overview="Test overview",
            release_date="2023-01-01",
            poster_path="/poster.jpg",
            backdrop_path="/backdrop.jpg",
            first_air_date="2023-01-01",
            last_air_date="2023-12-31",
            status="Released",
            vote_average=8.5,
            vote_count=1000,
            popularity=85.5,
            genres=["Action", "Drama"],
            networks=["Test Network"],
            production_companies=["Test Studio"],
            production_countries=["US"],
            spoken_languages=["English"],
            number_of_seasons=1,
            number_of_episodes=12,
            tagline="Test tagline",
            homepage="https://test.com",
            imdb_id="tt1234567",
            external_ids={"imdb": "tt1234567"},
            quality_score=0.95,
            search_strategy="exact",
            fallback_round=0,
        )
        cache._validate_cache_value(tmdb_anime, "test_key")  # Should not raise

    def test_validate_cache_value_invalid(self):
        """Test validation of invalid cache values."""
        cache = MetadataCache()

        # None value
        with pytest.raises(CacheValidationError) as exc_info:
            cache._validate_cache_value(None, "test_key")
        assert "Cache value cannot be None" in str(exc_info.value)

        # Wrong type
        with pytest.raises(CacheValidationError) as exc_info:
            cache._validate_cache_value("invalid", "test_key")
        assert "Cache value must be ParsedAnimeInfo or TMDBAnime" in str(exc_info.value)

        # Invalid ParsedAnimeInfo
        invalid_parsed = ParsedAnimeInfo(
            title="",  # Empty title
        )
        with pytest.raises(CacheValidationError) as exc_info:
            cache._validate_cache_value(invalid_parsed, "test_key")
        assert "title must be a non-empty string" in str(exc_info.value)
        assert exc_info.value.field == "title"

        # Invalid TMDBAnime
        invalid_tmdb = TMDBAnime(
            tmdb_id=0,  # Invalid tmdb_id
            title="Test",
        )
        with pytest.raises(CacheValidationError) as exc_info:
            cache._validate_cache_value(invalid_tmdb, "test_key")
        assert "tmdb_id must be a non-zero integer" in str(exc_info.value)
        assert exc_info.value.field == "tmdb_id"


class TestCacheErrorHandling:
    """Test cache error handling in main operations."""

    def test_get_with_invalid_key(self):
        """Test get() with invalid key raises CacheValidationError."""
        cache = MetadataCache()

        with pytest.raises(CacheValidationError):
            cache.get("")  # Empty key

        with pytest.raises(CacheValidationError):
            cache.get(None)  # None key

        with pytest.raises(CacheValidationError):
            cache.get("key\x00with_null")  # Invalid character

    def test_put_with_invalid_key(self):
        """Test put() with invalid key raises CacheValidationError."""
        cache = MetadataCache()
        valid_value = ParsedAnimeInfo(title="Test Anime")

        with pytest.raises(CacheValidationError):
            cache.put("", valid_value)  # Empty key

        with pytest.raises(CacheValidationError):
            cache.put(None, valid_value)  # None key

    def test_put_with_invalid_value(self):
        """Test put() with invalid value raises CacheValidationError."""
        cache = MetadataCache()

        with pytest.raises(CacheValidationError):
            cache.put("test_key", None)  # None value

        with pytest.raises(CacheValidationError):
            cache.put("test_key", "invalid")  # Wrong type

    def test_delete_with_invalid_key(self):
        """Test delete() with invalid key raises CacheValidationError."""
        cache = MetadataCache()

        with pytest.raises(CacheValidationError):
            cache.delete("")  # Empty key

        with pytest.raises(CacheValidationError):
            cache.delete(None)  # None key

    def test_get_with_corrupted_cache_entry(self):
        """Test get() handles corrupted cache entries gracefully."""
        cache = MetadataCache()
        cache._enabled = True
        cache._cache_only_mode = True  # Disable database fallback for simpler test

        # Create a corrupted entry that will fail decompression
        corrupted_entry = Mock()
        corrupted_entry.created_at = 0  # Not expired
        corrupted_entry.value = "corrupted_data"

        with patch.object(cache, '_decompress_if_needed') as mock_decompress:
            mock_decompress.side_effect = CacheSerializationError("Decompression failed")

            # Mock _cache as OrderedDict with move_to_end method
            mock_cache = OrderedDict({"test_key": corrupted_entry})
            mock_cache.move_to_end = MagicMock()

            with patch.object(cache, '_cache', mock_cache):
                with patch.object(cache, '_lock'):
                    with patch.object(cache, '_remove_entry') as mock_remove:
                        # Should not raise exception, should return default
                        result = cache.get("test_key", "default_value")

                        # Should have removed corrupted entry
                        mock_remove.assert_called_once_with("test_key")
                        # Should return default value
                        assert result == "default_value"

    def test_put_with_compression_failure(self):
        """Test put() handles compression failures."""
        cache = MetadataCache()
        cache._enabled = True

        valid_value = ParsedAnimeInfo(title="Test Anime")

        with patch.object(cache, '_apply_compression_if_needed') as mock_compress:
            mock_compress.side_effect = CacheSerializationError("Compression failed")

            with pytest.raises(CacheStorageError) as exc_info:
                cache.put("test_key", valid_value)

            assert "Compression failed" in str(exc_info.value)
            assert exc_info.value.operation == "store"

    def test_put_with_cache_storage_failure(self):
        """Test put() handles cache storage failures."""
        cache = MetadataCache()
        cache._enabled = True

        valid_value = ParsedAnimeInfo(title="Test Anime")

        with patch.object(cache, '_store_in_cache') as mock_store:
            mock_store.side_effect = CacheStorageError("Storage failed")

            with pytest.raises(CacheStorageError) as exc_info:
                cache.put("test_key", valid_value)

            assert "Storage failed" in str(exc_info.value)

    def test_store_in_cache_with_validation_failure(self):
        """Test _store_in_cache() handles validation failures."""
        cache = MetadataCache()

        with pytest.raises(CacheStorageError) as exc_info:
            cache._store_in_cache("", None)  # Invalid key and value

        assert "Validation failed" in str(exc_info.value)
        assert exc_info.value.operation == "store"

    def test_apply_compression_with_failure(self):
        """Test _apply_compression_if_needed() handles compression failures."""
        cache = MetadataCache()

        # Create a value with raw_data that will fail compression
        value = TMDBAnime(
            tmdb_id=123,
            title="Test",
            raw_data={"large": "data" * 1000}  # Large data to trigger compression
        )

        with patch('src.core.metadata_cache.compression_manager') as mock_compression:
            mock_compression.min_size_threshold = 100
            mock_compression.compress_for_storage.side_effect = CacheDeserializationError("Compression failed")

            with pytest.raises(CacheSerializationError) as exc_info:
                cache._apply_compression_if_needed(value)

            assert "TMDBAnime compression failed" in str(exc_info.value)
            assert exc_info.value.data_type == "TMDBAnime"

    def test_decompress_with_failure(self):
        """Test _decompress_if_needed() handles decompression failures."""
        cache = MetadataCache()

        # Create a value with compressed raw_data that will fail decompression
        value = TMDBAnime(
            tmdb_id=123,
            title="Test",
            raw_data="compressed_data"
        )

        with patch('src.core.metadata_cache.compression_manager') as mock_compression:
            mock_compression.decompress_from_storage.side_effect = CacheDeserializationError("Decompression failed")

            with pytest.raises(CacheSerializationError) as exc_info:
                cache._decompress_if_needed(value)

            assert "TMDBAnime decompression failed" in str(exc_info.value)
            assert exc_info.value.data_type == "TMDBAnime"


class TestCacheErrorRecovery:
    """Test cache error recovery mechanisms."""

    def test_cache_remains_stable_after_errors(self):
        """Test that cache remains stable after various errors."""
        cache = MetadataCache()
        cache._enabled = True

        # Store a valid entry
        valid_value = ParsedAnimeInfo(title="Test Anime")
        cache.put("valid_key", valid_value)

        # Verify it's stored
        assert cache.get("valid_key") is not None

        # Try to store invalid data (should fail but not affect existing data)
        with pytest.raises(CacheValidationError):
            cache.put("", None)  # Invalid key and value

        # Verify existing data is still there
        assert cache.get("valid_key") is not None

        # Try to get with invalid key (should fail but not affect existing data)
        with pytest.raises(CacheValidationError):
            cache.get("")  # Invalid key

        # Verify existing data is still there
        assert cache.get("valid_key") is not None

    def test_error_logging(self):
        """Test that errors are properly logged."""
        cache = MetadataCache()

        with patch('src.core.metadata_cache.logger') as mock_logger:
            # Test validation error logging
            with pytest.raises(CacheValidationError):
                cache.get("")

            # Should have logged the error
            mock_logger.error.assert_called()
            error_call = mock_logger.error.call_args[0][0]
            assert "Invalid cache key in get()" in error_call

    def test_custom_exception_attributes(self):
        """Test that custom exceptions have correct attributes."""
        # Test CacheValidationError
        error = CacheValidationError("Test message", "test_key", "test_field")
        assert error.key == "test_key"
        assert error.field == "test_field"
        assert str(error) == "Test message"

        # Test CacheStorageError
        error = CacheStorageError("Storage failed", "test_key", "store")
        assert error.key == "test_key"
        assert error.operation == "store"
        assert str(error) == "Storage failed"

        # Test CacheSerializationError
        error = CacheSerializationError("Serialization failed", "test_key", "TMDBAnime")
        assert error.key == "test_key"
        assert error.data_type == "TMDBAnime"
        assert str(error) == "Serialization failed"

        # Test CacheError with original_error
        original = ValueError("Original error")
        error = CacheError("Wrapper message", "test_key", original)
        assert error.key == "test_key"
        assert error.original_error == original
        assert str(error) == "Wrapper message"


if __name__ == "__main__":
    pytest.main([__file__])
